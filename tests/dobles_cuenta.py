"""Doble de prueba de la cuenta: usuarios en memoria."""

from dataclasses import replace
from uuid import UUID

from app.dominio.errores import EmailYaRegistrado
from app.dominio.usuario import Usuario


class RepositorioCuentaEnMemoria:
    def __init__(self, *usuarios: Usuario) -> None:
        self.usuarios: dict[UUID, Usuario] = {u.id: u for u in usuarios}
        self.claves_borradas: list[str] = []

    def buscar_por_id(self, usuario_id: UUID) -> Usuario | None:
        return self.usuarios.get(usuario_id)

    def buscar_por_email(self, email: str) -> Usuario | None:
        return next((u for u in self.usuarios.values() if u.email == email), None)

    def cambiar_email(self, usuario_id: UUID, email_nuevo: str) -> None:
        if self.buscar_por_email(email_nuevo) is not None:
            raise EmailYaRegistrado("Ya existe una cuenta con ese email")
        self.usuarios[usuario_id] = replace(self.usuarios[usuario_id], email=email_nuevo)

    def cambiar_hash(self, usuario_id: UUID, hash_nuevo: str) -> None:
        self.usuarios[usuario_id] = replace(self.usuarios[usuario_id], hash_contrasena=hash_nuevo)

    def eliminar_cuenta(self, usuario_id: UUID, clave_intentos: str) -> None:
        self.usuarios.pop(usuario_id, None)
        self.claves_borradas.append(clave_intentos)
