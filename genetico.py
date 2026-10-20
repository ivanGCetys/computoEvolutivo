"""
Algoritmo genético binario para diseñar jefes, y la búsqueda aleatoria con la que
se compara. Sigue la estructura del curso (L02): población -> costo -> selección
natural -> emparejamiento por rango -> cruce -> mutación -> convergencia.

Uso:  python genetico.py
"""
import random
import motor as m

# ---------------------------------------------------------------------------
# 1. Codificación: el cromosoma son 44 bits
# ---------------------------------------------------------------------------
# | tramo        | bits | qué guarda                                    |
# |--------------|------|-----------------------------------------------|
# | 4 atributos  | 4x4  | proporción del presupuesto (HP, ATK, DEF, VEL) |
# | 2 elementos  | 2x2  | elemento de fase 1 y de fase 2 (0..3)          |
# | 4 habilidades| 4x3  | índice de la habilidad (0..7; el 7 se dobla a 0)|
# | 4 pesos      | 4x3  | con cuánta frecuencia usa cada habilidad       |
# Total = 16 + 4 + 12 + 12 = 44 bits.
# Los valores crudos NO tienen que ser válidos: motor.reparar() se encarga de que
# los puntos sumen 1000, de que no haya habilidades repetidas y de normalizar pesos.
TRAMOS = [("puntos", 4, 4), ("elems", 2, 2), ("habs", 4, 3), ("pesos", 4, 3)]
N_BITS = sum(cuantos * ancho for _, cuantos, ancho in TRAMOS)      # 44


def _entero(bits):
    """Convierte una lista de bits a entero, el primer bit es el más significativo."""
    v = 0
    for b in bits:
        v = v * 2 + b
    return v


def decodificar(bits):
    """44 bits -> cromosoma válido (ya reparado)."""
    campos, i = {}, 0
    for nombre, cuantos, ancho in TRAMOS:
        campos[nombre] = [_entero(bits[i + k * ancho: i + (k + 1) * ancho]) for k in range(cuantos)]
        i += cuantos * ancho
    return m.reparar({"puntos": campos["puntos"],
                      "elem1": campos["elems"][0], "elem2": campos["elems"][1],
                      "habs": campos["habs"], "pesos": campos["pesos"]})


def bits_al_azar(rng):
    return [rng.randrange(2) for _ in range(N_BITS)]


def costo_bits(bits, n=30, semilla=0):
    """FUNCIÓN DE COSTO que el AG minimiza: C = 1 - F, con F = peor de los 4 equipos."""
    return m.costo(decodificar(bits), n=n, semilla=semilla)


# ---------------------------------------------------------------------------
# 2. Selección: emparejamiento por ponderación de rango (L02)
# ---------------------------------------------------------------------------
def probabilidades_rango(n_keep):
    """P_n = (n_keep - n + 1) / (1 + 2 + ... + n_keep). El mejor (rango 1) es el
    más probable. No depende del valor del costo, solo del orden."""
    total = n_keep * (n_keep + 1) / 2
    return [(n_keep - n + 1) / total for n in range(1, n_keep + 1)]


def acumuladas(probs):
    suma, acum = 0.0, []
    for p in probs:
        suma += p
        acum.append(suma)
    return acum


def elegir_por_rango(acum, rng):
    """Saca un número al azar en [0,1) y devuelve el primer rango cuya acumulada
    lo supera. Es la ruleta de la diapositiva 24."""
    r = rng.random()
    for i, a in enumerate(acum):
        if r < a:
            return i
    return len(acum) - 1


def probabilidades_costo(costos, costo_descartado):
    """Ponderación de COSTO (L02 diapositiva 25): C_n = c_n - c_(Nkeep+1), que deja
    todos los valores negativos, y P_n = |C_n| / suma de los |C_m|.
    Si todos los sobrevivientes cuestan lo mismo, se reparte parejo."""
    norm = [abs(c - costo_descartado) for c in costos]
    total = sum(norm)
    if total <= 1e-12:
        return [1 / len(costos)] * len(costos)
    return [v / total for v in norm]


def elegir_por_torneo(costos, rng, k=2):
    """Saca k individuos al azar y devuelve el de menor costo. Como el rango, solo
    mira el orden, pero no necesita ordenar toda la población."""
    mejor = rng.randrange(len(costos))
    for _ in range(k - 1):
        otro = rng.randrange(len(costos))
        if costos[otro] < costos[mejor]:
            mejor = otro
    return mejor


