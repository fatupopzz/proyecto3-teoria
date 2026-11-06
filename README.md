# Proyecto 3: Simulador de Máquinas de Turing

Teoría de la Computación, noviembre 2025.

Simulador de Máquinas de Turing de **una cinta**. Lee la descripción formal de la MT desde
un archivo YAML, simula cada cadena configurada, muestra la lista completa de
**descripciones instantáneas (IDs)** e indica si la cadena fue **aceptada** o **rechazada**
junto con la configuración final de la cinta.

Hay dos formas de usarlo:

- **Terminal** (`main.py`): definición formal, tabla δ, IDs paso a paso, cinta final y
  una animación opcional de la cabeza moviéndose sobre la cinta.
- **Visor web** (`app.py`): la cinta se desplaza bajo la cabeza, el diagrama de estados
  resalta la regla aplicada y las IDs se imprimen como en un teletipo, con un sello de
  ACEPTADA o RECHAZADA cuando la MT se detiene.

Toda la simulación corre en Python, en el paquete `mt`. El visor web solo reproduce
las IDs que recibe.

**En línea:** <https://fatupopzz.github.io/proyecto3-teoria/>. En GitHub Pages no hay
servidor, así que el visor carga [Pyodide](https://pyodide.org) (CPython compilado a
WebAssembly) y ejecuta **los mismos archivos de `mt/`** dentro del navegador. La primera
carga tarda unos segundos mientras descarga Python.

**Video:** <https://youtu.be/kTzLNvqlVE4>

---

## Instalación

Requiere Python 3.10 o superior.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Uso

### Terminal

```bash
python main.py maquinas/reconocedora_ww.yaml
python main.py maquinas/alteradora_suma_binaria.yaml
```

| Opción | Qué hace |
|---|---|
| `-e CADENA` | Simula esa cadena en lugar de las `inputs` del YAML (se puede repetir) |
| `-a`, `--animar` | Reproduce cada ejecución paso a paso sobre la cinta |
| `-v SEG` | Segundos entre pasos al animar (por defecto `0.12`) |
| `-c`, `--compacto` | Muestra solo el resultado, sin la lista de IDs |
| `-g CARPETA` | Guarda las IDs en `CARPETA/<maquina>.txt` |
| `--max-pasos N` | Pasos antes de declarar que la MT no se detuvo (por defecto 10 000) |
| `--sin-delta` | No imprime la tabla de transiciones |

```bash
python main.py maquinas/reconocedora_ww.yaml -e abbabb -e abbab
python main.py maquinas/alteradora_suma_binaria.yaml --animar -v 0.08
```

### Visor web

```bash
python app.py
```

Abrir <http://127.0.0.1:5050>.

En escritorio todo cabe en una pantalla:

- **Fichas** (arriba): cambian de máquina. **abrir .yaml** carga un archivo propio (también
  se puede arrastrar y soltar sobre la página).
- **Riel de sujetos** (izquierda): cada boleto es una de las `inputs` del YAML con su
  resultado y número de pasos; en *otra cadena…* se simula una cadena nueva sin tocar el
  archivo.
- **Cinta** (arriba al centro): la cinta se desliza bajo la cabeza; debajo, estado, cache,
  regla aplicada, paso y los controles. `espacio` reproduce o pausa, `←` `→` avanzan un
  paso, `Home` y `End` van al inicio y al final.
- **Control finito** y **descripciones instantáneas** (abajo): el diagrama resalta la
  regla usada; los estados se arrastran (la posición se recuerda), `Ctrl/⌘ + rueda`
  acerca, doble clic encuadra y **ampliar** lo pone en pantalla completa. Un clic sobre una
  ID lleva a ese paso.
- **Expediente** (lengüeta a la derecha): definición formal, tabla δ y editor YAML
  (`Ctrl/⌘ + Enter` carga los cambios; los errores marcan la línea). `Esc` lo cierra.
- **◐** alterna entre el *expediente* en papel y la *visión nocturna*, donde las tres
  zonas se vuelven cámaras de vigilancia (CAM 01–03) con código de tiempo que avanza con
  cada paso. La franja superior dice qué máquina corre y si el sujeto está en espera,
  registrando, en pausa, aceptado o rechazado.

### Versión estática (GitHub Pages)

```bash
python herramientas/construir_pages.py _site
python -m http.server 8765 --directory _site
```

Arma en `_site/` la página, el paquete `mt/` y las máquinas, y la página usa Pyodide en
lugar de Flask. El workflow `.github/workflows/pages.yml` corre las pruebas, construye
el sitio y lo publica en cada push a `master`.

### Pruebas

```bash
python -m pytest -q
```

Las pruebas comparan las máquinas contra la respuesta correcta calculada en Python:
**todas** las cadenas sobre {a, b} de longitud 0 a 10 para *ww* y palíndromos (2 047
cadenas cada una) y todas las sumas `x+y` con 0 ≤ x, y < 40 (1 600 sumas). También
cubren el parser: el ejemplo del enunciado, errores de definición y no determinismo.

---

## Formato del YAML

Es el formato del enunciado:

