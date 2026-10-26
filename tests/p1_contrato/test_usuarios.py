"""P1 v1: testes de integração gerados a partir do contrato (R01 a R03)."""
import pytest


def test_r01_put_cria_usuario_com_saldo(client):
    response = client.put("/users/ana", json={"credits": 10})
    assert response.status_code == 200
    assert response.json() == {"user_id": "ana", "credits": 10}


def test_r01_put_substitui_saldo_existente(client):
    client.put("/users/ana", json={"credits": 10})
    response = client.put("/users/ana", json={"credits": 3})
    assert response.status_code == 200
    assert client.get("/users/ana").json()["credits"] == 3


@pytest.mark.parametrize("credits", [0, 10000])
def test_r02_limites_validos_de_credits(client, credits):
    assert client.put("/users/ana", json={"credits": credits}).status_code == 200


@pytest.mark.parametrize("credits", [-1, 10001, "dez", 1.5, None])
def test_r02_credits_invalido_retorna_422(client, credits):
    assert client.put("/users/ana", json={"credits": credits}).status_code == 422


@pytest.mark.parametrize("user_id", ["ANA", "ana.silva", "a" * 33, "ana silva"])
def test_r02_user_id_invalido_retorna_422(client, user_id):
    assert client.put(f"/users/{user_id}", json={"credits": 1}).status_code == 422


def test_r03_get_usuario_existente(client):
    client.put("/users/bia", json={"credits": 7})
    response = client.get("/users/bia")
    assert response.status_code == 200
    assert response.json() == {"user_id": "bia", "credits": 7}


def test_r03_get_usuario_inexistente(client):
    response = client.get("/users/fantasma")
    assert response.status_code == 404
    assert response.json() == {"detail": "user_not_found"}
