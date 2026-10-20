"""
Motor de combate por turnos, v0.1 (BORRADOR).

Sirve como función de aptitud para un algoritmo genético que diseña jefes.
No imprime nada. Todo el azar sale de random.Random(semilla), así que la misma
semilla da exactamente el mismo combate.

Decisiones aceptadas el 13-oct (ver REPORTE_v0.1.md):
  - ATK y DEF del jefe: se empezó con ATK = DEF = puntos; la simulación obligó a
    recalibrar a HP = puntos x 3, ATK = puntos // 2, DEF = puntos // 3 (CALIBRADO).
  - Poderes de habilidades con la misma escala que el jugador.
  - Fitness = f_win * (0.5*margen + 0.25*duracion + 0.25*variedad), f_win = 1 - 2d.
  - Sin veneno, sin bomba, sin poción de SP. La fase 2 solo cambia el elemento.

Decisiones PROVISIONALES (pendientes de la Fase 3) marcadas con "PROVISIONAL".
"""
import math
import random

# ---------------------------------------------------------------------------
# 1. Elementos: fuego > hielo > viento > tierra > fuego
# ---------------------------------------------------------------------------
FUEGO, HIELO, VIENTO, TIERRA = 0, 1, 2, 3
NOMBRES_ELEM = ["fuego", "hielo", "viento", "tierra"]
N_ELEMENTOS = len(NOMBRES_ELEM)
VENCE = {FUEGO: HIELO, HIELO: VIENTO, VIENTO: TIERRA, TIERRA: FUEGO}


def mult_elemental(elem_ataque, elem_defensor):
    """1.5 si el ataque vence al defensor, 0.5 si el defensor vence al ataque,
    1.0 en otro caso (incluye mismo elemento y ataques sin elemento = None)."""
    if elem_ataque is None:
        return 1.0
    if VENCE[elem_ataque] == elem_defensor:
        return 1.5
    if VENCE[elem_defensor] == elem_ataque:
        return 0.5
    return 1.0


def calcular_dano(atk, poder, mult_elem, defensa, mult_bloqueo=1.0):
    """Daño = ATK x poder x elemento x 100/(100+DEF) x bloqueo, entero, mínimo 1.
    El 1e-9 evita que un 13.9999999 (error de punto flotante) se vuelva 13."""
    bruto = atk * poder * mult_elem * 100 / (100 + defensa) * mult_bloqueo
    return max(1, int(bruto + 1e-9))


# ---------------------------------------------------------------------------
# 2. Equipo del jugador (tabla del briefing)
# ---------------------------------------------------------------------------
# Los héroes se nombran por su ROL, no por su elemento: el elemento cambia según el
# equipo (A, B, C, D) pero los stats y el rol son siempre los mismos. Antes se
# llamaban Fuego/Hielo/Viento/Tierra, que confundía al rotar los elementos.
EQUIPO_BASE = [
    {"nombre": "Guerrero",   "elem": FUEGO,  "hp": 260, "sp": 60,  "atk": 60, "defe": 25, "vel": 20, "cura": False, "bloqueo": 0.5},
    {"nombre": "Curandero",  "elem": HIELO,  "hp": 240, "sp": 120, "atk": 40, "defe": 30, "vel": 15, "cura": True,  "bloqueo": 0.5},
    {"nombre": "Explorador", "elem": VIENTO, "hp": 250, "sp": 80,  "atk": 50, "defe": 25, "vel": 30, "cura": False, "bloqueo": 0.5},
    {"nombre": "Tanque",     "elem": TIERRA, "hp": 380, "sp": 40,  "atk": 35, "defe": 60, "vel": 10, "cura": False, "bloqueo": 0.3},
]

PODER_BASICO = 0.8
PODER_MAGIA, COSTO_MAGIA = 1.2, 15
PODER_FUERTE, COSTO_FUERTE = 1.6, 0.20      # cuesta 20% del HP máximo
CURA, COSTO_CURA = 0.25, 20                  # cura 25% del HP máximo del objetivo
POCION_HP, POCIONES_INICIALES = 0.40, 3      # mochila compartida
UMBRAL_POCION, UMBRAL_CURA, UMBRAL_FUERTE = 0.30, 0.40, 0.50
# PROVISIONAL (Fase 3): el heurístico del briefing no usa la acción de bloquear, así que
# el bloqueo existe en la fórmula de daño (bloq) pero hoy nadie lo activa.

