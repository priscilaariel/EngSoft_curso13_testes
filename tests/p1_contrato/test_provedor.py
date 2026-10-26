"""P1 v1: integração entre a API e o Provedor (R09 a R15)."""
import httpx
import pytest

from tests.conftest import API_KEY, create_job, make_user


def test_r09_requisicao_enviada_ao_provedor(client, provider):
    make_user(client, "ana", 10)
    job = create_job(client, prompt="um gato", resolution=512).json()

    assert provider.calls == 1
    request = provider.requests[0]
    assert request.method == "POST"
    assert request.url.path == "/v1/generations"
    assert request.headers["Authorization"] == f"Bearer {API_KEY}"
    assert request.headers["Idempotency-Key"] == job["id"]
    assert provider.body() == {"prompt": "um gato", "size": 512, "client_reference": job["id"]}


def test_r10_503_seguido_de_sucesso(client, provider):
    provider.enqueue(httpx.Response(503))
    make_user(client, "ana", 10)
    response = create_job(client)
    assert response.status_code == 201
    assert response.json()["status"] == "processing"
    assert provider.calls == 2


def test_r10_backoff_dobra_a_cada_tentativa(client, provider, sleeps):
    provider.enqueue(httpx.Response(503), httpx.Response(500))
    make_user(client, "ana", 10)
    assert create_job(client).status_code == 201
    assert sleeps == [0.5, 1.0]


def test_r10_retry_after_substitui_o_backoff(client, provider, sleeps):
    provider.enqueue(httpx.Response(429, headers={"Retry-After": "2"}))
    make_user(client, "ana", 10)
    assert create_job(client).status_code == 201
    assert sleeps == [2]


def test_r12_tres_falhas_5xx_retornam_502(client, provider):
    provider.enqueue(httpx.Response(503), httpx.Response(503), httpx.Response(503))
    make_user(client, "ana", 10)
    response = create_job(client)
    assert response.status_code == 502
    assert response.json()["detail"] == "provider_unavailable"
    assert provider.calls == 3


def test_r12_timeouts_retornam_504(client, provider):
    provider.enqueue(*[httpx.ReadTimeout("lento") for _ in range(3)])
    make_user(client, "ana", 10)
    response = create_job(client)
    assert response.status_code == 504
    assert response.json()["detail"] == "provider_timeout"


def test_r12_erro_de_conexao_retorna_502(client, provider):
    provider.enqueue(*[httpx.ConnectError("sem rota") for _ in range(3)])
    make_user(client, "ana", 10)
    response = create_job(client)
    assert response.status_code == 502
    assert response.json()["detail"] == "provider_unavailable"


def test_r11_4xx_nao_e_tentado_de_novo(client, provider):
    provider.enqueue(httpx.Response(400, json={"error": "prompt bloqueado"}))
    make_user(client, "ana", 10)
    response = create_job(client)
    assert response.status_code == 502
    assert response.json()["detail"] == "provider_rejected"
    assert provider.calls == 1


@pytest.mark.parametrize(
    "resposta",
    [
        httpx.Response(202, json={}),
        httpx.Response(202, content=b"nao e json"),
        httpx.Response(202, json={"id": ""}),
        httpx.Response(202, json={"id": 123}),
        httpx.Response(200, json={"id": "gen_x"}),
    ],
)
def test_r13_resposta_invalida_do_provedor(client, provider, resposta):
    provider.enqueue(resposta)
    make_user(client, "ana", 10)
    response = create_job(client)
    assert response.status_code == 502
    assert response.json()["detail"] == "provider_invalid_response"
    assert provider.calls == 1


def test_r14_falha_marca_job_como_failed_e_devolve_credito(client, provider):
    provider.enqueue(httpx.Response(400))
    make_user(client, "ana", 10)
    body = create_job(client, resolution=2048).json()
    job = client.get(f"/jobs/{body['job_id']}").json()
    assert job["status"] == "failed"
    assert job["failure_reason"] == "provider_rejected"
    assert client.get("/users/ana").json()["credits"] == 10


def test_r15_retentativa_com_sucesso_gera_um_unico_job(client, provider):
    provider.enqueue(httpx.Response(502))
    make_user(client, "ana", 10)
    create_job(client)
    assert client.get("/jobs").json()["total"] == 1
    assert client.get("/users/ana").json()["credits"] == 8
