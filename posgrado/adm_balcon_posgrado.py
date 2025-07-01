import json
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.db import transaction
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template

from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, generar_nombre
from sga.templatetags.sga_extras import encrypt

from posgrado.models import IntegranteGrupoAtencionBalcon, GrupoAtencionBalcon, SolicitudBalcon

class HelperProfesorMateria:
    def __init__(self, obj):
        self.obj = obj

    def get_solicitud_nuevas(self):
        return SolicitudBalcon.objects.filter(materia_asignada__materia__profesormateria=self.obj,
                                              estado=SolicitudBalcon.EstadoSolicitud.NUEVO).values('id').count()

    @staticmethod
    def get_all_solicitudes_nuevas_count(profesor):

        return SolicitudBalcon.objects.filter(status=True, materia_asignada__materia__profesormateria__profesor=profesor).values('id')

def validar_integrante_grupo(id_grupo, id_persona):
    return IntegranteGrupoAtencionBalcon.objects.filter(grupo_atencion=id_grupo, integrante=id_persona).exists()


@login_required(redirect_field_name='ret', login_url='/loginposgrado')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    hoy = datetime.now().date()
    data['personasesion'] = persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']
    ver_listado = False
    puede_configurar = False

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'dep_atencion_add':
            with transaction.atomic():
                try:
                    from posgrado.forms import DepartamentoAtencionBalconForm
                    from posgrado.models import DepartamentoAtencionBalcon
                    form = DepartamentoAtencionBalconForm(request.POST)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                    eDep = DepartamentoAtencionBalcon(
                        nombre=form.cleaned_data['nombre'],
                    )
                    eDep.save(request)
                    messages.success(request, 'Guardado con éxito')
                    return JsonResponse({'isSuccess': True, 'message': 'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'isSuccess': False, 'message': f'Error: {ex}'})

        if action == 'dep_atencion_edit':
            with transaction.atomic():
                try:
                    from posgrado.forms import DepartamentoAtencionBalconForm
                    from posgrado.models import DepartamentoAtencionBalcon
                    form = DepartamentoAtencionBalconForm(request.POST)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                    eDep = DepartamentoAtencionBalcon.objects.get(pk=int(encrypt(request.POST['id'])))
                    eDep.nombre = form.cleaned_data['nombre']
                    eDep.save(request)
                    messages.success(request, 'Editado con éxito')
                    return JsonResponse({'isSuccess': True, 'message': 'Editado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'isSuccess': False, 'message': f'Error: {ex}'})

        if action == 'dep_atencion_delete':
            with transaction.atomic():
                try:
                    from posgrado.models import DepartamentoAtencionBalcon
                    eDep = DepartamentoAtencionBalcon.objects.get(pk=int(encrypt(request.POST['id'])))
                    if not eDep.puede_eliminar():
                        raise NameError('El departamento de atención tiene grupos asociados')
                    eDep.status = False
                    eDep.save(request)
                    messages.success(request, 'Eliminado con éxito')
                    res_json = {"error": False}
                except Exception as ex:
                    transaction.set_rollback(True)
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        if action == 'dep_atencion_grupo_add':
            with transaction.atomic():
                try:
                    from posgrado.forms import GrupoAtencionBalconForm
                    from posgrado.models import DepartamentoAtencionBalcon
                    if not 'id' in request.POST:
                        raise NameError('No se ha especificado el departamento de atención')
                    eDep = DepartamentoAtencionBalcon.objects.get(pk=int(encrypt(request.POST['id'])))

                    form = GrupoAtencionBalconForm(request.POST)
                    id_lider = request.POST['lider']
                    ids_integrantes = request.POST.getlist('integrantes') if 'integrantes' in request.POST else []
                    form.edit(id_lider, ids_integrantes)
                    if not ids_integrantes:
                        form.ocultar_edit()
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse(
                            {'isSuccess': False, "form": form_error, "mensaje": "Error en el formulario"})

                    if verificar_lider(form.cleaned_data['lider']):
                        raise NameError('El líder seleccionado ya pertenece a otro grupo de atención')

                    eGrupo = GrupoAtencionBalcon(
                        nombre=form.cleaned_data['nombre'],
                        lider=form.cleaned_data['lider'],
                        departamento_atencion=eDep
                    )
                    eGrupo.save(request)
                    if ids_integrantes:
                        for integrante in form.cleaned_data['integrantes']:
                            if validar_integrante_grupo(eGrupo.id, integrante.id):
                                transaction.set_rollback(True)
                                return JsonResponse({'isSuccess': False,
                                                     'message': f'El integrante {integrante} ya pertenece al grupo de atención'})
                            if verificar_lider(integrante):
                                raise NameError(f'El integrante {integrante.__str__()} es lider de grupo de atención')
                            eIntegrante = IntegranteGrupoAtencionBalcon(
                                grupo_atencion=eGrupo,
                                integrante=integrante)
                            eIntegrante.save(request)
                    messages.success(request, 'Guardado con éxito')
                    return JsonResponse({'isSuccess': True, 'message': 'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    messages.error(request, f'Error: {ex}')
                    return JsonResponse({'results': False, 'message': f'Error: {ex}'})

        if action == 'dep_atencion_grupo_edit':
            try:
                from posgrado.forms import GrupoAtencionBalconForm
                if not 'id' in request.POST:
                    raise NameError('No se ha especificado el grupo de atención')

                form = GrupoAtencionBalconForm(request.POST)
                id_lider = request.POST['lider']
                ids_integrantes = request.POST.getlist('integrantes') if 'integrantes' in request.POST else []
                form.edit(id_lider, ids_integrantes)
                form.ocultar_edit()
                if not form.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse(
                        {'isSuccess': False, "form": form_error, "mensaje": "Error en el formulario"})
                eGrupo = GrupoAtencionBalcon.objects.get(pk=int(encrypt(request.POST['id'])))
                if verificar_lider(form.cleaned_data['lider'], eGrupo.id):
                    raise NameError('El líder seleccionado ya pertenece a otro grupo de atención')
                eGrupo.nombre = form.cleaned_data['nombre']
                eGrupo.lider = form.cleaned_data['lider']
                eGrupo.save(request)
                if ids_integrantes:
                    ids_integrantes_clean = form.cleaned_data['integrantes'].values_list('id', flat=True)
                    for integrante_id in ids_integrantes_clean:
                        IntegranteGrupoAtencionBalcon.objects.update_or_create(
                            grupo_atencion=eGrupo,
                            integrante_id=integrante_id,
                            defaults={'activo': True}
                        )
                    IntegranteGrupoAtencionBalcon.objects.filter(grupo_atencion=eGrupo).exclude(
                        integrante_id__in=ids_integrantes_clean).update(activo=False)
                messages.success(request, 'Editado con éxito')
                return JsonResponse({'isSuccess': True, 'message': 'Editado con éxito'})
            except Exception as ex:
                return JsonResponse({"isSuccess": False, "message": ex.__str__()})

        if action == 'dep_atencion_grupo_delete':
            with transaction.atomic():
                try:
                    eGrupo = GrupoAtencionBalcon.objects.get(pk=int(encrypt(request.POST['id'])))
                    if eGrupo.get_integrantes().exists():
                        raise NameError('El grupo de atención tiene integrantes asociados')
                    eGrupo.status = False
                    eGrupo.save(request)
                    messages.success(request, 'Eliminado con éxito')
                    res_json = {"error": False}
                except Exception as ex:
                    transaction.set_rollback(True)
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)


        if action == 'activa_integrante':
            try:
                from posgrado.forms import IntegranteGrupoAtencionBalconForm
                if not 'idin' in request.POST:
                    raise NameError('No se ha especificado el integrante')
                if not 'estado' in request.POST:
                    raise NameError('No se ha especificado el estado')
                eIntegrante = IntegranteGrupoAtencionBalcon.objects.get(pk=int(encrypt(request.POST['idin'])))
                eIntegrante.activo = not eIntegrante.activo
                eIntegrante.save(request)
                aData = {'isSuccess': True, 'id_grupo': encrypt(eIntegrante.grupo_atencion_id)}
                return JsonResponse(aData)
            except Exception as ex:
                return JsonResponse({"isSuccess": False, "message": ex.__str__()})

        if action == 'gestionar_integrantes':
            try:
                from posgrado.forms import IntegranteGrupoAtencionBalconForm
                if not 'id' in request.POST:
                    raise NameError('No se ha especificado el grupo de atención')
                eGrupo = GrupoAtencionBalcon.objects.get(pk=int(encrypt(request.POST['id'])))

                ids_integrantes = request.POST.getlist('integrantes') if 'integrantes' in request.POST else []
                if ids_integrantes:
                    form = IntegranteGrupoAtencionBalconForm(request.POST)
                    form.edit(ids_integrantes)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse(
                            {'isSuccess': False, "form": form_error, "mensaje": "Error en el formulario"})
                    ids_integrantes_clean = form.cleaned_data['integrantes'].values_list('id', flat=True)
                    for integrante_id in ids_integrantes_clean:
                        if verificar_lider(integrante_id, eGrupo.id):
                            raise NameError(f'El integrante {integrante_id} es lider de un grupoo de Atención.')
                        IntegranteGrupoAtencionBalcon.objects.update_or_create(
                            grupo_atencion=eGrupo,
                            integrante_id=integrante_id,
                            defaults={'activo': True}
                        )
                messages.success(request, 'Guardado con éxito')
                return JsonResponse({'isSuccess': True, 'message': 'Guardado con éxito'})

            except Exception as ex:
                return JsonResponse({"isSuccess": False, "message": ex.__str__()})

        if action == 'dep_atencion_grupo_delete':
            try:
                eGrupo = GrupoAtencionBalcon.objects.get(pk=int(encrypt(request.GET['id'])))
                eGrupo.status = False
                eGrupo.save(request)
                messages.success(request, 'Eliminado con éxito')
                return JsonResponse({'isSuccess': True, 'message': 'Eliminado con éxito'})
            except Exception as ex:
                return JsonResponse({"isSuccess": False, "message": ex.__str__()})

        ## GESTION COORDINADOR
        if action == 'receptar_soli':
            with transaction.atomic():
                try:
                    from posgrado.forms import GestionSolicitudBalconForm
                    from posgrado.models import DepartamentoAtencionBalcon, \
                        AdjuntoSolicitudBalcon

                    form = GestionSolicitudBalconForm(request.POST, request.FILES)
                    id_solicitud = int(encrypt(request.POST['id']))
                    eSolicitud = SolicitudBalcon.objects.get(pk=id_solicitud)
                    es_reasignada = True if eSolicitud.estado == 4 else False
                    if eSolicitud.estado == SolicitudBalcon.EstadoSolicitud.EN_GESTION and not es_reasignada:
                        raise NameError('La solicitud ya se encuentra en gestión')
                    if eSolicitud.tipo_proceso == 2 and not es_reasignada:
                        raise NameError('La solicitud ya se encuentra en gestión.')
                    if eSolicitud.estado == SolicitudBalcon.EstadoSolicitud.FINALIZADA:
                        raise NameError('La solicitud ya se encuentra finalizada')
                    if 'grupo_atencion' not in request.POST:
                        raise NameError('No se ha especificado el grupo de atención')
                    id_grupo =  request.POST.get('grupo_atencion', 0)
                    if id_grupo == 0:
                        raise NameError('No se ha especificado la solicitud o el grupo de atención')
                    form.set_queryset(id_solicitud, int(id_grupo))
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "message": "Error en el formulario"})
                    eSolicitud.grupo_atencion = form.cleaned_data['grupo_atencion']
                    eSolicitud.detalle_gestion = form.cleaned_data['detalle_gestion']
                    eSolicitud.asignado_por = persona
                    eSolicitud.fecha_derivacion = hoy
                    eSolicitud.estado = SolicitudBalcon.EstadoSolicitud.EN_GESTION
                    eSolicitud.persona_recepta = persona
                    eSolicitud.tipo_proceso = SolicitudBalcon.TipoProceso.GESTION
                    eSolicitud.save(request)

                    if 'archivo' in request.FILES:
                        file = request.FILES['archivo']
                        if file.size > 5242880:
                            raise NameError('El archivo no debe superar los 5MB')
                        else:
                            newfiles = request.FILES['archivo']
                            newfilesd = newfiles._name
                            ext = newfilesd[newfilesd.rfind("."):]
                            if not ext.lower() in ['.jpg', '.png', '.pdf', 'jpeg']:
                                raise NameError('El archivo debe ser de tipo imagen o pdf')
                        file_nombre = file._name.split('.')[-2]
                        file._name = generar_nombre(f'adjunto_{eSolicitud.id}_', file._name)
                        if not es_reasignada:
                            eAdjuntoGestion = AdjuntoSolicitudBalcon(
                                solicitud=eSolicitud,
                                archivo=file,
                                nombre=file_nombre,
                                tipo=AdjuntoSolicitudBalcon.TipoAdjunto.GESTION,
                            )
                            eAdjuntoGestion.save(request)
                    notificar_proceso_solicitud(eSolicitud.id, request)
                    return JsonResponse(
                        {'isSuccess': True, 'rt': True, 'idma': encrypt(eSolicitud.materia_asignada.materia_id),
                         'message': 'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'isSuccess': False, 'message': f'Error: {ex}'})

        ## GESTION LIDER DE GRUPO
        if action == 'asignar_responsable':
            with transaction.atomic():
                try:
                    from posgrado.forms import AsignarResponsableGestionForm
                    if 'id' not in request.POST or not request.POST['id'] or request.POST['id'] == '' or request.POST[
                        'id'] == '0':
                        raise NameError('No se ha especificado la gestión')
                    id_gestion = int(encrypt(request.POST['id']))
                    eGestion = SolicitudBalcon.objects.get(pk=id_gestion)
                    if eGestion.estado != SolicitudBalcon.EstadoSolicitud.EN_GESTION:
                        raise NameError('La solicitud no se encuentra en gestión')
                    form = AsignarResponsableGestionForm(request.POST)
                    id_responsable = int(request.POST['responsable'])
                    form.set_responsable(id_responsable)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse(
                            {'isSuccess': False, "form": form_error, "mensaje": "Error en el formulario"})
                    eGestion.responsable = form.cleaned_data['responsable']
                    eGestion.fecha_inicio_gestion = form.cleaned_data['fecha_inicio_gestion']
                    eGestion.fecha_fin_gestion = form.cleaned_data['fecha_finaliza_gestion'] if form.cleaned_data[
                        'fecha_finaliza_gestion'] else None
                    eGestion.estado = SolicitudBalcon.EstadoSolicitud.CON_RESPONSABLE
                    eGestion.save(request)
                    notificar_proceso_solicitud(eGestion.id, request)
                    messages.success(request, 'Guardado con éxito')
                    return JsonResponse({'isSuccess': True, 'message': 'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'isSuccess': False, 'message': ex.__str__()})

        if action == 'reasignar_lider':
            with transaction.atomic():
                try:
                    if not 'id' in request.POST:
                        raise NameError('No se ha especificado la gestión')
                    id_gestion = int(encrypt(request.POST['id']))
                    eGestion = SolicitudBalcon.objects.get(pk=id_gestion)
                    eGestion.grupo_atencion = None
                    eGestion.responsable = None
                    eGestion.estado = SolicitudBalcon.EstadoSolicitud.EN_REASIGNACION
                    eGestion.motivo_reasignacion = request.POST['motivo'] if request.POST['motivo'] else ''
                    eGestion.save(request)
                    notificar_proceso_solicitud(eGestion.id, request)
                    return JsonResponse({'isSuccess': True, 'message': 'Enviada con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'isSuccess': False, 'message': f'Error: {ex}'})

        ### GESTION INTEGRANTE DE GRUPO
        if action == 'responder_solicitud':
            with transaction.atomic():
                try:
                    from posgrado.forms import ResponderSolicitudGestionForm
                    from posgrado.models import AdjuntoSolicitudBalcon
                    if 'id' not in request.POST or not request.POST['id'] or request.POST['id'] == '' or request.POST[
                        'id'] == '0':
                        raise NameError('No se ha especificado la gestión')
                    eSolicitud = SolicitudBalcon.objects.get(pk=int(encrypt(request.POST['id'])))
                    form = ResponderSolicitudGestionForm(request.POST, request.FILES)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "message": "Error en el formulario"})
                    eSolicitud.estado = SolicitudBalcon.EstadoSolicitud.FINALIZADA
                    eSolicitud.fecha_finaliza_gestion = hoy
                    eSolicitud.respuesta = form.cleaned_data['respuesta'] if form.cleaned_data[
                        'respuesta'] else 'Solicitud finalizada'
                    eSolicitud.fecha_respuesta = hoy
                    eSolicitud.save(request)
                    if form.cleaned_data['archivo_respuesta']:
                        eAdjuntoRespuesta = AdjuntoSolicitudBalcon(
                            solicitud=eSolicitud,
                            archivo=form.cleaned_data['archivo_respuesta'],
                            tipo=AdjuntoSolicitudBalcon.TipoAdjunto.RESPUESTA
                        )
                        eAdjuntoRespuesta.save(request)
                    notificar_proceso_solicitud(eSolicitud.id, request)
                    messages.success(request, 'Guardado con éxito!')
                    return JsonResponse({'isSuccess': True, 'message': 'Guardado con éxitoOO'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'isSuccess': False, 'message': ex.__str__()})


        if action == 'tipo_solicitud_add':
            with transaction.atomic():
                try:
                    from posgrado.forms import TipoSolicitudBalconForm
                    from posgrado.models import TipoSolicitudBalcon
                    form = TipoSolicitudBalconForm(request.POST)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                    eTipo = TipoSolicitudBalcon(
                        nombre=form.cleaned_data['nombre'].strip().upper(),
                        descripcion=form.cleaned_data['descripcion'] if form.cleaned_data['descripcion'] else '',
                    )
                    eTipo.save(request)
                    messages.success(request, 'Guardado con éxito')
                    return JsonResponse({'isSuccess': True, 'message': 'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'isSuccess': False, 'message': f'Error: {ex}'})

        if action == 'tipo_solicitud_edit':
            with transaction.atomic():
                try:
                    from posgrado.forms import TipoSolicitudBalconForm
                    from posgrado.models import TipoSolicitudBalcon
                    if not 'id' in request.POST:
                        raise NameError('No se ha especificado el tipo de solicitud')

                    id_tipo = int(encrypt(request.POST['id']))
                    eTipo = TipoSolicitudBalcon.objects.get(pk=id_tipo)

                    form = TipoSolicitudBalconForm(request.POST)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                    eTipo.nombre=form.cleaned_data['nombre'].strip().upper()
                    eTipo.descripcion=form.cleaned_data['descripcion'] if form.cleaned_data['descripcion'] else ''
                    eTipo.save(request)
                    messages.success(request, 'Editado con éxito!!')
                    return JsonResponse({'isSuccess': True, 'message': 'Editado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'isSuccess': False, 'message': f'Error: {ex}'})

        if action == 'rect_periodo':
            try:
                from sga.models import Periodo
                if 'id' not in request.POST:
                    raise NameError('No se ha especificado el periodo')
                request.session['periodo'] = periodo = Periodo.objects.get(pk=int(encrypt(request.POST['id'])))
                return JsonResponse({'isSuccess': True})
            except Exception as ex:
                return JsonResponse({"isSuccess": False, "message": u"Error al guardar los datos."})

        if action == 'asigna_coordinador':
            with transaction.atomic():
                try:
                    from posgrado.forms import AsignaCoordinadorForm, GestionSolicitudBalconForm
                    from posgrado.models import DepartamentoAtencionBalcon, \
                        AdjuntoSolicitudBalcon

                    form = AsignaCoordinadorForm(request.POST)
                    id_solicitud = int(encrypt(request.POST['id']))
                    eSolicitud = SolicitudBalcon.objects.get(pk=id_solicitud)
                    es_reasignada = True if eSolicitud.estado == 4 else False
                    if eSolicitud.estado == SolicitudBalcon.EstadoSolicitud.EN_GESTION and not es_reasignada:
                        raise NameError('La solicitud ya se encuentra en gestión')
                    if eSolicitud.tipo_proceso == 2 and not es_reasignada:
                        raise NameError('La solicitud ya se encuentra en gestión.')
                    if eSolicitud.estado == SolicitudBalcon.EstadoSolicitud.FINALIZADA:
                        raise NameError('La solicitud ya se encuentra finalizada')

                    id_person = request.POST.get('coordinador', '')
                    if not id_person:
                        raise NameError('No se ha especificado el coordinador')

                    form.set_coordinador(id_person)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "message": "Error en el formulario"})
                    eSolicitud.asignado_por = persona
                    eSolicitud.fecha_derivacion = hoy
                    eSolicitud.estado = SolicitudBalcon.EstadoSolicitud.NUEVO
                    eSolicitud.persona_recepta = form.cleaned_data['coordinador']
                    eSolicitud.save(request)

                    notificar_proceso_solicitud(eSolicitud.id, request)
                    return JsonResponse(
                        {'isSuccess': True, 'rt': True,
                         'message': 'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'isSuccess': False, 'message': f'Error: {ex}'})

        return JsonResponse({"isSuccess": True, "message": u"Solicitud Incorrecta."})
    else:
        data['is_profesor'] = is_profesor = True if perfilprincipal.es_profesor() else False
        data['is_lidergrupo'] = is_lider = True if GrupoAtencionBalcon.objects.filter(lider=persona,
                                                                                      status=True).exists() else False
        data['is_integrante_grupo'] = is_integrante = True if IntegranteGrupoAtencionBalcon.objects.filter(
            integrante=persona, status=True) else False
        if request.user.has_perm('posgrado.puede_ver_solicitudes_gestion_balcon'):
            ver_listado = True
        data['ver_listado'] = ver_listado

        if request.user.has_perm('posgrado.puede_configurar_grupos_atencion_balcon'):
            puede_configurar = True
        data['puede_configurar'] = puede_configurar

        if 'action' in request.GET:
            action = request.GET['action']

            ### DEPARTAMENTO ATENCION
            if action == 'dep_atencion':
                try:
                    from posgrado.models import DepartamentoAtencionBalcon
                    data['title'] = f'Departamentos de Atención'
                    url_vars, filtro = '', Q(status=True)

                    if 's' in request.GET:
                        s = request.GET['s']
                        filtro.add(Q(nombre__icontains=s), Q.AND)
                        data['s'] = s

                    eDepAtenciones = DepartamentoAtencionBalcon.objects.filter(filtro).order_by('nombre')
                    paging = MiPaginador(eDepAtenciones, 15)
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
                    paging.rangos_paginado(p)
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['departamentos'] = page.object_list
                    data['url_vars'] = url_vars
                    data['tag_active'] = 3
                    return render(request, 'balcon_posgrado/dep_atencion/view.html', data)
                except Exception as ex:
                    pass

            elif action == 'dep_atencion_add':
                try:
                    from posgrado.forms import DepartamentoAtencionBalconForm
                    if not puede_configurar:
                        raise NameError('No tiene permisos para realizar esta acción')

                    data['form'] = form = DepartamentoAtencionBalconForm()
                    data['action'] = 'dep_atencion_add'
                    template = get_template('balcon_posgrado/dep_atencion/modal/dep_atencion_form.html')
                    return JsonResponse({"isSuccess": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"isSuccess": False, "message": ex.__str__()})

            elif action == 'dep_atencion_edit':
                try:
                    from posgrado.forms import DepartamentoAtencionBalconForm
                    from posgrado.models import DepartamentoAtencionBalcon
                    if not puede_configurar:
                        raise NameError('No tiene permisos para realizar esta acción')
                    if not 'id' in request.GET or not request.GET['id'] or int(request.GET['id']) == '0':
                        raise NameError('No se ha especificado el departamento de atención')
                    data['id'] = id_dep = int(request.GET['id'])
                    eDep = DepartamentoAtencionBalcon.objects.get(pk=id_dep)
                    data['form'] = form = DepartamentoAtencionBalconForm(initial=model_to_dict(eDep))
                    data['action'] = 'dep_atencion_edit'
                    template = get_template('balcon_posgrado/dep_atencion/modal/dep_atencion_form.html')
                    return JsonResponse({"isSuccess": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"isSuccess": False, "message": ex.__str__()})

            elif action == 'dep_atencion_grupo_add':
                try:
                    from posgrado.forms import GrupoAtencionBalconForm
                    if not puede_configurar:
                        raise NameError('No tiene permisos para realizar esta acción')
                    if not 'id' in request.GET:
                        raise NameError('No se ha especificado el departamento de atención')
                    data['id'] = id_dep = request.GET['id']
                    form = GrupoAtencionBalconForm()
                    # form.set_departamento(id_dep)
                    data['form'] = form
                    data['action'] = 'dep_atencion_grupo_add'
                    template = get_template('balcon_posgrado/dep_atencion/modal/grupoform.html')
                    return JsonResponse({"isSuccess": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"isSuccess": False, "message": ex.__str__()})

            elif action == 'dep_atencion_grupo_edit':
                try:
                    from posgrado.forms import GrupoAtencionBalconForm
                    if not puede_configurar:
                        raise NameError('No tiene permisos para realizar esta acción')
                    if not 'id' in request.GET:
                        raise NameError('No se ha especificado el departamento de atención')
                    data['id'] = id_grupo = int(encrypt(request.GET['id']))
                    eGrupo = GrupoAtencionBalcon.objects.get(pk=id_grupo)
                    form = GrupoAtencionBalconForm(initial=model_to_dict(eGrupo))
                    form.edit(eGrupo.lider_id)
                    form.ocultar_edit()
                    data['form'] = form
                    data['action'] = 'dep_atencion_grupo_edit'
                    template = get_template('balcon_posgrado/dep_atencion/modal/grupoform.html')
                    return JsonResponse({"isSuccess": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"isSuccess": False, "message": ex.__str__()})

            elif action == 'gestionar_integrantes':
                try:
                    from posgrado.forms import IntegranteGrupoAtencionBalconForm
                    if not 'id' in request.GET:
                        raise NameError('No se ha especificado el grupo de atención')
                    data['id'] = id_grupo = int(encrypt(request.GET['id']))
                    data['eGrupo'] = eGrupo = GrupoAtencionBalcon.objects.get(pk=id_grupo)
                    data['eIntegrantesGrupo'] = eGrupo.get_integrantes()
                    form = IntegranteGrupoAtencionBalconForm()
                    data['form'] = form
                    data['action'] = 'gestionar_integrantes'
                    template = get_template('balcon_posgrado/dep_atencion/modal/integrantes_form.html')
                    return JsonResponse({"isSuccess": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"isSuccess": False, "message": ex.__str__()})

            ### BUSCA PERSONAS
            elif action == 'buscarpersona':
                try:
                    resp = buscador_personas(request)
                    return HttpResponse(json.dumps({'isSuccess': True, 'results': resp}))
                except Exception as ex:
                    return HttpResponse(
                        json.dumps({'isSuccess': False, 'results': {'id': '0', 'name': f'Error - {ex.__str__()}'}}))

            elif action == 'buscarintegrantes':
                try:
                    id_exs = []
                    # if not 'id_lider' in request.GET or request.GET['id_lider'] == '':
                    #     data = {"result": "ok", "results": [{"id": "0", "name": "Eliga un perfil valido"}]}
                    #     return JsonResponse({'status': False, 'results': [
                    #         {"id": "0", "name": "Primero Seleccione un lider de departamento"}]})
                    if 'id_lider' in request.GET and request.GET['id_lider'] != '':
                        id_exs.append(int(request.GET['id_lider']))
                    else:
                        grupo = GrupoAtencionBalcon.objects.get(pk=int(request.GET['id_grupo']))
                        id_exs.append(grupo.lider_id)
                        id_exs.extend(grupo.get_integrantes().values_list('id', flat=True))
                    resp = buscador_personas(request, id_exs, is_integrante=True)
                    return HttpResponse(json.dumps({'status': True, 'results': resp}))
                except Exception as ex:
                    pass

            ### VISTA COORDINADOR

            elif action == 'vista_coordinador':
                try:
                    from sga.models import ProfesorMateria
                    data['title'] = f'Solicitudes de Atención'

                    if not perfilprincipal.es_profesor():
                        raise NameError('Solo los profesores tutores pueden revisar las solicitudes de atención')
                    data['profesor'] = eProfesor = perfilprincipal.profesor
                    profesorVirutal = ProfesorMateria.objects.filter(profesor_id=eProfesor, tipoprofesor_id=8)
                    if not profesorVirutal.exists():
                        raise NameError('Solo los coordinadores de maestria pueden revisar las solicitudes de atención')
                    eMateriasProfesor = ProfesorMateria.objects.filter(profesor_id=eProfesor,
                                                                       materia__nivel__periodo=periodo)
                    id_materia = None
                    def get_soli_nuevas_materia(materias):
                        for materia in materias:
                            if materia.get_solicitud_nuevas() > 0:
                                data['idma_ini'] = materia.obj.materia.id
                                return True
                        return False
                    data['eMateriasProfesor'] = eMateriasProfesorHelp = [HelperProfesorMateria(eMateriaProfesor) for eMateriaProfesor in
                                                 eMateriasProfesor]
                    data['tag_active'] = 2
                    get_soli_nuevas_materia(eMateriasProfesorHelp)
                    soli_asignadas = SolicitudBalcon.objects.filter(status=True, estado=SolicitudBalcon.EstadoSolicitud.NUEVO,
                                                                    persona_recepta=eProfesor.persona)
                    data['soli_desvinculadas'] = soli_asignadas.count() if soli_asignadas.exists() else 0

                    return render(request, 'balcon_posgrado/vista_coordinador/view.html', data)

                except Exception as ex:
                    messages.error(request, ex.__str__())
                    pass

            elif action == 'listar_solicitudes_coordinador':
                try:
                    if not 'id_materia' in request.GET:
                        raise NameError('No se ha especificado la materia')
                    id_materia = int(encrypt(request.GET['id_materia']))
                    data['id_materia'] = encrypt(id_materia)
                    filtro = Q(status=True, materia_asignada__materia__in=[id_materia])
                    url_vars = ''
                    et_filtro = filtro_estado_tipo(request, data, url_vars)
                    filtro.add(et_filtro['filtro'], Q.AND)
                    url_vars += et_filtro['url_vars']
                    v_filtro = filtro_solicitud(request, data, url_vars)
                    filtro.add(v_filtro['filtro'], Q.AND)
                    url_vars += v_filtro['url_vars']
                    url_vars += '&action=listar_solicitudes_coordinador'
                    url_vars += f'&id_materia={request.GET["id_materia"]}'
                    eSolicitudes = SolicitudBalcon.objects.filter(filtro).order_by('-fecha_creacion', 'estado')

                    paging = MiPaginador(eSolicitudes, 15)
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
                    paging.rangos_paginado(p)
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['solicitudes'] = page.object_list
                    data['url_vars'] = url_vars
                    template = get_template('balcon_posgrado/vista_coordinador/tabla_coordinador.html')
                    return JsonResponse({"isSuccess": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"isSuccess": False, "message": ex.__str__()})

            elif action == 'listar_solicitudes_coordinador_desvinculadas':
                try:


                    filtro = Q(status=True, estado=SolicitudBalcon.EstadoSolicitud.NUEVO,
                                                                    persona_recepta=persona)
                    url_vars = ''
                    et_filtro = filtro_estado_tipo(request, data, url_vars)
                    filtro.add(et_filtro['filtro'], Q.AND)
                    url_vars += et_filtro['url_vars']
                    v_filtro = filtro_solicitud(request, data, url_vars)
                    filtro.add(v_filtro['filtro'], Q.AND)
                    url_vars += v_filtro['url_vars']
                    url_vars += '&action=listar_solicitudes_coordinador_desvinculadas'
                    eSolicitudes = SolicitudBalcon.objects.filter(filtro).order_by('-fecha_creacion', 'estado')

                    paging = MiPaginador(eSolicitudes, 15)
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
                    paging.rangos_paginado(p)
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['solicitudes'] = page.object_list
                    data['url_vars'] = url_vars
                    data['b_desv'] = True
                    template = get_template('balcon_posgrado/vista_coordinador/tabla_coordinador.html')
                    return JsonResponse({"isSuccess": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"isSuccess": False, "message": ex.__str__()})

            elif action == 'listar_solicitudes':
                try:
                    from sga.models import MateriaAsignada
                    from api.serializers.alumno.balcon_posgrado_ser import SolicitudBalconSerializer

                    if not 'idma' in request.GET or request.GET['idma'] == '':
                        raise NameError('No se ha especificado la materia')

                    eMateriaAsignadas = MateriaAsignada.objects.filter(materia=int(encrypt(request.GET['idma'])),
                                                                       materia__nivel__periodo=periodo)
                    filtro = Q(status=True, materia_asignada__in=eMateriaAsignadas)
                    estado = 0
                    if 'e' in request.GET:
                        estado = int(request.GET['e'])
                        filtro.add(Q(estado=estado), Q.AND)

                    eSolicitudes = SolicitudBalcon.objects.filter(filtro).order_by('-fecha_creacion', 'estado')
                    aData = {
                        'nombre_materia': eMateriaAsignadas.first().materia.nombre_mostrar_sin_profesor(),
                        'eSolicitudes_serializer': SolicitudBalconSerializer(eSolicitudes, many=True).data,
                        'e': estado
                    }
                    return JsonResponse({"isSuccess": True, 'data': aData})
                except Exception as ex:
                    return JsonResponse({"isSuccess": False, "message": ex.__str__()})

            elif action == 'receptar_soli':
                try:
                    from posgrado.models import DepartamentoAtencionBalcon
                    from posgrado.forms import GestionSolicitudBalconForm

                    if 'id' not in request.GET:
                        raise NameError('No se ha especificado la solicitud')
                    data['id'] = id_soli = int(encrypt(request.GET['id']))
                    eSolicitud = SolicitudBalcon.objects.get(pk=id_soli)
                    eDepAtencions = DepartamentoAtencionBalcon.objects.filter(status=True)
                    eGrupoAtencions = GrupoAtencionBalcon.objects.filter(status=True)
                    data['eSolicitud'] = eSolicitud
                    data['eDepAtencions'] = eDepAtencions
                    data['eGrupoAtencions'] = eGrupoAtencions
                    if eSolicitud.estado == 4:
                        form = GestionSolicitudBalconForm(initial=model_to_dict(eSolicitud))
                        if eSolicitud.get_adjunto_gestion():
                            form.fields['archivo'].initial = eSolicitud.get_adjunto_gestion().first().archivo
                        form.fields['detalle_gestion'].initial = eSolicitud.detalle_gestion
                    else:
                        form = GestionSolicitudBalconForm()
                    data['form'] = form
                    data['action'] = 'receptar_soli'
                    template = get_template('balcon_posgrado/vista_coordinador/modal/receptar_solicitud.html')
                    return JsonResponse({"isSuccess": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"isSuccess": False, "message": ex.__str__()})

            elif action == 'get_lider_grupo':
                try:
                    if not 'id' in request.GET:
                        raise NameError('No se ha especificado el grupo')
                    aData = {"isSuccess": True, 'lider': None, 'lider_id': None}
                    eLiderGrupo = GrupoAtencionBalcon.objects.filter(pk=int(request.GET['id']))
                    if eLiderGrupo.exists():
                        aData['lider'] = eLiderGrupo.first().lider.nombre_completo_inverso()
                        aData['lider_id'] = eLiderGrupo.first().lider.id
                    return JsonResponse(aData)
                except Exception as ex:
                    messages.error(request, ex.__str__())
                    return JsonResponse({"isSuccess": False, "message": ex.__str__()})

            elif action == 'detalle_gestion_soli':
                try:
                    if 'id' not in request.GET:
                        raise NameError('No se ha especificado la solicitud')
                    data['id'] = id_soli = int(encrypt(request.GET['id']))
                    eSolicitud = SolicitudBalcon.objects.get(pk=id_soli)
                    data['eSolicitud'] = eSolicitud

                    template = get_template('balcon_posgrado/vista_coordinador/modal/detalle_gestion.html')
                    return JsonResponse({"isSuccess": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"isSuccess": False, "message": ex.__str__()})

            ### VISTA LIDER DE GRUPO DE ATENCIÓN
            elif action == 'vista_lidergrupo':
                try:
                    from posgrado.models import TipoSolicitudBalcon
                    data['title'] = f'Solicitudes de Atención'
                    data['subtitle'] = 'Listado de solicitudes de atención'

                    if not is_lider:
                        raise NameError(f'Solo los lideres de grupos de atención pueden acceder a esta vista')

                    url_vars, filtro = '', Q(status=True, grupo_atencion__lider=persona)

                    et_filtro = filtro_estado_tipo(request, data, url_vars)
                    filtro.add(et_filtro['filtro'], Q.AND)
                    url_vars += et_filtro['url_vars']
                    v_filtro = filtro_solicitud(request, data, url_vars)
                    filtro.add(v_filtro['filtro'], Q.AND)
                    url_vars += v_filtro['url_vars']

                    data['tipos_solicitud'] = TipoSolicitudBalcon.objects.filter(status=True)
                    data['estados'] = SolicitudBalcon.EstadoSolicitud.choices
                    gestiones = SolicitudBalcon.objects.filter(filtro).order_by('estado')

                    paging = MiPaginador(gestiones, 15)
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
                    paging.rangos_paginado(p)
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['solicitudes'] = page.object_list
                    data['url_vars'] = url_vars

                    return render(request, 'balcon_posgrado/vista_lidergrupo/view.html', data)
                except Exception as ex:
                    messages.error(request, ex.__str__())
                    pass

            elif action == 'asignar_responsable':
                try:
                    from posgrado.forms import AsignarResponsableGestionForm
                    if 'id' not in request.GET:
                        raise NameError('No se ha especificado la gestión para asignar')
                    data['id'] = id_gestion = int(encrypt(request.GET['id']))
                    eGestion = SolicitudBalcon.objects.get(pk=id_gestion)
                    data['eGestion'] = eGestion
                    form = AsignarResponsableGestionForm()
                    form.init_queryset(eGestion.grupo_atencion_id)
                    data['form'] = form
                    data['action'] = 'asignar_responsable'
                    template = get_template('balcon_posgrado/vista_lidergrupo/modal/asignar_responsable_form.html')
                    return JsonResponse({"isSuccess": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"isSuccess": False, "message": ex.__str__()})

            ### VISTA RESPONSABLE
            elif action == 'get_vista_responsable':
                try:
                    from posgrado.models import TipoSolicitudBalcon
                    if not is_integrante:
                        raise NameError(f'Solo los integrantes de grupos de atención pueden acceder a esta vista')
                    data['title'] = f'Solicitudes de Atención'
                    data['subtitle'] = 'Listado de solicitudes de atención'

                    if not 'idg' in request.GET:
                        raise NameError('No se ha especificado el grupo de atención')
                    data['id_grupo'] = id_grupo = int(encrypt(request.GET['idg']))

                    url_vars, filtro = '', Q(status=True, responsable__integrante=persona)

                    idsGrupos = IntegranteGrupoAtencionBalcon.objects.values_list('grupo_atencion_id',
                                                                                  flat=True).filter(integrante=persona,
                                                                                                    status=True)
                    et_filtro = filtro_estado_tipo(request, data, url_vars)
                    filtro.add(et_filtro['filtro'], Q.AND)
                    url_vars += et_filtro['url_vars']
                    v_filtro = filtro_solicitud(request, data, url_vars)
                    filtro.add(v_filtro['filtro'], Q.AND)
                    url_vars += v_filtro['url_vars']

                    eGruposAtencion = GrupoAtencionBalcon.objects.filter(pk__in=idsGrupos, status=True)
                    data['gruposAtencion'] = eGruposAtencion
                    data['tipos_solicitud'] = TipoSolicitudBalcon.objects.filter(status=True)
                    data['estados'] = SolicitudBalcon.EstadoSolicitud.choices
                    gestiones = SolicitudBalcon.objects.filter(filtro).order_by('-fecha_creacion')

                    paging = MiPaginador(gestiones, 15)
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
                    paging.rangos_paginado(p)
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['solicitudes'] = page.object_list
                    data['url_vars'] = url_vars
                    data['tag_active'] = 2
                    return render(request, 'balcon_posgrado/vista_responsable/view.html', data)
                except Exception as ex:
                    messages.error(request, ex.__str__())
                    pass

            elif action == 'vista_responsable':
                try:
                    if not is_integrante:
                        raise NameError(f'Solo los integrantes de grupos de atención pueden acceder a esta vista')
                    data['title'] = f'Solicitudes de Atención'
                    data['subtitle'] = 'Listado de solicitudes de atención'
                    idsGrupos = IntegranteGrupoAtencionBalcon.objects.values_list('grupo_atencion_id',
                                                                                  flat=True).filter(integrante=persona,
                                                                                                    status=True)
                    eGruposAtencion = GrupoAtencionBalcon.objects.filter(pk__in=idsGrupos, status=True)
                    data['gruposAtencion'] = eGruposAtencion
                    data['solicitudes'] = SolicitudBalcon.objects.filter(responsable__integrante=persona,
                                                                              status=True).order_by('-fecha_creacion')
                    data['tag_active'] = 2
                    return render(request, 'balcon_posgrado/vista_responsable/view.html', data)
                except Exception as ex:
                    messages.error(request, ex.__str__())
                    pass

            elif action == 'listar_gestion_responsable':
                try:
                    if not 'id' in request.GET:
                        raise NameError('No se ha especificado el grupo')

                    def get_gestiones_responsable(persona, id_grupo_atencion, estado=None, page=1):

                        aData = {"isSuccess": True, 'data': None, 'pages': None}
                        filtro = Q(status=True, grupo_atencion_id=id_grupo_atencion, responsable__integrante=persona)
                        if estado:
                            filtro.add(Q(estado=estado), Q.AND)
                        eGestiones = ''
                        paginator = MiPaginador(eGestiones, 10)
                        page_obj = paginator.get_page(page)
                        eGestiones_ser = []
                        for eGestion in page_obj:
                            eGestiones_ser.append(eGestion.to_json())
                        # aData['pages'] = {'has_next': page_obj.has_next(),
                        #                   'has_previous': page_obj.has_previous(),
                        #                   'number': page_obj.number,
                        #                   'num_pages': paginator.num_pages
                        #                   }
                        aData['data'] = eGestiones_ser
                        return aData

                    grupo_atencion_id = int(encrypt(request.GET['id']))
                    estado = request.GET.get('estado', None)
                    page = request.GET.get('page', 1)
                    data = get_gestiones_responsable(persona, grupo_atencion_id, estado, page)
                    return JsonResponse(data)

                except Exception as ex:
                    return JsonResponse({"isSuccess": False, "message": ex.__str__()})

            elif action == 'responder_solicitud':
                try:
                    from posgrado.forms import ResponderSolicitudGestionForm
                    if 'id' not in request.GET:
                        raise NameError('No se ha especificado la gestión para responder')
                    data['id'] = id_gestion = int(encrypt(request.GET['id']))
                    eGestion = SolicitudBalcon.objects.get(pk=id_gestion)
                    data['eGestion'] = eGestion
                    form = ResponderSolicitudGestionForm()
                    data['form'] = form
                    data['action'] = 'responder_solicitud'
                    template = get_template('balcon_posgrado/vista_responsable/modal/responder_form.html')
                    return JsonResponse({"isSuccess": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"isSuccess": False, "message": ex.__str__()})

            ### VISTA TIPOS SOLICITUD
            elif action == 'list_tipo_solicitud':
                try:
                    from posgrado.models import TipoSolicitudBalcon
                    data['title'] = f'Tipos de Solicitud'
                    eTiposSolicitud = TipoSolicitudBalcon.objects.filter(status=True)
                    data['eTiposSolicitud'] = eTiposSolicitud
                    data['tag_active'] = 1
                    return render(request, 'balcon_posgrado/dep_atencion/config_tipos/view.html', data)
                except Exception as ex:
                    messages.error(request, ex.__str__())
                    pass

            elif action == 'tipo_solicitud_add':
                try:
                    from posgrado.forms import TipoSolicitudBalconForm
                    data['form'] = form = TipoSolicitudBalconForm()
                    data['action'] = 'tipo_solicitud_add'
                    template = get_template('balcon_posgrado/dep_atencion/config_tipos/modal/tipo_solicitud_form.html')
                    return JsonResponse({"isSuccess": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"isSuccess": False, "message": ex.__str__()})

            elif action == 'tipo_solicitud_edit':
                try:
                    from posgrado.forms import TipoSolicitudBalconForm
                    from posgrado.models import TipoSolicitudBalcon
                    if not 'id' in request.GET or not request.GET['id']:
                        raise NameError('No se ha especificado el departamento de atención')
                    data['id'] = id = int(encrypt(request.GET['id']))
                    eTipo = TipoSolicitudBalcon.objects.get(pk=id)
                    data['form'] = form = TipoSolicitudBalconForm(initial=model_to_dict(eTipo))
                    data['action'] = 'tipo_solicitud_edit'
                    template = get_template('balcon_posgrado/dep_atencion/config_tipos/modal/tipo_solicitud_form.html')
                    return JsonResponse({"isSuccess": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"isSuccess": False, "message": ex.__str__()})

            ### VISTA LISTADO SOLICITUDES
            elif action == 'vista_listado':
                try:
                    from posgrado.models import TipoSolicitudBalcon
                    data['title'] = f'Solicitudes de Atención'
                    data['subtitle'] = 'Listado de solicitudes de atención'

                    if not ver_listado:
                        raise NameError(f'No tiene permiso para acceder a esta vista')

                    url_vars, filtro = '', Q(status=True)

                    eGruposAtencion = GrupoAtencionBalcon.objects.filter(status=True)
                    data['gruposAtencion'] = eGruposAtencion
                    # data['idg'] = eGruposAtencion.first().id if eGruposAtencion and 'idg' in request.GET else 0
                    et_filtro = filtro_estado_tipo(request, data, url_vars)
                    filtro.add(et_filtro['filtro'], Q.AND)
                    url_vars += et_filtro['url_vars']
                    v_filtro = filtro_solicitud(request, data, url_vars)
                    filtro.add(v_filtro['filtro'], Q.AND)
                    url_vars += v_filtro['url_vars']

                    data['tipos_solicitud'] = TipoSolicitudBalcon.objects.filter(status=True)
                    data['estados'] = SolicitudBalcon.EstadoSolicitud.choices
                    solicitudes = SolicitudBalcon.objects.filter(filtro).order_by('-fecha_creacion')

                    paging = MiPaginador(solicitudes, 15)
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
                    paging.rangos_paginado(p)
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['solicitudes'] = page.object_list
                    url_vars += '&action=vista_listado'
                    data['url_vars'] = url_vars
                    data['tag_active'] = 4
                    return render(request, 'balcon_posgrado/vista_listado/view.html', data)
                except Exception as ex:
                    messages.error(request, ex.__str__())
                    pass

            elif action == 'buscar_list_integrantes':
                try:
                    resp = buscador_integrantes(request)
                    return HttpResponse(json.dumps({'status': True, 'results': resp}))
                except Exception as ex:
                    pass

            elif action == 'asigna_coordinador':
                try:
                    from posgrado.forms import AsignaCoordinadorForm
                    if 'id' not in request.GET:
                        raise NameError('No se ha especificado la solicitud para asignar')
                    data['id'] = id_soli = int(encrypt(request.GET['id']))
                    eSoli = SolicitudBalcon.objects.get(pk=id_soli)
                    data['title'] = f'Asignar Coordinador'
                    data['subtitle'] = 'Asignar un coordinador'
                    data['form'] = form = AsignaCoordinadorForm()
                    data['action'] = 'asigna_coordinador'
                    template = get_template('balcon_posgrado/vista_listado/modal/asignar_coordinador_form.html')
                    return JsonResponse({"isSuccess": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"isSuccess": False, "message": ex.__str__()})

            elif action == 'buscarcoordinador':
                try:
                    resp = buscador_coordinador(request)
                    return HttpResponse(json.dumps({'isSuccess': True, 'results': resp}))
                except Exception as ex:
                    pass


            elif action == 'cambio_coordinador':
                try:
                    from posgrado.forms import AsignarResponsableGestionForm
                    if 'id' not in request.GET:
                        raise NameError('No se ha especificado la gestión para asignar')
                    data['id'] = id_gestion = int(encrypt(request.GET['id']))
                    eGestion = SolicitudBalcon.objects.get(pk=id_gestion)
                    data['eGestion'] = eGestion
                    form = AsignarResponsableGestionForm()
                    form.init_queryset(eGestion.grupo_atencion_id)
                    data['form'] = form
                    data['action'] = 'asignar_responsable'
                    template = get_template('balcon_posgrado/vista_lidergrupo/modal/asignar_responsable_form.html')
                    return JsonResponse({"isSuccess": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"isSuccess": False, "message": ex.__str__()})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['tag_active'] = 0
                data['persona'] = persona
                msj = {
                    'class': 'info',
                    'class_aux': 'info',
                    'bienvenida': f"Bienvenid{'a' if persona.es_mujer() else 'o'}, {persona}",
                    'texto': '',
                    'cant': ''
                }
                cont_solicitudes = 0
                cont_nuevas = 0
                url_act = f'{request.path}?action='

                if is_integrante:
                    url_act += 'vista_responsable'
                    msj['texto'] = f'Nuevas solicitudes para atender: '
                    msj['cant'] = cont_solicitudes = SolicitudBalcon.objects.filter(responsable__integrante=persona,
                                                                                    estado=SolicitudBalcon.EstadoSolicitud.CON_RESPONSABLE,
                                                                                    status=True).count()
                if is_lider:
                    url_act += 'vista_lidergrupo'
                    msj['texto'] = f'Nuevas Solicitudes asignadas a su grupo de atención: '
                    msj['cant'] = cont_solicitudes = SolicitudBalcon.objects.filter(grupo_atencion__lider=persona,
                                                                                    estado=SolicitudBalcon.EstadoSolicitud.EN_GESTION,
                                                                                    status=True).count()

                if is_profesor:
                    from sga.models import ProfesorMateria
                    from django.db.models import Count
                    eProfesor = perfilprincipal.profesor
                    all_solicitudes = HelperProfesorMateria.get_all_solicitudes_nuevas_count(eProfesor)
                    solicitudes_nuevas = all_solicitudes.filter(estado=SolicitudBalcon.EstadoSolicitud.NUEVO)
                    msj['periodo_soli'] = solicitudes_nuevas.values('materia_asignada__matricula__nivel__periodo_id',
                                                                    'materia_asignada__matricula__nivel__periodo__nombre').annotate(
                                                                    cant=Count('id')).distinct()
                    msj['cant'] = solicitudes_nuevas.count()
                    msj['texto'] = f'Solicitudes nuevas para asignar a grupo de atención: '
                    cont_reasigadas = all_solicitudes.filter(
                        estado=SolicitudBalcon.EstadoSolicitud.EN_REASIGNACION).count()
                    if cont_reasigadas > 0:
                        msj['texto_re'] = f'Solicitudes para reasignar a grupo de atención: '
                        msj['cant_re'] = cont_reasigadas
                        msj['class_aux'] = 'warning'
                    url_act += 'vista_coordinador'

                data['msj'] = msj
                data['url_rt'] = url_act

                return render(request, 'balcon_posgrado/view.html', data)
            except Exception as ex:
                pass

def buscador_personas(request, excludes=[], is_integrante=False):
    try:
        from sga.models import Administrativo, Persona
        q = request.GET['q'].upper().strip()
        s = q.split(" ")
        filtro = Q(status=True)
        if not is_integrante:
            if len(s) == 1:
                filtro.add((
                        Q(persona__nombres__icontains=q) | Q(persona__apellido1__icontains=q) |
                        Q(persona__cedula__icontains=q) | Q(persona__apellido2__icontains=q) |
                        Q(persona__cedula__icontains=q)), Q.AND)
            elif len(s) == 2:
                filtro.add(
                    (Q(persona__apellido1__icontains=s[0]) & Q(persona__apellido2__icontains=s[1])) |
                    (Q(persona__nombres__icontains=s[0]) & Q(persona__nombres__icontains=s[1])) |
                    (Q(persona__nombres__icontains=s[0]) & Q(persona__apellido1__icontains=s[1])),
                    Q.AND)

            else:
                filtro.add((Q(persona__nombres__icontains=s[0]) & Q(persona__apellido1__icontains=s[1]) & Q(
                    persona__apellido2__icontains=s[2])) |
                           (Q(persona__apellido1__icontains=s[0]) & Q(persona__apellido2__icontains=s[1]) & Q(
                               persona__nombres__icontains=s[2])),
                           Q.AND)
            personas = Administrativo.objects.filter(filtro).distinct()[:10]
            data = [{
                'id': per.persona.id,
                'name': (
                    f"<img src='{per.persona.get_foto()}' width='25px' height='25px' class='w-25px rounded-circle me-2' alt='...'>"
                    f" {per.persona.nombre_completo()} - "
                    f"{per.persona.cargo_persona_2().denominacionpuesto.descripcion if per.persona.cargo_persona_2() else ''}"
                )
            } for per in personas]
        else:
            if len(s) == 1:
                filtro.add((
                        Q(nombres__icontains=q) | Q(apellido1__icontains=q) |
                        Q(cedula__icontains=q) | Q(apellido2__icontains=q) |
                        Q(cedula__icontains=q)), Q.AND)
            elif len(s) == 2:
                filtro.add((Q(apellido1__icontains=s[0]) & Q(apellido2__icontains=s[1])) |
                           (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) |
                           (Q(nombres__icontains=s[0]) & Q(apellido1__icontains=s[1])), Q.AND)
            else:
                filtro.add((Q(nombres__icontains=s[0]) & Q(apellido1__icontains=s[1]) & Q(apellido2__icontains=s[2])) |
                           (Q(apellido1__icontains=s[0]) & Q(apellido2__icontains=s[1]) & Q(nombres__icontains=s[2])),
                           Q.AND)
            personas = Persona.objects.filter(filtro).exclude(id__in=excludes).distinct()[:10]
            data = [{'id': per.id,
                     'name': f"<img src='{per.get_foto()}' width='25px' height='25px' class='w-25px rounded-circle me-2' alt='...'> {per.nombre_completo()} - {per.cargo_persona_2().denominacionpuesto.descripcion if per.cargo_persona_2() else ''}"}
                    for per in personas]
        return data
    except Exception as ex:
        pass

def buscador_integrantes(request, excludes=[]):
    try:
        q = request.GET['q'].upper().strip()
        s = q.split(" ")
        filtro = Q(status=True)
        if 'idg' in request.GET and request.GET['idg'] != '':
            filtro.add(Q(grupo_atencion_id=int(request.GET['idg'])), Q.AND)
        if len(s) == 1:
            filtro.add((
                    Q(integrante__nombres__icontains=q) | Q(apellido1__icontains=q) |
                    Q(integrante__cedula__icontains=q) | Q(apellido2__icontains=q) |
                    Q(integrante__cedula__icontains=q)), Q.AND)
        elif len(s) == 2:
            filtro.add((Q(integrante__apellido1__icontains=s[0]) & Q(integrante__apellido2__icontains=s[1])) |
                       (Q(integrante__nombres__icontains=s[0]) & Q(integrante__nombres__icontains=s[1])) |
                       (Q(integrante__nombres__icontains=s[0]) & Q(integrante__apellido1__icontains=s[1])), Q.AND)
        else:
            filtro.add((Q(integrante__nombres__icontains=s[0]) & Q(integrante__apellido1__icontains=s[1]) & Q(integrante__apellido2__icontains=s[2])) |
                       (Q(integrante__apellido1__icontains=s[0]) & Q(integrante__apellido2__icontains=s[1]) & Q(integrante__nombres__icontains=s[2])),
                       Q.AND)
        integrantes = IntegranteGrupoAtencionBalcon.objects.filter(filtro).exclude(id__in=excludes).distinct()[:10]
        data = [{'id': per.id,
                 'name': f"<img src='{per.integrante.get_foto()}' width='25px' height='25px' class='w-25px rounded-circle me-2' alt='...'> {per.integrante.nombre_completo()} - <span class='badge {'badge-success' if per.activo else 'badge-warning'}'> {'Activo' if per.activo else 'Inactivo'}</span>",
                 'text': f"{per.integrante.nombre_completo()}"}
                for per in integrantes]
        return data
    except Exception as ex:
        pass

def buscador_coordinador(request, excludes=[]):
    try:
        from sga.models import Persona, ProfesorMateria
        q = request.GET['q'].upper().strip()
        s = q.split(" ")
        filtro = Q(status=True, tipoprofesor_id=8)

        if len(s) == 1:
            filtro.add((
                    Q(profesor__persona__nombres__icontains=q) | Q(profesor__persona__apellido1__icontains=q) |
                    Q(profesor__persona__cedula__icontains=q) | Q(profesor__persona__apellido2__icontains=q) |
                    Q(profesor__persona__cedula__icontains=q)), Q.AND)
        elif len(s) == 2:
            filtro.add(
                (Q(profesor__persona__apellido1__icontains=s[0]) & Q(profesor__persona__apellido2__icontains=s[1])) |
                (Q(profesor__persona__nombres__icontains=s[0]) & Q(profesor__persona__nombres__icontains=s[1])) |
                (Q(profesor__persona__nombres__icontains=s[0]) & Q(profesor__persona__apellido1__icontains=s[1])),
                Q.AND)

        else:
            filtro.add((Q(profesor__persona__nombres__icontains=s[0]) & Q(profesor__persona__apellido1__icontains=s[1]) & Q(
                        profesor__persona__apellido2__icontains=s[2])) |
                       (Q(profesor__persona__apellido1__icontains=s[0]) & Q(profesor__persona__apellido2__icontains=s[1]) & Q(
                           profesor__persona__nombres__icontains=s[2])),
                       Q.AND)
        personas = Persona.objects.filter(id__in=ProfesorMateria.objects.filter(filtro).distinct().values_list('profesor__persona_id',flat=True))[:10]
        data = [{
            'id': per.id,
            'name': (
                f"<img src='{per.get_foto()}' width='25px' height='25px' class='w-25px rounded-circle me-2' alt='...'>"
                f" {per.nombre_completo()}"
                f" - {per.cargo_persona_2().denominacionpuesto.descripcion if per.cargo_persona_2() else ''}"
            )
        } for per in personas]

        return data
    except Exception as ex:
        pass

def filtro_estado_tipo(request, data, url_vars):
    estado = 0
    filtro = Q()
    if 'e' in request.GET and request.GET['e'] != '0':
        estado = int(request.GET['e'])
        filtro.add(Q(estado=estado), Q.AND)
        url_vars += f'&e={estado}'
        data['e'] = estado
    else:
        filtro.add(Q(estado__in=[1, 2, 4]), Q.AND)
        data['e'] = 1

    if 't' in request.GET:
        t = int(request.GET['t'])
        filtro.add(Q(tipo_solicitud=t), Q.AND)
        data['t'] = t
        url_vars += f'&t={t}'

    return {'filtro': filtro, 'data': data, 'url_vars': url_vars}

def filtro_solicitud(request, data, url_vars):
    filtro = Q()
    if 's' in request.GET:
        s = request.GET['s']
        filtro.add(
            Q(materia_asignada__matricula__inscripcion__persona__nombres__icontains=s) |
            Q(materia_asignada__matricula__inscripcion__persona__apellido1__icontains=s) |
            Q(materia_asignada__matricula__inscripcion__persona__apellido2__icontains=s) |
            Q(materia_asignada__matricula__inscripcion__persona__cedula__icontains=s) |
            Q(materia_asignada__matricula__inscripcion__persona__pasaporte__icontains=s),
            Q.AND
        )
        data['s'] = s
        url_vars += f'&s={s}'
    if 'idg' in request.GET and request.GET['idg'] != '0':
        g = int(encrypt(request.GET['idg'])) if len(request.GET['idg']) > 10 else int(request.GET['idg'])
        filtro.add(Q(grupo_atencion_id=g), Q.AND)
        data['idg'] = g
        url_vars += f'&idg={g}'

    if 'r' in request.GET and request.GET['r'] != '0':
        r = request.GET['r']
        filtro.add(Q(responsable_id=r), Q.AND)
        data['r'] = r
        if 'rs' in request.GET:
            data['rs'] = request.GET['rs']
        url_vars += f'&r={r}'

    return {'filtro': filtro, 'data': data, 'url_vars': url_vars}

def verificar_lider(id_persona, id_grupo=None):
    filtro = Q(lider=id_persona, status=True)
    if id_grupo:
        return GrupoAtencionBalcon.objects.filter(filtro).exclude(pk=id_grupo).exists()
    return GrupoAtencionBalcon.objects.filter(filtro).exists()


def notificar_proceso_solicitud(solicitud, request):
    try:
        from sga.models import Notificacion, ProfesorMateria, PerfilUsuario

        app_label = 'SGA'
        url = f"https://sga.unemi.edu.ec/adm_balcon_pos?action="
        destinatario = None
        perfil = None
        eSolicitud = SolicitudBalcon.objects.get(pk=solicitud)
        estado_s = eSolicitud.estado
        v_estado = ''
        if estado_s == 1 or estado_s == 4:
            destinatario = ProfesorMateria.objects.filter(status=True,
                                                          materia__id=eSolicitud.materia_asignada.materia_id,
                                                          tipoprofesor_id=8).first().profesor.persona if eSolicitud.materia_asignada else None
            url += 'vista_coordinador'
            v_estado= 'NUEVA SOLICITUD RECIBIDA' if estado_s == 1 else 'SOLICITUD PARA REASIGNAR'
        elif estado_s == 2:
            destinatario = eSolicitud.grupo_atencion.lider
            url += 'vista_lidergrupo'
            v_estado = 'SOLICITUD ASIGNADA A GRUPO DE ATENCIÓN'
        elif estado_s == 3:
            inscripcion = eSolicitud.materia_asignada.matricula.inscripcion
            destinatario = inscripcion.persona
            perfil = PerfilUsuario.objects.filter(status=True, persona=destinatario, inscripcion=inscripcion,
                                                  visible=True).first()

            url = f"https://sgaestudiante.unemi.edu.ec/alu_balcon_posgrado"
            v_estado = 'SOLICITUD FINALIZADA'
            app_label = 'SIE'
        elif estado_s == 5:
            destinatario = eSolicitud.responsable.integrante
            url += 'vista_responsable'
            v_estado = 'SOLICITUD ASIGNADA PARA SU ATENCIÓN'

        notificacion = Notificacion(
            titulo='Solicitud de Balcon Posgrado',
            cuerpo=f'{v_estado}',
            destinatario=destinatario,
            url=url,
            content_type=None,
            object_id=None,
            perfil=perfil,
            prioridad=2,
            app_label=app_label,
            fecha_hora_visible=datetime.now() + timedelta(days=3))
        if request:
            notificacion.save(request)
        else:
            notificacion.save()
    except Exception as ex:
        return {'error': ex.__str__()}
