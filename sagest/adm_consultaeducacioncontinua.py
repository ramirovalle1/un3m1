# -*- coding: latin-1 -*-
import json
import random
import sys
from decimal import Decimal
import os
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Q, F, FloatField
from django.db.models.functions import Coalesce
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from xlwt import *
from decorators import secure_module, last_access
from sagest.models import Rubro, Pago, null_to_decimal, datetime, CapPeriodoIpec, CapEventoPeriodoIpec, CapInscritoIpec, \
    TipoOtroRubro
from settings import SITE_STORAGE
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import MatriculaNovedadForm
from sga.funciones import variable_valor, generar_nombre, log, null_to_numeric
from sga.models import Inscripcion, Periodo, Carrera, Matricula, miinstitucion, MatriculaNovedad, CUENTAS_CORREOS, \
    Persona
from django.template import Context
from django.template.loader import get_template
from sga.tasks import send_html_mail, conectar_cuenta


@login_required(redirect_field_name='ret', login_url='/loginsagest')
# @secure_module
@last_access
def view(request):
    global ex
    data = {}
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'periodo_evento':
            try:
                periodo = CapPeriodoIpec.objects.get(pk=int(request.POST['id']))
                eventos = CapEventoPeriodoIpec.objects.filter(periodo=periodo).distinct().order_by('capevento__nombre')
                lista = []
                for evento in eventos:
                    if [evento.pk, evento.capevento.nombre] not in lista:
                        lista.append([evento.pk, evento.capevento.nombre])
                return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'periodo_rubros':
            try:
                eventos = TipoOtroRubro.objects.filter(tiporubro__in=[2,6], status=True).distinct().order_by('-fecha_creacion')
                lista = []
                for evento in eventos:
                    if [evento.pk, evento.nombre] not in lista:
                        lista.append([evento.pk, evento.nombre])
                return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'notificar_deuda':
            try:
                datos = json.loads(request.POST['lista'])
                if datos:
                    # matricula.participante.email
                    for elemento in datos:
                        matricula = CapInscritoIpec.objects.get(pk=int(elemento))
                        send_html_mail("Notificacion de Deudas Unemi", "emails/notificacion_deuda.html",
                                       {'sistema': u'UNIVERSIDAD ESTATAL DE MILAGRO', 'matricula': matricula,
                                        't': miinstitucion()}, [matricula.participante.email,], [], coneccion=conectar_cuenta(CUENTAS_CORREOS[4][1]))

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'segmento':
            try:
                qsrubros = None
                tipo = int(request.POST['tipo'])
                if tipo == 1:
                    data['evento'] = evento = CapEventoPeriodoIpec.objects.get(pk=int(request.POST['evento']))
                    if evento.tiporubro:
                        data['tiposrubros'] = tiposrubros = TipoOtroRubro.objects.get(pk=evento.tiporubro.pk)
                        qsrubros = Rubro.objects.filter(capeventoperiodoipec=evento, tipo=tiposrubros, status=True, cancelado=False, fechavence__lt=datetime.now().date()).order_by('tipo', 'persona')
                    else:
                        qsrubros = Rubro.objects.filter(capeventoperiodoipec=evento, status=True, cancelado=False, fechavence__lt=datetime.now().date()).order_by('tipo', 'persona')
                elif tipo == 2:
                    data['tiposrubros'] = tiposrubros = TipoOtroRubro.objects.get(pk=int(request.POST['evento']))
                    qsrubros = Rubro.objects.filter(capeventoperiodoipec__isnull=True, tipo=tiposrubros, status=True, cancelado=False, fechavence__lt=datetime.now().date()).order_by('tipo', 'persona')
                elif tipo == 3:
                    qsrubros = Rubro.objects.filter(capeventoperiodoipec__isnull=True, tipo__tiporubro__in=[2,6], status=True, cancelado=False, fechavence__lt=datetime.now().date()).order_by('tipo', 'persona')
                rubroslist = qsrubros.values_list('pk', flat=True)
                data['totalrubros'] = totalrubro = valor = null_to_decimal(qsrubros.aggregate(valor=Sum('valortotal'))['valor'], 2)
                data['totalvencido'] = totalvencido = null_to_numeric(qsrubros.aggregate(valort=Sum('valortotal'))['valort'])
                data['totalpagado'] = totalpagado = null_to_numeric(Pago.objects.filter(rubro__in=rubroslist, status=True).aggregate(valort=Sum('valortotal'))['valort'])
                data['totalsaldo'] = totalsaldo = null_to_decimal(qsrubros.aggregate(valor=Sum('saldo'))['valor'], 2)
                data['listado'] = qsrubros
                data['listadocount'] = qsrubros.count()
                template = get_template("adm_consultaeducacioncontinua/segmento.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                print(ex)
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data = {}
        adduserdata(request, data)
        data['title'] = u'Consulta Cartera Educación Continua'
        if 'action' in request.GET:

            action = request.GET['action']

            if action == 'verdetallemeses':
                try:
                    data['estudiante'] = persona = Persona.objects.get(pk=request.GET['id'])
                    data['tiporubro'] = TipoOtroRubro.objects.get(pk=int(request.GET['tiporubro']))
                    data['rubros'] = rubros = Rubro.objects.filter(persona=persona, status=True, tipo=int(request.GET['tiporubro'])).distinct().order_by('pk')
                    data['count'] = rubros.count()
                    totalpagado = 0
                    for r in rubros:
                        totalpagado += r.total_pagado()
                    data['totalpagadototal'] = totalpagado
                    data['valortotal'] = rubros.aggregate(total=Coalesce(Sum(F('valor'), output_field=FloatField()), 0)).get('total')
                    data['valortotaltotal'] = rubros.aggregate(total=Coalesce(Sum(F('valortotal'), output_field=FloatField()), 0)).get('total')
                    data['saldototal'] = rubros.aggregate(total=Coalesce(Sum(F('saldo'), output_field=FloatField()), 0)).get('total')
                    template = get_template("adm_consultaeducacioncontinua/detallemesesdeuda.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'carteravencidageneral':
                try:
                    fechaactual = datetime.now().date()
                    __author__ = 'UNIVERSIDAD ESTATAL DE MILAGRO'
                    title = easyxf('font: name Calibri, color-index black, bold on , height 350; alignment: horiz centre')
                    fuentecabecera = easyxf('font: name Calibri, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentetexto = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    borders = Borders()
                    borders.left = Borders.THIN
                    borders.right = Borders.THIN
                    borders.top = Borders.THIN
                    borders.bottom = Borders.THIN
                    align = Alignment()
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style.borders = borders
                    font_style.alignment = align
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    font_style2.borders = borders
                    font_style2.alignment = align
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('CARTERA VENCIDA GENERAL')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=cartera_vencida_general_' + random.randint(1,10000).__str__() + '.xls'
                    ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 6, 'CARTERA VENCIDA GENERAL {}'.format(str(datetime.now().date())), fuentenormal)
                    columns = [
                        (u"TIPO RUBRO", 15000),
                        (u"TOTAL PERSONAS", 6000),
                        (u"TOTAL PAGADO", 6000),
                        (u"TOTAL VENCIDO", 6000),
                    ]
                    row_num = 4
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 5
                    saldovencido_total = 0
                    saldo_total = 0
                    valor_total = 0
                    valor_pagado_total = 0
                    count = 1
                    tipos = TipoOtroRubro.objects.filter(tiporubro__in=[2,6], status=True).distinct().order_by('-fecha_creacion')
                    for i in tipos:
                        qsrubros = Rubro.objects.filter(tipo=i, status=True, cancelado=False, fechavence__lt=datetime.now().date()).order_by('tipo', 'persona')
                        rubroslist = qsrubros.values_list('pk', flat=True)
                        totalrubro = valor = null_to_decimal(qsrubros.aggregate(valor=Sum('valortotal'))['valor'], 2)
                        # totalvencido = null_to_numeric(qsrubros.aggregate(valort=Sum('valortotal'))['valort'])
                        totalpagado = null_to_numeric(Pago.objects.filter(rubro__in=rubroslist, status=True).aggregate(valort=Sum('valortotal'))['valort'])
                        totalvencido = null_to_decimal(float(totalrubro)-float(totalpagado), 2)
                        totalsaldo = null_to_decimal(qsrubros.aggregate(valor=Sum('saldo'))['valor'], 2)
                        totalpersonas = qsrubros.count()
                        ws.write_merge(row_num, row_num, 0, 0, i.nombre, font_style2)
                        ws.write_merge(row_num, row_num, 1, 1, totalpersonas, font_style2)
                        ws.write_merge(row_num, row_num, 2, 2, totalpagado, font_style2)
                        ws.write_merge(row_num, row_num, 3, 3, totalvencido, font_style2)
                        row_num += 1
                        count += 1
                        saldo_total += totalpersonas
                        valor_pagado_total += totalpagado
                        saldovencido_total += totalvencido
                    ws.write_merge(row_num, row_num, 0, 0, u'TOTAL DE EJECUCIÓN', font_style)
                    ws.write_merge(row_num, row_num, 1, 1, Decimal(saldo_total), font_style2)
                    ws.write_merge(row_num, row_num, 2, 2, Decimal(valor_pagado_total), font_style2)
                    ws.write_merge(row_num, row_num, 3, 3, Decimal(saldovencido_total), font_style2)
                    wb.save(response)
                    return response
                except Exception as ex:
                    print(ex)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            if action == 'carteraporrubro':
                try:
                    fechaactual = datetime.now().date()
                    __author__ = 'UNIVERSIDAD ESTATAL DE MILAGRO'
                    title = easyxf('font: name Calibri, color-index black, bold on , height 350; alignment: horiz centre')
                    fuentecabecera = easyxf('font: name Calibri, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentetexto = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    borders = Borders()
                    borders.left = Borders.THIN
                    borders.right = Borders.THIN
                    borders.top = Borders.THIN
                    borders.bottom = Borders.THIN
                    align = Alignment()
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style.borders = borders
                    font_style.alignment = align
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    font_style2.borders = borders
                    font_style2.alignment = align
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('CARTERA VENCIDA POR RUBROS')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=cartera_vencida_por_rubros' + random.randint(1,10000).__str__() + '.xls'
                    ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 9, 'TODOS LOS RUBROS', title)
                    ws.write_merge(2, 2, 0, 9, 'CARTERA VENCIDA POR RUBROS {}'.format(str(datetime.now().date())), fuentenormal)
                    columns = [
                        (u"CODIGO", 3000),
                        (u"FECHA CREACIÓN", 6000),
                        (u"CURSO", 15000),
                        (u"DOCUMENTO", 6000),
                        (u"PERSONA", 12000),
                        (u"FECHA VENCIMIENTO", 6000),
                        (u"REGISTRADO POR", 6000),
                        (u"VALOR TOTAL", 6000),
                        (u"PAGADO", 6000),
                        (u"PENDIENTE", 6000),
                    ]
                    row_num = 4
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 5
                    saldovencido_total = 0
                    saldo_total = 0
                    valor_total = 0
                    valor_pagado_total = 0
                    count = 1
                    tipos = TipoOtroRubro.objects.filter(tiporubro__in=[2, 6], status=True).distinct().order_by('-fecha_creacion')
                    for i in tipos:
                        if Rubro.objects.filter(tipo=i, status=True, cancelado=False, fechavence__lt=datetime.now().date()).exists():
                            qsrubros = Rubro.objects.filter(tipo=i, status=True, cancelado=False, fechavence__lt=datetime.now().date()).order_by('tipo', 'persona')
                            for i in qsrubros:
                                ws.write_merge(row_num, row_num, 0, 0, i.pk, font_style2)
                                ws.write_merge(row_num, row_num, 1, 1, str(i.fecha), font_style2)
                                ws.write_merge(row_num, row_num, 2, 2, i.nombre, font_style2)
                                ws.write_merge(row_num, row_num, 3, 3, i.persona.cedula, font_style2)
                                ws.write_merge(row_num, row_num, 4, 4, i.persona.__str__(), font_style2)
                                ws.write_merge(row_num, row_num, 5, 5, str(i.fechavence), font_style2)
                                ws.write_merge(row_num, row_num, 6, 6, i.usuario_creacion.username, font_style2)
                                ws.write_merge(row_num, row_num, 7, 7, i.valortotal, font_style2)
                                ws.write_merge(row_num, row_num, 8, 8, i.total_pagado(), font_style2)
                                ws.write_merge(row_num, row_num, 9, 9, i.total_adeudado(), font_style2)
                                row_num += 1
                                count += 1
                                valor_total += i.valortotal
                                valor_pagado_total += i.total_pagado()
                                saldo_total += i.total_adeudado()
                    ws.write_merge(row_num, row_num, 0, 6, u'TOTAL DE EJECUCIÓN', font_style)
                    ws.write_merge(row_num, row_num, 7, 7, Decimal(valor_total), font_style2)
                    ws.write_merge(row_num, row_num, 8, 8, Decimal(valor_pagado_total), font_style2)
                    ws.write_merge(row_num, row_num, 9, 9, Decimal(saldo_total), font_style2)
                    wb.save(response)
                    return response
                except Exception as ex:
                    print(ex)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            if action == 'carteravencidadetallado':
                try:
                    fechaactual = datetime.now().date()
                    nombre = request.GET['nombre']
                    id = request.GET.get("id", '')
                    tipo = request.GET['tipo']
                    tiporubro = None
                    if tipo == '1':
                        evento = CapEventoPeriodoIpec.objects.get(id=id)
                        tiporubro = TipoOtroRubro.objects.get(pk=evento.tiporubro.pk)
                        qsrubros = Rubro.objects.filter(capeventoperiodoipec=evento, tipo=tiporubro, status=True, cancelado=False, fechavence__lt=datetime.now().date()).order_by('tipo', 'persona')

                    elif tipo == '2':
                        if id != '0':
                            tiporubro = TipoOtroRubro.objects.get(pk=id)
                            qsrubros = Rubro.objects.filter(capeventoperiodoipec__isnull=True, tipo=tiporubro, status=True, cancelado=False, fechavence__lt=datetime.now().date()).order_by('tipo', 'persona')
                        else:
                            tiposrubros = TipoOtroRubro.objects.filter(tiporubro__in=[2,6]).values_list('id',flat=True)
                            qsrubros = Rubro.objects.filter(capeventoperiodoipec__isnull=True, tipo__in=tiposrubros, status=True, cancelado=False,
                                                            fechavence__lt=datetime.now().date()).order_by('tipo', 'persona')
                    __author__ = 'UNIVERSIDAD ESTATAL DE MILAGRO'
                    title = easyxf('font: name Calibri, color-index black, bold on , height 350; alignment: horiz centre')
                    fuentecabecera = easyxf('font: name Calibri, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentetexto = easyxf('font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    borders = Borders()
                    borders.left = Borders.THIN
                    borders.right = Borders.THIN
                    borders.top = Borders.THIN
                    borders.bottom = Borders.THIN
                    align = Alignment()
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style.borders = borders
                    font_style.alignment = align
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    font_style2.borders = borders
                    font_style2.alignment = align
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('CARTERA VENCIDA')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=cartera_vencida_'+str(nombre) + random.randint(1,10000).__str__() + '.xls'
                    ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    if id != '0':
                        ws.write_merge(1, 1, 0, 9, tiporubro.nombre, title)
                    else:
                        ws.write_merge(1, 1, 0, 9, 'TODOS LOS RUBROS', title)
                    ws.write_merge(2, 2, 0, 9, 'CARTERA VENCIDA {} {}'.format(str(nombre).upper(), str(datetime.now().date())), fuentenormal)
                    columns = [
                        (u"CODIGO", 3000),
                        (u"FECHA CREACIÓN", 6000),
                        (u"CURSO", 4000),
                        (u"DOCUMENTO", 6000),
                        (u"PERSONA", 8000),
                        (u"FECHA VENCIMIENTO", 6000),
                        (u"REGISTRADO POR", 6000),
                        (u"VALOR TOTAL", 6000),
                        (u"PAGADO", 6000),
                        (u"PENDIENTE", 6000),
                    ]
                    row_num = 4
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 5
                    saldovencido_total = 0
                    saldo_total = 0
                    valor_total = 0
                    valor_pagado_total = 0
                    count = 1
                    for i in qsrubros:
                        ws.write_merge(row_num, row_num, 0, 0, i.pk, font_style2)
                        ws.write_merge(row_num, row_num, 1, 1, str(i.fecha), font_style2)
                        ws.write_merge(row_num, row_num, 2, 2, i.nombre, font_style2)
                        ws.write_merge(row_num, row_num, 3, 3, i.persona.cedula, font_style2)
                        ws.write_merge(row_num, row_num, 4, 4, i.persona.__str__(), font_style2)
                        ws.write_merge(row_num, row_num, 5, 5, str(i.fechavence), font_style2)
                        ws.write_merge(row_num, row_num, 6, 6, i.usuario_creacion.username, font_style2)
                        ws.write_merge(row_num, row_num, 7, 7, i.valortotal, font_style2)
                        ws.write_merge(row_num, row_num, 8, 8, i.total_pagado(), font_style2)
                        ws.write_merge(row_num, row_num, 9, 9, i.total_adeudado(), font_style2)
                        row_num += 1
                        count += 1
                        valor_total += i.valortotal
                        valor_pagado_total += i.total_pagado()
                        saldo_total += i.total_adeudado()
                    ws.write_merge(row_num, row_num, 0, 6, u'TOTAL DE EJECUCIÓN', font_style)
                    ws.write_merge(row_num, row_num, 7, 7, Decimal(valor_total), font_style2)
                    ws.write_merge(row_num, row_num, 8, 8, Decimal(valor_pagado_total), font_style2)
                    ws.write_merge(row_num, row_num, 9, 9, Decimal(saldo_total), font_style2)
                    wb.save(response)
                    return response
                except Exception as ex:
                    print(ex)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            if action == 'buscartiporubro':
                try:
                    q = request.GET['q'].upper().strip()
                    qset = TipoOtroRubro.objects.filter(tiporubro__in=[2,6], status=True).filter(Q(nombre__icontains=q)).order_by('nombre').distinct()[:15]
                    data = {"result": "ok",
                            "results": [{"id": x.id, "name": "{}".format(x.nombre)} for x in qset]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['periodos'] = CapPeriodoIpec.objects.filter(status=True).order_by('-fechainicio')
            data['tiporubros'] = tiprubro = TipoOtroRubro.objects.filter(tiporubro__in=[2,6], status=True).distinct().order_by('-fecha_creacion')
            if 'id' in request.GET:
                data['id'] = request.GET['id']
            data['anio'] = datetime.now().year
            return render(request, "adm_consultaeducacioncontinua/view.html", data)