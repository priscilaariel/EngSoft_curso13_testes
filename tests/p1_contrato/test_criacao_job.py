"""P1 v1: criação de job pela API (R04 a R08)."""
import pytest

from tests.conftest import create_job, credits_of, make_user


def test_r08_criacao_com_sucesso(client):
    make_user(client, "ana", 10)
    response = create_job(client)
    assert response.status_code == 201
    job = response.json()
    assert job["status"] == "processing"
    assert job["provider_id"] == "gen_1"
    assert job["user_id"] == "ana"
    assert job["image_url"] is None
    assert job["failure_reason"] is None


def test_r04_resolucao_padrao_e_1024_com_custo_2(client):
    make_user(client, "ana", 10)
    job = create_job(client).json()
    assert job["resolution"] == 1024
    assert job["cost"] == 2


@pytest.mark.parametrize("resolution,cost", [(512, 1), (1024, 2), (2048, 4)])
def test_r04_custo_por_resolucao(client, resolution, cost):
    make_user(client, "ana", 10)
    job = create_job(client, resolution=resolution).json()
    assert job["cost"] == cost
    assert credits_of(client) == 10 - cost


def test_r07_saldo_igual_ao_custo_termina_em_zero(client):
    make_user(client, "ana", 2)
    assert create_job(client, resolution=1024).status_code == 201
    assert credits_of(client) == 0


def test_r07_saldo_insuficiente_retorna_402(client):
    make_user(client, "ana", 1)
    response = create_job(client, resolution=1024)
    assert response.status_code == 402
    assert response.json() == {"detail": "insufficient_credits"}
    assert credits_of(client) == 1


def test_r06_usuario_inexistente_retorna_404(client):
    response = create_job(client, user_id="fantasma")
    assert response.status_code == 404
    assert response.json() == {"detail": "user_not_found"}


@pytest.mark.parametrize("prompt", ["", "   ", "x" * 501])
def test_r05_prompt_invalido(client, prompt):
    make_user(client, "ana", 10)
    assert create_job(client, prompt=prompt).status_code == 422


def test_r05_prompt_com_500_caracteres_e_aceito(client):
    make_user(client, "ana", 10)
    assert create_job(client, prompt="x" * 500).status_code == 201


def test_r05_prompt_e_aparado(client):
    make_user(client, "ana", 10)
    job = create_job(client, prompt="  gato  ").json()
    assert job["prompt"] == "gato"


def test_r05_resolucao_fora_da_lista(client):
    make_user(client, "ana", 10)
    assert create_job(client, resolution=256).status_code == 422


def test_r05_campo_extra_e_rejeitado(client):
    make_user(client, "ana", 10)
    assert create_job(client, cor="azul").status_code == 422


def test_r05_user_id_fora_do_padrao(client):
    assert create_job(client, user_id="ANA").status_code == 422
