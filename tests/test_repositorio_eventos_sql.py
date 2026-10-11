"""Prueba la bitácora contra SQLite en memoria, incluida la anonimización al borrar la cuenta."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.dominio.auditoria import EventoSeguridad, TipoEvento
from app.dominio.usuario import Usuario
from app.infraestructura.base_de_datos import crear_fabrica_sesiones, crear_motor, crear_tablas
from app.infraestructura.repositorio_cuenta_sql import RepositorioCuentaSQL
from app.infraestructura.repositorio_eventos_sql import (
    EventoSeguridadTabla,
    RepositorioEventosSQL,
)

AHORA = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
ANA = Usuario(id=uuid4(), email="ana@correo.cl", hash_contrasena="h", creado_en=AHORA)


def evento(tipo, usuario_id=None, minutos=0):
    return EventoSeguridad(uuid4(), tipo, usuario_id, "huella", AHORA + timedelta(minutes=minutos))


@pytest.fixture
def sesion():
    motor = crear_motor("sqlite+pysqlite:///:memory:")
    crear_tablas(motor)
    with crear_fabrica_sesiones(motor)() as sesion:
        RepositorioCuentaSQL(sesion).guardar(ANA)
        yield sesion


def test_guardar_y_listar_con_zona_y_orden(sesion):
    repo = RepositorioEventosSQL(sesion)
    repo.guardar(evento(TipoEvento.LOGIN_EXITOSO, ANA.id, 0))
    repo.guardar(evento(TipoEvento.EMAIL_CAMBIADO, ANA.id, 5))
    repo.guardar(evento(TipoEvento.LOGIN_FALLIDO, None, 9))
    lista = repo.listar_por_usuario(ANA.id, 10)
    assert [e.tipo for e in lista] == [TipoEvento.EMAIL_CAMBIADO, TipoEvento.LOGIN_EXITOSO]
    assert lista[0].creado_en.tzinfo is not None
    assert len(repo.listar_por_usuario(ANA.id, 1)) == 1


def test_eliminar_la_cuenta_conserva_los_eventos_sin_vinculo(sesion):
    repo = RepositorioEventosSQL(sesion)
    repo.guardar(evento(TipoEvento.LOGIN_EXITOSO, ANA.id))
    RepositorioCuentaSQL(sesion).eliminar_cuenta(ANA.id, "clave")
    assert repo.listar_por_usuario(ANA.id, 10) == []
    # El evento sigue en la base, pero ya sin dueño.
    assert sesion.scalar(select(func.count()).select_from(EventoSeguridadTabla)) == 1
    assert sesion.scalar(select(EventoSeguridadTabla.usuario_id)) is None
