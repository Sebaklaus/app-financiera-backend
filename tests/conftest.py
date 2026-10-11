"""Configuración común de las pruebas.

Las pruebas NUNCA deben tocar tu base de datos real. Antes de que se cargue cualquier archivo
de la app, se apunta DATABASE_URL a una base en memoria vacía: si una prueba olvida reemplazar
la base por la suya, falla de inmediato (tabla inexistente) en vez de leer o escribir en la
base de desarrollo. Así los resultados son iguales en tu computador y en GitHub Actions.
"""

import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
