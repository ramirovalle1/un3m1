# -*- coding: UTF-8 -*-
import json
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template.loader import get_template
from django.shortcuts import render
from django.contrib import messages
from decorators import secure_module, last_access
from investigacion.funciones import vicerrector_investigacion_posgrado, coordinador_investigacion
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre
from django.db.models import Q

from sga.models import Persona, CoordinadorCarrera, Notificacion
from sga.templatetags.sga_extras import encrypt
from vincula.forms import ActividadAyudantiaForm, SolicitudDocenteForm, GestionarSolicitudForm
from vincula.models import PeriodoInvestigacion, ActividadAyudantiaInvestigacion, SolicitudDocente, \
    AyudantiaInvestigacion


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
# @last_access
# @transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    periodo_inv = PeriodoInvestigacion.objects.filter(status=True, publico=True, freceptarsolicitud__gte=datetime.now().date()).first()
    dir_investigacion = vicerrector_investigacion_posgrado()
    if persona.es_profesor():
        coordinacion = persona.profesor().coordinacion
        carrera=persona.profesor().carrera_principal_periodo(periodo_inv.periodolectivo)
        dir_facultad = CoordinadorCarrera.objects.filter(carrera=carrera, tipo=3).last()

    if request.method == 'POST':
        action = request.POST['action']

        # Actividades
        if action == 'addactividad':
            with transaction.atomic():
                try:
                    form = ActividadAyudantiaForm(request.POST, request.FILES)
                    if form.is_valid():
                        instancia = ActividadAyudantiaInvestigacion(descripcion=form.cleaned_data['descripcion'])
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

        if action == 'editactividad':
            with transaction.atomic():
                try:
                    filtro=ActividadAyudantiaInvestigacion(id=int(encrypt(request.POST['id'])))
                    form = ActividadAyudantiaForm(request.POST, request.FILES)
                    if form.is_valid():
                        filtro.descripcion = form.cleaned_data['descripcion']
                        filtro.save(request)
                        log(u'Edito actividad: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'delactividad':
            with transaction.atomic():
                try:
                    instancia = ActividadAyudantiaInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino actividad de ayudantias: %s' % instancia, request, "del")
                    res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        # Solicitud Docente
        if action == 'addsolicitud':
            with transaction.atomic():
                try:
                    form = SolicitudDocenteForm(request.POST)
                    if form.is_valid():
                        instancia = SolicitudDocente(proyecto=form.cleaned_data['proyecto'],
                                                     cantidad=form.cleaned_data['cantidad'],
                                                     mensaje=form.cleaned_data['mensaje'],
                                                     solicitante=persona,
                                                     periodoinvestigacion=periodo_inv,
                                                     dir_investigacion = coordinador_investigacion()
                                                     )
                        instancia.save(request)
                    #     Notificacion para director de investigacion

                        notificacion = Notificacion(titulo="Nueva solicitud de ayudantia de investigación",
                                                    cuerpo='El docente {} acaba de solicitar una ayudantia de investigación'.format(instancia.proyecto.profesor),
                                                    destinatario=coordinador_investigacion(),
                                                    url='/adm_ayudantiasinvestigacion',
                                                    object_id=instancia.pk,
                                                    prioridad=1,
                                                    app_label='sga',
                                                    fecha_hora_visible=datetime.now() + timedelta(days=1)
                                                    )
                        notificacion.save()

                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                    messages.success(request, 'Guardado con exito')
                    log(u'Adiciono solicitud de ayudantias de investigacion: %s' % instancia, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'editsolicitud':
            with transaction.atomic():
                try:
                    filtro = SolicitudDocente(id=int(encrypt(request.POST['id'])))
                    form = SolicitudDocenteForm(request.POST, request.FILES)
                    if form.is_valid():
                        filtro.proyecto=form.cleaned_data['proyecto']
                        filtro.cantidad=form.cleaned_data['cantidad']
                        filtro.mensaje=form.cleaned_data['mensaje']
                        filtro.solicitante=persona
                        filtro.periodoinvestigacion=periodo_inv
                        filtro.save(request)
                        log(u'Edito soliciutd de ayudantia: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'delsolicitud':
            with transaction.atomic():
                try:
                    instancia = SolicitudDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Elimino solicitud de ayudantias: %s' % instancia, request, "del")
                    res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        # if action == 'mostrarservicioconf':
        #     with transaction.atomic():
        #         try:
        #             mostrar = eval(request.POST['val'].capitalize())
        #             if mostrar:
        #                 configuraciones = ServicioConfigurado.objects.filter(status=True, mostrar=True,serviciocita_id=int(request.POST['idex'])).exclude(pk=int(request.POST['id']))
        #                 for conf in configuraciones:
        #                     conf.mostrar = False
        #                     conf.save(request)
        #             registro = ServicioConfigurado.objects.get(pk=int(request.POST['id']))
        #             registro.mostrar = mostrar
        #             registro.save(request)
        #             log(u'Mostrar configuracion de servicio : %s (%s)' % (registro, registro.mostrar), request,
        #                 "mostrarservicioconf")
        #             return JsonResponse({"result": True, 'mensaje': 'Cambios guardados'})
        #         except Exception as ex:
        #             transaction.set_rollback(True)
        #             return JsonResponse({"result": False})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:

        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            data['periodo_inv'] = periodo_inv
            # SolicitudesDocente
            if action == 'solicitudes':
                try:
                    data['title'] = u'Solicitudes'
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
                    if search:
                        data['s'] = search
                        filtro = filtro & (Q(descripcion__unaccent__icontains=search))
                        url_vars += '&s=' + search

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
                    request.session['viewactivo'] = 2
                    return render(request, 'adm_ayudantiasinvestigacion/viewsolicitudes.html', data)
                except Exception as ex:
                    return render({'result': False, 'mensaje': '{}'.format(ex)})

            elif action == 'addsolicitud':
                try:
                    form = SolicitudDocenteForm()
                    # form.get_fields(persona.id)
                    data['form'] = form
                    template = get_template("adm_ayudantiasinvestigacion/modal/formsolicituddocente.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editsolicitud':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = SolicitudDocente.objects.get(pk=id)
                    form = SolicitudDocenteForm(initial=model_to_dict(filtro))
                    # form.get_fields(persona.id)
                    data['form'] = form
                    template = get_template("adm_ayudantiasinvestigacion/modal/formsolicituddocente.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            # Actividades
            if action == 'actividades':
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

            if action == 'addactividad':
                try:
                    form = ActividadAyudantiaForm()
                    data['form'] = form
                    template = get_template("adm_ayudantiasinvestigacion/modal/formactividad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'editactividad':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = ActividadAyudantiaInvestigacion.objects.get(pk=id)
                    form = ActividadAyudantiaForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("adm_ayudantiasinvestigacion/modal/formactividad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'buscarpersonas':
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
                data['title'] = u'Ayudantias de ivestigación'
                search, filtro, url_vars = request.GET.get('s', ''), Q(status=True, solicitud__solicitante=persona), ''

                if search:
                    filtro = filtro & (Q(nombre__unaccent__icontains=search))
                    url_vars += '&s=' + search
                    data['s'] = search

                listado = AyudantiaInvestigacion.objects.filter(filtro)
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
                return render(request, 'adm_ayudantiasinvestigacion/viewayudantiasinvestigacion.html', data)
            except Exception as ex:
                return render({'result': False, 'mensaje': '{}'.format(ex)})
