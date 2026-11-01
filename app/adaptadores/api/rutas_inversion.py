"""Adaptador HTTP de la inversión (HU-08 y HU-09). Todas las rutas exigen token.

La app solo muestra opciones y redirige a la entidad socia (simulada por ahora); nunca mueve
dinero.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.adaptadores.api.dependencias_auditoria import obtener_repositorio_eventos
from app.adaptadores.api.dependencias_auth import obtener_usuario_actual_id
from app.adaptadores.api.dependencias_consentimientos import obtener_repositorio_consentimientos
from app.adaptadores.api.ip_cliente import ip_del_cliente
from app.casos_de_uso.inversion import derivar_a_entidad_socia, listar_opciones
from app.casos_de_uso.puertos_auditoria import RepositorioEventos
from app.casos_de_uso.puertos_consentimientos import RepositorioConsentimientos
from app.dominio.consentimiento import PerfilRiesgo
from app.dominio.errores import MovimientoInvalido
from app.dominio.inversion import InstrumentoNoEncontrado, Riesgo

router = APIRouter(prefix="/inversion")

UsuarioActual = Annotated[UUID, Depends(obtener_usuario_actual_id)]
Consentimientos = Annotated[
    RepositorioConsentimientos, Depends(obtener_repositorio_consentimientos)
]
Eventos = Annotated[RepositorioEventos, Depends(obtener_repositorio_eventos)]

_RESPUESTAS = {
    401: {"description": "Falta el token o es inválido o está vencido"},
    404: {"description": "No existe ese instrumento"},
    422: {"description": "El monto no cumple las reglas"},
}


class RespuestaEntidad(BaseModel):
    id: str
    nombre: str


class RespuestaInstrumento(BaseModel):
    id: str
    nombre: str
    tipo: str
    riesgo: Riesgo
    plazo: str
    liquidez: str
    descripcion: str
    entidad: RespuestaEntidad
    recomendado: bool


class RespuestaOpciones(BaseModel):
    perfil_riesgo: PerfilRiesgo | None
    opciones: list[RespuestaInstrumento]
    aviso: str


class SolicitudDerivacion(BaseModel):
    instrumento_id: Annotated[str, Field(min_length=1, max_length=60)]
    monto: Annotated[int, Field(strict=True, gt=0, le=1_000_000_000)] | None = None


class RespuestaDerivacion(BaseModel):
    referencia: UUID
    instrumento_id: str
    instrumento_nombre: str
    entidad: RespuestaEntidad
    url: str
    monto: int | None
    simulada: bool
    creada_en: datetime
    mensaje: str


AVISO = (
    "Esta información es educativa y no es una recomendación de inversión. La app no vende "
    "productos ni mueve dinero: la operación se completa en la entidad socia."
)


@router.get("/opciones", response_model=RespuestaOpciones, responses={401: _RESPUESTAS[401]})
def get_opciones(usuario_id: UsuarioActual, consentimientos: Consentimientos) -> RespuestaOpciones:
    """Opciones de inversión; primero las que calzan con tu perfil de riesgo."""
    resultado = listar_opciones(usuario_id, consentimientos)
    return RespuestaOpciones(
        perfil_riesgo=resultado.perfil,
        opciones=[
            RespuestaInstrumento(
                id=o.instrumento.id,
                nombre=o.instrumento.nombre,
                tipo=o.instrumento.tipo,
                riesgo=o.instrumento.riesgo,
                plazo=o.instrumento.plazo,
                liquidez=o.instrumento.liquidez,
                descripcion=o.instrumento.descripcion,
                entidad=RespuestaEntidad(
                    id=o.instrumento.entidad.id, nombre=o.instrumento.entidad.nombre
                ),
                recomendado=o.recomendado,
            )
            for o in resultado.opciones
        ],
        aviso=AVISO,
    )


@router.post(
    "/derivaciones", response_model=RespuestaDerivacion, status_code=201, responses=_RESPUESTAS
)
def post_derivacion(
    solicitud: SolicitudDerivacion,
    request: Request,
    usuario_id: UsuarioActual,
    eventos: Eventos,
) -> RespuestaDerivacion:
    """Te lleva a la entidad socia (simulada). Queda anotado en tu bitácora; no se mueve dinero."""
    try:
        d = derivar_a_entidad_socia(
            usuario_id, solicitud.instrumento_id, solicitud.monto, eventos, ip_del_cliente(request)
        )
    except InstrumentoNoEncontrado as error:
        raise HTTPException(404, str(error)) from error
    except MovimientoInvalido as error:
        raise HTTPException(422, str(error)) from error
    return RespuestaDerivacion(
        referencia=d.referencia,
        instrumento_id=d.instrumento.id,
        instrumento_nombre=d.instrumento.nombre,
        entidad=RespuestaEntidad(id=d.entidad.id, nombre=d.entidad.nombre),
        url=d.entidad.url_simulada,
        monto=d.monto,
        simulada=True,
        creada_en=d.creada_en,
        mensaje=(
            "Redirección simulada: en producción aquí abrirías el sitio de la entidad socia y "
            "completarías la operación con tus propias credenciales."
        ),
    )
