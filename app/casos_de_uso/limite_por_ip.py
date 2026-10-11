"""Límites por dirección IP.

Login (fallos): el bloqueo por email frena a quien ataca UNA cuenta; este frena a quien prueba
muchas cuentas distintas desde un mismo lugar. Es como el guardia del edificio: aparte del PIN
de cada puerta, vigila al que anda probando todas las puertas.

Registro y recuperación de contraseña (peticiones): frenan a quien crea cuentas en masa o usa la
app para llenar de correos el buzón de otras personas.

Los topes son altos porque en las redes móviles chilenas muchas personas comparten una misma IP
y no hay que castigar a inocentes. Reutiliza la tabla `intentos_login`: la clave es la huella de
la acción más la dirección, así la IP no se guarda en claro.
"""

import hashlib
from datetime import datetime, timezone

from app.casos_de_uso.puertos import RepositorioIntentosLogin
from app.dominio.bloqueo import registrar_fallo
from app.dominio.errores import DemasiadosIntentos

MAX_FALLOS_POR_IP = 30  # fallos de login
MAX_REGISTROS_POR_IP = 20  # peticiones a /registro en 15 minutos
MAX_RECUPERACIONES_POR_IP = 10  # peticiones a /recuperacion/solicitar en 15 minutos

ACCION_LOGIN = "login"
ACCION_REGISTRO = "registro"
ACCION_RECUPERACION = "recuperacion"


def clave_de_ip(ip: str, accion: str = ACCION_LOGIN) -> str:
    # El login conserva la clave de la versión anterior ("ip:<dirección>").
    base = f"ip:{ip}" if accion == ACCION_LOGIN else f"ip:{accion}:{ip}"
    return hashlib.sha256(base.encode()).hexdigest()


def verificar_ip(
    ip: str,
    intentos: RepositorioIntentosLogin,
    ahora: datetime | None = None,
    accion: str = ACCION_LOGIN,
) -> None:
    """Lanza DemasiadosIntentos si esa IP está bloqueada para esa acción."""
    ahora = ahora or datetime.now(timezone.utc)
    registro = intentos.obtener(clave_de_ip(ip, accion))
    if registro is not None and registro.esta_bloqueado(ahora):
        raise DemasiadosIntentos(registro.segundos_restantes(ahora))


def registrar_fallo_ip(
    ip: str,
    intentos: RepositorioIntentosLogin,
    ahora: datetime | None = None,
    accion: str = ACCION_LOGIN,
    maximo: int = MAX_FALLOS_POR_IP,
) -> None:
    ahora = ahora or datetime.now(timezone.utc)
    clave = clave_de_ip(ip, accion)
    intentos.guardar(registrar_fallo(intentos.obtener(clave), clave, ahora, maximo))


def limitar_peticiones_ip(
    ip: str,
    accion: str,
    maximo: int,
    intentos: RepositorioIntentosLogin,
    ahora: datetime | None = None,
) -> None:
    """Cuenta UNA petición; si la IP ya estaba bloqueada para esa acción, lanza el error."""
    ahora = ahora or datetime.now(timezone.utc)
    verificar_ip(ip, intentos, ahora, accion)
    registrar_fallo_ip(ip, intentos, ahora, accion, maximo)
