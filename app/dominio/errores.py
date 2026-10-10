"""Errores de negocio. Son del dominio: no saben nada de HTTP ni de la base de datos."""


class ErrorDeDominio(Exception):
    """Base de los errores que el negocio sabe explicar."""


class EmailInvalido(ErrorDeDominio):
    pass


class ContrasenaInvalida(ErrorDeDominio):
    """El mensaje dice qué requisito falta, para poder mostrárselo al usuario."""


class EmailYaRegistrado(ErrorDeDominio):
    pass


class CredencialesInvalidas(ErrorDeDominio):
    """Email o contraseña incorrectos. El mensaje es siempre el mismo, a propósito."""


class TokenInvalido(ErrorDeDominio):
    """El token de acceso no sirve: está vencido, alterado o no es nuestro."""


class DemasiadosIntentos(ErrorDeDominio):
    """Se superó el máximo de contraseñas incorrectas: hay que esperar para volver a intentar."""

    def __init__(self, segundos: int) -> None:
        self.segundos = segundos
        minutos = max(1, -(-segundos // 60))  # redondea hacia arriba
        super().__init__(
            f"Demasiados intentos fallidos. Intenta de nuevo en {minutos} "
            f"minuto{'s' if minutos != 1 else ''}"
        )


class MovimientoInvalido(ErrorDeDominio):
    """Un ingreso o gasto con datos que no cumplen las reglas (monto, fecha, texto...)."""


class ConfirmacionNoEncontrada(ErrorDeDominio):
    """No existe esa propuesta, o pertenece a otra persona (no se distingue a propósito)."""


class ConfirmacionYaDecidida(ErrorDeDominio):
    """La propuesta ya fue confirmada o rechazada; una decisión no se repite."""


class MovimientoNoEncontrado(ErrorDeDominio):
    """No existe ese movimiento, o pertenece a otra persona (no se distingue a propósito)."""


class EdicionNoPermitida(ErrorDeDominio):
    """El cambio contradice decisiones ya tomadas (p. ej. el monto de un ingreso repartido)."""
