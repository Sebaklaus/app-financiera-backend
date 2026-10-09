"""Ingresos y gastos (HU-28) y sus reglas. Dominio puro: sin FastAPI ni base de datos."""

from dataclasses import astuple, dataclass, replace
from datetime import date, datetime
from enum import Enum
from uuid import UUID

from app.dominio.categorias import Categoria
from app.dominio.distribucion import distribuir
from app.dominio.errores import MovimientoInvalido

MONTO_MAXIMO = 1_000_000_000
DESCRIPCION_MAXIMA = 200


class TipoMovimiento(str, Enum):
    INGRESO = "ingreso"
    GASTO = "gasto"


@dataclass(frozen=True)
class Movimiento:
    id: UUID
    usuario_id: UUID
    tipo: TipoMovimiento
    monto: int  # pesos chilenos enteros
    categoria: Categoria | None  # solo los gastos tienen categoría
    descripcion: str
    fecha: date
    creado_en: datetime


def validar_monto(monto: object) -> int:
    # bool es un int en Python (True == 1): se descarta a propósito.
    if isinstance(monto, bool) or not isinstance(monto, int):
        raise MovimientoInvalido("El monto debe ser un número entero de pesos")
    if monto <= 0:
        raise MovimientoInvalido("El monto debe ser mayor que cero")
    if monto > MONTO_MAXIMO:
        raise MovimientoInvalido("El monto es demasiado grande")
    return monto


def validar_descripcion(descripcion: str) -> str:
    limpia = descripcion.strip()
    if not limpia:
        raise MovimientoInvalido("La descripción no puede estar vacía")
    if len(limpia) > DESCRIPCION_MAXIMA:
        raise MovimientoInvalido(f"La descripción admite hasta {DESCRIPCION_MAXIMA} caracteres")
    return limpia


def validar_fecha(fecha: date, hoy: date) -> date:
    if fecha > hoy:
        raise MovimientoInvalido("La fecha no puede estar en el futuro")
    return fecha


def repartir(monto: int) -> dict[Categoria, int]:
    """Aplica la regla 50/25/15/10 y devuelve cuánto va a cada categoría.

    Usa `distribuir` (el cálculo de siempre). Se lee por posición, que es el orden de la
    regla: necesidades, inversión, estabilidad, entretenimiento. Así este archivo no
    depende de cómo se llamen los campos de `Distribucion`.
    """
    necesidades, inversion, estabilidad, entretenimiento = astuple(distribuir(monto))
    return {
        Categoria.NECESIDADES: necesidades,
        Categoria.INVERSION: inversion,
        Categoria.ESTABILIDAD: estabilidad,
        Categoria.ENTRETENIMIENTO: entretenimiento,
    }


def editar(
    movimiento: Movimiento,
    hoy: date,
    monto: int | None = None,
    categoria: Categoria | None = None,
    descripcion: str | None = None,
    fecha: date | None = None,
) -> Movimiento:
    """Devuelve el movimiento con los cambios pedidos. Lo que viene como None no se toca."""
    if monto is None and categoria is None and descripcion is None and fecha is None:
        raise MovimientoInvalido("Indica al menos un dato para cambiar")
    if categoria is not None:
        if movimiento.tipo is TipoMovimiento.INGRESO:
            raise MovimientoInvalido("Un ingreso no tiene categoría")
        if not isinstance(categoria, Categoria):
            raise MovimientoInvalido("La categoría no es válida")
    return replace(
        movimiento,
        monto=movimiento.monto if monto is None else validar_monto(monto),
        categoria=movimiento.categoria if categoria is None else categoria,
        descripcion=(
            movimiento.descripcion if descripcion is None else validar_descripcion(descripcion)
        ),
        fecha=movimiento.fecha if fecha is None else validar_fecha(fecha, hoy),
    )
