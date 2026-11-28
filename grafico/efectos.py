# Los números que flotan sobre los personajes: daño, curación, esquivas y
# bloqueos. La animación de cada ataque vive en grafico/recetas.py; aquí solo
# se decide qué número sale sobre quién y en qué momento.
from grafico.interfaz import colores, dibujarTexto
from grafico.recursos import reproducirSonido

duracionNumero = 1.0


class NumeroFlotante:

    def __init__(self, texto, pos, color, retraso=0.0, sonido=None, tamano=34):
        self.texto, self.pos, self.color = texto, pos, color
        self.tiempo = -retraso
        self.sonido, self.tamano = sonido, tamano

    def actualizar(self, dt):
        self.tiempo += dt
        # El sonido va con el numero, cuando el golpe llega, y no cuando se lanza.
        if self.sonido is not None and self.tiempo >= 0:
            reproducirSonido(self.sonido)
            self.sonido = None
        return self.tiempo < duracionNumero

    def dibujar(self, lienzo):
        if self.tiempo < 0:
            return
        # Sale con un brinco y luego sube despacio.
        brinco = 14 * max(0.0, 1 - self.tiempo / 0.18)
        subida = 40 * self.tiempo / duracionNumero
        dibujarTexto(lienzo, self.texto, (self.pos[0], int(self.pos[1] - subida - brinco)), self.tamano, self.color,
                     centrado=True, contorno=True)


def numerosDeTurno(ev, posicionDe, llegada=0.0):
    # Convierte un turno del registro del motor en los números que se ven.
    # posicionDe es una función que da el centro en pantalla de un personaje
    # y llegada es cuánto falta para que el golpe pegue.
    numeros = []
    for nombre, dano, nota in ev["golpes"]:
        destino = posicionDe(nombre)
        if nota == "esquiva":
            numeros.append(NumeroFlotante("esquiva", destino, colores["aviso"], llegada, "esquiva"))
        elif nota == "bloqueado":
            numeros.append(NumeroFlotante("bloqueado", destino, colores["aviso"], llegada))
        elif nota == "critico":
            numeros.append(NumeroFlotante("-%d critico" % dano, destino, colores["dano"], llegada, "critico", 42))
        else:
            numeros.append(NumeroFlotante("-%d" % dano, destino, colores["dano"], llegada, "golpe"))

    for k, (nombre, cantidad) in enumerate(ev["curas"]):
        numeros.append(NumeroFlotante("+%d" % cantidad, posicionDe(nombre), colores["cura"], llegada,
                                      "curacion" if k == 0 else None))
    return numeros
