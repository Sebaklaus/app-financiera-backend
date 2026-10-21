"""Casos de uso de la conexión bancaria (solo lectura).

Regla de oro del proyecto: el dinero nunca pasa por la app. Aquí solo se LEE lo que el banco
informa y, si la persona lo pide, se importan los abonos como ingresos para proponerle su
reparto 50/25/15/10 (que ella debe confirmar).
"""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

from app.casos_de_uso.puertos import RepositorioMovimientos
from app.casos_de_uso.puertos_bancos import ProveedorBancario, RepositorioEnlaces
from app.casos_de_uso.registrar_ingreso import registrar_ingreso
from app.dominio.banco import (
    CuentaBancaria,
    EnlaceBancarioInvalido,
    MovimientoBancario,
    SinEnlaceBancario,
)
from app.dominio.errores import MovimientoInvalido
from app.dominio.movimiento import DESCRIPCION_MAXIMA
from app.dominio.reloj import hoy_en_chile

LARGO_MAXIMO_LINK = 200


@dataclass(frozen=True)
class ResultadoImportacion:
    importados: int
    ya_importados: int
    cargos_omitidos: int


def _enlace_de(usuario_id: UUID, enlaces: RepositorioEnlaces) -> str:
    link = enlaces.obtener(usuario_id)
    if link is None:
        raise SinEnlaceBancario("Primero conecta tu banco")
    return link


def conectar_banco(
    usuario_id: UUID,
    link_token: str,
    enlaces: RepositorioEnlaces,
    proveedor: ProveedorBancario,
) -> list[CuentaBancaria]:
    """Valida el enlace consultando las cuentas; solo si funciona lo guarda."""
    link = link_token.strip()
    if not link or len(link) > LARGO_MAXIMO_LINK:
        raise EnlaceBancarioInvalido("El enlace del banco no es válido")
    cuentas = proveedor.listar_cuentas(link)
    enlaces.guardar(usuario_id, link)
    return cuentas


def desconectar_banco(usuario_id: UUID, enlaces: RepositorioEnlaces) -> bool:
    return enlaces.eliminar(usuario_id)


def cuentas_del_banco(
    usuario_id: UUID, enlaces: RepositorioEnlaces, proveedor: ProveedorBancario
) -> list[CuentaBancaria]:
    return proveedor.listar_cuentas(_enlace_de(usuario_id, enlaces))


def movimientos_del_banco(
    usuario_id: UUID, cuenta_id: str, enlaces: RepositorioEnlaces, proveedor: ProveedorBancario
) -> list[MovimientoBancario]:
    return proveedor.listar_movimientos(_enlace_de(usuario_id, enlaces), cuenta_id)


def _descripcion(movimiento: MovimientoBancario) -> str:
    """El id del banco va en la descripción: así un abono no se importa dos veces."""
    return f"[{movimiento.id}] {movimiento.descripcion}"[:DESCRIPCION_MAXIMA]


def importar_abonos(
    usuario_id: UUID,
    cuenta_id: str,
    enlaces: RepositorioEnlaces,
    proveedor: ProveedorBancario,
    repositorio: RepositorioMovimientos,
    hoy: date | None = None,
) -> ResultadoImportacion:
    """Importa los abonos como ingresos (con su propuesta de reparto). Los cargos no se tocan."""
    hoy = hoy or hoy_en_chile(datetime.now(timezone.utc))
    movimientos = movimientos_del_banco(usuario_id, cuenta_id, enlaces, proveedor)
    existentes = {m.descripcion for m in repositorio.listar_por_usuario(usuario_id)}
    importados = ya_importados = cargos = 0
    for movimiento in movimientos:
        if movimiento.monto <= 0:
            cargos += 1
            continue
        descripcion = _descripcion(movimiento)
        if descripcion in existentes:
            ya_importados += 1
            continue
        try:
            registrar_ingreso(
                usuario_id,
                movimiento.monto,
                descripcion,
                min(movimiento.fecha, hoy),
                repositorio,
                hoy=hoy,
            )
        except MovimientoInvalido:
            cargos += 1  # monto fuera de rango: se omite
            continue
        existentes.add(descripcion)
        importados += 1
    return ResultadoImportacion(importados, ya_importados, cargos)
