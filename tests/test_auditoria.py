"""Pruebas de la bitácora de seguridad, sin base de datos."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.casos_de_uso.auditoria import listar_actividad, registrar_evento
from app.casos_de_uso.sesiones import renovar_sesion
from app.dominio.auditoria import ReusoDeToken, TipoEvento, huella_ip
from app.dominio.errores import TokenInvalido
from app.dominio.token_refresco import nuevo_token_refresco
from tests.dobles import EmisorFalso, RepositorioTokensEnMemoria
from tests.dobles_auditoria import RepositorioEventosEnMemoria, RepositorioEventosRoto

AHORA = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
ANA = uuid4()
LUIS = uuid4()


def test_registrar_guarda_el_evento_con_la_huella_de_la_ip():
    repo = RepositorioEventosEnMemoria()
    registrar_evento(repo, TipoEvento.LOGIN_EXITOSO, ANA, "203.0.113.7", AHORA)
    evento = repo.eventos[0]
    assert evento.tipo is TipoEvento.LOGIN_EXITOSO
    assert evento.usuario_id == ANA
    assert evento.creado_en == AHORA
    assert "203.0.113.7" not in str(evento)
    assert evento.ip_huella == huella_ip("203.0.113.7")


def test_sin_ip_no_hay_huella():
    assert huella_ip(None) is None
    assert huella_ip("") is None


def test_si_la_bitacora_falla_no_se_rompe_la_operacion():
    registrar_evento(RepositorioEventosRoto(), TipoEvento.LOGIN_EXITOSO, ANA, "1.2.3.4")


def test_la_actividad_es_de_cada_persona_y_la_mas_reciente_primero():
    repo = RepositorioEventosEnMemoria()
    registrar_evento(repo, TipoEvento.LOGIN_EXITOSO, ANA, None, AHORA)
    registrar_evento(repo, TipoEvento.CONTRASENA_CAMBIADA, ANA, None, AHORA + timedelta(hours=1))
    registrar_evento(repo, TipoEvento.LOGIN_EXITOSO, LUIS, None, AHORA)
    tipos = [e.tipo for e in listar_actividad(ANA, repo)]
    assert tipos == [TipoEvento.CONTRASENA_CAMBIADA, TipoEvento.LOGIN_EXITOSO]


def test_la_actividad_respeta_el_limite():
    repo = RepositorioEventosEnMemoria()
    for i in range(5):
        registrar_evento(repo, TipoEvento.LOGIN_EXITOSO, ANA, None, AHORA + timedelta(minutes=i))
    assert len(listar_actividad(ANA, repo, 3)) == 3


def test_reusar_un_token_de_refresco_levanta_reuso_con_el_id_del_dueno():
    tokens = RepositorioTokensEnMemoria()
    token, registro = nuevo_token_refresco(ANA, AHORA)
    tokens.guardar(registro)
    renovar_sesion(token, tokens, EmisorFalso(), AHORA)  # primer uso: normal
    try:
        renovar_sesion(token, tokens, EmisorFalso(), AHORA)  # segundo uso: sospechoso
    except ReusoDeToken as error:
        assert error.usuario_id == ANA
        assert isinstance(error, TokenInvalido)  # el resto del código lo sigue tratando igual
    else:
        raise AssertionError("debía levantar ReusoDeToken")


def test_un_token_desconocido_sigue_siendo_token_invalido_sin_reuso():
    try:
        renovar_sesion("falso", RepositorioTokensEnMemoria(), EmisorFalso(), AHORA)
    except ReusoDeToken:
        raise AssertionError("un token inventado no es un reuso") from None
    except TokenInvalido:
        pass
