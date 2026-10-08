"""Fabrica y lee tokens JWT firmados con RS256 (cumple el puerto EmisorTokens)."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from app.dominio.errores import TokenInvalido

ALGORITMO = "RS256"
EMISOR = "app-financiera"
VIDA_ACCESO_SEGUNDOS = 15 * 60  # el informe fija 15 minutos


class EmisorJWT:
    def __init__(
        self,
        clave_privada: str,
        clave_publica: str,
        segundos_de_vida: int = VIDA_ACCESO_SEGUNDOS,
    ) -> None:
        self._clave_privada = clave_privada
        self._clave_publica = clave_publica
        self.segundos_de_vida = segundos_de_vida

    def emitir(self, usuario_id: UUID) -> str:
        ahora = datetime.now(timezone.utc)
        # Solo lo mínimo: quién es (sub), quién lo emitió, cuándo y hasta cuándo.
        # Nada de email ni datos financieros dentro del token: cualquiera puede leerlo.
        datos = {
            "sub": str(usuario_id),
            "iss": EMISOR,
            "iat": ahora,
            "exp": ahora + timedelta(seconds=self.segundos_de_vida),
        }
        return jwt.encode(datos, self._clave_privada, algorithm=ALGORITMO)

    def leer(self, token: str) -> UUID:
        try:
            datos = jwt.decode(
                token,
                self._clave_publica,
                algorithms=[ALGORITMO],  # lista explícita: así no aceptamos "alg: none"
                issuer=EMISOR,
                options={"require": ["exp", "iat", "sub", "iss"]},
            )
            return UUID(datos["sub"])
        except (jwt.PyJWTError, ValueError) as error:
            raise TokenInvalido("Token de acceso inválido o vencido") from error
