# -*- coding: UTF-8 -*-
from xlwt import *
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from settings import UTILIZA_FICHA_MEDICA
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador
from sga.models import ProfesorMateria, Profesor


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']

    if request.method == 'POST':
        action = request.POST['action']

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Planificación de profesores'
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'verevidencia':
                try:
                    data['title'] = u'Planificación de materia'
                    data['materias'] = ProfesorMateria.objects.filter(profesor__id=request.GET['id'], materia__nivel__periodo=periodo)
                    return render(request, "doc_planificacion/planificaciones.html", data)
                except Exception as ex:
                    pass

            if action == 'excelevidencia':
                try:
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
                    ws.write_merge(0, 0, 0, 10, 'PLANIFICACIÓN DE MATERIA', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=planificacion.xls'
                    row_num = 2
                    for materia in ProfesorMateria.objects.filter(profesor__id=request.GET['id'], materia__nivel__periodo=periodo):
                        tmateria = "Materia: %s" % materia.materia
                        ws.write(row_num, 0, tmateria, font_style2)
                        row_num += 1
                        tfecha = "Fechas: %s al %s" % (materia.materia.inicio,materia.materia.fin)
                        ws.write(row_num, 0, tfecha, font_style2)
                        row_num += 1
                        for campomodelo in materia.materia.modeloevaluativo.campos_editables1():
                            tcampo = "Campo: %s" % campomodelo
                            ws.write(row_num, 0, tcampo, font_style2)
                            row_num += 1

                            columns = [
                                (u"DESCRIPCIÓN", 6000),
                                (u"TIPO PLANIFICACIÓN", 6000),
                                (u"DESDE", 6000),
                                (u"HASTA", 6000),
                                (u"EL LINEA?", 6000),
                                (u"PARA EVALIAR?", 6000),
                                (u"CALIFICADOS", 6000)
                            ]

                            for col_num in range(len(columns)):
                                ws.write(row_num, col_num, columns[col_num][0], font_style)
                                ws.col(col_num).width = columns[col_num][1]
                            row_num += 1

                            for planificacionmateria in campomodelo.planificaciones(materia.materia):
                                planificacionesmateriarealizadas = campomodelo.planificacionesrealizadas(materia.materia,planificacionmateria)
                                campo1 = planificacionmateria.descripcion
                                campo2 = planificacionmateria.tipoplanificacion.nombre
                                campo3 = planificacionmateria.desde
                                campo4 = planificacionmateria.hasta
                                campo5 = 'NO'
                                if planificacionmateria.enlinea:
                                    campo5 = 'SI'
                                campo6 = 'NO'
                                if planificacionmateria.paraevaluacion:
                                    campo6 = 'SI'
                                campo7 = "%s/%s" % (planificacionesmateriarealizadas,materia.materia.cantidad_asignados_a_esta_materia_sinretirados())
                                ws.write(row_num, 0, campo1, font_style2)
                                ws.write(row_num, 1, campo2, font_style2)
                                ws.write(row_num, 2, campo3, font_style2)
                                ws.write(row_num, 3, campo4, style1)
                                ws.write(row_num, 4, campo5, style1)
                                ws.write(row_num, 5, campo6, font_style2)
                                ws.write(row_num, 6, campo7, font_style2)
                                # while i < len(r):
                                #     # ws.write(row_num, i, r[i], font_style)
                                #     # ws.col(i).width = columns[i][1]
                                row_num += 1
                            row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            if not request.session['periodo'].visible:
                return HttpResponseRedirect("/?info=Periodo Inactivo.")
            if 's' in request.GET:
                search = request.GET['s']
                ss = search.split(' ')
                if len(ss) == 1:
                    profesores = Profesor.objects.filter(Q(persona__nombres__icontains=search) |
                                                         Q(persona__apellido1__icontains=search) |
                                                         Q(persona__apellido2__icontains=search) |
                                                         Q(persona__cedula__icontains=search) |
                                                         Q(persona__pasaporte__icontains=search), profesormateria__materia__nivel__periodo=periodo).distinct().order_by('-persona__usuario__is_active', 'persona__apellido1', 'persona__apellido2', 'persona__nombres')
                else:
                    profesores = Profesor.objects.filter(Q(persona__apellido1__icontains=ss[0]) &
                                                         Q(persona__apellido2__icontains=ss[1]), profesormateria__materia__nivel__periodo=periodo).distinct().order_by('-persona__usuario__is_active', 'persona__apellido1', 'persona__apellido2', 'persona__nombres')
            elif 'id' in request.GET:
                ids = request.GET['id']
                profesores = Profesor.objects.filter(id=ids, profesormateria__materia__nivel__periodo=periodo).distinct().order_by('-persona__usuario__is_active', 'persona__apellido1', 'persona__apellido2', 'persona__nombres')
            else:
                profesores = Profesor.objects.filter(profesormateria__materia__nivel__periodo=periodo).distinct().order_by('-persona__usuario__is_active', 'persona__apellido1', 'persona__apellido2', 'persona__nombres').distinct()
            paging = MiPaginador(profesores, 25)
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
            data['profesores'] = page.object_list
            data['alum'] = 0
            data['utiliza_ficha_medica'] = UTILIZA_FICHA_MEDICA
            return render(request, "doc_planificacion/view.html", data)