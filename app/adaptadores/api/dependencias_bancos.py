"""Piezas que las rutas bancarias piden: repositorio de enlaces y proveedor (Fintoc)."""

import os
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.adaptadores.api.dependencias import obtener_sesion
from app.infraestructura.cifrador import CifradorFernet
from app.infraestructura.proveedor_fintoc import ProveedorFintoc
from app.infraestructura.repositorio_enlaces_sql import RepositorioEnlacesSQL

load_dotenv()


def obtener_repositorio_enlaces(
    sesion: Annotated[Session, Depends(obtener_sesion)],
) -> RepositorioEnlacesSQL:
    clave = os.getenv("FINTOC_CLAVE_CIFRADO")
    if not clave:
        raise HTTPException(503, "La conexión bancaria no está configurada (falta la clave)")
    try:
        return RepositorioEnlacesSQL(sesion, CifradorFernet(clave))
    except ValueError as error:
        raise HTTPException(
            503, "La clave de cifrado de la conexión bancaria no es válida"
        ) from error


def obtener_proveedor_bancario() -> ProveedorFintoc:
    clave = os.getenv("FINTOC_SECRET_KEY")
    if not clave:
        raise HTTPException(503, "La conexión bancaria no está configurada (falta Fintoc)")
    return ProveedorFintoc(clave)
