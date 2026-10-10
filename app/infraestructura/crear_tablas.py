"""Script: crea las tablas en la base de datos indicada en .env.

Se ejecuta así, desde la raíz del proyecto:  python -m app.infraestructura.crear_tablas
Es seguro repetirlo: solo crea las tablas que falten.
"""

from app.configuracion import url_base_de_datos
from app.infraestructura import (  # noqa: F401  (registran las tablas)
    repositorio_intentos_sql,
    repositorio_movimientos_sql,
    repositorio_tokens_sql,
)
from app.infraestructura.base_de_datos import crear_motor, crear_tablas


def main() -> None:
    motor = crear_motor(url_base_de_datos())
    crear_tablas(motor)
    print("Tablas creadas (o ya existían).")


if __name__ == "__main__":
    main()
