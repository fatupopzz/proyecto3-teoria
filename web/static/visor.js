// Visor de la MT. La simulacion la hace Python (POST /api/simular); aqui solo
// se reproducen las IDs que regresa: cinta, control finito, impresion y sello.
"use strict";

const $ = (s) => document.querySelector(s);
const SVG = "http://www.w3.org/2000/svg";

const E = {
  fichas: $("#fichas"), archivo: $("#archivo"), descripcion: $("#descripcion"),
  entradas: $("#entradas"), propia: $("#propia"), cadena: $("#cadena"),
  marco: $("#cinta-marco"), cinta: $("#cinta"), posiciones: $("#posiciones"),
  sello: $("#sello"), aviso: $("#aviso"),
  estado: $("#estado"), cacheCaja: $("#cache-caja"), cache: $("#cache"), regla: $("#regla"),
  paso: $("#paso"), total: $("#total"),
  bInicio: $("#b-inicio"), bAtras: $("#b-atras"), bPlay: $("#b-play"),
  bAdelante: $("#b-adelante"), bFin: $("#b-fin"),
  tiempo: $("#tiempo"), velocidad: $("#velocidad"), velTxt: $("#vel-txt"),
  grafo: $("#grafo"), papel: $("#papel"), ids: $("#ids"),
  formal: $("#p-formal"), delta: $("#p-delta"),
  yaml: $("#yaml"), numeros: $("#numeros"), error: $("#error"), aplicar: $("#aplicar"),
  pieArchivo: $("#pie-archivo"),
};

const S = {
  maquinas: [],
  archivo: null,       // archivo de /maquinas abierto, o null si se subio uno
  subido: null,        // {nombre, yaml} del archivo subido por el usuario
  yaml: "",
  maquina: null,
  resultados: [],
  sel: 0,
  paso: 0,
  reproduciendo: false,
  vel: 8,
  raf: 0,
  cinta: null,
  pos: {},             // posicion de cada estado en el diagrama
  capas: {},
  filasIds: [],
  filasDelta: [],
  pasoPintado: null,
};

const guardar = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) {} };
const leer = (k) => { try { return JSON.parse(localStorage.getItem(k)); } catch (_) { return null; } };

function h(tag, attrs = {}, ...hijos) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v === true ? "" : v);
  }
  for (const c of hijos.flat()) if (c !== null && c !== undefined) n.append(c);
  return n;
}

function s(tag, attrs = {}) {
  const n = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
  return n;
}

const actual = () => S.resultados[S.sel];
const ultimoPaso = () => Math.max((actual()?.ids.length || 1) - 1, 0);
const anchoCelda = () => parseFloat(getComputedStyle(E.cinta.firstChild || E.cinta).flexBasis) || 58;

// ======================================================================
// carga
// ======================================================================

async function iniciar() {
  E.velocidad.value = leer("mt.vel") || 8;
  ajustarVelocidad(+E.velocidad.value);

  S.maquinas = await (await fetch("/api/maquinas")).json();
  const recordada = leer("mt.archivo");
  const inicial = S.maquinas.find((m) => m.archivo === recordada) || S.maquinas[0];
  if (inicial) await abrirMaquina(inicial.archivo);
}

async function abrirMaquina(archivo) {
  const r = await fetch("/api/maquinas/" + encodeURIComponent(archivo));
  if (!r.ok) return;
  const d = await r.json();
  S.archivo = archivo;
  guardar("mt.archivo", archivo);
  ponerYaml(d.yaml);
  renderFichas();
  await simular(d.yaml);
}

async function simular(yaml, { entradas = null, agregar = false } = {}) {
  let d, ok;
  try {
    const r = await fetch("/api/simular", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ yaml, entradas }),
    });
    ok = r.ok;
    d = await r.json();
  } catch (e) {
    mostrarError({ error: "no se pudo contactar al servidor: " + e.message });
    return false;
  }
  if (!ok) {
    mostrarError(d);
    return false;
  }
  limpiarError();

  if (agregar) {
    for (const x of d.resultados) S.resultados.push({ ...x, propia: true });
    renderEntradas();
    seleccionar(S.resultados.length - 1);
    return true;
  }

  S.yaml = yaml;
  S.maquina = d.maquina;
  S.resultados = d.resultados;
  renderMaquina();
  renderEntradas();
  seleccionar(0);
  return true;
}

// ======================================================================
// cabecera y cadenas
// ======================================================================

function tipoDe(archivo) {
  if (archivo.startsWith("reconocedora")) return "reconocedora";
  if (archivo.startsWith("alteradora")) return "alteradora";
  return "ejemplo";
}

