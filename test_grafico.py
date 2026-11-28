# Pruebas de la parte gráfica. Corren sin abrir ventana: pygame usa un
# controlador de video de mentira y las pantallas se dibujan en memoria.
# Correr con:  python -m pytest -q
import os
import time
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
pygame = pytest.importorskip("pygame")

import motor as m
import juego
from grafico import escenas, recursos
from grafico.puente import PartidaEnHilo

jefeDePrueba = {"puntos": [250] * 6, "objeto1": 0, "objeto2": 5,
                "habs": [28, 0, 12, 20, 8, 3, 17, 5], "pesos": [1] * 8,
                "cambios": [[0, 9], [7, 30]], "ajustes": [1] * 5,
                "predisposicion": [3] * 6}
equipoDePrueba = ["Guerrero", "Tanque", "Mago", "Picaro"]


def tecla(j, k):
    j.manejarEvento(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=""))


def clic(j, pos):
    j.manejarEvento(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def jugarComoElAutomatico(partida, limite=20.0):
    # Contesta cada petición del motor con lo que haría el jugador automático.
    inicio = time.time()
    while not partida.terminada():
        assert time.time() - inicio < limite
        p = partida.peticion
        if p is None:
            time.sleep(0.001)
            continue
        accion = m.decidir_accion(p["heroe"], p["est"])
        assert accion in p["opciones"]
        partida.responder(accion)
        while partida.peticion is p:
            time.sleep(0.001)


def testElPuenteDaElMismoCombateQueElMotor():
    # El combate que corre en un hilo para la ventana tiene que ser el mismo que
    # corre el motor solo, número por número, si se le contesta igual.
    crom = m.reparar(jefeDePrueba)
    for semilla in range(3):
        partida = PartidaEnHilo(crom, m.armarEquipo(equipoDePrueba), semilla)
        jugarComoElAutomatico(partida)
        assert partida.resultado == m.simular(crom, m.armarEquipo(equipoDePrueba), semilla)
        assert partida.registro[0]["tipo"] == "inicio"


def testCancelarSueltaAlHilo():
    partida = PartidaEnHilo(m.reparar(jefeDePrueba), m.armarEquipo(equipoDePrueba), 0)
    while partida.peticion is None:
        time.sleep(0.001)
    partida.cancelar()
    partida.hilo.join(timeout=5)
    assert not partida.hilo.is_alive() and not partida.terminada()


def testRecursoFaltanteEsUnMarcador():
    pygame.display.set_mode((1, 1))
    imagen = recursos.obtenerImagen("escenarios", "titulo", (1280, 720))
    assert imagen.get_size() == (1280, 720)
    assert not os.path.exists(recursos.rutaDe("escenarios", "titulo"))
    assert recursos.rutaDe("efectos", "Golpe pesado").endswith(os.path.join("efectos", "golpe_pesado.png"))


def testListaDeRecursosEsperados():
    esperados = recursos.recursosEsperados()
    # Cada clase tiene sus 8 poses, y todas existen ya como archivo
    assert esperados["personajes"][:3] == ["guerrero.png", "guerrero_ataque.png", "guerrero_magia.png"]
    assert len(esperados["personajes"]) == 6 * 8
    for archivo in esperados["personajes"]:
        assert os.path.exists(os.path.join(recursos.carpetaRecursos, "personajes", archivo)), archivo
    # El jefe tiene en cada fase su imagen, 8 poses de ataque, una de dano, una de derrota y 4 cuadros de ataque
    assert "jefe_pose_8.png" in esperados["jefes"] and "jefe_fase2_derrota.png" in esperados["jefes"]
    assert len(esperados["jefes"]) == 2 * (1 + 8 + 2 + 4)
    for archivo in esperados["jefes"]:
        assert os.path.exists(os.path.join(recursos.carpetaRecursos, "jefes", archivo)), archivo
    # Cada ataque del banco del jefe tiene su lugar en efectos, y todos los efectos ya tienen arte
    for ataque in m.HABILIDADES:
        assert recursos.nombreDeArchivo(ataque["nombre"]) + ".png" in esperados["efectos"]
    for archivo in esperados["efectos"]:
        assert os.path.exists(os.path.join(recursos.carpetaRecursos, "efectos", archivo)), archivo


def testSpritesDeHeroes():
    pygame.display.set_mode((1, 1))
    # El guerrero mide 30 pixeles: para 120 de alto se agranda 4 veces, y todas
    # sus poses usan el mismo factor aunque cambie su tamaño.
    base = recursos.obtenerSprite("Guerrero", "", 120)
    assert base.get_height() == 30 * 4
    caido = recursos.obtenerSprite("Guerrero", "caido", 120)
    assert caido.get_width() == 30 * 4
    # Una clase sin archivo cae en un marcador del alto pedido
    assert recursos.obtenerSprite("Nadie", "", 120).get_height() == 120


def testSpritesDelJefe():
    pygame.display.set_mode((1, 1))
    # La primera fase se dibuja a su tamaño real y la segunda un poco mas grande
    base1 = pygame.image.load(os.path.join(recursos.carpetaRecursos, "jefes", "base", "fase1.png"))
    base2 = pygame.image.load(os.path.join(recursos.carpetaRecursos, "jefes", "base", "fase2.png"))
    assert recursos.obtenerSpriteJefe("jefe", False).get_size() == base1.get_size()
    assert recursos.obtenerSpriteJefe("jefe_fase2", True).get_height() == round(base2.get_height() * 1.15)
    assert recursos.obtenerSpriteJefe("jefe_fase2", True).get_height() > recursos.obtenerSpriteJefe("jefe", False).get_height()


def testLasPosesSalenDeLaBase():
    from grafico import poses
    for clase in poses.clasesConSprite:
        base = poses.leerBase(clase)
        generadas = poses.generarPoses(clase)
        assert set(generadas) == set(recursos.posesHeroe)
        # Acostado ocupa lo que antes era su alto a lo ancho
        assert generadas["caido"].size == (base.height, base.width)
        # Agachado y de rodillas no cambian el ancho del lienzo mas que la inclinacion
        assert generadas["herido"].height == base.height
        # La pose de daño conserva la silueta: mismos pixeles opacos que la base inclinada
        opacos = lambda im: sum(im.getchannel("A").point(lambda a: 1 if a else 0).histogram()[1:])
        assert opacos(generadas["dano"]) == opacos(poses.inclinar(base, -3))

    # El jefe tiene sus 8 poses, la de dano y la de derrota, en cada fase
    from PIL import Image
    for fase in ("fase1", "fase2"):
        base = Image.open(os.path.join(recursos.carpetaRecursos, "jefes", "base", fase + ".png")).convert("RGBA")
        assert set(poses.posesDelJefe(base)) == {""} | {"pose_%d" % n for n in range(1, 9)} | {"dano", "derrota"}
        # Los cuadros de ataque no recorren al jefe: crecen lo mismo a los dos
        # lados, asi que su centro de abajo no cambia
        cuadros = poses.cuadrosDeAtaque(base, fase)
        assert set(cuadros) == set(recursos.cuadrosAtaqueJefe)
        for im in cuadros.values():
            assert (im.width - base.width) % 2 == 0 and im.height >= base.height - 20


def testPoseEnReposo():
    combate = escenas.EscenaCombate.__new__(escenas.EscenaCombate)
    combate.vida, combate.vidaMax = [300, 20, 0, 150], [300, 200, 200, 300]
    combate.mostrados, combate.fiesta = 5, None
    combate.tiempoDano, combate.protecciones = [0.0, 0.0, 0.0, 0.3], [["bloqueo"], [], [], []]
    assert [combate.poseEnReposo(j) for j in range(4)] == ["bloqueo", "herido", "caido", "dano"]
    combate.fiesta = 0.1
    assert [combate.poseEnReposo(j) for j in range(4)] == ["celebra", "celebra", "caido", "celebra"]
    assert combate.alturaDeSalto(2) == 0.0 and combate.alturaDeSalto(0) > 0


def testPosesDelJefe():
    # 32 ataques entre 8 poses: 4 por pose, en el orden del banco
    assert recursos.nPosesJefe == 8
    assert [recursos.poseDelJefe(m.HABILIDADES[i]["nombre"]) for i in (0, 3, 4, 11, 12, 27, 28, 31)] == [1, 1, 2, 3, 4, 7, 8, 8]
    cuentas = {}
    for ataque in m.HABILIDADES:
        pose = recursos.poseDelJefe(ataque["nombre"])
        cuentas[pose] = cuentas.get(pose, 0) + 1
    assert cuentas == {n: 4 for n in range(1, 9)}
    # Los cuatro ataques de carga comparten la última pose
    assert {recursos.poseDelJefe(a["nombre"]) for a in m.HABILIDADES if a["carga"]} == {8}


def testFrasesDelDialogo():
    azul, amarillo = escenas.colores["heroe"], escenas.colores["jefe"]
    rojo, verde = escenas.colores["dano"], escenas.colores["cura"]

    ev = {"actor": "Guerrero", "accion": "Ataque basico", "elem": None, "adelantado": False,
          "golpes": [("Jefe", 45, "")], "curas": [], "muertos": []}
    assert escenas.frasesDeTurno(ev) == [
        [("Guerrero", azul), (" usó ataque normal.", None)],
        [("El Jefe", amarillo), (" ha recibido ", None), ("45", rojo), (" de daño.", None)]]

    ev = {"actor": "Clerigo", "accion": "Curacion menor", "elem": None, "adelantado": False,
          "golpes": [], "curas": [("Mago", 60)], "muertos": []}
    assert escenas.frasesDeTurno(ev)[1] == [("Mago", azul), (" recuperó ", None), ("60", verde), (" de vida.", None)]

    ev = {"actor": "Jefe", "accion": "Llamarada", "elem": 0, "adelantado": False,
          "golpes": [("Tanque", 0, "esquiva"), ("Mago", 120, "critico")], "curas": [], "muertos": ["Mago"]}
    lineas = escenas.frasesDeTurno(ev)
    assert lineas[0] == [("El Jefe", amarillo), (" usó Llamarada de fuego.", None)]
    assert lineas[1] == [("Tanque", azul), (" esquivó el ataque.", None)]
    assert lineas[2][0][0] == "Golpe critico. " and ("120", rojo) in lineas[2]
    assert lineas[3] == [("Mago", azul), (" ha caído.", None)]

    ev = {"actor": "Picaro", "accion": "Le da a Mago una pocion de mana", "elem": None, "adelantado": False,
          "golpes": [], "curas": [], "muertos": []}
    assert escenas.frasesDeTurno(ev) == [[("Picaro", azul), (" le dio una pocion de mana a ", None),
                                          ("Mago", azul), (".", None)]]


def testMenuPorCategorias():
    opciones = [("basico", None, None), ("conjuro", 0, 0), ("conjuro", 0, 1), ("conjuro", 2, None),
                ("bloquear", None, None), ("pocion", "hpChica", 0), ("pocion", "hpChica", 2)]
    grupos = escenas.agruparOpciones(opciones)
    assert grupos["ataque"] == ("basico", None, None) and grupos["bloqueo"] == ("bloquear", None, None)
    assert grupos["magia"] == {0: [("conjuro", 0, 0), ("conjuro", 0, 1)], 2: [("conjuro", 2, None)]}
    # Cada poción junta a los aliados a los que se le puede dar
    assert grupos["objetos"] == {"hpChica": [("pocion", "hpChica", 0), ("pocion", "hpChica", 2)]}


def testAnimacionDeAtaque():
    # Primero avanza sin deformarse, luego se estira hacia atrás tomando impulso,
    # después hacia el frente ya en pose de ataque, y termina en su lugar.
    pasos = escenas.transformacionDeAtaque(escenas.finPasos / 2, 56)
    impulso = escenas.transformacionDeAtaque((escenas.finPasos + escenas.finImpulso) / 2, 56)
    golpe = escenas.transformacionDeAtaque((escenas.finImpulso + escenas.finGolpe) / 2, 56)
    final = escenas.transformacionDeAtaque(escenas.finRegreso, 56)

    assert pasos["dx"] == pytest.approx(28) and pasos["sx"] == 1.0 and not pasos["pose"]
    assert impulso["sx"] > 1 and impulso["ancla"] == "frente" and not impulso["pose"]
    assert golpe["sx"] > 1 and golpe["ancla"] == "atras" and golpe["pose"] and golpe["dx"] > 56
    assert final == {"dx": 0, "dy": 0, "sx": 1.0, "sy": 1.0, "ancla": "centro", "pose": False}


def elegirPrimeraActiva(combate):
    next(b for b in combate.botonesMenu if b.activo).alHacerClic()


def testUnaPartidaCompletaPorLasPantallas():
    # Recorre título, equipo, combate y resultados dando clics y teclas, y juega
    # hasta el final. En el combate alterna entre atacar y entrar al menú de magia.
    from grafico import pantallas
    j = juego.Juego()
    j.cuadro(0.016)
    assert isinstance(j.escena, pantallas.EscenaTitulo)
    assert [b.texto for b in j.escena.botones] == ["Jugar", "Entrenar jefe", "Opciones", "Salir"]
    clic(j, j.escena.botones[0].rect.center)
    assert isinstance(j.escena, escenas.EscenaEquipo)

    # Con el teclado: la mano se mueve con las flechas y Enter elige
    equipoEscena = j.escena
    assert not equipoEscena.botonPelear.activo
    tecla(j, pygame.K_RETURN)
    assert equipoEscena.elegidos == ["Guerrero"]
    tecla(j, pygame.K_RETURN)
    assert equipoEscena.elegidos == []
    equipo = ["Guerrero", "Mago", "Clerigo", "Picaro"]
    for rect, nombre, _ in equipoEscena.tarjetas:
        if nombre in equipo:
            clic(j, rect.center)
    assert equipoEscena.botonPelear.activo and equipoEscena.foco is equipoEscena.botonPelear
    tecla(j, pygame.K_RETURN)

    combate = j.escena
    assert isinstance(combate, escenas.EscenaCombate) and combate.nombres == equipo
    niveles, turnos = set(), 0
    inicio = time.time()
    while not combate.botonesFinal:
        assert time.time() - inicio < 150
        j.cuadro(0.1)
        if combate.cinematica is not None:
            # La cinematica de la segunda fase se salta con una tecla.
            tecla(j, pygame.K_SPACE)
            niveles.add("fase2")
        if not combate.botonesMenu:
            time.sleep(0.001)
            continue

        assert combate.nivelMenu == "raiz"
        textos = [b.texto for b in combate.botonesMenu]
        assert textos == ["1  Ataque", "2  Magia", "3  Bloqueo", "4  Objetos"]
        turnos += 1
        magia, objetos = combate.botonesMenu[1], combate.botonesMenu[3]

        if objetos.activo and turnos % 5 == 0:
            # Una poción se elige y luego se dice a quién va
            objetos.alHacerClic()
            assert combate.nivelMenu == "objetos"
            elegirPrimeraActiva(combate)
            assert combate.nivelMenu == "destino" and combate.botonesMenu[-1].texto.endswith("Atras")
            combate.botonesMenu[-1].alHacerClic()
            assert combate.nivelMenu == "objetos"
            elegirPrimeraActiva(combate)
            elegirPrimeraActiva(combate)
            niveles.add("objetos")
        elif magia.activo and turnos % 2 == 0:
            magia.alHacerClic()
            assert combate.nivelMenu == "magia" and combate.botonesMenu[-1].texto.endswith("Atras")
            # Escape regresa a la raiz y la mano vuelve a donde estaba
            tecla(j, pygame.K_ESCAPE)
            assert combate.nivelMenu == "raiz"
            magia.alHacerClic()
            elegirPrimeraActiva(combate)
            if combate.nivelMenu == "objetivo":
                # Una cura individual pide además a quién va, y también se puede regresar
                assert combate.botonesMenu[-1].texto.endswith("Atras")
                combate.botonesMenu[-1].alHacerClic()
                assert combate.nivelMenu == "magia"
                elegirPrimeraActiva(combate)
                if combate.nivelMenu == "objetivo":
                    elegirPrimeraActiva(combate)
            niveles.add("magia")
        else:
            elegirPrimeraActiva(combate)
        j.cuadro(0.01)

    assert "magia" in niveles
    res = combate.partida.resultado
    assert combate.vida == res["hp_equipo"] and combate.ronda == res["rondas"]
    assert combate.dialogo[0][0][0] in ("¡Victoria!", "Derrota")
    tecla(j, pygame.K_RETURN)
    resultados = j.escena
    assert isinstance(resultados, pantallas.EscenaResultados)
    for _ in range(5):
        j.cuadro(0.1)
    # Lo que muestra cuadra con lo que paso en el combate
    hecho = sum(e["hecho"] for e in resultados.porHeroe.values())
    assert hecho == combate.vidaJefeMax - max(0, res["hp_jefe"]) or res["hp_jefe"] > 0
    assert 0 <= resultados.evaluacion["nota"] <= 1
    clic(j, resultados.botones[1].rect.center)
    assert isinstance(j.escena, escenas.EscenaEquipo)


def testEscenariosDeCombate():
    pygame.display.set_mode((1, 1))
    # Las dos arenas existen y se recortan a la zona de la pelea sin deformarse
    for nombre in ("arena", "arena_fase2"):
        assert os.path.exists(recursos.rutaDe("escenarios", nombre))
        assert recursos.obtenerEscenario(nombre, (1280, 500)).get_size() == (1280, 500)
    assert recursos.obtenerEscenario("titulo", (1280, 500)).get_size() == (1280, 500)


def testCarreraHastaElJefe():
    # El que pega cuerpo a cuerpo llega hasta el jefe, pega ahi y vuelve a su lugar
    pasos, impulso, golpe, regreso = escenas.tiemposCarrera
    forma = escenas.transformacionDeAtaque((impulso + golpe) / 2, 400, escenas.tiemposCarrera, 60)
    assert forma["dx"] > 400 and forma["dy"] == 60 and forma["pose"]
    final = escenas.transformacionDeAtaque(regreso + 0.01, 400, escenas.tiemposCarrera, 60)
    assert (final["dx"], final["dy"]) == (0, 0)


def testProtecciones():
    # El motor anota en cada turno que protege a cada heroe, y coincide con
    # las reglas: bloquear dura hasta su siguiente turno, las mejoras de
    # defensa dos turnos suyos mas y el bloqueo total hasta el primer golpe.
    import random
    import genetico
    rng = random.Random(3)
    vistos = set()
    for semilla in range(40):
        crom = genetico.decodificar([rng.randint(0, 1) for _ in range(genetico.N_BITS)])
        registro = []
        m.simular(crom, m.armarEquipo(["Guerrero", "Tanque", "Clerigo", "Berserker"]), semilla, registro=registro)
        turnos = [ev for ev in registro if ev["tipo"] == "turno"]
        nombres = ["Guerrero", "Tanque", "Clerigo", "Berserker"]
        propios = {n: [] for n in nombres}
        for k, ev in enumerate(turnos):
            if ev["actor"] in propios:
                propios[ev["actor"]].append(k)
        for k, ev in enumerate(turnos):
            if ev["actor"] == "Jefe":
                # Al que le pega el jefe ya no le queda bloqueo total
                for nombre, _, _ in ev["golpes"]:
                    assert "total" not in ev["protecciones"][nombres.index(nombre)]
                continue
            j = nombres.index(ev["actor"])
            despues = [turnos[q] for q in propios[ev["actor"]] if q > k]
            if ev["accion"] == "Bloquea":
                vistos.add("bloqueo")
                assert "bloqueo" in ev["protecciones"][j]
                # Si en su siguiente turno vuelve a bloquear, la protección sigue
                if despues and despues[0]["accion"] != "Bloquea":
                    assert "bloqueo" not in despues[0]["protecciones"][j]
            if ev["accion"] in ("Guardia de acero", "Muralla"):
                vistos.add("defensa")
                assert "defensa" in ev["protecciones"][j]
                if len(despues) >= 2:
                    assert "defensa" in despues[0]["protecciones"][j] or despues[0]["accion"] in ("Guardia de acero", "Muralla")
                    if despues[0]["accion"] not in ("Guardia de acero", "Muralla") and despues[1]["accion"] not in ("Guardia de acero", "Muralla"):
                        assert "defensa" not in despues[1]["protecciones"][j]
            if ev["accion"] == "Bloqueo total":
                vistos.add("total")
                assert "total" in ev["protecciones"][j]
    assert vistos == {"bloqueo", "defensa", "total"}


def testCadaAtaqueTieneSuAnimacion():
    from grafico import galeria, recetas, animaciones
    pygame.display.set_mode((1, 1))
    # Los ataques del jefe y los conjuros de ataque de los heroes tienen receta propia
    for ataque in m.HABILIDADES:
        assert ataque["nombre"] in recetas.recetas, ataque["nombre"]
    for conjuro in m.conjurosMago + m.conjurosMagoPoderosos:
        assert conjuro["nombre"] in recetas.recetas, conjuro["nombre"]
    assert recetas.anchoCapa * animaciones.escala == escenas.ancho
    assert recetas.altoCapa * animaciones.escala == escenas.altoEscenario

    # Todo lo que puede pasar en un turno se anima de principio a fin sin
    # errores, el golpe llega antes de que termine y nada dura demasiado
    capas = animaciones.Capas(escenas.ancho, escenas.altoEscenario)
    origen, lejos = animaciones.Lugar(950, 190, 312), animaciones.Lugar(310, 123, 187)
    for quien, accion, elem, tipo in galeria.catalogo():
        esJefe = quien == "Jefe"
        yo, otro = (origen, lejos) if esJefe else (lejos, origen)
        objetivos = [otro] * (4 if tipo in ("area", "grupo") else 1)
        contexto = recetas.Contexto(accion, elem, yo, objetivos, 0.4, -1 if esJefe else 1, quien)
        if tipo in ("uno", "area"):
            animacion = recetas.crearAnimacion(contexto, escenas.esAtaqueFisico(accion))
        else:
            if tipo == "apoyo":
                contexto.objetivos = []
            animacion = recetas.crearApoyo(contexto)
        assert animacion is not None, accion
        assert 0 <= animacion.impacto <= animacion.duracion <= 4.0, accion
        pasos = 0
        while animacion.actualizar(1 / 20):
            capas.limpiar()
            animacion.dibujar(capas)
            animacion.velosActivos(), animacion.desplazamiento(), animacion.penumbra()
            pasos += 1
        assert pasos >= 5, accion


def testElTurnoEsperaASuAnimacion():
    from grafico import galeria
    pygame.display.set_mode((1, 1))
    escena = galeria.EscenaGaleria(juego.Juego())
    # Un golpe sencillo dura lo que la carrera; uno poderoso, bastante mas
    corto = escena.reproducir("Guerrero", "Ataque basico", None, "uno")
    largo = escena.reproducir("Jefe", "Cataclismo", 0, "area")
    assert corto < 1.2 < largo
    # Las vidas no cambian hasta el momento del impacto
    escena.reproducir("Guerrero", "Ataque basico", None, "uno")
    assert escena.pendientes and escena.pendientes[0]["falta"] > 0.4
    # El mago conjura desde su lugar y los demas corren hasta el jefe
    escena.reproducir("Mago", "Chispa", 0, "uno")
    assert "sosten" in escena.animacion and "carrera" not in escena.animacion
    escena.reproducir("Guerrero", "Tajo mayor", 0, "uno")
    assert "carrera" in escena.animacion


def testCinematicaDeLaSegundaFase():
    from grafico import galeria
    pygame.display.set_mode((1, 1))
    j = juego.Juego()
    escena = galeria.EscenaGaleria(j)
    escena.mostrarEvento({"tipo": "fase2", "objeto": "Amuleto de rayo", "nuevos": ["Tormenta"], "ronda": 3})
    cine = escena.cinematica
    assert cine is not None and cine.previa < cine.inicioGrito < cine.finRueda < cine.duracion
    # La rueda gira siempre hacia el mismo lado, se detiene en las puntas y la
    # boca solo se abre mientras grita
    angulos = [cine.angulo(t / 20) for t in range(int(cine.finRueda * 20))]
    assert all(b >= a - 3 for a, b in zip(angulos, angulos[1:]))
    paradas = [tr for tr in cine.tramos if tr[0] == "pausa"]
    assert len(paradas) >= 6 and all(tr[3] % 45 == 0 for tr in paradas)
    assert cine.apertura() == 0
    vista = set()
    while escena.cinematica is not None:
        escena.actualizar(1 / 15)
        escena.dibujar(j.lienzo)
        if escena.cinematica is not None:
            vista.add("retrato" if not escena.cinematica.enLaArena() else "arena")
            if escena.cinematica.apertura() > 10:
                vista.add("boca")
        assert escena.fase2 == (escena.cinematica is None or escena.cinematica.yaEsFase2())
    assert vista == {"retrato", "arena", "boca"} and escena.fase2

    # Una tecla brinca al destello final
    escena = galeria.EscenaGaleria(j)
    escena.mostrarEvento({"tipo": "fase2", "objeto": "Amuleto de rayo", "nuevos": ["Tormenta"], "ronda": 3})
    escena.manejarEvento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE, mod=0, unicode=" "))
    assert escena.cinematica.tiempo >= escena.cinematica.finRueda - 0.2


