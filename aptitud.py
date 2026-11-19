# Función objetivo F y función de costo C = 1 - F.
# F sale de simular varios combates y medir qué tan parejo quedó el jefe.
import math

from clases import EQUIPO_BASE, EQUIPOS
from jefe import reparar
from combate import simular

# Tasa de victoria del equipo que buscamos en cada dificultad. Por ahora solo
# se usa la media.
BANDAS = {"facil": (0.70, 0.90), "media": (0.40, 0.60), "dificil": (0.20, 0.40)}
W_MARGEN, W_DURACION, W_VARIEDAD = 0.5, 0.25, 0.25
RONDAS_IDEAL, SIGMA_RONDAS, HP_IDEAL = 10, 3, 0.20

# Con 15 equipos bajamos los combates por equipo de 30 a 10. Son 150 combates
# por jefe en lugar de 120, casi el mismo trabajo que antes.
combatesPorEquipo = 10
toleranciaBanda = 0.10
componentes = ["fitness", "p_victoria", "f_win", "margen", "duracion", "variedad",
               "desbalance", "rondas_prom", "tope_pct"]


def evaluar(crom, equipo=EQUIPO_BASE, n=combatesPorEquipo, semilla=0, banda=BANDAS["media"]):
    # Todos los individuos de una generación deben usar la misma semilla, si no
    # se estarían comparando combates distintos.
    crom = reparar(crom)
    resultados = [simular(crom, equipo, semilla + k) for k in range(n)]
    return calcular_fitness(resultados, banda)


def evaluar_jefe(crom, n=combatesPorEquipo, semilla=0, banda=BANDAS["media"]):
    # El jugador arma su equipo con 4 de las 6 clases. Al jefe se le califica
    # con el promedio sobre los 15 equipos posibles: con tantos equipos, quedarse
    # con el peor castigaba a jefes buenos por una sola combinación rara.
    crom = reparar(crom)
    f = {k: evaluar(crom, eq, n, semilla, banda) for k, eq in EQUIPOS.items()}

    r = {c: sum(f[k][c] for k in f) / len(f) for c in componentes}
    r["peor_equipo"] = min(f, key=lambda k: f[k]["fitness"])
    r["fitness_equipos"] = {k: f[k]["fitness"] for k in EQUIPOS}
    r["p_victoria_equipos"] = {k: f[k]["p_victoria"] for k in EQUIPOS}
    return r


def costo(crom, n=combatesPorEquipo, semilla=0, banda=BANDAS["media"]):
    return 1.0 - evaluar_jefe(crom, n, semilla, banda)["fitness"]


def objetivos(crom, n=combatesPorEquipo, semilla=0):
    # Los tres objetivos que minimiza NSGA-II. Son los ingredientes de F, pero
    # separados para que el algoritmo no tenga que aceptar los pesos que
    # nosotros escogimos al sumarlos:
    #   desbalance   qué tan lejos queda la tasa de victoria de 50%
    #   holgura      el equipo gana con mucha más vida que el 20% ideal
    #   desajuste    los combates duran mucho más o mucho menos de 10 rondas
    # La variedad se queda fuera. Desde que el jefe ataca con una cola, casi
    # cualquier jefe la tiene arriba de 0.9 y como objetivo solo llenaba el
    # frente de jefes malos que ganaban una centésima de variedad.
    #
    # Junto con los objetivos se devuelve la violación de la restricción: un
    # jefe solo cuenta como aceptable si, en promedio, la tasa de victoria de
    # los equipos queda a no más de toleranciaBanda de la banda 40-60%. Sin
    # esto el frente se llenaba de jefes con la duración perfecta que ningún
    # equipo podía vencer.
    r = evaluar_jefe(crom, n, semilla)
    distanciaBanda = (1 - r["f_win"]) / 2
    violacion = max(0.0, distanciaBanda - toleranciaBanda)
    return (r["desbalance"], 1 - r["margen"], 1 - r["duracion"]), violacion


def calcular_fitness(resultados, banda=BANDAS["media"]):
    # Está separada de evaluar para poder probarla a mano con resultados inventados.
    n = len(resultados)
    victorias = [r for r in resultados if r["gana_equipo"]]
    p = len(victorias) / n

    lo, hi = banda
    d = lo - p if p < lo else (p - hi if p > hi else 0.0)
    f_win = 1 - 2 * d

    margen = (sum(1 - abs(r["hp_final_pct"] - HP_IDEAL) / (1 - HP_IDEAL) for r in victorias) / len(victorias)
              if victorias else 0.0)
    duracion = sum(math.exp(-(r["rondas"] - RONDAS_IDEAL) ** 2 / (2 * SIGMA_RONDAS ** 2)) for r in resultados) / n

    nUsos = len(resultados[0]["usos"])
    usos = [sum(r["usos"][k] for r in resultados) for k in range(nUsos)]
    total = sum(usos)
    H = -sum(u / total * math.log2(u / total) for u in usos if u > 0)

    # La entropía se divide entre su máximo, que es log2 del número de ataques.
    variedad = H / math.log2(nUsos)

    fitness = f_win * (W_MARGEN * margen + W_DURACION * duracion + W_VARIEDAD * variedad)
    return {"fitness": fitness, "p_victoria": p, "f_win": f_win, "margen": margen,
            "duracion": duracion, "variedad": variedad, "desbalance": 2 * abs(p - 0.5),
            "rondas_prom": sum(r["rondas"] for r in resultados) / n,
            "tope_pct": sum(r["tope"] for r in resultados) / n}
