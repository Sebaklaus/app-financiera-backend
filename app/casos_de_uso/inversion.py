"""Casos de uso de la inversión: ver opciones según el perfil y derivar a la entidad socia."""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.casos_de_uso.auditoria import registrar_evento
from app.casos_de_uso.puertos_auditoria import RepositorioEventos
from app.casos_de_uso.puertos_consentimientos import RepositorioConsentimientos
from app.dominio.auditoria import TipoEvento
from app.dominio.consentimiento import PerfilRiesgo
from app.dominio.inversion import (
    CATALOGO,
    EntidadSocia,
    Instrumento,
    buscar_instrumento,
    es_recomendado,
)
from app.dominio.movimiento import validar_monto


@dataclass(frozen=True)
class OpcionDeInversion:
    instrumento: Instrumento
    recomendado: bool


@dataclass(frozen=True)
class OpcionesDeInversion:
    perfil: PerfilRiesgo | None
    opciones: tuple[OpcionDeInversion, ...]


@dataclass(frozen=True)
class Derivacion:
    referencia: UUID
    instrumento: Instrumento
    entidad: EntidadSocia
    monto: int | None
    creada_en: datetime


def listar_opciones(
    usuario_id: UUID, consentimientos: RepositorioConsentimientos
) -> OpcionesDeInversion:
    declarado = consentimientos.obtener_perfil(usuario_id)
    perfil = None if declarado is None else declarado.perfil
    # Primero lo que calza con el perfil; dentro de cada grupo se respeta el orden del catálogo.
    ordenadas = sorted(
        (OpcionDeInversion(i, es_recomendado(i, perfil)) for i in CATALOGO),
        key=lambda o: not o.recomendado,
    )
    return OpcionesDeInversion(perfil, tuple(ordenadas))


def derivar_a_entidad_socia(
    usuario_id: UUID,
    instrumento_id: str,
    monto: int | None,
    eventos: RepositorioEventos,
    ip: str | None = None,
    ahora: datetime | None = None,
) -> Derivacion:
    """Anota que la persona pidió ir a la entidad socia. El dinero no pasa por la app.

    Si el monto viene, solo orienta (cuánto pensaba invertir); no se guarda ni se mueve.
    """
    instrumento = buscar_instrumento(instrumento_id)
    if monto is not None:
        validar_monto(monto)
    momento = ahora or datetime.now(timezone.utc)
    registrar_evento(eventos, TipoEvento.DERIVACION_INVERSION, usuario_id, ip, momento)
    return Derivacion(uuid4(), instrumento, instrumento.entidad, monto, momento)
