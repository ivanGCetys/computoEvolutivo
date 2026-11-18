# Pruebas a mano del motor. Cada valor esperado está calculado en el comentario.
# Correr con:  python -m pytest -q
import math
import random
import pytest
import motor as m


class RNGFijo:
    # Devuelve siempre el mismo número, o va recorriendo una lista si se le da.
    def __init__(self, *valores):
        self.valores, self.k = valores, 0

    def random(self):
        v = self.valores[self.k % len(self.valores)]
        self.k += 1
        return v


jefeParejo = {"puntos": [250] * 6, "objeto1": 0, "objeto2": 0,
               "habs": [0, 1, 2, 3, 4, 5, 6, 7], "pesos": [0] * 8,
               "cambios": [[0, 8], [7, 30]], "ajustes": [1] * 5,
               "predisposicion": [0] * 6, "probBloqueo": 0}


def jefeDe(**genes):
    # El jefe parejo con los genes que se le indiquen cambiados.
    return dict(jefeParejo, **genes)


def estadoDePrueba(crom=jefeParejo, equipo=m.EQUIPO_BASE):
    return m.crearEstado(m.reparar(crom), equipo, random.Random(0))


# 1. Objetos: el elemento solo activa los bonos del objeto
def testBonosDeObjetos():
    amuleto, talisman = m.objetos[0], m.objetos[1]
    fuego, agua, viento = m.indiceElem["fuego"], m.indiceElem["agua"], m.indiceElem["viento"]
    assert amuleto["nombre"] == "Amuleto de fuego"
    assert amuleto["multAtk"][fuego] == pytest.approx(1.20)
    assert amuleto["multDef"][fuego] == pytest.approx(1.10)
    assert amuleto["multDef"][agua] == pytest.approx(0.75)      # débil al opuesto
    assert amuleto["multAtk"][viento] == 1.0                    # sin bono fuera de su elemento
    assert talisman["multAtk"][fuego] == pytest.approx(1.10)
    assert talisman["multDef"][agua] == pytest.approx(1.25)
    assert talisman["multDef"][viento] == pytest.approx(0.85)
    assert m.nObjetos == 16


# 2. Fórmula de daño
def test_dano_basico_del_equipo():
    # 60 x 0.8 x 100/350 = 13.71 -> 13
    assert m.calcular_dano(60, 0.8, 1.0, 250) == 13


def test_dano_minimo_1():
    # 10 x 0.8 x 0.5 x 100/600 = 0.67 -> 0 -> se sube a 1
    assert m.calcular_dano(10, 0.8, 0.5, 500) == 1


def testBloqueoParteElDanoALaMitad():
    # 300 x 0.8 x 100/160 = 150; bloqueando x0.5 = 75
    assert m.calcular_dano(300, 0.8, 1.0, 60, m.multBloqueo) == 75


def testProbabilidadDeEsquive():
    assert m.probEsquive(30, 20) == pytest.approx(0.01)     # el atacante es más rápido: mínimo
    assert m.probEsquive(20, 20) == pytest.approx(0.01)
    assert m.probEsquive(20, 30) == pytest.approx(0.05)     # 10 de diferencia x 0.005
    assert m.probEsquive(10, 50) == pytest.approx(0.15)     # 40 x 0.005 = 0.20 -> tope 0.15


def testVariacionFisicaYMagica():
    # Físico sin crítico: 0.80 + 0.40 x 0.5 = 1.00
    assert m.multVariacion(RNGFijo(0.5), True) == (pytest.approx(1.0), False)
    # Guerrero y pícaro tienen piso 0.90: 0.90 + 0.30 x 0.5 = 1.05
    assert m.multVariacion(RNGFijo(0.5), True, 0.90, 0.20) == (pytest.approx(1.05), False)
    # 0.05 < 0.10 de probabilidad de crítico -> multiplicador 1.60
    assert m.multVariacion(RNGFijo(0.05), True) == (1.60, True)
    # Mágico: 0.85 + 0.15 x 0.5 = 0.925, y nunca es crítico
    assert m.multVariacion(RNGFijo(0.0), False) == (pytest.approx(0.85), False)
    assert m.multVariacion(RNGFijo(0.5), False) == (pytest.approx(0.925), False)


