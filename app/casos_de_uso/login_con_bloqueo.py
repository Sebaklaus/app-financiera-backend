"""Caso de uso: iniciar sesión con bloqueo por intentos fallidos (HU-02)."""

from datetime import datetime, timezone

from app.casos_de_uso.iniciar_sesion import iniciar_sesion
from app.casos_de_uso.puertos import (
    HasheadorContrasenas,
    RepositorioIntentosLogin,
    RepositorioUsuarios,
)
from app.dominio.bloqueo import clave_de, registrar_fallo
from app.dominio.errores import CredencialesInvalidas, DemasiadosIntentos
from app.dominio.usuario import Usuario


def iniciar_sesion_con_bloqueo(
    email: str,
    contrasena: str,
    usuarios: RepositorioUsuarios,
    hasheador: HasheadorContrasenas,
    intentos: RepositorioIntentosLogin,
    ahora: datetime | None = None,
) -> Usuario:
    ahora = ahora or datetime.now(timezone.utc)
    clave = clave_de(email)
    registro = intentos.obtener(clave)
    if registro is not None and registro.esta_bloqueado(ahora):
        # Bloqueado: ni siquiera se mira la contraseña, aunque fuera la correcta.
        raise DemasiadosIntentos(registro.segundos_restantes(ahora))
    try:
        usuario = iniciar_sesion(email, contrasena, usuarios, hasheador)
    except CredencialesInvalidas:
        nuevo = registrar_fallo(registro, clave, ahora)
        intentos.guardar(nuevo)
        if nuevo.esta_bloqueado(ahora):
            raise DemasiadosIntentos(nuevo.segundos_restantes(ahora)) from None
        raise
    if registro is not None:
        intentos.borrar(clave)  # entró bien: se olvidan los fallos anteriores
    return usuario
