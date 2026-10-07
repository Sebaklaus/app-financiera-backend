"""Convierte contraseñas en huellas con bcrypt (cumple el puerto HasheadorContrasenas)."""

import bcrypt


class HasheadorBcrypt:
    def __init__(self, costo: int = 12) -> None:
        # El informe fija factor de coste 12. Las pruebas usan uno más bajo para ir rápido.
        self._costo = costo

    def hashear(self, contrasena: str) -> str:
        sal = bcrypt.gensalt(rounds=self._costo)
        return bcrypt.hashpw(contrasena.encode("utf-8"), sal).decode("ascii")

    def verificar(self, contrasena: str, hash_guardado: str) -> bool:
        """Se usará en el inicio de sesión: compara una clave con la huella guardada."""
        return bcrypt.checkpw(contrasena.encode("utf-8"), hash_guardado.encode("ascii"))
