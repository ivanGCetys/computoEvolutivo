# Modo interactivo: tú controlas al equipo contra un jefe del frente de NSGA-II.
# Usa el mismo motor y las mismas reglas con las que se evaluó al jefe, solo
# cambia quién elige las acciones del equipo.
#
# Uso: python jugar.py           con pausas, para demostrar
#      python jugar.py rapido    sin pausas
import sys
import time
import motor as m
import narrar

PAUSA = 1.2


def rangoDano(i, est, poder, esFisico, elem, buff=None):
    # Daño mínimo y máximo sin contar crítico ni esquive, con todo lo que el
    # motor aplicaría en este momento: objetos y buff de ataque.
    # buff es el del propio conjuro: el motor lo aplica antes de pegar, así que
    # ese mismo golpe ya sale con el ataque subido.
    yo, jefe = est["equipo"][i], est["jefe"]
    atk = yo["atk"] if esFisico else yo["atkMag"]
    defensa = jefe["defe"] if esFisico else jefe["defMag"]
    if buff is not None and buff[0] == "atk":
        atk = atk * buff[1]
    elif est["buffAtk"][i] > 0:
        atk = atk * est["multBuffAtk"][i]

    mult = 1.0
    if elem is not None:
        mult = yo["objeto"]["multAtk"][elem]
        defensa = defensa * est["objJefe"]["multDef"][elem]

    lo, hi = (yo["minFis"], m.variacionFisMax) if esFisico else (m.variacionMagMin, m.variacionMagMax)
    return (m.calcular_dano(atk, poder, mult * lo, defensa),
            m.calcular_dano(atk, poder, mult * hi, defensa))


def textoOpcion(i, accion, est):
    tipo, cual, objetivo = accion
    yo = est["equipo"][i]

    if tipo == "basico":
        return "Ataque basico (fisico, %d a %d de daño, gratis)" % rangoDano(i, est, m.PODER_BASICO, True, None)
    if tipo == "bloquear":
        return "Bloquear (recibe la mitad del daño hasta su siguiente turno)"
    if tipo == "pocion":
        # Las pociones son del equipo; las que otro ya apartó esta ronda no cuentan.
        quien = est["equipo"][i if objetivo is None else objetivo]
        base = quien["hp"] if cual.startswith("hp") else quien["sp"]
        que = "vida" if cual.startswith("hp") else "mana"
        quedan = est["pociones"][cual] - est.get("reservadas", {}).get(cual, 0)
        aQuien = "" if objetivo in (None, i) else " a " + quien["nombre"]
        return "%s%s (+%d de %s, quedan %d)" % (m.nombrePocion[cual].capitalize(), aQuien,
                                                int(m.efectoPocion[cual] * base), que, quedan)

    conj = yo["conjuros"][cual]
    costo = "%d de mana" % conj["costo"]
    if conj["tipo"] == "ataque":
        clase = "fisico" if conj["esFisico"] else "magico"
        if conj["elem"] is not None:
            clase += " de " + m.NOMBRES_ELEM[conj["elem"]]
        extra = ""
        if conj["prioridad"]:
            extra += ", se adelanta"
        if conj.get("buff"):
            extra += ", sube su ataque x%.1f por %d turnos" % conj["buff"][1:]
        lo, hi = rangoDano(i, est, conj["poder"], conj["esFisico"], conj["elem"], conj.get("buff"))
        return "%s (%s, %d a %d de daño%s, %s)" % (conj["nombre"], clase, lo, hi, extra, costo)

    if conj["tipo"] == "buff":
        stat = "ataque" if conj["buff"][0] == "atk" else "defensa"
        return "%s (%s x%.1f por %d turnos, %s)" % (conj["nombre"], stat, conj["buff"][1], conj["buff"][2], costo)

    if conj["tipo"] == "cura":
        cantidad = int(yo["atkMag"] * conj["poder"])
        aQuien = "a todos" if conj["enGrupo"] else "a " + est["equipo"][objetivo]["nombre"]
        return "%s %s (+%d de vida, %s)" % (conj["nombre"], aQuien, cantidad, costo)

    return "%s (anula el siguiente ataque que reciba, %s)" % (conj["nombre"], costo)


