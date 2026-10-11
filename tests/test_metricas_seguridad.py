from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infraestructura.base_de_datos import UsuarioTabla
from app.infraestructura.modelos import Base
from app.infraestructura.repositorio_intentos_sql import IntentosLoginTabla
from app.infraestructura.repositorio_tokens_sql import TokenRefrescoTabla
from herramientas.metricas_seguridad import calcular

AHORA = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)


def _sesion():
    motor = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(motor)
    return sessionmaker(motor)()


def _token(usuario_id, expira, revocado=None) -> TokenRefrescoTabla:
    return TokenRefrescoTabla(
        id=uuid4(),
        usuario_id=usuario_id,
        huella=uuid4().hex + uuid4().hex,
        creado_en=AHORA - timedelta(days=1),
        expira_en=expira,
        revocado_en=revocado,
    )


def test_base_vacia_devuelve_ceros() -> None:
    with _sesion() as s:
        assert set(calcular(s, AHORA).values()) == {0}


def test_cuenta_sesiones_y_bloqueos() -> None:
    with _sesion() as s:
        u = UsuarioTabla(id=uuid4(), email="a@b.cl", hash_contrasena="x", creado_en=AHORA)
        s.add(u)
        s.flush()
        s.add_all(
            [
                _token(u.id, AHORA + timedelta(days=5)),  # activa
                _token(u.id, AHORA - timedelta(days=1)),  # vencida
                _token(u.id, AHORA + timedelta(days=5), revocado=AHORA),  # revocada
                IntentosLoginTabla(
                    clave="k1",
                    fallos=5,
                    primer_fallo=AHORA,
                    bloqueado_hasta=AHORA + timedelta(minutes=5),
                ),
                IntentosLoginTabla(clave="k2", fallos=2, primer_fallo=AHORA, bloqueado_hasta=None),
            ]
        )
        s.commit()
        m = calcular(s, AHORA)
    assert m["usuarios_registrados"] == 1
    assert m["sesiones_activas"] == 1
    assert m["sesiones_revocadas"] == 1
    assert m["cuentas_bloqueadas_ahora"] == 1
    assert m["cuentas_con_fallos_recientes"] == 2
