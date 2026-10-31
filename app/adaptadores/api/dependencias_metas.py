"""Pieza que las rutas de metas de ahorro piden: el repositorio de metas."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.adaptadores.api.dependencias import obtener_sesion
from app.infraestructura.repositorio_metas_sql import RepositorioMetasSQL


def obtener_repositorio_metas(
    sesion: Annotated[Session, Depends(obtener_sesion)],
) -> RepositorioMetasSQL:
    return RepositorioMetasSQL(sesion)
