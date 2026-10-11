"""Cabeceras de seguridad en todas las respuestas.

Son instrucciones que la API le da al navegador para cerrar puertas que no necesita:
- no adivinar tipos de archivo, no mostrarse dentro de otra página, no filtrar la dirección de
  origen, usar siempre HTTPS, y no guardar copias de respuestas con datos financieros.
Las páginas de documentación (/docs, /redoc) cargan scripts de afuera y se dejan sin las dos
cabeceras que las romperían.
"""

from fastapi import FastAPI, Request

_DOCUMENTACION = ("/docs", "/redoc", "/openapi.json")

_BASE = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}
_SOLO_API = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}


def aplicar_cabeceras_seguridad(app: FastAPI) -> None:
    @app.middleware("http")
    async def agregar_cabeceras(request: Request, call_next):
        respuesta = await call_next(request)
        cabeceras = dict(_BASE)
        if not request.url.path.startswith(_DOCUMENTACION):
            cabeceras.update(_SOLO_API)
        for nombre, valor in cabeceras.items():
            respuesta.headers.setdefault(nombre, valor)
        return respuesta
