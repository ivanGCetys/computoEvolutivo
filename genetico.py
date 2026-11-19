# Algoritmo genético binario para diseñar jefes y la búsqueda aleatoria contra
# la que se compara. Sigue el orden del curso: población, costo, selección
# natural, emparejamiento, cruce y mutación.
#
# Uso: python genetico.py
import random
import motor as m

# El cromosoma son 134 bits partidos en tramos. Cada tramo es nombre, cuántos
# valores guarda y cuántos bits ocupa cada valor:
#   puntos          6 de 4 bits, la proporción del presupuesto por atributo
#   objetos         2 de 4 bits, el objeto equipado en cada fase
#   habs            8 de 5 bits, los ataques de la cola tomados del banco de 32
#   pesos           8 de 2 bits, qué tanto prefiere cada ataque de la cola
#   posCambios      2 de 3 bits, qué posiciones de la cola cambian en la fase 2
#   nuevosCambios   2 de 5 bits, por cuáles ataques se cambian
#   ajustes         5 de 2 bits, cómo se mueve cada atributo en la fase 2
#   predisposicion  6 de 3 bits, preferencia por atacar a cada clase
#   bloqueo         1 de 2 bits, qué tan seguido bloquea
# Los valores crudos no tienen que ser válidos porque motor.reparar los arregla.
TRAMOS = [("puntos", 6, 4), ("objetos", 2, 4), ("habs", 8, 5), ("pesos", 8, 2),
          ("posCambios", 2, 3), ("nuevosCambios", 2, 5), ("ajustes", 5, 2),
          ("predisposicion", 6, 3), ("bloqueo", 1, 2)]
N_BITS = sum(cuantos * ancho for _, cuantos, ancho in TRAMOS)


def _entero(bits):
    # El primer bit es el más significativo.
    v = 0
    for b in bits:
        v = v * 2 + b
    return v


def decodificar(bits):
    campos, i = {}, 0
    for nombre, cuantos, ancho in TRAMOS:
        campos[nombre] = [_entero(bits[i + k * ancho: i + (k + 1) * ancho]) for k in range(cuantos)]
        i += cuantos * ancho

    return m.reparar({"puntos": campos["puntos"],
                      "objeto1": campos["objetos"][0], "objeto2": campos["objetos"][1],
                      "habs": campos["habs"], "pesos": campos["pesos"],
                      "cambios": list(zip(campos["posCambios"], campos["nuevosCambios"])),
                      "ajustes": campos["ajustes"],
                      "predisposicion": campos["predisposicion"],
                      "probBloqueo": campos["bloqueo"][0]})


def bits_al_azar(rng):
    return [rng.randrange(2) for _ in range(N_BITS)]


def costo_bits(bits, n=m.combatesPorEquipo, semilla=0):
    return m.costo(decodificar(bits), n=n, semilla=semilla)


def probabilidades_rango(n_keep):
    # P_n = (n_keep - n + 1) / (1 + 2 + ... + n_keep). Solo depende del orden y
    # no del valor del costo, que en nuestro caso trae ruido de los combates.
    total = n_keep * (n_keep + 1) / 2
    return [(n_keep - n + 1) / total for n in range(1, n_keep + 1)]


def acumuladas(probs):
    suma, acum = 0.0, []
    for p in probs:
        suma += p
        acum.append(suma)
    return acum


def elegir_por_rango(acum, rng):
    # Ruleta: el primer rango cuya probabilidad acumulada supera al número sacado.
    r = rng.random()
    for i, a in enumerate(acum):
        if r < a:
            return i
    return len(acum) - 1


def probabilidades_costo(costos, costo_descartado):
    # Ponderación de costo: a cada costo se le resta el del mejor descartado, que
    # deja todo negativo, y la probabilidad es el valor absoluto normalizado.
    norm = [abs(c - costo_descartado) for c in costos]
    total = sum(norm)

    # Si todos los sobrevivientes cuestan lo mismo no hay nada que ponderar.
    if total <= 1e-12:
        return [1 / len(costos)] * len(costos)
    return [v / total for v in norm]


def elegir_por_torneo(costos, rng, k=2):
    mejor = rng.randrange(len(costos))
    for _ in range(k - 1):
        otro = rng.randrange(len(costos))
        if costos[otro] < costos[mejor]:
            mejor = otro
    return mejor


def cruce_un_punto(p1, p2, rng):
    # El corte nunca cae en los extremos, así los dos hijos llevan algo de cada padre.
    c = rng.randrange(1, N_BITS)
    return p1[:c] + p2[c:], p2[:c] + p1[c:]


def mutar(bits, tasa, rng):
    nuevo, cambios = list(bits), 0
    for i in range(N_BITS):
        if rng.random() < tasa:
            nuevo[i] = 1 - nuevo[i]
            cambios += 1
    return nuevo, cambios


