# -*- coding: UTF-8 -*-
import io
import json
from datetime import datetime
from decimal import Decimal

import xlsxwriter
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module
from sagest.commonviews import secuencia_bodega
from sagest.forms import SalidaProductoForm, DetalleSalidaProductoForm, SalidaProductoModalEditForm
from sagest.models import Producto, SalidaProducto, Departamento, DetalleSalidaProducto, InventarioReal
from sga.adm_convenioempresa import buscar_dicc
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import log, MiPaginador, puede_realizar_accion, null_to_decimal

from sga.templatetags.sga_extras import encrypt

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = SalidaProductoForm(request.POST)
                if f.is_valid():
                    datos = json.loads(request.POST['lista_items1'])
                    for elemento in datos:
                        producto = Producto.objects.get(pk=int(elemento['id']))
                        if null_to_decimal(producto.stock_inventario(),6) < null_to_decimal(float(elemento['cantidad'])):
                            return JsonResponse({"result": "bad", "mensaje": u"El producto %s no tiene la existencia ingresada." % producto.codigo})
                    salidaprod = SalidaProducto(departamento=f.cleaned_data['departamento'],
                                                responsable=f.cleaned_data['responsable'],
                                                fechaoperacion=datetime.now(),
                                                descripcion=f.cleaned_data['descripcion'],
                                                observaciones=f.cleaned_data['observaciones'])
                    salidaprod.save(request)
                    secuencia = secuencia_bodega(request)
                    secuencia.salida += 1
                    secuencia.save(request)
                    salidaprod.numerodocumento = secuencia.salida
                    salidaprod.save(request)
                    for elemento in datos:
                        producto = Producto.objects.get(pk=int(elemento['id']))
                        detallesalprod = DetalleSalidaProducto(producto=producto,
                                                               cantidad=Decimal(elemento['cantidad']).quantize(Decimal('.0001')))
                        detallesalprod.save(request)
                        salidaprod.productos.add(detallesalprod)
                        # ACTUALIZAR INVENTARIO REAL
                        producto.actualizar_inventario_salida(detallesalprod, request)
                    salidaprod.save(request)
                    log(u'Adiciono nueva salida de inventario: %s' % salidaprod, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})


 #------------------------------EDITAR POST--------------------------------------------------------------------------------

        if action == 'editsalidaproductomodal':
            try:
                salidapro= SalidaProducto.objects.get(pk=encrypt(request.POST['id']))
                f = SalidaProductoModalEditForm(request.POST)
                if f.is_valid():

                    salidapro.descripcion = f.cleaned_data['descripcion']
                    salidapro.observaciones = f.cleaned_data['observaciones']
                    salidapro.save(request)
                    log(u'Modifico Salida de Productos: %s' % salidapro, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})



        if action == 'buscarresponsable':
            try:
                departamento = Departamento.objects.get(pk=int(request.POST['id']))
                lista = []
                for integrante in departamento.integrantes.filter(administrativo__isnull=False):
                    lista.append([integrante.id, integrante.nombre_completo_inverso()])
                return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'chequeacodigos':
            try:
                cod_existen = [x.codigo for x in Producto.objects.filter(codigo__in=request.POST['codigos'].split(","))]
                if cod_existen:
                    return JsonResponse({"result": "ok", "codigosexisten": cod_existen})
                return JsonResponse({"result": "bad"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'comprobarnumero':
            try:
                departamento = Departamento.objects.get(pk=request.POST['pid'])
                numero = request.POST['numero']
                if departamento.salidaproducto_set.filter(numero=numero).exists():
                    return JsonResponse({"result": "bad"})
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'detalle_salida':
            try:
                data['salida'] = salida = SalidaProducto.objects.get(pk=request.POST['id'])
                data['detalles'] = salida.productos.filter(status=True)
                data['reporte_egreso'] = obtener_reporte('comprobante_egreso_cuenta')
                template = get_template("adm_salidas/detallesalidas.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content, 'numero': salida.numerodocumento})
            except Exception as ex:
                pass

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Salidas de productos'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    puede_realizar_accion(request, 'sagest.puede_dar_salida_inventario')
                    ultimo = 1
                    try:
                        ultimo = SalidaProducto.objects.all().order_by("-id")[0].numerodocumento
                        ultimo = int(ultimo) + 1
                    except:
                        pass
                    form = SalidaProductoForm(initial={'numerodocumento': str(ultimo)})
                    form.adicionar()
                    data['form'] = form
                    form2 = DetalleSalidaProductoForm()
                    form2.adicionar()
                    data['form2'] = form2
                    return render(request, "adm_salidas/add.html", data)
                except Exception as ex:
                    pass
#-----------------------------------------EDITAR POR GET----------------------------------------------------

            elif action == 'editsalidaproductomodal':
                try:

                    data['title'] = u"Editar salida producto"
                    salidapro = SalidaProducto.objects.get(pk=encrypt(request.GET['id']))
                    form = SalidaProductoModalEditForm(initial={"descripcion": salidapro.descripcion, "observaciones": salidapro.observaciones})
                    data['form'] = form
                    data['salidapro'] = salidapro

                    template = get_template("adm_salidas/editarsalidapro.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})

                except Exception as ex:
                    response = JsonResponse({'result': False, 'mensaje': 'Error {}'.format(ex)})
                return HttpResponse(response.content)


            elif action == 'consultarvalorInventario':
                try:
                    id = request.GET['id']
                    filtro = Producto.objects.get(pk=id)
                    inv = InventarioReal.objects.filter(status=True, producto=filtro)
                    stock = 0
                    if inv.exists():
                        stock = inv.first().cantidad
                    response = JsonResponse({'state': True, 'stock': stock})
                except Exception as ex:
                    response = JsonResponse({'state': False})
                return HttpResponse(response.content)

            elif action == 'generarreporte':
                try:
                    __author__ = 'Unemi'

                    desde = request.GET['desde']
                    hasta = request.GET['hasta']
                    departamento = request.GET['departamento']
                    departamento_nombre = request.GET['departamento_nombre']

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('salidas')
                    ws.set_column(0, 10, 30)
                    formatotitulo = workbook.add_format({'bold': 1, 'text_wrap': True,'border': 1,'align': 'center','valign': 'middle', 'fg_color': '#A2D0EC'})
                    formatotitulo_filtros = workbook.add_format({'bold': 1, 'text_wrap': True, 'border': 1, 'fg_color': '#EBF5FB'})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center','bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#EBF5FB'})
                    formatoceldaleft = workbook.add_format({'text_wrap': True, 'align': 'center', 'valign': 'vcenter' ,'border': 1})

                    ws.write(1, 0, 'DEPARTAMENTO', formatotitulo_filtros)
                    ws.merge_range('A1:I1', 'REPORTE DE SALIDAS A DEPARTAMENTOS', formatotitulo)
                    ws.merge_range('B2:E2', (departamento_nombre), formatoceldaleft)

                    ws.write(1, 5, 'DESDE', formatotitulo_filtros)
                    ws.write(1, 6, (desde), formatoceldaleft)
                    ws.write(1, 7, 'HASTA', formatotitulo_filtros)
                    ws.write(1, 8, (hasta), formatoceldaleft)

                    ws.write(2, 0, 'FECHA', formatoceldacab)
                    ws.write(2, 1, 'NUMERO', formatoceldacab)
                    ws.write(2, 2, 'DESCRIPCION', formatoceldacab)
                    ws.write(2, 3, 'CODIGO', formatoceldacab)
                    ws.write(2, 4, 'PRODUCTO', formatoceldacab)
                    ws.write(2, 5, 'CANTIDAD', formatoceldacab)
                    ws.write(2, 6, 'COSTO', formatoceldacab)
                    ws.write(2, 7, 'VALOR', formatoceldacab)
                    ws.write(2, 8, 'TOTAL', formatoceldacab)

                    filtrofechas = Q(fechaoperacion__range=(desde, hasta))
                    salidas = SalidaProducto.objects.filter(filtrofechas, status=True, departamento=departamento).distinct()

                    fila_salida = 3
                    fila_detalle_salida = 4

                    fila_desde = 4
                    fila_hasta = 0

                    for salida in salidas:
                        filas_recorridas=0
                        for detalle in salida.productos.all():
                            ws.write('D%s' % fila_detalle_salida, str(detalle.producto.codigo), formatoceldaleft)
                            ws.write('E%s' % fila_detalle_salida, str(detalle.producto.descripcion), formatoceldaleft)
                            ws.write('F%s' % fila_detalle_salida, int(detalle.cantidad), formatoceldaleft)
                            ws.write('G%s' % fila_detalle_salida, round(detalle.costo, 2), formatoceldaleft)
                            ws.write('H%s' % fila_detalle_salida, round(detalle.valor ,2), formatoceldaleft)
                            fila_detalle_salida+=1
                            fila_salida+=1
                            filas_recorridas+=1
                        if filas_recorridas > 0:
                            fila_hasta=fila_desde+filas_recorridas-1
                            ws.merge_range('A' + str(fila_desde) + ':' + 'A' + str(fila_hasta),salida.fechaoperacion.strftime('%Y-%m-%d'), formatoceldaleft)
                            ws.merge_range('B' + str(fila_desde) + ':' + 'B' + str(fila_hasta), salida.numerodocumento,formatoceldaleft)
                            ws.merge_range('C' + str(fila_desde) + ':' + 'C' + str(fila_hasta), salida.descripcion,formatoceldaleft)
                            ws.merge_range('I' + str(fila_desde) + ':' + 'I' + str(fila_hasta), round(salida.valor, 2),formatoceldaleft)
                            fila_desde=fila_hasta+1
                            if filas_recorridas==1:
                                ws.write('A%s' % fila_salida, salida.fechaoperacion.strftime('%Y-%m-%d'),formatoceldaleft)
                                ws.write('B%s' % fila_salida, salida.numerodocumento, formatoceldaleft)
                                ws.write('C%s' % fila_salida, salida.descripcion, formatoceldaleft)
                                ws.write('I%s' % fila_salida, round(salida.valor, 2), formatoceldaleft)

                    workbook.close()
                    output.seek(0)
                    filename = 'Salidas a departamentos.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'cargar_departamento':
                try:
                    lista = []
                    departamentos = Departamento.objects.filter(status=True).distinct()

                    for departamento in departamentos:
                        if not buscar_dicc(lista, 'id', departamento.id):
                            lista.append({'id': departamento.id, 'nombre': departamento.nombre})
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            try:
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s']
                if search:
                    salidas = SalidaProducto.objects.filter(Q(departamento__nombre__icontains=search) |
                                                            Q(numerodocumento__icontains=search) |
                                                            Q(descripcion__icontains=search) |
                                                            Q(observaciones__icontains=search))
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    salidas = SalidaProducto.objects.filter(id=ids)
                else:
                    salidas = SalidaProducto.objects.filter(status=True)
                paging = MiPaginador(salidas, 25)
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
                data['reporte_0'] = obtener_reporte('comprobante_egreso')
                data['salidas'] = page.object_list
                return render(request, "adm_salidas/view.html", data)
            except Exception as ex:
                error_linea = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                return JsonResponse({'ex': f'{ex} {error_linea}'})