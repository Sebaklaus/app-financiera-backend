"""Prueba el repositorio de movimientos contra SQLite en memoria."""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.dominio.categorias import Categoria
from app.dominio.movimiento import Movimiento, TipoMovimiento
from app.infraestructura.base_de_datos import crear_fabrica_sesiones, crear_motor, crear_tablas
from app.infraestructura.repositorio_movimientos_sql import RepositorioMovimientosSQL

ANA = uuid4()
LUIS = uuid4()


@pytest.fixture
def repo():
    motor = crear_motor("sqlite+pysqlite:///:memory:")
    crear_tablas(motor)
    with crear_fabrica_sesiones(motor)() as sesion:
        yield RepositorioMovimientosSQL(sesion)


def un_movimiento(usuario=ANA, tipo=TipoMovimiento.INGRESO, monto=1_000, fecha=date(2026, 10, 1)):
    return Movimiento(
        id=uuid4(),
        usuario_id=usuario,
        tipo=tipo,
        monto=monto,
        categoria=None if tipo is TipoMovimiento.INGRESO else Categoria.INVERSION,
        descripcion="Prueba",
        fecha=fecha,
        creado_en=datetime.now(timezone.utc),
    )


def test_guardar_y_listar_devuelve_lo_mismo(repo):
    ingreso = un_movimiento()
    gasto = un_movimiento(tipo=TipoMovimiento.GASTO, fecha=date(2026, 10, 2))
    repo.guardar(ingreso)
    repo.guardar(gasto)
    por_id = {m.id: m for m in repo.listar_por_usuario(ANA)}
    assert por_id[ingreso.id].categoria is None
    assert por_id[ingreso.id].tipo is TipoMovimiento.INGRESO
    assert por_id[gasto.id].categoria is Categoria.INVERSION
    assert por_id[gasto.id].monto == 1_000


def test_lista_primero_el_mas_reciente(repo):
    viejo = un_movimiento(fecha=date(2026, 9, 1))
    nuevo = un_movimiento(fecha=date(2026, 10, 5))
    repo.guardar(viejo)
    repo.guardar(nuevo)
    assert [m.id for m in repo.listar_por_usuario(ANA)] == [nuevo.id, viejo.id]


def test_cada_usuario_ve_solo_lo_suyo(repo):
    repo.guardar(un_movimiento(usuario=ANA))
    repo.guardar(un_movimiento(usuario=LUIS))
    assert len(repo.listar_por_usuario(ANA)) == 1
    assert repo.listar_por_usuario(uuid4()) == []


def test_la_base_rechaza_un_monto_cero(repo):
    with pytest.raises(IntegrityError):
        repo.guardar(un_movimiento(monto=0))
