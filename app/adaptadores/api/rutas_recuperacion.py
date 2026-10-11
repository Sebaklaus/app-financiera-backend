"""Adaptador HTTP de "olvidé mi contraseña". Estas rutas NO llevan token: la persona no puede
entrar. La seguridad está en el token de un solo uso que llega por correo."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.adaptadores.api.dependencias import obtener_hasheador
from app.adaptadores.api.dependencias_auditoria import obtener_repositorio_eventos
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
from app.casos_de_uso.auditoria import registrar_evento
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
from app.casos_de_uso.puertos_auditoria import RepositorioEventos
from app.casos_de_uso.puertos_cuenta import RepositorioCuenta
from app.casos_de_uso.puertos_recuperacion import EnviadorCorreo, RepositorioRecuperacion
from app.casos_de_uso.recuperar_contrasena import restablecer_contrasena, solicitar_recuperacion
from app.dominio.auditoria import TipoEvento
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
    eventos: Annotated[RepositorioEventos, Depends(obtener_repositorio_eventos)],
) -> RespuestaSolicitud:
    """Pide el correo de recuperación. Siempre responde 202 y lo mismo, tenga cuenta o no."""
    ip = ip_del_cliente(request)
    try:
        limitar_peticiones_ip(ip, ACCION_RECUPERACION, MAX_RECUPERACIONES_POR_IP, intentos)
    except DemasiadosIntentos as error:
        raise HTTPException(
            status_code=429, detail=str(error), headers={"Retry-After": str(error.segundos)}
        ) from error
    usuario_id = solicitar_recuperacion(solicitud.email, cuentas, recuperaciones, enviador)
    if usuario_id is not None:  # solo se anota en la bitácora; la respuesta es igual para todos
        registrar_evento(eventos, TipoEvento.RECUPERACION_SOLICITADA, usuario_id, ip)
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
    request: Request,
    eventos: Annotated[RepositorioEventos, Depends(obtener_repositorio_eventos)],
    cuentas: Annotated[RepositorioCuenta, Depends(obtener_repositorio_cuenta)],
    recuperaciones: Annotated[RepositorioRecuperacion, Depends(obtener_repositorio_recuperacion)],
    hasheador: Annotated[HasheadorContrasenas, Depends(obtener_hasheador)],
    tokens: Annotated[RepositorioTokensRefresco, Depends(obtener_repositorio_tokens)],
    intentos: Annotated[RepositorioIntentosLogin, Depends(obtener_repositorio_intentos)],
) -> Response:
    """Pone una contraseña nueva con el token del correo. Cierra todas las sesiones."""
    ip = ip_del_cliente(request)
    try:
        usuario_id = restablecer_contrasena(
            solicitud.token,
            solicitud.contrasena_nueva,
            cuentas,
            recuperaciones,
            hasheador,
            tokens,
            intentos,
        )
    except TokenInvalido as error:
        registrar_evento(eventos, TipoEvento.RECUPERACION_FALLIDA, None, ip)
        raise HTTPException(400, str(error)) from error
    except ContrasenaInvalida as error:
        raise HTTPException(422, str(error)) from error
    registrar_evento(eventos, TipoEvento.RECUPERACION_COMPLETADA, usuario_id, ip)
    return Response(status_code=204)
