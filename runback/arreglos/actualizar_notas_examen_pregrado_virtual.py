#!/usr/bin/env python

import os
import sys
import time



SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from sga.models import *
from sga.commonviews import *

try:
    periodo = Periodo.objects.filter(status=True, id=90)[0]
    cursor = connections['moodle_db'].cursor()
    carreras = Carrera.objects.filter(status=True, id__in =[134])
    for carrera in carreras:
        matriculas = Matricula.objects.filter(status=True, nivel__periodo=periodo, inscripcion__carrera=carrera).distinct().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
        cont=0
        for matricula in matriculas:
            lista = ""
            sql_examenes = ""
            nota = 0
            fullname = ""
            shortname = ""
            materiaasignadas = matricula.materiaasignada_set.filter(status=True,materiaasignadaretiro__isnull=True, materia__esintroductoria=False, estado__id__in=[2,3]).exclude(materia__asignatura_id__in =[1465, 3334,3320, 2477 ]).order_by( 'materia__id').distinct()
            for materiaasignada in materiaasignadas:
                nota=None
                cont += 1
                sql_examenes = """  SELECT DISTINCT test.id AS id_examen, test.name AS nombre_examen,notatest.grade AS calificacion, co.fullname, co.shortname, TO_TIMESTAMP( test.timeopen) AS fechainicio, TO_TIMESTAMP(test.timeclose) AS fechafin
                                    FROM mooc_quiz_grades notatest
                                    INNER JOIN mooc_quiz test ON notatest.quiz=test.id
                                    INNER JOIN mooc_user u ON u.id=notatest.userid
                                    INNER JOIN mooc_course co ON  co.id=test.course
                                    WHERE notatest.grade >= 0 AND u.idnumber='%s' AND co.id IN (%s) AND test.name LIKE '%s' 
                                                        """ % (str(matricula.inscripcion.persona.identificacion()), str(materiaasignada.materia.idcursomoodle), "%EXAMEN DE RECUPERACIÓN%")
                cursor.execute(sql_examenes)
                datosexamenes = cursor.fetchall()
                if datosexamenes:
                    for dato in datosexamenes:
                        id_actividad = dato[0]
                        nombreactividadsakai = dato[1]
                        nota = dato[2]
                    if nota:
                        if type(nota) is Decimal:
                            campo = materiaasignada.campo("RE")
                            if campo:
                                if null_to_decimal(campo.valor) != float(nota):
                                    actualizar_nota_planificacion(materiaasignada.id, "RE", nota)
                                    auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                                                                    calificacion=nota)
                                    auditorianotas.save()
                            print("%s Migrada : %s - (%s) - %s" % (cont, materiaasignada, nota, materiaasignada.materia.asignatura.id))
    # for carrera in carreras:
    #     matriculas = Matricula.objects.filter(status=True, nivel__periodo=periodo, inscripcion__carrera=carrera).distinct().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
    #     cont=0
    #     # ingenieria
    #     # nivel = 418 FACI, carrera_id=133 TECNOLOGIAS id_curso=1305 totalestudiantes=77
    #     # nivel = 419 FACAC, carrera_id=134 TURISMO  id_curso=1299 totalestudiantes=42
    #     # nivel = 420 FACE, carrera_id=129 IDIOMAS  id_curso=1304 totalestudiantes=77
    #     # nivel = 420 FACE, carrera_id=127 EDUCACIÓN INICIAL  id_curso=1303 totalestudiantes=177
    #     # nivel = 420 FACE, carrera_id=135 EDUCACIÓN BÁSICA  id_curso=1302 totalestudiantes=225
    #     # nivel = 421 FASO, carrera_id=131 COMUNICACIÓN id_curso=1301 totalestudiantes=108
    #     # nivel = 421 FASO, carrera_id=130 TRABAJO SOCIAL id_curso=1300 totalestudiantes=182
    #     # nivel = 421 FASO, carrera_id=126 DERECHO id_curso=1298 totalestudiantes=555
    #     # nivel = 421 FASO, carrera_id=128 ECONOMÍA id_curso=1307 totalestudiantes=111
    #     # nivel = 421 FASO, carrera_id=132 PSICOLOGÍA id_curso=1306 totalestudiantes=422
    #     if carrera.id == 133:
    #         id_curso =1305
    #     elif carrera.id == 134:
    #         id_curso = 1299
    #     elif carrera.id == 129:
    #         id_curso = 1304
    #     elif carrera.id == 127:
    #         id_curso = 1303
    #     elif carrera.id == 135:
    #         id_curso = 1302
    #     elif carrera.id == 131:
    #         id_curso = 1301
    #     elif carrera.id == 130:
    #         id_curso = 1300
    #     elif carrera.id == 126:
    #         id_curso = 1308
    #     elif carrera.id == 128:
    #         id_curso = 1307
    #     elif carrera.id == 132:
    #         id_curso = 1306
    #     for matricula in matriculas:
    #         lista = ""
    #         sql_examenes = ""
    #         nota = 0
    #         fullname = ""
    #         shortname = ""
    #         materiaasignadas = matricula.materiaasignada_set.filter(status=True,materiaasignadaretiro__isnull=True, materia__esintroductoria=False).exclude(estado=1).order_by( 'materia__id').distinct()
    #         for materiaasignada in materiaasignadas:
    #             cont += 1
    #             sql_examenes = """  SELECT DISTINCT test.id AS id_examen, test.name AS nombre_examen,notatest.grade AS calificacion, co.fullname, co.shortname, TO_TIMESTAMP( test.timeopen) AS fechainicio, TO_TIMESTAMP(test.timeclose) AS fechafin
    #                                 FROM mooc_quiz_grades notatest
    #                                 INNER JOIN mooc_quiz test ON notatest.quiz=test.id
    #                                 INNER JOIN mooc_user u ON u.id=notatest.userid
    #                                 INNER JOIN mooc_course co ON  co.id=test.course
    #                                 WHERE notatest.grade >= 0 AND u.idnumber='%s' AND co.id IN (%s) AND test.name LIKE '%s' AND test.name LIKE '%s'
    #                                                     """ % (str(matricula.inscripcion.persona.identificacion()), str(id_curso), "%"+str(materiaasignada.materia.asignatura.id)+"%", "%"+str('RECUPERACIÓN')+"%")
    #             cursor.execute(sql_examenes)
    #             datosexamenes = cursor.fetchall()
    #             if datosexamenes:
    #                 for dato in datosexamenes:
    #                     id_actividad = dato[0]
    #                     nombreactividadsakai = dato[1]
    #                     nota = dato[2]
    #                     fullname = dato[3]
    #                     shortname = dato[4]
    #                     fecha_inicio = dato[5]
    #                     fecha_fin = dato[6]
    #                     observacion='1er examen pregrado virtual'
    #                     if nota:
    #                         modeloevaluativo = materiaasignada.materia.modeloevaluativo
    #                         detallemodeloevaluativo = modeloevaluativo.campo("RE")
    #                         # 37
    #                         if EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada, detallemodeloevaluativo=detallemodeloevaluativo).exists():
    #                             evaluacion = EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada,detallemodeloevaluativo=detallemodeloevaluativo)[0]
    #                             if evaluacion.valor < nota:
    #                                 campo = materiaasignada.campo("RE")
    #                                 # if ActividadesSakaiAlumno.objects.filter(status=True,
    #                                 #                                          inscripcion=matricula.inscripcion,
    #                                 #                                          materia=materiaasignada.materia,
    #                                 #                                          tipo=4).exists():
    #                                 #     actividadsakai = \
    #                                 #         ActividadesSakaiAlumno.objects.filter(status=True,
    #                                 #                                               inscripcion=matricula.inscripcion,
    #                                 #                                               materia=materiaasignada.materia,
    #                                 #                                               tipo=4)[0]
    #                                 #     actividadsakai.notaposible = detallemodeloevaluativo.notaminima
    #                                 #     actividadsakai.observacion = observacion
    #                                 #     actividadsakai.nombreactividadsakai = nombreactividadsakai
    #                                 #     actividadsakai.fechainicio = fecha_inicio
    #                                 #     actividadsakai.fechafin = fecha_fin
    #                                 #     actividadsakai.nota = nota
    #                                 #     actividadsakai.pendiente=False
    #                                 # else:
    #                                 #     actividadsakai = ActividadesSakaiAlumno(idactividadsakai=id_actividad,
    #                                 #                                             nombreactividadsakai=nombreactividadsakai,
    #                                 #                                             inscripcion=matricula.inscripcion,
    #                                 #                                             materia=materiaasignada.materia,
    #                                 #                                             tipo=4, observacion=observacion,
    #                                 #                                             notaposible=detallemodeloevaluativo.notaminima,
    #                                 #                                             fechainicio=fecha_inicio, nota=nota,
    #                                 #                                             pendiente=False,
    #                                 #                                             fechafin=fecha_fin)
    #                                 # if actividadsakai:
    #                                 #     actividadsakai.save()
    #                                 # actualizar_nota(materiaasignada,"EX2", nota)
    #                                 if type(nota) is Decimal:
    #                                     if campo:
    #                                         if null_to_decimal(campo.valor) != float(nota):
    #                                             actualizar_nota_proceso(materiaasignada, "RE", nota)
    #                                 else:
    #                                     if campo:
    #                                         if null_to_decimal(campo.valor) != float(0):
    #                                             actualizar_nota_proceso(materiaasignada, "RE", nota)
    #                                 print("%s Migrada: %s - (%s) - %s" % ( cont, materiaasignada, nota, materiaasignada.materia.asignatura.id))
    #                             # else:
    #                             #     if ActividadesSakaiAlumno.objects.filter(status=True,
    #                             #                                              inscripcion=matricula.inscripcion,
    #                             #                                              materia=materiaasignada.materia,
    #                             #                                              tipo=4).exists():
    #                             #         actividadsakai = \
    #                             #             ActividadesSakaiAlumno.objects.filter(status=True,
    #                             #                                                   inscripcion=matricula.inscripcion,
    #                             #                                                   materia=materiaasignada.materia,
    #                             #                                                   tipo=4)[0]
    #                             #         actividadsakai.notaposible = detallemodeloevaluativo.notaminima
    #                             #         actividadsakai.observacion = observacion
    #                             #         actividadsakai.nombreactividadsakai = nombreactividadsakai
    #                             #         actividadsakai.fechainicio = fecha_inicio
    #                             #         actividadsakai.fechafin = fecha_fin
    #                             #         actividadsakai.nota = evaluacion.valor
    #                             #         actividadsakai.pendiente=False
    #                             #     else:
    #                             #         actividadsakai = ActividadesSakaiAlumno(idactividadsakai=id_actividad,
    #                             #                                                 nombreactividadsakai=nombreactividadsakai,
    #                             #                                                 inscripcion=matricula.inscripcion,
    #                             #                                                 materia=materiaasignada.materia,
    #                             #                                                 tipo=4, observacion=observacion,
    #                             #                                                 notaposible=detallemodeloevaluativo.notaminima,
    #                             #                                                 fechainicio=fecha_inicio,pendiente=False,
    #                             #                                                 nota=evaluacion.valor,
    #                             #                                                 fechafin=fecha_fin)
    #                             #     if actividadsakai:
    #                             #         actividadsakai.save()
    #                         else:
    #                             campo = materiaasignada.campo("RE")
    #                             # if ActividadesSakaiAlumno.objects.filter(status=True, inscripcion=matricula.inscripcion,
    #                             #                                          materia=materiaasignada.materia,
    #                             #                                          tipo=4).exists():
    #                             #     actividadsakai = ActividadesSakaiAlumno.objects.filter(status=True,
    #                             #                                               inscripcion=matricula.inscripcion,
    #                             #                                               materia=materiaasignada.materia, tipo=4)[0]
    #                             #     actividadsakai.notaposible = detallemodeloevaluativo.notaminima
    #                             #     actividadsakai.observacion = observacion
    #                             #     actividadsakai.nombreactividadsakai = nombreactividadsakai
    #                             #     actividadsakai.fechainicio = fecha_inicio
    #                             #     actividadsakai.fechafin = fecha_fin
    #                             #     actividadsakai.nota = nota
    #                             #     actividadsakai.pendiente=False
    #                             # else:
    #                             #     actividadsakai = ActividadesSakaiAlumno(idactividadsakai=id_actividad,
    #                             #                                             nombreactividadsakai=nombreactividadsakai,
    #                             #                                             inscripcion=matricula.inscripcion,
    #                             #                                             materia=materiaasignada.materia,
    #                             #                                             tipo=4, observacion=observacion,
    #                             #                                             notaposible=detallemodeloevaluativo.notaminima,
    #                             #                                             fechainicio=fecha_inicio, nota=nota,pendiente=False,
    #                             #                                             fechafin=fecha_fin)
    #                             # if actividadsakai:
    #                             #     actividadsakai.save()
    #                             if type(nota) is Decimal:
    #                                 if campo:
    #                                     if null_to_decimal(campo.valor) != float(nota):
    #                                         actualizar_nota_proceso(materiaasignada, "RE", nota)
    #                             else:
    #                                 if campo:
    #                                     if null_to_decimal(campo.valor) != float(0):
    #                                         actualizar_nota_proceso(materiaasignada, "RE", nota)
    #                             print("%s Migrada 2: %s - (%s) - %s" % (cont,materiaasignada, nota, materiaasignada.materia.asignatura.id))
    #             else:
    #                 print("%s No hay examen: %s - %s" % (cont, materiaasignada, materiaasignada.materia.asignatura.id))
except Exception as ex:
    print('error: %s' % ex)