# La musica con instrumentos de verdad: la pantalla de equipo y los dos
# combates contra el jefe. Las partituras se escriben aqui como MIDI y se
# tocan con FluidSynth, un sintetizador libre que usa bancos de sonidos
# (soundfonts). Es la misma idea que el soundtrack de Undertale: ondas
# cuadradas de consola mezcladas con bajo, cuerdas, coros y bateria de un
# banco General MIDI gratuito.
#
# Hace falta el programa fluidsynth y un banco .sf2. Con FluidR3_GM, que es
# libre (licencia MIT), en Ubuntu es: apt install fluidsynth fluid-soundfont-gm
# Si no se encuentran, generarAudio.py usa los temas de ondas puras de antes.
# El juego no los necesita: solo usa los ogg que quedan en recursos/sonidos.
import os
import shutil
import struct
import subprocess
import tempfile
import wave

import numpy as np

frecuenciaMusica = 44100
ticksPorNegra = 480
ticksPorDieciseisavo = ticksPorNegra // 4

bancosConocidos = ["/usr/share/sounds/sf2/FluidR3_GM.sf2", "/usr/share/soundfonts/FluidR3_GM.sf2",
                   "/usr/share/sounds/sf2/default-GM.sf2", "/usr/share/soundfonts/default.sf2"]

nombresNota = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# Programas de General MIDI que se usan, contando desde 0.
piano, cajaDeMusica, cuerdas, cuerdasLentas, coro, golpeDeOrquesta = 0, 10, 48, 49, 52, 55
timbales, campanas, guitarraDistorsionada, bajoDedos, bajoSinte, bajoSinte2 = 47, 14, 30, 33, 38, 39
leadCuadrada, leadSierra, colchonCalido, flauta = 80, 81, 89, 73
organo, contrabajo, cuerdasTremolo, trombon, cornos, metales = 19, 43, 44, 57, 60, 61

# Bateria del canal 10: una letra por pieza.
piezas = {"k": 36, "s": 38, "c": 39, "h": 42, "o": 46, "x": 49, "r": 51, "t": 45, "m": 47, "a": 50, "z": 52}


def bancoDeSonidos():
    elegido = os.environ.get("BANCO_SF2")
    for ruta in ([elegido] if elegido else []) + bancosConocidos:
        if ruta and os.path.exists(ruta):
            return ruta
    return None


def disponible():
    return shutil.which("fluidsynth") is not None and bancoDeSonidos() is not None


def numeroDeNota(nota):
    # "C#5" a numero MIDI, con C4 = 60.
    letra, resto = nota[0], nota[1:]
    alteracion = 0
    while resto[:1] in ("#", "b"):
        alteracion += 1 if resto[0] == "#" else -1
        resto = resto[1:]
    return 12 * (int(resto) + 1) + nombresNota[letra] + alteracion


def leerCompas(texto):
    # "E5.4 r.2 G5.2" es una lista de (nota, dieciseisavos) que suma un compas.
    notas = []
    for ficha in texto.split():
        nota, dur = ficha.rsplit(".", 1)
        notas.append((None if nota == "r" else nota, int(dur)))
    if sum(d for _, d in notas) != 16:
        raise ValueError("el compas no suma 16: " + texto)
    return notas


intervalosAcorde = {"": (0, 4, 7), "m": (0, 3, 7), "7": (0, 4, 7, 10), "m7": (0, 3, 7, 10),
                    "maj7": (0, 4, 7, 11), "dim": (0, 3, 6), "sus4": (0, 5, 7), "5": (0, 7, 12)}


def notasDeAcorde(nombre, octava):
    raiz, resto = nombre[0], nombre[1:]
    if resto[:1] in ("#", "b"):
        raiz, resto = raiz + resto[0], resto[1:]
    base = numeroDeNota(raiz + str(octava))
    return [base + i for i in intervalosAcorde[resto]]


