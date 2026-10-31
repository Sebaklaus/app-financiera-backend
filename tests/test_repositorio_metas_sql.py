"""Prueba el repositorio de metas de ahorro contra SQLite en memoria."""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.dominio.meta import Aporte, MetaAhorro
from app.infraestructura.base_de_datos import crear_fabrica_sesiones, crear_motor, crear_tablas
from app.infraestructura.repositorio_metas_sql import RepositorioMetasSQL

ANA = uuid4()
LUIS = uuid4()


@pytest.fixture
def repo():
    motor = crear_motor("sqlite+pysqlite:///:memory:")
    crear_tablas(motor)
    with crear_fabrica_sesiones(motor)() as sesion:
        # SQLite no exige las claves foráneas por defecto: aquí solo probamos las metas.
        yield RepositorioMetasSQL(sesion)


def una_meta(usuario=ANA, nombre="Viaje", objetivo=500_000, hora=0):
    return MetaAhorro(
        id=uuid4(),
        usuario_id=usuario,
        nombre=nombre,
        monto_objetivo=objetivo,
        fecha_limite=date(2026, 12, 31),
        creada_en=datetime(2026, 10, 28, hora, 0, tzinfo=timezone.utc),
    )


def un_aporte(meta, monto=10_000, usuario=ANA, dia=1):
    return Aporte(
        id=uuid4(),
        meta_id=meta.id,
        usuario_id=usuario,
        monto=monto,
        fecha=date(2026, 10, dia),
        creado_en=datetime(2026, 10, dia, 12, 0, tzinfo=timezone.utc),
    )


def test_guarda_y_recupera_una_meta(repo):
    meta = una_meta()
    repo.guardar_meta(meta)
    recuperada = repo.buscar_meta(ANA, meta.id)
    assert recuperada is not None
    assert (recuperada.nombre, recuperada.monto_objetivo) == ("Viaje", 500_000)
    assert recuperada.fecha_limite == date(2026, 12, 31)


def test_buscar_la_meta_de_otra_persona_da_none(repo):
    meta = una_meta()
    repo.guardar_meta(meta)
    assert repo.buscar_meta(LUIS, meta.id) is None


def test_listar_devuelve_solo_las_propias_la_mas_reciente_primero(repo):
    vieja = una_meta(nombre="Vieja", hora=1)
    nueva = una_meta(nombre="Nueva", hora=5)
    repo.guardar_meta(vieja)
    repo.guardar_meta(nueva)
    repo.guardar_meta(una_meta(usuario=LUIS, nombre="Ajena"))
    assert [m.nombre for m in repo.listar_metas(ANA)] == ["Nueva", "Vieja"]


def test_aportes_y_totales(repo):
    viaje = una_meta()
    auto = una_meta(nombre="Auto")
    repo.guardar_meta(viaje)
    repo.guardar_meta(auto)
    repo.guardar_aporte(un_aporte(viaje, 10_000, dia=1))
    repo.guardar_aporte(un_aporte(viaje, 25_000, dia=3))
    repo.guardar_aporte(un_aporte(auto, 5_000, dia=2))
    assert repo.total_aportado(ANA) == {viaje.id: 35_000, auto.id: 5_000}
    assert [a.monto for a in repo.listar_aportes(ANA, viaje.id)] == [25_000, 10_000]
    assert repo.total_aportado(LUIS) == {}


def test_eliminar_borra_la_meta_y_sus_aportes(repo):
    meta = una_meta()
    repo.guardar_meta(meta)
    repo.guardar_aporte(un_aporte(meta))
    assert repo.eliminar_meta(LUIS, meta.id) is False
    assert repo.eliminar_meta(ANA, meta.id) is True
    assert repo.buscar_meta(ANA, meta.id) is None
    assert repo.total_aportado(ANA) == {}
    assert repo.eliminar_meta(ANA, meta.id) is False


def test_la_base_rechaza_montos_de_cero(repo):
    with pytest.raises(IntegrityError):
        repo.guardar_meta(una_meta(objetivo=0))
    meta = una_meta()
    repo.guardar_meta(meta)
    with pytest.raises(IntegrityError):
        repo.guardar_aporte(un_aporte(meta, monto=0))
