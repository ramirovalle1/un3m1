#!/usr/bin/env python
import os
import sys
import openpyxl
# import urllib2

# Full path and name to your csv file
import unicodedata
# from django.db.backends.oracle.base import to_unicode
# from apt.package import Record

import xlrd
# from __builtin__ import file
# from IPython.lib.editorhooks import mate
from django.http import HttpResponse
# from numpy.core.records import record
# from numpy.matrixlib.defmatrix import matrix
from setuptools.windows_support import hide_file
from urllib3 import request
from docx import Document

from settings import EMAIL_INSTITUCIONAL_AUTOMATICO, EMAIL_DOMAIN, PROFESORES_GROUP_ID, \
    RESPONSABLE_BIENES_ID, ALUMNOS_GROUP_ID, USA_TIPOS_INSCRIPCIONES, TIPO_INSCRIPCION_INICIAL, DIAS_MATRICULA_EXPIRA, \
    CLAVE_USUARIO_CEDULA, CHEQUEAR_CONFLICTO_HORARIO

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

# cambio de malla del 2019 al 2012
# basisa = 166
# sistemas 147
# industrial 153
# diseño 144
# psicologia = 136
# cpa = 162
# ing cpa = 161
# ing marketing = 165
# marketing = 145
# comunicacion social = 159
# turismo = 138
# Comercio = 163
# Ing Comercial = 152
# Inicial = 148

