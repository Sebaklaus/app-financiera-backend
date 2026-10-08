"""Caso de uso: registrar un ingreso y repartirlo con la regla 50/25/15/10 (HU-28)."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from app.casos_de_uso.puertos import RepositorioMovimientos
from app.dominio.categorias import Categoria
from app.dominio.movimiento import (
    Movimiento,
    TipoMovimiento,
    repartir,
    validar_descripcion,
    validar_fecha,
    validar_monto,
)


@dataclass(frozen=True)
class ResultadoIngreso:
    movimiento: Movimiento
    reparto: dict[Categoria, int]


def registrar_ingreso(
    usuario_id: UUID,
    monto: int,
    descripcion: str,
    fecha: date | None,
    repositorio: RepositorioMovimientos,
    hoy: date | None = None,
) -> ResultadoIngreso:
    hoy = hoy or datetime.now(timezone.utc).date()
    movimiento = Movimiento(
        id=uuid4(),
        usuario_id=usuario_id,
        tipo=TipoMovimiento.INGRESO,
        monto=validar_monto(monto),
        categoria=None,
        descripcion=validar_descripcion(descripcion),
        fecha=validar_fecha(fecha or hoy, hoy),
        creado_en=datetime.now(timezone.utc),
    )
    repositorio.guardar(movimiento)
    return ResultadoIngreso(movimiento, repartir(movimiento.monto))
