# Las pantallas del juego: título, elegir jefe, armar equipo y combate.
# Cada pantalla es una clase con tres métodos que el ciclo principal llama en
# cada cuadro: manejarEvento, actualizar y dibujar.
import math
import time
import pygame

import motor as m
import jugar
from grafico.animaciones import suave
from grafico.interfaz import (ancho, alto, colores, dibujarTexto, dibujarTextoRico, dibujarTabla,
                              filasDeStats, dibujarPanel, dibujarBarra, Boton, moverFoco, dibujarTitulo,
                              dibujarCursor)
from grafico.recursos import (obtenerEscenario, obtenerImagen, obtenerSprite, obtenerSpriteJefe, poseDelJefe,
                              reproducirSonido, reproducirMusica)
from grafico.cinematica import CinematicaFase2
from grafico import animaciones
import random
from grafico.efectos import numerosDeTurno
from grafico.animaciones import Capas, Lugar
from grafico import recetas
from grafico.recetas import Contexto, crearAnimacion, crearApoyo
from grafico.puente import PartidaEnHilo

tamanoHeroe, tamanoJefe = (120, 128), (300, 330)
lugaresHeroes = [(250, 59), (430, 101), (250, 253), (430, 295)]
# La primera fase va un poco mas arriba; la segunda es mas alta y no cabria.
lugaresJefe = {False: (800, -6), True: (800, 9)}
altoEscenario = 500
tamanoRetrato = (130, 140)
alturaHeroe = 120

# Cuanto dura cada reaccion de los heroes y cada cuanto saltan al celebrar.
duracionDano = 0.45
fraccionHerido = 0.25
periodoSalto, alturaSalto = 0.55, 26

# Segundos que se queda en pantalla cada evento del combate antes de pasar al
# siguiente. El jugador no puede cambiar la velocidad, así que estos números
# son el ritmo del juego. Un turno dura más si su diálogo trae varias líneas.
pausaPorEvento = {"inicio": 0.2, "ronda": 0.45, "planes": 0.0, "turno": 1.15, "fase2": 2.0}
pausaPorLineaExtra = 0.18

# Tiempos de la animación de ataque, en segundos desde que empieza: dos pasos
# al frente, estirarse hacia atrás para tomar impulso, estirarse hacia el
# frente para soltar el golpe y volver a su lugar.
finPasos, finImpulso, finGolpe, finRegreso = 0.24, 0.38, 0.50, 0.80
avanceHeroe, avanceJefe = 56, 40
tiemposCortos = (finPasos, finImpulso, finGolpe, finRegreso)

# Los ataques cuerpo a cuerpo de los heroes corren hasta enfrente del jefe,
# asi que sus pasos duran mas. El efecto del golpe sale ya pegado al jefe y
# llega casi de inmediato.
tiemposCarrera = (0.34, 0.46, 0.56, 0.92)
distanciaAlJefe = 175

# El jefe tambien se lanza hacia un heroe cuando le pega con un golpe fisico
# a el solo, pero no llega hasta el: es tan grande que taparia a medio
# equipo. Avanza hasta el centro de la arena, se acerca un poco a la fila de
# su objetivo y desde ahi suelta el golpe.
avanceMaximoJefe, bajadaMaximaJefe, subidaMaximaJefe = 235, 46, 30

# Quien lanza magia no camina: alza los brazos, suelta el conjuro en este
# momento y aguanta la pose hasta que casi termina.
momentoDeConjuro = 0.3
duracionDestelloGolpe = 0.1
duracionEsquiva = 0.3

# En reposo los personajes se mecen un poco: los heroes y el jefe suben y
# bajan un par de pixeles, y el jefe con alas flota.
ritmoRespiro, flotacionJefe = 2.6, 6
anchoSombra = {"heroe": 84, "jefe": 210}

# Lo que hace que un heroe reciba menos daño se ve como un escudo sobre su
# cabeza, del color de su proteccion. El motor dice en cada turno cuales
# siguen activas, asi que el escudo se va justo cuando se acaba el efecto.
coloresEscudo = {"total": (255, 215, 110), "defensa": (120, 190, 255), "bloqueo": (200, 205, 220)}


class Escena:
    # Lo comun a todas las pantallas: sus botones se pueden recorrer con las
    # flechas o con el raton, la mano señala al que tiene el foco y Enter lo
    # elige. Escape llama a alCancelar si la pantalla lo define.

    def __init__(self, juego):
        self.juego = juego
        self.botones = []
        self.foco = None

    def navegables(self):
        return [b for b in self.botones if b.activo]

    def ponerFoco(self, boton, sonar=True):
        if boton is self.foco:
            return
        if self.foco is not None:
            self.foco.foco = False
        self.foco = boton
        if boton is not None:
            boton.foco = True
            if sonar:
                reproducirSonido("cursor", 0.7)

    def manejarEvento(self, evento):
        navegables = self.navegables()
        if self.foco is not None and self.foco not in navegables:
            self.ponerFoco(navegables[0] if navegables else None, False)
        if evento.type == pygame.MOUSEMOTION:
            for boton in navegables:
                if boton.rect.collidepoint(evento.pos):
                    self.ponerFoco(boton)
        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            for boton in self.botones:
                if boton.rect.collidepoint(evento.pos):
                    reproducirSonido("aceptar" if boton.activo else "error")
                    if boton.manejarEvento(evento):
                        return True
        elif evento.type == pygame.KEYDOWN:
            if evento.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT) and navegables:
                actual = navegables.index(self.foco) if self.foco in navegables else None
                nuevo = moverFoco(navegables, actual, evento.key) if actual is not None else 0
                self.ponerFoco(navegables[nuevo])
                return True
            if evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_z) and self.foco is not None:
                reproducirSonido("aceptar")
                self.foco.alHacerClic()
                return True
            if evento.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_x) and hasattr(self, "alCancelar"):
                reproducirSonido("cancelar")
                self.alCancelar()
                return True
        return False

    def actualizar(self, dt):
        pass

    def dibujarFondo(self, lienzo, nombre):
        lienzo.blit(obtenerImagen("escenarios", nombre, (ancho, alto)), (0, 0))

    def dibujarBotones(self, lienzo):
        for boton in self.botones:
            boton.dibujar(lienzo, None)


