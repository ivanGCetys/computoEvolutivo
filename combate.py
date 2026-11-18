# Simulación de un combate por turnos entre el equipo y un jefe.
# No imprime nada y todo el azar sale de random.Random(semilla), así que la
# misma semilla siempre da el mismo combate.
import random

from reglas import *
from clases import EQUIPO_BASE, sortearConjuros
from jefe import *
from heuristico import decidir_accion, decidirPrioridad

RONDAS_MAX = 40
umbralFase2 = 0.5


def crearEstado(crom, equipo, rng):
    equipo = sortearConjuros(equipo, rng)
    jefe = stats_jefe(crom)
    n = len(equipo)

    # El orden es fijo: mayor velocidad primero. En empate va primero el equipo
    # y después el orden de la tabla.
    actores = list(range(n)) + ["J"]
    actores.sort(key=lambda a: (-jefe["vel"], 1, 0) if a == "J" else (-equipo[a]["vel"], 0, a))

    return {"crom": crom, "equipo": equipo, "jefe": jefe, "actores": actores,
            "hp": [p["hp"] for p in equipo], "sp": [p["sp"] for p in equipo],
            "bloq": [False] * n, "bloqueoTotal": [False] * n,
            "buffAtk": [0] * n, "multBuffAtk": [1.0] * n,
            "buffDef": [0] * n, "multBuffDef": [1.0] * n,
            "pociones": dict(pocionesIniciales),
            "hp_jefe": jefe["hp"], "objJefe": objetos[crom["objeto1"]], "guardia": False,
            "ronda": 0, "ronda_fase2": None, "primera_muerte": None,
            "cola": list(range(tamanoCola)), "ataques": list(crom["habs"]),
            "cargando": None, "usos": [0] * tamanoCola}


def accionesLegales(i, est, soloPrioridad=False):
    yo, sp = est["equipo"][i], est["sp"][i]
    vivos = [j for j in range(len(est["equipo"])) if est["hp"][j] > 0]
    ops = [] if soloPrioridad else [("basico", None, None)]

    for k, conj in enumerate(yo["conjuros"]):
        if sp < conj["costo"] or (soloPrioridad and not conj["prioridad"]):
            continue
        if conj["tipo"] == "cura" and not conj["enGrupo"]:
            ops.extend(("conjuro", k, j) for j in vivos)
        else:
            ops.append(("conjuro", k, None))

    if soloPrioridad:
        return ops

    ops.append(("bloquear", None, None))

    # Una poción solo se ofrece si de verdad recuperaría algo.
    faltaVida = est["hp"][i] < yo["hp"]
    faltaMana = sp < yo["sp"]
    for clave, cuantas in est["pociones"].items():
        if cuantas > 0 and (faltaVida if clave.startswith("hp") else faltaMana):
            ops.append(("pocion", clave, None))
    return ops


def puedeAdelantarse(i, est):
    # La ventana de prioridad solo tiene sentido si alguien vivo actuaría antes.
    yo = est["equipo"][i]
    if not any(c["prioridad"] and est["sp"][i] >= c["costo"] for c in yo["conjuros"]):
        return False

    for a in est["actores"]:
        if a == i:
            return False
        if a == "J" or est["hp"][a] > 0:
            return True
    return False


def atacarJefe(i, poder, esFisico, elem, est, rng):
    yo, jefe = est["equipo"][i], est["jefe"]
    atk = yo["atk"] if esFisico else yo["atkMag"]
    defensa = jefe["defe"] if esFisico else jefe["defMag"]
    if est["buffAtk"][i] > 0:
        atk = atk * est["multBuffAtk"][i]

    bloqueo = multBloqueo if est["guardia"] else 1.0
    dano, nota = danoAtaque(rng, atk, poder, esFisico, elem, yo["objeto"], defensa, est["objJefe"],
                            yo["vel"], jefe["vel"], bloqueo, yo["minFis"], yo["probCritico"])
    est["hp_jefe"] -= dano
    return dano, nota


