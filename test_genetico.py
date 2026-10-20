"""
Pruebas a mano del AG. Cada valor esperado está calculado en el comentario.
Correr con:  python -m pytest -q
"""
import random
import pytest
import motor as m
import genetico as g


# 1. Codificación: 44 bits y cómo se parten
def test_tamano_del_cromosoma():
    # 4 atributos x 4 bits + 2 elementos x 2 + 4 habilidades x 3 + 4 pesos x 3
    assert 4 * 4 + 2 * 2 + 4 * 3 + 4 * 3 == 44
    assert g.N_BITS == 44


def test_entero_desde_bits():
    assert g._entero([1, 0, 0, 0]) == 8      # 8+0+0+0
    assert g._entero([0, 1, 0, 1]) == 5      # 0+4+0+1
    assert g._entero([1, 1, 1]) == 7


# 2. Decodificación completa, calculada a mano
def test_decodificar_a_mano():
    # atributos: 1000 0100 0010 0001 -> 8, 4, 2, 1   (suma 15)
    # elementos: 00 10               -> fuego, viento
    # habilidades: 000 001 010 011   -> 0, 1, 2, 3   (ya son distintas)
    # pesos: 100 010 001 001         -> 4, 2, 1, 1   (suma 8)
    bits = ([1,0,0,0] + [0,1,0,0] + [0,0,1,0] + [0,0,0,1]
            + [0,0] + [1,0]
            + [0,0,0] + [0,0,1] + [0,1,0] + [0,1,1]
            + [1,0,0] + [0,1,0] + [0,0,1] + [0,0,1])
    assert len(bits) == 44
    c = g.decodificar(bits)
    # puntos = 100 fijos + 600 por proporción:
    #   100 + 600x8/15 = 420 | 100 + 600x4/15 = 260
    #   100 + 600x2/15 = 180 | 100 + 600x1/15 = 140   (suman 1000)
    assert c["puntos"] == [420, 260, 180, 140]
    assert sum(c["puntos"]) == 1000
    assert (c["elem1"], c["elem2"]) == (m.FUEGO, m.VIENTO)
    assert c["habs"] == [0, 1, 2, 3]
    # pesos normalizados: [4,2,1,1]/8 = [0.5, 0.25, 0.125, 0.125]
    assert c["pesos"] == pytest.approx([0.5, 0.25, 0.125, 0.125])


def test_habilidad_7_se_dobla_a_0():
    # 111 vale 7, pero solo hay 7 habilidades (0..6): 7 % 7 = 0
    bits = [0] * 44
    for i, b in enumerate([1, 1, 1]):
        bits[20 + i] = b                      # primera habilidad = 111
    assert g.decodificar(bits)["habs"][0] == 0


# 3. Selección por rango: el ejemplo de la diapositiva 24 (Nkeep = 4)
def test_probabilidades_de_rango():
    # P_n = (4 - n + 1) / (1+2+3+4) = 4/10, 3/10, 2/10, 1/10
    assert g.probabilidades_rango(4) == pytest.approx([0.4, 0.3, 0.2, 0.1])
    assert sum(g.probabilidades_rango(15)) == pytest.approx(1.0)


def test_ruleta_por_rango():
    acum = g.acumuladas(g.probabilidades_rango(4))     # [0.4, 0.7, 0.9, 1.0]
    assert acum == pytest.approx([0.4, 0.7, 0.9, 1.0])

    class RNGFijo:                                      # devuelve el número que yo quiera
        def __init__(self, v): self.v = v
        def random(self): return self.v
    # r = 0.577 cae entre 0.4 y 0.7 -> rango 2 (índice 1), igual que la diapositiva
    assert g.elegir_por_rango(acum, RNGFijo(0.577)) == 1
    assert g.elegir_por_rango(acum, RNGFijo(0.0)) == 0      # el mejor
    assert g.elegir_por_rango(acum, RNGFijo(0.95)) == 3     # el peor


# 4. Cruce de un punto
def test_cruce_un_punto():
    p1, p2 = [0] * 44, [1] * 44

    class RNGCorte:
        def randrange(self, a, b=None): return 10          # corta en el bit 10
    h1, h2 = g.cruce_un_punto(p1, p2, RNGCorte())
    assert h1 == [0] * 10 + [1] * 34                       # 10 del padre 1, 34 del padre 2
    assert h2 == [1] * 10 + [0] * 34
    # Ningún bit se pierde: cada posición sigue teniendo un 0 y un 1 entre los dos hijos
    assert all(a + b == 1 for a, b in zip(h1, h2))


# 5. Mutación
def test_mutacion_extremos():
    rng = random.Random(0)
    iguales, _ = g.mutar([0] * 44, 0.0, rng)
    assert iguales == [0] * 44                              # tasa 0: no cambia nada
    todos, cambios = g.mutar([0] * 44, 1.0, rng)
    assert todos == [1] * 44 and cambios == 44              # tasa 1: se voltean todos


def test_mutacion_tasa_esperada():
    # Con tasa 1/44 se espera 1 bit mutado por cromosoma. En 2000 cromosomas,
    # el promedio debe acercarse a 1 (tolerancia amplia, es aleatorio).
    rng = random.Random(7)
    total = sum(g.mutar([0] * 44, 1 / 44, rng)[1] for _ in range(2000))
    assert 0.85 < total / 2000 < 1.15


# 6. Elitismo: el mejor costo nunca empeora
def test_elitismo_la_curva_nunca_sube():
    _, _, hist = g.correr_ag(semilla_rng=3, popsize=10, maxit=4, n_sim=5)
    costos = [c for _, c in hist]
    assert all(b <= a + 1e-12 for a, b in zip(costos, costos[1:]))


def test_mismo_presupuesto_de_evaluaciones():
    # popsize 10, maxit 4, 1 élite -> 10 + 4x9 = 46 evaluaciones
    _, _, hist = g.correr_ag(semilla_rng=3, popsize=10, maxit=4, n_sim=5)
    assert hist[-1][0] == 10 + 4 * 9
    _, _, hist_a = g.correr_aleatoria(semilla_rng=3, evaluaciones=46, n_sim=5)
    assert hist_a[-1][0] == 46


def test_reproducible():
    a = g.correr_ag(semilla_rng=5, popsize=8, maxit=3, n_sim=5)[1]
    b = g.correr_ag(semilla_rng=5, popsize=8, maxit=3, n_sim=5)[1]
    assert a == b
