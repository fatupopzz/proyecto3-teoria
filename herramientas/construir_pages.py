#!/usr/bin/env python3
"""Arma la version estatica del visor para GitHub Pages.

    python herramientas/construir_pages.py _site

Copia la pagina, el paquete mt/ y las maquinas. En Pages no hay Flask: el
visor carga Pyodide y ejecuta estos mismos archivos de Python en el navegador.
"""

import json
import os
import shutil
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from app import listar_maquinas  # noqa: E402  (mismo orden y nombres que el servidor)

ARCHIVOS_MT = ["__init__.py", "modelo.py", "parser.py", "cinta.py", "simulador.py", "exportar.py"]


def construir(destino):
    if os.path.exists(destino):
        shutil.rmtree(destino)
    os.makedirs(os.path.join(destino, "mt"))
    os.makedirs(os.path.join(destino, "maquinas"))

    with open(os.path.join(RAIZ, "web", "templates", "index.html"), encoding="utf-8") as f:
        pagina = f.read()
    marca = '<script src="static/visor.js"></script>'
    assert marca in pagina, "index.html cambio: no se encontro el script del visor"
    pagina = pagina.replace(marca, "<script>window.MT_ESTATICO = true;</script>\n  " + marca)
    with open(os.path.join(destino, "index.html"), "w", encoding="utf-8") as f:
        f.write(pagina)

    shutil.copytree(os.path.join(RAIZ, "web", "static"), os.path.join(destino, "static"))
    for archivo in ARCHIVOS_MT:
        shutil.copy(os.path.join(RAIZ, "mt", archivo), os.path.join(destino, "mt", archivo))

    maquinas = listar_maquinas()
    for m in maquinas:
        shutil.copy(os.path.join(RAIZ, "maquinas", m["archivo"]),
                    os.path.join(destino, "maquinas", m["archivo"]))
    with open(os.path.join(destino, "maquinas", "indice.json"), "w", encoding="utf-8") as f:
        json.dump(maquinas, f, ensure_ascii=False, indent=2)

    # sin esto Pages pasa los archivos por Jekyll
    open(os.path.join(destino, ".nojekyll"), "w").close()
    print(f"sitio estatico en {destino}/ ({len(maquinas)} maquinas)")


if __name__ == "__main__":
    construir(sys.argv[1] if len(sys.argv) > 1 else "_site")
