"""Casos de uso de consentimientos y perfil de riesgo (HU-03)."""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.casos_de_uso.puertos_consentimientos import RepositorioConsentimientos
from app.dominio.consentimiento import (
    VERSION_TEXTOS,
    CambioVacio,
    Consentimiento,
    PerfilDeclarado,
    PerfilRiesgo,
    TipoConsentimiento,
    estado_actual,
    pendientes,
    validar_cambio,
)


@dataclass(frozen=True)
class EstadoConsentimientos:
    version: str
    actuales: dict[TipoConsentimiento, Consentimiento]
    pendientes: list[TipoConsentimiento]


def obtener_consentimientos(
    usuario_id: UUID, repositorio: RepositorioConsentimientos
) -> EstadoConsentimientos:
    historial = repositorio.listar_consentimientos(usuario_id)
    return EstadoConsentimientos(
        version=VERSION_TEXTOS,
        actuales=estado_actual(historial),
        pendientes=pendientes(historial),
    )


def registrar_consentimientos(
    usuario_id: UUID,
    cambios: dict[TipoConsentimiento, bool],
    repositorio: RepositorioConsentimientos,
    ahora: datetime | None = None,
) -> EstadoConsentimientos:
    """Otorga o retira consentimientos. Solo se anota lo que de verdad cambia."""
    if not cambios:
        raise CambioVacio("Indica al menos un consentimiento")
    ahora = ahora or datetime.now(timezone.utc)
    for tipo, otorgado in cambios.items():
        validar_cambio(tipo, otorgado)
    actuales = estado_actual(repositorio.listar_consentimientos(usuario_id))
    nuevos = [
        Consentimiento(uuid4(), usuario_id, tipo, otorgado, VERSION_TEXTOS, ahora)
        for tipo, otorgado in cambios.items()
        if tipo not in actuales or actuales[tipo].otorgado != otorgado
    ]
    if nuevos:
        repositorio.guardar_consentimientos(nuevos)
    return obtener_consentimientos(usuario_id, repositorio)


def declarar_perfil(
    usuario_id: UUID,
    perfil: PerfilRiesgo,
    repositorio: RepositorioConsentimientos,
    ahora: datetime | None = None,
) -> PerfilDeclarado:
    declarado = PerfilDeclarado(usuario_id, perfil, ahora or datetime.now(timezone.utc))
    repositorio.guardar_perfil(declarado)
    return declarado


def obtener_perfil(
    usuario_id: UUID, repositorio: RepositorioConsentimientos
) -> PerfilDeclarado | None:
    return repositorio.obtener_perfil(usuario_id)
