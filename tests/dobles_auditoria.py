"""Dobles de prueba de la bitácora de seguridad."""

from uuid import UUID

from app.dominio.auditoria import EventoSeguridad


class RepositorioEventosEnMemoria:
    def __init__(self) -> None:
        self.eventos: list[EventoSeguridad] = []

    def guardar(self, evento: EventoSeguridad) -> None:
        self.eventos.append(evento)

    def listar_por_usuario(self, usuario_id: UUID, limite: int) -> list[EventoSeguridad]:
        propios = [e for e in self.eventos if e.usuario_id == usuario_id]
        return sorted(propios, key=lambda e: e.creado_en, reverse=True)[:limite]


class RepositorioEventosRoto:
    def guardar(self, evento: EventoSeguridad) -> None:
        raise RuntimeError("la base no responde")

    def listar_por_usuario(self, usuario_id: UUID, limite: int) -> list[EventoSeguridad]:
        raise RuntimeError("la base no responde")
