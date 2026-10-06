"""Caso de uso: calcular cómo se reparte un monto.

Hoy solo delega en el dominio. Más adelante aquí se agregará lo que el dominio
no debe saber: guardar el resultado, pedir la confirmación del 25 % y 15 %, etc.
"""

from app.dominio.distribucion import Distribucion, distribuir


def calcular_distribucion(monto: int) -> Distribucion:
    return distribuir(monto)
