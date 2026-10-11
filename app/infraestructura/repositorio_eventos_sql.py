"""Bitácora de eventos de seguridad en SQL.

`usuario_id` NO es una clave foránea a propósito: al eliminar una cuenta, sus eventos se
conservan sin vínculo con la persona (usuario_id queda vacío), porque la bitácora de seguridad
sirve para investigar incidentes aunque la cuenta ya no exista.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import DateTime, String, Uuid, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.dominio.auditoria import EventoSeguridad, TipoEvento
from app.infraestructura.base_de_datos import Base


class EventoSeguridadTabla(Base):
    __tablename__ = "eventos_seguridad"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(40), index=True)
    usuario_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    ip_huella: Mapped[str | None] = mapped_column(String(64), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


def _con_zona(momento: datetime) -> datetime:
    return momento.replace(tzinfo=timezone.utc) if momento.tzinfo is None else momento


class RepositorioEventosSQL:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def guardar(self, evento: EventoSeguridad) -> None:
        self._sesion.add(
            EventoSeguridadTabla(
                id=evento.id,
                tipo=evento.tipo.value,
                usuario_id=evento.usuario_id,
                ip_huella=evento.ip_huella,
                creado_en=evento.creado_en,
            )
        )
        try:
            self._sesion.commit()
        except Exception:
            self._sesion.rollback()
            raise

    def listar_por_usuario(self, usuario_id: UUID, limite: int) -> list[EventoSeguridad]:
        filas = self._sesion.scalars(
            select(EventoSeguridadTabla)
            .where(EventoSeguridadTabla.usuario_id == usuario_id)
            .order_by(EventoSeguridadTabla.creado_en.desc())
            .limit(limite)
        )
        return [
            EventoSeguridad(
                id=f.id,
                tipo=TipoEvento(f.tipo),
                usuario_id=f.usuario_id,
                ip_huella=f.ip_huella,
                creado_en=_con_zona(f.creado_en),
            )
            for f in filas
        ]
