#!/usr/bin/env python

import os
import sys
import time

import warnings

warnings.filterwarnings('ignore', message='Unverified HTTPS request')

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from sga.models import *
from moodle import moodle

# from django.db import connections
# cursor = connections['moodle_db'].cursor()
from Moodle_Funciones import crearhtmlphpmoodle

# servidor
AGREGAR_ESTUDIANTE = False
AGREGAR_DOCENTE = False
AGREGAR_SILABO = False
AGREGAR_MODELO_NOTAS = True
TIPO_AULA_VIRTUAL = True
parent_grupoid = 0
tipourl = 1
from Moodle_Funciones import buscarUsuario
materia=Materia.objects.get(id=45979)
clave = 'todo'
cursor = connections['moodle_pos'].cursor()

for estudiante in materia.asignados_a_esta_materia_moodle().filter(retiramateria=False):
    try:
        bandera = 0
        persona = estudiante.matricula.inscripcion.persona
        username = persona.usuario.username
        idnumber_user = persona.identificacion()
        cursoid = materia.idcursomoodle
        estudianteid = buscarUsuario(username, cursor)
        rolest = moodle.EnrolarCurso(materia.nivel.periodo, tipourl, materia.nivel.periodo.rolestudiante, estudianteid, cursoid)
        if persona.idusermoodleposgrado != estudianteid:
            persona.idusermoodleposgrado = estudianteid
            persona.save()
        print('************Estudiante: %s *** %s' % ( persona))
    except Exception as ex:
        print('Error al crear estudiante %s' % ex)