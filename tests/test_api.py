from fastapi.testclient import TestClient

from app.main import app

cliente = TestClient(app)


def test_salud():
    r = cliente.get("/salud")
    assert r.status_code == 200
    assert r.json() == {"estado": "ok"}


def test_distribucion_ok():
    r = cliente.post("/distribucion", json={"monto": 100_001})
    assert r.status_code == 200
    assert r.json() == {
        "necesidades": 50_001,
        "inversion": 25_000,
        "estabilidad": 15_000,
        "entretenimiento": 10_000,
        "total": 100_001,
    }


def test_distribucion_rechaza_datos_invalidos():
    for cuerpo in ({"monto": 0}, {"monto": -1}, {"monto": "1000"}, {"monto": 10.5}, {}):
        assert cliente.post("/distribucion", json=cuerpo).status_code == 422