# DECIDIDO 20-oct: hay CUATRO equipos, las 4 rotaciones del ciclo elemental sobre
# los mismos 4 héroes. Mismos stats y mismo HP total (1130); lo único que cambia es
# qué elemento le toca a cada rol: en A el curandero es de hielo, en B de viento, etc.
# En el juego el jugador elige uno al empezar; para el AG el jefe debe ser justo
# contra TODOS (ver evaluar_jefe), así que no puede abusar de un solo reparto.
def _rotar_equipo(k):
    """Devuelve el equipo base con todos los elementos corridos k lugares en el ciclo."""
    eq = [dict(p) for p in EQUIPO_BASE]
    for p in eq:
        p["elem"] = (p["elem"] + k) % N_ELEMENTOS
    return eq


NOMBRES_EQUIPOS = ["A", "B", "C", "D"]
EQUIPOS = {NOMBRES_EQUIPOS[k]: (EQUIPO_BASE if k == 0 else _rotar_equipo(k))
           for k in range(N_ELEMENTOS)}
EQUIPO_A, EQUIPO_B, EQUIPO_C, EQUIPO_D = (EQUIPOS[n] for n in NOMBRES_EQUIPOS)
EQUIPO_ROTADO = EQUIPO_C          # nombre viejo, por compatibilidad

# ---------------------------------------------------------------------------
# 3. Jefe
# ---------------------------------------------------------------------------
PRESUPUESTO, PUNTOS_MIN, PUNTOS_MAX = 1000, 100, 500
# CALIBRADO 13-oct con 2,000 jefes aleatorios (ver REPORTE). Con la escala original
# (HP x10, ATK x1, DEF x1) el 99.8% de los jefes aleatorios gana siempre.
# Para volver a la original: 10, 1, 1, 1, 1.
HP_POR_PUNTO = 3            # HP  = puntos x 3        (300 a 1500)
ATK_DIV, DEF_DIV = 2, 3     # ATK = puntos // 2 (50 a 250); DEF = puntos // 3 (33 a 166)
ESCALA_ATK, ESCALA_DEF = 1, 1   # multiplicadores extra (1 = sin efecto); útiles para calibrar
DIVISOR_VEL = 10            # VEL = puntos / 10       (10 a 50)
RONDAS_MAX = 40

# (nombre, poder, usa el elemento del jefe, cooldown, tipo)
HABILIDADES = [
    ("Zarpazo",        0.8, False, 0, "uno"),
    ("Golpe pesado",   1.6, False, 2, "uno"),
    ("Rafaga",         1.2, True,  0, "uno"),
    ("Tormenta",       1.8, True,  2, "uno"),
    ("Onda de choque", 0.5, False, 1, "todos"),
    ("Guardia",        0.0, False, 0, "guardia"),
    ("Presa debil",    1.0, False, 1, "presa"),
]
N_HABILIDADES = len(HABILIDADES)
GUARDIA_MULT = 0.5
PRESA_UMBRAL, PRESA_MULT = 0.5, 1.5


# ---------------------------------------------------------------------------
# 4. Cromosoma (ya decodificado) y reparación
# ---------------------------------------------------------------------------
# cromosoma = {"puntos": [hp, atk, def, vel], "elem1": 0..3, "elem2": 0..3,
#              "habs": [4 índices distintos de 0..6], "pesos": [4 números >= 0]}

