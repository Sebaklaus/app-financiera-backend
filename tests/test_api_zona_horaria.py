"""Las horas que entrega la API siempre vienen en UTC (terminan en Z)."""

import pytest

from tests.apoyo_api import crear_cliente

DATOS = {"email": "ana@correo.cl", "contrasena": "Clave1234"}


@pytest.fixture
def cliente():
    return crear_cliente()


def entrar(cliente):
    cliente.post("/registro", json=DATOS)
    token = cliente.post("/login", json=DATOS).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_creado_en_y_decidido_en_usan_el_mismo_formato_utc(cliente):
    cabecera = entrar(cliente)
    ingreso = cliente.post(
        "/ingresos", json={"monto": 100_000, "descripcion": "Sueldo"}, headers=cabecera
    )
    propuesta = ingreso.json()["por_confirmar"][0]
    assert propuesta["creado_en"].endswith("Z")
    decision = cliente.post(
        f"/confirmaciones/{propuesta['id']}/decision",
        json={"decision": "confirmar"},
        headers=cabecera,
    ).json()
    assert decision["creado_en"].endswith("Z")
    assert decision["decidido_en"].endswith("Z")


def test_las_pendientes_tambien_vienen_en_utc(cliente):
    cabecera = entrar(cliente)
    cliente.post("/ingresos", json={"monto": 100_000, "descripcion": "Sueldo"}, headers=cabecera)
    pendientes = cliente.get("/confirmaciones/pendientes", headers=cabecera).json()
    assert all(p["creado_en"].endswith("Z") for p in pendientes)
