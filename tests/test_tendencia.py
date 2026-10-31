"""Pruebas de la tendencia mensual (sin base de datos)."""

from datetime import date
from uuid import uuid4

import pytest

from app.casos_de_uso.obtener_tendencia import obtener_tendencia, ultimos_periodos
from app.casos_de_uso.registrar_gasto import registrar_gasto
from app.casos_de_uso.registrar_ingreso import registrar_ingreso
from app.dominio.categorias import Categoria
from app.dominio.errores import MovimientoInvalido
from app.dominio.periodo import Periodo
from tests.dobles import RepositorioEnMemoria

ANA = uuid4()
LUIS = uuid4()
HOY = date(2026, 10, 28)


def ingreso(repo, monto, fecha, usuario=ANA):
    return registrar_ingreso(usuario, monto, "Sueldo", fecha, repo, hoy=HOY)


def gasto(repo, monto, categoria, fecha, usuario=ANA):
    return registrar_gasto(usuario, monto, categoria, "Compra", fecha, repo, hoy=HOY)


def test_los_ultimos_periodos_cruzan_el_cambio_de_anio():
    assert ultimos_periodos(Periodo(2026, 2), 4) == [
        Periodo(2025, 11),
        Periodo(2025, 12),
        Periodo(2026, 1),
        Periodo(2026, 2),
    ]


def test_siempre_aparecen_todos_los_meses_aunque_esten_vacios():
    meses = obtener_tendencia(ANA, RepositorioEnMemoria(), meses=3, hoy=HOY)
    assert [str(m.periodo) for m in meses] == ["2026-08", "2026-09", "2026-10"]
    assert all(m.ingresos == 0 and m.gastos == 0 for m in meses)


def test_suma_ingresos_y_gastos_de_cada_mes_por_separado():
    repo = RepositorioEnMemoria()
    ingreso(repo, 100_000, date(2026, 9, 5))
    ingreso(repo, 200_000, date(2026, 10, 5))
    gasto(repo, 30_000, Categoria.NECESIDADES, date(2026, 9, 10))
    gasto(repo, 20_000, Categoria.NECESIDADES, date(2026, 10, 10))
    gasto(repo, 5_000, Categoria.ENTRETENIMIENTO, date(2026, 10, 11))
    septiembre, octubre = obtener_tendencia(ANA, repo, meses=2, hoy=HOY)
    assert (septiembre.ingresos, septiembre.gastos, septiembre.balance) == (100_000, 30_000, 70_000)
    assert (octubre.ingresos, octubre.gastos, octubre.balance) == (200_000, 25_000, 175_000)
    assert octubre.gastos_por_categoria[Categoria.NECESIDADES] == 20_000
    assert octubre.gastos_por_categoria[Categoria.ENTRETENIMIENTO] == 5_000
    assert octubre.gastos_por_categoria[Categoria.INVERSION] == 0


def test_el_balance_puede_ser_negativo():
    repo = RepositorioEnMemoria()
    ingreso(repo, 10_000, date(2026, 10, 1))
    gasto(repo, 15_000, Categoria.NECESIDADES, date(2026, 10, 2))
    assert obtener_tendencia(ANA, repo, meses=1, hoy=HOY)[0].balance == -5_000


def test_los_meses_fuera_de_la_ventana_no_cuentan():
    repo = RepositorioEnMemoria()
    ingreso(repo, 100_000, date(2026, 1, 5))
    meses = obtener_tendencia(ANA, repo, meses=3, hoy=HOY)
    assert sum(m.ingresos for m in meses) == 0


def test_solo_cuenta_lo_propio():
    repo = RepositorioEnMemoria()
    ingreso(repo, 100_000, date(2026, 10, 5), usuario=LUIS)
    assert obtener_tendencia(ANA, repo, meses=1, hoy=HOY)[0].ingresos == 0


@pytest.mark.parametrize("meses", [0, -1, 13, True, "6", None])
def test_cantidad_de_meses_invalida(meses):
    with pytest.raises(MovimientoInvalido):
        obtener_tendencia(ANA, RepositorioEnMemoria(), meses=meses, hoy=HOY)
