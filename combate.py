# Simulación de un combate por turnos entre el equipo y un jefe.
# No imprime nada y todo el azar sale de random.Random(semilla), así que la
# misma semilla siempre da el mismo combate.
import random

from reglas import *
from jefe import *

RONDAS_MAX = 40


def decidir_accion(i, equipo, hp, sp, pociones, elem_jefe):
    # Jugador automático: hace lo primero que se cumpla, en este orden.
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
    # Va por el héroe débil a su elemento actual y, si no hay, por el de menos vida.
    vivos = [j for j in range(len(equipo)) if hp[j] > 0]
    for j in vivos:
        if VENCE[elem_jefe] == equipo[j]["elem"]:
            return j
    return min(vivos, key=lambda j: (hp[j], j))


def simular(crom, equipo=EQUIPO_BASE, semilla=0, registro=None, politica=None):
    # crom debe venir reparado. Si registro es una lista se le agregan los eventos
    # del combate para narrarlo después, sin cambiar ningún número. Si politica es
    # una función, ella decide por el equipo en lugar del jugador automático, y así
    # el modo interactivo usa las mismas reglas con las que se calificó al jefe.
    rng = random.Random(semilla)
    jefe = stats_jefe(crom)
    n = len(equipo)
    hp = [p["hp"] for p in equipo]
    sp = [p["sp"] for p in equipo]
    bloq = [1.0] * n
    pociones = POCIONES_INICIALES
    hp_jefe, elem_jefe, guardia = jefe["hp"], crom["elem1"], False
    ronda_fase2 = None
    espera = [0, 0, 0, 0]
    usos = [0, 0, 0, 0]
    primera_muerte = None

    # El orden es fijo: mayor velocidad primero. En empate va primero el equipo
    # y después el orden de la tabla.
    actores = list(range(n)) + ["J"]
    actores.sort(key=lambda a: (-jefe["vel"], 1, 0) if a == "J" else (-equipo[a]["vel"], 0, a))

    if registro is not None:
        registro.append({"tipo": "inicio", "jefe": dict(jefe), "elem_jefe": elem_jefe,
                         "elem_fase2": crom["elem2"], "hp_equipo": list(hp),
                         "equipo": [p["nombre"] for p in equipo],
                         "elems_equipo": [p["elem"] for p in equipo],
                         "orden": ["JEFE" if x == "J" else equipo[x]["nombre"] for x in actores],
                         "habs": [HABILIDADES[h][0] for h in crom["habs"]]})

    for ronda in range(1, RONDAS_MAX + 1):
        if registro is not None:
            registro.append({"tipo": "ronda", "ronda": ronda})

        for a in actores:
            if a == "J":
                guardia = False
                if ronda_fase2 is None and hp_jefe < 0.5 * jefe["hp"]:
                    elem_jefe, ronda_fase2 = crom["elem2"], ronda
                    if registro is not None:
                        registro.append({"tipo": "fase2", "ronda": ronda, "elem": elem_jefe,
                                         "hp_jefe": hp_jefe})

                # Ruleta con los pesos de las habilidades que no están en espera.
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
                hp_antes = list(hp) if registro is not None else None

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

                if registro is not None:
                    danos = {equipo[j]["nombre"]: hp_antes[j] - hp[j]
                             for j in range(n) if hp_antes[j] != hp[j]}
                    registro.append({"tipo": "turno", "ronda": ronda, "actor": "JEFE",
                                     "accion": nombre, "elem": elem_jefe if con_elem else None,
                                     "danos": danos, "hp_equipo": list(hp), "hp_jefe": hp_jefe,
                                     "muertos": [equipo[j]["nombre"] for j in range(n)
                                                 if hp[j] == 0 and hp_antes[j] > 0]})

                if primera_muerte is None and any(h == 0 for h in hp):
                    primera_muerte = ronda
                if all(h == 0 for h in hp):
                    return _resultado(False, ronda, hp, usos, primera_muerte, False, hp_jefe, ronda_fase2, equipo)

            else:
                i = a
                if hp[i] <= 0:
                    continue
                bloq[i] = 1.0

                if politica is None:
                    accion, obj = decidir_accion(i, equipo, hp, sp, pociones, elem_jefe)
                else:
                    accion, obj = politica(i, equipo, hp, sp, pociones, elem_jefe,
                                           {"hp_jefe": hp_jefe, "jefe": jefe, "ronda": ronda,
                                            "guardia": guardia, "elem_jefe": elem_jefe})
                yo = equipo[i]
                mg = GUARDIA_MULT if guardia else 1.0
                if registro is not None:
                    hp_jefe_antes, hp_antes = hp_jefe, list(hp)

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

                if registro is not None:
                    registro.append({"tipo": "turno", "ronda": ronda, "actor": yo["nombre"],
                                     "accion": accion, "objetivo": equipo[obj]["nombre"] if obj is not None else None,
                                     "dano_jefe": hp_jefe_antes - hp_jefe,
                                     "cambio_propio": hp[i] - hp_antes[i],
                                     "curado": hp[obj] - hp_antes[obj] if accion == "curar" and obj is not None else 0,
                                     "jefe_en_guardia": guardia,
                                     "hp_jefe": max(0, hp_jefe), "hp_equipo": list(hp)})

                if hp_jefe <= 0:
                    return _resultado(True, ronda, hp, usos, primera_muerte, False, max(0, hp_jefe), ronda_fase2, equipo)

    # Llegar al tope de rondas cuenta como derrota del jefe.
    return _resultado(True, RONDAS_MAX, hp, usos, primera_muerte, True, hp_jefe, ronda_fase2, equipo)


def _resultado(gana_equipo, rondas, hp, usos, primera_muerte, tope, hp_jefe, ronda_fase2,
               equipo=EQUIPO_BASE):
    # El porcentaje final se saca contra la vida total del equipo que peleó y no
    # contra un número fijo, para que siga valiendo si el equipo cambia.
    return {"gana_equipo": gana_equipo, "rondas": rondas,
            "hp_final_pct": sum(hp) / sum(p["hp"] for p in equipo),
            "hp_equipo": list(hp), "vivos": sum(1 for h in hp if h > 0), "usos": usos,
            "primera_muerte": primera_muerte, "tope": tope,
            "hp_jefe": hp_jefe, "ronda_fase2": ronda_fase2}
