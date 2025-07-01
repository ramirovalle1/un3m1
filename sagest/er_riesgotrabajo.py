# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import RiesgoTrabajoForm
from sagest.models import RiesgoTrabajo
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {'title': u'Riesgos de Accidente de Trabajo y Enfermedades Profesionales'}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = RiesgoTrabajoForm(request.POST)
                if f.is_valid():
                    if RiesgoTrabajo.objects.filter(codigo=f.cleaned_data['codigo'], status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un riesgo de trabajo con el mismo código."})
                    if RiesgoTrabajo.objects.filter(descripcion=f.cleaned_data['descripcion'], status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La descripción ya existe."})
                    riesgotrabajo = RiesgoTrabajo(codigo=f.cleaned_data['codigo'],
                                                  descripcion=f.cleaned_data['descripcion'])
                    riesgotrabajo.save(request)
                    log(u'Adicionó un risgo de trabajo: %s' % riesgotrabajo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                riesgotrabajo = RiesgoTrabajo.objects.get(pk=request.POST['id'])
                f = RiesgoTrabajoForm(request.POST)
                if f.is_valid():

                    if f.cleaned_data['codigo']:
                        if RiesgoTrabajo.objects.filter(codigo=f.cleaned_data['codigo'], status=True).exclude(pk=request.POST['id']).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe un riesgo de trabajo con el mismo código."})
                        else:
                            if RiesgoTrabajo.objects.filter(descripcion=f.cleaned_data['descripcion'], status=True).exclude(pk=request.POST['id']).exists():
                                return JsonResponse({"result": "bad", "mensaje": u"La descripción ya existe."})
                            else:
                                if RiesgoTrabajo.objects.filter(descripcion=f.cleaned_data['descripcion'], status=True).exclude(pk=request.POST['id']).exists():
                                    return JsonResponse({"result": "bad", "mensaje": u"La descripción ya existe."})
                                if f.cleaned_data['codigo']:
                                    riesgotrabajo.codigo = f.cleaned_data['codigo']
                                riesgotrabajo.descripcion = f.cleaned_data['descripcion']
                                riesgotrabajo.save(request)
                                log(u'Editó traspaso custio de  activo: %s' % riesgotrabajo, request, "add")
                                return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delete':
            try:
                riesgotrabajo = RiesgoTrabajo.objects.get(pk=request.POST['id'])
                riesgotrabajo.status = False
                riesgotrabajo.save(request)
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
                    data['title'] = u'Riesgos de Accidente de Trabajo y Enfermedades Profesionales'
                    data['form'] = RiesgoTrabajoForm()
                    return render(request, 'er_riesgotrabajo/add.html', data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Modificar Riesgo de Accidente de Trabajo y Enfermedad Profesional'
                    data['riesgotrabajo'] = riesgotrabajo = RiesgoTrabajo.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(riesgotrabajo)
                    form = RiesgoTrabajoForm(initial=initial)
                    if riesgotrabajo.en_uso():
                        form.editar()
                    data['form'] = form
                    return render(request, 'er_riesgotrabajo/edit.html', data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar Riesgo de Accidente de Trabajo y Enfermedad Profesional'
                    data['riesgotrabajo'] = RiesgoTrabajo.objects.get(pk=request.GET['id'])
                    return render(request, 'er_riesgotrabajo/delete.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            search = None
            tipo = None

            if 's' in request.GET:
                search = request.GET['s']
            if search:
                riesgotrabajo = RiesgoTrabajo.objects.filter(Q(codigo__icontains=search, status=True) |
                                                             Q(descripcion__icontains=search, status=True))
            else:
                riesgotrabajo = RiesgoTrabajo.objects.filter(status=True)

            paging = MiPaginador(riesgotrabajo, 25)
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
            data['riesgostrabajo'] = page.object_list
            return render(request, "er_riesgotrabajo/view.html", data)
