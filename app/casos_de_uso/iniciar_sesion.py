"""Caso de uso: iniciar sesión (HU-02): comprobar email y contraseña."""

from app.casos_de_uso.puertos import HasheadorContrasenas, RepositorioUsuarios
from app.dominio.errores import CredencialesInvalidas
from app.dominio.usuario import Usuario, normalizar_email

# Un solo texto para los dos fallos: así nadie puede averiguar qué emails tienen cuenta.
MENSAJE_CREDENCIALES = "Email o contraseña incorrectos"


def iniciar_sesion(
    email: str,
    contrasena: str,
    repositorio: RepositorioUsuarios,
    hasheador: HasheadorContrasenas,
) -> Usuario:
    usuario = repositorio.buscar_por_email(normalizar_email(email))
    if usuario is None:
        raise CredencialesInvalidas(MENSAJE_CREDENCIALES)
    if not hasheador.verificar(contrasena, usuario.hash_contrasena):
        raise CredencialesInvalidas(MENSAJE_CREDENCIALES)
    return usuario
