# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sagest.forms import ResolucionForm
from sagest.models import Resoluciones, TipoResolucion
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre, convertir_fecha


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'add':
            try:
                form = ResolucionForm(request.POST, request.FILES)
                arch = request.FILES['archivo']
                extencion = arch._name.split('.')
                exte = extencion[1]
                if arch.size > 10485760:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                if not exte == 'pdf':
                    return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})
                if form.is_valid():
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("resolucion_", newfile._name)
                    resolucion = Resoluciones(tipo_id=int(request.POST['tipo']),
                                              numeroresolucion=form.cleaned_data['numeroresolucion'],
                                              resuelve=form.cleaned_data['resuelve'],
                                              fecha=form.cleaned_data['fecha'],
                                              archivo=newfile)
                    resolucion.save(request)
                    log(u'Adiciono una resolución: %s' % resolucion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, Al guadar los datos"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                form = ResolucionForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extencion = arch._name.split('.')
                    exte = extencion[1]
                    if arch.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 10 Mb."})
                    if not exte == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})
                if form.is_valid():
                    resolucion = Resoluciones.objects.get(status=True, id=int(request.POST['id']))
                    resolucion.tipo_id=int(request.POST['tipo'])
                    resolucion.numeroresolucion=form.cleaned_data['numeroresolucion']
                    resolucion.resuelve=form.cleaned_data['resuelve']
                    resolucion.fecha=form.cleaned_data['fecha']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("resolucion_", newfile._name)
                        resolucion.archivo=newfile
                    resolucion.save(request)
                    log(u'Editó una resolución: %s' % resolucion, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, Al guadar los datos"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'del':
            try:
                if 'id' in request.POST:
                    resolucion = Resoluciones.objects.get(status=True, pk=int(request.POST['id']))
                    log(u'Eliminó la resolución: %s' % resolucion, request, "del")
                    resolucion.delete()
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el tipo de resolución."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'addtiporesolucion':
            try:
                if 'nombre' in request.POST:
                    if TipoResolucion.objects.filter(nombre=request.POST['nombre'].strip()).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe el tipo de resolución."})
                    tipo = TipoResolucion(nombre=request.POST['nombre'].strip())
                    tipo.save(request)
                    log(u'Adiciono nuevo tipo de resolución: %s' % tipo, request, "add")
                    return JsonResponse({"result": "ok", "id":tipo.id, 'cantidad': TipoResolucion.objects.filter(status=True).count()})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edittiporesolucion':
            try:
                if 'nombre' in request.POST and 'id' in request.POST:
                    if TipoResolucion.objects.filter(nombre=request.POST['nombre'].strip()).exclude(pk=int(request.POST['id'])).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe el tipo de resolución."})
                    tipo = TipoResolucion.objects.get(pk=int(request.POST['id']))
                    tipo.nombre = request.POST['nombre']
                    tipo.save(request)
                    log(u'Modificó tipo de resolución: %s' % tipo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deltiporesolucion':
            try:
                if 'id' in request.POST:
                    tipo = TipoResolucion.objects.get(status=True, pk=int(request.POST['id']))
                    log(u'Eliminó tipo de resolución: %s' % tipo, request, "del")
                    tipo.delete()
                    return JsonResponse({"result": "ok", "cantidad": TipoResolucion.objects.filter(status=True).count()})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar el tipo de resolución."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar Resolución'
                    data['form'] = ResolucionForm()
                    return render(request, "adm_resoluciones/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar Resolución'
                    data['resolucion'] = resolucion = Resoluciones.objects.get(id=int(request.GET['id']))
                    data['form'] = ResolucionForm(initial={'numeroresolucion': resolucion.numeroresolucion,
                                                  'resuelve': resolucion.resuelve,
                                                  'tipo': resolucion.tipo,
                                                  'fecha': resolucion.fecha,
                                                  'archivo': resolucion.archivo})
                    return render(request, "adm_resoluciones/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'del':
                try:
                    data['title'] = u'Eliminar resolución'
                    data['resolucion'] = Resoluciones.objects.get(id=int(request.GET['id']))
                    return render(request, "adm_resoluciones/del.html", data)
                except Exception as ex:
                    pass

            if action == 'tiposresoluciones':
                data['title'] = u'Gestión de tipo de resoluciones'
                search = None
                ids = None
                tipos = TipoResolucion.objects.filter(status=True)
                if 's' in request.GET:
                    search = request.GET['s']
                    ss = search.split(' ')
                    if len(ss) == 1:
                        tipos = tipos.filter(Q(nombre__icontains=search))
                    elif len(ss) == 2:
                        tipos = tipos.filter(Q(nombre__icontains=ss[0]) & Q(nombre__icontains=ss[1]))
                    else:
                        tipos = tipos.filter(Q(nombre__icontains=ss[0]) & Q(nombre__icontains=ss[1]) & Q(nombre__icontains=ss[2]))
                paging = MiPaginador(tipos, 20)
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
                data['tipos'] = page.object_list
                data['email_domain'] = EMAIL_DOMAIN
                return render(request, "adm_resoluciones/tiporessoluciones.html", data)

            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Gestión de Resoluciones'
            search = None
            ids = None
            tiposelect = 0
            lista = []
            fecha = None
            data['tipos'] = TipoResolucion.objects.values_list('id', 'nombre', flat=False).filter(status=True)
            if 'id' in request.GET:
                ids = int(request.GET['id'])
                resoluciones = Resoluciones.objects.filter(status=True, id=ids)
            else:
                resoluciones = Resoluciones.objects.filter(status=True).order_by('-fecha')
            if 'fecha' in request.GET:
                fecha = convertir_fecha(request.GET['fecha'])
                resoluciones = resoluciones.filter(fecha=convertir_fecha(request.GET['fecha']))
            if 'idt' in request.GET:
                if int(request.GET['idt']) > 0:
                    tiposelect = int(request.GET['idt'])
                    resoluciones = resoluciones.filter(tipo_id=int(request.GET['idt']))
            if 's' in request.GET:
                search = request.GET['s'].strip()
                listabuscar = []
                for s in search.split(' '):
                    if s:
                        listabuscar.append(s)
                if len(listabuscar) == 1:
                    resoluciones = resoluciones.filter(Q(numeroresolucion__icontains=search)| Q(resuelve__icontains=search))
                else:
                    for s in listabuscar:
                        idres = resoluciones.values_list('id', flat=True).filter(resuelve__icontains=s)
                        for id in idres:
                            lista.append(id)
                    resoluciones = resoluciones.filter(id__in=lista).distinct()
            paging = MiPaginador(resoluciones, 10)
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
            data['fechaselect'] = fecha
            data['ids'] = ids if ids else ""
            data['tiposelect'] = tiposelect
            data['resoluciones'] = page.object_list
            data['email_domain'] = EMAIL_DOMAIN
            return render(request, "adm_resoluciones/view.html", data)
