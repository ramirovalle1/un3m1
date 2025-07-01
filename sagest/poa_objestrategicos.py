# -*- coding: UTF-8 -*-

import json

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import RequestContext
from django.template.loader import get_template


from decorators import secure_module
from sagest.forms import ObjetivoEstrategicoForm
from sagest.models import ObjetivoEstrategico
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
                f = ObjetivoEstrategicoForm(request.POST)
                if f.is_valid():
                    objetivo = ObjetivoEstrategico(periodopoa=f.cleaned_data['periodopoa'],
                                                   departamento=f.cleaned_data['departamento'],
                                                   carrera=f.cleaned_data['carrera'],
                                                   programa=f.cleaned_data['programa'],
                                                   descripcion=f.cleaned_data['descripcion'],
                                                   orden=f.cleaned_data['orden'])
                    objetivo.save(request)
                    log(u'Adicionó objetivo estrategico: %s' % objetivo, request, "add")
                    return HttpResponse(json.dumps({"result": False}), content_type="application/json")
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al guardar los datos. Ya existe registro con esto datos."}), content_type="application/json")

        if action == 'edit':
            try:
                objetivo = ObjetivoEstrategico.objects.get(pk=request.POST['id'])
                f = ObjetivoEstrategicoForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['periodopoa']:
                        objetivo.periodopoa = f.cleaned_data['periodopoa']
                    if f.cleaned_data['departamento']:
                        objetivo.departamento = f.cleaned_data['departamento']
                    if f.cleaned_data['carrera']:
                        objetivo.carrera = f.cleaned_data['carrera']
                    if f.cleaned_data['programa']:
                        objetivo.programa = f.cleaned_data['programa']
                    objetivo.descripcion = f.cleaned_data['descripcion']
                    objetivo.orden = f.cleaned_data['orden']
                    objetivo.save(request)
                    log(u'Edito objetivo estrategico: %s' % objetivo, request, "edit")
                    return JsonResponse({"result": False})
                else:
                    for k, v in f.errors.items():
                        raise NameError(v[0])
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result":"bad", "mensaje": u"%s" % ex.__str__()})

        if action == 'delete':
            try:
                objetivo = ObjetivoEstrategico.objects.get(pk=request.POST['id'])
                objetivo.status = False
                objetivo.save(request)
                log(u'Elimino objetivo estrategico: %s' % objetivo, request, "del")
                return HttpResponse(json.dumps({"result": "ok"}), content_type="application/json")
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al eliminar los datos."}), content_type="application/json")

        return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Solicitud Incorrecta."}), content_type="application/json")
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar Objetivo Estratégico'
                    data['action'] = 'add'
                    data['form'] = ObjetivoEstrategicoForm()
                    template = get_template('poa_objestrategicos/add.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Modificar Objetivo Estratégico'
                    data['action'] = 'edit'
                    data['objetivo'] = objetivo = ObjetivoEstrategico.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(objetivo)
                    form = ObjetivoEstrategicoForm(initial=initial)
                    form.editar()
                    data['form'] = form
                    template = get_template('poa_objestrategicos/edit.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar Objetivo Estratégico'
                    data['objetivo'] = ObjetivoEstrategico.objects.get(pk=request.GET['id'])
                    return render(request, 'poa_objestrategicos/delete.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Objetivos Estratégicos'
            search, url_vars = request.GET.get('s', ''), ''
            search = None
            tipo = None
            if 's' in request.GET:
                search = request.GET['s']
            if search:
                objetivos = ObjetivoEstrategico.objects.filter(Q(periodopoa__descripcion__icontains=search) |
                                                               Q(departamento__nombre__icontains=search) |
                                                               Q(programa__nombre__icontains=search) |
                                                               Q(descripcion__icontains=search), status=True).order_by('-periodopoa__anio', 'departamento', 'programa', 'descripcion')
                url_vars += "&s={}".format(search)

            else:
                objetivos = ObjetivoEstrategico.objects.filter(status=True).order_by('-periodopoa__anio', 'departamento', 'programa', 'descripcion')
            paging = MiPaginador(objetivos, 25)
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
            data['url_vars'] = url_vars
            return render(request, "poa_objestrategicos/view.html", data)
