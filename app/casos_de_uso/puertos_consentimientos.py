"""Puerto de consentimientos y perfil de riesgo."""

from typing import Protocol
from uuid import UUID

from app.dominio.consentimiento import Consentimiento, PerfilDeclarado


class RepositorioConsentimientos(Protocol):
    def guardar_consentimientos(self, registros: list[Consentimiento]) -> None:
        """Agrega filas al historial (todas juntas o ninguna). Nunca modifica las anteriores."""
        ...

    def listar_consentimientos(self, usuario_id: UUID) -> list[Consentimiento]:
        """El historial completo de ESA persona, del más antiguo al más reciente."""
        ...

    def obtener_perfil(self, usuario_id: UUID) -> PerfilDeclarado | None: ...

    def guardar_perfil(self, perfil: PerfilDeclarado) -> None:
        """Crea o reemplaza el perfil de esa persona."""
        ...
