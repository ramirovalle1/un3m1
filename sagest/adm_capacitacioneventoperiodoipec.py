# -*- coding: UTF-8 -*-
import json
import os
import sys
import time
from datetime import datetime, date, timedelta
import random
import pyqrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, connections
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template

import settings
from decorators import secure_module
from xlwt import *
from xlwt import easyxf
import xlwt

from moodle.models import UserAuth
from sagest.forms import CapPeriodoIpecForm, \
    CapEventoIpecForm, CapTurnoIpecForm, CapEventoPeriodoIpecForm, CapConfiguracionIpecForm, \
    ModeloEvaluativoGeneralForm, CapEnfocadaIpecForm, \
    CapInstructorIpecForm, CapClaseIpecForm, CapInscribirIpecForm, CapAsistenciaIpecForm, \
    CapNotaIpecForm, CapInscribirPersonaIpecForm, CapModeloEvaluativoTareaIpecForm, SeleccionarInstructorIpecForm, \
    InscritoEventoIpecForm, ObservacionInscritoEventoIpecForm, MoverInscritoEventoIpecForm, TipoOtroRubroIpecForm, \
    CapEventoPeriodoIpecFacturaTotalForm, CapInscribirIpecForm2, GenerarRubroDiferidoForm, \
    ConfigurarcionMejoraContinuaForm
from sagest.models import DistributivoPersona, CapPeriodoIpec, CapEventoIpec, CapTurnoIpec, CapModeloEvaluativoGeneral, \
    CapEventoPeriodoIpec, \
    CapConfiguracionIpec, \
    CapEnfocadaIpec, CapInstructorIpec, CapClaseIpec, CapInscritoIpec, Rubro, CapCabeceraAsistenciaIpec, \
    CapDetalleAsistenciaIpec, CapNotaIpec, CapDetalleNotaIpec, CapModeloEvaluativoTareaIpec, \
    CapRegistrarDatosInscritoIpec, PagoLiquidacion, CapInstructor, TipoOtroRubro, Pago, \
    CapEventoPeriodoFacturaTotalIpec, Departamento, PersonaDepartamentoFirmas, CuentaContable, \
    ConfigurarcionMejoraContinua
from settings import PUESTO_ACTIVO_ID, EMAIL_DOMAIN, EMAIL_INSTITUCIONAL_AUTOMATICO, SITE_STORAGE, SITE_POPPLER
from sga.commonviews import adduserdata, obtener_reporte, actualizar_nota_instructor
from sga.funciones import MiPaginador, log, generar_nombre, calculate_username, generar_usuario, variable_valor, \
    convertir_fecha, null_to_decimal, puede_realizar_accion, resetear_clave, remover_caracteres_especiales_unicode, notificacion, \
    salvaRubros, salvaRubrosEpunemiEdcon
from sga.models import Administrativo, Persona, DIAS_CHOICES, CUENTAS_CORREOS, Externo, Matricula, RecordAcademico, \
    Provincia, miinstitucion, Periodo, MESES_CHOICES, Inscripcion, FirmaPersona
from django.db.models import Max, Q
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsavevistaprevia, conviert_html_to_pdf, conviert_html_to_pdfsaveqrcertificadoinstructor, \
    conviert_html_to_pdfsaveqrcertificado, conviert_html_to_pdfsave, conviert_html_to_pdfsaveqrcertificadoinstructor2
