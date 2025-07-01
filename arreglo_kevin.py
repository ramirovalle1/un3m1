import base64
import os
import sys

import xlsxwriter
import xlwt
import json


from xlwt import *
from django.http import HttpResponse

from datetime import datetime, timedelta
from urllib.request import urlopen, Request



SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)
from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from settings import SITE_STORAGE, MEDIA_ROOT, MEDIA_URL, NOTA_ESTADO_EN_CURSO
from sga.models import Materia, Periodo, MateriaAsignada, \
    actualizar_nota_planificacion, AuditoriaNotas, GrupoTitulacionPostgrado, Notificacion, Persona
from postulaciondip.models import InscripcionInvitacion, PersonalApoyoMaestria
from django.db import transaction, connections
from django.contrib.auth.models import Group
from sga.funciones import null_to_decimal

def procesar_cierre_ingles_por_id_materia_asignada(id_materia_asignada):
    for materiaasignada in MateriaAsignada.objects.filter(pk__in =id_materia_asignada):
        materiaasignada.importa_nota = True
        materiaasignada.cerrado = True
        materiaasignada.fechacierre = datetime(2023, 8, 2, 0, 0, 0).date()
        materiaasignada.save()
        d = locals()
        exec(materiaasignada.materia.modeloevaluativo.logicamodelo, globals(), d)
        d['calculo_modelo_evaluativo'](materiaasignada)
        materiaasignada.cierre_materia_asignada()
        print(u"CIERRA -- %s" % (materiaasignada))

def proceso_cierre_ingles(periodo,id_nivel=1550):
    from django.http import HttpResponse
    response = HttpResponse(content_type="application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename=reporte_notas_ingles_segunda.xls'
    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
    style1 = easyxf(num_format_str='D-MMM-YY')
    font_style = XFStyle()
    font_style.font.bold = True
    font_style2 = XFStyle()
    font_style2.font.bold = False
    wb = xlwt.Workbook()
    ws = wb.add_sheet('Sheetname')
    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
    ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
    nombre = "reporte_notas_ingles_segunda" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
    filename = os.path.join(output_folder, nombre)
    columns = [(u"CEDULA", 6000),
               (u"APELLIDOS Y NOMBRES", 6000),
               (u"CARRERA", 6000),
               (u"URL", 6000),
               (u"MODULO", 6000),
               (u"NOTA BUCKINGHAM", 6000),
               (u"NOTA MATERIA", 6000),
               (u"ESTADO", 6000),
               (u"CURSO", 6000),
               (u"TIENE DEUDA", 6000),
               (u"VALOR PAGADO", 6000),
               (u"MATERIA ASIGNADA", 6000)
               ]
    row_num = 3
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num][0], font_style)
        ws.col(col_num).width = columns[col_num][1]
    row_num = 4
    cont=0
    materiasasignadas=MateriaAsignada.objects.filter(status=True,materia__inglesepunemi=True,cerrado=False,
                                                     matricula__status=True, retiramateria=False,materia__nivel__periodo=periodo,
                                                     materia__nivel_id=id_nivel,materia__status=True).order_by('matricula__inscripcion__carrera')
    # materiasasignadas = MateriaAsignada.objects.filter(pk=3288388)

    print(u"%s"%(materiasasignadas.values('id').count()))
    for materiaasignada in materiasasignadas:
        with transaction.atomic():
            try:
                idcursomoodle = materiaasignada.materia.idcursomoodle
                url = 'https://upei.buckcenter.edu.ec/usernamecoursetograde.php?username=%s&curso=%s' % (materiaasignada.matricula.inscripcion.persona.identificacion(),idcursomoodle)
                cont += 1
                ws.write(row_num, 0, materiaasignada.matricula.inscripcion.persona.identificacion())
                ws.write(row_num, 1, materiaasignada.matricula.inscripcion.persona.apellido1 + ' ' + materiaasignada.matricula.inscripcion.persona.apellido2 + ' ' + materiaasignada.matricula.inscripcion.persona.nombres)
                ws.write(row_num, 2, str(materiaasignada.matricula.inscripcion.carrera))
                ws.write(row_num, 3, str(url))
                req = Request(url)
                response = urlopen(req)
                result = json.loads(response.read().decode())
                idcurso = int(result['idcurso'])
                print(u"----- %s -----" % cont)
                print(u"PROCESANDO - %s" % materiaasignada)
                print(u"%s" % result)
                print(u"ID CURSO: %s" % idcurso)
                valores=0
                rubros = materiaasignada.rubro.filter(status=True, observacion='INGLÉS')
                for rubro in rubros:
                    valores= rubro.total_pagado()
                #         tiene_pagos=False
                # if tiene_pagos:
                if idcurso != idcursomoodle:
                    ws.write(row_num, 4, u"%s" % materiaasignada.materia)
                    ws.write(row_num, 5, u"NO COINCIDE CURSO")
                    ws.write(row_num, 6, u"NO COINCIDE CURSO")
                    ws.write(row_num, 7, u"NO COINCIDE CURSO")
                    ws.write(row_num, 8, u"NO COINCIDE CURSO")
                    ws.write(row_num, 9, u"NO COINCIDE CURSO")
                    ws.write(row_num, 10, u"NO COINCIDE CURSO")
                else:
                    nota = None
                    try:
                        nota = null_to_decimal(result['nota'], 0)
                    except:
                        if result['nota'] == '-' or result['nota'] == None :
                            nota = 0
                   # if nota>=70:
                    if (nota != materiaasignada.notafinal and type(nota) in [int, float]) or nota == 0:
                        campo = materiaasignada.campo('EX')
                        actualizar_nota_planificacion(materiaasignada.id, 'EX', nota)
                        auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False, calificacion=nota)
                        auditorianotas.save()
                        materiaasignada.importa_nota = True
                        materiaasignada.cerrado = True
                        materiaasignada.fechacierre = datetime.now().date()
                        materiaasignada.save()
                        d = locals()
                        exec(materiaasignada.materia.modeloevaluativo.logicamodelo, globals(), d)
                        d['calculo_modelo_evaluativo'](materiaasignada)
                        materiaasignada.cierre_materia_asignada()
                        print(u"IMPORTA Y CIERRA -- %s" % (materiaasignada))
                    ws.write(row_num, 4, u"%s" % materiaasignada.materia)
                    ws.write(row_num, 5, u"%s" % result['nota'])
                    ws.write(row_num, 6, nota)
                    ws.write(row_num, 7, u"APROBADO" if nota >= 70 else "REPROBADO")
                    ws.write(row_num, 8, u"COINCIDE CURSO" if idcurso == materiaasignada.materia.idcursomoodle else "NO COINCIDE CURSO")
                    ws.write(row_num, 9, u"%s"% rubros.count() if rubros else 0)
                    ws.write(row_num, 10, u"%s"% valores if rubros else 0)
                    ws.write(row_num, 11, u"%s"% materiaasignada.id)

                        # if not MateriaAsignadaRetiro.objects.filter(status=True, materiaasignada=materiaasignada).exists():
                        #     retiro = MateriaAsignadaRetiro(materiaasignada=materiaasignada,
                        #                                    motivo='RETIRO POR TÉRMINO DEl PROCESO DE INGLÉS 1S 2023 BUCKINGHAM',
                        #                                    valida=False,
                        #                                    fecha=datetime.now().date())
                        #     retiro.save()
                        # if not materiaasignada.retiramateria:
                        #     materiaasignada.retiramateria = True
                        #     materiaasignada.save()
                        # rubros=materiaasignada.rubro.filter(status=True,observacion='INGLÉS REGULAR 2023 AGOSTO 2023')
                        # for rubro in rubros:
                        #     if not rubro.pagos():
                        #         rubro.delete()
                        #         print(u"ELIMINADO -- %s" % (materiaasignada))
                    # ws.write(row_num, 3, u"%s" % materiaasignada.materia)
                    # ws.write(row_num, 4, u"%s" % result['nota'])
                    # ws.write(row_num, 5, nota)
                    # ws.write(row_num, 6, u"RETIRADO")
                    # ws.write(row_num, 7,u"COINCIDE CURSO" if idcurso == materiaasignada.materia.idcursomoodle else "NO COINCIDE CURSO")
            except Exception as ex:
                transaction.set_rollback(True)
                print('error: %s' % (ex))
                ws.write(row_num, 4, u"%s" % ex)
                ws.write(row_num, 5, u"%s" % ex)
                ws.write(row_num, 6, u"%s" % ex)
                ws.write(row_num, 7, u"%s" % ex)
                ws.write(row_num, 8, u"%s" % ex)
                ws.write(row_num, 9, u"%s" % ex)
                ws.write(row_num, 10, u"%s" % ex)
                pass
            row_num += 1
    wb.save(filename)
    print("FIN: ", filename)