def testDanoDeUnAtaqueAMano():
    amuletoFuego, amuletoAgua = m.objetos[0], m.objetos[2]
    fuego = m.indiceElem["fuego"]
    # Físico sin elemento: no esquiva (0.5 > 0.01), no crítico, variación 1.00
    # 100 x 1.0 x 1.00 x 100/200 = 50
    assert m.danoAtaque(RNGFijo(0.5), 100, 1.0, True, None, amuletoFuego, 100, amuletoAgua, 20, 20) == (50, "")
    # Mágico de fuego: variación 0.925 x 1.20 del amuleto = 1.11
    # la defensa 100 baja a 75 porque el amuleto de agua es débil al fuego
    # 100 x 1.0 x 1.11 x 100/175 = 63.43 -> 63
    assert m.danoAtaque(RNGFijo(0.5), 100, 1.0, False, fuego, amuletoFuego, 100, amuletoAgua, 20, 20) == (63, "")
    # Con 0.005 en el primer número el golpe se esquiva (0.005 < 0.01)
    assert m.danoAtaque(RNGFijo(0.005), 100, 1.0, True, None, amuletoFuego, 100, amuletoAgua, 20, 20) == (0, "esquiva")
    # Crítico: 100 x 1.60 x 100/200 = 80
    assert m.danoAtaque(RNGFijo(0.5, 0.05), 100, 1.0, True, None, amuletoFuego, 100, amuletoAgua, 20, 20) == (80, "critico")


# 3. Reparación del cromosoma
def test_reparar_puntos_todo_a_hp():
    # [1,0,0,0,0,0] -> vida = 100 + 900 = 1000 > 500 -> se recorta a 500
    # el exceso de 500 se reparte en 5: 100 c/u -> 200 cada uno, suma 1500
    c = m.reparar(jefeDe(puntos=[1, 0, 0, 0, 0, 0]))
    assert c["puntos"] == [500, 200, 200, 200, 200, 200]
    assert sum(c["puntos"]) == 1500


def test_reparar_es_idempotente():
    c = jefeDe(puntos=[206, 265, 253, 276, 300, 200], objeto1=1, objeto2=2,
               habs=[3, 6, 0, 1, 9, 9, 31, 12], pesos=[3, 2, 1, 0, 3, 2, 1, 0])
    r1 = m.reparar(c)
    assert r1["puntos"] == [206, 265, 253, 276, 300, 200]
    assert m.reparar(r1) == r1


def testRepararColaYCambios():
    # habs todos en 5: los repetidos se cambian por el menor índice libre
    #   -> [5, 0, 1, 2, 3, 4, 6, 7]
    # cambios: (9, 5) -> posición 9 % 8 = 1; el ataque 5 ya está en la cola, igual
    #   que 6 y 7, así que se recorre hasta el 8. (3, 5) -> llega hasta el 9
    #   porque el 8 ya lo tomó el cambio anterior.
    # el resto de los genes se dobla a su rango con el módulo
    c = m.reparar(jefeDe(puntos=[1] * 6, objeto1=17, objeto2=-1, habs=[5] * 8, pesos=[5] * 8,
                         cambios=[[9, 5], [3, 5]], ajustes=[7] * 5,
                         predisposicion=[9] * 6, probBloqueo=6))
    assert c["habs"] == [5, 0, 1, 2, 3, 4, 6, 7]
    assert c["cambios"] == [[1, 8], [3, 9]]
    assert c["pesos"] == [1] * 8                     # 5 % 4
    assert c["ajustes"] == [3] * 5                   # 7 % 4
    assert c["predisposicion"] == [1] * 6            # 9 % 8
    assert c["probBloqueo"] == 2                     # 6 % 4
    assert c["puntos"] == [250] * 6
    assert (c["objeto1"], c["objeto2"]) == (1, 15)   # 17 % 16 = 1 ; -1 % 16 = 15


def testStatsDelJefe():
    # 250 puntos en todo: vida int(250 x 3.5) = 875, ataques int(250 x 1.8 / 2) = 225,
    # defensas int(250 / 3) = 83, velocidad 250/10
    assert m.stats_jefe(jefeParejo) == {"hp": 875, "atk": 225, "defe": 83,
                                         "atkMag": 225, "defMag": 83, "vel": 25.0}


