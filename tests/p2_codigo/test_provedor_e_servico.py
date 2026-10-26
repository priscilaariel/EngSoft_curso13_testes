"""P2: testes gerados a partir do código-fonte, depois da análise em passos dos pontos de falha.

Pontos de integração cobertos: API e Provedor (cabeçalhos, retentativas, respostas malformadas),
serviço e repositório (falha parcial depois que o Provedor já aceitou) e atomicidade no SQLite.
"""
import sqlite3
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.conftest import BASE_URL, SECRET, create_job, credits_of, make_user, new_job, send_webhook


# --------------------------------------------- Retry-After vindo de uma rede não confiável

@pytest.mark.parametrize("valor", [b"abc", b"-1", b"1.5", b"", b"Wed, 21 Oct 2026 07:28:00 GMT"])
def test_p2_retry_after_que_nao_e_inteiro_cai_no_backoff(client, provider, sleeps, valor):
    provider.enqueue(httpx.Response(429, headers=[(b"Retry-After", valor)]))
    make_user(client, "ana", 10)
    assert create_job(client).status_code == 201
    assert sleeps == [0.5]


def test_p2_retry_after_zero_nao_espera(client, provider, sleeps):
    provider.enqueue(httpx.Response(429, headers={"Retry-After": "0"}))
    make_user(client, "ana", 10)
    assert create_job(client).status_code == 201
    assert sleeps == [0]


def test_p2_retry_after_com_digito_nao_ascii_nao_derruba_a_api(client, provider, sleeps):
    # "²" passa em str.isdigit() mas não em int(): o cabeçalho vem da rede e não pode causar erro 500
    provider.enqueue(httpx.Response(429, headers=[(b"Retry-After", b"\xb2")]))
    make_user(client, "ana", 10)
    response = create_job(client)
    assert response.status_code == 201
    assert sleeps == [0.5]


def test_p2_retry_after_so_vale_para_429(client, provider, sleeps):
    provider.enqueue(httpx.Response(503, headers={"Retry-After": "7"}))
    make_user(client, "ana", 10)
    assert create_job(client).status_code == 201
    assert sleeps == [0.5]


# ------------------------------------------------------ respostas estranhas do Provedor

def test_p2_provedor_repete_o_mesmo_id_para_outro_job(client, provider):
    provider.enqueue(httpx.Response(202, json={"id": "gen_dup"}), httpx.Response(202, json={"id": "gen_dup"}))
    make_user(client, "ana", 10)
    primeiro = create_job(client)
    segundo = create_job(client)

    assert primeiro.status_code == 201
    assert segundo.status_code == 502
    assert segundo.json()["detail"] == "provider_invalid_response"
    assert credits_of(client) == 8
    falho = client.get(f"/jobs/{segundo.json()['job_id']}").json()
    assert falho["status"] == "failed" and falho["provider_id"] is None
    assert client.get(f"/jobs/{primeiro.json()['id']}").json()["status"] == "processing"


def test_p2_corpo_extra_na_resposta_202_e_ignorado(client, provider):
    provider.enqueue(httpx.Response(202, json={"id": "gen_9", "eta": 12, "fila": 3}))
    make_user(client, "ana", 10)
    assert create_job(client).json()["provider_id"] == "gen_9"


def test_p2_prompt_com_emoji_e_quebra_de_linha_chega_intacto_ao_provedor(client, provider):
    prompt = "linha 1\nlinha 2 " + "😀" * 400
    make_user(client, "ana", 10)
    job = create_job(client, prompt=prompt).json()
    assert job["prompt"] == prompt
    assert provider.body()["prompt"] == prompt


def test_p2_500_emojis_contam_como_500_caracteres(client):
    make_user(client, "ana", 10)
    assert create_job(client, prompt="😀" * 500).status_code == 201
    assert create_job(client, prompt="😀" * 501).status_code == 422


# ------------------------------------------- configuração: URL base, tentativas e backoff

def _app_com(provider, sleeps, **overrides):
    settings = Settings(
        db_path=":memory:", provider_base_url=BASE_URL, provider_api_key="k",
        webhook_secret=SECRET, provider_backoff_seconds=0.5, **overrides,
    )
    http = httpx.Client(transport=httpx.MockTransport(provider.handler))
    return TestClient(create_app(settings=settings, http_client=http, sleep=sleeps.append))


def test_p2_url_base_com_barra_final_nao_gera_barra_dupla(provider, sleeps):
    settings = Settings(db_path=":memory:", provider_base_url=BASE_URL + "/", webhook_secret=SECRET)
    http = httpx.Client(transport=httpx.MockTransport(provider.handler))
    client = TestClient(create_app(settings=settings, http_client=http, sleep=sleeps.append))
    client.put("/users/ana", json={"credits": 5})
    assert client.post("/jobs", json={"user_id": "ana", "prompt": "x"}).status_code == 201
    assert str(provider.requests[-1].url) == BASE_URL + "/v1/generations"


