"""Adaptador de Fintoc (solo lectura): cuentas y movimientos de un enlace.

La clave secreta (FINTOC_SECRET_KEY) vive solo en el servidor; nunca viaja al teléfono ni a la
página. Usa la librería estándar (urllib) para no sumar dependencias.
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import date

from app.dominio.banco import (
    BancoNoDisponible,
    CuentaBancaria,
    EnlaceBancarioInvalido,
    MovimientoBancario,
)

URL_BASE = "https://api.fintoc.com/v1"
SEGUNDOS_DE_ESPERA = 10
POR_PAGINA = 100

# (url, clave secreta) -> (código HTTP, cuerpo). Se puede reemplazar en las pruebas.
Pedir = Callable[[str, str], tuple[int, str]]


def pedir_por_internet(url: str, clave: str) -> tuple[int, str]:
    # urlopen también acepta file:// y otros esquemas: solo se habla con la API de Fintoc.
    if not url.startswith(URL_BASE):
        raise ValueError("La dirección no pertenece a la API de Fintoc")
    peticion = urllib.request.Request(url, headers={"Authorization": clave})
    try:
        # La dirección se validó arriba: siempre es https://api.fintoc.com.
        with urllib.request.urlopen(  # nosec B310
            peticion, timeout=SEGUNDOS_DE_ESPERA
        ) as respuesta:
            return respuesta.status, respuesta.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise BancoNoDisponible("No se pudo conectar con Fintoc") from error


class ProveedorFintoc:
    def __init__(self, clave_secreta: str, pedir: Pedir = pedir_por_internet) -> None:
        self._clave = clave_secreta
        self._pedir = pedir

    def _get(self, ruta: str, parametros: dict[str, str | int]) -> list[dict]:
        url = f"{URL_BASE}{ruta}?{urllib.parse.urlencode(parametros)}"
        codigo, cuerpo = self._pedir(url, self._clave)
        if codigo >= 500:
            raise BancoNoDisponible("Fintoc no está disponible en este momento")
        if codigo != 200:
            raise EnlaceBancarioInvalido(
                "Fintoc rechazó la solicitud: revisa el link_token y la clave secreta"
            )
        try:
            datos = json.loads(cuerpo)
        except ValueError as error:
            raise BancoNoDisponible("Fintoc respondió algo inesperado") from error
        if not isinstance(datos, list):
            raise BancoNoDisponible("Fintoc respondió algo inesperado")
        return datos

    def listar_cuentas(self, link_token: str) -> list[CuentaBancaria]:
        filas = self._get("/accounts", {"link_token": link_token})
        try:
            return [_a_cuenta(fila) for fila in filas]
        except (ValueError, TypeError, AttributeError) as error:
            raise BancoNoDisponible("Fintoc respondió cuentas inesperadas") from error

    def listar_movimientos(self, link_token: str, cuenta_id: str) -> list[MovimientoBancario]:
        cuenta = urllib.parse.quote(cuenta_id, safe="")
        filas = self._get(
            f"/accounts/{cuenta}/movements",
            {"link_token": link_token, "per_page": POR_PAGINA},
        )
        try:
            return [_a_movimiento(fila) for fila in filas]
        except (ValueError, TypeError) as error:
            raise BancoNoDisponible("Fintoc respondió movimientos inesperados") from error


def _a_cuenta(fila: dict) -> CuentaBancaria:
    numero = str(fila.get("number") or "")
    saldo = (fila.get("balance") or {}).get("available")
    return CuentaBancaria(
        id=str(fila.get("id", "")),
        nombre=str(fila.get("name") or fila.get("official_name") or "Cuenta"),
        numero_enmascarado=("····" + numero[-4:]) if numero else "",
        moneda=str(fila.get("currency") or "CLP"),
        saldo=saldo if isinstance(saldo, int) else None,
    )


def _a_movimiento(fila: dict) -> MovimientoBancario:
    fecha_texto = str(fila.get("post_date") or fila.get("transaction_date") or "")[:10]
    return MovimientoBancario(
        id=str(fila.get("id", "")),
        fecha=date.fromisoformat(fecha_texto),
        monto=int(fila.get("amount", 0)),
        descripcion=str(fila.get("description") or fila.get("comment") or "Movimiento bancario"),
        moneda=str(fila.get("currency") or "CLP"),
    )
