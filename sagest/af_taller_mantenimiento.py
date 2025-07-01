# -*- coding: UTF-8 -*-

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import TallerMantenimientoForm
from sagest.models import TallerMantenimiento
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, puede_realizar_accion


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {'title': u'Talleres de Mantenimiento y Reparación'}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = TallerMantenimientoForm(request.POST)
                if f.is_valid():
                    if TallerMantenimiento.objects.filter(descripcion=f.cleaned_data['descripcion']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un registro con esos datos."})
                    taller = TallerMantenimiento(descripcion=f.cleaned_data['descripcion'],
                                                 observacion=f.cleaned_data['observacion'])
                    taller.save(request)
                    log(u'Adiciono nuevo taller: %s' % taller, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                f = TallerMantenimientoForm(request.POST)
                if f.is_valid():
                    taller = TallerMantenimiento.objects.get(pk=request.POST['id'])
                    if TallerMantenimiento.objects.filter(descripcion=f.cleaned_data['descripcion']).exclude(pk=request.POST['id']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un taller con la misma descripción."})
                    taller.descripcion = f.cleaned_data['descripcion']
                    taller.observacion = f.cleaned_data['observacion']
                    taller.save(request)
                    log(u'Modifico taller: %s' % taller, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delete':
            try:
                taller = TallerMantenimiento.objects.get(pk=request.POST['id'])
                log(u'Elimino taller: %s' % taller, request, "add")
                taller.delete()
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
                    puede_realizar_accion(request, 'sagest.puede_modificar_taller')
                    data['title'] = u'Adicionar taller de mantenimiento'
                    data['form'] = TallerMantenimientoForm()
                    return render(request, 'af_taller_mantenimiento/add.html', data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_taller')
                    data['title'] = u'Modificar taller'
                    data['talleres'] = taller = TallerMantenimiento.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(taller)
                    form = TallerMantenimientoForm(initial=initial)
                    data['form'] = form
                    return render(request, 'af_taller_mantenimiento/edit.html', data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_taller')
                    data['title'] = u'Eliminar taller'
                    data['taller'] = TallerMantenimiento.objects.get(pk=request.GET['id'])
                    return render(request, 'af_taller_mantenimiento/delete.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            search = None
            tipo = None
            if 's' in request.GET:
                search = request.GET['s']
            if search:
                taller = TallerMantenimiento.objects.filter(Q(descripcion__icontains=search))
            else:
                taller = TallerMantenimiento.objects.filter(status=True)
            paging = MiPaginador(taller, 25)
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
            data['talleres'] = page.object_list
            return render(request, "af_taller_mantenimiento/view.html", data)