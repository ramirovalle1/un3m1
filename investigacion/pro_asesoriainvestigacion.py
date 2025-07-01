# -*- coding: UTF-8 -*-
import io
import json
import os
import calendar
from math import ceil

import PyPDF2
from datetime import time, datetime, timedelta, date
from decimal import Decimal

import requests
import xlsxwriter
from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, ExpressionWrapper, F, DurationField
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
import time as pausaparaemail
from xlwt import easyxf, XFStyle, Workbook
import random
from decorators import secure_module
from investigacion.forms import GrupoInvestigacionForm, FinanciamientoPonenciaForm, EvaluadorObraRelevanciaForm, ConvocatoriaObraRelevanciaForm, CronogramavaluacionInvestigacionForm, CitaAsesoriaForm, ReagendamientoCitaAsesoriaForm
from investigacion.funciones import FORMATOS_CELDAS_EXCEL, secuencia_asesoria, notificar_asesoria_investigacion
from investigacion.models import GrupoInvestigacion, FUNCION_INTEGRANTE_GRUPO_INVESTIGACION, GrupoInvestigacionIntegrante, ConvocatoriaObraRelevancia, ObraRelevancia, ObraRelevanciaRecorrido, ObraRelevanciaEvaluador, EvaluacionObraRelevancia, RubricaObraRelevancia, RubricaObraRelevanciaConvocatoria, \
    CronogramaEvaluacionInvestigacion, CriterioEvaluacionInvestigacion, PeriodoEvaluacionInvestigacion, PeriodoCronogramaEvaluacionInvestigacion, CriterioCronogramaEvaluacionInvestigacion, CitaAsesoria, ServicioGestion, Gestion, HorarioResponsableServicio, TurnoCita, RecorridoCitaAsesoria, \
    ResponsableServicio, AnexoCitaAsesoria, RecorridoAsesoria, HistorialCitaAsesoria
from sagest.commonviews import obtener_estado_solicitud
from settings import SITE_STORAGE
from sga.commonviews import adduserdata
from sga.forms import PlanificarPonenciasForm
from sga.funciones import MiPaginador, log, variable_valor, \
    convertir_fecha, remover_caracteres_tildes_unicode, cuenta_email_disponible, generar_nombre, email_valido, \
    validar_archivo, null_to_decimal, cuenta_email_disponible_para_envio, fechaletra_corta, fecha_letra_rango, dia_semana_enletras_fecha
from sga.funcionesxhtml2pdf import convert_html_to_pdf
from sga.models import CUENTAS_CORREOS, Persona, PlanificarPonencias, ConvocatoriaPonencia, CriterioPonencia, PlanificarPonenciasCriterio, PlanificarPonenciasRecorrido, MESES_CHOICES, Matricula, ArticuloInvestigacion
from django.template import Context
from django.template.loader import get_template

import time as ET

from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt

from django.core.cache import cache


