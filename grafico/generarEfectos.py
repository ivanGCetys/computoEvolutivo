# Genera el arte de los efectos de ataque en recursos/efectos.
#
# Cada efecto se dibuja en una rejilla de 28 x 28 y se guarda al doble, a los
# 56 x 56 con los que se dibuja en el juego, para que sea pixel art del mismo
# grueso que los heroes. Se arma con figuras simples rellenas con la paleta
# de su elemento y al final se le pone un contorno oscuro de un pixel.
#
# Los conjuros tienen un motivo por elemento (llama, gota, remolino, roca,
# hoja, rayo, estrella y orbe), salvo unos pocos con forma propia, y su tamano crece con su poder: los chicos del
# mago, los medianos, los del jefe y los poderosos, que ademas llevan un
# anillo de chispas. Los que pegan en area repiten el motivo en un grupo. Los
# ataques fisicos son zarpazos, tajos, mordidas o impactos.
#
# Todos se dibujan mirando a la derecha; el juego los voltea cuando viajan
# hacia la izquierda.
#
# Uso: python -m grafico.generarEfectos
import math
import os

from PIL import Image, ImageDraw

import motor as m
from grafico.recursos import nombreDeArchivo
from grafico.recetas import paletas

carpetaEfectos = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recursos", "efectos")
lado = 28

paletaCorte = [(40, 40, 60), (170, 180, 205), (225, 232, 245), (255, 255, 255)]
paletaImpacto = [(90, 40, 20), (240, 150, 50), (255, 220, 120), (255, 255, 230)]
paletaFase = [(60, 20, 70), (190, 110, 255), (255, 210, 110), (255, 250, 235)]


def puntos(lista, escala, centro=(14, 14)):
    cx, cy = centro
    return [(cx + (x - 14) * escala, cy + (y - 14) * escala) for x, y in lista]


# Cada motivo dibuja con los tonos 1 a 3 de la paleta; el contorno se pone al final.
def llama(d, p, s, c):
    d.polygon(puntos([(14, 2), (18, 8), (22, 13), (21, 20), (14, 26), (7, 20), (6, 13), (10, 8), (12, 10)], s, c), fill=p[1])
    d.polygon(puntos([(14, 8), (17, 13), (18, 19), (14, 23), (10, 19), (10, 14)], s, c), fill=p[2])
    d.polygon(puntos([(14, 14), (16, 18), (14, 21), (12, 18)], s, c), fill=p[3])


def gota(d, p, s, c):
    cx, cy = c
    d.ellipse([cx - 8 * s, cy - 3 * s, cx + 8 * s, cy + 12 * s], fill=p[1])
    d.polygon(puntos([(14, -1), (21, 9), (7, 9)], s, c), fill=p[1])
    d.ellipse([cx - 5 * s, cy, cx + 4 * s, cy + 9 * s], fill=p[2])
    d.rectangle([cx - 4 * s, cy + 1 * s, cx - 2 * s, cy + 4 * s], fill=p[3])


def remolino(d, p, s, c):
    cx, cy = c
    for k, (r, tono) in enumerate(((11, 1), (7, 2), (3, 3))):
        r = r * s
        inicio = 40 + 70 * k
        d.arc([cx - r, cy - r, cx + r, cy + r], inicio, inicio + 270, fill=p[tono], width=max(2, round(2 * s)))


def roca(d, p, s, c):
    d.polygon(puntos([(6, 10), (12, 4), (20, 5), (24, 12), (22, 21), (14, 25), (6, 21), (4, 15)], s, c), fill=p[1])
    d.polygon(puntos([(9, 10), (13, 6), (19, 7), (16, 13), (10, 14)], s, c), fill=p[2])
    d.polygon(puntos([(12, 8), (15, 7), (13, 10)], s, c), fill=p[3])
    d.line(puntos([(16, 13), (20, 19)], s, c), fill=p[0], width=1)


def hoja(d, p, s, c):
    d.polygon(puntos([(3, 22), (8, 12), (16, 5), (25, 3), (23, 12), (16, 20), (8, 24)], s, c), fill=p[1])
    d.polygon(puntos([(8, 19), (12, 12), (18, 7), (22, 6), (20, 11), (14, 17)], s, c), fill=p[2])
    d.line(puntos([(4, 23), (22, 6)], s, c), fill=p[3], width=1)


def rayo(d, p, s, c):
    d.polygon(puntos([(17, 1), (8, 14), (13, 14), (9, 27), (21, 11), (15, 11), (20, 1)], s, c), fill=p[1])
    d.polygon(puntos([(17, 4), (11, 13), (15, 13), (12, 22), (18, 12), (13, 12), (17, 4)], s, c), fill=p[2])
    d.line(puntos([(16, 5), (12, 12)], s, c), fill=p[3], width=1)


