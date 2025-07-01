# -*- coding: UTF-8 -*-
import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template.loader import get_template
from django.shortcuts import render
from django.contrib import messages
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre
from django.db.models import Q

from sga.models import Persona
from sga.templatetags.sga_extras import encrypt
from vincula.forms import ActividadAyudantiaForm, PeriodoInvestigacionForm, GestionarSolicitudForm
from vincula.models import PeriodoInvestigacion, ActividadAyudantiaInvestigacion, SolicitudDocente


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
# @last_access
# @transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']

        # Actividades
        if action == 'addperiodo':
            with transaction.atomic():
                try:
                    form = PeriodoInvestigacionForm(request.POST)
                    if form.is_valid():
                        instancia = PeriodoInvestigacion(nombre=form.cleaned_data['nombre'],
                                                         periodolectivo=form.cleaned_data['periodolectivo'],
                                                         finicio=form.cleaned_data['finicio'],
                                                         ffin=form.cleaned_data['ffin'],
                                                         freceptarsolicitud=form.cleaned_data['freceptarsolicitud'],
                                                         fregistroactividad=form.cleaned_data['fregistroactividad'],
                                                         publico=form.cleaned_data['publico'],
                                                         descripcion=form.cleaned_data['descripcion'])
                        instancia.save(request)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                    messages.success(request, 'Guardado con exito')
                    log(u'Adiciono actividad de ayudantias de investigacion: %s' % instancia, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        elif action == 'editperiodo':
            with transaction.atomic():
                try:
                    filtro = PeriodoInvestigacion(id=int(encrypt(request.POST['id'])))
                    form = PeriodoInvestigacionForm(request.POST)
                    if form.is_valid():
                        filtro.nombre = form.cleaned_data['nombre']
                        filtro.periodolectivo = form.cleaned_data['periodolectivo']
                        filtro.finicio = form.cleaned_data['finicio']
                        filtro.ffin = form.cleaned_data['ffin']
                        filtro.freceptarsolicitud = form.cleaned_data['freceptarsolicitud']
                        filtro.fregistroactividad = form.cleaned_data['fregistroactividad']
                        filtro.publico = form.cleaned_data['publico']
                        filtro.descripcion = form.cleaned_data['descripcion']
                        filtro.save(request)
                        log(u'Edito periodo de investigacion: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        elif action == 'delperiodo':
            with transaction.atomic():
                try:
                    instancia = PeriodoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino periodo de investigación: %s' % instancia, request, "del")
                    res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)
        elif action == 'gestionar':
            with transaction.atomic():
                try:
                    form = GestionarSolicitudForm(request.POST)
                    if form.is_valid():
                        instancia = SolicitudDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                        instancia.val_dir_investigacion = form.cleaned_data['estado']
                        instancia.obs_dir_investigacion = form.cleaned_data['observacion']
                        instancia.fvalidacion_dir_investigacion = datetime.now()
                        instancia.estado = form.cleaned_data['estado']
                        instancia.save(request)
                        log(u'Gestionó solicitud de ayudantia de investigación: %s del docente: %s' % (instancia, instancia.solicitante), request, "edit")
                        res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        elif action == 'publicarperiodo':
            with transaction.atomic():
                try:
                    publico = eval(request.POST['val'].capitalize())
                    if publico:
                        periodos = PeriodoInvestigacion.objects.filter(status=True, publico=True).exclude(
                            pk=int(request.POST['id']))
                        for p in periodos:
                            p.publico = False
                            p.save(request)
                    registro = PeriodoInvestigacion.objects.get(pk=int(request.POST['id']))
                    registro.publico = publico
                    registro.save(request)
                    log(u'Publicar periodo de investigacion: %s (%s)' % (registro, registro.publico), request,
                        "edit")
                    return JsonResponse({"result": True, 'mensaje': 'Cambios guardados'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addperiodo':
                try:
                    form = PeriodoInvestigacionForm()
                    data['form'] = form
                    template = get_template("adm_controlayudantias/modal/formperiodoinvestigacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editperiodo':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = PeriodoInvestigacion.objects.get(pk=id)
                    form = PeriodoInvestigacionForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_controlayudantias/modal/formperiodoinvestigacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            # SolicitudesDocente
            elif action == 'solicitudes':
                try:
                    data['title'] = u'Solicitudes de ayudantia'
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
                    periodoinvestigacion = False
                    id = request.GET['id'] if 'id' in request.GET else None
                    if search:
                        data['s'] = search
                        filtro = filtro & (Q(descripcion__unaccent__icontains=search))
                        url_vars += '&s=' + search
                    if id:
                        data['id'] = id
                        filtro = filtro & (Q(periodoinvestigacion_id=int(encrypt(id))))
                        url_vars += '&id=' + encrypt(id)
                        periodoinvestigacion = True
                    if periodoinvestigacion:
                        data['periodoinvestigacion'] = PeriodoInvestigacion.objects.get(id=int(encrypt(id)))

                    listado = SolicitudDocente.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(listado, 10)
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
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    data['listcount'] = len(listado)
                    request.session['viewactivo'] = 3
                    return render(request, 'adm_controlayudantias/viewsolicitudes.html', data)
                except Exception as ex:
                    return render({'result': False, 'mensaje': '{}'.format(ex)})

            elif action == 'gestionar':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = SolicitudDocente.objects.get(pk=id)
                    form = GestionarSolicitudForm(initial=model_to_dict(filtro))
                    # form.get_fields(persona.id)
                    data['form'] = form
                    template = get_template("adm_ayudantiasinvestigacion/modal/formgestionarsolicituddocente.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addactividad':
                try:
                    form = ActividadAyudantiaForm()
                    data['form'] = form
                    template = get_template("adm_ayudantiasinvestigacion/modal/formactividad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editactividad':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = ActividadAyudantiaInvestigacion.objects.get(pk=id)
                    form = ActividadAyudantiaForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_ayudantiasinvestigacion/modal/formactividad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            # Actividades
            elif action == 'actividades':
                try:
                    data['title'] = u'Actividades'
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
                    if search:
                        data['s'] = search
                        filtro = filtro & (Q(descripcion__unaccent__icontains=search))
                        url_vars += '&s=' + search

                    listado = ActividadAyudantiaInvestigacion.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(listado, 10)
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
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    data['listcount'] = len(listado)
                    request.session['viewactivo'] = 3
                    return render(request, 'adm_ayudantiasinvestigacion/viewactividades.html', data)
                except Exception as ex:
                    return render({'result': False, 'mensaje': '{}'.format(ex)})

            elif action == 'addactividad':
                try:
                    form = ActividadAyudantiaForm()
                    data['form'] = form
                    template = get_template("adm_ayudantiasinvestigacion/modal/formactividad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editactividad':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = ActividadAyudantiaInvestigacion.objects.get(pk=id)
                    form = ActividadAyudantiaForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_ayudantiasinvestigacion/modal/formactividad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'buscarpersonas':
                try:
                    idsexcluidas = []
                    idsagregados = request.GET['idsagregados']
                    if idsagregados:
                        idsagregados = idsagregados.split(',')
                        idsexcluidas += [idl for idl in idsagregados]
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    qspersona = Persona.objects.filter(status=True, administrativo__isnull=False).exclude(
                        id__in=idsexcluidas).order_by('apellido1')
                    if len(s) == 1:
                        qspersona = qspersona.filter((Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(
                            cedula__icontains=q) | Q(apellido2__icontains=q) | Q(cedula__contains=q)),
                                                     Q(status=True)).distinct()[:15]
                    elif len(s) == 2:
                        qspersona = qspersona.filter((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) |
                                                     (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) |
                                                     (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1]))).filter(
                            status=True).distinct()[:15]
                    else:
                        qspersona = qspersona.filter(
                            (Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(apellido2__contains=s[2])) |
                            (Q(nombres__contains=s[0]) & Q(nombres__contains=s[1]) & Q(
                                apellido1__contains=s[2]))).filter(status=True).distinct()[:15]

                    resp = [{'id': qs.pk, 'text': f"{qs.nombre_completo_inverso()}",
                             'documento': qs.documento(),
                             'foto': qs.get_foto()} for qs in qspersona]
                    return HttpResponse(json.dumps({'status': True, 'results': resp}))
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Control de ayudantias de investigación'
                search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''

                if search:
                    filtro = filtro & (Q(nombre__unaccent__icontains=search))
                    url_vars += '&s=' + search
                    data['s'] = search

                listado = PeriodoInvestigacion.objects.filter(filtro)
                paging = MiPaginador(listado, 10)
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
                data["url_vars"] = url_vars
                data['listado'] = page.object_list
                data['listcount'] = len(listado)
                request.session['viewactivo'] = 1
                return render(request, 'adm_controlayudantias/viewcontrolayudantias.html', data)
            except Exception as ex:
                return render({'result': False, 'mensaje': '{}'.format(ex)})
