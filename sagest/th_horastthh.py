# -*- coding: UTF-8 -*-
from datetime import datetime, timedelta
import random
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from xlwt import *
from decorators import secure_module
from sagest.forms import PlanificacionHorasExtrasVerificarForm, PlanificacionHorasExtrasAprobacionForm
from sagest.models import PlanificacionHorasExtras, Departamento, PlanificacionHorasExtrasPersona
from sga.commonviews import adduserdata
from sga.funciones import log, convertir_hora
from sga.models import MESES_CHOICES


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
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'verificarplanificacion':
            try:

                form = PlanificacionHorasExtrasVerificarForm(request.POST)
                if form.is_valid():
                    planificacionhorasextras = PlanificacionHorasExtras.objects.filter(pk=request.POST['id'])[0]
                    planificacionhorasextras.observaciontthh = form.cleaned_data['observaciontthh']
                    planificacionhorasextras.verificadotthh = form.cleaned_data['verificar']
                    planificacionhorasextras.personaverificado = persona
                    planificacionhorasextras.save(request)
                    log(u'Verifico planificación horas extra: %s' % planificacionhorasextras, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al modificar los datos."})

        if action == 'aprobacionplanificacion':
            try:

                form = PlanificacionHorasExtrasAprobacionForm(request.POST)
                if form.is_valid():
                    planificacionhorasextras = PlanificacionHorasExtras.objects.filter(pk=request.POST['id'])[0]
                    planificacionhorasextras.observacionaprobado=form.cleaned_data['observacionaprobado']
                    planificacionhorasextras.aprobado=form.cleaned_data['aprobar']
                    planificacionhorasextras.personaaprobado = persona
                    planificacionhorasextras.save(request)
                    log(u'Aprobo planificación horas extra: %s' % planificacionhorasextras, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al modificar los datos."})

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'verificarplanificacion':
                try:
                    data['title'] = u'Verificar Planificación Horas Extra'
                    planificacionhorasextras = PlanificacionHorasExtras.objects.filter(pk=request.GET['id'])[0]
                    form = PlanificacionHorasExtrasVerificarForm(initial={'anio': planificacionhorasextras.anio,
                                                                          'mes': planificacionhorasextras.mes,
                                                                          'actividad': planificacionhorasextras.actividadplanificada,
                                                                          'observaciontthh': planificacionhorasextras.observaciontthh,
                                                                          'verificar': planificacionhorasextras.verificadotthh})
                    form.verificacion()
                    data['form'] = form
                    data['planificacionhorasextraspersonas'] = planificacionhorasextras.planificacionhorasextraspersona_set.filter(status=True)
                    data['planificacionhorasextras'] = planificacionhorasextras
                    return render(request, "th_horastthh/verificarplanificacion.html", data)
                except Exception as ex:
                    pass

            if action == 'aprobacionplanificacion':
                try:
                    data['title'] = u'Aprobación Planificación Horas Extra'
                    planificacionhorasextras = PlanificacionHorasExtras.objects.filter(pk=request.GET['id'])[0]
                    form = PlanificacionHorasExtrasAprobacionForm(initial={'anio': planificacionhorasextras.anio,
                                                                          'mes': planificacionhorasextras.mes,
                                                                          'actividad': planificacionhorasextras.actividadplanificada,
                                                                          'observacionaprobado': planificacionhorasextras.observacionaprobado,
                                                                          'aprobar': planificacionhorasextras.aprobado})
                    form.aprobacion()
                    data['form'] = form
                    data['planificacionhorasextraspersonas'] = planificacionhorasextras.planificacionhorasextraspersona_set.filter(status=True)
                    data['planificacionhorasextras'] = planificacionhorasextras
                    return render(request, "th_horastthh/aprobacionplanificacion.html", data)
                except Exception as ex:
                    pass

            if action == 'detalle_planificacion':
                try:
                    data['planificacionhorasextras'] = planificacionhorasextras = PlanificacionHorasExtras.objects.get(pk=request.GET['cid'])
                    data['planificacionhorasextraspersonas'] = planificacionhorasextras.planificacionhorasextraspersona_set.filter(status=True)
                    return render(request, 'th_horastthh/detalle_planificacion.html', data)
                except Exception as ex:
                    pass


            if action == 'exportarplanificacion':
                try:
                    idanio = int(request.GET['idanio'])
                    idmes = int(request.GET['idmes'])

                    planificacionhorasextraspersonas = PlanificacionHorasExtrasPersona.objects.filter(status=True, planificacion__mes=idmes, planificacion__anio=idanio, planificacion__aprobado=True).order_by('-fecha')
                    fecha = planificacionhorasextraspersonas[0].fecha
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    title2 = easyxf('font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    style1 = easyxf(num_format_str='DD/mm/YYYY')
                    # style2 = easyxf(num_format_str='HH:mm')
                    style2 = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    fuentecabecera = easyxf('font: name Times New Roman, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Times New Roman, color-index black, height 150; align: wrap on, horiz center; borders: left thin, right thin, top thin, bottom thin')
                    title3 = easyxf('font: name Times New Roman, color-index black, bold on , height 200; alignment: horiz centre; borders: top thin')
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 9, 'UNIDAD DE ADMINISTRACIÓN DE TALENTO HUMANO', title2)
                    ws.write_merge(2, 2, 0, 9, 'RESUMEN DE HORAS EXTRAS, SUPLEMENTARIAS Y NOCTURNAS', title2)

                    ws.write_merge(3, 3, 0, 0, 'AÑO:', font_style)
                    ws.write_merge(3, 3, 1, 3, str(idanio), font_style2)
                    ws.write_merge(3, 3, 4, 4, 'MES:', font_style)
                    ws.write_merge(3, 3, 5, 7, planificacionhorasextraspersonas[0].planificacion.get_mes_display(), font_style2)

                    ws.write_merge(5, 5, 0, 0, 'NOMBRE SERVIDOR', fuentecabecera)
                    ws.write_merge(5, 5, 1, 1, 'NRO. CÉDULA', fuentecabecera)
                    ws.write_merge(5, 5, 2, 2, 'UNIDAD ADMINISTRATIVA', fuentecabecera)
                    ws.write_merge(5, 5, 3, 3, 'HORAS PLANIFICADAS', fuentecabecera)
                    ws.write_merge(5, 5, 4, 4, 'HORAS LABORADAS BIOMÉTRICO', fuentecabecera)
                    ws.write_merge(5, 5, 5, 5, 'TOTAL HORAS SUPL.', fuentecabecera)
                    ws.write_merge(5, 5, 6, 6, 'TOTAL HORAS EXTRAS', fuentecabecera)
                    ws.write_merge(5, 5, 7, 7, 'TOTAL HORAS REC.', fuentecabecera)
                    ws.write_merge(5, 5, 8, 8, 'MODALIDAD', fuentecabecera)
                    ws.write_merge(5, 5, 9, 9, 'OBSERVACIONES', fuentecabecera)

                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=planificacion_horas_extra_' + random.randint(1, 10000).__str__() + '.xls'

                    columns = [
                        (u"", 6500),
                        (u"", 3000),
                        (u"", 10000),
                        (u"", 11000),
                        (u"", 6000),
                        (u"", 6000),
                        (u"", 4500),
                        (u"", 4500),
                        (u"", 4500),
                        (u"", 15000),
                    ]
                    row_num = 4
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style2)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 6
                    for r in planificacionhorasextraspersonas:
                        campo1 = r.persona.nombre_completo_inverso()
                        campo2 = r.persona.cedula
                        campo3 = r.persona.mi_departamento().nombre
                        campo4 = ""
                        campo5 = ""
                        campo6 = ""
                        campo7 = ""
                        if r.marcadas():
                            campo4 = str(r.marcadas().entrada.time())[0:5] + " - " + str(r.marcadas().salida.time())[0:5]
                            campo5 = r.horasuplementaria_horas(r.horadesde, r.horahasta, r.marcadas().entrada.time(), r.marcadas().salida.time())
                            if campo5:
                                campo5 = convertir_hora(campo5)

                            campo6 = r.horaextraordinaria_horas(r.horadesde, r.horahasta, r.marcadas().entrada.time(), r.marcadas().salida.time())
                            if campo6:
                                campo6 = convertir_hora(campo6)

                            campo7 = r.horanocturna_horas(r.horadesde, r.horahasta, r.marcadas().entrada.time(), r.marcadas().salida.time())
                            if campo7:
                                campo7 = convertir_hora(campo7)

                        campo8 = r.modalidadlaboral.descripcion
                        campo9 = ""

                        campo10 = str(r.horadesde)[0:5] + " - " + str(r.horahasta)[0:5]

                        ws.write(row_num, 0, campo1, fuentenormal)
                        ws.write(row_num, 1, campo2, fuentenormal)
                        ws.write(row_num, 2, campo3, fuentenormal)
                        ws.write(row_num, 3, campo4, fuentenormal)
                        ws.write(row_num, 4, campo10, fuentenormal)
                        ws.write(row_num, 5, str(campo5)[0:5], fuentenormal)
                        ws.write(row_num, 6, str(campo6)[0:5], fuentenormal)
                        ws.write(row_num, 7, str(campo7)[0:5], fuentenormal)
                        ws.write(row_num, 8, campo8, fuentenormal)
                        ws.write(row_num, 9, campo9, fuentenormal)

                        row_num += 1
                    ws.write_merge(row_num+4, row_num+4, 0, 1, 'Elaborado por:', title3)
                    ws.write_merge(row_num+4, row_num+4, 3, 4, 'Revisado por:', title3)
                    ws.write_merge(row_num+4, row_num+4, 6, 7, 'Aprobado por:', title3)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Verificación Planificación de Horas Extras'
            data['departamentos'] = departamentos = Departamento.objects.filter(planificacionhorasextras__departamento__isnull=False).distinct()
            if 'iddepartamento' in request.GET:
                iddepartamentos = int(request.GET['iddepartamento'])
            else:
                iddepartamentos = 0
                if departamentos:
                    iddepartamentos = departamentos[0].id
            data['departamentoselect'] = departamentoselect = iddepartamentos

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

            data['planificacionhorasextras'] = PlanificacionHorasExtras.objects.filter(status=True, mes=messelect , anio=anioselect, departamento__id=departamentoselect).order_by('-id')
            return render(request, 'th_horastthh/view.html', data)
