# Motor de las animaciones de ataque.
#
# Cada ataque se anima con una Animacion: una linea de tiempo a la que su
# receta (grafico/recetas.py) le va agendando piezas. Las piezas son cosas
# simples que se dibujan solas: grupos de particulas, trazos que duran un
# rato, relampagos, anillos. Ademas la animacion puede pedirle a la pantalla
# un destello, una sacudida o que se oscurezca el fondo para que la magia
# resalte, como en los RPG de 16 bits.
#
# Todo se dibuja en capas a la mitad de la resolucion y se agranda al doble
# sin suavizar, para que los efectos tengan pixeles del mismo grueso que los
# iconos de recursos/efectos. Hay tres capas: atras de los personajes, al
# frente, y una de luz que se suma a la imagen en lugar de taparla.
import math
import os
import random

import pygame

escala = 2
azar = random.Random()

# Quien reproduce los sonidos de las animaciones. La pantalla lo conecta con
# grafico.recursos; aqui no se importa pygame.mixer para que las animaciones
# se puedan probar en silencio.
reproductor = [None]


def sonar(nombre, volumen=1.0):
    if reproductor[0] is not None:
        reproductor[0](nombre, volumen)

blanco = (255, 255, 255)


def atenuar(color, k):
    k = max(0.0, min(1.0, k))
    return (int(color[0] * k), int(color[1] * k), int(color[2] * k))


def mezclar(a, b, t):
    t = max(0.0, min(1.0, t))
    return (int(a[0] + (b[0] - a[0]) * t), int(a[1] + (b[1] - a[1]) * t), int(a[2] + (b[2] - a[2]) * t))


def suave(u):
    # Arranca y frena despacio.
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


class Lugar:
    # Donde esta parado un personaje, ya en coordenadas de las capas: su
    # centro y la altura del piso bajo sus pies.
    def __init__(self, x, y, piso):
        self.x, self.y, self.piso = x / escala, y / escala, piso / escala


class Capas:

    def __init__(self, ancho, alto):
        self.tamano = (ancho, alto)
        self.ancho, self.alto = ancho // escala, alto // escala
        bajo = (self.ancho, self.alto)
        self.bajas = {"atras": pygame.Surface(bajo, pygame.SRCALPHA), "frente": pygame.Surface(bajo, pygame.SRCALPHA),
                      "luz": pygame.Surface(bajo)}
        self.altas = {"atras": pygame.Surface(self.tamano, pygame.SRCALPHA),
                      "frente": pygame.Surface(self.tamano, pygame.SRCALPHA), "luz": pygame.Surface(self.tamano)}
        self.usadas = set()

    def limpiar(self):
        for nombre in self.usadas:
            self.bajas[nombre].fill((0, 0, 0, 0))
        self.usadas = set()

    def de(self, nombre):
        self.usadas.add(nombre)
        return self.bajas[nombre]

    def volcar(self, lienzo, nombre):
        if nombre not in self.usadas:
            return
        pygame.transform.scale(self.bajas[nombre], self.tamano, self.altas[nombre])
        if nombre == "luz":
            lienzo.blit(self.altas[nombre], (0, 0), special_flags=pygame.BLEND_RGB_ADD)
        else:
            lienzo.blit(self.altas[nombre], (0, 0))


class Particulas:
    # Un grupo de particulas con la misma apariencia. La rampa es la lista de
    # colores por los que pasa cada una a lo largo de su vida; no se mezclan,
    # saltan de uno a otro, para que se vea la paleta.
    def __init__(self, rampa, capa="luz", gravedad=0.0, freno=0.0, encoge=True):
        self.rampa, self.capa = rampa, capa
        self.gravedad, self.freno, self.encoge = gravedad, freno, encoge
        self.lista = []

    def emitir(self, x, y, vx, vy, vida, tam=2):
        self.lista.append([x, y, vx, vy, 0.0, vida, tam])

    def rafaga(self, x, y, cuantas, velocidad, vida, tam=2, angulo=0.0, apertura=math.tau, dispersion=0.0):
        for _ in range(int(cuantas)):
            a = angulo + (azar.random() - 0.5) * apertura
            v = velocidad * (0.3 + 0.7 * azar.random())
            self.emitir(x + azar.uniform(-dispersion, dispersion), y + azar.uniform(-dispersion, dispersion),
                        v * math.cos(a), v * math.sin(a), vida * (0.55 + 0.45 * azar.random()), tam)

    def actualizar(self, dt):
        vivas = []
        frenado = max(0.0, 1 - self.freno * dt)
        for p in self.lista:
            p[4] += dt
            if p[4] < p[5]:
                p[3] += self.gravedad * dt
                p[2] *= frenado
                p[3] *= frenado
                p[0] += p[2] * dt
                p[1] += p[3] * dt
                vivas.append(p)
        self.lista = vivas
        return True

    def dibujar(self, sup):
        n = len(self.rampa)
        suma = pygame.BLEND_RGB_ADD if self.capa == "luz" else 0
        for x, y, _, _, edad, vida, tam in self.lista:
            f = edad / vida
            lado = max(1, round(tam * (1 - 0.7 * f))) if self.encoge else tam
            sup.fill(self.rampa[min(n - 1, int(f * n))], (int(x - lado / 2), int(y - lado / 2), lado, lado), suma)


