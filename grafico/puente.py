# Puente entre el motor y la ventana. El motor corre un combate completo de
# una sola llamada y le pregunta a una política qué hace cada héroe; la ventana
# en cambio tiene que seguir dibujando mientras el jugador piensa. Para no
# reescribir el motor, el combate corre en un hilo aparte y la política se
# queda esperando la respuesta que llega desde la ventana.
import queue
import threading

import motor as m


class PartidaCancelada(Exception):
    pass


class PartidaEnHilo:

    def __init__(self, crom, equipo, semilla):
        self.registro = []
        self.peticion = None
        self.resultado = None
        self.respuestas = queue.Queue()
        self.cancelada = False

        self.hilo = threading.Thread(target=self.correr, args=(crom, equipo, semilla), daemon=True)
        self.hilo.start()

    def correr(self, crom, equipo, semilla):
        try:
            self.resultado = m.simular(crom, equipo, semilla, registro=self.registro, politica=self.politica)
        except PartidaCancelada:
            pass

    def politica(self, i, est, opciones):
        self.peticion = {"heroe": i, "est": est, "opciones": opciones}
        respuesta = self.respuestas.get()
        self.peticion = None
        if self.cancelada:
            raise PartidaCancelada()
        return respuesta

    def responder(self, accion):
        self.respuestas.put(accion)

    def cancelar(self):
        # Si el jugador sale a media partida hay que soltar al hilo, que está
        # esperando una respuesta.
        self.cancelada = True
        self.respuestas.put(None)

    def terminada(self):
        return self.resultado is not None
