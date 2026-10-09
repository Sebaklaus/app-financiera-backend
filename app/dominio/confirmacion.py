"""Confirmación del reparto (RNF-06). Dominio puro: sin FastAPI ni base de datos.

Regla del informe: el sistema solo PROPONE el reparto. El 25 % de inversión y el 15 % de
estabilidad nunca se aplican sin que la persona los confirme de forma explícita.
"""

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from app.dominio.categorias import Categoria
from app.dominio.errores import ConfirmacionYaDecidida
from app.dominio.movimiento import Movimiento

# Las otras dos partes (necesidades y entretenimiento) no mueven dinero hacia ningún
# producto financiero, así que no piden confirmación.
CATEGORIAS_CON_CONFIRMACION = (Categoria.INVERSION, Categoria.ESTABILIDAD)


class EstadoConfirmacion(str, Enum):
    PENDIENTE = "pendiente"
    CONFIRMADA = "confirmada"
    RECHAZADA = "rechazada"


class Decision(str, Enum):
    CONFIRMAR = "confirmar"
    RECHAZAR = "rechazar"


@dataclass(frozen=True)
class Confirmacion:
    id: UUID
    usuario_id: UUID
    ingreso_id: UUID
    categoria: Categoria
    monto: int  # la parte propuesta, en pesos
    estado: EstadoConfirmacion
    creado_en: datetime
    decidido_en: datetime | None = None


def proponer(
    ingreso: Movimiento, reparto: dict[Categoria, int], ahora: datetime
) -> list[Confirmacion]:
    """Una propuesta pendiente por cada parte que exige confirmación (si la parte es > 0)."""
    return [
        Confirmacion(
            id=uuid4(),
            usuario_id=ingreso.usuario_id,
            ingreso_id=ingreso.id,
            categoria=categoria,
            monto=reparto[categoria],
            estado=EstadoConfirmacion.PENDIENTE,
            creado_en=ahora,
        )
        for categoria in CATEGORIAS_CON_CONFIRMACION
        if reparto[categoria] > 0
    ]


def decidir(confirmacion: Confirmacion, decision: Decision, ahora: datetime) -> Confirmacion:
    """Devuelve la propuesta ya decidida. Solo se puede decidir una vez."""
    if confirmacion.estado is not EstadoConfirmacion.PENDIENTE:
        raise ConfirmacionYaDecidida("Esta propuesta ya fue decidida")
    nuevo_estado = (
        EstadoConfirmacion.CONFIRMADA
        if decision is Decision.CONFIRMAR
        else EstadoConfirmacion.RECHAZADA
    )
    return replace(confirmacion, estado=nuevo_estado, decidido_en=ahora)
