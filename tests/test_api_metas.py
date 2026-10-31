"""Prueba las rutas de metas de ahorro con SQLite en memoria."""

from datetime import date, timedelta
from uuid import uuid4

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


META = {"nombre": "Viaje", "monto_objetivo": 500_000}


def crear(cliente, cabecera, **extra):
    respuesta = cliente.post("/metas", json={**META, **extra}, headers=cabecera)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_las_rutas_exigen_token(cliente):
    meta_id = uuid4()
    assert cliente.post("/metas", json=META).status_code == 401
    assert cliente.get("/metas").status_code == 401
    assert cliente.get(f"/metas/{meta_id}").status_code == 401
    assert cliente.post(f"/metas/{meta_id}/aportes", json={"monto": 1_000}).status_code == 401
    assert cliente.delete(f"/metas/{meta_id}").status_code == 401


def test_crear_meta_devuelve_201_con_avance_en_cero(cliente):
    cabecera = entrar(cliente)
    meta = crear(cliente, cabecera)
    assert meta["nombre"] == "Viaje"
    assert meta["monto_objetivo"] == 500_000
    assert (meta["ahorrado"], meta["falta"], meta["porcentaje"]) == (0, 500_000, 0)
    assert meta["cumplida"] is False
    assert meta["fecha_limite"] is None


def test_crear_meta_con_fecha_limite(cliente):
    cabecera = entrar(cliente)
    limite = (date.today() + timedelta(days=60)).isoformat()
    assert crear(cliente, cabecera, fecha_limite=limite)["fecha_limite"] == limite


@pytest.mark.parametrize(
    "datos",
    [
        {"nombre": "", "monto_objetivo": 1_000},
        {"nombre": "x" * 81, "monto_objetivo": 1_000},
        {"nombre": "Viaje", "monto_objetivo": 0},
        {"nombre": "Viaje", "monto_objetivo": "1000"},
        {"nombre": "Viaje", "monto_objetivo": 1.5},
        {"nombre": "Viaje", "monto_objetivo": 1_000, "fecha_limite": "2020-01-01"},
    ],
)
def test_meta_invalida_da_422(cliente, datos):
    cabecera = entrar(cliente)
    assert cliente.post("/metas", json=datos, headers=cabecera).status_code == 422


def test_aportar_actualiza_el_avance(cliente):
    cabecera = entrar(cliente)
    meta = crear(cliente, cabecera)
    r1 = cliente.post(f"/metas/{meta['id']}/aportes", json={"monto": 100_000}, headers=cabecera)
    assert r1.status_code == 201
    r2 = cliente.post(f"/metas/{meta['id']}/aportes", json={"monto": 150_000}, headers=cabecera)
    cuerpo = r2.json()
    assert (cuerpo["ahorrado"], cuerpo["porcentaje"]) == (250_000, 50)
    assert len(cuerpo["aportes"]) == 2


def test_alcanzar_el_objetivo_marca_la_meta_como_cumplida(cliente):
    cabecera = entrar(cliente)
    meta = crear(cliente, cabecera)
    r = cliente.post(f"/metas/{meta['id']}/aportes", json={"monto": 500_000}, headers=cabecera)
    cuerpo = r.json()
    assert cuerpo["cumplida"] is True
    assert (cuerpo["falta"], cuerpo["porcentaje"]) == (0, 100)


def test_aporte_invalido_da_422(cliente):
    cabecera = entrar(cliente)
    meta = crear(cliente, cabecera)
    url = f"/metas/{meta['id']}/aportes"
    assert cliente.post(url, json={"monto": 0}, headers=cabecera).status_code == 422
    futuro = (date.today() + timedelta(days=3)).isoformat()
    assert (
        cliente.post(url, json={"monto": 1_000, "fecha": futuro}, headers=cabecera).status_code
        == 422
    )


def test_listar_y_ver_detalle(cliente):
    cabecera = entrar(cliente)
    meta = crear(cliente, cabecera)
    cliente.post(f"/metas/{meta['id']}/aportes", json={"monto": 50_000}, headers=cabecera)
    lista = cliente.get("/metas", headers=cabecera).json()
    assert [m["nombre"] for m in lista] == ["Viaje"]
    assert lista[0]["ahorrado"] == 50_000
    detalle = cliente.get(f"/metas/{meta['id']}", headers=cabecera).json()
    assert detalle["porcentaje"] == 10
    assert [a["monto"] for a in detalle["aportes"]] == [50_000]


def test_una_persona_no_ve_ni_toca_las_metas_de_otra(cliente):
    ana = entrar(cliente, "ana@correo.cl")
    luis = entrar(cliente, "luis@correo.cl")
    meta = crear(cliente, ana)
    assert cliente.get("/metas", headers=luis).json() == []
    assert cliente.get(f"/metas/{meta['id']}", headers=luis).status_code == 404
    url = f"/metas/{meta['id']}/aportes"
    assert cliente.post(url, json={"monto": 1_000}, headers=luis).status_code == 404
    assert cliente.delete(f"/metas/{meta['id']}", headers=luis).status_code == 404
    assert cliente.get(f"/metas/{meta['id']}", headers=ana).status_code == 200


def test_eliminar_meta(cliente):
    cabecera = entrar(cliente)
    meta = crear(cliente, cabecera)
    cliente.post(f"/metas/{meta['id']}/aportes", json={"monto": 1_000}, headers=cabecera)
    assert cliente.delete(f"/metas/{meta['id']}", headers=cabecera).status_code == 204
    assert cliente.get(f"/metas/{meta['id']}", headers=cabecera).status_code == 404
    assert cliente.delete(f"/metas/{meta['id']}", headers=cabecera).status_code == 404


def test_eliminar_la_cuenta_borra_sus_metas(cliente):
    cabecera = entrar(cliente)
    meta = crear(cliente, cabecera)
    cliente.post(f"/metas/{meta['id']}/aportes", json={"monto": 1_000}, headers=cabecera)
    respuesta = cliente.post("/yo/eliminar", json={"contrasena": "Clave1234"}, headers=cabecera)
    assert respuesta.status_code == 204, respuesta.text
    # El token sigue firmado, pero la cuenta y sus metas ya no existen.
    assert cliente.get(f"/metas/{meta['id']}", headers=cabecera).status_code == 404
