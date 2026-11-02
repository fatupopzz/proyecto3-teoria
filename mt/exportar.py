"""Conversion de la MT y sus ejecuciones a diccionarios (JSON para el visor web).

`simular_texto` es lo que responde el visor: lo llama el servidor Flask y, en
GitHub Pages, el mismo codigo corriendo en el navegador con Pyodide.
"""

from .parser import ErrorConfiguracion, cargar_texto
from .simulador import Simulador


def transicion_a_dict(t):
    return {"estado": t.estado, "lee": t.lee, "cacheLee": t.cache_lee,
            "siguiente": t.siguiente, "escribe": t.escribe,
            "cacheEscribe": t.cache_escribe, "mueve": t.mueve, "linea": t.linea}


def maquina_a_dict(m):
    return {
        "nombre": m.nombre,
        "descripcion": m.descripcion,
        "estados": m.estados,
        "alfabetoEntrada": m.alfabeto_entrada,
        "alfabetoCinta": m.alfabeto_cinta,
        "inicial": m.estado_inicial,
        "blanco": m.blanco,
        "aceptacion": m.estados_aceptacion,
        "usaCache": m.usa_cache,
        "transiciones": [transicion_a_dict(t) for t in m.transiciones.values()],
        "entradas": m.entradas,
    }


def resultado_a_dict(r, maquina):
    reglas = list(maquina.transiciones.values())
    indice = {t.clave: k for k, t in enumerate(reglas)}
    return {
        "entrada": r.entrada,
        "aceptada": r.aceptada,
        "motivo": r.motivo,
        "detalle": r.detalle,
        "pasos": r.pasos,
        "cintaFinal": r.cinta_final,
        "ids": [{
            "paso": d.paso,
            "estado": d.estado,
            "cache": d.cache,
            "inicio": d.inicio,
            "cinta": list(d.simbolos),
            "cabeza": d.cabeza,
            "regla": None if d.transicion is None else indice[d.transicion.clave],
            "texto": d.texto(maquina.blanco, maquina.usa_cache),
        } for d in r.descripciones],
    }


def simular_texto(texto, entradas=None, limite_pasos=20_000):
    """YAML -> (respuesta, ok). Si entradas es None se usan las 'inputs' del YAML."""
    try:
        m = cargar_texto(texto)
    except ErrorConfiguracion as e:
        return {"error": e.mensaje, "linea": e.linea}, False
    if not isinstance(entradas, list):
        entradas = m.entradas
    simulador = Simulador(m, limite_pasos)
    return {
        "maquina": maquina_a_dict(m),
        "resultados": [resultado_a_dict(simulador.ejecutar(str(e)), m) for e in entradas],
    }, True
