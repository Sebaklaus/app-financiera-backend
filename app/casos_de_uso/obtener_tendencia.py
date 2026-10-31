"""Caso de uso: ingresos y gastos de los últimos meses, para los gráficos del panel (CU-09).

Cada mes se mira por separado y siempre aparecen todos los meses pedidos, también los que no
tienen movimientos (en cero), para que el gráfico no tenga huecos.
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.casos_de_uso.puertos import RepositorioMovimientos
from app.dominio.categorias import Categoria
from app.dominio.errores import MovimientoInvalido
from app.dominio.movimiento import TipoMovimiento
from app.dominio.periodo import Periodo
from app.dominio.reloj import hoy_en_chile

MESES_MAXIMOS = 12


@dataclass(frozen=True)
class MesTendencia:
    periodo: Periodo
    ingresos: int
    gastos: int
    gastos_por_categoria: dict[Categoria, int]

    @property
    def balance(self) -> int:
        """Ingresos menos gastos del mes. Negativo = gastaste más de lo que entró."""
        return self.ingresos - self.gastos


def ultimos_periodos(hasta: Periodo, cantidad: int) -> list[Periodo]:
    """Los `cantidad` meses que terminan en `hasta`, del más antiguo al más reciente."""
    indice_final = hasta.anio * 12 + (hasta.mes - 1)
    periodos = []
    for indice in range(indice_final - cantidad + 1, indice_final + 1):
        periodos.append(Periodo(indice // 12, indice % 12 + 1))
    return periodos


def obtener_tendencia(
    usuario_id: UUID,
    repositorio: RepositorioMovimientos,
    meses: int = 6,
    hoy: date | None = None,
) -> list[MesTendencia]:
    if isinstance(meses, bool) or not isinstance(meses, int) or not 1 <= meses <= MESES_MAXIMOS:
        raise MovimientoInvalido(f"Pide entre 1 y {MESES_MAXIMOS} meses")
    hoy = hoy or hoy_en_chile()
    periodos = ultimos_periodos(Periodo(hoy.year, hoy.month), meses)
    ingresos = {p: 0 for p in periodos}
    gastos = {p: 0 for p in periodos}
    por_categoria = {p: {c: 0 for c in Categoria} for p in periodos}

    for movimiento in repositorio.listar_por_usuario(usuario_id):
        periodo = Periodo(movimiento.fecha.year, movimiento.fecha.month)
        if periodo not in ingresos:
            continue
        if movimiento.tipo is TipoMovimiento.INGRESO:
            ingresos[periodo] += movimiento.monto
        elif movimiento.categoria is not None:
            gastos[periodo] += movimiento.monto
            por_categoria[periodo][movimiento.categoria] += movimiento.monto

    return [MesTendencia(p, ingresos[p], gastos[p], por_categoria[p]) for p in periodos]
