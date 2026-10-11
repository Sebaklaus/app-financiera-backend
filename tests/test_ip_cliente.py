from types import SimpleNamespace

from app.adaptadores.api.ip_cliente import ip_del_cliente


def pedido(directa="10.0.0.1", xff=None):
    cabeceras = {} if xff is None else {"x-forwarded-for": xff}
    return SimpleNamespace(client=SimpleNamespace(host=directa), headers=cabeceras)


def test_sin_proxies_se_usa_la_ip_directa_aunque_haya_encabezado():
    assert ip_del_cliente(pedido(xff="9.9.9.9"), proxies=0) == "10.0.0.1"


def test_con_un_proxy_se_toma_la_ultima_entrada():
    # Quien llama escribió "6.6.6.6" para engañar; nuestro proxy agregó la IP real al final.
    assert ip_del_cliente(pedido(xff="6.6.6.6, 203.0.113.7"), proxies=1) == "203.0.113.7"


def test_con_dos_proxies_se_toma_la_penultima():
    assert ip_del_cliente(pedido(xff="6.6.6.6, 203.0.113.7, 35.1.1.1"), proxies=2) == "203.0.113.7"


def test_si_faltan_entradas_se_usa_la_ip_directa():
    assert ip_del_cliente(pedido(xff="203.0.113.7"), proxies=2) == "10.0.0.1"
    assert ip_del_cliente(pedido(), proxies=1) == "10.0.0.1"


def test_lee_proxies_del_entorno(monkeypatch):
    monkeypatch.setenv("PROXIES_CONFIABLES", "1")
    assert ip_del_cliente(pedido(xff="6.6.6.6, 203.0.113.7")) == "203.0.113.7"
    monkeypatch.setenv("PROXIES_CONFIABLES", "basura")
    assert ip_del_cliente(pedido(xff="6.6.6.6, 203.0.113.7")) == "10.0.0.1"
