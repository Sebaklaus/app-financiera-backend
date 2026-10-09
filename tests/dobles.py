"""Dobles de prueba compartidos: un repositorio de movimientos que vive en memoria."""

from dataclasses import replace
from datetime import datetime
from uuid import UUID

from app.dominio.confirmacion import Confirmacion, EstadoConfirmacion
from app.dominio.errores import ConfirmacionYaDecidida
from app.dominio.movimiento import Movimiento
from app.dominio.token_refresco import TokenRefresco


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

    def buscar_movimiento(self, usuario_id: UUID, movimiento_id: UUID) -> Movimiento | None:
        for m in self.movimientos:
            if m.id == movimiento_id and m.usuario_id == usuario_id:
                return m
        return None

    def actualizar_movimiento(
        self, movimiento: Movimiento, propuestas: list[Confirmacion] | None = None
    ) -> None:
        self.movimientos = [movimiento if m.id == movimiento.id else m for m in self.movimientos]
        if propuestas is not None:
            self.confirmaciones = {
                k: c
                for k, c in self.confirmaciones.items()
                if not (c.ingreso_id == movimiento.id and c.estado is EstadoConfirmacion.PENDIENTE)
            }
            for c in propuestas:
                self.confirmaciones[c.id] = c

    def eliminar_movimiento(self, usuario_id: UUID, movimiento_id: UUID) -> bool:
        if self.buscar_movimiento(usuario_id, movimiento_id) is None:
            return False
        self.movimientos = [m for m in self.movimientos if m.id != movimiento_id]
        self.confirmaciones = {
            k: c for k, c in self.confirmaciones.items() if c.ingreso_id != movimiento_id
        }
        return True


class RepositorioTokensEnMemoria:
    def __init__(self) -> None:
        self.tokens: dict[UUID, TokenRefresco] = {}

    def guardar(self, token: TokenRefresco) -> None:
        self.tokens[token.id] = token

    def buscar_por_huella(self, huella: str) -> TokenRefresco | None:
        return next((t for t in self.tokens.values() if t.huella == huella), None)

    def revocar(self, token_id: UUID, ahora: datetime) -> bool:
        actual = self.tokens[token_id]
        if actual.revocado_en is not None:
            return False
        self.tokens[token_id] = replace(actual, revocado_en=ahora)
        return True

    def revocar_todos_de_usuario(self, usuario_id: UUID, ahora: datetime) -> None:
        for token_id, token in list(self.tokens.items()):
            if token.usuario_id == usuario_id and token.revocado_en is None:
                self.tokens[token_id] = replace(token, revocado_en=ahora)


class EmisorFalso:
    """Emisor de tokens de acceso que no firma nada: basta para probar la lógica."""

    segundos_de_vida = 900

    def emitir(self, usuario_id: UUID) -> str:
        return f"acceso-{usuario_id}"

    def leer(self, token: str) -> UUID:
        return UUID(token.removeprefix("acceso-"))