def testEntrenamientoGuardaAlJefe(tmp_path, monkeypatch):
    import entrenamiento
    monkeypatch.setattr(entrenamiento, "generaciones", 2)
    monkeypatch.setattr(entrenamiento, "tamPoblacion", 4)
    monkeypatch.setattr(entrenamiento, "combatesValidacion", 1)
    monkeypatch.setattr(entrenamiento, "archivoJefe", str(tmp_path / "jefe.json"))
    # Sin entrenar se usa el elegido del frente guardado
    jefe, entrenado = entrenamiento.jefeOptimo()
    assert not entrenado and "predisposicion" in jefe["crom"]

    avisos = []
    resultado = entrenamiento.entrenar(lambda tipo, datos: avisos.append(tipo), semilla=3)
    assert avisos == ["generacion", "generacion", "validando", "listo"]
    jefe, entrenado = entrenamiento.jefeOptimo()
    assert entrenado and jefe["crom"] == resultado["crom"]
    assert jefe["evaluaciones"] == 4 + 2 * 8
    assert 0 <= jefe["validacion"]["fitness"] <= 1


def testResultadosCalificanComoAptitud():
    from grafico import pantallas
    import narrar
    crom = m.reparar(next(j for j in narrar.cargarOCrearFrente() if j["elegido"])["crom"])
    for semilla in range(6):
        res = m.simular(crom, m.armarEquipo(["Guerrero", "Tanque", "Mago", "Clerigo"]), semilla)
        propia = pantallas.evaluacionDelCombate(res)
        oficial = m.calcular_fitness([res])
        for clave in ("margen", "duracion", "variedad"):
            assert propia[clave] == pytest.approx(oficial[clave])


