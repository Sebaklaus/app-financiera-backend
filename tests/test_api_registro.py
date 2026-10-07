"""Prueba la ruta POST /registro con una base SQLite en memoria (no toca tu PostgreSQL)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.adaptadores.api.dependencias import obtener_hasheador, obtener_repositorio_usuarios
from app.adaptadores.api.rutas_usuarios import router
from app.infraestructura.base_de_datos import crear_fabrica_sesiones, crear_tablas
from app.infraestructura.hasheador_bcrypt import HasheadorBcrypt
from app.infraestructura.repositorio_usuarios_sql import RepositorioUsuariosSQL


@pytest.fixture
def cliente():
    # StaticPool: una sola conexión compartida, porque TestClient corre en otro hilo.
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
    app.include_router(router)
    app.dependency_overrides[obtener_repositorio_usuarios] = repositorio_de_prueba
    app.dependency_overrides[obtener_hasheador] = lambda: HasheadorBcrypt(costo=4)
    return TestClient(app)


DATOS_OK = {"email": "Ana@Correo.cl", "contrasena": "Clave1234"}


def test_registro_exitoso_devuelve_201_sin_datos_secretos(cliente):
    respuesta = cliente.post("/registro", json=DATOS_OK)
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["email"] == "ana@correo.cl"
    assert "id" in cuerpo and "creado_en" in cuerpo
    assert "contrasena" not in cuerpo
    assert "hash_contrasena" not in cuerpo
    assert "Clave1234" not in respuesta.text


def test_email_repetido_devuelve_409(cliente):
    cliente.post("/registro", json=DATOS_OK)
    respuesta = cliente.post("/registro", json={**DATOS_OK, "email": "ANA@correo.cl"})
    assert respuesta.status_code == 409


def test_contrasena_debil_devuelve_422(cliente):
    respuesta = cliente.post("/registro", json={**DATOS_OK, "contrasena": "corta"})
    assert respuesta.status_code == 422
    assert "contraseña" in respuesta.json()["detail"]


def test_email_invalido_devuelve_422(cliente):
    respuesta = cliente.post("/registro", json={**DATOS_OK, "email": "no-es-un-email"})
    assert respuesta.status_code == 422


def test_faltan_campos_devuelve_422(cliente):
    assert cliente.post("/registro", json={"email": "ana@correo.cl"}).status_code == 422
