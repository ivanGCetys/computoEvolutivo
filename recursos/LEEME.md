# Recursos del juego

Aquí va el arte, la música y el sonido de `juego.py`. Todo ya existe; si se borra una imagen, en su lugar aparece un marcador con su nombre, y si se borra un sonido el juego sigue en silencio.

Para agregar un recurso basta con guardar el archivo con el nombre exacto de esta lista en su carpeta. No hay que tocar código. Las imágenes van en png con fondo transparente. Los héroes miran hacia la derecha y el jefe hacia la izquierda.

La lista sale de `grafico/recursos.py`, función `recursosEsperados`. Si se agregan ataques, conjuros o clases al juego, sus nombres de archivo aparecen ahí solos.

## personajes

Ya tienen arte. Ocho poses por clase en pixel art, a su resolución real; el juego las agranda un número entero de veces sin suavizar. No se dibujan a mano: las genera `python -m grafico.poses` a partir del sprite de cada clase en `personajes/base/`, que sale de la pose de ataque de su hoja de diseño. Para cambiar a un personaje se cambia su base y se vuelve a correr el generador. Los pasos al frente, el estirón y los saltos de celebración los hace el código moviendo la imagen.

| Pose | Cuándo se usa |
|---|---|
| normal | En guardia, esperando su turno |
| ataque | Al pegar con su arma |
| magia | Al lanzar un conjuro, curar o usar una mejora |
| bloqueo | Desde que bloquea hasta su siguiente turno |
| dano | Un instante al recibir un golpe |
| herido | De rodillas mientras le quede 25% de vida o menos |
| caido | Tirado cuando llega a cero |
| celebra | Saltando al ganar el combate |

- `guerrero.png`
- `guerrero_ataque.png`
- `guerrero_magia.png`
- `guerrero_bloqueo.png`
- `guerrero_dano.png`
- `guerrero_herido.png`
- `guerrero_caido.png`
- `guerrero_celebra.png`
- `tanque.png`
- `tanque_ataque.png`
- `tanque_magia.png`
- `tanque_bloqueo.png`
- `tanque_dano.png`
- `tanque_herido.png`
- `tanque_caido.png`
- `tanque_celebra.png`
- `mago.png`
- `mago_ataque.png`
- `mago_magia.png`
- `mago_bloqueo.png`
- `mago_dano.png`
- `mago_herido.png`
- `mago_caido.png`
- `mago_celebra.png`
- `clerigo.png`
- `clerigo_ataque.png`
- `clerigo_magia.png`
- `clerigo_bloqueo.png`
- `clerigo_dano.png`
- `clerigo_herido.png`
- `clerigo_caido.png`
- `clerigo_celebra.png`
- `picaro.png`
- `picaro_ataque.png`
- `picaro_magia.png`
- `picaro_bloqueo.png`
- `picaro_dano.png`
- `picaro_herido.png`
- `picaro_caido.png`
- `picaro_celebra.png`
- `berserker.png`
- `berserker_ataque.png`
- `berserker_magia.png`
- `berserker_bloqueo.png`
- `berserker_dano.png`
- `berserker_herido.png`
- `berserker_caido.png`
- `berserker_celebra.png`

## jefes

Ya tienen arte. Las dos fases salen de sus ilustraciones en `disenos/`: `python -m grafico.extraerJefe` las lleva a su rejilla real, lo separa con la transparencia de la imagen y las guarda en `jefes/base/`. De ahí `python -m grafico.poses` genera, para cada fase, una pose por cada grupo de cuatro ataques, una al recibir daño y una al ser vencido. El jefe se dibuja a su resolución real; la segunda fase ya viene dibujada más alta y además se agranda un 15 %, para que su cuerpo no se vea más chico que el de la primera entre el ala y el halo. Mientras carga un ataque se queda en la pose de ese ataque.

Al atacar usa cuatro cuadros más por fase, que `grafico/poses.py` arma con el cuerpo entero, como las poses de los héroes: `alzar` se echa para atrás y se estira para tomar impulso y `golpe` se lanza al frente agachado, para los ataques físicos; `conjuro` se yergue con el aura encendida y `lanzar` se inclina al frente con el aura, para los de elemento.