class EscenaEquipo(Escena):
    # Armar el equipo: seis tarjetas, una por clase, de las que se eligen
    # cuatro. Abajo van los elegidos y el jefe contra el que se va a pelear.

    def __init__(self, juego, crom=None):
        super().__init__(juego)
        from entrenamiento import jefeOptimo
        jefe, entrenado = jefeOptimo()
        self.jefe, self.entrenado = jefe, entrenado
        self.crom = crom or jefe["crom"]
        self.elegidos = []
        self.reloj = 0.0

        self.tarjetas = []
        self.botonesTarjeta = []
        for n, nombre in enumerate(m.nombresClases):
            rect = pygame.Rect(30 + (n % 3) * 410, 86 + (n // 3) * 236, 396, 222)
            self.tarjetas.append((rect, nombre, m.crearHeroe(nombre)))
            # Cada tarjeta es tambien un boton invisible para recorrerlas con las flechas.
            self.botonesTarjeta.append(Boton(rect, "", lambda nombre=nombre: self.alternar(nombre), estilo="lista"))

        self.botonPelear = Boton((ancho - 250, alto - 82, 220, 56), "¡A pelear!", self.pelear, activo=False, tamano=32)
        self.botonVolver = Boton((ancho - 250, alto - 146, 220, 50), "Volver", self.alCancelar, tamano=26)
        self.botones = self.botonesTarjeta + [self.botonPelear, self.botonVolver]
        self.ponerFoco(self.botonesTarjeta[0], False)
        reproducirMusica("seleccion")

    def alCancelar(self):
        from grafico.pantallas import EscenaTitulo
        self.juego.cambiarEscena(EscenaTitulo(self.juego))

    def alternar(self, nombre):
        if nombre in self.elegidos:
            self.elegidos.remove(nombre)
            reproducirSonido("cancelar")
        elif len(self.elegidos) < 4:
            self.elegidos.append(nombre)
            reproducirSonido("grito_%s%d" % (nombre.lower(), 1 + len(self.elegidos) % 2), 0.6)
        else:
            reproducirSonido("error")
        self.botonPelear.activo = len(self.elegidos) == 4
        if self.botonPelear.activo:
            self.ponerFoco(self.botonPelear, False)

    def pelear(self):
        # El orden del equipo es siempre el de la tabla de clases, sin importar
        # en qué orden se hayan escogido.
        nombres = [n for n in m.nombresClases if n in self.elegidos]
        self.juego.cambiarEscena(EscenaCombate(self.juego, self.crom, nombres))

    def actualizar(self, dt):
        self.reloj += dt

    def dibujar(self, lienzo):
        fondo = obtenerEscenario("arena", (ancho, alto))
        lienzo.blit(fondo, (0, 0))
        velo = pygame.Surface((ancho, alto))
        velo.fill((4, 4, 20))
        velo.set_alpha(150)
        lienzo.blit(velo, (0, 0))

        dibujarPanel(lienzo, (30, 14, 830, 58))
        dibujarTexto(lienzo, "Arma tu equipo", (52, 26), 40, colores["resaltado"])
        dibujarTexto(lienzo, "Elige 4 de las 6 clases   (%d de 4)" % len(self.elegidos), (330, 34), 26)

        for (rect, nombre, heroe), boton in zip(self.tarjetas, self.botonesTarjeta):
            elegido = nombre in self.elegidos
            dibujarPanel(lienzo, rect, (70, 90, 190) if elegido else None)
            if elegido:
                pygame.draw.rect(lienzo, colores["resaltado"], rect.inflate(-6, -6), width=3, border_radius=8)
                orden = self.elegidos.index(nombre) + 1
                pygame.draw.circle(lienzo, colores["marcoOscuro"], (rect.right - 24, rect.y + 24), 15)
                pygame.draw.circle(lienzo, colores["resaltado"], (rect.right - 24, rect.y + 24), 13)
                dibujarTexto(lienzo, str(orden), (rect.right - 24, rect.y + 25), 24, colores["marcoOscuro"], centrado=True, sombra=False)
            pose = "celebra" if elegido else ""
            brinco = 6 * abs(math.sin(self.reloj * 6)) if (elegido or boton.foco) else 0
            sprite = obtenerSprite(nombre, pose, alturaHeroe)
            lienzo.blit(sprite, sprite.get_rect(midbottom=(rect.x + 18 + tamanoRetrato[0] // 2, rect.y + 6 + tamanoRetrato[1] - brinco)))

            dibujarTexto(lienzo, nombre, (rect.x + 160, rect.y + 14), 32, colores["heroe"])
            dibujarTabla(lienzo, filasDeStats(heroe, heroe["sp"]), (rect.x + 160, rect.y + 48), anchoColumna=118, tamano=20, altoFila=22)
            conjuros = ", ".join(c["nombre"] for c in heroe["conjuros"]) or "4 conjuros al azar en cada combate"
            dibujarTexto(lienzo, conjuros, (rect.x + 18, rect.y + 152), 20, anchoMax=rect.width - 36)
            dibujarTexto(lienzo, heroe["objeto"]["nombre"], (rect.x + 18, rect.y + 176), 20, colores["resaltado"], anchoMax=rect.width - 36)
            dibujarTexto(lienzo, m.describirObjeto(heroe["objeto"]), (rect.x + 18, rect.y + 198), 17,
                         colores["textoSuave"], anchoMax=rect.width - 36)
            if boton.foco:
                dibujarCursor(lienzo, rect.x + 4, rect.y + 40)

        # Abajo: los elegidos y el jefe.
        dibujarPanel(lienzo, (30, 568, 470, 138))
        dibujarTitulo(lienzo, "Tu equipo", (30, 568, 470, 138))
        for k in range(4):
            x = 52 + k * 112
            pygame.draw.rect(lienzo, colores["marcoOscuro"], (x, 588, 96, 104), border_radius=6)
            pygame.draw.rect(lienzo, colores["marcoMedio"], (x, 588, 96, 104), width=1, border_radius=6)
            if k < len(self.elegidos):
                sprite = obtenerSprite(self.elegidos[k], "", 70)
                lienzo.blit(sprite, sprite.get_rect(midbottom=(x + 48, 676)))
                dibujarTexto(lienzo, self.elegidos[k], (x + 48, 682), 17, colores["heroe"], centrado=True)

        dibujarPanel(lienzo, (512, 568, 498, 138))
        dibujarTitulo(lienzo, "El jefe", (512, 568, 498, 138))
        retrato = obtenerSpriteJefe("jefe", False, 0.4)
        lienzo.blit(retrato, retrato.get_rect(midbottom=(588, 700)))
        stats = m.stats_jefe(self.crom)
        dibujarTexto(lienzo, "Vida %d   Ataque %d   Magia %d" % (stats["hp"], stats["atk"], stats["atkMag"]), (666, 590), 21)
        if self.entrenado:
            v = self.jefe["validacion"]
            dibujarTexto(lienzo, "Entrenado el %s" % self.jefe["fecha"], (666, 616), 20, colores["resaltado"])
            dibujarTexto(lienzo, "F validada %.3f, el equipo gana %.0f%%" % (v["fitness"], 100 * v["p_victoria"]), (666, 640), 20)
            dibujarTexto(lienzo, "en promedio de los 15 equipos posibles", (666, 662), 18, colores["textoSuave"])
        else:
            dibujarTexto(lienzo, "El que eligió NSGA-II en el experimento", (666, 616), 20, colores["resaltado"])
            dibujarTexto(lienzo, "Entrena uno propio desde el título", (666, 640), 20)
            dibujarTexto(lienzo, "y será el que enfrentes aquí.", (666, 662), 18, colores["textoSuave"])
        for boton in (self.botonVolver, self.botonPelear):
            boton.dibujar(lienzo)


def agruparOpciones(opciones):
    # Reparte las acciones legales que manda el motor en las categorías del menú.
    grupos = {"ataque": None, "magia": {}, "bloqueo": None, "objetos": {}}
    for accion in opciones:
        if accion[0] == "basico":
            grupos["ataque"] = accion
        elif accion[0] == "conjuro":
            grupos["magia"].setdefault(accion[1], []).append(accion)
        elif accion[0] == "bloquear":
            grupos["bloqueo"] = accion
        else:
            grupos["objetos"].setdefault(accion[1], []).append(accion)
    return grupos


def descripcionDeConjuro(i, k, est):
    yo = est["equipo"][i]
    conj = yo["conjuros"][k]
    lineas = [conj["nombre"]]

    if conj["tipo"] == "ataque":
        clase = "Fisico" if conj["esFisico"] else "Magico"
        if conj["elem"] is not None:
            clase += " de " + m.NOMBRES_ELEM[conj["elem"]]
        lineas.append(clase + ". Daño: %d a %d" % jugar.rangoDano(i, est, conj["poder"], conj["esFisico"], conj["elem"],
                                                                         conj.get("buff")))
        if conj["prioridad"]:
            lineas.append("Se adelanta a todos en la ronda.")
        if conj.get("buff"):
            lineas.append("Ademas sube su ataque x%.1f por %d turnos." % conj["buff"][1:])
    elif conj["tipo"] == "buff":
        stat = "ataque" if conj["buff"][0] == "atk" else "defensa"
        lineas.append("Sube su %s x%.1f por %d turnos." % (stat, conj["buff"][1], conj["buff"][2]))
    elif conj["tipo"] == "cura":
        aQuien = "a todo el equipo" if conj["enGrupo"] else "a un aliado"
        lineas.append("Devuelve %d de vida %s." % (int(yo["atkMag"] * conj["poder"]), aQuien))
    else:
        lineas.append("Anula por completo el siguiente ataque que reciba.")

    lineas.append("Cuesta %d de mana. Tiene %d." % (conj["costo"], est["sp"][i]))
    return lineas


def pocionesLibres(est, clave):
    # Las que quedan sin contar las que otro héroe ya apartó en esta ronda.
    return est["pociones"][clave] - est.get("reservadas", {}).get(clave, 0)


def descripcionDePocion(i, clave, est):
    deVida = clave.startswith("hp")
    porcentaje = int(round(100 * m.efectoPocion[clave]))
    lineas = [m.nombrePocion[clave].capitalize(),
              "Devuelve %d%% de la %s maxima a quien la reciba." % (porcentaje, "vida" if deVida else "mana"),
              "Quedan %d. Las pociones son de todo el equipo." % pocionesLibres(est, clave)]
    apartadas = est.get("reservadas", {}).get(clave, 0)
    if apartadas:
        lineas.append("Otro héroe ya apartó %d para esta ronda." % apartadas)
    return lineas


def descripcionDeDestino(clave, j, est):
    aliado = est["equipo"][j]
    deVida = clave.startswith("hp")
    cantidad = int(m.efectoPocion[clave] * (aliado["hp"] if deVida else aliado["sp"]))
    if deVida:
        tiene = "Tiene %d de %d de vida." % (est["hp"][j], aliado["hp"])
    else:
        tiene = "Tiene %d de %d de mana." % (est["sp"][j], aliado["sp"])
    return [m.nombrePocion[clave].capitalize() + " a " + aliado["nombre"], tiene,
            "Le devuelve %d de %s." % (cantidad, "vida" if deVida else "mana")]


def textoDePlan(accion, est, i):
    # Lo que se escribe sobre un héroe que ya eligió, mientras los demás eligen.
    tipo, cual, objetivo = accion
    if tipo == "basico":
        return "Ataque"
    if tipo == "bloquear":
        return "Bloqueo"
    if tipo == "pocion":
        texto = m.nombrePocion[cual].replace("pocion", "Pocion")
        if objetivo is not None and objetivo != i:
            texto += " a " + est["equipo"][objetivo]["nombre"]
        return texto
    texto = est["equipo"][i]["conjuros"][cual]["nombre"]
    if objetivo is not None:
        texto += " a " + est["equipo"][objetivo]["nombre"]
    return texto


def segmentoDeNombre(nombre):
    if nombre == "Jefe":
        return ("El Jefe", colores["jefe"])
    return (nombre, colores["heroe"])


def frasesDeTurno(ev):
    # El diálogo de un turno: una lista de líneas, cada una hecha de segmentos
    # de (texto, color). Los nombres de los héroes van en azul, el del jefe en
    # amarillo, el daño en rojo y la curación en verde.
    actor = segmentoDeNombre(ev["actor"])
    accion = ev["accion"]
    if ev["elem"] is not None:
        accion += " de " + m.NOMBRES_ELEM[ev["elem"]]

    if ev["accion"] == "Bloquea":
        lineas = [[actor, (" se pone en guardia.", None)]]
    elif ev["accion"].startswith("Carga "):
        lineas = [[actor, (" está cargando %s." % ev["accion"][6:], None)]]
    elif ev["accion"].startswith("Bebe "):
        lineas = [[actor, (" bebió %s." % ev["accion"][5:], None)]]
    elif ev["accion"].startswith("Le da a "):
        quien, pocion = ev["accion"][8:].split(" una ", 1)
        lineas = [[actor, (" le dio una %s a " % pocion, None), segmentoDeNombre(quien), (".", None)]]
    elif ev["accion"].startswith("Busca "):
        lineas = [[actor, (" buscó %s, pero ya no quedaba." % ev["accion"][6:], None)]]
    else:
        nombreAccion = "ataque normal" if ev["accion"] == "Ataque basico" else accion
        verbo = " se adelanta y usó " if ev.get("adelantado") else " usó "
        lineas = [[actor, (verbo + nombreAccion + ".", None)]]

    for nombre, dano, nota in ev["golpes"]:
        objetivo = segmentoDeNombre(nombre)
        if nota == "esquiva":
            lineas.append([objetivo, (" esquivó el ataque.", None)])
        elif nota == "bloqueado":
            lineas.append([objetivo, (" bloqueó el ataque por completo.", None)])
        else:
            linea = [("Golpe critico. ", colores["aviso"])] if nota == "critico" else []
            lineas.append(linea + [objetivo, (" ha recibido ", None), (str(dano), colores["dano"]), (" de daño.", None)])

    for nombre, cantidad in ev["curas"]:
        lineas.append([segmentoDeNombre(nombre), (" recuperó ", None), (str(cantidad), colores["cura"]),
                       (" de vida.", None)])
    for nombre in ev["muertos"]:
        lineas.append([segmentoDeNombre(nombre), (" ha caído.", None)])
    return lineas


def transformacionDeAtaque(t, avance, tiempos=tiemposCortos, bajada=0):
    # Dónde y cómo se dibuja un personaje a los t segundos de empezar su ataque.
    # Devuelve el desplazamiento hacia el frente y hacia abajo, la escala a lo
    # ancho y a lo alto, qué borde se queda fijo al estirarse y si ya va en pose
    # de ataque. avance es cuánto camina al frente y bajada cuánto baja o sube
    # para llegar al jefe; en los ataques cortos es cero. La deformación es puro
    # cambio de escala, así que sirve igual con un marcador que con el arte final.
    pasos, impulso, golpe, regreso = tiempos
    if t < pasos:
        u = t / pasos
        brincos = 2 if bajada == 0 and avance < 100 else 4
        return {"dx": avance * u, "dy": bajada * u - 8 * abs(math.sin(brincos / 2 * 2 * math.pi * u)),
                "sx": 1.0, "sy": 1.0, "ancla": "centro", "pose": False}

    if t < impulso:
        u = (t - pasos) / (impulso - pasos)
        return {"dx": avance, "dy": bajada, "sx": 1 + 0.22 * u, "sy": 1 - 0.10 * u, "ancla": "frente", "pose": False}

    if t < golpe:
        # El estiron dura lo mismo aunque despues se quede un rato junto al objetivo.
        u = min(1.0, (t - impulso) / 0.1)
        return {"dx": avance + 18 * u, "dy": bajada, "sx": 1 + 0.30 * u, "sy": 1 - 0.12 * u, "ancla": "atras", "pose": True}

    if t < regreso:
        u = (t - golpe) / (regreso - golpe)
        return {"dx": (avance + 18) * (1 - u), "dy": bajada * (1 - u), "sx": 1 + 0.30 * (1 - u) ** 2,
                "sy": 1 - 0.12 * (1 - u) ** 2, "ancla": "atras", "pose": u < 0.4}

    return {"dx": 0, "dy": 0, "sx": 1.0, "sy": 1.0, "ancla": "centro", "pose": False}


# El escudo que flota sobre un heroe protegido, en pixel art: o es contorno,
# x el color de su proteccion, s su sombra y + su brillo.
formaEscudo = [
    "oooooooooo",
    "ox+xxxxsso",
    "o+xxxxxsso",
    "oxxxooxsso",
    "oxxxooxsso",
    "oxooooooso",
    "oxxxooxsso",
    ".oxxooxso.",
    "..oxxxso..",
    "...oxso...",
    "....oo....",
]
escudosCargados = {}


def imagenEscudo(tipo, escala=3):
    if tipo not in escudosCargados:
        r, g, b = coloresEscudo[tipo]
        tonos = {"o": (30, 30, 46), "x": (r, g, b), "s": (r * 2 // 3, g * 2 // 3, b * 2 // 3), "+": (255, 255, 255)}
        imagen = pygame.Surface((len(formaEscudo[0]) * escala, len(formaEscudo) * escala), pygame.SRCALPHA)
        for y, fila in enumerate(formaEscudo):
            for x, c in enumerate(fila):
                if c in tonos:
                    imagen.fill(tonos[c], (x * escala, y * escala, escala, escala))
        escudosCargados[tipo] = imagen
    return escudosCargados[tipo]


# Para saber como se mueve quien ataca hace falta saber si su ataque es un
# golpe o un conjuro, y si es de los que el jefe carga un turno antes.
ataquesFisicos = {"Ataque basico"} | {a["nombre"] for a in m.HABILIDADES if a["esFisico"]}
for clase in m.tablaClases.values():
    ataquesFisicos |= {c["nombre"] for c in clase["conjuros"] if c["tipo"] == "ataque"}
ataquesDeCarga = {a["nombre"] for a in m.HABILIDADES if a["carga"]}


def esAtaqueFisico(nombre):
    return nombre in ataquesFisicos


class EscenaCombate(Escena):

    def __init__(self, juego, crom, nombres, semilla=None):
        super().__init__(juego)
        self.crom, self.nombres = crom, nombres

        # Sin semilla fija cada partida sale distinta.
        if semilla is None:
            semilla = int(time.time()) % 10000
        self.partida = PartidaEnHilo(m.reparar(crom), m.armarEquipo(nombres), semilla)

        self.capa = pygame.Surface((ancho, alto))
        self.mostrados = 0
        self.espera = 0.0
        self.ronda = 0
        self.dialogo = []
        self.efectos = []
        self.animaciones = []
        self.capasEfecto = None
        self.velo = None
        self.destelloGolpe = {}
        self.esquivas = {}
        self.sombras = {}
        self.reloj = 0.0
        self.ambiente = recetas.crearAmbiente(self.estadoDelAmbiente)
        self.animacion = None
        self.cinematica = None
        self.letreroFase = 0.0
        self.pausa = None
        self.azar = random.Random(semilla)
        reproducirMusica("batalla")
        reproducirSonido("encuentro")
        # La entrada al combate: franjas negras que se abren, como en los RPG
        # de antes al empezar una pelea, y un letrero con cada ronda nueva.
        self.entrada = 0.0
        self.letreroRonda = 0.0
        self.sinFundido = True
        animaciones.reproductor[0] = reproducirSonido

        # Lo que se ve va un paso atrás de lo que ya calculó el motor, así que
        # la pantalla lleva su propia copia de vidas y maná. Cada golpe se
        # anota en pendientes y se aplica cuando su efecto llega al objetivo.
        self.vida, self.vidaMax = [0] * 4, [1] * 4
        self.mana, self.manaMax = [0] * 4, [1] * 4
        self.vidaJefe, self.vidaJefeMax = 1, 1
        self.pendientes = []
        self.objetoJefe = ""
        self.estadoJefe = ""
        self.poseFijaJefe = None
        self.fase2 = False

        # Estado de cada heroe que no viene del motor sino de lo que se ve:
        # cuanto le queda a su reaccion al golpe, que lo protege y cuanto lleva
        # celebrando. Las protecciones vienen del motor en cada turno.
        self.tiempoDano = [0.0] * 4
        self.protecciones = [[] for _ in range(4)]
        self.fiesta = None
        self.tiempoDanoJefe = 0.0
        # Lo que se veia en las barras hace un momento, que se vacia despacio.
        self.fantasmas = {}
        self.muerteJefe = None

        self.peticionVista = None
        # Lo que ya eligió cada héroe en esta ronda, para que el siguiente lo vea.
        self.planesElegidos = {}
        self.grupos = None
        self.botonesMenu = []
        self.descripciones = []
        self.descripcion = []
        self.nivelMenu = None
        self.focoMenu = 0
        self.ultimoDt = 0.0
        self.esperaResultados = 0.0
        self.botonesFinal = []
        self.botones = [Boton((ancho - 150, 10, 136, 34), "Menú  (Esc)", self.abrirPausa, tamano=20)]

    def salirAlMenu(self):
        self.partida.cancelar()
        from grafico.pantallas import EscenaTitulo
        self.juego.cambiarEscena(EscenaTitulo(self.juego))

    def abrirPausa(self):
        from grafico.pantallas import MenuPausa
        reproducirSonido("pausa")
        self.pausa = MenuPausa(self, self.salirAlMenu)

    def posicionDe(self, nombre):
        if nombre == "Jefe":
            x, y = lugaresJefe[self.fase2]
            return (x + tamanoJefe[0] // 2, y + tamanoJefe[1] // 2)
        x, y = lugaresHeroes[self.nombres.index(nombre)]
        return (x + tamanoHeroe[0] // 2, y + tamanoHeroe[1] // 2)

    def manejarEvento(self, evento):
        if self.pausa is not None:
            self.pausa.manejarEvento(evento)
            return
        if self.cinematica is not None:
            # La cinematica se puede saltar con cualquier tecla o con un clic.
            if evento.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                self.cinematica.saltar()
            return
        for boton in self.botones + self.botonesFinal:
            if boton.manejarEvento(evento):
                return
        if self.botonesFinal and evento.type == pygame.KEYDOWN and evento.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
            self.verResultados()
            return
        for k, boton in enumerate(self.botonesMenu):
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1 and boton.rect.collidepoint(evento.pos):
                if boton.activo:
                    reproducirSonido("cancelar" if boton.texto.endswith("Atras") else "aceptar")
                    boton.alHacerClic()
                else:
                    reproducirSonido("error")
                return
        if evento.type == pygame.MOUSEMOTION and self.botonesMenu:
            for k, boton in enumerate(self.botonesMenu):
                if boton.rect.collidepoint(evento.pos) and k != self.focoMenu:
                    self.moverFocoMenu(k)

        if evento.type != pygame.KEYDOWN:
            return
        if evento.key == pygame.K_ESCAPE and (not self.botonesMenu or self.nivelMenu == "raiz"):
            self.abrirPausa()
            return
        if not self.botonesMenu:
            return
        # Las flechas mueven la mano, Enter elige, cada opción responde a su
        # número y Escape regresa un nivel.
        if pygame.K_1 <= evento.key <= pygame.K_9:
            k = evento.key - pygame.K_1
            if k < len(self.botonesMenu):
                self.moverFocoMenu(k)
                self.elegirFoco()
        elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_z):
            self.elegirFoco()
        elif evento.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
            self.moverFocoMenu(moverFoco(self.botonesMenu, self.focoMenu, evento.key))
        elif evento.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_x) and self.nivelMenu != "raiz":
            reproducirSonido("cancelar")
            self.armarMenu({"objetivo": "magia", "destino": "objetos"}.get(self.nivelMenu, "raiz"))

    def moverFocoMenu(self, k):
        if k is None or not self.botonesMenu:
            return
        k = max(0, min(len(self.botonesMenu) - 1, k))
        if k != self.focoMenu:
            reproducirSonido("cursor", 0.7)
        self.focoMenu = k
        for j, boton in enumerate(self.botonesMenu):
            boton.foco = j == k
        self.descripcion = self.descripciones[k]

    def elegirFoco(self):
        boton = self.botonesMenu[self.focoMenu]
        if boton.activo:
            reproducirSonido("cancelar" if boton.texto.endswith("Atras") else "aceptar")
            boton.alHacerClic()
        else:
            reproducirSonido("error")

    def actualizar(self, dt):
        if self.pausa is not None:
            self.pausa.actualizar(dt)
            return
        self.ultimoDt = dt
        self.actualizarLoQueSeVe(dt)
        self.seguirElCombate()

    def estadoDelAmbiente(self):
        carga = False
        if self.estadoJefe.startswith("Cargando "):
            carga = recetas.elementoDeAtaque.get(self.estadoJefe[9:])
        return {"fase2": self.fase2, "jefe": self.lugarDe("Jefe"), "carga": carga,
                "fiesta": self.fiesta is not None}

    def actualizarLoQueSeVe(self, dt):
        self.reloj += dt
        self.ambiente.actualizar(dt)
        self.efectos = [e for e in self.efectos if e.actualizar(dt)]
        self.animaciones = [a for a in self.animaciones if a.actualizar(dt)]
        self.destelloGolpe = {n: t - dt for n, t in self.destelloGolpe.items() if t > dt}
        self.esquivas = {n: t - dt for n, t in self.esquivas.items() if t > dt}

        if self.animacion is not None:
            self.animacion["tiempo"] += dt
            if self.animacion["tiempo"] >= self.animacion["duracion"]:
                self.animacion = None

        if self.cinematica is not None:
            sigue = self.cinematica.actualizar(dt)
            if self.cinematica.yaEsFase2() and not self.fase2:
                # De vuelta en la arena ya esta todo en la segunda fase.
                self.fase2 = True
                self.letreroFase = 3.0
                self.animaciones = [recetas.transformacion(self.lugarDe("Jefe"), 1.2)]
                reproducirMusica("batalla2", fundido=300)
            if not sigue:
                self.cinematica = None
        self.letreroFase = max(0.0, self.letreroFase - dt)
        self.letreroRonda = max(0.0, self.letreroRonda - dt)
        if self.entrada is not None:
            self.entrada += dt
            if self.entrada > 1.0:
                self.entrada = None

        self.tiempoDano = [max(0.0, t - dt) for t in self.tiempoDano]
        self.tiempoDanoJefe = max(0.0, self.tiempoDanoJefe - dt)
        if self.fiesta is not None:
            self.fiesta += dt

        for pendiente in self.pendientes:
            pendiente["falta"] -= dt
        for pendiente in [p for p in self.pendientes if p["falta"] <= 0]:
            # Quien pierde vida en este momento hace su gesto de dolor, que
            # coincide con la llegada del golpe y no con el inicio del ataque.
            for j, (antes, despues) in enumerate(zip(self.vida, pendiente["vida"])):
                if despues < antes:
                    self.destelloGolpe[self.nombres[j]] = duracionDestelloGolpe
                    # Un quejido cuando el golpe le quita mucho, pero no siempre.
                    if 0 < despues and antes - despues > 0.18 * self.vidaMax[j] and self.azar.random() < 0.6:
                        reproducirSonido("dolor_heroina" if self.nombres[j] == "Clerigo" else "dolor_heroe", 0.8)
                if 0 < despues < antes:
                    self.tiempoDano[j] = duracionDano
                elif despues == 0 < antes:
                    reproducirSonido("caida")
                    self.animaciones.append(recetas.caidaDeHeroe(self.lugarDe(self.nombres[j])))
            for nombre in pendiente.get("esquivan", ()):
                self.esquivas[nombre] = duracionEsquiva
            if pendiente["vidaJefe"] < self.vidaJefe:
                self.destelloGolpe["Jefe"] = duracionDestelloGolpe
            if pendiente["vidaJefe"] <= 0 < self.vidaJefe:
                self.muerteJefe = 0.0
                # El jefe cae: su final se ve completo antes de anunciar la victoria.
                final = recetas.derrotaDelJefe(self.lugarDe("Jefe"), self.fase2)
                self.animaciones.append(final)
                self.espera = max(self.espera, final.duracion)
            if 0 < pendiente["vidaJefe"] < self.vidaJefe:
                self.tiempoDanoJefe = duracionDano
                if self.vidaJefe - pendiente["vidaJefe"] > 0.07 * self.vidaJefeMax and self.azar.random() < 0.5:
                    reproducirSonido("jefe_dolor", 0.7)
            self.vida, self.mana, self.vidaJefe = pendiente["vida"], pendiente["mana"], pendiente["vidaJefe"]
            # Los escudos cambian junto con la vida: el bloqueo total se va
            # cuando le llega el golpe y no cuando el jefe empieza a atacar.
            self.protecciones = pendiente["protecciones"]
        self.pendientes = [p for p in self.pendientes if p["falta"] > 0]
        self.espera -= dt

    def seguirElCombate(self):
        registro = self.partida.registro
        if self.espera <= 0 and self.mostrados < len(registro):
            ev = registro[self.mostrados]
            self.mostrados += 1
            self.espera = pausaPorEvento[ev["tipo"]] + self.mostrarEvento(ev)

        # El motor corre en otro hilo. Primero se lee si espera respuesta o ya
        # terminó y después cuántos eventos lleva: si fuera al revés, podría
        # agregar los últimos eventos en medio y el menú o el final saldrían
        # antes de mostrarlos.
        peticion, terminada = self.partida.peticion, self.partida.terminada()
        alDia = self.mostrados == len(registro) and self.espera <= 0
        if alDia and peticion is not None and self.peticionVista is not peticion:
            self.abrirMenu(peticion)
        if alDia and terminada and not self.botonesFinal:
            self.mostrarFinal()
        if self.botonesFinal:
            self.esperaResultados -= self.ultimoDt
            if self.esperaResultados <= 0:
                self.verResultados()
                return

        if self.botonesMenu:
            raton = pygame.mouse.get_pos()
            for boton, lineas in zip(self.botonesMenu, self.descripciones):
                if boton.rect.collidepoint(raton):
                    self.descripcion = lineas

    def mostrarEvento(self, ev):
        # Pone en pantalla un evento del registro y devuelve cuánto tiempo extra
        # hay que dejarlo, además de la pausa normal de su tipo.
        if ev["tipo"] == "inicio":
            self.vida, self.vidaMax = list(ev["hp_equipo"]), list(ev["hp_equipo"])
            self.mana, self.manaMax = list(ev["sp_equipo"]), list(ev["sp_equipo"])
            self.vidaJefe = self.vidaJefeMax = ev["jefe"]["hp"]
            self.objetoJefe = ev["objeto"]
            return 0.0

        if ev["tipo"] == "planes":
            # Ya eligieron todos; empieza a correr la ronda.
            self.planesElegidos = {}
            return 0.0

        if ev["tipo"] == "ronda":
            self.ronda = ev["ronda"]
            self.letreroRonda = 1.1
            self.dialogo = [[("Ronda %d" % ev["ronda"], None)]]
            return 0.0

        if ev["tipo"] == "fase2":
            # La cinematica de la segunda fase: el combate espera a que termine.
            self.cinematica = CinematicaFase2(self)
            self.animaciones.append(recetas.previaTransformacion(self.lugarDe("Jefe"), self.cinematica.previa))
            reproducirMusica(None, fundido=900)
            self.objetoJefe = ev["objeto"]
            self.dialogo = [[segmentoDeNombre("Jefe"), (" entra en su segunda fase.", None)],
                            [("Cambia a %s y aprende %s." % (ev["objeto"], " y ".join(ev["nuevos"])), None)]]
            return self.cinematica.duracion + 0.4 - pausaPorEvento["fase2"]

        self.dialogo = frasesDeTurno(ev)
        duracion = self.animarTurno(ev)
        # El turno no se acaba hasta que termina su animacion.
        return max(pausaPorLineaExtra * max(0, len(self.dialogo) - 2), duracion + 0.15 - pausaPorEvento["turno"])

    def lugarDe(self, nombre):
        # Donde esta parado alguien, para las animaciones: el centro de su
        # cuerpo y la altura del piso bajo sus pies.
        x, y = self.posicionDe(nombre)
        if nombre == "Jefe":
            abajo = lugaresJefe[self.fase2][1] + tamanoJefe[1]
            return Lugar(x, abajo - 140, abajo - 12)
        return Lugar(x, y, lugaresHeroes[self.nombres.index(nombre)][1] + tamanoHeroe[1])

    def animarTurno(self, ev):
        # Arma lo que se ve en un turno: como se mueve quien actua, la
        # animacion de su ataque y en que momento cambian las vidas. Devuelve
        # cuanto dura todo.
        esJefe = ev["actor"] == "Jefe"
        ataca = bool(ev["golpes"])
        nombre = ev["accion"]
        fisico = esAtaqueFisico(nombre)
        self.animacion = {"actor": ev["actor"], "tiempo": 0.0, "ataca": ataca, "duracion": 0.35}
        origen = self.lugarDe(ev["actor"])
        t0 = 0.0

        if ataca and not esJefe and ev["actor"] != "Mago":
            # Todos los heroes menos el mago pegan cuerpo a cuerpo, tambien con
            # sus conjuros de ataque: corren hasta enfrente del jefe y regresan.
            hx, hy = self.posicionDe(ev["actor"])
            jx, _ = self.posicionDe("Jefe")
            piso = lugaresJefe[self.fase2][1] + tamanoJefe[1] - 12
            self.animacion["carrera"] = (jx - distanciaAlJefe - hx, piso - (hy + tamanoHeroe[1] // 2))
            origen = Lugar(jx - distanciaAlJefe, piso - tamanoHeroe[1] // 2, piso)
            t0 = tiemposCarrera[1]
        elif ataca and esJefe and fisico and len(ev["golpes"]) == 1 and nombre not in ataquesDeCarga:
            _, hy = self.posicionDe(ev["golpes"][0][0])
            jx, jy = self.posicionDe("Jefe")
            pisoJefe = lugaresJefe[self.fase2][1] + tamanoJefe[1] - 12
            bajada = max(-subidaMaximaJefe, min(bajadaMaximaJefe, hy + tamanoHeroe[1] // 2 + 12 - pisoJefe))
            self.animacion["carrera"] = (avanceMaximoJefe, bajada)
            origen = Lugar(jx - avanceMaximoJefe, pisoJefe - 128 + bajada, pisoJefe + bajada)
            t0 = tiemposCarrera[1]
        elif ataca and (not fisico or ev["actor"] == "Mago"):
            t0 = momentoDeConjuro
            self.animacion["sosten"] = (t0, t0 + 0.3)
        elif ataca:
            t0 = tiemposCortos[1]
            self.animacion["duracion"] = tiemposCortos[3]

        if not esJefe:
            # Atacar con el arma usa la pose de ataque; los conjuros, las curas
            # y las mejoras usan la de magia.
            cuerpoACuerpo = "carrera" in self.animacion
            sinMagia = nombre.startswith(("Bebe ", "Le da a ", "Busca "))
            self.animacion["poseHeroe"] = "ataque" if cuerpoACuerpo else ("" if sinMagia else "magia")
            if nombre == "Bloquea":
                self.animacion["poseHeroe"] = "bloqueo"

        if esJefe:
            if nombre.startswith("Carga "):
                # Mientras carga se queda en la pose del ataque que va a soltar.
                self.estadoJefe = "Cargando " + nombre[6:]
                self.poseFijaJefe = poseDelJefe(nombre[6:])
            else:
                self.estadoJefe = ""
                self.poseFijaJefe = None
            self.animacion["pose"] = poseDelJefe(nombre)
            self.animacion["magico"] = not fisico

        self.gritar(ev, nombre, fisico, t0)
        if ataca:
            objetivos = [self.lugarDe(quien) for quien, _, _ in ev["golpes"]]
            contexto = Contexto(nombre, ev["elem"], origen, objetivos, t0, -1 if esJefe else 1, ev["actor"])
            animacion = crearAnimacion(contexto, fisico)
        else:
            objetivos = [self.lugarDe(quien) for quien, _ in ev["curas"]]
            if nombre.startswith("Le da a "):
                # Una de maná no deja curas, así que el que la recibe sale del texto.
                objetivos = [self.lugarDe(nombre[8:].split(" una ", 1)[0])]
            contexto = Contexto(nombre, ev["elem"], origen, objetivos, t0, -1 if esJefe else 1, ev["actor"])
            animacion = crearApoyo(contexto)

        impacto, duracion = 0.0, self.animacion["duracion"]
        if animacion is not None:
            self.animaciones.append(animacion)
            impacto = animacion.impacto
            if ataca:
                notas = [(self.lugarDe(quien), nota) for quien, _, nota in ev["golpes"]]
                recetas.detallesDelGolpe(animacion, impacto, notas)
            if "carrera" in self.animacion:
                # Se queda junto a su objetivo hasta que el golpe termina de pegar.
                aguante = min(0.5, max(0.0, impacto - t0 - 0.08))
                pasos, impulso, pega, regreso = tiemposCarrera
                self.animacion["tiempos"] = (pasos, impulso, pega + aguante, regreso + aguante)
                self.animacion["duracion"] = regreso + aguante
            elif "sosten" in self.animacion:
                self.animacion["sosten"] = (t0, max(t0 + 0.3, animacion.duracion - 0.35))
                self.animacion["duracion"] = self.animacion["sosten"][1]
            duracion = max(self.animacion["duracion"], animacion.duracion)

        self.efectos.extend(numerosDeTurno(ev, self.posicionDe, impacto))
        self.pendientes.append({"falta": impacto,
                                "vida": list(ev["hp_equipo"]), "mana": list(ev["sp_equipo"]),
                                "protecciones": ev.get("protecciones", self.protecciones),
                                "esquivan": [quien for quien, _, nota in ev["golpes"] if nota == "esquiva"],
                                "vidaJefe": ev["hp_jefe"]})
        return duracion

    def gritar(self, ev, nombre, fisico, t0):
        # Unos que otros gritos: los heroes al lanzarse a pegar y el jefe en sus
        # ataques fuertes. Se agendan como sonido de una animacion corta.
        voz = None
        if ev["actor"] == "Jefe":
            if nombre in ataquesDeCarga or (ev["golpes"] and len(ev["golpes"]) > 1 and self.azar.random() < 0.7):
                voz = ("jefe_rugido", 0.0, 0.85)
            elif ev["golpes"] and fisico and self.azar.random() < 0.55:
                voz = ("jefe_golpe", 0.1, 0.8)
        elif ev["golpes"] and ev["actor"] != "Mago" and self.azar.random() < 0.65:
            voz = ("grito_%s%d" % (ev["actor"].lower(), self.azar.choice((1, 2))), max(0.0, t0 - 0.15), 0.85)
        elif ev["golpes"] and self.azar.random() < 0.35:
            voz = ("grito_mago%d" % self.azar.choice((1, 2)), 0.05, 0.75)
        if voz is not None:
            from grafico.animaciones import Animacion
            aviso = Animacion()
            aviso.sonido(voz[1], voz[0], voz[2])
            aviso.alargar(voz[1] + 0.05)
            self.animaciones.append(aviso)

    def dibujarEscudo(self, lienzo, j, base):
        # Un solo escudo aunque tenga varias protecciones; manda la mas fuerte.
        tipo = next((t for t in ("total", "defensa", "bloqueo") if t in self.protecciones[j]), None)
        if tipo is None or self.vida[j] <= 0:
            return
        flota = round(2 * math.sin(pygame.time.get_ticks() / 250))
        lienzo.blit(imagenEscudo(tipo), (base.right - 18, base.y + 2 + flota))

    def abrirMenu(self, peticion):
        # El motor está detenido esperando la respuesta, así que su estado se
        # puede leer sin riesgo para armar las opciones y sus descripciones.
        self.peticionVista = peticion
        self.grupos = agruparOpciones(peticion["opciones"])
        self.dialogo = []
        self.armarMenu("raiz")

    def armarMenu(self, nivel, conjuro=None):
        # El menú tiene hasta tres niveles: las categorías, la lista de conjuros
        # o de objetos, y el aliado al que va una cura. Cada entrada lleva su
        # texto, si está activa, qué pasa al elegirla y su descripción.
        peticion, grupos = self.peticionVista, self.grupos
        est, i = peticion["est"], peticion["heroe"]
        yo = est["equipo"][i]
        entradas = []

        if nivel == "raiz":
            rango = jugar.rangoDano(i, est, m.PODER_BASICO, True, None)
            entradas.append(("Ataque", True, lambda: self.responder(grupos["ataque"]),
                             ["Ataque normal", "Fisico. Daño: %d a %d" % rango, "No gasta mana."]))
            entradas.append(("Magia", bool(grupos["magia"]), lambda: self.armarMenu("magia"),
                             ["Magia", "Los conjuros de %s. Todos gastan mana." % yo["nombre"],
                              "Tiene %d de %d de mana." % (est["sp"][i], yo["sp"])]))
            entradas.append(("Bloqueo", True, lambda: self.responder(grupos["bloqueo"]),
                             ["Bloqueo", "No hace nada en este turno.",
                              "Recibe la mitad del daño hasta su siguiente turno."]))
            hayPociones = any(pocionesLibres(est, c) > 0 for c in m.pocionesIniciales)
            entradas.append(("Objetos", bool(grupos["objetos"]), lambda: self.armarMenu("objetos"),
                             ["Objetos", "Las pociones que comparte todo el equipo.",
                              "Se le pueden dar a cualquier aliado que la necesite." if hayPociones
                              else "Ya no queda ninguna."]))

        elif nivel == "magia":
            for k, conj in enumerate(yo["conjuros"]):
                lineas = descripcionDeConjuro(i, k, est)
                if k not in grupos["magia"]:
                    entradas.append((conj["nombre"], False, None, lineas + ["No le alcanza el mana."]))
                elif conj["tipo"] == "cura" and not conj["enGrupo"]:
                    entradas.append((conj["nombre"], True, lambda k=k: self.armarMenu("objetivo", k), lineas))
                else:
                    entradas.append((conj["nombre"], True, lambda k=k: self.responder(grupos["magia"][k][0]), lineas))

        elif nivel == "objetos":
            for clave in m.pocionesIniciales:
                lineas = descripcionDePocion(i, clave, est)
                if clave in grupos["objetos"]:
                    entradas.append(("%s (%d)" % (m.nombrePocion[clave].capitalize(), pocionesLibres(est, clave)),
                                     True, lambda clave=clave: self.armarMenu("destino", clave), lineas))
                else:
                    motivo = "Ya no queda." if pocionesLibres(est, clave) <= 0 else "Ahora no le serviría a nadie."
                    entradas.append(("%s (%d)" % (m.nombrePocion[clave].capitalize(), max(0, pocionesLibres(est, clave))),
                                     False, None, lineas + [motivo]))

        elif nivel == "destino":
            for accion in grupos["objetos"][conjuro]:
                j = accion[2]
                entradas.append((est["equipo"][j]["nombre"], True, lambda accion=accion: self.responder(accion),
                                 descripcionDeDestino(conjuro, j, est)))

        else:
            conj = yo["conjuros"][conjuro]
            for accion in grupos["magia"][conjuro]:
                j = accion[2]
                aliado = est["equipo"][j]
                entradas.append((aliado["nombre"], True, lambda accion=accion: self.responder(accion),
                                 [conj["nombre"] + " a " + aliado["nombre"],
                                  "Tiene %d de %d de vida." % (est["hp"][j], aliado["hp"]),
                                  "Le devuelve %d." % int(yo["atkMag"] * conj["poder"])]))

        if nivel != "raiz":
            anterior = {"objetivo": "magia", "destino": "objetos"}.get(nivel, "raiz")
            entradas.append(("Atras", True, lambda anterior=anterior: self.armarMenu(anterior),
                             ["Atras", "Regresa al menú anterior."]))

        dondeEstaba = (self.nivelMenu, self.focoMenu)
        self.nivelMenu = nivel
        self.botonesMenu, self.descripciones = [], []
        for k, (texto, activo, alElegir, lineas) in enumerate(entradas):
            if nivel == "raiz":
                rect = (44 + (k % 2) * 180, 548 + (k // 2) * 64, 170, 52)
            else:
                rect = (44, 544 + k * 31, 350, 29)
            self.botonesMenu.append(Boton(rect, "%d  %s" % (k + 1, texto), alElegir, activo,
                                          tamano=30 if nivel == "raiz" else 23, estilo="lista"))
            self.descripciones.append(lineas)
        # La mano empieza en la primera opcion que se puede elegir; al volver a
        # la raiz regresa a donde estaba.
        self.focoMenu = None
        inicial = next((k for k, b in enumerate(self.botonesMenu) if b.activo), 0)
        if nivel == "raiz" and dondeEstaba[0] not in (None, "raiz") and dondeEstaba[1] is not None:
            inicial = 1 if len(self.botonesMenu) > 1 else 0
        self.focoMenu = inicial
        for j, boton in enumerate(self.botonesMenu):
            boton.foco = j == inicial
        self.descripcion = self.descripciones[inicial]

    def responder(self, accion):
        peticion = self.peticionVista
        if peticion is not None and accion is not None:
            self.planesElegidos[peticion["heroe"]] = textoDePlan(accion, peticion["est"], peticion["heroe"])
        self.botonesMenu, self.descripciones = [], []
        self.nivelMenu = None
        self.partida.responder(accion)

    def mostrarFinal(self):
        res = self.partida.resultado
        if res["tope"]:
            # Aguantar todas las rondas cuenta como victoria, pero el jefe sigue en pie.
            self.dialogo = [[("¡Victoria!", colores["cura"])],
                            [("Resistieron las %d rondas y el jefe se retira." % res["rondas"], None)]]
        elif res["gana_equipo"]:
            self.dialogo = [[("¡Victoria!", colores["cura"])],
                            [("El jefe cayó en la ronda %d. Al equipo le queda %.0f%% de su vida."
                              % (res["rondas"], 100 * res["hp_final_pct"]), None)]]
        else:
            self.dialogo = [[("Derrota", colores["dano"])],
                            [("Todo el equipo cayó en la ronda %d." % res["rondas"], None)]]

        if res["gana_equipo"]:
            self.fiesta = 0.0
            reproducirMusica("victoria", bucle=True, fundido=200)
        else:
            reproducirMusica("derrota", fundido=1200)
            reproducirSonido("jefe_risa", 0.9)
        # Ya no hay golpes que esperar: los escudos se quitan para celebrar o caer.
        self.protecciones = [[] for _ in range(4)]
        self.botonesFinal = [Boton((ancho - 300, 640, 270, 50), "Ver resultados", self.verResultados, tamano=28)]
        self.botonesFinal[0].foco = True
        self.esperaResultados = 4.5

    def verResultados(self):
        from grafico.pantallas import EscenaResultados
        self.juego.cambiarEscena(EscenaResultados(self.juego, self))

    def dibujarPersonaje(self, lienzo, nombre, imagen, imagenPose, lugar, tamano, direccion, saltar=0.0, imagenImpulso=None):
        # direccion es 1 para los héroes, que atacan hacia la derecha, y -1 para
        # el jefe. tamano es el lugar que ocupa en pantalla; la imagen se apoya
        # en el centro de su borde de abajo, sin importar su propio tamaño.
        base = pygame.Rect(lugar, tamano)
        avance = avanceHeroe if direccion == 1 else avanceJefe
        forma = {"dx": 0, "dy": -saltar, "sx": 1.0, "sy": 1.0, "ancla": "centro", "pose": False}

        anim = self.animacion
        tiempos = tiemposCortos
        if anim is not None and anim["actor"] == nombre:
            tiempos = anim.get("tiempos", tiemposCortos)
            if anim["ataca"] and "carrera" in anim:
                forma = transformacionDeAtaque(anim["tiempo"], anim["carrera"][0], tiempos, anim["carrera"][1])
            elif anim["ataca"] and "sosten" in anim:
                # Conjura sin moverse de su lugar: alza los brazos y, al
                # soltar la magia, se inclina un poco hacia el frente.
                lanzo = anim["tiempo"] >= anim["sosten"][0]
                forma = dict(forma, dx=6 * suave((anim["tiempo"] - anim["sosten"][0]) / 0.12) if lanzo else 0,
                             dy=forma["dy"] - 3 * abs(math.sin(anim["tiempo"] * 9)), pose=lanzo)
                if not lanzo and imagenImpulso is None:
                    forma["pose"] = True
            elif anim["ataca"]:
                forma = transformacionDeAtaque(anim["tiempo"], avance)
            else:
                u = anim["tiempo"] / anim["duracion"]
                forma = dict(forma, dy=-10 * math.sin(math.pi * u), pose=True)
        if self.esquivas.get(nombre, 0) > 0:
            # Se hace a un lado de un brinco y vuelve.
            u = 1 - self.esquivas[nombre] / duracionEsquiva
            forma = dict(forma, dx=forma["dx"] - 24 * math.sin(math.pi * u), dy=forma["dy"] - 6 * math.sin(math.pi * u))

        if forma["pose"]:
            imagen = imagenPose
        elif imagenImpulso is not None and anim is not None and anim["actor"] == nombre and anim["ataca"] \
                and ("sosten" in anim or tiempos[0] <= anim["tiempo"] < tiempos[1]):
            # El jefe toma impulso con su propio cuadro antes de soltar el ataque.
            imagen = imagenImpulso
        anchoOriginal = imagen.get_width()
        if (forma["sx"], forma["sy"]) != (1.0, 1.0):
            # Sin suavizar, para que el pixel art no se emborrone al estirarse.
            imagen = pygame.transform.scale(imagen, (int(imagen.get_width() * forma["sx"]), int(imagen.get_height() * forma["sy"])))

        # Al estirarse se queda fijo un borde: el de atrás cuando se lanza al
        # frente y el del frente cuando se echa para atrás. Los pies no se mueven.
        rect = imagen.get_rect()
        rect.bottom = base.bottom + int(forma["dy"])
        centro = base.centerx + direccion * forma["dx"]
        if forma["ancla"] == "centro":
            rect.centerx = int(centro)
        elif (forma["ancla"] == "atras") == (direccion == 1):
            rect.left = int(centro - anchoOriginal / 2)
        else:
            rect.right = int(centro + anchoOriginal / 2)

        # La sombra queda en el piso aunque el personaje brinque o flote.
        enElAire = saltar if forma["dy"] == -saltar else 0
        self.dibujarSombra(lienzo, rect.centerx, base.bottom + int(forma["dy"] + enElAire) - (14 if direccion == -1 else 3),
                           anchoSombra["jefe" if direccion == -1 else "heroe"])
        lienzo.blit(imagen, rect)
        if self.destelloGolpe.get(nombre, 0) > 0:
            # Un parpadeo en blanco en el instante en que recibe el golpe.
            silueta = pygame.mask.from_surface(imagen).to_surface(setcolor=(255, 255, 255, 215), unsetcolor=(0, 0, 0, 0))
            lienzo.blit(silueta, rect)
        return base

    def fantasma(self, clave, fraccion, dt):
        # La barra fantasma espera un instante y luego baja hasta alcanzar a la real.
        valor, espera = self.fantasmas.get(clave, (fraccion, 0.0))
        if fraccion >= valor:
            valor, espera = fraccion, 0.45
        elif espera > 0:
            espera -= dt
        else:
            valor = max(fraccion, valor - 0.6 * dt)
        self.fantasmas[clave] = (valor, espera)
        return valor

    def poseEnReposo(self, j):
        # La pose de un heroe cuando no es su turno, de la mas a la menos urgente.
        if self.vida[j] <= 0 and self.mostrados > 0:
            return "caido"
        if self.fiesta is not None:
            return "celebra"
        if self.tiempoDano[j] > 0:
            return "dano"
        if "bloqueo" in self.protecciones[j]:
            return "bloqueo"
        if self.vida[j] <= fraccionHerido * self.vidaMax[j]:
            return "herido"
        return ""

    def alturaDeSalto(self, j):
        if self.fiesta is None or self.vida[j] <= 0:
            return 0.0
        # Cada heroe salta un poco desfasado del anterior, como en una ola.
        fase = (self.fiesta / periodoSalto + j * 0.25) % 1.0
        return alturaSalto * math.sin(math.pi * fase)

    def dibujarSombra(self, lienzo, x, y, anchoDeSombra):
        if anchoDeSombra not in self.sombras:
            sombra = pygame.Surface((anchoDeSombra, anchoDeSombra // 4), pygame.SRCALPHA)
            pygame.draw.ellipse(sombra, (8, 4, 20, 95), sombra.get_rect())
            self.sombras[anchoDeSombra] = sombra
        sombra = self.sombras[anchoDeSombra]
        lienzo.blit(sombra, sombra.get_rect(center=(x, y)))

    def respiro(self, desfase):
        # Dos pixeles arriba o abajo, a brincos, como los sprites de 16 bits.
        return 2 if math.sin(self.reloj * ritmoRespiro + desfase) > 0.2 else 0

    def dibujarJefe(self, lienzo):
        prefijo = "jefe_fase2" if self.fase2 else "jefe"

        pulso = 1.0

        def imagen(sufijo):
            return obtenerSpriteJefe(prefijo + ("_" + sufijo if sufijo else ""), self.fase2, pulso)

        # Su pose fuera de su turno: vencido, adolorido, cargando un ataque o normal.
        if self.vidaJefe <= 0 and self.mostrados > 0:
            reposo = imagen("derrota")
        elif self.tiempoDanoJefe > 0:
            reposo = imagen("dano")
        elif self.poseFijaJefe is not None:
            reposo = imagen("pose_%d" % self.poseFijaJefe)
        else:
            reposo = imagen("")
        # Al atacar toma impulso y se lanza al frente, o junta la magia con el
        # aura encendida y la suelta.
        magico = self.animacion is not None and self.animacion.get("magico", False)
        impulso, suelta = ("conjuro", "lanzar") if magico else ("alzar", "golpe")
        flota = 0.0
        if self.vidaJefe > 0 or self.mostrados == 0:
            flota = flotacionJefe * (1 + math.sin(self.reloj * 2.2)) if self.fase2 else self.respiro(1.0)
        lugar = lugaresJefe[self.fase2]
        if self.cinematica is not None:
            # Antes del corte a la cinematica el jefe se sacude.
            ax, ay = self.cinematica.agitacionJefe()
            lugar = (lugar[0] + ax, lugar[1] + ay)
        if self.muerteJefe is not None:
            # Vencido: tiembla mientras estalla, se pone blanco y se deshace.
            self.muerteJefe += self.ultimoDt
            t = self.muerteJefe
            if t > 2.6:
                return self.dibujarDatosJefe(lienzo, reposo)
            if t < 1.45:
                lugar = (lugar[0] + int(4 * math.sin(t * 70)), lugar[1])
            else:
                u = (t - 1.45) / 1.15
                reposo = reposo.copy()
                reposo.fill((int(255 * min(1, u * 2)),) * 3, special_flags=pygame.BLEND_RGB_ADD)
                reposo.set_alpha(int(255 * (1 - u)))
                alto = reposo.get_height()
                reposo = pygame.transform.scale(reposo, (int(reposo.get_width() * (1 + 0.2 * u)), max(1, int(alto * (1 - 0.35 * u)))))
        self.dibujarPersonaje(lienzo, "Jefe", reposo, imagen(suelta), lugar, tamanoJefe, -1,
                              saltar=flota, imagenImpulso=imagen(impulso))
        self.dibujarDatosJefe(lienzo, reposo)

    def dibujarDatosJefe(self, lienzo, reposo):

        base = pygame.Rect(lugaresJefe[self.fase2], tamanoJefe)
        # El nombre va justo arriba de su imagen, que en la segunda fase es mas
        # alta, sin salirse de la pantalla.
        arriba = max(16, base.bottom - reposo.get_height() - 16)
        dibujarTexto(lienzo, "Jefe", (base.centerx, arriba), 28, colores["jefe"], centrado=True, contorno=True)
        fraccion = max(0.0, self.vidaJefe / self.vidaJefeMax)
        dibujarBarra(lienzo, (base.x, base.bottom + 8, base.width, 10), fraccion, colores["vidaJefe"],
                     self.fantasma("Jefe", fraccion, self.ultimoDt))
        dibujarTexto(lienzo, "VIDA %d/%d" % (max(0, self.vidaJefe), self.vidaJefeMax), (base.x, base.bottom + 24), 24, contorno=True)
        dibujarTexto(lienzo, self.objetoJefe, (base.x + 170, base.bottom + 26), 21, contorno=True)
        if self.estadoJefe:
            dibujarTexto(lienzo, self.estadoJefe, (base.x, base.bottom + 50), 22, colores["aviso"], contorno=True)

    def dibujarLetreroFinal(self, lienzo):
        # El letrero grande sobre la arena al terminar: dorado y brincando si
        # ganaron, rojo y con la arena apagada si no.
        gano = self.partida.resultado["gana_equipo"]
        t = 4.5 - self.esperaResultados
        if not gano:
            gris = pygame.Surface((ancho, altoEscenario))
            gris.fill((20, 0, 10))
            gris.set_alpha(int(min(150, 150 * t / 1.2)))
            lienzo.blit(gris, (0, 0))
        entra = min(1.0, t / 0.4)
        escala = 0.4 + 0.6 * (1 - (1 - entra) ** 3) + (0.06 * math.sin(t * 5) if gano else 0)
        texto = "¡Victoria!" if gano else "Derrota"
        color = colores["jefe"] if gano else (240, 90, 90)
        imagen = pygame.font.Font(None, 120).render(texto, True, color)
        sombra = pygame.font.Font(None, 120).render(texto, True, (20, 10, 30))
        w, h = int(imagen.get_width() * escala), int(imagen.get_height() * escala)
        if w < 4:
            return
        for dx, dy in ((-4, 0), (4, 0), (0, -4), (0, 4), (5, 5)):
            s = pygame.transform.smoothscale(sombra, (w, h))
            lienzo.blit(s, s.get_rect(center=(640 + dx, 210 + dy)))
        lienzo.blit(pygame.transform.smoothscale(imagen, (w, h)), pygame.Rect(0, 0, w, h).move(640 - w // 2, 210 - h // 2))

    def dibujarEntrada(self, lienzo):
        u = self.entrada
        if u < 0.12:
            lienzo.fill((255, 255, 255))
            return
        franjas = 12
        alto_ = alto / franjas
        abierto = suave((u - 0.12) / 0.8)
        for k in range(franjas):
            ancho_ = int(ancho * (1 - abierto))
            x = 0 if k % 2 == 0 else ancho - ancho_
            pygame.draw.rect(lienzo, (0, 0, 0), (x, int(k * alto_), ancho_, int(alto_) + 1))

    def dibujarLetreroRonda(self, lienzo):
        t = 1.1 - self.letreroRonda
        entra = min(1.0, t / 0.2, self.letreroRonda / 0.25)
        y = int(-50 + 70 * suave(entra))
        dibujarPanel(lienzo, (545, y, 190, 46))
        dibujarTexto(lienzo, "Ronda %d" % self.ronda, (640, y + 23), 32, colores["resaltado"], centrado=True)

    def dibujarLetreroFase(self, lienzo):
        # El letrero de la segunda fase entra, se queda y se va.
        t = 3.0 - self.letreroFase
        entra = min(1.0, t / 0.3, self.letreroFase / 0.4)
        rect = pygame.Rect(0, 0, 420, 60)
        rect.center = (640, int(-40 + 100 * suave(entra)))
        dibujarPanel(lienzo, rect, (120, 60, 20))
        dibujarTexto(lienzo, "Segunda fase", rect.center, 44, colores["jefe"], centrado=True)

    def dibujar(self, lienzo):
        capa = self.capa
        if self.cinematica is not None and not self.cinematica.enLaArena():
            # A mitad de la cinematica la pantalla entera es el retrato del jefe.
            self.cinematica.dibujarRetrato(capa)
            self.cinematica.dibujarEncima(capa)
            dx, dy = self.cinematica.desplazamiento()
            lienzo.fill((0, 0, 0))
            lienzo.blit(capa, (dx, dy))
            dibujarTexto(lienzo, "Cualquier tecla para saltar", (ancho - 20 - 230, alto - 34), 20, (150, 150, 170))
            return
        # El escenario ocupa la zona de la pelea; abajo quedan los paneles. En
        # la segunda fase cambia junto con el jefe, en el destello.
        capa.fill(colores["fondo"])
        capa.blit(obtenerEscenario("arena_fase2" if self.fase2 else "arena", (ancho, altoEscenario)), (0, 0))

        # Las animaciones de ataque van en tres capas: una atras de los
        # personajes, y al frente una normal y otra de luz. Si alguna pide
        # oscurecer el fondo, se oscurece antes de dibujar a los personajes.
        if self.capasEfecto is None:
            self.capasEfecto = Capas(ancho, altoEscenario)
            self.velo = pygame.Surface((ancho, altoEscenario))
        capas = self.capasEfecto
        capas.limpiar()
        self.ambiente.dibujar(capas)
        penumbra = 0
        for animacion in self.animaciones:
            animacion.dibujar(capas)
            penumbra = max(penumbra, animacion.penumbra())
        if penumbra > 0:
            self.cubrir(capa, (0, 0, 12), penumbra)
        capas.volcar(capa, "atras")
        dibujarTexto(capa, "Ronda %d" % self.ronda, (20, 16), 30, contorno=True)

        # El heroe que corre hasta el jefe se dibuja despues de el, para quedar enfrente.
        alFrente = []
        for j, nombre in enumerate(self.nombres):
            anim = self.animacion
            poseTurno = anim.get("poseHeroe", "ataque") if anim is not None and anim["actor"] == nombre else "ataque"
            reposo = self.poseEnReposo(j)
            salto = self.alturaDeSalto(j) + (self.respiro(j * 1.3) if reposo in ("", "bloqueo") else 0)
            argumentos = (capa, nombre, obtenerSprite(nombre, reposo, alturaHeroe),
                          obtenerSprite(nombre, poseTurno, alturaHeroe), lugaresHeroes[j], tamanoHeroe, 1, salto)
            if anim is not None and anim["actor"] == nombre and "carrera" in anim:
                alFrente.append(argumentos)
                base = pygame.Rect(lugaresHeroes[j], tamanoHeroe)
            else:
                base = self.dibujarPersonaje(*argumentos)
                self.dibujarEscudo(capa, j, base)
            rectNombre = dibujarTexto(capa, nombre, (base.centerx, base.y - 12), 22, colores["heroe"], centrado=True,
                                      contorno=True)
            fraccion = self.vida[j] / self.vidaMax[j]
            colorVida = colores["vida"] if fraccion > 0.5 else ((230, 200, 70) if fraccion > fraccionHerido else (230, 80, 70))
            dibujarBarra(capa, (base.x, base.bottom + 4, base.width, 5), fraccion, colorVida,
                         self.fantasma(nombre, fraccion, self.ultimoDt))
            colorTexto = None if fraccion > fraccionHerido else ((255, 120, 110) if self.vida[j] > 0 else (150, 150, 160))
            dibujarTexto(capa, "VIDA %d/%d" % (self.vida[j], self.vidaMax[j]), (base.x, base.bottom + 12), 19, colorTexto, contorno=True)
            if self.botonesMenu and self.peticionVista["heroe"] == j:
                # Una flecha a su lado que lo señala mientras elige.
                x = base.x - 2 + 4 * abs(math.sin(self.reloj * 6))
                y = base.centery + 6
                pygame.draw.polygon(capa, colores["marcoOscuro"], [(x - 1, y - 10), (x + 13, y), (x - 1, y + 10)])
                pygame.draw.polygon(capa, colores["resaltado"], [(x, y - 8), (x + 11, y), (x, y + 8)])
            if j in self.planesElegidos:
                # Junto al nombre, en la misma linea, para no tapar al de arriba.
                dibujarTexto(capa, self.planesElegidos[j], (rectNombre.right + 10, rectNombre.y + 2), 18,
                             colores["resaltado"], contorno=True)
            if self.nivelMenu in ("objetivo", "destino") and self.focoMenu is not None:
                elegido = self.botonesMenu[self.focoMenu].texto.split("  ", 1)[-1]
                if elegido == nombre:
                    dibujarCursor(capa, base.x + 4, base.centery)
            dibujarTexto(capa, "MANA %d/%d" % (self.mana[j], self.manaMax[j]), (base.x, base.bottom + 28), 19,
                         colores["mana"], contorno=True)

        self.dibujarJefe(capa)
        for argumentos in alFrente:
            self.dibujarPersonaje(*argumentos)
        # Los destellos tapan el fondo y a los personajes, pero no a la magia.
        for animacion in self.animaciones:
            for color, fuerza in animacion.velosActivos():
                self.cubrir(capa, color, fuerza)
        capas.volcar(capa, "frente")
        capas.volcar(capa, "luz")
        for efecto in self.efectos:
            efecto.dibujar(capa)
        if self.letreroFase > 0:
            self.dibujarLetreroFase(capa)
        elif self.letreroRonda > 0 and self.cinematica is None:
            self.dibujarLetreroRonda(capa)
        if self.botonesFinal:
            self.dibujarLetreroFinal(capa)

        if self.botonesMenu:
            self.dibujarMenu(capa)
        else:
            self.dibujarDialogo(capa)
        self.dibujarBotones(capa)
        for boton in self.botonesFinal:
            boton.dibujar(capa, pygame.mouse.get_pos())
        if self.cinematica is not None:
            self.cinematica.dibujarEncima(capa)
        if self.entrada is not None:
            self.dibujarEntrada(capa)

        # Todo se dibuja primero en una capa para poder sacudir la pantalla
        # entera en los golpes fuertes y en la cinematica.
        dx = dy = 0
        if self.cinematica is not None:
            dx, dy = self.cinematica.desplazamiento()
        for animacion in self.animaciones:
            sx, sy = animacion.desplazamiento()
            dx, dy = dx + sx, dy + sy
        if (dx, dy) != (0, 0):
            lienzo.fill(colores["fondo"])
        lienzo.blit(capa, (dx, dy))
        if self.pausa is not None:
            self.pausa.dibujar(lienzo)

    def cubrir(self, lienzo, color, fuerza):
        # Un color sobre toda la zona de la pelea, para destellos y penumbras.
        self.velo.fill(color)
        self.velo.set_alpha(max(0, min(255, fuerza)))
        lienzo.blit(self.velo, (0, 0))

    def dibujarMenu(self, lienzo):
        peticion = self.peticionVista
        nombre = peticion["est"]["equipo"][peticion["heroe"]]["nombre"]

        dibujarPanel(lienzo, (12, 514, 402, 196))
        dibujarTitulo(lienzo, "¿Qué hará %s?" % nombre, (12, 514, 402, 196))
        for boton in self.botonesMenu:
            boton.dibujar(lienzo, None)

        dibujarPanel(lienzo, (424, 514, 844, 196))
        for k, linea in enumerate(self.descripcion):
            if k == 0:
                dibujarTexto(lienzo, linea, (450, 532), 32, colores["resaltado"])
            else:
                dibujarTexto(lienzo, linea, (450, 548 + k * 30), 24, anchoMax=790)

    def dibujarDialogo(self, lienzo):
        dibujarPanel(lienzo, (12, 514, 1256, 196))
        for k, linea in enumerate(self.dialogo[:6]):
            dibujarTextoRico(lienzo, linea, (40, 528 + k * 29), 27)
