"""Cinta infinita en ambas direcciones."""

from .modelo import IZQUIERDA, DERECHA


class Cinta:
    """Guarda solo las celdas no blancas en un diccionario posicion -> simbolo.

    Asi la cinta crece hacia cualquier lado sin copiar listas y una posicion que
    nunca se toco vale blanco.
    """

    def __init__(self, simbolos, blanco):
        self.blanco = blanco
        self.celdas = {i: s for i, s in enumerate(simbolos) if s != blanco}
        self.cabeza = 0

    def leer(self):
        return self.celdas.get(self.cabeza, self.blanco)

    def escribir(self, simbolo):
        if simbolo == self.blanco:
            self.celdas.pop(self.cabeza, None)
        else:
            self.celdas[self.cabeza] = simbolo

    def mover(self, direccion):
        if direccion == IZQUIERDA:
            self.cabeza -= 1
        elif direccion == DERECHA:
            self.cabeza += 1

    def ventana(self):
        """(inicio, simbolos) de la porcion no blanca, ampliada hasta incluir la cabeza."""
        if self.celdas:
            inicio = min(min(self.celdas), self.cabeza)
            fin = max(max(self.celdas), self.cabeza)
        else:
            inicio = fin = self.cabeza
        return inicio, [self.celdas.get(i, self.blanco) for i in range(inicio, fin + 1)]

    def contenido(self):
        """La cinta sin los blancos de los extremos."""
        if not self.celdas:
            return ""
        return "".join(self.celdas.get(i, self.blanco)
                       for i in range(min(self.celdas), max(self.celdas) + 1))
