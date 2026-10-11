"""Dobles de prueba de la recuperación de contraseña, todo en memoria."""

from dataclasses import replace
from datetime import datetime
from uuid import UUID

from app.dominio.recuperacion import TokenRecuperacion


class RepositorioRecuperacionEnMemoria:
    def __init__(self) -> None:
        self.tokens: dict[UUID, TokenRecuperacion] = {}

    def guardar(self, token: TokenRecuperacion) -> None:
        self.tokens[token.id] = token

    def buscar_por_huella(self, huella: str) -> TokenRecuperacion | None:
        return next((t for t in self.tokens.values() if t.huella == huella), None)

    def ultimo_creado_en(self, usuario_id: UUID) -> datetime | None:
        fechas = [t.creado_en for t in self.tokens.values() if t.usuario_id == usuario_id]
        return max(fechas, default=None)

    def marcar_usado(self, token_id: UUID, ahora: datetime) -> bool:
        actual = self.tokens[token_id]
        if actual.usado_en is not None:
            return False
        self.tokens[token_id] = replace(actual, usado_en=ahora)
        return True

    def invalidar_pendientes(self, usuario_id: UUID, ahora: datetime) -> None:
        for token_id, token in list(self.tokens.items()):
            if token.usuario_id == usuario_id and token.usado_en is None:
                self.tokens[token_id] = replace(token, usado_en=ahora)


class EnviadorEnMemoria:
    def __init__(self) -> None:
        self.enviados: list[tuple[str, str]] = []

    def enviar_recuperacion(self, email: str, token: str) -> None:
        self.enviados.append((email, token))
