"""Prueba editar y borrar contra SQLite en memoria ."""

from dataclasses import replace
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from app.dominio.categorias import Categoria
from app.dominio.confirmacion import Confirmacion, Decision, EstadoConfirmacion, decidir
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


def un_ingreso(usuario=ANA):
    return Movimiento(
        id=uuid4(),
        usuario_id=usuario,
        tipo=TipoMovimiento.INGRESO,
        monto=1_000,
        categoria=None,
        descripcion="Sueldo",
        fecha=date(2026, 10, 1),
        creado_en=datetime.now(timezone.utc),
    )


def un_gasto(usuario=ANA):
    return replace(un_ingreso(usuario), tipo=TipoMovimiento.GASTO, categoria=Categoria.NECESIDADES)


def propuesta(ingreso, categoria=Categoria.INVERSION, monto=250):
    return Confirmacion(
        id=uuid4(),
        usuario_id=ingreso.usuario_id,
        ingreso_id=ingreso.id,
        categoria=categoria,
        monto=monto,
        estado=EstadoConfirmacion.PENDIENTE,
        creado_en=datetime.now(timezone.utc),
    )


def test_buscar_movimiento_respeta_al_dueno(repo):
    gasto = un_gasto()
    repo.guardar(gasto)
    encontrado = repo.buscar_movimiento(ANA, gasto.id)
    assert encontrado is not None
    # creado_en no se compara: SQLite guarda la hora sin zona horaria (PostgreSQL sí la guarda).
    assert (encontrado.id, encontrado.monto, encontrado.descripcion) == (
        gasto.id,
        gasto.monto,
        gasto.descripcion,
    )
    assert repo.buscar_movimiento(LUIS, gasto.id) is None
    assert repo.buscar_movimiento(ANA, uuid4()) is None


def test_actualizar_un_gasto_guarda_los_cambios(repo):
    gasto = un_gasto()
    repo.guardar(gasto)
    cambiado = replace(gasto, monto=2_500, categoria=Categoria.ENTRETENIMIENTO, descripcion="Cine")
    repo.actualizar_movimiento(cambiado)
    guardado = repo.buscar_movimiento(ANA, gasto.id)
    assert guardado.monto == 2_500
    assert guardado.categoria is Categoria.ENTRETENIMIENTO
    assert guardado.descripcion == "Cine"


def test_actualizar_no_toca_el_movimiento_de_otra_persona(repo):
    gasto = un_gasto(usuario=ANA)
    repo.guardar(gasto)
    repo.actualizar_movimiento(replace(gasto, usuario_id=LUIS, monto=1))
    assert repo.buscar_movimiento(ANA, gasto.id).monto == 1_000


def test_actualizar_un_ingreso_reemplaza_solo_las_propuestas_pendientes(repo):
    ingreso = un_ingreso()
    inversion = propuesta(ingreso, Categoria.INVERSION, 250)
    estabilidad = propuesta(ingreso, Categoria.ESTABILIDAD, 150)
    repo.guardar_ingreso(ingreso, [inversion, estabilidad])
    repo.actualizar_confirmacion(decidir(inversion, Decision.CONFIRMAR, datetime.now(timezone.utc)))

    nuevas = [propuesta(replace(ingreso, monto=2_000), Categoria.ESTABILIDAD, 300)]
    repo.actualizar_movimiento(replace(ingreso, monto=2_000), nuevas)

    guardadas = {c.id: c for c in repo.listar_confirmaciones_por_usuario(ANA)}
    assert inversion.id in guardadas  # la ya decidida jamás se toca
    assert guardadas[inversion.id].estado is EstadoConfirmacion.CONFIRMADA
    assert estabilidad.id not in guardadas  # la pendiente vieja se reemplazó
    assert nuevas[0].id in guardadas


def test_eliminar_un_gasto(repo):
    gasto = un_gasto()
    repo.guardar(gasto)
    assert repo.eliminar_movimiento(ANA, gasto.id) is True
    assert repo.listar_por_usuario(ANA) == []


def test_eliminar_un_ingreso_borra_antes_sus_propuestas(repo):
    ingreso = un_ingreso()
    repo.guardar_ingreso(ingreso, [propuesta(ingreso)])
    assert repo.eliminar_movimiento(ANA, ingreso.id) is True
    assert repo.listar_por_usuario(ANA) == []
    assert repo.listar_confirmaciones_por_usuario(ANA) == []


def test_eliminar_lo_ajeno_o_inexistente_devuelve_false(repo):
    gasto = un_gasto(usuario=ANA)
    repo.guardar(gasto)
    assert repo.eliminar_movimiento(LUIS, gasto.id) is False
    assert repo.eliminar_movimiento(ANA, uuid4()) is False
    assert len(repo.listar_por_usuario(ANA)) == 1