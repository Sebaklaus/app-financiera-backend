import pytest

from app.infraestructura.enviador_correo import EnviadorCorreoConsola, crear_enviador


def test_por_defecto_es_el_modo_consola(monkeypatch):
    monkeypatch.delenv("CORREO_MODO", raising=False)
    assert isinstance(crear_enviador(), EnviadorCorreoConsola)


def test_un_modo_desconocido_falla_en_voz_alta(monkeypatch):
    monkeypatch.setenv("CORREO_MODO", "sendgrid")
    with pytest.raises(RuntimeError):
        crear_enviador()


def test_el_modo_consola_escribe_en_el_registro(caplog):
    EnviadorCorreoConsola().enviar_recuperacion("ana@correo.cl", "TOKEN123")
    assert "TOKEN123" in caplog.text