def atacarHeroe(j, poder, esFisico, elem, est, rng):
    heroe, jefe = est["equipo"][j], est["jefe"]

    # El bloqueo total se gasta con el primer ataque que le llegue, pegue o no.
    if est["bloqueoTotal"][j]:
        est["bloqueoTotal"][j] = False
        return 0, "bloqueado"

    atk = jefe["atk"] if esFisico else jefe["atkMag"]
    defensa = heroe["defe"] if esFisico else heroe["defMag"]
    if est["buffDef"][j] > 0:
        defensa = defensa * est["multBuffDef"][j]

    bloqueo = multBloqueo if est["bloq"][j] else 1.0
    dano, nota = danoAtaque(rng, atk, poder, esFisico, elem, est["objJefe"], defensa, heroe["objeto"],
                            jefe["vel"], heroe["vel"], bloqueo, variacionFisMin, probCriticoJefe)
    est["hp"][j] = max(0, est["hp"][j] - dano)
    return dano, nota


def objetivo_jefe(est, rng):
    # Ruleta entre los héroes vivos con la predisposición del jefe hacia cada
    # clase. Se le suma 1 a cada gen para que ninguna clase quede en cero.
    hp, equipo = est["hp"], est["equipo"]
    pred = est["crom"]["predisposicion"]
    vivos = [j for j in range(len(hp)) if hp[j] > 0]
    pesos = [pred[equipo[j]["indiceClase"]] + 1 for j in vivos]

    r = rng.random() * sum(pesos)
    for j, w in zip(vivos, pesos):
        r -= w
        if r < 0:
            return j
    return vivos[-1]


def ejecutarAccion(i, accion, est, rng):
    # Aplica la acción del héroe i y devuelve lo que pasó, para el registro.
    tipo, cual, objetivo = accion
    yo = est["equipo"][i]
    hecho = {"accion": tipo, "golpes": [], "curas": [], "elem": None}
    lanzoBuff = False

    if tipo == "basico":
        hecho["accion"] = "Ataque basico"
        hecho["golpes"].append(("Jefe",) + atacarJefe(i, PODER_BASICO, True, None, est, rng))

    elif tipo == "bloquear":
        hecho["accion"] = "Bloquea"
        est["bloq"][i] = True

    elif tipo == "pocion":
        est["pociones"][cual] -= 1
        hecho["accion"] = "Bebe " + nombrePocion[cual]
        if cual.startswith("hp"):
            antes = est["hp"][i]
            est["hp"][i] = min(yo["hp"], antes + int(efectoPocion[cual] * yo["hp"]))
            hecho["curas"].append((yo["nombre"], est["hp"][i] - antes))
        else:
            est["sp"][i] = min(yo["sp"], est["sp"][i] + int(efectoPocion[cual] * yo["sp"]))

    else:
        conj = yo["conjuros"][cual]
        est["sp"][i] -= conj["costo"]
        hecho["accion"] = conj["nombre"]

        if conj.get("buff"):
            stat, mult, turnos = conj["buff"]
            if stat == "atk":
                est["buffAtk"][i], est["multBuffAtk"][i] = turnos, mult
            else:
                est["buffDef"][i], est["multBuffDef"][i] = turnos, mult
            lanzoBuff = True

        if conj["tipo"] == "ataque":
            hecho["elem"] = conj["elem"]
            hecho["golpes"].append(("Jefe",) + atacarJefe(i, conj["poder"], conj["esFisico"],
                                                         conj["elem"], est, rng))
        elif conj["tipo"] == "cura":
            cantidad = int(yo["atkMag"] * conj["poder"])
            curados = ([j for j in range(len(est["equipo"])) if est["hp"][j] > 0]
                       if conj["enGrupo"] else [objetivo])
            for j in curados:
                antes = est["hp"][j]
                est["hp"][j] = min(est["equipo"][j]["hp"], antes + cantidad)
                hecho["curas"].append((est["equipo"][j]["nombre"], est["hp"][j] - antes))
        elif conj["tipo"] == "bloqueoTotal":
            est["bloqueoTotal"][i] = True

    # Los buffs duran dos turnos propios después del turno en que se lanzan,
    # por eso el turno del lanzamiento no descuenta.
    if not lanzoBuff:
        if est["buffAtk"][i] > 0:
            est["buffAtk"][i] -= 1
        if est["buffDef"][i] > 0:
            est["buffDef"][i] -= 1
    return hecho


