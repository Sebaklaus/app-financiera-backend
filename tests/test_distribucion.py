from app.dominio.distribucion import Distribucion, distribuir


def _lanza(excepcion, valor) -> bool:
    try:
        distribuir(valor)
    except excepcion:
        return True
    return False


def test_monto_exacto():
    assert distribuir(100_000) == Distribucion(50_000, 25_000, 15_000, 10_000)


def test_sobrante_va_a_necesidades():
    d = distribuir(100_001)
    assert d == Distribucion(50_001, 25_000, 15_000, 10_000)


def test_monto_minimo():
    assert distribuir(1) == Distribucion(1, 0, 0, 0)


def test_la_suma_siempre_es_el_monto():
    montos = list(range(1, 20_001)) + [999_999, 1_234_567, 1_000_000_000]
    for monto in montos:
        assert distribuir(monto).total == monto


def test_ninguna_parte_es_negativa_y_necesidades_es_la_mayor():
    for monto in range(1, 5_001):
        d = distribuir(monto)
        assert min(d.inversion, d.estabilidad, d.entretenimiento, d.necesidades) >= 0
        assert d.necesidades >= max(d.inversion, d.estabilidad, d.entretenimiento)


def test_necesidades_se_pasa_del_50_por_menos_de_3_pesos():
    for monto in range(1, 5_001):
        d = distribuir(monto)
        # 2 * necesidades - monto es el exceso sobre el 50 % exacto, multiplicado por 2
        assert 0 <= 2 * d.necesidades - monto < 6


def test_rechaza_montos_invalidos():
    assert _lanza(ValueError, 0)
    assert _lanza(ValueError, -500)
    assert _lanza(TypeError, 1000.5)
    assert _lanza(TypeError, "1000")
    assert _lanza(TypeError, True)
