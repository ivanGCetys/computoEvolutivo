# Las pantallas fuera del combate: titulo, opciones, entrenamiento del jefe y
# resultados, y el menu de pausa que se abre encima del combate.
import math
import multiprocessing
import os
import queue
import random
import sys

import pygame

import motor as m
from grafico.interfaz import (ancho, alto, colores, dibujarTexto, dibujarTextoRico, dibujarPanel, dibujarTitulo,
                              dibujarBarra, dibujarCursor, Boton)
from grafico.recursos import (obtenerEscenario, obtenerSprite, obtenerSpriteJefe, reproducirSonido, reproducirMusica,
                              rutaDe, volumenes, cambiarVolumen)
from grafico.escenas import Escena, EscenaEquipo, EscenaCombate, alturaHeroe
from grafico.cinematica import pasosDeRueda, centroRueda
import entrenamiento


class Brasas:
    # Unas chispas que suben despacio por la pantalla, para los menus.
    def __init__(self, cuantas, color, zona=(0, 0, ancho, alto)):
        self.azar = random.Random(3)
        self.zona = zona
        self.color = color
        self.lista = [self.nueva(True) for _ in range(cuantas)]

    def nueva(self, enCualquierAltura=False):
        x0, y0, w, h = self.zona
        y = y0 + self.azar.uniform(0, h) if enCualquierAltura else y0 + h + 5
        return [x0 + self.azar.uniform(0, w), y, self.azar.uniform(-8, 8), -self.azar.uniform(12, 40),
                self.azar.uniform(0, math.tau), self.azar.choice((2, 2, 3, 4))]

    def actualizar(self, dt):
        for k, b in enumerate(self.lista):
            b[0] += (b[2] + 10 * math.sin(b[4])) * dt
            b[1] += b[3] * dt
            b[4] += dt * 1.5
            if b[1] < self.zona[1] - 5:
                self.lista[k] = self.nueva()

    def dibujar(self, lienzo):
        for x, y, _, _, fase, tam in self.lista:
            brillo = 0.5 + 0.5 * math.sin(fase * 2)
            color = tuple(int(c * (0.4 + 0.6 * brillo)) for c in self.color)
            lienzo.fill(color, (int(x), int(y), tam, tam), special_flags=pygame.BLEND_RGB_ADD)


class RuedaDelTitulo:
    # La rueda del titulo: gira de punta en punta, se frena en seco y descansa,
    # siempre al mismo ritmo tranquilo.
    def __init__(self):
        self.fondo = self.rueda = None
        rutaFondo, rutaRueda = rutaDe("escenarios", "titulo_fondo"), rutaDe("escenarios", "titulo_rueda")
        if os.path.exists(rutaFondo) and os.path.exists(rutaRueda):
            self.fondo = pygame.image.load(rutaFondo).convert()
            self.rueda = pygame.image.load(rutaRueda).convert_alpha()
        self.tiempo = 0.0
        self.pausa, self.giro = 2.2, 0.55
        self.anguloBase = 0.0

    def actualizar(self, dt):
        antes = self.tiempo % (self.pausa + self.giro)
        self.tiempo += dt
        ahora = self.tiempo % (self.pausa + self.giro)
        if ahora < antes:
            self.anguloBase += 45
            reproducirSonido("rueda", 0.25)

    def angulo(self):
        t = self.tiempo % (self.pausa + self.giro)
        if t < self.pausa:
            d = t
            rebote = 2.0 * math.exp(-d / 0.045) * math.sin(d / 0.022) if self.tiempo > self.pausa else 0
            return self.anguloBase + rebote
        u = (t - self.pausa) / self.giro
        return self.anguloBase + 45 * u * u

    def dibujar(self, lienzo):
        if self.fondo is None:
            lienzo.fill((0, 0, 0))
            return
        lienzo.blit(self.fondo, (0, 0))
        girada = pygame.transform.rotozoom(self.rueda, -self.angulo(), 1.0)
        lienzo.blit(girada, girada.get_rect(center=centroRueda))