def turnoHeroe(i, est, rng, registro, politica, enVentana=False):
    # Devuelve False si el héroe prefirió esperar en la ventana de prioridad.
    if politica is None:
        accion = decidirPrioridad(i, est) if enVentana else decidir_accion(i, est)
    else:
        accion = politica(i, est, accionesLegales(i, est, enVentana), enVentana)
    if accion is None:
        return False

    yo = est["equipo"][i]
    est["bloq"][i] = False
    hecho = ejecutarAccion(i, accion, est, rng)

    # El maná de las clases mágicas vuelve poco a poco al terminar su turno.
    if yo["regenSp"]:
        est["sp"][i] = min(yo["sp"], est["sp"][i] + yo["regenSp"])

    if registro is not None:
        hecho.update({"tipo": "turno", "ronda": est["ronda"], "actor": yo["nombre"],
                      "adelantado": enVentana, "muertos": [],
                      "hp_jefe": max(0, est["hp_jefe"]), "hp_equipo": list(est["hp"])})
        registro.append(hecho)
    return True


def entrarFase2(est, registro):
    crom = est["crom"]
    est["ronda_fase2"] = est["ronda"]
    est["objJefe"] = objetos[crom["objeto2"]]
    est["jefe"] = statsFase2(crom)
    est["ataques"] = colaFase2(crom)

    if registro is not None:
        registro.append({"tipo": "fase2", "ronda": est["ronda"], "hp_jefe": est["hp_jefe"],
                         "objeto": est["objJefe"]["nombre"], "jefe": dict(est["jefe"]),
                         "nuevos": [HABILIDADES[nuevo]["nombre"] for _, nuevo in crom["cambios"]]})


def elegirDeLaCola(est, rng):
    # El jefe solo puede elegir entre los primeros ataques de su cola. El que
    # usa se va al final, así que tiene que pasar por los demás antes de repetirlo.
    cola, pesos = est["cola"], est["crom"]["pesos"]
    ventana = cola[:tamanoVentana]

    r, elegido = rng.random() * sum(pesos[k] + 1 for k in ventana), ventana[-1]
    for k in ventana:
        r -= pesos[k] + 1
        if r < 0:
            elegido = k
            break

    cola.remove(elegido)
    cola.append(elegido)
    est["usos"][elegido] += 1
    return elegido


def turnoJefe(est, rng, registro):
    crom, equipo, hp = est["crom"], est["equipo"], est["hp"]
    n = len(equipo)
    est["guardia"] = False

    if est["ronda_fase2"] is None and est["hp_jefe"] < umbralFase2 * est["jefe"]["hp"]:
        entrarFase2(est, registro)

    hp_antes = list(hp)
    golpes, elem = [], None

    if est["cargando"] is not None:
        # El turno anterior se fue en cargar, así que ahora el ataque sale sin más.
        atq, est["cargando"] = est["cargando"], None
        nombre = atq["nombre"]
    elif rng.random() < opcionesBloqueo[crom["probBloqueo"]]:
        atq, nombre = None, "Bloquea"
        est["guardia"] = True
    else:
        atq = HABILIDADES[est["ataques"][elegirDeLaCola(est, rng)]]
        nombre = atq["nombre"]
        if atq["carga"]:
            est["cargando"], atq = atq, None
            nombre = "Carga " + nombre

    if atq is not None:
        elem = atq["elem"]
        objetivos = ([j for j in range(n) if hp[j] > 0] if atq["enArea"]
                     else [objetivo_jefe(est, rng)])
        for j in objetivos:
            golpes.append((equipo[j]["nombre"],) + atacarHeroe(j, atq["poder"], atq["esFisico"], elem, est, rng))

    if est["primera_muerte"] is None and any(h == 0 for h in hp):
        est["primera_muerte"] = est["ronda"]

    if registro is not None:
        registro.append({"tipo": "turno", "ronda": est["ronda"], "actor": "Jefe", "accion": nombre,
                         "elem": elem, "golpes": golpes, "curas": [], "adelantado": False,
                         "muertos": [equipo[j]["nombre"] for j in range(n)
                                     if hp[j] == 0 and hp_antes[j] > 0],
                         "hp_jefe": est["hp_jefe"], "hp_equipo": list(hp)})


