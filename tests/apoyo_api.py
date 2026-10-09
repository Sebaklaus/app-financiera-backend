"""Apoyo para las pruebas de rutas: arma una app de prueba con base SQLite en memoria.

Todas las pruebas de rutas usan esta misma pieza, así que cuando se agrega una ruta o una
dependencia nueva, se cambia aquí una sola vez.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.adaptadores.api.dependencias import obtener_hasheador, obtener_repositorio_usuarios
from app.adaptadores.api.dependencias_auth import obtener_emisor_tokens, obtener_repositorio_tokens
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
from app.infraestructura.repositorio_tokens_sql import RepositorioTokensSQL
from app.infraestructura.repositorio_usuarios_sql import RepositorioUsuariosSQL

PRIVADA, PUBLICA = generar_par()


def crear_cliente() -> TestClient:
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

    def tokens_de_prueba():
        with fabrica() as sesion:
            yield RepositorioTokensSQL(sesion)

    app = FastAPI()
    for router in (router_usuarios, router_auth, router_movimientos, router_confirmaciones):
        app.include_router(router)
    app.dependency_overrides[obtener_repositorio_usuarios] = usuarios_de_prueba
    app.dependency_overrides[obtener_repositorio_movimientos] = movimientos_de_prueba
    app.dependency_overrides[obtener_repositorio_tokens] = tokens_de_prueba
    app.dependency_overrides[obtener_hasheador] = lambda: HasheadorBcrypt(costo=4)
    app.dependency_overrides[obtener_emisor_tokens] = lambda: EmisorJWT(PRIVADA, PUBLICA)
    return TestClient(app)
