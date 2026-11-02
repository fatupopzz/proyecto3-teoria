"""Conversion de la MT y sus ejecuciones a diccionarios (JSON para el visor web)."""


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
