"""Adaptador HTTP del registro de usuarios (HU-01)."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.adaptadores.api.dependencias import obtener_hasheador, obtener_repositorio_usuarios
from app.adaptadores.api.dependencias_auth import obtener_repositorio_intentos
from app.adaptadores.api.ip_cliente import ip_del_cliente
from app.casos_de_uso.limite_por_ip import (
    ACCION_REGISTRO,
    MAX_REGISTROS_POR_IP,
    limitar_peticiones_ip,
)
from app.casos_de_uso.puertos import (
    HasheadorContrasenas,
    RepositorioIntentosLogin,
    RepositorioUsuarios,
)
from app.casos_de_uso.registrar_usuario import registrar_usuario
from app.dominio.errores import (
    ContrasenaInvalida,
    DemasiadosIntentos,
    EmailInvalido,
    EmailYaRegistrado,
)

router = APIRouter()


class SolicitudRegistro(BaseModel):
    email: Annotated[str, Field(min_length=1, max_length=320)]
    # Tope generoso solo para no procesar textos gigantes; las reglas reales viven en el dominio.
    contrasena: Annotated[str, Field(min_length=1, max_length=256)]


class RespuestaRegistro(BaseModel):
    # Nunca se devuelve la contraseña ni su huella.
    id: UUID
    email: str
    creado_en: datetime


@router.post("/registro", response_model=RespuestaRegistro, status_code=201)
def post_registro(
    solicitud: SolicitudRegistro,
    request: Request,
    intentos: Annotated[RepositorioIntentosLogin, Depends(obtener_repositorio_intentos)],
    repositorio: Annotated[RepositorioUsuarios, Depends(obtener_repositorio_usuarios)],
    hasheador: Annotated[HasheadorContrasenas, Depends(obtener_hasheador)],
) -> RespuestaRegistro:
    try:
        ip = ip_del_cliente(request)
        limitar_peticiones_ip(ip, ACCION_REGISTRO, MAX_REGISTROS_POR_IP, intentos)
        usuario = registrar_usuario(solicitud.email, solicitud.contrasena, repositorio, hasheador)
    except DemasiadosIntentos as error:
        raise HTTPException(
            status_code=429, detail=str(error), headers={"Retry-After": str(error.segundos)}
        ) from error
    except EmailYaRegistrado as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (EmailInvalido, ContrasenaInvalida) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return RespuestaRegistro(id=usuario.id, email=usuario.email, creado_en=usuario.creado_en)
