"""Puertos: lo que los casos de uso NECESITAN, descrito como contrato.

Los casos de uso piden "algo que sepa guardar usuarios" sin saber si es PostgreSQL o una
lista en memoria. Los adaptadores (capa de afuera) cumplen estos contratos.
"""

from typing import Protocol

from app.dominio.usuario import Usuario


class RepositorioUsuarios(Protocol):
    def buscar_por_email(self, email: str) -> Usuario | None: ...

    def guardar(self, usuario: Usuario) -> None: ...


class HasheadorContrasenas(Protocol):
    def hashear(self, contrasena: str) -> str: ...
