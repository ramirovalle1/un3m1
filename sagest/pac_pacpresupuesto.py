# -*- coding: UTF-8 -*-
import json
import random

import xlrd
import xlwt

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import RequestContext
from xlwt import *

from decorators import secure_module
from settings import ARCHIVO_TIPO_GENERAL
from sga.forms import ImportarArchivoXLSForm
from sagest.models import PeriodoPac, Pac, datetime, PartidaPrograma, PartidaActividad, PartidaFuente
from sga.commonviews import adduserdata
from sga.funciones import generar_nombre, log
from sga.models import Archivo


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    departamento = persona.mi_departamento()
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'importar':
            mensaje = None
            try:
                form = ImportarArchivoXLSForm(request.POST, request.FILES)
                if form.is_valid():
                    pac=None

                    hoy = datetime.now().date()
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("subirpac_", nfile._name)
                    archivo = Archivo(nombre='SUBIR PAC MODIFICACION PRESUPUESTO',
                                      fecha=datetime.now().date(),
                                      archivo=nfile,
                                      tipo_id=ARCHIVO_TIPO_GENERAL)
                    archivo.save(request)
                    workbook = xlrd.open_workbook(archivo.archivo.file.name)
                    sheet = workbook.sheet_by_index(0)
                    linea = 1
                    for rowx in range(sheet.nrows):
                        if linea >= 5:
                            cols = sheet.row_values(rowx)
                            # PAC
                            partidaprograma = None
                            if int(cols[3]) != 0:
                                partidaprograma = PartidaPrograma.objects.filter(codigo__contains=int(cols[3]), status=True)[0]

                            partidaactividad = None
                            if int(cols[4]) != 0:
                                partidaactividad = PartidaActividad.objects.filter(codigo__contains=int(cols[4]), status=True)[0]

                            partidafuente = None
                            if int(cols[5]) != 0:
                                partidafuente = PartidaFuente.objects.filter(codigo__contains=int(cols[5]), status=True)[0]

                            estadoitem = 2
                            if cols[7].strip().upper() == 'PAC':
                                estadoitem = 1

                            pac = Pac.objects.get(pk=int(cols[0]), status=True)
                            pac.programa = partidaprograma
                            pac.actividad = partidaactividad
                            pac.fuente = partidafuente
                            pac.estadoitem = estadoitem
                            pac.save(request)
                        linea += 1

                    if pac:
                        log(u'Importo plantilla personal: %s' % pac , request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        mensaje = "No contiene modificacion de presupuesto"
                        raise NameError('No contiene modificacion de presupuesto')
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos." if not mensaje else mensaje})

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'importar':
                try:
                    data['title'] = u'Subir Modificaciones Presupuestaria PAC'
                    data['idperiodo'] = int(request.GET['idperiodo'])
                    data['form'] = ImportarArchivoXLSForm()
                    return render(request, "pac_pacpresupuesto/importar.html", data)
                except Exception as ex:
                    pass

            if action == 'descargar':
                try:
                    periodo = request.GET['periodo']

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
                    ws.write_merge(0, 0, 0, 12, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=pac_' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"CODIGO", 0),
                        (u"DEPARTAMENTO", 6000),
                        (u"ACTIVIDAD/PROYECTO", 6000),
                        (u"PROGRAMA", 6000),
                        (u"ACTIVIDAD", 6000),
                        (u"FUENTE", 6000),
                        (u"ITEM", 6000),
                        (u"ESTADO ITEM", 6000),
                        (u"CARACTERISTICA", 6000),
                        (u"CANTIDAD", 6000),
                        (u"UNIDAD", 6000),
                        (u"COSTO UNITARIO", 6000),
                        (u"TOTAL", 6000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    pacs = Pac.objects.filter(periodo_id=periodo, status=True)
                    row_num = 4
                    for r in pacs:
                        i = 0
                        campo1 = r.id
                        campo2 = r.departamento.nombre
                        # campo3 = r.acciondocumento.descripcion
                        campo3 = ''
                        campo4 = ''
                        if r.programa:
                            campo4 = r.programa.codigo
                        campo5 = ''
                        if r.actividad:
                            campo5 = r.actividad.codigo
                        campo6 = ''
                        if r.fuente:
                            campo6 = r.fuente.codigo
                        campo7 = ''
                        if r.item:
                            campo7 = r.item.codigo
                        campo8 = ''
                        if r.estadoitem:
                            campo8 = r.estado_letra()
                        campo9 = r.caracteristicas.descripcion
                        campo10 = r.cantidad
                        campo11 = r.unidadmedida.nombre
                        campo12 = r.costounitario
                        campo13 = r.total
                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, campo7, font_style2)
                        ws.write(row_num, 7, campo8, font_style2)
                        ws.write(row_num, 8, campo9, font_style2)
                        ws.write(row_num, 9, campo10, font_style2)
                        ws.write(row_num, 10, campo11, font_style2)
                        ws.write(row_num, 11, campo12, font_style2)
                        ws.write(row_num, 12, campo13, font_style2)
                        # while i < len(r):
                        #     # ws.write(row_num, i, r[i], font_style)
                        #     # ws.col(i).width = columns[i][1]
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'PAC UNEMI'
            search = None
            data['periodos'] = periodos = PeriodoPac.objects.filter(status=True).order_by('-id')
            if 'periodo' in request.GET:
                search = request.GET['periodo']
                idperiodo = int(request.GET['periodo'])
            if search:
                data['pacs'] = Pac.objects.filter(periodo_id=search, status=True)
            else:
                periodo = periodos[0]
                idperiodo = periodo.id
                data['pacs'] = Pac.objects.filter(periodo=periodo, status=True)
            data['periodo'] = PeriodoPac.objects.filter(pk=idperiodo,status=True)[0]
            data['idperiodo'] = idperiodo
            return render(request, 'pac_pacpresupuesto/view.html', data)