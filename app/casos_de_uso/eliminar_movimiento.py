"""Caso de uso: borrar un ingreso o un gasto propio."""

from uuid import UUID

from app.casos_de_uso.puertos import RepositorioMovimientos
from app.dominio.errores import MovimientoNoEncontrado


def eliminar_movimiento(
    usuario_id: UUID, movimiento_id: UUID, repositorio: RepositorioMovimientos
) -> None:
    if not repositorio.eliminar_movimiento(usuario_id, movimiento_id):
        raise MovimientoNoEncontrado("No existe ese movimiento")
