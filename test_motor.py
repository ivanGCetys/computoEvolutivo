"""
Pruebas a mano del motor v0.1. Cada valor esperado está calculado a mano en el
comentario. Correr con:  python -m pytest -q
"""
import math
import pytest
import motor as m


# 1. Ciclo elemental: fuego > hielo > viento > tierra > fuego
def test_elementos():
    assert m.mult_elemental(m.FUEGO, m.HIELO) == 1.5    # fuego vence a hielo
    assert m.mult_elemental(m.HIELO, m.FUEGO) == 0.5    # fuego resiste a hielo
    assert m.mult_elemental(m.TIERRA, m.FUEGO) == 1.5   # tierra vence a fuego
    assert m.mult_elemental(m.FUEGO, m.VIENTO) == 1.0   # no son vecinos
    assert m.mult_elemental(m.FUEGO, m.FUEGO) == 1.0    # mismo elemento = neutro
    assert m.mult_elemental(None, m.HIELO) == 1.0       # ataque sin elemento


# 2. Fórmula de daño
def test_dano_basico_del_equipo():
    # Fuego, básico, contra DEF 250: 60 x 0.8 x 100/350 = 13.71 -> 13
    assert m.calcular_dano(60, 0.8, 1.0, 250) == 13


def test_dano_jefe_elemental_mata_de_un_golpe():
    # Jefe ATK 250, Ráfaga de fuego contra Hielo (DEF 30, débil):
    # 250 x 1.2 x 1.5 x 100/130 = 346.15 -> 346  (Hielo tiene 240 HP)
    assert m.calcular_dano(250, 1.2, 1.5, 30) == 346


def test_dano_minimo_1():
    # 10 x 0.8 x 0.5 x 100/600 = 0.67 -> 0 -> se sube a 1
    assert m.calcular_dano(10, 0.8, 0.5, 500) == 1


def test_bloqueo_del_tanque():
    # 300 x 0.8 x 100/160 = 150; con bloqueo de Tierra x0.3 = 45
    assert m.calcular_dano(300, 0.8, 1.0, 60, 0.3) == 45


# 3. Reparación del cromosoma
def test_reparar_puntos_todo_a_hp():
    # [1,0,0,0] -> HP = 100 + 600 = 700 > 500 -> se recorta a 500
    # el exceso de 200 se reparte en 3: 166.67 c/u -> enteros 166,166,166 (suma 998)
    # faltan 2 puntos -> van a los de mayor residuo (empate: los primeros índices)
    c = m.reparar({"puntos": [1, 0, 0, 0], "elem1": 0, "elem2": 0, "habs": [0, 1, 2, 3], "pesos": [1, 1, 1, 1]})
    assert c["puntos"] == [500, 167, 167, 166]
    assert sum(c["puntos"]) == 1000


def test_reparar_pesos_y_habilidades():
    # pesos [1,0,0,0]: solo 1 habilidad > 10% -> la 2a mayor (índice 1) sube a 0.15
    # [1, 0.15, 0, 0] / 1.15 = [0.8696, 0.1304, 0, 0]
    # habs [2,2,2,2]: los repetidos se cambian por el menor índice libre -> [2,0,1,3]
    c = m.reparar({"puntos": [1, 1, 1, 1], "elem1": 5, "elem2": -1, "habs": [2, 2, 2, 2], "pesos": [1, 0, 0, 0]})
    assert c["pesos"][0] == pytest.approx(1 / 1.15)
    assert c["pesos"][1] == pytest.approx(0.15 / 1.15)
    assert c["habs"] == [2, 0, 1, 3]
    assert c["puntos"] == [250, 250, 250, 250]
    assert (c["elem1"], c["elem2"]) == (1, 3)   # 5 % 4 = 1 ; -1 % 4 = 3


# 4. Objetivo del jefe
def test_objetivo_jefe():
    eq, hp = m.EQUIPO_BASE, [260, 240, 250, 380]
    assert m.objetivo_jefe(m.FUEGO, eq, hp) == 1     # fuego -> Hielo es débil
    assert m.objetivo_jefe(m.TIERRA, eq, hp) == 0    # tierra -> Fuego es débil
    # Si Hielo está muerto, un jefe de fuego va por el de menor HP: Viento (250)
    assert m.objetivo_jefe(m.FUEGO, eq, [260, 0, 250, 380]) == 2


