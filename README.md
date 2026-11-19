# Jefe RPG evolutivo

Dos algoritmos evolutivos que diseñan jefes para un RPG por turnos: un algoritmo genético binario de un solo objetivo y NSGA-II, su versión multiobjetivo. Un motor de combate enfrenta a cada jefe contra los 15 equipos que puede armar el jugador, y los algoritmos buscan el jefe que da el combate más parejo: que el equipo gane entre 40% y 60% de las veces, en unas 10 rondas, y termine con poca vida.

Proyecto final de Cómputo Evolutivo, CETYS Universidad.

## Requisitos

- Python 3.10 o más reciente
- pytest y matplotlib

## Instalación

Windows (PowerShell):

```powershell
git clone <url-del-repositorio>
cd <carpeta-del-repositorio>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS o Linux:

```bash
git clone <url-del-repositorio>
cd <carpeta-del-repositorio>
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Cómo probarlo

Los comandos van en la terminal. Todo usa semillas fijas, así que los números deben coincidir con los de esta tabla.

| Paso | Comando | Qué debe salir | Tiempo |
|---|---|---|---|
| 1 | `python -m pytest -q` | 63 passed | 5 s |
| 2 | `python genetico.py` | Termina con F = 0.7491 | 30 s |
| 3 | `python nsga2.py` | Un frente de 9 jefes con hipervolumen 0.2734 | 30 s |
| 4 | `python narrar.py resumen` | Un combate, una línea por ronda | 1 s |
| 5 | `python jugar.py` | Juegas tú contra el mejor jefe | lo que dure la partida |
| 6 | `python comparar.py` | convergencia.png y resultados.csv | 10 min |

Si el paso 1 falla, no sigas: algo está roto.

## El juego

Cuatro héroes contra un jefe, por turnos. El jugador arma su equipo con 4 de las 6 clases.

Todos los personajes tienen seis atributos: vida, ataque físico, defensa física, ataque mágico, defensa mágica y velocidad. Cada clase reparte 600 puntos entre ellos; el maná va aparte.

| Clase | Perfil | Conjuros |
|---|---|---|
| Guerrero | Equilibrado en todo | Guardia de acero (sube su defensa dos turnos) y dos tajos mágicos de elemento aleatorio |
| Tanque | Mucha vida y defensa, poco ataque y velocidad | Muralla (sube su defensa dos turnos) y Bloqueo total (anula un ataque) |
| Mago | Mucho ataque mágico, poca vida y defensa | 3 conjuros de una lista de 16 y 1 de una lista de 8 poderosos, sin repetir elemento |
| Clérigo | Equilibrado, su magia cura | Curación menor, mayor y en grupo |
| Pícaro | Ataque físico y velocidad altos, defensa baja | Dos ataques que se adelantan a todos en la ronda |
| Berserker | Mucho ataque físico, poca defensa mágica | Furia (sube su ataque dos turnos) y Furia desatada (sube su ataque y pega) |

Reglas principales:

- **Ataques físicos y mágicos.** Los físicos usan ataque y defensa físicos, varían entre x0.80 y x1.20 y pueden salir críticos (x1.60). Guerrero y Pícaro tienen más probabilidad de crítico y su mínimo es x0.90. Los mágicos usan los atributos mágicos, varían entre x0.85 y x1.00, no tienen crítico y llevan un elemento.
- **Elementos y objetos.** Hay 8 elementos: fuego, agua, viento, tierra, planta, rayo, luz y oscuridad. Un elemento es solo una etiqueta: lo que importa son los objetos equipados, que dan bonos como +20% de ataque de fuego o -25% de defensa contra agua. Hay 16 objetos, dos por elemento.
- **Velocidad.** Decide el orden de los turnos. Quien es más rápido que su atacante puede esquivar: la probabilidad crece con la diferencia de velocidad, de 1% a 15%.
- **Maná.** Todos los conjuros cuestan maná y el ataque básico es gratis. Solo Mago y Clérigo lo recuperan poco a poco.
- **Bloquear.** Cualquiera puede gastar su turno en bloquear y recibir la mitad del daño hasta su siguiente turno.
- **Pociones.** El equipo comparte dos pociones chicas y una grande de vida, y lo mismo de maná. No hay forma de revivir.

El jefe reparte 1500 puntos entre sus seis atributos y lleva un objeto. No gasta maná y sus críticos son menos probables.

- **Cola de ataques.** Tiene 8 ataques tomados de un banco de 32, en fila. Solo puede elegir entre los primeros 4; el que usa pasa al final de la fila.
- **Ataques de área y de carga.** Los de área pegan menos a cada héroe pero suman más daño. Cuatro ataques del banco gastan un turno en cargar y pegan muy fuerte al siguiente, lo que le da tiempo al equipo de bloquear.
- **Fase 2.** Al bajar de la mitad de su vida cambia de objeto, dos ataques de su cola se reemplazan por otros y sus atributos se mueven un poco hacia arriba o hacia abajo.
- **Predisposición.** Elige a quién atacar con una probabilidad por clase que viene en sus genes.
- **Bloqueo.** También puede gastar un turno en bloquear.

Al equipo lo controla un jugador automático durante la evaluación (`heuristico.py`). En `jugar.py` lo controlas tú, con las mismas reglas.

## Archivos

