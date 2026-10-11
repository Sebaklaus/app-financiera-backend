"""Puertos de la recuperación de contraseña: guardar los tokens y enviar el correo."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.dominio.recuperacion import TokenRecuperacion


class RepositorioRecuperacion(Protocol):
    def guardar(self, token: TokenRecuperacion) -> None: ...

    def buscar_por_huella(self, huella: str) -> TokenRecuperacion | None: ...

    def ultimo_creado_en(self, usuario_id: UUID) -> datetime | None:
        """Cuándo se pidió el último token de esa persona (None si nunca)."""
        ...

    def marcar_usado(self, token_id: UUID, ahora: datetime) -> bool:
        """Lo marca solo si seguía sin usar. False si otro llegó primero."""
        ...

    def invalidar_pendientes(self, usuario_id: UUID, ahora: datetime) -> None:
        """Deja sin uso los tokens anteriores aún vigentes: solo sirve el último enviado."""
        ...


class EnviadorCorreo(Protocol):
    def enviar_recuperacion(self, email: str, token: str) -> None: ...
