# Las animaciones de cada ataque. Una receta recibe la Animacion vacia y el
# contexto del turno (quien ataca, a quien, con que elemento y en que momento
# suelta el golpe) y le agenda sus piezas. Las medidas estan en pixeles de
# las capas, que son la mitad de los de la pantalla.
#
# Los ataques que se usan poco y pegan fuerte tienen su propia receta, con
# la pantalla oscurecida, destellos y sacudidas. Los demas comparten unas
# cuantas recetas por tipo que cambian de color y de forma con el elemento.
import math

import pygame

import motor as m
from grafico.animaciones import (Animacion, anillo, atenuar, azar, blanco, cadencia, disco, estrella, icono,
                                 lineaBrillante, mediaLuna, mezclar, quebrar, roca, suave)

anchoCapa, altoCapa = 640, 250

# Contorno, base, claro y brillo de cada elemento, en el orden de m.NOMBRES_ELEM.
paletas = [
    [(110, 30, 20), (230, 80, 30), (255, 170, 50), (255, 240, 150)],
    [(20, 40, 110), (40, 110, 220), (110, 190, 255), (220, 245, 255)],
    [(30, 90, 80), (90, 200, 170), (170, 240, 220), (240, 255, 250)],
    [(60, 40, 25), (140, 95, 55), (190, 145, 90), (230, 200, 150)],
    [(20, 60, 25), (50, 150, 60), (120, 210, 90), (210, 250, 160)],
    [(90, 70, 10), (240, 200, 40), (255, 240, 120), (255, 255, 230)],
    [(120, 100, 40), (250, 230, 140), (255, 250, 210), (255, 255, 255)],
    [(20, 10, 35), (70, 30, 110), (140, 70, 200), (220, 170, 255)],
]

# Por donde pasa el color de una particula de cada elemento, de recien salida a apagada.
rampas = [
    [(255, 250, 200), (255, 220, 90), (255, 150, 40), (230, 70, 20), (140, 30, 10), (60, 10, 5)],
    [(235, 250, 255), (150, 215, 255), (70, 150, 240), (40, 90, 200), (20, 40, 120)],
    [(245, 255, 250), (180, 245, 225), (100, 210, 180), (50, 140, 120), (20, 70, 60)],
    [(255, 230, 170), (210, 160, 100), (150, 100, 60), (90, 60, 35), (40, 25, 15)],
    [(220, 255, 170), (130, 220, 90), (60, 160, 60), (30, 100, 40), (10, 40, 15)],
    [(255, 255, 240), (255, 245, 140), (245, 205, 50), (160, 120, 20), (70, 50, 5)],
    [(255, 255, 255), (255, 250, 210), (250, 230, 140), (180, 150, 70), (80, 60, 20)],
    [(230, 180, 255), (160, 80, 220), (90, 40, 150), (45, 15, 80), (20, 5, 35)],
]
rampaChispa = [(255, 255, 255), (255, 240, 170), (255, 190, 80), (180, 100, 30), (70, 30, 10)]
rampaPiedra = [(190, 145, 90), (150, 105, 65), (120, 85, 50), (95, 65, 40)]
rampaPolvo = [(205, 185, 155, 210), (185, 165, 140, 160), (165, 150, 130, 100), (150, 140, 125, 45)]
rampaHumo = [(70, 60, 60, 200), (60, 52, 52, 150), (50, 45, 45, 95), (40, 38, 38, 40)]
rampaHoja = [(150, 225, 95), (95, 190, 75), (60, 150, 60), (40, 110, 45)]
rampaPluma = [(255, 255, 255, 255), (245, 245, 235, 230), (235, 230, 210, 170), (225, 215, 190, 80)]
paletaRoca = [(50, 34, 22), (132, 92, 56), (186, 142, 92), (226, 196, 150)]
paletaMeteoro = [(80, 20, 8), (170, 70, 22), (255, 175, 70), (255, 235, 160)]


sonidoDeElemento = ["fuego", "agua", "viento", "tierra", "planta", "rayo", "luz", "oscuridad"]


class Contexto:
    # Lo que una receta necesita saber del turno. sentido es 1 cuando el
    # ataque va hacia la derecha, de un heroe al jefe, y -1 cuando va al reves.
    def __init__(self, nombre, elem, origen, objetivos, t0, sentido, actor=""):
        self.nombre, self.elem = nombre, elem
        self.origen, self.objetivos = origen, objetivos
        self.t0, self.sentido, self.actor = t0, sentido, actor


def conAlfa(color, k, capa):
    # En la capa de luz las cosas se apagan oscureciendose; en las otras, volviendose transparentes.
    if capa == "luz":
        return atenuar(color, k)
    return (color[0], color[1], color[2], int(255 * max(0.0, min(1.0, k))))


def anilloDeChoque(anim, t, x, y, radio, color, duracion=0.35, aplastado=0.45, grueso=2, capa="luz"):
    def dibujar(sup, u):
        anillo(sup, x, y, radio * (1 - (1 - u) ** 2), conAlfa(color, 1 - u, capa), grueso, aplastado)
    anim.trazo(t, duracion, dibujar, capa)


def fogonazo(anim, t, x, y, radio, color, duracion=0.22):
    # Una bola de luz que crece y se apaga.
    def dibujar(sup, u):
        r = radio * (0.4 + 0.6 * u)
        disco(sup, x, y, r, atenuar(color, 0.5 * (1 - u)))
        disco(sup, x, y, r * 0.65, atenuar(mezclar(color, blanco, 0.5), 1 - u))
        disco(sup, x, y, r * 0.3 * (1 - u), blanco)
    anim.trazo(t, duracion, dibujar)


def tajo(anim, t, cx, cy, radio, a0, a1, grosor, color, duracion=0.2):
    # El arco se va pintando de una punta a la otra y deja ver solo un tramo,
    # como el rastro de una hoja que ya paso.
    anim.sonido(t, "tajo", 0.7)
    def dibujar(sup, u):
        s1 = min(1.0, u * 1.8)
        s0 = max(0.0, u * 1.8 - 0.8)
        if s1 - s0 < 0.03:
            return
        brillo = 1.0 if u < 0.6 else 1 - (u - 0.6) / 0.4
        b0, b1 = a0 + (a1 - a0) * s0, a0 + (a1 - a0) * s1
        mediaLuna(sup, cx, cy, radio, b0, b1, grosor, atenuar(color, brillo))
        mediaLuna(sup, cx, cy, radio - 1, b0, b1, max(1.0, grosor * 0.45), atenuar(blanco, brillo))
    anim.trazo(t, duracion, dibujar)


def corte(anim, t, x0, y0, x1, y1, grosor, color, duracion=0.2, curva=0.3):
    # Un tajo de un punto a otro, apenas curvo, para los cortes que cruzan al enemigo.
    largo = math.hypot(x1 - x0, y1 - y0) or 1.0
    flecha = curva * largo / 2
    radio = (largo * largo / 4 + flecha * flecha) / (2 * flecha)
    nx, ny = -(y1 - y0) / largo, (x1 - x0) / largo
    cx, cy = (x0 + x1) / 2 + nx * (radio - flecha), (y0 + y1) / 2 + ny * (radio - flecha)
    a0, a1 = math.atan2(y0 - cy, x0 - cx), math.atan2(y1 - cy, x1 - cx)
    # Por el camino corto, para que no le de la vuelta entera al circulo.
    a1 = a0 + (a1 - a0 + math.pi) % math.tau - math.pi
    tajo(anim, t, cx, cy, radio, a0, a1, grosor, color, duracion)


def relampago(anim, t, x0, y0, x1, y1, color, duracion=0.22, grueso=2, desvio=9, ramas=2):
    anim.sonido(t, "rayo", 0.6)
    estado = {"vez": -1, "puntos": [], "ramas": []}
    tramos = max(4, int(math.hypot(x1 - x0, y1 - y0) / 14))

    def dibujar(sup, u):
        # Cambia de forma cada veinteavo de segundo, que es lo que lo hace temblar.
        vez = int(u * duracion / 0.05)
        if vez != estado["vez"]:
            estado["vez"] = vez
            estado["puntos"] = quebrar(x0, y0, x1, y1, desvio, tramos)
            estado["ramas"] = []
            for _ in range(ramas):
                px, py = azar.choice(estado["puntos"][1:-1])
                a, largo = azar.uniform(0, math.tau), azar.uniform(12, 30)
                estado["ramas"].append(quebrar(px, py, px + largo * math.cos(a), py + abs(largo * math.sin(a)), 4, 3))
        brillo = 1.0 if u < 0.5 else 2 * (1 - u)
        lineaBrillante(sup, estado["puntos"], color, grueso, brillo)
        for rama in estado["ramas"]:
            lineaBrillante(sup, rama, color, 1, brillo * 0.8)
    anim.trazo(t, duracion, dibujar)


def tira(sup, x0, y0, x1, y1, ancho, color):
    largo = math.hypot(x1 - x0, y1 - y0) or 1.0
    nx, ny = -(y1 - y0) / largo * ancho / 2, (x1 - x0) / largo * ancho / 2
    pygame.draw.polygon(sup, color, [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)])


def haz(anim, t, x0, y0, x1, y1, ancho, color, duracion):
    anim.sonido(t, "haz", 0.8)
    def dibujar(sup, u):
        forma = min(1.0, u / 0.1, (1 - u) / 0.25) * (0.88 + 0.12 * math.sin(u * 70))
        if forma <= 0.02:
            return
        tira(sup, x0, y0, x1, y1, ancho * forma + 8, atenuar(color, 0.35))
        tira(sup, x0, y0, x1, y1, ancho * forma + 3, color)
        tira(sup, x0, y0, x1, y1, max(1.0, ancho * forma * 0.55), blanco)
        disco(sup, x0, y0, ancho * forma * 0.9, mezclar(color, blanco, 0.6))
    anim.trazo(t, duracion, dibujar)


def chispazo(anim, t, x, y, fuerza=1.0, color=blanco):
    # El golpe de un arma: una estrella de impacto y chispas.
    chispas = anim.rayas(rampaChispa, freno=4.0, largo=0.035)
    anim.en(t, lambda: chispas.rafaga(x, y, 12 * fuerza, 230, 0.28, 1))

    def dibujar(sup, u):
        estrella(sup, x, y, 14 * fuerza * (0.5 + 0.5 * u), atenuar(color, 1 - u * u), 6, 0.3, 0.4)
        estrella(sup, x, y, 7 * fuerza * (1 - u), blanco, 4, 0.3)
    anim.trazo(t, 0.14, dibujar)


def polvareda(anim, t, x, y, fuerza=1.0):
    anim.sonido(t, "golpeSeco", min(1.0, 0.4 + 0.3 * fuerza))
    polvo = anim.particulas(rampaPolvo, capa="frente", gravedad=-25, freno=3.0)
    anim.en(t, lambda: polvo.rafaga(x, y, 14 * fuerza, 85, 0.6, 4, -math.pi / 2, math.pi * 1.1, 3))
    anilloDeChoque(anim, t, x, y, 26 * fuerza, (205, 185, 155), 0.35, 0.35, 2, "frente")


def estallido(anim, t, x, y, elem, fuerza=1.0):
    # Lo que se ve donde pega un ataque, segun su elemento.
    if elem is None:
        chispazo(anim, t, x, y, fuerza)
        return
    anim.sonido(t, sonidoDeElemento[elem], min(1.0, 0.5 + 0.25 * fuerza))

    rampa, color = rampas[elem], paletas[elem][2]
    if elem == 0:
        llamas = anim.particulas(rampa, gravedad=-70, freno=1.6)
        brasas = anim.particulas(rampa, gravedad=130, freno=0.6)
        anim.en(t, lambda: (llamas.rafaga(x, y, 30 * fuerza, 110, 0.55, 3, dispersion=3),
                            brasas.rafaga(x, y, 12 * fuerza, 170, 0.7, 1, -math.pi / 2, math.pi)))
        fogonazo(anim, t, x, y, 16 * fuerza, (255, 150, 40))
    elif elem == 1:
        gotas = anim.particulas(rampa, gravedad=380)
        anim.en(t, lambda: gotas.rafaga(x, y, 34 * fuerza, 175, 0.7, 2, -math.pi / 2, math.pi * 0.95, 2))
        anilloDeChoque(anim, t, x, y + 6, 24 * fuerza, color, 0.4, 0.35)
        fogonazo(anim, t, x, y, 10 * fuerza, (90, 170, 255), 0.18)
    elif elem == 2:
        rachas = anim.rayas(rampa, freno=2.5, largo=0.05)
        anim.en(t, lambda: rachas.rafaga(x, y, 22 * fuerza, 190, 0.4, 1))
        for k in range(3):
            giro = k * math.tau / 3
            tajo(anim, t + 0.04 * k, x, y, (10 + 6 * k) * fuerza, giro, giro + math.pi * 1.2, 3, color, 0.24)
    elif elem == 3:
        piedras = anim.particulas(rampaPiedra, capa="frente", gravedad=430, encoge=False)
        anim.en(t, lambda: piedras.rafaga(x, y, 16 * fuerza, 170, 0.7, 3, -math.pi / 2, math.pi, 2))
        polvareda(anim, t, x, y + 4, fuerza)
        chispazo(anim, t, x, y, 0.8 * fuerza, (255, 220, 160))
    elif elem == 4:
        hojas = anim.particulas(rampaHoja, capa="frente", gravedad=70, freno=2.6, encoge=False)
        brillo = anim.particulas(rampa, freno=2.0)
        anim.en(t, lambda: (hojas.rafaga(x, y, 18 * fuerza, 130, 0.9, 3), brillo.rafaga(x, y, 14 * fuerza, 90, 0.45, 2)))
        anilloDeChoque(anim, t, x, y, 20 * fuerza, color, 0.3, 1.0)
    elif elem == 5:
        chispas = anim.rayas(rampa, freno=4.0, largo=0.04)
        anim.en(t, lambda: chispas.rafaga(x, y, 28 * fuerza, 260, 0.3, 1))
        for k in range(3):
            a = azar.uniform(0, math.tau)
            relampago(anim, t + 0.03 * k, x, y, x + 26 * fuerza * math.cos(a), y + 26 * fuerza * math.sin(a),
                      paletas[5][1], 0.14, 1, 5, 0)
        fogonazo(anim, t, x, y, 12 * fuerza, (255, 240, 130), 0.15)
    elif elem == 6:
        motas = anim.particulas(rampa, gravedad=-75, freno=1.2)
        anim.en(t, lambda: motas.rafaga(x, y, 20 * fuerza, 70, 0.8, 2, dispersion=6))

        def cruz(sup, u):
            tam = 26 * fuerza * math.sin(math.pi * u)
            estrella(sup, x, y, tam, atenuar(paletas[6][1], 0.8), 4, 0.16, u)
            estrella(sup, x, y, tam * 0.6, blanco, 4, 0.2, u)
        anim.trazo(t, 0.32, cruz)
        anilloDeChoque(anim, t, x, y, 22 * fuerza, paletas[6][2], 0.35, 1.0)
    else:
        motas = anim.particulas(rampa, freno=2.2)
        anim.en(t, lambda: motas.rafaga(x, y, 26 * fuerza, 140, 0.5, 2))

        def orbe(sup, u):
            r = 14 * fuerza * math.sin(math.pi * u)
            disco(sup, x, y, r + 2, paletas[7][2] + (255,))
            disco(sup, x, y, r, (12, 4, 22, 255))
        anim.trazo(t, 0.3, orbe, "frente")
        anilloDeChoque(anim, t + 0.1, x, y, 24 * fuerza, paletas[7][2], 0.3, 1.0)


def explosion(anim, t, x, y, radio):
    # Una explosion de fuego grande: bola de luz, llamas, brasas, humo y dos ondas.
    k = radio / 40
    anim.sonido(t, "explosion", min(1.0, 0.45 + radio / 80))
    llamas = anim.particulas(rampas[0], gravedad=-60, freno=1.8)
    brasas = anim.rayas(rampas[0], gravedad=170, freno=0.4, largo=0.03)
    humo = anim.particulas(rampaHumo, capa="frente", gravedad=-35, freno=1.6)
    anim.en(t, lambda: (llamas.rafaga(x, y, 40 + 70 * k, 3.4 * radio, 0.75, 4, dispersion=radio * 0.25),
                        llamas.rafaga(x, y, 20 + 30 * k, 1.5 * radio, 0.9, 3, -math.pi / 2, math.pi, radio * 0.3),
                        brasas.rafaga(x, y, 14 + 26 * k, 6 * radio, 0.9, 1, -math.pi / 2, math.pi * 1.3),
                        humo.rafaga(x, y - 4, 8 + 12 * k, 1.3 * radio, 1.0, 4, -math.pi / 2, math.pi, radio * 0.2)))
    fogonazo(anim, t, x, y, radio * 1.1, (255, 160, 50), 0.32)
    anilloDeChoque(anim, t, x, y, radio * 1.5, (255, 200, 110), 0.4, 0.4, 3)
    anilloDeChoque(anim, t + 0.07, x, y, radio * 1.1, (255, 120, 40), 0.4, 0.4, 2)