def query_modulos_ingles_por_ver_y_vistos(id_periodo):
    sql = f"""
    SELECT 
 coordinacion.nombre AS facultad,
 carrera.nombre AS carrera,
 (
SELECT nivelmalla.nombre
FROM sga_inscripcionnivel inscripcionnivel
INNER JOIN sga_nivelmalla nivelmalla ON inscripcionnivel.nivel_id = nivelmalla.id
WHERE inscripcionnivel.inscripcion_id = inscripcion.id) AS nivel,
 (persona.apellido1||' '||persona.apellido2||' '||persona.nombres) AS estudiante,
 persona.cedula,
 persona.email,
 persona.emailinst, 
 (
SELECT COUNT(asignatura.id)
FROM sga_malla malla
INNER JOIN sga_asignaturamalla asignaturamalla ON asignaturamalla.malla_id = malla.id
INNER JOIN sga_asignatura asignatura ON asignaturamalla.asignatura_id = asignatura.id
WHERE malla.id = 353 AND asignatura."status") AS num_modulos_ingles_malla,
 
 (
SELECT COUNT(recordacademico.id)
FROM sga_recordacademico recordacademico
INNER JOIN sga_asignatura asignatura0 ON recordacademico.asignatura_id = asignatura0.id
WHERE recordacademico.aprobada = TRUE AND recordacademico."status" AND asignatura0."status" AND recordacademico.inscripcion_id=inscripcion.id AND asignatura0.nombre ILIKE '%INGL%' AND asignatura0.id IN (
SELECT asignatura8.id
FROM sga_malla malla8
INNER JOIN sga_asignaturamalla asignaturamalla8 ON asignaturamalla8.malla_id = malla8.id
INNER JOIN sga_asignatura asignatura8 ON asignaturamalla8.asignatura_id = asignatura8.id
WHERE malla8.id = 353 AND asignatura8."status")) AS num_modulos_aprobados,
 
 (ARRAY_TO_STRING(array(
SELECT asignatura0.nombre
FROM sga_recordacademico recordacademico
INNER JOIN sga_asignatura asignatura0 ON recordacademico.asignatura_id = asignatura0.id
WHERE recordacademico.aprobada = TRUE AND recordacademico."status" AND asignatura0."status" AND recordacademico.inscripcion_id=inscripcion.id AND asignatura0.nombre ILIKE '%INGL%' AND asignatura0.id IN (
SELECT asignatura8.id
FROM sga_malla malla8
INNER JOIN sga_asignaturamalla asignaturamalla8 ON asignaturamalla8.malla_id = malla8.id
INNER JOIN sga_asignatura asignatura8 ON asignaturamalla8.asignatura_id = asignatura8.id
WHERE malla8.id = 353 AND asignatura8."status")
ORDER BY asignatura0.nombre),', ')) AS nombres_modulos_aprobados, 
 
 
 (
SELECT COUNT(asignatura8.id)
FROM sga_malla malla8
INNER JOIN sga_asignaturamalla asignaturamalla8 ON asignaturamalla8.malla_id = malla8.id
INNER JOIN sga_asignatura asignatura8 ON asignaturamalla8.asignatura_id = asignatura8.id
WHERE malla8.id = 353 AND asignatura8."status" AND asignatura8.id NOT IN (
SELECT asignatura1.id
FROM sga_recordacademico recordacademico1
INNER JOIN sga_asignatura asignatura1 ON recordacademico1.asignatura_id = asignatura1.id
WHERE recordacademico1.aprobada = TRUE AND recordacademico1."status" AND recordacademico1.inscripcion_id=inscripcion.id AND asignatura1.nombre ILIKE '%INGL%')) AS num_modulos_por_aprobar,
 
 (ARRAY_TO_STRING(array(
SELECT asignatura8.nombre
FROM sga_malla malla8
INNER JOIN sga_asignaturamalla asignaturamalla8 ON asignaturamalla8.malla_id = malla8.id
INNER JOIN sga_asignatura asignatura8 ON asignaturamalla8.asignatura_id = asignatura8.id
WHERE malla8.id = 353 AND asignatura8."status" AND asignatura8.id NOT IN (
SELECT asignatura1.id
FROM sga_recordacademico recordacademico1
INNER JOIN sga_asignatura asignatura1 ON recordacademico1.asignatura_id = asignatura1.id
WHERE recordacademico1.aprobada = TRUE AND recordacademico1."status" AND recordacademico1.inscripcion_id=inscripcion.id AND asignatura1.nombre ILIKE '%INGL%')
ORDER BY asignatura8.nombre),', ')) AS nombres_modulos_por_aprobar 
FROM sga_matricula matricula
INNER JOIN sga_inscripcion inscripcion ON matricula.inscripcion_id = inscripcion.id
INNER JOIN sga_inscripcionmalla inscripcionmalla ON inscripcionmalla.inscripcion_id = inscripcion.id
INNER JOIN sga_persona persona ON inscripcion.persona_id = persona.id
INNER JOIN sga_carrera carrera ON inscripcion.carrera_id= carrera.id
INNER JOIN sga_nivel nivel ON matricula.nivel_id = nivel.id
INNER JOIN sga_coordinacion_carrera coorcar ON coorcar.carrera_id = carrera.id
INNER JOIN sga_coordinacion coordinacion ON coorcar.coordinacion_id = coordinacion.id
WHERE nivel.periodo_id = {id_periodo} AND coordinacion.id IN (1,2,3,4,5)  and matricula."status" AND inscripcion."status"
 AND matricula.retiradomatricula = FALSE AND carrera."status"
ORDER BY coordinacion.nombre, carrera.nombre
    """
    return sql

