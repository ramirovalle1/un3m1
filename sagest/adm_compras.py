# -*- coding: UTF-8 -*-
import json
from datetime import datetime
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.commonviews import secuencia_bodega
from sagest.forms import IngresoProductoForm, DetalleIngresoProductoForm, ProveedorForm
from sagest.models import IngresoProducto, Producto, DetalleIngresoProducto, Proveedor, KardexInventario
from settings import IVA
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import log, MiPaginador, puede_realizar_accion, convertir_fecha


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'ingresoinv':
            try:
                f = IngresoProductoForm(request.POST)
                if f.is_valid():
                    datos = json.loads(request.POST['lista_items1'])
                    iva = 0
                    for d in datos:
                        if Decimal(d['porcientoiva']) > 0 and iva == 0:
                            iva = Decimal(d['porcientoiva'])
                        elif Decimal(d['porcientoiva']) > 0 and iva != 0 and Decimal(d['porcientoiva']) != iva:
                            return JsonResponse({"result": "bad", "mensaje": u"Error Pocentajes de IVA diferentes en la factura"})
                    base12 = Decimal(request.POST['form_subtotal_base12'])
                    base0 = Decimal(request.POST['form_subtotal_base0'])
                    desc = Decimal(request.POST['form_total_descuento'])
                    iva = Decimal(request.POST['form_total_iva'])
                    total = Decimal(request.POST['form_total'])
                    ingresoprod = IngresoProducto(proveedor=f.cleaned_data['proveedor'],
                                                  tipodocumento=f.cleaned_data['tipodocumento'],
                                                  numerodocumento=f.cleaned_data['numerodocumento'],
                                                  fechadocumento=f.cleaned_data['fechadocumento'],
                                                  ordencompra=f.cleaned_data['ordencompra'],
                                                  solicitudcompra=f.cleaned_data['solicitudcompra'],
                                                  descripcion=f.cleaned_data['descripcion'],
                                                  fechaoperacion=datetime.now(),
                                                  subtotal_base12=base12,
                                                  subtotal_base0=base0,
                                                  total_descuento=desc,
                                                  total_iva=iva,
                                                  total=total,
                                                  transporte=0)
                    ingresoprod.save(request)
                    secuencia = secuencia_bodega(request)
                    secuencia.ingreso += 1
                    secuencia.save(request)
                    ingresoprod.numero = secuencia.ingreso
                    ingresoprod.save(request)
                    # ITEMS
                    for d in datos:
                        producto = Producto.objects.get(pk=int(d['id']))
                        detalleingprod = DetalleIngresoProducto(producto=producto,
                                                                cantidad=Decimal(d['cantidad']).quantize(Decimal('.0001')),
                                                                costo=Decimal(d['costo']).quantize(Decimal('.000001')),
                                                                subtotal=Decimal(d['subtotal']).quantize(Decimal('.000001')),
                                                                descuento=Decimal(d['valor_descuento']).quantize(Decimal('.000001')),
                                                                coniva=True if Decimal(d['valoriva']) else False,
                                                                valoriva=Decimal(d['valoriva']).quantize(Decimal('.000001')),
                                                                total=Decimal(d['total']).quantize(Decimal('.000001')),
                                                                estado_id=int(d['estado']),
                                                                fechacaducidad=convertir_fecha(d['fechacaducidad'])
                                                                )
                        detalleingprod.save(request)
                        ingresoprod.productos.add(detalleingprod)
                        # COSTO Y SALDO ANTES DEL MOVIMIENTO
                        saldoinicialvalor = Decimal(detalleingprod.producto.valor_inventario()).quantize(Decimal('.000000000000001'))
                        saldoinicialcantidad = Decimal(detalleingprod.producto.stock_inventario()).quantize(Decimal('.0001'))
                        # ACTUALIZAR INVENTARIO REAL
                        costoproducto = Decimal((detalleingprod.total / detalleingprod.cantidad)).quantize(Decimal('.000000000000001')) if detalleingprod.total else 0
                        producto.actualizar_inventario_ingreso(costoproducto, detalleingprod.cantidad, detalleingprod.total, request)
                        inventario = producto.mi_inventario_general()
                        # ACTUALIZAR KARDEX
                        kardex = KardexInventario(producto=detalleingprod.producto,
                                                  inventario=inventario,
                                                  tipomovimiento=1,
                                                  fecha=ingresoprod.fecha_creacion,
                                                  compra=detalleingprod,
                                                  saldoinicialvalor=saldoinicialvalor,
                                                  saldoinicialcantidad=saldoinicialcantidad,
                                                  cantidad=detalleingprod.cantidad,
                                                  costo=costoproducto,
                                                  valor=Decimal(costoproducto * detalleingprod.cantidad).quantize(Decimal('.0000000000000001')))
                        kardex.save(request)
                        # COSTO Y SALDO DESPUES DEL MOVIMIENTO
                        saldofinalvalor = Decimal(detalleingprod.producto.valor_inventario()).quantize(Decimal('.0000000000000001'))
                        saldofinalcantidad = Decimal(detalleingprod.producto.stock_inventario()).quantize(Decimal('.0001'))
                        kardex.saldofinalcantidad = saldofinalcantidad
                        kardex.saldofinalvalor = saldofinalvalor
                        kardex.save(request)
                    # ingresoprod.total = Decimal(ingresoprod.valor_compra()).quantize(Decimal('.01'))
                    ingresoprod.save(request)
                    log(u'Adiciono nueva compra de inventario: %s' % ingresoprod, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        # if action == 'anularcompra':
        #     try:
        #         f = AnulacionForm(request.POST)
        #         if f.is_valid():
        #             compra = IngresoProducto.objects.get(pk=request.POST['id'])
        #             anulacion = Anulacion(tipomovimiento=1,
        #                                   compra=compra,
        #                                   fecha=datetime.now(),
        #                                   motivo=f.cleaned_data['motivo'])
        #             anulacion.save(request)
        #             secuencia = secuencia_bodega(request)
        #             secuencia.anulaciones += 1
        #             secuencia.save(request)
        #             anulacion.numero = secuencia.anulaciones
        #             anulacion.save(request)
        #             compra.anulado = True
        #             compra.save(request)
        #             for detalle in compra.productos.all():
        #                 detalleanulacion = DetalleAnulacion(anulacion=anulacion,
        #                                                     producto=detalle.producto,
        #                                                     cantidad=detalle.cantidad,
        #                                                     costo=detalle.costo,
        #                                                     valor=detalle.valor)
        #                 detalleanulacion.save(request)
        #                 inv = detalleanulacion.producto.mi_inventario_general()
        #                 # COSTO Y SALDO ANTES DEL MOVIMIENTO
        #                 saldoinicialvalor = detalleanulacion.producto.valor_inventario()
        #                 saldoinicialcantidad = detalleanulacion.producto.stock_inventario()
        #                 inv.cantidad = round(inv.cantidad + detalleanulacion.cantidad, 4)
        #                 inv.valor = inv.cantidad * inv.costo
        #                 inv.save(request)
        #                 kardex = KardexInventario(producto=detalleanulacion.producto,
        #                                           inventario=inv,
        #                                           tipomovimiento=1,
        #                                           fecha=anulacion.fecha_creacion,
        #                                           anulacion=anulacion,
        #                                           saldoinicialvalor=saldoinicialvalor,
        #                                           saldoinicialcantidad=saldoinicialcantidad,
        #                                           cantidad=detalleanulacion.cantidad,
        #                                           costo=detalleanulacion.costo,
        #                                           valor=detalleanulacion.valor)
        #                 kardex.save(request)
        #                 # COSTO Y SALDO DESPUES DEL MOVIMIENTO
        #                 saldofinalvalor = detalleanulacion.producto.valor_inventario()
        #                 saldofinalcantidad = detalleanulacion.producto.stock_inventario()
        #                 kardex.saldofinalcantidad = saldofinalcantidad
        #                 kardex.saldofinalvalor = saldofinalvalor
        #                 kardex.save(request)
        #             return JsonResponse({"result": "ok"})
        #         else:
        #              raise NameError('Error')
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."}),
        #                             content_type="application/json")

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
                proveedor = Proveedor.objects.get(pk=request.POST['pid'])
                if proveedor.ingresoproducto_set.filter(numerodocumento=request.POST['numero'], tipodocumento__id=int(request.POST['tipodoc'])).exists():
                    return JsonResponse({"result": "bad"})
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    puede_realizar_accion(request, 'sagest.puede_ingresar_compras')
                    data['title'] = u'Nueva compra'
                    data['form'] = IngresoProductoForm()
                    data['form2'] = DetalleIngresoProductoForm()
                    data['form_entidad'] = ProveedorForm()
                    data['valor_iva'] = IVA
                    return render(request, "adm_compras/add.html", data)
                except Exception as ex:
                    pass

            if action == 'detalle_compra':
                try:
                    data['compra'] = compra = IngresoProducto.objects.get(pk=request.GET['cid'])
                    data['detalles'] = compra.productos.all()
                    return render(request, 'adm_compras/detallecompras.html', data)
                except Exception as ex:
                    pass

            # if action == 'anularcompra':
            #     try:
            #         data['title'] = u'Anular Comprobante de Compra'
            #         data['compra'] = IngresoProducto.objects.get(pk=request.GET['id'])
            #         form = AnulacionForm()
            #         data['form'] = form
            #         return render(request, "adm_compras/anularcompra.html", data)
            #     except Exception as ex:
            #         pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Compras de productos'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                compras = IngresoProducto.objects.filter(Q(proveedor__nombre__icontains=search) |
                                                         Q(proveedor__alias__icontains=search) |
                                                         Q(proveedor__identificacion__icontains=search) |
                                                         Q(numerodocumento__icontains=search) |
                                                         Q(descripcion__icontains=search))
            elif 'id' in request.GET:
                ids = request.GET['id']
                compras = IngresoProducto.objects.filter(id=ids)
            else:
                compras = IngresoProducto.objects.all()
            paging = MiPaginador(compras, 25)
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
            data['reporte_0'] = obtener_reporte('comprobante_ingresos')
            data['compras'] = page.object_list
            return render(request, "adm_compras/view.html", data)