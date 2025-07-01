# -*- coding: UTF-8 -*-

import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import RequestContext

from decorators import secure_module
from sagest.forms import ObjetivoOperativoForm
from sagest.models import ObjetivoEstrategico, ObjetivoTactico, ObjetivoOperativo, Departamento, PeriodoPoa
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador,log


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
                f = ObjetivoOperativoForm(request.POST)
                if f.is_valid():
                    objetivo = ObjetivoOperativo(objetivotactico=f.cleaned_data['objetivotactico'],
                                                 descripcion=f.cleaned_data['descripcion'],
                                                 orden=f.cleaned_data['orden'])
                    objetivo.save(request)
                    log(u'añadio objetivo: %s' % objetivo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                objetivo = ObjetivoOperativo.objects.get(pk=request.POST['id'])
                f = ObjetivoOperativoForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['objetivotactico']:
                        objetivo.objetivotactico = f.cleaned_data['objetivotactico']
                    objetivo.descripcion = f.cleaned_data['descripcion']
                    objetivo.orden = f.cleaned_data['orden']
                    objetivo.save(request)
                    log(u'edito objetivo operativo: %s' % objetivo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delete':
            try:
                objetivo = ObjetivoOperativo.objects.get(pk=request.POST['id'])
                objetivo.status = False
                objetivo.save(request)
                log(u'cambio estado objetivo operativo: %s' % objetivo, request, "edit")
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
                    data['title'] = u'Adicionar Objetivo Operativo'
                    form = ObjetivoOperativoForm()
                    form.query()
                    data['form'] = form
                    return render(request, 'poa_objoperativos/add.html', data)
                except Exception as ex:
                    pass

            if action == 'combotacticos':
                try:
                    data['objetivostacticos'] = ObjetivoTactico.objects.filter(objetivoestrategico=request.GET['id'])
                    return render(request, 'poa_objtacticos/combo.html', data)
                except Exception as ex:
                    pass

            if action == 'comboestrategico':
                try:
                    data['objetivostacticos'] = ObjetivoEstrategico.objects.filter(periodopoa=request.GET['id'])
                    return render(request, 'poa_objtacticos/combo.html', data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Modificar Objetivo Operativo'
                    data['objetivo'] = objetivo = ObjetivoOperativo.objects.get(pk=request.GET['id'])
                    form = ObjetivoOperativoForm(initial={"periodopoa": objetivo.objetivotactico.objetivoestrategico.periodopoa,
                                                          "objetivoestrategico": objetivo.objetivotactico.objetivoestrategico,
                                                          "objetivotactico": objetivo.objetivotactico,
                                                          "descripcion": objetivo.descripcion,
                                                          "orden": objetivo.orden})
                    form.editar()
                    data['form'] = form
                    return render(request, 'poa_objoperativos/edit.html', data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar Objetivo Operativo'
                    data['objetivo'] = ObjetivoOperativo.objects.get(pk=request.GET['id'])
                    return render(request, 'poa_objoperativos/delete.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Objetivos Operativos'
            search = None
            tipo = None
            data['periodoid'] = PeriodoPoa.objects.filter(status=True).order_by('-id')[0].id if 'periodoid' not in request.GET else int(request.GET['periodoid'])
            data['periodos'] = PeriodoPoa.objects.filter(status=True).order_by('-id')

            if 's' in request.GET:
                search = request.GET['s']
            if search:
                objetivostacticos = ObjetivoOperativo.objects.filter(objetivotactico__objetivoestrategico__periodopoa_id=data['periodoid'], descripcion__icontains=search, status=True)
            else:
                objetivostacticos = ObjetivoOperativo.objects.filter(objetivotactico__objetivoestrategico__periodopoa_id=data['periodoid'], status=True)
            if 'depaid' in request.GET:
                if int(request.GET['depaid']) > 0:
                    objetivostacticos = objetivostacticos.filter(objetivotactico__objetivoestrategico__periodopoa_id=data['periodoid'], objetivotactico__objetivoestrategico__departamento=int(request.GET['depaid']))

            paging = MiPaginador(objetivostacticos, 25)
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
            data['objetivos'] = page.object_list
            data['depaid'] = 0 if 'depaid' not in request.GET else int(request.GET['depaid'])
            data['departametos'] = Departamento.objects.filter(objetivoestrategico__status=True, status=True, objetivoestrategico__periodopoa_id=data['periodoid']).distinct()
            return render(request, "poa_objoperativos/view.html", data)