class Rayas(Particulas):
    # Particulas que se dibujan como una rayita en la direccion en que se
    # mueven: lluvia, rachas de viento, chispas rapidas.
    def __init__(self, rampa, capa="luz", gravedad=0.0, freno=0.0, largo=0.03):
        super().__init__(rampa, capa, gravedad, freno, False)
        self.largo = largo

    def dibujar(self, sup):
        n = len(self.rampa)
        for x, y, vx, vy, edad, vida, tam in self.lista:
            color = self.rampa[min(n - 1, int(edad / vida * n))]
            pygame.draw.line(sup, color, (int(x), int(y)), (int(x - vx * self.largo), int(y - vy * self.largo)), tam)


class Trazo:
    # Una figura que dura un rato. funcion(sup, u) la dibuja, con u de 0 a 1.
    def __init__(self, duracion, funcion, capa="luz"):
        self.duracion, self.funcion, self.capa = duracion, funcion, capa
        self.tiempo = 0.0

    def actualizar(self, dt):
        self.tiempo += dt
        return self.tiempo < self.duracion

    def dibujar(self, sup):
        self.funcion(sup, self.tiempo / self.duracion)


class Animacion:

    def __init__(self):
        self.tiempo = 0.0
        self.duracion = 0.0
        # Cuando llega el golpe: ahi cambian las vidas y salen los numeros.
        self.impacto = 0.0
        self.agenda = []
        self.procesos = []
        self.piezas = []
        self.velos = []
        self.sacudidas = []
        self.penumbras = []

    def alargar(self, hasta):
        self.duracion = max(self.duracion, hasta)

    def en(self, momento, funcion):
        self.agenda.append((momento, len(self.agenda), funcion))
        self.alargar(momento)

    def sonido(self, momento, nombre, volumen=1.0):
        self.en(momento, lambda: sonar(nombre, volumen))

    def particulas(self, rampa, capa="luz", gravedad=0.0, freno=0.0, encoge=True):
        grupo = Particulas(rampa, capa, gravedad, freno, encoge)
        self.piezas.append(grupo)
        return grupo

    def rayas(self, rampa, capa="luz", gravedad=0.0, freno=0.0, largo=0.03):
        grupo = Rayas(rampa, capa, gravedad, freno, largo)
        self.piezas.append(grupo)
        return grupo

    def trazo(self, momento, duracion, funcion, capa="luz"):
        self.en(momento, lambda: self.piezas.append(Trazo(duracion, funcion, capa)))
        self.alargar(momento + duracion)

    def durante(self, inicio, fin, funcion):
        # funcion(u, dt) se llama en cada cuadro entre inicio y fin, con u de 0 a 1.
        self.procesos.append([inicio, fin, funcion])
        self.alargar(fin)

    def destello(self, momento, color=blanco, duracion=0.2, fuerza=190):
        self.velos.append((momento, 0.0, 0.0, duracion, color, fuerza))
        self.alargar(momento + duracion)

    def tinte(self, inicio, fin, color, fuerza=70, entrada=0.2, salida=0.3):
        self.velos.append((inicio, entrada, max(0.0, fin - inicio - entrada - salida), salida, color, fuerza))
        self.alargar(fin)

    def sacudir(self, momento, fuerza=5, duracion=0.3):
        self.sacudidas.append((momento, duracion, fuerza))
        self.alargar(momento + duracion)

    def oscurecer(self, inicio, fin, fuerza=130):
        self.penumbras.append((inicio, fin, fuerza))
        self.alargar(fin)

    def actualizar(self, dt):
        self.tiempo += dt
        t = self.tiempo
        listas = sorted(a for a in self.agenda if a[0] <= t)
        self.agenda = [a for a in self.agenda if a[0] > t]
        for _, _, funcion in listas:
            funcion()

        for inicio, fin, funcion in self.procesos:
            if inicio <= t:
                funcion(min(1.0, (t - inicio) / max(0.001, fin - inicio)), dt)
        self.procesos = [p for p in self.procesos if p[1] > t]

        self.piezas = [p for p in self.piezas if p.actualizar(dt)]
        return t < self.duracion

    def dibujar(self, capas):
        for pieza in self.piezas:
            pieza.dibujar(capas.de(pieza.capa))

    def velosActivos(self):
        # Los colores que cubren la pantalla en este momento, con su opacidad.
        activos = []
        for inicio, entrada, sosten, salida, color, fuerza in self.velos:
            t = self.tiempo - inicio
            if t < 0 or t >= entrada + sosten + salida:
                continue
            if t < entrada:
                nivel = t / entrada
            elif t < entrada + sosten:
                nivel = 1.0
            else:
                nivel = 1 - (t - entrada - sosten) / salida
            activos.append((color, int(fuerza * nivel)))
        return activos

    def desplazamiento(self):
        dx = dy = 0.0
        for inicio, duracion, fuerza in self.sacudidas:
            t = self.tiempo - inicio
            if 0 <= t < duracion:
                queda = fuerza * (1 - t / duracion)
                dx += queda * math.sin(t * 83)
                dy += queda * math.cos(t * 67)
        return int(dx), int(dy)

    def penumbra(self):
        nivel = 0
        for inicio, fin, fuerza in self.penumbras:
            t = self.tiempo
            if inicio <= t < fin:
                borde = min(1.0, (t - inicio) / 0.15, (fin - t) / 0.25)
                nivel = max(nivel, int(fuerza * borde))
        return nivel


