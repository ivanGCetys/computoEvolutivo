# Motor v0.1: calibración y hallazgos (13 de octubre de 2026)

Etiquetas: **[calculado]** = salió de una cuenta o de la simulación; **[estimado]** = juicio con números aproximados; **[supuesto]** = decisión de diseño, no una cuenta.

## 1. Qué contiene esta versión

- `motor.py`: el motor completo, 316 líneas con comentarios. Expone `simular(cromosoma, equipo, semilla)`, `evaluar(...)`, `calcular_fitness(...)` y `reparar(...)`. No imprime nada; la misma semilla da el mismo combate.
- `test_motor.py`: 16 pruebas con el valor esperado calculado a mano en cada comentario. Todas pasan. Se corren con `python -m pytest -q`.
- `calibrar.py`: simula jefes aleatorios y muestra la distribución de la tasa de victoria.

Decisiones que aceptaste y que ya están en el código:
- Poderes de habilidades: Zarpazo 0.8, Golpe pesado 1.6 (cooldown 2), Ráfaga 1.2 con elemento, Tormenta 1.8 con elemento (cooldown 2), Onda 0.5 a los 4 (cooldown 1), Guardia (recibe ×0.5), Presa débil 1.0 (×1.5 si el objetivo está bajo 50% de HP, cooldown 1).
- Fitness = f_win × (0.5·margen + 0.25·duración + 0.25·variedad), con f_win = 1 − 2·distancia a la banda.
- Sin veneno, sin bomba, sin poción de SP. La fase 2 solo cambia el elemento.

## 2. Hallazgo 1: la escala original era inviable, y la recalibré

Con la escala original (ATK = DEF = puntos, HP = puntos × 10), **1,996 de 2,000 jefes aleatorios ganan el 100% de los combates** [calculado, 30 combates por jefe]. Incluso un jefe con el ATK mínimo aniquila al equipo en unas 12 rondas. El fitness sería 0 para casi toda la población inicial, y el AG no tendría pendiente que seguir.

Probé 54 combinaciones de escala. La que reparte mejor las tasas de victoria es:

| Atributo | Fórmula | Rango |
|---|---|---|
| HP | puntos × 3 | 300 a 1500 |
| ATK | puntos // 2 | 50 a 250 |
| DEF | puntos // 3 | 33 a 166 |
| VEL | puntos / 10 (sin cambio) | 10 a 50 |

**Esto cambia un número del briefing (HP × 10 → × 3).** Lo hice porque acordamos que la simulación decidiera la escala, y ninguna combinación con HP × 10 funcionó: la mejor dejaba el 64% de los jefes en tasa de victoria 0. Se revierte cambiando 3 constantes al inicio de la sección 3 de `motor.py`.

Distribución de la tasa de victoria del equipo con la escala calibrada [calculado, 2,000 jefes × 30 combates, 4 segundos en total, 0.07 ms por combate]:

| 0% | (0, 10%) | 10 a 30% | 30 a 50% | 50 a 70% | 70 a 90% | 90 a 100% | 100% |
|---|---|---|---|---|---|---|---|
| 321 | 165 | 315 | 257 | 243 | 239 | 205 | 255 |

Mediana de la tasa de victoria: 0.43. Mediana de duración: 10.7 rondas. El 84% de los jefes tiene fitness > 0, y casi ningún combate llega al tope de 40 rondas. Confianza **alta** en que esta escala da un paisaje con pendiente. Confianza **media** en que sea la mejor posible: solo exploré una rejilla.

## 3. Cuentas a mano: tres jefes extremos y el balanceado

Daño del equipo por ronda contra el jefe [calculado]. En las primeras 2 o 3 rondas casi todos usan físico fuerte; después, básico. Daño = ATK × poder × 100/(100 + DEF). El jefe es de viento, así que Hielo usa magia (×1.5).

| Jefe | HP / ATK / DEF | Equipo, rondas 1-2 | Equipo, con básico | Rondas para matarlo (rango) | Simulación (500 combates) |
|---|---|---|---|---|---|
| Todo ATK | 501 / 250 / 55 | 194 | 93 | 2.6 a 5.4 | p = 0.26, 6.3 rondas |
| Todo HP | 1500 / 83 / 55 | 194 | 93 | 7.7 a 16.1 | p = 0.38, 13.2 rondas |
| Todo DEF | 501 / 83 / 166 | 114 | 55 | 4.4 a 9.1 | p = 0.89, 9.3 rondas |
| Balanceado | 750 / 125 / 83 | 164 | 79 | 4.6 a 9.5 | p = 0.16, 10.8 rondas |

