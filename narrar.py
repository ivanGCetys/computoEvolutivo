# Convierte el registro de un combate en texto legible. Sirve para ver qué pasa
# turno por turno y es la base del modo interactivo.
#
# Uso: python narrar.py            combate detallado del mejor jefe guardado
#      python narrar.py resumen    una línea por ronda
import json
import os
import sys
import motor as m

ARCHIVO_JEFE = "mejor_jefe.json"

ACCIONES = {"pocion": "bebe una poción", "curar": "cura a", "magia": "lanza magia",
            "fuerte": "ataque fuerte", "basico": "ataque básico"}


def lineas(registro, detalle=True):
    out, ini = [], registro[0]
    jefe, elem = ini["jefe"], m.NOMBRES_ELEM
    hp_jefe_max = jefe["hp"]
    hp_eq_max = sum(ini["hp_equipo"])

    out.append("Jefe de %s, cambia a %s al bajar de 50%% de HP"
               % (elem[ini["elem_jefe"]], elem[ini["elem_fase2"]]))
    out.append("  HP %d   ATK %d   DEF %d   VEL %.1f"
               % (jefe["hp"], jefe["atk"], jefe["defe"], jefe["vel"]))
    out.append("  Habilidades: " + ", ".join(ini["habs"]))
    out.append("Equipo: " + "   ".join("%s (%s) %d" % (n, elem[e], h) for n, e, h
                                       in zip(ini["equipo"], ini["elems_equipo"], ini["hp_equipo"])))
    out.append("Orden de turnos: " + ", ".join(x.capitalize() for x in ini["orden"]))

    # En modo resumen se guarda el estado con que empezó cada ronda y lo que usó el jefe.
    hp_jefe, hp_eq, acciones_jefe = hp_jefe_max, hp_eq_max, []
    for ev in registro[1:]:
        if ev["tipo"] == "ronda":
            if detalle:
                out.append("")
                out.append("Ronda %d   jefe %d/%d   equipo %d/%d"
                           % (ev["ronda"], hp_jefe, hp_jefe_max, hp_eq, hp_eq_max))
            else:
                if ev["ronda"] > 1:
                    out.append(_resumen(ev["ronda"] - 1, hp_jefe, hp_eq, acciones_jefe,
                                        hp_jefe_max, hp_eq_max))
                acciones_jefe = []
            ronda_actual = ev["ronda"]

        elif ev["tipo"] == "fase2":
            out.append("  Fase 2: el jefe cambia a %s (HP %d, menos de la mitad)"
                       % (elem[ev["elem"]], ev["hp_jefe"]))

        elif ev["tipo"] == "turno":
            hp_jefe, hp_eq = ev["hp_jefe"], sum(ev["hp_equipo"])
            if ev["actor"] == "JEFE":
                acciones_jefe.append(ev["accion"])
                if detalle:
                    sufijo = " (%s)" % elem[ev["elem"]] if ev["elem"] is not None else ""
                    golpes = ", ".join("%s -%d" % (k, v) for k, v in ev["danos"].items()) or "sin daño"
                    out.append("  %-13s %-16s%-9s %s" % ("Jefe", ev["accion"], sufijo, golpes))
                    for muerto in ev["muertos"]:
                        out.append("      %s cae" % muerto)

            elif detalle:
                verbo = ACCIONES[ev["accion"]]
                if ev["accion"] == "curar":
                    detalle_txt = "%s %s  (+%d HP)" % (verbo, ev["objetivo"], ev["curado"])
                elif ev["accion"] == "pocion":
                    detalle_txt = "%s  (+%d HP)" % (verbo, ev["cambio_propio"])
                else:
                    detalle_txt = "%s  jefe -%d" % (verbo, ev["dano_jefe"])
                    if ev["cambio_propio"] < 0:
                        detalle_txt += "  (le cuesta %d HP)" % -ev["cambio_propio"]
                    if ev["jefe_en_guardia"]:
                        detalle_txt += "  (el jefe estaba en guardia)"
                out.append("  %-13s %s" % (ev["actor"], detalle_txt))

    if not detalle:
        out.append(_resumen(ronda_actual, hp_jefe, hp_eq, acciones_jefe, hp_jefe_max, hp_eq_max))
    return out


def _resumen(ronda, hp_jefe, hp_eq, acciones, hp_jefe_max, hp_eq_max):
    return ("Ronda %2d | jefe %4d/%d | equipo %4d/%d | el jefe usó: %s"
            % (ronda, hp_jefe, hp_jefe_max, hp_eq, hp_eq_max, ", ".join(acciones) or "nada"))


def narrar(crom, equipo=m.EQUIPO_A, semilla=0, detalle=True):
    reg = []
    res = m.simular(m.reparar(crom), equipo, semilla, registro=reg)

    texto = lineas(reg, detalle)
    texto.append("")
    texto.append("Resultado: %s en %d rondas. HP del equipo al final: %.0f%%"
                 % ("gana el equipo" if res["gana_equipo"] else "gana el jefe",
                    res["rondas"], 100 * res["hp_final_pct"]))
    if res["tope"]:
        texto.append("Se llegó al tope de %d rondas, cuenta como derrota del jefe." % m.RONDAS_MAX)
    return "\n".join(texto), res


def cargar_o_crear_mejor():
    if os.path.exists(ARCHIVO_JEFE):
        with open(ARCHIVO_JEFE) as f:
            return json.load(f)

    # Sin archivo guardado se corre el algoritmo una vez, con la misma semilla
    # de siempre para que el jefe sea reproducible.
    import genetico as g
    bits, c, _ = g.correr_ag(semilla_rng=1, verbose=False)
    crom = g.decodificar(bits)
    crom["_fitness"] = 1 - c
    with open(ARCHIVO_JEFE, "w") as f:
        json.dump(crom, f, indent=2)
    return crom


if __name__ == "__main__":
    detalle = "resumen" not in sys.argv
    crom = cargar_o_crear_mejor()
    r = m.evaluar_jefe(crom, n=30, semilla=0)

    print("Tasa de victoria del equipo por reparto: %s\n"
          % {k: round(v, 2) for k, v in r["p_victoria_equipos"].items()})
    texto, _ = narrar(crom, m.EQUIPOS[r["peor_equipo"]], semilla=0, detalle=detalle)
    print(texto)