def testBancoDeAtaques():
    assert m.N_HABILIDADES == 32
    assert sum(1 for a in m.HABILIDADES if a["carga"]) == 4
    # Los de área pegan menos a cada héroe que cualquier ataque a uno solo,
    # pero contra cuatro héroes suman más que el más fuerte de esos
    unicos = [a["poder"] for a in m.HABILIDADES if not a["enArea"] and not a["carga"]]
    areas = [a["poder"] for a in m.HABILIDADES if a["enArea"] and not a["carga"]]
    assert max(areas) < min(unicos)
    assert 4 * min(areas) > max(unicos)


# 4. Clases y equipos
def testClasesRepartenElMismoTope():
    for nombre in m.nombresClases:
        assert sum(m.tablaClases[nombre]["puntos"]) == m.topePuntosHeroe
    # Guerrero, 100 puntos en todo: vida 300, ataques 50, defensas 33, velocidad 25
    g = m.crearHeroe("Guerrero")
    assert (g["hp"], g["atk"], g["defe"], g["atkMag"], g["defMag"], g["vel"]) == (300, 50, 33, 50, 33, 25.0)
    # Solo mago y clérigo recuperan maná
    assert [n for n in m.nombresClases if m.tablaClases[n]["regenSp"] > 0] == ["Mago", "Clerigo"]


def testQuinceEquipos():
    # 6 clases tomadas de 4 en 4 = 15 combinaciones, todas de 4 héroes distintos
    assert len(m.EQUIPOS) == 15
    for clave, eq in m.EQUIPOS.items():
        assert len({p["nombre"] for p in eq}) == 4
        assert clave == "".join(p["nombre"][0] for p in eq)


def testSorteoDeConjuros():
    for semilla in range(20):
        eq = m.sortearConjuros(m.EQUIPO_BASE, random.Random(semilla))
        mago = next(p for p in eq if p["nombre"] == "Mago")
        guerrero = next(p for p in eq if p["nombre"] == "Guerrero")
        # 4 conjuros de 4 elementos distintos, y exactamente uno es de los poderosos
        assert len(mago["conjuros"]) == 4
        assert len({c["elem"] for c in mago["conjuros"]}) == 4
        assert sum(1 for c in mago["conjuros"] if c in m.conjurosMagoPoderosos) == 1
        # Los dos tajos del guerrero salen con elementos distintos
        tajos = [c["elem"] for c in guerrero["conjuros"] if c["tipo"] == "ataque"]
        assert len(set(tajos)) == 2 and all(isinstance(e, int) for e in tajos)
    # El sorteo no toca el equipo original
    assert m.EQUIPO_BASE[0]["conjuros"][1]["elem"] == "azar"


# 5. Acciones de los héroes, una por una (equipo base: Guerrero, Tanque, Mago, Clérigo)
def testAtaqueBasicoAMano():
    # Guerrero (ataque 50, velocidad 25) contra el jefe parejo (defensa 83, velocidad 25)
    # no esquiva, no crítico (0.5 > 0.20), variación 0.90 + 0.30 x 0.5 = 1.05
    # 50 x 0.8 x 1.05 x 100/183 = 22.95 -> 22
    est = estadoDePrueba()
    hecho = m.ejecutarAccion(0, ("basico", None, None), est, RNGFijo(0.5))
    assert hecho["golpes"] == [("Jefe", 22, "")]
    assert est["hp_jefe"] == 875 - 22


def testCurasDelClerigo():
    # Ataque mágico del clérigo: 120 // 2 = 60. Menor: 60 x 0.8 = 48. Grupo: 60 x 0.6 = 36
    est = estadoDePrueba()
    est["hp"] = [100, 470, 0, 300]
    m.ejecutarAccion(3, ("conjuro", 0, 0), est, RNGFijo(0.5))
    assert est["hp"][0] == 148 and est["sp"][3] == 110 - 10
    m.ejecutarAccion(3, ("conjuro", 2, None), est, RNGFijo(0.5))
    # el tanque se topa en su máximo de 480 y el mago caído no revive
    assert est["hp"] == [184, 480, 0, 300] and est["sp"][3] == 60


