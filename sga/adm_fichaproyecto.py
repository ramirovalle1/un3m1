# -*- coding: latin-1 -*-
import json
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import  FichaProyectoForm
from sga.funciones import log
from sga.models import FichaProyecto


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()

def view(request):
    global ex
    data = {}
    adduserdata(request, data)

    if request.method == 'POST':
        action = request.POST['action']
        if action == 'add':
            try:
                form = FichaProyectoForm(request.POST)
                if form.is_valid():
                    nivel=form.cleaned_data['nivel']
                    nombres=form.cleaned_data['nombre']
                    if not FichaProyecto.objects.values('id').filter(Q(nivel=nivel) | Q(nombre=nombres), estado=True).exists():
                        ficha=FichaProyecto(nombre=nombres,
                                            descripcion=form.cleaned_data['descripcion'],
                                            nivel=form.cleaned_data['nivel'],
                                            estado=True)
                        ficha.save(request)
                        log(u'Agregar Ficha Proyecto: %s' % ficha, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre o el nivel ya existe."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action=='editar':
            try:
                ficha = FichaProyecto.objects.get(pk=int(request.POST['id']))
                form = FichaProyectoForm(request.POST)
                if form.is_valid():
                    nivel= form.cleaned_data['nivel']
                    nombre = form.cleaned_data['nombre']
                    id= request.POST['id']
                    if ficha.no_ficha(nombre, nivel, id):
                        ficha.nombre=form.cleaned_data['nombre']
                        ficha.descripcion=form.cleaned_data['descripcion']
                        ficha.nivel = form.cleaned_data['nivel']
                        ficha.estado=True
                        ficha.save(request)
                    else:
                        return HttpResponse(
                            json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos estan repetidos."}),
                            content_type="application/json")
                else:
                     raise NameError('Error')
                log(u'Editar Calificación: %s' % ficha, request, "editar")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action=='eliminar':
                try:
                    ficha = FichaProyecto.objects.get(pk=int(request.POST['id']))
                    #log(u'Elimino tutoria: %s' % ficha, request, "del")
                    ficha.estado= False
                    ficha.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})
        return HttpResponseRedirect(request.path)

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'add':
                try:
                    data['title'] = u'Agregar Ficha Proyecto'
                    data['form'] = FichaProyectoForm()
                    return render(request, "adm_fichaproyecto/fichaproyecto.html", data)
                except Exception as ex:
                    pass

            if action=='eliminar':
                try:
                    data['title'] = u'Eliminar Ficha'
                    data['ficha'] = FichaProyecto.objects.get(pk=request.GET['id'])
                    return render(request, "adm_fichaproyecto/eliminar.html", data)
                except Exception as ex:
                    pass
            if action == 'editar':
                    try:
                        data['title'] = u'Editar Ficha'
                        data['ficha'] = ficha=FichaProyecto.objects.get(pk=request.GET['id'])
                        data['form'] = FichaProyectoForm(initial={'nombre':ficha.nombre,'nivel':ficha.nivel, 'descripcion':ficha.descripcion})
                        return render(request, "adm_fichaproyecto/editarficha.html", data)
                    except Exception as ex:
                        pass
            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Ficha Proyecto'
            data['ficha'] = FichaProyecto.objects.filter(estado=True).order_by('nivel')
            return render(request, "adm_fichaproyecto/view.html", data)
