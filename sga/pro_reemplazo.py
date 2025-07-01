# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from googletrans import Translator
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.db import transaction
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import ProfesorReemplazoForm
from sga.funciones import log, MiPaginador
from sga.models import ProfesorReemplazo


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = ProfesorReemplazoForm(request.POST)
                if f.is_valid():
                    profesorreemplazo = ProfesorReemplazo(solicita=f.cleaned_data['solicita'],
                                                          reemplaza=f.cleaned_data['reemplaza'],
                                                          desde=f.cleaned_data['desde'],
                                                          hasta=f.cleaned_data['hasta'],
                                                          motivo=f.cleaned_data['motivo'])
                    profesorreemplazo.save(request)
                    log(u'Adiciono profesor reemplazo: %s' % profesorreemplazo, request, "add")
                    return JsonResponse({"result": "ok", "id": profesorreemplazo.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                profesorreemplazo = ProfesorReemplazo.objects.get(pk=request.POST['id'])
                f = ProfesorReemplazoForm(request.POST)
                if f.is_valid():
                    profesorreemplazo.reemplaza = f.cleaned_data['reemplaza']
                    profesorreemplazo.desde = f.cleaned_data['desde']
                    profesorreemplazo.hasta = f.cleaned_data['hasta']
                    profesorreemplazo.motivo = f.cleaned_data['motivo']
                    profesorreemplazo.save(request)
                    log(u'Modifico profesor reemplazo: %s' % profesorreemplazo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al guardar los datos."})

        elif action == 'delete':
            try:
                profesorreemplazo = ProfesorReemplazo.objects.get(pk=request.POST['id'])
                if profesorreemplazo.procesado:
                    return JsonResponse({"result": "bad", "mensaje": u"Profesor reemplazo en uso."})
                log(u'Elimino profesor reemplazo: %s' % profesorreemplazo, request, "del")
                profesorreemplazo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(),'es').text, "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Reemplazo Docente'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar Reemplazo'
                    data['form'] = ProfesorReemplazoForm()
                    return render(request, "pro_reemplazo/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar Reemplazo'
                    profesorreemplazo = ProfesorReemplazo.objects.get(pk=request.GET['id'])
                    f = ProfesorReemplazoForm(initial={'solicita': profesorreemplazo.solicita,
                                                       'reemplaza': profesorreemplazo.reemplaza,
                                                       'desde': profesorreemplazo.desde,
                                                       'hasta': profesorreemplazo.hasta,
                                                       'motivo': profesorreemplazo.motivo})
                    f.fields['solicita'].widget.attrs['readonly'] = True
                    f.fields['solicita'].widget.attrs['disabled'] = True
                    f.fields['solicita'].widget.required = False
                    data['form'] = f
                    data['profesorreemplazo'] = profesorreemplazo
                    return render(request, "pro_reemplazo/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'delete':
                try:
                    data['title'] = u'Eliminar Reemplazo'
                    data['profesorreemplazo'] = ProfesorReemplazo.objects.get(pk=request.GET['id'])
                    return render(request, "pro_reemplazo/delete.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                profesorreemplazo = ProfesorReemplazo.objects.filter(Q(solicita__persona__nombres__icontains=search) | Q(solicita__persona__apellido1__icontains=search) | Q(solicita__persona__apellido2__icontains=search) | Q(reemplaza__persona__nombres__icontains=search) | Q(reemplaza__persona__apellido1__icontains=search) | Q(reemplaza__persona__apellido2__icontains=search)).order_by('solicita__persona__apellido1', 'solicita__persona__apellido2', 'solicita__persona__nombres')
            elif 'id' in request.GET:
                ids = request.GET['id']
                profesorreemplazo = ProfesorReemplazo.objects.filter(id=ids)
            else:
                profesorreemplazo = ProfesorReemplazo.objects.all().order_by('solicita__persona__nombres')
            paging = MiPaginador(profesorreemplazo, 25)
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
            data['profesorreemplazos'] = page.object_list
            return render(request, "pro_reemplazo/view.html", data)
