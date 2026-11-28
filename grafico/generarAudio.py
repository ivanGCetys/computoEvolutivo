# Compone y sintetiza toda la musica y los efectos de sonido del juego, al
# estilo de las consolas de 8 y 16 bits: ondas cuadradas con distinto ancho de
# pulso, triangulo para el bajo y ruido para la bateria. Nada viene de un
# archivo ajeno; todo sale de las partituras y recetas de este archivo, asi
# que no hay licencias de por medio.
#
# Los archivos quedan en recursos/sonidos. Si en la computadora hay ffmpeg se
# guardan en ogg, que pesa mucho menos; si no, en wav. El juego busca los dos.
#
# Uso: python -m grafico.generarAudio            todo
#      python -m grafico.generarAudio musica     solo la musica
import math
import os
import shutil
import subprocess
import wave

import numpy as np

frecuencia = 22050
carpetaSonidos = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recursos", "sonidos")
azar = np.random.default_rng(7)

nombresNota = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def hz(nota):
    # "A4" son 440 Hz. Acepta sostenidos y bemoles: "C#5", "Bb3".
    letra, resto = nota[0], nota[1:]
    semitono = nombresNota[letra]
    while resto and resto[0] in "#b":
        semitono += 1 if resto[0] == "#" else -1
        resto = resto[1:]
    midi = 12 * (int(resto) + 1) + semitono
    return 440.0 * 2 ** ((midi - 69) / 12)


def tiempo(segundos):
    return np.arange(int(segundos * frecuencia)) / frecuencia


# Las ondas. fase va de 0 a 1 en cada ciclo.
def cuadrada(fase, pulso=0.5):
    return np.where((fase % 1.0) < pulso, 1.0, -1.0)


def triangulo(fase):
    f = fase % 1.0
    return 4 * np.abs(f - 0.5) - 1


def sierra(fase):
    return 2 * (fase % 1.0) - 1


