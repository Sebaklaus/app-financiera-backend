"""Arma las piezas que cada petición necesita (sesión, repositorio, hasheador).

FastAPI las "inyecta" en las rutas: la ruta pide un repositorio y no sabe cómo se construye.
La conexión a la base se crea la primera vez que se necesita, no al importar el archivo.
"""

from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session, sessionmaker

from app.configuracion import url_base_de_datos
from app.infraestructura.base_de_datos import crear_fabrica_sesiones, crear_motor
from app.infraestructura.hasheador_bcrypt import HasheadorBcrypt
from app.infraestructura.repositorio_usuarios_sql import RepositorioUsuariosSQL


@lru_cache
def _fabrica_de_sesiones() -> sessionmaker[Session]:
    return crear_fabrica_sesiones(crear_motor(url_base_de_datos()))


def obtener_sesion() -> Iterator[Session]:
    with _fabrica_de_sesiones()() as sesion:
        yield sesion


def obtener_repositorio_usuarios(
    sesion: Annotated[Session, Depends(obtener_sesion)],
) -> RepositorioUsuariosSQL:
    return RepositorioUsuariosSQL(sesion)


def obtener_hasheador() -> HasheadorBcrypt:
    return HasheadorBcrypt()  # costo 12, como dice el informe
