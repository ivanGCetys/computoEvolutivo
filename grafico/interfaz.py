# Piezas de interfaz que usan todas las pantallas: colores, texto, ventanas,
# barras, botones y el cursor. Las ventanas imitan las de los RPG clasicos de
# 16 bits: azul degradado, marco plateado de doble linea y esquinas redondas.
import math

import pygame

# Todo se dibuja sobre un lienzo de este tamaño y la ventana lo escala. Así el
# arte que se agregue después se hace para una sola resolución.
ancho, alto = 1280, 720

colores = {
    "fondo": (24, 26, 32), "panel": (38, 42, 52), "borde": (84, 90, 106),
    "texto": (236, 236, 232), "textoSuave": (160, 164, 176),
    "boton": (58, 64, 80), "botonEncima": (78, 88, 112), "botonApagado": (44, 46, 54),
    "resaltado": (240, 200, 80),
    "vida": (88, 190, 110), "mana": (86, 150, 230), "vidaJefe": (220, 92, 92),
    "dano": (240, 96, 88), "cura": (110, 220, 130), "aviso": (240, 200, 80),
    "heroe": (120, 190, 255), "jefe": (255, 210, 90),
    "sombraTexto": (8, 10, 30),
    # Las ventanas: degradado azul de arriba a abajo y un marco plateado.
    "ventanaArriba": (48, 70, 168), "ventanaAbajo": (10, 16, 66),
    "marcoClaro": (236, 240, 252), "marcoMedio": (150, 160, 196), "marcoOscuro": (14, 16, 34),
    "ventanaApagada": (40, 44, 70),
}

fuentesCargadas = {}


def fuente(tamano):
    # La fuente por omisión de pygame trae acentos y no obliga a incluir un
    # archivo de fuente en el repositorio. Cuando haya una propia se carga aquí.
    if tamano not in fuentesCargadas:
        if not pygame.font.get_init():
            pygame.font.init()
        fuentesCargadas[tamano] = pygame.font.Font(None, tamano)
    return fuentesCargadas[tamano]


def recortarTexto(texto, tamano, anchoMax):
    if anchoMax is None or fuente(tamano).size(texto)[0] <= anchoMax:
        return texto
    while texto and fuente(tamano).size(texto + "...")[0] > anchoMax:
        texto = texto[:-1]
    return texto + "..."


textosCargados = {}


def renderizar(texto, tamano, color):
    # Los mismos textos se dibujan en cada cuadro; guardarlos ahorra trabajo.
    clave = (texto, tamano, color)
    if clave not in textosCargados:
        if len(textosCargados) > 3000:
            textosCargados.clear()
        textosCargados[clave] = fuente(tamano).render(texto, True, color)
    return textosCargados[clave]


def dibujarTexto(lienzo, texto, pos, tamano=24, color=None, centrado=False, anchoMax=None, contorno=False, sombra=True):
    texto = recortarTexto(texto, tamano, anchoMax)
    imagen = renderizar(texto, tamano, color or colores["texto"])
    rect = imagen.get_rect(center=pos) if centrado else imagen.get_rect(topleft=pos)
    if contorno:
        # Sobre el escenario, sobre todo el dorado de la segunda fase, el texto
        # se pierde; un borde oscuro lo separa de cualquier fondo.
        oscuro = renderizar(texto, tamano, colores["fondo"])
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, -1), (-1, 1), (1, 1)):
            lienzo.blit(oscuro, rect.move(dx, dy))
    elif sombra:
        # Como en las ventanas de los RPG clasicos: una sombra abajo a la derecha.
        lienzo.blit(renderizar(texto, tamano, colores["sombraTexto"]), rect.move(2, 2))
    lienzo.blit(imagen, rect)
    return rect


def dibujarTextoRico(lienzo, segmentos, pos, tamano=24):
    # Una línea armada con pedazos de distinto color. Cada segmento es un par
    # de (texto, color), y un color None es el del texto normal.
    x, y = pos
    for texto, color in segmentos:
        x = dibujarTexto(lienzo, texto, (x, y), tamano, color).right


