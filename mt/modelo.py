"""Estructuras de datos que alojan la configuracion de una MT de una cinta.

La maquina sigue la convencion del enunciado (Hopcroft, seccion 8.3.1):
el estado puede llevar un "cache", un simbolo guardado en el control finito.
Asi un estado completo es el par [q, c] y la funcion de transicion es

    delta([q, c], X) = ([p, c'], Y, D)

donde X es lo que se lee en la cinta, Y lo que se escribe, c' el nuevo valor
del cache y D el movimiento. Una maquina que no usa el cache simplemente lo
deja siempre en blanco.
"""

from dataclasses import dataclass, field

IZQUIERDA = "L"
DERECHA = "R"
QUIETO = "S"
MOVIMIENTOS = (IZQUIERDA, DERECHA, QUIETO)


@dataclass(frozen=True)
class Transicion:
    """Una regla delta([estado, cache_lee], lee) = ([siguiente, cache_escribe], escribe, mueve)."""

    estado: str
    lee: str
    cache_lee: str
    siguiente: str
    escribe: str
    cache_escribe: str
    mueve: str
    linea: int | None = field(default=None, compare=False)

    @property
    def clave(self):
        return (self.estado, self.lee, self.cache_lee)

    def formal(self, blanco="B", con_cache=True):
        """Texto de la regla en notacion de clase."""
        if con_cache:
            return (f"δ([{self.estado}, {self.cache_lee}], {self.lee}) = "
                    f"([{self.siguiente}, {self.cache_escribe}], {self.escribe}, {self.mueve})")
        return (f"δ({self.estado}, {self.lee}) = "
                f"({self.siguiente}, {self.escribe}, {self.mueve})")


@dataclass
class MaquinaTuring:
    """M = (Q, Σ, Γ, δ, q0, B, F)."""

    estados: list[str]
    alfabeto_entrada: list[str]
    alfabeto_cinta: list[str]
    transiciones: dict[tuple[str, str, str], Transicion]
    estado_inicial: str
    blanco: str
    estados_aceptacion: list[str]
    entradas: list[str] = field(default_factory=list)
    nombre: str = ""
    descripcion: str = ""

    @property
    def usa_cache(self):
        """True si alguna regla lee o escribe algo distinto de blanco en el cache."""
        return any(t.cache_lee != self.blanco or t.cache_escribe != self.blanco
                   for t in self.transiciones.values())

    def delta(self, estado, simbolo, cache):
        return self.transiciones.get((estado, simbolo, cache))

    def es_aceptacion(self, estado):
        return estado in self.estados_aceptacion

    def tokenizar(self, cadena):
        """Parte la cadena en simbolos de Σ (los simbolos pueden tener mas de un caracter).

        Usa coincidencia mas larga primero. Lanza ValueError si sobra algo que
        no pertenece al alfabeto de entrada.
        """
        alfabeto = sorted(self.alfabeto_entrada, key=len, reverse=True)
        simbolos, i = [], 0
        while i < len(cadena):
            for s in alfabeto:
                if cadena.startswith(s, i):
                    simbolos.append(s)
                    i += len(s)
                    break
            else:
                raise ValueError(f"'{cadena[i]}' (posicion {i}) no pertenece a Σ = "
                                 f"{{{', '.join(self.alfabeto_entrada)}}}")
        return simbolos
