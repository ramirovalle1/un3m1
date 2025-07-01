#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import openpyxl

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
from sga.models import AsignaturaMalla, Inscripcion, Asignatura, Matricula
from django.core.exceptions import ObjectDoesNotExist
#
#
# INSCRIPCIONES = [
#     56560, 56561, 56562, 56563, 56566, 56564, 56565, 56567, 56569, 56570,
#     56572, 56573, 56574, 56575, 56576, 56577, 56578, 56579, 56581, 56583,
#     56585, 56586, 56587, 56589, 56590, 56592, 56593, 56595, 56571, 56591
# ]
#
# creditos = Matricula.objects.filter(
#     inscripcion__carrera_id=111,
#     nivel__periodo_id=317,
#     status=True,
#     retiradomatricula=False,
#     inscripcion__status=True,
#     nivelmalla__id__gt=5
# ).values_list('inscripcion_id', flat=True)
#
#
# for pk in creditos:
#     inscripcion = Inscripcion.objects.get(pk=pk)
#     # Obtener registros académicos
#     records = inscripcion.recordacademico_set.filter(aprobada=True, status=True)
#
#     # Obtener asignaturas de computación
#     computacion = AsignaturaMalla.objects.filter(malla_id=32).values_list('asignatura_id', flat=True)
#
#     if inscripcion.inscripcionmalla_set.filter(status=True).exists():
#         malla = inscripcion.inscripcionmalla_set.filter(status=True).first().malla
#         for record in records:
#             if malla.asignaturamalla_set.filter(asignatura=record.asignatura).exists():
#                 asm = malla.asignaturamalla_set.filter(asignatura=record.asignatura).first()
#                 record.creditos = asm.creditos
#                 record.horas = asm.horas
#             elif record.tiene_acta_nivel():
#                 acta = record.acta_materia_nivel()
#                 if acta.creditos > 0:
#                     record.creditos = acta.creditos
#                     record.horas = acta.horas
#                 else:
#                     modulo_malla = inscripcion.asignatura_en_modulomalla(record.asignatura)
#                     if modulo_malla:
#                         record.creditos = modulo_malla.creditos
#                         record.horas = modulo_malla.horas
#             elif record.tiene_acta_curso():
#                 acta = record.acta_materia_curso()
#                 if acta.creditos > 0:
#                     record.creditos = acta.creditos
#                     record.horas = acta.horas
#                 elif record.asignatura_id in computacion:
#                     asigcompu = inscripcion.asignaturamalla_set.get(asignatura_id=record.asignatura_id, malla_id=32)
#                     record.creditos = asigcompu.creditos
#             record.save()
#             record.historicorecordacademico_set.filter(status=True, aprobada=True).update(creditos=record.creditos,
#                                                                                           horas=record.horas)
#
# print("Finalizing")


# def migrarMoodle():
#     from Moodle_Funciones import CrearRecursoMoodle,CrearCompendioMoodle, CrearMaterialesMoodle, CrearTareasMoodle, CrearTestMoodle, \
#                 CrearForosMoodle
#     from sga.models import Persona
#     # CrearRecursoMoodle(465233,None)
#     # CrearMaterialesMoodle(709278,None)
#     erecurso = CrearCompendioMoodle(133084, Persona.objects.get(id=147830))
#     print(erecurso)
#     print("Compendio creado en Moodle")
#
#     erecurso = CrearRecursoMoodle(452022, Persona.objects.get(id=147830))
#     print(erecurso)
#     print("Recurso creado en Moodle")
#
#     fcurso = CrearForosMoodle(24243, Persona.objects.get(id=147830))
#     print(fcurso)
#     print("Foro creado en Moodle")
#
#     fcurso = CrearTareasMoodle(169877, Persona.objects.get(id=147830))
#     print(fcurso)
#     print("Tarea creado en Moodle")
#
#
#
#
# migrarMoodle()
# print(u"FIN")
#
# def actualizarMateriaMoodle():
#     from sga.models import Materia, Silabo, SilaboSemanal, MaterialAdicionalSilaboSemanal, ForoSilaboSemanal, \
#         TestSilaboSemanal, TareaSilaboSemanal, DiapositivaSilaboSemanal
#
#     materias = Materia.objects.values_list('id', flat=True).filter(nivel__periodo_id=336, status=True, cerrado=False,
#                                                                    asignaturamalla__malla__carrera__modalidad=3)
#     print(materias.count())
#     eDiapositivaSilaboSemanals = DiapositivaSilaboSemanal.objects.filter(silabosemanal__silabo__materia__in=materias,estado_id=4,status=True)
#     print(eDiapositivaSilaboSemanals.count())
#     eDiapositivaSilaboSemanals.update(estado_id=1, iddiapositivamoodle=0)
#
#
#     eForoSilaboSemanals = ForoSilaboSemanal.objects.filter(silabosemanal__silabo__materia__in=materias,estado_id=4, status=True)
#     print(eForoSilaboSemanals.count())
#     eForoSilaboSemanals.update(estado_id=1, idforomoodle=0)
#
#     eTestSilaboSemanals = TestSilaboSemanal.objects.filter(silabosemanal__silabo__materia__in=materias,estado_id=4, status=True)
#     print(eTestSilaboSemanals.count())
#     eTestSilaboSemanals.update(estado_id=1, idtestmoodle=0)
#
#     eTareaSilaboSemanals = TareaSilaboSemanal.objects.filter(silabosemanal__silabo__materia__in=materias, estado_id=4,status=True)
#     print(eTareaSilaboSemanals.count())
#     eTareaSilaboSemanals.update(estado_id=1, idtareamoodle=0)
#
#     eMaterialAdicionalSilaboSemanals = MaterialAdicionalSilaboSemanal.objects.filter(silabosemanal__silabo__materia__in=materias, estado_id=4,status=True)
#     print(eMaterialAdicionalSilaboSemanals.count())
#     eMaterialAdicionalSilaboSemanals.update(estado_id=1, idmaterialesmoodle=0)
#
#
#
#
#
# actualizarMateriaMoodle()




def recalcular_creditos():
    from inno.models import TipoActaFirma
    inscripciones = TipoActaFirma.objects.filter(status=True,turnofirmar=True,tipoacta__tipo__in = (5,6),firmado=False,
                                                tipoacta__graduado__inscripcion__carrera_id__in=(1,110,111)).distinct('tipoacta__graduado__inscripcion')


    for ins in inscripciones:
        ins.tipoacta.graduado.inscripcion.actualizar_creditos()
        print(ins.tipoacta.graduado)

recalcular_creditos()