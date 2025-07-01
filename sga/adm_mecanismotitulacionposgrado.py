# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import AulaMantForm, TipoUbicacionAulaForm, MecanismoTitulacionPosgradoForm
from sga.funciones import MiPaginador, log, convertir_fecha, convertir_hora
from sga.models import AulaCoordinacion, Aula, Coordinacion, TipoUbicacionAula, Turno, Sesion, \
    MecanismoTitulacionPosgrado
from datetime import datetime, timedelta, date


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                form = MecanismoTitulacionPosgradoForm(request.POST)
                if form.is_valid():
                        if MecanismoTitulacionPosgrado.objects.filter(nombre=form.cleaned_data['nombre'], status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                        mecanismotitulacionposgrado = MecanismoTitulacionPosgrado(nombre=form.cleaned_data['nombre'],
                                                                                  activo=form.cleaned_data['activo'])
                        mecanismotitulacionposgrado.save(request)
                        log(u'Adiciono mecanismo titulacion posgrado : %s - [%s]' % (mecanismotitulacionposgrado,mecanismotitulacionposgrado.id), request, "add")
                        return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edit':
            try:
                form = MecanismoTitulacionPosgradoForm(request.POST)
                if form.is_valid():
                    mecanismotitulacionposgrado = MecanismoTitulacionPosgrado.objects.get(pk=int(request.POST['id']))
                    mecanismotitulacionposgrado.nombre = form.cleaned_data['nombre']
                    mecanismotitulacionposgrado.activo = form.cleaned_data['activo']
                    mecanismotitulacionposgrado.rubricatitulacionposgrado = form.cleaned_data['rubricatitulacionposgrado']
                    mecanismotitulacionposgrado.save(request)
                    log(u'Edito mecanismo titulacion posgrado : %s - [%s]' % (mecanismotitulacionposgrado,mecanismotitulacionposgrado.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delete':
            try:
                mecanismotitulacionposgrado = MecanismoTitulacionPosgrado.objects.get(pk=int(request.POST['id']))
                log(u'Elimino mecanismo titulacion posgrado: %s - [%s]' % (mecanismotitulacionposgrado,mecanismotitulacionposgrado.id), request, "del")
                mecanismotitulacionposgrado.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Error Mecanismo titulación."})
    else:
        data['title'] = u'Mecanísmo titulación posgrado'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar mecanísmo titulación posgrado'
                    data['form'] = MecanismoTitulacionPosgradoForm()
                    return render(request, "adm_mecanismotitulacionposgrado/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar mecanísmo titulación posgrado'
                    data['mecanismotitulacionposgrado'] = mecanismotitulacionposgrado = MecanismoTitulacionPosgrado.objects.get(pk=int(request.GET['id']))
                    form = MecanismoTitulacionPosgradoForm(initial={'nombre': mecanismotitulacionposgrado.nombre,
                                                                    'rubricatitulacionposgrado': mecanismotitulacionposgrado.rubricatitulacionposgrado,
                                                                    'activo': mecanismotitulacionposgrado.activo})
                    data['form'] = form
                    return render(request, "adm_mecanismotitulacionposgrado/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'delete':
                try:
                    data['title'] = u'Eliminar mecanísmo titulación posgrado'
                    data['mecanismotitulacionposgrado'] = MecanismoTitulacionPosgrado.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_mecanismotitulacionposgrado/delete.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Mecánismos Titulación PosGrado'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    mecanismotitulacionposgrados = MecanismoTitulacionPosgrado.objects.filter(nombre__icontains=search, status=True).order_by('nombre')
            else:
                mecanismotitulacionposgrados = MecanismoTitulacionPosgrado.objects.filter(status=True).order_by('nombre')
            paging = MiPaginador(mecanismotitulacionposgrados, 30)
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
            data['mecanismotitulacionposgrados'] = page.object_list
            return render(request, "adm_mecanismotitulacionposgrado/view.html", data)
