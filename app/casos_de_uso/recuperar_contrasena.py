"""Casos de uso: pedir y usar el enlace para recuperar la contraseña."""

from datetime import datetime, timezone

from app.casos_de_uso.puertos import (
    HasheadorContrasenas,
    RepositorioIntentosLogin,
    RepositorioTokensRefresco,
)
from app.casos_de_uso.puertos_cuenta import RepositorioCuenta
from app.casos_de_uso.puertos_recuperacion import EnviadorCorreo, RepositorioRecuperacion
from app.dominio.bloqueo import clave_de
from app.dominio.errores import TokenInvalido
from app.dominio.recuperacion import ESPERA_ENTRE_SOLICITUDES, nuevo_token_recuperacion
from app.dominio.token_refresco import calcular_huella
from app.dominio.usuario import normalizar_email, validar_contrasena

MENSAJE_ENLACE_INVALIDO = "El enlace no sirve o ya venció: pide uno nuevo"


def solicitar_recuperacion(
    email: str,
    cuentas: RepositorioCuenta,
    recuperaciones: RepositorioRecuperacion,
    enviador: EnviadorCorreo,
    ahora: datetime | None = None,
) -> None:
    """No devuelve nada A PROPÓSITO: existan o no la cuenta, la respuesta es la misma.

    Si respondiera distinto, cualquiera podría averiguar qué emails tienen cuenta.
    """
    ahora = ahora or datetime.now(timezone.utc)
    usuario = cuentas.buscar_por_email(normalizar_email(email))
    if usuario is None:
        return
    ultimo = recuperaciones.ultimo_creado_en(usuario.id)
    if ultimo is not None and ahora - ultimo < ESPERA_ENTRE_SOLICITUDES:
        return
    recuperaciones.invalidar_pendientes(usuario.id, ahora)
    token, registro = nuevo_token_recuperacion(usuario.id, ahora)
    recuperaciones.guardar(registro)
    enviador.enviar_recuperacion(usuario.email, token)


def restablecer_contrasena(
    token: str,
    contrasena_nueva: str,
    cuentas: RepositorioCuenta,
    recuperaciones: RepositorioRecuperacion,
    hasheador: HasheadorContrasenas,
    tokens: RepositorioTokensRefresco,
    intentos: RepositorioIntentosLogin,
    ahora: datetime | None = None,
) -> None:
    """Cambia la clave con el token del correo, cierra todas las sesiones y quita el bloqueo."""
    ahora = ahora or datetime.now(timezone.utc)
    registro = recuperaciones.buscar_por_huella(calcular_huella(token))
    if registro is None or not registro.esta_vigente(ahora):
        raise TokenInvalido(MENSAJE_ENLACE_INVALIDO)
    usuario = cuentas.buscar_por_id(registro.usuario_id)
    if usuario is None:
        raise TokenInvalido(MENSAJE_ENLACE_INVALIDO)
    # Se valida ANTES de gastar el token: si la clave es débil, puede corregirla y reintentar.
    validar_contrasena(contrasena_nueva)
    if not recuperaciones.marcar_usado(registro.id, ahora):
        raise TokenInvalido(MENSAJE_ENLACE_INVALIDO)  # lo usó otra petición un instante antes
    cuentas.cambiar_hash(usuario.id, hasheador.hashear(contrasena_nueva))
    tokens.revocar_todos_de_usuario(usuario.id, ahora)
    intentos.borrar(clave_de(usuario.email))
