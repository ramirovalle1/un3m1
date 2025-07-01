# -*- coding: UTF-8 -*-
import io
import sys
from datetime import datetime, timedelta
from urllib.request import urlopen

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.http.response import HttpResponse
from django.shortcuts import render
import xlrd
import xlsxwriter
import random
from xlwt import *
from decorators import secure_module
from sagest.models import Producto, KardexInventario
from settings import METODO_INVENTARIO
from sga.commonviews import adduserdata, obtener_reporte
from sga.excelbackground import reporte_corte_inventario_background
from sga.funciones import MiPaginador
from sga.models import Notificacion


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {'title': u'Inventarios'}
    persona = request.session['persona']
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'movimientos':
                try:
                    data['title'] = u'Movimientos de '
                    search = None
                    data['producto'] = producto = Producto.objects.get(pk=request.GET['id'])
                    if 's' in request.GET:
                        search = request.GET['s']
                        try:
                            valor = float(search)
                        except:
                            valor = 0
                        movimientos = producto.kardexinventario_set.filter(Q(compra__proveedor__nombre__icontains=search) |
                                                                           Q(compra__numerodocumento__icontains=search) |
                                                                           Q(compra__total=valor))

                    else:
                        movimientos = producto.kardexinventario_set.all()
                    paging = MiPaginador(movimientos, 25)
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
                    data['movimientos'] = page.object_list
                    return render(request, "adm_inventarios/kardex.html", data)
                except Exception as ex:
                    pass

            if action == 'reportedetalleexcel':
                try:
                    borders = Borders()
                    borders.left = 1
                    borders.right = 1
                    borders.top = 1
                    borders.bottom = 1
                    # data = extraervalores(request.GET['id'], request.GET['m'], request.GET['a'],True if 'h' in request.GET else False)
                    __author__ = 'Unemi'
                    title = easyxf('font: name Arial, bold on, height 350; alignment: horiz centre')
                    title1 = easyxf('font: name Bodoni MT, bold on, height 400; alignment: horiz centre')
                    title2 = easyxf('font: name Arial, bold on, height 200; align:wrap on; alignment: horiz left')
                    title3 = easyxf('font: name Arial, bold on, height 200; alignment: horiz center')
                    style = easyxf('font: name Arial, height 200; align:wrap on, horiz centre,vert centre')
                    style2 = easyxf('font: name Arial, height 200; align:wrap on, horiz left,vert centre')
                    style3 = easyxf('font: name Arial, bold on, height 200; align:wrap on, horiz right,vert centre')
                    normal = easyxf('font: name Arial , height 150; align: wrap on,horiz center ')
                    style.borders = borders
                    style2.borders = borders
                    wb = Workbook(encoding='utf-8')
                    producto = Producto.objects.get(pk=request.GET['idp'])
                    movimientos = producto.kardexinventario_set.all()


                    ws = wb.add_sheet('KARDEX')
                    ws.write_merge(1, 1, 0, 10, 'KARDEX '+producto.descripcion, title1)
                    ws.write_merge(2, 2, 0, 10, '', title2)
                    response = HttpResponse(content_type="application/ms-excel")
                    # response['Content-Disposition'] = 'attachment; filename=JORNADA_LABORAL_DE_'+distributivo.persona.apellido1.__str__()+"_"+distributivo.persona.apellido2.__str__() +"_"+distributivo.persona.nombres.__str__()+"_"+ random.randint(1, 10000).__str__() + '.xls'
                    response['Content-Disposition'] = 'attachment; filename=KARDEX_' + random.randint(1, 10000).__str__() + '.xls'
                    ws.col(0).width = 2000
                    ws.col(1).width = 4000
                    ws.col(2).width = 4000
                    ws.col(3).width = 15000
                    ws.col(4).width = 4000
                    ws.col(5).width = 4000
                    ws.col(6).width = 4000
                    ws.col(7).width = 4000
                    ws.col(8).width = 4000
                    ws.col(9).width = 4000
                    ws.col(10).width = 4000
                    row_num = 3

                    ws.write(row_num, 0, "No", title2)
                    ws.write(row_num, 1, "Fecha", title2)
                    ws.write(row_num, 2, "Movimiento", title2)
                    ws.write(row_num, 3, "Detalle", title2)
                    ws.write(row_num, 4, "Cantidad", title2)
                    ws.write(row_num, 5, "Costo", title2)
                    ws.write(row_num, 6, "Valor", title2)
                    ws.write(row_num, 7, "Saldo Ant.Cant.", title2)
                    ws.write(row_num, 8, "Saldo Act.Cant.", title2)
                    ws.write(row_num, 9, "Saldo Ant.Val.", title2)
                    ws.write(row_num, 10, "Saldo Act.Val.", title2)
                    row_num = 4
                    i = 0
                    for movimiento in movimientos:
                        i += 1
                        campo1 = str(i)
                        campo2 = movimiento.fecha
                        campo3 = 'SALIDA'
                        if movimiento.tipomovimiento == 1:
                            campo3 = 'ENTRADA'
                        campo4 = ''
                        if movimiento.es_compra:
                            if movimiento.compra:
                                ingreso_producto = movimiento.compra.ingresoproducto_set.filter(status=True)[0]
                                if ingreso_producto.tipodocumento:
                                    campo4 = ingreso_producto.tipodocumento.nombre + ': ' + ingreso_producto.numerodocumento + ' ' + (str(ingreso_producto.fechadocumento)) + ' ' + 'Proveedor:'  + ' ' + ingreso_producto.proveedor.nombre
                                else:
                                    campo4 = 'Proveedor:' + ingreso_producto.proveedor.nombre
                                if ingreso_producto.descripcion:
                                    campo4 = campo4 + 'Desc:'+ ' ' + ingreso_producto.descripcion
                        elif movimiento.es_salida:
                            campo4 = 'Doc:'+ movimiento.salida.salida_producto.numerodocumento+ ' ' + 'Responsable:'+ movimiento.salida.salida_producto.responsable + ', Dpto: ' + movimiento.salida.salida_producto.departamento
                        elif movimiento.es_anulacion:
                            campo4 = 'Motivo anulación:' + movimiento.anulacion.motivo
                        campo5 = ''
                        if movimiento.es_compra:
                            campo5 = movimiento.cantidad
                        elif movimiento.es_salida:
                            campo5 = '(' + movimiento.cantidad + ')'
                        elif movimiento.es_anulacion:
                            if movimiento.anulacion.tipomovimiento == 2:
                                campo5 = movimiento.cantidad
                            else:
                                campo5 = '(' + movimiento.cantidad + ')'
                        campo6 = movimiento.costo
                        campo7 = movimiento.valor
                        campo8 = movimiento.saldoinicialcantidad
                        campo9 = movimiento.saldofinalcantidad
                        campo10 = movimiento.saldoinicialvalor
                        campo11 = movimiento.saldofinalvalor
                        ws.write(row_num, 0, campo1, style2)
                        ws.write(row_num, 1, str(campo2)[0:10], style2)
                        ws.write(row_num, 2, campo3, style2)
                        ws.write(row_num, 3, campo4, style2)
                        ws.write(row_num, 4, campo5, style2)
                        ws.write(row_num, 5, campo6, style2)
                        ws.write(row_num, 6, campo7, style2)
                        ws.write(row_num, 7, campo8, style2)
                        ws.write(row_num, 8, campo9, style2)
                        ws.write(row_num, 9, campo10, style2)
                        ws.write(row_num, 10, campo11, style2)

                        row_num += 1

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'reportedetalleexcelxanio':
                try:
                    borders = Borders()
                    borders.left = 1
                    borders.right = 1
                    borders.top = 1
                    borders.bottom = 1
                    # data = extraervalores(request.GET['id'], request.GET['m'], request.GET['a'],True if 'h' in request.GET else False)
                    __author__ = 'Unemi'
                    title = easyxf('font: name Arial, bold on, height 350; alignment: horiz centre')
                    title1 = easyxf('font: name Bodoni MT, bold on, height 400; alignment: horiz centre')
                    title2 = easyxf('font: name Arial, bold on, height 200; align:wrap on; alignment: horiz left')
                    title3 = easyxf('font: name Arial, bold on, height 200; alignment: horiz center')
                    style = easyxf('font: name Arial, height 200; align:wrap on, horiz centre,vert centre')
                    style2 = easyxf('font: name Arial, height 200; align:wrap on, horiz left,vert centre')
                    style3 = easyxf('font: name Arial, bold on, height 200; align:wrap on, horiz right,vert centre')
                    normal = easyxf('font: name Arial , height 150; align: wrap on,horiz center ')
                    style.borders = borders
                    style2.borders = borders
                    wb = Workbook(encoding='utf-8')

                    fech_ini = request.GET['fechainicio']
                    fech_fin = request.GET['fechafin']
                    movimientos = KardexInventario.objects.filter(fecha__range=(fech_ini, fech_fin), status=True).order_by('fecha')

                    ws = wb.add_sheet('KARDEX')
                    ws.write_merge(1, 1, 0, 10, 'KARDEX ', title1)
                    ws.write_merge(2, 2, 0, 10, '', title2)
                    response = HttpResponse(content_type="application/ms-excel")
                    # response['Content-Disposition'] = 'attachment; filename=JORNADA_LABORAL_DE_'+distributivo.persona.apellido1.__str__()+"_"+distributivo.persona.apellido2.__str__() +"_"+distributivo.persona.nombres.__str__()+"_"+ random.randint(1, 10000).__str__() + '.xls'
                    response['Content-Disposition'] = 'attachment; filename=KARDEX_' + random.randint(1, 10000).__str__() + '.xls'

                    ws.col(0).width = 1000
                    ws.col(1).width = 4000
                    ws.col(2).width = 4000
                    ws.col(3).width = 10000
                    ws.col(4).width = 7000
                    ws.col(5).width = 15000
                    ws.col(6).width = 4000
                    ws.col(7).width = 4000
                    ws.col(8).width = 4000
                    ws.col(9).width = 4000
                    ws.col(10).width = 4000
                    ws.col(11).width = 4000
                    ws.col(12).width = 4000
                    ws.col(13).width = 4000
                    ws.col(14).width = 4000
                    row_num = 3

                    ws.write(row_num, 0, "No", title2)
                    ws.write(row_num, 1, "Fecha", title2)
                    ws.write(row_num, 2, "Movimiento", title2)
                    ws.write(row_num, 3, "Detalle", title2)
                    ws.write(row_num, 4, "Cuenta", title2)
                    ws.write(row_num, 5, "Producto", title2)
                    ws.write(row_num, 6, "Cantidad", title2)
                    ws.write(row_num, 7, "Costo", title2)
                    ws.write(row_num, 8, "Valor", title2)
                    ws.write(row_num, 9, "Saldo Ant.Cant.", title2)
                    ws.write(row_num, 10, "Saldo Act.Cant.", title2)
                    ws.write(row_num, 11, "Saldo Ant.Val.", title2)
                    ws.write(row_num, 12, "Saldo Act.Val.", title2)
                    ws.write(row_num, 13, "Prod Min.", title2)
                    ws.write(row_num, 14, "Prod Max.", title2)

                    row_num = 4
                    i = 0
                    for movimiento in movimientos:
                        i += 1
                        campo1 = str(i)
                        campo2 = movimiento.fecha
                        campo3 = 'E'
                        if movimiento.tipomovimiento == 1:
                            campo3 = 'I'
                        campo4 = ''
                        if movimiento.compra:
                            if movimiento.compra:
                                ingreso_producto = movimiento.compra.ingresoproducto_set.filter(status=True)[0]
                                campo4 = ingreso_producto.numerodocumento
                                # if ingreso_producto.tipodocumento:
                                #     campo4 = ingreso_producto.tipodocumento.nombre + ': ' + ingreso_producto.numerodocumento + ' ' + (str(ingreso_producto.fechadocumento)) + ' ' + 'Proveedor:'  + ' ' + ingreso_producto.proveedor.nombre
                                # else:
                                #     campo4 = 'Proveedor:' + ingreso_producto.proveedor.nombre
                                # if ingreso_producto.descripcion:
                                #     campo4 = campo4 + 'Desc:'+ ' ' + ingreso_producto.descripcion
                        elif movimiento.salida:
                            salida_producto = movimiento.salida.salidaproducto_set.filter(status=True)[0]
                            campo4 = salida_producto.numerodocumento
                            # campo4 = 'Doc:'+ movimiento.salida.salida_producto.numerodocumento+ ' ' + 'Responsable:'+ movimiento.salida.salida_producto.responsable + ', Dpto: ' + movimiento.salida.salida_producto.departamento
                        elif movimiento.es_anulacion:
                            campo4 = 'Motivo anulación:' + movimiento.anulacion.motivo
                        campo5 = ''
                        if movimiento.es_compra:
                            campo5 = movimiento.cantidad
                        elif movimiento.es_salida:
                            campo5 = '(' + movimiento.cantidad + ')'
                        elif movimiento.es_anulacion:
                            if movimiento.anulacion.tipomovimiento == 2:
                                campo5 = movimiento.cantidad
                            else:
                                campo5 = '(' + movimiento.cantidad + ')'
                        campo6 = round(movimiento.costo,4)
                        campo7 = round(movimiento.valor,4)
                        campo8 = movimiento.saldoinicialcantidad
                        campo9 = movimiento.saldofinalcantidad
                        campo10 = round(movimiento.saldoinicialvalor,4)
                        campo11 = round(movimiento.saldofinalvalor,4)
                        campo12 = movimiento.producto.descripcion
                        campo13 = movimiento.producto.cuenta.cuenta
                        campo14 = movimiento.producto.minimo
                        campo15 = movimiento.producto.maximo

                        ws.write(row_num, 0, campo1, style2)
                        ws.write(row_num, 1, str(campo2)[0:10], style2)
                        ws.write(row_num, 2, campo3, style2)
                        ws.write(row_num, 3, campo4, style2)
                        ws.write(row_num, 4, campo13, style2)
                        ws.write(row_num, 5, campo12, style2)
                        ws.write(row_num, 6, campo5, style2)
                        ws.write(row_num, 7, campo6, style2)
                        ws.write(row_num, 8, campo7, style2)
                        ws.write(row_num, 9, campo8, style2)
                        ws.write(row_num, 10, campo9, style2)
                        ws.write(row_num, 11, campo10, style2)
                        ws.write(row_num, 12, campo11, style2)
                        ws.write(row_num, 13, campo14, style2)
                        ws.write(row_num, 14, campo15, style2)
                        row_num += 1

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'reporteinventarioexcel':
                try:
                    productos = Producto.objects.filter(status=True, inventarioreal__isnull=False).distinct()
                    __author__ = 'Unemi'
                    ahora = datetime.now()
                    time_codigo = ahora.strftime('%Y%m%d_%H%M%S')
                    name_file = f'reporte_excel_inventario_{time_codigo}.xlsx'
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet("productos")

                    fuentecabecera = workbook.add_format({
                        'align': 'center',
                        'bg_color': 'silver',
                        'border': 1,
                        'bold': 1
                    })

                    formatoceldacenter = workbook.add_format({
                        'border': 1,
                        'valign': 'vcenter',
                        'align': 'center'})


                    fuenteencabezado = workbook.add_format({
                        'align': 'center',
                        'bg_color': '#1C3247',
                        'font_color': 'white',
                        'border': 1,
                        'font_size': 24,
                        'bold': 1
                    })

                    columnas = [
                        ('Cuenta', 10),
                        ('Código', 10),
                        ('Descripción', 40),
                        ('UM', 12),
                        ('Min.', 12),
                        ('Max.', 10),
                        ('Consumo mínimo diario', 10),
                        ('Consumo medio diario', 10),
                        ('Consumo máximo diario', 10),
                        ('Disp.', 10),
                        ('Costo', 10),
                        ('Total', 10),
                        ('Fecha último ingreso', 10),
                        ('Cantidad último ingreso', 10),
                    ]
                    ws.merge_range(0, 0, 0, 13, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', fuenteencabezado)
                    ws.merge_range(1, 0, 1, 13, 'LISTADO DE PRODUCTOS CON MINIMOS Y MAXIMOS', fuenteencabezado)

                    row_num, numcolum = 2, 0

                    for col_name in columnas:
                        ws.write(row_num, numcolum, col_name[0], fuentecabecera)
                        ws.set_column(row_num, numcolum, 40)
                        numcolum += 1
                    row_num += 1
                    iconalertaurl = 'https://sagest.unemi.edu.ec/static/images/alerta_inventario.gif'
                    iconalerta = io.BytesIO(urlopen(iconalertaurl).read())
                    format_red = workbook.add_format({'bg_color': 'red',
                                                      'border': 1,
                                                        'valign': 'vcenter',
                                                        'align': 'center'})
                    format_green = workbook.add_format({'bg_color': 'green',
                                                      'border': 1,
                                                        'valign': 'vcenter',
                                                        'align': 'center'})
                    for producto in productos:
                        ws.write(row_num, 0, producto.cuenta.cuenta.__str__(), formatoceldacenter)
                        ws.write(row_num, 1, producto.codigo, formatoceldacenter)
                        ws.write(row_num, 2, producto.descripcion, formatoceldacenter)
                        ws.write(row_num, 3, producto.unidadmedida.__str__(), formatoceldacenter)
                        ws.write(row_num, 4, producto.minimo, formatoceldacenter)
                        ws.write(row_num, 5, producto.maximo, formatoceldacenter)
                        ws.write(row_num, 6, producto.consumo_minimo_diario, formatoceldacenter)
                        ws.write(row_num, 7, producto.consumo_medio_diario, formatoceldacenter)
                        ws.write(row_num, 8, producto.consumo_maximo_diario, formatoceldacenter)
                        ws.write(row_num, 9, producto.stock_inventario(), formatoceldacenter)
                        ws.write(row_num, 10, producto.mi_inventario_general().costo, formatoceldacenter)
                        ws.write(row_num, 11, producto.valor_inventario(), formatoceldacenter)
                        ws.write(row_num, 12, str(producto.ultima_compra().fecha.date()) if producto.ultima_compra() else '', formatoceldacenter)
                        ws.write(row_num, 13, int(producto.ultima_compra().cantidad) if producto.ultima_compra() else '', formatoceldacenter)

                        # inventario = producto.mi_inventario_general()
                        # form_alerta_color = format_red if inventario.esta_bajo_minimo() and inventario.cantidad else format_green
                        # ws.write(row_num, 9, "", form_alerta_color)
                        row_num += 1
                    workbook.close()
                    output.seek(0)
                    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = f'attachment; filename="{name_file}"'
                    return response
                except Exception as ex:
                    pass

            if action == 'reporteinventarioexcel_min_max':
                try:
                    productos = Producto.objects.filter(status=True,
                                                        inventarioreal__isnull=False,).distinct()
                    __author__ = 'Unemi'
                    ahora = datetime.now()
                    time_codigo = ahora.strftime('%Y%m%d_%H%M%S')
                    name_file = f'reporte_excel_inventario_productos_{time_codigo}.xlsx'
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet("productos")

                    fuentecabecera = workbook.add_format({
                        'align': 'center',
                        'bg_color': 'silver',
                        'border': 1,
                        'bold': 1
                    })

                    formatoceldacenter = workbook.add_format({
                        'border': 1,
                        'valign': 'vcenter',
                        'align': 'center'})

                    fuenteencabezado = workbook.add_format({
                        'align': 'center',
                        'bg_color': '#1C3247',
                        'font_color': 'white',
                        'border': 1,
                        'font_size': 24,
                        'bold': 1
                    })

                    columnas = [
                        ('Cuenta', 10),
                        ('Código', 10),
                        ('Descripción', 40),
                        ('UM', 8),
                        ('Consumo Min.', 20),
                        ('Consumo Med.', 20),
                        ('Consumo Max.', 20),
                        ('Disp.', 8),
                        ('Costo', 8),
                        ('Total', 8),
                        ('Existencia Min', 25),
                        ('Punto de Pedido', 25),
                        ('Existencia Max', 25),
                        ('Cantidad de pedido', 25),
                    ]

                    ws.merge_range(0, 0, 0, 13, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', fuenteencabezado)
                    ws.merge_range(1, 0, 1, 13, 'LISTADO DE PRODUCTOS CON MINIMOS Y MAXIMOS', fuenteencabezado)

                    row_num, numcolum = 3, 0

                    for col_name in columnas:
                        ws.write(row_num, numcolum, col_name[0], fuentecabecera)
                        ws.set_column(row_num, numcolum, col_name[1])
                        numcolum += 1

                    row_num += 1

                    for producto in productos:
                        ws.write(row_num, 0, producto.cuenta.cuenta.__str__(), formatoceldacenter)
                        ws.write(row_num, 1, producto.codigo, formatoceldacenter)
                        ws.write(row_num, 2, producto.descripcion, formatoceldacenter)
                        ws.write(row_num, 3, producto.unidadmedida.__str__(), formatoceldacenter)
                        ws.write(row_num, 4, producto.consumo_minimo_diario, formatoceldacenter)
                        ws.write(row_num, 5, producto.consumo_medio_diario, formatoceldacenter)
                        ws.write(row_num, 6, producto.consumo_maximo_diario, formatoceldacenter)
                        ws.write(row_num, 7, producto.stock_inventario(), formatoceldacenter)
                        ws.write(row_num, 8, producto.mi_inventario_general().costo, formatoceldacenter)
                        ws.write(row_num, 9, producto.valor_inventario(), formatoceldacenter)
                        ws.write(row_num, 10, producto.minimo, formatoceldacenter)
                        ws.write(row_num, 11, producto.calcular_punto_pedido(), formatoceldacenter)
                        ws.write(row_num, 12, producto.maximo, formatoceldacenter)
                        ws.write(row_num, 13, producto.calcular_cantidad_pedido(), formatoceldacenter)
                        row_num += 1
                    workbook.close()
                    output.seek(0)
                    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = f'attachment; filename="{name_file}"'
                    return response
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    print(ex)
                    pass

            if action == 'reportecorteinventario':
                try:
                    titulo='Generación de reporte de corte de inventario en proceso.'
                    noti = Notificacion(cuerpo='Reporte de corte de inventario en progreso',
                                        titulo=titulo, destinatario=persona,
                                        url='',
                                        prioridad=1, app_label='sga-sagest',
                                        fecha_hora_visible=datetime.now() + timedelta(days=3), tipo=2,
                                        en_proceso=True)
                    noti.save(request)
                    reporte_corte_inventario_background(request=request, data=data, notif=noti.pk).start()
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': 'Error'.format(ex)})
            return HttpResponseRedirect(request.path)
        else:
            search = None
            tipo = None

            if 't' in request.GET:
                tipo = request.GET['t']
                data['tipoid'] = int(tipo) if tipo else ""

            if 's' in request.GET:
                search = request.GET['s']
                productos = Producto.objects.filter(Q(codigo__icontains=search) |
                                                    Q(descripcion__icontains=search), inventarioreal__isnull=False).distinct()
            else:
                productos = Producto.objects.filter(inventarioreal__isnull=False)
            paging = MiPaginador(productos, 25)
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
            data['reporte_0'] = obtener_reporte('movimientos_producto')
            data['reporte_1'] = obtener_reporte('inventario_general')
            data['productos'] = page.object_list
            data['metodo_inventario'] = METODO_INVENTARIO
            return render(request, "adm_inventarios/view.html", data)
