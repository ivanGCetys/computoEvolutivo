# Calibración: simula jefes aleatorios, como la población inicial del algoritmo,
# y cuenta cómo se reparte la tasa de victoria del equipo y qué tanto pesa
# cada clase en ella.
#
# Uso: python calibrar.py
import random
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


def efectoPorClase(filas):
    # Para cada clase, la tasa de victoria media de los equipos que la llevan
    # menos la de los que no. Cerca de cero quiere decir que la clase ni carga
    # ni estorba a su equipo. Solo se usan los jefes de dificultad intermedia,
    # porque contra uno que siempre gana o siempre pierde todos los equipos
    # salen iguales.
    medios = [f for _, f in filas if 0.25 <= f["p_victoria"] <= 0.75]
    porEquipo = {k: sum(f["p_victoria_equipos"][k] for f in medios) / len(medios) for k in m.EQUIPOS}

    efecto = {}
    for nombre in m.nombresClases:
        con = [p for k, p in porEquipo.items() if nombre[0] in k]
        sin = [p for k, p in porEquipo.items() if nombre[0] not in k]
        efecto[nombre] = round(sum(con) / len(con) - sum(sin) / len(sin), 2) + 0.0
    return porEquipo, efecto


if __name__ == "__main__":
    filas = correr()
    porEquipo, efecto = efectoPorClase(filas)

    print(histograma(filas))
    print("victoria por equipo: de %.2f a %.2f" % (min(porEquipo.values()), max(porEquipo.values())))
    print("efecto de llevar cada clase:", efecto)
