Jefe RPG evolutivo

Un algoritmo genético binario que diseña jefes para un RPG por turnos. Cada jefe es un cromosoma de 44 bits. Un motor de combate lo enfrenta 30 veces a cada uno de 4 equipos, y el AG busca el jefe que da el combate más parejo: que el equipo gane entre 40% y 60% de las veces, en unas 10 rondas, y termine con poca vida.

Proyecto final de Cómputo Evolutivo, CETYS Universidad.

Requisitos
Python 3.10 o más reciente
pytest y matplotlib
Instalación

Windows (PowerShell):

powershell
git clone <url-del-repositorio>
cd <carpeta-del-repositorio>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

macOS o Linux:

bash
git clone <url-del-repositorio>
cd <carpeta-del-repositorio>
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
Cómo probarlo

Los comandos van en la terminal, no dentro de Python. Todo usa semillas fijas, así que tus números deben coincidir con los de esta tabla. Si no coinciden, algún archivo no está actualizado.

Paso	Comando	Qué debe salir	Tiempo
1	python -m pytest -q	33 passed	1 s
2	python genetico.py	Termina con F = 0.8134 y puntos [294, 171, 188, 347]	7 s
3	python narrar.py resumen	Un combate, una línea por ronda	1 s
4	python jugar.py	Juegas tú contra el mejor jefe	lo que dure la partida
5	python comparar.py	convergencia.png y resultados.csv (AG contra búsqueda aleatoria)	5 min

Si el paso 1 falla, no sigas: algo está roto.

Jugar

python jugar.py muestra los stats de los héroes y te deja elegir uno de los 4 equipos. En cada turno escribes el número de la acción. Solo aparecen acciones legales, con el daño exacto al lado. python jugar.py rapido quita las pausas.

El juego usa exactamente las mismas reglas con las que el AG calificó al jefe. Los porcentajes que salen al inicio se recalculan cada vez con la función objetivo; no están escritos a mano.

Archivos
Archivo	Qué hace
motor.py	Reglas del juego, combate, función objetivo F y función de costo C = 1 − F
genetico.py	AG binario de 44 bits (selección por rango, cruce de un punto, mutación, elitismo) y búsqueda aleatoria
comparar.py	AG contra búsqueda aleatoria, 10 repeticiones, mismo presupuesto de evaluaciones
narrar.py	Cuenta un combate turno por turno
jugar.py	Modo interactivo en la terminal
calibrar.py	Histograma de la tasa de victoria de 2000 jefes aleatorios
test_motor.py, test_genetico.py	33 pruebas con los valores esperados calculados a mano
mejor_jefe.json	El mejor jefe de una corrida del AG; si lo borras, se vuelve a crear
Función objetivo y función de costo
F = f_win × (0.5·margen + 0.25·duración + 0.25·variedad)
C = 1 − F        (el AG minimiza C)
f_win = 1 − 2d, con d = distancia de la tasa de victoria del equipo a la banda 40–60%
margen: qué tan cerca de 20% de HP termina el equipo cuando gana
duración: qué tan cerca de 10 rondas dura el combate
variedad: entropía de Shannon del uso de las 4 habilidades del jefe, entre 2 bits

Cada jefe se evalúa contra los 4 equipos y se toma el peor F, para que sea parejo con cualquier equipo que elija el jugador.

Resultados iniciales

10 repeticiones por método, 610 evaluaciones cada una:

Método	F final	F con combates nuevos
AG, selección por rango	0.886 ± 0.017	0.687
AG, torneo	0.860 ± 0.026	0.723
AG, ponderación por costo	0.860 ± 0.041	0.697
Búsqueda aleatoria	0.787 ± 0.044	0.549

El AG con selección por rango supera a la búsqueda aleatoria (t = 6.37; t = 2.71 con combates nuevos). La limitación principal es el sobreajuste a las semillas de combate.
