# Las seis clases de héroe, sus conjuros y los equipos que se pueden armar.
from itertools import combinations

from reglas import NOMBRES_ELEM, N_ELEMENTOS, indiceElem, objetos, variacionFisMin, probCriticoBase

# Todas las clases reparten el mismo tope de puntos entre vida, ataque físico,
# defensa física, ataque mágico, defensa mágica y velocidad, en ese orden. El
# maná va aparte y se ajusta a mano por clase.
topePuntosHeroe = 600
hpPorPuntoHeroe = 3.8
atkDivHeroe, defDivHeroe = 2, 3
velDivHeroe = 4


def conjuroAtaque(nombre, costo, poder, esFisico, elem=None, prioridad=False, buff=None):
    return {"nombre": nombre, "costo": costo, "tipo": "ataque", "poder": poder,
            "esFisico": esFisico, "elem": elem, "prioridad": prioridad, "buff": buff}


def conjuroBuff(nombre, costo, stat, mult, turnos=2):
    return {"nombre": nombre, "costo": costo, "tipo": "buff", "buff": (stat, mult, turnos),
            "prioridad": False}


def conjuroCura(nombre, costo, poder, enGrupo=False):
    return {"nombre": nombre, "costo": costo, "tipo": "cura", "poder": poder,
            "enGrupo": enGrupo, "prioridad": False}


# Los puntos y los poderes de esta tabla están calibrados para que los 15
# equipos tengan una fuerza parecida. Con la primera versión, que seguía los
# perfiles al pie de la letra, un mismo jefe le ganaba casi siempre a los
# equipos con Guerrero y Tanque y perdía casi siempre contra los que llevaban
# Mago, Pícaro y Berserker, y ningún jefe podía ser parejo contra todos.
# La calibración se hizo contra jefes aleatorios, no contra los jefes que
# entregan los algoritmos: se midió cuánto cambia la tasa de victoria de un
# equipo por llevar cada clase y se fue corrigiendo hasta dejar ese efecto
# cerca de cero. calibrar.py vuelve a medirlo.
#
# El Tanque tiene además provocación: el jefe lo elige como objetivo 3.5 veces
# más seguido que a los demás. Sin eso su vida y su defensa solo lo protegían
# a él y el equipo no ganaba nada por llevarlo.
#
# El elemento "azar" de los tajos del guerrero se sortea al empezar cada combate.
# Los costos están pensados contra el maná de cada clase. Mago y Clérigo
# recuperan lo suficiente para vivir de sus conjuros; las demás clases
# recuperan un poco cada turno, como la energía de un guerrero, y pueden usar
# una técnica cada dos o tres turnos.
tablaClases = {
    "Guerrero": {
        "puntos": [100, 100, 100, 100, 100, 100], "sp": 66, "regenSp": 4,
        "probCritico": 0.20, "minFis": 0.90, "objeto": "Amuleto de fuego",
        "conjuros": [conjuroBuff("Guardia de acero", 8, "defe", 1.5),
                     conjuroAtaque("Tajo elemental", 13, 1.8, False, "azar"),
                     conjuroAtaque("Tajo mayor", 20, 2.6, False, "azar")],
    },
    "Tanque": {
        "puntos": [148, 84, 150, 40, 118, 60], "sp": 36, "regenSp": 3, "provocacion": 3.5,
        "probCritico": probCriticoBase, "minFis": variacionFisMin, "objeto": "Talisman de tierra",
        "conjuros": [conjuroBuff("Muralla", 8, "defe", 1.6),
                     {"nombre": "Bloqueo total", "costo": 14, "tipo": "bloqueoTotal", "prioridad": False}],
    },
    "Mago": {
        "puntos": [70, 40, 65, 250, 75, 100], "sp": 100, "regenSp": 5,
        "probCritico": probCriticoBase, "minFis": variacionFisMin, "objeto": "Amuleto de rayo",
        "conjuros": [],
    },
    "Clerigo": {
        "puntos": [100, 105, 88, 120, 97, 90], "sp": 110, "regenSp": 3,
        "probCritico": probCriticoBase, "minFis": variacionFisMin, "objeto": "Talisman de luz",
        "conjuros": [conjuroCura("Curacion menor", 10, 1.25),
                     conjuroCura("Curacion mayor", 22, 2.5),
                     conjuroCura("Curacion en grupo", 40, 0.95, enGrupo=True)],
    },
    "Picaro": {
        "puntos": [123, 114, 55, 83, 55, 170], "sp": 40, "regenSp": 2,
        "probCritico": 0.20, "minFis": 0.90, "objeto": "Amuleto de oscuridad",
        "conjuros": [conjuroAtaque("Punalada veloz", 9, 0.85, True, prioridad=True),
                     conjuroAtaque("Golpe sombra", 15, 1.2, True, prioridad=True)],
    },
    "Berserker": {
        "puntos": [110, 141, 100, 85, 64, 100], "sp": 40, "regenSp": 4,
        "probCritico": probCriticoBase, "minFis": variacionFisMin, "objeto": "Amuleto de viento",
        "conjuros": [conjuroBuff("Furia", 10, "atk", 1.3),
                     conjuroAtaque("Furia desatada", 18, 1.0, True, buff=("atk", 1.3, 2))],
    },
}

