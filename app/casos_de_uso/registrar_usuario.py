"""Caso de uso: registrar un usuario nuevo (HU-01, escenarios 1 y 2)."""

from datetime import datetime, timezone
from uuid import uuid4

from app.casos_de_uso.puertos import HasheadorContrasenas, RepositorioUsuarios
from app.dominio.errores import EmailYaRegistrado
from app.dominio.usuario import Usuario, validar_contrasena, validar_email


def registrar_usuario(
    email: str,
    contrasena: str,
    repositorio: RepositorioUsuarios,
    hasheador: HasheadorContrasenas,
) -> Usuario:
    email_normalizado = validar_email(email)
    validar_contrasena(contrasena)

    if repositorio.buscar_por_email(email_normalizado) is not None:
        raise EmailYaRegistrado("Ya existe una cuenta con ese email")

    usuario = Usuario(
        id=uuid4(),
        email=email_normalizado,
        hash_contrasena=hasheador.hashear(contrasena),
        creado_en=datetime.now(timezone.utc),
    )
    repositorio.guardar(usuario)
    return usuario
