"""Casos de uso de la sesión: abrirla, renovarla y cerrarla (HU-02)."""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from app.casos_de_uso.puertos import EmisorTokens, RepositorioTokensRefresco
from app.dominio.errores import TokenInvalido
from app.dominio.token_refresco import calcular_huella, nuevo_token_refresco

MENSAJE_SESION_INVALIDA = "Sesión inválida o vencida: inicia sesión de nuevo"


@dataclass(frozen=True)
class ParDeTokens:
    acceso: str  # dura 15 minutos
    refresco: str  # dura 30 días y se cambia cada vez que se usa
    expira_en: int  # segundos de vida del token de acceso


def abrir_sesion(
    usuario_id: UUID,
    repositorio: RepositorioTokensRefresco,
    emisor: EmisorTokens,
    ahora: datetime | None = None,
) -> ParDeTokens:
    ahora = ahora or datetime.now(timezone.utc)
    token, registro = nuevo_token_refresco(usuario_id, ahora)
    repositorio.guardar(registro)
    return ParDeTokens(emisor.emitir(usuario_id), token, emisor.segundos_de_vida)


def renovar_sesion(
    token_refresco: str,
    repositorio: RepositorioTokensRefresco,
    emisor: EmisorTokens,
    ahora: datetime | None = None,
) -> ParDeTokens:
    """Cambia un token de refresco por un par nuevo. El viejo queda inservible.

    Si alguien presenta un token que YA se usó, es señal de que se copió: se cierran todas
    las sesiones de esa persona por seguridad.
    """
    ahora = ahora or datetime.now(timezone.utc)
    guardado = repositorio.buscar_por_huella(calcular_huella(token_refresco))
    if guardado is None:
        raise TokenInvalido(MENSAJE_SESION_INVALIDA)
    if guardado.revocado_en is not None:
        repositorio.revocar_todos_de_usuario(guardado.usuario_id, ahora)
        raise TokenInvalido(MENSAJE_SESION_INVALIDA)
    if not guardado.esta_vigente(ahora):
        raise TokenInvalido(MENSAJE_SESION_INVALIDA)
    if not repositorio.revocar(guardado.id, ahora):
        # Dos peticiones usaron el mismo token a la vez: solo una puede ganar.
        repositorio.revocar_todos_de_usuario(guardado.usuario_id, ahora)
        raise TokenInvalido(MENSAJE_SESION_INVALIDA)
    return abrir_sesion(guardado.usuario_id, repositorio, emisor, ahora)


def cerrar_sesion(
    token_refresco: str,
    repositorio: RepositorioTokensRefresco,
    ahora: datetime | None = None,
) -> None:
    """Logout. No avisa si el token no existía: cerrar una sesión ya cerrada no es un error."""
    ahora = ahora or datetime.now(timezone.utc)
    guardado = repositorio.buscar_por_huella(calcular_huella(token_refresco))
    if guardado is not None and guardado.revocado_en is None:
        repositorio.revocar(guardado.id, ahora)


def cerrar_todas_las_sesiones(
    usuario_id: UUID,
    repositorio: RepositorioTokensRefresco,
    ahora: datetime | None = None,
) -> None:
    repositorio.revocar_todos_de_usuario(usuario_id, ahora or datetime.now(timezone.utc))
