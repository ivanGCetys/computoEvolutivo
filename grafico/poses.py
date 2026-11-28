# Genera todas las poses de cada heroe a partir de un solo sprite base.
#
# Los sprites base estan en recursos/personajes/base, a su resolucion real
# (un pixel del archivo es un pixel del dibujo) y mirando a la derecha. Salen
# de la pose de ataque de las hojas de diseno de cada clase.
#
# Cada pose se arma moviendo pixeles completos, nunca suavizando, para que el
# resultado siga siendo pixel art con la misma paleta y el mismo contorno:
#   ataque    el sprite base tal cual
#   normal    el mismo, con el cuerpo un poco hacia atras, en guardia
#   magia     un contorno brillante alrededor de la silueta
#   bloqueo   agachado: se acortan las piernas y se inclina hacia atras
#   dano      echado para atras y con un destello rojo
#   herido    de rodillas y encorvado, para cuando le queda poca vida
#   caido     acostado boca arriba
#   celebra   estirado hacia arriba, para los saltos de victoria
#
# El jefe sigue la misma idea con sus dos fases, que estan en
# recursos/jefes/base y miran a la izquierda. Tiene una pose por cada grupo de
# cuatro ataques de su banco, mas una al recibir dano y otra al ser vencido, y
# cuatro cuadros para el impulso y el golpe de sus ataques.
#
# Uso: python -m grafico.poses
import os
from PIL import Image

carpetaBase = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recursos", "personajes")
clasesConSprite = ["guerrero", "tanque", "mago", "clerigo", "picaro", "berserker"]

# El color del brillo de la pose de magia, uno por clase.
brilloMagia = {"guerrero": (120, 200, 255), "tanque": (150, 230, 120), "mago": (200, 120, 255),
               "clerigo": (255, 230, 120), "picaro": (230, 90, 110), "berserker": (255, 140, 60)}


def leerBase(clase):
    return Image.open(os.path.join(carpetaBase, "base", clase + ".png")).convert("RGBA")


def pixeles(im):
    return [[im.getpixel((x, y)) for x in range(im.width)] for y in range(im.height)]


def aImagen(filas):
    im = Image.new("RGBA", (len(filas[0]), len(filas)), (0, 0, 0, 0))
    for y, fila in enumerate(filas):
        for x, c in enumerate(fila):
            im.putpixel((x, y), c)
    return im


def conMargen(im, izq, der, arriba, abajo=0):
    lienzo = Image.new("RGBA", (im.width + izq + der, im.height + arriba + abajo), (0, 0, 0, 0))
    lienzo.paste(im, (izq, arriba))
    return lienzo


def inclinar(im, desplazamiento):
    # Corre cada fila hacia un lado, mas entre mas arriba esta, con los pies
    # fijos. Positivo inclina hacia el frente (la derecha).
    margen = abs(desplazamiento) + 1
    im = conMargen(im, margen, margen, 0)
    filas = pixeles(im)
    alto, vacio = len(filas), (0, 0, 0, 0)
    salida = []
    for y, fila in enumerate(filas):
        d = round(desplazamiento * (alto - 1 - y) / (alto - 1))
        if d > 0:
            fila = [vacio] * d + fila[:-d]
        elif d < 0:
            fila = fila[-d:] + [vacio] * (-d)
        salida.append(fila)
    return aImagen(salida)


