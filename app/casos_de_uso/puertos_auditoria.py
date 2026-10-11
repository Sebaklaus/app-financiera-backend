"""Puerto de la bitácora de eventos de seguridad."""

from typing import Protocol
from uuid import UUID

from app.dominio.auditoria import EventoSeguridad


class RepositorioEventos(Protocol):
    def guardar(self, evento: EventoSeguridad) -> None: ...

    def listar_por_usuario(self, usuario_id: UUID, limite: int) -> list[EventoSeguridad]:
        """Los eventos de ESA persona, el más reciente primero."""
        ...
