"""Conexión bancaria: casos de uso, rutas (con SQLite) y el adaptador de Fintoc sin Internet."""

import json
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.casos_de_uso.bancos import conectar_banco, cuentas_del_banco
from app.dominio.banco import BancoNoDisponible, EnlaceBancarioInvalido, SinEnlaceBancario
from app.infraestructura.base_de_datos import crear_fabrica_sesiones, crear_tablas
from app.infraestructura.cifrador import CifradorFernet
from app.infraestructura.proveedor_fintoc import ProveedorFintoc
from app.infraestructura.repositorio_enlaces_sql import RepositorioEnlacesSQL
from tests.apoyo_api import crear_cliente
from tests.dobles_bancos import EnlacesEnMemoria, ProveedorBancarioFalso


@pytest.fixture
def cliente():
    return crear_cliente()


def entrar(cliente, email="ana@correo.cl"):
    datos = {"email": email, "contrasena": "Clave1234"}
    cliente.post("/registro", json=datos)
    token = cliente.post("/login", json=datos).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_las_rutas_bancarias_exigen_token(cliente):
    assert cliente.post("/bancos/enlace", json={"link_token": "x"}).status_code == 401
    assert cliente.get("/bancos/cuentas").status_code == 401
    assert cliente.delete("/bancos/enlace").status_code == 401


def test_sin_enlace_pedir_cuentas_da_409(cliente):
    cabecera = entrar(cliente)
    r = cliente.get("/bancos/cuentas", headers=cabecera)
    assert r.status_code == 409


def test_conectar_devuelve_cuentas_sin_el_token(cliente):
    cabecera = entrar(cliente)
    r = cliente.post("/bancos/enlace", json={"link_token": "link_ok"}, headers=cabecera)
    assert r.status_code == 200
    assert r.json()[0]["numero_enmascarado"] == "····1234"
    assert "link_ok" not in r.text


def test_enlace_invalido_da_422_y_no_se_guarda(cliente):
    cabecera = entrar(cliente)
    r = cliente.post("/bancos/enlace", json={"link_token": "malo"}, headers=cabecera)
    assert r.status_code == 422
    assert cliente.get("/bancos/cuentas", headers=cabecera).status_code == 409


def test_banco_caido_da_502(cliente):
    cabecera = entrar(cliente)
    cliente.banco.caido = True
    r = cliente.post("/bancos/enlace", json={"link_token": "link_ok"}, headers=cabecera)
    assert r.status_code == 502


def test_movimientos_del_banco(cliente):
    cabecera = entrar(cliente)
    cliente.post("/bancos/enlace", json={"link_token": "link_ok"}, headers=cabecera)
    r = cliente.get("/bancos/cuentas/acc_1/movimientos", headers=cabecera)
    assert r.status_code == 200
    assert [m["monto"] for m in r.json()] == [1_000_000, -45_000]


def test_importar_crea_ingreso_con_reparto_y_no_duplica(cliente):
    cabecera = entrar(cliente)
    cliente.post("/bancos/enlace", json={"link_token": "link_ok"}, headers=cabecera)
    r = cliente.post("/bancos/cuentas/acc_1/importar", headers=cabecera)
    assert r.json() == {"importados": 1, "ya_importados": 0, "cargos_omitidos": 1}
    pendientes = cliente.get("/confirmaciones/pendientes", headers=cabecera).json()
    assert sorted(c["categoria"] for c in pendientes) == ["estabilidad", "inversion"]
    movimientos = cliente.get("/movimientos", headers=cabecera).json()
    assert len(movimientos) == 1 and movimientos[0]["monto"] == 1_000_000
    otra = cliente.post("/bancos/cuentas/acc_1/importar", headers=cabecera).json()
    assert otra == {"importados": 0, "ya_importados": 1, "cargos_omitidos": 1}


def test_desconectar_borra_el_enlace(cliente):
    cabecera = entrar(cliente)
    cliente.post("/bancos/enlace", json={"link_token": "link_ok"}, headers=cabecera)
    assert cliente.delete("/bancos/enlace", headers=cabecera).status_code == 204
    assert cliente.get("/bancos/cuentas", headers=cabecera).status_code == 409


