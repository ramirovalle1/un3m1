from xlwt import *
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, convertir_fecha, convertirfechahorainvertida
from sga.models import RegistrarIngresoCrai, BuzonMundoCrai, SolicitudCompraLibro
from sga.funcionesxhtml2pdf import conviert_html_to_pdf

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()

def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['periodo'] = periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'pdfgeneral':
            try:
                fecha = request.POST['fecha']
                fecha_hasta = request.POST['fecha_hasta']
                cursor = connection.cursor()
                data['title'] = u'Gráficas Acceso al CRAI General, fecha: ' + fecha
                colores = [u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8", u"FF335B", u"33FFA4", u"#b87333",
                           u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8",
                           u"FF335B", u"33FFA4", u"#b87333", u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33",
                           u"3370FF", u"D733FF", u"FF33A8", u"FF335B", u"33FFA4", u"#b87333", u"silver", u"gold",
                           u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8", u"FF335B", u"33FFA4",
                           u"#b87333", u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF",
                           u"FF33A8", u"FF335B", u"33FFA4", u"#b87333", u"silver", u"gold", u"#e5e4e2", u"FF3333",
                           u"8AFF33", u"3370FF", u"D733FF", u"FF33A8", u"FF335B", u"33FFA4", u"#b87333", u"silver",
                           u"gold", u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8", u"FF335B",
                           u"33FFA4", u"#b87333", u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF",
                           u"D733FF", u"FF33A8", u"FF335B", u"33FFA4", u"#b87333", u"silver", u"gold", u"#e5e4e2",
                           u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8", u"FF335B", u"33FFA4", u"#b87333",
                           u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8",
                           u"FF335B", u"33FFA4", u"#b87333", u"silver", u"gold", u"#e5e4e2"]
                # sql general
                sql1 = ""
                sql1 = "select 1, 'ESTUDIANTES', count(rc.id) from sga_registraringresocrai rc " \
                       " where rc.status=true and rc.fecha BETWEEN '" + fecha + "' and '" + fecha_hasta + "' and rc.persona_id is null " \
                                                                                                          " union " \
                                                                                                          " select 2, 'VISITAS EXTERNOS', count(rc.id) from sga_registraringresocrai rc " \
                                                                                                          " where rc.status=true and rc.fecha BETWEEN '" + fecha + "' and '" + fecha_hasta + "' and rc.inscripcion_id is null order by 1"

                # sql por facultad
                sql2 = ""
                sql2 = "select 1, co.alias, count(rc.id) from sga_registraringresocrai rc, sga_inscripcion i, sga_carrera ca, " \
                       " sga_coordinacion_carrera cc, sga_coordinacion co " \
                       " where rc.status=true and rc.fecha BETWEEN '" + fecha + "' and '" + fecha_hasta + "' and rc.inscripcion_id=i.id and i.status=true " \
                                                                                                          " and i.carrera_id=ca.id and ca.status=true and cc.carrera_id=ca.id and co.id=cc.coordinacion_id and co.status=true " \
                                                                                                          " GROUP by co.id " \
                                                                                                          " union " \
                                                                                                          " select 2, 'VISITAS EXTERNOS', count(rc.id) from sga_registraringresocrai rc " \
                                                                                                          " where rc.status=true and rc.fecha BETWEEN '" + fecha + "' and '" + fecha_hasta + "' and rc.inscripcion_id is null order by 1"

                # sql por carrera
                sql3 = ""
                sql3 = "select 1, ca.alias, count(rc.id) from sga_registraringresocrai rc, sga_inscripcion i, sga_carrera ca " \
                       " where rc.status=true and rc.fecha BETWEEN '" + fecha + "' and '" + fecha_hasta + "' and rc.inscripcion_id=i.id and i.status=true " \
                                                                                                          " and i.carrera_id=ca.id and ca.status=true GROUP by ca.id " \
                                                                                                          " union " \
                                                                                                          " select 2, 'VISITAS EXTERNOS', count(rc.id) from sga_registraringresocrai rc " \
                                                                                                          " where rc.status=true and rc.fecha BETWEEN '" + fecha + "' and '" + fecha_hasta + "' and rc.inscripcion_id is null order by 1"

                # ejecucion por general
                cursor.execute(sql1)
                results = cursor.fetchall()
                resultadosgeneral = []
                total = 0
                i = 0
                for r in results:
                    resultadosgeneral.append([r[1], r[2], u'%s' % colores[i]])
                    i += 1
                    total = total + int(r[2])

                # ejecucion por facultad
                cursor.execute(sql2)
                results = cursor.fetchall()
                resultadosfacultad = []
                i = 0
                for r in results:
                    resultadosfacultad.append([r[1], r[2], u'%s' % colores[i]])
                    i += 1

                # ejecucion por carrera
                cursor.execute(sql3)
                results = cursor.fetchall()
                resultadoscarrera = []
                i = 0
                for r in results:
                    resultadoscarrera.append([u'%s' % r[1], r[2], u'%s' % colores[i]])
                    i += 1

                data['total'] = total
                data['resultadosgeneral'] = resultadosgeneral
                data['resultadosfacultad'] = resultadosfacultad
                data['resultadoscarrera'] = resultadoscarrera
                data['fecha'] = fecha
                data['fecha_hasta'] = fecha_hasta

                return conviert_html_to_pdf(
                    'adm_crai_directores/generalpdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'piechartingresocrai':
                try:
                    fecha = request.GET['fecha']
                    fecha_hasta = request.GET['fecha_hasta']
                    cursor = connection.cursor()
                    data['title'] = u'Gráficas Acceso al CRAI General, fecha: ' + fecha
                    colores = [u"FF3333",u"8AFF33",u"3370FF",u"D733FF",u"FF33A8",u"FF335B",u"33FFA4",u"#b87333",u"silver",u"gold",u"#e5e4e2",u"FF3333",u"8AFF33",u"3370FF",u"D733FF",u"FF33A8",u"FF335B",u"33FFA4",u"#b87333",u"silver",u"gold",u"#e5e4e2",u"FF3333",u"8AFF33",u"3370FF",u"D733FF",u"FF33A8",u"FF335B",u"33FFA4",u"#b87333",u"silver",u"gold",u"#e5e4e2",u"FF3333",u"8AFF33",u"3370FF",u"D733FF",u"FF33A8",u"FF335B",u"33FFA4",u"#b87333",u"silver",u"gold",u"#e5e4e2",u"FF3333",u"8AFF33",u"3370FF",u"D733FF",u"FF33A8",u"FF335B",u"33FFA4",u"#b87333",u"silver",u"gold",u"#e5e4e2",u"FF3333",u"8AFF33",u"3370FF",u"D733FF",u"FF33A8",u"FF335B",u"33FFA4",u"#b87333",u"silver",u"gold",u"#e5e4e2",u"FF3333",u"8AFF33",u"3370FF",u"D733FF",u"FF33A8",u"FF335B",u"33FFA4",u"#b87333",u"silver",u"gold",u"#e5e4e2",u"FF3333",u"8AFF33",u"3370FF",u"D733FF",u"FF33A8",u"FF335B",u"33FFA4",u"#b87333",u"silver",u"gold",u"#e5e4e2",u"FF3333",u"8AFF33",u"3370FF",u"D733FF",u"FF33A8",u"FF335B",u"33FFA4",u"#b87333",u"silver",u"gold",u"#e5e4e2",u"FF3333",u"8AFF33",u"3370FF",u"D733FF",u"FF33A8",u"FF335B",u"33FFA4",u"#b87333",u"silver",u"gold",u"#e5e4e2"]
                    # sql general
                    sql1 = ""
                    sql1="select 1, 'ESTUDIANTES', count(rc.id) from sga_registraringresocrai rc " \
                         " where rc.status=true and rc.fecha BETWEEN '"+ fecha +"' and '"+ fecha_hasta +"' and rc.persona_id is null " \
                         " union " \
                         " select 2, 'VISITAS EXTERNOS', count(rc.id) from sga_registraringresocrai rc " \
                         " where rc.status=true and rc.fecha BETWEEN '"+ fecha +"' and '"+ fecha_hasta +"' and rc.inscripcion_id is null order by 1"

                    # sql por facultad
                    sql2=""
                    sql2="select 1, co.alias, count(rc.id) from sga_registraringresocrai rc, sga_inscripcion i, sga_carrera ca, " \
                         " sga_coordinacion_carrera cc, sga_coordinacion co " \
                         " where rc.status=true and rc.fecha BETWEEN '"+ fecha +"' and '"+ fecha_hasta +"' and rc.inscripcion_id=i.id and i.status=true " \
                         " and i.carrera_id=ca.id and ca.status=true and cc.carrera_id=ca.id and co.id=cc.coordinacion_id and co.status=true " \
                         " GROUP by co.id " \
                         " union " \
                         " select 2, 'VISITAS EXTERNOS', count(rc.id) from sga_registraringresocrai rc " \
                         " where rc.status=true and rc.fecha BETWEEN '"+ fecha +"' and '"+ fecha_hasta +"' and rc.inscripcion_id is null order by 1"

                    # sql por carrera
                    sql3 = ""
                    sql3="select 1, ca.alias, count(rc.id) from sga_registraringresocrai rc, sga_inscripcion i, sga_carrera ca " \
                        " where rc.status=true and rc.fecha BETWEEN '"+ fecha +"' and '"+ fecha_hasta +"' and rc.inscripcion_id=i.id and i.status=true " \
                        " and i.carrera_id=ca.id and ca.status=true GROUP by ca.id " \
                        " union " \
                        " select 2, 'VISITAS EXTERNOS', count(rc.id) from sga_registraringresocrai rc " \
                        " where rc.status=true and rc.fecha BETWEEN '"+ fecha +"' and '"+ fecha_hasta +"' and rc.inscripcion_id is null order by 1"

                    # ejecucion por general
                    cursor.execute(sql1)
                    results = cursor.fetchall()
                    resultadosgeneral = []
                    total = 0
                    i=0
                    for r in results:
                        resultadosgeneral.append([r[1],r[2],u'%s' % colores[i]])
                        i +=1
                        total = total + int(r[2])

                    # ejecucion por facultad
                    cursor.execute(sql2)
                    results = cursor.fetchall()
                    resultadosfacultad = []
                    i = 0
                    for r in results:
                        resultadosfacultad.append([r[1],r[2],u'%s' % colores[i]])
                        i += 1

                    # ejecucion por carrera
                    cursor.execute(sql3)
                    results = cursor.fetchall()
                    resultadoscarrera = []
                    i=0
                    for r in results:
                        resultadoscarrera.append([u'%s' % r[1],r[2],u'%s' % colores[i]])
                        i += 1

                    data['total'] = total
                    data['resultadosgeneral'] = resultadosgeneral
                    data['resultadosfacultad'] = resultadosfacultad
                    data['resultadoscarrera'] = resultadoscarrera
                    data['fecha'] = fecha
                    data['fecha_hasta'] = fecha_hasta

                    return render(request, "adm_crai_directores/piechartingresocrai.html", data)
                except Exception as ex:
                    pass

            if action == 'piechartingresocrai_detallado':
                try:
                    fecha = request.GET['fecha']
                    fecha_hasta = request.GET['fecha_hasta']
                    cursor = connection.cursor()
                    data['title'] = u'Gráficas Acceso al CRAI Detallado, fecha: ' + fecha
                    colores = [u"FF3333",u"8AFF33",u"3370FF",u"D733FF",u"FF33A8",u"FF335B",u"33FFA4",u"#b87333",u"silver",u"gold",u"#e5e4e2",u"FF3333",u"8AFF33",u"3370FF",u"D733FF",u"FF33A8",u"FF335B",u"33FFA4",u"#b87333",u"silver",u"gold",u"#e5e4e2",u"FF3333",u"8AFF33",u"3370FF",u"D733FF",u"FF33A8",u"FF335B",u"33FFA4",u"#b87333",u"silver",u"gold",u"#e5e4e2",u"FF3333",u"8AFF33",u"3370FF",u"D733FF",u"FF33A8",u"FF335B",u"33FFA4",u"#b87333",u"silver",u"gold",u"#e5e4e2",u"FF3333",u"8AFF33",u"3370FF",u"D733FF",u"FF33A8",u"FF335B",u"33FFA4",u"#b87333",u"silver",u"gold",u"#e5e4e2"]
                    # sql detallado
                    sql1 = ""
                    sql1 = "select  ts.descripcion, count(rc.id) from sga_registraringresocrai rc, sga_tiposerviciocrai ts  " \
                           " where rc.status=true and rc.fecha BETWEEN '"+ fecha +"' and '"+ fecha_hasta +"'  and rc.tiposerviciocrai_id=ts.id  " \
                           "  and rc.persona_id is null GROUP by ts.id"
                    # ejecucion por detallado
                    cursor.execute(sql1)
                    results = cursor.fetchall()
                    resultadosgeneral = []
                    total = 0
                    i=0
                    for r in results:
                        resultadosgeneral.append([r[0],r[1],u'%s' % colores[i]])
                        i +=1
                        total = total + int(r[1])
                    data['total'] = total
                    data['resultadosgeneral'] = resultadosgeneral

                    # sql detallado
                    sql2 = ""
                    sql2 = "select  ac.descripcion, count(ac.id) from sga_registraringresocrai rc, sga_registraractividadescrai ra, sga_actividadescrai ac   " \
                    " where rc.status=true and rc.fecha BETWEEN '"+ fecha +"' and '"+ fecha_hasta +"' and rc.id=ra.registraringresocrai_id  " \
                    " and rc.persona_id is null and ra.actividadescrai_id=ac.id and ac.status=true GROUP by ac.id"
                    # ejecucion por detallado
                    cursor.execute(sql2)
                    results2 = cursor.fetchall()
                    resultadosgeneral2 = []
                    total2 = 0
                    i2=0
                    for r2 in results2:
                        resultadosgeneral2.append([r2[0],r2[1],u'%s' % colores[i2]])
                        i2 +=1
                        total2 = total2 + int(r2[1])
                    data['total2'] = total2
                    data['resultadosgeneral2'] = resultadosgeneral2
                    data['fecha'] = fecha
                    data['fecha_hasta'] = fecha_hasta

                    return render(request, "adm_crai_directores/piechartingresocrai_detalle.html", data)
                except Exception as ex:
                    pass

            if action == 'descargarexcel':
                try:

                    fecha = convertir_fecha(request.GET['fecha'])
                    fecha_hasta = convertir_fecha(request.GET['fecha_hasta'])
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 10, 'ESTUDIANTES INGRESO - CRAI', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=ingresocrai.xls'
                    columns = [
                        (u"FECHA INGRESO", 2000),
                        (u"PERIODO LECTIVO", 10000),
                        (u"FACULTAD", 10000),
                        (u"CARRERA", 10000),
                        (u"NIVEL", 10000),
                        (u"ESTUDIANTE", 10000),
                    ]
                    row_num = 2
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 3
                    for registro in RegistrarIngresoCrai.objects.filter(status=True, fecha__range=(fecha, fecha_hasta), inscripcion__isnull=False):
                        campo1 = registro.fecha
                        matricula = registro.inscripcion.matricula_crai(campo1)
                        campo2 = ""
                        if matricula:
                            campo2 = matricula.periodo_name()
                        campo3 = registro.inscripcion.carrera.mi_coordinacion()
                        campo4 = registro.inscripcion.carrera.nombre
                        campo5 = ""
                        if matricula:
                            campo5 = matricula.nivelmalla.nombre
                        campo6 = registro.inscripcion.persona.nombre_completo_simple()
                        ws.write(row_num, 0, campo1, style1)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'descargarexcelsugerencias':
                try:

                    fecha = convertirfechahorainvertida(request.GET['fecha']+' 00:00:00')
                    fecha_hasta = convertirfechahorainvertida(request.GET['fecha_hasta']+' 23:59:59')
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 1, 'SUGERENCIAS LIBROS - CRAI', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=sugerencialibros.xls'
                    columns = [
                        (u"FECHA", 3000),
                        (u"LIBRO", 30000),
                    ]
                    row_num = 2
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 3
                    for registro in BuzonMundoCrai.objects.filter(status=True, fecha_creacion__range=(fecha, fecha_hasta)):
                        campo1 = registro.fecha_creacion
                        campo2 = registro.contenido
                        ws.write(row_num, 0, campo1, style1)
                        ws.write(row_num, 1, campo2, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'descargarexcelsugerenciassugerencia':
                try:

                    fecha = convertirfechahorainvertida(request.GET['fecha']+' 00:00:00')
                    fecha_hasta = convertirfechahorainvertida(request.GET['fecha_hasta']+' 23:59:59')
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 1, 'SUGERENCIAS LIBROS - SILABO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=sugerencialibrossilabo.xls'
                    columns = [
                        (u"FECHA", 3000),
                        (u"LIBRO", 30000),
                    ]
                    row_num = 2
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 3
                    for registro in BuzonMundoCrai.objects.filter(status=True, fecha_creacion__range=(fecha, fecha_hasta)):
                        campo1 = registro.fecha_creacion
                        campo2 = registro.contenido
                        ws.write(row_num, 0, campo1, style1)
                        ws.write(row_num, 1, campo2, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Información CRAI UNEMI'
            try:
                search = None
                ids = None
                fecha = None
                fechabuzon = None
                visitas = []
                buzons = []
                # if 'fecha' not in request.GET:
                #     request.GET['fecha'] = str(datetime.now().date().__format__('%d-%m-%Y'))
                # if 'fechabuzon' not in request.GET:
                #     request.GET['fechabuzon'] = str(datetime.now().date().__format__('%d-%m-%Y'))

                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if 'fecha' in request.GET:
                        fecha = convertir_fecha(request.GET['fecha'])
                        if len(ss) == 1:
                            visitas = RegistrarIngresoCrai.objects.filter(Q(status=True),
                                                                          ((Q(persona__nombres__icontains=search) |
                                                                            Q(persona__apellido1__icontains=search) |
                                                                            Q(persona__apellido2__icontains=search) |
                                                                            Q(persona__cedula__icontains=search)) | (
                                                                                   Q(inscripcion__persona__nombres__icontains=search) |
                                                                                   Q(inscripcion__persona__apellido1__icontains=search) |
                                                                                   Q(inscripcion__persona__apellido2__icontains=search) |
                                                                                   Q(inscripcion__persona__cedula__icontains=search))),
                                                                          Q(fecha=convertir_fecha(request.GET['fecha']))).order_by('horainicio')
                            #.exclude(horafin__isnull=True)
                        else:
                            visitas = RegistrarIngresoCrai.objects.filter(Q(status=True),
                                                                          (((Q(persona__nombres__icontains=ss[0]) & Q(persona__nombres__icontains=ss[0])) |
                                                                            (Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1]))) | ((Q(
                                                                              inscripcion__persona__nombres__icontains=ss[0]) & Q(inscripcion__persona__nombres__icontains=ss[1])) |
                                                                                                                          (Q(inscripcion__persona__apellido1__icontains=
                                                                                                                              ss[0]) & Q(inscripcion__persona__apellido2__icontains=
                                                                                                                              ss[1])))),
                                                                          Q(fecha=convertir_fecha(request.GET['fecha']))).order_by('horainicio')
                        #.exclude(horafin__isnull=True)
                    else:
                        if len(ss) == 1:
                            visitas = RegistrarIngresoCrai.objects.filter(Q(status=True),
                                                                          ((Q(persona__nombres__icontains=search) |
                                                                            Q(persona__apellido1__icontains=search) |
                                                                            Q(persona__apellido2__icontains=search) |
                                                                            Q(persona__cedula__icontains=search)) | (
                                                                                   Q(inscripcion__persona__nombres__icontains=search) |
                                                                                   Q(inscripcion__persona__apellido1__icontains=search) |
                                                                                   Q(inscripcion__persona__apellido2__icontains=search) |
                                                                                   Q(inscripcion__persona__cedula__icontains=search)))).order_by('horainicio')
                            # .exclude(horafin__isnull=True)
                        else:
                            visitas = RegistrarIngresoCrai.objects.filter(Q(status=True),
                                                                          (((Q(persona__nombres__icontains=ss[0]) & Q(persona__nombres__icontains=ss[0])) |
                                                                            (Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1]))) | (
                                                                                   (Q(inscripcion__persona__nombres__icontains=ss[0]) & Q(inscripcion__persona__nombres__icontains=ss[
                                                                                           1])) |
                                                                                   (Q(inscripcion__persona__apellido1__icontains=ss[0]) & Q(
                                                                                       inscripcion__persona__apellido2__icontains=ss[1]))))).order_by('horainicio')
                            #.exclude(horafin__isnull=True)
                elif 'fecha' in request.GET:
                    visitas = RegistrarIngresoCrai.objects.filter(status=True, fecha=convertir_fecha(request.GET['fecha'])).order_by('horainicio')
                    # .exclude(horafin__isnull=True)
                    fecha = convertir_fecha(request.GET['fecha'])
                elif 'fechabuzon' in request.GET:
                    buzons = BuzonMundoCrai.objects.filter(status=True, fecha_creacion__year=convertir_fecha(request.GET['fechabuzon']).year, fecha_creacion__day=convertir_fecha(request.GET['fechabuzon']).day, fecha_creacion__month=convertir_fecha(request.GET['fechabuzon']).month).order_by('id')
                    fechabuzon = convertir_fecha(request.GET['fechabuzon'])
                solicitudes = SolicitudCompraLibro.objects.filter(status=True, estadosolicitud=1).order_by('-fecha')
                # else:
                #     visitas = RegistrarIngresoCrai.objects.filter(status=True).exclude(horafin__isnull=False).order_by('-fecha', '-horainicio')
                paging = MiPaginador(visitas, 10)
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
                data['visitas'] = page.object_list
                data['buzons'] = buzons
                data['solicitudes'] = solicitudes
                data['fechaselect'] = fecha
                data['fechaselectbuzon'] = fechabuzon
                data['hora'] = datetime.now().time().strftime("%H:%M")
                return render(request, "adm_crai_directores/view.html", data)
            except Exception as ex:
                pass
