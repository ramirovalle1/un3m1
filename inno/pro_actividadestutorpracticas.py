# -*- coding: UTF-8 -*-
import os
import io
import random
import json
import calendar
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.forms import model_to_dict
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from api.helpers.functions_helper import get_variable
from django.db.models import Q, Count, Value, OuterRef, DateField, Subquery, TextField
from django.db.models.functions import Cast, TruncDate, TruncTime
from dateutil.relativedelta import relativedelta
from django.db.models.functions import Coalesce
from inno.models import UbicacionEmpresaPractica, PracticasPreprofesionalesInscripcion, TurnoEstudiantePractica, TurnoPractica, SupervisarDocentePracticaSalud, \
    DetalleSupervisarPracticaSalud, EstudianteSupervisarPracticaSalud, PlanificacionMensualSalud, DetallePlanificacionMensualSalud, DetalleTemaPlanificacionMensualSalud, InformePlanificacionSemanalSalud, \
    EstadoEvidenciaSalud, DetalleEstadoEvidenciaSalud, FirmaEvidenciaDocente
from inno.forms import TurnoPracticaForm, TurnoEstudianteForm, RegisitroSupervisarPracticaForm, PlanificacionMensualForm, DetallePlanificacionMensual2Form, InformePlanificacionMensualForm
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, notificacion, generar_nombre, remover_caracteres_especiales
from sga.models import Carrera, Profesor, AsignacionEmpresaPractica, ItinerariosMalla, MESES_CHOICES, DetalleDistributivo, Malla, ClaseActividad, CoordinadorCarrera, Group
from sagest.models import DistributivoPersona
from core.firmar_documentos_ec import JavaFirmaEc
from django.core.files.base import ContentFile
import datetime
from datetime import *
from settings import DEBUG, SITE_STORAGE
from sga.templatetags.sga_extras import encrypt, encrypt_alu, nombremes, diaisoweekday
from sga.funcionesxhtml2pdf import html_to_pdfsave_evienciassalud
from xlwt import *
from sga.funcionesxhtml2pdf import conviert_html_to_pdf

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    data['profesor'] = profesor = perfilprincipal.profesor
    periodo = request.session['periodo']
    hoy = datetime.now().date()
    hoytime = datetime.now()
    dominio_sistema = 'https://sga.unemi.edu.ec'
    if DEBUG:
        dominio_sistema = 'http://localhost:8000'
    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addturno':
            try:
                with transaction.atomic():
                    f = TurnoPracticaForm(request.POST)
                    tab = request.POST['tab']
                    if f.is_valid():
                        registro = TurnoPractica(turno=f.cleaned_data['turno'], comienza=f.cleaned_data['comienza'],
                                                  termina=f.cleaned_data['termina'], activo=f.cleaned_data['activo'])
                        registro.save(request)
                        log(u'Adicionó turno práctica Salud: %s' % (registro), request, "add")
                        messages.success(request, 'Registro guardado con éxito.')
                        # return JsonResponse({"result": False}, safe=False)
                        return JsonResponse({"result": False, 'to': f"{request.path}?action=turnossalud&tab={tab}"}, safe=False)

                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'editturno':
            try:
                with transaction.atomic():
                    registro = TurnoPractica.objects.get(pk=request.POST['id'])
                    tab = request.POST['tab']
                    f = TurnoPracticaForm(request.POST)
                    if f.is_valid():
                        registro.turno = f.cleaned_data['turno']
                        registro.comienza = f.cleaned_data['comienza']
                        registro.termina = f.cleaned_data['termina']
                        registro.activo = f.cleaned_data['activo']
                        registro.save(request)
                        log(u'Editó turno práctica Salud: %s' % registro, request, "edit")
                        # return JsonResponse({"result": False}, safe=False)
                        return JsonResponse({"result": False, 'to': f"{request.path}?action=turnossalud&tab={tab}"}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deleteturno':
            try:
                with transaction.atomic():
                    registro = TurnoPractica.objects.get(pk=int(request.POST['id']))
                    registro.status = False
                    registro.save(request)
                    log(u'Eliminó turno práctica Salud: %s' % registro, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'cantidadhorasturno':
            try:
                if 'id' in request.POST:
                    registro = TurnoPractica.objects.get(pk=int(request.POST['id']))
                    cantidad = registro.horas_entre_dos_horas()
                    if cantidad > 0:
                        return JsonResponse({"result": "ok", "cantidad": cantidad})
                raise NameError('Error al obtener los datos.')
            except Exception as ex:
                return JsonResponse({"result": "bad"})

        elif action == 'addturnoestudiante':
            try:
                with transaction.atomic():
                    f = TurnoEstudianteForm(request.POST)
                    tab = request.POST['tab']
                    if f.is_valid():
                        registro = TurnoEstudiantePractica(turno=f.cleaned_data['turno'], carrera=f.cleaned_data['carrera'], nombre=f.cleaned_data['nombre'], horas=f.cleaned_data['horas'],
                                                           abreviatura=f.cleaned_data['abreviatura'], descripcion=f.cleaned_data['descripcion'], color=f.cleaned_data['color'], activo=f.cleaned_data['activo'])
                        registro.save(request)
                        log(u'Adicionó turno estudiante práctica Salud: %s' % (registro), request, "add")
                        messages.success(request, 'Registro guardado con éxito.')
                        # return JsonResponse({"result": False}, safe=False)
                        return JsonResponse({"result": False, 'to': f"{request.path}?action=turnossalud&tab={tab}"}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'editturnoestudiante':
            try:
                with transaction.atomic():
                    registro = TurnoEstudiantePractica.objects.get(pk=request.POST['id'])
                    tab = request.POST['tab']
                    f = TurnoEstudianteForm(request.POST)
                    if f.is_valid():
                        registro.turno = f.cleaned_data['turno']
                        registro.carrera = f.cleaned_data['carrera']
                        registro.nombre = f.cleaned_data['nombre']
                        registro.horas = f.cleaned_data['horas']
                        registro.abreviatura = f.cleaned_data['abreviatura']
                        registro.descripcion = f.cleaned_data['descripcion']
                        registro.color = f.cleaned_data['color']
                        registro.activo = f.cleaned_data['activo']
                        registro.save(request)
                        log(u'Editó turno práctica Salud: %s' % registro, request, "edit")
                        # return JsonResponse({"result": False}, safe=False)
                        return JsonResponse({"result": False, 'to': f"{request.path}?action=turnossalud&tab={tab}"}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deleteturnoestudiante':
            try:
                with transaction.atomic():
                    registro = TurnoEstudiantePractica.objects.get(pk=int(request.POST['id']))
                    registro.status = False
                    registro.save(request)
                    log(u'Eliminó turno práctica Salud: %s' % registro, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'editdetestsupervisar':
            try:
                with transaction.atomic():
                    registro = DetalleSupervisarPracticaSalud.objects.get(pk=request.POST['id'])
                    f = RegisitroSupervisarPracticaForm(request.POST)
                    if f.is_valid():
                        registro.observacion = f.cleaned_data['observacion']
                        registro.save(request)
                        log(u'Editó registro supervisar práctica Salud: %s' % registro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deletedetestsupervisar':
            try:
                with transaction.atomic():
                    registro = DetalleSupervisarPracticaSalud.objects.get(pk=int(request.POST['id']))
                    registro.status = False
                    registro.save(request)
                    log(u'Eliminó registro supervisar práctica Salud: %s' % registro, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'updatecargodepartamento':
            try:
                registro = EstudianteSupervisarPracticaSalud.objects.get(pk=int(request.POST['id']))
                registro.cargodepartamentoest = request.POST['des']
                registro.save(request)
                log(u'Editó cargo departamento estudiante supervisar práctica Salud: %s' % registro, request, "edit")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad'})

        elif action == 'deleteestudiantesupervisar':
            try:
                with transaction.atomic():
                    registro = EstudianteSupervisarPracticaSalud.objects.get(pk=int(request.POST['id']))
                    registro.status = False
                    registro.save(request)
                    log(u'Eliminó estudiante supervisar práctica Salud: %s' % registro, request, "delete")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'admaddvisitasupervisor':
            with transaction.atomic():
                try:
                    if not request.POST['horario']:
                        raise NameError("Seleccione un horario para agendar.")
                    iddistributivo = request.POST['iddistributivo']
                    detalledistributivo = DetalleDistributivo.objects.get(pk=int(iddistributivo))
                    fecha = datetime.strptime(request.POST['fecha'], '%Y-%m-%d').date()
                    hora = request.POST['hora'] if 'hora' in request.POST else ''
                    turnoh = TurnoEstudiantePractica.objects.get(id=int(request.POST['horario']))
                    empresa = AsignacionEmpresaPractica.objects.get(id=int(request.POST['empresa']))
                    observacion = request.POST['observacion']
                    actividadtema = int(request.POST['actividadtema']) if 'actividadtema' in request.POST and int(request.POST['actividadtema']) > 0 else None
                    supervisor = profesor
                    ePeriodo = periodo if periodo else detalledistributivo.distributivo.periodo
                    supervisar = SupervisarDocentePracticaSalud.objects.filter(status=True, supervisor=supervisor, empresapractica=empresa, periodo=ePeriodo).first()
                    if not supervisar:
                        supervisar = SupervisarDocentePracticaSalud(supervisor=supervisor, empresapractica=empresa, periodo=ePeriodo, fecha=fecha)
                        supervisar.save(request)
                        log(u'Adicionó cabecera supervisar práctica salud: %s' % supervisar, request, "add")

                    listado_estudiantes = json.loads(request.POST['estudiantes[]'])
                    for p in listado_estudiantes:
                        estudiantesupervisar = EstudianteSupervisarPracticaSalud.objects.filter(status=True, supervisarpractica=supervisar, practicappp_id=int(p)).first()
                        if not estudiantesupervisar:
                            estudiantesupervisar = EstudianteSupervisarPracticaSalud(supervisarpractica=supervisar, practicappp_id=int(p))
                            estudiantesupervisar.save(request)
                            log(u'Adicionó estudiante supervisar práctica salud: %s' % estudiantesupervisar, request, "add")

                        detalle = DetalleSupervisarPracticaSalud(estudiantesupervisar=estudiantesupervisar, fecha=fecha, hora=hora, turno=turnoh, observacion=observacion, detalletemapm_id=actividadtema)
                        detalle.save(request)
                        log(u'Adicionó detalle supervisar práctica salud: %s' % detalle, request, "add")

                        #Envío de notificación
                        estudiante = detalle.estudiantesupervisar.practicappp.inscripcion.persona
                        titulo = f"Supervisión de prácticas pre profesionales"
                        mensaje = f'Estimad{"a" if estudiante.es_mujer() else "o"} {estudiante.nombre_completo_inverso()}, se registró visita de prácticas pre profesionales en {empresa.nombre}. Observación: {observacion}'
                        notificacion(mensaje, titulo, estudiante, None, f'/alu_practicaspro', detalle.pk, 1, 'sga', DetalleSupervisarPracticaSalud, request)

                    messages.success(request, 'Registro guardado con éxito.')
                    url_ = f'{request.path}?action=visitasupervisorsalud&id={encrypt(iddistributivo)}'
                    return JsonResponse({"result": False, "to": url_})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        if action == 'addplanificacion':
            try:
                with transaction.atomic():
                    f = PlanificacionMensualForm(request.POST)
                    f.iniciar(request.POST['carrera'], request.POST['itinerariomalla'])
                    if f.is_valid():
                        if not PlanificacionMensualSalud.objects.values('id').filter(status=True, supervisor_id=request.POST['idp'], periodo_id=request.POST['idex'], mes=int(f.cleaned_data['mes']), itinerariomalla=f.cleaned_data['itinerariomalla']).exists():
                            registro = PlanificacionMensualSalud(supervisor_id=request.POST['idp'], periodo_id=request.POST['idex'],
                                                                 mes=int(f.cleaned_data['mes']), itinerariomalla=f.cleaned_data['itinerariomalla'])
                            registro.save(request)
                            log(u'Adicionó Planificación Mensual Salud: %s' % (registro), request, "add")
                            messages.success(request, 'Registro guardado con éxito.')
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            raise NameError('El registro a ingresar ya existe.')
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'editplanificacion':
            try:
                with transaction.atomic():
                    registro = PlanificacionMensualSalud.objects.get(pk=request.POST['id'])
                    f = PlanificacionMensualForm(request.POST)
                    f.iniciar(request.POST['carrera'], request.POST['itinerariomalla'])
                    if f.is_valid():
                        if not PlanificacionMensualSalud.objects.values('id').filter(status=True, supervisor=registro.supervisor, periodo=registro.periodo, mes=int(f.cleaned_data['mes']), itinerariomalla=f.cleaned_data['itinerariomalla']).exclude(id=request.POST['id']).exists():
                            registro.mes = int(f.cleaned_data['mes'])
                            registro.itinerariomalla = f.cleaned_data['itinerariomalla']
                            registro.save(request)
                            log(u'Editó Planificación Mensual Salud: %s' % registro, request, "edit")
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            raise NameError('El registro a ingresar ya existe.')
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'informeplanificacion':
            try:
                with transaction.atomic():
                    registro = PlanificacionMensualSalud.objects.get(pk=request.POST['id'])
                    f = InformePlanificacionMensualForm(request.POST, request.FILES)

                    if not 'archivo' in request.FILES:
                        return JsonResponse({"result": "bad", "mensaje": u"Por favor, debe seleccionar un archivo en formato PDF."})

                    if 'archivo' in request.FILES:
                        arch = request.FILES['archivo']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                    if f.is_valid():
                        newfile = request.FILES['archivo']
                        nombrearchivo = f'mensual{registro.get_mes()}{registro.supervisor.id}'
                        newfile._name = generar_nombre(f"informeplanificacion{nombrearchivo}_", newfile._name)
                        registro.archivo = newfile
                        registro.save(request)
                        log(u'Editó archivo Planificación Mensual Salud: %s' % registro, request, "edit")
                        messages.success(request, 'Archivo guardado con éxito.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'informeplanificacionsemanal':
            try:
                with transaction.atomic():
                    registro = InformePlanificacionSemanalSalud.objects.get(pk=request.POST['id'])
                    f = InformePlanificacionMensualForm(request.POST, request.FILES)

                    if not 'archivo' in request.FILES:
                        return JsonResponse({"result": "bad", "mensaje": u"Por favor, debe seleccionar un archivo en formato PDF."})

                    if 'archivo' in request.FILES:
                        arch = request.FILES['archivo']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                    if f.is_valid():
                        newfile = request.FILES['archivo']
                        nombrearchivo = f"informesemanal_{registro.planificacionmensual.supervisor.persona.usuario.username}_{registro.pk}"
                        newfile._name = generar_nombre(f"{nombrearchivo}_", newfile._name)
                        registro.archivo = newfile
                        registro.save(request)
                        log(u'Editó archivo planificación Semanal Salud: %s' % registro, request, "edit")
                        messages.success(request, 'Archivo guardado con éxito.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'adddetalleplanificacion':
            try:
                with transaction.atomic():
                    f = DetallePlanificacionMensual2Form(request.POST)
                    if f.is_valid():
                        registro = DetallePlanificacionMensualSalud(planificacionmensual_id=request.POST['idp'],
                                                                    fechainicio=f.cleaned_data['fechainicio'],
                                                                    fechafin=f.cleaned_data['fechafin'],
                                                                    numerosemana=f.cleaned_data['numerosemana'],
                                                                    descripciontema=f.cleaned_data['tema'],
                                                                    objetivo=f.cleaned_data['objetivo'],
                                                                    enfoque=f.cleaned_data['enfoque'],
                                                                    evaluacion=f.cleaned_data['evaluacion'],
                                                                    horas=f.cleaned_data['horas'])
                        registro.save(request)
                        log(u'Adicionó Detalle Planificación Mensual 2 Salud: %s' % (registro), request, "add")
                        messages.success(request, 'Registro guardado con éxito.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'editdetalleplanificacion':
            try:
                with transaction.atomic():
                    registro = DetallePlanificacionMensualSalud.objects.get(pk=request.POST['id'])
                    f = DetallePlanificacionMensual2Form(request.POST)
                    if f.is_valid():
                        registro.fechainicio = f.cleaned_data['fechainicio']
                        registro.fechafin = f.cleaned_data['fechafin']
                        registro.numerosemana = f.cleaned_data['numerosemana']
                        registro.descripciontema = f.cleaned_data['tema']
                        registro.objetivo = f.cleaned_data['objetivo']
                        registro.enfoque = f.cleaned_data['enfoque']
                        registro.evaluacion = f.cleaned_data['evaluacion']
                        registro.horas = f.cleaned_data['horas']
                        registro.save(request)
                        log(u'Editó Detalle Planificación Mensual 2 Salud: %s' % registro, request, "edit")
                        messages.success(request, 'Registro editado con éxito.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'deletedetalleplanificacion':
            try:
                with transaction.atomic():
                    registro = DetallePlanificacionMensualSalud.objects.get(pk=int(request.POST['id']))
                    for sb in registro.lista_subtemas_all():
                        sb.status = False
                        sb.save(request)
                        log(u'Eliminó Detalle Subtema Planificación Mensual Salud: %s' % sb, request, "delete")
                    registro.status = False
                    registro.save(request)
                    log(u'Eliminó Detalle Planificación Mensual 2 Salud: %s' % registro, request, "delete")
                    messages.success(request, 'Registro eliminado con éxito.')
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'deleteinformeplanificacionsemanal':
            try:
                with transaction.atomic():
                    registro = InformePlanificacionSemanalSalud.objects.get(pk=int(request.POST['id']))
                    registro.status = False
                    registro.save(request)
                    log(u'Eliminó Informe Planificación Semanal Salud: %s' % registro, request, "delete")
                    messages.success(request, 'Registro eliminado con éxito.')
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'generarinformesemanal':
            try:
                with transaction.atomic():
                    data['urlbase'] = urlbase = get_variable('SITE_URL_SGA')
                    ahora = datetime.now()
                    data['pm'] = pm = PlanificacionMensualSalud.objects.get(pk=int(request.POST['id']))
                    registros_por_numerosemana = {}
                    numerosemana = request.POST['semana']
                    observacion = request.POST['observacion']
                    etiqueta, etiqueta2 = 'Editó', 'edit'

                    #INICIO CAPTURA DE DATOS PARA EL INFORME
                    detalledistributivo = DetalleDistributivo.objects.get(id=int(request.POST['iddistributivo']))
                    asignaturas = pm.itinerariomalla.itinerarioasignaturasalud_set.filter(status=True)
                    if asignaturas: semestre = asignaturas.last().asignaturamalla.nivelmalla.orden
                    else: semestre = pm.itinerariomalla.nivel.orden
                    data['semestre'] = semestre
                    data['tutorsupervisor'] = eProfesor = detalledistributivo.distributivo.profesor
                    data['ePeriodo'] = ePeriodo = detalledistributivo.distributivo.periodo
                    estudiantespracticas = PracticasPreprofesionalesInscripcion.objects.filter(status=True, supervisor=eProfesor, itinerariomalla=pm.itinerariomalla, culminada=False, estadosolicitud__in=[1, 2], preinscripcion__preinscripcion__periodo=ePeriodo)
                    listadopracticas = estudiantespracticas.order_by('inscripcion_id').values_list('id', flat=True).distinct('inscripcion_id')
                    listadoempresas = PracticasPreprofesionalesInscripcion.objects.values_list('asignacionempresapractica__nombre', flat=True).filter(pk__in=listadopracticas).order_by('asignacionempresapractica__nombre').distinct('asignacionempresapractica__nombre')
                    lugarpracticas = []
                    for e in listadoempresas:
                        lugarpracticas.append(e)
                    data['lugarpracticas'] = lugarpracticas
                    data['periodorotacion'] = estudiantespracticas.first().periodoppp if estudiantespracticas else ePeriodo
                    docenteasignaturas = []
                    fecha_inicio_pm = date(ahora.year, pm.mes, 1)
                    fecha_fin_pm = date(ahora.year, pm.mes, calendar.monthrange(ahora.year, pm.mes)[1])
                    for a in asignaturas:
                        materia = a.asignaturamalla.materia_set.filter(status=True, nivel__periodo=pm.periodo, silabo__silabosemanal__fechafinciosemana__gte=fecha_inicio_pm, silabo__silabosemanal__fechainiciosemana__lte=fecha_fin_pm).first()
                        docente = materia.profesor_principal()
                        docenteasignaturas.append(docente)
                    data['docenteasignaturas'] = docenteasignaturas
                    # FIN CAPTURA DE DATOS PARA EL INFORME

                    if int(numerosemana) == 100:
                        # listadoregistros = pm.detalleplanificacionmensualsalud_set.filter(status=True).order_by('numerosemana').exclude(numerosemana__in=pm.informeplanificacionsemanalsalud_set.values_list('numerosemana', flat=True).filter(status=True, archivo__isnull=False))
                        listadoregistros = pm.detalleplanificacionmensualsalud_set.filter(status=True).order_by('numerosemana')
                        listado_semanas = listadoregistros.values_list('numerosemana', flat=True).distinct('numerosemana')

                        for s in listado_semanas:
                            registros_por_numerosemana = {}
                            numerosemana = s
                            eListadoregistros = listadoregistros.filter(numerosemana=numerosemana)
                            informesemanal = InformePlanificacionSemanalSalud.objects.filter(planificacionmensual=pm, nombre=f'Informe semanal {numerosemana}', numerosemana=numerosemana, status=True).first()
                            if not informesemanal:
                                etiqueta, etiqueta2 = 'Adicionó', 'add'
                                informesemanal = InformePlanificacionSemanalSalud(planificacionmensual=pm, nombre=f'Informe semanal {numerosemana}', numerosemana=numerosemana)
                                informesemanal.save(request)

                            fecha_inicio_ps, fecha_fin_ps = fecha_inicio_pm, fecha_fin_pm
                            if eListadoregistros:
                                eRegistro = eListadoregistros.first()
                                data['f_inicio'] = fecha_inicio_ps = eRegistro.fechainicio
                                data['f_fin'] = fecha_fin_ps = eRegistro.fechafin
                                data['totalhorassemanal'] = eRegistro.horas
                            for registro in eListadoregistros:
                                numerosemana = registro.numerosemana
                                if numerosemana not in registros_por_numerosemana:
                                    registros_por_numerosemana[numerosemana] = []
                                registros_por_numerosemana[numerosemana].append(registro)
                            data['eListado'] = registros_por_numerosemana
                            data['observaciones'] = observacion

                            # INICIO GENERA INFORME
                            qrname = f"informesemanal_{persona.usuario.username}_{informesemanal.pk}"
                            rutafolder = f"planificacionsemanal/{str(ahora.year)}/{ahora.month:02d}/"
                            folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'planificacionsemanal', str(ahora.year), f'{ahora.month:02d}', ''))
                            os.makedirs(folder, exist_ok=True)
                            genero, archivogenerado = html_to_pdfsave_evienciassalud('alu_practicaspro/formatos_salud/tutor/planificacionsemanal.html',
                                                                                                  {'pagesize': 'A4', 'data': data, }, qrname + '.pdf', rutafolder)
                            # FIN GENERA INFORME

                            informesemanal.fechainicio = fecha_inicio_ps
                            informesemanal.fechafin = fecha_fin_ps
                            informesemanal.archivo = rutafolder + qrname + '.pdf'
                            informesemanal.observacion = observacion.strip()
                            informesemanal.save(request)
                            log(u'%s Informe Planificación Semanal Salud: %s' % (etiqueta, informesemanal), request, etiqueta2)
                    else:
                        listadoregistros = pm.detalleplanificacionmensualsalud_set.filter(status=True, numerosemana=numerosemana).order_by('numerosemana')
                        informesemanal = InformePlanificacionSemanalSalud.objects.filter(planificacionmensual=pm, nombre=f'Informe semanal {numerosemana}', numerosemana=numerosemana, status=True).first()
                        if not informesemanal:
                            etiqueta, etiqueta2 = 'Adicionó', 'add'
                            informesemanal = InformePlanificacionSemanalSalud(planificacionmensual=pm, nombre=f'Informe semanal {numerosemana}', numerosemana=numerosemana)
                            informesemanal.save(request)

                        fecha_inicio_ps, fecha_fin_ps = fecha_inicio_pm, fecha_fin_pm
                        if listadoregistros:
                            eRegistro = listadoregistros.first()
                            data['f_inicio'] = fecha_inicio_ps = eRegistro.fechainicio
                            data['f_fin'] = fecha_fin_ps = eRegistro.fechafin
                            data['totalhorassemanal'] = eRegistro.horas
                        for registro in listadoregistros:
                            numerosemana = registro.numerosemana
                            if numerosemana not in registros_por_numerosemana:
                                registros_por_numerosemana[numerosemana] = []
                            registros_por_numerosemana[numerosemana].append(registro)
                        data['eListado'] = registros_por_numerosemana
                        data['observaciones'] = observacion

                        # INICIO GENERA INFORME
                        qrname = f"informesemanal_{persona.usuario.username}_{informesemanal.pk}"
                        rutafolder = f"planificacionsemanal/{str(ahora.year)}/{ahora.month:02d}/"
                        folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'planificacionsemanal', str(ahora.year), f'{ahora.month:02d}', ''))
                        os.makedirs(folder, exist_ok=True)
                        genero, archivogenerado = html_to_pdfsave_evienciassalud('alu_practicaspro/formatos_salud/tutor/planificacionsemanal.html',
                                                                                 {'pagesize': 'A4', 'data': data, }, qrname + '.pdf', rutafolder)
                        # FIN GENERA INFORME

                        informesemanal.fechainicio = fecha_inicio_ps
                        informesemanal.fechafin = fecha_fin_ps
                        informesemanal.archivo = rutafolder + qrname + '.pdf'
                        informesemanal.observacion = observacion.strip()
                        informesemanal.save(request)
                        log(u'%s Informe Planificación Semanal Salud: %s' % (etiqueta, informesemanal), request, etiqueta2)
                    messages.success(request, 'Proceso ejecutado con éxito.')
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
                messages.warning(request, 'Existieron problemas en la generación del informe. Intente nuevamente más tarde.')
            return JsonResponse(res_json, safe=False)

        elif action == 'generardetallepm':
            with transaction.atomic():
                try:
                    listaids = request.POST['id'].split(',')
                    idpm, iddistributivo = listaids[0], listaids[1]
                    instancia = PlanificacionMensualSalud.objects.get(id=int(encrypt(idpm)))
                    detalledistributivo = DetalleDistributivo.objects.get(id=int(encrypt(iddistributivo)))
                    eProfesor = detalledistributivo.distributivo.profesor
                    asignaturas = instancia.itinerariomalla.itinerarioasignaturasalud_set.filter(status=True)
                    eTotalhoras = 0
                    listadocentes = []
                    listatemas = []
                    fecha = datetime.now().date()
                    anio = fecha.year
                    mes = MESES_CHOICES[instancia.mes - 1]
                    fecha_inicio_pm = date(anio, instancia.mes, 1)
                    fecha_fin_pm = date(anio, instancia.mes, calendar.monthrange(anio, instancia.mes)[1])
                    for a in asignaturas:
                        materia = a.asignaturamalla.materia_set.filter(status=True, nivel__periodo=instancia.periodo,
                                                                       silabo__silabosemanal__fechafinciosemana__gte=fecha_inicio_pm,
                                                                       silabo__silabosemanal__fechainiciosemana__lte=fecha_fin_pm).first()
                        docente = materia.profesor_principal()
                        silabo = materia.silabo_set.filter(status=True, aprobado=True).first()
                        if not silabo: silabo = materia.silabo_set.filter(status=True).first()
                        if silabo:
                            silabosemanal = silabo.silabosemanal_set.filter(status=True, fechafinciosemana__gte=fecha_inicio_pm, fechainiciosemana__lte=fecha_fin_pm)
                            for sm in silabosemanal:
                                for det in sm.detallesilabosemanaltema_set.filter(status=True):
                                    listatemas.append([sm, sm.numsemana, det])
                    orden_listatemas = list(sorted(listatemas, key=lambda x: (x[1]), reverse=False))

                    claseactividad = ClaseActividad.objects.filter(detalledistributivo=detalledistributivo, detalledistributivo__distributivo__profesor=eProfesor, status=True).order_by('inicio', 'dia', 'turno__comienza')
                    inicio, fin = fecha_inicio_pm, fecha_fin_pm
                    if actividad := detalledistributivo.actividaddetalledistributivo_set.filter(vigente=True, status=True).first():
                        if actividad.hasta < fecha_fin_pm:
                            fin = actividad.hasta

                    dt, end, step = date(fecha_fin_pm.year, fecha_fin_pm.month, 1), fecha_fin_pm, timedelta(days=1)
                    _result, total_ejecutada = [], 0
                    while dt <= end:
                        if inicio <= dt <= fin:
                            exclude = 0
                            if not periodo.diasnolaborable_set.values('id').filter(status=True, fecha=dt, activo=True).exclude(motivo=exclude):
                                _result += [dt.strftime('%Y-%m-%d') for dclase in claseactividad.values_list('dia', 'turno_id') if dt.isocalendar()[2] == dclase[0]]
                        dt += step
                    eTotalhoras = _result.__len__()

                    for l in orden_listatemas:
                        silabosemanal = l[0]
                        numerosemana = l[1]
                        detallesilabosemanaltema = l[2]
                        tema = detallesilabosemanaltema.temaunidadresultadoprogramaanalitico
                        if not DetallePlanificacionMensualSalud.objects.values('id').filter(planificacionmensual=instancia, silabosemanal=silabosemanal, tema=tema, status=True).exists():

                            objetivo = detallesilabosemanaltema.objetivoaprendizaje
                            enfoque = silabosemanal.enfoque
                            listaevaluacion = silabosemanal.eval_componente()
                            evaluacion = ''
                            for e in listaevaluacion:
                                evaluacion += str(e.evaluacionaprendizaje.get_tipoevaluacion_display()) +':'+ str(e.evaluacionaprendizaje.descripcion) + str(e.numactividad) +';'

                            fecha_inicio = silabosemanal.fechainiciosemana
                            fecha_fin = silabosemanal.fechafinciosemana

                            fechas_en_semana = [fecha for fecha in _result if fecha_inicio <= datetime.strptime(fecha, '%Y-%m-%d').date() <= fecha_fin]
                            horas = fechas_en_semana.__len__()

                            if horas > 0:
                                fecha_inicio = datetime.strptime(fechas_en_semana[0], '%Y-%m-%d').date()
                                fecha_fin = datetime.strptime(fechas_en_semana[-1], '%Y-%m-%d').date()

                            detalle = DetallePlanificacionMensualSalud(planificacionmensual=instancia,
                                                                       fechainicio=fecha_inicio,
                                                                       fechafin=fecha_fin,
                                                                       silabosemanal=silabosemanal,
                                                                       tema=tema,
                                                                       numerosemana=numerosemana,
                                                                       descripciontema=tema.descripcion,
                                                                       objetivo=objetivo,
                                                                       enfoque=enfoque,
                                                                       evaluacion=evaluacion,
                                                                       horas=horas
                                                                       )
                            detalle.save(request)
                            log(f'Adicionó Detalle Planificación Mensual Salud {detalle}', request, 'add')

                            subtemasselec = silabosemanal.subtemas_silabosemanal(tema)
                            for st in subtemasselec:
                                subtema = DetalleTemaPlanificacionMensualSalud(detalleplanificacionmensual=detalle, subtema=st, descripcionsubtema=st.subtemaunidadresultadoprogramaanalitico.descripcion)
                                subtema.save(request)
                                log(f'Adicionó Detalle Tema Planificación Mensual Salud {subtema}', request, 'add')

                            subtemasadicionales = silabosemanal.subtemas_adicionales(detallesilabosemanaltema.id)
                            for sta in subtemasadicionales:
                                subtemaa = DetalleTemaPlanificacionMensualSalud(detalleplanificacionmensual=detalle, subtemaadicional=sta, descripcionsubtemaadicional=sta.objetivoaprendizaje)
                                subtemaa.save(request)
                                log(f'Adicionó Detalle Tema Adicional Planificación Mensual Salud {subtemaa}', request, 'add')

                    instancia.totalhoras = eTotalhoras
                    instancia.save(request)
                    log(f'Editó Planificación Mensual Salud {instancia}', request, 'edit')
                    return JsonResponse({'result': 'ok', 'mensaje': u'Guardado con éxito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        elif action == 'firmadocumento':
            try:
                tfirmas = json.loads(request.POST['txtFirmas'])
                if not tfirmas:
                    raise NameError("Debe seleccionar la ubicación de la firma")
                x = tfirmas[-1]
                posx, posy, numpaginafirma, datau = x["x"] + 50, x["y"] + 40, x["numPage"], None
                evidenciaactividad = EstadoEvidenciaSalud.objects.get(pk=int(encrypt(request.POST['id_objeto'])))
                certificado = request.FILES["firma"]
                passfirma = request.POST['palabraclave']
                documento_a_firmar = evidenciaactividad.archivorespaldo if evidenciaactividad.archivorespaldo else evidenciaactividad.planificacionmensual.archivo
                bytes_certificado = certificado.read()
                extension_certificado = os.path.splitext(certificado.name)[1][1:]

                try:
                    datau = JavaFirmaEc(archivo_a_firmar=documento_a_firmar, archivo_certificado=bytes_certificado,
                                        extension_certificado=extension_certificado, password_certificado=passfirma,
                                        page=numpaginafirma, reason=f"Legalizar evidencia", lx=posx,
                                        ly=posy).sign_and_get_content_bytes()
                except Exception as ex:
                    ...

                if not datau:
                    raise NameError(u'Problemas de conexión con la plataforma Firma Ec. Por favor asegúrese de estar ingresando la contraseña correcta e intentelo más tarde')

                documento_a_firmar = io.BytesIO()
                documento_a_firmar.write(datau)
                documento_a_firmar.seek(0)

                _name = generar_nombre('evidencia_', 'file.pdf')

                evidenciaactividad.archivorespaldo = evidenciaactividad.planificacionmensual.archivo if evidenciaactividad.planificacionmensual.archivo else None
                evidenciaactividad.planificacionmensual.archivo.save(_name, ContentFile(documento_a_firmar.read()))

                evidenciaactividad.estado = 2
                evidenciaactividad.persona = persona
                evidenciaactividad.fecha = hoytime
                evidenciaactividad.observacion = 'Documento firmado por Supervisor Tutor'
                evidenciaactividad.firma_tutor = True
                evidenciaactividad.save(request)

                detalle = DetalleEstadoEvidenciaSalud(evidencia_estado=evidenciaactividad, persona=persona, observacion='Documento firmado por Supervisor Tutor', fecha=hoytime, estado=2)
                detalle.save(request)

                log(u'Guardo archivo firmado: {}'.format(evidenciaactividad), request, "add")
                return JsonResponse({"result": False, "mensaje": "Guardado con exito", }, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar. %s" % ex.__str__()}, safe=False)

        # elif action == 'asistenciaestudiantepdf':
        #     try:
        #         data['urlbase'] = urlbase = get_variable('SITE_URL_SGA')
        #         results = []
        #         data['mes'] = mes = int(request.POST['mes'])
        #         data['observacion'] = observacion = request.POST['observacion']
        #         hoy = datetime.now().date()
        #         fecha_inicio = date(hoy.year, mes, 1)
        #         fecha_fin = date(hoy.year, mes, calendar.monthrange(hoy.year, mes)[1])
        #         abrwd = ['LU', 'MA', 'MI', 'JU', 'VI', 'SA', 'DO']
        #
        #         if not 'id' in request.POST and int(request.POST['id']) > 0:
        #             raise NameError('Problemas en la generación del informe. Intente nuevamente más tarde.')
        #
        #         data['estudiante'] = estudiantesupervisar = EstudianteSupervisarPracticaSalud.objects.get(pk=int(request.POST['id']))
        #
        #         # Obtener el nombre del Itinerario conforme al formato del documento
        #         if estudiantesupervisar.practicappp.itinerariomalla.malla.carrera.id in [3, 111]:
        #             aux = estudiantesupervisar.practicappp.itinerariomalla.nombre.split('-')
        #             nombreitinerario = aux[0].split('PROFESIONALES EN ')[1] + '- ' + aux[1].split('PROFESIONALES EN ')[1]
        #         elif estudiantesupervisar.practicappp.itinerariomalla.malla.carrera.id in [112]:
        #             nombreitinerario = estudiantesupervisar.practicappp.itinerariomalla.nombre.split('PROFESIONALES ')[1]
        #         else:
        #             nombreitinerario = estudiantesupervisar.practicappp.itinerariomalla.nombre
        #         data['nombreitinerario'] = nombreitinerario
        #         # cargos
        #         if responablesalud := estudiantesupervisar.practicappp.practicaspreprofesionalesinscripcionextensionsalud_set.filter(status=True).first():
        #             data['responablesalud'] = responablesalud
        #         data['tutor'] = tutor = estudiantesupervisar.practicappp.tutorunemi if estudiantesupervisar.practicappp.tutorunemi else estudiantesupervisar.practicappp.supervisor
        #         data['coordinadorppp'] = coordinadorppp = DistributivoPersona.objects.get(denominacionpuesto_id=169, estadopuesto_id=1)
        #
        #
        #         results = estudiantesupervisar.listado_registros_supervisar()
        #         data['itemshorario'] = itemshorario = results.order_by('turno').distinct('turno')
        #
        #         listadiasmes = []
        #         fecha_actual = fecha_inicio
        #         while fecha_actual <= fecha_fin:
        #             listadiasmes.append(fecha_actual)
        #             fecha_actual += timedelta(days=1)
        #
        #         abrdia = []
        #
        #         for r in listadiasmes:
        #             abrdia.append({'abr': abrwd[diaisoweekday(r) - 1], 'dia': r.day})
        #
        #         # for res in results:
        #         #     abrdia.append({'abr': abrwd[diaisoweekday(res.fecha) - 1], 'dia': res.fecha.day})
        #         data["abrdia"] =abrdia
        #         data['results'] = results
        #         data['hoy'] = str(datetime.now().date())
        #
        #         # INICIO GENERA INFORME
        #         qrname = f"informesemanal_{persona.usuario.username}_{informesemanal.pk}"
        #         rutafolder = f"planificacionsemanal/{str(ahora.year)}/{ahora.month:02d}/"
        #         folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'planificacionsemanal', str(ahora.year), f'{ahora.month:02d}', ''))
        #         os.makedirs(folder, exist_ok=True)
        #         genero, archivogenerado = html_to_pdfsave_evienciassalud('alu_practicaspro/formatos_salud/registroasistencia.html',
        #                                                                  {'pagesize': 'A4', 'data': data, }, qrname + '.pdf', rutafolder)
        #         # FIN GENERA INFORME
        #
        #         estudiantesupervisar.fechainicio = fecha_inicio_ps
        #         estudiantesupervisar.fechafin = fecha_fin_ps
        #         estudiantesupervisar.archivo = rutafolder + qrname + '.pdf'
        #         estudiantesupervisar.observacion = observacion.strip()
        #         informesemanal.save(request)
        #         log(u'Informe Planificación Semanal Salud: %s' % (informesemanal), request, etiqueta2)
        #         messages.success(request, 'Proceso ejecutado con éxito.')
        #
        #
        #
        #         # return conviert_html_to_pdf(
        #         #     'alu_practicaspro/formatos_salud/registroasistencia.html',
        #         #     {
        #         #         'pagesize': 'A4',
        #         #         'data': data,
        #         #     },
        #         # )
        #     except Exception as ex:
        #         pass

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'view_estudiantes':
                try:
                    if 'id' in request.GET:
                        data['id'] = id = request.GET['id']

                        profesor = Profesor.objects.get(pk=id)
                        listado = PracticasPreprofesionalesInscripcion.objects.filter(status=True, supervisor=profesor, culminada=False, estadosolicitud__in=[1, 2], preinscripcion__preinscripcion__periodo=periodo).order_by('inscripcion__persona__apellido1')

                        data['profesor'] = profesor
                        data['cantidadestudiantes'] = listado.values_list('inscripcion_id').distinct().count()
                        data['cantidadinscripciones'] = listado.count()
                        data['listado'] = listado
                        template = get_template("pro_actividadestutorpracticas/modal/viewregistros.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'viewpersonaubicacion':
                try:
                    idprofesor = int(request.GET['docente'])
                    idcarrera = int(request.GET['carrera']) if 'carrera' in request.GET and request.GET['carrera'] != '' else 0
                    data['check_fecha'] = check_fecha = request.GET['check_fecha'] == 'true' or request.GET['check_fecha'] == True
                    data['docente'] = eProfesor = Profesor.objects.get(pk=idprofesor)
                    # bandera_subquery = False
                    if check_fecha:
                        data['fecha'] = fecha = datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date()
                        registrostutor = DetalleSupervisarPracticaSalud.objects.filter(fecha=fecha, estudiantesupervisar__supervisarpractica__supervisor=eProfesor, status=True)
                        if idcarrera > 0: registrostutor = registrostutor.filter(estudiantesupervisar__practicappp__inscripcion__carrera_id=idcarrera)
                        listadopracticas = registrostutor.values_list('estudiantesupervisar__practicappp_id', flat=True).order_by('estudiantesupervisar__practicappp__asignacionempresapractica_id').distinct('estudiantesupervisar__practicappp__inscripcion_id', 'estudiantesupervisar__practicappp__asignacionempresapractica_id')
                        subquery_fecha = DetalleSupervisarPracticaSalud.objects.filter(estudiantesupervisar__practicappp__asignacionempresapractica_id=OuterRef('asignacionempresapractica__id'),
                                                                                           estudiantesupervisar__practicappp_id=OuterRef('id'), fecha=fecha, status=True).values('fecha', 'hora').order_by('-fecha')[:1]
                    else:
                        filtro_ = Q(status=True)
                        if idcarrera > 0: filtro_ &= Q(inscripcion__carrera_id=idcarrera)
                        listadopracticas = PracticasPreprofesionalesInscripcion.objects.filter(filtro_).filter(supervisor=eProfesor, culminada=False, estadosolicitud__in=[1, 2], preinscripcion__preinscripcion__periodo=periodo, asignacionempresapractica__isnull=False).order_by('asignacionempresapractica_id').values_list('id', flat=True).distinct('inscripcion_id', 'asignacionempresapractica_id')

                    listado = PracticasPreprofesionalesInscripcion.objects.filter(pk__in=listadopracticas)
                    ubicacionempresa = UbicacionEmpresaPractica.objects.filter(status=True, asignacionempresapractica__id__in=[listado.values_list('asignacionempresapractica_id', flat=True)])
                    listaciudades = listado.values('asignacionempresapractica__canton__nombre', 'asignacionempresapractica__canton__provincia__nombre', 'asignacionempresapractica__nombre','asignacionempresapractica__ubicacionempresapractica__latitud', 'asignacionempresapractica__ubicacionempresapractica__longitud').annotate(total=Count(Coalesce('asignacionempresapractica', Value(0)))).order_by('-total')
                    if check_fecha:
                        listaretorno = json.dumps(list(listado.values('id', 'asignacionempresapractica__nombre', 'inscripcion__persona__nombres', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__carrera__nombre', 'asignacionempresapractica__ubicacionempresapractica__latitud', 'asignacionempresapractica__ubicacionempresapractica__longitud', 'asignacionempresapractica__canton__nombre', 'asignacionempresapractica__canton__provincia__nombre', 'asignacionempresapractica__canton__provincia__pais__nombre').annotate(
                                                                    fecha=Cast(TruncDate(Subquery(subquery_fecha.values('fecha'))), output_field=TextField()),
                                                                    hora=Cast(TruncTime(Subquery(subquery_fecha.values('hora'))), output_field=TextField()))))
                    else:
                        listaretorno = json.dumps(list(listado.values('id', 'asignacionempresapractica__nombre', 'inscripcion__persona__nombres', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__carrera__nombre', 'asignacionempresapractica__ubicacionempresapractica__latitud', 'asignacionempresapractica__ubicacionempresapractica__longitud', 'asignacionempresapractica__canton__nombre', 'asignacionempresapractica__canton__provincia__nombre', 'asignacionempresapractica__canton__provincia__pais__nombre')))
                    data['listadociudades'] = listaciudades
                    data['totalestudiantes'] = listado.count()
                    data['totalempresasmapa'] = ubicacionempresa.count()
                    template = get_template("pro_actividadestutorpracticas/datos_resultado.html")
                    return JsonResponse({"result": "ok", "cantidad": len(ubicacionempresa), "listado": listaretorno, 'data': template.render(data)})
                except Exception as ex:
                    data['msg_error'] = ex.__str__()
                    return JsonResponse({"result": "bad", "mensaje": str(ex)})

            elif action == 'ubicaciondocente':
                try:
                    data['hoy'] = hoy = datetime.now().date()
                    data['title'] = u'Ubicación de docentes'
                    data['action'] = action
                    filters_ = Q(status=True, inscripcion__carrera__coordinacion__id__in=[1], estadosolicitud__in=[1, 2], culminada=False, preinscripcion__preinscripcion__periodo=periodo)
                    listado = PracticasPreprofesionalesInscripcion.objects.filter(filters_).exclude(estadosolicitud=3)
                    listadodocente = listado.values_list('supervisor', flat=True).order_by('supervisor').distinct()
                    listadocarrera = listado.values_list('inscripcion__carrera', flat=True).order_by('inscripcion__carrera').distinct()
                    listadoregistros = Profesor.objects.filter(pk__in=listadodocente)
                    data['listadoregistros'] = listadoregistros
                    data['listadocarreras'] = Carrera.objects.filter(pk__in=listadocarrera)
                    request.session['viewactivo'] = 2
                    return render(request, "pro_actividadestutorpracticas/mapadocente.html", data)
                except Exception as ex:
                    data['msg_error'] = ex.__str__()
                    return render(request, "adm_asistenciaexamensede/error.html", data)

            elif action == 'reporteexcelubicaciones':
                try:
                    idprofesor = int(request.GET['docente'])
                    idcarrera = int(request.GET['carrera']) if 'carrera' in request.GET and request.GET['carrera'] != '' else 0
                    check_fecha = request.GET['check_fecha'] == 'true' or request.GET['check_fecha'] == True
                    profesor = Profesor.objects.get(pk=idprofesor)

                    if check_fecha:
                        data['fecha'] = fecha = datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date()
                        registrostutor = DetalleSupervisarPracticaSalud.objects.filter(fecha=fecha, estudiantesupervisar__supervisarpractica__supervisor=profesor, status=True)
                        if idcarrera > 0: registrostutor = registrostutor.filter(estudiantesupervisar__practicappp__inscripcion__carrera_id=idcarrera)
                        listadopracticas = registrostutor.values_list('estudiantesupervisar__practicappp_id', flat=True).order_by('estudiantesupervisar__practicappp__asignacionempresapractica_id').distinct('estudiantesupervisar__practicappp__asignacionempresapractica_id')
                    else:
                        filtro_ = Q(status=True)
                        if idcarrera > 0: filtro_ &= Q(inscripcion__carrera_id=idcarrera)
                        listadopracticas = PracticasPreprofesionalesInscripcion.objects.filter(filtro_).filter(supervisor=profesor, culminada=False, estadosolicitud__in=[1, 2], preinscripcion__preinscripcion__periodo=periodo, asignacionempresapractica__isnull=False).order_by('asignacionempresapractica_id').values_list('id', flat=True).distinct('asignacionempresapractica_id')

                    queryresultado = PracticasPreprofesionalesInscripcion.objects.filter(pk__in=listadopracticas)

                    # INICIO EXCEL
                    __author__ = 'UNIVERSIDAD ESTATAL DE MILAGRO'
                    title = easyxf('font: name Calibri, color-index black, bold on , height 350; alignment: horiz centre')
                    fuentecabecera = easyxf(
                        'font: name Calibri, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentetexto = easyxf(
                        'font: name Calibri, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    borders = Borders()
                    borders.left = Borders.THIN
                    borders.right = Borders.THIN
                    borders.top = Borders.THIN
                    borders.bottom = Borders.THIN
                    align = Alignment()
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style.borders = borders
                    font_style.alignment = align
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    font_style2.borders = borders
                    font_style2.alignment = align
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('LISTADO ESTUDIANTES')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=ubicacion_estudiantes_prácticas' + random.randint(1, 10000).__str__() + '.xls'
                    ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 9, 'ESTUDIANTES PRÁCTICAS PRE PROFESIONALES', title)
                    ws.write_merge(2, 2, 0, 9, 'REPORTE DE UBICACIÓN {}'.format(str(datetime.now().date())), fuentenormal)
                    ws.write_merge(3, 3, 0, 9, 'DOCENTE: {}'.format(str(profesor.persona)), fuentetexto)
                    columns = [
                        (u"DOCUMENTO", 8000),
                        (u"APELLIDOS", 8000),
                        (u"NOMBRES", 8000),
                        (u"CARRERA", 8000),
                        (u"ITINERARIO", 8000),
                        (u"EMPRESA", 11000),
                        (u"CANTON", 8000),
                        (u"PROVINCIA", 8000),
                        (u"PAIS", 8000),
                        (u"ESTADO", 8000),
                    ]
                    if check_fecha:
                        columns.append(('FECHA', 8000))
                        columns.append(('HORA', 8000))
                    row_num = 4
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 5
                    count = 1
                    for i in queryresultado:
                        ws.write_merge(row_num, row_num, 0, 0, i.inscripcion.persona.cedula if i.inscripcion.persona.cedula else i.inscripcion.persona.pasaporte, font_style2)
                        ws.write_merge(row_num, row_num, 1, 1, "{} {}".format(i.inscripcion.persona.apellido1, i.inscripcion.persona.apellido2), font_style2)
                        ws.write_merge(row_num, row_num, 2, 2, i.inscripcion.persona.nombres, font_style2)
                        ws.write_merge(row_num, row_num, 3, 3, str(i.inscripcion.carrera), font_style2)
                        ws.write_merge(row_num, row_num, 4, 4, str(i.itinerariomalla.nombre), font_style2)
                        ws.write_merge(row_num, row_num, 5, 5, i.asignacionempresapractica.nombre if i.asignacionempresapractica else '', font_style2)
                        ws.write_merge(row_num, row_num, 6, 6, i.asignacionempresapractica.canton.nombre if i.asignacionempresapractica and i.asignacionempresapractica.canton else '', font_style2)
                        ws.write_merge(row_num, row_num, 7, 7, i.asignacionempresapractica.canton.provincia.nombre if i.asignacionempresapractica and i.asignacionempresapractica.canton and i.asignacionempresapractica.canton.provincia else '', font_style2)
                        ws.write_merge(row_num, row_num, 8, 8, i.asignacionempresapractica.canton.provincia.pais.nombre if i.asignacionempresapractica and i.asignacionempresapractica.canton and i.asignacionempresapractica.canton.provincia and i.asignacionempresapractica.canton.provincia.pais else '', font_style2)
                        ws.write_merge(row_num, row_num, 9, 9, i.get_estadosolicitud_display(), font_style2)
                        if check_fecha:
                            ws.write_merge(row_num, row_num, 9, 9, i.get_estadosolicitud_display(), font_style2)
                            ws.write_merge(row_num, row_num, 9, 9, i.get_estadosolicitud_display(), font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": str(ex)})

            elif action == 'listadodocentes':
                try:
                    idcarrera = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] != '' else 0
                    filtro_ = Q(status=True)
                    if idcarrera > 0:
                        filtro_ &= Q(inscripcion__carrera_id=idcarrera)
                    filtro = Q(inscripcion__carrera__coordinacion__id__in=[1], estadosolicitud__in=[1, 2], culminada=False, preinscripcion__preinscripcion__periodo=periodo)
                    listado = PracticasPreprofesionalesInscripcion.objects.filter(filtro_).filter(filtro).exclude(estadosolicitud=3)
                    listadodocente = listado.filter(filtro_).values_list('supervisor', flat=True).order_by('supervisor').distinct()
                    qsbase = Profesor.objects.filter(pk__in=listadodocente)
                    resp = [{'id': cr.pk, 'text': cr.persona.__str__()} for cr in qsbase.order_by('persona__apellido1')]
                    return HttpResponse(json.dumps({'state': True, 'result': resp}))
                except Exception as ex:
                    pass

            elif action == 'turnossalud':
                try:
                    data['title'] = 'Gestión de Turnos'
                    data['tab'] = int(request.GET.get('tab', 0))
                    data['listadoturno'] = listadoturno = TurnoPractica.objects.filter(status=True)
                    data['listadoestudiante'] = listadoestudiante = TurnoEstudiantePractica.objects.filter(status=True)
                    data['listadodocente'] = listadodocente = TurnoEstudiantePractica.objects.filter(status=True)
                    request.session['viewactivo'] = 3
                    return render(request, 'pro_actividadestutorpracticas/viewturno.html', data)
                except Exception as ex:
                    pass

            elif action == 'addturno':
                try:
                    data['action'] = request.GET['action']
                    data['title'] = u'Adicionar turno'
                    data['tab'] = request.GET['tab']
                    form = TurnoPracticaForm()
                    form.fields['turno'].initial = TurnoPractica.objects.values('id').filter(status=True).count() + 1
                    data['form'] = form
                    template = get_template("pro_actividadestutorpracticas/modal/formturno.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'editturno':
                try:
                    data['title'] = u'Editar turno'
                    data['action'] = request.GET['action']
                    data['tab'] = request.GET['tab']
                    if id := int(request.GET.get('id', 0)): data['id'] = id
                    if id > 0:
                        data['registro'] = registro = TurnoPractica.objects.get(pk=id)
                        f = TurnoPracticaForm(initial=model_to_dict(registro))
                        data['form'] = f
                        template = get_template("pro_actividadestutorpracticas/modal/formturno.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": u"Problemas al obtener los datos. Intente nuevamente más tarde."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'addturnoestudiante':
                try:
                    data['action'] = request.GET['action']
                    data['title'] = u'Adicionar turno estudiante'
                    data['tab'] = request.GET['tab']
                    form = TurnoEstudianteForm()
                    data['form'] = form
                    template = get_template("pro_actividadestutorpracticas/modal/formturno.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'editturnoestudiante':
                try:
                    data['title'] = u'Editar turno estudiante'
                    data['action'] = request.GET['action']
                    data['tab'] = request.GET['tab']
                    if id := int(request.GET.get('id', 0)): data['id'] = id
                    if id > 0:
                        data['registro'] = registro = TurnoEstudiantePractica.objects.get(pk=id)
                        f = TurnoEstudianteForm(initial=model_to_dict(registro))
                        data['form'] = f
                        template = get_template("pro_actividadestutorpracticas/modal/formturno.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": u"Problemas al obtener los datos. Intente nuevamente más tarde."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'viewsupervisiontutor':
                try:
                    data['action'] = action

                    data['title'] = 'Supervisión de prácticas pre profesionales'
                    data['detalledistributivo'] = detalledistributivo = DetalleDistributivo.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    data['supervisor'] = supervisor = detalledistributivo.distributivo.profesor
                    ePeriodo = periodo if periodo else detalledistributivo.distributivo.periodo

                    filtros, s, e, c, i, url_vars = Q(status=True, supervisarpractica__supervisor=supervisor, supervisarpractica__periodo=ePeriodo), request.GET.get('s', ''), request.GET.get('e', '0'), request.GET.get('c', '0'), request.GET.get('i', '0'), ''
                    filtrosbase = filtros
                    if s:
                        data['s'] = f"{s}"
                        url_vars += f"&s={s}"
                        ss = s.split(' ')
                        if len(ss) == 1:
                            filtros = filtros & (Q(practicappp__inscripcion__persona__cedula__icontains=ss[0]) | Q(practicappp__inscripcion__persona__pasaporte__icontains=ss[0]) |
                                                 Q(practicappp__inscripcion__persona__ruc__icontains=ss[0]) | Q(practicappp__inscripcion__persona__nombres__icontains=ss[0]) |
                                                 Q(practicappp__inscripcion__persona__apellido1__icontains=ss[0]) | Q(practicappp__inscripcion__persona__apellido2__icontains=ss[0]) |
                                                 Q(supervisarpractica__empresapractica__nombre__icontains=ss[0]))
                        elif len(ss) == 2:
                            filtros = filtros & ((Q(practicappp__inscripcion__persona__nombres__icontains=ss[0]) & Q(practicappp__inscripcion__persona__nombres__icontains=ss[1])) |
                                                 (Q(practicappp__inscripcion__persona__apellido1__icontains=ss[0]) & Q(practicappp__inscripcion__persona__apellido2__icontains=ss[1])) |
                                                 (Q(supervisarpractica__empresapractica__nombre__icontains=ss[0]) & Q(supervisarpractica__empresapractica__nombre__icontains=ss[1])))
                        else:
                            filtros = filtros & (Q(practicappp__inscripcion__persona__cedula__icontains=s) | Q(practicappp__inscripcion__persona__pasaporte__icontains=s) |
                                                 Q(practicappp__inscripcion__persona__ruc__icontains=s) | Q(practicappp__inscripcion__persona__nombres__icontains=s) |
                                                 Q(practicappp__inscripcion__persona__apellido1__icontains=s) | Q(practicappp__inscripcion__persona__apellido2__icontains=s) |
                                                 Q(supervisarpractica__empresapractica__nombre__icontains=s))
                    if int(e):
                        filtros = filtros & (Q(supervisarpractica__empresapractica_id=e))
                        data['e'] = f"{e}"
                        url_vars += f"&e={e}"

                    if int(c):
                        filtros = filtros & (Q(practicappp__inscripcion__carrera_id=c))
                        data['c'] = f"{c}"
                        url_vars += f"&c={c}"

                    if int(i):
                        filtros = filtros & (Q(practicappp__itinerariomalla_id=i))
                        data['i'] = f"{i}"
                        url_vars += f"&i={i}"

                    eListado = EstudianteSupervisarPracticaSalud.objects.filter(filtrosbase)
                    data['empresas'] = eListado.values_list('supervisarpractica__empresapractica_id', 'supervisarpractica__empresapractica__nombre').order_by('supervisarpractica__empresapractica_id').distinct('supervisarpractica__empresapractica_id')
                    data['carreras'] = eListado.values_list('practicappp__inscripcion__carrera_id', 'practicappp__inscripcion__carrera__nombre').order_by('practicappp__inscripcion__carrera_id').distinct('practicappp__inscripcion__carrera_id')
                    if int(c): eListado = eListado.filter(practicappp__inscripcion__carrera_id=int(c))
                    data['itinerarios'] = eListado.values_list('practicappp__itinerariomalla_id', 'practicappp__itinerariomalla__nombre').order_by('practicappp__itinerariomalla_id').distinct('practicappp__itinerariomalla_id')

                    eListado = eListado.filter(filtros)

                    # if int(request.GET.get('genera', 0)) == 1:
                    #     data['urlbase'] = urlbase = get_variable('SITE_URL_SGA')
                    #     return conviert_html_to_pdf(
                    #         'alu_practicaspro/formatos_salud/tutor/planificacionmensual.html',
                    #         {
                    #             'pagesize': 'A4',
                    #             'data': data,
                    #         },
                    #     )

                    paging = MiPaginador(eListado.order_by('supervisarpractica__empresapractica__nombre', 'practicappp__inscripcion__persona__apellido1'), 15)
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
                    data['listado'] = page.object_list
                    data['tableIds'] = page.object_list.values_list('id', flat=True)
                    data['url_vars'] = url_vars
                    return render(request, 'pro_actividadestutorpracticas/viewsupervision.html', data)
                except Exception as ex:
                    ex_err = f"Error al obtener los datos. {ex}. Intente nuevamente más tarde."
                    return HttpResponseRedirect(f'/pro_cronograma?action=listasupervision&info={ex_err}')

            elif action == 'asistenciaestudiantepdf':
                try:
                    data['urlbase'] = urlbase = get_variable('SITE_URL_SGA')
                    results = []

                    data['detalledistributivo'] = detalledistributivo = DetalleDistributivo.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    data['supervisor'] = supervisor = detalledistributivo.distributivo.profesor
                    ePeriodo = periodo if periodo else detalledistributivo.distributivo.periodo
                    iditinerario = int(request.GET['iditinerario'])
                    idempresa = int(request.GET['idempresa'])
                    filtros = Q(status=True, estudiantesupervisar__supervisarpractica__supervisor=supervisor, estudiantesupervisar__supervisarpractica__periodo=ePeriodo, estudiantesupervisar__practicappp__itinerariomalla_id=iditinerario, estudiantesupervisar__practicappp__asignacionempresapractica_id=idempresa)

                    data['mes'] = mes = int(request.GET['mes'])
                    data['observacion'] = observacion = request.GET['observacion']
                    hoy = datetime.now().date()
                    data['fechainicio'] = fecha_inicio = date(hoy.year, mes, 1)
                    data['fechafin'] = fecha_fin = date(hoy.year, mes, calendar.monthrange(hoy.year, mes)[1])
                    abrwd = ['LU', 'MA', 'MI', 'JU', 'VI', 'SA', 'DO']
                    abrdia = []
                    listadiasmes = []
                    fecha_actual = fecha_inicio
                    while fecha_actual <= fecha_fin:
                        listadiasmes.append(fecha_actual)
                        abrdia.append({'abr': abrwd[diaisoweekday(fecha_actual) - 1], 'dia': fecha_actual.day})
                        fecha_actual += timedelta(days=1)
                    # for r in listadiasmes:
                    #     abrdia.append({'abr': abrwd[diaisoweekday(r) - 1], 'dia': r.day})
                    data["abrdia"] = abrdia

                    data['registros'] = registros = DetalleSupervisarPracticaSalud.objects.filter(filtros).filter(fecha__gte=fecha_inicio, fecha__lte=fecha_fin)
                    data['estudiante'] = detalleestudiantes = registros.first()
                    data['itinerario'] = itinerario = detalleestudiantes.estudiantesupervisar.practicappp.itinerariomalla if detalleestudiantes else ''
                    data['empresa'] = empresa = detalleestudiantes.estudiantesupervisar.practicappp.asignacionempresapractica.nombre if detalleestudiantes else ''

                    # Obtener el nombre del Itinerario conforme al formato del documento
                    if itinerario.malla.carrera.id in [3, 111]:
                        aux = itinerario.nombre.split('-')
                        nombreitinerario = aux[0].split('PROFESIONALES EN ')[1] + '- ' + aux[1].split('PROFESIONALES EN ')[1]
                    elif itinerario.malla.carrera.id in [112]:
                        nombreitinerario = itinerario.nombre.split('PROFESIONALES ')[1]
                    else:
                        nombreitinerario = itinerario.nombre
                    data['nombreitinerario'] = nombreitinerario

                    # cargos
                    if responablesalud := detalleestudiantes.estudiantesupervisar.practicappp.practicaspreprofesionalesinscripcionextensionsalud_set.filter(status=True).first():
                        data['responablesalud'] = responablesalud
                    data['tutor'] = tutor = detalleestudiantes.estudiantesupervisar.practicappp.tutorunemi if detalleestudiantes.estudiantesupervisar.practicappp.tutorunemi else detalleestudiantes.estudiantesupervisar.practicappp.supervisor
                    data['coordinadorppp'] = coordinadorppp = DistributivoPersona.objects.get(denominacionpuesto_id=169, estadopuesto_id=1)

                    results = registros
                    data['itemshorario'] = turnosestudiante =TurnoEstudiantePractica.objects.filter(status=True, carrera=itinerario.malla.carrera, activo=True)
                    libre = turnosestudiante.filter(nombre__icontains='libre').first()
                    academico = turnosestudiante.filter(Q(nombre__icontains='academico') | Q(nombre__icontains='académico')).first()
                    registros_por_estudiante = {}

                    for rd in registros:
                        estudiante = rd.estudiantesupervisar
                        if estudiante not in registros_por_estudiante:
                            # Inicializa la lista para cada estudiante con listas vacías para cada día del mes
                            diaacademico = estudiante.practicappp.practicaspreprofesionalesinscripcionextensionsalud_set.values_list('dia', flat=True).filter(status=True).first()
                            registros_por_estudiante[estudiante] = [[libre] if libre and abrwd[diaisoweekday(_) - 1] in ['SA', 'DO'] else [academico] if academico and diaacademico and abrwd[diaisoweekday(_) - 1] == abrwd[diaacademico - 1] else [] for _ in listadiasmes]
                        # Encuentra el índice del día correspondiente en listadiasmes
                        if rd.fecha.date() in listadiasmes:
                            index = listadiasmes.index(rd.fecha.date())
                            registros_por_estudiante[estudiante][index] = []
                            registros_por_estudiante[estudiante][index].append(rd.turno)

                    data['eListado'] = registros_por_estudiante
                    data['hoy'] = str(datetime.now().date())

                    return conviert_html_to_pdf(
                        'alu_practicaspro/formatos_salud/tutor/registroasistenciatutor.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        },
                    )
                except Exception as ex:
                    pass


            elif action == 'editdetestsupervisar':
                try:
                    data['title'] = u'Editar registro supervisión'
                    data['action'] = request.GET['action']
                    if id := int(request.GET.get('id', 0)): data['id'] = id
                    if id > 0:
                        data['registro'] = registro = DetalleSupervisarPracticaSalud.objects.get(pk=id)
                        f = RegisitroSupervisarPracticaForm(initial={'observacion': registro.observacion})
                        data['form'] = f
                        template = get_template("pro_actividadestutorpracticas/modal/formsupervisar.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": u"Problemas al obtener los datos. Intente nuevamente más tarde."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos. Intente nuevamente más tarde."})

            elif action == 'visitasupervisorsalud':

                try:
                    data['title'] = u'Registro de supervisión y control de profesor'
                    data['detalledistributivo'] = detalledistributivo = DetalleDistributivo.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    data['supervisor'] = supervisor = detalledistributivo.distributivo.profesor
                    filters_coordinacion = Q(status=True, supervisor=supervisor, inscripcion__carrera__coordinacion__id__in=[1], preinscripcion__estado__in=[1, 2], culminada=False, supervisor__isnull=False, preinscripcion__preinscripcion__periodo=periodo)  # Salud
                    listado = PracticasPreprofesionalesInscripcion.objects.filter(filters_coordinacion).exclude(estadosolicitud=3)

                    eItinerarios = listado.values_list('itinerariomalla_id', 'itinerariomalla__nombre').order_by('itinerariomalla').distinct()
                    data['listadoitinerarios'] = listadoitinerarios = [[i[0], i[1]] for i in eItinerarios]

                    return render(request, 'pro_actividadestutorpracticas/supervisardocentesalud.html', data)
                except Exception as ex:
                    pass

            elif action == 'listadodatos':
                try:
                    lista = []
                    supervisor = int(request.GET['idsupervisor'])
                    filters_ = Q(status=True, supervisor_id=supervisor, inscripcion__carrera__coordinacion__id__in=[1], preinscripcion__estado__in=[1, 2], culminada=False, supervisor__isnull=False, preinscripcion__preinscripcion__periodo=periodo)  # Salud
                    listado = PracticasPreprofesionalesInscripcion.objects.filter(filters_).exclude(estadosolicitud=3)

                    if 'bandera' in request.GET and int(request.GET['bandera']) == 1 and 'iditinerario' in request.GET:
                        iditinerario = int(request.GET['iditinerario'])
                        eEmpresas = listado.filter(itinerariomalla_id=iditinerario).values_list('asignacionempresapractica_id','asignacionempresapractica__nombre').order_by('asignacionempresapractica').distinct()
                        if eEmpresas: lista = [[d[0], d[1]] for d in eEmpresas]
                        return JsonResponse({'result': True, 'lista': lista})

                    elif 'bandera' in request.GET and int(request.GET['bandera']) == 2 and 'idempresa' in request.GET and 'iditinerario' in request.GET:
                        iditinerario = int(request.GET['iditinerario'])
                        idempresa = int(request.GET['idempresa'])
                        eEstudiantes = listado.filter(itinerariomalla_id=iditinerario, asignacionempresapractica_id=idempresa).order_by('inscripcion').distinct()
                        if eEstudiantes: data['lista'] = lista = eEstudiantes
                        template = get_template("pro_actividadestutorpracticas/datos_resultados_estudiantes.html")
                        return JsonResponse({"result": True, 'cantidad': eEstudiantes.count(), 'data': template.render(data)})

                    return JsonResponse({'result': False, 'mensaje': u"Error al obtener los datos."})
                except Exception as e:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'listadomeses':
                try:
                    lista = []
                    id = int(request.GET['id'])
                    registro = EstudianteSupervisarPracticaSalud.objects.get(pk=id)
                    meses = registro.detallesupervisarpracticasalud_set.filter(status=True).values_list('fecha__month', flat=True).distinct()
                    # periodopp = registro.practicappp.periodoppp
                    # fecha_inicio = periodopp.fechainicio
                    # fecha_fin = periodopp.fechafin
                    # meses = []
                    # fecha_actual = fecha_inicio.replace(day=1)
                    # while fecha_actual <= fecha_fin:
                    #     meses.append(fecha_actual.month)
                    #     fecha_actual += relativedelta(months=1)
                    listadomeses = sorted(meses)
                    if listadomeses: lista = [MESES_CHOICES[m - 1] for m in listadomeses]
                    return JsonResponse({'result': True, 'lista': lista})
                except Exception as e:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'listadomesestutor':
                try:
                    lista = []
                    id = int(request.GET['id'])
                    detalledistributivo = DetalleDistributivo.objects.get(pk=id, status=True)
                    supervisor = detalledistributivo.distributivo.profesor
                    ePeriodo = periodo if periodo else detalledistributivo.distributivo.periodo
                    filtros = Q(status=True, supervisarpractica__supervisor=supervisor, supervisarpractica__periodo=ePeriodo)
                    registros = EstudianteSupervisarPracticaSalud.objects.values_list('id', flat=True).filter(filtros)
                    meses = DetalleSupervisarPracticaSalud.objects.filter(estudiantesupervisar_id__in=registros, status=True).values_list('fecha__month', flat=True).distinct()
                    listadomeses = sorted(meses)
                    if listadomeses: lista = [MESES_CHOICES[m - 1] for m in listadomeses]
                    return JsonResponse({'result': True, 'lista': lista})
                except Exception as e:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'listadodatoshorario':
                try:
                    lista = []
                    id = int(request.GET['iddistributivo'])
                    mes = int(request.GET['mes'])
                    if not mes or not mes > 0:
                        raise NameError('Seleccione un mes, por favor')
                    detalledistributivo = DetalleDistributivo.objects.get(pk=id)
                    supervisor = detalledistributivo.distributivo.profesor
                    ePeriodo = periodo if periodo else detalledistributivo.distributivo.periodo
                    if 'iditinerario' in request.GET and int(request.GET['iditinerario']) > 0:
                        filtros = Q(status=True, supervisarpractica__supervisor=supervisor, supervisarpractica__periodo=ePeriodo, practicappp__itinerariomalla_id=int(request.GET['iditinerario']))
                        registros = EstudianteSupervisarPracticaSalud.objects.values_list('id', flat=True).filter(filtros)
                        eEmpresas = DetalleSupervisarPracticaSalud.objects.filter(estudiantesupervisar_id__in=registros, fecha__month=mes, status=True).values_list('estudiantesupervisar__supervisarpractica__empresapractica_id', 'estudiantesupervisar__supervisarpractica__empresapractica__nombre').order_by('estudiantesupervisar__supervisarpractica__empresapractica__nombre').distinct()
                        if eEmpresas: lista = [[d[0], d[1]] for d in eEmpresas]
                        return JsonResponse({'result': True, 'lista': lista})
                    return JsonResponse({'result': False, 'mensaje': u"Seleccione los campos correctamente"})
                except Exception as e:
                    return JsonResponse({"result": False, "mensaje": f"Error al obtener los datos. {e}"})

            elif action == 'admcalendariosalud':
                try:
                    data['title'] = u'Supervisión y control de profesor'
                    numero_dias_antes_habilitado = 5
                    hoy = datetime.now().date()
                    ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
                    efecha = date(hoy.year, hoy.month, ultimo_dia)
                    numero_dias_extendido = 5
                    while numero_dias_extendido > 0:
                        efecha += timedelta(days=1)
                        if efecha.weekday() < 5: numero_dias_extendido -= 1

                    while numero_dias_antes_habilitado > 0:
                        hoy -= timedelta(days=1)
                        if hoy.weekday() < 5: numero_dias_antes_habilitado -= 1

                    fecha = datetime.now().date()
                    panio = fecha.year
                    pmes = fecha.month
                    if 'mover' in request.GET:
                        mover = request.GET['mover']

                        if mover == 'anterior':
                            mes = int(request.GET['mes'])
                            anio = int(request.GET['anio'])
                            pmes = mes - 1
                            if pmes == 0:
                                pmes = 12
                                panio = anio - 1
                            else:
                                panio = anio

                        elif mover == 'proximo':
                            mes = int(request.GET['mes'])
                            anio = int(request.GET['anio'])
                            pmes = mes + 1
                            if pmes == 13:
                                pmes = 1
                                panio = anio + 1
                            else:
                                panio = anio

                    # id = int(encrypt(request.GET['id']))
                    s_anio = panio
                    s_mes = pmes
                    s_dia = 1
                    data['mes'] = MESES_CHOICES[s_mes - 1]
                    data['ws'] = [0, 7, 14, 21, 28, 35]
                    lista = {}
                    listahorarios = []
                    for i in range(1, 43, 1):
                        dia = {i: 'no'}
                        lista.update(dia)
                    comienzo = False
                    fin = False
                    for i in lista.items():
                        try:
                            fecha = date(s_anio, s_mes, s_dia)
                            if fecha.isoweekday() == i[0] and fin is False and comienzo is False:
                                comienzo = True
                        except Exception as ex:
                            pass
                        if comienzo:
                            try:
                                fecha = date(s_anio, s_mes, s_dia)
                            except Exception as ex:
                                fin = True
                        if comienzo and fin is False:
                            dia = {i[0]: s_dia}
                            lista.update(dia)
                            listhorario = []
                            sinhorario = True
                            puedereservar = False
                            numerodia = fecha.weekday() + 1
                            if fecha >= hoy:
                                turnos = 0
                                listturnos = []
                                turnossalud = TurnoPractica.objects.filter(status=True)

                                if len(list(turnossalud)) > 0 and fecha <= efecha:
                                    puedereservar = True

                                diccionario = {'dia': s_dia, 'turnos': turnos, 'listahorario': list(turnossalud), 'sinhorario': sinhorario, 'fecha': fecha, 'puedereservar': puedereservar}
                                listahorarios.append(diccionario)
                            s_dia += 1

                    data['year'] = panio
                    data['dias_mes'] = lista
                    data['dwnm'] = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
                    data['dwn'] = [1, 2, 3, 4, 5, 6, 7]
                    data['daymonth'] = 1
                    data['s_anio'] = s_anio
                    data['s_mes'] = s_mes
                    data['lista'] = lista
                    data['hoy'] = hoy
                    data['hoy_dia'] = hoy.day
                    data['hoy_mes'] = hoy.month
                    data['listahorarios'] = listahorarios
                    data['fechaactual'] = date(hoy.year, hoy.month, ultimo_dia)
                    data['fechacalendario'] = date(s_anio, s_mes, s_dia - 1)
                    template = get_template("pro_actividadestutorpracticas/viewcalendariosalud.html")
                    return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": 'bad', 'mensaje': 'Error'.format(ex)})

            elif action == 'admaddvisitasupervisor':
                try:
                    data['iddistributivo'] = iddistributivo = request.GET['iddistributivo']
                    detalledistributivo = DetalleDistributivo.objects.get(pk=int(iddistributivo), status=True)
                    data['empresa'] = empresa = AsignacionEmpresaPractica.objects.get(pk=int(request.GET['idempresa']))
                    data['fecha'] = fecha = datetime.strptime(request.GET['fecha'], '%Y-%m-%d').date()
                    data['dwnm'] = semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                    data['dia'] = dia = semana[int(request.GET['dia'])-1]
                    data['itinerario'] = itinerario = ItinerariosMalla.objects.get(pk=int(request.GET['iditinerario']))
                    data['horarios'] = horarios = itinerario.malla.carrera.turnoestudiantepractica_set.filter(status=True, activo=True).order_by('turno')

                    pm = PlanificacionMensualSalud.objects.filter(status=True, supervisor=detalledistributivo.distributivo.profesor, periodo=detalledistributivo.distributivo.periodo, itinerariomalla=itinerario, mes=fecha.month).first()
                    listadotemas = []
                    if pm: listadotemas = pm.detalleplanificacionmensualsalud_set.filter(status=True, fechainicio__lte=fecha, fechafin__gte=fecha)
                    data['listadotemas'] = listadotemas

                    template = get_template("pro_actividadestutorpracticas/modal/formadmvisitasupervisor.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': 'Error'.format(ex)})

            elif action == 'planificacionmensualsalud':
                try:
                    data['action'] = action

                    data['title'] = 'Planificación mensual'
                    data['detalledistributivo'] = detalledistributivo = DetalleDistributivo.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    data['supervisor'] = supervisor = detalledistributivo.distributivo.profesor
                    data['ePeriodo'] = ePeriodo = detalledistributivo.distributivo.periodo

                    filtros, ids, s, m, i, url_vars = Q(status=True, supervisor=supervisor, periodo=ePeriodo), request.GET.get('ids', ''), request.GET.get('s', ''), request.GET.get('m', '0'), request.GET.get('i', '0'), ''

                    if ids:
                        data['ids'] = f"{ids}"
                        filtros = filtros & (Q(pk=int(encrypt(ids))))

                    if s:
                        data['s'] = f"{s}"
                        url_vars += f"&s={s}"
                        ss = s.split(' ')
                        if len(ss) == 1:
                            filtros = filtros & (Q(itinerariomalla__nombre__icontains=ss[0]))
                        elif len(ss) == 2:
                            filtros = filtros & ((Q(itinerariomalla__nombre__icontains=ss[0]) & Q(itinerariomalla__nombre__icontains=ss[1])))
                        else:
                            filtros = filtros & (Q(itinerariomalla__nombre__icontains=s))

                    if int(m):
                        filtros = filtros & (Q(mes=m))
                        data['m'] = f"{m}"
                        url_vars += f"&m={m}"

                    if int(i):
                        filtros = filtros & (Q(itinerariomalla_id=i))
                        data['i'] = f"{i}"
                        url_vars += f"&i={i}"

                    eListado = PlanificacionMensualSalud.objects.filter(status=True)
                    data['meses'] = eListado.order_by('mes').distinct('mes')
                    data['itinerarios'] = eListado.values_list('itinerariomalla_id', 'itinerariomalla__nombre').order_by('itinerariomalla_id').distinct('itinerariomalla_id')

                    eListado = eListado.filter(filtros)

                    paging = MiPaginador(eListado.order_by('mes'), 15)
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
                    data['listado'] = page.object_list
                    data['tableIds'] = page.object_list.values_list('id', flat=True)
                    data['url_vars'] = url_vars
                    return render(request, 'pro_actividadestutorpracticas/viewplanificacionmensual.html', data)
                except Exception as ex:
                    ex_err = f"Error al obtener los datos. {ex}. Intente nuevamente más tarde."
                    return HttpResponseRedirect(f'/pro_cronograma?action=listasupervision&info={ex_err}')

            elif action == 'viewdetalleplanificacion':
                try:
                    data['title'] = u'Detalle Planificación Mensual'
                    fecha = datetime.now().date()
                    anio = fecha.year
                    search, url_vars, numerofilas, listadoregistros = request.GET.get('s', ''), '', 10, []
                    semestre = 0
                    registros_por_numerosemana = {}
                    filters, eProfesor = Q(status=True), None
                    data['iddistributivo'] = iddis = int(encrypt(request.GET.get('iddistributivo', 0)))
                    id = request.GET.get('id', None)
                    if not id:
                        raise NameError('Problemas al obtener los datos, intente nuevamente más tarde.')
                    data['id'] = id
                    url_vars += f'&id={id}'
                    id  = int(encrypt(id))
                    data['pm'] = pm = PlanificacionMensualSalud.objects.get(pk=id)
                    filters &= Q(planificacionmensual_id=id)

                    detalledistributivo = DetalleDistributivo.objects.get(id=iddis)
                    data['tutorsupervisor'] = eProfesor = detalledistributivo.distributivo.profesor
                    data['coordinadorppp'] = coordinadorppp = DistributivoPersona.objects.get(denominacionpuesto_id=169, estadopuesto_id=1)
                    data['ePeriodo'] = ePeriodo = detalledistributivo.distributivo.periodo
                    data['directorcarrera'] = directorcarrera = CoordinadorCarrera.objects.filter(carrera=pm.itinerariomalla.malla.carrera, tipo=3, periodo=ePeriodo, status=True).first()
                    docenteasignaturas = []
                    lugarpracticas = []
                    asignaturas = pm.itinerariomalla.itinerarioasignaturasalud_set.filter(status=True)
                    if asignaturas: semestre = asignaturas.last().asignaturamalla.nivelmalla.orden
                    else: semestre = pm.itinerariomalla.nivel.orden
                    data['semestre'] = semestre
                    mes = MESES_CHOICES[pm.mes - 1]
                    data['f_inicio'] = fecha_inicio_pm = date(anio, pm.mes, 1)
                    data['f_fin'] = fecha_fin_pm = date(anio, pm.mes, calendar.monthrange(anio, pm.mes)[1])

                    estudiantespracticas = PracticasPreprofesionalesInscripcion.objects.filter(status=True, supervisor=eProfesor, itinerariomalla=pm.itinerariomalla, culminada=False, estadosolicitud__in=[1, 2], preinscripcion__preinscripcion__periodo=ePeriodo)
                    listadopracticas = estudiantespracticas.order_by('inscripcion_id').values_list('id', flat=True).distinct('inscripcion_id')
                    listadoempresas = PracticasPreprofesionalesInscripcion.objects.values_list('asignacionempresapractica__nombre', flat=True).filter(pk__in=listadopracticas).order_by('asignacionempresapractica__nombre').distinct('asignacionempresapractica__nombre')
                    for e in listadoempresas:
                        lugarpracticas.append(e)
                    data['lugarpracticas'] = lugarpracticas
                    data['periodorotacion'] = estudiantespracticas.first().periodoppp if estudiantespracticas else ePeriodo

                    for a in asignaturas:
                        materia = a.asignaturamalla.materia_set.filter(status=True, nivel__periodo=pm.periodo,
                                                                       silabo__silabosemanal__fechafinciosemana__gte=fecha_inicio_pm,
                                                                       silabo__silabosemanal__fechainiciosemana__lte=fecha_fin_pm).first()
                        docente = materia.profesor_principal()
                        docenteasignaturas.append(docente)

                    data['docenteasignaturas'] = docenteasignaturas
                    listadoregistros = DetallePlanificacionMensualSalud.objects.filter(filters).order_by('numerosemana')

                    for registro in listadoregistros:
                        numerosemana = registro.numerosemana
                        if numerosemana not in registros_por_numerosemana:
                            registros_por_numerosemana[numerosemana] = []
                        registros_por_numerosemana[numerosemana].append(registro)

                    data['eListado'] = registros_por_numerosemana

                    if pm and int(request.GET.get('genera', 0)) == 1:

                        # INICIO GENERA INFORME
                        qrname = f"planificacionmensual_{persona.usuario.username}_{pm.pk}"
                        rutafolder = f"planificacionmensual/{str(anio)}/{pm.mes:02d}/"
                        folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'planificacionmensual', str(anio), f'{pm.mes:02d}', ''))
                        os.makedirs(folder, exist_ok=True)
                        data['urlbase'] = urlbase = get_variable('SITE_URL_SGA')
                        genero, archivogenerado = html_to_pdfsave_evienciassalud('alu_practicaspro/formatos_salud/tutor/planificacionmensual.html',
                                                                                 {'pagesize': 'A4', 'data': data, }, qrname + '.pdf', rutafolder)
                        # FIN GENERA INFORME

                        pm.archivo = rutafolder + qrname + '.pdf'
                        pm.save(request)
                        etiqueta, etiqueta2 = 'Adiciona', 'add'
                        ee = EstadoEvidenciaSalud.objects.filter(planificacionmensual=pm, status=True).first()
                        if ee:
                            ee.archivorespaldo = rutafolder + qrname + '.pdf'
                            ee.persona = persona
                            ee.observacion = 'Archivo planificación mensual generado'
                            ee.fecha = hoytime
                            ee.save(request)
                            etiqueta, etiqueta2 = 'Edita', 'edit'
                        else:
                            ee = EstadoEvidenciaSalud(planificacionmensual=pm, persona=persona, observacion='Archivo planificación mensual generado',
                                                      fecha=hoytime, archivorespaldo=f'{rutafolder}{qrname}.pdf')
                            ee.save(request)
                        log(u'%s estado evidencia Salud: %s' % (etiqueta, str(ee)), request, etiqueta2)
                        detalle = DetalleEstadoEvidenciaSalud(evidencia_estado=ee, persona=persona, observacion='Archivo planificación mensual generado', fecha=hoytime, estado=1)
                        detalle.save(request)
                        log(u'Detalle estado evidencia Salud: %s' % detalle, request, 'add')
                        for d in docenteasignaturas:
                            etiqueta_accion = 'add'
                            if df := FirmaEvidenciaDocente.objects.filter(status=True, evidencia_estado=ee, docente=d.persona):
                                df.firmado = False
                                etiqueta_accion = 'edit'
                            else:
                                df = FirmaEvidenciaDocente(evidencia_estado=ee, docente=d.persona)
                            df.save(request)
                            # if not persona.usuario.group_set.filter(pk=285, user=persona.usuario):
                            #     g = Group.objects.get(pk=285)
                            #     g.user_set.add(persona.usuario)
                            #     g.save()
                            log(u'Firma evidencia docente Salud: %s' % detalle, request, etiqueta_accion)

                        archivo = ee.archivorespaldo.url if ee.archivorespaldo else None
                        if ee.planificacionmensual.archivo:
                            archivo = ee.planificacionmensual.archivo.url

                        data['archivo'] = archivo
                        data['url_archivo'] = '{}{}'.format(dominio_sistema, archivo)
                        data['id_objeto'] = ee.id
                        data['action_firma'] = 'firmadocumento'

                        template = get_template("pro_actividadestutorpracticas/modal/firmarevidenciasalud.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})

                        # data['urlbase'] = urlbase = get_variable('SITE_URL_SGA')
                        # return conviert_html_to_pdf(
                        #     'alu_practicaspro/formatos_salud/tutor/planificacionmensual.html',
                        #     {
                        #         'pagesize': 'A4',
                        #         'data': data,
                        #     },
                        # )

                    return render(request, "pro_actividadestutorpracticas/viewdetalleplanificacionmensual.html", data)
                except Exception as ex:
                    if int(request.GET.get('genera', 0)) == 1:
                        transaction.set_rollback(True)
                    data['msg_error'] = ex.__str__()
                    return render(request, "adm_horarios/error.html", data)

            elif action == 'viewdetalleestadopm':
                try:
                    if 'id' in request.GET:
                        data['id'] = id = request.GET['id']
                        data['estado_evidencia'] = estado_evidencia = EstadoEvidenciaSalud.objects.get(pk=id)
                        data['listado'] = listado = estado_evidencia.detalleestadoevidenciasalud_set.filter(status=True).order_by('fecha')
                        template = get_template("pro_actividadestutorpracticas/modal/viewdetalleestado.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'viewinformesemanales':
                try:
                    data['title'] = u'Informes de planificación Semanal'
                    fecha = datetime.now().date()
                    anio = fecha.year
                    search, url_vars, numerofilas, listadoregistros = request.GET.get('s', ''), '', 10, []
                    semestre = 0
                    registros_por_numerosemana = {}
                    filters = Q(status=True)
                    data['iddistributivo'] = iddis = int(encrypt(request.GET.get('iddistributivo', 0)))
                    if id := request.GET.get('id', None):
                        data['id'] = id
                        url_vars += f'&id={id}'
                        id  = int(encrypt(id))
                        data['pm'] = pm = PlanificacionMensualSalud.objects.get(pk=id)
                        filters &= Q(planificacionmensual_id=id)
                        detalledistributivo = DetalleDistributivo.objects.get(id=iddis)
                        data['tutorsupervisor'] = eProfesor = detalledistributivo.distributivo.profesor
                        # data['coordinadorppp'] = coordinadorppp = DistributivoPersona.objects.get(denominacionpuesto_id=169, estadopuesto_id=1)
                        data['ePeriodo'] = ePeriodo = detalledistributivo.distributivo.periodo
                        # data['directorcarrera'] = directorcarrera = CoordinadorCarrera.objects.filter(carrera=pm.itinerariomalla.malla.carrera, tipo=3, periodo=ePeriodo, status=True).first()
                        docenteasignaturas = []
                        lugarpracticas = []
                        asignaturas = pm.itinerariomalla.itinerarioasignaturasalud_set.filter(status=True)
                        if asignaturas: semestre = asignaturas.last().asignaturamalla.nivelmalla.orden
                        else: semestre = pm.itinerariomalla.nivel.orden
                        data['semestre'] = semestre
                        mes = MESES_CHOICES[pm.mes - 1]
                        data['f_inicio'] = fecha_inicio_pm = date(anio, pm.mes, 1)
                        data['f_fin'] = fecha_fin_pm = date(anio, pm.mes, calendar.monthrange(anio, pm.mes)[1])

                        estudiantespracticas = PracticasPreprofesionalesInscripcion.objects.filter(status=True, supervisor=eProfesor, itinerariomalla=pm.itinerariomalla, culminada=False, estadosolicitud__in=[1, 2], preinscripcion__preinscripcion__periodo=ePeriodo)
                        listadopracticas = estudiantespracticas.order_by('inscripcion_id').values_list('id', flat=True).distinct('inscripcion_id')
                        listadoempresas = PracticasPreprofesionalesInscripcion.objects.values_list('asignacionempresapractica__nombre', flat=True).filter(pk__in=listadopracticas).order_by('asignacionempresapractica__nombre').distinct('asignacionempresapractica__nombre')
                        for e in listadoempresas:
                            lugarpracticas.append(e)
                        data['lugarpracticas'] = lugarpracticas
                        data['periodorotacion'] = estudiantespracticas.first().periodoppp if estudiantespracticas else ePeriodo

                        for a in asignaturas:
                            materia = a.asignaturamalla.materia_set.filter(status=True, nivel__periodo=pm.periodo,
                                                                           silabo__silabosemanal__fechafinciosemana__gte=fecha_inicio_pm,
                                                                           silabo__silabosemanal__fechainiciosemana__lte=fecha_fin_pm).first()
                            docente = materia.profesor_principal()
                            docenteasignaturas.append(docente)

                        data['docenteasignaturas'] = docenteasignaturas

                        detalleplanificacion = pm.detalleplanificacionmensualsalud_set.filter(status=True)
                        data['semanas'] = detalleplanificacion.values_list('numerosemana', flat=True).distinct('numerosemana')
                        listadoregistros = InformePlanificacionSemanalSalud.objects.filter(filters).order_by('numerosemana')

                    data['eListado'] = listadoregistros

                    if int(request.GET.get('genera', 0)) == 1:
                        data['urlbase'] = urlbase = get_variable('SITE_URL_SGA')
                        return conviert_html_to_pdf(
                            'alu_practicaspro/formatos_salud/tutor/planificacionmensual.html',
                            {
                                'pagesize': 'A4',
                                'data': data,
                            },
                        )

                    return render(request, "pro_actividadestutorpracticas/viewinformeplanificacionsemanal.html", data)
                except Exception as ex:
                    data['msg_error'] = ex.__str__()
                    return render(request, "adm_horarios/error.html", data)

            elif action == 'buscaritinerario':
                try:
                    idcarrera = int(request.GET['id']) if 'id' in request.GET and request.GET['id'] != '' else 0
                    resp = []
                    if idcarrera > 0:
                        mallas = Malla.objects.filter(carrera__id=idcarrera)
                        qsbase = ItinerariosMalla.objects.filter(status=True, malla__vigente=True, malla__in=mallas)
                        resp = [{'id': cr.pk, 'text': cr.__str__()} for cr in qsbase.order_by('nombre')]
                    return HttpResponse(json.dumps({'state': True, 'result': resp}))
                except Exception as ex:
                    pass

            # elif action == 'generarinformeplanificacionsemanal':
            #     try:
            #         data['action'] = request.GET['action']
            #         data['id'] = int(encrypt(request.GET['id']))
            #         data['title'] = u'Generar Informe Planificación Semanal'
            #         form = PlanificacionMensualForm()
            #         data['form'] = form
            #         template = get_template("pro_actividadestutorpracticas/modal/formplanificacionmensual.html")
            #         return JsonResponse({"result": True, 'data': template.render(data)})
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'addplanificacion':
                try:
                    data['action'] = request.GET['action']
                    data['idp'] = id_supervisor = int(encrypt(request.GET['idp']))
                    data['idex'] = id_periodo =int(encrypt(request.GET['idex']))
                    data['title'] = u'Adicionar Planificación Mensual'
                    filters_coordinacion = Q(status=True, supervisor_id=id_supervisor, inscripcion__carrera__coordinacion__id__in=[1], preinscripcion__estado__in=[1, 2], culminada=False, supervisor__isnull=False, preinscripcion__preinscripcion__periodo=id_periodo)  # Salud
                    eCarreras = PracticasPreprofesionalesInscripcion.objects.filter(filters_coordinacion).exclude(estadosolicitud=3).values_list('inscripcion__carrera_id', flat=True).order_by('inscripcion__carrera__nombre').distinct()
                    form = PlanificacionMensualForm()
                    form.inicio(eCarreras)
                    data['form'] = form
                    template = get_template("pro_actividadestutorpracticas/modal/formplanificacionmensual.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'editplanificacion':
                try:
                    data['title'] = u'Editar turno'
                    data['action'] = request.GET['action']
                    if id := int(request.GET.get('id', 0)): data['id'] = id
                    if id > 0:
                        data['registro'] = registro = PlanificacionMensualSalud.objects.get(pk=id)
                        id_supervisor = registro.supervisor.id
                        id_periodo = registro.periodo.id
                        filters_coordinacion = Q(status=True, supervisor_id=id_supervisor, inscripcion__carrera__coordinacion__id__in=[1], preinscripcion__estado__in=[1, 2], culminada=False, supervisor__isnull=False, preinscripcion__preinscripcion__periodo=id_periodo)  # Salud
                        eCarreras = PracticasPreprofesionalesInscripcion.objects.filter(filters_coordinacion).exclude(estadosolicitud=3).values_list('inscripcion__carrera_id', flat=True).order_by('inscripcion__carrera__nombre').distinct()
                        f = PlanificacionMensualForm(initial=model_to_dict(registro))
                        f.inicio(eCarreras)
                        f.editar(eCarreras, registro)
                        data['form'] = f
                        template = get_template("pro_actividadestutorpracticas/modal/formplanificacionmensual.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": u"Problemas al obtener los datos. Intente nuevamente más tarde."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'informeplanificacion':
                try:
                    data['title'] = u'Cargar informe mensual'
                    data['action'] = request.GET['action']
                    if id := int(request.GET.get('id', 0)): data['id'] = id
                    if id > 0:
                        data['registro'] = registro = PlanificacionMensualSalud.objects.get(pk=id)
                        f = InformePlanificacionMensualForm(initial={'archivo': registro.archivo.url if registro.archivo else None})
                        data['form'] = f
                        template = get_template("pro_actividadestutorpracticas/modal/formplanificacionmensual.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": u"Problemas al obtener los datos. Intente nuevamente más tarde."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'informeplanificacionsemanal':
                try:
                    data['title'] = u'Cargar informe mensual'
                    data['action'] = request.GET['action']
                    if id := int(request.GET.get('id', 0)): data['id'] = id
                    if id > 0:
                        data['registro'] = registro = InformePlanificacionSemanalSalud.objects.get(pk=id)
                        f = InformePlanificacionMensualForm(initial={'archivo': registro.archivo.url if registro.archivo else None})
                        data['form'] = f
                        template = get_template("pro_actividadestutorpracticas/modal/formplanificacionmensual.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": u"Problemas al obtener los datos. Intente nuevamente más tarde."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'adddetalleplanificacion':
                try:
                    data['action'] = request.GET['action']
                    data['idp'] = int(encrypt(request.GET['idp']))
                    data['title'] = u'Adicionar registro'
                    form = DetallePlanificacionMensual2Form()
                    data['form'] = form
                    template = get_template("pro_actividadestutorpracticas/modal/formplanificacionmensual.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'editdetalleplanificacion':
                try:
                    data['title'] = u'Editar registro'
                    data['action'] = request.GET['action']
                    if id := int(request.GET.get('id', 0)): data['id'] = id
                    if id > 0:
                        data['registro'] = registro = DetallePlanificacionMensualSalud.objects.get(pk=id)
                        f = DetallePlanificacionMensual2Form(initial={'tema': registro.descripciontema,
                                                                      'numerosemana': registro.numerosemana,
                                                                      'fechainicio': registro.fechainicio,
                                                                      'fechafin': registro.fechafin,
                                                                      'objetivo': registro.objetivo,
                                                                      'enfoque': registro.enfoque,
                                                                      'evaluacion': registro.evaluacion,
                                                                      'horas': registro.horas
                                                                      })
                        data['form'] = f
                        template = get_template("pro_actividadestutorpracticas/modal/formplanificacionmensual.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    else:
                        return JsonResponse({"result": False, "mensaje": u"Problemas al obtener los datos. Intente nuevamente más tarde."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})


            return HttpResponseRedirect('/')
        else:
            try:
                data['title'] = u'Listado de Supervisores'
                search, url_vars, numerofilas = request.GET.get('s', ''), '', 10
                nombre_mes = lambda i: ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][i - 1]
                _get_first_col = lambda x: [i[0] for i in x]

                # filters_coordinacion = Q(inscripcion__carrera__coordinacion__id__in=[1], estadosolicitud__in=[1, 2], culminada=False, supervisor__isnull=False, preinscripcion__preinscripcion__periodo=periodo) #Salud
                filters_coordinacion = Q(inscripcion__carrera__coordinacion__id__in=[1], preinscripcion__estado__in=[1, 2], culminada=False, supervisor__isnull=False, preinscripcion__preinscripcion__periodo=periodo) #Salud
                filters = Q(status=True)
                if ids := request.GET.get('id', None):
                    data['ids'] = ids
                    filters &= Q(pk=ids)
                    url_vars += f'&id={ids}'
                listadodocentes = PracticasPreprofesionalesInscripcion.objects.filter(filters_coordinacion & filters).exclude(estadosolicitud=3).values('supervisor').annotate(
                                    cantidad_registros=Count('inscripcion', distinct=True)).order_by('supervisor').distinct()

                listadoregistros = [[Profesor.objects.get(pk=d['supervisor']), d['cantidad_registros']] for d in listadodocentes]
                data['eListado'] = listadoregistros
                request.session['viewactivo'] = 1
                return render(request, "pro_actividadestutorpracticas/viewtutor.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                return render(request, "adm_horarios/error.html", data)