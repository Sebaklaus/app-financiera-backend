"""Envío de correos. Hoy solo existe el modo `consola`, para desarrollo.

El modo consola NO envía nada: escribe el correo en la terminal del servidor, y así puedes
copiar el token de ahí. Nunca debe usarse en producción, porque deja el token a la vista.
Cuando se contrate un proveedor real (por ejemplo, SendGrid o Amazon SES), se agrega otra clase
que cumpla el mismo puerto `EnviadorCorreo` y se elige con CORREO_MODO en el .env.
"""

import logging
import os

_registro = logging.getLogger("uvicorn.error")


class EnviadorCorreoConsola:
    def enviar_recuperacion(self, email: str, token: str) -> None:
        _registro.warning(
            "[CORREO DE DESARROLLO] Para: %s | Asunto: Recupera tu contraseña | Token: %s",
            email,
            token,
        )


def crear_enviador() -> EnviadorCorreoConsola:
    modo = os.environ.get("CORREO_MODO", "consola")
    if modo != "consola":
        raise RuntimeError(f"CORREO_MODO='{modo}' no está disponible todavía (solo 'consola').")
    return EnviadorCorreoConsola()