function renderFichas() {
  E.fichas.replaceChildren();
  const fichas = S.maquinas.map((m, i) => ({
    clave: m.archivo, num: String(i + 1).padStart(2, "0"), nom: m.nombre.replace(/\s+/g, " "),
    tipo: tipoDe(m.archivo), activa: S.archivo === m.archivo,
    abrir: () => abrirMaquina(m.archivo),
  }));
  if (S.subido) {
    fichas.push({
      clave: "subido", num: "↑", nom: S.subido.nombre, tipo: "archivo propio",
      activa: S.archivo === null,
      abrir: () => { S.archivo = null; ponerYaml(S.subido.yaml); renderFichas(); simular(S.subido.yaml); },
    });
  }
  for (const f of fichas) {
    E.fichas.append(h("button", {
      class: "ficha", role: "tab", "aria-selected": String(f.activa),
      onclick: () => { if (!f.activa) f.abrir(); },
    }, h("span", { class: "num" }, f.num), h("span", { class: "nom" }, f.nom),
       h("span", { class: "tipo" }, f.tipo)));
  }
  E.pieArchivo.textContent = S.archivo ? "maquinas/" + S.archivo : (S.subido?.nombre || "");
}

function renderEntradas() {
  E.entradas.replaceChildren();
  S.resultados.forEach((r, i) => {
    let marca = h("span", { class: "marca no", title: "rechazada" }, "✕");
    if (r.aceptada) marca = h("span", { class: "marca si", title: "aceptada" }, "✓");
    else if (r.motivo === "limite_pasos") marca = h("span", { class: "marca", title: "no se detuvo" }, "∞");
    const info = r.motivo === "entrada_invalida"
      ? "fuera de Σ"
      : `|w|=${[...r.entrada].length} · ${r.pasos} pasos`;
    E.entradas.append(h("button", {
      class: "entrada" + (r.propia ? " propia-res" : ""), role: "tab",
      "aria-selected": String(i === S.sel),
      onclick: () => seleccionar(i),
    }, marca, h("span", { class: "w" }, r.entrada || "ε"), h("span", { class: "info" }, info)));
  });
}

function seleccionar(i) {
  pausar();
  S.sel = i;
  [...E.entradas.children].forEach((b, k) => b.setAttribute("aria-selected", String(k === i)));
  construirCinta();
  construirIds();
  E.tiempo.max = ultimoPaso();
  E.total.textContent = ultimoPaso();
  S.pasoPintado = null;
  E.sello.hidden = true;
  irA(0);
}

// ======================================================================
// maquina: descripcion, definicion formal, tabla delta, diagrama
// ======================================================================

function renderMaquina() {
  const m = S.maquina;
  E.descripcion.textContent = m.descripcion || "";
  E.cacheCaja.hidden = !m.usaCache;
  renderFormal();
  renderDelta();
  construirGrafo();
}

function simbolos(lista, clase = "") {
  return lista.map((x) => h("span", { class: "simb " + clase }, x));
}

function renderFormal() {
  const m = S.maquina;
  const fila = (dt, ...dd) => [h("dt", {}, dt), h("dd", {}, ...dd)];
  const llaves = (xs) => ["{", ...xs, "}"];
  E.formal.replaceChildren(h("dl", { class: "formal" },
    fila("Q", llaves(simbolos(m.estados, "estado")),
         h("small", {}, `${m.estados.length} estados`)),
    fila("Σ", llaves(simbolos(m.alfabetoEntrada)), h("small", {}, "alfabeto de entrada")),
    fila("Γ", llaves(simbolos(m.alfabetoCinta)),
         h("small", {}, "alfabeto de la cinta: Σ más los símbolos de trabajo y el blanco")),
    fila("q₀", simbolos([m.inicial], "estado")),
    fila("B", simbolos([m.blanco]), h("small", {}, "símbolo blanco")),
    fila("F", llaves(simbolos(m.aceptacion, "estado acepta"))),
    fila("δ", h("span", {}, `${m.transiciones.length} reglas`),
         h("small", {}, m.usaCache
           ? "el control finito guarda un símbolo (cache): δ([q, c], X) = ([p, c′], Y, D). " +
             "En el YAML read = [X, c] y write = [c′, Y]."
           : "δ(q, X) = (p, Y, D) con D ∈ {L, R, S}")),
  ));
}

function renderDelta() {
  const m = S.maquina;
  const cc = m.usaCache;
  const cab = ["estado", cc && "cache", "lee", "", "siguiente", cc && "cache′", "escribe", "mueve", "línea"]
    .filter((x) => x !== false);
  const cuerpo = h("tbody");
  S.filasDelta = [];
  let previo = null;
  m.transiciones.forEach((t) => {
    const celdas = [
      h("td", { class: "q" }, t.estado), cc && h("td", { class: "c" }, t.cacheLee),
      h("td", {}, t.lee), h("td", { class: "flecha" }, "→"),
      h("td", { class: "q" }, t.siguiente), cc && h("td", { class: "c" }, t.cacheEscribe),
      h("td", {}, t.escribe), h("td", { class: "m" }, t.mueve),
      h("td", { class: "ln" }, t.linea ?? ""),
    ].filter((x) => x !== false);
    const tr = h("tr", { class: previo !== null && previo !== t.estado ? "grupo" : "" }, celdas);
    previo = t.estado;
    S.filasDelta.push(tr);
    cuerpo.append(tr);
  });
  E.delta.replaceChildren(h("div", { class: "tabla-delta" },
    h("table", {}, h("thead", {}, h("tr", {}, cab.map((c) => h("th", {}, c)))), cuerpo)));
}

