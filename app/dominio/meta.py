"""Metas de ahorro (CU-08) y sus aportes. Dominio puro: sin FastAPI ni base de datos.

Una meta es un objetivo con nombre y monto (por ejemplo, "Viaje" por $500.000). Los aportes
son anotaciones de cuánto se ha apartado para esa meta. La aplicación NUNCA mueve dinero:
los aportes solo llevan la cuenta de lo que la persona dice haber apartado.
"""

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from app.dominio.errores import MetaInvalida
from app.dominio.movimiento import MONTO_MAXIMO

NOMBRE_MAXIMO = 80


@dataclass(frozen=True)
class MetaAhorro:
    id: UUID
    usuario_id: UUID
    nombre: str
    monto_objetivo: int  # pesos chilenos enteros
    fecha_limite: date | None
    creada_en: datetime


@dataclass(frozen=True)
class Aporte:
    id: UUID
    meta_id: UUID
    usuario_id: UUID
    monto: int  # pesos chilenos enteros
    fecha: date
    creado_en: datetime


@dataclass(frozen=True)
class ProgresoMeta:
    meta: MetaAhorro
    ahorrado: int
    falta: int  # nunca negativo: si te pasaste, es 0
    porcentaje: int  # de 0 a 100 (se redondea hacia abajo y se detiene en 100)
    cumplida: bool


def validar_nombre(nombre: str) -> str:
    limpio = nombre.strip()
    if not limpio:
        raise MetaInvalida("El nombre de la meta no puede estar vacío")
    if len(limpio) > NOMBRE_MAXIMO:
        raise MetaInvalida(f"El nombre admite hasta {NOMBRE_MAXIMO} caracteres")
    return limpio


def validar_monto(monto: object) -> int:
    # bool es un int en Python (True == 1): se descarta a propósito.
    if isinstance(monto, bool) or not isinstance(monto, int):
        raise MetaInvalida("El monto debe ser un número entero de pesos")
    if monto <= 0:
        raise MetaInvalida("El monto debe ser mayor que cero")
    if monto > MONTO_MAXIMO:
        raise MetaInvalida("El monto es demasiado grande")
    return monto


def validar_fecha_limite(fecha: date | None, hoy: date) -> date | None:
    if fecha is not None and fecha < hoy:
        raise MetaInvalida("La fecha límite no puede estar en el pasado")
    return fecha


def validar_fecha_aporte(fecha: date, hoy: date) -> date:
    if fecha > hoy:
        raise MetaInvalida("La fecha del aporte no puede estar en el futuro")
    return fecha


def calcular_progreso(meta: MetaAhorro, ahorrado: int) -> ProgresoMeta:
    """Cuánto se lleva ahorrado respecto del objetivo."""
    return ProgresoMeta(
        meta=meta,
        ahorrado=ahorrado,
        falta=max(0, meta.monto_objetivo - ahorrado),
        porcentaje=min(100, ahorrado * 100 // meta.monto_objetivo),
        cumplida=ahorrado >= meta.monto_objetivo,
    )
