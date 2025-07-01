# -*- coding: latin-1 -*-
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import GrupoForm, UnirGruposForm
from sga.funciones import MiPaginador, log
from sga.models import Grupo


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
                f = GrupoForm(request.POST)
                if f.is_valid():
                    carrera = f.cleaned_data['carrera']
                    sesion = f.cleaned_data['sesion']
                    sede = f.cleaned_data['sede']
                    grupo = Grupo(carrera=carrera,
                                  modalidad=f.cleaned_data['modalidad'],
                                  sesion=sesion,
                                  nombre=f.cleaned_data['nombre'],
                                  sede=sede,
                                  inicio=f.cleaned_data['inicio'],
                                  fin=f.cleaned_data['fin'],
                                  capacidad=f.cleaned_data['capacidad'],
                                  observaciones=f.cleaned_data['observaciones'],
                                  costoinscripcion=f.cleaned_data['costoinscripcion'],
                                  abierto=True)
                    grupo.save(request)
                    log(u'Adicionado grupo: %s' % grupo, request, "add")
                    return JsonResponse({"result": "ok", "id": grupo.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                grupo = Grupo.objects.get(pk=request.POST['id'])
                f = GrupoForm(request.POST)
                if f.is_valid():
                    grupo.nombre = f.cleaned_data['nombre']
                    grupo.inicio = f.cleaned_data['inicio']
                    grupo.fin = f.cleaned_data['fin']
                    grupo.capacidad = f.cleaned_data['capacidad']
                    grupo.observaciones = f.cleaned_data['observaciones']
                    grupo.costoinscripcion = f.cleaned_data['costoinscripcion']
                    grupo.save(request)
                    log(u'Modifico grupo: %s' % grupo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'merge':
            try:
                f = UnirGruposForm(request.POST)
                if f.is_valid():
                    fuente = Grupo.objects.get(pk=request.POST['id'])
                    destino = f.cleaned_data['destino']
                    for ig in fuente.inscripciongrupo_set.all():
                        ig.grupo = destino
                        ig.save(request)
                    destino.capacidad = destino.inscripciongrupo_set.count()
                    fuente.fin = datetime.now().date() - timedelta(1)
                    fuente.save(request)
                    if destino.capacidad < destino.inscripciongrupo_set.count():
                        destino.capacidad = destino.inscripciongrupo_set.count()
                        destino.save(request)
                    log(u'Unifico grupos: %s - %s' % (fuente, destino), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'del':
            try:
                grupo = Grupo.objects.get(pk=request.POST['id'])
                if grupo.inscripciongrupo_set.exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Existen alumnos inscritos en el grupo."})
                log(u'Elimino grupo: %s' % grupo, request, "del")
                grupo.delete()
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
                    data['title'] = u'Adicionar grupo'
                    periodo = request.session['periodo']
                    data['form'] = GrupoForm(initial={'inicio': datetime.now(),
                                                      'fin': periodo.fin})
                    data['periodo'] = periodo
                    return render(request, "adm_grupos/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar grupo'
                    grupo = Grupo.objects.get(pk=request.GET['id'])
                    form = GrupoForm(initial={'carrera': grupo.carrera,
                                              'modalidad': grupo.modalidad,
                                              'sesion': grupo.sesion,
                                              'nombre': grupo.nombre,
                                              'sede': grupo.sede,
                                              'inicio': grupo.inicio,
                                              'fin': grupo.fin,
                                              'capacidad': grupo.capacidad,
                                              'costoinscripcion': grupo.costoinscripcion,
                                              'observaciones': grupo.observaciones})
                    form.editar()
                    data['form'] = form
                    data['grupo'] = grupo
                    return render(request, "adm_grupos/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'merge':
                try:
                    data['title'] = u'Unir grupos'
                    grupoinicial = Grupo.objects.get(pk=request.GET['id'])
                    form = UnirGruposForm(initial={'fuente': grupoinicial})
                    form.sin_origen(grupoinicial)
                    data['form'] = form
                    data['grupo'] = grupoinicial
                    return render(request, "adm_grupos/merge.html", data)
                except Exception as ex:
                    pass

            elif action == 'cerrar':
                try:
                    grupo = Grupo.objects.get(pk=request.GET['id'])
                    grupo.capacidad = grupo.inscripciongrupo_set.all().count()
                    grupo.save(request)
                    return HttpResponseRedirect("/adm_grupos?id=" + request.GET['id'])
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'del':
                try:
                    data['title'] = 'Borrar Grupo'
                    if 'formerror' in request.GET:
                        data['formerror'] = request.GET['formerror']
                        if 'formerrordata' in request.GET:
                            data['formerrordata'] = request.GET['formerrordata']
                    data['grupo'] = Grupo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_grupos/del.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Listado de grupos de alumnos'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                grupos = Grupo.objects.filter(Q(nombre__icontains=search) |
                                              Q(carrera__nombre__icontains=search) |
                                              Q(modalidad__nombre__icontains=search) |
                                              Q(sesion__nombre__icontains=search)).order_by('-nombre').distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                grupos = Grupo.objects.filter(id=ids)
            else:
                grupos = Grupo.objects.all().order_by('-nombre').distinct()
            paging = MiPaginador(grupos, 25)
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
            data['grupos'] = page.object_list
            data['reporte_0'] = obtener_reporte('lista_alumnos_inscritos')
            return render(request, "adm_grupos/view.html", data)