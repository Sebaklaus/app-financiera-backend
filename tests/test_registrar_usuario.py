"""Pruebas del registro. Usan dobles en memoria: no necesitan base de datos ni bcrypt."""

import pytest

from app.casos_de_uso.registrar_usuario import registrar_usuario
from app.dominio.errores import ContrasenaInvalida, EmailInvalido, EmailYaRegistrado
from app.dominio.usuario import Usuario


class RepositorioEnMemoria:
    def __init__(self) -> None:
        self.usuarios: dict[str, Usuario] = {}

    def buscar_por_email(self, email: str) -> Usuario | None:
        return self.usuarios.get(email)

    def guardar(self, usuario: Usuario) -> None:
        self.usuarios[usuario.email] = usuario


class HasheadorFalso:
    """No es seguro a propósito: solo sirve para probar el flujo rápido."""

    def hashear(self, contrasena: str) -> str:
        return "hash:" + contrasena[::-1]


CLAVE_OK = "Clave1234"


def registrar(email="ana@correo.cl", contrasena=CLAVE_OK, repo=None):
    repo = repo if repo is not None else RepositorioEnMemoria()
    usuario = registrar_usuario(email, contrasena, repo, HasheadorFalso())
    return usuario, repo


def test_registro_exitoso_guarda_el_usuario():
    usuario, repo = registrar()
    assert repo.buscar_por_email("ana@correo.cl") == usuario


def test_nunca_se_guarda_la_contrasena_en_claro():
    usuario, _ = registrar()
    assert usuario.hash_contrasena != CLAVE_OK
    assert CLAVE_OK not in usuario.hash_contrasena


def test_el_email_se_normaliza():
    usuario, _ = registrar(email="  Ana@Correo.CL ")
    assert usuario.email == "ana@correo.cl"


def test_email_duplicado_se_rechaza_aunque_cambien_las_mayusculas():
    _, repo = registrar(email="ana@correo.cl")
    with pytest.raises(EmailYaRegistrado):
        registrar(email="ANA@correo.cl", repo=repo)


@pytest.mark.parametrize("email", ["", "ana", "ana@", "@correo.cl", "ana@correo", "a b@c.cl"])
def test_email_con_formato_invalido(email):
    with pytest.raises(EmailInvalido):
        registrar(email=email)


@pytest.mark.parametrize(
    "contrasena",
    [
        "Ab1",  # muy corta
        "soloLetrasAqui",  # sin número
        "123456789",  # sin letra
        "a1" * 40,  # pasa de 72 bytes
    ],
)
def test_contrasena_que_no_cumple_los_requisitos(contrasena):
    with pytest.raises(ContrasenaInvalida):
        registrar(contrasena=contrasena)


def test_si_falla_la_validacion_no_se_guarda_nada():
    repo = RepositorioEnMemoria()
    with pytest.raises(ContrasenaInvalida):
        registrar(contrasena="corta", repo=repo)
    assert repo.usuarios == {}
