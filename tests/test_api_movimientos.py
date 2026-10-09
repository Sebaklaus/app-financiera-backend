"""Prueba las rutas de ingresos, gastos y resumen con SQLite en memoria."""

import pytest

from tests.apoyo_api import crear_cliente


@pytest.fixture
def cliente():
    return crear_cliente()


def entrar(cliente, email="ana@correo.cl"):
    """Registra a la persona, inicia sesión y devuelve la cabecera con su token."""
    datos = {"email": email, "contrasena": "Clave1234"}
    cliente.post("/registro", json=datos)
    token = cliente.post("/login", json=datos).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


INGRESO = {"monto": 100_000, "descripcion": "Sueldo", "fecha": "2026-10-01"}


def lineas(cliente, cabecera):
    resumen = cliente.get("/resumen", headers=cabecera).json()
    return {linea["categoria"]: linea for linea in resumen["categorias"]}


def test_las_rutas_exigen_token(cliente):
    assert cliente.post("/ingresos", json=INGRESO).status_code == 401
    assert cliente.post("/gastos", json=INGRESO).status_code == 401
    assert cliente.get("/movimientos").status_code == 401
    assert cliente.get("/resumen").status_code == 401


def test_ingreso_devuelve_201_con_la_propuesta_de_reparto(cliente):
    cabecera = entrar(cliente)
    respuesta = cliente.post("/ingresos", json=INGRESO, headers=cabecera)
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["monto"] == 100_000
    assert cuerpo["reparto"] == {
        "necesidades": 50_000,
        "inversion": 25_000,
        "estabilidad": 15_000,
        "entretenimiento": 10_000,
    }
    pendientes = {c["categoria"]: c for c in cuerpo["por_confirmar"]}
    assert set(pendientes) == {"inversion", "estabilidad"}
    assert pendientes["inversion"]["monto"] == 25_000
    assert pendientes["inversion"]["estado"] == "pendiente"


def test_ingreso_sin_fecha_usa_hoy(cliente):
    cabecera = entrar(cliente)
    datos = {"monto": 5_000, "descripcion": "Venta"}
    assert cliente.post("/ingresos", json=datos, headers=cabecera).status_code == 201


def test_ingreso_con_fecha_futura_da_422(cliente):
    cabecera = entrar(cliente)
    datos = {**INGRESO, "fecha": "2999-01-01"}
    respuesta = cliente.post("/ingresos", json=datos, headers=cabecera)
    assert respuesta.status_code == 422
    assert "futuro" in respuesta.json()["detail"]


@pytest.mark.parametrize("monto", [0, -5, "1000", 10.5])
def test_ingreso_con_monto_invalido_da_422(cliente, monto):
    cabecera = entrar(cliente)
    respuesta = cliente.post("/ingresos", json={**INGRESO, "monto": monto}, headers=cabecera)
    assert respuesta.status_code == 422


def test_gasto_devuelve_201(cliente):
    cabecera = entrar(cliente)
    datos = {"monto": 8_000, "categoria": "entretenimiento", "descripcion": "Cine"}
    respuesta = cliente.post("/gastos", json=datos, headers=cabecera)
    assert respuesta.status_code == 201
    assert respuesta.json()["categoria"] == "entretenimiento"


def test_gasto_con_categoria_inexistente_da_422(cliente):
    cabecera = entrar(cliente)
    datos = {"monto": 8_000, "categoria": "viajes", "descripcion": "Cine"}
    assert cliente.post("/gastos", json=datos, headers=cabecera).status_code == 422


def test_resumen_antes_de_confirmar_deja_inversion_y_estabilidad_por_confirmar(cliente):
    cabecera = entrar(cliente)
    cliente.post("/ingresos", json=INGRESO, headers=cabecera)
    gasto = {"monto": 12_000, "categoria": "entretenimiento", "descripcion": "Salida"}
    cliente.post("/gastos", json=gasto, headers=cabecera)
    resumen = cliente.get("/resumen", headers=cabecera).json()
    assert resumen["ingresos_total"] == 100_000
    assert resumen["gastos_total"] == 12_000
    assert [linea["categoria"] for linea in resumen["categorias"]] == [
        "necesidades",
        "inversion",
        "estabilidad",
        "entretenimiento",
    ]
    por_categoria = lineas(cliente, cabecera)
    assert por_categoria["entretenimiento"]["disponible"] == -2_000
    assert por_categoria["necesidades"]["disponible"] == 50_000
    assert por_categoria["inversion"]["asignado"] == 0
    assert por_categoria["inversion"]["por_confirmar"] == 25_000
    assert por_categoria["estabilidad"]["por_confirmar"] == 15_000


def test_movimientos_lista_el_mas_reciente_primero(cliente):
    cabecera = entrar(cliente)
    cliente.post("/ingresos", json={**INGRESO, "fecha": "2026-09-01"}, headers=cabecera)
    cliente.post("/ingresos", json={**INGRESO, "fecha": "2026-10-05"}, headers=cabecera)
    fechas = [m["fecha"] for m in cliente.get("/movimientos", headers=cabecera).json()]
    assert fechas == ["2026-10-05", "2026-09-01"]


def test_una_persona_no_ve_los_movimientos_de_otra(cliente):
    cabecera_ana = entrar(cliente, "ana@correo.cl")
    cabecera_luis = entrar(cliente, "luis@correo.cl")
    cliente.post("/ingresos", json=INGRESO, headers=cabecera_ana)
    assert cliente.get("/movimientos", headers=cabecera_luis).json() == []
    resumen_luis = cliente.get("/resumen", headers=cabecera_luis).json()
    assert resumen_luis["ingresos_total"] == 0
    assert len(cliente.get("/movimientos", headers=cabecera_ana).json()) == 1
