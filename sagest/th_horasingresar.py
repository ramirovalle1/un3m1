# -*- coding: UTF-8 -*-
import random
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from xlwt import *
from decorators import secure_module
from sagest.models import PlanificacionHorasExtras, PlanificacionHorasExtrasPersona
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
    departamento = persona.mi_departamento()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'observacion':
            try:
                planificacionhorasextraspersona = PlanificacionHorasExtrasPersona.objects.get(pk=request.POST['id'])
                planificacionhorasextraspersona.actividadrealizada = request.POST['valor']
                planificacionhorasextraspersona.save(request)
                log(u'Ingreso actividad horas extra: %s' % planificacionhorasextraspersona, request, "edit")
                return JsonResponse({"result": "ok"})
            except:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'detalle_planificacion':
                try:
                    data['planificacionhorasextras'] = planificacionhorasextras = PlanificacionHorasExtras.objects.get(pk=request.GET['cid'])
                    data['planificacionhorasextraspersonas'] = planificacionhorasextras.planificacionhorasextraspersona_set.filter(status=True)
                    return render(request, 'th_horas/detalle_planificacion.html', data)
                except Exception as ex:
                    pass

            if action == 'exportarplanificacion':
                try:
                    idanio = int(request.GET['idanio'])
                    idmes = int(request.GET['idmes'])

                    planificacionhorasextraspersonas = PlanificacionHorasExtrasPersona.objects.filter(status=True, planificacion__mes=idmes, planificacion__anio=idanio, planificacion__departamento=departamento, persona=persona, planificacion__aprobado=True).order_by('-fecha')
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
                    fuentenormal = easyxf('font: name Times New Roman, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    title3 = easyxf('font: name Times New Roman, color-index black, bold on , height 200; alignment: horiz centre; borders: top thin')
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 8, 'UNIDAD DE ADMINISTRACIÓN DE TALENTO HUMANO', title2)
                    ws.write_merge(2, 2, 0, 8, 'REGISTRO PARA PAGO HORAS SUPLEMENTARIAS Y EXTRAORDINARIAS', title2)

                    ws.write_merge(3, 3, 0, 0, 'APELLIDOS Y NOMBRES:', font_style)
                    ws.write_merge(3, 3, 1, 8, persona.nombre_completo_inverso(), font_style2)

                    ws.write_merge(4, 4, 0, 0, 'DIRECCIÓN / UNIDAD:', font_style)
                    ws.write_merge(4, 4, 1, 8, departamento.nombre, font_style2)

                    ws.write_merge(5, 5, 0, 0, 'CARGO / DENOMINACIÓN:', font_style)
                    ws.write_merge(5, 5, 1, 8, persona.mi_cargo_administrativo().descripcion, font_style2)

                    ws.write_merge(6, 6, 0, 0, 'HORARIO REGULAR:', font_style)
                    ws.write_merge(6, 6, 1, 8, persona.jornada_fecha(fecha).jornada.nombre, font_style2)

                    ws.write_merge(7, 7, 0, 0, 'AÑO:', font_style)
                    ws.write_merge(7, 7, 1, 3, str(idanio), font_style2)

                    ws.write_merge(7, 7, 4, 4, 'MES:', font_style)
                    ws.write_merge(7, 7, 5, 8, planificacionhorasextraspersonas[0].planificacion.get_mes_display(), font_style2)

                    ws.write_merge(9, 10, 0, 0, 'FECHA (DIA/MES/AÑO)', fuentecabecera)

                    ws.write_merge(9, 9, 1, 2, 'HORARIO PLANIFICADO', fuentecabecera)
                    ws.write_merge(10, 10, 1, 1, 'DESDE', fuentecabecera)
                    ws.write_merge(10, 10, 2, 2, 'HASTA', fuentecabecera)

                    ws.write_merge(9, 9, 3, 4, 'HORARIO SUPLEMENTARIO O EXTRAORDINARIO (Horas)', fuentecabecera)
                    ws.write_merge(10, 10, 3, 3, 'DESDE', fuentecabecera)
                    ws.write_merge(10, 10, 4, 4, 'HASTA', fuentecabecera)

                    ws.write_merge(9, 10, 5, 5, 'SUPLEMENTARIAS', fuentecabecera)
                    ws.write_merge(9, 10, 6, 6, 'EXTRAORDINARIAS', fuentecabecera)
                    ws.write_merge(9, 10, 7, 7, 'NOCTURNAS', fuentecabecera)
                    ws.write_merge(9, 10, 8, 8, 'ACTIVIDAD REALIZADA', fuentecabecera)

                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=planificacion_horas_extra_' + random.randint(1, 10000).__str__() + '.xls'

                    columns = [
                        (u"", 6500),
                        (u"", 3000),
                        (u"", 3000),
                        (u"", 5500),
                        (u"", 5500),
                        (u"", 4500),
                        (u"", 4500),
                        (u"", 4500),
                        (u"", 15000),
                    ]
                    row_num = 8
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style2)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 11
                    for r in planificacionhorasextraspersonas:
                        campo1 = r.fecha
                        campo2 = r.horadesde
                        campo3 = r.horahasta
                        campo4 = ""
                        campo5 = ""

                        if r.marcadas():
                            campo4 = r.marcadas().entrada.time()
                            campo5 = r.marcadas().salida.time()
                        campo6 = r.horasuplementaria_horas(campo2,campo3,campo4,campo5)
                        if campo6 != '':
                            campo6 = convertir_hora(campo6)

                        campo7 = r.horaextraordinaria_horas(campo2,campo3,campo4,campo5)
                        if campo7 != '':
                            campo7 = convertir_hora(campo7)

                        campo8 = r.horanocturna_horas(campo2,campo3,campo4,campo5)
                        if campo8 != '':
                            campo8 = convertir_hora(campo8)

                        campo9 = r.actividadrealizada

                        ws.write(row_num, 0, str(campo1), style2)
                        ws.write(row_num, 1, str(campo2)[0:5], style2)
                        ws.write(row_num, 2, str(campo3)[0:5], style2)
                        ws.write(row_num, 3, str(campo4)[0:5], style2)
                        ws.write(row_num, 4, str(campo5)[0:5], style2)
                        ws.write(row_num, 5, str(campo6)[0:5], style2)
                        ws.write(row_num, 6, str(campo7)[0:5], style2)
                        ws.write(row_num, 7, str(campo8)[0:5], style2)
                        ws.write(row_num, 8, campo9, fuentenormal)

                        row_num += 1
                    ws.write_merge(row_num+8, row_num+8, 1, 2, 'FUNCIONARIO', title3)
                    ws.write_merge(row_num+8, row_num+8, 5, 6, 'REVISADO POR JEFE INMEDIATO', title3)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Ingresar Actividad Horas Extra'
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
            data['planificacionhorasextraspersonas'] = PlanificacionHorasExtrasPersona.objects.filter(status=True, planificacion__mes=messelect , planificacion__anio=anioselect, planificacion__departamento=departamento, persona=persona).order_by('fecha')
            return render(request, 'th_horasingresar/view.html', data)
