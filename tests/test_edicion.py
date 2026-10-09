"""Pruebas de editar y borrar movimientos (lógica, sin base de datos)."""

from datetime import date
from uuid import uuid4

import pytest

from app.casos_de_uso.decidir_confirmacion import decidir_confirmacion
from app.casos_de_uso.editar_movimiento import editar_movimiento
from app.casos_de_uso.eliminar_movimiento import eliminar_movimiento
from app.casos_de_uso.obtener_resumen import obtener_resumen
from app.casos_de_uso.registrar_gasto import registrar_gasto
from app.casos_de_uso.registrar_ingreso import registrar_ingreso
from app.dominio.categorias import Categoria
from app.dominio.confirmacion import Decision
from app.dominio.errores import EdicionNoPermitida, MovimientoInvalido, MovimientoNoEncontrado
from tests.dobles import RepositorioEnMemoria

ANA = uuid4()
LUIS = uuid4()
HOY = date(2026, 10, 9)


def un_gasto(repo, usuario=ANA):
    return registrar_gasto(usuario, 5_000, Categoria.NECESIDADES, "Super", None, repo)


def un_ingreso(repo, usuario=ANA):
    return registrar_ingreso(usuario, 100_000, "Sueldo", None, repo)


def linea(repo, categoria, usuario=ANA):
    resumen = obtener_resumen(usuario, repo)
    return next(x for x in resumen.lineas if x.categoria is categoria)


# --- editar gastos ----------------------------------------------------------------------


def test_editar_un_gasto_cambia_solo_lo_pedido():
    repo = RepositorioEnMemoria()
    gasto = un_gasto(repo)
    resultado = editar_movimiento(ANA, gasto.id, repo, monto=7_000, hoy=HOY)
    assert resultado.movimiento.monto == 7_000
    assert resultado.movimiento.descripcion == "Super"
    assert resultado.movimiento.categoria is Categoria.NECESIDADES
    assert resultado.pendientes == []
    assert repo.buscar_movimiento(ANA, gasto.id).monto == 7_000


def test_editar_la_categoria_de_un_gasto_mueve_el_gasto_en_el_resumen():
    repo = RepositorioEnMemoria()
    gasto = un_gasto(repo)
    editar_movimiento(ANA, gasto.id, repo, categoria=Categoria.ENTRETENIMIENTO, hoy=HOY)
    assert linea(repo, Categoria.NECESIDADES).gastado == 0
    assert linea(repo, Categoria.ENTRETENIMIENTO).gastado == 5_000


def test_editar_sin_ningun_dato_se_rechaza():
    repo = RepositorioEnMemoria()
    gasto = un_gasto(repo)
    with pytest.raises(MovimientoInvalido):
        editar_movimiento(ANA, gasto.id, repo, hoy=HOY)


def test_editar_valida_igual_que_al_crear():
    repo = RepositorioEnMemoria()
    gasto = un_gasto(repo)
    with pytest.raises(MovimientoInvalido):
        editar_movimiento(ANA, gasto.id, repo, monto=-1, hoy=HOY)
    with pytest.raises(MovimientoInvalido):
        editar_movimiento(ANA, gasto.id, repo, descripcion="   ", hoy=HOY)
    with pytest.raises(MovimientoInvalido):
        editar_movimiento(ANA, gasto.id, repo, fecha=date(2999, 1, 1), hoy=HOY)


def test_un_ingreso_no_acepta_categoria():
    repo = RepositorioEnMemoria()
    ingreso = un_ingreso(repo).movimiento
    with pytest.raises(MovimientoInvalido):
        editar_movimiento(ANA, ingreso.id, repo, categoria=Categoria.INVERSION, hoy=HOY)