def testTodosLosSonidosExisten(monkeypatch):
    # Recorre todas las animaciones y la cinematica anotando lo que pide sonar
    from grafico import galeria, animaciones, cinematica, recursos as r
    pygame.display.set_mode((1, 1))
    pedidos = set()
    monkeypatch.setattr(animaciones, "reproductor", [lambda nombre, volumen=1.0: pedidos.add(nombre)])
    monkeypatch.setattr(cinematica, "reproducirSonido", lambda nombre, volumen=1.0: pedidos.add(nombre))
    monkeypatch.setattr(escenas, "reproducirSonido", lambda nombre, volumen=1.0: pedidos.add(nombre))
    j = juego.Juego()
    for quien, accion, elem, tipo in galeria.catalogo():
        escena = galeria.EscenaGaleria(j, galeria.equipos[0] if quien == "Jefe" or quien in galeria.equipos[0] else galeria.equipos[1])
        animaciones.reproductor[0] = lambda nombre, volumen=1.0: pedidos.add(nombre)
        escena.azar.seed(1)
        for semilla in range(4):
            escena.azar.seed(semilla)
            escena.reproducir(quien, accion, elem, tipo)
            for _ in range(80):
                escena.actualizarLoQueSeVe(0.05)
    escena.mostrarEvento({"tipo": "fase2", "objeto": "Amuleto de rayo", "nuevos": ["Tormenta"], "ronda": 3})
    while escena.cinematica is not None:
        escena.actualizarLoQueSeVe(0.1)
    assert {"tajo", "rueda", "jefe_grito", "giro_rapido", "explosion"} <= pedidos
    for nombre in pedidos:
        assert r.rutaDeSonido(nombre) is not None, nombre
    for tema in r.temasDeMusica:
        assert r.rutaDeSonido(os.path.join("musica", tema)) is not None, tema
