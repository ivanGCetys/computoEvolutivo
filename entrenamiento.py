# Entrenar al jefe: corre NSGA-II con el presupuesto completo del experimento
# (30 generaciones de 30 jefes con semillas rotativas), escoge del frente al
# jefe que juega y lo valida con combates que el algoritmo nunca vio. El
# resultado queda en jefe_optimo.json y es el jefe contra el que se juega.
#
# Lo usa la pantalla de entrenamiento de juego.py, que lo corre en un proceso
# aparte para que la ventana no se congele, pero tambien se puede correr solo.
#
# Uso: python entrenamiento.py
import json
import os
import time

import motor as m
import genetico as g
import nsga2
import narrar

archivoJefe = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jefe_optimo.json")
generaciones, tamPoblacion = 30, 30
combatesValidacion, semillaValidacion = 30, 5000


def entrenar(avisar=None, semilla=None):
    # avisar recibe tuplas: ("generacion", datos) en cada generacion,
    # ("validando", None) al terminar la busqueda y ("listo", jefe) al final.
    avisar = avisar or (lambda tipo, datos: None)
    semilla = int(time.time()) % 100000 if semilla is None else semilla
    inicio = time.time()

    def alAvanzar(gen, evals, hv, objs, viols):
        avisar("generacion", {"generacion": gen, "total": generaciones, "evaluaciones": evals, "hipervolumen": hv,
                              "objetivos": [list(o) for o in objs], "violaciones": list(viols),
                              "segundos": time.time() - inicio})

    frente, historia = nsga2.correrNsga2(semillaRng=semilla, tamPoblacion=tamPoblacion, generaciones=generaciones,
                                         alAvanzar=alAvanzar)
    avisar("validando", None)
    bits, objs, viol = nsga2.elegirParaJugar(frente)
    crom = g.decodificar(bits)

    v = m.evaluar_jefe(crom, n=combatesValidacion, semilla=semillaValidacion)
    jefe = {"crom": crom, "objetivos": list(objs), "violacion": viol, "semilla": semilla,
            "fecha": time.strftime("%Y-%m-%d %H:%M"), "segundos": round(time.time() - inicio, 1),
            "evaluaciones": historia[-1][0], "hipervolumen": historia[-1][1],
            "historia": [list(h) for h in historia], "frente": [list(o) for _, o, _ in frente],
            "validacion": {k: v[k] for k in ("fitness", "p_victoria", "margen", "duracion", "variedad", "rondas_prom")}}
    with open(archivoJefe, "w") as f:
        json.dump(jefe, f, indent=1)
    avisar("listo", jefe)
    return jefe


def entrenarEnProceso(cola, semilla=None):
    # La version para correr en otro proceso: los avisos viajan por una cola.
    try:
        entrenar(lambda tipo, datos: cola.put((tipo, datos)), semilla)
    except Exception as error:
        cola.put(("error", repr(error)))


def jefeOptimo():
    # El jefe contra el que se juega: el ultimo entrenado, o si todavia no se
    # entrena ninguno, el que eligio la corrida de NSGA-II guardada en el repo.
    # El segundo valor dice de donde salio.
    if os.path.exists(archivoJefe):
        try:
            with open(archivoJefe) as f:
                jefe = json.load(f)
            if "predisposicion" in jefe["crom"]:
                return jefe, True
        except (OSError, ValueError, KeyError):
            pass
    elegido = next(j for j in narrar.cargarOCrearFrente() if j["elegido"])
    return {"crom": elegido["crom"], "objetivos": elegido["objetivos"]}, False


if __name__ == "__main__":
    def mostrar(tipo, datos):
        if tipo == "generacion":
            print("generacion %2d de %d  hipervolumen %.4f  %.0f s"
                  % (datos["generacion"], datos["total"], datos["hipervolumen"], datos["segundos"]))
        elif tipo == "listo":
            print("F validada %.4f, el equipo gana %.0f%%. Guardado en %s"
                  % (datos["validacion"]["fitness"], 100 * datos["validacion"]["p_victoria"], archivoJefe))
    entrenar(mostrar)