id_periodos=[85,90]
id_carrera19_aux= (136, 0)
# id_carrera19_aux= (166,147,153,144,136,162,161,165,145,159,138,163,152,148)
id_inscripciones_todo = []
for id_carrera19 in id_carrera19_aux:
    print("Id Carrera:%s" % id_carrera19)
    equivalenciaasignaturasreversos = EquivalenciaAsignaturasReverso.objects.filter(asignatura19__malla__carrera_id=id_carrera19)
    if equivalenciaasignaturasreversos:
        id_mallaequivalencia12 = equivalenciaasignaturasreversos[0].asignatura12.malla_id
        #sacar los alumnos egresados de esa carrera
        id_egresados = Egresado.objects.values_list('inscripcion_id', flat=True).filter(status=True, inscripcion__status=True, inscripcion__matricula__estado_matricula__in=[2,3], inscripcion__matricula__nivel__periodo_id__in=id_periodos, inscripcion__carrera_id=id_carrera19, inscripcion__inscripcionold__isnull=False)
        inscripciontodo = Inscripcion.objects.filter(status=True, matricula__estado_matricula__in=[2,3], matricula__nivel__periodo_id__in=id_periodos, carrera_id=id_carrera19, inscripcionold__isnull=False).distinct().exclude(id__in=id_egresados)
        # cantidad = matriculatodo.filter(inscripcion__reverso=False).count()
        cantidad = inscripciontodo.filter(reverso=False).count()
        print ("Cantidad: %s" % cantidad)
        # for matriculas in matriculatodo.filter(inscripcion__reverso=False):
        for inscripcion in inscripciontodo.filter(reverso=False):
            print (cantidad)
            cantidad=cantidad-1
            # inscripcion19 = matriculas.inscripcion
            inscripcion19 = inscripcion
            inscripcion12 = inscripcion19.inscripcionold
            id_mallainscripcion12 = inscripcion12.mi_malla().id
            persona = inscripcion19.persona
            if id_mallainscripcion12 == id_mallaequivalencia12:
                if inscripcion19.id not in id_inscripciones_todo:
                    id_inscripciones_todo.append(inscripcion19.id)
                matriculainscripcion = inscripcion.matricula_set.filter(status=True, nivel__periodo_id__in=id_periodos, estado_matricula__in=[2,3])
                materiasmatricula19 = list(MateriaAsignada.objects.values_list('materia__asignaturamalla__asignatura_id',flat=True).filter(status=True, matricula__in=matriculainscripcion))
                matarecoraprobadareconocimiento2019 = inscripcion19.recordacademico_set.values_list('asignaturamalla__asignatura_id',flat=True).filter(status=True, aprobada=True, observaciones__icontains='PROCESO DE RECONOCIMIENTO DE CREDITOS')
                for a in matarecoraprobadareconocimiento2019:
                    materiasmatricula19.append(a)

                for record in inscripcion19.recordacademico_set.filter(status=True,aprobada=True, asignaturamalla__asignatura_id__in=materiasmatricula19):
                    for equivalencia in equivalenciaasignaturasreversos.filter(asignatura19=record.asignaturamalla):
                        inscripcionrecord12 = inscripcion12.recordacademico_set.filter(asignaturamalla=equivalencia.asignatura12)
                        #si tiene registros
                        if inscripcionrecord12:
                            if inscripcionrecord12[0].aprobada == False:
                                # sirve para valiidar cual de las notas que vio en el 2019 es mayo
                                if record.nota > inscripcionrecord12[0].nota:
                                    inscripcionrecord12.update(nota=record.nota, aprobada=True, fecha=record.fecha, observaciones="R2020m")
                                    if inscripcionrecord12[0].historicorecordacademico_set.filter(status=True)[0].fecha==record.fecha:
                                        inscripcionrecord12[0].historicorecordacademico_set.filter(status=True).update(nota=record.nota, aprobada=True, observaciones="R2020M")
                                    else:
                                        inscripcionrecord12[0].historicorecordacademico_set.filter(status=True).update(nota=record.nota, aprobada=True, observaciones="R2020M")
                        else:
                            asignaturamalla12 = equivalencia.asignatura12
                            recordaux = RecordAcademico.objects.filter(inscripcion=inscripcion12, asignatura=asignaturamalla12.asignatura)
                            if not recordaux:
                                record1 = RecordAcademico(inscripcion=inscripcion12,
                                                         asignatura=asignaturamalla12.asignatura,
                                                         nota=record.nota,
                                                         asistencia=record.asistencia,
                                                         fecha=record.fecha,
                                                         convalidacion=False,
                                                         aprobada=True,
                                                         pendiente=False,
                                                         creditos=asignaturamalla12.creditos, #preguntar
                                                         horas=asignaturamalla12.horas, #preguntar
                                                         homologada=False,
                                                         valida=True,
                                                         observaciones="R2020I_FASE3")
                                record1.save()
                                record1.actualizar()
                            else:
                                recordaux.update(asignaturamalla=equivalencia.asignatura12, nota=record.nota, aprobada=True, fecha=record.fecha, observaciones="R2020M")
                                if recordaux[0].historicorecordacademico_set.filter(status=True)[0].fecha==record.fecha:
                                    recordaux[0].historicorecordacademico_set.filter(status=True).update(asignaturamalla=equivalencia.asignatura12, nota=record.nota, aprobada=True, observaciones="R2020M")
                                else:
                                    recordaux[0].historicorecordacademico_set.filter(status=True).update(asignaturamalla=equivalencia.asignatura12, nota=record.nota, aprobada=True, observaciones="R2020M")
                            if not record.asignaturamalla:
                                RecordAcademico.objects.filter(id=record.id).update(asignaturamalla=equivalencia.asignatura12, observaciones="R2020A")
                                RecordAcademico.objects.filter(id=record.id)[0].historicorecordacademico_set.filter(status=True).update(asignaturamalla=equivalencia.asignatura12, observaciones="R2020A")

                Inscripcion.objects.filter(pk=inscripcion19.id).update(reverso=True, procesado=True)
                #modifica el nivel de la inscripcion del 2019 pasa al 2012
                nivel12aux = inscripcion12.mi_nivel()
                # sacar el nivel de matricula de su ultima matricula
                nivel19 = inscripcion19.ultima_matricula().nivelmalla
                nivel12aux.nivel = nivel19
                nivel12aux.save()
                # nuevo proceso de verificar las asignaturas reprobadas hacia atras en el 2012 para buscarlas en el 2019
                id_asignaturas2012 = inscripcion12.mi_malla().asignaturamalla_set.values_list('asignatura_id', flat=True).filter(status=True, nivelmalla__lte=nivel19)
                id_aprobadas2012 = inscripcion12.recordacademico_set.values_list('asignatura_id',flat=True).filter(status=True, aprobada=True)
                for record2019 in inscripcion19.recordacademico_set.filter(status=True,asignaturamalla__nivelmalla__lte=nivel19, aprobada=True, asignaturamalla__asignatura_id__in=id_asignaturas2012).exclude(asignaturamalla__asignatura_id__in=id_aprobadas2012):
                    recordaux = inscripcion12.recordacademico_set.filter(asignaturamalla__asignatura=record2019.asignaturamalla.asignatura, status=True)
                    if recordaux:
                        if recordaux[0].aprobada==False:
                            recordaux.update(nota=record2019.nota, aprobada=True, fecha=record2019.fecha, observaciones="R2020V2M")
                            if recordaux[0].historicorecordacademico_set.filter(status=True)[0].fecha==record2019.fecha:
                                recordaux[0].historicorecordacademico_set.filter(status=True).update(nota=record2019.nota, aprobada=True, observaciones="R2020V2M")
                            else:
                                recordaux[0].historicorecordacademico_set.filter(status=True).update(nota=record2019.nota, aprobada=True, observaciones="R2020V2M")
                    else:
                        record1 = RecordAcademico(inscripcion=inscripcion12,
                                                  asignatura=record2019.asignaturamalla.asignatura,
                                                  nota=record2019.nota,
                                                  asistencia=record2019.asistencia,
                                                  fecha=record2019.fecha,
                                                  convalidacion=False,
                                                  aprobada=True,
                                                  pendiente=False,
                                                  creditos=record2019.asignaturamalla.creditos,  # preguntar
                                                  horas=record2019.asignaturamalla.horas,  # preguntar
                                                  homologada=False,
                                                  valida=True,
                                                  observaciones="R2020V2I_FASE3")
                        record1.save()
                        record1.actualizar()
                persona.perfilusuario_set.filter(inscripcion=inscripcion19).update(visible=False)
                persona.perfilusuario_set.filter(inscripcion=inscripcion12).update(visible=True)
                print(inscripcion)

            #no aplica
            nivelactual = inscripcion12.mi_nivel()
            id_materiasmalla = inscripcion12.mi_malla().asignaturamalla_set.values_list("id", flat=True).filter(status=True, nivelmalla__lt=nivelactual.nivel)
            id_recordmaterias = inscripcion12.recordacademico_set.values_list('asignaturamalla__id', flat=True).filter(status=True, asignaturamalla__id__isnull=False)
            for materiasmallas in AsignaturaMalla.objects.filter(status=True, id__in=id_materiasmalla).exclude(id__in=id_recordmaterias):
                if not RecordAcademico.objects.filter(inscripcion=inscripcion12, asignatura=materiasmallas.asignatura):
                    record1 = RecordAcademico(inscripcion=inscripcion12,
                                              asignatura=materiasmallas.asignatura,
                                              nota=0,
                                              asistencia=0,
                                              fecha=datetime.now().date(),
                                              convalidacion=False,
                                              aprobada=True,
                                              pendiente=False,
                                              noaplica=True,
                                              creditos=materiasmallas.creditos,  # preguntar
                                              horas=materiasmallas.horas,  # preguntar
                                              homologada=False,
                                              valida=True,
                                              validapromedio=False,
                                              observaciones="R2020NOAPLICA_FASE3")
                    record1.save()
                    record1.actualizar()
                else:
                    r = RecordAcademico.objects.filter(inscripcion=inscripcion12, asignatura=materiasmallas.asignatura)
                    r.update(nota=0, asistencia=0, fecha=datetime.now(), convalidacion=False, aprobada=True, pendiente=False, noaplica=True, creditos=materiasmallas.creditos, horas=materiasmallas.horas, homologada=False, valida=True, validapromedio=False, observaciones="R2020NOAPLICA_FASE3")
                    if r[0].historicorecordacademico_set.filter(inscripcion=inscripcion12, asignatura=materiasmallas.asignatura, fecha=datetime.now().date()).exists():
                        r[0].historicorecordacademico_set.filter(inscripcion=inscripcion12, asignatura=materiasmallas.asignatura, fecha=datetime.now().date()).update(nota=0, asistencia=0, convalidacion=False, aprobada=True, pendiente=False, noaplica=True, creditos=materiasmallas.creditos, horas=materiasmallas.horas, homologada=False, valida=True, validapromedio=False, observaciones="R2020NOAPLICA_FASE3")
                    else:
                        h = r[0].historicorecordacademico_set.filter(inscripcion=inscripcion12, asignatura=materiasmallas.asignatura).order_by('-id')[0]
                        h.nota=0
                        h.fecha=datetime.now().date()
                        h.asistencia=0
                        h.convalidacion=False
                        h.aprobada=True
                        h.pendiente=False
                        h.noaplica=True
                        h.creditos=materiasmallas.creditos
                        h.horas=materiasmallas.horas
                        h.homologada=False
                        h.valida=True
                        h.validapromedio=False
                        h.observaciones="R2020NOAPLICA_FASE3"
                        h.save()


print(id_inscripciones_todo)
