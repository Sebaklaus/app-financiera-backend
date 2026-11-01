"""Opciones de inversión y derivación a la entidad socia (sin base de datos)."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.casos_de_uso.inversion import derivar_a_entidad_socia, listar_opciones
from app.dominio.auditoria import TipoEvento
from app.dominio.consentimiento import PerfilDeclarado, PerfilRiesgo
from app.dominio.errores import MovimientoInvalido
from app.dominio.inversion import (
    CATALOGO,
    InstrumentoNoEncontrado,
    Riesgo,
    buscar_instrumento,
    es_recomendado,
)
from tests.dobles_auditoria import RepositorioEventosEnMemoria
from tests.dobles_consentimientos import RepositorioConsentimientosEnMemoria

ANA = uuid4()
AHORA = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


def con_perfil(perfil):
    repo = RepositorioConsentimientosEnMemoria()
    if perfil is not None:
        repo.guardar_perfil(PerfilDeclarado(ANA, perfil, AHORA))
    return repo


def test_el_catalogo_tiene_ids_unicos_y_los_tres_niveles_de_riesgo():
    ids = [i.id for i in CATALOGO]
    assert len(ids) == len(set(ids))
    assert {i.riesgo for i in CATALOGO} == {Riesgo.BAJO, Riesgo.MEDIO, Riesgo.ALTO}


def test_las_entidades_son_simuladas_y_no_apuntan_a_sitios_reales():
    for instrumento in CATALOGO:
        assert "simulad" in instrumento.entidad.nombre.lower()
        assert instrumento.entidad.url_simulada.split("/")[2].endswith(".invalid")


@pytest.mark.parametrize(
    ("perfil", "recomendados"),
    [
        (PerfilRiesgo.CONSERVADOR, {Riesgo.BAJO}),
        (PerfilRiesgo.MODERADO, {Riesgo.BAJO, Riesgo.MEDIO}),
        (PerfilRiesgo.ARRIESGADO, {Riesgo.BAJO, Riesgo.MEDIO, Riesgo.ALTO}),
    ],
)
def test_cada_perfil_ve_recomendado_solo_lo_que_acepta(perfil, recomendados):
    for instrumento in CATALOGO:
        assert es_recomendado(instrumento, perfil) is (instrumento.riesgo in recomendados)


def test_sin_perfil_nada_es_recomendado():
    assert not any(es_recomendado(i, None) for i in CATALOGO)


def test_las_opciones_muestran_primero_lo_recomendado():
    resultado = listar_opciones(ANA, con_perfil(PerfilRiesgo.CONSERVADOR))
    assert resultado.perfil is PerfilRiesgo.CONSERVADOR
    marcas = [o.recomendado for o in resultado.opciones]
    assert marcas == sorted(marcas, reverse=True)
    assert len(resultado.opciones) == len(CATALOGO)
    assert not resultado.opciones[-1].recomendado


def test_sin_perfil_igual_se_ven_todas_las_opciones():
    resultado = listar_opciones(ANA, con_perfil(None))
    assert resultado.perfil is None
    assert len(resultado.opciones) == len(CATALOGO)


def test_derivar_anota_el_evento_en_la_bitacora_y_no_mueve_dinero():
    eventos = RepositorioEventosEnMemoria()
    d = derivar_a_entidad_socia(ANA, "deposito-a-plazo", 250_000, eventos, "203.0.113.7", AHORA)
    assert d.instrumento.id == "deposito-a-plazo"
    assert d.entidad.id == "banco-socio"
    assert d.monto == 250_000
    (evento,) = eventos.eventos
    assert evento.tipo is TipoEvento.DERIVACION_INVERSION
    assert evento.usuario_id == ANA


def test_el_monto_es_opcional():
    eventos = RepositorioEventosEnMemoria()
    assert derivar_a_entidad_socia(ANA, "cuenta-ahorro", None, eventos).monto is None


@pytest.mark.parametrize("monto", [0, -1, 1.5, True, 1_000_000_001])
def test_un_monto_invalido_no_registra_nada(monto):
    eventos = RepositorioEventosEnMemoria()
    with pytest.raises(MovimientoInvalido):
        derivar_a_entidad_socia(ANA, "cuenta-ahorro", monto, eventos)
    assert eventos.eventos == []


def test_un_instrumento_inexistente_no_registra_nada():
    eventos = RepositorioEventosEnMemoria()
    with pytest.raises(InstrumentoNoEncontrado):
        derivar_a_entidad_socia(ANA, "bitcoin", None, eventos)
    with pytest.raises(InstrumentoNoEncontrado):
        buscar_instrumento("")
    assert eventos.eventos == []
