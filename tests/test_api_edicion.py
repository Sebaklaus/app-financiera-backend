"""Prueba las rutas de editar y borrar movimientos con SQLite en memoria."""

from uuid import uuid4

import pytest

from tests.apoyo_api import crear_cliente


@pytest.fixture
def cliente():
    return crear_cliente()


def entrar(cliente, email="ana@correo.cl"):
    """Registra a la persona, inicia sesión y devuelve la cabecera con su token."""
    datos = {"email": email, "contrasena": "Clave1234"}
    cliente.post("/registro", json=datos)
    token = cliente.post("/login", json=datos).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


INGRESO = {"monto": 100_000, "descripcion": "Sueldo", "fecha": "2026-10-01"}
GASTO = {"monto": 5_000, "categoria": "necesidades", "descripcion": "Super"}


def crear_gasto(cliente, cabecera):
    return cliente.post("/gastos", json=GASTO, headers=cabecera).json()["id"]


def crear_ingreso(cliente, cabecera):
    return cliente.post("/ingresos", json=INGRESO, headers=cabecera).json()


def editar(cliente, cabecera, movimiento_id, cambios):
    return cliente.patch(f"/movimientos/{movimiento_id}", json=cambios, headers=cabecera)


def test_las_rutas_exigen_token(cliente):
    assert cliente.patch(f"/movimientos/{uuid4()}", json={"monto": 1}).status_code == 401
    assert cliente.delete(f"/movimientos/{uuid4()}").status_code == 401


def test_editar_un_gasto_devuelve_200_con_los_cambios(cliente):
    cabecera = entrar(cliente)
    gasto_id = crear_gasto(cliente, cabecera)
    respuesta = editar(cliente, cabecera, gasto_id, {"monto": 7_000, "categoria": "inversion"})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["monto"] == 7_000
    assert cuerpo["categoria"] == "inversion"
    assert cuerpo["descripcion"] == "Super"
    assert cuerpo["por_confirmar"] == []


def test_editar_sin_ningun_dato_da_422(cliente):
    cabecera = entrar(cliente)
    gasto_id = crear_gasto(cliente, cabecera)
    assert editar(cliente, cabecera, gasto_id, {}).status_code == 422


@pytest.mark.parametrize("cambios", [{"monto": 0}, {"monto": "1000"}, {"categoria": "viajes"}])
def test_editar_con_datos_invalidos_da_422(cliente, cambios):
    cabecera = entrar(cliente)
    gasto_id = crear_gasto(cliente, cabecera)
    assert editar(cliente, cabecera, gasto_id, cambios).status_code == 422


def test_editar_el_monto_de_un_ingreso_vuelve_a_proponer(cliente):
    cabecera = entrar(cliente)
    ingreso = crear_ingreso(cliente, cabecera)
    respuesta = editar(cliente, cabecera, ingreso["id"], {"monto": 200_000})
    assert respuesta.status_code == 200
    montos = {c["categoria"]: c["monto"] for c in respuesta.json()["por_confirmar"]}
    assert montos == {"inversion": 50_000, "estabilidad": 30_000}
    pendientes = cliente.get("/confirmaciones/pendientes", headers=cabecera).json()
    assert len(pendientes) == 2


def test_no_se_cambia_el_monto_de_un_ingreso_con_partes_decididas(cliente):
    cabecera = entrar(cliente)
    ingreso = crear_ingreso(cliente, cabecera)
    propuesta_id = ingreso["por_confirmar"][0]["id"]
    cliente.post(
        f"/confirmaciones/{propuesta_id}/decision",
        json={"decision": "confirmar"},
        headers=cabecera,
    )
    respuesta = editar(cliente, cabecera, ingreso["id"], {"monto": 200_000})
    assert respuesta.status_code == 409


def test_editar_lo_ajeno_o_inexistente_da_404(cliente):
    cabecera_ana = entrar(cliente, "ana@correo.cl")
    cabecera_luis = entrar(cliente, "luis@correo.cl")
    gasto_id = crear_gasto(cliente, cabecera_ana)
    assert editar(cliente, cabecera_luis, gasto_id, {"monto": 1}).status_code == 404
    assert editar(cliente, cabecera_ana, uuid4(), {"monto": 1}).status_code == 404


def test_un_id_que_no_es_uuid_da_422(cliente):
    cabecera = entrar(cliente)
    assert editar(cliente, cabecera, "no-es-uuid", {"monto": 1}).status_code == 422


def test_borrar_un_gasto_da_204_y_desaparece(cliente):
    cabecera = entrar(cliente)
    gasto_id = crear_gasto(cliente, cabecera)
    assert cliente.delete(f"/movimientos/{gasto_id}", headers=cabecera).status_code == 204
    assert cliente.get("/movimientos", headers=cabecera).json() == []
    assert cliente.delete(f"/movimientos/{gasto_id}", headers=cabecera).status_code == 404


def test_borrar_un_ingreso_borra_sus_propuestas_y_limpia_el_resumen(cliente):
    cabecera = entrar(cliente)
    ingreso = crear_ingreso(cliente, cabecera)
    assert cliente.delete(f"/movimientos/{ingreso['id']}", headers=cabecera).status_code == 204
    assert cliente.get("/confirmaciones/pendientes", headers=cabecera).json() == []
    assert cliente.get("/resumen", headers=cabecera).json()["ingresos_total"] == 0


def test_nadie_borra_lo_de_otra_persona(cliente):
    cabecera_ana = entrar(cliente, "ana@correo.cl")
    cabecera_luis = entrar(cliente, "luis@correo.cl")
    gasto_id = crear_gasto(cliente, cabecera_ana)
    assert cliente.delete(f"/movimientos/{gasto_id}", headers=cabecera_luis).status_code == 404
    assert len(cliente.get("/movimientos", headers=cabecera_ana).json()) == 1
