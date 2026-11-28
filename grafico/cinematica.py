# La cinematica del paso a la segunda fase.
#
# 1. En la arena el jefe empieza a sacudirse, la pantalla retumba y caen rayos
#    y destellos a su alrededor.
# 2. Un destello blanco corta a su retrato: la rueda que flota sobre su cabeza
#    gira de punta en punta y se frena en seco en cada una, cada vez con menos
#    pausa y mas velocidad, y cada frenon sacude la pantalla mas fuerte. Al
#    final ya no se detiene y acelera hasta volverse un disco de luz.
# 3. Con la rueda a todo lo que da abre la boca y grita, y todo retiembla.
# 4. Otro destello y de vuelta en la arena, que ya es la de la segunda fase,
#    con el jefe transformado.
#
# La rueda y el fondo son recursos/escenarios/titulo_rueda.png y
# titulo_fondo.png, las mismas capas de la pantalla de titulo.
import math

import numpy as np
import pygame

from grafico.interfaz import ancho, alto
from grafico.recursos import reproducirSonido, rutaDe
from grafico.animaciones import Animacion, Capas, azar
from grafico import recetas
import os

centroRueda = (640, 132)

# Donde esta la boca en titulo_fondo.png: entre que columnas se mueve la cara,
# entre cuales estan los dientes (solo ahi se abre el hueco), la linea entre
# los dientes (una curva que sube hacia las comisuras), desde donde se estiran
# los cachetes y hasta donde baja la mandibula.
bocaIzquierda, bocaDerecha, bocaCentro = 576, 714, 645
dientesIzquierda, dientesDerecha = 614, 676
lineaBoca, curvaBoca, inicioCachetes, finMandibula = 525, 0.003, 474, 600
# Cuanto suben las comisuras por cada pixel que se abre la boca.
subidaComisuras = 0.35


def pasosDeRueda(pausa, giro, reduccionPausa, reduccionGiro, giroMinimo, sinPausa, velocidadFinal):
    # Arma la lista de tramos de la rueda: pausas y giros de 45 grados.
    tramos, t, angulo = [], 0.0, 0.0
    while pausa > 0.045:
        tramos.append(("pausa", t, t + pausa, angulo, True))
        t += pausa
        tramos.append(("giro", t, t + giro, angulo, True))
        t += giro
        angulo += 45
        pausa *= reduccionPausa
        giro = max(giroMinimo, giro * reduccionGiro)
    # Ya sin pausas sigue acelerando hasta su velocidad final.
    corrido = giro / 2
    paso = 45 / velocidadFinal
    inicio = t
    while t - inicio < sinPausa:
        u = min(1.0, (t - inicio) / sinPausa)
        corrido = (giro / 2) * (paso / (giro / 2)) ** u
        tramos.append(("giro", t, t + corrido, angulo, False))
        t += corrido
        angulo += 45
    return tramos, t, angulo


