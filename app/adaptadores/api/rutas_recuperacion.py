"""Adaptador HTTP de "olvidé mi contraseña". Estas rutas NO llevan token: la persona no puede
entrar. La seguridad está en el token de un solo uso que llega por correo."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.adaptadores.api.dependencias import obtener_hasheador
from app.adaptadores.api.dependencias_auth import (
    obtener_repositorio_intentos,
    obtener_repositorio_tokens,
)
from app.adaptadores.api.dependencias_cuenta import obtener_repositorio_cuenta
from app.adaptadores.api.dependencias_recuperacion import (
    obtener_enviador_correo,
    obtener_repositorio_recuperacion,
)
from app.adaptadores.api.ip_cliente import ip_del_cliente
from app.casos_de_uso.limite_por_ip import (
    ACCION_RECUPERACION,
    MAX_RECUPERACIONES_POR_IP,
    limitar_peticiones_ip,
)
from app.casos_de_uso.puertos import (
    HasheadorContrasenas,
    RepositorioIntentosLogin,
    RepositorioTokensRefresco,
)
from app.casos_de_uso.puertos_cuenta import RepositorioCuenta
from app.casos_de_uso.puertos_recuperacion import EnviadorCorreo, RepositorioRecuperacion
from app.casos_de_uso.recuperar_contrasena import restablecer_contrasena, solicitar_recuperacion
from app.dominio.errores import ContrasenaInvalida, DemasiadosIntentos, TokenInvalido

router = APIRouter(prefix="/recuperacion")

MENSAJE_SOLICITUD = "Si el email tiene una cuenta, te enviamos un correo con las instrucciones"


class SolicitudRecuperacion(BaseModel):
    email: Annotated[str, Field(min_length=1, max_length=320)]


class RespuestaSolicitud(BaseModel):
    mensaje: str


class SolicitudRestablecer(BaseModel):
    token: Annotated[str, Field(min_length=1, max_length=512)]
    contrasena_nueva: Annotated[str, Field(min_length=1, max_length=256)]


@router.post(
    "/solicitar",
    response_model=RespuestaSolicitud,
    status_code=202,
    responses={429: {"description": "Demasiadas solicitudes desde esta dirección"}},
)
def post_solicitar(
    solicitud: SolicitudRecuperacion,
    request: Request,
    intentos: Annotated[RepositorioIntentosLogin, Depends(obtener_repositorio_intentos)],
    cuentas: Annotated[RepositorioCuenta, Depends(obtener_repositorio_cuenta)],
    recuperaciones: Annotated[RepositorioRecuperacion, Depends(obtener_repositorio_recuperacion)],
    enviador: Annotated[EnviadorCorreo, Depends(obtener_enviador_correo)],
) -> RespuestaSolicitud:
    """Pide el correo de recuperación. Siempre responde 202 y lo mismo, tenga cuenta o no."""
    try:
        limitar_peticiones_ip(
            ip_del_cliente(request), ACCION_RECUPERACION, MAX_RECUPERACIONES_POR_IP, intentos
        )
    except DemasiadosIntentos as error:
        raise HTTPException(
            status_code=429, detail=str(error), headers={"Retry-After": str(error.segundos)}
        ) from error
    solicitar_recuperacion(solicitud.email, cuentas, recuperaciones, enviador)
    return RespuestaSolicitud(mensaje=MENSAJE_SOLICITUD)


@router.post(
    "/restablecer",
    status_code=204,
    responses={
        400: {"description": "El enlace no sirve o ya venció"},
        422: {"description": "La contraseña nueva no cumple los requisitos"},
    },
)
def post_restablecer(
    solicitud: SolicitudRestablecer,
    cuentas: Annotated[RepositorioCuenta, Depends(obtener_repositorio_cuenta)],
    recuperaciones: Annotated[RepositorioRecuperacion, Depends(obtener_repositorio_recuperacion)],
    hasheador: Annotated[HasheadorContrasenas, Depends(obtener_hasheador)],
    tokens: Annotated[RepositorioTokensRefresco, Depends(obtener_repositorio_tokens)],
    intentos: Annotated[RepositorioIntentosLogin, Depends(obtener_repositorio_intentos)],
) -> Response:
    """Pone una contraseña nueva con el token del correo. Cierra todas las sesiones."""
    try:
        restablecer_contrasena(
            solicitud.token,
            solicitud.contrasena_nueva,
            cuentas,
            recuperaciones,
            hasheador,
            tokens,
            intentos,
        )
    except TokenInvalido as error:
        raise HTTPException(400, str(error)) from error
    except ContrasenaInvalida as error:
        raise HTTPException(422, str(error)) from error
    return Response(status_code=204)
