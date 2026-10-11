"""Lee la configuración desde el entorno (.env). Los secretos nunca viven en el código."""

import os

from dotenv import load_dotenv

load_dotenv()


def url_base_de_datos() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "Falta DATABASE_URL. Copia .env.example como .env y completa los valores."
        )
    return url


def origenes_cors() -> list[str]:
    """Direcciones web autorizadas a llamar a la API desde un navegador (CORS_ORIGINS).

    Van separadas por coma. Vacío = ninguna (lo más seguro; las apps móviles no lo necesitan).
    """
    return [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]
