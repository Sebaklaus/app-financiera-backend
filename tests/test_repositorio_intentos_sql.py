"""Prueba el repositorio de intentos de login contra SQLite en memoria."""

from datetime import datetime, timedelta, timezone

import pytest

from app.dominio.bloqueo import RegistroIntentos, clave_de
from app.infraestructura.base_de_datos import crear_fabrica_sesiones, crear_motor, crear_tablas
from app.infraestructura.repositorio_intentos_sql import RepositorioIntentosSQL

AHORA = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def repo():
    motor = crear_motor("sqlite+pysqlite:///:memory:")
    crear_tablas(motor)
    with crear_fabrica_sesiones(motor)() as sesion:
        yield RepositorioIntentosSQL(sesion)


def test_guardar_y_obtener(repo):
    clave = clave_de("ana@correo.cl")
    repo.guardar(RegistroIntentos(clave, 3, AHORA))
    registro = repo.obtener(clave)
    assert registro is not None
    assert registro.fallos == 3
    assert registro.bloqueado_hasta is None


def test_obtener_una_clave_desconocida_da_none(repo):
    assert repo.obtener("0" * 64) is None


def test_guardar_de_nuevo_reemplaza_el_registro(repo):
    clave = clave_de("ana@correo.cl")
    repo.guardar(RegistroIntentos(clave, 1, AHORA))
    repo.guardar(RegistroIntentos(clave, 5, AHORA, AHORA + timedelta(minutes=15)))
    registro = repo.obtener(clave)
    assert registro.fallos == 5
    assert registro.esta_bloqueado(AHORA)  # comparar horas no debe fallar


def test_borrar_elimina_el_registro_y_es_seguro_repetirlo(repo):
    clave = clave_de("ana@correo.cl")
    repo.guardar(RegistroIntentos(clave, 2, AHORA))
    repo.borrar(clave)
    repo.borrar(clave)
    assert repo.obtener(clave) is None
