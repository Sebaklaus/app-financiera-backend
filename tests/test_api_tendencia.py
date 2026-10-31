"""Pruebas de GET /tendencia."""

from datetime import date

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


def test_exige_token(cliente):
    assert cliente.get("/tendencia").status_code == 401


def test_por_defecto_devuelve_seis_meses_terminando_en_el_actual(cliente):
    cabecera = entrar(cliente)
    meses = cliente.get("/tendencia", headers=cabecera).json()
    assert len(meses) == 6
    hoy = date.today()
    assert meses[-1]["mes"] == f"{hoy.year:04d}-{hoy.month:02d}"
    assert all(m["ingresos"] == 0 and m["gastos"] == 0 for m in meses)


def test_refleja_los_movimientos_del_mes_actual(cliente):
    cabecera = entrar(cliente)
    hoy = date.today().isoformat()
    cliente.post(
        "/ingresos",
        json={"monto": 100_000, "descripcion": "Sueldo", "fecha": hoy},
        headers=cabecera,
    )
    cliente.post(
        "/gastos",
        json={"monto": 20_000, "categoria": "necesidades", "descripcion": "Super", "fecha": hoy},
        headers=cabecera,
    )
    actual = cliente.get("/tendencia?meses=3", headers=cabecera).json()[-1]
    assert (actual["ingresos"], actual["gastos"], actual["balance"]) == (100_000, 20_000, 80_000)
    assert actual["gastos_por_categoria"]["necesidades"] == 20_000
    assert actual["gastos_por_categoria"]["inversion"] == 0


@pytest.mark.parametrize("meses", ["0", "13", "abc", "-2"])
def test_cantidad_invalida_da_422(cliente, meses):
    cabecera = entrar(cliente)
    assert cliente.get(f"/tendencia?meses={meses}", headers=cabecera).status_code == 422


def test_no_mezcla_datos_de_otra_persona(cliente):
    ana = entrar(cliente, "ana@correo.cl")
    luis = entrar(cliente, "luis@correo.cl")
    hoy = date.today().isoformat()
    cliente.post(
        "/ingresos", json={"monto": 50_000, "descripcion": "Sueldo", "fecha": hoy}, headers=ana
    )
    assert cliente.get("/tendencia", headers=luis).json()[-1]["ingresos"] == 0
