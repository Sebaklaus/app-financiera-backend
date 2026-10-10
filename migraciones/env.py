"""Conecta Alembic con nuestra base de datos y nuestras tablas."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.configuracion import url_base_de_datos
from app.infraestructura.modelos import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Las tablas que Alembic compara contra la base cuando se pide una migración automática.
target_metadata = Base.metadata


def _url() -> str:
    # Si quien llama indica una dirección (las pruebas lo hacen), se usa esa y NUNCA la real.
    return config.get_main_option("sqlalchemy.url") or url_base_de_datos()


def run_migrations_offline() -> None:
    """Genera el SQL sin conectarse (alembic upgrade head --sql)."""
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    motor = create_engine(_url())
    with motor.connect() as conexion:
        context.configure(connection=conexion, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
    motor.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
