"""P1 v2: acréscimos gerados depois do ajuste do prompt (limites, efeitos colaterais e cada tentativa).

Cada teste aqui verifica algo que a v1 não verificava: o outro lado de um limite, o saldo
depois de uma falha, o número de chamadas ao Provedor ou o conteúdo de todas as tentativas.
"""
import httpx
import pytest

from tests.conftest import create_job, credits_of, make_user, new_job, send_webhook


# ------------------------------------------------------------------ R10: retentativas

def test_r10_retry_after_acima_de_10_segundos_e_limitado(client, provider, sleeps):
    provider.enqueue(httpx.Response(429, headers={"Retry-After": "60"}))
    make_user(client, "ana", 10)
    assert create_job(client).status_code == 201
    assert sleeps == [10]


def test_r10_429_sem_retry_after_usa_o_backoff(client, provider, sleeps):
    provider.enqueue(httpx.Response(429))
    make_user(client, "ana", 10)
    assert create_job(client).status_code == 201
    assert sleeps == [0.5]


def test_r10_nao_ha_espera_depois_da_ultima_tentativa(client, provider, sleeps):
    provider.enqueue(httpx.Response(503), httpx.Response(503), httpx.Response(503))
    make_user(client, "ana", 10)
    assert create_job(client).status_code == 502
    assert sleeps == [0.5, 1.0]


def test_r10_todas_as_tentativas_usam_a_mesma_idempotency_key_e_o_mesmo_corpo(client, provider):
    provider.enqueue(httpx.Response(503), httpx.Response(503))
    make_user(client, "ana", 10)
    job = create_job(client, resolution=512).json()
    assert provider.calls == 3
    assert {r.headers["Idempotency-Key"] for r in provider.requests} == {job["id"]}
    assert all(provider.body(i) == provider.body(0) for i in range(3))
    assert provider.body(0)["client_reference"] == job["id"]


def test_r10_429_persistente_esgota_as_tres_tentativas(client, provider):
    provider.enqueue(*[httpx.Response(429) for _ in range(3)])
    make_user(client, "ana", 10)
    response = create_job(client)
    assert response.status_code == 502
    assert response.json()["detail"] == "provider_unavailable"
    assert provider.calls == 3


def test_r12_a_ultima_falha_define_o_codigo_de_erro(client, provider):
    provider.enqueue(httpx.ReadTimeout("x"), httpx.ReadTimeout("x"), httpx.Response(503))
    make_user(client, "ana", 10)
    assert create_job(client).json()["detail"] == "provider_unavailable"

    provider.enqueue(httpx.Response(503), httpx.Response(503), httpx.ReadTimeout("x"))
    assert create_job(client).json()["detail"] == "provider_timeout"


# ------------------------------------------------------- R13: respostas inválidas

@pytest.mark.parametrize(
    "resposta",
    [
        httpx.Response(202, json=[]),
        httpx.Response(202, json=None),
        httpx.Response(202, json="gen_1"),
        httpx.Response(202, json=42),
        httpx.Response(204),
        httpx.Response(301, headers={"Location": "https://outro.test"}),
    ],
)
def test_r13_respostas_que_nao_sao_um_objeto_com_id(client, provider, resposta):
    provider.enqueue(resposta)
    make_user(client, "ana", 10)
    response = create_job(client)
    assert response.status_code == 502
    assert response.json()["detail"] == "provider_invalid_response"
    assert provider.calls == 1


# ------------------------------------------------ R14: efeitos de toda falha de criação

CENARIOS_DE_FALHA = {
    "5xx": ([httpx.Response(503)] * 3, 502, "provider_unavailable"),
    "timeout": ([httpx.ReadTimeout("x")] * 3, 504, "provider_timeout"),
    "conexao": ([httpx.ConnectError("x")] * 3, 502, "provider_unavailable"),
    "rejeitado": ([httpx.Response(422)], 502, "provider_rejected"),
    "sem_id": ([httpx.Response(202, json={})], 502, "provider_invalid_response"),
}