Daño del jefe por golpe [calculado]. Un jefe de viento apunta a Tierra (DEF 60, débil al viento); uno de fuego apunta a Hielo (DEF 30).

| Jefe | Zarpazo / Golpe / Ráfaga / Tormenta, de viento contra Tierra (380 HP) | Lo mismo, de fuego contra Hielo (240 HP) |
|---|---|---|
| ATK 250 | 125 / 250 / 281 / **421** | 153 / **307** / **346** / **519** |
| ATK 125 | 62 / 125 / 140 / 210 | 76 / 153 / 173 / **259** |
| ATK 83 | 41 / 83 / 93 / 140 | 51 / 102 / 114 / 172 |

Las cifras en negritas matan de un golpe. Los cuatro jefes tienen las mismas 4 habilidades (Zarpazo, Golpe, Ráfaga, Tormenta) con pesos iguales.

**La relación que hace sensible la tasa de victoria** [calculado y estimado]:
- Rondas que tarda el equipo en matar al jefe: T_eq ≈ HP_jefe · (100 + DEF_jefe)/100 ÷ daño bruto del equipo (≈ 300 por ronda al principio, ≈ 150 después).
- Rondas que tarda el jefe en matar al equipo: T_jefe ≈ HP efectivo del equipo ÷ daño del jefe por turno. El HP efectivo del equipo es 1130, más unas 6 curaciones y 3 pociones, menos el autodaño del físico fuerte.
- La tasa de victoria se vuelve sensible a los genes cuando el jefe "promedio" del espacio tiene T_eq ≈ T_jefe ≈ 10. Eso es lo que logra la escala calibrada, y por eso la mediana es 0.43 y la duración 10.7 rondas.

## 4. ¿Qué genes importan? Hay epistasis real

Medí desde un jefe balanceado, con 300 combates por variante. Esta prueba se corrió con la escala calibrada antes de redondear ATK y DEF a enteros; los resultados casi no cambian [calculado].

**Elemento de fase 1:** la tasa de victoria del equipo va de **0.06 (fuego) a 0.69 (viento)**. El jefe de fuego mata al curandero, como predijimos.

**Combinación de 4 habilidades** (las 35 posibles): va de **0.16** (Golpe, Ráfaga, Tormenta, Presa) a **0.99** (Zarpazo, Golpe, Onda, Guardia).

**Interacción Onda × Presa** (tasa de victoria del equipo; las otras dos habilidades son Zarpazo y Ráfaga):

| | Sin Presa | Con Presa |
|---|---|---|
| Sin Onda | 0.38 | 0.44 |
| Con Onda | 0.88 | 0.78 |

La interacción es 0.78 − 0.88 − 0.44 + 0.38 = **−0.16**, unos 3 errores estándar. Es real.

**Elemento de fase 1 × fase 2:** la tabla de 4 × 4 no es aditiva. Por ejemplo, hielo → viento da 0.79, mientras que hielo → hielo da 0.45. El elemento de fase 2 importa, y su efecto depende del de fase 1.

## 5. Hallazgo 2, el más importante: la búsqueda aleatoria casi empata con el AG

Con el fitness acordado y un solo equipo:
- La búsqueda aleatoria encuentra un jefe con fitness ≥ 0.85 en **10 a 18 evaluaciones**, en las tres dificultades [calculado].
- Con 2,000 evaluaciones, el mejor jefe aleatorio, reevaluado con 400 combates, queda **a entre 0.004 y 0.016 del techo** que encontré con búsqueda local [calculado].
- El techo de la banda media es el jefe balanceado: puntos 251/254/252/243, fitness ≈ 0.93.

Para medirlo mejor escribí un AG desechable. Está en mi espacio de trabajo y **no es tu AG**. Comparé AG contra búsqueda aleatoria con el mismo presupuesto: 2,040 evaluaciones de 30 combates cada una, 5 repeticiones por método, y el mejor jefe de cada corrida reevaluado con 1,000 combates [calculado]:

