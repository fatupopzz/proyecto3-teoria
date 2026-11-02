#!/usr/bin/env python3
"""Visor web del simulador.

Toda la simulacion corre en Python (paquete mt); el navegador solo recibe las
IDs ya calculadas y las reproduce sobre la cinta y el diagrama de estados.

Uso:
    python app.py            -> http://127.0.0.1:5050
    python app.py --puerto 8000
"""

import argparse
import os

from flask import Flask, abort, jsonify, render_template, request

from mt import ErrorConfiguracion, Simulador, cargar_archivo, cargar_texto
from mt.exportar import maquina_a_dict, resultado_a_dict

RAIZ = os.path.dirname(os.path.abspath(__file__))
CARPETA_MAQUINAS = os.path.join(RAIZ, "maquinas")
# Tope para el navegador: mas pasos que esto no se pueden ver uno por uno de
# todos modos y el JSON con una foto de la cinta por paso crece rapido.
LIMITE_PASOS_WEB = 20_000

app = Flask(__name__, template_folder="web/templates", static_folder="web/static")


def _maquinas():
    archivos = sorted(f for f in os.listdir(CARPETA_MAQUINAS) if f.endswith((".yaml", ".yml")))
    lista = []
    for archivo in archivos:
        try:
            m = cargar_archivo(os.path.join(CARPETA_MAQUINAS, archivo))
            nombre = m.nombre or archivo
        except ErrorConfiguracion:
            nombre = archivo
        lista.append({"archivo": archivo, "nombre": nombre})
    # las dos del proyecto primero
    orden = {"reconocedora_ww.yaml": 0, "alteradora_suma_binaria.yaml": 1}
    return sorted(lista, key=lambda m: (orden.get(m["archivo"], 2), m["archivo"]))


@app.get("/")
def inicio():
    return render_template("index.html")


@app.get("/api/maquinas")
def maquinas():
    return jsonify(_maquinas())


@app.get("/api/maquinas/<archivo>")
def maquina(archivo):
    if archivo not in {m["archivo"] for m in _maquinas()}:
        abort(404)
    with open(os.path.join(CARPETA_MAQUINAS, archivo), encoding="utf-8") as f:
        return jsonify({"archivo": archivo, "yaml": f.read()})


@app.post("/api/simular")
def simular():
    datos = request.get_json(silent=True) or {}
    try:
        m = cargar_texto(datos.get("yaml", ""))
    except ErrorConfiguracion as e:
        return jsonify({"error": e.mensaje, "linea": e.linea}), 400

    entradas = datos.get("entradas")
    if not isinstance(entradas, list):
        entradas = m.entradas
    simulador = Simulador(m, LIMITE_PASOS_WEB)
    return jsonify({
        "maquina": maquina_a_dict(m),
        "resultados": [resultado_a_dict(simulador.ejecutar(str(e)), m) for e in entradas],
    })


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Visor web del simulador de MT")
    p.add_argument("--puerto", type=int, default=5050)
    args = p.parse_args()
    app.run(host="127.0.0.1", port=args.puerto, debug=False)
