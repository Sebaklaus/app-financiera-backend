"""Caso de uso: registrar un ingreso y PROPONER su reparto 50/25/15/10 (HU-28, HU-12)."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from app.casos_de_uso.puertos import RepositorioMovimientos
from app.dominio.categorias import Categoria
from app.dominio.confirmacion import Confirmacion, proponer
from app.dominio.movimiento import (
    Movimiento,
    TipoMovimiento,
    repartir,
    validar_descripcion,
    validar_fecha,
    validar_monto,
)
from app.dominio.reloj import hoy_en_chile


@dataclass(frozen=True)
class ResultadoIngreso:
    movimiento: Movimiento
    reparto: dict[Categoria, int]
    confirmaciones: list[Confirmacion]  # lo que la persona debe aceptar o rechazar


def registrar_ingreso(
    usuario_id: UUID,
    monto: int,
    descripcion: str,
    fecha: date | None,
    repositorio: RepositorioMovimientos,
    hoy: date | None = None,
) -> ResultadoIngreso:
    ahora = datetime.now(timezone.utc)
    hoy = hoy or hoy_en_chile(ahora)
    movimiento = Movimiento(
        id=uuid4(),
        usuario_id=usuario_id,
        tipo=TipoMovimiento.INGRESO,
        monto=validar_monto(monto),
        categoria=None,
        descripcion=validar_descripcion(descripcion),
        fecha=validar_fecha(fecha or hoy, hoy),
        creado_en=ahora,
    )
    reparto = repartir(movimiento.monto)
    confirmaciones = proponer(movimiento, reparto, ahora)
    repositorio.guardar_ingreso(movimiento, confirmaciones)
    return ResultadoIngreso(movimiento, reparto, confirmaciones)
