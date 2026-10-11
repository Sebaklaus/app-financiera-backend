"""El límite por IP a través de POST /login, con SQLite en memoria."""

from app.casos_de_uso.limite_por_ip import MAX_FALLOS_POR_IP
from tests.apoyo_api import crear_cliente

CLAVE = "Clave1234"


def test_probar_muchas_cuentas_distintas_bloquea_a_esa_ip():
    cliente = crear_cliente()
    cliente.post("/registro", json={"email": "ana@correo.cl", "contrasena": CLAVE})
    codigos = [
        cliente.post(
            "/login", json={"email": f"persona{i}@correo.cl", "contrasena": "Equivocada99"}
        ).status_code
        for i in range(MAX_FALLOS_POR_IP)
    ]
    assert set(codigos) == {401}  # ningún email llegó a su propio tope de 5
    r = cliente.post("/login", json={"email": "ana@correo.cl", "contrasena": CLAVE})
    assert r.status_code == 429
    assert int(r.headers["retry-after"]) > 0


def test_un_login_correcto_no_cuenta_como_fallo():
    cliente = crear_cliente()
    datos = {"email": "ana@correo.cl", "contrasena": CLAVE}
    cliente.post("/registro", json=datos)
    for _ in range(MAX_FALLOS_POR_IP + 5):
        assert cliente.post("/login", json=datos).status_code == 200