def testPociones():
    est = estadoDePrueba()
    est["hp"][2], est["sp"][2] = 10, 0
    m.ejecutarAccion(2, ("pocion", "hpGrande", None), est, RNGFijo(0.5))    # 60% de 210 = 126
    m.ejecutarAccion(2, ("pocion", "spChica", None), est, RNGFijo(0.5))     # 30% de 100 = 30
    assert est["hp"][2] == 136 and est["sp"][2] == 30
    assert est["pociones"] == {"hpChica": 2, "hpGrande": 0, "spChica": 1, "spGrande": 1}


def testBuffDuraDosTurnos():
    est = estadoDePrueba()
    m.ejecutarAccion(0, ("conjuro", 0, None), est, RNGFijo(0.5))     # Guardia de acero
    assert est["buffDef"][0] == 2 and est["sp"][0] == 44 - 8
    m.ejecutarAccion(0, ("basico", None, None), est, RNGFijo(0.5))
    assert est["buffDef"][0] == 1
    m.ejecutarAccion(0, ("basico", None, None), est, RNGFijo(0.5))
    assert est["buffDef"][0] == 0


def testDefensasDelTanque():
    # Jefe parejo (ataque 225) pega físico con poder 1.0 al tanque (defensa 50), variación 1.00
    # normal: 225 x 100/150 = 150 | bloqueando: 75 | con Muralla (50 x 1.6 = 80): 225 x 100/180 = 125
    est = estadoDePrueba()
    assert m.atacarHeroe(1, 1.0, True, None, est, RNGFijo(0.5)) == (150, "")
    est["bloq"][1] = True
    assert m.atacarHeroe(1, 1.0, True, None, est, RNGFijo(0.5)) == (75, "")
    est["bloq"][1] = False
    m.ejecutarAccion(1, ("conjuro", 0, None), est, RNGFijo(0.5))
    assert m.atacarHeroe(1, 1.0, True, None, est, RNGFijo(0.5)) == (125, "")
    assert est["hp"][1] == 480 - 150 - 75 - 125

    # Bloqueo total: anula un ataque y se gasta
    m.ejecutarAccion(1, ("conjuro", 1, None), est, RNGFijo(0.5))
    assert m.atacarHeroe(1, 1.0, True, None, est, RNGFijo(0.5)) == (0, "bloqueado")
    assert m.atacarHeroe(1, 1.0, True, None, est, RNGFijo(0.5))[0] == 125


def testFuriaDesatadaPegaConElBuff():
    # Berserker: ataque 95 x 1.5 = 142.5; poder 1.0; variación 1.00; defensa del jefe 83
    # 142.5 x 100/183 = 77.87 -> 77
    est = estadoDePrueba(equipo=m.EQUIPOS["GTMB"])
    hecho = m.ejecutarAccion(3, ("conjuro", 1, None), est, RNGFijo(0.5))
    assert hecho["golpes"] == [("Jefe", 77, "")]
    assert est["buffAtk"][3] == 2 and est["sp"][3] == 40 - 18


def testAccionesLegales():
    est = estadoDePrueba()
    # Con todo lleno no se ofrecen pociones; el guerrero tiene básico, 3 conjuros y bloquear
    assert m.accionesLegales(0, est) == [("basico", None, None), ("conjuro", 0, None), ("conjuro", 1, None),
                                         ("conjuro", 2, None), ("bloquear", None, None)]
    # Sin maná desaparecen los conjuros
    est["sp"][0] = 5
    assert ("conjuro", 0, None) not in m.accionesLegales(0, est)
    # Herido aparecen las pociones de vida, y con poco maná las de maná
    est["hp"][0] = 50
    assert ("pocion", "hpChica", None) in m.accionesLegales(0, est)
    assert ("pocion", "spGrande", None) in m.accionesLegales(0, est)
    # La cura individual del clérigo da una opción por cada aliado vivo
    est["hp"][2] = 0
    assert [a for a in m.accionesLegales(3, est) if a[1] == 0] == [("conjuro", 0, 0), ("conjuro", 0, 1), ("conjuro", 0, 3)]


