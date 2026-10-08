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


class MovimientoInvalido(ErrorDeDominio):
    """Un ingreso o gasto con datos que no cumplen las reglas (monto, fecha, texto...)."""
