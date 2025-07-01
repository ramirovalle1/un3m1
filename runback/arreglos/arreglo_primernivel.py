#!/usr/bin/env python
import csv
import os
import sys

import xlrd

from settings import USA_TIPOS_INSCRIPCIONES, TIPO_INSCRIPCION_INICIAL, DIAS_MATRICULA_EXPIRA

# import urllib2
# Full path and name to your csv file
# from django.db.backends.oracle.base import to_unicode
# from apt.package import Record
# from __builtin__ import file
# from IPython.lib.editorhooks import mate
# from numpy.core.records import record
# from numpy.matrixlib.defmatrix import matrix
csv_filepathname3 = "problemas2021_corregido_g6.csv"
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

def convertirfecha2(fecha):
    try:
        return date(int(fecha[0:4]),int(fecha[5:7]),int(fecha[8:10]))
    except Exception as ex:
        return datetime.now().date()

from moodle import moodle

def fechatope(fecha):
    contador = 0
    nuevafecha = fecha
    while contador < DIAS_MATRICULA_EXPIRA:
        nuevafecha = nuevafecha + timedelta(1)
        if nuevafecha.weekday() != 5 and nuevafecha.weekday() != 6:
            contador += 1
    return nuevafecha

# matriculacion de alumnos
workbook = xlrd.open_workbook("primero2021_12_10.xlsx")
sheet = workbook.sheet_by_index(0)
linea = 1
periodo = Periodo.objects.get(pk=112)
with open(csv_filepathname3, 'w', newline='') as csvfile:
    spamwriter = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    for rowx in range(sheet.nrows):
        if linea>1:
            cols = sheet.row_values(rowx)
            cedula = cols[0].strip().upper()
            print(cedula)
            bandera = True
            if Persona.objects.filter(cedula=cedula).exists():
                persona = Persona.objects.filter(cedula=cedula)[0]
                sesion = Sesion.objects.get(pk=int(cols[2]))
                carrera = Carrera.objects.get(pk=int(cols[1]))
                sede = Sede.objects.get(pk=1)
                modalidad = Modalidad.objects.get(pk=int(cols[5]))
                cordinacion_alias = str(carrera.coordinacion_set.all()[0].alias)
                # cordinacion_alias = 'FESAD'
                colegio = persona.inscripcion_set.all()[0].colegio
                p = persona.mi_perfil()
                raza_id = 6
                if p:
                    raza_id = persona.mi_perfil().raza_id

                if not Inscripcion.objects.filter(persona=persona,carrera=carrera).exists():
                    inscripcion = Inscripcion(persona=persona,
                                              fecha=datetime.now().date(),
                                              carrera=carrera,
                                              modalidad=modalidad,
                                              sesion=sesion,
                                              sede=sede,
                                              colegio=colegio,
                                              aplica_b2=True,
                                              fechainicioprimernivel=convertirfecha2('2020-11-23'),
                                              fechainiciocarrera=convertirfecha2('2020-11-02'))
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

                    perfil_inscripcion.raza_id =  raza_id
                    perfil_inscripcion.save()
                    inscripciontesdrive = InscripcionTesDrive(inscripcion=inscripcion,
                                                              licencia=False,
                                                              record=False,
                                                              certificado_tipo_sangre=False,
                                                              prueba_psicosensometrica=False,
                                                              certificado_estudios=False)
                    inscripciontesdrive.save()
                    # inscripcion.mi_malla()
                    inscripcion.malla_inscripcion()
                    inscripcion.actualizar_nivel()
                    if USA_TIPOS_INSCRIPCIONES:
                        inscripciontipoinscripcion = InscripcionTipoInscripcion(inscripcion=inscripcion,
                                                                                tipoinscripcion_id=TIPO_INSCRIPCION_INICIAL)
                        inscripciontipoinscripcion.save()
                    # persona.creacion_persona(request.session['nombresistema'])
                else:
                    inscripcion = Inscripcion.objects.filter(persona=persona,carrera=carrera)[0]
                    perfil_inscripcion = inscripcion.persona.mi_perfil()
                    perfil_inscripcion.raza_id = raza_id
                    perfil_inscripcion.save()
                # inscripcion = Inscripcion.objects.filter(persona=persona,carrera=carrera)[0]
                inscripcion.sesion = sesion
                inscripcion.save()
                # considerar si que existe en titulo persona
                if not persona.tiene_otro_titulo(inscripcion=inscripcion):
                    nivel = Nivel.objects.get(periodo=periodo, sesion=sesion, paralelo__icontains=cordinacion_alias)
                    # # matricula
                    # if inscripcion.matricula_periodo(periodo):
                    #     matricula = inscripcion.matricula_periodo(periodo)
                    #     Matricula.objects.filter(id=matricula.id).delete()


                    if not inscripcion.matricula_periodo(periodo):
                        matricula = Matricula(inscripcion=inscripcion,
                                              nivel=nivel,
                                              pago=False,
                                              iece=False,
                                              becado=False,
                                              porcientobeca=0,
                                              fecha=convertirfecha2('2020-12-10'),
                                              hora=datetime.now().time(),
                                              fechatope=fechatope(datetime.now().date()))
                        matricula.save()
                    else:
                        matricula = Matricula.objects.get(inscripcion=inscripcion, nivel=nivel)
                    print(u"matriculado %s" % cedula)
                    data = [u"matriculado %s" % cedula]
                    spamwriter.writerow(data)


                    asignatura_malla=RecordAcademico.objects.values_list('asignatura__id',flat=True).filter(asignaturamalla__nivelmalla__id__lt=int(cols[4]), aprobada=True)

                    for materia in Materia.objects.filter(nivel__periodo=periodo, paralelo=str(cols[3].strip()), asignaturamalla__malla__carrera=carrera, nivel__sesion=sesion, asignaturamalla__nivelmalla__id=int(cols[4])):
                        if not MateriaAsignada.objects.filter(matricula=matricula,materia=materia).exists():
                            matriculas = matricula.inscripcion.historicorecordacademico_set.filter(asignatura=materia.asignatura, fecha__lt=materia.nivel.fin).count() + 1
                            materiaasignada = MateriaAsignada(matricula=matricula,
                                                              materia=materia,
                                                              notafinal=0,
                                                              asistenciafinal=0,
                                                              cerrado=False,
                                                              matriculas=matriculas,
                                                              observaciones='',
                                                              estado_id=NOTA_ESTADO_EN_CURSO)
                            materiaasignada.save()
                            materiaasignada.asistencias()
                            materiaasignada.evaluacion()
                            materiaasignada.mis_planificaciones()
                            materiaasignada.save()
                            print(u"matriculado (%s) en la materia %s " % (cedula, materia))
                            data = [u"matriculado (%s) en la materia %s " % (cedula, materia)]
                            spamwriter.writerow(data)
                        else:
                            print(u"ya estaba matriculado (%s) en la materia %s " % (cedula, materia))
                            data = [u"ya estaba matriculado (%s) en la materia %s " % (cedula, materia)]
                            spamwriter.writerow(data)
                        # actualizo de una vez el aula virtual
                        # materia.crear_actualizar_estudiantes_curso(moodle, 1)
                    inscripcion.actualizar_nivel()
                    matricula.actualiza_matricula()
                    matricula.inscripcion.actualiza_estado_matricula()
                    matricula.grupo_socio_economico(1)
                    matricula.calcula_nivel()
        linea += 1
        print (linea)
