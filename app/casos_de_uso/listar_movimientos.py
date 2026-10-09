"""Caso de uso: listar los movimientos propios, todos o de un solo mes."""

from uuid import UUID

from app.casos_de_uso.puertos import RepositorioMovimientos
from app.dominio.movimiento import Movimiento
from app.dominio.periodo import Periodo


def listar_movimientos(
    usuario_id: UUID, repositorio: RepositorioMovimientos, periodo: Periodo | None = None
) -> list[Movimiento]:
    movimientos = repositorio.listar_por_usuario(usuario_id)
    if periodo is None:
        return movimientos
    return [m for m in movimientos if periodo.contiene(m.fecha)]
