"""Caso de uso: corregir un ingreso o un gasto ya registrado."""

from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

from app.casos_de_uso.puertos import RepositorioMovimientos
from app.dominio.categorias import Categoria
from app.dominio.confirmacion import Confirmacion, EstadoConfirmacion, proponer
from app.dominio.errores import EdicionNoPermitida, MovimientoNoEncontrado
from app.dominio.movimiento import Movimiento, TipoMovimiento, editar, repartir
from app.dominio.reloj import hoy_en_chile


@dataclass(frozen=True)
class ResultadoEdicion:
    movimiento: Movimiento
    pendientes: list[Confirmacion]  # propuestas de un ingreso que siguen esperando decisión


def editar_movimiento(
    usuario_id: UUID,
    movimiento_id: UUID,
    repositorio: RepositorioMovimientos,
    monto: int | None = None,
    categoria: Categoria | None = None,
    descripcion: str | None = None,
    fecha: date | None = None,
    hoy: date | None = None,
) -> ResultadoEdicion:
    actual = repositorio.buscar_movimiento(usuario_id, movimiento_id)
    if actual is None:
        raise MovimientoNoEncontrado("No existe ese movimiento")
    ahora = datetime.now(timezone.utc)
    nuevo = editar(
        actual,
        hoy or hoy_en_chile(ahora),
        monto=monto,
        categoria=categoria,
        descripcion=descripcion,
        fecha=fecha,
    )
    if actual.tipo is TipoMovimiento.GASTO:
        repositorio.actualizar_movimiento(nuevo)
        return ResultadoEdicion(nuevo, [])

    propias = [
        c
        for c in repositorio.listar_confirmaciones_por_usuario(usuario_id)
        if c.ingreso_id == actual.id
    ]
    if nuevo.monto == actual.monto:
        # El reparto no cambia: se corrige el texto o la fecha y las propuestas siguen igual.
        repositorio.actualizar_movimiento(nuevo)
        pendientes = [c for c in propias if c.estado is EstadoConfirmacion.PENDIENTE]
        return ResultadoEdicion(nuevo, pendientes)

    if any(c.estado is not EstadoConfirmacion.PENDIENTE for c in propias):
        raise EdicionNoPermitida(
            "No se puede cambiar el monto: ya decidiste una parte de este ingreso. "
            "Borra el ingreso y regístralo de nuevo."
        )
    propuestas = proponer(nuevo, repartir(nuevo.monto), ahora)
    repositorio.actualizar_movimiento(nuevo, propuestas)
    return ResultadoEdicion(nuevo, propuestas)
