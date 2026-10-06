"""Regla de distribución 50/25/15/10 (dominio puro).

Esta capa no conoce FastAPI, la base de datos ni Fintoc: solo reglas de negocio.
Los montos son enteros en pesos chilenos (CLP no usa decimales en la práctica).
"""

from dataclasses import dataclass

PCT_INVERSION = 25
PCT_estabilidad = 15
PCT_entretenimiento = 10
# Necesidades es el 50 % restante: se calcula por diferencia, ver `distribuir`.


@dataclass(frozen=True)
class Distribucion:
    necesidades: int
    inversion: int
    estabilidad: int
    entretenimiento: int

    @property
    def total(self) -> int:
        return self.necesidades + self.inversion + self.estabilidad + self.entretenimiento


def distribuir(monto: int) -> Distribucion:
    """Reparte `monto` (pesos enteros) en las cuatro partes.

    Como el reparto rara vez es exacto (con $100.001 no se puede dar 25 % exacto),
    inversión, estabilidad y entretenimiento se redondean hacia abajo y los pesos sobrantes
    (menos de 3 en total) se suman a necesidades. Así la suma de las partes es siempre
    igual al monto original.
    """
    if isinstance(monto, bool) or not isinstance(monto, int):
        raise TypeError("El monto debe ser un entero en pesos")
    if monto <= 0:
        raise ValueError("El monto debe ser mayor que cero")

    inversion = monto * PCT_INVERSION // 100
    estabilidad = monto * PCT_estabilidad // 100
    entretenimiento = monto * PCT_entretenimiento // 100
    necesidades = monto - inversion - estabilidad - entretenimiento
    return Distribucion(necesidades, inversion, estabilidad, entretenimiento)
