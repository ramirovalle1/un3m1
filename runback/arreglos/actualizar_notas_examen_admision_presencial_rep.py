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
# ECONOMIA 96
# COMUNICACION 102
# DERECHO 103
#
#
# PSICOLOGIA 97
# TRABAJO SOCIAL 98
# EDUCACION BASICA 99
# EDUCACION INICIAL 100
# IDIOMAS 101
# TURISMO 104
# TECNOLOGIA 105

try:
    periodo = Periodo.objects.filter(status=True, id=90)[0]
    matriculas = Matricula.objects.filter(status=True, nivel__periodo=periodo, estado_matricula__in=[2,3], inscripcion__carrera__in=[64,
87,
65,
83,
82,
67,
73,
47,
51,
68,
84,
55,
107,
108,
74,
85,
66,
52,
124,
86], inscripcion__inscripcionmalla__malla_id__in=[151,
163,
155,
166,
169,
167,
168,
165,
156,
162,
152,
159,
153,
160,
157,
158,
164,
154,
184,
161]).distinct().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
    cont = 0
    cursor = connections['db_moodle_virtual'].cursor()
    for matricula in matriculas:
        cont+=1
        sql_examenes2 = ""
        nota = None
        materiaasignadas = matricula.materiaasignada_set.filter(materia__asignatura_id__in =[2690,2688], status=True,materiaasignadaretiro__isnull=True, materia__esintroductoria=False).order_by( 'materia__id').distinct()
        for materiaasignada in materiaasignadas:
            nota=None
            if materiaasignada.materia.asignatura.id == 2690:
                codigoasignatura=1507
            else:
                codigoasignatura=materiaasignada.materia.asignatura.id
            sql_examenes2 = """ SELECT DISTINCT test.id AS id_examen, test.name AS nombre_examen,
                                            notatest.grade AS calificacion, co.fullname, 
                                            co.shortname, TO_TIMESTAMP( test.timeopen) AS fechainicio, TO_TIMESTAMP(test.timeclose) AS fechafin
                                            FROM mooc_quiz_grades notatest
                                            INNER JOIN mooc_quiz test ON notatest.quiz=test.id
                                            INNER JOIN mooc_user u ON u.id=notatest.userid
                                            INNER JOIN mooc_course co ON  co.id=test.course
                                            WHERE notatest.grade >= 0 
                                            AND u.idnumber='%s' 
                                            AND co.shortname LIKE '%s'  
                                            """ % (str(matricula.inscripcion.persona.identificacion()),
                                                   "%2020-RP-" + str(codigoasignatura) + "%")
            cursor.execute(sql_examenes2)
            datosexamenes2 = cursor.fetchall()
            if datosexamenes2:
                for nota2 in datosexamenes2:
                    nota = nota2[2]
            if type(nota) is Decimal:
                # modeloevaluativo = materiaasignada.materia.modeloevaluativo
                # detallemodeloevaluativo = modeloevaluativo.campo("EX")
                # # 66
                # if EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada, detallemodeloevaluativo=detallemodeloevaluativo).exists():
                #     evaluacion =  EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada, detallemodeloevaluativo=detallemodeloevaluativo)[0]
                #     if evaluacion.valor != nota:
                campo = materiaasignada.campo("EX")
                if campo:
                    if null_to_decimal(campo.valor) != float(nota):
                        actualizar_nota_planificacion(materiaasignada.id, "EX", nota)
                        auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                                                        calificacion=nota)
                        auditorianotas.save()
                # else:
                #     if campo:
                #         if null_to_decimal(campo.valor) != float(0):
                #             actualizar_nota_planificacion(materiaasignada.id, "EX", nota)
                #             auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                #                                             calificacion=0)
                #             auditorianotas.save()
                # else:
                #     campo = materiaasignada.campo("EX")
                #     if type(nota) is Decimal:
                #         if campo:
                #             if null_to_decimal(campo.valor) != float(nota):
                #                 actualizar_nota_planificacion(materiaasignada.id, "EX", nota)
                #                 auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                #                                                 calificacion=nota)
                #                 auditorianotas.save()
                #     else:
                #         if campo:
                #             if null_to_decimal(campo.valor) != float(0):
                #                 actualizar_nota_planificacion(materiaasignada.id, "EX", nota)
                #                 auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                #                                                 calificacion=0)
                #                 auditorianotas.save()
                print("%s Migrada: %s - (%s)" % (cont,materiaasignada, nota))



    # periodo = Periodo.objects.filter(status=True, id=82)[0]
    # matriculas = Matricula.objects.filter(status=True, nivel__periodo=periodo,
    #                                       inscripcion__carrera__id__in=[96, 97, 98, 99, 100, 101, 102, 103, 104, 105]).distinct().order_by(
    #     'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
    # cont=1
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
    #     sql_examenes = """
    #                                                 SELECT DISTINCT co.fullname, co.shortname, notatest.grade
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
    #                 if EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada, detallemodeloevaluativo=71).exists():
    #                     evaluacion = EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada,detallemodeloevaluativo=71)[0]
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

    # periodo = Periodo.objects.filter(status=True, id=82)[0]
    #
    # cursor = connections['db_moodle_virtual'].cursor()
    # sql_examenes = """  SELECT DISTINCT  u.idnumber, notatest.grade
    #                             FROM mooc_quiz_grades notatest
    #                             INNER JOIN mooc_quiz test ON notatest.quiz=test.id
    #                             INNER JOIN mooc_user u ON u.id=notatest.userid
    #                             INNER JOIN mooc_course co ON co.id=test.course
    #                             WHERE notatest.grade >= 0 AND co.shortname='%s'
    #                                                     """ % ('VIER06_LITERATU')
    # cursor.execute(sql_examenes)
    # datosexamenes = cursor.fetchall()
    # lista = []
    # cont=0
    # for dato in datosexamenes:
    #     nota = dato[1] if dato else 0
    #     identificacion = str(dato[0])
    #     materiaasignada=None
    #     if MateriaAsignada.objects.filter(matricula__inscripcion__persona__cedula=identificacion ,status=True, materiaasignadaretiro__isnull=True, materia__asignatura__id=2675, materia__nivel__periodo=periodo).exists():
    #         materiaasignada = MateriaAsignada.objects.filter(status=True, materiaasignadaretiro__isnull=True, materia__asignatura__id=2675,matricula__inscripcion__persona__cedula=identificacion, materia__nivel__periodo=periodo)[0]
    #     elif MateriaAsignada.objects.filter(status=True, materiaasignadaretiro__isnull=True, materia__asignatura__id=2675, matricula__inscripcion__persona__pasaporte=identificacion, materia__nivel__periodo=periodo).exists():
    #         materiaasignada = MateriaAsignada.objects.filter(status=True, materiaasignadaretiro__isnull=True, materia__asignatura__id=2675,matricula__inscripcion__persona__pasaporte=identificacion, materia__nivel__periodo=periodo)[0]
    #     elif MateriaAsignada.objects.filter(status=True, materiaasignadaretiro__isnull=True, materia__asignatura__id=2675, matricula__inscripcion__persona__ruc=identificacion, materia__nivel__periodo=periodo).exists():
    #         materiaasignada = MateriaAsignada.objects.filter(status=True, materiaasignadaretiro__isnull=True, materia__asignatura__id=2675,matricula__inscripcion__persona__ruc=identificacion, materia__nivel__periodo=periodo)[0]
    #     if materiaasignada:
    #         modeloevaluativo = materiaasignada.materia.modeloevaluativo
    #         detallemodeloevaluativo = modeloevaluativo.campo("EX")
    #         # 71
    #         if EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada,detallemodeloevaluativo=detallemodeloevaluativo).exists():
    #             evaluacion =  EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada, detallemodeloevaluativo=detallemodeloevaluativo)[ 0]
    #             if evaluacion.valor < nota:
    #                 campo = materiaasignada.campo("EX")
    #                 if type(nota) is Decimal:
    #                     if campo:
    #                         if null_to_decimal(campo.valor) != float(nota):
    #                             actualizar_nota_planificacion(materiaasignada.id, "EX", nota)
    #                             auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
    #                                                             calificacion=nota)
    #                             auditorianotas.save()
    #                 else:
    #                     if campo:
    #                         if null_to_decimal(campo.valor) != float(0):
    #                             actualizar_nota_planificacion(materiaasignada.id, "EX", nota)
    #                             auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
    #                                                             calificacion=0)
    #                             auditorianotas.save()
    #         else:
    #             campo = materiaasignada.campo("EX")
    #             if type(nota) is Decimal:
    #                 if campo:
    #                     if null_to_decimal(campo.valor) != float(nota):
    #                         actualizar_nota_planificacion(materiaasignada.id, "EX", nota)
    #                         auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
    #                                                         calificacion=nota)
    #                         auditorianotas.save()
    #             else:
    #                 if campo:
    #                     if null_to_decimal(campo.valor) != float(0):
    #                         actualizar_nota_planificacion(materiaasignada.id, "EX", nota)
    #                         auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
    #                                                         calificacion=0)
    #                         auditorianotas.save()
    #     print("%s Migrada: %s - (%s)" % (cont, materiaasignada, nota))
    #     cont+=1
except Exception as ex:
    print('error: %s' % ex)
