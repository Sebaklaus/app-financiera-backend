"""Crea el par de llaves RSA con el que se firman los tokens.

Uso (una sola vez, desde la raíz del proyecto):  python -m app.infraestructura.generar_claves
Deja dos archivos en la carpeta claves/. La privada firma, la pública solo verifica.
La carpeta claves/ está en .gitignore: jamás se sube a GitHub.
"""

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generar_par() -> tuple[str, str]:
    """Devuelve (clave_privada, clave_publica) en formato PEM (texto)."""
    privada = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem_privada = privada.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    pem_publica = (
        privada.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("ascii")
    )
    return pem_privada, pem_publica


def main() -> None:
    carpeta = Path("claves")
    carpeta.mkdir(exist_ok=True)
    destino_privada = carpeta / "jwt_privada.pem"
    destino_publica = carpeta / "jwt_publica.pem"
    if destino_privada.exists():
        print("Ya existen claves; no las toco. Borra la carpeta claves/ si quieres nuevas.")
        return
    privada, publica = generar_par()
    destino_privada.write_text(privada, encoding="ascii")
    destino_publica.write_text(publica, encoding="ascii")
    print("Claves creadas en claves/ (no las subas a GitHub).")


if __name__ == "__main__":
    main()
