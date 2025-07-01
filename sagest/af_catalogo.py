# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import CatalogoForm
from sagest.models import CatalogoBien
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, puede_realizar_accion


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
                f = CatalogoForm(request.POST)
                if f.is_valid():
                    if CatalogoBien.objects.filter(identificador=f.cleaned_data['identificador'].upper().strip(), tipobien=f.cleaned_data['tipobien'], tipocatalogo=f.cleaned_data['tipocatalogo']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El registro ya existe."})
                    if int(f.cleaned_data['tipocatalogo']) == 1:
                        catalogo = CatalogoBien(tipocatalogo=f.cleaned_data['tipocatalogo'],
                                                identificador=f.cleaned_data['identificador'].strip(),
                                                descripcion=f.cleaned_data['descripcion'].strip(),
                                                tipobien=f.cleaned_data['tipobien'],
                                                item=f.cleaned_data['item'])
                    else:
                        catalogo = CatalogoBien(tipocatalogo=f.cleaned_data['tipocatalogo'],
                                                descripcion=f.cleaned_data['descripcion'].strip(),
                                                item=f.cleaned_data['item'])

                    catalogo.save(request)
                    log(u'Adiciono nuevo catalogo: %s' % catalogo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                f = CatalogoForm(request.POST)
                if f.is_valid():
                    catalogo = CatalogoBien.objects.get(pk=request.POST['id'])
                    if int(catalogo.tipocatalogo) == 1:
                        if CatalogoBien.objects.filter(descripcion=f.cleaned_data['descripcion'].strip() ,identificador=catalogo.identificador, tipobien=f.cleaned_data['tipobien'], tipocatalogo=int(request.POST['idt'])).exclude(id=catalogo.id).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El registro ya existe."})
                        catalogo.descripcion = f.cleaned_data['descripcion'].strip()
                        catalogo.tipobien = f.cleaned_data['tipobien']
                        catalogo.item = f.cleaned_data['item']
                    else:
                        if CatalogoBien.objects.filter(descripcion=f.cleaned_data['descripcion'].strip() ,tipocatalogo=catalogo.tipocatalogo).exclude(id=catalogo.id).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El registro ya existe."})
                        catalogo.descripcion = f.cleaned_data['descripcion'].strip()
                        catalogo.item = f.cleaned_data['item']
                    catalogo.save(request)
                    log(u'Modifico catalogo: %s' % catalogo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delete':
            try:
                catalogo = CatalogoBien.objects.get(pk=request.POST['id'])
                log(u'Elimino catalogo: %s' % catalogo, request, "del")
                catalogo.delete()
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
                    puede_realizar_accion(request, 'sagest.puede_modificar_catalogo')
                    data['title'] = u'Catálogo'
                    data['form'] = CatalogoForm()
                    return render(request, 'af_catalogo/add.html', data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_catalogo')
                    data['title'] = u'Modificar Catálogo de Bienes'
                    data['catalogo'] = catalogo = CatalogoBien.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(catalogo)
                    form = CatalogoForm(initial=initial)
                    form.editar()
                    data['form'] = form
                    return render(request, 'af_catalogo/edit.html', data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    puede_realizar_accion(request, 'sagest.puede_modificar_catalogo')
                    data['title'] = u'Eliminar Catálogo'
                    data['catalogo'] = CatalogoBien.objects.get(pk=request.GET['id'])
                    return render(request, 'af_catalogo/delete.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Catálogo'
            search = None
            tipo = None
            if 's' in request.GET:
                search = request.GET['s']
            if search:
                catalogo = CatalogoBien.objects.filter(Q(identificador__icontains=search) |
                                                       Q(descripcion__icontains=search) |
                                                       Q(item__codigo__icontains=search) |
                                                       Q(item__nombre__icontains=search))
            else:
                catalogo = CatalogoBien.objects.filter(status=True)
            paging = MiPaginador(catalogo, 25)
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
            data['catalogos'] = page.object_list
            return render(request, "af_catalogo/view.html", data)
