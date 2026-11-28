# Experimento final: los dos algoritmos, cada uno con semillas fijas y con
# semillas rotativas, contra la búsqueda aleatoria. Todos reciben casi el mismo
# presupuesto de evaluaciones y al final se les mide con combates que ninguno vio.
#
# Uso: python comparar.py          presupuesto largo, 60 generaciones
#      python comparar.py corto    presupuesto del avance 2, 20 generaciones
# Genera resultados_largo.csv, comparacion_largo.png y frente.png, o los mismos
# archivos con "corto" en el nombre y sin la gráfica del frente.
import csv
import statistics as st
import sys
import time
from multiprocessing import Pool

import motor as m
import genetico as g
import nsga2

# Con el presupuesto corto ningún método se separa de la búsqueda aleatoria una
# vez que se mide con combates nuevos, por eso el experimento principal es el largo.
generacionesPorPresupuesto = {"corto": 20, "largo": 60}
presupuesto = "corto" if "corto" in sys.argv else "largo"

REPETICIONES = 10
POPSIZE, N_ELITE = 30, 1
MAXIT = generacionesPorPresupuesto[presupuesto]
N_SIM = m.combatesPorEquipo

# Se busca con unas semillas de combate y se valida con otras, y con el triple
# de combates por equipo para que la nota final traiga menos ruido.
SEMILLA_BUSQUEDA = 0
SEMILLA_PRUEBA = 5000
nValidacion = 30

# El algoritmo genético con semillas fijas no vuelve a evaluar a su élite, por
# eso gasta una evaluación menos por generación que los demás. NSGA-II rotando
# semillas gasta el doble por generación, así que corre la mitad de generaciones.
evalsReferencia = POPSIZE + MAXIT * POPSIZE
METODOS = ["agFijo", "agRotado", "nsga2Fijo", "nsga2Rotado", "aleatoria"]
etiquetas = {"agFijo": "AG, semillas fijas", "agRotado": "AG, semillas rotativas",
             "nsga2Fijo": "NSGA-II, semillas fijas", "nsga2Rotado": "NSGA-II, semillas rotativas",
             "aleatoria": "Búsqueda aleatoria"}


def validar(crom):
    return m.evaluar_jefe(crom, n=nValidacion, semilla=SEMILLA_PRUEBA)


def validarFrente(frente):
    # Vuelve a medir los objetivos de cada jefe del frente con los combates de
    # prueba y se queda con los que siguen cumpliendo la restricción.
    puntos = []
    for bits, _, _ in frente:
        objs, viol = m.objetivos(g.decodificar(bits), n=nValidacion, semilla=SEMILLA_PRUEBA)
        if viol == 0:
            puntos.append(objs)
    return puntos


def unaCorrida(tarea):
    metodo, rep = tarea
    t = time.time()
    semilla = 100 + rep
    fila = {"metodo": metodo, "rep": rep, "fBusqueda": None, "hvValidado": None, "tamFrente": None}

    if metodo.startswith("ag"):
        bits, c, hist = g.correr_ag(semilla_rng=semilla, popsize=POPSIZE, maxit=MAXIT, n_elite=N_ELITE,
                                    n_sim=N_SIM, semilla_sim=SEMILLA_BUSQUEDA,
                                    rotarSemillas=(metodo == "agRotado"))
        fila["fBusqueda"], fila["evals"] = 1 - c, hist[-1][0]

    elif metodo.startswith("nsga2"):
        rotar = metodo == "nsga2Rotado"
        frente, hist = nsga2.correrNsga2(semillaRng=semilla, tamPoblacion=POPSIZE,
                                         generaciones=MAXIT // 2 if rotar else MAXIT,
                                         nSim=N_SIM, semillaSim=SEMILLA_BUSQUEDA, rotarSemillas=rotar)
        bits = nsga2.elegirDelFrente(frente)[0]
        validos = validarFrente(frente)
        fila.update({"evals": hist[-1][0], "tamFrente": len(frente),
                     "hvValidado": nsga2.hipervolumen(validos), "frenteValidado": validos})

    else:
        bits, c, hist = g.correr_aleatoria(semilla_rng=semilla, evaluaciones=evalsReferencia,
                                           n_sim=N_SIM, semilla_sim=SEMILLA_BUSQUEDA)
        fila["fBusqueda"], fila["evals"] = 1 - c, hist[-1][0]

    crom = g.decodificar(bits)
    r = validar(crom)
    fila.update({"fValidado": r["fitness"], "pVictoria": r["p_victoria"], "crom": crom,
                 "objsElegido": m.objetivos(crom, n=nValidacion, semilla=SEMILLA_PRUEBA)[0],
                 "segundos": time.time() - t})
    return fila


def correr_todo():
    # Las corridas son independientes entre sí, así que se reparten entre los
    # núcleos de la máquina. Cada una lleva su propia semilla y el resultado no
    # depende de en qué orden terminen.
    tareas = [(metodo, rep) for metodo in METODOS for rep in range(REPETICIONES)]
    with Pool() as pool:
        filas = pool.map(unaCorrida, tareas)
    return {metodo: [f for f in filas if f["metodo"] == metodo] for metodo in METODOS}


def tDeWelch(a, b):
    # Estadístico t para dos muestras con varianzas distintas.
    return (st.mean(a) - st.mean(b)) / (st.variance(a) / len(a) + st.variance(b) / len(b)) ** 0.5


def media(valores):
    valores = [v for v in valores if v is not None]
    return round(st.mean(valores), 4) if valores else ""