| Fitness | AG | Búsqueda aleatoria |
|---|---|---|
| Acordado, 1 equipo | 0.905 ± 0.025 | 0.879 ± 0.049 |
| Más estricto (margen ±20 puntos, σ = 2) | 0.729 ± 0.038 | 0.741 ± 0.035 |
| **Mínimo de 2 equipos** (el segundo con elementos rotados) | **0.887 ± 0.012** | **0.813 ± 0.100** |

**Interpretación:** hay muchos jefes buenos, así que con un solo equipo el AG gana por poco. Si el jefe tiene que ser justo contra **dos composiciones a la vez**, el AG le saca 0.07 a la búsqueda aleatoria y es **8 veces más consistente**: la búsqueda aleatoria cayó a 0.69 y 0.72 en 2 de 5 corridas.

Con 5 repeticiones esto es evidencia **media**; con 30 repeticiones sería concluyente. Hay una parte de la ventaja que conviene declarar: el AG reevalúa a sus sobrevivientes en cada generación, y eso filtra evaluaciones afortunadas. El profesor podría preguntar si una búsqueda aleatoria que reevalúa a sus 5 mejores cerraría la brecha. Conviene correr esa línea base también [estimado].

**Mi recomendación (decisión tuya):** usar el fitness = mínimo sobre 2 equipos, con `EQUIPO_ROTADO`, que ya está en `motor.py` como dato. Tiene los mismos stats, así que no inventa números nuevos: solo rota los elementos. Cuesta unas 3 líneas y duplica el tiempo de evaluación, que sigue siendo bajo: unos 4 ms por individuo con 30 combates por equipo [estimado]. Además respalda la promesa de PF01 de "composiciones de equipo asimétricas".

## 6. Otros problemas que encontré (para las Fases 3 y 4)

1. **VEL es un "basurero" de puntos.** El jefe "todo VEL" pierde el 100% de los combates. Los puntos en VEL casi no hacen nada, salvo cambiar el orden de turnos, así que el AG puede usar VEL para debilitar al jefe a propósito. No es un gen muerto, pero su papel mecánico es mínimo. Se decide en la Fase 3.
2. **El físico fuerte del heurístico le cuesta al equipo** [calculado, escala final, 2,000 jefes]. Si el equipo nunca lo usa, la proporción de jefes que pierden siempre sube de 13% a 30%. El heurístico pesa en el resultado casi tanto como la escala. Se decide en la Fase 3.
3. **El bloqueo existe en la fórmula de daño, pero el heurístico nunca lo usa.** Se decide en la Fase 3.
4. **Guardia no tiene cooldown.** Un jefe con mucho peso en Guardia puede alargar el combate. Va a la Fase 4 (estrategias degeneradas).
5. **El tope de 40 rondas cuenta como victoria del equipo** (regla del briefing). Hoy casi no ocurre, pero un jefe que solo se defiende podría explotarlo. Va a la Fase 4.
6. **"Matar a alguien antes de la ronda 3" todavía no se penaliza.** El resultado ya reporta `primera_muerte` para poder añadirlo en la Fase 4.

## 7. Decisiones provisionales que tomé para que el motor corra

Todas están marcadas en el código. Cámbialas si no estás de acuerdo:
- Mismo elemento contra mismo elemento = ×1.0. El básico y el físico fuerte del jugador no tienen elemento. Las habilidades físicas del jefe tampoco.
- "Cooldown k" significa que la habilidad no está disponible durante los siguientes k turnos del jefe.
- Al entrar a fase 2, los cooldowns se conservan.
- Guardia y bloqueo duran hasta el siguiente turno de quien los usó.
- Hielo cura al aliado vivo con menor % de HP, incluido él mismo.
- Objetivo del jefe: si nadie es débil a su elemento, va por el de menor HP absoluto; en empate, el primero de la tabla.
- Si los pesos de todas las habilidades disponibles son 0, el jefe elige al azar entre ellas.
- Reparación de pesos: si menos de 2 habilidades tienen peso > 10%, la segunda más alta sube a 0.15 y se renormaliza.

## 8. Lo que falta decidir

1. Confirmar la escala calibrada (HP × 3, ATK ÷ 2, DEF ÷ 3).
2. Fitness con 1 equipo o con el mínimo de 2.
3. Fase 3: velocidad, regla de físico fuerte y bloqueo del heurístico.
4. Fase 4: estrategias degeneradas, incluidas Guardia y el tope de rondas.
