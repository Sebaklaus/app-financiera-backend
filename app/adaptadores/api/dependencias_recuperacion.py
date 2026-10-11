"""Piezas que las rutas de recuperación de contraseña piden."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.adaptadores.api.dependencias import obtener_sesion
from app.infraestructura.enviador_correo import EnviadorCorreoConsola, crear_enviador
from app.infraestructura.repositorio_recuperacion_sql import RepositorioRecuperacionSQL


def obtener_repositorio_recuperacion(
    sesion: Annotated[Session, Depends(obtener_sesion)],
) -> RepositorioRecuperacionSQL:
    return RepositorioRecuperacionSQL(sesion)


@lru_cache
def obtener_enviador_correo() -> EnviadorCorreoConsola:
    return crear_enviador()
