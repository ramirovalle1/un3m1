#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import unicodedata

from settings import USA_TIPOS_INSCRIPCIONES, TIPO_INSCRIPCION_INICIAL

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


#Actualizar horas presenciales y autonomas semanales del silabo
# for mat in Materia.objects.filter(status=True, nivel__periodo_id=80, asignaturamalla__malla__id=97):
#     if mat.silabo_actual():
#         silabo = mat.silabo_actual()
#         if silabo.tiene_silabo_semanal():
#             for s in silabo.silabosemanal_set.filter(status=True):
#                 s.horaautonoma = silabo.materia.asignaturamalla.horasautonomassemanales
#                 s.horaspresencial = silabo.materia.asignaturamalla.horaspresencialessemanales
#                 print(str(s.horaautonoma) + " - " + str(s.horaspresencial))
#                 s.save()
#                 print(str(s.horaautonoma) + " - " + str(s.horaspresencial))
#actualizar examen complexivo
# for alter in AlternativaTitulacion.objects.filter(status=True, tipotitulacion__id=2, grupotitulacion__periodogrupo__id=6):
#     if alter.tiene_cronogramaadicional():
#         if alter.complexivoexamen_set.values('id').filter(status=True, examenadicional=True).exists():
#             c = alter.cronogramaexamencomplexivo_set.filter(status=True)[0]
#             c = c.lista_cronogramaadicional()[0]
#             ex = alter.complexivoexamen_set.filter(status=True, examenadicional=True, aplicaexamen=True)[0]
#             ex.cronogramaadicional=c
#             ex.save()
#             print(alter.carrera.nombre)

# for alter in AlternativaTitulacion.objects.filter(status=True, tipotitulacion__id=2, grupotitulacion__periodogrupo__id=6):
#     if alter.tiene_cronogramaadicional():
#         if alter.complexivoexamen_set.values('id').filter(status=True, examenadicional=True).exists():
#             for mat in alter.matriculatitulacion_set.filter(status=True).exclude(estado=8):
#                 if mat.complexivoexamendetalle_set.filter(status=True, estado=3).exclude(examen__examenadicional=True).exists():
#                     examen = mat.complexivoexamendetalle_set.filter(status=True, examen__examenadicional=True)
#                     print(alter.carrera.nombre)
#                     print(mat)
#                     print(examen)
#                     examen.delete()

# for mat in Materia.objects.filter(status=True, asignaturamalla__malla__carrera__modalidad=3, nivel__sesion__id=13):
#     if mat.tiene_silabo():
#         if mat.silabo_actual():
#             print(mat.asignatura.nombre)
#             if VirtualActividadesSilabo.objects.filter(silabosemanal__silabo=mat.silabo_actual()).exists():
#                 for act in VirtualActividadesSilabo.objects.filter(silabosemanal__silabo=mat.silabo_actual()):
#                     if act.subtema:
#                         tema = act.subtema.temaunidadresultadoprogramaanalitico
#                         if tema:
#                             act.tema=tema
#                             act.save()
#                             print(tema.descripcion)
#             if VirtualCasosPracticosSilabo.objects.filter(silabosemanal__silabo=mat.silabo_actual()).exists():
#                 for cas in VirtualCasosPracticosSilabo.objects.filter(silabosemanal__silabo=mat.silabo_actual()):
#                     if cas.subtema:
#                         tema = cas.subtema.temaunidadresultadoprogramaanalitico
#                         if tema:
#                             cas.tema = tema
#                             cas.save()
#                             print(tema.descripcion)
#             if VirtualLecturasSilabo.objects.filter(silabosemanal__silabo=mat.silabo_actual()).exists():
#                 for lec in VirtualLecturasSilabo.objects.filter(silabosemanal__silabo=mat.silabo_actual()):
#                     if lec.subtema:
#                         tema = lec.subtema.temaunidadresultadoprogramaanalitico
#                         if tema:
#                             lec.tema = tema
#                             lec.save()
#                             print(tema.descripcion)
#             if VirtualMasRecursoSilabo.objects.filter(silabosemanal__silabo=mat.silabo_actual()).exists():
#                 for rec in VirtualMasRecursoSilabo.objects.filter(silabosemanal__silabo=mat.silabo_actual()):
#                     if rec.subtema:
#                         tema = rec.subtema.temaunidadresultadoprogramaanalitico
#                         if tema:
#                             rec.tema = tema
#                             rec.save()
#                             print(tema.descripcion)
#             if VirtualPresencialSilabo.objects.filter(silabosemanal__silabo=mat.silabo_actual()).exists():
#                 for pre in VirtualPresencialSilabo.objects.filter(silabosemanal__silabo=mat.silabo_actual()):
#                     if pre.subtema:
#                         tema = pre.subtema.temaunidadresultadoprogramaanalitico
#                         if tema:
#                             pre.tema = tema
#                             pre.save()
#                             print(tema.descripcion)
#             if VirtualTestSilabo.objects.filter(silabosemanal__silabo=mat.silabo_actual()).exists():
#                 for tes in VirtualTestSilabo.objects.filter(silabosemanal__silabo=mat.silabo_actual()):
#                     if tes.subtema:
#                         tema = tes.subtema.temaunidadresultadoprogramaanalitico
#                         if tema:
#                             tes.tema = tema
#                             tes.save()
#                             print(tema.descripcion)

