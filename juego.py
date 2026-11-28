# Juego con ventana. Mismo motor y mismas reglas que jugar.py, pero dibujado,
# con musica y sonido.
#
# Uso: python juego.py
import multiprocessing

import pygame

from grafico.interfaz import ancho, alto, colores
from grafico.recursos import iniciarAudio

cuadrosPorSegundo = 60
duracionFundido = 0.35


class Juego:

    def __init__(self):
        iniciarAudio()
        pygame.init()
        pygame.display.set_caption("Jefe RPG evolutivo")

        # Con SCALED pygame estira el lienzo al tamaño de la ventana y traduce
        # las coordenadas del ratón. Hay equipos y entornos de prueba sin
        # ventana donde ese modo no existe, y ahí se usa el modo simple.
        try:
            self.lienzo = pygame.display.set_mode((ancho, alto), pygame.SCALED | pygame.RESIZABLE)
        except pygame.error:
            self.lienzo = pygame.display.set_mode((ancho, alto))

        self.corriendo = True
        self.fundido = duracionFundido
        self.negro = pygame.Surface((ancho, alto))
        from grafico.pantallas import EscenaTitulo
        self.escena = EscenaTitulo(self)

    def cambiarEscena(self, escena):
        # La escena nueva entra de inmediato y aparece desde negro.
        self.escena = escena
        self.fundido = 0.0 if getattr(escena, "sinFundido", False) else duracionFundido

    def salir(self):
        self.corriendo = False

    def manejarEvento(self, evento):
        if evento.type == pygame.QUIT:
            self.salir()
        elif evento.type == pygame.KEYDOWN and evento.key == pygame.K_F11:
            try:
                pygame.display.toggle_fullscreen()
            except pygame.error:
                pass
        else:
            self.escena.manejarEvento(evento)

    def cuadro(self, dt):
        # Un cuadro muy largo, como al arrastrar la ventana, no debe adelantar
        # de golpe las animaciones.
        dt = min(dt, 0.1)
        self.escena.actualizar(dt)
        self.lienzo.fill(colores["fondo"])
        self.escena.dibujar(self.lienzo)
        if self.fundido > 0:
            self.negro.set_alpha(int(255 * self.fundido / duracionFundido))
            self.lienzo.blit(self.negro, (0, 0))
            self.fundido -= dt

    def correr(self):
        reloj = pygame.time.Clock()
        while self.corriendo:
            dt = reloj.tick(cuadrosPorSegundo) / 1000
            for evento in pygame.event.get():
                self.manejarEvento(evento)
            self.cuadro(dt)
            pygame.display.flip()
        pygame.quit()


if __name__ == "__main__":
    # En Windows el entrenamiento corre en otro proceso y esto lo necesita.
    multiprocessing.freeze_support()
    Juego().correr()
