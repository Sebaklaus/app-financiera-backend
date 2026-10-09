"""Pruebas de ingresos, gastos y resumen. Usan un repositorio en memoria: sin base de datos."""

from datetime import date
from uuid import uuid4

import pytest

from app.casos_de_uso.decidir_confirmacion import decidir_confirmacion
from app.casos_de_uso.obtener_resumen import obtener_resumen
from app.casos_de_uso.registrar_gasto import registrar_gasto
from app.casos_de_uso.registrar_ingreso import registrar_ingreso
from app.dominio.categorias import Categoria
from app.dominio.confirmacion import Decision
from app.dominio.errores import MovimientoInvalido
from app.dominio.movimiento import TipoMovimiento, repartir
from tests.dobles import RepositorioEnMemoria

HOY = date(2026, 10, 8)
ANA = uuid4()
LUIS = uuid4()


def ingreso(repo, monto=100_000, usuario=ANA, descripcion="Sueldo", fecha=None):
    return registrar_ingreso(usuario, monto, descripcion, fecha, repo, hoy=HOY)


def gasto(repo, monto=1_000, categoria=Categoria.NECESIDADES, usuario=ANA, descripcion="Compra"):
    return registrar_gasto(usuario, monto, categoria, descripcion, None, repo, hoy=HOY)


def lineas_por_categoria(resumen):
    return {linea.categoria: linea for linea in resumen.lineas}


# --- la regla 50/25/15/10 ---------------------------------------------------------------


def test_un_ingreso_exacto_se_reparte_50_25_15_10():
    resultado = ingreso(RepositorioEnMemoria())
    assert resultado.reparto == {
        Categoria.NECESIDADES: 50_000,
        Categoria.INVERSION: 25_000,
        Categoria.ESTABILIDAD: 15_000,
        Categoria.ENTRETENIMIENTO: 10_000,
    }


def test_los_pesos_sobrantes_van_a_necesidades():
    assert repartir(100_001)[Categoria.NECESIDADES] == 50_001


def test_el_reparto_siempre_suma_el_monto():
    for monto in list(range(1, 3_000)) + [999_999, 1_000_000_000]:
        assert sum(repartir(monto).values()) == monto


# --- registrar ingresos -----------------------------------------------------------------


def test_el_ingreso_queda_guardado_como_ingreso_sin_categoria():
    repo = RepositorioEnMemoria()
    resultado = ingreso(repo)
    guardado = repo.movimientos[0]
    assert guardado == resultado.movimiento
    assert guardado.tipo is TipoMovimiento.INGRESO
    assert guardado.categoria is None
    assert guardado.usuario_id == ANA


def test_sin_fecha_se_usa_hoy():
    assert ingreso(RepositorioEnMemoria()).movimiento.fecha == HOY


def test_una_fecha_pasada_es_valida():
    resultado = ingreso(RepositorioEnMemoria(), fecha=date(2026, 9, 1))
    assert resultado.movimiento.fecha == date(2026, 9, 1)


def test_una_fecha_futura_se_rechaza():
    with pytest.raises(MovimientoInvalido):
        ingreso(RepositorioEnMemoria(), fecha=date(2026, 10, 9))


@pytest.mark.parametrize("monto", [0, -1, -5_000, 1_000_000_001, 10.5, "1000", True, None])
def test_montos_invalidos_se_rechazan(monto):
    repo = RepositorioEnMemoria()
    with pytest.raises(MovimientoInvalido):
        ingreso(repo, monto=monto)
    assert repo.movimientos == []  # no se guardó nada
    assert repo.confirmaciones == {}


@pytest.mark.parametrize("descripcion", ["", "   ", "x" * 201])
def test_descripciones_invalidas_se_rechazan(descripcion):
    with pytest.raises(MovimientoInvalido):
        ingreso(RepositorioEnMemoria(), descripcion=descripcion)


def test_la_descripcion_se_recorta():
    resultado = ingreso(RepositorioEnMemoria(), descripcion="  Sueldo  ")
    assert resultado.movimiento.descripcion == "Sueldo"


# --- registrar gastos -------------------------------------------------------------------


def test_el_gasto_queda_guardado_con_su_categoria():
    repo = RepositorioEnMemoria()
    movimiento = gasto(repo, categoria=Categoria.ENTRETENIMIENTO)
    assert movimiento.tipo is TipoMovimiento.GASTO
    assert movimiento.categoria is Categoria.ENTRETENIMIENTO
    assert repo.movimientos == [movimiento]


@pytest.mark.parametrize("categoria", [None, "comida", "necesidades"])
def test_un_gasto_exige_una_categoria_valida(categoria):
    with pytest.raises(MovimientoInvalido):
        registrar_gasto(ANA, 1_000, categoria, "Compra", None, RepositorioEnMemoria(), hoy=HOY)


def test_un_gasto_no_acepta_monto_negativo():
    with pytest.raises(MovimientoInvalido):
        gasto(RepositorioEnMemoria(), monto=-1)


# --- resumen (con la confirmación del reparto) ------------------------------------------


