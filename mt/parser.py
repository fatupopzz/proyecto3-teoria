"""Lectura y validacion del archivo YAML que describe la MT.

Formato (el del enunciado):

    mt:
      states: [q0, q1, qf]
      input_alphabet: [a, b]
      tape_alphabet: [a, b, B, X]
      initial_state: q0
      accept_states: [qf]
      transitions:
        - state: q0
          read: [a, B]      # [simbolo en cinta, cache]
          write: [a, B]     # [nuevo cache, simbolo que se escribe]
          move: R
          next: q1
      inputs:
        - "aabb"

`read` y `write` tambien aceptan un solo simbolo cuando la regla no toca el
cache: `read: a` equivale a `[a, B]` y `write: X` a `[B, X]`.
Claves opcionales: `blank` (por defecto B), `name` y `description`.
"""

import yaml

from .modelo import MaquinaTuring, Transicion, MOVIMIENTOS


class ErrorConfiguracion(Exception):
    def __init__(self, mensaje, linea=None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.linea = linea

    def __str__(self):
        if self.linea:
            return f"línea {self.linea}: {self.mensaje}"
        return self.mensaje


class _Cargador(yaml.SafeLoader):
    """SafeLoader donde todo escalar es texto y cada mapeo recuerda su linea.

    Sin esto YAML 1.1 convierte Y, N, on, off en booleanos y 0/1 en enteros,
    y un alfabeto como [a, b, X, Y] llega como ['a', 'b', 'X', True].
    """

    yaml_implicit_resolvers = {}

    def construct_mapping(self, node, deep=False):
        mapa = super().construct_mapping(node, deep=deep)
        mapa["__linea__"] = node.start_mark.line + 1
        return mapa


_Cargador.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                          _Cargador.construct_mapping)

# Sinonimos de movimiento que se ven seguido en libros y otros simuladores.
_MOVIMIENTOS = {"L": "L", "R": "R", "S": "S", "N": "S", "-": "S",
                "I": "L", "D": "R", "LEFT": "L", "RIGHT": "R", "STAY": "S"}


def cargar_archivo(ruta):
    with open(ruta, encoding="utf-8") as f:
        return cargar_texto(f.read())


def cargar_texto(texto):
    try:
        datos = yaml.load(texto, Loader=_Cargador)
    except yaml.YAMLError as e:
        marca = getattr(e, "problem_mark", None)
        linea = marca.line + 1 if marca else None
        problema = getattr(e, "problem", None) or str(e)
        raise ErrorConfiguracion(f"YAML mal formado: {problema}", linea) from None

    if not isinstance(datos, dict):
        raise ErrorConfiguracion("el archivo debe ser un mapeo con la clave 'mt'")
    raiz = datos.get("mt", datos)
    if not isinstance(raiz, dict):
        raise ErrorConfiguracion("'mt' debe ser un mapeo", datos.get("__linea__"))
    return _construir(raiz)


def _lista(raiz, clave, obligatoria=True):
    valor = raiz.get(clave)
    if valor is None:
        if obligatoria:
            raise ErrorConfiguracion(f"falta la clave '{clave}'", raiz.get("__linea__"))
        return []
    if not isinstance(valor, list):
        valor = [valor]
    for v in valor:
        if not isinstance(v, str):
            raise ErrorConfiguracion(f"'{clave}' solo puede contener símbolos o nombres",
                                     raiz.get("__linea__"))
    return [v.strip() for v in valor]


def _texto(raiz, clave, defecto=None):
    valor = raiz.get(clave, defecto)
    if valor is None:
        raise ErrorConfiguracion(f"falta la clave '{clave}'", raiz.get("__linea__"))
    if not isinstance(valor, str):
        raise ErrorConfiguracion(f"'{clave}' debe ser un solo valor", raiz.get("__linea__"))
    return valor.strip()


def _repetidos(valores):
    vistos, rep = set(), []
    for v in valores:
        if v in vistos and v not in rep:
            rep.append(v)
        vistos.add(v)
    return rep