def aplastarPiernas(im, fraccionPiernas, filasQuitadas):
    # Quita filas repartidas dentro del tercio de abajo, que es donde estan
    # las piernas, para que el personaje quede agachado o de rodillas.
    filas = pixeles(im)
    alto = len(filas)
    inicio = int(alto * (1 - fraccionPiernas))
    candidatas = list(range(inicio + 1, alto - 2))
    paso = max(1, len(candidatas) // max(1, filasQuitadas))
    quitar = set(candidatas[::paso][:filasQuitadas])
    nuevas = [f for y, f in enumerate(filas) if y not in quitar]
    vacio = [(0, 0, 0, 0)] * len(filas[0])
    return aImagen([vacio] * len(quitar) + nuevas)


def estirar(im, filasExtra):
    # Duplica algunas filas del torso para alargar el cuerpo hacia arriba.
    filas = pixeles(im)
    alto = len(filas)
    candidatas = list(range(int(alto * 0.35), int(alto * 0.7)))
    paso = max(1, len(candidatas) // max(1, filasExtra))
    dobles = set(candidatas[::paso][:filasExtra])
    nuevas = []
    for y, f in enumerate(filas):
        nuevas.append(f)
        if y in dobles:
            nuevas.append(list(f))
    return aImagen(nuevas)


def teñir(im, color, fuerza):
    filas = pixeles(im)
    salida = []
    for fila in filas:
        nueva = []
        for r, g, b, a in fila:
            if a == 0:
                nueva.append((r, g, b, a))
            else:
                nueva.append((round(r + (color[0] - r) * fuerza), round(g + (color[1] - g) * fuerza),
                              round(b + (color[2] - b) * fuerza), a))
        salida.append(nueva)
    return aImagen(salida)


def aura(im, color):
    # Un contorno de un pixel por fuera de la silueta, y otro mas tenue por
    # fuera de ese, como el brillo de quien lanza un conjuro.
    im = conMargen(im, 2, 2, 2, 2)
    filas = pixeles(im)
    alto, ancho = len(filas), len(filas[0])
    tenue = color + (110,)
    fuerte = color + (230,)
    for capa, tono in ((1, fuerte), (2, tenue)):
        lleno = [[filas[y][x][3] > 0 for x in range(ancho)] for y in range(alto)]
        for y in range(alto):
            for x in range(ancho):
                if not lleno[y][x] and any(0 <= y + b < alto and 0 <= x + a < ancho and lleno[y + b][x + a]
                                           for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    filas[y][x] = tono
    return aImagen(filas)


def acostar(im):
    # Cae de espaldas: la cabeza queda a la izquierda, del lado contrario al jefe.
    return im.rotate(90, expand=True)


def generarPoses(clase):
    base = leerBase(clase)
    alto = base.height
    return {
        "": inclinar(base, -1),
        "ataque": inclinar(base, 2),
        "magia": aura(base, brilloMagia[clase]),
        "bloqueo": inclinar(aplastarPiernas(base, 0.35, max(2, alto // 12)), -2),
        "dano": teñir(inclinar(base, -3), (255, 70, 60), 0.35),
        "herido": inclinar(aplastarPiernas(base, 0.4, max(3, alto // 6)), 3),
        "caido": acostar(base),
        "celebra": estirar(base, max(1, alto // 15)),
    }


def nombreArchivo(clase, pose):
    return clase + ("_" + pose if pose else "") + ".png"


carpetaJefes = os.path.join(os.path.dirname(carpetaBase), "jefes")

# Lo que hace cada una de las 8 poses del jefe, en el orden de su banco de
# ataques. El jefe mira a la izquierda, asi que inclinarse hacia el frente es
# un desplazamiento negativo.
moradoJefe, doradoJefe, blancoJefe = (190, 110, 255), (255, 210, 110), (255, 250, 235)


def posesDelJefe(base):
    alto = base.height
    return {
        "": base,
        "pose_1": inclinar(base, -6),
        "pose_2": estirar(inclinar(base, -10), max(2, alto // 40)),
        "pose_3": inclinar(aplastarPiernas(base, 0.35, max(4, alto // 18)), -5),
        "pose_4": aura(inclinar(base, -4), moradoJefe),
        "pose_5": aura(inclinar(base, -4), doradoJefe),
        "pose_6": aura(estirar(base, max(2, alto // 30)), moradoJefe),
        "pose_7": aura(estirar(base, max(2, alto // 30)), doradoJefe),
        "pose_8": aura(aplastarPiernas(base, 0.35, max(6, alto // 12)), blancoJefe),
        "dano": teñir(inclinar(base, 6), (255, 70, 60), 0.35),
        "derrota": teñir(inclinar(aplastarPiernas(base, 0.45, max(10, alto // 6)), 10), (20, 16, 30), 0.45),
    }


# Los cuadros que usa el jefe al atacar, armados igual que las poses: con todo
# el cuerpo, sin recortar partes. El jefe mira a la izquierda, asi que echarse
# para atras es inclinarse a la derecha.
#   alzar     se echa para atras y se estira, tomando impulso
#   golpe     se lanza hacia el frente y se agacha al soltar el golpe
#   conjuro   se yergue con el aura encendida mientras junta la magia
#   lanzar    se inclina hacia el frente con el aura al soltarla
def cuadrosDeAtaque(base, fase):
    alto = base.height
    color = moradoJefe if fase == "fase1" else doradoJefe
    cuadros = {
        "alzar": estirar(inclinar(base, 9), max(3, alto // 25)),
        "golpe": inclinar(aplastarPiernas(base, 0.35, max(5, alto // 16)), -14),
        "conjuro": aura(estirar(inclinar(base, 4), max(4, alto // 20)), color),
        "lanzar": aura(inclinar(base, -10), color),
    }
    # El aura agrega dos pixeles por lado; se quitan para que siga apoyado en
    # el mismo lugar que los otros cuadros.
    for nombre in ("conjuro", "lanzar"):
        im = cuadros[nombre]
        cuadros[nombre] = im.crop((2, 2, im.width - 2, im.height - 2))
    return cuadros


def nombreArchivoJefe(fase, pose):
    prefijo = "jefe" if fase == "fase1" else "jefe_fase2"
    return prefijo + ("_" + pose if pose else "") + ".png"


def generarTodo():
    for clase in clasesConSprite:
        for pose, im in generarPoses(clase).items():
            im.save(os.path.join(carpetaBase, nombreArchivo(clase, pose)))
    for fase in ("fase1", "fase2"):
        ruta = os.path.join(carpetaJefes, "base", fase + ".png")
        if os.path.exists(ruta):
            base = Image.open(ruta).convert("RGBA")
            for pose, im in list(posesDelJefe(base).items()) + list(cuadrosDeAtaque(base, fase).items()):
                im.save(os.path.join(carpetaJefes, nombreArchivoJefe(fase, pose)))


if __name__ == "__main__":
    generarTodo()