def traer_datos_query(sql):
    try:
        cursor = connections['default'].cursor()
        cursor.execute(sql)
        rows_effected = cursor.rowcount
        listado = cursor.fetchall()
        campos = [desc[0] for desc in cursor.description]
        directory = os.path.join(MEDIA_ROOT, 'reportes', 'gestion')
        try:
            os.stat(directory)
        except:
            os.mkdir(directory)
        name_document = 'reporte'
        nombre_archivo = name_document + "_1.xlsx"
        directory = os.path.join(MEDIA_ROOT, 'reportes', 'gestion', nombre_archivo)

        _author_ = 'Unemi'
        workbook = xlsxwriter.Workbook(directory, {'constant_memory': True})
        ws = workbook.add_worksheet('resultados')
        fuentecabecera = workbook.add_format({
            'align': 'center',
            'bg_color': 'silver',
            'border': 1,
            'bold': 1
        })

        formatoceldacenter = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'align': 'center'})

        row_num, numcolum = 0, 0

        for col_num in campos:
            ws.write(row_num, numcolum, col_num, fuentecabecera)
            ws.set_column(row_num, numcolum, 40)
            numcolum += 1
        row_num += 1
        for lis in listado:
            colum_num = 0
            for l in lis:
                ws.write(row_num, colum_num, l, formatoceldacenter)
                ws.set_column(row_num, numcolum, 40)
                colum_num += 1
            row_num += 1

        workbook.close()
        response = HttpResponse(directory,
                                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=%s' % name_document
        #
        url_file = "{}reportes/gestion/{}".format(MEDIA_URL, nombre_archivo)
        print(url_file)

    except Exception as ex:
        print(ex)

def borrar_materias_nivel_ingles():
    print("inicio.....")
    eMaterias= Materia.objects.filter(nivel_id=1508)
    print(f"total materias a borrar {eMaterias.count()}")
    for materia in eMaterias:
        print(f"borrando.. {materia}")
        # materia.delete()
        print("borrado")
    print("fin")

def eliminar_materiasasignadas():
    materiasasignadas = MateriaAsignada.objects.filter(status=True, materia__inglesepunemi=True,
                                                       materia__id__in=[67490, 67491, 67494,67309,67410,67446]).order_by(
        'matricula__inscripcion__carrera')
    print(u"%s" % (materiasasignadas.values('id').count()))
    for materiaasignada1 in materiasasignadas:
        if materiaasignada1.estado_id  == 1:
            maa2= MateriaAsignada.objects.filter(materia__nivel_id=1508,matricula=materiaasignada1.matricula ,materia__asignatura=materiaasignada1.materia.asignatura)
            if maa2.values('id').exists():
                maa2=maa2.first()
                print(u"ELIMINADO -- %s" % (maa2))
                rubros=maa2.rubro.filter(status=True,observacion__icontains='INGLÉS ABRIL - AGOSTO 2023')
                for rubro in rubros:
                    if not rubro.pagos():
                        # rubro.delete()
                        print(u"ELIMINADO -- %s" % (rubro))
                # maa2.delete()

# eliminar_materiasasignadas()
def proceso_cierre_ingles_por_materia_de_la_persona_quemado(periodo,id_nivel=1542, id_materia_asignada= 0,id_curso_nuevo= 0):
    from django.http import HttpResponse
    response = HttpResponse(content_type="application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename=reporte_notas_ingles.xls'
    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
    style1 = easyxf(num_format_str='D-MMM-YY')
    font_style = XFStyle()
    font_style.font.bold = True
    font_style2 = XFStyle()
    font_style2.font.bold = False
    wb = xlwt.Workbook()
    ws = wb.add_sheet('Sheetname')
    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
    ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
    nombre = "Lista" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
    filename = os.path.join(output_folder, nombre)
    columns = [(u"CEDULA", 6000),
               (u"APELLIDOS Y NOMBRES", 6000),
               (u"CARRERA", 6000),
               (u"URL", 6000),
               (u"MODULO", 6000),
               (u"NOTA BUCKINGHAM", 6000),
               (u"NOTA MATERIA", 6000),
               (u"ESTADO", 6000),
               (u"CURSO", 6000),
               (u"TIENE DEUDA", 6000),
               (u"VALOR", 6000)
               ]
    row_num = 3
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num][0], font_style)
        ws.col(col_num).width = columns[col_num][1]
    row_num = 4
    cont=0
    materiasasignadas=MateriaAsignada.objects.filter(status=True,materia__inglesepunemi=True, pk = id_materia_asignada,
                                                     matricula__status=True, retiramateria=False,materia__nivel__periodo=periodo,
                                                     materia__nivel_id=id_nivel,materia__status=True).order_by('matricula__inscripcion__carrera')
    print(u"%s"%(materiasasignadas.values('id').count()))
    for materiaasignada in materiasasignadas:
        with transaction.atomic():
            try:
                idcursomoodle = id_curso_nuevo
                url = 'https://upei.buckcenter.edu.ec/usernamecoursetograde.php?username=%s&curso=%s' % (materiaasignada.matricula.inscripcion.persona.identificacion(),id_curso_nuevo)
                cont += 1
                ws.write(row_num, 0, materiaasignada.matricula.inscripcion.persona.identificacion())
                ws.write(row_num, 1, materiaasignada.matricula.inscripcion.persona.apellido1 + ' ' + materiaasignada.matricula.inscripcion.persona.apellido2 + ' ' + materiaasignada.matricula.inscripcion.persona.nombres)
                ws.write(row_num, 2, str(materiaasignada.matricula.inscripcion.carrera))
                ws.write(row_num, 3, str(url))
                req = Request(url)
                response = urlopen(req)
                result = json.loads(response.read().decode())
                idcurso = int(result['idcurso'])
                print(u"----- %s -----" % cont)
                print(u"PROCESANDO - %s" % materiaasignada)
                print(u"%s" % result)
                print(u"ID CURSO: %s" % idcurso)
                valores=0
                rubros = materiaasignada.rubro.filter(status=True, observacion='INGLÉS ABRIL - AGOSTO 2023')
                for rubro in rubros:
                    valores= rubro.total_pagado()
                #         tiene_pagos=False
                # if tiene_pagos:
                if idcurso != idcursomoodle:
                    ws.write(row_num, 4, u"%s" % materiaasignada.materia)
                    ws.write(row_num, 5, u"NO COINCIDE CURSO")
                    ws.write(row_num, 6, u"NO COINCIDE CURSO")
                    ws.write(row_num, 7, u"NO COINCIDE CURSO")
                    ws.write(row_num, 8, u"NO COINCIDE CURSO")
                    ws.write(row_num, 9, u"NO COINCIDE CURSO")
                    ws.write(row_num, 10, u"NO COINCIDE CURSO")
                else:
                    nota = None
                    try:
                        nota = null_to_decimal(result['nota'], 0)
                    except:
                        if result['nota'] == '-'or result['nota'] == None :
                            nota = 0
                    if nota:
                        if (nota != materiaasignada.notafinal and type(nota) in [int,float]) or nota == 0 :
                            campo = materiaasignada.campo('EX')
                            actualizar_nota_planificacion(materiaasignada.id, 'EX', nota)
                            auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False, calificacion=nota)
                            auditorianotas.save()
                            materiaasignada.importa_nota = True
                            materiaasignada.cerrado = True
                            materiaasignada.fechacierre = datetime.now().date()
                            materiaasignada.save()
                            d = locals()
                            exec(materiaasignada.materia.modeloevaluativo.logicamodelo, globals(), d)
                            d['calculo_modelo_evaluativo'](materiaasignada)
                            materiaasignada.cierre_materia_asignada()
                            print(u"IMPORTA Y CIERRA -- %s" % (materiaasignada))
                    ws.write(row_num, 4, u"%s" % materiaasignada.materia)
                    ws.write(row_num, 5, u"%s" % result['nota'])
                    ws.write(row_num, 6, nota)
                    ws.write(row_num, 7, u"APROBADO" if nota >= 70 else "REPROBADO")
                    ws.write(row_num, 8, u"COINCIDE CURSO" if idcurso == idcursomoodle else "NO COINCIDE CURSO")
                    ws.write(row_num, 9, u"TIENE RUBROS %s"% rubros.count() if rubros else 0)
                    ws.write(row_num, 10, u"VALORES %s"% valores if rubros else 0)

            except Exception as ex:
                transaction.set_rollback(True)
                print('error: %s' % (ex))
                ws.write(row_num, 4, u"%s" % ex)
                ws.write(row_num, 5, u"%s" % ex)
                ws.write(row_num, 6, u"%s" % ex)
                ws.write(row_num, 7, u"%s" % ex)
                ws.write(row_num, 8, u"%s" % ex)
                ws.write(row_num, 9, u"%s" % ex)
                ws.write(row_num, 10, u"%s" % ex)
                pass
            row_num += 1
    wb.save(filename)
    print("FIN: ", filename)

