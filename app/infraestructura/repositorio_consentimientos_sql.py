"""Consentimientos (historial) y perfil de riesgo en SQL."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.dominio.consentimiento import (
    Consentimiento,
    PerfilDeclarado,
    PerfilRiesgo,
    TipoConsentimiento,
)
from app.infraestructura.base_de_datos import Base


class ConsentimientoTabla(Base):
    __tablename__ = "consentimientos"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(30))
    otorgado: Mapped[bool] = mapped_column(Boolean)
    version: Mapped[str] = mapped_column(String(20))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PerfilRiesgoTabla(Base):
    __tablename__ = "perfiles_riesgo"

    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"), primary_key=True)
    perfil: Mapped[str] = mapped_column(String(15))
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _con_zona(momento: datetime) -> datetime:
    """SQLite devuelve horas sin zona; se asume UTC."""
    return momento.replace(tzinfo=timezone.utc) if momento.tzinfo is None else momento


class RepositorioConsentimientosSQL:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def _confirmar_cambios(self) -> None:
        try:
            self._sesion.commit()
        except Exception:
            self._sesion.rollback()
            raise

    def guardar_consentimientos(self, registros: list[Consentimiento]) -> None:
        self._sesion.add_all(
            ConsentimientoTabla(
                id=r.id,
                usuario_id=r.usuario_id,
                tipo=r.tipo.value,
                otorgado=r.otorgado,
                version=r.version,
                creado_en=r.creado_en,
            )
            for r in registros
        )
        self._confirmar_cambios()

    def listar_consentimientos(self, usuario_id: UUID) -> list[Consentimiento]:
        filas = self._sesion.scalars(
            select(ConsentimientoTabla)
            .where(ConsentimientoTabla.usuario_id == usuario_id)
            .order_by(ConsentimientoTabla.creado_en)
        )
        return [
            Consentimiento(
                id=f.id,
                usuario_id=f.usuario_id,
                tipo=TipoConsentimiento(f.tipo),
                otorgado=f.otorgado,
                version=f.version,
                creado_en=_con_zona(f.creado_en),
            )
            for f in filas
        ]

    def obtener_perfil(self, usuario_id: UUID) -> PerfilDeclarado | None:
        fila = self._sesion.get(PerfilRiesgoTabla, usuario_id)
        if fila is None:
            return None
        return PerfilDeclarado(
            usuario_id=fila.usuario_id,
            perfil=PerfilRiesgo(fila.perfil),
            actualizado_en=_con_zona(fila.actualizado_en),
        )

    def guardar_perfil(self, perfil: PerfilDeclarado) -> None:
        self._sesion.merge(
            PerfilRiesgoTabla(
                usuario_id=perfil.usuario_id,
                perfil=perfil.perfil.value,
                actualizado_en=perfil.actualizado_en,
            )
        )
        self._confirmar_cambios()
