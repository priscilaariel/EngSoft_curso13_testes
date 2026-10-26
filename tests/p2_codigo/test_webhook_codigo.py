"""P2: webhook, a partir do código (assinatura, parsing do corpo bruto e concorrência)."""
import json
import threading

import pytest
from fastapi.testclient import TestClient

from tests.conftest import SECRET, credits_of, new_job, send_webhook, sign


def test_p2_corpo_que_nao_e_json_com_assinatura_valida_retorna_422(client):
    new_job(client)
    response = send_webhook(client, {}, raw=b"isto nao e json")
    assert response.status_code == 422
    assert response.json() == {"detail": "invalid_payload"}


def test_p2_corpo_vazio_com_assinatura_valida_retorna_422(client):
    assert send_webhook(client, {}, raw=b"").status_code == 422


def test_p2_campo_desconhecido_no_evento_e_rejeitado(client):
    job = new_job(client)
    response = send_webhook(client, {"id": job["provider_id"], "status": "failed", "extra": 1})
    assert response.status_code == 422


def test_p2_evento_failed_com_image_url_nao_guarda_a_url(client):
    job = new_job(client)
    send_webhook(client, {"id": job["provider_id"], "status": "failed", "image_url": "https://cdn.test/x.png"})
    final = client.get(f"/jobs/{job['id']}").json()
    assert final["status"] == "failed" and final["image_url"] is None


def test_p2_evento_succeeded_com_error_ignora_o_texto_de_erro(client):
    job = new_job(client)
    send_webhook(
        client,
        {"id": job["provider_id"], "status": "succeeded", "image_url": "https://cdn.test/x.png", "error": "ruido"},
    )
    final = client.get(f"/jobs/{job['id']}").json()
    assert final["status"] == "succeeded" and final["failure_reason"] is None


def test_p2_id_vazio_no_evento_retorna_422(client):
    assert send_webhook(client, {"id": "", "status": "failed"}).status_code == 422


def test_p2_job_que_falhou_na_criacao_nao_pode_receber_webhook(client, provider):
    import httpx

    provider.enqueue(httpx.Response(400))
    client.put("/users/ana", json={"credits": 10})
    client.post("/jobs", json={"user_id": "ana", "prompt": "x"})
    assert send_webhook(client, {"id": "gen_1", "status": "succeeded", "image_url": "https://a.test/i.png"}).status_code == 404
    assert credits_of(client) == 10


def test_p2_assinatura_em_maiusculas_e_recusada(client):
    job = new_job(client)
    raw = json.dumps({"id": job["provider_id"], "status": "failed"}).encode()
    headers = {"Content-Type": "application/json", "X-Signature": sign(raw).upper()}
    assert client.post("/webhooks/provider", content=raw, headers=headers).status_code == 401


def test_p2_assinatura_calculada_sobre_o_corpo_reserializado_e_recusada(client):
    job = new_job(client)
    evento = {"id": job["provider_id"], "status": "failed"}
    raw_com_espacos = json.dumps(evento, indent=2).encode()
    headers = {"Content-Type": "application/json", "X-Signature": sign(json.dumps(evento).encode())}
    assert client.post("/webhooks/provider", content=raw_com_espacos, headers=headers).status_code == 401


def test_p2_assinatura_com_caractere_nao_ascii_retorna_401_e_nao_erro_500(client):
    job = new_job(client)
    raw = json.dumps({"id": job["provider_id"], "status": "failed"}).encode()
    headers = [(b"content-type", b"application/json"), (b"x-signature", "assinatura-é".encode("latin-1"))]
    assert client.post("/webhooks/provider", content=raw, headers=dict(headers)).status_code == 401


def test_p2_webhooks_simultaneos_do_mesmo_evento_reembolsam_uma_unica_vez(app):
    setup = TestClient(app)
    job = new_job(setup, credits=10, resolution=2048)
    assert credits_of(setup) == 6
    evento = {"id": job["provider_id"], "status": "failed", "error": "falha"}
    resultados, barreira = [], threading.Barrier(8)

    def disparar():
        local = TestClient(app)
        barreira.wait()
        resultados.append(send_webhook(local, evento).json()["result"])

    threads = [threading.Thread(target=disparar) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]

    assert sorted(resultados) == ["applied"] + ["ignored"] * 7
    assert credits_of(setup) == 10


def test_p2_webhooks_de_jobs_diferentes_do_mesmo_usuario_somam_os_reembolsos(client):
    primeiro = new_job(client, credits=20, resolution=2048)
    segundo = client.post("/jobs", json={"user_id": "ana", "prompt": "outro", "resolution": 512}).json()
    assert credits_of(client) == 15
    send_webhook(client, {"id": primeiro["provider_id"], "status": "failed"})
    send_webhook(client, {"id": segundo["provider_id"], "status": "failed"})
    assert credits_of(client) == 20