# periodo=Periodo.objects.get(id=177)
# id_materia_asignada = 3243926
# id_curso = 465
# id_nivel=1501
# proceso_cierre_ingles_por_materia_de_la_persona_quemado(periodo,id_nivel,id_materia_asignada,558)

def proceso_cierre_ingles_por_id_materia_asignada(periodo,id_nivel,ids_materias_asignadas):
    from django.http import HttpResponse
    response = HttpResponse(content_type="application/ms-excel")
    response['Content-Disposition'] = 'attachment; filename=reporte_notas_ingles.xls'
    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
    style1 = easyxf(num_format_str='D-MMM-YY')
    font_style = XFStyle()
    font_style.font.bold = True
    font_style2 = XFStyle()
    font_style2.font.bold = False
    wb = xlwt.Workbook()
    ws = wb.add_sheet('Sheetname')
    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
    ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
    nombre = "Lista" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
    filename = os.path.join(output_folder, nombre)
    columns = [(u"CEDULA", 6000),
               (u"APELLIDOS Y NOMBRES", 6000),
               (u"CARRERA", 6000),
               (u"URL", 6000),
               (u"MODULO", 6000),
               (u"NOTA BUCKINGHAM", 6000),
               (u"NOTA MATERIA", 6000),
               (u"ESTADO", 6000),
               (u"CURSO", 6000),
               (u"TIENE DEUDA", 6000),
               (u"VALOR", 6000)
               ]
    row_num = 3
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num][0], font_style)
        ws.col(col_num).width = columns[col_num][1]
    row_num = 4
    cont=0
    materiasasignadas=MateriaAsignada.objects.filter(status=True,materia__inglesepunemi=True, id__in=ids_materias_asignadas,
                                                     matricula__status=True, retiramateria=False,materia__nivel__periodo=periodo,
                                                     materia__nivel_id=id_nivel,materia__status=True).order_by('matricula__inscripcion__carrera')
    print(u"%s"%(materiasasignadas.values('id').count()))
    for materiaasignada in materiasasignadas:
        with transaction.atomic():
            try:
                idcursomoodle = materiaasignada.materia.idcursomoodle
                url = 'https://upei.buckcenter.edu.ec/usernamecoursetograde.php?username=%s&curso=%s' % (materiaasignada.matricula.inscripcion.persona.identificacion(),idcursomoodle)
                cont += 1
                ws.write(row_num, 0, materiaasignada.matricula.inscripcion.persona.identificacion())
                ws.write(row_num, 1, materiaasignada.matricula.inscripcion.persona.apellido1 + ' ' + materiaasignada.matricula.inscripcion.persona.apellido2 + ' ' + materiaasignada.matricula.inscripcion.persona.nombres)
                ws.write(row_num, 2, str(materiaasignada.matricula.inscripcion.carrera))
                ws.write(row_num, 3, str(url))
                req = Request(url)
                response = urlopen(req)
                result = json.loads(response.read().decode())
                idcurso = int(result['idcurso'])
                print(u"----- %s -----" % cont)
                print(u"PROCESANDO - %s" % materiaasignada)
                print(u"%s" % result)
                print(u"ID CURSO: %s" % idcurso)
                valores=0
                rubros = materiaasignada.rubro.filter(status=True, observacion='INGLÉS ABRIL - AGOSTO 2023')
                for rubro in rubros:
                    valores= rubro.total_pagado()
                #         tiene_pagos=False
                # if tiene_pagos:
                if idcurso != idcursomoodle:
                    ws.write(row_num, 4, u"%s" % materiaasignada.materia)
                    ws.write(row_num, 5, u"NO COINCIDE CURSO")
                    ws.write(row_num, 6, u"NO COINCIDE CURSO")
                    ws.write(row_num, 7, u"NO COINCIDE CURSO")
                    ws.write(row_num, 8, u"NO COINCIDE CURSO")
                    ws.write(row_num, 9, u"NO COINCIDE CURSO")
                    ws.write(row_num, 10, u"NO COINCIDE CURSO")
                else:
                    nota = None
                    try:
                        nota = null_to_decimal(result['nota'], 0)
                    except:
                        if result['nota'] == '-'or result['nota'] == None :
                            nota = 0
                    if nota:
                        if (nota != materiaasignada.notafinal and type(nota) in [int,float]) or nota == 0 :
                            campo = materiaasignada.campo('EX')
                            actualizar_nota_planificacion(materiaasignada.id, 'EX', nota)
                            auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False, calificacion=nota)
                            auditorianotas.save()
                            materiaasignada.importa_nota = True
                            materiaasignada.cerrado = True
                            materiaasignada.fechacierre = datetime.now().date()
                            materiaasignada.save()
                            d = locals()
                            exec(materiaasignada.materia.modeloevaluativo.logicamodelo, globals(), d)
                            d['calculo_modelo_evaluativo'](materiaasignada)
                            materiaasignada.cierre_materia_asignada()
                            print(u"IMPORTA Y CIERRA -- %s" % (materiaasignada))
                    ws.write(row_num, 4, u"%s" % materiaasignada.materia)
                    ws.write(row_num, 5, u"%s" % result['nota'])
                    ws.write(row_num, 6, nota)
                    ws.write(row_num, 7, u"APROBADO" if nota >= 70 else "REPROBADO")
                    ws.write(row_num, 8, u"COINCIDE CURSO" if idcurso == materiaasignada.materia.idcursomoodle else "NO COINCIDE CURSO")
                    ws.write(row_num, 9, u"TIENE RUBROS %s"% rubros.count() if rubros else 0)
                    ws.write(row_num, 10, u"VALORES %s"% valores if rubros else 0)

                        # if not MateriaAsignadaRetiro.objects.filter(status=True, materiaasignada=materiaasignada).exists():
                        #     retiro = MateriaAsignadaRetiro(materiaasignada=materiaasignada,
                        #                                    motivo='RETIRO POR TÉRMINO DEl PROCESO DE INGLÉS 1S 2023 BUCKINGHAM',
                        #                                    valida=False,
                        #                                    fecha=datetime.now().date())
                        #     retiro.save()
                        # if not materiaasignada.retiramateria:
                        #     materiaasignada.retiramateria = True
                        #     materiaasignada.save()
                        # rubros=materiaasignada.rubro.filter(status=True,observacion='INGLÉS REGULAR 2023 AGOSTO 2023')
                        # for rubro in rubros:
                        #     if not rubro.pagos():
                        #         rubro.delete()
                        #         print(u"ELIMINADO -- %s" % (materiaasignada))
                    # ws.write(row_num, 3, u"%s" % materiaasignada.materia)
                    # ws.write(row_num, 4, u"%s" % result['nota'])
                    # ws.write(row_num, 5, nota)
                    # ws.write(row_num, 6, u"RETIRADO")
                    # ws.write(row_num, 7,u"COINCIDE CURSO" if idcurso == materiaasignada.materia.idcursomoodle else "NO COINCIDE CURSO")
            except Exception as ex:
                transaction.set_rollback(True)
                print('error: %s' % (ex))
                ws.write(row_num, 4, u"%s" % ex)
                ws.write(row_num, 5, u"%s" % ex)
                ws.write(row_num, 6, u"%s" % ex)
                ws.write(row_num, 7, u"%s" % ex)
                ws.write(row_num, 8, u"%s" % ex)
                ws.write(row_num, 9, u"%s" % ex)
                ws.write(row_num, 10, u"%s" % ex)
                pass
            row_num += 1
    wb.save(filename)
    print("FIN: ", filename)

