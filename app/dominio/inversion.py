"""Opciones de inversión y derivación a la entidad socia (HU-08 y HU-09). Dominio puro.

La app NO vende, NO custodia y NO mueve dinero: solo muestra opciones que calzan con el perfil
de la persona y la envía a la entidad socia, donde ella completa la operación con sus propias
credenciales. En esta etapa las entidades y las direcciones son SIMULADAS (no hay convenios
firmados). El catálogo es educativo: no promete ni informa rentabilidades.
"""

from dataclasses import dataclass
from enum import Enum

from app.dominio.consentimiento import PerfilRiesgo
from app.dominio.errores import ErrorDeDominio


class Riesgo(str, Enum):
    BAJO = "bajo"
    MEDIO = "medio"
    ALTO = "alto"


class InstrumentoNoEncontrado(ErrorDeDominio):
    """No existe ese instrumento en el catálogo."""


@dataclass(frozen=True)
class EntidadSocia:
    id: str
    nombre: str
    url_simulada: str  # dominio .invalid: reservado, nunca resuelve a un sitio real


@dataclass(frozen=True)
class Instrumento:
    id: str
    nombre: str
    tipo: str
    riesgo: Riesgo
    plazo: str
    liquidez: str
    descripcion: str
    entidad: EntidadSocia


BANCO_SOCIO = EntidadSocia(
    "banco-socio", "Banco socio (simulado)", "https://banco-socio.simulado.invalid/inversiones"
)
AGF_SOCIA = EntidadSocia(
    "agf-socia",
    "Administradora de fondos socia (simulada)",
    "https://agf-socia.simulada.invalid/fondos",
)

CATALOGO: tuple[Instrumento, ...] = (
    Instrumento(
        "cuenta-ahorro",
        "Cuenta de ahorro",
        "Cuenta de ahorro",
        Riesgo.BAJO,
        "Sin plazo fijo",
        "Alta: puedes retirar cuando quieras",
        "Guarda tu dinero en el banco sin compromiso de plazo. Es lo más parecido a tenerlo "
        "a mano, con un riesgo muy bajo.",
        BANCO_SOCIO,
    ),
    Instrumento(
        "deposito-a-plazo",
        "Depósito a plazo",
        "Depósito a plazo",
        Riesgo.BAJO,
        "De 30 días a 1 año",
        "Media: se recupera completo al vencimiento",
        "Prestas tu dinero al banco por un plazo fijo y él te lo devuelve al vencer, con el "
        "interés acordado de antemano.",
        BANCO_SOCIO,
    ),
    Instrumento(
        "fondo-deuda-corto-plazo",
        "Fondo mutuo de deuda de corto plazo",
        "Fondo mutuo",
        Riesgo.BAJO,
        "Desde unos días",
        "Alta: rescate en pocos días hábiles",
        "Reúne dinero de muchas personas para invertir en instrumentos de deuda de corto "
        "plazo. Su valor puede variar un poco; la rentabilidad no está garantizada.",
        AGF_SOCIA,
    ),
    Instrumento(
        "fondo-balanceado",
        "Fondo mutuo balanceado",
        "Fondo mutuo",
        Riesgo.MEDIO,
        "Mediano plazo (1 a 3 años)",
        "Media: rescate en pocos días hábiles",
        "Combina instrumentos de deuda y acciones. Puede subir y bajar de valor; conviene "
        "mantenerlo varios años. La rentabilidad no está garantizada.",
        AGF_SOCIA,
    ),
    Instrumento(
        "fondo-acciones",
        "Fondo mutuo de acciones",
        "Fondo mutuo",
        Riesgo.ALTO,
        "Largo plazo (más de 5 años)",
        "Media: rescate en pocos días hábiles",
        "Invierte sobre todo en acciones. Puede perder valor en el corto plazo y busca "
        "crecer en el largo plazo. La rentabilidad no está garantizada.",
        AGF_SOCIA,
    ),
)

_RIESGOS_POR_PERFIL: dict[PerfilRiesgo, frozenset[Riesgo]] = {
    PerfilRiesgo.CONSERVADOR: frozenset({Riesgo.BAJO}),
    PerfilRiesgo.MODERADO: frozenset({Riesgo.BAJO, Riesgo.MEDIO}),
    PerfilRiesgo.ARRIESGADO: frozenset({Riesgo.BAJO, Riesgo.MEDIO, Riesgo.ALTO}),
}


def es_recomendado(instrumento: Instrumento, perfil: PerfilRiesgo | None) -> bool:
    """Un instrumento calza si su riesgo no supera lo que la persona declaró aceptar."""
    if perfil is None:
        return False
    return instrumento.riesgo in _RIESGOS_POR_PERFIL[perfil]


def buscar_instrumento(instrumento_id: str) -> Instrumento:
    for instrumento in CATALOGO:
        if instrumento.id == instrumento_id:
            return instrumento
    raise InstrumentoNoEncontrado("Ese instrumento no existe")
