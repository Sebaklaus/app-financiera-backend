"""Prueba las rutas de confirmación del reparto con SQLite en memoria."""

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.adaptadores.api.dependencias import obtener_hasheador, obtener_repositorio_usuarios
from app.adaptadores.api.dependencias_auth import obtener_emisor_tokens
from app.adaptadores.api.dependencias_movimientos import obtener_repositorio_movimientos
from app.adaptadores.api.rutas_auth import router as router_auth
from app.adaptadores.api.rutas_confirmaciones import router as router_confirmaciones
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
    app.include_router(router_confirmaciones)
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


def propuestas(cuerpo_ingreso):
    return {c["categoria"]: c["id"] for c in cuerpo_ingreso["por_confirmar"]}


def decidir(cliente, cabecera, confirmacion_id, decision):
    return cliente.post(
        f"/confirmaciones/{confirmacion_id}/decision",
        json={"decision": decision},
        headers=cabecera,
    )


def registrar_ingreso(cliente, cabecera):
    return cliente.post("/ingresos", json=INGRESO, headers=cabecera).json()


def test_las_rutas_de_confirmacion_exigen_token(cliente):
    assert cliente.get("/confirmaciones/pendientes").status_code == 401
    respuesta = cliente.post(f"/confirmaciones/{uuid4()}/decision", json={"decision": "confirmar"})
    assert respuesta.status_code == 401


def test_pendientes_lista_las_dos_partes_del_ingreso(cliente):
    cabecera = entrar(cliente)
    registrar_ingreso(cliente, cabecera)
    respuesta = cliente.get("/confirmaciones/pendientes", headers=cabecera)
    assert respuesta.status_code == 200
    assert {c["categoria"] for c in respuesta.json()} == {"inversion", "estabilidad"}


def test_confirmar_devuelve_200_y_la_parte_pasa_a_asignada(cliente):
    cabecera = entrar(cliente)
    ids = propuestas(registrar_ingreso(cliente, cabecera))
    respuesta = decidir(cliente, cabecera, ids["inversion"], "confirmar")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "confirmada"
    assert respuesta.json()["decidido_en"] is not None
    resumen = cliente.get("/resumen", headers=cabecera).json()
    linea = {x["categoria"]: x for x in resumen["categorias"]}["inversion"]
    assert linea["asignado"] == 25_000
    assert linea["por_confirmar"] == 0


def test_rechazar_deja_el_dinero_sin_apartar(cliente):
    cabecera = entrar(cliente)
    ids = propuestas(registrar_ingreso(cliente, cabecera))
    respuesta = decidir(cliente, cabecera, ids["estabilidad"], "rechazar")
    assert respuesta.json()["estado"] == "rechazada"
    resumen = cliente.get("/resumen", headers=cabecera).json()
    linea = {x["categoria"]: x for x in resumen["categorias"]}["estabilidad"]
    assert linea["asignado"] == 0
    assert linea["rechazado"] == 15_000


def test_las_decididas_salen_de_pendientes(cliente):
    cabecera = entrar(cliente)
    ids = propuestas(registrar_ingreso(cliente, cabecera))
    decidir(cliente, cabecera, ids["inversion"], "confirmar")
    pendientes = cliente.get("/confirmaciones/pendientes", headers=cabecera).json()
    assert [c["categoria"] for c in pendientes] == ["estabilidad"]


def test_decidir_dos_veces_da_409(cliente):
    cabecera = entrar(cliente)
    ids = propuestas(registrar_ingreso(cliente, cabecera))
    decidir(cliente, cabecera, ids["inversion"], "confirmar")
    respuesta = decidir(cliente, cabecera, ids["inversion"], "rechazar")
    assert respuesta.status_code == 409


def test_decidir_una_propuesta_inexistente_da_404(cliente):
    cabecera = entrar(cliente)
    assert decidir(cliente, cabecera, uuid4(), "confirmar").status_code == 404


def test_nadie_decide_la_propuesta_de_otra_persona(cliente):
    cabecera_ana = entrar(cliente, "ana@correo.cl")
    cabecera_luis = entrar(cliente, "luis@correo.cl")
    ids = propuestas(registrar_ingreso(cliente, cabecera_ana))
    respuesta = decidir(cliente, cabecera_luis, ids["inversion"], "confirmar")
    assert respuesta.status_code == 404
    # y para Ana sigue pendiente
    pendientes = cliente.get("/confirmaciones/pendientes", headers=cabecera_ana).json()
    assert len(pendientes) == 2
    assert cliente.get("/confirmaciones/pendientes", headers=cabecera_luis).json() == []


def test_una_decision_invalida_da_422(cliente):
    cabecera = entrar(cliente)
    ids = propuestas(registrar_ingreso(cliente, cabecera))
    assert decidir(cliente, cabecera, ids["inversion"], "quizas").status_code == 422


def test_un_id_que_no_es_uuid_da_422(cliente):
    cabecera = entrar(cliente)
    assert decidir(cliente, cabecera, "no-es-uuid", "confirmar").status_code == 422