# ids_materias_asignadas=[3194758,]
# proceso_cierre_ingles_por_id_materia_asignada(periodo,1501,ids_materias_asignadas)

# periodo=Periodo.objects.get(id=224)
# proceso_cierre_ingles(periodo,id_nivel = 1550)
# id_nivel = 1501
# fecha_asignacion = '2023-06-24'

def eliminar_estudiantes_que_se_matricularon_en_la_fase_1_en_el_modulo_ingles_I(periodo,id_nivel,fecha_asignacion):
    with transaction.atomic():
        eMateriaAsignada= MateriaAsignada.objects.filter(status=True, materia__inglesepunemi=True,
                                       matricula__status=True,
                                       retiramateria=False, materia__nivel__periodo=periodo,
                                       materia__asignatura_id=783,
                                       materia__nivel_id=id_nivel, materia__status=True,
                                       fechaasignacion__gte=fecha_asignacion).order_by(
            'matricula__inscripcion__carrera')
        print(f"Total a borrar {eMateriaAsignada.count()}")
        print(f"borrando")
        # eMateriaAsignada.delete()
        print(f"fin")
def eliminar_del_nivel_1501_estudiantes_matriculados_de_la_fase_2_por_fecha(periodo,id_nivel,fecha_asignacion):
    cedulas = []
    with transaction.atomic():
        i = 0

        materiasasignadas = MateriaAsignada.objects.filter(status=True, materia__inglesepunemi=True,matricula__status=True, retiramateria=False,
                                                           materia__nivel__periodo=periodo, materia__nivel_id=id_nivel,
                                                           materia__status=True, fechaasignacion__gte=fecha_asignacion).order_by('matricula__inscripcion__carrera').exclude(materia__asignatura=783)
        print(f" total inscritos fase 1 : {materiasasignadas.values('id').count()}")
        total = materiasasignadas.values('id').count()
        for materiaasignadafase1 in materiasasignadas:
            i+=1
            print(f"{total} / {i}")
            eMateriaAsignadaExisteFase2 = MateriaAsignada.objects.filter(status=True,matricula=materiaasignadafase1.matricula,
                                                                         materia__asignatura=materiaasignadafase1.materia.asignatura,
                                                                         materia__inglesepunemi=True,matricula__status=True,
                                                                         retiramateria=False,materia__nivel__periodo=periodo,
                                                                         materia__nivel_id=1508, materia__status=True).order_by('matricula__inscripcion__carrera')
            rubros = materiaasignadafase1.rubro.filter(status=True,observacion__icontains='INGLÉS ABRIL - AGOSTO 2023').exists()
            print(f"{materiaasignadafase1.materia.nivel_id} -{materiaasignadafase1.matricula.inscripcion.persona.cedula} -{materiaasignadafase1.materia.asignatura} - {materiaasignadafase1.materia.paralelo} : tiene materia fase2: {eMateriaAsignadaExisteFase2.exists()}- cantidad fase 2::{eMateriaAsignadaExisteFase2.count()} - tiene_rubro fase 1: {rubros}")
            if eMateriaAsignadaExisteFase2.exists():
                print(f"Eliminando materia de fase 1 {materiaasignadafase1}")
                rubros = materiaasignadafase1.rubro.filter(status=True, observacion__icontains='INGLÉS ABRIL - AGOSTO 2023')
                for rubro in rubros:
                    if not rubro.pagos():
                        # rubro.delete()
                        print(u" RUBRO ELIMINADO -- %s" % (rubro))
                    else:
                        print(f"Tiene cancelado rubro fase 1: {materiaasignadafase1.matricula.inscripcion.persona.cedula}")
                        cedulas.append(materiaasignadafase1.matricula.inscripcion.persona.cedula)
                # materiaasignadafase1.delete()

                print("eliminadade la fase 1 ya tiene en fase 2 materia")
            else:
                print(f"matriculando en fase 2 no tiene en fase 2 pero en fase 1 se matriculo")
                eMaterias = Materia.objects.filter(status=True, asignatura=materiaasignadafase1.materia.asignatura, nivel_id=1508)
                print("buscando curso disponible...")
                for materia in eMaterias:
                    if materia.capacidad_disponible() > 0:
                        print("curso disponible encontrado..")
                        print("Asignando materiaasignada dl nivel de la fase 2..")
                        materiaasignada = MateriaAsignada(matricula=materiaasignadafase1.matricula,
                                                          materia=materia,
                                                          notafinal=0,
                                                          asistenciafinal=100,
                                                          cerrado=False,
                                                          matriculas=materiaasignadafase1.matriculas,
                                                          observaciones='',
                                                          estado_id=NOTA_ESTADO_EN_CURSO
                                                          )
                        materiaasignada.save()
                        materiaasignada.asistencias()
                        materiaasignada.evaluacion()




