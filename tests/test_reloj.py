"""Pruebas de las fechas y horas con zona horaria."""

from datetime import date, datetime, timedelta, timezone

from app.dominio.reloj import a_utc, ahora_utc, hoy_en_chile


def test_de_noche_en_chile_aun_es_el_dia_anterior_que_en_utc():
    # 02:30 UTC del 10 de octubre = 23:30 del 9 de octubre en Chile (verano: UTC-3)
    ahora = datetime(2026, 10, 10, 2, 30, tzinfo=timezone.utc)
    assert ahora.date() == date(2026, 10, 10)
    assert hoy_en_chile(ahora) == date(2026, 10, 9)


def test_en_invierno_la_diferencia_es_de_cuatro_horas():
    # 02:30 UTC del 1 de julio = 22:30 del 30 de junio en Chile (invierno: UTC-4)
    ahora = datetime(2026, 7, 1, 2, 30, tzinfo=timezone.utc)
    assert hoy_en_chile(ahora) == date(2026, 6, 30)


def test_de_dia_ambas_fechas_coinciden():
    ahora = datetime(2026, 10, 10, 15, 0, tzinfo=timezone.utc)
    assert hoy_en_chile(ahora) == date(2026, 10, 10)


def test_el_limite_exacto_del_dia_en_chile():
    justo_antes = datetime(2026, 10, 10, 2, 59, tzinfo=timezone.utc)  # 23:59 en Chile
    justo_despues = datetime(2026, 10, 10, 3, 0, tzinfo=timezone.utc)  # 00:00 en Chile
    assert hoy_en_chile(justo_antes) == date(2026, 10, 9)
    assert hoy_en_chile(justo_despues) == date(2026, 10, 10)


def test_una_hora_con_otra_zona_se_interpreta_bien():
    chile = timezone(timedelta(hours=-3))
    ahora = datetime(2026, 10, 9, 23, 30, tzinfo=chile)  # es 02:30 UTC del día 10
    assert hoy_en_chile(ahora) == date(2026, 10, 9)


def test_a_utc_convierte_horas_con_zona():
    chile = timezone(timedelta(hours=-3))
    assert a_utc(datetime(2026, 10, 9, 22, 0, tzinfo=chile)) == datetime(
        2026, 10, 10, 1, 0, tzinfo=timezone.utc
    )


def test_a_utc_asume_utc_si_no_hay_zona():
    sin_zona = datetime(2026, 10, 10, 1, 0)
    assert a_utc(sin_zona) == datetime(2026, 10, 10, 1, 0, tzinfo=timezone.utc)
    assert a_utc(sin_zona).tzinfo is not None


def test_ahora_utc_trae_zona():
    assert ahora_utc().utcoffset() == timedelta(0)
