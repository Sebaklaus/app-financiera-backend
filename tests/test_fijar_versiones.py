"""Pruebas del script que fija las versiones de requirements.txt."""

import pytest

from herramientas.fijar_versiones import LibreriaNoInstalada, fijar, version_instalada

VERSIONES = {"fastapi": "0.115.0", "psycopg": "3.2.1", "PyJWT": "2.9.0", "pytest": "8.3.2"}


def buscar(nombre):
    return VERSIONES[nombre]


def test_una_libreria_sin_version_queda_fijada():
    assert fijar(["fastapi"], buscar) == ["fastapi==0.115.0"]


def test_se_reemplaza_un_rango_por_la_version_exacta():
    assert fijar(["fastapi>=0.100", "pytest~=8.0"], buscar) == [
        "fastapi==0.115.0",
        "pytest==8.3.2",
    ]


def test_se_conservan_los_extras():
    assert fijar(["psycopg[binary]", "PyJWT[crypto]>=2"], buscar) == [
        "psycopg[binary]==3.2.1",
        "PyJWT[crypto]==2.9.0",
    ]


def test_comentarios_lineas_vacias_y_opciones_no_se_tocan():
    entrada = ["# dependencias", "", "-r otro.txt", "--index-url https://x.cl", "fastapi"]
    assert fijar(entrada, buscar) == [
        "# dependencias",
        "",
        "-r otro.txt",
        "--index-url https://x.cl",
        "fastapi==0.115.0",
    ]


def test_un_comentario_al_final_de_la_linea_se_conserva():
    assert fijar(["pytest  # para pruebas"], buscar) == ["pytest==8.3.2  # para pruebas"]


def test_ejecutarlo_dos_veces_da_lo_mismo():
    primera = fijar(["fastapi>=0.100", "psycopg[binary]"], buscar)
    assert fijar(primera, buscar) == primera


def test_una_libreria_no_instalada_se_avisa():
    with pytest.raises(LibreriaNoInstalada):
        version_instalada("libreria-que-no-existe-xyz")


def test_una_libreria_instalada_devuelve_su_version():
    assert version_instalada("pytest")[0].isdigit()