def meteoro(anim, t, x0, y0, x1, y1, duracion, radio, alLlegar=None, curva=1.6):
    anim.sonido(t, "meteoro", min(1.0, 0.4 + radio / 25))
    fuego = anim.particulas(rampas[0], gravedad=-20, freno=1.0)
    ritmo = cadencia(110 + 14 * radio)

    def lugar(u):
        s = u ** curva
        return x0 + (x1 - x0) * s, y0 + (y1 - y0) * s

    def soltarEstela(u, dt):
        x, y = lugar(u)
        for _ in range(ritmo(dt)):
            fuego.emitir(x + azar.uniform(-radio, radio) * 0.6, y + azar.uniform(-radio, radio) * 0.6,
                         azar.uniform(-18, 18), azar.uniform(-18, 18), azar.uniform(0.25, 0.55), azar.choice((2, 3, 4)))
    anim.durante(t, t + duracion, soltarEstela)

    def cuerpo(sup, u):
        x, y = lugar(u)
        roca(sup, x, y, radio, paletaMeteoro, u * 6)
    anim.trazo(t, duracion, cuerpo, "frente")

    def halo(sup, u):
        x, y = lugar(u)
        disco(sup, x, y, radio * 2.0, (80, 26, 6))
        disco(sup, x, y, radio * 1.4, (110, 45, 10))
    anim.trazo(t, duracion, halo)
    if alLlegar is not None:
        anim.en(t + duracion, alLlegar)


def pico(anim, t, x, y, alto, ancho, duracion=0.6):
    # Una punta de roca que sale del piso, aguanta un momento y se hunde.
    def dibujar(sup, u):
        h = alto * min(1.0, u / 0.12) * (1.0 if u < 0.72 else (1 - u) / 0.28)
        if h < 2:
            return
        cuerpo = [(x - ancho / 2, y), (x - ancho * 0.12, y - h), (x + ancho * 0.16, y - h * 0.78), (x + ancho / 2, y)]
        pygame.draw.polygon(sup, paletaRoca[1], cuerpo)
        pygame.draw.polygon(sup, paletaRoca[2], [(x - ancho / 2, y), (x - ancho * 0.12, y - h), (x - ancho * 0.05, y)])
        pygame.draw.polygon(sup, paletaRoca[0], cuerpo, 1)
    anim.trazo(t, duracion, dibujar, "frente")


def centroDe(objetivos):
    n = len(objetivos)
    return sum(o.x for o in objetivos) / n, sum(o.y for o in objetivos) / n, sum(o.piso for o in objetivos) / n


def cataclismo(anim, c):
    # El jefe avienta una bola de fuego al cielo, el cielo se pone rojo y cae
    # una lluvia de meteoros que termina con uno enorme.
    t0, o = c.t0, c.origen
    cx, _, piso = centroDe(c.objetivos)
    blancos = [(d.x + azar.uniform(-8, 8), d.piso - 3) for d in c.objetivos]
    blancos += [(cx + azar.uniform(-90, 110), piso + azar.uniform(-45, 45)) for _ in range(3)]
    azar.shuffle(blancos)
    tLluvia = t0 + 0.8
    tGrande = tLluvia + 0.13 * len(blancos) + 0.1
    fin = tGrande + 1.45

    anim.oscurecer(t0, fin, 150)
    meteoro(anim, t0, o.x - 30, o.y - 35, o.x - 95, -30, 0.45, 6, None, 0.75)
    fogonazo(anim, t0, o.x - 30, o.y - 35, 18, (255, 150, 40))
    anim.tinte(t0 + 0.4, fin - 0.2, (190, 30, 5), 55, 0.35, 0.5)
    anim.sacudir(t0 + 0.5, 2, 0.5)

    for k, (x, y) in enumerate(blancos):
        t = tLluvia + 0.13 * k

        meteoro(anim, t, x + 150 + azar.uniform(-20, 20), -25, x, y, 0.36, 6)
        explosion(anim, t + 0.36, x, y, 22)
        anim.sacudir(t + 0.36, 4, 0.2)
    meteoro(anim, tGrande, cx + 250, -60, cx, piso - 4, 0.5, 20)
    llegada = tGrande + 0.5
    anim.destello(llegada, blanco, 0.22, 235)
    anim.sacudir(llegada, 14, 0.8)
    explosion(anim, llegada, cx, piso - 6, 80)
    anilloDeChoque(anim, llegada + 0.12, cx, piso, 230, (255, 170, 80), 0.6, 0.4, 3)
    for d in c.objetivos:
        estallido(anim, llegada + 0.08, d.x, d.y, 0, 1.8)
    anim.impacto = llegada
    anim.alargar(fin)


def rayoFinal(anim, c):
    # Junta electricidad en las manos y suelta un rayo que cruza la pantalla.
    t0, o, d = c.t0, c.origen, c.objetivos[0]
    bx, by = o.x - 48, o.y - 4
    color = paletas[5][1]
    tHaz = t0 + 0.42
    fin = tHaz + 1.25
    anim.oscurecer(t0 - 0.05, fin, 165)

    chispas = anim.rayas(rampas[5], freno=1.0, largo=0.04)
    ritmo = cadencia(130)

    def juntar(u, dt):
        for _ in range(ritmo(dt)):
            a, r = azar.uniform(0, math.tau), azar.uniform(26, 48)
            chispas.emitir(bx + r * math.cos(a), by + r * math.sin(a), -r * math.cos(a) / 0.22, -r * math.sin(a) / 0.22, 0.22, 1)
    anim.durante(t0, tHaz, juntar)

    def bola(sup, u):
        disco(sup, bx, by, 4 + 10 * u, atenuar(color, 0.7))
        estrella(sup, bx, by, 7 + 16 * u, blanco, 4, 0.2, u * 4)
    anim.trazo(t0, 0.42, bola)

    # El haz sigue de largo hasta salirse de la pantalla.
    largo = math.hypot(d.x - bx, d.y - by) or 1.0
    ex, ey = bx + (d.x - bx) / largo * 720, by + (d.y - by) / largo * 720
    haz(anim, tHaz, bx, by, ex, ey, 22, color, 0.8)
    for k in range(7):
        relampago(anim, tHaz + 0.1 * k, bx, by, d.x + azar.uniform(-30, 10), d.y + azar.uniform(-26, 26), color, 0.14, 1, 14, 1)

    sueltas = anim.rayas(rampas[5], gravedad=120, freno=1.5, largo=0.04)
    ritmoSueltas = cadencia(160)

    def chisporrotear(u, dt):
        for _ in range(ritmoSueltas(dt)):
            s = azar.random()
            sueltas.emitir(bx + (d.x - bx) * s, by + (d.y - by) * s, azar.uniform(-90, 90), azar.uniform(-130, 70), 0.35, 1)
    anim.durante(tHaz, tHaz + 0.7, chisporrotear)

    anim.destello(tHaz, blanco, 0.16, 225)
    anim.destello(tHaz + 0.26, (255, 245, 170), 0.12, 130)
    anim.destello(tHaz + 0.5, (255, 245, 170), 0.12, 110)
    anim.sacudir(tHaz, 9, 0.85)
    estallido(anim, tHaz + 0.06, d.x, d.y, 5, 2.2)
    estallido(anim, tHaz + 0.4, d.x, d.y, 5, 1.6)
    anilloDeChoque(anim, tHaz + 0.06, d.x, d.y, 60, paletas[5][2], 0.4, 1.0, 3)
    anim.impacto = tHaz + 0.1
    anim.alargar(fin)


def devastacion(anim, c):
    # Golpea el piso y la tierra revienta en linea hasta cada heroe.
    t0, o = c.t0, c.origen
    px, py = o.x - 38, o.piso
    pasos = 6
    fin = t0 + 1.5
    anim.oscurecer(t0, fin, 95)
    anim.destello(t0, blanco, 0.16, 160)
    anim.sacudir(t0, 12, 1.0)
    chispazo(anim, t0, px, py - 4, 2.4, (255, 220, 160))
    anilloDeChoque(anim, t0, px, py, 150, (255, 230, 190), 0.5, 0.4, 3)
    anilloDeChoque(anim, t0 + 0.08, px, py, 110, (205, 185, 155), 0.5, 0.4, 2, "frente")
    polvareda(anim, t0, px, py, 2.2)

    piedras = anim.particulas(rampaPiedra, capa="frente", gravedad=430, encoge=False)
    for d in c.objetivos:
        for k in range(1, pasos + 1):
            s = k / pasos
            x, y = px + (d.x - px) * s, py + (d.piso - py) * s
            t = t0 + 0.085 * k
            ultimo = k == pasos
            pico(anim, t, x, y, 44 if ultimo else 12 + 4 * k, 26 if ultimo else 11 + 2 * k, 0.75 if ultimo else 0.5)
            anim.en(t, lambda x=x, y=y: piedras.rafaga(x, y - 3, 5, 120, 0.6, 2, -math.pi / 2, math.pi * 0.8))
        estallido(anim, t0 + 0.085 * pasos, d.x, d.piso - 8, 3, 1.5)
    anim.impacto = t0 + 0.085 * pasos + 0.03
    anim.alargar(fin)


def espadaEspectral(sup, x, punta, largo, ancho, capa, brillo=1.0):
    # Una hoja enorme con la punta hacia abajo.
    arriba = punta - largo
    hoja = [(x, punta), (x - ancho / 2, punta - ancho * 1.3), (x - ancho / 2, arriba), (x + ancho / 2, arriba),
            (x + ancho / 2, punta - ancho * 1.3)]
    if capa == "luz":
        contorno = [(px + (3 if px > x else -3 if px < x else 0), py) for px, py in hoja]
        pygame.draw.polygon(sup, atenuar((150, 70, 230), 0.8 * brillo), contorno, 2)
        return
    alfa = int(255 * brillo)
    pygame.draw.polygon(sup, (196, 180, 236, alfa), hoja)
    pygame.draw.polygon(sup, (236, 228, 255, alfa), [(x, punta), (x - ancho / 2, punta - ancho * 1.3), (x - ancho / 2, arriba), (x, arriba)])
    pygame.draw.polygon(sup, (60, 30, 100, alfa), hoja, 1)
    pygame.draw.line(sup, (150, 130, 200, alfa), (x, punta - ancho), (x, arriba), 1)
    guarda = (int(x - ancho * 1.5), int(arriba - 6), int(ancho * 3), 6)
    pygame.draw.rect(sup, (230, 190, 90, alfa), guarda)
    pygame.draw.rect(sup, (90, 60, 20, alfa), guarda, 1)
    mango = (int(x - 3), int(arriba - 26), 6, 20)
    pygame.draw.rect(sup, (110, 70, 160, alfa), mango)
    pygame.draw.rect(sup, (60, 30, 100, alfa), mango, 1)
    disco(sup, x, arriba - 29, 5, (230, 190, 90, alfa))


def aplastamiento(anim, c):
    # Una espada gigante cae del cielo sobre un solo heroe.
    t0, d = c.t0, c.objetivos[0]
    tCae = t0 + 0.5
    llegada = tCae + 0.1
    fin = llegada + 1.15
    largo, ancho = min(125.0, d.piso - 14), 16
    anim.oscurecer(t0, fin, 150)

    def sombra(sup, u):
        disco(sup, d.x, d.piso, 8 + 26 * u, (10, 0, 20, int(150 * u)), 0.32)
    anim.trazo(t0, 0.6, sombra, "atras")

    def aviso(sup, u):
        estrella(sup, d.x, 6, 10 * math.sin(math.pi * u), (200, 150, 255), 4, 0.2, u * 3)
    anim.trazo(t0 + 0.1, 0.4, aviso)

    def punta(u):
        # Cae, se queda clavada y al final se desvanece.
        if u < 0.08:
            return -20 + (d.piso + 20) * (u / 0.08) ** 2, 1.0
        return d.piso, 1.0 if u < 0.6 else max(0.0, (1 - u) / 0.4)

    for capa in ("frente", "luz"):
        def dibujar(sup, u, capa=capa):
            y, brillo = punta(u)
            if brillo > 0.02:
                espadaEspectral(sup, d.x, y, largo, ancho, capa, brillo)
        anim.trazo(tCae, 1.25, dibujar, capa)

    anim.destello(llegada, blanco, 0.22, 215)
    anim.sacudir(llegada, 13, 0.7)
    estallido(anim, llegada, d.x, d.piso - 4, 3, 2.0)
    chispazo(anim, llegada, d.x, d.piso - 6, 2.6, (220, 170, 255))
    anilloDeChoque(anim, llegada, d.x, d.piso, 90, (220, 170, 255), 0.45, 0.4, 3)
    anilloDeChoque(anim, llegada + 0.1, d.x, d.piso, 60, (150, 70, 230), 0.45, 0.4, 2)
    motas = anim.particulas(rampas[7], gravedad=-50, freno=1.0)
    ritmo = cadencia(70)

    def deshacer(u, dt):
        for _ in range(ritmo(dt)):
            motas.emitir(d.x + azar.uniform(-ancho, ancho) * 0.6, d.piso - azar.uniform(0, largo * 0.8),
                         azar.uniform(-25, 25), azar.uniform(-40, 0), 0.6, 2)
    anim.durante(llegada + 0.55, llegada + 1.1, deshacer)
    anim.impacto = llegada
    anim.alargar(fin)


def infierno(anim, c):
    # Un circulo de fuego bajo el jefe del que sale una columna de llamas.
    t0, b = c.t0, c.objetivos[0]
    tColumna = t0 + 0.35
    fin = tColumna + 1.65
    anim.oscurecer(t0, fin, 155)
    llamas = anim.particulas(rampas[0], gravedad=-170, freno=0.8)
    brasas = anim.particulas(rampas[0], gravedad=-30, freno=0.4)

    def circulo(sup, u):
        r = 64 * min(1.0, u * 4) * (1.0 if u < 0.85 else (1 - u) / 0.15)
        parpadeo = 0.75 + 0.25 * math.sin(u * 90)
        anillo(sup, b.x, b.piso, r, atenuar((255, 150, 40), parpadeo), 2, 0.3)
        anillo(sup, b.x, b.piso, r * 0.62, atenuar((255, 220, 110), parpadeo), 1, 0.3)
    anim.trazo(t0, 1.7, circulo)

    ritmo, ritmoBrasas = cadencia(430), cadencia(60)

    def columna(u, dt):
        ancho = 52 * min(1.0, u * 5) * (1.0 if u < 0.85 else (1 - u) / 0.15)
        for _ in range(ritmo(dt)):
            llamas.emitir(b.x + azar.uniform(-ancho, ancho), b.piso - azar.uniform(0, 6), azar.uniform(-14, 14),
                          -azar.uniform(120, 310), azar.uniform(0.35, 0.7), azar.choice((3, 4, 5)))
        for _ in range(ritmoBrasas(dt)):
            brasas.emitir(b.x + azar.uniform(-70, 70), b.piso - azar.uniform(0, 110), azar.uniform(-40, 40),
                          -azar.uniform(20, 90), 0.9, 1)
    anim.durante(tColumna, tColumna + 1.1, columna)

    def pilar(sup, u):
        # Tres lenguas de fuego, una dentro de otra, con los bordes ondulando hacia arriba.
        ancho = 34 * min(1.0, u * 6, (1 - u) * 5)
        if ancho < 2:
            return
        fase = u * 1.1 * 26
        for factor, tono, desfase in ((1.0, (150, 55, 10), 0.0), (0.66, (240, 140, 40), 1.3), (0.3, (255, 235, 170), 2.1)):
            izquierda, derecha = [], []
            for y in range(int(b.piso), -8, -6):
                altura = (b.piso - y) / b.piso
                medio = ancho * factor * (1 - 0.45 * altura) * (0.8 + 0.2 * math.sin(y * 0.16 + fase + desfase))
                corrido = 5 * math.sin(y * 0.07 - fase * 0.6 + desfase) * altura
                izquierda.append((b.x + corrido - medio, y))
                derecha.append((b.x + corrido + medio, y))
            pygame.draw.polygon(sup, tono, izquierda + derecha[::-1])
    anim.trazo(tColumna, 1.1, pilar)

    anim.destello(tColumna, (255, 180, 70), 0.2, 120)
    anim.sacudir(tColumna, 5, 1.1)
    anim.tinte(tColumna, tColumna + 1.2, (230, 70, 10), 45, 0.15, 0.3)
    explosion(anim, tColumna + 1.1, b.x, b.piso - 30, 60)
    anim.destello(tColumna + 1.1, (255, 220, 150), 0.25, 150)
    anim.impacto = tColumna + 0.15
    anim.alargar(fin)


