from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.dominio.auditoria import TipoEvento
from app.infraestructura.modelos import Base
from app.infraestructura.repositorio_eventos_sql import EventoSeguridadTabla
from herramientas.metricas_seguridad import calcular

AHORA = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)


def _evento(tipo, creado_en):
    return EventoSeguridadTabla(
        id=uuid4(), tipo=tipo.value, usuario_id=None, ip_huella=None, creado_en=creado_en
    )


def test_cuenta_los_eventos_de_las_ultimas_24_horas_por_tipo():
    motor = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(motor)
    with sessionmaker(motor)() as s:
        s.add_all(
            [
                _evento(TipoEvento.LOGIN_FALLIDO, AHORA - timedelta(hours=1)),
                _evento(TipoEvento.LOGIN_FALLIDO, AHORA - timedelta(hours=5)),
                _evento(TipoEvento.LOGIN_FALLIDO, AHORA - timedelta(hours=30)),  # fuera de rango
                _evento(TipoEvento.REFRESCO_REUTILIZADO, AHORA - timedelta(hours=2)),
            ]
        )
        s.commit()
        m = calcular(s, AHORA)
    assert m["eventos_24h_login_fallido"] == 2
    assert m["eventos_24h_refresco_reutilizado"] == 1
    assert m["eventos_24h_login_exitoso"] == 0
    assert all(f"eventos_24h_{t.value}" in m for t in TipoEvento)