class Voz:
    # Un instrumento en su propio canal. Las notas se guardan como
    # (inicio, duracion, nota, fuerza), todo en ticks.
    def __init__(self, canal, programa, volumen, paneo=64, eco=40):
        self.canal, self.programa = canal, programa
        self.volumen, self.paneo, self.eco = volumen, paneo, eco
        self.notas = []

    def nota(self, inicio, duracion, numero, fuerza):
        self.notas.append((int(inicio), max(1, int(duracion)), int(numero), max(1, min(127, int(fuerza)))))

    def melodia(self, compases, desde=0, octava=0, fuerza=96, ligado=0.92, acento=12):
        t = desde * 16 * ticksPorDieciseisavo
        for texto in compases:
            pos = 0
            for nota, dur in leerCompas(texto):
                if nota is not None:
                    # Los tiempos fuertes suenan un poco mas, como si alguien la tocara.
                    extra = acento if pos % 4 == 0 else 0
                    self.nota(t, dur * ticksPorDieciseisavo * ligado, numeroDeNota(nota) + 12 * octava, fuerza + extra)
                t += dur * ticksPorDieciseisavo
                pos += dur

    def acordes(self, acordes, ritmo, desde=0, octava=4, fuerza=80, ligado=0.9):
        # ritmo es un texto de 16 letras: X fuerte, x suave, - sigue sonando, . silencio.
        for k, nombre in enumerate(acordes):
            inicio = (desde + k) * 16
            for pos, duracion, fuerte in golpesDeRitmo(ritmo):
                for numero in notasDeAcorde(nombre, octava):
                    self.nota((inicio + pos) * ticksPorDieciseisavo, duracion * ticksPorDieciseisavo * ligado,
                              numero, fuerza if fuerte else fuerza - 22)

    def arpegio(self, acordes, figura, desde=0, octava=4, fuerza=70, ligado=1.0):
        # figura: un digito por dieciseisavo con la nota del acorde que toca (0 la
        # raiz, 3 la raiz una octava arriba si el acorde es de tres notas), - sigue, . nada.
        for k, nombre in enumerate(acordes):
            notas = notasDeAcorde(nombre, octava)
            notas = notas + [n + 12 for n in notas]
            inicio = (desde + k) * 16
            for pos, duracion, letra in golpesDeFigura(figura):
                self.nota((inicio + pos) * ticksPorDieciseisavo, duracion * ticksPorDieciseisavo * ligado,
                          notas[int(letra) % len(notas)], fuerza + (8 if pos % 8 == 0 else 0))

    def ostinato(self, acordes, saltos, acentos, desde=0, octava=3, fuerza=78, ligado=0.8):
        # Un dibujo de dieciseisavos que se repite sobre la raiz de cada acorde:
        # saltos dice cuantos semitonos arriba de la raiz va cada nota (None es
        # silencio) y acentos marca con X los golpes fuertes, como en las cuerdas
        # que empujan los temas de jefe.
        for k, nombre in enumerate(acordes):
            raiz = notasDeAcorde(nombre, octava)[0]
            tercera = notasDeAcorde(nombre, octava)[1] - raiz
            inicio = (desde + k) * 16
            for pos, salto in enumerate(saltos):
                if salto is None:
                    continue
                salto = tercera if salto == "3" else salto
                fuerte = acentos[pos] == "X"
                self.nota((inicio + pos) * ticksPorDieciseisavo, ticksPorDieciseisavo * ligado, raiz + salto,
                          fuerza + 22 if fuerte else fuerza - 10)

    def bajo(self, acordes, figura, desde=0, octava=2, fuerza=100, ligado=0.85):
        # figura dice que nota del acorde va en cada dieciseisavo: 0 la raiz,
        # 1 la raiz una octava arriba, 5 la quinta, 7 la septima menor, - sigue, . nada.
        saltos = {"0": 0, "1": 12, "5": 7, "7": 10, "3": None}
        for k, nombre in enumerate(acordes):
            raiz = notasDeAcorde(nombre, octava)
            inicio = (desde + k) * 16
            for pos, duracion, letra in golpesDeFigura(figura):
                salto = saltos[letra]
                numero = raiz[1] if salto is None else raiz[0] + salto
                self.nota((inicio + pos) * ticksPorDieciseisavo, duracion * ticksPorDieciseisavo * ligado, numero,
                          fuerza if pos % 4 == 0 else fuerza - 12)