def diluvio(anim, c):
    # Llueve sobre toda la arena y un geiser revienta bajo el jefe.
    t0, b = c.t0, c.objetivos[0]
    tGeiser = t0 + 0.6
    fin = tGeiser + 1.5
    anim.oscurecer(t0, fin, 150)
    anim.tinte(t0, fin - 0.2, (20, 60, 160), 55, 0.3, 0.4)
    lluvia = anim.rayas([(190, 225, 255), (120, 180, 250), (70, 130, 230)], largo=0.035)
    ritmoLluvia = cadencia(240)

    def llover(u, dt):
        for _ in range(ritmoLluvia(dt)):
            lluvia.emitir(azar.uniform(0, anchoCapa + 80), -5, -110, azar.uniform(420, 520), 0.6, 1)
    anim.durante(t0, fin - 0.5, llover)

    agua = anim.particulas(rampas[1], gravedad=560)
    espuma = anim.particulas([(255, 255, 255), (220, 240, 255), (150, 200, 250), (80, 140, 230)], gravedad=420)
    ritmo, ritmoEspuma = cadencia(400), cadencia(110)

    def geiser(u, dt):
        fuerza = min(1.0, u * 6) * (1.0 if u < 0.8 else (1 - u) / 0.2)
        for _ in range(ritmo(dt)):
            agua.emitir(b.x + azar.uniform(-26, 26), b.piso, azar.uniform(-50, 50), -azar.uniform(260, 440) * fuerza,
                        azar.uniform(0.6, 0.95), azar.choice((3, 4)))
        for _ in range(ritmoEspuma(dt)):
            espuma.emitir(b.x + azar.uniform(-34, 34), b.piso - azar.uniform(60, 150) * fuerza, azar.uniform(-120, 120),
                          -azar.uniform(40, 160), 0.6, 2)
    anim.durante(tGeiser, tGeiser + 0.9, geiser)

    def columna(sup, u):
        forma = min(1.0, u * 6, (1 - u) * 4)
        alto = 165 * forma
        ancho = 24 + 5 * math.sin(u * 50)
        if alto > 4:
            pygame.draw.polygon(sup, (60, 130, 235, 150), [(b.x - ancho, b.piso), (b.x - ancho * 1.5, b.piso - alto),
                                                           (b.x + ancho * 1.5, b.piso - alto), (b.x + ancho, b.piso)])
            pygame.draw.polygon(sup, (160, 215, 255, 170), [(b.x - ancho * 0.4, b.piso), (b.x - ancho * 0.7, b.piso - alto),
                                                            (b.x + ancho * 0.3, b.piso - alto), (b.x + ancho * 0.2, b.piso)])
    anim.trazo(tGeiser, 0.9, columna, "frente")

    for k in range(4):
        anilloDeChoque(anim, tGeiser + 0.2 * k, b.x, b.piso, 70 + 10 * k, paletas[1][2], 0.45, 0.3, 2)
    anim.destello(tGeiser, (150, 200, 255), 0.2, 170)
    anim.sacudir(tGeiser, 6, 0.9)
    estallido(anim, tGeiser + 0.9, b.x, b.piso - 30, 1, 2.4)
    anim.impacto = tGeiser + 0.15
    anim.alargar(fin)


def tornado(anim, t, x, piso, alto, duracion, paleta, anchoBase=10, anchoCima=58):
    niveles = 16

    def dibujar(sup, u):
        forma = min(1.0, u * 5, (1 - u) * 5)
        giro = u * duracion * 14
        for k in range(niveles):
            s = k / (niveles - 1)
            y = piso - alto * s * forma
            ancho = (anchoBase + (anchoCima - anchoBase) * s) * forma
            cx = x + math.sin(giro * 0.5 + s * 5) * 12 * s
            color = paleta[1 + (k + int(giro)) % 3]
            rect = (int(cx - ancho), int(y - ancho * 0.22), int(ancho * 2), max(3, int(ancho * 0.44)))
            if rect[2] > 5:
                inicio = giro + k * 0.9
                pygame.draw.arc(sup, color, rect, inicio, inicio + math.pi * 1.25, 2)
                pygame.draw.arc(sup, atenuar(color, 0.5), rect, inicio + math.pi * 1.25, inicio + math.tau, 1)
    anim.trazo(t, duracion, dibujar)


def huracan(anim, c):
    # Un tornado envuelve al jefe mientras el viento cruza toda la arena.
    t0, b = c.t0, c.objetivos[0]
    tGiro = t0 + 0.3
    fin = tGiro + 1.65
    anim.oscurecer(t0, fin, 140)
    anim.tinte(t0, fin - 0.2, (40, 150, 120), 40, 0.3, 0.4)

    rachas = anim.rayas([(230, 255, 245), (150, 230, 205), (80, 170, 150)], largo=0.06)
    ritmoRachas = cadencia(90)

    def soplar(u, dt):
        for _ in range(ritmoRachas(dt)):
            rachas.emitir(-10, azar.uniform(10, altoCapa - 20), azar.uniform(520, 760), azar.uniform(-30, 30), 1.0, 1)
    anim.durante(t0, fin - 0.6, soplar)

    tornado(anim, tGiro, b.x, b.piso, 175, 1.35, paletas[2])
    hojas = anim.particulas(rampaHoja, capa="frente", encoge=False)
    polvo = anim.particulas(rampaPolvo, capa="frente", gravedad=-200, freno=1.0)
    ritmoPolvo = cadencia(70)
    restos = [(azar.uniform(0, math.tau), azar.uniform(0.1, 1.0), azar.uniform(5, 9)) for _ in range(26)]

    def girarRestos(sup, u):
        forma = min(1.0, u * 5, (1 - u) * 5)
        for fase, s, velocidad in restos:
            a = fase + u * 1.35 * velocidad
            radio = (14 + 52 * s) * forma
            if math.sin(a) > -0.3:
                x, y = b.x + radio * math.cos(a), b.piso - 170 * s * forma + 4 * math.sin(a)
                sup.fill(rampaHoja[int(fase * 7) % 4], (int(x), int(y), 3, 2))
    anim.trazo(tGiro, 1.35, girarRestos, "frente")

    def levantar(u, dt):
        for _ in range(ritmoPolvo(dt)):
            polvo.emitir(b.x + azar.uniform(-30, 30), b.piso, azar.uniform(-60, 60), -azar.uniform(20, 80), 0.6, 4)
    anim.durante(tGiro, tGiro + 1.2, levantar)

    anim.sacudir(tGiro, 4, 1.3)
    anim.destello(tGiro + 1.3, (200, 255, 240), 0.2, 150)
    estallido(anim, tGiro + 1.3, b.x, b.y, 2, 2.4)
    anim.en(tGiro + 1.3, lambda: hojas.rafaga(b.x, b.y, 30, 200, 0.9, 3))
    anim.impacto = tGiro + 0.3
    anim.alargar(fin)


def grieta(anim, t, x0, y0, x1, y1, duracion, permanencia):
    puntos = quebrar(x0, y0, x1, y1, 6, max(4, int(math.hypot(x1 - x0, y1 - y0) / 16)))
    total = duracion + permanencia

    def visibles(u):
        avance = min(1.0, u * total / duracion)
        n = max(2, int(avance * len(puntos)))
        return puntos[:n]

    def oscura(sup, u):
        alfa = 255 if u < 0.8 else int(255 * (1 - u) / 0.2)
        pygame.draw.lines(sup, (24, 14, 10, alfa), False, visibles(u), 3)
    anim.trazo(t, total, oscura, "atras")

    def brasa(sup, u):
        brillo = 1.0 if u < 0.5 else max(0.0, (1 - u) * 2)
        pygame.draw.lines(sup, atenuar((255, 140, 50), brillo), False, visibles(u), 1)
    anim.trazo(t, total, brasa)


def sismo(anim, c):
    # Una grieta corre por el piso hasta el jefe y bajo el revientan puntas de roca.
    t0, o, b = c.t0, c.origen, c.objetivos[0]
    tPicos = t0 + 0.45
    fin = tPicos + 1.3
    anim.oscurecer(t0, fin, 130)
    anim.sacudir(t0, 4, 0.45)
    anim.sacudir(tPicos, 11, 1.0)
    grieta(anim, t0, o.x + 14, o.piso, b.x - 40, b.piso, 0.42, 1.1)
    grieta(anim, t0 + 0.1, o.x + 14, o.piso + 8, b.x + 10, b.piso + 10, 0.4, 1.0)

    piedras = anim.particulas(rampaPiedra, capa="frente", gravedad=420, encoge=False)
    for k, (dx, alto, ancho) in enumerate(((-46, 46, 26), (34, 58, 30), (-12, 84, 38), (58, 40, 22), (-70, 34, 20), (12, 62, 28))):
        t = tPicos + 0.09 * k
        pico(anim, t, b.x + dx, b.piso + azar.uniform(-4, 8), alto, ancho, 0.95)
        polvareda(anim, t, b.x + dx, b.piso, 1.2)
        anim.en(t, lambda dx=dx: piedras.rafaga(b.x + dx, b.piso - 10, 9, 230, 0.9, 3, -math.pi / 2, math.pi * 0.7))
    anim.destello(tPicos, (255, 230, 190), 0.18, 150)
    estallido(anim, tPicos + 0.2, b.x, b.piso - 20, 3, 2.2)
    anim.impacto = tPicos + 0.15
    anim.alargar(fin)


def enredadera(anim, t, x, piso, alto, lado, duracion, conFlor=True):
    # Un tallo que crece ondulando, echa hojas y al final se recoge.
    pasos = 18
    puntos = [(x + lado * 16 * math.sin(k / pasos * math.pi * 1.6), piso - alto * k / pasos) for k in range(pasos + 1)]

    def dibujar(sup, u):
        crece = min(1.0, u / 0.4) if u < 0.82 else max(0.0, (1 - u) / 0.18)
        n = int(crece * pasos) + 1
        if n < 2:
            return
        visibles = puntos[:n]
        pygame.draw.lines(sup, (16, 56, 24), False, visibles, 7)
        pygame.draw.lines(sup, (50, 150, 60), False, visibles, 5)
        pygame.draw.lines(sup, (120, 210, 90), False, [(px - 1, py) for px, py in visibles], 1)
        for k in range(2, n, 2):
            px, py = visibles[k]
            sentido = 1 if k % 4 else -1
            hoja = [(px, py), (px + 11 * sentido, py - 5), (px + 14 * sentido, py), (px + 7 * sentido, py + 4)]
            pygame.draw.polygon(sup, (120, 210, 90), hoja)
            pygame.draw.polygon(sup, (16, 56, 24), hoja, 1)
            # Una espina del otro lado.
            pygame.draw.line(sup, (210, 250, 160), (px, py), (px - 5 * sentido, py - 3), 1)
        if conFlor and n == pasos + 1:
            px, py = visibles[-1]
            estrella(sup, px, py, 9, (150, 40, 90), 5, 0.5, u * 3)
            estrella(sup, px, py, 8, (255, 150, 190), 5, 0.5, u * 3)
            disco(sup, px, py, 3, (255, 235, 120))
    anim.trazo(t, duracion, dibujar, "frente")


def selvaViva(anim, c):
    # Brotan tallos alrededor del jefe, lo envuelven y florecen.
    t0, b = c.t0, c.objetivos[0]
    fin = t0 + 2.0
    anim.oscurecer(t0, fin, 135)
    anim.tinte(t0, fin - 0.2, (30, 140, 40), 40, 0.3, 0.4)

    def brote(sup, u):
        r = 66 * min(1.0, u * 4) * (1.0 if u < 0.85 else (1 - u) / 0.15)
        anillo(sup, b.x, b.piso, r, atenuar(paletas[4][2], 0.8), 2, 0.3)
    anim.trazo(t0, 1.7, brote)

    for k, (dx, alto) in enumerate(((-58, 96), (-32, 132), (-6, 150), (22, 126), (50, 104), (72, 80))):
        enredadera(anim, t0 + 0.15 + 0.07 * k, b.x + dx, b.piso + (k % 2) * 6, alto, 1 if k % 2 else -1, 1.5)

    hojas = anim.particulas(rampaHoja, capa="frente", gravedad=50, freno=1.5, encoge=False)
    brillo = anim.particulas(rampas[4], gravedad=-60, freno=1.0)
    ritmo, ritmoBrillo = cadencia(60), cadencia(70)

    def revolotear(u, dt):
        for _ in range(ritmo(dt)):
            a = azar.uniform(0, math.tau)
            hojas.emitir(b.x + 70 * math.cos(a), b.y + 50 * math.sin(a), -90 * math.sin(a), 60 * math.cos(a) - 30, 0.9, 3)
        for _ in range(ritmoBrillo(dt)):
            brillo.emitir(b.x + azar.uniform(-70, 70), b.piso - azar.uniform(0, 30), 0, -azar.uniform(30, 90), 0.8, 2)
    anim.durante(t0 + 0.3, t0 + 1.5, revolotear)

    tGolpe = t0 + 0.85
    anim.sacudir(tGolpe, 6, 0.5)
    anim.destello(tGolpe, (190, 255, 170), 0.2, 150)
    estallido(anim, tGolpe, b.x, b.y, 4, 2.4)
    estallido(anim, tGolpe + 0.3, b.x - 30, b.y + 20, 4, 1.4)
    estallido(anim, tGolpe + 0.45, b.x + 30, b.y - 20, 4, 1.4)
    anim.impacto = tGolpe
    anim.alargar(fin)


def nubarrones(anim, t, duracion):
    nubes = [(azar.uniform(-20, anchoCapa), azar.uniform(-10, 12), azar.uniform(60, 110), azar.choice((-1, 1))) for _ in range(22)]

    def dibujar(sup, u):
        entra = min(1.0, u * 5, (1 - u) * 4)
        for k, (x, y, ancho, lado) in enumerate(nubes):
            x += lado * 18 * u
            y = y - 46 * (1 - entra)
            pygame.draw.ellipse(sup, (20, 18, 34, 255), (int(x - 1), int(y - 1), int(ancho + 2), 30))
            pygame.draw.ellipse(sup, (62, 60, 92, 255), (int(x), int(y), int(ancho), 28))
            pygame.draw.ellipse(sup, (96, 94, 130, 255), (int(x + 6), int(y + 3), int(ancho * 0.6), 11))
    anim.trazo(t, duracion, dibujar, "frente")


def tormentaElectrica(anim, c):
    # Se cierra el cielo y cae un rayo tras otro sobre el jefe.
    t0, b = c.t0, c.objetivos[0]
    fin = t0 + 2.05
    color = paletas[5][1]
    anim.oscurecer(t0, fin, 175)
    nubarrones(anim, t0, fin - t0)

    def caer(t, grueso, fuerza):
        x0 = b.x + azar.uniform(-70, 70)
        x1, y1 = b.x + azar.uniform(-28, 28), b.piso - azar.uniform(0, 70)
        relampago(anim, t, x0, 18, x1, y1, color, 0.2, grueso, 12, 3)
        estallido(anim, t + 0.02, x1, y1, 5, fuerza)
        anim.destello(t, (235, 240, 255), 0.1, 110 + 40 * grueso)
    for k, t in enumerate((0.45, 0.63, 0.8, 0.94, 1.06)):
        caer(t0 + t, 2, 1.0)
        anim.sacudir(t0 + t, 3, 0.12)

    tFinal = t0 + 1.3
    for _ in range(3):
        caer(tFinal, 4, 1.8)
    anim.destello(tFinal, blanco, 0.22, 235)
    anim.sacudir(tFinal, 10, 0.6)
    anilloDeChoque(anim, tFinal, b.x, b.piso, 120, paletas[5][2], 0.5, 0.35, 3)
    anim.impacto = t0 + 0.5
    anim.alargar(fin)


def juicio(anim, c):
    # Se abre el cielo: una columna de luz baja sobre el jefe, la recorren
    # halos y al final estalla en una cruz.
    t0, b = c.t0, c.objetivos[0]
    tCruz = t0 + 1.2
    fin = tCruz + 0.95
    anim.oscurecer(t0, fin, 160)
    anim.tinte(t0 + 0.2, fin - 0.2, (255, 230, 150), 35, 0.3, 0.4)

    def columna(sup, u):
        ancho = 40 * min(1.0, u * 4) * (1.0 if u < 0.8 else (1 - u) / 0.2)
        if ancho > 1:
            for factor, tono in ((1.0, (70, 62, 30)), (0.7, (150, 135, 75)), (0.42, (235, 220, 160)), (0.16, blanco)):
                pygame.draw.rect(sup, tono, (int(b.x - ancho * factor), 0, max(1, int(ancho * factor * 2)), int(b.piso + 4)))
            disco(sup, b.x, b.piso + 4, ancho * 1.3, (150, 135, 75), 0.3)
    anim.trazo(t0 + 0.1, 1.5, columna)

    for k in range(5):
        def halo(sup, u):
            y = -10 + (b.piso + 10) * u
            anillo(sup, b.x, y, 34 + 10 * math.sin(u * math.pi), atenuar(paletas[6][1], math.sin(math.pi * u)), 2, 0.28)
        anim.trazo(t0 + 0.2 + 0.17 * k, 0.6, halo)

    motas = anim.particulas(rampas[6], gravedad=-60, freno=0.6)
    plumas = anim.particulas(rampaPluma, capa="frente", gravedad=26, freno=1.2, encoge=False)
    ritmo, ritmoPlumas = cadencia(90), cadencia(16)

    def flotar(u, dt):
        for _ in range(ritmo(dt)):
            motas.emitir(b.x + azar.uniform(-80, 80), b.piso - azar.uniform(0, 140), azar.uniform(-10, 10), -azar.uniform(20, 70), 0.9, 2)
        for _ in range(ritmoPlumas(dt)):
            plumas.emitir(b.x + azar.uniform(-90, 90), azar.uniform(0, 40), azar.uniform(-30, 30), azar.uniform(20, 50), 1.4, 3)
    anim.durante(t0 + 0.2, tCruz + 0.3, flotar)

    def cruz(sup, u):
        tam = 95 * math.sin(math.pi * min(1.0, u * 1.2))
        estrella(sup, b.x, b.y, tam, atenuar(paletas[6][1], 0.85), 4, 0.1, 0)
        estrella(sup, b.x, b.y, tam * 0.7, blanco, 4, 0.12, 0)
        estrella(sup, b.x, b.y, tam * 0.45, atenuar(paletas[6][2], 0.9), 4, 0.2, math.pi / 4)
    anim.trazo(tCruz, 0.55, cruz)
    anim.destello(tCruz, blanco, 0.25, 240)
    anim.sacudir(tCruz, 8, 0.5)
    anilloDeChoque(anim, tCruz, b.x, b.y, 150, paletas[6][2], 0.55, 1.0, 3)
    anilloDeChoque(anim, tCruz + 0.1, b.x, b.y, 100, paletas[6][1], 0.5, 1.0, 2)
    estallido(anim, tCruz, b.x, b.y, 6, 2.2)
    anim.impacto = tCruz
    anim.alargar(fin)


