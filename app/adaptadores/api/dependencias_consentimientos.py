"""Pieza que las rutas de consentimientos piden: su repositorio."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.adaptadores.api.dependencias import obtener_sesion
from app.infraestructura.repositorio_consentimientos_sql import RepositorioConsentimientosSQL


def obtener_repositorio_consentimientos(
    sesion: Annotated[Session, Depends(obtener_sesion)],
) -> RepositorioConsentimientosSQL:
    return RepositorioConsentimientosSQL(sesion)
