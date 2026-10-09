"""Pruebas de la confirmación del reparto (RNF-06): proponer, decidir y no repetir."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.casos_de_uso.decidir_confirmacion import decidir_confirmacion
from app.casos_de_uso.listar_confirmaciones_pendientes import listar_confirmaciones_pendientes
from app.casos_de_uso.registrar_ingreso import registrar_ingreso
from app.dominio.categorias import Categoria
from app.dominio.confirmacion import Decision, EstadoConfirmacion
from app.dominio.errores import ConfirmacionNoEncontrada, ConfirmacionYaDecidida
from tests.dobles import RepositorioEnMemoria

ANA = uuid4()
LUIS = uuid4()


def un_ingreso(repo, monto=100_000, usuario=ANA):
    return registrar_ingreso(usuario, monto, "Sueldo", None, repo)


def por_categoria(confirmaciones):
    return {c.categoria: c for c in confirmaciones}


def test_un_ingreso_propone_confirmar_solo_inversion_y_estabilidad():
    resultado = un_ingreso(RepositorioEnMemoria())
    propuestas = por_categoria(resultado.confirmaciones)
    assert set(propuestas) == {Categoria.INVERSION, Categoria.ESTABILIDAD}
    assert propuestas[Categoria.INVERSION].monto == 25_000
    assert propuestas[Categoria.ESTABILIDAD].monto == 15_000
    assert all(c.estado is EstadoConfirmacion.PENDIENTE for c in resultado.confirmaciones)
    assert all(c.decidido_en is None for c in resultado.confirmaciones)


def test_las_propuestas_quedan_guardadas_junto_al_ingreso():
    repo = RepositorioEnMemoria()
    resultado = un_ingreso(repo)
    assert {c.id for c in resultado.confirmaciones} == set(repo.confirmaciones)
    assert all(c.ingreso_id == resultado.movimiento.id for c in resultado.confirmaciones)


def test_un_ingreso_muy_chico_no_propone_partes_en_cero():
    # Con $1, inversión y estabilidad valen $0: no hay nada que confirmar.
    assert un_ingreso(RepositorioEnMemoria(), monto=1).confirmaciones == []


def test_confirmar_marca_la_propuesta_como_confirmada():
    repo = RepositorioEnMemoria()
    propuesta = un_ingreso(repo).confirmaciones[0]
    ahora = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)
    decidida = decidir_confirmacion(ANA, propuesta.id, Decision.CONFIRMAR, repo, ahora)
    assert decidida.estado is EstadoConfirmacion.CONFIRMADA
    assert decidida.decidido_en == ahora
    assert repo.confirmaciones[propuesta.id].estado is EstadoConfirmacion.CONFIRMADA


def test_rechazar_marca_la_propuesta_como_rechazada():
    repo = RepositorioEnMemoria()
    propuesta = un_ingreso(repo).confirmaciones[0]
    decidida = decidir_confirmacion(ANA, propuesta.id, Decision.RECHAZAR, repo)
    assert decidida.estado is EstadoConfirmacion.RECHAZADA


@pytest.mark.parametrize("segunda", [Decision.CONFIRMAR, Decision.RECHAZAR])
def test_una_decision_no_se_puede_repetir_ni_cambiar(segunda):
    repo = RepositorioEnMemoria()
    propuesta = un_ingreso(repo).confirmaciones[0]
    decidir_confirmacion(ANA, propuesta.id, Decision.CONFIRMAR, repo)
    with pytest.raises(ConfirmacionYaDecidida):
        decidir_confirmacion(ANA, propuesta.id, segunda, repo)
    assert repo.confirmaciones[propuesta.id].estado is EstadoConfirmacion.CONFIRMADA


def test_una_propuesta_que_no_existe_se_rechaza():
    with pytest.raises(ConfirmacionNoEncontrada):
        decidir_confirmacion(ANA, uuid4(), Decision.CONFIRMAR, RepositorioEnMemoria())


def test_nadie_puede_decidir_la_propuesta_de_otra_persona():
    repo = RepositorioEnMemoria()
    propuesta = un_ingreso(repo, usuario=ANA).confirmaciones[0]
    with pytest.raises(ConfirmacionNoEncontrada):
        decidir_confirmacion(LUIS, propuesta.id, Decision.CONFIRMAR, repo)
    assert repo.confirmaciones[propuesta.id].estado is EstadoConfirmacion.PENDIENTE


def test_pendientes_solo_lista_las_no_decididas_y_las_propias():
    repo = RepositorioEnMemoria()
    primera = un_ingreso(repo, usuario=ANA).confirmaciones
    un_ingreso(repo, usuario=LUIS)
    decidir_confirmacion(ANA, primera[0].id, Decision.CONFIRMAR, repo)
    pendientes = listar_confirmaciones_pendientes(ANA, repo)
    assert [c.id for c in pendientes] == [primera[1].id]