def golpesDeRitmo(ritmo):
    golpes = []
    for pos, letra in enumerate(ritmo):
        if letra in "Xx":
            dur = 1
            while pos + dur < len(ritmo) and ritmo[pos + dur] == "-":
                dur += 1
            golpes.append((pos, dur, letra == "X"))
    return golpes


def golpesDeFigura(figura):
    golpes = []
    for pos, letra in enumerate(figura):
        if letra not in "-.":
            dur = 1
            while pos + dur < len(figura) and figura[pos + dur] == "-":
                dur += 1
            golpes.append((pos, dur, letra))
    return golpes


class Partitura:

    def __init__(self, bpm, compases):
        self.bpm, self.compases = bpm, compases
        self.voces = []
        self.tambores = Voz(9, 0, 110, 64, 30)

    def voz(self, programa, volumen, paneo=64, eco=40):
        canal = len(self.voces)
        if canal >= 9:
            canal += 1
        v = Voz(canal, programa, volumen, paneo, eco)
        self.voces.append(v)
        return v

    def bateria(self, patron, compases, desde=0, fuerza=100):
        # patron: una linea de 16 letras por pieza; mayuscula es golpe fuerte.
        for c in range(compases):
            for pieza, linea in patron.items():
                for pos, letra in enumerate(linea):
                    if letra in ".-":
                        continue
                    golpe = fuerza if letra.isupper() else fuerza - 25
                    self.tambores.nota(((desde + c) * 16 + pos) * ticksPorDieciseisavo, ticksPorDieciseisavo,
                                       piezas[pieza], golpe)

    def redoble(self, compas, pieza="s", desde=8, fuerza=70):
        # Un redoble que crece hasta el final del compas.
        for pos in range(desde, 16):
            self.tambores.nota((compas * 16 + pos) * ticksPorDieciseisavo, ticksPorDieciseisavo, piezas[pieza],
                               fuerza + (pos - desde) * 6)

    def segundos(self):
        return self.compases * 16 * 60 / self.bpm / 4

    def midi(self):
        pistas = [pistaDeTempo(self.bpm)]
        for v in self.voces + [self.tambores]:
            pistas.append(pistaDeVoz(v))
        cabecera = b"MThd" + struct.pack(">IHHH", 6, 1, len(pistas), ticksPorNegra)
        return cabecera + b"".join(b"MTrk" + struct.pack(">I", len(p)) + p for p in pistas)


def numeroVariable(n):
    datos = [n & 0x7F]
    n >>= 7
    while n:
        datos.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(datos))


def pistaDeTempo(bpm):
    microsegundos = int(60_000_000 / bpm)
    return (b"\x00\xff\x51\x03" + microsegundos.to_bytes(3, "big") +
            b"\x00\xff\x58\x04\x04\x02\x18\x08" + b"\x00\xff\x2f\x00")


def pistaDeVoz(v):
    c = v.canal
    inicio = bytes([0xC0 | c, v.programa]) if c != 9 else b""
    eventos = [(0, 0, bytes([0xB0 | c, 7, v.volumen])), (0, 0, bytes([0xB0 | c, 10, v.paneo])),
               (0, 0, bytes([0xB0 | c, 91, v.eco]))]
    for t, dur, numero, fuerza in v.notas:
        # Al mismo tiempo, primero se apagan las notas y luego se prenden.
        eventos.append((t, 1, bytes([0x90 | c, numero, fuerza])))
        eventos.append((t + dur, 0, bytes([0x80 | c, numero, 0])))
    eventos.sort(key=lambda e: (e[0], e[1]))
    datos = bytearray(b"\x00" + inicio if inicio else b"")
    ahora = 0
    for t, _, evento in eventos:
        datos += numeroVariable(t - ahora) + evento
        ahora = t
    datos += b"\x00\xff\x2f\x00"
    return bytes(datos)


