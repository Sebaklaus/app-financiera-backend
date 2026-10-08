"""Caso de uso: registrar un gasto contra una de las cuatro categorías (HU-28)."""

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from app.casos_de_uso.puertos import RepositorioMovimientos
from app.dominio.categorias import Categoria
from app.dominio.errores import MovimientoInvalido
from app.dominio.movimiento import (
    Movimiento,
    TipoMovimiento,
    validar_descripcion,
    validar_fecha,
    validar_monto,
)


def registrar_gasto(
    usuario_id: UUID,
    monto: int,
    categoria: Categoria,
    descripcion: str,
    fecha: date | None,
    repositorio: RepositorioMovimientos,
    hoy: date | None = None,
) -> Movimiento:
    if not isinstance(categoria, Categoria):
        raise MovimientoInvalido("La categoría no es válida")
    hoy = hoy or datetime.now(timezone.utc).date()
    movimiento = Movimiento(
        id=uuid4(),
        usuario_id=usuario_id,
        tipo=TipoMovimiento.GASTO,
        monto=validar_monto(monto),
        categoria=categoria,
        descripcion=validar_descripcion(descripcion),
        fecha=validar_fecha(fecha or hoy, hoy),
        creado_en=datetime.now(timezone.utc),
    )
    repositorio.guardar(movimiento)
    return movimiento
