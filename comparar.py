# Compara el algoritmo genético, con tres métodos de emparejamiento, contra la
# búsqueda aleatoria. Todos reciben el mismo presupuesto de evaluaciones.
#
# Uso: python comparar.py
# Genera convergencia.png y resultados.csv
import csv
import statistics as st
import time
from multiprocessing import Pool
import motor as m
import genetico as g

REPETICIONES = 10
POPSIZE, MAXIT, N_ELITE = 30, 20, 1
EVALS = POPSIZE + MAXIT * (POPSIZE - N_ELITE)
N_SIM = m.combatesPorEquipo

# Se optimiza con unas semillas de combate y se revalida con otras que el
# algoritmo nunca vio.
SEMILLA_BUSQUEDA = 0
SEMILLA_PRUEBA = 500
METODOS = ["rango", "costo", "torneo"]


def curva_en_rejilla(historia, evals=EVALS):
    # Deja un valor por evaluación para poder promediar curvas de distinto largo.
    fila, k = [], 0
    for e in range(1, evals + 1):
        while k + 1 < len(historia) and historia[k + 1][0] <= e:
            k += 1
        fila.append(historia[k][1])
    return fila


def revalidar(bits):
    # Si el fitness se cae mucho con semillas nuevas, el algoritmo se
    # sobreajustó a las semillas con las que buscó.
    return m.evaluar_jefe(g.decodificar(bits), n=N_SIM, semilla=SEMILLA_PRUEBA)["fitness"]


def unaCorrida(tarea):
    metodo, rep = tarea
    t = time.time()
    if metodo == "aleatoria":
        bits, c, hist = g.correr_aleatoria(semilla_rng=100 + rep, evaluaciones=EVALS,
                                           n_sim=N_SIM, semilla_sim=SEMILLA_BUSQUEDA)
    else:
        bits, c, hist = g.correr_ag(semilla_rng=100 + rep, popsize=POPSIZE, maxit=MAXIT,
                                    n_elite=N_ELITE, n_sim=N_SIM,
                                    semilla_sim=SEMILLA_BUSQUEDA, seleccion=metodo)
    return 1 - c, revalidar(bits), curva_en_rejilla(hist), time.time() - t


def correr_todo():
    # Las corridas son independientes entre sí, así que se reparten entre los
    # núcleos de la máquina. Cada una lleva su propia semilla y el resultado no
    # depende de en qué orden terminen.
    datos = {}
    with Pool() as pool:
        for metodo in METODOS + ["aleatoria"]:
            corridas = pool.map(unaCorrida, [(metodo, rep) for rep in range(REPETICIONES)])
            finales = [c[0] for c in corridas]
            revalidados = [c[1] for c in corridas]

            datos[metodo] = {"fitness": finales, "revalidado": revalidados,
                             "curva": [st.mean(col) for col in zip(*(c[2] for c in corridas))],
                             "segundos": st.mean(c[3] for c in corridas)}
            print("%-10s F = %.4f +- %.4f  (revalidado %.4f)"
                  % (metodo, st.mean(finales), st.pstdev(finales), st.mean(revalidados)))
    return datos


def evals_para_llegar(curva, objetivo):
    for i, c in enumerate(curva, start=1):
        if 1 - c >= objetivo:
            return i
    return None


def guardar(datos):
    with open("resultados.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metodo", "fitness_medio", "desv", "fitness_min", "fitness_max",
                    "revalidado_medio", "evals_para_F0.60", "evals_para_F0.70", "seg_por_corrida"])
        for k, d in datos.items():
            w.writerow([k, round(st.mean(d["fitness"]), 4), round(st.pstdev(d["fitness"]), 4),
                        round(min(d["fitness"]), 4), round(max(d["fitness"]), 4),
                        round(st.mean(d["revalidado"]), 4),
                        evals_para_llegar(d["curva"], 0.60), evals_para_llegar(d["curva"], 0.70),
                        round(d["segundos"], 1)])

    # El backend Agg dibuja directo a archivo, sin abrir ventana, para que el
    # script corra igual en una terminal sin entorno gráfico.
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


if __name__ == "__main__":
    datos = correr_todo()
    guardar(datos)