def abismo(anim, c):
    # Una esfera negra crece sobre el jefe tragandose la luz, se colapsa y revienta.
    t0, b = c.t0, c.objetivos[0]
    tFinal = t0 + 1.3
    fin = tFinal + 0.9
    morado = paletas[7][2]
    anim.oscurecer(t0, fin, 190)

    def radioDe(u):
        if u < 0.6:
            return 44 * suave(u / 0.6) + 2 * math.sin(u * 60)
        if u < 0.9:
            return 44 + 3 * math.sin(u * 80)
        return 44 * (1 - (u - 0.9) / 0.1)

    def esfera(sup, u):
        r = radioDe(u)
        disco(sup, b.x, b.y, r + 3, morado + (255,))
        disco(sup, b.x, b.y, r + 1, (60, 20, 100, 255))
        disco(sup, b.x, b.y, r, (6, 2, 12, 255))
    anim.trazo(t0, 1.3, esfera, "frente")

    def corona(sup, u):
        r = radioDe(u)
        anillo(sup, b.x, b.y, r + 10 + 3 * math.sin(u * 40), atenuar(morado, 0.5), 2)
        anillo(sup, b.x, b.y, r + 5, atenuar(paletas[7][3], 0.6), 1)
    anim.trazo(t0, 1.3, corona)

    tragadas = anim.rayas(list(reversed(rampas[7])), largo=0.05)
    ritmo = cadencia(210)

    def tragar(u, dt):
        for _ in range(ritmo(dt)):
            a, r = azar.uniform(0, math.tau), azar.uniform(80, 150)
            vida = azar.uniform(0.35, 0.55)
            tragadas.emitir(b.x + r * math.cos(a), b.y + r * 0.7 * math.sin(a), -r * math.cos(a) / vida,
                            -r * 0.7 * math.sin(a) / vida, vida, 1)
    anim.durante(t0 + 0.1, tFinal - 0.15, tragar)

    for k in range(7):
        a = azar.uniform(0, math.tau)
        relampago(anim, t0 + 0.3 + 0.13 * k, b.x + 40 * math.cos(a), b.y + 40 * math.sin(a), b.x + 85 * math.cos(a + 0.5),
                  b.y + 70 * math.sin(a + 0.5), morado, 0.14, 1, 8, 1)

    anim.sacudir(t0 + 0.3, 3, 1.0)
    anim.destello(tFinal, (170, 70, 240), 0.2, 160)
    anim.sacudir(tFinal, 12, 0.7)
    estallido(anim, tFinal, b.x, b.y, 7, 2.6)
    anilloDeChoque(anim, tFinal, b.x, b.y, 170, morado, 0.55, 1.0, 4)
    anilloDeChoque(anim, tFinal + 0.08, b.x, b.y, 120, paletas[7][3], 0.5, 1.0, 2)
    anilloDeChoque(anim, tFinal, b.x, b.y, 140, (10, 4, 20), 0.5, 1.0, 5, "frente")
    anim.impacto = tFinal
    anim.alargar(fin)


def proyectil(anim, c):
    # La receta de los conjuros sencillos: el dibujo del ataque vuela hasta
    # cada objetivo dejando una estela de su elemento y estalla al llegar.
    o = c.origen
    imagen = icono(c.nombre)
    if imagen is not None and c.sentido < 0:
        imagen = pygame.transform.flip(imagen, True, False)
    rampa = rampas[c.elem] if c.elem is not None else rampaChispa
    duracion = 0.3
    anim.oscurecer(c.t0 - 0.05, c.t0 + 0.75, 60)
    estela = anim.particulas(rampa, freno=2.0)

    for k, d in enumerate(c.objetivos):
        t = c.t0 + 0.03 * k
        ritmo = cadencia(110)

        def lugar(u, d=d):
            return o.x + (d.x - o.x) * u, o.y + (d.y - o.y) * u - 16 * math.sin(math.pi * u)

        def soltar(u, dt, lugar=lugar, ritmo=ritmo):
            x, y = lugar(u)
            for _ in range(ritmo(dt)):
                estela.emitir(x + azar.uniform(-3, 3), y + azar.uniform(-3, 3), azar.uniform(-20, 20), azar.uniform(-20, 20), 0.3, 3)
        anim.durante(t, t + duracion, soltar)

        def cuerpo(sup, u, lugar=lugar):
            x, y = lugar(u)
            if imagen is not None:
                sup.blit(imagen, imagen.get_rect(center=(int(x), int(y))))
        anim.trazo(t, duracion, cuerpo, "frente")
        estallido(anim, t + duracion, d.x, d.y, c.elem, 1.1)
    anim.impacto = c.t0 + duracion
    anim.alargar(c.t0 + duracion + 0.6)


def golpe(anim, c):
    # La receta de los golpes sencillos: un tajo y chispas sobre cada objetivo.
    for k, d in enumerate(c.objetivos):
        t = c.t0 + 0.03 * k
        x = d.x - 14 * c.sentido
        tajo(anim, t, x - 8 * c.sentido, d.y + 6, 30, -math.pi * 0.75, math.pi * 0.1, 6, (225, 232, 245), 0.2)
        chispazo(anim, t + 0.07, x, d.y, 1.0)
    anim.impacto = c.t0 + 0.08
    anim.alargar(c.t0 + 0.5)


def alPasar(t0, duracion, x0, x1, x):
    # En que momento pasa por x algo que va de x0 a x1 a paso parejo.
    return t0 + duracion * max(0.0, min(1.0, (x - x0) / ((x1 - x0) or 1.0)))


def incendio(anim, c):
    # Un muro de llamas barre el piso desde el jefe hasta los heroes.
    t0, o = c.t0, c.origen
    x0, x1, duracion = o.x - 45, 30.0, 0.6
    arriba = min(d.piso for d in c.objetivos) - 18
    abajo = max(d.piso for d in c.objetivos) + 8
    fin = t0 + 1.35
    anim.oscurecer(t0, fin, 120)
    anim.tinte(t0, fin - 0.2, (200, 50, 10), 40, 0.15, 0.3)
    llamas = anim.particulas(rampas[0], gravedad=-190, freno=1.0)
    ritmo = cadencia(520)

    def avanzar(u, dt):
        x = x0 + (x1 - x0) * u
        for _ in range(ritmo(dt)):
            llamas.emitir(x + azar.uniform(-10, 10), azar.uniform(arriba, abajo), azar.uniform(-40, 10),
                          -azar.uniform(40, 150), azar.uniform(0.3, 0.6), azar.choice((3, 4, 5)))
    anim.durante(t0, t0 + duracion, avanzar)

    def lenguas(sup, u):
        # El frente del incendio: una hilera de lenguas de fuego que se mecen.
        x = x0 + (x1 - x0) * u
        fuerza = min(1.0, u * 8, (1 - u) * 6)
        for k in range(7):
            y = arriba + (abajo - arriba) * k / 6 + 6
            mecida = 5 * math.sin(u * 40 + k * 1.7)
            alto = (30 + 10 * math.sin(u * 55 + k)) * fuerza
            cx = x + 5 * (k % 2)
            for factor, tono in ((1.0, (150, 55, 10)), (0.65, (240, 140, 40)), (0.32, (255, 235, 170))):
                pygame.draw.polygon(sup, tono, [(cx - 9 * factor, y), (cx - 4 * factor + mecida * 0.5, y - alto * factor * 0.6),
                                               (cx + mecida, y - alto * factor), (cx + 5 * factor + mecida * 0.5, y - alto * factor * 0.5),
                                               (cx + 9 * factor, y)])
    anim.trazo(t0, duracion, lenguas)

    rescoldo = anim.particulas(rampas[0], gravedad=-60, freno=1.5)
    ritmoRescoldo = cadencia(160)

    def dejarRescoldo(u, dt):
        x = x0 + (x1 - x0) * u
        for _ in range(ritmoRescoldo(dt)):
            rescoldo.emitir(x + azar.uniform(0, 40), azar.uniform(arriba, abajo), 0, -azar.uniform(10, 50), azar.uniform(0.5, 0.9), 3)
    anim.durante(t0, t0 + duracion, dejarRescoldo)

    for d in c.objetivos:
        estallido(anim, alPasar(t0, duracion, x0, x1, d.x), d.x, d.y, 0, 1.4)
    anim.sacudir(t0, 3, 0.6)
    anim.impacto = alPasar(t0, duracion, x0, x1, centroDe(c.objetivos)[0])
    anim.alargar(fin)


def marejada(anim, c):
    # Una ola enorme cruza la arena y revienta sobre cada heroe.
    t0, o = c.t0, c.origen
    x0, x1, duracion = o.x - 20, -150.0, 0.85
    base, alto = altoCapa + 4, 150
    fin = t0 + 1.45
    anim.oscurecer(t0, fin, 120)
    anim.tinte(t0, fin - 0.2, (20, 60, 170), 45, 0.15, 0.3)
    espuma = anim.particulas([(255, 255, 255), (220, 240, 255), (150, 200, 250), (80, 140, 230)], gravedad=300)
    gotas = anim.particulas(rampas[1], gravedad=380)
    ritmo = cadencia(260)

    def ola(sup, u):
        x = x0 + (x1 - x0) * u
        h = alto * min(1.0, u * 5) * (1.0 if u < 0.85 else (1 - u) / 0.15)
        cresta = [(x + 170, base), (x + 120, base - h * 0.45), (x + 60, base - h * 0.85), (x + 14, base - h),
                  (x - 16, base - h * 0.93), (x - 26, base - h * 0.78), (x - 14, base - h * 0.7), (x + 2, base - h * 0.6),
                  (x - 6, base - h * 0.3), (x - 18, base)]
        pygame.draw.polygon(sup, (30, 90, 200, 225), cresta)
        pygame.draw.polygon(sup, (70, 150, 240, 225), [(x + 150, base), (x + 104, base - h * 0.42), (x + 52, base - h * 0.74),
                                                       (x + 20, base - h * 0.82), (x + 26, base - h * 0.5), (x + 16, base)])
        pygame.draw.lines(sup, (235, 250, 255, 255), False, cresta[2:8], 3)
        pygame.draw.polygon(sup, (14, 40, 110, 255), cresta, 1)
    anim.trazo(t0, duracion, ola, "frente")

    def salpicar(u, dt):
        x = x0 + (x1 - x0) * u
        h = alto * min(1.0, u * 5)
        for _ in range(ritmo(dt)):
            espuma.emitir(x + azar.uniform(-26, 20), base - h * azar.uniform(0.7, 1.0), azar.uniform(-160, 40),
                          -azar.uniform(20, 120), 0.5, 2)
    anim.durante(t0, t0 + duracion, salpicar)

    for d in c.objetivos:
        t = alPasar(t0, duracion, x0, x1, d.x)
        estallido(anim, t, d.x, d.y, 1, 1.5)
        anim.en(t, lambda d=d: gotas.rafaga(d.x, d.piso, 14, 200, 0.7, 2, -math.pi / 2, math.pi * 0.6))
    anim.sacudir(t0 + 0.2, 4, 0.6)
    anim.impacto = alPasar(t0, duracion, x0, x1, centroDe(c.objetivos)[0])
    anim.alargar(fin)


def vendaval(anim, c):
    # Cuchillas de viento cruzan la arena de lado a lado.
    t0, o = c.t0, c.origen
    fin = t0 + 1.2
    arriba = min(d.y for d in c.objetivos) - 26
    abajo = max(d.piso for d in c.objetivos) + 4
    anim.oscurecer(t0, fin, 110)
    rachas = anim.rayas([(230, 255, 245), (150, 230, 205), (80, 170, 150)], largo=0.06)
    ritmo = cadencia(110)

    def soplar(u, dt):
        for _ in range(ritmo(dt)):
            rachas.emitir(anchoCapa + 10, azar.uniform(10, altoCapa - 16), -azar.uniform(560, 800), azar.uniform(-20, 20), 0.9, 1)
    anim.durante(t0 - 0.1, t0 + 0.7, soplar)

    for k in range(11):
        y = arriba + (abajo - arriba) * ((k * 5) % 11) / 10
        tam = azar.uniform(14, 24)

        def cuchilla(sup, u, y=y, tam=tam):
            x = o.x - 40 + (-30 - (o.x - 40)) * u
            brillo = min(1.0, u * 6, (1 - u) * 4)
            mediaLuna(sup, x + tam, y, tam, math.pi * 0.55, math.pi * 1.45, tam * 0.4, atenuar(paletas[2][1], brillo))
            mediaLuna(sup, x + tam, y, tam - 1, math.pi * 0.6, math.pi * 1.4, tam * 0.18, atenuar(blanco, brillo))
        anim.trazo(t0 + 0.045 * k, 0.42, cuchilla)

    for k, d in enumerate(c.objetivos):
        estallido(anim, t0 + 0.3 + 0.07 * k, d.x, d.y, 2, 1.2)
    anim.sacudir(t0 + 0.25, 3, 0.4)
    anim.impacto = t0 + 0.38
    anim.alargar(fin)


def pedrusco(anim, t, x0, y0, x1, y1, duracion, radio, alLlegar=None):
    polvo = anim.particulas(rampaPolvo, capa="frente", gravedad=-10, freno=2.0)
    ritmo = cadencia(60)

    def lugar(u):
        return x0 + (x1 - x0) * u, y0 + (y1 - y0) * u * u

    def soltar(u, dt):
        x, y = lugar(u)
        for _ in range(ritmo(dt)):
            polvo.emitir(x + azar.uniform(-3, 3), y - radio, azar.uniform(-10, 10), azar.uniform(-10, 10), 0.35, 3)
    anim.durante(t, t + duracion, soltar)
    anim.trazo(t, duracion, lambda sup, u: roca(sup, *lugar(u), radio, paletaRoca, u * 5), "frente")
    if alLlegar is not None:
        anim.en(t + duracion, alLlegar)


def avalancha(anim, c):
    # Llueven rocas: una grande sobre cada heroe y otras mas chicas alrededor.
    t0 = c.t0
    fin = t0 + 1.4
    cx, _, piso = centroDe(c.objetivos)
    anim.oscurecer(t0, fin, 110)
    anim.sacudir(t0, 3, 0.9)
    for k in range(7):
        x, y = cx + azar.uniform(-110, 130), piso + azar.uniform(-50, 50)
        pedrusco(anim, t0 + azar.uniform(0, 0.6), x + 30, -14, x, y, 0.3, azar.uniform(3, 5))
        polvareda(anim, t0 + 0.9, x, y, 0.6)
    ultimo = t0
    for k, d in enumerate(c.objetivos):
        t = t0 + 0.12 * k
        pedrusco(anim, t, d.x + 36, -20, d.x, d.piso - 10, 0.34, 14)
        estallido(anim, t + 0.34, d.x, d.piso - 10, 3, 1.5)
        anim.sacudir(t + 0.34, 5, 0.2)
        ultimo = t + 0.34
    anim.impacto = (t0 + 0.34 + ultimo) / 2
    anim.alargar(fin)


def enredaderas(anim, c):
    # Brotan tallos con espinas a los pies de cada heroe.
    t0 = c.t0
    fin = t0 + 1.4
    anim.oscurecer(t0, fin, 110)
    for k, d in enumerate(c.objetivos):
        t = t0 + 0.06 * k
        anilloDeChoque(anim, t, d.x, d.piso, 24, paletas[4][2], 0.4, 0.35)
        enredadera(anim, t, d.x - 12, d.piso, 46, -1, 1.1, False)
        enredadera(anim, t + 0.05, d.x + 12, d.piso + 3, 54, 1, 1.1)
        estallido(anim, t + 0.4, d.x, d.y, 4, 1.3)
    anim.sacudir(t0 + 0.4, 3, 0.3)
    anim.impacto = t0 + 0.43
    anim.alargar(fin)


