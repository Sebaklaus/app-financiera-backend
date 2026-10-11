"""Métricas de seguridad: una foto de cómo está la defensa de la app en este momento.

Uso (desde la raíz, con el entorno activado):  python -m herramientas.metricas_seguridad
Solo cuenta filas: no muestra emails, contraseñas ni tokens.
"""

import json
import sys
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infraestructura.base_de_datos import UsuarioTabla
from app.infraestructura.repositorio_intentos_sql import IntentosLoginTabla
from app.infraestructura.repositorio_tokens_sql import TokenRefrescoTabla


def calcular(sesion: Session, ahora: datetime | None = None) -> dict[str, int]:
    ahora = ahora or datetime.now(timezone.utc)

    def contar(consulta) -> int:
        return int(sesion.scalar(consulta) or 0)

    return {
        "usuarios_registrados": contar(select(func.count()).select_from(UsuarioTabla)),
        "sesiones_activas": contar(
            select(func.count())
            .select_from(TokenRefrescoTabla)
            .where(TokenRefrescoTabla.revocado_en.is_(None), TokenRefrescoTabla.expira_en > ahora)
        ),
        "sesiones_revocadas": contar(
            select(func.count())
            .select_from(TokenRefrescoTabla)
            .where(TokenRefrescoTabla.revocado_en.is_not(None))
        ),
        "cuentas_bloqueadas_ahora": contar(
            select(func.count())
            .select_from(IntentosLoginTabla)
            .where(IntentosLoginTabla.bloqueado_hasta > ahora)
        ),
        "cuentas_con_fallos_recientes": contar(
            select(func.count())
            .select_from(IntentosLoginTabla)
            .where(IntentosLoginTabla.fallos > 0)
        ),
    }


def main() -> int:
    from app.configuracion import url_base_de_datos
    from app.infraestructura.base_de_datos import crear_fabrica_sesiones, crear_motor

    fabrica = crear_fabrica_sesiones(crear_motor(url_base_de_datos()))
    with fabrica() as sesion:
        print(json.dumps(calcular(sesion), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
