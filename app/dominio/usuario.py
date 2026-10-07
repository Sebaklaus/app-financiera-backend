"""Usuario y reglas de registro (HU-01). Dominio puro: sin FastAPI, sin base de datos."""

import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.dominio.errores import ContrasenaInvalida, EmailInvalido

LARGO_MIN_CONTRASENA = 8
# bcrypt solo mira los primeros 72 bytes: más allá no aporta seguridad (y la librería
# rechaza esas claves). Se rechaza de forma explícita para no dar una falsa sensación.
BYTES_MAX_CONTRASENA = 72

_FORMA_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class Usuario:
    id: UUID
    email: str
    hash_contrasena: str  # nunca la contraseña: solo su huella
    creado_en: datetime


def normalizar_email(email: str) -> str:
    """Quita espacios y pasa a minúsculas, para que Ana@x.cl y ana@x.cl sean el mismo."""
    return email.strip().lower()


def validar_email(email: str) -> str:
    """Devuelve el email normalizado o lanza EmailInvalido."""
    limpio = normalizar_email(email)
    if not _FORMA_EMAIL.match(limpio):
        raise EmailInvalido("El email no tiene un formato válido")
    return limpio


def validar_contrasena(contrasena: str) -> None:
    """Lanza ContrasenaInvalida si no cumple los requisitos mínimos."""
    if len(contrasena) < LARGO_MIN_CONTRASENA:
        raise ContrasenaInvalida(
            f"La contraseña debe tener al menos {LARGO_MIN_CONTRASENA} caracteres"
        )
    if len(contrasena.encode("utf-8")) > BYTES_MAX_CONTRASENA:
        raise ContrasenaInvalida(
            f"La contraseña es demasiado larga (máximo {BYTES_MAX_CONTRASENA} bytes)"
        )
    if not any(c.isalpha() for c in contrasena):
        raise ContrasenaInvalida("La contraseña debe incluir al menos una letra")
    if not any(c.isdigit() for c in contrasena):
        raise ContrasenaInvalida("La contraseña debe incluir al menos un número")
