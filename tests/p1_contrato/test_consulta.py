"""P1 v1: consulta de jobs (R16 e R17)."""
import pytest

from tests.conftest import create_job, make_user, new_job


def test_r16_get_job_existente(client):
    created = new_job(client)
    response = client.get(f"/jobs/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_r16_get_job_inexistente(client):
    response = client.get("/jobs/3f2b8c1e-9c0a-4b0e-8a57-111111111111")
    assert response.status_code == 404
    assert response.json() == {"detail": "job_not_found"}


def test_r16_id_que_nao_e_uuid(client):
    assert client.get("/jobs/abc").status_code == 422


def test_r17_listagem_com_total(client):
    make_user(client, "ana", 20)
    for _ in range(3):
        create_job(client)
    body = client.get("/jobs").json()
    assert body["total"] == 3
    assert len(body["items"]) == 3


def test_r17_filtro_por_usuario(client):
    make_user(client, "ana", 20)
    make_user(client, "bia", 20)
    create_job(client, user_id="ana")
    create_job(client, user_id="bia")
    create_job(client, user_id="bia")
    body = client.get("/jobs", params={"user_id": "bia"}).json()
    assert body["total"] == 2
    assert {item["user_id"] for item in body["items"]} == {"bia"}


def test_r17_filtro_por_status(client):
    make_user(client, "ana", 20)
    create_job(client)
    body = client.get("/jobs", params={"status": "processing"}).json()
    assert body["total"] == 1
    assert client.get("/jobs", params={"status": "failed"}).json()["total"] == 0


def test_r17_paginacao_com_limit_e_offset(client):
    make_user(client, "ana", 50)
    for _ in range(5):
        create_job(client)
    page = client.get("/jobs", params={"limit": 2, "offset": 2}).json()
    assert page["total"] == 5
    assert len(page["items"]) == 2


def test_r17_mais_recente_primeiro(client):
    make_user(client, "ana", 20)
    ids = [create_job(client).json()["id"] for _ in range(3)]
    items = client.get("/jobs").json()["items"]
    assert [item["id"] for item in items] == list(reversed(ids))


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"status": "voando"}],
)
def test_r17_parametros_invalidos(client, params):
    assert client.get("/jobs", params=params).status_code == 422
