"""
Comparación para el Avance 2: AG (con tres métodos de emparejamiento) contra
búsqueda aleatoria, con el MISMO presupuesto de evaluaciones y varias repeticiones.

Uso:  python comparar.py
Genera: convergencia.png  y  resultados.csv
"""
import csv
import statistics as st
import time
import motor as m
import genetico as g

REPETICIONES = 10
POPSIZE, MAXIT, N_ELITE = 30, 20, 1
EVALS = POPSIZE + MAXIT * (POPSIZE - N_ELITE)        # 610
N_SIM = 30
SEMILLA_BUSQUEDA = 0                                  # semillas de combate al optimizar
SEMILLA_PRUEBA = 500                                  # semillas NUEVAS para revalidar
METODOS = ["rango", "costo", "torneo"]


def curva_en_rejilla(historia, evals=EVALS):
    """Convierte la historia (evaluaciones, mejor_costo) en un valor por evaluación,
    para poder promediar curvas de distinta longitud."""
    fila, k = [], 0
    for e in range(1, evals + 1):
        while k + 1 < len(historia) and historia[k + 1][0] <= e:
            k += 1
        fila.append(historia[k][1])
    return fila


def revalidar(bits):
    """Reevalúa al mejor jefe con semillas que NUNCA se usaron al optimizar.
    Si el fitness se cae mucho, el AG se sobreajustó a las semillas."""
    return m.evaluar_jefe(g.decodificar(bits), n=N_SIM, semilla=SEMILLA_PRUEBA)["fitness"]


def correr_todo():
    datos = {}
    for metodo in METODOS + ["aleatoria"]:
        finales, revalidados, curvas, segundos = [], [], [], []
        for rep in range(REPETICIONES):
            t = time.time()
            if metodo == "aleatoria":
                bits, c, hist = g.correr_aleatoria(semilla_rng=100 + rep, evaluaciones=EVALS,
                                                   n_sim=N_SIM, semilla_sim=SEMILLA_BUSQUEDA)
            else:
                bits, c, hist = g.correr_ag(semilla_rng=100 + rep, popsize=POPSIZE, maxit=MAXIT,
                                            n_elite=N_ELITE, n_sim=N_SIM,
                                            semilla_sim=SEMILLA_BUSQUEDA, seleccion=metodo)
            finales.append(1 - c)                      # fitness del mejor encontrado
            revalidados.append(revalidar(bits))
            curvas.append(curva_en_rejilla(hist))
            segundos.append(time.time() - t)
        datos[metodo] = {"fitness": finales, "revalidado": revalidados,
                         "curva": [st.mean(col) for col in zip(*curvas)],
                         "segundos": st.mean(segundos)}
        print("%-10s F = %.4f +- %.4f  (revalidado %.4f)  %.1f s/corrida"
              % (metodo, st.mean(finales), st.pstdev(finales),
                 st.mean(revalidados), datos[metodo]["segundos"]))
    return datos


def evals_para_llegar(curva, objetivo):
    """Cuántas evaluaciones necesitó la curva promedio para bajar de 1-objetivo."""
    for i, c in enumerate(curva, start=1):
        if 1 - c >= objetivo:
            return i
    return None


def guardar(datos):
    with open("resultados.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metodo", "fitness_medio", "desv", "fitness_min", "fitness_max",
                    "revalidado_medio", "evals_para_F0.70", "evals_para_F0.80", "seg_por_corrida"])
        for k, d in datos.items():
            w.writerow([k, round(st.mean(d["fitness"]), 4), round(st.pstdev(d["fitness"]), 4),
                        round(min(d["fitness"]), 4), round(max(d["fitness"]), 4),
                        round(st.mean(d["revalidado"]), 4),
                        evals_para_llegar(d["curva"], 0.70), evals_para_llegar(d["curva"], 0.80),
                        round(d["segundos"], 1)])

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    estilos = {"rango": "-", "costo": "--", "torneo": "-.", "aleatoria": ":"}
    etiquetas = {"rango": "AG, rango", "costo": "AG, costo",
                 "torneo": "AG, torneo", "aleatoria": "Búsqueda aleatoria"}
    for k, d in datos.items():
        ax.plot(range(1, EVALS + 1), [1 - c for c in d["curva"]],
                estilos[k], label=etiquetas[k], linewidth=1.8)
    ax.set_xlabel("Evaluaciones de la función de costo")
    ax.set_ylabel("Mejor fitness F encontrado")
    ax.set_title("Convergencia: promedio de %d corridas" % REPETICIONES)
    ax.legend(loc="lower right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig("convergencia.png", dpi=160)
    print("\nguardados: convergencia.png y resultados.csv")


if __name__ == "__main__":
    t = time.time()
    datos = correr_todo()
    guardar(datos)
    print("total %.0f s" % (time.time() - t))
