"""Puerto de las metas de ahorro: dónde se guardan metas y aportes."""

from typing import Protocol
from uuid import UUID

from app.dominio.meta import Aporte, MetaAhorro


class RepositorioMetas(Protocol):
    def guardar_meta(self, meta: MetaAhorro) -> None: ...

    def listar_metas(self, usuario_id: UUID) -> list[MetaAhorro]:
        """Las metas de ESA persona, la más reciente primero."""
        ...

    def buscar_meta(self, usuario_id: UUID, meta_id: UUID) -> MetaAhorro | None:
        """None si no existe o si pertenece a otra persona."""
        ...

    def guardar_aporte(self, aporte: Aporte) -> None: ...

    def listar_aportes(self, usuario_id: UUID, meta_id: UUID) -> list[Aporte]:
        """Los aportes de ESA meta, el más reciente primero."""
        ...

    def total_aportado(self, usuario_id: UUID) -> dict[UUID, int]:
        """Cuánto se ha aportado a cada meta de ESA persona (las metas sin aportes no salen)."""
        ...

    def eliminar_meta(self, usuario_id: UUID, meta_id: UUID) -> bool:
        """Borra la meta y sus aportes. False si no existía o era de otra persona."""
        ...
