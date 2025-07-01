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
from sagest.forms import ProveedorForm, SuministroForm, DetalleSuministroProductoForm
from sagest.models import Producto, Proveedor, SuministroProducto, DetalleSuministroProducto
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import log, MiPaginador, puede_realizar_accion


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
                f = SuministroForm(request.POST)
                if f.is_valid():
                    datos = json.loads(request.POST['lista_items1'])
                    ingresoprod = SuministroProducto(proveedor=f.cleaned_data['proveedor'],
                                                  tipodocumento=f.cleaned_data['tipodocumento'],
                                                  numerodocumento=f.cleaned_data['numerodocumento'],
                                                  fechadocumento=f.cleaned_data['fechadocumento'],
                                                  ordencompra=f.cleaned_data['ordencompra'],
                                                  solicitudcompra=f.cleaned_data['solicitudcompra'],
                                                  descripcion=f.cleaned_data['descripcion'],
                                                  fechaoperacion=datetime.now())
                    ingresoprod.save(request)
                    # ITEMS
                    for d in datos:
                        producto = Producto.objects.get(pk=int(d['id']))
                        detalleingprod = DetalleSuministroProducto(producto=producto,
                                                                   cantidad=Decimal(d['cantidad']).quantize(Decimal('.0001')),
                                                                   estado_id=int(d['estado']))
                        detalleingprod.save(request)
                        ingresoprod.productos.add(detalleingprod)
                    ingresoprod.save(request)
                    log(u'Adiciono nuevo suministro de inventario: %s' % ingresoprod, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

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
                if proveedor.suministroproducto_set.filter(numerodocumento=request.POST['numero'], tipodocumento__id=int(request.POST['tipodoc'])).exists():
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
                    puede_realizar_accion(request, 'sagest.puede_ingresar_sumistro')
                    data['title'] = u'Nuevo Ingreso de Suministro'
                    data['form'] = SuministroForm()
                    data['form2'] = DetalleSuministroProductoForm()
                    data['form_entidad'] = ProveedorForm()
                    return render(request, "adm_suministro/add.html", data)
                except Exception as ex:
                    pass

            if action == 'detalle_compra':
                try:
                    data['compra'] = compra = SuministroProducto.objects.get(pk=request.GET['cid'])
                    data['detalles'] = compra.productos.all()
                    return render(request, 'adm_suministro/detallecompras.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Suministro de productos'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                compras = SuministroProducto.objects.filter(Q(proveedor__nombre__icontains=search) |
                                                         Q(proveedor__alias__icontains=search) |
                                                         Q(proveedor__identificacion__icontains=search) |
                                                         Q(numerodocumento__icontains=search) |
                                                         Q(descripcion__icontains=search))
            elif 'id' in request.GET:
                ids = request.GET['id']
                compras = SuministroProducto.objects.filter(id=ids)
            else:
                compras = SuministroProducto.objects.all()
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
            data['reporte_0'] = obtener_reporte('comprobante_suministro')
            data['compras'] = page.object_list
            return render(request, "adm_suministro/view.html", data)