def simular(crom, equipo=EQUIPO_BASE, semilla=0, registro=None, politica=None):
    # crom debe venir reparado. Si registro es una lista se le agregan los eventos
    # del combate para narrarlo después, sin cambiar ningún número. Si politica es
    # una función, ella decide por el equipo en lugar del jugador automático, y así
    # el modo interactivo usa las mismas reglas con las que se calificó al jefe.
    # La política recibe el héroe, el estado, sus acciones legales y si está en
    # la ventana de prioridad, y devuelve una de esas acciones.
    rng = random.Random(semilla)
    est = crearEstado(crom, equipo, rng)
    equipo = est["equipo"]
    n = len(equipo)

    if registro is not None:
        registro.append({"tipo": "inicio", "jefe": dict(est["jefe"]),
                         "objeto": est["objJefe"]["nombre"],
                         "objeto2": objetos[crom["objeto2"]]["nombre"],
                         "habs": [HABILIDADES[h]["nombre"] for h in crom["habs"]],
                         "equipo": [p["nombre"] for p in equipo],
                         "hp_equipo": list(est["hp"]),
                         "conjuros": {p["nombre"]: [c["nombre"] for c in p["conjuros"]] for p in equipo},
                         "orden": ["Jefe" if x == "J" else equipo[x]["nombre"] for x in est["actores"]]})

    for ronda in range(1, RONDAS_MAX + 1):
        est["ronda"] = ronda
        if registro is not None:
            registro.append({"tipo": "ronda", "ronda": ronda})

        # Ventana de prioridad: quien tenga un ataque que se adelanta puede
        # usarlo antes que todos, y con eso gasta su turno de esta ronda.
        yaActuo = [False] * n
        for i in range(n):
            if est["hp"][i] > 0 and puedeAdelantarse(i, est):
                yaActuo[i] = turnoHeroe(i, est, rng, registro, politica, enVentana=True)
                if est["hp_jefe"] <= 0:
                    return _resultado(True, est, False)

        for a in est["actores"]:
            if a == "J":
                turnoJefe(est, rng, registro)
                if all(h == 0 for h in est["hp"]):
                    return _resultado(False, est, False)

            elif est["hp"][a] > 0 and not yaActuo[a]:
                turnoHeroe(a, est, rng, registro, politica)
                if est["hp_jefe"] <= 0:
                    return _resultado(True, est, False)

    # Llegar al tope de rondas cuenta como derrota del jefe.
    return _resultado(True, est, True)


def _resultado(gana_equipo, est, tope):
    # El porcentaje final se saca contra la vida total del equipo que peleó y no
    # contra un número fijo, para que valga igual con cualquiera de los equipos.
    hp = est["hp"]
    return {"gana_equipo": gana_equipo, "rondas": est["ronda"],
            "hp_final_pct": sum(hp) / sum(p["hp"] for p in est["equipo"]),
            "hp_equipo": list(hp), "vivos": sum(1 for h in hp if h > 0), "usos": est["usos"],
            "primera_muerte": est["primera_muerte"], "tope": tope,
            "hp_jefe": max(0, est["hp_jefe"]), "ronda_fase2": est["ronda_fase2"]}
