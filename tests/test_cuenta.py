"""Pruebas de los casos de uso de la cuenta, sin base de datos."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.casos_de_uso.cuenta import (
    cambiar_contrasena,
    cambiar_email,
    eliminar_cuenta,
    exportar_datos,
)
from app.dominio.bloqueo import clave_de
from app.dominio.errores import (
    ContrasenaInvalida,
    CredencialesInvalidas,
    DemasiadosIntentos,
    EmailInvalido,
    EmailYaRegistrado,
)
from app.dominio.token_refresco import nuevo_token_refresco
from app.dominio.usuario import Usuario
from tests.dobles import (
    RepositorioEnMemoria,
    RepositorioIntentosEnMemoria,
    RepositorioTokensEnMemoria,
)
from tests.dobles_cuenta import RepositorioCuentaEnMemoria

AHORA = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)


class HasheadorFalso:
    def hashear(self, contrasena: str) -> str:
        return f"hash:{contrasena}"

    def verificar(self, contrasena: str, hash_guardado: str) -> bool:
        return hash_guardado == f"hash:{contrasena}"


def usuario(email: str = "ana@correo.cl", clave: str = "Clave1234") -> Usuario:
    return Usuario(id=uuid4(), email=email, hash_contrasena=f"hash:{clave}", creado_en=AHORA)


def cambiar_clave(ana, cuentas, intentos, hasheador, actual, nueva, tokens=None):
    cambiar_contrasena(
        ana.id,
        actual,
        nueva,
        cuentas,
        hasheador,
        intentos,
        tokens or RepositorioTokensEnMemoria(),
        AHORA,
    )


def preparar():
    ana = usuario()
    return ana, RepositorioCuentaEnMemoria(ana), RepositorioIntentosEnMemoria(), HasheadorFalso()


def test_exportar_entrega_los_datos_de_la_persona():
    ana, cuentas, _, _ = preparar()
    datos = exportar_datos(ana.id, cuentas, RepositorioEnMemoria(), AHORA)
    assert datos.usuario.email == "ana@correo.cl"
    assert datos.movimientos == []
    assert datos.exportado_en == AHORA


def test_exportar_cuenta_inexistente_falla():
    _, cuentas, _, _ = preparar()
    with pytest.raises(CredencialesInvalidas):
        exportar_datos(uuid4(), cuentas, RepositorioEnMemoria())


def test_cambiar_contrasena_guarda_la_nueva_y_cierra_sesiones():
    ana, cuentas, intentos, hasheador = preparar()
    tokens = RepositorioTokensEnMemoria()
    _, token = nuevo_token_refresco(ana.id, AHORA)
    tokens.guardar(token)
    cambiar_clave(ana, cuentas, intentos, hasheador, "Clave1234", "Otra56789", tokens)
    assert cuentas.usuarios[ana.id].hash_contrasena == "hash:Otra56789"
    assert tokens.tokens[token.id].revocado_en == AHORA


def test_cambiar_contrasena_con_la_actual_incorrecta_no_cambia_nada():
    ana, cuentas, intentos, hasheador = preparar()
    with pytest.raises(CredencialesInvalidas):
        cambiar_clave(ana, cuentas, intentos, hasheador, "mala", "Otra56789")
    assert cuentas.usuarios[ana.id].hash_contrasena == "hash:Clave1234"


def test_la_contrasena_nueva_debe_cumplir_los_requisitos():
    ana, cuentas, intentos, hasheador = preparar()
    with pytest.raises(ContrasenaInvalida):
        cambiar_clave(ana, cuentas, intentos, hasheador, "Clave1234", "corta")


def test_la_contrasena_nueva_debe_ser_distinta():
    ana, cuentas, intentos, hasheador = preparar()
    with pytest.raises(ContrasenaInvalida):
        cambiar_clave(ana, cuentas, intentos, hasheador, "Clave1234", "Clave1234")


def test_equivocarse_muchas_veces_bloquea_la_confirmacion():
    ana, cuentas, intentos, hasheador = preparar()
    for i in range(5):
        with pytest.raises((CredencialesInvalidas, DemasiadosIntentos)):
            instante = AHORA + timedelta(seconds=i)
            eliminar_cuenta(ana.id, "mala", cuentas, hasheador, intentos, instante)
    instante = AHORA + timedelta(seconds=9)
    with pytest.raises(DemasiadosIntentos):
        eliminar_cuenta(ana.id, "Clave1234", cuentas, hasheador, intentos, instante)
    assert ana.id in cuentas.usuarios


def test_cambiar_email_normaliza_y_guarda():
    ana, cuentas, intentos, hasheador = preparar()
    nuevo = cambiar_email(
        ana.id, "Clave1234", "  Ana.Nueva@Correo.CL ", cuentas, hasheador, intentos, AHORA
    )
    assert nuevo == "ana.nueva@correo.cl"
    assert cuentas.usuarios[ana.id].email == "ana.nueva@correo.cl"


def test_cambiar_email_a_uno_ocupado_falla():
    ana, cuentas, intentos, hasheador = preparar()
    luis = usuario("luis@correo.cl")
    cuentas.usuarios[luis.id] = luis
    with pytest.raises(EmailYaRegistrado):
        cambiar_email(ana.id, "Clave1234", "luis@correo.cl", cuentas, hasheador, intentos, AHORA)


def test_cambiar_email_invalido_falla():
    ana, cuentas, intentos, hasheador = preparar()
    with pytest.raises(EmailInvalido):
        cambiar_email(ana.id, "Clave1234", "esto-no-es-email", cuentas, hasheador, intentos, AHORA)


def test_cambiar_email_pide_la_contrasena():
    ana, cuentas, intentos, hasheador = preparar()
    with pytest.raises(CredencialesInvalidas):
        cambiar_email(ana.id, "mala", "otro@correo.cl", cuentas, hasheador, intentos, AHORA)
    assert cuentas.usuarios[ana.id].email == "ana@correo.cl"


def test_eliminar_cuenta_borra_y_olvida_los_intentos():
    ana, cuentas, intentos, hasheador = preparar()
    eliminar_cuenta(ana.id, "Clave1234", cuentas, hasheador, intentos, AHORA)
    assert ana.id not in cuentas.usuarios
    assert cuentas.claves_borradas == [clave_de("ana@correo.cl")]


def test_eliminar_con_contrasena_incorrecta_no_borra():
    ana, cuentas, intentos, hasheador = preparar()
    with pytest.raises(CredencialesInvalidas):
        eliminar_cuenta(ana.id, "mala", cuentas, hasheador, intentos, AHORA)
    assert ana.id in cuentas.usuarios