// ---------- diagrama de estados ----------------------------------------

const R = 25;          // radio de los nodos
const COL = 140;       // separacion entre capas
const FIL = 118;       // separacion dentro de una capa

function firma(m) {
  return "mt.pos." + (m.nombre || "") + "|" + m.estados.join(",");
}

/* Capas por BFS desde el estado inicial y luego unas pasadas de baricentro
   para ordenar cada capa y que se crucen menos aristas. */
function acomodar(m) {
  const vecinos = Object.fromEntries(m.estados.map((q) => [q, new Set()]));
  for (const t of m.transiciones) {
    if (t.estado !== t.siguiente) {
      vecinos[t.estado].add(t.siguiente);
      vecinos[t.siguiente].add(t.estado);
    }
  }
  const salida = Object.fromEntries(m.estados.map((q) => [q, []]));
  for (const t of m.transiciones) if (t.estado !== t.siguiente) salida[t.estado].push(t.siguiente);

  const capa = { [m.inicial]: 0 };
  const cola = [m.inicial];
  while (cola.length) {
    const q = cola.shift();
    for (const p of salida[q]) if (capa[p] === undefined) { capa[p] = capa[q] + 1; cola.push(p); }
  }
  let max = Math.max(0, ...Object.values(capa));
  for (const q of m.estados) if (capa[q] === undefined) capa[q] = max + 1;

  const capas = [];
  for (const q of m.estados) (capas[capa[q]] ||= []).push(q);
  const filas = capas.filter(Boolean);
  const indice = {};
  const reindexar = () => filas.forEach((c) => c.forEach((q, k) => { indice[q] = k - (c.length - 1) / 2; }));
  reindexar();
  for (let vuelta = 0; vuelta < 6; vuelta++) {
    const orden = vuelta % 2 ? [...filas].reverse() : filas;
    for (const c of orden) {
      const bary = (q) => {
        const vs = [...vecinos[q]].filter((p) => capa[p] !== capa[q]);
        return vs.length ? vs.reduce((a, p) => a + indice[p], 0) / vs.length : indice[q];
      };
      const b = Object.fromEntries(c.map((q) => [q, bary(q)]));
      c.sort((x, y) => b[x] - b[y]);
      reindexar();
    }
  }

  const pos = {};
  filas.forEach((c, i) => c.forEach((q, k) => {
    pos[q] = { x: i * COL, y: (k - (c.length - 1) / 2) * FIL };
  }));
  return { pos, capa };
}

function construirGrafo() {
  const m = S.maquina;
  const auto = acomodar(m);
  S.capas = auto.capa;
  const guardadas = leer(firma(m));
  S.pos = guardadas && m.estados.every((q) => guardadas[q]) ? guardadas : auto.pos;
  dibujarGrafo();
}

function etiquetaRegla(t, m) {
  const conCache = m.usaCache && !(t.cacheLee === m.blanco && t.cacheEscribe === m.blanco);
  const partes = [[t.lee]];
  if (conCache) partes.push(["·" + t.cacheLee, "c"]);
  partes.push(["→" + t.escribe]);
  if (conCache) partes.push(["·" + t.cacheEscribe, "c"]);
  partes.push(["," + t.mueve]);
  return partes;
}

function encuadrar() {
  const xs = Object.values(S.pos).map((p) => p.x);
  const ys = Object.values(S.pos).map((p) => p.y);
  const x0 = Math.min(...xs) - 110, x1 = Math.max(...xs) + 100;
  const y0 = Math.min(...ys) - 120, y1 = Math.max(...ys) + 120;
  ponerVista({ x: x0, y: y0, w: x1 - x0, h: y1 - y0 });
}

function ponerVista(v) {
  S.vista = v;
  E.grafo.setAttribute("viewBox", `${v.x} ${v.y} ${v.w} ${v.h}`);
}

// ctrl/cmd + rueda = zoom alrededor del cursor, arrastrar el fondo = mover, doble clic = encuadrar
function navegableGrafo() {
  E.grafo.addEventListener("wheel", (ev) => {
    // sin modificador la rueda sigue bajando la pagina (salvo en pantalla completa)
    if (!S.vista || !(ev.ctrlKey || ev.metaKey || document.fullscreenElement)) return;
    ev.preventDefault();
    const p = puntoSvg(ev);
    const f = Math.exp(ev.deltaY * 0.0015);
    const v = S.vista;
    ponerVista({ x: p.x - (p.x - v.x) * f, y: p.y - (p.y - v.y) * f, w: v.w * f, h: v.h * f });
  }, { passive: false });
  let arrastre = null;
  E.grafo.addEventListener("pointerdown", (ev) => {
    if (ev.target.closest(".nodo")) return;
    arrastre = { p: puntoSvg(ev) };
    E.grafo.setPointerCapture(ev.pointerId);
    E.grafo.classList.add("moviendo");
  });
  E.grafo.addEventListener("pointermove", (ev) => {
    if (!arrastre) return;
    const p = puntoSvg(ev);
    const v = S.vista;
    ponerVista({ ...v, x: v.x - (p.x - arrastre.p.x), y: v.y - (p.y - arrastre.p.y) });
  });
  const fin = () => { arrastre = null; E.grafo.classList.remove("moviendo"); };
  E.grafo.addEventListener("pointerup", fin);
  E.grafo.addEventListener("pointercancel", fin);
  E.grafo.addEventListener("dblclick", (ev) => { if (!ev.target.closest(".nodo")) encuadrar(); });
}

