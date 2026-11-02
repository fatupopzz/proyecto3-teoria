"""Salida en terminal con rich: definicion formal, IDs, cinta y animacion."""

import time

from rich import box
from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from .simulador import ACEPTADA, LIMITE, ENTRADA_INVALIDA

TINTA = "#e8e1d0"
TENUE = "#8a8475"
CABEZA = "#ff7a3d"
ESTADO = "#7fb4ff"
CACHE = "#e0b84a"
SI = "#6fcf7f"
NO = "#ff6b5e"

consola = Console(highlight=False)


def _con_cache(maquina):
    return maquina.usa_cache


def _id_coloreado(d, maquina):
    """La ID con el estado resaltado y el simbolo bajo la cabeza subrayado."""
    plano = d.texto(maquina.blanco, _con_cache(maquina))
    abre, cierra = plano.index("["), plano.index("]") + 1
    t = Text()
    t.append(plano[:abre], style=TINTA)
    t.append("[", style=TENUE)
    t.append(d.estado, style=f"bold {ESTADO}")
    if _con_cache(maquina):
        t.append(", ", style=TENUE)
        t.append(d.cache, style=f"bold {CACHE}")
    t.append("]", style=TENUE)
    resto = plano[cierra:]
    if resto:
        t.append(resto[0], style=f"bold underline {CABEZA}")
        t.append(resto[1:], style=TINTA)
    return t


def mostrar_maquina(maquina, archivo=""):
    titulo = maquina.nombre or archivo or "Maquina de Turing"
    cabecera = Text()
    cabecera.append(titulo.upper(), style=f"bold {TINTA}")
    if archivo:
        cabecera.append(f"   {archivo}", style=TENUE)
    partes = [cabecera]
    if maquina.descripcion:
        partes.append(Text(maquina.descripcion, style=TENUE))

    tupla = Table.grid(padding=(0, 2))
    tupla.add_column(style=f"bold {CACHE}", justify="right")
    tupla.add_column(style=TINTA)
    llaves = lambda xs: "{ " + ", ".join(xs) + " }"
    tupla.add_row("Q", llaves(maquina.estados))
    tupla.add_row("Σ", llaves(maquina.alfabeto_entrada))
    tupla.add_row("Γ", llaves(maquina.alfabeto_cinta))
    tupla.add_row("q₀", maquina.estado_inicial)
    tupla.add_row("B", maquina.blanco)
    tupla.add_row("F", llaves(maquina.estados_aceptacion))
    tupla.add_row("δ", f"{len(maquina.transiciones)} reglas"
                  + ("  ·  el estado lleva cache [q, c]" if _con_cache(maquina) else ""))
    partes += [Text(""), Text("M = (Q, Σ, Γ, δ, q₀, B, F)", style=TENUE), tupla]

    consola.print(Panel(Group(*partes), box=box.HEAVY, border_style=TENUE, padding=(1, 2)))


def mostrar_transiciones(maquina):
    cache = _con_cache(maquina)
    tabla = Table(box=box.SIMPLE_HEAD, header_style=f"bold {TENUE}", border_style=TENUE,
                  title="δ", title_style=f"bold {CACHE}", title_justify="left")
    tabla.add_column("estado", style=f"bold {ESTADO}")
    if cache:
        tabla.add_column("cache", style=CACHE, justify="center")
    tabla.add_column("lee", justify="center", style=TINTA)
    tabla.add_column("", style=TENUE, justify="center")
    tabla.add_column("siguiente", style=f"bold {ESTADO}")
    if cache:
        tabla.add_column("cache'", style=CACHE, justify="center")
    tabla.add_column("escribe", justify="center", style=TINTA)
    tabla.add_column("mueve", justify="center", style=CABEZA)

    anterior = None
    for t in maquina.transiciones.values():
        if anterior is not None and t.estado != anterior:
            tabla.add_section()
        anterior = t.estado
        fila = [t.estado] + ([t.cache_lee] if cache else []) + [t.lee, "→", t.siguiente]
        fila += ([t.cache_escribe] if cache else []) + [t.escribe, t.mueve]
        tabla.add_row(*fila)
    consola.print(tabla)


def cinta_visual(simbolos, inicio, cabeza, blanco, margen=2):
    """Dibuja la cinta como celdas con la cabeza marcada encima."""
    izquierda = min(inicio, cabeza) - margen
    derecha = max(inicio + len(simbolos) - 1, cabeza) + margen
    celdas = [simbolos[i - inicio] if 0 <= i - inicio < len(simbolos) else blanco
              for i in range(izquierda, derecha + 1)]
    ancho = max(len(s) for s in celdas)

    marca, arriba, medio, abajo = Text(), Text(), Text(), Text()
    for k, s in enumerate(celdas):
        es_cabeza = izquierda + k == cabeza
        marca.append(" " + ("▼" if es_cabeza else " ").center(ancho + 2),
                     style=f"bold {CABEZA}")
        arriba.append("┌" + "─" * (ancho + 2) + "┐" if k == 0 else "┬" + "─" * (ancho + 2),
                      style=TENUE)
        estilo = f"bold reverse {CABEZA}" if es_cabeza else (TENUE if s == blanco else f"bold {TINTA}")
        medio.append("│", style=TENUE)
        medio.append(f" {s.center(ancho)} ", style=estilo)
        abajo.append("└" + "─" * (ancho + 2) if k == 0 else "┴" + "─" * (ancho + 2),
                     style=TENUE)
    arriba = Text(arriba.plain.replace("┐┬", "┬"), style=TENUE)
    arriba.append("┐", style=TENUE)
    medio.append("│", style=TENUE)
    abajo.append("┘", style=TENUE)
    return Group(marca, arriba, medio, abajo)