def reparar(crom):
    """Devuelve un cromosoma válido. No modifica el original."""
    # Puntos: 100 fijos a cada atributo + 600 repartidos según la proporción.
    crudos = [max(0.0, float(v)) for v in crom["puntos"]]
    total = sum(crudos)
    proporcion = [v / total for v in crudos] if total > 0 else [0.25] * 4
    pts = [PUNTOS_MIN + (PRESUPUESTO - 4 * PUNTOS_MIN) * p for p in proporcion]
    # Recorta a 500 y reparte el exceso entre los que no llegaron al tope.
    while any(p > PUNTOS_MAX + 1e-9 for p in pts):
        exceso = sum(p - PUNTOS_MAX for p in pts if p > PUNTOS_MAX)
        libres = [i for i, p in enumerate(pts) if p < PUNTOS_MAX]
        pts = [min(p, PUNTOS_MAX) for p in pts]
        for i in libres:
            pts[i] += exceso / len(libres)
    # A enteros que sumen exactamente 1000 (método del mayor residuo).
    enteros = [int(p) for p in pts]
    faltan = PRESUPUESTO - sum(enteros)
    orden = sorted(range(4), key=lambda i: pts[i] - enteros[i], reverse=True)
    for i in orden[:faltan]:
        enteros[i] += 1

    # Habilidades: sin repetir; un repetido se cambia por el menor índice libre.
    habs = []
    for h in crom["habs"]:
        h = int(h) % N_HABILIDADES
        if h in habs:
            h = min(i for i in range(N_HABILIDADES) if i not in habs)
        habs.append(h)

    # Pesos: normalizados; al menos 2 habilidades con peso > 10%.
    pesos = [max(0.0, float(w)) for w in crom["pesos"]]
    if sum(pesos) == 0:
        pesos = [1.0] * 4
    pesos = [w / sum(pesos) for w in pesos]
    if sum(1 for w in pesos if w > 0.10) < 2:
        orden_w = sorted(range(4), key=lambda i: (-pesos[i], i))
        pesos[orden_w[1]] = 0.15
        pesos = [w / sum(pesos) for w in pesos]

    return {"puntos": enteros, "elem1": int(crom["elem1"]) % 4, "elem2": int(crom["elem2"]) % 4,
            "habs": habs, "pesos": pesos}


