"""Pruebas de los tokens JWT. No necesitan base de datos ni servidor."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest

from app.dominio.errores import TokenInvalido
from app.infraestructura.emisor_jwt import ALGORITMO, EMISOR, EmisorJWT
from app.infraestructura.generar_claves import generar_par

PRIVADA, PUBLICA = generar_par()
OTRA_PRIVADA, OTRA_PUBLICA = generar_par()


def emisor(segundos_de_vida: int = 900) -> EmisorJWT:
    return EmisorJWT(PRIVADA, PUBLICA, segundos_de_vida)


def _datos_validos(ahora: datetime) -> dict:
    return {
        "sub": str(uuid4()),
        "iss": EMISOR,
        "iat": ahora,
        "exp": ahora + timedelta(hours=1),
    }


def test_un_token_emitido_se_puede_leer_de_vuelta():
    usuario_id = uuid4()
    token = emisor().emitir(usuario_id)
    assert emisor().leer(token) == usuario_id


def test_el_token_dura_15_minutos():
    token = emisor().emitir(uuid4())
    datos = jwt.decode(token, options={"verify_signature": False})
    assert datos["exp"] - datos["iat"] == 15 * 60


def test_el_token_solo_lleva_datos_minimos():
    token = emisor().emitir(uuid4())
    datos = jwt.decode(token, options={"verify_signature": False})
    assert set(datos) == {"sub", "iss", "iat", "exp"}


def test_un_token_vencido_se_rechaza():
    token = emisor(segundos_de_vida=-10).emitir(uuid4())
    with pytest.raises(TokenInvalido):
        emisor().leer(token)


def test_un_token_firmado_con_otra_clave_se_rechaza():
    token = EmisorJWT(OTRA_PRIVADA, OTRA_PUBLICA).emitir(uuid4())
    with pytest.raises(TokenInvalido):
        emisor().leer(token)


def test_un_token_alterado_se_rechaza():
    token = emisor().emitir(uuid4())
    cabecera, cuerpo, firma = token.split(".")
    cuerpo_alterado = cuerpo[:-2] + ("AA" if cuerpo[-2:] != "AA" else "BB")
    with pytest.raises(TokenInvalido):
        emisor().leer(f"{cabecera}.{cuerpo_alterado}.{firma}")


def test_un_token_sin_firma_algoritmo_none_se_rechaza():
    ahora = datetime.now(timezone.utc)
    datos = {**_datos_validos(ahora), "iss": EMISOR}
    token = jwt.encode(datos, None, algorithm="none")
    with pytest.raises(TokenInvalido):
        emisor().leer(token)


def test_un_token_de_otro_emisor_se_rechaza():
    ahora = datetime.now(timezone.utc)
    datos = {**_datos_validos(ahora), "iss": "otra-app"}
    token = jwt.encode(datos, PRIVADA, algorithm=ALGORITMO)
    with pytest.raises(TokenInvalido):
        emisor().leer(token)


def test_un_token_con_sub_que_no_es_uuid_se_rechaza():
    ahora = datetime.now(timezone.utc)
    datos = {**_datos_validos(ahora), "sub": "no-es-uuid"}
    token = jwt.encode(datos, PRIVADA, algorithm=ALGORITMO)
    with pytest.raises(TokenInvalido):
        emisor().leer(token)


@pytest.mark.parametrize("basura", ["", "abc", "a.b.c", "esto no es un token"])
def test_texto_que_no_es_un_token_se_rechaza(basura):
    with pytest.raises(TokenInvalido):
        emisor().leer(basura)
