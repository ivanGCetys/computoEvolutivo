"""
Modo interactivo: tú controlas al equipo contra el jefe que diseñó el AG.

Usa EXACTAMENTE el mismo motor y las mismas reglas con las que se evaluó al jefe.
Lo único que cambia es quién elige las acciones del equipo: en el AG lo hace el
heurístico, aquí lo haces tú. Por eso el resultado de tus partidas se puede
comparar con la tasa de victoria que predijo el fitness.

Uso:  python jugar.py             (con pausas, para demostrar)
      python jugar.py rapido      (sin pausas)
"""
import json
import sys
import time
import motor as m
import narrar

PAUSA = 1.2


class Partida:
    """Lleva el combate: muestra lo que pasa y pregunta qué hace cada héroe."""

    def __init__(self, pausa=PAUSA):
        self.registro = []
        self.mostrados = 1          # el evento 0 es la cabecera, se imprime aparte
        self.pausa = pausa

    # ---- mostrar lo que ha pasado desde la última pregunta ----
    def al_dia(self):
        nuevos = self.registro[self.mostrados:]
        self.mostrados = len(self.registro)
        if any(e["tipo"] in ("fase2", "ronda") or e["actor"] == "JEFE"
               for e in nuevos if e["tipo"] != "inicio"):
            print()                      # separa del prompt "> " del jugador
        for ev in nuevos:
            if ev["tipo"] == "ronda":
                print("\n" + "-" * 60)
                print(" RONDA %d" % ev["ronda"])
                print("-" * 60)
            elif ev["tipo"] == "fase2":
                self._pausa()
                print("  *** EL JEFE CAMBIA A %s *** (bajó del 50%% de HP)"
                      % m.NOMBRES_ELEM[ev["elem"]].upper())
            elif ev["tipo"] == "turno" and ev["actor"] == "JEFE":
                self._pausa()
                golpes = ", ".join("%s pierde %d HP" % (k, v) for k, v in ev["danos"].items())
                print("  EL JEFE usa %s. %s" % (ev["accion"], golpes or "No hace daño."))
                for muerto in ev["muertos"]:
                    print("  *** %s cae ***" % muerto)

    def _pausa(self):
        if self.pausa:
            time.sleep(self.pausa)

    # ---- la política: aquí pregunta el menú ----
    def turno(self, i, equipo, hp, sp, pociones, elem_jefe, ctx):
        self.al_dia()
        yo = equipo[i]
        print("\n  Jefe: %d/%d HP (%s)   |   Pociones: %d"
              % (ctx["hp_jefe"], ctx["jefe"]["hp"], m.NOMBRES_ELEM[elem_jefe], pociones))
        print("  " + "  ".join("%s %d/%d%s" % (p["nombre"], hp[j], p["hp"], "" if hp[j] else " (caído)")
                               for j, p in enumerate(equipo)))
        if ctx["guardia"]:
            print("  (el jefe está en guardia: recibirá la mitad del daño)")
        print("\n  Turno de %s (%s, SP %d):" % (yo["nombre"], m.NOMBRES_ELEM[yo["elem"]], sp[i]))

        opciones = self._opciones(i, equipo, hp, sp, pociones, elem_jefe,
                                  m.GUARDIA_MULT if ctx["guardia"] else 1.0)
        for n, (_, _, texto) in enumerate(opciones, start=1):
            print("    %d) %s" % (n, texto))
        return self._leer(opciones, equipo, hp)

    def _opciones(self, i, equipo, hp, sp, pociones, elem_jefe, mg=1.0):
        """Solo ofrece acciones legales, con el daño EXACTO al lado (mg = guardia)."""
        yo, jefe_def = equipo[i], self.def_jefe
        ops = []
        d_bas = m.calcular_dano(yo["atk"], m.PODER_BASICO, 1.0, jefe_def, mg)
        ops.append(("basico", None, "Ataque básico        (%d de daño, gratis)" % d_bas))

        costo_f = int(m.COSTO_FUERTE * yo["hp"])
        if hp[i] - costo_f >= 1:
            d_f = m.calcular_dano(yo["atk"], m.PODER_FUERTE, 1.0, jefe_def, mg)
            ops.append(("fuerte", None, "Ataque fuerte        (%d de daño, te cuesta %d HP)" % (d_f, costo_f)))

        if sp[i] >= m.COSTO_MAGIA:
            mult = m.mult_elemental(yo["elem"], elem_jefe)
            d_m = m.calcular_dano(yo["atk"], m.PODER_MAGIA, mult, jefe_def, mg)
            efecto = {1.5: " MUY EFECTIVO", 0.5: " poco efectivo"}.get(mult, "")
            ops.append(("magia", None, "Magia                (%d de daño%s, %d SP)" % (d_m, efecto, m.COSTO_MAGIA)))

        if yo["cura"] and sp[i] >= m.COSTO_CURA:
            ops.append(("curar", "elegir", "Curar a un aliado    (+25%% de su HP máximo, %d SP)" % m.COSTO_CURA))

        if pociones > 0 and hp[i] < yo["hp"]:
            ops.append(("pocion", i, "Beber poción         (+%d HP, quedan %d)"
                        % (int(m.POCION_HP * yo["hp"]), pociones)))
        return ops

    def _leer(self, opciones, equipo, hp):
        while True:
            try:
                txt = input("  > ").strip()
            except EOFError:
                print("  (sin entrada: se usa la opción 1)")
                txt = "1"
            if txt.isdigit() and 1 <= int(txt) <= len(opciones):
                accion, obj, _ = opciones[int(txt) - 1]
                if obj == "elegir":
                    obj = self._elegir_aliado(equipo, hp)
                return accion, obj
            print("  Escribe un número del 1 al %d." % len(opciones))

    def _elegir_aliado(self, equipo, hp):
        vivos = [j for j in range(len(equipo)) if hp[j] > 0]
        print("    ¿A quién curas?")
        for n, j in enumerate(vivos, start=1):
            print("      %d) %s  %d/%d HP" % (n, equipo[j]["nombre"], hp[j], equipo[j]["hp"]))
        while True:
            try:
                txt = input("    > ").strip()
            except EOFError:
                return vivos[0]
            if txt.isdigit() and 1 <= int(txt) <= len(vivos):
                return vivos[int(txt) - 1]
            print("    Escribe un número del 1 al %d." % len(vivos))