def estrella(d, p, s, c):
    d.polygon(puntos([(14, 1), (17, 11), (27, 14), (17, 17), (14, 27), (11, 17), (1, 14), (11, 11)], s, c), fill=p[1])
    d.polygon(puntos([(14, 6), (16, 12), (22, 14), (16, 16), (14, 22), (12, 16), (6, 14), (12, 12)], s, c), fill=p[2])
    cx, cy = c
    d.rectangle([cx - 1 * s, cy - 1 * s, cx + 1 * s, cy + 1 * s], fill=p[3])


def orbe(d, p, s, c):
    cx, cy = c
    d.ellipse([cx - 11 * s, cy - 11 * s, cx + 11 * s, cy + 11 * s], fill=p[1])
    d.ellipse([cx - 7 * s, cy - 7 * s, cx + 7 * s, cy + 7 * s], fill=p[0])
    d.arc([cx - 9 * s, cy - 9 * s, cx + 9 * s, cy + 9 * s], 200, 330, fill=p[2], width=max(1, round(2 * s)))
    d.rectangle([cx + 3 * s, cy - 5 * s, cx + 4 * s, cy - 4 * s], fill=p[3])


def espinas(d, p, s, c):
    for x0, y0, x1, y1 in ((4, 24, 12, 4), (12, 26, 17, 6), (18, 25, 25, 8)):
        d.polygon(puntos([(x0 - 2, y0), (x0 + 3, y0), (x1, y1)], s, c), fill=p[1])
        d.line(puntos([(x0, y0 - 1), (x1, y1 + 2)], s, c), fill=p[2], width=1)


def zarza(d, p, s, c):
    hoja(d, p, s, c)
    for x, y in ((9, 15), (15, 10), (19, 13), (12, 20)):
        d.polygon(puntos([(x, y), (x + 3, y - 4), (x + 2, y + 1)], s, c), fill=p[3])


def lanza(d, p, s, c):
    d.polygon(puntos([(1, 17), (8, 11), (27, 13), (8, 19)], s, c), fill=p[1])
    d.polygon(puntos([(5, 15), (9, 12), (24, 13), (9, 15)], s, c), fill=p[2])
    d.line(puntos([(10, 13), (22, 13)], s, c), fill=p[3], width=1)


def chorro(d, p, s, c):
    for k, y in enumerate((9, 14, 19)):
        d.ellipse(puntos([(3 + 2 * k, y - 2), (22 - k, y + 2)], s, c), fill=p[1])
        d.line(puntos([(6 + 2 * k, y - 1), (18 - k, y - 1)], s, c), fill=p[3], width=1)
    gota(d, p, 0.5 * s, (c[0] + 8 * s, c[1]))


motivos = [llama, gota, remolino, roca, hoja, rayo, estrella, orbe]

# Algunos conjuros tienen su propio motivo en lugar del de su elemento.
motivoPropio = {"Espinas": espinas, "Zarza": zarza, "Lanza de roca": lanza, "Chorro": chorro}


def chispas(d, p, radio, cuantas):
    for k in range(cuantas):
        angulo = 2 * math.pi * k / cuantas + 0.3
        x, y = 14 + radio * math.cos(angulo), 14 + radio * math.sin(angulo)
        d.rectangle([x - 1, y - 1, x, y], fill=p[3 if k % 2 else 2])


def corte(d, p, desde, hasta, grueso):
    # Un tajo curvo: una media luna delgada que se afila en las puntas.
    (x0, y0), (x1, y1) = desde, hasta
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    nx, ny = -(y1 - y0), x1 - x0
    largo = math.hypot(nx, ny)
    nx, ny = nx / largo, ny / largo
    afuera = [(mx + nx * grueso * 1.6, my + ny * grueso * 1.6)]
    adentro = [(mx + nx * grueso * 0.2, my + ny * grueso * 0.2)]
    d.polygon([desde] + afuera + [hasta] + adentro, fill=p[1])
    d.line([desde, (mx + nx * grueso * 0.9, my + ny * grueso * 0.9), hasta], fill=p[3], width=1)


def zarpazo(d, p, n=3):
    for k in range(n):
        dx = (k - (n - 1) / 2) * 6
        corte(d, p, (6 + dx, 23), (20 + dx, 4), 2.5)


def tajo(d, p, grande=False):
    corte(d, p, (3, 25), (25, 3), 5 if grande else 3.5)


