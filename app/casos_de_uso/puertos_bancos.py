"""Puertos de la conexión bancaria: dónde se guarda el enlace y quién consulta al banco."""

from typing import Protocol
from uuid import UUID

from app.dominio.banco import CuentaBancaria, MovimientoBancario


class RepositorioEnlaces(Protocol):
    def guardar(self, usuario_id: UUID, link_token: str) -> None:
        """Guarda (o reemplaza) el enlace de esa persona."""
        ...

    def obtener(self, usuario_id: UUID) -> str | None:
        """El enlace en claro, o None si no hay. Nunca sale de la capa de casos de uso."""
        ...

    def eliminar(self, usuario_id: UUID) -> bool:
        """True si había un enlace y se borró."""
        ...


class ProveedorBancario(Protocol):
    def listar_cuentas(self, link_token: str) -> list[CuentaBancaria]: ...

    def listar_movimientos(self, link_token: str, cuenta_id: str) -> list[MovimientoBancario]: ...
