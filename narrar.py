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

notasGolpe = {"critico": " (critico)", "esquiva": " esquiva", "bloqueado": " lo bloquea por completo"}


def textoStats(s):
    return ("Vida %d   Ataque %d   Defensa %d   Ataque magico %d   Defensa magica %d   Velocidad %.1f"
            % (s["hp"], s["atk"], s["defe"], s["atkMag"], s["defMag"], s["vel"]))


def textoTurno(ev):
    # Arma la parte de un turno que dice a quién se le pegó o se le curó.
    partes = []
    for nombre, dano, nota in ev["golpes"]:
        if nota in ("esquiva", "bloqueado"):
            partes.append(nombre + notasGolpe[nota])
        else:
            partes.append("%s -%d%s" % (nombre, dano, notasGolpe.get(nota, "")))
    for nombre, cantidad in ev["curas"]:
        partes.append("%s +%d" % (nombre, cantidad))

    accion = ev["accion"]
    if ev["elem"] is not None:
        accion += " de " + m.NOMBRES_ELEM[ev["elem"]]
    if ev.get("adelantado"):
        accion += ", se adelanta"
    return accion, ", ".join(partes)


def lineas(registro, detalle=True):
    out, ini = [], registro[0]
    hp_jefe_max = ini["jefe"]["hp"]
    hp_eq_max = sum(ini["hp_equipo"])

    out.append("Jefe con %s, cambia a %s al bajar de 50%% de vida" % (ini["objeto"], ini["objeto2"]))
    out.append("  " + textoStats(ini["jefe"]))
    out.append("  Cola de ataques: " + ", ".join(ini["habs"]))
    out.append("Equipo: " + "   ".join("%s %d" % (n, h) for n, h in zip(ini["equipo"], ini["hp_equipo"])))
    for nombre in ini["equipo"]:
        if nombre in ("Mago", "Guerrero"):
            out.append("  Conjuros de %s: %s" % (nombre, ", ".join(ini["conjuros"][nombre])))
    out.append("Orden de turnos: " + ", ".join(ini["orden"]))

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
            out.append("  Fase 2: el jefe cambia a %s y aprende %s (vida %d, menos de la mitad)"
                       % (ev["objeto"], " y ".join(ev["nuevos"]), ev["hp_jefe"]))
            if detalle:
                out.append("    " + textoStats(ev["jefe"]))

        elif ev["tipo"] == "turno":
            hp_jefe, hp_eq = ev["hp_jefe"], sum(ev["hp_equipo"])
            if ev["actor"] == "Jefe":
                acciones_jefe.append(ev["accion"])
            if detalle:
                accion, efecto = textoTurno(ev)
                out.append(("  %-10s %-34s %s" % (ev["actor"], accion, efecto)).rstrip())
                for muerto in ev["muertos"]:
                    out.append("      %s cae" % muerto)

    if not detalle and len(registro) > 1:
        out.append(_resumen(ronda_actual, hp_jefe, hp_eq, acciones_jefe, hp_jefe_max, hp_eq_max))
    return out


def _resumen(ronda, hp_jefe, hp_eq, acciones, hp_jefe_max, hp_eq_max):
    return ("Ronda %2d | jefe %4d/%d | equipo %4d/%d | el jefe usó: %s"
            % (ronda, hp_jefe, hp_jefe_max, hp_eq, hp_eq_max, ", ".join(acciones) or "nada"))


def narrar(crom, equipo=m.EQUIPO_BASE, semilla=0, detalle=True):
    reg = []
    res = m.simular(m.reparar(crom), equipo, semilla, registro=reg)

    texto = lineas(reg, detalle)
    texto.append("")
    texto.append("Resultado: %s en %d rondas. Vida del equipo al final: %.0f%%"
                 % ("gana el equipo" if res["gana_equipo"] else "gana el jefe",
                    res["rondas"], 100 * res["hp_final_pct"]))
    if res["tope"]:
        texto.append("Se llegó al tope de %d rondas, cuenta como derrota del jefe." % m.RONDAS_MAX)
    return "\n".join(texto), res


def cargar_o_crear_mejor():
    # Un archivo guardado con el formato de una versión anterior del juego no
    # sirve, así que se trata igual que si no existiera.
    if os.path.exists(ARCHIVO_JEFE):
        with open(ARCHIVO_JEFE) as f:
            crom = json.load(f)
        if "predisposicion" in crom:
            return crom

    # Se corre el algoritmo una vez, con la misma semilla de siempre para que
    # el jefe sea reproducible.
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
    r = m.evaluar_jefe(crom)

    print("Tasa de victoria del equipo, promedio de los 15 equipos: %.2f\n" % r["p_victoria"])
    texto, _ = narrar(crom, m.EQUIPO_BASE, semilla=0, detalle=detalle)
    print(texto)