# ---------------------------------------------------------------------------
# 3. Cruce de un punto y 4. Mutación
# ---------------------------------------------------------------------------
def cruce_un_punto(p1, p2, rng):
    """Corta a los dos padres en el mismo punto y los intercambia de ahí en adelante.
    El punto va de 1 a 43 para que los dos hijos tengan algo de cada padre."""
    c = rng.randrange(1, N_BITS)
    return p1[:c] + p2[c:], p2[:c] + p1[c:]


def mutar(bits, tasa, rng):
    """Voltea cada bit con probabilidad 'tasa'. Devuelve (bits, cuántos cambiaron)."""
    nuevo, cambios = list(bits), 0
    for i in range(N_BITS):
        if rng.random() < tasa:
            nuevo[i] = 1 - nuevo[i]
            cambios += 1
    return nuevo, cambios


# ---------------------------------------------------------------------------
# 5. El algoritmo genético
# ---------------------------------------------------------------------------
def correr_ag(semilla_rng=0, popsize=30, maxit=20, tasa_sel=0.5, tasa_mut=1 / N_BITS,
              n_elite=1, n_sim=30, semilla_sim=0, seleccion="rango", verbose=False):
    """Devuelve (mejor_bits, mejor_costo, historia).
    historia = lista de (evaluaciones_acumuladas, mejor_costo_hasta_ahora).

    Todas las evaluaciones usan las MISMAS semillas de combate (semilla_sim..+n_sim-1),
    así el costo es el mismo para el mismo cromosoma y la curva no sube por azar."""
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
        # --- Selección natural: ordenar por costo y quedarse con los n_keep mejores
        orden = sorted(range(len(pob)), key=lambda i: costos[i])
        costos_descartados = [costos[i] for i in orden[n_keep:]]
        pob = [pob[i] for i in orden[:n_keep]]
        costos = [costos[i] for i in orden[:n_keep]]

        # --- Emparejamiento + cruce: llenar hasta popsize
        if seleccion == "costo":
            # c_(Nkeep+1) = el mejor de los descartados, el que quedó justo afuera
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

        # --- Mutación: los n_elite mejores no se tocan (elitismo)
        sobrevivientes = pob[:n_elite] + [mutar(b, tasa_mut, rng)[0] for b in pob[n_elite:]]
        hijos = [mutar(b, tasa_mut, rng)[0] for b in hijos]
        pob = sobrevivientes + hijos

        # --- Costo: la élite conserva el suyo (sus bits no cambiaron)
        nuevos = costos[:n_elite] + [costo_bits(b, n_sim, semilla_sim) for b in pob[n_elite:]]
        costos = nuevos
        evals += len(pob) - n_elite

        i = min(range(len(pob)), key=lambda k: costos[k])
        if costos[i] < mejor_costo:
            mejor_bits, mejor_costo = list(pob[i]), costos[i]
        historia.append((evals, mejor_costo))
        if verbose:
            print("  gen %2d  evals %4d  mejor C %.4f  (F %.4f)" % (gen + 1, evals, mejor_costo, 1 - mejor_costo))

    return mejor_bits, mejor_costo, historia


# ---------------------------------------------------------------------------
# 6. Búsqueda aleatoria: la línea base, con el MISMO número de evaluaciones
# ---------------------------------------------------------------------------
def correr_aleatoria(semilla_rng=0, evaluaciones=610, n_sim=30, semilla_sim=0):
    """Genera cromosomas al azar y se queda con el mejor. Mismo presupuesto que el AG."""
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
    bits, c, hist = correr_ag(semilla_rng=1, verbose=True)
    print("AG: C = %.4f  F = %.4f  en %.1f s" % (c, 1 - c, time.time() - t))
    crom = decodificar(bits)
    r = m.evaluar_jefe(crom, n=30, semilla=0)
    print("mejor jefe:", crom["puntos"], m.NOMBRES_ELEM[crom["elem1"]], "->", m.NOMBRES_ELEM[crom["elem2"]])
    print("  p_victoria por equipo:", {k: round(v, 2) for k, v in r["p_victoria_equipos"].items()})