def tormenta(anim, c):
    # Nubes negras y un rayo sobre cada heroe.
    t0 = c.t0
    fin = t0 + 1.45
    anim.oscurecer(t0, fin, 150)
    nubarrones(anim, t0, fin - t0)
    for k, d in enumerate(c.objetivos):
        t = t0 + 0.32 + 0.11 * k
        relampago(anim, t, d.x + azar.uniform(-30, 30), 18, d.x, d.piso - 8, paletas[5][1], 0.22, 3, 10, 2)
        estallido(anim, t + 0.02, d.x, d.y, 5, 1.4)
        anim.destello(t, (235, 240, 255), 0.09, 120)
        anim.sacudir(t, 4, 0.12)
    anim.impacto = t0 + 0.38
    anim.alargar(fin)


def resplandor(anim, c):
    # El jefe se enciende y una onda de luz recorre la arena.
    t0, o = c.t0, c.origen
    fin = t0 + 1.3
    anim.oscurecer(t0, fin, 140)

    def rayos(sup, u):
        brillo = math.sin(math.pi * u)
        for k in range(12):
            a = k * math.tau / 12 + u * 1.2
            largo = 130 + 50 * (k % 3)
            punta = (o.x + largo * math.cos(a), o.y + largo * math.sin(a))
            lado = (o.x + 14 * math.cos(a + 1.5), o.y + 14 * math.sin(a + 1.5))
            otro = (o.x + 14 * math.cos(a - 1.5), o.y + 14 * math.sin(a - 1.5))
            pygame.draw.polygon(sup, atenuar((120, 105, 55), brillo), [lado, punta, otro])
        estrella(sup, o.x, o.y, 46 * brillo, blanco, 4, 0.18, u * 2)
    anim.trazo(t0, 0.8, rayos)

    def onda(sup, u):
        r = 30 + 430 * u
        anillo(sup, o.x, o.y, r, atenuar(paletas[6][1], 1 - u * 0.6), 5)
        anillo(sup, o.x, o.y, r - 4, atenuar(blanco, 1 - u), 2)
    anim.trazo(t0 + 0.15, 0.55, onda)
    anim.destello(t0 + 0.12, (255, 250, 220), 0.2, 150)

    for d in c.objetivos:
        distancia = math.hypot(d.x - o.x, d.y - o.y)
        estallido(anim, t0 + 0.15 + 0.55 * min(1.0, max(0.0, (distancia - 30) / 430)), d.x, d.y, 6, 1.4)
    anim.impacto = t0 + 0.15 + 0.55 * min(1.0, (math.hypot(centroDe(c.objetivos)[0] - o.x, 0) - 30) / 430)
    anim.alargar(fin)


def eclipse(anim, c):
    # Un disco negro tapa el cielo y de el cae una sombra sobre cada heroe.
    t0 = c.t0
    cx = centroDe(c.objetivos)[0]
    sx, sy = cx + 60, 26
    fin = t0 + 1.55
    morado = paletas[7][2]
    anim.oscurecer(t0, fin, 195)

    def sol(sup, u):
        r = 24 * min(1.0, u * 5) * (1.0 if u < 0.85 else (1 - u) / 0.15)
        disco(sup, sx, sy, r + 3, morado + (255,))
        disco(sup, sx, sy, r, (4, 2, 10, 255))
    anim.trazo(t0, 1.4, sol, "frente")

    def corona(sup, u):
        r = 24 * min(1.0, u * 5) * (1.0 if u < 0.85 else (1 - u) / 0.15)
        anillo(sup, sx, sy, r + 9 + 2 * math.sin(u * 50), atenuar(morado, 0.6), 2)
        for k in range(8):
            a = k * math.tau / 8 + u * 2
            pygame.draw.line(sup, atenuar(paletas[7][3], 0.5), (sx + (r + 6) * math.cos(a), sy + (r + 6) * math.sin(a)),
                             (sx + (r + 18) * math.cos(a), sy + (r + 18) * math.sin(a)), 1)
    anim.trazo(t0, 1.4, corona)

    for k, d in enumerate(c.objetivos):
        t = t0 + 0.4 + 0.08 * k

        def sombra(sup, u, d=d):
            ancho = 14 * math.sin(math.pi * u)
            pygame.draw.polygon(sup, (8, 2, 18, 230), [(sx - 4, sy), (sx + 4, sy), (d.x + ancho, d.piso), (d.x - ancho, d.piso)])
        anim.trazo(t, 0.45, sombra, "frente")

        def filo(sup, u, d=d):
            ancho = 14 * math.sin(math.pi * u)
            pygame.draw.line(sup, atenuar(morado, 0.9), (sx - 4, sy), (d.x - ancho, d.piso), 1)
            pygame.draw.line(sup, atenuar(morado, 0.9), (sx + 4, sy), (d.x + ancho, d.piso), 1)
        anim.trazo(t, 0.45, filo)
        estallido(anim, t + 0.2, d.x, d.y, 7, 1.5)
    anim.sacudir(t0 + 0.6, 4, 0.4)
    anim.impacto = t0 + 0.65
    anim.alargar(fin)


def terremoto(anim, c):
    # Pisa y el piso se agrieta hasta cada heroe, donde brota una roca.
    t0, o = c.t0, c.origen
    px, py = o.x - 30, o.piso
    fin = t0 + 1.3
    anim.oscurecer(t0, fin, 80)
    anim.sacudir(t0, 10, 0.9)
    polvareda(anim, t0, px, py, 1.8)
    anilloDeChoque(anim, t0, px, py, 90, (230, 200, 150), 0.4, 0.4, 3)
    for d in c.objetivos:
        grieta(anim, t0, px, py, d.x, d.piso, 0.3, 0.8)
        pico(anim, t0 + 0.3, d.x, d.piso + 2, 34, 22, 0.75)
        estallido(anim, t0 + 0.32, d.x, d.piso - 10, 3, 1.3)
    for k in range(6):
        pedrusco(anim, t0 + 0.1 + 0.1 * k, azar.uniform(60, 420), -10, azar.uniform(60, 420), azar.uniform(90, 220), 0.3, 3)
    anim.impacto = t0 + 0.34
    anim.alargar(fin)


def ondaDeChoque(anim, c):
    # Tres anillos se abren por el piso desde los pies del jefe.
    t0, o = c.t0, c.origen
    px, py = o.x - 30, o.piso
    fin = t0 + 1.1
    anim.oscurecer(t0, fin, 70)
    anim.sacudir(t0, 7, 0.6)
    chispazo(anim, t0, px, py - 4, 2.0)
    for k in range(3):
        anilloDeChoque(anim, t0 + 0.09 * k, px, py, 400, (255, 240, 200), 0.6, 0.36, 4 - k)
        anilloDeChoque(anim, t0 + 0.04 + 0.09 * k, px, py, 380, (205, 185, 155), 0.6, 0.36, 2, "frente")
    for d in c.objetivos:
        t = t0 + 0.6 * math.sqrt(min(1.0, math.hypot(d.x - px, (d.piso - py) / 0.36) / 400)) * 0.75
        chispazo(anim, t, d.x, d.y, 1.3)
        polvareda(anim, t, d.x, d.piso, 1.0)
    anim.impacto = t0 + 0.33
    anim.alargar(fin)


def barrido(anim, c):
    # Un solo tajo enorme que alcanza a todo el equipo.
    t0, o = c.t0, c.origen
    cx, cy = o.x - 10, o.y + 10
    lejos = max(math.hypot(d.x - cx, d.y - cy) for d in c.objetivos) + 22
    cerca = min(math.hypot(d.x - cx, d.y - cy) for d in c.objetivos) - 10
    fin = t0 + 0.95
    anim.oscurecer(t0, fin, 90)
    tajo(anim, t0, cx, cy, lejos, math.pi * 0.72, math.pi * 1.24, 22, (190, 150, 240), 0.3)
    tajo(anim, t0 + 0.04, cx, cy, (lejos + cerca) / 2, math.pi * 0.74, math.pi * 1.22, 14, (225, 232, 245), 0.3)
    tajo(anim, t0 + 0.08, cx, cy, max(40, cerca), math.pi * 0.76, math.pi * 1.2, 9, (190, 150, 240), 0.3)
    for k, d in enumerate(sorted(c.objetivos, key=lambda d: d.y)):
        chispazo(anim, t0 + 0.08 + 0.04 * k, d.x, d.y, 1.4)
    anim.destello(t0 + 0.1, blanco, 0.1, 90)
    anim.sacudir(t0 + 0.1, 5, 0.3)
    anim.impacto = t0 + 0.14
    anim.alargar(fin)


def estampida(anim, c):
    # Una carga de pisotones que levanta polvo de un lado a otro.
    t0, o = c.t0, c.origen
    fin = t0 + 1.25
    arriba = min(d.piso for d in c.objetivos)
    abajo = max(d.piso for d in c.objetivos)
    anim.oscurecer(t0, fin, 80)
    anim.sacudir(t0, 6, 0.9)
    rachas = anim.rayas([(255, 255, 255), (230, 220, 200), (160, 150, 130)], largo=0.05)
    polvo = anim.particulas(rampaPolvo, capa="frente", gravedad=-30, freno=2.0)
    ritmo, ritmoPolvo = cadencia(70), cadencia(160)
    x0, x1, duracion = o.x - 60, 40.0, 0.7

    def correr(u, dt):
        x = x0 + (x1 - x0) * u
        for _ in range(ritmo(dt)):
            rachas.emitir(x + 60, azar.uniform(arriba - 40, abajo), -azar.uniform(500, 700), 0, 0.3, 1)
        for _ in range(ritmoPolvo(dt)):
            polvo.emitir(x + azar.uniform(-10, 30), azar.uniform(arriba - 6, abajo + 6), azar.uniform(-20, 60),
                         -azar.uniform(10, 70), 0.6, azar.choice((4, 5, 6)))
    anim.durante(t0, t0 + duracion, correr)

    for k in range(9):
        s = k / 8
        x = x0 + (x1 - x0) * s
        chispazo(anim, t0 + duracion * s, x, arriba + (abajo - arriba) * (k % 3) / 2, 1.1, (255, 230, 190))
    for d in c.objetivos:
        chispazo(anim, alPasar(t0, duracion, x0, x1, d.x), d.x, d.y, 1.4)
    anim.impacto = alPasar(t0, duracion, x0, x1, centroDe(c.objetivos)[0])
    anim.alargar(fin)


def chorroDeParticulas(anim, c, grupo, tamanos, caida=0.0):
    # Un chorro continuo del jefe a su objetivo, para la llamarada y el chorro de agua.
    t0, o, d = c.t0, c.origen, c.objetivos[0]
    bx, by = o.x - 44, o.y - 6
    largo = math.hypot(d.x - bx, d.y - by) or 1.0
    vuelo = 0.34
    ritmo = cadencia(900)

    def soltar(u, dt):
        # Sale angosto de las manos del jefe y se va abriendo hasta el heroe.
        for _ in range(ritmo(dt)):
            vx = (d.x - bx) / vuelo * azar.uniform(0.85, 1.15)
            vy = (d.y - by) / vuelo + azar.uniform(-75, 75) - caida * vuelo / 2
            grupo.emitir(bx + azar.uniform(-3, 3), by + azar.uniform(-3, 3), vx, vy, vuelo * azar.uniform(0.85, 1.2), azar.choice(tamanos))
    anim.durante(t0, t0 + 0.55, soltar)
    return t0 + vuelo, largo


def llamarada(anim, c):
    d = c.objetivos[0]
    anim.oscurecer(c.t0, c.t0 + 1.1, 110)
    llamas = anim.particulas(rampas[0], gravedad=-40, freno=0.3)
    llegada, _ = chorroDeParticulas(anim, c, llamas, (4, 5, 6))
    fogonazo(anim, c.t0, c.origen.x - 44, c.origen.y - 6, 14, (255, 150, 40))
    estallido(anim, llegada, d.x, d.y, 0, 1.3)
    estallido(anim, llegada + 0.25, d.x, d.y, 0, 1.5)
    anim.sacudir(llegada, 3, 0.4)
    anim.impacto = llegada + 0.05
    anim.alargar(c.t0 + 1.1)


def chorro(anim, c):
    d = c.objetivos[0]
    anim.oscurecer(c.t0, c.t0 + 1.1, 110)
    agua = anim.particulas(rampas[1], gravedad=160, freno=0.2)
    llegada, _ = chorroDeParticulas(anim, c, agua, (3, 4, 5), 160)
    estallido(anim, llegada, d.x, d.y, 1, 1.3)
    estallido(anim, llegada + 0.25, d.x, d.y, 1, 1.6)
    anim.sacudir(llegada, 3, 0.4)
    anim.impacto = llegada + 0.05
    anim.alargar(c.t0 + 1.1)


def rafaga(anim, c):
    # Tres cuchillas de viento seguidas.
    t0, o, d = c.t0, c.origen, c.objetivos[0]
    bx, by = o.x - 44, o.y - 6
    anim.oscurecer(t0, t0 + 1.0, 100)
    for k in range(3):
        def cuchilla(sup, u, k=k):
            x, y = bx + (d.x - bx) * u, by + (d.y - by) * u + (k - 1) * 10 * math.sin(math.pi * u)
            mediaLuna(sup, x + 16, y, 18, math.pi * 0.55, math.pi * 1.45, 7, paletas[2][1])
            mediaLuna(sup, x + 16, y, 17, math.pi * 0.6, math.pi * 1.4, 3, blanco)
        anim.trazo(t0 + 0.09 * k, 0.24, cuchilla)
        estallido(anim, t0 + 0.24 + 0.09 * k, d.x, d.y, 2, 0.9 + 0.25 * k)
    anim.impacto = t0 + 0.28
    anim.alargar(t0 + 1.0)


def lanzaDeRoca(anim, c):
    t0, o, d = c.t0, c.origen, c.objetivos[0]
    bx, by = o.x - 44, o.y - 6
    imagen = icono(c.nombre)
    if imagen is not None:
        imagen = pygame.transform.flip(imagen, True, False)
    anim.oscurecer(t0, t0 + 0.95, 90)
    polvo = anim.particulas(rampaPolvo, capa="frente", freno=2.0)
    ritmo = cadencia(120)

    def volar(u, dt):
        for _ in range(ritmo(dt)):
            polvo.emitir(bx + (d.x - bx) * u + 10, by + (d.y - by) * u + azar.uniform(-3, 3), azar.uniform(20, 60), azar.uniform(-12, 12), 0.3, 3)
    anim.durante(t0, t0 + 0.2, volar)

    def cuerpo(sup, u):
        if imagen is not None:
            sup.blit(imagen, imagen.get_rect(center=(int(bx + (d.x - bx) * u), int(by + (d.y - by) * u))))
    anim.trazo(t0, 0.2, cuerpo, "frente")
    estallido(anim, t0 + 0.2, d.x, d.y, 3, 1.7)
    anim.sacudir(t0 + 0.2, 5, 0.25)
    anim.impacto = t0 + 0.2
    anim.alargar(t0 + 0.95)


def puas(anim, t, x, y, alto, ancho, duracion=0.6):
    def dibujar(sup, u):
        h = alto * min(1.0, u / 0.12) * (1.0 if u < 0.72 else (1 - u) / 0.28)
        if h < 2:
            return
        cuerpo = [(x - ancho / 2, y), (x + ancho * 0.1, y - h), (x + ancho / 2, y)]
        pygame.draw.polygon(sup, (50, 150, 60), cuerpo)
        pygame.draw.polygon(sup, (150, 225, 95), [(x - ancho / 2, y), (x + ancho * 0.1, y - h), (x - ancho * 0.1, y)])
        pygame.draw.polygon(sup, (16, 56, 24), cuerpo, 1)
    anim.trazo(t, duracion, dibujar, "frente")


def espinas(anim, c):
    t0, d = c.t0, c.objetivos[0]
    anim.oscurecer(t0, t0 + 1.0, 100)
    anilloDeChoque(anim, t0, d.x, d.piso, 30, paletas[4][2], 0.35, 0.35)
    for k, (dx, alto) in enumerate(((-16, 30), (12, 38), (-4, 50), (22, 26), (-26, 22))):
        puas(anim, t0 + 0.1 + 0.04 * k, d.x + dx, d.piso + (k % 2) * 4, alto, 11)
    estallido(anim, t0 + 0.2, d.x, d.y, 4, 1.4)
    anim.sacudir(t0 + 0.2, 3, 0.25)
    anim.impacto = t0 + 0.22
    anim.alargar(t0 + 1.0)


def descarga(anim, c):
    t0, o, d = c.t0, c.origen, c.objetivos[0]
    bx, by = o.x - 44, o.y - 6
    anim.oscurecer(t0, t0 + 0.95, 140)
    fogonazo(anim, t0, bx, by, 14, (255, 240, 130), 0.2)
    relampago(anim, t0, bx, by, d.x, d.y, paletas[5][1], 0.32, 3, 14, 3)
    relampago(anim, t0 + 0.05, bx, by, d.x, d.y, paletas[5][2], 0.25, 1, 22, 1)
    estallido(anim, t0 + 0.04, d.x, d.y, 5, 1.6)
    estallido(anim, t0 + 0.22, d.x, d.y, 5, 1.0)
    anim.destello(t0, (235, 240, 255), 0.1, 120)
    anim.sacudir(t0, 4, 0.3)
    anim.impacto = t0 + 0.06
    anim.alargar(t0 + 0.95)


