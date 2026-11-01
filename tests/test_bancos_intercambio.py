"""Conexión bancaria por intercambio (widget de Fintoc -> exchange_token -> link_token)."""

import json
from uuid import uuid4

import pytest

from app.casos_de_uso.bancos import conectar_con_intercambio, cuentas_del_banco, iniciar_conexion
from app.dominio.banco import BancoNoDisponible, EnlaceBancarioInvalido
from app.infraestructura.proveedor_fintoc import ProveedorFintoc
from tests.dobles_bancos import EnlacesEnMemoria, ProveedorBancarioFalso

ANA = uuid4()


# ---- casos de uso ----


def test_iniciar_la_conexion_entrega_un_widget_token():
    banco = ProveedorBancarioFalso()
    assert iniciar_conexion(banco) == "widget_token_prueba"
    assert banco.intenciones == 1


def test_el_intercambio_guarda_el_link_y_devuelve_las_cuentas():
    banco, enlaces = ProveedorBancarioFalso(), EnlacesEnMemoria()
    cuentas = conectar_con_intercambio(ANA, " exch_ok ", enlaces, banco)
    assert cuentas[0].id == "acc_1"
    assert enlaces.obtener(ANA) == "link_ok"
    assert cuentas_del_banco(ANA, enlaces, banco)[0].id == "acc_1"


def test_un_codigo_malo_no_guarda_nada():
    banco, enlaces = ProveedorBancarioFalso(), EnlacesEnMemoria()
    with pytest.raises(EnlaceBancarioInvalido):
        conectar_con_intercambio(ANA, "exch_malo", enlaces, banco)
    assert enlaces.obtener(ANA) is None


def test_el_codigo_sirve_una_sola_vez():
    banco, enlaces = ProveedorBancarioFalso(), EnlacesEnMemoria()
    conectar_con_intercambio(ANA, "exch_ok", enlaces, banco)
    with pytest.raises(EnlaceBancarioInvalido):
        conectar_con_intercambio(uuid4(), "exch_ok", EnlacesEnMemoria(), banco)


@pytest.mark.parametrize("codigo", ["", "   ", "x" * 201])
def test_un_codigo_vacio_o_enorme_no_llega_al_banco(codigo):
    banco = ProveedorBancarioFalso()
    with pytest.raises(EnlaceBancarioInvalido):
        conectar_con_intercambio(ANA, codigo, EnlacesEnMemoria(), banco)
    assert banco.exchanges_usados == []


def test_banco_caido_en_el_intercambio():
    banco = ProveedorBancarioFalso()
    banco.caido = True
    with pytest.raises(BancoNoDisponible):
        conectar_con_intercambio(ANA, "exch_ok", EnlacesEnMemoria(), banco)


# ---- adaptador de Fintoc (sin Internet) ----


def _fintoc(codigo, cuerpo, destino):
    def pedir(url, clave):
        destino["get"] = (url, clave)
        return codigo, cuerpo if isinstance(cuerpo, str) else json.dumps(cuerpo)

    def enviar(url, clave, datos):
        destino["post"] = (url, clave, datos)
        return codigo, cuerpo if isinstance(cuerpo, str) else json.dumps(cuerpo)

    return ProveedorFintoc("sk_test_x", pedir, enviar)


def test_fintoc_crea_la_intencion_de_solo_lectura_para_chile():
    visto = {}
    token = _fintoc(201, {"widget_token": "wt_123"}, visto).crear_intencion()
    assert token == "wt_123"
    url, clave, datos = visto["post"]
    assert url.endswith("/link_intents") and clave == "sk_test_x"
    assert datos == {"country": "cl", "holder_type": "individual", "product": "movements"}


def test_fintoc_intercambia_el_codigo_por_el_link_token():
    visto = {}
    link = _fintoc(200, {"id": "link_1", "link_token": "link_1_token_abc"}, visto).intercambiar(
        "exch 1&x"
    )
    assert link == "link_1_token_abc"
    url, clave = visto["get"]
    assert clave == "sk_test_x"
    assert "exchange_token=exch+1%26x" in url  # el código se escapa, no se pega crudo


@pytest.mark.parametrize("codigo", [400, 401, 403, 404])
def test_fintoc_rechaza_codigos_malos(codigo):
    with pytest.raises(EnlaceBancarioInvalido):
        _fintoc(codigo, "{}", {}).intercambiar("x")
    with pytest.raises(EnlaceBancarioInvalido):
        _fintoc(codigo, "{}", {}).crear_intencion()


def test_fintoc_caido_o_respuesta_rara():
    with pytest.raises(BancoNoDisponible):
        _fintoc(503, "{}", {}).intercambiar("x")
    with pytest.raises(BancoNoDisponible):
        _fintoc(200, "no es json", {}).intercambiar("x")
    with pytest.raises(BancoNoDisponible):
        _fintoc(200, [1, 2], {}).intercambiar("x")
    with pytest.raises(BancoNoDisponible):
        _fintoc(200, {"sin": "link_token"}, {}).intercambiar("x")
    with pytest.raises(BancoNoDisponible):
        _fintoc(201, {"sin": "widget_token"}, {}).crear_intencion()
