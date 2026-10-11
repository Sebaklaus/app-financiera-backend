"""Los secretos nunca viajan en la URL (las URL quedan en registros de servidores y navegadores).

Revisa TODAS las rutas de la app, leyendo su documentación OpenAPI: ninguna puede pedir
contraseñas ni tokens como parámetro de la dirección. Deben ir en el cuerpo de la petición o en
la cabecera Authorization.
"""

from app.main import app

PROHIBIDOS = ("token", "contrasena", "password", "clave", "secret", "refresh")


def test_ninguna_ruta_recibe_secretos_por_la_url():
    rutas = app.openapi()["paths"]
    assert len(rutas) > 10, "La prueba no encontró las rutas: no estaría revisando nada"
    for ruta, metodos in rutas.items():
        for metodo, detalle in metodos.items():
            for parametro in detalle.get("parameters", []):
                nombre = parametro["name"].lower()
                if parametro["in"] in ("query", "path"):
                    assert not any(p in nombre for p in PROHIBIDOS), f"{metodo} {ruta}: {nombre}"
