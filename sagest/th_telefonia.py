# -*- coding: UTF-8 -*-
import random
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from xlwt import *
from xlwt import easyxf
from decorators import secure_module
from sagest.models import DistributivoPersona
from settings import EMAIL_DOMAIN, PUESTO_ACTIVO_ID
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log
from sga.models import Persona


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'estension':
            try:
                personaid = Persona.objects.get(pk=request.POST['personaid'])
                numextencion = int(request.POST['numextencion'])
                personaid.telefonoextension = numextencion
                personaid.save(request)
                log(u'Adicionó Estación: %s' % personaid, request, "add")
                return JsonResponse({'result': 'ok', 'valor': numextencion})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'descargar':
                try:
                    __author__ = 'Unemi'
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
                        'Content-Disposition'] = 'attachment; filename=empleados_' + random.randint(
                        1, 10000).__str__() + '.xls'
                    columns = [
                        (u"DEPARTAMENTO", 6000),
                        (u"CEDULA", 6000),
                        (u"APELLIDO 1", 6000),
                        (u"APELLIDO 2", 6000),
                        (u"NOMBRE", 6000),
                        (u"FECHA NACIMIENTO", 6000),
                        (u"EMAIL INSTITUCIONAL", 6000),
                        (u"REGIMEN LABORAL", 12000),
                        (u"DENOMINACIÓN PUESTO", 12000),
                        (u"NIVEL OCUPACIONAL", 6000),
                        (u"MODALIDAD LABORAL", 6000),
                        (u"USUARIO", 6000),
                        (u"SEXO", 6000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    cursor = connection.cursor()
                    # lista_json = []
                    # data = {}
                    sql = "select dep.nombre , p.cedula, p.apellido1, p.apellido2, p.nombres, p.nacimiento, p.emailinst , r.descripcion, de.descripcion, nio.descripcion, mod.descripcion, usua.username, (case p.sexo_id when 1 then 'FEMENINO' else 'MASCULINO' end) as sexo " \
                          " from sga_persona p, auth_user usua, sagest_distributivopersona d, sagest_nivelocupacional nio, sagest_modalidadlaboral mod, sagest_regimenlaboral r, sagest_denominacionpuesto de, sagest_departamento dep " \
                          " where p.id=d.persona_id and d.status=true and d.estadopuesto_id=1 and r.id=d.regimenlaboral_id " \
                          " and usua.id=p.usuario_id and d.nivelocupacional_id=nio.id and d.modalidadlaboral_id=mod.id and de.id=d.denominacionpuesto_id and dep.id=d.unidadorganica_id order by dep.nombre, r.id "
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    row_num = 4
                    for r in results:
                        i = 0
                        campo1 = r[0]
                        campo2 = r[1]
                        campo3 = r[2]
                        campo4 = r[3]
                        campo5 = r[4]
                        campo6 = r[5]
                        campo7 = r[6]
                        campo8 = r[7]
                        campo9 = r[8]
                        campo10 = r[9]
                        campo11 = r[10]
                        campo12 = r[11]
                        campo13 = r[12]
                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, style1)
                        ws.write(row_num, 6, campo7, font_style2)
                        ws.write(row_num, 7, campo8, font_style2)
                        ws.write(row_num, 8, campo9, font_style2)
                        ws.write(row_num, 9, campo10, font_style2)
                        ws.write(row_num, 10, campo11, font_style2)
                        ws.write(row_num, 11, campo12, font_style2)
                        ws.write(row_num, 12, campo13, font_style2)
                        row_num += 1
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            if action == 'descargarlotaip':
                try:
                    __author__ = 'Unemi'
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
                        'Content-Disposition'] = 'attachment; filename=empleados_' + random.randint(
                        1, 10000).__str__() + '.xls'
                    columns = [
                        (u"N", 1000),
                        # (u"CODIGOPERSONA", 2000),
                        (u"CEDULA", 3000),
                        (u"NOMBRES", 11000),
                        (u"PUESTO", 11000),
                        (u"UNIDAD", 14444),
                        (u"DIRECCION INSTITUCIONAL", 9000),
                        (u"CIUDAD QUE LABORA", 5500),
                        (u"TELEFONO", 6000),
                        (u"EXTENSION", 3000),
                        (u"EMAIL INSTITUCIONAL", 7000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    cursor = connection.cursor()
                    # lista_json = []
                    # data = {}
                    sql = "select p.apellido1 , p.apellido2, p.nombres,de.descripcion, dep.nombre, p.telefonoextension ,p.emailinst,p.cedula,p.id " \
                          " from sga_persona p, auth_user usua, sagest_distributivopersona d, sagest_nivelocupacional nio, sagest_modalidadlaboral mod, sagest_regimenlaboral r, sagest_denominacionpuesto de, sagest_departamento dep " \
                          " where p.id=d.persona_id and d.status=true and d.estadopuesto_id=1 and r.id=d.regimenlaboral_id " \
                          " and usua.id=p.usuario_id and d.nivelocupacional_id=nio.id and d.modalidadlaboral_id=mod.id and de.id=d.denominacionpuesto_id and dep.id=d.unidadorganica_id order by p.apellido1,p.apellido2 "
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    row_num = 4
                    a = 0
                    for r in results:
                        i = 0
                        campo1 = i
                        campo2 = r[0]
                        campo3 = r[1]
                        campo4 = r[2]
                        campo5 = r[3]
                        campo6 = r[4]
                        campo7 = r[5]
                        campo8 = r[6]
                        campo9 = r[7]
                        # campo10 = r[8]
                        a += 1
                        ws.write(row_num, 0, a, font_style2)
                        # ws.write(row_num, 1, campo10, font_style2)
                        ws.write(row_num, 1, campo9, font_style2)
                        ws.write(row_num, 2, campo2 + ' ' + campo3 + ' ' + campo4, font_style2)
                        ws.write(row_num, 3, campo5, font_style2)
                        ws.write(row_num, 4, campo6, style1)
                        ws.write(row_num, 5, 'Cdla. Universitaria Km. 1 1/2 vía Km. 26', font_style2)
                        ws.write(row_num, 6, 'MILAGRO', font_style2)
                        ws.write(row_num, 7, '(04) 2 715081 - 2715079', font_style2)
                        ws.write(row_num, 8, campo7, font_style2)
                        ws.write(row_num, 9, campo8, font_style2)
                        row_num += 1
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            if action == 'descargarlotaip':
                try:
                    __author__ = 'Unemi'
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
                        'Content-Disposition'] = 'attachment; filename=empleados_' + random.randint(
                        1, 10000).__str__() + '.xls'
                    columns = [
                        (u"N", 1000),
                        # (u"CODIGOPERSONA", 2000),
                        (u"CEDULA", 3000),
                        (u"NOMBRES", 11000),
                        (u"PUESTO", 11000),
                        (u"UNIDAD", 14444),
                        (u"DIRECCION INSTITUCIONAL", 9000),
                        (u"CIUDAD QUE LABORA", 5500),
                        (u"TELEFONO", 6000),
                        (u"EXTENSION", 3000),
                        (u"EMAIL INSTITUCIONAL", 7000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    cursor = connection.cursor()
                    # lista_json = []
                    # data = {}
                    sql = "select p.apellido1 , p.apellido2, p.nombres,de.descripcion, dep.nombre, p.telefonoextension ,p.emailinst,p.cedula,p.id " \
                          " from sga_persona p, auth_user usua, sagest_distributivopersona d, sagest_nivelocupacional nio, sagest_modalidadlaboral mod, sagest_regimenlaboral r, sagest_denominacionpuesto de, sagest_departamento dep " \
                          " where p.id=d.persona_id and d.status=true and d.estadopuesto_id=1 and r.id=d.regimenlaboral_id " \
                          " and usua.id=p.usuario_id and d.nivelocupacional_id=nio.id and d.modalidadlaboral_id=mod.id and de.id=d.denominacionpuesto_id and dep.id=d.unidadorganica_id and nio.id<>4 order by p.apellido1,p.apellido2 "
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    row_num = 4
                    a = 0
                    for r in results:
                        i = 0
                        campo1 = i
                        campo2 = r[0]
                        campo3 = r[1]
                        campo4 = r[2]
                        campo5 = r[3]
                        campo6 = r[4]
                        campo7 = r[5]
                        campo8 = r[6]
                        campo9 = r[7]
                        # campo10 = r[8]
                        a += 1
                        ws.write(row_num, 0, a, font_style2)
                        # ws.write(row_num, 1, campo10, font_style2)
                        ws.write(row_num, 1, campo9, font_style2)
                        ws.write(row_num, 2, campo2 + ' ' + campo3 + ' ' + campo4, font_style2)
                        ws.write(row_num, 3, campo5, font_style2)
                        ws.write(row_num, 4, campo6, style1)
                        ws.write(row_num, 5, 'Cdla. Universitaria Km. 1 1/2 vía Km. 26', font_style2)
                        ws.write(row_num, 6, 'MILAGRO', font_style2)
                        ws.write(row_num, 7, '(04) 2 715081 - 2715079', font_style2)
                        ws.write(row_num, 8, campo7, font_style2)
                        ws.write(row_num, 9, campo8, font_style2)
                        row_num += 1
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Directorio de extensiones'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    plantillas = DistributivoPersona.objects.filter(Q(persona__nombres__icontains=search) |
                                                                    Q(persona__apellido1__icontains=search) |
                                                                    Q(persona__apellido2__icontains=search) |
                                                                    Q(persona__cedula__icontains=search) |
                                                                    Q(persona__pasaporte__icontains=search), status=True, estadopuesto__id=PUESTO_ACTIVO_ID).distinct()
                else:
                    plantillas = DistributivoPersona.objects.filter(Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1]), status=True, estadopuesto__id=PUESTO_ACTIVO_ID).distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                plantillas = DistributivoPersona.objects.filter(id=ids, status=True, estadopuesto__id=PUESTO_ACTIVO_ID).order_by('persona__telefonoextension')
            else:
                plantillas = DistributivoPersona.objects.filter(status=True, estadopuesto__id=PUESTO_ACTIVO_ID).order_by('persona__telefonoextension')
            paging = MiPaginador(plantillas, 20)
            p = 1
            try:
                paginasesion = 1
                if 'paginador' in request.session:
                    paginasesion = int(request.session['paginador'])
                if 'page' in request.GET:
                    p = int(request.GET['page'])
                else:
                    p = paginasesion
                try:
                    page = paging.page(p)
                except:
                    p = 1
                page = paging.page(p)
            except:
                page = paging.page(p)
            request.session['paginador'] = p
            data['paging'] = paging
            data['rangospaging'] = paging.rangos_paginado(p)
            data['page'] = page
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['plantillas'] = page.object_list
            data['email_domain'] = EMAIL_DOMAIN
            return render(request, 'th_telefonia/view.html', data)
