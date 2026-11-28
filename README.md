Jefe RPG evolutivo

Proyecto final de Cómputo Evolutivo, CETYS Universidad.

Dos algoritmos evolutivos diseñan al jefe de un RPG por turnos: un algoritmo genético binario y NSGA-II, su versión multiobjetivo. Cada jefe pelea contra los 15 equipos que puede armar el jugador y los algoritmos buscan el que da el combate más parejo: que el equipo gane entre 40% y 60% de las veces, en unas 14 rondas, y termine con poca vida. El jefe que salió se puede jugar en una versión con ventana, música y sonido.


Cómo correrlo

Necesitas Python 3.10 o más nuevo; lo más seguro es 3.12 o 3.13. Si no lo tienes, se descarga de python.org. En Windows, al instalarlo marca la casilla "Add python.exe to PATH".

Descomprime el zip. A veces queda una carpeta dentro de otra: entra hasta la que tiene juego.py y requirements.txt y abre una terminal ahí. En Windows puedes escribir powershell en la barra de direcciones del explorador y darle Enter.

En Windows, con PowerShell:

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python juego.py

Si PowerShell no te deja activar el entorno, corre esto antes y vuelve a intentar (solo cambia esa ventana):

    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

En macOS o Linux:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    python juego.py

En Ubuntu, si falla el primer comando, instala antes el paquete del entorno con sudo apt install python3-venv.

La instalación se hace una sola vez. Las siguientes veces basta con abrir la terminal en la carpeta, activar el entorno (el segundo comando) y correr python juego.py.

El juego se maneja con las flechas y Enter (o Z) para elegir, Escape (o X) para regresar, o con el ratón. F11 cambia a pantalla completa.


Otras cosas que se pueden correr

Todo usa semillas fijas, así que los números deben salir iguales. Los tiempos son de una máquina con 2 núcleos.

python -m pytest -q corre las 95 pruebas. Debe decir 95 passed en menos de un minuto. Si algo falla aquí, lo demás no es confiable.

python genetico.py corre el algoritmo genético y termina con F = 0.8110 en menos de un minuto.

python nsga2.py corre NSGA-II y entrega un frente de 7 jefes con hipervolumen 0.4268, también en menos de un minuto.

python narrar.py resumen cuenta un combate, una línea por ronda.

python jugar.py es la versión de terminal: eliges un jefe del frente y peleas contra él con las mismas reglas.

python entrenamiento.py entrena un jefe nuevo con NSGA-II sin abrir la ventana y lo guarda en jefe_optimo.json. Tarda unos dos minutos y medio, y cada vez sale un jefe distinto porque cambia la semilla.

python comparar.py corto y python comparar.py repiten el experimento del reporte con el presupuesto corto (unos 12 minutos) y el largo (unos 40). Dejan sus tablas en resultados_corto.csv y resultados_largo.csv y sus gráficas en comparacion_corto.png, comparacion_largo.png y frente.png.

python calibrar.py mide qué tanto cambia la tasa de victoria de un equipo por llevar cada clase.

python -m grafico.galeria muestra cualquier animación de ataque suelta.


El juego

Son cuatro héroes contra un jefe. El jugador arma su equipo con 4 de 6 clases, lo que da 15 equipos posibles. Todos los personajes tienen seis atributos: vida, ataque físico, defensa física, ataque mágico, defensa mágica y velocidad. Cada clase reparte 600 puntos entre ellos y el maná va aparte.

El Guerrero es equilibrado y tiene una guardia y dos tajos mágicos. El Tanque tiene mucha vida y defensa, provoca al jefe para que lo ataque más seguido y se protege con Muralla y Bloqueo total. El Mago tiene mucho ataque mágico pero poca vida, y lleva tres conjuros normales y uno poderoso, sin repetir elemento. El Clérigo cura a uno o a todos. El Pícaro es rápido y tiene dos ataques que se adelantan a todos en la ronda. El Berserker pega muy fuerte, pero se defiende mal de la magia, y tiene dos furias que le suben el ataque.

En cada ronda los cuatro héroes eligen qué hacer con lo que se sabe en ese momento y luego se resuelve todo: primero los ataques con prioridad y después todos por velocidad, el jefe incluido. Los ataques físicos varían un poco y pueden salir críticos; los mágicos llevan un elemento. Hay 8 elementos y 16 objetos que dan bonos de ataque o de defensa por elemento. Quien es más rápido que su atacante puede esquivar. Cualquiera puede bloquear para recibir la mitad del daño, y el equipo comparte sus pociones: tres chicas y dos grandes de vida, y dos chicas y una grande de maná. No hay forma de revivir.

