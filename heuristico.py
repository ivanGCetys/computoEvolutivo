# Jugador automático. Controla al equipo cuando el algoritmo califica a un jefe.
# No planea a futuro: al empezar cada ronda elige para cada héroe lo primero que
# se cumpla de una lista de prioridades. Cada clase sigue la de su papel, como
# la jugaría una persona en un RPG por turnos:
#   curandero (Clérigo)  cura en cuanto alguien baja un poco y solo pega si
#                        todos están casi llenos
#   mago                 vive de su magia: repone maná antes de quedarse sin
#                        conjuros y guarda el poderoso para cuando conviene
#   tanque               mantiene su defensa arriba para aguantar los golpes
#   guerreros (Guerrero, Pícaro, Berserker)  usan sus técnicas siempre que les
#                        alcanza el maná y el ataque básico cuando no
# Todos toman poción si están por caer, le pasan una al aliado que lo está si
# ellos van bien, y se cubren cuando el jefe carga un golpe fuerte.
#
# Una acción es una tupla (tipo, cuál, objetivo):
#   ("basico", None, None)
#   ("conjuro", índice del conjuro, objetivo o None)
#   ("bloquear", None, None)
#   ("pocion", clave de la poción, a quién se la da; None es a sí mismo)
from reglas import PODER_BASICO

umbralPocion, umbralPocionGrande, umbralPocionAliado = 0.30, 0.20, 0.25
umbralCuraMenor, umbralCuraMayor, umbralCuraGrupo = 0.80, 0.50, 0.75
umbralBuffDefensa, umbralBloqueoTotal = 0.50, 0.40
umbralBloqueoCarga = 0.50
costoPoderoso = 40

papeles = {"Clerigo": "curandero", "Mago": "mago", "Tanque": "tanque"}


def papelDe(heroe):
    return papeles.get(heroe["nombre"], "guerrero")


def fraccionVida(j, est):
    return est["hp"][j] / est["equipo"][j]["hp"]


def valorAtaque(i, est, poder, esFisico, elem):
    # Daño esperado sin contar variación, para comparar opciones entre sí.
    yo, jefe = est["equipo"][i], est["jefe"]
    atk = yo["atk"] if esFisico else yo["atkMag"]
    defensa = jefe["defe"] if esFisico else jefe["defMag"]

    mult = 1.0
    if elem is not None:
        mult = yo["objeto"]["multAtk"][elem]
        defensa = defensa * est["objJefe"]["multDef"][elem]
    return atk * poder * mult * 100 / (100 + defensa)


def disponibles(est):
    # Las pociones que quedan sin contar las que otro héroe ya apartó esta ronda.
    reservadas = est.get("reservadas", {})
    return {k: v - reservadas.get(k, 0) for k, v in est["pociones"].items()}


def atendidos(est):
    # Los aliados a los que otro héroe ya les va a dar una cura o una poción en esta ronda.
    return est.get("atendidos", [])


def elegirPocionVida(i, est):
    poc = disponibles(est)
    if fraccionVida(i, est) < umbralPocionGrande and poc["hpGrande"] > 0:
        return "hpGrande"
    if poc["hpChica"] > 0:
        return "hpChica"
    if poc["hpGrande"] > 0:
        return "hpGrande"
    return None


def elegirCura(i, est):
    yo = est["equipo"][i]
    sp = est["sp"][i]
    vivos = [j for j in range(len(est["equipo"])) if est["hp"][j] > 0]
    sinAtender = [j for j in vivos if j not in atendidos(est)]

    for k, conj in enumerate(yo["conjuros"]):
        if conj["tipo"] == "cura" and conj["enGrupo"] and sp >= conj["costo"]:
            if sum(1 for j in sinAtender if fraccionVida(j, est) < umbralCuraGrupo) >= 2:
                return ("conjuro", k, None)

    if not sinAtender:
        return None
    masHerido = min(sinAtender, key=lambda j: (fraccionVida(j, est), j))

    # Con alguien muy herido va la cura fuerte; si no, la menor, que cuesta menos.
    individuales = [(k, c) for k, c in enumerate(yo["conjuros"])
                    if c["tipo"] == "cura" and not c["enGrupo"] and sp >= c["costo"]]
    individuales.sort(key=lambda par: -par[1]["poder"])
    for pos, (k, conj) in enumerate(individuales):
        esLaFuerte = pos == 0 and len(individuales) > 1
        umbral = umbralCuraMayor if esLaFuerte else umbralCuraMenor
        if fraccionVida(masHerido, est) < umbral:
            return ("conjuro", k, masHerido)
    return None


def pocionParaAliado(i, est):
    # Un héroe que está bien le pasa una poción al aliado que está por caer,
    # si nadie más lo va a atender en esta ronda.
    if fraccionVida(i, est) < 0.5:
        return None
    enPeligro = [j for j in range(len(est["equipo"]))
                 if j != i and est["hp"][j] > 0 and j not in atendidos(est)
                 and fraccionVida(j, est) < umbralPocionAliado]
    if not enPeligro:
        return None
    j = min(enPeligro, key=lambda j: (fraccionVida(j, est), j))
    poc = disponibles(est)
    for clave in ("hpGrande", "hpChica"):
        if poc[clave] > 0:
            return ("pocion", clave, j)
    return None


