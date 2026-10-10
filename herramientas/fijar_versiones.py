"""Fija las versiones de requirements.txt a las que tienes instaladas ahora mismo.

Uso, desde la raíz del proyecto y con el entorno virtual activado:

    python -m herramientas.fijar_versiones

Lee tu requirements.txt, y a cada librería le pone la versión exacta que tienes instalada
(por ejemplo, "fastapi" pasa a "fastapi==0.115.0"). Así todos instalan lo mismo, y una
actualización inesperada de una librería no rompe el proyecto de un día para otro.

Antes de escribir, guarda una copia en requirements.txt.antes.
"""

import re
import sys
from collections.abc import Callable
from importlib import metadata
from pathlib import Path

ARCHIVO = Path("requirements.txt")
RESPALDO = Path("requirements.txt.antes")

# nombre (con guiones o puntos), extras opcionales como [binary], y lo que venga después
_LINEA = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(\[[^\]]*\])?\s*(.*)$")


class LibreriaNoInstalada(Exception):
    pass


def version_instalada(nombre: str) -> str:
    try:
        return metadata.version(nombre)
    except metadata.PackageNotFoundError as error:
        raise LibreriaNoInstalada(nombre) from error


def fijar(lineas: list[str], obtener_version: Callable[[str], str]) -> list[str]:
    """Devuelve las líneas con cada librería fijada a una versión exacta (==).

    Los comentarios, las líneas vacías y las opciones (-r, -e, --index-url...) no se tocan.
    """
    resultado = []
    for linea in lineas:
        texto = linea.strip()
        if not texto or texto.startswith(("#", "-")):
            resultado.append(linea.rstrip("\n"))
            continue
        coincide = _LINEA.match(texto)
        if coincide is None:
            resultado.append(linea.rstrip("\n"))
            continue
        nombre, extras, resto = coincide.group(1), coincide.group(2) or "", coincide.group(3)
        # Un comentario al final de la línea ("# para pruebas") se conserva.
        comentario = ""
        if "#" in resto:
            comentario = "  " + resto[resto.index("#") :]
        resultado.append(f"{nombre}{extras}=={obtener_version(nombre)}{comentario}")
    return resultado


def main() -> int:
    if not ARCHIVO.exists():
        print("No encuentro requirements.txt: ejecuta esto desde la raíz del proyecto.")
        return 1
    original = ARCHIVO.read_text(encoding="utf-8").splitlines()
    try:
        fijadas = fijar(original, version_instalada)
    except LibreriaNoInstalada as error:
        print(f"La librería '{error}' no está instalada en este entorno virtual.")
        print(
            "Activa el entorno (.venv) o instala las librerías con: pip install -r requirements.txt"
        )
        return 1
    RESPALDO.write_text("\n".join(original) + "\n", encoding="utf-8")
    ARCHIVO.write_text("\n".join(fijadas) + "\n", encoding="utf-8")
    print(f"Listo. Copia del archivo anterior en {RESPALDO}. Quedó así:\n")
    print("\n".join(fijadas))
    return 0


if __name__ == "__main__":
    sys.exit(main())
