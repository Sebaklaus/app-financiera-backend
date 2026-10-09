"""Prueba el repositorio de tokens de refresco contra SQLite en memoria."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.dominio.token_refresco import nuevo_token_refresco
from app.infraestructura.base_de_datos import crear_fabrica_sesiones, crear_motor, crear_tablas
from app.infraestructura.repositorio_tokens_sql import RepositorioTokensSQL

ANA = uuid4()
LUIS = uuid4()
AHORA = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def repo():
    motor = crear_motor("sqlite+pysqlite:///:memory:")
    crear_tablas(motor)
    with crear_fabrica_sesiones(motor)() as sesion:
        yield RepositorioTokensSQL(sesion)


def test_guardar_y_buscar_por_huella(repo):
    _, registro = nuevo_token_refresco(ANA, AHORA)
    repo.guardar(registro)
    encontrado = repo.buscar_por_huella(registro.huella)
    assert encontrado is not None
    assert encontrado.id == registro.id
    assert encontrado.usuario_id == ANA
    assert encontrado.revocado_en is None


def test_las_horas_vuelven_con_zona_horaria(repo):
    _, registro = nuevo_token_refresco(ANA, AHORA)
    repo.guardar(registro)
    encontrado = repo.buscar_por_huella(registro.huella)
    assert encontrado.expira_en.tzinfo is not None
    assert encontrado.esta_vigente(AHORA)  # comparar no debe fallar


def test_buscar_una_huella_desconocida_devuelve_none(repo):
    assert repo.buscar_por_huella("0" * 64) is None


def test_revocar_funciona_una_sola_vez(repo):
    _, registro = nuevo_token_refresco(ANA, AHORA)
    repo.guardar(registro)
    assert repo.revocar(registro.id, AHORA) is True
    assert repo.revocar(registro.id, AHORA) is False
    assert repo.buscar_por_huella(registro.huella).revocado_en is not None


def test_revocar_todos_solo_afecta_a_ese_usuario(repo):
    _, a1 = nuevo_token_refresco(ANA, AHORA)
    _, a2 = nuevo_token_refresco(ANA, AHORA)
    _, l1 = nuevo_token_refresco(LUIS, AHORA)
    for registro in (a1, a2, l1):
        repo.guardar(registro)
    repo.revocar_todos_de_usuario(ANA, AHORA)
    assert repo.buscar_por_huella(a1.huella).revocado_en is not None
    assert repo.buscar_por_huella(a2.huella).revocado_en is not None
    assert repo.buscar_por_huella(l1.huella).revocado_en is None