def test_cada_persona_ve_solo_su_enlace(cliente):
    ana = entrar(cliente, "ana@correo.cl")
    bea = entrar(cliente, "bea@correo.cl")
    cliente.post("/bancos/enlace", json={"link_token": "link_ok"}, headers=ana)
    assert cliente.get("/bancos/cuentas", headers=bea).status_code == 409


def test_eliminar_la_cuenta_borra_el_enlace(cliente):
    cabecera = entrar(cliente)
    cliente.post("/bancos/enlace", json={"link_token": "link_ok"}, headers=cabecera)
    r = cliente.post("/yo/eliminar", json={"contrasena": "Clave1234"}, headers=cabecera)
    assert r.status_code == 204


def test_el_enlace_se_guarda_cifrado():
    motor = create_engine(
        "sqlite+pysqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    crear_tablas(motor)
    cifrador = CifradorFernet(Fernet.generate_key().decode())
    with crear_fabrica_sesiones(motor)() as sesion:
        usuario = uuid4()
        repo = RepositorioEnlacesSQL(sesion, cifrador)
        repo.guardar(usuario, "link_secreto")
        crudo = sesion.execute(text("SELECT token_cifrado FROM enlaces_bancarios")).scalar_one()
        assert "link_secreto" not in crudo
        assert repo.obtener(usuario) == "link_secreto"
        assert repo.eliminar(usuario) is True
        assert repo.obtener(usuario) is None


def test_casos_de_uso_sin_enlace():
    with pytest.raises(SinEnlaceBancario):
        cuentas_del_banco(uuid4(), EnlacesEnMemoria(), ProveedorBancarioFalso())


def test_conectar_rechaza_enlace_vacio():
    with pytest.raises(EnlaceBancarioInvalido):
        conectar_banco(uuid4(), "   ", EnlacesEnMemoria(), ProveedorBancarioFalso())


# ---- Adaptador de Fintoc: se prueba con respuestas falsas, sin Internet ----


def _proveedor(codigo: int, cuerpo):
    visto = {}

    def pedir(url: str, clave: str):
        visto["url"], visto["clave"] = url, clave
        return codigo, cuerpo if isinstance(cuerpo, str) else json.dumps(cuerpo)

    return ProveedorFintoc("sk_test_x", pedir), visto


def test_fintoc_lee_cuentas():
    proveedor, visto = _proveedor(
        200,
        [
            {
                "id": "acc_9",
                "name": "Cuenta Vista",
                "number": "987654321",
                "currency": "CLP",
                "balance": {"available": 120000, "current": 120000},
            }
        ],
    )
    cuenta = proveedor.listar_cuentas("link_1")[0]
    assert (cuenta.id, cuenta.numero_enmascarado, cuenta.saldo) == ("acc_9", "····4321", 120000)
    assert visto["clave"] == "sk_test_x" and "link_token=link_1" in visto["url"]


def test_fintoc_lee_movimientos_con_signo():
    proveedor, _ = _proveedor(
        200,
        [
            {
                "id": "m1",
                "amount": 50000,
                "description": "Transferencia",
                "post_date": "2026-10-05T12:00:00Z",
            },
            {"id": "m2", "amount": -2000, "description": None, "post_date": "2026-10-06"},
        ],
    )
    movimientos = proveedor.listar_movimientos("link_1", "acc_9")
    assert [m.monto for m in movimientos] == [50000, -2000]
    assert movimientos[1].descripcion == "Movimiento bancario"


@pytest.mark.parametrize("codigo", [400, 401, 403, 404])
def test_fintoc_rechazo_es_enlace_invalido(codigo):
    proveedor, _ = _proveedor(codigo, "{}")
    with pytest.raises(EnlaceBancarioInvalido):
        proveedor.listar_cuentas("link_1")


def test_fintoc_error_de_servidor_o_respuesta_rara_es_banco_no_disponible():
    with pytest.raises(BancoNoDisponible):
        _proveedor(503, "{}")[0].listar_cuentas("l")
    with pytest.raises(BancoNoDisponible):
        _proveedor(200, "no es json")[0].listar_cuentas("l")
    with pytest.raises(BancoNoDisponible):
        _proveedor(200, [{"id": "m", "amount": 1, "post_date": ""}])[0].listar_movimientos("l", "a")
