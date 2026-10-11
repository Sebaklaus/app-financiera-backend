"""Prueba el repositorio de la cuenta contra SQLite en memoria."""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from app.dominio.bloqueo import RegistroIntentos
from app.dominio.categorias import Categoria
from app.dominio.confirmacion import Confirmacion, EstadoConfirmacion
from app.dominio.errores import EmailYaRegistrado
from app.dominio.movimiento import Movimiento, TipoMovimiento
from app.dominio.token_refresco import nuevo_token_refresco
from app.dominio.usuario import Usuario
from app.infraestructura.base_de_datos import crear_fabrica_sesiones, crear_motor, crear_tablas
from app.infraestructura.repositorio_cuenta_sql import RepositorioCuentaSQL
from app.infraestructura.repositorio_intentos_sql import RepositorioIntentosSQL
from app.infraestructura.repositorio_movimientos_sql import RepositorioMovimientosSQL
from app.infraestructura.repositorio_tokens_sql import RepositorioTokensSQL

AHORA = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)


def crear_usuario(email: str) -> Usuario:
    return Usuario(id=uuid4(), email=email, hash_contrasena="h", creado_en=AHORA)


@pytest.fixture
def sesion():
    motor = crear_motor("sqlite+pysqlite:///:memory:")
    crear_tablas(motor)
    with crear_fabrica_sesiones(motor)() as sesion:
        yield sesion


def test_buscar_por_id(sesion):
    repo = RepositorioCuentaSQL(sesion)
    ana = crear_usuario("ana@correo.cl")
    repo.guardar(ana)
    assert repo.buscar_por_id(ana.id).email == "ana@correo.cl"
    assert repo.buscar_por_id(uuid4()) is None


def test_cambiar_email_y_hash(sesion):
    repo = RepositorioCuentaSQL(sesion)
    ana = crear_usuario("ana@correo.cl")
    repo.guardar(ana)
    repo.cambiar_email(ana.id, "nueva@correo.cl")
    repo.cambiar_hash(ana.id, "otro-hash")
    actual = repo.buscar_por_id(ana.id)
    assert actual.email == "nueva@correo.cl"
    assert actual.hash_contrasena == "otro-hash"


def test_cambiar_email_a_uno_ocupado_falla_y_deja_todo_igual(sesion):
    repo = RepositorioCuentaSQL(sesion)
    ana, luis = crear_usuario("ana@correo.cl"), crear_usuario("luis@correo.cl")
    repo.guardar(ana)
    repo.guardar(luis)
    with pytest.raises(EmailYaRegistrado):
        repo.cambiar_email(ana.id, "luis@correo.cl")
    assert repo.buscar_por_id(ana.id).email == "ana@correo.cl"


def test_eliminar_cuenta_borra_todo_lo_de_esa_persona_y_nada_mas(sesion):
    cuentas = RepositorioCuentaSQL(sesion)
    movimientos = RepositorioMovimientosSQL(sesion)
    tokens = RepositorioTokensSQL(sesion)
    intentos = RepositorioIntentosSQL(sesion)
    ana, luis = crear_usuario("ana@correo.cl"), crear_usuario("luis@correo.cl")
    cuentas.guardar(ana)
    cuentas.guardar(luis)
    for dueno in (ana, luis):
        ingreso = Movimiento(
            id=uuid4(),
            usuario_id=dueno.id,
            tipo=TipoMovimiento.INGRESO,
            monto=1000,
            categoria=None,
            descripcion="Sueldo",
            fecha=date(2026, 10, 1),
            creado_en=AHORA,
        )
        propuesta = Confirmacion(
            id=uuid4(),
            usuario_id=dueno.id,
            ingreso_id=ingreso.id,
            categoria=Categoria.INVERSION,
            monto=250,
            estado=EstadoConfirmacion.PENDIENTE,
            creado_en=AHORA,
        )
        movimientos.guardar_ingreso(ingreso, [propuesta])
        _, token = nuevo_token_refresco(dueno.id, AHORA)
        tokens.guardar(token)
    intentos.guardar(RegistroIntentos(clave="clave-ana", fallos=2, primer_fallo=AHORA))

    cuentas.eliminar_cuenta(ana.id, "clave-ana")

    assert cuentas.buscar_por_id(ana.id) is None
    assert movimientos.listar_por_usuario(ana.id) == []
    assert movimientos.listar_confirmaciones_por_usuario(ana.id) == []
    assert intentos.obtener("clave-ana") is None
    assert cuentas.buscar_por_id(luis.id) is not None
    assert len(movimientos.listar_por_usuario(luis.id)) == 1
    assert len(movimientos.listar_confirmaciones_por_usuario(luis.id)) == 1