class EscenaTitulo(Escena):

    def __init__(self, juego):
        super().__init__(juego)
        self.rueda = RuedaDelTitulo()
        self.brasas = Brasas(70, (170, 110, 255))
        self.reloj = 0.0
        x = 80
        self.botones = [Boton((x, 392, 300, 54), "Jugar", self.jugar, tamano=32),
                        Boton((x, 454, 300, 54), "Entrenar jefe", self.entrenar, tamano=32),
                        Boton((x, 516, 300, 54), "Opciones", self.opciones, tamano=32),
                        Boton((x, 578, 300, 54), "Salir", juego.salir, tamano=32)]
        self.ponerFoco(self.botones[0], False)
        self.jefe, self.entrenado = entrenamiento.jefeOptimo()
        reproducirMusica("titulo")

    def jugar(self):
        self.juego.cambiarEscena(EscenaEquipo(self.juego))

    def entrenar(self):
        self.juego.cambiarEscena(EscenaEntrenamiento(self.juego))

    def opciones(self):
        self.juego.cambiarEscena(EscenaOpciones(self.juego, lambda: EscenaTitulo(self.juego)))

    def actualizar(self, dt):
        self.reloj += dt
        self.rueda.actualizar(dt)
        self.brasas.actualizar(dt)

    def dibujar(self, lienzo):
        self.rueda.dibujar(lienzo)
        self.brasas.dibujar(lienzo)

        # El nombre del juego, con un brillo que lo recorre.
        brillo = 0.75 + 0.25 * math.sin(self.reloj * 1.7)
        dorado = (int(255 * brillo), int(214 * brillo), int(110 * brillo))
        for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (3, 3)):
            dibujarTexto(lienzo, "JEFE RPG", (230 + dx, 150 + dy), 104, (30, 10, 50), centrado=True, sombra=False)
        dibujarTexto(lienzo, "JEFE RPG", (230, 150), 104, dorado, centrado=True, sombra=False)
        dibujarTexto(lienzo, "evolutivo", (230, 222), 52, (210, 190, 255), centrado=True)
        pygame.draw.line(lienzo, (150, 120, 60), (90, 256), (370, 256), 2)
        dibujarTexto(lienzo, "Un jefe diseñado por NSGA-II", (230, 282), 24, colores["textoSuave"], centrado=True)
        dibujarTexto(lienzo, "contra cuatro héroes", (230, 308), 24, colores["textoSuave"], centrado=True)

        self.dibujarBotones(lienzo)

        if self.entrenado:
            v = self.jefe["validacion"]
            texto = "Jefe entrenado el %s   F = %.3f" % (self.jefe["fecha"], v["fitness"])
        else:
            texto = "Todavía no entrenas un jefe; se usará el del experimento"
        imagen = pygame.font.Font(None, 20).size(texto)[0]
        dibujarTexto(lienzo, texto, (ancho - 20 - imagen, alto - 30), 20, colores["textoSuave"])
        dibujarTexto(lienzo, "Flechas y Enter, o el ratón", (20, alto - 30), 18, (120, 120, 150))


class EscenaOpciones(Escena):
    # Volumen de la musica y de los efectos, y pantalla completa.

    def __init__(self, juego, regresar):
        super().__init__(juego)
        self.regresar = regresar
        self.rueda = RuedaDelTitulo()
        y = 250
        self.botones = [Boton((440, y, 400, 54), "", lambda: self.mover("musica", 0.1), estilo="lista"),
                        Boton((440, y + 70, 400, 54), "", lambda: self.mover("efectos", 0.1), estilo="lista"),
                        Boton((440, y + 140, 400, 54), "Pantalla completa", self.pantallaCompleta, estilo="lista", tamano=30),
                        Boton((540, y + 230, 200, 54), "Volver", self.alCancelar, tamano=30)]
        self.ponerFoco(self.botones[0], False)

    def mover(self, tipo, paso):
        valor = volumenes[tipo] + paso
        if valor > 1.001:
            valor = 0.0
        cambiarVolumen(tipo, valor)
        reproducirSonido("cursor")

    def pantallaCompleta(self):
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            reproducirSonido("error")

    def alCancelar(self):
        self.juego.cambiarEscena(self.regresar())

    def manejarEvento(self, evento):
        # Con izquierda y derecha se mueve el volumen que tiene el foco.
        if evento.type == pygame.KEYDOWN and evento.key in (pygame.K_LEFT, pygame.K_RIGHT):
            for k, tipo in enumerate(("musica", "efectos")):
                if self.foco is self.botones[k]:
                    self.mover(tipo, 0.1 if evento.key == pygame.K_RIGHT else -0.1)
                    return True
        return super().manejarEvento(evento)

    def actualizar(self, dt):
        self.rueda.actualizar(dt)

    def dibujar(self, lienzo):
        self.rueda.dibujar(lienzo)
        velo = pygame.Surface((ancho, alto))
        velo.fill((0, 0, 10))
        velo.set_alpha(140)
        lienzo.blit(velo, (0, 0))
        dibujarPanel(lienzo, (400, 190, 480, 380))
        dibujarTitulo(lienzo, "Opciones", (400, 190, 480, 380))
        for k, (tipo, nombre) in enumerate((("musica", "Música"), ("efectos", "Efectos"))):
            boton = self.botones[k]
            dibujarTexto(lienzo, nombre, (boton.rect.x + 40, boton.rect.y + 14), 30)
            dibujarBarra(lienzo, (boton.rect.x + 190, boton.rect.y + 20, 170, 14), volumenes[tipo], (110, 170, 255))
            dibujarTexto(lienzo, "%d" % round(volumenes[tipo] * 10), (boton.rect.x + 372, boton.rect.y + 14), 26)
            if boton.foco:
                dibujarCursor(lienzo, boton.rect.x + 30, boton.rect.centery)
        dibujarTexto(lienzo, "Izquierda y derecha cambian el volumen", (640, 450), 20, colores["textoSuave"], centrado=True)
        for boton in self.botones[2:]:
            boton.dibujar(lienzo)


