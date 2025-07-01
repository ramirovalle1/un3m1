# -*- coding: UTF-8 -*-
import json
import io
import os

import zipfile
from hashlib import md5

import pyqrcode
import time
import sys
import random
import xlsxwriter
from django.core.exceptions import ObjectDoesNotExist
from googletrans import Translator
from datetime import datetime, date, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction, connections
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.forms import model_to_dict
from decimal import Decimal
from xlwt import *
from decorators import secure_module, last_access
from sagest.forms import MoverInscritoEventoIpecForm, MoverInscritoEventoCapacitacionForm, CapNotaDocenteForm
from sga.excelbackground import reporte_generalcapacitaciones_background, reporte_generalcapacitaciones_inscritos_background, reporte_generalcapacitaciones_facultad_background, reporte_inscritos_carrera_capdocente_background, reporte_totalinscritos_facultad_background, reporte_capacitaciones_aprobadas_background,reporte_generalenncuesta_background
from sga.forms import CapEventoPeriodoForm, CapInscribirForm, CapPeriodoForm, CapEventoForm, CapEnfocadaForm, \
    CapTurnoForm, CapInstructorForm, CapClaseForm, CapConfiguracionForm, CapAsistenciaForm, \
    CapModeloEvaluativoDocenteForm, CapModeloEvaluativoDocenteGeneralForm, CapInscribirPersonaCapacitacionForm, \
    CapSolicitudNecesidadForm, CapPeriodoCronogramaForm
from sga.models import CapEventoPeriodoDocente, CapPeriodoDocente, CapCabeceraSolicitudDocente, \
    CapDetalleSolicitudDocente, \
    CapEventoDocente, CapEnfocadaDocente, CapTurnoDocente, CapInstructorDocente, CapClaseDocente, \
    CapConfiguracionDocente, CapCabeceraAsistenciaDocente, \
    CapDetalleAsistenciaDocente, CapEventoPeriodoFirmasDocente, CapModeloEvaluativoDocente, \
    CapModeloEvaluativoDocenteGeneral, CapNotaDocente, CapDetalleNotaDocente, actualizar_nota_capdocente, Notificacion, \
    CapCronogramaNecesidad, ProfesorDistributivoHoras
