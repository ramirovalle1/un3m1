# -*- coding: latin-1 -*-
import random
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from xlwt import *
from decorators import last_access, secure_module
from settings import CLASES_HORARIO_ESTRICTO
from sga.commonviews import adduserdata
from sga.funciones import log, variable_valor
from sga.models import Carrera, Inscripcion, AsignaturaMalla, Asignatura, Malla, \
    PreMatriculaModulo, miinstitucion, CUENTAS_CORREOS
from sga.tasks import send_html_mail, conectar_cuenta


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'eliminarprematriculamodulo':
                try:
                    prematricula = PreMatriculaModulo.objects.filter(pk=int(request.POST['id']))[0]
                    log(u'Eliminacion PreMatricula Modulo: %s, usuario: %s' % (prematricula, persona), request, "del")
                    prematricula.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error Eliminar."})

            if action == 'correo':
                try:
                    mensaje = request.POST['motivo']
                    grupocorreo = request.POST['grupocorreo']
                    for prematriculamodulo in PreMatriculaModulo.objects.filter(periodo=periodo, tipo=2, grupo=grupocorreo).distinct():
                        correo = prematriculamodulo.inscripcion.persona.lista_emails_envio()
                        send_html_mail(u"Notificacion Pre-Matricula Modulo", "emails/notificacionprematricula.html", {'sistema': request.session['nombresistema'], 'prematricula': prematriculamodulo, 't': miinstitucion(), 'motivo': mensaje}, correo, [], cuenta=CUENTAS_CORREOS[5][1])
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error Envio."})

            if action == 'grupo':
                try:
                    codi = request.POST['id']
                    valor = request.POST['valor']
                    prematriculamodulo = PreMatriculaModulo.objects.get(pk=codi)
                    prematriculamodulo.grupo = valor
                    prematriculamodulo.save(request)
                    log(u'Modificación de Grupo: %s, al grupo %s ,usuario: %s' % (prematriculamodulo, valor, persona), request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error Envio."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Listado de estudiantes pre matriculados Modulos'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'materiasprematriculamodulo':
                try:
                    prematricula = PreMatriculaModulo.objects.filter(pk=int(request.GET['id']))
                    lista = []
                    for materiasprematricula in prematricula:
                            lista.append([materiasprematricula.asignaturas.nombre])
                    return JsonResponse({"result": "ok", "lista": lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

            if action == 'excel':
                try:

                    periodo1 = str(periodo.id)
                    __author__ = 'Justin & Amy'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False

                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')

                    ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=exp_xls_post_part_' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"CODIGO", 0),
                        (u"PERIODO", 6000),
                        (u"CARRERA", 6000),
                        (u"ALUMNO", 6000),
                        (u"EMAILPERSONAL", 6000),
                        (u"EMAILINSTITUCIONAL", 6000),
                        (u"MODULO", 6000),
                        (u"GRUPO", 6000),
                        (u"FACULTAD", 6000),
                        (u"INSCRIPCION", 6000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]

                    cursor = connection.cursor()
                    sql = "select pe.nombre as nperiodo, (p.apellido1 || ' ' || p.apellido2  || ' ' || p.nombres) as alumno,p.email as email, p.emailinst as  emailinst, a.nombre as modulo, c.nombre as carrera, pm.grupo,pm.id , co.nombre as facultad, i.id  " \
                    " from sga_prematriculamodulo pm, sga_inscripcion i, sga_persona p, sga_asignatura a, sga_carrera c, sga_periodo pe , sga_coordinacion_carrera cc, sga_coordinacion co " \
                    " where i.id=pm.inscripcion_id and p.id=i.persona_id and a.id=pm.asignaturas_id and c.id=i.carrera_id and pe.id=pm.periodo_id " \
                    " and pm.periodo_id='"+periodo1+"' and pm.tipo=2 and cc.carrera_id=c.id and cc.coordinacion_id=co.id " \
                    " order by co.nombre, c.nombre,a.nombre,alumno"
                    cursor.execute(sql)
                    results = cursor.fetchall()

                    row_num = 4
                    for r in results:
                        i = 0
                        campo1 = r[0]
                        campo2 = r[5]
                        campo3 = r[1]
                        campo4 = r[2]
                        campo5 = r[3]
                        campo6 = r[4]
                        campo7 = r[6]
                        campo8 = r[7]
                        campo9 = r[8]
                        campo10 = r[9]

                        ws.write(row_num, 0, campo8, font_style2)
                        ws.write(row_num, 1, campo1, font_style2)
                        ws.write(row_num, 2, campo2, font_style2)
                        ws.write(row_num, 3, campo3, font_style2)
                        ws.write(row_num, 4, campo4, font_style2)
                        ws.write(row_num, 5, campo5, font_style2)
                        ws.write(row_num, 6, campo6, font_style2)
                        ws.write(row_num, 7, campo7, font_style2)
                        ws.write(row_num, 8, campo9, font_style2)
                        ws.write(row_num, 9, campo10, font_style2)
                        # while i < len(r):
                        #     # ws.write(row_num, i, r[i], font_style)
                        #     # ws.col(i).width = columns[i][1]
                        row_num += 1

                    wb.save(response)
                    connection.close()
                    return response

                except Exception as ex:
                    pass

            if action == 'excelingles':
                try:

                    periodo1 = str(periodo.id)
                    __author__ = 'Justin & Amy'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False

                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')

                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=exp_xls_post_part_' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"PERIODO", 6000),
                        (u"CARRERA", 6000),
                        (u"ALUMNO", 6000),
                        (u"EMAILPERSONAL", 6000),
                        (u"EMAILINSTITUCIONAL", 6000),
                        (u"MODULO", 6000),
                        (u"NIVEL MALLA", 6000),
                        (u"NIVEL MATRICULA", 6000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]

                    cursor = connection.cursor()
                    sql = "select pe.nombre as nperiodo, (p.apellido1 || ' ' || p.apellido2  || ' ' || p.nombres) as alumno,p.email as email, p.emailinst as  emailinst, a.nombre as modulo, c.nombre as carrera, pm.grupo , nma.nombre as nivel_malla, " \
                          "COALESCE((select nma1.nombre from sga_matricula mat, sga_nivel niv, sga_nivelmalla nma1 where mat.inscripcion_id=i.id and niv.periodo_id=pe.id and mat.nivel_id=niv.id and mat.nivelmalla_id=nma1.id),'') as nivel_matricula " \
                          "from sga_prematriculamodulo pm, sga_inscripcion i, sga_persona p, sga_asignatura a, sga_carrera c, sga_periodo pe, sga_inscripcionnivel ini, sga_nivelmalla nma " \
                          "where i.id=pm.inscripcion_id and p.id=i.persona_id and a.id=pm.asignaturas_id and c.id=i.carrera_id and pe.id=pm.periodo_id " \
                          "and ini.inscripcion_id=i.id and nma.id=ini.nivel_id " \
                          "and pm.periodo_id='" + periodo1 + "' and pm.tipo=1 and a.id in (1818,1819) order by c.nombre,a.nombre,alumno"
                    cursor.execute(sql)
                    results = cursor.fetchall()

                    row_num = 4
                    for r in results:
                        i = 0
                        campo1 = r[0]
                        campo2 = r[5]
                        campo3 = r[1]
                        campo4 = r[2]
                        campo5 = r[3]
                        campo6 = r[4]
                        campo7 = r[7]
                        campo8 = r[8]

                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, campo7, font_style2)
                        ws.write(row_num, 7, campo8, font_style2)
                        # while i < len(r):
                        #     # ws.write(row_num, i, r[i], font_style)
                        #     # ws.col(i).width = columns[i][1]
                        row_num += 1

                    wb.save(response)
                    connection.close()
                    return response

                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            carreras = Carrera.objects.filter(malla__isnull=False, malla__asignaturamalla__materia__nivel__periodo=periodo, status=True).distinct()
            if 'id' in request.GET:
                data['carrera'] = carrera = Carrera.objects.get(pk=request.GET['id'], status=True)
                inscripcion = Inscripcion.objects.filter(carrera=carrera).distinct().order_by('-carrera')
                prematriculasingles = PreMatriculaModulo.objects.filter(periodo=periodo, inscripcion__carrera=carrera, tipo=1,asignaturas__id__in=[1818,1819]).order_by('inscripcion__persona__apellido1').distinct()
                # prematriculasingles = PreMatriculaModulo.objects.filter(periodo=periodo, inscripcion__carrera=carrera, tipo=1).order_by('inscripcion__persona__apellido1').distinct()
                prematriculascomputacion = PreMatriculaModulo.objects.filter(periodo=periodo, inscripcion__carrera=carrera, tipo=2).order_by('inscripcion__persona__apellido1').distinct()
                data['id'] = carrera.id
            else:
                data['carrera'] = carrera = carreras[0]
                prematriculasingles = PreMatriculaModulo.objects.filter(periodo=periodo, inscripcion__carrera=carrera, tipo=1,asignaturas__id__in=[1818,1819]).order_by('inscripcion__persona__apellido1').distinct()
                # prematriculasingles = PreMatriculaModulo.objects.filter(periodo=periodo, inscripcion__carrera=carrera, tipo=1).order_by('inscripcion__persona__apellido1').distinct()
                prematriculascomputacion = PreMatriculaModulo.objects.filter(periodo=periodo, inscripcion__carrera=carrera, tipo=2).order_by('inscripcion__persona__apellido1').distinct()
                inscripcion = Inscripcion.objects.all()
                data['id'] = carrera.id
            asignaturas = Asignatura.objects.filter(prematriculamodulo__inscripcion__carrera=carrera, status=True).distinct()
            data['carreras'] = carreras
            data['prematriculasmoduloingles'] = prematriculasingles
            data['prematriculasmodulocomputacion'] = prematriculascomputacion
            data['asignaturas'] = asignaturas
            data['clases_horario_estricto'] = CLASES_HORARIO_ESTRICTO
            data['mallas'] = mallas = Malla.objects.filter(carrera=carrera)
            if 'idm' in request:
                data['mallaselect'] = AsignaturaMalla.objects.filter(malla__id__in=[22, 32], status=True)
            else:
                data['mallaselect'] = AsignaturaMalla.objects.filter(malla__id__in=[22, 32], status=True)
            return render(request, "cons_prematriculamodulo/view.html", data)