function dibujarGrafo() {
  const m = S.maquina;
  E.grafo.replaceChildren();
  encuadrar();

  const defs = s("defs");
  for (const [id, color] of [["punta", "var(--tinta-media)"], ["punta-usada", "var(--senal)"]]) {
    const mk = s("marker", { id, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 7,
                             markerHeight: 7, orient: "auto-start-reverse" });
    mk.append(s("path", { d: "M0,0 L10,5 L0,10 L2.5,5 z", fill: color }));
    defs.append(mk);
  }
  E.grafo.append(defs);

  S.capaAristas = s("g", { class: "aristas" });
  S.capaNodos = s("g", { class: "nodos" });
  E.grafo.append(S.capaAristas, S.capaNodos);

  S.nodos = {};
  for (const q of m.estados) {
    const g = s("g", { class: "nodo", "data-q": q });
    g.append(s("circle", { class: "halo", r: R + 7 }));
    g.append(s("circle", { class: "borde", r: R, filter: "url(#tinta)" }));
    if (m.aceptacion.includes(q)) g.append(s("circle", { class: "doble", r: R - 5, filter: "url(#tinta)" }));
    const tx = s("text");
    tx.textContent = q;
    if (q.length > 3) tx.style.fontSize = Math.max(9, 15 - (q.length - 3) * 2) + "px";
    g.append(tx);
    arrastrable(g, q);
    S.capaNodos.append(g);
    S.nodos[q] = g;
  }
  colocarNodos();
  dibujarAristas();
}

function colocarNodos() {
  for (const [q, g] of Object.entries(S.nodos)) {
    g.setAttribute("transform", `translate(${S.pos[q].x},${S.pos[q].y})`);
  }
}

function dibujarAristas() {
  const m = S.maquina;
  S.capaAristas.replaceChildren();
  S.aristas = {};
  S.lineaRegla = {};

  // inicio
  const p0 = S.pos[m.inicial];
  const ini = s("g", { class: "inicial" });
  ini.append(s("path", { d: `M${p0.x - R - 58},${p0.y} L${p0.x - R - 3},${p0.y}`,
                         "marker-end": "url(#punta)" }));
  const txi = s("text", { x: p0.x - R - 58, y: p0.y - 8 });
  txi.textContent = "inicio";
  ini.append(txi);
  S.capaAristas.append(ini);

  const grupos = new Map();
  m.transiciones.forEach((t, k) => {
    const clave = t.estado + "\u0000" + t.siguiente;
    if (!grupos.has(clave)) grupos.set(clave, []);
    grupos.get(clave).push(k);
  });
  const ys = Object.values(S.pos).map((p) => p.y);
  const centroY = (Math.min(...ys) + Math.max(...ys)) / 2;

  for (const [clave, reglas] of grupos) {
    const [de, a] = clave.split("\u0000");
    const A = S.pos[de], B = S.pos[a];
    const g = s("g", { class: "arista" });
    let d, ancla, lado;

    if (de === a) {
      lado = A.y > centroY + 1 ? 1 : -1;               // lazo hacia afuera del dibujo
      const y1 = A.y + lado * (R - 3), y2 = A.y + lado * (R + 52);
      d = `M${A.x - 11},${y1} C${A.x - 40},${y2} ${A.x + 40},${y2} ${A.x + 11},${y1 + lado * 2}`;
      ancla = { x: A.x, y: A.y + lado * (R + 46) };
    } else {
      const dx = B.x - A.x, dy = B.y - A.y, L = Math.hypot(dx, dy) || 1;
      const nx = -dy / L, ny = dx / L;
      const hayVuelta = grupos.has(a + "\u0000" + de);
      const salto = Math.abs((S.capas[a] ?? 0) - (S.capas[de] ?? 0));
      let curva = 0;
      if (hayVuelta) curva = 30;
      else if (salto !== 1 || Math.abs(dy) > 1 && Math.abs(dx) < 1) curva = 34 + L * 0.16;
      const c = { x: (A.x + B.x) / 2 + nx * curva, y: (A.y + B.y) / 2 + ny * curva };
      const ua = unidad(c.x - A.x, c.y - A.y), ub = unidad(c.x - B.x, c.y - B.y);
      const i = { x: A.x + ua.x * R, y: A.y + ua.y * R };
      const f = { x: B.x + ub.x * (R + 2), y: B.y + ub.y * (R + 2) };
      d = `M${i.x},${i.y} Q${c.x},${c.y} ${f.x},${f.y}`;
      const cima = { x: (i.x + 2 * c.x + f.x) / 4, y: (i.y + 2 * c.y + f.y) / 4 };
      // la etiqueta va del lado convexo; en aristas rectas, arriba
      let sx = nx, sy = ny;
      if (curva === 0 && ny > 0) { sx = -nx; sy = -ny; }
      lado = sy >= 0 ? 1 : -1;
      ancla = { x: cima.x + sx * 9, y: cima.y + sy * 9 };
    }

    g.append(s("path", { d, "marker-end": "url(#punta)", filter: "url(#tinta)" }));

    const MAX = 5;
    const visibles = reglas.length > MAX ? reglas.slice(0, MAX - 1) : reglas;
    const lineas = visibles.length + (reglas.length > visibles.length ? 1 : 0);
    const alto = 13.5;
    const y0 = lado > 0 ? ancla.y + 9 : ancla.y - (lineas - 1) * alto - 2;
    const tx = s("text", { x: ancla.x, y: y0, "text-anchor": "middle" });
    visibles.forEach((k, j) => {
      const linea = s("tspan", { x: ancla.x, dy: j === 0 ? 0 : alto });
      for (const [txt, cls] of etiquetaRegla(m.transiciones[k], m)) {
        const parte = s("tspan", cls ? { class: cls } : {});
        parte.textContent = txt;
        linea.append(parte);
      }
      S.lineaRegla[k] = linea;
      tx.append(linea);
    });
    if (reglas.length > visibles.length) {
      const mas = s("tspan", { x: ancla.x, dy: alto, class: "mas" });
      mas.textContent = `+${reglas.length - visibles.length} más`;
      tx.append(mas);
    }
    g.append(tx);
    S.capaAristas.append(g);
    for (const k of reglas) S.aristas[k] = g;
  }
  resaltarGrafo();
}