class MenuPausa:
    # El menu que se abre sobre el combate con Escape.

    def __init__(self, escena, salir):
        self.escena = escena
        self.botones = [Boton((520, 270, 240, 50), "Continuar", self.cerrar, tamano=28),
                        Boton((520, 330, 240, 50), "", lambda: self.mover("musica", 0.1), estilo="lista"),
                        Boton((520, 390, 240, 50), "", lambda: self.mover("efectos", 0.1), estilo="lista"),
                        Boton((520, 460, 240, 50), "Salir al título", salir, tamano=28)]
        self.foco = 0
        self.botones[0].foco = True

    def cerrar(self):
        reproducirSonido("cancelar")
        self.escena.pausa = None

    def mover(self, tipo, paso):
        valor = volumenes[tipo] + paso
        if valor > 1.001:
            valor = 0.0
        cambiarVolumen(tipo, max(0.0, valor))
        reproducirSonido("cursor")

    def enfocar(self, k):
        self.foco = k % len(self.botones)
        for j, b in enumerate(self.botones):
            b.foco = j == self.foco
        reproducirSonido("cursor", 0.7)

    def manejarEvento(self, evento):
        if evento.type == pygame.KEYDOWN:
            if evento.key == pygame.K_ESCAPE:
                self.cerrar()
            elif evento.key in (pygame.K_UP, pygame.K_DOWN):
                self.enfocar(self.foco + (1 if evento.key == pygame.K_DOWN else -1))
            elif evento.key in (pygame.K_LEFT, pygame.K_RIGHT) and self.foco in (1, 2):
                self.mover(("musica", "efectos")[self.foco - 1], 0.1 if evento.key == pygame.K_RIGHT else -0.1)
            elif evento.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_z):
                reproducirSonido("aceptar")
                self.botones[self.foco].alHacerClic()
        elif evento.type == pygame.MOUSEMOTION:
            for k, b in enumerate(self.botones):
                if b.rect.collidepoint(evento.pos) and k != self.foco:
                    self.enfocar(k)
        elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            for b in self.botones:
                if b.manejarEvento(evento):
                    return

    def actualizar(self, dt):
        pass

    def dibujar(self, lienzo):
        velo = pygame.Surface((ancho, alto))
        velo.fill((0, 0, 10))
        velo.set_alpha(150)
        lienzo.blit(velo, (0, 0))
        dibujarPanel(lienzo, (480, 220, 320, 320))
        dibujarTitulo(lienzo, "Pausa", (480, 220, 320, 320))
        for k, (tipo, nombre) in enumerate((("musica", "Música"), ("efectos", "Efectos"))):
            b = self.botones[k + 1]
            dibujarTexto(lienzo, nombre, (b.rect.x + 30, b.rect.y + 13), 26)
            dibujarBarra(lienzo, (b.rect.x + 140, b.rect.y + 19, 90, 12), volumenes[tipo], (110, 170, 255))
            if b.foco:
                dibujarCursor(lienzo, b.rect.x + 22, b.rect.centery)
        self.botones[0].dibujar(lienzo)
        self.botones[3].dibujar(lienzo)


