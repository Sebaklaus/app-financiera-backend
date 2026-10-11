"""Puerto de la cuenta del usuario: lo que hace falta para ver, corregir y borrar sus datos."""

from typing import Protocol
from uuid import UUID

from app.dominio.usuario import Usuario


class RepositorioCuenta(Protocol):
    def buscar_por_id(self, usuario_id: UUID) -> Usuario | None: ...

    def buscar_por_email(self, email: str) -> Usuario | None: ...

    def cambiar_email(self, usuario_id: UUID, email_nuevo: str) -> None:
        """Lanza EmailYaRegistrado si otra cuenta ya usa ese email."""
        ...

    def cambiar_hash(self, usuario_id: UUID, hash_nuevo: str) -> None: ...

    def eliminar_cuenta(self, usuario_id: UUID, clave_intentos: str) -> None:
        """Borra TODO lo de la persona (movimientos, propuestas, sesiones, intentos, usuario).

        Todo en una sola operación: o se borra todo o nada.
        """
        ...