def correr_ag(semilla_rng=0, popsize=30, maxit=20, tasa_sel=0.5, tasa_mut=1 / N_BITS,
              n_elite=1, n_sim=m.combatesPorEquipo, semilla_sim=0, seleccion="rango", verbose=False,
              rotarSemillas=False):
    # Devuelve los mejores bits, su costo y la historia como pares de
    # (evaluaciones acumuladas, mejor costo hasta ahora). Por defecto todas las
    # evaluaciones usan las mismas semillas de combate, así el mismo cromosoma
    # siempre cuesta lo mismo y la curva no se mueve por azar.
    #
    # Con rotarSemillas cada generación pelea combates distintos y toda la
    # población se vuelve a evaluar, la élite incluida. Así nadie sobrevive por
    # haber tenido suerte con unos combates en particular, pero el mejor costo
    # ya no es monótono y lo que se devuelve es el mejor de la última generación.
    rng = random.Random(semilla_rng)
    n_keep = int(popsize * tasa_sel)
    acum = acumuladas(probabilidades_rango(n_keep))

    pob = [bits_al_azar(rng) for _ in range(popsize)]
    costos = [costo_bits(b, n_sim, semilla_sim) for b in pob]
    evals = popsize
    mejor_i = min(range(popsize), key=lambda i: costos[i])
    mejor_bits, mejor_costo = list(pob[mejor_i]), costos[mejor_i]
    historia = [(evals, mejor_costo)]

    for gen in range(maxit):
        orden = sorted(range(len(pob)), key=lambda i: costos[i])
        costos_descartados = [costos[i] for i in orden[n_keep:]]
        pob = [pob[i] for i in orden[:n_keep]]
        costos = [costos[i] for i in orden[:n_keep]]

        if seleccion == "costo":
            acum_costo = acumuladas(probabilidades_costo(costos, costos_descartados[0]))

        def _padre():
            if seleccion == "rango":
                return elegir_por_rango(acum, rng)
            if seleccion == "costo":
                return elegir_por_rango(acum_costo, rng)
            if seleccion == "torneo":
                return elegir_por_torneo(costos, rng)
            raise ValueError("selección desconocida: " + seleccion)

        hijos = []
        while len(hijos) < popsize - n_keep:
            i, j = _padre(), _padre()
            h1, h2 = cruce_un_punto(pob[i], pob[j], rng)
            hijos.append(h1)
            if len(hijos) < popsize - n_keep:
                hijos.append(h2)

        # La élite no se muta y conserva su costo, por eso el mejor nunca empeora.
        sobrevivientes = pob[:n_elite] + [mutar(b, tasa_mut, rng)[0] for b in pob[n_elite:]]
        hijos = [mutar(b, tasa_mut, rng)[0] for b in hijos]
        pob = sobrevivientes + hijos

        if rotarSemillas:
            semillaGen = semilla_sim + (gen + 1) * n_sim
            costos = [costo_bits(b, n_sim, semillaGen) for b in pob]
            evals += len(pob)
        else:
            costos = costos[:n_elite] + [costo_bits(b, n_sim, semilla_sim) for b in pob[n_elite:]]
            evals += len(pob) - n_elite

        i = min(range(len(pob)), key=lambda k: costos[k])
        if rotarSemillas or costos[i] < mejor_costo:
            mejor_bits, mejor_costo = list(pob[i]), costos[i]
        historia.append((evals, mejor_costo))

        if verbose:
            print("gen %2d  evals %4d  mejor C %.4f  (F %.4f)" % (gen + 1, evals, mejor_costo, 1 - mejor_costo))

    return mejor_bits, mejor_costo, historia


def correr_aleatoria(semilla_rng=0, evaluaciones=610, n_sim=m.combatesPorEquipo, semilla_sim=0):
    # Línea base: cromosomas al azar con el mismo presupuesto de evaluaciones.
    rng = random.Random(semilla_rng)
    mejor_bits, mejor_costo, historia = None, float("inf"), []

    for k in range(1, evaluaciones + 1):
        b = bits_al_azar(rng)
        c = costo_bits(b, n_sim, semilla_sim)
        if c < mejor_costo:
            mejor_bits, mejor_costo = b, c
        historia.append((k, mejor_costo))
    return mejor_bits, mejor_costo, historia


if __name__ == "__main__":
    import time
    t = time.time()
    bits, c, hist = correr_ag(semilla_rng=1)
    crom = decodificar(bits)
    r = m.evaluar_jefe(crom)

    print("AG: C = %.4f  F = %.4f  en %.1f s" % (c, 1 - c, time.time() - t))
    print("mejor jefe:", crom["puntos"], m.objetos[crom["objeto1"]]["nombre"], "->", m.objetos[crom["objeto2"]]["nombre"])
    print("victoria promedio del equipo: %.2f" % r["p_victoria"])
