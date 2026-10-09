"""Prueba el repositorio de movimientos y confirmaciones contra SQLite en memoria."""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.dominio.categorias import Categoria
from app.dominio.confirmacion import (
    Confirmacion,
    Decision,
    EstadoConfirmacion,
    decidir,
)
from app.dominio.errores import ConfirmacionYaDecidida
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


def una_confirmacion(ingreso, categoria=Categoria.INVERSION, monto=250):
    return Confirmacion(
        id=uuid4(),
        usuario_id=ingreso.usuario_id,
        ingreso_id=ingreso.id,
        categoria=categoria,
        monto=monto,
        estado=EstadoConfirmacion.PENDIENTE,
        creado_en=datetime.now(timezone.utc),
    )


# --- movimientos ------------------------------------------------------------------------


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


# --- confirmaciones ---------------------------------------------------------------------


def test_guardar_ingreso_guarda_tambien_sus_propuestas(repo):
    ingreso = un_movimiento(monto=1_000)
    propuestas = [
        una_confirmacion(ingreso, Categoria.INVERSION, 250),
        una_confirmacion(ingreso, Categoria.ESTABILIDAD, 150),
    ]
    repo.guardar_ingreso(ingreso, propuestas)
    assert len(repo.listar_por_usuario(ANA)) == 1
    guardadas = {c.id: c for c in repo.listar_confirmaciones_por_usuario(ANA)}
    assert set(guardadas) == {p.id for p in propuestas}
    assert guardadas[propuestas[0].id].categoria is Categoria.INVERSION
    assert guardadas[propuestas[0].id].estado is EstadoConfirmacion.PENDIENTE
    assert guardadas[propuestas[0].id].decidido_en is None


def test_si_una_propuesta_falla_no_se_guarda_ni_el_ingreso(repo):
    ingreso = un_movimiento()
    mala = una_confirmacion(ingreso, monto=0)  # la base rechaza montos no positivos
    with pytest.raises(IntegrityError):
        repo.guardar_ingreso(ingreso, [mala])
    assert repo.listar_por_usuario(ANA) == []
    assert repo.listar_confirmaciones_por_usuario(ANA) == []


def test_buscar_confirmacion_respeta_al_dueno(repo):
    ingreso = un_movimiento()
    propuesta = una_confirmacion(ingreso)
    repo.guardar_ingreso(ingreso, [propuesta])
    assert repo.buscar_confirmacion(ANA, propuesta.id) is not None
    assert repo.buscar_confirmacion(LUIS, propuesta.id) is None
    assert repo.buscar_confirmacion(ANA, uuid4()) is None


def test_actualizar_guarda_la_decision(repo):
    ingreso = un_movimiento()
    propuesta = una_confirmacion(ingreso)
    repo.guardar_ingreso(ingreso, [propuesta])
    decidida = decidir(propuesta, Decision.CONFIRMAR, datetime.now(timezone.utc))
    repo.actualizar_confirmacion(decidida)
    guardada = repo.buscar_confirmacion(ANA, propuesta.id)
    assert guardada is not None
    assert guardada.estado is EstadoConfirmacion.CONFIRMADA
    assert guardada.decidido_en is not None


def test_la_base_impide_decidir_dos_veces(repo):
    ingreso = un_movimiento()
    propuesta = una_confirmacion(ingreso)
    repo.guardar_ingreso(ingreso, [propuesta])
    ahora = datetime.now(timezone.utc)
    repo.actualizar_confirmacion(decidir(propuesta, Decision.CONFIRMAR, ahora))
    # Simula una segunda petición que todavía veía la propuesta como pendiente.
    with pytest.raises(ConfirmacionYaDecidida):
        repo.actualizar_confirmacion(decidir(propuesta, Decision.RECHAZAR, ahora))
    guardada = repo.buscar_confirmacion(ANA, propuesta.id)
    assert guardada is not None
    assert guardada.estado is EstadoConfirmacion.CONFIRMADA
