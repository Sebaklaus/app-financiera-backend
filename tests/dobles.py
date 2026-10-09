"""Dobles de prueba compartidos: un repositorio de movimientos que vive en memoria."""

from uuid import UUID

from app.dominio.confirmacion import Confirmacion, EstadoConfirmacion
from app.dominio.errores import ConfirmacionYaDecidida
from app.dominio.movimiento import Movimiento


class RepositorioEnMemoria:
    def __init__(self) -> None:
        self.movimientos: list[Movimiento] = []
        self.confirmaciones: dict[UUID, Confirmacion] = {}

    def guardar(self, movimiento: Movimiento) -> None:
        self.movimientos.append(movimiento)

    def guardar_ingreso(self, ingreso: Movimiento, confirmaciones: list[Confirmacion]) -> None:
        self.movimientos.append(ingreso)
        for confirmacion in confirmaciones:
            self.confirmaciones[confirmacion.id] = confirmacion

    def listar_por_usuario(self, usuario_id: UUID) -> list[Movimiento]:
        propios = [m for m in self.movimientos if m.usuario_id == usuario_id]
        return sorted(propios, key=lambda m: m.fecha, reverse=True)

    def listar_confirmaciones_por_usuario(self, usuario_id: UUID) -> list[Confirmacion]:
        propias = [c for c in self.confirmaciones.values() if c.usuario_id == usuario_id]
        return sorted(propias, key=lambda c: c.creado_en, reverse=True)

    def buscar_confirmacion(self, usuario_id: UUID, confirmacion_id: UUID) -> Confirmacion | None:
        confirmacion = self.confirmaciones.get(confirmacion_id)
        if confirmacion is None or confirmacion.usuario_id != usuario_id:
            return None
        return confirmacion

    def actualizar_confirmacion(self, confirmacion: Confirmacion) -> None:
        actual = self.confirmaciones[confirmacion.id]
        if actual.estado is not EstadoConfirmacion.PENDIENTE:
            raise ConfirmacionYaDecidida("Esta propuesta ya fue decidida")
        self.confirmaciones[confirmacion.id] = confirmacion