ROLES = {"Guerrero": "el que más pega", "Curandero": "puede curar (20 SP)",
         "Explorador": "el más rápido", "Tanque": "más HP y DEF"}


def mostrar_heroes():
    """Stats de los héroes. Son iguales en los 4 equipos, así que se muestran una vez."""
    print("\nTUS HÉROES (iguales en los cuatro equipos)\n")
    print("  %-11s %5s %5s %5s %5s %5s   %s" % ("Héroe", "HP", "SP", "ATK", "DEF", "VEL", "Rol"))
    for p in m.EQUIPO_BASE:
        print("  %-11s %5d %5d %5d %5d %5d   %s"
              % (p["nombre"], p["hp"], p["sp"], p["atk"], p["defe"], p["vel"], ROLES.get(p["nombre"], "")))
    print("\n  Acciones: ataque básico (gratis) | ataque fuerte (x2 de daño, cuesta 20% de tu HP)")
    print("            magia (%d SP, usa tu elemento) | poción (+40%% HP, %d para todo el equipo)"
          % (m.COSTO_MAGIA, m.POCIONES_INICIALES))
    print("  Elementos: fuego > hielo > viento > tierra > fuego")
    print("             x1.5 contra el que vences, x0.5 contra el que te vence")


def elegir_equipo():
    mostrar_heroes()
    print("\nElige tu equipo. Lo único que cambia es qué elemento le toca a cada héroe:\n")
    print("     %s" % "".join("%-12s" % p["nombre"] for p in m.EQUIPO_BASE))
    for k, eq in m.EQUIPOS.items():
        print("  %s) %s" % (k, "".join("%-12s" % m.NOMBRES_ELEM[p["elem"]] for p in eq)))
    while True:
        try:
            k = input("\n  > ").strip().upper()
        except EOFError:
            return "A"
        if k in m.EQUIPOS:
            return k
        print("  Escribe A, B, C o D.")


def jugar(crom, clave_equipo=None, semilla=None, pausa=PAUSA):
    equipo = m.EQUIPOS[clave_equipo or elegir_equipo()]
    if semilla is None:
        semilla = int(time.time()) % 10000        # cada partida es distinta
    jefe = m.stats_jefe(crom)

    p = Partida(pausa)
    p.def_jefe = jefe["defe"]
    print("\n" + "=" * 60)
    print(" EL JEFE:  %s   (cambia a %s bajo el 50%% de HP)"
          % (m.NOMBRES_ELEM[crom["elem1"]].upper(), m.NOMBRES_ELEM[crom["elem2"]].upper()))
    print(" HP %d   ATK %d   DEF %d   VEL %.1f"
          % (jefe["hp"], jefe["atk"], jefe["defe"], jefe["vel"]))
    print(" Sus habilidades: " + ", ".join(m.HABILIDADES[h][0] for h in crom["habs"]))
    print("=" * 60)

    res = m.simular(crom, equipo, semilla, registro=p.registro, politica=p.turno)
    p.al_dia()

    print("\n" + "=" * 60)
    if res["gana_equipo"]:
        print(" ¡GANASTE! en %d rondas, con %.0f%% del HP del equipo."
              % (res["rondas"], 100 * res["hp_final_pct"]))
        if res["tope"]:
            print(" (se agotaron las %d rondas: cuenta como derrota del jefe)" % m.RONDAS_MAX)
    else:
        print(" PERDISTE en la ronda %d. Todo el equipo cayó." % res["rondas"])
    print("=" * 60)
    return res


if __name__ == "__main__":
    pausa = 0 if "rapido" in sys.argv else PAUSA
    crom = narrar.cargar_o_crear_mejor()
    pred = m.evaluar_jefe(crom, n=30, semilla=0)
    print("\nEste jefe lo diseñó el AG (F = %.4f)." % pred["fitness"])
    print("Contra el heurístico gana el equipo así: %s"
          % {k: "%.0f%%" % (100 * v) for k, v in pred["p_victoria_equipos"].items()})
    print("A ver si tú lo haces mejor o peor que la máquina.")
    jugar(crom, pausa=pausa)