def test_resumen_sin_movimientos_son_cuatro_ceros_en_orden_fijo():
    resumen = obtener_resumen(ANA, RepositorioEnMemoria())
    assert [linea.categoria for linea in resumen.lineas] == list(Categoria)
    for linea in resumen.lineas:
        assert linea.asignado == linea.gastado == linea.disponible == 0
        assert linea.por_confirmar == linea.rechazado == 0
    assert resumen.ingresos_total == resumen.gastos_total == 0


def test_antes_de_confirmar_solo_necesidades_y_entretenimiento_estan_asignados():
    repo = RepositorioEnMemoria()
    ingreso(repo, 100_000)
    lineas = lineas_por_categoria(obtener_resumen(ANA, repo))
    assert lineas[Categoria.NECESIDADES].asignado == 50_000
    assert lineas[Categoria.ENTRETENIMIENTO].asignado == 10_000
    assert lineas[Categoria.INVERSION].asignado == 0
    assert lineas[Categoria.INVERSION].por_confirmar == 25_000
    assert lineas[Categoria.ESTABILIDAD].asignado == 0
    assert lineas[Categoria.ESTABILIDAD].por_confirmar == 15_000


def test_al_confirmar_la_parte_pasa_a_asignada():
    repo = RepositorioEnMemoria()
    resultado = ingreso(repo, 100_000)
    inversion = next(c for c in resultado.confirmaciones if c.categoria is Categoria.INVERSION)
    decidir_confirmacion(ANA, inversion.id, Decision.CONFIRMAR, repo)
    lineas = lineas_por_categoria(obtener_resumen(ANA, repo))
    assert lineas[Categoria.INVERSION].asignado == 25_000
    assert lineas[Categoria.INVERSION].por_confirmar == 0
    assert lineas[Categoria.ESTABILIDAD].por_confirmar == 15_000  # la otra sigue pendiente


def test_al_rechazar_la_parte_queda_sin_apartar():
    repo = RepositorioEnMemoria()
    resultado = ingreso(repo, 100_000)
    estabilidad = next(c for c in resultado.confirmaciones if c.categoria is Categoria.ESTABILIDAD)
    decidir_confirmacion(ANA, estabilidad.id, Decision.RECHAZAR, repo)
    linea = lineas_por_categoria(obtener_resumen(ANA, repo))[Categoria.ESTABILIDAD]
    assert linea.asignado == 0
    assert linea.por_confirmar == 0
    assert linea.rechazado == 15_000


def test_resumen_con_un_ingreso_confirmado_y_un_gasto():
    repo = RepositorioEnMemoria()
    resultado = ingreso(repo, 100_000)
    for confirmacion in resultado.confirmaciones:
        decidir_confirmacion(ANA, confirmacion.id, Decision.CONFIRMAR, repo)
    gasto(repo, 20_000, Categoria.NECESIDADES)
    resumen = obtener_resumen(ANA, repo)
    lineas = lineas_por_categoria(resumen)
    assert resumen.ingresos_total == 100_000
    assert resumen.gastos_total == 20_000
    assert lineas[Categoria.NECESIDADES].disponible == 30_000
    assert lineas[Categoria.INVERSION].disponible == 25_000


def test_pasarse_de_una_categoria_da_disponible_negativo():
    repo = RepositorioEnMemoria()
    ingreso(repo, 100_000)  # entretenimiento: 10.000
    gasto(repo, 12_000, Categoria.ENTRETENIMIENTO)
    linea = lineas_por_categoria(obtener_resumen(ANA, repo))[Categoria.ENTRETENIMIENTO]
    assert linea.disponible == -2_000


def test_cada_ingreso_se_reparte_por_separado():
    repo = RepositorioEnMemoria()
    ingreso(repo, 100_001)
    ingreso(repo, 100_001)
    linea = lineas_por_categoria(obtener_resumen(ANA, repo))[Categoria.NECESIDADES]
    assert linea.asignado == 100_002  # 50.001 + 50.001


def test_nada_se_pierde_asignado_mas_pendiente_mas_rechazado_es_lo_ingresado():
    repo = RepositorioEnMemoria()
    for monto in (1, 7, 99, 100_001, 333_333):
        resultado = ingreso(repo, monto)
        for i, confirmacion in enumerate(resultado.confirmaciones):
            if i == 0:
                decidir_confirmacion(ANA, confirmacion.id, Decision.CONFIRMAR, repo)
            elif i == 1:
                decidir_confirmacion(ANA, confirmacion.id, Decision.RECHAZAR, repo)
    resumen = obtener_resumen(ANA, repo)
    total = sum(linea.asignado + linea.por_confirmar + linea.rechazado for linea in resumen.lineas)
    assert total == resumen.ingresos_total


def test_el_resumen_solo_cuenta_los_movimientos_del_usuario():
    repo = RepositorioEnMemoria()
    ingreso(repo, 100_000, usuario=ANA)
    ingreso(repo, 500_000, usuario=LUIS)
    gasto(repo, 7_000, usuario=LUIS)
    resumen_ana = obtener_resumen(ANA, repo)
    assert resumen_ana.ingresos_total == 100_000
    assert resumen_ana.gastos_total == 0
    assert sum(linea.por_confirmar for linea in resumen_ana.lineas) == 40_000