@pytest.mark.parametrize("cenario", list(CENARIOS_DE_FALHA))
def test_r14_toda_falha_devolve_o_credito_e_registra_o_job_como_failed(client, provider, cenario):
    respostas, http_status, codigo = CENARIOS_DE_FALHA[cenario]
    provider.enqueue(*respostas)
    make_user(client, "ana", 10)

    response = create_job(client, resolution=2048)

    assert response.status_code == http_status
    corpo = response.json()
    assert corpo["detail"] == codigo
    assert credits_of(client) == 10
    job = client.get(f"/jobs/{corpo['job_id']}").json()
    assert job["status"] == "failed"
    assert job["failure_reason"] == codigo
    assert job["cost"] == 4
    assert client.get("/jobs").json()["total"] == 1


# ---------------------------------------- R05 a R08: o Provedor não é chamado sem necessidade

def test_r06_r07_r05_nao_chamam_o_provedor(client, provider):
    make_user(client, "ana", 1)
    create_job(client, user_id="fantasma")
    create_job(client, resolution=2048)
    create_job(client, prompt="")
    assert provider.calls == 0
    assert credits_of(client) == 1
    assert client.get("/jobs").json()["total"] == 0


def test_r08_um_unico_debito_e_uma_unica_chamada(client, provider):
    make_user(client, "ana", 10)
    create_job(client, resolution=2048)
    assert provider.calls == 1
    assert credits_of(client) == 6


# --------------------------------------------------------------- limites de validação

def test_r19_error_com_200_caracteres_e_aceito_e_com_201_nao(client):
    job = new_job(client)
    ok = send_webhook(client, {"id": job["provider_id"], "status": "failed", "error": "e" * 200})
    assert ok.status_code == 200

    outro = new_job(client, user_id="bia")
    nok = send_webhook(client, {"id": outro["provider_id"], "status": "failed", "error": "e" * 201})
    assert nok.status_code == 422


def test_r02_credits_como_texto_numerico_e_rejeitado(client):
    assert client.put("/users/ana", json={"credits": "10"}).status_code == 422


def test_r17_offset_alem_do_fim_devolve_lista_vazia_com_total(client):
    make_user(client, "ana", 20)
    for _ in range(3):
        create_job(client)
    body = client.get("/jobs", params={"offset": 10}).json()
    assert body == {"items": [], "total": 3}


def test_r17_limit_100_e_aceito(client):
    assert client.get("/jobs", params={"limit": 100}).status_code == 200


def test_r17_filtros_combinados(client):
    make_user(client, "ana", 20)
    make_user(client, "bia", 20)
    a = create_job(client, user_id="ana").json()
    create_job(client, user_id="bia")
    send_webhook(client, {"id": a["provider_id"], "status": "failed"})
    body = client.get("/jobs", params={"user_id": "ana", "status": "failed"}).json()
    assert body["total"] == 1 and body["items"][0]["id"] == a["id"]
    assert client.get("/jobs", params={"user_id": "bia", "status": "failed"}).json()["total"] == 0


# ----------------------------------------------------------- webhook: efeitos colaterais

def test_r18_assinatura_invalida_nao_altera_nada(client):
    job = new_job(client, credits=10)
    send_webhook(client, {"id": job["provider_id"], "status": "failed"}, secret="errado")
    assert client.get(f"/jobs/{job['id']}").json()["status"] == "processing"
    assert credits_of(client) == 8


def test_r18_a_assinatura_e_verificada_antes_do_corpo(client):
    response = send_webhook(client, {"status": "talvez"}, secret="errado")
    assert response.status_code == 401


def test_r21_sucesso_nao_mexe_nos_creditos(client):
    job = new_job(client, credits=10)
    send_webhook(client, {"id": job["provider_id"], "status": "succeeded", "image_url": "https://cdn.test/a.png"})
    assert credits_of(client) == 8


def test_r23_evento_ignorado_nao_altera_image_url_nem_motivo(client):
    job = new_job(client, credits=10)
    send_webhook(client, {"id": job["provider_id"], "status": "failed", "error": "primeiro"})
    send_webhook(client, {"id": job["provider_id"], "status": "succeeded", "image_url": "https://cdn.test/b.png"})
    final = client.get(f"/jobs/{job['id']}").json()
    assert final["status"] == "failed"
    assert final["failure_reason"] == "primeiro"
    assert final["image_url"] is None
    assert credits_of(client) == 10
