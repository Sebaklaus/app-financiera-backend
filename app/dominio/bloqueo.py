"""Bloqueo por intentos fallidos de login (HU-02). Dominio puro.

Regla: 5 contraseñas incorrectas dentro de 15 minutos bloquean los intentos por 15 minutos.
Es como el PIN de un cajero: tras varios errores seguidos, la tarjeta se bloquea un rato, y
así nadie puede probar miles de contraseñas por fuerza bruta.

Se cuenta por email (exista o no la cuenta), para que el bloqueo no delate qué emails
tienen cuenta. Un login correcto borra el contador.
"""

import hashlib
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from app.dominio.usuario import normalizar_email

MAX_INTENTOS = 5
VENTANA = timedelta(minutes=15)  # los fallos se olvidan si pasan más de 15 min entre ellos
DURACION_BLOQUEO = timedelta(minutes=15)


@dataclass(frozen=True)
class RegistroIntentos:
    clave: str  # huella del email normalizado
    fallos: int
    primer_fallo: datetime
    bloqueado_hasta: datetime | None = None

    def esta_bloqueado(self, ahora: datetime) -> bool:
        return self.bloqueado_hasta is not None and ahora < self.bloqueado_hasta

    def segundos_restantes(self, ahora: datetime) -> int:
        if not self.esta_bloqueado(ahora):
            return 0
        resto = (self.bloqueado_hasta - ahora).total_seconds()  # type: ignore[operator]
        return int(resto) + (1 if resto % 1 else 0)  # redondea hacia arriba


def clave_de(email: str) -> str:
    """Huella del email: largo fijo y sin guardar texto escrito por quien ataca."""
    return hashlib.sha256(normalizar_email(email).encode("utf-8")).hexdigest()


def registrar_fallo(
    previo: RegistroIntentos | None, clave: str, ahora: datetime
) -> RegistroIntentos:
    """Suma un fallo y devuelve el registro nuevo (bloqueado si llegó al máximo)."""
    if previo is None:
        nuevo = RegistroIntentos(clave, 1, ahora)
    elif previo.bloqueado_hasta is not None and ahora >= previo.bloqueado_hasta:
        nuevo = RegistroIntentos(clave, 1, ahora)  # el bloqueo ya terminó: se parte de cero
    elif previo.bloqueado_hasta is None and ahora - previo.primer_fallo > VENTANA:
        nuevo = RegistroIntentos(clave, 1, ahora)  # los fallos viejos se olvidan
    else:
        nuevo = replace(previo, fallos=previo.fallos + 1)
    if nuevo.fallos >= MAX_INTENTOS:
        nuevo = replace(nuevo, bloqueado_hasta=ahora + DURACION_BLOQUEO)
    return nuevo
