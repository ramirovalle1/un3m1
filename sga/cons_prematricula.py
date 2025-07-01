# -*- coding: latin-1 -*-
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction, connection
from django.db.models import Q, Count
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from xlwt import *
import xlwt
from decorators import secure_module, last_access
from settings import CLASES_HORARIO_ESTRICTO
from sga.commonviews import adduserdata, traerNotificaciones
from sga.excelbackground import reporte_pre_matriculados_background
from sga.funciones import log, MiPaginador
from sga.models import PreMatricula, Carrera, Inscripcion, Asignatura, Malla, Notificacion, PreMatriculaAsignatura


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

            if action == 'eliminarprematricula':
                prematricula = PreMatricula.objects.get(pk=int(request.POST['id']))
                log(u'Eliminacion PreMatricula: %s, usuario: %s' % (prematricula, persona), request, "del")
                prematricula.delete()

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Listado de estudiantes con planificación de matricula'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'reporteprematriculados':
                try:
                    idcarrera = request.GET['id']
                    cursor = connection.cursor()
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=prematricula_asignaturas.xls'
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
                    # ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)


                    columns=[
                        (u"N.", 2000),
                        (u"CARRERA", 6000),
                        (u"IDENTIFICACION", 6000),
                        (u"ASIGNATURA", 6000),
                        (u"NIVEL", 4000),
                        (u"MATUTINA", 2000),
                        (u"VESPERTINA", 2000),
                        (u"NOCTURNA", 2000),
                        (u"FIN DE SEMANA", 2000),
                        (u"P1", 2000),
                        (u"P2", 2000),
                        (u"TOTAL", 2000),
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    a = 0
                    listaestudiante = "select codigomalla,carreras,inicio,identificacion,asignatura,nivel,totalmanana,vespertina,nocturna,finsemana," \
                                      "(totalmanana+vespertina+nocturna+finsemana) as total, idasignatura " \
                                      "from (select  smalla.id as codigomalla,carr.nombre as carreras,smalla.inicio,asi.identificacion,(mat.nombre || ' [' || mat.codigo || ']' ) as asignatura," \
                                      "nmall.nombre as nivel,(SELECT count(sga_asignatura.id) FROM sga_asignatura " \
                                      "INNER JOIN sga_prematricula_asignaturas ON (sga_asignatura.id = sga_prematricula_asignaturas.asignatura_id) " \
                                      "INNER JOIN sga_prematricula ON (sga_prematricula_asignaturas.prematricula_id = sga_prematricula.id) " \
                                      "INNER JOIN sga_inscripcion ON (sga_prematricula.inscripcion_id = sga_inscripcion.id) " \
                                      "INNER JOIN sga_inscripcionmalla ON (sga_inscripcion.id = sga_inscripcionmalla.inscripcion_id) " \
                                      "WHERE sga_prematricula.periodo_id = '" + str(periodo.id) + "' AND sga_inscripcion.sesion_id = 1 " \
                                      "AND sga_inscripcionmalla.malla_id = smalla.id " \
                                      "AND sga_asignatura.id = asi.asignatura_id )as totalmanana,(SELECT count(sga_asignatura.id) " \
                                      "FROM sga_asignatura INNER JOIN sga_prematricula_asignaturas ON (sga_asignatura.id = sga_prematricula_asignaturas.asignatura_id) " \
                                      "INNER JOIN sga_prematricula ON (sga_prematricula_asignaturas.prematricula_id = sga_prematricula.id) " \
                                      "INNER JOIN sga_inscripcion ON (sga_prematricula.inscripcion_id = sga_inscripcion.id) " \
                                      "INNER JOIN sga_inscripcionmalla ON (sga_inscripcion.id = sga_inscripcionmalla.inscripcion_id) " \
                                      "WHERE sga_prematricula.periodo_id = '" + str(periodo.id) + "'  AND sga_inscripcion.sesion_id = 4 " \
                                      "AND sga_inscripcionmalla.malla_id = smalla.id  AND sga_asignatura.id = asi.asignatura_id )as vespertina," \
                                      "(SELECT count(sga_asignatura.id)FROM sga_asignatura " \
                                      "INNER JOIN sga_prematricula_asignaturas ON sga_asignatura.id = sga_prematricula_asignaturas.asignatura_id " \
                                      "INNER JOIN sga_prematricula ON sga_prematricula_asignaturas.prematricula_id = sga_prematricula.id " \
                                      "INNER JOIN sga_inscripcion ON sga_prematricula.inscripcion_id = sga_inscripcion.id " \
                                      "INNER JOIN sga_inscripcionmalla ON sga_inscripcion.id = sga_inscripcionmalla.inscripcion_id " \
                                      "WHERE sga_prematricula.periodo_id = '" + str(periodo.id) + "'  AND sga_inscripcion.sesion_id = 5  " \
                                      "AND sga_inscripcionmalla.malla_id = smalla.id  AND sga_asignatura.id = asi.asignatura_id )as nocturna," \
                                      "(SELECT count(sga_asignatura.id) FROM sga_asignatura " \
                                      "INNER JOIN sga_prematricula_asignaturas ON sga_asignatura.id = sga_prematricula_asignaturas.asignatura_id " \
                                      "INNER JOIN sga_prematricula ON sga_prematricula_asignaturas.prematricula_id = sga_prematricula.id " \
                                      "INNER JOIN sga_inscripcion ON sga_prematricula.inscripcion_id = sga_inscripcion.id " \
                                      "INNER JOIN sga_inscripcionmalla ON sga_inscripcion.id = sga_inscripcionmalla.inscripcion_id " \
                                      "WHERE sga_prematricula.periodo_id = '" + str(periodo.id) + "'  AND sga_inscripcion.sesion_id = 7 " \
                                      "AND sga_inscripcionmalla.malla_id = smalla.id  AND sga_asignatura.id = asi.asignatura_id )as finsemana, mat.id as idasignatura " \
                                      "from sga_asignaturamalla asi left join sga_asignatura mat on asi.asignatura_id=mat.id " \
                                      "left join sga_nivelmalla  nmall on nmall.id=asi.nivelmalla_id " \
                                      "left join sga_malla  smalla on smalla.id=asi.malla_id " \
                                      "left join sga_carrera  carr on carr.id=smalla.carrera_id " \
                                      "where carr.id='" + idcarrera + "' order by nmall.id, mat.nombre) as d"
                    cursor.execute(listaestudiante)
                    results = cursor.fetchall()
                    for per in results:
                        asignatura = Asignatura.objects.get(id=int(per[11]))
                        p1 = PreMatricula.objects.filter(periodo=periodo, prematriculaasignatura__asignatura=asignatura, prematriculaasignatura__tipo='P1').count()
                        p2 = PreMatricula.objects.filter(periodo=periodo, prematriculaasignatura__asignatura=asignatura, prematriculaasignatura__tipo='P2').count()

                        a += 1
                        ws.write(a, 0, a)
                        ws.write(a, 1, per[1])
                        ws.write(a, 2, per[3])
                        ws.write(a, 3, per[4])
                        ws.write(a, 4, per[5])
                        ws.write(a, 5, per[6])
                        ws.write(a, 6, per[7])
                        ws.write(a, 7, per[8])
                        ws.write(a, 8, per[9])
                        ws.write(a, 9, str(p1))
                        ws.write(a, 10, str(p2))
                        ws.write(a, 11, per[10])
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            if action == 'materiasprematricula':
                try:
                    data['prematricula'] = prematricula = PreMatricula.objects.get(pk=int(request.GET['id']))
                    # lista = []
                    # for materiasprematricula in prematricula.asignaturas.all():
                    #     lista.append([materiasprematricula.nombre])
                    template = get_template("cons_prematricula/detallelmaterias.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", "html": json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

            if action == 'reporteplanificacion':
                if 'id' in request.GET and int(request.GET['id']) > 0:
                    data['carrera'] = carrera = Carrera.objects.get(pk=request.GET['id'])
                    prematriculas = PreMatriculaAsignatura.objects.filter(prematricula__periodo=periodo, prematricula__inscripcion__carrera=carrera).select_related().order_by('prematricula__inscripcion__persona__apellido1')
                else:
                    prematriculas = PreMatriculaAsignatura.objects.filter(prematricula__periodo=periodo).select_related().order_by('prematricula__inscripcion__persona__apellido1', 'prematricula__inscripcion__carrera__nombre')
                noti = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                    titulo='Reporte de Planificación de Matricula', destinatario=persona,
                                    url='',
                                    prioridad=1, app_label='SGA',
                                    fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                    en_proceso=True)
                noti.save(request)
                reporte_pre_matriculados_background(request=request, data=prematriculas, notiid=noti.pk, periodo=periodo).start()
                return JsonResponse({"result": True,
                                     "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                     "btn_notificaciones": traerNotificaciones(request, data, persona)})

            return HttpResponseRedirect(request.path)
        else:
            querybase = PreMatricula.objects.filter(periodo=periodo)
            data['carreras'] = carreras = querybase.values_list('inscripcion__carrera__id', 'inscripcion__carrera__nombre').order_by('inscripcion__carrera').annotate(total=Count('inscripcion_id'))
            if 'id' in request.GET and int(request.GET['id']) > 0:
                data['carrera'] = carrera = Carrera.objects.get(pk=request.GET['id'])
                # inscripcion = Inscripcion.objects.filter(carrera=carrera).select_related().distinct().order_by('-carrera')
                prematriculas = querybase.filter(periodo=periodo, inscripcion__carrera=carrera).select_related().order_by('inscripcion__persona__apellido1')
                data['id'] = id = carrera.id
            else:
                # data['carrera'] = carrera = carreras[0]
                prematriculas = querybase.select_related().order_by('inscripcion__carrera__nombre', 'inscripcion__persona__apellido1')
                # inscripcion = Inscripcion.objects.all()
                data['id'] = id = 0
            if 's' in request.GET:
                data['search'] = search = request.GET['s']
                ss = search.split(' ')
                if len(ss) == 1:
                    prematriculas = prematriculas.filter(Q(inscripcion__persona__nombres__icontains=search) |
                                                               Q(inscripcion__persona__apellido1__icontains=search) |
                                                               Q(inscripcion__persona__apellido2__icontains=search) |
                                                               Q(inscripcion__persona__cedula__icontains=search)).distinct().order_by('inscripcion__persona')
                else:
                    prematriculas = prematriculas.filter(Q(inscripcion__persona__apellido1__icontains=ss[0]) &
                                                               Q(inscripcion__persona__apellido2__icontains=ss[1])).distinct().order_by('inscripcion__persona')

            # asignaturas = Asignatura.objects.filter(prematricula__inscripcion__carrera=carrera).distinct()

            # data['prematriculas'] = prematriculas
            data['prematriculastotal'] = prematriculas.count()
            # data['asignaturas'] = asignaturas
            data['clases_horario_estricto'] = CLASES_HORARIO_ESTRICTO
            paging = MiPaginador(prematriculas, 25)
            p = 1
            try:
                if 'page' in request.GET:
                    p = int(request.GET['page'])
                page = paging.page(p)
            except Exception as ex:
                page = paging.page(1)
            data['paging'] = paging
            data['rangospaging'] = paging.rangos_paginado(p)
            data['page'] = page
            data['ids'] = id if id else ""
            data['prematriculas'] = page.object_list
            return render(request, "cons_prematricula/view.html", data)
