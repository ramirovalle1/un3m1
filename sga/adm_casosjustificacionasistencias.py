# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import CasosJustificacionForm
from sga.funciones import log, MiPaginador
from django.db.models import Q
from sga.models import CasosJustificacion


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'add':
            try:
                form = CasosJustificacionForm(request.POST)
                if form.is_valid():
                    nombres=form.cleaned_data['nombre']
                    if CasosJustificacion.objects.filter(nombre=nombres, status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                    caso=CasosJustificacion(nombre=form.cleaned_data['nombre'],
                                             descripcion=form.cleaned_data['descripcion'],
                                             activo=form.cleaned_data['activo'])
                    caso.save(request)
                    log(u'Adiciono un Caso de Justificacion de Asistencia para el alumno : %s[%s]' % (caso,caso.id), request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                form = CasosJustificacionForm(request.POST)
                if form.is_valid():
                    caso = CasosJustificacion.objects.get(pk=int(request.POST['id']))
                    caso.nombre=form.cleaned_data['nombre']
                    caso.descripcion = form.cleaned_data['descripcion']
                    caso.activo = form.cleaned_data['activo']
                    caso.save(request)
                    log(u'Edito un Caso de Justificacion de Asistencia para el alumno : %s[%s]' % (caso, caso.id),request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Faltan campos de llenar."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action=='del':
            try:
                caso = CasosJustificacion.objects.get(pk=int(request.POST['id']))
                if caso.solicitudjustificacionasistencia_set.all().exists():
                    return JsonResponse({"result": "bad","mensaje": u"No puede eliminar, tiene solicitud de justificacion realizadas.."})
                caso.delete()
                log(u'Elimino un Caso de Justificacion de Asistencia para el alumno : %s[%s]' % (caso, caso.id),request, "del")
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
                    data['title'] = u'Adicionar caso de justificación'
                    data['form'] = CasosJustificacionForm()
                    return render(request, "adm_casosjustificacionasistencias/add.html", data)
                except Exception as ex:
                    pass

            if action=='del':
                try:
                    data['title'] = u'Eliminar caso de justificación'
                    data['caso'] = CasosJustificacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_casosjustificacionasistencias/eliminar.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar caso de justificación'
                    data['caso'] = caso=CasosJustificacion.objects.get(pk=int(request.GET['id']))
                    form = CasosJustificacionForm(initial={'nombre':caso.nombre,
                                                           'descripcion':caso.descripcion,
                                                           'activo': caso.activo})
                    data['form']= form
                    return render(request, "adm_casosjustificacionasistencias/editar.html", data)
                except Exception as ex:
                    pass
            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Caso de justificación'
            data['casos'] = CasosJustificacion.objects.all()
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    casos = CasosJustificacion.objects.filter(Q(nombre__icontains=search) |
                                                              Q(descripcion__icontains=search)).distinct().\
                                                              order_by('nombre', 'descripcion')
                else:
                    casos = CasosJustificacion.objects.filter(Q(nombre__icontains=ss[0]) &
                                                              Q(nombre__icontains=ss[1])).distinct().\
                                                              order_by('nombre', 'descripcion')
            else:
                    casos = CasosJustificacion.objects.all()
            paging = MiPaginador(casos, 20)
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
            data['casos'] = page.object_list
            return render(request, "adm_casosjustificacionasistencias/view.html", data)