def rayoDeLuz(anim, c):
    t0, o, d = c.t0, c.origen, c.objetivos[0]
    bx, by = o.x - 44, o.y - 6
    anim.oscurecer(t0, t0 + 1.0, 130)
    haz(anim, t0, bx, by, d.x, d.y, 9, paletas[6][1], 0.45)
    motas = anim.particulas(rampas[6], gravedad=-50, freno=1.0)
    ritmo = cadencia(120)

    def brillar(u, dt):
        for _ in range(ritmo(dt)):
            s = azar.random()
            motas.emitir(bx + (d.x - bx) * s, by + (d.y - by) * s, azar.uniform(-30, 30), azar.uniform(-40, 10), 0.4, 2)
    anim.durante(t0, t0 + 0.4, brillar)
    estallido(anim, t0 + 0.05, d.x, d.y, 6, 1.6)
    anim.destello(t0, (255, 250, 220), 0.1, 100)
    anim.impacto = t0 + 0.08
    anim.alargar(t0 + 1.0)


def zarpas(anim, t, x, y, cuantas, color, tam=30, lado=1, separacion=9):
    # Varios tajos paralelos, como las marcas de una garra.
    for k in range(cuantas):
        corrido = (k - (cuantas - 1) / 2) * separacion
        if lado > 0:
            tajo(anim, t + 0.02 * k, x + corrido + tam * 0.5, y + tam * 0.3, tam, math.pi * 1.45, math.pi * 0.85, 5, color, 0.2)
        else:
            tajo(anim, t + 0.02 * k, x + corrido - tam * 0.5, y + tam * 0.3, tam, math.pi * 1.55, math.pi * 2.15, 5, color, 0.2)


def garraSombria(anim, c):
    t0, d = c.t0, c.objetivos[0]
    anim.oscurecer(t0, t0 + 1.0, 160)
    zarpas(anim, t0, d.x, d.y, 3, paletas[7][2], 34)
    zarpas(anim, t0 + 0.12, d.x, d.y, 3, paletas[7][3], 34, -1)
    estallido(anim, t0 + 0.16, d.x, d.y, 7, 1.5)
    anim.sacudir(t0 + 0.12, 4, 0.3)
    anim.impacto = t0 + 0.16
    anim.alargar(t0 + 1.0)


colorGarra = (215, 200, 245)


def zarpazo(anim, c):
    t0, d = c.t0, c.objetivos[0]
    zarpas(anim, t0, d.x, d.y, 3, colorGarra, 32)
    chispazo(anim, t0 + 0.08, d.x, d.y, 1.2)
    anim.sacudir(t0 + 0.08, 2, 0.15)
    anim.impacto = t0 + 0.09
    anim.alargar(t0 + 0.55)


def garraDoble(anim, c):
    t0, d = c.t0, c.objetivos[0]
    zarpas(anim, t0, d.x, d.y, 2, colorGarra, 32)
    zarpas(anim, t0 + 0.13, d.x, d.y, 2, colorGarra, 32, -1)
    chispazo(anim, t0 + 0.08, d.x, d.y, 1.0)
    chispazo(anim, t0 + 0.21, d.x, d.y, 1.4)
    anim.sacudir(t0 + 0.2, 3, 0.2)
    anim.impacto = t0 + 0.2
    anim.alargar(t0 + 0.7)


def mordida(anim, c):
    # Dos hileras de colmillos que se cierran sobre el heroe.
    t0, d = c.t0, c.objetivos[0]

    def fauces(sup, u):
        cierre = min(1.0, u / 0.35)
        alfa = 255 if u < 0.7 else int(255 * (1 - u) / 0.3)
        abertura = 26 * (1 - cierre * cierre)
        for lado in (-1, 1):
            orilla = d.y + lado * (abertura + 13)
            encia = [(d.x - 26, orilla), (d.x + 26, orilla), (d.x + 22, orilla - lado * 5), (d.x - 22, orilla - lado * 5)]
            pygame.draw.polygon(sup, (120, 40, 70, alfa), encia)
            for k in range(5):
                x = d.x - 20 + k * 10
                largo = 12 if k in (0, 4) else 9
                diente = [(x - 4, orilla - lado * 5), (x + 4, orilla - lado * 5), (x, orilla - lado * (5 + largo))]
                pygame.draw.polygon(sup, (250, 250, 240, alfa), diente)
                pygame.draw.polygon(sup, (60, 40, 70, alfa), diente, 1)
    anim.trazo(t0, 0.4, fauces, "frente")
    chispazo(anim, t0 + 0.14, d.x, d.y, 1.5, (255, 120, 120))
    anim.sacudir(t0 + 0.14, 3, 0.2)
    anim.impacto = t0 + 0.14
    anim.alargar(t0 + 0.65)


def coletazo(anim, c):
    t0, d = c.t0, c.objetivos[0]
    tajo(anim, t0, d.x + 34, d.y + 6, 46, math.pi * 0.55, math.pi * 1.5, 13, (190, 170, 225), 0.24)
    chispazo(anim, t0 + 0.1, d.x, d.y, 1.5)
    polvareda(anim, t0 + 0.1, d.x, d.piso, 1.0)
    anim.sacudir(t0 + 0.1, 3, 0.2)
    anim.impacto = t0 + 0.1
    anim.alargar(t0 + 0.6)


def pisoton(anim, c):
    t0, d = c.t0, c.objetivos[0]
    chispazo(anim, t0, d.x, d.piso - 6, 1.6)
    polvareda(anim, t0, d.x, d.piso, 1.8)
    anilloDeChoque(anim, t0, d.x, d.piso, 46, (255, 240, 200), 0.3, 0.38, 2)
    piedras = anim.particulas(rampaPiedra, capa="frente", gravedad=430, encoge=False)
    anim.en(t0, lambda: piedras.rafaga(d.x, d.piso - 3, 10, 150, 0.6, 2, -math.pi / 2, math.pi * 0.9))
    anim.sacudir(t0, 6, 0.3)
    anim.impacto = t0 + 0.02
    anim.alargar(t0 + 0.65)


def embestida(anim, c):
    t0, d = c.t0, c.objetivos[0]
    rachas = anim.rayas([(255, 255, 255), (220, 210, 240), (140, 120, 180)], largo=0.05)
    anim.en(t0 - 0.05, lambda: [rachas.emitir(d.x + azar.uniform(20, 90), d.y + azar.uniform(-30, 30), -azar.uniform(500, 800), 0, 0.25, 1)
                                for _ in range(16)])
    chispazo(anim, t0 + 0.02, d.x, d.y, 1.8)
    anilloDeChoque(anim, t0 + 0.02, d.x, d.y, 40, blanco, 0.25, 1.0, 2)
    anim.sacudir(t0 + 0.02, 5, 0.25)
    anim.impacto = t0 + 0.03
    anim.alargar(t0 + 0.6)


def cabezazo(anim, c):
    t0, d = c.t0, c.objetivos[0]
    chispazo(anim, t0, d.x, d.y - 8, 1.6, (255, 240, 170))

    def estrellitas(sup, u):
        for k in range(3):
            a = k * math.tau / 3 + u * 7
            estrella(sup, d.x + 18 * math.cos(a), d.y - 30 + 5 * math.sin(a), 5 * (1 - u * 0.5), (255, 235, 120), 5, 0.45, u * 4)
    anim.trazo(t0 + 0.08, 0.5, estrellitas)
    anim.sacudir(t0, 4, 0.2)
    anim.impacto = t0 + 0.02
    anim.alargar(t0 + 0.65)


def golpePesado(anim, c):
    t0, d = c.t0, c.objetivos[0]
    anim.oscurecer(t0 - 0.05, t0 + 0.6, 70)
    chispazo(anim, t0, d.x, d.y, 2.4, (255, 230, 190))
    anilloDeChoque(anim, t0, d.x, d.y, 56, blanco, 0.3, 1.0, 3)
    anilloDeChoque(anim, t0 + 0.06, d.x, d.y, 38, (255, 200, 120), 0.3, 1.0, 2)
    polvareda(anim, t0, d.x, d.piso, 1.4)
    anim.destello(t0, blanco, 0.09, 110)
    anim.sacudir(t0, 8, 0.35)
    anim.impacto = t0 + 0.02
    anim.alargar(t0 + 0.7)


def puntoDeGolpe(c):
    # Donde le pega un heroe al jefe: del lado por el que llega y a media altura.
    b = c.objetivos[0]
    return b.x - 22, b.y + 14


def ataqueBasico(anim, c):
    # Cada clase pega a su manera con su arma.
    t0 = c.t0
    x, y = puntoDeGolpe(c)
    if c.actor == "Mago":
        orbe(anim, c)
        return
    if c.actor == "Tanque":
        chispazo(anim, t0, x, y, 1.6, (255, 235, 190))
        anilloDeChoque(anim, t0, x, y, 30, blanco, 0.22, 1.0, 2)
        anim.sacudir(t0, 2, 0.15)
    elif c.actor == "Clerigo":
        chispazo(anim, t0, x, y, 1.2, paletas[6][1])
        anim.trazo(t0, 0.25, lambda sup, u: estrella(sup, x, y, 16 * math.sin(math.pi * u), paletas[6][2], 4, 0.18, u))
    elif c.actor == "Picaro":
        corte(anim, t0, x - 22, y - 22, x + 22, y + 20, 6, (215, 225, 245), 0.14)
        corte(anim, t0 + 0.07, x - 22, y + 20, x + 22, y - 22, 6, (215, 225, 245), 0.14)
        chispazo(anim, t0 + 0.09, x, y, 1.0)
    elif c.actor == "Berserker":
        corte(anim, t0, x - 6, y - 52, x + 10, y + 40, 15, (255, 200, 150), 0.2, 0.45)
        chispazo(anim, t0 + 0.08, x, y + 8, 1.6, (255, 220, 170))
        anim.sacudir(t0 + 0.08, 3, 0.2)
    else:
        corte(anim, t0, x - 28, y - 34, x + 30, y + 30, 10, (200, 220, 255), 0.2)
        chispazo(anim, t0 + 0.07, x, y, 1.2)
    anim.impacto = t0 + 0.08
    anim.alargar(t0 + 0.5)


def orbe(anim, c):
    # El golpe basico del mago: una bolita de energia.
    t0, o, d = c.t0, c.origen, c.objetivos[0]
    x0, y0 = o.x + 14, o.y - 12
    estela = anim.particulas(rampas[7], freno=2.0)
    ritmo = cadencia(90)

    def lugar(u):
        return x0 + (d.x - x0) * u, y0 + (d.y - y0) * u - 12 * math.sin(math.pi * u)

    def soltar(u, dt):
        x, y = lugar(u)
        for _ in range(ritmo(dt)):
            estela.emitir(x, y, azar.uniform(-15, 15), azar.uniform(-15, 15), 0.25, 2)
    anim.durante(t0, t0 + 0.28, soltar)

    def cuerpo(sup, u):
        x, y = lugar(u)
        disco(sup, x, y, 5, paletas[7][2])
        disco(sup, x, y, 3, blanco)
    anim.trazo(t0, 0.28, cuerpo)
    chispazo(anim, t0 + 0.28, d.x, d.y, 1.0, paletas[7][3])
    anim.impacto = t0 + 0.28
    anim.alargar(t0 + 0.7)


def tajoElemental(anim, c):
    t0, elem = c.t0, c.elem if c.elem is not None else 0
    x, y = puntoDeGolpe(c)
    anim.oscurecer(t0 - 0.1, t0 + 0.85, 110)
    corte(anim, t0, x - 40, y - 46, x + 44, y + 44, 16, paletas[elem][1], 0.24)
    corte(anim, t0 + 0.03, x - 34, y - 38, x + 36, y + 36, 8, paletas[elem][2], 0.22)
    estallido(anim, t0 + 0.1, x, y, elem, 1.5)
    anim.destello(t0 + 0.08, paletas[elem][2], 0.1, 70)
    anim.sacudir(t0 + 0.08, 4, 0.25)
    anim.impacto = t0 + 0.1
    anim.alargar(t0 + 0.85)


def tajoMayor(anim, c):
    # Brilla la espada, dos tajos enormes cruzan al jefe y el corte revienta.
    t0, o, elem = c.t0, c.origen, c.elem if c.elem is not None else 0
    b = c.objetivos[0]
    x, y = b.x - 10, b.y + 8
    fin = t0 + 1.25
    anim.oscurecer(t0 - 0.3, fin, 160)

    def brillo(sup, u):
        estrella(sup, o.x + 22, o.y - 24, 20 * math.sin(math.pi * u), blanco, 4, 0.14, u * 2)
        estrella(sup, o.x + 22, o.y - 24, 12 * math.sin(math.pi * u), paletas[elem][2], 4, 0.3, math.pi / 4 + u * 2)
    anim.trazo(t0 - 0.28, 0.28, brillo)

    corte(anim, t0, x - 70, y - 62, x + 62, y + 66, 22, paletas[elem][1], 0.26)
    corte(anim, t0 + 0.02, x - 62, y - 54, x + 54, y + 58, 10, paletas[elem][2], 0.24)
    corte(anim, t0 + 0.16, x + 70, y - 62, x - 62, y + 66, 22, paletas[elem][1], 0.26)
    corte(anim, t0 + 0.18, x + 62, y - 54, x - 54, y + 58, 10, paletas[elem][2], 0.24)
    anim.destello(t0 + 0.05, blanco, 0.12, 150)
    anim.destello(t0 + 0.34, blanco, 0.2, 215)
    anim.sacudir(t0 + 0.05, 5, 0.2)
    anim.sacudir(t0 + 0.34, 11, 0.6)
    for k, (dx, dy) in enumerate(((-36, -40), (0, 0), (36, 40), (-34, 34), (34, -34))):
        estallido(anim, t0 + 0.36 + 0.05 * k, x + dx, y + dy, elem, 1.5)
    anilloDeChoque(anim, t0 + 0.36, x, y, 120, paletas[elem][2], 0.5, 1.0, 3)
    anim.impacto = t0 + 0.36
    anim.alargar(fin)


def punaladaVeloz(anim, c):
    t0 = c.t0
    x, y = puntoDeGolpe(c)
    for k, dy in enumerate((-14, 10, -2)):
        def estocada(sup, u, dy=dy):
            largo = 70 * min(1.0, u * 3)
            brillo = 1 - u
            pygame.draw.line(sup, atenuar((150, 190, 255), brillo), (x - 60, y + dy), (x - 60 + largo, y + dy), 3)
            pygame.draw.line(sup, atenuar(blanco, brillo), (x - 50, y + dy), (x - 60 + largo, y + dy), 1)
        anim.trazo(t0 + 0.06 * k, 0.16, estocada)
        chispazo(anim, t0 + 0.05 + 0.06 * k, x + 6, y + dy, 0.8)
    anim.impacto = t0 + 0.12
    anim.alargar(t0 + 0.6)


def golpeSombra(anim, c):
    # Una sombra atraviesa al jefe y un instante despues aparecen los cortes.
    t0 = c.t0
    b = c.objetivos[0]
    x, y = b.x - 6, b.y + 10
    fin = t0 + 1.0
    anim.oscurecer(t0 - 0.1, fin, 170)

    def sombra(sup, u):
        frente = x - 90 + 190 * suave(u)
        alfa = int(230 * (1 - u))
        pygame.draw.polygon(sup, (10, 4, 22, alfa), [(frente - 80, y - 3), (frente, y - 9), (frente + 14, y), (frente, y + 9), (frente - 80, y + 3)])
    anim.trazo(t0, 0.22, sombra, "frente")
    anim.trazo(t0, 0.22, lambda sup, u: pygame.draw.line(sup, atenuar(paletas[7][2], 1 - u), (x - 90, y), (x - 90 + 190 * suave(u), y), 1))

    for k, giro in enumerate((0.3, 1.5, 2.6, 0.9)):
        corte(anim, t0 + 0.24, x - 40 * math.cos(giro), y - 40 * math.sin(giro), x + 40 * math.cos(giro),
              y + 40 * math.sin(giro), 8, paletas[7][2], 0.2)
    estallido(anim, t0 + 0.28, x, y, 7, 1.6)
    anim.destello(t0 + 0.24, paletas[7][3], 0.1, 90)
    anim.sacudir(t0 + 0.26, 5, 0.3)
    anim.impacto = t0 + 0.28
    anim.alargar(fin)


