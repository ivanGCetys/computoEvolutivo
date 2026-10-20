"""
Calibración: simula jefes aleatorios (como la población inicial de un AG) y reporta
la distribución de la tasa de victoria del equipo. Uso: python calibrar.py
"""
import random
import time
import motor as m


def jefe_aleatorio(rng):
    return m.reparar({
        "puntos": [rng.random() for _ in range(4)],
        "elem1": rng.randrange(4), "elem2": rng.randrange(4),
        "habs": rng.sample(range(m.N_HABILIDADES), 4),
        "pesos": [rng.random() for _ in range(4)],
    })


def correr(n_jefes=2000, n_sim=30, semilla=123):
    rng = random.Random(semilla)
    filas = []
    for _ in range(n_jefes):
        c = jefe_aleatorio(rng)
        f = m.evaluar(c, n=n_sim, semilla=0)
        filas.append((c, f))
    return filas


def histograma(filas, campo="p_victoria"):
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
    print("segundos:", round(time.time() - t, 1))
    print(histograma(filas))
