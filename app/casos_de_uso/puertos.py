"""Puertos: lo que los casos de uso NECESITAN, descrito como contrato.

Los casos de uso piden "algo que sepa guardar usuarios" sin saber si es PostgreSQL o una
lista en memoria. Los adaptadores (capa de afuera) cumplen estos contratos.
"""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.dominio.confirmacion import Confirmacion
from app.dominio.movimiento import Movimiento
from app.dominio.token_refresco import TokenRefresco
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


class RepositorioMovimientos(Protocol):
    def guardar(self, movimiento: Movimiento) -> None:
        """Guarda un gasto."""
        ...

    def guardar_ingreso(self, ingreso: Movimiento, confirmaciones: list[Confirmacion]) -> None:
        """Guarda el ingreso y sus propuestas de confirmación juntos: o todo o nada."""
        ...

    def listar_por_usuario(self, usuario_id: UUID) -> list[Movimiento]:
        """Los movimientos de ESE usuario, el más reciente primero."""
        ...

    def listar_confirmaciones_por_usuario(self, usuario_id: UUID) -> list[Confirmacion]:
        """Las propuestas de ESE usuario, la más reciente primero."""
        ...

    def buscar_confirmacion(self, usuario_id: UUID, confirmacion_id: UUID) -> Confirmacion | None:
        """None si no existe o si pertenece a otra persona."""
        ...

    def actualizar_confirmacion(self, confirmacion: Confirmacion) -> None:
        """Guarda la decisión. Lanza ConfirmacionYaDecidida si ya estaba decidida."""
        ...

    def buscar_movimiento(self, usuario_id: UUID, movimiento_id: UUID) -> Movimiento | None:
        """None si no existe o si pertenece a otra persona."""
        ...

    def actualizar_movimiento(
        self, movimiento: Movimiento, propuestas: list[Confirmacion] | None = None
    ) -> None:
        """Guarda los cambios. Si vienen `propuestas`, reemplazan a las pendientes del ingreso.

        Todo en una sola operación: o se guarda todo o nada.
        """
        ...

    def eliminar_movimiento(self, usuario_id: UUID, movimiento_id: UUID) -> bool:
        """Borra el movimiento (y las propuestas de un ingreso). False si no era de esa persona."""
        ...


class RepositorioTokensRefresco(Protocol):
    def guardar(self, token: TokenRefresco) -> None: ...

    def buscar_por_huella(self, huella: str) -> TokenRefresco | None: ...

    def revocar(self, token_id: UUID, ahora: datetime) -> bool:
        """Revoca solo si seguía vigente. False si ya estaba revocado (otro llegó primero)."""
        ...

    def revocar_todos_de_usuario(self, usuario_id: UUID, ahora: datetime) -> None: ...
