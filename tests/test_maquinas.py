"""Las maquinas del proyecto contra una respuesta calculada en Python.

Se prueban todas las cadenas hasta cierta longitud, no solo las del video.
"""

import itertools
import os

import pytest

from mt import Simulador, cargar_archivo

MAQUINAS = os.path.join(os.path.dirname(__file__), "..", "maquinas")


def maquina(nombre):
    return Simulador(cargar_archivo(os.path.join(MAQUINAS, nombre)))


def cadenas(alfabeto, hasta):
    for n in range(hasta + 1):
        for t in itertools.product(alfabeto, repeat=n):
            yield "".join(t)


def es_ww(w):
    n = len(w)
    return n > 0 and n % 2 == 0 and w[: n // 2] == w[n // 2:]


def test_ww_todas_las_cadenas_hasta_10():
    sim = maquina("reconocedora_ww.yaml")
    for w in cadenas("ab", 10):
        r = sim.ejecutar(w)
        assert r.aceptada == es_ww(w), w
        assert r.motivo in ("aceptada", "sin_transicion"), w


def test_palindromos_todas_las_cadenas_hasta_10():
    sim = maquina("palindromos.yaml")
    for w in cadenas("ab", 10):
        assert sim.ejecutar(w).aceptada == (w == w[::-1]), w


@pytest.mark.parametrize("x", range(0, 40))
def test_suma_binaria(x):
    sim = maquina("alteradora_suma_binaria.yaml")
    for y in range(0, 40):
        entrada = f"{x:b}+{y:b}"
        r = sim.ejecutar(entrada)
        assert r.aceptada, entrada
        assert int(r.cinta_final, 2) == x + y, entrada
        # solo queda el resultado y la cabeza al inicio de el
        assert set(r.cinta_final) <= {"0", "1"}, entrada
        assert r.final.cabeza == r.final.inicio, entrada


def test_suma_con_ceros_a_la_izquierda_y_operandos_vacios():
    sim = maquina("alteradora_suma_binaria.yaml")
    assert sim.ejecutar("0011+1").cinta_final == "0100"
    assert sim.ejecutar("101+").cinta_final == "101"
    assert sim.ejecutar("+11").cinta_final == "11"


def test_entradas_del_video():
    ww = maquina("reconocedora_ww.yaml")
    resultados = {w: ww.ejecutar(w).aceptada for w in ww.maquina.entradas}
    aceptadas = [w for w, a in resultados.items() if a and len(w) >= 5]
    rechazadas = [w for w, a in resultados.items() if not a and len(w) >= 5]
    assert len(aceptadas) >= 2 and len(rechazadas) >= 2

    suma = maquina("alteradora_suma_binaria.yaml")
    largas = [w for w in suma.maquina.entradas if len(w) >= 5]
    assert len(largas) >= 4
    for w in largas:
        x, y = w.split("+")
        assert int(suma.ejecutar(w).cinta_final, 2) == int(x, 2) + int(y, 2)
