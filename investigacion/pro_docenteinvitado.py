# -*- coding: UTF-8 -*-
import io
import json
import os
import calendar
from math import ceil
import zipfile
from core.firmar_documentos_ec import JavaFirmaEc

import PyPDF2
from datetime import time, datetime, timedelta, date
from decimal import Decimal
from calendar import monthrange

import requests
import xlsxwriter
from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q, ExpressionWrapper, F, DurationField
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
import time as pausaparaemail
from django.core.files import File as DjangoFile
from fitz import fitz
from xlwt import easyxf, XFStyle, Workbook
import random
from decorators import secure_module
from investigacion.forms import HorarioServicioForm
from investigacion.funciones import FORMATOS_CELDAS_EXCEL, notificar_docente_invitado, iniciales_nombres_apellidos, vicerrector_investigacion_posgrado, getmonthname, decano_investigacion, analista_verifica_informe_docente_invitado, isvalidurl, director_escuela_investigacion, \
    reemplazar_fuente_para_informe, guardar_recorrido_informe_docente_invitado, secuencia_informe_docente_invitado, extension_archivo
from investigacion.models import DocenteInvitado, FuncionDocenteInvitado, HorarioDocenteInvitado, DetalleHorarioDocenteInvitado, ESTADO_CUMPLIMIENTO_ACTIVIDAD, InformeDocenteInvitado, AnexoInformeDocenteInvitado, ActividadInformeDocenteInvitado, ActividadCriterioDocenteInvitado, \
    ConclusionRecomendacionInformeDocenteInvitado, TIPO_ANEXO, RecorridoInformeDocenteInvitado
from sagest.commonviews import obtener_estado_solicitud, obtener_estados_solicitud
from settings import SITE_STORAGE
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, variable_valor, \
    convertir_fecha, remover_caracteres_tildes_unicode, cuenta_email_disponible, generar_nombre, email_valido, \
    validar_archivo, null_to_decimal, cuenta_email_disponible_para_envio, fechaletra_corta, fecha_letra_rango, dia_semana_enletras_fecha, remover_atributo_style_html
from sga.funcionesxhtml2pdf import convert_html_to_pdf
from sga.models import CUENTAS_CORREOS, Persona, MESES_CHOICES, Profesor, Modalidad, Turno
from django.template import Context
from django.template.loader import get_template

