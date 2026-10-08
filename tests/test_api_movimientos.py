"""Prueba las rutas de ingresos, gastos y resumen con SQLite en memoria."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.adaptadores.api.dependencias import obtener_hasheador, obtener_repositorio_usuarios
from app.adaptadores.api.dependencias_auth import obtener_emisor_tokens
from app.adaptadores.api.dependencias_movimientos import obtener_repositorio_movimientos
from app.adaptadores.api.rutas_auth import router as router_auth
from app.adaptadores.api.rutas_movimientos import router as router_movimientos
from app.adaptadores.api.rutas_usuarios import router as router_usuarios
from app.infraestructura.base_de_datos import crear_fabrica_sesiones, crear_tablas
from app.infraestructura.emisor_jwt import EmisorJWT
from app.infraestructura.generar_claves import generar_par
from app.infraestructura.hasheador_bcrypt import HasheadorBcrypt
from app.infraestructura.repositorio_movimientos_sql import RepositorioMovimientosSQL
from app.infraestructura.repositorio_usuarios_sql import RepositorioUsuariosSQL

PRIVADA, PUBLICA = generar_par()


@pytest.fixture
def cliente():
    motor = create_engine(
        "sqlite+pysqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    crear_tablas(motor)
    fabrica = crear_fabrica_sesiones(motor)

    def usuarios_de_prueba():
        with fabrica() as sesion:
            yield RepositorioUsuariosSQL(sesion)

    def movimientos_de_prueba():
        with fabrica() as sesion:
            yield RepositorioMovimientosSQL(sesion)

    app = FastAPI()
    app.include_router(router_usuarios)
    app.include_router(router_auth)
    app.include_router(router_movimientos)
    app.dependency_overrides[obtener_repositorio_usuarios] = usuarios_de_prueba
    app.dependency_overrides[obtener_repositorio_movimientos] = movimientos_de_prueba
    app.dependency_overrides[obtener_hasheador] = lambda: HasheadorBcrypt(costo=4)
    app.dependency_overrides[obtener_emisor_tokens] = lambda: EmisorJWT(PRIVADA, PUBLICA)
    return TestClient(app)


def entrar(cliente, email="ana@correo.cl"):
    """Registra a la persona, inicia sesión y devuelve la cabecera con su token."""
    datos = {"email": email, "contrasena": "Clave1234"}
    cliente.post("/registro", json=datos)
    token = cliente.post("/login", json=datos).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


INGRESO = {"monto": 100_000, "descripcion": "Sueldo", "fecha": "2026-10-01"}


def test_las_rutas_exigen_token(cliente):
    assert cliente.post("/ingresos", json=INGRESO).status_code == 401
    assert cliente.post("/gastos", json=INGRESO).status_code == 401
    assert cliente.get("/movimientos").status_code == 401
    assert cliente.get("/resumen").status_code == 401


def test_ingreso_devuelve_201_con_el_reparto(cliente):
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


def test_resumen_refleja_ingresos_y_gastos(cliente):
    cabecera = entrar(cliente)
    cliente.post("/ingresos", json=INGRESO, headers=cabecera)
    gasto = {"monto": 12_000, "categoria": "entretenimiento", "descripcion": "Salida"}
    cliente.post("/gastos", json=gasto, headers=cabecera)
    resumen = cliente.get("/resumen", headers=cabecera).json()
    assert resumen["ingresos_total"] == 100_000
    assert resumen["gastos_total"] == 12_000
    por_categoria = {linea["categoria"]: linea for linea in resumen["categorias"]}
    assert [linea["categoria"] for linea in resumen["categorias"]] == [
        "necesidades",
        "inversion",
        "estabilidad",
        "entretenimiento",
    ]
    assert por_categoria["entretenimiento"]["disponible"] == -2_000
    assert por_categoria["necesidades"]["disponible"] == 50_000


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
