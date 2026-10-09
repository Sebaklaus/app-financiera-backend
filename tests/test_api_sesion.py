"""Pruebas de /refrescar, /logout y /logout/todas con SQLite en memoria."""

import pytest

from tests.apoyo_api import crear_cliente

DATOS = {"email": "ana@correo.cl", "contrasena": "Clave1234"}


@pytest.fixture
def cliente():
    return crear_cliente()


def iniciar(cliente, datos=DATOS):
    cliente.post("/registro", json=datos)
    return cliente.post("/login", json=datos).json()


def refrescar(cliente, token):
    return cliente.post("/refrescar", json={"refresh_token": token})


def test_login_entrega_tambien_el_token_de_refresco(cliente):
    sesion = iniciar(cliente)
    assert sesion["refresh_token"]
    assert sesion["refresh_token"] != sesion["access_token"]


def test_refrescar_entrega_un_par_nuevo_que_funciona(cliente):
    sesion = iniciar(cliente)
    respuesta = refrescar(cliente, sesion["refresh_token"])
    assert respuesta.status_code == 200
    nuevo = respuesta.json()
    assert nuevo["refresh_token"] != sesion["refresh_token"]
    cabecera = {"Authorization": f"Bearer {nuevo['access_token']}"}
    assert cliente.get("/yo", headers=cabecera).status_code == 200


def test_el_refresco_ya_usado_da_401(cliente):
    sesion = iniciar(cliente)
    refrescar(cliente, sesion["refresh_token"])
    assert refrescar(cliente, sesion["refresh_token"]).status_code == 401


def test_reusar_un_refresco_cierra_tambien_el_nuevo(cliente):
    sesion = iniciar(cliente)
    nuevo = refrescar(cliente, sesion["refresh_token"]).json()
    refrescar(cliente, sesion["refresh_token"])  # alguien reusa el viejo
    assert refrescar(cliente, nuevo["refresh_token"]).status_code == 401


def test_un_refresco_inventado_da_401(cliente):
    respuesta = refrescar(cliente, "esto-no-existe")
    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"


def test_refrescar_sin_el_campo_da_422(cliente):
    assert cliente.post("/refrescar", json={}).status_code == 422


def test_logout_da_204_y_el_refresco_deja_de_servir(cliente):
    sesion = iniciar(cliente)
    respuesta = cliente.post("/logout", json={"refresh_token": sesion["refresh_token"]})
    assert respuesta.status_code == 204
    assert refrescar(cliente, sesion["refresh_token"]).status_code == 401


def test_logout_con_un_token_desconocido_tambien_da_204(cliente):
    assert cliente.post("/logout", json={"refresh_token": "inventado"}).status_code == 204


def test_logout_todas_exige_token_de_acceso(cliente):
    assert cliente.post("/logout/todas").status_code == 401


def test_logout_todas_cierra_todos_los_dispositivos(cliente):
    telefono = iniciar(cliente)
    notebook = cliente.post("/login", json=DATOS).json()
    cabecera = {"Authorization": f"Bearer {telefono['access_token']}"}
    assert cliente.post("/logout/todas", headers=cabecera).status_code == 204
    assert refrescar(cliente, telefono["refresh_token"]).status_code == 401
    assert refrescar(cliente, notebook["refresh_token"]).status_code == 401


def test_cerrar_las_sesiones_de_una_persona_no_afecta_a_otra(cliente):
    ana = iniciar(cliente)
    luis = iniciar(cliente, {"email": "luis@correo.cl", "contrasena": "Clave1234"})
    cabecera = {"Authorization": f"Bearer {ana['access_token']}"}
    cliente.post("/logout/todas", headers=cabecera)
    assert refrescar(cliente, luis["refresh_token"]).status_code == 200
