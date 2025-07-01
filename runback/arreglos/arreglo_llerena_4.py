# coding=utf-8
# !/usr/bin/env python

import os
import sys

from django.http import HttpResponse

YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from webpush import send_user_notification
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from settings import SITE_STORAGE
import xlwt
from xlwt import easyxf, XFStyle
from sga.models import Inscripcion, AsignaturaMalla, Persona
from xlwt import *
import io
import xlsxwriter

def mtpsicologia():
    try:

        archivo_ = 'MT_PSICOLOGIA'
        url_archivo = "{}/media/{}.xlsx".format(SITE_STORAGE, archivo_)

        __author__ = 'Unemi'
        workbook = xlsxwriter.Workbook(url_archivo, {'constant_memory': True})
        ws = workbook.add_worksheet('resultados')
        fuentecabecera = workbook.add_format({
            'align': 'center',
            'bg_color': 'silver',
            'border': 1,
            'bold': 1
        })
        formatoceldacenter = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'align': 'center'})

        columns = [
            (u"DOCUMENTO_ESTUDIANTE", 20, 0),
            (u"APELLIDOS_NOMBRES", 120, 1),
            (u"EMAIL", 60, 2),
            (u"TELEFONO", 20, 3),
            (u"CARRERA", 120, 4),
            (u"MALLA_ESTUDIANTE", 120, 5),
            (u"ULTIMO_NIVEL", 60, 6),
            (u"PERIODO", 100, 7),
            (u"HORAS_PRACTICAS_PENDIENTES", 20, 8),
            (u"HORAS_PRACTICAS_CUMPLIDAS", 20, 9),
            (u"NUM_MODULOS_INGLES_APROBADOS", 20, 10),
            (u"NUM_MODULOS_COMPUTACION_APROBADOS", 20, 11),
            (u"HORAS_VINCULACION_CUMPLIDAS", 20, 12),
            (u"HORAS_VINCULACION_PENDIENTES", 20, 13),
            (u"FECHA_ULTIMA_MATRICULA", 20, 14),
        ]

        row_num, numcolum = 0, 0
        for col_num in range(len(columns)):
            ws.write(row_num, numcolum, columns[col_num][0], fuentecabecera)
            ws.set_column(row_num, numcolum, columns[col_num][1])
            numcolum += 1


        row_num, leido = 1, 1
        qsinscripcion = Inscripcion.objects.filter(status=True, carrera__in=[136, 18, 122], perfilusuario__isnull=False, matricula__isnull=False, perfilusuario__visible=True).exclude(graduado__status=True)
        qspersona = Persona.objects.filter(status=True, id__in=qsinscripcion.values_list('persona__id',flat=True))
        for persona in qspersona:
            inscripcion = Inscripcion.objects.filter(carrera__in=[136, 18, 122], status=True, persona=persona).order_by('-id').first()
            mallaest_ = inscripcion.inscripcionmalla_set.filter(status=True).order_by('-id')
            malla_ = mallaest_.first().malla
            asignaturasmalla = malla_.asignaturamalla_set.filter(opcional=False, status=True)
            xyz = [1, 2, 3]
            if inscripcion.itinerario and inscripcion.itinerario > 0:
                xyz.remove(inscripcion.itinerario)
                asignaturasmalla = asignaturasmalla.exclude(itinerario__in=xyz)
            aprobadas = inscripcion.recordacademico_set.filter(status=True, aprobada=True, asignatura__in=asignaturasmalla.values_list('asignatura_id', flat=True))
            tienereprobadas = inscripcion.recordacademico_set.filter(status=True, aprobada=False).exclude(asignatura__in=[1053, 1054]).exclude(asignatura__nombre__icontains='INGLES').exists()
            if (aprobadas and not len(aprobadas) >= len(asignaturasmalla.values_list('asignatura_id', flat=True)) or not aprobadas) or tienereprobadas:
                print('NO APROBADO')
                continue
            print(f"{len(qsinscripcion)}/{leido} - {inscripcion}")
            ingles_aprobado = inscripcion.recordacademico_set.filter(status=True, aprobada=True, asignatura__nombre__icontains='INGLES').count()
            computacion_aprobado = inscripcion.recordacademico_set.filter(status=True, aprobada=True, asignatura__in=[1053, 1054]).count()
            ultimamatricula = inscripcion.matricula_set.filter(status=True).exclude(retiradomatricula=True).order_by('-id').first()
            if inscripcion.persona.documento() == '0940325608':
                print(23)

            ws.write(row_num, 0, inscripcion.persona.documento(), formatoceldacenter)
            ws.write(row_num, 1, f"{inscripcion.persona.nombre_completo_minus()}", formatoceldacenter)
            ws.write(row_num, 2, inscripcion.persona.emailinst, formatoceldacenter)
            ws.write(row_num, 3, inscripcion.persona.telefono, formatoceldacenter)
            ws.write(row_num, 4, inscripcion.carrera.__str__(), formatoceldacenter)
            if malla_:
                ws.write(row_num, 5, f"{malla_.__str__()}", formatoceldacenter)
            else:
                ws.write(row_num, 5, '', formatoceldacenter)
            ws.write(row_num, 6, malla_.ultimo_nivel_malla().orden, formatoceldacenter)
            if ultimamatricula:
                if ultimamatricula.nivel:
                    ws.write(row_num, 7, ultimamatricula.nivel.periodo.__str__(), formatoceldacenter)
            else:
                ws.write(row_num, 7, '', formatoceldacenter)
            ws.write(row_num, 8, inscripcion.mi_malla().horas_practicas, formatoceldacenter)
            ws.write(row_num, 9, inscripcion.numero_horas_practicas_pre_profesionales(), formatoceldacenter)
            ws.write(row_num, 10, ingles_aprobado, formatoceldacenter)
            ws.write(row_num, 11, computacion_aprobado, formatoceldacenter)
            ws.write(row_num, 12, inscripcion.numero_horas_proyectos_vinculacion(), formatoceldacenter)
            ws.write(row_num, 13, inscripcion.mi_malla().horas_vinculacion, formatoceldacenter)
            if ultimamatricula:
                if ultimamatricula.fecha_creacion:
                   ws.write(row_num, 14, str(ultimamatricula.fecha_creacion.year), formatoceldacenter)
            else:
                ws.write(row_num, 14, '', formatoceldacenter)
            row_num += 1
            leido += 1
        # wb.save(url_archivo)
        print(url_archivo)
        workbook.close()
    except Exception as ex:
        textoerror = '{} Linea:{}'.format(str(ex), sys.exc_info()[-1].tb_lineno)
        print(textoerror)


mtpsicologia()
