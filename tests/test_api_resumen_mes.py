"""Pruebas de ?mes=AAAA-MM en /resumen y /movimientos."""

import pytest

from tests.apoyo_api import crear_cliente

DATOS = {"email": "ana@correo.cl", "contrasena": "Clave1234"}


@pytest.fixture
def cliente():
    return crear_cliente()


def entrar(cliente, email="ana@correo.cl"):
    datos = {**DATOS, "email": email}
    cliente.post("/registro", json=datos)
    token = cliente.post("/login", json=datos).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def ingreso(cliente, cabecera, monto, fecha):
    datos = {"monto": monto, "descripcion": "Sueldo", "fecha": fecha}
    return cliente.post("/ingresos", json=datos, headers=cabecera).json()


def preparar(cliente):
    cabecera = entrar(cliente)
    ingreso(cliente, cabecera, 100_000, "2026-09-05")
    ingreso(cliente, cabecera, 200_000, "2026-10-05")
    gasto = {
        "monto": 9_000,
        "categoria": "necesidades",
        "descripcion": "Super",
        "fecha": "2026-10-06",
    }
    cliente.post("/gastos", json=gasto, headers=cabecera)
    return cabecera


def test_resumen_sin_mes_suma_todo_y_no_indica_mes(cliente):
    cabecera = preparar(cliente)
    cuerpo = cliente.get("/resumen", headers=cabecera).json()
    assert cuerpo["mes"] is None
    assert cuerpo["ingresos_total"] == 300_000


def test_resumen_de_un_mes_solo_cuenta_ese_mes(cliente):
    cabecera = preparar(cliente)
    cuerpo = cliente.get("/resumen?mes=2026-10", headers=cabecera).json()
    assert cuerpo["mes"] == "2026-10"
    assert cuerpo["ingresos_total"] == 200_000
    assert cuerpo["gastos_total"] == 9_000
    septiembre = cliente.get("/resumen?mes=2026-09", headers=cabecera).json()
    assert septiembre["ingresos_total"] == 100_000
    assert septiembre["gastos_total"] == 0


def test_resumen_de_un_mes_sin_datos_da_ceros(cliente):
    cabecera = preparar(cliente)
    cuerpo = cliente.get("/resumen?mes=2026-01", headers=cabecera).json()
    assert cuerpo["ingresos_total"] == 0
    assert all(linea["asignado"] == 0 for linea in cuerpo["categorias"])


def test_movimientos_filtra_por_mes(cliente):
    cabecera = preparar(cliente)
    todos = cliente.get("/movimientos", headers=cabecera).json()
    octubre = cliente.get("/movimientos?mes=2026-10", headers=cabecera).json()
    assert len(todos) == 3
    assert {m["fecha"] for m in octubre} == {"2026-10-05", "2026-10-06"}


@pytest.mark.parametrize("mes", ["2026-13", "2026-00", "octubre", "2026-1", "26-10", ""])
def test_un_mes_mal_escrito_da_422(cliente, mes):
    cabecera = preparar(cliente)
    assert cliente.get(f"/resumen?mes={mes}", headers=cabecera).status_code == 422
    assert cliente.get(f"/movimientos?mes={mes}", headers=cabecera).status_code == 422


def test_el_mes_tambien_exige_token(cliente):
    assert cliente.get("/resumen?mes=2026-10").status_code == 401
