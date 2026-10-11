"""Adaptador HTTP de consentimientos y perfil de riesgo (HU-03). Todas las rutas exigen token.

El front los pide justo después de registrarse, cada consentimiento con su propio interruptor.
"""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.adaptadores.api.dependencias_auth import obtener_usuario_actual_id
from app.adaptadores.api.dependencias_consentimientos import obtener_repositorio_consentimientos
from app.casos_de_uso.consentimientos import (
    EstadoConsentimientos,
    declarar_perfil,
    obtener_consentimientos,
    obtener_perfil,
    registrar_consentimientos,
)
from app.casos_de_uso.puertos_consentimientos import RepositorioConsentimientos
from app.dominio.consentimiento import (
    OBLIGATORIOS,
    CambioVacio,
    ConsentimientoObligatorio,
    PerfilRiesgo,
    TipoConsentimiento,
)
from app.dominio.reloj import a_utc

router = APIRouter(prefix="/yo")

UsuarioActual = Annotated[UUID, Depends(obtener_usuario_actual_id)]
Repositorio = Annotated[RepositorioConsentimientos, Depends(obtener_repositorio_consentimientos)]
_NO_AUTENTICADO = {401: {"description": "Falta el token o es inválido o está vencido"}}


class LineaConsentimiento(BaseModel):
    tipo: TipoConsentimiento
    obligatorio: bool
    otorgado: bool
    version: str | None
    desde: datetime | None


class RespuestaConsentimientos(BaseModel):
    version_textos: str
    consentimientos: list[LineaConsentimiento]
    pendientes: list[TipoConsentimiento]


class SolicitudConsentimientos(BaseModel):
    terminos_y_privacidad: bool | None = None
    datos_financieros: bool | None = None
    comunicaciones: bool | None = None


class PerfilConsulta(BaseModel):
    perfil: PerfilRiesgo | None
    actualizado_en: datetime | None


class SolicitudPerfil(BaseModel):
    perfil: PerfilRiesgo


def a_respuesta(estado: EstadoConsentimientos) -> RespuestaConsentimientos:
    lineas = []
    for tipo in TipoConsentimiento:
        registro = estado.actuales.get(tipo)
        lineas.append(
            LineaConsentimiento(
                tipo=tipo,
                obligatorio=tipo in OBLIGATORIOS,
                otorgado=registro is not None and registro.otorgado,
                version=None if registro is None else registro.version,
                desde=None if registro is None else a_utc(registro.creado_en),
            )
        )
    return RespuestaConsentimientos(
        version_textos=estado.version, consentimientos=lineas, pendientes=estado.pendientes
    )


@router.get("/consentimientos", response_model=RespuestaConsentimientos, responses=_NO_AUTENTICADO)
def get_consentimientos(usuario_id: UsuarioActual, repositorio: Repositorio):
    """Qué has aceptado y qué falta por aceptar (`pendientes`)."""
    return a_respuesta(obtener_consentimientos(usuario_id, repositorio))


@router.put("/consentimientos", response_model=RespuestaConsentimientos, responses=_NO_AUTENTICADO)
def put_consentimientos(
    solicitud: SolicitudConsentimientos, usuario_id: UsuarioActual, repositorio: Repositorio
):
    """Otorga o retira consentimientos. Envía solo los que quieras cambiar."""
    cambios = {
        TipoConsentimiento(nombre): valor
        for nombre, valor in solicitud.model_dump().items()
        if valor is not None
    }
    try:
        estado = registrar_consentimientos(usuario_id, cambios, repositorio)
    except (CambioVacio, ConsentimientoObligatorio) as error:
        raise HTTPException(422, str(error)) from error
    return a_respuesta(estado)


@router.get("/perfil-riesgo", response_model=PerfilConsulta, responses=_NO_AUTENTICADO)
def get_perfil_riesgo(usuario_id: UsuarioActual, repositorio: Repositorio):
    declarado = obtener_perfil(usuario_id, repositorio)
    if declarado is None:
        return PerfilConsulta(perfil=None, actualizado_en=None)
    return PerfilConsulta(perfil=declarado.perfil, actualizado_en=a_utc(declarado.actualizado_en))


@router.put("/perfil-riesgo", response_model=PerfilConsulta, responses=_NO_AUTENTICADO)
def put_perfil_riesgo(
    solicitud: SolicitudPerfil, usuario_id: UsuarioActual, repositorio: Repositorio
):
    """Declara (o corrige) tu perfil de riesgo: conservador, moderado o arriesgado."""
    declarado = declarar_perfil(usuario_id, solicitud.perfil, repositorio)
    return PerfilConsulta(perfil=declarado.perfil, actualizado_en=a_utc(declarado.actualizado_en))