from sagest.models import DistributivoPersona, Departamento
from settings import PUESTO_ACTIVO_ID, SITE_STORAGE, DEBUG
from sga.commonviews import adduserdata, obtener_reporte, traerNotificaciones
from sga.forms import BibliografiaProgramaAnaliticoAsignaturaForm, CapEventoPeriodoFirmasForm
from sga.funciones import MiPaginador, log, variable_valor, generar_nombre, suma_dias_habiles, convertir_lista, null_to_decimal
from sga.models import Administrativo, Persona, Pais, Provincia, Canton, Parroquia, DIAS_CHOICES, CUENTAS_CORREOS
from django.template.context import Context
from django.db.models import Max, Q
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdfsaveqrcertificado, conviert_html_to_pdfsaveqrcertificado_v2, conviert_html_to_pdfsaveqrcertificadocapacitacioninstructor
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret',login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    lista = []
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']
        #PERIODO

        if action == 'addperiodomodal':
            try:
                if request.FILES:
                    arch = request.FILES['archivo']
                    nom, ext = os.path.splitext(arch.name)
                    extensiones_permitidas = [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png"]
                    if ext.lower() not in extensiones_permitidas:
                        raise NameError("Formato de archivo no permitido")

                form = CapPeriodoForm(request.POST, request.FILES)
                if not form.is_valid():
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})

                nombres=form.cleaned_data['nombre']
                if form.cleaned_data['fechainicio'] > form.cleaned_data['fechafin']:
                    raise NameError(u"La Fecha esta mal ingresados.")
                if CapPeriodoDocente.objects.values('id').filter(nombre=nombres, status=True).exists():
                    raise NameError(u"El nombre ya existe.")
                if form.cleaned_data['utilizacronograma'] and CapPeriodoDocente.objects.values('id').filter(status=True, utilizacronograma=True).exists():
                    raise NameError(u"Solo se permite tener activado una proyección por periodo.")
                periodo=CapPeriodoDocente(nombre=form.cleaned_data['nombre'],
                                          descripcion=form.cleaned_data['descripcion'],
                                          abreviatura=form.cleaned_data['abreviatura'],
                                          fechainicio=form.cleaned_data['fechainicio'],
                                          fechafin=form.cleaned_data['fechafin'],
                                          utilizacronograma=form.cleaned_data['utilizacronograma'])

                periodo.save(request)
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("capacitacionPA_", newfile._name)
                    periodo.archivo = newfile
                    periodo.save(request)
                log(u'Agrego Período de Evento Docente: %s - [%s]' % (periodo,periodo.id), request, "add")
                return JsonResponse({"result": False, "mensaje": u"Se guardo correctamente los datos"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'editperiodomodal':
            try:
                if request.FILES:
                    arch = request.FILES['archivo']
                    nom, ext = os.path.splitext(arch.name)
                    extensiones_permitidas = [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png"]
                    if ext.lower() not in extensiones_permitidas:
                        raise NameError("Formato de archivo no permitido")
                form = CapPeriodoForm(request.POST, request.FILES)
                if not form.is_valid():
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})

                eCapPeriodoDocente = CapPeriodoDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                if form.cleaned_data['utilizacronograma'] and CapPeriodoDocente.objects.values('id').filter(status=True, utilizacronograma=True).exclude(pk=eCapPeriodoDocente.pk).exists():
                    raise NameError(u"Solo se permite tener activado una proyección por periodo.")
                eCapPeriodoDocente.descripcion = form.cleaned_data['descripcion']
                eCapPeriodoDocente.nombre = form.cleaned_data['nombre']
                eCapPeriodoDocente.abreviatura = form.cleaned_data['abreviatura']
                eCapPeriodoDocente.utilizacronograma = form.cleaned_data['utilizacronograma']

                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("capacitacionPA_", newfile._name)
                    eCapPeriodoDocente.archivo = newfile
                else:
                    if 'archivo-clear' in request.POST:
                        eCapPeriodoDocente.archivo = None

                if eCapPeriodoDocente.esta_cap_evento_periodo_activo():
                    eCapPeriodoDocente.save(request)
                    log(u'Editar Período de Evento Docente: %s' % eCapPeriodoDocente, request, "edit")
                elif form.cleaned_data['fechainicio'] < form.cleaned_data['fechafin']:
                    eCapPeriodoDocente.fechainicio = form.cleaned_data['fechainicio']
                    eCapPeriodoDocente.fechafin = form.cleaned_data['fechafin']
                    eCapPeriodoDocente.save(request)
                    log(u'Editar Período de Evento Docente: %s - [%s]' % (eCapPeriodoDocente, eCapPeriodoDocente.id), request, "edit")
                else:
                    raise NameError(u"La Fecha esta mal ingresados.")
                return JsonResponse({"result": False, "mensaje": u"Se guardo correctamente los datos"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": ex.__str__()})

        elif action == 'delperiodo':
            try:
                periodo = CapPeriodoDocente.objects.get(pk=int(request.POST['id']))
                if periodo.esta_cap_evento_periodo_activo():
                    return JsonResponse({"result": "bad","mensaje": u"No se puede Eliminar el Periodo, tiene planificacion de evento Activas.."})
                log(u'Elimino Período de Evento Docente: %s - [%s]' % (periodo,periodo.id), request, "del")
                periodo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        # EVENTO

        elif action == 'addeventomodal':
            try:
                form = CapEventoForm(request.POST)
                if form.is_valid():
                    if CapEventoDocente.objects.values('id').filter(nombre=form.cleaned_data['nombre'], status=True).exists():
                        return JsonResponse({"result": True, "mensaje": u"El nombre ya existe."})
                    evento = CapEventoDocente(nombre=form.cleaned_data['nombre'],
                                              tipocurso=form.cleaned_data['tipocurso'])
                    evento.save(request)
                    log(u'Agrego Evento Docente: %s - [%s]' % (evento,evento.id), request, "add")
                    return JsonResponse({"result": False, 'mensaje': 'Registro Exitoso'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'editeventomodal':
            try:
                form = CapEventoForm(request.POST)
                if form.is_valid():
                    evento = CapEventoDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                    evento.nombre = form.cleaned_data['nombre']
                    if not evento.esta_cap_evento_activo():
                        evento.tipocurso = form.cleaned_data['tipocurso']
                    evento.save(request)
                    log(u'Editar Evento Docente: %s - [%s]' % (evento,evento.id), request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})

                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'delevento':
            try:
                evento = CapEventoDocente.objects.get(pk=int(request.POST['id']))
                if evento.esta_cap_evento_activo():
                    return JsonResponse({"result": "bad","mensaje": u"No se puede Eliminar, se esta utilizando en Planificación de Eventos.."})
                log(u'Elimino Evento Docente: %s - [%s]' % (evento,evento.id), request, "del")
                evento.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        #ENFOQUE

        elif action == 'addenfoquemodal':
            try:
                form = CapEnfocadaForm(request.POST)
                if form.is_valid():
                    if CapEnfocadaDocente.objects.values('id').filter(nombre=form.cleaned_data['nombre'], status=True).exists():
                        return JsonResponse({"result": True, "mensaje": u"El nombre ya existe."})
                    enfo=CapEnfocadaDocente(nombre=form.cleaned_data['nombre'])
                    enfo.save(request)
                    log(u'Agrego Capacitación Enfoque Docente: %s - [%s]' % (enfo,enfo.id), request, "add")
                    return JsonResponse({"result": False, 'mensaje': 'Registro Exitoso'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'editenfoquemod':
            try:
                form = CapEnfocadaForm(request.POST)
                if form.is_valid():
                    enfo = CapEnfocadaDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                    enfo.nombre = form.cleaned_data['nombre']
                    enfo.save(request)
                    log(u'Editar Capacitación Enfoque Docente: %s - [%s]' % (enfo,enfo.id), request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Registro Exitoso'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'delenfoque':
            try:
                enfo = CapEnfocadaDocente.objects.get(pk=int(request.POST['id']))
                if enfo.capeventoperiododocente_set.values('id').filter(status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar, esta usado en planificación de evento."})
                log(u'Elimino Capacitación Enfoque Docente: %s - [%s]' % (enfo,enfo.id), request, "del")
                enfo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        #MODELO EVALUATIVO

        elif action == 'addmodelomodal':
            try:
                form = CapModeloEvaluativoDocenteForm(request.POST)
                if form.is_valid():
                    if not form.cleaned_data['notaminima'] < form.cleaned_data['notamaxima']:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"La nota mínima y máxima estan mal ingresadas."})
                    if CapModeloEvaluativoDocente.objects.filter(nombre=form.cleaned_data['nombre'],
                                                                   status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                    modelo = CapModeloEvaluativoDocente(nombre=form.cleaned_data['nombre'],
                                                          notaminima=form.cleaned_data['notaminima'],
                                                          notamaxima=form.cleaned_data['notamaxima'],
                                                          principal=form.cleaned_data['principal'],
                                                          evaluacion=form.cleaned_data['evaluacion'])
                    modelo.save(request)
                    log(u'Agrego Detalle Modelo Evaluativo de docente: %s - [%s]' % (modelo, modelo.id),
                        request, "add")
                    return JsonResponse({"result": False, 'messaje': 'Registro Exitoso'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'editmodelomodal':
            try:
                form = CapModeloEvaluativoDocenteForm(request.POST)
                if form.is_valid():
                    modelo = CapModeloEvaluativoDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                    if not form.cleaned_data['notaminima'] < form.cleaned_data['notamaxima']:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"La nota mínima y máxima esta mal ingresadas."})
                    modelo.nombre = form.cleaned_data['nombre']
                    modelo.notaminima = form.cleaned_data['notaminima']
                    modelo.notamaxima = form.cleaned_data['notamaxima']
                    modelo.principal = form.cleaned_data['principal']
                    modelo.evaluacion = form.cleaned_data['evaluacion']
                    modelo.save(request)
                    log(u'Edito Detalle Modelo Evaluativo de Capacitación docente: %s - [%s]' % (modelo, modelo.id),
                        request, "edit")
                    return JsonResponse({"result": False, "message" : "Registro exitoso"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'delmodelo':
            try:
                modelo = CapModeloEvaluativoDocente.objects.get(pk=int(request.POST['id']))
                if modelo.capnotadocente_set.filter(status=True).exists():
                    return JsonResponse({"result": "bad",
                                         "mensaje": u"No puede Eliminar el Modelo Evaluativo, está siendo utilizado en notas.."})
                log(u'Elimino Modelo Evaluativo de Capacitación docente: %s - [%s]' % (modelo, modelo.id), request, "del")
                modelo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addmodelogeneral':
            try:

                if CapModeloEvaluativoDocenteGeneral.objects.filter(status=True,
                                                                 modelo_id=int(request.POST['modelo'])).exists():
                    transaction.set_rollback(True)
                    return JsonResponse({"error": True, "mensaje": "Modelo Evaluativo ya existe."}, safe=False)

                if CapModeloEvaluativoDocenteGeneral.objects.filter(orden=request.POST['orden'],
                                                             status=True).exists():
                    return JsonResponse({"result": True, "mensaje": u"El orden ya existe."})

                form = CapModeloEvaluativoDocenteGeneralForm(request.POST)
                if form.is_valid():
                    filtro = CapModeloEvaluativoDocenteGeneral(modelo=form.cleaned_data['modelo'],
                                                            orden=form.cleaned_data['orden'])
                    filtro.save(request)
                    log(u'Adiciono Modelo Evaluativo general de docente a la configuración: %s' % filtro, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editmodelogeneral':
            try:
                with transaction.atomic():

                    # excluido = CapModeloEvaluativoDocenteGeneral.objects.filter(status=True).exclude(pk=int(encrypt(request.POST['id'])))
                    # if CapModeloEvaluativoDocenteGeneral.objects.filter(orden=request.POST['orden'],
                    #                                                     status=True ).exclude(pk__in=excluido):
                    #     return JsonResponse({"result": True, "mensaje": u"El orden ya existe."})

                    excluido = CapModeloEvaluativoDocenteGeneral.objects.filter(
                        orden=request.POST['orden'],
                        status=True
                    ).exclude(pk=int(encrypt(request.POST['id']))).exists()


                    if excluido:
                        return JsonResponse({"result": True, "mensaje": u"El orden ya existe."})


                    filtro = CapModeloEvaluativoDocenteGeneral.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = CapModeloEvaluativoDocenteGeneralForm(request.POST)
                    if f.is_valid():
                        filtro.orden = f.cleaned_data['orden']

                        filtro.modelo = f.cleaned_data['modelo']

                        filtro.save(request)
                        log(u'Modificó Modelo Evaluativo de docente de la configuración: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Error al guardar los datos."}, safe=False)

        elif action == 'delmodelogeneral':
            try:
                modelo = CapModeloEvaluativoDocenteGeneral.objects.get(pk=int(request.POST['id']))
                log(u'Elimino Modelo Evaluativo de Capacitación docente: %s - [%s]' % (modelo, modelo.id), request, "del")
                modelo.status = False
                modelo.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addmodelonotas':
            try:
                modelonota = CapNotaDocente(modelo_id=int(request.POST['idm']),
                                         fecha=datetime.now().date(),
                                         instructor_id=int(request.POST['idi']))
                modelonota.save(request)
                log(u'Agrego Modelo en Notas de Capacitación Docente: %s - [%s]' % (modelonota, modelonota.id), request,
                    "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delmodelonota':
            try:
                modelonota = CapNotaDocente.objects.get(pk=int(request.POST['id']))
                log(u'Elimino modelo en nota de Capacitación Docente: %s - [%s]' % (modelonota, modelonota.id), request,
                    "del")
                modelonota.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'calificar':
            try:
                tarea = CapNotaDocente.objects.get(pk=int(request.POST['id']), status=True)
                if not tarea.instructor.capeventoperiodo.exiten_inscritos():
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"No puede continuar, porque no existen inscritos."})
                for inscrito in tarea.instructor.capeventoperiodo.inscritos():
                    if not inscrito.capdetallenotadocente_set.filter(status=True, cabeceranota=tarea,
                                                                  inscrito=inscrito).exists():
                        detalle = CapDetalleNotaDocente(cabeceranota=tarea, inscrito=inscrito)
                        detalle.save(request)
                        log(u'Adicionado inscrito para calificar tarea de capacitacion docente: %s - [%s]' % (
                            detalle, detalle.id), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'calificageneral':
            try:
                instructor = CapInstructorDocente.objects.get(pk=int(request.POST['id']), status=True)
                if not instructor.capeventoperiodo.exiten_inscritos():
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"No puede continuar, porque no existen inscritos."})
                for inscrito in instructor.capeventoperiodo.inscritos():
                    for tarea in instructor.capnotadocente_set.all():
                        if not inscrito.capdetallenotadocente_set.filter(status=True, cabeceranota=tarea,
                                                                      inscrito=inscrito).exists():
                            detalle = CapDetalleNotaDocente(cabeceranota=tarea, inscrito=inscrito)
                            detalle.save(request)
                            log(u'Adicionado inscrito para calificar tarea de capacitacion docente: %s - [%s]' % (
                                detalle, detalle.id), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        #TURNO

        elif action == 'addturnomodal':
            try:
                form = CapTurnoForm(request.POST)
                if form.is_valid():
                    if CapTurnoDocente.objects.values('id').filter(turno=form.cleaned_data['turno'], status=True).exists():
                        return JsonResponse({"result": True, "mensaje": u"El Turno ya existe."})
                    if CapTurnoDocente.objects.values('id').filter(horainicio=form.cleaned_data['horainicio'], status=True).exists():
                        return JsonResponse({"result": True, "mensaje": u"La hora inicio ya existe."})
                    if CapTurnoDocente.objects.values('id').filter(horafin=form.cleaned_data['horafin'], status=True).exists():
                        return JsonResponse({"result": True, "mensaje": u"La hora fin ya existe."})
                    if form.cleaned_data['horainicio']>form.cleaned_data['horafin']:
                        return JsonResponse({"result": True, "mensaje": u"Las hora fin no debe ser mayor."})

                    horas=float(request.POST['horas'])

                    turno=CapTurnoDocente(turno=request.POST['turno'],
                                          horainicio=form.cleaned_data['horainicio'],
                                          horafin=form.cleaned_data['horafin'],
                                          horas=horas)
                    turno.save(request)
                    log(u'Agrego Turno de Capacitación Docente: %s - [%s]' % (turno,turno.id), request, "add")
                    return JsonResponse({"result": False, "message" : "Registro exitoso"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'editturno':
            try:
                form = CapTurnoForm(request.POST)
                if form.is_valid():
                    turno = CapTurnoDocente.objects.get(pk=int(request.POST['id']))
                    if CapTurnoDocente.objects.values('id').filter(horainicio=form.cleaned_data['horainicio'], status=True).exclude(pk=turno.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La hora inicio ya existe."})
                    if CapTurnoDocente.objects.values('id').filter(horafin=form.cleaned_data['horafin'], status=True).exclude(pk=turno.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La hora fin ya existe."})
                    if form.cleaned_data['horainicio']>form.cleaned_data['horafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"Las hora fin no debe ser mayor."})
                    datos = json.loads(request.POST['lista_items1'])
                    horas = 0
                    for elemento in datos:
                        horas = float(elemento['horas'])
                    turno.horainicio = form.cleaned_data['horainicio']
                    turno.horafin = form.cleaned_data['horafin']
                    turno.horas= horas
                    turno.save(request)
                    log(u'Editar Turno de Capacitación Docente: %s - [%s]' % (turno,turno.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editturnomodal':
            try:

                horainicio = request.POST.get('horainicio', '')
                horafin = request.POST.get('horafin', '')

                horainicio = horainicio[:5]
                horafin = horafin[:5]

                modified_data = {'horainicio': horainicio, 'horafin': horafin}
                request.POST = request.POST.copy()
                request.POST.update(modified_data)

                form = CapTurnoForm(request.POST)

                if form.is_valid():
                    turno = CapTurnoDocente.objects.get(pk=int(encrypt(request.POST['id'])))
                    if CapTurnoDocente.objects.values('id').filter(horainicio=form.cleaned_data['horainicio'], status=True).exclude(pk=turno.id).exists():
                        return JsonResponse({"result": True, "mensaje": u"La hora inicio ya existe."})
                    if CapTurnoDocente.objects.values('id').filter(horafin=form.cleaned_data['horafin'], status=True).exclude(pk=turno.id).exists():
                        return JsonResponse({"result": True, "mensaje": u"La hora fin ya existe."})
                    if form.cleaned_data['horainicio']>form.cleaned_data['horafin']:
                        return JsonResponse({"result": True, "mensaje": u"Las hora fin no debe ser mayor."})

                    horas=float(request.POST['horas'])

                    turno.horainicio = form.cleaned_data['horainicio']
                    turno.horafin = form.cleaned_data['horafin']
                    turno.horas= horas
                    turno.save(request)
                    log(u'Editar Turno de Capacitación Docente: %s - [%s]' % (turno,turno.id), request, "edit")
                    return JsonResponse({"result": False, "mensaje": u"Registro exitoso."})
                else:
                    raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        elif action == 'delturno':
            try:
                turno = CapTurnoDocente.objects.get(pk=int(request.POST['id']))
                if turno.capclasedocente_set.values('id').filter(status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, se esta usando en horarios"})
                log(u'Elimino Turno en Capacitación Docente: %s - [%s]' % (turno,turno.id), request, "del")
                turno.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        #CONFIGURACION
        elif action == 'configuracion':
            try:
                if 'fondocertificado' in request.FILES:
                    arch = request.FILES['fondocertificado']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 6291456:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 6 Mb."})
                    if not exte.lower() == 'jpg':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .jpg"})
                form = CapConfiguracionForm(request.POST)
                if form.is_valid():
                    if not form.cleaned_data['minasistencia'] > 0 and not form.cleaned_data['minnota'] > 0:
                        return JsonResponse({"result": "bad", "mensaje": u"La minima nota y asistencia debe ser mayor a cero ."})
                    configuracion = CapConfiguracionDocente.objects.filter()
                    if configuracion.values('id').exists():
                        configuracion=configuracion[0]
                        log(u'Edito configuración de capacitación Docente: %s' % configuracion, request, "edit")
                    else:
                        configuracion = CapConfiguracionDocente()
                        log(u'Adiciono configuración de capacitación Docente: %s' % configuracion, request, "add")
                    revisado = DistributivoPersona.objects.get(pk=form.cleaned_data['revisado'])
                    aprobado1 = DistributivoPersona.objects.get(pk=form.cleaned_data['aprobado1'])
                    aprobado2 = DistributivoPersona.objects.get(pk=form.cleaned_data['aprobado2'])
                    aprobado3 = DistributivoPersona.objects.get(pk=form.cleaned_data['aprobado3'])
                    personasubrogante = DistributivoPersona.objects.get(pk=form.cleaned_data['personasubrogante'])
                    configuracion.minasistencia = form.cleaned_data['minasistencia']
                    configuracion.minnota = form.cleaned_data['minnota']
                    configuracion.revisado = revisado.persona
                    configuracion.aprobado1 = aprobado1.persona
                    configuracion.aprobado2 = aprobado2.persona
                    configuracion.aprobado3 = aprobado3.persona
                    configuracion.denominacionrevisado = revisado.denominacionpuesto
                    configuracion.denominacionaprobado1 = aprobado1.denominacionpuesto
                    configuracion.denominacionaprobado2 = aprobado2.denominacionpuesto
                    configuracion.denominacionaprobado3 = aprobado3.denominacionpuesto
                    configuracion.personasubrogante = personasubrogante.persona
                    configuracion.tiposubrogante = form.cleaned_data['tiposubrogante']
                    configuracion.essubrogante = form.cleaned_data['essubrogante']
                    configuracion.abreviaturadepartamento = form.cleaned_data['abreviaturadepartamento']
                    configuracion.save(request)
                    if 'fondocertificado' in request.FILES:
                        ruta = os.path.join(SITE_STORAGE, 'media', 'reportes', 'encabezados_pies','')
                        rutapdf = ruta + u"capacitaciondocente.jpg"
                        if os.path.isfile(rutapdf):
                            os.remove(rutapdf)

                        fondo = request.FILES['fondocertificado']
                        fondo._name = u"capacitaciondocente.jpg"
                        configuracion.fondocertificado = fondo
                        configuracion.save(request)
                    return JsonResponse({"result": "ok","redirect_url": "/adm_capacitaciondocente/gestion?action=eventos"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        #EVENTO PERIODO
        elif action == 'addperiodoevento':
            try:
                form = CapEventoPeriodoForm(request.POST)
                periodo = CapPeriodoDocente.objects.get(pk=int(request.POST['periodo']))
                form.editar_encuesta(periodo)
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError(v[0])
                if form.is_valid():
                    if not form.cleaned_data['responsable'] > 0:
                        return JsonResponse({"result": "bad", "mensaje": u"Ingrese un responsable."})
                    if not form.cleaned_data['fechainicio'] >=periodo.fechainicio or not form.cleaned_data['fechafin'] <= periodo.fechafin:
                        return JsonResponse({"result": "bad", "mensaje": u"Las fecha no puede ser mayor a las fecha del periodo."})
                    if not form.cleaned_data['fechainicio'] <= form.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ser mayor la fecha de inicio."})
                    if not form.cleaned_data['regimenlaboral']:
                        return JsonResponse({"result": "bad", "mensaje": u"Ingrese un regimen laboral."})
                    configuracion=CapConfiguracionDocente.objects.all()
                    evento=CapEventoPeriodoDocente(periodo=periodo,
                                                    periodoac = form.cleaned_data['periodoac'],
                                                    capevento=form.cleaned_data['capevento'],
                                                    departamento=form.cleaned_data['departamento'],
                                                    horas= form.cleaned_data['horas'],
                                                    horasautonoma=form.cleaned_data['horasautonoma'],
                                                    horaspropedeutica=form.cleaned_data['horaspropedeutica'],
                                                    horaspracticas=form.cleaned_data['horaspracticas'],
                                                    horasexperimentales=form.cleaned_data['horasexperimentales'],
                                                    objetivo=form.cleaned_data['objetivo'],
                                                    observacion=form.cleaned_data['observacion'],
                                                    minasistencia=form.cleaned_data['minasistencia'],
                                                    minnota=form.cleaned_data['minnota'],
                                                    regimenlaboral=form.cleaned_data['regimenlaboral'],
                                                    tipoparticipacion=form.cleaned_data['tipoparticipacion'],
                                                    contextocapacitacion=form.cleaned_data['contextocapacitacion'],
                                                    modalidad=form.cleaned_data['modalidad'],
                                                    tipocertificacion=form.cleaned_data['tipocertificacion'],
                                                    tipocapacitacion=form.cleaned_data['tipocapacitacion'],
                                                    pais=form.cleaned_data['pais'],
                                                    provincia=form.cleaned_data['provincia'],
                                                    canton=form.cleaned_data['canton'],
                                                    parroquia=form.cleaned_data['parroquia'],
                                                    areaconocimiento=form.cleaned_data['areaconocimiento'],
                                                    subareaconocimiento=form.cleaned_data['subareaconocimiento'],
                                                    subareaespecificaconocimiento=form.cleaned_data['subareaespecificaconocimiento'],
                                                    aula=form.cleaned_data['aula'],
                                                    fechainicio=form.cleaned_data['fechainicio'],
                                                    fechafin=form.cleaned_data['fechafin'],
                                                    cupo=form.cleaned_data['cupo'],
                                                    enfoque=form.cleaned_data['enfoque'],
                                                    visualizar=form.cleaned_data['visualizar'],
                                                    contenido=form.cleaned_data['contenido'],
                                                    revisado = configuracion[0].revisado,
                                                    aprobado1 = configuracion[0].aprobado1,
                                                    aprobado2 = configuracion[0].aprobado2,
                                                    aprobado3=configuracion[0].aprobado3,
                                                    denominacionrevisado = configuracion[0].denominacionrevisado,
                                                    denominacionaprobado1 = configuracion[0].denominacionaprobado1,
                                                    denominacionaprobado2 = configuracion[0].denominacionaprobado2,
                                                    denominacionaprobado3=configuracion[0].denominacionaprobado3,
                                                    codigo=form.cleaned_data['codigo'],
                                                    abreviaturadepartamento=configuracion[0].abreviaturadepartamento,
                                                    responsable=Administrativo.objects.get(pk=form.cleaned_data['responsable']).persona,
                                                    observacionreporte=form.cleaned_data['observacionreporte'],
                                                    modeloevaluativoindividual=form.cleaned_data['modeloevaluativoindividual'],
                                                    unificarmoodle = form.cleaned_data['unificarmoodle'],
                                                    encuesta = form.cleaned_data['encuesta']
                                                    )
                    evento.save(request)
                    evento.modalidadlaboral.clear()
                    for modalidad in form.cleaned_data['modalidadlaboral']:
                        evento.modalidadlaboral.add(modalidad)
                    log(u'Agrego Planificación de Evento Docente: %s - [%s] ' % (evento,evento.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editperiodoevento':
            try:
                form = CapEventoPeriodoForm(request.POST)
                evento = CapEventoPeriodoDocente.objects.get(pk=int(request.POST['id']))
                form.editar_encuesta(evento.periodo)
                if form.is_valid():

                    if not form.cleaned_data['fechainicio']>=evento.periodo.fechainicio or not form.cleaned_data['fechafin']<=evento.periodo.fechafin:
                        return JsonResponse({"result": "bad", "mensaje": u"Las fecha no puede ser mayor a las fecha del periodo."})
                    if not form.cleaned_data['fechainicio'] <= form.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ser mayor la fecha de inicio."})
                    evento.capevento = form.cleaned_data['capevento']
                    evento.periodoac = form.cleaned_data['periodoac']
                    evento.horas = form.cleaned_data['horas']
                    evento.horaspracticas = form.cleaned_data['horaspracticas']
                    evento.horasexperimentales = form.cleaned_data['horasexperimentales']
                    evento.horasautonoma = form.cleaned_data['horasautonoma']
                    evento.departamento = form.cleaned_data['departamento']
                    evento.horaspropedeutica = form.cleaned_data['horaspropedeutica']
                    evento.objetivo = form.cleaned_data['objetivo']
                    evento.observacion = form.cleaned_data['observacion']
                    evento.minasistencia = form.cleaned_data['minasistencia']
                    evento.minnota = form.cleaned_data['minnota']
                    evento.folder = form.cleaned_data['folder']
                    if not evento.exiten_inscritos():
                        evento.regimenlaboral = form.cleaned_data['regimenlaboral']
                    evento.aula = form.cleaned_data['aula']
                    evento.fechainicio = form.cleaned_data['fechainicio']
                    evento.fechafin = form.cleaned_data['fechafin']
                    evento.tipoparticipacion = form.cleaned_data['tipoparticipacion']
                    evento.contextocapacitacion = form.cleaned_data['contextocapacitacion']
                    evento.modalidad = form.cleaned_data['modalidad']
                    evento.tipocertificacion = form.cleaned_data['tipocertificacion']
                    evento.tipocapacitacion = form.cleaned_data['tipocapacitacion']
                    evento.pais = form.cleaned_data['pais']
                    evento.provincia = form.cleaned_data['provincia']
                    evento.canton = form.cleaned_data['canton']
                    evento.parroquia = form.cleaned_data['parroquia']
                    evento.areaconocimiento = form.cleaned_data['areaconocimiento']
                    evento.subareaconocimiento = form.cleaned_data['subareaconocimiento']
                    evento.subareaespecificaconocimiento = form.cleaned_data['subareaespecificaconocimiento']
                    evento.visualizar = form.cleaned_data['visualizar']
                    evento.contenido = form.cleaned_data['contenido']
                    evento.enfoque = form.cleaned_data['enfoque']
                    evento.cupo = form.cleaned_data['cupo']
                    evento.responsable_id = form.cleaned_data['responsable']
                    evento.modeloevaluativoindividual = form.cleaned_data['modeloevaluativoindividual']
                    evento.unificarmoodle = form.cleaned_data['unificarmoodle']
                    evento.encuesta = form.cleaned_data['encuesta']
                    if form.cleaned_data['actualizar']:
                        configuracion = CapConfiguracionDocente.objects.all()
                        evento.revisado = configuracion[0].revisado
                        evento.aprobado1 = configuracion[0].aprobado1
                        evento.aprobado2 = configuracion[0].aprobado2
                        evento.aprobado3 = configuracion[0].aprobado3
                        evento.abreviaturadepartamento = configuracion[0].abreviaturadepartamento
                        evento.denominacionrevisado = configuracion[0].denominacionrevisado
                        evento.denominacionaprobado1 = configuracion[0].denominacionaprobado1
                        evento.denominacionaprobado2 = configuracion[0].denominacionaprobado2
                        evento.denominacionaprobado3 = configuracion[0].denominacionaprobado3
                        log(u'Actualizo los aprobados, revisar y abreviaturas del departamento en el evento Docente: %s [%s] - %s - %s - %s - %s - %s - %s - %s - %s - %s ' % (evento, evento.id, evento.revisado, evento.aprobado1, evento.aprobado2, evento.aprobado3, evento.abreviaturadepartamento, evento.denominacionrevisado, evento.denominacionaprobado1, evento.denominacionaprobado2, evento.denominacionaprobado3), request, "edit")
                    else:
                        if form.cleaned_data['revisado']:
                            evento.revisado_id = form.cleaned_data['revisado']
                            if DistributivoPersona.objects.filter(persona_id=form.cleaned_data['revisado'], estadopuesto__id=PUESTO_ACTIVO_ID,  status=True).exists():
                                distributivo =  DistributivoPersona.objects.filter(persona_id=form.cleaned_data['revisado'], estadopuesto__id=PUESTO_ACTIVO_ID,
                                                                   status=True)[0]
                                evento.denominacionrevisado = distributivo.denominacionpuesto
                    evento.codigo=form.cleaned_data['codigo']
                    evento.observacionreporte = form.cleaned_data['observacionreporte']
                    evento.modalidadlaboral.clear()
                    for modalidad in form.cleaned_data['modalidadlaboral']:
                        evento.modalidadlaboral.add(modalidad)
                    evento.save(request)
                    log(u'Edito Planificación de Evento Docente: %s - [%s] ' % (evento,evento.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delperiodoevento':
            try:
                evento = CapEventoPeriodoDocente.objects.get(pk=int(request.POST['id']))
                # if evento.puede_eliminar_planificacion_evento():
                if not evento.puede_eliminar_evento():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, porque tiene inscritos"})
                    # return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, porque tiene "+evento.puede_eliminar_planificacion_evento()+" activos"})
                log(u'Elimino Evento Periodo Docente: %s' % evento, request, "del")
                evento.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'updatecupo':
            try:
                evento = CapEventoPeriodoDocente.objects.get(pk=int(request.POST['eid']))
                valor = int(request.POST['vc'])
                if valor > 999:
                    return JsonResponse({"result": "bad", "mensaje": u"No puede establecer un cupo menor a" + str(999 + 1)})
                if valor < evento.contar_inscripcion_evento_periodo():
                    return JsonResponse({"result": "bad", "mensaje": u"El cupo no puede ser menor a la cantidad de inscrito"})
                cupoanterior = evento.cupo
                evento.cupo = valor
                evento.save(request)
                log(u'Actualizo cupo a evento: %s cupo anterior: %s cupo actual Docente: %s' % (evento, str(cupoanterior), str(evento.cupo)), request, "add")
                return JsonResponse({'result': 'ok', 'valor': evento.cupo})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u"Error al eliminar los datos."})

        elif action == 'addinscribir':
            try:
                f = CapInscribirForm(request.POST)
                if f.is_valid():
                    listadatos = json.loads(request.POST['lista_items1'])
                    if listadatos:
                        listadistributivo = Persona.objects.filter(id__in=[int(datos['iddistributivo']) for datos in listadatos]) if listadatos else []
                        for distributivo in listadistributivo:
                            if not CapEventoPeriodoDocente.objects.get(pk=int(request.POST['eventoperiodo'])).hay_cupo_inscribir():
                                return JsonResponse({"result": "bad", "mensaje": u"No hay cupo para continuar adicionando"})
                            if CapCabeceraSolicitudDocente.objects.values('id').filter(participante=distributivo, capeventoperiodo_id=int(request.POST['eventoperiodo'])).exists():
                                return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra inscrito o está en estado solicitado"})
                            cabecera = CapCabeceraSolicitudDocente(capeventoperiodo_id=int(request.POST['eventoperiodo']),
                                                                    solicita=persona,
                                                                    fechasolicitud=datetime.now().date(),
                                                                    estadosolicitud=variable_valor('APROBADO_CAPACITACION'),
                                                                    fechaultimaestadosolicitud=datetime.now().date(),
                                                                    participante=distributivo.persona)
                            cabecera.save(request)
                            log(u'Ingreso Cabecera Inscribio en Evento Docente: %s (participante: %s )(estado solicitud : %s) - [%s]' % (cabecera,cabecera.participante,cabecera.estadosolicitud,cabecera.id), request, "add")
                            detalle = CapDetalleSolicitudDocente(cabecera=cabecera,
                                                                  aprueba=persona,
                                                                  observacion=f.cleaned_data['observacion'],
                                                                  fechaaprobacion=datetime.now().date(),
                                                                  estado=2)
                            detalle.save(request)
                            detalle.mail_notificar_talento_humano(request.session['nombresistema'], True)
                            log(u'Ingreso Detalle Inscribio de Evento Docente: %s  (fechaaprobacion: %s)-[%id]' % (detalle,detalle.fechaaprobacion,detalle.id), request, "add")
                    else:
                        distributivo=Persona.objects.get(id=f.cleaned_data['participante'])
                        if CapCabeceraSolicitudDocente.objects.values('id').filter(participante=distributivo,capeventoperiodo_id=int(request.POST['eventoperiodo'])).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra inscrito o está en estado solicitado"})
                        if not CapEventoPeriodoDocente.objects.get(pk=int(request.POST['eventoperiodo'])).hay_cupo_inscribir():
                            return JsonResponse({"result": "bad", "mensaje": u"No hay cupo para continuar adicionando"})
                        cabecera = CapCabeceraSolicitudDocente(capeventoperiodo_id=int(request.POST['eventoperiodo']),
                                                                solicita=persona,
                                                                fechasolicitud=datetime.now().date(),
                                                                estadosolicitud=variable_valor('APROBADO_CAPACITACION'),
                                                                fechaultimaestadosolicitud=datetime.now(),
                                                                participante=distributivo)
                        cabecera.save(request)
                        log(u'Ingreso Cabecera Inscribio en Evento Docente: %s' % cabecera, request, "add")
                        detalle = CapDetalleSolicitudDocente(cabecera=cabecera,
                                                              aprueba=persona,
                                                              observacion=f.cleaned_data['observacion'],
                                                              fechaaprobacion=datetime.now().date(),
                                                              estado=2)
                        detalle.save(request)
                        detalle.mail_notificar_talento_humano(request.session['nombresistema'], True)
                        log(u'Ingreso Detalle Inscribio de Evento Docente: %s  (fechaaprobacion: %s)-[%id]' % (detalle,detalle.fechaaprobacion,detalle.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Llene todos los campos"})

        elif action == 'delinscrito':
            try:
                cabecera = CapCabeceraSolicitudDocente.objects.get(pk=int(request.POST['id']))
                # if not cabecera.puede_eliminar_inscrito():
                #     return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, el inscrito ya cuenta con asistencia"})
                if not cabecera.puede_eliminar_inscrito2():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, el inscrito ya cuenta con asistencia o calificación"})
                cabecera.capdetallesolicituddocente_set.all().delete()
                # cabecera.mail_notificar_talento_humano(request.session['nombresistema'])
                log(u'Elimino Incrito cabecera y sus detalle de Solicitud Docente: %s' % cabecera, request, "del")
                cabecera.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'bloqueopublicacion':
            try:
                evento = CapEventoPeriodoDocente.objects.get(pk=request.POST['id'])
                evento.visualizar = True if request.POST['val'] == 'y' else False
                if evento.visualizar == True:
                    docentes = ProfesorDistributivoHoras.objects.filter(periodo=evento.periodoac)
                    titulo = 'Nuevo curso perfeccionamiento'
                    cuerpo = f'La capacitación {evento.capevento.nombre} se encuentra activa'
                    for pro in docentes:
                        noti = Notificacion(cuerpo=cuerpo,
                                            titulo=titulo,
                                            destinatario=pro.profesor.persona,
                                            url='',
                                            prioridad=1,
                                            app_label='SGA',
                                            fecha_hora_visible=datetime.now() + timedelta(days=1),
                                            tipo=2, en_proceso=True)
                        noti.save()

                evento.save(request)
                log(u'Visualiza o no en capacitacion evento periodo Docente: %s (%s)' % (evento,evento.visualizar), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        elif action == 'listadoexportarmoodle':
            try:
                instructor = CapInstructorDocente.objects.get(pk=request.POST['idinstructor'])
                modeloNotas = instructor.capnotadocente_set.filter(status=True).count()
                if modeloNotas > 0:
                    curso = instructor.capeventoperiodo
                    listadocodigo = curso.capcabecerasolicituddocente_set.values_list('participante__idusermoodle', flat=True).filter(status=True).distinct()
                    if not listadocodigo:
                        return JsonResponse({"result": "bad", "mensaje": 'Este curso no tiene ningún inscrito'})
                    if len(listadocodigo) == 1:
                        listadocodigo = '({})'.format(listadocodigo[0])
                    else:
                        listadocodigo = tuple(listadocodigo)


                    cursor = connections['moodle_pos'].cursor()
                    sql = """SELECT DISTINCT  ARRAY_TO_STRING(array_agg(us1.id),',')                                      
                             FROM mooc_role_assignments asi
                            INNER JOIN MOOC_CONTEXT CON ON asi.CONTEXTID=CON.ID
                            INNER JOIN mooc_user us1 ON us1.id=asi.userid
                            AND ASI.ROLEID=%s
                            AND CON.INSTANCEID=%s
                            AND us1.id in %s""" % (9, instructor.idcursomoodle, listadocodigo)
                    cursor.execute(sql)

                    listadosmoodle = []
                    row = cursor.fetchall()
                    if instructor.idcursomoodle:
                        if row[0][0]:
                            listadosmoodle = row[0][0].split(",")
                    listac = None

                    listacurso = curso.capcabecerasolicituddocente_set.filter(status=True).distinct()

                    listac = listacurso.values('id', 'participante__id',
                                                               'participante__apellido1',
                                                               'participante__apellido2',
                                                               'participante__nombres').filter(
                    participante__status=True, status=True).exclude(
                    participante__idusermoodle__in=listadosmoodle).order_by(
                    'participante__apellido1',
                    'participante__apellido2',
                    'participante__nombres')
                    cursor.close()
                    return JsonResponse({"result": "ok", "cantidad": len(listac),
                                         "listacurso": list(listac)})
                else:
                    return JsonResponse({"result":"bad", "mensaje": u"Asigne un modelo evaluativo al evento"})
            except Exception as ex:
                transaction.set_rollback(True)
                eline = 'Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, ex)
                return JsonResponse({"result": "bad", "mensaje": u"Error al verificar listado. %s" % eline})

        elif action == 'exportarinscrito':
            try:
                contador = int(request.POST['contador'])
                inscrito = int(request.POST['inscrito'])
                instructor = CapInstructorDocente.objects.get(status=True, pk=request.POST['idinstructor'])
                grupo = instructor.capeventoperiodo
                codigointegrante = grupo.capcabecerasolicituddocente_set.get(pk=inscrito, status=True)
                codigointegrante.encursomoodle = True
                codigointegrante.save(request)
                instructor.crear_curso_moodle(inscrito, contador)
                time.sleep(3)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                print(ex)
                print('Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, ex))
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos.%s" % ('Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, ex))})

        elif action == 'reporte_asistencia':
            try:
                persona_cargo_tercernivel=None
                revisadotercernivel=None
                aprobado1tercernivel=None
                aprobado2tercernivel=None
                data['idp'] = request.POST['id']
                data['evento'] = evento = CapEventoPeriodoDocente.objects.get(status=True, id=int(request.POST['id']))
                data['fechas'] = fechas = evento.todas_fechas_asistencia()
                lista_fechas = CapCabeceraAsistenciaDocente.objects.values_list("fecha").filter(clase__capeventoperiodo=evento).distinct('fecha').order_by('fecha')
                contarcolumnas= CapCabeceraAsistenciaDocente.objects.filter(Q(clase__capeventoperiodo=evento)& Q(fecha__in=lista_fechas)).count()+6
                data['vertical_horizontal']= True if contarcolumnas>10 else False
                data['ubicacion_promedio'] = contarcolumnas-3
                data['elabora_persona'] = persona
                cargo=None
                if DistributivoPersona.objects.values('id').filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,status=True).exists():
                    cargo = DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,status=True)[0]
                data['persona_cargo'] = cargo
                titulo = persona.titulacion_principal_senescyt_registro()
                # if not titulo == '':
                #     titulo_3 = persona.titulacion_set.filter(titulo__nivel=3).order_by( '-fechaobtencion') if titulo.titulo.nivel_id == 2 else None
                #     titulo_4 = persona.titulacion_set.filter(titulo__nivel=4).order_by('-fechaobtencion') if titulo.titulo.nivel_id == 2 else None
                #     if titulo_4:
                #         titulo = titulo_4[0]
                #     elif titulo_3:
                #         titulo = titulo_3[0]
                # if not titulo == '':
                #     persona_cargo_tercernivel = persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[0] if titulo.titulo.nivel_id == 4 else None
                persona_cargo_tercernivel = persona.nombre_titulomaximo()
                data['persona_cargo_titulo'] = titulo
                revisado = ''
                if evento.revisado:
                    revisado = evento.revisado.titulacion_principal_senescyt_registro()
                data['revisado'] = revisado
                revisadotercernivel = ''
                if evento.revisado:
                    # if evento.revisado.titulacion_set.filter(titulo__nivel=3):
                    #     revisadotercernivel= evento.revisado.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[0] if revisado.titulo.nivel_id == 4 else None
                    revisadotercernivel = evento.revisado.nombre_titulomaximo()
                data['aprobado1'] = aprobado1 = evento.aprobado1.titulacion_principal_senescyt_registro()
                if aprobado1:
                    # if evento.aprobado1.titulacion_set.filter(titulo__nivel=3):
                    #     aprobado1tercernivel = evento.aprobado1.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[0] if aprobado1.titulo.nivel_id == 4 else None
                    aprobado1tercernivel = evento.aprobado1.nombre_titulomaximo()
                data['aprobado2'] = aprobado2 = evento.aprobado2.titulacion_principal_senescyt_registro()
                if aprobado2:
                    # if evento.aprobado2.titulacion_set.filter(titulo__nivel=3):
                    #     aprobado2tercernivel= evento.aprobado2.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[0] if aprobado2.titulo.nivel_id == 4 else None
                    aprobado2tercernivel = evento.aprobado2.nombre_titulomaximo()
                data['persona_cargo_tercernivel']=persona_cargo_tercernivel
                data['revisadotercernivel']=revisadotercernivel
                data['aprobado1tercernivel']=aprobado1tercernivel
                data['aprobado2tercernivel']=aprobado2tercernivel
                ultima_fecha=fechas.order_by('-fecha')[0].fecha
                if ultima_fecha.weekday() >= 0 and ultima_fecha.weekday() <= 3 or ultima_fecha.weekday() == 6:
                    dias = timedelta(days=1)
                else:
                    dias = timedelta(days=2)
                data['fecha_corte'] = ultima_fecha + dias
                return conviert_html_to_pdf('adm_capacitaciondocente/gestion/informe_asistencia_pdf.html',{'pagesize': 'A4', 'data': data})
            except Exception as ex:
                pass

        elif action == 'ver_certificado_pdf':
            try:
                persona_cargo_tercernivel = None
                cargo = None
                tamano = 0
                data['tiposubrogante'] = None
                cabecera = CapCabeceraSolicitudDocente.objects.get(status=True, id=int(request.POST['id']))
                subrog = CapConfiguracionDocente.objects.first()
                data['evento'] = evento = cabecera.capeventoperiodo
                evento.aprobado1 = subrog.aprobado1
                evento.aprobado2 = subrog.aprobado2
                evento.aprobado3 = subrog.aprobado3
                if subrog.essubrogante and subrog.tiposubrogante not in [None, '', ""] and  data['tiposubrogante'] is None:
                    setattr(evento, subrog.tiposubrogante, subrog.personasubrogante)
                    data['tiposubrogante'] = subrog.tiposubrogante
                # data['facilitador'] = evento.capinstructordocente_set.filter(status=True, instructorprincipal=True)
                data['facilitador'] = CapInstructorDocente.objects.filter(status=True, capeventoperiodo=evento)
                data['listadofirmas'] = listadofirmas = cabecera.capeventoperiodo.capeventoperiodofirmasdocente_set.filter(status=True)
                firma1 = None
                firma2 = None
                firma3 = None
                firma4= None
                if listadofirmas.filter(tipofirmaevento=1):
                    firma1 = listadofirmas.filter(tipofirmaevento=1)[0]
                if listadofirmas.filter(tipofirmaevento=2):
                    firma2 = listadofirmas.filter(tipofirmaevento=2)[0]
                if listadofirmas.filter(tipofirmaevento=3):
                    firma3 = listadofirmas.filter(tipofirmaevento=3)[0]
                if listadofirmas.filter(tipofirmaevento=4):
                    firma4 = listadofirmas.filter(tipofirmaevento=4)[0]
                data['firma1'] = firma1
                data['firma2'] = firma2
                data['firma3'] = firma3
                data['firma4'] = firma4

                evento.actualizar_folio()
                data['elabora_persona'] = persona
                if DistributivoPersona.objects.values('id').filter(persona_id=persona,estadopuesto__id=PUESTO_ACTIVO_ID,status=True).exists():
                    cargo = DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,status=True)[0]
                data['persona_cargo'] = cargo
                titulo = persona.titulacion_principal_senescyt_registro()
                if not titulo == '':
                    titulo_3 = persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion') if titulo.titulo.nivel_id == 2 else None
                    titulo_4 = persona.titulacion_set.filter(titulo__nivel=4).order_by('-fechaobtencion') if titulo.titulo.nivel_id == 2 else None
                    if titulo_4:
                        titulo = titulo_4[0]
                    elif titulo_3:
                        titulo = titulo_3[0]
                if not titulo == '':
                    persona_cargo_tercernivel = persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[0] if titulo.titulo.nivel_id == 4 else None
                data['persona_cargo_titulo'] = titulo
                data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
                data['inscrito'] = cabecera
                mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre","octubre", "noviembre", "diciembre"]

                fechainicio = evento.fechainicio
                fechafin = evento.fechafin
                fechacertificado = suma_dias_habiles(fechafin, 7)
                data['fecha'] = u"Milagro, %s de %s del %s" % (fechacertificado.day, str(mes[fechacertificado.month - 1]), fechacertificado.year)
                if fechainicio == fechafin:
                    fechascapacitacion = "el %s de %s del %s" % (fechainicio.day, str(mes[fechainicio.month - 1]), fechainicio.year)
                elif fechainicio.month != fechafin.month:
                    if fechainicio.year == fechafin.year:
                        fechascapacitacion = "del %s de %s al %s de %s del %s" % (fechainicio.day, str(mes[fechainicio.month - 1]), fechafin.day, str(mes[fechafin.month - 1]), fechafin.year)
                    else:
                        fechascapacitacion = "del %s de %s del %s al %s de %s del %s" % (fechainicio.day, str(mes[fechainicio.month - 1]), fechainicio.year, fechafin.day, str(mes[fechafin.month - 1]), fechafin.year)
                else:
                    fechascapacitacion = "del %s al %s de %s del %s" % (fechainicio.day, fechafin.day, str(mes[fechainicio.month - 1]), fechainicio.year)
                data['fechascapacitacion'] = fechascapacitacion
                data['listado_contenido'] = listado = evento.contenido.split("\n")
                if evento.objetivo.__len__() < 290:
                    if listado.__len__() < 21:
                        tamano = 120
                    elif listado.__len__() < 35:
                        tamano = 100
                    elif listado.__len__() < 41:
                        tamano = 70
                data['controlar_bajada_logo'] = tamano
                viceacad=None
                if DistributivoPersona.objects.filter(denominacionpuesto_id=115, estadopuesto_id=1, status=True).exists():
                    viceacad = DistributivoPersona.objects.get(denominacionpuesto_id=115, estadopuesto_id=1, status=True)
                data['viceacad'] = viceacad
                url_path = data['url_path'] = 'http://127.0.0.1:8000'
                if not DEBUG:
                    url_path = data['url_path'] = 'https://sga.unemi.edu.ec'


                qrname = 'capins_qr_certificado_' + str(cabecera.id)
                # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
                # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                if os.path.isfile(rutapdf):
                    os.remove(rutaimg)
                    os.remove(rutapdf)
                url = pyqrcode.create(f'{url_path}//media/qrcode/certificados/' + qrname + '.pdf')
                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                data['qrname'] = 'qr' + qrname
                data['url_qr'] = f'{url_path}/media/qrcode/certificados/qr{qrname}.png'

                d = datetime.now()
                data['horasegundo'] = d.strftime('%Y%m%d_%H%M%S')
                return conviert_html_to_pdf(
                    'adm_capacitaciondocente/gestion/certificado_individual_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )

            except Exception as ex:
                pass

        elif action == 'ver_certificadoinstructor_pdf':
            try:
                persona_cargo_tercernivel = None
                cargo = None
                tamano = 0
                data['tiposubrogante'] = None
                facilitador = CapInstructorDocente.objects.get(status=True, id=int(request.POST['id']))
                data['evento'] = evento = facilitador.capeventoperiodo
                subrog = CapConfiguracionDocente.objects.first()
                evento.aprobado1 = subrog.aprobado1
                evento.aprobado2 = subrog.aprobado2
                evento.aprobado3 = subrog.aprobado3
                if subrog.essubrogante and subrog.tiposubrogante not in [None, '', ""] and data[
                    'tiposubrogante'] is None:
                    setattr(evento, subrog.tiposubrogante, subrog.personasubrogante)
                    data['tiposubrogante'] = subrog.tiposubrogante
                data['listadofirmas'] = listadofirmas = facilitador.capeventoperiodo.capeventoperiodofirmasdocente_set.filter(status=True)
                firma1 = None
                firma2 = None
                firma3 = None
                firma4= None
                if listadofirmas.filter(tipofirmaevento=1):
                    firma1 = listadofirmas.filter(tipofirmaevento=1)[0]
                if listadofirmas.filter(tipofirmaevento=2):
                    firma2 = listadofirmas.filter(tipofirmaevento=2)[0]
                if listadofirmas.filter(tipofirmaevento=3):
                    firma3 = listadofirmas.filter(tipofirmaevento=3)[0]
                if listadofirmas.filter(tipofirmaevento=4):
                    firma4 = listadofirmas.filter(tipofirmaevento=4)[0]
                data['firma1'] = firma1
                data['firma2'] = firma2
                data['firma3'] = firma3
                data['firma4'] = firma4

                data['elabora_persona'] = persona
                if DistributivoPersona.objects.values('id').filter(persona_id=persona,estadopuesto__id=PUESTO_ACTIVO_ID,status=True).exists():
                    cargo = DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,status=True)[0]
                data['persona_cargo'] = cargo
                titulo = persona.titulacion_principal_senescyt_registro()
                if not titulo == '':
                    titulo_3 = persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion') if titulo.titulo.nivel_id == 2 else None
                    titulo_4 = persona.titulacion_set.filter(titulo__nivel=4).order_by('-fechaobtencion') if titulo.titulo.nivel_id == 2 else None
                    if titulo_4:
                        titulo = titulo_4[0]
                    elif titulo_3:
                        titulo = titulo_3[0]
                if not titulo == '':
                    persona_cargo_tercernivel = persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[0] if titulo.titulo.nivel_id == 4 else None
                data['persona_cargo_titulo'] = titulo
                data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
                data['facilitador'] = facilitador
                mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre","octubre", "noviembre", "diciembre"]

                fechainicio = evento.fechainicio
                fechafin = evento.fechafin
                fechacertificado = suma_dias_habiles(fechafin, 7)
                data['fecha'] = u"Milagro, %s de %s del %s" % (fechacertificado.day, str(mes[fechacertificado.month - 1]), fechacertificado.year)
                if fechainicio == fechafin:
                    fechascapacitacion = "el %s de %s del %s" % (fechainicio.day, str(mes[fechainicio.month - 1]), fechainicio.year)
                elif fechainicio.month != fechafin.month:
                    if fechainicio.year == fechafin.year:
                        fechascapacitacion = "del %s de %s al %s de %s del %s" % (fechainicio.day, str(mes[fechainicio.month - 1]), fechafin.day, str(mes[fechafin.month - 1]), fechafin.year)
                    else:
                        fechascapacitacion = "del %s de %s del %s al %s de %s del %s" % (fechainicio.day, str(mes[fechainicio.month - 1]), fechainicio.year, fechafin.day, str(mes[fechafin.month - 1]), fechafin.year)
                else:
                    fechascapacitacion = "del %s al %s de %s del %s" % (fechainicio.day, fechafin.day, str(mes[fechainicio.month - 1]), fechainicio.year)
                data['fechascapacitacion'] = fechascapacitacion
                data['listado_contenido'] = listado = evento.contenido.split("\n")
                if evento.objetivo.__len__() < 290:
                    if listado.__len__() < 21:
                        tamano = 120
                    elif listado.__len__() < 35:
                        tamano = 100
                    elif listado.__len__() < 41:
                        tamano = 70
                data['controlar_bajada_logo'] = tamano
                viceacad=None
                if DistributivoPersona.objects.filter(denominacionpuesto_id=115, estadopuesto_id=1, status=True).exists():
                    viceacad = DistributivoPersona.objects.get(denominacionpuesto_id=115, estadopuesto_id=1, status=True)
                data['viceacad'] = viceacad
                url_path = data['url_path'] = 'http://127.0.0.1:8000'
                if not DEBUG:
                    url_path = data['url_path'] = 'https://sga.unemi.edu.ec'


                d = datetime.now()
                data['horasegundo'] = d.strftime('%Y%m%d_%H%M%S')

                qrname = 'capins_qr_certificado_' + str(facilitador.id)
                # folder = SITE_STORAGE + 'media/qrcode/certificados_capacitacion_facilitadores/'
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados_capacitacion_facilitadores',''))
                # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados_capacitacion_facilitadores')
                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                if os.path.isfile(rutapdf):
                    os.remove(rutaimg)
                    os.remove(rutapdf)
                url = pyqrcode.create(f'{url_path}//media/qrcode/certificados_capacitacion_facilitadores/' + qrname + '.pdf')
                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                data['qrname'] = qrname
                data['url_qr'] = f'{url_path}/media/qrcode/certificados_capacitacion_facilitadores/qr{qrname}.png'


                return conviert_html_to_pdfsaveqrcertificadocapacitacioninstructor(
                    'adm_capacitaciondocente/gestion/certificado_facilitador_pdf.html',
                    {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                )

            except Exception as ex:
                pass

        elif action == 'generar_certificado_pdf':
            try:
                persona_cargo_tercernivel=None
                cargo = None
                tamano=0
                data['tiposubrogante'] = None
                cabecera = CapCabeceraSolicitudDocente.objects.get(status=True, id=int(request.POST['id']))
                data['evento'] = evento = cabecera.capeventoperiodo
                subrog = CapConfiguracionDocente.objects.first()
                evento.aprobado1 = subrog.aprobado1
                evento.aprobado2 = subrog.aprobado2
                evento.aprobado3 = subrog.aprobado3
                if subrog.essubrogante and subrog.tiposubrogante not in [None, '', ""] and data[
                    'tiposubrogante'] is None:
                    setattr(evento, subrog.tiposubrogante, subrog.personasubrogante)
                    data['tiposubrogante'] = subrog.tiposubrogante
                data['facilitador'] = evento.capinstructordocente_set.filter(status=True)
                data['listadofirmas'] = listadofirmas = cabecera.capeventoperiodo.capeventoperiodofirmasdocente_set.filter(status=True)
                firma1 = None
                firma2 = None
                firma3 = None
                firma4 = None
                if listadofirmas.filter(tipofirmaevento=1):
                    firma1 = listadofirmas.filter(tipofirmaevento=1)[0]
                if listadofirmas.filter(tipofirmaevento=2):
                    firma2 = listadofirmas.filter(tipofirmaevento=2)[0]
                if listadofirmas.filter(tipofirmaevento=3):
                    firma3 = listadofirmas.filter(tipofirmaevento=3)[0]
                if listadofirmas.filter(tipofirmaevento=4):
                    firma4 = listadofirmas.filter(tipofirmaevento=4)[0]
                data['firma1'] = firma1
                data['firma2'] = firma2
                data['firma3'] = firma3
                data['firma4'] = firma4

                evento.actualizar_folio()
                firmacertificado = 'robles'
                fechacambio = (datetime(2019, 11, 1, 0, 0, 0)).date()
                if evento.fechafin >= fechacambio:
                    firmacertificado = 'firmaguillermo'
                data['firmacertificado'] = firmacertificado
                data['elabora_persona'] = persona
                if DistributivoPersona.objects.values('id').filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,status=True).exists():
                    cargo = DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,status=True)[0]
                data['persona_cargo'] = cargo
                titulo = persona.titulacion_principal_senescyt_registro()
                if not titulo == '':
                    titulo_3 = persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion') if titulo.titulo.nivel_id == 2 else None
                    titulo_4 = persona.titulacion_set.filter(titulo__nivel=4).order_by('-fechaobtencion') if titulo.titulo.nivel_id == 2 else None
                    if titulo_4:
                        titulo = titulo_4[0]
                    elif titulo_3:
                        titulo = titulo_3[0]
                if not titulo == '':
                    persona_cargo_tercernivel = persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[0] if titulo.titulo.nivel_id == 4 else None
                data['persona_cargo_titulo'] = titulo
                data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
                data['inscrito'] = cabecera
                mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre","octubre", "noviembre", "diciembre"]
                fechainicio = evento.fechainicio
                fechafin = evento.fechafin
                fechacertificado = suma_dias_habiles(fechafin, 7)
                data['fecha'] = u"Milagro, %s de %s del %s" % (
                    fechacertificado.day, str(mes[fechacertificado.month - 1]), fechacertificado.year)
                if fechainicio == fechafin:
                    fechascapacitacion = "el %s de %s del %s" % (
                        fechainicio.day, str(mes[fechainicio.month - 1]), fechainicio.year)
                elif fechainicio.month != fechafin.month:
                    if fechainicio.year == fechafin.year:
                        fechascapacitacion = "del %s de %s al %s de %s del %s" % (
                            fechainicio.day, str(mes[fechainicio.month - 1]), fechafin.day, str(mes[fechafin.month - 1]),
                            fechafin.year)
                    else:
                        fechascapacitacion = "del %s de %s del %s al %s de %s del %s" % (
                            fechainicio.day, str(mes[fechainicio.month - 1]), fechainicio.year, fechafin.day,
                            str(mes[fechafin.month - 1]), fechafin.year)
                else:
                    fechascapacitacion = "del %s al %s de %s del %s" % (
                        fechainicio.day, fechafin.day, str(mes[fechainicio.month - 1]), fechainicio.year)
                data['fechascapacitacion'] = fechascapacitacion
                data['listado_contenido'] = listado = evento.contenido.split("\n")
                if evento.objetivo.__len__()<290:
                    if listado.__len__() < 21:
                        tamano = 120
                    elif listado.__len__() < 35:
                        tamano = 100
                    elif listado.__len__() < 41:
                        tamano = 70
                data['controlar_bajada_logo'] = tamano
                viceacad=None
                if DistributivoPersona.objects.filter(denominacionpuesto_id=115, estadopuesto_id=1, status=True).exists():
                    viceacad = DistributivoPersona.objects.get(denominacionpuesto_id=115, estadopuesto_id=1, status=True)
                data['viceacad'] = viceacad
                data['url_path'] = 'http://127.0.0.1:8000'
                if not DEBUG:
                    data['url_path'] = 'https://sga.unemi.edu.ec'

                qrname = 'perf_qr_certificado_' + str(cabecera.id)
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                if os.path.isfile(rutapdf):
                    os.remove(rutaimg)
                    os.remove(rutapdf)
                url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/certificados/' + qrname + '.pdf')
                # imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                data['qrname'] = 'qr' + qrname
                valida, pdf, result = conviert_html_to_pdfsaveqrcertificado_v2(
                    'adm_capacitaciondocente/gestion/certificado_individual_pdf.html',
                    {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                )

                if valida:
                    return HttpResponse(result.getvalue(), content_type='application/pdf')
                else:
                    raise NameError('Error al generar certificado')
            except Exception as ex:
                pass

        elif action == 'enviar_certificado_pdf':
            try:
                persona_cargo_tercernivel=None
                cargo = None
                tamano=0
                data['tiposubrogante'] = None
                cabecera = CapCabeceraSolicitudDocente.objects.get(status=True, id=int(request.POST['id']))
                data['evento'] = evento = cabecera.capeventoperiodo
                subrog = CapConfiguracionDocente.objects.first()
                evento.aprobado1 = subrog.aprobado1
                evento.aprobado2 = subrog.aprobado2
                evento.aprobado3 = subrog.aprobado3
                if subrog.essubrogante and subrog.tiposubrogante not in [None, '', ""] and data[
                    'tiposubrogante'] is None:
                    setattr(evento, subrog.tiposubrogante, subrog.personasubrogante)
                    data['tiposubrogante'] = subrog.tiposubrogante
                data['facilitador'] = evento.capinstructordocente_set.filter(status=True)
                data['listadofirmas'] = listadofirmas = cabecera.capeventoperiodo.capeventoperiodofirmasdocente_set.filter(status=True)
                firma1 = None
                firma2 = None
                firma3 = None
                firma4 = None
                if listadofirmas.filter(tipofirmaevento=1):
                    firma1 = listadofirmas.filter(tipofirmaevento=1)[0]
                if listadofirmas.filter(tipofirmaevento=2):
                    firma2 = listadofirmas.filter(tipofirmaevento=2)[0]
                if listadofirmas.filter(tipofirmaevento=3):
                    firma3 = listadofirmas.filter(tipofirmaevento=3)[0]
                if listadofirmas.filter(tipofirmaevento=4):
                    firma4 = listadofirmas.filter(tipofirmaevento=4)[0]
                data['firma1'] = firma1
                data['firma2'] = firma2
                data['firma3'] = firma3
                data['firma4'] = firma4

                evento.actualizar_folio()
                firmacertificado = 'robles'
                fechacambio = (datetime(2019, 11, 1, 0, 0, 0)).date()
                if evento.fechafin >= fechacambio:
                    firmacertificado = 'firmaguillermo'
                data['firmacertificado'] = firmacertificado
                data['elabora_persona'] = persona
                if DistributivoPersona.objects.values('id').filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,status=True).exists():
                    cargo = DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,status=True)[0]
                data['persona_cargo'] = cargo
                titulo = persona.titulacion_principal_senescyt_registro()
                if not titulo == '':
                    titulo_3 = persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion') if titulo.titulo.nivel_id == 2 else None
                    titulo_4 = persona.titulacion_set.filter(titulo__nivel=4).order_by('-fechaobtencion') if titulo.titulo.nivel_id == 2 else None
                    if titulo_4:
                        titulo = titulo_4[0]
                    elif titulo_3:
                        titulo = titulo_3[0]
                if not titulo == '':
                    persona_cargo_tercernivel = persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[0] if titulo.titulo.nivel_id == 4 else None
                data['persona_cargo_titulo'] = titulo
                data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
                data['inscrito'] = cabecera
                mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre","octubre", "noviembre", "diciembre"]
                fechainicio = evento.fechainicio
                fechafin = evento.fechafin
                fechacertificado = suma_dias_habiles(fechafin, 7)
                data['fecha'] = u"Milagro, %s de %s del %s" % (
                    fechacertificado.day, str(mes[fechacertificado.month - 1]), fechacertificado.year)
                if fechainicio == fechafin:
                    fechascapacitacion = "el %s de %s del %s" % (
                        fechainicio.day, str(mes[fechainicio.month - 1]), fechainicio.year)
                elif fechainicio.month != fechafin.month:
                    if fechainicio.year == fechafin.year:
                        fechascapacitacion = "del %s de %s al %s de %s del %s" % (
                            fechainicio.day, str(mes[fechainicio.month - 1]), fechafin.day, str(mes[fechafin.month - 1]),
                            fechafin.year)
                    else:
                        fechascapacitacion = "del %s de %s del %s al %s de %s del %s" % (
                            fechainicio.day, str(mes[fechainicio.month - 1]), fechainicio.year, fechafin.day,
                            str(mes[fechafin.month - 1]), fechafin.year)
                else:
                    fechascapacitacion = "del %s al %s de %s del %s" % (
                        fechainicio.day, fechafin.day, str(mes[fechainicio.month - 1]), fechainicio.year)
                data['fechascapacitacion'] = fechascapacitacion
                data['listado_contenido'] = listado = evento.contenido.split("\n")
                if evento.objetivo.__len__() < 290:
                    if listado.__len__() < 21:
                        tamano = 120
                    elif listado.__len__() < 35:
                        tamano = 100
                    elif listado.__len__() < 41:
                        tamano = 70
                data['controlar_bajada_logo'] = tamano
                viceacad=None
                if DistributivoPersona.objects.filter(denominacionpuesto_id=115, estadopuesto_id=1, status=True).exists():
                    viceacad = DistributivoPersona.objects.get(denominacionpuesto_id=115, estadopuesto_id=1, status=True)
                data['viceacad'] = viceacad
                url_path = data['url_path'] = 'http://127.0.0.1:8000'
                if not DEBUG:
                    url_path = data['url_path'] = 'https://sga.unemi.edu.ec'

                qrname = 'capins_qr_certificado_' + str(cabecera.id)
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                if os.path.isfile(rutapdf):
                    os.remove(rutaimg)
                    os.remove(rutapdf)
                url = pyqrcode.create(f'{url_path}//media/qrcode/certificados/' + qrname + '.pdf')
                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                data['qrname'] = 'qr' + qrname
                data['url_path'] = url_path = 'http://127.0.0.1:8000'
                if not DEBUG:
                    data['url_path'] = url_path = 'https://sga.unemi.edu.ec'

                d = datetime.now()
                data['horasegundo'] = d.strftime('%Y%m%d_%H%M%S')

                valida = conviert_html_to_pdfsaveqrcertificado(
                    'adm_capacitaciondocente/gestion/certificado_individual_pdf.html',
                    {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                )
                if not valida:
                    raise NameError("Problemas al ejecutar el reporte.")
                # os.remove(rutaimg)
                cabecera.rutapdf = 'qrcode/certificados/' + qrname + '.pdf'
                cabecera.notificado = True
                cabecera.fechanotifica = datetime.now()
                cabecera.personanotifica = persona
                fecha = datetime.now().date()
                hora = datetime.now().time()
                fecha_hora = fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__()
                token = md5(str(encrypt(cabecera.id) + fecha_hora).encode("utf-8")).hexdigest()
                if not cabecera.token:
                    cabecera.token = token
                cabecera.save(request)
                if DEBUG:
                    cabecera.mail_notificar_certificado(request.session['nombresistema'])
                    time.sleep(5)
                data['cabecera'] = cabecera
                template = get_template("adm_capacitaciondocente/gestion/modal/dataenviocertificado.html")
                return JsonResponse({"result": True, 'data': template.render(data)})
            except Exception as ex:
                return JsonResponse({"result": False, "mensaje": f"{ex.__str__()}"})

        elif action == 'enviar_certificadofacilitador_pdf':
            try:
                persona_cargo_tercernivel = None
                cargo = None
                tamano = 0
                data['tiposubrogante'] = None
                facilitador = CapInstructorDocente.objects.get(status=True, id=int(request.POST['id']))
                data['evento'] = evento = facilitador.capeventoperiodo
                subrog = CapConfiguracionDocente.objects.first()
                evento.aprobado1 = subrog.aprobado1
                evento.aprobado2 = subrog.aprobado2
                evento.aprobado3 = subrog.aprobado3
                if subrog.essubrogante and subrog.tiposubrogante not in [None, '', ""] and data[
                    'tiposubrogante'] is None:
                    setattr(evento, subrog.tiposubrogante, subrog.personasubrogante)
                    data['tiposubrogante'] = subrog.tiposubrogante
                data['listadofirmas'] = listadofirmas = facilitador.capeventoperiodo.capeventoperiodofirmasdocente_set.filter(status=True)
                firma1 = None
                firma2 = None
                firma3 = None
                firma4 = None
                if listadofirmas.filter(tipofirmaevento=1):
                    firma1 = listadofirmas.filter(tipofirmaevento=1)[0]
                if listadofirmas.filter(tipofirmaevento=2):
                    firma2 = listadofirmas.filter(tipofirmaevento=2)[0]
                if listadofirmas.filter(tipofirmaevento=3):
                    firma3 = listadofirmas.filter(tipofirmaevento=3)[0]
                if listadofirmas.filter(tipofirmaevento=4):
                    firma4 = listadofirmas.filter(tipofirmaevento=4)[0]
                data['firma1'] = firma1
                data['firma2'] = firma2
                data['firma3'] = firma3
                data['firma4'] = firma4

                data['elabora_persona'] = persona
                if DistributivoPersona.objects.values('id').filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID, status=True).exists():
                    cargo = DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID, status=True)[0]
                data['persona_cargo'] = cargo
                titulo = persona.titulacion_principal_senescyt_registro()
                if not titulo == '':
                    titulo_3 = persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion') if titulo.titulo.nivel_id == 2 else None
                    titulo_4 = persona.titulacion_set.filter(titulo__nivel=4).order_by('-fechaobtencion') if titulo.titulo.nivel_id == 2 else None
                    if titulo_4:
                        titulo = titulo_4[0]
                    elif titulo_3:
                        titulo = titulo_3[0]
                if not titulo == '':
                    persona_cargo_tercernivel = persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[0] if titulo.titulo.nivel_id == 4 else None
                data['persona_cargo_titulo'] = titulo
                data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
                data['facilitador'] = facilitador
                mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

                fechainicio = evento.fechainicio
                fechafin = evento.fechafin
                fechacertificado = suma_dias_habiles(fechafin, 7)
                data['fecha'] = u"Milagro, %s de %s del %s" % (fechacertificado.day, str(mes[fechacertificado.month - 1]), fechacertificado.year)
                if fechainicio == fechafin:
                    fechascapacitacion = "el %s de %s del %s" % (fechainicio.day, str(mes[fechainicio.month - 1]), fechainicio.year)
                elif fechainicio.month != fechafin.month:
                    if fechainicio.year == fechafin.year:
                        fechascapacitacion = "del %s de %s al %s de %s del %s" % (fechainicio.day, str(mes[fechainicio.month - 1]), fechafin.day, str(mes[fechafin.month - 1]), fechafin.year)
                    else:
                        fechascapacitacion = "del %s de %s del %s al %s de %s del %s" % (fechainicio.day, str(mes[fechainicio.month - 1]), fechainicio.year, fechafin.day, str(mes[fechafin.month - 1]), fechafin.year)
                else:
                    fechascapacitacion = "del %s al %s de %s del %s" % (fechainicio.day, fechafin.day, str(mes[fechainicio.month - 1]), fechainicio.year)
                data['fechascapacitacion'] = fechascapacitacion
                data['listado_contenido'] = listado = evento.contenido.split("\n")
                if evento.objetivo.__len__() < 290:
                    if listado.__len__() < 21:
                        tamano = 120
                    elif listado.__len__() < 35:
                        tamano = 100
                    elif listado.__len__() < 41:
                        tamano = 70
                data['controlar_bajada_logo'] = tamano
                viceacad = None
                if DistributivoPersona.objects.filter(denominacionpuesto_id=115, estadopuesto_id=1, status=True).exists():
                    viceacad = DistributivoPersona.objects.get(denominacionpuesto_id=115, estadopuesto_id=1, status=True)
                data['viceacad'] = viceacad
                data['url_path'] = 'http://127.0.0.1:8000'
                if not DEBUG:
                    data['url_path'] = 'https://sga.unemi.edu.ec'
                d = datetime.now()
                data['horasegundo'] = d.strftime('%Y%m%d_%H%M%S')

                qrname = 'qr_certificado_' + str(facilitador.id)
                # folder = SITE_STORAGE + 'media/qrcode/certificados_capacitacion_facilitadores/'
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados_capacitacion_facilitadores', ''))
                # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados_capacitacion_facilitadores')
                try:
                    os.stat(folder)
                except:
                    os.mkdir(folder)
                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                # if os.path.isfile(rutapdf):
                #     # os.remove(rutaimg)
                #     os.remove(rutapdf)

                url = pyqrcode.create(
                    'http://sga.unemi.edu.ec//media/qrcode/certificados_capacitacion_facilitadores/' + qrname + '.pdf')
                # url = pyqrcode.create('http://127.0.0.1:8000//media/qrcode/certificados_capacitacion_facilitadores/' + qrname + '.pdf')
                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                data['qrname'] = qrname

                valida = conviert_html_to_pdfsaveqrcertificadocapacitacioninstructor(
                    'adm_capacitaciondocente/gestion/certificado_facilitador_pdf.html',
                    {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                )

                if valida:
                    # os.remove(rutaimg)
                    facilitador.rutapdf = 'qrcode/certificados_capacitacion_facilitadores/' + qrname + '.pdf'
                    facilitador.notificado = True
                    facilitador.fechanotifica = datetime.now()
                    facilitador.personanotifica = persona
                    facilitador.save(request)
                    asunto = u"CERTIFICADO - " + facilitador.capeventoperiodo.capevento.nombre
                    send_html_mail(asunto,
                                   "emails/notificar_certificado_facilitador_docente.html",
                                   {'sistema': request.session['nombresistema'],
                                    'facilitador': facilitador,
                                    'evento': evento
                                    },
                                   #micorreo.lista_emails_envio(),
                                   facilitador.instructor.lista_emails_envio(),
                                   [],
                                   [facilitador.rutapdf],
                                   cuenta=CUENTAS_CORREOS[1][1])

                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte."})

            except Exception as ex:
                pass

        elif action == 'moverinscrito':
            try:
                form = MoverInscritoEventoCapacitacionForm(request.POST)
                if form.is_valid():
                    inscrito = CapCabeceraSolicitudDocente.objects.get(pk=int(request.POST['id']))
                    if CapCabeceraSolicitudDocente.objects.filter(status=True, participante=inscrito.participante,
                                                      capeventoperiodo_id=int(request.POST['curso'])).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra inscrito"})
                    if not CapEventoPeriodoDocente.objects.get(pk=int(request.POST['curso'])).hay_cupo_inscribir():
                        return JsonResponse({"result": "bad", "mensaje": u"No hay cupo para continuar adicionando"})

                    # if CapCabeceraAsistenciaDocente.objects.filter(clase__capeventoperiodo=inscrito.capeventoperiodo,
                    #                                                capdetalleasistenciadocente__isnull=False,
                    #                                                capdetalleasistenciadocente__cabecerasolicitud=inscrito).exists():
                    #     cabeceraasistencias = CapCabeceraAsistenciaDocente.objects.filter(clase__capeventoperiodo=inscrito.capeventoperiodo,
                    #                                                                       capdetalleasistenciadocente__isnull=False,
                    #                                                                       capdetalleasistenciadocente__cabecerasolicitud=inscrito)

                        # for cabasist in cabeceraasistencias:
                        #     cabasist.clase.capeventoperiodo = form.cleaned_data['curso']
                        #     cabasist.save(request)


                    inscrito.observacionmover = form.cleaned_data['observacion']
                    inscrito.capeventoperiodo = form.cleaned_data['curso']
                    inscrito.save(request)

                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'updatenota':
            try:
                detalle = CapDetalleNotaDocente.objects.get(pk=int(request.POST['id']))
                nota = float(request.POST['vc'])
                if not nota:
                    nota = 0
                cupoanterior = detalle.nota
                detalle.nota = nota
                detalle.save(request)
                cabecera = CapCabeceraSolicitudDocente.objects.get(pk=detalle.inscrito.id)
                cabecera.notafinal = cabecera.nota_final_curso()
                cabecera.save()

                log(u'Actualizo nota en tarea de capacitacion docente: %s cupo anterior: %s cupo actual: %s' % (
                    detalle, str(cupoanterior), str(detalle.nota)), request, "edit")
                if 'idl' in request.POST:
                    capcabecerasolicituddocente = CapCabeceraSolicitudDocente.objects.get(pk=int(request.POST['idl']))
                    nofinal = capcabecerasolicituddocente.nota_total_porinstructor(
                        detalle.cabeceranota.instructor.capeventoperiodo.id, detalle.cabeceranota.instructor.pk)
                    return JsonResponse({'result': 'ok', 'valor': detalle.nota, 'nofinal': nofinal})
                else:
                    return JsonResponse({'result': 'ok', 'valor': detalle.nota})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u"Error al actualizar la nota."})

        elif action == 'observacion':
            try:
                detalle = CapDetalleNotaDocente.objects.get(pk=request.POST['id'])
                detalle.observacion = request.POST['valor']
                detalle.save(request)
                log(u'Actualizo observacion en tarea de capacitacion docente: %s ' % detalle.observacion, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        #INSTRUCTOR
        elif action == 'addinstructor':
            try:
                form = CapInstructorForm(request.POST)
                if form.is_valid():
                    if CapInstructorDocente.objects.values('id').filter(instructor=form.cleaned_data['instructor'],capeventoperiodo_id=int(request.POST['eventoperiodo']), status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                    instructor=CapInstructorDocente(capeventoperiodo_id=int(request.POST['eventoperiodo']),
                                                     instructor_id=form.cleaned_data['instructor'],
                                                     tipo= 1,
                                                     nombrecurso=form.cleaned_data['nombrecurso'],
                                                     descripcion=form.cleaned_data['descripcion'],
                                                     instructorprincipal=form.cleaned_data['instructorprincipal'])
                    instructor.save(request)
                    if form.cleaned_data['instructorprincipal']==True and CapInstructorDocente.objects.values('id').filter(capeventoperiodo=instructor.capeventoperiodo,status=True,instructorprincipal=True).exclude(pk=instructor.id).exists():
                        editarprincipales=CapInstructorDocente.objects.filter(capeventoperiodo=instructor.capeventoperiodo, status=True,instructorprincipal=True).exclude(pk=instructor.id)
                        for editarprincipal in editarprincipales:
                            editarprincipal.instructorprincipal=False
                            editarprincipal.save(request)
                            log(u'Edito Instructor Principan en Capacitacion Instructor Docente: %s - [%s]' % (editarprincipal, editarprincipal.id), request,"edit")
                    log(u'Agrego Capacitacion Instructor: %s - [%s]' % (instructor,instructor.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editinstructor':
            try:
                form = CapInstructorForm(request.POST)
                if form.is_valid():
                    instructor = CapInstructorDocente.objects.get(pk=int(request.POST['id']))
                    if CapInstructorDocente.objects.values('id').filter(instructor=form.cleaned_data['instructor'],capeventoperiodo=instructor.capeventoperiodo,status=True).exclude(pk=instructor.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                    if form.cleaned_data['instructorprincipal']==True and CapInstructorDocente.objects.values('id').filter(capeventoperiodo=instructor.capeventoperiodo,status=True,instructorprincipal=True).exclude(pk=instructor.id).exists():
                        editarprincipales=CapInstructorDocente.objects.filter(capeventoperiodo=instructor.capeventoperiodo, status=True,instructorprincipal=True).exclude(pk=instructor.id)
                        for editarprincipal in editarprincipales:
                            editarprincipal.instructorprincipal=False
                            editarprincipal.save(request)
                            log(u'Edito Instructor Principal en Capacitacion Instructor Docente: %s - [%s]' % (editarprincipal, editarprincipal.id), request, "edit")
                    instructor.instructor_id = form.cleaned_data['instructor']
                    #instructor.tipo = form.cleaned_data['tipo']
                    instructor.instructorprincipal = form.cleaned_data['instructorprincipal']
                    instructor.nombrecurso = form.cleaned_data['nombrecurso']
                    instructor.descripcion = form.cleaned_data['descripcion']
                    instructor.save(request)
                    log(u'Editar Capacitación Instructor Docente: %s - [%s]' % (instructor,instructor.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delinstructor':
            try:
                enfo = CapInstructorDocente.objects.get(pk=int(request.POST['id']))
                log(u'Elimino Capacitación InstructorDocente: %s' % enfo, request, "del")
                enfo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'verificarcedula':
            try:
                if Persona.objects.filter(cedula=request.POST["cedula"]).exists():
                    return JsonResponse({"result": "no"})
                else:
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad"})

        elif action == 'addpersona':
            try:
                form = CapInscribirPersonaCapacitacionForm(request.POST)
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError(v[0])
                if form.is_valid():
                    tipoidentificacion = int(form.cleaned_data['tipoidentificacion'])
                    if tipoidentificacion == 1:
                        if Persona.objects.filter(cedula=request.POST["cedula"]).exists():
                            return JsonResponse({"result": "no", "mensaje": u"Existe un usuario con la cédula digitada."})
                        persona = Persona(nombres=form.cleaned_data['nombres'],
                                          apellido1=form.cleaned_data['apellido1'],
                                          apellido2=form.cleaned_data['apellido2'],
                                          cedula=form.cleaned_data['cedula'],
                                          nacimiento=form.cleaned_data['nacimiento'],
                                          sexo=form.cleaned_data['sexo'],
                                          telefono=form.cleaned_data['telefono'],
                                          email=form.cleaned_data['email'],
                                          direccion=form.cleaned_data['direccion'],
                                          tipopersona=1)
                        persona.save(request)

                    elif tipoidentificacion == 2:
                        if Persona.objects.filter(pasaporte=request.POST["cedula"]).exists():
                            return JsonResponse({"result": "no", "mensaje": u"Existe un usuario con el pasaporte digitado."})
                        persona = Persona(nombres=form.cleaned_data['nombres'],
                                          apellido1=form.cleaned_data['apellido1'],
                                          apellido2=form.cleaned_data['apellido2'],
                                          pasaporte=form.cleaned_data['cedula'],
                                          nacimiento=form.cleaned_data['nacimiento'],
                                          sexo=form.cleaned_data['sexo'],
                                          telefono=form.cleaned_data['telefono'],
                                          email=form.cleaned_data['email'],
                                          direccion=form.cleaned_data['direccion'],
                                          tipopersona=1)
                        persona.save(request)

                    if int(request.POST['tipo']) == 1:
                        capeven = CapEventoPeriodoDocente.objects.get(id=int(request.POST['id']))
                        instructor = CapInstructorDocente(capeventoperiodo_id=capeven.id, instructor=persona, tipo=2)
                        instructor.save(request)
                        log(u'Adicionó nuevo instructor %s para la Capacitacion docente: %s' % (instructor, capeven),
                            request, "add")

                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        # HORARIOS
        elif action == 'addclase':
            try:
                form = CapClaseForm(request.POST)
                if form.is_valid():
                    periodo = CapEventoPeriodoDocente.objects.get(id=int(request.POST['cepid']))
                    if CapClaseDocente.objects.values('id').filter(capeventoperiodo_id=int(request.POST['cepid']),dia=form.cleaned_data['dia'], turno=form.cleaned_data['turno'],fechainicio=form.cleaned_data['fechainicio'],fechafin=form.cleaned_data['fechafin'], status=True).exists():
                        return JsonResponse({"result": "bad","mensaje": u"Hay una Clase que existe con las misma fechas y turno."})
                    if not form.cleaned_data['fechainicio'] >= periodo.periodo.fechainicio and form.cleaned_data['fechafin'] <= periodo.periodo.fechafin:
                        return JsonResponse({"result": "bad","mensaje": u"Las fecha no puede ser mayor a las fecha del periodo."})
                    if not form.cleaned_data['fechainicio'] <= form.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ser mayor la fecha de inicio."})
                    if form.cleaned_data['fechainicio'] == form.cleaned_data['fechafin']:
                        if not int(form.cleaned_data['dia']) == form.cleaned_data['fechainicio'].weekday()+1:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha no concuerdan con el dia."})
                    clase = CapClaseDocente(capeventoperiodo_id=int(request.POST['cepid']),
                                             turno=form.cleaned_data['turno'],
                                             dia=form.cleaned_data['dia'],
                                             fechainicio=form.cleaned_data['fechainicio'],
                                             fechafin=form.cleaned_data['fechafin'])
                    clase.save(request)
                    log(u'Adicionado horario de Evento Docente: %s' % clase, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editclase':
            try:
                form = CapClaseForm(request.POST)
                if form.is_valid():
                    clase = CapClaseDocente.objects.get(pk=int(request.POST['claseid']))
                    if CapClaseDocente.objects.values('id').filter(capeventoperiodo=clase.capeventoperiodo, dia=clase.dia,turno=clase.turno, fechainicio=form.cleaned_data['fechainicio'],fechafin=form.cleaned_data['fechafin'], status=True).exclude(pk=clase.id).exists():
                        return JsonResponse({"result": "bad","mensaje": u"Hay una Clase que existe con las misma fechas y turno."})
                    if not form.cleaned_data['fechainicio'] >= clase.capeventoperiodo.fechainicio and form.cleaned_data['fechafin'] <= clase.capeventoperiodo.fechafin:
                        return JsonResponse({"result": "bad","mensaje": u"Las fecha no puede ser mayor a las fecha del periodo."})
                    if not form.cleaned_data['fechainicio'] <= form.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ser mayor la fecha de inicio."})
                    if form.cleaned_data['fechainicio'] == form.cleaned_data['fechafin']:
                        if not clase.dia == form.cleaned_data['fechainicio'].weekday()+1:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha no concuerdan con el dia."})
                    clase.fechainicio = form.cleaned_data['fechainicio']
                    clase.fechafin = form.cleaned_data['fechafin']
                    clase.save(request)
                    log(u'Edito horario de Evento Docente: %s' % clase, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delclase':
            try:
                clase = CapClaseDocente.objects.get(pk=int(request.POST['id']))
                if clase.capcabeceraasistenciadocente_set.values('id').filter(status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar, porque tiene asistencias registradas."})
                log(u'Elimino horario de Evento Docente: %s' % clase, request, "del")
                clase.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        #ASISTENCIAS
        elif action == 'asistencia':
            try:
                asis = CapCabeceraAsistenciaDocente.objects.filter(fecha=datetime.now().date() if not 'fecha' in request.POST else datetime.strptime(request.POST["fecha"], '%d-%m-%Y'),clase_id=int(request.POST["idc"]), status=True)
                if not CapClaseDocente.objects.get(pk=int(request.POST['idc'])).capeventoperiodo.exiten_inscritos():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede continuar, porque no existe inscrito."})
                if 'fecha' in request.POST:
                    fecha=datetime.strptime(request.POST["fecha"], '%d-%m-%Y')
                    if asis.values('id').exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe asistencia en esa fecha y clase."})
                    if not CapClaseDocente.objects.values('id').filter(Q(pk=int(request.POST['idc'])),(Q(fechainicio__lte=fecha) & Q(fechafin__gte=fecha)), status=True,dia=fecha.weekday() + 1).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"No esta en rango de fecha o en dia."})
                if not asis.values('id').exists():
                    clase=CapClaseDocente.objects.get(pk=int(request.POST['idc']))
                    asistencia=CapCabeceraAsistenciaDocente(clase_id=int(request.POST['idc']),
                                                             fecha= fecha.date() if 'fecha' in request.POST else datetime.now().date(),
                                                             horaentrada=clase.turno.horainicio,
                                                             horasalida=clase.turno.horafin,
                                                             contenido="SIN CONTENIDO",
                                                             observaciones="SIN OBSERVACIONES")
                    asistencia.save(request)
                    log(u'Agrego Asistencia: %s [%s]' % (asistencia,asistencia.id), request, "add")
                    for integrante in clase.capeventoperiodo.inscritos_aprobado():
                        resultadovalores = CapDetalleAsistenciaDocente(cabecerasolicitud=integrante,cabeceraasistencia=asistencia, asistio=False)
                        resultadovalores.save(request)
                else:
                    asistencia=asis[0]
                return JsonResponse({"result": "ok",'id':asistencia.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addasistenciagrupal':
            try:
                cadenaselect = request.POST['cadenaselect']
                cadenanoselect = request.POST['cadenanoselect']
                cadenadatos = cadenaselect.split(',')
                cadenanodatos = cadenanoselect.split(',')
                asistencia=CapCabeceraAsistenciaDocente.objects.get(pk=int(request.POST["id"]))
                for cadena in cadenadatos:
                    if cadena:
                        if asistencia.capdetalleasistenciadocente_set.values('id').filter(cabecerasolicitud_id=cadena,status=True).exists():
                            resultadovalores =asistencia.capdetalleasistenciadocente_set.get(cabecerasolicitud_id=cadena,status=True)
                            resultadovalores.asistio = True
                            resultadovalores.save(request)
                        else:
                            resultadovalores = CapDetalleAsistenciaDocente(cabecerasolicitud_id=cadena,cabeceraasistencia=asistencia,asistio=True)
                            resultadovalores.save(request)
                for cadenano in cadenanodatos:
                    if cadenano:
                        if asistencia.capdetalleasistenciadocente_set.values('id').filter(cabecerasolicitud_id=cadenano,status=True).exists():
                            resultadovalores =asistencia.capdetalleasistenciadocente_set.get(cabecerasolicitud_id=cadenano,status=True)
                            resultadovalores.asistio = False
                            resultadovalores.save(request)
                        else:
                            resultadovalores = CapDetalleAsistenciaDocente(cabecerasolicitud_id=cadenano,cabeceraasistencia=asistencia,asistio=False)
                            resultadovalores.save(request)
                log(u'Edito Asistencia: %s [%s]' % (asistencia,asistencia.id), request, "edit")
                data = {"result": "ok", "results": [{"id": x.cabecerasolicitud.id, "porcientoasist": x.cabecerasolicitud.porciento_asistencia(),"porcientorequerido":x.cabecerasolicitud.porciento_requerido_asistencia()} for x in asistencia.capdetalleasistenciadocente_set.filter(status=True)]}
                return JsonResponse(data)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addasistenciaindividual':
            try:
                asistencia=CapCabeceraAsistenciaDocente.objects.get(pk=int(request.POST["id"]))
                if asistencia.capdetalleasistenciadocente_set.values('id').filter(cabecerasolicitud_id=int(request.POST['idi']),status=True).exists():
                    resultadovalores =asistencia.capdetalleasistenciadocente_set.get(cabecerasolicitud_id=int(request.POST['idi']),status=True)
                    resultadovalores.asistio = True if request.POST['valor']=="y" else False
                    resultadovalores.save(request)
                else:
                    resultadovalores = CapDetalleAsistenciaDocente(cabecerasolicitud_id=int(request.POST['idi']),cabeceraasistencia=asistencia,asistio=True if request.POST['valor']=="y" else False)
                    resultadovalores.save(request)
                datos={}
                datos['id'] = resultadovalores.cabecerasolicitud.id
                datos['porcientoasist'] = resultadovalores.cabecerasolicitud.porciento_asistencia()
                datos['porcientorequerido'] = resultadovalores.cabecerasolicitud.porciento_requerido_asistencia()
                datos['result']='ok'
                log(u'Edito Asistencia de Evento Docente: %s [%s]' % (asistencia,asistencia.id), request, "edit")
                return JsonResponse(datos)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addasistenciacontenido':
            try:
                asistencia=CapCabeceraAsistenciaDocente.objects.get(pk=int(request.POST["id"]))
                asistencia.contenido=request.POST["valor"]
                asistencia.save(request)
                log(u'Edito Contenido de Asistencia de Evento Docente: %s [%s]' % (asistencia,asistencia.id), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addasistenciaobservacion':
            try:
                asistencia=CapCabeceraAsistenciaDocente.objects.get(pk=int(request.POST["id"]))
                asistencia.observaciones=request.POST["valor"]
                asistencia.save(request)
                log(u'Edito Observacion de Asistencia de Evento Docente: %s [%s]' % (asistencia,asistencia.id), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delasistencia':
            try:
                asistencia = CapCabeceraAsistenciaDocente.objects.get(pk=int(request.POST["id"]))
                asistencia.delete()
                log(u'Elimino asistencia Docente: %s [%s]' % (asistencia,asistencia.id), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'adicionarpersonafirma':
            try:
                form = CapEventoPeriodoFirmasForm(request.POST, request.FILES)
                # if 'firma' in request.FILES:
                #     arch = request.FILES['firma']
                #     extension = arch._name.split('.')
                #     tam = len(extension)
                #     exte = extension[tam - 1]
                #
                #     if arch.size > 6291456:
                #         return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 6 Mb."})
                #     if not exte.lower() == 'png':
                #         return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .png"})
                if form.is_valid():
                    evento = CapEventoPeriodoFirmasDocente(capeventoperiodo_id=int(request.POST['id']),
                                                           firmapersona_id=form.cleaned_data['personafirma'],
                                                           tipofirmaevento=form.cleaned_data['tipofirmaevento']
                                                           )
                    evento.save(request)
                    # if 'firma' in request.FILES:
                    #     ruta = os.path.join(SITE_STORAGE, 'media', 'reportes', 'encabezados_pies', 'firmas','')
                    #     rutapdf = ruta + u"%s.png" % evento.firmapersona.cedula
                    #     if os.path.isfile(rutapdf):
                    #         os.remove(rutapdf)
                    #
                    #     firma = request.FILES['firma']
                    #     firma._name = u"%s.png" % evento.firmapersona.cedula
                    #     evento.firma = firma
                    #     evento.save(request)
                    # else:
                    #     ruta = os.path.join(SITE_STORAGE, 'media', 'reportes', 'encabezados_pies', 'firmas','')
                    #     rutapdf = ruta + u"%s.png" % evento.firmapersona.cedula
                    #     if not os.path.isfile(rutapdf):
                    #         transaction.set_rollback(True)
                    #         return JsonResponse({"result": "bad", "mensaje": u"Debe ingresar un archivo de firma."})

                    log(u'Adiciono firma evento periodo Docente: %s [%s]' % (evento, evento.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletefirma':
            try:
                itemfirma = CapEventoPeriodoFirmasDocente.objects.get(pk=int(request.POST['id']))
                itemfirma.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar la firma."})

        elif action == 'addaprobacion':
            try:
                cabecera=CapCabeceraSolicitudDocente.objects.get(pk=int(request.POST['id']))
                # cabecera.estadosolicitud=variable_valor('PENDIENTE_CAPACITACION') if int(request.POST['estado'])==variable_valor('APROBADO_CAPACITACION') else variable_valor('RECHAZADO_CAPACITACION')
                cabecera.estadosolicitud=request.POST['estado']
                cabecera.fechaultimaestadosolicitud=datetime.now().date()
                cabecera.save(request)
                detalle = CapDetalleSolicitudDocente(cabecera=cabecera,
                                                     fechaaprobacion=datetime.now().date(),
                                                     observacion=request.POST['observacion'],
                                                     aprueba=persona,
                                                     estado= 2 if int(request.POST['estado'])==variable_valor('APROBADO_CAPACITACION') else 3)
                detalle.save(request)
                detalle.mail_notificar_talento_humano(request.session['nombresistema'],True)
                log(u'Aprobar solicitud Docente: %s' % detalle, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'modelonotas':
            try:
                instructor = CapInstructorDocente.objects.get(pk=int(request.POST['id']))
                modelos = instructor.modelo_sin_utilizar()
                return JsonResponse({"result": "ok", 'instructor': instructor.instructor.nombre_completo_inverso(),
                                     'modelos': [{'id': modelo.id, 'nombre': modelo.__str__()} for modelo in modelos]})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        elif action == 'confimodelogeneral':
            try:
                with transaction.atomic():
                    filtro = CapModeloEvaluativoDocenteGeneral.objects.filter(status=True).order_by('orden')
                    instructor = CapInstructorDocente.objects.get(pk=int(request.POST['id']))
                    for f in filtro:
                        if not CapNotaDocente.objects.filter(status=True, modelo=f.modelo,
                                                          instructor_id=instructor.pk).exists():
                            modelonota = CapNotaDocente(modelo=f.modelo,
                                                     fecha=datetime.now().date(),
                                                     instructor_id=instructor.pk)
                            modelonota.save(request)
                            log(u'Adiciono Modelo Evaluativo Docente: %s' % modelonota, request, "add")
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'traeralumnosmoodle':
            try:
                instructor = CapInstructorDocente.objects.get(pk=int(request.POST['id']), status=True)
                estudiantes = instructor.capeventoperiodo.capcabecerasolicituddocente_set.filter(status=True)
                primerestudiante = estudiantes.filter(status=True).first()
                bandera = True
                modelo_mood = ''
                modelo_sga = ''
                for notasmooc in instructor.notas_de_moodle_capacitacion(primerestudiante.participante):
                    bandera = instructor.modelo_evaluativo().filter(modelo__nombre=notasmooc[1].upper().strip()).exists()
                    if not bandera:
                        for notasmoocstr in instructor.notas_de_moodle_capacitacion(primerestudiante.participante):
                            modelo_mood += "{}, ".format(notasmoocstr[1])
                        for notassga in instructor.modelo_evaluativo():
                            modelo_sga += "{}, ".format(notassga.modelo.nombre)
                        return JsonResponse({"result": "bad", "mensaje": u"Modelo Evaluativo extraído es diferente al modelo existente\nMoodle:\n{}\nSGA:\n{}".format(modelo_mood, modelo_sga)})
                listaenviar = estudiantes.filter(status=True).values('id', 'participante__apellido1', 'participante__apellido2', 'participante__nombres').order_by('participante__apellido1')
                return JsonResponse({"result": "ok", "cantidad": len(listaenviar), "inscritos": convertir_lista(listaenviar)})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'traernotaindividual':
            try:
                instructor = CapInstructorDocente.objects.get(pk=int(request.POST['idinstructor']), status=True)
                alumno = CapCabeceraSolicitudDocente.objects.get(pk=request.POST['id'])
                modelos = instructor.capnotadocente_set.filter(status=True)
                if instructor.notas_de_moodle_capacitacion(alumno.participante):
                    for notasmooc in instructor.notas_de_moodle_capacitacion(alumno.participante):
                        # campo = alumno.campo_capdocente(notasmooc[1].upper().strip())
                        # if not alumno.matricula.bloqueomatricula:
                        if type(notasmooc[0]) is Decimal:
                            # if null_to_decimal(campo.valor) != float(notasmooc[0]) or (
                            #         alumno.asistenciafinal < campo.detallemodeloevaluativo.modelo.asistenciaaprobar):
                            actualizar_nota_capdocente(alumno.id, instructor.id, notasmooc[1].upper().strip(), notasmooc[0])
                                # auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                                #                                 calificacion=notasmooc[0])
                                # auditorianotas.save(request)
                        # else:
                        #     if null_to_decimal(campo.valor) != float(0) or (
                        #             alumno.asistenciafinal < campo.detallemodeloevaluativo.modelo.asistenciaaprobar):
                        #         actualizar_nota_planificacion(alumno.id, notasmooc[1].upper().strip(), notasmooc[0])
                        #         auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False, calificacion=0)
                        #         auditorianotas.save(request)
                else:
                    for modelo in modelos:
                    # for detallemodelo in materia.modeloevaluativo.detallemodeloevaluativo_set.filter(migrarmoodle=True):
                    #     campo = alumno.campo(detallemodelo.nombre)
                        actualizar_nota_capdocente(alumno.id, instructor.id, modelo.modelo.nombre, 0)
                        # auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False, calificacion=0)
                        # auditorianotas.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex})

        elif action == 'actualizar_modelo_moodle':
            try:
                evento = CapEventoPeriodoDocente.objects.get(pk=request.POST['id'], status=True)
                clave = request.POST['clave']
                evento.crear_actualizar_categoria_notas_curso(clave)
                log(u'Actualizo moodle evento docente: %s' % (evento), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar los datos."})

        elif action == 'crearcursomoodle':
            try:
                instructor = CapInstructorDocente.objects.get(status=True, pk=request.POST['id'])
                instructor.crear_curso_moodle_principal()
                log(u'Creo curso moodle evento docente: %s' % (instructor), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al crear el curso."})

        elif action == 'crearmasivocursomoodle':
            try:
                from moodle import moodle
                leadsselect = eval(request.POST['ids'])
                instructores = CapInstructorDocente.objects.filter(status=True, pk__in=leadsselect)
                primerinstructor = instructores.first()
                primerinstructor.nombrecurso = request.POST["nomcurso"]
                #primerinstructor.idcursomoodle = 100
                primerinstructor.save(request)
                primerinstructor.crear_curso_moodle_principal()
                for instructor in instructores.exclude(id=primerinstructor.pk):
                    instructor.idcursomoodle = primerinstructor.idcursomoodle
                    instructor.nombrecurso = primerinstructor.nombrecurso
                    instructor.save(request)
                    instructor.crear_actualizar_instructor_curso(moodle,1)

                log(u'Creo curso moodle evento docente: %s' % (instructores), request, "add")
                return JsonResponse({"result": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al crear el curso."})

        elif action == 'updategrade':
            try:
                cap = CapDetalleNotaDocente.objects.get(pk=request.POST.get('id'))
                if value := request.POST.get('value', '').strip():
                    if value.isdigit():
                        cap.nota = int(value)
                        cap.save()
                        return JsonResponse({'result': 'ok'})
                    else:
                        return JsonResponse({'result': 'bad', 'mensaje': 'Solo se admiten números'})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': ex.__str__()})

        elif action == 'saveEtapaPeriodo':
            try:
                idp = int(request.POST.get('idp', '0'))
                id = int(request.POST.get('id', '0'))
                if idp == 0:
                    raise NameError(u"No se encontro parametro de periodo")
                try:
                    eCapPeriodoDocente = CapPeriodoDocente.objects.get(pk=idp)
                except ObjectDoesNotExist:
                    raise NameError(u"No se encontro el periodo.")
                form = CapPeriodoCronogramaForm(request.POST)
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError(v[0])
                try:
                    eCapCronogramaNecesidad = CapCronogramaNecesidad.objects.get(pk=id)
                    if CapCronogramaNecesidad.objects.values("id").filter(periodo=eCapPeriodoDocente, etapa=form.cleaned_data['etapa']).exclude(pk=eCapCronogramaNecesidad.pk).exists():
                        raise NameError(u"Etapa ya se encuentra registrada")
                except ObjectDoesNotExist:
                    if CapCronogramaNecesidad.objects.values("id").filter(periodo=eCapPeriodoDocente, etapa=form.cleaned_data['etapa']).exists():
                        raise NameError(u"Etapa ya se encuentra registrada")
                    eCapCronogramaNecesidad = CapCronogramaNecesidad(periodo=eCapPeriodoDocente)
                eCapCronogramaNecesidad.etapa = form.cleaned_data['etapa']
                eCapCronogramaNecesidad.inicio = form.cleaned_data['inicio']
                eCapCronogramaNecesidad.fin = form.cleaned_data['fin']
                eCapCronogramaNecesidad.activo = form.cleaned_data['activo']
                eCapCronogramaNecesidad.save(request)
                if id == 0:
                    log(u'Adiciono etapa al cronograma del periodo: %s' % eCapCronogramaNecesidad, request, 'add')
                else:
                    log(u'Edito etapa al cronograma del periodo: %s' % eCapCronogramaNecesidad, request, 'edit')
                return JsonResponse({"result": True, "message": f"Se guardo correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'deleteCronogramaNecesidadEtapa':
            try:
                id = int(request.POST.get('id', '0'))
                try:
                    eCapCronogramaNecesidad = deleteCapCronogramaNecesidad = CapCronogramaNecesidad.objects.get(pk=id)
                except ObjectDoesNotExist:
                    raise NameError(u"No se encontro registro a eliminar.")
                eCapCronogramaNecesidad.delete()
                log(u'Elimino etapa de cronograma del periodo: %s' % (deleteCapCronogramaNecesidad), request, "del")
                return JsonResponse({"result": True, "message": u"Se elimino correctamente el registro."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "message": u"Error al eliminar el registro."})

        elif action == 'saveCapEncuestaPeriodo':
            from inno.models import CapEncuestaPeriodo
            from inno.forms import CapEncuestaPeriodoForm
            with transaction.atomic():
                try:
                    idp = int(encrypt(request.POST.get('idp', encrypt('0'))))
                    id = int(encrypt(request.POST.get('id', encrypt('0'))))
                    try:
                        eCapPeriodoDocente = CapPeriodoDocente.objects.get(id=idp)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro periodo de capacitación")
                    form = CapEncuestaPeriodoForm(request.POST)
                    if not form.is_valid():
                        for k, v in form.errors.items():
                            raise NameError(v[0])
                    try:
                        eCapEncuestaPeriodo = CapEncuestaPeriodo.objects.get(pk=id)
                        if CapEncuestaPeriodo.objects.values("id").filter(periodo=eCapPeriodoDocente, nombre=form.cleaned_data['nombre']).exclude(pk=eCapEncuestaPeriodo.pk).exists():
                            raise NameError(u"Encuentra ya se encuentra registrada")
                    except ObjectDoesNotExist:
                        if CapEncuestaPeriodo.objects.values("id").filter(periodo=eCapPeriodoDocente, nombre=form.cleaned_data['nombre']).exists():
                            raise NameError(u"Encuentra ya se encuentra registrada")
                        eCapEncuestaPeriodo = CapEncuestaPeriodo(periodo=eCapPeriodoDocente)
                    eCapEncuestaPeriodo.nombre = form.cleaned_data['nombre']
                    eCapEncuestaPeriodo.isVigente = form.cleaned_data['isVigente']
                    eCapEncuestaPeriodo.save(request)
                    if id == 0:
                        log(u'Adiciono encuesta a periodo de capacitación: %s' % eCapEncuestaPeriodo, request, 'add')
                    else:
                        log(u'Edito encuesta a periodo de capacitación: %s' % eCapEncuestaPeriodo, request, 'edit')
                    return JsonResponse({"result": True, "message": f"Se guardo correctamente"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'saveCapPreguntaEncuestaPeriodo':
            from inno.models import CapEncuestaPeriodo, CapPreguntaEncuestaPeriodo, CapOpcionPreguntaEncuestaPeriodo
            from inno.forms import CapPreguntaEncuestaPeriodoForm
            with transaction.atomic():
                try:
                    idp = int(encrypt(request.POST.get('idp', encrypt('0'))))
                    id = int(encrypt(request.POST.get('id', encrypt('0'))))
                    try:
                        eCapEncuestaPeriodo = CapEncuestaPeriodo.objects.get(id=idp)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro periodo de capacitación")

                    form = CapPreguntaEncuestaPeriodoForm(request.POST)
                    if not form.is_valid():
                        for k, v in form.errors.items():
                            raise NameError(v[0])
                    try:
                        eCapPreguntaEncuestaPeriodo = CapPreguntaEncuestaPeriodo.objects.get(pk=id)
                        if CapPreguntaEncuestaPeriodo.objects.values("id").filter(encuesta=eCapEncuestaPeriodo, descripcion=form.cleaned_data['descripcion']).exclude(pk=eCapPreguntaEncuestaPeriodo.pk).exists():
                            raise NameError(u"Pregunta ya se encuentra registrada")
                    except ObjectDoesNotExist:
                        if CapPreguntaEncuestaPeriodo.objects.values("id").filter(encuesta=eCapEncuestaPeriodo, descripcion=form.cleaned_data['descripcion']).exists():
                            raise NameError(u"Pregunta ya se encuentra registrada")
                        eCapPreguntaEncuestaPeriodo = CapPreguntaEncuestaPeriodo(encuesta=eCapEncuestaPeriodo)
                    eCapPreguntaEncuestaPeriodo.descripcion = form.cleaned_data['descripcion']
                    eCapPreguntaEncuestaPeriodo.isActivo = form.cleaned_data['isActivo']
                    eCapPreguntaEncuestaPeriodo.save(request)
                    if id == 0:
                        log(u'Adiciono pregunta a la encuesta a periodo de capacitación: %s' % eCapPreguntaEncuestaPeriodo, request, 'add')
                    else:
                        log(u'Edito pregunta de la encuesta a periodo de capacitación: %s' % eCapPreguntaEncuestaPeriodo, request, 'edit')
                    opciones = json.loads(request.POST['lista_items1'])
                    if len(opciones) == 0:
                        raise NameError(u"No se encontro opciones de la pregunta")
                    lista = []
                    for o in opciones:
                        idopcion = int(o.get('id_opcion', '0'))
                        try:
                            eCapOpcionPreguntaEncuestaPeriodo = CapOpcionPreguntaEncuestaPeriodo.objects.get(id=idopcion, pregunta=eCapPreguntaEncuestaPeriodo)
                            isNew = True
                        except ObjectDoesNotExist:
                            eCapOpcionPreguntaEncuestaPeriodo = CapOpcionPreguntaEncuestaPeriodo(pregunta=eCapPreguntaEncuestaPeriodo)
                            isNew = False
                        if not eCapOpcionPreguntaEncuestaPeriodo.en_uso():
                            eCapOpcionPreguntaEncuestaPeriodo.descripcion = o['descripcion']
                        eCapOpcionPreguntaEncuestaPeriodo.valoracion = o['valoracion']
                        eCapOpcionPreguntaEncuestaPeriodo.isActivo = o['activo']
                        eCapOpcionPreguntaEncuestaPeriodo.save(request)
                        if isNew:
                            log(u'Agrego opción a la pregunta pregunta : %s' % eCapOpcionPreguntaEncuestaPeriodo, request, "add")
                        else:
                            log(u'Edito pregunta : %s' % eCapOpcionPreguntaEncuestaPeriodo, request, "edit")
                        lista.append(eCapOpcionPreguntaEncuestaPeriodo.id)
                    CapOpcionPreguntaEncuestaPeriodo.objects.filter(status=True, pregunta=eCapPreguntaEncuestaPeriodo).exclude(id__in=lista).update(status=False)
                    return JsonResponse({"result": True, "message": f"Se guardo correctamente"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, 'message': str(ex)})

        return HttpResponseRedirect(request.path)
    else:
        action = request.GET.get('action', None)
        if not action is None:

            #PERIODO

            if action == 'addperiodomodal':
                try:
                    data['title'] = u'Adicionar periodo de evento'
                    data['action'] = request.GET['action']
                    data['form'] = CapPeriodoForm()
                    template = get_template("adm_capacitaciondocente/gestion/modal/formaddperiodoevento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})


            elif action == 'delperiodo':
                try:
                    data['title'] = u'Eliminar Periodo de Evento'
                    data['periodo'] = CapPeriodoDocente.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitaciondocente/gestion/delperiodo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editperiodomodal':
                try:
                    data['title'] = u'Editar Periodo de Evento'
                    data['id'] = id = int(request.GET['id'])
                    data['action'] = request.GET['action']
                    data['periodo'] = periodo=CapPeriodoDocente.objects.get(pk=int(request.GET['id']))
                    # form = CapPeriodoForm(initial={'nombre':periodo.nombre,'descripcion':periodo.descripcion,'abreviatura':periodo.abreviatura,'fechainicio':periodo.fechainicio,'fechafin':periodo.fechafin})
                    form = CapPeriodoForm(initial=model_to_dict(periodo))
                    if periodo.esta_cap_evento_periodo_activo():
                        form.editar_grupo()
                    data['form'] = form
                    template = get_template("adm_capacitaciondocente/gestion/modal/formaddperiodoevento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            #EVENTO
            elif action == 'crearmasivocursomoodle':
                try:
                    if 'ids[]' in request.GET:
                        ids = request.GET.getlist('ids[]')
                        instructores = CapInstructorDocente.objects.filter(status=True, pk__in=ids)

                    leadsselect = ids
                    data['listadoseleccion'] = leadsselect
                    data['listadoinstructores'] = instructores


                    template = get_template('adm_capacitaciondocente/gestion/modal/migrarmasivomoodle.html')

                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    mensaje = 'Intentelo mas tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})


            elif action == 'addeventomodal':
                try:
                    data['action'] = request.GET['action']

                    data['title'] = u'Adicionar evento'
                    data['form'] = CapEventoForm()
                    template = get_template("adm_capacitaciondocente/gestion/modal/formaddperiodoevento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'delevento':
                try:
                    data['title'] = u'Eliminar Evento'
                    data['evento'] = CapEventoDocente.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitaciondocente/gestion/delevento.html", data)
                except Exception as ex:
                    pass


            elif action == 'editeventomodal':
                try:
                    data['title'] = u'Editar Evento'
                    data['action'] = request.GET['action']
                    data['id'] = id = int(request.GET['id'])
                    data['evento'] = evento = CapEventoDocente.objects.get(pk=int(request.GET['id']))
                    form = CapEventoForm(initial={'nombre': evento.nombre,
                                                  'tipocurso': evento.tipocurso})
                    if evento.esta_cap_evento_activo():
                        form.editar_grupo()
                    data['form'] = form
                    template = get_template("adm_capacitaciondocente/gestion/modal/formaddperiodoevento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'eventos':
                try:
                    request.session['viewactivoAreaConocimiento'] = 1
                    data['title'] = u'Evento'
                    search = None
                    ids = None
                    url_vars = ''
                    evento = None
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        evento = CapEventoDocente.objects.filter(pk=ids, status=True)
                    elif 's' in request.GET:
                        search = request.GET['s']
                        if search.isdigit():
                            evento = CapEventoDocente.objects.filter(pk=search, status=True)
                        else:
                            if search:
                                s = search.split(" ")
                                if len(s) == 1:
                                    evento = CapEventoDocente.objects.filter(Q(nombre__icontains=s[0]),Q(status=True))
                                elif len(s) == 2:
                                    evento = CapEventoDocente.objects.filter(Q(nombre__icontains=s[0]),Q(nombre__icontains=s[1]),Q(status=True))
                                elif len(s) == 3:
                                    evento = CapEventoDocente.objects.filter(Q(nombre__icontains=s[0]),Q(nombre__icontains=s[1]), Q(nombre__icontains=s[2]),Q(status=True))
                                elif len(s) == 4:
                                    evento = CapEventoDocente.objects.filter(Q(nombre__icontains=s[0]),Q(nombre__icontains=s[1]), Q(nombre__icontains=s[2]), Q(nombre__icontains=s[3]),Q(status=True))
                            else:
                                evento = CapEventoDocente.objects.filter(status=True)
                    else:
                        evento = CapEventoDocente.objects.filter(status=True)
                    paging = MiPaginador(evento, 25)
                    p = 1
                    url_vars += "&action=eventos"
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
                    data['evento'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data["url_vars"] = url_vars
                    return render(request, "adm_capacitaciondocente/gestion/viewevento.html", data)
                except Exception as ex:
                    pass

            #ENFOQUE
            elif action == 'addenfoque':
                try:
                    data['title'] = u'Adicionar Capacitación Enfoque'
                    data['form'] = CapEnfocadaForm()
                    return render(request, "adm_capacitaciondocente/gestion/addenfoque.html", data)
                except Exception as ex:
                    pass

            elif action == 'addenfoquemodal':
                try:
                    data['title'] = u'Adicionar Capacitación Enfoque'
                    data['form'] = CapEnfocadaForm()
                    data['action'] = request.GET['action']
                    template = get_template("adm_capacitaciondocente/gestion/modal/formaddperiodoevento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'delenfoque':
                try:
                    data['title'] = u'Eliminar Capacitación Enfoque'
                    data['enfocada'] = CapEnfocadaDocente.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitaciondocente/gestion/delenfoque.html", data)
                except Exception as ex:
                    pass


            elif action == 'editenfoquemod':
                try:
                    data['title'] = u'Editar Capacitación Enfoque'
                    data['action'] = request.GET['action']
                    data['id'] = int(request.GET['id'])
                    data['enfocada'] = enfo=CapEnfocadaDocente.objects.get(pk=int(request.GET['id']))
                    form = CapEnfocadaForm(initial={'nombre':enfo.nombre})
                    data['form'] = form
                    template = get_template("adm_capacitaciondocente/gestion/modal/formaddperiodoevento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'enfoques':
                try:
                    request.session['viewactivoAreaConocimiento'] = 2
                    data['title'] = u'Enfoque'
                    data['enfocada'] = CapEnfocadaDocente.objects.filter(status=True)
                    return render(request, "adm_capacitaciondocente/gestion/viewenfoque.html", data)
                except Exception as ex:
                    pass

            #TURNO
            elif action == 'addturno':
                try:
                    data['title'] = u'Adicionar Turno'
                    form= CapTurnoForm(initial={'turno':int((CapTurnoDocente.objects.filter(status=True).aggregate(Max('turno'))['turno__max'])+1) if CapTurnoDocente.objects.values('id').filter(status=True).exists() else 1})
                    form.editar_grupo()
                    data['form'] =form
                    return render(request, "adm_capacitaciondocente/gestion/addturno.html", data)
                except Exception as ex:
                    pass

            elif action == 'addturnomodal':
                try:
                    data['title'] = u'Adicionar Turno'
                    data['action'] = request.GET['action']
                    data['id'] = request.GET['id']
                    data['horas'] = request.GET['id']
                    form= CapTurnoForm(initial={'turno':int((CapTurnoDocente.objects.filter(status=True).aggregate(Max('turno'))['turno__max'])+1) if CapTurnoDocente.objects.values('id').filter(status=True).exists() else 1})
                    form.editar_grupo()
                    data['form'] =form
                    template = get_template("adm_capacitaciondocente/gestion/modal/formaddperiodoevento.html")
                    return JsonResponse({'result' : True, 'data' : template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result' : False, 'message' : str(ex)})

            elif action == 'delturno':
                try:
                    data['title'] = u'Eliminar Turno'
                    data['turno'] = CapTurnoDocente.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitaciondocente/gestion/delturno.html", data)
                except Exception as ex:
                    pass

            elif action == 'editturno':
                try:
                    data['title'] = u'Editar Turno'
                    data['turno'] = turno=CapTurnoDocente.objects.get(pk=int(request.GET['id']))
                    form = CapTurnoForm(initial={'turno': turno.turno,
                                                 'horainicio': str(turno.horainicio),
                                                 'horafin': str(turno.horafin),
                                                 'horas': str(turno.horas)})
                    form.editar_grupo()
                    form.editar_turno()
                    data['form'] = form
                    return render(request, "adm_capacitaciondocente/gestion/editturno.html", data)
                except Exception as ex:
                    pass

            elif action == 'editturnomodal':
                try:
                    data['title'] = u'Editar Turno'
                    data['action'] = request.GET['action']
                    data['id'] = request.GET['id']
                    data['turno'] = turno=CapTurnoDocente.objects.get(pk=int(request.GET['id']))
                    form = CapTurnoForm(initial={'turno': turno.turno,
                                                 'horainicio': str(turno.horainicio),
                                                 'horafin': str(turno.horafin),
                                                 'horas': str(turno.horas)})
                    form.editar_grupo()
                    form.editar_turno()
                    data['form'] = form
                    template = get_template("adm_capacitaciondocente/gestion/modal/formaddperiodoevento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'turnos':
                try:
                    request.session['viewactivoAreaConocimiento'] = 3
                    data['title'] = u'Turnos'
                    data['turno'] = CapTurnoDocente.objects.filter(status=True)
                    return render(request, "adm_capacitaciondocente/gestion/viewturno.html", data)
                except Exception as ex:
                    pass


            #CONFIGURACION
            elif action == 'configuracion':
                try:

                    data['title'] = u'Configuración'
                    configuracion = CapConfiguracionDocente.objects.filter()
                    existeimgfondo = False
                    if configuracion.values('id').exists():
                        try:
                            if configuracion[0].fondocertificado:
                                existeimgfondo = True
                            revisado = DistributivoPersona.objects.filter(persona=configuracion[0].revisado,denominacionpuesto=configuracion[0].denominacionrevisado)
                            aprobado1 = DistributivoPersona.objects.filter(persona=configuracion[0].aprobado1,denominacionpuesto=configuracion[0].denominacionaprobado1)
                            aprobado2 = DistributivoPersona.objects.filter(persona=configuracion[0].aprobado2,denominacionpuesto=configuracion[0].denominacionaprobado2)
                            aprobado3 = DistributivoPersona.objects.filter(persona=configuracion[0].aprobado3,denominacionpuesto=configuracion[0].denominacionaprobado3)
                            personasubrogante = DistributivoPersona.objects.filter(persona=configuracion[0].personasubrogante)
                            form = CapConfiguracionForm(initial={'minasistencia': configuracion[0].minasistencia,
                                                                 'minnota': configuracion[0].minnota,
                                                                 'abreviaturadepartamento': configuracion[0].abreviaturadepartamento,
                                                                 'revisado': revisado[0].id if revisado.values('id').exists() else 0,
                                                                 'aprobado1': aprobado1[0].id if aprobado1.values('id').exists() else 0,
                                                                 'aprobado2': aprobado2[0].id if aprobado2.values('id').exists() else 0,
                                                                 'aprobado3': aprobado3[0].id if aprobado3.values('id').exists() else 0,
                                                                 'personasubrogante': personasubrogante[0].id if personasubrogante.values('id').exists() else 0,
                                                                 'essubrogante': configuracion[0].essubrogante,
                                                                 'tiposubrogante': configuracion[0].tiposubrogante})
                            form.editar(revisado,aprobado1,aprobado2,aprobado3,personasubrogante)
                        except Exception as ex:
                            form = CapConfiguracionForm(initial={'minasistencia': configuracion[0].minasistencia,
                                                                 'minnota': configuracion[0].minnota})
                    else:
                        form = CapConfiguracionForm()
                    data['form'] = form
                    data['existeimgfondo'] = existeimgfondo
                    d = datetime.now()
                    data['horasegundo'] = d.strftime('%Y%m%d_%H%M%S')
                    return render(request, "adm_capacitaciondocente/gestion/configuracion.html", data)
                except Exception as ex:
                    pass



            elif action == 'busquedaconcargo':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__()==2:
                        distributivo = DistributivoPersona.objects.filter(Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1]),estadopuesto__id=PUESTO_ACTIVO_ID, status=True).distinct()[:20]
                    else:
                        distributivo = DistributivoPersona.objects.filter(Q(persona__nombres__contains=q) | Q(persona__apellido1__contains=q) | Q(persona__apellido2__contains=q) | Q(persona__cedula__contains=q)).filter(estadopuesto__id=PUESTO_ACTIVO_ID, status=True)[:20]
                    data = {"result": "ok", "results": [{"id": x.id, "name": (u'%s - %s - %s'%(x.persona.cedula , x.persona.nombre_completo_inverso(),x.denominacionpuesto)) } for x in distributivo]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            #EVENTO PERIODO
            elif action == 'addperiodoevento':
                try:
                    data['title'] = u'Adicionar Evento'
                    periodo=CapPeriodoDocente.objects.get(pk=int(request.GET['id']))
                    data['periodo'] = periodo.id
                    pais=Pais.objects.get(pk=1)
                    provincia = Provincia.objects.get(pk=10)
                    canton=Canton.objects.get(pk=2)
                    parroquia = Parroquia.objects.get(pk=4)
                    idrevisado = 0
                    nomrevisado = 0
                    nomaprobador1 = ''
                    nomaprobador2 = ''
                    nomaprobador3 = ''
                    abreviaturadepartamento = ''
                    minasistencia = 0
                    minnota = 0
                    if CapConfiguracionDocente.objects.filter(status=True):
                        configuracion = CapConfiguracionDocente.objects.filter(status=True)[0]
                        if configuracion.revisado:
                            idrevisado = configuracion.revisado.id
                            nomrevisado = configuracion.revisado
                        if configuracion.aprobado1:
                            nomaprobador1 = configuracion.aprobado1
                        if configuracion.aprobado2:
                            nomaprobador2 = configuracion.aprobado2
                        if configuracion.aprobado3:
                            nomaprobador3 = configuracion.aprobado3
                        abreviaturadepartamento = configuracion.abreviaturadepartamento
                        minasistencia = configuracion.minasistencia
                        minnota = configuracion.minnota
                    data['idrevisado'] = idrevisado
                    data['nomrevisado'] = nomrevisado
                    form=CapEventoPeriodoForm(initial={'periodo':periodo,
                                                       'pais': pais,
                                                       'provincia': provincia,
                                                       'canton': canton,
                                                       'parroquia': parroquia,
                                                       'minasistencia': minasistencia,
                                                       'minnota': minnota,
                                                       'revisado': idrevisado,
                                                       'aprobado1': nomaprobador1,
                                                       'aprobado2': nomaprobador2,
                                                       'aprobado3': nomaprobador3,
                                                       'horas' : 0,
                                                       'horaspropedeutica': 0,
                                                       'horaspracticas': 0,
                                                       'horasexperimentales' : 0,
                                                       'horasautonoma': 0,
                                                       'horastotal': 0,

                                                       'abreviaturadepartamento': abreviaturadepartamento,
                                                       'codigo':int((CapEventoPeriodoDocente.objects.filter(status=True,periodo=periodo).aggregate(Max('codigo'))['codigo__max'])+1 if CapEventoPeriodoDocente.objects.values('id').filter(status=True,periodo=periodo).exists() else 1)
                                                       })
                    form.editar_grupo()
                    form.adicionar(pais,provincia,canton)
                    form.editar_encuesta(periodo)
                    data['form'] =form
                    return render(request, "adm_capacitaciondocente/gestion/addperiodoevento.html", data)
                except Exception as ex:
                    pass

            elif action == 'delperiodoevento':
                try:
                    data['title'] = u'Eliminar Evento'
                    data['evento'] = CapEventoPeriodoDocente.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitaciondocente/gestion/delperiodoevento.html", data)
                except Exception as ex:
                    pass

            elif action == 'editperiodoevento':
                try:
                    data['title'] = u'Editar Evento'
                    data['evento'] = evento=CapEventoPeriodoDocente.objects.get(pk=int(request.GET['id']))
                    responsable= evento.responsable
                    form = CapEventoPeriodoForm(initial={'periodo':evento.periodo,
                                                         'periodoac':evento.periodoac,
                                                         'capevento':evento.capevento,
                                                         'horas': evento.horas,
                                                         'horasexperimentales': evento.horasexperimentales,
                                                         'horaspracticas': evento.horaspracticas,
                                                         'departamento': evento.departamento,
                                                         'horaspropedeutica': evento.horaspropedeutica,
                                                         'horasautonoma': evento.horasautonoma,
                                                         'horastotal': evento.horasautonoma+ evento.horas+evento.horaspropedeutica+evento.horaspracticas+evento.horasexperimentales,
                                                         'folder': evento.folder,
                                                         'objetivo': evento.objetivo,
                                                         'observacion': evento.observacion,
                                                         'minasistencia': evento.minasistencia,
                                                         'minnota': evento.minnota,
                                                         'fechainicio': evento.fechainicio,
                                                         'fechafin': evento.fechafin,
                                                         'regimenlaboral': evento.regimenlaboral,
                                                         'tipoparticipacion': evento.tipoparticipacion,
                                                         'contextocapacitacion': evento.contextocapacitacion,
                                                         'modalidad' : evento.modalidad,
                                                         'tipocertificacion': evento.tipocertificacion,
                                                         'tipocapacitacion': evento.tipocapacitacion,
                                                         'pais':  evento.pais,
                                                         'provincia': evento.provincia,
                                                         'canton': evento.canton,
                                                         'parroquia': evento.parroquia,
                                                         'visualizar': evento.visualizar,
                                                         'enfoque': evento.enfoque,
                                                         'contenido': evento.contenido,
                                                         'cupo': evento.cupo,
                                                         'responsable': responsable.id,
                                                         'areaconocimiento': evento.areaconocimiento,
                                                         'subareaconocimiento': evento.subareaconocimiento,
                                                         'subareaespecificaconocimiento': evento.subareaespecificaconocimiento,
                                                         'revisado':(u'%s - %s - %s'%(evento.revisado.cedula,evento.revisado.nombre_completo_inverso(),evento.denominacionrevisado)) if evento.revisado else '',
                                                         'aprobado1':(u'%s - %s - %s'%(evento.aprobado1.cedula,evento.aprobado1.nombre_completo_inverso(),evento.denominacionaprobado1)) if evento.aprobado1 else '',
                                                         'aprobado2':(u'%s - %s - %s'%(evento.aprobado2.cedula,evento.aprobado2.nombre_completo_inverso(),evento.denominacionaprobado2)) if evento.aprobado2 else '',
                                                         'aprobado3': (u'%s - %s - %s' % (evento.aprobado3.cedula,evento.aprobado3.nombre_completo_inverso(),evento.denominacionaprobado3)) if evento.aprobado3 else '',
                                                         'abreviaturadepartamento': (u'%s' % evento.abreviaturadepartamento if evento.abreviaturadepartamento else ''),
                                                         'codigo':evento.codigo,
                                                         'observacionreporte': evento.observacionreporte,
                                                         'aula': evento.aula,
                                                         'modeloevaluativoindividual': evento.modeloevaluativoindividual,
                                                         'unificarmoodle': evento.unificarmoodle,
                                                         'encuesta': evento.encuesta,
                                                         'modalidadlaboral': evento.modalidadlaboral.all()
                                                         })

                    form.editar_grupo()
                    if evento.exiten_inscritos():
                        form.editar_regimenlaboral()
                    form.editar_responsable(responsable)
                    form.editar_encuesta(evento.periodo)
                    if not evento.periodo.esta_activo_periodo:
                        data['permite_modificar'] = False
                    data['form'] = form
                    return render(request, "adm_capacitaciondocente/gestion/editperiodoevento.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/adm_capacitaciondocente/gestion?action=planificacion&id={evento.periodo_id}")

            elif action == 'busqueda':
                try:
                    q = request.GET['q'].upper().strip()
                    if ' ' in q:
                        s = q.split(" ")
                        distributivo=DistributivoPersona.objects.filter(Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1]),estadopuesto__id=PUESTO_ACTIVO_ID,status=True).distinct()[:20]
                    distributivo=DistributivoPersona.objects.filter(Q(persona__nombres__contains=q) | Q(persona__apellido1__contains=q) | Q(persona__apellido2__contains=q) | Q(persona__cedula__contains=q)).filter(estadopuesto__id=PUESTO_ACTIVO_ID,status=True)[:20]
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_repr()}for x in distributivo]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'busquedaregistro':
                try:
                    eventoperiodo= CapEventoPeriodoDocente.objects.get(pk=int(request.GET['id']))
                    data = {"result": "ok", "results": [{"id": eventoperiodo.id,"horas":str(eventoperiodo.horas),"evento":str(eventoperiodo.capevento), "inicio":str(eventoperiodo.fechainicio.strftime('%d-%m-%Y')),"fin":str(eventoperiodo.fechafin.strftime('%d-%m-%Y')),"enfoque":str(eventoperiodo.enfoque)}if eventoperiodo else ""]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'listadoinscripcion':
                try:
                    participante= DistributivoPersona.objects.get(pk=int(request.GET['idp']))
                    tieneeventos = CapCabeceraSolicitudDocente.objects.values_list("capeventoperiodo_id").filter(participante=participante.persona)
                    excluir = CapEventoPeriodoDocente.objects.values_list("id").filter(capevento__nombre__in=[datos['evento'] for datos in json.loads(request.GET['listado'])]) if request.GET['listado'] else []
                    eventoperiodolista =CapEventoPeriodoDocente.objects.filter(Q(status=True)&Q(visualizar=True)&Q(regimenlaboral=participante.regimenlaboral)).exclude(Q(pk__in=excluir)|Q(pk__in=tieneeventos))
                    if eventoperiodolista:
                        data = {"result": "ok", "results": [{"id": str(eventoperiodo.id),"horas":str(eventoperiodo.horas),"evento":str(eventoperiodo.capevento),"inicio":str(eventoperiodo.fechainicio.strftime('%d-%m-%Y')),"fin":str(eventoperiodo.fechafin.strftime('%d-%m-%Y')),"enfoque":str(eventoperiodo.enfoque),"inscrito":str(eventoperiodo.contar_inscripcion_evento_periodo()),"modalidad":str(eventoperiodo.get_modalidad_display())}for eventoperiodo in eventoperiodolista]}
                    else:
                        data = {"result": "no"}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'addinscribir':
                try:
                    data['title'] = u'Inscribir'
                    data['form'] = form = CapInscribirForm()
                    data['eventoperiodo'] = id = int(request.GET['id'])
                    evento = CapEventoPeriodoDocente.objects.get(id=id)
                    data['modalidadeslab'] = evento.modalidadlaboral.exists()
                    form.cargar_regimen(evento)
                    return render(request, "adm_capacitaciondocente/gestion/addinscribir.html", data)
                except Exception as ex:
                    pass

            elif action == 'inscritos':
                try:
                    data['title'] = u'Inscritos'
                    ids = None
                    url_vars = ''
                    eventoperiodo = CapEventoPeriodoDocente.objects.get(pk=int(request.GET['id']))
                    filtro = Q(capeventoperiodo=eventoperiodo) & Q(status=True) & Q(estadosolicitud=variable_valor('APROBADO_CAPACITACION'))
                    id, search, encuesta, estado = eventoperiodo.id, request.GET.get('s', None), int(request.GET.get('encuesta', '0')), int(request.GET.get('estado', '0'))
                    url_vars += f"&action=inscritos&id={str(eventoperiodo.id)}"
                    if search:
                        search = search.strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & Q(Q(participante__nombres__icontains=search) |
                                                Q(participante__apellido1__icontains=search) |
                                                Q(participante__apellido2__icontains=search) |
                                                Q(participante__cedula__icontains=search) |
                                                Q(participante__pasaporte__icontains=search))
                        else:
                            filtro = filtro & Q(Q(Q(participante__apellido1__contains=ss[0]) &
                                                  Q(participante__apellido2__contains=ss[1])) |
                                                Q(Q(participante__nombres__icontains=ss[0]) &
                                                  Q(participante__nombres__icontains=ss[1])))
                        url_vars += f'&s={search}'

                    if estado:
                        estado_ids = []
                        inscritos = CapCabeceraSolicitudDocente.objects.filter(status=True, capeventoperiodo=eventoperiodo)
                        if estado == 1:
                            if eventoperiodo.tipoparticipacion_id == 1:
                                for inscrito in inscritos:
                                    if inscrito.porciento_requerido_asistencia():
                                        estado_ids.append(inscrito.id)
                                filtro = filtro & Q(pk__in=estado_ids)
                            elif eventoperiodo.tipoparticipacion_id == 2:
                                for inscrito in inscritos:
                                    if inscrito.calificacion_requerido_aprobacion():
                                        estado_ids.append(inscrito.id)
                                filtro = filtro & Q(pk__in=estado_ids)
                            elif eventoperiodo.tipoparticipacion_id == 3:
                                for inscrito in inscritos:
                                    if inscrito.calificacion_requerido_aprobacion() and inscrito.porciento_requerido_asistencia():
                                        estado_ids.append(inscrito.id)
                                filtro = filtro & Q(pk__in=estado_ids)
                            else:
                                filtro = filtro & Q(estadosolicitud=variable_valor('APROBADO_CAPACITACION'))
                        elif estado == 2:
                            if eventoperiodo.tipoparticipacion_id == 1:
                                for inscrito in inscritos:
                                    if not inscrito.porciento_requerido_asistencia():
                                        estado_ids.append(inscrito.id)
                                filtro = filtro & Q(pk__in=estado_ids)
                            elif eventoperiodo.tipoparticipacion_id == 2:
                                for inscrito in inscritos:
                                    if not inscrito.calificacion_requerido_aprobacion():
                                        estado_ids.append(inscrito.id)
                                filtro = filtro & Q(pk__in=estado_ids)
                            elif eventoperiodo.tipoparticipacion_id == 3:
                                for inscrito in inscritos:
                                    if not inscrito.calificacion_requerido_aprobacion() and inscrito.porciento_requerido_asistencia():
                                        estado_ids.append(inscrito.id)
                                filtro = filtro & Q(pk__in=estado_ids)

                        url_vars += f'&estado={estado}'

                    if encuesta:
                        encuesta_ids = []
                        inscritos = CapCabeceraSolicitudDocente.objects.filter(status=True, capeventoperiodo=eventoperiodo)
                        if encuesta == 1:
                            for inscrito in inscritos:
                                if inscrito.aplica_encuesta():
                                    if inscrito.respondio_encuesta():
                                        encuesta_ids.append(inscrito.id)
                            filtro = filtro & Q(pk__in=encuesta_ids)
                        elif encuesta == 2:
                            for inscrito in inscritos:
                                if inscrito.aplica_encuesta():
                                    if not inscrito.respondio_encuesta():
                                        encuesta_ids.append(inscrito.id)
                            filtro = filtro & Q(pk__in=encuesta_ids)
                        url_vars += f'&encuesta={encuesta}'
                    cabecera = CapCabeceraSolicitudDocente.objects.filter(filtro).distinct()
                    paging = MiPaginador(cabecera, 20)
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
                    filename_certificado = 'perf_qr_certificado_'
                    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', ''))
                    data['url_path'] = 'http://127.0.0.1:8000'
                    if not DEBUG:
                        data['url_path'] = 'https://sga.unemi.edu.ec'
                    data['folder'] = folder
                    data['filename_certificado'] = filename_certificado
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['encuesta'] = encuesta
                    data['estado'] = estado
                    data['cabecera'] = page.object_list
                    data["url_vars"] = url_vars
                    data['eventoperiodo'] = eventoperiodo
                    return render(request, "adm_capacitaciondocente/gestion/inscritos.html", data)
                except Exception as ex:
                    pass

            elif action == 'inscritos_solicitud':
                try:
                    data['title'] = u'Solicitantes'
                    search = None
                    ids = None
                    eventoperiodo=CapEventoPeriodoDocente.objects.get(pk=int(request.GET['id']))
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            cabecera = CapCabeceraSolicitudDocente.objects.filter((Q(participante__nombres__icontains=search) |
                                                                                    Q(participante__apellido1__icontains=search) |
                                                                                    Q(participante__apellido2__icontains=search) |
                                                                                    Q(participante__cedula__icontains=search) |
                                                                                    Q(participante__pasaporte__icontains=search)) &
                                                                                   Q(capeventoperiodo=eventoperiodo)&
                                                                                   Q(status=True)).distinct()
                                                                                    # Q(estadosolicitud=variable_valor('SOLICITUD_CAPACITACION')) &
                        else:
                            cabecera = CapCabeceraSolicitudDocente.objects.filter(Q(participante__apellido1__icontains=ss[0]) & Q(solicita__apellido2__icontains=ss[1]) &
                                                                           Q(capeventoperiodo=eventoperiodo)&Q(status=True)).distinct()
                    else:
                        cabecera = CapCabeceraSolicitudDocente.objects.filter(capeventoperiodo=eventoperiodo, status=True)
                    paging = MiPaginador(cabecera, 20)
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
                    data['cabecera'] = page.object_list
                    data['eventoperiodo'] = eventoperiodo
                    data['existeevento'] = CapEventoPeriodoDocente.objects.filter((Q(fechainicio__lte=datetime.now().date()) & Q(fechafin__gte=datetime.now().date())) & Q(status=True) & Q(visualizar=True)).exists()
                    data['solicitud_capacitacion'] = variable_valor('SOLICITUD_CAPACITACION')
                    data['pendiente_capacitacion'] = variable_valor('PENDIENTE_CAPACITACION')
                    data['aprobado_capacitacion'] = variable_valor('APROBADO_CAPACITACION')
                    return render(request, "adm_capacitaciondocente/gestion/inscritos_solicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'listafirmas':
                try:
                    data['title'] = u'Listado de firmas'
                    eventoperiodo = CapEventoPeriodoDocente.objects.get(pk=int(request.GET['id']))
                    data['listadofirmas'] = listadofirmas = eventoperiodo.capeventoperiodofirmasdocente_set.filter(status=True)
                    firma1 = None
                    firma2 = None
                    firma3 = None
                    firma4 = None
                    if listadofirmas.filter(tipofirmaevento=1):
                        firma1 = listadofirmas.filter(tipofirmaevento=1)[0]
                    if listadofirmas.filter(tipofirmaevento=2):
                        firma2 = listadofirmas.filter(tipofirmaevento=2)[0]
                    if listadofirmas.filter(tipofirmaevento=3):
                        firma3 = listadofirmas.filter(tipofirmaevento=3)[0]
                    if listadofirmas.filter(tipofirmaevento=4):
                        firma4 = listadofirmas.filter(tipofirmaevento=4)[0]
                    data['firma1'] = firma1
                    data['firma2'] = firma2
                    data['firma3'] = firma3
                    data['firma4'] = firma4
                    data['eventoperiodo'] = eventoperiodo
                    d = datetime.now()
                    data['horasegundo'] = d.strftime('%Y%m%d_%H%M%S')
                    return render(request, "adm_capacitaciondocente/gestion/listafirmas.html", data)
                except Exception as ex:
                    pass

            elif action == 'adicionarpersonafirma':
                try:
                    data['title'] = u'Adicionar firma'
                    data['capeventoperiodo'] = capeventoperiodo = CapEventoPeriodoDocente.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['listafirmas'] = listafirmas = capeventoperiodo.capeventoperiodofirmasdocente_set.values_list('tipofirmaevento',flat=True).filter(status=True)
                    form = CapEventoPeriodoFirmasForm()
                    data['form'] = form
                    return render(request, "adm_capacitaciondocente/gestion/adicionarpersonafirma.html", data)
                except Exception as ex:
                    pass

            elif action == 'delinscrito':
                try:
                    data['title'] = u'Eliminar Inscrito'
                    data['cabecera'] = CapCabeceraSolicitudDocente.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitaciondocente/gestion/delinscrito.html", data)
                except Exception as ex:
                    pass

            elif action == 'confimodelogeneral':
                try:
                    data['id'] = request.GET['id']
                    data['action'] = 'confimodelogeneral'
                    data['modeloevaluativo'] = modelos = CapModeloEvaluativoDocenteGeneral.objects.filter(
                        status=True).order_by('orden')
                    data['instructor'] = instructor = CapInstructorDocente.objects.get(pk=int(request.GET['id']))
                    if instructor.capnotadocente_set.filter(status=True).count() >= modelos.count():
                        return JsonResponse({"result": False, 'mensaje': 'Instructor ya cuenta con modelo evaluativo'})
                    data['instructorname'] = instructor.instructor.nombre_completo_inverso()
                    template = get_template("adm_capacitaciondocente/gestion/modal/confirmarmodelo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'actualizar_modelo_moodle_pos':
                try:
                    instructor = CapInstructorDocente.objects.get(pk=request.GET['id'], status=True)
                    modeloNotas = instructor.capnotadocente_set.filter(status=True).count()
                    if modeloNotas > 0:
                        if instructor.idcursomoodle != 0:
                            modelo = instructor.crear_actualizar_categoria_notas_curso_instructor()
                            if modelo:
                                return JsonResponse({"result":"ok"})
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"Modelo evaluativo no actualizado"})
                        else:
                            return JsonResponse({"result":"bad", "mensaje": u"Instructor no cuenta con curso moodle"})
                    else:
                        return JsonResponse({"result":"bad", "mensaje": u"Por favor, asigne un modelo evaluativo al evento"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar los datos"})

            elif action == 'listadodistributivo':
                try:
                    id = int (request.GET['id'])
                    listado_participante=CapCabeceraSolicitudDocente.objects.values_list("participante_id").filter(capeventoperiodo_id=int(request.GET['ide']), estadosolicitud=variable_valor('APROBADO_CAPACITACION'))
                    evento = CapEventoPeriodoDocente.objects.get(id=int(request.GET['ide']))
                    modalidades = evento.modalidadlaboral.values_list('id', flat=True) if evento.modalidadlaboral.exists() else [1, 2, 3, 4, 5, 6, 7]
                    distributivo=DistributivoPersona.objects.filter(unidadorganica_id=id,estadopuesto__id=PUESTO_ACTIVO_ID,status=True).exclude(persona_id__in=listado_participante).distinct()[:20]
                    if distributivo:
                        data = {"result": "ok", "results": [{'aplica': x.modalidadlaboral_id in modalidades, "id": str(x.id),"cedula":str(x.persona.cedula), "apellidos": x.persona.nombre_completo_minus(), "cargo": str(x.denominacionpuesto), 'regimen': str(x.regimenlaboral).lower().capitalize(), 'modalidadlaboral': str(x.modalidadlaboral).lower().capitalize()}for x in distributivo]}
                    else:
                        data = {"result": "no"}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'verdetalle':
                try:
                    data = {}
                    cabecera = CapCabeceraSolicitudDocente.objects.get(pk=int(request.GET['id']))
                    data['cabecerasolicitud'] = cabecera
                    data['detallesolicitud'] = cabecera.capdetallesolicituddocente_set.all()
                    data['solicitud_capacitacion'] = variable_valor('SOLICITUD_CAPACITACION')
                    data['pendiente_capacitacion'] = variable_valor('PENDIENTE_CAPACITACION')
                    data['aprobado_capacitacion'] = variable_valor('APROBADO_CAPACITACION')
                    template = get_template("adm_capacitaciondocente/gestion/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'verdetalleevento':
                try:
                    data = {}
                    data['evento'] =CapEventoPeriodoDocente.objects.get(pk=int(request.GET['id']))
                    template = get_template("adm_capacitaciondocente/gestion/detalleevento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'planificacion':
                try:
                    data['title'] = u'Planificación de Eventos'
                    search = None
                    url_vars = ''
                    ids = None
                    data['eCapPeriodoDocente'] = eCapPeriodoDocente = CapPeriodoDocente.objects.get(pk=int(request.GET['id']))
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            evento = CapEventoPeriodoDocente.objects.filter((Q(capevento__nombre__icontains=search)|
                                                                              Q(enfoque__nombre__icontains=search)) &
                                                                             Q(periodo=eCapPeriodoDocente) &
                                                                             Q(status=True)).distinct().order_by('capevento','enfoque', '-fechainicio')
                        else:
                            evento = CapEventoPeriodoDocente.objects.filter(Q(capevento__nombre__icontains=ss[0]) & Q(enfoque__nombre__icontains=ss[1]) &
                                                                             Q(periodo=eCapPeriodoDocente) &
                                                                             Q(status=True)).distinct().order_by('capevento','enfoque','-fechainicio')
                    else:
                        evento = CapEventoPeriodoDocente.objects.filter(periodo=eCapPeriodoDocente, status=True).order_by('-fechainicio')
                    paging = MiPaginador(evento, 20)
                    p = 1
                    url_vars += "&action=planificacion&id="+request.GET['id']
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
                    data['evento'] = page.object_list
                    data['reporte_0'] = obtener_reporte('inscritos_capacitacion_perf')
                    data['aprobado_capacitacion'] = variable_valor('APROBADO_CAPACITACION')
                    data["url_vars"] = url_vars
                    return render(request, "adm_capacitaciondocente/gestion/viewperiodoevento.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'listEncuestas':
                from inno.models import CapEncuestaPeriodo
                try:
                    data['title'] = u'Encuestas de satisfacción'
                    search = None
                    url_vars = ''
                    ids = None
                    try:
                        data['eCapPeriodoDocente'] = eCapPeriodoDocente = CapPeriodoDocente.objects.get(pk=int(request.GET.get('id', 0)))
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro periodo de capacitación")
                    filtro = Q(periodo=eCapPeriodoDocente) & Q(status=True)
                    eCapEncuestas = CapEncuestaPeriodo.objects.filter(filtro)
                    paging = MiPaginador(eCapEncuestas, 20)
                    p = 1
                    url_vars += "&action=listEncuestas&id=" + request.GET.get('id', 0)
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
                    data['eCapEncuestas'] = page.object_list
                    data["url_vars"] = url_vars
                    return render(request, "adm_capacitaciondocente/gestion/viewperiodoencuesta.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'listPreguntas':
                from inno.models import CapEncuestaPeriodo, CapPreguntaEncuestaPeriodo
                try:
                    try:
                        data['eCapEncuestaPeriodo'] = eCapEncuestaPeriodo = CapEncuestaPeriodo.objects.get(pk=int(encrypt(request.GET.get('id', encrypt('0')))))
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro periodo de capacitación")
                    data['title'] = u'Preguntas de encuesta de satisfacción'
                    search = None
                    url_vars = ''
                    ids = None
                    filtro = Q(encuesta=eCapEncuestaPeriodo) & Q(status=True)
                    eCapPreguntas = CapPreguntaEncuestaPeriodo.objects.filter(filtro)
                    paging = MiPaginador(eCapPreguntas, 20)
                    p = 1
                    url_vars += "&action=listPreguntas&id=" + request.GET.get('id', 0)
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
                    data['eCapPreguntas'] = page.object_list
                    data["url_vars"] = url_vars
                    return render(request, "adm_capacitaciondocente/gestion/viewpreguntaencuesta.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'loadFormEncuesta':
                from inno.models import CapPreguntaEncuestaPeriodo, CapEncuestaPeriodo
                from inno.forms import CapEncuestaPeriodoForm
                try:
                    data['idp'] = idp = int(encrypt(request.GET.get('idp', encrypt('0'))))
                    data['id'] = id = int(encrypt(request.GET.get('id', encrypt('0'))))
                    try:
                        eCapPeriodoDocente = CapPeriodoDocente.objects.get(id=idp)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro periodo de capacitación")
                    try:
                        eCapEncuestaPeriodo = CapEncuestaPeriodo.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        eCapEncuestaPeriodo = None
                    if eCapEncuestaPeriodo:
                        form = CapEncuestaPeriodoForm(initial=model_to_dict(eCapEncuestaPeriodo))
                    else:
                        form = CapEncuestaPeriodoForm()
                    data['form'] = form
                    data['switchery'] = True
                    data['action'] = 'saveCapEncuestaPeriodo'
                    template = get_template('adm_capacitaciondocente/gestion/modal/formencuesta.html')
                    return JsonResponse({"result": True, 'html': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "message": u"Error al obtener los datos."})

            elif action == 'loadFormPregunta':
                from inno.models import CapPreguntaEncuestaPeriodo, CapEncuestaPeriodo, CapOpcionPreguntaEncuestaPeriodo
                from inno.forms import CapPreguntaEncuestaPeriodoForm
                try:
                    data['idp'] = idp = int(encrypt(request.GET.get('idp', encrypt('0'))))
                    data['id'] = id = int(encrypt(request.GET.get('id', encrypt('0'))))
                    try:
                        data['eCapEncuestaPeriodo'] = eCapEncuestaPeriodo = CapEncuestaPeriodo.objects.get(id=idp)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro encuesta de satisfaccióin")
                    try:
                        eCapPreguntaEncuestaPeriodo = CapPreguntaEncuestaPeriodo.objects.get(pk=id, encuesta=eCapEncuestaPeriodo)
                    except ObjectDoesNotExist:
                        eCapPreguntaEncuestaPeriodo = None
                    if eCapPreguntaEncuestaPeriodo:
                        form = CapPreguntaEncuestaPeriodoForm(initial=model_to_dict(eCapPreguntaEncuestaPeriodo))
                        data['eCapOpciones'] = CapOpcionPreguntaEncuestaPeriodo.objects.filter(status=True, pregunta=eCapPreguntaEncuestaPeriodo)
                    else:
                        form = CapPreguntaEncuestaPeriodoForm()
                    data['form'] = form
                    data['switchery'] = True
                    data['action'] = 'saveCapPreguntaEncuestaPeriodo'
                    template = get_template('adm_capacitaciondocente/gestion/modal/formpreguntaencuesta.html')
                    return JsonResponse({"result": True, 'html': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "message": u"Error al obtener los datos."})

            elif action == 'repositoriodocente':
                try:
                    if 'id' in request.GET:
                        id = request.GET['id']
                        periodo = periodo = CapPeriodoDocente.objects.get(id=id)

                        eInscritos = CapCabeceraSolicitudDocente.objects.filter(capeventoperiodo__periodo_id=id,
                                                                            status=True).distinct('participante__apellido1', 'participante__apellido2', 'participante__nombres').order_by('participante')


                        data['inscritos'] = eInscritos
                        data['eventoperiodo'] = periodo
                        data['existecertificado'] = True if eInscritos else False
                    return render(request, "adm_capacitaciondocente/gestion/repositoriodocente.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'descargarcertificadosdocente':
                try:
                    rutas_certificados = []
                    inscripcion = None
                    if 'idp' in request.GET:
                        id = request.GET['idp']
                        periodo = CapPeriodoDocente.objects.get(id=id)
                        inscripcion = CapCabeceraSolicitudDocente.objects.filter( notificado=True, capeventoperiodo__periodo=periodo, rutapdf__isnull=False)
                    else:
                        id = request.GET['id']
                        inscripcion =  CapCabeceraSolicitudDocente.objects.filter(id=int(request.GET['id']))[0].participante.mis_capacitaciones_docente(CapCabeceraSolicitudDocente.objects.filter(id=int(request.GET['id']))[0].capeventoperiodo.periodo)

                    dominiosistema = request.build_absolute_uri('/')[:-1].strip("/")
                    directory = os.path.join(SITE_STORAGE, 'media/qrcode/certificados')

                    try:
                        os.stat(directory)
                    except:
                        os.mkdir(directory)

                    url = os.path.join(SITE_STORAGE, 'media', 'qrcode/certificados',
                                       'certificadoscapdocente.zip')
                    url_zip = url
                    fantasy_zip = zipfile.ZipFile(url, 'w')
                    if inscripcion:
                        if 'idp' in request.GET:
                            for ins in inscripcion:
                                if ins.rutapdf:
                                    carpeta_facultad = f"{ins.facultad}/" if ins.facultad else "SIN FACULTAD/"
                                    carpeta_carrera = f"{ins.carrera}/" if ins.carrera else "SIN CARRERA/"
                                    carpeta_inscripcion = f"Carpeta_{ins.participante}/"
                                    fantasy_zip.write(ins.rutapdf.path,
                                                      carpeta_facultad + carpeta_carrera + carpeta_inscripcion + os.path.basename(
                                                          ins.rutapdf.path))
                        else:
                            for ins in inscripcion:
                                if ins.rutapdf:
                                    carpeta_inscripcion = f"Carpeta_{ins.participante}/"
                                    # Agregar el archivo PDF a la carpeta de la inscripción dentro del ZIP
                                    fantasy_zip.write(ins.rutapdf.path, carpeta_inscripcion + os.path.basename(ins.rutapdf.path))
                                    #fantasy_zip.write(ins.rutapdf.path)
                    else:
                        raise NameError('Erro al generar')
                    fantasy_zip.close()
                    response = HttpResponse(open(url_zip, 'rb'), content_type='application/zip')
                    response['Content-Disposition'] = 'attachment; filename=certificadoscapdocente.zip'
                    return response
                except Exception as es:
                    pass


            elif action == 'excelasistencia':
                try:
                    # bordes
                    borders = Borders()
                    borders.left = 1
                    borders.right = 1
                    borders.top = 1
                    borders.bottom = 1
                    # estilos para los reportes
                    title = easyxf('font: name Arial, bold on , height 235; alignment: horiz centre')
                    subtitle1 = easyxf('font: name Arial, height 200; alignment: horiz centre')
                    subtitle2 = easyxf('font: name Arial, height 180; alignment: horiz centre')
                    nnormal = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
                    nnormal1 = easyxf('font: name Arial, bold on , height 150; alignment: horiz left')
                    nnormal2 = easyxf('font: name Arial, bold on , height 150; alignment: horiz right')
                    normal = easyxf('font: name Arial , height 150; alignment: horiz left')
                    normal2 = easyxf('font: name Arial, bold on , height 170; alignment: horiz left')
                    normal3 = easyxf('font: name Arial, bold on , height 150; alignment: horiz left')
                    stylenotas = easyxf('font: name Arial , height 150; alignment: horiz centre')
                    stylebnotas = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
                    stylebnotas1 = easyxf('font: name Arial, bold on , height 140; align:wrap on, horiz centre')
                    stylebfirmas = easyxf('font: name Arial, bold on , height 120; align:wrap on, horiz left,vert top')
                    stylebnombre = easyxf('font: name Arial, bold on , height 150; alignment: horiz centre')
                    stylevacio = easyxf('font: name Arial , height 600; alignment: horiz centre')
                    normal.borders = borders
                    stylebnotas.borders = borders
                    stylebnotas1.borders = borders
                    stylenotas.borders = borders
                    stylebnombre.borders = borders
                    stylevacio.borders = borders
                    #consulta
                    evento = CapEventoPeriodoDocente.objects.get(status=True, id=int(request.GET['id']))

                    __author__ = 'Unemi'
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('reporte1')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename =CONTROL DE ASISTENCIA ' + '.xls'

                    ws.col(0).width = 1000
                    ws.col(1).width = 5000
                    ws.col(2).width = 4000
                    encabezado = 13

                    ws.write_merge(encabezado,encabezado+1, 0,0, 'Nº', stylebnotas)
                    ws.write_merge(encabezado, encabezado+1, 1, 2, 'APELLIDOS Y NOMBRES', stylebnombre)
                    fechas=CapCabeceraAsistenciaDocente.objects.filter(clase__capeventoperiodo=evento).distinct('fecha').order_by('fecha')
                    meses = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP","OCT", "NOV", "DIC"]
                    fila=3
                    for fecha in fechas:
                        turno_fecha=CapCabeceraAsistenciaDocente.objects.filter(clase__capeventoperiodo=evento,fecha=fecha.fecha).order_by('clase__turno')
                        contar_turnos=turno_fecha.count()
                        nombre_concatenado=""
                        nombre_concatenado=str(fecha.fecha.day)+" "+meses[fecha.fecha.month-1]
                        if contar_turnos>1:
                            ws.write_merge(encabezado, encabezado, fila , fila+contar_turnos-1, nombre_concatenado , stylebnotas)
                            cada_uno=fila
                            for turno in turno_fecha:
                                ws.write(encabezado+1, cada_uno, str(turno.clase.turno.horainicio.strftime("%H:%M")), stylenotas)
                                cada_uno+=1
                            fila += contar_turnos
                        else:
                            ws.write(encabezado, fila, nombre_concatenado,stylebnotas)
                            ws.write(encabezado+1, fila, str(turno_fecha[0].clase.turno.horainicio.strftime("%H:%M")), stylenotas)
                            fila += 1
                    ws.col(fila).width = 2000
                    ws.col(fila+1).width = 2000
                    ws.col(fila + 2).width = 2550
                    ws.write_merge(encabezado, encabezado+1, fila,fila, '% HORAS ASISTIDA', stylebnotas1)
                    ws.write_merge(encabezado, encabezado+1, fila+1,fila+1, '% HORAS ASISTIDA', stylebnotas1)
                    ws.write_merge(encabezado, encabezado+1, fila+2, fila + 2, 'ESTADO', stylebnombre)
                    ws.write_merge(encabezado, encabezado+1, fila+3, fila + 3, 'OBSERVACIÓN', stylebnotas)

                    listainscritos = evento.inscritos_aprobado()
                    colum = 3
                    sumar_promedio_asistencia=0
                    contar_promedio_asistencia = 0
                    ultima_fecha = 0
                    if listainscritos.exists():
                        i = 0
                        for inscrito in listainscritos:
                            fil = i + 15
                            ws.write(fil, 0, str(i + 1), stylenotas)
                            ws.write(fil, 1, (u'%s'%inscrito.participante), normal)
                            ws.merge(fil, fil, 1, 2, normal)
                            colum=3
                            asistencia_asistida=0
                            for fecha in fechas:
                                turno_fecha = CapCabeceraAsistenciaDocente.objects.filter(clase__capeventoperiodo=evento,fecha=fecha.fecha).order_by('clase__turno')
                                for turno in turno_fecha:
                                    ws.col(colum).width = 1425
                                    asistio=CapDetalleAsistenciaDocente.objects.filter(cabeceraasistencia=turno,cabecerasolicitud=inscrito)
                                    if asistio.exists():
                                        ws.write(fil, colum, str('A'if asistio[0].asistio else 'F'), stylenotas)
                                        if asistio[0].asistio:
                                            asistencia_asistida+=1
                                    else:
                                        ws.write(fil, colum, str('N'), stylenotas)
                                    colum+=1
                                ultima_fecha = fecha.fecha
                            ws.write(fil, colum, str(asistencia_asistida), stylenotas)
                            promedio=inscrito.porciento_asistencia()
                            sumar_promedio_asistencia+=promedio
                            contar_promedio_asistencia+=1
                            ws.write(fil, colum+1, str(promedio)+'%', stylenotas)
                            if inscrito.porciento_requerido_asistencia():
                                ws.write(fil, colum + 2, str('APROBADO'), normal)
                            else:
                                ws.write(fil, colum + 2, str('REPROBADO'), normal)
                            ws.write(fil, colum + 3, str(''), stylenotas)
                            i = i + 1
                    ws.write_merge(fil + 1,fil + 1,colum-1, colum, 'PROMEDIO:', nnormal2)
                    ws.write(fil + 1,colum+1, str(round((sumar_promedio_asistencia/contar_promedio_asistencia),2) if contar_promedio_asistencia>0 else 0)+'%', stylenotas)
                    # hoja
                    ws.write_merge(1, 1, 0, colum+3, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(2, 2, 0, colum+3, 'INSTITUTO DE POSTGRADO Y EDUCACIÓN CONTINUA', subtitle1)
                    ws.write_merge(3, 3, 0, colum+3, 'UNIDAD DE TALENTO HUMANO', subtitle2)
                    ws.write_merge(4, 4, 0, colum+3, 'ÁREA DE FORMACIÓN Y DESARROLLO DE TALENTO HUMANO', subtitle2)
                    ws.write_merge(5, 5, 0, colum+3, 'RESUMEN CONTROL DE ASISTENCIA', title)
                    ws.write(7, 1, 'CÓDIGO: ', normal3)
                    ws.write(7, 2, evento.concatenar_codigo(), normal2)
                    ws.merge(7, 7, 2, colum)
                    ws.write(8, 1, 'CURSO: ', normal3)
                    ws.merge(8, 8, 1, 1)
                    ws.write(8, 2, (u'%s'% evento.capevento.nombre), normal2)
                    ws.merge(8, 8, 2, colum+3)
                    ws.write(9, 1, 'FACILITADORES:', normal3)
                    ws.merge(9, 9, 1, 1)
                    ws.write(9, 2, evento.concatenar_facilitadores(), normal3)
                    ws.merge(9, 9, 2, colum+3)
                    ws.write(10, 4, 'LUGAR:', normal3)
                    ws.merge(10, 10, 4, 5)
                    ws.write(10, 6, (u'%s'%evento.aula.nombre) + ' - ' + str(evento.aula.sede), normal3)
                    ws.merge(10, 10, 6, colum+3)
                    ws.write(10, 1, 'FECHA INICIO: ', normal3)
                    ws.merge(10, 10, 1, 1)
                    ws.write(10, 2, str(evento.fechainicio.strftime('%d-%m-%Y')), normal3)
                    ws.merge(10, 10, 2, 2)
                    ws.write(11, 1, 'FECHA FIN: ', normal3)
                    ws.merge(11, 11, 1, 1)
                    ws.write(11, 2, str(evento.fechafin.strftime('%d-%m-%Y')), normal3)
                    ws.merge(11, 11, 2, 2)
                    ws.write(11, 4, 'HORAS:', normal3)
                    ws.merge(11, 11, 4, 5)
                    ws.write(11, 6, str(evento.horas), normal3)
                    ws.merge(11, 11, 6, 9)
                    fecha_corte=0
                    if ultima_fecha.weekday()>=0 and ultima_fecha.weekday()<=3 or ultima_fecha.weekday()==6 :
                        dias = timedelta(days=1)
                    else:
                        dias = timedelta(days=2)
                    fecha_corte = ultima_fecha + dias
                    ws.write_merge(fil + 3, fil + 3, colum-2, colum-1, 'FECHA CORTE:', nnormal)
                    ws.write_merge(fil + 3, fil + 3, colum,colum, 'DIA', stylebnotas)
                    ws.write_merge(fil + 3, fil + 3, colum+1, colum+1, 'MES', stylebnotas)
                    ws.write_merge(fil + 3, fil + 3, colum+2, colum+2, 'AÑO', stylebnotas)
                    ws.write_merge(fil + 3, fil + 3, colum+3, colum+3, 'HORA', stylebnotas)
                    ws.write_merge(fil + 4, fil + 4, colum, colum,str(fecha_corte.day), stylenotas)
                    ws.write_merge(fil + 4, fil + 4, colum+1, colum+1, str(fecha_corte.month), stylenotas)
                    ws.write_merge(fil + 4, fil + 4, colum+2, colum+2, str(fecha_corte.year), stylenotas)
                    ws.write_merge(fil + 4, fil + 4, colum + 3, colum + 3, str(''), stylenotas)
                    ws.write_merge(fil + 5, fil + 5, colum , colum + 3,evento.concatenar_codigo(), stylebnotas)

                    ws.write_merge(fil + 2, fil + 2, 1, 1, 'OBSERVACIÓN:', nnormal1)
                    ws.write_merge(fil + 3, fil + 4, 1, 2, (evento.observacionreporte if evento.observacionreporte else ""), stylebnotas1)

                    ws.write_merge(fil + 6, fil + 6, 1, 8, 'RESUMEN GENERAL DE ASISTENCIA', nnormal)
                    ws.write_merge(fil + 7, fil + 8, 1, 1, 'SESIÓN', stylebnotas)
                    ws.write_merge(fil + 7, fil + 8, 2, 2, 'FECHA EJECUCIÓN DEL EVENTO', stylebnotas1)
                    ws.write_merge(fil + 7, fil + 8, 3, 4, '% ASISTENCIA', stylebnotas1)
                    fil=fil + 8
                    c = 0
                    suma_promedio=0
                    for fecha in fechas:
                        c += 1
                        fil += 1
                        fecha_asistencia = CapDetalleAsistenciaDocente.objects.filter(cabeceraasistencia__clase__capeventoperiodo=evento,cabeceraasistencia__fecha=fecha.fecha)
                        asistencia=fecha_asistencia.filter(asistio=True, status=True).count()
                        promedio=round((asistencia*100)/float(fecha_asistencia.count()),2)
                        suma_promedio+=promedio
                        ws.write_merge(fil, fil, 1, 1,str(c), stylebnotas)
                        ws.write_merge(fil, fil, 2, 2, str(fecha.fecha.strftime('%d-%m-%Y')), stylenotas)
                        ws.write_merge(fil, fil, 3, 4, str(promedio)+'%', stylenotas)

                    ws.write_merge(fil+1, fil+1, 1, 2, str('%PROMEDIO DE ASISTENCIA:'),nnormal2)
                    ws.write_merge(fil+1, fil+1, 3, 4,str(round((float(suma_promedio/c) if c>0 else 0),2)) + '%',stylenotas)
                    fil += 2
                    ws.write(fil + 1, 1, str('ELABORADO POR:'), nnormal1)
                    ws.write_merge(fil + 1, fil + 1, 3, 5, str('REVISADO POR:'), nnormal1)
                    ws.write_merge(fil + 1, fil + 1, 9, 10, str('APROBADO POR:'), nnormal1)
                    ws.write_merge(fil + 1, fil + 1, 13, 15, str('APROBADO POR:'), nnormal1)
                    fil += 3
                    cargo=DistributivoPersona.objects.filter(persona_id=persona,estadopuesto__id=PUESTO_ACTIVO_ID, status=True)
                    titulacion = persona.titulacion_principal_senescyt_registro()
                    ws.write_merge(fil, fil, 1, 2, '_________________________', nnormal1)
                    ws.write_merge(fil + 1,fil + 3, 1,2, (titulacion.titulo.abreviatura if not titulacion=='' else "")+""+str(persona)+ '\n' + str(cargo[0].denominacionpuesto if cargo.exists()else''), stylebfirmas)

                    ws.write_merge(fil, fil, 3, 7, '_________________________', nnormal1)
                    titulacionrevisado=evento.revisado.titulacion_principal_senescyt_registro()
                    ws.write_merge(fil + 1, fil + 3,3, 7, (titulacionrevisado.titulo.abreviatura if not titulacionrevisado=='' else "")+""+(evento.revisado.nombre_completo_inverso()if evento.revisado else '') + '\n' + str(evento.denominacionrevisado if evento.denominacionrevisado else ''),stylebfirmas)

                    ws.write_merge(fil, fil, 9, 11, '_________________________', nnormal1)
                    titulacionaprobado1 = evento.aprobado1.titulacion_principal_senescyt_registro()
                    ws.write_merge(fil + 1, fil + 3, 9, 11, (titulacionaprobado1.titulo.abreviatura if not titulacionaprobado1 == '' else "") + "" + (evento.aprobado1.nombre_completo_inverso() if evento.aprobado1 else '') + '\n' + str(evento.denominacionaprobado1 if evento.denominacionaprobado1 else ''), stylebfirmas)

                    ws.write_merge(fil, fil, 13, 16, '_________________________', nnormal1)
                    titulacionaprobado2 = evento.aprobado2.titulacion_principal_senescyt_registro()
                    ws.write_merge(fil + 1, fil + 3, 13, 15, (titulacionaprobado2.titulo.abreviatura if not titulacionaprobado2 == '' else "") + "" + (evento.aprobado2.nombre_completo_inverso() if evento.aprobado2 else '') + '\n' + str(evento.denominacionaprobado2 if evento.denominacionaprobado2 else ''), stylebfirmas)
                    wb.save(response)
                    return response
                except Exception as es:
                    pass

            elif action == 'reporte_generar_masivo':
                try:
                    persona_cargo_tercernivel = None
                    cargo = None
                    tamano = 0
                    data['tiposubrogante'] = None
                    data['evento'] = eventoperiodo = CapEventoPeriodoDocente.objects.get(status=True, pk=int(request.GET['id']))
                    subrog = CapConfiguracionDocente.objects.first()
                    eventoperiodo.aprobado1 = subrog.aprobado1
                    eventoperiodo.aprobado2 = subrog.aprobado2
                    eventoperiodo.aprobado3 = subrog.aprobado3
                    if subrog.essubrogante and subrog.tiposubrogante not in [None, '', ""] and data[
                        'tiposubrogante'] is None:
                        setattr(eventoperiodo, subrog.tiposubrogante, subrog.personasubrogante)
                        data['tiposubrogante'] = subrog.tiposubrogante
                    data['elabora_persona'] = persona
                    data['facilitador'] = eventoperiodo.capinstructordocente_set.filter(status=True)
                    totalinscritos = eventoperiodo.capcabecerasolicituddocente_set.filter(status=True)
                    data['listadofirmas'] = listadofirmas = eventoperiodo.capeventoperiodofirmasdocente_set.filter(status=True)
                    firma1 = None
                    firma2 = None
                    firma3 = None
                    firma4 = None
                    if listadofirmas.filter(tipofirmaevento=1):
                        firma1 = listadofirmas.filter(tipofirmaevento=1)[0]
                    if listadofirmas.filter(tipofirmaevento=2):
                        firma2 = listadofirmas.filter(tipofirmaevento=2)[0]
                    if listadofirmas.filter(tipofirmaevento=3):
                        firma3 = listadofirmas.filter(tipofirmaevento=3)[0]
                    if listadofirmas.filter(tipofirmaevento=4):
                        firma4 = listadofirmas.filter(tipofirmaevento=4)[0]
                    data['firma1'] = firma1
                    data['firma2'] = firma2
                    data['firma3'] = firma3
                    data['firma4'] = firma4
                    if DistributivoPersona.objects.values('id').filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID, status=True).exists():
                        cargo = DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID, status=True)[0]
                    data['persona_cargo'] = cargo

                    mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
                    fechainicio = eventoperiodo.fechainicio
                    fechafin = eventoperiodo.fechafin
                    fechacertificado = suma_dias_habiles(fechafin, 7)
                    data['fecha'] = u"Milagro, %s de %s del %s" % (
                        fechacertificado.day, str(mes[fechacertificado.month - 1]), fechacertificado.year)
                    if fechainicio == fechafin:
                        fechascapacitacion = "el %s de %s del %s" % (
                            fechainicio.day, str(mes[fechainicio.month - 1]), fechainicio.year)
                    elif fechainicio.month != fechafin.month:
                        if fechainicio.year == fechafin.year:
                            fechascapacitacion = "del %s de %s al %s de %s del %s" % (
                                fechainicio.day, str(mes[fechainicio.month - 1]), fechafin.day, str(mes[fechafin.month - 1]),
                                fechafin.year)
                        else:
                            fechascapacitacion = "del %s de %s del %s al %s de %s del %s" % (
                                fechainicio.day, str(mes[fechainicio.month - 1]), fechainicio.year, fechafin.day,
                                str(mes[fechafin.month - 1]), fechafin.year)
                    else:
                        fechascapacitacion = "del %s al %s de %s del %s" % (
                            fechainicio.day, fechafin.day, str(mes[fechainicio.month - 1]), fechainicio.year)
                    data['fechascapacitacion'] = fechascapacitacion
                    data['listado_contenido'] = listado = eventoperiodo.contenido.split("\n")

                    if eventoperiodo.objetivo.__len__() < 290:
                        if listado.__len__() < 21:
                            tamano = 120
                        elif listado.__len__() < 35:
                            tamano = 100
                        elif listado.__len__() < 41:
                            tamano = 70
                    data['controlar_bajada_logo'] = tamano
                    viceacad = None
                    if DistributivoPersona.objects.filter(denominacionpuesto_id=115, estadopuesto_id=1, status=True).exists():
                        viceacad = DistributivoPersona.objects.get(denominacionpuesto_id=115, estadopuesto_id=1, status=True)
                    data['viceacad'] = viceacad

                    titulo = persona.titulacion_principal_senescyt_registro()
                    if not titulo == '':
                        titulo_3 = persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion') if titulo.titulo.nivel_id == 2 else None
                        titulo_4 = persona.titulacion_set.filter(titulo__nivel=4).order_by('-fechaobtencion') if titulo.titulo.nivel_id == 2 else None
                        if titulo_4:
                            titulo = titulo_4[0]
                        elif titulo_3:
                            titulo = titulo_3[0]
                    if not titulo == '':
                        persona_cargo_tercernivel = persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[0] if titulo.titulo.nivel_id == 4 else None
                    data['persona_cargo_titulo'] = titulo
                    data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
                    fecha = datetime.now().date()
                    hora = datetime.now().time()
                    fecha_hora = fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__()

                    if eventoperiodo.tipoparticipacion_id == 3:
                        for inscrito in totalinscritos:
                            inscrito = CapCabeceraSolicitudDocente.objects.get(pk=inscrito.id)
                            token = md5(str(encrypt(inscrito.id) + fecha_hora).encode("utf-8")).hexdigest()
                            # if not inscrito.notificado:
                            if inscrito.porciento_requerido_asistencia() and inscrito.calificacion_requerido_aprobacion():
                                firmacertificado = 'robles'
                                fechacambio = (datetime(2019, 11, 1, 0, 0, 0)).date()
                                if eventoperiodo.fechafin >= fechacambio:
                                    firmacertificado = 'firmaguillermo'
                                data['firmacertificado'] = firmacertificado
                                eventoperiodo.actualizar_folio()
                                data['inscrito'] = inscrito
                                url_path = data['url_path'] = 'http://127.0.0.1:8000'
                                if not DEBUG:
                                    url_path = data['url_path'] = 'https://sga.unemi.edu.ec'

                                qrname = 'capins_qr_certificado_' + str(inscrito.id)
                                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
                                rutapdf = folder + qrname + '.pdf'
                                rutaimg = folder + qrname + '.png'
                                if os.path.isfile(rutapdf):
                                    os.remove(rutaimg)
                                    os.remove(rutapdf)
                                url = pyqrcode.create(f'{url_path}//media/qrcode/certificados/' + qrname + '.pdf')
                                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                                data['qrname'] = 'qr' + qrname
                                data['url_path'] = 'http://127.0.0.1:8000'
                                d = datetime.now()
                                data['horasegundo'] = d.strftime('%Y%m%d_%H%M%S')

                                valida = conviert_html_to_pdfsaveqrcertificado(
                                    'adm_capacitaciondocente/gestion/certificado_individual_pdf.html',
                                     {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                                )
                                if valida:
                                    inscrito.rutapdf = 'qrcode/certificados/' + qrname + '.pdf'
                                    inscrito.notificado = True
                                    inscrito.fechanotifica = datetime.now()
                                    inscrito.personanotifica = persona
                                    if not inscrito.token:
                                        inscrito.token = token
                                    inscrito.save(request)
                                    if not DEBUG:
                                        inscrito.mail_notificar_certificado(request.session['nombresistema'])
                                        time.sleep(5)

                    elif eventoperiodo.tipoparticipacion_id == 2:
                        for inscrito in totalinscritos:
                            inscrito = CapCabeceraSolicitudDocente.objects.get(pk=inscrito.id)
                            token = md5(str(encrypt(inscrito.id) + fecha_hora).encode("utf-8")).hexdigest()
                            # if not inscrito.notificado:
                            if inscrito.calificacion_requerido_aprobacion():
                                firmacertificado = 'robles'
                                fechacambio = (datetime(2019, 11, 1, 0, 0, 0)).date()
                                if eventoperiodo.fechafin >= fechacambio:
                                    firmacertificado = 'firmaguillermo'
                                data['firmacertificado'] = firmacertificado

                                eventoperiodo.actualizar_folio()

                                data['inscrito'] = inscrito

                                url_path = data['url_path'] = 'http://127.0.0.1:8000'
                                if not DEBUG:
                                    url_path = data['url_path'] = 'https://sga.unemi.edu.ec'

                                qrname = 'capins_qr_certificado_' + str(inscrito.id)
                                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
                                rutapdf = folder + qrname + '.pdf'
                                rutaimg = folder + qrname + '.png'
                                if os.path.isfile(rutapdf):
                                    os.remove(rutaimg)
                                    os.remove(rutapdf)
                                url = pyqrcode.create(f'{url_path}//media/qrcode/certificados/' + qrname + '.pdf')
                                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                                data['qrname'] = 'qr' + qrname
                                data['url_path'] = 'http://127.0.0.1:8000'
                                d = datetime.now()
                                data['horasegundo'] = d.strftime('%Y%m%d_%H%M%S')

                                valida = conviert_html_to_pdfsaveqrcertificado(
                                    'adm_capacitaciondocente/gestion/certificado_individual_pdf.html',
                                    {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                                )
                                if valida:
                                        # os.remove(rutaimg)
                                    inscrito.rutapdf = 'qrcode/certificados/' + qrname + '.pdf'
                                    inscrito.notificado = True
                                    inscrito.fechanotifica = datetime.now()
                                    inscrito.personanotifica = persona
                                    if not inscrito.token:
                                        inscrito.token = token
                                    inscrito.save(request)
                                    asunto = u"CERTIFICADO - " + inscrito.capeventoperiodo.capevento.nombre
                                    if not DEBUG:
                                        inscrito.mail_notificar_certificado(request.session['nombresistema'])
                                        time.sleep(5)

                    elif eventoperiodo.tipoparticipacion_id == 1:
                        for inscrito in totalinscritos:
                            inscrito = CapCabeceraSolicitudDocente.objects.get(pk=inscrito.id)
                            token = md5(str(encrypt(inscrito.id) + fecha_hora).encode("utf-8")).hexdigest()
                            # if not inscrito.notificado:
                            if inscrito.porciento_requerido_asistencia():
                                firmacertificado = 'robles'
                                fechacambio = (datetime(2019, 11, 1, 0, 0, 0)).date()
                                if eventoperiodo.fechafin >= fechacambio:
                                    firmacertificado = 'firmaguillermo'
                                data['firmacertificado'] = firmacertificado

                                eventoperiodo.actualizar_folio()

                                data['inscrito'] = inscrito

                                url_path = data['url_path'] = 'http://127.0.0.1:8000'
                                if not DEBUG:
                                    url_path = data['url_path'] = 'https://sga.unemi.edu.ec'

                                qrname = 'capins_qr_certificado_' + str(inscrito.id)
                                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
                                rutapdf = folder + qrname + '.pdf'
                                rutaimg = folder + qrname + '.png'
                                if os.path.isfile(rutapdf):
                                    os.remove(rutaimg)
                                    os.remove(rutapdf)
                                url = pyqrcode.create(f'{url_path}//media/qrcode/certificados/' + qrname + '.pdf')
                                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                                data['qrname'] = 'qr' + qrname
                                data['url_path'] = 'http://127.0.0.1:8000'
                                d = datetime.now()
                                data['horasegundo'] = d.strftime('%Y%m%d_%H%M%S')

                                valida = conviert_html_to_pdfsaveqrcertificado(
                                    'adm_capacitaciondocente/gestion/certificado_individual_pdf.html',
                                    {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                                )
                                if valida:
                                        # os.remove(rutaimg)
                                    inscrito.rutapdf = 'qrcode/certificados/' + qrname + '.pdf'
                                    inscrito.notificado = True
                                    inscrito.fechanotifica = datetime.now()
                                    inscrito.personanotifica = persona
                                    if not inscrito.token:
                                        inscrito.token = token
                                    inscrito.save(request)
                                    if not DEBUG:
                                        inscrito.mail_notificar_certificado(request.session['nombresistema'])
                                        time.sleep(5)

                    else:
                        for inscrito in totalinscritos:
                            inscrito = CapCabeceraSolicitudDocente.objects.get(pk=inscrito.id)
                            token = md5(str(encrypt(inscrito.id) + fecha_hora).encode("utf-8")).hexdigest()
                            # if not inscrito.notificado:
                            # if inscrito.porciento_requerido_asistencia() :
                            firmacertificado = 'robles'
                            fechacambio = (datetime(2019, 11, 1, 0, 0, 0)).date()
                            if eventoperiodo.fechafin >= fechacambio:
                                firmacertificado = 'firmaguillermo'
                            data['firmacertificado'] = firmacertificado

                            eventoperiodo.actualizar_folio()

                            data['inscrito'] = inscrito

                            url_path = data['url_path'] = 'http://127.0.0.1:8000'
                            if not DEBUG:
                                url_path = data['url_path'] = 'https://sga.unemi.edu.ec'

                            qrname = 'capins_qr_certificado_' + str(inscrito.id)
                            folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
                            rutapdf = folder + qrname + '.pdf'
                            rutaimg = folder + qrname + '.png'
                            if os.path.isfile(rutapdf):
                                os.remove(rutaimg)
                                os.remove(rutapdf)
                            url = pyqrcode.create(f'{url_path}//media/qrcode/certificados/' + qrname + '.pdf')
                            imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                            data['qrname'] = 'qr' + qrname
                            data['url_path'] = 'http://127.0.0.1:8000'
                            d = datetime.now()
                            data['horasegundo'] = d.strftime('%Y%m%d_%H%M%S')

                            valida = conviert_html_to_pdfsaveqrcertificado(
                                    'adm_capacitaciondocente/gestion/certificado_individual_pdf.html',
                                    {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                            )
                            if valida:
                                        # os.remove(rutaimg)
                                inscrito.rutapdf = 'qrcode/certificados/' + qrname + '.pdf'
                                inscrito.notificado = True
                                inscrito.fechanotifica = datetime.now()
                                inscrito.personanotifica = persona
                                if not inscrito.token:
                                    inscrito.token = token
                                inscrito.save(request)
                                asunto = u"CERTIFICADO - " + inscrito.capeventoperiodo.capevento.nombre
                                if not DEBUG:
                                    inscrito.mail_notificar_certificado(request.session['nombresistema'])
                                    time.sleep(5)

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'notas':
                try:
                    data['title'] = u'Notas'
                    data['idinstructor'] = request.GET['id']
                    data['evento'] = evento = CapEventoPeriodoDocente.objects.get(id=int(request.GET['id']), status=True)
                    data['instructores'] = evento.capinstructordocente_set.filter(status=True).order_by(
                        'instructor__apellido1', 'instructor__apellido2', 'instructor__nombres')
                    form = CapNotaDocenteForm()
                    form.deshabilitar_profesor()
                    data['form'] = form
                    if not evento.modeloevaluativoindividual:
                        data['modeloevaluativogeneral'] = CapModeloEvaluativoDocenteGeneral.objects.filter(
                            status=True).order_by('orden')
                    return render(request, 'adm_capacitaciondocente/gestion/viewnota.html', data)
                except Exception as ex:
                    pass

            elif action == 'notasmoodle':
                try:
                    data['title'] = u'Notas de moodle'
                    lista = []
                    data['instructor'] = instructor = CapInstructorDocente.objects.get(pk=int(request.GET['id']))
                    data['evento'] = evento = instructor.capeventoperiodo
                    data['inscritos'] = inscritos = evento.capcabecerasolicituddocente_set.filter(status=True)
                    data['tareas'] = tarea = CapNotaDocente.objects.filter(instructor=instructor)
                    # data['utiliza_validacion_calificaciones'] = variable_valor('UTILIZA_VALIDACION_CALIFICACIONES')
                    # data['habilitado_ingreso_calificaciones'] = profesor.habilitado_ingreso_calificaciones()
                    return render(request, "adm_capacitaciondocente/gestion/notasmoodle.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'delmodelonota':
                try:
                    data['title'] = u'Eliminar modelo de nota'
                    data['modelonota'] = modelonotas = CapNotaDocente.objects.get(pk=int(request.GET['id']))
                    data['evento'] = modelonotas.instructor.capeventoperiodo
                    return render(request, "adm_capacitaciondocente/gestion/delmodelonotas.html", data)
                except Exception as ex:
                    pass

            elif action == 'moverinscrito':
                try:
                    data['inscrito'] = inscrito = CapCabeceraSolicitudDocente.objects.get(pk=int(request.GET['id']))
                    data['title'] = u'Mover a %s' % inscrito.participante.nombre_completo_inverso()
                    form = MoverInscritoEventoCapacitacionForm()
                    data['form'] = form
                    return render(request, "adm_capacitaciondocente/gestion/moverinscrito.html", data)
                except Exception as ex:
                    pass

            elif action == 'reporteinscritoscurso':
                try:
                    eventoperiodo = CapEventoPeriodoDocente.objects.get(pk=int(request.GET['id']))

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('Listado')

                    formatocabeceracolumna = workbook.add_format({
                        'bold': 1,
                        'border': 1,
                        'align': 'center',
                        'valign': 'vcenter',
                        'bg_color': 'silver',
                        'text_wrap': 1,
                        'font_size': 10})

                    formatocelda = workbook.add_format({
                        'border': 1
                    })

                    formatotitulo = workbook.add_format(
                        {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 14})

                    ws.merge_range(0, 0, 0, 14, 'UNIVERSIDAD ESTATAL DE MILAGRO', formatotitulo)

                    columns = [
                        (u"APELLIDOS", 25),
                        (u"NOMBRES", 25),
                        (u"CORREO INSTITUCIONAL", 25),
                        (u"CORREO PERSONAL", 25),
                        (u"FACULTAD", 50),
                        (u"CARRERA", 50),
                        (u"MODALIDAD", 30)


                    ]
                    row_num = 4
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], formatocabeceracolumna)
                        ws.set_column(col_num, col_num, columns[col_num][1])

                    totalinscritos = CapCabeceraSolicitudDocente.objects.filter(capeventoperiodo=eventoperiodo,
                                                                    status=True).distinct('participante__apellido1', 'participante__apellido2','participante__nombres').order_by('participante')



                    row_num = 5
                    for inscrito in totalinscritos:
                        apellidos = inscrito.participante.apellido1 + ' ' + inscrito.participante.apellido2
                        nombres = inscrito.participante.nombres
                        correoinstitucional = inscrito.participante.emailinst
                        correopersonal = inscrito.participante.email
                        facultad = inscrito.facultad if inscrito.facultad else 'NINGUNO'
                        carrera = inscrito.carrera if inscrito.carrera else 'NINGUNO'
                        if inscrito.participante.distributivopersona_set.filter(status=True).exists():
                            plantilla = inscrito.participante.distributivopersona_set.filter(status=True)[0]
                            modalidad = plantilla.modalidadlaboral
                        else:
                            modalidad = 'NINGUNA'



                        ws.write(row_num, 0, u'%s' % apellidos, formatocelda)
                        ws.write(row_num, 1, u'%s' % nombres, formatocelda)
                        ws.write(row_num, 2, u'%s' % correoinstitucional, formatocelda)
                        ws.write(row_num, 3, u'%s' % correopersonal, formatocelda)
                        ws.write(row_num, 4, u'%s' % facultad, formatocelda)
                        ws.write(row_num, 5, u'%s' % carrera, formatocelda)
                        ws.write(row_num, 6, u'%s' % modalidad, formatocelda)


                        row_num += 1

                    workbook.close()
                    output.seek(0)
                    # Set up the Http response.
                    filename = 'reporte_inscrito_curso_capacitacion_docente' + random.randint(1, 10000).__str__() + '.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename

                    return response
                except Exception as ex:
                    pass

            elif action == 'reportecalificaciones':
                try:
                    eventoperiodo = CapEventoPeriodoDocente.objects.get(pk=int(request.GET['id']))

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('Listado')

                    formatocabeceracolumna = workbook.add_format({
                        'bold': 1,
                        'border': 1,
                        'align': 'center',
                        'valign': 'vcenter',
                        'bg_color': 'silver',
                        'text_wrap': 1,
                        'font_size': 10})

                    formatocelda = workbook.add_format({
                        'border': 1
                    })

                    formatotitulo = workbook.add_format(
                        {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 14})

                    ws.merge_range(0, 0, 0, 14, 'UNIVERSIDAD ESTATAL DE MILAGRO', formatotitulo)

                    columns = [
                        (u"APELLIDOS", 25),
                        (u"NOMBRES", 25),
                        (u"CORREO INSTITUCIONAL", 25),
                        (u"CORREO PERSONAL", 25),
                        (u"FACULTAD", 50),
                        (u"CARRERA", 50),
                        (u"MODALIDAD", 30),
                        (u"CALIFICACIÓN", 30),
                        (u"ESTADO", 30)
                    ]
                    row_num = 4
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], formatocabeceracolumna)
                        ws.set_column(col_num, col_num, columns[col_num][1])

                    totalinscritos = CapCabeceraSolicitudDocente.objects.filter(capeventoperiodo=eventoperiodo,
                                                                    status=True).distinct('participante__apellido1', 'participante__apellido2','participante__nombres').order_by('participante')



                    row_num = 5
                    for inscrito in totalinscritos:
                        apellidos = inscrito.participante.apellido1 + ' ' + inscrito.participante.apellido2
                        nombres = inscrito.participante.nombres
                        correoinstitucional = inscrito.participante.emailinst
                        correopersonal = inscrito.participante.email
                        facultad = inscrito.facultad if inscrito.facultad else 'NINGUNO'
                        carrera = inscrito.carrera if inscrito.carrera else 'NINGUNO'
                        if inscrito.participante.distributivopersona_set.filter(status=True).exists():
                            plantilla = inscrito.participante.distributivopersona_set.filter(status=True)[0]
                            modalidad = plantilla.modalidadlaboral
                        else:
                            modalidad = 'NINGUNA'
                        calificacion = inscrito.notafinal
                        if inscrito.notafinal >= 70:
                            estado = 'APROBADO'
                        else:
                            estado = 'REPROBADO'


                        ws.write(row_num, 0, u'%s' % apellidos, formatocelda)
                        ws.write(row_num, 1, u'%s' % nombres, formatocelda)
                        ws.write(row_num, 2, u'%s' % correoinstitucional, formatocelda)
                        ws.write(row_num, 3, u'%s' % correopersonal, formatocelda)
                        ws.write(row_num, 4, u'%s' % facultad, formatocelda)
                        ws.write(row_num, 5, u'%s' % carrera, formatocelda)
                        ws.write(row_num, 6, u'%s' % modalidad, formatocelda)
                        ws.write(row_num, 7, u'%s' % calificacion, formatocelda)
                        ws.write(row_num, 8, u'%s' % estado, formatocelda)


                        row_num += 1

                    workbook.close()
                    output.seek(0)
                    # Set up the Http response.
                    filename = 'reporte_inscrito_curso_capacitacion_docente' + random.randint(1, 10000).__str__() + '.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename

                    return response
                except Exception as ex:
                    pass

            elif action == 'reporteaprobadosfacultad':
                try:
                    eventoperiodo = CapEventoPeriodoDocente.objects.get(pk=int(request.GET['id']))

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('Listado')

                    formatocabeceracolumna = workbook.add_format({
                        'bold': 1,
                        'border': 1,
                        'align': 'center',
                        'valign': 'vcenter',
                        'bg_color': 'silver',
                        'text_wrap': 1,
                        'font_size': 10})

                    formatocelda = workbook.add_format({
                        'border': 1
                    })

                    formatotitulo = workbook.add_format(
                        {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 14})

                    ws.merge_range(0, 0, 0, 14, 'UNIVERSIDAD ESTATAL DE MILAGRO', formatotitulo)

                    columns = [
                        (u"FACULTAD", 50),
                        (u"INSCRITOS", 30),
                        (u"APROBADOS", 30),
                        (u"REPROBADOS", 30)


                    ]
                    row_num = 4
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], formatocabeceracolumna)
                        ws.set_column(col_num, col_num, columns[col_num][1])

                    row_num = 5
                    facultades = eventoperiodo.listado_facultades()
                    for facultad in facultades:
                        inscritos = eventoperiodo.contar_inscripcion_evento_periodo_por_facultad2(facultad)
                        aprobados = eventoperiodo.total_inscritos_aprobados_facultad2(facultad)
                        reprobados = eventoperiodo.total_inscritos_reprobados_facultad2(facultad)

                        if facultad is None:
                            facultad = 'NINGUNO'

                        ws.write(row_num, 0, u'%s' % facultad, formatocelda)
                        ws.write(row_num, 1, u'%s' % inscritos, formatocelda)
                        ws.write(row_num, 2, u'%s' % aprobados, formatocelda)
                        ws.write(row_num, 3, u'%s' % reprobados, formatocelda)



                        row_num += 1

                    workbook.close()
                    output.seek(0)
                    # Set up the Http response.
                    filename = 'reporte_aprobados_facultad_capacitacion_docente' + random.randint(1, 10000).__str__() + '.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename

                    return response
                except Exception as ex:
                    pass

            elif action == 'reportegeneral':
                try:
                    periodo = CapPeriodoDocente.objects.get(pk=int(request.GET['id']))
                    noti = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                        titulo='Excel reporte general de capacitaciones', destinatario=persona,
                                        url='',
                                        prioridad=1, app_label='SGA',
                                        fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                        en_proceso=True)
                    noti.save(request)
                    reporte_generalcapacitaciones_background(request=request, data=data, notiid=noti.pk , periodo=periodo).start()

                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})

                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass

            elif action == 'reportecapacitacionesaprobadas':
                try:
                    periodo = CapPeriodoDocente.objects.get(pk=int(request.GET['id']))
                    noti = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                        titulo='Excel reporte de capacitaciones aprobadas', destinatario=persona,
                                        url='',
                                        prioridad=1, app_label='SGA',
                                        fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                        en_proceso=True)
                    noti.save(request)
                    reporte_capacitaciones_aprobadas_background(request=request, data=data, notiid=noti.pk , periodo=periodo).start()

                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})

                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass

            elif action == 'reporteinscritosgeneral':
                try:
                    periodo = CapPeriodoDocente.objects.get(pk=int(request.GET['id']))
                    noti = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                        titulo='Excel reporte general de inscritos en capacitaciones', destinatario=persona,
                                        url='',
                                        prioridad=1, app_label='SGA',
                                        fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                        en_proceso=True)
                    noti.save(request)
                    reporte_generalcapacitaciones_inscritos_background(request=request, data=data, notiid=noti.pk , periodo=periodo).start()

                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})

                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass

            elif action == 'reporteinscritosfacultad':
                try:
                    periodo = CapPeriodoDocente.objects.get(pk=int(request.GET['id']))
                    noti = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                        titulo='Excel reporte general de inscritos facultad en capacitaciones', destinatario=persona,
                                        url='',
                                        prioridad=1, app_label='SGA',
                                        fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                        en_proceso=True)
                    noti.save(request)
                    reporte_generalcapacitaciones_facultad_background(request=request, data=data, notiid=noti.pk , periodo=periodo).start()

                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})

                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass

            elif action == 'reportetotalfacultad':
                try:
                    periodo = CapPeriodoDocente.objects.get(pk=int(request.GET['id']))
                    noti = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                     titulo='Excel reporte total de inscritos facultad en capacitaciones', destinatario=persona,
                                        url='',
                                        prioridad=1, app_label='SGA',
                                        fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                        en_proceso=True)
                    noti.save(request)
                    reporte_totalinscritos_facultad_background(request=request, data=data, notiid=noti.pk , periodo=periodo).start()

                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})

                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass

            elif action == 'reporteinscritoscarrera':
                try:
                    periodo = CapPeriodoDocente.objects.get(pk=int(request.GET['id']))
                    noti = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                        titulo='Excel reporte general de inscritos por carrera en capacitaciones', destinatario=persona,
                                        url='',
                                        prioridad=1, app_label='SGA',
                                        fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                        en_proceso=True)
                    noti.save(request)
                    reporte_inscritos_carrera_capdocente_background(request=request, data=data, notiid=noti.pk , periodo=periodo).start()

                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})

                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass


            #INSTRUCTOR
            if action == 'busquedainstructor':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    evento = CapEventoPeriodoDocente.objects.get(id=int(request.GET['ide']))
                    modalidades = evento.modalidadlaboral.values_list('id', flat=True) if evento.modalidadlaboral.exists() else [1, 2, 3, 4, 5, 6, 7]
                    if len(s) == 2:
                        persona = Persona.objects.filter(apellido1__icontains=s[0],apellido2__icontains=s[1],real=True).exclude(pk__in=lista).distinct()[:15]
                    else:
                        persona = Persona.objects.filter(Q(real=True) & (Q(nombres__contains=s[0]) | Q(apellido1__contains=s[0]) | Q(apellido2__contains=s[0]) | Q(cedula__contains=s[0]))).exclude(pk__in=lista).distinct()[:15]
                    data = {"result": True, "aData": [{"id": x.id, "name": x.flexbox_repr(), "aplica":
                        DistributivoPersona.objects.filter(estadopuesto__id=PUESTO_ACTIVO_ID, status=True, persona=x, modalidadlaboral_id__in=modalidades).distinct().exists()} for x in persona]}
                    return JsonResponse(data)
                except Exception as ex:
                    data = {"result": False, "mensaje": f"{ex.__str__()}", "aData": []}
                    return JsonResponse(data)

            if action == 'addinstructor':
                try:
                    data['title'] = u'Adicionar Instructor'
                    data['form'] = CapInstructorForm()
                    lista = CapInstructorDocente.objects.values_list('instructor_id').filter(capeventoperiodo_id=int(request.GET['id']), status=True)
                    data['eventoperiodo']=request.GET['id']
                    return render(request, "adm_capacitaciondocente/gestion/addinstructor.html", data)
                except Exception as ex:
                    pass

            if action == 'addnuevoinstructor':
                try:
                    data['title'] = u'Registrar datos del instructor'
                    data['eventoperiodo'] = CapEventoPeriodoDocente.objects.get(pk=int(request.GET['id']))
                    form = CapInscribirPersonaCapacitacionForm()
                    data['form'] = form
                    return render(request, "adm_capacitaciondocente/gestion/addnuevoinstructor.html", data)
                except Exception as ex:
                    pass

            if action == 'delinstructor':
                try:
                    data['title'] = u'Eliminar Instructor'
                    data['instructor'] = CapInstructorDocente.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitaciondocente/gestion/delinstructor.html", data)
                except Exception as ex:
                    pass

            if action == 'editinstructor':
                try:
                    data['title'] = u'Editar Instructor'
                    data['instructor'] = instructor=CapInstructorDocente.objects.get(pk=int(request.GET['id']))
                    lista = CapInstructorDocente.objects.values_list('instructor_id').filter(capeventoperiodo=instructor.capeventoperiodo, status=True).exclude(pk=instructor.id)
                    # form = CapInstructorForm(initial={'instructor':instructor.instructor_id,
                    #                                   'tipo': instructor.tipo,
                    #                                   'instructorprincipal': instructor.instructorprincipal})
                    form = CapInstructorForm(initial=model_to_dict(instructor))
                    data['periodo']= instructor.capeventoperiodo.periodo_id
                    form.editar(instructor)
                    data['form'] = form
                    return render(request, "adm_capacitaciondocente/gestion/editinstructor.html", data)
                except Exception as ex:
                    pass

            if action == 'instructor':
                try:
                    data['title'] = u'Instructor'
                    data['instructor'] = CapInstructorDocente.objects.filter(capeventoperiodo=int(request.GET['id']), status=True).order_by('-fecha_creacion')
                    data['idinstructor'] = request.GET['id']
                    data['eventoperiodo'] = CapEventoPeriodoDocente.objects.get(pk=int(request.GET['id']), status=True)
                    return render(request, "adm_capacitaciondocente/gestion/viewinstructor.html", data)
                except Exception as ex:
                    pass

            #HORARIOS
            if action == 'addclase':
                try:
                    data['title'] = u'Adicionar horario'
                    evento = CapEventoPeriodoDocente.objects.get(pk=int(request.GET['cepid']))
                    form = CapClaseForm(initial={'capeventoperiodo': evento,
                                                 'turno': CapTurnoDocente.objects.get(pk=request.GET['turno']),
                                                 'dia': request.GET['dia'],
                                                 'fechainicio': evento.fechainicio,
                                                 'fechafin': evento.fechafin})
                    data['cepid'] = evento.id
                    form.editar_grupo()
                    data['form'] = form
                    return render(request, "adm_capacitaciondocente/gestion/addclase.html", data)
                except Exception as ex:
                    pass

            if action == 'delclase':
                try:
                    data['title'] = u'Eliminar horario'
                    data['clase'] =clase= CapClaseDocente.objects.get(pk=int(request.GET['cid']))
                    data['eventoperiodo'] = clase.capeventoperiodo.id
                    return render(request, "adm_capacitaciondocente/gestion/delclase.html", data)
                except Exception as ex:
                    pass

            if action == 'editclase':
                try:
                    data['title'] = u'Editar horario'
                    clase = CapClaseDocente.objects.get(pk=int(request.GET['cid']))
                    form = CapClaseForm(initial={'capeventoperiodo': clase.capeventoperiodo,
                                                 'turno': clase.turno,
                                                 'fechainicio': clase.fechainicio,
                                                 'fechafin': clase.fechafin,
                                                 'dia': clase.dia})
                    data['cepid'] = clase.capeventoperiodo.id
                    data['claseid'] = clase.id
                    form.editar_grupo()
                    form.editar_turno()
                    data['form'] = form
                    return render(request, "adm_capacitaciondocente/gestion/editclase.html", data)
                except Exception as ex:
                    pass

            if action == 'calificar':
                try:
                    data['title'] = u'Calificar'
                    data['tarea'] = tarea = CapNotaDocente.objects.get(pk=int(request.GET['id']))
                    data['listadoinscritos'] = tarea.capdetallenotadocente_set.filter(status=True)
                    return render(request, 'adm_capacitaciondocente/gestion/calificar.html', data)
                except Exception as ex:
                    pass

            if action == 'calificageneral':
                try:
                    data['title'] = u'Calificación General'
                    data['instructor'] = instructor = CapInstructorDocente.objects.get(pk=int(request.GET['id']),
                                                                                    status=True)
                    data['tareas'] = tarea = CapNotaDocente.objects.filter(instructor=instructor)
                    data['listadoinscritos'] = instructor.capeventoperiodo.inscritos()
                    return render(request, 'adm_capacitaciondocente/gestion/calificargeneral.html', data)
                except Exception as ex:
                    pass


            if action == 'horario':
                try:
                    data['title'] = u'Horarios'
                    data['capeventoperiodo'] = None
                    data['eventoperiodoid'] = None
                    data['semana'] = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']
                    evento = CapEventoPeriodoDocente.objects.get(pk=int(request.GET['id']))
                    data['activo'] = datetime.now().date() <= evento.fechafin
                    data['turnos'] = CapTurnoDocente.objects.filter(status=True)
                    data['capeventoperiodo'] = evento
                    data['eventoperiodoid'] = evento.id
                    return render(request, "adm_capacitaciondocente/gestion/horario.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            #ASISTENCIA
            if action == 'asistencia':
                try:
                    data['title'] = u'Horarios'
                    dia = 0
                    clase_activa = False
                    capeventoperiodo = CapEventoPeriodoDocente.objects.get(pk=int(request.GET['id']))
                    semana = [[0, 'Hoy'], [1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'],[4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo'], [8, 'Todos']]
                    if 'd' in request.GET:
                        dia = int(request.GET['d'])
                        if dia == 8 :
                            data['dias'] = {1:'Lunes', 2: 'Martes', 3:'Miercoles',4:'Jueves', 5:'Viernes', 6:'Sabado', 7: 'Domingo'}
                        elif dia > 0 and dia < 8:
                            data['dias'] = {DIAS_CHOICES[dia-1][0]:  DIAS_CHOICES[dia-1][1]}
                    else:
                        clase_activa = True
                        data['fecha_hoy'] = datetime.now().date()
                        data['clases_hoy'] = capeventoperiodo.clases_activas()
                        data['dias'] = {DIAS_CHOICES[date.today().weekday()][0]: DIAS_CHOICES[date.today().weekday()][1]}
                    data['select_dia'] = dia
                    data['capeventoperiodo'] = capeventoperiodo
                    data['clase_activa'] = clase_activa
                    data['dia_list'] = semana
                    form = CapAsistenciaForm()
                    form.adicionar(capeventoperiodo)
                    data['form'] = form
                    return render(request, "adm_capacitaciondocente/gestion/asistencia.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'addasistencia':
                try:
                    revisar=False
                    data['title'] = u'Asistencia'
                    data['cabeceraasistencia'] = asistencia = CapCabeceraAsistenciaDocente.objects.get(pk=int(request.GET['id']))
                    data['clase']= asistencia.clase
                    data['listadoinscritos'] = asistencia.clase.capeventoperiodo.inscritos_aprobado()
                    if 'm' in request.GET:
                        revisar=True
                    data['revisar'] = revisar
                    return render(request, "adm_capacitaciondocente/gestion/addasistencia.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'delasistencia':
                try:
                    data['title'] = u'Eliminar asistencia'
                    data['cabeceraasistencia'] = CapCabeceraAsistenciaDocente.objects.get(pk=int(request.GET['id']))
                    data['dia'] = int(request.GET['d'])
                    return render(request, "adm_capacitaciondocente/gestion/delasistencia.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'detalle':
                try:
                    data = {}
                    cabecera = CapCabeceraSolicitudDocente.objects.get(pk=int(request.GET['id']))
                    data['cabecerasolicitud'] = cabecera
                    data['detallesolicitud'] = cabecera.capdetallesolicituddocente_set.all()
                    data['aprobador'] = persona
                    data['fecha'] = datetime.now().date()
                    data['solicitud_capacitacion'] = variable_valor('SOLICITUD_CAPACITACION')
                    data['pendiente_capacitacion'] = variable_valor('PENDIENTE_CAPACITACION')
                    data['aprobado_capacitacion'] = variable_valor('APROBADO_CAPACITACION')
                    data['rechazado_capacitacion'] = variable_valor('RECHAZADO_CAPACITACION')
                    template = get_template("adm_capacitaciondocente/gestion/detalle_aprobar.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'modelo':
                try:
                    request.session['viewactivoAreaConocimiento'] = 5
                    data['title'] = u'Modelo Evaluativo'
                    data['modelos'] = CapModeloEvaluativoDocente.objects.filter(status=True).order_by('fecha_creacion')
                    return render(request, 'adm_capacitaciondocente/gestion/viewmodeloevaluativo.html', data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'addmodelo':
                try:
                    data['title'] = u'Adicionar Modelo Evaluativo'
                    data['form'] = CapModeloEvaluativoDocenteForm()
                    return render(request, "adm_capacitaciondocente/gestion/addmodeloevaluativo.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'addmodelomodal':
                try:
                    data['title'] = u'Adicionar Modelo Evaluativo'
                    data['form'] = CapModeloEvaluativoDocenteForm()
                    data['action'] = request.GET['action']
                    template = get_template("adm_capacitaciondocente/gestion/modal/formaddperiodoevento.html")
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'data': template.render(data)})

            elif action == 'editmodelomodal':
                try:
                    data['title'] = u'Editar Modelo Evaluativo'
                    data['action'] = request.GET['action']
                    data['id'] = request.GET['id']
                    data['modelo'] = modelo = CapModeloEvaluativoDocente.objects.get(pk=int(request.GET['id']))
                    form = CapModeloEvaluativoDocenteForm(initial={'nombre': modelo.nombre,
                                                                   'principal': modelo.principal,
                                                                   'notaminima': modelo.notaminima,
                                                                   'notamaxima': modelo.notamaxima,
                                                                   'evaluacion': modelo.evaluacion})
                    data['form'] = form
                    template = get_template("adm_capacitaciondocente/gestion/modal/formaddperiodoevento.html")
                    return JsonResponse({'result': True, 'data' : template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'data': template.render(data)})

            elif action == 'delmodelo':
                try:
                    data['title'] = u'Eliminar Modelo Evaluativo'
                    data['evaluativo'] = CapModeloEvaluativoDocente.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitaciondocente/gestion/delmodeloevaluativo.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'modelogeneral':
                try:
                    request.session['viewactivoAreaConocimiento'] = 6
                    data['title'] = u'Modelo Evaluativo General'
                    data['modelos'] = CapModeloEvaluativoDocenteGeneral.objects.filter(status=True).order_by('orden')
                    return render(request, 'adm_capacitaciondocente/gestion/viewmodeloevaluativogeneral.html', data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'addmodelogeneral':
                try:
                    filtro = CapModeloEvaluativoDocenteGeneral.objects.filter(status=True)
                    form = CapModeloEvaluativoDocenteGeneralForm()
                    form.fields['modelo'].queryset = CapModeloEvaluativoDocente.objects.filter(status=True).exclude(
                        id__in=filtro.values_list('modelo__id', flat=True)).order_by('nombre')
                    form.fields['orden'].initial = filtro.count() + 1
                    data['form'] = form
                    data['action'] = 'addmodelogeneral'
                    template = get_template("adm_capacitaciondocente/gestion/modal/formaddperiodoevento.html")
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'data': template.render(data)})

            elif action == 'editmodelogeneral':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = CapModeloEvaluativoDocenteGeneral.objects.get(pk=request.GET['id'])

                    data['form'] = form = CapModeloEvaluativoDocenteGeneralForm(initial=model_to_dict(filtro))

                    data['action'] = 'editmodelogeneral'
                    template = get_template("adm_capacitaciondocente/gestion/modal/formaddperiodoevento.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'data': template.render(data)})

            elif action == 'delmodelogeneral':
                try:
                    data['title'] = u'Eliminar Modelo Evaluativo General'
                    data['evaluativo'] = CapModeloEvaluativoDocenteGeneral.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitaciondocente/gestion/delmodeloevaluativogeneral.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'confirmar_actualizacion_modelo':
                try:
                    data['title'] = u'Actualización moodle'
                    data['evento'] = CapEventoPeriodoDocente.objects.get(pk=request.GET['id'])
                    data['clave'] = request.GET['clave']
                    return render(request, "adm_capacitaciondocente/gestion/confirmar_actualizacion_modelo.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'viewcronograma':
                try:
                    id = int(request.GET.get('id', '0'))
                    try:
                        data['eCapPeriodoDocente'] = eCapPeriodoDocente = CapPeriodoDocente.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro periodo.")
                    data['title'] = f'Cronograma de INC'
                    data['subtitle'] = eCapPeriodoDocente.nombre
                    return render(request, "adm_capacitaciondocente/gestion/viewcronograma.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            if action == 'loadFrmEtapa':
                try:
                    data['idForm'] = 'formEtapa'
                    data['action'] = 'saveEtapaPeriodo'
                    idp = int(request.GET.get('idp', '0'))
                    id = int(request.GET.get('id', '0'))
                    if idp == 0:
                        raise NameError(u"No se encontro parametro de periodo")
                    try:
                        data['eCapPeriodoDocente'] = eCapPeriodoDocente = CapPeriodoDocente.objects.get(pk=idp)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro el periodo.")
                    try:
                        initial = model_to_dict(CapCronogramaNecesidad.objects.get(pk=id))
                    except ObjectDoesNotExist:
                        initial = {}

                    form = CapPeriodoCronogramaForm(initial=initial)
                    data['form'] = form
                    data['id'] = id
                    template = get_template("adm_capacitaciondocente/gestion/modal/frmCronogramaEtapa.html")
                    return JsonResponse({"result": True, 'html': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            #REPORTES

            elif action == 'reporteactividades':
                try:
                    noti = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                        titulo='Excel reporte general de resultados de encuesta',
                                        destinatario=persona,
                                        url='',
                                        prioridad=1, app_label='SGA',
                                        fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                        en_proceso=True)
                    noti.save(request)
                    reporte_generalenncuesta_background(request=request, notiid=noti.pk).start()
                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Periodo de evento'
                data['eCapPeriodoDocentes'] = CapPeriodoDocente.objects.filter(status=True).order_by('fechainicio')
                d = datetime.now()
                data['horasegundo'] = d.strftime('%Y%m%d_%H%M%S')
                return render(request, "adm_capacitaciondocente/gestion/viewperiodo.html", data)
            except Exception as ex:
                return HttpResponseRedirect(f"/?info={ex.__str__()}")