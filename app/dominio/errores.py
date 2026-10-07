"""Errores de negocio. Son del dominio: no saben nada de HTTP ni de la base de datos."""


class ErrorDeDominio(Exception):
    """Base de los errores que el negocio sabe explicar."""


class EmailInvalido(ErrorDeDominio):
    pass


class ContrasenaInvalida(ErrorDeDominio):
    """El mensaje dice qué requisito falta, para poder mostrárselo al usuario."""


class EmailYaRegistrado(ErrorDeDominio):
    pass