def _veredicto(resultado):
    if resultado.aceptada:
        return Text(" ACEPTADA ", style=f"bold black on {SI}")
    if resultado.motivo == LIMITE:
        return Text(" NO SE DETUVO ", style=f"bold black on {CACHE}")
    return Text(" RECHAZADA ", style=f"bold black on {NO}")


def mostrar_resultado(resultado, maquina, mostrar_ids=True):
    entrada = resultado.entrada if resultado.entrada else "ε"
    consola.print()
    consola.print(Rule(Text(f" w = {entrada} ", style=f"bold {TINTA}"), style=TENUE,
                       align="left"))

    if resultado.motivo == ENTRADA_INVALIDA:
        consola.print(_veredicto(resultado), Text(f"  {resultado.detalle}", style=NO))
        return

    if mostrar_ids:
        ids = Table(box=None, show_header=False, padding=(0, 1))
        ids.add_column(style=TENUE, justify="right")
        ids.add_column(style=TENUE)
        ids.add_column(no_wrap=True)
        ids.add_column(style=TENUE, no_wrap=True)
        for d in resultado.descripciones:
            regla = ""
            if d.transicion is not None:
                regla = d.transicion.formal(maquina.blanco, _con_cache(maquina))
            ids.add_row(str(d.paso), "  " if d.paso == 0 else "⊢ ",
                        _id_coloreado(d, maquina), Text(regla))
        consola.print(ids)
        consola.print()

    final = resultado.final
    consola.print(cinta_visual(final.simbolos, final.inicio, final.cabeza, maquina.blanco))
    resumen = Text()
    resumen.append_text(_veredicto(resultado))
    resumen.append(f"  {resultado.pasos} pasos", style=f"bold {TINTA}")
    resumen.append(f"  ·  cinta final: ", style=TENUE)
    resumen.append(resultado.cinta_final or "(vacia)", style=f"bold {TINTA}")
    resumen.append(f"\n  {resultado.detalle}", style=TENUE)
    consola.print(resumen)


def mostrar_resumen(resultados):
    tabla = Table(box=box.ROUNDED, border_style=TENUE, header_style=f"bold {TENUE}",
                  title="resumen", title_style=f"bold {CACHE}", title_justify="left")
    tabla.add_column("entrada", style=f"bold {TINTA}")
    tabla.add_column("|w|", justify="right", style=TENUE)
    tabla.add_column("resultado")
    tabla.add_column("pasos", justify="right", style=TINTA)
    tabla.add_column("cinta final", style=TINTA)
    for r in resultados:
        tabla.add_row(r.entrada or "ε", str(len(r.entrada)), _veredicto(r),
                      str(r.pasos), r.cinta_final or "(vacia)")
    consola.print()
    consola.print(tabla)


def animar(resultado, maquina, pausa=0.12):
    """Reproduce la ejecucion paso a paso sobre la misma zona de la terminal."""
    if not resultado.descripciones:
        mostrar_resultado(resultado, maquina, mostrar_ids=False)
        return
    # La ventana se fija al principio para que la cinta no "salte" al crecer.
    ventana_ini = min(d.inicio for d in resultado.descripciones)
    ventana_fin = max(d.inicio + len(d.simbolos) - 1 for d in resultado.descripciones)
    ventana_ini = min(ventana_ini, *(d.cabeza for d in resultado.descripciones))
    ventana_fin = max(ventana_fin, *(d.cabeza for d in resultado.descripciones))

    def cuadro(d, final=False):
        simbolos = [maquina.blanco] * (ventana_fin - ventana_ini + 1)
        for k, s in enumerate(d.simbolos):
            simbolos[d.inicio + k - ventana_ini] = s
        cabecera = Text()
        cabecera.append(f"paso {d.paso:>4} / {resultado.pasos}   ", style=TENUE)
        cabecera.append("estado ", style=TENUE)
        cabecera.append(d.estado, style=f"bold {ESTADO}")
        if _con_cache(maquina):
            cabecera.append("   cache ", style=TENUE)
            cabecera.append(d.cache, style=f"bold {CACHE}")
        regla = Text(d.transicion.formal(maquina.blanco, _con_cache(maquina))
                     if d.transicion else "configuración inicial", style=TENUE)
        partes = [cabecera, cinta_visual(simbolos, ventana_ini, d.cabeza, maquina.blanco),
                  Text(""), regla, Text(""), _id_coloreado(d, maquina)]
        if final:
            pie = Text("\n")
            pie.append_text(_veredicto(resultado))
            pie.append(f"  {resultado.detalle}", style=TENUE)
            partes.append(pie)
        return Panel(Group(*partes), title=Text(f" w = {resultado.entrada or 'ε'} ",
                                                style=f"bold {TINTA}"),
                     title_align="left", box=box.HEAVY, border_style=TENUE, padding=(1, 2))

    with Live(cuadro(resultado.descripciones[0]), console=consola,
              refresh_per_second=60) as vivo:
        for d in resultado.descripciones[1:]:
            time.sleep(pausa)
            vivo.update(cuadro(d))
        time.sleep(pausa)
        vivo.update(cuadro(resultado.descripciones[-1], final=True))
