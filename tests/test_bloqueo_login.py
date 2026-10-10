"""Pruebas del bloqueo por intentos fallidos de login (sin base de datos)."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.casos_de_uso.login_con_bloqueo import iniciar_sesion_con_bloqueo
from app.dominio.bloqueo import (
    DURACION_BLOQUEO,
    MAX_INTENTOS,
    VENTANA,
    clave_de,
    registrar_fallo,
)
from app.dominio.errores import CredencialesInvalidas, DemasiadosIntentos
from app.dominio.usuario import Usuario
from tests.dobles import RepositorioIntentosEnMemoria

AHORA = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
CLAVE_OK = "Clave1234"


class UsuariosEnMemoria:
    def __init__(self) -> None:
        self.usuarios: dict[str, Usuario] = {}

    def buscar_por_email(self, email: str) -> Usuario | None:
        return self.usuarios.get(email)

    def guardar(self, usuario: Usuario) -> None:
        self.usuarios[usuario.email] = usuario


class HasheadorFalso:
    def hashear(self, contrasena: str) -> str:
        return "hash:" + contrasena[::-1]

    def verificar(self, contrasena: str, hash_guardado: str) -> bool:
        return self.hashear(contrasena) == hash_guardado


def escenario():
    usuarios = UsuariosEnMemoria()
    usuarios.guardar(
        Usuario(
            id=uuid4(),
            email="ana@correo.cl",
            hash_contrasena=HasheadorFalso().hashear(CLAVE_OK),
            creado_en=AHORA,
        )
    )
    return usuarios, HasheadorFalso(), RepositorioIntentosEnMemoria()


def entrar(esc, contrasena, ahora=AHORA, email="ana@correo.cl"):
    usuarios, hasheador, intentos = esc
    return iniciar_sesion_con_bloqueo(email, contrasena, usuarios, hasheador, intentos, ahora)


def fallar(esc, veces, ahora=AHORA, email="ana@correo.cl"):
    for _ in range(veces):
        with pytest.raises(CredencialesInvalidas):
            entrar(esc, "mala", ahora, email)


# --- reglas puras -----------------------------------------------------------------------


def test_la_clave_no_distingue_mayusculas_ni_espacios():
    assert clave_de(" ANA@correo.cl ") == clave_de("ana@correo.cl")
    assert len(clave_de("x@y.cl")) == 64


def test_antes_del_maximo_no_hay_bloqueo():
    registro = None
    for _ in range(MAX_INTENTOS - 1):
        registro = registrar_fallo(registro, "k", AHORA)
    assert registro.fallos == MAX_INTENTOS - 1
    assert not registro.esta_bloqueado(AHORA)


def test_el_ultimo_intento_bloquea_por_la_duracion_fijada():
    registro = None
    for _ in range(MAX_INTENTOS):
        registro = registrar_fallo(registro, "k", AHORA)
    assert registro.esta_bloqueado(AHORA)
    assert registro.bloqueado_hasta == AHORA + DURACION_BLOQUEO
    assert registro.segundos_restantes(AHORA) == int(DURACION_BLOQUEO.total_seconds())


def test_los_fallos_viejos_se_olvidan():
    registro = registrar_fallo(None, "k", AHORA)
    registro = registrar_fallo(registro, "k", AHORA)
    despues = AHORA + VENTANA + timedelta(seconds=1)
    registro = registrar_fallo(registro, "k", despues)
    assert registro.fallos == 1


def test_terminado_el_bloqueo_se_parte_de_cero():
    registro = None
    for _ in range(MAX_INTENTOS):
        registro = registrar_fallo(registro, "k", AHORA)
    despues = AHORA + DURACION_BLOQUEO + timedelta(seconds=1)
    assert not registro.esta_bloqueado(despues)
    registro = registrar_fallo(registro, "k", despues)
    assert registro.fallos == 1
    assert not registro.esta_bloqueado(despues)


# --- caso de uso ------------------------------------------------------------------------


def test_un_login_correcto_funciona_y_no_deja_rastro():
    esc = escenario()
    assert entrar(esc, CLAVE_OK).email == "ana@correo.cl"
    assert esc[2].registros == {}


def test_una_contrasena_mala_sigue_dando_credenciales_invalidas():
    esc = escenario()
    fallar(esc, MAX_INTENTOS - 1)


def test_el_quinto_fallo_bloquea():
    esc = escenario()
    fallar(esc, MAX_INTENTOS - 1)
    with pytest.raises(DemasiadosIntentos) as error:
        entrar(esc, "mala")
    assert error.value.segundos == int(DURACION_BLOQUEO.total_seconds())
    assert "15 minutos" in str(error.value)


def test_bloqueado_ni_la_contrasena_correcta_entra():
    esc = escenario()
    fallar(esc, MAX_INTENTOS - 1)
    with pytest.raises(DemasiadosIntentos):
        entrar(esc, "mala")
    with pytest.raises(DemasiadosIntentos):
        entrar(esc, CLAVE_OK)


def test_pasado_el_bloqueo_se_puede_entrar_de_nuevo():
    esc = escenario()
    fallar(esc, MAX_INTENTOS - 1)
    with pytest.raises(DemasiadosIntentos):
        entrar(esc, "mala")
    despues = AHORA + DURACION_BLOQUEO + timedelta(seconds=1)
    assert entrar(esc, CLAVE_OK, despues).email == "ana@correo.cl"
    assert esc[2].registros == {}


def test_un_login_correcto_reinicia_la_cuenta():
    esc = escenario()
    fallar(esc, MAX_INTENTOS - 1)
    entrar(esc, CLAVE_OK)
    fallar(esc, MAX_INTENTOS - 1)  # vuelve a tener todos sus intentos


def test_el_bloqueo_es_por_email_y_no_afecta_a_otros():
    esc = escenario()
    fallar(esc, MAX_INTENTOS - 1)
    with pytest.raises(DemasiadosIntentos):
        entrar(esc, "mala")
    fallar(esc, 1, email="otra@correo.cl")  # otra persona sigue con sus intentos


def test_un_email_sin_cuenta_tambien_se_bloquea_igual():
    esc = escenario()
    fallar(esc, MAX_INTENTOS - 1, email="nadie@correo.cl")
    with pytest.raises(DemasiadosIntentos):
        entrar(esc, "mala", email="nadie@correo.cl")


def test_mayusculas_y_espacios_cuentan_como_el_mismo_email():
    esc = escenario()
    fallar(esc, 2, email="ana@correo.cl")
    fallar(esc, 2, email="  ANA@correo.cl ")
    with pytest.raises(DemasiadosIntentos):
        entrar(esc, "mala", email="Ana@Correo.cl")
