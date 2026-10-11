"""Adaptador HTTP de la sesión (HU-02): login, renovar, logout y una ruta protegida de ejemplo."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.adaptadores.api.dependencias import obtener_hasheador, obtener_repositorio_usuarios
from app.adaptadores.api.dependencias_auditoria import obtener_repositorio_eventos
from app.adaptadores.api.dependencias_auth import (
    obtener_emisor_tokens,
    obtener_repositorio_intentos,
    obtener_repositorio_tokens,
    obtener_usuario_actual_id,
)
from app.adaptadores.api.ip_cliente import ip_del_cliente
from app.casos_de_uso.auditoria import registrar_evento
from app.casos_de_uso.limite_por_ip import registrar_fallo_ip, verificar_ip
from app.casos_de_uso.login_con_bloqueo import iniciar_sesion_con_bloqueo
from app.casos_de_uso.puertos import (
    EmisorTokens,
    HasheadorContrasenas,
    RepositorioIntentosLogin,
    RepositorioTokensRefresco,
    RepositorioUsuarios,
)
from app.casos_de_uso.puertos_auditoria import RepositorioEventos
from app.casos_de_uso.sesiones import (
    ParDeTokens,
    abrir_sesion,
    cerrar_sesion,
    cerrar_todas_las_sesiones,
    renovar_sesion,
)
from app.dominio.auditoria import ReusoDeToken, TipoEvento
from app.dominio.errores import CredencialesInvalidas, DemasiadosIntentos, TokenInvalido

router = APIRouter()

_CABECERA_401 = {"WWW-Authenticate": "Bearer"}
UsuarioActual = Annotated[UUID, Depends(obtener_usuario_actual_id)]
RepoTokens = Annotated[RepositorioTokensRefresco, Depends(obtener_repositorio_tokens)]
Emisor = Annotated[EmisorTokens, Depends(obtener_emisor_tokens)]
Eventos = Annotated[RepositorioEventos, Depends(obtener_repositorio_eventos)]
TokenRefrescoTexto = Annotated[str, Field(min_length=1, max_length=512)]


class SolicitudLogin(BaseModel):
    email: Annotated[str, Field(min_length=1, max_length=320)]
    contrasena: Annotated[str, Field(min_length=1, max_length=256)]


class SolicitudRefresco(BaseModel):
    refresh_token: TokenRefrescoTexto


class RespuestaLogin(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos de vida del token de acceso


class RespuestaYo(BaseModel):
    id: UUID


def _a_respuesta(par: ParDeTokens) -> RespuestaLogin:
    return RespuestaLogin(
        access_token=par.acceso, refresh_token=par.refresco, expires_in=par.expira_en
    )


@router.post(
    "/login",
    response_model=RespuestaLogin,
    responses={
        401: {"description": "Email o contraseña incorrectos"},
        429: {"description": "Demasiados intentos fallidos: espera antes de volver a intentar"},
    },
)
def post_login(
    solicitud: SolicitudLogin,
    request: Request,
    repositorio: Annotated[RepositorioUsuarios, Depends(obtener_repositorio_usuarios)],
    hasheador: Annotated[HasheadorContrasenas, Depends(obtener_hasheador)],
    emisor: Emisor,
    tokens: RepoTokens,
    intentos: Annotated[RepositorioIntentosLogin, Depends(obtener_repositorio_intentos)],
    eventos: Eventos,
) -> RespuestaLogin:
    ip = ip_del_cliente(request)
    try:
        verificar_ip(ip, intentos)
    except DemasiadosIntentos as error:
        registrar_evento(eventos, TipoEvento.IP_BLOQUEADA, None, ip)
        raise _demasiados(error) from error
    try:
        usuario = iniciar_sesion_con_bloqueo(
            solicitud.email, solicitud.contrasena, repositorio, hasheador, intentos
        )
    except DemasiadosIntentos as error:
        registrar_evento(eventos, TipoEvento.LOGIN_RECHAZADO_POR_BLOQUEO, None, ip)
        raise _demasiados(error) from error
    except CredencialesInvalidas as error:
        registrar_fallo_ip(ip, intentos)
        registrar_evento(eventos, TipoEvento.LOGIN_FALLIDO, None, ip)
        raise HTTPException(status_code=401, detail=str(error), headers=_CABECERA_401) from error
    registrar_evento(eventos, TipoEvento.LOGIN_EXITOSO, usuario.id, ip)
    return _a_respuesta(abrir_sesion(usuario.id, tokens, emisor))


def _demasiados(error: DemasiadosIntentos) -> HTTPException:
    return HTTPException(
        status_code=429, detail=str(error), headers={"Retry-After": str(error.segundos)}
    )


@router.post(
    "/refrescar",
    response_model=RespuestaLogin,
    responses={401: {"description": "El token de refresco no sirve (vencido, usado o falso)"}},
)
def post_refrescar(
    solicitud: SolicitudRefresco,
    request: Request,
    emisor: Emisor,
    tokens: RepoTokens,
    eventos: Eventos,
) -> RespuestaLogin:
    """Cambia tu token de refresco por un par nuevo. El token que enviaste deja de servir."""
    try:
        par = renovar_sesion(solicitud.refresh_token, tokens, emisor)
    except ReusoDeToken as error:
        ip = ip_del_cliente(request)
        registrar_evento(eventos, TipoEvento.REFRESCO_REUTILIZADO, error.usuario_id, ip)
        raise HTTPException(401, str(error), headers=_CABECERA_401) from error
    except TokenInvalido as error:
        raise HTTPException(status_code=401, detail=str(error), headers=_CABECERA_401) from error
    return _a_respuesta(par)


@router.post("/logout", status_code=204)
def post_logout(solicitud: SolicitudRefresco, tokens: RepoTokens) -> Response:
    """Cierra esta sesión. Siempre responde 204, exista o no el token."""
    cerrar_sesion(solicitud.refresh_token, tokens)
    return Response(status_code=204)


@router.post(
    "/logout/todas",
    status_code=204,
    responses={401: {"description": "Falta el token o es inválido o está vencido"}},
)
def post_logout_todas(
    usuario_id: UsuarioActual, request: Request, tokens: RepoTokens, eventos: Eventos
) -> Response:
    """Cierra TODAS tus sesiones (por ejemplo, si perdiste el teléfono)."""
    cerrar_todas_las_sesiones(usuario_id, tokens)
    registrar_evento(eventos, TipoEvento.SESIONES_CERRADAS, usuario_id, ip_del_cliente(request))
    return Response(status_code=204)


@router.get(
    "/yo",
    response_model=RespuestaYo,
    responses={401: {"description": "Falta el token o es inválido o está vencido"}},
)
def get_yo(usuario_id: UsuarioActual) -> RespuestaYo:
    """Ruta protegida de prueba: solo responde si llegas con un token válido."""
    return RespuestaYo(id=usuario_id)