def guardarTabla(datos):
    base = [f["fValidado"] for f in datos["aleatoria"]]
    with open("resultados_%s.csv" % presupuesto, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["metodo", "evaluaciones", "f_busqueda", "f_validado", "desv", "f_min", "f_max",
                    "t_contra_aleatoria", "corridas_que_le_ganan_a_la_media_aleatoria",
                    "hipervolumen_validado", "tamano_frente", "seg_por_corrida"])
        for metodo, filas in datos.items():
            fv = [x["fValidado"] for x in filas]
            w.writerow([metodo, filas[0]["evals"], media(x["fBusqueda"] for x in filas),
                        round(st.mean(fv), 4), round(st.stdev(fv), 4), round(min(fv), 4), round(max(fv), 4),
                        "" if metodo == "aleatoria" else round(tDeWelch(fv, base), 2),
                        "" if metodo == "aleatoria" else sum(v > st.mean(base) for v in fv),
                        media(x["hvValidado"] for x in filas), media(x["tamFrente"] for x in filas),
                        round(st.mean(x["segundos"] for x in filas), 1)])


# Colores de las gráficas. Las dos usan un solo tono: en la primera el método se
# lee en el eje y no hace falta distinguirlo por color, y en la segunda el
# color es una magnitud, así que va de claro a oscuro.
superficie, tinta, tintaSuave, rejilla = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
azul = "#2a78d6"
rampaAzul = ["#9ec5f4", "#5598e7", "#256abf", "#0d366b"]


def prepararEjes(ax):
    ax.set_facecolor(superficie)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(rejilla)
    ax.tick_params(colors=tintaSuave, length=0)
    ax.grid(color=rejilla, linewidth=0.8)
    ax.set_axisbelow(True)


def graficarComparacion(datos, plt):
    fig, ax = plt.subplots(figsize=(7.5, 3.8), facecolor=superficie)
    prepararEjes(ax)
    ax.grid(axis="y", visible=False)

    orden = list(reversed(METODOS))
    for y, metodo in enumerate(orden):
        fv = sorted(x["fValidado"] for x in datos[metodo])
        ax.scatter(fv, [y] * len(fv), s=46, color=azul, alpha=0.55, edgecolors=superficie, linewidths=1.2, zorder=3)

        prom = st.mean(fv)
        ax.plot([prom, prom], [y - 0.3, y + 0.3], color=tinta, linewidth=2, zorder=4)
        ax.annotate("%.3f" % prom, (prom, y + 0.3), xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=9, color=tinta)

    ax.set_yticks(range(len(orden)))
    ax.set_yticklabels([etiquetas[k] for k in orden], color=tinta)
    ax.set_ylim(-0.6, len(orden) - 0.3)
    ax.set_xlabel("F con combates nuevos (cada punto es una corrida, la raya es la media)", color=tintaSuave)
    ax.set_title("Qué tan bueno es el jefe que entrega cada método, con %d evaluaciones" % evalsReferencia,
                 color=tinta, loc="left", fontsize=12)
    fig.tight_layout()
    fig.savefig("comparacion_%s.png" % presupuesto, dpi=160, facecolor=superficie)


def graficarFrente(datos, plt):
    # Se dibuja el frente más grande de las corridas de NSGA-II con semillas
    # fijas, ya medido con los combates de prueba.
    from matplotlib.colors import LinearSegmentedColormap
    corrida = max(datos["nsga2Fijo"], key=lambda x: len(x["frenteValidado"]))
    puntos = corrida["frenteValidado"]
    if not puntos:
        return

    fig, ax = plt.subplots(figsize=(6.6, 4.6), facecolor=superficie)
    prepararEjes(ax)
    mapa = LinearSegmentedColormap.from_list("azules", rampaAzul)
    marcas = ax.scatter([p[1] for p in puntos], [p[2] for p in puntos], c=[p[0] for p in puntos],
                        cmap=mapa, s=70, edgecolors=superficie, linewidths=1.5, zorder=3)

    barra = fig.colorbar(marcas, ax=ax)
    barra.set_label("Desbalance (más oscuro es peor)", color=tintaSuave)
    barra.outline.set_visible(False)
    barra.ax.tick_params(colors=tintaSuave, length=0)

    elegido = corrida["objsElegido"]
    ax.scatter([elegido[1]], [elegido[2]], s=190, facecolors="none", edgecolors=tinta, linewidths=1.6, zorder=4)
    ax.annotate("jefe elegido", (elegido[1], elegido[2]), xytext=(12, 12), textcoords="offset points",
                fontsize=9, color=tinta)

    ax.set_xlabel("Holgura: el equipo gana con vida de sobra", color=tintaSuave)
    ax.set_ylabel("Desajuste de duración", color=tintaSuave)
    ax.set_title("Frente de una corrida de NSGA-II, medido con combates nuevos (%d jefes)" % len(puntos),
                 color=tinta, loc="left", fontsize=12)
    fig.tight_layout()
    fig.savefig("frente.png", dpi=160, facecolor=superficie)


def guardar(datos):
    guardarTabla(datos)

    # El backend Agg dibuja directo a archivo, sin abrir ventana, para que el
    # script corra igual en una terminal sin entorno gráfico.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    graficarComparacion(datos, plt)
    if presupuesto == "largo":
        graficarFrente(datos, plt)


if __name__ == "__main__":
    datos = correr_todo()
    guardar(datos)
    for metodo, filas in datos.items():
        fv = [x["fValidado"] for x in filas]
        print("%-28s F validado = %.4f +- %.4f" % (etiquetas[metodo], st.mean(fv), st.stdev(fv)))