| Archivo | Qué hace |
|---|---|
| `motor.py` | Fachada: junta los módulos de abajo para que los scripts usen `import motor` |
| `reglas.py` | Elementos, objetos y fórmulas de daño |
| `clases.py` | Las seis clases, sus conjuros y los 15 equipos |
| `jefe.py` | Puntos del jefe, banco de 32 ataques, fase 2 y reparación del cromosoma |
| `heuristico.py` | Jugador automático |
| `combate.py` | Simulación de un combate |
| `aptitud.py` | Función objetivo F y función de costo C = 1 − F |
| `genetico.py` | Algoritmo genético binario (rango, costo o torneo; cruce de un punto; mutación; elitismo) y búsqueda aleatoria |
| `nsga2.py` | NSGA-II: ordenamiento no dominado, distancia de crowding, torneo binario, restricción e hipervolumen |
| `comparar.py` | Algoritmo genético contra búsqueda aleatoria, 10 repeticiones, mismo presupuesto |
| `narrar.py` | Cuenta un combate turno por turno |
| `jugar.py` | Modo interactivo en la terminal |
| `calibrar.py` | Histograma de la tasa de victoria de jefes aleatorios |
| `test_motor.py`, `test_genetico.py`, `test_nsga2.py` | Pruebas con los valores esperados calculados a mano |
| `mejor_jefe.json` | El mejor jefe de una corrida; si lo borras, se vuelve a crear |

## Cromosoma

134 bits:

| Tramo | Bits | Qué guarda |
|---|---|---|
| 6 atributos | 6 × 4 | Proporción del presupuesto de 1500 puntos |
| 2 objetos | 2 × 4 | Objeto de la fase 1 y de la fase 2 |
| 8 ataques | 8 × 5 | La cola inicial, con índices del banco de 32 |
| 8 pesos | 8 × 2 | Qué tanto prefiere cada ataque de la cola |
| 2 cambios de fase 2 | 2 × (3 + 5) | Qué posición de la cola cambia y por cuál ataque |
| 5 ajustes de fase 2 | 5 × 2 | Cómo se mueve cada atributo, menos la vida |
| 6 predisposiciones | 6 × 3 | Preferencia por atacar a cada clase |
| Bloqueo | 2 | Probabilidad de bloquear en un turno: 0, 5, 10 o 15% |

Una función de reparación hace válida cualquier cadena de bits: los puntos suman 1500, no hay ataques repetidos en la cola y los ataques que entran en la fase 2 no repiten a los que ya están.

## Función objetivo y función de costo

```
F = f_win × (0.5·margen + 0.25·duración + 0.25·variedad)
C = 1 − F        (el algoritmo minimiza C)
```

- `f_win = 1 − 2d`, con d = distancia de la tasa de victoria del equipo a la banda 40–60%
- margen: qué tan cerca de 20% de vida termina el equipo cuando gana
- duración: qué tan cerca de 10 rondas dura el combate
- variedad: entropía de Shannon del uso de las habilidades del jefe, entre su máximo

Cada jefe pelea 10 combates contra cada uno de los 15 equipos (150 en total) y su F es el promedio de los 15.

## NSGA-II

F junta tres medidas en un solo número con pesos que escogimos a mano. NSGA-II trabaja con las medidas por separado y entrega un frente de Pareto: un conjunto de jefes donde ninguno es mejor que otro en todo.

Objetivos, los tres a minimizar:

| Objetivo | Qué mide |
|---|---|
| Desbalance | Qué tan lejos queda la tasa de victoria de cada equipo de 50% |
| Holgura | El equipo gana con mucha más vida que el 20% ideal (1 − margen) |
| Desajuste de duración | Los combates duran mucho más o mucho menos de 10 rondas (1 − duración) |

La variedad no entra como objetivo. Desde que el jefe ataca con una cola, casi cualquier jefe la tiene arriba de 0.9, y como objetivo solo llenaba el frente de jefes malos que ganaban una centésima de variedad.

Restricción: un jefe solo es aceptable si, en promedio, la tasa de victoria de los equipos queda a no más de 0.10 de la banda 40–60%. Se usa dominancia con restricciones: el que cumple le gana al que no, y entre dos que no cumplen gana el que viola menos. Sin la restricción el frente se llenaba de jefes con la duración perfecta que ningún equipo podía vencer.

El cromosoma, el cruce de un punto y la mutación son los mismos del algoritmo genético. Cambia la selección: ordenamiento no dominado, distancia de crowding y torneo binario, y los sobrevivientes se escogen entre padres e hijos juntos.

**Semillas rotativas.** Para atacar el sobreajuste, cada generación pelea combates distintos y los padres se vuelven a evaluar junto con sus hijos. Cuesta el doble de evaluaciones por generación. El algoritmo genético de un solo objetivo también lo puede usar, con `rotarSemillas=True`.

## Resultados del algoritmo genético

10 repeticiones por método, 610 evaluaciones cada una:

| Método | F final | F con combates nuevos |
|---|---|---|
| AG, selección por rango | 0.751 ± 0.015 | 0.606 |
| AG, torneo | 0.743 ± 0.019 | 0.635 |
| AG, ponderación por costo | 0.757 ± 0.015 | 0.629 |
| Búsqueda aleatoria | 0.698 ± 0.024 | 0.620 |

Con los combates de la búsqueda, los tres métodos del algoritmo genético superan a la búsqueda aleatoria. Con combates nuevos la ventaja desaparece: el algoritmo aprende las 10 semillas de combate con las que evalúa. Con el cromosoma de 134 bits el sobreajuste pesa más que antes y es lo siguiente que hay que atacar.
