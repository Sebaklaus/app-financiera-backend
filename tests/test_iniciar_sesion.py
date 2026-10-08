"""Pruebas del inicio de sesión (HU-02, pieza 1). Usan dobles en memoria, sin base de datos."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.casos_de_uso.iniciar_sesion import iniciar_sesion
from app.dominio.errores import CredencialesInvalidas
from app.dominio.usuario import Usuario


class RepositorioEnMemoria:
    def __init__(self) -> None:
        self.usuarios: dict[str, Usuario] = {}

    def buscar_por_email(self, email: str) -> Usuario | None:
        return self.usuarios.get(email)

    def guardar(self, usuario: Usuario) -> None:
        self.usuarios[usuario.email] = usuario


class HasheadorFalso:
    """No es seguro a propósito: 'hashear' da vuelta el texto y 'verificar' lo compara."""

    def hashear(self, contrasena: str) -> str:
        return "hash:" + contrasena[::-1]

    def verificar(self, contrasena: str, hash_guardado: str) -> bool:
        return self.hashear(contrasena) == hash_guardado


CLAVE_OK = "Clave1234"


def repositorio_con_ana() -> RepositorioEnMemoria:
    repo = RepositorioEnMemoria()
    repo.guardar(
        Usuario(
            id=uuid4(),
            email="ana@correo.cl",
            hash_contrasena=HasheadorFalso().hashear(CLAVE_OK),
            creado_en=datetime.now(timezone.utc),
        )
    )
    return repo


def entrar(email="ana@correo.cl", contrasena=CLAVE_OK, repo=None):
    repo = repo if repo is not None else repositorio_con_ana()
    return iniciar_sesion(email, contrasena, repo, HasheadorFalso())


def test_credenciales_correctas_devuelven_al_usuario():
    usuario = entrar()
    assert usuario.email == "ana@correo.cl"


def test_el_email_se_normaliza_al_entrar():
    usuario = entrar(email="  ANA@Correo.CL ")
    assert usuario.email == "ana@correo.cl"


def test_contrasena_incorrecta_se_rechaza():
    with pytest.raises(CredencialesInvalidas):
        entrar(contrasena="OtraClave99")


def test_email_inexistente_se_rechaza():
    with pytest.raises(CredencialesInvalidas):
        entrar(email="nadie@correo.cl")


def test_la_contrasena_distingue_mayusculas():
    with pytest.raises(CredencialesInvalidas):
        entrar(contrasena="clave1234")


@pytest.mark.parametrize("email", ["", "ana", "no es un email"])
def test_email_mal_formado_tambien_da_credenciales_invalidas(email):
    with pytest.raises(CredencialesInvalidas):
        entrar(email=email)


def test_el_mensaje_es_el_mismo_para_email_inexistente_y_clave_mala():
    try:
        entrar(email="nadie@correo.cl")
    except CredencialesInvalidas as error_email:
        mensaje_email = str(error_email)
    try:
        entrar(contrasena="OtraClave99")
    except CredencialesInvalidas as error_clave:
        mensaje_clave = str(error_clave)
    assert mensaje_email == mensaje_clave