def ruido(n, grueso=1):
    # El ruido de las consolas cambia de valor cada tantas muestras; entre
    # mas grueso, mas grave suena.
    base = azar.uniform(-1, 1, n // grueso + 2)
    return np.repeat(base, grueso)[:n]


def faseDe(frecuencias):
    # Integra una frecuencia que cambia en el tiempo para que no haya saltos.
    return np.cumsum(frecuencias) / frecuencia


def envolvente(n, ataque=0.005, caida=0.08, sosten=0.6, suelta=0.05):
    t = np.arange(n) / frecuencia
    dur = n / frecuencia
    e = np.ones(n) * sosten
    e = np.where(t < ataque, t / max(ataque, 1e-6), e)
    enCaida = (t >= ataque) & (t < ataque + caida)
    e = np.where(enCaida, 1 - (1 - sosten) * (t - ataque) / max(caida, 1e-6), e)
    fin = dur - suelta
    e = np.where(t > fin, e * np.clip((dur - t) / max(suelta, 1e-6), 0, 1), e)
    return e


def apagar(n, rapidez):
    return np.exp(-np.arange(n) / frecuencia * rapidez)


# Musica

def leerCompas(texto):
    # "E5.4 r.2 G5.2" es una lista de (nota, dieciseisavos).
    notas = []
    for ficha in texto.split():
        nota, dur = ficha.rsplit(".", 1)
        notas.append((None if nota == "r" else nota, int(dur)))
    if sum(d for _, d in notas) != 16:
        raise ValueError("el compas no suma 16: " + texto)
    return notas


def acorde(nombre, octava=3):
    # "Am7" son las notas del acorde en orden, empezando en la octava dada.
    raiz = nombre[0]
    resto = nombre[1:]
    if resto[:1] in ("#", "b"):
        raiz, resto = raiz + resto[0], resto[1:]
    intervalos = {"": (0, 4, 7), "m": (0, 3, 7), "7": (0, 4, 7, 10), "m7": (0, 3, 7, 10),
                  "maj7": (0, 4, 7, 11), "dim": (0, 3, 6), "sus4": (0, 5, 7)}[resto]
    base = hz(raiz + str(octava))
    return [base * 2 ** (i / 12) for i in intervalos]


class Pista:
    # Una cancion: se le van agregando voces y al final se mezclan.
    def __init__(self, bpm, compases):
        self.dieciseisavo = 60 / bpm / 4
        self.compases = compases
        self.muestras = int(round(compases * 16 * self.dieciseisavo * frecuencia))
        self.mezcla = np.zeros(self.muestras)

    def poner(self, inicio, sonido, volumen):
        i = int(round(inicio * frecuencia))
        if i >= self.muestras:
            return
        fin = min(self.muestras, i + len(sonido))
        self.mezcla[i:fin] += volumen * sonido[:fin - i]

    def melodia(self, compases, onda="cuadrada", pulso=0.25, volumen=0.16, vibrato=0.0, octava=0, ligado=0.85,
                eco=0.0, desde=0):
        t = desde * 16 * self.dieciseisavo
        for texto in compases:
            for nota, dur in leerCompas(texto):
                largo = dur * self.dieciseisavo
                if nota is not None:
                    f = hz(nota) * 2 ** octava
                    n = int(largo * ligado * frecuencia)
                    tt = np.arange(n) / frecuencia
                    # El vibrato entra despues de un momento, como en los temas de antes.
                    vib = 1 + vibrato * np.sin(2 * np.pi * 5.5 * tt) * np.clip((tt - 0.18) / 0.2, 0, 1)
                    fase = faseDe(f * vib)
                    if onda == "cuadrada":
                        s = cuadrada(fase, pulso)
                    elif onda == "triangulo":
                        s = triangulo(fase)
                    else:
                        s = 0.6 * cuadrada(fase, 0.5) + 0.4 * cuadrada(fase * 2, 0.25)
                    s = s * envolvente(n, 0.004, 0.12, 0.7, 0.03)
                    self.poner(t, s, volumen)
                    if eco:
                        self.poner(t + 3 * self.dieciseisavo, s, volumen * eco)
                t += largo

    def bajo(self, acordes, patron="corcheas", volumen=0.24, desde=0):
        # El bajo en triangulo sobre la raiz de cada acorde.
        t0 = desde * 16 * self.dieciseisavo
        for k, nombre in enumerate(acordes):
            raiz = acorde(nombre, 2)[0]
            quinta = acorde(nombre, 2)[2]
            inicio = t0 + k * 16 * self.dieciseisavo
            if patron == "corcheas":
                golpes = [(2 * j, 2, raiz * (2 if j % 2 else 1)) for j in range(8)]
            elif patron == "galope":
                golpes = []
                for j in range(4):
                    golpes += [(4 * j, 1, raiz), (4 * j + 1, 1, raiz), (4 * j + 2, 2, raiz * 2)]
            elif patron == "blancas":
                golpes = [(0, 8, raiz), (8, 8, quinta)]
            else:
                golpes = [(0, 6, raiz), (6, 2, raiz), (8, 4, quinta), (12, 4, raiz * 2)]
            for pos, dur, f in golpes:
                n = int(dur * self.dieciseisavo * 0.9 * frecuencia)
                s = triangulo(faseDe(np.full(n, f))) * envolvente(n, 0.003, 0.05, 0.85, 0.02)
                self.poner(inicio + pos * self.dieciseisavo, s, volumen)

    def arpegio(self, acordes, pulso=0.125, volumen=0.08, octava=4, figura=(0, 1, 2, 1), paso=1, desde=0, subida=True):
        t0 = desde * 16 * self.dieciseisavo
        for k, nombre in enumerate(acordes):
            notas = acorde(nombre, octava)
            notas = notas + [notas[0] * 2]
            for j in range(0, 16, paso):
                indice = figura[(j // paso) % len(figura)] % len(notas)
                f = notas[indice]
                n = int(paso * self.dieciseisavo * 0.8 * frecuencia)
                s = cuadrada(faseDe(np.full(n, f)), pulso) * envolvente(n, 0.002, 0.05, 0.5, 0.02)
                self.poner(t0 + (k * 16 + j) * self.dieciseisavo, s, volumen)

    def acordesLargos(self, acordes, volumen=0.05, octava=4, desde=0):
        # Un colchon de acorde con pulso fino, para los temas lentos.
        t0 = desde * 16 * self.dieciseisavo
        for k, nombre in enumerate(acordes):
            n = int(16 * self.dieciseisavo * frecuencia)
            s = np.zeros(n)
            for f in acorde(nombre, octava):
                s += cuadrada(faseDe(f * (1 + 0.003 * np.sin(np.arange(n) / frecuencia * 6))), 0.125)
            s *= envolvente(n, 0.15, 0.3, 0.7, 0.3)
            self.poner(t0 + k * 16 * self.dieciseisavo, s, volumen)

    def bateria(self, patron, compases, volumen=0.18, desde=0):
        # patron es un texto de 16 letras por instrumento: k bombo, s caja, h platillo, x nada.
        t0 = desde * 16 * self.dieciseisavo
        for c in range(compases):
            for instrumento, golpes in patron.items():
                for j, letra in enumerate(golpes):
                    if letra == "x":
                        continue
                    fuerte = 1.0 if letra.isupper() or letra == "o" else 0.7
                    self.poner(t0 + (c * 16 + j) * self.dieciseisavo, tambor(instrumento), volumen * fuerte)

    def final(self, normal=0.9):
        s = self.mezcla
        s = np.tanh(s * 1.3) / np.tanh(1.3)
        pico = np.max(np.abs(s)) or 1.0
        return s / pico * normal


tamboresHechos = {}


def tambor(tipo):
    if tipo not in tamboresHechos:
        if tipo == "k":
            n = int(0.16 * frecuencia)
            f = 120 * np.exp(-np.arange(n) / frecuencia * 28) + 45
            s = np.sin(2 * np.pi * faseDe(f)) * apagar(n, 22)
        elif tipo == "s":
            n = int(0.14 * frecuencia)
            s = (0.7 * ruido(n, 2) + 0.3 * triangulo(faseDe(np.full(n, 190)))) * apagar(n, 26)
        elif tipo == "h":
            n = int(0.05 * frecuencia)
            s = ruido(n, 1) * apagar(n, 80) * 0.6
        elif tipo == "t":
            # Timbal: un tono grave que cae, para los temas solemnes.
            n = int(0.5 * frecuencia)
            f = 95 * np.exp(-np.arange(n) / frecuencia * 3) + 55
            s = (np.sin(2 * np.pi * faseDe(f)) + 0.2 * ruido(n, 4)) * apagar(n, 7)
        else:
            n = int(0.6 * frecuencia)
            s = ruido(n, 1) * apagar(n, 6) * 0.7
        tamboresHechos[tipo] = s
    return tamboresHechos[tipo]


def temaTitulo():
    acordes = ["Dm", "Bb", "C", "Am", "Dm", "Gm", "A", "A", "Bb", "C", "Dm", "A", "Gm", "Dm", "A", "Dm"]
    melodia = ["A4.6 D5.2 E5.4 F5.4", "F5.6 E5.2 D5.4 F5.4", "E5.6 D5.2 C5.4 E5.4", "A4.12 r.4",
               "A4.6 D5.2 E5.4 F5.4", "G5.6 A5.2 Bb5.4 G5.4", "A5.6 G5.2 F5.2 E5.2 C#5.4", "E5.12 r.4",
               "D5.4 F5.4 Bb5.6 A5.2", "G5.4 E5.4 C5.6 E5.2", "F5.4 A5.4 D6.6 C6.2", "A5.12 G5.2 E5.2",
               "D5.4 G5.4 Bb5.6 A5.2", "A5.4 F5.4 D5.6 E5.2", "C#5.4 E5.4 A5.4 G5.4", "D5.12 r.4"]
    p = Pista(84, 16)
    p.melodia(melodia, "cuadrada", 0.25, 0.15, vibrato=0.006, eco=0.35)
    p.arpegio(acordes, 0.125, 0.055, 4, (0, 1, 2, 3, 2, 1), 1)
    p.acordesLargos(acordes, 0.035, 3)
    p.bajo(acordes, "blancas", 0.26)
    p.bateria({"t": "Oxxxxxxxoxxxxxxx", "h": "xxxxhxxxxxxxhxxx"}, 16, 0.2)
    return p.final()


def temaBatalla():
    acordes = ["Em", "C", "D", "B", "Em", "C", "D", "B", "Am", "Em", "C", "B", "Am", "C", "B", "B"]
    melodia = ["E5.3 E5.1 B4.2 E5.2 G5.4 F#5.4", "E5.3 E5.1 C5.2 E5.2 G5.2 A5.2 G5.4",
               "F#5.3 F#5.1 D5.2 F#5.2 A5.4 G5.2 F#5.2", "D#5.6 B4.2 F#5.8",
               "E5.3 E5.1 B4.2 E5.2 G5.4 B5.4", "C6.6 B5.2 A5.2 G5.2 E5.4",
               "F#5.2 G5.2 A5.4 D5.2 E5.2 F#5.4", "B4.4 D#5.4 F#5.4 A5.4",
               "A5.6 G5.2 E5.4 C5.4", "B4.6 E5.2 G5.4 B5.4", "C6.4 B5.4 G5.4 E5.4", "F#5.6 D#5.2 B4.8",
               "C5.2 E5.2 A5.4 G5.2 A5.2 B5.4", "C6.4 B5.2 A5.2 G5.4 E5.4", "D#5.4 F#5.4 B5.4 A5.4", "F#5.4 D#5.4 B4.8"]
    p = Pista(150, 32)
    for vuelta in (0, 16):
        p.melodia(melodia, "cuadrada", 0.25 if vuelta == 0 else 0.5, 0.14, vibrato=0.004, desde=vuelta)
        p.arpegio(acordes, 0.125, 0.06, 4, (0, 2, 1, 2), 2, desde=vuelta)
        p.bajo(acordes, "corcheas", 0.25, desde=vuelta)
    p.melodia(melodia[8:], "cuadrada", 0.125, 0.06, octava=-1, desde=24)
    p.bateria({"k": "oxxxxxkxoxxkxxxx", "s": "xxxxsxxxxxxxsxxx", "h": "hxhxhxhxhxhxhxhx"}, 32, 0.17)
    return p.final()


def temaBatalla2():
    acordes = ["Cm", "Ab", "Bb", "G", "Cm", "Ab", "Bb", "G", "Fm", "Cm", "Ab", "G", "Fm", "Ab", "G", "G"]
    melodia = ["C5.2 Eb5.2 G5.2 C6.6 Bb5.2 G5.2", "Ab5.6 G5.2 Eb5.4 C5.4", "D5.2 F5.2 Bb5.2 D6.6 C6.2 Bb5.2",
               "B5.6 G5.2 D5.4 F5.4", "Eb5.2 G5.2 C6.2 Eb6.6 D6.2 C6.2", "C6.6 Bb5.2 Ab5.4 Eb5.4",
               "F5.2 Bb5.2 D6.2 F6.6 Eb6.2 D6.2", "D6.8 B5.4 G5.4", "Ab5.4 F5.4 C6.6 Ab5.2",
               "G5.4 Eb5.4 C5.6 Eb5.2", "F5.4 Ab5.4 C6.4 Eb6.4", "D6.6 C6.2 B5.4 G5.4",
               "C6.2 Ab5.2 F5.2 Ab5.2 C6.4 F6.4", "Eb6.4 C6.4 Ab5.4 C6.4", "B5.4 D6.4 G6.4 F6.4", "D6.4 B5.4 G5.8"]
    p = Pista(168, 32)
    for vuelta in (0, 16):
        p.melodia(melodia, "organo", 0.5, 0.13, vibrato=0.005, desde=vuelta)
        p.arpegio(acordes, 0.25, 0.055, 4, (0, 1, 2, 3, 2, 1, 0, 1), 1, desde=vuelta)
        p.bajo(acordes, "galope", 0.26, desde=vuelta)
    p.melodia(melodia, "cuadrada", 0.125, 0.05, octava=-1, desde=16)
    p.bateria({"k": "oxxkoxxxoxxkoxkx", "s": "xxxxsxxsxxxxsxxs", "h": "hhhhhhhhhhhhhhhh"}, 32, 0.15)
    return p.final()


def temaVictoria():
    fanfarria = ["G4.2 B4.2 D5.2 G5.6 r.2 D5.2", "C5.2 E5.2 G5.2 C6.4 D6.2 B5.4", "G5.12 r.4"]
    acordesFanfarria = ["G", "C", "G"]
    acordes = ["G", "C", "D", "G", "Em", "C", "D", "G"]
    tema = ["B4.4 D5.4 G5.4 F#5.2 G5.2", "E5.4 G5.4 C6.4 B5.2 A5.2", "F#5.4 A5.4 D6.4 C6.2 A5.2", "B5.8 G5.4 D5.4",
            "E5.4 G5.4 B5.4 A5.2 G5.2", "A5.4 G5.4 E5.4 C5.4", "D5.4 F#5.4 A5.4 C6.4", "B5.8 G5.8"]
    p = Pista(132, 3 + 16)
    p.melodia(fanfarria, "organo", 0.5, 0.16, vibrato=0.006)
    p.melodia(fanfarria, "cuadrada", 0.25, 0.07, octava=-1)
    p.arpegio(acordesFanfarria, 0.125, 0.06, 4, (0, 1, 2, 3), 1)
    p.bajo(acordesFanfarria, "blancas", 0.25)
    p.bateria({"t": "OxxxxxxxOxxxOxOx"}, 3, 0.2)
    for vuelta in (3, 11):
        p.melodia(tema, "cuadrada", 0.25, 0.14, vibrato=0.004, desde=vuelta)
        p.arpegio(acordes, 0.125, 0.055, 4, (0, 2, 1, 2), 2, desde=vuelta)
        p.bajo(acordes, "marcha", 0.24, desde=vuelta)
        p.bateria({"k": "oxxxxxxxoxxxxxxx", "s": "xxxxsxxxxxxxsxxx", "h": "xxhxxxhxxxhxxxhx"}, 8, 0.14, desde=vuelta)
    return p.final()


def temaDerrota():
    acordes = ["Am", "F", "C", "E", "Am", "Dm", "E", "Am"]
    melodia = ["E5.8 C5.4 A4.4", "F5.8 E5.4 C5.4", "G4.8 C5.4 E5.4", "D5.8 B4.4 G#4.4",
               "A4.8 C5.4 E5.4", "F5.8 D5.4 A4.4", "G#4.4 B4.4 E5.4 D5.4", "A4.16"]
    p = Pista(66, 8)
    p.melodia(melodia, "triangulo", 0.5, 0.22, vibrato=0.008, ligado=0.95, eco=0.4)
    p.acordesLargos(acordes, 0.04, 3)
    p.bajo(acordes, "blancas", 0.22)
    return p.final(0.8)


def temaEntrenamiento():
    acordes = ["Am7", "D7", "Fmaj7", "Em7", "Am7", "D7", "Fmaj7", "Em7", "Dm7", "G", "Cmaj7", "E", "Am7", "D7", "Fmaj7", "Em7"]
    melodia = ["E5.8 r.4 A5.4", "F#5.8 r.4 D5.4", "E5.8 r.4 C5.4", "B4.12 r.4",
               "E5.8 r.4 A5.4", "F#5.8 A5.4 C6.4", "B5.8 A5.4 G5.4", "E5.12 r.4",
               "F5.8 r.4 D5.4", "D5.8 r.4 B4.4", "C5.8 E5.4 G5.4", "G#5.12 r.4",
               "E5.8 r.4 A5.4", "F#5.8 r.4 D5.4", "E5.8 r.4 C5.4", "B4.12 r.4"]
    p = Pista(112, 16)
    p.arpegio(acordes, 0.25, 0.07, 4, (0, 1, 2, 3, 4, 3, 2, 1), 1)
    p.arpegio(acordes, 0.125, 0.035, 5, (3, 2, 1, 0), 2)
    p.melodia(melodia, "triangulo", 0.5, 0.2, vibrato=0.006, eco=0.4)
    p.bajo(acordes, "marcha", 0.22)
    p.bateria({"k": "oxxxxxxxoxxxxxxx", "h": "xxhxxxhxxxhxxxhx", "s": "xxxxxxxxxxxxsxxx"}, 16, 0.12)
    return p.final()


# Efectos

def barrido(f0, f1, dur, onda="cuadrada", pulso=0.5, curva=1.0):
    n = int(dur * frecuencia)
    u = np.linspace(0, 1, n) ** curva
    f = f0 * (f1 / f0) ** u
    fase = faseDe(f)
    if onda == "cuadrada":
        return cuadrada(fase, pulso)
    if onda == "triangulo":
        return triangulo(fase)
    if onda == "seno":
        return np.sin(2 * np.pi * fase)
    return sierra(fase)


def pasaBajos(s, corte):
    # Un filtro de un polo, suficiente para quitarle lo chillon al ruido.
    a = math.exp(-2 * math.pi * corte / frecuencia)
    salida = np.empty_like(s)
    y = 0.0
    for k in range(len(s)):
        y = (1 - a) * s[k] + a * y
        salida[k] = y
    return salida


def pasaBajosVariable(s, cortes):
    salida = np.empty_like(s)
    y = 0.0
    for k in range(len(s)):
        a = math.exp(-2 * math.pi * cortes[k] / frecuencia)
        y = (1 - a) * s[k] + a * y
        salida[k] = y
    return salida


def resonador(s, centro, ancho):
    # Un filtro de dos polos que deja pasar una banda: con tres de ellos se
    # arma una vocal, porque eso son los formantes de la voz.
    r = math.exp(-math.pi * ancho / frecuencia)
    c = 2 * r * math.cos(2 * math.pi * centro / frecuencia)
    salida = np.empty_like(s)
    y1 = y2 = 0.0
    for k in range(len(s)):
        y = (1 - r) * s[k] + c * y1 - r * r * y2
        salida[k] = y
        y2, y1 = y1, y
    return salida


def reverberacion(s, cola=0.6, mezcla=0.3):
    n = int(cola * frecuencia)
    respuesta = azar.uniform(-1, 1, n) * np.exp(-np.arange(n) / frecuencia * 6 / cola)
    respuesta[0] = 0
    largo = len(s) + n
    tam = 1 << (largo - 1).bit_length()
    humedo = np.fft.irfft(np.fft.rfft(s, tam) * np.fft.rfft(respuesta, tam), tam)[:largo]
    humedo /= (np.max(np.abs(humedo)) or 1)
    seco = np.concatenate([s, np.zeros(n)])
    return seco * (1 - mezcla) + humedo * mezcla * (np.max(np.abs(s)) or 1)


# Las vocales: frecuencias y anchos de sus tres formantes.
vocales = {"a": ((800, 80), (1200, 90), (2600, 120)), "e": ((450, 70), (1900, 100), (2600, 120)),
           "o": ((500, 70), (850, 80), (2500, 120)), "u": ((330, 60), (750, 80), (2400, 120)),
           "aa": ((700, 110), (1100, 120), (2500, 160))}


def voz(tono, dur, vocal="a", aspiracion=0.06, aspereza=0.0, curva=None, jitter=0.01, quiebre=0.0):
    # Una voz sintetizada: una serie de pulsos con el tono dado, pasada por
    # los formantes de la vocal. tono puede ser un numero o una funcion de u.
    n = int(dur * frecuencia)
    u = np.linspace(0, 1, n)
    f = tono(u) if callable(tono) else np.full(n, float(tono))
    f = f * (1 + jitter * pasaBajos(azar.normal(0, 1, n), 30) * 8)
    fase = faseDe(f)
    glotis = sierra(fase) * 0.6 + cuadrada(fase, 0.3) * 0.4
    if quiebre:
        glotis += quiebre * cuadrada(fase * 0.5, 0.5)
    if aspereza:
        glotis = glotis + aspereza * ruido(n, 1) * (0.5 + 0.5 * np.sin(2 * np.pi * fase * 0.5))
    s = np.zeros(n)
    for k, (centro, ancho) in enumerate(vocales[vocal]):
        s += resonador(glotis, centro, ancho) * (1.0, 0.6, 0.25)[k]
    s = s / (np.max(np.abs(s)) or 1)
    # La h del principio: un soplo de ruido antes de la vocal.
    soplo = resonador(ruido(n, 1), vocales[vocal][1][0], 400) * np.exp(-u * dur / 0.06) * aspiracion * 8
    return s + soplo


def unirCon(*pedazos):
    largo = max(int(t * frecuencia) + len(s) for t, s, _ in pedazos)
    salida = np.zeros(largo)
    for t, s, vol in pedazos:
        i = int(t * frecuencia)
        salida[i:i + len(s)] += vol * s
    return salida


def normalizar(s, nivel=0.9):
    return s / (np.max(np.abs(s)) or 1) * nivel


def grito(tono, vocal="a", dur=0.32, aspereza=0.0, caida=0.35, subida=0.12, aspiracion=0.08, quiebre=0.0):
    # Los gritos cortos de los heroes al atacar: suben un poco y caen.
    def curvaTono(u):
        return tono * (1 + subida * np.sin(np.pi * np.clip(u * 3, 0, 1)) - caida * u * u)
    n = int(dur * frecuencia)
    s = voz(curvaTono, dur, vocal, aspiracion, aspereza, quiebre=quiebre)
    s *= envolvente(n, 0.015, 0.08, 0.75, dur * 0.4)
    return normalizar(reverberacion(s, 0.25, 0.15), 0.8)


def rugido(dur=1.2, tono=70, vocal="aa", sube=0.25, eco=True):
    def curvaTono(u):
        return tono * (1 + sube * np.sin(np.pi * u) - 0.15 * u)
    n = int(dur * frecuencia)
    capas = voz(curvaTono, dur, vocal, 0.1, 0.45, jitter=0.04, quiebre=0.6)
    capas += 0.6 * voz(lambda u: curvaTono(u) * 1.505, dur, "o", 0.05, 0.3, jitter=0.05)
    capas += 0.25 * pasaBajos(ruido(n, 2), 900)
    s = np.tanh(capas * 2.5) * envolvente(n, 0.06, 0.2, 0.85, dur * 0.35)
    sub = np.sin(2 * np.pi * faseDe(curvaTono(np.linspace(0, 1, n)) / 2)) * envolvente(n, 0.05, 0.2, 0.8, dur * 0.3)
    s = s + 0.5 * sub
    return normalizar(reverberacion(s, 0.9, 0.3) if eco else s, 0.95)


def efectos():
    e = {}
    n = lambda d: int(d * frecuencia)

    # Interfaz
    e["cursor"] = normalizar(cuadrada(faseDe(np.full(n(0.035), 1320)), 0.5) * apagar(n(0.035), 60), 0.35)
    e["aceptar"] = normalizar(np.concatenate([cuadrada(faseDe(np.full(n(0.05), 880)), 0.25),
                                              cuadrada(faseDe(np.full(n(0.08), 1320)), 0.25) * apagar(n(0.08), 30)]), 0.4)
    e["cancelar"] = normalizar(barrido(700, 300, 0.12, "cuadrada", 0.25) * apagar(n(0.12), 18), 0.4)
    e["error"] = normalizar(cuadrada(faseDe(np.full(n(0.16), 140)), 0.5) * envolvente(n(0.16), 0.002, 0.02, 0.8, 0.03), 0.4)
    e["pausa"] = normalizar(unirCon((0, barrido(600, 600, 0.06, "cuadrada", 0.25), 1), (0.07, barrido(900, 900, 0.1, "cuadrada", 0.25) * apagar(n(0.1), 20), 1)), 0.4)

    # Golpes
    e["golpe"] = normalizar(unirCon((0, pasaBajos(ruido(n(0.14), 2), 1800) * apagar(n(0.14), 30), 1),
                                    (0, barrido(160, 60, 0.12, "seno") * apagar(n(0.12), 25), 1.2)), 0.85)
    e["critico"] = normalizar(unirCon((0, e["golpe"], 1), (0.0, barrido(2200, 900, 0.18, "cuadrada", 0.25) * apagar(n(0.18), 16), 0.5),
                                      (0.04, ruido(n(0.25), 1) * apagar(n(0.25), 14), 0.4)), 0.95)
    e["tajo"] = normalizar(pasaBajosVariable(ruido(n(0.2), 1), np.linspace(1500, 7000, n(0.2))) * np.sin(np.linspace(0, np.pi, n(0.2))) ** 2, 0.7)
    e["espadazo"] = normalizar(unirCon((0, e["tajo"], 1), (0.1, barrido(3000, 2400, 0.3, "cuadrada", 0.5) * apagar(n(0.3), 14), 0.25),
                                       (0.1, e["golpe"], 0.8)), 0.9)
    e["golpeSeco"] = normalizar(unirCon((0, barrido(220, 50, 0.22, "seno") * apagar(n(0.22), 14), 1.4),
                                        (0, pasaBajos(ruido(n(0.2), 3), 900) * apagar(n(0.2), 18), 1)), 0.9)
    e["esquiva"] = normalizar(pasaBajosVariable(ruido(n(0.18), 1), np.linspace(5000, 900, n(0.18))) * np.sin(np.linspace(0, np.pi, n(0.18))), 0.55)
    e["bloqueo"] = normalizar(unirCon((0, barrido(1800, 1700, 0.35, "cuadrada", 0.5) * apagar(n(0.35), 12), 0.6),
                                      (0, barrido(2700, 2650, 0.35, "cuadrada", 0.25) * apagar(n(0.35), 16), 0.4),
                                      (0, ruido(n(0.05), 1) * apagar(n(0.05), 60), 0.8)), 0.6)
    e["escudo"] = normalizar(unirCon(*[(0.05 * k, barrido(f, f, 0.25, "triangulo") * apagar(n(0.25), 10), 0.6)
                                       for k, f in enumerate((660, 880, 1100, 1320))]), 0.55)
    e["curacion"] = normalizar(unirCon(*[(0.07 * k, barrido(f, f * 1.01, 0.35, "triangulo") * apagar(n(0.35), 8), 0.7)
                                         for k, f in enumerate((784, 988, 1175, 1568))]), 0.6)
    e["pocion"] = normalizar(unirCon(*[(0.06 * k, barrido(300 + 90 * k, 900 + 120 * k, 0.07, "seno") * apagar(n(0.07), 30), 0.8)
                                       for k in range(6)]), 0.6)
    e["furia"] = normalizar(unirCon((0, barrido(80, 300, 0.5, "cuadrada", 0.5, 2) * envolvente(n(0.5), 0.05, 0.1, 0.8, 0.15), 0.6),
                                    (0, pasaBajosVariable(ruido(n(0.6), 2), np.linspace(400, 3000, n(0.6))) * apagar(n(0.6), 4), 0.7)), 0.8)
    e["caida"] = normalizar(unirCon((0, barrido(400, 90, 0.35, "cuadrada", 0.5) * apagar(n(0.35), 7), 0.6),
                                    (0.25, e["golpeSeco"], 0.8)), 0.8)
    e["carga"] = normalizar(barrido(110, 880, 1.0, "cuadrada", 0.25, 1.5) * np.linspace(0.2, 1, n(1.0))
                            * (0.7 + 0.3 * cuadrada(faseDe(np.full(n(1.0), 14)))), 0.55)
    e["lanzar"] = normalizar(barrido(300, 1600, 0.18, "cuadrada", 0.125, 0.6) * apagar(n(0.18), 10), 0.45)

    # Elementos
    e["fuego"] = normalizar(unirCon((0, pasaBajos(ruido(n(0.6), 2), 1400) * envolvente(n(0.6), 0.03, 0.1, 0.7, 0.3), 1),
                                    (0, ruido(n(0.6), 1) * (azar.uniform(0, 1, n(0.6)) > 0.996) * 4, 0.6)), 0.8)
    e["agua"] = normalizar(unirCon(*([(0, pasaBajosVariable(ruido(n(0.45), 1), np.linspace(3000, 600, n(0.45))) * apagar(n(0.45), 6), 1)]
                                     + [(0.03 * k + 0.02, barrido(500 + 200 * k, 1400 + 300 * k, 0.05, "seno") * apagar(n(0.05), 40), 0.5) for k in range(5)])), 0.8)
    e["viento"] = normalizar(pasaBajosVariable(ruido(n(0.6), 1), 600 + 2500 * np.sin(np.linspace(0, np.pi, n(0.6)))) * np.sin(np.linspace(0, np.pi, n(0.6))), 0.75)
    e["tierra"] = normalizar(unirCon((0, pasaBajos(ruido(n(0.7), 6), 300) * apagar(n(0.7), 5), 1.4),
                                     (0, ruido(n(0.08), 1) * apagar(n(0.08), 40), 0.7),
                                     (0, barrido(90, 40, 0.5, "seno") * apagar(n(0.5), 6), 1)), 0.9)
    e["planta"] = normalizar(unirCon(*[(0.04 * k, pasaBajosVariable(ruido(n(0.12), 1), np.linspace(4000, 1500, n(0.12))) * apagar(n(0.12), 25), 0.7)
                                       for k in range(7)]), 0.6)
    rayo = ruido(n(0.45), 1) * (cuadrada(faseDe(np.full(n(0.45), 60)), 0.3) * 0.5 + 0.5)
    e["rayo"] = normalizar(unirCon((0, rayo * apagar(n(0.45), 8), 1), (0, barrido(2400, 300, 0.3, "sierra") * apagar(n(0.3), 10), 0.5)), 0.85)
    e["luz"] = normalizar(unirCon(*[(0.05 * k, barrido(f, f, 0.6, "triangulo") * apagar(n(0.6), 5) * (1 + 0.3 * np.sin(np.arange(n(0.6)) / frecuencia * 40)), 0.5)
                                    for k, f in enumerate((1047, 1319, 1568, 2093, 2637))]), 0.6)
    e["oscuridad"] = normalizar(unirCon((0, barrido(220, 55, 0.8, "sierra") * envolvente(n(0.8), 0.05, 0.1, 0.8, 0.3)
                                         * (0.6 + 0.4 * np.sin(np.arange(n(0.8)) / frecuencia * 2 * np.pi * 9)), 0.8),
                                        (0, pasaBajos(ruido(n(0.8), 3), 500) * apagar(n(0.8), 3), 0.6)), 0.8)
    e["magia"] = normalizar(unirCon(*[(0.03 * k, barrido(f, f * 2, 0.15, "cuadrada", 0.25) * apagar(n(0.15), 14), 0.5)
                                      for k, f in enumerate((523, 659, 784, 1047))]), 0.55)

    # Lo grande
    e["explosion"] = normalizar(unirCon((0, pasaBajosVariable(ruido(n(1.2), 2), np.linspace(2500, 200, n(1.2))) * apagar(n(1.2), 3.5), 1.3),
                                        (0, barrido(120, 30, 0.8, "seno") * apagar(n(0.8), 4), 1.2)), 0.95)
    e["meteoro"] = normalizar(barrido(2200, 300, 0.5, "seno", curva=1.4) * np.linspace(0.3, 1, n(0.5))
                              + pasaBajos(ruido(n(0.5), 1), 2000) * np.linspace(0.1, 0.6, n(0.5)), 0.6)
    e["trueno"] = normalizar(unirCon((0, ruido(n(0.1), 1) * apagar(n(0.1), 30), 1.2),
                                     (0.05, pasaBajos(ruido(n(1.6), 3), 400) * apagar(n(1.6), 2.5) * (0.7 + 0.3 * np.sin(np.arange(n(1.6)) / frecuencia * 2 * np.pi * 7)), 1.5)), 0.95)
    e["temblor"] = normalizar(pasaBajos(ruido(n(1.4), 8), 160) * envolvente(n(1.4), 0.1, 0.2, 0.9, 0.5), 0.9)
    e["destello"] = normalizar(unirCon((0, barrido(800, 3200, 0.25, "triangulo") * apagar(n(0.25), 8), 0.6),
                                       (0, ruido(n(0.4), 1) * apagar(n(0.4), 9), 0.5)), 0.7)
    e["ola"] = normalizar(pasaBajosVariable(ruido(n(1.2), 2), 300 + 1800 * np.sin(np.linspace(0, np.pi, n(1.2)))) * np.sin(np.linspace(0, np.pi, n(1.2))), 0.85)
    e["haz"] = normalizar(unirCon((0, barrido(150, 150, 1.0, "sierra") * (0.6 + 0.4 * cuadrada(faseDe(np.full(n(1.0), 30)))) * envolvente(n(1.0), 0.02, 0.1, 0.8, 0.3), 0.6),
                                  (0, ruido(n(1.0), 1) * envolvente(n(1.0), 0.02, 0.1, 0.6, 0.3), 0.4)), 0.85)
    e["cambio_de_fase"] = normalizar(unirCon((0, e["explosion"], 1), (0, e["destello"], 0.8)), 0.95)
    e["rueda"] = normalizar(unirCon((0, barrido(300, 120, 0.12, "cuadrada", 0.5) * apagar(n(0.12), 25), 0.8),
                                    (0, pasaBajos(ruido(n(0.15), 3), 700) * apagar(n(0.15), 20), 0.8),
                                    (0, barrido(1900, 1850, 0.25, "triangulo") * apagar(n(0.25), 14), 0.25)), 0.85)
    e["zumbido"] = normalizar(barrido(55, 55, 4.0, "sierra") * (0.7 + 0.3 * np.sin(np.arange(n(4.0)) / frecuencia * 2 * np.pi * 0.7))
                              + 0.4 * pasaBajos(ruido(n(4.0), 4), 200), 0.6)
    # El sonido de entrada al combate: un barrido que sube y un golpe.
    e["encuentro"] = normalizar(unirCon((0, barrido(200, 1800, 0.45, "cuadrada", 0.25, 1.5) * np.linspace(0.3, 1, n(0.45)), 0.5),
                                        (0, pasaBajosVariable(ruido(n(0.5), 1), np.linspace(500, 6000, n(0.5))) * np.linspace(0.1, 1, n(0.5)), 0.5),
                                        (0.45, barrido(140, 45, 0.5, "seno") * apagar(n(0.5), 6), 1.2),
                                        (0.45, ruido(n(0.3), 2) * apagar(n(0.3), 12), 0.6)), 0.9)
    # La rueda acelerando: un zumbido que sube de tono y tiembla cada vez mas rapido.
    dur = 4.5
    u = np.linspace(0, 1, n(dur))
    f = 70 * (9 ** (u ** 1.6))
    temblor = 0.65 + 0.35 * np.sin(2 * np.pi * faseDe(4 + 40 * u ** 2))
    giro = (0.5 * sierra(faseDe(f)) + 0.35 * cuadrada(faseDe(f * 1.5), 0.25) + 0.25 * pasaBajosVariable(ruido(n(dur), 1), 300 + 3000 * u))
    e["giro_rapido"] = normalizar(giro * temblor * np.clip(u * 4, 0, 1) * (0.5 + 0.5 * u), 0.75)
    e["victoria"] = normalizar(unirCon(*[(0.09 * k, barrido(f, f, 0.2, "cuadrada", 0.25) * apagar(n(0.2), 8), 0.6)
                                         for k, f in enumerate((523, 659, 784, 1047))]), 0.5)
    e["derrota"] = normalizar(unirCon(*[(0.18 * k, barrido(f, f * 0.97, 0.3, "triangulo") * apagar(n(0.3), 5), 0.7)
                                        for k, f in enumerate((440, 392, 349, 262))]), 0.6)

    # Voces de los heroes al pegar, dos por clase para que no suene siempre igual.
    e["grito_guerrero1"] = grito(150, "a", 0.3)
    e["grito_guerrero2"] = grito(140, "aa", 0.36, subida=0.2)
    e["grito_tanque1"] = grito(105, "o", 0.34, aspereza=0.25)
    e["grito_tanque2"] = grito(100, "aa", 0.4, aspereza=0.3, subida=0.2)
    e["grito_mago1"] = grito(130, "e", 0.28, caida=0.2)
    e["grito_mago2"] = grito(125, "a", 0.3)
    e["grito_clerigo1"] = grito(290, "a", 0.28)
    e["grito_clerigo2"] = grito(310, "e", 0.3, subida=0.2)
    e["grito_picaro1"] = grito(175, "e", 0.2, caida=0.5, aspiracion=0.2)
    e["grito_picaro2"] = grito(165, "a", 0.22, aspiracion=0.2)
    e["grito_berserker1"] = grito(110, "aa", 0.48, aspereza=0.5, subida=0.3, quiebre=0.3)
    e["grito_berserker2"] = grito(115, "a", 0.42, aspereza=0.45, subida=0.25, quiebre=0.3)
    e["dolor_heroe"] = grito(170, "u", 0.25, caida=0.5, aspiracion=0.15)
    e["dolor_heroina"] = grito(320, "u", 0.25, caida=0.5, aspiracion=0.15)

    # El jefe
    e["jefe_rugido"] = rugido(1.1, 72, "aa", 0.25)
    e["jefe_golpe"] = rugido(0.5, 85, "o", 0.35)
    e["jefe_dolor"] = rugido(0.45, 95, "u", -0.2)
    e["jefe_risa"] = normalizar(reverberacion(np.concatenate([rugido(0.17, 92 - 4 * k, "a", 0.1, False) for k in range(5)]), 0.9, 0.3), 0.85)
    e["jefe_grito"] = gritoTransformacion()
    e["jefe_muerte"] = normalizar(unirCon((0, rugido(2.2, 80, "aa", -0.45), 1), (0.4, e["explosion"], 0.6)), 0.95)
    return e


def gritoTransformacion():
    # El grito de la segunda fase: varias voces graves que suben y tiemblan,
    # con mucha distorsion y eco, como si retumbara toda la arena.
    dur = 3.0
    n = int(dur * frecuencia)

    def curva(u):
        return 70 * (1 + 1.4 * np.clip(u / 0.35, 0, 1) ** 0.6 - 0.5 * np.clip((u - 0.7) / 0.3, 0, 1)) * (1 + 0.05 * np.sin(u * 60))
    capas = np.zeros(n)
    for desvio, vocal, vol in ((1.0, "aa", 1.0), (1.007, "a", 0.8), (0.5, "o", 0.6), (1.5, "aa", 0.45), (2.01, "e", 0.25)):
        capas += vol * voz(lambda u: curva(u) * desvio, dur, vocal, 0.1, 0.5, jitter=0.05, quiebre=0.5)
    capas += 0.3 * pasaBajos(ruido(n, 1), 2500)
    s = np.tanh(capas * 3) * envolvente(n, 0.2, 0.3, 0.9, 0.8)
    return normalizar(reverberacion(s, 1.6, 0.4), 0.95)


def guardar(nombre, s, usarOgg):
    datos = (np.clip(s, -1, 1) * 32767).astype("<i2")
    ruta = os.path.join(carpetaSonidos, nombre + ".wav")
    with wave.open(ruta, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(frecuencia)
        w.writeframes(datos.tobytes())
    if usarOgg:
        ogg = ruta[:-4] + ".ogg"
        calidad = "3" if len(s) > frecuencia * 8 else "4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", ruta, "-c:a", "libvorbis", "-q:a", calidad, ogg], check=True)
        os.remove(ruta)


def guardarEstereo(nombre, s, usarOgg):
    # La musica tocada con FluidSynth sale en estereo y a 44100.
    from grafico.componerMusica import frecuenciaMusica
    datos = (np.clip(s, -1, 1) * 32767).astype("<i2")
    ruta = os.path.join(carpetaSonidos, nombre + ".wav")
    with wave.open(ruta, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(frecuenciaMusica)
        w.writeframes(datos.tobytes())
    if usarOgg:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", ruta, "-c:a", "libvorbis", "-q:a", "4",
                        ruta[:-4] + ".ogg"], check=True)
        os.remove(ruta)


# La pantalla de equipo y los combates se tocan con instrumentos si hay
# FluidSynth (ver componerMusica.py); si no, salen con ondas puras.
musica = {"titulo": temaTitulo, "seleccion": temaTitulo, "batalla": temaBatalla, "batalla2": temaBatalla2,
          "victoria": temaVictoria, "derrota": temaDerrota, "entrenamiento": temaEntrenamiento}


def generarTodo(soloEfectos=False, soloMusica=False):
    from grafico import componerMusica
    os.makedirs(os.path.join(carpetaSonidos, "musica"), exist_ok=True)
    usarOgg = shutil.which("ffmpeg") is not None
    if not soloMusica:
        for nombre, s in efectos().items():
            guardar(nombre, s, usarOgg)
    if not soloEfectos:
        conInstrumentos = componerMusica.disponible()
        for nombre, componer in musica.items():
            if conInstrumentos and nombre in componerMusica.temas:
                guardarEstereo(os.path.join("musica", nombre), componerMusica.temas[nombre](), usarOgg)
            else:
                guardar(os.path.join("musica", nombre), componer(), usarOgg)


if __name__ == "__main__":
    import sys
    generarTodo("efectos" in sys.argv, "musica" in sys.argv)