def furiaDesatada(anim, c):
    # Una lluvia de hachazos rojos que termina en cruz.
    t0, o = c.t0, c.origen
    x, y = puntoDeGolpe(c)
    fin = t0 + 1.2
    anim.oscurecer(t0 - 0.1, fin, 140)
    anim.tinte(t0, fin - 0.2, (200, 20, 10), 40, 0.1, 0.3)
    auraDeFuego(anim, t0 - 0.15, t0 + 0.6, o, (255, 90, 40))
    for k in range(6):
        giro = azar.uniform(0, math.tau)
        px, py = x + azar.uniform(-22, 22), y + azar.uniform(-26, 26)
        corte(anim, t0 + 0.07 * k, px - 30 * math.cos(giro), py - 30 * math.sin(giro), px + 30 * math.cos(giro),
              py + 30 * math.sin(giro), 9, (255, 120, 60), 0.16)
        chispazo(anim, t0 + 0.05 + 0.07 * k, px, py, 0.9, (255, 200, 150))
        anim.sacudir(t0 + 0.05 + 0.07 * k, 2, 0.08)
    tFinal = t0 + 0.5
    corte(anim, tFinal, x - 52, y - 50, x + 50, y + 52, 18, (255, 90, 40), 0.24)
    corte(anim, tFinal + 0.04, x + 52, y - 50, x - 50, y + 52, 18, (255, 90, 40), 0.24)
    estallido(anim, tFinal + 0.1, x, y, 0, 1.8)
    anim.destello(tFinal + 0.08, (255, 220, 180), 0.14, 150)
    anim.sacudir(tFinal + 0.08, 9, 0.45)
    anim.impacto = tFinal + 0.1
    anim.alargar(fin)


def auraDeFuego(anim, inicio, fin, lugar, color):
    # Llamas que suben alrededor de un personaje.
    rampa = [mezclar(color, blanco, 0.7), mezclar(color, blanco, 0.3), color, atenuar(color, 0.6), atenuar(color, 0.25)]
    llamas = anim.particulas(rampa, gravedad=-150, freno=1.0)
    ritmo = cadencia(130)

    def subir(u, dt):
        for _ in range(ritmo(dt)):
            llamas.emitir(lugar.x + azar.uniform(-14, 14), lugar.piso - azar.uniform(0, 8), azar.uniform(-10, 10),
                          -azar.uniform(40, 110), azar.uniform(0.3, 0.55), azar.choice((2, 3, 4)))
    anim.durante(inicio, fin, subir)


conjurosMedianos = {"Llama", "Oleaje", "Remolino", "Roca", "Zarza", "Relampago", "Fulgor", "Sombra"}


def conjuroDeMago(anim, c):
    # Los conjuros chicos y medianos del mago: su dibujo vuela dejando estela,
    # y los medianos van escoltados por dos chispas y pegan mas fuerte.
    t0, o, d = c.t0, c.origen, c.objetivos[0]
    mediano = c.nombre in conjurosMedianos
    imagen = icono(c.nombre)
    x0, y0 = o.x + 14, o.y - 14
    duracion = 0.32
    anim.oscurecer(t0 - 0.1, t0 + 0.9, 110 if mediano else 80)
    estela = anim.particulas(rampas[c.elem], freno=2.0)
    ritmo = cadencia(170 if mediano else 110)
    fogonazo(anim, t0, x0, y0, 12 if mediano else 8, paletas[c.elem][2], 0.18)

    def lugar(u):
        return x0 + (d.x - x0) * u, y0 + (d.y - y0) * u - 18 * math.sin(math.pi * u)

    def soltar(u, dt):
        x, y = lugar(u)
        for _ in range(ritmo(dt)):
            estela.emitir(x + azar.uniform(-3, 3), y + azar.uniform(-3, 3), azar.uniform(-22, 22), azar.uniform(-22, 22), 0.32,
                          azar.choice((2, 3, 4) if mediano else (2, 3)))
    anim.durante(t0, t0 + duracion, soltar)

    def cuerpo(sup, u):
        x, y = lugar(u)
        if imagen is not None:
            sup.blit(imagen, imagen.get_rect(center=(int(x), int(y))))
    anim.trazo(t0, duracion, cuerpo, "frente")

    def halo(sup, u):
        x, y = lugar(u)
        disco(sup, x, y, 13 if mediano else 9, atenuar(paletas[c.elem][1], 0.45))
        if mediano:
            for lado in (0, math.pi):
                a = u * 16 + lado
                disco(sup, x + 15 * math.cos(a), y + 9 * math.sin(a), 2, paletas[c.elem][3])
    anim.trazo(t0, duracion, halo)

    estallido(anim, t0 + duracion, d.x, d.y, c.elem, 1.7 if mediano else 1.1)
    if mediano:
        anilloDeChoque(anim, t0 + duracion, d.x, d.y, 44, paletas[c.elem][2], 0.35, 1.0, 2)
        anim.sacudir(t0 + duracion, 3, 0.25)
        anim.destello(t0 + duracion, paletas[c.elem][2], 0.1, 60)
    anim.impacto = t0 + duracion
    anim.alargar(t0 + 0.95)


def sanacion(anim, t, lugar, fuerza=1.0):
    # Luz verde que sube alrededor de quien recibe la cura.
    verde = [(245, 255, 235), (190, 255, 170), (110, 230, 120), (50, 150, 70), (20, 70, 30)]
    motas = anim.particulas(verde, gravedad=-90, freno=0.8)
    ritmo = cadencia(90 * fuerza)

    def subir(u, dt):
        for _ in range(ritmo(dt)):
            motas.emitir(lugar.x + azar.uniform(-18, 18), lugar.piso - azar.uniform(0, 40), azar.uniform(-8, 8),
                         -azar.uniform(20, 70), azar.uniform(0.5, 0.8), 2)
    anim.durante(t, t + 0.6, subir)

    for k in range(2 + int(fuerza)):
        def aro(sup, u, k=k):
            y = lugar.piso - 56 * u
            anillo(sup, lugar.x, y, 20 - 6 * u, atenuar((150, 255, 160), math.sin(math.pi * u)), 2, 0.3)
        anim.trazo(t + 0.14 * k, 0.5, aro)

    def cruces(sup, u):
        for k in range(3):
            fase = (u + k / 3) % 1.0
            x = lugar.x + (k - 1) * 16
            y = lugar.y + 6 - 34 * fase
            tam = 5 * math.sin(math.pi * fase) * fuerza
            if tam > 1:
                pygame.draw.rect(sup, (220, 255, 210), (int(x - 1), int(y - tam), 2, int(tam * 2)))
                pygame.draw.rect(sup, (220, 255, 210), (int(x - tam), int(y - 1), int(tam * 2), 2))
    anim.trazo(t, 0.75, cruces)
    if fuerza > 1.2:
        def pilar(sup, u):
            ancho = 16 * math.sin(math.pi * u)
            pygame.draw.rect(sup, (30, 80, 40), (int(lugar.x - ancho), 0, int(ancho * 2), int(lugar.piso)))
            pygame.draw.rect(sup, (90, 190, 110), (int(lugar.x - ancho * 0.5), 0, max(1, int(ancho)), int(lugar.piso)))
        anim.trazo(t, 0.6, pilar)
        anilloDeChoque(anim, t + 0.1, lugar.x, lugar.piso, 40, (150, 255, 160), 0.4, 0.35)


def escudoDeLuz(anim, t, lugar, color, duracion=0.7, grande=False):
    # El contorno de un escudo que aparece frente al personaje, brilla y se apaga.
    tam = 30 if grande else 22

    def dibujar(sup, u):
        crece = min(1.0, u / 0.2)
        brillo = 1.0 if u < 0.55 else (1 - u) / 0.45
        ancho, alto = tam * crece, tam * 1.25 * crece
        x, y = lugar.x, lugar.y - 2
        forma = [(x - ancho, y - alto), (x + ancho, y - alto), (x + ancho, y + alto * 0.2), (x, y + alto), (x - ancho, y + alto * 0.2)]
        pygame.draw.polygon(sup, atenuar(color, 0.28 * brillo), forma)
        pygame.draw.polygon(sup, atenuar(color, brillo), forma, 2)
        # Un reflejo que lo recorre de lado a lado.
        paso = x - ancho + 2 * ancho * ((u * 2.2) % 1.0)
        pygame.draw.line(sup, atenuar(blanco, brillo), (paso, y - alto), (paso - 6, y + alto * 0.2), 2)
    anim.trazo(t, duracion, dibujar)
    motas = anim.particulas([mezclar(color, blanco, 0.6), color, atenuar(color, 0.6), atenuar(color, 0.3)], gravedad=-80, freno=1.0)
    anim.en(t + 0.1, lambda: motas.rafaga(lugar.x, lugar.piso - 6, 16, 60, 0.6, 2, -math.pi / 2, math.pi, 12))
    anilloDeChoque(anim, t, lugar.x, lugar.piso, 28, color, 0.35, 0.35)


def cupula(anim, t, lugar, color, duracion=0.9):
    # Una cupula que se cierra sobre el personaje: el bloqueo total.
    def dibujar(sup, u):
        crece = min(1.0, u / 0.25)
        brillo = 1.0 if u < 0.6 else (1 - u) / 0.4
        radio = 30 * crece
        rect = (int(lugar.x - radio), int(lugar.piso - radio * 1.5), int(radio * 2), int(radio * 3))
        if radio > 4:
            pygame.draw.arc(sup, atenuar(color, brillo), rect, 0, math.pi, 3)
            for k in (-0.6, 0, 0.6):
                costilla = (int(lugar.x - radio * abs(k) - 2), rect[1], int(radio * 2 * abs(k)) + 4, rect[3])
                pygame.draw.arc(sup, atenuar(color, 0.6 * brillo), costilla, 0, math.pi, 1)
            anillo(sup, lugar.x, lugar.piso, radio, atenuar(color, brillo), 2, 0.3)
            estrella(sup, lugar.x - radio * 0.5, lugar.piso - radio * 1.1, 8 * math.sin(math.pi * min(1.0, u * 2)), blanco, 4, 0.2)
    anim.trazo(t, duracion, dibujar)
    motas = anim.particulas([blanco, (255, 240, 170), color, atenuar(color, 0.5)], gravedad=-70, freno=1.0)
    anim.en(t + 0.15, lambda: motas.rafaga(lugar.x, lugar.piso - 10, 24, 80, 0.7, 2, -math.pi / 2, math.pi * 1.2, 14))


def lanzarFrasco(anim, t, desde, hasta, color, duracion):
    def lugar(u):
        x = desde.x + (hasta.x - desde.x) * u
        y = desde.y - 10 + (hasta.y - desde.y) * u - 70 * math.sin(math.pi * u)
        return x, y

    def frasco(sup, u):
        x, y = lugar(u)
        disco(sup, x, y, 5, color)
        disco(sup, x, y - 1, 2, blanco)
    anim.trazo(t, duracion, frasco, "frente")
    anim.trazo(t, duracion, lambda sup, u: disco(sup, *lugar(u), 10, atenuar(color, 0.35)))


def burbujas(anim, t, lugar, color):
    # Lo que se ve al beber una pocion.
    rampa = [mezclar(color, blanco, 0.7), color, atenuar(color, 0.7), atenuar(color, 0.35)]
    motas = anim.particulas(rampa, gravedad=-60, freno=0.6, encoge=False)
    ritmo = cadencia(60)

    def subir(u, dt):
        for _ in range(ritmo(dt)):
            motas.emitir(lugar.x + azar.uniform(-14, 14), lugar.y + azar.uniform(-4, 22), azar.uniform(-10, 10),
                         -azar.uniform(20, 60), 0.6, azar.choice((2, 3)))
    anim.durante(t, t + 0.5, subir)
    anim.trazo(t + 0.15, 0.35, lambda sup, u: estrella(sup, lugar.x + 8, lugar.y - 18, 9 * math.sin(math.pi * u), blanco, 4, 0.2, u))
    anilloDeChoque(anim, t, lugar.x, lugar.piso, 22, color, 0.35, 0.35)


def cargar(anim, c, elem):
    # El jefe junta energia para el ataque que va a soltar el turno que sigue.
    o = c.origen
    bx, by = o.x - 30, o.y - 10
    color = paletas[elem][1] if elem is not None else (200, 150, 255)
    rampa = list(reversed(rampas[elem])) if elem is not None else [(40, 20, 70), (90, 50, 150), (150, 100, 230), (210, 180, 255), blanco]
    fin = 1.15
    anim.oscurecer(0.0, fin, 110)
    anim.sacudir(0.1, 2, 0.9)
    chispas = anim.rayas(rampa, largo=0.05)
    ritmo = cadencia(170)

    def juntar(u, dt):
        for _ in range(ritmo(dt)):
            a, r = azar.uniform(0, math.tau), azar.uniform(70, 130)
            vida = azar.uniform(0.3, 0.45)
            chispas.emitir(bx + r * math.cos(a), by + r * math.sin(a), -r * math.cos(a) / vida, -r * math.sin(a) / vida, vida, 1)
    anim.durante(0.05, 0.9, juntar)

    def nucleo(sup, u):
        r = 5 + 13 * u + 2 * math.sin(u * 50)
        disco(sup, bx, by, r * 1.6, atenuar(color, 0.35))
        disco(sup, bx, by, r, atenuar(color, 0.8))
        estrella(sup, bx, by, r * 1.5, blanco, 4, 0.16, u * 5)
    anim.trazo(0.05, 0.95, nucleo)
    for k in range(3):
        def aro(sup, u):
            anillo(sup, bx, by, 90 * (1 - u), atenuar(color, u), 2)
        anim.trazo(0.1 + 0.25 * k, 0.4, aro)
    anim.destello(0.95, mezclar(color, blanco, 0.5), 0.15, 110)
    anilloDeChoque(anim, 0.95, bx, by, 70, color, 0.3, 1.0, 2)
    anim.alargar(fin)


recetas = {
    "Cataclismo": cataclismo, "Rayo final": rayoFinal, "Devastacion": devastacion, "Aplastamiento": aplastamiento,
    "Infierno": infierno, "Diluvio": diluvio, "Huracan": huracan, "Sismo": sismo, "Selva viva": selvaViva,
    "Tormenta electrica": tormentaElectrica, "Juicio": juicio, "Abismo": abismo,
    "Incendio": incendio, "Marejada": marejada, "Vendaval": vendaval, "Avalancha": avalancha, "Enredadera": enredaderas,
    "Tormenta": tormenta, "Resplandor": resplandor, "Eclipse": eclipse,
    "Terremoto": terremoto, "Onda de choque": ondaDeChoque, "Barrido": barrido, "Estampida": estampida,
    "Llamarada": llamarada, "Chorro": chorro, "Rafaga": rafaga, "Lanza de roca": lanzaDeRoca, "Espinas": espinas,
    "Descarga": descarga, "Rayo de luz": rayoDeLuz, "Garra sombria": garraSombria,
    "Zarpazo": zarpazo, "Garra doble": garraDoble, "Mordida": mordida, "Coletazo": coletazo, "Pisoton": pisoton,
    "Embestida": embestida, "Cabezazo": cabezazo, "Golpe pesado": golpePesado,
    "Ataque basico": ataqueBasico, "Tajo elemental": tajoElemental, "Tajo mayor": tajoMayor,
    "Punalada veloz": punaladaVeloz, "Golpe sombra": golpeSombra, "Furia desatada": furiaDesatada,
}
for conjuro in m.conjurosMago:
    recetas[conjuro["nombre"]] = conjuroDeMago

elementoDeAtaque = {a["nombre"]: a["elem"] for a in m.HABILIDADES}
colorDeMejora = {"Guardia de acero": (120, 190, 255), "Muralla": (120, 190, 255)}


# Lo que suena en cada ataque ademas de lo que ya ponen sus piezas (los tajos,
# los rayos, las explosiones y los estallidos de cada elemento suenan solos).
# Cada entrada es (segundos desde que suelta el ataque, sonido, volumen).
sonidosDeAtaque = {
    "Cataclismo": [(-0.1, "jefe_rugido", 0.9), (0.4, "temblor", 0.8)],
    "Rayo final": [(-0.05, "carga", 0.8)],
    "Devastacion": [(-0.1, "jefe_rugido", 0.8), (0.0, "temblor", 1.0)],
    "Aplastamiento": [(0.0, "oscuridad", 0.7), (0.6, "espadazo", 1.0), (0.6, "temblor", 0.9)],
    "Infierno": [(0.0, "magia", 0.8), (0.35, "fuego", 1.0), (0.7, "fuego", 0.8), (1.0, "fuego", 0.8)],
    "Diluvio": [(0.0, "ola", 0.6), (0.6, "agua", 1.0), (0.65, "ola", 0.9)],
    "Huracan": [(0.0, "viento", 0.8), (0.35, "viento", 1.0), (0.9, "viento", 1.0)],
    "Sismo": [(0.0, "temblor", 0.9), (0.45, "tierra", 1.0)],
    "Selva viva": [(0.0, "planta", 0.8), (0.3, "planta", 0.8)],
    "Tormenta electrica": [(0.0, "trueno", 0.6), (1.3, "trueno", 1.0)],
    "Juicio": [(0.0, "luz", 0.8), (1.2, "destello", 1.0)],
    "Abismo": [(0.0, "zumbido", 0.6), (1.3, "oscuridad", 1.0)],
    "Incendio": [(0.0, "fuego", 1.0)], "Marejada": [(0.0, "ola", 1.0)], "Vendaval": [(0.0, "viento", 1.0)],
    "Avalancha": [(0.0, "temblor", 0.6)], "Tormenta": [(0.3, "trueno", 0.8)], "Resplandor": [(0.0, "luz", 1.0)],
    "Eclipse": [(0.0, "oscuridad", 1.0)], "Terremoto": [(0.0, "temblor", 1.0)],
    "Onda de choque": [(0.0, "golpeSeco", 1.0), (0.0, "temblor", 0.5)], "Estampida": [(0.0, "temblor", 0.7)],
    "Golpe pesado": [(0.0, "golpeSeco", 1.0)], "Pisoton": [(0.0, "golpeSeco", 1.0)], "Mordida": [(0.12, "golpe", 1.0)],
    "Llamarada": [(0.0, "fuego", 0.9)], "Chorro": [(0.0, "agua", 0.9)], "Rafaga": [(0.0, "viento", 0.8)],
    "Lanza de roca": [(0.0, "lanzar", 0.6)], "Descarga": [(0.0, "rayo", 0.9)], "Rayo de luz": [(0.0, "luz", 0.9)],
    "Garra sombria": [(0.0, "oscuridad", 0.7)],
    "Tajo mayor": [(-0.28, "destello", 0.5), (0.34, "espadazo", 1.0)], "Tajo elemental": [(0.08, "espadazo", 0.9)],
    "Furia desatada": [(0.5, "espadazo", 1.0)], "Golpe sombra": [(0.0, "oscuridad", 0.6)],
}


