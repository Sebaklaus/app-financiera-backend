"""Pruebas de /yo/datos, /yo/contrasena, /yo/email y /yo/eliminar con SQLite en memoria."""

import pytest

from tests.apoyo_api import crear_cliente

CLAVE = "Clave1234"
INGRESO = {"monto": 100_000, "descripcion": "Sueldo", "fecha": "2026-10-01"}


@pytest.fixture
def cliente():
    return crear_cliente()


def entrar(cliente, email="ana@correo.cl", clave=CLAVE):
    datos = {"email": email, "contrasena": clave}
    cliente.post("/registro", json=datos)
    sesion = cliente.post("/login", json=datos).json()
    return {"Authorization": f"Bearer {sesion['access_token']}"}, sesion["refresh_token"]


def test_las_rutas_exigen_token(cliente):
    assert cliente.get("/yo/datos").status_code == 401
    assert cliente.post("/yo/eliminar", json={"contrasena": CLAVE}).status_code == 401
    assert cliente.patch("/yo/email", json={}).status_code == 401
    assert cliente.post("/yo/contrasena", json={}).status_code == 401


def test_datos_incluye_movimientos_y_propuestas(cliente):
    cabecera, _ = entrar(cliente)
    cliente.post("/ingresos", json=INGRESO, headers=cabecera)
    cuerpo = cliente.get("/yo/datos", headers=cabecera).json()
    assert cuerpo["email"] == "ana@correo.cl"
    assert cuerpo["creado_en"].endswith("Z")
    assert cuerpo["exportado_en"].endswith("Z")
    assert len(cuerpo["movimientos"]) == 1
    assert len(cuerpo["confirmaciones"]) == 2
    assert "hash" not in str(cuerpo).lower()


def test_datos_no_incluye_lo_de_otra_persona(cliente):
    ana, _ = entrar(cliente)
    luis, _ = entrar(cliente, "luis@correo.cl")
    cliente.post("/ingresos", json=INGRESO, headers=ana)
    assert cliente.get("/yo/datos", headers=luis).json()["movimientos"] == []


def test_cambiar_contrasena_cierra_las_sesiones_y_sirve_la_nueva(cliente):
    cabecera, refresco = entrar(cliente)
    r = cliente.post(
        "/yo/contrasena",
        json={"contrasena_actual": CLAVE, "contrasena_nueva": "Nueva56789"},
        headers=cabecera,
    )
    assert r.status_code == 204
    assert cliente.post("/refrescar", json={"refresh_token": refresco}).status_code == 401
    viejo = {"email": "ana@correo.cl", "contrasena": CLAVE}
    nuevo = {"email": "ana@correo.cl", "contrasena": "Nueva56789"}
    assert cliente.post("/login", json=viejo).status_code == 401
    assert cliente.post("/login", json=nuevo).status_code == 200


def test_cambiar_contrasena_con_la_actual_mala_da_403_y_no_401(cliente):
    cabecera, _ = entrar(cliente)
    r = cliente.post(
        "/yo/contrasena",
        json={"contrasena_actual": "mala", "contrasena_nueva": "Nueva56789"},
        headers=cabecera,
    )
    assert r.status_code == 403


def test_cambiar_contrasena_debil_da_422(cliente):
    cabecera, _ = entrar(cliente)
    r = cliente.post(
        "/yo/contrasena",
        json={"contrasena_actual": CLAVE, "contrasena_nueva": "corta"},
        headers=cabecera,
    )
    assert r.status_code == 422


def test_cambiar_email_y_entrar_con_el_nuevo(cliente):
    cabecera, _ = entrar(cliente)
    r = cliente.patch(
        "/yo/email", json={"contrasena": CLAVE, "email_nuevo": "NUEVO@correo.cl"}, headers=cabecera
    )
    assert r.status_code == 200
    assert r.json() == {"email": "nuevo@correo.cl"}
    entrada = {"email": "nuevo@correo.cl", "contrasena": CLAVE}
    assert cliente.post("/login", json=entrada).status_code == 200


def test_cambiar_email_a_uno_ocupado_da_409(cliente):
    cabecera, _ = entrar(cliente)
    entrar(cliente, "luis@correo.cl")
    r = cliente.patch(
        "/yo/email", json={"contrasena": CLAVE, "email_nuevo": "luis@correo.cl"}, headers=cabecera
    )
    assert r.status_code == 409


def test_cambiar_email_invalido_da_422(cliente):
    cabecera, _ = entrar(cliente)
    r = cliente.patch(
        "/yo/email", json={"contrasena": CLAVE, "email_nuevo": "no-es-email"}, headers=cabecera
    )
    assert r.status_code == 422


def test_eliminar_con_contrasena_mala_da_403_y_no_borra(cliente):
    cabecera, _ = entrar(cliente)
    r = cliente.post("/yo/eliminar", json={"contrasena": "mala"}, headers=cabecera)
    assert r.status_code == 403
    assert cliente.get("/yo/datos", headers=cabecera).status_code == 200


def test_eliminar_cuenta_borra_todo(cliente):
    cabecera, refresco = entrar(cliente)
    cliente.post("/ingresos", json=INGRESO, headers=cabecera)
    r = cliente.post("/yo/eliminar", json={"contrasena": CLAVE}, headers=cabecera)
    assert r.status_code == 204
    assert cliente.post("/refrescar", json={"refresh_token": refresco}).status_code == 401
    datos = {"email": "ana@correo.cl", "contrasena": CLAVE}
    assert cliente.post("/login", json=datos).status_code == 401
    # El token de acceso aún no vence, pero la cuenta ya no existe.
    assert cliente.get("/yo/datos", headers=cabecera).status_code == 401
    # El email queda libre para registrarse de nuevo.
    assert cliente.post("/registro", json=datos).status_code == 201


def test_eliminar_no_toca_a_las_otras_personas(cliente):
    ana, _ = entrar(cliente)
    luis, _ = entrar(cliente, "luis@correo.cl")
    cliente.post("/ingresos", json=INGRESO, headers=luis)
    cliente.post("/yo/eliminar", json={"contrasena": CLAVE}, headers=ana)
    assert len(cliente.get("/yo/datos", headers=luis).json()["movimientos"]) == 1


def test_equivocarse_cinco_veces_da_429(cliente):
    cabecera, _ = entrar(cliente)
    codigos = [
        cliente.post("/yo/eliminar", json={"contrasena": "mala"}, headers=cabecera).status_code
        for _ in range(5)
    ]
    assert codigos[-1] == 429
    r = cliente.post("/yo/eliminar", json={"contrasena": CLAVE}, headers=cabecera)
    assert r.status_code == 429
    assert "retry-after" in r.headers