# yaevaluaron =RespuestaEvaluacionAcreditacion.objects.values_list('profesor_id').filter(proceso__periodo_id=82,tipoinstrumento=2)
# profe = Profesor.objects.values_list('id').filter(profesormateria__materia__nivel__periodo_id=82,profesormateria__tipoprofesor_id=1,profesormateria__materia__nivel__modalidad_id=1,profesormateria__materia__asignaturamalla__malla__carrera__coordinacion=9).distinct().exclude(pk__in=yaevaluaron)
# docentes = ProfesorDistributivoHoras.objects.values_list('periodo__nombre','profesor__persona__cedula','profesor__persona__apellido1','profesor__persona__apellido2','profesor__persona__nombres','carrera__nombre').filter(periodo_id=82).exclude(profesor_id__in=yaevaluaron).exclude(horasdocencia=0,horasinvestigacion=0,horasgestion=0)
#
# print(docentes.query)
#
# print(len(profe))
#
# yaevaluaron =RespuestaEvaluacionAcreditacion.objects.values_list('profesor_id').filter(proceso__periodo_id=85,tipoinstrumento=2)
# profe = Profesor.objects.values_list('id').filter(profesormateria__materia__nivel__periodo_id=85).distinct().exclude(pk__in=yaevaluaron)
# docentes = ProfesorDistributivoHoras.objects.values_list('periodo__nombre','profesor__persona__cedula','profesor__persona__apellido1','profesor__persona__apellido2','profesor__persona__nombres','carrera__nombre').filter(periodo_id=85).exclude(profesor_id__in=yaevaluaron).exclude(horasdocencia=0,horasinvestigacion=0,horasgestion=0)
#
# print(docentes.query)
#
# print(len(docentes))
import xlrd
workbook = xlrd.open_workbook("inscribiradmisionvirtual.xlsx")
sheet = workbook.sheet_by_index(0)
linea = 1

try:
    for rowx in range(sheet.nrows):
        if linea>1:
            cols = sheet.row_values(rowx)
            # session_id = 1
            cedula = cols[0].strip().upper()

            persona = Persona.objects.filter(cedula=cols[0])[0]
            # sesion = Sesion.objects.get(id=session_id)
            carrera = Carrera.objects.get(pk=int(cols[2]))
            coordinacion = Coordinacion.objects.get(pk=int(cols[8]))
            modalidad = Modalidad.objects.get(pk=int(cols[7]))
            sede = Sede.objects.get(pk=1)

            if not Inscripcion.objects.values('id').filter(persona=persona,carrera=carrera).exists():
                inscripcion = Inscripcion(persona=persona,
                                          fecha=datetime.now().date(),
                                          carrera=carrera,
                                          modalidad=modalidad,
                                          coordinacion=coordinacion,
                                          # sesion=null,
                                          sede=sede,
                                          colegio="N/S")
                inscripcion.save()
                persona.crear_perfil(inscripcion=inscripcion)
                documentos = DocumentosDeInscripcion(inscripcion=inscripcion,
                                                     titulo=False,
                                                     acta=False,
                                                     cedula=False,
                                                     votacion=False,
                                                     actaconv=False,
                                                     partida_nac=False,
                                                     pre=False,
                                                     observaciones_pre='',
                                                     fotos=False)
                documentos.save()
                preguntasinscripcion = inscripcion.preguntas_inscripcion()
                perfil_inscripcion = inscripcion.persona.mi_perfil()
                inscripcion.malla_inscripcion()
                inscripcion.actualizar_nivel()
                if USA_TIPOS_INSCRIPCIONES:
                    inscripciontipoinscripcion = InscripcionTipoInscripcion(inscripcion=inscripcion,
                                                                            tipoinscripcion_id=TIPO_INSCRIPCION_INICIAL)
                    inscripciontipoinscripcion.save()
        linea += 1
        print(str(linea) + ' de ' + str(range(sheet.nrows)) )
except Exception as ex:
    print(ex)







