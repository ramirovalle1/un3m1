# -*- coding: UTF-8 -*-

import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect,JsonResponse
from django.shortcuts import render
from django.template import RequestContext

from decorators import secure_module
from sagest.forms import ObjetivoTacticoForm
from sagest.models import ObjetivoTactico, ObjetivoEstrategico
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
                f = ObjetivoTacticoForm(request.POST)
                if f.is_valid():
                    objetivo = ObjetivoTactico(objetivoestrategico=f.cleaned_data['objetivoestrategico'],
                                               descripcion=f.cleaned_data['descripcion'],
                                               orden=f.cleaned_data['orden'])
                    objetivo.save(request)
                    log(u'Añadio objetivo tactico: %s' % objetivo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                objetivo = ObjetivoTactico.objects.get(pk=request.POST['id'])
                f = ObjetivoTacticoForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['objetivoestrategico']:
                        objetivo.objetivoestrategico = f.cleaned_data['objetivoestrategico']
                    objetivo.descripcion = f.cleaned_data['descripcion']
                    objetivo.orden = f.cleaned_data['orden']
                    objetivo.save(request)
                    log(u'edito objetivo tactico: %s' % objetivo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delete':
            try:
                objetivo = ObjetivoTactico.objects.get(pk=request.POST['id'])
                objetivo.status = False
                objetivo.save(request)
                log(u'edito estado de objetivo tactico: %s' % objetivo, request, "edit")
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
                    data['title'] = u'Adicionar Objetivo Táticos'
                    form = ObjetivoTacticoForm()
                    form.query()
                    data['form'] = form
                    return render(request, 'poa_objtacticos/add.html', data)
                except Exception as ex:
                    pass

            if action == 'combo':
                try:
                    data['objetivostacticos'] = ObjetivoEstrategico.objects.filter(periodopoa=request.GET['id'])
                    return render(request, 'poa_objtacticos/combo.html', data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Modificar Objetivo Tácticos'
                    data['objetivo'] = objetivo = ObjetivoTactico.objects.get(pk=request.GET['id'])
                    form = ObjetivoTacticoForm(initial={"periodopoa": objetivo.objetivoestrategico.periodopoa,
                                                        "objetivoestrategico": objetivo.objetivoestrategico,
                                                        "descripcion": objetivo.descripcion,
                                                        "orden": objetivo.orden})
                    form.editar()
                    data['form'] = form
                    return render(request, 'poa_objtacticos/edit.html', data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar Objetivo Táctico'
                    data['objetivo'] = ObjetivoTactico.objects.get(pk=request.GET['id'])
                    return render(request, 'poa_objtacticos/delete.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Objetivos Tácticos'
            search = None
            tipo = None
            if 's' in request.GET:
                search = request.GET['s']
            if search:
                objetivostacticos = ObjetivoTactico.objects.filter(descripcion__icontains=search, status=True).order_by('-objetivoestrategico__periodopoa__anio','objetivoestrategico__departamento', 'orden')
            else:
                objetivostacticos = ObjetivoTactico.objects.filter(status=True).order_by('-objetivoestrategico__periodopoa__anio','objetivoestrategico__departamento', 'orden')
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
            data['objetivostacticos'] = page.object_list
            return render(request, "poa_objtacticos/view.html", data)