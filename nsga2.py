# NSGA-II para diseñar jefes con tres objetivos a la vez, en lugar de juntarlos
# en un solo número. Usa el mismo cromosoma, el mismo cruce y la misma mutación
# que el algoritmo genético de genetico.py; lo que cambia es cómo se decide
# quién sobrevive.
#
# Uso: python nsga2.py
import random
import motor as m
import genetico as g

nombresObjetivos = ["desbalance", "holgura", "desajuste de duracion"]
puntoReferencia = (1.0, 1.0, 1.0)


def objetivosBits(bits, n=m.combatesPorEquipo, semilla=0):
    # Devuelve la tupla de objetivos y la violación de la restricción.
    return m.objetivos(g.decodificar(bits), n=n, semilla=semilla)


def domina(a, b, violA=0.0, violB=0.0):
    # Dominancia con restricciones: un jefe que cumple la restricción le gana a
    # uno que no, y entre dos que no la cumplen gana el que la viola menos. Solo
    # cuando empatan en eso se comparan los objetivos: a domina a b si no es
    # peor en ninguno y es mejor en al menos uno.
    if violA != violB:
        return violA < violB
    return all(x <= y for x, y in zip(a, b)) and any(x < y for x, y in zip(a, b))


def ordenarPorFrentes(objs, viols=None):
    # Ordenamiento no dominado rápido. Devuelve una lista de frentes, cada uno
    # con los índices de sus individuos. El primero es el frente de Pareto.
    n = len(objs)
    viols = viols or [0.0] * n
    dominados = [[] for _ in range(n)]
    cuantosLoDominan = [0] * n

    for p in range(n):
        for q in range(p + 1, n):
            if domina(objs[p], objs[q], viols[p], viols[q]):
                dominados[p].append(q)
                cuantosLoDominan[q] += 1
            elif domina(objs[q], objs[p], viols[q], viols[p]):
                dominados[q].append(p)
                cuantosLoDominan[p] += 1

    frentes = [[p for p in range(n) if cuantosLoDominan[p] == 0]]
    while frentes[-1]:
        siguiente = []
        for p in frentes[-1]:
            for q in dominados[p]:
                cuantosLoDominan[q] -= 1
                if cuantosLoDominan[q] == 0:
                    siguiente.append(q)
        frentes.append(siguiente)
    return frentes[:-1]


def distanciaCrowding(objs, frente):
    # Qué tan solo está cada individuo dentro de su frente. Los extremos de
    # cada objetivo reciben infinito para que nunca se pierdan.
    dist = {i: 0.0 for i in frente}
    for k in range(len(objs[0])):
        orden = sorted(frente, key=lambda i: objs[i][k])
        lo, hi = objs[orden[0]][k], objs[orden[-1]][k]
        dist[orden[0]] = dist[orden[-1]] = float("inf")

        if hi == lo:
            continue
        for pos in range(1, len(orden) - 1):
            dist[orden[pos]] += (objs[orden[pos + 1]][k] - objs[orden[pos - 1]][k]) / (hi - lo)
    return dist


def rangoYCrowding(objs, viols=None):
    rango, crowding = [0] * len(objs), [0.0] * len(objs)
    for r, frente in enumerate(ordenarPorFrentes(objs, viols)):
        dist = distanciaCrowding(objs, frente)
        for i in frente:
            rango[i], crowding[i] = r, dist[i]
    return rango, crowding


def torneoBinario(rango, crowding, rng):
    # Gana el de mejor frente y, si empatan, el que tiene más espacio alrededor.
    a, b = rng.randrange(len(rango)), rng.randrange(len(rango))
    if (rango[b], -crowding[b]) < (rango[a], -crowding[a]):
        return b
    return a


def elegirSobrevivientes(objs, cuantos, viols=None):
    # Se llenan los lugares frente por frente. El frente que ya no cabe completo
    # se recorta dejando a los de mayor distancia de crowding.
    elegidos = []
    for frente in ordenarPorFrentes(objs, viols):
        if len(elegidos) + len(frente) <= cuantos:
            elegidos.extend(frente)
            continue
        dist = distanciaCrowding(objs, frente)
        resto = sorted(frente, key=lambda i: (-dist[i], i))
        elegidos.extend(resto[:cuantos - len(elegidos)])
        break
    return elegidos


def area2d(puntos, ref):
    # Área dominada por puntos de dos objetivos, medida hasta el punto de referencia.
    area, techo = 0.0, ref[1]
    for x, y in sorted(puntos):
        if y < techo:
            area += (ref[0] - x) * (techo - y)
            techo = y
    return area


def hipervolumen(puntos, ref=puntoReferencia):
    # Volumen dominado por un frente de tres objetivos. Se rebana a lo largo
    # del tercero y en cada rebanada se mide el área de los puntos ya alcanzados.
    puntos = sorted((p for p in puntos if all(v < r for v, r in zip(p, ref))), key=lambda p: p[2])
    volumen = 0.0
    for i, p in enumerate(puntos):
        siguienteCorte = puntos[i + 1][2] if i + 1 < len(puntos) else ref[2]
        volumen += area2d([q[:2] for q in puntos[:i + 1]], ref) * (siguienteCorte - p[2])
    return volumen


def crearHijos(pob, objs, viols, rng, probCruce, tasaMut):
    rango, crowding = rangoYCrowding(objs, viols)
    hijos = []
    while len(hijos) < len(pob):
        p1 = pob[torneoBinario(rango, crowding, rng)]
        p2 = pob[torneoBinario(rango, crowding, rng)]
        if rng.random() < probCruce:
            h1, h2 = g.cruce_un_punto(p1, p2, rng)
        else:
            h1, h2 = list(p1), list(p2)

        hijos.append(g.mutar(h1, tasaMut, rng)[0])
        if len(hijos) < len(pob):
            hijos.append(g.mutar(h2, tasaMut, rng)[0])
    return hijos


