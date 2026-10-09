"""Token de refresco (HU-02): permite renovar la sesión sin pedir la contraseña otra vez.

Idea: el token de acceso dura 15 minutos (si lo roban, sirve poco). El de refresco dura más
y se guarda en la base SOLO como huella (hash): si alguien leyera la base, no podría usarlo.
Cada vez que se usa se cambia por uno nuevo (rotación) y el viejo queda revocado.
"""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

VIDA_REFRESCO = timedelta(days=30)


@dataclass(frozen=True)
class TokenRefresco:
    id: UUID
    usuario_id: UUID
    huella: str  # SHA-256 del token; el token en sí nunca se guarda
    creado_en: datetime
    expira_en: datetime
    revocado_en: datetime | None = None

    def esta_vigente(self, ahora: datetime) -> bool:
        return self.revocado_en is None and ahora < self.expira_en


def generar_token() -> str:
    """Un texto aleatorio e imposible de adivinar (48 bytes de azar)."""
    return secrets.token_urlsafe(48)


def calcular_huella(token: str) -> str:
    # SHA-256 basta aquí (no bcrypt): el token ya es aleatorio y largo, no una contraseña
    # que alguien pueda adivinar por fuerza bruta.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def nuevo_token_refresco(usuario_id: UUID, ahora: datetime) -> tuple[str, TokenRefresco]:
    """Devuelve (token en claro para entregar, registro con la huella para guardar)."""
    token = generar_token()
    registro = TokenRefresco(
        id=uuid4(),
        usuario_id=usuario_id,
        huella=calcular_huella(token),
        creado_en=ahora,
        expira_en=ahora + VIDA_REFRESCO,
    )
    return token, registro
