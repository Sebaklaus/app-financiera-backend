"""Guarda el conteo de intentos fallidos de login en una base SQL."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, delete
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.dominio.bloqueo import RegistroIntentos
from app.infraestructura.base_de_datos import Base


class IntentosLoginTabla(Base):
    __tablename__ = "intentos_login"

    clave: Mapped[str] = mapped_column(String(64), primary_key=True)
    fallos: Mapped[int] = mapped_column(Integer)
    primer_fallo: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def _con_zona(momento: datetime | None) -> datetime | None:
    """SQLite devuelve horas sin zona; se asume UTC para poder compararlas."""
    if momento is not None and momento.tzinfo is None:
        return momento.replace(tzinfo=timezone.utc)
    return momento


class RepositorioIntentosSQL:
    def __init__(self, sesion: Session) -> None:
        self._sesion = sesion

    def _confirmar_cambios(self) -> None:
        try:
            self._sesion.commit()
        except Exception:
            self._sesion.rollback()
            raise

    def obtener(self, clave: str) -> RegistroIntentos | None:
        fila = self._sesion.get(IntentosLoginTabla, clave)
        if fila is None:
            return None
        return RegistroIntentos(
            clave=fila.clave,
            fallos=fila.fallos,
            primer_fallo=_con_zona(fila.primer_fallo),
            bloqueado_hasta=_con_zona(fila.bloqueado_hasta),
        )

    def guardar(self, registro: RegistroIntentos) -> None:
        # merge: crea la fila si no existe y la reemplaza si ya existe.
        self._sesion.merge(
            IntentosLoginTabla(
                clave=registro.clave,
                fallos=registro.fallos,
                primer_fallo=registro.primer_fallo,
                bloqueado_hasta=registro.bloqueado_hasta,
            )
        )
        self._confirmar_cambios()

    def borrar(self, clave: str) -> None:
        self._sesion.execute(delete(IntentosLoginTabla).where(IntentosLoginTabla.clave == clave))
        self._confirmar_cambios()
