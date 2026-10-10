"""Lista de TODAS las tablas de la aplicación.

Importar este archivo basta para que SQLAlchemy (y Alembic) conozcan todas las tablas.
Cuando se agregue una tabla nueva, se anota su archivo aquí, y solo aquí.
"""

from app.infraestructura import (  # noqa: F401  (registran las tablas)
    repositorio_intentos_sql,
    repositorio_movimientos_sql,
    repositorio_tokens_sql,
)
from app.infraestructura.base_de_datos import Base, UsuarioTabla  # noqa: F401

__all__ = ["Base"]
