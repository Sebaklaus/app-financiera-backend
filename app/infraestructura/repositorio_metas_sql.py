"""Guarda metas de ahorro y sus aportes en una base SQL.

Las tablas `meta_ahorro` y `aporte_meta` se definen aquí mismo; modelos.py importa este
archivo para que SQLAlchemy (y Alembic) se enteren de que existen.
"""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    String,
    Uuid,
    delete,
    func,
    select,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.dominio.meta import Aporte, MetaAhorro
from app.infraestructura.base_de_datos import Base


class MetaAhorroTabla(Base):
    __tablename__ = "meta_ahorro"
    __table_args__ = (CheckConstraint("monto_objetivo > 0", name="meta_ahorro_monto_positivo"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(80))
    monto_objetivo: Mapped[int] = mapped_column(BigInteger)
    fecha_limite: Mapped[date | None] = mapped_column(Date, nullable=True)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AporteMetaTabla(Base):
    __tablename__ = "aporte_meta"
    __table_args__ = (CheckConstraint("monto > 0", name="aporte_meta_monto_positivo"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    meta_id: Mapped[UUID] = mapped_column(ForeignKey("meta_ahorro.id"), index=True)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    monto: Mapped[int] = mapped_column(BigInteger)
    fecha: Mapped[date] = mapped_column(Date)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _meta_a_dominio(fila: MetaAhorroTabla) -> MetaAhorro:
    return MetaAhorro(
        id=fila.id,
        usuario_id=fila.usuario_id,
        nombre=fila.nombre,
        monto_objetivo=fila.monto_objetivo,
        fecha_limite=fila.fecha_limite,
        creada_en=fila.creada_en,
    )


def _aporte_a_dominio(fila: AporteMetaTabla) -> Aporte:
    return Aporte(
        id=fila.id,
        meta_id=fila.meta_id,
        usuario_id=fila.usuario_id,
        monto=fila.monto,
        fecha=fila.fecha,
        creado_en=fila.creado_en,
    )


class RepositorioMetasSQL:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def guardar_meta(self, meta: MetaAhorro) -> None:
        try:
            self._sesion.add(
                MetaAhorroTabla(
                    id=meta.id,
                    usuario_id=meta.usuario_id,
                    nombre=meta.nombre,
                    monto_objetivo=meta.monto_objetivo,
                    fecha_limite=meta.fecha_limite,
                    creada_en=meta.creada_en,
                )
            )
            self._sesion.commit()
        except Exception:
            self._sesion.rollback()
            raise

    def listar_metas(self, usuario_id: UUID) -> list[MetaAhorro]:
        filas = self._sesion.scalars(
            select(MetaAhorroTabla)
            .where(MetaAhorroTabla.usuario_id == usuario_id)
            .order_by(MetaAhorroTabla.creada_en.desc())
        )
        return [_meta_a_dominio(fila) for fila in filas]

    def buscar_meta(self, usuario_id: UUID, meta_id: UUID) -> MetaAhorro | None:
        fila = self._sesion.get(MetaAhorroTabla, meta_id)
        if fila is None or fila.usuario_id != usuario_id:
            return None
        return _meta_a_dominio(fila)

    def guardar_aporte(self, aporte: Aporte) -> None:
        try:
            self._sesion.add(
                AporteMetaTabla(
                    id=aporte.id,
                    meta_id=aporte.meta_id,
                    usuario_id=aporte.usuario_id,
                    monto=aporte.monto,
                    fecha=aporte.fecha,
                    creado_en=aporte.creado_en,
                )
            )
            self._sesion.commit()
        except Exception:
            self._sesion.rollback()
            raise

    def listar_aportes(self, usuario_id: UUID, meta_id: UUID) -> list[Aporte]:
        filas = self._sesion.scalars(
            select(AporteMetaTabla)
            .where(AporteMetaTabla.usuario_id == usuario_id, AporteMetaTabla.meta_id == meta_id)
            .order_by(AporteMetaTabla.fecha.desc(), AporteMetaTabla.creado_en.desc())
        )
        return [_aporte_a_dominio(fila) for fila in filas]

    def total_aportado(self, usuario_id: UUID) -> dict[UUID, int]:
        filas = self._sesion.execute(
            select(AporteMetaTabla.meta_id, func.sum(AporteMetaTabla.monto))
            .where(AporteMetaTabla.usuario_id == usuario_id)
            .group_by(AporteMetaTabla.meta_id)
        )
        return {meta_id: int(total) for meta_id, total in filas}

    def eliminar_meta(self, usuario_id: UUID, meta_id: UUID) -> bool:
        if self.buscar_meta(usuario_id, meta_id) is None:
            return False
        try:
            self._sesion.execute(delete(AporteMetaTabla).where(AporteMetaTabla.meta_id == meta_id))
            self._sesion.execute(delete(MetaAhorroTabla).where(MetaAhorroTabla.id == meta_id))
            self._sesion.commit()  # las dos cosas juntas: o se borra todo o nada
        except Exception:
            self._sesion.rollback()
            raise
        return True
