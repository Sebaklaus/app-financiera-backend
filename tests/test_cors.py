import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adaptadores.api.cors import aplicar_cors
from app.configuracion import origenes_cors


def _app(origenes: list[str]) -> TestClient:
    app = FastAPI()

    @app.get("/ping")
    def ping() -> dict[str, str]:
        return {"ok": "si"}

    aplicar_cors(app, origenes)
    return TestClient(app)


def test_origen_autorizado_recibe_permiso() -> None:
    cliente = _app(["http://localhost:5000"])
    r = cliente.get("/ping", headers={"Origin": "http://localhost:5000"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5000"


def test_origen_desconocido_no_recibe_permiso() -> None:
    cliente = _app(["http://localhost:5000"])
    r = cliente.get("/ping", headers={"Origin": "http://malo.example"})
    assert "access-control-allow-origin" not in r.headers


def test_preflight_permite_authorization_y_patch() -> None:
    cliente = _app(["http://localhost:5000"])
    r = cliente.options(
        "/ping",
        headers={
            "Origin": "http://localhost:5000",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert r.status_code == 200
    assert "PATCH" in r.headers["access-control-allow-methods"]


def test_sin_origenes_configurados_no_se_activa_cors() -> None:
    cliente = _app([])
    r = cliente.get("/ping", headers={"Origin": "http://localhost:5000"})
    assert "access-control-allow-origin" not in r.headers


def test_asterisco_se_rechaza() -> None:
    with pytest.raises(RuntimeError):
        aplicar_cors(FastAPI(), ["*"])


def test_lee_origenes_del_entorno(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", " http://a.cl , http://b.cl ,")
    assert origenes_cors() == ["http://a.cl", "http://b.cl"]
    monkeypatch.delenv("CORS_ORIGINS")
    assert origenes_cors() == []
