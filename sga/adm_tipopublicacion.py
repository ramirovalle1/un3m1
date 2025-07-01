# -*- coding: UTF-8 -*-
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from sga.commonviews import adduserdata
from sga.forms import TipoPublicacionForm
from sga.funciones import log, MiPaginador
from sga.models import TipoPublicacion


def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'addtipo' or action=='edittipo':
                try:
                    f = TipoPublicacionForm(request.POST)
                    if f.is_valid():
                        if action == 'addtipo':
                            tipo = TipoPublicacion()
                        else:
                            tipo = TipoPublicacion.objects.get(pk=request.POST['id'])
                        tipo.tipo = f.cleaned_data['tipo']
                        tipo.codigo  = f.cleaned_data['codigo']
                        tipo.save(request)
                        if action =='addtipo':
                            log(u"Adiciono tipo de publicación: %s" % tipo, request, "add")
                        else:
                            log(u"Edito tipo de publicación: %s" % tipo, request, "edit")
                        return JsonResponse({"result":"ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result":"bad", 'mensaje': u'Eror al guardar los datos'})

            if action == 'deletetipo':
                try:
                    tipo = TipoPublicacion.objects.get(pk=request.POST['id'])
                    tipo.status = False
                    tipo.save(request)
                    log(u"Elimino Tipo Publicación: %s" % tipo, request, "delete")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos.(%s)" % ex})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'addtipo':
                try:
                    data['title'] = u"Añadir Tipo de Publicación"
                    data['form'] = TipoPublicacionForm()
                    return render(request, "adm_tipopublicacion/addtipo.html", data)
                except Exception as ex:
                    pass
            elif action == 'edittipo':
                try:
                    data['title'] = u"Editar Tipo de Publicación"
                    data['tipo'] = tipo = TipoPublicacion.objects.get(pk=request.GET['id'])
                    data['form'] = TipoPublicacionForm(initial={
                        'codigo': tipo.codigo,
                        'tipo': tipo.tipo
                    })
                    return render(request, "adm_tipopublicacion/edittipo.html", data)
                except Exception as ex:
                    pass
            elif action == 'deletetipo':
                try:
                    data['title'] = u'Tipo de Publicación'
                    data['tipo'] = tipo = TipoPublicacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_tipopublicacion/deletetipo.html", data)
                except Exception as ex:
                    pass
            return HttpResponseRedirect(request.path)

        else:
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                asignaturas = TipoPublicacion.objects.filter(tipo__icontains=search, status=True).distinct().order_by('tipo')
            elif 'id' in request.GET:
                ids = request.GET['id']
                asignaturas = TipoPublicacion.objects.filter(id=ids, status=True)
            else:
                asignaturas = TipoPublicacion.objects.filter(status=True).order_by('tipo')
            paging = MiPaginador(asignaturas, 25)
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
            data['tipopublicaciones'] = page.object_list
            data['title'] = u"Tipo de Publicación"

            return render(request, "adm_tipopublicacion/viewtipo.html", data)