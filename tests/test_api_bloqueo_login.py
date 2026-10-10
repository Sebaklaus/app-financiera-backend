"""Pruebas del bloqueo de login a través de POST /login con SQLite en memoria."""

import pytest

from app.dominio.bloqueo import MAX_INTENTOS
from tests.apoyo_api import crear_cliente

DATOS = {"email": "ana@correo.cl", "contrasena": "Clave1234"}


@pytest.fixture
def cliente():
    return crear_cliente()


def fallar(cliente, veces, email="ana@correo.cl"):
    codigos = []
    for _ in range(veces):
        r = cliente.post("/login", json={"email": email, "contrasena": "Equivocada99"})
        codigos.append(r.status_code)
    return codigos


def test_los_primeros_fallos_dan_401(cliente):
    cliente.post("/registro", json=DATOS)
    assert fallar(cliente, MAX_INTENTOS - 1) == [401] * (MAX_INTENTOS - 1)


def test_el_quinto_fallo_da_429_con_retry_after(cliente):
    cliente.post("/registro", json=DATOS)
    fallar(cliente, MAX_INTENTOS - 1)
    respuesta = cliente.post("/login", json={**DATOS, "contrasena": "Equivocada99"})
    assert respuesta.status_code == 429
    assert int(respuesta.headers["retry-after"]) == 900
    assert "15 minutos" in respuesta.json()["detail"]


def test_bloqueado_ni_la_clave_correcta_entra(cliente):
    cliente.post("/registro", json=DATOS)
    fallar(cliente, MAX_INTENTOS)
    assert cliente.post("/login", json=DATOS).status_code == 429


def test_un_login_correcto_reinicia_el_conteo(cliente):
    cliente.post("/registro", json=DATOS)
    fallar(cliente, MAX_INTENTOS - 1)
    assert cliente.post("/login", json=DATOS).status_code == 200
    assert fallar(cliente, MAX_INTENTOS - 1) == [401] * (MAX_INTENTOS - 1)


def test_el_bloqueo_de_una_persona_no_afecta_a_otra(cliente):
    cliente.post("/registro", json=DATOS)
    otra = {"email": "luis@correo.cl", "contrasena": "Clave1234"}
    cliente.post("/registro", json=otra)
    fallar(cliente, MAX_INTENTOS)
    assert cliente.post("/login", json=otra).status_code == 200


def test_un_email_inexistente_se_bloquea_igual_que_uno_real(cliente):
    codigos = fallar(cliente, MAX_INTENTOS, email="nadie@correo.cl")
    assert codigos == [401] * (MAX_INTENTOS - 1) + [429]
