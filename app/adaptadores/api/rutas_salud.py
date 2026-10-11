"""Comprobación de que la app está lista para recibir tráfico (Cloud Run la usa al arrancar).

/salud (en rutas.py) responde si el programa vive. /salud/listo responde si además puede
hablar con la base de datos. Si falla, responde 503 sin contar por qué (no se filtran detalles).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.adaptadores.api.dependencias import obtener_sesion

router = APIRouter()


@router.get("/salud/listo", responses={503: {"description": "No hay conexión con la base"}})
def get_listo(sesion: Annotated[Session, Depends(obtener_sesion)]) -> dict[str, str]:
    try:
        sesion.execute(text("SELECT 1"))
    except Exception as error:
        raise HTTPException(503, "Servicio no disponible") from error
    return {"estado": "listo"}
