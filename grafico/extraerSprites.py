# Saca el sprite base de cada heroe de su hoja de diseno.
#
# Las hojas de recursos/disenos son imagenes grandes donde cada pixel del
# dibujo ocupa un cuadro de unos 11 o 12 pixeles de la imagen, y ademas son
# jpg, asi que los cuadros no son parejos. De cada hoja se toma la ultima pose
# de la fila de armadura, que es la de ataque, y se lleva de vuelta a un pixel
# por cuadro. El resultado queda en recursos/personajes/base, mirando a la
# derecha, y de ahi grafico/poses.py genera todas las demas poses.
#
# Uso: python -m grafico.extraerSprites
import os
from collections import deque

import numpy as np
from PIL import Image

carpetaRecursos = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recursos")

# Donde esta la pose en cada hoja y cuantos pixeles de la imagen mide un pixel
# del dibujo. Hay dos formatos de hoja: las anchas de cinco columnas y las
# altas de cinco columnas con filas mas grandes. El recorte del clerigo es un
# poco mas bajo porque sus pies tocan la linea del marco de la hoja.
recortes = {
    "guerrero": ((2062, 815, 2572, 1152), 10.75),
    "berserker": ((2062, 815, 2572, 1152), 10.75),
    "picaro": ((2062, 815, 2572, 1152), 10.75),
    "mago": ((1380, 1250, 1790, 1835), 12.0),
    "tanque": ((1380, 1250, 1790, 1835), 12.0),
    "clerigo": ((1380, 1250, 1790, 1822), 12.0),
}
coloresPorSprite = 40


def aRejilla(a, paso):
    # Prueba todas las formas de alinear la rejilla y se queda con la que deja
    # cada cuadro mas parejo por dentro: esa es la rejilla real del dibujo. De
    # cada cuadro se toma la mediana del centro, que es donde el jpg ensucia menos.
    alto, ancho, _ = a.shape
    mejor = None
    for fy in np.arange(0, paso, 0.5):
        for fx in np.arange(0, paso, 0.5):
            ny, nx = int((alto - fy) // paso), int((ancho - fx) // paso)
            salida = np.zeros((ny, nx, 3))
            error = 0.0
            for j in range(ny):
                y = fy + j * paso
                for i in range(nx):
                    x = fx + i * paso
                    cuadro = a[int(y + paso * .3):int(y + paso * .7) + 1,
                               int(x + paso * .3):int(x + paso * .7) + 1].reshape(-1, 3)
                    salida[j, i] = np.median(cuadro, axis=0)
                    error += cuadro.std(axis=0).sum()
            if mejor is None or error < mejor[0]:
                mejor = (error, salida)
    return mejor[1]


def marcarFondo(g):
    # El fondo es el color de las orillas y todo lo parecido que este conectado
    # a ellas. Lo que quede encerrado por el contorno es parte del personaje
    # aunque tenga un color parecido.
    alto, ancho, _ = g.shape
    fondo = np.median(np.array([g[0, 0], g[0, -1], g[-1, 0], g[-1, -1], g[0, ancho // 2]]), axis=0)
    parecido = np.abs(g - fondo).sum(axis=2) < 40
    vacio = np.zeros((alto, ancho), bool)
    cola = deque([(y, x) for y in range(alto) for x in (0, ancho - 1)] +
                 [(y, x) for x in range(ancho) for y in (0, alto - 1)])
    while cola:
        y, x = cola.popleft()
        if 0 <= y < alto and 0 <= x < ancho and not vacio[y, x] and parecido[y, x]:
            vacio[y, x] = True
            cola.extend(((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)))
    return vacio


def quitarSueltos(lleno):
    # Las lineas del marco de la hoja quedan como tiras de un pixel de grueso.
    # Se descarta toda pieza suelta que sea asi de delgada o muy chica.
    alto, ancho = lleno.shape
    visto = np.zeros_like(lleno)
    quedan = np.zeros_like(lleno)
    for y0 in range(alto):
        for x0 in range(ancho):
            if not lleno[y0, x0] or visto[y0, x0]:
                continue
            pieza, cola = [], deque([(y0, x0)])
            visto[y0, x0] = True
            while cola:
                y, x = cola.popleft()
                pieza.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < alto and 0 <= xx < ancho and lleno[yy, xx] and not visto[yy, xx]:
                            visto[yy, xx] = True
                            cola.append((yy, xx))
            ys, xs = [p[0] for p in pieza], [p[1] for p in pieza]
            if len(pieza) >= 12 and max(ys) - min(ys) >= 2 and max(xs) - min(xs) >= 2:
                for y, x in pieza:
                    quedan[y, x] = True
    return quedan


def extraer(clase):
    caja, paso = recortes[clase]
    hoja = Image.open(os.path.join(carpetaRecursos, "disenos", clase + ".jpg")).convert("RGB")
    g = aRejilla(np.asarray(hoja.crop(caja)).astype(float), paso)
    lleno = quitarSueltos(~marcarFondo(g))

    # La paleta se calcula solo con los pixeles del personaje, para que el
    # fondo no le quite colores.
    muestra = Image.fromarray(g[lleno].astype(np.uint8).reshape(1, -1, 3))
    reducida = muestra.quantize(coloresPorSprite, method=Image.Quantize.MAXCOVERAGE, dither=Image.Dither.NONE)
    paleta = np.array(reducida.getpalette()[:coloresPorSprite * 3]).reshape(-1, 3)

    rgba = np.zeros(g.shape[:2] + (4,), np.uint8)
    rgba[lleno, :3] = paleta[np.asarray(reducida)[0]]
    rgba[lleno, 3] = 255
    sprite = Image.fromarray(rgba)

    # En las hojas miran a la izquierda; en el juego miran al jefe, a la derecha.
    return sprite.crop(sprite.getbbox()).transpose(Image.FLIP_LEFT_RIGHT)


if __name__ == "__main__":
    for clase in recortes:
        extraer(clase).save(os.path.join(carpetaRecursos, "personajes", "base", clase + ".png"))
