"""Guarda y lista ingresos y gastos en una base SQL (cumple RepositorioMovimientos).

La tabla `movimientos` se define aquí mismo para no tocar base_de_datos.py. Por eso
crear_tablas.py importa este archivo: así SQLAlchemy se entera de que la tabla existe.
"""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, String, Uuid, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.dominio.categorias import Categoria
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


def _a_dominio(fila: MovimientoTabla) -> Movimiento:
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


class RepositorioMovimientosSQL:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def guardar(self, movimiento: Movimiento) -> None:
        self._sesion.add(
            MovimientoTabla(
                id=movimiento.id,
                usuario_id=movimiento.usuario_id,
                tipo=movimiento.tipo.value,
                monto=movimiento.monto,
                categoria=None if movimiento.categoria is None else movimiento.categoria.value,
                descripcion=movimiento.descripcion,
                fecha=movimiento.fecha,
                creado_en=movimiento.creado_en,
            )
        )
        try:
            self._sesion.commit()
        except Exception:
            self._sesion.rollback()
            raise

    def listar_por_usuario(self, usuario_id: UUID) -> list[Movimiento]:
        consulta = (
            select(MovimientoTabla)
            .where(MovimientoTabla.usuario_id == usuario_id)
            .order_by(MovimientoTabla.fecha.desc(), MovimientoTabla.creado_en.desc())
        )
        return [_a_dominio(fila) for fila in self._sesion.scalars(consulta)]
