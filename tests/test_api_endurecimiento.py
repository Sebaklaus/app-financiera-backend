"""Salud, cabeceras y límites por IP a través de la app de prueba."""

from app.casos_de_uso.limite_por_ip import MAX_RECUPERACIONES_POR_IP, MAX_REGISTROS_POR_IP
from tests.apoyo_api import crear_cliente


def test_salud_listo_responde_cuando_hay_base():
    r = crear_cliente().get("/salud/listo")
    assert r.status_code == 200
    assert r.json() == {"estado": "listo"}


def test_las_respuestas_llevan_cabeceras_de_seguridad():
    h = crear_cliente().get("/salud/listo").headers
    assert h["x-content-type-options"] == "nosniff"
    assert h["cache-control"] == "no-store"


def test_registrar_cuentas_en_masa_desde_una_ip_da_429():
    cliente = crear_cliente()
    codigos = [
        cliente.post(
            "/registro", json={"email": f"persona{i}@correo.cl", "contrasena": "Clave1234"}
        ).status_code
        for i in range(MAX_REGISTROS_POR_IP + 1)
    ]
    assert codigos[:MAX_REGISTROS_POR_IP] == [201] * MAX_REGISTROS_POR_IP
    assert codigos[-1] == 429


def test_pedir_muchos_correos_de_recuperacion_desde_una_ip_da_429():
    cliente = crear_cliente()
    codigos = [
        cliente.post("/recuperacion/solicitar", json={"email": f"p{i}@correo.cl"}).status_code
        for i in range(MAX_RECUPERACIONES_POR_IP + 1)
    ]
    assert codigos[:MAX_RECUPERACIONES_POR_IP] == [202] * MAX_RECUPERACIONES_POR_IP
    r = cliente.post("/recuperacion/solicitar", json={"email": "otra@correo.cl"})
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) > 0