@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    es_profesor = perfilprincipal.es_profesor()
    es_administrativo = perfilprincipal.es_administrativo()

    if not es_profesor and not es_administrativo:
        return HttpResponseRedirect("/?info=El Módulo está disponible para docentes y administrativos.")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'serviciogestion':
            try:
                gestion = Gestion.objects.get(pk=request.POST['id'])
                lista = []
                for servicio in ServicioGestion.objects.filter(gestion=gestion, status=True, tipo=1).order_by('nombre'):
                    lista.append([servicio.id, servicio.nombre])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. [%s]" % msg})

        elif action == 'addcita':
            try:
                f = CitaAsesoriaForm(request.POST)

                if f.is_valid():
                    # Obtener los valores del formulario
                    modalidad = f.cleaned_data['modalidad']
                    gestion = f.cleaned_data['gestion']
                    servicio = f.cleaned_data['servicio']
                    fecha = datetime.strptime(request.POST['fecha'], '%Y-%m-%d').date()
                    idturno = request.POST['idturno']
                    motivo = request.POST['motivo'].strip()

                    # Anexos
                    nfilas_ca_anexo = json.loads(request.POST['lista_items1']) if 'lista_items1' in request.POST else []  # Números de filas que tienen lleno el campo archivo en detalle de anexos
                    nfilas_anexo = request.POST.getlist('nfila_anexo[]')  # Todos los número de filas del detalle de anexos
                    descripciones_anexo = request.POST.getlist('descripcion_anexo[]')  # Todas las descripciones detalle anexos
                    archivos_anexo = request.FILES.getlist('archivo_anexo[]')  # Todos los archivos detalle anexos

                    # Valido los archivos cargados de detalle de anexos
                    for nfila, archivo in zip(nfilas_ca_anexo, archivos_anexo):
                        descripcionarchivo = 'Anexos'
                        resp = validar_archivo(descripcionarchivo, archivo, variable_valor("TIPOS_ANEXOS_ASESORIAS_INV"), variable_valor("TAMANIO_ANEXOS_ASESORIAS_INV"))
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "{} en la fila # {}".format(resp["mensaje"], nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                    # Consultar turno
                    turnocita = TurnoCita.objects.get(pk=idturno)

                    # Obtener fecha en letras
                    dialetras = dia_semana_enletras_fecha(fecha)
                    fechadialetras = dialetras + " " + str(fecha.day) + " de " + MESES_CHOICES[fecha.month - 1][1].capitalize() + " del " + str(fecha.year)
                    mensajehorario = "<b>" + fechadialetras + "</b> en horario de <b>" + turnocita.comienza.strftime('%H:%M') + " a " + turnocita.termina.strftime('%H:%M') + "</b>"

                    # Validar si aún existe el turno disponible para el servicio en ese horario
                    if HorarioResponsableServicio.objects.values("id").filter(status=True, fecha=fecha, turno_id=idturno, habilitado=True, ocupado=False, responsableservicio__estado=2, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__servicioresponsableservicio__visiblesolicitante=True).exists():
                        # Determinar el asesor que lo va a atender. El que menos asignaciones tenga
                        listaresponsables = []
                        responsablesservicio = HorarioResponsableServicio.objects.filter(status=True, fecha=fecha, turno_id=idturno, habilitado=True, ocupado=False, responsableservicio__estado=2, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__servicioresponsableservicio__visiblesolicitante=True)
                        for r in responsablesservicio:
                            totalhora = HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=datetime.now().date(), fecha__lte=fecha, turno_id=idturno, habilitado=True, ocupado=True, responsableservicio=r.responsableservicio).count()
                            totaldia = HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=datetime.now().date(), fecha__lte=fecha, habilitado=True, ocupado=True, responsableservicio=r.responsableservicio).count()
                            totalasignaciones = totalhora + totaldia
                            listaresponsables.append({"idresponsable": r.responsableservicio.responsable.id, "idresponsableservicio": r.responsableservicio.id, "totalasignaciones": totalasignaciones})

                        # Ordenar por campo totalasignaciones de menor a mayor
                        ordenados = sorted(listaresponsables, key=lambda dato: dato['totalasignaciones'], reverse=False)

                        # Obtener el responsable para la cita
                        dato = ordenados[0]
                        responsableservicio = ResponsableServicio.objects.get(pk=dato["idresponsableservicio"])

                        # Obtengo estado AGENDADO
                        estado = obtener_estado_solicitud(21, 1)

                        # Obtener secuencia de la cita
                        secuencia = secuencia_asesoria(1)

                        # Guardar la cita
                        citaasesoria = CitaAsesoria(
                            tipo=1,
                            secuencia=secuencia,
                            tiposolicitante=1 if es_profesor else 2,
                            solicitante=persona,
                            servicio=servicio,
                            responsable=responsableservicio.responsable,
                            ubicacion=responsableservicio.ubicacion,
                            bloque=responsableservicio.bloque,
                            oficina=responsableservicio.oficina,
                            piso=responsableservicio.piso,
                            modalidad=modalidad,
                            fecha=fecha,
                            horainicio=turnocita.comienza,
                            horafin=turnocita.termina,
                            motivo=motivo,
                            origen=1,
                            estado=estado
                        )
                        citaasesoria.save(request)

                        # Guarda detalle de anexos
                        for nfila, descripcion in zip(nfilas_anexo, descripciones_anexo):
                            anexocita = AnexoCitaAsesoria(
                                citaasesoria=citaasesoria,
                                descripcion=descripcion.strip(),
                                propietario=1
                            )
                            anexocita.save(request)

                            # Guardo el archivo del detalle
                            for nfilaarchi, archivo in zip(nfilas_ca_anexo, archivos_anexo):
                                # Si la fila de la descripcion es igual a la fila que contiene archivo
                                if int(nfilaarchi['nfila']) == int(nfila):
                                    # actualizo campo archivo del registro creado
                                    archivoreg = archivo
                                    archivoreg._name = generar_nombre("anexocita_", archivoreg._name)
                                    anexocita.archivo = archivoreg
                                    anexocita.save(request)
                                    break

                        # Creo el recorrido de la cita
                        recorrido = RecorridoCitaAsesoria(
                            citaasesoria=citaasesoria,
                            fecha=datetime.now().date(),
                            observacion=estado.observacion,
                            estado=estado
                        )
                        recorrido.save(request)

                        # Creo el historial de la cita
                        historialcita = HistorialCitaAsesoria(
                            citaasesoria=citaasesoria,
                            servicio=citaasesoria.servicio,
                            responsable=citaasesoria.responsable,
                            modalidad=citaasesoria.modalidad,
                            fecha=citaasesoria.fecha,
                            horainicio=citaasesoria.horainicio,
                            horafin=citaasesoria.horafin,
                            observacion=citaasesoria.observacion,
                            estado=citaasesoria.estado
                        )
                        historialcita.save(request)

                        # Asignar ocupado al horario del responsable
                        horarioresponsable = HorarioResponsableServicio.objects.get(status=True, responsableservicio=responsableservicio, turno=turnocita, fecha=fecha)
                        horarioresponsable.ocupado = True
                        horarioresponsable.save()

                        # Notificar por e-mail al responsable
                        notificar_asesoria_investigacion(citaasesoria, "AGECIT", request)

                        # Notificar por e-mail al solicitante
                        notificar_asesoria_investigacion(citaasesoria, "AGECITSOL", request)

                        log(u'%s agregó cita para asesoría de investigación: %s' % (persona, citaasesoria), request, "add")
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito. <br><br>Usted agendó una cita para el servicio de <b>{}</b> el {} con <b>{}</b>".format(servicio.nombre, mensajehorario, responsableservicio.responsable.nombre_completo_inverso()), "showSwal": True})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No existen turnos disponibles para el día {}".format(mensajehorario), "showSwal": "True", "swalType": "warning"})
                else:
                    for k, v in f.errors.items():
                        raise NameError( k + ', ' + v[0])
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'subiranexos':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                citaasesoria = CitaAsesoria.objects.get(pk=int(encrypt(request.POST['id'])))

                if citaasesoria:
                    # Verifico que pueda editar anexos
                    if not citaasesoria.puede_subir_anexos():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el registro debido a que fue revisado por la Coordinación de Investigación", "showSwal": "True", "swalType": "warning"})

                    # Obtener los valores de los detalles del formulario
                    nfilas_ca_anexo = json.loads(request.POST['lista_items1']) if 'lista_items1' in request.POST else []  # Números de filas que tienen lleno el campo archivo en detalle de anexos
                    nfilas_anexo = request.POST.getlist('nfila_anexo[]')  # Todos los número de filas del detalle de evidencias de anexo
                    idsreganexos = request.POST.getlist('idreganexo[]')  # Todos los ids de detalle de anexos
                    descripciones_anexos = request.POST.getlist('descripcion_anexo[]')  # Todas las descripciones detalle anexos
                    archivos_anexos = request.FILES.getlist('archivo_anexo[]')  # Todos los archivos detalle anexos
                    anexos_elim = json.loads(request.POST['lista_items2']) if 'lista_items2' in request.POST else [] # Ids registros de anexos borrados

                    # Valido los archivos cargados de detalle de anexos
                    for nfila, archivo in zip(nfilas_ca_anexo, archivos_anexos):
                        descripcionarchivo = 'Anexos'
                        resp = validar_archivo(descripcionarchivo, archivo, variable_valor("TIPOS_ANEXOS_ASESORIAS_INV"), variable_valor("TAMANIO_ANEXOS_ASESORIAS_INV"))
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "{} en la fila # {}".format(resp["mensaje"], nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                    # Consulto la asesoría
                    asesoria = citaasesoria.asesoria()

                    if asesoria:
                        # Si el estado de la asesoría es PENDIENTE S.
                        if asesoria.estado.valor == 3:
                            # Obtengo estado REGISTRADO S.
                            estadoasesoria = obtener_estado_solicitud(22, 4)

                            # Actualizo la asesoría
                            asesoria.estado = estadoasesoria
                            asesoria.save(request)

                            # Guardo el recorrido de la asesoría
                            recorrido = RecorridoAsesoria(
                                asesoria=asesoria,
                                fecha=datetime.now().date(),
                                observacion=estadoasesoria.observacion,
                                estado=estadoasesoria
                            )
                            recorrido.save(request)

                    # Guarda anexos de la cita
                    for idreg, nfila, descripcion in zip(idsreganexos, nfilas_anexo, descripciones_anexos):
                        # Si es registro nuevo
                        if int(idreg) == 0:
                            anexocita = AnexoCitaAsesoria(
                                citaasesoria=citaasesoria,
                                descripcion=descripcion.strip(),
                                propietario=1
                            )
                            anexocita.save(request)
                        else:
                            anexocita = AnexoCitaAsesoria.objects.get(pk=idreg)
                            anexocita.descripcion = descripcion.strip()

                        anexocita.save(request)

                        # Guardo el archivo del detalle
                        for nfilaarchi, archivo in zip(nfilas_ca_anexo, archivos_anexos):
                            # Si la fila de la descripcion es igual a la fila que contiene archivo
                            if int(nfilaarchi['nfila']) == int(nfila):
                                # actualizo campo archivo del registro creado
                                archivoreg = archivo
                                archivoreg._name = generar_nombre("anexocita_", archivoreg._name)
                                anexocita.archivo = archivoreg
                                anexocita.save(request)
                                break

                    # Elimino detalles de anexos
                    if anexos_elim:
                        for registro in anexos_elim:
                            anexocita = AnexoCitaAsesoria.objects.get(pk=registro['idreg'])
                            anexocita.status = False
                            anexocita.save(request)

                    log(u'%s actualizó anexos para la cita de asesoría: %s' % (persona, citaasesoria), request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La cita para asesoría no existe", "showSwal": "True", "swalType": "warning"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'reagendarcita':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                f = ReagendamientoCitaAsesoriaForm(request.POST)

                if f.is_valid():
                    # Consultar la cita para asesoría
                    citaasesoria = CitaAsesoria.objects.get(pk=int(encrypt(request.POST['id'])))

                    # Obtener los valores del formulario
                    modalidad = f.cleaned_data['modalidad']
                    fecha = datetime.strptime(request.POST['fecha'], '%Y-%m-%d').date()
                    idturno = request.POST['idturno']
                    observacion = request.POST['motivo'].strip()

                    # Obtengo estado REAGENDADA
                    estado = obtener_estado_solicitud(21, 2)

                    # Consulto el horario actual de la cita
                    horarioresponsableanterior = citaasesoria.horario_responsable_liberar()
                    responsable = citaasesoria.responsable
                    servicio = citaasesoria.servicio

                    # Consultar turno
                    turnocita = TurnoCita.objects.get(pk=idturno)

                    # Obtener fecha en letras
                    dialetras = dia_semana_enletras_fecha(fecha)
                    fechadialetras = dialetras + " " + str(fecha.day) + " de " + MESES_CHOICES[fecha.month - 1][1].capitalize() + " del " + str(fecha.year)
                    mensajehorario = "<b>" + fechadialetras + "</b> en horario de <b>" + turnocita.comienza.strftime('%H:%M') + " a " + turnocita.termina.strftime('%H:%M') + "</b>"

                    # Validar si aún existe el turno disponible para el servicio en ese horario
                    if HorarioResponsableServicio.objects.values("id").filter(status=True, fecha=fecha, turno_id=idturno, habilitado=True, ocupado=False, responsableservicio__estado=2, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__servicioresponsableservicio__visiblesolicitante=True).exists():
                        # Determinar el asesor que lo va a atender. El que menos asignaciones tenga
                        listaresponsables = []
                        responsablesservicio = HorarioResponsableServicio.objects.filter(status=True, fecha=fecha, turno_id=idturno, habilitado=True, ocupado=False, responsableservicio__estado=2, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__servicioresponsableservicio__visiblesolicitante=True)
                        for r in responsablesservicio:
                            totalhora = HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=datetime.now().date(), fecha__lte=fecha, turno_id=idturno, habilitado=True, ocupado=True, responsableservicio=r.responsableservicio).count()
                            totaldia = HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=datetime.now().date(), fecha__lte=fecha, habilitado=True, ocupado=True, responsableservicio=r.responsableservicio).count()
                            totalasignaciones = totalhora + totaldia
                            listaresponsables.append({"idresponsable": r.responsableservicio.responsable.id, "idresponsableservicio": r.responsableservicio.id, "totalasignaciones": totalasignaciones})

                        # Ordenar por campo totalasignaciones de menor a mayor
                        ordenados = sorted(listaresponsables, key=lambda dato: dato['totalasignaciones'], reverse=False)

                        # Obtener el responsable para la cita
                        dato = ordenados[0]
                        responsableservicio = ResponsableServicio.objects.get(pk=dato["idresponsableservicio"])

                        # Actualizo la cita
                        citaasesoria.responsable = responsableservicio.responsable
                        citaasesoria.ubicacion = responsableservicio.ubicacion
                        citaasesoria.bloque = responsableservicio.bloque
                        citaasesoria.oficina = responsableservicio.oficina
                        citaasesoria.piso = responsableservicio.piso
                        citaasesoria.modalidad = modalidad
                        citaasesoria.fecha = fecha
                        citaasesoria.horainicio = turnocita.comienza
                        citaasesoria.horafin = turnocita.termina
                        citaasesoria.observacion = observacion
                        citaasesoria.estado = estado
                        citaasesoria.save(request)

                        # Creo el recorrido de la cita
                        recorrido = RecorridoCitaAsesoria(
                            citaasesoria=citaasesoria,
                            fecha=datetime.now().date(),
                            observacion=estado.observacion,
                            estado=estado
                        )
                        recorrido.save(request)

                        # Creo el historial de la cita
                        historialcita = HistorialCitaAsesoria(
                            citaasesoria=citaasesoria,
                            servicio=citaasesoria.servicio,
                            responsable=citaasesoria.responsable,
                            modalidad=citaasesoria.modalidad,
                            fecha=citaasesoria.fecha,
                            horainicio=citaasesoria.horainicio,
                            horafin=citaasesoria.horafin,
                            observacion=citaasesoria.observacion,
                            estado=citaasesoria.estado
                        )
                        historialcita.save(request)

                        # Asignar ocupado al horario del responsable al cuál será reagendado
                        horarioresponsable = HorarioResponsableServicio.objects.get(status=True, responsableservicio=responsableservicio, turno=turnocita, fecha=fecha)
                        horarioresponsable.ocupado = True
                        horarioresponsable.save()

                        # Libero la hora que estaba ocupada anteriormente
                        horarioresponsableanterior.ocupado = False
                        horarioresponsableanterior.save(request)

                        # Notificar por e-mail al responsable
                        notificar_asesoria_investigacion(citaasesoria, "REACIT", request)

                        # Notificar por e-mail al solicitante
                        notificar_asesoria_investigacion(citaasesoria, "REACITSOL", request)

                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito. <br><br>Usted re-agendó una cita para el servicio de <b>{}</b> el {} con <b>{}</b>".format(servicio.nombre, mensajehorario, responsableservicio.responsable.nombre_completo_inverso()), "showSwal": True})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No existen turnos disponibles para el día {}".format(mensajehorario), "showSwal": "True", "swalType": "warning"})
                else:
                    for k, v in f.errors.items():
                        raise NameError(k + ', ' + v[0])
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'cancelarcita':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar la cita para asesoría
                citaasesoria = CitaAsesoria.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que se pueda cancelar
                if not citaasesoria.puede_cancelar_solicitante():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede cancelar la cita", "showSwal": "True", "swalType": "warning"})

                # Obtengo estado CANCELADO
                estado = obtener_estado_solicitud(21, 4)

                # Obtengo los valores del formulario
                observacion = request.POST['observacion'].strip()

                # Actualizar el registro de la cita
                citaasesoria.observacion = observacion
                citaasesoria.estado = estado
                citaasesoria.save(request)

                # Creo el recorrido de la cita
                recorrido = RecorridoCitaAsesoria(
                    citaasesoria=citaasesoria,
                    fecha=datetime.now().date(),
                    observacion=observacion,
                    estado=estado
                )
                recorrido.save(request)

                # Actualizo la hora como libre
                horarioresponsable = citaasesoria.horario_responsable_liberar()
                horarioresponsable.ocupado = False
                horarioresponsable.save(request)

                # Notificar por e-mail al responsable
                notificar_asesoria_investigacion(citaasesoria, "CANCIT", request)

                # Notificar por e-mail al solicitante
                notificar_asesoria_investigacion(citaasesoria, "CANCITSOL", request)

                log(u'%s canceló registro de cita para asesoría: %s' % (persona, citaasesoria), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Solicitud incorrecta.", "showSwal": "True", "swalType": "error"})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addcita':
                try:
                    data['title'] = u'Agregar Cita para Asesoría en Investigación'
                    form = CitaAsesoriaForm()
                    data['anio'] = datetime.now().date().year
                    data['mes'] = datetime.now().date().month
                    data['form'] = form
                    data['tipoanexos'] = ", ".join(variable_valor("TIPOS_ANEXOS_ASESORIAS_INV"))
                    data['tamanio'] = variable_valor("TAMANIO_ANEXOS_ASESORIAS_INV")
                    return render(request, "pro_asesoriainvestigacion/addcita.html", data)
                except Exception as ex:
                    pass

            elif action == 'cargarcalendario':
                try:
                    # Consulta el servicio de la gestión
                    servicio = ServicioGestion.objects.get(pk=int(request.GET['idserv']))
                    detalle = servicio.descripcion
                    fechaactual = datetime.now().date()
                    horaactual = datetime.now().time()

                    # Formar el calendario según mes y año
                    anio = int(request.GET['anio'])
                    mes = int(request.GET['mes'])

                    if request.GET['mov'] != '':
                        tipomovimiento = request.GET['mov']
                        if tipomovimiento == 'ant':
                            mes = mes - 1
                            if mes < 1:
                                anio = anio - 1
                                mes = 12
                        else:
                            mes = mes + 1
                            if mes > 12:
                                anio = anio + 1
                                mes = 1

                    listadias = []
                    calendario = calendar.TextCalendar()

                    for dia in calendario.itermonthdays(anio, mes):
                        if dia > 0:
                            # Consultar si existen turnos disponibles en ese día
                            fechacal = date(anio, mes, dia)

                            # Consulto si hay habilitados
                            # if fechacal == fechaactual:
                            #     if HorarioResponsableServicio.objects.values("id").filter(status=True, tiposervicio=1, fecha__gte=fechaactual, fecha=fechacal, turno__comienza__gte=horaactual, habilitado=True, responsableservicio__estado=2, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__servicioresponsableservicio__visiblesolicitante=True).exists():
                            #         if HorarioResponsableServicio.objects.values("id").filter(status=True, tiposervicio=1, fecha__gte=fechaactual, fecha=fechacal, turno__comienza__gte=horaactual, habilitado=True, ocupado=False, responsableservicio__estado=2, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__servicioresponsableservicio__visiblesolicitante=True).exists():
                            #             listadias.append({"dia": dia, "status": "TDI"})
                            #         else:
                            #             listadias.append({"dia": dia, "status": "OCU"})
                            #     else:
                            #         listadias.append({"dia": dia, "status": "STU"})
                            # else:
                            # Ahora sólo se podrá agendar desde el siguiente día con respecto a la fecha actual
                            if fechacal > fechaactual:
                                if HorarioResponsableServicio.objects.values("id").filter(status=True, tiposervicio=1, fecha__gte=fechaactual, fecha=fechacal, habilitado=True, responsableservicio__estado=2, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__servicioresponsableservicio__visiblesolicitante=True).exists():
                                    if HorarioResponsableServicio.objects.values("id").filter(status=True, tiposervicio=1, fecha__gte=fechaactual, fecha=fechacal, habilitado=True, ocupado=False, responsableservicio__estado=2, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__servicioresponsableservicio__visiblesolicitante=True).exists():
                                        listadias.append({"dia": dia, "status": "TDI"})
                                    else:
                                        listadias.append({"dia": dia, "status": "OCU"})
                                else:
                                    listadias.append({"dia": dia, "status": "STU"})
                            else:
                                listadias.append({"dia": dia, "status": "STU"})
                        else:
                            listadias.append({"dia": dia, "status": "STU"})

                    data['idserv'] = request.GET['idserv']
                    data['anio'] = anio
                    data['mes'] = mes
                    data['titulomes'] = MESES_CHOICES[mes - 1][1] + " " + str(anio)
                    data['listadias'] = listadias

                    template = get_template("pro_asesoriainvestigacion/calendario.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'detalle': detalle})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cargarturnosservicio':
                try:
                    servicio = ServicioGestion.objects.get(pk=int(request.GET['idserv']))

                    anio = int(request.GET['anio'])
                    mes = int(request.GET['mes'])
                    dia = int(request.GET['dia'])

                    fechacal = date(anio, mes, dia)
                    fechaactual = datetime.now().date()
                    horaactual = datetime.now().time()

                    # Obtener fecha en letras
                    dialetras = dia_semana_enletras_fecha(fechacal)
                    fechadialetras = dialetras + " " + str(fechacal.day) + " de " + MESES_CHOICES[fechacal.month - 1][1].capitalize() + " del " + str(fechacal.year)

                    data['idserv'] = request.GET['idserv']
                    data['fecha'] = fechacal
                    data['anio'] = anio
                    data['mes'] = mes
                    data['fechadialetras'] = fechadialetras

                    turnos = TurnoCita.objects.filter(status=True, tipo=1, horarioresponsableservicio__responsableservicio__estado=2, horarioresponsableservicio__status=True, horarioresponsableservicio__tiposervicio=1, horarioresponsableservicio__fecha=fechacal, horarioresponsableservicio__habilitado=True, horarioresponsableservicio__ocupado=False, horarioresponsableservicio__responsableservicio__servicioresponsableservicio__servicio=servicio, horarioresponsableservicio__responsableservicio__servicioresponsableservicio__vigente=True, horarioresponsableservicio__responsableservicio__servicioresponsableservicio__visiblesolicitante=True).distinct().order_by('orden')

                    listaturnos = []

                    for turno in turnos:
                        tienecitas = CitaAsesoria.objects.values("id").filter(status=True, tipo=1, fecha=fechacal, horainicio=turno.comienza, solicitante=persona).exclude(estado__valor=4).exists()
                        if not tienecitas:
                            if fechacal == fechaactual:
                                if turno.comienza >= horaactual:
                                    listaturnos.append({"id": turno.id, "comienza": turno.comienza.strftime('%H:%M'), "termina": turno.termina.strftime('%H:%M')})
                            else:
                                listaturnos.append({"id": turno.id, "comienza": turno.comienza.strftime('%H:%M'), "termina": turno.termina.strftime('%H:%M')})

                    data['turnos'] = listaturnos

                    template = get_template("pro_asesoriainvestigacion/turnoservicio.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'informacioncita':
                try:
                    title = u'Información de la Cita'
                    citaasesoria = CitaAsesoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['citaasesoria'] = citaasesoria
                    data['detalleasesoria'] = citaasesoria.detalle_asesoria()
                    data['proximacita'] = citaasesoria.proxima_cita()
                    template = get_template("adm_asesoriainvestigacion/modal/informacioncita.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'anexoscita':
                try:
                    data['title'] = u'Anexos del Solicitante de la Cita'
                    citaasesoria = CitaAsesoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['citaasesoria'] = citaasesoria
                    data['tipoanexos'] = ", ".join(variable_valor("TIPOS_ANEXOS_ASESORIAS_INV"))
                    data['tamanio'] = variable_valor("TAMANIO_ANEXOS_ASESORIAS_INV")
                    data['obligatorio'] = 'S' if citaasesoria.asesoria() else 'N'
                    template = get_template("pro_asesoriainvestigacion/modal/anexocita.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'reagendarcita':
                try:
                    data['title'] = u'Re-Agendar Cita para Asesoría en Investigación'
                    data['cita'] = cita = CitaAsesoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['fecha'] = datetime.now() if cita.fecha == datetime.now().date() else datetime.combine(cita.fecha, cita.horainicio)
                    data['anio'] = datetime.now().date().year
                    data['mes'] = datetime.now().date().month

                    form = ReagendamientoCitaAsesoriaForm(
                        initial={
                            'gestiona': cita.servicio.gestion.nombre,
                            'servicioa': cita.servicio.nombre,
                            'responsable': cita.responsable.nombre_completo_inverso(),
                            'fechaa': cita.fecha.strftime("%d-%m-%Y"),
                            'modalidada': cita.get_modalidad_display(),
                            'horainicio': cita.horainicio.strftime("%H:%M"),
                            'horafin': cita.horafin.strftime("%H:%M"),
                            'solicitantea': cita.solicitante.nombre_completo_inverso(),
                            'motivoa': cita.motivo
                        }
                    )
                    data['form'] = form
                    data['tipoanexos'] = ", ".join(variable_valor("TIPOS_ANEXOS_ASESORIAS_INV"))
                    data['tamanio'] = variable_valor("TAMANIO_ANEXOS_ASESORIAS_INV")

                    return render(request, "pro_asesoriainvestigacion/reagendarcita.html", data)
                except Exception as ex:
                    pass

            elif action == 'unirsereunion':
                try:
                    citaasesoria = CitaAsesoria.objects.get(pk=int(encrypt(request.GET['id'])))

                    # Obtener fecha en letras
                    fecha = citaasesoria.fecha
                    dialetras = dia_semana_enletras_fecha(fecha)
                    fechadialetras = dialetras + " " + str(fecha.day) + " de " + MESES_CHOICES[fecha.month - 1][1].capitalize() + " del " + str(fecha.year)
                    mensajehorario = "<b>" + fechadialetras + "</b> en horario de <b>" + citaasesoria.horainicio.strftime('%H:%M') + " a " + citaasesoria.horafin.strftime('%H:%M') + "</b>"
                    inicio = datetime.combine(citaasesoria.fecha, citaasesoria.horainicio) - timedelta(minutes=5) # Para que pueda conectarse 5 minutos antes

                    if datetime.now().date() == fecha:
                        if inicio.time() <= datetime.now().time() <= citaasesoria.horafin:
                            return JsonResponse({"result": "ok", "urlavirtual": citaasesoria.url_avirtual_responsable()})
                        elif datetime.now().time() < inicio.time():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"Usted podrá unirse a la reunión a partir de las <b>{inicio.time().strftime('%H:%M')}</b>", "showSwal": "True", "swalType": "warning"})
                        else:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"Usted no puede unirse a la reunión que estaba agendada para {mensajehorario}", "showSwal": "True", "swalType": "error"})
                    elif datetime.now().date() < fecha:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"Usted podrá unirse a la reunión el {mensajehorario}", "showSwal": "True", "swalType": "warning"})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"Usted no puede unirse a la reunión que estaba agendada para {mensajehorario}", "showSwal": "True", "swalType": "error"})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al obtener los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

            elif action == 'cancelarcita':
                try:
                    data['title'] = u'Cancelar Cita'
                    data['citaasesoria'] = CitaAsesoria.objects.get(pk=int(encrypt(request.GET['id'])))

                    template = get_template("pro_asesoriainvestigacion/modal/cancelarcita.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            try:
                search, filtro, url_vars = request.GET.get('s', ''), Q(status=True, solicitante=persona, tipo=1), ''

                citasasesorias = CitaAsesoria.objects.filter(filtro).order_by('-fecha', '-horainicio')

                paging = MiPaginador(citasasesorias, 25)
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
                data['citasasesorias'] = page.object_list
                data['title'] = u'Citas para Asesorías en Investigación'
                data['enlaceatras'] = "/pro_investigacion"

                return render(request, "pro_asesoriainvestigacion/view.html", data)
            except Exception as ex:
                pass