El jefe reparte 1500 puntos entre sus seis atributos y lleva un objeto. Ataca con una cola de 8 ataques tomados de un banco de 32: solo puede elegir entre los primeros 4 y el que usa pasa al final. Los ataques de área pegan a todos pero salen poco, y cuatro del banco gastan un turno en cargar y pegan muy fuerte al siguiente. Cuando baja de la mitad de su vida entra a su segunda fase: la ronda se corta ahí, cambia de objeto, dos ataques de su cola se reemplazan y sus atributos se mueven un poco. También tiene una preferencia por atacar a ciertas clases. El jefe no bloquea: cuando podía hacerlo, los algoritmos aprendían a usar el bloqueo para alargar los combates en lugar de atacar mejor, y por eso se quitó.

Durante la evaluación al equipo lo controla un jugador automático en el que cada clase juega su papel. El Clérigo cura en cuanto alguien baja de 80% de vida, el Mago vive de su magia y guarda su conjuro poderoso para cuando conviene, el Tanque mantiene su defensa arriba, y el Guerrero, el Pícaro y el Berserker usan sus técnicas siempre que les alcanza el maná. Contra jefes al azar el Clérigo cura en 64% de sus turnos, el Mago lanza magia en 86% de los suyos y el Guerrero usa sus tajos en 46%.

Antes de optimizar se calibraron las clases para que los 15 equipos tuvieran una fuerza parecida. Al principio el efecto de una clase sobre la tasa de victoria de su equipo iba de −0.22 a +0.19; después del ajuste ninguna lo mueve más de 0.04, y contra 500 jefes al azar los equipos ganan entre 43% y 55% de las veces.


El juego con ventana

python juego.py abre la pantalla de título con cuatro opciones: Jugar, Entrenar jefe, Opciones y Salir.

En Jugar se arma el equipo y se pelea contra el último jefe que se entrenó, o si todavía no hay ninguno, contra el que eligió NSGA-II en la corrida guardada en frente.json. El combate usa exactamente el mismo motor que la evaluación: corre aparte y se detiene cada vez que le toca decidir al jugador, y una de las pruebas comprueba combate por combate que el juego y la evaluación dan lo mismo. Cada ataque tiene su animación, el jefe tiene una cinemática al entrar a su segunda fase y al final aparece una pantalla con lo que hizo cada héroe y cómo calificaría la función objetivo ese combate.

En Entrenar jefe corre NSGA-II en vivo, con el hipervolumen de cada generación y la población a la vista. Al terminar toma los cinco mejores del frente, los vuelve a medir con combates nuevos, se queda con el mejor y lo guarda para la siguiente partida.

La música se compuso con código y se tocó con FluidSynth y el banco de sonidos libre FluidR3_GM, y los efectos se sintetizaron igual. Todos los archivos ya vienen listos en recursos/sonidos, así que no hace falta instalar nada más para escucharlos. El volumen se guarda en opciones.json.


Cómo se evalúa a un jefe

El jefe es un cromosoma de 132 bits. Los primeros 24 son sus seis atributos, cada uno con 4 bits; luego vienen 8 bits para el objeto de cada fase, 40 para su cola de 8 ataques, 16 para el peso de cada ataque, 16 para los dos cambios de su segunda fase, 10 para cómo se ajustan sus atributos en esa fase y 18 para su preferencia por cada clase. Una función de reparación convierte cualquier cadena de bits en un jefe válido: los puntos siempre suman 1500 y no hay ataques repetidos.

La función objetivo es F = f_win × (0.5·margen + 0.25·duración + 0.25·variedad), y el algoritmo genético minimiza el costo C = 1 − F. f_win vale 1 si la tasa de victoria del equipo está entre 40% y 60% y baja conforme se aleja; el margen mide qué tan cerca de 20% de vida termina el equipo cuando gana; la duración es una campana centrada en 14 rondas, y la variedad es la entropía de Shannon del uso de sus ataques. Cada jefe pelea 10 combates contra cada uno de los 15 equipos y su F es el promedio.