def estocada(d, p):
    for k, y in enumerate((8, 14, 20)):
        d.polygon([(4 + 3 * k % 2, y), (24, y - 1), (27, y), (24, y + 1)], fill=p[2])
        d.line([(10, y), (25, y)], fill=p[3], width=1)


def mordida(d, p):
    d.arc([3, 2, 25, 16], 200, 340, fill=p[1], width=3)
    d.arc([3, 12, 25, 26], 20, 160, fill=p[1], width=3)
    for x in (7, 11, 15, 19):
        d.polygon([(x, 6), (x + 3, 6), (x + 1.5, 11)], fill=p[3])
        d.polygon([(x + 1, 22), (x + 4, 22), (x + 2.5, 17)], fill=p[3])


def impacto(d, p, puntas=8, grande=False):
    radioFuera, radioDentro = (13, 6) if grande else (11, 5)
    lista = []
    for k in range(2 * puntas):
        r = radioFuera if k % 2 == 0 else radioDentro
        angulo = math.pi * k / puntas
        lista.append((14 + r * math.cos(angulo), 14 + r * math.sin(angulo)))
    d.polygon(lista, fill=p[1])
    d.polygon([(14 + (x - 14) * 0.55, 14 + (y - 14) * 0.55) for x, y in lista], fill=p[2])
    d.ellipse([12, 12, 16, 16], fill=p[3])


def onda(d, p):
    for r, tono in ((12, 1), (8, 2)):
        d.arc([14 - r, 14 - r * 0.6, 14 + r, 14 + r * 0.6], 180, 360, fill=p[tono], width=2)
    for x, y in ((5, 19), (10, 22), (18, 22), (23, 19), (14, 24)):
        d.rectangle([x, y, x + 2, y + 1], fill=p[1])
    d.rectangle([4, 16, 24, 17], fill=p[3])


def coletazo(d, p):
    d.arc([2, 2, 30, 30], 160, 280, fill=p[1], width=5)
    d.arc([5, 5, 27, 27], 170, 270, fill=p[2], width=2)
    d.arc([2, 2, 30, 30], 190, 250, fill=p[3], width=1)