def stats_jefe(crom):
    p_hp, p_atk, p_def, p_vel = crom["puntos"]
    return {"hp": p_hp * HP_POR_PUNTO, "atk": p_atk // ATK_DIV * ESCALA_ATK,
            "defe": p_def // DEF_DIV * ESCALA_DEF, "vel": p_vel / DIVISOR_VEL}


# ---------------------------------------------------------------------------
# 5. Jugador heurístico (lista de prioridades del briefing)
# ---------------------------------------------------------------------------
def decidir_accion(i, equipo, hp, sp, pociones, elem_jefe):
    """Devuelve (accion, objetivo). Acciones: pocion, curar, magia, fuerte, basico."""
    yo = equipo[i]
    pct = hp[i] / yo["hp"]
    if pct < UMBRAL_POCION and pociones > 0:
        return "pocion", i
    if yo["cura"] and sp[i] >= COSTO_CURA:
        heridos = [j for j in range(len(equipo)) if hp[j] > 0 and hp[j] / equipo[j]["hp"] < UMBRAL_CURA]
        if heridos:
            return "curar", min(heridos, key=lambda j: (hp[j] / equipo[j]["hp"], j))
    if sp[i] >= COSTO_MAGIA and mult_elemental(yo["elem"], elem_jefe) == 1.5:
        return "magia", None
    costo = int(COSTO_FUERTE * yo["hp"])
    if pct > UMBRAL_FUERTE and hp[i] - costo >= 1:
        return "fuerte", None
    return "basico", None


def objetivo_jefe(elem_jefe, equipo, hp):
    """El personaje débil al elemento actual del jefe; si no hay, el de menor HP."""
    vivos = [j for j in range(len(equipo)) if hp[j] > 0]
    for j in vivos:
        if VENCE[elem_jefe] == equipo[j]["elem"]:
            return j
    return min(vivos, key=lambda j: (hp[j], j))


# ---------------------------------------------------------------------------
# 6. Un combate
# ---------------------------------------------------------------------------
def simular(crom, equipo=EQUIPO_BASE, semilla=0):
    """Simula un combate. crom debe venir reparado. Devuelve un diccionario."""
    rng = random.Random(semilla)
    jefe = stats_jefe(crom)
    n = len(equipo)
    hp = [p["hp"] for p in equipo]
    sp = [p["sp"] for p in equipo]
    bloq = [1.0] * n
    pociones = POCIONES_INICIALES
    hp_jefe, elem_jefe, guardia = jefe["hp"], crom["elem1"], False
    ronda_fase2 = None             # ronda en que entró a fase 2 (None = nunca)
    espera = [0, 0, 0, 0]          # turnos que le faltan a cada habilidad
    usos = [0, 0, 0, 0]
    primera_muerte = None

    # Orden fijo: VEL descendente; en empate, primero el equipo y luego el orden de la tabla.
    actores = list(range(n)) + ["J"]
    actores.sort(key=lambda a: (-jefe["vel"], 1, 0) if a == "J" else (-equipo[a]["vel"], 0, a))

    for ronda in range(1, RONDAS_MAX + 1):
        for a in actores:
            if a == "J":
                guardia = False
                if ronda_fase2 is None and hp_jefe < 0.5 * jefe["hp"]:
                    elem_jefe, ronda_fase2 = crom["elem2"], ronda
                disponibles = [k for k in range(4) if espera[k] == 0]
                total = sum(crom["pesos"][k] for k in disponibles)
                if total > 0:
                    r, elegido = rng.random() * total, disponibles[-1]
                    for k in disponibles:
                        r -= crom["pesos"][k]
                        if r < 0:
                            elegido = k
                            break
                else:
                    elegido = disponibles[int(rng.random() * len(disponibles))]
                nombre, poder, con_elem, cooldown, tipo = HABILIDADES[crom["habs"][elegido]]
                usos[elegido] += 1
                if tipo == "guardia":
                    guardia = True
                elif tipo == "todos":
                    for j in range(n):
                        if hp[j] > 0:
                            hp[j] -= calcular_dano(jefe["atk"], poder, 1.0, equipo[j]["defe"], bloq[j])
                else:
                    j = objetivo_jefe(elem_jefe, equipo, hp)
                    m = mult_elemental(elem_jefe if con_elem else None, equipo[j]["elem"])
                    p = poder * PRESA_MULT if tipo == "presa" and hp[j] < PRESA_UMBRAL * equipo[j]["hp"] else poder
                    hp[j] -= calcular_dano(jefe["atk"], p, m, equipo[j]["defe"], bloq[j])
                for k in range(4):
                    espera[k] = max(0, espera[k] - 1)
                espera[elegido] = cooldown
                hp = [max(0, h) for h in hp]
                if primera_muerte is None and any(h == 0 for h in hp):
                    primera_muerte = ronda
                if all(h == 0 for h in hp):
                    return _resultado(False, ronda, hp, usos, primera_muerte, False, hp_jefe, ronda_fase2, equipo)
            else:
                i = a
                if hp[i] <= 0:
                    continue
                bloq[i] = 1.0
                accion, obj = decidir_accion(i, equipo, hp, sp, pociones, elem_jefe)
                yo = equipo[i]
                mg = GUARDIA_MULT if guardia else 1.0
                if accion == "pocion":
                    pociones -= 1
                    hp[i] = min(yo["hp"], hp[i] + int(POCION_HP * yo["hp"]))
                elif accion == "curar":
                    sp[i] -= COSTO_CURA
                    hp[obj] = min(equipo[obj]["hp"], hp[obj] + int(CURA * equipo[obj]["hp"]))
                elif accion == "magia":
                    sp[i] -= COSTO_MAGIA
                    hp_jefe -= calcular_dano(yo["atk"], PODER_MAGIA, mult_elemental(yo["elem"], elem_jefe), jefe["defe"], mg)
                elif accion == "fuerte":
                    hp[i] -= int(COSTO_FUERTE * yo["hp"])
                    hp_jefe -= calcular_dano(yo["atk"], PODER_FUERTE, 1.0, jefe["defe"], mg)
                else:
                    hp_jefe -= calcular_dano(yo["atk"], PODER_BASICO, 1.0, jefe["defe"], mg)
                if hp_jefe <= 0:
                    return _resultado(True, ronda, hp, usos, primera_muerte, False, max(0, hp_jefe), ronda_fase2, equipo)
    # Tope de rondas: cuenta como derrota del jefe (regla del briefing).
    return _resultado(True, RONDAS_MAX, hp, usos, primera_muerte, True, hp_jefe, ronda_fase2, equipo)


def _resultado(gana_equipo, rondas, hp, usos, primera_muerte, tope, hp_jefe, ronda_fase2,
               equipo=EQUIPO_BASE):
    # El denominador es el HP total del equipo que se simuló, no uno fijo:
    # así hp_final_pct sigue siendo un porcentaje si el equipo cambia de tamaño.
    return {"gana_equipo": gana_equipo, "rondas": rondas,
            "hp_final_pct": sum(hp) / sum(p["hp"] for p in equipo),
            "hp_equipo": list(hp), "vivos": sum(1 for h in hp if h > 0), "usos": usos,
            "primera_muerte": primera_muerte, "tope": tope,
            "hp_jefe": hp_jefe, "ronda_fase2": ronda_fase2}


# ---------------------------------------------------------------------------
# 7. Fitness (Monte Carlo)
# ---------------------------------------------------------------------------
# Banda de tasa de victoria del EQUIPO. "media" = combate parejo (decisión del 20/10).
# Las otras dos quedan como estaban; solo se usa "media" en el avance.
BANDAS = {"facil": (0.70, 0.90), "media": (0.40, 0.60), "dificil": (0.20, 0.40)}
W_MARGEN, W_DURACION, W_VARIEDAD = 0.5, 0.25, 0.25
RONDAS_IDEAL, SIGMA_RONDAS, HP_IDEAL = 10, 3, 0.20


def evaluar(crom, equipo=EQUIPO_BASE, n=30, semilla=0, banda=BANDAS["media"]):
    """Corre n combates (semillas semilla..semilla+n-1) y calcula el fitness.
    Usar la MISMA semilla para todos los individuos de una generación."""
    crom = reparar(crom)
    resultados = [simular(crom, equipo, semilla + k) for k in range(n)]
    return calcular_fitness(resultados, banda)


def evaluar_jefe(crom, n=30, semilla=0, banda=BANDAS["media"]):
    """FUNCIÓN OBJETIVO F(x): fitness del jefe contra los 4 equipos, quedándose con
    el PEOR. El jugador elige equipo al empezar, así que un jefe solo es bueno si es
    parejo contra cualquiera de los cuatro. Con el mínimo, un jefe que abusa de un
    reparto se castiga por ese reparto, no se salva con el promedio."""
    crom = reparar(crom)
    f = {k: evaluar(crom, eq, n, semilla, banda) for k, eq in EQUIPOS.items()}
    peor = min(f, key=lambda k: f[k]["fitness"])
    r = dict(f[peor])                       # las métricas son las del peor equipo
    r["peor_equipo"] = peor
    r["fitness_equipos"] = {k: f[k]["fitness"] for k in EQUIPOS}
    r["p_victoria_equipos"] = {k: f[k]["p_victoria"] for k in EQUIPOS}
    return r


def costo(crom, n=30, semilla=0, banda=BANDAS["media"]):
    """FUNCIÓN DE COSTO C(x) = 1 - F(x). Se MINIMIZA (notación del curso, L01).
    F está en [0,1], así que C también. Mejor jefe = costo más bajo."""
    return 1.0 - evaluar_jefe(crom, n, semilla, banda)["fitness"]


def calcular_fitness(resultados, banda=BANDAS["media"]):
    """Separado de evaluar() para poder probarlo a mano con resultados inventados."""
    n = len(resultados)
    victorias = [r for r in resultados if r["gana_equipo"]]
    p = len(victorias) / n
    lo, hi = banda
    d = lo - p if p < lo else (p - hi if p > hi else 0.0)   # distancia a la banda
    f_win = 1 - 2 * d
    margen = (sum(1 - abs(r["hp_final_pct"] - HP_IDEAL) / (1 - HP_IDEAL) for r in victorias) / len(victorias)
              if victorias else 0.0)
    duracion = sum(math.exp(-(r["rondas"] - RONDAS_IDEAL) ** 2 / (2 * SIGMA_RONDAS ** 2)) for r in resultados) / n
    usos = [sum(r["usos"][k] for r in resultados) for k in range(4)]
    total = sum(usos)
    H = -sum(u / total * math.log2(u / total) for u in usos if u > 0)
    variedad = H / 2.0                                       # log2(4) = 2 bits
    fitness = f_win * (W_MARGEN * margen + W_DURACION * duracion + W_VARIEDAD * variedad)
    return {"fitness": fitness, "p_victoria": p, "f_win": f_win, "margen": margen,
            "duracion": duracion, "variedad": variedad,
            "rondas_prom": sum(r["rondas"] for r in resultados) / n,
            "tope_pct": sum(r["tope"] for r in resultados) / n}
