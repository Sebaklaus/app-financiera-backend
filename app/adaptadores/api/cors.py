"""CORS: qué páginas web pueden hablar con la API desde un navegador.

Analogía: es la lista de invitados en la puerta. Si no estás en la lista, el navegador
no te deja entrar, aunque tengas la dirección correcta.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def aplicar_cors(app: FastAPI, origenes: list[str]) -> None:
    if not origenes:
        return
    if "*" in origenes:
        raise RuntimeError("CORS_ORIGINS no puede ser '*': lista las direcciones exactas.")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origenes,
        allow_credentials=False,  # los tokens viajan en el encabezado Authorization, no en cookies
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        max_age=600,
    )
