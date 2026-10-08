"""Caso de uso: cuánto se asignó, cuánto se gastó y cuánto queda en cada categoría."""

from dataclasses import dataclass
from uuid import UUID

from app.casos_de_uso.puertos import RepositorioMovimientos
from app.dominio.categorias import Categoria
from app.dominio.movimiento import TipoMovimiento, repartir


@dataclass(frozen=True)
class LineaResumen:
    categoria: Categoria
    asignado: int
    gastado: int

    @property
    def disponible(self) -> int:
        """Puede ser negativo: significa que ya te pasaste en esa categoría."""
        return self.asignado - self.gastado


@dataclass(frozen=True)
class Resumen:
    ingresos_total: int
    gastos_total: int
    lineas: tuple[LineaResumen, ...]


def obtener_resumen(usuario_id: UUID, repositorio: RepositorioMovimientos) -> Resumen:
    asignado = {categoria: 0 for categoria in Categoria}
    gastado = {categoria: 0 for categoria in Categoria}
    ingresos_total = 0
    gastos_total = 0

    for movimiento in repositorio.listar_por_usuario(usuario_id):
        if movimiento.tipo is TipoMovimiento.INGRESO:
            ingresos_total += movimiento.monto
            # Cada ingreso se reparte por separado, para que los pesos sobrantes
            # de cada reparto se traten igual que al registrarlo.
            for categoria, parte in repartir(movimiento.monto).items():
                asignado[categoria] += parte
        elif movimiento.categoria is not None:
            gastos_total += movimiento.monto
            gastado[movimiento.categoria] += movimiento.monto

    lineas = tuple(LineaResumen(c, asignado[c], gastado[c]) for c in Categoria)
    return Resumen(ingresos_total, gastos_total, lineas)