def test_no_se_edita_lo_ajeno_ni_lo_inexistente():
    repo = RepositorioEnMemoria()
    gasto = un_gasto(repo, usuario=ANA)
    with pytest.raises(MovimientoNoEncontrado):
        editar_movimiento(LUIS, gasto.id, repo, monto=1, hoy=HOY)
    with pytest.raises(MovimientoNoEncontrado):
        editar_movimiento(ANA, uuid4(), repo, monto=1, hoy=HOY)
    assert repo.buscar_movimiento(ANA, gasto.id).monto == 5_000


# --- editar ingresos --------------------------------------------------------------------


def test_cambiar_el_texto_de_un_ingreso_no_toca_sus_propuestas():
    repo = RepositorioEnMemoria()
    resultado = un_ingreso(repo)
    editado = editar_movimiento(
        ANA, resultado.movimiento.id, repo, descripcion="Sueldo oct", hoy=HOY
    )
    assert editado.movimiento.descripcion == "Sueldo oct"
    assert {c.id for c in editado.pendientes} == {c.id for c in resultado.confirmaciones}


def test_cambiar_el_monto_con_todo_pendiente_vuelve_a_proponer_el_reparto():
    repo = RepositorioEnMemoria()
    resultado = un_ingreso(repo)
    editado = editar_movimiento(ANA, resultado.movimiento.id, repo, monto=200_000, hoy=HOY)
    montos = {c.categoria: c.monto for c in editado.pendientes}
    assert montos == {Categoria.INVERSION: 50_000, Categoria.ESTABILIDAD: 30_000}
    # las propuestas viejas desaparecen: quedan solo las dos nuevas
    assert len(repo.listar_confirmaciones_por_usuario(ANA)) == 2
    assert linea(repo, Categoria.NECESIDADES).asignado == 100_000


def test_no_se_cambia_el_monto_si_ya_se_decidio_una_parte():
    repo = RepositorioEnMemoria()
    resultado = un_ingreso(repo)
    primera = resultado.confirmaciones[0]
    decidir_confirmacion(ANA, primera.id, Decision.CONFIRMAR, repo)
    with pytest.raises(EdicionNoPermitida):
        editar_movimiento(ANA, resultado.movimiento.id, repo, monto=200_000, hoy=HOY)
    assert repo.buscar_movimiento(ANA, resultado.movimiento.id).monto == 100_000


def test_con_una_parte_decidida_si_se_puede_corregir_el_texto():
    repo = RepositorioEnMemoria()
    resultado = un_ingreso(repo)
    decidir_confirmacion(ANA, resultado.confirmaciones[0].id, Decision.CONFIRMAR, repo)
    editado = editar_movimiento(ANA, resultado.movimiento.id, repo, descripcion="Sueldo", hoy=HOY)
    assert len(editado.pendientes) == 1  # la otra parte sigue esperando


# --- borrar -----------------------------------------------------------------------------


def test_borrar_un_gasto_lo_quita_del_resumen():
    repo = RepositorioEnMemoria()
    gasto = un_gasto(repo)
    eliminar_movimiento(ANA, gasto.id, repo)
    assert repo.listar_por_usuario(ANA) == []
    assert linea(repo, Categoria.NECESIDADES).gastado == 0


def test_borrar_un_ingreso_borra_tambien_sus_propuestas():
    repo = RepositorioEnMemoria()
    resultado = un_ingreso(repo)
    decidir_confirmacion(ANA, resultado.confirmaciones[0].id, Decision.CONFIRMAR, repo)
    eliminar_movimiento(ANA, resultado.movimiento.id, repo)
    assert repo.listar_por_usuario(ANA) == []
    assert repo.listar_confirmaciones_por_usuario(ANA) == []


def test_no_se_borra_lo_ajeno_ni_lo_inexistente():
    repo = RepositorioEnMemoria()
    gasto = un_gasto(repo, usuario=ANA)
    with pytest.raises(MovimientoNoEncontrado):
        eliminar_movimiento(LUIS, gasto.id, repo)
    with pytest.raises(MovimientoNoEncontrado):
        eliminar_movimiento(ANA, uuid4(), repo)
    assert len(repo.listar_por_usuario(ANA)) == 1
