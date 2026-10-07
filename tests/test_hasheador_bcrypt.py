from app.infraestructura.hasheador_bcrypt import HasheadorBcrypt

# Costo 4 es el mínimo de bcrypt: las pruebas corren rápido. En producción es 12.
hasheador = HasheadorBcrypt(costo=4)


def test_la_huella_no_es_la_contrasena():
    huella = hasheador.hashear("Clave1234")
    assert huella != "Clave1234"
    assert "Clave1234" not in huella


def test_verificar_acepta_la_clave_correcta_y_rechaza_otra():
    huella = hasheador.hashear("Clave1234")
    assert hasheador.verificar("Clave1234", huella) is True
    assert hasheador.verificar("OtraClave99", huella) is False


def test_la_misma_clave_da_huellas_distintas_por_la_sal():
    assert hasheador.hashear("Clave1234") != hasheador.hashear("Clave1234")


def test_acepta_tildes_y_enes():
    huella = hasheador.hashear("Contraseña1ñ")
    assert hasheador.verificar("Contraseña1ñ", huella) is True
