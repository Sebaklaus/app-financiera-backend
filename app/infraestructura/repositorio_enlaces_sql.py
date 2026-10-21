"""Guarda el enlace bancario (link_token) de cada persona, SIEMPRE cifrado."""

from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, delete
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.infraestructura.base_de_datos import Base


class Cifrador(Protocol):
    def cifrar(self, texto: str) -> str: ...

    def descifrar(self, cifrado: str) -> str: ...


class EnlaceBancarioTabla(Base):
    __tablename__ = "enlaces_bancarios"

    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"), primary_key=True)
    token_cifrado: Mapped[str] = mapped_column(String(600))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RepositorioEnlacesSQL:
    def __init__(self, sesion: Session, cifrador: Cifrador) -> None:
        self._sesion = sesion
        self._cifrador = cifrador

    def guardar(self, usuario_id: UUID, link_token: str) -> None:
        fila = self._sesion.get(EnlaceBancarioTabla, usuario_id)
        cifrado = self._cifrador.cifrar(link_token)
        ahora = datetime.now(timezone.utc)
        try:
            if fila is None:
                self._sesion.add(
                    EnlaceBancarioTabla(
                        usuario_id=usuario_id, token_cifrado=cifrado, creado_en=ahora
                    )
                )
            else:
                fila.token_cifrado = cifrado
                fila.creado_en = ahora
            self._sesion.commit()
        except Exception:
            self._sesion.rollback()
            raise

    def obtener(self, usuario_id: UUID) -> str | None:
        fila = self._sesion.get(EnlaceBancarioTabla, usuario_id)
        return None if fila is None else self._cifrador.descifrar(fila.token_cifrado)

    def eliminar(self, usuario_id: UUID) -> bool:
        try:
            resultado = self._sesion.execute(
                delete(EnlaceBancarioTabla).where(EnlaceBancarioTabla.usuario_id == usuario_id)
            )
            self._sesion.commit()
        except Exception:
            self._sesion.rollback()
            raise
        return resultado.rowcount > 0