function unidad(x, y) {
  const l = Math.hypot(x, y) || 1;
  return { x: x / l, y: y / l };
}

function arrastrable(g, q) {
  let inicio = null;
  g.addEventListener("pointerdown", (ev) => {
    const p = puntoSvg(ev);
    inicio = { dx: p.x - S.pos[q].x, dy: p.y - S.pos[q].y };
    g.setPointerCapture(ev.pointerId);
  });
  g.addEventListener("pointermove", (ev) => {
    if (!inicio) return;
    const p = puntoSvg(ev);
    S.pos[q] = { x: Math.round(p.x - inicio.dx), y: Math.round(p.y - inicio.dy) };
    colocarNodos();
    dibujarAristas();
  });
  const soltar = () => {
    if (!inicio) return;
    inicio = null;
    guardar(firma(S.maquina), S.pos);
  };
  g.addEventListener("pointerup", soltar);
  g.addEventListener("pointercancel", soltar);
}

function puntoSvg(ev) {
  const pt = E.grafo.createSVGPoint();
  pt.x = ev.clientX;
  pt.y = ev.clientY;
  return pt.matrixTransform(E.grafo.getScreenCTM().inverse());
}

function resaltarGrafo() {
  const r = actual();
  if (!r || !S.nodos) return;
  const ids = r.ids;
  const d = ids[S.paso];
  const visitados = new Set();
  for (let k = 0; k <= S.paso && k < ids.length; k++) visitados.add(ids[k].estado);
  for (const [q, g] of Object.entries(S.nodos)) {
    g.classList.toggle("actual", !!d && d.estado === q);
    g.classList.toggle("visitado", visitados.has(q));
  }
  S.capaAristas.querySelectorAll(".usada").forEach((n) => {
    n.classList.remove("usada");
    n.querySelector("path").setAttribute("marker-end", "url(#punta)");
  });
  S.capaAristas.querySelectorAll("tspan[style]").forEach((n) => n.removeAttribute("style"));
  if (d && d.regla !== null) {
    const g = S.aristas[d.regla];
    if (g) {
      g.classList.add("usada");
      g.querySelector("path").setAttribute("marker-end", "url(#punta-usada)");
      const linea = S.lineaRegla[d.regla];
      if (linea) linea.setAttribute("style", "font-weight:700;text-decoration:underline");
    }
  }
}

// ======================================================================
// cinta
// ======================================================================

function construirCinta() {
  const r = actual();
  E.cinta.replaceChildren();
  E.posiciones.replaceChildren();
  E.aviso.hidden = true;
  S.cinta = null;
  if (!r || !r.ids.length) {
    E.aviso.hidden = false;
    E.aviso.textContent = r ? "entrada inválida: " + r.detalle : "";
    return;
  }
  let lo = Infinity, hi = -Infinity;
  for (const d of r.ids) {
    lo = Math.min(lo, d.inicio, d.cabeza);
    hi = Math.max(hi, d.inicio + d.cinta.length - 1, d.cabeza);
  }
  const prueba = h("div", { class: "celda" });
  E.cinta.append(prueba);
  const W = anchoCelda();
  prueba.remove();
  const extra = Math.ceil(E.marco.clientWidth / W / 2) + 3;
  lo -= extra;
  hi += extra;

  const celdas = [];
  const frag = document.createDocumentFragment();
  const fragPos = document.createDocumentFragment();
  for (let i = lo; i <= hi; i++) {
    const sp = h("span", { class: "s" });
    const c = h("div", { class: "celda" }, sp);
    frag.append(c);
    celdas.push({ c, s: sp, v: null });
    fragPos.append(h("span", { class: i === 0 ? "cero" : "" }, i % 5 === 0 || i === 0 ? String(i) : ""));
  }
  E.cinta.append(frag);
  E.posiciones.append(fragPos);
  S.cinta = { lo, hi, W, celdas };
}

