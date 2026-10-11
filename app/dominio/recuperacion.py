"""Recuperar la contraseña olvidada. Dominio puro.

Funciona como una llave de un solo uso: se le envía a la persona, por correo, un token secreto
que dura 30 minutos y sirve una sola vez. En la base solo se guarda su huella (como el token de
refresco), así que quien lea la base no puede usarlo.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.dominio.token_refresco import calcular_huella, generar_token

VIDA_RECUPERACION = timedelta(minutes=30)
# Pedir otro correo antes de este tiempo se ignora en silencio: evita llenar un buzón ajeno.
ESPERA_ENTRE_SOLICITUDES = timedelta(minutes=1)


@dataclass(frozen=True)
class TokenRecuperacion:
    id: UUID
    usuario_id: UUID
    huella: str
    creado_en: datetime
    expira_en: datetime
    usado_en: datetime | None = None

    def esta_vigente(self, ahora: datetime) -> bool:
        return self.usado_en is None and ahora < self.expira_en


def nuevo_token_recuperacion(usuario_id: UUID, ahora: datetime) -> tuple[str, TokenRecuperacion]:
    """Devuelve (token en claro para enviar por correo, registro con la huella para guardar)."""
    token = generar_token()
    registro = TokenRecuperacion(
        id=uuid4(),
        usuario_id=usuario_id,
        huella=calcular_huella(token),
        creado_en=ahora,
        expira_en=ahora + VIDA_RECUPERACION,
    )
    return token, registro