class CinematicaFase2:

    def __init__(self, escena):
        self.escena = escena
        self.tiempo = 0.0
        self.previa = 2.6
        tramos, giros, angulo = pasosDeRueda(0.65, 0.38, 0.76, 0.82, 0.07, 2.4, 1500.0)
        self.tramos = [(tipo, a + self.previa + 0.25, b + self.previa + 0.25, ang, frena) for tipo, a, b, ang, frena in tramos]
        self.anguloFinal = angulo
        self.inicioGrito = self.previa + 0.25 + giros
        self.duracionGrito = 2.7
        self.finRueda = self.inicioGrito + self.duracionGrito
        self.duracion = self.finRueda + 1.1
        self.velocidadFinal = 1500.0

        # Lo que suena y cuando.
        self.agenda = [(0.0, "temblor", 1.0), (0.1, "jefe_rugido", 0.9), (0.9, "trueno", 0.9), (1.6, "trueno", 0.8),
                       (2.2, "temblor", 1.0), (self.previa, "destello", 1.0), (self.previa + 0.3, "zumbido", 0.5),
                       (self.inicioGrito - 1.2, "temblor", 1.0), (self.inicioGrito, "jefe_grito", 1.0),
                       (self.inicioGrito + 0.2, "temblor", 1.0), (self.inicioGrito + 1.3, "temblor", 1.0),
                       (self.finRueda, "cambio_de_fase", 1.0)]
        self.sacudidas = [(0.0, 3, 2.6)]
        frenones = [tr for tr in self.tramos if tr[0] == "pausa"]
        for k, tr in enumerate(frenones[1:], start=1):
            self.agenda.append((tr[1], "rueda", 0.6 + 0.04 * k))
            self.sacudidas.append((tr[1], 2.5 + 1.1 * k, 0.4))
        self.sacudidas.append((self.inicioGrito - 1.2, 6, 1.4))
        self.sacudidas.append((self.inicioGrito, 16, self.duracionGrito + 0.2))
        inicioCorrido = next((tr[1] for tr in self.tramos if not tr[4]), self.inicioGrito - 2.0)
        self.inicioCorrido = inicioCorrido
        self.agenda.append((inicioCorrido - 0.8, "giro_rapido", 0.9))
        self.agenda.append((self.inicioGrito - 0.6, "zumbido", 0.6))
        self.agenda.sort()
        self.sonados = 0

        self.fondo = self.rueda = None
        rutaFondo, rutaRueda = rutaDe("escenarios", "titulo_fondo"), rutaDe("escenarios", "titulo_rueda")
        if os.path.exists(rutaFondo) and os.path.exists(rutaRueda):
            self.fondo = pygame.image.load(rutaFondo).convert()
            self.rueda = pygame.image.load(rutaRueda).convert_alpha()
            self.bocaOriginal = pygame.surfarray.array3d(self.fondo.subsurface(self.rectBoca())).copy()
        self.ruedaSuma = {}
        self.efectos = self.armarEfectos()
        self.capas = Capas(ancho, alto)
        self.blanco = pygame.Surface((ancho, alto))
        self.blanco.fill((255, 255, 255))

    def rectBoca(self):
        return pygame.Rect(bocaIzquierda, inicioCachetes, bocaDerecha - bocaIzquierda, finMandibula - inicioCachetes)

    def armarEfectos(self):
        # Lo que pasa sobre el retrato: chispas en cada frenon de la rueda y,
        # mientras grita, rayos que salen de la rueda, la pantalla que late en
        # rojo y destellos. Las medidas van a la mitad, como en las capas.
        anim = Animacion()
        cx, cy = centroRueda[0] / 2, centroRueda[1] / 2
        inicio = self.previa + 0.12
        for tipo, a, b, ang, frena in self.tramos:
            if tipo == "pausa" and a > inicio + 0.2:
                for k in range(2):
                    angulo = math.radians(ang - 90 + k * 180)
                    recetas.chispazo(anim, a - inicio, cx + 58 * math.cos(angulo), cy + 58 * math.sin(angulo), 0.8, (255, 230, 170))
        g = self.inicioGrito - inicio
        anim.tinte(g, g + self.duracionGrito, (150, 10, 20), 38, 0.3, 0.4)
        k = 0
        t = g + 0.1
        while t < g + self.duracionGrito - 0.2:
            a = azar.uniform(0, math.tau)
            largo = azar.uniform(180, 330)
            recetas.relampago(anim, t, cx, cy, cx + largo * math.cos(a), cy + largo * 0.7 * math.sin(a),
                              (190, 110, 255) if k % 2 else (255, 220, 140), 0.18, 2, 18, 3)
            if k % 3 == 0:
                anim.destello(t, (255, 235, 230), 0.1, 90)
            t += azar.uniform(0.12, 0.24)
            k += 1
        for k in range(4):
            recetas.anilloDeChoque(anim, g + 0.15 + 0.55 * k, cx, cy, 340, (255, 200, 170), 0.6, 1.0, 3)
        motas = anim.particulas([(255, 250, 230), (255, 200, 150), (230, 90, 70), (120, 30, 40), (40, 10, 14)], gravedad=-40, freno=0.3)
        ritmo = recetas.cadencia(120)

        def soltar(u, dt):
            for _ in range(ritmo(dt)):
                a = azar.uniform(0, math.tau)
                motas.emitir(cx, cy, 260 * math.cos(a) * azar.uniform(0.4, 1), 260 * math.sin(a) * azar.uniform(0.4, 1), 1.0, azar.choice((2, 3)))
        anim.durante(g + 0.1, g + self.duracionGrito - 0.3, soltar)
        anim.alargar(self.finRueda - inicio + 0.2)
        return anim

    # El paso del tiempo

    def actualizar(self, dt):
        self.tiempo += dt
        if self.tiempo > self.previa + 0.12:
            self.efectos.actualizar(dt)
        while self.sonados < len(self.agenda) and self.agenda[self.sonados][0] <= self.tiempo:
            _, nombre, volumen = self.agenda[self.sonados]
            reproducirSonido(nombre, volumen)
            self.sonados += 1
        return self.tiempo < self.duracion

    def saltar(self):
        # Con una tecla se brinca al destello final.
        if self.tiempo < self.finRueda - 0.1:
            self.tiempo = self.finRueda - 0.1
            self.sonados = len([a for a in self.agenda if a[0] < self.tiempo])

    def enLaArena(self):
        return self.tiempo < self.previa + 0.12 or self.tiempo >= self.finRueda + 0.12

    def yaEsFase2(self):
        return self.tiempo >= self.finRueda + 0.12

    def agitacionJefe(self):
        # Cuanto se sacude el jefe en la arena antes del corte.
        if self.tiempo >= self.previa:
            return 0, 0
        fuerza = 2 + 7 * self.tiempo / self.previa
        return int(fuerza * math.sin(self.tiempo * 61)), int(fuerza * 0.5 * math.cos(self.tiempo * 47))

    def desplazamiento(self):
        dx = dy = 0.0
        for inicio, fuerza, dura in self.sacudidas:
            d = self.tiempo - inicio
            if 0 <= d < dura:
                queda = fuerza * (1 - d / dura) if dura > 0.6 else fuerza * math.exp(-d / 0.12)
                dx += queda * math.sin(d * 83 + inicio)
                dy += queda * math.cos(d * 67 + inicio * 2)
        limite = 24
        return int(max(-limite, min(limite, dx))), int(max(-limite, min(limite, dy)))

    def velo(self):
        # El blanco de los dos destellos: el del corte y el del regreso.
        for centro, sube, baja in ((self.previa + 0.1, 0.12, 0.35), (self.finRueda + 0.1, 0.15, 0.9)):
            d = self.tiempo - centro
            if -sube <= d < 0:
                return int(255 * (1 + d / sube))
            if 0 <= d < baja:
                return int(255 * (1 - d / baja))
        return 0

    # La rueda

    def angulo(self, t):
        for tipo, a, b, ang, frena in self.tramos:
            if a <= t < b:
                if tipo == "giro":
                    u = (t - a) / (b - a)
                    return ang + 45 * (u * u if frena else u)
                # Al frenar se pasa tantito y regresa: el golpe seco.
                d = t - a
                return ang + 2.5 * math.exp(-d / 0.045) * math.sin(d / 0.022)
        if self.tramos and t >= self.tramos[-1][2]:
            return self.anguloFinal + self.velocidadFinal * (t - self.tramos[-1][2])
        return 0.0

    def ruedaPara(self, muestras):
        # La rueda ya oscurecida para sumarse varias veces y dar el barrido.
        if muestras not in self.ruedaSuma:
            sup = pygame.Surface(self.rueda.get_size())
            sup.fill((0, 0, 0))
            sup.blit(self.rueda, (0, 0))
            sup.fill((255 // muestras,) * 3, special_flags=pygame.BLEND_RGB_MULT)
            self.ruedaSuma[muestras] = sup
        return self.ruedaSuma[muestras]

    def apertura(self):
        # Cuanto tiene abierta la boca, en pixeles.
        d = self.tiempo - self.inicioGrito
        if d < 0:
            return 0.0
        if d < 0.35:
            base = 30 * (d / 0.35) ** 0.6
        elif d < self.duracionGrito - 0.4:
            base = 30
        else:
            base = 30 * max(0.0, (self.duracionGrito - d) / 0.4)
        return base + (3 * math.sin(d * 40) if 0.35 < d < self.duracionGrito - 0.4 else 0)

    def dibujarBoca(self, lienzo, abierta):
        # La boca se abre como una sonrisa, en forma de luna creciente: el borde
        # de arriba sube hacia las comisuras, la mandibula baja en medio y las
        # dos orillas se juntan en punta en las orillas de los dientes. Solo ahi
        # hay hueco; de los dientes a los cachetes la cara se estira como hule
        # siguiendo a las comisuras, sin cortarse.
        rect = self.rectBoca()
        original = self.bocaOriginal
        ancho_, alto_ = original.shape[0], original.shape[1]
        salida = original.copy()
        centroDientes = (dientesIzquierda + dientesDerecha) / 2
        mitadDientes = (dientesDerecha - dientesIzquierda) / 2
        mitadBoca = max(centroDientes - bocaIzquierda, bocaDerecha - centroDientes)
        subida = abierta * subidaComisuras
        for cx in range(ancho_):
            x = rect.x + cx
            distancia = abs(x - centroDientes)
            if distancia >= mitadBoca:
                continue
            corte = int(lineaBoca - curvaBoca * (x - centroDientes) ** 2) - rect.y
            corte = max(4, min(alto_ - 6, corte))
            if distancia <= mitadDientes:
                u = distancia / mitadDientes
                arriba = corte - subida * u * u
                hueco = abierta * (1 - u * u) ** 0.7
            else:
                # Entre los dientes y los cachetes las comisuras bajan poco a
                # poco a su lugar.
                v = (distancia - mitadDientes) / (mitadBoca - mitadDientes)
                arriba = corte - subida * (1 - v * v * (3 - 2 * v))
                hueco = 0.0
            arriba = int(round(arriba))
            negro = int(round(hueco))
            abajo = arriba + negro
            if arriba < 2 or alto_ - abajo < 4:
                continue

            columna = original[cx]
            nueva = columna.copy()
            # Lo de arriba del corte se encoge hasta donde empieza el hueco y lo
            # de abajo se acomoda desde donde termina, sin mover la barbilla.
            origen = (np.arange(arriba) * (corte - 1) / max(1, arriba - 1)).astype(int)
            nueva[:arriba] = columna[origen]
            largo = alto_ - corte
            origen = corte + (np.arange(alto_ - abajo) * (largo - 1) / max(1, alto_ - abajo - 1)).astype(int)
            nueva[abajo:] = columna[origen]
            if negro > 0:
                for k in range(negro):
                    profundo = 1 - abs(k - negro / 2) / max(1, negro / 2)
                    nueva[arriba + k] = (int(38 * profundo), int(3 * profundo), int(8 * profundo))
                # Una linea oscura en cada borde del hueco, como el contorno del dibujo.
                nueva[arriba] = (8, 6, 10)
                nueva[min(alto_ - 1, abajo)] = (8, 6, 10)
            salida[cx] = nueva
        lienzo.blit(pygame.surfarray.make_surface(salida), rect)

    def dibujarRetrato(self, lienzo):
        if self.fondo is None:
            lienzo.fill((0, 0, 0))
            return
        lienzo.blit(self.fondo, (0, 0))
        abierta = self.apertura()
        if abierta > 0.5:
            self.dibujarBoca(lienzo, abierta)

        t = self.tiempo
        a0, a1 = self.angulo(t), self.angulo(t + 1 / 60)
        muestras = max(1, min(5, int(abs(a1 - a0) / 4)))
        for m in range(muestras):
            a = a0 + (a1 - a0) * m / muestras
            girada = pygame.transform.rotozoom(self.ruedaPara(muestras), -a, 1.0)
            lienzo.blit(girada, girada.get_rect(center=centroRueda), special_flags=pygame.BLEND_RGB_ADD)

        # Mientras grita la rueda echa un resplandor que late.
        d = t - self.inicioGrito
        if d > 0:
            fuerza = min(1.0, d / 0.4) * (0.6 + 0.4 * math.sin(d * 30))
            radio = int(170 + 20 * math.sin(d * 23))
            halo = pygame.Surface((radio * 2, radio * 2))
            halo.fill((0, 0, 0))
            for r, tono in ((radio, 40), (int(radio * 0.7), 70), (int(radio * 0.4), 110)):
                pygame.draw.circle(halo, (int(tono * fuerza), int(tono * 0.8 * fuerza), int(tono * 0.4 * fuerza)), (radio, radio), r)
            lienzo.blit(halo, halo.get_rect(center=centroRueda), special_flags=pygame.BLEND_RGB_ADD)
        self.dibujarEfectos(lienzo)
        self.acercar(lienzo)

    def zoom(self):
        # La camara se acerca despacio mientras la rueda acelera, y de golpe
        # cuando grita, con un latido en cada rugido.
        t = self.tiempo
        if t < self.inicioCorrido:
            return 1.0
        if t < self.inicioGrito:
            return 1.0 + 0.06 * (t - self.inicioCorrido) / max(0.1, self.inicioGrito - self.inicioCorrido)
        d = t - self.inicioGrito
        return 1.06 + 0.08 * min(1.0, d / 0.25) + 0.015 * math.sin(d * 25)

    def acercar(self, lienzo):
        z = self.zoom()
        if z <= 1.001:
            return
        cx, cy = 640, 300
        w, h = int(ancho / z), int(alto / z)
        x = int(cx - w * cx / ancho)
        y = int(cy - h * cy / alto)
        recorte = lienzo.subsurface(pygame.Rect(x, y, w, h)).copy()
        pygame.transform.smoothscale(recorte, (ancho, alto), lienzo)

    def dibujarEfectos(self, lienzo):
        capas = self.capas
        capas.limpiar()
        self.efectos.dibujar(capas)
        for color, fuerza in self.efectos.velosActivos():
            velo = pygame.Surface((ancho, alto))
            velo.fill(color)
            velo.set_alpha(fuerza)
            lienzo.blit(velo, (0, 0))
        capas.volcar(lienzo, "frente")
        capas.volcar(lienzo, "luz")

    def dibujarEncima(self, lienzo):
        nivel = self.velo()
        if nivel > 0:
            self.blanco.set_alpha(nivel)
            lienzo.blit(self.blanco, (0, 0))
