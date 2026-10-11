from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adaptadores.api.cabeceras_seguridad import aplicar_cabeceras_seguridad


def _cliente() -> TestClient:
    app = FastAPI()

    @app.get("/dato")
    def dato() -> dict[str, int]:
        return {"valor": 1}

    aplicar_cabeceras_seguridad(app)
    return TestClient(app)


def test_las_respuestas_de_la_api_llevan_todas_las_cabeceras():
    h = _cliente().get("/dato").headers
    assert h["x-content-type-options"] == "nosniff"
    assert h["x-frame-options"] == "DENY"
    assert h["referrer-policy"] == "no-referrer"
    assert "max-age" in h["strict-transport-security"]
    assert h["cache-control"] == "no-store"
    assert "default-src 'none'" in h["content-security-policy"]


def test_la_documentacion_no_lleva_las_que_la_romperian():
    h = _cliente().get("/docs").headers
    assert h["x-content-type-options"] == "nosniff"
    assert "content-security-policy" not in h
    assert "cache-control" not in h
