"""Prueba POST /login y GET /yo con SQLite en memoria y claves RSA temporales."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.adaptadores.api.dependencias import obtener_hasheador, obtener_repositorio_usuarios
from app.adaptadores.api.dependencias_auth import obtener_emisor_tokens
from app.adaptadores.api.rutas_auth import router as router_auth
from app.adaptadores.api.rutas_usuarios import router as router_usuarios
from app.infraestructura.base_de_datos import crear_fabrica_sesiones, crear_tablas
from app.infraestructura.emisor_jwt import EmisorJWT
from app.infraestructura.generar_claves import generar_par
from app.infraestructura.hasheador_bcrypt import HasheadorBcrypt
from app.infraestructura.repositorio_usuarios_sql import RepositorioUsuariosSQL

PRIVADA, PUBLICA = generar_par()
DATOS_OK = {"email": "ana@correo.cl", "contrasena": "Clave1234"}


@pytest.fixture
def cliente():
    motor = create_engine(
        "sqlite+pysqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    crear_tablas(motor)
    fabrica = crear_fabrica_sesiones(motor)

    def repositorio_de_prueba():
        with fabrica() as sesion:
            yield RepositorioUsuariosSQL(sesion)

    app = FastAPI()
    app.include_router(router_usuarios)
    app.include_router(router_auth)
    app.dependency_overrides[obtener_repositorio_usuarios] = repositorio_de_prueba
    app.dependency_overrides[obtener_hasheador] = lambda: HasheadorBcrypt(costo=4)
    app.dependency_overrides[obtener_emisor_tokens] = lambda: EmisorJWT(PRIVADA, PUBLICA)
    return TestClient(app)


def registrar_a_ana(cliente):
    return cliente.post("/registro", json=DATOS_OK).json()["id"]


def test_login_correcto_devuelve_token(cliente):
    registrar_a_ana(cliente)
    respuesta = cliente.post("/login", json=DATOS_OK)
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["token_type"] == "bearer"
    assert cuerpo["expires_in"] == 900
    assert cuerpo["access_token"]
    assert "Clave1234" not in respuesta.text


def test_login_acepta_email_con_mayusculas(cliente):
    registrar_a_ana(cliente)
    respuesta = cliente.post("/login", json={**DATOS_OK, "email": "  ANA@correo.cl "})
    assert respuesta.status_code == 200


def test_login_con_contrasena_incorrecta_da_401(cliente):
    registrar_a_ana(cliente)
    respuesta = cliente.post("/login", json={**DATOS_OK, "contrasena": "OtraClave99"})
    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"


def test_login_con_email_inexistente_da_el_mismo_401(cliente):
    registrar_a_ana(cliente)
    mala_clave = cliente.post("/login", json={**DATOS_OK, "contrasena": "OtraClave99"})
    sin_cuenta = cliente.post("/login", json={**DATOS_OK, "email": "nadie@correo.cl"})
    assert sin_cuenta.status_code == 401
    assert sin_cuenta.json() == mala_clave.json()


def test_login_sin_campos_da_422(cliente):
    assert cliente.post("/login", json={"email": "ana@correo.cl"}).status_code == 422


def test_ruta_protegida_con_token_valido_devuelve_el_id(cliente):
    id_ana = registrar_a_ana(cliente)
    token = cliente.post("/login", json=DATOS_OK).json()["access_token"]
    respuesta = cliente.get("/yo", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 200
    assert respuesta.json() == {"id": id_ana}


def test_ruta_protegida_sin_token_da_401(cliente):
    assert cliente.get("/yo").status_code == 401


def test_ruta_protegida_con_token_falso_da_401(cliente):
    respuesta = cliente.get("/yo", headers={"Authorization": "Bearer esto.no.sirve"})
    assert respuesta.status_code == 401
