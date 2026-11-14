# Todo lo que define a un jefe: su presupuesto de puntos, sus habilidades y la
# reparación que convierte cualquier cromosoma crudo en un jefe válido.
#
# Un cromosoma ya decodificado es un diccionario con puntos (hp, atk, def, vel),
# elem1, elem2, habs (4 índices distintos) y pesos (4 números no negativos).

PRESUPUESTO, PUNTOS_MIN, PUNTOS_MAX = 1000, 100, 500

# Esta escala salió de simular 2000 jefes aleatorios. Con la original (HP x10,
# ATK x1, DEF x1) casi todos ganaban siempre y el algoritmo no tenía pendiente
# que seguir. El detalle está en REPORTE_v0.1.md.
HP_POR_PUNTO = 3
ATK_DIV, DEF_DIV = 2, 3
ESCALA_ATK, ESCALA_DEF = 1, 1
DIVISOR_VEL = 10

# Cada habilidad es nombre, poder, si usa el elemento del jefe, cooldown y tipo.
HABILIDADES = [
    ("Zarpazo", 0.8, False, 0, "uno"),
    ("Golpe pesado", 1.6, False, 2, "uno"),
    ("Rafaga", 1.2, True, 0, "uno"),
    ("Tormenta", 1.8, True, 2, "uno"),
    ("Onda de choque", 0.5, False, 1, "todos"),
    ("Guardia", 0.0, False, 0, "guardia"),
    ("Presa debil", 1.0, False, 1, "presa"),
]
N_HABILIDADES = len(HABILIDADES)
GUARDIA_MULT = 0.5
PRESA_UMBRAL, PRESA_MULT = 0.5, 1.5


def reparar(crom):
    # Reparar dos veces tiene que dar lo mismo que reparar una. Antes los puntos
    # ya válidos se volvían a tratar como proporciones y el jefe evaluado no era
    # el mismo que el guardado, por eso se revisa primero si ya son un reparto final.
    if _puntos_validos(crom["puntos"]):
        enteros = [int(v) for v in crom["puntos"]]
        return _reparar_resto(crom, enteros)

    crudos = [max(0.0, float(v)) for v in crom["puntos"]]
    total = sum(crudos)
    proporcion = [v / total for v in crudos] if total > 0 else [0.25] * 4
    pts = [PUNTOS_MIN + (PRESUPUESTO - 4 * PUNTOS_MIN) * p for p in proporcion]

    # Lo que pase del máximo se reparte entre los atributos que todavía tienen espacio.
    while any(p > PUNTOS_MAX + 1e-9 for p in pts):
        exceso = sum(p - PUNTOS_MAX for p in pts if p > PUNTOS_MAX)
        libres = [i for i, p in enumerate(pts) if p < PUNTOS_MAX]
        pts = [min(p, PUNTOS_MAX) for p in pts]
        for i in libres:
            pts[i] += exceso / len(libres)

    # Para que los enteros sumen exactamente el presupuesto usamos el método del
    # mayor residuo: los puntos que faltan van a quienes más perdieron al truncar.
    enteros = [int(p) for p in pts]
    faltan = PRESUPUESTO - sum(enteros)
    orden = sorted(range(4), key=lambda i: pts[i] - enteros[i], reverse=True)
    for i in orden[:faltan]:
        enteros[i] += 1
    return _reparar_resto(crom, enteros)


def _puntos_validos(puntos):
    # Los valores crudos del algoritmo van de 0 a 15, así que nunca pasan por
    # un reparto final de cuatro enteros entre 100 y 500 que suman 1000.
    return (len(puntos) == 4 and all(float(v).is_integer() for v in puntos)
            and sum(puntos) == PRESUPUESTO
            and all(PUNTOS_MIN <= v <= PUNTOS_MAX for v in puntos))


def _reparar_resto(crom, enteros):
    # Una habilidad repetida se cambia por la de menor índice que siga libre.
    habs = []
    for h in crom["habs"]:
        h = int(h) % N_HABILIDADES
        if h in habs:
            h = min(i for i in range(N_HABILIDADES) if i not in habs)
        habs.append(h)

    pesos = [max(0.0, float(w)) for w in crom["pesos"]]
    if sum(pesos) == 0:
        pesos = [1.0] * 4
    pesos = [w / sum(pesos) for w in pesos]

    # Pedimos al menos dos habilidades con más de 10% de uso para que ningún
    # jefe sea de un solo ataque.
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
