# coding=utf-8
# !/usr/bin/env python

import os
import sys
YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

import xlwt
from webpush import send_user_notification
from xlwt import easyxf
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
import openpyxl
from gdocumental.models import *
from postulate.models import *


def matrizadmision2023():
    cadena = ''
    linea, excluidos, conexito = 0, 0, 0
    try:
        archivo_ = 'MT_ESTUDIANTES1'
        url_archivo = "{}/media/{}.xlsx".format(SITE_STORAGE, archivo_)
        wb = openpyxl.load_workbook(filename=url_archivo)
        ws = wb.get_sheet_by_name("UNEMI")
        worksheet = ws
        lis_excluidos = []
        linea_archivo = 1
        for row in worksheet.iter_rows(min_row=0):
            numinscripciones, nummatriculas = 0, 0
            var1, var2, var3, var4, var5, var6, var7, var8 = 'NO', 'NO', 'NO', 'NO', 'NO', 'NO', 'NO', 'NO'
            if linea >= 2:
                currentValues, cadena = [], ''
                worksheet["P{}".format(linea_archivo)].value = 'SI'
                worksheet["Q{}".format(linea_archivo)].value = ''
                worksheet["R{}".format(linea_archivo)].value = ''
                worksheet["S{}".format(linea_archivo)].value = ''
                worksheet["T{}".format(linea_archivo)].value = ''
                worksheet["U{}".format(linea_archivo)].value = ''
                worksheet["V{}".format(linea_archivo)].value = ''
                worksheet["W{}".format(linea_archivo)].value = ''
                worksheet["X{}".format(linea_archivo)].value = ''
                worksheet["Y{}".format(linea_archivo)].value = ''
                for cell in row:
                    cadena += str(cell.value) + ' '
                    currentValues.append(str(cell.value))
                cedula_ = currentValues[11]
                carrera_ = currentValues[3]
                carrerapregrado_ = currentValues[2]
                qsbasepersona = Persona.objects.filter(status=True, cedula__icontains=cedula_)
                if qsbasepersona.exists():
                    persona_ = qsbasepersona.first()
                    qsbaseinscripcion = Inscripcion.objects.filter(status=True, persona=persona_, coordinacion_id=9, carrera__nombre__unaccent__icontains=carrera_.strip())
                    numinscripciones = qsbaseinscripcion.count()
                    if qsbaseinscripcion.exists():
                        qsmatriculas = Matricula.objects.filter(status=True, inscripcion=qsbaseinscripcion.first()).order_by('id')
                        nummatriculas = len(qsmatriculas)
                        periodo_aprobacion_pre = ''
                        if nummatriculas >= 1:
                            var1 = 'SI' if nummatriculas >= 1 else 'NO'
                            var2 = qsmatriculas.first().materias_aprobadas_todas()

                            worksheet["Q{}".format(linea_archivo)].value = var1
                            worksheet["R{}".format(linea_archivo)].value = 'SI' if var2 else ''
                            periodo_aprobacion_pre = qsmatriculas.first().nivel.periodo.__str__()

                            if nummatriculas >= 2:
                                var3 = 'SI' if nummatriculas >= 2 else ''
                                var4 = qsmatriculas[1].materias_aprobadas_todas()

                                worksheet["S{}".format(linea_archivo)].value = var3
                                worksheet["T{}".format(linea_archivo)].value = 'SI' if var4 else ''
                                periodo_aprobacion_pre = qsmatriculas[1].nivel.periodo.__str__()

                            if nummatriculas >= 3:
                                var5 = 'SI' if nummatriculas >= 3 else ''
                                var6 = qsmatriculas[2].materias_aprobadas_todas()

                                worksheet["U{}".format(linea_archivo)].value = var5
                                worksheet["V{}".format(linea_archivo)].value = 'SI' if var6 else ''
                                periodo_aprobacion_pre = qsmatriculas[2].nivel.periodo.__str__()

                            qsprimernivel = Matricula.objects.filter(status=True, inscripcion__persona__cedula__icontains=cedula_, nivelmalla_id=1, inscripcion__carrera__nombre__unaccent__icontains=carrerapregrado_).exclude(inscripcion__coordinacion_id=9)
                            if qsprimernivel.exists():
                                var7 = 'SI'
                                var8 = qsprimernivel.first().nivel.periodo.__str__()
                                worksheet["W{}".format(linea_archivo)].value = 'SI'
                                worksheet["X{}".format(linea_archivo)].value = var8

                            if not var2 and not var7:
                                worksheet["Y{}".format(linea_archivo)].value = f"{cedula_} - No aprobo primera matricula."

                            if not var4 and not var7:
                                worksheet["Y{}".format(linea_archivo)].value = f"{cedula_} - No aprobo segunda matricula."

                            if not var5 and not var7:
                                worksheet["Y{}".format(linea_archivo)].value = f"{cedula_} - No aprobo tercera matricula."

                            if var7:
                                worksheet["Y{}".format(linea_archivo)].value = f"{cedula_} - Aprobo en periodo {periodo_aprobacion_pre}"

                        conexito += 1
                        if not qsmatriculas:
                            lis_excluidos.append({'cedula': cedula_, 'obs': 'No existe matricula'})
                            worksheet["Y{}".format(linea_archivo)].value = f"{cedula_} - No tiene matriculas."
                            excluidos += 1
                    else:
                        lis_excluidos.append({'cedula': cedula_, 'obs': 'No existe inscripción'})
                        worksheet["W{}".format(linea_archivo)].value = f"{cedula_} - No existe inscripción"
                        excluidos += 1
                else:
                    lis_excluidos.append({'cedula': cedula_, 'obs': 'No existe persona'})
                    worksheet["W{}".format(linea_archivo)].value = f"{cedula_} - No existe persona"
                    excluidos += 1
                print("Linea {}/? - Persona: {}, Inscripciones: {}, Matricula: {} | {} - {} - {} - {} - {} - {} - {} - {}".format(linea, cedula_, numinscripciones, nummatriculas, var1, var2, var3, var4, var5, var6, var7, var8))
            linea += 1
            linea_archivo += 1
            if linea in (25, 50, 400, 800, 1200, 3000, 5000, 6000, 8000, 10000, 15000, 18000, 20000):
                wb.save(url_archivo)
                print("Guardado Rapido Linea {} . .".format(linea))
        print('Total Leidos con exito: {}'.format(conexito))
        print('Total Excluidos: {}'.format(excluidos))
        # print(lis_excluidos)
        wb.save(url_archivo)
    except Exception as ex:
        textoerror = '{} Linea:{} - Info: {} / Lectura: {}'.format(str(ex), sys.exc_info()[-1].tb_lineno, cadena, linea)
        print(textoerror)


matrizadmision2023()