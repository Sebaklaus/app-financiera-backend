"""Tokens de recuperación de contraseña en SQL."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func, select, update
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.dominio.recuperacion import TokenRecuperacion
from app.infraestructura.base_de_datos import Base


class TokenRecuperacionTabla(Base):
    __tablename__ = "tokens_recuperacion"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    huella: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def _con_zona(momento: datetime | None) -> datetime | None:
    """SQLite devuelve horas sin zona; se asume UTC para poder compararlas."""
    if momento is not None and momento.tzinfo is None:
        return momento.replace(tzinfo=timezone.utc)
    return momento


class RepositorioRecuperacionSQL:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def _confirmar_cambios(self) -> None:
        try:
            self._sesion.commit()
        except Exception:
            self._sesion.rollback()
            raise

    def guardar(self, token: TokenRecuperacion) -> None:
        self._sesion.add(
            TokenRecuperacionTabla(
                id=token.id,
                usuario_id=token.usuario_id,
                huella=token.huella,
                creado_en=token.creado_en,
                expira_en=token.expira_en,
                usado_en=token.usado_en,
            )
        )
        self._confirmar_cambios()

    def buscar_por_huella(self, huella: str) -> TokenRecuperacion | None:
        fila = self._sesion.scalar(
            select(TokenRecuperacionTabla).where(TokenRecuperacionTabla.huella == huella)
        )
        if fila is None:
            return None
        return TokenRecuperacion(
            id=fila.id,
            usuario_id=fila.usuario_id,
            huella=fila.huella,
            creado_en=_con_zona(fila.creado_en),
            expira_en=_con_zona(fila.expira_en),
            usado_en=_con_zona(fila.usado_en),
        )

    def ultimo_creado_en(self, usuario_id: UUID) -> datetime | None:
        momento = self._sesion.scalar(
            select(func.max(TokenRecuperacionTabla.creado_en)).where(
                TokenRecuperacionTabla.usuario_id == usuario_id
            )
        )
        return _con_zona(momento)

    def marcar_usado(self, token_id: UUID, ahora: datetime) -> bool:
        # "WHERE usado_en IS NULL": si dos peticiones llegan a la vez, solo una gana.
        resultado = self._sesion.execute(
            update(TokenRecuperacionTabla)
            .where(TokenRecuperacionTabla.id == token_id, TokenRecuperacionTabla.usado_en.is_(None))
            .values(usado_en=ahora)
        )
        self._confirmar_cambios()
        return resultado.rowcount == 1

    def invalidar_pendientes(self, usuario_id: UUID, ahora: datetime) -> None:
        self._sesion.execute(
            update(TokenRecuperacionTabla)
            .where(
                TokenRecuperacionTabla.usuario_id == usuario_id,
                TokenRecuperacionTabla.usado_en.is_(None),
            )
            .values(usado_en=ahora)
        )
        self._confirmar_cambios()
