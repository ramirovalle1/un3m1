# -*- coding: UTF-8 -*-

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect,JsonResponse
from django.shortcuts import render
from django.template.loader import get_template

from datetime import datetime

from decorators import secure_module
from sagest.forms import PeriodoPoaForm, EvaluacionPoaForm, UsuarioPermisoForm, PrevalidacionForm, AccionDocumentoRevisaActividadForm, EvidenciaDocumentalForm, AccionDocumentoRevisaForm, \
    ValidacionPOAForm, ProcesoEleccionForm, ValidarSolicitudForm
from sagest.funciones import encrypt_id
from sagest.models import ProcesoEleccion, SolicitudJustificacionPE,HistorialValidacionJustificacion
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, generar_nombre, log
from sga.templatetags.sga_extras import encrypt
from utils.filtros_genericos import filtro_persona


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    persona = request.session['persona']
    usuario = request.user
    hoy = datetime.now()
    if request.method == 'POST':
        action = request.POST['action']
        # PERMISOS POA
        if action == 'addproceso':
            try:
                form = ProcesoEleccionForm(request.POST)
                if not form.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                proceso = ProcesoEleccion(descripcion=form.cleaned_data['descripcion'],
                                                   periodoacademico=form.cleaned_data['periodoacademico'],
                                                   activo = form.cleaned_data['activo'])
                proceso.save(request)
                log(f'Agrego proceso: {proceso}', request, 'add')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': str(ex)})

        elif action == 'editproceso':
            try:
                instancia = ProcesoEleccion.objects.get(pk=encrypt_id(request.POST['id']))
                form = ProcesoEleccionForm(request.POST, instancia=instancia)
                if not form.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                instancia.descripcion = form.cleaned_data['descripcion']
                instancia.periodoacademico = form.cleaned_data['periodoacademico']
                instancia.activo = form.cleaned_data['activo']
                instancia.save(request)
                log(f'Edito permiso: {instancia}', request, 'edit')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': str(ex)})

        elif action == 'delproceso':
            try:
                instancia = ProcesoEleccion.objects.get(pk=encrypt_id(request.POST['id']))
                instancia.status = False
                instancia.save(request)
                log(f'Elimino proceso: {instancia}', request, 'del')
                return JsonResponse({'error': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'error': True, 'mensaje': str(ex)})

        elif action == 'validarjustificacion':
            try:
                instancia = SolicitudJustificacionPE.objects.get(pk=encrypt_id(request.POST['id']))
                form = ValidarSolicitudForm(request.POST, instancia=instancia)
                if not form.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                instancia.responsable_valida = persona
                instancia.fecha_valida = hoy
                instancia.observacion = form.cleaned_data['observacion']
                instancia.estado = form.cleaned_data['estado']
                instancia.save(request)
                historial = HistorialValidacionJustificacion(solicitud=instancia,
                                                             responsable_valida=persona,
                                                             observacion=form.cleaned_data['observacion'],
                                                             estado=form.cleaned_data['estado'])
                historial.save(request)
                log(f'Valido solicitud de justificación proceso: {instancia}', request, 'del')
                return JsonResponse({'error': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'error': True, 'mensaje': str(ex)})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addproceso':
                try:
                    data['switchery'] = True
                    data['form'] = ProcesoEleccionForm()
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editproceso':
                try:
                    data['switchery'] = True
                    data['periodo'] = proceso = ProcesoEleccion.objects.get(pk=encrypt_id(request.GET['id']))
                    data['id'] = proceso.id
                    data['form'] = ProcesoEleccionForm(initial=model_to_dict(proceso))
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'solicitudes':
                try:
                    data['title'] = u'Solicitudes de Justificación de Sufragio'
                    proceso = ProcesoEleccion.objects.get(pk=encrypt_id(request.GET['id']))
                    search, url_vars, filtro = request.GET.get('s', ''),\
                                               f'&action={action}&id={request.GET["id"]}',\
                                               Q(proceso=proceso, status=True)
                    if search:
                        data['s'] = search = search.strip()
                        filtro = filtro_persona(search, filtro)
                        url_vars += f'&s={search}'
                    listado = SolicitudJustificacionPE.objects.filter(filtro).order_by('-id')
                    paginator = MiPaginador(listado, 20)
                    page = int(request.GET.get('page', 1))
                    paginator.rangos_paginado(page)
                    data['paging'] = paging = paginator.get_page(page)
                    data['listado'] = paging.object_list
                    data['url_vars'] = url_vars
                    data['proceso'] = proceso
                    return render(request, "adm_justificacioneleccion/solicitudesjustificacion.html", data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'validarjustificacion':
                try:
                    data['solicitud'] = solicitud = SolicitudJustificacionPE.objects.get(pk=encrypt_id(request.GET['id']))
                    data['id'] = solicitud.id
                    data['form'] = ValidarSolicitudForm()
                    template = get_template('adm_justificacioneleccion/modal/formvalidar.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Procesos de elección'
                search, url_vars = request.GET.get('s', ''), ''
                filtro = Q(status=True)
                if search:
                    data['s'] = search = search.strip()
                    filtro &= Q(descripcion__unaccent__icontains=search)
                    url_vars += f'&s={search}'
                listado = ProcesoEleccion.objects.filter(filtro).order_by('-id')
                paginator = MiPaginador(listado, 20)
                page = int(request.GET.get('page', 1))
                paginator.rangos_paginado(page)
                data['paging'] = paging = paginator.get_page(page)
                data['listado'] = paging.object_list
                data['url_vars'] = url_vars
                return render(request, "adm_justificacioneleccion/view.html", data)
            except Exception as ex:
                messages.error(request, f'Error: {ex}')
                return HttpResponseRedirect(request.path)