function pintarCinta(d, anterior) {
  const m = S.maquina;
  const { lo, W, celdas } = S.cinta;
  for (let k = 0; k < celdas.length; k++) {
    const pos = lo + k;
    const j = pos - d.inicio;
    const v = j >= 0 && j < d.cinta.length ? d.cinta[j] : m.blanco;
    const cel = celdas[k];
    if (v !== cel.v) {
      cel.v = v;
      cel.s.textContent = v;
      cel.c.classList.toggle("blanco", v === m.blanco);
      cel.c.classList.toggle("marcada", v !== m.blanco && !m.alfabetoEntrada.includes(v));
    }
    cel.c.classList.toggle("bajo", pos === d.cabeza);
  }
  // el simbolo recien escrito "se entinta" cuando se avanza un solo paso
  if (anterior && d.paso === anterior.paso + 1 && d.regla !== null) {
    const t = m.transiciones[d.regla];
    if (t.escribe !== t.lee) {
      const cel = celdas[anterior.cabeza - lo];
      if (cel) { cel.c.classList.remove("tinta"); void cel.c.offsetWidth; cel.c.classList.add("tinta"); }
    }
  }
  const x = E.marco.clientWidth / 2 - (d.cabeza - lo) * W - W / 2;
  E.cinta.style.transform = `translateX(${x}px)`;
  E.posiciones.style.transform = `translateX(${x}px)`;
}

// ======================================================================
// paso actual
// ======================================================================

function textoRegla(t, m) {
  const q = (x) => `<span class="q">${esc(x)}</span>`;
  const c = (x) => `<span class="c">${esc(x)}</span>`;
  if (m.usaCache) {
    return `δ([${q(t.estado)}, ${c(t.cacheLee)}], ${esc(t.lee)}) = ` +
           `([${q(t.siguiente)}, ${c(t.cacheEscribe)}], ${esc(t.escribe)}, <span class="m">${t.mueve}</span>)`;
  }
  return `δ(${q(t.estado)}, ${esc(t.lee)}) = (${q(t.siguiente)}, ${esc(t.escribe)}, <span class="m">${t.mueve}</span>)`;
}

function esc(x) {
  return String(x).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
}

function irA(p) {
  const r = actual();
  if (!r) return;
  const fin = ultimoPaso();
  p = Math.max(0, Math.min(fin, p));
  const previo = S.pasoPintado;
  S.paso = p;
  E.tiempo.value = p;
  E.paso.textContent = p;
  E.bInicio.disabled = E.bAtras.disabled = p === 0;
  E.bFin.disabled = E.bAdelante.disabled = p === fin;

  const d = r.ids[p];
  if (!d) {
    E.estado.textContent = "—";
    E.regla.textContent = r.detalle;
    marcarIds(p);
    ponerSello(r, false);
    return;
  }
  const anterior = previo !== null ? r.ids[previo] : null;
  if (S.cinta) pintarCinta(d, anterior);

  E.estado.textContent = d.estado;
  if (E.cache.textContent !== d.cache) {
    E.cache.textContent = d.cache;
    E.cacheCaja.classList.remove("cambia");
    void E.cacheCaja.offsetWidth;
    E.cacheCaja.classList.add("cambia");
  }
  E.regla.innerHTML = d.regla === null ? "configuración inicial" : textoRegla(S.maquina.transiciones[d.regla], S.maquina);

  marcarIds(p);
  resaltarGrafo();
  S.filasDelta.forEach((tr, k) => tr.classList.toggle("actual", k === d.regla));

  if (p === fin) ponerSello(r, previo !== fin);
  else E.sello.hidden = true;
  S.pasoPintado = p;
}

function ponerSello(r, golpe) {
  let clase = "no", texto = "rechazada";
  if (r.aceptada) { clase = "si"; texto = "aceptada"; }
  else if (r.motivo === "limite_pasos") { clase = "alto"; texto = "no se detuvo"; }
  const salida = r.ids.length ? `${r.pasos} pasos · cinta: ${r.cintaFinal || "vacía"}` : "";
  E.sello.className = "sello " + clase;
  E.sello.replaceChildren(texto, h("small", {}, salida), h("small", {}, r.detalle));
  E.sello.hidden = false;
  if (golpe) { void E.sello.offsetWidth; E.sello.classList.add("golpe"); }
}

// ======================================================================
// impresion de IDs
// ======================================================================

