#!/usr/bin/env python

import os
import sys
import time

from settings import SITE_STORAGE

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from sga.models import *
import zipfile
from xlwt import *
from sga.funciones import generar_nombre
try:
    periodo = Periodo.objects.filter(status=True, id=90)[0]
    font_style = XFStyle()
    hoy = datetime.now()
    hoy1='%s-%s-%s %s:%s:%s'%(hoy.year,hoy.month,hoy.day, hoy.hour, hoy.minute, hoy.second)
    hoy2=hoy - timedelta(hours=1)
    hoy2 = '%s-%s-%s %s:%s:%s'%(hoy2.year,hoy2.month,hoy2.day, hoy2.hour, hoy2.minute, hoy2.second)
    direccion = os.path.join(SITE_STORAGE, '../../media', 'importacionnotas')
    archivoname = generar_nombre('novedades_importacion_adm_pres_%s'%(str(periodo.id)), 'fichero.xls')
    url2 = 'https://sga.unemi.edu.ec/media/importacionnotas/%s' % (archivoname)
    filename = os.path.join(direccion, archivoname)
    wb = Workbook(encoding='utf-8')
    ws = wb.add_sheet('hoja1')
    columns = [
        (u"FACULTAD", 4000),
        (u"CARRERA", 12000),
        (u"CEDULA", 5000),
        (u"NOMBRES", 3000),
        (u"MATERIA", 4000),
        (u"NOVEDAD", 3000),
    ]
    row_num = 2
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num][0], font_style)
        ws.col(col_num).width = columns[col_num][1]
    row_num = row_num + 1
    matriculasimportacion = ImportacionNotasAdmision.objects.filter(status=True,matricula_id=207734, matricula__nivel__periodo=periodo, matricula__estado_matricula__in=[2,3])
    # matriculasimportacion2 = ImportacionNotasAdmision.objects.filter(Q(ejecuta=False, fechafin__lt=hoy), status=True, matricula__nivel__periodo=periodo, matricula__estado_matricula__in=[2,3]).exclude(id__in=matriculasimportacion1.values_list('id',flat=True))
    # matriculasimportacion=matriculasimportacion2|matriculasimportacion1
    cont=0
    cursor = connections['db_moodle_virtual'].cursor()
    sientro = 0
    for matriculaimporta in matriculasimportacion:
        cont+=1
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
        aux=0
        materiaasignadas = matriculaimporta.matricula.materiaasignada_set.filter(id=785608,status=True,materiaasignadaretiro__isnull=True).order_by( 'materia__id').distinct()
        for materiaasignada in materiaasignadas:
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
                                """ % (str(matriculaimporta.matricula.inscripcion.persona.identificacion()),"%2020-01_"+str(materiaasignada.materia.asignatura.id)+"%")
            cursor.execute(sql_examenes2)
            datosexamenes2 = cursor.fetchall()
            if datosexamenes2:
                for nota2 in datosexamenes2:
                    id_actividad = nota2[0]
                    nombreactividadsakai=nota2[1]
                    nota = nota2[2]
                    # fullname = nota2[3]
                    # shortname = nota2[4]
                    # fecha_inicio = nota2[5]
                    # fecha_fin = nota2[6]
            # else:
                # sql_examenes1="""
                #    SELECT to_timestamp(att.timestart) AS inicio,TO_TIMESTAMP(att.timemodified) AS modifico
                #     FROM mooc_quiz_attempts att
                #     INNER JOIN mooc_quiz q ON att.quiz=q.id
                #     INNER JOIN mooc_course c ON c.id=q.course
                #     INNER JOIN mooc_user u ON u.id=att.userid
                #     WHERE att.state='inprogress' AND u.idnumber='%s'  and
                #     to_timestamp(att.timestart ) BETWEEN  '%s' AND '%s'
                #     AND c.shortname LIKE '%s'
                # """ % (str(matriculaimporta.matricula.inscripcion.persona.identificacion()),
                #        str(hoy2),
                #        str(hoy1),
                #        "%2020-01_"+str(materiaasignada.materia.asignatura.id)+"%")
                # w="""
                # SELECT to_timestamp(att.timestart) AS inicio,TO_TIMESTAMP(att.timemodified) AS modifico
                # FROM mooc_quiz_attempts att
                # INNER JOIN mooc_quiz q ON att.quiz=q.id
                # INNER JOIN mooc_course c ON c.id=q.course
                # INNER JOIN mooc_user u ON u.id=att.userid
                # WHERE att.state='inprogress' AND u.id=29043  and
                # to_timestamp(att.timestart ) BETWEEN  '2020-01-24 06:00:00' AND'2020-01-24 09:00:00'
                #
                # AND c.id=945
                # """
                # cursor.execute(w)
                # cursor.execute(sql_examenes1)
                # datosexamenes1 = cursor.fetchall()
                # if datosexamenes1:
                #     for nohayexamen in datosexamenes1:
                #         sientro=1
                #         ws.write(row_num, 0,str(matriculaimporta.matricula.inscripcion.mi_coordinacion()), font_style)
                #         ws.write(row_num, 1,str(matriculaimporta.matricula.inscripcion.carrera.nombre_completo()), font_style)
                #         ws.write(row_num, 2,str(matriculaimporta.matricula.inscripcion.persona.identificacion()), font_style)
                #         ws.write(row_num, 3,str(matriculaimporta.matricula.inscripcion.persona.nombre_completo_inverso()), font_style)
                #         ws.write(row_num, 4,str(materiaasignada.materia), font_style)
                #         ws.write(row_num, 5,str("Examen en progreso"), font_style)
                #         ws.write(row_num, 6,str(nohayexamen[0]), font_style)
                #         ws.write(row_num, 7,str(nohayexamen[1]), font_style)
                #         row_num = row_num + 1
            if nota:
                modeloevaluativo = materiaasignada.materia.modeloevaluativo
                detallemodeloevaluativo = modeloevaluativo.campo("EX")
                if EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada, detallemodeloevaluativo=detallemodeloevaluativo).exists():
                    evaluacion =  EvaluacionGenerica.objects.filter(materiaasignada=materiaasignada, detallemodeloevaluativo=detallemodeloevaluativo)[0]
                    if evaluacion.valor != nota:
                        observacion+=' SE MIGRO NOTA'
                        aux +=1
                        print("%s Migrada: %s - (%s)" % (cont, materiaasignada, nota))
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
                                if null_to_decimal(nota) != float(0):
                                    actualizar_nota_planificacion(materiaasignada.id, "EX", nota)
                                    auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                                                                    calificacion=nota)
                                    auditorianotas.save()
                    else:
                        aux+=1
                else:
                    aux+=1
                    observacion += ' SE MIGRO NOTA'
                    print("%s Migrada: %s - (%s)" % (cont, materiaasignada, nota))
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
            if aux>1:
                matriculaimporta.ejecuta = True
                matriculaimporta.save()
            # ws.write(row_num, 0,str(matriculaimporta.matricula.inscripcion.mi_coordinacion()), font_style)
            # ws.write(row_num, 1,str(matriculaimporta.matricula.inscripcion.carrera.nombre_completo()), font_style)
            # ws.write(row_num, 2,str(matriculaimporta.matricula.inscripcion.persona.identificacion()), font_style)
            # ws.write(row_num, 3,str(matriculaimporta.matricula.inscripcion.persona.nombre_completo_inverso()), font_style)
            # ws.write(row_num, 4,str(materiaasignada.materia), font_style)
            # ws.write(row_num, 5,str(observacion), font_style)
            # row_num = row_num + 1
    # if sientro>0:
    #     wb.save(filename)
    #     lista = []
    #     lista.append('jplacesc@unemi.edu.ec')
    #     lista.append('farevaloc@unemi.edu.ec')
    #     lista.append('kpalaciosz@unemi.edu.ec')
    #     lista.append('mchiflav@unemi.edu.ec')
    #     send_html_mail("Novedades importacion notas admision", "emails/novedades_importacion_nota_admison_examen.html",
    #                    {'sistema': "SGA", 'hoy': hoy}, lista, [],
    #                    [SITE_STORAGE + url2],
    #                    cuenta=CUENTAS_CORREOS[0][1])
except Exception as ex:
    print('error: %s' % ex)
