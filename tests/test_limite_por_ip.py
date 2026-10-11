from datetime import datetime, timedelta, timezone

import pytest

from app.casos_de_uso.limite_por_ip import (
    MAX_FALLOS_POR_IP,
    clave_de_ip,
    registrar_fallo_ip,
    verificar_ip,
)
from app.dominio.bloqueo import MAX_INTENTOS, clave_de
from app.dominio.errores import DemasiadosIntentos
from tests.dobles import RepositorioIntentosEnMemoria

AHORA = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)


def test_la_ip_no_se_guarda_en_claro():
    assert "203.0.113.7" not in clave_de_ip("203.0.113.7")
    assert len(clave_de_ip("203.0.113.7")) == 64


def test_la_clave_de_ip_no_choca_con_la_de_un_email():
    assert clave_de_ip("ana@correo.cl") != clave_de("ana@correo.cl")


def test_tope_mas_alto_que_el_de_un_email():
    assert MAX_FALLOS_POR_IP > MAX_INTENTOS


def test_bloquea_al_llegar_al_tope():
    intentos = RepositorioIntentosEnMemoria()
    for i in range(MAX_FALLOS_POR_IP - 1):
        registrar_fallo_ip("1.2.3.4", intentos, AHORA + timedelta(seconds=i))
    verificar_ip("1.2.3.4", intentos, AHORA + timedelta(minutes=1))  # aún no bloquea
    registrar_fallo_ip("1.2.3.4", intentos, AHORA + timedelta(minutes=1))
    with pytest.raises(DemasiadosIntentos):
        verificar_ip("1.2.3.4", intentos, AHORA + timedelta(minutes=2))


def test_otra_ip_no_se_ve_afectada():
    intentos = RepositorioIntentosEnMemoria()
    for i in range(MAX_FALLOS_POR_IP):
        registrar_fallo_ip("1.2.3.4", intentos, AHORA + timedelta(seconds=i))
    verificar_ip("5.6.7.8", intentos, AHORA + timedelta(minutes=2))


def test_el_bloqueo_termina_solo():
    intentos = RepositorioIntentosEnMemoria()
    for i in range(MAX_FALLOS_POR_IP):
        registrar_fallo_ip("1.2.3.4", intentos, AHORA + timedelta(seconds=i))
    verificar_ip("1.2.3.4", intentos, AHORA + timedelta(minutes=16))