function construirIds() {
  const r = actual();
  const m = S.maquina;
  E.ids.replaceChildren();
  S.filasIds = [];
  if (!r) return;
  const frag = document.createDocumentFragment();
  r.ids.forEach((d, k) => {
    const li = h("li", { onclick: () => { pausar(); irA(k); } },
      h("span", { class: "n" }, String(d.paso).padStart(3, "0")),
      h("span", { class: "t" }, k === 0 ? "" : "⊢"),
      idFormateada(d, m));
    if (k === r.ids.length - 1) li.classList.add("fin");
    frag.append(li);
    S.filasIds.push(li);
  });
  E.ids.append(frag);
  S.idsMarcado = null;
}

function idFormateada(d, m) {
  const t = d.texto;
  const a = t.indexOf("["), b = t.indexOf("]") + 1;
  const bajo = d.cinta[d.cabeza - d.inicio] ?? m.blanco;
  const resto = t.slice(b);
  const span = h("span", {}, t.slice(0, a), "[", h("span", { class: "q" }, d.estado));
  if (m.usaCache) span.append(", ", h("span", { class: "c" }, d.cache));
  span.append("]", h("span", { class: "h" }, resto.slice(0, bajo.length)), resto.slice(bajo.length));
  return span;
}

function marcarIds(p) {
  const filas = S.filasIds;
  if (!filas.length) return;
  const previo = S.idsMarcado;
  if (previo === null) {
    filas.forEach((li, k) => li.classList.toggle("futuro", k > p));
  } else {
    const [a, b] = previo < p ? [previo, p] : [p, previo];
    for (let k = a; k <= b; k++) filas[k].classList.toggle("futuro", k > p);
    filas[previo]?.classList.remove("actual");
  }
  filas[p].classList.add("actual");
  // el teletipo "teclea" la linea nueva solo cuando se avanza de a un paso
  filas[previo ?? 0]?.classList.remove("nuevo");
  if (previo !== null && p === previo + 1) filas[p].classList.add("nuevo");
  S.idsMarcado = p;
  // lo ultimo impreso siempre queda abajo, como el papel saliendo de la maquina
  const li = filas[p];
  const objetivo = li.offsetTop + li.offsetHeight - E.papel.clientHeight + 26;
  E.papel.scrollTo({ top: Math.max(0, objetivo), behavior: S.reproduciendo && S.vel > 12 ? "auto" : "smooth" });
}

// ======================================================================
// reproduccion
// ======================================================================

function reproducir() {
  if (!actual()?.ids.length) return;
  if (S.paso >= ultimoPaso()) irA(0);
  S.reproduciendo = true;
  E.bPlay.textContent = "❚❚";
  E.bPlay.setAttribute("aria-label", "Pausar");
  let ultimo = performance.now(), acumulado = 0;
  const tic = (t) => {
    if (!S.reproduciendo) return;
    acumulado += ((t - ultimo) / 1000) * S.vel;
    ultimo = t;
    const n = Math.floor(acumulado);
    if (n > 0) {
      acumulado -= n;
      irA(S.paso + n);
      if (S.paso >= ultimoPaso()) { pausar(); return; }
    }
    S.raf = requestAnimationFrame(tic);
  };
  S.raf = requestAnimationFrame(tic);
}

function pausar() {
  S.reproduciendo = false;
  cancelAnimationFrame(S.raf);
  E.bPlay.textContent = "▶";
  E.bPlay.setAttribute("aria-label", "Reproducir");
}

function ajustarVelocidad(v) {
  S.vel = v;
  E.velTxt.textContent = v;
  document.documentElement.style.setProperty("--dur", Math.min(0.28, 0.8 / v).toFixed(3) + "s");
  guardar("mt.vel", v);
}

// ======================================================================
// editor YAML
// ======================================================================

function ponerYaml(texto) {
  E.yaml.value = texto;
  actualizarNumeros();
}

function actualizarNumeros(lineaError = null) {
  const n = E.yaml.value.split("\n").length;
  E.numeros.replaceChildren();
  for (let i = 1; i <= n; i++) {
    E.numeros.append(i === lineaError ? h("span", { class: "err" }, String(i)) : String(i), "\n");
  }
  E.numeros.scrollTop = E.yaml.scrollTop;
}

function mostrarError(d) {
  E.error.textContent = (d.linea ? `línea ${d.linea}: ` : "") + d.error;
  actualizarNumeros(d.linea || null);
  abrirPestana("p-yaml");
  if (d.linea) {
    const lineas = E.yaml.value.split("\n");
    const ini = lineas.slice(0, d.linea - 1).join("\n").length + (d.linea > 1 ? 1 : 0);
    E.yaml.focus();
    E.yaml.setSelectionRange(ini, ini + (lineas[d.linea - 1] || "").length);
    E.yaml.scrollTop = Math.max(0, (d.linea - 6) * 20);
  }
  E.yaml.scrollIntoView({ behavior: "smooth", block: "center" });
}

function limpiarError() {
  E.error.textContent = "";
  actualizarNumeros();
}

