"""Conexión con el banco (solo lectura): cuentas y movimientos que informa el proveedor.

Dominio puro. Los montos son pesos chilenos enteros; el movimiento es POSITIVO si entra dinero
a la cuenta (abono) y NEGATIVO si sale (cargo).
"""

from dataclasses import dataclass
from datetime import date

from app.dominio.errores import ErrorDeDominio


class EnlaceBancarioInvalido(ErrorDeDominio):
    """El proveedor no reconoce el enlace (link_token) o rechazó la solicitud."""


class SinEnlaceBancario(ErrorDeDominio):
    """La persona todavía no ha conectado su banco."""


class BancoNoDisponible(ErrorDeDominio):
    """El proveedor (Fintoc) no respondió o falló. Se puede reintentar más tarde."""


@dataclass(frozen=True)
class CuentaBancaria:
    id: str
    nombre: str
    numero_enmascarado: str  # solo los últimos dígitos
    moneda: str
    saldo: int | None


@dataclass(frozen=True)
class MovimientoBancario:
    id: str
    fecha: date
    monto: int  # positivo = abono, negativo = cargo
    descripcion: str
    moneda: str