def tocar(partitura, ganancia=0.5):
    # Toca la partitura con fluidsynth y regresa el audio en estereo, ya con
    # la cola del final sumada al principio para que el bucle no se note.
    with tempfile.TemporaryDirectory() as carpeta:
        rutaMidi = os.path.join(carpeta, "tema.mid")
        rutaWav = os.path.join(carpeta, "tema.wav")
        with open(rutaMidi, "wb") as f:
            f.write(partitura.midi())
        subprocess.run(["fluidsynth", "-ni", "-q", "-g", str(ganancia), "-r", str(frecuenciaMusica),
                        "-F", rutaWav, bancoDeSonidos(), rutaMidi], check=True, stdout=subprocess.DEVNULL)
        with wave.open(rutaWav) as w:
            canales = w.getnchannels()
            datos = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float) / 32768
    datos = datos.reshape(-1, canales)
    if canales == 1:
        datos = np.repeat(datos, 2, axis=1)

    largo = int(round(partitura.segundos() * frecuenciaMusica))
    if len(datos) < largo:
        datos = np.vstack([datos, np.zeros((largo - len(datos), 2))])
    sonido = datos[:largo].copy()
    cola = datos[largo:largo + largo // 2]
    sonido[:len(cola)] += cola
    return sonido


def masterizar(sonido, nivel=0.89, empuje=1.6):
    # Sube el volumen parejo y aplana los picos con una curva suave, para que
    # suene lleno sin recortarse.
    rms = np.sqrt(np.mean(sonido ** 2)) or 1.0
    s = sonido * (0.16 / rms) * empuje
    s = np.tanh(s) / np.tanh(1.0)
    return s / (np.max(np.abs(s)) or 1.0) * nivel


def temaSeleccion():
    # Tranquila, como un cuarto para descansar antes de la pelea: piano,
    # caja de musica y un colchon calido.
    acordes = ["Fmaj7", "Em7", "Dm7", "Cmaj7", "Bbmaj7", "Am7", "Gm7", "C",
               "Fmaj7", "Em7", "Dm7", "Cmaj7", "Bbmaj7", "Gm7", "Csus4", "C"]
    melodia = ["A5.6 G5.2 F5.4 C5.4", "E5.6 D5.2 E5.4 G5.4", "F5.6 E5.2 D5.4 A4.4", "G4.8 r.4 C5.4",
               "D5.6 C5.2 D5.4 F5.4", "E5.6 D5.2 C5.4 E5.4", "D5.4 Bb4.4 F5.6 E5.2", "E5.12 r.4",
               "A5.6 G5.2 F5.4 C6.4", "B5.6 A5.2 G5.4 E5.4", "F5.6 E5.2 D5.4 F5.4", "E5.8 G5.4 B5.4",
               "A5.6 F5.2 D5.4 F5.4", "G5.6 F5.2 D5.4 Bb4.4", "C5.8 F5.4 E5.4", "G4.12 r.4"]
    p = Partitura(76, 32)
    caja = p.voz(cajaDeMusica, 82, 70, 70)
    pianoVoz = p.voz(piano, 92, 58, 60)
    colchon = p.voz(colchonCalido, 58, 64, 80)
    bajo = p.voz(bajoDedos, 80, 64, 30)
    flautaVoz = p.voz(flauta, 64, 76, 70)
    for vuelta in (0, 16):
        pianoVoz.arpegio(acordes, "0-1-2-3-4-3-2-1-", vuelta, 3, 58, 1.8)
        colchon.acordes(acordes, "x---------------", vuelta, 4, 50, 1.0)
        bajo.bajo(acordes, "0-------5-------", vuelta, 2, 70, 0.95)
    caja.melodia(melodia, 0, 0, 84, 0.95, 8)
    # La segunda vuelta la canta la flauta una octava abajo y la caja la adorna.
    flautaVoz.melodia(melodia, 16, -1, 78, 0.95, 6)
    caja.melodia(melodia[8:], 24, 0, 60, 0.9, 4)
    return masterizar(tocar(p, 0.6), 0.8, 1.1)


# El leitmotiv del jefe es la melodia del titulo pasada a menor armonica: en
# la primera fase la cantan los metales y en la segunda vuelve tres semitonos
# mas arriba, mas rapida y con todo encima. La forma sigue a los temas de jefe
# final de los RPG: empieza oscura con organo, timbales y coro, entra un
# ostinato de cuerdas con acentos 3+3+2 que no deja respirar, bateria de rock
# con el bombo en los acentos y un climax con organo, coro y golpes de orquesta.
acentos332 = "X..X..X.X..X..X."
saltosOstinato = [0, 0, 12, 0, 0, 12, 7, 12, 0, 0, 12, 0, 0, 12, "3", 12]


def temaBatalla():
    intro = ["Dm", "Dm", "Bb", "A"]
    acordesA = ["Dm", "Dm", "Bb", "Bb", "Gm", "Gm", "A", "A"]
    acordesB = ["Bb", "C", "Dm", "Dm", "Gm", "Eb", "A", "A"]
    acordesC = ["Dm", "Bb", "Gm", "A", "Dm", "Eb", "A", "A"]
    leitmotiv = ["A4.6 D5.2 E5.4 F5.4", "G5.6 F5.2 E5.4 D5.4", "F5.6 E5.2 D5.4 Bb4.4", "D5.12 r.4",
                 "Bb4.6 D5.2 G5.4 F5.4", "E5.6 D5.2 C#5.4 D5.4", "E5.4 C#5.4 A4.4 E5.4", "C#5.12 r.4"]
    melodiaB = ["F5.4 Bb5.4 D6.6 C6.2", "E5.4 G5.4 C6.6 Bb5.2", "A5.6 G5.2 F5.4 E5.4", "D5.8 F5.4 A5.4",
                "Bb5.6 A5.2 G5.4 D5.4", "Eb5.6 G5.2 Bb5.4 G5.4", "A5.4 C#6.4 E6.4 C#6.4", "E6.8 r.8"]
    melodiaC = ["D6.8 A5.4 F5.4", "D6.6 C6.2 Bb5.4 F5.4", "G5.6 Bb5.2 D6.4 G6.4", "F6.4 E6.4 C#6.4 A5.4",
                "A5.6 D6.2 E6.4 F6.4", "G6.6 F6.2 Eb6.4 Bb5.4", "C#6.4 E6.4 A6.4 G6.4", "E6.4 C#6.4 A5.4 r.4"]
    todos = intro + acordesA + acordesA + acordesB + acordesC

    p = Partitura(138, 36)
    p.tambores.volumen = 110
    cornosVoz = p.voz(cornos, 100, 54, 60)
    trombonVoz = p.voz(trombon, 92, 70, 50)
    metalesVoz = p.voz(metales, 96, 64, 55)
    cuerdasVoz = p.voz(cuerdas, 100, 76, 50)
    tremolo = p.voz(cuerdasTremolo, 100, 40, 70)
    organoVoz = p.voz(organo, 76, 64, 90)
    coroVoz = p.voz(coro, 90, 64, 100)
    bajo = p.voz(contrabajo, 127, 64, 20)
    timbal = p.voz(timbales, 110, 64, 60)
    golpe = p.voz(golpeDeOrquesta, 92, 64, 60)

    # Introduccion: organo y coro sobre un pedal de timbal; el ostinato entra solo.
    organoVoz.acordes(intro, "X---------------", 0, 3, 90, 1.0)
    coroVoz.acordes(intro[2:], "x---------------", 2, 4, 70, 1.0)
    timbal.ostinato(intro[:3], [0] * 16, "X...x...X...x...", 0, 2, 70, 0.9)
    timbal.ostinato(["A"], [0] * 16, "X.x.x.x.XxXxXxXx", 3, 2, 80, 0.9)
    cuerdasVoz.ostinato(intro[2:], saltosOstinato, acentos332, 2, 3, 56)

    # Seccion A dos veces: el leitmotiv en cornos y trombon, luego arriba en
    # cuerdas y metales con el coro detras.
    cornosVoz.melodia(leitmotiv, 4, 0, 98)
    trombonVoz.melodia(leitmotiv, 4, -1, 84)
    metalesVoz.melodia(leitmotiv, 12, 0, 100)
    cuerdasVoz.melodia(leitmotiv, 12, 1, 84)
    coroVoz.acordes(acordesA, "x-------x-------", 12, 4, 74, 1.0)
    cuerdasVoz.ostinato(acordesA, saltosOstinato, acentos332, 4, 3, 66)
    tremolo.ostinato(acordesA, saltosOstinato, acentos332, 12, 2, 60)

    # Seccion B: la melodia sube, cuerdas largas y el Napolitano (Eb) antes del La.
    metalesVoz.melodia(melodiaB, 20, 0, 104)
    cuerdasVoz.melodia(melodiaB, 20, 0, 90)
    tremolo.acordes(acordesB, "x---------------", 20, 4, 66, 1.0)
    cornosVoz.acordes(acordesB, "X-------X-------", 20, 3, 80, 1.0)

    # Seccion C: el climax con organo y coro a todo, y golpes de orquesta.
    metalesVoz.melodia(melodiaC, 28, 0, 112)
    cornosVoz.melodia(melodiaC, 28, -1, 100)
    organoVoz.acordes(acordesC, "X-------X-------", 28, 3, 100, 1.0)
    coroVoz.acordes(acordesC, "X---------------", 28, 4, 104, 1.0)
    cuerdasVoz.ostinato(acordesC, saltosOstinato, acentos332, 28, 4, 74)

    for inicio, acorde in ((4, "Dm"), (12, "Dm"), (20, "Bb"), (28, "Dm")):
        golpe.acordes([acorde], "X...............", inicio, 4, 116)
    golpe.acordes(["A", "A"], "X..X..X.X..X..X.", 34, 4, 104)
    golpesBajo = [0, None, None, 0, None, None, 0, None, 0, None, None, 0, None, None, 0, None]
    bajo.ostinato(todos[2:], golpesBajo, acentos332, 2, 2, 100)
    # Un piano en lo grave dobla al bajo y le da golpe a cada acento.
    pianoGrave = p.voz(piano, 96, 64, 30)
    pianoGrave.ostinato(todos[2:], golpesBajo, acentos332, 2, 1, 96, 0.9)
    timbal.ostinato(["A"], [0] * 16, "X...X...XxXxXxXx", 27, 2, 92, 0.9)
    timbal.ostinato(acordesC, [0] + [None] * 7 + [0] + [None] * 7, "X.......X.......", 28, 2, 100)

    acentos = {"k": "K..K..K.K..K..K.", "s": "....S.......S...", "h": "h.h.h.h.h.h.h.h."}
    climax = {"k": "KkkKkkKkKkkKkkKk", "s": "....S.......S..s", "r": "R.r.R.r.R.r.R.r."}
    p.redoble(3, "s", 8, 50)
    p.bateria(acentos, 15, 4, 110)
    p.redoble(19, "t", 8, 70)
    p.bateria(dict(acentos, r="r.r.r.r.r.r.r.r."), 7, 20, 112)
    p.redoble(27, "s", 0, 50)
    p.bateria(climax, 7, 28, 118)
    p.bateria({"t": "..........t.m.a.", "a": "..............A."}, 1, 35, 110)
    for inicio in (4, 12, 20, 28, 32):
        p.bateria({"x": "X..............."}, 1, inicio)
    return masterizar(tocar(p, 0.5))


def temaBatalla2():
    acordesA = ["Fm", "Fm", "Db", "Db", "Bbm", "Bbm", "C", "C"]
    acordesB = ["Db", "Eb", "Fm", "Fm", "Bbm", "Gb", "C", "C"]
    acordesC = ["Fm", "Db", "Bbm", "C", "Fm", "Db", "Gb", "C"]
    acordesD = ["Fm", "Db", "Bbm", "C", "Fm", "C"]
    leitmotiv = ["C5.6 F5.2 G5.4 Ab5.4", "Bb5.6 Ab5.2 G5.4 F5.4", "Ab5.6 G5.2 F5.4 Db5.4", "F5.12 r.4",
                 "Db5.6 F5.2 Bb5.4 Ab5.4", "G5.6 F5.2 E5.4 F5.4", "G5.4 E5.4 C5.4 G5.4", "E5.12 r.4"]
    melodiaB = ["F5.2 Ab5.2 Db6.2 F6.2 Eb6.4 Db6.4", "G5.2 Bb5.2 Eb6.2 G6.2 F6.4 Eb6.4", "Ab6.6 G6.2 F6.4 C6.4",
                "F6.2 Eb6.2 C6.2 Ab5.2 C6.4 F6.4", "Db6.6 C6.2 Bb5.4 F5.4", "Gb5.6 Bb5.2 Db6.4 Bb5.4",
                "C6.4 E6.4 G6.4 E6.4", "G6.8 r.8"]
    canto = ["F5.8 Ab5.8", "Db6.8 C6.8", "Bb5.8 Db6.8", "C6.16", "F6.8 Eb6.8", "Db6.8 F6.8",
             "Gb6.8 F6.4 Eb6.4", "E6.16"]
    melodiaD = ["C6.6 F6.2 G6.4 Ab6.4", "Bb6.6 Ab6.2 G6.4 F6.4", "Db6.6 F6.2 Bb6.4 Ab6.4", "G6.4 E6.4 C6.4 G5.4",
                "F6.4 C6.4 Ab5.4 F5.4", "E5.4 G5.4 C6.4 r.4"]
    todos = ["Fm", "C"] + acordesA + acordesB + acordesC + acordesD

    p = Partitura(156, 32)
    p.tambores.volumen = 112
    metalesVoz = p.voz(metales, 100, 60, 55)
    cornosVoz = p.voz(cornos, 96, 48, 60)
    cuerdasVoz = p.voz(cuerdas, 100, 80, 50)
    coroVoz = p.voz(coro, 100, 64, 100)
    organoVoz = p.voz(organo, 80, 64, 90)
    guitarra = p.voz(guitarraDistorsionada, 70, 36, 20)
    bajo = p.voz(contrabajo, 127, 64, 20)
    timbal = p.voz(timbales, 112, 64, 60)
    golpe = p.voz(golpeDeOrquesta, 96, 64, 60)

    # Dos compases de entrada: golpes de orquesta, coro cortado y timbales.
    golpe.acordes(["Fm", "C"], "X..X..X.........", 0, 4, 120)
    coroVoz.acordes(["Fm", "C"], "X..X..X.X-------", 0, 4, 110, 0.9)
    timbal.ostinato(["F", "C"], [0] * 16, "X..X..X.XxXxXxXx", 0, 2, 90, 0.9)

    # A: el leitmotiv en metales con el coro cantando acordes cortados.
    metalesVoz.melodia(leitmotiv, 2, 0, 108)
    cornosVoz.melodia(leitmotiv, 2, -1, 96)
    coroVoz.acordes(acordesA, "X..X..X.X..X..X.", 2, 4, 84, 0.8)
    cuerdasVoz.ostinato(acordesA, saltosOstinato, acentos332, 2, 3, 76)

    # B: carreras en cuerdas y metales, el Napolitano (Gb) antes del Do.
    cuerdasVoz.melodia(melodiaB, 10, 0, 100)
    metalesVoz.melodia(melodiaB, 10, -1, 96)
    organoVoz.acordes(acordesB, "X-------X-------", 10, 3, 90, 1.0)

    # C: el coro canta largo mientras las cuerdas corren abajo, como una misa.
    coroVoz.melodia(canto, 18, 0, 110, 0.98, 0)
    cornosVoz.melodia(canto, 18, -1, 92, 0.98, 0)
    organoVoz.acordes(acordesC, "X---------------", 18, 3, 96, 1.0)
    cuerdasVoz.ostinato(acordesC, saltosOstinato, acentos332, 18, 3, 82)

    # D: el leitmotiv arriba con todo.
    metalesVoz.melodia(melodiaD, 26, 0, 118)
    cuerdasVoz.melodia(melodiaD, 26, 0, 104)
    coroVoz.acordes(acordesD, "X-------X-------", 26, 4, 110, 1.0)
    organoVoz.acordes(acordesD, "X---------------", 26, 3, 100, 1.0)

    for k, nombre in enumerate(todos[2:]):
        raiz = nombre[:2] if nombre[1:2] in ("#", "b") else nombre[:1]
        guitarra.acordes([raiz + "5"], "X..X..X.X..X..X." if k < 16 else "XxxXxxXxXxxXxxXx", 2 + k, 3, 92, 0.6)
    bajo.ostinato(todos[2:], [0, 0, 12, 0, 0, 12, 0, 12, 0, 0, 12, 0, 0, 12, 0, 12], acentos332, 2, 2, 96, 0.8)
    pianoGrave = p.voz(piano, 96, 64, 30)
    pianoGrave.ostinato(todos[2:], [0, None, None, 0, None, None, 0, None, 0, None, None, 0, None, None, 0, None],
                        acentos332, 2, 1, 100, 0.9)
    for inicio in (2, 10, 18, 26):
        golpe.acordes([todos[inicio]], "X...............", inicio, 4, 120)
    golpe.acordes(["C", "C"], "X..X..X.X..X..X.", 24, 4, 110)
    timbal.ostinato(acordesC, [0] + [None] * 7 + [0] + [None] * 7, "X.......X.......", 18, 2, 104)
    timbal.ostinato(["C"], [0] * 16, "X...X...XxXxXxXx", 25, 2, 100, 0.9)

    marcha = {"k": "K..K..K.K..K..K.", "s": "....S.......S...", "h": "hhhhhhhhhhhhhhhh"}
    furia = {"k": "KkkkKkkkKkkkKkkk", "s": "....S..s....S.ss", "z": "Z.......Z.......", "r": "r.r.r.r.r.r.r.r."}
    p.redoble(1, "s", 8, 60)
    p.bateria(marcha, 8, 2, 112)
    p.bateria(furia, 7, 10, 118)
    p.redoble(17, "s", 4, 60)
    p.bateria({"k": "K.......K.......", "s": "............S...", "r": "R...r...R...r..."}, 8, 18, 104)
    p.bateria(furia, 5, 26, 120)
    p.bateria({"t": "........t.t.m.a.", "a": "..............A.", "k": "K..K..K........."}, 1, 31, 116)
    for inicio in (2, 10, 18, 26, 30):
        p.bateria({"x": "X..............."}, 1, inicio)
    return masterizar(tocar(p, 0.5))


temas = {"seleccion": temaSeleccion, "batalla": temaBatalla, "batalla2": temaBatalla2}
