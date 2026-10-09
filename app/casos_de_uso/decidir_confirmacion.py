"""Caso de uso: la persona confirma o rechaza una propuesta de reparto (RNF-06)."""

from datetime import datetime, timezone
from uuid import UUID

from app.casos_de_uso.puertos import RepositorioMovimientos
from app.dominio.confirmacion import Confirmacion, Decision, decidir
from app.dominio.errores import ConfirmacionNoEncontrada


def decidir_confirmacion(
    usuario_id: UUID,
    confirmacion_id: UUID,
    decision: Decision,
    repositorio: RepositorioMovimientos,
    ahora: datetime | None = None,
) -> Confirmacion:
    confirmacion = repositorio.buscar_confirmacion(usuario_id, confirmacion_id)
    if confirmacion is None:
        # Misma respuesta si no existe o si es de otra persona: no se revela cuál.
        raise ConfirmacionNoEncontrada("No existe esa propuesta")
    decidida = decidir(confirmacion, decision, ahora or datetime.now(timezone.utc))
    repositorio.actualizar_confirmacion(decidida)
    return decidida
