"""Eventos de seguridad (auditoría). Dominio puro.

Es la bitácora de la portería: anota QUÉ pasó y CUÁNDO (un login fallido, un cambio de
contraseña, un token robado), pero nunca contraseñas, tokens ni textos escritos por la persona.
Sirve para detectar ataques, mostrarle a la persona su actividad y, si hubiera un incidente,
reconstruir lo ocurrido (Ley 21.663: alerta temprana en 3 horas, informe en 15 días).
"""

import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID

from app.dominio.errores import TokenInvalido


class TipoEvento(str, Enum):
    LOGIN_EXITOSO = "login_exitoso"
    LOGIN_FALLIDO = "login_fallido"
    LOGIN_RECHAZADO_POR_BLOQUEO = "login_rechazado_por_bloqueo"
    IP_BLOQUEADA = "ip_bloqueada"
    REFRESCO_REUTILIZADO = "refresco_reutilizado"
    SESIONES_CERRADAS = "sesiones_cerradas"
    REAUTENTICACION_FALLIDA = "reautenticacion_fallida"
    CONTRASENA_CAMBIADA = "contrasena_cambiada"
    EMAIL_CAMBIADO = "email_cambiado"
    CUENTA_ELIMINADA = "cuenta_eliminada"
    RECUPERACION_SOLICITADA = "recuperacion_solicitada"
    RECUPERACION_COMPLETADA = "recuperacion_completada"
    RECUPERACION_FALLIDA = "recuperacion_fallida"


class ReusoDeToken(TokenInvalido):
    """Alguien presentó un token de refresco que ya se había usado: probablemente fue copiado."""

    def __init__(self, mensaje: str, usuario_id: UUID) -> None:
        super().__init__(mensaje)
        self.usuario_id = usuario_id


@dataclass(frozen=True)
class EventoSeguridad:
    id: UUID
    tipo: TipoEvento
    usuario_id: UUID | None  # None si no se sabe de quién es, o si la cuenta ya se eliminó
    ip_huella: str | None  # huella de la IP, nunca la IP en claro
    creado_en: datetime


def huella_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    return hashlib.sha256(f"auditoria:{ip}".encode()).hexdigest()