def test_p2_uma_unica_tentativa_configurada_nao_tem_retentativa_nem_espera(provider, sleeps):
    client = _app_com(provider, sleeps, provider_max_attempts=1)
    client.put("/users/ana", json={"credits": 5})
    provider.enqueue(httpx.Response(503))
    response = client.post("/jobs", json={"user_id": "ana", "prompt": "x"})
    assert response.status_code == 502
    assert provider.calls == 1 and sleeps == []


def test_p2_cinco_tentativas_configuradas_seguem_o_backoff_dobrando(provider, sleeps):
    client = _app_com(provider, sleeps, provider_max_attempts=5)
    client.put("/users/ana", json={"credits": 5})
    provider.enqueue(*[httpx.Response(500) for _ in range(5)])
    assert client.post("/jobs", json={"user_id": "ana", "prompt": "x"}).status_code == 502
    assert provider.calls == 5
    assert sleeps == [0.5, 1.0, 2.0, 4.0]


def test_p2_settings_from_env(monkeypatch):
    monkeypatch.setenv("RJ_DB_PATH", "outro.db")
    monkeypatch.setenv("RJ_PROVIDER_URL", "https://x.test")
    monkeypatch.setenv("RJ_PROVIDER_KEY", "abc")
    monkeypatch.setenv("RJ_WEBHOOK_SECRET", "s3")
    settings = Settings.from_env()
    assert (settings.db_path, settings.provider_base_url, settings.provider_api_key, settings.webhook_secret) == (
        "outro.db", "https://x.test", "abc", "s3",
    )


# ------------------------------- falha parcial: o Provedor aceitou, mas o banco falhou depois

def test_p2_falha_do_banco_depois_do_aceite_do_provedor_nao_deixa_credito_preso(app, provider):
    client = TestClient(app, raise_server_exceptions=False)
    make_user(client, "ana", 10)

    def quebrado(*_args, **_kwargs):
        raise sqlite3.OperationalError("disk I/O error")

    app.state.repo.mark_processing = quebrado
    response = create_job(client, resolution=1024)

    assert response.status_code == 500
    corpo = response.json()
    assert corpo["detail"] == "internal_error"
    job = client.get(f"/jobs/{corpo['job_id']}").json()
    assert job["status"] == "failed" and job["failure_reason"] == "internal_error"
    assert credits_of(client) == 10


# ------------------------------------------------ atomicidade do débito no SQLite

def test_p2_debito_e_insercao_do_job_sao_atomicos(app, monkeypatch):
    repo = app.state.repo
    repo.put_user("ana", 10)
    job = repo.create_job_debiting("ana", "x", 1024, 2)
    # força colisão de chave primária na inserção: o débito do mesmo comando precisa ser desfeito
    monkeypatch.setattr(uuid, "uuid4", lambda: uuid.UUID(job["id"]))
    with pytest.raises(sqlite3.IntegrityError):
        repo.create_job_debiting("ana", "y", 1024, 2)
    assert repo.get_user("ana")["credits"] == 8


def test_p2_fail_and_refund_em_job_finalizado_ou_inexistente_nao_devolve_nada(app):
    repo = app.state.repo
    repo.put_user("ana", 10)
    job = repo.create_job_debiting("ana", "x", 1024, 2)
    repo.mark_processing(job["id"], "gen_1")
    assert repo.fail_and_refund(job["id"], "motivo") is True
    assert repo.get_user("ana")["credits"] == 10
    assert repo.fail_and_refund(job["id"], "motivo") is False
    assert repo.fail_and_refund(str(uuid.uuid4()), "motivo") is False
    assert repo.get_user("ana")["credits"] == 10


def test_p2_user_id_com_sql_e_tratado_como_texto(client):
    make_user(client, "ana", 10)
    create_job(client)
    body = client.get("/jobs", params={"user_id": "x' OR '1'='1"}).json()
    assert body == {"items": [], "total": 0}


def test_p2_get_job_aceita_uuid_em_maiusculas(client):
    job = new_job(client)
    assert client.get(f"/jobs/{job['id'].upper()}").status_code == 200


def test_p2_updated_at_muda_quando_o_webhook_e_aplicado(client):
    job = new_job(client)
    send_webhook(client, {"id": job["provider_id"], "status": "succeeded", "image_url": "https://cdn.test/a.png"})
    depois = client.get(f"/jobs/{job['id']}").json()
    assert depois["updated_at"] > job["updated_at"]
    assert depois["created_at"] == job["created_at"]