function abrirPestana(id) {
  document.querySelectorAll(".pestanas [role=tab]").forEach((b) => {
    const activa = b.dataset.panel === id;
    b.setAttribute("aria-selected", String(activa));
    document.getElementById(b.dataset.panel).hidden = !activa;
  });
}

async function cargarArchivo(file) {
  const texto = await file.text();
  S.subido = { nombre: file.name, yaml: texto };
  S.archivo = null;
  ponerYaml(texto);
  renderFichas();
  await simular(texto);
}

// ======================================================================
// eventos
// ======================================================================

E.bInicio.onclick = () => { pausar(); irA(0); };
E.bAtras.onclick = () => { pausar(); irA(S.paso - 1); };
E.bAdelante.onclick = () => { pausar(); irA(S.paso + 1); };
E.bFin.onclick = () => { pausar(); irA(ultimoPaso()); };
E.bPlay.onclick = () => (S.reproduciendo ? pausar() : reproducir());
E.tiempo.oninput = () => { pausar(); irA(+E.tiempo.value); };
E.velocidad.oninput = () => ajustarVelocidad(+E.velocidad.value);

E.propia.onsubmit = async (ev) => {
  ev.preventDefault();
  const w = E.cadena.value.trim();
  if (!S.yaml) return;
  if (await simular(S.yaml, { entradas: [w], agregar: true })) E.cadena.value = "";
};

E.aplicar.onclick = async () => {
  if (S.archivo === null && S.subido) S.subido.yaml = E.yaml.value;
  await simular(E.yaml.value);
};
E.yaml.addEventListener("input", () => actualizarNumeros());
E.yaml.addEventListener("scroll", () => { E.numeros.scrollTop = E.yaml.scrollTop; });
E.yaml.addEventListener("keydown", (ev) => {
  if (ev.key === "Tab") {
    ev.preventDefault();
    E.yaml.setRangeText("  ", E.yaml.selectionStart, E.yaml.selectionEnd, "end");
    actualizarNumeros();
  } else if (ev.key === "Enter" && (ev.metaKey || ev.ctrlKey)) {
    ev.preventDefault();
    E.aplicar.click();
  }
});

document.querySelectorAll(".pestanas [role=tab]").forEach((b) => {
  b.onclick = () => abrirPestana(b.dataset.panel);
});

E.archivo.onchange = () => { if (E.archivo.files[0]) cargarArchivo(E.archivo.files[0]); E.archivo.value = ""; };

let arrastres = 0;
window.addEventListener("dragenter", (ev) => { ev.preventDefault(); arrastres++; document.body.classList.add("soltando"); });
window.addEventListener("dragleave", () => { if (--arrastres <= 0) { arrastres = 0; document.body.classList.remove("soltando"); } });
window.addEventListener("dragover", (ev) => ev.preventDefault());
window.addEventListener("drop", (ev) => {
  ev.preventDefault();
  arrastres = 0;
  document.body.classList.remove("soltando");
  const f = ev.dataTransfer.files[0];
  if (f) cargarArchivo(f);
});

document.addEventListener("keydown", (ev) => {
  if (ev.target.closest("input, textarea") || ev.metaKey || ev.ctrlKey || ev.altKey) return;
  if (ev.key === " ") { ev.preventDefault(); S.reproduciendo ? pausar() : reproducir(); }
  else if (ev.key === "ArrowRight") { pausar(); irA(S.paso + 1); }
  else if (ev.key === "ArrowLeft") { pausar(); irA(S.paso - 1); }
  else if (ev.key === "Home") { pausar(); irA(0); }
  else if (ev.key === "End") { pausar(); irA(ultimoPaso()); }
});

let espera = 0;
window.addEventListener("resize", () => {
  clearTimeout(espera);
  espera = setTimeout(() => {
    if (!actual()) return;
    construirCinta();
    S.pasoPintado = null;
    if (S.cinta) pintarCinta(actual().ids[S.paso], null);
  }, 120);
});

// tema: papel (claro) o cianotipo (oscuro); sin eleccion se sigue al sistema
function temaActual() {
  const elegido = document.documentElement.dataset.tema;
  if (elegido) return elegido;
  return matchMedia("(prefers-color-scheme: dark)").matches ? "cianotipo" : "papel";
}
function pintarBotonTema() {
  $("#tema").textContent = temaActual() === "papel" ? "◐ cianotipo" : "◑ papel";
}
$("#tema").onclick = () => {
  const nuevo = temaActual() === "papel" ? "cianotipo" : "papel";
  document.documentElement.dataset.tema = nuevo;
  guardar("mt.tema", nuevo);
  pintarBotonTema();
};
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", pintarBotonTema);
pintarBotonTema();

navegableGrafo();
$("#reacomodar").onclick = () => {
  try { localStorage.removeItem(firma(S.maquina)); } catch (_) {}
  construirGrafo();
};
$("#ampliar").onclick = () => {
  const sec = $(".diagrama");
  if (document.fullscreenElement) document.exitFullscreen();
  else sec.requestFullscreen?.();
};
document.addEventListener("fullscreenchange", () => setTimeout(encuadrar, 50));

iniciar();