def testElPicaroSeAdelanta():
    # Jefe con la velocidad al máximo: 500 / 10 = 50 > 42.5 del pícaro. En el orden
    # normal iría primero el jefe, pero el pícaro abre la ronda con un ataque que se adelanta.
    crom = m.reparar(jefeDe(puntos=[200, 200, 200, 200, 200, 500]))
    reg = []
    m.simular(crom, m.EQUIPOS["GTMP"], 0, registro=reg)
    assert reg[0]["orden"][0] == "Jefe"
    primerTurno = next(e for e in reg if e["tipo"] == "turno")
    assert primerTurno["actor"] == "Picaro" and primerTurno["adelantado"]
    assert primerTurno["accion"] in ("Punalada veloz", "Golpe sombra")


# 6. El turno del jefe
def testColaDeAtaques():
    # Con todos los pesos iguales la ventana [0,1,2,3] reparte 1/4 a cada uno.
    # r = 0.6 x 4 = 2.4 -> pasa el 0 (1.4), pasa el 1 (0.4), cae en el 2
    est = estadoDePrueba()
    assert m.elegirDeLaCola(est, RNGFijo(0.6)) == 2
    assert est["cola"] == [0, 1, 3, 4, 5, 6, 7, 2]       # el usado se va al final
    assert m.elegirDeLaCola(est, RNGFijo(0.0)) == 0
    assert est["cola"] == [1, 3, 4, 5, 6, 7, 2, 0]
    assert est["usos"] == [1, 0, 1, 0, 0, 0, 0, 0]
    # El 2 no puede volver a salir hasta que la cola avance: no está en la ventana
    assert 2 not in est["cola"][:m.tamanoVentana]


def testAtaqueDeCarga():
    # Aplastamiento (ataque 28 del banco) va primero en la cola. Con 0.0 no bloquea
    # (0.0 < 0.0 es falso) y elige el primero de la ventana: gasta el turno en cargar.
    est = estadoDePrueba(jefeDe(habs=[28, 0, 1, 2, 3, 4, 5, 6]))
    reg = []
    m.turnoJefe(est, RNGFijo(0.0), reg)
    assert reg[-1]["accion"] == "Carga Aplastamiento" and reg[-1]["golpes"] == []
    assert est["cargando"]["nombre"] == "Aplastamiento"

    # Siguiente turno: 0.0 elige al Guerrero; 0.5 no esquiva, no es crítico y da variación 1.00
    # 225 x 2.6 x 1.00 x 100/133 = 439.8 -> 439, más que los 300 de vida del Guerrero
    m.turnoJefe(est, RNGFijo(0.0, 0.5, 0.5, 0.5), reg)
    assert reg[-1]["accion"] == "Aplastamiento"
    assert reg[-1]["golpes"] == [("Guerrero", 439, "")]
    assert reg[-1]["muertos"] == ["Guerrero"] and est["hp"][0] == 0
    assert est["cargando"] is None and est["primera_muerte"] == 0


def testElJefeBloquea():
    # probBloqueo 3 -> 15%. Con 0.10 bloquea y no ataca; con 0.50 ataca normal.
    est = estadoDePrueba(jefeDe(probBloqueo=3))
    reg = []
    m.turnoJefe(est, RNGFijo(0.10), reg)
    assert est["guardia"] and reg[-1]["accion"] == "Bloquea" and reg[-1]["golpes"] == []
    m.turnoJefe(est, RNGFijo(0.50), reg)
    assert not est["guardia"] and len(reg[-1]["golpes"]) == 1


def testPredisposicion():
    # Predisposición 7 al Tanque y 0 al resto: pesos 8 contra 1, 1 y 1 (total 11)
    est = estadoDePrueba(jefeDe(predisposicion=[0, 7, 0, 0, 0, 0]))
    assert m.objetivo_jefe(est, RNGFijo(0.05)) == 0      # 0.55 cae en el Guerrero
    assert m.objetivo_jefe(est, RNGFijo(0.50)) == 1      # 5.5 pasa al Guerrero y cae en el Tanque
    assert m.objetivo_jefe(est, RNGFijo(0.95)) == 3      # 10.45 llega hasta el Clérigo
    # Con el Tanque caído quedan tres pesos de 1: 0.5 x 3 = 1.5 cae en el segundo vivo
    est["hp"][1] = 0
    assert m.objetivo_jefe(est, RNGFijo(0.50)) == 2


