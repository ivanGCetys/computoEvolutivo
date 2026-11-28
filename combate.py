# Simulación de un combate por turnos entre el equipo y un jefe.
# No imprime nada y todo el azar sale de random.Random(semilla), así que la
# misma semilla siempre da el mismo combate.
import random

from reglas import *
from clases import EQUIPO_BASE, sortearConjuros
from jefe import *
from heuristico import decidir_accion

RONDAS_MAX = 40
umbralFase2 = 0.5
basePredisposicion = 2
pesoArea = 0.3


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
            "pociones": dict(pocionesIniciales), "reservadas": {k: 0 for k in pocionesIniciales}, "atendidos": [],
            "hp_jefe": jefe["hp"], "objJefe": objetos[crom["objeto1"]],
            "ronda": 0, "ronda_fase2": None, "primera_muerte": None,
            "cola": list(range(tamanoCola)), "ataques": list(crom["habs"]),
            "cargando": None, "usos": [0] * tamanoCola}


def accionesLegales(i, est):
    yo, sp = est["equipo"][i], est["sp"][i]
    vivos = [j for j in range(len(est["equipo"])) if est["hp"][j] > 0]
    ops = [("basico", None, None)]

    for k, conj in enumerate(yo["conjuros"]):
        if sp < conj["costo"]:
            continue
        if conj["tipo"] == "cura" and not conj["enGrupo"]:
            ops.extend(("conjuro", k, j) for j in vivos)
        else:
            ops.append(("conjuro", k, None))

    ops.append(("bloquear", None, None))

    # Las pociones son de todo el equipo: cualquiera puede darle una a
    # cualquier aliado vivo mientras queden, aunque esté lleno, como en
    # cualquier RPG; decidir si conviene es cosa del jugador. Las que ya apartó
    # otro héroe en esta misma ronda no cuentan.
    for clave, cuantas in est["pociones"].items():
        if cuantas - est["reservadas"][clave] > 0:
            ops.extend(("pocion", clave, j) for j in vivos)
    return ops


def esPrioridad(accion, est, i):
    tipo, cual, _ = accion
    return tipo == "conjuro" and est["equipo"][i]["conjuros"][cual].get("prioridad", False)


def atacarJefe(i, poder, esFisico, elem, est, rng):
    yo, jefe = est["equipo"][i], est["jefe"]
    atk = yo["atk"] if esFisico else yo["atkMag"]
    defensa = jefe["defe"] if esFisico else jefe["defMag"]
    if est["buffAtk"][i] > 0:
        atk = atk * est["multBuffAtk"][i]

    dano, nota = danoAtaque(rng, atk, poder, esFisico, elem, yo["objeto"], defensa, est["objJefe"],
                            yo["vel"], jefe["vel"], 1.0, yo["minFis"], yo["probCritico"])
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


def proteccionesActivas(est):
    # Lo que reduce el daño que recibe cada héroe en este momento, para que la
    # pantalla lo muestre exactamente mientras dura. Solo va al registro.
    activas = []
    for j in range(len(est["equipo"])):
        tipos = []
        if est["hp"][j] > 0:
            if est["bloqueoTotal"][j]:
                tipos.append("total")
            if est["buffDef"][j] > 0:
                tipos.append("defensa")
            if est["bloq"][j]:
                tipos.append("bloqueo")
        activas.append(tipos)
    return activas


def objetivo_jefe(est, rng):
    # Ruleta entre los héroes vivos con la predisposición del jefe hacia cada
    # clase. A cada gen (de 0 a 7) se le suma una base: con 2, la clase
    # preferida sale a lo mucho 4.5 veces más que la que menos; con 1 eran ocho
    # veces y el jefe podía ensañarse con una sola clase. Con una base más alta
    # el jefe ya no alcanza a emparejar a los 15 equipos y F baja. El peso se
    # multiplica por la provocación del héroe, que solo el Tanque tiene arriba de 1.
    hp, equipo = est["hp"], est["equipo"]
    pred = est["crom"]["predisposicion"]
    vivos = [j for j in range(len(hp)) if hp[j] > 0]
    pesos = [(pred[equipo[j]["indiceClase"]] + basePredisposicion) * equipo[j]["provocacion"] for j in vivos]

    r = rng.random() * sum(pesos)
    for j, w in zip(vivos, pesos):
        r -= w
        if r < 0:
            return j
    return vivos[-1]


def objetivoVivo(j, est):
    # Las acciones se eligen al empezar la ronda. Si el aliado elegido cayó
    # antes de que le toque, la cura o la poción va al aliado vivo más herido.
    if est["hp"][j] > 0:
        return j
    vivos = [k for k in range(len(est["equipo"])) if est["hp"][k] > 0]
    return min(vivos, key=lambda k: (est["hp"][k] / est["equipo"][k]["hp"], k))


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
        if est["pociones"][cual] <= 0:
            # Otro se tomó la última antes; el turno se va en buscarla.
            hecho["accion"] = "Busca una " + nombrePocion[cual]
        else:
            est["pociones"][cual] -= 1
            j = objetivoVivo(objetivo if objetivo is not None else i, est)
            otro = est["equipo"][j]
            hecho["accion"] = ("Bebe " if j == i else "Le da a %s una " % otro["nombre"]) + nombrePocion[cual]
            if cual.startswith("hp"):
                antes = est["hp"][j]
                est["hp"][j] = min(otro["hp"], antes + int(efectoPocion[cual] * otro["hp"]))
                hecho["curas"].append((otro["nombre"], est["hp"][j] - antes))
            else:
                est["sp"][j] = min(otro["sp"], est["sp"][j] + int(efectoPocion[cual] * otro["sp"]))

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
                       if conj["enGrupo"] else [objetivoVivo(objetivo, est)])
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


