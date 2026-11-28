# Todo lo que define a un jefe: su presupuesto de puntos, su banco de ataques y
# la reparación que convierte cualquier cromosoma crudo en un jefe válido.
#
# Un cromosoma ya decodificado es un diccionario con:
#   puntos          vida, ataque, defensa, ataque mágico, defensa mágica y velocidad
#   objeto1, 2      el objeto que lleva en cada fase
#   habs            8 ataques distintos del banco, en el orden inicial de su cola
#   pesos           8 valores de 0 a 3, qué tanto prefiere cada ataque
#   cambios         2 pares (posición, ataque nuevo) que se aplican en la fase 2
#   ajustes         5 valores de 0 a 3, cómo cambian sus atributos en la fase 2
#   predisposicion  6 valores de 0 a 7, a qué clases prefiere atacar
from reglas import nObjetos, indiceElem

nStats = 6
PRESUPUESTO, PUNTOS_MIN, PUNTOS_MAX = 1500, 100, 500

# La escala viene de la calibración con jefes aleatorios. Al pasar a seis
# atributos se subió el presupuesto de 1000 a 1500 para conservar el promedio
# de 250 puntos por atributo. Con el banco de 32 ataques el jefe reparte su
# daño entre más héroes, así que se le subió la vida por punto para que la
# mediana de los jefes aleatorios volviera a quedar cerca de 50%. El valor
# actual es el que deja esa mediana en su lugar con las clases ya calibradas.
# Cuando el objetivo pasó a 14 rondas se le dio más vida al jefe y se le bajó
# el ataque (antes 3.3 y 1.8), junto con más vida a los héroes, para que las
# peleas duren eso sin que el jefe tenga que esconderse detrás del bloqueo.
HP_POR_PUNTO = 5.5
ATK_DIV, DEF_DIV = 2, 3
ESCALA_ATK, ESCALA_DEF = 1.54, 1
DIVISOR_VEL = 10

tamanoCola, tamanoVentana = 8, 4
nCambios = 2

# En la fase 2 cada atributo, menos la vida, se mueve un poco hacia arriba o
# hacia abajo según su gen.
multAjuste = [0.85, 0.95, 1.05, 1.15]
statsAjustables = ["atk", "defe", "atkMag", "defMag", "vel"]


def ataque(nombre, poder, esFisico, elem=None, enArea=False, carga=False):
    return {"nombre": nombre, "poder": poder, "esFisico": esFisico,
            "elem": indiceElem[elem] if elem else None, "enArea": enArea, "carga": carga}


# Banco de 32 ataques. Los de área pegan menos a cada héroe pero suman más
# daño en total; salen la mitad de seguido que los demás (ver pesoArea en
# combate.py), así que cuando llegan pegan fuerte. Los cuatro últimos gastan un turno en cargar y pegan al
# siguiente, lo que le da tiempo al equipo de bloquear.
HABILIDADES = [
    ataque("Zarpazo", 0.80, True),
    ataque("Mordida", 0.90, True),
    ataque("Coletazo", 1.00, True),
    ataque("Pisoton", 1.00, True),
    ataque("Embestida", 1.10, True),
    ataque("Cabezazo", 1.15, True),
    ataque("Garra doble", 1.20, True),
    ataque("Golpe pesado", 1.30, True),

    ataque("Onda de choque", 0.65, True, enArea=True),
    ataque("Barrido", 0.70, True, enArea=True),
    ataque("Estampida", 0.75, True, enArea=True),
    ataque("Terremoto", 0.75, True, "tierra", enArea=True),

    ataque("Llamarada", 1.30, False, "fuego"),
    ataque("Chorro", 1.30, False, "agua"),
    ataque("Rafaga", 1.30, False, "viento"),
    ataque("Lanza de roca", 1.30, False, "tierra"),
    ataque("Espinas", 1.30, False, "planta"),
    ataque("Descarga", 1.30, False, "rayo"),
    ataque("Rayo de luz", 1.30, False, "luz"),
    ataque("Garra sombria", 1.30, False, "oscuridad"),

    ataque("Incendio", 0.85, False, "fuego", enArea=True),
    ataque("Marejada", 0.85, False, "agua", enArea=True),
    ataque("Vendaval", 0.85, False, "viento", enArea=True),
    ataque("Avalancha", 0.85, False, "tierra", enArea=True),
    ataque("Enredadera", 0.85, False, "planta", enArea=True),
    ataque("Tormenta", 0.85, False, "rayo", enArea=True),
    ataque("Resplandor", 0.85, False, "luz", enArea=True),
    ataque("Eclipse", 0.85, False, "oscuridad", enArea=True),

    ataque("Aplastamiento", 2.60, True, carga=True),
    ataque("Devastacion", 1.40, True, enArea=True, carga=True),
    ataque("Rayo final", 2.80, False, "rayo", carga=True),
    ataque("Cataclismo", 1.50, False, "fuego", enArea=True, carga=True),
]
N_HABILIDADES = len(HABILIDADES)


