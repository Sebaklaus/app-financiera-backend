"""Prueba el repositorio contra SQLite en memoria: misma lógica SQL, sin instalar nada."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.casos_de_uso.registrar_usuario import registrar_usuario
from app.dominio.errores import EmailYaRegistrado
from app.dominio.usuario import Usuario
from app.infraestructura.base_de_datos import (
    crear_fabrica_sesiones,
    crear_motor,
    crear_tablas,
)
from app.infraestructura.hasheador_bcrypt import HasheadorBcrypt
from app.infraestructura.repositorio_usuarios_sql import RepositorioUsuariosSQL


@pytest.fixture
def sesion():
    motor = crear_motor("sqlite+pysqlite:///:memory:")
    crear_tablas(motor)
    with crear_fabrica_sesiones(motor)() as s:
        yield s


def un_usuario(email="ana@correo.cl") -> Usuario:
    return Usuario(
        id=uuid4(),
        email=email,
        hash_contrasena="hash-de-prueba",
        creado_en=datetime.now(timezone.utc),
    )


def test_guardar_y_buscar(sesion):
    repo = RepositorioUsuariosSQL(sesion)
    usuario = un_usuario()
    repo.guardar(usuario)
    encontrado = repo.buscar_por_email("ana@correo.cl")
    assert encontrado is not None
    assert encontrado.id == usuario.id
    assert encontrado.hash_contrasena == "hash-de-prueba"


def test_buscar_un_email_que_no_existe(sesion):
    assert RepositorioUsuariosSQL(sesion).buscar_por_email("nadie@correo.cl") is None


def test_la_base_impide_dos_usuarios_con_el_mismo_email(sesion):
    repo = RepositorioUsuariosSQL(sesion)
    repo.guardar(un_usuario("ana@correo.cl"))
    with pytest.raises(EmailYaRegistrado):
        repo.guardar(un_usuario("ana@correo.cl"))


def test_registro_completo_con_base_y_bcrypt_reales(sesion):
    repo = RepositorioUsuariosSQL(sesion)
    hasheador = HasheadorBcrypt(costo=4)
    usuario = registrar_usuario("Ana@Correo.cl", "Clave1234", repo, hasheador)
    guardado = repo.buscar_por_email("ana@correo.cl")
    assert guardado is not None and guardado.id == usuario.id
    assert hasheador.verificar("Clave1234", guardado.hash_contrasena)
