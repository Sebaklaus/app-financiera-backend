"""Rutas /inversion/opciones y /inversion/derivaciones."""

import pytest

from tests.apoyo_api import crear_cliente


@pytest.fixture
def cliente():
    return crear_cliente()


def entrar(cliente, email="ana@correo.cl"):
    datos = {"email": email, "contrasena": "Clave1234"}
    cliente.post("/registro", json=datos)
    token = cliente.post("/login", json=datos).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_exigen_token(cliente):
    assert cliente.get("/inversion/opciones").status_code == 401
    r = cliente.post("/inversion/derivaciones", json={"instrumento_id": "cuenta-ahorro"})
    assert r.status_code == 401


def test_sin_perfil_se_ven_las_opciones_sin_recomendadas(cliente):
    cabecera = entrar(cliente)
    cuerpo = cliente.get("/inversion/opciones", headers=cabecera).json()
    assert cuerpo["perfil_riesgo"] is None
    assert len(cuerpo["opciones"]) == 5
    assert not any(o["recomendado"] for o in cuerpo["opciones"])
    assert "no es una recomendación" in cuerpo["aviso"]


def test_con_perfil_conservador_solo_el_riesgo_bajo_es_recomendado(cliente):
    cabecera = entrar(cliente)
    cliente.put("/yo/perfil-riesgo", json={"perfil": "conservador"}, headers=cabecera)
    cuerpo = cliente.get("/inversion/opciones", headers=cabecera).json()
    assert cuerpo["perfil_riesgo"] == "conservador"
    for o in cuerpo["opciones"]:
        assert o["recomendado"] is (o["riesgo"] == "bajo")
    assert cuerpo["opciones"][0]["recomendado"] is True


def test_derivar_devuelve_la_redireccion_simulada_y_queda_en_la_bitacora(cliente):
    cabecera = entrar(cliente)
    r = cliente.post(
        "/inversion/derivaciones",
        json={"instrumento_id": "deposito-a-plazo", "monto": 250_000},
        headers=cabecera,
    )
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["simulada"] is True
    assert cuerpo["monto"] == 250_000
    assert cuerpo["entidad"]["id"] == "banco-socio"
    assert cuerpo["url"].endswith("/inversiones") and ".invalid" in cuerpo["url"]
    actividad = cliente.get("/yo/actividad", headers=cabecera).json()
    assert "derivacion_inversion" in [e["tipo"] for e in actividad]


def test_instrumento_inexistente_da_404(cliente):
    cabecera = entrar(cliente)
    r = cliente.post("/inversion/derivaciones", json={"instrumento_id": "x"}, headers=cabecera)
    assert r.status_code == 404


@pytest.mark.parametrize("monto", [0, -5, "100", 1.5])
def test_monto_invalido_da_422(cliente, monto):
    cabecera = entrar(cliente)
    r = cliente.post(
        "/inversion/derivaciones",
        json={"instrumento_id": "cuenta-ahorro", "monto": monto},
        headers=cabecera,
    )
    assert r.status_code == 422
