"""Pruebas de la sesión: abrirla, renovarla con rotación y cerrarla (sin base de datos)."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.casos_de_uso.sesiones import (
    abrir_sesion,
    cerrar_sesion,
    cerrar_todas_las_sesiones,
    renovar_sesion,
)
from app.dominio.errores import TokenInvalido
from app.dominio.token_refresco import VIDA_REFRESCO, calcular_huella
from tests.dobles import EmisorFalso, RepositorioTokensEnMemoria

ANA = uuid4()
LUIS = uuid4()
AHORA = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)


def preparar():
    return RepositorioTokensEnMemoria(), EmisorFalso()


def test_abrir_sesion_entrega_acceso_y_refresco():
    repo, emisor = preparar()
    par = abrir_sesion(ANA, repo, emisor, AHORA)
    assert par.acceso == f"acceso-{ANA}"
    assert par.refresco
    assert par.expira_en == 900


def test_solo_se_guarda_la_huella_nunca_el_token():
    repo, emisor = preparar()
    par = abrir_sesion(ANA, repo, emisor, AHORA)
    guardado = next(iter(repo.tokens.values()))
    assert guardado.huella == calcular_huella(par.refresco)
    assert par.refresco not in repr(guardado)
    assert guardado.expira_en == AHORA + VIDA_REFRESCO


def test_cada_sesion_tiene_un_refresco_distinto():
    repo, emisor = preparar()
    a = abrir_sesion(ANA, repo, emisor, AHORA)
    b = abrir_sesion(ANA, repo, emisor, AHORA)
    assert a.refresco != b.refresco


def test_renovar_entrega_un_par_nuevo_y_revoca_el_viejo():
    repo, emisor = preparar()
    primero = abrir_sesion(ANA, repo, emisor, AHORA)
    segundo = renovar_sesion(primero.refresco, repo, emisor, AHORA)
    assert segundo.refresco != primero.refresco
    viejo = repo.buscar_por_huella(calcular_huella(primero.refresco))
    assert viejo is not None and viejo.revocado_en == AHORA
    # el nuevo sí sirve
    tercero = renovar_sesion(segundo.refresco, repo, emisor, AHORA)
    assert tercero.acceso == f"acceso-{ANA}"


def test_un_token_ya_usado_no_sirve_y_cierra_todas_las_sesiones():
    repo, emisor = preparar()
    primero = abrir_sesion(ANA, repo, emisor, AHORA)
    segundo = renovar_sesion(primero.refresco, repo, emisor, AHORA)
    with pytest.raises(TokenInvalido):
        renovar_sesion(primero.refresco, repo, emisor, AHORA)  # reutilizado: señal de robo
    with pytest.raises(TokenInvalido):
        renovar_sesion(segundo.refresco, repo, emisor, AHORA)  # el legítimo también cae


def test_un_token_vencido_no_sirve():
    repo, emisor = preparar()
    par = abrir_sesion(ANA, repo, emisor, AHORA)
    despues = AHORA + VIDA_REFRESCO + timedelta(seconds=1)
    with pytest.raises(TokenInvalido):
        renovar_sesion(par.refresco, repo, emisor, despues)


def test_un_token_desconocido_no_sirve():
    repo, emisor = preparar()
    with pytest.raises(TokenInvalido):
        renovar_sesion("inventado", repo, emisor, AHORA)


def test_cerrar_sesion_deja_el_token_inservible():
    repo, emisor = preparar()
    par = abrir_sesion(ANA, repo, emisor, AHORA)
    cerrar_sesion(par.refresco, repo, AHORA)
    with pytest.raises(TokenInvalido):
        renovar_sesion(par.refresco, repo, emisor, AHORA)


def test_cerrar_una_sesion_inexistente_o_ya_cerrada_no_falla():
    repo, emisor = preparar()
    par = abrir_sesion(ANA, repo, emisor, AHORA)
    cerrar_sesion("inventado", repo, AHORA)
    cerrar_sesion(par.refresco, repo, AHORA)
    cerrar_sesion(par.refresco, repo, AHORA)


def test_cerrar_una_sesion_no_toca_las_otras_del_mismo_usuario():
    repo, emisor = preparar()
    telefono = abrir_sesion(ANA, repo, emisor, AHORA)
    notebook = abrir_sesion(ANA, repo, emisor, AHORA)
    cerrar_sesion(telefono.refresco, repo, AHORA)
    renovar_sesion(notebook.refresco, repo, emisor, AHORA)  # sigue funcionando


def test_cerrar_todas_las_sesiones_solo_afecta_a_esa_persona():
    repo, emisor = preparar()
    a1 = abrir_sesion(ANA, repo, emisor, AHORA)
    a2 = abrir_sesion(ANA, repo, emisor, AHORA)
    luis = abrir_sesion(LUIS, repo, emisor, AHORA)
    cerrar_todas_las_sesiones(ANA, repo, AHORA)
    for par in (a1, a2):
        with pytest.raises(TokenInvalido):
            renovar_sesion(par.refresco, repo, emisor, AHORA)
    renovar_sesion(luis.refresco, repo, emisor, AHORA)
