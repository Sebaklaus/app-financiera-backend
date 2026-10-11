"""Pruebas de /recuperacion/solicitar y /recuperacion/restablecer con SQLite en memoria."""

import pytest

from tests.apoyo_api import crear_cliente

DATOS = {"email": "ana@correo.cl", "contrasena": "Clave1234"}


@pytest.fixture
def cliente():
    c = crear_cliente()
    c.post("/registro", json=DATOS)
    return c


def solicitar(cliente, email="ana@correo.cl"):
    return cliente.post("/recuperacion/solicitar", json={"email": email})


def restablecer(cliente, token, nueva="Nueva56789"):
    cuerpo = {"token": token, "contrasena_nueva": nueva}
    return cliente.post("/recuperacion/restablecer", json=cuerpo)


def test_solicitar_responde_igual_exista_o_no_la_cuenta(cliente):
    con_cuenta = solicitar(cliente)
    sin_cuenta = solicitar(cliente, "nadie@correo.cl")
    assert con_cuenta.status_code == sin_cuenta.status_code == 202
    assert con_cuenta.json() == sin_cuenta.json()
    assert len(cliente.espia.enviados) == 1


def test_solicitar_con_un_email_raro_tambien_da_202(cliente):
    assert solicitar(cliente, "esto no es un email").status_code == 202


def test_recorrido_completo(cliente):
    sesion = cliente.post("/login", json=DATOS).json()
    solicitar(cliente)
    _, token = cliente.espia.enviados[-1]
    assert restablecer(cliente, token).status_code == 204
    # La sesión anterior se cerró, la clave vieja ya no sirve y la nueva sí.
    viejo = {"refresh_token": sesion["refresh_token"]}
    assert cliente.post("/refrescar", json=viejo).status_code == 401
    assert cliente.post("/login", json=DATOS).status_code == 401
    nuevo = {"email": "ana@correo.cl", "contrasena": "Nueva56789"}
    assert cliente.post("/login", json=nuevo).status_code == 200


def test_restablecer_quita_el_bloqueo_del_login(cliente):
    for _ in range(5):
        cliente.post("/login", json={"email": "ana@correo.cl", "contrasena": "mala"})
    assert cliente.post("/login", json=DATOS).status_code == 429
    solicitar(cliente)
    restablecer(cliente, cliente.espia.enviados[-1][1])
    nuevo = {"email": "ana@correo.cl", "contrasena": "Nueva56789"}
    assert cliente.post("/login", json=nuevo).status_code == 200


def test_el_token_no_se_puede_reusar(cliente):
    solicitar(cliente)
    token = cliente.espia.enviados[-1][1]
    assert restablecer(cliente, token).status_code == 204
    assert restablecer(cliente, token, "Otra987654").status_code == 400


def test_token_falso_da_400(cliente):
    assert restablecer(cliente, "falso").status_code == 400


def test_clave_debil_da_422_y_el_token_sigue_sirviendo(cliente):
    solicitar(cliente)
    token = cliente.espia.enviados[-1][1]
    assert restablecer(cliente, token, "corta").status_code == 422
    assert restablecer(cliente, token, "Buena56789").status_code == 204


def test_borrar_la_cuenta_borra_tambien_sus_tokens_de_recuperacion(cliente):
    sesion = cliente.post("/login", json=DATOS).json()
    cabecera = {"Authorization": f"Bearer {sesion['access_token']}"}
    solicitar(cliente)
    token = cliente.espia.enviados[-1][1]
    borrado = cliente.post("/yo/eliminar", json={"contrasena": "Clave1234"}, headers=cabecera)
    assert borrado.status_code == 204
    assert restablecer(cliente, token).status_code == 400
