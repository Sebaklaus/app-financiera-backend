"""Puertos: lo que los casos de uso NECESITAN, descrito como contrato.

Los casos de uso piden "algo que sepa guardar usuarios" sin saber si es PostgreSQL o una
lista en memoria. Los adaptadores (capa de afuera) cumplen estos contratos.
"""

from typing import Protocol
from uuid import UUID

from app.dominio.usuario import Usuario


class RepositorioUsuarios(Protocol):
    def buscar_por_email(self, email: str) -> Usuario | None: ...

    def guardar(self, usuario: Usuario) -> None: ...


class HasheadorContrasenas(Protocol):
    def hashear(self, contrasena: str) -> str: ...

    def verificar(self, contrasena: str, hash_guardado: str) -> bool: ...


class EmisorTokens(Protocol):
    """Fabrica y lee los 'brazaletes' (tokens de acceso)."""

    segundos_de_vida: int

    def emitir(self, usuario_id: UUID) -> str: ...

    def leer(self, token: str) -> UUID:
        """Devuelve el id del usuario o lanza TokenInvalido."""
        ...
