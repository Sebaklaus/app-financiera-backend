"""Consentimientos y perfil de riesgo (HU-03). Dominio puro.

La Ley 21.719 exige consentimiento libre, informado y específico. Por eso cada uno se pide y
se guarda POR SEPARADO, y nunca se borra el historial: retirar un consentimiento agrega una
fila nueva ("otorgado = falso"), así siempre se puede demostrar qué aceptó la persona y cuándo.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID

from app.dominio.errores import ErrorDeDominio

# Cambia cuando cambian los textos legales: así se sabe qué versión aceptó cada persona.
VERSION_TEXTOS = "2026-10"


class TipoConsentimiento(str, Enum):
    TERMINOS_Y_PRIVACIDAD = "terminos_y_privacidad"
    DATOS_FINANCIEROS = "datos_financieros"
    COMUNICACIONES = "comunicaciones"


OBLIGATORIOS = (TipoConsentimiento.TERMINOS_Y_PRIVACIDAD, TipoConsentimiento.DATOS_FINANCIEROS)


class PerfilRiesgo(str, Enum):
    CONSERVADOR = "conservador"
    MODERADO = "moderado"
    ARRIESGADO = "arriesgado"


class ConsentimientoObligatorio(ErrorDeDominio):
    """Un consentimiento necesario para usar la app no se puede retirar sin cerrar la cuenta."""


class CambioVacio(ErrorDeDominio):
    """No se indicó ningún consentimiento que cambiar."""


@dataclass(frozen=True)
class Consentimiento:
    id: UUID
    usuario_id: UUID
    tipo: TipoConsentimiento
    otorgado: bool
    version: str
    creado_en: datetime


@dataclass(frozen=True)
class PerfilDeclarado:
    usuario_id: UUID
    perfil: PerfilRiesgo
    actualizado_en: datetime


def estado_actual(historial: list[Consentimiento]) -> dict[TipoConsentimiento, Consentimiento]:
    """El último registro de cada tipo. Ante empate de hora, gana el que se guardó después."""
    actual: dict[TipoConsentimiento, Consentimiento] = {}
    for registro in historial:
        previo = actual.get(registro.tipo)
        if previo is None or registro.creado_en >= previo.creado_en:
            actual[registro.tipo] = registro
    return actual


def pendientes(historial: list[Consentimiento]) -> list[TipoConsentimiento]:
    """Los consentimientos obligatorios que la persona todavía no ha otorgado."""
    actual = estado_actual(historial)
    return [t for t in OBLIGATORIOS if t not in actual or not actual[t].otorgado]


def validar_cambio(tipo: TipoConsentimiento, otorgado: bool) -> None:
    if not otorgado and tipo in OBLIGATORIOS:
        raise ConsentimientoObligatorio(
            "Este consentimiento es necesario para usar la app. "
            "Si quieres retirarlo, elimina tu cuenta."
        )
