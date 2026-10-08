"""Adaptador HTTP del inicio de sesión (HU-02) y una ruta protegida de ejemplo."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.adaptadores.api.dependencias import obtener_hasheador, obtener_repositorio_usuarios
from app.adaptadores.api.dependencias_auth import obtener_emisor_tokens, obtener_usuario_actual_id
from app.casos_de_uso.iniciar_sesion import iniciar_sesion
from app.casos_de_uso.puertos import EmisorTokens, HasheadorContrasenas, RepositorioUsuarios
from app.dominio.errores import CredencialesInvalidas

router = APIRouter()


class SolicitudLogin(BaseModel):
    email: Annotated[str, Field(min_length=1, max_length=320)]
    contrasena: Annotated[str, Field(min_length=1, max_length=256)]


class RespuestaLogin(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos de vida del token


class RespuestaYo(BaseModel):
    id: UUID


@router.post(
    "/login",
    response_model=RespuestaLogin,
    responses={401: {"description": "Email o contraseña incorrectos"}},
)
def post_login(
    solicitud: SolicitudLogin,
    repositorio: Annotated[RepositorioUsuarios, Depends(obtener_repositorio_usuarios)],
    hasheador: Annotated[HasheadorContrasenas, Depends(obtener_hasheador)],
    emisor: Annotated[EmisorTokens, Depends(obtener_emisor_tokens)],
) -> RespuestaLogin:
    try:
        usuario = iniciar_sesion(solicitud.email, solicitud.contrasena, repositorio, hasheador)
    except CredencialesInvalidas as error:
        raise HTTPException(
            status_code=401, detail=str(error), headers={"WWW-Authenticate": "Bearer"}
        ) from error
    return RespuestaLogin(
        access_token=emisor.emitir(usuario.id), expires_in=emisor.segundos_de_vida
    )


@router.get(
    "/yo",
    response_model=RespuestaYo,
    responses={401: {"description": "Falta el token o es inválido o está vencido"}},
)
def get_yo(usuario_id: Annotated[UUID, Depends(obtener_usuario_actual_id)]) -> RespuestaYo:
    """Ruta protegida de prueba: solo responde si llegas con un token válido."""
    return RespuestaYo(id=usuario_id)