def evaluarPoblacion(pob, nSim, semilla):
    pares = [objetivosBits(b, nSim, semilla) for b in pob]
    return [p[0] for p in pares], [p[1] for p in pares]


def hipervolumenDelFrente(objs, viols):
    # Solo cuentan los jefes del primer frente que cumplen la restricción.
    primero = ordenarPorFrentes(objs, viols)[0]
    return hipervolumen([objs[i] for i in primero if viols[i] == 0])


def correrNsga2(semillaRng=0, tamPoblacion=30, generaciones=10, probCruce=0.9,
                tasaMut=1 / g.N_BITS, nSim=m.combatesPorEquipo, semillaSim=0,
                rotarSemillas=True, verbose=False, alAvanzar=None):
    # Devuelve el frente final como lista de (bits, objetivos, violación) y la
    # historia como pares de (evaluaciones acumuladas, hipervolumen del frente).
    #
    # Con rotarSemillas cada generación pelea combates distintos. Eso ataca el
    # sobreajuste que vimos con semillas fijas, donde un jefe sobrevivía por
    # tener suerte con unos combates en particular. El costo es que los padres
    # se tienen que volver a evaluar para compararlos con sus hijos en los mismos
    # combates, así que cada generación gasta el doble de evaluaciones.
    #
    # alAvanzar, si se da, se llama al terminar cada generación con el número
    # de generación, las evaluaciones, el hipervolumen y los objetivos y
    # violaciones de la población. Solo sirve para mostrar el avance; no cambia
    # nada del algoritmo.
    rng = random.Random(semillaRng)
    pob = [g.bits_al_azar(rng) for _ in range(tamPoblacion)]
    objs, viols = evaluarPoblacion(pob, nSim, semillaSim)
    evals = tamPoblacion
    historia = [(evals, hipervolumenDelFrente(objs, viols))]

    for gen in range(1, generaciones + 1):
        hijos = crearHijos(pob, objs, viols, rng, probCruce, tasaMut)

        if rotarSemillas:
            semillaGen = semillaSim + gen * nSim
            objs, viols = evaluarPoblacion(pob, nSim, semillaGen)
            evals += tamPoblacion
        else:
            semillaGen = semillaSim

        objsHijos, violsHijos = evaluarPoblacion(hijos, nSim, semillaGen)
        evals += tamPoblacion
        todos, objsTodos, violsTodos = pob + hijos, objs + objsHijos, viols + violsHijos

        quedan = elegirSobrevivientes(objsTodos, tamPoblacion, violsTodos)
        pob = [todos[i] for i in quedan]
        objs = [objsTodos[i] for i in quedan]
        viols = [violsTodos[i] for i in quedan]

        hv = hipervolumenDelFrente(objs, viols)
        historia.append((evals, hv))
        if verbose:
            print("gen %2d  evals %4d  hipervolumen %.4f" % (gen, evals, hv))
        if alAvanzar is not None:
            alAvanzar(gen, evals, hv, objs, viols)

    # Dos cromosomas distintos pueden decodificar al mismo jefe, y en el frente
    # final solo interesa uno de cada uno.
    frente, vistos = [], set()
    for i in ordenarPorFrentes(objs, viols)[0]:
        clave = repr(g.decodificar(pob[i]))
        if clave not in vistos:
            vistos.add(clave)
            frente.append((pob[i], objs[i], viols[i]))
    return frente, historia


def notaAproximada(objs):
    # La misma fórmula de F armada con los tres objetivos. No es F exacta: usa
    # la distancia a 50% en lugar de la distancia a la banda y da la variedad
    # por buena. Alcanza para ordenar el frente sin gastar más evaluaciones.
    desbalance, holgura, desajuste = objs
    return (1 - desbalance) * (0.5 * (1 - holgura) + 0.25 * (1 - desajuste) + 0.25)


def elegirDelFrente(frente):
    # Del frente hay que quedarse con un jefe para jugar y para comparar contra
    # el algoritmo de un solo objetivo. Se prefiere a los que cumplen la
    # restricción y, entre ellos, al de mejor nota aproximada.
    return max(frente, key=lambda t: (t[2] == 0, notaAproximada(t[1])))


def elegirParaJugar(frente, cuantos=5, n=30, semilla=7000):
    # El jefe contra el que se juega. Los objetivos del frente se midieron con
    # pocos combates y traen mucho ruido, así que de los mejores según
    # elegirDelFrente se vuelve a medir a cada uno con combates nuevos y se
    # queda el que mejor sale. Usa semillas distintas a las de la validación
    # para que el número que se reporta después no salga inflado por escoger.
    candidatos = sorted(frente, key=lambda t: (t[2] == 0, notaAproximada(t[1])), reverse=True)[:cuantos]
    return max(candidatos, key=lambda t: m.evaluar_jefe(g.decodificar(t[0]), n=n, semilla=semilla)["fitness"])


if __name__ == "__main__":
    frente, historia = correrNsga2(semillaRng=1)
    elegido = elegirDelFrente(frente)

    print("frente de %d jefes, hipervolumen %.4f, %d evaluaciones"
          % (len(frente), historia[-1][1], historia[-1][0]))
    print("%-12s %-9s %-23s %-11s %s" % (tuple(nombresObjetivos) + ("violacion", "nota")))
    for bits, objs, viol in sorted(frente, key=lambda t: t[1]):
        marca = "  elegido" if bits is elegido[0] else ""
        print("%-12.3f %-9.3f %-23.3f %-11.3f %.3f%s" % (objs + (viol, notaAproximada(objs), marca)))
