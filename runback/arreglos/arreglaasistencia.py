# coding=utf-8
#!/usr/bin/env python

import os
import sys


# SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
# print(f"YOUR_PATH: {YOUR_PATH}")
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
# print(f"SITE_ROOT: {SITE_ROOT}")
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
# print(f"your_djangoproject_home: {your_djangoproject_home}")
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from datetime import datetime, timedelta
from django.db import transaction
from sga.models import Materia, Clase, Leccion, LeccionGrupo, AsistenciaLeccion
from sga.funciones import variable_valor


@transaction.atomic()
def copia_clases(lec, cla, inicio):
    if LeccionGrupo.objects.filter(profesor=lec.leccion_grupo().profesor, turno=cla.turno, fecha=inicio).exists():
        lecciongrupo = LeccionGrupo.objects.get(profesor=lec.leccion_grupo().profesor, turno=cla.turno, fecha=inicio)
    else:
        lecciongrupo = LeccionGrupo(profesor=lec.leccion_grupo().profesor,
                                    turno=cla.turno,
                                    aula=cla.aula,
                                    dia=cla.dia,
                                    fecha=inicio,
                                    horaentrada=cla.turno.comienza,
                                    horasalida=cla.turno.termina,
                                    abierta=False,
                                    automatica=True,
                                    contenido=lec.contenido,
                                    estrategiasmetodologicas=lec.estrategiasmetodologicas,
                                    observaciones=lec.observaciones)
        lecciongrupo.save()
    leccion = Leccion(clase=cla,
                      fecha=inicio,
                      horaentrada=cla.turno.comienza,
                      abierta=False,
                      horasalida=cla.turno.termina,
                      contenido=lec.contenido,
                      estrategiasmetodologicas=lec.estrategiasmetodologicas,
                      observaciones=lec.observaciones,
                      automatica=True,
                      aperturaleccion=True)
    leccion.save()
    lecciongrupo.lecciones.add(leccion)
    for asistencias in AsistenciaLeccion.objects.filter(leccion=lec):
        asistencialeccion = AsistenciaLeccion(leccion=leccion,
                                              materiaasignada=asistencias.materiaasignada,
                                              asistio=asistencias.asistio)
        asistencialeccion.save()
        materiaasignada = asistencialeccion.materiaasignada
        materiaasignada.save(actualiza=True)
        materiaasignada.actualiza_estado()
    lecciongrupo.save()

print("DUPLICAR CLASES NO CREADAS POR EL CRON: " + datetime.now().__str__() + "\r")
inicio = datetime.now().date() - timedelta(hours=24)
# inicio = (datetime(2017, 5, 23, 0, 0, 0)).date()
print("FECHA A PROCESAR: " + inicio.__str__() + "\r")
for ma in Materia.objects.filter(status=True, nivel__periodo__id=variable_valor('PERIODO_PROCESO_MOODLE')):
    clase = Clase.objects.filter(materia=ma, status=True, activo=True, dia=inicio.isoweekday(), inicio__lte=inicio, fin__gte=inicio)
    canhoras = clase.values('id').count()
    leccion = 0
    for cl in clase:
        if Leccion.objects.filter(clase=cl, status=True, fecha=inicio).exists():
            leccion += 1
    if (canhoras > leccion) and leccion > 0:
        lec = []
        for cl in clase:
            estado = "No registrada"
            if Leccion.objects.filter(clase=cl, status=True, fecha=inicio).exists():
                estado = "registrada"
                lec = Leccion.objects.get(clase=cl, status=True, fecha=inicio)
            else:
                if lec:
                    copia_clases(lec, cl, inicio)
                    print("clase: %s, Duplicada con exito" % (cl))

print("HECHO: " + datetime.now().__str__())