def cadencia(porSegundo):
    # Para emitir particulas a un ritmo parejo sin importar a cuantos cuadros
    # por segundo corra el juego: devuelve cuantas tocan en este cuadro.
    guardado = [0.0]

    def cuantas(dt):
        guardado[0] += porSegundo * dt
        n = int(guardado[0])
        guardado[0] -= n
        return n
    return cuantas


def anillo(sup, x, y, radio, color, grueso=2, aplastado=1.0):
    ancho, alto = int(radio * 2), int(radio * 2 * aplastado)
    if ancho > 2 * grueso + 1 and alto > 2 * grueso + 1:
        pygame.draw.ellipse(sup, color, (int(x - radio), int(y - radio * aplastado), ancho, alto), grueso)


def disco(sup, x, y, radio, color, aplastado=1.0):
    if radio >= 1:
        pygame.draw.ellipse(sup, color, (int(x - radio), int(y - radio * aplastado), int(radio * 2), max(1, int(radio * 2 * aplastado))))


def estrella(sup, x, y, radio, color, puntas=4, hueco=0.22, giro=0.0):
    if radio < 2:
        return
    lista = []
    for k in range(2 * puntas):
        r = radio if k % 2 == 0 else radio * hueco
        a = giro + math.pi * k / puntas
        lista.append((x + r * math.cos(a), y + r * math.sin(a)))
    pygame.draw.polygon(sup, color, lista)


def mediaLuna(sup, cx, cy, radio, a0, a1, grosor, color, pasos=10):
    # Un arco que se afila en las puntas, como el rastro de un tajo.
    fuera, dentro = [], []
    for k in range(pasos + 1):
        s = k / pasos
        a = a0 + (a1 - a0) * s
        fuera.append((cx + radio * math.cos(a), cy + radio * math.sin(a)))
        r2 = radio - grosor * math.sin(math.pi * s)
        dentro.append((cx + r2 * math.cos(a), cy + r2 * math.sin(a)))
    pygame.draw.polygon(sup, color, fuera + dentro[::-1])


def quebrar(x0, y0, x1, y1, desvio, tramos):
    # Una linea quebrada entre dos puntos, para rayos y grietas.
    largo = math.hypot(x1 - x0, y1 - y0) or 1.0
    nx, ny = -(y1 - y0) / largo, (x1 - x0) / largo
    puntos = [(x0, y0)]
    for k in range(1, tramos):
        s = k / tramos
        d = azar.uniform(-desvio, desvio)
        puntos.append((x0 + (x1 - x0) * s + nx * d, y0 + (y1 - y0) * s + ny * d))
    puntos.append((x1, y1))
    return puntos


def lineaBrillante(sup, puntos, color, grueso, brillo=1.0):
    # Halo del color, cuerpo mas claro y nucleo blanco.
    if len(puntos) < 2:
        return
    pygame.draw.lines(sup, atenuar(color, 0.45 * brillo), False, puntos, grueso + 4)
    pygame.draw.lines(sup, atenuar(color, brillo), False, puntos, grueso + 2)
    pygame.draw.lines(sup, atenuar(blanco, brillo), False, puntos, grueso)


def roca(sup, x, y, radio, paleta, giro=0.0):
    lista, luz = [], []
    for k in range(8):
        a = giro + math.tau * k / 8
        r = radio * (0.78 + 0.22 * math.sin(k * 2.4 + 1))
        lista.append((x + r * math.cos(a), y + r * math.sin(a)))
        luz.append((x - radio * 0.2 + r * 0.55 * math.cos(a), y - radio * 0.25 + r * 0.5 * math.sin(a)))
    pygame.draw.polygon(sup, paleta[1], lista)
    pygame.draw.polygon(sup, paleta[2], luz)
    pygame.draw.polygon(sup, paleta[0], lista, 1)


carpetaEfectos = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recursos", "efectos")
iconosCargados = {}


def icono(nombre):
    # El dibujo del ataque en recursos/efectos, al tamaño de las capas. Si
    # falta el archivo la animacion sigue igual, solo sin esa imagen.
    if nombre not in iconosCargados:
        ruta = os.path.join(carpetaEfectos, nombre.lower().replace(" ", "_") + ".png")
        imagen = None
        if os.path.exists(ruta):
            imagen = pygame.image.load(ruta).convert_alpha()
            imagen = pygame.transform.scale(imagen, (imagen.get_width() // escala, imagen.get_height() // escala))
        iconosCargados[nombre] = imagen
    return iconosCargados[nombre]
