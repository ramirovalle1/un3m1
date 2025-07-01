# -*- coding: UTF-8 -*-
from googletrans import Translator
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import AgenteRiesgoForm
from sagest.models import AgenteRiesgo, AgenteRiesgoRiesgo
from sga.commonviews import adduserdata
from sga.funciones import log, MiPaginador


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = AgenteRiesgoForm(request.POST)
                if f.is_valid():
                    if AgenteRiesgo.objects.filter(codigo=f.cleaned_data['codigo'], status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El código del agente ya existe"})
                    subgrupo = f.cleaned_data['subgrupo']
                    if subgrupo == '':
                        subgrupo = None
                    agente = AgenteRiesgo(grupo=f.cleaned_data['grupo'],
                                          subgrupo=subgrupo,
                                          apartado=f.cleaned_data['apartado'],
                                          codigo=f.cleaned_data['codigo'],
                                          descripcion=f.cleaned_data['descripcion'])

                    agente.save(request)
                    if len(request.POST['listariesgo']):
                        items = request.POST['listariesgo']
                        for d in items.split(';'):
                            agentedetalle = AgenteRiesgoRiesgo(agente=agente,
                                                               riesgo_id=int(d.split(':')[0]),
                                                               medida=d.split(':')[1])
                            agentedetalle.save(request)
                    log(u'Adiciono un nuevo agente de riesgo: %s' % agente, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        elif action == 'edit':
            try:
                agente = AgenteRiesgo.objects.get(pk=request.POST['id'])

                f = AgenteRiesgoForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['codigo']:
                        if AgenteRiesgo.objects.filter(codigo=f.cleaned_data['codigo'], status=True).exclude(pk=agente.id).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El código del agente ya existe"})
                    subgrupo = f.cleaned_data['subgrupo']
                    if subgrupo == '':
                        subgrupo = None
                    detallemanipulado = request.POST['detallemanipulado']
                    if f.cleaned_data['grupo']:
                        agente.grupo = f.cleaned_data['grupo']
                        agente.subgrupo = subgrupo
                        agente.codigo = f.cleaned_data['codigo']
                    agente.apartado = f.cleaned_data['apartado']
                    agente.descripcion = f.cleaned_data['descripcion']
                    agente.save(request)
                    if detallemanipulado == 'SI':
                        # Si hay items a eliminar
                        if len(request.POST['listaeliminar']):
                            itemsborrar = request.POST['listaeliminar']
                            for ib in itemsborrar.split(';'):
                                idriesgo = ib[0]
                                agentedetalle = agente.agenteriesgoriesgo_set.get(riesgo_id=int(idriesgo), status=True)
                                agentedetalle.status = False
                                agentedetalle.save(request)
                        # Si hay items en el detalle
                        if len(request.POST['listariesgo']):
                            items = request.POST['listariesgo']
                            for d in items.split(';'):
                                acciondetalle = d.split(':')[2]
                                # Si accion es Insert
                                if acciondetalle == "I":
                                    agentedetalle = AgenteRiesgoRiesgo(agente=agente,
                                                                       riesgo_id=int(d.split(':')[0]),
                                                                       medida=d.split(':')[1])
                                    agentedetalle.save(request)
                                else:
                                    agentedetalle = agente.agenteriesgoriesgo_set.get(riesgo_id=int(d.split(':')[0]), status=True)
                                    agentedetalle.medida = d.split(':')[1]
                                    agentedetalle.save(request)
                    log(u'Actualizo un agente de riesgo: %s' % agente, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "mensaje": translator.translate(ex.__str__(),'es').text})

        elif action == 'delete':
            try:
                agente = AgenteRiesgo.objects.get(pk=request.POST['id'])
                agente.status = False
                agente.save(request)
                agente.agenteriesgoriesgo_set.update(status=False)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Agentes de Riesgo'
                    data['form'] = AgenteRiesgoForm()
                    return render(request, 'er_agenteriesgo/add.html', data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Modificar Agente de Riesgo'
                    data['agenteriesgo'] = agenteriesgo = AgenteRiesgo.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(agenteriesgo)
                    form = AgenteRiesgoForm(initial=initial)

                    if agenteriesgo.en_uso():
                        form.editar()

                    data['form'] = form
                    return render(request, 'er_agenteriesgo/edit.html', data)

                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar Agente de Riesgo'
                    data['agenteriesgo'] = AgenteRiesgo.objects.get(pk=request.GET['id'])
                    return render(request, 'er_agenteriesgo/delete2.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Agentes de Riesgo'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                agentes = AgenteRiesgo.objects.filter(Q(codigo__icontains=search, status=True) |
                                                      Q(descripcion__icontains=search, status=True) |
                                                      Q(grupo__descripcion__contains=search, status=True) |
                                                      Q(subgrupo__descripcion__contains=search, status=True) |
                                                      Q(apartado__contains=search, status=True))
            elif 'id' in request.GET:
                ids = request.GET['id']
                agentes = AgenteRiesgo.objects.filter(id=ids)
            else:
                agentes = AgenteRiesgo.objects.filter(status=True)
            paging = MiPaginador(agentes, 25)
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
            data['agentes'] = page.object_list
            return render(request, "er_agenteriesgo/view.html", data)