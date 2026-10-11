"""Pruebas de consentimientos y perfil de riesgo, sin base de datos."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.casos_de_uso.consentimientos import (
    declarar_perfil,
    obtener_consentimientos,
    obtener_perfil,
    registrar_consentimientos,
)
from app.dominio.consentimiento import (
    VERSION_TEXTOS,
    CambioVacio,
    ConsentimientoObligatorio,
    PerfilRiesgo,
    TipoConsentimiento,
)
from tests.dobles_consentimientos import RepositorioConsentimientosEnMemoria

ANA = uuid4()
LUIS = uuid4()
AHORA = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
T = TipoConsentimiento
TODOS_LOS_OBLIGATORIOS = {T.TERMINOS_Y_PRIVACIDAD: True, T.DATOS_FINANCIEROS: True}


def test_al_inicio_faltan_los_dos_obligatorios():
    estado = obtener_consentimientos(ANA, RepositorioConsentimientosEnMemoria())
    assert estado.pendientes == [T.TERMINOS_Y_PRIVACIDAD, T.DATOS_FINANCIEROS]
    assert estado.actuales == {}


def test_otorgar_los_obligatorios_deja_sin_pendientes():
    repo = RepositorioConsentimientosEnMemoria()
    estado = registrar_consentimientos(ANA, TODOS_LOS_OBLIGATORIOS, repo, AHORA)
    assert estado.pendientes == []
    assert estado.actuales[T.DATOS_FINANCIEROS].version == VERSION_TEXTOS


def test_cada_consentimiento_se_otorga_por_separado():
    repo = RepositorioConsentimientosEnMemoria()
    estado = registrar_consentimientos(ANA, {T.TERMINOS_Y_PRIVACIDAD: True}, repo, AHORA)
    assert estado.pendientes == [T.DATOS_FINANCIEROS]


def test_repetir_lo_mismo_no_agrega_filas():
    repo = RepositorioConsentimientosEnMemoria()
    registrar_consentimientos(ANA, TODOS_LOS_OBLIGATORIOS, repo, AHORA)
    registrar_consentimientos(ANA, TODOS_LOS_OBLIGATORIOS, repo, AHORA + timedelta(hours=1))
    assert len(repo.historial) == 2


def test_retirar_un_opcional_agrega_una_fila_y_conserva_el_historial():
    repo = RepositorioConsentimientosEnMemoria()
    registrar_consentimientos(ANA, {T.COMUNICACIONES: True}, repo, AHORA)
    estado = registrar_consentimientos(
        ANA, {T.COMUNICACIONES: False}, repo, AHORA + timedelta(days=1)
    )
    assert estado.actuales[T.COMUNICACIONES].otorgado is False
    assert [r.otorgado for r in repo.historial] == [True, False]


def test_no_se_puede_retirar_un_obligatorio():
    repo = RepositorioConsentimientosEnMemoria()
    registrar_consentimientos(ANA, TODOS_LOS_OBLIGATORIOS, repo, AHORA)
    with pytest.raises(ConsentimientoObligatorio):
        registrar_consentimientos(ANA, {T.DATOS_FINANCIEROS: False}, repo, AHORA)
    assert obtener_consentimientos(ANA, repo).pendientes == []


def test_un_cambio_invalido_no_guarda_nada_de_lo_demas():
    repo = RepositorioConsentimientosEnMemoria()
    with pytest.raises(ConsentimientoObligatorio):
        registrar_consentimientos(ANA, {T.COMUNICACIONES: True, T.DATOS_FINANCIEROS: False}, repo)
    assert repo.historial == []


def test_sin_cambios_falla():
    with pytest.raises(CambioVacio):
        registrar_consentimientos(ANA, {}, RepositorioConsentimientosEnMemoria())


def test_los_consentimientos_son_de_cada_persona():
    repo = RepositorioConsentimientosEnMemoria()
    registrar_consentimientos(ANA, TODOS_LOS_OBLIGATORIOS, repo, AHORA)
    assert len(obtener_consentimientos(LUIS, repo).pendientes) == 2


def test_declarar_y_corregir_el_perfil():
    repo = RepositorioConsentimientosEnMemoria()
    assert obtener_perfil(ANA, repo) is None
    declarar_perfil(ANA, PerfilRiesgo.CONSERVADOR, repo, AHORA)
    declarar_perfil(ANA, PerfilRiesgo.MODERADO, repo, AHORA + timedelta(days=2))
    actual = obtener_perfil(ANA, repo)
    assert actual.perfil is PerfilRiesgo.MODERADO
    assert actual.actualizado_en == AHORA + timedelta(days=2)
    assert obtener_perfil(LUIS, repo) is None