def testFase2CambiaObjetoStatsYCola():
    # ajustes [3,0,1,2,3] -> ataque x1.15, defensa x0.85, ataque mágico x0.95,
    # defensa mágica x1.05, velocidad x1.15. La vida máxima no cambia.
    #   225 x 1.15 = 258.75 -> 258 | 83 x 0.85 = 70.55 -> 70 | 225 x 0.95 = 213.75 -> 213
    #   83 x 1.05 = 87.15 -> 87    | 25 x 1.15 = 28.75
    # cambios: la posición 0 pasa al ataque 8 y la 7 al ataque 30
    crom = jefeDe(objeto2=5, ajustes=[3, 0, 1, 2, 3])
    assert m.statsFase2(crom) == {"hp": 875, "atk": 258, "defe": 70, "atkMag": 213,
                                  "defMag": 87, "vel": pytest.approx(28.75)}
    assert m.colaFase2(crom) == [8, 1, 2, 3, 4, 5, 6, 30]

    est = estadoDePrueba(crom)
    est["hp_jefe"] = 437          # la mitad de 875 es 437.5
    reg = []
    m.turnoJefe(est, RNGFijo(0.5), reg)
    assert est["ronda_fase2"] == 0 and est["objJefe"] is m.objetos[5]
    assert est["jefe"]["atk"] == 258 and est["ataques"] == [8, 1, 2, 3, 4, 5, 6, 30]
    assert reg[0]["tipo"] == "fase2" and reg[0]["nuevos"] == ["Onda de choque", "Rayo final"]


def testElAutomaticoRespondeALaCarga():
    est = estadoDePrueba()
    est["cargando"] = m.HABILIDADES[28]
    # El Tanque prepara su bloqueo total; el Guerrero sano sigue atacando y herido bloquea
    assert m.decidir_accion(1, est) == ("conjuro", 1, None)
    assert m.decidir_accion(0, est)[0] != "bloquear"
    est["hp"][0] = 120            # 40% de 300, y arriba de 30% para que no pida poción
    assert m.decidir_accion(0, est) == ("bloquear", None, None)


# 7. Combates completos
def test_reproducible():
    crom = m.reparar(jefeDe(puntos=[3, 2, 2, 1, 2, 2]))
    assert m.simular(crom, semilla=7) == m.simular(crom, semilla=7)
    assert m.evaluar(crom, n=10, semilla=5) == m.evaluar(crom, n=10, semilla=5)


def test_fase2_ocurre():
    # Para ganar, el equipo tiene que bajar al jefe de la mitad de su vida, y el
    # cambio de fase se registra una sola vez.
    crom = m.reparar(jefeDe(puntos=[100, 100, 500, 100, 500, 200], objeto2=5))
    reg = []
    r = m.simular(crom, semilla=0, registro=reg)
    assert r["gana_equipo"] and not r["tope"]
    assert r["ronda_fase2"] is not None
    cambios = [e for e in reg if e["tipo"] == "fase2"]
    assert len(cambios) == 1 and cambios[0]["objeto"] == m.objetos[5]["nombre"]


def test_registro_no_cambia_el_combate():
    # Activar el registro no debe alterar ningún número.
    crom = m.reparar(jefeDe(puntos=[3, 2, 2, 1, 2, 2], probBloqueo=2))
    for semilla in range(4):
        for eq in m.EQUIPOS.values():
            assert m.simular(crom, eq, semilla) == m.simular(crom, eq, semilla, registro=[])


def test_politica_equivalente_da_el_mismo_combate():
    # El modo interactivo cambia quién decide, no las reglas. Si la política hace
    # lo mismo que el jugador automático, el combate debe salir idéntico.
    def comoElAutomatico(i, est, opciones, enVentana):
        accion = m.decidirPrioridad(i, est) if enVentana else m.decidir_accion(i, est)
        assert accion is None or accion in opciones
        return accion

    crom = m.reparar(jefeDe(puntos=[3, 2, 2, 1, 2, 2], habs=[28, 29, 30, 31, 0, 12, 20, 8]))
    for semilla in range(4):
        for eq in m.EQUIPOS.values():
            assert m.simular(crom, eq, semilla) == m.simular(crom, eq, semilla, politica=comoElAutomatico)


