"""Pruebas del resumen y del listado por mes (sin base de datos)."""

from datetime import date
from uuid import uuid4

import pytest

from app.casos_de_uso.decidir_confirmacion import decidir_confirmacion
from app.casos_de_uso.listar_movimientos import listar_movimientos
from app.casos_de_uso.obtener_resumen import obtener_resumen
from app.casos_de_uso.registrar_gasto import registrar_gasto
from app.casos_de_uso.registrar_ingreso import registrar_ingreso
from app.dominio.categorias import Categoria
from app.dominio.confirmacion import Decision
from app.dominio.errores import MovimientoInvalido
from app.dominio.periodo import Periodo
from tests.dobles import RepositorioEnMemoria

ANA = uuid4()
LUIS = uuid4()
SEPTIEMBRE = Periodo(2026, 9)
OCTUBRE = Periodo(2026, 10)


def ingreso(repo, monto, fecha, usuario=ANA):
    return registrar_ingreso(usuario, monto, "Sueldo", fecha, repo, hoy=date(2026, 10, 31))


def gasto(repo, monto, categoria, fecha, usuario=ANA):
    return registrar_gasto(usuario, monto, categoria, "Compra", fecha, repo, hoy=date(2026, 10, 31))


def lineas(resumen):
    return {linea.categoria: linea for linea in resumen.lineas}


# --- Periodo ----------------------------------------------------------------------------


def test_un_periodo_se_lee_desde_texto():
    assert Periodo.desde_texto("2026-10") == OCTUBRE
    assert str(Periodo(2026, 3)) == "2026-03"


@pytest.mark.parametrize(
    "texto", ["", "2026", "2026-13", "2026-00", "26-10", "octubre", "2026-1-5", "２０２６-10"]
)
def test_un_mes_mal_escrito_se_rechaza(texto):
    with pytest.raises(MovimientoInvalido):
        Periodo.desde_texto(texto)


def test_un_periodo_contiene_solo_las_fechas_de_su_mes():
    assert OCTUBRE.contiene(date(2026, 10, 1))
    assert OCTUBRE.contiene(date(2026, 10, 31))
    assert not OCTUBRE.contiene(date(2026, 9, 30))
    assert not OCTUBRE.contiene(date(2025, 10, 15))  # mismo mes, otro año


# --- listado ----------------------------------------------------------------------------


def test_listar_un_mes_trae_solo_ese_mes():
    repo = RepositorioEnMemoria()
    ingreso(repo, 100_000, date(2026, 9, 5))
    ingreso(repo, 200_000, date(2026, 10, 5))
    assert len(listar_movimientos(ANA, repo)) == 2
    del_mes = listar_movimientos(ANA, repo, OCTUBRE)
    assert [m.monto for m in del_mes] == [200_000]


# --- resumen ----------------------------------------------------------------------------


def test_sin_periodo_el_resumen_suma_todo():
    repo = RepositorioEnMemoria()
    ingreso(repo, 100_000, date(2026, 9, 5))
    ingreso(repo, 200_000, date(2026, 10, 5))
    assert obtener_resumen(ANA, repo).ingresos_total == 300_000


def test_el_resumen_de_un_mes_ignora_los_demas():
    repo = RepositorioEnMemoria()
    ingreso(repo, 100_000, date(2026, 9, 5))
    ingreso(repo, 200_000, date(2026, 10, 5))
    gasto(repo, 5_000, Categoria.NECESIDADES, date(2026, 9, 6))
    gasto(repo, 9_000, Categoria.NECESIDADES, date(2026, 10, 6))
    sep = obtener_resumen(ANA, repo, SEPTIEMBRE)
    octu = obtener_resumen(ANA, repo, OCTUBRE)
    assert (sep.ingresos_total, sep.gastos_total) == (100_000, 5_000)
    assert (octu.ingresos_total, octu.gastos_total) == (200_000, 9_000)
    assert lineas(sep)[Categoria.NECESIDADES].disponible == 45_000
    assert lineas(octu)[Categoria.NECESIDADES].disponible == 91_000


def test_las_propuestas_se_cuentan_en_el_mes_de_su_ingreso():
    repo = RepositorioEnMemoria()
    ingreso(repo, 100_000, date(2026, 9, 5))
    resultado = ingreso(repo, 200_000, date(2026, 10, 5))
    inversion = next(c for c in resultado.confirmaciones if c.categoria is Categoria.INVERSION)
    decidir_confirmacion(ANA, inversion.id, Decision.CONFIRMAR, repo)
    sep = lineas(obtener_resumen(ANA, repo, SEPTIEMBRE))
    octu = lineas(obtener_resumen(ANA, repo, OCTUBRE))
    assert sep[Categoria.INVERSION].asignado == 0
    assert sep[Categoria.INVERSION].por_confirmar == 25_000
    assert octu[Categoria.INVERSION].asignado == 50_000
    assert octu[Categoria.INVERSION].por_confirmar == 0
    assert octu[Categoria.ESTABILIDAD].por_confirmar == 30_000


def test_un_mes_sin_movimientos_da_ceros():
    repo = RepositorioEnMemoria()
    ingreso(repo, 100_000, date(2026, 10, 5))
    vacio = obtener_resumen(ANA, repo, Periodo(2026, 1))
    assert vacio.ingresos_total == vacio.gastos_total == 0
    assert all(linea.asignado == linea.por_confirmar == 0 for linea in vacio.lineas)


def test_lo_que_sobra_no_pasa_al_mes_siguiente():
    repo = RepositorioEnMemoria()
    ingreso(repo, 100_000, date(2026, 9, 5))
    ingreso(repo, 100_000, date(2026, 10, 5))
    gasto(repo, 40_000, Categoria.NECESIDADES, date(2026, 9, 6))
    assert lineas(obtener_resumen(ANA, repo, OCTUBRE))[Categoria.NECESIDADES].disponible == 50_000


def test_el_resumen_mensual_no_mezcla_personas():
    repo = RepositorioEnMemoria()
    ingreso(repo, 100_000, date(2026, 10, 5), usuario=ANA)
    ingreso(repo, 999_000, date(2026, 10, 5), usuario=LUIS)
    assert obtener_resumen(ANA, repo, OCTUBRE).ingresos_total == 100_000
