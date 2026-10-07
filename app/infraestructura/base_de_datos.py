"""Conexión a la base de datos y forma de las tablas (capa de infraestructura)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Engine, String, Uuid, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    """Punto de partida de todas las tablas."""


class UsuarioTabla(Base):
    """Cómo se ve un usuario en PostgreSQL. No es el Usuario del dominio: es su ficha."""

    __tablename__ = "usuarios"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    # unique=True: la propia base impide dos cuentas con el mismo email.
    email: Mapped[str] = mapped_column(String(320), unique=True)
    hash_contrasena: Mapped[str] = mapped_column(String(100))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def crear_motor(url: str) -> Engine:
    return create_engine(url)


def crear_fabrica_sesiones(motor: Engine) -> sessionmaker[Session]:
    # expire_on_commit=False: los objetos siguen usables después de guardar.
    return sessionmaker(motor, expire_on_commit=False)


def crear_tablas(motor: Engine) -> None:
    """Crea las tablas que falten. Más adelante lo reemplazan las migraciones (Alembic)."""
    Base.metadata.create_all(motor)
