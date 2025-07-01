# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import ProveedorForm, IngresoSalidaObrasForm
from sagest.models import Proveedor, IngresoSalidaObras, Producto
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, puede_realizar_accion
from django.forms import model_to_dict
from datetime import datetime
from django.template.loader import get_template
from django.template import Context

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
                f = IngresoSalidaObrasForm(request.POST)
                if f.is_valid():
                    producto = Producto.objects.get(id=f.cleaned_data['producto'])
                    saldo=None
                    if f.cleaned_data['cantidad'] <=0:
                        return JsonResponse({"result": "bad", "mensaje": u"Ingrese una cantidad mayor a cero."})
                    if producto.ingresosalidaobras_set.filter(status=True, producto=producto).exists():
                        ultimoregistro = producto.ingresosalidaobras_set.filter(status=True, producto=producto)[0]
                        if f.cleaned_data['tipomovimiento'] == '1':
                            saldo = ultimoregistro.saldo + f.cleaned_data['cantidad']
                        elif ultimoregistro.saldo > 0 and ultimoregistro.saldo>=f.cleaned_data['cantidad']:
                            saldo = ultimoregistro.saldo - f.cleaned_data['cantidad']
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error no tiene saldo disponible."})
                    else:
                        if f.cleaned_data['tipomovimiento'] == '2':
                            return JsonResponse({"result": "bad", "mensaje": u"Error no tiene saldo disponible."})
                        saldo = f.cleaned_data['cantidad']
                    ingresosalida = IngresoSalidaObras(producto=producto,
                                                   tipomovimiento=f.cleaned_data['tipomovimiento'],
                                                   cantidad=f.cleaned_data['cantidad'],
                                                   fecha=datetime.now(),saldo=saldo)
                    ingresosalida.save(request)
                    log(u'Adiciono nuevo movimiento: %s' % ingresosalida, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                proveedor = Proveedor.objects.get(pk=request.POST['id'])
                f = ProveedorForm(request.POST)
                if f.is_valid():
                    proveedor.alias = f.cleaned_data['alias']
                    proveedor.direccion = f.cleaned_data['direccion']
                    proveedor.pais = f.cleaned_data['pais']
                    proveedor.telefono = f.cleaned_data['telefono']
                    proveedor.celular = f.cleaned_data['celular']
                    proveedor.email = f.cleaned_data['email']
                    proveedor.fax = f.cleaned_data['fax']
                    proveedor.save(request)
                    log(u'Modificó proveedor: %s' % proveedor, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delete':
            try:
                proveedor = Proveedor.objects.get(pk=request.POST['id'])
                if proveedor.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"El proveedor se encuentra en uso, no es posible eliminar."})
                log(u'Eliminó proveedor: %s' % proveedor, request, "del")
                proveedor.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'detalle_producto':
            try:
                data['producto'] = producto = Producto.objects.get(pk=int(request.POST['id']))
                data['registros'] = producto.ingresosalidaobras_set.filter(status=True).order_by('-id')
                template = get_template("entradasalidaobras/detalle_producto.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar Movimiento'
                    data['form'] = IngresoSalidaObrasForm()
                    return render(request, "entradasalidaobras/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar Movimiento'
                    data['ingresossalida'] = ingresosalida = IngresoSalidaObras.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(ingresosalida)
                    form = IngresoSalidaObrasForm(initial=initial)
                    data['form'] = form
                    return render(request, "entradasalidaobras/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'delete':
                try:
                    data['title'] = u'Borrar Movimiento'
                    data['ingresossalida'] = IngresoSalidaObras.objects.get(pk=request.GET['id'])
                    return render(request, "entradasalidaobras/delete.html", data)
                except Exception as ex:
                    pass

            elif action == 'buscarproducto':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__() == 1:
                        producto = Producto.objects.filter(Q(codigo__icontains=q) | Q(descripcion__icontains=s[0]) | Q(descripcion__icontains=q),status=True).distinct()[:20]
                    else:
                        producto = Producto.objects.filter((Q(codigo__icontains=s[0])& Q(codigo__icontains=s[1]))|
                                                           (Q(descripcion__icontains=s[0]) & Q(descripcion__icontains=s[1]))).filter(status=True).distinct()[:20]
                    data = {"result": "ok","results": [{"id": x.id, "name": x.flexbox_reprprod()} for x in producto]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Inventario Suministros Obras'
                search = None
                ids = None
                inventarios=IngresoSalidaObras.objects.filter(status=True).values_list('producto__id', flat=True)
                if 's' in request.GET:
                    search = request.GET['s']
                if search:
                    productos = Producto.objects.filter(Q(descripcion__icontains=search) |
                                                           Q(codigo__icontains=search), id__in=inventarios).distinct()
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    productos = Producto.objects.filter(id=ids, id__in=inventarios).distinct()
                else:
                    productos = Producto.objects.filter(status=True, id__in=inventarios).distinct()
                paging = MiPaginador(productos, 20)
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
                data['inventarios'] = page.object_list
                return render(request, "entradasalidaobras/view.html", data)
            except Exception as ex:
                pass
