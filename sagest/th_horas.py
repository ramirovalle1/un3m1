# -*- coding: UTF-8 -*-
import json
import random
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from xlwt import *
from decorators import secure_module
from sagest.forms import PlanificacionHorasExtrasForm
from sagest.models import PlanificacionHorasExtras, PlanificacionHorasExtrasPersona
from settings import PUESTO_ACTIVO_ID
from sga.commonviews import adduserdata
from sga.funciones import log, convertir_fecha, convertir_hora
from sga.models import MESES_CHOICES, Persona


def rango_anios():
    if PlanificacionHorasExtras.objects.exists():
        inicio = datetime.now().year
        fin = PlanificacionHorasExtras.objects.order_by('anio')[0].anio
        return range(inicio, fin - 1, -1)
    return [datetime.now().date().year]

def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    anios = rango_anios()
    adduserdata(request, data)
    persona = request.session['persona']
    departamento = persona.mi_departamento()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addplanificacion':
            try:
                form = PlanificacionHorasExtrasForm(request.POST)
                if form.is_valid():
                    items = json.loads(request.POST['lista_items1'])
                    if len(items) == 0:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar personas para poder asignar planificación"})

                    planificacionhorasextras = PlanificacionHorasExtras(departamento=departamento,
                                                                        mes=form.cleaned_data['mes'],
                                                                        anio=form.cleaned_data['anio'],
                                                                        actividadplanificada=form.cleaned_data['actividad'],
                                                                        observacionplanificada=form.cleaned_data['observacion'])
                    planificacionhorasextras.save(request)

                    for elemento in items:
                        persona1 = Persona.objects.filter(pk=int(elemento['idpersona']))[0]
                        modalidadlaboral = persona1.distributivopersona_set.filter(status=True, estadopuesto__id=PUESTO_ACTIVO_ID)[0].modalidadlaboral
                        regimenlaboral = persona1.distributivopersona_set.filter(status=True, estadopuesto__id=PUESTO_ACTIVO_ID)[0].regimenlaboral
                        planificacionhorasextraspersona = PlanificacionHorasExtrasPersona(planificacion=planificacionhorasextras,
                                                                                          persona_id=int(elemento['idpersona']),
                                                                                          fecha= convertir_fecha(elemento['fecha']),
                                                                                          horadesde = convertir_hora(elemento['horadesde']),
                                                                                          horahasta = convertir_hora(elemento['horahasta']),
                                                                                          actividadplanificada = elemento['actividadplanificada'],
                                                                                          modalidadlaboral = modalidadlaboral,
                                                                                          regimenlaboral = regimenlaboral)
                        planificacionhorasextraspersona.save(request)
                    log(u'Registro nuevo planificación horas extra: %s' % planificacionhorasextras, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'editplanificacion':
            try:

                form = PlanificacionHorasExtrasForm(request.POST)
                if form.is_valid():
                    items = json.loads(request.POST['lista_items1'])
                    if len(items) == 0:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar personas para poder asignar planificación"})
                    planificacionhorasextras = PlanificacionHorasExtras.objects.filter(pk=request.POST['id'])[0]
                    planificacionhorasextras.actividadplanificada=form.cleaned_data['actividad']
                    planificacionhorasextras.observacionplanificada=form.cleaned_data['observacion']
                    planificacionhorasextras.save(request)
                    planificacionhorasextras.planificacionhorasextraspersona_set.all().delete()
                    for elemento in items:
                        persona1 = Persona.objects.filter(pk=int(elemento['idpersona']))[0]
                        modalidadlaboral = persona1.distributivopersona_set.filter(status=True, estadopuesto__id=PUESTO_ACTIVO_ID)[0].modalidadlaboral
                        regimenlaboral = persona1.distributivopersona_set.filter(status=True, estadopuesto__id=PUESTO_ACTIVO_ID)[0].regimenlaboral
                        planificacionhorasextraspersona = PlanificacionHorasExtrasPersona(planificacion=planificacionhorasextras,
                                                                                          persona_id=int(elemento['idpersona']),
                                                                                          fecha= convertir_fecha(elemento['fecha']),
                                                                                          horadesde = convertir_hora(elemento['horadesde']),
                                                                                          horahasta = convertir_hora(elemento['horahasta']),
                                                                                          actividadplanificada=elemento['actividadplanificada'],
                                                                                          modalidadlaboral=modalidadlaboral,
                                                                                          regimenlaboral=regimenlaboral)
                        planificacionhorasextraspersona.save(request)
                    log(u'Registro modificado planificación horas extra: %s' % planificacionhorasextras, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al modificar los datos."})

        if action == 'deleteplanificacion':
            try:
                planificacionhorasextras = PlanificacionHorasExtras.objects.filter(pk=request.POST['id'])[0]
                planificacionhorasextras.status=False
                planificacionhorasextras.save(request)
                planificacionhorasextras.planificacionhorasextraspersona_set.filter(status=True).update(status=False)
                log(u'Elimino planificación horas extra: %s' % planificacionhorasextras, request, "del")
                return JsonResponse({"result": "ok", "id": planificacionhorasextras.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar datos."})

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addplanificacion':
                try:
                    data['title'] = u'Nuevo Planificación Horas Extra'
                    form = PlanificacionHorasExtrasForm(initial={'anio': request.session['anioplanificacion'],
                                                                 'mes': request.session['mesplanificacion']})
                    form.adicionar(departamento)
                    data['form'] = form
                    # data['personas'] = Persona.objects.filter(status=True, distributivopersona__unidadorganica=departamento, distributivopersona__estadopuesto__id=PUESTO_ACTIVO_ID)
                    return render(request, "th_horas/addplanificacion.html", data)
                except Exception as ex:
                    pass

            if action == 'editplanificacion':
                try:
                    data['title'] = u'Editar Planificación Horas Extra'
                    planificacionhorasextras = PlanificacionHorasExtras.objects.filter(pk=request.GET['id'])[0]
                    form = PlanificacionHorasExtrasForm(initial={'anio': planificacionhorasextras.anio,
                                                                 'mes': planificacionhorasextras.mes,
                                                                 'actividad': planificacionhorasextras.actividadplanificada,
                                                                 'observacion': planificacionhorasextras.observacionplanificada})
                    form.editar(departamento)
                    data['form'] = form
                    data['planificacionhorasextraspersonas'] = planificacionhorasextras.planificacionhorasextraspersona_set.filter(status=True)
                    data['planificacionhorasextras'] = planificacionhorasextras
                    return render(request, "th_horas/editplanificacion.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteplanificacion':
                try:
                    data['title'] = u'Eliminar planificación horas extra'
                    data['planificacionhorasextras'] = PlanificacionHorasExtras.objects.get(pk=request.GET['id'])
                    return render(request, "th_horas/delete.html", data)
                except Exception as ex:
                    pass

            if action == 'detalle_planificacion':
                try:
                    data['planificacionhorasextras'] = planificacionhorasextras = PlanificacionHorasExtras.objects.get(pk=request.GET['cid'])
                    data['planificacionhorasextraspersonas'] = planificacionhorasextras.planificacionhorasextraspersona_set.filter(status=True)
                    return render(request, 'th_horas/detalle_planificacion.html', data)
                except Exception as ex:
                    pass

            if action == 'exportarplanificacion':
                try:
                    planificacionhorasextras = PlanificacionHorasExtras.objects.get(pk=request.GET['id'])
                    detalles = planificacionhorasextras.planificacionhorasextraspersona_set.filter(status=True).order_by('fecha','persona')
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    title2 = easyxf('font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    style2 = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    fuentecabecera = easyxf('font: name Times New Roman, color-index black, bold on , height 200; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Times New Roman, color-index black, height 200; borders: left thin, right thin, top thin, bottom thin')
                    title3 = easyxf('font: name Times New Roman, color-index black, bold on , height 200; alignment: horiz centre; borders: top thin')
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 4, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 4, 'UNIDAD DE ADMINISTRACIÓN DE TALENTO HUMANO', title2)
                    ws.write_merge(2, 2, 0, 4, 'INFORME DE PLANIFICACIÓN DE HORAS EXTAORDINARIAS, SUPLEMENTARIAS Y/O NOCTURNAS', title2)
                    ws.write_merge(3, 3, 0, 0, 'ÁREA ADMINISTRATIVA:', font_style)
                    ws.write_merge(3, 3, 1, 1, planificacionhorasextras.departamento.nombre, font_style)
                    ws.write_merge(3, 3, 2, 2, 'MES:', font_style)
                    ws.write_merge(3, 3, 3, 4, planificacionhorasextras.get_mes_display() + ' - ' + str(planificacionhorasextras.anio), font_style2)
                    ws.write_merge(4, 4, 0, 0, 'OBJETIVO ESTRATÉGICO INSTITUCIONAL:', font_style)
                    ws.write_merge(4, 5, 1, 4, planificacionhorasextras.actividadplanificada, font_style2)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=planificacion_horas_extra_' + random.randint(1, 10000).__str__() + '.xls'

                    columns = [
                        (u"NOMBRE DEL FUNCIONARIO", 12000),
                        (u"ACTIVIDADES A DESARROLLAR FUERA DE LA JORNADA NORMAL DE TRABAJO", 20000),
                        (u"HORAS SUP.", 6000),
                        (u"HORASEXT.", 6000),
                        (u"HORASNOCT.", 6000),
                    ]
                    row_num = 7
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 8
                    for r in detalles:
                        i = 0
                        campo1 = r.persona.nombre_completo_inverso()
                        campo2 = r.actividadplanificada
                        campo3 = r.horasuplementaria()
                        if campo3:
                            campo3 = convertir_hora(campo3)
                        campo4 = r.horaextraordinaria()
                        if campo4:
                            campo4 = convertir_hora(campo4)
                        campo5 = r.horanocturna()
                        if campo5:
                            campo5 = convertir_hora(campo5)
                        ws.write(row_num, 0, campo1, fuentenormal)
                        ws.write(row_num, 1, campo2, fuentenormal)
                        ws.write(row_num, 2, str(campo3)[0:5], style2)
                        ws.write(row_num, 3, str(campo4)[0:5], style2)
                        ws.write(row_num, 4, str(campo5)[0:5], style2)
                        row_num += 1

                    ws.write_merge(row_num+2, row_num+2, 0, 0, 'NOTAS / OBSERVACIONES:', font_style)
                    ws.write_merge(row_num+2, row_num+2, 1, 3, planificacionhorasextras.observacionplanificada, font_style2)

                    # ws.write_merge(row_num+8, row_num+8, 0, 0, 'NOMBRE DEL  SOLICITANTE', title3)
                    # ws.write_merge(row_num+8, row_num+8, 2, 3, 'FIRMA DEL DIRECTOR ÁREA', title3)
                    # ws.write_merge(row_num+14, row_num+14, 1, 1, 'VISTO BUENO RECTOR', title3)
                    ws.write_merge(row_num+8, row_num+8, 0, 0, 'FIRMA DEL DIRECTOR ÁREA', title3)
                    ws.write_merge(row_num+8, row_num+8, 3, 4, 'VISTO BUENO RECTOR', title3)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Planificación de Horas Extras'
            data['anios'] = anios = rango_anios()
            if 'anio' in request.GET:
                request.session['anioplanificacion'] = int(request.GET['anio'])
            else:
                request.session['anioplanificacion'] = anios[0]
            data['anioselect'] = anioselect = request.session['anioplanificacion']
            data['meses'] = MESES_CHOICES
            if 'mes' in request.GET:
                request.session['mesplanificacion'] = int(request.GET['mes'])
            else:
                request.session['mesplanificacion'] = 1
            data['messelect'] = messelect = request.session['mesplanificacion']
            data['planificacionhorasextras'] = PlanificacionHorasExtras.objects.filter(status=True, mes=messelect , anio=anioselect, departamento=departamento).order_by('id')
            return render(request, 'th_horas/view.html', data)
