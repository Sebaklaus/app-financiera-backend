"""Adaptador HTTP de las metas de ahorro (CU-08). Todas las rutas exigen token.

La aplicación no mueve dinero: un aporte solo anota cuánto dices haber apartado.
"""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.adaptadores.api.dependencias_auth import obtener_usuario_actual_id
from app.adaptadores.api.dependencias_metas import obtener_repositorio_metas
from app.casos_de_uso.metas import (
    DetalleMeta,
    aportar_a_meta,
    crear_meta,
    eliminar_meta,
    listar_metas,
    obtener_meta,
)
from app.casos_de_uso.puertos_metas import RepositorioMetas
from app.dominio.errores import MetaInvalida, MetaNoEncontrada
from app.dominio.meta import ProgresoMeta

router = APIRouter(prefix="/metas")

UsuarioActual = Annotated[UUID, Depends(obtener_usuario_actual_id)]
Repositorio = Annotated[RepositorioMetas, Depends(obtener_repositorio_metas)]

_RESPUESTAS = {
    401: {"description": "Falta el token o es inválido o está vencido"},
    422: {"description": "Los datos no cumplen las reglas (nombre, monto, fecha...)"},
}
_NO_ENCONTRADA = {404: {"description": "No existe esa meta (o es de otra persona)"}}

# strict=True: rechaza "1000" y 1000.5; solo acepta enteros. Los topes reales viven en el dominio.
Monto = Annotated[int, Field(strict=True, gt=0, le=1_000_000_000)]
Nombre = Annotated[str, Field(min_length=1, max_length=80)]


class SolicitudMeta(BaseModel):
    nombre: Nombre
    monto_objetivo: Monto
    fecha_limite: date | None = None


class SolicitudAporte(BaseModel):
    monto: Monto
    fecha: date | None = None  # si se omite, se usa la fecha de hoy


class RespuestaMeta(BaseModel):
    id: UUID
    nombre: str
    monto_objetivo: int
    fecha_limite: date | None
    ahorrado: int
    falta: int
    porcentaje: int
    cumplida: bool


class RespuestaAporte(BaseModel):
    id: UUID
    monto: int
    fecha: date


class RespuestaDetalleMeta(RespuestaMeta):
    aportes: list[RespuestaAporte]


def _a_respuesta(progreso: ProgresoMeta) -> RespuestaMeta:
    meta = progreso.meta
    return RespuestaMeta(
        id=meta.id,
        nombre=meta.nombre,
        monto_objetivo=meta.monto_objetivo,
        fecha_limite=meta.fecha_limite,
        ahorrado=progreso.ahorrado,
        falta=progreso.falta,
        porcentaje=progreso.porcentaje,
        cumplida=progreso.cumplida,
    )


def _a_detalle(detalle: DetalleMeta) -> RespuestaDetalleMeta:
    base = _a_respuesta(detalle.progreso)
    return RespuestaDetalleMeta(
        **base.model_dump(),
        aportes=[RespuestaAporte(id=a.id, monto=a.monto, fecha=a.fecha) for a in detalle.aportes],
    )


@router.post("", response_model=RespuestaMeta, status_code=201, responses=_RESPUESTAS)
def post_meta(
    solicitud: SolicitudMeta, usuario_id: UsuarioActual, repositorio: Repositorio
) -> RespuestaMeta:
    """Crea una meta de ahorro con su monto objetivo y, si quieres, una fecha límite."""
    try:
        progreso = crear_meta(
            usuario_id,
            solicitud.nombre,
            solicitud.monto_objetivo,
            solicitud.fecha_limite,
            repositorio,
        )
    except MetaInvalida as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return _a_respuesta(progreso)


@router.get(
    "",
    response_model=list[RespuestaMeta],
    responses={401: _RESPUESTAS[401]},
)
def get_metas(usuario_id: UsuarioActual, repositorio: Repositorio) -> list[RespuestaMeta]:
    """Tus metas con su avance, la más reciente primero."""
    return [_a_respuesta(p) for p in listar_metas(usuario_id, repositorio)]


@router.get(
    "/{meta_id}",
    response_model=RespuestaDetalleMeta,
    responses={401: _RESPUESTAS[401], **_NO_ENCONTRADA},
)
def get_meta(
    meta_id: UUID, usuario_id: UsuarioActual, repositorio: Repositorio
) -> RespuestaDetalleMeta:
    """Una meta con su avance y sus aportes."""
    try:
        return _a_detalle(obtener_meta(usuario_id, meta_id, repositorio))
    except MetaNoEncontrada as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post(
    "/{meta_id}/aportes",
    response_model=RespuestaDetalleMeta,
    status_code=201,
    responses={**_RESPUESTAS, **_NO_ENCONTRADA},
)
def post_aporte(
    meta_id: UUID,
    solicitud: SolicitudAporte,
    usuario_id: UsuarioActual,
    repositorio: Repositorio,
) -> RespuestaDetalleMeta:
    """Anota cuánto apartaste para la meta. La aplicación no mueve dinero."""
    try:
        detalle = aportar_a_meta(
            usuario_id, meta_id, solicitud.monto, solicitud.fecha, repositorio
        )
    except MetaNoEncontrada as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except MetaInvalida as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return _a_detalle(detalle)


@router.delete(
    "/{meta_id}",
    status_code=204,
    responses={401: _RESPUESTAS[401], **_NO_ENCONTRADA},
)
def delete_meta(meta_id: UUID, usuario_id: UsuarioActual, repositorio: Repositorio) -> Response:
    """Borra una meta tuya y todos sus aportes."""
    try:
        eliminar_meta(usuario_id, meta_id, repositorio)
    except MetaNoEncontrada as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=204)