def notificar_analistas_posgrado(eUsers,eInscripcionInvitacion):
    print("start process notification")
    ecarrera = eInscripcionInvitacion.get_personal_a_contratar().actaparalelo.convocatoria.carrera
    eperiodo = eInscripcionInvitacion.get_personal_a_contratar().actaparalelo.convocatoria.periodo
    ePersonalApoyoMaestrias = PersonalApoyoMaestria.objects.filter(status=True, carrera=ecarrera, periodo=eperiodo)
    titulonotificacion = f"Plazo para subir requisitos por vencer: {eInscripcionInvitacion.get_personal_a_contratar()} - {eInscripcionInvitacion.fecharevisionrequisitos}"
    cuerponotificacion = f"La fecha limité para subir los requisitos esta por terminar, le quedan 2 días para subir todos los documentos."

    if ePersonalApoyoMaestrias:
        for ePersona in ePersonalApoyoMaestrias:
            notificacion = Notificacion(
                titulo=titulonotificacion,
                cuerpo=cuerponotificacion,
                destinatario=ePersona.personalapoyo.persona,
                url=f"https://sga.unemi.edu.ec/adm_postulacion?action=revision_requisitos_personal_a_contratar&id={eInscripcionInvitacion.get_personal_a_contratar().pk}",
                content_type=None,
                object_id=None,
                prioridad=1,
                app_label='SGA',
                fecha_hora_visible=datetime.now() + timedelta(days=3))
            notificacion.save()

    else:
        for user in eUsers:
            ePersona = Persona.objects.filter(status=True, usuario=user).first()
            notificacion = Notificacion(
                titulo=titulonotificacion,
                cuerpo=cuerponotificacion,
                destinatario=ePersona,
                url=f"https://sga.unemi.edu.ec/adm_postulacion?action=revision_requisitos_personal_a_contratar&id={eInscripcionInvitacion.get_personal_a_contratar().pk}",
                content_type=None,
                object_id=None,
                prioridad=1,
                app_label='SGA',
                fecha_hora_visible=datetime.now() + timedelta(days=3))
            notificacion.save()
    print("End proccess notification")

