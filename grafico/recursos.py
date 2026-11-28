# Carga de imágenes, música y sonidos. Si a una imagen le falta su archivo se
# dibuja un marcador con el nombre que le toca, y si falta un sonido el juego
# sigue en silencio; asi un recurso nuevo se agrega con solo dejar el archivo
# con su nombre en la carpeta.
import json
import os

import pygame

import motor as m
from grafico.interfaz import colores, dibujarTexto

carpetaRecursos = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recursos")

# Un color por categoría para distinguir los marcadores de un vistazo.
coloresMarcador = {"personajes": (70, 110, 160), "jefes": (150, 70, 80), "escenarios": (46, 60, 58),
                   "efectos": (170, 130, 60)}
coloresElemento = [(226, 92, 60), (70, 140, 226), (110, 200, 190), (176, 132, 84),
                   (96, 180, 90), (236, 208, 80), (240, 236, 200), (130, 96, 190)]

imagenesCargadas = {}
sonidosCargados = {}


def nombreDeArchivo(texto):
    return texto.lower().replace(" ", "_")


def rutaDe(categoria, nombre, extension="png"):
    return os.path.join(carpetaRecursos, categoria, nombreDeArchivo(nombre) + "." + extension)


def crearMarcador(categoria, nombre, tamano):
    imagen = pygame.Surface(tamano, pygame.SRCALPHA)
    rect = imagen.get_rect()
    pygame.draw.rect(imagen, coloresMarcador.get(categoria, (90, 90, 90)), rect, border_radius=10)
    pygame.draw.rect(imagen, colores["borde"], rect, width=2, border_radius=10)

    # En los marcadores chicos el nombre no cabe y solo estorbaría.
    if rect.width >= 90 and rect.height >= 50:
        dibujarTexto(imagen, categoria, (rect.centerx, rect.centery - 11), 18, colores["textoSuave"],
                     centrado=True, anchoMax=rect.width - 10)
        dibujarTexto(imagen, nombreDeArchivo(nombre) + ".png", (rect.centerx, rect.centery + 9), 18,
                     colores["texto"], centrado=True, anchoMax=rect.width - 10)
    return imagen


def obtenerImagen(categoria, nombre, tamano):
    clave = (categoria, nombre, tuple(tamano))
    if clave not in imagenesCargadas:
        ruta = rutaDe(categoria, nombre)
        if os.path.exists(ruta):
            imagen = pygame.image.load(ruta).convert_alpha()
            # Los efectos son pixel art y se agrandan sin suavizar.
            escalar = pygame.transform.scale if categoria == "efectos" else pygame.transform.smoothscale
            imagen = escalar(imagen, tamano)
        else:
            imagen = crearMarcador(categoria, nombre, tamano)
        imagenesCargadas[clave] = imagen
    return imagenesCargadas[clave]


def obtenerEscenario(nombre, tamano):
    # Los escenarios de combate son mas anchos que la zona donde se pelea, asi
    # que se escalan hasta cubrirla y se recorta lo que sobra a los lados, sin
    # deformarlos.
    clave = ("escenarioCubierto", nombre, tuple(tamano))
    if clave not in imagenesCargadas:
        ruta = rutaDe("escenarios", nombre)
        if not os.path.exists(ruta):
            return obtenerImagen("escenarios", nombre, tamano)
        imagen = pygame.image.load(ruta).convert()
        escala = max(tamano[0] / imagen.get_width(), tamano[1] / imagen.get_height())
        grande = pygame.transform.smoothscale(imagen, (round(imagen.get_width() * escala),
                                                       round(imagen.get_height() * escala)))
        recorte = pygame.Rect(0, 0, *tamano)
        recorte.center = grande.get_rect().center
        imagenesCargadas[clave] = grande.subsurface(recorte).copy()
    return imagenesCargadas[clave]


# Los heroes ya tienen arte: un sprite de pixel art por pose, guardado a su
# resolucion real. Estas son las poses que el juego sabe usar; las genera
# grafico/poses.py a partir de recursos/personajes/base.
posesHeroe = ["", "ataque", "magia", "bloqueo", "dano", "herido", "caido", "celebra"]
spritesCargados = {}
alturasBase = {}


def alturaBase(clase):
    # Todas las poses de una clase se escalan con el mismo factor, el que deja
    # a su sprite base del alto pedido, para que los pixeles no cambien de
    # tamano de una pose a otra.
    if clase not in alturasBase:
        ruta = os.path.join(carpetaRecursos, "personajes", "base", nombreDeArchivo(clase) + ".png")
        alturasBase[clase] = pygame.image.load(ruta).get_height() if os.path.exists(ruta) else None
    return alturasBase[clase]


