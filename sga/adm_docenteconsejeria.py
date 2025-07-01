# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from googletrans import Translator

from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import DocenteConsejeriaForm
from sga.funciones import log, MiPaginador
from sga.models import DocenteConsejeriaAcademica


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = DocenteConsejeriaForm(request.POST)
                if f.is_valid():
                    if int(request.POST['profesor'])<=0:
                        return JsonResponse({'result': 'bad', 'mensaje': u"Ingrese un Profesor"})
                    docenteconsejeriaacademica = DocenteConsejeriaAcademica(profesor_id=int(request.POST['profesor']),
                                                                            todos=f.cleaned_data['todos'])
                    docenteconsejeriaacademica.save(request)
                    if not f.cleaned_data['todos']:
                        docenteconsejeriaacademica.coordinacion = docenteconsejeriaacademica.profesor.coordinacion
                    docenteconsejeriaacademica.save(request)
                    log(u'Adiciono docente consejeria: %s' % docenteconsejeriaacademica, request, "add")
                    return JsonResponse({"result": "ok", "id": docenteconsejeriaacademica.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                docenteconsejeriaacademica = DocenteConsejeriaAcademica.objects.get(pk=request.POST['id'])
                f = DocenteConsejeriaForm(request.POST)
                if f.is_valid():
                    if int(request.POST['profesor'])<=0:
                        return JsonResponse({'result': 'bad', 'mensaje': u"Ingrese un Profesor"})
                    docenteconsejeriaacademica.profesor_id = int(request.POST['profesor'])
                    docenteconsejeriaacademica.todos = f.cleaned_data['todos']
                    docenteconsejeriaacademica.save(request)
                    if not f.cleaned_data['todos']:
                        docenteconsejeriaacademica.coordinacion = docenteconsejeriaacademica.profesor.coordinacion
                    else:
                        docenteconsejeriaacademica.coordinacion = None
                    docenteconsejeriaacademica.save(request)
                    log(u'Modifico docente consejeria: %s' % docenteconsejeriaacademica, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        elif action == 'delete':
            try:
                docenteconsejeriaacademica = DocenteConsejeriaAcademica.objects.get(pk=request.POST['id'])
                if docenteconsejeriaacademica.enuso(periodo):
                    return JsonResponse({"result": "bad", "mensaje": u"Docente en uso en el periodo."})
                log(u'Elimino docente consejeria: %s' % docenteconsejeriaacademica, request, "del")
                docenteconsejeriaacademica.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Docentes Consejerias'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar Docente Consejeria'
                    data['form'] = DocenteConsejeriaForm()
                    return render(request, "adm_docenteconsejeria/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar Docente Consejeria'
                    data['docenteconsejeriaacademica'] = docenteconsejeriaacademica = DocenteConsejeriaAcademica.objects.get(pk=request.GET['id'])
                    f = DocenteConsejeriaForm(initial={'profesor': docenteconsejeriaacademica.profesor.id,
                                                       'todos': docenteconsejeriaacademica.todos})
                    f.fields['profesor'].widget.attrs['descripcion'] = docenteconsejeriaacademica.profesor
                    f.fields['profesor'].widget.attrs['value'] = docenteconsejeriaacademica.profesor.id

                    data['form'] = f
                    return render(request, "adm_docenteconsejeria/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'delete':
                try:
                    data['title'] = u'Eliminar Docente Consejeria'
                    data['docenteconsejeriaacademica'] = DocenteConsejeriaAcademica.objects.get(pk=request.GET['id'])
                    return render(request, "adm_docenteconsejeria/delete.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                docenteconsejeriaacademica = DocenteConsejeriaAcademica.objects.filter(profesor__persona__nombre__icontains=search, status=True).order_by('profesor__persona__nombres')
            elif 'id' in request.GET:
                ids = request.GET['id']
                docenteconsejeriaacademica = DocenteConsejeriaAcademica.objects.filter(id=ids)
            else:
                docenteconsejeriaacademica = DocenteConsejeriaAcademica.objects.filter(status=True).order_by('profesor__persona__nombres')
            paging = MiPaginador(docenteconsejeriaacademica, 25)
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
            data['docenteconsejeriaacademicas'] = page.object_list
            data['periodo'] = periodo
            return render(request, "adm_docenteconsejeria/view.html", data)
