"""Apoyo para las pruebas de rutas: arma una app de prueba con base SQLite en memoria.

Todas las pruebas de rutas usan esta misma pieza, así que cuando se agrega una ruta o una
dependencia nueva, se cambia aquí una sola vez.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.adaptadores.api.dependencias import obtener_hasheador, obtener_repositorio_usuarios
from app.adaptadores.api.dependencias_auth import (
    obtener_emisor_tokens,
    obtener_repositorio_intentos,
    obtener_repositorio_tokens,
)
from app.adaptadores.api.dependencias_consentimientos import obtener_repositorio_consentimientos
from app.adaptadores.api.dependencias_cuenta import obtener_repositorio_cuenta
from app.adaptadores.api.dependencias_movimientos import obtener_repositorio_movimientos
from app.adaptadores.api.dependencias_recuperacion import (
    obtener_enviador_correo,
    obtener_repositorio_recuperacion,
)
from app.adaptadores.api.rutas_auth import router as router_auth
from app.adaptadores.api.rutas_confirmaciones import router as router_confirmaciones
from app.adaptadores.api.rutas_consentimientos import router as router_consentimientos
from app.adaptadores.api.rutas_cuenta import router as router_cuenta
from app.adaptadores.api.rutas_movimientos import router as router_movimientos
from app.adaptadores.api.rutas_recuperacion import router as router_recuperacion
from app.adaptadores.api.rutas_usuarios import router as router_usuarios
from app.infraestructura.base_de_datos import crear_fabrica_sesiones, crear_tablas
from app.infraestructura.emisor_jwt import EmisorJWT
from app.infraestructura.generar_claves import generar_par
from app.infraestructura.hasheador_bcrypt import HasheadorBcrypt
from app.infraestructura.repositorio_consentimientos_sql import RepositorioConsentimientosSQL
from app.infraestructura.repositorio_cuenta_sql import RepositorioCuentaSQL
from app.infraestructura.repositorio_intentos_sql import RepositorioIntentosSQL
from app.infraestructura.repositorio_movimientos_sql import RepositorioMovimientosSQL
from app.infraestructura.repositorio_recuperacion_sql import RepositorioRecuperacionSQL
from app.infraestructura.repositorio_tokens_sql import RepositorioTokensSQL
from app.infraestructura.repositorio_usuarios_sql import RepositorioUsuariosSQL

PRIVADA, PUBLICA = generar_par()


class EnviadorEspia:
    """Guarda los correos que se 'enviarían', para que las pruebas lean el token."""

    def __init__(self) -> None:
        self.enviados: list[tuple[str, str]] = []

    def enviar_recuperacion(self, email: str, token: str) -> None:
        self.enviados.append((email, token))


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

    def consentimientos_de_prueba():
        with fabrica() as sesion:
            yield RepositorioConsentimientosSQL(sesion)

    def recuperacion_de_prueba():
        with fabrica() as sesion:
            yield RepositorioRecuperacionSQL(sesion)

    def cuenta_de_prueba():
        with fabrica() as sesion:
            yield RepositorioCuentaSQL(sesion)

    def intentos_de_prueba():
        with fabrica() as sesion:
            yield RepositorioIntentosSQL(sesion)

    espia = EnviadorEspia()
    app = FastAPI()
    for router in (
        router_usuarios,
        router_auth,
        router_movimientos,
        router_confirmaciones,
        router_cuenta,
        router_consentimientos,
        router_recuperacion,
    ):
        app.include_router(router)
    app.dependency_overrides[obtener_repositorio_usuarios] = usuarios_de_prueba
    app.dependency_overrides[obtener_repositorio_movimientos] = movimientos_de_prueba
    app.dependency_overrides[obtener_repositorio_tokens] = tokens_de_prueba
    app.dependency_overrides[obtener_repositorio_intentos] = intentos_de_prueba
    app.dependency_overrides[obtener_repositorio_cuenta] = cuenta_de_prueba
    app.dependency_overrides[obtener_repositorio_recuperacion] = recuperacion_de_prueba
    app.dependency_overrides[obtener_enviador_correo] = lambda: espia
    app.dependency_overrides[obtener_repositorio_consentimientos] = consentimientos_de_prueba
    app.dependency_overrides[obtener_hasheador] = lambda: HasheadorBcrypt(costo=4)
    app.dependency_overrides[obtener_emisor_tokens] = lambda: EmisorJWT(PRIVADA, PUBLICA)
    cliente = TestClient(app)
    cliente.espia = espia  # las pruebas leen aquí el token que 'llegó por correo'
    return cliente
