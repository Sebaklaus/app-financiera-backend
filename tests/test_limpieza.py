from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.infraestructura.base_de_datos import UsuarioTabla
from app.infraestructura.modelos import Base
from app.infraestructura.repositorio_intentos_sql import IntentosLoginTabla
from app.infraestructura.repositorio_recuperacion_sql import TokenRecuperacionTabla
from app.infraestructura.repositorio_tokens_sql import TokenRefrescoTabla
from herramientas.limpieza import limpiar

AHORA = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
VIEJO = AHORA - timedelta(days=3)


def _sesion():
    motor = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(motor)
    return sessionmaker(motor)()


def _contar(sesion, tabla):
    return sesion.scalar(select(func.count()).select_from(tabla))


def _refresco(usuario_id, expira, revocado=None):
    return TokenRefrescoTabla(
        id=uuid4(),
        usuario_id=usuario_id,
        huella=uuid4().hex + uuid4().hex,
        creado_en=VIEJO,
        expira_en=expira,
        revocado_en=revocado,
    )


def _recuperacion(usuario_id, expira):
    return TokenRecuperacionTabla(
        id=uuid4(),
        usuario_id=usuario_id,
        huella=uuid4().hex + uuid4().hex,
        creado_en=VIEJO,
        expira_en=expira,
    )


def test_base_vacia_no_borra_nada():
    with _sesion() as s:
        assert set(limpiar(s, AHORA).values()) == {0}


def test_borra_lo_vencido_y_conserva_lo_demas():
    with _sesion() as s:
        u = UsuarioTabla(id=uuid4(), email="a@b.cl", hash_contrasena="x", creado_en=AHORA)
        s.add(u)
        s.flush()
        s.add_all(
            [
                _refresco(u.id, AHORA - timedelta(days=2)),  # vencido hace 2 días: se borra
                _refresco(u.id, AHORA - timedelta(hours=2)),  # vencido hace poco: se conserva
                _refresco(u.id, AHORA + timedelta(days=5), revocado=AHORA),  # revocado vigente
                _recuperacion(u.id, AHORA - timedelta(days=2)),  # se borra
                _recuperacion(u.id, AHORA + timedelta(minutes=10)),  # vigente: se conserva
                IntentosLoginTabla(clave="viejo", fallos=2, primer_fallo=VIEJO),  # se borra
                IntentosLoginTabla(clave="reciente", fallos=2, primer_fallo=AHORA),  # se conserva
                IntentosLoginTabla(
                    clave="bloqueo-terminado",
                    fallos=5,
                    primer_fallo=VIEJO,
                    bloqueado_hasta=AHORA - timedelta(minutes=1),
                ),  # se borra
                IntentosLoginTabla(
                    clave="bloqueado",
                    fallos=5,
                    primer_fallo=AHORA,
                    bloqueado_hasta=AHORA + timedelta(minutes=5),
                ),  # se conserva
            ]
        )
        s.commit()
        resultado = limpiar(s, AHORA)
        assert resultado == {
            "tokens_refresco_borrados": 1,
            "tokens_recuperacion_borrados": 1,
            "intentos_login_borrados": 2,
        }
        assert _contar(s, TokenRefrescoTabla) == 2
        assert _contar(s, TokenRecuperacionTabla) == 1
        claves = set(s.scalars(select(IntentosLoginTabla.clave)))
        assert claves == {"reciente", "bloqueado"}


def test_repetirla_no_hace_nada_mas():
    with _sesion() as s:
        s.add(IntentosLoginTabla(clave="viejo", fallos=1, primer_fallo=VIEJO))
        s.commit()
        assert limpiar(s, AHORA)["intentos_login_borrados"] == 1
        assert limpiar(s, AHORA)["intentos_login_borrados"] == 0