class EscenaEntrenamiento(Escena):
    # Corre el entrenamiento en otro proceso y va mostrando como mejora: el
    # avance, el hipervolumen de cada generacion y la poblacion sobre dos de
    # sus objetivos.

    def __init__(self, juego):
        super().__init__(juego)
        self.estado = "inicio"
        self.reloj = 0.0
        self.generaciones = []
        self.poblacion = None
        self.resultado = None
        self.proceso = None
        self.cola = None
        self.bitacora = []
        self.brasas = Brasas(50, (120, 170, 255), (640, 90, 600, 400))
        self.anterior, _ = entrenamiento.jefeOptimo()
        self.botonComenzar = Boton((380, 600, 240, 56), "Comenzar", self.comenzar, tamano=32)
        self.botonVolver = Boton((660, 600, 240, 56), "Volver", self.alCancelar, tamano=32)
        self.botones = [self.botonComenzar, self.botonVolver]
        self.ponerFoco(self.botonComenzar, False)
        reproducirMusica("entrenamiento")

    def comenzar(self):
        # En Linux se copia el proceso tal cual; en Windows y macOS se arranca
        # uno nuevo, que es lo unico que funciona bien ahi con pygame.
        contexto = multiprocessing.get_context("fork" if sys.platform.startswith("linux") else "spawn")
        self.cola = contexto.Queue()
        self.proceso = contexto.Process(target=entrenamiento.entrenarEnProceso, args=(self.cola,), daemon=True)
        self.proceso.start()
        self.estado = "corriendo"
        self.reloj = 0.0
        self.botones = [Boton((520, 640, 240, 50), "Cancelar", self.alCancelar, tamano=28)]
        self.ponerFoco(None, False)
        self.bitacora.append("Población inicial de %d jefes al azar..." % entrenamiento.tamPoblacion)

    def alCancelar(self):
        if self.proceso is not None and self.proceso.is_alive():
            self.proceso.terminate()
        from grafico.pantallas import EscenaTitulo
        self.juego.cambiarEscena(EscenaTitulo(self.juego))

    def jugar(self):
        self.juego.cambiarEscena(EscenaEquipo(self.juego))

    def actualizar(self, dt):
        self.reloj += dt
        self.brasas.actualizar(dt)
        if self.cola is None:
            return
        while True:
            try:
                tipo, datos = self.cola.get_nowait()
            except queue.Empty:
                break
            if tipo == "generacion":
                self.generaciones.append(datos)
                self.poblacion = datos
                factibles = sum(1 for v in datos["violaciones"] if v == 0)
                self.bitacora.append("Generación %d: hipervolumen %.4f, %d jefes dentro de la banda"
                                     % (datos["generacion"], datos["hipervolumen"], factibles))
                reproducirSonido("cursor", 0.5)
            elif tipo == "validando":
                self.estado = "validando"
                self.bitacora.append("Validando al elegido con %d combates por equipo nuevos..."
                                     % entrenamiento.combatesValidacion)
            elif tipo == "listo":
                self.estado = "listo"
                self.resultado = datos
                reproducirSonido("victoria")
                reproducirMusica("victoria", fundido=300)
                self.bitacora.append("Listo. El jefe quedó guardado.")
                self.botones = [Boton((380, 640, 240, 50), "Jugar contra él", self.jugar, tamano=28),
                                Boton((660, 640, 240, 50), "Volver", self.alCancelar, tamano=28)]
                self.ponerFoco(self.botones[0], False)
            elif tipo == "error":
                self.estado = "error"
                self.bitacora.append("Algo falló: " + datos)
                self.botones = [Boton((520, 640, 240, 50), "Volver", self.alCancelar, tamano=28)]
        self.bitacora = self.bitacora[-6:]

    def dibujarGrafica(self, lienzo, rect, puntos, color, minimo=None, maximo=None):
        x, y, w, h = rect
        pygame.draw.rect(lienzo, (6, 10, 40), rect)
        for k in range(1, 4):
            pygame.draw.line(lienzo, (30, 40, 90), (x, y + h * k // 4), (x + w, y + h * k // 4))
        if len(puntos) < 2:
            return
        valores = [p for p in puntos]
        lo = min(valores) if minimo is None else minimo
        hi = max(valores) if maximo is None else maximo
        if hi - lo < 1e-9:
            hi = lo + 1e-9
        total = entrenamiento.generaciones
        lista = [(x + w * (k + 1) / total, y + h - h * (v - lo) / (hi - lo)) for k, v in enumerate(valores)]
        pygame.draw.lines(lienzo, color, False, lista, 3)
        for px, py in lista:
            pygame.draw.circle(lienzo, (255, 255, 255), (int(px), int(py)), 3)

    def dibujarPoblacion(self, lienzo, rect):
        x, y, w, h = rect
        pygame.draw.rect(lienzo, (6, 10, 40), rect)
        for k in range(1, 4):
            pygame.draw.line(lienzo, (30, 40, 90), (x + w * k // 4, y), (x + w * k // 4, y + h))
            pygame.draw.line(lienzo, (30, 40, 90), (x, y + h * k // 4), (x + w, y + h * k // 4))
        if self.poblacion is None:
            return
        for objs, viol in zip(self.poblacion["objetivos"], self.poblacion["violaciones"]):
            px = x + w * min(1.0, objs[0])
            py = y + h - h * min(1.0, objs[1])
            # El color dice el tercer objetivo: verde si la duracion queda cerca de 14 rondas.
            t = min(1.0, objs[2])
            color = (int(80 + 175 * t), int(230 - 150 * t), 90) if viol == 0 else (110, 110, 130)
            pygame.draw.circle(lienzo, (10, 10, 20), (int(px), int(py)), 6)
            pygame.draw.circle(lienzo, color, (int(px), int(py)), 5)

    def dibujar(self, lienzo):
        fondo = obtenerEscenario("arena", (ancho, alto))
        lienzo.blit(fondo, (0, 0))
        velo = pygame.Surface((ancho, alto))
        velo.fill((2, 4, 24))
        velo.set_alpha(185)
        lienzo.blit(velo, (0, 0))

        dibujarPanel(lienzo, (30, 14, 1220, 58))
        dibujarTexto(lienzo, "Entrenar al jefe", (52, 26), 40, colores["resaltado"])
        dibujarTexto(lienzo, "NSGA-II con tres objetivos y semillas rotativas", (390, 34), 26)

        if self.estado == "inicio":
            self.dibujarInicio(lienzo)
        else:
            self.dibujarAvance(lienzo)
        self.dibujarBotones(lienzo)

    def dibujarInicio(self, lienzo):
        dibujarPanel(lienzo, (130, 110, 1020, 460))
        dibujarTitulo(lienzo, "Antes de empezar", (130, 110, 1020, 460))
        lineas = [
            "El algoritmo empieza con %d jefes al azar y los hace evolucionar %d generaciones."
            % (entrenamiento.tamPoblacion, entrenamiento.generaciones),
            "Cada jefe pelea 10 combates contra cada uno de los 15 equipos posibles: 150 combates.",
            "En total son unas 1,830 evaluaciones, más de 270,000 combates simulados.",
            "",
            "Busca jefes que no tengan que ceder en ninguno de estos tres objetivos:",
            "   que el equipo gane cerca de la mitad de las veces,",
            "   que cuando gane le quede poca vida, cerca del 20%,",
            "   y que el combate dure cerca de 14 rondas.",
            "",
            "Del frente final se miden los 5 mejores con combates nuevos y se valida al ganador.",
            "Ese jefe se guarda y es contra el que juegas. Tarda unos minutos.",
        ]
        for k, linea in enumerate(lineas):
            dibujarTexto(lienzo, linea, (170, 140 + k * 34), 26, colores["resaltado"] if k == 4 else None)
        jefe = obtenerSpriteJefe("jefe", False, 0.55)
        lienzo.blit(jefe, jefe.get_rect(midbottom=(1040, 540)))

    def dibujarAvance(self, lienzo):
        hecho = len(self.generaciones)
        total = entrenamiento.generaciones

        # El jefe en entrenamiento, con chispas que suben a su alrededor.
        dibujarPanel(lienzo, (30, 90, 380, 420))
        dibujarTitulo(lienzo, "El jefe", (30, 90, 380, 420))
        self.brasas.zona = (60, 140, 320, 340)
        self.brasas.dibujar(lienzo)
        sprite = "jefe_fase2" if self.estado == "listo" else "jefe"
        flota = 6 * math.sin(self.reloj * 2)
        imagen = obtenerSpriteJefe(sprite, self.estado == "listo", 0.95)
        lienzo.blit(imagen, imagen.get_rect(midbottom=(220, 490 + flota)))

        dibujarPanel(lienzo, (424, 90, 400, 260))
        dibujarTitulo(lienzo, "Hipervolumen del frente", (424, 90, 400, 260))
        self.dibujarGrafica(lienzo, (446, 118, 356, 212), [g["hipervolumen"] for g in self.generaciones], (120, 200, 255))

        dibujarPanel(lienzo, (838, 90, 412, 260))
        dibujarTitulo(lienzo, "Población", (838, 90, 412, 260))
        self.dibujarPoblacion(lienzo, (860, 118, 368, 192))
        dibujarTexto(lienzo, "horizontal: desbalance   vertical: holgura", (860, 318), 18, colores["textoSuave"])
        dibujarTexto(lienzo, "verde: buena duración   gris: fuera de la banda", (860, 336), 16, colores["textoSuave"])

        dibujarPanel(lienzo, (424, 362, 826, 148))
        dibujarTitulo(lienzo, "Bitácora", (424, 362, 826, 148))
        for k, linea in enumerate(self.bitacora[-4:]):
            dibujarTexto(lienzo, linea, (448, 380 + k * 30), 22, anchoMax=780)

        dibujarPanel(lienzo, (30, 522, 1220, 104))
        segundos = self.generaciones[-1]["segundos"] if self.generaciones else self.reloj
        if self.estado == "corriendo":
            texto = "Generación %d de %d" % (hecho, total)
            if hecho:
                falta = segundos / hecho * (total - hecho)
                texto += "   faltan unos %d s" % max(1, falta)
        elif self.estado == "validando":
            texto = "Validando al elegido..."
        elif self.estado == "listo":
            texto = "Entrenamiento terminado en %.0f s" % self.resultado["segundos"]
        else:
            texto = "El entrenamiento se detuvo"
        dibujarTexto(lienzo, texto, (56, 538), 28)
        avance = hecho / total if self.estado == "corriendo" else (0.98 if self.estado == "validando" else 1.0)
        dibujarBarra(lienzo, (56, 580, 1168, 22), avance, (240, 190, 70))

        if self.estado == "listo":
            v = self.resultado["validacion"]
            dibujarPanel(lienzo, (30, 90, 380, 420), (90, 70, 20))
            dibujarTitulo(lienzo, "¡Jefe listo!", (30, 90, 380, 420))
            imagen = obtenerSpriteJefe("jefe", False, 0.8)
            lienzo.blit(imagen, imagen.get_rect(midbottom=(220, 330 + flota)))
            filas = [("F validada", "%.3f" % v["fitness"]), ("Gana el equipo", "%.0f%%" % (100 * v["p_victoria"])),
                     ("Rondas promedio", "%.1f" % v["rondas_prom"]), ("Margen", "%.2f" % v["margen"]),
                     ("Duración", "%.2f" % v["duracion"])]
            for k, (etiqueta, valor) in enumerate(filas):
                dibujarTexto(lienzo, etiqueta, (60, 344 + k * 30), 23, colores["textoSuave"])
                dibujarTexto(lienzo, valor, (300, 344 + k * 30), 23)


def estadisticas(registro, nombres):
    # Lo que hizo cada quien en el combate, sacado del registro del motor.
    porHeroe = {n: {"hecho": 0, "recibido": 0, "curado": 0, "criticos": 0, "esquivas": 0, "turnos": 0} for n in nombres}
    ataquesJefe = {}
    for ev in registro:
        if ev.get("tipo") != "turno":
            continue
        actor = ev["actor"]
        if actor == "Jefe":
            if ev["golpes"]:
                ataquesJefe[ev["accion"]] = ataquesJefe.get(ev["accion"], 0) + 1
            for quien, dano, nota in ev["golpes"]:
                porHeroe[quien]["recibido"] += dano
                if nota == "esquiva":
                    porHeroe[quien]["esquivas"] += 1
        else:
            yo = porHeroe[actor]
            yo["turnos"] += 1
            for _, dano, nota in ev["golpes"]:
                yo["hecho"] += dano
                yo["criticos"] += nota == "critico"
            for _, cantidad in ev["curas"]:
                yo["curado"] += cantidad
    return porHeroe, ataquesJefe


def evaluacionDelCombate(res):
    # Los ingredientes de la aptitud del jefe medidos en este solo combate, con
    # las mismas formulas de aptitud.py.
    margen = 1 - abs(res["hp_final_pct"] - m.HP_IDEAL) / (1 - m.HP_IDEAL) if res["gana_equipo"] else 0.0
    duracion = math.exp(-(res["rondas"] - m.RONDAS_IDEAL) ** 2 / (2 * m.SIGMA_RONDAS ** 2))
    usos = res["usos"]
    total = sum(usos)
    variedad = 0.0
    if total:
        H = -sum(u / total * math.log2(u / total) for u in usos if u > 0)
        variedad = H / math.log2(len(usos))
    nota = m.W_MARGEN * margen + m.W_DURACION * duracion + m.W_VARIEDAD * variedad
    return {"margen": margen, "duracion": duracion, "variedad": variedad, "nota": nota}


class EscenaResultados(Escena):

    def __init__(self, juego, combate):
        super().__init__(juego)
        self.combate = combate
        self.res = combate.partida.resultado
        self.nombres = combate.nombres
        self.gano = self.res["gana_equipo"]
        self.porHeroe, self.ataquesJefe = estadisticas(combate.partida.registro, self.nombres)
        self.evaluacion = evaluacionDelCombate(self.res)
        self.jefe, self.entrenado = entrenamiento.jefeOptimo()
        self.reloj = 0.0
        self.confeti = Brasas(90, (255, 210, 110)) if self.gano else Brasas(40, (90, 110, 200))
        self.botones = [Boton((690, 646, 180, 52), "Revancha", self.revancha, tamano=28),
                        Boton((880, 646, 180, 52), "Otro equipo", self.otroEquipo, tamano=28),
                        Boton((1070, 646, 180, 52), "Título", self.alCancelar, tamano=28)]
        self.ponerFoco(self.botones[0], False)
        if self.gano:
            reproducirMusica("victoria")
        else:
            reproducirMusica("derrota")
        # El mas valioso: el que mas daño hizo, con la curacion contando igual.
        self.mvp = max(self.nombres, key=lambda n: self.porHeroe[n]["hecho"] + self.porHeroe[n]["curado"])

    def revancha(self):
        self.juego.cambiarEscena(EscenaCombate(self.juego, self.combate.crom, self.nombres))

    def otroEquipo(self):
        self.juego.cambiarEscena(EscenaEquipo(self.juego))

    def alCancelar(self):
        self.juego.cambiarEscena(EscenaTitulo(self.juego))

    def actualizar(self, dt):
        self.reloj += dt
        self.confeti.actualizar(dt)

    def dibujar(self, lienzo):
        fondo = obtenerEscenario("arena_fase2" if self.res["ronda_fase2"] else "arena", (ancho, alto))
        lienzo.blit(fondo, (0, 0))
        velo = pygame.Surface((ancho, alto))
        velo.fill((2, 4, 20) if self.gano else (16, 2, 6))
        velo.set_alpha(170)
        lienzo.blit(velo, (0, 0))
        self.confeti.dibujar(lienzo)

        # El letrero baja desde arriba.
        entra = min(1.0, self.reloj / 0.5)
        y = int(-60 + 84 * (1 - (1 - entra) ** 3))
        titulo = "¡Victoria!" if self.gano else "Derrota"
        dibujarPanel(lienzo, (440, y, 400, 70), (110, 80, 20) if self.gano else (90, 20, 30))
        dibujarTexto(lienzo, titulo, (640, y + 36), 56, colores["jefe"] if self.gano else (255, 140, 140), centrado=True)

        # Los heroes: saltan si ganaron y quedan tendidos si no.
        for k, nombre in enumerate(self.nombres):
            x = 120 + k * 130
            vivo = self.res["hp_equipo"][k] > 0
            pose = "celebra" if self.gano and vivo else ("caido" if not vivo else "herido")
            salto = 0
            if self.gano and vivo:
                fase = (self.reloj / 0.55 + k * 0.25) % 1.0
                salto = 22 * math.sin(math.pi * fase)
            sprite = obtenerSprite(nombre, pose, alturaHeroe)
            pygame.draw.ellipse(lienzo, (0, 0, 0), (x - 40, 252, 80, 14))
            lienzo.blit(sprite, sprite.get_rect(midbottom=(x, 260 - salto)))
            dibujarTexto(lienzo, nombre, (x, 278), 22, colores["heroe"], centrado=True)
            if nombre == self.mvp:
                dibujarTexto(lienzo, "MVP", (x, 120 - salto), 22, colores["resaltado"], centrado=True)

        # Tabla de lo que hizo cada uno.
        dibujarPanel(lienzo, (30, 304, 640, 250))
        dibujarTitulo(lienzo, "Estadísticas", (30, 304, 640, 250))
        columnas = (("Héroe", 52), ("Daño", 210), ("Recibido", 300), ("Curó", 420), ("Críticos", 500), ("Esquivas", 590))
        for texto, x in columnas:
            dibujarTexto(lienzo, texto, (x, 324), 22, colores["resaltado"])
        for k, nombre in enumerate(self.nombres):
            e = self.porHeroe[nombre]
            yy = 356 + k * 34
            valores = (nombre, e["hecho"], e["recibido"], e["curado"], e["criticos"], e["esquivas"])
            for (texto, x), valor in zip(columnas, valores):
                dibujarTexto(lienzo, str(valor), (x, yy), 23, colores["heroe"] if x == 52 else None)
        dibujarTexto(lienzo, "Rondas: %d     Vida del equipo al final: %.0f%%"
                     % (self.res["rondas"], 100 * self.res["hp_final_pct"]), (52, 500), 22)
        if self.ataquesJefe:
            favorito = max(self.ataquesJefe, key=self.ataquesJefe.get)
            veces = self.ataquesJefe[favorito]
            dibujarTexto(lienzo, "Lo que más usó el jefe: %s (%d %s)" % (favorito, veces, "vez" if veces == 1 else "veces"),
                         (52, 524), 20, colores["textoSuave"])

        # Como califica el algoritmo este combate.
        ev = self.evaluacion
        dibujarPanel(lienzo, (690, 104, 560, 530))
        dibujarTitulo(lienzo, "Cómo evalúa el algoritmo este combate", (690, 104, 560, 530))
        texto = [
            "El jefe se diseñó para que los combates sean parejos:",
            "que el equipo gane 40-60% de las veces, con cerca de",
            "20% de vida y en unas 14 rondas.",
        ]
        for k, linea in enumerate(texto):
            dibujarTexto(lienzo, linea, (714, 128 + k * 26), 21, colores["textoSuave"])
        filas = [("Margen", ev["margen"], "%.0f%% de vida al final, lo ideal es 20%%" % (100 * self.res["hp_final_pct"])
                  if self.gano else "si el equipo pierde, el margen es cero"),
                 ("Duración", ev["duracion"], "%d rondas, lo ideal es %d" % (self.res["rondas"], m.RONDAS_IDEAL)),
                 ("Variedad", ev["variedad"], "qué tan repartidos usó sus %d ataques" % len(self.res["usos"]))]
        for k, (nombre, valor, explicacion) in enumerate(filas):
            yy = 220 + k * 76
            dibujarTexto(lienzo, nombre, (714, yy), 26)
            dibujarBarra(lienzo, (850, yy + 6, 300, 16), valor, (110, 200, 120) if valor > 0.6 else (230, 190, 80) if valor > 0.3 else (220, 100, 100))
            dibujarTexto(lienzo, "%.2f" % valor, (1166, yy), 26)
            dibujarTexto(lienzo, explicacion, (714, yy + 32), 20, colores["textoSuave"])
        dibujarTexto(lienzo, "Nota de este combate", (714, 452), 26, colores["resaltado"])
        dibujarTexto(lienzo, "%.3f" % ev["nota"], (1166, 452), 28, colores["resaltado"])
        dibujarTexto(lienzo, "0.5 margen + 0.25 duración + 0.25 variedad", (714, 484), 19, colores["textoSuave"])
        if self.entrenado:
            v = self.jefe["validacion"]
            dibujarTexto(lienzo, "F del jefe en su validación: %.3f (el equipo gana %.0f%%)" % (v["fitness"], 100 * v["p_victoria"]),
                         (714, 520), 20)
        dibujarTexto(lienzo, "La F real promedia cientos de combates y se multiplica por qué tan", (714, 552), 18, colores["textoSuave"])
        dibujarTexto(lienzo, "cerca de la banda de 40-60% de victorias queda el jefe.", (714, 574), 18, colores["textoSuave"])

        self.dibujarBotones(lienzo)