import time as ET
import collections
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

    if not es_profesor:
        return HttpResponseRedirect("/?info=El Módulo está disponible para docentes.")

    profesor = persona.profesor()
    if not profesor.categoria.id == 2:
        return HttpResponseRedirect("/?info=El Módulo está disponible para docentes invitados.")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'actualizarhorario':
            try:
                if 'idh' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar horario, la función o actividad, turno
                horario = HorarioDocenteInvitado.objects.get(pk=int(encrypt(request.POST['idh'])))
                funcion = FuncionDocenteInvitado.objects.get(pk=int(encrypt(request.POST['idf'])))
                turno = Turno.objects.get(pk=int(encrypt(request.POST['idt'])))
                dia = int(encrypt(request.POST['dia']))
                marcado = request.POST['valor'] == 'S'

                # Si la casilla está marcada debo crear o actualizar
                if marcado:
                    # Validar que no haya completado el total de horas a planificar
                    if horario.horaplanificada + 1 > horario.totalhora:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No puede seleccionar la hora debido a que ya ha completado el total de horas a planificar", "showSwal": "True", "swalType": "warning"})

                    # Si no existe el detalle lo creo
                    if not horario.detallehorariodocenteinvitado_set.values("id").filter(turno=turno, dia=dia, funcion=funcion).exists():
                        detallehorario = DetalleHorarioDocenteInvitado(
                            horario=horario,
                            turno=turno,
                            dia=dia,
                            funcion=funcion
                        )
                        detallehorario.save(request)
                    else:
                        # Actualizo el estado que previamente fue False por haber desmarcado la casilla
                        detallehorario = horario.detallehorariodocenteinvitado_set.filter(status=False, turno=turno, dia=dia, funcion=funcion)[0]
                        detallehorario.status = True
                        detallehorario.save(request)
                else:
                    # Actualizo el estado
                    detallehorario = horario.detallehorariodocenteinvitado_set.filter(turno=turno, dia=dia, funcion=funcion)[0]
                    detallehorario.status = False
                    detallehorario.save(request)

                # Actualizar total de horas planificadas
                horario.horaplanificada = horario.total_horas_planificadas()
                horario.estado = 2
                horario.observacion = ''
                horario.save(request)

                horasfuncion = funcion.total_horas_asignadas_horario(horario)
                textohoras = f"{horario.horaplanificada} de {horario.totalhora} horas"

                log(u'{} actualizó horario de actividades: {}'.format(persona, horario), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True, "horasfuncion": horasfuncion, "textohoras": textohoras, "confirmar": "S" if horario.horaplanificada == horario.totalhora else "N"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'confirmarhorario':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                horario = HorarioDocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))

                # Actualizar del horario
                horario.estado = 3
                horario.observacion = ''
                horario.save(request)

                # Notificar por e-mail
                notificar_docente_invitado(horario, "REGHOR")

                log(u'%s confirmó horario de actividades del mes de [ %s ]' % (persona, MESES_CHOICES[horario.inicio.month - 1][1].capitalize()), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al actualizar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addinforme':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                docente = DocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))
                fi = str(int(encrypt(request.POST['finicio'])))
                ff = str(int(encrypt(request.POST['ffin'])))
                inicio = datetime.strptime(f'{fi[0:4]}-{fi[4:6]}-{fi[6:8]}', '%Y-%m-%d').date()
                fin = datetime.strptime(f'{ff[0:4]}-{ff[4:6]}-{ff[6:8]}', '%Y-%m-%d').date()
                diaslaborados = monthrange(inicio.year, inicio.month)[1]

                secuencia = secuencia_informe_docente_invitado(inicio.year, 1)
                numero = f'{str(secuencia).zfill(3)}-PI-EFI-FI-{iniciales_nombres_apellidos(docente.profesor.persona)}-{inicio.year}'

                # Validar que no esté repetido el número del informe
                if not InformeDocenteInvitado.objects.filter(status=True, numero=numero).exists():
                    # Validar que no hay colocado imágenes en la motivación técnica
                    if '<img' in request.POST['motivaciontecnica'].strip():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"La motivación técnica no debe contener imágenes en el contenido", "showSwal": "True", "swalType": "warning"})

                    # Obtiene los valores del detalle de actividades
                    idsactividades = request.POST.getlist('idactividad[]')
                    idsactividadmed = request.POST.getlist('idactividadmed[]')
                    idsactividadnomed = request.POST.getlist('idactividadnomed[]')
                    nfilasactimed = request.POST.getlist('nfilaactimed[]')
                    planificados = request.POST.getlist('planificado[]')
                    ejecutados = request.POST.getlist('ejecutado[]')
                    estados = request.POST.getlist('estado[]')

                    # Obtiene los valores de los arreglos del detalle de conclusiones y recomendaciones
                    descripciones_conclusiones = request.POST.getlist('descripcion_conclusion[]')
                    descripciones_recomendaciones = request.POST.getlist('descripcion_recomendacion[]')

                    # Validar los estados asignados
                    for nfilaacti, planificado, ejecutado, estado in zip(nfilasactimed, planificados, ejecutados, estados):
                        planificado = int(planificado)
                        ejecutado = int(ejecutado)
                        estado = int(estado)

                        if estado == 1:
                            if ejecutado > 0:
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"El valor del campo ejecutado debe ser igual a <b>0</b> en la fila # <b>{nfilaacti}</b> del detalle de avance de actividades y productos", "showSwal": "True", "swalType": "warning"})
                        elif estado == 2:
                            if ejecutado >= planificado:
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"El valor del campo ejecutado debe ser menor a <b>{planificado}</b> en la fila # <b>{nfilaacti}</b> del detalle de avance de actividades y productos", "showSwal": "True", "swalType": "warning"})
                        elif estado == 3:
                            if ejecutado < 1 or ejecutado >= planificado:
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"El valor del campo ejecutado debe ser mayor o igual a <b>1</b> y menor a <b>{planificado}</b> en la fila # <b>{nfilaacti}</b> del detalle de avance de actividades y productos", "showSwal": "True", "swalType": "warning"})
                        else:
                            if ejecutado < planificado:
                                return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"El valor del campo ejecutado debe ser mayor o igual a <b>{planificado}</b> en la fila # <b>{nfilaacti}</b> del detalle de avance de actividades y productos", "showSwal": "True", "swalType": "warning"})

                    elabora = docente.profesor.persona
                    directorefi = None
                    decano = decano_investigacion()
                    analista = analista_verifica_informe_docente_invitado()

                    # Guardar informe
                    informedocente = InformeDocenteInvitado(
                        tipo=1,
                        docente=docente,
                        secuencia=secuencia,
                        fecha=datetime.now(),
                        numero=numero,
                        inicio=inicio,
                        fin=fin,
                        dialaborado=diaslaborados,
                        remitente=elabora,
                        cargoremitente=None,
                        destinatario=decano,
                        cargodestinatario=decano.mi_cargo_actual().denominacionpuesto,
                        objeto=f'Informe técnico de actividades ejecutadas en el mes de {getmonthname(inicio).capitalize()} del {inicio.year}',
                        motivaciontecnica=reemplazar_fuente_para_informe(request.POST['motivaciontecnica'].strip()),
                        impreso=False,
                        elabora=elabora,
                        cargoelabora=None,
                        valida=analista,
                        cargovalida=analista.mi_cargo_actual().denominacionpuesto,
                        aprueba=None,
                        cargoaprueba=None,
                        estado=1
                    )
                    informedocente.save(request)

                    # Guardar la actividad del informe
                    for idactividad in idsactividades:
                        # Guardar la actividad del informe
                        actividadinforme = ActividadInformeDocenteInvitado(
                            informe=informedocente,
                            actividad_id=idactividad,
                            planificado=None,
                            ejecutado=None,
                            estado=None
                        )
                        actividadinforme.save(request)

                    # Guardar cumplimiento de la actividad para los tipos medible
                    for idactividad, planificado, ejecutado, estado in zip(idsactividadmed, planificados, ejecutados, estados):
                        # Consultar y actualizar la actividad del docente
                        actividad = ActividadCriterioDocenteInvitado.objects.get(id=idactividad)
                        actividad.ejecutado = ejecutado
                        actividad.estado = estado
                        actividad.save(request)

                        # Consultar y actualizar la actividad del informe
                        actividadinforme = ActividadInformeDocenteInvitado.objects.get(actividad=actividad, informe=informedocente)
                        actividadinforme.planificado = planificado
                        actividadinforme.ejecutado = ejecutado
                        actividadinforme.estado = estado
                        actividadinforme.save(request)

                    # Guardar conclusiones
                    for descripcion in descripciones_conclusiones:
                        conclusion = ConclusionRecomendacionInformeDocenteInvitado(
                            informe=informedocente,
                            descripcion=descripcion.strip(),
                            tipo=1
                        )
                        conclusion.save(request)

                    # Guardar recomendaciones
                    for descripcion in descripciones_recomendaciones:
                        recomendacion = ConclusionRecomendacionInformeDocenteInvitado(
                            informe=informedocente,
                            descripcion=descripcion.strip(),
                            tipo=2
                        )
                        recomendacion.save(request)

                    # Obtengo estado EN EDICIÓN
                    estadoregistro = obtener_estado_solicitud(23, 1)

                    # Guardar el recorrido
                    guardar_recorrido_informe_docente_invitado(informedocente, estadoregistro, 'INFORME AGREGADO POR EL DOCENTE', request)

                    log(u'%s agregó informe de actividades: %s' % (persona, informedocente), request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El número de informe ya ha sido ingresado", "showSwal": "True", "swalType": "warning"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editinforme':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                informedocente = InformeDocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))

                # Obtiene los valores del detalle de actividades
                idsregactividades = request.POST.getlist('idregactividad[]')
                idsactividadmed = request.POST.getlist('idactividadmed[]')
                idsactividadnomed = request.POST.getlist('idactividadnomed[]')
                nfilasactimed = request.POST.getlist('nfilaactimed[]')
                planificados = request.POST.getlist('planificado[]')
                ejecutados = request.POST.getlist('ejecutado[]')
                estados = request.POST.getlist('estado[]')

                # Obtiene los valores de los arreglos del detalle de conclusiones y recomendaciones
                ids_conclusiones = request.POST.getlist('idregcon[]')
                descripciones_conclusiones = request.POST.getlist('descripcion_conclusion[]')
                conclelim = json.loads(request.POST['lista_items1']) if 'lista_items1' in request.POST else []  # Ids registros de conclusiones borradas

                ids_recomendaciones = request.POST.getlist('idregreco[]')
                descripciones_recomendaciones = request.POST.getlist('descripcion_recomendacion[]')
                recoelim = json.loads(request.POST['lista_items2']) if 'lista_items2' in request.POST else []  # Ids registros de recomendaciones borradas

                # Validar los estados asignados
                for nfilaacti, planificado, ejecutado, estado in zip(nfilasactimed, planificados, ejecutados, estados):
                    planificado = int(planificado)
                    ejecutado = int(ejecutado)
                    estado = int(estado)

                    if estado == 1:
                        if ejecutado > 0:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"El valor del campo ejecutado debe ser igual a <b>0</b> en la fila # <b>{nfilaacti}</b> del detalle de avance de actividades y productos", "showSwal": "True", "swalType": "warning"})
                    elif estado == 2:
                        if ejecutado >= planificado:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"El valor del campo ejecutado debe ser menor a <b>{planificado}</b> en la fila # <b>{nfilaacti}</b> del detalle de avance de actividades y productos", "showSwal": "True", "swalType": "warning"})
                    elif estado == 3:
                        if ejecutado < 1 or ejecutado >= planificado:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"El valor del campo ejecutado debe ser mayor o igual a <b>1</b> y menor a <b>{planificado}</b> en la fila # <b>{nfilaacti}</b> del detalle de avance de actividades y productos", "showSwal": "True", "swalType": "warning"})
                    else:
                        if ejecutado < planificado:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"El valor del campo ejecutado debe ser mayor o igual a <b>{planificado}</b> en la fila # <b>{nfilaacti}</b> del detalle de avance de actividades y productos", "showSwal": "True", "swalType": "warning"})

                # Actualizar informe
                informedocente.motivaciontecnica = reemplazar_fuente_para_informe(request.POST['motivaciontecnica'].strip())
                informedocente.impreso = False
                informedocente.archivo = None
                informedocente.archivofirmado = None
                informedocente.observacion = ''
                informedocente.firmaelabora = False
                informedocente.firmaverifica = False
                informedocente.firmaaprueba = False
                informedocente.estado = 1
                informedocente.save(request)

                # Guardar cumplimiento de la actividad (sólo medibles)
                for idactividad, planificado, ejecutado, estado in zip(idsactividadmed, planificados, ejecutados, estados):
                    # Consultar actividad
                    actividad = ActividadCriterioDocenteInvitado.objects.get(pk=idactividad)
                    actividadinforme = ActividadInformeDocenteInvitado.objects.get(actividad=actividad, informe=informedocente)

                    # Actualizar la actividad del docente
                    actividad.ejecutado = ejecutado
                    actividad.estado = estado
                    actividad.save(request)

                    # Actualizar la actividad del informe
                    actividadinforme.ejecutado = ejecutado
                    actividadinforme.estado = estado
                    actividadinforme.save(request)

                # Guardar conclusiones
                for idreg, descripcion in zip(ids_conclusiones, descripciones_conclusiones):
                    # Si es registro nuevo
                    if int(idreg) == 0:
                        conclusion = ConclusionRecomendacionInformeDocenteInvitado(
                            informe=informedocente,
                            descripcion=descripcion.strip(),
                            tipo=1
                        )
                    else:
                        conclusion = ConclusionRecomendacionInformeDocenteInvitado.objects.get(pk=idreg)
                        conclusion.descripcion = descripcion.strip()

                    conclusion.save(request)

                # Elimino conclusiones
                if conclelim:
                    for registro in conclelim:
                        conclusion = ConclusionRecomendacionInformeDocenteInvitado.objects.get(pk=registro['idreg'])
                        conclusion.status = False
                        conclusion.save(request)

                # Guardar recomendaciones
                for idreg, descripcion in zip(ids_recomendaciones, descripciones_recomendaciones):
                    # Si es registro nuevo
                    if int(idreg) == 0:
                        recomendacion = ConclusionRecomendacionInformeDocenteInvitado(
                            informe=informedocente,
                            descripcion=descripcion.strip(),
                            tipo=2
                        )
                    else:
                        recomendacion = ConclusionRecomendacionInformeDocenteInvitado.objects.get(pk=idreg)
                        recomendacion.descripcion = descripcion.strip()

                    recomendacion.save(request)

                # Elimino recomendaciones
                if recoelim:
                    for registro in recoelim:
                        recomendacion = ConclusionRecomendacionInformeDocenteInvitado.objects.get(pk=registro['idreg'])
                        recomendacion.status = False
                        recomendacion.save(request)

                # Obtengo estado EN EDICIÓN
                estadoregistro = obtener_estado_solicitud(23, 1)

                # Guardar el recorrido
                guardar_recorrido_informe_docente_invitado(informedocente, estadoregistro, 'INFORME EDITADO POR EL DOCENTE', request)

                log(u'%s editó informe de actividades: %s' % (persona, informedocente), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addanexoinforme':
            try:
                if 'idactividadinforme' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                actividadinforme = ActividadInformeDocenteInvitado.objects.get(pk=int(encrypt(request.POST['idactividadinforme'])))
                informedocente = actividadinforme.informe

                # Obtengo los valores del formulario
                tipo = int(request.POST['tipo'])
                descripcion = request.POST['descripcion'].strip()
                archivo = request.FILES['archivo'] if tipo == 1 else None
                fechagenera = informedocente.fecha
                numeropagina = None
                url = request.POST['url'].strip() if tipo == 2 else None

                # Validar archivo o url
                if tipo == 1:
                    descripcionarchivo = 'Archivo del anexo'
                    resp = validar_archivo(descripcionarchivo, archivo, variable_valor("TIPOS_ANEXOS_INFORME_DINVITADO"), variable_valor("TAMANIO_ANEXOS_INFORME_DINVITADO"))
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})
                else:
                    if not isvalidurl(url):
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"La url del enlace no es válida", "showSwal": "True", "swalType": "warning"})

                # Guardar el anexo
                anexoinforme = AnexoInformeDocenteInvitado(
                    informe=informedocente,
                    actividad=actividadinforme,
                    descripcion=descripcion.strip(),
                    fechagenera=fechagenera,
                    numeropagina=numeropagina,
                    url=url,
                    tipo=tipo
                )
                anexoinforme.save(request)

                if tipo == 1:
                    # actualizo campo archivo del registro creado
                    archivoreg = archivo
                    archivoreg._name = generar_nombre("anexo", archivoreg._name)
                    anexoinforme.archivo = archivoreg
                    anexoinforme.save(request)

                # Actualizo el informe
                informedocente.impreso = False
                informedocente.archivo = None
                informedocente.archivofirmado = None
                informedocente.observacion = ''
                informedocente.firmaelabora = False
                informedocente.firmaverifica = False
                informedocente.firmaaprueba = False
                informedocente.documentosoporte = None
                informedocente.estado = 1
                informedocente.save(request)

                # Cargo la sección del detalle de anexos para la actividad
                data['actividadinforme'] = actividadinforme
                data['numacti'] = request.POST['numacti']
                data['detalles'] = informedocente.anexos_actividad(actividadinforme)
                totalanexo = informedocente.total_anexo_actividad(actividadinforme)
                template = get_template("pro_docenteinvitado/secciondetalleactividad.html")
                json_content = template.render(data)

                log(u'% agregó anexo a la actividad: %s - %s' % (persona, anexoinforme, actividadinforme), request, "add")
                return JsonResponse({"result": "ok", "idacti": actividadinforme.id, "totalanexo": totalanexo, 'data': json_content, "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editanexoinforme':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                anexoinforme = AnexoInformeDocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))
                informedocente = anexoinforme.informe
                tipo = anexoinforme.tipo

                # Obtengo los valores del formulario
                descripcion = request.POST['descripcione'].strip()
                if tipo == 1:
                    archivo = request.FILES['archivoe'] if 'archivoe' in request.FILES else None
                    # numeropagina = request.POST['numeropaginae']
                else:
                    archivo = None
                    # numeropagina = None

                # fechagenera = datetime.strptime(request.POST['fechagenerae'], '%Y-%m-%d').date() if tipo == 1 else None
                url = request.POST['urle'].strip() if tipo == 2 else None

                # Validar archivo o url
                if tipo == 1:
                    if archivo:
                        descripcionarchivo = 'Archivo del anexo'
                        resp = validar_archivo(descripcionarchivo, archivo, variable_valor("TIPOS_ANEXOS_INFORME_DINVITADO"), variable_valor("TAMANIO_ANEXOS_INFORME_DINVITADO"))
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})
                else:
                    if not isvalidurl(url):
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"La url del enlace no es válida", "showSwal": "True", "swalType": "warning"})

                # Actualizar el anexo
                anexoinforme.descripcion = descripcion.strip()
                # anexoinforme.fechagenera = fechagenera
                # anexoinforme.numeropagina = numeropagina
                anexoinforme.url = url
                anexoinforme.save(request)

                if tipo == 1 and archivo:
                    # actualizo campo archivo del registro creado
                    archivoreg = archivo
                    archivoreg._name = generar_nombre("anexo", archivoreg._name)
                    anexoinforme.archivo = archivoreg
                    anexoinforme.numeropagina = numeropagina
                    anexoinforme.save(request)

                # Actualizo el informe
                informedocente.impreso = False
                informedocente.archivo = None
                informedocente.archivofirmado = None
                informedocente.observacion = ''
                informedocente.firmaelabora = False
                informedocente.firmaverifica = False
                informedocente.firmaaprueba = False
                informedocente.documentosoporte = None
                informedocente.estado = 1
                informedocente.save(request)

                # Cargo la sección del detalle de anexos para la actividad
                data['actividadinforme'] = actividadinforme = anexoinforme.actividad
                data['numacti'] = request.POST['numacti']
                data['detalles'] = informedocente.anexos_actividad(anexoinforme.actividad)
                totalanexo = informedocente.total_anexo_actividad(anexoinforme.actividad)
                template = get_template("pro_docenteinvitado/secciondetalleactividad.html")
                json_content = template.render(data)

                log(u'%s editó anexo de la actividad: %s - %s' % (persona, anexoinforme, anexoinforme.actividad), request, "edit")
                return JsonResponse({"result": "ok", "idacti": actividadinforme.id, "totalanexo": totalanexo, 'data': json_content, "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'delanexoinforme':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                anexoinforme = AnexoInformeDocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))
                actividad = anexoinforme.actividad
                informedocente = anexoinforme.informe

                # Elimino el anexo
                anexoinforme.status = False
                anexoinforme.save(request)

                # Actualizo el informe
                informedocente.impreso = False
                informedocente.archivo = None
                informedocente.archivofirmado = None
                informedocente.observacion = ''
                informedocente.firmaelabora = False
                informedocente.firmaverifica = False
                informedocente.firmaaprueba = False
                informedocente.documentosoporte = None
                informedocente.estado = 1
                informedocente.save(request)

                # Consulto los totales
                totalanexo = informedocente.total_anexo_actividad(actividad)

                log(u'%s eliminó anexo del informe: %s' % (persona, anexoinforme), request, "del")
                return JsonResponse({"result": "ok", "totalanexo": totalanexo, "titulo": "Proceso exitoso!!!", "mensaje": u"Registro eliminado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al eliminar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'generarenlace':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                directorio = os.path.join(os.path.join(SITE_STORAGE, 'media', 'zipav'))

                # Consultar el informe
                informedocente = InformeDocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))
                fechaactual = datetime.now().date()
                archivoenlaces = None

                if informedocente.anexos_enlace():
                    # Generar documento que contiene los anexos tipo enlace
                    data['informedocente'] = informedocente
                    nombrearchivo = 'listaenlace_' + str(informedocente.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                    valida = convert_html_to_pdf(
                        'pro_docenteinvitado/anexoenlacepdf.html',
                        {'pagesize': 'A4', 'data': data},
                        nombrearchivo,
                        directorio
                    )

                    if not valida:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al generar documento del listado de enlaces."})

                    archivoenlaces = directorio + "/" + nombrearchivo

                mes = getmonthname(informedocente.inicio)
                anio = informedocente.inicio.year
                nombre_archivo = informedocente.numero.replace("-", "_")
                nombre_archivo = generar_nombre(f'{nombre_archivo}_', f'{nombre_archivo}_.zip')
                filename = os.path.join(directorio, nombre_archivo)
                fantasy_zip = zipfile.ZipFile(filename, 'w')

                subcarpeta = ""

                if archivoenlaces:
                    nombreanexo = f"enlaces"
                    ext = ".pdf"
                    fantasy_zip.write(archivoenlaces, subcarpeta + "/" + nombreanexo + ext.lower())

                # Agregar los anexos tipo archivo
                for detalle in informedocente.anexos_archivo():
                    nombreanexo = f"anexo{str(detalle.id).zfill(3)}"
                    ext = extension_archivo(detalle.archivo.name)

                    if os.path.exists(SITE_STORAGE + detalle.archivo.url):
                        fantasy_zip.write(SITE_STORAGE + detalle.archivo.url, subcarpeta + "/" + nombreanexo + ext.lower())

                fantasy_zip.close()

                archivo = directorio + "/" + nombre_archivo

                # Aperturo el archivo generado
                with open(archivo, 'rb') as f:
                    data = f.read()

                buffer = io.BytesIO()
                buffer.write(data)
                pdfcopia = buffer.getvalue()
                buffer.seek(0)
                buffer.close()

                # Extraigo el contenido
                archivocopiado = ContentFile(pdfcopia)
                archivocopiado.name =  nombre_archivo

                # Actualizo el informe
                informedocente.documentosoporte = archivocopiado
                informedocente.fechadocumento = datetime.now().date()
                informedocente.save(request)

                # Borro el archivo lista de enlaces y el informe creado de manera general, no la del registro
                if archivoenlaces:
                    os.remove(archivoenlaces)

                os.remove(archivo)

                log(u'%s generó enlace de descarga de evidencias para informe: %s' % (persona, informedocente), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Enlace generado con éxito", "showSwal": True, "documento": informedocente.documentosoporte.url})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar el enlace. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'informetecnicopdf':
            try:
                data = {}

                informedocente = InformeDocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))

                if not informedocente.impreso:
                    data['informe'] = informedocente
                    data['docente'] = informedocente.docente
                    data['actividades'] = informedocente.actividades()
                    data['conclusiones'] = informedocente.conclusiones()
                    data['recomendaciones'] = informedocente.recomendaciones()
                    data['anexos'] = informedocente.anexos()

                    # Creacion de los archivos por separado
                    directorio = SITE_STORAGE + '/media/proyectoinvestigacion/informes'
                    try:
                        os.stat(directorio)
                    except:
                        os.mkdir(directorio)

                    # Archivo de la parte 1 del informe
                    nombrearchivo = 'informeparte1_' + str(informedocente.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                    valida = convert_html_to_pdf(
                        'pro_docenteinvitado/informetecnicopdf.html',
                        {'pagesize': 'A4', 'data': data},
                        nombrearchivo,
                        directorio
                    )

                    if not valida:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al generar documento de la parte 1 del informe."})

                    archivo1 = directorio + "/" + nombrearchivo

                    # Leer los archivos
                    pdf1Reader = PyPDF2.PdfFileReader(archivo1)

                    # Crea un nuevo objeto PdfFileWriter que representa un documento PDF en blanco
                    pdfWriter = PyPDF2.PdfFileWriter()

                    # Recorre todas las páginas del documento 1
                    for pageNum in range(pdf1Reader.numPages):
                        pageObj = pdf1Reader.getPage(pageNum)
                        pdfWriter.addPage(pageObj)

                    # Luego de haberse copiado todas las paginas de todos los documentos, se las escribe en el documento en blanco
                    nombrearchivoresultado = generar_nombre('informeactividades', 'informeactividades.pdf')
                    pdfOutputFile = open(directorio + "/" + nombrearchivoresultado, "wb")
                    pdfWriter.write(pdfOutputFile)

                    # Borro los documento individuales creados a exepción del archivo del proyecto cargado por el docente
                    os.remove(archivo1)

                    pdfOutputFile.close()

                    # archivo = SITE_STORAGE + '/media/certificadoedocente/' + nombrearchivoresultado
                    archivo = directorio + "/" + nombrearchivoresultado

                    # Aperturo el archivo generado
                    with open(archivo, 'rb') as f:
                        data = f.read()

                    buffer = io.BytesIO()
                    buffer.write(data)
                    pdfcopia = buffer.getvalue()
                    buffer.seek(0)
                    buffer.close()

                    # Extraigo el contenido
                    archivocopiado = ContentFile(pdfcopia)
                    archivocopiado.name = nombrearchivoresultado

                    # Actualizo el informe
                    informedocente.impreso = True
                    informedocente.archivo = archivocopiado
                    informedocente.save(request)

                    # Borro el informe creado de manera general, no la del registro
                    os.remove(archivo)

                    log(u'%s generó informe de actividades: %s' % (persona, informedocente), request, "edit")

                return JsonResponse({"result": "ok", "idi": encrypt(informedocente.id), "id": encrypt(informedocente.docente.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar documento del informe. [%s]" % msg})

        elif action == 'firmarinforme':
            try:
                if 'iddoc' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                archivofirma = request.FILES['archivofirma']
                clavefirma = request.POST['cfirma']
                descripcionarchivo = 'Archivo de la firma electrónica'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivofirma, ['P12', 'PFX'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto el informe
                informe = InformeDocenteInvitado.objects.get(pk=int(encrypt(request.POST['iddoc'])))

                # Obtengo el archivo del informe
                archivoinforme = informe.archivo
                rutapdfarchivo = SITE_STORAGE + archivoinforme.url
                textoabuscar = informe.docente.nombrefirma
                textofirma = 'Elaborado por:'
                ocurrencia = 1

                vecesencontrado = 0
                # ocurrencia = 5

                # Obtener coordenadas para ubicar al firma dependiendo de donde se encuentra ubicado el nombre de la persona
                documento = fitz.open(rutapdfarchivo)
                # numpaginafirma = int(documento.page_count) - 1

                # Busca la página donde se encuentran ubicados los textos: Elaboraro por, Verificado por y Aprobado por
                words_dict = {}
                encontrado = False
                for page_number, page in enumerate(documento):
                    words = page.get_text("blocks")
                    words_dict[0] = words

                    for cadena in words_dict[0]:
                        linea = cadena[4].replace("\n", " ")
                        if linea:
                            linea = linea.strip()

                        if textofirma in linea:
                            numpaginafirma = page_number
                            encontrado = True
                            break

                    if encontrado:
                        break

                # Obtener coordenadas para ubicar al firma dependiendo de donde se encuentra ubicado el nombre de la persona
                saltolinea = False
                words_dict = {}
                for page_number, page in enumerate(documento):
                    if page_number == numpaginafirma:
                        words = page.get_text("blocks")
                        words_dict[0] = words
                        break

                valor = None
                for cadena in words_dict[0]:
                    linea = cadena[4].replace("\n", " ")
                    if linea:
                        linea = linea.strip()

                    if textoabuscar in linea:
                        valor = cadena

                        vecesencontrado += 1
                        if vecesencontrado == ocurrencia:
                            break

                if valor:
                    y = 5000 - int(valor[3]) - 4120
                else:
                    y = 0

                # x = 87  # izq
                # x = 230  # cent
                x = 350  # der

                # Si no existe el nombre de la persona en el documento
                if y == 0:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"No se encuentra el nombre del firmante en el documento", "showSwal": "True", "swalType": "warning"})

                # Obtener extensión y leer archivo de la firma
                extfirma = os.path.splitext(archivofirma.name)[1][1:]
                bytesfirma = archivofirma.read()

                # Firma del documento
                datau = JavaFirmaEc(
                    archivo_a_firmar=archivoinforme,
                    archivo_certificado=bytesfirma,
                    extension_certificado=extfirma,
                    password_certificado=clavefirma,
                    page=numpaginafirma,
                    reason='',
                    lx=x,
                    ly=y
                ).sign_and_get_content_bytes()

                generar_archivo_firmado = io.BytesIO()
                generar_archivo_firmado.write(datau)
                generar_archivo_firmado.seek(0)

                nombre = "informeactividadesfirmado"

                nombrearchivofirmado = generar_nombre(nombre, nombre + '.pdf')
                objarchivo = DjangoFile(generar_archivo_firmado, nombrearchivofirmado)

                informe.archivofirmado = objarchivo
                informe.firmaelabora = True
                informe.estado = 2
                informe.save(request)

                # Obtengo estado FIRMADO POR DOCENTE
                estadoregistro = obtener_estado_solicitud(23, 3)

                # Guardar el recorrido
                guardar_recorrido_informe_docente_invitado(informe, estadoregistro, '', request)

                log(u'%s firmó informe técnico de actividades: %s' % (persona, informe), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Documento firmado con éxito", "showSwal": True, "idi": encrypt(informe.id), "id": encrypt(informe.docente.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'enviarinforme':
            try:
                # Consulto el informe
                informe = InformeDocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))

                # Actualizo el informe
                informe.fechaenvio = datetime.now()
                informe.estado = 3
                informe.save(request)

                # Obtengo estado ENVIADO
                estadoregistro = obtener_estado_solicitud(23, 4)

                # Guardar el recorrido
                guardar_recorrido_informe_docente_invitado(informe, estadoregistro, '', request)

                # Notificar por e-mail
                notificar_docente_invitado(informe, "ENVINF")

                log(u'%s envió informe de actividades: %s' % (persona, informe), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Informe de actividades enviado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Solicitud incorrecta.", "showSwal": "True", "swalType": "error"})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'horarios':
                try:
                    data['title'] = u'Horarios del Profesor Invitado'
                    data['docente'] = docenteinvitado = DocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['horarios'] = horarios = docenteinvitado.horarios_habilitados()
                    if horarios:
                        if horarios.filter(estado=5).exists():
                            data['horarionovedad'] = horarios.filter(estado=5)[0]

                    return render(request, "pro_docenteinvitado/horario.html", data)
                except Exception as ex:
                    pass

            elif action == 'horario':
                try:
                    data['title'] = u'Horario de Actividades'
                    data['horario'] = horario = HorarioDocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['docente'] = docenteinvitado = horario.docente
                    data['puedeeditar'] = puedeeditar = horario.puede_editar()
                    funciones = docenteinvitado.funciones_asignadas()
                    funcion1 = funciones[0]

                    lista_funciones = []
                    for funcion in funciones:
                        lista_funciones.append({"id": funcion.id, "descripcion": funcion.criterio.descripcion, "totalhoras": funcion.total_horas_asignadas_horario(horario)})

                    data['funciones'] = lista_funciones
                    data['diascab'] = dias = [{"numero": 1, "nombre": "Lunes", "ancho": 12},
                                              {"numero": 2, "nombre": "Martes", "ancho": 12},
                                              {"numero": 3, "nombre": "Miércoles", "ancho": 12},
                                              {"numero": 4, "nombre": "Jueves", "ancho": 12},
                                              {"numero": 5, "nombre": "Viernes", "ancho": 12},
                                              {"numero": 6, "nombre": "Sábado", "ancho": 12},
                                              {"numero": 7, "nombre": "Domingo", "ancho": 12}]
                    turnos = Turno.objects.filter(status=True, mostrar=True, sesion_id=20).order_by('comienza')
                    lista_turnos = []
                    for turno in turnos:
                        lista_dias_turno = []
                        for dia in dias:
                            if puedeeditar:
                                if not horario:
                                    lista_dias_turno.append({"numerodia": dia["numero"], "idturno": turno.id, "idfuncion": funcion1.id, "marcado": "N", "bloqueado": "N"})
                                else:
                                    if not horario.detallehorariodocenteinvitado_set.values("id").filter(status=True, turno=turno, dia=dia['numero']).exists():
                                        lista_dias_turno.append({"numerodia": dia["numero"], "idturno": turno.id, "idfuncion": funcion1.id, "marcado": "N", "bloqueado": "N"})
                                    elif horario.detallehorariodocenteinvitado_set.values("id").filter(status=True, turno=turno, dia=dia['numero'], funcion=funcion1).exists():
                                        lista_dias_turno.append({"numerodia": dia["numero"], "idturno": turno.id, "idfuncion": funcion1.id, "marcado": "S", "bloqueado": "N"})
                                    elif horario.detallehorariodocenteinvitado_set.values("id").filter(status=False, turno=turno, dia=dia['numero'], funcion=funcion1).exists():
                                        lista_dias_turno.append({"numerodia": dia["numero"], "idturno": turno.id, "idfuncion": funcion1.id, "marcado": "N", "bloqueado": "N"})
                                    else:
                                        lista_dias_turno.append({"numerodia": dia["numero"], "idturno": turno.id, "idfuncion": "0", "marcado": "S", "bloqueado": "S"})
                            else:
                                if horario.detallehorariodocenteinvitado_set.values("id").filter(status=True, turno=turno, dia=dia['numero'], funcion=funcion1).exists():
                                    lista_dias_turno.append({"numerodia": dia["numero"], "idturno": turno.id, "idfuncion": funcion1.id, "marcado": "S", "bloqueado": "N"})
                                else:
                                    lista_dias_turno.append({"numerodia": dia["numero"], "idturno": turno.id, "idfuncion": "0", "marcado": "N", "bloqueado": "S"})

                        lista_turnos.append({"turno": turno, "dias": lista_dias_turno})

                    data['turnos'] = lista_turnos
                    return render(request, "pro_docenteinvitado/edithorario.html", data)
                except Exception as ex:
                    pass

            elif action == 'detallehorario':
                try:
                    data['horario'] = horario = HorarioDocenteInvitado.objects.get(pk=int(encrypt(request.GET['idh'])))
                    funcion = FuncionDocenteInvitado.objects.get(pk=int(encrypt(request.GET['idf'])))
                    data['puedeeditar'] = puedeeditar = horario.puede_editar()
                    data['diascab'] = dias = [{"numero": 1, "nombre": "Lunes", "ancho": 12},
                                              {"numero": 2, "nombre": "Martes", "ancho": 12},
                                              {"numero": 3, "nombre": "Miércoles", "ancho": 12},
                                              {"numero": 4, "nombre": "Jueves", "ancho": 12},
                                              {"numero": 5, "nombre": "Viernes", "ancho": 12},
                                              {"numero": 6, "nombre": "Sábado", "ancho": 12},
                                              {"numero": 7, "nombre": "Domingo", "ancho": 12}]
                    data['turnos'] = turnos = Turno.objects.filter(status=True, mostrar=True, sesion_id=20).order_by('comienza')
                    lista_turnos = []
                    for turno in turnos:
                        lista_dias_turno = []
                        for dia in dias:
                            if puedeeditar:
                                if horario.estado == 1:
                                    lista_dias_turno.append({"numerodia": dia["numero"], "idturno": turno.id, "idfuncion": funcion.id, "marcado": "N", "bloqueado": "N"})
                                else:
                                    if not horario.detallehorariodocenteinvitado_set.values("id").filter(status=True, turno=turno, dia=dia['numero']).exists():
                                        lista_dias_turno.append({"numerodia": dia["numero"], "idturno": turno.id, "idfuncion": funcion.id, "marcado": "N", "bloqueado": "N"})
                                    elif horario.detallehorariodocenteinvitado_set.values("id").filter(status=True, turno=turno, dia=dia['numero'], funcion=funcion).exists():
                                        lista_dias_turno.append({"numerodia": dia["numero"], "idturno": turno.id, "idfuncion": funcion.id, "marcado": "S", "bloqueado": "N"})
                                    elif horario.detallehorariodocenteinvitado_set.values("id").filter(status=False, turno=turno, dia=dia['numero'], funcion=funcion).exists():
                                        lista_dias_turno.append({"numerodia": dia["numero"], "idturno": turno.id, "idfuncion": funcion.id, "marcado": "N", "bloqueado": "N"})
                                    else:
                                        lista_dias_turno.append({"numerodia": dia["numero"], "idturno": turno.id, "idfuncion": "0", "marcado": "S", "bloqueado": "S"})
                            else:
                                if horario.detallehorariodocenteinvitado_set.values("id").filter(status=True, turno=turno, dia=dia['numero'], funcion=funcion).exists():
                                    lista_dias_turno.append({"numerodia": dia["numero"], "idturno": turno.id, "idfuncion": funcion.id, "marcado": "S", "bloqueado": "N"})
                                else:
                                    lista_dias_turno.append({"numerodia": dia["numero"], "idturno": turno.id, "idfuncion": "0", "marcado": "N", "bloqueado": "S"})

                        lista_turnos.append({"turno": turno, "dias": lista_dias_turno})

                    data['turnos'] = lista_turnos
                    template = get_template("pro_docenteinvitado/detallehorario.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'actividades':
                try:
                    data['title'] = u'Actividades y Metas del Profesor Invitado'
                    data['docente'] = docenteinvitado = DocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['criteriosdocente'] = docenteinvitado.criterios_asignados_actividad()
                    return render(request, "pro_docenteinvitado/actividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'informes':
                try:
                    idi = request.GET.get('idi', '')
                    data['title'] = u'Informes de Actividades del Profesor Invitado'
                    data['docente'] = docenteinvitado = DocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    plazos = variable_valor('PLAZOS_DIAS_INFORME_DINVITADO')
                    DIAS_MOSTRAR_PENDIENTE = int(plazos[0]) # 15 PARA PRUEBAS
                    DIAS_INICIO_PLAZO = int(plazos[1]) # 15 PARA PRUEBAS
                    DIAS_FIN_PLAZO = int(plazos[2])

                    if idi:
                        informe = InformeDocenteInvitado.objects.get(pk=int(encrypt(idi)))
                        data['informe'] = informe.archivofirmado.url if informe.archivofirmado else informe.archivo.url
                        data['tipoinforme'] = 'Informe Técnico de Actividades Firmado' if informe.archivofirmado else 'Informe Técnico de Actividades'

                    informes = docenteinvitado.informes()
                    informes_pendientes = []

                    fechainicial = docenteinvitado.inicio.replace(day=1)
                    fechaactual = datetime.now().date()

                    while fechainicial <= docenteinvitado.fin:
                        last_day_of_month = date(fechainicial.year, fechainicial.month, 1) + timedelta(days=32)
                        fechafinal = last_day_of_month - timedelta(days=last_day_of_month.day)

                        plazodesde = fechainicial + timedelta(days=DIAS_INICIO_PLAZO)
                        plazohasta = fechafinal + timedelta(days=DIAS_FIN_PLAZO)

                        # Esta condición se debe borrar para el próximo año
                        if fechainicial >= datetime.strptime('2024-07-01', '%Y-%m-%d').date():
                            # Verificar que no exista el informe del mes
                            if not informes.filter(inicio=fechainicial).exists():
                                # Si faltan 10 días con respecto al próximo mes entonces se muestra
                                if (fechaactual - fechainicial).days >= DIAS_MOSTRAR_PENDIENTE:
                                    puedeagregar = plazodesde <= fechaactual <= plazohasta
                                    observacion = ''
                                    if puedeagregar is False:
                                        if fechaactual > plazohasta:
                                            observacion = f'Usted debió haber registrado su informe del <b>{plazodesde.strftime("%d-%m-%Y")}</b> al <b>{plazohasta.strftime("%d-%m-%Y")}</b>'
                                            color = 'danger'
                                        else:
                                            observacion = f'Usted podrá registrar su informe del <b>{plazodesde.strftime("%d-%m-%Y")}</b> al <b>{plazohasta.strftime("%d-%m-%Y")}</b>'
                                            color = 'secondary'
                                    else:
                                        observacion = f'Usted deberá registrar y enviar su informe hasta el <b>{plazohasta.strftime("%d-%m-%Y")}</b>'
                                        color = 'info'

                                    informes_pendientes.append({"inicio": fechainicial, "fin": fechafinal, "puedeagregar": puedeagregar, "observacion": observacion, "color": color, "fi": fechainicial.strftime("%Y%m%d"), "ff": fechafinal.strftime("%Y%m%d")})
                                    break

                                # if (fechaactual - fechainicial).days <= 16:# 10
                                #     # Verificar que no exista el informe del mes
                                #     if not informes.filter(inicio=fechainicial).exists():
                                #         plazodesde = fechainicial + timedelta(days=DIAS_INICIO_PLAZO)
                                #         plazohasta = fechafinal + timedelta(days=DIAS_FIN_PLAZO)
                                #
                                #         # Si faltan 10 días con respecto al próximo mes entonces se muestra
                                #         if (plazodesde - fechaactual).days <= DIAS_MOSTRAR_PENDIENTE:
                                #             puedeagregar = plazodesde <= fechaactual <= plazohasta
                                #             observacion = ''
                                #             if puedeagregar is False:
                                #                 if fechaactual > plazohasta:
                                #                     observacion = f'Usted debió haber registrado su informe del <b>{plazodesde.strftime("%d-%m-%Y")}</b> al <b>{plazohasta.strftime("%d-%m-%Y")}</b>'
                                #                     color = 'danger'
                                #                 else:
                                #                     observacion = f'Usted podrá registrar su informe del <b>{plazodesde.strftime("%d-%m-%Y")}</b> al <b>{plazohasta.strftime("%d-%m-%Y")}</b>'
                                #                     color = 'secondary'
                                #             else:
                                #                 observacion = f'Usted deberá registrar su informe hasta el <b>{plazohasta.strftime("%d-%m-%Y")}</b>'
                                #                 color = 'info'
                                #
                                #             informes_pendientes.append({"inicio": fechainicial, "fin": fechafinal, "puedeagregar": puedeagregar, "observacion": observacion, "color": color, "fi": fechainicial.strftime("%Y%m%d"), "ff": fechafinal.strftime("%Y%m%d")})
                                #             break

                        fechainicial = fechafinal + timedelta(days=1)

                    data['informes'] = informes
                    data['informespendientes'] = informes_pendientes
                    return render(request, "pro_docenteinvitado/informe.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinforme':
                try:
                    data['title'] = u'Agregar Informe de Actividades'
                    data['docente'] = docente = DocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    fi = str(int(encrypt(request.GET['fi'])))
                    fechainicial = datetime.strptime(f'{fi[0:4]}-{fi[4:6]}-{fi[6:8]}', '%Y-%m-%d').date()

                    data['fechainicial'] = fechainicial
                    data['decano'] = decano_investigacion()
                    data['fecha'] = datetime.now().date()
                    data['actividades'] = docente.actividades()
                    data['estados'] = ESTADO_CUMPLIMIENTO_ACTIVIDAD
                    data['finicio'] = request.GET['fi']
                    data['ffin'] = request.GET['ff']

                    return render(request, "pro_docenteinvitado/addinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'editinforme':
                try:
                    data['title'] = u'Editar Informe de Actividades'
                    data['informe'] = informe = InformeDocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['totalinformes'] = informe.docente.informes().count()
                    data['actividades'] = informe.actividades()
                    data['conclusiones'] = informe.conclusiones()
                    data['recomendaciones'] = informe.recomendaciones()
                    data['estados'] = ESTADO_CUMPLIMIENTO_ACTIVIDAD
                    data['fecha'] = datetime.now().date()
                    return render(request, "pro_docenteinvitado/editinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'anexosinforme':
                try:
                    data['title'] = u'Anexos del Informe de Actividades'
                    data['informe'] = informe = InformeDocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['docente'] = informe.docente
                    data['actividadesinforme'] = informe.actividades()
                    data['puedeeditar'] = informe.estado in [1, 2, 5]
                    return render(request, "pro_docenteinvitado/anexoinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'addanexoinforme':
                try:
                    data['title'] = u'Agregar Anexo al Informe'
                    data['actividadinforme'] = ActividadInformeDocenteInvitado.objects.get(pk=int(encrypt(request.GET['idacti'])))
                    data['numacti'] = request.GET['numacti']
                    data['tipos'] = TIPO_ANEXO
                    data['tipoarchivoanexos'] = ", ".join(variable_valor("TIPOS_ANEXOS_INFORME_DINVITADO"))
                    data['tamanio'] = variable_valor("TAMANIO_ANEXOS_INFORME_DINVITADO")
                    template = get_template("pro_docenteinvitado/modal/addanexoinforme.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editanexoinforme':
                try:
                    data['title'] = u'Editar Anexo del Informe'
                    data['anexo'] = AnexoInformeDocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['numacti'] = request.GET['numacti']
                    data['tipos'] = TIPO_ANEXO
                    data['tipoarchivoanexos'] = ", ".join(variable_valor("TIPOS_ANEXOS_INFORME_DINVITADO"))
                    data['tamanio'] = variable_valor("TAMANIO_ANEXOS_INFORME_DINVITADO")
                    template = get_template("pro_docenteinvitado/modal/editanexoinforme.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'firmarinforme':
                try:
                    data['title'] = u'Firmar Informe de Actividades'

                    informe = InformeDocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))

                    data['solicitud'] = informe
                    data['iddoc'] = informe.id  # ID del documento a firmar
                    data['idper'] = informe.docente.profesor.persona.id  # ID de la persona que firma
                    data['tipofirma'] = 'SOL'

                    data['mensaje'] = "Firma del Informe de Actividades N° <b>{}</b> del docente <b>{}</b>".format(informe.numero, informe.docente.profesor.persona.nombre_completo_inverso())
                    data['accionfirma'] = action

                    template = get_template("pro_becadocente/firmardocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            try:
                search, filtro, url_vars = request.GET.get('s', ''), Q(status=True, profesor__persona=persona, habilitado=True), ''

                docentes = DocenteInvitado.objects.filter(filtro).order_by('-inicio')

                paging = MiPaginador(docentes, 25)
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
                data['docentes'] = page.object_list
                data['title'] = u'Profesores Invitados'

                return render(request, "pro_docenteinvitado/view.html", data)
            except Exception as ex:
                pass

