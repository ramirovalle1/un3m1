# -*- coding: UTF-8 -*-
import json
from datetime import datetime
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module
from sagest.commonviews import secuencia_bodega, DetalleAnulacion
from sagest.forms import AnulacionForm
from sagest.models import SalidaProducto, Anulacion, KardexInventario, IngresoProducto, SolicitudProductos, \
    InventarioReal
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import MiPaginador, null_to_decimal, log


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'detalle_anulacion':
            try:
                data['anulacion'] = anulacion = Anulacion.objects.get(pk=request.POST['id'])
                data['detalles'] = anulacion.detalleanulacion_set.all()
                template = get_template("adm_anulaciones/detalleanulacion.html")
                json_content = template.render(data)
                return HttpResponse(json.dumps({"result": "ok", 'data': json_content, 'id': anulacion.id}), content_type="application/json")
            except Exception as ex:
                pass

        if action == 'anularsalida':
            try:
                f = AnulacionForm(request.POST)
                if f.is_valid():
                    if not SalidaProducto.objects.filter(numerodocumento=f.cleaned_data['numerodocumento']).exists():
                        return HttpResponse(json.dumps({"result": "bad", "mensaje": u"No existe ese número de documento."}), content_type="application/json")
                    salida = SalidaProducto.objects.filter(numerodocumento=f.cleaned_data['numerodocumento'])[0]
                    anulacion = Anulacion(tipomovimiento=2,
                                          salida=salida,
                                          fecha=datetime.now(),
                                          motivo=f.cleaned_data['motivo'])
                    anulacion.save(request)
                    if salida.solicitud:
                        soli = SolicitudProductos.objects.get(pk=salida.solicitud.id)
                        soli.estados = 5
                        soli.save(request)
                    secuencia = secuencia_bodega(request)
                    secuencia.anulaciones += 1
                    secuencia.save(request)
                    anulacion.numero = secuencia.anulaciones
                    anulacion.save(request)
                    salida.anulado = True
                    salida.save(request)
                    for detalle in salida.productos.all():
                        detalleanulacion = DetalleAnulacion(anulacion=anulacion,
                                                            producto=detalle.producto,
                                                            cantidad=detalle.cantidad,
                                                            costo=detalle.costo,
                                                            valor=detalle.valor)
                        detalleanulacion.save(request)
                        kardex = detalle.kardex_inventario()
                        kardex.anulado = True
                        kardex.save(request)
                        inv = detalleanulacion.producto.mi_inventario_general()
                        # COSTO Y SALDO ANTES DEL MOVIMIENTO
                        saldoinicialvalor = null_to_decimal(detalleanulacion.producto.valor_inventario(), 15)
                        saldoinicialcantidad = null_to_decimal(detalleanulacion.producto.stock_inventario(),4)
                        # inv.cantidad = null_to_decimal((inv.cantidad + detalleanulacion.cantidad), 4)
                        # inv.valor = null_to_decimal((inv.cantidad * float(inv.costo)), 15)
                        # inv.save(request)
                        kardex = KardexInventario(producto=detalleanulacion.producto,
                                                  inventario=inv,
                                                  tipomovimiento=1,
                                                  fecha=anulacion.fecha_creacion,
                                                  anulacion=anulacion,
                                                  saldoinicialvalor=saldoinicialvalor,
                                                  saldoinicialcantidad=saldoinicialcantidad,
                                                  cantidad=detalleanulacion.cantidad,
                                                  costo=detalleanulacion.costo,
                                                  valor=detalleanulacion.valor)
                        kardex.save(request)
                        # COSTO Y SALDO DESPUES DEL MOVIMIENTO
                        kardex.producto.actualizar_inventario_anular_salida(detalle.costo,detalle.cantidad,detalle.valor,request)

                        saldofinalvalor = null_to_decimal(detalleanulacion.producto.valor_inventario(), 15)
                        saldofinalcantidad = null_to_decimal(detalleanulacion.producto.stock_inventario(),4)
                        kardex.saldofinalcantidad = saldofinalcantidad
                        kardex.saldofinalvalor = saldofinalvalor
                        kardex.save(request)

                    log(u'Adicionó anulación de salida: %s' % anulacion, request, "add")
                    return HttpResponse(json.dumps({"result": "ok"}), content_type="application/json")
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

        if action == 'anularcompra':
            try:
                f = AnulacionForm(request.POST)
                if f.is_valid():
                    if not IngresoProducto.objects.filter(numero=f.cleaned_data['numerodocumento']).exists():
                        return HttpResponse(json.dumps({"result": "bad", "mensaje": u"No existe ese número de documento."}), content_type="application/json")
                    ingreso = IngresoProducto.objects.filter(numero=f.cleaned_data['numerodocumento'])[0]
                    # for detalle in ingreso.productos.all():
                    #     if detalle.cantidad < detalle.producto.mi_inventario_general().cantidad:
                    #         return HttpResponse(json.dumps({"result": "bad", "mensaje": u"No se puede anular ese documento, ya tuvo salida."}), content_type="application/json")
                    anulacion = Anulacion(tipomovimiento=1,
                                          ingreso=ingreso,
                                          fecha=datetime.now(),
                                          motivo=f.cleaned_data['motivo'])
                    anulacion.save(request)
                    secuencia = secuencia_bodega(request)
                    secuencia.anulaciones += 1
                    secuencia.save(request)
                    anulacion.numero = secuencia.anulaciones
                    anulacion.save(request)
                    ingreso.anulado = True
                    ingreso.save(request)
                    for detalle in ingreso.productos.all():
                        kardex = detalle.kardex()
                        kardex.anulado = True
                        kardex.save(request)
                        detalleanulacion = DetalleAnulacion(anulacion=anulacion,
                                                            producto=detalle.producto,
                                                            cantidad=detalle.cantidad,
                                                            costo=detalle.costo,
                                                            valor=detalle.total)
                        detalleanulacion.save(request)
                        kardex = detalle.kardex()
                        kardex.anulado = True
                        kardex.save(request)
                        inv = detalleanulacion.producto.mi_inventario_general()
                        # COSTO Y SALDO ANTES DEL MOVIMIENTO
                        saldoinicialvalor = null_to_decimal(detalleanulacion.producto.valor_inventario(),15)
                        saldoinicialcantidad = null_to_decimal(detalleanulacion.producto.stock_inventario(),4)
                        # inv.cantidad = null_to_decimal((inv.cantidad - detalleanulacion.cantidad),4)
                        # inv.valor = null_to_decimal((inv.cantidad * float(inv.costo)),15)
                        # inv.save(request)
                        kardex = KardexInventario(producto=detalleanulacion.producto,
                                                  inventario=inv,
                                                  tipomovimiento=2,
                                                  fecha=anulacion.fecha_creacion,
                                                  anulacion=anulacion,
                                                  saldoinicialvalor=saldoinicialvalor,
                                                  saldoinicialcantidad=saldoinicialcantidad,
                                                  cantidad=detalleanulacion.cantidad,
                                                  costo=detalleanulacion.costo,
                                                  valor=detalleanulacion.valor)
                        kardex.save(request)
                        kardex.producto.actualizar_inventario_anular_ingreso(detalle.costo,detalle.cantidad,detalle.total,request)
                        # COSTO Y SALDO DESPUES DEL MOVIMIENTO
                        saldofinalvalor = null_to_decimal(detalleanulacion.producto.valor_inventario(),15)
                        saldofinalcantidad = null_to_decimal(detalleanulacion.producto.stock_inventario(),4)
                        kardex.saldofinalcantidad = saldofinalcantidad
                        kardex.saldofinalvalor = saldofinalvalor
                        kardex.save(request)

                    log(u'Adicionó anulación de compra: %s' % anulacion, request, "add")
                    return HttpResponse(json.dumps({"result": "ok"}), content_type="application/json")
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos."}), content_type="application/json")

        if action == 'buscardocumento':
            try:
                if SalidaProducto.objects.filter(numerodocumento=request.POST['id']).exists():
                    salida = SalidaProducto.objects.filter(numerodocumento=request.POST['id'])[0]
                    return HttpResponse(json.dumps({"result": "ok", "informacion": u'%s - %s' % (salida.descripcion, salida.responsable.nombre_completo())}), content_type="application/json")
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"El documento no existe"}), content_type="application/json")
            except Exception as ex:
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al obtener los datos"}), content_type="application/json")

        if action == 'buscardocumento_compra':
            try:
                if IngresoProducto.objects.filter(numero=request.POST['id']).exists():
                    ingreso = IngresoProducto.objects.filter(numero=request.POST['id'])[0]
                    return HttpResponse(json.dumps({"result": "ok", "informacion": u'%s - %s' % (ingreso.descripcion, ingreso.proveedor)}), content_type="application/json")
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"El documento no existe"}), content_type="application/json")
            except Exception as ex:
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al obtener los datos"}), content_type="application/json")

        return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Solicitud Incorrecta."}), content_type="application/json")
    else:
        data['title'] = u'Anulaciones de Documentos'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'anularsalida':
                try:
                    data['title'] = u'Anular Comprobante de Salida'
                    form = AnulacionForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "adm_anulaciones/anularsalida.html", data)
                except Exception as ex:
                    pass

            if action == 'anularcompra':
                try:
                    data['title'] = u'Anular Comprobante de Ingreso'
                    form = AnulacionForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "adm_anulaciones/anularcompra.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
            if search:
                anulaciones = Anulacion.objects.filter(Q(salida__departamento__nombre__icontains=search) |
                                                       Q(salida__numerodocumento__icontains=search) |
                                                       Q(numerodo__icontains=search) |
                                                       Q(salida__descripcion__icontains=search) |
                                                       Q(salida__observaciones__icontains=search) |
                                                       Q(ingreso__proveedor__nombre__icontains=search) |
                                                       Q(ingreso__proveedor__alias__icontains=search) |
                                                       Q(ingreso__proveedor__identificacion__icontains=search) |
                                                       Q(ingreso__numero__icontains=search))
            elif 'id' in request.GET:
                ids = request.GET['id']
                anulaciones = Anulacion.objects.filter(id=ids)
            else:
                anulaciones = Anulacion.objects.all()
            paging = MiPaginador(anulaciones, 25)
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
            data['reporte_0'] = obtener_reporte('documento_salida_anulado')
            data['anulaciones'] = page.object_list
            return render(request, "adm_anulaciones/view.html", data)