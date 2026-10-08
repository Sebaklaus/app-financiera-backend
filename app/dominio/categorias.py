"""Las cuatro partes en que se reparte el dinero (regla 50/25/15/10)."""

from enum import Enum


class Categoria(str, Enum):
    NECESIDADES = "necesidades"  # 50 %
    INVERSION = "inversion"  # 25 %
    ESTABILIDAD = "estabilidad"  # 15 %
    ENTRETENIMIENTO = "entretenimiento"  # 10 %