```yaml
mt:
  states: [q0, q1, q2, qf]
  input_alphabet: [a, b]
  tape_alphabet: [a, b, B, X, Y]
  initial_state: q0
  accept_states: [qf]
  transitions:
    - state: q0
      read: [a, B]
      write: [a, B]
      move: R
      next: q1
  inputs:
    - "aabb"
```

### El cache del estado

Como en el ejemplo del enunciado, el control finito puede **guardar un símbolo**: el
estado completo es el par `[q, c]`. Cada regla

```
δ([q, c], X) = ([p, c'], Y, D)
```

se escribe así:

| Clave | Contenido |
|---|---|
| `state` / `next` | `q` / `p` |
| `read` | `[X, c]`: símbolo leído en la cinta y valor actual del cache |
| `write` | `[c', Y]`: nuevo valor del cache y símbolo que se escribe en la cinta |
| `move` | `L`, `R` o `S` (quedarse) |

Con esto la regla del enunciado `read: [a, B]`, `write: [a, B]` es exactamente
`δ([q0, B], a) = ([q1, a], B, R)`: guarda la `a` en el cache y deja un blanco en la cinta.
El archivo `maquinas/ejemplo_enunciado.yaml` es ese ejemplo sin cambios.

Cuando una regla no toca el cache se puede escribir un solo símbolo: `read: a` equivale a
`[a, B]` y `write: X` equivale a `[B, X]`. Si una máquina nunca usa el cache, las IDs
siguen mostrando `[q, B]`.

### Claves opcionales

- `blank`: símbolo blanco (por defecto `B`).
- `name` y `description`: título y descripción que muestran la terminal y el visor.

### Validaciones

El parser rechaza el archivo, indicando la línea, si falta una clave; si Σ no está
contenido en Γ; si el blanco no está en Γ o está en Σ; si el estado inicial o los de
aceptación no están en Q; si una regla usa un estado o símbolo inexistente; si el
movimiento no es L/R/S; o si dos reglas tienen el mismo `(estado, cache, símbolo)`, es
decir, si la MT no es determinista.

Los símbolos se leen siempre como texto. PyYAML normalmente convierte `Y`, `N`, `on`
y `off` en booleanos y `0`/`1` en enteros, así que un alfabeto `[a, b, X, Y]` llegaría
como `['a', 'b', 'X', True]`. El cargador propio lo evita.

---

## Semántica de la simulación

1. La cinta empieza con la cadena de entrada a partir de la posición 0, la cabeza en
   la posición 0, el estado inicial y el cache en blanco.
2. Si el estado actual es de aceptación, la MT **se detiene y acepta**.
3. Si δ no está definida para `([q, c], X)`, la MT **se detiene y rechaza**.
4. Si no, se escribe, se mueve la cabeza, se cambian estado y cache, y se registra
   una nueva ID.
5. Si pasa el límite de pasos se reporta *no se detuvo* (el problema de la parada no
   permite decidir si ciclaría para siempre).

Las IDs usan la notación de Hopcroft, `X₁…Xᵢ₋₁ [q, c] Xᵢ…Xₙ`: el estado va justo
antes del símbolo que está bajo la cabeza y se recortan los blancos de los extremos,
salvo el que está bajo la cabeza.

```
[q0, B]abba ⊢ [q1, a]bba ⊢ b[q1, a]ba ⊢ bb[q1, a]a ⊢ bba[q1, a]B ⊢ bb[q2, a]a ⊢ …
```

---

## Máquinas

### 1. Reconocedora: L = { ww | w ∈ {a, b}⁺ } (`maquinas/reconocedora_ww.yaml`)

Acepta las cadenas cuya primera mitad es igual a la segunda (`abaaba` = `aba·aba`).
Este lenguaje **no es libre de contexto**, así que ningún autómata de pila lo reconoce.

| Fase | Estados | Qué hace |
|---|---|---|
| Encontrar la mitad | q0 – q3 | Marca alternadamente el primer símbolo sin marcar (a→X, b→Y) y el último, cerrando desde ambos extremos. Si al ir a la derecha ya no queda nada, la longitud es impar y rechaza. |
| Separar mitades | q4, q5 | Cuando q0 choca con una marca está al inicio de la segunda mitad: la regresa a minúsculas y vuelve al inicio. |
| Comparar | q6 – q8 | q6 toma el siguiente símbolo de la primera mitad, **lo guarda en el cache** y lo tacha con Z. q7 viaja cargándolo (`[q7, a]` o `[q7, b]`) hasta el primer símbolo sin tachar de la segunda mitad y solo sigue si coincide. q8 regresa. Si todo quedó tachado, acepta. |

41 reglas, 10 estados, Γ = {a, b, X, Y, Z, B}. Complejidad O(n²) pasos.

