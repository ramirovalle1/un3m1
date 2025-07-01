# -*- coding: UTF-8 -*-
import xlwt
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models import Q
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template
from decorators import secure_module
from sagest.funciones import dominio_sistema_base
from sagest.models import PermisoInstitucional, PermisoAprobacion, PermisoInstitucionalDetalle, TipoPermiso
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, generar_nombre
import xlwt
import xlsxwriter
from xlwt import easyxf, XFStyle, Workbook, Alignment


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'verdetalle':
                try:
                    data = {}
                    detalle = PermisoInstitucional.objects.get(pk=int(request.GET['id']))
                    data['permiso'] = detalle
                    data['detallepermiso'] = detalle.permisoinstitucionaldetalle_set.all()
                    data['aprobadores'] = detalle.permisoaprobacion_set.all()
                    template = get_template("th_permiso_institucional/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'cargar_tipopermiso':
                try:
                    lista = [{'id': p.id, 'descripcion': p.descripcion} for p in TipoPermiso.objects.filter(status=True)]
                    return JsonResponse({"result": "ok", "data": lista})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'generarexcelpermisos':
                try:
                    tipo = request.GET.get('tipo', '0')
                    fechainicio = request.GET.get('fechai', '')
                    fechafinal = request.GET.get('fechaf', '')
                    filtro = Q(status=True)
                    if tipo != '0':
                        filtro = filtro & Q(tipopermiso_id=int(tipo))
                    if fechainicio != '':
                        filtro = filtro & Q(fechasolicitud__gte=fechainicio)
                    if fechafinal != '':
                        filtro = filtro & Q(fechasolicitud__lte=fechafinal)

                    permisos = PermisoInstitucional.objects.filter(filtro).order_by('estadosolicitud', '-fechasolicitud')

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
                    font_style_center = XFStyle()
                    font_style_center.alignment.horz = Alignment.HORZ_CENTER
                    font_style_center.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('reporte')
                    ws.write_merge(0, 0, 0, 10, 'REPORTE DE PERMISOS INSTITUCIONALES', title)
                    columns = [
                        (u"CÓDIGO", 4000),
                        (u"FECHA", 3000),
                        (u"ESTADO", 4000),
                        (u"CÉDULA", 4000),
                        (u"SOLICITANTE", 10000),
                        (u"DIRECCIÓN", 10000),
                        (u"TIPO SOLICITUD", 6000),
                        (u"TIPO PERMISO", 9000),
                        (u"MOTIVO", 10000),
                        (u"SOPORTE", 9000),
                    ]
                    row_num = 1
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_format.alignment.horz = Alignment.HORZ_CENTER
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    row_num = 2
                    for permiso in permisos:
                        url_archivo = dominio_sistema_base(request) + permiso.archivo.url if permiso.archivo else ''
                        ws.write(row_num, 0, permiso.codificacion(), font_style2)
                        ws.write(row_num, 1, permiso.fechasolicitud, date_format)
                        ws.write(row_num, 2, permiso.get_estadosolicitud_display(), font_style2)
                        ws.write(row_num, 3, permiso.solicita.cedula, font_style2)
                        ws.write(row_num, 4, u"%s" % permiso.solicita.nombre_completo(), font_style2)
                        ws.write(row_num, 5, u"%s" % permiso.unidadorganica, font_style2)
                        ws.write(row_num, 6, permiso.get_tiposolicitud_display(), font_style2)
                        ws.write(row_num, 7, permiso.tipopermiso.descripcion if permiso.tipopermiso else '', font_style2)
                        ws.write(row_num, 8, permiso.motivo, font_style2)
                        ws.write(row_num, 9, url_archivo, font_style2)
                        row_num += 1

                    response = HttpResponse(content_type='application/ms-excel')
                    filename = generar_nombre(f'reporte_permisos_', 'genrado') + ".xls"
                    response['Content-Disposition'] = f'attachment; filename={filename}'
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass


            if action == 'xlsaprobarpermiso':
                try:
                    cursor = connection.cursor()
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_aprobarpermiso.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    ws.col(0).width = 1000
                    ws.col(1).width = 6000
                    ws.col(2).width = 3000
                    ws.col(3).width = 3000
                    ws.col(4).width = 3000
                    ws.col(5).width = 8000
                    ws.col(6).width = 8000
                    ws.col(7).width = 3000
                    ws.col(8).width = 3000
                    ws.col(6).width = 3000
                    ws.col(10).width = 15000
                    ws.col(11).width = 2000
                    ws.col(12).width = 15000
                    ws.col(13).width = 2000

                    ws.write(0, 0, 'N.')
                    ws.write(0, 1, 'CODIGO')
                    ws.write(0, 2, 'FECHA')
                    ws.write(0, 3, 'FECHA INICIO')
                    ws.write(0, 4, 'FECHA FIN')
                    ws.write(0, 5, 'HORA INICIO')
                    ws.write(0, 6, 'HORA FIN')
                    ws.write(0, 7, 'DIAS')
                    ws.write(0, 8, 'HORAS')
                    ws.write(0, 9, 'TOTAL HORAS')
                    ws.write(0, 10, 'ESTADO')
                    ws.write(0, 11, 'CEDULA')
                    ws.write(0, 12, 'SOLICITANTE')
                    ws.write(0, 13, 'DEPARTAMENTO')
                    ws.write(0, 14, 'TIPO SOLICIDUTD')
                    ws.write(0, 15, 'TIPO PERMISO')
                    ws.write(0, 16, 'DETALLE PERMISO')
                    ws.write(0, 17, 'DESCUENTO VACACIONES')
                    ws.write(0, 18, 'MOTIVO')
                    ws.write(0, 19, 'SOPORTE')
                    ws.write(0, 20, 'USUARIO')

                    a = 0
                    date_format = xlwt.XFStyle()
                    hora_format = xlwt.XFStyle()
                    fechainicio = request.GET['fechainicio']
                    fechafinal = request.GET['fechafinal']
                    date_format.num_format_str = 'yyyy/mm/dd'
                    hora_format.num_format_str = '[h]:mm:ss; @'
                    cursor = connection.cursor()
                    cursor.execute("select CAST(sum(totaleshora)AS text) as totales from (select CAST((de.fechafin-de.fechainicio)AS text) as dias,CAST((de.horafin-de.horainicio)AS text) as horas,(cast(CAST((de.horafin-de.horainicio)AS text) as time) * ((CAST((de.fechafin-de.fechainicio)AS int))+1))  as totaleshora from sagest_permisoinstitucionaldetalle de,sagest_permisoinstitucional per where de.permisoinstitucional_id=per.id and per.fechasolicitud >= '" + str(fechainicio) + "' and per.fechasolicitud <= '" + str(fechafinal) + "' and de.horafin > de.horainicio) as f")
                    resultas = cursor.fetchall()
                    for re in resultas:
                        tot_horas = re[0]
                    # plantillas = PermisoInstitucional.objects.filter(fechasolicitud__gte=fechainicio, fechasolicitud__lte=fechafinal).order_by('estadosolicitud', '-fechasolicitud')
                    plantillas = PermisoInstitucionalDetalle.objects.filter(permisoinstitucional__fechasolicitud__gte=fechainicio, permisoinstitucional__fechasolicitud__lte=fechafinal,permisoinstitucional__status=True).order_by('permisoinstitucional__estadosolicitud', '-permisoinstitucional__fechasolicitud')
                    archivos = ''
                    for per in plantillas:
                        nompersona = ''
                        # if PermisoAprobacion.objects.filter(permisoinstitucional=per).exists():
                        #     aprobadores = PermisoAprobacion.objects.filter(permisoinstitucional=per)
                        #     if aprobadores.count() > 1:
                        #         apro = PermisoAprobacion.objects.filter(permisoinstitucional=per).order_by('-id')[0]
                        #         nompersona = u"%s" % apro.aprueba
                        if PermisoAprobacion.objects.filter(permisoinstitucional=per.permisoinstitucional,status=True).exists():
                            aprobadores = PermisoAprobacion.objects.filter(permisoinstitucional=per.permisoinstitucional,status=True)
                            if aprobadores.count() > 1:
                                apro = PermisoAprobacion.objects.filter(permisoinstitucional=per.permisoinstitucional,status=True).order_by('-id')[0]
                                nompersona = u"%s" % apro.aprueba
                        horas = 0
                        totaldias = 0
                        sumahoras = 0
                        if per.horafin > per.horainicio:
                            cursor = connection.cursor()
                            cursor.execute("select CAST((fechafin-fechainicio)AS text) as dias,CAST((horafin-horainicio)AS text) as horas,CAST((cast(CAST((horafin-horainicio)AS text) as time) * ((CAST((fechafin-fechainicio)AS int))+1))  as text) as totaleshora from sagest_PermisoInstitucionalDetalle where id=" + str(per.id))
                            results = cursor.fetchall()
                            for r in results:
                                # if r[0] == '0':
                                #     # diastotales = r[0]
                                #     totalhoras = r[2]
                                # else:
                                #     # diastotales = int(r[0]) + 1
                                #     totalhoras = r[2]
                                #     # horastotales = r[1]
                                horas = r[1]
                                sumahoras = r[2]
                            # horas = 1
                        if per.fechafin > per.fechainicio:
                            totald = per.fechafin - per.fechainicio
                            totaldias = int(totald.days)
                            if totaldias == 1:
                                totaldias = 2
                            else:
                                totaldias = totaldias + 1
                        # listafini = []
                        # listaffin = []
                        # listahini = []
                        # listahfin = []
                        # listatotalhoras = []
                        # diastotales = ''
                        # horastotales = ''
                        # permisosdetalles = PermisoInstitucionalDetalle.objects.filter(permisoinstitucional=per)
                        # for perdetalles in permisosdetalles:
                        #     if permisosdetalles.count() > 1:
                        #         listafini.append(('%s-' % perdetalles.fechainicio))
                        #         listaffin.append(('%s-' % perdetalles.fechafin))
                        #         listahini.append(('%s-' % perdetalles.horainicio))
                        #         listahfin.append(('%s-' % perdetalles.horafin))
                        #         cursor = connection.cursor()
                        #         if perdetalles.horafin > perdetalles.horainicio:
                        #             cursor.execute(
                        #                 "select CAST((fechafin-fechainicio)AS text) as dias,CAST((horafin-horainicio)AS text) as horas,CAST((cast(CAST((horafin-horainicio)AS text) as time) * ((CAST((fechafin-fechainicio)AS int))+1))  as text)  as totaleshora from sagest_PermisoInstitucionalDetalle where id=" + str(
                        #                     perdetalles.id))
                        #         else:
                        #             cursor.execute(
                        #                 "select CAST((fechafin-fechainicio)AS text) as dias,CAST((horafin-horainicio)AS text) as horas,0 as totaleshora from sagest_PermisoInstitucionalDetalle where id=" + str(
                        #                     perdetalles.id))
                        #         results = cursor.fetchall()
                        #         diastotales = 0;
                        #         for r in results:
                        #             if r[0] == '0':
                        #                 # diastotales = r[0]
                        #                 totalhoras = r[2]
                        #             else:
                        #                 # diastotales = int(r[0]) + 1
                        #                 totalhoras = r[2]
                        #             # horastotales = r[1]
                        #         listatotalhoras.append(0)
                        #     else:
                        #         cursor = connection.cursor()
                        #         if perdetalles.horafin > perdetalles.horainicio:
                        #             cursor.execute("select CAST((fechafin-fechainicio)AS text) as dias,CAST((horafin-horainicio)AS text) as horas,CAST((cast(CAST((horafin-horainicio)AS text) as time) * ((CAST((fechafin-fechainicio)AS int))+1))  as text)  as totaleshora from sagest_PermisoInstitucionalDetalle where id="+str(perdetalles.id))
                        #         else:
                        #             cursor.execute("select CAST((fechafin-fechainicio)AS text) as dias,CAST((horafin-horainicio)AS text) as horas,0 as totaleshora from sagest_PermisoInstitucionalDetalle where id="+str(perdetalles.id))
                        #         results = cursor.fetchall()
                        #         diastotales = 0;
                        #         for r in results:
                        #             if r[0] == '0':
                        #                 diastotales = r[0]
                        #                 totalhoras = r[2]
                        #             else:
                        #                 diastotales = int(r[0])+1
                        #                 totalhoras = r[2]
                        #             horastotales = r[1]
                        #         fini = perdetalles.fechainicio
                        #         ffin = perdetalles.fechafin
                        #
                        #         listahini.append(str(perdetalles.horainicio))
                        #         listahfin.append(str(perdetalles.horafin))
                        #         listatotalhoras.append(str(totalhoras))
                        a += 1
                        ws.write(a, 0, a)
                        ws.write(a, 1, per.permisoinstitucional.codificacion())
                        ws.write(a, 2, per.permisoinstitucional.fechasolicitud, date_format)
                        # if permisosdetalles.count() == 1:
                        #     ws.write(a, 3, fini, date_format)
                        #     ws.write(a, 4, ffin, date_format)
                        #     ws.write(a, 5, listahini)
                        #     ws.write(a, 6, listahfin)
                        # else:
                        #     ws.write(a, 3, '%s' % listafini)
                        #     ws.write(a, 4, '%s' % listaffin)
                        #     ws.write(a, 5, '%s' % listahini)
                        #     ws.write(a, 6, '%s' % listahfin)
                        ws.write(a, 3, '%s' % per.fechainicio)
                        ws.write(a, 4, '%s' % per.fechafin)
                        ws.write(a, 5, '%s' % per.horainicio)
                        ws.write(a, 6, '%s' % per.horafin)
                        # ws.write(a, 7, diastotales)
                        # ws.write(a, 8, horastotales)
                        # ws.write(a, 9, '%s' % listatotalhoras)
                        ws.write(a, 7, totaldias)
                        ws.write(a, 8, horas, hora_format)
                        ws.write(a, 9, sumahoras,hora_format)
                        ws.write(a, 10, per.permisoinstitucional.get_estadosolicitud_display())
                        ws.write(a, 11, per.permisoinstitucional.solicita.cedula)
                        ws.write(a, 12, u"%s" % per.permisoinstitucional.solicita.nombre_completo())
                        ws.write(a, 13, u"%s" % per.permisoinstitucional.unidadorganica.nombre)
                        ws.write(a, 14, per.permisoinstitucional.get_tiposolicitud_display().upper())
                        if per.permisoinstitucional.tipopermiso:
                            ws.write(a, 15, u"%s" % per.permisoinstitucional.tipopermiso.descripcion)
                        else:
                            ws.write(a, 15, '')
                        if per.permisoinstitucional.tipopermisodetalle:
                            ws.write(a, 16, u"%s" % per.permisoinstitucional.tipopermisodetalle.descripcion)
                        else:
                            ws.write(a, 16, '')
                        if per.permisoinstitucional.descuentovacaciones:
                            ws.write(a, 17, 'SI')
                        else:
                            ws.write(a, 17, 'NO')
                        ws.write(a, 18, u"%s" % per.permisoinstitucional.motivo)
                        if per.permisoinstitucional.archivo:
                            archivos = 'SI'
                        else:
                            archivos = 'NO'
                        ws.write(a, 19, archivos)
                        ws.write(a, 20, nompersona)
                    ws.write(a+2, 8, 'TOTAL HORAS')
                    ws.write(a+2, 9, tot_horas,hora_format)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Consultar Permiso Institucional.'
            search = None
            ids = None
            plantillas = PermisoInstitucional.objects.all().order_by('estadosolicitud', '-fechasolicitud')
            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    plantillas = plantillas.filter(Q(solicita__nombres__icontains=search) |
                                                   Q(solicita__apellido1__icontains=search) |
                                                   Q(solicita__apellido2__icontains=search) |
                                                   Q(solicita__cedula__icontains=search) |
                                                   Q(motivo__icontains=search)).distinct().order_by('estadosolicitud', '-fechasolicitud')
                else:
                    plantillas = plantillas.filter(Q(solicita__apellido1__icontains=ss[0]) & Q(solicita__apellido2__icontains=ss[1])).distinct().order_by(
                        'estadosolicitud', '-fechasolicitud')
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
            data['permisos'] = page.object_list
            data['email_domain'] = EMAIL_DOMAIN
            return render(request, 'th_permiso_institucional/consultar_view.html', data)