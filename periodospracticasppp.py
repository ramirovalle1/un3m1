
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

from django.db import transaction

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from sga.models import *
from sagest.models import *

try:
    # PARA EJECUTAR 09/07/2021
    # EXISTEN PERIODOS DE PRACTICAS PP SIN ATAR A UNA CABECERA POR EL TEMA DE CARRERA,
    # SE CREA PARA PODER HACER CORRECIÓN DE PERIODO DE LOS ESTUDIANTES Y NO PERDER LA INFORMACIÓN DE LAS EVIDENCIAS
    periodoevidencia = PeriodoEvidenciaPracticaProfesionales.objects.filter(status=True).distinct('nombre', 'fechainicio')
    for p in periodoevidencia:
        print("------------- {} -------------".format(p.nombre))
        if CabPeriodoEvidenciaPPP.objects.filter(nombre=p.nombre, fechainicio=p.fechainicio, fechafin=p.fechafin, evaluarpromedio=p.evaluarpromedio, status=True).exists():
            periodo = CabPeriodoEvidenciaPPP.objects.filter(nombre=p.nombre, fechainicio=p.fechainicio, fechafin=p.fechafin, evaluarpromedio=p.evaluarpromedio).first()
        else:
            periodo = CabPeriodoEvidenciaPPP(nombre=p.nombre, fechainicio=p.fechainicio, fechafin=p.fechafin, evaluarpromedio=p.evaluarpromedio)
            periodo.save()
        for carrera in PeriodoEvidenciaPracticaProfesionales.objects.filter(status=True, nombre=p.nombre):
            nombrecarrera = carrera.carrera.nombre if carrera.carrera else 'SIN CARRERA'
            print('-- {}'.format(nombrecarrera))
            carrera.periodo = periodo
            carrera.save()
            apertura = AperturaPracticaPreProfesional.objects.filter(periodoevidencia=carrera).update(periodoppp=periodo)
            print('----- APERTURAS: {}'.format(AperturaPracticaPreProfesional.objects.filter(periodoevidencia=carrera).count()))
            evidencia = EvidenciaPracticasProfesionales.objects.filter(periodoevidencia=carrera).update(periodoppp=periodo)
            print('----- EVIDENCIAS: {}'.format(EvidenciaPracticasProfesionales.objects.filter(periodoevidencia=carrera).count()))
            detallepreins = DetallePreInscripcionPracticasPP.objects.filter(periodoevidencia=carrera).update(periodoppp=periodo)
            print('----- DETALLE PREINSCRIPCION: {}'.format(DetallePreInscripcionPracticasPP.objects.filter(periodoevidencia=carrera).count()))
            pppinscripcion = PracticasPreprofesionalesInscripcion.objects.filter(periodoevidencia=carrera).update(periodoppp=periodo)
            print('----- PRACTICAS INSCRIPCION: {}'.format(PracticasPreprofesionalesInscripcion.objects.filter(periodoevidencia=carrera).count()))
        listaevidencias = EvidenciaPracticasProfesionales.objects.filter(periodoppp=periodo, status=True).distinct('nombre').order_by('nombre')
        for ev in listaevidencias:
            print('EVIDENCIA {} ------------'.format(ev.pk))

            evidencias = EvidenciaPracticasProfesionales.objects.filter(periodoppp=periodo, status=True, nombre=ev.nombre).exclude(pk=ev.pk).order_by('nombre')
            for e in evidencias:
                print('------ EVIDENCIA {} ------------'.format(e.pk))
                documentos = e.detalleevidenciaspracticaspro_set.all()
                for doc in documentos:
                    print('{})  ACTUAL {} ANTERIOR {}'.format(doc.pk, ev.pk, doc.evidencia.pk))
                    doc.evidencia = ev
                    doc.save()
            evidencias.update(status=False)
except Exception as ex:
    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
    print(ex)