def crearAnimacion(c, esFisico):
    # Devuelve la animacion de un ataque ya armada, con su momento de impacto.
    anim = Animacion()
    receta = recetas.get(c.nombre)
    if receta is None:
        receta = golpe if esFisico else proyectil
    receta(anim, c)
    for momento, nombre, volumen in sonidosDeAtaque.get(c.nombre, ()):
        anim.sonido(max(0.0, c.t0 + momento), nombre, volumen)
    if receta in (conjuroDeMago, proyectil):
        anim.sonido(c.t0, "lanzar", 0.7)
    return anim


def crearApoyo(c):
    # Las acciones que no pegan: curas, mejoras, bloqueos, pociones y cargas.
    anim = Animacion()
    nombre, yo = c.nombre, c.origen
    if nombre.startswith("Carga "):
        cargar(anim, c, elementoDeAtaque.get(nombre[6:]))
        anim.sonido(0.0, "carga", 0.9)
        anim.sonido(0.05, "jefe_risa", 0.7)
    elif nombre == "Bloquea":
        escudoDeLuz(anim, 0.0, yo, (200, 205, 220), 0.6)
        anim.sonido(0.05, "bloqueo", 0.7)
    elif nombre in colorDeMejora:
        escudoDeLuz(anim, 0.0, yo, colorDeMejora[nombre], 0.8, True)
        anim.sonido(0.0, "escudo", 0.9)
    elif nombre == "Bloqueo total":
        cupula(anim, 0.0, yo, (255, 215, 110))
        anim.sonido(0.0, "escudo", 1.0)
    elif nombre == "Furia":
        anim.sonido(0.0, "furia", 1.0)
        auraDeFuego(anim, 0.0, 0.7, yo, (255, 90, 40))
        anilloDeChoque(anim, 0.05, yo.x, yo.piso, 34, (255, 120, 60), 0.4, 0.35)
        anim.trazo(0.1, 0.4, lambda sup, u: estrella(sup, yo.x, yo.y - 30, 12 * math.sin(math.pi * u), (255, 200, 150), 4, 0.2, u * 2))
        anim.alargar(0.9)
    elif nombre.startswith("Bebe "):
        anim.sonido(0.0, "pocion", 0.9)
        burbujas(anim, 0.0, yo, (120, 230, 130) if "vida" in nombre else (110, 170, 255))
    elif nombre.startswith("Le da a ") and c.objetivos:
        # Le avienta la poción a un aliado: el frasco hace un arco y revienta
        # en burbujas sobre quien la recibe.
        color = (120, 230, 130) if "vida" in nombre else (110, 170, 255)
        destino = c.objetivos[0]
        lanzarFrasco(anim, 0.0, yo, destino, color, 0.4)
        anim.sonido(0.38, "pocion", 0.9)
        burbujas(anim, 0.4, destino, color)
        anim.impacto = 0.45
        return anim
    elif nombre == "Curacion en grupo":
        anilloDeChoque(anim, 0.0, yo.x, yo.piso, 260, (150, 255, 160), 0.6, 0.4, 3)
        anim.destello(0.05, (190, 255, 190), 0.15, 60)
        for k, lugar in enumerate(c.objetivos):
            sanacion(anim, 0.12 + 0.05 * k, lugar, 1.0)
    elif c.objetivos:
        sanacion(anim, 0.05, c.objetivos[0], 1.6 if nombre == "Curacion mayor" else 1.0)
    else:
        return None
    anim.impacto = 0.25 if c.objetivos else 0.0
    return anim


def detallesDelGolpe(anim, impacto, notas):
    # Lo que se agrega a cualquier ataque segun como salio: un critico sacude
    # la pantalla y un bloqueo total enciende una cupula sobre el heroe.
    for lugar, nota in notas:
        if nota == "critico":
            anim.sacudir(impacto, 5, 0.22)
            anim.destello(impacto, blanco, 0.08, 70)
            anilloDeChoque(anim, impacto, lugar.x, lugar.y, 36, blanco, 0.25, 1.0, 2)
        elif nota == "bloqueado":
            cupula(anim, impacto - 0.05, lugar, (255, 215, 110), 0.6)


def caidaDeHeroe(lugar):
    # Cuando un heroe cae: polvo a sus pies y unas luces que se van hacia arriba.
    anim = Animacion()
    polvareda(anim, 0.0, lugar.x, lugar.piso, 1.2)
    almas = anim.particulas([(255, 255, 255), (200, 220, 255), (130, 160, 230), (60, 80, 150), (20, 30, 70)], gravedad=-70, freno=0.6)
    ritmo = cadencia(40)

    def subir(u, dt):
        for _ in range(ritmo(dt)):
            almas.emitir(lugar.x + azar.uniform(-16, 16), lugar.piso - azar.uniform(0, 14), azar.uniform(-8, 8), -azar.uniform(20, 60), 0.9, 2)
    anim.durante(0.05, 0.7, subir)
    anim.alargar(1.5)
    return anim


def derrotaDelJefe(lugar, fase2):
    # El jefe vencido: estallidos por todo su cuerpo, la pantalla tiembla y al
    # final una onda de luz.
    anim = Animacion()
    color = (255, 210, 110) if fase2 else (190, 110, 255)
    anim.sonido(0.0, "jefe_muerte", 1.0)
    for k in (2, 5, 8, 10):
        anim.sonido(0.12 * k, "explosion", 0.6)
    anim.sonido(1.45, "cambio_de_fase", 1.0)
    anim.oscurecer(0.0, 2.3, 120)
    anim.sacudir(0.0, 5, 1.5)
    for k in range(11):
        t = 0.12 * k
        x, y = lugar.x + azar.uniform(-55, 55), lugar.y + azar.uniform(-55, 60)
        fogonazo(anim, t, x, y, azar.uniform(16, 28), color, 0.3)
        chispazo(anim, t, x, y, 1.6, color)
        anilloDeChoque(anim, t, x, y, 34, blanco, 0.3, 1.0, 2)
        if k % 3 == 0:
            anim.destello(t, blanco, 0.08, 90)
    tFinal = 1.45

    def rayos(sup, u):
        brillo = math.sin(math.pi * u)
        for k in range(10):
            a = k * math.tau / 10 + u * 0.8
            punta = (lugar.x + 260 * math.cos(a), lugar.y + 260 * math.sin(a))
            lado = (lugar.x + 10 * math.cos(a + 1.5), lugar.y + 10 * math.sin(a + 1.5))
            otro = (lugar.x + 10 * math.cos(a - 1.5), lugar.y + 10 * math.sin(a - 1.5))
            pygame.draw.polygon(sup, atenuar(color, 0.5 * brillo), [lado, punta, otro])
    anim.trazo(tFinal - 0.3, 1.0, rayos)
    anim.destello(tFinal, blanco, 0.35, 240)
    anim.sacudir(tFinal, 12, 0.6)
    for k in range(3):
        anilloDeChoque(anim, tFinal + 0.08 * k, lugar.x, lugar.y, 260, color if k else blanco, 0.7, 1.0, 4 - k)
    motas = anim.particulas([blanco, mezclar(color, blanco, 0.5), color, atenuar(color, 0.6), atenuar(color, 0.25)], gravedad=-30, freno=0.8)
    anim.en(tFinal, lambda: motas.rafaga(lugar.x, lugar.y, 120, 260, 1.3, 3, dispersion=30))
    # Mientras se deshace, su cuerpo se va en motas de luz hacia arriba.
    polvo = anim.particulas([blanco, mezclar(color, blanco, 0.6), color, atenuar(color, 0.5)], gravedad=-90, freno=0.5)
    ritmo = cadencia(260)

    def deshacer(u, dt):
        alto = 150 * (1 - 0.35 * u)
        for _ in range(ritmo(dt)):
            polvo.emitir(lugar.x + azar.uniform(-70, 70), lugar.piso - azar.uniform(0, alto), azar.uniform(-15, 15),
                         -azar.uniform(20, 80), azar.uniform(0.6, 1.1), azar.choice((1, 2, 2, 3)))
    anim.durante(tFinal, tFinal + 1.15, deshacer)
    anim.alargar(2.8)
    return anim


def transformacion(lugar, duracion):
    # El cambio de fase: el jefe se traga la luz, a la mitad estalla y queda
    # rodeado de plumas y de luz dorada.
    anim = Animacion()
    mitad = duracion / 2
    morado, dorado = (190, 110, 255), (255, 210, 110)
    anim.oscurecer(0.0, duracion + 0.3, 150)
    tragadas = anim.rayas([(40, 20, 70), (90, 50, 150), (150, 100, 230), (210, 180, 255), blanco], largo=0.05)
    ritmo = cadencia(230)

    def tragar(u, dt):
        for _ in range(ritmo(dt)):
            a, r = azar.uniform(0, math.tau), azar.uniform(90, 190)
            vida = azar.uniform(0.3, 0.5)
            tragadas.emitir(lugar.x + r * math.cos(a), lugar.y + r * 0.8 * math.sin(a), -r * math.cos(a) / vida,
                            -r * 0.8 * math.sin(a) / vida, vida, 1)
    anim.durante(0.0, mitad - 0.1, tragar)
    for k in range(6):
        a = azar.uniform(0, math.tau)
        relampago(anim, 0.15 + 0.11 * k, lugar.x, lugar.y, lugar.x + 120 * math.cos(a), lugar.y + 90 * math.sin(a), morado, 0.14, 1, 10, 1)

    def pilar(sup, u):
        ancho = 46 * math.sin(math.pi * u)
        if ancho > 1:
            for factor, tono in ((1.0, (80, 62, 26)), (0.6, (190, 150, 70)), (0.25, (255, 245, 210))):
                pygame.draw.rect(sup, tono, (int(lugar.x - ancho * factor), 0, max(1, int(ancho * factor * 2)), int(lugar.piso + 6)))
    anim.trazo(mitad - 0.05, 0.7, pilar)
    for k in range(3):
        anilloDeChoque(anim, mitad + 0.1 * k, lugar.x, lugar.y, 300, dorado if k else blanco, 0.7, 1.0, 4 - k)
        anilloDeChoque(anim, mitad + 0.1 * k, lugar.x, lugar.piso, 240, dorado, 0.7, 0.35, 2)

    plumas = anim.particulas([(255, 235, 150, 255), (240, 200, 100, 255), (60, 40, 70, 255), (40, 26, 50, 200)], capa="frente",
                             gravedad=40, freno=1.6, encoge=False)
    motas = anim.particulas([blanco, (255, 240, 170), dorado, (160, 120, 40), (60, 40, 10)], gravedad=-50, freno=0.8)
    anim.en(mitad, lambda: (plumas.rafaga(lugar.x, lugar.y, 60, 260, 1.4, 3, dispersion=20),
                            motas.rafaga(lugar.x, lugar.y, 90, 220, 1.0, 2, dispersion=20)))
    ritmoMotas = cadencia(80)

    def brillar(u, dt):
        for _ in range(ritmoMotas(dt)):
            motas.emitir(lugar.x + azar.uniform(-80, 80), lugar.piso - azar.uniform(0, 150), azar.uniform(-10, 10), -azar.uniform(20, 70), 0.8, 2)
    anim.durante(mitad, duracion, brillar)
    anim.tinte(mitad, duracion + 0.3, (255, 220, 120), 35, 0.1, 0.4)
    anim.alargar(duracion + 0.4)
    return anim


def crearAmbiente(leer):
    # Lo que se mueve en la arena aunque nadie ataque: motas de luz que
    # flotan, el aura del jefe mientras carga un ataque y el confeti de la
    # victoria. leer() dice en que fase va el combate, donde esta el jefe, si
    # esta cargando (y de que elemento) y si el equipo ya gano.
    anim = Animacion()
    anim.duracion = float("inf")
    moradas = anim.particulas([(30, 16, 54), (90, 56, 150), (190, 150, 250), (90, 56, 150), (30, 16, 54)], gravedad=-4, encoge=False)
    doradas = anim.particulas([(50, 40, 14), (150, 120, 50), (255, 235, 150), (150, 120, 50), (50, 40, 14)], gravedad=-6, encoge=False)
    confeti = anim.particulas([(255, 220, 90, 255), (255, 120, 120, 255), (120, 200, 255, 255), (150, 235, 140, 255)], capa="frente",
                              gravedad=30, freno=1.2, encoge=False)
    auras = {}
    ritmo, ritmoAura, ritmoConfeti = cadencia(9), cadencia(90), cadencia(45)

    def mover(u, dt):
        estado = leer()
        grupo = doradas if estado["fase2"] else moradas
        for _ in range(ritmo(dt)):
            grupo.emitir(azar.uniform(0, anchoCapa), azar.uniform(50, altoCapa), azar.uniform(-5, 5), -azar.uniform(3, 12),
                         azar.uniform(2.0, 4.0), azar.choice((1, 1, 2)))
        if estado["carga"] is not False:
            elem = estado["carga"]
            if elem not in auras:
                rampa = rampas[elem] if elem is not None else [blanco, (220, 190, 255), (170, 110, 250), (90, 50, 160), (40, 20, 70)]
                auras[elem] = anim.particulas(rampa, gravedad=-120, freno=0.8)
            jefe = estado["jefe"]
            for _ in range(ritmoAura(dt)):
                auras[elem].emitir(jefe.x + azar.uniform(-60, 60), jefe.piso - azar.uniform(0, 20), azar.uniform(-8, 8),
                                   -azar.uniform(30, 120), azar.uniform(0.5, 0.9), azar.choice((2, 3)))
        if estado["fiesta"]:
            for _ in range(ritmoConfeti(dt)):
                confeti.emitir(azar.uniform(0, anchoCapa), -4, azar.uniform(-30, 30), azar.uniform(40, 90), azar.uniform(2.0, 3.2), azar.choice((2, 3)))
    anim.durante(0.0, float("inf"), mover)
    return anim


def previaTransformacion(lugar, duracion):
    # Lo que pasa en la arena antes del corte a la cinematica: el jefe junta
    # energia, caen rayos a su alrededor y la pantalla destella cada vez mas.
    anim = Animacion()
    morado = (190, 110, 255)
    anim.oscurecer(0.0, duracion + 0.2, 140)
    anim.tinte(0.3, duracion + 0.2, (90, 30, 150), 50, 0.6, 0.1)
    tragadas = anim.rayas([(40, 20, 70), (90, 50, 150), (150, 100, 230), (210, 180, 255), blanco], largo=0.05)
    ritmo = cadencia(160)

    def tragar(u, dt):
        for _ in range(ritmo(dt) + int(u * 3)):
            a, r = azar.uniform(0, math.tau), azar.uniform(90, 180)
            vida = azar.uniform(0.3, 0.5)
            tragadas.emitir(lugar.x + r * math.cos(a), lugar.y + r * 0.8 * math.sin(a), -r * math.cos(a) / vida,
                            -r * 0.8 * math.sin(a) / vida, vida, 1)
    anim.durante(0.0, duracion, tragar)

    momentos = [0.35, 0.8, 1.15, 1.45, 1.7, 1.9, 2.05, 2.2, 2.32, 2.44]
    for k, t in enumerate(m for m in momentos if m < duracion):
        x = lugar.x + azar.uniform(-130, 130)
        relampago(anim, t, x + azar.uniform(-30, 30), 0, x, lugar.piso + azar.uniform(-20, 20), morado if k % 2 else paletas[5][1],
                  0.16, 2 + k // 4, 12, 2)
        anim.destello(t, (235, 225, 255), 0.08, 60 + 12 * k)
        anim.sonido(t, "trueno" if k % 3 == 0 else "rayo", 0.6)

    def aura(sup, u):
        r = 60 + 40 * u + 8 * math.sin(u * 60)
        anillo(sup, lugar.x, lugar.y, r, atenuar(morado, 0.4 + 0.6 * u), 3)
        anillo(sup, lugar.x, lugar.y, r * 0.7, atenuar(paletas[7][3], 0.3 + 0.5 * u), 2)
    anim.trazo(0.0, duracion, aura)
    anim.alargar(duracion)
    return anim
