# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import UbicacionForm
from sagest.models import Ubicacion
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, puede_realizar_accion


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = UbicacionForm(request.POST)
                if f.is_valid():
                    if Ubicacion.objects.filter(nombre=f.cleaned_data['nombre']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El registro ya existe."})
                    if Ubicacion.objects.filter(codigo=f.cleaned_data['codigo'].strip()).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El registro ya existe."})
                    ubicacion = Ubicacion(codigo=f.cleaned_data['codigo'],
                                          nombre=f.cleaned_data['nombre'],
                                          observacion=f.cleaned_data['observacion'],
                                          responsable=f.cleaned_data['responsable'])
                    ubicacion.save(request)
                    log(u'Adiciono nueva ubicacion: %s' % ubicacion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                f = UbicacionForm(request.POST)
                if f.is_valid():
                    ubicacion = Ubicacion.objects.get(pk=request.POST['id'])
                    if Ubicacion.objects.filter(Q(nombre=f.cleaned_data['nombre']) | Q(codigo=f.cleaned_data['codigo'])).exclude(id=ubicacion.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El registro ya existe."})
                    ubicacion.codigo = f.cleaned_data['codigo']
                    ubicacion.nombre = f.cleaned_data['nombre']
                    ubicacion.observacion = f.cleaned_data['observacion']
                    ubicacion.responsable = f.cleaned_data['responsable']
                    ubicacion.save(request)
                    log(u'Modifico ubicacion: %s' % ubicacion, request, "edit")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editresponsable':
            try:
                f = UbicacionForm(request.POST)
                if f.is_valid():
                    ubicacion = Ubicacion.objects.get(pk=request.POST['id'])
                    ubicacion.responsable = f.cleaned_data['responsable']
                    ubicacion.save(request)
                    log(u'Modifico responsable de ubicación: %s' % ubicacion, request, "edit")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delete':
            try:
                ubicacion = Ubicacion.objects.get(pk=request.POST['id'])
                if ubicacion.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"El registro esta en uso."})
                log(u'Elimino ubicacion: %s' % ubicacion, request, "del")
                ubicacion.delete()
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
                    puede_realizar_accion(request, 'sagest.puede_modificar_ubicacion')
                    data['title'] = u'Adicionar nueva ubicación'
                    data['form'] = UbicacionForm()
                    return render(request, 'af_ubicacion/add.html', data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_ubicacion')
                    data['title'] = u'Modificar Ubicación'
                    data['ubicaciones'] = ubicacion = Ubicacion.objects.get(pk=request.GET['id'])
                    form = UbicacionForm(initial={'codigo': ubicacion.codigo,
                                                  'nombre': ubicacion.nombre,
                                                  'observacion': ubicacion.observacion,
                                                  'responsable': ubicacion.responsable})
                    data['form'] = form
                    return render(request, 'af_ubicacion/edit.html', data)
                except Exception as ex:
                    pass

            if action == 'editresponsable':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_ubicacion')
                    data['title'] = u'Modificar Responsable'
                    data['ubicaciones'] = ubicacion = Ubicacion.objects.get(pk=request.GET['id'])
                    form = UbicacionForm(initial={'responsable': ubicacion.responsable})
                    form.solo_responsable()
                    data['form'] = form
                    return render(request, 'af_ubicacion/editresponsable.html', data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_ubicacion')
                    data['title'] = u'Eliminar Ubicación'
                    data['ubicacion'] = Ubicacion.objects.get(pk=request.GET['id'])
                    return render(request, 'af_ubicacion/delete.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Ubicaciones de activos'
            search = None
            tipo = None
            if 's' in request.GET:
                search = request.GET['s']
                ubicacion = Ubicacion.objects.filter(Q(codigo__icontains=search) | Q(nombre__icontains=search, status=True)).distinct()
            else:
                ubicacion = Ubicacion.objects.filter(status=True).distinct()
            paging = MiPaginador(ubicacion, 25)
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
            data['ubicaciones'] = page.object_list
            return render(request, "af_ubicacion/view.html", data)