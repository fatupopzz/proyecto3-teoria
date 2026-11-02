#!/usr/bin/env python3
"""Simulador de Maquinas de Turing de una cinta.

Uso:
    python main.py maquinas/reconocedora_ww.yaml
    python main.py maquinas/alteradora_suma_binaria.yaml --animar
    python main.py maquinas/palindromos.yaml -e abba -e abc
    python main.py maquinas/reconocedora_ww.yaml --guardar salidas/
"""

import argparse
import os
import sys

from mt import ErrorConfiguracion, Simulador, cargar_archivo
from mt.consola import (consola, animar, mostrar_maquina, mostrar_resultado,
                        mostrar_resumen, mostrar_transiciones)
from mt.simulador import LIMITE_PASOS


def guardar_traza(carpeta, archivo, maquina, resultados):
    """Escribe las IDs de cada entrada en un .txt plano."""
    os.makedirs(carpeta, exist_ok=True)
    base = os.path.splitext(os.path.basename(archivo))[0]
    ruta = os.path.join(carpeta, f"{base}.txt")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(f"{maquina.nombre or base}\n\n")
        for r in resultados:
            f.write(f"w = {r.entrada or 'ε'}\n")
            for d in r.descripciones:
                prefijo = "   " if d.paso == 0 else "⊢  "
                f.write(f"{d.paso:>5} {prefijo}{d.texto(maquina.blanco, maquina.usa_cache)}\n")
            estado = "ACEPTADA" if r.aceptada else "RECHAZADA"
            f.write(f"=> {estado} en {r.pasos} pasos. {r.detalle}. "
                    f"Cinta final: {r.cinta_final or '(vacia)'}\n\n")
    return ruta


def main():
    p = argparse.ArgumentParser(description="Simulador de Maquinas de Turing de una cinta")
    p.add_argument("archivo", help="archivo YAML con la descripcion de la MT")
    p.add_argument("-e", "--entrada", action="append",
                   help="cadena a simular (reemplaza las 'inputs' del YAML; se puede repetir)")
    p.add_argument("-a", "--animar", action="store_true",
                   help="reproducir cada ejecucion paso a paso en la terminal")
    p.add_argument("-v", "--velocidad", type=float, default=0.12,
                   help="segundos entre pasos al animar (por defecto 0.12)")
    p.add_argument("-c", "--compacto", action="store_true",
                   help="no listar las IDs, solo el resultado")
    p.add_argument("-g", "--guardar", metavar="CARPETA",
                   help="guardar las IDs de cada entrada en CARPETA/<maquina>.txt")
    p.add_argument("--max-pasos", type=int, default=LIMITE_PASOS,
                   help=f"pasos antes de declarar que la MT no se detuvo ({LIMITE_PASOS})")
    p.add_argument("--sin-delta", action="store_true",
                   help="no imprimir la tabla de transiciones")
    args = p.parse_args()

    try:
        maquina = cargar_archivo(args.archivo)
    except FileNotFoundError:
        consola.print(f"[bold red]No existe el archivo {args.archivo}[/]")
        return 1
    except ErrorConfiguracion as e:
        consola.print(f"[bold red]Configuracion invalida[/] en {args.archivo}, {e}")
        return 1

    mostrar_maquina(maquina, args.archivo)
    if not args.sin_delta:
        mostrar_transiciones(maquina)

    entradas = args.entrada if args.entrada is not None else maquina.entradas
    if not entradas:
        consola.print("[yellow]El YAML no trae 'inputs'; pase cadenas con -e.[/]")
        return 0

    simulador = Simulador(maquina, args.max_pasos)
    resultados = []
    for entrada in entradas:
        r = simulador.ejecutar(entrada)
        resultados.append(r)
        if args.animar:
            consola.print()
            animar(r, maquina, args.velocidad)
        else:
            mostrar_resultado(r, maquina, mostrar_ids=not args.compacto)

    mostrar_resumen(resultados)
    if args.guardar:
        ruta = guardar_traza(args.guardar, args.archivo, maquina, resultados)
        consola.print(f"\n[dim]IDs guardadas en[/] {ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
