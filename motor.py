# Fachada del motor. El código vive repartido en cuatro módulos y aquí solo se
# juntan, para que los scripts sigan usando "import motor as m" como siempre.
#
#   reglas.py    elementos, daño y equipos
#   jefe.py      puntos, habilidades y reparación del cromosoma
#   combate.py   simulación de un combate
#   aptitud.py   función objetivo y función de costo
import reglas
import jefe
import combate
import aptitud

from reglas import *
from jefe import *
from combate import *
from aptitud import *
