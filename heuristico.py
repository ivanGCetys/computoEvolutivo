# Jugador automático. Controla al equipo cuando el algoritmo califica a un jefe.
# No planea a futuro: en cada turno hace lo primero que se cumpla de una lista
# de prioridades, como un jugador razonable que solo reacciona.
#
# Una acción es una tupla (tipo, cuál, objetivo):
#   ("basico", None, None)
#   ("conjuro", índice del conjuro, objetivo o None)
#   ("bloquear", None, None)
#   ("pocion", clave de la poción, None)
from reglas import PODER_BASICO

umbralPocion, umbralPocionGrande = 0.30, 0.20
umbralCuraMenor, umbralCuraMayor, umbralCuraGrupo = 0.55, 0.35, 0.50
umbralBuffDefensa, umbralBloqueoTotal = 0.70, 0.60
umbralBloqueoCarga = 0.50


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


def elegirPocionVida(i, est):
    poc = est["pociones"]
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
    masHerido = min(vivos, key=lambda j: (fraccionVida(j, est), j))

    for k, conj in enumerate(yo["conjuros"]):
        if conj["tipo"] == "cura" and conj["enGrupo"] and sp >= conj["costo"]:
            if sum(1 for j in vivos if fraccionVida(j, est) < umbralCuraGrupo) >= 2:
                return ("conjuro", k, None)

    # De las curas individuales se prueba primero la más fuerte.
    individuales = [(k, c) for k, c in enumerate(yo["conjuros"])
                    if c["tipo"] == "cura" and not c["enGrupo"] and sp >= c["costo"]]
    individuales.sort(key=lambda par: -par[1]["poder"])

    for pos, (k, conj) in enumerate(individuales):
        esLaFuerte = pos == 0 and len(individuales) > 1
        umbral = umbralCuraMayor if esLaFuerte else umbralCuraMenor
        if fraccionVida(masHerido, est) < umbral:
            return ("conjuro", k, masHerido)
    return None


def elegirPocionMana(i, est):
    # Las pociones de maná son para las clases que viven de sus conjuros. Las
    # demás solo las toman si ya no queda nadie así en pie.
    yo, poc = est["equipo"][i], est["pociones"]
    if poc["spChica"] + poc["spGrande"] == 0 or not yo["conjuros"]:
        return None

    if yo["regenSp"] == 0:
        quedaMagico = any(est["hp"][j] > 0 and h["regenSp"] > 0
                          for j, h in enumerate(est["equipo"]))
        if quedaMagico:
            return None

    masBarato = min(c["costo"] for c in yo["conjuros"])
    if est["sp"][i] >= masBarato:
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
    sp = est["sp"][i]
    vida = fraccionVida(i, est)

    if vida < umbralPocion:
        clave = elegirPocionVida(i, est)
        if clave:
            return ("pocion", clave, None)

    if any(c["tipo"] == "cura" for c in yo["conjuros"]):
        cura = elegirCura(i, est)
        if cura:
            return cura

    if est["cargando"] is not None:
        respuesta = responderACarga(i, est)
        if respuesta:
            return respuesta

    clave = elegirPocionMana(i, est)
    if clave:
        return ("pocion", clave, None)

    for k, conj in enumerate(yo["conjuros"]):
        if sp < conj["costo"]:
            continue
        if conj["tipo"] == "bloqueoTotal":
            if not est["bloqueoTotal"][i] and vida < umbralBloqueoTotal:
                return ("conjuro", k, None)
        elif conj["tipo"] == "buff" and conj["buff"][0] == "defe":
            if est["buffDef"][i] == 0 and vida < umbralBuffDefensa:
                return ("conjuro", k, None)

    # Para subir el ataque se prefiere el conjuro que además pega en el mismo turno.
    if est["buffAtk"][i] == 0:
        conBuff = [k for k, c in enumerate(yo["conjuros"])
                   if sp >= c["costo"] and c.get("buff") and c["buff"][0] == "atk"]
        if conBuff:
            return ("conjuro", max(conBuff, key=lambda k: yo["conjuros"][k]["tipo"] == "ataque"), None)

    return mejorAtaque(i, est)


def mejorAtaque(i, est, soloPrioridad=False):
    yo, sp = est["equipo"][i], est["sp"][i]
    mejor, mejorValor = None, 0.0
    if not soloPrioridad:
        mejor = ("basico", None, None)
        mejorValor = valorAtaque(i, est, PODER_BASICO, True, None)

    for k, conj in enumerate(yo["conjuros"]):
        if conj["tipo"] != "ataque" or sp < conj["costo"]:
            continue
        if soloPrioridad and not conj["prioridad"]:
            continue
        valor = valorAtaque(i, est, conj["poder"], conj["esFisico"], conj["elem"])
        if valor > mejorValor:
            mejor, mejorValor = ("conjuro", k, None), valor
    return mejor


def decidirPrioridad(i, est):
    # Se llama al empezar la ronda si el héroe puede adelantarse a alguien más
    # rápido. Devuelve None cuando prefiere esperar su turno normal.
    return mejorAtaque(i, est, soloPrioridad=True)