class Partida:

    def __init__(self, pausa=PAUSA):
        self.registro = []
        self.mostrados = 0
        self.pausa = pausa
        self.rondaMostrada = None

    def al_dia(self):
        # Muestra lo que pasó desde la última vez que se le preguntó al jugador.
        nuevos = self.registro[self.mostrados:]
        self.mostrados = len(self.registro)

        for ev in nuevos:
            if ev["tipo"] == "inicio":
                print()
                for linea in narrar.lineas([ev]):
                    print(linea)
            elif ev["tipo"] == "ronda":
                print("\nRonda %d" % ev["ronda"])
            elif ev["tipo"] == "fase2":
                self._pausa()
                print("  El jefe bajó de la mitad de su vida: cambia a %s y aprende %s."
                      % (ev["objeto"], " y ".join(ev["nuevos"])))
                print("  " + narrar.textoStats(ev["jefe"]))
            elif ev["tipo"] == "turno":
                if ev["actor"] == "Jefe":
                    self._pausa()
                accion, efecto = narrar.textoTurno(ev)
                print(("  %s: %s. %s" % (ev["actor"], accion, efecto)).rstrip())
                for muerto in ev["muertos"]:
                    print("  %s cae." % muerto)

    def _pausa(self):
        if self.pausa:
            time.sleep(self.pausa)

    def turno(self, i, est, opciones):
        # Esta es la política que recibe el motor: en lugar de decidir, pregunta.
        self.al_dia()
        equipo, hp, sp = est["equipo"], est["hp"], est["sp"]
        yo = equipo[i]

        # Como todos eligen con la misma información, la situación se muestra
        # una vez por ronda, antes del primer héroe.
        if est["ronda"] != self.rondaMostrada:
            self.rondaMostrada = est["ronda"]
            self.mostrarSituacion(est)

        # Todos eligen antes de que empiece la ronda; luego se juega por velocidad.
        print("\n  ¿Qué hará %s esta ronda?" % yo["nombre"])

        textos = [textoOpcion(i, a, est) for a in opciones]
        for n, texto in enumerate(textos, start=1):
            print("    %d) %s" % (n, texto))
        return opciones[leerNumero(len(opciones), "  > ") - 1]

    def mostrarSituacion(self, est):
        equipo, hp, sp = est["equipo"], est["hp"], est["sp"]
        print("\n  Jefe: %d/%d de vida, lleva %s" % (est["hp_jefe"], est["jefe"]["hp"], est["objJefe"]["nombre"]))
        if est["cargando"] is not None:
            print("  El jefe está cargando %s y lo suelta en su siguiente turno." % est["cargando"]["nombre"])
        else:
            proximos = [m.HABILIDADES[est["ataques"][k]]["nombre"] for k in est["cola"][:m.tamanoVentana]]
            print("  Su siguiente ataque saldrá de: " + ", ".join(proximos))
        for j, p in enumerate(equipo):
            estado = "" if hp[j] else " (caído)"
            print("  %-10s vida %3d/%-3d  mana %3d/%-3d%s" % (p["nombre"], hp[j], p["hp"], sp[j], p["sp"], estado))


def leerNumero(maximo, prompt):
    while True:
        try:
            txt = input(prompt).strip()
        except EOFError:
            # Sin entrada, por ejemplo al correrlo desde un script, se toma la primera opción.
            return 1
        if txt.isdigit() and 1 <= int(txt) <= maximo:
            return int(txt)
        print("  Escribe un número del 1 al %d." % maximo)


def mostrar_heroes():
    print("\nClases disponibles\n")
    print("     %-10s %5s %5s %7s %7s %8s %8s %5s   %s"
          % ("Clase", "Vida", "Mana", "Ataque", "Defensa", "At. mag.", "Def. mag.", "Vel.", "Objeto"))
    for n, nombre in enumerate(m.nombresClases, start=1):
        p = m.crearHeroe(nombre)
        print("  %d) %-10s %5d %5d %7d %7d %8d %8d %5.1f   %s"
              % (n, nombre, p["hp"], p["sp"], p["atk"], p["defe"], p["atkMag"], p["defMag"], p["vel"],
                 p["objeto"]["nombre"]))


