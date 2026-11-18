# Fachada del motor. El código vive repartido en varios módulos y aquí solo se
# juntan, para que los scripts sigan usando "import motor as m" como siempre.
#
#   reglas.py      elementos, objetos y fórmulas de daño
#   clases.py      las seis clases, sus conjuros y los 15 equipos
#   jefe.py        puntos, habilidades y reparación del cromosoma
#   heuristico.py  jugador automático
#   combate.py     simulación de un combate
#   aptitud.py     función objetivo y función de costo
import reglas
import clases
import jefe
import heuristico
import combate
import aptitud

from reglas import *
from clases import *
from jefe import *
from heuristico import *
from combate import *
from aptitud import *