def elegirPocionMana(i, est, reserva=0):
    # Las pociones de maná son para las clases que viven de sus conjuros. Las
    # demás solo las toman si ya no queda nadie así en pie. reserva es el
    # maná que el héroe quiere tener a la mano además de su conjuro más barato.
    yo, poc = est["equipo"][i], disponibles(est)
    if poc["spChica"] + poc["spGrande"] == 0 or not yo["conjuros"]:
        return None

    if papelDe(yo) not in ("mago", "curandero"):
        quedaMagico = any(est["hp"][j] > 0 and papelDe(h) in ("mago", "curandero")
                          for j, h in enumerate(est["equipo"]))
        if quedaMagico:
            return None

    masBarato = min(c["costo"] for c in yo["conjuros"])
    if est["sp"][i] >= masBarato + reserva:
        return None
    return "spChica" if poc["spChica"] > 0 else "spGrande"


def responderACarga(i, est):
    # Cuando el jefe está cargando, su siguiente turno trae un golpe fuerte.
    # Quien puede anularlo lo anula, y quien anda bajo de vida bloquea.
    yo = est["equipo"][i]
    for k, conj in enumerate(yo["conjuros"]):
        if conj["tipo"] == "bloqueoTotal" and est["sp"][i] >= conj["costo"] and not est["bloqueoTotal"][i]:
            return ("conjuro", k, None)

    if fraccionVida(i, est) < umbralBloqueoCarga:
        return ("bloquear", None, None)
    return None


def decidir_accion(i, est):
    yo = est["equipo"][i]
    papel = papelDe(yo)

    if fraccionVida(i, est) < umbralPocion and i not in atendidos(est):
        clave = elegirPocionVida(i, est)
        if clave:
            return ("pocion", clave, i)

    if papel == "curandero":
        cura = elegirCura(i, est)
        if cura:
            return cura
    else:
        ayuda = pocionParaAliado(i, est)
        if ayuda:
            return ayuda

    if est["cargando"] is not None:
        respuesta = responderACarga(i, est)
        if respuesta:
            return respuesta

    if papel == "curandero":
        return jugarCurandero(i, est)
    if papel == "mago":
        return jugarMago(i, est)
    if papel == "tanque":
        return jugarTanque(i, est)
    return jugarGuerrero(i, est)


def jugarCurandero(i, est):
    # Nadie necesita cura: repone maná si ya no le alcanza para curar y, si
    # no, pega con lo que tenga.
    clave = elegirPocionMana(i, est)
    if clave:
        return ("pocion", clave, i)
    return mejorAtaque(i, est)


def jugarMago(i, est):
    yo, sp = est["equipo"][i], est["sp"][i]
    # Repone maná antes de quedarse sin su conjuro de en medio.
    normales = [c["costo"] for c in yo["conjuros"] if c["costo"] < costoPoderoso]
    reserva = (max(normales) - min(normales)) if normales else 0
    clave = elegirPocionMana(i, est, reserva)
    if clave:
        return ("pocion", clave, i)

    # El poderoso cuesta más de la mitad de su maná: lo usa contra un objeto
    # débil a su elemento o cuando el jefe ya está en su segunda fase.
    for k, conj in enumerate(yo["conjuros"]):
        if conj["tipo"] == "ataque" and conj["costo"] >= costoPoderoso and sp >= conj["costo"]:
            debil = est["objJefe"]["multDef"][conj["elem"]] < 1.0
            if debil or est["ronda_fase2"] is not None:
                return ("conjuro", k, None)
    return mejorAtaque(i, est, soloNormales=True)


def jugarTanque(i, est):
    yo, sp = est["equipo"][i], est["sp"][i]
    for k, conj in enumerate(yo["conjuros"]):
        if sp < conj["costo"]:
            continue
        if conj["tipo"] == "buff" and conj["buff"][0] == "defe" and est["buffDef"][i] == 0:
            return ("conjuro", k, None)
        if conj["tipo"] == "bloqueoTotal" and not est["bloqueoTotal"][i] and fraccionVida(i, est) < umbralBloqueoTotal:
            return ("conjuro", k, None)
    return ("basico", None, None)


def jugarGuerrero(i, est):
    yo, sp = est["equipo"][i], est["sp"][i]
    for k, conj in enumerate(yo["conjuros"]):
        if conj["tipo"] == "buff" and conj["buff"][0] == "defe" and sp >= conj["costo"]:
            if est["buffDef"][i] == 0 and fraccionVida(i, est) < umbralBuffDefensa:
                return ("conjuro", k, None)

    # Para subir el ataque se prefiere el conjuro que además pega en el mismo turno.
    if est["buffAtk"][i] == 0:
        conBuff = [k for k, c in enumerate(yo["conjuros"])
                   if sp >= c["costo"] and c.get("buff") and c["buff"][0] == "atk"]
        if conBuff:
            return ("conjuro", max(conBuff, key=lambda k: yo["conjuros"][k]["tipo"] == "ataque"), None)

    # Sus técnicas siempre que le alcance el maná, la que más pegue.
    tecnicas = [k for k, c in enumerate(yo["conjuros"]) if c["tipo"] == "ataque" and sp >= c["costo"]]
    if tecnicas:
        conj = yo["conjuros"]
        mejor = max(tecnicas, key=lambda k: valorAtaque(i, est, conj[k]["poder"], conj[k]["esFisico"], conj[k]["elem"]))
        return ("conjuro", mejor, None)
    return ("basico", None, None)


def mejorAtaque(i, est, soloNormales=False):
    yo, sp = est["equipo"][i], est["sp"][i]
    mejor = ("basico", None, None)
    mejorValor = valorAtaque(i, est, PODER_BASICO, True, None)

    for k, conj in enumerate(yo["conjuros"]):
        if conj["tipo"] != "ataque" or sp < conj["costo"] or (soloNormales and conj["costo"] >= costoPoderoso):
            continue
        valor = valorAtaque(i, est, conj["poder"], conj["esFisico"], conj["elem"])
        if valor > mejorValor:
            mejor, mejorValor = ("conjuro", k, None), valor
    return mejor