def notificar_persona_a_contratar(eInscripcionInvitacion):
    print("start process notification")
    titulonotificacion = f"Plazo para subir requisitos por vencer {eInscripcionInvitacion.fecharevisionrequisitos}"
    cuerponotificacion = f"La fecha limité para subir los requisitos esta por terminar, le quedan 2 días para subir todos los documentos."
    ePersona = eInscripcionInvitacion.inscripcion.postulante.persona
    if ePersona:
        notificacion = Notificacion(
            titulo=titulonotificacion,
            cuerpo=cuerponotificacion,
            destinatario=ePersona,
            url=f"https://seleccionposgrado.unemi.edu.ec/loginpostulacion",
            content_type=None,
            object_id=None,
            prioridad=1,
            app_label='SGA',
            fecha_hora_visible=datetime.now() + timedelta(days=3))
        notificacion.save()
    print("End proccess notification")


def notificar_plazo_a_vencer_requisitos():
    # Obtener la fecha actual
    fecha_actual = datetime.now().date()

    # Obtener la fecha actual + 2 días
    fecha_limite = fecha_actual + timedelta(days=2)
    eInscripcionInvitacion = InscripcionInvitacion.objects.filter(status=True,fecharevisionrequisitos=fecha_limite)
    eGrupo = Group.objects.get(pk=422)
    eUsers = eGrupo.user_set.all()

    # Realizar acciones con las inscripciones caducas si es necesario
    for inscripcion in eInscripcionInvitacion:
        notificar_analistas_posgrado(eUsers,inscripcion)
        notificar_persona_a_contratar(inscripcion)

