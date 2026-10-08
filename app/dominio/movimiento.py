"""Ingresos y gastos (HU-28) y sus reglas. Dominio puro: sin FastAPI ni base de datos."""

from dataclasses import astuple, dataclass
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
