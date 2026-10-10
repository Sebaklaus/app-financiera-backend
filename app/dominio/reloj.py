"""La hora y la fecha de hoy, con zonas horarias bien definidas. Dominio puro.

Regla del proyecto: las horas se guardan y se entregan siempre en UTC (el "huso cero",
la hora del mundo). Pero "hoy" para una persona en Chile no es "hoy" en UTC: a las 21:30 en
Santiago ya es el día siguiente en UTC. Por eso, cuando un movimiento no trae fecha, se usa
la fecha de HOY EN CHILE, no la de UTC.
"""

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

ZONA_CHILE = ZoneInfo("America/Santiago")  # incluye el cambio de hora de verano e invierno


def ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


def a_utc(momento: datetime) -> datetime:
    """Lleva cualquier hora a UTC. Una hora sin zona (SQLite) se asume que ya está en UTC."""
    if momento.tzinfo is None:
        return momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(timezone.utc)


def hoy_en_chile(ahora: datetime | None = None) -> date:
    """La fecha de hoy según el calendario de Chile."""
    return a_utc(ahora or ahora_utc()).astimezone(ZONA_CHILE).date()
