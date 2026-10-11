"""Casos de uso de la bitácora de seguridad."""

import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.casos_de_uso.puertos_auditoria import RepositorioEventos
from app.dominio.auditoria import EventoSeguridad, TipoEvento, huella_ip

_registro = logging.getLogger(__name__)
LIMITE_ACTIVIDAD = 50


def registrar_evento(
    repositorio: RepositorioEventos,
    tipo: TipoEvento,
    usuario_id: UUID | None = None,
    ip: str | None = None,
    ahora: datetime | None = None,
) -> None:
    """Anota el evento. Si la bitácora falla, NO se rompe la operación de la persona.

    Es como el cuaderno de la portería: si se le acaba la tinta, igual se deja pasar a la gente,
    pero queda un aviso en el registro del servidor para arreglarlo.
    """
    try:
        repositorio.guardar(
            EventoSeguridad(uuid4(), tipo, usuario_id, huella_ip(ip), ahora or _ahora())
        )
    except Exception:
        _registro.exception("No se pudo registrar el evento de seguridad %s", tipo.value)


def listar_actividad(
    usuario_id: UUID, repositorio: RepositorioEventos, limite: int = LIMITE_ACTIVIDAD
) -> list[EventoSeguridad]:
    return repositorio.listar_por_usuario(usuario_id, limite)


def _ahora() -> datetime:
    return datetime.now(timezone.utc)
