"""Conexión bancaria de solo lectura (Fintoc): conectar, ver cuentas y movimientos, importar."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Response
from pydantic import BaseModel, Field

from app.adaptadores.api.dependencias_auth import obtener_usuario_actual_id
from app.adaptadores.api.dependencias_bancos import (
    obtener_proveedor_bancario,
    obtener_repositorio_enlaces,
)
from app.adaptadores.api.dependencias_movimientos import obtener_repositorio_movimientos
from app.casos_de_uso.bancos import (
    conectar_banco,
    cuentas_del_banco,
    desconectar_banco,
    importar_abonos,
    movimientos_del_banco,
)
from app.casos_de_uso.puertos import RepositorioMovimientos
from app.casos_de_uso.puertos_bancos import ProveedorBancario, RepositorioEnlaces
from app.dominio.banco import BancoNoDisponible, EnlaceBancarioInvalido, SinEnlaceBancario

router = APIRouter(prefix="/bancos")

UsuarioActual = Annotated[UUID, Depends(obtener_usuario_actual_id)]
Enlaces = Annotated[RepositorioEnlaces, Depends(obtener_repositorio_enlaces)]
Proveedor = Annotated[ProveedorBancario, Depends(obtener_proveedor_bancario)]
Movimientos = Annotated[RepositorioMovimientos, Depends(obtener_repositorio_movimientos)]
CuentaId = Annotated[str, Path(min_length=1, max_length=100)]
_RESPUESTAS = {
    401: {"description": "Falta el token o es inválido o está vencido"},
    409: {"description": "Todavía no has conectado tu banco"},
    422: {"description": "Fintoc no reconoce el enlace"},
    502: {"description": "Fintoc no respondió"},
    503: {"description": "La conexión bancaria no está configurada en el servidor"},
}


class SolicitudEnlace(BaseModel):
    link_token: Annotated[str, Field(min_length=1, max_length=200)]


class RespuestaCuenta(BaseModel):
    id: str
    nombre: str
    numero_enmascarado: str
    moneda: str
    saldo: int | None


class RespuestaMovimientoBanco(BaseModel):
    id: str
    fecha: str
    monto: int
    descripcion: str
    moneda: str


class RespuestaImportacion(BaseModel):
    importados: int
    ya_importados: int
    cargos_omitidos: int


def _http(error: Exception) -> HTTPException:
    if isinstance(error, SinEnlaceBancario):
        return HTTPException(409, str(error))
    if isinstance(error, EnlaceBancarioInvalido):
        return HTTPException(422, str(error))
    return HTTPException(502, str(error))


_ERRORES = (SinEnlaceBancario, EnlaceBancarioInvalido, BancoNoDisponible)


def _cuentas(lista) -> list[RespuestaCuenta]:
    return [
        RespuestaCuenta(
            id=c.id,
            nombre=c.nombre,
            numero_enmascarado=c.numero_enmascarado,
            moneda=c.moneda,
            saldo=c.saldo,
        )
        for c in lista
    ]


@router.post("/enlace", response_model=list[RespuestaCuenta], responses=_RESPUESTAS)
def post_enlace(
    solicitud: SolicitudEnlace, usuario_id: UsuarioActual, enlaces: Enlaces, proveedor: Proveedor
) -> list[RespuestaCuenta]:
    """Conecta tu banco: valida el enlace con Fintoc y lo guarda cifrado. Devuelve tus cuentas."""
    try:
        return _cuentas(conectar_banco(usuario_id, solicitud.link_token, enlaces, proveedor))
    except _ERRORES as error:
        raise _http(error) from error


@router.delete("/enlace", status_code=204, responses={401: _RESPUESTAS[401]})
def delete_enlace(usuario_id: UsuarioActual, enlaces: Enlaces) -> Response:
    """Desconecta tu banco: borra el enlace guardado."""
    desconectar_banco(usuario_id, enlaces)
    return Response(status_code=204)


@router.get("/cuentas", response_model=list[RespuestaCuenta], responses=_RESPUESTAS)
def get_cuentas(
    usuario_id: UsuarioActual, enlaces: Enlaces, proveedor: Proveedor
) -> list[RespuestaCuenta]:
    try:
        return _cuentas(cuentas_del_banco(usuario_id, enlaces, proveedor))
    except _ERRORES as error:
        raise _http(error) from error


@router.get(
    "/cuentas/{cuenta_id}/movimientos",
    response_model=list[RespuestaMovimientoBanco],
    responses=_RESPUESTAS,
)
def get_movimientos_banco(
    cuenta_id: CuentaId, usuario_id: UsuarioActual, enlaces: Enlaces, proveedor: Proveedor
) -> list[RespuestaMovimientoBanco]:
    try:
        lista = movimientos_del_banco(usuario_id, cuenta_id, enlaces, proveedor)
    except _ERRORES as error:
        raise _http(error) from error
    return [
        RespuestaMovimientoBanco(
            id=m.id,
            fecha=m.fecha.isoformat(),
            monto=m.monto,
            descripcion=m.descripcion,
            moneda=m.moneda,
        )
        for m in lista
    ]


@router.post(
    "/cuentas/{cuenta_id}/importar",
    response_model=RespuestaImportacion,
    responses=_RESPUESTAS,
)
def post_importar(
    cuenta_id: CuentaId,
    usuario_id: UsuarioActual,
    enlaces: Enlaces,
    proveedor: Proveedor,
    repositorio: Movimientos,
) -> RespuestaImportacion:
    """Importa los abonos como ingresos (propone su reparto). Los cargos no se importan."""
    try:
        r = importar_abonos(usuario_id, cuenta_id, enlaces, proveedor, repositorio)
    except _ERRORES as error:
        raise _http(error) from error
    return RespuestaImportacion(
        importados=r.importados, ya_importados=r.ya_importados, cargos_omitidos=r.cargos_omitidos
    )