def test_registro_cuadra_con_el_resultado():
    crom = m.reparar(jefeDe(puntos=[3, 2, 2, 1, 2, 2]))
    reg = []
    r = m.simular(crom, m.EQUIPO_BASE, 0, registro=reg)
    assert reg[0]["tipo"] == "inicio" and reg[0]["hp_equipo"] == [300, 480, 210, 300]
    turnos = [e for e in reg if e["tipo"] == "turno"]
    assert turnos[-1]["hp_equipo"] == r["hp_equipo"]
    assert max(e["ronda"] for e in reg if e["tipo"] == "ronda") == r["rondas"]
    assert sum(r["usos"]) <= r["rondas"]


# 8. Fitness con resultados inventados
def _res(gana, hp_pct, rondas):
    return {"gana_equipo": gana, "hp_final_pct": hp_pct, "rondas": rondas, "usos": [1, 1, 1, 1], "tope": False}


def test_fitness_perfecto():
    # 6 de 10 victorias con 20% de vida, 10 rondas, uso uniforme
    # f_win = 1, margen = 1, duración = 1, variedad = 2/2 = 1  -> fitness = 1.0
    res = [_res(True, 0.20, 10)] * 6 + [_res(False, 0.0, 10)] * 4
    f = m.calcular_fitness(res)
    assert f["fitness"] == pytest.approx(1.0)


def test_fitness_fuera_de_banda_y_margen():
    # Banda media = 40-60%. 9 de 10 victorias -> p = 0.9
    # distancia a la banda: d = 0.9 - 0.60 = 0.30 -> f_win = 1 - 2(0.30) = 0.40
    # vida final 60%: margen = 1 - |0.6-0.2|/0.8 = 0.5
    # 13 rondas: duración = exp(-(13-10)^2 / (2x3^2)) = exp(-0.5) = 0.6065
    # variedad: usos [1,1,1,1] -> H = 2 bits -> 2/2 = 1
    # fitness = 0.40 x (0.5x0.5 + 0.25x0.6065 + 0.25x1) = 0.40 x 0.6516 = 0.2607
    res = [_res(True, 0.60, 13)] * 9 + [_res(False, 0.0, 13)]
    f = m.calcular_fitness(res)
    assert f["f_win"] == pytest.approx(0.4)
    assert f["margen"] == pytest.approx(0.5)
    assert f["duracion"] == pytest.approx(math.exp(-0.5))
    assert f["fitness"] == pytest.approx(0.2606533, abs=1e-6)


def test_fitness_extremos_quedan_abajo():
    # Jefe invencible (0 victorias): d = 0.40 -> f_win = 0.20
    #   margen = 0 (no hay victorias); duración = 1; variedad = 1
    #   fitness = 0.20 x (0.5x0 + 0.25x1 + 0.25x1) = 0.10
    invencible = [_res(False, 0.0, 10)] * 10
    f_inv = m.calcular_fitness(invencible)
    assert f_inv["f_win"] == pytest.approx(0.2)
    assert f_inv["fitness"] == pytest.approx(0.10)

    # Jefe trivial (10 de 10 victorias): d = 1.0 - 0.60 = 0.40 -> mismo f_win
    trivial = [_res(True, 0.95, 2)] * 10
    assert m.calcular_fitness(trivial)["f_win"] == pytest.approx(0.2)

    en_banda = [_res(True, 0.20, 10)] * 5 + [_res(False, 0.0, 10)] * 5
    assert m.calcular_fitness(en_banda)["fitness"] > 5 * f_inv["fitness"]


def testElJefeSeCalificaConElPromedioDeLosEquipos():
    crom = jefeDe(puntos=[300, 300, 200, 200, 250, 250], objeto1=3, objeto2=8)
    r = m.evaluar_jefe(crom, n=6, semilla=0)
    uno = {k: m.evaluar(m.reparar(crom), eq, n=6, semilla=0)["fitness"] for k, eq in m.EQUIPOS.items()}
    assert r["fitness"] == pytest.approx(sum(uno.values()) / 15)
    assert r["fitness_equipos"] == pytest.approx(uno)
    assert r["peor_equipo"] == min(uno, key=uno.get)
    assert m.costo(crom, n=6, semilla=0) == pytest.approx(1 - r["fitness"])
