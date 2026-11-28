# Pruebas a mano de NSGA-II. Cada valor esperado está calculado en el comentario.
# Correr con:  python -m pytest -q
import pytest
import motor as m
import genetico as g
import nsga2 as n2

# Seis puntos de dos objetivos, los dos a minimizar:
#   A(1,5) B(2,2) C(5,1) no se dominan entre sí      -> frente 1
#   D(3,3) solo lo domina B                          -> frente 2
#   E(4,4) lo dominan B y D                          -> frente 3
#   F(6,6) lo dominan todos                          -> frente 4
puntosDePrueba = [(1, 5), (2, 2), (5, 1), (3, 3), (4, 4), (6, 6)]


def testDominancia():
    assert n2.domina((1, 2, 3), (1, 2, 4))           # igual en dos y mejor en uno
    assert not n2.domina((1, 2, 3), (1, 2, 3))       # iguales: nadie domina
    assert not n2.domina((0, 5, 5), (5, 0, 0))       # cada uno gana en algo
    assert not n2.domina((5, 0, 0), (0, 5, 5))


def testDominanciaConRestriccion():
    # El que cumple la restricción gana aunque sea peor en todos los objetivos
    assert n2.domina((9, 9, 9), (0, 0, 0), 0.0, 0.1)
    assert not n2.domina((0, 0, 0), (9, 9, 9), 0.1, 0.0)
    # Entre dos que no la cumplen gana el que la viola menos
    assert n2.domina((9, 9, 9), (0, 0, 0), 0.1, 0.2)
    # Con la misma violación se vuelve a comparar por objetivos
    assert n2.domina((1, 1, 1), (2, 2, 2), 0.1, 0.1)


def testOrdenarPorFrentes():
    assert n2.ordenarPorFrentes(puntosDePrueba) == [[0, 1, 2], [3], [4], [5]]
    # Si B viola la restricción baja de frente y D, que ya nadie domina, sube al primero
    assert n2.ordenarPorFrentes(puntosDePrueba, [0, 0.5, 0, 0, 0, 0])[0] == [0, 2, 3]


def testDistanciaDeCrowding():
    # Frente A, B, C. Los extremos valen infinito. Para B:
    #   objetivo 1: vecinos A(1) y C(5) -> (5 - 1) / (5 - 1) = 1
    #   objetivo 2: vecinos C(1) y A(5) -> (5 - 1) / (5 - 1) = 1      total 2
    d = n2.distanciaCrowding(puntosDePrueba, [0, 1, 2])
    assert d[0] == d[2] == float("inf")
    assert d[1] == pytest.approx(2.0)

    # Cuatro puntos: (0,10) (2,6) (5,5) (10,0)
    #   (2,6): objetivo 1 -> (5 - 0)/10 = 0.5 ; objetivo 2 -> (10 - 5)/10 = 0.5 ; total 1.0
    #   (5,5): objetivo 1 -> (10 - 2)/10 = 0.8 ; objetivo 2 -> (6 - 0)/10 = 0.6 ; total 1.4
    d = n2.distanciaCrowding([(0, 10), (2, 6), (5, 5), (10, 0)], [0, 1, 2, 3])
    assert d[1] == pytest.approx(1.0)
    assert d[2] == pytest.approx(1.4)


def testElegirSobrevivientes():
    # Con 4 lugares entran el frente 1 completo y D
    assert n2.elegirSobrevivientes(puntosDePrueba, 4) == [0, 1, 2, 3]
    # Con 2 lugares el frente 1 no cabe: se quedan sus extremos, A y C
    assert n2.elegirSobrevivientes(puntosDePrueba, 2) == [0, 2]


def testTorneoBinario():
    class RNGPares:
        def __init__(self, *v): self.v = list(v)
        def randrange(self, n): return self.v.pop(0)

    rango, crowding = [0, 0, 1], [1.0, 2.0, 9.0]
    assert n2.torneoBinario(rango, crowding, RNGPares(2, 0)) == 0     # gana el de mejor frente
    assert n2.torneoBinario(rango, crowding, RNGPares(0, 1)) == 1     # mismo frente: el más solo


