"""Piezas de autenticación que las rutas piden (emisor de tokens y 'quién es el usuario')."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated
from uuid import UUID

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.adaptadores.api.dependencias import obtener_sesion
from app.casos_de_uso.puertos import EmisorTokens
from app.dominio.errores import TokenInvalido
from app.infraestructura.emisor_jwt import EmisorJWT
from app.infraestructura.repositorio_intentos_sql import RepositorioIntentosSQL
from app.infraestructura.repositorio_tokens_sql import RepositorioTokensSQL

load_dotenv()

# auto_error=False: el error 401 lo armamos nosotros, con nuestro mensaje en español.
_esquema_bearer = HTTPBearer(auto_error=False)
_CABECERA_401 = {"WWW-Authenticate": "Bearer"}


@lru_cache
def obtener_emisor_tokens() -> EmisorJWT:
    ruta_privada = Path(os.getenv("JWT_CLAVE_PRIVADA", "claves/jwt_privada.pem"))
    ruta_publica = Path(os.getenv("JWT_CLAVE_PUBLICA", "claves/jwt_publica.pem"))
    if not ruta_privada.exists() or not ruta_publica.exists():
        raise RuntimeError(
            "Faltan las claves JWT. Ejecuta: python -m app.infraestructura.generar_claves"
        )
    return EmisorJWT(
        clave_privada=ruta_privada.read_text(encoding="ascii"),
        clave_publica=ruta_publica.read_text(encoding="ascii"),
    )


def obtener_repositorio_tokens(
    sesion: Annotated[Session, Depends(obtener_sesion)],
) -> RepositorioTokensSQL:
    return RepositorioTokensSQL(sesion)


def obtener_repositorio_intentos(
    sesion: Annotated[Session, Depends(obtener_sesion)],
) -> RepositorioIntentosSQL:
    return RepositorioIntentosSQL(sesion)


def obtener_usuario_actual_id(
    credenciales: Annotated[HTTPAuthorizationCredentials | None, Depends(_esquema_bearer)],
    emisor: Annotated[EmisorTokens, Depends(obtener_emisor_tokens)],
) -> UUID:
    """El 'guardia de la puerta': exige el brazalete y devuelve el id de su dueño."""
    if credenciales is None:
        raise HTTPException(401, "Falta el token de acceso", headers=_CABECERA_401)
    try:
        return emisor.leer(credenciales.credentials)
    except TokenInvalido as error:
        raise HTTPException(401, str(error), headers=_CABECERA_401) from error
