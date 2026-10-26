"""P1 v1: webhook do Provedor (R18 a R23)."""
import json

import pytest

from tests.conftest import credits_of, new_job, send_webhook


def _evento(job, status="succeeded", **extra):
    base = {"id": job["provider_id"], "status": status}
    if status == "succeeded":
        base["image_url"] = "https://cdn.test/img.png"
    base.update(extra)
    return base


def test_r18_assinatura_invalida_retorna_401(client):
    job = new_job(client)
    response = send_webhook(client, _evento(job), secret="outro-segredo")
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid_signature"}


def test_r18_sem_assinatura_retorna_401(client):
    job = new_job(client)
    response = send_webhook(client, _evento(job), headers={"Content-Type": "application/json"})
    assert response.status_code == 401


def test_r21_sucesso_atualiza_o_job(client):
    job = new_job(client)
    response = send_webhook(client, _evento(job))
    assert response.status_code == 200
    assert response.json() == {"result": "applied"}
    atualizado = client.get(f"/jobs/{job['id']}").json()
    assert atualizado["status"] == "succeeded"
    assert atualizado["image_url"] == "https://cdn.test/img.png"


def test_r22_falha_devolve_credito(client):
    job = new_job(client, credits=10, resolution=2048)
    assert credits_of(client) == 6
    response = send_webhook(client, _evento(job, "failed", error="conteudo bloqueado"))
    assert response.status_code == 200
    atualizado = client.get(f"/jobs/{job['id']}").json()
    assert atualizado["status"] == "failed"
    assert atualizado["failure_reason"] == "conteudo bloqueado"
    assert credits_of(client) == 10


def test_r22_falha_sem_mensagem_usa_provider_failed(client):
    job = new_job(client)
    send_webhook(client, _evento(job, "failed"))
    assert client.get(f"/jobs/{job['id']}").json()["failure_reason"] == "provider_failed"


def test_r20_id_desconhecido(client):
    response = send_webhook(client, {"id": "gen_999", "status": "failed"})
    assert response.status_code == 404
    assert response.json() == {"detail": "job_not_found"}


@pytest.mark.parametrize(
    "payload",
    [
        {"id": "gen_1", "status": "talvez"},
        {"id": "gen_1", "status": "succeeded"},
        {"id": "gen_1", "status": "succeeded", "image_url": "http://inseguro.test/a.png"},
        {"status": "failed"},
    ],
)
def test_r19_payload_invalido(client, payload):
    new_job(client)
    response = send_webhook(client, payload)
    assert response.status_code == 422
    assert response.json() == {"detail": "invalid_payload"}


def test_r23_evento_duplicado_e_ignorado(client):
    job = new_job(client)
    send_webhook(client, _evento(job))
    response = send_webhook(client, _evento(job))
    assert response.status_code == 200
    assert response.json() == {"result": "ignored"}


def test_r23_falha_duplicada_nao_reembolsa_duas_vezes(client):
    job = new_job(client, credits=10)
    send_webhook(client, _evento(job, "failed"))
    send_webhook(client, _evento(job, "failed"))
    assert credits_of(client) == 10


def test_r23_evento_conflitante_apos_estado_final(client):
    job = new_job(client)
    send_webhook(client, _evento(job, "succeeded"))
    response = send_webhook(client, _evento(job, "failed"))
    assert response.json() == {"result": "ignored"}
    assert client.get(f"/jobs/{job['id']}").json()["status"] == "succeeded"
