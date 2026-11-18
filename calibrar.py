# Calibración: simula jefes aleatorios, como la población inicial del algoritmo,
# y cuenta cómo se reparte la tasa de victoria del equipo.
#
# Uso: python calibrar.py
import random
import time
import motor as m
import genetico as g


def jefe_aleatorio(rng):
    # Igual que la población inicial del algoritmo: bits al azar y a decodificar.
    return g.decodificar(g.bits_al_azar(rng))


def correr(n_jefes=500, n_sim=m.combatesPorEquipo, semilla=123):
    # Cada jefe pelea contra los 15 equipos, así que la tasa de victoria que se
    # cuenta es el promedio de todos.
    rng = random.Random(semilla)
    filas = []
    for _ in range(n_jefes):
        c = jefe_aleatorio(rng)
        f = m.evaluar_jefe(c, n=n_sim, semilla=0)
        filas.append((c, f))
    return filas


def histograma(filas, campo="p_victoria"):
    # Los cortes en 0.0001 y 0.9999 separan a los jefes que siempre ganan o
    # siempre pierden de los que casi siempre.
    cortes = [0, 0.0001, 0.1, 0.3, 0.5, 0.7, 0.9, 0.9999, 1.0001]
    etiquetas = ["0", "(0,10%)", "[10,30%)", "[30,50%)", "[50,70%)", "[70,90%)", "[90,100%)", "100%"]
    cuenta = [0] * len(etiquetas)

    for _, f in filas:
        v = f[campo]
        for k in range(len(etiquetas)):
            if cortes[k] <= v < cortes[k + 1]:
                cuenta[k] += 1
                break
    return dict(zip(etiquetas, cuenta))


if __name__ == "__main__":
    t = time.time()
    filas = correr()
    print(histograma(filas))
    print("segundos:", round(time.time() - t, 1))
