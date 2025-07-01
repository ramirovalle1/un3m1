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
    matriculas = Matricula.objects.filter(status=True, nivel__periodo=periodo,inscripcion__carrera__id=100).distinct().order_by(
        'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
    cont=1
    cursor = connections['db_moodle_virtual'].cursor()
    n1o = 20
    n2o = 30
    n3o = 10
    for matricula in matriculas:
        lista = ""
        sql_examenes = ""
        nota = 0
        fullname = ""
        shortname = ""
        materiaasignadas = matricula.materiaasignada_set.filter(status=True, materiaasignadaretiro__isnull=True, materia__asignatura__id=2677).order_by( 'materia__id').distinct()
        for materiaasignada in materiaasignadas:
            listacategorias=[]
            sql_examenes = """  SELECT b.itemname AS Actividad,COALESCE(g.fullname,'CATEGORIA_PRINCIPAL'),
                                COALESCE(ROUND(d.rawgrademax,2),0) AS NotaMaximaCATE,COALESCE(ROUND(d.rawgrade,2),0) AS NotaInicial, 
                                COALESCE(ROUND(d.finalgrade,2),0) AS NotaFInal, COALESCE(UPPER(a.fullname),g.fullname), b.iteminstance
                                FROM mooc_grade_grades d
                                INNER JOIN mooc_grade_items b ON d.itemid=b.id AND b.courseid=%s
                                left JOIN mooc_grade_categories a ON a.courseid=b.courseid AND a.id=b.iteminstance AND a.depth=2
                                left JOIN mooc_grade_categories g ON g.id=b.categoryid AND g.courseid=b.courseid
                                INNER JOIN mooc_user e ON d.userid=e.id
                                INNER JOIN mooc_course AS c ON c.id=b.courseid
                                LEFT JOIN mooc_user AS f ON f.id=d.usermodified
                                WHERE e.idnumber ='%s'
                                ORDER BY g.fullname  """ % ( materiaasignada.materia.idcursomoodle, str(matricula.inscripcion.persona.identificacion()))
            cursor.execute(sql_examenes)
            datosnotas = cursor.fetchall()
            n1=0
            n2=0
            n3=0
            n1b=0
            n2b=0
            n3b=0
            contn1=0
            contn2=0
            contn3=0
            notamaximacate=0
            if datosnotas:
                for dato in datosnotas:
                    if dato:
                        id_actividadsakai = dato[6] if dato else ""
                        actividad = dato[0] if dato else ""
                        categoria = dato[1] if dato else ""
                        notamaximacate = dato[2] if dato else ""
                        notainicial = dato[3] if dato else ""
                        notafinal = dato[4] if dato else ""
                        categoriafinal = dato[5] if dato else ""
                        if notainicial>notafinal:
                            notafinal=notainicial
                        if categoriafinal == 'N1' and categoriafinal==categoria:
                            if notafinal > n1o:
                                notafinal = (notafinal/notamaximacate) * n1o
                            n1+= notafinal
                            contn1+=1
                        if categoriafinal == 'N2' and categoriafinal==categoria:
                            if notafinal > n2o:
                                notafinal = (notafinal/notamaximacate) * n2o
                            n2+= notafinal
                            contn2 += 1
                        if categoriafinal == 'N3' and categoriafinal==categoria:
                            if notafinal > n3o:
                                notafinal = (notafinal/notamaximacate) * n3o
                            n3+= notafinal
                            contn3 += 1
                        if ActividadesSakaiAlumno.objects.filter(status=True,
                                                                 inscripcion=matricula.inscripcion,
                                                                 materia=materiaasignada.materia,
                                                                 tipo=2, idactividadsakai=id_actividadsakai).exists():
                            actividadsakai = ActividadesSakaiAlumno.objects.filter(status=True,
                                                                                   inscripcion=matricula.inscripcion,
                                                                                   materia=materiaasignada.materia,
                                                                                   tipo=2, idactividadsakai=id_actividadsakai)[0]
                            actividadsakai.notaposible = notamaximacate
                            actividadsakai.observacion = "Migrado arreglo"
                            actividadsakai.nombreactividadsakai = actividad
                            actividadsakai.nota = notafinal
                            actividadsakai.pendiente = False
                        else:
                            actividadsakai = ActividadesSakaiAlumno(idactividadsakai=id_actividadsakai,
                                                                    nombreactividadsakai=actividad,
                                                                    inscripcion=matricula.inscripcion,
                                                                    materia=materiaasignada.materia,
                                                                    tipo=4, observacion="Migrado arreglo",
                                                                    notaposible=notamaximacate,
                                                                    nota=notafinal,
                                                                    pendiente=False)
                        if actividadsakai:
                            actividadsakai.save()

                        if categoria == 'CATEGORIA_PRINCIPAL' and categoriafinal=='N1':
                            n1b=null_to_decimal(notafinal,0)
                        if categoria == 'CATEGORIA_PRINCIPAL' and categoriafinal=='N2':
                            n2b=null_to_decimal(notafinal,0)
                        if categoria == 'CATEGORIA_PRINCIPAL' and categoriafinal=='N3':
                            n3b=null_to_decimal(notafinal,0)
                n1=null_to_decimal(n1/contn1,0)
                n2=null_to_decimal(n2/contn2,0)
                n3=null_to_decimal(n3/contn3,0)

                if n1 != n1b:
                    print("%s Diferentes notas n1: %s - (%s - %s)" % (cont, materiaasignada, n1, n1b))
                modeloevaluativo = materiaasignada.materia.modeloevaluativo
                detallemodeloevaluativo = modeloevaluativo.campo("N1")
                if EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada, detallemodeloevaluativo=detallemodeloevaluativo).exists():
                    evaluacion = EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada,detallemodeloevaluativo=detallemodeloevaluativo)[0]
                    if evaluacion.valor < n1:
                        print("%s Migrada: %s - (%s)" % (cont, materiaasignada, n1))
                        campo = materiaasignada.campo("N1")
                        if type(n1) is Decimal:
                            if campo:
                                if null_to_decimal(campo.valor) != float(n1):
                                    actualizar_nota_planificacion(materiaasignada.id, "N1", n1)
                                    auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                                                                    calificacion=n1)
                                    auditorianotas.save()
                        else:
                            if campo:
                                if null_to_decimal(campo.valor) != float(0):
                                    actualizar_nota_planificacion(materiaasignada.id, "N1", n1)
                                    auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                                                                    calificacion=0)
                                    auditorianotas.save()
                else:
                    campo = materiaasignada.campo("N1")
                    print("%s Migrada: %s - (%s)" % (cont, materiaasignada, n1))
                    if type(n1) is Decimal:
                        if campo:
                            if null_to_decimal(campo.valor) != float(n1):
                                actualizar_nota_planificacion(materiaasignada.id, "N1", n1)
                                auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                                                                calificacion=n1)
                                auditorianotas.save()
                    else:
                        if campo:
                            if null_to_decimal(campo.valor) != float(0):
                                actualizar_nota_planificacion(materiaasignada.id, "N1", n1)
                                auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                                                                calificacion=0)
                                auditorianotas.save()


            # if n2 != n2b:
            #     print("%s Diferentes notas n2: %s - (%s - %s)" % (cont, materiaasignada, n2, n2b))
            # modeloevaluativo = materiaasignada.materia.modeloevaluativo
            # detallemodeloevaluativo = modeloevaluativo.campo("N2")
            # if EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada, detallemodeloevaluativo=detallemodeloevaluativo).exists():
            #     evaluacion = EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada,detallemodeloevaluativo=detallemodeloevaluativo)[0]
            #     if evaluacion.valor < n2:
            #         campo = materiaasignada.campo("N2")
            #         if type(n2) is Decimal:
            #             if campo:
            #                 if null_to_decimal(campo.valor) != float(n2):
            #                     actualizar_nota_planificacion(materiaasignada.id, "N2", n2)
            #                     auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
            #                                                     calificacion=n2)
            #                     auditorianotas.save()
            #         else:
            #             if campo:
            #                 if null_to_decimal(campo.valor) != float(0):
            #                     actualizar_nota_planificacion(materiaasignada.id, "N2", n2)
            #                     auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
            #                                                     calificacion=0)
            #                     auditorianotas.save()
            # else:
            #     campo = materiaasignada.campo("N2")
            #     if type(n2) is Decimal:
            #         if campo:
            #             if null_to_decimal(campo.valor) != float(n2):
            #                 actualizar_nota_planificacion(materiaasignada.id, "N2", n2)
            #                 auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
            #                                                 calificacion=n2)
            #                 auditorianotas.save()
            #     else:
            #         if campo:
            #             if null_to_decimal(campo.valor) != float(0):
            #                 actualizar_nota_planificacion(materiaasignada.id, "N2", n2)
            #                 auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
            #                                                 calificacion=0)
            #                 auditorianotas.save()
            #
            # if n3 != n3b:
            #     print("%s Diferentes notas n3: %s - (%s - %s)" % (cont, materiaasignada, n3, n3b))
            # modeloevaluativo = materiaasignada.materia.modeloevaluativo
            # detallemodeloevaluativo = modeloevaluativo.campo("N3")
            # if EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada, detallemodeloevaluativo=detallemodeloevaluativo).exists():
            #     evaluacion = EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada,detallemodeloevaluativo=detallemodeloevaluativo)[0]
            #     if evaluacion.valor < n3:
            #         campo = materiaasignada.campo("N3")
            #         if type(n3) is Decimal:
            #             if campo:
            #                 if null_to_decimal(campo.valor) != float(n3):
            #                     actualizar_nota_planificacion(materiaasignada.id, "N3", n3)
            #                     auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
            #                                                     calificacion=n3)
            #                     auditorianotas.save()
            #         else:
            #             if campo:
            #                 if null_to_decimal(campo.valor) != float(0):
            #                     actualizar_nota_planificacion(materiaasignada.id, "N3", n3)
            #                     auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
            #                                                     calificacion=0)
            #                     auditorianotas.save()
            # else:
            #     campo = materiaasignada.campo("N3")
            #     if type(n3) is Decimal:
            #         if campo:
            #             if null_to_decimal(campo.valor) != float(n3):
            #                 actualizar_nota_planificacion(materiaasignada.id, "N3", n3)
            #                 auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
            #                                                 calificacion=n3)
            #                 auditorianotas.save()
            #     else:
            #         if campo:
            #             if null_to_decimal(campo.valor) != float(0):
            #                 actualizar_nota_planificacion(materiaasignada.id, "N3", n3)
            #                 auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
            #                                                 calificacion=0)
            #                 auditorianotas.save()
            #     print("%s Migrada: %s - (%s)" % (cont,materiaasignada, n3))
                cont+=1
except Exception as ex:
    print('error: %s' % ex)