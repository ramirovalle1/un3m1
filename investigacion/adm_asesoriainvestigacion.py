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
from investigacion.forms import GrupoInvestigacionForm, FinanciamientoPonenciaForm, EvaluadorObraRelevanciaForm, ConvocatoriaObraRelevanciaForm, CronogramavaluacionInvestigacionForm, CitaAsesoriaForm, GestionCitaAsesoriaForm, ReagendamientoCitaAsesoriaForm, HorarioServicioForm
from investigacion.funciones import FORMATOS_CELDAS_EXCEL, getdaterangefromweek, url_atencion_virtual, DIAS_FERIADOS, tipo_vista_gestion_asesoria, secuencia_asesoria, \
    analista_verifica_informe_docente_invitado, director_escuela_investigacion, tecnico_escuela_investigacion_auxiliar, notificar_asesoria_investigacion
from investigacion.models import GrupoInvestigacion, FUNCION_INTEGRANTE_GRUPO_INVESTIGACION, GrupoInvestigacionIntegrante, ConvocatoriaObraRelevancia, ObraRelevancia, ObraRelevanciaRecorrido, ObraRelevanciaEvaluador, EvaluacionObraRelevancia, RubricaObraRelevancia, RubricaObraRelevanciaConvocatoria, \
    CronogramaEvaluacionInvestigacion, CriterioEvaluacionInvestigacion, PeriodoEvaluacionInvestigacion, PeriodoCronogramaEvaluacionInvestigacion, CriterioCronogramaEvaluacionInvestigacion, CitaAsesoria, ServicioGestion, Gestion, HorarioResponsableServicio, TurnoCita, RecorridoCitaAsesoria, \
    ResponsableServicio, AnexoCitaAsesoria, Asesoria, DetalleAsesoria, RecorridoAsesoria, ServicioResponsableServicio, TIPO_SERVICIO, MODALIDAD_ATENCION, HistorialCitaAsesoria, TurnoDiaResponsableServicio, EnlaceAtencionVirtualPersona, TIPO_HERRAMIENTA_AVIRTUAL, ESTADO_HORARIO_SERVICIO, TipoServicioSemanaResponsableServicio, \
    TIPO_PERSONA_SOLICITANTE
from sagest.commonviews import obtener_estado_solicitud, obtener_estados_solicitud
from settings import SITE_STORAGE
from sga.commonviews import adduserdata
from sga.forms import PlanificarPonenciasForm
from sga.funciones import MiPaginador, log, variable_valor, \
    convertir_fecha, remover_caracteres_tildes_unicode, cuenta_email_disponible, generar_nombre, email_valido, \
    validar_archivo, null_to_decimal, cuenta_email_disponible_para_envio, fechaletra_corta, fecha_letra_rango, dia_semana_enletras_fecha
