"""Averigua la IP real de quien llama, sin dejarse engañar.

Detrás de un balanceador (Cloud Run, Cloud Armor), la IP de la conexión es la del balanceador y
la del cliente viene en el encabezado X-Forwarded-For. Pero ese encabezado lo puede escribir
cualquiera: solo se confía en las entradas que agregaron NUESTROS servidores, que van al final.

PROXIES_CONFIABLES = cuántos servidores nuestros hay delante de la app (0 = ninguno: se usa la
IP de la conexión directa). En Cloud Run suele ser 1.
"""

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import Request


def _proxies_confiables() -> int:
    try:
        return max(0, int(os.environ.get("PROXIES_CONFIABLES", "0")))
    except ValueError:
        return 0


def ip_del_cliente(request: "Request", proxies: int | None = None) -> str:
    proxies = _proxies_confiables() if proxies is None else proxies
    directa = request.client.host if request.client else "desconocida"
    if proxies <= 0:
        return directa
    cadena = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    if len(cadena) < proxies:
        return directa
    return cadena[-proxies]
