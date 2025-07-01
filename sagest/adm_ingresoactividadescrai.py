# -*- coding: UTF-8 -*-
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from decorators import secure_module
from sagest.forms import IngresoActividadesCraiForm, TipoActividadCraiForm
from sagest.models import IngresoActividadesCrai, TipoActividadCrai
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    tipo_mundo = 0
    if request.user.has_perm('sagest.es_biblioteca'):
        tipo_mundo = 1
    if request.user.has_perm('sagest.es_docencia'):
        tipo_mundo = 2
    if request.user.has_perm('sagest.es_investigacion'):
        tipo_mundo = 3
    if request.user.has_perm('sagest.es_cultural'):
        tipo_mundo = 4

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            f = IngresoActividadesCraiForm(request.POST)
            if f.is_valid():
                try:
                    tipo_atencion = ""
                    if int(request.POST['tipoactividad']) == 1:
                        tipo_atencion = "Estudiante"
                        ingresoactividadescrai = IngresoActividadesCrai(tipoactividadcrai=f.cleaned_data['tipoactividadcrai'],
                                                                        inscripcion_id=f.cleaned_data['inscripcion'],
                                                                        fecha=datetime.now().date(),
                                                                        actividad=f.cleaned_data['actividad'])
                    else:
                        if int(request.POST['tipoactividad']) == 2:
                            tipo_atencion = "Profesor"
                            ingresoactividadescrai = IngresoActividadesCrai(tipoactividadcrai=f.cleaned_data['tipoactividadcrai'],
                                                                            profesor_id=f.cleaned_data['profesor'],
                                                                            fecha=datetime.now().date(),
                                                                            actividad=f.cleaned_data['actividad'])
                        else:
                            tipo_atencion = "Administrativo"
                            ingresoactividadescrai = IngresoActividadesCrai(tipoactividadcrai=f.cleaned_data['tipoactividadcrai'],
                                                                            administrativo_id=f.cleaned_data['administrativo'],
                                                                            fecha=datetime.now().date(),
                                                                            actividad=f.cleaned_data['actividad'])
                    ingresoactividadescrai.save(request)
                    log(u'Adiciono Ingreso Actividad: %s' % ingresoactividadescrai, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            else:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addtipo':
            f = TipoActividadCraiForm(request.POST)
            if f.is_valid():
                try:
                    tipoactividadcrai = TipoActividadCrai(tipo=f.cleaned_data['tipo'],
                                                          descripcion=f.cleaned_data['descripcion'])
                    tipoactividadcrai.save(request)
                    log(u'Adiciono Tipo Actividad: %s' % tipoactividadcrai, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            else:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            ingresoactividadescrai = IngresoActividadesCrai.objects.get(pk=request.POST['id'])
            f = IngresoActividadesCraiForm(request.POST)
            if f.is_valid():
                try:
                    ingresoactividadescrai.tipoactividadcrai = f.cleaned_data['tipoactividadcrai']
                    tipo_atencion = ""
                    if int(request.POST['tipoactividad']) == 1:
                        ingresoactividadescrai.inscripcion_id = f.cleaned_data['inscripcion']
                    else:
                        if int(request.POST['tipoactividad']) == 2:
                            ingresoactividadescrai.profesor_id = f.cleaned_data['profesor']
                        else:
                            ingresoactividadescrai.administrativo_id = f.cleaned_data['administrativo']
                    ingresoactividadescrai.actividad = f.cleaned_data['actividad']
                    ingresoactividadescrai.save(request)
                    log(u'Editó Ingreso Actividad: %s' % ingresoactividadescrai, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            else:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edittipo':
            tipoactividadcrai = TipoActividadCrai.objects.get(pk=request.POST['id'])
            f = TipoActividadCraiForm(request.POST)
            if f.is_valid():
                try:
                    tipoactividadcrai.descripcion = f.cleaned_data['descripcion']
                    tipoactividadcrai.save(request)
                    log(u'Editó Tipo Actividad: %s' % tipoactividadcrai, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            else:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delete':
            try:
                ingresoactividadescrai = IngresoActividadesCrai.objects.get(pk=request.POST['id'])
                ingresoactividadescrai.status=False
                ingresoactividadescrai.save(request)
                log(u'Eliminó Ingreso Actividad: %s' % ingresoactividadescrai, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deletetipo':
            try:
                tipoactividadcrai = TipoActividadCrai.objects.get(pk=request.POST['id'])
                tipoactividadcrai.status=False
                tipoactividadcrai.save(request)
                log(u'Eliminó Tipo Actividad: %s' % tipoactividadcrai, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Ingresar Actividad'
                    data['tipoactividad'] = int(request.GET['tipoactividad'])
                    form = IngresoActividadesCraiForm()
                    form.add(tipo_mundo)
                    data['form'] = form
                    return render(request, 'adm_ingresoactividadescrai/add.html', data)
                except Exception as ex:
                    pass

            if action == 'addtipo':
                try:
                    data['title'] = u'Ingresar Tipo Actividad'
                    data['form'] = TipoActividadCraiForm()
                    return render(request, 'adm_ingresoactividadescrai/addtipo.html', data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Modificar Actividad'
                    data['ingresoactividadescrai'] = ingresoactividadescrai = IngresoActividadesCrai.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(ingresoactividadescrai)
                    form = IngresoActividadesCraiForm(initial=initial)
                    form.edit(tipo_mundo,ingresoactividadescrai)
                    data['form'] = form
                    data['tipoactividad'] = ingresoactividadescrai.tipoactividad()
                    return render(request, 'adm_ingresoactividadescrai/edit.html', data)
                except Exception as ex:
                    pass

            if action == 'edittipo':
                try:
                    data['title'] = u'Modificar Tipo Actividad'
                    data['tipoactividadcrai'] = tipoactividadcrai = TipoActividadCrai.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(tipoactividadcrai)
                    form = TipoActividadCraiForm(initial=initial)
                    form.editar()
                    data['form'] = form
                    return render(request, 'adm_ingresoactividadescrai/edittipo.html', data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar Actividad'
                    data['ingresoactividadescrai'] = IngresoActividadesCrai.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_ingresoactividadescrai/delete.html', data)
                except Exception as ex:
                    pass

            if action == 'deletetipo':
                try:
                    data['title'] = u'Eliminar Tipo Actividad'
                    data['tipoactividadcrai'] = TipoActividadCrai.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_ingresoactividadescrai/deletetipo.html', data)
                except Exception as ex:
                    pass

            if action == 'tipo':
                try:
                    data['title'] = u'Tipo de Actividades'
                    data['tipoactividadcrais'] = TipoActividadCrai.objects.filter(status=True, tipo=tipo_mundo).order_by('tipo')
                    return render(request, "adm_ingresoactividadescrai/tipo.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Ingreso Actividades'
            search = None
            tipo = None

            if 't' in request.GET:
                tipo = request.GET['t']
                data['tipoid'] = int(tipo) if tipo else ""

            if 's' in request.GET:
                search = request.GET['s']
            if search:
                ingresoactividadescrais = IngresoActividadesCrai.objects.filter((Q(cuenta__icontains=search) |
                                                        Q(descripcion__icontains=search) |
                                                        Q(tipo__nombre__icontains=search)), status=True, tipoactividadcrai__tipo=tipo_mundo).order_by('-id')
            elif tipo:
                ingresoactividadescrais = IngresoActividadesCrai.objects.filter(tipoactividadcrai__id=tipo, tipoactividadcrai__tipo=tipo_mundo).order_by('-id')
            else:
                ingresoactividadescrais = IngresoActividadesCrai.objects.filter(status=True, tipoactividadcrai__tipo=tipo_mundo).order_by('-id')

            paging = MiPaginador(ingresoactividadescrais, 25)
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
            data['tipos'] = TipoActividadCrai.objects.filter(status=True, tipo=tipo_mundo)
            data['ingresoactividadescrais'] = page.object_list
            return render(request, "adm_ingresoactividadescrai/view.html", data)
