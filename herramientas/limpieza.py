"""Limpieza de datos que ya no sirven (principio de minimización de la Ley 21.719).

Uso (desde la raíz, con el entorno activado):  python -m herramientas.limpieza
Se puede ejecutar a mano o agendar (por ejemplo, una vez al día con Cloud Scheduler).
Es seguro repetirlo: borrar lo que ya se borró no hace nada.

Qué borra:
- Tokens de refresco vencidos hace más de 1 día. Los revocados se conservan hasta que vencen,
  porque sirven para detectar que alguien reusa un token robado.
- Tokens de recuperación de contraseña vencidos hace más de 1 día.
- Registros de intentos de login que ya no bloquean ni cuentan: bloqueos terminados y fallos
  más viejos que la ventana de 15 minutos.
"""

import json
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, delete, or_
from sqlalchemy.orm import Session

from app.dominio.bloqueo import VENTANA
from app.infraestructura.repositorio_intentos_sql import IntentosLoginTabla
from app.infraestructura.repositorio_recuperacion_sql import TokenRecuperacionTabla
from app.infraestructura.repositorio_tokens_sql import TokenRefrescoTabla

GRACIA = timedelta(days=1)


def limpiar(sesion: Session, ahora: datetime | None = None) -> dict[str, int]:
    """Borra lo obsoleto, todo en una sola operación, y cuenta cuántas filas fueron."""
    ahora = ahora or datetime.now(timezone.utc)
    try:
        tokens = sesion.execute(
            delete(TokenRefrescoTabla).where(TokenRefrescoTabla.expira_en < ahora - GRACIA)
        ).rowcount
        recuperacion = sesion.execute(
            delete(TokenRecuperacionTabla).where(TokenRecuperacionTabla.expira_en < ahora - GRACIA)
        ).rowcount
        intentos = sesion.execute(
            delete(IntentosLoginTabla).where(
                or_(
                    and_(
                        IntentosLoginTabla.bloqueado_hasta.is_(None),
                        IntentosLoginTabla.primer_fallo < ahora - VENTANA,
                    ),
                    IntentosLoginTabla.bloqueado_hasta < ahora,
                )
            )
        ).rowcount
        sesion.commit()
    except Exception:
        sesion.rollback()
        raise
    return {
        "tokens_refresco_borrados": tokens,
        "tokens_recuperacion_borrados": recuperacion,
        "intentos_login_borrados": intentos,
    }


def main() -> int:
    from app.configuracion import url_base_de_datos
    from app.infraestructura.base_de_datos import crear_fabrica_sesiones, crear_motor

    fabrica = crear_fabrica_sesiones(crear_motor(url_base_de_datos()))
    with fabrica() as sesion:
        print(json.dumps(limpiar(sesion), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
