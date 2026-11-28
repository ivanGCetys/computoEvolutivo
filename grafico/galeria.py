# Galeria de animaciones: reproduce el ataque que se elija sobre la arena, sin
# jugar una partida, para revisar como se ve cada uno.
#
# Uso: python -m grafico.galeria
#   flechas izquierda y derecha   cambiar de ataque
#   espacio                       repetirlo
#   F                             cambiar de fase del jefe
#   Escape                        salir
import pygame

import jugar
import motor as m
from grafico import escenas
from grafico.interfaz import ancho, alto, colores, dibujarPanel, dibujarTexto

equipos = (["Guerrero", "Tanque", "Mago", "Clerigo"], ["Mago", "Clerigo", "Picaro", "Berserker"])


def catalogo():
    # Todo lo que se puede animar: (quien, accion, elemento, tipo).
    lista = []
    for ataque in m.HABILIDADES:
        if ataque["carga"]:
            lista.append(("Jefe", "Carga " + ataque["nombre"], None, "apoyo"))
        lista.append(("Jefe", ataque["nombre"], ataque["elem"], "area" if ataque["enArea"] else "uno"))

    for clase in m.nombresClases:
        lista.append((clase, "Ataque basico", None, "uno"))
        for conjuro in m.tablaClases[clase]["conjuros"]:
            elem = conjuro.get("elem")
            if elem == "azar":
                elem = 0
            tipo = {"ataque": "uno", "cura": "grupo" if conjuro.get("enGrupo") else "cura"}.get(conjuro["tipo"], "apoyo")
            lista.append((clase, conjuro["nombre"], elem, tipo))
        lista.append((clase, "Bloquea", None, "apoyo"))
    for conjuro in m.conjurosMago + m.conjurosMagoPoderosos:
        lista.append(("Mago", conjuro["nombre"], conjuro["elem"], "uno"))
    lista.append(("Guerrero", "Bebe " + m.nombrePocion["hpChica"], None, "cura"))
    lista.append(("Mago", "Bebe " + m.nombrePocion["spChica"], None, "apoyo"))
    return lista


class EscenaGaleria(escenas.EscenaCombate):

    def __init__(self, juego, nombres=equipos[0], fase2=False):
        crom = jugar.candidatosDeJefe()[1][0][1]["crom"]
        super().__init__(juego, crom, list(nombres), semilla=1)
        # De la partida solo hace falta su primer evento, que trae las vidas.
        while not self.partida.registro:
            pygame.time.wait(2)
        self.mostrarEvento(self.partida.registro[0])
        self.partida.cancelar()
        self.fase2 = fase2
        self.botones = []
        self.rotulo = ""
        self.entrada = None

    def actualizar(self, dt):
        self.actualizarLoQueSeVe(dt)

    def eventoDe(self, quien, accion, elem, tipo):
        ev = {"tipo": "turno", "actor": quien, "accion": accion, "elem": elem, "golpes": [], "curas": [], "muertos": [],
              "adelantado": False, "hp_equipo": list(self.vida), "sp_equipo": list(self.mana), "hp_jefe": self.vidaJefe,
              "protecciones": [[] for _ in self.nombres]}
        if quien == "Jefe":
            if tipo == "area":
                ev["golpes"] = [(n, 40 + 7 * k, "") for k, n in enumerate(self.nombres)]
            elif tipo == "uno":
                ev["golpes"] = [(self.nombres[2], 85, "critico")]
        elif tipo == "uno":
            ev["golpes"] = [("Jefe", 64, "")]
        elif tipo == "cura":
            ev["curas"] = [(quien, 60)]
        elif tipo == "grupo":
            ev["curas"] = [(n, 45) for n in self.nombres]
        return ev

    def reproducir(self, quien, accion, elem, tipo):
        self.efectos, self.animaciones, self.pendientes = [], [], []
        self.rotulo = "%s: %s" % (quien, accion)
        return self.animarTurno(self.eventoDe(quien, accion, elem, tipo))

    def dibujar(self, lienzo):
        self.dialogo = [[(self.rotulo, None)],
                        [("Flechas: cambiar   Espacio: repetir   F: fase del jefe   Escape: salir", colores["textoSuave"])]]
        super().dibujar(lienzo)


def abrir():
    import juego as moduloJuego
    juego = moduloJuego.Juego()
    lista, k, fase2 = catalogo(), 0, False
    escena, falta = None, 0.0

    def poner():
        nonlocal escena, falta
        quien = lista[k][0]
        nombres = equipos[0] if quien == "Jefe" or quien in equipos[0] else equipos[1]
        escena = EscenaGaleria(juego, nombres, fase2)
        juego.escena = escena
        falta = escena.reproducir(*lista[k]) + 0.6

    poner()
    reloj = pygame.time.Clock()
    while True:
        dt = reloj.tick(60) / 1000
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT or (evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE):
                return
            if evento.type == pygame.KEYDOWN:
                if evento.key in (pygame.K_RIGHT, pygame.K_LEFT):
                    k = (k + (1 if evento.key == pygame.K_RIGHT else -1)) % len(lista)
                elif evento.key == pygame.K_f:
                    fase2 = not fase2
                poner()
        falta -= dt
        if falta <= 0:
            poner()
        escena.actualizar(dt)
        escena.dibujar(juego.lienzo)
        pygame.display.flip()


if __name__ == "__main__":
    abrir()
