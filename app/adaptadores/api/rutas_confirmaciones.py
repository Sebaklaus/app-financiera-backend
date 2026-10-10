"""Adaptador HTTP de las propuestas de reparto: ver las pendientes y decidirlas (RNF-06)."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.adaptadores.api.dependencias_auth import obtener_usuario_actual_id
from app.adaptadores.api.dependencias_movimientos import obtener_repositorio_movimientos
from app.casos_de_uso.decidir_confirmacion import decidir_confirmacion
from app.casos_de_uso.listar_confirmaciones_pendientes import listar_confirmaciones_pendientes
from app.casos_de_uso.puertos import RepositorioMovimientos
from app.dominio.categorias import Categoria
from app.dominio.confirmacion import Confirmacion, Decision, EstadoConfirmacion
from app.dominio.errores import ConfirmacionNoEncontrada, ConfirmacionYaDecidida
from app.dominio.reloj import a_utc

router = APIRouter()

UsuarioActual = Annotated[UUID, Depends(obtener_usuario_actual_id)]
Repositorio = Annotated[RepositorioMovimientos, Depends(obtener_repositorio_movimientos)]

_NO_AUTENTICADO = {401: {"description": "Falta el token o es inválido o está vencido"}}


class SolicitudDecision(BaseModel):
    decision: Decision


class RespuestaConfirmacion(BaseModel):
    id: UUID
    ingreso_id: UUID
    categoria: Categoria
    monto: int
    estado: EstadoConfirmacion
    creado_en: datetime
    decidido_en: datetime | None


def a_respuesta(confirmacion: Confirmacion) -> RespuestaConfirmacion:
    return RespuestaConfirmacion(
        id=confirmacion.id,
        ingreso_id=confirmacion.ingreso_id,
        categoria=confirmacion.categoria,
        monto=confirmacion.monto,
        estado=confirmacion.estado,
        # Siempre en UTC (termina en Z), venga de PostgreSQL o de SQLite.
        creado_en=a_utc(confirmacion.creado_en),
        decidido_en=(None if confirmacion.decidido_en is None else a_utc(confirmacion.decidido_en)),
    )


@router.get(
    "/confirmaciones/pendientes",
    response_model=list[RespuestaConfirmacion],
    responses=_NO_AUTENTICADO,
)
def get_confirmaciones_pendientes(
    usuario_id: UsuarioActual, repositorio: Repositorio
) -> list[RespuestaConfirmacion]:
    """Las partes del reparto (inversión y estabilidad) que esperan tu decisión."""
    return [a_respuesta(c) for c in listar_confirmaciones_pendientes(usuario_id, repositorio)]


@router.post(
    "/confirmaciones/{confirmacion_id}/decision",
    response_model=RespuestaConfirmacion,
    responses={
        **_NO_AUTENTICADO,
        404: {"description": "No existe esa propuesta"},
        409: {"description": "Esa propuesta ya fue decidida"},
    },
)
def post_decision(
    confirmacion_id: UUID,
    solicitud: SolicitudDecision,
    usuario_id: UsuarioActual,
    repositorio: Repositorio,
) -> RespuestaConfirmacion:
    """Confirma o rechaza una propuesta. Solo se puede decidir una vez."""
    try:
        decidida = decidir_confirmacion(
            usuario_id, confirmacion_id, solicitud.decision, repositorio
        )
    except ConfirmacionNoEncontrada as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ConfirmacionYaDecidida as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return a_respuesta(decidida)
