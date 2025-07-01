# -*- coding: UTF-8 -*-
from datetime import datetime
import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.utils.dateparse import parse_date
from django.utils.datetime_safe import datetime

from core.choices.models.sagest import MY_ESTADO_SOLICITUD_EQUIPO_COMPUTO, MY_ESTADO_EQUIPO_COMPUTO
from decorators import secure_module, last_access
from sagest.models import TerminosCondicionesEquipoComputo, EquipoComputo, ActivoTecnologico, \
    ConfiguracionEquipoComputo, SolicitudEquipoComputo, PreguntaEstadoEC, EstadoEntregaEC, EquipoPrestado, \
    HistorialSolicitudEC, EstadoDevuelveEC
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador
from sga.models import  Persona
from sagest.forms import TerminoyCondicionForm, ConfiguracionEquipoComputoForm, EquipoComputoForm, \
    SolicitudEquipoComputoForm, PreguntaEstadoECForm, \
    EntregarEquipoComputoForm, GestionSolicitudECForm
from sga.templatetags.sga_extras import encrypt
from utils.filtros_genericos import filtro_persona_select_v2, filtro_persona_select
import random
import string

unicode = str


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    data['periodo'] = periodosesion = request.session['periodo']
    configuracionactiva = ConfiguracionEquipoComputo.objects.filter(status=True, activo=True).first()
    terminosactivo = TerminosCondicionesEquipoComputo.objects.filter(status=True, activo=True).first()

    hoy = datetime.now()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addterminoycondicion':
            try:
                f = TerminoyCondicionForm(request.POST)
                if not f.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in f.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})

                terminosycondiciones = TerminosCondicionesEquipoComputo(
                    titulo=f.cleaned_data['titulo'],
                    descripcion=f.cleaned_data['descripcion'],
                    activo=f.cleaned_data['activo'],
                )
                terminosycondiciones.save(request)
                if terminosycondiciones.activo:
                    TerminosCondicionesEquipoComputo.objects.filter(status=True).exclude(id=terminosycondiciones.id).update(activo=False)
                return JsonResponse({"result": False, "mensaje": u"Datos guardados correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos. [%s]" % ex})

        elif action == 'editterminoycondicion':
            try:
                id = request.POST['id']
                termino = TerminosCondicionesEquipoComputo.objects.get(id=int(encrypt(id)))
                f = TerminoyCondicionForm(request.POST, instancia=termino)

                if not f.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in f.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})

                termino.titulo = f.cleaned_data['titulo']
                termino.descripcion = f.cleaned_data['descripcion']
                termino.activo = f.cleaned_data['activo']
                termino.save(request)
                if termino.activo:
                    TerminosCondicionesEquipoComputo.objects.filter(status=True).exclude(id=termino.id).update(activo=False)
                return JsonResponse({"result": False, "mensaje": u"Datos guardados correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos. [%s]" % ex})

        elif action == 'cambiarestadoterminos':
            try:
                id = request.POST['id']
                termino = TerminosCondicionesEquipoComputo.objects.get(id=id)
                # if termino.activo and SolicitudEquipoComputo.objects.filter(status=True, estadosolicitud__in=[1, 2, 3], terminos=termino):
                #     return JsonResponse({"result": True, "mensaje": u"No se puede desactivar, ya que existe una solicitud en proceso."})

                termino.activo = not termino.activo
                termino.save(request)
                if termino.activo:
                    TerminosCondicionesEquipoComputo.objects.filter(status=True).exclude(id=termino.id).update(activo=False)

                return JsonResponse({"result": True, "mensaje": u"Estado actualizado correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos. [%s]" % ex})

        elif action == 'delterminoycondicion':
            try:
                id = request.POST['id']
                termino = TerminosCondicionesEquipoComputo.objects.get(id=id)
                termino.status = False
                termino.save(request)
                return JsonResponse({"error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "message": u"Error al eliminar el registro. [%s]" % ex})

        elif action == 'addpreguntasestadoequipo':
            try:
                f = PreguntaEstadoECForm(request.POST)
                if not f.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in f.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})

                pregunta = PreguntaEstadoEC(
                    descripcion=f.cleaned_data['descripcion'],
                    activo=f.cleaned_data['activo'],
                )
                pregunta.save(request)
                return JsonResponse({"result": False, "mensaje": u"Datos guardados correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos. [%s]" % ex})

        elif action == 'editpreguntasestadoequipo':
            try:
                id = request.POST['id']
                pregunta = PreguntaEstadoEC.objects.get(id=int(encrypt(id)))
                f = PreguntaEstadoECForm(request.POST, instancia=pregunta)
                if not f.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in f.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})

                pregunta.descripcion = f.cleaned_data['descripcion']
                pregunta.activo = f.cleaned_data['activo']
                pregunta.save(request)
                return JsonResponse({"result": False, "mensaje": u"Datos guardados correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos. [%s]" % ex})

        elif action == 'delpregutaestado':
            try:
                id = request.POST['id']
                pregunta = PreguntaEstadoEC.objects.get(id=id)
                pregunta.status = False
                pregunta.save(request)
                return JsonResponse({"error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "message": u"Error al eliminar el registro. [%s]" % ex})

        elif action == 'cambiarestadopregunta':
            try:
                id = request.POST['id']
                pregunta = PreguntaEstadoEC.objects.get(id=id)
                pregunta.activo = not pregunta.activo
                pregunta.save(request)
                return JsonResponse({"result": True, "mensaje": u"Estado actualizado correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos. [%s]" % ex})

        elif action == 'migrarequiposcomputo':
            try:
                listado = json.loads(request.POST['lista_items1'])
                if len(listado) < 1:
                    return JsonResponse({"result": True, "mensaje": u"Debe seleccionar al menos un equipo de cómputo."})

                # if not configuracionactiva:
                #     return JsonResponse({"result": True, "mensaje": u"No existe una configuración activa."})

                for item in listado:
                    activo = ActivoTecnologico.objects.get(id=int(item['id']))

                    # equipo = EquipoComputo.objects.filter(equipo=activo, configuracion=configuracionactiva)
                    # tiempo_obj = datetime.strptime(item['tiempolimite'], '%H:%M').time()

                    equipo = EquipoComputo(
                        equipo=activo,
                        activo=item['activo'],
                    )

                    equipo.save(request)
                return JsonResponse({"result": False, "mensaje": u"Migración realizada correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al migrar equipos de cómputo [%s]" % ex})

        elif action == 'editequipocomputo':
            try:
                id = request.POST['id']
                equipo = EquipoComputo.objects.get(id=int(encrypt(id)))
                f = EquipoComputoForm(request.POST, instancia=equipo)
                if f.is_valid():
                    # equipo.tiempolimite = f.cleaned_data['tiempolimite']
                    equipo.activo = f.cleaned_data['activo']
                    equipo.save(request)
                    return JsonResponse({"result": False, "mensaje": u"Datos guardados correctamente."})
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos. [%s]" % ex})

        elif action == 'delequipocomputo':
            try:
                id = request.POST['id']
                equipo = EquipoComputo.objects.get(id=int(id))
                equipo.status = False
                equipo.save(request)
                return JsonResponse({"error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "message": u"Error al eliminar el registro. [%s]" % ex})

        elif action == 'addconfiguracion':
            try:
                f = ConfiguracionEquipoComputoForm(request.POST)
                if not f.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in f.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})

                configuracion = ConfiguracionEquipoComputo(
                    titulo=f.cleaned_data['titulo'],
                    descripcion=f.cleaned_data['descripcion'],
                    fechainicio=f.cleaned_data['fechainicio'],
                    fechafin=f.cleaned_data['fechafin'],
                    horainiciouso=f.cleaned_data['horainiciouso'],
                    horafinuso=f.cleaned_data['horafinuso'],
                    # tiempolimite=f.cleaned_data['tiempolimite'],
                    activo=f.cleaned_data['activo'], )
                configuracion.save(request)
                if configuracion.activo:
                    ConfiguracionEquipoComputo.objects.filter(activo=True).exclude(id=configuracion.id).update(activo=False)
                return JsonResponse({"result": False, "mensaje": u"Datos guardados correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos. [%s]" % ex})

        elif action == 'editconfiguracion':
            try:
                id = request.POST['id']
                configuracion = ConfiguracionEquipoComputo.objects.get(id=int(encrypt(id)))
                f = ConfiguracionEquipoComputoForm(request.POST, instancia=configuracion)
                if not f.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in f.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})

                configuracion.titulo = f.cleaned_data['titulo']
                configuracion.descripcion = f.cleaned_data['descripcion']
                configuracion.fechainicio = f.cleaned_data['fechainicio']
                configuracion.fechafin = f.cleaned_data['fechafin']
                configuracion.horainiciouso = f.cleaned_data['horainiciouso']
                configuracion.horafinuso = f.cleaned_data['horafinuso']
                # configuracion.tiempolimite = f.cleaned_data['tiempolimite']
                configuracion.activo = f.cleaned_data['activo']
                configuracion.save(request)

                if configuracion.activo:
                    ConfiguracionEquipoComputo.objects.filter(activo=True).exclude(id=configuracion.id).update(activo=False)
                return JsonResponse({"result": False, "mensaje": u"Datos guardados correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos. [%s]" % ex})

        elif action == 'delconfiguracion':
            try:
                id = request.POST['id']
                configuracion = ConfiguracionEquipoComputo.objects.get(id=int(id))

                if configuracion.activo:
                    return JsonResponse({"error": True, "message": u"No se puede eliminar una configuración activa."})

                # if configuracion.existe_relacion_equipo_computo():
                #     return JsonResponse({"error": True, "message": u"No se puede eliminar una configuración que tenga equipos de cómputo asignados."})

                configuracion.status = False
                configuracion.save(request)
                return JsonResponse({"error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "message": u"Error al eliminar el registro. [%s]" % ex})

        elif action == 'cambiarestadoconfiguracion':
            try:
                id = request.POST['id']
                configuracion = ConfiguracionEquipoComputo.objects.get(id=int(id))
                # if configuracion.activo and SolicitudEquipoComputo.objects.filter(status=True, estadosolicitud__in=[1, 2, 3], configuracion=configuracion).exists():
                #     return JsonResponse({"result": True, "mensaje": u"No se puede desactivar, ya que existe una solicitud en proceso."})
                configuracion.activo = not configuracion.activo
                configuracion.save(request)
                if configuracion.activo:
                    ConfiguracionEquipoComputo.objects.filter(activo=True).exclude(id=configuracion.id).update(activo=False)
                return JsonResponse({"result": True, "mensaje": u"Estado actualizado correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos. [%s]" % ex})

        elif action == 'cambiarestadoequipocomputo':
            try:
                id = request.POST['id']
                equipo = EquipoComputo.objects.get(id=int(id))
                equipo.activo = not equipo.activo
                equipo.save(request)
                return JsonResponse({"result": True, "mensaje": u"Estado actualizado correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos. [%s]" % ex})

        elif action == 'addsolicitudequipo':
            try:
                f = SolicitudEquipoComputoForm(request.POST)
                if not f.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in f.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})

                config = ConfiguracionEquipoComputo.objects.get(id=int(request.POST['configuracion']))
                terminos = TerminosCondicionesEquipoComputo.objects.get(id=int(request.POST['terminos']))
                estadosoli = int(f.cleaned_data['estadosolicitud'])
                solicitante = f.cleaned_data['solicitante']

                codigo = generate_unique_code_ec()

                solicitud = SolicitudEquipoComputo(
                    configuracion=config,
                    terminos=terminos,
                    solicitante=solicitante,
                    inscripcion=solicitante.inscripcion_principal(),
                    estadosolicitud=estadosoli,
                    motivo=f.cleaned_data['motivo'],
                    fechauso=f.cleaned_data['fechauso'],
                    codigo=codigo,
                    responsable=persona,
                    tipodocumento=f.cleaned_data['tipodocumento'],
                    descripciondocumento=f.cleaned_data['descripciondocumento'],
                )

                if estadosoli == 1 or estadosoli == 2:
                    observacion = 'SOLICITUD CREADA' if estadosoli == 1 else 'SOLICITUD CREADA Y APROBADA'
                    cambiar_estado_crear_historial(request, solicitud, estadosoli, observacion, persona)

                elif estadosoli == 3:
                    if SolicitudEquipoComputo.objects.filter(status=True, configuracion=config,  solicitante=solicitante, estadosolicitud=3):
                        return JsonResponse({"result": True, "mensaje": f"El solicitante ya tiene un equipo en uso."})

                    horaactual = datetime.now().time().strftime('%H:%M:%S')
                    solicitud.horainiciouso = horaactual

                    equipo = f.cleaned_data['equipocomputo']
                    observacion = f.cleaned_data['observacion'] if f.cleaned_data['observacion'] != '' else 'EQUIPO ENTREGADO'

                    cambiar_estado_crear_historial(request, solicitud, estadosoli, observacion, persona)
                    equipoprestado = EquipoPrestado(solicitudec=solicitud, persona=solicitud.solicitante,
                                                    equipocomputo=equipo)
                    equipoprestado.save(request)
                    cambiar_estado_equipo(request, solicitud, solicitud.solicitante, 2)

                    itemspreguntas = json.loads(request.POST['lista_items1'])
                    for item in itemspreguntas:
                        pregunta = PreguntaEstadoEC.objects.get(id=int(item['id']))
                        estadoentrega = EstadoEntregaEC(solicitudec=solicitud, preguntaestado=pregunta,
                                                        acepto=item['acepto'])
                        estadoentrega.save(request)

                return JsonResponse({"result": False, "mensaje": u"Datos guardados correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos. [%s]" % ex})

        elif action == 'gestionsolicitud':
            try:
                f = GestionSolicitudECForm(request.POST)
                if not f.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in f.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})

                solicitud = SolicitudEquipoComputo.objects.get(id=int(f.cleaned_data['solicitud']))
                estadosoli = int(f.cleaned_data['estadosolicitud'])
                if estadosoli == solicitud.estadosolicitud:
                    return JsonResponse({"result": True, "mensaje": f"La solicitud ya se encuentra en el estado:{solicitud.get_estadosolicitud_display()}"})
                itemspreguntas = json.loads(request.POST['lista_items1'])
                if estadosoli == 1:
                    cambiar_estado_crear_historial(request, solicitud, estadosoli, 'CAMBIO A ESTADO PENDIENTE', persona)
                if estadosoli == 2:
                    if not solicitud.configuracion.activo:
                        return JsonResponse({"result": True, "mensaje": f"La configuración relacionada con la solicitud esta inactiva."})
                    cambiar_estado_crear_historial(request, solicitud, estadosoli, 'SOLICITUD APROBADA', persona)
                elif estadosoli == 3:
                    if not solicitud.configuracion.activo:
                        return JsonResponse({"result": True, "mensaje": f"La configuración relacionada con la solicitud esta inactiva."})
                    if SolicitudEquipoComputo.objects.filter(status=True, configuracion=solicitud.configuracion, solicitante=solicitud.solicitante, estadosolicitud=3).exclude(id=solicitud.id):
                        return JsonResponse({"result": True, "mensaje": f"El solicitante ya tiene un equipo en uso."})
                    horaactual = datetime.now().time().strftime('%H:%M:%S')
                    solicitud.horainiciouso = horaactual
                    solicitud.tipodocumento = f.cleaned_data['tipodocumento']
                    solicitud.descripciondocumento = f.cleaned_data['descripciondocumento']
                    solicitud.save(request)
                    equipo = f.cleaned_data['equipocomputo']
                    observacion = f.cleaned_data['observacion'] if f.cleaned_data['observacion'] != '' else 'EQUIPO ENTREGADO'
                    equipoprestado = EquipoPrestado(solicitudec=solicitud, persona=solicitud.solicitante,
                                                    equipocomputo=equipo)
                    equipoprestado.save(request)
                    cambiar_estado_crear_historial(request, solicitud, estadosoli, observacion, persona)
                    cambiar_estado_equipo(request, solicitud, solicitud.solicitante, 2)
                    for item in itemspreguntas:
                        pregunta = PreguntaEstadoEC.objects.get(id=int(item['id']))
                        estadoentrega = EstadoEntregaEC(solicitudec=solicitud, preguntaestado=pregunta,
                                                        acepto=item['acepto'])
                        estadoentrega.save(request)
                elif estadosoli == 5:
                    observacion = f.cleaned_data['observacion'] if f.cleaned_data['observacion'] != '' else 'SOLICITUD RECHAZADA'
                    cambiar_estado_crear_historial(request, solicitud, estadosoli, observacion, persona)
                    cambiar_estado_equipo(request, solicitud, solicitud.solicitante, 1)

                return JsonResponse({"result": False, "mensaje": u"Datos guardados correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos. [%s]" % ex})

        elif action == 'finalizarprestamo':
            try:
                f = EntregarEquipoComputoForm(request.POST)
                if not f.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in f.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})

                solicitud = SolicitudEquipoComputo.objects.get(id=int(f.cleaned_data['solicitud']))
                itemspreguntas = json.loads(request.POST['lista_items1'])
                observacion = f.cleaned_data['observacion'] if f.cleaned_data['observacion'] != '' else 'EQUIPO DEVUELTO'

                for item in itemspreguntas:
                    preguntaentrega = EstadoEntregaEC.objects.get(id=int(item['id']))
                    estadodevulve = EstadoDevuelveEC(solicitudec=solicitud, estadoentrega=preguntaentrega, acepto=item['acepto'])
                    estadodevulve.save(request)

                horaactual = datetime.now().time().strftime('%H:%M:%S')
                solicitud.horafinuso = horaactual
                solicitud.save(request)

                cambiar_estado_crear_historial(request, solicitud, 4, observacion, persona)

                cambiar_estado_equipo(request, solicitud, solicitud.solicitante, 1)

                return JsonResponse({"result": False, "mensaje": u"Datos guardados correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos. [%s]" % ex})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addterminoycondicion':
                try:
                    form = TerminoyCondicionForm()
                    data['form'] = form
                    data['action'] = action
                    template = get_template('adm_equiposcomputo/modal/formterminoycondicion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editterminoycondicion':
                try:
                    data['id'] = id = request.GET['id']
                    termino = TerminosCondicionesEquipoComputo.objects.get(id=id)
                    form = TerminoyCondicionForm(initial=model_to_dict(termino))
                    data['form'] = form
                    data['action'] = action
                    template = get_template('adm_equiposcomputo/modal/formterminoycondicion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editequipocomputo':
                try:
                    data['id'] = id = request.GET['id']
                    equipo = EquipoComputo.objects.get(id=id)
                    form = EquipoComputoForm(initial={
                        'activo': equipo.activo,
                    })
                    data['form'] = form
                    data['action'] = action
                    template = get_template('adm_equiposcomputo/modal/formequipocomputo.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'addconfiguracion':
                try:
                    form = ConfiguracionEquipoComputoForm(initial={'fechainicio': datetime.now().date()})
                    data['form'] = form
                    data['action'] = action
                    template = get_template('adm_equiposcomputo/modal/formconfiguracion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editconfiguracion':
                try:
                    data['id'] = id = request.GET['id']
                    configuracion = ConfiguracionEquipoComputo.objects.get(id=int(id))
                    form = ConfiguracionEquipoComputoForm(initial=model_to_dict(configuracion))
                    data['form'] = form
                    data['action'] = action
                    template = get_template('adm_equiposcomputo/modal/formconfiguracion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})

                except Exception as ex:
                    messages.error(request, f'{ex}')

            if action == 'migrarequiposcomputo':
                try:
                    data['action'] = action
                    ids_migrados = [i.equipo.id for i in EquipoComputo.objects.filter(status=True)]
                    activostecnologicos = ActivoTecnologico.objects.filter(status=True,
                                                                           activotecnologico__catalogo_id=4590,
                                                                           activotecnologico__codigogobierno__isnull=False).exclude(id__in=ids_migrados).order_by('-id')
                    listado = []
                    for activo in activostecnologicos:
                        activofijo = activo.activotecnologico
                        listado.append({
                            'id_activo_tec': activo.id,
                            'descripcion': activofijo.descripcion,
                            'codigogobierno': activofijo.codigogobierno,
                            'codigointerno': activofijo.codigointerno,
                            'codigotic': activo.codigotic,
                            'modelo': activofijo.modelo,
                            'marca': activofijo.marca,
                            'ubicacion': activo.ubicacion.nombre if activo.ubicacion else 'No Asignado',
                            'responsable': activo.responsable.nombre_completo_inverso() if activo.responsable else 'Sin Responsable',
                        })
                    data['activostecnologicos'] = listado
                    template = get_template('adm_equiposcomputo/modal/formmigrarequipos.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'terminosycondiciones':
                try:
                    data['title'] = u'Términos y Condiciones'
                    data['action'] = action
                    data['persona'] = persona = Persona.objects.get(id=persona.id)
                    data['switchery']=True
                    request.session['viewactivoth'] = ['configuraciones', action]

                    url_vars, filtro, search, = f'&action={action}', Q(status=True), request.GET.get('s', '').strip()
                    estado = request.GET.get('estado', '')

                    if search:
                        filtro = filtro & Q(Q(titulo__icontains=search)|Q(descripcion__icontains=search))
                        data['s'] = search
                        url_vars += f'&s={search}'

                    if estado:
                        estado = int(estado)
                        activo = estado == 1
                        filtro = filtro & Q(Q(activo=activo))
                        data['estado'] = estado
                        url_vars += f'&estado={estado}'

                    terminosycondiciones = TerminosCondicionesEquipoComputo.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(terminosycondiciones, 10)
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
                    request.session['viewactivo'] = 1
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['terminosycondiciones'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, "adm_equiposcomputo/terminosycondiciones.html", data)
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'configuracionequiposcomputo':
                try:
                    data['title'] = u'Configuración general'
                    data['action'] = action
                    data['switchery'] = True

                    request.session['viewactivoth'] = ['configuraciones', action]

                    url_vars, filtro, search, = f'&action={action}', Q(status=True), request.GET.get('s', '').strip()
                    estado = request.GET.get('estado', '')

                    if search:
                        filtro = filtro & Q(Q(titulo__icontains=search)|Q(descripcion__icontains=search))
                        data['s'] = search
                        url_vars += f'&s={search}'

                    if estado:
                        estado = int(estado)
                        activo = estado == 1
                        filtro = filtro & Q(Q(activo=activo))
                        data['estado'] = estado
                        url_vars += f'&estado={estado}'

                    configuraciones = ConfiguracionEquipoComputo.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(configuraciones, 10)
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
                    request.session['viewactivo'] = 1
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['configuraciones'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, "adm_equiposcomputo/configuracionequiposcomputo.html", data)
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'equiposcomputo':
                try:
                    data['title'] = u'Equipos de Cómputo'
                    request.session['viewactivoth'] = ['configuraciones', 'equiposcomputo']

                    url_vars, filtro, search, =  f'&action={action}', Q(status=True), request.GET.get('s', '').strip()
                    estadoequipo, estadouso = request.GET.get('estadoequipo', ''), request.GET.get('estadouso', '')

                    if search:
                        ss = search.split(' ')
                        data['s'] = search
                        url_vars += "&s={}".format(search)
                        if len(ss) == 1:
                            filtro = filtro & (Q(equipo__activotecnologico__codigogobierno=search) |
                                               Q(equipo__activotecnologico__serie=search) |
                                               Q(equipo__activotecnologico__codigointerno=search) |
                                               Q(equipo__activotecnologico__responsable__cedula=search) |
                                               Q(equipo__activotecnologico__responsable__pasaporte=search) |
                                               Q(equipo__activotecnologico__responsable__nombres__icontains=search) |
                                               Q(equipo__activotecnologico__responsable__apellido1__icontains=search) |
                                               Q(equipo__activotecnologico__responsable__apellido2__icontains=search))
                        else:
                            filtro = filtro & (Q(equipo__activotecnologico__responsable__apellido1__icontains=ss[0]) &
                                               Q(equipo__activotecnologico__responsable__apellido2__icontains=ss[1]) |
                                               Q(equipo__activotecnologico__descripcion=search))


                    if estadoequipo:
                        estadoequipo = int(estadoequipo)
                        activo = estadoequipo == 1
                        filtro = filtro & Q(Q(activo=activo))
                        data['estadoequipo'] = estadoequipo
                        url_vars += f'&estadoequipo={estadoequipo}'

                    if estadouso:
                        estadouso = int(estadouso)
                        filtro = filtro & Q(Q(estado=estadouso))
                        data['estadouso'] = estadouso
                        url_vars += f'&estadouso={estadouso}'

                    equiposcomputo = EquipoComputo.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(equiposcomputo, 10)
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
                    request.session['viewactivo'] = 1
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['equiposcomputo'] = page.object_list
                    data['configuracionactiva'] = configuracionactiva
                    data['url_vars'] = url_vars
                    data['estados'] = MY_ESTADO_EQUIPO_COMPUTO
                    return render(request, "adm_equiposcomputo/equiposcomputo.html", data)
                except Exception as ex:
                    messages.error(request, f'{ex}')

            if action == 'addsolicitudequipo':
                try:
                    form = SolicitudEquipoComputoForm()
                    form.fields['solicitante'].queryset = Persona.objects.none()
                    data['form'] = form
                    data['action'] = action
                    data['configuracion'] = configuracionactiva
                    data['terminos'] = terminosactivo
                    data['preguntas'] = PreguntaEstadoEC.objects.filter(status=True, activo=True).order_by('-id')
                    template = get_template('adm_equiposcomputo/modal/formsolicitudequipocomputo.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'preguntasestadoequipo':
                try:
                    data['title'] = u'Preguntas de Estado del Equipo'
                    data['action'] = action
                    data['switchery'] = True

                    request.session['viewactivoth'] = ['configuraciones', action]

                    url_vars, filtro, search, = f'&action={action}', Q(status=True), request.GET.get('s', '').strip()
                    estado, iter = request.GET.get('estado', ''), False

                    if search:
                        filtro = filtro & Q(descripcion__icontains=search)
                        data['s'] = search
                        url_vars += f'&s={search}'

                    if estado:
                        estado = int(estado)
                        activo = estado == 1
                        filtro = filtro & Q(activo=activo)
                        data['estado'] = estado
                        url_vars += f'&estado={estado}'

                    preguntas = PreguntaEstadoEC.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(preguntas, 10)
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
                    request.session['viewactivo'] = 1
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['preguntas'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, "adm_equiposcomputo/preguntasestado.html", data)
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'addpreguntasestadoequipo':
                try:
                    form = PreguntaEstadoECForm()
                    data['form'] = form
                    data['action'] = action
                    template = get_template('adm_equiposcomputo/modal/formpreguntaestadoequipo.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editpreguntasestadoequipo':
                try:
                    data['id'] = id = request.GET['id']
                    pregunta = PreguntaEstadoEC.objects.get(pk=id)
                    form = PreguntaEstadoECForm(initial={
                        'descripcion': pregunta.descripcion,
                        'activo': pregunta.activo
                    })
                    data['form'] = form
                    data['action'] = action
                    template = get_template('adm_equiposcomputo/modal/formpreguntaestadoequipo.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'verterminoycondicion':
                try:
                    id = request.GET['id']
                    data['termino'] = TerminosCondicionesEquipoComputo.objects.get(pk=id)
                    template = get_template('adm_equiposcomputo/modal/verterminoycondicion.html')
                    template = get_template('adm_equiposcomputo/modal/verterminoycondicion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'detallesolicitud':
                try:
                    id = request.GET['id']
                    data['solicitud'] = solicitud = SolicitudEquipoComputo.objects.get(pk=id)
                    data['historial'] = solicitud.historialsolicitudec_set.filter(status=True).order_by('id')
                    data['preguntasestadoentrega'] = solicitud.get_preguntasestadoentrega()
                    data['preguntasestadodevuelve'] = solicitud.get_preguntasestadodevuelve()
                    template = get_template('adm_equiposcomputo/modal/detallesolicitud.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'gestionsolicitud':
                try:
                    id = request.GET['id']
                    solicitud = SolicitudEquipoComputo.objects.get(pk=id)
                    form = GestionSolicitudECForm(initial={'solicitud': solicitud.id})
                    data['form'] = form
                    data['action'] = action
                    data['preguntas'] = PreguntaEstadoEC.objects.filter(status=True, activo=True)
                    template = get_template('adm_equiposcomputo/modal/formgestionsolicitud.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'finalizarprestamo':
                try:
                    id = request.GET['id']
                    data['solicitud'] = solicitud = SolicitudEquipoComputo.objects.get(pk=id)
                    form = EntregarEquipoComputoForm(initial={'solicitud': solicitud.id})
                    data['form'] = form
                    data['action'] = action
                    data['preguntasestadoentrega'] = solicitud.get_preguntasestadoentrega()
                    template = get_template('adm_equiposcomputo/modal/formdevuelveequipo.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'buscarpersonas':
                try:
                    # filtro = (Q(inscripcion__status=True, inscripcion__activo=True,
                    #           inscripcion__matricula__nivel__periodo=periodosesion,
                    #           inscripcion__matricula__status=True,
                    #           inscripcion__coordinacion__id__in=[1, 2, 3, 4, 5],
                    #           perfilusuario__visible=True, perfilusuario__status=True))
                    # idsexcluidas = SolicitudEquipoComputo.objects.filter(status=True, estadosolicitud=3).values_list('solicitante', flat=True)
                    resp = filtro_persona_select(request, [])
                    return HttpResponse(json.dumps({'status': True, 'results': resp}))
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Gestión de solicitudes'
                request.session['viewactivoth'] = ['configuraciones', 'solicitudes']

                url_vars, filtro, search, = '', Q(status=True), request.GET.get('s', '').strip()
                estado, config = request.GET.get('estado', ''), request.GET.get('config', '')
                fechadesde = request.GET.get('fechadesde', '')
                fechahasta = request.GET.get('fechahasta', '')

                if fechadesde:
                    fecha_desde_parsed = parse_date(fechadesde)
                    if fecha_desde_parsed:
                        data['fechadesde'] = fechadesde
                        url_vars += f'&fechadesde={fechadesde}'
                        filtro = filtro & Q(fechauso__gte=fecha_desde_parsed)

                if fechahasta:
                    fecha_hasta_parsed = parse_date(fechahasta)
                    if fecha_hasta_parsed:
                        data['fechahasta'] = fechahasta
                        url_vars += f'&fechahasta={fechahasta}'
                        filtro = filtro & Q(fechauso__lte=fecha_hasta_parsed)

                if search:
                    ss = search.split(" ")
                    q_objects = [
                        Q(solicitante__nombres__icontains=term) | Q(solicitante__apellido1__icontains=term) | Q(codigo__icontains=term) |
                        Q(solicitante__cedula__icontains=term) | Q(solicitante__apellido2__icontains=term) for term in ss if term]
                    filtro = filtro & Q(*q_objects)
                    data['s'] = search
                    url_vars += f'&s={search}'

                if estado:
                    estadosolicitud = int(estado)
                    filtro = filtro & Q(estadosolicitud=estadosolicitud)
                    data['estado'] = estadosolicitud
                    url_vars += f'&estado={estadosolicitud}'

                if config:
                    config = int(config)
                    filtro = filtro & Q(configuracion__id=config)
                    data['config'] = config
                    url_vars += f'&config={config}'

                solicitudes = SolicitudEquipoComputo.objects.filter(filtro).order_by('-id')
                paging = MiPaginador(solicitudes, 10)
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
                request.session['viewactivo'] = 1
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['solicitudes'] = page.object_list
                solicitudes_values = SolicitudEquipoComputo.objects.filter(filtro).values('id', 'estadosolicitud')
                data['count_pendientes'] = solicitudes_values.filter(estadosolicitud=1).count()
                data['count_aprobadas'] = solicitudes_values.filter(estadosolicitud=2).count()
                data['count_equipoentregado'] = solicitudes_values.filter(estadosolicitud=3).count()
                data['count_finalizado'] = solicitudes_values.filter(estadosolicitud=4).count()
                data['count_rechazadas'] = solicitudes_values.filter(estadosolicitud=5).count()
                data['count_total'] = solicitudes_values.count()
                data['configuraciones'] = ConfiguracionEquipoComputo.objects.filter(status=True)
                data['puedecrearsoli'] = configuracionactiva and terminosactivo
                data['url_vars'] = url_vars
                data['estados'] = MY_ESTADO_SOLICITUD_EQUIPO_COMPUTO
                return render(request, "adm_equiposcomputo/solicitudequiposcomputo.html", data)
            except Exception as ex:
                messages.error(request, f'{ex}')


def cambiar_estado_equipo(request, solicitud, responsable, estado):
    try:
        equipo_prestado = solicitud.equipoprestado_set.filter(persona=responsable).first()
        if equipo_prestado:
            equipo = equipo_prestado.equipocomputo
            equipo.estado = estado
            equipo.save(request)
    except Exception as ex:
        raise NameError(f'Error: {ex}')


def cambiar_estado_crear_historial(request, solicitud, estado, observacion, persona):
    try:
        solicitud.estadosolicitud = estado
        solicitud.save(request)
        historial = HistorialSolicitudEC(solicitudec=solicitud,
                                         estadosolicitud=solicitud.estadosolicitud,
                                         observacion=observacion,
                                         persona=persona,)
        historial.save(request)
    except Exception as ex:
        raise NameError(f'Error: {ex}')


def generate_unique_code_ec():
    length = 8
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if not SolicitudEquipoComputo.objects.filter(codigo=code).exists():
            break
    return code


