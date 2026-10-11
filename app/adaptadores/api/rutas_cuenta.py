"""Adaptador HTTP de la cuenta: ver mis datos, cambiar clave o email y borrar la cuenta.

Regla de estas rutas: 401 significa "tu token no sirve". Si la contraseña que escribes para
confirmar está mal, es 403, para que la app no confunda eso con una sesión vencida.
"""

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.adaptadores.api.dependencias import obtener_hasheador
from app.adaptadores.api.dependencias_auth import (
    obtener_repositorio_intentos,
    obtener_repositorio_tokens,
    obtener_usuario_actual_id,
)
from app.adaptadores.api.dependencias_cuenta import obtener_repositorio_cuenta
from app.adaptadores.api.dependencias_movimientos import obtener_repositorio_movimientos
from app.casos_de_uso.cuenta import (
    cambiar_contrasena,
    cambiar_email,
    eliminar_cuenta,
    exportar_datos,
)
from app.casos_de_uso.puertos import (
    HasheadorContrasenas,
    RepositorioIntentosLogin,
    RepositorioMovimientos,
    RepositorioTokensRefresco,
)
from app.casos_de_uso.puertos_cuenta import RepositorioCuenta
from app.dominio.categorias import Categoria
from app.dominio.confirmacion import EstadoConfirmacion
from app.dominio.errores import (
    ContrasenaInvalida,
    CredencialesInvalidas,
    DemasiadosIntentos,
    EmailInvalido,
    EmailYaRegistrado,
)
from app.dominio.reloj import a_utc

router = APIRouter(prefix="/yo")

_CABECERA_401 = {"WWW-Authenticate": "Bearer"}
UsuarioActual = Annotated[UUID, Depends(obtener_usuario_actual_id)]
Cuenta = Annotated[RepositorioCuenta, Depends(obtener_repositorio_cuenta)]
Movimientos = Annotated[RepositorioMovimientos, Depends(obtener_repositorio_movimientos)]
Tokens = Annotated[RepositorioTokensRefresco, Depends(obtener_repositorio_tokens)]
Intentos = Annotated[RepositorioIntentosLogin, Depends(obtener_repositorio_intentos)]
Hasheador = Annotated[HasheadorContrasenas, Depends(obtener_hasheador)]
Clave = Annotated[str, Field(min_length=1, max_length=256)]

_RESPUESTAS = {
    401: {"description": "Falta el token o es inválido o está vencido"},
    403: {"description": "La contraseña de confirmación no es correcta"},
    429: {"description": "Demasiados intentos fallidos: espera antes de volver a intentar"},
}


class SolicitudCambioClave(BaseModel):
    contrasena_actual: Clave
    contrasena_nueva: Clave


class SolicitudCambioEmail(BaseModel):
    contrasena: Clave
    email_nuevo: Annotated[str, Field(min_length=1, max_length=320)]


class SolicitudEliminar(BaseModel):
    contrasena: Clave


class RespuestaEmail(BaseModel):
    email: str


class MovimientoExportado(BaseModel):
    id: UUID
    tipo: str
    monto: int
    categoria: Categoria | None
    descripcion: str
    fecha: date


class ConfirmacionExportada(BaseModel):
    id: UUID
    ingreso_id: UUID
    categoria: Categoria
    monto: int
    estado: EstadoConfirmacion
    creado_en: datetime
    decidido_en: datetime | None


class RespuestaDatos(BaseModel):
    id: UUID
    email: str
    creado_en: datetime
    exportado_en: datetime
    movimientos: list[MovimientoExportado]
    confirmaciones: list[ConfirmacionExportada]


def _error_de_clave(error: Exception) -> HTTPException:
    if isinstance(error, DemasiadosIntentos):
        return HTTPException(429, str(error), headers={"Retry-After": str(error.segundos)})
    return HTTPException(403, "La contraseña no es correcta")


@router.get("/datos", response_model=RespuestaDatos, responses={401: _RESPUESTAS[401]})
def get_datos(usuario_id: UsuarioActual, cuentas: Cuenta, movimientos: Movimientos):
    """Descarga todo lo que la app guarda de ti (derecho de acceso y portabilidad)."""
    try:
        datos = exportar_datos(usuario_id, cuentas, movimientos)
    except CredencialesInvalidas as error:
        raise HTTPException(401, "La cuenta ya no existe", headers=_CABECERA_401) from error
    return RespuestaDatos(
        id=datos.usuario.id,
        email=datos.usuario.email,
        creado_en=a_utc(datos.usuario.creado_en),
        exportado_en=a_utc(datos.exportado_en),
        movimientos=[
            MovimientoExportado(
                id=m.id,
                tipo=m.tipo.value,
                monto=m.monto,
                categoria=m.categoria,
                descripcion=m.descripcion,
                fecha=m.fecha,
            )
            for m in datos.movimientos
        ],
        confirmaciones=[
            ConfirmacionExportada(
                id=c.id,
                ingreso_id=c.ingreso_id,
                categoria=c.categoria,
                monto=c.monto,
                estado=c.estado,
                creado_en=a_utc(c.creado_en),
                decidido_en=None if c.decidido_en is None else a_utc(c.decidido_en),
            )
            for c in datos.confirmaciones
        ],
    )


@router.post("/contrasena", status_code=204, responses=_RESPUESTAS)
def post_cambiar_contrasena(
    solicitud: SolicitudCambioClave,
    usuario_id: UsuarioActual,
    cuentas: Cuenta,
    hasheador: Hasheador,
    intentos: Intentos,
    tokens: Tokens,
) -> Response:
    """Cambia tu contraseña y cierra todas tus sesiones: tendrás que entrar de nuevo."""
    try:
        cambiar_contrasena(
            usuario_id,
            solicitud.contrasena_actual,
            solicitud.contrasena_nueva,
            cuentas,
            hasheador,
            intentos,
            tokens,
        )
    except (CredencialesInvalidas, DemasiadosIntentos) as error:
        raise _error_de_clave(error) from error
    except ContrasenaInvalida as error:
        raise HTTPException(422, str(error)) from error
    return Response(status_code=204)


@router.patch("/email", response_model=RespuestaEmail, responses=_RESPUESTAS)
def patch_cambiar_email(
    solicitud: SolicitudCambioEmail,
    usuario_id: UsuarioActual,
    cuentas: Cuenta,
    hasheador: Hasheador,
    intentos: Intentos,
) -> RespuestaEmail:
    """Corrige tu email (derecho de rectificación). Pide tu contraseña."""
    try:
        email = cambiar_email(
            usuario_id, solicitud.contrasena, solicitud.email_nuevo, cuentas, hasheador, intentos
        )
    except (CredencialesInvalidas, DemasiadosIntentos) as error:
        raise _error_de_clave(error) from error
    except EmailInvalido as error:
        raise HTTPException(422, str(error)) from error
    except EmailYaRegistrado as error:
        raise HTTPException(409, str(error)) from error
    return RespuestaEmail(email=email)


@router.post("/eliminar", status_code=204, responses=_RESPUESTAS)
def post_eliminar_cuenta(
    solicitud: SolicitudEliminar,
    usuario_id: UsuarioActual,
    cuentas: Cuenta,
    hasheador: Hasheador,
    intentos: Intentos,
) -> Response:
    """Borra tu cuenta y TODOS tus datos (derecho de supresión). No se puede deshacer."""
    try:
        eliminar_cuenta(usuario_id, solicitud.contrasena, cuentas, hasheador, intentos)
    except (CredencialesInvalidas, DemasiadosIntentos) as error:
        raise _error_de_clave(error) from error
    return Response(status_code=204)
