# Pruebas a mano del AG. Cada valor esperado está calculado en el comentario.
# Correr con:  python -m pytest -q
import random
import pytest
import motor as m
import genetico as g


def enBits(valor, ancho):
    return [int(c) for c in format(valor, "0%db" % ancho)]


# 1. Codificación: 134 bits y cómo se parten
def test_tamano_del_cromosoma():
    # 6 atributos x 4 + 2 objetos x 4 + 8 ataques x 5 + 8 pesos x 2
    # + 2 cambios x (3 + 5) + 5 ajustes x 2 + 6 predisposiciones x 3 + 2 de bloqueo
    assert 24 + 8 + 40 + 16 + 16 + 10 + 18 + 2 == 134
    assert g.N_BITS == 134


def test_entero_desde_bits():
    assert g._entero([1, 0, 0, 0]) == 8      # 8+0+0+0
    assert g._entero([0, 1, 0, 1]) == 5      # 0+4+0+1
    assert g._entero([1, 1, 1]) == 7
    assert enBits(5, 4) == [0, 1, 0, 1]


# 2. Decodificación completa, calculada a mano
def test_decodificar_a_mano():
    bits = []
    for v in [4, 4, 2, 2, 2, 1]:            # atributos, suman 15
        bits += enBits(v, 4)
    for v in [0, 5]:                        # objetos
        bits += enBits(v, 4)
    for v in range(8):                      # cola de ataques: 0 a 7
        bits += enBits(v, 5)
    for v in [0, 1, 2, 3, 0, 1, 2, 3]:      # pesos
        bits += enBits(v, 2)
    for v in [0, 7]:                        # posiciones que cambian en la fase 2
        bits += enBits(v, 3)
    for v in [8, 30]:                       # ataques que entran
        bits += enBits(v, 5)
    for v in [3, 0, 1, 2, 3]:               # ajustes de atributos
        bits += enBits(v, 2)
    for v in [0, 7, 0, 0, 0, 0]:            # predisposición por clase
        bits += enBits(v, 3)
    bits += enBits(2, 2)                    # bloqueo
    assert len(bits) == 134

    c = g.decodificar(bits)
    # puntos = 100 fijos + 900 por proporción:
    #   100 + 900x4/15 = 340 | 100 + 900x2/15 = 220 | 100 + 900x1/15 = 160
    assert c["puntos"] == [340, 340, 220, 220, 220, 160]
    assert sum(c["puntos"]) == 1500
    assert (c["objeto1"], c["objeto2"]) == (0, 5)
    assert c["habs"] == [0, 1, 2, 3, 4, 5, 6, 7]
    assert c["pesos"] == [0, 1, 2, 3, 0, 1, 2, 3]
    assert c["cambios"] == [[0, 8], [7, 30]]
    assert c["ajustes"] == [3, 0, 1, 2, 3]
    assert c["predisposicion"] == [0, 7, 0, 0, 0, 0]
    assert c["probBloqueo"] == 2


def testCualquierCadenaEsUnJefeValido():
    # Todo en ceros repetiría el ataque 0 ocho veces: la reparación deja 0 a 7 en
    # la cola y manda los dos cambios de la fase 2 a los siguientes libres, 8 y 9.
    c = g.decodificar([0] * 134)
    assert c["habs"] == [0, 1, 2, 3, 4, 5, 6, 7]
    assert c["cambios"] == [[0, 8], [0, 9]]
    assert c["puntos"] == [250] * 6
    rng = random.Random(3)
    for _ in range(200):
        c = g.decodificar(g.bits_al_azar(rng))
        assert len(set(c["habs"])) == 8 and sum(c["puntos"]) == 1500
        assert not {nuevo for _, nuevo in c["cambios"]} & set(c["habs"])


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
    n = g.N_BITS
    p1, p2 = [0] * n, [1] * n

    class RNGCorte:
        def randrange(self, a, b=None): return 10          # corta en el bit 10
    h1, h2 = g.cruce_un_punto(p1, p2, RNGCorte())
    assert h1 == [0] * 10 + [1] * (n - 10)
    assert h2 == [1] * 10 + [0] * (n - 10)
    # Ningún bit se pierde: cada posición sigue teniendo un 0 y un 1 entre los dos hijos
    assert all(a + b == 1 for a, b in zip(h1, h2))


# 5. Mutación
def test_mutacion_extremos():
    n = g.N_BITS
    rng = random.Random(0)
    iguales, _ = g.mutar([0] * n, 0.0, rng)
    assert iguales == [0] * n                               # tasa 0: no cambia nada
    todos, cambios = g.mutar([0] * n, 1.0, rng)
    assert todos == [1] * n and cambios == n                # tasa 1: se voltean todos


def test_mutacion_tasa_esperada():
    # Con tasa 1/N_BITS se espera 1 bit mutado por cromosoma. En 2000 cromosomas,
    # el promedio debe acercarse a 1 (tolerancia amplia, es aleatorio).
    n = g.N_BITS
    rng = random.Random(7)
    total = sum(g.mutar([0] * n, 1 / n, rng)[1] for _ in range(2000))
    assert 0.85 < total / 2000 < 1.15


# 6. Elitismo: el mejor costo nunca empeora
def test_elitismo_la_curva_nunca_sube():
    _, _, hist = g.correr_ag(semilla_rng=3, popsize=10, maxit=4, n_sim=2)
    costos = [c for _, c in hist]
    assert all(b <= a + 1e-12 for a, b in zip(costos, costos[1:]))


def test_mismo_presupuesto_de_evaluaciones():
    # popsize 10, maxit 4, 1 élite -> 10 + 4x9 = 46 evaluaciones
    _, _, hist = g.correr_ag(semilla_rng=3, popsize=10, maxit=4, n_sim=2)
    assert hist[-1][0] == 10 + 4 * 9
    _, _, hist_a = g.correr_aleatoria(semilla_rng=3, evaluaciones=46, n_sim=2)
    assert hist_a[-1][0] == 46


def test_reproducible():
    a = g.correr_ag(semilla_rng=5, popsize=8, maxit=3, n_sim=2)[1]
    b = g.correr_ag(semilla_rng=5, popsize=8, maxit=3, n_sim=2)[1]
    assert a == b


# 7. Semillas rotativas
def testRotarSemillasEvaluaATodaLaPoblacion():
    # popsize 10, maxit 4: con rotación la élite también se vuelve a evaluar
    # -> 10 + 4x10 = 50 evaluaciones en lugar de 46
    _, _, hist = g.correr_ag(semilla_rng=3, popsize=10, maxit=4, n_sim=2, rotarSemillas=True)
    assert hist[-1][0] == 10 + 4 * 10
    a = g.correr_ag(semilla_rng=3, popsize=10, maxit=4, n_sim=2, rotarSemillas=True)[1]
    assert a == hist[-1][1]
