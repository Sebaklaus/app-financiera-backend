"""Script: crea las tablas en una base NUEVA y vacía, sin migraciones.

    python -m app.infraestructura.crear_tablas

Solo sirve para pruebas rápidas. Para la base real se usan las migraciones (Alembic):

    alembic upgrade head

No mezcles ambos en la misma base: si las tablas ya existen, Alembic no sabrá en qué
versión está (en ese caso se marca con `alembic stamp head`).
"""

from app.configuracion import url_base_de_datos
from app.infraestructura import modelos  # noqa: F401  (registra todas las tablas)
from app.infraestructura.base_de_datos import crear_motor, crear_tablas


def main() -> None:
    motor = crear_motor(url_base_de_datos())
    crear_tablas(motor)
    print("Tablas creadas (o ya existían). Para la base real usa: alembic upgrade head")


if __name__ == "__main__":
    main()
