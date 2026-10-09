"""Adaptador HTTP de ingresos, gastos y resumen (HU-28). Todas las rutas exigen token."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from app.adaptadores.api.dependencias_auth import obtener_usuario_actual_id
from app.adaptadores.api.dependencias_movimientos import obtener_repositorio_movimientos
from app.adaptadores.api.rutas_confirmaciones import RespuestaConfirmacion, a_respuesta
from app.casos_de_uso.editar_movimiento import editar_movimiento
from app.casos_de_uso.eliminar_movimiento import eliminar_movimiento
from app.casos_de_uso.listar_movimientos import listar_movimientos
from app.casos_de_uso.obtener_resumen import obtener_resumen
from app.casos_de_uso.puertos import RepositorioMovimientos
from app.casos_de_uso.registrar_gasto import registrar_gasto
from app.casos_de_uso.registrar_ingreso import registrar_ingreso
from app.dominio.categorias import Categoria
from app.dominio.errores import EdicionNoPermitida, MovimientoInvalido, MovimientoNoEncontrado
from app.dominio.movimiento import Movimiento
from app.dominio.periodo import Periodo

router = APIRouter()

UsuarioActual = Annotated[UUID, Depends(obtener_usuario_actual_id)]
Repositorio = Annotated[RepositorioMovimientos, Depends(obtener_repositorio_movimientos)]

_RESPUESTAS_PROTEGIDAS = {
    401: {"description": "Falta el token o es inválido o está vencido"},
    422: {"description": "Los datos no cumplen las reglas (monto, fecha, texto...)"},
}

# strict=True: rechaza "1000" y 1000.5; solo acepta enteros. Los topes reales viven en el dominio.
Monto = Annotated[int, Field(strict=True, gt=0, le=1_000_000_000)]
Descripcion = Annotated[str, Field(min_length=1, max_length=200)]
# Formato AAAA-MM. Un mes mal escrito se rechaza con 422 antes de llegar al dominio.
MesConsulta = Annotated[
    str | None,
    Query(
        pattern=r"^\d{4}-(0[1-9]|1[0-2])$",
        description="Mes en formato AAAA-MM (por ejemplo 2026-10). Si se omite, se usan todos.",
        examples=["2026-10"],
    ),
]


class SolicitudIngreso(BaseModel):
    monto: Monto
    descripcion: Descripcion
    fecha: date | None = None  # si se omite, se usa la fecha de hoy


class SolicitudGasto(BaseModel):
    monto: Monto
    categoria: Categoria
    descripcion: Descripcion
    fecha: date | None = None


class RespuestaReparto(BaseModel):
    necesidades: int
    inversion: int
    estabilidad: int
    entretenimiento: int


class RespuestaIngreso(BaseModel):
    id: UUID
    monto: int
    descripcion: str
    fecha: date
    reparto: RespuestaReparto  # es una PROPUESTA: inversión y estabilidad esperan tu decisión
    por_confirmar: list[RespuestaConfirmacion]


class RespuestaGasto(BaseModel):
    id: UUID
    monto: int
    categoria: Categoria
    descripcion: str
    fecha: date


class RespuestaMovimiento(BaseModel):
    id: UUID
    tipo: str
    monto: int
    categoria: Categoria | None
    descripcion: str
    fecha: date


class SolicitudEdicion(BaseModel):
    """Solo se cambia lo que envíes; lo que omitas queda igual."""

    monto: Monto | None = None
    categoria: Categoria | None = None  # solo para gastos
    descripcion: Descripcion | None = None
    fecha: date | None = None


class RespuestaEdicion(RespuestaMovimiento):
    # Propuestas de un ingreso que siguen esperando tu decisión (vacío en los gastos).
    por_confirmar: list[RespuestaConfirmacion] = []


class RespuestaLinea(BaseModel):
    categoria: Categoria
    asignado: int  # ya decidido: lo que de verdad cuenta como tuyo en esta categoría
    gastado: int
    disponible: int
    por_confirmar: int  # propuesto, esperando tu decisión
    rechazado: int  # propuesto y rechazado: ese dinero queda sin apartar


class RespuestaResumen(BaseModel):
    mes: str | None  # el mes consultado (AAAA-MM), o null si se resumió todo
    ingresos_total: int
    gastos_total: int
    categorias: list[RespuestaLinea]


def _periodo(mes: str | None) -> Periodo | None:
    """Convierte el texto AAAA-MM; si no sirve, responde 422 en vez de fallar."""
    if mes is None:
        return None
    try:
        return Periodo.desde_texto(mes)
    except MovimientoInvalido as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


def _a_respuesta(movimiento: Movimiento) -> RespuestaMovimiento:
    return RespuestaMovimiento(
        id=movimiento.id,
        tipo=movimiento.tipo.value,
        monto=movimiento.monto,
        categoria=movimiento.categoria,
        descripcion=movimiento.descripcion,
        fecha=movimiento.fecha,
    )


@router.post(
    "/ingresos",
    response_model=RespuestaIngreso,
    status_code=201,
    responses=_RESPUESTAS_PROTEGIDAS,
)
def post_ingreso(
    solicitud: SolicitudIngreso, usuario_id: UsuarioActual, repositorio: Repositorio
) -> RespuestaIngreso:
    """Registra un ingreso y PROPONE su reparto 50/25/15/10 (25 % y 15 % quedan pendientes)."""
    try:
        resultado = registrar_ingreso(
            usuario_id,
            solicitud.monto,
            solicitud.descripcion,
            solicitud.fecha,
            repositorio,
        )
    except MovimientoInvalido as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    movimiento = resultado.movimiento
    return RespuestaIngreso(
        id=movimiento.id,
        monto=movimiento.monto,
        descripcion=movimiento.descripcion,
        fecha=movimiento.fecha,
        reparto=RespuestaReparto(**{c.value: m for c, m in resultado.reparto.items()}),
        por_confirmar=[a_respuesta(c) for c in resultado.confirmaciones],
    )


@router.post(
    "/gastos",
    response_model=RespuestaGasto,
    status_code=201,
    responses=_RESPUESTAS_PROTEGIDAS,
)
def post_gasto(
    solicitud: SolicitudGasto, usuario_id: UsuarioActual, repositorio: Repositorio
) -> RespuestaGasto:
    """Registra un gasto contra una de las cuatro categorías."""
    try:
        movimiento = registrar_gasto(
            usuario_id,
            solicitud.monto,
            solicitud.categoria,
            solicitud.descripcion,
            solicitud.fecha,
            repositorio,
        )
    except MovimientoInvalido as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    assert movimiento.categoria is not None  # un gasto siempre trae categoría
    return RespuestaGasto(
        id=movimiento.id,
        monto=movimiento.monto,
        categoria=movimiento.categoria,
        descripcion=movimiento.descripcion,
        fecha=movimiento.fecha,
    )


@router.get(
    "/movimientos",
    response_model=list[RespuestaMovimiento],
    responses={401: _RESPUESTAS_PROTEGIDAS[401]},
)
def get_movimientos(
    usuario_id: UsuarioActual, repositorio: Repositorio, mes: MesConsulta = None
) -> list[RespuestaMovimiento]:
    """Tus ingresos y gastos, el más reciente primero (todos, o solo los de un mes)."""
    periodo = _periodo(mes)
    return [_a_respuesta(m) for m in listar_movimientos(usuario_id, repositorio, periodo)]


@router.patch(
    "/movimientos/{movimiento_id}",
    response_model=RespuestaEdicion,
    responses={
        **_RESPUESTAS_PROTEGIDAS,
        404: {"description": "No existe ese movimiento (o es de otra persona)"},
        409: {"description": "Ese ingreso ya tiene partes decididas: no se puede cambiar su monto"},
    },
)
def patch_movimiento(
    movimiento_id: UUID,
    solicitud: SolicitudEdicion,
    usuario_id: UsuarioActual,
    repositorio: Repositorio,
) -> RespuestaEdicion:
    """Corrige un movimiento. Si cambias el monto de un ingreso, se vuelve a proponer su reparto."""
    try:
        resultado = editar_movimiento(
            usuario_id,
            movimiento_id,
            repositorio,
            monto=solicitud.monto,
            categoria=solicitud.categoria,
            descripcion=solicitud.descripcion,
            fecha=solicitud.fecha,
        )
    except MovimientoNoEncontrado as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except EdicionNoPermitida as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except MovimientoInvalido as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    base = _a_respuesta(resultado.movimiento)
    return RespuestaEdicion(
        **base.model_dump(), por_confirmar=[a_respuesta(c) for c in resultado.pendientes]
    )


@router.delete(
    "/movimientos/{movimiento_id}",
    status_code=204,
    responses={
        401: _RESPUESTAS_PROTEGIDAS[401],
        404: {"description": "No existe ese movimiento (o es de otra persona)"},
    },
)
def delete_movimiento(
    movimiento_id: UUID, usuario_id: UsuarioActual, repositorio: Repositorio
) -> Response:
    """Borra un movimiento tuyo. Si es un ingreso, se borran también sus propuestas."""
    try:
        eliminar_movimiento(usuario_id, movimiento_id, repositorio)
    except MovimientoNoEncontrado as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=204)


@router.get(
    "/resumen",
    response_model=RespuestaResumen,
    responses={401: _RESPUESTAS_PROTEGIDAS[401]},
)
def get_resumen(
    usuario_id: UsuarioActual, repositorio: Repositorio, mes: MesConsulta = None
) -> RespuestaResumen:
    """Por categoría: cuánto se asignó, cuánto gastaste y cuánto te queda.

    Con `mes` (AAAA-MM) se resume solo ese mes; cada mes se mira por separado.
    """
    periodo = _periodo(mes)
    resumen = obtener_resumen(usuario_id, repositorio, periodo)
    return RespuestaResumen(
        mes=None if periodo is None else str(periodo),
        ingresos_total=resumen.ingresos_total,
        gastos_total=resumen.gastos_total,
        categorias=[
            RespuestaLinea(
                categoria=linea.categoria,
                asignado=linea.asignado,
                gastado=linea.gastado,
                disponible=linea.disponible,
                por_confirmar=linea.por_confirmar,
                rechazado=linea.rechazado,
            )
            for linea in resumen.lineas
        ],
    )
