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

try:
    periodo = Periodo.objects.filter(status=True, id=82)[0]
    # matriculas = Matricula.objects.filter(status=True, nivel__periodo=periodo, inscripcion__carrera__in=[51,65,66,68,74,84,85,124]).distinct().order_by(
    matriculas = Matricula.objects.filter(status=True, nivel__periodo=periodo, inscripcion__carrera__in=[86]).distinct().order_by( 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
    cont=1
    cursor = connections['db_moodle_virtual'].cursor()
    for matricula in matriculas:
        lista = ""
        sql_examenes2 = ""
        sql_examenes1 = ""
        nota = None
        id_actividad=None
        fullname = ""
        shortname = ""
        observacion = ""
        nombreactividadsakai = ""
        fecha_inicio = ""
        fecha_fin = ""
        materiaasignadas = matricula.materiaasignada_set.filter(status=True,materiaasignadaretiro__isnull=True).exclude(estado=1).order_by( 'materia__id').distinct()
        for materiaasignada in materiaasignadas:
            sql_examenes2 = """ SELECT DISTINCT test.id AS id_examen, test.name AS nombre_examen,notatest.grade AS calificacion, co.fullname, co.shortname, TO_TIMESTAMP( test.timeopen) AS fechainicio, TO_TIMESTAMP(test.timeclose) AS fechafin
                                                    FROM mooc_quiz_grades notatest
                                                    INNER JOIN mooc_quiz test ON notatest.quiz=test.id
                                                    INNER JOIN mooc_user u ON u.id=notatest.userid
                                                    INNER JOIN mooc_course co ON  co.id=test.course
                                                    WHERE notatest.grade >= 0 AND u.idnumber='%s' AND co.shortname LIKE'%s'
                                                                                """ % (
                str(matricula.inscripcion.persona.identificacion()),
                "%" + str(materiaasignada.materia.asignatura.id) + "%")
            cursor.execute(sql_examenes2)
            datosexamenes2 = cursor.fetchall()
            if datosexamenes2:
                observacion ='2do examen'
                for nota2 in datosexamenes2:
                    id_actividad = nota2[0]
                    nombreactividadsakai=nota2[1]
                    nota = nota2[2]
                    fullname = nota2[3]
                    shortname = nota2[4]
                    fecha_inicio = nota2[5]
                    fecha_fin = nota2[6]
            else:
                sql_examenes1 = """ SELECT DISTINCT test.id AS id_examen, test.name AS nombre_examen,notatest.grade AS calificacion, co.fullname, co.shortname, TO_TIMESTAMP( test.timeopen) AS fechainicio, TO_TIMESTAMP(test.timeclose) AS fechafin
                                                           FROM mooc_quiz_grades notatest
                                                           INNER JOIN mooc_quiz test ON notatest.quiz=test.id
                                                           INNER JOIN mooc_user u ON u.id=notatest.userid
                                                           INNER JOIN mooc_course co ON  co.id=test.course
                                                           WHERE notatest.grade >= 0 AND u.idnumber='%s' AND co.fullname LIKE'%s' 
                                                                                   """ % (
                    str(matricula.inscripcion.persona.identificacion()),
                    "%" + materiaasignada.materia.asignatura.nombre + "%")
                cursor.execute(sql_examenes1)
                datosexamenes1 = cursor.fetchall()
                if datosexamenes1:
                    observacion = '1er examen'
                    for nota1 in datosexamenes1:
                        id_actividad = nota1[0]
                        nombreactividadsakai = nota1[1]
                        nota = nota1[2]
                        fullname = nota1[3]
                        shortname = nota1[4]
                        fecha_inicio = nota1[5]
                        fecha_fin = nota1[6]
                else:
                    print("%s No hay examen: %s " % (cont, materiaasignada))
            if nota:
                modeloevaluativo = materiaasignada.materia.modeloevaluativo
                detallemodeloevaluativo = modeloevaluativo.campo("EX")
                # 66
                if EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada, detallemodeloevaluativo=detallemodeloevaluativo).exists():
                    evaluacion =  EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada, detallemodeloevaluativo=detallemodeloevaluativo)[0]
                    if evaluacion.valor != nota:
                        print("%s Migrada: %s - (%s)" % (cont, materiaasignada, nota))
                        if ActividadesSakaiAlumno.objects.filter(status=True, inscripcion=matricula.inscripcion,
                                                                 materia=materiaasignada.materia, tipo=4).exists():
                            actividadsakai = \
                            ActividadesSakaiAlumno.objects.filter(status=True, inscripcion=matricula.inscripcion,
                                                                  materia=materiaasignada.materia, tipo=4)[0]
                            actividadsakai.notaposible = detallemodeloevaluativo.notaminima
                            actividadsakai.observacion = observacion
                            actividadsakai.nombreactividadsakai = nombreactividadsakai
                            actividadsakai.fechainicio = fecha_inicio
                            actividadsakai.fechafin = fecha_fin
                            actividadsakai.nota = nota
                            actividadsakai.pendiente=False
                        else:
                            actividadsakai = ActividadesSakaiAlumno(idactividadsakai=id_actividad,
                                                                    nombreactividadsakai=nombreactividadsakai,
                                                                    inscripcion=matricula.inscripcion,
                                                                    materia=materiaasignada.materia,
                                                                    tipo=4, observacion=observacion,
                                                                    notaposible=detallemodeloevaluativo.notaminima,
                                                                    fechainicio=fecha_inicio,nota=nota,pendiente=False,
                                                                    fechafin=fecha_fin)
                        if actividadsakai:
                            actividadsakai.save()
                        campo = materiaasignada.campo("EX")
                        if type(nota) is Decimal:
                            if campo:
                                if null_to_decimal(campo.valor) != float(nota):
                                    actualizar_nota_planificacion(materiaasignada.id, "EX", nota)
                                    auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                                                                    calificacion=nota)
                                    auditorianotas.save()
                        else:
                            if campo:
                                if null_to_decimal(campo.valor) != float(0):
                                    actualizar_nota_planificacion(materiaasignada.id, "EX", nota)
                                    auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                                                                    calificacion=0)
                                    auditorianotas.save()
                    else:
                        if ActividadesSakaiAlumno.objects.filter(status=True, inscripcion=matricula.inscripcion,
                                                                 materia=materiaasignada.materia, tipo=4).exists():
                            actividadsakai =  ActividadesSakaiAlumno.objects.filter(status=True, inscripcion=matricula.inscripcion,
                                                                      materia=materiaasignada.materia, tipo=4)[0]
                            actividadsakai.notaposible = detallemodeloevaluativo.notaminima
                            actividadsakai.observacion = observacion
                            actividadsakai.nombreactividadsakai = nombreactividadsakai
                            actividadsakai.fechainicio = fecha_inicio
                            actividadsakai.fechafin = fecha_fin
                            actividadsakai.nota = evaluacion.valor
                            actividadsakai.nota = pendiente=False
                        else:
                            actividadsakai = ActividadesSakaiAlumno(idactividadsakai=id_actividad,
                                                                    nombreactividadsakai=nombreactividadsakai,
                                                                    inscripcion=matricula.inscripcion,
                                                                    materia=materiaasignada.materia,
                                                                    tipo=4, observacion=observacion,
                                                                    notaposible=detallemodeloevaluativo.notaminima,
                                                                    fechainicio=fecha_inicio,
                                                                    nota=evaluacion.valor,
                                                                    pendiente=False,
                                                                    fechafin=fecha_fin)
                        if actividadsakai:
                            actividadsakai.save()
                else:
                    print("%s Migrada: %s - (%s)" % (cont, materiaasignada, nota))
                    campo = materiaasignada.campo("EX")
                    if ActividadesSakaiAlumno.objects.filter(status=True, inscripcion=matricula.inscripcion,
                                                             materia=materiaasignada.materia, tipo=4).exists():
                        actividadsakai = \
                            ActividadesSakaiAlumno.objects.filter(status=True, inscripcion=matricula.inscripcion,
                                                                  materia=materiaasignada.materia, tipo=4)[0]
                        actividadsakai.notaposible = detallemodeloevaluativo.notaminima
                        actividadsakai.observacion = observacion
                        actividadsakai.nombreactividadsakai = nombreactividadsakai
                        actividadsakai.fechainicio = fecha_inicio
                        actividadsakai.fechafin = fecha_fin
                        actividadsakai.nota = nota
                        actividadsakai.pendiente=False
                    else:
                        actividadsakai = ActividadesSakaiAlumno(idactividadsakai=id_actividad,
                                                                nombreactividadsakai=nombreactividadsakai,
                                                                inscripcion=matricula.inscripcion,
                                                                materia=materiaasignada.materia,
                                                                tipo=4, observacion=observacion,
                                                                notaposible=detallemodeloevaluativo.notaminima,
                                                                fechainicio=fecha_inicio,
                                                                nota=nota,
                                                                pendiente=False,
                                                                fechafin=fecha_fin)
                    if type(nota) is Decimal:
                        if campo:
                            if null_to_decimal(campo.valor) != float(nota):
                                actualizar_nota_planificacion(materiaasignada.id, "EX", nota)
                                auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                                                                calificacion=nota)
                                auditorianotas.save()
                    else:
                        if campo:
                            if null_to_decimal(campo.valor) != float(0):
                                actualizar_nota_planificacion(materiaasignada.id, "EX", nota)
                                auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                                                                calificacion=0)
                                auditorianotas.save()
                cont+=1

    # for matricula in matriculas:
    #     lista = ""
    #     sql_examenes = ""
    #     nota = 0
    #     fullname = ""
    #     shortname = ""
    #     materiaasignada = matricula.materiaasignada_set.filter(status=True,materiaasignadaretiro__isnull=True).order_by( 'materia__id').distinct()
    #     for x in materiaasignada:
    #         if x.materia.idcursomoodle != materiaasignada.order_by('-materia__id')[0].materia.idcursomoodle:
    #             if x.materia.idcursomoodle:
    #                 lista += str(x.materia.idcursomoodle) + ","
    #         else:
    #             lista += str(x.materia.idcursomoodle)
    #     cursor = connections['db_moodle_virtual'].cursor()
    #     sql_examenes = """ SELECT DISTINCT co.fullname, co.shortname, notatest.grade
    #                                                 FROM mooc_quiz_grades notatest
    #                                                 INNER JOIN mooc_quiz test ON notatest.quiz=test.id
    #                                                 INNER JOIN mooc_user u ON u.id=notatest.userid
    #                                                 INNER JOIN mooc_course co ON  co.id=test.course
    #                                                 WHERE notatest.grade >= 0 AND u.idnumber='%s' AND not co.id IN (%s)
    #                                             """ % (str(matricula.inscripcion.persona.identificacion()), lista)
    #     cursor.execute(sql_examenes)
    #     datosexamenes = cursor.fetchall()
    #     for dato in datosexamenes:
    #         nota = dato[2] if dato else 0
    #         fullname = dato[0] if dato else ""
    #         shortname = dato[1] if dato else ""
    #         if nota:
    #             if MateriaAsignada.objects.filter(Q(materia__asignatura__nombre__icontains=fullname) | Q(materia__asignatura__nombre__icontains=shortname), status=True, materiaasignadaretiro__isnull=True,  matricula=matricula).exists():
    #                 materiaasignada = MateriaAsignada.objects.filter( Q(materia__asignatura__nombre__icontains=fullname) | Q( materia__asignatura__nombre__icontains=shortname), status=True, materiaasignadaretiro__isnull=True, matricula=matricula)[0]
    #
    #                 if EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada, detallemodeloevaluativo=66).exists():
    #                     evaluacion = EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada,detallemodeloevaluativo=66)[0]
    #                     if evaluacion.valor < nota:
    #                         campo = materiaasignada.campo("EX")
    #                         if type(nota) is Decimal:
    #                             if campo:
    #                                 if null_to_decimal(campo.valor) != float(nota):
    #                                     actualizar_nota_planificacion(materiaasignada.id, "EX", nota)
    #                                     auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
    #                                                                     calificacion=nota)
    #                                     auditorianotas.save()
    #                         else:
    #                             if campo:
    #                                 if null_to_decimal(campo.valor) != float(0):
    #                                     actualizar_nota_planificacion(materiaasignada.id, "EX", nota)
    #                                     auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
    #                                                                     calificacion=0)
    #                                     auditorianotas.save()
    #                 else:
    #                     campo = materiaasignada.campo("EX")
    #                     if type(nota) is Decimal:
    #                         if campo:
    #                             if null_to_decimal(campo.valor) != float(nota):
    #                                 actualizar_nota_planificacion(materiaasignada.id, "EX", nota)
    #                                 auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
    #                                                                 calificacion=nota)
    #                                 auditorianotas.save()
    #                     else:
    #                         if campo:
    #                             if null_to_decimal(campo.valor) != float(0):
    #                                 actualizar_nota_planificacion(materiaasignada.id, "EX", nota)
    #                                 auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
    #                                                                 calificacion=0)
    #                                 auditorianotas.save()
    #
    #                 print("%s Migrada: %s - (%s)" % (cont,materiaasignada, nota))
    #                 cont+=1


except Exception as ex:
    print('error: %s' % ex)