nombresClases = list(tablaClases)

# Conjuros del mago. De la lista normal hay dos por elemento, uno barato y uno
# medio. De la lista de poderosos hay uno por elemento y cuesta más de la mitad
# de su maná, para que no pueda lanzarlo a cada rato.
nombresConjuroChico = ["Chispa", "Gota", "Brisa", "Guijarro", "Brote", "Calambre", "Destello", "Penumbra"]
nombresConjuroMedio = ["Llama", "Oleaje", "Remolino", "Roca", "Zarza", "Relampago", "Fulgor", "Sombra"]
nombresConjuroPoderoso = ["Infierno", "Diluvio", "Huracan", "Sismo", "Selva viva", "Tormenta electrica",
                          "Juicio", "Abismo"]

conjurosMago = []
for e in range(N_ELEMENTOS):
    conjurosMago.append(conjuroAtaque(nombresConjuroChico[e], 9, 0.7, False, e))
    conjurosMago.append(conjuroAtaque(nombresConjuroMedio[e], 14, 0.9, False, e))
conjurosMagoPoderosos = [conjuroAtaque(nombresConjuroPoderoso[e], 55, 1.4, False, e)
                         for e in range(N_ELEMENTOS)]


def statsHeroe(puntos):
    pHp, pAtk, pDef, pAtkMag, pDefMag, pVel = puntos
    return {"hp": int(pHp * hpPorPuntoHeroe), "atk": pAtk // atkDivHeroe, "defe": pDef // defDivHeroe,
            "atkMag": pAtkMag // atkDivHeroe, "defMag": pDefMag // defDivHeroe,
            "vel": pVel / velDivHeroe}


def buscarObjeto(nombre):
    for obj in objetos:
        if obj["nombre"] == nombre:
            return obj
    raise ValueError("objeto desconocido: " + nombre)


def crearHeroe(nombreClase, nombreObjeto=None):
    c = tablaClases[nombreClase]
    heroe = statsHeroe(c["puntos"])
    heroe.update({"nombre": nombreClase, "indiceClase": nombresClases.index(nombreClase),
                  "sp": c["sp"], "regenSp": c["regenSp"], "provocacion": c.get("provocacion", 1.0),
                  "probCritico": c["probCritico"], "minFis": c["minFis"],
                  "objeto": buscarObjeto(nombreObjeto or c["objeto"]),
                  "conjuros": [dict(k) for k in c["conjuros"]]})
    return heroe


def armarEquipo(nombres, objetosElegidos=None):
    # objetosElegidos deja que el jugador cambie el objeto de alguna clase. Sin
    # él cada clase lleva su objeto de siempre, que es con lo que se evalúa al jefe.
    objetosElegidos = objetosElegidos or {}
    return [crearHeroe(n, objetosElegidos.get(n)) for n in nombres]


def sortearConjuros(equipo, rng):
    # Devuelve una copia del equipo con lo que se decide al empezar el combate:
    # los cuatro conjuros del mago y los elementos de los tajos del guerrero.
    listo = []
    for heroe in equipo:
        h = dict(heroe)

        if h["nombre"] == "Mago":
            # Un poderoso y tres normales, sin repetir elemento entre los cuatro.
            elemPoderoso = rng.randrange(N_ELEMENTOS)
            otros = rng.sample([e for e in range(N_ELEMENTOS) if e != elemPoderoso], 3)
            h["conjuros"] = [conjurosMago[2 * e + rng.randrange(2)] for e in otros]
            h["conjuros"].append(conjurosMagoPoderosos[elemPoderoso])

        elif any(k.get("elem") == "azar" for k in h["conjuros"]):
            elems = rng.sample(range(N_ELEMENTOS), 2)
            nuevos = []
            for k in h["conjuros"]:
                if k.get("elem") == "azar":
                    k = dict(k)
                    k["elem"] = elems.pop()
                nuevos.append(k)
            h["conjuros"] = nuevos

        listo.append(h)
    return listo


def claveEquipo(nombres):
    return "".join(n[0] for n in nombres)


# El jugador arma su equipo con 4 de las 6 clases, así que hay 15 equipos posibles.
EQUIPOS = {claveEquipo(combo): armarEquipo(combo) for combo in combinations(nombresClases, 4)}
NOMBRES_EQUIPOS = list(EQUIPOS)
EQUIPO_BASE = EQUIPOS["GTMC"]
