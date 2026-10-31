"""Doble de prueba de las metas de ahorro: un repositorio que vive en memoria."""

from uuid import UUID

from app.dominio.meta import Aporte, MetaAhorro


class RepositorioMetasEnMemoria:
    def __init__(self) -> None:
        self.metas: dict[UUID, MetaAhorro] = {}
        self.aportes: list[Aporte] = []

    def guardar_meta(self, meta: MetaAhorro) -> None:
        self.metas[meta.id] = meta

    def listar_metas(self, usuario_id: UUID) -> list[MetaAhorro]:
        propias = [m for m in self.metas.values() if m.usuario_id == usuario_id]
        return sorted(propias, key=lambda m: m.creada_en, reverse=True)

    def buscar_meta(self, usuario_id: UUID, meta_id: UUID) -> MetaAhorro | None:
        meta = self.metas.get(meta_id)
        return meta if meta is not None and meta.usuario_id == usuario_id else None

    def guardar_aporte(self, aporte: Aporte) -> None:
        self.aportes.append(aporte)

    def listar_aportes(self, usuario_id: UUID, meta_id: UUID) -> list[Aporte]:
        propios = [
            a for a in self.aportes if a.usuario_id == usuario_id and a.meta_id == meta_id
        ]
        return sorted(propios, key=lambda a: (a.fecha, a.creado_en), reverse=True)

    def total_aportado(self, usuario_id: UUID) -> dict[UUID, int]:
        totales: dict[UUID, int] = {}
        for aporte in self.aportes:
            if aporte.usuario_id == usuario_id:
                totales[aporte.meta_id] = totales.get(aporte.meta_id, 0) + aporte.monto
        return totales

    def eliminar_meta(self, usuario_id: UUID, meta_id: UUID) -> bool:
        if self.buscar_meta(usuario_id, meta_id) is None:
            return False
        del self.metas[meta_id]
        self.aportes = [a for a in self.aportes if a.meta_id != meta_id]
        return True
