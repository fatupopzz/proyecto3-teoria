"""Simulacion de la MT y generacion de descripciones instantaneas (IDs)."""

from dataclasses import dataclass

from .cinta import Cinta
from .modelo import MaquinaTuring, Transicion

ACEPTADA = "aceptada"
SIN_TRANSICION = "sin_transicion"
LIMITE = "limite_pasos"
ENTRADA_INVALIDA = "entrada_invalida"

LIMITE_PASOS = 10_000


@dataclass(frozen=True)
class DescripcionInstantanea:
    """Foto de la MT en un paso: cinta visible, posicion de la cabeza y estado.

    `transicion` es la regla que se aplico para llegar a esta ID (None en la
    ID inicial).
    """

    paso: int
    estado: str
    cache: str
    inicio: int
    simbolos: tuple[str, ...]
    cabeza: int
    transicion: Transicion | None

    def texto(self, blanco="B", con_cache=True):
        """ID en notacion de Hopcroft: X1...Xi-1 [q, c] Xi...Xn.

        Se recortan los blancos de los extremos salvo el que esta bajo la cabeza.
        """
        i = self.cabeza - self.inicio
        izquierda = list(self.simbolos[:i])
        derecha = list(self.simbolos[i:])
        while izquierda and izquierda[0] == blanco:
            izquierda.pop(0)
        while len(derecha) > 1 and derecha[-1] == blanco:
            derecha.pop()
        estado = f"[{self.estado}, {self.cache}]" if con_cache else f"[{self.estado}]"
        return "".join(izquierda) + estado + "".join(derecha)


@dataclass
class Resultado:
    entrada: str
    aceptada: bool
    motivo: str
    detalle: str
    descripciones: list[DescripcionInstantanea]
    cinta_final: str

    @property
    def pasos(self):
        return max(len(self.descripciones) - 1, 0)

    @property
    def final(self):
        return self.descripciones[-1] if self.descripciones else None


class Simulador:
    def __init__(self, maquina: MaquinaTuring, limite_pasos=LIMITE_PASOS):
        self.maquina = maquina
        self.limite_pasos = limite_pasos

    def ejecutar(self, entrada: str) -> Resultado:
        """Corre la MT sobre la entrada hasta que se detenga.

        La MT se detiene al entrar a un estado de aceptacion (acepta) o cuando
        delta no esta definida para la configuracion actual (rechaza). Si pasa
        el limite de pasos se reporta como no detenida, porque el problema de
        la parada no deja decidir si ciclaria para siempre.
        """
        mt = self.maquina
        try:
            simbolos = mt.tokenizar(entrada)
        except ValueError as e:
            return Resultado(entrada, False, ENTRADA_INVALIDA, str(e), [], entrada)

        cinta = Cinta(simbolos, mt.blanco)
        estado, cache = mt.estado_inicial, mt.blanco
        ids = [self._foto(0, estado, cache, cinta, None)]

        while True:
            if mt.es_aceptacion(estado):
                return Resultado(entrada, True, ACEPTADA,
                                 f"la MT se detuvo en el estado de aceptación {estado}",
                                 ids, cinta.contenido())

            leido = cinta.leer()
            regla = mt.delta(estado, leido, cache)
            if regla is None:
                pareja = f"[{estado}, {cache}]" if mt.usa_cache else estado
                return Resultado(entrada, False, SIN_TRANSICION,
                                 f"δ({pareja}, {leido}) no está definida y {estado} no es "
                                 f"de aceptación", ids, cinta.contenido())

            if len(ids) > self.limite_pasos:
                return Resultado(entrada, False, LIMITE,
                                 f"la MT no se detuvo en {self.limite_pasos} pasos",
                                 ids, cinta.contenido())

            cinta.escribir(regla.escribe)
            cinta.mover(regla.mueve)
            estado, cache = regla.siguiente, regla.cache_escribe
            ids.append(self._foto(len(ids), estado, cache, cinta, regla))

    @staticmethod
    def _foto(paso, estado, cache, cinta, regla):
        inicio, simbolos = cinta.ventana()
        return DescripcionInstantanea(paso, estado, cache, inicio, tuple(simbolos),
                                      cinta.cabeza, regla)
