"""Casos de uso de la cuenta (Ley 21.719, derechos de acceso, rectificación y supresión).

Las acciones delicadas (cambiar clave o email, borrar la cuenta) piden la contraseña otra vez,
aunque la persona ya tenga sesión: así, quien encuentre un teléfono desbloqueado no puede
adueñarse ni destruir la cuenta. Esa verificación comparte el bloqueo por intentos del login.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from app.casos_de_uso.login_con_bloqueo import iniciar_sesion_con_bloqueo
from app.casos_de_uso.puertos import (
    HasheadorContrasenas,
    RepositorioIntentosLogin,
    RepositorioMovimientos,
    RepositorioTokensRefresco,
)
from app.casos_de_uso.puertos_consentimientos import RepositorioConsentimientos
from app.casos_de_uso.puertos_cuenta import RepositorioCuenta
from app.dominio.bloqueo import clave_de
from app.dominio.confirmacion import Confirmacion
from app.dominio.consentimiento import Consentimiento, PerfilDeclarado
from app.dominio.errores import ContrasenaInvalida, CredencialesInvalidas
from app.dominio.movimiento import Movimiento
from app.dominio.usuario import Usuario, validar_contrasena, validar_email


@dataclass(frozen=True)
class DatosExportados:
    usuario: Usuario
    movimientos: list[Movimiento]
    confirmaciones: list[Confirmacion]
    exportado_en: datetime
    consentimientos: list[Consentimiento] = field(default_factory=list)
    perfil: PerfilDeclarado | None = None


def _reautenticar(
    usuario_id: UUID,
    contrasena: str,
    cuentas: RepositorioCuenta,
    hasheador: HasheadorContrasenas,
    intentos: RepositorioIntentosLogin,
    ahora: datetime,
) -> Usuario:
    """Comprueba la contraseña actual. Lanza CredencialesInvalidas o DemasiadosIntentos."""
    usuario = cuentas.buscar_por_id(usuario_id)
    if usuario is None:
        raise CredencialesInvalidas("Email o contraseña incorrectos")
    return iniciar_sesion_con_bloqueo(
        usuario.email, contrasena, cuentas, hasheador, intentos, ahora
    )


def exportar_datos(
    usuario_id: UUID,
    cuentas: RepositorioCuenta,
    movimientos: RepositorioMovimientos,
    ahora: datetime | None = None,
    consentimientos: RepositorioConsentimientos | None = None,
) -> DatosExportados:
    """Derecho de acceso y portabilidad: todo lo que la app guarda de la persona."""
    usuario = cuentas.buscar_por_id(usuario_id)
    if usuario is None:
        raise CredencialesInvalidas("La cuenta no existe")
    return DatosExportados(
        usuario=usuario,
        movimientos=movimientos.listar_por_usuario(usuario_id),
        confirmaciones=movimientos.listar_confirmaciones_por_usuario(usuario_id),
        exportado_en=ahora or datetime.now(timezone.utc),
        consentimientos=(
            [] if consentimientos is None else consentimientos.listar_consentimientos(usuario_id)
        ),
        perfil=None if consentimientos is None else consentimientos.obtener_perfil(usuario_id),
    )


def cambiar_contrasena(
    usuario_id: UUID,
    contrasena_actual: str,
    contrasena_nueva: str,
    cuentas: RepositorioCuenta,
    hasheador: HasheadorContrasenas,
    intentos: RepositorioIntentosLogin,
    tokens: RepositorioTokensRefresco,
    ahora: datetime | None = None,
) -> None:
    """Cambia la clave y cierra TODAS las sesiones (también esta: hay que entrar de nuevo)."""
    ahora = ahora or datetime.now(timezone.utc)
    _reautenticar(usuario_id, contrasena_actual, cuentas, hasheador, intentos, ahora)
    validar_contrasena(contrasena_nueva)
    if contrasena_nueva == contrasena_actual:
        raise ContrasenaInvalida("La contraseña nueva debe ser distinta de la actual")
    cuentas.cambiar_hash(usuario_id, hasheador.hashear(contrasena_nueva))
    tokens.revocar_todos_de_usuario(usuario_id, ahora)


def cambiar_email(
    usuario_id: UUID,
    contrasena: str,
    email_nuevo: str,
    cuentas: RepositorioCuenta,
    hasheador: HasheadorContrasenas,
    intentos: RepositorioIntentosLogin,
    ahora: datetime | None = None,
) -> str:
    """Derecho de rectificación. Devuelve el email ya normalizado."""
    ahora = ahora or datetime.now(timezone.utc)
    usuario = _reautenticar(usuario_id, contrasena, cuentas, hasheador, intentos, ahora)
    email = validar_email(email_nuevo)
    if email != usuario.email:
        cuentas.cambiar_email(usuario_id, email)
    return email


def eliminar_cuenta(
    usuario_id: UUID,
    contrasena: str,
    cuentas: RepositorioCuenta,
    hasheador: HasheadorContrasenas,
    intentos: RepositorioIntentosLogin,
    ahora: datetime | None = None,
) -> None:
    """Derecho de supresión: borra la cuenta y todos sus datos. No se puede deshacer."""
    ahora = ahora or datetime.now(timezone.utc)
    usuario = _reautenticar(usuario_id, contrasena, cuentas, hasheador, intentos, ahora)
    cuentas.eliminar_cuenta(usuario_id, clave_de(usuario.email))