# 5. Una ronda completa calculada a mano (escala calibrada: HP x3, ATK //2, DEF //3)
def test_ronda_1_a_mano(monkeypatch):
    # Jefe: puntos [500,100,300,100] -> HP 1500, ATK 50, DEF 100, VEL 10. Elemento viento.
    # Orden: Viento(30), Fuego(20), Hielo(15), Tierra(10), Jefe(10; empate -> equipo primero)
    # Viento: fuerte. HP 250-50=200. Daño 50x1.6x100/200 = 40 -> jefe 1460
    # Fuego:  fuerte. HP 260-52=208. Daño 60x1.6/2      = 48 -> jefe 1412
    # Hielo:  nadie < 40%; hielo vence a viento -> magia. SP 105. 40x1.2x1.5/2 = 36 -> 1376
    # Tierra: fuerte. HP 380-76=304. Daño 35x1.6/2      = 28 -> jefe 1348
    # Jefe:   Zarpazo (peso 1) a Tierra (débil a viento). 50x0.8x100/160 = 25 -> Tierra 279
    monkeypatch.setattr(m, "RONDAS_MAX", 1)
    crom = {"puntos": [500, 100, 300, 100], "elem1": m.VIENTO, "elem2": m.VIENTO,
            "habs": [0, 1, 2, 3], "pesos": [1, 0, 0, 0]}
    assert m.stats_jefe(crom) == {"hp": 1500, "atk": 50, "defe": 100, "vel": 10.0}
    r = m.simular(crom, semilla=0)
    assert r["hp_equipo"] == [208, 240, 200, 279]
    assert r["hp_jefe"] == 1348
    assert r["tope"] and r["gana_equipo"]           # tope de rondas = derrota del jefe
    assert r["hp_final_pct"] == pytest.approx(927 / 1130)


# 6. Cooldown: Golpe pesado (cooldown 2) solo puede salir 1 de cada 3 turnos
def test_cooldown_golpe_pesado():
    # Peso 1 en Golpe pesado y 0 en las demás: sale en los turnos 1, 4, 7, ...
    # => usos de Golpe = techo(turnos_del_jefe / 3)
    crom = {"puntos": [500, 100, 300, 100], "elem1": m.VIENTO, "elem2": m.VIENTO,
            "habs": [1, 0, 2, 4], "pesos": [1, 0, 0, 0]}
    r = m.simular(crom, semilla=3)
    turnos = sum(r["usos"])
    assert r["usos"][0] == math.ceil(turnos / 3)


# 7. Semilla: mismo resultado con la misma semilla
def test_reproducible():
    crom = m.reparar({"puntos": [3, 2, 2, 1], "elem1": 0, "elem2": 2, "habs": [0, 2, 4, 6], "pesos": [1, 1, 1, 1]})
    assert m.simular(crom, semilla=7) == m.simular(crom, semilla=7)
    assert m.evaluar(crom, n=10, semilla=5) == m.evaluar(crom, n=10, semilla=5)


# 8. Fase 2: el jefe la activa al empezar su turno con HP < 50%, una sola vez
def test_fase2_ocurre():
    # Jefe [220,220,280,280] -> HP 660. Con la semilla 0 el equipo gana en la ronda 9
    # y el jefe entra a fase 2 en la ronda 4 (verificado: una victoria exige pasar por < 330 HP).
    crom = {"puntos": [220, 220, 280, 280], "elem1": m.FUEGO, "elem2": m.VIENTO,
            "habs": [0, 2, 4, 6], "pesos": [0.25] * 4}
    r = m.simular(crom, semilla=0)
    assert r["gana_equipo"] and not r["tope"]
    assert r["ronda_fase2"] == 4


def test_fase2_no_ocurre_si_no_baja_de_50(monkeypatch):
    # Ronda 1 del test 5: el jefe queda en 1348 de 1500 (90%) -> no entra a fase 2
    monkeypatch.setattr(m, "RONDAS_MAX", 1)
    crom = {"puntos": [500, 100, 300, 100], "elem1": m.VIENTO, "elem2": m.FUEGO,
            "habs": [0, 1, 2, 3], "pesos": [1, 0, 0, 0]}
    assert m.simular(crom, semilla=0)["ronda_fase2"] is None


# 9 y 10. Fitness con resultados inventados
def _res(gana, hp_pct, rondas):
    return {"gana_equipo": gana, "hp_final_pct": hp_pct, "rondas": rondas, "usos": [1, 1, 1, 1], "tope": False}


def test_fitness_perfecto():
    # 6 de 10 victorias (banda 50-70%) con 20% de HP, 10 rondas, uso uniforme
    # f_win = 1, margen = 1, duración = 1, variedad = 2/2 = 1  -> fitness = 1.0
    res = [_res(True, 0.20, 10)] * 6 + [_res(False, 0.0, 10)] * 4
    f = m.calcular_fitness(res)
    assert f["fitness"] == pytest.approx(1.0)