def testArea2d():
    # Referencia (6,6). Ordenados por x: (1,5) (2,2) (5,1)
    #   (1,5): (6-1) x (6-5) = 5 ; (2,2): (6-2) x (5-2) = 12 ; (5,1): (6-5) x (2-1) = 1
    assert n2.area2d([(1, 5), (2, 2), (5, 1)], (6, 6)) == pytest.approx(18)
    # Un punto dominado no agrega área
    assert n2.area2d([(1, 5), (2, 2), (5, 1), (3, 3)], (6, 6)) == pytest.approx(18)


def testHipervolumen():
    # Un punto en (0.5, 0.5, 0.5): un cubo de lado 0.5 -> 0.125
    assert n2.hipervolumen([(0.5, 0.5, 0.5)]) == pytest.approx(0.125)
    # Con (0.25, 0.75, 0.75) se agrega una caja de 0.75 x 0.25 x 0.25 = 0.046875
    # menos lo que comparte con el cubo, 0.5 x 0.25 x 0.25 = 0.03125 -> 0.140625
    assert n2.hipervolumen([(0.5, 0.5, 0.5), (0.25, 0.75, 0.75)]) == pytest.approx(0.140625)
    # Un punto fuera de la referencia no cuenta
    assert n2.hipervolumen([(0.5, 0.5, 1.2)]) == 0.0


def testElegirDelFrente():
    # nota = (1 - desbalance) x (0.5 x (1 - holgura) + 0.25 x (1 - desajuste) + 0.25)
    #   (0.2, 0.4, 0.6): 0.8 x (0.30 + 0.10 + 0.25) = 0.52
    #   (0.4, 0.2, 0.2): 0.6 x (0.40 + 0.20 + 0.25) = 0.51
    assert n2.notaAproximada((0.2, 0.4, 0.6)) == pytest.approx(0.52)
    assert n2.notaAproximada((0.4, 0.2, 0.2)) == pytest.approx(0.51)
    frente = [("a", (0.2, 0.4, 0.6), 0.0), ("b", (0.4, 0.2, 0.2), 0.0), ("c", (0.0, 0.0, 0.0), 0.3)]
    # "c" tiene la mejor nota pero viola la restricción, así que gana "a"
    assert n2.elegirDelFrente(frente)[0] == "a"


def testObjetivosSalenDeLaEvaluacion():
    crom = g.decodificar([0, 1] * 67)
    r = m.evaluar_jefe(crom, n=4, semilla=0)
    objs, viol = m.objetivos(crom, n=4, semilla=0)
    assert objs == pytest.approx((r["desbalance"], 1 - r["margen"], 1 - r["duracion"]))
    assert viol == pytest.approx(max(0.0, (1 - r["f_win"]) / 2 - m.toleranciaBanda))
    assert all(0 <= v <= 1 for v in objs)


def testPresupuestoDeEvaluaciones():
    # Población 6 y 2 generaciones. Con semillas rotativas cada generación evalúa
    # a los 6 padres otra vez y a los 6 hijos: 6 + 2x12 = 30. Sin rotar: 6 + 2x6 = 18.
    _, hist = n2.correrNsga2(semillaRng=3, tamPoblacion=6, generaciones=2, nSim=2)
    assert [e for e, _ in hist] == [6, 18, 30]
    _, hist = n2.correrNsga2(semillaRng=3, tamPoblacion=6, generaciones=2, nSim=2, rotarSemillas=False)
    assert [e for e, _ in hist] == [6, 12, 18]


def testFrenteFinal():
    frente, _ = n2.correrNsga2(semillaRng=5, tamPoblacion=8, generaciones=3, nSim=2)
    otro, _ = n2.correrNsga2(semillaRng=5, tamPoblacion=8, generaciones=3, nSim=2)
    assert frente == otro                                    # misma semilla, mismo frente
    assert 1 <= len(frente) <= 8
    # Nadie en el frente domina a otro del frente
    for _, a, va in frente:
        for _, b, vb in frente:
            assert not n2.domina(a, b, va, vb)


def testTDeWelch():
    # medias 2 y 3, varianzas muestrales 1 y 1, tres datos cada una
    # t = (2 - 3) / raiz(1/3 + 1/3) = -1.2247
    import comparar
    assert comparar.tDeWelch([1, 2, 3], [2, 3, 4]) == pytest.approx(-1.2247, abs=1e-4)