def contornear(im, color):
    # Un pixel oscuro alrededor de todo lo dibujado, como el de los heroes.
    salida = im.copy()
    for y in range(lado):
        for x in range(lado):
            if im.getpixel((x, y))[3] == 0 and any(
                    0 <= x + a < lado and 0 <= y + b < lado and im.getpixel((x + a, y + b))[3] > 0
                    for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                salida.putpixel((x, y), color + (255,))
    return salida


def conjuro(nombre, elem, nivel, enArea):
    # nivel 0 chico, 1 mediano, 2 del jefe, 3 poderoso, 4 de carga
    im = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    p = paletas[elem]
    motivo = motivoPropio.get(nombre, motivos[elem])
    if enArea:
        for centro in ((9, 10), (19, 9), (14, 19)):
            motivo(d, p, 0.5, centro)
    else:
        motivo(d, p, (0.55, 0.7, 0.8, 0.85, 0.9)[nivel], (14, 14))
    im = contornear(im, p[0])
    if nivel >= 3:
        d = ImageDraw.Draw(im)
        chispas(d, p, 13, 8 if nivel == 3 else 12)
    return im


def velocidad(d, p):
    # Lineas de arrastre detras de lo que avanza.
    for y, largo in ((9, 7), (14, 10), (19, 7)):
        d.line([(1, y), (1 + largo, y)], fill=p[2], width=1)


def grietas(d, p):
    d.rectangle([3, 21, 25, 22], fill=p[1])
    for x0, x1, y1 in ((8, 6, 26), (14, 15, 27), (20, 22, 26)):
        d.line([(x0, 22), (x1, y1)], fill=p[0], width=1)


def anillo(d, p):
    for r, tono in ((13, 1), (9, 2), (5, 3)):
        d.ellipse([14 - r, 14 - r * 0.7, 14 + r, 14 + r * 0.7], outline=p[tono], width=2)


def fisico(nombre, enArea, carga):
    im = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    p = paletaCorte
    if nombre == "Zarpazo":
        zarpazo(d, p, 3)
    elif nombre == "Garra doble":
        zarpazo(d, p, 2)
        for k in range(2):
            corte(d, p, (6 + 6 * k, 5), (20 + 6 * k, 24), 2.5)
    elif nombre == "Garra sombria":
        p = paletas[7]
        zarpazo(d, p, 3)
    elif nombre == "Tajo mayor":
        tajo(d, p, grande=True)
        corte(d, p, (3, 18), (18, 3), 2.5)
    elif nombre == "Tajo elemental":
        p = paletas[6]
        tajo(d, p, grande=True)
    elif nombre == "Furia desatada":
        p = paletas[0]
        corte(d, p, (3, 25), (25, 3), 4)
        corte(d, p, (3, 3), (25, 25), 4)
    elif nombre == "Golpe sombra":
        p = paletas[7]
        tajo(d, p)
    elif nombre == "Ataque basico":
        tajo(d, p)
    elif nombre == "Punalada veloz":
        estocada(d, p)
    elif nombre == "Mordida":
        mordida(d, p)
    elif nombre == "Coletazo":
        p = paletaImpacto
        coletazo(d, p)
    elif nombre == "Barrido":
        p = paletaImpacto
        d.arc([-6, 2, 34, 34], 200, 340, fill=p[1], width=5)
        d.arc([-3, 5, 31, 31], 210, 330, fill=p[2], width=2)
        velocidad(d, p)
    elif nombre == "Onda de choque":
        p = paletaImpacto
        anillo(d, p)
    elif nombre == "Terremoto":
        p = paletas[3]
        onda(d, p)
        grietas(d, p)
    elif nombre == "Estampida":
        p = paletas[3]
        for x, y in ((6, 8), (16, 6), (10, 17), (20, 16)):
            d.ellipse([x - 4, y - 3, x + 4, y + 3], fill=p[1 + (x + y) % 2])
        velocidad(d, p)
    elif nombre == "Pisoton":
        p = paletaImpacto
        impacto(d, p, 6)
        grietas(d, p)
    elif nombre == "Embestida":
        p = paletaImpacto
        impacto(d, p, 8)
        velocidad(d, p)
    elif nombre == "Cabezazo":
        p = paletaImpacto
        impacto(d, p, 5)
    elif nombre == "Devastacion":
        p = paletaImpacto
        anillo(d, p)
        impacto(d, p, 10)
    else:
        p = paletaImpacto
        impacto(d, p, 10 if carga else 8, grande=carga or nombre == "Golpe pesado")
    im = contornear(im, p[0])
    if carga:
        chispas(ImageDraw.Draw(im), p, 13, 12)
    return im


def cambioDeFase():
    # Este crece sobre el jefe hasta mas de 400 pixeles, asi que se dibuja en
    # una rejilla mas fina que la de los ataques para que no se vea de bloques.
    n = 110
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    p, c = paletaFase, n / 2
    for k in range(16):
        angulo = 2 * math.pi * k / 16
        largo = 52 if k % 2 == 0 else 40
        d.line([(c + 18 * math.cos(angulo), c + 18 * math.sin(angulo)),
                (c + largo * math.cos(angulo), c + largo * math.sin(angulo))], fill=p[2 if k % 2 else 1], width=3)
    for r, tono, grueso in ((44, 1, 4), (34, 2, 3), (22, 3, 2)):
        d.ellipse([c - r, c - r, c + r, c + r], outline=p[tono], width=grueso)
    d.ellipse([c - 12, c - 12, c + 12, c + 12], fill=p[3])
    d.ellipse([c - 7, c - 7, c + 7, c + 7], fill=(255, 255, 255))
    return im


def todosLosEfectos():
    efectos = {}
    for ataque in m.HABILIDADES:
        if ataque["elem"] is not None and not ataque["esFisico"] and ataque["nombre"] != "Garra sombria":
            nivel = 4 if ataque["carga"] else 2
            efectos[ataque["nombre"]] = conjuro(ataque["nombre"], ataque["elem"], nivel, ataque["enArea"])
        else:
            efectos[ataque["nombre"]] = fisico(ataque["nombre"], ataque["enArea"], ataque["carga"])
    for k, c in enumerate(m.conjurosMago):
        efectos[c["nombre"]] = conjuro(c["nombre"], c["elem"], k % 2, False)
    for c in m.conjurosMagoPoderosos:
        efectos[c["nombre"]] = conjuro(c["nombre"], c["elem"], 3, False)
    for nombre in ("Ataque basico", "Tajo mayor", "Tajo elemental", "Punalada veloz", "Furia desatada", "Golpe sombra"):
        efectos[nombre] = fisico(nombre, False, False)
    efectos["Cambio de fase"] = cambioDeFase()
    return efectos


if __name__ == "__main__":
    os.makedirs(carpetaEfectos, exist_ok=True)
    for nombre, im in todosLosEfectos().items():
        im.resize((im.width * 2, im.height * 2), Image.NEAREST).save(os.path.join(carpetaEfectos, nombreDeArchivo(nombre) + ".png"))
