"""La bitácora a través de la API: lo que la persona ve en /yo/actividad."""

import pytest

from tests.apoyo_api import crear_cliente

CLAVE = "Clave1234"
DATOS = {"email": "ana@correo.cl", "contrasena": CLAVE}


@pytest.fixture
def cliente():
    c = crear_cliente()
    c.post("/registro", json=DATOS)
    return c


def entrar(cliente):
    sesion = cliente.post("/login", json=DATOS).json()
    return {"Authorization": f"Bearer {sesion['access_token']}"}, sesion["refresh_token"]


def tipos(cliente, cabecera):
    r = cliente.get("/yo/actividad", headers=cabecera)
    assert r.status_code == 200
    return [e["tipo"] for e in r.json()]


def test_la_ruta_exige_token(cliente):
    assert cliente.get("/yo/actividad").status_code == 401


def test_el_login_exitoso_queda_anotado_con_fecha_utc(cliente):
    cabecera, _ = entrar(cliente)
    cuerpo = cliente.get("/yo/actividad", headers=cabecera).json()
    assert [e["tipo"] for e in cuerpo] == ["login_exitoso"]
    assert cuerpo[0]["fecha"].endswith("Z")


def test_un_login_fallido_no_aparece_en_la_actividad_de_nadie(cliente):
    cliente.post("/login", json={**DATOS, "contrasena": "Equivocada99"})
    cabecera, _ = entrar(cliente)
    assert tipos(cliente, cabecera) == ["login_exitoso"]


def test_cambiar_la_contrasena_queda_anotado(cliente):
    cabecera, _ = entrar(cliente)
    cuerpo = {"contrasena_actual": CLAVE, "contrasena_nueva": "Nueva56789"}
    assert cliente.post("/yo/contrasena", json=cuerpo, headers=cabecera).status_code == 204
    assert tipos(cliente, cabecera)[0] == "contrasena_cambiada"


def test_cambiar_el_email_queda_anotado(cliente):
    cabecera, _ = entrar(cliente)
    cuerpo = {"contrasena": CLAVE, "email_nuevo": "nuevo@correo.cl"}
    assert cliente.patch("/yo/email", json=cuerpo, headers=cabecera).status_code == 200
    assert tipos(cliente, cabecera)[0] == "email_cambiado"


def test_equivocarse_al_confirmar_queda_anotado(cliente):
    cabecera, _ = entrar(cliente)
    r = cliente.post("/yo/eliminar", json={"contrasena": "mala"}, headers=cabecera)
    assert r.status_code == 403
    assert tipos(cliente, cabecera)[0] == "reautenticacion_fallida"


def test_reusar_un_token_de_refresco_queda_anotado(cliente):
    cabecera, refresco = entrar(cliente)
    cliente.post("/refrescar", json={"refresh_token": refresco})
    r = cliente.post("/refrescar", json={"refresh_token": refresco})  # reuso
    assert r.status_code == 401
    assert "refresco_reutilizado" in tipos(cliente, cabecera)


def test_cerrar_todas_las_sesiones_queda_anotado(cliente):
    cabecera, _ = entrar(cliente)
    cliente.post("/logout/todas", headers=cabecera)
    assert tipos(cliente, cabecera)[0] == "sesiones_cerradas"


def test_la_recuperacion_de_contrasena_queda_anotada(cliente):
    cliente.post("/recuperacion/solicitar", json={"email": "ana@correo.cl"})
    token = cliente.espia.enviados[-1][1]
    cuerpo = {"token": token, "contrasena_nueva": "Nueva56789"}
    assert cliente.post("/recuperacion/restablecer", json=cuerpo).status_code == 204
    nuevo = {"email": "ana@correo.cl", "contrasena": "Nueva56789"}
    sesion = cliente.post("/login", json=nuevo).json()
    cabecera = {"Authorization": f"Bearer {sesion['access_token']}"}
    anotados = tipos(cliente, cabecera)
    assert "recuperacion_solicitada" in anotados
    assert "recuperacion_completada" in anotados


def test_el_limite_de_la_lista_se_valida(cliente):
    cabecera, _ = entrar(cliente)
    assert cliente.get("/yo/actividad?limite=0", headers=cabecera).status_code == 422
    assert cliente.get("/yo/actividad?limite=51", headers=cabecera).status_code == 422
    assert cliente.get("/yo/actividad?limite=1", headers=cabecera).status_code == 200


def test_cada_persona_ve_solo_su_actividad(cliente):
    cliente.post("/registro", json={"email": "luis@correo.cl", "contrasena": CLAVE})
    ana, _ = entrar(cliente)
    cliente.post("/login", json={"email": "luis@correo.cl", "contrasena": CLAVE})
    assert tipos(cliente, ana) == ["login_exitoso"]