def obtenerSprite(clase, pose, alturaCuerpo):
    clave = (clase, pose, alturaCuerpo)
    if clave not in spritesCargados:
        nombre = clase + (" " + pose if pose else "")
        ruta = rutaDe("personajes", nombre)
        base = alturaBase(clase)
        if os.path.exists(ruta) and base:
            # Se agranda por un numero entero de veces y sin suavizar, para que
            # cada pixel del dibujo quede como un cuadro parejo en pantalla.
            factor = max(1, round(alturaCuerpo / base))
            imagen = pygame.image.load(ruta).convert_alpha()
            imagen = pygame.transform.scale(imagen, (imagen.get_width() * factor, imagen.get_height() * factor))
        else:
            imagen = crearMarcador("personajes", nombre, (int(alturaCuerpo * 0.94), alturaCuerpo))
        spritesCargados[clave] = imagen
    return spritesCargados[clave]


# El jefe tambien ya tiene arte. Sus sprites estan a la resolucion real de
# su ilustracion, que es mas fina que la de los heroes, asi que se dibujan sin
# agrandar. La segunda fase ya viene dibujada mas alta, pero entre el ala y el
# halo su cuerpo queda chico, asi que se agranda un poco mas.
escalaJefe = {"fase1": 1.0, "fase2": 1.15}
tamanoMarcadorJefe = (300, 330)


def obtenerSpriteJefe(nombre, fase2, extra=1.0):
    # Cada tamaño distinto se guarda, y el crecimiento del cambio de fase
    # pediría uno nuevo en cada cuadro. Se redondea a pasos de 0.02 para que
    # solo existan unos cuantos.
    escala = escalaJefe["fase2" if fase2 else "fase1"] * round(extra / 0.02) * 0.02
    clave = (nombre, round(escala, 3))
    if clave not in spritesCargados:
        ruta = rutaDe("jefes", nombre)
        if os.path.exists(ruta):
            imagen = pygame.image.load(ruta).convert_alpha()
            if escala != 1.0:
                imagen = pygame.transform.scale(imagen, (round(imagen.get_width() * escala), round(imagen.get_height() * escala)))
        else:
            imagen = crearMarcador("jefes", nombre, (round(tamanoMarcadorJefe[0] * escala), round(tamanoMarcadorJefe[1] * escala)))
        spritesCargados[clave] = imagen
    return spritesCargados[clave]


# El jefe tiene 8 poses de ataque repartidas entre los 32 ataques de su banco,
# 4 ataques por pose en el orden del banco. Así cada pose corresponde a un
# grupo parecido: golpes, golpes pesados, área física, magia, y así.
ataquesPorPose = 4
nPosesJefe = len(m.HABILIDADES) // ataquesPorPose

# Los cuadros que usa el jefe al atacar: toma impulso y suelta el golpe, o
# junta la magia y la suelta.
cuadrosAtaqueJefe = ["alzar", "golpe", "conjuro", "lanzar"]


def poseDelJefe(nombreAtaque):
    for i, ataque in enumerate(m.HABILIDADES):
        if ataque["nombre"] == nombreAtaque:
            return i // ataquesPorPose + 1
    return 1


# El volumen de la musica y de los efectos, de 0 a 1. Se guardan en
# opciones.json para que el juego los recuerde la siguiente vez.
archivoOpciones = os.path.join(os.path.dirname(carpetaRecursos), "opciones.json")
volumenes = {"musica": 0.6, "efectos": 0.8}
musicaActual = [None]
ultimoSonido = {}


def cargarOpciones():
    try:
        with open(archivoOpciones) as f:
            volumenes.update({k: float(v) for k, v in json.load(f).items() if k in volumenes})
    except (OSError, ValueError):
        pass


def guardarOpciones():
    try:
        with open(archivoOpciones, "w") as f:
            json.dump(volumenes, f)
    except OSError:
        pass


def iniciarAudio():
    # Se llama antes de pygame.init para pedir un buffer chico, que hace que
    # los efectos suenen justo cuando pasa lo que se ve.
    cargarOpciones()
    try:
        # En estereo y a 44100, que es como viene la musica con instrumentos; los
        # efectos, que son mono a 22050, pygame los convierte al cargarlos.
        pygame.mixer.pre_init(44100, -16, 2, 1024)
    except pygame.error:
        pass


