"""Límite de fallos de login por dirección IP.

El bloqueo por email frena a quien ataca UNA cuenta. Este frena a quien prueba muchas cuentas
distintas desde un mismo lugar (por ejemplo, una lista de emails filtrados). Es como el guardia
del edificio: aparte del PIN de cada puerta, vigila al que anda probando todas las puertas.

El tope es más alto que el de un email (30 en vez de 5) porque en las redes móviles chilenas
muchas personas comparten una misma IP y no hay que castigar a inocentes.
Reutiliza la tabla `intentos_login`: la clave es la huella de "ip:" + la dirección.
"""

import hashlib
from datetime import datetime, timezone

from app.casos_de_uso.puertos import RepositorioIntentosLogin
from app.dominio.bloqueo import registrar_fallo
from app.dominio.errores import DemasiadosIntentos

MAX_FALLOS_POR_IP = 30


def clave_de_ip(ip: str) -> str:
    return hashlib.sha256(f"ip:{ip}".encode()).hexdigest()


def verificar_ip(
    ip: str, intentos: RepositorioIntentosLogin, ahora: datetime | None = None
) -> None:
    """Lanza DemasiadosIntentos si esa IP está bloqueada."""
    ahora = ahora or datetime.now(timezone.utc)
    registro = intentos.obtener(clave_de_ip(ip))
    if registro is not None and registro.esta_bloqueado(ahora):
        raise DemasiadosIntentos(registro.segundos_restantes(ahora))


def registrar_fallo_ip(
    ip: str, intentos: RepositorioIntentosLogin, ahora: datetime | None = None
) -> None:
    ahora = ahora or datetime.now(timezone.utc)
    clave = clave_de_ip(ip)
    intentos.guardar(registrar_fallo(intentos.obtener(clave), clave, ahora, MAX_FALLOS_POR_IP))
