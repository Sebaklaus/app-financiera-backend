"""Actividad de seguridad de la propia cuenta: la persona ve qué ha pasado con ella."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.adaptadores.api.dependencias_auditoria import obtener_repositorio_eventos
from app.adaptadores.api.dependencias_auth import obtener_usuario_actual_id
from app.casos_de_uso.auditoria import LIMITE_ACTIVIDAD, listar_actividad
from app.casos_de_uso.puertos_auditoria import RepositorioEventos
from app.dominio.auditoria import TipoEvento
from app.dominio.reloj import a_utc

router = APIRouter(prefix="/yo")


class EventoVisible(BaseModel):
    tipo: TipoEvento
    fecha: datetime


@router.get(
    "/actividad",
    response_model=list[EventoVisible],
    responses={401: {"description": "Falta el token o es inválido o está vencido"}},
)
def get_actividad(
    usuario_id: Annotated[UUID, Depends(obtener_usuario_actual_id)],
    eventos: Annotated[RepositorioEventos, Depends(obtener_repositorio_eventos)],
    limite: Annotated[int, Query(ge=1, le=LIMITE_ACTIVIDAD)] = 20,
):
    """Tus últimos eventos de seguridad: inicios de sesión, cambios de clave o email, etc."""
    return [
        EventoVisible(tipo=e.tipo, fecha=a_utc(e.creado_en))
        for e in listar_actividad(usuario_id, eventos, limite)
    ]
