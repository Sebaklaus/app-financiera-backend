"""Pieza que las rutas de ingresos y gastos piden: el repositorio de movimientos."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.adaptadores.api.dependencias import obtener_sesion
from app.infraestructura.repositorio_movimientos_sql import RepositorioMovimientosSQL


def obtener_repositorio_movimientos(
    sesion: Annotated[Session, Depends(obtener_sesion)],
) -> RepositorioMovimientosSQL:
    return RepositorioMovimientosSQL(sesion)
