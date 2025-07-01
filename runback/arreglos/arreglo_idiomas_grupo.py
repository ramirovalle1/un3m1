import os
import statistics
import sys
# SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
import openpyxl

YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
# print(f"YOUR_PATH: {YOUR_PATH}")
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
# print(f"SITE_ROOT: {SITE_ROOT}")
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
# print(f"your_djangoproject_home: {your_djangoproject_home}")
sys.path.append(your_djangoproject_home)
import xlwt
from webpush import send_user_notification
from xlwt import easyxf
from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from idioma.models import Periodo, Grupo, GrupoInscripcion
from sga.models import Matricula, Inscripcion
import pandas as pd
from django.db import transaction


def inscribir_grupos_ingles(hoja):
    with transaction.atomic():
        try:
            print('Inicio del proceso')
            miarchivo = openpyxl.load_workbook("listado_examen_2023.xlsx")
            lista = miarchivo.get_sheet_by_name(hoja)
            totallista = lista.rows
            a = 0
            periodo_id = Periodo.objects.get(id=3)
            for filas in totallista:
                a += 1
                if a > 2:
                    cod_matricula = int(filas[0].value) if filas[0].value else 0
                    cod_grupo = int(filas[1].value)
                    cedula = filas[2].value
                    text = cod_matricula if cod_matricula else cedula
                    print(f"Fila {a} - matricula: {text}")
                    eGrupo = Grupo.objects.get(id =int(cod_grupo), periodo_id=periodo_id)
                    #inscripcion = Matricula.objects.values_list('inscripcion_id').filter(id=cod_matricula)
                    if Matricula.objects.filter(id=cod_matricula).exists():
                        inscripcion_id = Matricula.objects.get(id=cod_matricula).inscripcion.id
                    else:
                        inscripcion_id = Inscripcion.objects.filter(persona__cedula=cedula).first()
                        if inscripcion_id:
                            inscripcion_id = inscripcion_id.id
                    if not GrupoInscripcion.objects.filter(grupo_id=eGrupo.id, inscripcion_id=inscripcion_id).exists():
                        eInscripcionGrupo = GrupoInscripcion(
                            grupo_id=eGrupo.id,
                            inscripcion_id=inscripcion_id,
                            estado=0,
                        )
                        eInscripcionGrupo.save()
                    #print(f"Fila {a}")
        except Exception as ex:
            transaction.set_rollback(True)
            print(f'Error on line {sys.exc_info()[-1].tb_lineno} {ex.__str__()}')
            print(ex)


def eliminar_duplicados_ingles(hoja):
    with transaction.atomic():
        try:
            print('Inicio eliminacion dupicado')
            miarchivo = openpyxl.load_workbook("listado_examen.xlsx")
            lista = miarchivo.get_sheet_by_name(hoja)
            totallista = lista.rows
            a = 0
            periodo_id = Periodo.objects.get(id=2)
            for filas in totallista:
                a += 1
                if a > 2:
                    cod_matricula = int(filas[0].value)
                    cod_grupo = int(filas[1].value)
                    eGrupo = Grupo.objects.get(id =int(cod_grupo), periodo_id=periodo_id)
                    inscripcion_id = Matricula.objects.get(id=cod_matricula).inscripcion.id
                    duplicadosList = GrupoInscripcion.objects.filter(grupo_id=eGrupo.id, inscripcion_id=inscripcion_id)
                    if len(duplicadosList) > 1:
                        eDuplicado = duplicadosList.last()
                        eDuplicado.delete()
                        print(f'Duplicado Eliminado {cod_matricula}')
        except Exception as ex:
            transaction.set_rollback(True)
            print(ex)

#inscribir_grupos_ingles('1S-2023')
# eliminar_duplicados_ingles('1S-2023')
total_inscritos_grupo5 = GrupoInscripcion.objects.filter(grupo_id =8).count()
print(f"Inscritos en Grupo 8 {total_inscritos_grupo5}")
inscribir_grupos_ingles('2S-2023')
total_inscritos_grupo6 = GrupoInscripcion.objects.filter(grupo_id =9).count()
print(f"Inscritos en Grupo 9 {total_inscritos_grupo6}")