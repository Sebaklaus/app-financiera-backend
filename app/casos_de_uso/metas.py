"""Casos de uso de las metas de ahorro (CU-08)."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from app.casos_de_uso.puertos_metas import RepositorioMetas
from app.dominio.errores import MetaNoEncontrada
from app.dominio.meta import (
    Aporte,
    MetaAhorro,
    ProgresoMeta,
    calcular_progreso,
    validar_fecha_aporte,
    validar_fecha_limite,
    validar_monto,
    validar_nombre,
)
from app.dominio.reloj import hoy_en_chile


@dataclass(frozen=True)
class DetalleMeta:
    progreso: ProgresoMeta
    aportes: list[Aporte]


def crear_meta(
    usuario_id: UUID,
    nombre: str,
    monto_objetivo: int,
    fecha_limite: date | None,
    repositorio: RepositorioMetas,
    hoy: date | None = None,
) -> ProgresoMeta:
    ahora = datetime.now(timezone.utc)
    hoy = hoy or hoy_en_chile(ahora)
    meta = MetaAhorro(
        id=uuid4(),
        usuario_id=usuario_id,
        nombre=validar_nombre(nombre),
        monto_objetivo=validar_monto(monto_objetivo),
        fecha_limite=validar_fecha_limite(fecha_limite, hoy),
        creada_en=ahora,
    )
    repositorio.guardar_meta(meta)
    return calcular_progreso(meta, 0)


def listar_metas(usuario_id: UUID, repositorio: RepositorioMetas) -> list[ProgresoMeta]:
    totales = repositorio.total_aportado(usuario_id)
    return [
        calcular_progreso(meta, totales.get(meta.id, 0))
        for meta in repositorio.listar_metas(usuario_id)
    ]


def obtener_meta(usuario_id: UUID, meta_id: UUID, repositorio: RepositorioMetas) -> DetalleMeta:
    meta = repositorio.buscar_meta(usuario_id, meta_id)
    if meta is None:
        raise MetaNoEncontrada("No existe esa meta")
    aportes = repositorio.listar_aportes(usuario_id, meta_id)
    return DetalleMeta(calcular_progreso(meta, sum(a.monto for a in aportes)), aportes)


def aportar_a_meta(
    usuario_id: UUID,
    meta_id: UUID,
    monto: int,
    fecha: date | None,
    repositorio: RepositorioMetas,
    hoy: date | None = None,
) -> DetalleMeta:
    """Anota un aporte (la app no mueve dinero: solo lleva la cuenta) y devuelve el avance."""
    if repositorio.buscar_meta(usuario_id, meta_id) is None:
        raise MetaNoEncontrada("No existe esa meta")
    ahora = datetime.now(timezone.utc)
    hoy = hoy or hoy_en_chile(ahora)
    aporte = Aporte(
        id=uuid4(),
        meta_id=meta_id,
        usuario_id=usuario_id,
        monto=validar_monto(monto),
        fecha=validar_fecha_aporte(fecha or hoy, hoy),
        creado_en=ahora,
    )
    repositorio.guardar_aporte(aporte)
    return obtener_meta(usuario_id, meta_id, repositorio)


def eliminar_meta(usuario_id: UUID, meta_id: UUID, repositorio: RepositorioMetas) -> None:
    if not repositorio.eliminar_meta(usuario_id, meta_id):
        raise MetaNoEncontrada("No existe esa meta")
