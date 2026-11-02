import pytest

from mt import ErrorConfiguracion, Simulador, cargar_texto
from mt.simulador import ENTRADA_INVALIDA, LIMITE, SIN_TRANSICION

BASE = """
mt:
  states: [q0, q1, qf]
  input_alphabet: [a, b]
  tape_alphabet: [a, b, X, Y, B]
  initial_state: q0
  accept_states: [qf]
  transitions:
{reglas}
  inputs: ["ab"]
"""


def mt(reglas):
    return cargar_texto(BASE.format(reglas=reglas))


def test_ejemplo_del_enunciado():
    m = cargar_texto("""
mt:
  states: [q0, q1, q2, qf]
  input_alphabet: [a, b]
  tape_alphabet: [a, b, B, X, Y]
  initial_state: q0
  accept_states: [qf]
  transitions:
    - state: q0
      read: [a, B]
      write: [a, B]
      move: R
      next: q1
  inputs:
    - "aabb"
""")
    t = m.delta("q0", "a", "B")
    # δ([q0, B], a) = ([q1, a], B, R)
    assert (t.siguiente, t.cache_escribe, t.escribe, t.mueve) == ("q1", "a", "B", "R")
    assert t.formal() == "δ([q0, B], a) = ([q1, a], B, R)"
    assert m.entradas == ["aabb"]


def test_y_n_no_se_vuelven_booleanos():
    m = mt("    - {state: q0, read: a, write: Y, move: R, next: qf}")
    assert "Y" in m.alfabeto_cinta
    assert m.delta("q0", "a", "B").escribe == "Y"


def test_ids_en_notacion_de_hopcroft():
    m = mt("""    - {state: q0, read: a, write: X, move: R, next: q1}
    - {state: q1, read: b, write: Y, move: L, next: qf}""")
    r = Simulador(m).ejecutar("ab")
    assert [d.texto() for d in r.descripciones] == ["[q0, B]ab", "X[q1, B]b", "[qf, B]XY"]
    assert r.aceptada and r.cinta_final == "XY"


def test_rechaza_cuando_no_hay_transicion():
    m = mt("    - {state: q0, read: a, write: a, move: R, next: q1}")
    r = Simulador(m).ejecutar("ab")
    assert not r.aceptada and r.motivo == SIN_TRANSICION
    assert "δ" in r.detalle


def test_limite_de_pasos():
    m = mt("""    - {state: q0, read: a, write: a, move: R, next: q1}
    - {state: q1, read: b, write: b, move: L, next: q0}""")
    r = Simulador(m, limite_pasos=50).ejecutar("ab")
    assert r.motivo == LIMITE and r.pasos == 50


def test_cinta_crece_a_la_izquierda():
    m = mt("""    - {state: q0, read: a, write: a, move: L, next: q1}
    - {state: q1, read: B, write: X, move: S, next: qf}""")
    r = Simulador(m).ejecutar("a")
    assert r.cinta_final == "Xa"
    assert r.final.inicio == -1


def test_entrada_fuera_del_alfabeto():
    m = mt("    - {state: q0, read: a, write: a, move: R, next: qf}")
    r = Simulador(m).ejecutar("abc")
    assert r.motivo == ENTRADA_INVALIDA and not r.descripciones


def test_cadena_vacia():
    m = mt("    - {state: q0, read: B, write: B, move: S, next: qf}")
    assert Simulador(m).ejecutar("").aceptada


@pytest.mark.parametrize("reglas, fragmento", [
    ("    - {state: q0, read: a, write: X, move: R, next: q9}", "'q9' no esta en Q"),
    ("    - {state: q0, read: z, write: X, move: R, next: q1}", "'z' en read no pertenece a Γ"),
    ("    - {state: q0, read: a, write: X, move: U, next: q1}", "movimiento 'U'"),
    ("    - {state: q0, read: [a, b, c], write: X, move: R, next: q1}", "lista de dos"),
    ("    - {state: q0, read: a, move: R, next: q1}", "no tiene 'write'"),
    ("""    - {state: q0, read: a, write: X, move: R, next: q1}
    - {state: q0, read: a, write: Y, move: L, next: q1}""", "no es determinista"),
])
def test_errores_de_transiciones(reglas, fragmento):
    with pytest.raises(ErrorConfiguracion) as e:
        mt(reglas)
    assert fragmento in str(e.value)
    assert e.value.linea is not None


def test_determinismo_reporta_ambas_lineas():
    with pytest.raises(ErrorConfiguracion) as e:
        mt("""    - {state: q0, read: a, write: X, move: R, next: q1}
    - {state: q0, read: a, write: Y, move: L, next: q1}""")
    assert e.value.linea == 10 and "linea 9" in e.value.mensaje


@pytest.mark.parametrize("texto, fragmento", [
    ("mt: [1, 2]", "debe ser un mapeo"),
    ("mt:\n  states: [q0]\n", "input_alphabet"),
    ("mt:\n  states: [q0]\n  input_alphabet: [a, B]\n  tape_alphabet: [a, B]\n"
     "  initial_state: q0\n  accept_states: []\n  transitions: []\n", "blanco"),
    ("mt:\n  states: [q0]\n  input_alphabet: [a]\n  tape_alphabet: [B]\n"
     "  initial_state: q0\n  accept_states: []\n  transitions: []\n", "Σ debe estar contenido"),
    ("mt:\n  states: [q0]\n  input_alphabet: [a]\n  tape_alphabet: [a, B]\n"
     "  initial_state: q5\n  accept_states: []\n  transitions: []\n", "estado inicial"),
    ("mt:\n  states: [q0\n", "YAML mal formado"),
])
def test_errores_de_definicion(texto, fragmento):
    with pytest.raises(ErrorConfiguracion) as e:
        cargar_texto(texto)
    assert fragmento in str(e.value)
