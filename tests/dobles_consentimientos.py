"""Doble de prueba de consentimientos: todo en memoria."""

from uuid import UUID

from app.dominio.consentimiento import Consentimiento, PerfilDeclarado


class RepositorioConsentimientosEnMemoria:
    def __init__(self) -> None:
        self.historial: list[Consentimiento] = []
        self.perfiles: dict[UUID, PerfilDeclarado] = {}

    def guardar_consentimientos(self, registros: list[Consentimiento]) -> None:
        self.historial.extend(registros)

    def listar_consentimientos(self, usuario_id: UUID) -> list[Consentimiento]:
        return [r for r in self.historial if r.usuario_id == usuario_id]

    def obtener_perfil(self, usuario_id: UUID) -> PerfilDeclarado | None:
        return self.perfiles.get(usuario_id)

    def guardar_perfil(self, perfil: PerfilDeclarado) -> None:
        self.perfiles[perfil.usuario_id] = perfil
