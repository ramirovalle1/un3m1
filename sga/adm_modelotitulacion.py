# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import ModeloTitulacionForm
from sga.funciones import log
from sga.models import ModeloTitulacion


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'add':
            try:
                form = ModeloTitulacionForm(request.POST)
                if form.is_valid():
                    nombres=form.cleaned_data['nombre']
                    if not ModeloTitulacion.objects.filter(nombre=nombres, status=True).exists():
                        modelo=ModeloTitulacion(nombre=form.cleaned_data['nombre'],
                                                horaspresencial=int(form.cleaned_data['horaspresencial']),
                                                horasvirtual=int(form.cleaned_data['horasvirtual']),
                                                horasautonoma=int(form.cleaned_data['horasautonoma']),
                                                clases=form.cleaned_data['clases'],
                                                acompanamiento=form.cleaned_data['acompanamiento']
                                                )
                        modelo.save(request)
                        log(u'Agrego Modelo de Titulación: %s' % modelo, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editar':
            try:
                modelo = ModeloTitulacion.objects.get(pk=int(request.POST['id']))
                form = ModeloTitulacionForm(request.POST)
                if form.is_valid():
                    if modelo.tiene_alternativa_activas():
                        modelo.nombre = form.cleaned_data['nombre']
                    else:
                        modelo.nombre=form.cleaned_data['nombre']
                        modelo.horaspresencial = int (form.cleaned_data['horaspresencial'])
                        modelo.horasvirtual = int(form.cleaned_data['horasvirtual'])
                        modelo.horasautonoma = int(form.cleaned_data['horasautonoma'])
                    modelo.acompanamiento = form.cleaned_data['acompanamiento']
                    modelo.clases = form.cleaned_data['clases']
                    modelo.save(request)
                    log(u'Editar Modelo de Titulación: %s' % modelo, request, "editar")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Faltan campos de llenar."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action=='eliminar':
            try:
                modelo = ModeloTitulacion.objects.get(pk=int(request.POST['id']))
                if not modelo.tiene_alternativa_activas():
                    modelo.status= False
                    modelo.save(request)
                    log(u'Elimino Modelo de Titulación: %s' % modelo, request, "del")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede Eliminar el Modelo de Titulacion, tiene Alternativa de Titulacion proceso.."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})
        return HttpResponseRedirect(request.path)

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'add':
                try:
                    data['title'] = u'Modelo de Titulación'
                    data['form'] = ModeloTitulacionForm()
                    return render(request, "adm_modelotitulacion/add.html", data)
                except Exception as ex:
                    pass

            if action=='eliminar':
                try:
                    data['title'] = u'Eliminar Modelo de Titulación'
                    data['modelo'] = ModeloTitulacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_modelotitulacion/eliminar.html", data)
                except Exception as ex:
                    pass
            if action == 'editar':
                try:
                    data['title'] = u'Editar Modelo de Titulación'
                    data['modelo'] = modelo=ModeloTitulacion.objects.get(pk=int(request.GET['id']))
                    form = ModeloTitulacionForm(initial={'nombre':modelo.nombre,
                                                                 'horaspresencial':modelo.horaspresencial,
                                                                 'horasvirtual': modelo.horasvirtual,
                                                                 'horasautonoma': modelo.horasautonoma,
                                                                 'clases': modelo.clases,
                                                                 'acompanamiento': modelo.acompanamiento
                                                                 })
                    if modelo.tiene_alternativa_activas():
                        form.editar()
                    data['form']= form
                    return render(request, "adm_modelotitulacion/editar.html", data)
                except Exception as ex:
                    pass
            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Modelo de Titulación'
            data['modelo'] = ModeloTitulacion.objects.filter(status=True).order_by('nombre')
            return render(request, "adm_modelotitulacion/view.html", data)