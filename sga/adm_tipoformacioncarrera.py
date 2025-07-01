# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sga.commonviews import adduserdata
from sga.forms import TipoFormacionCarreraForm
from sga.funciones import MiPaginador, log
from django.db.models import Q
from sga.models import TipoFormacionCarrera


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                form = TipoFormacionCarreraForm(request.POST)
                if form.is_valid():
                    formacion = TipoFormacionCarrera(nombre=form.cleaned_data['nombre'])
                    formacion.save(request)
                    log(u'Adiciono tipo de formacion carrera: %s - [%s]' % (formacion, formacion.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                form = TipoFormacionCarreraForm(request.POST, request.FILES)
                if form.is_valid():
                    formacion = TipoFormacionCarrera.objects.get(pk=int(request.POST['id']))
                    formacion.nombre = form.cleaned_data['nombre']
                    formacion.save(request)
                    log(u'Edito tipo de formacion carrera: %s - [%s]' % (formacion, formacion.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'del':
            try:
                formacion = TipoFormacionCarrera.objects.get(pk=int(request.POST['id']))
                if formacion.esta_utilizado:
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, se esta utilizando en carrera.."})
                log(u'Elimino tipo de formacion carrera: %s - [%s]' % (formacion, formacion.id), request, "del")
                formacion.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return HttpResponseRedirect(request.path)

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar tipo de formación'
                    data['form'] = TipoFormacionCarreraForm()
                    return render(request, "adm_tipoformacioncarrera/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'del':
                try:
                    data['title'] = u'Eliminar tipo de formación'
                    data['formacion'] = TipoFormacionCarrera.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_tipoformacioncarrera/del.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar tipo de formación'
                    data['formacion'] = formacion = TipoFormacionCarrera.objects.get(pk=int(request.GET['id']))
                    form = TipoFormacionCarreraForm(initial={'nombre': formacion.nombre})
                    data['form'] = form
                    return render(request, "adm_tipoformacioncarrera/edit.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Tipo de formación'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    formacion = TipoFormacionCarrera.objects.filter(Q(nombre__icontains=search) &
                                                                    Q(status=True)).distinct()
                else:
                    formacion = TipoFormacionCarrera.objects.filter(Q(nombre__icontains=ss[0]) & Q(nombre__icontains=ss[1]) &
                                                                    Q(status=True)).distinct()
            else:
                formacion = TipoFormacionCarrera.objects.filter(status=True)
            paging = MiPaginador(formacion, 20)
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
            data['formaciones'] = page.object_list
            return render(request, 'adm_tipoformacioncarrera/view.html', data)