from sga.funcionesxhtml2pdf import convert_html_to_pdf
from sga.models import CUENTAS_CORREOS, Persona, PlanificarPonencias, ConvocatoriaPonencia, CriterioPonencia, PlanificarPonenciasCriterio, PlanificarPonenciasRecorrido, MESES_CHOICES, Matricula, ArticuloInvestigacion, Profesor, Administrativo, Inscripcion
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
    es_administrativo = perfilprincipal.es_administrativo()
    es_coordinador = persona.es_coordinador_investigacion()
    es_tecnico = persona.es_tecnico_investigacion()
    es_director_ei = persona == director_escuela_investigacion()
    es_analista_ei = persona == analista_verifica_informe_docente_invitado()
    es_auxiliar_ei = persona == tecnico_escuela_investigacion_auxiliar()

    if not es_administrativo:
        return HttpResponseRedirect("/?info=El Módulo está disponible para administrativos.")
    elif not es_coordinador and not es_tecnico and not es_director_ei and not es_analista_ei and not es_auxiliar_ei:
        return HttpResponseRedirect("/?info=Usted no tiene permitido el acceso al módulo.")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'gestionarcita':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                f = GestionCitaAsesoriaForm(request.POST)

                if f.is_valid():
                    # Si hay próxima cita debo validar que el turno aún esté disponible
                    proxima = f.cleaned_data['proxima']
                    modalidad = gestion = servicio = fechaproximacita = idturno = idresponsable = motivo = None

                    if proxima:
                        modalidad = f.cleaned_data['modalidad']
                        gestion = f.cleaned_data['gestion']
                        servicio = f.cleaned_data['servicio']
                        fechaproximacita = datetime.strptime(request.POST['fechaproximacita'], '%Y-%m-%d').date()
                        idturno = request.POST['idturno']
                        idresponsable = request.POST['idresponsable']
                        motivo = request.POST['motivo'].strip()

                        # Consultar turno
                        turnocita = TurnoCita.objects.get(pk=idturno)
                        responsable = Persona.objects.get(pk=idresponsable)

                        # Obtener fecha en letras
                        dialetras = dia_semana_enletras_fecha(fechaproximacita)
                        fechadialetras = dialetras + " " + str(fechaproximacita.day) + " de " + MESES_CHOICES[fechaproximacita.month - 1][1].capitalize() + " del " + str(fechaproximacita.year)
                        mensajehorario = "<b>" + fechadialetras + "</b> en horario de <b>" + turnocita.comienza.strftime('%H:%M') + " a " + turnocita.termina.strftime('%H:%M') + "</b>"

                        # Validar que turno esté disponible
                        if servicio.tipo == 1:
                            if not HorarioResponsableServicio.objects.values("id").filter(status=True, fecha=fechaproximacita, turno_id=idturno, habilitado=True, ocupado=False, responsableservicio__responsable=responsable, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True).exists():
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No existen turnos disponibles para el día {}".format(mensajehorario), "showSwal": "True", "swalType": "warning"})
                        else:
                            if not HorarioResponsableServicio.objects.values("id").filter(status=True, fecha=fechaproximacita, turno_id=idturno, habilitado=True, reutilizable=True, responsableservicio__responsable=responsable, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True).exists():
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No existen turnos disponibles para el día {}".format(mensajehorario), "showSwal": "True", "swalType": "warning"})

                    # Consultar la cita para asesoría
                    citaasesoria = CitaAsesoria.objects.get(pk=int(encrypt(request.POST['id'])))

                    # Obtengo estado FINALIZADO
                    estado = obtener_estado_solicitud(21, 5)

                    # Obtener los valores del formulario
                    asistio = f.cleaned_data['asistio']
                    horainicioase = f.cleaned_data['horainicioase']
                    horafinase = f.cleaned_data['horafinase']
                    observacion = f.cleaned_data['observacion'].strip()
                    realizaproximaacti = f.cleaned_data['realizaproximaacti']
                    compromisoinv = ''
                    compromisosol = ''
                    horacompleta = asistio

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

                    # Si asistió calcular minutos atraso y sobrante
                    if asistio:
                        hiniciocita = datetime.combine(citaasesoria.fecha, citaasesoria.horainicio)
                        hfincita = datetime.combine(citaasesoria.fecha, citaasesoria.horafin)
                        hinicioase2 = datetime.combine(citaasesoria.fecha, horainicioase)
                        hfinase2 = datetime.combine(citaasesoria.fecha, horafinase)

                        # Validar los campos de horas de inicio y fin de asesoria
                        if hinicioase2 < hiniciocita or hinicioase2 > hfincita:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La hora de inicio de la asesoría debe estar en el rango <b>{}</b> - <b>{}</b>".format(hiniciocita.strftime('%H:%M'), hfincita.strftime('%H:%M')), "showSwal": "True", "swalType": "warning"})

                        # if hfinase2 < hiniciocita or hfinase2 > hfincita:
                        #     return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La hora de fin de la asesoría debe estar en el rango <b>{}</b> - <b>{}</b>".format(hiniciocita.strftime('%H:%M'), hfincita.strftime('%H:%M')), "showSwal": "True", "swalType": "warning"})

                        if hfinase2 < hinicioase2:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La hora de fin de la asesoría debe mayor o igual a la hora de inicio", "showSwal": "True", "swalType": "warning"})

                        atraso = hinicioase2 - hiniciocita
                        atraso = str(atraso)

                        if hfinase2 <= hfincita:
                            sobrante = hfincita - hfinase2
                            minutossob = int(str(sobrante).split(":")[1])
                            if minutossob >= 20:
                                horacompleta = False

                            sobrante = str(sobrante)
                        else:
                            sobrante = '00:00:00'
                    else:
                        horainicioase = horafinase = atraso = sobrante = minutossob = None

                    msgguardado = ""

                    # Actualizar el registro de la cita
                    citaasesoria.horainicioase = horainicioase if asistio else None
                    citaasesoria.horafinase = horafinase if asistio else None
                    citaasesoria.atraso = atraso
                    citaasesoria.sobrante = sobrante
                    citaasesoria.observacion = observacion if not asistio else ''
                    citaasesoria.asistio = asistio
                    citaasesoria.horacompleta = horacompleta
                    citaasesoria.estado = estado
                    citaasesoria.save(request)

                    # Creo el recorrido de la cita
                    recorrido = RecorridoCitaAsesoria(
                        citaasesoria=citaasesoria,
                        fecha=datetime.now().date(),
                        observacion=estado.observacion if asistio else observacion,
                        estado=estado
                    )
                    recorrido.save(request)

                    # Guarda detalle de anexos subidos por el responsable de investigación
                    for nfila, descripcion in zip(nfilas_anexo, descripciones_anexo):
                        anexocita = AnexoCitaAsesoria(
                            citaasesoria=citaasesoria,
                            descripcion=descripcion.strip(),
                            propietario=2
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

                    # En caso de haber asistido a la cita
                    if asistio:
                        # Crear el registro de la asesoría
                        asesoria = citaasesoria.asesoria()
                        detalleasesoria = None

                        if not asesoria:
                            # Obtengo estado INICIADA
                            estadoasesoria = obtener_estado_solicitud(22, 1)

                            asesoria = Asesoria(
                                citaasesoria=citaasesoria,
                                fechainicio=citaasesoria.fecha,
                                observacion=observacion,
                                estado=estadoasesoria
                            )
                            asesoria.save(request)

                            # Guardo el detalle de la asesoría
                            detalleasesoria = DetalleAsesoria(
                                asesoria=asesoria,
                                citaasesoria=citaasesoria,
                                fecha=citaasesoria.fecha,
                                comienzo=horainicioase,
                                fin=horafinase,
                                proxima=proxima,
                                realizaproximaacti=realizaproximaacti if realizaproximaacti != '' else None,
                                observacion=observacion,
                                compromisoinv=compromisoinv,
                                compromisosol=compromisosol,
                                estado=estadoasesoria
                            )
                            detalleasesoria.save(request)

                            # Guardo el recorrido de la asesoría
                            recorrido = RecorridoAsesoria(
                                asesoria=asesoria,
                                fecha=datetime.now().date(),
                                observacion=observacion,
                                estado=estadoasesoria
                            )
                            recorrido.save(request)
                        else:
                            # Obtengo estado REGISTRADA
                            estadoasesoria = obtener_estado_solicitud(22, 7)

                            # Actualizo
                            asesoria.observacion = observacion
                            asesoria.estado = estadoasesoria
                            asesoria.save(request)

                            # Guardo el detalle de la asesoría
                            detalleasesoria = DetalleAsesoria(
                                asesoria=asesoria,
                                citaasesoria=citaasesoria,
                                fecha=citaasesoria.fecha,
                                comienzo=horainicioase,
                                fin=horafinase,
                                proxima=proxima,
                                realizaproximaacti=realizaproximaacti if realizaproximaacti != '' else None,
                                observacion=observacion,
                                compromisoinv=compromisoinv,
                                compromisosol=compromisosol,
                                estado=estadoasesoria
                            )
                            detalleasesoria.save(request)

                            # Guardo el recorrido de la asesoría
                            recorrido = RecorridoAsesoria(
                                asesoria=asesoria,
                                fecha=datetime.now().date(),
                                observacion=observacion,
                                estado=estadoasesoria
                            )
                            recorrido.save(request)

                        # En caso de no continuar con las asesorías se debe asignar estado FINALIZADO
                        if not proxima:
                            # Obtengo estado FINALIZADA
                            estadoasesoria = obtener_estado_solicitud(22, 2)

                            # Actualizo la asesoría
                            asesoria.fechafin = citaasesoria.fecha
                            asesoria.estado = estadoasesoria
                            asesoria.save(request)

                            # Guardo el recorrido de la asesoría
                            recorrido = RecorridoAsesoria(
                                asesoria=asesoria,
                                fecha=datetime.now().date(),
                                observacion="ASESORÍA FINALIZADA",
                                estado=estadoasesoria
                            )
                            recorrido.save(request)
                        else:
                            # Si proxima actividad la realiza el solicitante inicial de las asesorías o el técnico responsable
                            solicitante = asesoria.citaasesoria.solicitante
                            if int(realizaproximaacti) == 1:
                                # Obtengo estado ACTIVIDAD PENDIENTE SOLICITANTE
                                estadoasesoria = obtener_estado_solicitud(22, 3)
                            else:
                                # Obtengo estado ACTIVIDAD PENDIENTE INVESTIGACIÓN
                                estadoasesoria = obtener_estado_solicitud(22, 5)

                            # Actualizo la asesoría
                            asesoria.observacion = observacion
                            asesoria.estado = estadoasesoria
                            asesoria.save(request)

                            # Guardo el recorrido de la asesoría
                            recorrido = RecorridoAsesoria(
                                asesoria=asesoria,
                                fecha=datetime.now().date(),
                                observacion=observacion,
                                estado=estadoasesoria
                            )
                            recorrido.save(request)

                            # Creo la nueva cita
                            responsableservicio = ResponsableServicio.objects.filter(responsable=responsable, servicioresponsableservicio__servicio=servicio, status=True, desde__lte=fechaproximacita, hasta__gte=fechaproximacita)[0]

                            # Si el tipo de servicio es asesoría
                            if servicio.tipo == 1:
                                # Obtengo estado AGENDADO
                                estado = obtener_estado_solicitud(21, 1)

                                # Obtener secuencia de la cita
                                secuencia = secuencia_asesoria(1)

                                # Guardar la nueva cita
                                nuevacita = CitaAsesoria(
                                    tipo=realizaproximaacti,
                                    secuencia=secuencia,
                                    solicitante=solicitante,
                                    servicio=servicio,
                                    responsable=responsable,
                                    ubicacion=responsableservicio.ubicacion,
                                    bloque=responsableservicio.bloque,
                                    oficina=responsableservicio.oficina,
                                    piso=responsableservicio.piso,
                                    modalidad=modalidad,
                                    fecha=fechaproximacita,
                                    horainicio=turnocita.comienza,
                                    horafin=turnocita.termina,
                                    motivo=motivo,
                                    origen=2,
                                    estado=estado
                                )
                                nuevacita.save(request)

                                # Si la próxima cita es asesoría y se adjuntaron anexos
                                if nuevacita.tipo == 1:
                                    # Guarda detalle de anexos subidos por el responsable de investigación
                                    for nfila, descripcion in zip(nfilas_anexo, descripciones_anexo):
                                        anexocita = AnexoCitaAsesoria(
                                            citaasesoria=citaasesoria,
                                            descripcion=descripcion.strip(),
                                            propietario=2
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
                                    citaasesoria=nuevacita,
                                    fecha=datetime.now().date(),
                                    observacion="AGENDADA POR INVESTIGACIÓN",
                                    estado=estado
                                )
                                recorrido.save(request)

                                # Creo el historial de la cita
                                historialcita = HistorialCitaAsesoria(
                                    citaasesoria=nuevacita,
                                    servicio=nuevacita.servicio,
                                    responsable=nuevacita.responsable,
                                    modalidad=nuevacita.modalidad,
                                    fecha=nuevacita.fecha,
                                    horainicio=nuevacita.horainicio,
                                    horafin=nuevacita.horafin,
                                    observacion=nuevacita.observacion,
                                    estado=nuevacita.estado
                                )
                                historialcita.save(request)
                            else:
                                # Consultar la cita tipo gestión y actualizar la información
                                citagestion = CitaAsesoria.objects.get(status=True, responsable=responsable, tipo=2, fecha=fechaproximacita, horainicio=turnocita.comienza)
                                citagestion.solicitante = solicitante
                                citagestion.servicio = servicio
                                citagestion.responsable = responsable
                                citagestion.ubicacion = responsableservicio.ubicacion
                                citagestion.bloque = responsableservicio.bloque
                                citagestion.oficina = responsableservicio.oficina
                                citagestion.piso = responsableservicio.piso
                                citagestion.modalidad = modalidad
                                citagestion.motivo = motivo
                                citagestion.save(request)

                                # Actualizar recorrido
                                recorrido = RecorridoCitaAsesoria.objects.get(citaasesoria=citagestion, status=True)
                                recorrido.fecha = datetime.now().date()
                                recorrido.save(request)

                                # Actualizr el historial de la cita
                                historialcita = HistorialCitaAsesoria.objects.get(citaasesoria=citagestion, status=True)
                                historialcita.servicio = citagestion.servicio
                                historialcita.responsable = citagestion.responsable
                                historialcita.modalidad = citagestion.modalidad
                                historialcita.observacion = citagestion.observacion
                                historialcita.save(request)

                                nuevacita = citagestion

                            # Asignar ocupado al horario del responsable
                            horarioresponsable = HorarioResponsableServicio.objects.get(status=True, responsableservicio=responsableservicio, turno=turnocita, fecha=fechaproximacita)
                            if servicio.tipo == 1:
                                horarioresponsable.ocupado = True
                            else:
                                horarioresponsable.reutilizable = False
                            horarioresponsable.save()

                            # Actualizo el detalle de la asesoría
                            detalleasesoria.citaasesoriaproxima = nuevacita
                            detalleasesoria.save(request)

                            log(u'%s agregó cita para asesoría de investigación: %s' % (persona, nuevacita), request, "add")
                            if int(realizaproximaacti) == 1:
                                msgguardado = "Registro guardado con éxito. <br><br>Usted agendó una cita de asesoría para el servicio de <b>{}</b> el {} con <b>{}</b>".format(servicio.nombre, mensajehorario, responsableservicio.responsable.nombre_completo_inverso())
                            else:
                                msgguardado = "Registro guardado con éxito. <br><br>Usted agendó una actividad de gestión administrativa para el servicio de <b>{}</b> el {} con <b>{}</b>".format(servicio.nombre, mensajehorario, responsableservicio.responsable.nombre_completo_inverso())

                        # Activar si los turnos son de una hora. Si sobraron más de veinte minutos se debe crear una hora libre para el responsable
                        # if minutossob >= 20:
                        #     # Agregar horario disponible
                        #     responsableservicio = ResponsableServicio.objects.filter(status=True, responsable=persona, servicioresponsableservicio__servicio=citaasesoria.servicio, desde__lte=citaasesoria.fecha, hasta__gte=citaasesoria.fecha)[0]
                        #
                        #     horarioresponsable = HorarioResponsableServicio(
                        #         responsableservicio=responsableservicio,
                        #         turno=None,
                        #         dia=citaasesoria.fecha.weekday() + 1,
                        #         fecha=citaasesoria.fecha,
                        #         comienza=horafinase,
                        #         termina=citaasesoria.horafin,
                        #         ocupado=False,
                        #         habilitado=True,
                        #         horacompleta=False
                        #     )
                        #     horarioresponsable.save(request)
                    else:
                        # Agregar horario disponible en caso que no haya asisitido a la cita
                        responsableservicio = ResponsableServicio.objects.filter(status=True, responsable=persona, servicioresponsableservicio__servicio=citaasesoria.servicio, desde__lte=citaasesoria.fecha, hasta__gte=citaasesoria.fecha)[0]

                        horarioresponsable = HorarioResponsableServicio(
                            responsableservicio=responsableservicio,
                            turno=None,
                            dia=citaasesoria.fecha.weekday()+1,
                            fecha=citaasesoria.fecha,
                            comienza=citaasesoria.horainicio,
                            termina=citaasesoria.horafin,
                            ocupado=True,
                            habilitado=True,
                            reutilizable=False,
                            horacompleta=False
                        )
                        horarioresponsable.save(request)

                        # Crear una cita tipo gestión
                        # Obtengo estado AGENDADO
                        estado = obtener_estado_solicitud(21, 1)

                        # Obtener el servicio Gestión Administrativa
                        servicio = responsableservicio.servicio_gestion()

                        # Obtener la secuencia
                        secuencia = secuencia_asesoria(2)

                        # Guardar la nueva cita
                        nuevacita = CitaAsesoria(
                            tipo=2,
                            secuencia=secuencia,
                            solicitante=responsableservicio.responsable,
                            servicio=servicio,
                            responsable=responsableservicio.responsable,
                            ubicacion=responsableservicio.ubicacion,
                            bloque=responsableservicio.bloque,
                            oficina=responsableservicio.oficina,
                            piso=responsableservicio.piso,
                            modalidad=1,
                            fecha=citaasesoria.fecha,
                            horainicio=citaasesoria.horainicio,
                            horafin=citaasesoria.horafin,
                            motivo='GESTIONES ADMINISTRATIVAS',
                            horacompleta=False,
                            estado=estado
                        )
                        nuevacita.save(request)

                        # Creo el recorrido de la cita
                        recorrido = RecorridoCitaAsesoria(
                            citaasesoria=nuevacita,
                            fecha=datetime.now().date(),
                            observacion="AGENDADA POR INVESTIGACIÓN",
                            estado=estado
                        )
                        recorrido.save(request)

                        # Creo el historial de la cita
                        historialcita = HistorialCitaAsesoria(
                            citaasesoria=nuevacita,
                            servicio=nuevacita.servicio,
                            responsable=nuevacita.responsable,
                            modalidad=nuevacita.modalidad,
                            fecha=nuevacita.fecha,
                            horainicio=nuevacita.horainicio,
                            horafin=nuevacita.horafin,
                            observacion=nuevacita.observacion,
                            estado=nuevacita.estado
                        )
                        historialcita.save(request)

                    log(u'%s gestionó cita para asesoría de investigación: %s' % (persona, citaasesoria), request, "edit")

                    if not proxima:
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                    else:
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": msgguardado, "showSwal": True})
                else:
                    for k, v in f.errors.items():
                        raise NameError(k + ', ' + v[0])
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'serviciogestion':
            try:
                gestion = Gestion.objects.get(pk=request.POST['id'])
                lista = []
                if int(request.POST['tipo']) == 0:
                    servicios = ServicioGestion.objects.filter(gestion=gestion, status=True).order_by('tipo', 'nombre')
                else:
                    servicios = ServicioGestion.objects.filter(gestion=gestion, status=True, tipo=request.POST['tipo']).order_by('nombre')

                for servicio in servicios:
                    lista.append([servicio.id, servicio.nombre])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. [%s]" % msg})

        elif action == 'serviciogestionresponsable':
            try:
                gestion = Gestion.objects.get(pk=request.POST['idg'])
                responsable = Persona.objects.get(pk=request.POST['idr'])
                lista = []
                idsservicios = ServicioResponsableServicio.objects.values_list("servicio_id", flat=True).filter(status=True, vigente=True, responsableservicio__responsable=responsable)

                for servicio in ServicioGestion.objects.filter(pk__in=idsservicios, gestion=gestion, status=True, tipo=request.POST['tipo']).order_by('nombre'):
                    lista.append([servicio.id, servicio.nombre])

                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. [%s]" % msg})

        elif action == 'addcita':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                horarioresponsable = HorarioResponsableServicio.objects.get(pk=int(encrypt(request.POST['id'])))
                responsableservicio = horarioresponsable.responsableservicio

                # Verificar si el horario está disponible
                if horarioresponsable.ocupado:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La hora no se encuentra disponible", "showSwal": "True", "swalType": "warning"})

                # Ontener los valores del formulario
                tipo = int(request.POST['tiposervicioc'])
                modalidad = request.POST['modalidadc']
                servicio = ServicioGestion.objects.get(pk=request.POST['servicioc'])
                fecha = horarioresponsable.fecha
                motivo = request.POST['motivoc'].strip()

                if tipo == 1:
                    tiposolicitante = int(request.POST['tipopersonac'])
                    if tiposolicitante == 1:
                        solicitante = Profesor.objects.get(pk=request.POST['persona_select2']).persona.id
                    elif tiposolicitante == 2:
                        solicitante = Administrativo.objects.get(pk=request.POST['persona_select2']).persona.id
                    else:
                        solicitante = Inscripcion.objects.get(pk=request.POST['persona_select2']).persona.id
                else:
                    tiposolicitante = 2
                    solicitante = responsableservicio.responsable.id

                # Obtener fecha en letras
                dialetras = dia_semana_enletras_fecha(fecha)
                fechadialetras = dialetras + " " + str(fecha.day) + " de " + MESES_CHOICES[fecha.month - 1][1].capitalize() + " del " + str(fecha.year)
                mensajehorario = "<b>" + fechadialetras + "</b> en horario de <b>" + horarioresponsable.comienza.strftime('%H:%M') + " a " + horarioresponsable.termina.strftime('%H:%M') + "</b>"

                # Obtengo estado AGENDADO
                estado = obtener_estado_solicitud(21, 1)

                # Guardar la cita
                citaasesoria = CitaAsesoria(
                    tipo=tipo,
                    tiposolicitante=tiposolicitante,
                    solicitante_id=solicitante,
                    servicio=servicio,
                    responsable=responsableservicio.responsable,
                    ubicacion=responsableservicio.ubicacion,
                    bloque=responsableservicio.bloque,
                    oficina=responsableservicio.oficina,
                    piso=responsableservicio.piso,
                    modalidad=modalidad,
                    fecha=fecha,
                    horainicio=horarioresponsable.comienza,
                    horafin=horarioresponsable.termina,
                    motivo=motivo,
                    horacompleta=horarioresponsable.horacompleta,
                    origen=2,
                    estado=estado
                )
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

                # Asignar ocupado al horario del responsable
                horarioresponsable.ocupado = True
                horarioresponsable.save()

                # Notificar por e-mail
                if tipo == 1 and datetime.combine(citaasesoria.fecha, citaasesoria.horainicio) >= datetime.now():
                    # Notificar por e-mail al responsable
                    notificar_asesoria_investigacion(citaasesoria, "AGECIT", request)

                    # Notificar por e-mail al solicitante
                    notificar_asesoria_investigacion(citaasesoria, "AGECITSOL", request)

                if tipo == 1:
                    log(u'%s agregó cita para asesoría de investigación: %s' % (persona, citaasesoria), request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito. <br><br>Usted agendó una cita para el servicio de <b>{}</b> el {} con <b>{}</b>".format(servicio.nombre, mensajehorario, responsableservicio.responsable.nombre_completo_inverso()), "showSwal": True})
                else:
                    log(u'%s agregó actividad de gestión administrativa: %s' % (persona, citaasesoria), request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'finalizaractividad':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar la cita para asesoría
                citaasesoria = CitaAsesoria.objects.get(pk=int(encrypt(request.POST['id'])))

                # Obtengo estado FINALIZADO
                estado = obtener_estado_solicitud(21, 5)

                # Obtengo los valores del formulario
                observacion = request.POST['observacion'].strip()

                # Actualizar el registro de la cita
                citaasesoria.horainicioase = citaasesoria.horainicio
                citaasesoria.horafinase = citaasesoria.horafin
                citaasesoria.atraso = "00:00:00"
                citaasesoria.sobrante = "00:00:00"
                citaasesoria.asistio = True
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

                log(u'%s actualizó registro de cita para asesoría: %s' % (persona, citaasesoria), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'finalizaractividaddia':
            try:
                if 'fecha' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Obtengo estado FINALIZADO
                estado = obtener_estado_solicitud(21, 5)

                # Obtengo los valores del formulario
                observacion = request.POST['observacion'].strip()

                # Consultar las citas del día tipo gestión administrativas
                citasasesoria = CitaAsesoria.objects.filter(status=True, tipo=2, fecha=request.POST['fecha'], responsable=persona).order_by('horainicio')

                for citaasesoria in citasasesoria:
                    # Si la gestión no tiene como origen una asesoría
                    if not citaasesoria.asesoria_origen():
                        # Actualizar el registro de la cita
                        citaasesoria.horainicioase = citaasesoria.horainicio
                        citaasesoria.horafinase = citaasesoria.horafin
                        citaasesoria.atraso = "00:00:00"
                        citaasesoria.sobrante = "00:00:00"
                        citaasesoria.asistio = True
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

                        log(u'%s actualizó registro de cita para asesoría: %s' % (persona, citaasesoria), request, "edit")

                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registros actualizados con éxito", "showSwal": True})
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
                    # Obtener los valores de los detalles del formulario
                    nfilas_ca_anexo = json.loads(request.POST['lista_items1']) if 'lista_items1' in request.POST else []  # Números de filas que tienen lleno el campo archivo en detalle de anexos
                    nfilas_anexo = request.POST.getlist('nfila_anexo[]')  # Todos los número de filas del detalle de evidencias de anexo
                    idsreganexos = request.POST.getlist('idreganexo[]')  # Todos los ids de detalle de anexos
                    descripciones_anexos = request.POST.getlist('descripcion_anexo[]')  # Todas las descripciones detalle anexos
                    archivos_anexos = request.FILES.getlist('archivo_anexo[]')  # Todos los archivos detalle anexos
                    anexos_elim = json.loads(request.POST['lista_items2']) if 'lista_items2' in request.POST else [] # Ids registros de anexos borrados

                    nfilas_enlace = request.POST.getlist('nfila_enlace[]')  # Todos los número de filas del detalle de enlaces de anexo
                    idsregenlaces = request.POST.getlist('idregenlace[]')  # Todos los ids de detalle de enlaces
                    descripciones_enlaces = request.POST.getlist('descripcion_enlace[]')  # Todas las descripciones detalle enlaces
                    urls_enlaces = request.POST.getlist('url_enlace[]')  # Todas las urls detalle enlaces
                    enlaces_elim = json.loads(request.POST['lista_items3']) if 'lista_items3' in request.POST else [] # Ids registros de enlaces borrados

                    # Valido los archivos cargados de detalle de anexos
                    for nfila, archivo in zip(nfilas_ca_anexo, archivos_anexos):
                        descripcionarchivo = 'Anexos'
                        resp = validar_archivo(descripcionarchivo, archivo, variable_valor("TIPOS_ANEXOS_ASESORIAS_INV"), variable_valor("TAMANIO_ANEXOS_ASESORIAS_INV"))
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "{} en la fila # {}".format(resp["mensaje"], nfila['cfila']), "showSwal": "True", "swalType": "warning"})

                    # Guarda anexos de la cita
                    for idreg, nfila, descripcion in zip(idsreganexos, nfilas_anexo, descripciones_anexos):
                        # Si es registro nuevo
                        if int(idreg) == 0:
                            anexocita = AnexoCitaAsesoria(
                                tipo=1,
                                citaasesoria=citaasesoria,
                                descripcion=descripcion.strip(),
                                propietario=2
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

                    # Guarda enlaces de la cita
                    for idreg, nfila, descripcion, url in zip(idsregenlaces, nfilas_enlace, descripciones_enlaces, urls_enlaces):
                        # Si es registro nuevo
                        if int(idreg) == 0:
                            anexocita = AnexoCitaAsesoria(
                                tipo=2,
                                citaasesoria=citaasesoria,
                                descripcion=descripcion.strip(),
                                url=url.strip(),
                                propietario=2
                            )
                            anexocita.save(request)
                        else:
                            anexocita = AnexoCitaAsesoria.objects.get(pk=idreg)
                            anexocita.descripcion = descripcion.strip()
                            anexocita.url = url.strip()

                        anexocita.save(request)

                    # Elimino detalles de enlaces
                    if enlaces_elim:
                        for registro in enlaces_elim:
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

        elif action == 'delcita':
            try:
                # Consultar la cita para asesoría
                citaasesoria = CitaAsesoria.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que se pueda eliminar
                if not citaasesoria.puede_eliminar(persona):
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede eliminar el Registro", "showSwal": "True", "swalType": "warning"})

                # Elimino la cita
                citaasesoria.status = False
                citaasesoria.save(request)

                # Actualizo la hora como libre
                horarioresponsable = citaasesoria.horario_responsable_liberar()

                if horarioresponsable.tiposervicio == 2:
                    horarioresponsable.tiposervicio = 1

                horarioresponsable.ocupado = False
                horarioresponsable.save(request)

                log(u'%s eliminó cita para asesoría: %s' % (persona, citaasesoria), request, "del")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro eliminado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al eliminar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'cancelarcita':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar la cita para asesoría
                citaasesoria = CitaAsesoria.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que se pueda eliminar
                if not citaasesoria.puede_cancelar(persona):
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

                log(u'%s canceló registro de cita para asesoría: %s' % (persona, citaasesoria), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
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
                    fecha = datetime.strptime(request.POST['fechaproximacita'], '%Y-%m-%d').date()
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

                    # Verifico si la hora aún está disponible
                    if HorarioResponsableServicio.objects.values("id").filter(status=True, fecha=fecha, turno_id=idturno, habilitado=True, ocupado=False, responsableservicio__responsable=responsable, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True).exists() or HorarioResponsableServicio.objects.values("id").filter(status=True, fecha=fecha, turno_id=idturno, habilitado=True, reutilizable=True, responsableservicio__responsable=responsable, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True).exists():
                        # Eliminar la cita tipo gestión del responsable a quíen fue derivada la cita de asesoría
                        if CitaAsesoria.objects.values("id").filter(status=True, tipo=2, fecha=fecha, horainicio=turnocita.comienza, responsable=responsable).exists():
                            citagestion = CitaAsesoria.objects.get(status=True, tipo=2, fecha=fecha, horainicio=turnocita.comienza, responsable=responsable)
                            citagestion.status = False
                            citagestion.save(request)

                        # Actualizo la cita
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

                        responsableservicio = ResponsableServicio.objects.filter(status=True, responsable=responsable, servicioresponsableservicio__servicio=citaasesoria.servicio, desde__lte=citaasesoria.fecha, hasta__gte=citaasesoria.fecha)[0]

                        # Asignar ocupado al horario del responsable al cuál será reagendado
                        horarioresponsable = HorarioResponsableServicio.objects.get(status=True, responsableservicio=responsableservicio, turno=turnocita, fecha=fecha)
                        horarioresponsable.ocupado = True
                        horarioresponsable.save()

                        # Libero la hora que estaba ocupada anteriormente
                        horarioresponsableanterior.ocupado = False
                        horarioresponsableanterior.save(request)

                        log(u'%s re-agendó cita para asesoría de investigación: %s' % (persona, citaasesoria), request, "edit")
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

        elif action == 'derivarcita':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                f = ReagendamientoCitaAsesoriaForm(request.POST)

                if f.is_valid():
                    # Consultar la cita para asesoría
                    citaasesoria = CitaAsesoria.objects.get(pk=int(encrypt(request.POST['id'])))

                    # Obtener los valores del formulario
                    modalidad = f.cleaned_data['modalidad']
                    servicio = f.cleaned_data['servicio']
                    fecha = datetime.strptime(request.POST['fechaproximacita'], '%Y-%m-%d').date()
                    responsable = Persona.objects.get(pk=request.POST['idresponsable'])
                    idturno = request.POST['idturno']
                    observacion = request.POST['motivo'].strip()

                    # Obtengo estado DERIVADA
                    estado = obtener_estado_solicitud(21, 3)

                    # Consulto el horario actual de la cita
                    horarioresponsableanterior = citaasesoria.horario_responsable_liberar()

                    # Consultar turno
                    turnocita = TurnoCita.objects.get(pk=idturno)

                    # Obtener fecha en letras
                    dialetras = dia_semana_enletras_fecha(fecha)
                    fechadialetras = dialetras + " " + str(fecha.day) + " de " + MESES_CHOICES[fecha.month - 1][1].capitalize() + " del " + str(fecha.year)
                    mensajehorario = "<b>" + fechadialetras + "</b> en horario de <b>" + turnocita.comienza.strftime('%H:%M') + " a " + turnocita.termina.strftime('%H:%M') + "</b>"

                    # Verifico si la hora aún está disponible
                    if HorarioResponsableServicio.objects.values("id").filter(status=True, fecha=fecha, turno_id=idturno, habilitado=True, ocupado=False, responsableservicio__responsable=responsable, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True).exists() or HorarioResponsableServicio.objects.values("id").filter(status=True, fecha=fecha, turno_id=idturno, habilitado=True, reutilizable=True, responsableservicio__responsable=responsable, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True).exists():
                        # Eliminar la cita tipo gestión del responsable a quíen fue derivada la cita de asesoría
                        if CitaAsesoria.objects.values("id").filter(status=True, tipo=2, fecha=fecha, horainicio=turnocita.comienza, responsable=responsable).exists():
                            citagestion = CitaAsesoria.objects.get(status=True, tipo=2, fecha=fecha, horainicio=turnocita.comienza, responsable=responsable)
                            citagestion.status = False
                            citagestion.save(request)

                        # Actualizo la cita
                        citaasesoria.servicio = servicio
                        citaasesoria.responsable = responsable
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

                        responsableservicio = ResponsableServicio.objects.filter(status=True, responsable=responsable, servicioresponsableservicio__servicio=servicio, desde__lte=fecha, hasta__gte=fecha)[0]

                        # Asignar ocupado al horario del responsable al cuál será derivado
                        horarioresponsable = HorarioResponsableServicio.objects.get(status=True, responsableservicio=responsableservicio, turno=turnocita, fecha=fecha)
                        horarioresponsable.ocupado = True
                        horarioresponsable.save()

                        # Libero la hora que estaba ocupada anteriormente
                        horarioresponsableanterior.ocupado = False
                        horarioresponsableanterior.save(request)

                        log(u'%s derivó cita para asesoría de investigación: %s' % (persona, citaasesoria), request, "edit")
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito. <br><br>Usted derivó una cita para el servicio de <b>{}</b> el {} con <b>{}</b>".format(servicio.nombre, mensajehorario, responsableservicio.responsable.nombre_completo_inverso()), "showSwal": True})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No existen turnos disponibles para el día {}".format(mensajehorario), "showSwal": "True", "swalType": "warning"})
                else:
                    for k, v in f.errors.items():
                        raise NameError(k + ', ' + v[0])
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'cambioresponsable':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar la cita para asesoría
                citaasesoria = CitaAsesoria.objects.get(pk=int(encrypt(request.POST['id'])))

                # Obtener el dato del formulario y consultar el responsable
                nuevoresponsable = request.POST['nuevoresponsable']
                responsableservicio = ResponsableServicio.objects.get(pk=int(nuevoresponsable))

                # Actualizar el registro de la cita
                citaasesoria.responsable = responsableservicio.responsable
                citaasesoria.ubicacion = responsableservicio.ubicacion
                citaasesoria.bloque = responsableservicio.bloque
                citaasesoria.oficina = responsableservicio.oficina
                citaasesoria.piso = responsableservicio.piso
                citaasesoria.save(request)

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

                # Borrar actividad de gestión en caso de tener asignada en el mismo día y hora
                CitaAsesoria.objects.filter(status=True, tipo=2, responsable=citaasesoria.responsable, fecha=citaasesoria.fecha, horainicio=citaasesoria.horainicio).update(status=False)

                log(f'{persona} cambió responsable de la cita para asesoría {citaasesoria}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addenlaceatencion':
            try:
                persona_id = request.POST['persona_select2']
                tipo = request.POST['tipoherramienta']
                enlace = request.POST['enlace'].strip().lower()

                # Verificar que el enlace no lo tenga otra persona
                if EnlaceAtencionVirtualPersona.objects.values("id").filter(status=True, url=enlace).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El enlace de atención virtual ya ha sido asignada a otra persona", "showSwal": "True", "swalType": "warning"})

                # Verificar que no se repita el registro
                if EnlaceAtencionVirtualPersona.objects.values("id").filter(status=True, persona_id=persona_id).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La persona ya tiene asignada un enlace de atención virtual", "showSwal": "True", "swalType": "warning"})

                # Guardar el registro
                enlaceatencion = EnlaceAtencionVirtualPersona(
                    tipo=tipo,
                    persona_id=persona_id,
                    url=enlace
                )
                enlaceatencion.save(request)

                log(u'%s agregó enlace de atención virtual a persona: %s' % (persona, enlaceatencion), request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editenlaceatencion':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                persona_id = request.POST['personae_select2']
                tipo = request.POST['tipoherramientae']
                enlace = request.POST['enlacee'].strip().lower()

                # Verificar que el enlace no lo tenga otra persona
                if EnlaceAtencionVirtualPersona.objects.values("id").filter(status=True, url=enlace).exclude(pk=int(encrypt(request.POST['id']))).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El enlace de atención virtual ya ha sido asignada a otra persona", "showSwal": "True", "swalType": "warning"})

                # Verificar que no se repita el registro
                if EnlaceAtencionVirtualPersona.objects.values("id").filter(status=True, persona_id=persona_id).exclude(pk=int(encrypt(request.POST['id']))).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La persona ya tiene asignada un enlace de atención virtual", "showSwal": "True", "swalType": "warning"})

                # Consultar la cita para asesoría
                enlaceatencion = EnlaceAtencionVirtualPersona.objects.get(pk=int(encrypt(request.POST['id'])))

                # Actualizar el registro
                enlaceatencion.persona_id = persona_id
                enlaceatencion.tipo = tipo
                enlaceatencion.url = enlace
                enlaceatencion.save(request)

                log(u'%s editó enlace de atención virtual a persona: %s' % (persona, enlaceatencion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addservicio':
            try:
                idgestion = request.POST['gestion']
                nombre = request.POST['nombre'].strip().upper()
                abreviatura = request.POST['abreviatura'].strip().upper()
                tipo = request.POST['tipo']
                descripcion = request.POST['descripcion'].strip()

                # Verificar que no se repita el registro
                if ServicioGestion.objects.values("id").filter(status=True, gestion_id=idgestion, nombre=nombre).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El nombre del servicio ya existe", "showSwal": "True", "swalType": "warning"})

                if ServicioGestion.objects.values("id").filter(status=True, gestion_id=idgestion, abreviatura=abreviatura).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La abreviatura ya existe", "showSwal": "True", "swalType": "warning"})

                # Guardar el registro
                serviciogestion = ServicioGestion(
                    gestion_id=idgestion,
                    nombre=nombre,
                    descripcion=descripcion,
                    abreviatura=abreviatura,
                    tipo=tipo
                )
                serviciogestion.save(request)

                log(u'%s agregó servicio ofertado: %s' % (persona, serviciogestion), request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editservicio':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                idgestion = request.POST['gestione']
                nombre = request.POST['nombree'].strip().upper()
                abreviatura = request.POST['abreviaturae'].strip().upper()
                tipo = request.POST['tipoe']
                descripcion = request.POST['descripcione'].strip()

                # Verificar que no se repita el registro
                if ServicioGestion.objects.values("id").filter(status=True, gestion_id=idgestion, nombre=nombre).exclude(pk=int(encrypt(request.POST['id']))).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El nombre del servicio ya existe", "showSwal": "True", "swalType": "warning"})

                if ServicioGestion.objects.values("id").filter(status=True, gestion_id=idgestion, abreviatura=abreviatura).exclude(pk=int(encrypt(request.POST['id']))).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La abreviatura ya existe", "showSwal": "True", "swalType": "warning"})

                # Consultar el servicio
                serviciogestion = ServicioGestion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Actualizar el registro
                serviciogestion.gestion_id = idgestion
                serviciogestion.nombre = nombre
                serviciogestion.descripcion = descripcion
                serviciogestion.abreviatura = abreviatura
                serviciogestion.tipo = tipo
                serviciogestion.save(request)

                log(u'%s editó servicio ofertado: %s' % (persona, serviciogestion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addhorarioservicio':
            try:
                diasferiados = DIAS_FERIADOS

                responsable = Persona.objects.get(pk=request.POST['responsable']) if 'responsable' in request.POST else persona
                desde = datetime.strptime(request.POST['desde'], '%Y-%m-%d').date()
                hasta = datetime.strptime(request.POST['hasta'], '%Y-%m-%d').date()

                # Verifico que no tenga horario vigente
                if ResponsableServicio.objects.values("id").filter(status=True, vigente=True, responsable=responsable).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La persona ya cuenta con un horario de servicios vigente", "showSwal": "True", "swalType": "warning"})

                if desde > hasta:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin deber ser mayor o igual a la fecha inicio", "showSwal": "True", "swalType": "warning"})

                # Validar que al menos uno de los servicios sea de tipo gestión admin
                if not ServicioGestion.objects.values("id").filter(pk__in=request.POST.getlist('servicio'), tipo=2).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"Debe seleccionar al menos un servicio de gestión administrativa", "showSwal": "True", "swalType": "warning"})

                # Obtener los valores del detalle del horario
                dialunes = 'S' if 'dia1' in request.POST else 'N'
                tiposluns1 = int(request.POST['tiposervicios11']) if 'tiposervicios11' in request.POST else None
                tiposluns2 = int(request.POST['tiposervicios21']) if 'tiposervicios21' in request.POST else None
                turnoslunes = json.loads(request.POST['lista_items1'])
                diamartes = 'S' if 'dia2' in request.POST else 'N'
                tiposmars1 = int(request.POST['tiposervicios12']) if 'tiposervicios12' in request.POST else None
                tiposmars2 = int(request.POST['tiposervicios22']) if 'tiposervicios22' in request.POST else None
                turnosmartes = json.loads(request.POST['lista_items2'])
                diamiercoles = 'S' if 'dia3' in request.POST else 'N'
                tiposmies1 = int(request.POST['tiposervicios13']) if 'tiposervicios13' in request.POST else None
                tiposmies2 = int(request.POST['tiposervicios23']) if 'tiposervicios23' in request.POST else None
                turnosmiercoles = json.loads(request.POST['lista_items3'])
                diajueves = 'S' if 'dia4' in request.POST else 'N'
                tiposjues1 = int(request.POST['tiposervicios14']) if 'tiposervicios14' in request.POST else None
                tiposjues2 = int(request.POST['tiposervicios24']) if 'tiposervicios24' in request.POST else None
                turnosjueves = json.loads(request.POST['lista_items4'])
                diaviernes = 'S' if 'dia5' in request.POST else 'N'
                tiposvies1 = int(request.POST['tiposervicios15']) if 'tiposervicios15' in request.POST else None
                tiposvies2 = int(request.POST['tiposervicios25']) if 'tiposervicios25' in request.POST else None
                turnosviernes = json.loads(request.POST['lista_items5'])
                diasabado = 'S' if 'dia6' in request.POST else 'N'
                tipossabs1 = int(request.POST['tiposervicios16']) if 'tiposervicios16' in request.POST else None
                tipossabs2 = int(request.POST['tiposervicios26']) if 'tiposervicios26' in request.POST else None
                turnossabado = json.loads(request.POST['lista_items6'])
                diadomingo = 'S' if 'dia7' in request.POST else 'N'
                tiposdoms1 = int(request.POST['tiposervicios17']) if 'tiposervicios17' in request.POST else None
                tiposdoms2 = int(request.POST['tiposervicios27']) if 'tiposervicios27' in request.POST else None
                turnosdomingo = json.loads(request.POST['lista_items7'])

                # Guardar el responsable
                responsableservicio = ResponsableServicio(
                    responsable=responsable,
                    ubicacion_id=request.POST['ubicacion'],
                    bloque_id=request.POST['bloque'],
                    oficina=request.POST['oficina'].strip(),
                    piso=request.POST['piso'].strip(),
                    desde=desde,
                    hasta=hasta,
                    lunes=dialunes == 'S',
                    martes=diamartes == 'S',
                    miercoles=diamiercoles == 'S',
                    jueves=diajueves == 'S',
                    viernes=diaviernes == 'S',
                    sabado=diasabado == 'S',
                    domingo=diadomingo == 'S',
                    estado=1
                )
                responsableservicio.save(request)

                # Guardar los servicios del responsable
                for idservicio in request.POST.getlist('servicio'):
                    servicio = ServicioGestion.objects.get(pk=idservicio)

                    if servicio.tipo == 2:
                        visiblesolicitante = False
                    else:
                        visiblesolicitante = not Gestion.objects.values("id").filter(status=True, responsable=responsableservicio.responsable).exists()

                    servicioresponsable = ServicioResponsableServicio(
                        responsableservicio=responsableservicio,
                        servicio=servicio,
                        vigente=True,
                        visiblesolicitante=visiblesolicitante
                    )
                    servicioresponsable.save(request)

                # Guardar Turnos por día y Tipo de servicio del responsable
                for dia in range(1, 8):
                    # Guarda tipo de servicio por semana
                    if dia == 1: tiposervicio = tiposluns1
                    elif dia == 2: tiposervicio = tiposmars1
                    elif dia == 3: tiposervicio = tiposmies1
                    elif dia == 4: tiposervicio = tiposjues1
                    elif dia == 5: tiposervicio = tiposvies1
                    elif dia == 6: tiposervicio = tipossabs1
                    else: tiposervicio = tiposdoms1

                    if tiposervicio:
                        semana1 = TipoServicioSemanaResponsableServicio(
                            responsableservicio=responsableservicio,
                            semana=1,
                            dia=dia,
                            tipo=tiposervicio
                        )
                        semana1.save(request)

                    if dia == 1: tiposervicio = tiposluns2
                    elif dia == 2: tiposervicio = tiposmars2
                    elif dia == 3: tiposervicio = tiposmies2
                    elif dia == 4: tiposervicio = tiposjues2
                    elif dia == 5: tiposervicio = tiposvies2
                    elif dia == 6: tiposervicio = tipossabs2
                    else: tiposervicio = tiposdoms2

                    if tiposervicio:
                        semana2 = TipoServicioSemanaResponsableServicio(
                            responsableservicio=responsableservicio,
                            semana=2,
                            dia=dia,
                            tipo=tiposervicio
                        )
                        semana2.save(request)

                    if dia == 1: turnos = turnoslunes
                    elif dia == 2: turnos = turnosmartes
                    elif dia == 3: turnos = turnosmiercoles
                    elif dia == 4: turnos = turnosjueves
                    elif dia == 5: turnos = turnosviernes
                    elif dia == 6: turnos = turnossabado
                    else: turnos = turnosdomingo

                    # Guarda turno por día
                    for turno in turnos:
                        if turno["marcado"]:
                            turnodia = TurnoDiaResponsableServicio(
                                responsableservicio=responsableservicio,
                                dia=dia,
                                turno_id=turno["idturno"]
                            )
                            turnodia.save(request)

                # Guardar los horarios con las fechas que estén dentro del rango
                semana = 1
                fecha = desde
                while fecha <= hasta:
                    diasemana = fecha.weekday() + 1
                    turnos = ""
                    tiposervicio = ""

                    if dialunes == 'S' and diasemana == 1:
                        observacion = "DÍA FERIADO" if fecha in diasferiados else ""
                        habilitado = not fecha in diasferiados
                        turnos = turnoslunes
                        tiposervicio = tiposluns1 if semana == 1 else tiposluns2
                    elif diamartes == 'S' and diasemana == 2:
                        observacion = "DÍA FERIADO" if fecha in diasferiados else ""
                        habilitado = not fecha in diasferiados
                        turnos = turnosmartes
                        tiposervicio = tiposmars1 if semana == 1 else tiposmars2
                    elif diamiercoles == 'S' and diasemana == 3:
                        observacion = "DÍA FERIADO" if fecha in diasferiados else ""
                        habilitado = not fecha in diasferiados
                        turnos = turnosmiercoles
                        tiposervicio = tiposmies1 if semana == 1 else tiposmies2
                    elif diajueves == 'S' and diasemana == 4:
                        observacion = "DÍA FERIADO" if fecha in diasferiados else ""
                        habilitado = not fecha in diasferiados
                        turnos = turnosjueves
                        tiposervicio = tiposjues1 if semana == 1 else tiposjues2
                    elif diaviernes == 'S' and diasemana == 5:
                        observacion = "DÍA FERIADO" if fecha in diasferiados else ""
                        habilitado = not fecha in diasferiados
                        turnos = turnosviernes
                        tiposervicio = tiposvies1 if semana == 1 else tiposvies2
                    elif diasabado == 'S' and diasemana == 6:
                        observacion = "DÍA FERIADO" if fecha in diasferiados else ""
                        habilitado = not fecha in diasferiados
                        turnos = turnossabado
                        tiposervicio = tipossabs1 if semana == 1 else tipossabs2
                    elif diadomingo == 'S' and diasemana == 7:
                        observacion = "DÍA FERIADO" if fecha in diasferiados else ""
                        habilitado = not fecha in diasferiados
                        turnos = turnosdomingo
                        tiposervicio = tiposdoms1 if semana == 1 else tiposdoms2

                    # Guardo el horario
                    if turnos:
                        for turno in turnos:
                            if turno["marcado"]:
                                turno = TurnoCita.objects.get(pk=turno["idturno"])
                                horarioresponsable = HorarioResponsableServicio(
                                    responsableservicio=responsableservicio,
                                    tiposervicio=tiposervicio,
                                    turno=turno,
                                    dia=diasemana,
                                    fecha=fecha,
                                    comienza=turno.comienza,
                                    termina=turno.termina,
                                    ocupado=False,
                                    habilitado=habilitado,
                                    reutilizable=tiposervicio == 2,
                                    observacion=observacion
                                )
                                horarioresponsable.save()

                    if diasemana == 7:
                        semana = 2 if semana == 1 else 1

                    fecha = fecha + timedelta(days=1)

                log(u'%s agregó horario para servicios: %s' % (persona, responsableservicio), request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'edithorarioservicio':
            try:
                responsableservicio = ResponsableServicio.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verificar que se pueda editar
                if responsableservicio.estado == 2:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el Registro porque ya fue Aprobado", "showSwal": "True", "swalType": "warning"})

                diasferiados = DIAS_FERIADOS

                responsable = Persona.objects.get(pk=request.POST['responsable']) if 'responsable' in request.POST else persona

                desde = datetime.strptime(request.POST['desde'], '%Y-%m-%d').date()
                hasta = datetime.strptime(request.POST['hasta'], '%Y-%m-%d').date()

                # Verifico que no tenga horario vigente
                if ResponsableServicio.objects.values("id").filter(status=True, vigente=True, responsable=responsable).exclude(pk=int(encrypt(request.POST['id']))).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La persona ya cuenta con un horario de servicios vigente", "showSwal": "True", "swalType": "warning"})

                if desde > hasta:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin deber ser mayor o igual a la fecha inicio", "showSwal": "True", "swalType": "warning"})

                # Validar que al menos uno de los servicios sea de tipo gestión admin
                if not ServicioGestion.objects.values("id").filter(pk__in=request.POST.getlist('servicio'), tipo=2).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"Debe seleccionar al menos un servicio de gestión administrativa", "showSwal": "True", "swalType": "warning"})

                # Obtener los valores del detalle del horario
                dialunes = 'S' if 'dia1' in request.POST else 'N'
                tiposluns1 = int(request.POST['tiposervicios11']) if 'tiposervicios11' in request.POST else None
                tiposluns2 = int(request.POST['tiposervicios21']) if 'tiposervicios21' in request.POST else None
                turnoslunes = json.loads(request.POST['lista_items1'])
                diamartes = 'S' if 'dia2' in request.POST else 'N'
                tiposmars1 = int(request.POST['tiposervicios12']) if 'tiposervicios12' in request.POST else None
                tiposmars2 = int(request.POST['tiposervicios22']) if 'tiposervicios22' in request.POST else None
                turnosmartes = json.loads(request.POST['lista_items2'])
                diamiercoles = 'S' if 'dia3' in request.POST else 'N'
                tiposmies1 = int(request.POST['tiposervicios13']) if 'tiposervicios13' in request.POST else None
                tiposmies2 = int(request.POST['tiposervicios23']) if 'tiposervicios23' in request.POST else None
                turnosmiercoles = json.loads(request.POST['lista_items3'])
                diajueves = 'S' if 'dia4' in request.POST else 'N'
                tiposjues1 = int(request.POST['tiposervicios14']) if 'tiposervicios14' in request.POST else None
                tiposjues2 = int(request.POST['tiposervicios24']) if 'tiposervicios24' in request.POST else None
                turnosjueves = json.loads(request.POST['lista_items4'])
                diaviernes = 'S' if 'dia5' in request.POST else 'N'
                tiposvies1 = int(request.POST['tiposervicios15']) if 'tiposervicios15' in request.POST else None
                tiposvies2 = int(request.POST['tiposervicios25']) if 'tiposervicios25' in request.POST else None
                turnosviernes = json.loads(request.POST['lista_items5'])
                diasabado = 'S' if 'dia6' in request.POST else 'N'
                tipossabs1 = int(request.POST['tiposervicios16']) if 'tiposervicios16' in request.POST else None
                tipossabs2 = int(request.POST['tiposervicios26']) if 'tiposervicios26' in request.POST else None
                turnossabado = json.loads(request.POST['lista_items6'])
                diadomingo = 'S' if 'dia7' in request.POST else 'N'
                tiposdoms1 = int(request.POST['tiposervicios17']) if 'tiposervicios17' in request.POST else None
                tiposdoms2 = int(request.POST['tiposervicios27']) if 'tiposervicios27' in request.POST else None
                turnosdomingo = json.loads(request.POST['lista_items7'])

                # Actualizar el responsable
                responsableservicio.responsable = responsable
                responsableservicio.ubicacion_id = request.POST['ubicacion']
                responsableservicio.bloque_id = request.POST['bloque']
                responsableservicio.oficina = request.POST['oficina'].strip()
                responsableservicio.piso = request.POST['piso'].strip()
                responsableservicio.desde = desde
                responsableservicio.hasta = hasta
                responsableservicio.lunes = dialunes == 'S'
                responsableservicio.martes = diamartes == 'S'
                responsableservicio.miercoles = diamiercoles == 'S'
                responsableservicio.jueves = diajueves == 'S'
                responsableservicio.viernes = diaviernes == 'S'
                responsableservicio.sabado = diasabado == 'S'
                responsableservicio.domingo = diadomingo == 'S'
                responsableservicio.observacion = ''
                responsableservicio.estado = 1
                responsableservicio.save(request)

                # Guardar los servicios del responsable
                for idservicio in request.POST.getlist('servicio'):
                    servicio = ServicioGestion.objects.get(pk=idservicio)

                    if servicio.tipo == 2:
                        visiblesolicitante = False
                    else:
                        visiblesolicitante = not Gestion.objects.values("id").filter(status=True, responsable=responsableservicio.responsable).exists()

                    # Si no tiene servicio asignado, lo guardo
                    if not ServicioResponsableServicio.objects.values("id").filter(status=True, responsableservicio=responsableservicio, servicio=servicio).exists():
                        servicioresponsable = ServicioResponsableServicio(
                            responsableservicio=responsableservicio,
                            servicio=servicio,
                            vigente=True,
                            visiblesolicitante=visiblesolicitante
                        )
                        servicioresponsable.save(request)

                # Eliminar los servicios que hayan sido quitados de la lista
                ServicioResponsableServicio.objects.filter(status=True, responsableservicio=responsableservicio).exclude(servicio_id__in=request.POST.getlist('servicio')).update(status=False)

                # Guardar / Actualizar Turnos por día del responsable
                for dia in range(1, 8):
                    # Actualizo tipo de servicio por semana
                    # Semana 1
                    if dia == 1: tiposervicio = tiposluns1
                    elif dia == 2: tiposervicio = tiposmars1
                    elif dia == 3: tiposervicio = tiposmies1
                    elif dia == 4: tiposervicio = tiposjues1
                    elif dia == 5: tiposervicio = tiposvies1
                    elif dia == 6: tiposervicio = tipossabs1
                    else: tiposervicio = tiposdoms1

                    if tiposervicio:
                        semana1 = TipoServicioSemanaResponsableServicio.objects.get(responsableservicio=responsableservicio, semana=1, dia=dia, status=True)
                        semana1.tipo = tiposervicio
                        semana1.save(request)
                    else:
                        # Inactivo tipo de servicio por semana en caso de existir
                        TipoServicioSemanaResponsableServicio.objects.filter(responsableservicio=responsableservicio, semana=1, dia=dia, status=True).update(status=False)

                    # Semana 2
                    if dia == 1: tiposervicio = tiposluns2
                    elif dia == 2: tiposervicio = tiposmars2
                    elif dia == 3: tiposervicio = tiposmies2
                    elif dia == 4: tiposervicio = tiposjues2
                    elif dia == 5: tiposervicio = tiposvies2
                    elif dia == 6: tiposervicio = tipossabs2
                    else: tiposervicio = tiposdoms2

                    if tiposervicio:
                        semana2 = TipoServicioSemanaResponsableServicio.objects.get(responsableservicio=responsableservicio, semana=2, dia=dia, status=True)
                        semana2.tipo = tiposervicio
                        semana2.save(request)
                    else:
                        # Inactivo tipo de servicio por semana en caso de existir
                        TipoServicioSemanaResponsableServicio.objects.filter(responsableservicio=responsableservicio, semana=2, dia=dia, status=True).update(status=False)

                    # Proceso los turnos
                    if dia == 1: turnos = turnoslunes
                    elif dia == 2: turnos = turnosmartes
                    elif dia == 3: turnos = turnosmiercoles
                    elif dia == 4: turnos = turnosjueves
                    elif dia == 5: turnos = turnosviernes
                    elif dia == 6: turnos = turnossabado
                    else: turnos = turnosdomingo

                    for turno in turnos:
                        if turno["marcado"]:
                            # Si no existe lo creo
                            if not TurnoDiaResponsableServicio.objects.values("id").filter(status=True, responsableservicio=responsableservicio, dia=dia, turno_id=turno["idturno"]).exists():
                                turnodia = TurnoDiaResponsableServicio(
                                    responsableservicio=responsableservicio,
                                    dia=dia,
                                    turno_id=turno["idturno"]
                                )
                                turnodia.save(request)
                        else:
                            # Inactivo cada turno en caso de existir
                            TurnoDiaResponsableServicio.objects.filter(status=True, responsableservicio=responsableservicio, dia=dia, turno_id=turno["idturno"]).update(status=False)

                # Guardar los horarios con las fechas que estén dentro del rango
                semana = 1
                fecha = desde
                while fecha <= hasta:
                    diasemana = fecha.weekday() + 1
                    turnos = ""
                    tiposervicio = ""

                    if diasemana == 1:
                        observacion = "DÍA FERIADO" if fecha in diasferiados else ""
                        habilitado = not fecha in diasferiados
                        turnos = turnoslunes
                        tiposervicio = tiposluns1 if semana == 1 else tiposluns2
                    elif diasemana == 2:
                        observacion = "DÍA FERIADO" if fecha in diasferiados else ""
                        habilitado = not fecha in diasferiados
                        turnos = turnosmartes
                        tiposervicio = tiposmars1 if semana == 1 else tiposmars2
                    elif diasemana == 3:
                        observacion = "DÍA FERIADO" if fecha in diasferiados else ""
                        habilitado = not fecha in diasferiados
                        turnos = turnosmiercoles
                        tiposervicio = tiposmies1 if semana == 1 else tiposmies2
                    elif diasemana == 4:
                        observacion = "DÍA FERIADO" if fecha in diasferiados else ""
                        habilitado = not fecha in diasferiados
                        turnos = turnosjueves
                        tiposervicio = tiposjues1 if semana == 1 else tiposjues2
                    elif diasemana == 5:
                        observacion = "DÍA FERIADO" if fecha in diasferiados else ""
                        habilitado = not fecha in diasferiados
                        turnos = turnosviernes
                        tiposervicio = tiposvies1 if semana == 1 else tiposvies2
                    elif diasemana == 6:
                        observacion = "DÍA FERIADO" if fecha in diasferiados else ""
                        habilitado = not fecha in diasferiados
                        turnos = turnossabado
                        tiposervicio = tipossabs1 if semana == 1 else tipossabs2
                    else:
                        observacion = "DÍA FERIADO" if fecha in diasferiados else ""
                        habilitado = not fecha in diasferiados
                        turnos = turnosdomingo
                        tiposervicio = tiposdoms1 if semana == 1 else tiposdoms2

                    # Guardo el horario
                    for turno in turnos:
                        if turno["marcado"]:
                            turno = TurnoCita.objects.get(pk=turno["idturno"])
                            # Si no existe creo el registro
                            if not HorarioResponsableServicio.objects.values("id").filter(status=True, responsableservicio=responsableservicio, turno=turno, fecha=fecha).exists():
                                horarioresponsable = HorarioResponsableServicio(
                                    responsableservicio=responsableservicio,
                                    tiposervicio=tiposervicio,
                                    turno=turno,
                                    dia=diasemana,
                                    fecha=fecha,
                                    comienza=turno.comienza,
                                    termina=turno.termina,
                                    ocupado=False,
                                    habilitado=habilitado,
                                    reutilizable=tiposervicio == 2,
                                    observacion=observacion
                                )
                                horarioresponsable.save()
                            else:
                                # Consultar y actualizar tipo de servicio
                                horarioresponsable = HorarioResponsableServicio.objects.get(status=True, responsableservicio=responsableservicio, turno=turno, fecha=fecha)
                                horarioresponsable.tiposervicio = tiposervicio
                                horarioresponsable.reutilizable = tiposervicio == 2
                                horarioresponsable.save(request)
                        else:
                            # Inactivo el horario en caso de existir y no haber sido reservado
                            HorarioResponsableServicio.objects.filter(status=True, responsableservicio=responsableservicio, turno_id=turno["idturno"], fecha=fecha).update(status=False)

                    if diasemana == 7:
                        semana = 2 if semana == 1 else 1

                    fecha = fecha + timedelta(days=1)

                log(u'%s editó horario para servicios: %s' % (persona, responsableservicio), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'aprobarhorario':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar el horario
                responsableservicio = ResponsableServicio.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que se pueda aprobar
                if not responsableservicio.puede_aprobar():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el Registro debido que ya existen citas registradas", "showSwal": "True", "swalType": "warning"})

                # Actualizar el registro
                responsableservicio.observacion = request.POST['observacion'].strip() if 'observacion' in request.POST else ''
                responsableservicio.estado = request.POST['estado']
                responsableservicio.save(request)

                # Si es APROBADO creo la agenda con gestiones administrativas
                if int(request.POST['estado']) == 2:
                    # Obtengo estado AGENDADO
                    estado = obtener_estado_solicitud(21, 1)

                    # Obtener el servicio Gestión Administrativa
                    servicio = responsableservicio.servicio_gestion()

                    # Crear la agenda con tipo gestión administrativa
                    for horarioresponsable in responsableservicio.horario_gestion_libre():
                        secuencia = secuencia_asesoria(2)
                        citaasesoria = CitaAsesoria(
                            tipo=2,
                            secuencia=secuencia,
                            solicitante=responsableservicio.responsable,
                            servicio=servicio,
                            responsable=responsableservicio.responsable,
                            ubicacion=responsableservicio.ubicacion,
                            bloque=responsableservicio.bloque,
                            oficina=responsableservicio.oficina,
                            piso=responsableservicio.piso,
                            modalidad=1,
                            fecha=horarioresponsable.fecha,
                            horainicio=horarioresponsable.comienza,
                            horafin=horarioresponsable.termina,
                            motivo='GESTIONES ADMINISTRATIVAS',
                            horacompleta=horarioresponsable.horacompleta,
                            origen=2,
                            estado=estado
                        )
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

                        # Asignar ocupado al horario del responsable
                        horarioresponsable.ocupado = True
                        horarioresponsable.save()

                log(u'{} {} horario para servicios: {}'.format(persona, 'aprobó' if responsableservicio.estado == 2 else 'registro novedades en', responsableservicio), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'servicioasignado':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar el horario
                responsableservicio = ResponsableServicio.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que se pueda finalizar vigencia
                if not responsableservicio.puede_editar_servicios_asignados():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el Registro debido que ya no tiene vigencia", "showSwal": "True", "swalType": "warning"})

                # Obtener los valores de los detalles del formulario
                servicios = json.loads(request.POST['lista_items3'])  # Lista de servicios

                # Guardar y/o actualizar los servicios asignados
                for servicio in servicios:
                    if not responsableservicio.servicios().filter(servicio_id=servicio["idservicio"]).exists():
                        servicioasignado = ServicioResponsableServicio(
                            responsableservicio=responsableservicio,
                            servicio_id=servicio["idservicio"],
                            vigente=servicio["vigente"] == 'S',
                            visiblesolicitante=servicio["visible"] == 'S'
                        )
                    else:
                        servicioasignado = responsableservicio.servicios().filter(servicio_id=servicio["idservicio"])[0]
                        servicioasignado.vigente = servicio["vigente"] == 'S'
                        servicioasignado.visiblesolicitante = servicio["visible"] == 'S'

                    servicioasignado.save(request)

                log(f'{persona} actualizó los servicios asignados al horario {responsableservicio}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'finalizarvigencia':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar el horario
                responsableservicio = ResponsableServicio.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que se pueda finalizar vigencia
                if not responsableservicio.puede_finalizar_vigencia():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el Registro debido que ya no tiene vigencia", "showSwal": "True", "swalType": "warning"})

                # Actualizar el registro
                responsableservicio.observacion = request.POST['observacionfv'].strip()
                responsableservicio.vigente = False
                responsableservicio.finvigencia = datetime.now().date()
                responsableservicio.save(request)

                # Borrar las gestiones administrativas existentes de la fecha actual en adelante
                CitaAsesoria.objects.filter(status=True, tipo=2, responsable=responsableservicio.responsable, fecha__gte=datetime.now().date()).update(status=False, observacion='FIN DE VIGENCIA DE HORARIO')

                log(f'{persona} finalizó la vigencia del horario para servicios {responsableservicio}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'reportegeneral':
            try:
                desde = datetime.strptime(request.POST['desde'], '%Y-%m-%d').date()
                hasta = datetime.strptime(request.POST['hasta'], '%Y-%m-%d').date()
                tipovista = tipo_vista_gestion_asesoria(persona)
                filtro = Q(status=True, tipo=1, fecha__gte=desde, fecha__lte=hasta)

                if tipovista == 'RG':
                    filtro = filtro & (Q(servicio__gestion__responsable=persona))
                elif tipovista == 'RS':
                    filtro = filtro & (Q(responsable=persona))

                citasasesorias = CitaAsesoria.objects.filter(filtro).order_by('-fecha', '-horainicio')

                if not citasasesorias:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No existen registros de citas para asesorías en ese renago de fechas", "showSwal": "True", "swalType": "warning"})

                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'postgrado'))
                nombrearchivo = "LISTADO_GENERAL_CITAS_ASESORIAS_INVESTIGACION_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xlsx"

                # Create un nuevo archivo de excel y le agrega una hoja
                workbook = xlsxwriter.Workbook(output_folder + '/' + nombrearchivo)
                ws = workbook.add_worksheet("Listado")

                fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])
                fceldageneral = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdageneral"])
                ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
                fceldafechaDMA = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdafechaDMA"])
                fceldahora = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdahora"])

                ws.merge_range(0, 0, 0, 15, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo1)
                ws.merge_range(1, 0, 1, 15, 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADO', ftitulo1)
                ws.merge_range(2, 0, 2, 15, 'FACULTAD DE INVESTIGACIÓN', ftitulo1)
                ws.merge_range(3, 0, 3, 15, 'ESCUELA DE FORMACIÓN EN INVESTIGACIÓN', ftitulo1)
                ws.merge_range(4, 0, 4, 15, 'LISTADO GENERAL DE CITAS PARA ASESORÍAS EN INVESTIGACIÓN', ftitulo1)

                columns = [
                    (u"DÍA", 12),
                    (u"FECHA", 12),
                    (u"HORA", 12),
                    (u"MODALIDAD", 12),
                    (u"SERVICIO", 25),
                    (u"RESPONSABLE", 40),
                    (u"TIPO SOLICITANTE", 15),
                    (u"SOLICITANTE", 40),
                    (u"MOTIVO", 40),
                    (u"ESTADO", 13),
                    (u"ASISTIÓ", 11),
                    (u"OBSERVACIÓN", 40),
                    (u"HORA INICIO ASESORÍA", 12),
                    (u"HORA FIN ASESORÍA", 12),
                    (u"OBSERVACIÓN ASESORÍA", 40),
                    (u"CONTINÚA", 11)
                ]

                row_num = 6
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                    ws.set_column(col_num, col_num, columns[col_num][1])

                row_num = 7

                for cita in citasasesorias:
                    if cita.estado.valor == 5:
                        asistio = "SI" if cita.asistio else "NO"
                    else:
                        asistio = ""

                    ws.write(row_num, 0, dia_semana_enletras_fecha(cita.fecha), fceldageneral)
                    ws.write(row_num, 1, cita.fecha, fceldafechaDMA)
                    ws.write(row_num, 2, cita.horainicio, fceldahora)
                    ws.write(row_num, 3, cita.get_modalidad_display().title(), fceldageneral)
                    ws.write(row_num, 4, cita.servicio.nombre.title(), fceldageneral)
                    ws.write(row_num, 5, cita.responsable.nombre_completo_inverso().title(), fceldageneral)
                    ws.write(row_num, 6, cita.get_tiposolicitante_display().title(), fceldageneral)
                    ws.write(row_num, 7, cita.solicitante.nombre_completo_inverso().title(), fceldageneral)
                    ws.write(row_num, 8, cita.motivo, fceldageneral)
                    ws.write(row_num, 9, cita.estado.descripcion.title(), fceldageneral)
                    ws.write(row_num, 10, asistio.title(), fceldageneral)
                    ws.write(row_num, 11, cita.observacion if asistio == 'NO' else '', fceldageneral)

                    if asistio == 'SI':
                        asesoria = cita.detalle_asesoria()
                        ws.write(row_num, 12, asesoria.comienzo, fceldahora)
                        ws.write(row_num, 13, asesoria.fin, fceldahora)
                        ws.write(row_num, 14, asesoria.observacion, fceldageneral)
                        ws.write(row_num, 15, "Si" if asesoria.proxima else "No", fceldageneral)
                    else:
                        ws.write(row_num, 12, "", fceldageneral)
                        ws.write(row_num, 13, "", fceldageneral)
                        ws.write(row_num, 14, "", fceldageneral)
                        ws.write(row_num, 15, "", fceldageneral)

                    row_num += 1

                workbook.close()

                ruta = "media/postgrado/" + nombrearchivo
                return JsonResponse({'result': 'ok', 'archivo': ruta})
            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar el reporte. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Solicitud incorrecta.", "showSwal": "True", "swalType": "error"})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'cargaragenda':
                try:
                    idgest, idserv, idresp, estado = request.GET.get('idgest', ''), request.GET.get('idserv', ''), request.GET.get('idresp', ''), request.GET.get('estado', '')
                    anio, semana, tipovista, tipomovimiento = int(request.GET.get('anio', '0')), int(request.GET.get('semana', '0')), request.GET.get('tv', ''), request.GET.get('tm', '')

                    if tipomovimiento != '':
                        if tipomovimiento == 'ant':
                            semana = semana - 1
                            if semana < 1:
                                anio = anio - 1
                                semana = 52
                        else:
                            semana = semana + 1
                            if semana > 52:
                                anio = anio + 1
                                semana = 1

                    fechainicio, fechafin = getdaterangefromweek(anio, semana)

                    turnos = TurnoCita.objects.filter(status=True, vigente=True, tipo=1).order_by('comienza')

                    calendario = []
                    fecha = fechainicio
                    while fecha <= fechafin:
                        detalles = []
                        citas = None
                        libres = None
                        pendientesgest = 0

                        # Buscar las horas libres
                        if estado in ['', '6']:
                            if tipovista in ['CI', 'SL']:
                                if not idresp:
                                    libres = HorarioResponsableServicio.objects.filter(status=True, fecha=fecha, ocupado=False, habilitado=True, responsableservicio__estado=2, responsableservicio__vigente=True).distinct().order_by('responsableservicio__servicioresponsableservicio__servicio__gestion__nombre', 'responsableservicio__responsable__apellido1', 'responsableservicio__responsable__apellido2', 'responsableservicio__responsable__nombres')
                                else:
                                    libres = HorarioResponsableServicio.objects.filter(status=True, fecha=fecha, ocupado=False, habilitado=True, responsableservicio__estado=2, responsableservicio__vigente=True, responsableservicio__responsable_id=idresp).distinct().order_by('responsableservicio__servicioresponsableservicio__servicio__gestion__nombre', 'responsableservicio__responsable__apellido1', 'responsableservicio__responsable__apellido2', 'responsableservicio__responsable__nombres')
                            elif tipovista == 'RG':
                                idgestiones = Gestion.objects.values_list("id", flat=True).filter(status=True, responsable=persona)
                                if not idresp:
                                    libres = HorarioResponsableServicio.objects.filter(status=True, fecha=fecha, ocupado=False, habilitado=True, responsableservicio__estado=2, responsableservicio__vigente=True, responsableservicio__servicioresponsableservicio__servicio__gestion__id__in=idgestiones).distinct().order_by('responsableservicio__servicioresponsableservicio__servicio__gestion__nombre', 'responsableservicio__responsable__apellido1', 'responsableservicio__responsable__apellido2', 'responsableservicio__responsable__nombres')
                                else:
                                    libres = HorarioResponsableServicio.objects.filter(status=True, fecha=fecha, ocupado=False, habilitado=True, responsableservicio__estado=2, responsableservicio__vigente=True, responsableservicio__responsable_id=idresp, responsableservicio__servicioresponsableservicio__servicio__gestion__id__in=idgestiones).distinct().order_by('responsableservicio__servicioresponsableservicio__servicio__gestion__nombre', 'responsableservicio__responsable__apellido1', 'responsableservicio__responsable__apellido2', 'responsableservicio__responsable__nombres')
                            elif tipovista == 'RS':
                                libres = HorarioResponsableServicio.objects.filter(status=True, fecha=fecha, ocupado=False, habilitado=True, responsableservicio__estado=2, responsableservicio__vigente=True, responsableservicio__responsable=persona).distinct().order_by('responsableservicio__servicioresponsableservicio__servicio__gestion__nombre', 'responsableservicio__responsable__apellido1', 'responsableservicio__responsable__apellido2', 'responsableservicio__responsable__nombres')

                        # Buscar las citas agendadas
                        if estado in ['', '1', '5']:
                            if tipovista in ['CI', 'SL']:
                                if estado == '':
                                    if not idresp:
                                        citas = CitaAsesoria.objects.filter(status=True, fecha=fecha).exclude(estado__valor=4).order_by('horainicio', 'servicio__gestion__nombre', 'servicio__nombre', 'responsable__apellido1', 'responsable__apellido2', 'responsable__nombres')
                                    else:
                                        citas = CitaAsesoria.objects.filter(status=True, fecha=fecha, responsable_id=idresp).exclude(estado__valor=4).order_by('horainicio', 'servicio__gestion__nombre', 'servicio__nombre', 'responsable__apellido1', 'responsable__apellido2', 'responsable__nombres')
                                else:
                                    if not idresp:
                                        citas = CitaAsesoria.objects.filter(status=True, fecha=fecha, estado__valor=estado).order_by('horainicio', 'servicio__gestion__nombre', 'servicio__nombre', 'responsable__apellido1', 'responsable__apellido2', 'responsable__nombres')
                                    else:
                                        citas = CitaAsesoria.objects.filter(status=True, fecha=fecha, estado__valor=estado, responsable_id=idresp).order_by('horainicio', 'servicio__gestion__nombre', 'servicio__nombre', 'responsable__apellido1', 'responsable__apellido2', 'responsable__nombres')

                            elif tipovista == 'RG':
                                idgestiones = Gestion.objects.values_list("id", flat=True).filter(status=True, responsable=persona)
                                if estado == '':
                                    if not idresp:
                                        citas = CitaAsesoria.objects.filter(status=True, fecha=fecha, servicio__gestion__id__in=idgestiones).exclude(estado__valor=4).order_by('horainicio', 'servicio__gestion__nombre', 'servicio__nombre', 'responsable__apellido1', 'responsable__apellido2', 'responsable__nombres')
                                    else:
                                        citas = CitaAsesoria.objects.filter(status=True, fecha=fecha, responsable_id=idresp, servicio__gestion__id__in=idgestiones).exclude(estado__valor=4).order_by('horainicio', 'servicio__gestion__nombre', 'servicio__nombre', 'responsable__apellido1', 'responsable__apellido2', 'responsable__nombres')
                                else:
                                    if not idresp:
                                        citas = CitaAsesoria.objects.filter(status=True, fecha=fecha, estado__valor=estado, servicio__gestion__id__in=idgestiones).order_by('horainicio', 'servicio__gestion__nombre', 'servicio__nombre', 'responsable__apellido1', 'responsable__apellido2', 'responsable__nombres')
                                    else:
                                        citas = CitaAsesoria.objects.filter(status=True, fecha=fecha, estado__valor=estado, responsable_id=idresp, servicio__gestion__id__in=idgestiones).order_by('horainicio', 'servicio__gestion__nombre', 'servicio__nombre', 'responsable__apellido1', 'responsable__apellido2', 'responsable__nombres')

                            elif tipovista == 'RS':
                                if estado == '':
                                    citas = CitaAsesoria.objects.filter(status=True, fecha=fecha, responsable=persona).exclude(estado__valor=4).order_by('horainicio', 'servicio__nombre')
                                else:
                                    citas = CitaAsesoria.objects.filter(status=True, fecha=fecha, estado__valor=estado, responsable=persona).order_by('horainicio', 'servicio__nombre')

                            # if int(idserv) > 0:
                            #     citas = citas.filter(servicio_id=idserv)
                            # elif int(idserv) == 0:
                            #     citas = citas.exclude(tipo=2)

                        # Si existen citas agendadas u horas libres debo armar la agenda combinada
                        if citas or libres:
                            if libres:
                                for horario in libres:
                                    # Si no se filtra por servicio específico
                                    if int(idserv) < 1:
                                        registro = {
                                            "idhorario": horario.id,
                                            "hora": horario.comienza,
                                            "horaini": horario.comienza.strftime('%H:%M'),
                                            "horafin": horario.termina.strftime('%H:%M'),
                                            "estado": "LIB",
                                            "gestion": horario.responsableservicio.mi_gestion().nombre,
                                            "abreviaturagest": horario.responsableservicio.mi_gestion().abreviatura,
                                            "servicio": "Por Definir<br>Servicio" if horario.horacompleta else "Por Definir Servicio",
                                            "abreviaturaserv": "P.D.S",
                                            "solicitante": "Hora<br>Disponible" if horario.horacompleta else "Hora Disponible",
                                            "idresponsable": horario.responsableservicio.responsable.id,
                                            "responsable": horario.responsableservicio.responsable.nombre_completo_inverso(),
                                            "modalidad:": "",
                                            "asistio": "",
                                            "horacompleta": "S" if horario.horacompleta else "N",
                                            "fechapasada": "N" if datetime.now().date() <= fecha else "S",
                                            "orden": 2
                                        }
                                    else:
                                        registro = {
                                            "hora": horario.comienza,
                                            "horaini": horario.comienza.strftime('%H:%M'),
                                            "horafin": horario.termina.strftime('%H:%M'),
                                            "idresponsable": 0,
                                            "estado": "NDI",
                                            "orden": 1
                                        }
                                    detalles.append(registro)

                            if citas:
                                for cita in citas:
                                    if cita.estado.valor in [1, 2, 3]:
                                        estadocita = "PEN"
                                        if cita.tipo == 2 and not cita.asesoria_origen():
                                            pendientesgest += 1
                                    elif cita.estado.valor == 5:
                                        estadocita = "FIN"
                                    else:
                                        estadocita = "ANU"

                                    if cita.tipo == 1:
                                        mostrarmodalgest = "N"
                                    else:
                                        mostrarmodalgest = "N" if cita.asesoria() else "S"

                                    # Todos los registros
                                    if int(idserv) == -1:
                                        registro = {
                                            "id": cita.id,
                                            "cita": cita,
                                            "hora": cita.horainicio,
                                            "tipo": cita.tipo,
                                            "horaini": cita.horainicio.strftime('%H:%M'),
                                            "horafin": cita.horafin.strftime('%H:%M'),
                                            "estado": estadocita,
                                            "gestion": cita.servicio.gestion.nombre,
                                            "abreviaturagest": cita.servicio.gestion.abreviatura,
                                            "servicio": cita.servicio.nombre,
                                            "abreviaturaserv": cita.servicio.abreviatura,
                                            "solicitante": cita.solicitante.nombre_completo_inverso(),
                                            "idresponsable": cita.responsable.id,
                                            "responsable": cita.responsable.nombre_completo_inverso(),
                                            "idmodalidad": cita.modalidad,
                                            "modalidad": cita.get_modalidad_display(),
                                            "abreviaturamod": cita.get_modalidad_display()[:4],
                                            "asistio": "S" if cita.asistio else "N",
                                            "textoasis": ("Asistió" if cita.asistio else "No Asistió") if cita.tipo == 1 else "Realizada",
                                            "abreviaturaasis": "A" if cita.asistio else "NA",
                                            "horacompleta": "S" if cita.horacompleta else "N",
                                            "fechapasada": "N" if datetime.now().date() <= fecha else "S",
                                            "puedegestionar": "S" if cita.puede_gestionar(persona) else "N",
                                            "mostrarmodalgest": mostrarmodalgest,
                                            "asesoriaorigen": cita.asesoria_origen(),
                                            "urlservirtual": url_atencion_virtual(cita.responsable),
                                            "orden": 1
                                        }
                                    elif int(idserv) == 0: # Todos excepto gestión
                                        if cita.tipo == 1:
                                            registro = {
                                                "id": cita.id,
                                                "cita": cita,
                                                "hora": cita.horainicio,
                                                "tipo": cita.tipo,
                                                "horaini": cita.horainicio.strftime('%H:%M'),
                                                "horafin": cita.horafin.strftime('%H:%M'),
                                                "estado": estadocita,
                                                "gestion": cita.servicio.gestion.nombre,
                                                "abreviaturagest": cita.servicio.gestion.abreviatura,
                                                "servicio": cita.servicio.nombre,
                                                "abreviaturaserv": cita.servicio.abreviatura,
                                                "solicitante": cita.solicitante.nombre_completo_inverso(),
                                                "idresponsable": cita.responsable.id,
                                                "responsable": cita.responsable.nombre_completo_inverso(),
                                                "idmodalidad": cita.modalidad,
                                                "modalidad": cita.get_modalidad_display(),
                                                "abreviaturamod": cita.get_modalidad_display()[:4],
                                                "asistio": "S" if cita.asistio else "N",
                                                "textoasis": ("Asistió" if cita.asistio else "No Asistió") if cita.tipo == 1 else "Realizada",
                                                "abreviaturaasis": "A" if cita.asistio else "NA",
                                                "horacompleta": "S" if cita.horacompleta else "N",
                                                "fechapasada": "N" if datetime.now().date() <= fecha else "S",
                                                "puedegestionar": "S" if cita.puede_gestionar(persona) else "N",
                                                "mostrarmodalgest": mostrarmodalgest,
                                                "asesoriaorigen": cita.asesoria_origen(),
                                                "urlservirtual": url_atencion_virtual(cita.responsable),
                                                "orden": 1
                                            }
                                        else:
                                            registro = {
                                                "hora": cita.horainicio,
                                                "horaini": cita.horainicio.strftime('%H:%M'),
                                                "horafin": cita.horafin.strftime('%H:%M'),
                                                "idresponsable": 0,
                                                "estado": "NDI",
                                                "orden": 1
                                            }
                                    else: # Por tipo de servicio en específico
                                        if cita.servicio.id == int(idserv):
                                            registro = {
                                                "id": cita.id,
                                                "cita": cita,
                                                "hora": cita.horainicio,
                                                "tipo": cita.tipo,
                                                "horaini": cita.horainicio.strftime('%H:%M'),
                                                "horafin": cita.horafin.strftime('%H:%M'),
                                                "estado": estadocita,
                                                "gestion": cita.servicio.gestion.nombre,
                                                "abreviaturagest": cita.servicio.gestion.abreviatura,
                                                "servicio": cita.servicio.nombre,
                                                "abreviaturaserv": cita.servicio.abreviatura,
                                                "solicitante": cita.solicitante.nombre_completo_inverso(),
                                                "idresponsable": cita.responsable.id,
                                                "responsable": cita.responsable.nombre_completo_inverso(),
                                                "idmodalidad": cita.modalidad,
                                                "modalidad": cita.get_modalidad_display(),
                                                "abreviaturamod": cita.get_modalidad_display()[:4],
                                                "asistio": "S" if cita.asistio else "N",
                                                "textoasis": ("Asistió" if cita.asistio else "No Asistió") if cita.tipo == 1 else "Realizada",
                                                "abreviaturaasis": "A" if cita.asistio else "NA",
                                                "horacompleta": "S" if cita.horacompleta else "N",
                                                "fechapasada": "N" if datetime.now().date() <= fecha else "S",
                                                "puedegestionar": "S" if cita.puede_gestionar(persona) else "N",
                                                "mostrarmodalgest": mostrarmodalgest,
                                                "asesoriaorigen": cita.asesoria_origen(),
                                                "urlservirtual": url_atencion_virtual(cita.responsable),
                                                "orden": 1
                                            }
                                        else:
                                            registro = {
                                                "hora": cita.horainicio,
                                                "horaini": cita.horainicio.strftime('%H:%M'),
                                                "horafin": cita.horafin.strftime('%H:%M'),
                                                "idresponsable": 0,
                                                "estado": "NDI",
                                                "orden": 1
                                            }
                                    detalles.append(registro)
                        else:
                            # Mostrar como no disponibles los turnos
                            for turno in turnos:
                                registro = {
                                    "hora": turno.comienza,
                                    "horaini": turno.comienza.strftime('%H:%M'),
                                    "horafin": turno.termina.strftime('%H:%M'),
                                    "idresponsable": 0,
                                    "estado": "NDI",
                                    "orden": 1
                                }
                                detalles.append(registro)

                        # Ordenar por hora
                        ordenados = sorted(detalles, key=lambda dato: (dato['hora'], dato['idresponsable'], dato['orden']), reverse=False)
                        detalles = ordenados

                        mostrarmenu = ""

                        # Obtener que tipo de actividad según el horario es por día (Sólo para responsables de servicios)
                        if tipovista == 'RS' and datetime.now().date() >= fecha and pendientesgest > 1:
                            mostrarmenu = "S"

                        registro = {"dia": f'{dia_semana_enletras_fecha(fecha)} {fecha.day}', "mostrarmenu": mostrarmenu, "fecha": fecha, "detalles": detalles}
                        calendario.append(registro)
                        fecha = fecha + timedelta(days=1)

                    data['idserv'] = idserv
                    data['idgest'] = idgest
                    data['idresp'] = idresp
                    data['estado'] = estado
                    data['anio'] = anio
                    data['semana'] = semana
                    data['tipovista'] = tipovista
                    data['titulosemana'] = f'Del {fechainicio.strftime("%d-%m-%Y")} al {fechafin.strftime("%d-%m-%Y")}'
                    data['calendario'] = calendario

                    template = get_template("adm_asesoriainvestigacion/agenda.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al obtener los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

            elif action == 'horariosservicios':
                try:
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), '&action=' + action
                    ids = request.GET.get('ids', '')
                    tipovista = tipo_vista_gestion_asesoria(persona)
                    if search:
                        data['s'] = search
                        ss = search.split(" ")
                        if len(ss) == 1:
                            filtro = filtro & (Q(responsable__nombres__icontains=search) |
                                               Q(responsable__apellido1__icontains=search) |
                                               Q(responsable__apellido2__icontains=search))
                        else:
                            filtro = filtro & (Q(responsable__apellido1__contains=ss[0]) &
                                               Q(responsable__apellido2__contains=ss[1]))

                        url_vars += '&s=' + search

                    mostraragregar = True
                    if tipovista == 'RS':
                        filtro = filtro & (Q(responsable=persona))
                        mostraragregar = not ResponsableServicio.objects.values("id").filter(status=True, vigente=True, responsable=persona).exists()
                    elif tipovista == 'SL':
                        mostraragregar = False

                    horariosservicios = ResponsableServicio.objects.filter(filtro).order_by('responsable__apellido1', 'responsable__apellido2','responsable__nombres')

                    paging = MiPaginador(horariosservicios, 25)
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
                    data['url_vars'] = url_vars
                    data['horariosservicios'] = page.object_list
                    data['tipovista'] = tipovista
                    data['mostraragregar'] = mostraragregar
                    data['title'] = u'Horarios de los Servicios para Asesorías en Investigación'
                    data['tipovista'] = tipo_vista_gestion_asesoria(persona)

                    return render(request, "adm_asesoriainvestigacion/horarioservicio.html", data)
                except Exception as ex:
                    pass

            elif action == 'addhorarioservicio':
                try:
                    data['title'] = u'Agregar Horario para Asesoría en Investigación'
                    form = HorarioServicioForm()
                    data['anio'] = datetime.now().date().year
                    data['mes'] = datetime.now().date().month
                    data['form'] = form
                    data['dias'] = [1, 2, 3, 4, 5, 6, 7]
                    data['diascab'] = [{"numero": 1, "nombre": "Lunes", "ancho": 14},
                                       {"numero": 2, "nombre": "Martes", "ancho": 14},
                                       {"numero": 3, "nombre": "Miércoles", "ancho": 14},
                                       {"numero": 4, "nombre": "Jueves", "ancho": 14},
                                       {"numero": 5, "nombre": "Viernes", "ancho": 14},
                                       {"numero": 6, "nombre": "Sábado", "ancho": 14},
                                       {"numero": 7, "nombre": "Domingo", "ancho": 16}]
                    data['tiposervicio'] = TIPO_SERVICIO
                    data['turnos'] = TurnoCita.objects.filter(status=True, vigente=True, tipo=1).order_by('orden')
                    data['tipovista'] = tipo_vista_gestion_asesoria(persona)
                    return render(request, "adm_asesoriainvestigacion/addhorarioservicio.html", data)
                except Exception as ex:
                    pass

            elif action == 'edithorarioservicio':
                try:
                    data['title'] = u'Editar para Asesoría en Investigación'
                    data['horario'] = horario = ResponsableServicio.objects.get(pk=int(encrypt(request.GET['id'])))
                    tiposerviciosemana = TipoServicioSemanaResponsableServicio.objects.filter(status=True, responsableservicio=horario).order_by('semana', 'dia')

                    form = HorarioServicioForm(
                        initial={
                            'gestion': horario.mi_gestion(),
                            'ubicacion': horario.ubicacion,
                            'bloque': horario.bloque,
                            'oficina': horario.oficina,
                            'piso': horario.piso,
                            'desde': horario.desde,
                            'hasta': horario.hasta
                        }
                    )

                    form.editar(horario)
                    data['form'] = form
                    data['dias'] = [1, 2, 3, 4, 5, 6, 7]
                    data['diascab'] = [{"numero": 1, "nombre": "Lunes", "ancho": 14, "marcado": "S" if horario.lunes else "", "tiposervicios1": tiposerviciosemana.filter(dia=1, semana=1)[0].tipo if tiposerviciosemana.filter(dia=1, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=1, semana=2)[0].tipo if tiposerviciosemana.filter(dia=1, semana=2).exists() else ''},
                                       {"numero": 2, "nombre": "Martes", "ancho": 14, "marcado": "S" if horario.martes else "", "tiposervicios1": tiposerviciosemana.filter(dia=2, semana=1)[0].tipo if tiposerviciosemana.filter(dia=2, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=2, semana=2)[0].tipo if tiposerviciosemana.filter(dia=2, semana=2).exists() else ''},
                                       {"numero": 3, "nombre": "Miércoles", "ancho": 14, "marcado": "S" if horario.miercoles else "", "tiposervicios1": tiposerviciosemana.filter(dia=3, semana=1)[0].tipo if tiposerviciosemana.filter(dia=3, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=3, semana=2)[0].tipo if tiposerviciosemana.filter(dia=3, semana=2).exists() else ''},
                                       {"numero": 4, "nombre": "Jueves", "ancho": 14, "marcado": "S" if horario.jueves else "", "tiposervicios1": tiposerviciosemana.filter(dia=4, semana=1)[0].tipo if tiposerviciosemana.filter(dia=4, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=4, semana=2)[0].tipo if tiposerviciosemana.filter(dia=4, semana=2).exists() else ''},
                                       {"numero": 5, "nombre": "Viernes", "ancho": 14, "marcado": "S" if horario.viernes else "", "tiposervicios1": tiposerviciosemana.filter(dia=5, semana=1)[0].tipo if tiposerviciosemana.filter(dia=5, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=5, semana=2)[0].tipo if tiposerviciosemana.filter(dia=5, semana=2).exists() else ''},
                                       {"numero": 6, "nombre": "Sábado", "ancho": 14, "marcado": "S" if horario.sabado else "", "tiposervicios1": tiposerviciosemana.filter(dia=6, semana=1)[0].tipo if tiposerviciosemana.filter(dia=6, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=6, semana=2)[0].tipo if tiposerviciosemana.filter(dia=6, semana=2).exists() else ''},
                                       {"numero": 7, "nombre": "Domingo", "ancho": 16, "marcado": "S" if horario.domingo else "", "tiposervicios1": tiposerviciosemana.filter(dia=7, semana=1)[0].tipo if tiposerviciosemana.filter(dia=7, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=7, semana=2)[0].tipo if tiposerviciosemana.filter(dia=7, semana=2).exists() else ''}]
                    data['tiposervicio'] = TIPO_SERVICIO
                    data['servicios'] = [s.servicio.id for s in horario.servicios()]

                    detalles = []
                    turnos = TurnoCita.objects.filter(status=True, vigente=True, tipo=1).order_by('orden')
                    turnosdiahorario = horario.turnosdia()

                    for turno in turnos:
                        turnosdia = []
                        for dia in range(1, 8):
                            if dia == 1:
                                bloqueado = "N" if horario.lunes else "S"
                            elif dia == 2:
                                bloqueado = "N" if horario.martes else "S"
                            elif dia == 3:
                                bloqueado = "N" if horario.miercoles else "S"
                            elif dia == 4:
                                bloqueado = "N" if horario.jueves else "S"
                            elif dia == 5:
                                bloqueado = "N" if horario.viernes else "S"
                            elif dia == 6:
                                bloqueado = "N" if horario.sabado else "S"
                            else:
                                bloqueado = "N" if horario.domingo else "S"

                            turnosdia.append({"dia": dia,
                                              "idturno": turno.id,
                                              "comienza": turno.comienza,
                                              "termina": turno.termina,
                                              "marcado": "S" if turnosdiahorario.filter(dia=dia, turno=turno).exists() else "N",
                                              "bloqueado": bloqueado})

                        detalles.append({"turno": turno, "turnosdias": turnosdia})

                    data['detalles'] = detalles
                    data['tipovista'] = tipo_vista_gestion_asesoria(persona)
                    return render(request, "adm_asesoriainvestigacion/edithorarioservicio.html", data)
                except Exception as ex:
                    pass

            elif action == 'horarioservicio':
                try:
                    title = u'Horario para Asesoría en Investigación'
                    horario = ResponsableServicio.objects.get(pk=int(encrypt(request.GET['id'])))
                    tiposerviciosemana = TipoServicioSemanaResponsableServicio.objects.filter(status=True, responsableservicio=horario).order_by('semana', 'dia')
                    data['horario'] = horario

                    dias = [{"dia": 1, "nombre": "LUNES", "marcado": "S" if horario.lunes else "N", "tiposervicios1": tiposerviciosemana.filter(dia=1, semana=1)[0].get_tipo_display() if tiposerviciosemana.filter(dia=1, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=1, semana=2)[0].get_tipo_display() if tiposerviciosemana.filter(dia=1, semana=2).exists() else ''},
                            {"dia": 2, "nombre": "MARTES", "marcado": "S" if horario.martes else "N", "tiposervicios1": tiposerviciosemana.filter(dia=2, semana=1)[0].get_tipo_display() if tiposerviciosemana.filter(dia=2, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=2, semana=2)[0].get_tipo_display() if tiposerviciosemana.filter(dia=2, semana=2).exists() else ''},
                            {"dia": 3, "nombre": "MIÉRCOLES", "marcado": "S" if horario.miercoles else "N", "tiposervicios1": tiposerviciosemana.filter(dia=3, semana=1)[0].get_tipo_display() if tiposerviciosemana.filter(dia=3, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=3, semana=2)[0].get_tipo_display() if tiposerviciosemana.filter(dia=3, semana=2).exists() else ''},
                            {"dia": 4, "nombre": "JUEVES", "marcado": "S" if horario.jueves else "N", "tiposervicios1": tiposerviciosemana.filter(dia=4, semana=1)[0].get_tipo_display() if tiposerviciosemana.filter(dia=4, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=4, semana=2)[0].get_tipo_display() if tiposerviciosemana.filter(dia=4, semana=2).exists() else ''},
                            {"dia": 5, "nombre": "VIERNES", "marcado": "S" if horario.viernes else "N", "tiposervicios1": tiposerviciosemana.filter(dia=5, semana=1)[0].get_tipo_display() if tiposerviciosemana.filter(dia=5, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=5, semana=2)[0].get_tipo_display() if tiposerviciosemana.filter(dia=5, semana=2).exists() else ''},
                            {"dia": 6, "nombre": "SÁBADO", "marcado": "S" if horario.sabado else "N", "tiposervicios1": tiposerviciosemana.filter(dia=6, semana=1)[0].get_tipo_display() if tiposerviciosemana.filter(dia=6, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=6, semana=2)[0].get_tipo_display() if tiposerviciosemana.filter(dia=6, semana=2).exists() else ''},
                            {"dia": 7, "nombre": "DOMINGO", "marcado": "S" if horario.domingo else "N", "tiposervicios1": tiposerviciosemana.filter(dia=7, semana=1)[0].get_tipo_display() if tiposerviciosemana.filter(dia=7, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=7, semana=2)[0].get_tipo_display() if tiposerviciosemana.filter(dia=7, semana=2).exists() else ''}]

                    detalles = []

                    turnos = TurnoCita.objects.filter(status=True, vigente=True, tipo=1).order_by('orden')
                    turnosdiahorario = horario.turnosdia()

                    for turno in turnos:
                        turnosdia = []
                        for dia in range(1, 8):
                            turnosdia.append({"dia": dia,
                                            "comienza": turno.comienza,
                                            "termina": turno.termina,
                                            "marcado": "S" if turnosdiahorario.filter(dia=dia, turno=turno).exists() else "N"})

                        detalles.append({"turno": turno, "turnosdias": turnosdia})

                    data['dias'] = dias
                    data['detalles'] = detalles

                    template = get_template("adm_asesoriainvestigacion/modal/informacionhorario.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'aprobarhorario':
                try:
                    title = u'Aprobar Horario para Asesoría en Investigación'
                    horario = ResponsableServicio.objects.get(pk=int(encrypt(request.GET['id'])))
                    tiposerviciosemana = TipoServicioSemanaResponsableServicio.objects.filter(status=True, responsableservicio=horario).order_by('semana', 'dia')
                    data['horario'] = horario

                    # dias = [{"dia": 1, "nombre": "LUNES", "marcado": "S" if horario.lunes else "N", "tiposervicio": horario.get_tiposlun_display()},
                    #         {"dia": 2, "nombre": "MARTES", "marcado": "S" if horario.martes else "N", "tiposervicio": horario.get_tiposmar_display()},
                    #         {"dia": 3, "nombre": "MIÉRCOLES", "marcado": "S" if horario.miercoles else "N", "tiposervicio": horario.get_tiposmie_display()},
                    #         {"dia": 4, "nombre": "JUEVES", "marcado": "S" if horario.jueves else "N", "tiposervicio": horario.get_tiposjue_display()},
                    #         {"dia": 5, "nombre": "VIERNES", "marcado": "S" if horario.viernes else "N", "tiposervicio": horario.get_tiposvie_display()},
                    #         {"dia": 6, "nombre": "SÁBADO", "marcado": "S" if horario.sabado else "N", "tiposervicio": horario.get_tipossab_display()},
                    #         {"dia": 7, "nombre": "DOMINGO", "marcado": "S" if horario.domingo else "N", "tiposervicio": horario.get_tiposdom_display()}]

                    dias = [{"dia": 1, "nombre": "LUNES", "marcado": "S" if horario.lunes else "N", "tiposervicios1": tiposerviciosemana.filter(dia=1, semana=1)[0].get_tipo_display() if tiposerviciosemana.filter(dia=1, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=1, semana=2)[0].get_tipo_display() if tiposerviciosemana.filter(dia=1, semana=2).exists() else ''},
                            {"dia": 2, "nombre": "MARTES", "marcado": "S" if horario.martes else "N", "tiposervicios1": tiposerviciosemana.filter(dia=2, semana=1)[0].get_tipo_display() if tiposerviciosemana.filter(dia=2, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=2, semana=2)[0].get_tipo_display() if tiposerviciosemana.filter(dia=2, semana=2).exists() else ''},
                            {"dia": 3, "nombre": "MIÉRCOLES", "marcado": "S" if horario.miercoles else "N", "tiposervicios1": tiposerviciosemana.filter(dia=3, semana=1)[0].get_tipo_display() if tiposerviciosemana.filter(dia=3, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=3, semana=2)[0].get_tipo_display() if tiposerviciosemana.filter(dia=3, semana=2).exists() else ''},
                            {"dia": 4, "nombre": "JUEVES", "marcado": "S" if horario.jueves else "N", "tiposervicios1": tiposerviciosemana.filter(dia=4, semana=1)[0].get_tipo_display() if tiposerviciosemana.filter(dia=4, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=4, semana=2)[0].get_tipo_display() if tiposerviciosemana.filter(dia=4, semana=2).exists() else ''},
                            {"dia": 5, "nombre": "VIERNES", "marcado": "S" if horario.viernes else "N", "tiposervicios1": tiposerviciosemana.filter(dia=5, semana=1)[0].get_tipo_display() if tiposerviciosemana.filter(dia=5, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=5, semana=2)[0].get_tipo_display() if tiposerviciosemana.filter(dia=5, semana=2).exists() else ''},
                            {"dia": 6, "nombre": "SÁBADO", "marcado": "S" if horario.sabado else "N", "tiposervicios1": tiposerviciosemana.filter(dia=6, semana=1)[0].get_tipo_display() if tiposerviciosemana.filter(dia=6, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=6, semana=2)[0].get_tipo_display() if tiposerviciosemana.filter(dia=6, semana=2).exists() else ''},
                            {"dia": 7, "nombre": "DOMINGO", "marcado": "S" if horario.domingo else "N", "tiposervicios1": tiposerviciosemana.filter(dia=7, semana=1)[0].get_tipo_display() if tiposerviciosemana.filter(dia=7, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=7, semana=2)[0].get_tipo_display() if tiposerviciosemana.filter(dia=7, semana=2).exists() else ''}]

                    detalles = []

                    turnos = TurnoCita.objects.filter(status=True, vigente=True, tipo=1).order_by('orden')
                    turnosdiahorario = horario.turnosdia()

                    for turno in turnos:
                        turnosdia = []
                        for dia in range(1, 8):
                            turnosdia.append({"dia": dia,
                                            "comienza": turno.comienza,
                                            "termina": turno.termina,
                                            "marcado": "S" if turnosdiahorario.filter(dia=dia, turno=turno).exists() else "N"})

                        detalles.append({"turno": turno, "turnosdias": turnosdia})

                    data['dias'] = dias
                    data['detalles'] = detalles
                    data['estados'] = ESTADO_HORARIO_SERVICIO

                    template = get_template("adm_asesoriainvestigacion/modal/aprobarhorario.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'servicioasignado':
                try:
                    data['title'] = u'Servicios Asignados al Responsable'
                    data['horario'] = horario = ResponsableServicio.objects.get(pk=int(encrypt(request.GET['id'])))
                    servicios = ServicioGestion.objects.filter(status=True, gestion=horario.mi_gestion()).order_by('tipo', 'nombre')
                    servicioshorario = horario.servicios()
                    lista = []
                    for servicio in servicios:
                        vigente = visible = False
                        if serviciohorario := servicioshorario.filter(servicio=servicio):
                            lista.append({"servicio": servicio, "vigente": "S" if serviciohorario[0].vigente else "N", "visible": "S" if serviciohorario[0].visiblesolicitante else "N"})
                        else:
                            lista.append({"servicio": servicio, "vigente": "N", "visible": "N"})

                    data['listaservicios'] = lista
                    template = get_template("adm_asesoriainvestigacion/modal/servicioasignado.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al obtener los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

            elif action == 'finalizarvigencia':
                try:
                    title = u'Finalizar Vigencia de Horario para Asesoría en Investigación'
                    horario = ResponsableServicio.objects.get(pk=int(encrypt(request.GET['id'])))
                    tiposerviciosemana = TipoServicioSemanaResponsableServicio.objects.filter(status=True, responsableservicio=horario).order_by('semana', 'dia')
                    data['horario'] = horario

                    dias = [{"dia": 1, "nombre": "LUNES", "marcado": "S" if horario.lunes else "N", "tiposervicios1": tiposerviciosemana.filter(dia=1, semana=1)[0].get_tipo_display() if tiposerviciosemana.filter(dia=1, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=1, semana=2)[0].get_tipo_display() if tiposerviciosemana.filter(dia=1, semana=2).exists() else ''},
                            {"dia": 2, "nombre": "MARTES", "marcado": "S" if horario.martes else "N", "tiposervicios1": tiposerviciosemana.filter(dia=2, semana=1)[0].get_tipo_display() if tiposerviciosemana.filter(dia=2, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=2, semana=2)[0].get_tipo_display() if tiposerviciosemana.filter(dia=2, semana=2).exists() else ''},
                            {"dia": 3, "nombre": "MIÉRCOLES", "marcado": "S" if horario.miercoles else "N", "tiposervicios1": tiposerviciosemana.filter(dia=3, semana=1)[0].get_tipo_display() if tiposerviciosemana.filter(dia=3, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=3, semana=2)[0].get_tipo_display() if tiposerviciosemana.filter(dia=3, semana=2).exists() else ''},
                            {"dia": 4, "nombre": "JUEVES", "marcado": "S" if horario.jueves else "N", "tiposervicios1": tiposerviciosemana.filter(dia=4, semana=1)[0].get_tipo_display() if tiposerviciosemana.filter(dia=4, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=4, semana=2)[0].get_tipo_display() if tiposerviciosemana.filter(dia=4, semana=2).exists() else ''},
                            {"dia": 5, "nombre": "VIERNES", "marcado": "S" if horario.viernes else "N", "tiposervicios1": tiposerviciosemana.filter(dia=5, semana=1)[0].get_tipo_display() if tiposerviciosemana.filter(dia=5, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=5, semana=2)[0].get_tipo_display() if tiposerviciosemana.filter(dia=5, semana=2).exists() else ''},
                            {"dia": 6, "nombre": "SÁBADO", "marcado": "S" if horario.sabado else "N", "tiposervicios1": tiposerviciosemana.filter(dia=6, semana=1)[0].get_tipo_display() if tiposerviciosemana.filter(dia=6, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=6, semana=2)[0].get_tipo_display() if tiposerviciosemana.filter(dia=6, semana=2).exists() else ''},
                            {"dia": 7, "nombre": "DOMINGO", "marcado": "S" if horario.domingo else "N", "tiposervicios1": tiposerviciosemana.filter(dia=7, semana=1)[0].get_tipo_display() if tiposerviciosemana.filter(dia=7, semana=1).exists() else '', "tiposervicios2": tiposerviciosemana.filter(dia=7, semana=2)[0].get_tipo_display() if tiposerviciosemana.filter(dia=7, semana=2).exists() else ''}]

                    detalles = []

                    turnos = TurnoCita.objects.filter(status=True, vigente=True, tipo=1).order_by('orden')
                    turnosdiahorario = horario.turnosdia()

                    for turno in turnos:
                        turnosdia = []
                        for dia in range(1, 8):
                            turnosdia.append({"dia": dia,
                                            "comienza": turno.comienza,
                                            "termina": turno.termina,
                                            "marcado": "S" if turnosdiahorario.filter(dia=dia, turno=turno).exists() else "N"})

                        detalles.append({"turno": turno, "turnosdias": turnosdia})

                    data['dias'] = dias
                    data['detalles'] = detalles

                    template = get_template("adm_asesoriainvestigacion/modal/finalizarvigenciahorario.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'enlacesatencionvirtual':
                try:
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), '&action=' + action

                    if search:
                        data['s'] = search
                        ss = search.split(" ")
                        if len(ss) == 1:
                            filtro = filtro & (Q(persona__nombres__icontains=search) |
                                               Q(persona__apellido1__icontains=search) |
                                               Q(persona__apellido2__icontains=search))
                        else:
                            filtro = filtro & (Q(persona__apellido1__contains=ss[0]) &
                                               Q(persona__apellido2__contains=ss[1]))

                        url_vars += '&s=' + search

                    enlacesatencionvirtual = EnlaceAtencionVirtualPersona.objects.filter(filtro).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    paging = MiPaginador(enlacesatencionvirtual, 25)
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
                    data['url_vars'] = url_vars
                    data['enlacesatencionvirtual'] = page.object_list
                    data['title'] = u'Enlaces de Atención Virtual del Personal'
                    data['tipovista'] = tipo_vista_gestion_asesoria(persona)

                    return render(request, "adm_asesoriainvestigacion/enlaceatencion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addenlaceatencion':
                try:
                    data['title'] = u'Agregar Enlace de Atención Virtual'
                    data['tipoherramienta'] = TIPO_HERRAMIENTA_AVIRTUAL
                    template = get_template("adm_asesoriainvestigacion/modal/addenlaceatencion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editenlaceatencion':
                try:
                    data['title'] = u'Editar Enlace de Atención Virtual'
                    data['enlaceatencion'] = EnlaceAtencionVirtualPersona.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['tipoherramienta'] = TIPO_HERRAMIENTA_AVIRTUAL
                    template = get_template("adm_asesoriainvestigacion/modal/editenlaceatencion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'servicios':
                try:
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), '&action=' + action

                    if search:
                        data['s'] = search
                        filtro = filtro & (Q(nombre__icontains=search))
                        url_vars += '&s=' + search

                    servicios = ServicioGestion.objects.filter(filtro).order_by('nombre')

                    paging = MiPaginador(servicios, 25)
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
                    data['url_vars'] = url_vars
                    data['servicios'] = page.object_list
                    data['title'] = u'Servicios Ofertados'
                    data['tipovista'] = tipo_vista_gestion_asesoria(persona)

                    return render(request, "adm_asesoriainvestigacion/servicio.html", data)
                except Exception as ex:
                    pass

            elif action == 'addservicio':
                try:
                    data['title'] = u'Agregar Servicio Ofertado'
                    data['gestiones'] = Gestion.objects.filter(status=True).order_by('nombre')
                    data['tipos'] = TIPO_SERVICIO
                    template = get_template("adm_asesoriainvestigacion/modal/addservicio.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editservicio':
                try:
                    data['title'] = u'Editar Servicio Ofertado'
                    data['servicio'] = ServicioGestion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['gestiones'] = Gestion.objects.filter(status=True).order_by('nombre')
                    data['tipos'] = TIPO_SERVICIO
                    template = get_template("adm_asesoriainvestigacion/modal/editservicio.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'gestionarcita':
                try:
                    data['title'] = u'Gestionar Cita para Asesoría en Investigación'
                    data['cita'] = cita = CitaAsesoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['fecha'] = datetime.now() if cita.fecha == datetime.now().date() else datetime.combine(cita.fecha, cita.horainicio)
                    data['anio'] = datetime.now().date().year
                    data['mes'] = datetime.now().date().month

                    asesoria = cita.asesoria()
                    if asesoria:
                        data['nombresol'] = asesoria.citaasesoria.solicitante.nombre_completo_inverso()
                        data['nombreresp'] = asesoria.citaasesoria.responsable.nombre_completo_inverso()
                    else:
                        data['nombresol'] = cita.solicitante.nombre_completo_inverso()
                        data['nombreresp'] = cita.responsable.nombre_completo_inverso()

                    form = GestionCitaAsesoriaForm(
                        initial={
                            'gestiona': cita.servicio.gestion.nombre,
                            'servicioa': cita.servicio.nombre,
                            'responsable': cita.responsable.nombre_completo_inverso(),
                            'fecha': cita.fecha.strftime("%d-%m-%Y"),
                            'modalidada': cita.get_modalidad_display(),
                            'horainicio': cita.horainicio.strftime("%H:%M"),
                            'horafin': cita.horafin.strftime("%H:%M"),
                            'solicitantea': cita.solicitante.nombre_completo_inverso(),
                            'motivoa': cita.motivo,
                            'horainicioase': cita.horainicio.strftime("%H:%M"),
                            'horafinase': cita.horafin.strftime("%H:%M")
                        }
                    )
                    data['form'] = form
                    data['tipoanexos'] = ", ".join(variable_valor("TIPOS_ANEXOS_ASESORIAS_INV"))
                    data['tamanio'] = variable_valor("TAMANIO_ANEXOS_ASESORIAS_INV")

                    return render(request, "adm_asesoriainvestigacion/gestionarcita.html", data)
                except Exception as ex:
                    pass

            elif action == 'cargarcalendario':
                try:
                    # Opción desde donde se invoca
                    nopcion = request.GET['nopcion']
                    # Consulta el servicio de la gestión
                    servicio = ServicioGestion.objects.get(pk=int(request.GET['idserv']))
                    # if 'idresp' in request.GET:
                    responsable = Persona.objects.get(pk=int(request.GET['idresp'])) if int(request.GET['idresp']) > 0 else None
                    # else:
                    #     responsable = None

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

                            if not responsable:
                                # Consulto si hay habilitados
                                if fechacal == fechaactual:
                                    if HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=fechaactual, fecha=fechacal, turno__comienza__gte=horaactual, habilitado=True, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__estado=2, responsableservicio__vigente=True).exists():
                                        if nopcion != 'GES':
                                            if HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=fechaactual, fecha=fechacal, turno__comienza__gte=horaactual, habilitado=True, ocupado=False, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__estado=2, responsableservicio__vigente=True).exists():
                                                listadias.append({"dia": dia, "status": "TDI"})
                                            elif HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=fechaactual, fecha=fechacal, turno__comienza__gte=horaactual, habilitado=True, reutilizable=True, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__estado=2, responsableservicio__vigente=True).exists():
                                                listadias.append({"dia": dia, "status": "TDI"})
                                            else:
                                                listadias.append({"dia": dia, "status": "OCU"})
                                        else:
                                            if servicio.tipo == 1:
                                                if HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=fechaactual, fecha=fechacal, turno__comienza__gte=horaactual, habilitado=True, ocupado=False, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__estado=2, responsableservicio__vigente=True).exists():
                                                    listadias.append({"dia": dia, "status": "TDI"})
                                                else:
                                                    listadias.append({"dia": dia, "status": "OCU"})
                                            else:
                                                if HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=fechaactual, fecha=fechacal, turno__comienza__gte=horaactual, habilitado=True, reutilizable=True, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__estado=2, responsableservicio__vigente=True).exists():
                                                    listadias.append({"dia": dia, "status": "TDI"})
                                                else:
                                                    listadias.append({"dia": dia, "status": "OCU"})
                                    else:
                                        listadias.append({"dia": dia, "status": "STU"})
                                else:
                                    if HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=fechaactual, fecha=fechacal, habilitado=True, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__estado=2, responsableservicio__vigente=True).exists():
                                        if nopcion != 'GES':
                                            if HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=fechaactual, fecha=fechacal, habilitado=True, ocupado=False, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__estado=2, responsableservicio__vigente=True).exists():
                                                listadias.append({"dia": dia, "status": "TDI"})
                                            elif HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=fechaactual, fecha=fechacal, habilitado=True, reutilizable=True, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__estado=2, responsableservicio__vigente=True).exists():
                                                listadias.append({"dia": dia, "status": "TDI"})
                                            else:
                                                listadias.append({"dia": dia, "status": "OCU"})
                                        else:
                                            if servicio.tipo == 1:
                                                if HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=fechaactual, fecha=fechacal, habilitado=True, ocupado=False, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__estado=2, responsableservicio__vigente=True).exists():
                                                    listadias.append({"dia": dia, "status": "TDI"})
                                                else:
                                                    listadias.append({"dia": dia, "status": "OCU"})
                                            else:
                                                if HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=fechaactual, fecha=fechacal, habilitado=True, reutilizable=True, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__estado=2, responsableservicio__vigente=True).exists():
                                                    listadias.append({"dia": dia, "status": "TDI"})
                                                else:
                                                    listadias.append({"dia": dia, "status": "OCU"})

                                    else:
                                        listadias.append({"dia": dia, "status": "STU"})
                            else:
                                # Consulto si hay habilitados
                                if fechacal == fechaactual:
                                    if HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=fechaactual, fecha=fechacal, turno__comienza__gte=horaactual, habilitado=True, responsableservicio__responsable=responsable, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__estado=2, responsableservicio__vigente=True).exists():
                                        if nopcion != 'GES':
                                            if HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=fechaactual, fecha=fechacal, turno__comienza__gte=horaactual, habilitado=True, ocupado=False, responsableservicio__responsable=responsable, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__estado=2, responsableservicio__vigente=True).exists():
                                                listadias.append({"dia": dia, "status": "TDI"})
                                            elif HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=fechaactual, fecha=fechacal, turno__comienza__gte=horaactual, habilitado=True, reutilizable=True, responsableservicio__responsable=responsable, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__estado=2, responsableservicio__vigente=True).exists():
                                                listadias.append({"dia": dia, "status": "TDI"})
                                            else:
                                                listadias.append({"dia": dia, "status": "STU"})
                                        else:
                                            if servicio.tipo == 1:
                                                if HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=fechaactual, fecha=fechacal, turno__comienza__gte=horaactual, habilitado=True, ocupado=False, responsableservicio__responsable=responsable, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__estado=2, responsableservicio__vigente=True).exists():
                                                    listadias.append({"dia": dia, "status": "TDI"})
                                                else:
                                                    listadias.append({"dia": dia, "status": "OCU"})
                                            else:
                                                if HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=fechaactual, fecha=fechacal, turno__comienza__gte=horaactual, habilitado=True, reutilizable=True, responsableservicio__responsable=responsable, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__estado=2, responsableservicio__vigente=True).exists():
                                                    listadias.append({"dia": dia, "status": "TDI"})
                                                else:
                                                    listadias.append({"dia": dia, "status": "OCU"})
                                    else:
                                        listadias.append({"dia": dia, "status": "STU"})
                                else:
                                    if HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=fechaactual, fecha=fechacal, habilitado=True, responsableservicio__responsable=responsable, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__estado=2, responsableservicio__vigente=True).exists():
                                        if nopcion != 'GES':
                                            if HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=fechaactual, fecha=fechacal, habilitado=True, ocupado=False, responsableservicio__responsable=responsable, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__estado=2, responsableservicio__vigente=True).exists():
                                                listadias.append({"dia": dia, "status": "TDI"})
                                            elif HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=fechaactual, fecha=fechacal, habilitado=True, reutilizable=True, responsableservicio__responsable=responsable, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__estado=2, responsableservicio__vigente=True).exists():
                                                listadias.append({"dia": dia, "status": "TDI"})
                                            else:
                                                listadias.append({"dia": dia, "status": "OCU"})
                                        else:
                                            if servicio.tipo == 1:
                                                if HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=fechaactual, fecha=fechacal, habilitado=True, ocupado=False, responsableservicio__responsable=responsable, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__estado=2, responsableservicio__vigente=True).exists():
                                                    listadias.append({"dia": dia, "status": "TDI"})
                                                else:
                                                    listadias.append({"dia": dia, "status": "OCU"})
                                            else:
                                                if HorarioResponsableServicio.objects.values("id").filter(status=True, fecha__gte=fechaactual, fecha=fechacal, habilitado=True, reutilizable=True, responsableservicio__responsable=responsable, responsableservicio__servicioresponsableservicio__servicio=servicio, responsableservicio__servicioresponsableservicio__vigente=True, responsableservicio__estado=2, responsableservicio__vigente=True).exists():
                                                    listadias.append({"dia": dia, "status": "TDI"})
                                                else:
                                                    listadias.append({"dia": dia, "status": "OCU"})
                                    else:
                                        listadias.append({"dia": dia, "status": "STU"})
                        else:
                            listadias.append({"dia": dia, "status": "STU"})

                    data['nopcion'] = request.GET['nopcion']
                    data['idserv'] = request.GET['idserv']
                    data['idresp'] = request.GET['idresp']
                    data['anio'] = anio
                    data['mes'] = mes
                    data['titulomes'] = MESES_CHOICES[mes - 1][1] + " " + str(anio)
                    data['listadias'] = listadias

                    template = get_template("adm_asesoriainvestigacion/calendario.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'detalle': detalle})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cargarresponsablesservicio':
                try:
                    nopcion = request.GET['nopcion']
                    servicio = ServicioGestion.objects.get(pk=int(request.GET['idserv']))
                    responsable = Persona.objects.get(pk=int(request.GET['idresp'])) if int(request.GET['idresp']) > 0 else None

                    anio = int(request.GET['anio'])
                    mes = int(request.GET['mes'])
                    dia = int(request.GET['dia'])

                    fechacal = date(anio, mes, dia)

                    listaresponsables = []

                    if not responsable:
                        if nopcion != 'GES':
                            responsablesservicio1 = ResponsableServicio.objects.filter(status=True, vigente=True, estado=2, servicioresponsableservicio__servicio=servicio, servicioresponsableservicio__vigente=True, horarioresponsableservicio__status=True, horarioresponsableservicio__fecha=fechacal, horarioresponsableservicio__habilitado=True, horarioresponsableservicio__ocupado=False, horarioresponsableservicio__tiposervicio=1).distinct()

                            responsablesservicio2 = ResponsableServicio.objects.filter(status=True, vigente=True, estado=2, servicioresponsableservicio__servicio=servicio, servicioresponsableservicio__vigente=True, horarioresponsableservicio__status=True, horarioresponsableservicio__fecha=fechacal, horarioresponsableservicio__habilitado=True, horarioresponsableservicio__reutilizable=True, horarioresponsableservicio__tiposervicio=2).distinct()

                            responsablesservicio = responsablesservicio1 | responsablesservicio2
                            responsablesservicio = responsablesservicio.distinct()
                        else:
                            if servicio.tipo == 1:
                                responsablesservicio = ResponsableServicio.objects.filter(status=True, vigente=True, estado=2, servicioresponsableservicio__servicio=servicio, servicioresponsableservicio__vigente=True, horarioresponsableservicio__status=True, horarioresponsableservicio__fecha=fechacal, horarioresponsableservicio__habilitado=True, horarioresponsableservicio__ocupado=False, horarioresponsableservicio__tiposervicio=servicio.tipo).distinct()
                            else:
                                responsablesservicio = ResponsableServicio.objects.filter(status=True, vigente=True, estado=2, servicioresponsableservicio__servicio=servicio, servicioresponsableservicio__vigente=True, horarioresponsableservicio__status=True, horarioresponsableservicio__fecha=fechacal, horarioresponsableservicio__habilitado=True, horarioresponsableservicio__reutilizable=True, horarioresponsableservicio__tiposervicio=servicio.tipo).distinct()
                    else:
                        if nopcion != 'GES':
                            responsablesservicio1 = ResponsableServicio.objects.filter(status=True, responsable=responsable, servicioresponsableservicio__servicio=servicio, servicioresponsableservicio__vigente=True, horarioresponsableservicio__status=True, horarioresponsableservicio__fecha=fechacal, horarioresponsableservicio__habilitado=True, horarioresponsableservicio__ocupado=False, horarioresponsableservicio__tiposervicio=1).distinct()

                            responsablesservicio2 = ResponsableServicio.objects.filter(status=True, responsable=responsable, servicioresponsableservicio__servicio=servicio, servicioresponsableservicio__vigente=True, horarioresponsableservicio__status=True, horarioresponsableservicio__fecha=fechacal, horarioresponsableservicio__habilitado=True, horarioresponsableservicio__reutilizable=True, horarioresponsableservicio__tiposervicio=2).distinct()

                            responsablesservicio = responsablesservicio1 | responsablesservicio2
                            responsablesservicio = responsablesservicio.distinct()
                        else:
                            if servicio.tipo == 1:
                                responsablesservicio = ResponsableServicio.objects.filter(status=True, responsable=responsable, servicioresponsableservicio__servicio=servicio, servicioresponsableservicio__vigente=True, horarioresponsableservicio__status=True, horarioresponsableservicio__fecha=fechacal, horarioresponsableservicio__habilitado=True, horarioresponsableservicio__ocupado=False, horarioresponsableservicio__tiposervicio=servicio.tipo).distinct()
                            else:
                                responsablesservicio = ResponsableServicio.objects.filter(status=True, responsable=responsable, servicioresponsableservicio__servicio=servicio, servicioresponsableservicio__vigente=True, horarioresponsableservicio__status=True, horarioresponsableservicio__fecha=fechacal, horarioresponsableservicio__habilitado=True, horarioresponsableservicio__reutilizable=True, horarioresponsableservicio__tiposervicio=servicio.tipo).distinct()

                    for responsableserv in responsablesservicio:
                        listaresponsables.append({"id": responsableserv.responsable.id, "nombres": responsableserv.responsable.nombre_completo_inverso()})

                    data['nopcion'] = request.GET['nopcion']
                    data['idserv'] = request.GET['idserv']
                    data['idresp'] = request.GET['idresp']
                    data['fecha'] = fechacal
                    data['anio'] = anio
                    data['mes'] = mes
                    data['dia'] = dia
                    data['responsables'] = listaresponsables

                    template = get_template("adm_asesoriainvestigacion/responsableservicio.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cargarturnosservicio':
                try:
                    nopcion = request.GET['nopcion']
                    servicio = ServicioGestion.objects.get(pk=int(request.GET['idserv']))
                    responsable = Persona.objects.get(pk=int(request.GET['idresp']))

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
                    data['idresp'] = request.GET['idresp']
                    data['fecha'] = fechacal
                    data['anio'] = anio
                    data['mes'] = mes
                    data['fechadialetras'] = fechadialetras


                    if nopcion != 'GES':
                        turnos1 = TurnoCita.objects.filter(status=True, tipo=1, horarioresponsableservicio__status=True, horarioresponsableservicio__fecha=fechacal, horarioresponsableservicio__habilitado=True, horarioresponsableservicio__ocupado=False, horarioresponsableservicio__responsableservicio__servicioresponsableservicio__servicio=servicio, horarioresponsableservicio__responsableservicio__servicioresponsableservicio__vigente=True, horarioresponsableservicio__responsableservicio__responsable=responsable).distinct().order_by('orden')
                        turnos2 = TurnoCita.objects.filter(status=True, tipo=1, horarioresponsableservicio__status=True, horarioresponsableservicio__fecha=fechacal, horarioresponsableservicio__habilitado=True, horarioresponsableservicio__reutilizable=True, horarioresponsableservicio__responsableservicio__servicioresponsableservicio__vigente=True, horarioresponsableservicio__responsableservicio__responsable=responsable).distinct().order_by('orden')

                        turnos = turnos1 | turnos2
                        turnos = turnos.distinct().order_by('orden')
                    else:
                        if servicio.tipo == 1:
                            turnos = TurnoCita.objects.filter(status=True, tipo=1, horarioresponsableservicio__status=True, horarioresponsableservicio__fecha=fechacal, horarioresponsableservicio__habilitado=True, horarioresponsableservicio__ocupado=False, horarioresponsableservicio__responsableservicio__servicioresponsableservicio__servicio=servicio, horarioresponsableservicio__responsableservicio__servicioresponsableservicio__vigente=True, horarioresponsableservicio__responsableservicio__responsable=responsable).distinct().order_by('orden')
                        else:
                            turnos = TurnoCita.objects.filter(status=True, tipo=1, horarioresponsableservicio__status=True, horarioresponsableservicio__fecha=fechacal, horarioresponsableservicio__habilitado=True, horarioresponsableservicio__reutilizable=True, horarioresponsableservicio__responsableservicio__servicioresponsableservicio__servicio=servicio, horarioresponsableservicio__responsableservicio__servicioresponsableservicio__vigente=True, horarioresponsableservicio__responsableservicio__responsable=responsable).distinct().order_by('orden')

                    listaturnos = []

                    for turno in turnos:
                        if fechacal == fechaactual:
                            actual = datetime.combine(fechaactual, horaactual) - timedelta(minutes=15)
                            if turno.comienza >= actual.time():
                                listaturnos.append({"id": turno.id, "comienza": turno.comienza.strftime('%H:%M'), "termina": turno.termina.strftime('%H:%M'), "responsable": responsable.nombre_completo_inverso()})
                        else:
                            listaturnos.append({"id": turno.id, "comienza": turno.comienza.strftime('%H:%M'), "termina": turno.termina.strftime('%H:%M'), "responsable": responsable.nombre_completo_inverso()})

                    data['turnos'] = listaturnos

                    template = get_template("adm_asesoriainvestigacion/turnoservicio.html")
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

            elif action == 'addcita':
                try:
                    data['title'] = u'Agregar Cita / Actividad'
                    horario = HorarioResponsableServicio.objects.get(pk=int(encrypt(request.GET['id'])))

                    # Verificar si el horario está disponible
                    if horario.ocupado:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La hora no se encuentra disponible", "showSwal": "True", "swalType": "warning"})

                    data['horario'] = horario
                    data['tiposervicio'] = TIPO_SERVICIO
                    data['modalidades'] = MODALIDAD_ATENCION
                    data['tiposolicitante'] = TIPO_PERSONA_SOLICITANTE
                    template = get_template("adm_asesoriainvestigacion/modal/addcita.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscarprofesor':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if len(s) == 1:
                        personas = Profesor.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                        | Q(persona__apellido2__icontains=s[0])
                                                        | Q(persona__cedula__icontains=s[0])
                                                        | Q(persona__ruc__icontains=s[0])
                                                        | Q(persona__pasaporte__icontains=s[0]),
                                                        status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    else:
                        personas = Profesor.objects.filter(persona__apellido1__icontains=s[0],
                                                           persona__apellido2__icontains=s[1],
                                                           status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    # data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso()), "identificacion": x.persona.identificacion(), "idpersona": x.persona.id, "usuario": x.persona.usuario.username, "emailinst": x.persona.emailinst, "email": x.persona.email, "celular": x.persona.telefono, "telefono": x.persona.telefono_conv} for x in personas]}
                    data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso()), "identificacion": x.persona.identificacion(), "idpersona": x.persona.id, "usuario": x.persona.usuario.username if x.persona.usuario else '', "emailinst": x.persona.emailinst, "email": x.persona.email, "celular": x.persona.telefono, "telefono": x.persona.telefono_conv} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscaralumno':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if len(s) == 1:
                        personas = Inscripcion.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                      | Q(persona__apellido2__icontains=s[0])
                                                      | Q(persona__cedula__icontains=s[0])
                                                      | Q(persona__pasaporte__icontains=s[0])
                                                      | Q(persona__ruc__icontains=s[0]),
                                                      status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    else:
                        personas = Inscripcion.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                               & Q(persona__apellido2__icontains=s[1]),
                                                           status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    personas = personas.filter(persona__perfilusuario__visible=True, persona__perfilusuario__status=True).exclude(coordinacion_id=9).distinct()

                    data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso()) + ' - ' + x.carrera.nombre} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscaradministrativo':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if len(s) == 1:
                        personas = Administrativo.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                      | Q(persona__apellido2__icontains=s[0])
                                                      | Q(persona__cedula__icontains=s[0])
                                                      | Q(persona__pasaporte__icontains=s[0])
                                                      | Q(persona__ruc__icontains=s[0]),
                                                      status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    else:
                        personas = Administrativo.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                               & Q(persona__apellido2__icontains=s[1]),
                                                           status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    data = {"result": "ok", "results": [{"id": x.id, "name": str(x.persona.nombre_completo_inverso())} for x in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'finalizaractividad':
                try:
                    data['title'] = u'Finalizar Actividad'
                    data['citaasesoria'] = CitaAsesoria.objects.get(pk=int(encrypt(request.GET['id'])))

                    template = get_template("adm_asesoriainvestigacion/modal/gestionarcita.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'finalizaractividaddia':
                try:
                    data['title'] = u'Finalizar Actividades de Gestión del día'
                    data['responsableservicio'] = ResponsableServicio.objects.get(status=True, responsable=persona, vigente=True, estado=2)
                    data['fecha'] = request.GET['fecha']
                    template = get_template("adm_asesoriainvestigacion/modal/finalizaractividaddia.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'anexoscita':
                try:
                    data['title'] = u'Anexos de la Cita'
                    citaasesoria = CitaAsesoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['citaasesoria'] = citaasesoria
                    data['tipoanexos'] = ", ".join(variable_valor("TIPOS_ANEXOS_ASESORIAS_INV"))
                    data['tamanio'] = variable_valor("TAMANIO_ANEXOS_ASESORIAS_INV")
                    data['obligatorio'] = 'N'
                    template = get_template("adm_asesoriainvestigacion/modal/anexocita.html")
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

                    # Aqui se debe identificar si el usuario es el coordinador, responsable de gestión o del servicio
                    if persona.es_coordinador_investigacion():
                        tipovista = 'CI'
                    elif Gestion.objects.values("id").filter(status=True, responsable=persona).exists():
                        tipovista = 'RG'
                    elif ResponsableServicio.objects.values("id").filter(status=True, responsable=persona).exists():
                        tipovista = 'RS'

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
                    data['tipovista'] = tipovista

                    return render(request, "adm_asesoriainvestigacion/reagendarcita.html", data)
                except Exception as ex:
                    pass

            elif action == 'derivarcita':
                try:
                    data['title'] = u'Derivar Cita para Asesoría en Investigación'
                    data['cita'] = cita = CitaAsesoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['fecha'] = datetime.now() if cita.fecha == datetime.now().date() else datetime.combine(cita.fecha, cita.horainicio)
                    data['anio'] = datetime.now().date().year
                    data['mes'] = datetime.now().date().month

                    # Aqui se debe identificar si el usuario es el coordinador, responsable de gestión o del servicio
                    if persona.es_coordinador_investigacion():
                        tipovista = 'CI'
                    else:
                        tipovista = 'RG'

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
                    data['tipovista'] = tipovista

                    return render(request, "adm_asesoriainvestigacion/derivarcita.html", data)
                except Exception as ex:
                    pass

            elif action == 'asesoriaorigen':
                try:
                    title = u'Información de la Asesoría que derivó a la Cita actual'
                    citaasesoria = CitaAsesoria.objects.get(pk=int(encrypt(request.GET['id'])))

                    data['detalleasesoria'] = detalleasesoria = citaasesoria.asesoria_origen()
                    data['citaasesoria'] = detalleasesoria.citaasesoria

                    template = get_template("adm_asesoriainvestigacion/modal/informacionasesoria.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cancelarcita':
                try:
                    data['title'] = u'Cancelar Cita'
                    data['citaasesoria'] = CitaAsesoria.objects.get(pk=int(encrypt(request.GET['id'])))

                    template = get_template("adm_asesoriainvestigacion/modal/cancelarcita.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'citasasesoria':
                try:
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True, tipo=1), '&action=' + action
                    tipovista = tipo_vista_gestion_asesoria(persona)

                    if tipovista == 'RG':
                        filtro = filtro & (Q(servicio__gestion__responsable=persona))
                    elif tipovista == 'RS':
                        filtro = filtro & (Q(responsable=persona))

                    if search:
                        data['s'] = search
                        ss = search.split(" ")
                        if len(ss) == 1:
                            filtro = filtro & (Q(solicitante__nombres__icontains=search) |
                                               Q(solicitante__apellido1__icontains=search) |
                                               Q(solicitante__apellido2__icontains=search))
                        else:
                            filtro = filtro & (Q(solicitante__apellido1__contains=ss[0]) &
                                               Q(solicitante__apellido2__contains=ss[1]))

                        url_vars += '&s=' + search

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
                    data['url_vars'] = url_vars
                    data['citasasesorias'] = page.object_list
                    data['title'] = u'Citas para Asesorías en Investigación'
                    data['tipovista'] = tipovista

                    return render(request, "adm_asesoriainvestigacion/citaasesoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'gestionarasesoria':
                try:
                    citaasesoria = CitaAsesoria.objects.get(pk=int(encrypt(request.GET['id'])))

                    # Obtener fecha en letras
                    fecha = citaasesoria.fecha
                    inicio = datetime.combine(citaasesoria.fecha, citaasesoria.horainicio) - timedelta(minutes=5) # Para que pueda abrir la pantalla 5 minutos antes

                    if datetime.now().date() == fecha:
                        if inicio.time() <= datetime.now().time() <= citaasesoria.horafin:
                            return JsonResponse({"result": "ok"})
                        elif datetime.now().time() < inicio.time():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"Usted podrá gestionar la cita a partir de las <b>{inicio.time().strftime('%H:%M')}</b>", "showSwal": "True", "swalType": "warning"})
                        else:
                            return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "ok"})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al obtener los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

            elif action == 'cambioresponsable':
                try:
                    data['title'] = u'Cambio de Responsable - Cita para Asesoría en Investigación'
                    data['citaasesoria'] = citaasesoria = CitaAsesoria.objects.get(pk=int(encrypt(request.GET['id'])))
                    lista = []
                    responsablesservicio = ResponsableServicio.objects.filter(status=True, vigente=True, estado=2, servicioresponsableservicio__servicio=citaasesoria.servicio, servicioresponsableservicio__vigente=True, servicioresponsableservicio__status=True).exclude(responsable=citaasesoria.responsable).distinct().order_by('responsable__apellido1', 'responsable__apellido2', 'responsable__nombres')
                    for responsableservicio in responsablesservicio:
                        if not CitaAsesoria.objects.values("id").filter(status=True, tipo=1, responsable=responsableservicio.responsable, fecha=citaasesoria.fecha, horainicio=citaasesoria.horainicio).exists():
                            lista.append({"id": responsableservicio.id, "nombres": responsableservicio.responsable.nombre_completo_inverso()})

                    data['responsablesservicio'] = lista
                    template = get_template("adm_asesoriainvestigacion/modal/cambioresponsable.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al obtener los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

            return HttpResponseRedirect(request.path)
        else:
            try:
                # Aqui se debe identificar si el usuario es el coordinador, responsable de gestión o del servicio
                tipovista = tipo_vista_gestion_asesoria(persona)

                if tipovista != 'RS':
                    gestiones = Gestion.objects.filter(status=True).order_by('nombre')
                    servicios = ServicioGestion.objects.filter(status=True).order_by('nombre')
                    responsables = Persona.objects.filter(responsableservicio__status=True, responsableservicio__vigente=True).distinct().order_by('apellido1', 'apellido2', 'nombres')
                else:
                    gestiones = Gestion.objects.filter(status=True, serviciogestion__servicioresponsableservicio__responsableservicio__responsable=persona).distinct().order_by('nombre')
                    servicios = ServicioGestion.objects.filter(status=True, servicioresponsableservicio__responsableservicio__responsable=persona, servicioresponsableservicio__vigente=True).order_by('nombre')
                    responsables = Persona.objects.filter(responsableservicio__status=True, responsableservicio__responsable=persona).distinct()

                estados = [{"id": "1", "descripcion": "PENDIENTE"},
                           {"id": "5", "descripcion": "FINALIZADA"},
                           {"id": "6", "descripcion": "DISPONIBLE"}]

                fechaactual = datetime.now().date()
                data['anio'] = fechaactual.year
                data['semana'] = fechaactual.isocalendar()[1]
                data['tipovista'] = tipovista
                data['gestiones'] = gestiones
                data['servicios'] = servicios
                data['responsables'] = responsables
                data['estados'] = estados
                data['title'] = u'Agenda de Citas para Asesorías en Investigación'
                data['enlaceatras'] = "/ges_investigacion"

                return render(request, "adm_asesoriainvestigacion/view.html", data)
            except Exception as ex:
                pass
