"""Prueba el repositorio de consentimientos contra SQLite en memoria."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.dominio.consentimiento import (
    Consentimiento,
    PerfilDeclarado,
    PerfilRiesgo,
    TipoConsentimiento,
)
from app.dominio.usuario import Usuario
from app.infraestructura.base_de_datos import crear_fabrica_sesiones, crear_motor, crear_tablas
from app.infraestructura.repositorio_consentimientos_sql import RepositorioConsentimientosSQL
from app.infraestructura.repositorio_usuarios_sql import RepositorioUsuariosSQL

AHORA = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
ANA = Usuario(id=uuid4(), email="ana@correo.cl", hash_contrasena="h", creado_en=AHORA)
LUIS = Usuario(id=uuid4(), email="luis@correo.cl", hash_contrasena="h", creado_en=AHORA)


@pytest.fixture
def repo():
    motor = crear_motor("sqlite+pysqlite:///:memory:")
    crear_tablas(motor)
    with crear_fabrica_sesiones(motor)() as sesion:
        usuarios = RepositorioUsuariosSQL(sesion)
        usuarios.guardar(ANA)
        usuarios.guardar(LUIS)
        yield RepositorioConsentimientosSQL(sesion)


def registro(usuario, tipo, otorgado, minutos=0):
    return Consentimiento(
        uuid4(), usuario.id, tipo, otorgado, "2026-10", AHORA + timedelta(minutes=minutos)
    )


def test_guardar_y_listar_en_orden_con_zona(repo):
    T = TipoConsentimiento
    repo.guardar_consentimientos(
        [registro(ANA, T.COMUNICACIONES, False, 5), registro(ANA, T.COMUNICACIONES, True, 1)]
    )
    historial = repo.listar_consentimientos(ANA.id)
    assert [r.otorgado for r in historial] == [True, False]
    assert historial[0].creado_en.tzinfo is not None
    assert historial[0].tipo is T.COMUNICACIONES


def test_cada_persona_ve_solo_lo_suyo(repo):
    repo.guardar_consentimientos([registro(ANA, TipoConsentimiento.DATOS_FINANCIEROS, True)])
    assert repo.listar_consentimientos(LUIS.id) == []


def test_perfil_se_crea_y_se_reemplaza(repo):
    assert repo.obtener_perfil(ANA.id) is None
    repo.guardar_perfil(PerfilDeclarado(ANA.id, PerfilRiesgo.CONSERVADOR, AHORA))
    repo.guardar_perfil(PerfilDeclarado(ANA.id, PerfilRiesgo.ARRIESGADO, AHORA))
    actual = repo.obtener_perfil(ANA.id)
    assert actual.perfil is PerfilRiesgo.ARRIESGADO
    assert actual.actualizado_en.tzinfo is not None