def reparar(crom):
    # Reparar dos veces tiene que dar lo mismo que reparar una. Antes los puntos
    # ya válidos se volvían a tratar como proporciones y el jefe evaluado no era
    # el mismo que el guardado, por eso se revisa primero si ya son un reparto final.
    if _puntos_validos(crom["puntos"]):
        enteros = [int(v) for v in crom["puntos"]]
        return _reparar_resto(crom, enteros)

    crudos = [max(0.0, float(v)) for v in crom["puntos"]]
    total = sum(crudos)
    proporcion = [v / total for v in crudos] if total > 0 else [1 / nStats] * nStats
    pts = [PUNTOS_MIN + (PRESUPUESTO - nStats * PUNTOS_MIN) * p for p in proporcion]

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
    orden = sorted(range(nStats), key=lambda i: pts[i] - enteros[i], reverse=True)
    for i in orden[:faltan]:
        enteros[i] += 1
    return _reparar_resto(crom, enteros)


def _puntos_validos(puntos):
    # Los valores crudos del algoritmo van de 0 a 15, así que nunca pasan por
    # un reparto final de enteros entre 100 y 500 que suman el presupuesto.
    return (len(puntos) == nStats and all(float(v).is_integer() for v in puntos)
            and sum(puntos) == PRESUPUESTO
            and all(PUNTOS_MIN <= v <= PUNTOS_MAX for v in puntos))


def _reparar_resto(crom, enteros):
    # Un ataque repetido en la cola se cambia por el de menor índice que siga libre.
    habs = []
    for h in crom["habs"]:
        h = int(h) % N_HABILIDADES
        if h in habs:
            h = min(i for i in range(N_HABILIDADES) if i not in habs)
        habs.append(h)

    # Los ataques que entran en la fase 2 tampoco pueden repetir a los de la
    # cola ni entre sí. Si chocan se recorre el banco hasta encontrar uno libre.
    cambios, ocupados = [], set(habs)
    for pos, nuevo in crom["cambios"]:
        nuevo = int(nuevo) % N_HABILIDADES
        while nuevo in ocupados:
            nuevo = (nuevo + 1) % N_HABILIDADES
        ocupados.add(nuevo)
        cambios.append([int(pos) % tamanoCola, nuevo])

    return {"puntos": enteros,
            "objeto1": int(crom["objeto1"]) % nObjetos, "objeto2": int(crom["objeto2"]) % nObjetos,
            "habs": habs,
            "pesos": [int(w) % 4 for w in crom["pesos"]],
            "cambios": cambios,
            "ajustes": [int(a) % len(multAjuste) for a in crom["ajustes"]],
            "predisposicion": [int(p) % 8 for p in crom["predisposicion"]]}


def stats_jefe(crom):
    p_hp, p_atk, p_def, pAtkMag, pDefMag, p_vel = crom["puntos"]
    return {"hp": int(p_hp * HP_POR_PUNTO),
            "atk": int(p_atk * ESCALA_ATK / ATK_DIV), "defe": int(p_def * ESCALA_DEF / DEF_DIV),
            "atkMag": int(pAtkMag * ESCALA_ATK / ATK_DIV), "defMag": int(pDefMag * ESCALA_DEF / DEF_DIV),
            "vel": p_vel / DIVISOR_VEL}


def statsFase2(crom):
    # La vida máxima no cambia: el umbral de la fase y los porcentajes de vida
    # se siguen midiendo contra la misma cantidad.
    stats = stats_jefe(crom)
    for nombre, gen in zip(statsAjustables, crom["ajustes"]):
        valor = stats[nombre] * multAjuste[gen]
        stats[nombre] = valor if nombre == "vel" else int(valor)
    return stats


def colaFase2(crom):
    # Los ataques con que queda cada posición de la cola después de los cambios.
    cola = list(crom["habs"])
    for pos, nuevo in crom["cambios"]:
        cola[pos] = nuevo
    return cola
