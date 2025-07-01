# -*- coding: UTF-8 -*-
import json
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms.models import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect,JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import get_template

from decorators import secure_module
from sagest.forms import ProgramaForm
from sagest.models import ProgramaPoa
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador,log


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = ProgramaForm(request.POST)
                if f.is_valid():
                    programa = ProgramaPoa(nombre=f.cleaned_data['nombre'])
                    programa.save(request)
                    log(u'añadio programa poa: %s' % programa, request, "add")
                    return redirect('/poa_programas')
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                programa = ProgramaPoa.objects.get(pk=request.POST['id'])
                f = ProgramaForm(request.POST)
                if f.is_valid():
                    programa.nombre = f.cleaned_data['nombre']
                    programa.save(request)
                    log(u'edit programa poa: %s' % programa, request, "add")
                    return redirect('/poa_programas')
                    #return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delete':
            try:
                programa = ProgramaPoa.objects.get(pk=request.POST['id'])
                programa.delete()
                log(u'cambio esatdo programa poa: %s' % programa, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data = {}
        adduserdata(request, data)
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar Programa'
                    data['action'] = 'add'
                    data['form'] = ProgramaForm()
                    template = get_template('poa_programas/add.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                    #return render(request, 'poa_programas/add.html', data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Modificar Programa'
                    data['action'] = 'edit'
                    data['programa'] = programa = ProgramaPoa.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(programa)
                    data['form'] = ProgramaForm(initial=initial)
                    template = get_template('poa_programas/edit.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar Programa'
                    data['programa'] = ProgramaPoa.objects.get(pk=request.GET['id'])
                    return render(request, 'poa_programas/delete.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Programas'
            search, url_vars = request.GET.get('s', ''),''
            search = None
            tipo = None
            if 's' in request.GET:
                search = request.GET['s']
            # if search:
                programas = ProgramaPoa.objects.filter(nombre__icontains=search, status=True)
                url_vars += "&s={}".format(search)
            else:
                programas = ProgramaPoa.objects.filter(status=True)
            paging = MiPaginador(programas, 25)
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
            data['programas'] = page.object_list
            data['url_vars'] = url_vars
            return render(request, "poa_programas/view.html", data)
