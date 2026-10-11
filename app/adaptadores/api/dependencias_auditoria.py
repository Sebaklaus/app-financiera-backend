"""Pieza que las rutas piden para anotar eventos de seguridad."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.adaptadores.api.dependencias import obtener_sesion
from app.infraestructura.repositorio_eventos_sql import RepositorioEventosSQL


def obtener_repositorio_eventos(
    sesion: Annotated[Session, Depends(obtener_sesion)],
) -> RepositorioEventosSQL:
    return RepositorioEventosSQL(sesion)
