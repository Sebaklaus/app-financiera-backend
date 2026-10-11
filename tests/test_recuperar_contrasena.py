"""Pruebas de la recuperación de contraseña, sin base de datos."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.casos_de_uso.recuperar_contrasena import restablecer_contrasena, solicitar_recuperacion
from app.dominio.bloqueo import RegistroIntentos, clave_de
from app.dominio.errores import ContrasenaInvalida, TokenInvalido
from app.dominio.recuperacion import ESPERA_ENTRE_SOLICITUDES, VIDA_RECUPERACION
from app.dominio.token_refresco import nuevo_token_refresco
from app.dominio.usuario import Usuario
from tests.dobles import RepositorioIntentosEnMemoria, RepositorioTokensEnMemoria
from tests.dobles_cuenta import RepositorioCuentaEnMemoria
from tests.dobles_recuperacion import EnviadorEnMemoria, RepositorioRecuperacionEnMemoria

AHORA = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)


class HasheadorFalso:
    def hashear(self, contrasena: str) -> str:
        return f"hash:{contrasena}"

    def verificar(self, contrasena: str, hash_guardado: str) -> bool:
        return hash_guardado == f"hash:{contrasena}"


class Entorno:
    def __init__(self) -> None:
        self.ana = Usuario(uuid4(), "ana@correo.cl", "hash:Clave1234", AHORA)
        self.cuentas = RepositorioCuentaEnMemoria(self.ana)
        self.recuperaciones = RepositorioRecuperacionEnMemoria()
        self.enviador = EnviadorEnMemoria()
        self.tokens = RepositorioTokensEnMemoria()
        self.intentos = RepositorioIntentosEnMemoria()

    def pedir(self, email="ana@correo.cl", ahora=AHORA):
        solicitar_recuperacion(email, self.cuentas, self.recuperaciones, self.enviador, ahora)

    def restablecer(self, token, nueva="Nueva56789", ahora=AHORA):
        restablecer_contrasena(
            token,
            nueva,
            self.cuentas,
            self.recuperaciones,
            HasheadorFalso(),
            self.tokens,
            self.intentos,
            ahora,
        )

    def token_enviado(self):
        return self.enviador.enviados[-1][1]


def test_solicitar_envia_el_correo_con_un_token():
    e = Entorno()
    e.pedir()
    assert len(e.enviador.enviados) == 1
    assert e.enviador.enviados[0][0] == "ana@correo.cl"
    assert len(e.token_enviado()) > 30


def test_solicitar_con_email_distinto_en_mayusculas_igual_funciona():
    e = Entorno()
    e.pedir("  ANA@correo.CL ")
    assert len(e.enviador.enviados) == 1


def test_solicitar_con_un_email_sin_cuenta_no_envia_ni_falla():
    e = Entorno()
    e.pedir("nadie@correo.cl")
    assert e.enviador.enviados == []
    assert e.recuperaciones.tokens == {}


def test_el_token_no_se_guarda_en_claro():
    e = Entorno()
    e.pedir()
    token = e.token_enviado()
    assert all(token not in str(t) for t in e.recuperaciones.tokens.values())


def test_pedir_otra_vez_enseguida_se_ignora():
    e = Entorno()
    e.pedir()
    e.pedir(ahora=AHORA + ESPERA_ENTRE_SOLICITUDES - timedelta(seconds=1))
    assert len(e.enviador.enviados) == 1


def test_pedir_pasado_el_tiempo_envia_otro_y_el_primero_deja_de_servir():
    e = Entorno()
    e.pedir()
    primero = e.token_enviado()
    e.pedir(ahora=AHORA + timedelta(minutes=5))
    assert len(e.enviador.enviados) == 2
    ahora = AHORA + timedelta(minutes=6)
    with pytest.raises(TokenInvalido):
        e.restablecer(primero, ahora=ahora)
    e.restablecer(e.token_enviado(), ahora=ahora)


def test_restablecer_cambia_la_clave_cierra_sesiones_y_quita_el_bloqueo():
    e = Entorno()
    _, sesion = nuevo_token_refresco(e.ana.id, AHORA)
    e.tokens.guardar(sesion)
    clave = clave_de(e.ana.email)
    e.intentos.guardar(RegistroIntentos(clave, 5, AHORA, AHORA + timedelta(minutes=15)))
    e.pedir()
    e.restablecer(e.token_enviado(), ahora=AHORA + timedelta(minutes=2))
    assert e.cuentas.usuarios[e.ana.id].hash_contrasena == "hash:Nueva56789"
    assert e.tokens.tokens[sesion.id].revocado_en is not None
    assert e.intentos.obtener(clave) is None


def test_el_token_sirve_una_sola_vez():
    e = Entorno()
    e.pedir()
    token = e.token_enviado()
    e.restablecer(token)
    with pytest.raises(TokenInvalido):
        e.restablecer(token, nueva="Otra987654")


def test_un_token_vencido_no_sirve():
    e = Entorno()
    e.pedir()
    with pytest.raises(TokenInvalido):
        e.restablecer(e.token_enviado(), ahora=AHORA + VIDA_RECUPERACION + timedelta(seconds=1))


def test_un_token_inventado_no_sirve():
    with pytest.raises(TokenInvalido):
        Entorno().restablecer("token-falso")


def test_una_clave_debil_no_gasta_el_token():
    e = Entorno()
    e.pedir()
    token = e.token_enviado()
    with pytest.raises(ContrasenaInvalida):
        e.restablecer(token, nueva="corta")
    e.restablecer(token, nueva="Buena56789")
    assert e.cuentas.usuarios[e.ana.id].hash_contrasena == "hash:Buena56789"
