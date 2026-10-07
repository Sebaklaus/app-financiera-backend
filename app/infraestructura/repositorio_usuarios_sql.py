"""Guarda y busca usuarios en una base SQL (cumple el puerto RepositorioUsuarios)."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dominio.errores import EmailYaRegistrado
from app.dominio.usuario import Usuario
from app.infraestructura.base_de_datos import UsuarioTabla


def _a_dominio(fila: UsuarioTabla) -> Usuario:
    return Usuario(
        id=fila.id,
        email=fila.email,
        hash_contrasena=fila.hash_contrasena,
        creado_en=fila.creado_en,
    )


class RepositorioUsuariosSQL:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def buscar_por_email(self, email: str) -> Usuario | None:
        fila = self._sesion.scalar(select(UsuarioTabla).where(UsuarioTabla.email == email))
        return None if fila is None else _a_dominio(fila)

    def guardar(self, usuario: Usuario) -> None:
        self._sesion.add(
            UsuarioTabla(
                id=usuario.id,
                email=usuario.email,
                hash_contrasena=usuario.hash_contrasena,
                creado_en=usuario.creado_en,
            )
        )
        try:
            self._sesion.commit()
        except IntegrityError as error:
            # Dos personas registrando el mismo email a la vez: la base lo detecta
            # aunque el caso de uso no lo haya visto.
            self._sesion.rollback()
            raise EmailYaRegistrado("Ya existe una cuenta con ese email") from error