NSGA-II no junta todo en un número. Trabaja con tres objetivos a minimizar: el desbalance, que mide qué tan lejos de 50% queda cada equipo; la holgura, que es 1 menos el margen, y el desajuste de duración, que es 1 menos la duración. Además pide que la tasa de victoria promedio no quede a más de 0.10 de la banda de 40 a 60%. Entrega un frente de jefes donde ninguno es mejor que otro en todo.

Si siempre se evalúa con los mismos combates, los algoritmos aprenden esos combates en lugar de aprender a hacer buenos jefes. Por eso los dos pueden usar semillas rotativas: cada generación pelea combates nuevos y se vuelve a evaluar a toda la población.


Resultados

Cada método se corrió 10 veces y al final el jefe que entregó cada corrida se volvió a medir con 30 combates por equipo que nadie vio durante la búsqueda. Esa es la nota que cuenta.

Con 1830 evaluaciones, el algoritmo genético con semillas rotativas entregó jefes con F = 0.775 ± 0.020, contra 0.709 ± 0.032 de una búsqueda aleatoria con el mismo presupuesto. La prueba t de Welch da 5.64 y sus 10 corridas quedaron arriba de la media aleatoria. Le siguen el algoritmo genético con semillas fijas (0.756), NSGA-II con semillas rotativas (0.755) y NSGA-II con semillas fijas (0.726). Con el presupuesto corto de 630 evaluaciones el orden es el mismo y el algoritmo genético con semillas rotativas llega a 0.768. Para comparar, un jefe generado al azar vale en promedio 0.319 y el 87% queda fuera de la banda.

Rotar las semillas es lo que más ayuda: con semillas fijas el algoritmo genético cree tener 0.826 durante la búsqueda pero baja a 0.756 con combates nuevos. NSGA-II quedó por debajo del algoritmo genético, probablemente por el ruido de sus tres objetivos, pero a cambio entrega un frente para escoger.

El jefe del juego salió del frente de NSGA-II. Con 450 combates nuevos tiene F = 0.780, el equipo le gana en promedio el 46% de las veces, los combates duran 13 rondas y 8 de los 15 equipos quedan dentro de la banda. La duración es el término más difícil de cumplir: según el equipo, los combates tardan entre 9 y 17 rondas.

Lo que queda pendiente: 10 combates por equipo miden la tasa de victoria con mucho ruido, 10 corridas por método son pocas para diferencias chicas, y el jugador automático no planea a futuro, así que un jefe parejo contra él no tiene por qué serlo contra una persona.


Cómo está organizado

motor.py junta todo el motor para que los demás archivos solo tengan que importarlo. Las reglas están en reglas.py, las clases y los 15 equipos en clases.py, el jefe y su reparación en jefe.py, el jugador automático en heuristico.py, la simulación de un combate en combate.py y la función objetivo en aptitud.py.

genetico.py tiene el algoritmo genético y la búsqueda aleatoria, nsga2.py tiene NSGA-II, comparar.py corre el experimento final y calibrar.py mide el efecto de las clases. narrar.py cuenta combates, jugar.py es la versión de terminal y entrenamiento.py entrena al jefe del juego.

juego.py abre el juego con ventana, y todo lo que usa está en la carpeta grafico: pantallas, escenas, animaciones, la cinemática de la segunda fase y el puente con el motor. Ahí mismo, poses.py genera las poses de los personajes a partir de las imágenes en recursos/personajes/base. El arte, la música y los sonidos están en recursos.

frente.json guarda el frente de la corrida de NSGA-II y mejor_jefe.json el jefe elegido de ese frente; si se borran, se vuelven a crear. Las pruebas están en los cuatro archivos test_.


Cómo se llegó aquí

El proyecto empezó en el segundo avance con cuatro héroes fijos, un jefe de 44 bits y un algoritmo genético que calificaba al jefe con el peor de cuatro equipos. A partir de ahí se separó el motor en módulos, se agregaron las seis clases con sus conjuros, el jefe con su cola de ataques y su segunda fase, NSGA-II con las semillas rotativas, el experimento con validación y la calibración de las clases. Al final se pasó a rondas planeadas con un objetivo de 14 rondas, se quitó el bloqueo del jefe, cada clase empezó a jugar su papel y se hizo la versión con ventana. En cada paso el repositorio quedó funcionando y con sus pruebas pasando, de 33 pruebas al inicio a las 95 de ahora.
