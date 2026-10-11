"""Pruebas de /yo/consentimientos y /yo/perfil-riesgo con SQLite en memoria."""

import pytest

from tests.apoyo_api import crear_cliente

CLAVE = "Clave1234"


@pytest.fixture
def cliente():
    return crear_cliente()


def entrar(cliente, email="ana@correo.cl"):
    datos = {"email": email, "contrasena": CLAVE}
    cliente.post("/registro", json=datos)
    token = cliente.post("/login", json=datos).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def lineas(cuerpo):
    return {c["tipo"]: c for c in cuerpo["consentimientos"]}


def test_las_rutas_exigen_token(cliente):
    assert cliente.get("/yo/consentimientos").status_code == 401
    assert cliente.put("/yo/consentimientos", json={}).status_code == 401
    assert cliente.get("/yo/perfil-riesgo").status_code == 401
    assert cliente.put("/yo/perfil-riesgo", json={"perfil": "moderado"}).status_code == 401


def test_al_inicio_faltan_los_obligatorios(cliente):
    cabecera = entrar(cliente)
    cuerpo = cliente.get("/yo/consentimientos", headers=cabecera).json()
    assert cuerpo["pendientes"] == ["terminos_y_privacidad", "datos_financieros"]
    assert cuerpo["version_textos"]
    assert lineas(cuerpo)["comunicaciones"]["obligatorio"] is False
    assert lineas(cuerpo)["datos_financieros"]["otorgado"] is False


def test_otorgar_obligatorios_y_un_opcional(cliente):
    cabecera = entrar(cliente)
    r = cliente.put(
        "/yo/consentimientos",
        json={"terminos_y_privacidad": True, "datos_financieros": True, "comunicaciones": False},
        headers=cabecera,
    )
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["pendientes"] == []
    assert lineas(cuerpo)["terminos_y_privacidad"]["otorgado"] is True
    assert lineas(cuerpo)["terminos_y_privacidad"]["desde"].endswith("Z")
    assert lineas(cuerpo)["comunicaciones"]["otorgado"] is False


def test_se_puede_otorgar_de_a_uno(cliente):
    cabecera = entrar(cliente)
    r = cliente.put("/yo/consentimientos", json={"datos_financieros": True}, headers=cabecera)
    assert r.json()["pendientes"] == ["terminos_y_privacidad"]


def test_retirar_un_obligatorio_da_422(cliente):
    cabecera = entrar(cliente)
    cliente.put("/yo/consentimientos", json={"datos_financieros": True}, headers=cabecera)
    r = cliente.put("/yo/consentimientos", json={"datos_financieros": False}, headers=cabecera)
    assert r.status_code == 422
    estado = cliente.get("/yo/consentimientos", headers=cabecera).json()
    assert lineas(estado)["datos_financieros"]["otorgado"] is True


def test_un_cuerpo_vacio_da_422(cliente):
    cabecera = entrar(cliente)
    assert cliente.put("/yo/consentimientos", json={}, headers=cabecera).status_code == 422


def test_retirar_un_opcional_funciona(cliente):
    cabecera = entrar(cliente)
    cliente.put("/yo/consentimientos", json={"comunicaciones": True}, headers=cabecera)
    r = cliente.put("/yo/consentimientos", json={"comunicaciones": False}, headers=cabecera)
    assert lineas(r.json())["comunicaciones"]["otorgado"] is False


def test_una_persona_no_ve_los_consentimientos_de_otra(cliente):
    ana = entrar(cliente)
    luis = entrar(cliente, "luis@correo.cl")
    cliente.put("/yo/consentimientos", json={"datos_financieros": True}, headers=ana)
    estado = cliente.get("/yo/consentimientos", headers=luis).json()
    assert lineas(estado)["datos_financieros"]["otorgado"] is False


def test_perfil_de_riesgo_se_declara_y_se_corrige(cliente):
    cabecera = entrar(cliente)
    vacio = cliente.get("/yo/perfil-riesgo", headers=cabecera).json()
    assert vacio == {"perfil": None, "actualizado_en": None}
    r = cliente.put("/yo/perfil-riesgo", json={"perfil": "conservador"}, headers=cabecera)
    assert r.status_code == 200
    assert r.json()["perfil"] == "conservador"
    assert r.json()["actualizado_en"].endswith("Z")
    cliente.put("/yo/perfil-riesgo", json={"perfil": "arriesgado"}, headers=cabecera)
    assert cliente.get("/yo/perfil-riesgo", headers=cabecera).json()["perfil"] == "arriesgado"


def test_perfil_invalido_da_422(cliente):
    cabecera = entrar(cliente)
    r = cliente.put("/yo/perfil-riesgo", json={"perfil": "temerario"}, headers=cabecera)
    assert r.status_code == 422


def test_el_export_incluye_consentimientos_y_perfil(cliente):
    cabecera = entrar(cliente)
    cliente.put("/yo/consentimientos", json={"datos_financieros": True}, headers=cabecera)
    cliente.put("/yo/perfil-riesgo", json={"perfil": "moderado"}, headers=cabecera)
    datos = cliente.get("/yo/datos", headers=cabecera).json()
    assert datos["perfil_riesgo"] == "moderado"
    assert [c["tipo"] for c in datos["consentimientos"]] == ["datos_financieros"]
    assert datos["consentimientos"][0]["fecha"].endswith("Z")


def test_eliminar_la_cuenta_borra_consentimientos_y_perfil(cliente):
    cabecera = entrar(cliente)
    cliente.put("/yo/consentimientos", json={"datos_financieros": True}, headers=cabecera)
    cliente.put("/yo/perfil-riesgo", json={"perfil": "moderado"}, headers=cabecera)
    borrado = cliente.post("/yo/eliminar", json={"contrasena": CLAVE}, headers=cabecera)
    assert borrado.status_code == 204
    # Al registrarse de nuevo con el mismo email, parte desde cero.
    nueva = entrar(cliente)
    assert cliente.get("/yo/perfil-riesgo", headers=nueva).json()["perfil"] is None
    assert len(cliente.get("/yo/consentimientos", headers=nueva).json()["pendientes"]) == 2
