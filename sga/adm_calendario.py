# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import ActividadForm
from sga.funciones import MiPaginador, log
from sga.models import Actividad

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = ActividadForm(request.POST)
                if f.is_valid():
                    actividad = Actividad(nombre=f.cleaned_data['nombre'],
                                          inicio=f.cleaned_data['fechainicio'],
                                          fin=f.cleaned_data['fechafin'],
                                          tipo=f.cleaned_data['tipo'],
                                          lunes=f.cleaned_data['lunes'],
                                          martes=f.cleaned_data['martes'],
                                          miercoles=f.cleaned_data['miercoles'],
                                          jueves=f.cleaned_data['jueves'],
                                          viernes=f.cleaned_data['viernes'],
                                          sabado=f.cleaned_data['sabado'],
                                          domingo=f.cleaned_data['domingo'])
                    actividad.save(request)
                    log(u'Adiciono actividad al calendario: %s' % actividad, request, "add")
                    return JsonResponse({"result": "ok", "id": actividad.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                actividad = Actividad.objects.get(pk=request.POST['id'])
                f = ActividadForm(request.POST)
                if f.is_valid():
                    actividad.nombre = f.cleaned_data['nombre']
                    actividad.tipo = f.cleaned_data['tipo']
                    actividad.inicio = f.cleaned_data['fechainicio']
                    actividad.fin = f.cleaned_data['fechafin']
                    actividad.lunes = f.cleaned_data['lunes']
                    actividad.martes = f.cleaned_data['martes']
                    actividad.miercoles = f.cleaned_data['miercoles']
                    actividad.jueves = f.cleaned_data['jueves']
                    actividad.viernes = f.cleaned_data['viernes']
                    actividad.sabado = f.cleaned_data['sabado']
                    actividad.domingo = f.cleaned_data['domingo']
                    actividad.save(request)
                    log(u'Modifico actividad al calendario: %s' % actividad, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'del':
            try:
                actividad = Actividad.objects.get(pk=request.POST['id'])
                log(u'Elimino actividad de calendario: %s' % actividad, request, "del")
                actividad.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data = {}
        adduserdata(request, data)
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = U'Adicionar actividad'
                    form = ActividadForm(initial={'fechainicio': datetime.now().date(),
                                                  'fechafin': datetime.now().date()})
                    data['form'] = form
                    return render(request, "adm_calendario/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'del':
                try:
                    data['title'] = u'Eliminar actividad'
                    data['actividad'] = Actividad.objects.get(pk=request.GET['id'])
                    return render(request, "adm_calendario/del.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar actividad'
                    actividad = Actividad.objects.get(pk=request.GET['id'])
                    form = ActividadForm(initial={'nombre': actividad.nombre,
                                                  'tipo': actividad.tipo,
                                                  'fechainicio': actividad.inicio,
                                                  'fechafin': actividad.fin,
                                                  'lunes': actividad.lunes,
                                                  'martes': actividad.martes,
                                                  'miercoles': actividad.miercoles,
                                                  'jueves': actividad.jueves,
                                                  'viernes': actividad.viernes,
                                                  'sabado': actividad.sabado,
                                                  'domingo': actividad.domingo})
                    data['form'] = form
                    data['actividad'] = actividad
                    return render(request, "adm_calendario/edit.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Calendario de actividades de la institución'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                actividades = Actividad.objects.filter(Q(nombre__icontains=search) |
                                                       Q(tipo__nombre__icontains=search)).distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                actividades = Actividad.objects.filter(id=ids)
            else:
                actividades = Actividad.objects.all()
            paging = MiPaginador(actividades, 25)
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
            data['actividades'] = page.object_list
            return render(request, "adm_calendario/view.html", data)