def elegir_equipo():
    mostrar_heroes()
    print("\nArma tu equipo con 4 clases. Escribe sus números separados por espacios, por ejemplo: 1 2 3 4")
    while True:
        try:
            txt = input("  > ").split()
        except EOFError:
            return m.NOMBRES_EQUIPOS[0]

        if len(set(txt)) == 4 and all(t.isdigit() and 1 <= int(t) <= 6 for t in txt):
            elegidos = sorted(int(t) - 1 for t in txt)
            return m.claveEquipo([m.nombresClases[k] for k in elegidos])
        print("  Tienen que ser 4 números distintos del 1 al 6.")


def elegirObjetos(nombres):
    # Cambiar objetos es opcional. El jefe se calificó contra los objetos de
    # siempre, así que con otros el combate puede salir más fácil o más difícil.
    print("\nObjetos disponibles")
    for n, obj in enumerate(m.objetos, start=1):
        print("  %2d) %-22s %s" % (n, obj["nombre"], m.describirObjeto(obj)))
    print("\nPara cada héroe escribe el número del objeto, o deja vacío para no cambiarlo.")

    elegidos = {}
    for nombre in nombres:
        try:
            txt = input("  %s (%s) > " % (nombre, m.tablaClases[nombre]["objeto"])).strip()
        except EOFError:
            break
        if txt.isdigit() and 1 <= int(txt) <= m.nObjetos:
            elegidos[nombre] = m.objetos[int(txt) - 1]["nombre"]
    return elegidos


def jugar(crom, clave_equipo=None, semilla=None, pausa=PAUSA, objetosElegidos=None):
    clave = clave_equipo or elegir_equipo()
    nombres = [p["nombre"] for p in m.EQUIPOS[clave]]
    if clave_equipo is None and objetosElegidos is None:
        objetosElegidos = elegirObjetos(nombres)
    equipo = m.armarEquipo(nombres, objetosElegidos)

    # Sin semilla fija cada partida sale distinta.
    if semilla is None:
        semilla = int(time.time()) % 10000

    p = Partida(pausa)
    res = m.simular(crom, equipo, semilla, registro=p.registro, politica=p.turno)

    p.al_dia()

    if res["gana_equipo"]:
        print("\nGanaste en %d rondas, con %.0f%% de la vida del equipo."
              % (res["rondas"], 100 * res["hp_final_pct"]))
        if res["tope"]:
            print("Se agotaron las %d rondas y eso cuenta como derrota del jefe." % m.RONDAS_MAX)
    else:
        print("\nPerdiste en la ronda %d. Todo el equipo cayó." % res["rondas"])
    return res


def candidatosDeJefe():
    # NSGA-II no entrega un jefe sino un frente. De ahí se ofrecen el que eligió
    # el algoritmo y el mejor en cada objetivo, para que se note la diferencia
    # entre ellos al jugar. Devuelve el tamaño del frente y los pares de
    # (título, jefe), sin repetir jefes.
    frente = narrar.cargarOCrearFrente()
    candidatos = [("El que eligió el algoritmo", next(j for j in frente if j["elegido"])),
                  ("El más parejo", min(frente, key=lambda j: j["objetivos"][0])),
                  ("El de final más cerrado", min(frente, key=lambda j: j["objetivos"][1])),
                  ("El de duración más cercana a 14 rondas", min(frente, key=lambda j: j["objetivos"][2]))]

    opciones = []
    for titulo, jefe in candidatos:
        if all(jefe is not otro for _, otro in opciones):
            opciones.append((titulo, jefe))
    return len(frente), opciones


def elegirJefe():
    tamFrente, opciones = candidatosDeJefe()

    print("\nElige al jefe. Todos vienen del mismo frente de Pareto, de %d jefes:" % tamFrente)
    for n, (titulo, jefe) in enumerate(opciones, start=1):
        print("  %d) %-40s desbalance %.2f, holgura %.2f, desajuste de duración %.2f"
              % ((n, titulo) + tuple(jefe["objetivos"])))
    return opciones[leerNumero(len(opciones), "  > ") - 1][1]["crom"]


if __name__ == "__main__":
    pausa = 0 if "rapido" in sys.argv else PAUSA
    crom = elegirJefe()
    pred = m.evaluar_jefe(crom)

    print("\nContra el jugador automático el equipo le gana %.0f%% de las veces, en promedio de los 15 equipos (F = %.4f)."
          % (100 * pred["p_victoria"], pred["fitness"]))
    jugar(crom, pausa=pausa)
