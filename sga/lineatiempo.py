# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import ProveedorForm
from sagest.models import Proveedor
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, puede_realizar_accion
from sga.models import ActividadAcademica, LineaTiempo
from datetime import datetime, timedelta

@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_profesor():
        return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    data['profesor'] = profesor = perfilprincipal.profesor
    periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = ProveedorForm(request.POST)
                if f.is_valid():
                    if Proveedor.objects.filter(identificacion=f.cleaned_data['identificacion'].strip()).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un proveedor registrado con ese número de identificacion."})
                    proveedor = Proveedor(identificacion=f.cleaned_data['identificacion'],
                                          nombre=f.cleaned_data['nombre'],
                                          alias=f.cleaned_data['alias'],
                                          pais=f.cleaned_data['pais'],
                                          direccion=f.cleaned_data['direccion'],
                                          telefono=f.cleaned_data['telefono'],
                                          celular=f.cleaned_data['celular'],
                                          email=f.cleaned_data['email'],
                                          fax=f.cleaned_data['fax'])
                    proveedor.save(request)
                    log(u'Adiciono nuevo proveedor: %s' % proveedor, request, "add")
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

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_proveedor')
                    data['title'] = u'Adicionar Proveedor'
                    data['form'] = ProveedorForm()
                    return render(request, "adm_proveedores/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_proveedor')
                    data['title'] = u'Editar Proveedor'
                    data['proveedor'] = proveedor = Proveedor.objects.get(pk=request.GET['id'])
                    form = ProveedorForm(initial={'identificacion': proveedor.identificacion,
                                                  'nombre': proveedor.nombre,
                                                  'alias': proveedor.alias,
                                                  'direccion': proveedor.direccion,
                                                  'pais': proveedor.pais,
                                                  'telefono': proveedor.telefono,
                                                  'celular': proveedor.celular,
                                                  'email': proveedor.email,
                                                  'fax': proveedor.fax})
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_proveedores/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_proveedor')
                    data['title'] = u'Borrar Proveedor'
                    data['proveedor'] = Proveedor.objects.get(pk=request.GET['id'])
                    return render(request, "adm_proveedores/delete.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u''
                data['lineatiempo'] = LineaTiempo.objects.filter(status=True).order_by('anio','mes')
                return render(request, "lineatiempo/view.html", data)
            except Exception as ex:
                pass
