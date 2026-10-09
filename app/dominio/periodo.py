"""Un mes calendario (por ejemplo, octubre de 2026). Dominio puro."""

from dataclasses import dataclass
from datetime import date

from app.dominio.errores import MovimientoInvalido


@dataclass(frozen=True)
class Periodo:
    anio: int
    mes: int

    def __post_init__(self) -> None:
        if not (1 <= self.mes <= 12) or not (1 <= self.anio <= 9999):
            raise MovimientoInvalido("El mes debe tener el formato AAAA-MM, por ejemplo 2026-10")

    @classmethod
    def desde_texto(cls, texto: str) -> "Periodo":
        """Lee "2026-10". Cualquier otra forma se rechaza."""
        partes = texto.split("-")
        formato_ok = len(partes) == 2 and len(partes[0]) == 4 and len(partes[1]) == 2
        if not formato_ok or not all(p.isascii() and p.isdigit() for p in partes):
            raise MovimientoInvalido("El mes debe tener el formato AAAA-MM, por ejemplo 2026-10")
        return cls(int(partes[0]), int(partes[1]))

    def contiene(self, fecha: date) -> bool:
        return fecha.year == self.anio and fecha.month == self.mes

    def __str__(self) -> str:
        return f"{self.anio:04d}-{self.mes:02d}"
