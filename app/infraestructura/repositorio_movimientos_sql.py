"""Guarda y lista ingresos, gastos y propuestas de reparto en una base SQL.

Las tablas `movimientos` y `confirmaciones` se definen aquí mismo para no tocar
base_de_datos.py. Por eso crear_tablas.py importa este archivo: así SQLAlchemy se entera
de que existen.
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
    select,
    update,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.dominio.categorias import Categoria
from app.dominio.confirmacion import Confirmacion, EstadoConfirmacion
from app.dominio.errores import ConfirmacionYaDecidida
from app.dominio.movimiento import Movimiento, TipoMovimiento
from app.infraestructura.base_de_datos import Base


class MovimientoTabla(Base):
    __tablename__ = "movimientos"
    # La propia base impide montos de cero o negativos, aunque el programa fallara.
    __table_args__ = (CheckConstraint("monto > 0", name="movimientos_monto_positivo"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    # index=True: casi toda consulta es "los movimientos de este usuario".
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(10))
    monto: Mapped[int] = mapped_column(BigInteger)
    categoria: Mapped[str | None] = mapped_column(String(20), nullable=True)
    descripcion: Mapped[str] = mapped_column(String(200))
    fecha: Mapped[date] = mapped_column(Date)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ConfirmacionTabla(Base):
    __tablename__ = "confirmaciones"
    __table_args__ = (CheckConstraint("monto > 0", name="confirmaciones_monto_positivo"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    ingreso_id: Mapped[UUID] = mapped_column(ForeignKey("movimientos.id"), index=True)
    categoria: Mapped[str] = mapped_column(String(20))
    monto: Mapped[int] = mapped_column(BigInteger)
    estado: Mapped[str] = mapped_column(String(12))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decidido_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def _movimiento_a_dominio(fila: MovimientoTabla) -> Movimiento:
    return Movimiento(
        id=fila.id,
        usuario_id=fila.usuario_id,
        tipo=TipoMovimiento(fila.tipo),
        monto=fila.monto,
        categoria=None if fila.categoria is None else Categoria(fila.categoria),
        descripcion=fila.descripcion,
        fecha=fila.fecha,
        creado_en=fila.creado_en,
    )


def _confirmacion_a_dominio(fila: ConfirmacionTabla) -> Confirmacion:
    return Confirmacion(
        id=fila.id,
        usuario_id=fila.usuario_id,
        ingreso_id=fila.ingreso_id,
        categoria=Categoria(fila.categoria),
        monto=fila.monto,
        estado=EstadoConfirmacion(fila.estado),
        creado_en=fila.creado_en,
        decidido_en=fila.decidido_en,
    )


def _fila_de_movimiento(movimiento: Movimiento) -> MovimientoTabla:
    return MovimientoTabla(
        id=movimiento.id,
        usuario_id=movimiento.usuario_id,
        tipo=movimiento.tipo.value,
        monto=movimiento.monto,
        categoria=None if movimiento.categoria is None else movimiento.categoria.value,
        descripcion=movimiento.descripcion,
        fecha=movimiento.fecha,
        creado_en=movimiento.creado_en,
    )


class RepositorioMovimientosSQL:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def _confirmar_cambios(self) -> None:
        try:
            self._sesion.commit()
        except Exception:
            self._sesion.rollback()
            raise

    def guardar(self, movimiento: Movimiento) -> None:
        self._sesion.add(_fila_de_movimiento(movimiento))
        self._confirmar_cambios()

    def guardar_ingreso(self, ingreso: Movimiento, confirmaciones: list[Confirmacion]) -> None:
        self._sesion.add(_fila_de_movimiento(ingreso))
        # flush: escribe primero el ingreso, porque las propuestas apuntan a él.
        self._sesion.flush()
        for c in confirmaciones:
            self._sesion.add(
                ConfirmacionTabla(
                    id=c.id,
                    usuario_id=c.usuario_id,
                    ingreso_id=c.ingreso_id,
                    categoria=c.categoria.value,
                    monto=c.monto,
                    estado=c.estado.value,
                    creado_en=c.creado_en,
                    decidido_en=c.decidido_en,
                )
            )
        # Un solo commit: o se guardan el ingreso y sus propuestas, o no se guarda nada.
        self._confirmar_cambios()

    def listar_por_usuario(self, usuario_id: UUID) -> list[Movimiento]:
        consulta = (
            select(MovimientoTabla)
            .where(MovimientoTabla.usuario_id == usuario_id)
            .order_by(MovimientoTabla.fecha.desc(), MovimientoTabla.creado_en.desc())
        )
        return [_movimiento_a_dominio(fila) for fila in self._sesion.scalars(consulta)]

    def listar_confirmaciones_por_usuario(self, usuario_id: UUID) -> list[Confirmacion]:
        consulta = (
            select(ConfirmacionTabla)
            .where(ConfirmacionTabla.usuario_id == usuario_id)
            .order_by(ConfirmacionTabla.creado_en.desc())
        )
        return [_confirmacion_a_dominio(fila) for fila in self._sesion.scalars(consulta)]

    def buscar_confirmacion(self, usuario_id: UUID, confirmacion_id: UUID) -> Confirmacion | None:
        consulta = select(ConfirmacionTabla).where(
            ConfirmacionTabla.id == confirmacion_id,
            ConfirmacionTabla.usuario_id == usuario_id,
        )
        fila = self._sesion.scalar(consulta)
        return None if fila is None else _confirmacion_a_dominio(fila)

    def actualizar_confirmacion(self, confirmacion: Confirmacion) -> None:
        # "WHERE estado = pendiente": si dos peticiones deciden a la vez, solo una gana.
        resultado = self._sesion.execute(
            update(ConfirmacionTabla)
            .where(
                ConfirmacionTabla.id == confirmacion.id,
                ConfirmacionTabla.usuario_id == confirmacion.usuario_id,
                ConfirmacionTabla.estado == EstadoConfirmacion.PENDIENTE.value,
            )
            .values(estado=confirmacion.estado.value, decidido_en=confirmacion.decidido_en)
        )
        if resultado.rowcount == 0:
            self._sesion.rollback()
            raise ConfirmacionYaDecidida("Esta propuesta ya fue decidida")
        self._confirmar_cambios()