def _construir(raiz):
    linea_raiz = raiz.get("__linea__")
    estados = _lista(raiz, "states")
    sigma = _lista(raiz, "input_alphabet")
    gamma = _lista(raiz, "tape_alphabet")
    inicial = _texto(raiz, "initial_state")
    aceptacion = _lista(raiz, "accept_states")
    blanco = _texto(raiz, "blank", "B")

    if not estados:
        raise ErrorConfiguracion("Q no puede ser vacío", linea_raiz)
    for nombre, valores in (("states", estados), ("input_alphabet", sigma),
                            ("tape_alphabet", gamma)):
        if rep := _repetidos(valores):
            raise ErrorConfiguracion(f"'{nombre}' repite {', '.join(rep)}", linea_raiz)
        if "" in valores:
            raise ErrorConfiguracion(f"'{nombre}' tiene un elemento vacío", linea_raiz)

    if blanco not in gamma:
        raise ErrorConfiguracion(f"el blanco '{blanco}' debe estar en Γ (tape_alphabet)",
                                 linea_raiz)
    if blanco in sigma:
        raise ErrorConfiguracion(f"el blanco '{blanco}' no puede estar en Σ (input_alphabet)",
                                 linea_raiz)
    if fuera := [s for s in sigma if s not in gamma]:
        raise ErrorConfiguracion(f"Σ debe estar contenido en Γ; faltan en Γ: {', '.join(fuera)}",
                                 linea_raiz)
    if inicial not in estados:
        raise ErrorConfiguracion(f"el estado inicial '{inicial}' no está en Q", linea_raiz)
    if fuera := [q for q in aceptacion if q not in estados]:
        raise ErrorConfiguracion(f"estados de aceptación fuera de Q: {', '.join(fuera)}",
                                 linea_raiz)

    reglas = raiz.get("transitions")
    if reglas is None:
        raise ErrorConfiguracion("falta la clave 'transitions'", linea_raiz)
    if not isinstance(reglas, list):
        raise ErrorConfiguracion("'transitions' debe ser una lista", linea_raiz)

    transiciones = {}
    for regla in reglas:
        t = _transicion(regla, estados, gamma, blanco)
        if (previa := transiciones.get(t.clave)) is not None:
            raise ErrorConfiguracion(
                f"la MT no es determinista: δ([{t.estado}, {t.cache_lee}], {t.lee}) ya se "
                f"definió en la línea {previa.linea}", t.linea)
        transiciones[t.clave] = t

    entradas = raiz.get("inputs", [])
    if not isinstance(entradas, list):
        entradas = [entradas]
    entradas = ["" if e is None else e for e in entradas]
    if any(not isinstance(e, str) for e in entradas):
        raise ErrorConfiguracion("cada elemento de 'inputs' debe ser una cadena", linea_raiz)

    return MaquinaTuring(
        estados=estados,
        alfabeto_entrada=sigma,
        alfabeto_cinta=gamma,
        transiciones=transiciones,
        estado_inicial=inicial,
        blanco=blanco,
        estados_aceptacion=aceptacion,
        entradas=entradas,
        nombre=str(raiz.get("name", "")).strip(),
        descripcion=" ".join(str(raiz.get("description", "")).split()),
    )


def _par(regla, clave, linea):
    """Normaliza read/write a una pareja; un escalar deja el cache en blanco."""
    valor = regla.get(clave)
    if valor is None:
        raise ErrorConfiguracion(f"la transición no tiene '{clave}'", linea)
    if isinstance(valor, str):
        return None, valor.strip()
    if isinstance(valor, list) and len(valor) == 2 and all(isinstance(v, str) for v in valor):
        return valor[0].strip(), valor[1].strip()
    if isinstance(valor, list) and len(valor) == 1 and isinstance(valor[0], str):
        return None, valor[0].strip()
    raise ErrorConfiguracion(f"'{clave}' debe ser un símbolo o una lista de dos símbolos", linea)


def _transicion(regla, estados, gamma, blanco):
    if not isinstance(regla, dict):
        raise ErrorConfiguracion("cada transición debe ser un mapeo con state, read, "
                                 "write, move y next")
    linea = regla["__linea__"]
    for clave in ("state", "next", "move"):
        if not isinstance(regla.get(clave), str):
            raise ErrorConfiguracion(f"la transición no tiene '{clave}'", linea)

    estado, siguiente = regla["state"].strip(), regla["next"].strip()
    for q in (estado, siguiente):
        if q not in estados:
            raise ErrorConfiguracion(f"el estado '{q}' no está en Q", linea)

    # read = [simbolo leido, cache]   write = [nuevo cache, simbolo escrito]
    a, b = _par(regla, "read", linea)
    lee, cache_lee = (b, blanco) if a is None else (a, b)
    a, b = _par(regla, "write", linea)
    cache_escribe, escribe = (blanco, b) if a is None else (a, b)

    for nombre, s in (("read", lee), ("read (cache)", cache_lee),
                      ("write", escribe), ("write (cache)", cache_escribe)):
        if s not in gamma:
            raise ErrorConfiguracion(f"'{s}' en {nombre} no pertenece a Γ", linea)

    mueve = _MOVIMIENTOS.get(regla["move"].strip().upper())
    if mueve not in MOVIMIENTOS:
        raise ErrorConfiguracion(f"movimiento '{regla['move']}' inválido; use L, R o S", linea)

    return Transicion(estado, lee, cache_lee, siguiente, escribe, cache_escribe,
                      mueve, linea)