def elegirAccion(i, est, politica):
    # Lo que el héroe i decide hacer en esta ronda, con lo que sabe al empezarla.
    if politica is None:
        accion = decidir_accion(i, est)
    else:
        accion = politica(i, est, accionesLegales(i, est))
    if accion[0] == "pocion":
        if accion[2] is None:
            accion = ("pocion", accion[1], i)
        est["reservadas"][accion[1]] += 1
    # A quién ya le va a llegar una cura o una poción en esta ronda, para que
    # los demás no se encimen sobre el mismo aliado.
    esCura = accion[0] == "conjuro" and est["equipo"][i]["conjuros"][accion[1]]["tipo"] == "cura"
    if (accion[0] == "pocion" or esCura) and accion[2] is not None:
        est["atendidos"].append(accion[2])
    return accion


def turnoHeroe(i, accion, est, rng, registro, adelantado=False):
    yo = est["equipo"][i]
    est["bloq"][i] = False
    if accion[0] == "pocion":
        est["reservadas"][accion[1]] -= 1
    hecho = ejecutarAccion(i, accion, est, rng)

    # El maná de las clases mágicas vuelve poco a poco al terminar su turno.
    if yo["regenSp"]:
        est["sp"][i] = min(yo["sp"], est["sp"][i] + yo["regenSp"])

    if registro is not None:
        hecho.update({"tipo": "turno", "ronda": est["ronda"], "actor": yo["nombre"],
                      "adelantado": adelantado, "muertos": [],
                      "hp_jefe": max(0, est["hp_jefe"]), "hp_equipo": list(est["hp"]),
                      "sp_equipo": list(est["sp"]), "protecciones": proteccionesActivas(est)})
        registro.append(hecho)


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
    # Los ataques de área cuentan la mitad en la ruleta: salen menos seguido.
    cola, pesos = est["cola"], est["crom"]["pesos"]
    ventana = cola[:tamanoVentana]

    def peso(k):
        return (pesos[k] + 1) * (pesoArea if HABILIDADES[est["ataques"][k]]["enArea"] else 1.0)

    r, elegido = rng.random() * sum(peso(k) for k in ventana), ventana[-1]
    for k in ventana:
        r -= peso(k)
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

    if est["ronda_fase2"] is None and est["hp_jefe"] < umbralFase2 * est["jefe"]["hp"]:
        entrarFase2(est, registro)

    hp_antes = list(hp)
    golpes, elem = [], None

    if est["cargando"] is not None:
        # El turno anterior se fue en cargar, así que ahora el ataque sale sin más.
        atq, est["cargando"] = est["cargando"], None
        nombre = atq["nombre"]
    else:
        # El jefe ya no bloquea: los algoritmos aprendían a usar el bloqueo
        # para alargar la pelea y emparejarla sin atacar.
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
                         "hp_jefe": est["hp_jefe"], "hp_equipo": list(hp),
                         "sp_equipo": list(est["sp"]), "protecciones": proteccionesActivas(est)})


def simular(crom, equipo=EQUIPO_BASE, semilla=0, registro=None, politica=None):
    # crom debe venir reparado. Si registro es una lista se le agregan los eventos
    # del combate para narrarlo después, sin cambiar ningún número. Si politica es
    # una función, ella decide por el equipo en lugar del jugador automático, y así
    # el modo interactivo usa las mismas reglas con las que se calificó al jefe.
    # La política recibe el héroe, el estado y sus acciones legales al empezar
    # la ronda, y devuelve una de esas acciones.
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
                         "hp_equipo": list(est["hp"]), "sp_equipo": list(est["sp"]),
                         "conjuros": {p["nombre"]: [c["nombre"] for c in p["conjuros"]] for p in equipo},
                         "orden": ["Jefe" if x == "J" else equipo[x]["nombre"] for x in est["actores"]]})

    for ronda in range(1, RONDAS_MAX + 1):
        est["ronda"] = ronda
        if registro is not None:
            registro.append({"tipo": "ronda", "ronda": ronda})

        # Todos los héroes eligen qué hacer antes de que pase nada, con lo que
        # saben al empezar la ronda: nadie puede esperar a ver qué hace el jefe
        # o a quién le pega para decidir.
        # Si alguien apartó una poción y cayó antes de usarla, vuelve a estar libre.
        est["reservadas"] = {k: 0 for k in pocionesIniciales}
        est["atendidos"] = []
        planes = {}
        for i in range(n):
            if est["hp"][i] > 0:
                planes[i] = elegirAccion(i, est, politica)
        if registro is not None:
            registro.append({"tipo": "planes", "ronda": ronda,
                             "acciones": {equipo[i]["nombre"]: planes[i] for i in planes}})

        # Luego se resuelve: primero los ataques que se adelantan, después
        # todos por velocidad.
        adelantados = [i for i in est["actores"] if i != "J" and i in planes and esPrioridad(planes[i], est, i)]
        orden = adelantados + [a for a in est["actores"] if a not in adelantados]
        for a in orden:
            if a == "J":
                turnoJefe(est, rng, registro)
                if all(h == 0 for h in est["hp"]):
                    return _resultado(False, est, False)
            elif est["hp"][a] > 0:
                turnoHeroe(a, planes[a], est, rng, registro, a in adelantados)
                if est["hp_jefe"] <= 0:
                    return _resultado(True, est, False)
                if est["ronda_fase2"] is None and est["hp_jefe"] < umbralFase2 * est["jefe"]["hp"]:
                    # Al bajar de la mitad el jefe se transforma en ese momento y
                    # la ronda se corta: lo que faltaba por hacer ya no pasa y
                    # todos vuelven a elegir con el jefe nuevo.
                    entrarFase2(est, registro)
                    break

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