def dibujarTabla(lienzo, filas, pos, anchoColumna=150, columnas=2, tamano=21, altoFila=24):
    # Pares de (etiqueta, valor) en columnas, con los valores alineados a la derecha.
    for k, (etiqueta, valor) in enumerate(filas):
        x = pos[0] + (k % columnas) * anchoColumna
        y = pos[1] + (k // columnas) * altoFila
        dibujarTexto(lienzo, etiqueta, (x, y), tamano, colores["textoSuave"])

        imagen = fuente(tamano).render(str(valor), True, colores["texto"])
        lienzo.blit(imagen, imagen.get_rect(topright=(x + anchoColumna - 22, y)))


def filasDeStats(stats, mana=None):
    # El jefe no tiene maná, y en su lugar va la velocidad para que los ataques
    # y las defensas sigan quedando emparejados en la misma fila.
    segundo = ("MANA", mana) if mana is not None else ("VEL", "%.1f" % stats["vel"])
    filas = [("VIDA", stats["hp"]), segundo,
             ("ATK NOR", stats["atk"]), ("DEF NOR", stats["defe"]),
             ("ATK MAG", stats["atkMag"]), ("DEF MAG", stats["defMag"])]
    if mana is not None:
        filas.append(("VEL", "%.1f" % stats["vel"]))
    return filas


ventanasCargadas = {}


def ventana(tamano, arriba=None, abajo=None, alfa=255):
    # La superficie de una ventana de cierto tamaño, ya con su marco.
    clave = (tuple(tamano), arriba, abajo, alfa)
    if clave not in ventanasCargadas:
        w, h = tamano
        arriba = arriba or colores["ventanaArriba"]
        abajo = abajo or colores["ventanaAbajo"]
        sup = pygame.Surface((w, h), pygame.SRCALPHA)
        fondo = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            t = y / max(1, h - 1)
            color = tuple(int(a + (b - a) * t) for a, b in zip(arriba, abajo))
            pygame.draw.line(fondo, color + (alfa,), (0, y), (w, y))
        # Unas lineas finas horizontales, como la trama de las ventanas de antes.
        for y in range(3, h, 4):
            pygame.draw.line(fondo, (255, 255, 255, 10), (0, y), (w, y))
        mascara = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mascara, (255, 255, 255, 255), (0, 0, w, h), border_radius=9)
        fondo.blit(mascara, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        sup.blit(fondo, (0, 0))
        pygame.draw.rect(sup, colores["marcoOscuro"], (0, 0, w, h), width=2, border_radius=9)
        pygame.draw.rect(sup, colores["marcoClaro"], (2, 2, w - 4, h - 4), width=2, border_radius=8)
        pygame.draw.rect(sup, colores["marcoMedio"], (4, 4, w - 8, h - 8), width=1, border_radius=7)
        pygame.draw.rect(sup, colores["marcoOscuro"], (5, 5, w - 10, h - 10), width=1, border_radius=6)
        # Un adorno en cada esquina: un rombito dorado.
        for cx, cy in ((7, 7), (w - 8, 7), (7, h - 8), (w - 8, h - 8)):
            pygame.draw.polygon(sup, (255, 222, 140), [(cx, cy - 3), (cx + 3, cy), (cx, cy + 3), (cx - 3, cy)])
            pygame.draw.polygon(sup, (120, 80, 20), [(cx, cy - 3), (cx + 3, cy), (cx, cy + 3), (cx - 3, cy)], 1)
        if len(ventanasCargadas) > 200:
            ventanasCargadas.clear()
        ventanasCargadas[clave] = sup
    return ventanasCargadas[clave]


def dibujarPanel(lienzo, rect, color=None, alfa=255):
    rect = pygame.Rect(rect)
    if color is not None:
        abajo = tuple(max(0, c // 3) for c in color)
        lienzo.blit(ventana(rect.size, color, abajo, alfa), rect)
    else:
        lienzo.blit(ventana(rect.size, alfa=alfa), rect)


def dibujarTitulo(lienzo, texto, rect):
    # Una pestaña con el nombre de la ventana, montada sobre su borde de arriba.
    rect = pygame.Rect(rect)
    imagen = renderizar(texto, 22, colores["resaltado"])
    pestana = pygame.Rect(rect.x + 18, rect.y - 13, imagen.get_width() + 26, 26)
    dibujarPanel(lienzo, pestana)
    dibujarTexto(lienzo, texto, pestana.center, 22, colores["resaltado"], centrado=True)


def dibujarBarra(lienzo, rect, fraccion, color, fantasma=None):
    # Una barra con hueco oscuro, relleno con brillo arriba y marco fino.
    # fantasma es lo que tenia hace un momento: se ve en blanco y se va
    # vaciando detras del color, para que se note cuanto quito el golpe.
    rect = pygame.Rect(rect)
    pygame.draw.rect(lienzo, colores["marcoOscuro"], rect.inflate(2, 2), border_radius=3)
    pygame.draw.rect(lienzo, (30, 30, 46), rect, border_radius=3)
    if fantasma is not None and fantasma > fraccion:
        resto = rect.copy()
        resto.width = int(rect.width * max(0.0, min(1.0, fantasma)))
        pygame.draw.rect(lienzo, (240, 236, 220), resto, border_radius=3)
    lleno = rect.copy()
    lleno.width = int(rect.width * max(0.0, min(1.0, fraccion)))
    if lleno.width > 0:
        pygame.draw.rect(lienzo, color, lleno, border_radius=3)
        claro = tuple(min(255, c + 70) for c in color)
        if lleno.height >= 4:
            pygame.draw.line(lienzo, claro, (lleno.x + 1, lleno.y + 1), (lleno.right - 2, lleno.y + 1))
        oscuro = tuple(c // 2 for c in color)
        pygame.draw.line(lienzo, oscuro, (lleno.x + 1, lleno.bottom - 1), (lleno.right - 2, lleno.bottom - 1))
    pygame.draw.rect(lienzo, colores["marcoMedio"], rect.inflate(2, 2), width=1, border_radius=3)


# La mano que señala la opcion elegida, en pixel art. g es guante, o contorno,
# s sombra del guante.
formaCursor = [
    "......oooo.......",
    ".....oggggo......",
    "oooooggggggooooo.",
    "oggggggggggggggo.",
    "ogggggggggggoooo.",
    "oggggggggggggo...",
    "ogggggggggggsoo..",
    "osggggggggggso...",
    ".osssgggggsoo....",
    "..oooooooooo.....",
]
cursorCargado = []


def dibujarCursor(lienzo, x, y, tiempo=None):
    # x, y es la punta del dedo. El cursor se mece de lado a lado.
    if not cursorCargado:
        escala = 2
        sup = pygame.Surface((len(formaCursor[0]) * escala, len(formaCursor) * escala), pygame.SRCALPHA)
        tonos = {"o": (20, 20, 36), "g": (250, 250, 250), "s": (170, 176, 200)}
        for fy, fila in enumerate(formaCursor):
            for fx, c in enumerate(fila):
                if c in tonos:
                    sup.fill(tonos[c], (fx * escala, fy * escala, escala, escala))
        cursorCargado.append(sup)
    sup = cursorCargado[0]
    if tiempo is None:
        tiempo = pygame.time.get_ticks() / 1000
    vaiven = 3 if math.sin(tiempo * 7) > 0 else 0
    lienzo.blit(sup, (x - sup.get_width() - vaiven, y - sup.get_height() // 2))


class Boton:
    # Dos estilos: "ventana" es un boton suelto con su propio marco, y
    # "lista" es una opcion de texto dentro de otra ventana, como en los menus
    # de combate. En los dos el cursor de mano señala al que tiene el foco.

    def __init__(self, rect, texto, alHacerClic, activo=True, tamano=24, estilo="ventana", centrado=True):
        self.rect = pygame.Rect(rect)
        self.texto, self.alHacerClic = texto, alHacerClic
        self.activo, self.tamano = activo, tamano
        self.estilo, self.centrado = estilo, centrado
        self.marcado = False
        self.foco = False

    def manejarEvento(self, evento):
        if (self.activo and evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1
                and self.rect.collidepoint(evento.pos)):
            self.alHacerClic()
            return True
        return False

    def dibujar(self, lienzo, posRaton=None):
        encima = self.foco or (posRaton is not None and self.rect.collidepoint(posRaton))
        if self.estilo == "ventana":
            if not self.activo:
                dibujarPanel(lienzo, self.rect, colores["ventanaApagada"])
            elif encima or self.marcado:
                dibujarPanel(lienzo, self.rect, (74, 100, 210))
            else:
                dibujarPanel(lienzo, self.rect)
            if self.marcado:
                pygame.draw.rect(lienzo, colores["resaltado"], self.rect.inflate(-6, -6), width=2, border_radius=7)
        colorTexto = colores["texto"] if self.activo else (120, 124, 150)
        if self.centrado and self.estilo == "ventana":
            dibujarTexto(lienzo, self.texto, self.rect.center, self.tamano, colorTexto, centrado=True,
                         anchoMax=self.rect.width - 24)
        else:
            dibujarTexto(lienzo, self.texto, (self.rect.x + 14, self.rect.centery - self.tamano // 3),
                         self.tamano, colorTexto, anchoMax=self.rect.width - 24)
        if self.foco:
            dibujarCursor(lienzo, self.rect.x + 6, self.rect.centery)


def moverFoco(botones, actual, tecla):
    # Con las flechas el foco salta al boton mas cercano en esa direccion.
    # Devuelve el indice nuevo, o el mismo si no hay nada para alla.
    if not botones:
        return actual
    if actual is None or actual >= len(botones):
        return 0
    direcciones = {pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1), pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0)}
    if tecla not in direcciones:
        return actual
    dx, dy = direcciones[tecla]
    origen = botones[actual].rect.center
    mejor, distancia = actual, None
    for k, boton in enumerate(botones):
        if k == actual:
            continue
        vx, vy = boton.rect.centerx - origen[0], boton.rect.centery - origen[1]
        avance = vx * dx + vy * dy
        if avance <= 0:
            continue
        lateral = abs(vx * dy) + abs(vy * dx)
        costo = avance + 2.5 * lateral
        if distancia is None or costo < distancia:
            mejor, distancia = k, costo
    return mejor
