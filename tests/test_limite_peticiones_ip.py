from datetime import datetime, timedelta, timezone

import pytest

from app.casos_de_uso.limite_por_ip import (
    ACCION_LOGIN,
    ACCION_RECUPERACION,
    ACCION_REGISTRO,
    clave_de_ip,
    limitar_peticiones_ip,
)
from app.dominio.errores import DemasiadosIntentos
from tests.dobles import RepositorioIntentosEnMemoria

AHORA = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)


def test_cada_accion_tiene_su_propia_clave():
    acciones = (ACCION_LOGIN, ACCION_REGISTRO, ACCION_RECUPERACION)
    claves = {clave_de_ip("1.2.3.4", a) for a in acciones}
    assert len(claves) == 3


def test_deja_pasar_hasta_el_tope_y_luego_bloquea():
    intentos = RepositorioIntentosEnMemoria()
    for i in range(3):  # tope de 3: la tercera petición activa el bloqueo, la cuarta se rechaza
        limitar_peticiones_ip("1.2.3.4", "prueba", 3, intentos, AHORA + timedelta(seconds=i))
    with pytest.raises(DemasiadosIntentos):
        limitar_peticiones_ip("1.2.3.4", "prueba", 3, intentos, AHORA + timedelta(seconds=10))


def test_otra_ip_u_otra_accion_no_se_ven_afectadas():
    intentos = RepositorioIntentosEnMemoria()
    for i in range(3):
        limitar_peticiones_ip("1.2.3.4", "prueba", 3, intentos, AHORA + timedelta(seconds=i))
    limitar_peticiones_ip("5.6.7.8", "prueba", 3, intentos, AHORA + timedelta(seconds=10))
    limitar_peticiones_ip("1.2.3.4", "otra", 3, intentos, AHORA + timedelta(seconds=10))


def test_el_bloqueo_termina_solo():
    intentos = RepositorioIntentosEnMemoria()
    for i in range(3):
        limitar_peticiones_ip("1.2.3.4", "prueba", 3, intentos, AHORA + timedelta(seconds=i))
    limitar_peticiones_ip("1.2.3.4", "prueba", 3, intentos, AHORA + timedelta(minutes=16))
