"""Caso de uso: qué propuestas de reparto está esperando decidir esta persona."""

from uuid import UUID

from app.casos_de_uso.puertos import RepositorioMovimientos
from app.dominio.confirmacion import Confirmacion, EstadoConfirmacion


def listar_confirmaciones_pendientes(
    usuario_id: UUID, repositorio: RepositorioMovimientos
) -> list[Confirmacion]:
    todas = repositorio.listar_confirmaciones_por_usuario(usuario_id)
    return [c for c in todas if c.estado is EstadoConfirmacion.PENDIENTE]