def test_fitness_fuera_de_banda_y_margen():
    # Banda media = 40-60%. 9 de 10 victorias -> p = 0.9
    # distancia a la banda: d = 0.9 - 0.60 = 0.30 -> f_win = 1 - 2(0.30) = 0.40
    # HP final 60%: margen = 1 - |0.6-0.2|/0.8 = 0.5
    # 13 rondas: duración = exp(-(13-10)^2 / (2x3^2)) = exp(-0.5) = 0.6065
    # variedad: usos [1,1,1,1] -> H = 2 bits -> 2/2 = 1
    # fitness = 0.40 x (0.5x0.5 + 0.25x0.6065 + 0.25x1) = 0.40 x 0.6516 = 0.2607
    res = [_res(True, 0.60, 13)] * 9 + [_res(False, 0.0, 13)]
    f = m.calcular_fitness(res)
    assert f["f_win"] == pytest.approx(0.4)
    assert f["margen"] == pytest.approx(0.5)
    assert f["duracion"] == pytest.approx(math.exp(-0.5))
    assert f["fitness"] == pytest.approx(0.4 * (0.25 + 0.25 * math.exp(-0.5) + 0.25))
    assert f["fitness"] == pytest.approx(0.2606533, abs=1e-6)


def test_cuatro_equipos_toma_el_peor():
    # Los 4 equipos son rotaciones: mismos stats y mismo HP total, solo cambia
    # qué elemento le toca a cada rol. A = base; B, C y D corren 1, 2 y 3 lugares.
    assert list(m.EQUIPOS) == ["A", "B", "C", "D"]
    for eq in m.EQUIPOS.values():
        assert sum(p["hp"] for p in eq) == 1130
    assert [p["elem"] for p in m.EQUIPO_A] == [m.FUEGO, m.HIELO, m.VIENTO, m.TIERRA]
    assert [p["elem"] for p in m.EQUIPO_B] == [m.HIELO, m.VIENTO, m.TIERRA, m.FUEGO]
    assert [p["elem"] for p in m.EQUIPO_C] == [m.VIENTO, m.TIERRA, m.FUEGO, m.HIELO]
    assert [p["elem"] for p in m.EQUIPO_D] == [m.TIERRA, m.FUEGO, m.HIELO, m.VIENTO]

    crom = {"puntos": [300, 300, 200, 200], "elem1": m.FUEGO, "elem2": m.HIELO,
            "habs": [0, 1, 2, 5], "pesos": [0.25] * 4}
    r = m.evaluar_jefe(crom, n=10, semilla=0)
    uno = {k: m.evaluar(m.reparar(crom), eq, n=10, semilla=0)["fitness"]
           for k, eq in m.EQUIPOS.items()}
    assert r["fitness"] == pytest.approx(min(uno.values()))
    assert r["peor_equipo"] == min(uno, key=uno.get)
    assert r["fitness_equipos"] == pytest.approx(uno)
    # Costo = 1 - fitness (se minimiza)
    assert m.costo(crom, n=10, semilla=0) == pytest.approx(1 - min(uno.values()))


def test_fitness_extremos_quedan_abajo():
    # Con la banda 40-60% ya NINGÚN jefe vale exactamente 0: la distancia máxima
    # es 0.40, así que el piso de f_win es 1 - 2(0.40) = 0.20.
    # Jefe invencible (0 victorias): d = 0.40 - 0 = 0.40 -> f_win = 0.20
    #   margen = 0 (no hay victorias); duración = exp(0) = 1; variedad = 1
    #   fitness = 0.20 x (0.5x0 + 0.25x1 + 0.25x1) = 0.20 x 0.5 = 0.10
    invencible = [_res(False, 0.0, 10)] * 10
    f_inv = m.calcular_fitness(invencible)
    assert f_inv["f_win"] == pytest.approx(0.2)
    assert f_inv["fitness"] == pytest.approx(0.10)

    # Jefe trivial (10 de 10 victorias): d = 1.0 - 0.60 = 0.40 -> mismo f_win = 0.20
    trivial = [_res(True, 0.95, 2)] * 10
    assert m.calcular_fitness(trivial)["f_win"] == pytest.approx(0.2)

    # Lo que importa: los dos extremos quedan muy por debajo de un jefe en banda.
    en_banda = [_res(True, 0.20, 10)] * 5 + [_res(False, 0.0, 10)] * 5
    assert m.calcular_fitness(en_banda)["fitness"] > 5 * f_inv["fitness"]
