"""Cifra y descifra textos con una clave que vive en el entorno (nunca en el código).

Se usa para el enlace bancario: si alguien copiara la base de datos, vería texto ilegible.
Generar una clave (una sola vez, y guardarla en .env como FINTOC_CLAVE_CIFRADO):

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from cryptography.fernet import Fernet


class CifradorFernet:
    def __init__(self, clave: str) -> None:
        self._fernet = Fernet(clave.encode("ascii"))

    def cifrar(self, texto: str) -> str:
        return self._fernet.encrypt(texto.encode("utf-8")).decode("ascii")

    def descifrar(self, cifrado: str) -> str:
        return self._fernet.decrypt(cifrado.encode("ascii")).decode("utf-8")
