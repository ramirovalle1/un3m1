# coding=utf-8
# !/usr/bin/env python

import os
import sys

from django.db.models.fields import IntegerField

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


def matrizadmision2023docentes():
    cadena = ''
    linea, excluidos, conexito = 0, 0, 0
    try:
        archivo_ = 'MT_DOCENTES_SENESCYT1'
        url_archivo = "{}/media/{}.xlsx".format(SITE_STORAGE, archivo_)
        wb = openpyxl.load_workbook(filename=url_archivo)
        ws = wb.get_sheet_by_name("BASEREG3OCU (2)")
        worksheet = ws
        lis_excluidos = []
        linea_archivo = 1
        for row in worksheet.iter_rows(min_row=0, max_row=346):
            numinscripciones, nummatriculas = 0, 0
            var1, var2, var3, var4, var5, var6, var7, var8, var9, var10, var11, var12, var13 = 'NO', 'NO', 'NO', 'NO', 'NO', 'NO', 'NO', 'NO', 'NO', 'NO', 'NO', 'NO', 'NO'
            if linea >= 1:
                currentValues, cadena = [], ''
                worksheet["E{}".format(linea_archivo)].value = ''
                worksheet["F{}".format(linea_archivo)].value = ''
                worksheet["G{}".format(linea_archivo)].value = ''
                worksheet["H{}".format(linea_archivo)].value = ''
                worksheet["I{}".format(linea_archivo)].value = ''
                worksheet["J{}".format(linea_archivo)].value = ''
                worksheet["K{}".format(linea_archivo)].value = ''
                worksheet["L{}".format(linea_archivo)].value = ''
                worksheet["M{}".format(linea_archivo)].value = ''
                worksheet["N{}".format(linea_archivo)].value = ''
                worksheet["P{}".format(linea_archivo)].value = ''
                worksheet["O{}".format(linea_archivo)].value = ''
                worksheet["P{}".format(linea_archivo)].value = ''
                worksheet["Q{}".format(linea_archivo)].value = ''
                worksheet["R{}".format(linea_archivo)].value = ''
                worksheet["S{}".format(linea_archivo)].value = ''
                worksheet["T{}".format(linea_archivo)].value = ''
                worksheet["U{}".format(linea_archivo)].value = ''
                worksheet["V{}".format(linea_archivo)].value = ''
                worksheet["W{}".format(linea_archivo)].value = ''
                worksheet["X{}".format(linea_archivo)].value = ''
                worksheet["Y{}".format(linea_archivo)].value = ''
                worksheet["Z{}".format(linea_archivo)].value = ''
                worksheet["AA{}".format(linea_archivo)].value = ''
                worksheet["AB{}".format(linea_archivo)].value = ''
                worksheet["AC{}".format(linea_archivo)].value = ''
                worksheet["AD{}".format(linea_archivo)].value = ''
                for cell in row:
                    cadena += str(cell.value) + ' '
                    currentValues.append(str(cell.value))

                cedula_ = currentValues[3]

                qsbasepersona = Persona.objects.filter(status=True, cedula__icontains=cedula_)
                if qsbasepersona.exists():
                    persona_ = qsbasepersona.first()

                    worksheet["F{}".format(linea_archivo)].value = persona_.nacimiento
                    worksheet["G{}".format(linea_archivo)].value = persona_.sexo.__str__() if persona_.sexo else ''

                    qsprofesor = Profesor.objects.filter(status=True, persona=persona_).order_by('-id')
                    if qsprofesor.exists():
                        profesor_ = qsprofesor.first()

                        periodos_ = Periodo.objects.filter(status=True, id__in=[126, 153])
                        qsdistributivoprofe = ProfesorDistributivoHoras.objects.filter(status=True, profesor=profesor_, periodo__in=periodos_.values_list('id', flat=True)).order_by('-id')
                        fechainicio=periodos_.first().inicio
                        fechafin=periodos_.last().fin
                        personacontrato = persona_.personacontratos_set.filter(status=True, fechainicio__gte=fechainicio, fechafin__lte=fechafin, regimenlaboral_id=2).order_by('id')
                        # contratopersona = persona_.contratopersona_set.filter(status=True, estado=True, fechainicio__gte=fechainicio, fechafin__lte=fechafin, regimenlaboral_id=2).order_by('id')
                        finicio, ffin, regimenlaboral, unidadorganica = 'Sin contrato en periodos', 'Sin contrato en periodos', 'NO', 'NO'
                        worksheet["E{}".format(linea_archivo)].value = f'{persona_}'
                        worksheet["F{}".format(linea_archivo)].value = f'{persona_.nacimiento}'
                        worksheet["G{}".format(linea_archivo)].value = f'{persona_.sexo}'
                        if personacontrato:
                            persona_c = personacontrato.last()
                            finicio = f'{personacontrato.first().fechainicio}'
                            ffin = f'{persona_c.fechafin}'
                            regimenlaboral = f'{persona_c.regimenlaboral}' if persona_c.regimenlaboral else regimenlaboral
                            unidadorganica = f'{persona_c.unidadorganica}' if persona_c.unidadorganica else unidadorganica

                        worksheet["H{}".format(linea_archivo)].value = finicio
                        worksheet["I{}".format(linea_archivo)].value = ffin
                        worksheet["J{}".format(linea_archivo)].value = regimenlaboral
                        if qsdistributivoprofe.exists():
                            distributivoprofe_ = qsdistributivoprofe.first()
                            var1 = distributivoprofe_.nivelcategoria.__str__() if distributivoprofe_.nivelcategoria else ''
                            var2 = distributivoprofe_.categoria.__str__() if distributivoprofe_.categoria else ''
                            var3 = distributivoprofe_.dedicacion.__str__() if distributivoprofe_.dedicacion else ''
                            qsdistributivo = persona_.distributivopersona_set.filter(status=True, regimenlaboral__in=[2]).order_by('-id')
                            nivelocupacional, modalidadlaboral, escalaocupacional, denominacionpuesto, estadopuesto = 'NO', 'NO', 'NO', 'NO','NO'
                            if qsdistributivo.exists():
                                distributivo_ = qsdistributivo.first()
                                var4 = distributivo_.rmupuesto
                                nivelocupacional=f'{distributivo_.nivelocupacional}' if distributivo_.nivelocupacional else 'NO'
                                modalidadlaboral=f'{distributivo_.modalidadlaboral}' if distributivo_.modalidadlaboral else 'NO'
                                escalaocupacional=f'{distributivo_.escalaocupacional}' if distributivo_.escalaocupacional else 'NO'
                                denominacionpuesto=f'{distributivo_.denominacionpuesto}' if distributivo_.denominacionpuesto else 'NO'
                                estadopuesto=f'{distributivo_.estadopuesto}' if distributivo_.estadopuesto else 'NO'
                                unidadorganica=f'{distributivo_.unidadorganica}' if distributivo_.unidadorganica else 'NO'
                                regimenlaboral = f'{distributivo_.regimenlaboral}' if distributivo_.regimenlaboral else regimenlaboral
                            else:
                                var4 = f"NO REGISTRA EN DISTRIBUTIVO"


                            var5 = distributivoprofe_.detalledistributivo_set.filter(status=True, criteriodocenciaperiodo__isnull=False, criteriodocenciaperiodo__criterio__id=118).aggregate(tothoras=Coalesce(Sum(F('horas'), output_field=IntegerField()), 0)).get('tothoras')
                            var6 = distributivoprofe_.detalledistributivo_set.filter(status=True, criteriodocenciaperiodo__isnull=False, criteriodocenciaperiodo__criterio__in=[122, 121]).aggregate(tothoras=Coalesce(Sum(F('horas'), output_field=IntegerField()), 0)).get('tothoras')
                            var7 = distributivoprofe_.detalledistributivo_set.filter(status=True, criteriodocenciaperiodo__isnull=False).exclude(criteriodocenciaperiodo__criterio__in=[118, 122, 121]).aggregate(tothoras=Coalesce(Sum(F('horas'), output_field=IntegerField()), 0)).get('tothoras')
                            var8 = distributivoprofe_.detalledistributivo_set.filter(status=True, criterioinvestigacionperiodo__isnull=False).aggregate(tothoras=Coalesce(Sum(F('horas'), output_field=IntegerField()), 0)).get('tothoras')
                            var9 = distributivoprofe_.detalledistributivo_set.filter(status=True, criteriogestionperiodo__isnull=False).aggregate(tothoras=Coalesce(Sum(F('horas'), output_field=IntegerField()), 0)).get('tothoras')
                            var10 = distributivoprofe_.detalledistributivo_set.filter(status=True, criteriovinculacionperiodo__isnull=False).aggregate(tothoras=Coalesce(Sum(F('horas'), output_field=IntegerField()), 0)).get('tothoras')
                            var11 = var5 + var6 + var7 + var8 + var9 + var10
                            var12 = distributivoprofe_.periodo.__str__()
                            var13 = f'Periodos: {qsdistributivoprofe.count()}'

                            worksheet["J{}".format(linea_archivo)].value = regimenlaboral
                            worksheet["K{}".format(linea_archivo)].value = nivelocupacional
                            worksheet["L{}".format(linea_archivo)].value = modalidadlaboral
                            worksheet["M{}".format(linea_archivo)].value = escalaocupacional
                            worksheet["N{}".format(linea_archivo)].value = denominacionpuesto
                            worksheet["O{}".format(linea_archivo)].value = estadopuesto
                            worksheet["P{}".format(linea_archivo)].value = unidadorganica
                            worksheet["Q{}".format(linea_archivo)].value = var1
                            worksheet["R{}".format(linea_archivo)].value = var2
                            worksheet["S{}".format(linea_archivo)].value = var3
                            worksheet["T{}".format(linea_archivo)].value = var4
                            worksheet["U{}".format(linea_archivo)].value = var5
                            worksheet["V{}".format(linea_archivo)].value = var6
                            worksheet["W{}".format(linea_archivo)].value = var7
                            worksheet["X{}".format(linea_archivo)].value = var8
                            worksheet["Y{}".format(linea_archivo)].value = var9
                            worksheet["Z{}".format(linea_archivo)].value = var10
                            worksheet["AA{}".format(linea_archivo)].value = var11
                            worksheet["AB{}".format(linea_archivo)].value = var12
                            worksheet["AC{}".format(linea_archivo)].value = var13
                            worksheet["AD{}".format(linea_archivo)].value = cedula_

                        else:
                            lis_excluidos.append({'cedula': cedula_, 'obs': 'No existe en distributivo profesor '})
                            worksheet["AD{}".format(linea_archivo)].value = f"{cedula_} - No existe en distributivo profesor o en persona contrato"
                            excluidos += 1
                    else:
                        lis_excluidos.append({'cedula': cedula_, 'obs': 'No existe en profesores'})
                        worksheet["AD{}".format(linea_archivo)].value = f"{cedula_} - No existe en profesores"
                        excluidos += 1

                else:
                    lis_excluidos.append({'cedula': cedula_, 'obs': 'No existe persona'})
                    worksheet["AD{}".format(linea_archivo)].value = f"{cedula_} - No existe persona"
                    excluidos += 1
                print("Linea {}/? - Persona: {}, {}, {} - {} - {} - {} - {} - {} - {}".format(linea, cedula_, var1, var2, var3, var4, var5, var6, var7, var8))
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


matrizadmision2023docentes()