def rutaDeSonido(nombre):
    for extension in ("ogg", "wav"):
        ruta = os.path.join(carpetaRecursos, "sonidos", nombre + "." + extension)
        if os.path.exists(ruta):
            return ruta
    return None


def reproducirSonido(nombre, volumen=1.0):
    # Los sonidos son opcionales del todo: sin archivo o sin tarjeta de sonido
    # el juego sigue igual, en silencio. Si el mismo sonido se pide dos veces
    # casi al mismo tiempo, como al pegarle a todo el equipo, suena una vez.
    if not pygame.mixer.get_init():
        return
    if nombre not in sonidosCargados:
        if pygame.mixer.get_num_channels() < 24:
            pygame.mixer.set_num_channels(24)
        ruta = rutaDeSonido(nombre)
        sonidosCargados[nombre] = pygame.mixer.Sound(ruta) if ruta else None
    sonido = sonidosCargados[nombre]
    ahora = pygame.time.get_ticks()
    if sonido is None or ahora - ultimoSonido.get(nombre, -1000) < 45:
        return
    ultimoSonido[nombre] = ahora
    sonido.set_volume(max(0.0, min(1.0, volumen * volumenes["efectos"])))
    sonido.play()


def reproducirMusica(nombre, bucle=True, fundido=600):
    # Cambia la musica de fondo. Pedir la que ya suena no la reinicia.
    if not pygame.mixer.get_init() or musicaActual[0] == nombre:
        return
    musicaActual[0] = nombre
    if nombre is None:
        pygame.mixer.music.fadeout(fundido)
        return
    ruta = rutaDeSonido(os.path.join("musica", nombre))
    if ruta is None:
        pygame.mixer.music.fadeout(fundido)
        return
    pygame.mixer.music.load(ruta)
    pygame.mixer.music.set_volume(volumenes["musica"])
    pygame.mixer.music.play(-1 if bucle else 0, fade_ms=fundido)


def detenerMusica(fundido=400):
    reproducirMusica(None, fundido=fundido)


def cambiarVolumen(tipo, valor):
    volumenes[tipo] = max(0.0, min(1.0, round(valor, 2)))
    if tipo == "musica" and pygame.mixer.get_init():
        pygame.mixer.music.set_volume(volumenes["musica"])
    guardarOpciones()


def recursosEsperados():
    # Todos los archivos que el juego sabe buscar, por carpeta. Sirve para
    # saber qué falta por dibujar o grabar.
    efectos = ["ataque_basico", "cambio_de_fase"]
    efectos += [nombreDeArchivo(a["nombre"]) for a in m.HABILIDADES]
    for clase in m.tablaClases.values():
        efectos += [nombreDeArchivo(c["nombre"]) for c in clase["conjuros"] if c["tipo"] == "ataque"]
    efectos += [nombreDeArchivo(c["nombre"]) for c in m.conjurosMago + m.conjurosMagoPoderosos]

    personajes = []
    for nombre in m.nombresClases:
        personajes += [nombreDeArchivo(nombre) + ("_" + pose if pose else "") + ".png" for pose in posesHeroe]

    jefes = []
    for prefijo in ("jefe", "jefe_fase2"):
        jefes += [prefijo + ".png"] + ["%s_pose_%d.png" % (prefijo, n) for n in range(1, nPosesJefe + 1)]
        jefes += [prefijo + "_dano.png", prefijo + "_derrota.png"]
        jefes += ["%s_%s.png" % (prefijo, cuadro) for cuadro in cuadrosAtaqueJefe]

    return {
        "personajes": personajes,
        "jefes": jefes,
        "escenarios": ["arena.png", "arena_fase2.png", "titulo_fondo.png", "titulo_rueda.png"],
        "efectos": sorted(set(e + ".png" for e in efectos)),
        "sonidos": sorted(nombre + ".ogg" for nombre in efectosDeSonido()),
        "musica": [nombre + ".ogg" for nombre in temasDeMusica],
    }


temasDeMusica = ["titulo", "seleccion", "batalla", "batalla2", "victoria", "derrota", "entrenamiento"]


def efectosDeSonido():
    # Los nombres de los efectos los decide grafico/generarAudio.py; aqui se
    # leen de su carpeta para no repetir la lista.
    carpeta = os.path.join(carpetaRecursos, "sonidos")
    if not os.path.isdir(carpeta):
        return []
    return sorted({os.path.splitext(f)[0] for f in os.listdir(carpeta) if f.endswith((".ogg", ".wav"))})