from pdf2image import convert_from_bytes
from sga.tasks import send_html_mail, conectar_cuenta
from decimal import Decimal, ROUND_UP
from django.db.models import Sum, Q, Count
from dateutil.relativedelta import relativedelta
import zipfile
import psycopg2

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    global ex
    data = {}
    lista = []
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user

    data['IS_DEBUG'] = IS_DEBUG = variable_valor('IS_DEBUG')
    data['version'] = version = datetime.now().strftime('%Y%m%d_%H%M%S%f')
    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema = 'https://sga.unemi.edu.ec' if not IS_DEBUG else 'http://127.0.0.1:8000'

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addmodelogeneral':
            try:
                with transaction.atomic():
                    if CapModeloEvaluativoGeneral.objects.filter(status=True,
                                                                 modelo_id=int(request.POST['modelo'])).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Modelo Evaluativo ya existe."}, safe=False)
                    form = ModeloEvaluativoGeneralForm(request.POST)
                    if form.is_valid():
                        filtro = CapModeloEvaluativoGeneral(modelo=form.cleaned_data['modelo'],
                                                            orden=form.cleaned_data['orden'])
                        filtro.save(request)
                        log(u'Adiciono Modelo Evaluativo a la configuración: %s' % filtro, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'editmodelogeneral':
            try:
                with transaction.atomic():
                    filtro = CapModeloEvaluativoGeneral.objects.get(pk=request.POST['id'])
                    f = ModeloEvaluativoGeneralForm(request.POST)
                    if f.is_valid():
                        filtro.orden = f.cleaned_data['orden']
                        filtro.save(request)
                        log(u'Modificó Modelo Evaluativo de la configuración: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        if action == 'confimodelogeneral':
            try:
                with transaction.atomic():
                    filtro = CapModeloEvaluativoGeneral.objects.filter(status=True).order_by('orden')
                    instructor = CapInstructorIpec.objects.get(pk=int(request.POST['id']))
                    for f in filtro:
                        if not CapNotaIpec.objects.filter(status=True, modelo=f.modelo,
                                                          instructor_id=instructor.pk).exists():
                            modelonota = CapNotaIpec(modelo=f.modelo,
                                                     fecha=datetime.now().date(),
                                                     instructor_id=instructor.pk)
                            modelonota.save(request)
                            log(u'Adiciono Modelo Evaluativo Instructor: %s' % modelonota, request, "add")
                    return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        # PERIODO
        if action == 'addperiodo':
            try:
                form = CapPeriodoIpecForm(request.POST, request.FILES)
                if form.is_valid():
                    nombres = form.cleaned_data['nombre']
                    if form.cleaned_data['fechainicio'] < form.cleaned_data['fechafin']:
                        if CapPeriodoIpec.objects.filter(nombre=nombres, status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                        periodo = CapPeriodoIpec(nombre=form.cleaned_data['nombre'],
                                                 descripcion=form.cleaned_data['descripcion'],
                                                 fechainicio=form.cleaned_data['fechainicio'],
                                                 fechafin=form.cleaned_data['fechafin'])
                        periodo.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("capacitacionIPEC_", newfile._name)
                            periodo.archivo = newfile
                            periodo.save(request)
                        if 'instructivo' in request.FILES:
                            newfile = request.FILES['instructivo']
                            newfile._name = generar_nombre("instructivoIPEC_", newfile._name)
                            periodo.instructivo = newfile
                            periodo.save(request)
                        log(u'Agrego Período de Evento IPEC: %s - [%s]' % (periodo, periodo.id), request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"La Fecha esta mal ingresados."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editinscrito':
            try:
                inscrito = CapInscritoIpec.objects.get(pk=request.POST['id'])
                f = InscritoEventoIpecForm(request.POST)
                if f.is_valid():
                    inscritoipec = Persona.objects.get(pk=inscrito.participante.id)
                    inscritoipec.nombres = f.cleaned_data['nombres']
                    inscritoipec.apellido1 = f.cleaned_data['apellido1']
                    inscritoipec.apellido2 = f.cleaned_data['apellido2']
                    inscritoipec.nacimiento = f.cleaned_data['nacimiento']
                    inscritoipec.sexo = f.cleaned_data['sexo']
                    inscritoipec.pais = f.cleaned_data['pais']
                    inscritoipec.provincia = f.cleaned_data['provincia']
                    inscritoipec.canton = f.cleaned_data['canton']
                    inscritoipec.parroquia = f.cleaned_data['parroquia']
                    inscritoipec.sector = f.cleaned_data['sector']
                    inscritoipec.direccion = f.cleaned_data['direccion']
                    inscritoipec.direccion2 = f.cleaned_data['direccion2']
                    inscritoipec.num_direccion = f.cleaned_data['num_direccion']
                    inscritoipec.telefono = f.cleaned_data['telefono']
                    inscritoipec.telefono_conv = f.cleaned_data['telefono_conv']
                    inscritoipec.email = f.cleaned_data['email']
                    inscritoipec.save(request)
                    log(u'Modifico inscrito ipec: %s' % inscritoipec, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editperiodo':
            try:
                form = CapPeriodoIpecForm(request.POST, request.FILES)
                if form.is_valid():
                    periodo = CapPeriodoIpec.objects.get(pk=int(request.POST['id']))
                    periodo.descripcion = form.cleaned_data['descripcion']
                    periodo.nombre = form.cleaned_data['nombre']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("capacitacionTH_", newfile._name)
                        periodo.archivo = newfile
                    if 'instructivo' in request.FILES:
                        newfile = request.FILES['instructivo']
                        newfile._name = generar_nombre("instructivoIPEC_", newfile._name)
                        periodo.instructivo = newfile
                        periodo.save(request)
                    if periodo.esta_cap_evento_periodo_activo():
                        periodo.save(request)
                        log(u'Editar Periodo de Capacitación IPEC: %s [%s]' % (periodo, periodo.id), request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        if form.cleaned_data['fechainicio'] < form.cleaned_data['fechafin']:
                            periodo.fechainicio = form.cleaned_data['fechainicio']
                            periodo.fechafin = form.cleaned_data['fechafin']
                            periodo.save(request)
                            log(u'Editar Periodo de Capacitación IPEC: %s - [%s]' % (periodo, periodo.id), request,
                                "edit")
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"La Fecha esta mal ingresados."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delperiodo':
            try:
                periodo = CapPeriodoIpec.objects.get(pk=int(request.POST['id']))
                if periodo.esta_cap_evento_periodo_activo():
                    return JsonResponse({"result": "bad",
                                         "mensaje": u"No se puede Eliminar el Periodo, tiene planificacion de evento Activas.."})
                log(u'Elimino Periodo de Capacitación IPEC: %s - [%s]' % (periodo, periodo.id), request, "del")
                periodo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        # EVENTO
        elif action == 'addevento':
            try:
                form = CapEventoIpecForm(request.POST)
                if form.is_valid():
                    if CapEventoIpec.objects.filter(nombre=form.cleaned_data['nombre'], status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                    evento = CapEventoIpec(nombre=form.cleaned_data['nombre'])
                    evento.save(request)
                    log(u'Agrego Evento en Capacitación IPEC: %s - [%s]' % (evento, evento.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editevento':
            try:
                form = CapEventoIpecForm(request.POST)
                if form.is_valid():
                    evento = CapEventoIpec.objects.get(pk=int(request.POST['id']))
                    evento.nombre = form.cleaned_data['nombre']
                    evento.save(request)
                    log(u'Editar Evento en Capacitación: %s - [%s]' % (evento, evento.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delevento':
            try:
                evento = CapEventoIpec.objects.get(pk=int(request.POST['id']))
                if evento.esta_cap_evento_activo():
                    return JsonResponse({"result": "bad",
                                         "mensaje": u"No se puede Eliminar, se esta utilizando en Planificación de Eventos.."})
                log(u'Elimino Evento en Capacitacion IPEC: %s - [%s]' % (evento, evento.id), request, "del")
                evento.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        # TURNO
        elif action == 'addturno':
            try:
                form = CapTurnoIpecForm(request.POST)
                if form.is_valid():
                    if CapTurnoIpec.objects.values('id').filter(turno=form.cleaned_data['turno'], status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El Turno ya existe."})
                    # if CapTurnoIpec.objects.filter(horainicio=form.cleaned_data['horainicio'], status=True).exists():
                    #     return JsonResponse({"result": "bad", "mensaje": u"La hora inicio ya existe."})
                    # if CapTurnoIpec.objects.filter(horafin=form.cleaned_data['horafin'], status=True).exists():
                    #     return JsonResponse({"result": "bad", "mensaje": u"La hora fin ya existe."})
                    if form.cleaned_data['horainicio'] > form.cleaned_data['horafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"Las hora fin no debe ser mayor."})
                    datos = json.loads(request.POST['lista_items1'])
                    horas = 0
                    for elemento in datos:
                        horas = float(elemento['horas'])
                    turno = CapTurnoIpec(turno=request.POST['turno'],
                                         horainicio=form.cleaned_data['horainicio'],
                                         horafin=form.cleaned_data['horafin'],
                                         horas=horas)
                    turno.save(request)
                    log(u'Adiciono Turno en Capacitación IPEC: %s - [%s]' % (turno, turno.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editturno':
            try:
                form = CapTurnoIpecForm(request.POST)
                if form.is_valid():
                    turno = CapTurnoIpec.objects.get(pk=int(request.POST['id']))
                    # if CapTurnoIpec.objects.filter(horainicio=form.cleaned_data['horainicio'], status=True).exclude(pk=turno.id).exists():
                    #     return JsonResponse({"result": "bad", "mensaje": u"La hora inicio ya existe."})
                    # if CapTurnoIpec.objects.filter(horafin=form.cleaned_data['horafin'], status=True).exclude(pk=turno.id).exists():
                    #     return JsonResponse({"result": "bad", "mensaje": u"La hora fin ya existe."})
                    if form.cleaned_data['horainicio'] > form.cleaned_data['horafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"Las hora fin no debe ser mayor."})
                    datos = json.loads(request.POST['lista_items1'])
                    horas = 0
                    for elemento in datos:
                        horas = float(elemento['horas'])
                    turno.horainicio = form.cleaned_data['horainicio']
                    turno.horafin = form.cleaned_data['horafin']
                    turno.horas = horas
                    turno.save(request)
                    log(u'Edito Turno en Capacitación IPEC: %s - [%s]' % (turno, turno.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delturno':
            try:
                turno = CapTurnoIpec.objects.get(pk=int(request.POST['id']))
                if turno.capclaseipec_set.filter(status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, se esta usando en horarios"})
                log(u'Elimino Turno en Capacitación IPEC: %s - [%s]' % (turno, turno.id), request, "del")
                turno.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        # ENFOQUE
        elif action == 'addenfoque':
            try:
                form = CapEnfocadaIpecForm(request.POST)
                if form.is_valid():
                    if CapEnfocadaIpec.objects.filter(nombre=form.cleaned_data['nombre'], status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                    enfo = CapEnfocadaIpec(nombre=form.cleaned_data['nombre'])
                    enfo.save(request)
                    log(u'Adiciono Enfoque en Capacitación IPEC: %s - [%s]' % (enfo, enfo.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editenfoque':
            try:
                form = CapEnfocadaIpecForm(request.POST)
                if form.is_valid():
                    enfo = CapEnfocadaIpec.objects.get(pk=int(request.POST['id']))
                    enfo.nombre = form.cleaned_data['nombre']
                    enfo.save(request)
                    log(u'Editar Enfoque en Capacitación IPEC: %s - [%s]' % (enfo, enfo.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delenfoque':
            try:
                enfo = CapEnfocadaIpec.objects.get(pk=int(request.POST['id']))
                if enfo.capeventoperiodoipec_set.filter(status=True).exists():
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"No se puede eliminar, esta usado en planificación de evento."})
                log(u'Elimino Enfoque en Capacitación IPEC: %s - [%s]' % (enfo, enfo.id), request, "del")
                enfo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        # NOTAS
        elif action == 'modelonotas':
            try:
                instructor = CapInstructorIpec.objects.get(pk=int(request.POST['id']))
                modelos = instructor.modelo_sin_utilizar()
                return JsonResponse({"result": "ok", 'instructor': instructor.instructor.nombre_completo_inverso(),
                                     'modelos': [{'id': modelo.id, 'nombre': modelo.__str__()} for modelo in modelos]})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

        elif action == 'addmodelonotas':
            try:
                modelonota = CapNotaIpec(modelo_id=int(request.POST['idm']),
                                         fecha=datetime.now().date(),
                                         instructor_id=int(request.POST['idi']))
                modelonota.save(request)
                log(u'Agrego Modelo en Notas de Capacitación IPEC: %s - [%s]' % (modelonota, modelonota.id), request,
                    "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delmodelonota':
            try:
                modelonota = CapNotaIpec.objects.get(pk=int(request.POST['id']))
                log(u'Elimino modelo en nota de Capacitación IPEC: %s - [%s]' % (modelonota, modelonota.id), request,
                    "del")
                modelonota.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'updatenota':
            try:
                detalle = CapDetalleNotaIpec.objects.get(pk=int(request.POST['id']))
                nota = float(request.POST['vc'])
                if not nota:
                    nota = None
                cupoanterior = detalle.nota
                detalle.nota = nota
                detalle.save(request)
                log(u'Actualizo nota en tarea de capacitacion IPEC: %s cupo anterior: %s cupo actual: %s' % (
                    detalle, str(cupoanterior), str(detalle.nota)), request, "edit")
                if 'idl' in request.POST:
                    capinscritoipec = CapInscritoIpec.objects.get(pk=int(request.POST['idl']))
                    nofinal = capinscritoipec.nota_total_evento_porinstructor(
                        detalle.cabeceranota.instructor.capeventoperiodo.id, detalle.cabeceranota.instructor.pk)
                    return JsonResponse({'result': 'ok', 'valor': detalle.nota, 'nofinal': nofinal})
                else:
                    return JsonResponse({'result': 'ok', 'valor': detalle.nota})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u"Error al actualizar la nota."})

        elif action == 'observacion':
            try:
                detalle = CapDetalleNotaIpec.objects.get(pk=request.POST['id'])
                detalle.observacion = request.POST['valor']
                detalle.save(request)
                log(u'Actualizo observacion en tarea de capacitacion IPEC: %s ' % detalle.observacion, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'calificar':
            try:
                tarea = CapNotaIpec.objects.get(pk=int(request.POST['id']), status=True)
                if not tarea.instructor.capeventoperiodo.exiten_inscritos():
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"No puede continuar, porque no existen inscritos."})
                for inscrito in tarea.instructor.capeventoperiodo.inscritos():
                    if not inscrito.capdetallenotaipec_set.filter(status=True, cabeceranota=tarea,
                                                                  inscrito=inscrito).exists():
                        detalle = CapDetalleNotaIpec(cabeceranota=tarea, inscrito=inscrito)
                        detalle.save(request)
                        log(u'Adicionado inscrito para calificar tarea de capacitacion IPEC: %s - [%s]' % (
                            detalle, detalle.id), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'calificageneral':
            try:
                instructor = CapInstructorIpec.objects.get(pk=int(request.POST['id']), status=True)
                if not instructor.capeventoperiodo.exiten_inscritos():
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"No puede continuar, porque no existen inscritos."})
                for inscrito in instructor.capeventoperiodo.inscritos():
                    for tarea in instructor.capnotaipec_set.all():
                        if not inscrito.capdetallenotaipec_set.filter(status=True, cabeceranota=tarea,
                                                                      inscrito=inscrito).exists():
                            detalle = CapDetalleNotaIpec(cabeceranota=tarea, inscrito=inscrito)
                            detalle.save(request)
                            log(u'Adicionado inscrito para cadlificar tarea de capacitacion IPEC: %s - [%s]' % (
                                detalle, detalle.id), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # CONFIGURACION
        elif action == 'configuracion':
            try:
                form = CapConfiguracionIpecForm(request.POST)
                if form.is_valid():
                    if not form.cleaned_data['minasistencia'] > 0 or not form.cleaned_data['minnota'] > 0:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"La minima nota y asistencia debe ser mayor a cero ."})
                    configuracion = CapConfiguracionIpec.objects.filter()
                    if configuracion.exists():
                        configuracion = configuracion[0]
                        log(u'Edito configuración de capacitación IPEC: %s [%s]' % (configuracion, configuracion.id),
                            request, "edit")
                    else:
                        configuracion = CapConfiguracionIpec()
                        log(u'Adiciono configuración de capacitación IPEC: %s [%s]' % (configuracion, configuracion.id),
                            request, "add")
                    aprobado2 = DistributivoPersona.objects.get(pk=form.cleaned_data['aprobado2'])
                    aprobado3 = DistributivoPersona.objects.get(pk=form.cleaned_data['aprobado3'])
                    configuracion.minasistencia = form.cleaned_data['minasistencia']
                    configuracion.minnota = form.cleaned_data['minnota']
                    configuracion.aprobado2 = aprobado2.persona
                    configuracion.aprobado3 = aprobado3.persona
                    configuracion.denominacionaprobado2 = aprobado2.denominacionpuesto
                    configuracion.denominacionaprobado3 = aprobado3.denominacionpuesto
                    configuracion.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'configuracionfirma':
            try:
                form = ConfigurarcionMejoraContinuaForm(request.POST,request.FILES)
                if form.is_valid():
                    confi = ConfigurarcionMejoraContinua(
                        nombre=form.cleaned_data['nombre'],
                        cargo=form.cleaned_data['cargo'],
                        orden=form.cleaned_data['orden'],
                        firma=request.FILES['firma'],
                        curso_id=int(request.POST['id'])
                    )
                    confi.save(request)
                    cap_evento = CapEventoPeriodoIpec.objects.get(pk=int(request.POST['id']))
                    if cap_evento.configuraciondefirmas == False:
                        cap_evento.configuraciondefirmas = True
                        cap_evento.save(request)
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editconfiguracionfirma':
            try:
                form = ConfigurarcionMejoraContinuaForm(request.POST, request.FILES)
                modelo = ConfigurarcionMejoraContinua.objects.get(pk=int(request.POST['id']))
                firma_archivo = request.FILES.get('firma', None)
                form.chek_file(modelo.firma, firma_archivo)
                if firma_archivo:
                    modelo.firma = firma_archivo
                if form.is_valid():
                    modelo.nombre = form.cleaned_data['nombre']
                    modelo.cargo = form.cleaned_data['cargo']
                    modelo.orden = form.cleaned_data['orden']
                    modelo.firma = modelo.firma
                    modelo.save(request)
                    log(u'Edito Configuracion Firma : %s - [%s]' % (modelo, modelo.id),
                        request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delconfiguracionfirma':
            try:
                evento = ConfigurarcionMejoraContinua.objects.get(pk=int(request.POST['id']))
                configuraciones = evento.curso
                log(u'Elimino Configuracion de Evento: %s - [%s] ' % (evento, evento.id), request,
                    "del")
                evento.delete()
                if not ConfigurarcionMejoraContinua.objects.filter(curso=configuraciones).exists():
                    if configuraciones.configuraciondefirmas == True:
                        configuraciones.configuraciondefirmas = False
                        configuraciones.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        # EVENTO PERIODO
        elif action == 'addperiodoevento':
            try:
                form = CapEventoPeriodoIpecForm(request.POST)
                if form.is_valid():
                    tipootrorubro = None
                    generarubro = False
                    fechacertificado = ''
                    periodo = CapPeriodoIpec.objects.get(pk=int(request.POST['periodo']))
                    if form.cleaned_data['fechacertificado']:
                        fechacertificado = form.cleaned_data['fechacertificado']
                    if form.cleaned_data['tipootrorubro']:
                        tipootrorubro = form.cleaned_data['tipootrorubro']
                        generarubro = True
                    if not form.cleaned_data['fechainicio'] >= periodo.fechainicio or not form.cleaned_data[
                                                                                              'fechafin'] <= periodo.fechafin:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Las fecha no puede ser mayor a las fecha del periodo."})
                    if not form.cleaned_data['responsable']:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe ingresar el responsable del evento."})
                    if not form.cleaned_data['fechainicio'] <= form.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ser mayor la fecha de inicio."})
                    if 'imagen' in request.FILES:
                        newfile = request.FILES['imagen']
                        if newfile:
                            newfile._name = generar_nombre("capacitacion_", newfile._name)
                            configuracion = CapConfiguracionIpec.objects.all()
                            evento = CapEventoPeriodoIpec(periodo=periodo,
                                                          capevento=form.cleaned_data['capevento'],
                                                          tiporubro_id=tipootrorubro,
                                                          horas=form.cleaned_data['horas'],
                                                          costo=form.cleaned_data['costo'],
                                                          costoexterno=form.cleaned_data['costoexterno'],
                                                          objetivo=form.cleaned_data['objetivo'],
                                                          observacion=form.cleaned_data['observacion'],
                                                          minasistencia=form.cleaned_data['minasistencia'],
                                                          minnota=form.cleaned_data['minnota'],
                                                          tipoparticipacion=form.cleaned_data['tipoparticipacion'],
                                                          contextocapacitacion=form.cleaned_data[
                                                              'contextocapacitacion'],
                                                          modalidad=form.cleaned_data['modalidad'],
                                                          tipocertificacion=form.cleaned_data['tipocertificacion'],
                                                          tipocapacitacion=form.cleaned_data['tipocapacitacion'],
                                                          areaconocimiento=form.cleaned_data['areaconocimiento'],
                                                          aula=form.cleaned_data['aula'],
                                                          fechainicio=form.cleaned_data['fechainicio'],
                                                          fechafin=form.cleaned_data['fechafin'],
                                                          fechainicioinscripcion=form.cleaned_data[
                                                              'fechainiinscripcion'],
                                                          fechafininscripcion=form.cleaned_data['fechafininscripcion'],
                                                          fechamaxpago=form.cleaned_data['fechamaxpago'],
                                                          cupo=form.cleaned_data['cupo'],
                                                          enfoque=form.cleaned_data['enfoque'],
                                                          visualizar=form.cleaned_data['visualizar'],
                                                          publicarinscripcion=form.cleaned_data['publicarinscripcion'],
                                                          contenido=form.cleaned_data['contenido'],
                                                          aprobado2=configuracion[0].aprobado2,
                                                          aprobado3=configuracion[0].aprobado3,
                                                          denominacionaprobado2=configuracion[0].denominacionaprobado2,
                                                          denominacionaprobado3=configuracion[0].denominacionaprobado3,
                                                          generarrubro=generarubro,
                                                          fechacertificado=fechacertificado,
                                                          modeloevaludativoindividual=form.cleaned_data[
                                                              'modeloevaludativoindividual'],
                                                          notificarubro=form.cleaned_data[
                                                              'notificarubro'],
                                                          seguimientograduado=form.cleaned_data[
                                                              'seguimientograduado'],
                                                          responsable=Administrativo.objects.get(
                                                              pk=form.cleaned_data['responsable']).persona,
                                                          archivo=newfile)
                    else:
                        configuracion = CapConfiguracionIpec.objects.all()
                        evento = CapEventoPeriodoIpec(periodo=periodo,
                                                      capevento=form.cleaned_data['capevento'],
                                                      tiporubro_id=tipootrorubro,
                                                      horas=form.cleaned_data['horas'],
                                                      costo=form.cleaned_data['costo'],
                                                      costoexterno=form.cleaned_data['costoexterno'],
                                                      objetivo=form.cleaned_data['objetivo'],
                                                      observacion=form.cleaned_data['observacion'],
                                                      minasistencia=form.cleaned_data['minasistencia'],
                                                      minnota=form.cleaned_data['minnota'],
                                                      tipoparticipacion=form.cleaned_data['tipoparticipacion'],
                                                      contextocapacitacion=form.cleaned_data['contextocapacitacion'],
                                                      modalidad=form.cleaned_data['modalidad'],
                                                      tipocertificacion=form.cleaned_data['tipocertificacion'],
                                                      tipocapacitacion=form.cleaned_data['tipocapacitacion'],
                                                      areaconocimiento=form.cleaned_data['areaconocimiento'],
                                                      aula=form.cleaned_data['aula'],
                                                      fechainicio=form.cleaned_data['fechainicio'],
                                                      fechafin=form.cleaned_data['fechafin'],
                                                      fechainicioinscripcion=form.cleaned_data['fechainiinscripcion'],
                                                      fechafininscripcion=form.cleaned_data['fechafininscripcion'],
                                                      fechamaxpago=form.cleaned_data['fechamaxpago'],
                                                      cupo=form.cleaned_data['cupo'],
                                                      enfoque=form.cleaned_data['enfoque'],
                                                      visualizar=form.cleaned_data['visualizar'],
                                                      publicarinscripcion=form.cleaned_data['publicarinscripcion'],
                                                      contenido=form.cleaned_data['contenido'],
                                                      aprobado2=configuracion[0].aprobado2,
                                                      aprobado3=configuracion[0].aprobado3,
                                                      denominacionaprobado2=configuracion[0].denominacionaprobado2,
                                                      denominacionaprobado3=configuracion[0].denominacionaprobado3,
                                                      generarrubro=generarubro,
                                                      fechacertificado=fechacertificado,
                                                      modeloevaludativoindividual=form.cleaned_data[
                                                          'modeloevaludativoindividual'],
                                                      notificarubro=form.cleaned_data[
                                                          'notificarubro'],
                                                      responsable=Administrativo.objects.get(
                                                          pk=form.cleaned_data['responsable']).persona)
                    evento.save(request)
                    if 'brochure' in request.FILES:
                        newfile = request.FILES['brochure']
                        if newfile:
                            newfile._name = generar_nombre("_", newfile._name)
                            evento.brochure = newfile
                            evento.save(request)

                    log(u'Agrego Planificación de Evento en Capacitacion IPEC: %s - [%s] ' % (evento, evento.id),
                        request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": (u"Error al guardar los datos. %s" % ex)})

        elif action == 'editperiodoevento':
            try:
                form = CapEventoPeriodoIpecForm(request.POST)
                # form.editar_rubro_habilitar()
                if form.is_valid():
                    evento = CapEventoPeriodoIpec.objects.get(pk=int(request.POST['id']))
                    if not form.cleaned_data['fechainicio'] >= evento.periodo.fechainicio or not form.cleaned_data[
                                                                                                     'fechafin'] <= evento.periodo.fechafin:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Las fecha no puede ser mayor a las fecha del periodo."})
                    if not form.cleaned_data['fechainicio'] <= form.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ser mayor la fecha de inicio."})
                    if 'imagen' in request.FILES:
                        newfile = request.FILES['imagen']
                        if newfile:
                            newfile._name = generar_nombre("_", newfile._name)
                            evento.archivo = newfile
                    if 'banner' in request.FILES:
                        newfile = request.FILES['banner']
                        if newfile:
                            newfile._name = generar_nombre("_", newfile._name)
                            evento.banner = newfile
                    evento.capevento = form.cleaned_data['capevento']
                    evento.horas = form.cleaned_data['horas']
                    evento.costo = form.cleaned_data['costo']
                    evento.costoexterno = form.cleaned_data['costoexterno']
                    evento.objetivo = form.cleaned_data['objetivo']
                    evento.observacion = form.cleaned_data['observacion']
                    if form.cleaned_data['fechacertificado']:
                        evento.fechacertificado = form.cleaned_data['fechacertificado']
                    evento.minasistencia = form.cleaned_data['minasistencia']
                    evento.minnota = form.cleaned_data['minnota']
                    evento.aula = form.cleaned_data['aula']
                    evento.fechainicio = form.cleaned_data['fechainicio']
                    evento.fechafin = form.cleaned_data['fechafin']
                    evento.fechainicioinscripcion = form.cleaned_data['fechainiinscripcion']
                    evento.fechafininscripcion = form.cleaned_data['fechafininscripcion']
                    evento.fechamaxpago = form.cleaned_data['fechamaxpago']
                    evento.tipoparticipacion = form.cleaned_data['tipoparticipacion']
                    evento.contextocapacitacion = form.cleaned_data['contextocapacitacion']
                    evento.modalidad = form.cleaned_data['modalidad']
                    evento.tipocertificacion = form.cleaned_data['tipocertificacion']
                    evento.tipocapacitacion = form.cleaned_data['tipocapacitacion']
                    evento.areaconocimiento = form.cleaned_data['areaconocimiento']
                    evento.visualizar = form.cleaned_data['visualizar']
                    evento.publicarinscripcion = form.cleaned_data['publicarinscripcion']
                    evento.enfoque = form.cleaned_data['enfoque']
                    evento.cupo = form.cleaned_data['cupo']
                    evento.contenido = form.cleaned_data['contenido']
                    evento.envionotaemail = form.cleaned_data['envionotaemail']
                    evento.modeloevaludativoindividual = form.cleaned_data['modeloevaludativoindividual']
                    evento.mes = form.cleaned_data['mes']
                    evento.notificarubro = form.cleaned_data['notificarubro']
                    evento.seguimientograduado = form.cleaned_data['seguimientograduado']

                    if form.cleaned_data['tipootrorubro']:
                        evento.tiporubro_id = form.cleaned_data['tipootrorubro']
                        evento.generarrubro = True
                    else:
                        evento.generarrubro = False
                    evento.responsable = Administrativo.objects.get(pk=form.cleaned_data['responsable']).persona
                    configuracion = CapConfiguracionIpec.objects.all()
                    evento.aprobado2 = configuracion[0].aprobado2
                    evento.aprobado3 = configuracion[0].aprobado3
                    evento.denominacionaprobado2 = configuracion[0].denominacionaprobado2
                    evento.denominacionaprobado3 = configuracion[0].denominacionaprobado3
                    evento.save(request)
                    if 'brochure' in request.FILES:
                        newfile = request.FILES['brochure']
                        if newfile:
                            newfile._name = generar_nombre("_", newfile._name)
                            evento.brochure = newfile
                            evento.save()
                    log(u'Edito Planificación de Evento en capacitacion IPEC: %s - [%s] ' % (evento, evento.id),
                        request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": (u"Error al guardar los datos. %s" % ex)})
        elif action == 'editperiodomes':
            try:
                id = request.POST['pk']
                mes = request.POST['mes']
                registro = CapEventoPeriodoIpec.objects.get(pk=id)
                registro.mes = mes
                registro.save(request)
                log(u'Modificó Mes : %s' % registro, request, "editperiodomes")
                return JsonResponse({"result": True, "pk": registro.id, "mes": mes})
            except Exception as ex:
                return JsonResponse({'result': False, "message": str(ex)})
        elif action == 'facturatotal':
            try:
                form = CapEventoPeriodoIpecFacturaTotalForm(request.POST, request.FILES)
                if form.is_valid():
                    evento = CapEventoPeriodoIpec.objects.get(pk=int(request.POST['id']))
                    if evento.capeventoperiodofacturatotalipec_set.filter(status=True).exists():
                        facturatotal = evento.capeventoperiodofacturatotalipec_set.filter(status=True)[0]
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if newfile:
                                newfile._name = generar_nombre("_", newfile._name)
                                facturatotal.archivo = newfile
                        facturatotal.subtotal = form.cleaned_data['subtotal']
                        facturatotal.iva = form.cleaned_data['iva']
                        facturatotal.total = form.cleaned_data['subtotal'] + form.cleaned_data['iva']
                        facturatotal.save(request)
                    else:
                        facturatotal = CapEventoPeriodoFacturaTotalIpec(capeventoperiodoipec=evento,
                                                                        subtotal=form.cleaned_data['subtotal'],
                                                                        iva=form.cleaned_data['iva'],
                                                                        total=form.cleaned_data['subtotal'] +
                                                                              form.cleaned_data['iva'])
                        facturatotal.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if newfile:
                                newfile._name = generar_nombre("_", newfile._name)
                                facturatotal.archivo = newfile
                            facturatotal.save(request)
                    log(u'Factura Total IPEC: %s - [%s] ' % (evento, facturatotal.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delperiodoevento':
            try:
                evento = CapEventoPeriodoIpec.objects.get(pk=int(request.POST['id']))
                if evento.puede_eliminar_planificacion_evento():
                    return JsonResponse({"result": "bad",
                                         "mensaje": u"No puede eliminar, porque tiene " + evento.puede_eliminar_planificacion_evento() + " activos"})
                log(u'Elimino Planificación de Evento en capacitacion IPEC: %s - [%s] ' % (evento, evento.id), request,
                    "del")
                evento.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'updatecupo':
            try:
                evento = CapEventoPeriodoIpec.objects.get(pk=int(request.POST['eid']))
                valor = int(request.POST['vc'])
                if valor > 999:
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"No puede establecer un cupo menor a" + str(999 + 1)})
                if valor < evento.contar_inscripcion_evento_periodo():
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"El cupo no puede ser menor a la cantidad de inscrito"})
                cupoanterior = evento.cupo
                evento.cupo = valor
                evento.save(request)
                log(u'Actualizo cupo a evento periodo capacitacion IPEC: %s cupo anterior: %s cupo actual: %s' % (
                    evento, str(cupoanterior), str(evento.cupo)), request, "add")
                return JsonResponse({'result': 'ok', 'valor': evento.cupo})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u"Error al eliminar los datos."})

        elif action == 'bloqueopublicacion':
            try:
                evento = CapEventoPeriodoIpec.objects.get(pk=request.POST['id'])
                evento.visualizar = True if request.POST['val'] == 'y' else False
                evento.save(request)
                log(u'Visualiza o no en capacitacion evento periodo IPEC : %s (%s)' % (evento, evento.visualizar),
                    request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        elif action == 'convalidar':
            try:
                evento = CapEventoPeriodoIpec.objects.get(pk=request.POST['id'])
                evento.convalidar = True if request.POST['val'] == 'y' else False
                evento.save(request)
                log(u'Convalida evento periodo IPEC : %s (%s)' % (evento, evento.convalidar),
                    request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        elif action == 'cargar_instructor':
            try:
                lista = []
                asistencia = 1
                promedio = 2
                if int(request.POST['idt']) == asistencia:
                    evento = CapEventoPeriodoIpec.objects.get(pk=request.POST['ide'])
                    instructores = evento.capinstructoripec_set.filter(status=True,
                                                                       capclaseipec__capcabeceraasistenciaipec__isnull=False).distinct().order_by(
                        'instructor__apellido1', 'instructor__apellido2', 'instructor__nombres')
                    for instructor in instructores:
                        lista.append([instructor.id, instructor.instructor.nombre_completo_inverso()])
                elif int(request.POST['idt']) == promedio:
                    evento = CapEventoPeriodoIpec.objects.get(pk=request.POST['ide'])
                    instructores = evento.capinstructoripec_set.filter(status=True,
                                                                       capnotaipec__isnull=False).distinct().order_by(
                        'instructor__apellido1', 'instructor__apellido2', 'instructor__nombres')
                    for instructor in instructores:
                        lista.append([instructor.id, instructor.instructor.nombre_completo_inverso()])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'resetear':
            try:
                instructor = CapInstructorIpec.objects.get(pk=request.POST['id'])
                # user = profesor.persona.usuario
                # if CLAVE_USUARIO_CEDULA:
                #     if profesor.persona.cedula:
                #         password = profesor.persona.cedula.strip()
                #     elif profesor.persona.pasaporte:
                #         password = profesor.persona.pasaporte.strip()
                #     else:
                #         profesor.password = profesor.persona.ruc.strip()
                #     user.set_password(password)
                # else:
                #     user.set_password(DEFAULT_PASSWORD)
                # user.save()
                # profesor.persona.cambiar_clave()
                if not instructor.instructor.emailinst:
                    return JsonResponse({"result": "bad", "mensaje": u"No tiene correo institucional."})
                resetear_clave(instructor.instructor)
                return JsonResponse({"result": "ok", "mensaje": u"Su contraseña nueva es: cedula*añodenacimiento."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # INCRITOS
        elif action == 'addinscribir':
            try:
                f = CapInscribirIpecForm(request.POST)
                if f.is_valid():
                    participante = Persona.objects.get(pk=request.POST['idestudiante'])

                    if CapInscritoIpec.objects.filter(participante=participante,
                                                      capeventoperiodo_id=int(request.POST['id'])).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra inscrito"})
                    if not CapEventoPeriodoIpec.objects.get(pk=int(request.POST['id'])).hay_cupo_inscribir():
                        return JsonResponse({"result": "bad", "mensaje": u"No hay cupo para continuar adicionando"})

                    inscribir = CapInscritoIpec(capeventoperiodo_id=int(request.POST['id']),
                                                participante=participante)
                    inscribir.save(request)

                    return JsonResponse(
                        {'result': 'ok', "mensaje": u"Estimado participante, se inscribió correctamente."})
                    # return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Llene todos los campos"})

        elif action == 'addinscribir_modal':
            try:
                f = CapInscribirIpecForm(request.POST)
                if f.is_valid():
                    participante = Persona.objects.get(pk=request.POST['idestudiante'])

                    if CapInscritoIpec.objects.filter(participante=participante,
                                                      capeventoperiodo_id=int(request.POST['id']),status=True).exists():
                        return JsonResponse({"result": False, "mensaje": u"Ya se encuentra inscrito"})

                    if not CapEventoPeriodoIpec.objects.get(pk=int(request.POST['id'])).hay_cupo_inscribir():
                        return JsonResponse({"result": False, "mensaje": u"No hay cupo para continuar adicionando"})


                    inscribir = CapInscritoIpec(capeventoperiodo_id=int(request.POST['id']),
                                                participante=participante)
                    inscribir.save(request)

                    return JsonResponse({"result": True, "mensaje": u"Se ha adicionado el participante"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Llene todos los campos"})


        elif action == 'generar_rubro':
            try:
                inscribir = CapInscritoIpec.objects.get(id=request.POST['id'])

                if not inscribir.capeventoperiodo.tiporubro and inscribir.capeventoperiodo.generarrubro:
                    return JsonResponse({'result': 'bad', "mensaje": u"No existe Rubro en curso."})
                tiprubroarancel = inscribir.capeventoperiodo.tiporubro

                personalunemi = False
                if inscribir.participante.distributivopersona_set.filter(estadopuesto_id=1, status=True).exists():
                    costo_total_curso = inscribir.capeventoperiodo.costo
                    personalunemi = True
                else:
                    if inscribir.participante.inscripcion_set.filter(status=True).exclude(coordinacion_id=9):
                        verificainsripcion = inscribir.participante.inscripcion_set.values_list('id').filter(
                            status=True).exclude(coordinacion_id=9)
                        if Matricula.objects.filter(inscripcion_id__in=verificainsripcion, status=True):
                            costo_total_curso = inscribir.capeventoperiodo.costo
                            personalunemi = True
                        else:
                            if RecordAcademico.objects.filter(inscripcion_id__in=verificainsripcion, status=True):
                                costo_total_curso = inscribir.capeventoperiodo.costo
                                personalunemi = True
                            else:
                                costo_total_curso = inscribir.capeventoperiodo.costoexterno
                    else:
                        costo_total_curso = inscribir.capeventoperiodo.costoexterno

                if inscribir.capeventoperiodo.generarrubro:
                    inscribir.personalunemi = personalunemi
                    inscribir.save()
                    if not Rubro.objects.filter(persona=inscribir.participante,capeventoperiodoipec=inscribir.capeventoperiodo,status=True).exists():
                        rubro = Rubro(tipo=tiprubroarancel,
                                      persona=inscribir.participante,
                                      relacionados=None,
                                      nombre=tiprubroarancel.nombre + ' - ' + inscribir.capeventoperiodo.capevento.nombre,
                                      cuota=1,
                                      fecha=datetime.now().date(),
                                      fechavence=inscribir.capeventoperiodo.fechamaxpago + timedelta(days=1),
                                      valor=costo_total_curso,
                                      iva_id=1,
                                      valortotal=costo_total_curso,
                                      capeventoperiodoipec=inscribir.capeventoperiodo,
                                      saldo=costo_total_curso,
                                      epunemi=True,
                                      cancelado=False)
                        rubro.save(request)
                        log(u'Adiciono un inscrito en Evento en Capacitacion IPEC: %s [%s]' % (
                        inscribir, inscribir.participante.id),
                            request, "add")
                        # Migración a EPUNEMI
                        resultado_migracion = migrar_crear_rubro_deunemi_aepunemi(request, [rubro], action='generar_rubro')
                        if resultado_migracion['result'] == 'ok':
                            res_json = {"error": False}
                            messages.success(request, "Se creó  el rubro y se migró exitosamente a EPUNEMI.")
                        else:
                            raise NameError(resultado_migracion['mensaje'])
                        # Migración a EPUNEMI
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'borrar_rubro':
            try:
                inscribir = CapInscritoIpec.objects.get(id=request.POST['id'])
                id_evento = inscribir.capeventoperiodo.id
                id_participante = inscribir.participante_id
                rubro = Rubro.objects.filter(status=True, capeventoperiodoipec_id=id_evento, persona_id=id_participante,cancelado=False)
                # for r in rubro:
                #     r.status = False
                #     r.save(request)
                #     log(u'Se elimino un rubro a inscrito : %s [%s]' % (inscribir, r),
                #         request, "del")
                # res_json = {"error": False}

                # Eliminar rubro unemi y migrar rubros a epunemi
                result_migrar = eliminar_y_migrar_rubro_deunemi_aepunemi(request, rubro, action='borrar_rubro')
                if result_migrar['result'] == "ok":
                    mensajemigrar = result_migrar['mensaje']
                    result_rubrosunemi = mensajemigrar['total_rubrosunemi']
                    result_rubrosepunemi = mensajemigrar['total_rubrosepunemi']
                    resultrubpagados_noeli = mensajemigrar['rubrospagados_noeliminados']
                    if result_rubrosunemi == 0 and result_rubrosepunemi == 0:
                        if resultrubpagados_noeli:
                            mensajeeliminados = f'No se eliminó ningún rubro. Por los siguientes motivos: {resultrubpagados_noeli}.'
                        else:
                            mensajeeliminados = f'No se eliminó ningún rubro.'
                    else:
                        if resultrubpagados_noeli:
                            mensajeeliminados = f"Se han eliminado {result_rubrosunemi} rubros y se han migrado (eliminado) {result_rubrosepunemi} rubros a EPUNEMI exitosamente. No se eliminaron o migraron: {resultrubpagados_noeli}."
                            # mensajeeliminados = f"Se han migrado (eliminado) {result_rubrosepunemi} rubros exitosamente a EPUNEMI."
                        else:
                            mensajeeliminados = f"Se han eliminado {result_rubrosunemi} rubros y se han migrado (eliminado) {result_rubrosepunemi} rubros a EPUNEMI exitosamente."
                    res_json = {"error": False, "message": mensajeeliminados}
                    messages.success(request, mensajeeliminados)
                    inscribir.formapago = 1
                    inscribir.save()
                else:
                    raise NameError(result_migrar['mensaje'])
                # Eliminar rubro unemi y migrar rubros a epunemi
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'delinscrito':
            try:
                inscribir = CapInscritoIpec.objects.get(pk=int(request.POST['id']))
                # if inscribir.capdetalleasistenciaipec_set.all().exists():
                #     return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, el inscrito ya cuenta con asistencia"})
                # inscribir.mail_notificar_talento_humano(request.session['nombresistema'])

                # inscribir.delete()
                # rubro = Rubro.objects.get(persona=inscribir.participante,capeventoperiodoipec=inscribir.capeventoperiodo,cancelado=False, status=True)
                if inscribir.capeventoperiodo.tiporubro:
                    if Rubro.objects.filter(persona=inscribir.participante,
                                            capeventoperiodoipec=inscribir.capeventoperiodo,
                                            cancelado=False, status=True).exists():
                        listarubros = Rubro.objects.filter(persona=inscribir.participante,
                                                           capeventoperiodoipec=inscribir.capeventoperiodo,
                                                           cancelado=False,
                                                           status=True)
                        for rubro in listarubros:
                            if not rubro.tiene_pagos():
                                rubro.status = False
                                rubro.save(request)

                                if rubro.epunemi and rubro.idrubroepunemi > 0:
                                    cursor = connections['epunemi'].cursor()
                                    sql = "UPDATE sagest_rubro SET status=false WHERE sagest_rubro.status=true and sagest_rubro.id=" + str(
                                        rubro.idrubroepunemi)
                                    cursor.execute(sql)
                                    cursor.close()
                                log(u'Elimino Rubro en Evento en Capacitacion IPEC : %s [%s]' % (
                                    inscribir, inscribir.capeventoperiodo), request, "del")
                                inscribir.status = False
                                inscribir.save()
                                log(u'Elimino Incrito en Evento en Capacitacion IPEC : %s [%s]' % (
                                inscribir, inscribir.id),
                                    request,
                                    "del")
                            else:
                                return JsonResponse({"result": "bad", "mensaje": u"El inscrito tiene pago."})

                    else:
                        inscribir.delete()
                else:
                    inscribir.delete()

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})
        # REPORTES
        elif action == 'reporte_asistencia':
            try:
                if request.POST['id']:
                    # if CapInstructorIpec.objects.filter(status=True, pk=request.POST['id']):
                    data['instructor'] = instructor = CapInstructorIpec.objects.get(status=True,
                                                                                    pk=int(request.POST['id']))
                # data['evento'] = evento = CapEventoIpec.objects.get(status=True, pk=int(request.POST['ieven']))
                data['evento'] = evento = CapEventoPeriodoIpec.objects.get(status=True, pk=int(request.POST['ieven']))
                # data['evento'] = evento = instructor.capeventoperiodo
                data['fechas'] = fechas = evento.todas_fechas_asistencia()
                lista_fechas = CapCabeceraAsistenciaIpec.objects.values_list("fecha").filter(
                    clase__capeventoperiodo=evento).distinct('fecha').order_by('fecha')
                contarcolumnas = CapCabeceraAsistenciaIpec.objects.filter(
                    Q(clase__capeventoperiodo=evento) & Q(fecha__in=lista_fechas)).count() + 6
                data['vertical_horizontal'] = True if contarcolumnas > 16 else False
                data['ubicacion_promedio'] = contarcolumnas - 4
                if fechas:
                    ultima_fecha = fechas.order_by('-fecha')[0].fecha
                    if ultima_fecha.weekday() >= 0 and ultima_fecha.weekday() <= 3 or ultima_fecha.weekday() == 6:
                        dias = timedelta(days=1)
                    else:
                        dias = timedelta(days=2)
                    data['fecha_corte'] = ultima_fecha + dias
                return conviert_html_to_pdf('adm_capacitacioneventoperiodoipec/informe_asistencia_pdf.html',
                                            {'pagesize': 'A4', 'data': data})
            except Exception as ex:
                pass

        elif action == 'reporte_promedio':
            try:
                campos_sinnotas = 5
                campos_ubicar_promedio = 3
                instructor = None
                if request.POST['id']:
                    data['instructor'] = instructor = CapInstructorIpec.objects.get(status=True,
                                                                                    pk=int(request.POST['id']))
                # data['evento'] = instructor.capeventoperiodo
                data['evento'] = evento = CapEventoPeriodoIpec.objects.get(status=True, pk=int(request.POST['ieven']))
                inscritos=evento.inscritos_id()
                pagado=Rubro.objects.filter(persona__in=inscritos,capeventoperiodoipec=evento, cancelado=True).values_list('persona__id').exclude(pago__factura__valida=False)
                data['rubro']= rubro = evento.capinscritoipec_set.filter(status=True, participante__id__in=pagado).order_by('participante__apellido1','participante__apellido2','participante__nombres') if evento.capinscritoipec_set.filter(status=True).exists() else []
                if request.POST['id']:
                    contarcolumnas = instructor.contar_unido_modelo_evaluativo_evaluativo_utilizado() + campos_sinnotas
                    data['vertical_horizontal'] = True if contarcolumnas > 10 else False
                    data['ubicacion_promedio'] = contarcolumnas - campos_ubicar_promedio
                    data['fecha_corte'] = datetime.now()
                    data['promediototal'] = instructor.extraer_promediocurso()
                data['instructor'] = instructor
                return conviert_html_to_pdf('adm_capacitacioneventoperiodoipec/informe_promedio_pdf.html',
                                            {'pagesize': 'A4', 'data': data})
            except Exception as ex:
                pass

        elif action == 'reporte_promedioexcel':
            try:
                campos_sinnotas = 5
                campos_ubicar_promedio = 3
                instructor = None
                if request.POST['id']:
                    instructor = CapInstructorIpec.objects.get(status=True, pk=int(request.POST['id']))
                evento = CapEventoPeriodoIpec.objects.get(status=True, pk=int(request.POST['ieven']))
                if request.POST['id']:
                    contarcolumnas = instructor.contar_unido_modelo_evaluativo_evaluativo_utilizado() + campos_sinnotas
                    vertical_horizontal = True if contarcolumnas > 10 else False
                    ubicacion_promedio = contarcolumnas - campos_ubicar_promedio
                    fecha_corte = datetime.now()
                    promediototal = instructor.extraer_promediocurso()
                instructor = instructor
                __author__ = 'Unemi'
                style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                title = easyxf(
                    'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                style1 = easyxf(num_format_str='D-MMM-YY')
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('exp_xls_post_part')
                ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                if instructor:
                    ws.write_merge(1, 1, 0, 6,
                                   instructor.instructor.apellido1 + ' ' + instructor.instructor.apellido2 + ' ' + instructor.instructor.nombres,
                                   font_style)
                ws.write_merge(2, 2, 0, 6, evento.capevento.nombre, font_style)
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=exp_xls_post_part_' + random.randint(1,
                                                                                                             10000).__str__() + '.xls'

                ws.col(0).width = 4000
                ws.col(1).width = 10000
                encabezado = 3
                ws.write(encabezado, 0, 'CEDULA', font_style)
                ws.write(encabezado, 1, 'APELLIDOS Y NOMBRE', font_style)
                contador = 0
                columna = 1
                if instructor:
                    for modelo in instructor.modelo_evaluativo_utilizado_sin_evaluacion():
                        contador = contador + 1
                        columna = columna + 1
                        ws.write(encabezado, columna, contador, font_style)
                    for modeloevaluacion in instructor.modelo_evaluativo_utilizado_evaluacion():
                        columna = columna + 1
                        ws.write(encabezado, columna, modeloevaluacion.nombre, font_style)
                ws.write(encabezado, columna + 1, 'NOTA FINAL', font_style)
                ws.write(encabezado, columna + 2, 'ESTADO', font_style)

                row_num = 4
                for alumno in evento.inscritos():
                    if alumno.participante.cedula:
                        campo1 = alumno.participante.cedula
                    else:
                        campo1 = alumno.participante.pasaporte
                    campo2 = alumno.participante.__str__()
                    campo6 = ''
                    campo7 = ''
                    if instructor:
                        campo6 = instructor.extaer_notatotal(alumno)
                    if instructor:
                        estado = instructor.notatotal_requerido(alumno)
                        campo7 = 'REPROBADO'
                        if estado:
                            campo7 = 'APROBADO'
                    ws.write(row_num, 0, campo1, font_style2)
                    ws.write(row_num, 1, campo2, font_style2)
                    row_column = 1
                    if instructor:
                        for modeloevaluacion in instructor.unido_modelo_evaluativo_evaluativo_utilizado():
                            row_column = row_column + 1
                            modelos_profesor = modeloevaluacion.extraer_capnotasipec(instructor)
                            if modelos_profesor:
                                for modelo_profesor in modelos_profesor:
                                    nota_inscrito = modelo_profesor.extraer_detallenotaipec(alumno)
                                    if nota_inscrito:
                                        ws.write(row_num, row_column, nota_inscrito.nota, font_style2)
                    ws.write(row_num, 5, campo6, font_style2)
                    ws.write(row_num, 6, campo7, font_style2)
                    row_num += 1
                wb.save(response)
                return response
            except Exception as ex:
                pass

        elif action == 'reporte_recaudado_mes':
            try:
                data = {}
                valormes = 0
                valoranterior = 0
                val = 0
                valan = 0
                meses = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
                data['nombremes'] = nombremes = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio',
                                                 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
                data['pagomes'] = pagomes = []
                data['pagoperanteior'] = pagoperanterior = []
                data['evento'] = evento = CapEventoPeriodoIpec.objects.get(pk=int(request.POST['id']))
                data['periodo'] = periodo = CapPeriodoIpec.objects.get(status=True, capeventoperiodoipec=evento)
                even = evento
                rubro = Rubro.objects.filter(status=True, capeventoperiodoipec=even)
                fecha_p = str(periodo.fechainicio)
                d_fecha = datetime.strptime(fecha_p, '%Y-%m-%d') - timedelta(days=365)
                for mes in meses:
                    for ru in rubro:
                        pago = Pago.objects.filter(status=True, rubro=ru, fecha__month=mes,
                                                   fecha__year=evento.fechainicio.year)
                        for p in pago:
                            valormes += p.valortotal
                        pagoante = Pago.objects.filter(status=True, rubro=ru, fecha__month=mes,
                                                       fecha__year=d_fecha.year)
                        for pg in pagoante:
                            valoranterior += pg.valortotal
                    pagomes.insert(mes, valormes)
                    pagoperanterior.insert(mes, valoranterior)
                    data['totalmes'] = val = val + valormes
                    data['totalmesanterior'] = valan = valan + valoranterior
                    valormes = 0
                    valoranterior = 0

                return conviert_html_to_pdf('adm_capacitacioneventoperiodoipec/reporte_recaudacion_mes.html',
                                            {'pagesize': 'A4', 'data': data})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte. %s" % ex})

        elif action == 'reporte_certificado':
            try:
                evento_ipec = CapInscritoIpec.objects.get(pk=int(request.POST['id'])).capeventoperiodo
                periodo_ipec = evento_ipec.periodo.fechainicio.year
                # if str(evento_ipec.fechainicio) >= '2021-09-20':
                import uuid
                # data["DOMINIO_DEL_SISTEMA"] = dominio_sistema = request.build_absolute_uri('/')[:-1].strip("/")
                persona_cargo_tercernivel = None
                cargo = None
                tamano = 0
                inscrito = CapInscritoIpec.objects.get(pk=int(request.POST['id']))
                data['evento'] = evento = inscrito.capeventoperiodo
                data['logoaval'] = inscrito.capeventoperiodo.archivo
                data['elabora_persona'] = persona
                firmacertificado = None
                # if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
                #     firmacertificado = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
                #                                                              tipopersonadepartamento_id=1,
                #                                                              departamentofirma_id=1)
                #
                # if PersonaDepartamentoFirmas.objects.filter(status=True, fechafin__gte=evento.fechafin,
                #                                             fechainicio__lte=evento.fechafin,
                #                                             tipopersonadepartamento_id=1,
                #                                             departamentofirma_id=1).exists():
                #     firmacertificado = PersonaDepartamentoFirmas.objects.get(status=True, fechafin__gte=evento.fechafin,
                #                                                              fechainicio__lte=evento.fechafin,
                #                                                              tipopersonadepartamento_id=1,
                #                                                              departamentofirma_id=1)
                if periodo_ipec >= 2022:
                    if PersonaDepartamentoFirmas.objects.filter(status=True, departamento=111).exists():
                        firmacertificado = PersonaDepartamentoFirmas.objects.filter(status=True, departamento=111).order_by('-id').first()

                    if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
                        firmaizquierda = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
                                                                               tipopersonadepartamento_id=8,
                                                                               departamentofirma_id=5)
                    if PersonaDepartamentoFirmas.objects.values('id').filter(status=True,
                                                                             fechafin__gte=evento.fechafin,
                                                                             fechainicio__lte=evento.fechafin,
                                                                             tipopersonadepartamento_id=8,
                                                                             departamentofirma_id=5).exists():
                        firmaizquierda = PersonaDepartamentoFirmas.objects.get(status=True,
                                                                               fechafin__gte=evento.fechafin,
                                                                               fechainicio__lte=evento.fechafin,
                                                                               tipopersonadepartamento_id=8,
                                                                               departamentofirma_id=5)
                else:
                    if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
                        firmacertificado = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
                                                                                 tipopersonadepartamento_id=1,
                                                                                 departamentofirma_id=1)
                    if PersonaDepartamentoFirmas.objects.filter(status=True, fechafin__gte=evento.fechafin,
                                                                fechainicio__lte=evento.fechafin,
                                                                tipopersonadepartamento_id=1,
                                                                departamentofirma_id=1).exists():
                        firmacertificado = PersonaDepartamentoFirmas.objects.get(status=True,
                                                                                 fechafin__gte=evento.fechafin,
                                                                                 fechainicio__lte=evento.fechafin,
                                                                                 tipopersonadepartamento_id=1,
                                                                                 departamentofirma_id=1)

                    if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
                        firmaizquierda = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
                                                                               tipopersonadepartamento_id=2,
                                                                               departamentofirma_id=1)
                    if PersonaDepartamentoFirmas.objects.values('id').filter(status=True,
                                                                             fechafin__gte=evento.fechafin,
                                                                             fechainicio__lte=evento.fechafin,
                                                                             tipopersonadepartamento_id=2,
                                                                             departamentofirma_id=1).exists():
                        firmaizquierda = PersonaDepartamentoFirmas.objects.get(status=True,
                                                                               fechafin__gte=evento.fechafin,
                                                                               fechainicio__lte=evento.fechafin,
                                                                               tipopersonadepartamento_id=2,
                                                                               departamentofirma_id=1)

                #
                # # firmacertificado = 'robles'
                # # fechacambio = (datetime(2019, 11, 1, 0, 0, 0)).date()
                # if evento.fechafin >= fechacambio and evento.fechafin.year < 2021:

                #     firmacertificado = 'firmaguillermo'
                # else:
                #     if evento.fechafin.year > 2020:
                #         firmacertificado = 'firmachacon'
                data['firmacertificado'] = firmacertificado
                data['firmaimg'] = FirmaPersona.objects.filter(status=True, persona = firmacertificado.personadepartamento, tipofirma=1).last()
                data['firmaizquierda'] = firmaizquierda
                data['firmaimgizq'] = FirmaPersona.objects.filter(status=True, persona=firmaizquierda.personadepartamento, tipofirma=1).last()
                if evento.envionotaemail:
                    data['nota'] = evento.instructor_principal().extaer_notatotal(inscrito.id)
                if DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,
                                                      status=True).exists():
                    cargo = DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,
                                                               status=True)[0]
                data['persona_cargo'] = cargo
                data['persona_cargo_titulo'] = titulo = persona.titulacion_principal_senescyt_registro()
                if not titulo == '':
                    persona_cargo_tercernivel = \
                        persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[
                            0] if titulo.titulo.nivel_id == 4 else None
                data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
                # Tercera firma
                data['firma_aprobado2'] = FirmaPersona.objects.filter(status=True, persona=evento.aprobado2, tipofirma=1).first().firma
                # Tercera firma
                data['inscrito'] = inscrito
                mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                       "octubre", "noviembre", "diciembre"]
                data['fecha'] = u"Milagro, %s de %s del %s" % (
                    datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)
                data['listado_contenido'] = listado = evento.contenido.split("\n") if evento.contenido else []
                if evento.objetivo.__len__() < 290:
                    if listado.__len__() < 21:
                        tamano = 120
                    elif listado.__len__() < 35:
                        tamano = 100
                    elif listado.__len__() < 41:
                        tamano = 70
                data['controlar_bajada_logo'] = tamano
                qrname = 'qr_certificado_' + str(inscrito.id)
                # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
                # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                if os.path.isfile(rutapdf):
                    os.remove(rutaimg)
                    os.remove(rutapdf)
                if periodo_ipec >= 2022:
                    # generar nombre html y url html
                    if not inscrito.namehtmlinsignia:
                        htmlname = "%s%s" % (uuid.uuid4().hex, '.html')
                    else:
                        htmlname = inscrito.namehtmlinsignia
                    urlname = "/media/qrcode/certificados/%s" % htmlname
                    rutahtml = SITE_STORAGE + urlname
                    if os.path.isfile(rutahtml):
                        os.remove(rutahtml)
                    # generar nombre html y url html
                    url = pyqrcode.create(f'{dominio_sistema}/media/qrcode/certificados/{htmlname}?v={data["version"]}')
                    data['urlhtmlinsignia'] = dominio_sistema + urlname
                else:
                    url = pyqrcode.create(f'{dominio_sistema}/media/qrcode/certificados/{qrname}.pdf?v={data["version"]}')
                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                data['qrname'] = 'qr' + qrname
                # Cambio al diseño propuesto en Educacion continua 07/10/22
                # if str(evento.fechainicio) >= "2022-05-01":
                #     valida = conviert_html_to_pdfsaveqrcertificado(
                #         'adm_capacitacioneventoperiodoipec/certificado_formatonuevo_pdf.html',
                #         {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                #     )
                # else:
                #     valida = conviert_html_to_pdfsaveqrcertificado(
                #         'adm_capacitacioneventoperiodoipec/certificado_pdf.html',
                #         {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                #     )
                # data['version'] = datetime.now().strftime('%Y%m%d_%H%M%S')
                # Cambio al diseño propuesto en Educacion continua 07/10/22

                # Restablecer diseño anterior Educacion continua 20/09/2021
                if periodo_ipec >= 2022:
                    if evento.configuraciondefirmas == True:
                        firmas = ConfigurarcionMejoraContinua.objects.filter(curso=evento).order_by('orden')
                        data['firmas'] = firmas
                        valida = conviert_html_to_pdfsavevistaprevia(
                            'adm_capacitacioneventoperiodoipec/certificadoconfiguraciondefirmas.html',
                            {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                        )
                    else:
                        valida = conviert_html_to_pdfsavevistaprevia(
                            'adm_capacitacioneventoperiodoipec/certificado_nuevodiseno_pdf.html',
                            {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                        )
                else:
                    # certificado_formatonuevo_pdf.html
                    valida = conviert_html_to_pdfsaveqrcertificado(
                        'adm_capacitacioneventoperiodoipec/certificado_pdf.html',
                        {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                    )
                data['version'] = datetime.now().strftime('%Y%m%d_%H%M%S')
                # Restablecer diseño anterior Educacion continua 20/09/2021
                if valida:
                    if periodo_ipec >= 2022:
                        # generar portada del certificado
                        # portada = convertir_certificadopdf_a_jpg(qrname, SITE_STORAGE, dominio_sistema, data)
                        pass
                    # os.remove(rutaimg)
                    inscrito.rutapdf = 'qrcode/certificados/' + qrname + '.pdf'
                    inscrito.emailnotificado = True
                    inscrito.fecha_emailnotifica = datetime.now().date()
                    inscrito.persona_emailnotifica = persona
                    inscrito.estado = 2
                    # inscrito.save(request)
                    data['rutapdf'] = '/media/{}'.format(inscrito.rutapdf)
                    if periodo_ipec >= 2022:
                        #fecha para licencia o certificacion linkedin
                        if evento.fechacertificado:
                            data['fechalinkedin'] = evento.fechacertificado
                        else:
                            data['fechalinkedin'] = evento.fechafin
                        data['idcertificado'] = htmlname[0:len(htmlname)-5]
                        #crear html de certificado valido en la media  y guardar url en base
                        a = render(request, "adm_capacitacioneventoperiodoipec/certificadovalido.html", {"data": data, 'institucion': 'UNIVERSIDAD ESTATAL DE MILAGRO', "remotenameaddr": 'sga.unemi.edu.ec'})
                        with open(SITE_STORAGE + urlname, "wb") as f:
                            f.write(a.content)
                        f.close()
                        inscrito.namehtmlinsignia = htmlname
                        inscrito.urlhtmlinsignia = urlname
                    inscrito.save(request)
                    # fin crear html en la media y guardar url en base

                    # Notificacion de certificado por correo
                    asunto = u"CERTIFICADO - " + inscrito.capeventoperiodo.capevento.nombre
                    correoinscrito = inscrito.participante.emailpersonal()
                    if IS_DEBUG:
                        correoinscrito = ['pruebasdesarrollo2023@gmail.com']
                    send_html_mail(asunto, "emails/notificar_certificado.html",
                               {'sistema': request.session['nombresistema'], 'inscrito': inscrito,
                                'director': firmacertificado},
                               correoinscrito,
                               [], [inscrito.rutapdf],
                               cuenta=CUENTAS_CORREOS[0][1])

                    #     if str(evento.fechainicio) >= "2022-01-01":
                    #         # Notificacion de certificado por SGA
                    #         notificacion('Insignia digital',
                    #                      'Tienes una Insignia digital del curso {} puedes compartirla en Linkedin, Twitter y/o Facebook. Para visualizarla clic en el link compartido aquí.'.format(evento.capevento, data['urlhtmlinsignia']),
                    #                      inscrito.participante,
                    #                      None,
                    #                      inscrito.rutapdf,
                    #                      inscrito.pk,
                    #                      1,
                    #                      'sga',
                    #                      CapInscritoIpec,
                    #                      request)
                    time.sleep(5)
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte."})
                # else:
                #     return JsonResponse({"result": "bad", "mensaje": u"Acción no permitida, el periodo del evento debe ser mayor a 2021."})
            except Exception as ex:
                messages.error(request, ex)
                return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte. %s" % ex})

        # elif action == 'pruebagenerarcertificado':
        #     try:
        #         import uuid
        #         data["DOMINIO_DEL_SISTEMA"] = dominio_sistema = request.build_absolute_uri('/')[:-1].strip("/")
        #         persona_cargo_tercernivel = None
        #         cargo = None
        #         tamano = 0
        #         inscrito = CapInscritoIpec.objects.get(pk=int(request.POST['id']))
        #         data['evento'] = evento = inscrito.capeventoperiodo
        #         data['logoaval'] = inscrito.capeventoperiodo.archivo
        #         data['elabora_persona'] = persona
        #         firmacertificado = None
        #         if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
        #             firmacertificado = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
        #                                                                      tipopersonadepartamento_id=1,
        #                                                                      departamentofirma_id=1)
        #
        #         if PersonaDepartamentoFirmas.objects.filter(status=True, fechafin__gte=evento.fechafin,
        #                                                     fechainicio__lte=evento.fechafin,
        #                                                     tipopersonadepartamento_id=1,
        #                                                     departamentofirma_id=1).exists():
        #             firmacertificado = PersonaDepartamentoFirmas.objects.get(status=True, fechafin__gte=evento.fechafin,
        #                                                                      fechainicio__lte=evento.fechafin,
        #                                                                      tipopersonadepartamento_id=1,
        #                                                                      departamentofirma_id=1)
        #         #
        #         if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
        #             firmaizquierda = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
        #                                                                      tipopersonadepartamento_id=2,
        #                                                                      departamentofirma_id=1)
        #         if PersonaDepartamentoFirmas.objects.values('id').filter(status=True, fechafin__gte=evento.fechafin,
        #                                                                      fechainicio__lte=evento.fechafin,
        #                                                                      tipopersonadepartamento_id=2,
        #                                                                      departamentofirma_id=1).exists():
        #             firmaizquierda = PersonaDepartamentoFirmas.objects.get(status=True, fechafin__gte=evento.fechafin,
        #                                                   fechainicio__lte=evento.fechafin,
        #                                                   tipopersonadepartamento_id=2,
        #                                                   departamentofirma_id=1)
        #         #
        #         # # firmacertificado = 'robles'
        #         # # fechacambio = (datetime(2019, 11, 1, 0, 0, 0)).date()
        #         # if evento.fechafin >= fechacambio and evento.fechafin.year < 2021:
        #
        #         #     firmacertificado = 'firmaguillermo'
        #         # else:
        #         #     if evento.fechafin.year > 2020:
        #         #         firmacertificado = 'firmachacon'
        #         data['firmacertificado'] = firmacertificado
        #         data['firmaimg'] = FirmaPersona.objects.filter(status=True, persona = firmacertificado.personadepartamento).last()
        #         data['firmaizquierda'] = firmaizquierda
        #         data['firmaimgizq'] = FirmaPersona.objects.filter(status=True, persona=firmaizquierda.personadepartamento).last()
        #         if evento.envionotaemail:
        #             data['nota'] = evento.instructor_principal().extaer_notatotal(inscrito.id)
        #         if DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,
        #                                               status=True).exists():
        #             cargo = DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,
        #                                                        status=True)[0]
        #         data['persona_cargo'] = cargo
        #         data['persona_cargo_titulo'] = titulo = persona.titulacion_principal_senescyt_registro()
        #         if not titulo == '':
        #             persona_cargo_tercernivel = \
        #                 persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[
        #                     0] if titulo.titulo.nivel_id == 4 else None
        #         data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
        #         data['inscrito'] = inscrito
        #         mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
        #                "octubre", "noviembre", "diciembre"]
        #         data['fecha'] = u"Milagro, %s de %s del %s" % (
        #             datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)
        #         data['listado_contenido'] = listado = evento.contenido.split("\n") if evento.contenido else []
        #         if evento.objetivo.__len__() < 290:
        #             if listado.__len__() < 21:
        #                 tamano = 120
        #             elif listado.__len__() < 35:
        #                 tamano = 100
        #             elif listado.__len__() < 41:
        #                 tamano = 70
        #         data['controlar_bajada_logo'] = tamano
        #         qrname = 'qr_certificado_' + str(inscrito.id)
        #         # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
        #         folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
        #         # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
        #         rutapdf = folder + qrname + '.pdf'
        #         rutaimg = folder + qrname + '.png'
        #         if os.path.isfile(rutapdf):
        #             os.remove(rutaimg)
        #             os.remove(rutapdf)
        #         # generar nombre html y url html
        #         if not inscrito.namehtmlinsignia:
        #             htmlname = "%s%s" % (uuid.uuid4().hex, '.html')
        #         else:
        #             htmlname = inscrito.namehtmlinsignia
        #         urlname = "/media/qrcode/certificados/%s" % htmlname
        #         rutahtml = SITE_STORAGE+urlname
        #         if os.path.isfile(rutahtml):
        #             os.remove(rutahtml)
        #         # generar nombre html y url html
        #         # url = pyqrcode.create('https://sga.unemi.edu.ec/media/qrcode/certificados/' + qrname + '.pdf')
        #         url = pyqrcode.create('https://sga.unemi.edu.ec/media/qrcode/certificados/' + htmlname)
        #         # url = pyqrcode.create(dominio_sistema+'/media/qrcode/certificados/' + htmlname)
        #         imageqr = url.png(folder + qrname + '.png', 16, '#000000')
        #         data['qrname'] = 'qr' + qrname
        #
        #         data['urlhtmlinsignia'] = dominio_sistema + urlname
        #         # Cambio al diseño propuesto en Educacion continua 07/10/22
        #         # if str(evento.fechainicio) >= "2022-05-01":
        #         #     valida = conviert_html_to_pdfsaveqrcertificado(
        #         #         'adm_capacitacioneventoperiodoipec/certificado_formatonuevo_pdf.html',
        #         #         {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
        #         #     )
        #         # else:
        #         #     valida = conviert_html_to_pdfsaveqrcertificado(
        #         #         'adm_capacitacioneventoperiodoipec/certificado_pdf.html',
        #         #         {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
        #         #     )
        #         valida = conviert_html_to_pdfsaveqrcertificado(
        #             'adm_capacitacioneventoperiodoipec/certificado_nuevodiseno_pdf.html',
        #             {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
        #         )
        #         if valida:
        #             # os.remove(rutaimg)
        #             inscrito.rutapdf = 'qrcode/certificados/' + qrname + '.pdf'
        #             inscrito.emailnotificado = True
        #             inscrito.fecha_emailnotifica = datetime.now().date()
        #             inscrito.persona_emailnotifica = persona
        #             # inscrito.save(request)
        #             data['rutapdf'] = '/media/{}'.format(inscrito.rutapdf)
        #             #fecha para licencia o certificacion linkedin
        #             if evento.fechacertificado:
        #                 data['fechalinkedin'] = evento.fechacertificado
        #             else:
        #                 data['fechalinkedin'] = evento.fechafin
        #             data['idcertificado'] = htmlname[0:len(htmlname)-5]
        #             #crear html de certificado valido en la media  y guardar url en base
        #             # a = requests.get(dominio_sistema+'/adm_silabo?action=pregrado&codigo=%s' % encrypt(inscrito.id), verify=False)
        #             a = render(request, "adm_capacitacioneventoperiodoipec/certificadovalido.html", {"data": data})
        #             with open(SITE_STORAGE + urlname, "wb") as f:
        #                 f.write(a.content)
        #             f.close()
        #             inscrito.namehtmlinsignia = htmlname
        #             inscrito.urlhtmlinsignia = urlname
        #             inscrito.save(request)
        #             # fin crear html en la media y guardar url en base
        #             # Notificacion
        #             # if str(evento.fechafin) >= "2022-10-01":
        #             #     # Notificacion de certificado por correo
        #             #     asunto = u"CERTIFICADO - " + inscrito.capeventoperiodo.capevento.nombre
        #             #     # useremail = Persona.objects.get(cedula='0927984807') # Terminator
        #             #     send_html_mail(asunto, "emails/notificar_certificado.html",
        #             #                    {'sistema': request.session['nombresistema'], 'inscrito': inscrito,
        #             #                     'director': firmacertificado},
        #             #                    inscrito.participante.emailpersonal(),
        #             #                    # useremail.emailpersonal(), # Terminator
        #             #                    [], [inscrito.rutapdf],
        #             #                    cuenta=CUENTAS_CORREOS[0][1])
        #             # else:
        #             #     # Notificacion de certificado por SGA
        #             #     notificacion('Insignia digital',
        #             #                  'Tienes una Insignia digital del curso {} puedes compartirla en Linkedin, Twitter y/o Facebook. Para visualizarla clic en el link compartido aquí.'.format(evento.capevento, data['urlhtmlinsignia']),
        #             #                  inscrito.participante,
        #             #                  None,
        #             #                  data['urlhtmlinsignia'],
        #             #                  inscrito.pk,
        #             #                  1,
        #             #                  'sga',
        #             #                  CapInscritoIpec,
        #             #                  request)
        #             return JsonResponse({"result": "ok"})
        #         else:
        #             return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte."})
        #     except Exception as ex:
        #         messages.error(request, ex)
        #         print(str(ex))
        #         return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte. %s" % ex})


        # elif action == 'reporte_certificadoprevio':
        #     try:
        #         persona_cargo_tercernivel = None
        #         cargo = None
        #         tamano = 0
        #         inscrito = CapInscritoIpec.objects.get(pk=int(request.POST['id']))
        #         data['evento'] = evento = inscrito.capeventoperiodo
        #         firmacertificado = None
        #         if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
        #             firmacertificado = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
        #                                                                      tipopersonadepartamento_id=1,
        #                                                                      departamentofirma_id=1)
        #
        #         if PersonaDepartamentoFirmas.objects.filter(status=True, fechafin__gte=evento.fechafin,
        #                                                     fechainicio__lte=evento.fechafin,
        #                                                     tipopersonadepartamento_id=1,
        #                                                     departamentofirma_id=1).exists():
        #             firmacertificado = PersonaDepartamentoFirmas.objects.get(status=True, fechafin__gte=evento.fechafin,
        #                                                                      fechainicio__lte=evento.fechafin,
        #                                                                      tipopersonadepartamento_id=1,
        #                                                                      departamentofirma_id=1)
        #         #
        #         # firmacertificado = 'robles'
        #         # fechacambio = (datetime(2019, 11, 1, 0, 0, 0)).date()
        #         # if evento.fechafin >= fechacambio and evento.fechafin.year < 2021:
        #         #     firmacertificado = 'firmaguillermo'
        #         # else:
        #         #     if evento.fechafin.year > 2020:
        #         #         firmacertificado = 'firmachacon'
        #
        #         if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
        #             firmaizquierda = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
        #                                                                    tipopersonadepartamento_id=2,
        #                                                                    departamentofirma_id=1)
        #         if PersonaDepartamentoFirmas.objects.values('id').filter(status=True, fechafin__gte=evento.fechafin,
        #                                                                  fechainicio__lte=evento.fechafin,
        #                                                                  tipopersonadepartamento_id=2,
        #                                                                  departamentofirma_id=1).exists():
        #             firmaizquierda = PersonaDepartamentoFirmas.objects.get(status=True, fechafin__gte=evento.fechafin,
        #                                                                    fechainicio__lte=evento.fechafin,
        #                                                                    tipopersonadepartamento_id=2,
        #                                                                    departamentofirma_id=1)
        #         data['firmacertificado'] = firmacertificado
        #         data['firmaimg'] = FirmaPersona.objects.filter(status=True, persona=firmacertificado.personadepartamento).last()
        #         data['firmaizquierda'] = firmaizquierda
        #         data['firmaimgizq'] = FirmaPersona.objects.filter(status=True, persona=firmaizquierda.personadepartamento).last()
        #         data['logoaval'] = inscrito.capeventoperiodo.archivo
        #         data['elabora_persona'] = persona
        #         if evento.envionotaemail:
        #             data['nota'] = evento.instructor_principal().extaer_notatotal(inscrito.id)
        #         if DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,
        #                                               status=True).exists():
        #             cargo = DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,
        #                                                        status=True)[0]
        #         data['persona_cargo'] = cargo
        #         data['persona_cargo_titulo'] = titulo = persona.titulacion_principal_senescyt_registro()
        #         if not titulo == '':
        #             persona_cargo_tercernivel = \
        #                 persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[
        #                     0] if titulo.titulo.nivel_id == 4 else None
        #         data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
        #         data['inscrito'] = inscrito
        #         mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
        #                "octubre", "noviembre", "diciembre"]
        #         data['fecha'] = u"Milagro, %s de %s del %s" % (
        #             datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)
        #         data['listado_contenido'] = listado = evento.contenido.split("\n") if evento.contenido else []
        #         if evento.objetivo.__len__() < 290:
        #             if listado.__len__() < 21:
        #                 tamano = 120
        #             elif listado.__len__() < 35:
        #                 tamano = 100
        #             elif listado.__len__() < 41:
        #                 tamano = 70
        #         data['controlar_bajada_logo'] = tamano
        #         qrname = 'qr_certificado_' + str(inscrito.id)
        #         # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
        #         folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
        #         # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
        #         rutapdf = folder + qrname + '.pdf'
        #         rutaimg = folder + qrname + '.png'
        #         if os.path.isfile(rutapdf):
        #             os.remove(rutaimg)
        #             os.remove(rutapdf)
        #         url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/certificados/' + qrname + '.pdf')
        #         # url = pyqrcode.create('http://127.0.0.1:8000//media/qrcode/certificados/' + qrname + '.pdf')
        #         imageqr = url.png(folder + qrname + '.png', 16, '#000000')
        #         data['qrname'] = 'qr' + qrname
        #         if str(evento.fechainicio) >= "2022-05-01":
        #             return conviert_html_to_pdfsaveqrcertificado(
        #                 'adm_capacitacioneventoperiodoipec/certificado_formatonuevo_pdf.html',
        #                 {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
        #             )
        #         else:
        #             return conviert_html_to_pdfsaveqrcertificado(
        #                 'adm_capacitacioneventoperiodoipec/certificado_pdf.html',
        #                 {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
        #             )
        #
        #     except Exception as ex:
        #         messages.error(request, ex)


        elif action == 'reporte_certificadoprevio':
            try:
                periodo_ipec = CapInscritoIpec.objects.get(pk=int(request.POST['id'])).capeventoperiodo.periodo.fechainicio.year
                if periodo_ipec >= 2022:
                    import uuid
                    # data["DOMINIO_DEL_SISTEMA"] = dominio_sistema = request.build_absolute_uri('/')[:-1].strip("/")
                    persona_cargo_tercernivel = None
                    cargo = None
                    tamano = 0
                    inscrito = CapInscritoIpec.objects.get(pk=int(request.POST['id']))
                    data['evento'] = evento = inscrito.capeventoperiodo
                    firmacertificado = None
                    # if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
                    #     firmacertificado = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
                    #                                                              tipopersonadepartamento_id=1,
                    #                                                              departamentofirma_id=1)
                    #
                    # if PersonaDepartamentoFirmas.objects.filter(status=True, fechafin__gte=evento.fechafin,
                    #                                             fechainicio__lte=evento.fechafin,
                    #                                             tipopersonadepartamento_id=1,
                    #                                             departamentofirma_id=1).exists():
                    #     firmacertificado = PersonaDepartamentoFirmas.objects.get(status=True, fechafin__gte=evento.fechafin,
                    #                                                              fechainicio__lte=evento.fechafin,
                    #                                                              tipopersonadepartamento_id=1,
                    #                                                              departamentofirma_id=1)
                    if PersonaDepartamentoFirmas.objects.filter(status=True, departamento=111).exists():
                        firmacertificado = PersonaDepartamentoFirmas.objects.filter(status=True, departamento=111).order_by(
                            '-id').first()
                    #
                    # firmacertificado = 'robles'
                    # fechacambio = (datetime(2019, 11, 1, 0, 0, 0)).date()
                    # if evento.fechafin >= fechacambio and evento.fechafin.year < 2021:
                    #     firmacertificado = 'firmaguillermo'
                    # else:
                    #     if evento.fechafin.year > 2020:
                    #         firmacertificado = 'firmachacon'

                    if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
                        firmaizquierda = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
                                                                               tipopersonadepartamento_id=8,
                                                                               departamentofirma_id=5)
                    if PersonaDepartamentoFirmas.objects.values('id').filter(status=True, fechafin__gte=evento.fechafin,
                                                                             fechainicio__lte=evento.fechafin,
                                                                             tipopersonadepartamento_id=8,
                                                                             departamentofirma_id=5).exists():
                        firmaizquierda = PersonaDepartamentoFirmas.objects.get(status=True, fechafin__gte=evento.fechafin,
                                                                               fechainicio__lte=evento.fechafin,
                                                                               tipopersonadepartamento_id=8,
                                                                               departamentofirma_id=5)
                    data['firmacertificado'] = firmacertificado
                    data['firmaimg'] = FirmaPersona.objects.filter(status=True, persona=firmacertificado.personadepartamento, tipofirma=1).last()
                    data['firmaizquierda'] = firmaizquierda
                    data['firmaimgizq'] = FirmaPersona.objects.filter(status=True, persona=firmaizquierda.personadepartamento, tipofirma=1).last()
                    data['logoaval'] = inscrito.capeventoperiodo.archivo
                    data['elabora_persona'] = persona
                    if evento.envionotaemail:
                        data['nota'] = evento.instructor_principal().extaer_notatotal(inscrito.id)
                    if DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,
                                                          status=True).exists():
                        cargo = DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,
                                                                   status=True)[0]
                    data['persona_cargo'] = cargo
                    data['persona_cargo_titulo'] = titulo = persona.titulacion_principal_senescyt_registro()
                    if not titulo == '':
                        persona_cargo_tercernivel = \
                            persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[
                                0] if titulo.titulo.nivel_id == 4 else None
                    data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
                    # Tercera firma
                    data['firma_aprobado2'] = FirmaPersona.objects.filter(status=True, persona=evento.aprobado2, tipofirma=1).first().firma
                    # Tercera firma
                    data['inscrito'] = inscrito
                    mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                           "octubre", "noviembre", "diciembre"]
                    data['fecha'] = u"Milagro, %s de %s del %s" % (
                        datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)
                    data['listado_contenido'] = listado = evento.contenido.split("\n") if evento.contenido else []
                    if evento.objetivo.__len__() < 290:
                        if listado.__len__() < 21:
                            tamano = 120
                        elif listado.__len__() < 35:
                            tamano = 100
                        elif listado.__len__() < 41:
                            tamano = 70
                    data['controlar_bajada_logo'] = tamano
                    qrname = 'qr_certificado_' + str(inscrito.id)
                    # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
                    # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                    rutapdf = folder + qrname + '.pdf'
                    rutaimg = folder + qrname + '.png'

                    if os.path.isfile(rutapdf):
                        os.remove(rutaimg)
                        os.remove(rutapdf)
                    # generar nombre html y url html
                    if not inscrito.namehtmlinsignia:
                        htmlname = "%s%s" % (uuid.uuid4().hex, '.html')
                    else:
                        htmlname = inscrito.namehtmlinsignia
                    urlname = "/media/qrcode/certificados/%s" % htmlname
                    rutahtml = SITE_STORAGE + urlname
                    if os.path.isfile(rutahtml):
                        os.remove(rutahtml)
                    # generar nombre html y url html
                    # url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/certificados/'+ htmlname)
                    url = pyqrcode.create(f'{dominio_sistema}/media/qrcode/certificados/{htmlname}?v={data["version"]}')
                    # url = pyqrcode.create('vistaprevia')
                    # url = pyqrcode.create('http://127.0.0.1:8000//media/qrcode/certificados/' + qrname + '.pdf')
                    imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                    data['qrname'] = 'qr' + qrname
                    data['urlhtmlinsignia'] = dominio_sistema + urlname
                    # data['version'] = datetime.now().strftime('%Y%m%d_%H%M%S')
                    if evento.configuraciondefirmas == True:
                        firmas = ConfigurarcionMejoraContinua.objects.filter(curso=evento).order_by('orden')
                        data['firmas'] = firmas
                        valida = conviert_html_to_pdfsavevistaprevia(
                            'adm_capacitacioneventoperiodoipec/certificadoconfiguraciondefirmas.html',
                            {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                        )
                    else:
                        valida = conviert_html_to_pdfsavevistaprevia(
                            'adm_capacitacioneventoperiodoipec/certificado_nuevodiseno_pdf.html',
                            {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                        )

                    if valida:
                        # generar portada del certificado
                        # portada = convertir_certificadopdf_a_jpg(qrname, SITE_STORAGE, dominio_sistema, data)

                        data['rutapdf'] = '/media/qrcode/certificados/{}.pdf'.format(qrname)
                        # fecha para licencia o certificacion linkedin
                        if evento.fechacertificado:
                            data['fechalinkedin'] = evento.fechacertificado
                        else:
                            data['fechalinkedin'] = evento.fechafin
                        data['idcertificado'] = htmlname[0:len(htmlname) - 5]
                        # crear html de certificado valido en la media  y guardar url en base
                        # a = requests.get(dominio_sistema+'/adm_silabo?action=pregrado&codigo=%s' % encrypt(inscrito.id), verify=False)
                        a = render(request, "adm_capacitacioneventoperiodoipec/certificadovalido.html", {"data": data, 'institucion': 'UNIVERSIDAD ESTATAL DE MILAGRO', "remotenameaddr": 'sga.unemi.edu.ec'})
                        with open(SITE_STORAGE + urlname, "wb") as f:
                            f.write(a.content)
                        f.close()
                        # fin crear html en la media y guardar url en base
                        time.sleep(5)
                    return valida
                else:
                    messages.warning(request, "Acción no permitida, el periodo del evento debe ser mayor a 2021.")
            except Exception as ex:
                print(str(ex))
                messages.error(request, ex)

        # CERTIFICADO_FACILITADOR
        elif action == 'reporte_certificado_facilitador':
            try:
                persona_cargo_tercernivel = None
                cargo = None
                tamano = 0
                instructor = CapInstructorIpec.objects.get(pk=int(request.POST['id']))
                data['evento'] = evento = instructor.capeventoperiodo
                data['logoaval'] = instructor.capeventoperiodo.archivo
                data['elabora_persona'] = persona
                firmacertificado = None
                if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
                    firmacertificado = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
                                                                             tipopersonadepartamento_id=1,
                                                                             departamentofirma_id=1)

                if PersonaDepartamentoFirmas.objects.filter(status=True, fechafin__gte=evento.fechafin,
                                                            fechainicio__lte=evento.fechainicio,
                                                            tipopersonadepartamento_id=1,
                                                            departamentofirma_id=1).exists():
                    firmacertificado = PersonaDepartamentoFirmas.objects.get(status=True, fechafin__gte=evento.fechafin,
                                                                             fechainicio__lte=evento.fechainicio,
                                                                             tipopersonadepartamento_id=1,
                                                                             departamentofirma_id=1)
                #
                data['firmacertificado'] = firmacertificado

                if DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,
                                                      status=True).exists():
                    cargo = DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,
                                                               status=True)[0]
                data['persona_cargo'] = cargo
                data['persona_cargo_titulo'] = titulo = persona.titulacion_principal_senescyt_registro()
                if not titulo == '':
                    persona_cargo_tercernivel = \
                        persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[
                            0] if titulo.titulo.nivel_id == 4 else None
                data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
                data['instructor'] = instructor
                mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                       "octubre", "noviembre", "diciembre"]
                data['fecha'] = u"Milagro, %s de %s del %s" % (
                    datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)
                data['listado_contenido'] = listado = evento.contenido.split("\n") if evento.contenido else []
                if evento.objetivo.__len__() < 290:
                    if listado.__len__() < 21:
                        tamano = 120
                    elif listado.__len__() < 35:
                        tamano = 100
                    elif listado.__len__() < 41:
                        tamano = 70
                data['controlar_bajada_logo'] = tamano
                qrname = 'qr_certificado_' + str(instructor.id)
                # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados_facilitadores', 'qr'))
                # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                if os.path.isfile(rutapdf):
                    os.remove(rutaimg)
                    os.remove(rutapdf)
                url = pyqrcode.create(
                    'http://sga.unemi.edu.ec//media/qrcode/certificados_facilitadores/' + qrname + '.pdf')
                # url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/certificados_facilitadores/' + qrname + '.pdf')
                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                data['qrname'] = 'qr' + qrname
                valida = conviert_html_to_pdfsaveqrcertificadoinstructor2(
                    'adm_capacitacioneventoperiodoipec/certificado_facilitador_pdf.html',
                    {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                )
                if valida:
                    os.remove(rutaimg)
                    instructor.rutapdf = 'qrcode/certificados_facilitadores/' + qrname + '.pdf'
                    instructor.emailnotificado = True
                    instructor.fecha_emailnotifica = datetime.now().date()
                    instructor.persona_emailnotifica = persona
                    instructor.save(request)
                    asunto = u"CERTIFICADO - " + instructor.capeventoperiodo.capevento.nombre
                    # useremail = Persona.objects.get(cedula='0923363030')
                    send_html_mail(asunto, "emails/notificar_certificado_facilitador.html",
                                   {'sistema': request.session['nombresistema'], 'instructor': instructor,
                                    't': miinstitucion()},
                                   instructor.instructor.emailpersonal(), [], [instructor.rutapdf],
                                   # useremail.emailpersonal(), [], [inscrito.rutapdf],
                                   cuenta=CUENTAS_CORREOS[0][1])
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte."})

            except Exception as ex:
                pass

        elif action == 'reporte_certificadopreviofacilitador':
            try:
                persona_cargo_tercernivel = None
                cargo = None
                tamano = 0
                instructor = CapInstructorIpec.objects.get(pk=int(request.POST['id']))
                data['evento'] = evento = instructor.capeventoperiodo
                firmacertificado = None
                if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
                    firmacertificado = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
                                                                             tipopersonadepartamento_id=1,
                                                                             departamentofirma_id=1)

                if PersonaDepartamentoFirmas.objects.filter(status=True, fechafin__gte=evento.fechafin,
                                                            fechainicio__lte=evento.fechainicio,
                                                            tipopersonadepartamento_id=1,
                                                            departamentofirma_id=1).exists():
                    firmacertificado = PersonaDepartamentoFirmas.objects.get(status=True, fechafin__gte=evento.fechafin,
                                                                             fechainicio__lte=evento.fechainicio,
                                                                             tipopersonadepartamento_id=1,
                                                                             departamentofirma_id=1)

                data['firmacertificado'] = firmacertificado
                data['logoaval'] = instructor.capeventoperiodo.archivo
                data['elabora_persona'] = persona

                if DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,
                                                      status=True).exists():
                    cargo = DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,
                                                               status=True)[0]
                data['persona_cargo'] = cargo
                data['persona_cargo_titulo'] = titulo = persona.titulacion_principal_senescyt_registro()
                if not titulo == '':
                    persona_cargo_tercernivel = \
                        persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[
                            0] if titulo.titulo.nivel_id == 4 else None
                data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
                data['instructor'] = instructor
                mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                       "octubre", "noviembre", "diciembre"]
                data['fecha'] = u"Milagro, %s de %s del %s" % (
                    datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)
                data['listado_contenido'] = listado = evento.contenido.split("\n") if evento.contenido else []
                if evento.objetivo.__len__() < 290:
                    if listado.__len__() < 21:
                        tamano = 120
                    elif listado.__len__() < 35:
                        tamano = 100
                    elif listado.__len__() < 41:
                        tamano = 70
                data['controlar_bajada_logo'] = tamano
                qrname = 'qr_certificado_' + str(instructor.id)
                # folder = SITE_STORAGE + 'media/qrcode/certificados_facilitadores/'
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados_facilitadores', 'qr'))
                # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados_facilitadores')
                rutapdf = folder + qrname + '.pdf'
                rutaimg = folder + qrname + '.png'
                if os.path.isfile(rutapdf):
                    os.remove(rutaimg)
                    os.remove(rutapdf)

                url = pyqrcode.create(
                    'http://sga.unemi.edu.ec//media/qrcode/certificados_facilitadores/' + qrname + '.pdf')
                # url = pyqrcode.create('http://127.0.0.1:8000//media/qrcode/certificados_facilitadores/' + qrname + '.pdf')
                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                data['qrname'] = 'qr' + qrname
                return conviert_html_to_pdfsaveqrcertificadoinstructor(
                    'adm_capacitacioneventoperiodoipec/certificado_facilitador_pdf.html',
                    {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                )

            except Exception as ex:
                pass

        # INSTRUCTOR
        elif action == 'addinstructor':
            try:
                form = CapInstructorIpecForm(request.POST)
                if form.is_valid():
                    if CapInstructorIpec.objects.filter(instructor=form.cleaned_data['instructor'],
                                                        capeventoperiodo_id=int(request.POST['eventoperiodo']),
                                                        status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                    instructor = CapInstructorIpec(capeventoperiodo_id=int(request.POST['eventoperiodo']),
                                                   instructor_id=form.cleaned_data['instructor'],
                                                   instructorprincipal=form.cleaned_data['instructorprincipal'],
                                                   nombrecurso = form.cleaned_data['nombrecurso'])
                    instructor.save(request)
                    if not CapInstructorIpec.objects.filter(instructor=instructor.instructor, activo=True).exists():
                        if instructor.instructorprincipal:
                            instructor.activo = True
                    instructor.save(request)

                    if not instructor.tiene_perfilusuario():
                        if not instructor.instructor.usuario:
                            persona = Persona.objects.get(pk=instructor.instructor.id)
                            username = calculate_username(persona)
                            generar_usuario(persona, username, variable_valor('INSTRUCTOR_GROUP_ID'))
                            if EMAIL_INSTITUCIONAL_AUTOMATICO:
                                persona.emailinst = username + '@' + EMAIL_DOMAIN
                            persona.save(request)
                        instructor.crear_eliminar_perfil_instructor(True)

                    log(u'Adiciono Instructor en Capacitacion IPEC: %s - [%s]' % (instructor, instructor.id), request,
                        "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editinstructor':
            try:
                form = CapInstructorIpecForm(request.POST)
                if form.is_valid():
                    instructor = CapInstructorIpec.objects.get(pk=int(request.POST['id']))
                    if CapInstructorIpec.objects.filter(instructor_id=int(form.cleaned_data['instructor']),
                                                        capeventoperiodo=instructor.capeventoperiodo,
                                                        status=True).exclude(pk=instructor.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                    instructor.instructor = Persona.objects.get(pk=form.cleaned_data['instructor'])
                    instructor.instructorprincipal = form.cleaned_data['instructorprincipal']
                    instructor.nombrecurso = form.cleaned_data['nombrecurso']
                    if not CapInstructorIpec.objects.filter(instructor_id=form.cleaned_data['instructor'],
                                                            activo=True).exists():
                        if instructor.instructorprincipal:
                            instructor.activo = True
                    instructor.save(request)
                    # if not instructor.tiene_perfilusuario():
                    #     instructor.crear_eliminar_perfil_instructor(True)
                    log(u'Editar Instructor Capacitación IPEC: %s - [%s]' % (instructor, instructor.id), request,
                        "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delinstructor':
            try:
                enfo = CapInstructorIpec.objects.get(pk=int(request.POST['id']))
                log(u'Elimino Instructor Capacitación IPEC : %s' % enfo, request, "del")
                enfo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})
        # HORARIOS
        elif action == 'addclase':
            try:
                form = CapClaseIpecForm(request.POST)
                if form.is_valid():
                    periodo = CapEventoPeriodoIpec.objects.get(id=int(request.POST['cepid']))
                    if CapClaseIpec.objects.filter(capeventoperiodo_id=int(request.POST['cepid']),
                                                   dia=form.cleaned_data['dia'], turno=form.cleaned_data['turno'],
                                                   fechainicio=form.cleaned_data['fechainicio'],
                                                   fechafin=form.cleaned_data['fechafin'], status=True).exists():
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Hay una Clase que existe con las misma fechas y turno."})
                    if not form.cleaned_data['fechainicio'] >= periodo.fechainicio or not form.cleaned_data[
                                                                                              'fechafin'] <= periodo.fechafin:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Las fecha no puede ser mayor a las fecha del evento."})
                    if not form.cleaned_data['fechainicio'] <= form.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ser mayor la fecha de inicio."})
                    if form.cleaned_data['fechainicio'] == form.cleaned_data['fechafin']:
                        if not int(form.cleaned_data['dia']) == form.cleaned_data['fechainicio'].weekday() + 1:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha no concuerdan con el dia."})
                    clase = CapClaseIpec(capeventoperiodo_id=int(request.POST['cepid']),
                                         turno=form.cleaned_data['turno'],
                                         dia=form.cleaned_data['dia'],
                                         fechainicio=form.cleaned_data['fechainicio'],
                                         fechafin=form.cleaned_data['fechafin'],
                                         instructor=form.cleaned_data['instructor'])
                    clase.save(request)
                    log(u'Adiciono horario en Evento en capacitacion IPEC: %s [%s]' % (clase, clase.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editclase':
            try:
                form = CapClaseIpecForm(request.POST)
                if form.is_valid():
                    clase = CapClaseIpec.objects.get(pk=int(request.POST['claseid']))
                    if CapClaseIpec.objects.filter(capeventoperiodo=clase.capeventoperiodo, dia=clase.dia,
                                                   turno=clase.turno, fechainicio=form.cleaned_data['fechainicio'],
                                                   fechafin=form.cleaned_data['fechafin'], status=True).exclude(
                        pk=clase.id).exists():
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Hay una Clase que existe con las misma fechas y turno."})
                    if not form.cleaned_data['fechainicio'] >= clase.capeventoperiodo.fechainicio or not \
                            form.cleaned_data['fechafin'] <= clase.capeventoperiodo.fechafin:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Las fecha no puede ser mayor a las fecha del evento."})
                    if not form.cleaned_data['fechainicio'] <= form.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"No puede ser mayor la fecha de inicio."})
                    if form.cleaned_data['fechainicio'] == form.cleaned_data['fechafin']:
                        if not clase.dia == form.cleaned_data['fechainicio'].weekday() + 1:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha no concuerdan con el dia."})
                    clase.fechainicio = form.cleaned_data['fechainicio']
                    clase.fechafin = form.cleaned_data['fechafin']
                    if not clase.capcabeceraasistenciaipec_set.filter(status=True).exists():
                        clase.instructor = form.cleaned_data['instructor']
                    clase.save(request)
                    log(u'Edito horario en Evento en capacitacion IPEC: %s [%s]' % (clase, clase.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delclase':
            try:
                clase = CapClaseIpec.objects.get(pk=int(request.POST['id']))
                if clase.capcabeceraasistenciaipec_set.filter(status=True).exists():
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"No se puede eliminar, porque tiene asistencias registradas."})
                log(u'Elimino horario en Evento en capacitacion IPEC: %s [%s]' % (clase, clase.id), request, "del")
                clase.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'extraerprofesor':
            try:
                clase = CapClaseIpec.objects.get(pk=int(request.POST['id']))
                return JsonResponse({"result": "ok", "profesor": clase.instructor.instructor.nombre_completo_inverso()})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})
        # ASISTENCIAS
        elif action == 'asistencia':
            try:
                fecha = None
                asis = CapCabeceraAsistenciaIpec.objects.filter(
                    fecha=datetime.now().date() if not 'fecha' in request.POST else datetime.strptime(
                        request.POST["fecha"], '%d-%m-%Y'), clase_id=int(request.POST["idc"]), status=True)
                if not CapClaseIpec.objects.get(pk=int(request.POST['idc'])).capeventoperiodo.exiten_inscritos():
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"No puede continuar, porque no existen inscritos."})
                if 'fecha' in request.POST:
                    fecha = datetime.strptime(request.POST["fecha"], '%d-%m-%Y')
                    if asis.exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe asistencia en esa fecha y clase."})
                    if not CapClaseIpec.objects.filter(Q(pk=int(request.POST['idc'])),
                                                       (Q(fechainicio__lte=fecha) & Q(fechafin__gte=fecha)),
                                                       status=True, dia=fecha.weekday() + 1).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"No esta en rango de fecha o en dia."})
                if not asis.exists():
                    clase = CapClaseIpec.objects.get(pk=int(request.POST['idc']))
                    asistencia = CapCabeceraAsistenciaIpec(clase_id=int(request.POST['idc']),
                                                           fecha=fecha.date() if 'fecha' in request.POST else datetime.now().date(),
                                                           horaentrada=clase.turno.horainicio,
                                                           horasalida=clase.turno.horafin,
                                                           contenido="SIN CONTENIDO",
                                                           observaciones="SIN OBSERVACIONES")
                    asistencia.save(request)
                    log(u'Agrego Asistencia en Capacitacion IPEC: %s [%s]' % (asistencia, asistencia.id), request,
                        "add")
                    for integrante in clase.capeventoperiodo.inscritos():
                        resultadovalores = CapDetalleAsistenciaIpec(inscrito=integrante, cabeceraasistencia=asistencia,
                                                                    asistio=False)
                        resultadovalores.save(request)
                else:
                    asistencia = asis[0]
                return JsonResponse({"result": "ok", 'id': asistencia.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addasistenciagrupal':
            try:
                cadenaselect = request.POST['cadenaselect']
                cadenanoselect = request.POST['cadenanoselect']
                cadenadatos = cadenaselect.split(',')
                cadenanodatos = cadenanoselect.split(',')
                asistencia = CapCabeceraAsistenciaIpec.objects.get(pk=int(request.POST["id"]))
                for cadena in cadenadatos:
                    if cadena:
                        if asistencia.capdetalleasistenciaipec_set.filter(inscrito_id=cadena, status=True).exists():
                            resultadovalores = asistencia.capdetalleasistenciaipec_set.get(inscrito_id=cadena,
                                                                                           status=True)
                            resultadovalores.asistio = True
                            resultadovalores.save(request)
                        else:
                            resultadovalores = CapDetalleAsistenciaIpec(inscrito_id=cadena,
                                                                        cabeceraasistencia=asistencia, asistio=True)
                            resultadovalores.save(request)
                for cadenano in cadenanodatos:
                    if cadenano:
                        if asistencia.capdetalleasistenciaipec_set.filter(inscrito_id=cadenano, status=True).exists():
                            resultadovalores = asistencia.capdetalleasistenciaipec_set.get(inscrito_id=cadenano,
                                                                                           status=True)
                            resultadovalores.asistio = False
                            resultadovalores.save(request)
                        else:
                            resultadovalores = CapDetalleAsistenciaIpec(inscrito_id=cadenano,
                                                                        cabeceraasistencia=asistencia, asistio=False)
                            resultadovalores.save(request)
                log(u'Edito Asistencia en Capacitacion IPEC: %s [%s]' % (asistencia, asistencia.id), request, "edit")
                data = {"result": "ok", "results": [
                    {"id": x.inscrito.id, "porcientoasist": x.inscrito.porciento_asistencia_ipec(),
                     "porcientorequerido": x.inscrito.porciento_requerido_asistencia_ipec()} for x in
                    asistencia.capdetalleasistenciaipec_set.filter(status=True)]}
                return JsonResponse(data)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addasistenciaindividual':
            try:
                asistencia = CapCabeceraAsistenciaIpec.objects.get(pk=int(request.POST["id"]))
                if asistencia.capdetalleasistenciaipec_set.filter(inscrito_id=int(request.POST['idi']),
                                                                  status=True).exists():
                    resultadovalores = asistencia.capdetalleasistenciaipec_set.get(inscrito_id=int(request.POST['idi']),
                                                                                   status=True)
                    resultadovalores.asistio = True if request.POST['valor'] == "y" else False
                    resultadovalores.save(request)
                else:
                    resultadovalores = CapDetalleAsistenciaIpec(inscrito_id=int(request.POST['idi']),
                                                                cabeceraasistencia=asistencia,
                                                                asistio=True if request.POST['valor'] == "y" else False)
                    resultadovalores.save(request)
                datos = {}
                datos['id'] = resultadovalores.inscrito.id
                datos['porcientoasist'] = resultadovalores.inscrito.porciento_asistencia_ipec()
                datos['porcientorequerido'] = resultadovalores.inscrito.porciento_requerido_asistencia_ipec()
                datos['result'] = 'ok'
                log(u'Edito Asistencia de Evento en Capacitacion IPEC: %s [%s]' % (asistencia, asistencia.id), request,
                    "edit")
                return JsonResponse(datos)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addasistenciacontenido':
            try:
                asistencia = CapCabeceraAsistenciaIpec.objects.get(pk=int(request.POST["id"]))
                asistencia.contenido = request.POST["valor"]
                asistencia.save(request)
                log(u'Edito Contenido de Asistencia de Evento en Capacitacion IPEC: %s [%s]' % (
                    asistencia, asistencia.id), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addasistenciaobservacion':
            try:
                asistencia = CapCabeceraAsistenciaIpec.objects.get(pk=int(request.POST["id"]))
                asistencia.observaciones = request.POST["valor"]
                asistencia.save(request)
                log(u'Edito Observacion de Asistencia de Evento en Capacitacion IPEC: %s [%s]' % (
                    asistencia, asistencia.id), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # PERSONA
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
                form = CapInscribirPersonaIpecForm(request.POST)
                if form.is_valid():
                    if Persona.objects.filter(cedula=request.POST["cedula"]).exists():
                        return JsonResponse({"result": "no", "mensaje": u"Existe un usuario con la cédula digitada."})
                    persona = Persona(nombres=form.cleaned_data['nombres'],
                                      apellido1=form.cleaned_data['apellido1'],
                                      apellido2=form.cleaned_data['apellido2'],
                                      cedula=form.cleaned_data['cedula'],
                                      nacimiento=form.cleaned_data['nacimiento'],
                                      sexo=form.cleaned_data['sexo'],
                                      telefono=form.cleaned_data['telefono'],
                                      telefono_conv=form.cleaned_data['telefono_conv'],
                                      email=form.cleaned_data['email'],
                                      direccion=form.cleaned_data['direccion'],
                                      tipopersona=1)
                    persona.save(request)
                    if int(request.POST['tipo']) == 1:
                        capeven = CapEventoPeriodoIpec.objects.get(id=int(request.POST['id']))
                        instructor = CapInstructorIpec(capeventoperiodo_id=capeven.id, instructor=persona)
                        instructor.save(request)
                        log(u'Adicionó nuevo instructor %s para la Capacitacion IPEC: %s' % (instructor, capeven),
                            request, "add")
                    else:
                        registrodatos = CapRegistrarDatosInscritoIpec(persona=persona,
                                                                      lugarestudio=form.cleaned_data['lugarestudio'],
                                                                      carrera=form.cleaned_data['carrera'],
                                                                      profesion=form.cleaned_data['profesion'],
                                                                      institucionlabora=form.cleaned_data[
                                                                          'institucionlabora'],
                                                                      cargodesempena=form.cleaned_data[
                                                                          'cargodesempena'],
                                                                      esparticular=form.cleaned_data['esparticular'])
                        registrodatos.save(request)
                        log(
                            u'Adiciono Persona desde en Capacitacion IPEC: persona: %s [%s] - Registrodatosipec: %s [%s]' % (
                                persona, persona.id, registrodatos, registrodatos.id), request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        # MODELO EVALUABLE
        elif action == 'addmodelo':
            try:
                form = CapModeloEvaluativoTareaIpecForm(request.POST)
                if form.is_valid():
                    if not form.cleaned_data['notaminima'] < form.cleaned_data['notamaxima']:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"La nota minima y maxima esta mal ingresados."})
                    if CapModeloEvaluativoTareaIpec.objects.filter(nombre=form.cleaned_data['nombre'],
                                                                   status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El nombre ya existe."})
                    modelo = CapModeloEvaluativoTareaIpec(nombre=form.cleaned_data['nombre'],
                                                          notaminima=form.cleaned_data['notaminima'],
                                                          notamaxima=form.cleaned_data['notamaxima'],
                                                          principal=form.cleaned_data['principal'],
                                                          evaluacion=form.cleaned_data['evaluacion'])
                    modelo.save(request)
                    log(u'Agrego Detalle Modelo Evaluativo de Capacitación IPEC: %s - [%s]' % (modelo, modelo.id),
                        request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editmodelo':
            try:
                form = CapModeloEvaluativoTareaIpecForm(request.POST, request.FILES)
                if form.is_valid():
                    modelo = CapModeloEvaluativoTareaIpec.objects.get(pk=int(request.POST['id']))
                    if not form.cleaned_data['notaminima'] < form.cleaned_data['notamaxima']:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"La nota minima y maxima esta mal ingresados."})
                    modelo.nombre = form.cleaned_data['nombre']
                    modelo.notaminima = form.cleaned_data['notaminima']
                    modelo.notamaxima = form.cleaned_data['notamaxima']
                    modelo.principal = form.cleaned_data['principal']
                    modelo.evaluacion = form.cleaned_data['evaluacion']
                    modelo.save(request)
                    log(u'Edito Detalle Modelo Evaluativo de Capacitación IPEC: %s - [%s]' % (modelo, modelo.id),
                        request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delmodelo':
            try:
                modelo = CapModeloEvaluativoTareaIpec.objects.get(pk=int(request.POST['id']))
                if modelo.capnotaipec_set.filter(status=True).exists():
                    return JsonResponse({"result": "bad",
                                         "mensaje": u"No puede Eliminar el Modelo Evaluativo, esta utilizado en notas.."})
                log(u'Elimino Modelo Evaluativo de Capacitación IPEC: %s - [%s]' % (modelo, modelo.id), request, "del")
                modelo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delmodelogeneral':
            try:
                modelo = CapModeloEvaluativoGeneral.objects.get(pk=int(request.POST['id']))
                log(u'Elimino Modelo Evaluativo de Capacitación IPEC: %s - [%s]' % (modelo, modelo.id), request, "del")
                modelo.status = False
                modelo.save()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'editpersona':
            try:
                form = CapInscribirPersonaIpecForm(request.POST)
                if form.is_valid():
                    persona = Persona.objects.get(pk=int(request.POST['id']))
                    if Persona.objects.filter(cedula=form.cleaned_data['cedula']).exclude(pk=persona.id).exists():
                        return JsonResponse({"result": "no", "mensaje": u"Existe un usuario con la cédula digitada."})
                    persona.nombres = form.cleaned_data['nombres']
                    persona.apellido1 = form.cleaned_data['apellido1']
                    persona.apellido2 = form.cleaned_data['apellido2']
                    persona.cedula = form.cleaned_data['cedula']
                    persona.nacimiento = form.cleaned_data['nacimiento']
                    persona.sexo = form.cleaned_data['sexo']
                    persona.telefono = form.cleaned_data['telefono']
                    persona.telefono_conv = form.cleaned_data['telefono_conv']
                    persona.email = form.cleaned_data['email']
                    persona.direccion = form.cleaned_data['direccion']
                    persona.tipopersona = 1
                    persona.save(request)
                    if int(request.POST['tipo']) == 1:
                        log(u'Editó instructor %s IPEC' % persona, request, "add")
                    else:
                        if CapRegistrarDatosInscritoIpec.objects.filter(persona=persona, status=True):
                            inscrito = CapRegistrarDatosInscritoIpec.objects.filter(persona=persona)[0]
                            inscrito.lugarestudio = form.cleaned_data['lugarestudio']
                            inscrito.carrera = form.cleaned_data['carrera']
                            inscrito.profesion = form.cleaned_data['profesion']
                            inscrito.institucionlabora = form.cleaned_data['institucionlabora']
                            inscrito.cargodesempena = form.cleaned_data['cargodesempena']
                            inscrito.esparticular = form.cleaned_data['esparticular']
                            inscrito.save(request)
                            log(u'Editó Inscripción %s IPEC' % persona, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cambiarinstructorprincipal':
            if 'id' in request.POST:
                instructor = CapInstructorIpec.objects.get(pk=int(request.POST['id']))
                if instructor.instructorprincipal:
                    instructor.instructorprincipal = False
                else:
                    instructor.instructorprincipal = True
                # if CapInstructorIpec.objects.filter(capeventoperiodo=instructor.capeventoperiodo, status=True,
                #                                     instructorprincipal=True).exclude(
                #         pk=int(request.POST['id'])).exists():
                #     CapInstructorIpec.objects.filter(capeventoperiodo=instructor.capeventoperiodo, status=True).exclude(
                #         pk=int(request.POST['id'])).update(instructorprincipal=False)
                instructor.save(request)
                log(u'Canbio el instructor principal %s IPEC' % persona, request, "add")
                return JsonResponse({"result": "ok"})
            else:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        elif action == 'activardesactivarperfil':
            try:
                instructor = CapInstructorIpec.objects.filter(instructor_id=int(request.POST['id']), status=True)[0]
                if instructor.estado_perfil():
                    instructor.activo = False
                    instructor.save(request)
                    log(u'Desactivo perfil de usuario de instructor: %s' % instructor, request, "desc")
                else:
                    if instructor.tiene_perfilusuario():
                        instructor.activo = True
                        instructor.save(request)
                        log(u'Desactivo perfil de usuario de instructor: %s' % instructor, request, "act")
                    else:
                        instructor.activo = True
                        instructor.save(request)
                        instructor.crear_eliminar_perfil_instructor(True)
                        log(u'Desactivo perfil de usuario de instructor: %s' % instructor, request, "act")
                        log(u'Se creo el perfil de usuario de instructor por activar perfil: %s' % instructor, request,
                            "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'listacursos':
            try:
                lista = []
                c = 0
                for i in CapInstructorIpec.objects.filter(instructor_id=request.POST['id']):
                    c = c + 1
                    etiqueta = 'important'
                    if i.capeventoperiodo.estado_evento() == 'EN CURSO':
                        etiqueta = 'info'
                    elif i.capeventoperiodo.estado_evento() == 'PENDIENTE':
                        etiqueta = 'warning'
                    lista.append(
                        [i.id, c, str(i.capeventoperiodo.capevento.nombre), str(i.capeventoperiodo.estado_evento()),
                         str(i.capeventoperiodo.fechainicio.strftime("%d-%m-%Y")),
                         str(i.capeventoperiodo.fechafin.strftime("%d-%m-%Y")), etiqueta])
                return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'crearperfil':
            try:
                instructor = CapInstructorIpec.objects.get(pk=int(request.POST['id']), status=True)
                if not instructor.tiene_perfilusuario():
                    if not instructor.instructor.usuario:
                        persona = Persona.objects.get(pk=instructor.instructor.id)
                        username = calculate_username(persona)
                        generar_usuario(persona, username, variable_valor('INSTRUCTOR_GROUP_ID'))
                        if EMAIL_INSTITUCIONAL_AUTOMATICO:
                            persona.emailinst = username + '@' + EMAIL_DOMAIN
                        persona.save(request)
                instructor.crear_eliminar_perfil_instructor(True)
                log(u'Se creo el perfil de usuario del instructor: %s' % instructor, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'activaremision':
            try:
                valor = 0
                if CapEventoPeriodoIpec.objects.filter(id=request.POST['id'], status=True).exists():
                    criterio = CapEventoPeriodoIpec.objects.get(id=request.POST['id'], status=True)
                    if not criterio.generarrubro:
                        criterio.generarrubro = True
                        valor = 1
                    elif criterio.generarrubro == False:
                        criterio.generarrubro = True
                        valor = 1
                    else:
                        criterio.generarrubro = False
                    criterio.save(request)
                return JsonResponse({"result": "ok", "valor": valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'reporte_detallado_general':
            try:
                __author__ = 'Unemi'

                title = easyxf(
                    'font: name Times New Roman, color-index black, bold on , height 220; alignment: horiz left')
                title2 = easyxf('font: name Verdana, color-index black, bold on , height 170; alignment: horiz left')
                fuentecabecera = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                fuentenormal = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentenormalneg = easyxf(
                    'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentenormalder = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
                fuentemoneda = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str=' "$" #,##0.00')
                fuentemonedaneg = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
                    num_format_str=' "$" #,##0.00')
                fuentenumero = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str='#,##0.00')

                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('Listado')

                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'documentos'))
                nombre = "INFORME_MOVIMIENTOS_EDU_CON_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
                filename = os.path.join(output_folder, nombre)

                fechacorte = convertir_fecha(request.POST['fechaf'])

                ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                ws.write_merge(1, 1, 0, 6, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', title)
                ws.write_merge(2, 2, 0, 6, 'DEUDAS DE ESTUDIANTES EDUCACIÓN CONTINUA', title)
                ws.write_merge(3, 3, 0, 6, 'FECHA DE CORTE: %s' % fechacorte, title)

                row_num = 5

                columns = [
                    (u"N°", 700),
                    (u"PER/INI", 3000),
                    (u"PER/FIN", 3000),
                    (u"PROGRAMAS", 4000),
                    (u"IDENTIFICACION", 3500),
                    (u"ESTUDIANTE", 8000),
                    (u"FECHA MATRICULA", 3000),
                    (u"FECHA RUBRO", 3000),
                    (u"TIPO MOVIMIENTO", 3000),
                    (u"VALOR PROGRAMA", 3000),
                    (u"VALOR UNEMI", 3000),
                    (u"ES UNEMI", 3000),
                    (u"VALOR NETO", 3000),
                    (u"VALOR CUOTA GENERADA", 3000),
                    (u"DIFERENCIA NO GENERADA", 3000),
                    (u"#CUOTA", 1500),
                    (u"FECHA VENCE PAGO", 3000),
                    (u"MONTO CUOTA", 3000),
                    (u"PAGADO", 3000),
                    (u"FECHA PAGO", 3000),
                    (u"MONTO PAGO", 3000),
                    (u"DEUDA", 3000),
                    (u"FACTURA", 4500),
                    (u"#INGRESO CAJA", 2500),
                    (u"FORMA PAGO", 3500),
                ]
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                    ws.col(col_num).width = columns[col_num][1]
                date_format = xlwt.XFStyle()
                date_format.num_format_str = 'yyyy/mm/dd'

                secuencia = 0
                matriculas = CapInscritoIpec.objects.db_manager('sga_select').select_related().filter(status=True,
                                                                                                      fecha_creacion__lte=fechacorte).distinct().order_by(
                    'capeventoperiodo__periodo', 'capeventoperiodo__fechainicio', 'participante__apellido1',
                    'participante__apellido2')

                for lista in matriculas:
                    row_num += 1
                    secuencia += 1
                    fila_totales = row_num
                    alumno = lista.participante.apellido1 + ' ' + lista.participante.apellido2 + ' ' + lista.participante.nombres
                    identificacion = lista.participante.identificacion()
                    evento = lista.capeventoperiodo

                    valorgenerado = lista.total_generado_alumno_programa(fechacorte)
                    valorpendiente = lista.total_saldo_rubrosinanular_programa(fechacorte)

                    ws.write(row_num, 0, secuencia, fuentenormalder)
                    ws.write(row_num, 1, u'%s' % evento.fechainicio, date_format)
                    ws.write(row_num, 2, u'%s' % evento.fechafin, date_format)
                    ws.write(row_num, 3, u'%s' % evento.capevento.codigo(), fuentenormal)
                    ws.write(row_num, 4, u'%s' % identificacion, fuentenormal)
                    ws.write(row_num, 5, u'%s' % alumno, fuentenormal)
                    ws.write(row_num, 6, lista.fecha_creacion, date_format)
                    ws.write(row_num, 7, '', fuentenormal)
                    ws.write(row_num, 8, 'COSTO', fuentenormal)
                    ws.write(row_num, 9, evento.costoexterno, fuentemonedaneg)
                    ws.write(row_num, 10, evento.costo, fuentemonedaneg)
                    ws.write(row_num, 11, 'SI' if lista.personalunemi else 'NO', fuentenormal)
                    costo = evento.costo if lista.personalunemi else evento.costoexterno
                    diferencia = null_to_decimal(costo - valorgenerado, 2)
                    ws.write(row_num, 12, costo, fuentemonedaneg)
                    ws.write(row_num, 13, valorgenerado, fuentemonedaneg)
                    ws.write(row_num, 14, diferencia if diferencia != 0 else '', fuentemonedaneg)
                    ws.write(row_num, 15, '', fuentenormal)
                    ws.write(row_num, 16, '', fuentenormal)
                    ws.write(row_num, 17, '', fuentenormal)
                    ws.write(row_num, 19, '', fuentenormal)
                    ws.write(row_num, 20, '', fuentenormal)
                    ws.write(row_num, 21, valorpendiente, fuentemonedaneg)
                    ws.write(row_num, 22, '', fuentenormal)
                    ws.write(row_num, 23, '', fuentenormal)
                    ws.write(row_num, 24, '', fuentenormal)
                    cuota = 0
                    for rubro in lista.capeventoperiodo.rubro_set.db_manager('sga_select').select_related().filter(
                            persona_id=lista.participante_id, status=True, fecha__lte=fechacorte).distinct().order_by(
                        'fechavence'):
                        anulado = Decimal(null_to_decimal(
                            rubro.pago_set.db_manager('sga_select').filter(status=True, factura__valida=False,
                                                                           factura__status=True).aggregate(
                                valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))
                        liquidado = Decimal(null_to_decimal(
                            PagoLiquidacion.objects.db_manager('sga_select').filter(status=True,
                                                                                    pagos__rubro=rubro).aggregate(
                                valor=Sum('pagos__valortotal'))['valor'], 2)).quantize(Decimal('.01'))
                        if (rubro.valortotal - (liquidado + anulado)) > 0:
                            row_num += 1
                            secuencia += 1
                            cuota += 1
                            ws.write(row_num, 0, secuencia, fuentenormalder)
                            ws.write(row_num, 1, u'%s' % evento.fechainicio, date_format)
                            ws.write(row_num, 2, u'%s' % evento.fechafin, date_format)
                            ws.write(row_num, 3, u'%s' % evento.capevento.codigo(), fuentenormal)
                            ws.write(row_num, 4, u'%s' % identificacion, fuentenormal)
                            ws.write(row_num, 5, u'%s' % alumno, fuentenormal)
                            ws.write(row_num, 6, '', fuentenormal)
                            ws.write(row_num, 7, rubro.fecha, date_format)
                            ws.write(row_num, 8, 'CUOTA', fuentenormal)
                            ws.write(row_num, 9, '', fuentenormal)
                            ws.write(row_num, 10, '', fuentenormal)
                            ws.write(row_num, 11, '', fuentenormal)
                            ws.write(row_num, 12, '', fuentenormal)
                            ws.write(row_num, 13, '', fuentenormal)
                            ws.write(row_num, 14, '', fuentenormal)
                            ws.write(row_num, 15, cuota, fuentenormal)
                            ws.write(row_num, 16, rubro.fechavence, date_format)
                            ws.write(row_num, 17, (rubro.valortotal - (liquidado + anulado)), fuentemoneda)
                            ws.write(row_num, 18, '', fuentenormal)
                            ws.write(row_num, 19, '', fuentenormal)
                            ws.write(row_num, 20, '', fuentenormal)
                            ws.write(row_num, 21, '', fuentenormal)
                            ws.write(row_num, 22, '', fuentenormal)
                            ws.write(row_num, 23, '', fuentenormal)
                            ws.write(row_num, 24, '', fuentenormal)

                            for pago in rubro.pago_set.db_manager('sga_select').select_related().filter(status=True,
                                                                                                        pagoliquidacion__isnull=True,
                                                                                                        fecha__lte=fechacorte).exclude(
                                factura__valida=False, factura__status=True):
                                row_num += 1
                                secuencia += 1
                                ws.write(row_num, 0, secuencia, fuentenormalder)
                                ws.write(row_num, 1, u'%s' % evento.fechainicio, date_format)
                                ws.write(row_num, 2, u'%s' % evento.fechafin, date_format)
                                ws.write(row_num, 3, u'%s' % evento.capevento.codigo(), fuentenormal)
                                ws.write(row_num, 4, u'%s' % identificacion, fuentenormal)
                                ws.write(row_num, 5, u'%s' % alumno, fuentenormal)
                                ws.write(row_num, 6, '', fuentenormal)
                                ws.write(row_num, 7, '', fuentenormal)
                                ws.write(row_num, 8, 'PAGO', fuentenormal)
                                ws.write(row_num, 9, '', fuentenormal)
                                ws.write(row_num, 10, '', fuentenormal)
                                ws.write(row_num, 11, '', fuentenormal)
                                ws.write(row_num, 12, '', fuentenormal)
                                ws.write(row_num, 13, '', fuentenormal)
                                ws.write(row_num, 14, '', fuentenormal)
                                ws.write(row_num, 15, cuota, fuentenormal)
                                ws.write(row_num, 16, '', fuentenormal)
                                ws.write(row_num, 17, '', fuentenormal)
                                ws.write(row_num, 18, '', fuentenormal)
                                ws.write(row_num, 19, pago.fecha, date_format)
                                ws.write(row_num, 20, pago.valortotal, fuentemoneda)
                                ws.write(row_num, 21, '', fuentenormal)
                                ws.write(row_num, 22, pago.factura().numerocompleto if pago.factura() else '',
                                         fuentenormal)
                                ws.write(row_num, 23, pago.comprobante.numero if pago.comprobante else '', fuentenormal)
                                ws.write(row_num, 24, pago.tipo(), fuentenormal)
                    ws.write(fila_totales, 18, Formula("SUM(U%s:U%s" % (fila_totales + 1, row_num + 1) + ")"),
                             fuentemonedaneg)

                row_num += 1

                wp = wb.add_sheet('Programas')
                wp.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                wp.write_merge(1, 1, 0, 6, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', title)
                wp.write_merge(2, 2, 0, 6, 'PROGRMAS EDUCACIÓN CONTINUA', title)
                columns = [
                    (u"N°", 700),
                    (u"ALIAS", 3500),
                    (u"PROGRAMAS", 16000),
                ]

                row_num = 5
                secuencia = 0
                for col_num in range(len(columns)):
                    wp.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                    wp.col(col_num).width = columns[col_num][1]
                eventos_id = CapInscritoIpec.objects.db_manager('sga_select').values_list(
                    "capeventoperiodo__capevento_id").filter(status=True, fecha_creacion__lte=fechacorte).distinct()
                carreras = CapEventoIpec.objects.db_manager('sga_select').filter(pk__in=eventos_id)
                for lista in carreras:
                    row_num += 1
                    secuencia += 1
                    wp.write(row_num, 0, secuencia, fuentenormalder)
                    wp.write(row_num, 1, u'%s' % lista.codigo(), fuentenormal)
                    wp.write(row_num, 2, u'%s' % lista.nombre, fuentenormal)

                wb.save(filename)
                return JsonResponse({"result": "ok", "archivo": 'https://sga.unemi.edu.ec/media/documentos/%s' % nombre})
            except Exception as ex:
                pass

        elif action == 'observacioninscripcion':
            try:
                form = ObservacionInscritoEventoIpecForm(request.POST)
                if form.is_valid():
                    inscrito = CapInscritoIpec.objects.get(pk=int(request.POST['id']))
                    inscrito.observacionmanual = form.cleaned_data['observacionmanual']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("observacion_inscripcionipec", newfile._name)
                        inscrito.archivo = newfile
                    inscrito.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'moverinscrito':
            try:
                form = MoverInscritoEventoIpecForm(request.POST)
                if form.is_valid():
                    inscrito = CapInscritoIpec.objects.get(pk=int(request.POST['id']))
                    if CapInscritoIpec.objects.filter(status=True, participante=inscrito.participante,
                                                      capeventoperiodo_id=int(request.POST['curso'])).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra inscrito"})
                    if not CapEventoPeriodoIpec.objects.get(pk=int(request.POST['curso'])).hay_cupo_inscribir():
                        return JsonResponse({"result": "bad", "mensaje": u"No hay cupo para continuar adicionando"})

                    rubros = Rubro.objects.filter(status=True, persona=inscrito.participante,
                                                  capeventoperiodoipec=inscrito.capeventoperiodo)
                    inscrito.observacionmover = form.cleaned_data['observacion']
                    inscrito.capeventoperiodo = form.cleaned_data['curso']
                    inscrito.save(request)
                    for r in rubros:
                        r.capeventoperiodoipec = inscrito.capeventoperiodo
                        r.save()
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'verobservacioninscripcion':
            try:
                # iditem
                data['inscrito'] = inscrito = CapInscritoIpec.objects.get(pk=int(request.POST['id']))
                data['title'] = u'Observación'
                template = get_template("adm_capacitacioneventoperiodoipec/verobservacioninscripcion.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad"})
        # Rubros
        if action == 'addrubros':
            try:
                form = TipoOtroRubroIpecForm(request.POST)
                if form.is_valid():
                    registro = TipoOtroRubro(nombre=form.cleaned_data['nombre'],
                                             partida_id=100,
                                             unidad_organizacional_id=115,
                                             programa_id=8,
                                             interface=True,
                                             valor=form.cleaned_data['valor'],
                                             ivaaplicado=form.cleaned_data['ivaaplicado'],
                                             activo=True,
                                             tiporubro=2,
                                             exportabanco=False,
                                             nofactura=False)
                    registro.save(request)
                    log(u'Registro nuevo rubro: %s' % registro, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editrubros':
            try:
                form = TipoOtroRubroIpecForm(request.POST)
                if form.is_valid():
                    rubro = TipoOtroRubro.objects.get(pk=int(request.POST['id']))
                    if rubro.se_usa():
                        return JsonResponse({"result": "bad", "mensaje": "El rubro se encuentra en uso."})
                    if TipoOtroRubro.objects.filter(nombre=(request.POST['nombre'])).exists():
                        return JsonResponse({"result": "bad", "mensaje": "Existe un rubro con el mismo nombre."})
                    rubro.nombre = form.cleaned_data['nombre']
                    rubro.valor = form.cleaned_data['valor']
                    rubro.ivaaplicado = form.cleaned_data['ivaaplicado']
                    rubro.save(request)

                    log(u'Registro modificado Rubro: %s' % rubro, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al editar los datos."})

        if action == 'deleterubro':
            try:
                rubro = TipoOtroRubro.objects.get(pk=request.POST['id'], status=True)
                if rubro.se_usa():
                    return JsonResponse({"result": "bad", "mensaje": "El rubro se encuentra en uso."})
                rubro.delete()
                log(u'Eliminó rubro: %s' % rubro, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'vinvularrubro':
            try:
                rubro = Rubro.objects.get(pk=int(request.POST['idrubro']))
                codigoeventoanterior = rubro.capeventoperiodoipec_id
                rubro.capeventoperiodoipec_id = int(request.POST['codeventoipec'])
                rubro.save(request)
                codigoeventoactual = int(request.POST['codeventoipec'])
                log(u'Vinculó rubro de curso IPEC: %s idrubro %s codeventoanterior: %s codigoeventoactual: %s ' % (
                rubro, rubro.id, codigoeventoanterior, codigoeventoactual), request, "vin")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al vincular rubro."})

        if action == 'eliminamasivo':
            try:
                evento = CapEventoPeriodoIpec.objects.get(pk=int(request.POST['codeventoipec']))
                inscritos = CapInscritoIpec.objects.filter(capeventoperiodo=evento, status=True)
                totaleliminado, idrubrosunemieliminar = 0, []
                for inscrito in inscritos:
                    nota = inscrito.nota_total_evento(evento)

                    if not nota:
                        if not inscrito.rutapdf:
                            if Rubro.objects.filter(cancelado=False, status=True, persona=inscrito.participante,
                                                    capeventoperiodoipec=evento).exists():
                                rubro = Rubro.objects.get(cancelado=False, status=True, persona=inscrito.participante,
                                                          capeventoperiodoipec=evento)

                                # if not rubro.tiene_pagos():
                                #     inscrito.desactivado = True
                                #     inscrito.save(request)
                                #     rubro.status = False
                                #     rubro.save(request)
                                #     totaleliminado += 1
                                #     if rubro.epunemi and rubro.idrubroepunemi > 0:
                                #         # OJO FALTA VALIDAR QUE SÓLO PUEDA ELIMINAR SI NO TIENE PAGOS EN EPUNEMI
                                #         cursor = connections['epunemi'].cursor()
                                #         sql = "UPDATE sagest_rubro SET status=false WHERE sagest_rubro.status=true and sagest_rubro.id=" + str(
                                #             rubro.idrubroepunemi)
                                #         cursor.execute(sql)
                                #         cursor.close()
                                #         log(u'Elimino rubro: %s - %s' % (rubro, rubro.persona), request, "del")
                                idrubrosunemieliminar.append(rubro.id)
                rubrosunemi_aeliminar = Rubro.objects.filter(id__in=idrubrosunemieliminar)
                # Eliminar y migrar a epunemi
                result_migrar = eliminar_y_migrar_rubro_deunemi_aepunemi(request, rubrosunemi_aeliminar, action='borrar_rubro', procesomasivo=True)
                if result_migrar['result'] == "ok":
                    mensajemigrar = result_migrar['mensaje']
                    result_rubrosunemi = mensajemigrar['total_rubrosunemi']
                    result_rubrosepunemi = mensajemigrar['total_rubrosepunemi']
                    resultrubpagados_noeli = mensajemigrar['rubrospagados_noeliminados']
                    if result_rubrosunemi == 0 and result_rubrosepunemi == 0:
                        if resultrubpagados_noeli:
                            mensajeeliminados = f'No se eliminó ningún rubro. Por los siguientes motivos: {resultrubpagados_noeli}.'
                        else:
                            mensajeeliminados = f'No se eliminó ningún rubro.'
                    else:
                        if resultrubpagados_noeli:
                            mensajeeliminados = f"Se han eliminado {result_rubrosunemi} rubros y se han migrado(eliminado) {result_rubrosepunemi} rubros a EPUNEMI exitosamente. No se eliminaron o migraron: {resultrubpagados_noeli}."
                            # mensajeeliminados = f"Se han migrado (eliminado) {result_rubrosepunemi} rubros exitosamente a EPUNEMI."
                        else:
                            mensajeeliminados = f"Se han eliminado {result_rubrosunemi} rubros y se han migrado(eliminado) {result_rubrosepunemi} rubros a EPUNEMI exitosamente."

                    # Desactivar
                    # Desactivar
                    # "mensaje": mensajeeliminados
                    messages.success(request, mensajeeliminados)
                    return JsonResponse({"result": "ok", })

                else:
                    raise NameError(result_migrar['mensaje'])
                # Eliminar y migrar a epunemi
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar rubros. {} CodLine {}".format(ex, sys.exc_info()[-1].tb_lineno)})

        if action == 'activamasivo':
            try:
                evento = CapEventoPeriodoIpec.objects.get(pk=int(request.POST['codeventoipec']))

                # Si el evento no tiene costo no podrá generar rubros.
                if evento.costo == 0 and evento.costoexterno == 0:
                    return JsonResponse({'result': 'bad', "mensaje": u"Éste evento no tiene costo, por lo tanto no se permite generar rubros a los inscritos."})

                # Si el evento genera rubros=true debe tener tipo rubro
                if not evento.tiporubro and evento.generarrubro:
                    return JsonResponse({'result': 'bad', "mensaje": u"No existe rubro en éste evento, por lo tanto no puede generar rubros a los inscritos."})

                # Inscritos que NO se hayan desactivado y que NO tengan rubro creado
                inscritos = CapInscritoIpec.objects.filter(status=True, capeventoperiodo=evento, desactivado=False)
                if not inscritos:
                    return JsonResponse({'result': 'bad', "mensaje": u"No hay inscritos pendientes de generación de rubro."})

                totalrubros, listarubrosunemi = 0, []
                for inscribir in inscritos:

                    if not inscribir.existerubrocurso():
                        tiprubroarancel = inscribir.capeventoperiodo.tiporubro
                        personalunemi = False
                        if inscribir.participante.distributivopersona_set.filter(estadopuesto_id=1, status=True).exists():
                            costo_total_curso = inscribir.capeventoperiodo.costo
                            personalunemi = True
                        else:
                            if inscribir.participante.inscripcion_set.filter(status=True).exclude(coordinacion_id=9):
                                verificainsripcion = inscribir.participante.inscripcion_set.values_list('id').filter(
                                    status=True).exclude(coordinacion_id=9)
                                if Matricula.objects.filter(inscripcion_id__in=verificainsripcion, status=True):
                                    costo_total_curso = inscribir.capeventoperiodo.costo
                                    personalunemi = True
                                else:
                                    if RecordAcademico.objects.filter(inscripcion_id__in=verificainsripcion, status=True):
                                        costo_total_curso = inscribir.capeventoperiodo.costo
                                        personalunemi = True
                                    else:
                                        costo_total_curso = inscribir.capeventoperiodo.costoexterno
                            else:
                                costo_total_curso = inscribir.capeventoperiodo.costoexterno

                        if inscribir.capeventoperiodo.generarrubro:
                            inscribir.personalunemi = personalunemi
                            inscribir.save()
                            if not Rubro.objects.filter(persona=inscribir.participante,
                                                        capeventoperiodoipec=inscribir.capeventoperiodo,
                                                        status=True).exists():
                                rubro = Rubro(tipo=tiprubroarancel,
                                              persona=inscribir.participante,
                                              relacionados=None,
                                              nombre=tiprubroarancel.nombre + ' - ' + inscribir.capeventoperiodo.capevento.nombre,
                                              cuota=1,
                                              fecha=datetime.now().date(),
                                              fechavence=inscribir.capeventoperiodo.fechamaxpago + timedelta(days=1),
                                              valor=costo_total_curso,
                                              iva_id=1,
                                              valortotal=costo_total_curso,
                                              capeventoperiodoipec=inscribir.capeventoperiodo,
                                              saldo=costo_total_curso,
                                              epunemi=True,
                                              cancelado=False)
                                rubro.save(request)
                                totalrubros += 1
                                # Listado de rubros a migrar
                                listarubrosunemi.append(rubro)
                if totalrubros > 0:
                    # Migrar rubros
                    resultado_migraciones = migrar_crear_rubro_deunemi_aepunemi(request, listarubrosunemi, action='activamasivo')
                    if resultado_migraciones['result'] == 'ok':
                        resultado_funcion = resultado_migraciones['mensaje']
                        log(u'Generó rubros masivo a los inscritos en evento IPEC: %s [%s]' % (inscritos, inscribir.capeventoperiodo.id), request, "add")
                        messages.success(request, f"Se creó {totalrubros} rubros y se migró {resultado_funcion['total']} rubros exitosamente a EPUNEMI.")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError(resultado_migraciones['mensaje'])
                    # Migrar rubros
                else:
                    return JsonResponse({'result': 'bad', "mensaje": u"No hay inscritos pendientes de generación de rubro."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar los rubros a los inscritos. {} CodLine {}".format(ex,
                                                                                                                   sys.exc_info()[
                                                                                                                       -1].tb_lineno)})

        if action == 'activainscrito':
            try:
                inscrito = CapInscritoIpec.objects.get(pk=int(request.POST['idinscrito']))
                inscrito.desactivado=False
                inscrito.save()
                log(u'Activó inscrito: %s' % (inscrito), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al activar inscrito. {} CodLine {}".format(ex,
                                                                                                                   sys.exc_info()[
                                                                                                                       -1].tb_lineno)})

        elif action == 'actualizar_modelo_moodle':
            try:
                evento = CapEventoPeriodoIpec.objects.get(pk=request.POST['id'], status=True)
                clave = request.POST['clave']
                evento.crear_actualizar_categoria_notas_curso(clave)
                log(u'Actualizo moodle evento docente: %s' % (evento), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al actualizar los datos."})

        elif action == 'importarinscritos':
            try:
                idinstructor = request.POST['idinstructor']
                lista = request.POST['lista'].split(',')
                curso = CapInstructor.object.get(id=idinstructor)
                for elemento in lista:
                    if not CapInscritoIpec.objects.filter(inscripcion__status=True, inscripcion_id=elemento,
                                                                   grupoexamen_id=idinstructor, status=True):
                        integrantes = CapInscritoIpec(inscripcion_id=elemento,
                                                               grupoexamen_id=idinstructor)
                        integrantes.save(request)
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'listadoexportarmoodle':
            try:
                instructor = CapInstructorIpec.objects.get(pk=request.POST['idinstructor'])
                modeloNotas = instructor.capnotaipec_set.filter(status=True).count()
                if modeloNotas > 0:
                    curso = instructor.capeventoperiodo
                    if curso.costo:
                        listadocodigo = curso.list_inscritos_costo().values_list('participante__idusermoodleposgrado', flat=True)
                    else:
                        listadocodigo = curso.list_inscritos_sin_costo().values_list('participante__idusermoodleposgrado', flat=True)


                    cursorpos = connections['moodle_pos'].cursor()
                    sql = """SELECT DISTINCT  ARRAY_TO_STRING(array_agg(us1.id),',')                                      
                             FROM mooc_role_assignments asi
                            INNER JOIN MOOC_CONTEXT CON ON asi.CONTEXTID=CON.ID
                            INNER JOIN mooc_user us1 ON us1.id=asi.userid
                            AND ASI.ROLEID=%s
                            AND CON.INSTANCEID=%s
                            AND us1.id in %s""" % (10, instructor.idcursomoodle, tuple(listadocodigo))
                    cursorpos.execute(sql)
                    listadosmoodle = []
                    row = cursorpos.fetchall()
                    if instructor.idcursomoodle:
                        if row[0][0]:
                            listadosmoodle = row[0][0].split(",")
                    listac = None
                    if curso.costo:
                        listacurso = curso.list_inscritos_costo()
                    else:
                        listacurso = curso.list_inscritos_sin_costo()

                    listac = listacurso.values('id', 'participante__id',
                                                               'participante__apellido1',
                                                               'participante__apellido2',
                                                               'participante__nombres').filter(
                    participante__status=True, status=True).exclude(
                    participante__idusermoodleposgrado__in=listadosmoodle).order_by(
                    'participante__apellido1',
                    'participante__apellido2',
                    'participante__nombres')
                    cursorpos.close()
                    return JsonResponse({"result": "ok", "cantidad": len(listac),
                                         "listacurso": list(listac)})
                else:
                    return JsonResponse({"result":"bad", "mensaje": u"Asigne un modelo evaluativo al evento"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al verificar listado."})

        elif action == 'exportarinscrito':
            try:
                contador = int(request.POST['contador'])
                inscrito = request.POST['inscrito']
                instructor = CapInstructorIpec.objects.get(status=True, pk=request.POST['idinstructor'])
                grupo = instructor.capeventoperiodo
                codigointegrante = grupo.capinscritoipec_set.get(pk=inscrito, status=True)
                codigointegrante.encursomoodle = True
                codigointegrante.save(request)
                instructor.crear_curso_moodle(inscrito, contador, edcon=True)
                time.sleep(3)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'resetearusu':
            try:
                inscripcion = CapInscritoIpec.objects.get(pk=request.POST['id'])
                pers = inscripcion.participante
                usuario = pers.usuario
                password = pers.identificacion()
                usuario.set_password(password)
                usuario.save()
                pers.clave_cambiada()
                if not UserAuth.objects.filter(usuario=usuario).exists():
                    usermoodle = UserAuth(usuario=usuario)
                    usermoodle.set_data()
                    usermoodle.set_password(password)
                    usermoodle.save()
                else:
                    usermoodle = UserAuth.objects.filter(usuario=usuario)[0]
                    usermoodle.set_data()
                    usermoodle.set_password(password)
                    usermoodle.save()
                log(u'Reseteo clave de inscrito: %s' % inscripcion, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'generarrubrodiferido':
            try:
                form = GenerarRubroDiferidoForm(request.POST)
                if form.is_valid():
                    fechavence = form.cleaned_data['fechavence']
                    c = 1
                    vc = 0
                    fechav = None
                    if int(form.cleaned_data['cuota']) > 1:
                        inscribir = CapInscritoIpec.objects.get(id=request.POST['id'])

                        if not inscribir.capeventoperiodo.tiporubro and inscribir.capeventoperiodo.generarrubro:
                            return JsonResponse({'result': 'bad', "mensaje": u"No existe Rubro en curso."})
                        tiprubroarancel = inscribir.capeventoperiodo.tiporubro

                        personalunemi = False
                        if inscribir.participante.distributivopersona_set.filter(estadopuesto_id=1, status=True).exists():
                            costo_total_curso = inscribir.capeventoperiodo.costo
                            personalunemi = True
                        else:
                            if inscribir.participante.inscripcion_set.filter(status=True).exclude(coordinacion_id=9):
                                verificainsripcion = inscribir.participante.inscripcion_set.values_list('id').filter(
                                    status=True).exclude(coordinacion_id=9)
                                if Matricula.objects.filter(inscripcion_id__in=verificainsripcion, status=True):
                                    costo_total_curso = inscribir.capeventoperiodo.costo
                                    personalunemi = True
                                else:
                                    if RecordAcademico.objects.filter(inscripcion_id__in=verificainsripcion,
                                                                      status=True):
                                        costo_total_curso = inscribir.capeventoperiodo.costo
                                        personalunemi = True
                                    else:
                                        costo_total_curso = inscribir.capeventoperiodo.costoexterno
                            else:
                                costo_total_curso = inscribir.capeventoperiodo.costoexterno

                        if inscribir.capeventoperiodo.generarrubro:
                            inscribir.personalunemi = personalunemi
                            inscribir.formapago = 2
                            inscribir.save()

                            vc = costo_total_curso / int(form.cleaned_data['cuota'])
                            while c <= int(form.cleaned_data['cuota']):
                                if c > 1:
                                    fechav = fechav + relativedelta(months=1)
                                else:
                                    fechav = fechavence

                                if not Rubro.objects.filter(persona=inscribir.participante, capeventoperiodoipec=inscribir.capeventoperiodo, cuota=c, status=True).exists():
                                    rubro = Rubro(tipo=tiprubroarancel,
                                                  persona=inscribir.participante,
                                                  relacionados=None,
                                                  nombre=tiprubroarancel.nombre + ' - ' + inscribir.capeventoperiodo.capevento.nombre,
                                                  cuota=c,
                                                  fecha=datetime.now().date(),
                                                  fechavence=fechav,
                                                  valor=vc,
                                                  iva_id=1,
                                                  valortotal=vc,
                                                  capeventoperiodoipec=inscribir.capeventoperiodo,
                                                  saldo=vc,
                                                  epunemi=True,
                                                  cancelado=False)
                                    rubro.save(request)
                                    log(u'Adiciono un inscrito en Evento en Capacitacion IPEC: %s [%s]' % (
                                        inscribir, inscribir.participante.id),
                                        request, "add")
                                    # Migración a EPUNEMI
                                    resultado_migracion = migrar_crear_rubro_deunemi_aepunemi(request, [rubro],
                                                                                              action='generar_rubro')
                                    if resultado_migracion['result'] == 'ok':
                                        res_json = {"error": False}
                                        messages.success(request, "Se creó  el rubro y se migró exitosamente a EPUNEMI.")
                                        c += 1
                                    else:
                                        raise NameError(resultado_migracion['mensaje'])
                                    # Migración a EPUNEMI
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({"result": True, "mensaje": "El proceso de pago dfierido requiere de mínimo 2 cuotas."}, safe=False)
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return HttpResponseRedirect(request.path)

    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'reportecarteravencidatotal':
                try:
                    fechaactual = datetime.now().date()
                    periodoid = request.GET.get("idperiodo", '')
                    if periodoid:
                        periodo = CapPeriodoIpec.objects.get(pk=periodoid)
                        carreras = CapEventoPeriodoIpec.objects.filter(periodo_id=periodoid, status=True).order_by(
                            'periodo__nombre')
                    else:
                        carreras = CapEventoPeriodoIpec.objects.filter(status=True).order_by('periodo__nombre')

                    __author__ = 'UNIVERSIDAD ESTATAL DE MILAGRO'

                    title = easyxf(
                        'font: name Calibri, color-index black, bold on , height 350; alignment: horiz centre')
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
                    ws = wb.add_sheet('CARTERA VENCIDA GENERAL')
                    response = HttpResponse(content_type="application/ms-excel")
                    if not periodoid:
                        response[
                            'Content-Disposition'] = 'attachment; filename=cartera_vencida_general_' + random.randint(1,
                                                                                                                      10000).__str__() + '.xls'
                    else:
                        response[
                            'Content-Disposition'] = 'attachment; filename=cartera_vencida_general_{}_{}.xls'.format(
                            periodo.descripcion.lower(), random.randint(1, 10000).__str__())
                    ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 7, 'CARTERA VENCIDA {}'.format(str(datetime.now().date())), fuentenormal)
                    columns = [
                        (u"#", 1000),
                        (u"PERIODO AÑO", 3000),
                        (u"PERIODO", 12000),
                        (u"PROGRAMA EN EJECUCIÓN", 12000),
                        (u"TOTAL RECAUDADO", 6000),
                        (u"TOTAL PENDIENTE", 6000),
                        (u"TOTAL VENCIDO", 6000),
                        (u"TOTAL", 6000),
                    ]
                    row_num = 2
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 3
                    saldovencido_total = 0
                    saldo_total = 0
                    valor_total = 0
                    valor_pagado_total = 0
                    count = 0

                    rubrosvencidos = Rubro.objects.filter(
                        capeventoperiodoipec__in=carreras.values_list('pk', flat=True), status=True,
                        fechavence__lt=fechaactual).values_list('capeventoperiodoipec__id', flat=True).distinct(
                        'capeventoperiodoipec')

                    for car in carreras.filter(pk__in=rubrosvencidos):
                        saldovencido = null_to_decimal(Rubro.objects.filter(capeventoperiodoipec=car, status=True,
                                                                            fechavence__lt=fechaactual).aggregate(
                            valor=Sum('saldo'))['valor'], 2)
                        saldo = null_to_decimal(
                            Rubro.objects.filter(capeventoperiodoipec=car, status=True, ).aggregate(valor=Sum('saldo'))[
                                'valor'], 2)
                        valor = null_to_decimal(Rubro.objects.filter(capeventoperiodoipec=car, status=True, ).aggregate(
                            valor=Sum('valortotal'))['valor'], 2)
                        valor_pagado = Decimal(null_to_decimal(
                            Pago.objects.filter(rubro__capeventoperiodoipec=car, status=True,
                                                rubro__status=True).aggregate(valor=Sum('valortotal'))['valor'],
                            2)).quantize(Decimal('.01'))
                        ws.write_merge(row_num, row_num, 0, 0, count, font_style2)
                        ws.write_merge(row_num, row_num, 1, 1, car.periodo.nombre, font_style2)
                        ws.write_merge(row_num, row_num, 2, 2, car.periodo.descripcion, font_style2)
                        ws.write_merge(row_num, row_num, 3, 3, car.capevento.nombre, font_style2)
                        ws.write_merge(row_num, row_num, 4, 4, valor_pagado, font_style2)
                        ws.write_merge(row_num, row_num, 5, 5, saldo, font_style2)
                        ws.write_merge(row_num, row_num, 6, 6, saldovencido, font_style2)
                        ws.write_merge(row_num, row_num, 7, 7, valor, font_style2)
                        row_num += 1
                        count += 1
                        valor_pagado_total += valor_pagado
                        saldo_total += saldo
                        valor_total += valor
                        saldovencido_total += saldovencido
                    ws.write_merge(row_num, row_num, 0, 3, u'TOTAL DE EJECUCIÓN', font_style)
                    ws.write_merge(row_num, row_num, 4, 4, Decimal(valor_pagado_total), font_style2)
                    ws.write_merge(row_num, row_num, 5, 5, Decimal(saldo_total), font_style2)
                    ws.write_merge(row_num, row_num, 6, 6, Decimal(saldovencido_total), font_style2)
                    ws.write_merge(row_num, row_num, 7, 7, Decimal(valor_total), font_style2)
                    wb.save(response)
                    return response
                except Exception as ex:
                    print(ex)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            # PERIODO
            if action == 'addperiodo':
                try:
                    data['title'] = u'Adicionar Periodo'
                    data['form'] = CapPeriodoIpecForm()
                    return render(request, "adm_capacitacioneventoperiodoipec/addperiodo.html", data)
                except Exception as ex:
                    pass

            elif action == 'delperiodo':
                try:
                    data['title'] = u'Eliminar Periodo'
                    data['periodo'] = CapPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitacioneventoperiodoipec/delperiodo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editperiodo':
                try:
                    data['title'] = u'Editar Periodo'
                    data['periodo'] = periodo = CapPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    form = CapPeriodoIpecForm(initial={'nombre': periodo.nombre, 'descripcion': periodo.descripcion,
                                                       'fechainicio': periodo.fechainicio,
                                                       'fechafin': periodo.fechafin})
                    if periodo.esta_cap_evento_periodo_activo():
                        form.editar_grupo()
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec/editperiodo.html", data)
                except Exception as ex:
                    pass
            # EVENTO
            elif action == 'addevento':
                try:
                    data['title'] = u'Adicionar Evento'
                    data['form'] = CapEventoIpecForm()
                    return render(request, "adm_capacitacioneventoperiodoipec/addevento.html", data)
                except Exception as ex:
                    pass

            elif action == 'delevento':
                try:
                    data['title'] = u'Eliminar Evento'
                    data['evento'] = CapEventoIpec.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitacioneventoperiodoipec/delevento.html", data)
                except Exception as ex:
                    pass


            elif action == 'actualizar_modelo_moodle_pos':
                try:
                    instructor = CapInstructorIpec.objects.get(pk=request.GET['id'], status=True)
                    modeloNotas = instructor.capnotaipec_set.filter(status=True).count()
                    if modeloNotas > 0:
                        if instructor.idcursomoodle != 0:
                            modelo = instructor.crear_actualizar_categoria_notas_curso()
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

            elif action == 'editevento':
                try:
                    data['title'] = u'Editar Evento'
                    data['evento'] = evento = CapEventoIpec.objects.get(pk=int(request.GET['id']))
                    form = CapEventoIpecForm(initial={'nombre': evento.nombre})
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec/editevento.html", data)
                except Exception as ex:
                    pass

            elif action == 'eventos':
                try:
                    data['title'] = u'Evento'
                    data['evento'] = CapEventoIpec.objects.filter(status=True)
                    return render(request, "adm_capacitacioneventoperiodoipec/viewevento.html", data)
                except Exception as ex:
                    pass
            # ENFOQUE
            elif action == 'addenfoque':
                try:
                    data['title'] = u'Adicionar Capacitación Enfoque'
                    data['form'] = CapEnfocadaIpecForm()
                    return render(request, "adm_capacitacioneventoperiodoipec/addenfoque.html", data)
                except Exception as ex:
                    pass

            elif action == 'delenfoque':
                try:
                    data['title'] = u'Eliminar Capacitación Enfoque'
                    data['enfocada'] = CapEnfocadaIpec.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitacioneventoperiodoipec/delenfoque.html", data)
                except Exception as ex:
                    pass

            elif action == 'editenfoque':
                try:
                    data['title'] = u'Editar Capacitación Enfoque'
                    data['enfocada'] = enfo = CapEnfocadaIpec.objects.get(pk=int(request.GET['id']))
                    form = CapEnfocadaIpecForm(initial={'nombre': enfo.nombre})
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec/editenfoque.html", data)
                except Exception as ex:
                    pass

            elif action == 'enfoques':
                try:
                    data['title'] = u'Enfoque'
                    data['enfocada'] = CapEnfocadaIpec.objects.filter(status=True)
                    return render(request, "adm_capacitacioneventoperiodoipec/viewenfoque.html", data)
                except Exception as ex:
                    pass
            # TURNO
            elif action == 'addturno':
                try:
                    data['title'] = u'Adicionar Turno'
                    form = CapTurnoIpecForm(initial={'turno': int((CapTurnoIpec.objects.filter(status=True).aggregate(
                        Max('turno'))['turno__max']) + 1) if CapTurnoIpec.objects.filter(status=True).exists() else 1})
                    form.editar_grupo()
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec/addturno.html", data)
                except Exception as ex:
                    pass

            elif action == 'delturno':
                try:
                    data['title'] = u'Eliminar Turno'
                    data['turno'] = CapTurnoIpec.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitacioneventoperiodoipec/delturno.html", data)
                except Exception as ex:
                    pass

            elif action == 'editturno':
                try:
                    data['title'] = u'Editar Turno'
                    data['turno'] = turno = CapTurnoIpec.objects.get(pk=int(request.GET['id']))
                    form = CapTurnoIpecForm(initial={'turno': turno.turno,
                                                     'horainicio': str(turno.horainicio),
                                                     'horafin': str(turno.horafin),
                                                     'horas': str(turno.horas)})
                    form.editar_grupo()
                    form.editar_turno()
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec/editturno.html", data)
                except Exception as ex:
                    pass

            elif action == 'turnos':
                try:
                    data['title'] = u'Turnos'
                    data['turno'] = CapTurnoIpec.objects.filter(status=True)
                    return render(request, "adm_capacitacioneventoperiodoipec/viewturno.html", data)
                except Exception as ex:
                    pass
            # CONFIGURACION
            elif action == 'configuracion':
                try:
                    data['title'] = u'Configuración'
                    configuracion = CapConfiguracionIpec.objects.filter()
                    if configuracion.exists():
                        try:
                            aprobado2 = DistributivoPersona.objects.filter(persona=configuracion[0].aprobado2,
                                                                           denominacionpuesto=configuracion[
                                                                               0].denominacionaprobado2)
                            aprobado3 = DistributivoPersona.objects.filter(persona=configuracion[0].aprobado3,
                                                                           denominacionpuesto=configuracion[
                                                                               0].denominacionaprobado3)
                            form = CapConfiguracionIpecForm(initial={'minasistencia': configuracion[0].minasistencia,
                                                                     'minnota': configuracion[0].minnota,
                                                                     'aprobado2': aprobado2[
                                                                         0].id if aprobado2.exists() else 0,
                                                                     'aprobado3': aprobado3[
                                                                         0].id if aprobado3.exists() else 0})
                            form.editar(aprobado2, aprobado3)
                        except Exception as ex:
                            form = CapConfiguracionIpecForm(initial={'minasistencia': configuracion[0].minasistencia,
                                                                     'minnota': configuracion[0].minnota})
                    else:
                        form = CapConfiguracionIpecForm()
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec/configuracion.html", data)
                except Exception as ex:
                    pass

            elif action == 'configuracionfirma':
                try:
                    data['title'] = u'Configuración de Firmas'
                    curso = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    configuracion = ConfigurarcionMejoraContinua.objects.filter(curso=curso)
                    if configuracion.exists():
                        data['configuraciones'] = configuracion.order_by('orden')
                    form = ConfigurarcionMejoraContinuaForm(initial={'curso': curso})
                    form.deshabilitar()
                    data['action'] = 'configuracionfirma'
                    data['curso'] = curso.id
                    data['periodo'] = int(request.GET['periodo'])
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec/configuracionfirmas.html", data)
                except Exception as ex:
                    pass

            elif action == 'editconfiguracionfirma':
                try:
                    data['title'] = u'Edicion de Firmas'
                    configuracion = ConfigurarcionMejoraContinua.objects.get(pk=int(request.GET['id']))
                    form = ConfigurarcionMejoraContinuaForm(initial={
                        'nombre': configuracion.nombre,
                        'cargo': configuracion.cargo,
                        'orden': configuracion.orden,
                        'firma': configuracion.firma,
                        'curso': configuracion.curso
                    })
                    form.deshabilitar()
                    data['action'] = 'editconfiguracionfirma'
                    data['curso'] = configuracion.id
                    data['periodo'] = int(request.GET['periodo'])
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec/configuracionfirmas.html", data)
                except Exception as ex:
                    pass

            elif action == 'busquedaconcargo':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__() == 2:
                        distributivo = DistributivoPersona.objects.filter(
                            Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1]),
                            estadopuesto__id=PUESTO_ACTIVO_ID, status=True).distinct()[:20]
                    else:
                        distributivo = DistributivoPersona.objects.filter(
                            Q(persona__nombres__contains=q) | Q(persona__apellido1__contains=q) | Q(
                                persona__apellido2__contains=q) | Q(persona__cedula__contains=q)).filter(
                            estadopuesto__id=PUESTO_ACTIVO_ID, status=True)[:20]
                    data = {"result": "ok", "results": [{"id": x.id, "name": (u'%s - %s - %s' % (
                        x.persona.cedula, x.persona.nombre_completo_inverso(), x.denominacionpuesto))} for x in
                                                        distributivo]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass
            # EVENTO PERIODO
            elif action == 'addperiodoevento':
                try:
                    data['title'] = u'Adicionar Evento'
                    periodo = CapPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    data['periodo'] = periodo.id
                    configuracion = CapConfiguracionIpec.objects.all()
                    form = CapEventoPeriodoIpecForm(initial={'periodo': periodo,
                                                             'minasistencia': configuracion[
                                                                 0].minasistencia if configuracion.exists() else 0,
                                                             'minnota': configuracion[
                                                                 0].minnota if configuracion.exists() else 0,
                                                             'aprobado2': (u'%s - %s - %s' % (
                                                                 configuracion[0].aprobado2.cedula,
                                                                 configuracion[0].aprobado2.nombre_completo_inverso(),
                                                                 configuracion[
                                                                     0].denominacionaprobado2)) if configuracion.exists() else '',
                                                             'aprobado3': (u'%s - %s - %s' % (
                                                                 configuracion[0].aprobado3.cedula,
                                                                 configuracion[0].aprobado3.nombre_completo_inverso(),
                                                                 configuracion[
                                                                     0].denominacionaprobado3)) if configuracion.exists() else ''
                                                             })
                    form.editar_grupo()
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec/addperiodoevento.html", data)
                except Exception as ex:
                    pass

            elif action == 'delperiodoevento':
                try:
                    data['title'] = u'Eliminar Evento'
                    data['evento'] = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitacioneventoperiodoipec/delperiodoevento.html", data)
                except Exception as ex:
                    pass

            elif action == 'editperiodoevento':
                try:
                    data['title'] = u'Editar Evento'
                    data['evento'] = evento = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    if evento.tiporubro_id in [None, '', 0]:
                        data['idtipootrorubro'] = idtipootrorubro = 0
                    else:
                        data['idtipootrorubro'] = idtipootrorubro = evento.tiporubro_id
                    responsable = Administrativo.objects.get(persona=evento.responsable)
                    form = CapEventoPeriodoIpecForm(initial={'periodo': evento.periodo,
                                                             'capevento': evento.capevento,
                                                             'tipootrorubro': idtipootrorubro,
                                                             'horas': evento.horas,
                                                             'costo': evento.costo,
                                                             'costoexterno': evento.costoexterno,
                                                             'objetivo': evento.objetivo,
                                                             'observacion': evento.observacion,
                                                             'minasistencia': evento.minasistencia,
                                                             'minnota': evento.minnota,
                                                             'fechainicio': evento.fechainicio,
                                                             'fechafin': evento.fechafin,
                                                             'fechainiinscripcion': evento.fechainicioinscripcion,
                                                             'fechafininscripcion': evento.fechafininscripcion,
                                                             'tipoparticipacion': evento.tipoparticipacion,
                                                             'contextocapacitacion': evento.contextocapacitacion,
                                                             'modalidad': evento.modalidad,
                                                             'tipocertificacion': evento.tipocertificacion,
                                                             'tipocapacitacion': evento.tipocapacitacion,
                                                             'visualizar': evento.visualizar,
                                                             'publicarinscripcion': evento.publicarinscripcion,
                                                             'enfoque': evento.enfoque,
                                                             'cupo': evento.cupo,
                                                             'contenido': evento.contenido,
                                                             'modeloevaludativoindividual': evento.modeloevaludativoindividual,
                                                             'notificarubro': evento.notificarubro,
                                                             'seguimientograduado': evento.seguimientograduado,
                                                             'mes': evento.mes,
                                                             'responsable': responsable.id,
                                                             'fechacertificado': evento.fechacertificado,
                                                             'fechamaxpago': evento.fechamaxpago,
                                                             'areaconocimiento': evento.areaconocimiento,
                                                             'aprobado2': (u'%s - %s - %s' % (evento.aprobado2.cedula,
                                                                                              evento.aprobado2.nombre_completo_inverso(),
                                                                                              evento.denominacionaprobado2)) if evento.aprobado2 else '',
                                                             'aprobado3': (u'%s - %s - %s' % (evento.aprobado3.cedula,
                                                                                              evento.aprobado3.nombre_completo_inverso(),
                                                                                              evento.denominacionaprobado3)) if evento.aprobado3 else '',
                                                             'aula': evento.aula,
                                                             'envionotaemail': evento.envionotaemail})
                    form.editar_grupo()
                    form.editar_responsable(responsable)
                    if not evento.periodo.esta_activo_periodo:
                        data['permite_modificar'] = False
                    # Si el evento tiene rubro generado no se permite modificar el costo
                    # data['puede_editar_valorrubro'] = puede_editar_valorrubro = evento.puede_modificar_valorrubro_evento()
                    # if not puede_editar_valorrubro:
                    #     form.editar_rubro_deshabilitar()
                    data['form'] = form
                    data['logoaval'] = evento.archivo
                    data['banner'] = evento.banner
                    return render(request, "adm_capacitacioneventoperiodoipec/editperiodoevento.html", data)
                except Exception as ex:
                    messages.error(request, f'Error {ex} on line {sys.exc_info()[-1].tb_lineno}')

            elif action == 'facturatotal':
                try:
                    data['title'] = u'Factura Total'
                    data['evento'] = evento = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    if evento.capeventoperiodofacturatotalipec_set.filter(status=True):
                        facturatotal = evento.capeventoperiodofacturatotalipec_set.filter(status=True)[0]
                        form = CapEventoPeriodoIpecFacturaTotalForm(initial={'subtotal': facturatotal.subtotal,
                                                                             'iva': facturatotal.iva,
                                                                             'total': facturatotal.total})
                    else:
                        form = CapEventoPeriodoIpecFacturaTotalForm(initial={'subtotal': 0,
                                                                             'iva': 0,
                                                                             'total': 0})
                    # form.deshabilitar()
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec/facturatotal.html", data)
                except Exception as ex:
                    pass

            elif action == 'busqueda':
                try:
                    q = request.GET['q'].upper().strip()
                    if ' ' in q:
                        s = q.split(" ")
                        distributivo = DistributivoPersona.objects.filter(
                            Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1]),
                            estadopuesto__id=PUESTO_ACTIVO_ID, status=True).distinct()[:20]
                    distributivo = DistributivoPersona.objects.filter(
                        Q(persona__nombres__contains=q) | Q(persona__apellido1__contains=q) | Q(
                            persona__apellido2__contains=q) | Q(persona__cedula__contains=q)).filter(
                        estadopuesto__id=PUESTO_ACTIVO_ID, status=True)[:20]
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_repr()} for x in distributivo]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'verdetalleevento':
                try:
                    data = {}
                    data['evento'] = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    template = get_template("adm_capacitacioneventoperiodoipec/detalleevento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'verdetalle':
                try:
                    data = {}
                    data['inscrito'] = inscrito = CapInscritoIpec.objects.get(pk=request.GET['idi'])
                    rubrostodos = CapEventoPeriodoIpec.objects.filter(status=True)
                    # rubrostodos = CapEventoPeriodoIpec.objects.values_list('tiporubro_id').filter(status=True)
                    # rubrostodos = CapEventoPeriodoIpec.objects.values_list('tiporubro_id').filter(periodo=inscrito.capeventoperiodo.periodo, status=True)
                    if inscrito.capeventoperiodo.instructor_principal():
                        data[
                            'modelos'] = inscrito.capeventoperiodo.instructor_principal().modelo_calificacion_abreviado(
                            inscrito.capeventoperiodo)
                    data['instructores'] = inscrito.capeventoperiodo.capinstructoripec_set.filter(status=True)
                    # data['rubros'] = Rubro.objects.filter(persona=inscrito.participante,capeventoperiodoipec=inscrito.capeventoperiodo, status=True)
                    data['rubros'] = Rubro.objects.filter(persona=inscrito.participante,
                                                          tipo_id__in=rubrostodos.values_list('tiporubro_id'),
                                                          status=True)
                    data['rubroscoinciden'] = Rubro.objects.filter(persona=inscrito.participante,
                                                                   capeventoperiodoipec=inscrito.capeventoperiodo,
                                                                   status=True)
                    template = get_template("adm_capacitacioneventoperiodoipec/detalleinscrito.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'planificacion':
                try:
                    data['title'] = u'Planificación de Eventos'
                    search = None
                    ids = None
                    data['periodo'] = periodo = CapPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            evento = CapEventoPeriodoIpec.objects.filter((Q(capevento__nombre__icontains=search) |
                                                                          Q(enfoque__nombre__icontains=search)) &
                                                                         Q(periodo=periodo) &
                                                                         Q(status=True)).distinct().order_by(
                                'fechainicio')
                        else:
                            evento = CapEventoPeriodoIpec.objects.filter(
                                (Q(capevento__nombre__icontains=search) | Q(enfoque__nombre__in=ss)) &
                                Q(periodo=periodo) &
                                Q(status=True)).distinct().order_by('fechainicio')
                    else:
                        evento = CapEventoPeriodoIpec.objects.filter(periodo=periodo, status=True).order_by(
                            'fechainicio')
                    paging = MiPaginador(evento, 10)
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
                    data['evento'] = page.object_list
                    form = SeleccionarInstructorIpecForm()
                    form.seleccionar()
                    data['form'] = form
                    data['meses'] = MESES_CHOICES
                    # reportes
                    data['reporte_0'] = obtener_reporte('inscritos_capacitacion_ipec')
                    data['reporte_1'] = obtener_reporte('inscritos_capacitacion_ipec2')
                    data['estado_cancelado'] = True
                    return render(request, "adm_capacitacioneventoperiodoipec/viewperiodoevento.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            # INSCRITOS
            elif action == 'addinscribir':
                try:
                    data['title'] = u'Inscribir'
                    data['form'] = CapInscribirIpecForm()
                    data['eventoperiodo'] = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitacioneventoperiodoipec/addinscribir.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinscribir_modal':
                try:

                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = CapEventoPeriodoIpec.objects.get(pk=id)
                    form = CapInscribirIpecForm2()
                    form.fields['participante'].queryset = Persona.objects.none()
                    data['form2'] = form
                    template = get_template("adm_capacitacioneventoperiodoipec/modal/formmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})

                except Exception as ex:
                    pass

            elif action == 'generarrubrodiferido':
                try:
                    data['id'] = id = request.GET['id']
                    data['action'] = 'generarrubrodiferido'
                    data['filtro'] = filtro = CapInscritoIpec.objects.get(pk=id)
                    hoy = datetime.now().date()
                    form = GenerarRubroDiferidoForm(initial={'participante': filtro.participante,
                                                             'valor': filtro.capeventoperiodo.costo,
                                                             'fechavence': hoy})
                    data['form2'] = form
                    template = get_template("adm_capacitacioneventoperiodoipec/modal/diferidoedcon.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'buscarinscritos':
                try:
                    id = request.GET['id']
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    carrera = ""

                    querybase = Persona.objects.filter(status=True).order_by('apellido1')
                    if len(s) == 1:
                        querybase = querybase.filter((Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(cedula__icontains=q) |  Q(apellido2__icontains=q) | Q(cedula__contains=q)), Q(status=True)).distinct()[:15]
                    elif len(s) == 2:
                        querybase = querybase.filter((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) |
                                                       (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) |
                                                       (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1]))).filter(status=True).distinct()[:15]
                    else:
                        querybase = querybase.filter((Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(apellido2__contains=s[2])) |
                                                       (Q(nombres__contains=s[0]) & Q(nombres__contains=s[1]) & Q(apellido1__contains=s[2]))).filter(status=True).distinct()[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {} | {}".format(x.cedula, x.nombre_completo(), x.nombres)} for x in querybase]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass




            elif action == 'inscripcioncursoposgrado':
                try:
                    data['title'] = u'Registrar certificado'
                    hoy = datetime.now().date()
                    cursos = None
                    listacur = []
                    if CapEventoPeriodoIpec.objects.filter(fechainicioinscripcion__lte=hoy,
                                                           fechafininscripcion__gte=hoy, publicarinscripcion=True,
                                                           status=True).exists():
                        cursos = CapEventoPeriodoIpec.objects.filter(fechainicioinscripcion__lte=hoy,
                                                                     fechafininscripcion__gte=hoy,
                                                                     publicarinscripcion=True, status=True)
                        for cur in cursos:
                            if cur.cupo > cur.capinscritoipec_set.filter(status=True).count():
                                listacur.append(cur.id)
                        if listacur:
                            cursos = CapEventoPeriodoIpec.objects.filter(pk__in=listacur)
                        else:
                            cursos = None
                        if not TipoOtroRubro.objects.filter(
                                pk__in=cursos.values_list('tiporubro_id').filter(status=True)).exists():
                            cursos = None
                    data['cursos'] = cursos
                    data['listaprovinvias'] = Provincia.objects.filter(pais_id=1, status=True).order_by('nombre')
                    return render(request, "inscripcionescursos/inscripcionescursos.html", data)
                except Exception as ex:
                    pass


            elif action == 'addregistrar':
                try:
                    data['title'] = u'Registrar datos de la inscripción'
                    data['eventoperiodo'] = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    data['form'] = CapInscribirPersonaIpecForm()
                    return render(request, "adm_capacitacioneventoperiodoipec/addregistrardatos.html", data)
                except Exception as ex:
                    pass

            elif action == 'inscritoaplicagratuidad':
                try:
                    idinscrito = request.GET['idinscrito']
                    ideventoperiodo = request.GET['ideventoperiodo']
                    estadogratuidad = str(request.GET['estadogratuidad'])
                    identificadorgratuidad = 0
                    actualizar_aplicagratuidad = CapInscritoIpec.objects.get(id=idinscrito, capeventoperiodo_id=ideventoperiodo)
                    if estadogratuidad == 'true':
                        actualizar_aplicagratuidad.aplicagratuidad = 1
                        identificadorgratuidad = 1
                    if estadogratuidad == 'false':
                        actualizar_aplicagratuidad.aplicagratuidad = 2
                    actualizar_aplicagratuidad.save(request)
                    log(u'Actualiza aplica gratuidad %s - %s' % (persona, actualizar_aplicagratuidad), request, "edit")
                    return JsonResponse({"result":True,"identificadorgratuidad":identificadorgratuidad})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje":u'Error al momento de actualizar'})

            elif action == 'inscritos':
                try:
                    data['title'] = u'Inscritos'
                    ids = None
                    url_vars = ''
                    filtro = Q(capeventoperiodo=int(request.GET['id']), status=True)
                    search = request.GET.get('s', None)
                    ide = request.GET.get('ide', '0')
                    eventoperiodo = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    if search:
                        data['search'] = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(participante__nombres__icontains=search) |
                                Q(participante__apellido1__icontains=search) |
                                Q(participante__apellido2__icontains=search) |
                                Q(participante__cedula__icontains=search) |
                                Q(participante__pasaporte__icontains=search))
                            url_vars += "&s={}".format(search)

                        else:
                            filtro = filtro & ((Q(participante__apellido1__icontains=ss[0]) & Q(participante__apellido2__icontains=ss[1])) |
                                               (Q(participante__nombres__icontains=ss[0]) & Q(participante__nombres__icontains=ss[1])))

                            url_vars += "&s={}".format(ss)

                    if int(ide):
                        if int(ide) == 1:
                            filtro = filtro & (Q(formapago=1))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"
                        elif int(ide) == 2:
                            filtro = filtro & (Q(formapago=2))
                            data['ide'] = int(ide)
                            url_vars += f"&ide={ide}"

                    inscrito = CapInscritoIpec.objects.filter(filtro).distinct().order_by('participante__apellido1',
                                                                                          'participante__apellido2',
                                                                                          'participante__nombres')
                    paging = MiPaginador(inscrito, 50)
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
                    data['persona'] = persona
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['inscritos'] = page.object_list
                    data["url_vars"] = url_vars
                    data['eventoperiodo'] = eventoperiodo
                    data['periodo_ipec'] = eventoperiodo.fechainicio.year
                    # print('periodo_ipec año', str(data['periodo_ipec']))
                    data['sagest_capperiodoipec'] = eventoperiodo.periodo.nombre
                    data['reporte_2'] = obtener_reporte('inscritoscursoeducacioncontinua')
                    costo = False
                    data['costoext'] = eventoperiodo.costoexterno
                    data['costoint'] = eventoperiodo.costo
                    if eventoperiodo.costo==0 and eventoperiodo.costoexterno==0:
                        costo=True
                    data['costo'] = costo
                    return render(request, "adm_capacitacioneventoperiodoipec/inscritos.html", data)
                except Exception as ex:
                    messages.error(request, ex)


            elif action == 'consultapagoepunemi':
                try:
                    rubros = Rubro.objects.filter(persona__id=int(request.GET['id']),
                                                 capeventoperiodoipec__id=int(request.GET['capeventoperiodo']),
                                                 status=True).exclude(pago__factura__valida=False).order_by('cuota')
                    data['rubros'] = rubros
                    template = get_template('adm_capacitacioneventoperiodoipec/pagoepunemi.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            elif action == 'inscritos_all':
                try:
                    data['title'] = u'Cursos Inscritos'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            inscrito = CapInscritoIpec.objects.filter(Q(participante__nombres__icontains=search) |
                                                                      Q(participante__apellido1__icontains=search) |
                                                                      Q(participante__apellido2__icontains=search) |
                                                                      Q(participante__cedula__icontains=search) |
                                                                      Q(
                                                                          participante__pasaporte__icontains=search)).distinct().order_by(
                                'participante__apellido1', 'participante__apellido2', 'participante__nombres')
                        else:
                            inscrito = CapInscritoIpec.objects.filter((Q(participante__apellido1__icontains=ss[0]) &
                                                                       Q(participante__apellido2__icontains=ss[1])) |
                                                                      (Q(participante__nombres__icontains=ss[0]) &
                                                                       Q(participante__nombres__icontains=ss[
                                                                           1]))).distinct().order_by(
                                'participante__apellido1', 'participante__apellido2', 'participante__nombres')
                    else:
                        inscrito = CapInscritoIpec.objects.filter(status=True).distinct().order_by(
                            'participante__apellido1', 'participante__apellido2', 'participante__nombres')
                    paging = MiPaginador(inscrito, 20)
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
                    data['inscritos'] = page.object_list
                    return render(request, "adm_capacitacioneventoperiodoipec/inscritos_all.html", data)
                except Exception as ex:
                    pass

            elif action == 'delinscrito':
                try:
                    data['title'] = u'Eliminar Inscrito'
                    data['inscrito'] = CapInscritoIpec.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitacioneventoperiodoipec/delinscrito.html", data)
                except Exception as ex:
                    pass
            # INSTRUCTOR
            elif action == 'busquedainstructor':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if s.__len__() == 2:
                        persona = Persona.objects.filter(apellido1__icontains=s[0], apellido2__icontains=s[1],
                                                         real=True).exclude(pk__in=lista).distinct()[:15]
                    else:
                        persona = Persona.objects.filter(Q(real=True) & (
                                Q(nombres__contains=s[0]) | Q(apellido1__contains=s[0]) | Q(
                            apellido2__contains=s[0]) | Q(cedula__contains=s[0]))).exclude(pk__in=lista).distinct()[
                                  :15]
                    data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_repr()} for x in persona]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'addinstructor':
                try:
                    data['title'] = u'Adicionar Instructor'
                    data['form'] = CapInstructorIpecForm()
                    # lista = CapInstructorIpec.objects.values_list('instructor_id').filter(capeventoperiodo_id=int(request.GET['id']), status=True)
                    data['eventoperiodo'] = request.GET['id']
                    return render(request, "adm_capacitacioneventoperiodoipec/addinstructor.html", data)
                except Exception as ex:
                    pass

            elif action == 'delinstructor':
                try:
                    data['title'] = u'Eliminar Instructor'
                    data['instructor'] = CapInstructorIpec.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitacioneventoperiodoipec/delinstructor.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinstructor':
                try:
                    data['title'] = u'Editar Instructor'
                    data['instructor'] = instructor = CapInstructorIpec.objects.get(pk=int(request.GET['id']))
                    lista = CapInstructorIpec.objects.values_list('instructor_id').filter(
                        capeventoperiodo=instructor.capeventoperiodo, status=True).exclude(pk=instructor.id)
                    # form = CapInstructorIpecForm(initial={'instructor': instructor.instructor_id,
                    #                                       'instructorprincipal': instructor.instructorprincipal})
                    form = CapInstructorIpecForm(initial=model_to_dict(instructor))
                    data['periodo'] = instructor.capeventoperiodo.periodo_id
                    form.editar(instructor)
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec/editinstructor.html", data)
                except Exception as ex:
                    pass

            elif action == 'instructor':
                try:
                    data['title'] = u'Instructor'
                    data['instructor'] = CapInstructorIpec.objects.filter(capeventoperiodo=int(request.GET['id']),
                                                                          status=True)
                    data['eventoperiodo'] = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']), status=True)
                    return render(request, "adm_capacitacioneventoperiodoipec/viewinstructor.html", data)
                except Exception as ex:
                    pass

            if action == 'resetear':
                try:
                    puede_realizar_accion(request, 'sga.puede_resetear_clave')
                    data['title'] = u'Resetear clave del usuario'
                    instructor = CapInstructorIpec.objects.get(pk=request.GET['id'])
                    data['instructor'] = instructor
                    data['insid'] = request.GET['insid']
                    return render(request, "adm_capacitacioneventoperiodoipec/resetear.html", data)
                except Exception as ex:
                    pass

            elif action == 'addnuevoinstructor':
                try:
                    data['title'] = u'Registrar datos del instructor'
                    data['eventoperiodo'] = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    form = CapInscribirPersonaIpecForm()
                    form.adicionar_instructor()
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec/addnuevoinstructor.html", data)
                except Exception as ex:
                    pass

            elif action == 'editpersona':
                try:
                    if int(request.GET['tipo']) == 1:
                        data['title'] = u'Editar datos del instructor'
                        data['cap'] = cap = CapInstructorIpec.objects.get(pk=int(request.GET['id']))
                        data['per'] = cap.instructor
                        initial = model_to_dict(cap.instructor)
                        form = CapInscribirPersonaIpecForm(initial=initial)
                        form.adicionar_instructor()
                    else:
                        data['title'] = u'Editar datos del inscrito'
                        data['cap'] = cap = CapInscritoIpec.objects.get(pk=int(request.GET['id']))
                        data['per'] = cap.participante
                        initial = model_to_dict(cap.participante)
                        form = CapInscribirPersonaIpecForm(initial=initial)
                    data['tipo'] = int(request.GET['tipo'])
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec/editpersona.html", data)
                except Exception as ex:
                    pass
            # HORARIOS
            elif action == 'addclase':
                try:
                    data['title'] = u'Adicionar horario'
                    evento = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['cepid']))
                    form = CapClaseIpecForm(initial={'capeventoperiodo': evento,
                                                     'turno': CapTurnoIpec.objects.get(pk=request.GET['turno']),
                                                     'dia': request.GET['dia'],
                                                     'fechainicio': evento.fechainicio,
                                                     'fechafin': evento.fechafin})
                    data['cepid'] = evento.id
                    form.editar_grupo()
                    form.cargar_instructores(evento)
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec/addclase.html", data)
                except Exception as ex:
                    pass

            elif action == 'delclase':
                try:
                    data['title'] = u'Eliminar horario'
                    data['clase'] = clase = CapClaseIpec.objects.get(pk=int(request.GET['cid']))
                    data['eventoperiodo'] = clase.capeventoperiodo.id
                    return render(request, "adm_capacitacioneventoperiodoipec/delclase.html", data)
                except Exception as ex:
                    pass

            elif action == 'editclase':
                try:
                    data['title'] = u'Editar horario'
                    clase = CapClaseIpec.objects.get(pk=int(request.GET['cid']))
                    form = CapClaseIpecForm(initial={'capeventoperiodo': clase.capeventoperiodo,
                                                     'turno': clase.turno,
                                                     'fechainicio': clase.fechainicio,
                                                     'fechafin': clase.fechafin,
                                                     'instructor': clase.instructor,
                                                     'dia': clase.dia})
                    data['cepid'] = clase.capeventoperiodo.id
                    data['claseid'] = clase.id
                    form.editar_grupo()
                    form.editar_turno()
                    if clase.capcabeceraasistenciaipec_set.filter(status=True).exists():
                        form.editar_instructor()
                    form.cargar_instructores(clase.capeventoperiodo)
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec/editclase.html", data)
                except Exception as ex:
                    pass

            elif action == 'horario':
                try:
                    data['title'] = u'Horarios'
                    data['capeventoperiodo'] = None
                    data['eventoperiodoid'] = None
                    data['semana'] = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']
                    evento = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    data['activo'] = datetime.now().date() <= evento.fechafin
                    data['turnos'] = CapTurnoIpec.objects.filter(status=True)
                    data['capeventoperiodo'] = evento
                    data['eventoperiodoid'] = evento.id
                    return render(request, "adm_capacitacioneventoperiodoipec/horario.html", data)
                except Exception as ex:
                    pass
            # ASISTENCIA
            elif action == 'asistencia':
                try:
                    data['title'] = u'Horarios'
                    dia = 0
                    clase_activa = False
                    capeventoperiodo = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    semana = [[0, 'Hoy'], [1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'],
                              [6, 'Sabado'], [7, 'Domingo'], [8, 'Todos']]
                    if 'd' in request.GET:
                        dia = int(request.GET['d'])
                        if dia == 8:
                            data['dias'] = {1: 'Lunes', 2: 'Martes', 3: 'Miercoles', 4: 'Jueves', 5: 'Viernes',
                                            6: 'Sabado', 7: 'Domingo'}
                        elif dia > 0 and dia < 8:
                            data['dias'] = {DIAS_CHOICES[dia - 1][0]: DIAS_CHOICES[dia - 1][1]}
                    else:
                        clase_activa = True
                        data['fecha_hoy'] = datetime.now().date()
                        data['clases_hoy'] = capeventoperiodo.clases_activas()
                        data['dias'] = {
                            DIAS_CHOICES[date.today().weekday()][0]: DIAS_CHOICES[date.today().weekday()][1]}
                    data['select_dia'] = dia
                    data['capeventoperiodo'] = capeventoperiodo
                    data['clase_activa'] = clase_activa
                    data['dia_list'] = semana
                    form = CapAsistenciaIpecForm()
                    form.adicionar(capeventoperiodo)
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec/asistencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'addasistencia':
                try:
                    revisar = False
                    data['title'] = u'Asistencia'
                    data['cabeceraasistencia'] = asistencia = CapCabeceraAsistenciaIpec.objects.get(
                        pk=int(request.GET['id']))
                    data['clase'] = asistencia.clase
                    data['listadoinscritos'] = asistencia.clase.capeventoperiodo.inscritos()
                    if 'm' in request.GET:
                        revisar = True
                    data['revisar'] = revisar
                    return render(request, "adm_capacitacioneventoperiodoipec/addasistencia.html", data)
                except Exception as ex:
                    pass
            # NOTAS
            elif action == 'delmodelonota':
                try:
                    data['title'] = u'Eliminar modelo de nota'
                    data['modelonota'] = modelonotas = CapNotaIpec.objects.get(pk=int(request.GET['id']))
                    data['evento'] = modelonotas.instructor.capeventoperiodo
                    return render(request, "adm_capacitacioneventoperiodoipec/delmodelonotas.html", data)
                except Exception as ex:
                    pass

            elif action == 'notas':
                try:
                    data['title'] = u'Notas'
                    data['evento'] = evento = CapEventoPeriodoIpec.objects.get(id=int(request.GET['id']), status=True)
                    data['instructores'] = evento.capinstructoripec_set.filter(status=True,
                                                                               instructorprincipal=True).order_by(
                        'instructor__apellido1', 'instructor__apellido2', 'instructor__nombres')
                    form = CapNotaIpecForm()
                    form.deshabilitar_profesor()
                    data['form'] = form
                    if not evento.modeloevaludativoindividual:
                        data['modeloevaluativogeneral'] = CapModeloEvaluativoGeneral.objects.filter(
                            status=True).order_by('orden')
                    return render(request, 'adm_capacitacioneventoperiodoipec/viewnota.html', data)
                except Exception as ex:
                    pass

            elif action == 'calificar':
                try:
                    data['title'] = u'Calificar'
                    data['tarea'] = tarea = CapNotaIpec.objects.get(pk=int(request.GET['id']))
                    data['listadoinscritos'] = tarea.capdetallenotaipec_set.filter(status=True)
                    return render(request, 'adm_capacitacioneventoperiodoipec/calificar.html', data)
                except Exception as ex:
                    pass

            elif action == 'calificageneral':
                try:
                    data['title'] = u'Calificación General'
                    data['instructor'] = instructor = CapInstructorIpec.objects.get(pk=int(request.GET['id']),
                                                                                    status=True)
                    data['tareas'] = tarea = CapNotaIpec.objects.filter(instructor=instructor)
                    data['listadoinscritos'] = instructor.capeventoperiodo.inscritos()
                    return render(request, 'adm_capacitacioneventoperiodoipec/calificargeneral.html', data)
                except Exception as ex:
                    pass

            elif action == 'descargarnotas':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_inscritos_notas' + random.randint(1,
                                                                                                                      10000).__str__() + '.xls'
                    row_num = 1
                    intructor = CapInstructorIpec.objects.get(pk=int(request.GET['idi']))
                    eventoperiodo = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['idp']))
                    totalinscritos = eventoperiodo.capinscritoipec_set.filter(status=True)
                    modelos = intructor.modelo_calificacion_abreviado(intructor.capeventoperiodo)

                    columns = [
                        (u"N.", 2000),
                        (u"CEDULA", 4000),
                        (u"NOMBRES", 10000)
                    ]
                    for m in modelos:
                        columns.append((u'%s' % m[1], 4000))
                    columns.append(('Nota Final', 4000))
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    for lista in totalinscritos:
                        row_num += 1
                        campo2 = lista.participante.identificacion()
                        campo3 = lista.participante.nombre_completo_inverso()
                        ws.write(row_num, 0, row_num, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        col = 3
                        total = 0
                        for m in modelos:
                            nota = lista.mi_nota_individual(m[0], eventoperiodo.id)
                            # total += nota if nota else 0
                            notaalumno = 0
                            if nota:
                                if nota.nota:
                                    total += nota.nota
                                    notaalumno = nota.nota
                                else:
                                    total += 0
                            else:
                                total += 0
                            ws.write(row_num, col, notaalumno, font_style2)
                            col += 1
                        ws.write(row_num, col, total, font_style2)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass
            # MODELO EVALUATIVO
            elif action == 'addmodelo':
                try:
                    data['title'] = u'Adicionar Modelo Evaluativo'
                    data['form'] = CapModeloEvaluativoTareaIpecForm()
                    return render(request, "adm_capacitacioneventoperiodoipec/addmodeloevaluativo.html", data)
                except Exception as ex:
                    pass

            elif action == 'delmodelo':
                try:
                    data['title'] = u'Eliminar Modelo Evaluativo'
                    data['evaluativo'] = CapModeloEvaluativoTareaIpec.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitacioneventoperiodoipec/delmodeloevaluativo.html", data)
                except Exception as ex:
                    pass

            elif action == 'delmodelogeneral':
                try:
                    data['title'] = u'Eliminar Modelo Evaluativo General'
                    data['evaluativo'] = CapModeloEvaluativoGeneral.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capacitacioneventoperiodoipec/delmodeloevaluativoevaluativo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editmodelo':
                try:
                    data['title'] = u'Editar Modelo Evaluativo'
                    data['modelo'] = modelo = CapModeloEvaluativoTareaIpec.objects.get(pk=int(request.GET['id']))
                    form = CapModeloEvaluativoTareaIpecForm(initial={'nombre': modelo.nombre,
                                                                     'principal': modelo.principal,
                                                                     'notaminima': modelo.notaminima,
                                                                     'notamaxima': modelo.notamaxima,
                                                                     'evaluacion': modelo.evaluacion})
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec/editmodeloevaluativo.html", data)
                except Exception as ex:
                    pass

            elif action == 'modelo':
                try:
                    data['title'] = u'Modelo Evaluativo'
                    data['modelos'] = CapModeloEvaluativoTareaIpec.objects.filter(status=True).order_by(
                        'fecha_creacion')
                    return render(request, 'adm_capacitacioneventoperiodoipec/viewmodeloevaluativo.html', data)
                except Exception as ex:
                    pass

            elif action == 'modelogeneral':
                try:
                    data['title'] = u'Modelo Evaluativo General'
                    data['modelos'] = CapModeloEvaluativoGeneral.objects.filter(status=True).order_by('orden')
                    return render(request, 'adm_capacitacioneventoperiodoipec/viewmodeloevaluativogeneral.html', data)
                except Exception as ex:
                    pass

            elif action == 'addmodelogeneral':
                try:
                    filtro = CapModeloEvaluativoGeneral.objects.filter(status=True)
                    form = ModeloEvaluativoGeneralForm()
                    form.fields['modelo'].queryset = CapModeloEvaluativoTareaIpec.objects.filter(status=True).exclude(
                        id__in=filtro.values_list('modelo__id', flat=True)).order_by('nombre')
                    form.fields['orden'].initial = filtro.count() + 1
                    data['form2'] = form
                    template = get_template("adm_capacitacioneventoperiodoipec/modal/formmodeloevaluativoconfi.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editmodelogeneral':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = CapModeloEvaluativoGeneral.objects.get(pk=request.GET['id'])
                    data['form2'] = ModeloEvaluativoGeneralForm(initial=model_to_dict(filtro))
                    template = get_template("adm_capacitacioneventoperiodoipec/modal/formmodeloevaluativoconfi.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'confimodelogeneral':
                try:
                    data['id'] = request.GET['id']
                    data['modeloevaluativo'] = modelos = CapModeloEvaluativoGeneral.objects.filter(
                        status=True).order_by('orden')
                    data['instructor'] = instructor = CapInstructorIpec.objects.get(pk=int(request.GET['id']))
                    if instructor.capnotaipec_set.filter(status=True).count() >= modelos.count():
                        return JsonResponse({"result": False, 'mensaje': 'Instructor ya cuenta con modelo evaluativo'})
                    data['instructorname'] = instructor.instructor.nombre_completo_inverso()
                    template = get_template("adm_capacitacioneventoperiodoipec/modal/confirmarmodelo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'cambiarinstructorprincipal':
                try:
                    data['title'] = u'Cambiar intructor principal'
                    data['instructor'] = CapInstructorIpec.objects.get(status=True, pk=int(request.GET['id']))
                    return render(request, 'adm_capacitacioneventoperiodoipec/cambiarinstructorprincipal.html', data)
                except Exception as ex:
                    pass

            elif action == 'crearperfil':
                try:
                    data['title'] = u'Crear perfil intructor'
                    data['instructor'] = CapInstructorIpec.objects.get(status=True, pk=int(request.GET['id']))
                    return render(request, 'adm_capacitacioneventoperiodoipec/crearperfil.html', data)
                except Exception as ex:
                    pass

            elif action == 'instructores':
                try:
                    data['title'] = u'Intructores'
                    search = None
                    ids = None
                    instructores = CapInstructorIpec.objects.filter(status=True).distinct('instructor')
                    if 'id' in request.GET:
                        ids = int(request.GET['id'])
                        instructores = instructores.filter(instructor_id=int(request.GET['id']))
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) == 1:
                            instructores = instructores.filter(Q(instructor__nombres__icontains=search) | Q(
                                instructor__apellido1__icontains=search) | Q(
                                instructor__apellido2__icontains=search) | Q(instructor__cedula__icontains=search))
                        elif len(ss) == 2:
                            instructores = instructores.filter(
                                (Q(instructor__nombres__icontains=ss[0]) & Q(instructor__nombres__icontains=ss[1])) | (
                                        Q(instructor__apellido1__icontains=ss[0]) & Q(
                                    instructor__apellido2__icontains=ss[1])))
                    paging = MiPaginador(instructores, 20)
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
                    data['ids'] = ids if ids else ""
                    data['search'] = search if search else ""
                    data['instructores'] = page.object_list
                    return render(request, 'adm_capacitacioneventoperiodoipec/instructores.html', data)
                except Exception as ex:
                    pass

            elif action == 'editinscrito':
                try:
                    # puede_realizar_accion(request, 'sga.puede_modificar_administrativos')
                    data['title'] = u'Editar Inscrito'
                    data['inscrito'] = inscrito = CapInscritoIpec.objects.get(pk=request.GET['id'])
                    form = InscritoEventoIpecForm(initial={'nombres': inscrito.participante.nombres,
                                                           'apellido1': inscrito.participante.apellido1,
                                                           'apellido2': inscrito.participante.apellido2,
                                                           'cedula': inscrito.participante.cedula,
                                                           'sexo': inscrito.participante.sexo,
                                                           'pasaporte': inscrito.participante.pasaporte,
                                                           'nacimiento': inscrito.participante.nacimiento,
                                                           'pais': inscrito.participante.pais,
                                                           'provincia': inscrito.participante.provincia,
                                                           'canton': inscrito.participante.canton,
                                                           'parroquia': inscrito.participante.parroquia,
                                                           'sector': inscrito.participante.sector,
                                                           'direccion': inscrito.participante.direccion,
                                                           'direccion2': inscrito.participante.direccion2,
                                                           'num_direccion': inscrito.participante.num_direccion,
                                                           'telefono': inscrito.participante.telefono,
                                                           'telefono_conv': inscrito.participante.telefono_conv,
                                                           'email': inscrito.participante.email})
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec/editinscrito.html", data)
                except Exception as ex:
                    pass

            elif action == 'activardesactivarperfil':
                try:
                    s = ''
                    if 's' in request.GET:
                        s = request.GET['s']
                    data['s'] = s
                    if CapInstructorIpec.objects.filter(instructor_id=int(request.GET['id'])).exists():
                        if CapInstructorIpec.objects.filter(instructor_id=int(request.GET['id']), activo=True).exists():
                            instructor = \
                                CapInstructorIpec.objects.filter(instructor_id=int(request.GET['id']), activo=True,
                                                                 status=True)[0]
                        else:
                            instructor = CapInstructorIpec.objects.filter(instructor_id=int(request.GET['id']),
                                                                          instructorprincipal=True)[0]
                        data['instructor'] = instructor
                        data[
                            'title'] = u'Activar perfil de usuario' if instructor.estado_perfil() else u'Desactivar perfil de usuario'
                        return render(request, "adm_capacitacioneventoperiodoipec/activardesactivarperfil.html", data)
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})
                except Exception as ex:
                    pass

            elif action == 'descargarinscritos':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    # ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_inscritos' + random.randint(1,
                                                                                                                10000).__str__() + '.xls'
                    row_num = 0
                    columns = [
                        (u"N.", 2000),
                        (u"CEDULA", 4000),
                        (u"NOMBRES", 6000),
                        (u"EMAIL PERSONAL", 6000),
                        (u"EMAIL INSTITUCIONAL", 6000),
                        (u"CANCELADO", 6000),
                        (u"TELEFONO CELULAR", 6000),
                        (u"TELEFONO CONVENCIONAL", 6000),
                        (u"VALOR PAGADO", 3000),
                        (u"VALOR CURSO", 3000),
                        (u"CERTIFICADO EMAIL", 3000),
                        (u"CALIFICACIÓN", 3000),
                        (u"ESTADO", 3000),
                        (u"FACULTAD", 3000),
                        (u"CARRERA", 3000),
                        (u"MODULO", 3000),
                        (u"FORMA PAGO", 4000),
                        (u"FECHA DE INSCRIPCIÓN", 4000),
                        (u"USUARIO", 4000),
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    eventoperiodo = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    totalinscritos = eventoperiodo.capinscritoipec_set.filter(status=True)
                    row_num = 0
                    for lista in totalinscritos:
                        insc = Inscripcion.objects.filter(persona__id=lista.participante.id, status=True).values_list(
                            'coordinacion__nombre', flat=True).exclude(coordinacion_id=7)
                        carr = Inscripcion.objects.values_list('carrera__nombre', flat=True).filter(
                            persona__id=lista.participante.id, status=True).exclude(coordinacion_id=7)
                        reco = RecordAcademico.objects.values_list('asignatura__nombre', 'creditos').filter(
                            inscripcion__id=lista.id, status=True, asignatura__modulo=True, aprobada = True).exclude(
                            asignatura__nombre__icontains='INGL')
                        if not insc:
                            insc = Inscripcion.objects.filter(persona__id=lista.participante.id,
                                                              status=True).values_list(
                                'coordinacion__nombre', flat=True).exclude(coordinacion_id = 7)
                        if not carr:
                            carr = Inscripcion.objects.values_list('carrera__nombre', flat=True).filter(
                                persona__id=lista.participante.id, status=True).exclude(coordinacion_id = 7)
                        row_num += 1
                        cancelado = 'NO'
                        certificadoemail = 'NO'
                        campo6 = ''
                        campo7 = 0
                        if lista.emailnotificado:
                            certificadoemail = 'SI'
                        if lista.participante.cedula:
                            campo2 = lista.participante.cedula
                        else:
                            campo2 = lista.participante.pasaporte
                        campo3 = lista.participante.apellido1 + ' ' + lista.participante.apellido2 + ' ' + lista.participante.nombres
                        if lista.capeventoperiodo.costo == 0 and lista.capeventoperiodo.costoexterno == 0:
                            cancelado = 'SIN COSTO'
                        else:
                            if lista.existerubrocurso():
                                if lista.pagorubrocurso_2():
                                    cancelado = 'SI'
                                else:
                                    cancelado = 'NO'
                            else:
                                cancelado = 'FALTA CONFIGURAR RUBRO'
                            # if lista.personalunemi:
                            #     if lista.total_pagado_rubro()==lista.capeventoperiodo.costo:
                            #         cancelado = 'SI'
                            # else:
                            #     if lista.total_pagado_rubro()==lista.capeventoperiodo.costoexterno:
                            #         cancelado = 'SI'
                        # Email personal
                        campo6 = lista.participante.email if lista.participante.email else 'NO REGISTRA'
                        # Email institucional
                        emailinst = lista.participante.emailinst if lista.participante.emailinst else 'NO REGISTRA'

                        campo7 = lista.participante.telefono
                        campo8 = lista.participante.telefono_conv
                        # campo9 = lista.valor_rubrocursos()
                        # campo9 = lista.total_pagado_rubro()
                        campo9 = lista.total_pagos_rubros_edcon()
                        if lista.capeventoperiodo.costo == 0 and lista.capeventoperiodo.costoexterno == 0:
                            campo10 = 'SIN COSTO'
                        else:
                            if lista.personalunemi:
                                campo10 = lista.capeventoperiodo.costo
                            else:
                                campo10 = lista.capeventoperiodo.costoexterno
                        campo12 = 'NO REGISTRA PERFIL'
                        for perfil in lista.participante.mis_perfilesusuarios():
                            if perfil.tipo() == 'EXTERNO':
                                campo12 = 'EXTERNO'
                            else:
                                if perfil.tipo() == 'NO DEFINIDO':
                                    campo12 = 'NO DEFINIDO'
                                else:
                                    campo12 = 'COMUNIDAD UNEMI'

                        campo11=CapInscritoIpec.instructor_notasfinales(lista)
                        ws.write(row_num, 0, row_num, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo6, font_style2)
                        ws.write(row_num, 4, emailinst, font_style2)
                        ws.write(row_num, 5, cancelado, font_style2)
                        ws.write(row_num, 6, campo7, font_style2)
                        ws.write(row_num, 7, campo8, font_style2)
                        ws.write(row_num, 8, campo9, font_style2)
                        ws.write(row_num, 9, campo10, font_style2)
                        ws.write(row_num, 10, certificadoemail, font_style2)
                        ws.write(row_num, 11, campo11[0][0], font_style2)
                        ws.write(row_num, 12, campo11[0][1], font_style2)
                        ws.write(row_num, 13, list(insc), font_style2)
                        ws.write(row_num, 14, list(carr), font_style2)
                        ws.write(row_num, 15, str(list(reco)), font_style2)
                        ws.write(row_num, 16, lista.get_formapago_display().upper(), font_style2)
                        ws.write(row_num, 17, str(lista.fecha_creacion.date()), font_style2)
                        ws.write(row_num, 18, campo12, font_style2)
                    wb.save(response)
                    return response
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'descargarinscritosall':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    # ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_inscritos' + random.randint(1,
                                                                                                                10000).__str__() + '.xls'
                    row_num = 0
                    columns = [
                        (u"N.", 2000),
                        (u"CURSO", 10000),
                        (u"FACULTAD", 3000),
                        (u"CARRERA", 3000),
                        (u"USUARIO", 3000),
                        (u"CEDULA", 4000),
                        (u"NOMBRES", 6000),
                        (u"EMAIL", 6000),
                        (u"CORREO INSTITUCIONAL", 7000),
                        (u"CANCELADO", 6000),
                        (u"CALIFICACIÓN", 3000),
                        (u"ESTADO", 3000),
                        (u"TELEFONO CELULAR", 6000),
                        (u"TELEFONO CONVENCIONAL", 6000),
                        (u"VALOR PAGADO", 3000),
                        (u"VALOR CURSO", 3000),
                        (u"CERTIFICADO EMAIL", 3000),
                        (u"MES", 4000),
                        (u"FORMA PAGO", 4000),
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    eventoperiodo = int(request.GET['id'])
                    totalinscritos = CapInscritoIpec.objects.filter(capeventoperiodo__periodo_id=eventoperiodo,
                                                                    status=True).order_by('participante')

                    row_num = 0
                    for lista in totalinscritos:
                        insc = Inscripcion.objects.filter(persona__id=lista.participante.id, status=True).values_list(
                            'coordinacion__nombre', flat=True).exclude(coordinacion_id=7)
                        carr = Inscripcion.objects.values_list('carrera__nombre', flat=True).filter(
                            persona__id=lista.participante.id, status=True).exclude(coordinacion_id=7)
                        if not insc:
                            insc = Inscripcion.objects.filter(persona__id=lista.participante.id,
                                                              status=True).values_list(
                                'coordinacion__nombre', flat=True).exclude(coordinacion_id=7)
                        if not carr:
                            carr = Inscripcion.objects.values_list('carrera__nombre', flat=True).filter(
                                persona__id=lista.participante.id, status=True).exclude(coordinacion_id=7)
                        row_num += 1
                        cancelado = 'NO'
                        certificadoemail = 'NO'
                        if lista.participante.emailinst:
                            campo5=lista.participante.emailinst
                        else:
                            campo5 = 'NO REGISTRA'
                        usuario = ''
                        if lista.personalunemi or lista.es_alumnounemi():
                            usuario = 'UNEMI'
                        else:
                            usuario = 'EXTERNO'
                        campo6 = ''
                        campo7 = 0
                        if lista.emailnotificado:
                            certificadoemail = 'SI'
                        if lista.participante.cedula:
                            campo2 = lista.participante.cedula
                        else:
                            campo2 = lista.participante.pasaporte
                        campo3 = lista.participante.apellido1 + ' ' + lista.participante.apellido2 + ' ' + lista.participante.nombres
                        if lista.capeventoperiodo.costo == 0 and lista.capeventoperiodo.costoexterno == 0:
                            cancelado = 'SIN COSTO'
                        else:
                            if lista.existerubrocurso():
                                if lista.pagorubrocurso_2():
                                    cancelado = 'SI'
                                else:
                                    cancelado = 'NO'
                            else:
                                cancelado = 'FALTA CONFIGURAR RUBRO'
                            # if lista.personalunemi:
                            #     if lista.total_pagado_rubro()==lista.capeventoperiodo.costo:
                            #         cancelado = 'SI'
                            # else:
                            #     if lista.total_pagado_rubro()==lista.capeventoperiodo.costoexterno:
                            #         cancelado = 'SI'
                        if lista.participante.email:
                            campo6 = lista.participante.email
                        campo7 = lista.participante.telefono
                        campo8 = lista.participante.telefono_conv
                        # campo9 = lista.valor_rubrocursos()
                        campo9 = lista.total_pagos_rubros_edcon()

                        if lista.capeventoperiodo.costo == 0 and lista.capeventoperiodo.costoexterno == 0:
                            campo10 = 'SIN COSTO'
                        else:
                            if lista.personalunemi:
                                campo10 = lista.capeventoperiodo.costo
                            else:
                                campo10 = lista.capeventoperiodo.costoexterno
                        # if lista.inscrito.valor_rubro():
                        #     campo7 = lista.inscrito.valor_rubro()
                        campo11 = CapInscritoIpec.instructor_notasfinales(lista)
                        ws.write(row_num, 0, row_num, font_style2)
                        ws.write(row_num, 1, lista.capeventoperiodo.capevento.nombre, font_style2)
                        ws.write(row_num, 2, list(insc), font_style2)
                        ws.write(row_num, 3, list(carr), font_style2)
                        ws.write(row_num, 4, str(usuario), font_style2)
                        ws.write(row_num, 5, campo2, font_style2)
                        ws.write(row_num, 6, campo3, font_style2)
                        ws.write(row_num, 7, campo6, font_style2)
                        ws.write(row_num, 8, campo5, font_style2)
                        ws.write(row_num, 9, cancelado, font_style2)
                        ws.write(row_num, 10, campo11[0][0], font_style2)
                        ws.write(row_num, 11, campo11[0][1], font_style2)
                        ws.write(row_num, 12, campo7, font_style2)
                        ws.write(row_num, 13, campo8, font_style2)
                        ws.write(row_num, 14, campo9, font_style2)
                        ws.write(row_num, 15, campo10, font_style2)
                        ws.write(row_num, 16, certificadoemail, font_style2)
                        ws.write(row_num, 17, lista.capeventoperiodo.get_mes_display().upper() if lista.capeventoperiodo.mes else 'NO REGISTRA', font_style2)
                        ws.write(row_num, 18, lista.get_formapago_display().upper(), font_style2)

                        # ws.write(row_num, 7, campo7, font_style2)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'generarmasivo':
                try:
                    dominiosistema = request.build_absolute_uri('/')[:-1].strip("/")
                    eventoperiodo = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    totalinscritos = eventoperiodo.capinscritoipec_set.filter(status=True)
                    archivos_lista = []

                    directory = os.path.join(SITE_STORAGE, 'zipav')
                    try:
                        os.stat(directory)
                    except:
                        os.mkdir(directory)

                    url = os.path.join(SITE_STORAGE, 'media', 'zipav',
                                       'certificadosmasiv_{}_{}.zip'.format(eventoperiodo.pk,
                                                                            random.randint(1, 10000).__str__()))
                    url_zip = url
                    fantasy_zip = zipfile.ZipFile(url, 'w')

                    for inscrito in totalinscritos:
                        inscrito.rutapdf.delete()
                        inscrito.save(request)
                        if inscrito.instructor_notasfinales()[0][1] == 'APROBADO' and inscrito.total_saldo_rubro() == 0:
                            if inscrito.rutapdf:
                                nombre = remover_caracteres_especiales_unicode(
                                    inscrito.participante.__str__().lower().replace(' ', '_')).lower().replace(' ', '_')
                                fantasy_zip.write(inscrito.rutapdf.path, '{}_certificado_.pdf'.format(nombre))
                            else:
                                persona_cargo_tercernivel = None
                                cargo = None
                                tamano = 0
                                data['evento'] = evento = inscrito.capeventoperiodo
                                data['logoaval'] = inscrito.capeventoperiodo.archivo
                                data['elabora_persona'] = persona
                                firmacertificado = None
                                if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
                                    firmacertificado = PersonaDepartamentoFirmas.objects.get(actualidad=True,
                                                                                             status=True,
                                                                                             tipopersonadepartamento_id=1,
                                                                                             departamentofirma_id=1)

                                if PersonaDepartamentoFirmas.objects.filter(status=True, fechafin__gte=evento.fechafin,
                                                                            fechainicio__lte=evento.fechafin,
                                                                            tipopersonadepartamento_id=1,
                                                                            departamentofirma_id=1).exists():
                                    firmacertificado = PersonaDepartamentoFirmas.objects.get(status=True,
                                                                                             fechafin__gte=evento.fechafin,
                                                                                             fechainicio__lte=evento.fechadin,
                                                                                             tipopersonadepartamento_id=1,
                                                                                             departamentofirma_id=1)
                                #
                                data['firmacertificado'] = firmacertificado
                                if evento.envionotaemail:
                                    data['nota'] = evento.instructor_principal().extaer_notatotal(inscrito.id)
                                if DistributivoPersona.objects.filter(persona_id=persona,
                                                                      estadopuesto__id=PUESTO_ACTIVO_ID,
                                                                      status=True).exists():
                                    cargo = DistributivoPersona.objects.filter(persona_id=persona,
                                                                               estadopuesto__id=PUESTO_ACTIVO_ID,
                                                                               status=True)[0]
                                data['persona_cargo'] = cargo
                                data['persona_cargo_titulo'] = titulo = persona.titulacion_principal_senescyt_registro()
                                if not titulo == '':
                                    persona_cargo_tercernivel = \
                                        persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[
                                            0] if titulo.titulo.nivel_id == 4 else None
                                data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
                                data['inscrito'] = inscrito
                                mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                                       "septiembre",
                                       "octubre", "noviembre", "diciembre"]
                                data['fecha'] = u"Milagro, %s de %s del %s" % (
                                    datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)
                                data['listado_contenido'] = listado = evento.contenido.split(
                                    "\n") if evento.contenido else []
                                if evento.objetivo.__len__() < 290:
                                    if listado.__len__() < 21:
                                        tamano = 120
                                    elif listado.__len__() < 35:
                                        tamano = 100
                                    elif listado.__len__() < 41:
                                        tamano = 70
                                data['controlar_bajada_logo'] = tamano
                                print('{} -----  {}'.format(inscrito.id, inscrito))
                                qrname = 'qr_certificado_{}_{}'.format(inscrito.id, random.randint(1, 10000).__str__())
                                # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                                folder = os.path.join(
                                    os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
                                # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                                rutapdf = folder + qrname + '.pdf'
                                rutaimg = folder + qrname + '.png'
                                if os.path.isfile(rutapdf):
                                    os.remove(rutaimg)
                                    os.remove(rutapdf)

                                url = pyqrcode.create(
                                    'http://sga.unemi.edu.ec//media/qrcode/certificados/' + qrname + '.pdf')
                                # url = pyqrcode.create('http://127.0.0.1:8000//media/qrcode/certificados/' + qrname + '.pdf')

                                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                                data['qrname'] = 'qr' + qrname
                                valida = conviert_html_to_pdfsaveqrcertificado(
                                    'adm_capacitacioneventoperiodoipec/certificado_pdf.html',
                                    {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                                )
                                if valida:
                                    os.remove(rutaimg)
                                    inscrito.rutapdf = 'qrcode/certificados/' + qrname + '.pdf'
                                    inscrito.save(request)
                                    urlarchivo = os.path.join(SITE_STORAGE, 'media',
                                                              'qrcode/certificados/' + qrname + '.pdf')
                                    nombre = remover_caracteres_especiales_unicode(
                                        inscrito.participante.__str__().lower().replace(' ', '_')).lower().replace(' ',
                                                                                                                   '_')
                                    fantasy_zip.write(urlarchivo, '{}_certificado_.pdf'.format(nombre))
                    fantasy_zip.close()
                    response = HttpResponse(open(url_zip, 'rb'), content_type='application/zip')
                    response['Content-Disposition'] = 'attachment; filename=certificadosmasiv_{}_{}.zip'.format(
                        eventoperiodo.pk, random.randint(1, 10000).__str__())
                    return response
                except Exception as ex:
                    messages.error(request, ex)
                    print(ex)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

            elif action == 'inscritosmasivos':
                try:
                    eventoperiodo = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    totalinscritos = eventoperiodo.capinscritoipec_set.filter(status=True)
                    listaenviar = []
                    for inscrito in totalinscritos:
                        if inscrito.instructor_notasfinales()[0][1] == 'APROBADO' and inscrito.total_saldo_rubro() == 0:
                            listaenviar.append({'id': inscrito.pk,
                                                'participante__apellido1': inscrito.participante.apellido1,
                                                'participante__apellido2': inscrito.participante.apellido2,
                                                'participante__nombres': inscrito.participante.nombres,
                                                'capeventoperiodo__id': inscrito.capeventoperiodo.pk})
                    return JsonResponse({"result": "ok", "cantidad": len(listaenviar), "inscritos": listaenviar})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'generarcertificadosinnotificar':
                try:
                    periodo_ipec = CapInscritoIpec.objects.get(
                        pk=int(request.GET['id'])).capeventoperiodo.periodo.fechainicio.year
                    if periodo_ipec >= 2022:
                        import uuid
                        # data["DOMINIO_DEL_SISTEMA"] = dominio_sistema = request.build_absolute_uri('/')[:-1].strip("/")
                        persona_cargo_tercernivel = None
                        cargo = None
                        tamano = 0
                        inscrito = CapInscritoIpec.objects.get(pk=int(request.GET['id']))
                        data['evento'] = evento = inscrito.capeventoperiodo
                        data['logoaval'] = inscrito.capeventoperiodo.archivo
                        data['elabora_persona'] = persona
                        firmacertificado = None
                        if PersonaDepartamentoFirmas.objects.filter(status=True, departamento=111).exists():
                            firmacertificado = PersonaDepartamentoFirmas.objects.filter(status=True,
                                                                                        departamento=111).order_by(
                                '-id').first()

                        if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
                            firmaizquierda = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
                                                                                   tipopersonadepartamento_id=8,
                                                                                   departamentofirma_id=5)
                        if PersonaDepartamentoFirmas.objects.values('id').filter(status=True,
                                                                                 fechafin__gte=evento.fechafin,
                                                                                 fechainicio__lte=evento.fechafin,
                                                                                 tipopersonadepartamento_id=8,
                                                                                 departamentofirma_id=5).exists():
                            firmaizquierda = PersonaDepartamentoFirmas.objects.get(status=True,
                                                                                   fechafin__gte=evento.fechafin,
                                                                                   fechainicio__lte=evento.fechafin,
                                                                                   tipopersonadepartamento_id=8,
                                                                                   departamentofirma_id=5)
                        data['firmacertificado'] = firmacertificado
                        data['firmaimg'] = FirmaPersona.objects.filter(status=True,
                                                                       persona=firmacertificado.personadepartamento, tipofirma=1).last()
                        data['firmaizquierda'] = firmaizquierda
                        data['firmaimgizq'] = FirmaPersona.objects.filter(status=True,
                                                                          persona=firmaizquierda.personadepartamento, tipofirma=1).last()
                        if evento.envionotaemail:
                            data['nota'] = evento.instructor_principal().extaer_notatotal(inscrito.id)
                        if DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,
                                                              status=True).exists():
                            cargo = \
                            DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,
                                                               status=True)[0]
                        data['persona_cargo'] = cargo
                        data['persona_cargo_titulo'] = titulo = persona.titulacion_principal_senescyt_registro()
                        if not titulo == '':
                            persona_cargo_tercernivel = \
                                persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[
                                    0] if titulo.titulo.nivel_id == 4 else None
                        data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
                        # Tercera firma
                        data['firma_aprobado2'] = FirmaPersona.objects.filter(status=True,
                                                                              persona=evento.aprobado2, tipofirma=1).first().firma
                        # Tercera firma



                        data['inscrito'] = inscrito
                        mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                               "octubre", "noviembre", "diciembre"]
                        data['fecha'] = u"Milagro, %s de %s del %s" % (
                            datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)
                        data['listado_contenido'] = listado = evento.contenido.split("\n") if evento.contenido else []
                        if evento.objetivo.__len__() < 290:
                            if listado.__len__() < 21:
                                tamano = 120
                            elif listado.__len__() < 35:
                                tamano = 100
                            elif listado.__len__() < 41:
                                tamano = 70
                        data['controlar_bajada_logo'] = tamano
                        qrname = 'qr_certificado_' + str(inscrito.id)
                        # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                        folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
                        # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                        rutapdf = folder + qrname + '.pdf'
                        rutaimg = folder + qrname + '.png'
                        if os.path.isfile(rutapdf):
                            os.remove(rutaimg)
                            os.remove(rutapdf)
                        # generar nombre html y url html
                        if not inscrito.namehtmlinsignia:
                            htmlname = "%s%s" % (uuid.uuid4().hex, '.html')
                        else:
                            htmlname = inscrito.namehtmlinsignia
                        urlname = "/media/qrcode/certificados/%s" % htmlname
                        rutahtml = SITE_STORAGE + urlname
                        if os.path.isfile(rutahtml):
                            os.remove(rutahtml)
                        # generar nombre html y url html
                        # url = pyqrcode.create('https://sga.unemi.edu.ec/media/qrcode/certificados/' + htmlname)
                        url = pyqrcode.create(f'https://sga.unemi.edu.ec/media/qrcode/certificados/{htmlname}?v={data["version"]}')
                        # url = pyqrcode.create(dominio_sistema+'/media/qrcode/certificados/' + htmlname)
                        imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                        data['qrname'] = 'qr' + qrname

                        data['urlhtmlinsignia'] = dominio_sistema + urlname
                        # data['version'] = datetime.now().strftime('%Y%m%d_%H%M%S')
                        if evento.configuraciondefirmas == True:
                            firmas = ConfigurarcionMejoraContinua.objects.filter(curso=evento).order_by('orden')
                            data['firmas'] = firmas
                            valida = conviert_html_to_pdfsavevistaprevia(
                                'adm_capacitacioneventoperiodoipec/certificadoconfiguraciondefirmas.html',
                                {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                            )
                        else:
                            valida = conviert_html_to_pdfsavevistaprevia(
                                'adm_capacitacioneventoperiodoipec/certificado_nuevodiseno_pdf.html',
                                {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                            )
                        if valida:
                            # generar portada del certificado
                            # portada = convertir_certificadopdf_a_jpg(qrname, SITE_STORAGE, dominio_sistema, data)

                            # os.remove(rutaimg)
                            inscrito.rutapdf = 'qrcode/certificados/' + qrname + '.pdf'
                            inscrito.emailnotificado = True
                            inscrito.fecha_emailnotifica = datetime.now().date()
                            inscrito.persona_emailnotifica = persona
                            # inscrito.save(request)
                            data['rutapdf'] = '/media/{}'.format(inscrito.rutapdf)
                            # fecha para licencia o certificacion linkedin
                            if evento.fechacertificado:
                                data['fechalinkedin'] = evento.fechacertificado
                            else:
                                data['fechalinkedin'] = evento.fechafin
                            data['idcertificado'] = htmlname[0:len(htmlname) - 5]
                            # crear html de certificado valido en la media  y guardar url en base
                            # a = requests.get(dominio_sistema+'/adm_silabo?action=pregrado&codigo=%s' % encrypt(inscrito.id), verify=False)
                            a = render(request, "adm_capacitacioneventoperiodoipec/certificadovalido.html",
                                       {"data": data, 'institucion': 'UNIVERSIDAD ESTATAL DE MILAGRO', "remotenameaddr": 'sga.unemi.edu.ec'})
                            with open(SITE_STORAGE + urlname, "wb") as f:
                                f.write(a.content)
                            f.close()
                            inscrito.namehtmlinsignia = htmlname
                            inscrito.urlhtmlinsignia = urlname
                            inscrito.estado = 2
                            inscrito.save(request)
                            # fin crear html en la media y guardar url en base
                            time.sleep(5)
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Problemas al generar el reporte."})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Acción no permitida, el periodo del evento debe ser mayor a 2021."})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al generar el reporte. %s (%s)"%(ex,sys.exc_info()[-1].tb_lineno)})

            elif action == 'solonotificarcertificado':
                try:
                    periodo_ipec = CapInscritoIpec.objects.get(
                        pk=int(request.GET['id'])).capeventoperiodo.periodo.fechainicio.year
                    if periodo_ipec >= 2022:
                        # data["DOMINIO_DEL_SISTEMA"] = dominio_sistema = request.build_absolute_uri('/')[:-1].strip("/")
                        inscrito = CapInscritoIpec.objects.get(pk=int(request.GET['id']))
                        data['evento'] = evento = inscrito.capeventoperiodo
                        firmacertificado = None
                        if PersonaDepartamentoFirmas.objects.filter(status=True, departamento=111).exists():
                            firmacertificado = PersonaDepartamentoFirmas.objects.filter(status=True,
                                                                                        departamento=111).order_by(
                                '-id').first()
                        if inscrito.rutapdf and inscrito.urlhtmlinsignia:
                            data['urlhtmlinsignia'] = dominio_sistema + inscrito.urlhtmlinsignia
                            if str(evento.fechafin) >= "2022-10-01":
                                # Notificacion de certificado por correo
                                asunto = u"CERTIFICADO - " + inscrito.capeventoperiodo.capevento.nombre
                                correoinscrito = inscrito.participante.emailpersonal()
                                if IS_DEBUG:
                                    correoinscrito = ['pruebasdesarrollo2023@gmail.com']
                                send_html_mail(asunto, "emails/notificar_certificado.html",
                                               {'sistema': request.session['nombresistema'], 'inscrito': inscrito,
                                                'director': firmacertificado},
                                               correoinscrito,
                                               [], [inscrito.rutapdf],
                                               cuenta=CUENTAS_CORREOS[0][1])
                            else:
                                # Notificacion de certificado por SGA
                                notificacion('Insignia digital',
                                             'Tienes una Insignia digital del curso {} puedes compartirla en Linkedin, Twitter y/o Facebook. Para visualizarla clic en el link compartido aquí.'.format(
                                                 evento.capevento, data['urlhtmlinsignia']),
                                             inscrito.participante,
                                             None,
                                             data['urlhtmlinsignia'],
                                             inscrito.pk,
                                             1,
                                             'sga',
                                             CapInscritoIpec,
                                             request)
                            return JsonResponse({"result": "bad", "mensaje": u'Notificación enviada.'})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u'Problemas al enviar la notificación.'})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": 'Acción no permitida, el periodo del evento debe ser mayor a 2021.'})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Problemas al enviar la notificación. %s" % ex})

            elif action == 'reporte_generar_masivo':
                try:

                    periodo_ipec = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id'])).periodo.fechainicio.year
                    if periodo_ipec >= 2022:
                        import uuid
                        # data["DOMINIO_DEL_SISTEMA"] = dominio_sistema = request.build_absolute_uri('/')[:-1].strip("/")
                        eventoperiodo = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                        totalinscritos = eventoperiodo.capinscritoipec_set.filter(status=True)
                        if IS_DEBUG:
                            totalinscritos = eventoperiodo.capinscritoipec_set.filter(status=True).order_by('id')[:2] # terminator
                        listaenviar = []
                        listacorrecto = []
                        for inscrito in totalinscritos:
                            verifica=None
                            verifica=inscrito.instructor_notasfinales()
                            if verifica[0][1] == 'APROBADO' and inscrito.total_saldo_rubro() == 0:
                                persona_cargo_tercernivel = None
                                cargo = None
                                tamano = 0
                                inscrito = CapInscritoIpec.objects.get(pk=inscrito.id)
                                data['evento'] = evento = inscrito.capeventoperiodo
                                data['logoaval'] = inscrito.capeventoperiodo.archivo
                                data['elabora_persona'] = persona
                                firmacertificado = None
                                # if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
                                #     firmacertificado = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
                                #                                                              tipopersonadepartamento_id=1,
                                #                                                              departamentofirma_id=1)
                                #
                                # if PersonaDepartamentoFirmas.objects.filter(status=True, fechafin__gte=evento.fechafin,
                                #                                             fechainicio__lte=evento.fechafin,
                                #                                             tipopersonadepartamento_id=1,
                                #                                             departamentofirma_id=1).exists():
                                #     firmacertificado = PersonaDepartamentoFirmas.objects.get(status=True,
                                #                                                              fechafin__gte=evento.fechafin,
                                #                                                              fechainicio__lte=evento.fechafin,
                                #                                                              tipopersonadepartamento_id=1,
                                #                                                              departamentofirma_id=1)
                                if PersonaDepartamentoFirmas.objects.filter(status=True, departamento=111).exists():
                                    firmacertificado = PersonaDepartamentoFirmas.objects.filter(status=True,
                                                                                                departamento=111).order_by('-id').first()
                                if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
                                    firmaizquierda = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
                                                                                           tipopersonadepartamento_id=8,
                                                                                           departamentofirma_id=5)
                                if PersonaDepartamentoFirmas.objects.values('id').filter(status=True,
                                                                                         fechafin__gte=evento.fechafin,
                                                                                         fechainicio__lte=evento.fechafin,
                                                                                         tipopersonadepartamento_id=8,
                                                                                         departamentofirma_id=5).exists():
                                    firmaizquierda = PersonaDepartamentoFirmas.objects.get(status=True,
                                                                                           fechafin__gte=evento.fechafin,
                                                                                           fechainicio__lte=evento.fechafin,
                                                                                           tipopersonadepartamento_id=8,
                                                                                           departamentofirma_id=5)
                                #
                                # # firmacertificado = 'robles'
                                # # fechacambio = (datetime(2019, 11, 1, 0, 0, 0)).date()
                                # if evento.fechafin >= fechacambio and evento.fechafin.year < 2021:
                                #     firmacertificado = 'firmaguillermo'
                                # else:
                                #     if evento.fechafin.year > 2020:
                                #         firmacertificado = 'firmachacon'
                                data['firmacertificado'] = firmacertificado
                                data['firmaimg'] = FirmaPersona.objects.filter(status=True,
                                                                               persona=firmacertificado.personadepartamento, tipofirma=1).last()
                                data['firmaizquierda'] = firmaizquierda
                                data['firmaimgizq'] = FirmaPersona.objects.filter(status=True,
                                                                                  persona=firmaizquierda.personadepartamento, tipofirma=1).last()
                                if evento.envionotaemail:
                                    data['nota'] = evento.instructor_principal().extaer_notatotal(inscrito.id)
                                if DistributivoPersona.objects.filter(persona_id=persona, estadopuesto__id=PUESTO_ACTIVO_ID,
                                                                      status=True).exists():
                                    cargo = \
                                        DistributivoPersona.objects.filter(persona_id=persona,
                                                                           estadopuesto__id=PUESTO_ACTIVO_ID,
                                                                           status=True)[0]
                                data['persona_cargo'] = cargo
                                data['persona_cargo_titulo'] = titulo = persona.titulacion_principal_senescyt_registro()
                                if not titulo == '':
                                    persona_cargo_tercernivel = \
                                        persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[
                                            0] if titulo.titulo.nivel_id == 4 else None
                                data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
                                # Tercera firma
                                data['firma_aprobado2'] = FirmaPersona.objects.filter(status=True,
                                                                                      persona=evento.aprobado2, tipofirma=1).first().firma
                                # Tercera firma
                                data['inscrito'] = inscrito
                                mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                                       "octubre", "noviembre", "diciembre"]
                                data['fecha'] = u"Milagro, %s de %s del %s" % (
                                    datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)
                                data['listado_contenido'] = listado = evento.contenido.split("\n") if evento.contenido else []
                                if evento.objetivo.__len__() < 290:
                                    if listado.__len__() < 21:
                                        tamano = 120
                                    elif listado.__len__() < 35:
                                        tamano = 100
                                    elif listado.__len__() < 41:
                                        tamano = 70
                                data['controlar_bajada_logo'] = tamano
                                qrname = 'qr_certificado_' + str(inscrito.id)
                                # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
                                # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                                rutapdf = folder + qrname + '.pdf'
                                rutaimg = folder + qrname + '.png'
                                if os.path.isfile(rutapdf):
                                    os.remove(rutaimg)
                                    os.remove(rutapdf)
                                # generar nombre html y url html
                                if not inscrito.namehtmlinsignia:
                                    htmlname = "%s%s" % (uuid.uuid4().hex, '.html')
                                else:
                                    htmlname = inscrito.namehtmlinsignia
                                urlname = "/media/qrcode/certificados/%s" % htmlname
                                rutahtml = SITE_STORAGE + urlname
                                if os.path.isfile(rutahtml):
                                    os.remove(rutahtml)
                                # generar nombre html y url html
                                # url = pyqrcode.create('https://sga.unemi.edu.ec/media/qrcode/certificados/' + htmlname)
                                url = pyqrcode.create(f'{dominio_sistema}/media/qrcode/certificados/{htmlname}?v={data["version"]}')
                                # url = pyqrcode.create(dominio_sistema + '/media/qrcode/certificados/' + htmlname)
                                imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                                data['qrname'] = 'qr' + qrname
                                data['urlhtmlinsignia'] = dominio_sistema + urlname
                                # Cambio al diseño propuesto en Educacion continua 07/10/2022
                                # if str(evento.fechainicio) >= "2022-05-01":
                                #     valida = conviert_html_to_pdfsaveqrcertificado(
                                #         'adm_capacitacioneventoperiodoipec/certificado_formatonuevo_pdf.html',
                                #         {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                                #     )
                                # else:
                                #     valida = conviert_html_to_pdfsaveqrcertificado(
                                #         'adm_capacitacioneventoperiodoipec/certificado_pdf.html',
                                #         {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                                #     )
                                # data['version'] = datetime.now().strftime('%Y%m%d_%H%M%S')
                                if evento.configuraciondefirmas == True:
                                    firmas = ConfigurarcionMejoraContinua.objects.filter(curso=evento).order_by('orden')
                                    data['firmas'] = firmas
                                    valida = conviert_html_to_pdfsavevistaprevia(
                                        'adm_capacitacioneventoperiodoipec/certificadoconfiguraciondefirmas.html',
                                        {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                                    )
                                else:
                                    valida = conviert_html_to_pdfsavevistaprevia(
                                        'adm_capacitacioneventoperiodoipec/certificado_nuevodiseno_pdf.html',
                                        {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                                    )
                                if valida:
                                    # generar portada del certificado
                                    # portada = convertir_certificadopdf_a_jpg(qrname, SITE_STORAGE, dominio_sistema, data)

                                    #os.remove(rutaimg)
                                    inscrito.rutapdf = 'qrcode/certificados/' + qrname + '.pdf'
                                    # inscrito.emailnotificado = True
                                    # inscrito.fecha_emailnotifica = datetime.now().date()
                                    # inscrito.persona_emailnotifica = persona
                                    inscrito.save(request)
                                    data['rutapdf'] = '/media/{}'.format(inscrito.rutapdf)
                                    # fecha para licencia o certificacion linkedin
                                    if evento.fechacertificado:
                                        data['fechalinkedin'] = evento.fechacertificado
                                    else:
                                        data['fechalinkedin'] = evento.fechafin
                                    data['idcertificado'] = htmlname[0:len(htmlname) - 5]
                                    # crear html de certificado valido en la media  y guardar url en base
                                    a = render(request, "adm_capacitacioneventoperiodoipec/certificadovalido.html",
                                               {"data": data, 'institucion': 'UNIVERSIDAD ESTATAL DE MILAGRO', "remotenameaddr": 'sga.unemi.edu.ec'})
                                    with open(SITE_STORAGE + urlname, "wb") as f:
                                        f.write(a.content)
                                    f.close()
                                    inscrito.namehtmlinsignia = htmlname
                                    inscrito.urlhtmlinsignia = urlname
                                    inscrito.estado = 2
                                    inscrito.save(request) # fin crear html en la media y guardar url en base
                                    listacorrecto.append(inscrito.id)
                                    time.sleep(5)
                        print('total ok: ', listacorrecto)
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Acción no permitida, el periodo del evento debe ser mayor a 2021."})
                except Exception as ex:
                    messages.error(request, ex)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'inscritopagadomasivo':
                try:
                    curso = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    listaenviar = []
                    if curso.costo:
                        totalinscritos = curso.list_inscritos_costo()
                    else:
                        totalinscritos = curso.list_inscritos_sin_costo()

                    for inscrito in totalinscritos:
                            listaenviar.append({'id': inscrito.pk,

                                                'participante__apellido1': inscrito.participante.apellido1,
                                                'participante__apellido2': inscrito.participante.apellido2,
                                                'participante__nombres': inscrito.participante.nombres,
                                                'capeventoperiodo__id': curso.pk})

                    return JsonResponse({"result": "ok", "cantidad": len(listaenviar), "inscritos": listaenviar})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'inscritopagadoindividual':
                try:
                    from moodle import moodle
                    cursor = connections['moodle_pos'].cursor()
                    curso = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    inscrito=CapInscritoIpec.objects.get(id=int(request.GET['idinscrito']))
                    instructores = curso.capinstructoripec_set.filter(status=True)
                    data['evento'] = curso
                    if inscrito:
                        for inst in instructores:
                            queryest = """
                                    SELECT DISTINCT asi.userid, asi.roleid
                                    FROM  mooc_role_assignments asi
                                    INNER JOIN MOOC_CONTEXT CON ON asi.CONTEXTID=CON.ID AND ASI.ROLEID=%s 
                                    AND CON.INSTANCEID=%s AND asi.userid =%s
                                        """ % (10, inst.idcursomoodle, inscrito.participante.idusermoodleposgrado)
                            cursor.execute(queryest)
                            rowest = cursor.fetchall()
                            if not rowest:
                                inst.crear_actualizar_estudiantes_curso(moodle, 1, inscrito.id, edcon=True)

                        if inscrito.participante.usuario:
                            periodo = inscrito.capeventoperiodo.periodo
                            interno = False
                            usuario = inscrito.participante.usuario.username
                            correo = inscrito.participante.emailpersonal()

                            # Determina si es interno o no actual
                            if inscrito.personalunemi or inscrito.es_alumnounemi():
                                interno = True

                            # Determina si es interno o no antes
                            # if inscrito.participante.tiene_multiples_perfiles() or ( not inscrito.participante.tiene_usuario_externo()):
                            #     interno = True
                            # if not inscrito.participante.tiene_perfilusuario():
                            #     interno = False

                            asunto = u"CREDENCIALES - " + inscrito.capeventoperiodo.capevento.nombre
                            # instructivo = os.path.join(SITE_STORAGE,periodo.download_link_instructivo())
                            instructivo = [periodo.instructivo] if periodo.instructivo else None
                            if IS_DEBUG:
                                correo=['pruebasdesarrollo2023@gmail.com']
                            datos = {'sistema': request.session['nombresistema'], 'inscrito': inscrito,
                                     'interno': interno}
                            send_html_mail(asunto, "emails/credenciales_edcon.html", datos,
                                                          correo, [], instructivo,
                                           cuenta=CUENTAS_CORREOS[4][1])
                            log(u'se notifico credenciales educacion continua: %s' % inscrito.participante.cedula, request, "add")
                            # print(f'Usuario: {inscrito.participante.usuario.username}')
                            # print(f'Contraseña: {inscrito.participante.identificacion()}')
                            # print(f'Contraseña unemi: {inscrito.participante.usuario.password}')
                        return JsonResponse({"result":"ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Por favor seleccione un inscrito"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            # elif action == 'notificarinscritomsv':
            #     try:
            #         inscrito = CapInscritoIpec.objects.get(pk=request.GET['id'])
            #         certificadopdf = None
            #         inscrito.rutapdf.delete()
            #         inscrito.save(request)
            #         if inscrito.rutapdf:
            #             certificadopdf = inscrito.rutapdf.path
            #         else:
            #
            #             persona_cargo_tercernivel = None
            #             cargo = None
            #             tamano = 0
            #             data['evento'] = evento = inscrito.capeventoperiodo
            #             data['logoaval'] = inscrito.capeventoperiodo.archivo
            #             data['elabora_persona'] = persona
            #             firmacertificado = None
            #             if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
            #                 firmacertificado = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
            #                                                                          tipopersonadepartamento_id=1,
            #                                                                          departamentofirma_id=1)
            #
            #             if PersonaDepartamentoFirmas.objects.filter(status=True, fechafin__gte=evento.fechafin,
            #                                                         fechainicio__lte=evento.fechafin,
            #                                                         tipopersonadepartamento_id=1,
            #                                                         departamentofirma_id=1).exists():
            #                 firmacertificado = PersonaDepartamentoFirmas.objects.get(status=True,
            #                                                                          fechafin__gte=evento.fechafin,
            #                                                                          fechainicio__lte=evento.fechainicio,
            #                                                                          tipopersonadepartamento_id=1,
            #                                                                          departamentofirma_id=1)
            #
            #             if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
            #                 firmaizquierda = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
            #                                                                        tipopersonadepartamento_id=2,
            #                                                                        departamentofirma_id=1)
            #             if PersonaDepartamentoFirmas.objects.values('id').filter(status=True, fechafin__gte=evento.fechafin,
            #                                                                      fechainicio__lte=evento.fechafin,
            #                                                                      tipopersonadepartamento_id=2,
            #                                                                      departamentofirma_id=1).exists():
            #                 firmaizquierda = PersonaDepartamentoFirmas.objects.get(status=True, fechafin__gte=evento.fechafin,
            #                                                                        fechainicio__lte=evento.fechafin,
            #                                                                        tipopersonadepartamento_id=2,
            #                                                                        departamentofirma_id=1)
            #             data['firmacertificado'] = firmacertificado
            #             data['firmaimg'] = FirmaPersona.objects.filter(status=True, persona=firmacertificado.personadepartamento).last()
            #             data['firmaizquierda'] = firmaizquierda
            #             data['firmaimgizq'] = FirmaPersona.objects.filter(status=True, persona=firmaizquierda.personadepartamento).last()
            #             if evento.envionotaemail:
            #                 data['nota'] = evento.instructor_principal().extaer_notatotal(inscrito.id)
            #             if DistributivoPersona.objects.filter(persona_id=persona,
            #                                                   estadopuesto__id=PUESTO_ACTIVO_ID,
            #                                                   status=True).exists():
            #                 cargo = DistributivoPersona.objects.filter(persona_id=persona,
            #                                                            estadopuesto__id=PUESTO_ACTIVO_ID,
            #                                                            status=True)[0]
            #             data['persona_cargo'] = cargo
            #             data['persona_cargo_titulo'] = titulo = persona.titulacion_principal_senescyt_registro()
            #             if not titulo == '':
            #                 persona_cargo_tercernivel = \
            #                     persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[
            #                         0] if titulo.titulo.nivel_id == 4 else None
            #             data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
            #             data['inscrito'] = inscrito
            #             mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
            #                    "septiembre",
            #                    "octubre", "noviembre", "diciembre"]
            #             data['fecha'] = u"Milagro, %s de %s del %s" % (
            #                 datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)
            #             data['listado_contenido'] = listado = evento.contenido.split(
            #                 "\n") if evento.contenido else []
            #             if evento.objetivo.__len__() < 290:
            #                 if listado.__len__() < 21:
            #                     tamano = 120
            #                 elif listado.__len__() < 35:
            #                     tamano = 100
            #                 elif listado.__len__() < 41:
            #                     tamano = 70
            #             data['controlar_bajada_logo'] = tamano
            #             qrname = 'qr_certificado_{}_{}'.format(inscrito.id, random.randint(1, 10000).__str__())
            #             # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
            #             folder = os.path.join(
            #                 os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
            #             # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
            #             rutapdf = folder + qrname + '.pdf'
            #             rutaimg = folder + qrname + '.png'
            #             if os.path.isfile(rutapdf):
            #                 os.remove(rutaimg)
            #                 os.remove(rutapdf)
            #
            #             url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/certificados/' + qrname + '.pdf')
            #             # url = pyqrcode.create('http://127.0.0.1:8000//media/qrcode/certificados/' + qrname + '.pdf')
            #
            #             imageqr = url.png(folder + qrname + '.png', 16, '#000000')
            #             data['qrname'] = 'qr' + qrname
            #             if str(evento.fechainicio) >= "2022-05-01":
            #                 valida = conviert_html_to_pdfsaveqrcertificado(
            #                     'adm_capacitacioneventoperiodoipec/certificado_formatonuevo_pdf.html',
            #                     {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
            #                 )
            #             else:
            #                 valida = conviert_html_to_pdfsaveqrcertificado(
            #                     'adm_capacitacioneventoperiodoipec/certificado_pdf.html',
            #                     {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
            #                 )
            #             if valida:
            #                 os.remove(rutaimg)
            #                 inscrito.rutapdf = 'qrcode/certificados/' + qrname + '.pdf'
            #                 inscrito.save(request)
            #                 certificadopdf = os.path.join(SITE_STORAGE, 'media',
            #                                               'qrcode/certificados/' + qrname + '.pdf')
            #         if certificadopdf:
            #             inscrito.emailnotificado = True
            #             inscrito.fecha_emailnotifica = datetime.now().date()
            #             inscrito.persona_emailnotifica = persona
            #             inscrito.save(request)
            #             asunto = u"CERTIFICADO - " + inscrito.capeventoperiodo.capevento.nombre
            #             datos = {'sistema': request.session['nombresistema'], 'inscrito': inscrito}
            #             send_html_mail(asunto, "emails/notificar_certificado.html", datos,
            #                            inscrito.participante.emailpersonal(), [], [certificadopdf],
            #                            cuenta=CUENTAS_CORREOS[4][1])
            #         return JsonResponse({"result": "ok"})
            #     except Exception as ex:
            #         return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'notificarinscritomsv':
                try:
                    periodo_ipec = CapInscritoIpec.objects.get(pk=int(request.GET['id'])).capeventoperiodo.periodo.fechainicio.year
                    if periodo_ipec >= 2022:
                        import uuid
                        # data["DOMINIO_DEL_SISTEMA"] = dominio_sistema = request.build_absolute_uri('/')[:-1].strip("/")
                        inscrito = CapInscritoIpec.objects.get(pk=request.GET['id'])
                        # if IS_DEBUG:
                        #     inscrito = CapInscritoIpec.objects.get(pk=14713)
                        certificadopdf = None
                        # si el certificado fue generado ya no se genera
                        inscrito.rutapdf.delete()
                        inscrito.save(request)
                        if inscrito.rutapdf and inscrito.urlhtmlinsignia:
                            certificadopdf = inscrito.rutapdf.path
                        else:
                            persona_cargo_tercernivel = None
                            cargo = None
                            tamano = 0
                            data['evento'] = evento = inscrito.capeventoperiodo
                            data['logoaval'] = inscrito.capeventoperiodo.archivo
                            data['elabora_persona'] = persona
                            firmacertificado = None
                            # if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
                            #     firmacertificado = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
                            #                                                              tipopersonadepartamento_id=1,
                            #                                                              departamentofirma_id=1)
                            #
                            # if PersonaDepartamentoFirmas.objects.filter(status=True, fechafin__gte=evento.fechafin,
                            #                                             fechainicio__lte=evento.fechafin,
                            #                                             tipopersonadepartamento_id=1,
                            #                                             departamentofirma_id=1).exists():
                            #     firmacertificado = PersonaDepartamentoFirmas.objects.get(status=True,
                            #                                                              fechafin__gte=evento.fechafin,
                            #                                                              fechainicio__lte=evento.fechainicio,
                            #                                                              tipopersonadepartamento_id=1,
                            #                                                              departamentofirma_id=1)

                            if PersonaDepartamentoFirmas.objects.filter(status=True, departamento=111).exists():
                                firmacertificado = PersonaDepartamentoFirmas.objects.filter(status=True,
                                                                                            departamento=111).order_by('-id').first()

                            if PersonaDepartamentoFirmas.objects.filter(actualidad=True, status=True).exists():
                                firmaizquierda = PersonaDepartamentoFirmas.objects.get(actualidad=True, status=True,
                                                                                       tipopersonadepartamento_id=8,
                                                                                       departamentofirma_id=5)
                            if PersonaDepartamentoFirmas.objects.values('id').filter(status=True,
                                                                                     fechafin__gte=evento.fechafin,
                                                                                     fechainicio__lte=evento.fechafin,
                                                                                     tipopersonadepartamento_id=8,
                                                                                     departamentofirma_id=5).exists():
                                firmaizquierda = PersonaDepartamentoFirmas.objects.get(status=True,
                                                                                       fechafin__gte=evento.fechafin,
                                                                                       fechainicio__lte=evento.fechafin,
                                                                                       tipopersonadepartamento_id=8,
                                                                                       departamentofirma_id=5)
                            data['firmacertificado'] = firmacertificado
                            data['firmaimg'] = FirmaPersona.objects.filter(status=True,
                                                                           persona=firmacertificado.personadepartamento, tipofirma=1).last()
                            data['firmaizquierda'] = firmaizquierda
                            data['firmaimgizq'] = FirmaPersona.objects.filter(status=True,
                                                                              persona=firmaizquierda.personadepartamento, tipofirma=1).last()
                            if evento.envionotaemail:
                                data['nota'] = evento.instructor_principal().extaer_notatotal(inscrito.id)
                            if DistributivoPersona.objects.filter(persona_id=persona,
                                                                  estadopuesto__id=PUESTO_ACTIVO_ID,
                                                                  status=True).exists():
                                cargo = DistributivoPersona.objects.filter(persona_id=persona,
                                                                           estadopuesto__id=PUESTO_ACTIVO_ID,
                                                                           status=True)[0]
                            data['persona_cargo'] = cargo
                            data['persona_cargo_titulo'] = titulo = persona.titulacion_principal_senescyt_registro()
                            if not titulo == '':
                                persona_cargo_tercernivel = \
                                    persona.titulacion_set.filter(titulo__nivel=3).order_by('-fechaobtencion')[
                                        0] if titulo.titulo.nivel_id == 4 else None
                            data['persona_cargo_tercernivel'] = persona_cargo_tercernivel
                            # Tercera firma
                            data['firma_aprobado2'] = FirmaPersona.objects.filter(status=True,
                                                                                  persona=evento.aprobado2, tipofirma=1).first().firma
                            # Tercera firma
                            data['inscrito'] = inscrito
                            mes = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                                   "septiembre",
                                   "octubre", "noviembre", "diciembre"]
                            data['fecha'] = u"Milagro, %s de %s del %s" % (
                                datetime.now().day, str(mes[datetime.now().month - 1]), datetime.now().year)
                            data['listado_contenido'] = listado = evento.contenido.split(
                                "\n") if evento.contenido else []
                            if evento.objetivo.__len__() < 290:
                                if listado.__len__() < 21:
                                    tamano = 120
                                elif listado.__len__() < 35:
                                    tamano = 100
                                elif listado.__len__() < 41:
                                    tamano = 70
                            data['controlar_bajada_logo'] = tamano
                            qrname = 'qr_certificado_{}'.format(inscrito.id)
                            # folder = SITE_STORAGE + 'media/qrcode/evaluaciondocente/'
                            folder = os.path.join(
                                os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
                            # folder = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'evaluaciondocente')
                            rutapdf = folder + qrname + '.pdf'
                            rutaimg = folder + qrname + '.png'
                            if os.path.isfile(rutapdf):
                                os.remove(rutaimg)
                                os.remove(rutapdf)
                            # generar nombre html y url html
                            if not inscrito.namehtmlinsignia:
                                htmlname = "%s%s" % (uuid.uuid4().hex, '.html')
                            else:
                                htmlname = inscrito.namehtmlinsignia
                            urlname = "/media/qrcode/certificados/%s" % htmlname
                            rutahtml = SITE_STORAGE + urlname
                            if os.path.isfile(rutahtml):
                                os.remove(rutahtml)
                            # generar nombre html y url html
                            # url = pyqrcode.create('http://sga.unemi.edu.ec//media/qrcode/certificados/' + qrname + '.pdf')
                            url = pyqrcode.create(f'{dominio_sistema}/media/qrcode/certificados/{htmlname}?v={data["version"]}')
                            # url = pyqrcode.create('http://127.0.0.1:8000//media/qrcode/certificados/' + qrname + '.pdf')
                            imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                            data['qrname'] = 'qr' + qrname
                            data['urlhtmlinsignia'] = dominio_sistema + urlname
                            # data['version'] = datetime.now().strftime('%Y%m%d_%H%M%S')
                            valida = conviert_html_to_pdfsaveqrcertificado(
                                'adm_capacitacioneventoperiodoipec/certificado_nuevodiseno_pdf.html',
                                {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                            )
                            if valida:
                                # generar portada del certificado
                                # portada = convertir_certificadopdf_a_jpg(qrname, SITE_STORAGE, dominio_sistema, data)

                                # os.remove(rutaimg)
                                inscrito.rutapdf = 'qrcode/certificados/' + qrname + '.pdf'
                                inscrito.save(request)
                                certificadopdf = os.path.join(SITE_STORAGE, 'media',
                                                              'qrcode/certificados/' + qrname + '.pdf')
                                data['rutapdf'] = '/media/{}'.format(inscrito.rutapdf)
                                # fecha para licencia o certificacion linkedin
                                if evento.fechacertificado:
                                    data['fechalinkedin'] = evento.fechacertificado
                                else:
                                    data['fechalinkedin'] = evento.fechafin
                                data['idcertificado'] = htmlname[0:len(htmlname) - 5]
                                # crear html de certificado valido en la media  y guardar url en base
                                # a = requests.get(dominio_sistema+'/adm_silabo?action=pregrado&codigo=%s' % encrypt(inscrito.id), verify=False)
                                a = render(request, "adm_capacitacioneventoperiodoipec/certificadovalido.html",
                                           {"data": data, 'institucion': 'UNIVERSIDAD ESTATAL DE MILAGRO', "remotenameaddr": 'sga.unemi.edu.ec'})
                                with open(SITE_STORAGE + urlname, "wb") as f:
                                    f.write(a.content)
                                f.close()
                                inscrito.namehtmlinsignia = htmlname
                                inscrito.urlhtmlinsignia = urlname
                                inscrito.estado = 2
                                inscrito.save(request)
                                # fin crear html en la media y guardar url en base
                        if certificadopdf:
                            inscrito.emailnotificado = True
                            inscrito.fecha_emailnotifica = datetime.now().date()
                            inscrito.persona_emailnotifica = persona
                            inscrito.save(request)
                            # Notificacion
                            if str(evento.fechafin) >= "2022-10-01":
                                # Notificacion de certificado por correo
                                asunto = u"CERTIFICADO - " + inscrito.capeventoperiodo.capevento.nombre
                                datos = {'sistema': request.session['nombresistema'], 'inscrito': inscrito}
                                correoinscrito = inscrito.participante.emailpersonal()
                                if IS_DEBUG:
                                    correoinscrito = ['pruebasdesarrollo2023@gmail.com']
                                send_html_mail(asunto, "emails/notificar_certificado.html", datos,
                                               correoinscrito,
                                               [], [certificadopdf],
                                               cuenta=CUENTAS_CORREOS[4][1])
                            else:
                                # Notificacion de certificado por SGA
                                notificacion('Insignia digital',
                                             'Tienes una Insignia digital del curso {} puedes compartirla en Linkedin, Twitter y/o Facebook. Para visualizarla clic en el link compartido aquí.'.format(
                                                 evento.capevento, data['urlhtmlinsignia']),
                                             inscrito.participante,
                                             None,
                                             data['urlhtmlinsignia'],
                                             inscrito.pk,
                                             1,
                                             'sga',
                                             CapInscritoIpec,
                                             request)
                            time.sleep(5)
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Acción no permitida, el periodo del evento debe ser mayor a 2021."})
                except Exception as ex:
                    messages.error(request, ex)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'notificarcorreomasivo':
                try:
                    inscrito = CapInscritoIpec.objects.get(pk=request.GET['id'])
                    periodo = inscrito.capeventoperiodo.periodo
                    if inscrito.participante.usuario:
                        interno=False
                        usuario =  inscrito.participante.usuario.username
                        correo =  inscrito.participante.emailpersonal()

                        # Determina si es interno o no actual
                        if inscrito.personalunemi or inscrito.es_alumnounemi():
                            interno = True

                        # Determina si es interno o no antes
                        # if inscrito.participante.tiene_multiples_perfiles() or (not inscrito.participante.tiene_usuario_externo()):
                        #     interno = True
                        # if not inscrito.participante.tiene_perfilusuario():
                        #     interno=False

                        asunto = u"CREDENCIALES - " + inscrito.capeventoperiodo.capevento.nombre
                        # instructivo = os.path.join(SITE_STORAGE,periodo.download_link_instructivo())
                        instructivo =  [periodo.instructivo] if periodo.instructivo else None
                        if IS_DEBUG:
                            correo = ['pruebasdesarrollo2023@gmail.com']
                        datos = {'sistema': request.session['nombresistema'], 'inscrito': inscrito,'interno': interno}
                        send_html_mail(asunto, "emails/credenciales_edcon.html", datos,
                                       correo,[],instructivo,
                                       cuenta=CUENTAS_CORREOS[4][1])
                        log(u'se notifico credenciales educacion continua: %s' % inscrito.participante.cedula, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'observacioninscripcion':
                try:
                    data['inscrito'] = inscrito = CapInscritoIpec.objects.get(pk=int(request.GET['id']))
                    data['title'] = u'Observación de %s' % inscrito.participante.nombre_completo_inverso()
                    initial = model_to_dict(inscrito)
                    form = ObservacionInscritoEventoIpecForm(initial=initial)
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec/observacioninscripcion.html", data)
                except Exception as ex:
                    pass

            elif action == 'moverinscrito':
                try:
                    data['inscrito'] = inscrito = CapInscritoIpec.objects.get(pk=int(request.GET['id']))
                    data['title'] = u'Mover a %s' % inscrito.participante.nombre_completo_inverso()
                    form = MoverInscritoEventoIpecForm()
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec/moverinscrito.html", data)
                except Exception as ex:
                    pass

            elif action == 'addrubros':
                try:
                    data['title'] = u'Nuevo Rubro'
                    data['form'] = TipoOtroRubroIpecForm()
                    return render(request, "adm_capacitacioneventoperiodoipec/addrubros.html", data)
                except Exception as ex:
                    pass

            elif action == 'editrubros':
                try:
                    data['title'] = u'Modificación Rubro'
                    data['tipootrorubro'] = tipootrorubro = TipoOtroRubro.objects.get(pk=request.GET['id'])
                    form = TipoOtroRubroIpecForm(initial={'nombre': tipootrorubro.nombre,
                                                          'partida': tipootrorubro.partida,
                                                          'unidad_organizacional': tipootrorubro.unidad_organizacional,
                                                          'programa': tipootrorubro.programa,
                                                          'ivaaplicado': tipootrorubro.ivaaplicado,
                                                          'valor': tipootrorubro.valor,
                                                          'tipo': tipootrorubro.tiporubro})
                    # Si el evento tiene al menos un rubro no se permite modificar el costo ni valor del rubro
                    # data['puede_editar_valorrubro'] = puede_editar_valorrubro = evento.puede_modificar_valorrubro_evento()
                    # if not puede_editar_valorrubro:
                    #     form.editar_rubro_deshabilitar()
                    data['form'] = form
                    return render(request, "adm_capacitacioneventoperiodoipec/editrubros.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleterubro':
                try:
                    data['title'] = u'Eliminar Rubro'
                    data['rubro'] = TipoOtroRubro.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_capacitacioneventoperiodoipec/deleterubro.html', data)
                except Exception as ex:
                    pass

            elif action == 'rubros':
                try:
                    data['title'] = u'Rubros'
                    search = None
                    ids = None
                    rubros = TipoOtroRubro.objects.filter(tiporubro=2, status=True)

                    if 'id' in request.GET:
                        ids = int(request.GET['id'])
                        rubros = rubros.filter(instructor_id=int(request.GET['id']))
                    if 's' in request.GET:
                        search = request.GET['s']
                        rubros = rubros.filter(nombre__icontains=search)

                    paging = MiPaginador(rubros, 20)
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
                    data['ids'] = ids if ids else ""
                    data['search'] = search if search else ""
                    data['rubros'] = page.object_list

                    return render(request, "adm_capacitacioneventoperiodoipec/viewrubros.html", data)
                except Exception as ex:
                    pass

            elif action == 'confirmar_actualizacion_modelo':
                try:
                    data['title'] = u'Actualización moodle'
                    data['evento'] = CapEventoPeriodoIpec.objects.get(pk=request.GET['id'])
                    data['clave'] = request.GET['clave']
                    return render(request, "adm_capacitacioneventoperiodoipec/confirmar_actualizacion_modelo.html",
                                  data)
                except Exception as ex:
                    pass

            elif action == 'actanotasindividual':
                try:
                    dtpdf = {'pagesize': 'A4', }
                    dtpdf['instructor'] = instructor = CapInstructorIpec.objects.get(pk=int(request.GET['id']),
                                                                                     status=True)
                    dtpdf['tareas'] = tarea = CapNotaIpec.objects.filter(instructor=instructor)
                    departamentogestion = Departamento.objects.filter(pk=96).first()
                    dtpdf['departamentogestion'] = departamentogestion
                    inscritos = instructor.capeventoperiodo.inscritos()
                    dtpdf['evento'] = instructor.capeventoperiodo
                    dtpdf['listadoinscritos'] = inscritos.exclude(desactivado=True)
                    return conviert_html_to_pdf('adm_capacitacioneventoperiodoipec/actasindividual.html', dtpdf)
                except Exception as ex:
                    pass

            elif action == 'reporte_recaudacion':
                try:
                    data['periodo'] = periodo = CapPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    data['evento'] = evento = CapEventoPeriodoIpec.objects.filter(periodo=periodo,
                                                                                  status=True).order_by('fechainicio')
                    return conviert_html_to_pdf('adm_capacitacioneventoperiodoipec/reporte_recaudacion_pdf.html',
                                                {'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    pass


            elif action == 'reporte_inscrito_epunemi':
                try:
                    data['evento'] = eventoperiodo = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    data['inscritos'] = inscrito = eventoperiodo.capinscritoipec_set.filter(status=True).distinct()
                    return conviert_html_to_pdf('adm_capacitacioneventoperiodoipec/reporte_inscrito_recaudacion_pdf.html',
                                                {'pagesize': 'A4', 'data': data})
                except Exception as ex:
                    pass


            elif action == 'actageneral':
                try:
                    dtpdf = {'pagesize': 'A4', }
                    dtpdf['evento'] = capeventoperiodo = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']),
                                                                                          status=True)
                    dtpdf['instructores'] = instructores = CapInstructorIpec.objects.filter(
                        capeventoperiodo_id=int(request.GET['id']), status=True)
                    # dtpdf['tareas'] = tarea = CapNotaIpec.objects.filter(instructor=instructor)
                    departamentogestion = Departamento.objects.filter(pk=96).first()
                    dtpdf['departamentogestion'] = departamentogestion
                    # inscritos = capeventoperiodo.inscritos()
                    inscritos = capeventoperiodo.inscritos_id()
                    pagado = Rubro.objects.filter(persona__in=inscritos, capeventoperiodoipec=capeventoperiodo,
                                                                                cancelado=True).values_list('persona__id').exclude(pago__factura__valida=False)
                    filtrobusqueda = (Q(status=True) & (Q(participante__id__in=pagado) | Q(aplicagratuidad=1)))
                    data['rubro'] = rubro = capeventoperiodo.capinscritoipec_set.filter(filtrobusqueda).order_by(
                        'participante__apellido1', 'participante__apellido2',
                        'participante__nombres') if capeventoperiodo.capinscritoipec_set.filter(status=True).exists() else []

                    dtpdf['listadoinscritos'] = rubro.exclude(desactivado=True)
                    if capeventoperiodo.convalidar:
                        return conviert_html_to_pdf('adm_capacitacioneventoperiodoipec/actageneralconvalida.html',
                                                    dtpdf)
                    return conviert_html_to_pdf('adm_capacitacioneventoperiodoipec/actageneral.html', dtpdf)
                except Exception as ex:
                    pass

            elif action == 'resetearusu':
                try:
                    data['title'] = u'Resetear clave del usuario'
                    data['inscrito'] = inscripcion = CapInscritoIpec.objects.get(pk=request.GET['id'])
                    return render(request, "adm_capacitacioneventoperiodoipec/modal/resetear.html", data)
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Periodo de Evento IPEC'
                data['reporte_3'] = obtener_reporte('inscritoscursoeducacioncontinuaperiodo')
                data['periodo'] = CapPeriodoIpec.objects.filter(status=True).order_by('-fechainicio')
                return render(request, 'adm_capacitacioneventoperiodoipec/viewperiodo.html', data)
            except Exception as ex:
                pass
# convertir de pdf a jpg
def convertir_certificadopdf_a_jpg(qrname, SITE_STORAGE, dominio_sistema, data):
    # ruta jpg
    jpgname = f'{qrname}'
    rutajpg = f'{SITE_STORAGE}/media/qrcode/certificados/{jpgname}.jpg'
    if os.path.isfile(rutajpg):
        os.remove(f'{rutajpg}')
    with open(f'{SITE_STORAGE}/media/qrcode/certificados/{qrname}.pdf', mode='rb') as pdf:
        images = convert_from_bytes(pdf.read(),
                                    output_folder=f'{SITE_STORAGE}/media/qrcode/certificados/',
                                    # first_page = True,
                                    poppler_path=SITE_POPPLER,
                                    fmt="jpg",
                                    single_file=True,
                                    thread_count=1,
                                    output_file=f'{jpgname}',
                                    size = (711, 549))
    data['url_jpg'] = dominio_sistema + f'/media/qrcode/certificados/{jpgname}.jpg'

# Busca id de persona EPUNEMI
def buscarIdPersonaEpunemi(identificacion):
    cursor = connections['epunemi'].cursor()
    sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (
    identificacion, identificacion, identificacion)
    cursor.execute(sql)
    idpersonaepunemi = cursor.fetchone()
    cursor.close()
    return idpersonaepunemi

# Consultar id de Tipo otro rubro EPUNEMI
def buscarIdTipootrorubroEpunemi(idtipootrorubrounemi):
    cursor = connections['epunemi'].cursor()
    sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (idtipootrorubrounemi)
    cursor.execute(sql)
    idtipootrorubroepunemi = cursor.fetchone()
    cursor.close()
    return idtipootrorubroepunemi

# Consultar si el Rubro Unemi tiene pagos en Epunemi
def buscarPagosEpunemiRubroUnemi(idrubroepuneminocan):
    cursor = connections['epunemi'].cursor()
    sql = """SELECT id FROM sagest_pago WHERE rubro_id=%s AND status=TRUE; """ % (idrubroepuneminocan)
    cursor.execute(sql)
    rubrotienepagosepunemi = cursor.fetchone()
    cursor.close()
    return rubrotienepagosepunemi

# Verifica si el rubro epunemi posee comprobantes registrados
def buscarComprobantedeRubroEpunemi(nombretiporubroepunemi, idpersonaepunemi):
    cursor = connections['epunemi'].cursor()
    sql = """SELECT id FROM sagest_comprobantealumno WHERE status=TRUE and persona_id=%s and curso='%s'; """ % (idpersonaepunemi, nombretiporubroepunemi)
    cursor.execute(sql)
    rubrotienecomprobanteepunemi = cursor.fetchone()
    cursor.close()
    return rubrotienecomprobanteepunemi

# Busca id de Rubro EPUNEMI
# def buscarIdRubroEpunemi(idrubrounemi):
#     cursor = connections['epunemi'].cursor()
#     sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE; """ % (idrubrounemi)
#     cursor.execute(sql)
#     rubroepunemi = cursor.fetchone()
#     cursor.close()
#     return rubroepunemi

# Migrar (guardar) rubro de unemi epunemi - 05/2023
# El parametro rubrosunemi debe ser de tipo list o queryset
def migrar_crear_rubro_deunemi_aepunemi(request, rubrosunemi, action='MIGRADO_UNEMI'):
    with transaction.atomic():
        try:
            # Valida que rubrosunemi sea una lista o queryset
            if isinstance(rubrosunemi, list) or callable(rubrosunemi):
                # Valida que lista o queryset no esté vacía
                if rubrosunemi[0]:

                    rubrospagados, total = [], 0
                    for r in rubrosunemi:

                        # idperunemi = rubrounemi.persona.id
                        identificacion = r.persona.identificacion()

                        # rubrosunemi = RubrosBuscar(idperunemi)
                        # Buscar ID persona EPUNEMI
                        idpersonaepunemi = buscarIdPersonaEpunemi(identificacion)
                        cursor = connections['epunemi'].cursor()

                        if idpersonaepunemi is None:
                            personaunemi = r.persona
                            sql = """ INSERT INTO sga_persona (status, nombres, apellido1, apellido2, cedula, ruc, pasaporte, 
                                                nacimiento, tipopersona, sector, direccion,  direccion2, num_direccion, telefono, telefono_conv, email,
                                                contribuyenteespecial, anioresidencia, nacionalidad, ciudad, referencia, emailinst,
                                                identificacioninstitucion, regitrocertificacion, libretamilitar, servidorcarrera, concursomeritos, 
                                                telefonoextension, tipocelular, periodosabatico, real, lgtbi, datosactualizados, 
                                                confirmarextensiontelefonia, acumuladecimo, acumulafondoreserva, representantelegal, inscripcioncurso, 
                                                unemi, idunemi)
                                                VALUES(TRUE, '%s', '%s', '%s', '%s', '%s', '%s', '/%s/', %s, '%s', '%s', '%s', '%s', '%s', '%s', '%s', 
                                                FALSE, 0, '', '', '', '', '', '', '', FALSE, FALSE, '', 0, FALSE, TRUE, FALSE, 0, FALSE, TRUE, FALSE, FALSE, FALSE, FALSE, 0); """ % (
                                personaunemi.nombres,
                                personaunemi.apellido1,
                                personaunemi.apellido2,
                                personaunemi.cedula,
                                personaunemi.ruc if personaunemi.ruc else '',
                                personaunemi.pasaporte if personaunemi.pasaporte else '',
                                personaunemi.nacimiento,
                                personaunemi.tipopersona if personaunemi.tipopersona else 1,
                                personaunemi.sector if personaunemi.sector else '',
                                personaunemi.direccion if personaunemi.direccion else '',
                                personaunemi.direccion2 if personaunemi.direccion2 else '',
                                personaunemi.num_direccion if personaunemi.num_direccion else '',
                                personaunemi.telefono if personaunemi.telefono else '',
                                personaunemi.telefono_conv if personaunemi.telefono_conv else '',
                                personaunemi.email if personaunemi.email else '')
                            cursor.execute(sql)
                            # Actualizar persona
                            # Verificar que exista en epunemi el id de estos datos
                            sexoepunemi, parroquiaepunemi, cantonepunemi, provinciaepunemi, paisepunemi = None, None, None, None, None

                            # Buscar los datos en EPUNEMI
                            if personaunemi.sexo:
                                sql = """SELECT sexo.id FROM sga_sexo AS sexo WHERE sexo.id='%s'  AND sexo.status=TRUE;  """ % (
                                    personaunemi.sexo.id)
                                cursor.execute(sql)
                                sexoepunemi = cursor.fetchone()
                                if sexoepunemi:
                                    sql = """UPDATE sga_persona SET sexo_id='%s' WHERE cedula='%s'; """ % (
                                    sexoepunemi[0], personaunemi.cedula)
                                    cursor.execute(sql)

                            if personaunemi.parroquia:
                                sql = """SELECT pa.id FROM sga_parroquia AS pa WHERE pa.id='%s'  AND pa.status=TRUE;  """ % (
                                    personaunemi.parroquia.id)
                                cursor.execute(sql)
                                parroquiaepunemi = cursor.fetchone()

                                if parroquiaepunemi:
                                    sql = """UPDATE sga_persona SET parroquia_id='%s' WHERE cedula='%s'; """ % (
                                    parroquiaepunemi[0], personaunemi.cedula)
                                    cursor.execute(sql)

                            if personaunemi.canton:
                                sql = """SELECT ca.id FROM sga_canton AS ca WHERE ca.id='%s'  AND ca.status=TRUE;  """ % (
                                    personaunemi.canton.id)
                                cursor.execute(sql)
                                cantonepunemi = cursor.fetchone()

                                if cantonepunemi:
                                    sql = """UPDATE sga_persona SET canton_id='%s' WHERE cedula='%s'; """ % (
                                    cantonepunemi[0], personaunemi.cedula)
                                    cursor.execute(sql)

                            if personaunemi.provincia:
                                sql = """SELECT pro.id FROM sga_provincia AS pro WHERE pro.id='%s'  AND pro.status=TRUE;  """ % (
                                    personaunemi.provincia.id)
                                cursor.execute(sql)
                                provinciaepunemi = cursor.fetchone()

                                if provinciaepunemi:
                                    sql = """UPDATE sga_persona SET provincia_id='%s' WHERE cedula='%s'; """ % (
                                    provinciaepunemi[0], personaunemi.cedula)
                                    cursor.execute(sql)

                            if personaunemi.pais:
                                sql = """SELECT pai.id FROM sga_pais AS pai WHERE pai.id='%s'  AND pai.status=TRUE;  """ % (
                                    personaunemi.pais.id)
                                cursor.execute(sql)
                                paisepunemi = cursor.fetchone()

                                if paisepunemi:
                                    sql = """UPDATE sga_persona SET pais_id='%s' WHERE cedula='%s'; """ % (
                                    paisepunemi[0], personaunemi.cedula)
                                    cursor.execute(sql)

                            print("*** Persona creada en EPUNEMI ***")

                            # ID DE PERSONA EPUNEMI creado
                            idpersonaepunemi = buscarIdPersonaEpunemi(identificacion)

                        idpersonaepunemi = idpersonaepunemi[0]




                        # Consulto id de Tipo otro rubro de EPUNEMI
                        idtipootrorubroepunemi = buscarIdTipootrorubroEpunemi(r.tipo.id)

                        if not idtipootrorubroepunemi:
                            tipootrorubrounemi = r.tipo

                            # Consulto id Centro costo de EPUNEMI
                            sql = """SELECT id FROM sagest_centrocosto WHERE status=True AND unemi=True AND tipo=%s;""" % (tipootrorubrounemi.tiporubro)
                            cursor.execute(sql)
                            centrocostoepunemi = cursor.fetchone()
                            idcentrocostoepunemi = centrocostoepunemi[0]

                            # Valido que no se guarde duplicado en Tipo otro rubro EPUNEMI
                            sql = """SELECT id FROM sagest_tipootrorubro WHERE status=True AND nombre ILIKE '%s'; """ % (tipootrorubrounemi.nombre)
                            cursor.execute(sql)
                            idtipootrorubroepunemi = cursor.fetchone()

                            if not idtipootrorubroepunemi:
                                # Consulto id y partida_id de la Cuenta contable de EPUNEMI
                                cuentacontable = CuentaContable.objects.filter(status=True, partida_id=int(tipootrorubrounemi.partida_id)).first()
                                sql = """SELECT id, partida_id FROM sagest_cuentacontable WHERE id=%s; """ % (cuentacontable.id)
                                cursor.execute(sql)
                                cuentacontableepunemi = cursor.fetchone()

                                # Creo el tipo otro rubro en epunemi
                                sql = """ Insert Into sagest_tipootrorubro (status, nombre, partida_id, valor, interface, activo, 
                                ivaaplicado_id, nofactura, exportabanco, cuentacontable_id, centrocosto_id, tiporubro, 
                                idtipootrorubrounemi, unemi, es_especie, es_convalidacionconocimiento)
                                VALUES(TRUE, '%s', %s, %s, FALSE, TRUE, %s, FALSE, TRUE, %s, %s, 1, %s, TRUE, FALSE, FALSE); """ % (
                                    r.tipo.nombre,
                                    cuentacontableepunemi[1],
                                    r.tipo.valor,
                                    r.tipo.ivaaplicado.id,
                                    cuentacontableepunemi[0],
                                    idcentrocostoepunemi,
                                    r.tipo.id)
                                cursor.execute(sql)
                                print("*** Tipo otro rubro creado en EPUNEMI ***")
                                # Excelente
                                # Consulto id de Tipo otro rubro de EPUNEMI creado
                                idtipootrorubroepunemi = buscarIdTipootrorubroEpunemi(r.tipo.id)

                        idtipootrorubroepunemi = idtipootrorubroepunemi[0]

                        # Consulto id de Rubro de EPUNEMI
                        # rubroepunemi = buscarIdRubroEpunemi(r.id)
                        sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE; """ % (r.id)
                        cursor.execute(sql)
                        rubroepunemi = cursor.fetchone()

                        # Pregunto si el rubro no existe en EPUNEMI
                        if not rubroepunemi:
                            # Creo el rubro en EPUNEMI
                            sql = """ INSERT INTO sagest_rubro (status, persona_id, nombre, cuota, tipocuota, fecha, fechavence,
                                valor, saldo, iva_id, valoriva, totalunemi, valortotal, cancelado, observacion, idrubrounemi, 
                                tipo_id, 
                                fecha_creacion, usuario_creacion_id, tienenotacredito, valornotacredito, valordescuento, 
                                anulado, compromisopago, refinanciado, bloqueado, bloqueadopornovedad, titularcambiado, coactiva)
                                VALUES (TRUE, %s, '%s', %s, %s, '/%s/', '/%s/', %s, %s, %s, %s, %s, %s, %s, '%s', %s, %s, 
                                NOW(), 1, FALSE, 0, 0, FALSE, %s, %s, %s, FALSE, FALSE, %s); """ % (
                                idpersonaepunemi,
                                r.nombre,
                                r.cuota,
                                r.tipocuota,
                                r.fecha,
                                r.fechavence,
                                r.valor,
                                r.saldo,
                                r.iva_id,
                                r.valoriva,
                                r.valor,
                                r.valortotal,
                                r.cancelado,
                                r.observacion,
                                r.id,
                                idtipootrorubroepunemi,
                                r.compromisopago if r.compromisopago else 0,
                                r.refinanciado,
                                r.bloqueado,
                                r.coactiva)
                            cursor.execute(sql)
                            print("*** Rubro creado en EPUNEMI ***")

                            # consultar Rubro de EPUNEMI creado NO anulado
                            # sql = """SELECT * FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND anulado=FALSE; """ % (r.id)
                            # cursor.execute(sql)
                            # rubroepuneminoanu = cursor.fetchone()
                            sql = """SELECT row_to_json(r) FROM (SELECT * FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND anulado=FALSE) r;"""
                            cursor.execute(sql, [r.id])
                            rubroepuneminoanu_dic = cursor.fetchone()
                            rubroepuneminoanu_dic = rubroepuneminoanu_dic[0]

                            # Vincular rubro de unemi con rubro migrado a epunemi
                            r.idrubroepunemi = rubroepuneminoanu_dic['id']  # Guardo solo el id
                            r.save()

                            # guardar auditoría en UNEMI el log del rubro migrado a EPUNEMI
                            qs_nuevo = [vars(r)]
                            salvaRubros(request, r, action, qs_nuevo=qs_nuevo)

                            # guardar auditoría en EPUNEMI el log del rubro migrado desde UNEMI
                            qs_nuevoepunemi = [rubroepuneminoanu_dic]
                            salvaRubrosEpunemiEdcon(rubroepuneminoanu_dic, action, qs_nuevo=qs_nuevoepunemi)
                            total += 1
                            print("*** Log rubro migrado (creado) en UNEMI y EPUNEMI ***")
                        # else:
                            # # consultar id, valor, totalunemi Rubro de EPUNEMI NO cancelado
                            # sql = """SELECT id, valor, totalunemi FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND cancelado=FALSE; """ % (r.id)
                            # cursor.execute(sql)
                            # rubroepuneminocan = cursor.fetchone()
                            # if rubroepuneminocan:
                                # if eliminarrubro:
                                #     # Consulto Pago Epunemi
                                #     rubrotienepagos = buscarPagosEpunemiRubroUnemi(rubroepuneminocan[0])
                                #     # Valido que no tenga pagos el rubro unemi, epunemi y que sean iguales el valor del rubro
                                #     if not r.tiene_pagos() and not rubrotienepagos and r.valor == rubroepuneminocan[1] and r.valor == rubroepuneminocan[2]:
                                #         # Consulto * rubro epunemi a eliminar (antes de cambiar el status)
                                #         sql = """SELECT row_to_json(r) FROM (SELECT * FROM sagest_rubro WHERE status=TRUE AND id=%s) r;"""
                                #         cursor.execute(sql, [rubroepuneminocan[0]])
                                #         rubroepuneminocan_dic = cursor.fetchone()
                                #         rubroepuneminocan_dic = rubroepuneminocan_dic[0]
                                #
                                #         # Elimino logicamente el rubro en Epunemi
                                #         sql = """UPDATE sagest_rubro SET status=false WHERE status=TRUE AND id=%s; """ % (rubroepuneminocan_dic[0])
                                #         cursor.execute(sql)
                                #
                                #         # guardar auditoría en UNEMI el log del rubro unemi eliminado
                                #         qs_nuevo = [vars(r)]
                                #         salvaRubros(request, r, action, qs_nuevo=qs_nuevo)
                                #
                                #         # guardar auditoría en EPUNEMI el log del rubro epunemi eliminado desde UNEMI
                                #         qs_nuevoepunemi = [rubroepuneminocan_dic]
                                #         salvaRubrosEpunemiEdcon(rubroepuneminocan, action, qs_nuevo=qs_nuevoepunemi)
                                #         total += 1
                                #         print("*** Log rubro eliminado en UNEMI y EPUNEMI ***")
                                #     else:
                                #         rubrospagados.append(f'{identificacion} [{r.id}] porque el rubro tiene pagos o su valor difiere con EPUNEMI')
                                #         print(f'{identificacion} [{r.id}] porque el rubro tiene pagos o su valor difiere con EPUNEMI')
                                # else:
                                #     # MODIFICA RUBRO SOLO SI NO HA SIDO CANCELADO NO POSEE PAGOS Y ACTUALIZA EL ID VINCULADO
                                #     pass
                    cursor.close()
                    return {"result": "ok", "mensaje": {"rubrospagados": rubrospagados, "total": total}}
                else:
                    raise NameError('¡Error!') # list o queryset vacía
            else:
                raise NameError('¡Error!') # Se espera una list o queryset
        except Exception as ex:
            transaction.set_rollback(True)
            return {"result": "bad", "mensaje": f"Error {str(ex)} on line {sys.exc_info()[-1].tb_lineno}"}

# Elimina rubros unemi y migra cambios a EPUNEMI
def eliminar_y_migrar_rubro_deunemi_aepunemi(request, rubrosunemi, action='MIGRADO_UNEMI', procesomasivo = False):
    with transaction.atomic():
        try:
            rubrospagados_noeliminados, total_rubrosunemi, total_rubrosepunemi = [], 0, 0
            for r in rubrosunemi:
                # consultar rubro epunemi
                cursor = connections['epunemi'].cursor()
                sql = """SELECT id, valor, totalunemi, cancelado, nombre, persona_id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE; """ % (
                    r.id)
                cursor.execute(sql)
                rubroepunemi = cursor.fetchone()
                inscrito = CapInscritoIpec.objects.filter(status=True, capeventoperiodo_id=r.capeventoperiodoipec.id, participante=r.persona).first()
                if rubroepunemi:
                    # consultar pago de rubro epunemi
                    tienepagosepunemi = buscarPagosEpunemiRubroUnemi(rubroepunemi[0])
                    # Valido que sólo elimine cuando no haya pago, no este cancelado y el valor de los rubros sean iguales en unemi y epunemi
                    if not r.tiene_pagos() and r.cancelado == False and not tienepagosepunemi and rubroepunemi[3] == False and r.valor == rubroepunemi[1] and r.valor == rubroepunemi[2]:
                        # Verificar que no tenga pendiente registro de pago, es decir que no tenga comprobante alumno epunemi
                        rubroepunemitienecomprobante =  buscarComprobantedeRubroEpunemi(rubroepunemi[4], rubroepunemi[5])
                        if not rubroepunemitienecomprobante:
                            # Elimino el rubro en UNEMI y llamo funcion eliminar en EPUNEMI
                            r.status = False
                            r.save(request)
                            if procesomasivo:
                                # Desactivar el inscrito
                                inscrito.desactivado = True
                                inscrito.save(request)
                                # Desactivar el inscrito
                            total_rubrosunemi += 1

                            # Consulto * rubro epunemi a eliminar (antes de cambiar el status)
                            sql = """SELECT row_to_json(r) FROM (SELECT * FROM sagest_rubro WHERE status=TRUE AND id=%s) r;"""
                            cursor.execute(sql, [rubroepunemi[0]])
                            rubroepunemi_dic = cursor.fetchone()
                            rubroepunemi_dic = rubroepunemi_dic[0]

                            # Elimino logicamente el rubro en Epunemi
                            sql = """UPDATE sagest_rubro SET status=false WHERE status=TRUE AND id=%s; """ % (rubroepunemi[0])
                            cursor.execute(sql)
                            total_rubrosepunemi += 1

                            # guardar auditoría en UNEMI el log del rubro unemi eliminado
                            qs_nuevo = [vars(r)]
                            salvaRubros(request, r, action, qs_nuevo=qs_nuevo)

                            # guardar auditoría en EPUNEMI el log del rubro epunemi eliminado desde UNEMI
                            qs_nuevoepunemi = [rubroepunemi_dic]
                            salvaRubrosEpunemiEdcon(rubroepunemi_dic, action, qs_nuevo=qs_nuevoepunemi)
                        else:
                            rubrospagados_noeliminados.append(f'{r.persona.cedula} [{r.id}] porque el rubro posee un comprobante de pago')
                    else:
                        rubrospagados_noeliminados.append(f'{r.persona.cedula} [{r.id}] porque el rubro posee pagos o su valor difiere con el rubro EPUNEMI')
                else:
                    # Elimino el rubro que sólo existe en UNEMI
                    # guardar auditoría en UNEMI el log del rubro elimminado en unemi
                    qs_nuevo = [vars(r)]
                    salvaRubros(request, r, action, qs_nuevo=qs_nuevo)
                    r.status = False
                    r.save(request)
                    if procesomasivo:
                        # Desactivar el inscrito
                        inscrito.desactivado = True
                        inscrito.save(request)
                        # Desactivar el inscrito
                    log(u'Se elimino un rubro a inscrito : %s [%s]' % (inscrito, r), request, "del")
                    total_rubrosunemi += total_rubrosunemi
                    rubrospagados_noeliminados.append(f'{r.persona.cedula} [{r.id}] porque el rubro no ha sido migrado a EPUNEMI')
                cursor.close()
            # concatenar rubrospagados_noeliminados
            textorubrosnoeliminado = rubrospagados_noeliminados[0] if rubrospagados_noeliminados else None
            for error in rubrospagados_noeliminados[1:]:
                textorubrosnoeliminado += f", {error}"
            return {"result": "ok", "mensaje": {"total_rubrosunemi": total_rubrosunemi, "total_rubrosepunemi": total_rubrosepunemi, "rubrospagados_noeliminados": textorubrosnoeliminado}}
        except Exception as ex:
            transaction.set_rollback(True)
            print(f"Error {str(ex)} on line {sys.exc_info()[-1].tb_lineno}")
            return {"result": "bad", "mensaje": f"Error {str(ex)} on line {sys.exc_info()[-1].tb_lineno}"}
