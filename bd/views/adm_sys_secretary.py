# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from secretaria.forms import ServicioForm, CategoriaServicioForm
from secretaria.models import Servicio, CategoriaServicio
from decorators import secure_module
from sagest.models import TipoOtroRubro
from sga.commonviews import adduserdata
from django.db import connection, transaction

from sga.funciones import MiPaginador, log
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@transaction.atomic()
def services(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                errors = []
                form = ServicioForm(request.POST)
                form.edit(request.POST['categoria'], request.POST['tiporubro'])
                if not form.is_valid():
                    errors = [{k: v[0]} for k, v in form.errors.items()]
                    raise NameError(u"Formulario incorrecto")
                eServicio = Servicio(orden=form.cleaned_data['orden'],
                                     alias=form.cleaned_data['alias'],
                                     nombre=form.cleaned_data['nombre'],
                                     categoria=form.cleaned_data['categoria'],
                                     tiporubro=form.cleaned_data['tiporubro'],
                                     proceso=form.cleaned_data['proceso'],
                                     costo=form.cleaned_data['costo'],
                                     activo=form.cleaned_data['activo'],
                                     )
                eServicio.save(request)
                log(u'Adiciono nuevo servicio de secretaria: %s' % eServicio, request, "add")
                return JsonResponse({"result": 'ok', "mensaje": u"Se creo el servicio correctamente", "showSwal": True, 'id': f'?id={eServicio.pk}'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', 'error': True, "form": errors, "mensaje": f"Ocurrio un error: {ex.__str__()}"})

        elif action == 'edit':
            try:
                errors = []
                eServicio = Servicio.objects.get(pk=int(encrypt(request.POST['id'])))
                form = ServicioForm(request.POST)
                form.edit(request.POST['categoria'], request.POST['tiporubro'])
                if not form.is_valid():
                    errors = [{k: v[0]} for k, v in form.errors.items()]
                    raise NameError(u"Formulario incorrecto")
                eServicio.orden = form.cleaned_data['orden']
                eServicio.alias = form.cleaned_data['alias']
                eServicio.nombre = form.cleaned_data['nombre']
                eServicio.categoria = form.cleaned_data['categoria']
                eServicio.tiporubro = form.cleaned_data['tiporubro']
                eServicio.proceso = form.cleaned_data['proceso']
                eServicio.costo = form.cleaned_data['costo']
                eServicio.activo = form.cleaned_data['activo']
                eServicio.save(request)
                log(u'Edito servicio de secretaria: %s' % eServicio, request, "edit")
                return JsonResponse({"result": 'ok', "mensaje": u"Se edito el servicio correctamente", "showSwal": True, 'id': f'?id={eServicio.pk}'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', 'error': True, "form": errors, "mensaje": f"Ocurrio un error: {ex.__str__()}"})

        elif action == 'delete':
            try:
                eServicio = delete = Servicio.objects.get(pk=int(encrypt(request.POST['id'])))
                if not eServicio.puede_eliminar():
                    raise NameError(u"Categoria se esta utilizando en un servicio")
                eServicio.delete()
                log(u'Eliminó servicio de secretaria: %s' % delete, request, "del")
                return JsonResponse({"result": 'ok', "mensaje": u"Servicio eliminado correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'searchCategoria':
                try:
                    q = request.GET['q'].upper().strip()
                    eCategoriaServicios = CategoriaServicio.objects.filter((Q(nombre__icontains=q) | Q(descripcion__icontains=q))).distinct().order_by('id')[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{}".format(x.nombre)} for x in eCategoriaServicios]}
                    return JsonResponse(data)
                except Exception as ex:
                    data = {"result": "ok", "results": []}
                    return JsonResponse(data)

            elif action == 'searchTipoRubro':
                try:
                    q = request.GET['q'].upper().strip()
                    eTipoOtroRubros = TipoOtroRubro.objects.filter(Q(nombre__icontains=q) | Q(partida__codigo__icontains=q) | Q(partida__nombre__icontains=q)).distinct().order_by('id')[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} ({})".format(x.nombre, x.partida.codigo)} for x in eTipoOtroRubros]}
                    return JsonResponse(data)
                except Exception as ex:
                    data = {"result": "ok", "results": []}
                    return JsonResponse(data)

            elif action == 'add':
                try:
                    form = ServicioForm()
                    data['title'] = u"Adicionar servicio"
                    data['form'] = form
                    data['id'] = 0
                    data['action'] = 'add'
                    return render(request, "adm_sistemas/secretary/services/crud.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'edit':
                try:
                    eServicio = Servicio.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = ServicioForm(initial=model_to_dict(eServicio))
                    form.edit(eServicio.categoria.pk, eServicio.tiporubro.pk)
                    data['title'] = u"Editar servicio"
                    data['form'] = form
                    data['id'] = eServicio.pk
                    data['action'] = 'edit'
                    return render(request, "adm_sistemas/secretary/services/crud.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Servicios de secretaria'
                filtros, s, pro, url_vars, id = Q(pk__gte=0), request.GET.get('s', ''), request.GET.get('p', '0'), '', request.GET.get('id', '0')
                eServicios = Servicio.objects.filter(filtros).order_by('nombre', 'categoria')
                data['count'] = eServicios.values("id").count()
                if int(id):
                    filtros = filtros & (Q(id=id))
                    data['id'] = f"{id}"
                    url_vars += f"&id={id}"
                if s:
                    filtros = filtros & (Q(nombre__icontains=s) | Q(categoria__nombre__icontains=s) | Q(categoria__descripcion__icontains=s))
                    data['s'] = f"{s}"
                    url_vars += f"&s={s}"

                if int(pro):
                    filtros = filtros & (Q(categoria_id=pro))
                    data['p'] = f"{pro}"
                    url_vars += f"&p={pro}"
                eServicios = eServicios.filter(filtros).order_by('nombre', 'categoria')
                paging = MiPaginador(eServicios, 10)
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
                data['page'] = page
                data['rangospaging'] = paging.rangos_paginado(p)
                data['eServicios'] = page.object_list
                data['url_vars'] = url_vars
                data['eCategorias'] = CategoriaServicio.objects.values_list('id', 'nombre').filter(status=True).distinct()
                return render(request, "adm_sistemas/secretary/services/view.html", data)
            except Exception as ex:
                HttpResponseRedirect(f"/adm_sistemas?info={ex.__str__()}")


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@transaction.atomic()
def categories(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                errors = []
                form = CategoriaServicioForm(request.POST)
                if not form.is_valid():
                    errors = [{k: v[0]} for k, v in form.errors.items()]
                    raise NameError(u"Formulario incorrecto")
                eCategoriaServicio = CategoriaServicio(nombre=form.cleaned_data['nombre'],
                                                       descripcion=form.cleaned_data['descripcion'],
                                                       icono=form.cleaned_data['icono'],
                                                       roles=','.join(form.cleaned_data['roles']))
                eCategoriaServicio.save(request)
                for grupo in form.cleaned_data['grupos']:
                    eCategoriaServicio.grupos.add(grupo)
                eCategoriaServicio.save(request)

                log(u'Adiciono nueva categoria de servicio de secretaria: %s' % eCategoriaServicio, request, "add")
                return JsonResponse({"result": 'ok', "mensaje": u"Se creo la categoria correctamente", "showSwal": True, 'id': f'?id={eCategoriaServicio.pk}'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', 'error': True, "form": errors, "mensaje": f"Ocurrio un error: {ex.__str__()}"})

        elif action == 'edit':
            try:
                errors = []
                eCategoriaServicio = CategoriaServicio.objects.get(pk=int(encrypt(request.POST['id'])))
                form = CategoriaServicioForm(request.POST)
                if not form.is_valid():
                    errors = [{k: v[0]} for k, v in form.errors.items()]
                    raise NameError(u"Formulario incorrecto")
                eCategoriaServicio.nombre = form.cleaned_data['nombre']
                eCategoriaServicio.descripcion = form.cleaned_data['descripcion']
                eCategoriaServicio.icono = form.cleaned_data['icono']
                eCategoriaServicio.activo = form.cleaned_data['activo']
                eCategoriaServicio.roles = ','.join(form.cleaned_data['roles'])
                eCategoriaServicio.save(request)

                for grupo in eCategoriaServicio.grupos.all():
                    eCategoriaServicio.grupos.remove(grupo)

                if form.cleaned_data['grupos']:
                    for grupo in form.cleaned_data['grupos']:
                        eCategoriaServicio.grupos.add(grupo)
                    eCategoriaServicio.save(request)

                log(u'Edito categoria de servicio de secretaria: %s' % eCategoriaServicio, request, "edit")
                return JsonResponse({"result": 'ok', "mensaje": u"Se edito la categoria correctamente", "showSwal": True, 'id': f'?id={eCategoriaServicio.pk}'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', 'error': True, "form": errors, "mensaje": f"Ocurrio un error: {ex.__str__()}"})

        elif action == 'delete':
            try:
                eCategoriaServicio = delete = CategoriaServicio.objects.get(pk=int(encrypt(request.POST['id'])))
                if not eCategoriaServicio.puede_eliminar():
                    raise NameError(u"Categoria se esta utilizando en un servicio")
                eCategoriaServicio.delete()
                log(u'Eliminó categoria de servicio de secretaria: %s' % delete, request, "del")
                return JsonResponse({"result": 'ok', "mensaje": u"Categoria eliminada correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', "mensaje": f"Ocurrio un error al eliminar: {ex.__str__()}"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    form = CategoriaServicioForm()
                    data['title'] = u"Adicionar categoría de secretaría"
                    data['form'] = form
                    data['id'] = 0
                    data['action'] = 'add'
                    return render(request, "adm_sistemas/secretary/categories/crud.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'edit':
                try:
                    eCategoriaServicio = CategoriaServicio.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = CategoriaServicioForm(initial=model_to_dict(eCategoriaServicio))
                    data['title'] = u"Editar categoría de secretaría"
                    data['form'] = form
                    data['id'] = eCategoriaServicio.pk
                    data['action'] = 'edit'
                    return render(request, "adm_sistemas/secretary/categories/crud.html", data)
                except Exception as ex:
                    HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Categorias de secretaría'
                filtros, s, url_vars, id = Q(pk__gte=0), request.GET.get('s', ''), '', request.GET.get('id', '0')
                eCategoriaServicios = CategoriaServicio.objects.filter(filtros)
                data['count'] = eCategoriaServicios.values("id").count()
                if int(id):
                    filtros = filtros & (Q(id=id))
                    data['id'] = f"{id}"
                    url_vars += f"&id={id}"
                if s:
                    filtros = filtros & (Q(nombre__icontains=s) | Q(descripcion__icontains=s))
                    data['s'] = f"{s}"
                    url_vars += f"&s={s}"

                eCategoriaServicios = eCategoriaServicios.filter(filtros)
                paging = MiPaginador(eCategoriaServicios, 10)
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
                data['page'] = page
                data['rangospaging'] = paging.rangos_paginado(p)
                data['eCategoriaServicios'] = page.object_list
                data['url_vars'] = url_vars
                return render(request, "adm_sistemas/secretary/categories/view.html", data)
            except Exception as ex:
                HttpResponseRedirect(f"/adm_sistemas?info={ex.__str__()}")