| Cadena | \|w\| | Resultado | Pasos | Motivo |
|---|---|---|---|---|
| `abaaba` | 6 | aceptada | 75 | w = aba |
| `babbbabb` | 8 | aceptada | 119 | w = babb |
| `aabbaabb` | 8 | aceptada | 119 | w = aabb |
| `abaab` | 5 | rechazada | 20 | longitud impar: δ([q2, B], X) no existe |
| `aabbab` | 6 | rechazada | 41 | aab ≠ bab: δ([q7, a], b) no existe |
| `ababbaba` | 8 | rechazada | 62 | abab ≠ baba: δ([q7, a], b) no existe |

### 2. Alteradora: suma binaria x + y (`maquinas/alteradora_suma_binaria.yaml`)

Recibe dos números binarios separados por `+` y deja en la cinta **solo su suma**,
con la cabeza al inicio del resultado: `101+11` → `1000`.

Suma columna por columna, de derecha a izquierda, con acarreo:

- **El acarreo vive en el nombre del estado**: la familia `f0 t0 m0 s0 p0` trabaja con
  acarreo 0 y `f1 t1 m1 s1 p1` con acarreo 1.
- **El bit de y que se está sumando viaja en el cache.**

| Estado | Qué hace |
|---|---|
| `f` | Va al final de la cinta. |
| `t` | Toma el último bit de y: lo guarda en el cache y lo borra. Si solo queda `+`, y se acabó. |
| `m` | Cruza lo que queda de y hasta el `+`. |
| `s` | Cruza los bits ya sumados de x (marcados `o` = 0, `i` = 1) hasta el siguiente bit de x (un blanco cuenta como 0) y escribe el bit de `x + cache + acarreo`. El nuevo acarreo decide si sigue `f0` o `f1`. |
| `p` | Cuando y se acaba, borra el `+` y propaga el acarreo sobre los bits pendientes de x. |
| `v`, `c`, `r` | Vuelve al inicio, convierte las marcas `o`/`i` en `0`/`1` y deja la cabeza sobre el primer bit. |

71 reglas, 14 estados, Γ = {0, 1, +, o, i, B}. Funciona con operandos de distinta
longitud, con acarreo final que agrega un dígito y con ceros a la izquierda.

| Entrada | Decimal | Cinta final | Pasos |
|---|---|---|---|
| `101+11` | 5 + 3 | `1000` | 37 |
| `1111+1` | 15 + 1 | `10000` | 31 |
| `110+101` | 6 + 5 | `1011` | 51 |
| `1101+1011` | 13 + 11 | `11000` | 73 |
| `10011+110` | 19 + 6 | `11001` | 56 |

### Extras

- `maquinas/palindromos.yaml`: palíndromos sobre {a, b}. Guarda el primer símbolo en el
  cache, lo compara con el último y borra ambos.
- `maquinas/ejemplo_enunciado.yaml`: el YAML del enunciado tal cual, solo con las dos
  reglas del ejemplo, así que toda cadena termina rechazada en `q1`.

---

## Arquitectura

```
proyecto3-teoria/
├── main.py                 CLI: lee el YAML, simula y muestra con rich
├── app.py                  servidor Flask del visor web
├── herramientas/
│   └── construir_pages.py  version estatica para GitHub Pages (Pyodide)
├── mt/
│   ├── modelo.py           Transicion y MaquinaTuring (Q, Σ, Γ, δ, q0, B, F)
│   ├── parser.py           YAML → MaquinaTuring, con validaciones y número de línea
│   ├── cinta.py            cinta infinita en ambos sentidos
│   ├── simulador.py        ciclo de ejecución, IDs y resultado
│   ├── consola.py          salida en terminal (tablas, IDs, cinta, animación)
│   └── exportar.py         MT y ejecuciones a JSON; simular_texto() que usa el visor
├── web/
│   ├── templates/index.html
│   └── static/visor.css, visor.js
├── maquinas/               archivos YAML
└── tests/
```

```
 archivo.yaml ──► parser ──► MaquinaTuring ──► Simulador.ejecutar(w) ──► Resultado
                    │              │                    │                    │
              ErrorConfiguracion  δ: dict          Cinta + estado      IDs, aceptada,
              (con línea)    (q, X, c) → regla     + cache             motivo, cinta final
                                                                             │
                                                         consola (rich) ◄────┴────► exportar → visor web
```

Decisiones de diseño:

- **δ es un diccionario** con clave `(estado, símbolo leído, cache)`. Buscar la regla de
  cada paso cuesta O(1), y detectar no determinismo al cargar es inmediato: una clave
  repetida.
- **La cinta es un diccionario disperso** `posición → símbolo` que solo guarda celdas no
  blancas. Crece hacia la izquierda o la derecha sin copiar listas, y una celda que nunca
  se tocó vale blanco.
- **Cada ID es una foto inmutable** (`DescripcionInstantanea`): estado, cache, porción
  visible de la cinta, posición de la cabeza y la regla que llevó a ella. Con eso se
  imprime la notación de Hopcroft, se anima en la terminal y se reproduce en el visor,
  incluso hacia atrás.
- **La lógica no depende de la interfaz**: `mt` no sabe nada de rich ni de Flask. La
  terminal y el visor consumen el mismo `Resultado`, y por eso el mismo paquete corre
  sin cambios en el navegador con Pyodide para la versión de GitHub Pages.
