"""Cuenta del usuario en SQL: buscar por id, corregir email o clave y borrar todo."""

from uuid import UUID

from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dominio.errores import EmailYaRegistrado
from app.dominio.usuario import Usuario
from app.infraestructura.base_de_datos import UsuarioTabla
from app.infraestructura.repositorio_consentimientos_sql import (
    ConsentimientoTabla,
    PerfilRiesgoTabla,
)
from app.infraestructura.repositorio_intentos_sql import IntentosLoginTabla
from app.infraestructura.repositorio_movimientos_sql import ConfirmacionTabla, MovimientoTabla
from app.infraestructura.repositorio_recuperacion_sql import TokenRecuperacionTabla
from app.infraestructura.repositorio_tokens_sql import TokenRefrescoTabla
from app.infraestructura.repositorio_usuarios_sql import RepositorioUsuariosSQL, _a_dominio


class RepositorioCuentaSQL(RepositorioUsuariosSQL):
    def __init__(self, sesion: Session) -> None:
        super().__init__(sesion)

    def buscar_por_id(self, usuario_id: UUID) -> Usuario | None:
        fila = self._sesion.get(UsuarioTabla, usuario_id)
        return None if fila is None else _a_dominio(fila)

    def cambiar_email(self, usuario_id: UUID, email_nuevo: str) -> None:
        try:
            self._sesion.execute(
                update(UsuarioTabla).where(UsuarioTabla.id == usuario_id).values(email=email_nuevo)
            )
            self._sesion.commit()
        except IntegrityError as error:
            self._sesion.rollback()
            raise EmailYaRegistrado("Ya existe una cuenta con ese email") from error

    def cambiar_hash(self, usuario_id: UUID, hash_nuevo: str) -> None:
        try:
            self._sesion.execute(
                update(UsuarioTabla)
                .where(UsuarioTabla.id == usuario_id)
                .values(hash_contrasena=hash_nuevo)
            )
            self._sesion.commit()
        except Exception:
            self._sesion.rollback()
            raise

    def eliminar_cuenta(self, usuario_id: UUID, clave_intentos: str) -> None:
        # Orden: primero lo que depende de otras tablas, al final el usuario.
        try:
            self._sesion.execute(
                delete(ConsentimientoTabla).where(ConsentimientoTabla.usuario_id == usuario_id)
            )
            self._sesion.execute(
                delete(PerfilRiesgoTabla).where(PerfilRiesgoTabla.usuario_id == usuario_id)
            )
            self._sesion.execute(
                delete(ConfirmacionTabla).where(ConfirmacionTabla.usuario_id == usuario_id)
            )
            self._sesion.execute(
                delete(MovimientoTabla).where(MovimientoTabla.usuario_id == usuario_id)
            )
            self._sesion.execute(
                delete(TokenRecuperacionTabla).where(
                    TokenRecuperacionTabla.usuario_id == usuario_id
                )
            )
            self._sesion.execute(
                delete(TokenRefrescoTabla).where(TokenRefrescoTabla.usuario_id == usuario_id)
            )
            self._sesion.execute(
                delete(IntentosLoginTabla).where(IntentosLoginTabla.clave == clave_intentos)
            )
            self._sesion.execute(delete(UsuarioTabla).where(UsuarioTabla.id == usuario_id))
            self._sesion.commit()  # todo junto: o se borra todo o nada
        except Exception:
            self._sesion.rollback()
            raise
