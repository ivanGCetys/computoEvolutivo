# Reglas base del juego: elementos, fórmula de daño y el equipo del jugador.
# Aquí no hay azar ni estado, solo tablas y cuentas.

FUEGO, HIELO, VIENTO, TIERRA = 0, 1, 2, 3
NOMBRES_ELEM = ["fuego", "hielo", "viento", "tierra"]
N_ELEMENTOS = len(NOMBRES_ELEM)

# El ciclo es fuego, hielo, viento, tierra y de vuelta a fuego: cada uno vence al siguiente.
VENCE = {FUEGO: HIELO, HIELO: VIENTO, VIENTO: TIERRA, TIERRA: FUEGO}


def mult_elemental(elem_ataque, elem_defensor):
    if elem_ataque is None:
        return 1.0
    if VENCE[elem_ataque] == elem_defensor:
        return 1.5
    if VENCE[elem_defensor] == elem_ataque:
        return 0.5
    return 1.0


def calcular_dano(atk, poder, mult_elem, defensa, mult_bloqueo=1.0):
    bruto = atk * poder * mult_elem * 100 / (100 + defensa) * mult_bloqueo

    # Sumamos 1e-9 antes de truncar porque un 13.9999999 por error de punto
    # flotante se nos volvía 13.
    return max(1, int(bruto + 1e-9))


# Los héroes se llaman por su rol y no por su elemento, porque el elemento
# cambia según el equipo y los stats no.
EQUIPO_BASE = [
    {"nombre": "Guerrero", "elem": FUEGO, "hp": 260, "sp": 60, "atk": 60, "defe": 25, "vel": 20, "cura": False, "bloqueo": 0.5},
    {"nombre": "Curandero", "elem": HIELO, "hp": 240, "sp": 120, "atk": 40, "defe": 30, "vel": 15, "cura": True, "bloqueo": 0.5},
    {"nombre": "Explorador", "elem": VIENTO, "hp": 250, "sp": 80, "atk": 50, "defe": 25, "vel": 30, "cura": False, "bloqueo": 0.5},
    {"nombre": "Tanque", "elem": TIERRA, "hp": 380, "sp": 40, "atk": 35, "defe": 60, "vel": 10, "cura": False, "bloqueo": 0.3},
]

PODER_BASICO = 0.8
PODER_MAGIA, COSTO_MAGIA = 1.2, 15

# El ataque fuerte se paga con vida: 20% del HP máximo de quien lo usa.
PODER_FUERTE, COSTO_FUERTE = 1.6, 0.20

CURA, COSTO_CURA = 0.25, 20
POCION_HP, POCIONES_INICIALES = 0.40, 3
UMBRAL_POCION, UMBRAL_CURA, UMBRAL_FUERTE = 0.30, 0.40, 0.50


def _rotar_equipo(k):
    eq = [dict(p) for p in EQUIPO_BASE]
    for p in eq:
        p["elem"] = (p["elem"] + k) % N_ELEMENTOS
    return eq


# Los cuatro equipos son el mismo equipo con los elementos corridos un lugar
# cada vez. Mismos stats y mismo HP total, así la comparación entre equipos
# solo mide el efecto del reparto de elementos.
NOMBRES_EQUIPOS = ["A", "B", "C", "D"]
EQUIPOS = {NOMBRES_EQUIPOS[k]: (EQUIPO_BASE if k == 0 else _rotar_equipo(k))
           for k in range(N_ELEMENTOS)}
EQUIPO_A, EQUIPO_B, EQUIPO_C, EQUIPO_D = (EQUIPOS[n] for n in NOMBRES_EQUIPOS)

# Nombre anterior del equipo C, lo dejamos para no romper scripts viejos.
EQUIPO_ROTADO = EQUIPO_C