- `jefe.png`
- `jefe_pose_1.png`
- `jefe_pose_2.png`
- `jefe_pose_3.png`
- `jefe_pose_4.png`
- `jefe_pose_5.png`
- `jefe_pose_6.png`
- `jefe_pose_7.png`
- `jefe_pose_8.png`
- `jefe_dano.png`
- `jefe_derrota.png`
- `jefe_alzar.png`
- `jefe_golpe.png`
- `jefe_conjuro.png`
- `jefe_lanzar.png`
- `jefe_fase2.png`
- `jefe_fase2_pose_1.png`
- `jefe_fase2_pose_2.png`
- `jefe_fase2_pose_3.png`
- `jefe_fase2_pose_4.png`
- `jefe_fase2_pose_5.png`
- `jefe_fase2_pose_6.png`
- `jefe_fase2_pose_7.png`
- `jefe_fase2_pose_8.png`
- `jefe_fase2_dano.png`
- `jefe_fase2_derrota.png`
- `jefe_fase2_alzar.png`
- `jefe_fase2_golpe.png`
- `jefe_fase2_conjuro.png`
- `jefe_fase2_lanzar.png`

Qué ataques usa cada pose:

| Pose | Ataques |
|---|---|
| 1 | Zarpazo, Mordida, Coletazo, Pisoton |
| 2 | Embestida, Cabezazo, Garra doble, Golpe pesado |
| 3 | Onda de choque, Barrido, Estampida, Terremoto |
| 4 | Llamarada, Chorro, Rafaga, Lanza de roca |
| 5 | Espinas, Descarga, Rayo de luz, Garra sombria |
| 6 | Incendio, Marejada, Vendaval, Avalancha |
| 7 | Enredadera, Tormenta, Resplandor, Eclipse |
| 8 | Aplastamiento, Devastacion, Rayo final, Cataclismo |

## escenarios

Las dos arenas ocupan la zona de la pelea, 1280 x 500, arriba de los paneles; `arena.png` es la de la primera fase y `arena_fase2.png` la de la segunda. Se escalan hasta cubrir esa zona y se recorta lo que sobre a los lados, así que una imagen más ancha no se deforma. `titulo_fondo.png` es el retrato del jefe a pantalla completa, 1280 x 720, sin la rueda, y `titulo_rueda.png` es la rueda sola, con transparencia, centrada en el punto (640, 132); salen de una ilustración de la que se separó la rueda trazo por trazo. Se usan en el título y en la cinemática de la segunda fase, que además le abre la boca al jefe estirando la mandíbula del retrato.

- `arena.png`
- `arena_fase2.png`
- `titulo_fondo.png`
- `titulo_rueda.png`

## efectos

El dibujo de cada ataque y `cambio_de_fase`, que crece sobre el jefe cuando pasa a su segunda fase. Las animaciones de ataque se arman por código (`grafico/recetas.py`) y no necesitan archivos; estos dibujos son los que vuelan como proyectil en los conjuros sencillos del mago y en la lanza de roca del jefe, y si falta alguno la animación sigue igual, solo sin esa imagen. Miden 56 x 56. Ya tienen arte: `python -m grafico.generarEfectos` los dibuja en pixel art, con un motivo por elemento para los conjuros (llama, gota, remolino, roca, hoja, rayo, estrella y orbe) que crece con su poder, y zarpazos, tajos, mordidas, impactos u ondas para los físicos. Se dibujan mirando a la derecha y el juego los voltea cuando van hacia los héroes.

- `abismo.png`
- `aplastamiento.png`
- `ataque_basico.png`
- `avalancha.png`
- `barrido.png`
- `brisa.png`
- `brote.png`
- `cabezazo.png`
- `calambre.png`
- `cambio_de_fase.png`
- `cataclismo.png`
- `chispa.png`
- `chorro.png`
- `coletazo.png`
- `descarga.png`
- `destello.png`
- `devastacion.png`
- `diluvio.png`
- `eclipse.png`
- `embestida.png`
- `enredadera.png`
- `espinas.png`
- `estampida.png`
- `fulgor.png`
- `furia_desatada.png`
- `garra_doble.png`
- `garra_sombria.png`
- `golpe_pesado.png`
- `golpe_sombra.png`
- `gota.png`
- `guijarro.png`
- `huracan.png`
- `incendio.png`
- `infierno.png`
- `juicio.png`
- `lanza_de_roca.png`
- `llama.png`
- `llamarada.png`
- `marejada.png`
- `mordida.png`
- `oleaje.png`
- `onda_de_choque.png`
- `penumbra.png`
- `pisoton.png`
- `punalada_veloz.png`
- `rafaga.png`
- `rayo_de_luz.png`
- `rayo_final.png`
- `relampago.png`
- `remolino.png`
- `resplandor.png`
- `roca.png`
- `selva_viva.png`
- `sismo.png`
- `sombra.png`
- `tajo_elemental.png`
- `tajo_mayor.png`
- `terremoto.png`
- `tormenta.png`
- `tormenta_electrica.png`
- `vendaval.png`
- `zarpazo.png`
- `zarza.png`

