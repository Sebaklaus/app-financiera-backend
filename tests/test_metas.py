"""Prueba las reglas y los casos de uso de las metas de ahorro (sin base de datos)."""

from datetime import date
from uuid import uuid4

import pytest

from app.casos_de_uso.metas import (
    aportar_a_meta,
    crear_meta,
    eliminar_meta,
    listar_metas,
    obtener_meta,
)
from app.dominio.errores import MetaInvalida, MetaNoEncontrada
from app.dominio.meta import MetaAhorro, calcular_progreso, validar_monto
from tests.dobles_metas import RepositorioMetasEnMemoria

ANA = uuid4()
LUIS = uuid4()
HOY = date(2026, 10, 28)


@pytest.fixture
def repo():
    return RepositorioMetasEnMemoria()


def una_meta(repo, usuario=ANA, nombre="Viaje", objetivo=500_000, limite=None):
    return crear_meta(usuario, nombre, objetivo, limite, repo, hoy=HOY)


# ---- reglas del dominio ----


def test_progreso_a_medias():
    meta = MetaAhorro(uuid4(), ANA, "Viaje", 500_000, None, None)
    progreso = calcular_progreso(meta, 125_000)
    assert (progreso.ahorrado, progreso.falta, progreso.porcentaje) == (125_000, 375_000, 25)
    assert progreso.cumplida is False


def test_progreso_redondea_hacia_abajo():
    meta = MetaAhorro(uuid4(), ANA, "Viaje", 300, None, None)
    assert calcular_progreso(meta, 100).porcentaje == 33


def test_progreso_cumplido_y_pasado_se_detiene_en_100():
    meta = MetaAhorro(uuid4(), ANA, "Viaje", 1_000, None, None)
    exacto = calcular_progreso(meta, 1_000)
    pasado = calcular_progreso(meta, 1_500)
    assert exacto.cumplida and exacto.falta == 0 and exacto.porcentaje == 100
    assert pasado.cumplida and pasado.falta == 0 and pasado.porcentaje == 100


@pytest.mark.parametrize("monto", [0, -5, 1.5, "100", True, None, 1_000_000_001])
def test_monto_invalido(monto):
    with pytest.raises(MetaInvalida):
        validar_monto(monto)


# ---- casos de uso ----


def test_crear_meta_empieza_en_cero(repo):
    progreso = una_meta(repo)
    assert progreso.ahorrado == 0
    assert progreso.porcentaje == 0
    assert progreso.falta == 500_000
    assert progreso.meta.nombre == "Viaje"


def test_el_nombre_se_limpia_y_no_puede_estar_vacio(repo):
    assert una_meta(repo, nombre="  Viaje  ").meta.nombre == "Viaje"
    with pytest.raises(MetaInvalida):
        una_meta(repo, nombre="   ")
    with pytest.raises(MetaInvalida):
        una_meta(repo, nombre="x" * 81)


def test_la_fecha_limite_no_puede_estar_en_el_pasado(repo):
    with pytest.raises(MetaInvalida):
        una_meta(repo, limite=date(2026, 10, 27))
    assert una_meta(repo, limite=HOY).meta.fecha_limite == HOY


def test_aportar_suma_y_actualiza_el_avance(repo):
    meta = una_meta(repo).meta
    aportar_a_meta(ANA, meta.id, 100_000, HOY, repo, hoy=HOY)
    detalle = aportar_a_meta(ANA, meta.id, 150_000, None, repo, hoy=HOY)
    assert detalle.progreso.ahorrado == 250_000
    assert detalle.progreso.porcentaje == 50
    assert len(detalle.aportes) == 2


def test_un_aporte_no_puede_ser_del_futuro(repo):
    meta = una_meta(repo).meta
    with pytest.raises(MetaInvalida):
        aportar_a_meta(ANA, meta.id, 1_000, date(2026, 10, 29), repo, hoy=HOY)


def test_aportar_con_monto_invalido(repo):
    meta = una_meta(repo).meta
    with pytest.raises(MetaInvalida):
        aportar_a_meta(ANA, meta.id, 0, None, repo, hoy=HOY)


def test_no_se_puede_aportar_a_la_meta_de_otra_persona(repo):
    meta = una_meta(repo).meta
    with pytest.raises(MetaNoEncontrada):
        aportar_a_meta(LUIS, meta.id, 1_000, None, repo, hoy=HOY)
    assert repo.aportes == []


def test_listar_muestra_solo_las_propias_con_su_avance(repo):
    viaje = una_meta(repo).meta
    una_meta(repo, usuario=LUIS, nombre="Ajena")
    aportar_a_meta(ANA, viaje.id, 50_000, None, repo, hoy=HOY)
    metas = listar_metas(ANA, repo)
    assert [p.meta.nombre for p in metas] == ["Viaje"]
    assert metas[0].ahorrado == 50_000
    assert metas[0].porcentaje == 10


def test_obtener_una_meta_ajena_o_inexistente(repo):
    meta = una_meta(repo).meta
    with pytest.raises(MetaNoEncontrada):
        obtener_meta(LUIS, meta.id, repo)
    with pytest.raises(MetaNoEncontrada):
        obtener_meta(ANA, uuid4(), repo)


def test_eliminar_borra_la_meta_y_sus_aportes(repo):
    meta = una_meta(repo).meta
    aportar_a_meta(ANA, meta.id, 10_000, None, repo, hoy=HOY)
    eliminar_meta(ANA, meta.id, repo)
    assert listar_metas(ANA, repo) == []
    assert repo.aportes == []


def test_no_se_puede_eliminar_la_meta_de_otra_persona(repo):
    meta = una_meta(repo).meta
    with pytest.raises(MetaNoEncontrada):
        eliminar_meta(LUIS, meta.id, repo)
    assert len(listar_metas(ANA, repo)) == 1
