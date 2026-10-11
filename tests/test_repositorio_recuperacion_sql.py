"""Prueba el repositorio de tokens de recuperación contra SQLite en memoria."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.dominio.recuperacion import nuevo_token_recuperacion
from app.dominio.usuario import Usuario
from app.infraestructura.base_de_datos import crear_fabrica_sesiones, crear_motor, crear_tablas
from app.infraestructura.repositorio_recuperacion_sql import RepositorioRecuperacionSQL
from app.infraestructura.repositorio_usuarios_sql import RepositorioUsuariosSQL

AHORA = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
ANA = Usuario(id=uuid4(), email="ana@correo.cl", hash_contrasena="h", creado_en=AHORA)


@pytest.fixture
def repo():
    motor = crear_motor("sqlite+pysqlite:///:memory:")
    crear_tablas(motor)
    with crear_fabrica_sesiones(motor)() as sesion:
        RepositorioUsuariosSQL(sesion).guardar(ANA)
        yield RepositorioRecuperacionSQL(sesion)


def test_guardar_y_buscar_por_huella_con_zona(repo):
    _, registro = nuevo_token_recuperacion(ANA.id, AHORA)
    repo.guardar(registro)
    encontrado = repo.buscar_por_huella(registro.huella)
    assert encontrado.id == registro.id
    assert encontrado.expira_en.tzinfo is not None
    assert encontrado.esta_vigente(AHORA)  # comparar no debe fallar
    assert repo.buscar_por_huella("0" * 64) is None


def test_marcar_usado_funciona_una_sola_vez(repo):
    _, registro = nuevo_token_recuperacion(ANA.id, AHORA)
    repo.guardar(registro)
    assert repo.marcar_usado(registro.id, AHORA) is True
    assert repo.marcar_usado(registro.id, AHORA) is False
    assert repo.buscar_por_huella(registro.huella).usado_en is not None


def test_ultimo_creado_en(repo):
    assert repo.ultimo_creado_en(ANA.id) is None
    _, uno = nuevo_token_recuperacion(ANA.id, AHORA)
    _, dos = nuevo_token_recuperacion(ANA.id, AHORA + timedelta(minutes=5))
    repo.guardar(uno)
    repo.guardar(dos)
    assert repo.ultimo_creado_en(ANA.id) == AHORA + timedelta(minutes=5)


def test_invalidar_pendientes_deja_sin_uso_los_anteriores(repo):
    _, uno = nuevo_token_recuperacion(ANA.id, AHORA)
    repo.guardar(uno)
    repo.invalidar_pendientes(ANA.id, AHORA)
    assert repo.buscar_por_huella(uno.huella).esta_vigente(AHORA) is False