# notificar_plazo_a_vencer_requisitos()z

def generard_qr_jefa():
    print("inicio")
    from sga.funciones import null_to_decimal, puede_realizar_accion, log, generar_nombre, MiPaginador, variable_valor, \
        daterange, notificacion, \
        remover_caracteres_tildes_unicode, remover_caracteres_especiales_unicode, puede_realizar_accion_afirmativo
    IS_DEBUG = variable_valor('IS_DEBUG')
    import random
    import os
    from datetime import datetime

    import pyqrcode

    from sga.models import  MESES_CHOICES
    from postulaciondip.models import InscripcionInvitacion,DocumentoInvitacion,ClasificacionDocumentoInvitacion,SecuenciaDocumentoInvitacion
    from sga.funcionesxhtml2pdf import conviert_html_to_pdf_save_file_model

    data = {}



    dominio_sistema = 'https://sga.unemi.edu.ec'
    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema
    temp = lambda x: remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(x.__str__()))
    eInscripcionInvitacion = InscripcionInvitacion.objects.get(pk=732)
    eInscripcionInvitacion.fechaaceptacion =datetime(2024, 4, 23, 11, 0)
    eInscripcionInvitacion.save()
    fecha = eInscripcionInvitacion.fechaaceptacion
    data['eInscripcionInvitacion'] = eInscripcionInvitacion
    data['fecha'] = str(fecha.day) + " de " + str(MESES_CHOICES[fecha.month - 1][1]).lower() + " del " + str(fecha.year)
    #

    qrname = 'qr_certificado_cartaaceptacion_' + str(eInscripcionInvitacion.id)
    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'cartaaceptacionposgrado', 'qr'))
    directory = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'cartaaceptacionposgrado'))
    os.makedirs(f'{directory}/qr/', exist_ok=True)
    try:
        os.stat(directory)
    except:
        os.mkdir(directory)
    nombrepersona = temp(eInscripcionInvitacion.inscripcion.postulante.persona.__str__()).replace(' ', '_')
    htmlname = 'cartaaceptacion_{}_{}'.format(nombrepersona, random.randint(1, 100000).__str__())
    urlname = "/media/qrcode/cartaaceptacionposgrado/%s" % htmlname
    # rutahtml = SITE_STORAGE + urlname
    data['url_qr'] = url_qr = f'{SITE_STORAGE}/media/qrcode/cartaaceptacionposgrado/qr/{htmlname}.png'
    url = pyqrcode.create(f'FIRMADO POR: {nombrepersona}\nfirmado desde https://sga.unemi.edu.ec\n FECHA: {eInscripcionInvitacion.fechaaceptacion}\n{dominio_sistema}/media/qrcode/cartaaceptacionposgrado/{htmlname}.pdf\n2.10.1')
    imageqr = url.png(f'{directory}/qr/{htmlname}.png', 16, '#000000')
    data['qrname'] = 'qr' + qrname
    pdf_file, response = conviert_html_to_pdf_save_file_model(
        'adm_postulacion/docs/cartaaceptacioninvitacion.html',
        {'pagesize': 'A4', 'data': data}
    )

    CARTA_ACEPTACION_ID = 2
    EDocumentoInvitacion = DocumentoInvitacion.objects.filter(status=True, inscripcioninvitacion=eInscripcionInvitacion,
                                                              clasificacion_id=CARTA_ACEPTACION_ID)
    filename = generar_nombre(f'carta_aceptacion_{eInscripcionInvitacion.id}_', 'aceptacion') + ".pdf"
    if EDocumentoInvitacion.exists():
        instance = EDocumentoInvitacion.first()
        instance.archivo.save(filename, pdf_file, save=True)
        instance.save()
    else:
        abreviaturanombre = ''
        documento = ClasificacionDocumentoInvitacion.objects.get(pk=CARTA_ACEPTACION_ID)
        secuencia = SecuenciaDocumentoInvitacion(tipo=documento)
        secuencia.save()
        codigo = secuencia.set_secuencia()
        for c in eInscripcionInvitacion.inscripcion.postulante.persona.nombre_completo().split(' '):
            abreviaturanombre += c[0] if c.__len__() else ''
        codigodocumento = "ITI-POS-%s-%s-%s" % (abreviaturanombre, "%03d" % codigo, secuencia.anioejercicio)

        instance = DocumentoInvitacion(
            codigo=codigodocumento,
            clasificacion_id=CARTA_ACEPTACION_ID,
            secuenciadocumento=secuencia,
            inscripcioninvitacion=eInscripcionInvitacion,
            archivo=filename
        )
        instance.archivo.save(filename, pdf_file)
        instance.save()
    print("DocumentoInvitacion pk: ")
    print(instance.pk)
    print("eInscripcionInvitacion pk: ")
    print(eInscripcionInvitacion.pk)
    print("file pk: ")
    print(instance.archivo)
    print("fin")
# generard_qr_jefa()
