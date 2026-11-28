# Saca al jefe de sus dos ilustraciones, una por fase. Vienen ya sin fondo, asi
# que el canal alfa dice que es jefe y que no.
#
# El proceso es el mismo que el de los heroes en extraerSprites.py:
#   1. Llevar la imagen a su rejilla real. Las dos ilustraciones no vienen a la
#      misma escala: en la primera cada pixel del dibujo mide 5.7 pixeles de la
#      imagen, y en la segunda 4.23 a lo ancho por 4.43 a lo alto, porque se
#      reescalo distinto en cada eje.
#   2. Cada celda se queda con la mediana de su centro, color y transparencia.
#      El aura se desvanece en semitransparencia; lo que este a menos de la
#      mitad se descarta y el aura queda como un borde de color.
#   3. Descartar chispas sueltas y cerrar la paleta.
# El resultado queda en recursos/jefes/base, mirando a la izquierda, hacia los
# heroes. De ahi grafico/poses.py genera sus poses.
#
# Uso: python -m grafico.extraerJefe
import os
from collections import deque

import numpy as np
from PIL import Image

from grafico.extraerSprites import quitarSueltos

carpetaRecursos = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recursos")

# Paso horizontal, paso vertical y una zona con mucho detalle donde buscar
# como queda alineada la rejilla.
rejillas = {
    "fase1": (5.7, 5.7, (1100, 700, 1300, 900)),
    "fase2": (4.23, 4.43, (900, 800, 1100, 1000)),
}
coloresPorSprite = 128
alfaMinimo = 128

# Las llamas del aura se desvanecen hacia el blanco ya opaco. Ese blanco se
# come desde afuera hacia adentro mientras siga siendo casi puro; los brillos
# de adentro del jefe no tocan lo transparente y se quedan.
sumaDesvanecido = 735


def faseDeRejilla(a, px, py):
    alto, ancho, _ = a.shape
    mejor = None
    for fy in np.arange(0, py, 0.33):
        for fx in np.arange(0, px, 0.33):
            ny, nx = int((alto - fy) // py), int((ancho - fx) // px)
            error = 0.0
            for j in range(ny):
                y = fy + j * py
                for i in range(nx):
                    x = fx + i * px
                    cuadro = a[int(y + py * .25):int(y + py * .75) + 1,
                               int(x + px * .25):int(x + px * .75) + 1].reshape(-1, 3)
                    error += cuadro.std(axis=0).sum()
            if mejor is None or error < mejor[0]:
                mejor = (error, fy, fx)
    return mejor[1], mejor[2]


def aRejilla(ruta, px, py, zona):
    a = np.asarray(Image.open(ruta).convert("RGBA")).astype(float)
    x0, y0, x1, y1 = zona
    fy, fx = faseDeRejilla(a[y0:y1, x0:x1, :3], px, py)
    gy, gx = (y0 + fy) % py, (x0 + fx) % px

    alto, ancho, _ = a.shape
    ny, nx = int((alto - gy) // py), int((ancho - gx) // px)
    salida = np.zeros((ny, nx, 4), np.uint8)
    for j in range(ny):
        y = gy + j * py
        ya, yb = int(y + py * .3), int(y + py * .7) + 1
        for i in range(nx):
            x = gx + i * px
            cuadro = a[ya:yb, int(x + px * .3):int(x + px * .7) + 1].reshape(-1, 4)
            salida[j, i] = np.median(cuadro, axis=0)
    return salida


def comerDesvanecido(g, lleno):
    alto, ancho = lleno.shape
    blanco = g[..., :3].astype(int).sum(axis=2) > sumaDesvanecido
    cola = deque((y, x) for y, x in zip(*np.nonzero(~lleno)))
    while cola:
        y, x = cola.popleft()
        for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            if 0 <= yy < alto and 0 <= xx < ancho and lleno[yy, xx] and blanco[yy, xx]:
                lleno[yy, xx] = False
                cola.append((yy, xx))
    return lleno


def extraer(fase):
    px, py, zona = rejillas[fase]
    g = aRejilla(os.path.join(carpetaRecursos, "disenos", "jefe_%s.png" % fase), px, py, zona)
    lleno = quitarSueltos(comerDesvanecido(g, g[..., 3] >= alfaMinimo))

    muestra = Image.fromarray(g[..., :3][lleno].reshape(1, -1, 3))
    # Con tantos tonos de piel y de aura hace falta una paleta mas amplia que
    # la de los heroes, y el octree respeta mejor los colores saturados del halo.
    reducida = muestra.quantize(coloresPorSprite, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    paleta = np.array(reducida.getpalette()[:coloresPorSprite * 3]).reshape(-1, 3)

    rgba = np.zeros(g.shape[:2] + (4,), np.uint8)
    rgba[lleno, :3] = paleta[np.asarray(reducida)[0]]
    rgba[lleno, 3] = 255
    sprite = Image.fromarray(rgba)
    return sprite.crop(sprite.getbbox())


if __name__ == "__main__":
    for fase in rejillas:
        extraer(fase).save(os.path.join(carpetaRecursos, "jefes", "base", fase + ".png"))
