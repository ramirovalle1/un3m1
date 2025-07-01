import json

from django.contrib import messages
from django.db.models import Q
from django.forms import model_to_dict
from django.template.loader import get_template

from bd.forms import CrearSolicitudForm, CrearComentarioForm, CrearActvSecundariaForm
from bd.models import IncidenciaSCRUM, ProcesoSCRUM, ComentarioIncidenciaSCRUM, IncidenciaSecundariasSCRUM, ESTADO_REQUERIMIENTO, PRIORIDAD_REQUERIMIENTO, APP_LABEL
from decorators import secure_module, last_access
from datetime import datetime, time
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection, connections
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render

from pdip.models import ActividadesPerfil
from sagest.funciones import encrypt_id
from sagest.models import BitacoraActividadDiaria, TIPO_SISTEMA, Departamento
from sga.commonviews import adduserdata
from sga.funciones import log, MiPaginador, convertir_fecha_hora_invertida, notificacion, generar_nombre
from sga.models import Persona
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module()
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema = request.build_absolute_uri('/')[:-1].strip("/")
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addactividad':
            try:
                form = CrearSolicitudForm(request.POST, request.FILES)
                if form.is_valid():
                    filtro = IncidenciaSCRUM(categoria=form.cleaned_data['categoria'],
                                             titulo=form.cleaned_data['titulo'],
                                             descripcion=form.cleaned_data['descripcion'],
                                             app=form.cleaned_data['app'],
                                             prioridad=form.cleaned_data['prioridad'],
                                             estado=1,
                                             asignadoa=persona,
                                             asignadopor=form.cleaned_data['asignadopor'],
                                             finicioactividad=form.cleaned_data['finicioactividad'])
                    filtro.save(request)
                    log(u'Autoasigno una Incidencia: %s' % filtro, request, 'add')
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        if action == 'editactividad':
            try:
                form = CrearSolicitudForm(request.POST)
                filtro = IncidenciaSCRUM.objects.get(id=int(request.POST['id']))
                if form.is_valid():
                    filtro.categoria = form.cleaned_data['categoria']
                    filtro.titulo = form.cleaned_data['titulo']
                    filtro.descripcion = form.cleaned_data['descripcion']
                    filtro.asignadopor = form.cleaned_data['asignadopor']
                    filtro.app = form.cleaned_data['app']
                    filtro.finicioactividad = form.cleaned_data['finicioactividad']
                    filtro.prioridad = form.cleaned_data['prioridad']
                    filtro.save(request)
                    log(u'Edito Responsable de Gestión, Gestión Documental: %s' % filtro, request, action)
                    return JsonResponse({'result': False, 'mensaje': 'Edicion Exitosa'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        if action == 'delactividad':
            try:
                with transaction.atomic():
                    instancia = IncidenciaSCRUM.objects.get(pk=request.POST['id'])
                    instancia.status = False
                    instancia.save(request)
                    log(f'Elimino una incidencia en {instancia.__str__()} - {instancia.get_estado_display()}', request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'do':
            try:
                with transaction.atomic():
                    idactividad = request.POST['idactividad']
                    actividad = IncidenciaSCRUM.objects.get(pk=idactividad)
                    actividad.estado = 1
                    actividad.ffinactividad = None
                    actividad.save(request)
                    log(u'Puso en pendiente una actividad: %s' % actividad, request, "change")
                    qsincidencia =  IncidenciaSCRUM.objects.values('id').filter(status=True, asignadoa=persona)
                    res_json = {"resp": True, 'totdo': qsincidencia.filter(estado=1).count(),'totprogress': qsincidencia.filter(estado=2).count(),'totdone': qsincidencia.filter(estado=3)[:10].count()}
            except Exception as ex:
                res_json = {'resp': False, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'progress':
            try:
                with transaction.atomic():
                    idactividad = request.POST['idactividad']
                    actividad = IncidenciaSCRUM.objects.get(pk=idactividad)
                    actividad.estado = 2
                    actividad.ffinactividad = None
                    actividad.save(request)
                    log(u'Puso en marcha una incidencia: %s' % actividad, request, "change")
                    qsincidencia =  IncidenciaSCRUM.objects.values('id').filter(status=True, asignadoa=persona)
                    res_json = {"resp": True, 'totdo': qsincidencia.filter(estado=1).count(),'totprogress': qsincidencia.filter(estado=2).count(),'totdone': qsincidencia.filter(estado=3)[:10].count()}
            except Exception as ex:
                res_json = {'resp': False, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'done':
            try:
                with transaction.atomic():
                    idactividad = request.POST['idactividad']
                    actividad = IncidenciaSCRUM.objects.get(pk=idactividad)
                    actividad.estado = 3
                    actividad.ffinactividad = datetime.now()
                    actividad.save(request)
                    requerimiento = actividad.requerimiento
                    if requerimiento:
                        requerimiento.estado = 3
                        requerimiento.estadoevaluacion = 1
                        requerimiento.save(request, update_fields=['estado', 'estadoevaluacion'])

                        titulo = f'El requerimiento ({requerimiento}) se finalizo correctamente.'
                        cuerpo = f'El requerimiento {requerimiento} receptado fue finalizado satisfactoriamente, por favor revisar las opciones solicitadas.'
                        notificacion(titulo, cuerpo, requerimiento.responsable, None,
                                     f'/adm_ingresarequerimiento?actionrequerimientos&idp={encrypt(requerimiento.periodo.id)}&s={requerimiento.procedimiento}',
                                     requerimiento.responsable.pk, 1, 'sga-sagest',
                                     IncidenciaSCRUM, request)
                    log(u'Puso en marcha una incidencia: %s' % actividad, request, "change")
                    qsincidencia =  IncidenciaSCRUM.objects.values('id').filter(status=True, asignadoa=persona)
                    res_json = {"resp": True, 'totdo': qsincidencia.filter(estado=1).count(),'totprogress': qsincidencia.filter(estado=2).count(),'totdone': qsincidencia.filter(estado=3)[:10].count()}
            except Exception as ex:
                res_json = {'resp': False, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'listcomentarios':
            try:
                form = CrearComentarioForm(request.POST, request.FILES)
                if form.is_valid():
                    filtro = ComentarioIncidenciaSCRUM(incidencia=form.cleaned_data['incidencia'],
                                             observacion=form.cleaned_data['observacion'])
                    filtro.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre(str(filtro.id), newfile._name)
                        filtro.archivo = newfile
                        filtro.save(request)
                        if filtro.observacion and not filtro.observacion=='':
                            titulo = f'El requerimiento ({filtro.incidencia.requerimiento}) se tiene novedades.'
                            cuerpo = f'El requerimiento {filtro.incidencia.requerimiento} tiene el siguiente comentario: {filtro.observacion}.'
                            notificacion(titulo, cuerpo, filtro.incidencia.requerimiento.responsable, None,
                                         f'/adm_ingresarequerimiento?actionrequerimientos&idp={encrypt(filtro.incidencia.requerimiento.periodo.id)}&s={filtro.incidencia.requerimiento.procedimiento}',
                                         filtro.incidencia.requerimiento.responsable.pk, 1, 'sga-sagest',
                                         IncidenciaSCRUM, request)
                    log(u'Comento una Incidencia: %s' % filtro, request, 'add')
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        if action == 'listactividadessecundarias':
            try:
                form = CrearActvSecundariaForm(request.POST, request.FILES)
                if form.is_valid():
                    filtro = IncidenciaSecundariasSCRUM(incidencia=form.cleaned_data['incidencia'],
                                                        descripcion=form.cleaned_data['descripcion'],
                                                        asignadoa = form.cleaned_data['asignadoa'],
                                                        prioridad=form.cleaned_data['prioridad'],
                                                        finicioactividad=form.cleaned_data['finicioactividad'])
                    filtro.save(request)
                    log(u'Comento una Incidencia: %s' % filtro, request, 'add')
                    return JsonResponse({'result': False, 'mensaje': u'Guardado con exito'})
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                         "mensaje": "Error en el formulario"}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error al guardar los datos. {ex}'})

        if action == 'migrarbitacora':
            try:
                listado = json.loads(request.POST['lista_items1'])
                iddepartamento = persona.mi_departamento().id if persona.mi_departamento() else request.POST.get('departamento', None)
                for incidencia in listado:
                    actividad = IncidenciaSCRUM.objects.get(id=incidencia['id_incidencia'])
                    hora = actividad.fecha_creacion.time()
                    if not time(8, 0) < hora < time(17, 0):
                        hora = time(9, 0)
                    fecha = datetime.strptime(incidencia['fechainicio'], '%Y-%m-%d').date()
                    fecha = datetime.combine(fecha, hora)
                    tipoactividad = incidencia['tipoactividad'] if 'tipoactividad' in incidencia else None
                    # if not actividad.actividad_bitacora():
                    bitacora = BitacoraActividadDiaria(persona=persona,
                                                       titulo=incidencia['titulo'],
                                                       fecha=fecha,
                                                       fechafin=actividad.ffinactividad,
                                                       departamento_id=iddepartamento,
                                                       descripcion=incidencia['descripcion'],
                                                       link='',
                                                       tiposistema=actividad.tipo_sistema(int(incidencia['tiposistema'])),
                                                       actividades_id=tipoactividad,
                                                       incidenciascrum=actividad,
                                                       departamento_requiriente=actividad.categoria.direccion)
                    bitacora.save(request)
                    log(f'Agrego actividad a bitácora {bitacora}', request, 'add')
                return JsonResponse({'result':False, 'mensaje':'Guardado con exito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, 'mensaje': f'Error: {ex}'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addactividad':
                try:
                    data['title'] = u'Crear Actividad'
                    form = CrearSolicitudForm()
                    form.fields['finicioactividad'].initial = str(datetime.now().date())
                    form.fields['asignadopor'].queryset = Persona.objects.none()
                    data['form'] = form
                    template = get_template("adm_actividades_scrum/modal/formactividad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'editactividad':
                try:
                    data['title'] = u'Editar Actividad'
                    data['id'] = id = request.GET['id']
                    filtro = IncidenciaSCRUM.objects.get(pk=id)
                    initial = model_to_dict(filtro)
                    form = CrearSolicitudForm(initial=initial)
                    form.fields['finicioactividad'].initial = str(filtro.finicioactividad)
                    if filtro.asignadopor:
                        form.fields['asignadopor'].queryset = Persona.objects.filter(id=filtro.asignadopor.id)
                    else:
                        form.fields['asignadopor'].queryset = Persona.objects.none()
                    data['form'] = form
                    template = get_template("adm_actividades_scrum/modal/formactividad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'buscarpersonas':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    querybase = Persona.objects.filter(status=True, ).order_by('apellido1')
                    if len(s) == 1:
                        per = querybase.filter((Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(
                            cedula__icontains=q) | Q(apellido2__icontains=q) | Q(cedula__contains=q)),
                                               Q(status=True)).distinct()[:15]
                    elif len(s) == 2:
                        per = querybase.filter((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) |
                                               (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) |
                                               (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1]))).filter(
                            status=True).distinct()[:15]
                    else:
                        per = querybase.filter(
                            (Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(apellido2__contains=s[2])) |
                            (Q(nombres__contains=s[0]) & Q(nombres__contains=s[1]) & Q(
                                apellido1__contains=s[2]))).filter(
                            status=True).distinct()[:15]
                    data = {"result": "ok",
                            "results": [{"id": x.id, "name": "{} - {}".format(x.cedula, x.nombre_completo())} for x in
                                        per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'listcomentarios':
                try:
                    data ['fkincidencia'] = fkincidencia = request.GET.get('id')
                    form = CrearComentarioForm()
                    form.fields['categoria'].queryset = ProcesoSCRUM.objects.none()
                    form.fields['asignadoa'].queryset = Persona.objects.none()
                    form.fields['incidencia'].queryset = IncidenciaSCRUM.objects.filter(pk=fkincidencia)
                    data['form'] = form
                    template = get_template("adm_actividades_scrum/modal/formactividad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'listactividadessecundarias':
                try:
                    data['title'] = u'Ver Actividades Secundaria'
                    data['fkincidencia'] = fkincidencia = request.GET.get('id')
                    form = CrearActvSecundariaForm()
                    form.fields['incidencia'].queryset = IncidenciaSCRUM.objects.filter(pk=fkincidencia)
                    form.fields['finicioactividad'].initial = str(datetime.now().date())
                    form.fields['asignadoa'].queryset = Persona.objects.none()
                    data['form'] = form
                    template = get_template("adm_actividades_scrum/modal/formactividad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'viewactv':
                try:
                    data['title'] = u'Actividad'
                    data['id'] = id = request.GET['id']
                    actv = IncidenciaSCRUM.objects.filter(pk=id)
                    if actv:
                        data['actividades'] = actv
                        template = get_template("adm_actividades_scrum/modal/secundcoment.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, 'message': "No se encontraron actividades"})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'viewcomentarios':
                try:
                    data['title'] = u'Comentarios'
                    data['id'] = id = request.GET['id']
                    coment = ComentarioIncidenciaSCRUM.objects.filter(incidencia=id).order_by('fecha_creacion')
                    if coment:
                        data['comentarios'] = coment
                        template = get_template("adm_actividades_scrum/modal/secundcoment.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, 'message': "No se encontraron comentarios"})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'viewactsecundarias':
                try:
                    data['title'] = u'Actividades Secundarias'
                    data['id'] = id = request.GET['id']
                    secont = IncidenciaSecundariasSCRUM.objects.filter(incidencia=id).order_by('fecha_creacion')
                    if secont:
                        data['secundarias'] = secont
                        template = get_template("adm_actividades_scrum/modal/secundcoment.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, 'message': "No se encontraron actividades"})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'listfinalizadas':
                try:
                    data['title'] = u'Lista de Actividades'

                    criterio, desde, hasta, categoria, prioridad, estado, filtro, url_vars = request.GET.get('criterio', ''), request.GET.get('desde', ''), request.GET.get('hasta', ''), request.GET.get('categoria', ''),request.GET.get('prioridad', ''), request.GET.get('estado', ''), (Q(status=True)), f'&action={action}'


                    if criterio:
                        data['criterio'] = criterio
                        filtro = filtro & (Q(titulo__unaccent__icontains=criterio) | Q(descripcion__search=criterio))
                        url_vars += '&criterio=' + criterio

                    if desde:
                        data['desde'] = desde
                        filtro = filtro & (Q(finicioactividad__gte=desde))
                        url_vars += '&desde=' + desde

                    if hasta:
                        data['hasta'] = hasta
                        filtro = filtro & Q(ffinactividad__lte=hasta)
                        url_vars += "&hasta={}".format(hasta)

                    if categoria:
                        data['categoria'] = int(categoria)
                        filtro = filtro & Q(categoria__id=categoria)
                        url_vars += "&categoria{}".format(categoria)

                    if prioridad:
                        data['prioridad'] = int(prioridad)
                        filtro &= Q(prioridad=prioridad)
                        url_vars += "&prioridad{}".format(prioridad)

                    if estado:
                        data['estado'] = int(estado)
                        filtro = filtro & Q(estado=estado)
                        url_vars += "&estado{}".format(estado)

                    listado = IncidenciaSCRUM.objects.filter(asignadoa=persona).filter(filtro).order_by('-id')
                    paging = MiPaginador(listado, 15)
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
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    data['comboestado'] = ESTADO_REQUERIMIENTO
                    data['comboprioridad'] = PRIORIDAD_REQUERIMIENTO
                    data['combocategorias'] = ProcesoSCRUM.objects.values('id', 'descripcion').filter(status=True)
                    #data['listadofin'] = IncidenciaSCRUM.objects.filter(estado=3)
                    #data['categorialist'] = ProcesoSCRUM.objects.filter(status=True)


                    return render(request, "adm_actividades_scrum/viewlistafinalizadas.html", data)
                except Exception as ex:
                    pass

            if action == 'subincidenciasview':
                try:
                    data['title'] = u'Mi tablero de actividades'

                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''

                    if search:
                        filtro = filtro & (Q(titulo__icontains=search))
                        url_vars += '&s=' + search
                        data['s'] = search

                    qsbase = IncidenciaSecundariasSCRUM.objects.filter(incidencia_id= request.GET['id']).filter(filtro)

                    data['listpendientes'] = listpendientes = qsbase.filter(estado=1)
                    data['listenproceso'] = listenproceso = qsbase.filter(estado=2)
                    data['listfinalizadas'] = listfinalizadas = qsbase.filter(estado=3)
                    data['totpendiente'] = len(listpendientes)
                    data['totenproceso'] = len(listenproceso)
                    data['totfinalizada'] = len(listfinalizadas)
                    template = get_template("adm_actividades_scrum/modal/subincidenciasview.html")
                    return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": 'bad', 'message': str(ex)})

            if action == 'migrarbitacora':
                try:
                    qsbase = IncidenciaSCRUM.objects.filter(asignadoa=persona, estado__in=[2, 3], status=True,categoria__isnull=False).order_by('-finicioactividad')
                    listado = []
                    tipoactividades = []
                    for actividad in qsbase:
                        if not actividad.actividad_bitacora():
                            context = {'id': actividad.id,
                                       'inicio': actividad.finicioactividad,
                                       'fin': actividad.ffinactividad,
                                       'titulo': actividad.titulo,
                                       'descripcion': actividad.descripcion.strip(),
                                       'departamento': actividad.categoria.direccion,
                                       'app': actividad.app}
                            listado.append(context)
                            for actividad_s in actividad.incidencias_secundarias():
                                if not BitacoraActividadDiaria.objects.filter(status=True, fecha__date=actividad_s.finicioactividad.date(), descripcion=actividad_s.descripcion).exists():
                                    context = {
                                        'id': actividad.id,
                                        'inicio': actividad_s.finicioactividad,
                                        'fin': actividad_s.ffinactividad,
                                        'titulo': actividad.titulo,
                                        'descripcion': actividad_s.descripcion.strip(),
                                        'departamento': actividad.categoria.direccion,
                                        'app': actividad.app,
                                    }
                                    listado.append(context)
                    if persona.contratodip_set.filter(status=True).exists():
                        contratodip = persona.contratodip_set.filter(status=True).last()
                        actividades = contratodip.cargo.actividadescontratoperfil_set.filter(status=True).all()
                        actextra = contratodip.actividadescontratoperfil_set.filter(status=True).all()
                        acti = actividades.values_list('actividad_id', flat=True) | actextra.values_list('actividad_id',flat=True)
                        tipoactividades = ActividadesPerfil.objects.filter(status=True, pk__in=acti)

                    data['apps'] = APP_LABEL
                    data['mi_departamento'] = departamento = persona.mi_departamento()
                    if not departamento:
                        data['departamentos'] = Departamento.objects.filter(status=True)
                    data['tipoactividades'] = tipoactividades
                    data['incidencias'] = listado
                    template = get_template('adm_actividades_scrum/modal/formmigracion.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': f'Error: {ex}'})

            elif action == 'detallerequerimiento':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    data['requerimiento'] = IncidenciaSCRUM.objects.get(id=id).requerimiento
                    template = get_template('scrum_actividades/modal/detallerequerimiento.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
        else:
            try:
                data['title'] = u'Mi tablero de actividades'

                search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''

                if search:
                    filtro = filtro & (Q(titulo__icontains=search))
                    url_vars += '&s=' + search
                    data['s'] = search

                qsbase = IncidenciaSCRUM.objects.filter(asignadoa=persona).filter(filtro)
                data['listpendientes'] = listpendientes = qsbase.filter(estado=1).order_by('-fecha_creacion')
                data['listenproceso'] = listenproceso = qsbase.filter(estado=2).order_by('-fecha_modificacion')
                listfinalizadas = qsbase.filter(estado=3).order_by('-ffinactividad')
                data['listfinalizadas'] = limite = listfinalizadas[:10]
                data['totpendiente'] = len(listpendientes)
                data['totenproceso'] = len(listenproceso)
                data['totfinalizada'] = len(limite)
                data['mas']=True if len(listfinalizadas)  else False
                qsbase = IncidenciaSCRUM.objects.filter(asignadoa=persona, estado__in=[2, 3], status=True).order_by('-finicioactividad')
                for actividad in qsbase:
                    if not actividad.actividad_bitacora():
                        data['puede_migrar'] = True
                        break
                data["url_vars"] = url_vars

                return render(request,'adm_actividades_scrum/view.html',data)
            except Exception as ex:
                msg = ex.__str__()
                return HttpResponseRedirect(f"/?info=Error al obtener los datos. {msg}")
                # pass