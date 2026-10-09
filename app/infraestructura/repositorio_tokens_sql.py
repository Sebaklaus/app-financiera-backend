"""Guarda las huellas de los tokens de refresco en una base SQL."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Uuid, select, update
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.dominio.token_refresco import TokenRefresco
from app.infraestructura.base_de_datos import Base


class TokenRefrescoTabla(Base):
    __tablename__ = "tokens_refresco"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    # unique + index: se busca por huella en cada renovación.
    huella: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revocado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def _con_zona(momento: datetime | None) -> datetime | None:
    """SQLite devuelve horas sin zona; se asume UTC para poder compararlas."""
    if momento is not None and momento.tzinfo is None:
        return momento.replace(tzinfo=timezone.utc)
    return momento


def _a_dominio(fila: TokenRefrescoTabla) -> TokenRefresco:
    return TokenRefresco(
        id=fila.id,
        usuario_id=fila.usuario_id,
        huella=fila.huella,
        creado_en=_con_zona(fila.creado_en),
        expira_en=_con_zona(fila.expira_en),
        revocado_en=_con_zona(fila.revocado_en),
    )


class RepositorioTokensSQL:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def _confirmar_cambios(self) -> None:
        try:
            self._sesion.commit()
        except Exception:
            self._sesion.rollback()
            raise

    def guardar(self, token: TokenRefresco) -> None:
        self._sesion.add(
            TokenRefrescoTabla(
                id=token.id,
                usuario_id=token.usuario_id,
                huella=token.huella,
                creado_en=token.creado_en,
                expira_en=token.expira_en,
                revocado_en=token.revocado_en,
            )
        )
        self._confirmar_cambios()

    def buscar_por_huella(self, huella: str) -> TokenRefresco | None:
        fila = self._sesion.scalar(
            select(TokenRefrescoTabla).where(TokenRefrescoTabla.huella == huella)
        )
        return None if fila is None else _a_dominio(fila)

    def revocar(self, token_id: UUID, ahora: datetime) -> bool:
        # "WHERE revocado_en IS NULL": si dos peticiones llegan a la vez, solo una gana.
        resultado = self._sesion.execute(
            update(TokenRefrescoTabla)
            .where(TokenRefrescoTabla.id == token_id, TokenRefrescoTabla.revocado_en.is_(None))
            .values(revocado_en=ahora)
        )
        self._confirmar_cambios()
        return resultado.rowcount == 1

    def revocar_todos_de_usuario(self, usuario_id: UUID, ahora: datetime) -> None:
        self._sesion.execute(
            update(TokenRefrescoTabla)
            .where(
                TokenRefrescoTabla.usuario_id == usuario_id,
                TokenRefrescoTabla.revocado_en.is_(None),
            )
            .values(revocado_en=ahora)
        )
        self._confirmar_cambios()
