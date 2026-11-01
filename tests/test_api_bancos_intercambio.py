"""Rutas /bancos/intencion y /bancos/intercambio."""

import pytest

from tests.apoyo_api import crear_cliente


@pytest.fixture
def cliente():
    return crear_cliente()


def entrar(cliente, email="ana@correo.cl"):
    datos = {"email": email, "contrasena": "Clave1234"}
    cliente.post("/registro", json=datos)
    token = cliente.post("/login", json=datos).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_exigen_token(cliente):
    assert cliente.post("/bancos/intencion").status_code == 401
    assert cliente.post("/bancos/intercambio", json={"exchange_token": "x"}).status_code == 401


def test_la_intencion_entrega_widget_token_y_clave_publica(cliente):
    cabecera = entrar(cliente)
    r = cliente.post("/bancos/intencion", headers=cabecera)
    assert r.status_code == 200
    assert r.json() == {"widget_token": "widget_token_prueba", "public_key": "pk_test_prueba"}
    assert "sk_" not in r.text  # la clave secreta nunca sale del servidor


def test_flujo_completo_intencion_intercambio_cuentas_e_importacion(cliente):
    cabecera = entrar(cliente)
    cliente.post("/bancos/intencion", headers=cabecera)
    r = cliente.post("/bancos/intercambio", json={"exchange_token": "exch_ok"}, headers=cabecera)
    assert r.status_code == 200
    assert r.json()[0]["numero_enmascarado"] == "····1234"
    assert "link_ok" not in r.text  # el link_token no viaja al cliente
    assert cliente.get("/bancos/cuentas", headers=cabecera).status_code == 200
    importar = cliente.post("/bancos/cuentas/acc_1/importar", headers=cabecera)
    assert importar.json()["importados"] == 1


def test_codigo_invalido_da_422_y_no_conecta(cliente):
    cabecera = entrar(cliente)
    r = cliente.post("/bancos/intercambio", json={"exchange_token": "malo"}, headers=cabecera)
    assert r.status_code == 422
    assert cliente.get("/bancos/cuentas", headers=cabecera).status_code == 409


def test_el_codigo_no_se_puede_reutilizar(cliente):
    cabecera = entrar(cliente)
    cliente.post("/bancos/intercambio", json={"exchange_token": "exch_ok"}, headers=cabecera)
    otra = entrar(cliente, "luis@correo.cl")
    r = cliente.post("/bancos/intercambio", json={"exchange_token": "exch_ok"}, headers=otra)
    assert r.status_code == 422
    assert cliente.get("/bancos/cuentas", headers=otra).status_code == 409


@pytest.mark.parametrize("cuerpo", [{}, {"exchange_token": ""}, {"exchange_token": "x" * 201}])
def test_cuerpo_invalido_da_422(cliente, cuerpo):
    cabecera = entrar(cliente)
    assert cliente.post("/bancos/intercambio", json=cuerpo, headers=cabecera).status_code == 422


def test_banco_caido_da_502(cliente):
    cabecera = entrar(cliente)
    cliente.banco.caido = True
    assert cliente.post("/bancos/intencion", headers=cabecera).status_code == 502
    r = cliente.post("/bancos/intercambio", json={"exchange_token": "exch_ok"}, headers=cabecera)
    assert r.status_code == 502
