import os
import sys
import xlsxwriter
import xlwt
import openpyxl
from xlwt import *

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

from sga.models import *


def cargacriterios_docentes_distributivos(periodo):
    per = Periodo.objects.get(id=periodo)

    # PLANIFICAR Y ACTUALIZAR CONTENIDOS DE CLASES, SEMINARIOS, TALLERES, ENTRE OTROS     id >>>>>>>> 774 ---- criterioid ----- 122
    # PREPARAR, ELABORAR, APLICAR Y CALIFICAR EXÁMENES, TRABAJOS Y PRÁCTICAS              id >>>>>>>> 775 ---- criteriosid----121
    # DISEÑAR Y ELABORAR MATERIAL DIDÁCTICO, GUÍAS DOCENTES O SYLLABUS    id >>>>>>>> 937 correcion ----942------- criterioid---- 123
    # ORIENTAR Y ACOMPAÑAR A ESTUDIANTES A TRAVÉS DE TUTORÍAS ACADÉMICAS DE FORMA PRESENCIAL Y/O EN LÍNEA. id >>>>>>>> 938 correcion 943 ------ criterios---- 124
    for profesor in ProfesorDistributivoHoras.objects.filter(status=True, periodo_id=periodo,activo=True, profesor__persona__real=True):
        print(profesor)
        es_enlinea = profesor.profesor.profesormateria_set.filter(materia__asignaturamalla__malla__modalidad_id=3, materia__nivel__periodo_id=periodo, status=True, principal=True, tipoprofesor_id__in=[8, 14], activo=True).exists()

        horasdocencia = profesor.detalledistributivo_set.filter(status=True, criteriodocenciaperiodo__criterio_id=118).first()
        if horasdocencia:
            sixpercnt=round(horasdocencia.horas * 0.6)
            sixpercnt_sub=round(sixpercnt * 0.6)
            fourpercnt_sub=round(horasdocencia.horas * 0.4) - 1 if not es_enlinea else round(horasdocencia.horas * 0.4) - 2
            fourpercnt=round(sixpercnt * 0.4)
            criterio_orientar=1
            Elaborar_material=horasdocencia.horas-sixpercnt-criterio_orientar

            # para criterio PLANIFICAR Y ACTUALIZAR CONTENIDOS DE CLASES, SEMINARIOS, TALLERES, ENTRE OTROS
            if not profesor.detalledistributivo_set.filter(status=True, criteriodocenciaperiodo_id=774).exists():
                det = DetalleDistributivo(criteriodocenciaperiodo_id=774, distributivo=profesor, horas=sixpercnt_sub)
            else:
                det = profesor.detalledistributivo_set.filter(status=True, criteriodocenciaperiodo_id=774).first()
                det.horas = sixpercnt_sub
            det.save()
            if not ActividadDetalleDistributivo.objects.filter(status=True, criterio=det).exists():
                act = ActividadDetalleDistributivo(criterio=det, nombre=det.criteriodocenciaperiodo.criterio.nombre, desde=per.inicio, hasta=per.fin, horas=sixpercnt_sub)
                act.save()

            # PREPARAR, ELABORAR, APLICAR Y CALIFICAR EXÁMENES, TRABAJOS Y PRÁCTICAS              id >>>>>>>> 775
            if not profesor.detalledistributivo_set.filter(status=True, criteriodocenciaperiodo_id=775).exists():
                det = DetalleDistributivo(criteriodocenciaperiodo_id=775, distributivo=profesor, horas=fourpercnt)
            else:
                det = profesor.detalledistributivo_set.filter(status=True, criteriodocenciaperiodo_id=775).first()
                det.horas = fourpercnt
            det.save()

            if not ActividadDetalleDistributivo.objects.filter(status=True, criterio=det).exists():
                act = ActividadDetalleDistributivo(criterio=det, nombre=det.criteriodocenciaperiodo.criterio.nombre, desde=per.inicio, hasta=per.fin, horas=fourpercnt)
                act.save()

            # DISEÑAR Y ELABORAR MATERIAL DIDÁCTICO, GUÍAS DOCENTES O SYLLABUS                     id >>>>>>>> 942
            if not profesor.detalledistributivo_set.filter(status=True, criteriodocenciaperiodo_id=942).exists():
                det = DetalleDistributivo(criteriodocenciaperiodo_id=942, distributivo=profesor, horas=fourpercnt_sub)
            else:
                det = profesor.detalledistributivo_set.filter(status=True, criteriodocenciaperiodo_id=942).first()
                det.horas = fourpercnt_sub
            det.save()

            if not ActividadDetalleDistributivo.objects.filter(status=True, criterio=det).exists():
                act = ActividadDetalleDistributivo(criterio=det, nombre=det.criteriodocenciaperiodo.criterio.nombre, desde=per.inicio, hasta=per.fin, horas=fourpercnt_sub)
                act.save()

            # ORIENTAR Y ACOMPAÑAR A ESTUDIANTES A TRAVÉS DE TUTORÍAS ACADÉMICAS DE FORMA PRESENCIAL Y/O EN LÍNEA. id >>>>>>>> 943
            if not profesor.detalledistributivo_set.filter(status=True, criteriodocenciaperiodo_id=943).exists():
                det = DetalleDistributivo(criteriodocenciaperiodo_id=943, distributivo=profesor, horas=criterio_orientar)
            else:
                det = profesor.detalledistributivo_set.filter(status=True, criteriodocenciaperiodo_id=943).first()
                det.horas = criterio_orientar
            det.save()

            if not ActividadDetalleDistributivo.objects.filter(status=True, criterio=det).exists():
                act = ActividadDetalleDistributivo(criterio=det, nombre=det.criteriodocenciaperiodo.criterio.nombre, desde=per.inicio, hasta=per.fin, horas=criterio_orientar)
                act.save()

                # ORIENTAR Y MOTIVAR A ESTUDIANTES DE LAS CARRERAS EN MODALIDAD EN LÍNEA MEDIANTE EL SEGUIMIENTO A TRAVÉS DE LA PLATAFORMA INSTITUCIONAL. id >>>>>>>> 939 correcion--- 944 ---- criterioid----136
                #if profesor.carrera.modalidad == 3:
            if es_enlinea:
                if not profesor.detalledistributivo_set.filter(status=True, criteriodocenciaperiodo_id=944).exists():
                    det = DetalleDistributivo(criteriodocenciaperiodo_id=944, distributivo=profesor, horas=1)
                else:
                    det = profesor.detalledistributivo_set.filter(status=True, criteriodocenciaperiodo_id=944).first()
                    det.horas = criterio_orientar
                det.save()
                if not ActividadDetalleDistributivo.objects.filter(status=True, criterio=det).exists():
                    act = ActividadDetalleDistributivo(criterio=det, nombre=det.criteriodocenciaperiodo.criterio.nombre, desde=per.inicio, hasta=per.fin, horas=1)
                    act.save()
            else:
                print("NO ES EN LINEA")

            profesor.actualiza_hijos()
            profesor.resumen_evaluacion_acreditacion().actualizar_resumen()
cargacriterios_docentes_distributivos(177)