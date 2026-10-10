"""Comprueba que las migraciones de Alembic y las tablas del código dicen lo mismo.

Es la red de seguridad: si alguien cambia una tabla en el código y olvida crear la
migración, esta prueba falla (y GitHub Actions avisa antes de que llegue a la base real).
Trabaja sobre un archivo SQLite temporal, nunca sobre la base real.
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.infraestructura.modelos import Base

RAIZ = Path(__file__).resolve().parent.parent
TABLAS = {"usuarios", "movimientos", "confirmaciones", "tokens_refresco", "intentos_login"}


@pytest.fixture
def base(tmp_path):
    """Una base SQLite vacía y la configuración de Alembic apuntando a ella."""
    url = f"sqlite:///{(tmp_path / 'prueba.db').as_posix()}"
    config = Config(str(RAIZ / "alembic.ini"))
    config.set_main_option("script_location", str(RAIZ / "migraciones"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config, create_engine(url)


def test_upgrade_crea_todas_las_tablas(base):
    config, motor = base
    command.upgrade(config, "head")
    assert TABLAS <= set(inspect(motor).get_table_names())


def test_las_migraciones_y_el_codigo_no_se_contradicen(base):
    config, motor = base
    command.upgrade(config, "head")
    with motor.connect() as conexion:
        contexto = MigrationContext.configure(conexion, opts={"compare_type": False})
        diferencias = compare_metadata(contexto, Base.metadata)
    assert diferencias == [], f"Falta una migración para estos cambios: {diferencias}"


def test_downgrade_deja_la_base_vacia(base):
    config, motor = base
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    assert not (TABLAS & set(inspect(motor).get_table_names()))


def test_repetir_upgrade_no_falla(base):
    config, motor = base
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    assert TABLAS <= set(inspect(motor).get_table_names())
