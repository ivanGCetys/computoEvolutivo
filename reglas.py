# Reglas base del juego: elementos, objetos equipables y las cuentas de daño.
# Aquí no hay estado de combate, solo tablas y fórmulas.

NOMBRES_ELEM = ["fuego", "agua", "viento", "tierra", "planta", "rayo", "luz", "oscuridad"]
N_ELEMENTOS = len(NOMBRES_ELEM)
FUEGO, VIENTO, TIERRA = 0, 2, 3
indiceElem = {nombre: i for i, nombre in enumerate(NOMBRES_ELEM)}

# Los elementos ya no forman un ciclo. Un elemento es solo la etiqueta de un
# ataque y lo único que hace es activar los bonos de los objetos equipados.
# Van en pares de opuestos (fuego y agua, viento y tierra, planta y rayo, luz
# y oscuridad) y por cómo está ordenada la lista el opuesto es el vecino del par.


def elemOpuesto(elem):
    return elem ^ 1


def crearObjetos():
    # Dos objetos por elemento. El amuleto pega más fuerte con su elemento y lo
    # paga con una debilidad grande al opuesto. El talismán es la versión
    # defensiva: menos bono de ataque, resiste al opuesto y cede ante otro.
    lista = []
    for e, nombre in enumerate(NOMBRES_ELEM):
        amuleto = {"nombre": "Amuleto de " + nombre, "elem": e,
                   "bonoAtaque": {e: 0.20},
                   "bonoDefensa": {e: 0.10, elemOpuesto(e): -0.25}}
        talisman = {"nombre": "Talisman de " + nombre, "elem": e,
                    "bonoAtaque": {e: 0.10},
                    "bonoDefensa": {elemOpuesto(e): 0.25, (e + 2) % N_ELEMENTOS: -0.15}}
        lista.append(amuleto)
        lista.append(talisman)

    # Los multiplicadores se dejan ya calculados por elemento porque el combate
    # los consulta en cada golpe.
    for obj in lista:
        obj["multAtk"] = [1.0 + obj["bonoAtaque"].get(e, 0.0) for e in range(N_ELEMENTOS)]
        obj["multDef"] = [1.0 + obj["bonoDefensa"].get(e, 0.0) for e in range(N_ELEMENTOS)]
    return lista


objetos = crearObjetos()
nObjetos = len(objetos)


def describirObjeto(obj):
    partes = []
    for e, bono in obj["bonoAtaque"].items():
        partes.append("%+d%% ataque de %s" % (round(100 * bono), NOMBRES_ELEM[e]))
    for e, bono in obj["bonoDefensa"].items():
        partes.append("%+d%% defensa contra %s" % (round(100 * bono), NOMBRES_ELEM[e]))
    return ", ".join(partes)


# Los ataques físicos varían más y pueden salir críticos. Los mágicos son más
# parejos, no tienen crítico y lo compensan con más poder base.
variacionFisMin, variacionFisMax = 0.80, 1.20
variacionMagMin, variacionMagMax = 0.85, 1.00
multCritico = 1.60
probCriticoBase = 0.10
probCriticoJefe = 0.04

# El esquive solo existe para el que es más rápido que su atacante y crece con
# la diferencia de velocidad, entre 1% y 15%.
esquiveMin, esquiveMax = 0.01, 0.15
esquivePorPunto = 0.005

multBloqueo = 0.5
PODER_BASICO = 0.8

# Mochila compartida del equipo. Cada poción devuelve una fracción del máximo
# de quien la bebe.
pocionesIniciales = {"hpChica": 2, "hpGrande": 1, "spChica": 2, "spGrande": 1}
efectoPocion = {"hpChica": 0.30, "hpGrande": 0.60, "spChica": 0.30, "spGrande": 0.60}
nombrePocion = {"hpChica": "pocion de vida", "hpGrande": "pocion grande de vida",
                "spChica": "pocion de mana", "spGrande": "pocion grande de mana"}


def calcular_dano(atk, poder, mult_elem, defensa, mult_bloqueo=1.0):
    bruto = atk * poder * mult_elem * 100 / (100 + defensa) * mult_bloqueo

    # Sumamos 1e-9 antes de truncar porque un 13.9999999 por error de punto
    # flotante se nos volvía 13.
    return max(1, int(bruto + 1e-9))


def probEsquive(velAtacante, velDefensor):
    dif = velDefensor - velAtacante
    return min(esquiveMax, max(esquiveMin, dif * esquivePorPunto))


def multVariacion(rng, esFisico, minFis=variacionFisMin, probCritico=probCriticoBase):
    if not esFisico:
        return variacionMagMin + (variacionMagMax - variacionMagMin) * rng.random(), False

    if rng.random() < probCritico:
        return multCritico, True
    return minFis + (variacionFisMax - minFis) * rng.random(), False


def danoAtaque(rng, atk, poder, esFisico, elem, objAtacante, defensa, objDefensor,
               velAtacante, velDefensor, bloqueo=1.0, minFis=variacionFisMin,
               probCritico=probCriticoBase):
    # Devuelve el daño y una nota que dice si fue esquive o crítico. El esquive
    # se tira primero porque un golpe esquivado no necesita más cuentas.
    if rng.random() < probEsquive(velAtacante, velDefensor):
        return 0, "esquiva"

    mult, critico = multVariacion(rng, esFisico, minFis, probCritico)
    if elem is not None:
        mult *= objAtacante["multAtk"][elem]
        defensa = defensa * objDefensor["multDef"][elem]

    return calcular_dano(atk, poder, mult, defensa, bloqueo), ("critico" if critico else "")
