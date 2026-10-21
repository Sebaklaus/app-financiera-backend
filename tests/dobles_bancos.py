"""Doble de prueba del banco: responde lo que la prueba le ordene, sin salir a Internet."""

from datetime import date

from app.dominio.banco import (
    BancoNoDisponible,
    CuentaBancaria,
    EnlaceBancarioInvalido,
    MovimientoBancario,
)

CUENTA = CuentaBancaria(
    id="acc_1",
    nombre="Cuenta corriente",
    numero_enmascarado="····1234",
    moneda="CLP",
    saldo=500000,
)
ABONO = MovimientoBancario("mov_1", date(2026, 10, 1), 1_000_000, "Sueldo octubre", "CLP")
CARGO = MovimientoBancario("mov_2", date(2026, 10, 2), -45_000, "Supermercado", "CLP")


class ProveedorBancarioFalso:
    def __init__(self) -> None:
        self.link_valido = "link_ok"
        self.caido = False
        self.cuentas = [CUENTA]
        self.movimientos = [ABONO, CARGO]
        self.consultas: list[str] = []

    def _revisar(self, link_token: str) -> None:
        self.consultas.append(link_token)
        if self.caido:
            raise BancoNoDisponible("Fintoc no está disponible en este momento")
        if link_token != self.link_valido:
            raise EnlaceBancarioInvalido("Fintoc rechazó la solicitud")

    def listar_cuentas(self, link_token: str) -> list[CuentaBancaria]:
        self._revisar(link_token)
        return list(self.cuentas)

    def listar_movimientos(self, link_token: str, cuenta_id: str) -> list[MovimientoBancario]:
        self._revisar(link_token)
        return list(self.movimientos)


class EnlacesEnMemoria:
    def __init__(self) -> None:
        self.datos: dict = {}

    def guardar(self, usuario_id, link_token: str) -> None:
        self.datos[usuario_id] = link_token

    def obtener(self, usuario_id):
        return self.datos.get(usuario_id)

    def eliminar(self, usuario_id) -> bool:
        return self.datos.pop(usuario_id, None) is not None