## sonidos

Todos salen de `python -m grafico.generarAudio`, que los compone y sintetiza al estilo de las consolas de 8 y 16 bits. No viene nada de fuera, así que no hay licencias de por medio. Si en la computadora hay ffmpeg se guardan en ogg; si no, en wav, y el juego busca los dos. Los nombres de esta lista los decide ese archivo.

- `aceptar.ogg`
- `agua.ogg`
- `bloqueo.ogg`
- `caida.ogg`
- `cambio_de_fase.ogg`
- `cancelar.ogg`
- `carga.ogg`
- `critico.ogg`
- `curacion.ogg`
- `cursor.ogg`
- `derrota.ogg`
- `destello.ogg`
- `dolor_heroe.ogg`
- `dolor_heroina.ogg`
- `encuentro.ogg`
- `error.ogg`
- `escudo.ogg`
- `espadazo.ogg`
- `esquiva.ogg`
- `explosion.ogg`
- `fuego.ogg`
- `furia.ogg`
- `giro_rapido.ogg`
- `golpe.ogg`
- `golpeSeco.ogg`
- `grito_berserker1.ogg`
- `grito_berserker2.ogg`
- `grito_clerigo1.ogg`
- `grito_clerigo2.ogg`
- `grito_guerrero1.ogg`
- `grito_guerrero2.ogg`
- `grito_mago1.ogg`
- `grito_mago2.ogg`
- `grito_picaro1.ogg`
- `grito_picaro2.ogg`
- `grito_tanque1.ogg`
- `grito_tanque2.ogg`
- `haz.ogg`
- `jefe_dolor.ogg`
- `jefe_golpe.ogg`
- `jefe_grito.ogg`
- `jefe_muerte.ogg`
- `jefe_risa.ogg`
- `jefe_rugido.ogg`
- `lanzar.ogg`
- `luz.ogg`
- `magia.ogg`
- `meteoro.ogg`
- `ola.ogg`
- `oscuridad.ogg`
- `pausa.ogg`
- `planta.ogg`
- `pocion.ogg`
- `rayo.ogg`
- `rueda.ogg`
- `tajo.ogg`
- `temblor.ogg`
- `tierra.ogg`
- `trueno.ogg`
- `victoria.ogg`
- `viento.ogg`
- `zumbido.ogg`

## musica

Dentro de `sonidos/musica`. Cada tema se repite sin corte.

`seleccion`, `batalla` y `batalla2` se tocan con instrumentos: `grafico/componerMusica.py` escribe la partitura como MIDI y la toca FluidSynth con el banco de sonidos libre FluidR3_GM (licencia MIT), y el final se empalma con el principio para que el bucle no se note. Van en estéreo a 44100. Los demás son de ondas puras, mono a 22050.

- `titulo.ogg`: el título, lento y solemne, en re menor.
- `seleccion.ogg`: la pantalla de equipo, tranquila: piano, caja de música y flauta en fa mayor.
- `batalla.ogg`: la primera fase, en re menor a 138 pulsos por minuto, al estilo de un jefe final: órgano, coro y timbales al principio, luego cuerdas en ostinato, el leitmotiv del jefe (la melodía del título en menor) en cornos y metales, batería de rock y un clímax con golpes de orquesta.
- `batalla2.ogg`: la segunda fase, el mismo leitmotiv en fa menor a 156: coro en acordes cortados, carreras de cuerdas, órgano, guitarra, timbales y doble bombo.
- `victoria.ogg`: una fanfarria y luego un tema alegre en sol mayor.
- `derrota.ogg`: lento, en la menor.
- `entrenamiento.ogg`: mientras se entrena al jefe, con arpegios que no paran.
