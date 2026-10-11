"""Pieza que las rutas de la cuenta piden: el repositorio de la cuenta."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.adaptadores.api.dependencias import obtener_sesion
from app.infraestructura.repositorio_cuenta_sql import RepositorioCuentaSQL


def obtener_repositorio_cuenta(
    sesion: Annotated[Session, Depends(obtener_sesion)],
) -> RepositorioCuentaSQL:
    return RepositorioCuentaSQL(sesion)
