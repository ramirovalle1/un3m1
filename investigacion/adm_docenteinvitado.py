# -*- coding: UTF-8 -*-
import io
import json
import os
import calendar
import shutil
import zipfile
from math import ceil
from calendar import monthrange
import PyPDF2
from datetime import time, datetime, timedelta, date
from decimal import Decimal

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

from core.firmar_documentos_ec import JavaFirmaEc
from decorators import secure_module
from investigacion.forms import HorarioServicioForm
from investigacion.funciones import FORMATOS_CELDAS_EXCEL, notificar_docente_invitado, analista_uath_valida_asistencia, decano_investigacion, analista_verifica_informe_docente_invitado, director_escuela_investigacion, guardar_recorrido_informe_docente_invitado, secuencia_reporte_validacion_asistencia, secuencia_solicitud_validacion_asistencia, experto_uath_revisa_asistencia, director_uath, getmonthname, vicerrector_investigacion_posgrado, \
    existen_informes_conformidad_pendiente_firmar
from investigacion.models import DocenteInvitado, FuncionDocenteInvitado, CriterioDocenteInvitado, HorarioDocenteInvitado, ESTADO_HORARIO_DOCENTE, ActividadCriterioDocenteInvitado, InformeDocenteInvitado, ActividadInformeDocenteInvitado, AnexoInformeDocenteInvitado, AsistenciaDocenteInvitado, VALOR_AVANCE_ACTIVIDAD, DetalleAsistenciaDocenteInvitado, ConclusionRecomendacionInformeDocenteInvitado
from sagest.commonviews import obtener_estado_solicitud, obtener_estados_solicitud
from settings import SITE_STORAGE, MEDIA_ROOT
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, variable_valor, \
    convertir_fecha, remover_caracteres_tildes_unicode, cuenta_email_disponible, generar_nombre, email_valido, \
    validar_archivo, null_to_decimal, cuenta_email_disponible_para_envio, fechaletra_corta, fecha_letra_rango, dia_semana_enletras_fecha, elimina_tildes, remover_caracteres_especiales_unicode
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
    es_administrativo = perfilprincipal.es_administrativo()

    if not es_administrativo:
        return HttpResponseRedirect("/?info=El Módulo está disponible para administrativos.")

    es_director = director_escuela_investigacion() == persona
    es_decano = decano_investigacion() == persona
    es_analista = analista_verifica_informe_docente_invitado() == persona
    es_analista_uath = analista_uath_valida_asistencia() == persona
    es_experto_uath = experto_uath_revisa_asistencia() == persona
    es_director_uath = director_uath() == persona
    es_uath = es_analista_uath or es_experto_uath or es_director_uath
    es_tics = persona.usuario.is_staff or persona.usuario.is_superuser

    if not es_director and not es_decano and not es_analista and not es_uath and not es_tics:
        return HttpResponseRedirect("/?info=Usted no tiene permitido el acceso al módulo.")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'adddocenteinvitado':
            try:
                profesor_id = request.POST['profesor_select2']
                profesor = Profesor.objects.get(pk=profesor_id)
                modalidad_id = request.POST['modalidad']
                inicio = datetime.strptime(request.POST['inicio'], '%Y-%m-%d').date()
                fin = datetime.strptime(request.POST['fin'], '%Y-%m-%d').date()
                numerocontrato = request.POST['numerocontrato'].strip().upper()
                remuneracion = request.POST['remuneracion'].strip()
                observacion = ''
                archivocontrato = request.FILES['archivocontrato']

                # Validaciones
                if DocenteInvitado.objects.values("id").filter(status=True, profesor=profesor, vigente=True).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El profesor invitado ya tiene un registro vigente", "showSwal": "True", "swalType": "warning"})

                descripcionarchivo = 'Archivo del contrato'
                resp = validar_archivo(descripcionarchivo, archivocontrato, ['pdf'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if fin <= inicio:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin debe ser mayor a la fecha de inicio", "showSwal": "True", "swalType": "warning"})

                newfile = request.FILES['archivocontrato']
                newfile._name = generar_nombre("contrato", newfile._name)

                # Guardar el registro
                docenteinvitado = DocenteInvitado(
                    profesor=profesor,
                    dedicacion=profesor.dedicacion,
                    modalidad_id=modalidad_id,
                    inicio=inicio,
                    fin=fin,
                    numerocontrato=numerocontrato,
                    archivocontrato=newfile,
                    remuneracion=remuneracion,
                    observacion=observacion,
                    vigente=True
                )
                docenteinvitado.save(request)

                log(u'%s agregó profesor invitado para investigación: %s' % (persona, docenteinvitado), request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editdocenteinvitado':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                profesor_id = request.POST['profesore_select2']
                profesor = Profesor.objects.get(pk=profesor_id)
                modalidad_id = request.POST['modalidade']
                inicio = datetime.strptime(request.POST['inicioe'], '%Y-%m-%d').date()
                fin = datetime.strptime(request.POST['fine'], '%Y-%m-%d').date()
                numerocontrato = request.POST['numerocontratoe'].strip().upper()
                remuneracion = request.POST['remuneracione'].strip()
                observacion = ''
                archivocontrato = None

                if 'archivocontratoe' in request.FILES:
                    archivocontrato = request.FILES['archivocontratoe']

                # Validaciones
                if DocenteInvitado.objects.values("id").filter(status=True, profesor=profesor, vigente=True).exclude(pk=int(encrypt(request.POST['id']))).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El profesor invitado ya tiene un registro vigente", "showSwal": "True", "swalType": "warning"})

                if archivocontrato:
                    descripcionarchivo = 'Archivo del contrato'
                    resp = validar_archivo(descripcionarchivo, archivocontrato, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if fin <= inicio:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin debe ser mayor a la fecha de inicio", "showSwal": "True", "swalType": "warning"})

                # Consultar el docente invitado
                docenteinvitado = DocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))

                # Actualizar el registro
                docenteinvitado.profesor = profesor
                docenteinvitado.dedicacion = profesor.dedicacion
                docenteinvitado.modalidad_id = modalidad_id
                docenteinvitado.inicio = inicio
                docenteinvitado.fin = fin
                docenteinvitado.numerocontrato = numerocontrato

                if archivocontrato:
                    newfile = request.FILES['archivocontratoe']
                    newfile._name = generar_nombre("contrato", newfile._name)
                    docenteinvitado.archivocontrato = newfile

                docenteinvitado.remuneracion = remuneracion
                docenteinvitado.observacion = observacion
                docenteinvitado.save(request)

                log(u'%s editó profesor para investigación: %s' % (persona, docenteinvitado), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'criteriosdocenteinvitado':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar el docente invitado
                docenteinvitado = DocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))
                funciones = docenteinvitado.funciones()
                nuevoreg = False if funciones else True

                # Obtener los valores de los detalles del formulario
                criterios = json.loads(request.POST['lista_items1'])   # Lista de criterios

                # Guardar y/o actualizar los criterios del docente
                for criterio in criterios:
                    if criterio["marcado"] == 'S':
                        if not docenteinvitado.funciones().filter(criterio_id=criterio["idcriterio"]).exists():
                            funciondocente = FuncionDocenteInvitado(
                                docente=docenteinvitado,
                                criterio_id=criterio["idcriterio"]
                            )
                        else:
                            funciondocente = docenteinvitado.funciones().filter(criterio_id=criterio["idcriterio"])[0]
                            funciondocente.status = True

                        funciondocente.save(request)
                    else:
                        docenteinvitado.funciones().filter(criterio_id=criterio["idcriterio"]).update(status=False)

                if nuevoreg:
                    log(u'%s agregó funciones a profesor invitado para investigación: %s' % (persona, docenteinvitado), request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    log(u'%s editó funciones del profesor invitado para investigación: %s' % (persona, docenteinvitado), request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addactividadcriterio':
            try:
                if 'idcriteriodocente' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                criteriodocente = FuncionDocenteInvitado.objects.get(pk=int(encrypt(request.POST['idcriteriodocente'])))
                docenteinvitado = criteriodocente.docente

                # Guardo la actividad del criterio
                actividadcriterio = ActividadCriterioDocenteInvitado(
                    criteriodocente=criteriodocente,
                    descripcion=request.POST['descripcion'].strip(),
                    medible='medible' in request.POST,
                    planificado=request.POST['planificado'] if 'medible' in request.POST else None,
                    ejecutado=0 if 'medible' in request.POST else None,
                    estado=1 if 'medible' in request.POST else None
                )
                actividadcriterio.save(request)

                # Cargo la sección del detalle de actividades para el criterio
                data['criteriodocente'] = criteriodocente
                data['numcrit'] = request.POST['numcrit']
                data['detalles'] = docenteinvitado.actividades_criterio(criteriodocente)
                totalactividad = docenteinvitado.total_actividad_criterio(criteriodocente)
                template = get_template("adm_docenteinvitado/secciondetallecriterio.html")
                json_content = template.render(data)

                log(u'% agregó actividad al criterio del docente: %s - %s' % (persona, docenteinvitado, actividadcriterio), request, "add")
                return JsonResponse({"result": "ok", "idcrit": criteriodocente.id, "totalactividad": totalactividad, 'data': json_content, "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editactividadcriterio':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                actividadcriterio = ActividadCriterioDocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))
                criteriodocente = actividadcriterio.criteriodocente
                docenteinvitado = actividadcriterio.criteriodocente.docente

                # Actualizo la actividad
                actividadcriterio.descripcion = request.POST['descripcione'].strip()
                actividadcriterio.medible = 'mediblee' in request.POST
                actividadcriterio.planificado = request.POST['planificadoe'] if 'mediblee' in request.POST else None
                actividadcriterio.ejecutado = 0 if 'mediblee' in request.POST else None
                actividadcriterio.estado = 1 if 'mediblee' in request.POST else None
                actividadcriterio.save(request)

                # Cargo la sección del detalle de actividades para el criterio
                data['criteriodocente'] = criteriodocente
                data['numcrit'] = request.POST['numcrit']
                data['detalles'] = docenteinvitado.actividades_criterio(criteriodocente)
                totalactividad = docenteinvitado.total_actividad_criterio(criteriodocente)
                template = get_template("adm_docenteinvitado/secciondetallecriterio.html")
                json_content = template.render(data)

                log(u'%s editó actividad del criterio del docente: %s - %s' % (persona, docenteinvitado, actividadcriterio), request, "edit")
                return JsonResponse({"result": "ok", "idcrit": criteriodocente.id, "totalactividad": totalactividad, 'data': json_content, "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'delactividadcriterio':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                actividadcriterio = ActividadCriterioDocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))
                criteriodocente = actividadcriterio.criteriodocente
                docenteinvitado = actividadcriterio.criteriodocente.docente

                # Elimino la actividad
                actividadcriterio.status = False
                actividadcriterio.save(request)

                # Consulto los totales
                totalactividad = docenteinvitado.total_actividad_criterio(criteriodocente)

                log(u'%s eliminó actividad actividad del criterio del docente: %s' % (persona, actividadcriterio), request, "del")
                return JsonResponse({"result": "ok", "totalactividad": totalactividad, "titulo": "Proceso exitoso!!!", "mensaje": u"Registro eliminado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al eliminar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'habilitardocente':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar el docente invitado
                docenteinvitado = DocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))
                habilitado = request.POST['valor'] == 'S'

                # Si lo deshabilita debo verificar que no exista horario registrado
                if habilitado is False:
                    if docenteinvitado.tiene_horarios_registrados():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede deshabilitar el registro porque ya existen horarios registrados", "showSwal": "True", "swalType": "warning"})

                # Actualizar el registro
                docenteinvitado.habilitado = habilitado
                docenteinvitado.save(request)

                # Si está habilitado creo o actualizo el horario
                if habilitado:
                    if not docenteinvitado.horariodocenteinvitado_set.filter(status=True).exists():
                        fechainicial = docenteinvitado.inicio.replace(day=1)
                        fechaactual = datetime.now().date()

                        while fechainicial <= docenteinvitado.fin:
                            last_day_of_month = date(fechainicial.year, fechainicial.month, 1) + timedelta(days=32)
                            fechafinal = last_day_of_month - timedelta(days=last_day_of_month.day)

                            # Si los días transcurridos de cada mes con respecto a la fecha actual es <= 10 creo el horario
                            if (fechaactual - fechainicial).days <= 15:
                                # Guardar horario
                                horario = HorarioDocenteInvitado(
                                    docente=docenteinvitado,
                                    inicio=fechainicial,
                                    fin=fechafinal,
                                    observacion='',
                                    horaplanificada=0,
                                    totalhora=docenteinvitado.dedicacion.horas,
                                    habilitado=False,
                                    estado=1
                                )
                                horario.save(request)

                            fechainicial = fechafinal + timedelta(days=1)
                else:
                    pass

                log(u'{} {} a profesor invitado para investigación: {}'.format(persona, "habilitó" if habilitado else "deshabilitó", docenteinvitado), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'habilitarhorario':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar el horario del docente invitado
                horario = HorarioDocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))
                habilitado = request.POST['valor'] == 'S'

                # Si lo deshabilita debo verificar que no esté registrado
                if habilitado is False:
                    if horario.estado != 1:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede deshabilitar el registro porque ya existen un horario registrado", "showSwal": "True", "swalType": "warning"})

                # Actualizar el registro
                horario.habilitado = habilitado
                horario.save(request)

                log(u'{} {} horario a profesor invitado para investigación: {}'.format(persona, "habilitó" if habilitado else "deshabilitó", horario), request, "edit")
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
                horario = HorarioDocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))

                # Actualizar el registro
                horario.observacion = request.POST['observacion'].strip() if 'observacion' in request.POST else ''
                horario.estado = int(request.POST['estado'])
                horario.save(request)

                # Notificar por e-mail
                notificar_docente_invitado(horario, "APRHOR" if horario.estado == 4 else "NOVHOR")

                log(u'{} {} horario de actividades de profesor invitado: {}'.format(persona, 'aprobó' if horario.estado == 4 else 'registro novedades en', horario), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editnombrefirma':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar el docente invitado
                docenteinvitado = DocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))

                if not docenteinvitado.puede_editar_nombre_firma():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el Registro", "showSwal": "True", "swalType": "warning"})

                # Actualizar el registro
                docenteinvitado.nombrefirma = request.POST['nombrefirma'].strip()
                docenteinvitado.save(request)

                log(u'%s editó nombre para firma de documentos del profesor invitado para investigación: %s' % (persona, docenteinvitado), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'finalizarcontrato':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                fechaactual = datetime.now().date()
                finreal = datetime.strptime(request.POST['finreal'], '%Y-%m-%d').date()
                observacion = request.POST['observacionfin'].strip()

                # Consultar el docente invitado
                docenteinvitado = DocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))

                if finreal <= docenteinvitado.inicio or finreal > fechaactual:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"La fecha de fin real debe ser mayor a <b>{docenteinvitado.inicio.strftime('%d-%m-%Y')}</b> y menor o igual a <b>{fechaactual.strftime('%d-%m-%Y')}</b>", "showSwal": "True", "swalType": "warning"})

                # Actualizar el registro
                docenteinvitado.finreal = finreal
                docenteinvitado.observacion = observacion
                docenteinvitado.vigente = False
                docenteinvitado.save(request)

                log(u'%s finalizó contrato de profesor invitado para investigación: %s' % (persona, docenteinvitado), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'actualizardetalleavanceinforme':
            try:
                if 'idact' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar el detalle de avance del informe
                actividadinforme = ActividadInformeDocenteInvitado.objects.get(pk=request.POST['idact'])
                actividadinforme.observacion = request.POST['observacion'].strip()
                actividadinforme.save(request)

                log(f'{persona} actualizó observaciones del detalle de actividades del informe: {actividadinforme}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'actualizardetalleanexoinforme':
            try:
                if 'idane' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar el detalle de anexo del informe
                anexoinforme = AnexoInformeDocenteInvitado.objects.get(pk=request.POST['idane'])
                anexoinforme.observacion = request.POST['observacion'].strip()
                anexoinforme.save(request)

                log(f'{persona} actualizó observaciones del detalle de anexos del informe: {anexoinforme}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'validarinforme':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                informedocente = InformeDocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico si puedo validar
                if not informedocente.puede_validar():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el Registro", "showSwal": "True", "swalType": "warning"})

                # Obtiene los valores del formulario
                estado = int(request.POST['estado'])
                observacion = request.POST['observacion'].strip()

                # Obtiene los valores de los arreglos del detalle de actividades y anexos
                idsregactividad = request.POST.getlist('idregactividad[]')
                observacionesactividad = request.POST.getlist('observacionactividad[]')
                # avancessatisf = request.POST.getlist('avancesatisf[]')

                idsreganexo = request.POST.getlist('idreganexo[]')
                observacionesanexo = request.POST.getlist('observacionanexo[]')

                # Actualizar informe
                informedocente.fechavalida = datetime.now()
                informedocente.observacion = observacion
                informedocente.estado = estado
                informedocente.save(request)

                # Guardar las observaciones para las actividades
                # for idreg, observacion, satisfactorio in zip(idsregactividad, observacionesactividad, avancessatisf):
                for idreg, observacion in zip(idsregactividad, observacionesactividad):
                    # Actualizo la actividad del informe
                    actividadinforme = ActividadInformeDocenteInvitado.objects.get(pk=idreg)
                    actividadinforme.observacion = observacion.strip()
                    # actividadinforme.avancesatisf = satisfactorio
                    actividadinforme.save(request)

                    # Actualizo la actividad del docente
                    actividaddocente = actividadinforme.actividad
                    actividaddocente.observacion = observacion.strip()
                    # actividaddocente.avancesatisf = satisfactorio
                    actividaddocente.save(request)

                # Guardar las observaciones para los anexos
                for idreg, observacion in zip(idsreganexo, observacionesanexo):
                    anexoinforme = AnexoInformeDocenteInvitado.objects.get(pk=idreg)
                    anexoinforme.observacion = observacion.strip()
                    anexoinforme.save(request)

                if estado == 4:
                    # Obtengo estado VALIDADO
                    estadoregistro = obtener_estado_solicitud(23, 5)

                    # Guardar el recorrido
                    guardar_recorrido_informe_docente_invitado(informedocente, estadoregistro, '', request)

                    # Notificar al docente
                    notificar_docente_invitado(informedocente, "VALINF")

                    log(u'%s validó informe de actividades: %s' % (persona, informedocente), request, "edit")
                else:
                    # Obtengo estado NOVEDAD
                    estadoregistro = obtener_estado_solicitud(23, 6)

                    # Guardar el recorrido
                    guardar_recorrido_informe_docente_invitado(informedocente, estadoregistro, '', request)

                    log(u'%s registró novedades en informe de actividades: %s' % (persona, informedocente), request, "edit")

                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addsolicitudasistencia':
            try:
                if 'fechaenvio' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Obtener los campos del formulario y detalle
                fechaenvio = datetime.now().date()
                concepto = request.POST['concepto'].strip()
                totaldocente = request.POST['totaldocente']
                idsinforme = request.POST.getlist('idinforme[]')

                # Obtener secuencia de la solicitud
                anio = fechaenvio.year
                secuencia = secuencia_solicitud_validacion_asistencia(anio)
                numero = f'SGA-{str(secuencia).zfill(3)}-PI-EFI-FI-SOL-VA-{anio}'

                decano = decano_investigacion()
                directoruath = director_uath()

                # Guardar solicitud
                solicitud = AsistenciaDocenteInvitado(
                    secuencia=secuencia,
                    numero=numero,
                    solicita=decano,
                    cargosolicita=decano.mi_cargo_actual().denominacionpuesto,
                    concepto=concepto,
                    totaldocente=totaldocente,
                    aprueba=directoruath,
                    cargoaprueba=directoruath.mi_cargo_actual().denominacionpuesto,
                    estado=4
                )
                solicitud.save(request)

                informe = None
                # Guardar detalle de la solicitud
                for idinforme in idsinforme:
                    # Consultar informe
                    informe = InformeDocenteInvitado.objects.get(pk=idinforme)

                    # Guardo detalle de solicitud
                    detallesolicitud = DetalleAsistenciaDocenteInvitado(
                        solicitud=solicitud,
                        informe=informe,
                        estado=1
                    )
                    detallesolicitud.save(request)

                solicitud.fechavalida = informe.inicio
                solicitud.save(request)

                log(f'{persona} agregó solicitud de validación de asistencia de docentes invitados: {solicitud}', request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'solicitudvalidacionpdf':
            try:
                data = {}

                asistenciadocente = AsistenciaDocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))

                if not asistenciadocente.solimpresa:
                    # Generar el número del reporte
                    fecha = asistenciadocente.fecha_creacion
                    anio = fecha.year
                    fechaletras = f'{str(fecha.day).zfill(2)} de {getmonthname(fecha)} de {anio}'

                    data['asistencia'] = asistenciadocente
                    data['fechaletras'] = fechaletras

                    # Creacion de los archivos por separado
                    directorio = SITE_STORAGE + '/media/proyectoinvestigacion/informes'
                    try:
                        os.stat(directorio)
                    except:
                        os.mkdir(directorio)

                    # Archivo de la parte 1 del informe
                    nombrearchivo = 'reporteparte1_' + str(asistenciadocente.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                    valida = convert_html_to_pdf(
                        'adm_docenteinvitado/solicitudasistenciapdf.html',
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
                    nombrearchivoresultado = generar_nombre('solicitudasistencia', 'solicitudasistencia.pdf')
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
                    asistenciadocente.solimpresa = True
                    asistenciadocente.archivosol = archivocopiado
                    asistenciadocente.save(request)

                    # Borro el informe creado de manera general, no la del registro
                    os.remove(archivo)

                    # Notificar a Decano para que firme la solicitud
                    notificar_docente_invitado(asistenciadocente, "FIRSOLASIS")

                    log(f'{persona} generó solicitud de validación de asistencias {asistenciadocente}', request, "edit")

                return JsonResponse({"result": "ok", "idsol": encrypt(asistenciadocente.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar documento del reporte de validación de asistencias. [%s]" % msg})

        elif action == 'firmarsolicitudasistencia':
            try:
                if 'iddoc' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                tipofirma = request.POST['tipofirma']
                archivofirma = request.FILES['archivofirma']
                clavefirma = request.POST['cfirma']
                descripcionarchivo = 'Archivo de la firma electrónica'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivofirma, ['P12', 'PFX'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto asistencia
                asistenciadocente = AsistenciaDocenteInvitado.objects.get(pk=int(encrypt(request.POST['iddoc'])))

                # Obtengo el archivo del reporte
                archivoreporte = asistenciadocente.archivosolfirmada if asistenciadocente.archivosolfirmada else asistenciadocente.archivosol
                rutapdfarchivo = SITE_STORAGE + archivoreporte.url

                textoabuscar = asistenciadocente.nombre_firma_solicitante()
                textofirma = textoabuscar  # 'Validado por:'
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
                    y = 5000 - int(valor[3]) - 4087
                else:
                    y = 0

                # x = 127 # if tipofirma == 'SOL' else 355
                x = 87  # izq
                # x = 230  # cent
                # x = 350  # der

                # Si no existe el nombre de la persona en el documento
                if y == 0:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"No se encuentra el nombre del firmante en el documento", "showSwal": "True", "swalType": "warning"})

                # Obtener extensión y leer archivo de la firma
                extfirma = os.path.splitext(archivofirma.name)[1][1:]
                bytesfirma = archivofirma.read()

                # Firma del documento
                datau = JavaFirmaEc(
                    archivo_a_firmar=archivoreporte,
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

                nombre = "solicitudasistenciafirmada"

                nombrearchivofirmado = generar_nombre(nombre, nombre + '.pdf')
                objarchivo = DjangoFile(generar_archivo_firmado, nombrearchivofirmado)

                asistenciadocente.fechaenvio = datetime.now()
                asistenciadocente.archivosolfirmada = objarchivo
                asistenciadocente.estado = 1
                asistenciadocente.save(request)

                # Notificar a Utah para que validen la solicitud
                notificar_docente_invitado(asistenciadocente, "SOLASIS")

                log(f'{persona} firmó solicitud de validación de asistencias: {asistenciadocente}', request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Documento firmado con éxito", "showSwal": True, "idsol": encrypt(asistenciadocente.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % msg, "showSwal": "True", "swalType": "error"})


        # elif action == 'enviarwhatsapp':
        #     try:
        #         import pywhatkit
        #         phone_numer = '+593996734649'
        #         group_id = ''
        #         message = 'Hola que tal :) ...'
        #         time_hour = 11
        #         time_minute = 59
        #
        #         waiting_time_to_send = 15
        #         close_tab = True
        #         waiting_time_to_close = 2
        #
        #         mode = "contact"
        #
        #         print("Enviando jajja....")
        #         # pywhatkit.sendwhatmsg(phone_numer, message, time_hour, time_minute, waiting_time_to_send, close_tab, waiting_time_to_close)
        #         pywhatkit.sendwhatmsg_instantly(phone_numer, message, waiting_time_to_send, close_tab, waiting_time_to_close)
        #
        #         return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
        #     except Exception as ex:
        #         msg = ex.__str__()
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})


        elif action == 'firmarinforme':
            try:
                if 'iddoc' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                tipofirma = request.POST['tipofirma']
                archivofirma = request.FILES['archivofirma']
                clavefirma = request.POST['cfirma']
                descripcionarchivo = 'Archivo de la firma electrónica'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivofirma, ['P12', 'PFX'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto el informe
                informe = InformeDocenteInvitado.objects.get(pk=int(encrypt(request.POST['iddoc'])))

                # Verifico si puede firmar el informe
                if tipofirma == 'VAL':
                    if not informe.puede_firmar_validador():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede editar el Registro porque ya ha sido revisado por otra instancia", "showSwal": "True", "swalType": "warning"})
                else:
                    if not informe.puede_firmar_aprobador():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede editar el Registro porque ya ha sido revisado por otra instancia", "showSwal": "True", "swalType": "warning"})

                # Obtengo el archivo del informe firmado previamente
                archivoinforme = informe.archivofirmado
                rutapdfarchivo = SITE_STORAGE + archivoinforme.url

                if tipofirma == 'VAL':
                    textoabuscar = informe.nombre_firma_valida()
                    textofirma = 'Validado por:'
                    ocurrencia = 1
                else:
                    textoabuscar = informe.nombre_firma_aprueba()
                    textofirma = 'Aprobado por:'
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

                if tipofirma == 'VAL':
                    informe.firmavalida = True
                else:
                    informe.fechaaprueba = datetime.now()
                    informe.firmaaprueba = True
                    informe.estado = 6

                informe.save(request)

                # Crear registro para que UATH valide la asistencia
                if informe.estado == 6:
                    if not informe.asistencia():
                        asistenciadocente = AsistenciaDocenteInvitado(
                            informe=informe,
                            fechaenvio=datetime.now(),
                            estado=1
                        )
                        asistenciadocente.save(request)

                    # Obtengo estado APROBADO
                    estadoregistro = obtener_estado_solicitud(23, 7)

                    # Guardar el recorrido
                    guardar_recorrido_informe_docente_invitado(informe, estadoregistro, '', request)

                    # Notificar al docente
                    notificar_docente_invitado(informe, "APRINF")

                    # Notificar a UATH que valide asistencia
                    notificar_docente_invitado(informe, "REVASIS")

                log(u'%s firmó informe técnico de actividades: %s' % (persona, informe), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Documento firmado con éxito", "showSwal": True, "idi": encrypt(informe.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'validarasistencia':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar detalle de solicitud de asistencia
                tipo = request.POST['tipo']
                asistencia = DetalleAsistenciaDocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))
                solicitud = asistencia.solicitud

                # Actualizar la solicitud a EN REVISIÓN
                if solicitud.estado == 1:
                    solicitud.estado = 2
                    solicitud.save(request)

                # Actualizar el registro del detalle
                if tipo == 'V':
                    asistencia.fechavalida = datetime.now()
                    asistencia.valida = persona
                    asistencia.cargovalida = persona.mi_cargo_actual().denominacionpuesto
                    asistencia.observacion = request.POST['observacionvalasis'].strip()
                elif tipo == 'R':
                    asistencia.fecharevisa = datetime.now()
                    asistencia.revisa = persona
                    asistencia.cargorevisa = persona.mi_cargo_actual().denominacionpuesto
                else:
                    asistencia.fechaaprueba = datetime.now()
                    asistencia.aprueba = persona
                    asistencia.cargoaprueba = persona.mi_cargo_actual().denominacionpuesto

                asistencia.estado = int(request.POST['estadovalasis'])
                asistencia.save(request)

                # Obtengo estado para el registro
                if tipo == 'V':
                    estadoregistro = obtener_estado_solicitud(23, 8 if asistencia.estado == 2 else 9)
                else:
                    estadoregistro = obtener_estado_solicitud(23, 10 if tipo == 'R' else 11)

                # Guardar el recorrido
                guardar_recorrido_informe_docente_invitado(asistencia.informe, estadoregistro, '', request)

                # Notificar por e-mail
                if tipo == 'V':
                    notificar_docente_invitado(asistencia, "VALASIS" if asistencia.estado == 2 else "NOVASIS")
                    log(u'{} {} asistencia del profesor invitado: {}'.format(persona, 'validó' if asistencia.estado == 4 else 'registro novedades en', asistencia), request, "edit")
                else:
                    if tipo == 'R':
                        notificar_docente_invitado(asistencia, "REVASIS")
                    log(u'{} {} asistencia del profesor invitado: {}'.format(persona, 'revisó' if tipo == 'R' else 'aprobó', asistencia), request, "edit")

                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'reporteasistenciapdf':
            try:
                data = {}

                asistenciadocente = AsistenciaDocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))

                if not asistenciadocente.repimpreso:
                    # Generar el número del reporte
                    fecha = datetime.now().date()
                    anio = fecha.year
                    secuencia = secuencia_reporte_validacion_asistencia(anio)
                    numero = f'UNEMI-DTH-VA-PI-{anio}-{str(secuencia).zfill(3)}'
                    fechaletras = f'{str(fecha.day).zfill(2)} de {getmonthname(fecha)} de {anio}'
                    directoruath = director_uath()

                    # Actualizar el registro
                    asistenciadocente.secuenciarep = secuencia
                    asistenciadocente.numerorep = numero
                    asistenciadocente.fecharep = datetime.now()
                    # asistenciadocente.aprueba = directoruath
                    # asistenciadocente.cargoaprueba = directoruath.mi_cargo_actual().denominacionpuesto
                    asistenciadocente.save(request)

                    data['asistencia'] = asistenciadocente
                    data['fechaletras'] = fechaletras

                    # Creacion de los archivos por separado
                    directorio = SITE_STORAGE + '/media/proyectoinvestigacion/informes'
                    try:
                        os.stat(directorio)
                    except:
                        os.mkdir(directorio)

                    # Archivo de la parte 1 del informe
                    nombrearchivo = 'reporteparte1_' + str(asistenciadocente.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                    valida = convert_html_to_pdf(
                        'adm_docenteinvitado/reporteasistenciapdf.html',
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
                    nombrearchivoresultado = generar_nombre('reporteasistencia', 'reporteasistencia.pdf')
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
                    asistenciadocente.repimpreso = True
                    asistenciadocente.archivorep = archivocopiado
                    asistenciadocente.save(request)

                    # Borro el informe creado de manera general, no la del registro
                    os.remove(archivo)

                    log(u'%s generó reporte de validación de asistencias: %s' % (persona, asistenciadocente), request, "edit")

                return JsonResponse({"result": "ok"})
                # return JsonResponse({"result": "ok", "documento": informedocente.archivo.url})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar documento del reporte de validación de asistencias. [%s]" % msg})

        elif action == 'firmarreporteasistencia':
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

                # Consulto asistencia
                asistenciadocente = AsistenciaDocenteInvitado.objects.get(pk=int(encrypt(request.POST['iddoc'])))

                # Verifico si puede firmar el reporte
                # if not asistenciadocente.puede_firmar_aprobador():
                #     return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede editar el Registro porque ya ha sido revisado por otra instancia", "showSwal": "True", "swalType": "warning"})

                # Obtengo el archivo del reporte
                archivoreporte = asistenciadocente.archivorepfirmado if asistenciadocente.archivorepfirmado else asistenciadocente.archivorep
                rutapdfarchivo = SITE_STORAGE + archivoreporte.url

                textoabuscar = asistenciadocente.nombre_firma_aprueba()
                textofirma = textoabuscar #'Aprobado por:'
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
                    y = 5000 - int(valor[3]) - 4087
                else:
                    y = 0

                x = 87
                # x = 87  # izq
                # x = 230  # cent
                # x = 350  # der

                # Si no existe el nombre de la persona en el documento
                if y == 0:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"No se encuentra el nombre del firmante en el documento", "showSwal": "True", "swalType": "warning"})

                # Obtener extensión y leer archivo de la firma
                extfirma = os.path.splitext(archivofirma.name)[1][1:]
                bytesfirma = archivofirma.read()

                # Firma del documento
                datau = JavaFirmaEc(
                    archivo_a_firmar=archivoreporte,
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

                nombre = "reporteasistencia"

                nombrearchivofirmado = generar_nombre(nombre, nombre + '.pdf')
                objarchivo = DjangoFile(generar_archivo_firmado, nombrearchivofirmado)

                asistenciadocente.archivorepfirmado = objarchivo
                asistenciadocente.fechaaprueba = datetime.now()
                asistenciadocente.firmaaprueba = True
                asistenciadocente.estado = 3
                asistenciadocente.save(request)

                notificar_docente_invitado(asistenciadocente, "APRASIS")

                log(u'%s firmó reporte de validación de asistencias: %s' % (persona, asistenciadocente), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Documento firmado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'cargarseccioninformeconformidad':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                asistencia = AsistenciaDocenteInvitado.objects.get(pk=request.POST['id'])
                objetivo = f'Informe de conformidad de los resultados y/o productos obtenidos de profesores invitados correspondiente al mes de {getmonthname(asistencia.fechavalida).title()} {asistencia.fechavalida.year}'
                conclusion = "Que de acuerdo a los informes de actividades mensuales presentados por los profesores invitados " \
                             "se evidencia avances en los productos y servicios que se establecen en el presente contrato por prestación de servicios profesionales, " \
                             f"mismos que permiten dar continuidad al proceso de pago correspondiente al mes de {getmonthname(asistencia.fechavalida).title()} {asistencia.fechavalida.year}."

                # Cargo la sección del detalle de profesores del informe
                data['reporteasistencia'] = asistencia
                template = get_template("adm_docenteinvitado/secciondetalleinforme.html")
                json_content = template.render(data)

                return JsonResponse({"result": "ok", "objetivo": objetivo, "conclusion": conclusion, 'data': json_content})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al obtener los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addinformeconformidad':
            try:
                if 'numero' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                numero = request.POST['numero'].strip()
                reporteasistencia = request.POST['reporteasistencia'] if 'reporteasistencia' in request.POST else request.POST['reporteasistencia2']

                # Validar que no esté repetido el número del informe
                if not InformeDocenteInvitado.objects.filter(status=True, numero=numero, tipo=2).exists():
                    # Consultar la asistencia
                    asistencia = AsistenciaDocenteInvitado.objects.get(pk=reporteasistencia)
                    informedocente = asistencia.detalles_reporte()[0].informe
                    inicio = informedocente.inicio
                    fin = informedocente.fin
                    diaslaborados = monthrange(inicio.year, inicio.month)[1]

                    # Obtiene los valores de los arreglos del detalle de conclusiones y recomendaciones
                    descripciones_conclusiones = request.POST.getlist('descripcion_conclusion[]')
                    descripciones_recomendaciones = request.POST.getlist('descripcion_recomendacion[]')

                    elabora = analista_verifica_informe_docente_invitado()
                    directorefi = director_escuela_investigacion()
                    decano = decano_investigacion()
                    vicerrector = vicerrector_investigacion_posgrado()

                    # Guardar informe
                    informeconformidad = InformeDocenteInvitado(
                        tipo=2,
                        docente=None,
                        secuencia=0,
                        fecha=datetime.now(),
                        numero=numero,
                        inicio=inicio,
                        fin=fin,
                        dialaborado=diaslaborados,
                        remitente=decano,
                        cargoremitente=decano.mi_cargo_actual().denominacionpuesto,
                        destinatario=vicerrector,
                        cargodestinatario=vicerrector.mi_cargo_actual().denominacionpuesto,
                        objeto=f'Informe de conformidad de los resultados y/o productos obtenidos de profesores invitados correspondiente al mes de {getmonthname(inicio).capitalize()} del {inicio.year}',
                        motivaciontecnica='',
                        impreso=False,
                        elabora=elabora,
                        cargoelabora=elabora.mi_cargo_actual().denominacionpuesto,
                        valida=directorefi,
                        cargovalida=directorefi.mi_cargo_actual().denominacionpuesto,
                        aprueba=decano,
                        cargoaprueba=decano.mi_cargo_actual().denominacionpuesto,
                        solicitudasistencia=asistencia,
                        estado=1
                    )
                    informeconformidad.save(request)

                    # Guardar conclusiones
                    for descripcion in descripciones_conclusiones:
                        conclusion = ConclusionRecomendacionInformeDocenteInvitado(
                            informe=informeconformidad,
                            descripcion=descripcion.strip(),
                            tipo=1
                        )
                        conclusion.save(request)

                    # Guardar recomendaciones
                    for descripcion in descripciones_recomendaciones:
                        recomendacion = ConclusionRecomendacionInformeDocenteInvitado(
                            informe=informeconformidad,
                            descripcion=descripcion.strip(),
                            tipo=2
                        )
                        recomendacion.save(request)

                    # Actualizo la solicitud de validación de asistencia
                    asistencia.tieneinforme = True
                    asistencia.save(request)

                    # Obtengo estado EN EDICIÓN
                    estadoregistro = obtener_estado_solicitud(23, 1)

                    # Guardar el recorrido
                    guardar_recorrido_informe_docente_invitado(informeconformidad, estadoregistro, 'INFORME AGREGADO POR INVESTIGACIÓN', request)

                    log(u'%s agregó informe de conformidad de resultados: %s' % (persona, informeconformidad), request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El número de informe ya ha sido ingresado", "showSwal": "True", "swalType": "warning"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editinformeconformidad':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                numero = request.POST['numero'].strip()
                informeconformidad = InformeDocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))

                # Validar que no esté repetido el número del informe
                if InformeDocenteInvitado.objects.filter(status=True, numero=numero, tipo=2).exclude(pk=int(encrypt(request.POST['id']))).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El número de informe ya ha sido ingresado", "showSwal": "True", "swalType": "warning"})

                # Obtiene los valores de los arreglos del detalle de conclusiones y recomendaciones
                ids_conclusiones = request.POST.getlist('idregcon[]')
                descripciones_conclusiones = request.POST.getlist('descripcion_conclusion[]')
                conclelim = json.loads(request.POST['lista_items1']) if 'lista_items1' in request.POST else []  # Ids registros de conclusiones borradas

                ids_recomendaciones = request.POST.getlist('idregreco[]')
                descripciones_recomendaciones = request.POST.getlist('descripcion_recomendacion[]')
                recoelim = json.loads(request.POST['lista_items2']) if 'lista_items2' in request.POST else []  # Ids registros de recomendaciones borradas

                # Actualizar informe
                informeconformidad.numero = numero
                informeconformidad.impreso = False
                informeconformidad.archivo = None
                informeconformidad.archivofirmado = None
                informeconformidad.observacion = ''
                informeconformidad.firmaelabora = False
                informeconformidad.firmaverifica = False
                informeconformidad.firmaaprueba = False
                informeconformidad.estado = 1
                informeconformidad.save(request)

                # Guardar conclusiones
                for idreg, descripcion in zip(ids_conclusiones, descripciones_conclusiones):
                    # Si es registro nuevo
                    if int(idreg) == 0:
                        conclusion = ConclusionRecomendacionInformeDocenteInvitado(
                            informe=informeconformidad,
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
                            informe=informeconformidad,
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
                guardar_recorrido_informe_docente_invitado(informeconformidad, estadoregistro, 'INFORME EDITADO POR INVESTIGACIÓN', request)

                log(u'%s editó informe de actividades: %s' % (persona, informeconformidad), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'generarenlace':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consultar el informe
                informeconformidad = InformeDocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))
                solicitudasistencia = informeconformidad.solicitudasistencia
                fechaactual = datetime.now().date()

                directorio = os.path.join(os.path.join(SITE_STORAGE, 'media', 'zipav'))

                # response = HttpResponse(content_type='application/zip')
                # response['Content-Disposition'] = 'attachment; filename=documentacionsoporte_' + random.randint(1, 10000).__str__() + '.zip'

                mes = getmonthname(informeconformidad.inicio)
                anio = informeconformidad.inicio.year
                nombre_archivo = generar_nombre(f'doc{mes}{anio}_', f'doc{mes}{anio}_.zip')
                filename = os.path.join(directorio, nombre_archivo)
                fantasy_zip = zipfile.ZipFile(filename, 'w')

                carpetaarticulo = ""
                nombreevidencia = "reporteasistencia"
                # Agregar el reporte de validación de asistencia
                ext = solicitudasistencia.archivorepfirmado.__str__()[solicitudasistencia.archivorepfirmado.__str__().rfind("."):]
                if os.path.exists(SITE_STORAGE + solicitudasistencia.archivorepfirmado.url):
                    fantasy_zip.write(SITE_STORAGE + solicitudasistencia.archivorepfirmado.url, carpetaarticulo + "/" + nombreevidencia + ext.lower())

                # Agregar informe de actividades y contrato de cada profesor
                for detalle in solicitudasistencia.detalles():
                    informeactividad = detalle.informe
                    profesorinvitado = detalle.informe.docente
                    nombreprofesor = profesorinvitado.profesor.persona.nombre_completo_inverso().replace(' ', '_')
                    contrato = profesorinvitado.numerocontrato
                    nombreprofesor = elimina_tildes(remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(nombreprofesor)))

                    carpetaprofesor = f"PI_{contrato}_{nombreprofesor}"

                    # Agregar informe del profesor
                    nombreevidencia = "informeactividad"
                    ext = informeactividad.archivofirmado.__str__()[informeactividad.archivofirmado.__str__().rfind("."):]
                    if os.path.exists(SITE_STORAGE + informeactividad.archivofirmado.url):
                        fantasy_zip.write(SITE_STORAGE + informeactividad.archivofirmado.url, carpetaprofesor + "/" + nombreevidencia + ext.lower())

                    # Agregar contrato del profesor
                    nombreevidencia = "contrato"
                    ext = profesorinvitado.archivocontrato.__str__()[profesorinvitado.archivocontrato.__str__().rfind("."):]
                    if os.path.exists(SITE_STORAGE + profesorinvitado.archivocontrato.url):
                        fantasy_zip.write(SITE_STORAGE + profesorinvitado.archivocontrato.url, carpetaprofesor + "/" + nombreevidencia + ext.lower())

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
                # archivocopiado = ContentFile(archivo.read())
                archivocopiado.name =  nombre_archivo

                # Actualizo el informe
                informeconformidad.documentosoporte = archivocopiado
                informeconformidad.fechadocumento = datetime.now().date()
                informeconformidad.save(request)

                # Borro el informe creado de manera general, no la del registro
                os.remove(archivo)

                log(u'%s generó enlace de descarga de evidencias para informe: %s' % (persona, informeconformidad), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Enlace generado con éxito", "showSwal": True, "documento": informeconformidad.documentosoporte.url})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar el enlace. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'informeconformidadpdf':
            try:
                data = {}

                informeconformidad = InformeDocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))

                if not informeconformidad.impreso:
                    data['informe'] = informeconformidad
                    data['conclusiones'] = informeconformidad.conclusiones()
                    data['recomendaciones'] = informeconformidad.recomendaciones()

                    # Creacion de los archivos por separado
                    directorio = SITE_STORAGE + '/media/proyectoinvestigacion/informes'
                    try:
                        os.stat(directorio)
                    except:
                        os.mkdir(directorio)

                    # Archivo de la parte 1 del informe
                    nombrearchivo = 'informeparte1_' + str(informeconformidad.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                    valida = convert_html_to_pdf(
                        'adm_docenteinvitado/informeconformidadpdf.html',
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
                    nombrearchivoresultado = generar_nombre('informeconformidad', 'informeconformidad.pdf')
                    pdfOutputFile = open(directorio + "/" + nombrearchivoresultado, "wb")
                    pdfWriter.write(pdfOutputFile)

                    # Borro los documento individuales creados a exepción del archivo del proyecto cargado por el docente
                    os.remove(archivo1)

                    pdfOutputFile.close()

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
                    informeconformidad.impreso = True
                    informeconformidad.archivo = archivocopiado
                    informeconformidad.save(request)

                    # Borro el informe creado de manera general, no la del registro
                    os.remove(archivo)

                    log(u'%s generó informe de conformidad de resultados: %s' % (persona, informeconformidad), request, "edit")
                return JsonResponse({"result": "ok", "id": encrypt(informeconformidad.id)})
                # return JsonResponse({"result": "ok", "documento": informedocente.archivo.url})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar documento del informe. [%s]" % msg})

        elif action == 'firmarinformeconformidad':
            try:
                if 'iddoc' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                tipofirma = request.POST['tipofirma']
                archivofirma = request.FILES['archivofirma']
                clavefirma = request.POST['cfirma']
                descripcionarchivo = 'Archivo de la firma electrónica'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivofirma, ['P12', 'PFX'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto el informe
                informe = InformeDocenteInvitado.objects.get(pk=int(encrypt(request.POST['iddoc'])))

                # Verifico si puede firmar el informe
                if tipofirma == 'ELA':
                    if not informe.puede_firmar_elabora():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede editar el Registro porque ya ha sido revisado por otra instancia", "showSwal": "True", "swalType": "warning"})
                elif tipofirma == 'VAL':
                    if not informe.puede_firmar_validador():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede editar el Registro porque ya ha sido revisado por otra instancia", "showSwal": "True", "swalType": "warning"})
                else:
                    if not informe.puede_firmar_aprobador():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede editar el Registro porque ya ha sido revisado por otra instancia", "showSwal": "True", "swalType": "warning"})

                # Obtengo el archivo del informe firmado previamente
                archivoinforme = informe.archivofirmado if informe.archivofirmado else informe.archivo
                rutapdfarchivo = SITE_STORAGE + archivoinforme.url

                if tipofirma == 'ELA':
                    textoabuscar = informe.nombre_firma_elabora()
                    textofirma = 'Elaborado por:'
                    ocurrencia = 1
                elif tipofirma == 'VAL':
                    textoabuscar = informe.nombre_firma_valida()
                    textofirma = 'Validado por:'
                    ocurrencia = 1
                else:
                    textoabuscar = informe.nombre_firma_aprueba()
                    textofirma = 'Aprobado por:'
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

                nombre = "informeconformidadfirmado"

                nombrearchivofirmado = generar_nombre(nombre, nombre + '.pdf')
                objarchivo = DjangoFile(generar_archivo_firmado, nombrearchivofirmado)

                informe.archivofirmado = objarchivo

                if tipofirma == 'ELA':
                    informe.firmaelabora = True
                    informe.estado = 3
                elif tipofirma == 'VAL':
                    informe.fechavalida = datetime.now()
                    informe.firmavalida = True
                    informe.estado = 4
                else:
                    informe.fechaaprueba = datetime.now()
                    informe.firmaaprueba = True
                    informe.estado = 6

                informe.save(request)

                # Notificar para las firmas del validador y aprobador
                if informe.estado != 6:
                    notificar_docente_invitado(informe, "VALINFCONF" if informe.estado == 3 else "APRINFCONF")

                log(u'%s firmó informe de conformidad de resultados: %s' % (persona, informe), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Documento firmado con éxito", "showSwal": True, "idi": encrypt(informe.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % msg, "showSwal": "True", "swalType": "error"})



        elif action == 'reporteactividadpdf':
            try:
                data = {}

                asistenciadocente = AsistenciaDocenteInvitado.objects.get(pk=int(encrypt(request.POST['id'])))
                informedocente = asistenciadocente.informe

                if not asistenciadocente.repimpreso:
                    # Generar el número del reporte
                    anio = datetime.now().date().year
                    secuencia = secuencia_reporte_validacion_asistencia(anio)
                    numero = f'{str(secuencia).zfill(3)}-EFI-FI-REP-AE-{anio}'

                    # Actualizar el registro
                    asistenciadocente.secuenciarep = secuencia
                    asistenciadocente.numerorep = numero
                    asistenciadocente.fecharep = datetime.now()
                    asistenciadocente.save(request)

                    data['asistencia'] = asistenciadocente
                    data['informe'] = informedocente
                    data['actividades'] = informedocente.actividades()

                    # Creacion de los archivos por separado
                    directorio = SITE_STORAGE + '/media/proyectoinvestigacion/informes'
                    try:
                        os.stat(directorio)
                    except:
                        os.mkdir(directorio)

                    # Archivo de la parte 1 del informe
                    nombrearchivo = 'reporteparte1_' + str(asistenciadocente.id) + '_' + str(random.randint(1, 10000)) + '.pdf'
                    valida = convert_html_to_pdf(
                        'adm_docenteinvitado/reporteactividadejecpdf.html',
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
                    nombrearchivoresultado = generar_nombre('reporteconformidad', 'reporteconformidad.pdf')
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
                    asistenciadocente.repimpreso = True
                    asistenciadocente.archivorep = archivocopiado
                    asistenciadocente.save(request)

                    # Borro el informe creado de manera general, no la del registro
                    os.remove(archivo)

                    log(u'%s generó reporte de conformidad de actividades ejecutadas: %s' % (persona, asistenciadocente), request, "edit")

                return JsonResponse({"result": "ok", "idr": encrypt(asistenciadocente.id)})
                # return JsonResponse({"result": "ok", "documento": informedocente.archivo.url})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar documento del reporte de actividades. [%s]" % msg})

        elif action == 'firmarreporte':
            try:
                if 'iddoc' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                tipofirma = request.POST['tipofirma']
                archivofirma = request.FILES['archivofirma']
                clavefirma = request.POST['cfirma']
                descripcionarchivo = 'Archivo de la firma electrónica'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivofirma, ['P12', 'PFX'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto asistencia
                asistenciadocente = AsistenciaDocenteInvitado.objects.get(pk=int(encrypt(request.POST['iddoc'])))
                informe = asistenciadocente.informe

                # Verifico si puede firmar el reporte
                if tipofirma == 'VAL':
                    if not asistenciadocente.puede_firmar_validador():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede editar el Registro porque ya ha sido revisado por otra instancia", "showSwal": "True", "swalType": "warning"})
                else:
                    if not asistenciadocente.puede_firmar_aprobador():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede editar el Registro porque ya ha sido revisado por otra instancia", "showSwal": "True", "swalType": "warning"})

                # Obtengo el archivo del reporte
                archivoreporte = asistenciadocente.archivorepfirmado if asistenciadocente.archivorepfirmado else asistenciadocente.archivorep
                rutapdfarchivo = SITE_STORAGE + archivoreporte.url

                if tipofirma == 'VAL':
                    textoabuscar = informe.nombre_firma_valida()
                    textofirma =  textoabuscar # 'Validado por:'
                    ocurrencia = 1
                else:
                    textoabuscar = informe.nombre_firma_aprueba()
                    textofirma = textoabuscar #'Aprobado por:'
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
                    y = 5000 - int(valor[3]) - 4087
                else:
                    y = 0

                x = 127 if tipofirma == 'VAL' else 355
                # x = 87  # izq
                # x = 230  # cent
                # x = 350  # der

                # Si no existe el nombre de la persona en el documento
                if y == 0:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"No se encuentra el nombre del firmante en el documento", "showSwal": "True", "swalType": "warning"})

                # Obtener extensión y leer archivo de la firma
                extfirma = os.path.splitext(archivofirma.name)[1][1:]
                bytesfirma = archivofirma.read()

                # Firma del documento
                datau = JavaFirmaEc(
                    archivo_a_firmar=archivoreporte,
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

                nombre = "reporteactividadfirmado"

                nombrearchivofirmado = generar_nombre(nombre, nombre + '.pdf')
                objarchivo = DjangoFile(generar_archivo_firmado, nombrearchivofirmado)

                asistenciadocente.archivorepfirmado = objarchivo

                if tipofirma == 'VAL':
                    asistenciadocente.fechavalidarep = datetime.now()
                    asistenciadocente.firmavalidarep = True
                else:
                    asistenciadocente.fechaapruebarep = datetime.now()
                    asistenciadocente.firmaapruebarep = True

                asistenciadocente.save(request)

                log(u'%s firmó reporte de actividades ejecutadas: %s' % (persona, asistenciadocente), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Documento firmado con éxito", "showSwal": True, "idr": encrypt(asistenciadocente.id)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % msg, "showSwal": "True", "swalType": "error"})


        return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Solicitud incorrecta.", "showSwal": "True", "swalType": "error"})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'adddocenteinvitado':
                try:
                    data['title'] = u'Agregar Profesor Invitado'
                    data['modalidades'] = Modalidad.objects.filter(status=True).order_by('id')
                    template = get_template("adm_docenteinvitado/modal/adddocenteinvitado.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editdocenteinvitado':
                try:
                    data['title'] = u'Editar Profesor Invitado'
                    data['docenteinvitado'] = DocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['modalidades'] = Modalidad.objects.filter(status=True).order_by('id')
                    template = get_template("adm_docenteinvitado/modal/editdocenteinvitado.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscarprofesorinvitado':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if len(s) == 1:
                        profesores = Profesor.objects.filter(Q(persona__apellido1__icontains=s[0])
                                                        | Q(persona__apellido2__icontains=s[0])
                                                        | Q(persona__cedula__icontains=s[0])
                                                        | Q(persona__ruc__icontains=s[0])
                                                        | Q(persona__pasaporte__icontains=s[0]),
                                                        status=True, categoria_id=2).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                    else:
                        profesores = Profesor.objects.filter(persona__apellido1__icontains=s[0],
                                                           persona__apellido2__icontains=s[1],
                                                           status=True, categoria_id=2).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    listado = [{"id": pro.id,
                                "name": str(pro.persona.nombre_completo_inverso()),
                                "identificacion": pro.persona.identificacion(),
                                "idpersona": pro.persona.id,
                                "usuario": pro.persona.usuario.username if pro.persona.usuario else '',
                                "emailinst": pro.persona.emailinst,
                                "email": pro.persona.email,
                                "celular": pro.persona.telefono,
                                "telefono": pro.persona.telefono_conv,
                                "coordinacion": pro.coordinacion.nombre,
                                "dedicacion": pro.dedicacion.nombre,
                                "horas": pro.dedicacion.horas} for pro in profesores]

                    data = {"result": "ok", "results": listado}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'criteriosdocenteinvitado':
                try:
                    data['title'] = u'Criterios del Profesor'
                    docenteinvitado = DocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    criterios = CriterioDocenteInvitado.objects.filter(status=True, vigente=True).order_by('id')
                    lista = []
                    for criterio in criterios:
                        lista.append({"criterio": criterio, "marcado": "S" if docenteinvitado.funciones_asignadas().filter(criterio=criterio).exists() else "N"})

                    data['docenteinvitado'] = docenteinvitado
                    data['listacriterios'] = lista
                    template = get_template("adm_docenteinvitado/modal/funciondocenteinvitado.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'actividades':
                try:
                    data['title'] = u'Actividades y Metas del Profesor Invitado'
                    data['docente'] = docenteinvitado = DocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['criteriosdocente'] = docenteinvitado.funciones_asignadas()
                    data['puedeeditar'] = False if docenteinvitado.informes() or not docenteinvitado.vigente else True
                    return render(request, "adm_docenteinvitado/actividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'addactividadcriterio':
                try:
                    data['title'] = u'Agregar Actividad al Criterio'
                    data['criteriodocente'] = FuncionDocenteInvitado.objects.get(pk=int(encrypt(request.GET['idcrit'])))
                    data['numcrit'] = request.GET['numcrit']
                    template = get_template("adm_docenteinvitado/modal/addactividadcriterio.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editactividadcriterio':
                try:
                    data['title'] = u'Editar Actividad del Criterio'
                    data['actividad'] = ActividadCriterioDocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['numcrit'] = request.GET['numcrit']
                    template = get_template("adm_docenteinvitado/modal/editactividadcriterio.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'horarios':
                try:
                    data['title'] = u'Horarios del Profesor Invitado'
                    data['docente'] = docenteinvitado = DocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    horarios = docenteinvitado.horarios()
                    lista_horarios = []
                    fechaactual = datetime.now().date()

                    for horario in horarios:
                        if docenteinvitado.vigente:
                            if horario.estado == 1:
                                dias = (horario.inicio - fechaactual).days if fechaactual <= horario.inicio else (fechaactual - horario.inicio).days
                                habilitar = dias <= 30 # 10
                            else:
                                habilitar = False
                        else:
                            habilitar = False

                        lista_horarios.append({"horario": horario, "puedehabilitar": habilitar})

                    data['detallehorarios'] = lista_horarios
                    return render(request, "adm_docenteinvitado/horario.html", data)
                except Exception as ex:
                    pass

            elif action == 'aprobarhorario':
                try:
                    data['horario'] = horario = HorarioDocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['puedeaprobar'] = puedeaprobar = horario.puede_aprobar()
                    title = u'Aprobar Horario de Actividades del Docente' if puedeaprobar else u'Horario de Actividades del Docente'
                    data['docente'] = docenteinvitado = horario.docente

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
                            if horario.detallehorariodocenteinvitado_set.values("id").filter(status=True, turno=turno, dia=dia['numero'], funcion=funcion1).exists():
                                lista_dias_turno.append({"numerodia": dia["numero"], "idturno": turno.id, "idfuncion": funcion1.id, "marcado": "S", "bloqueado": "N"})
                            else:
                                lista_dias_turno.append({"numerodia": dia["numero"], "idturno": turno.id, "idfuncion": "0", "marcado": "N", "bloqueado": "S"})

                        lista_turnos.append({"turno": turno, "dias": lista_dias_turno})

                    data['turnos'] = lista_turnos
                    data['estados'] = ESTADO_HORARIO_DOCENTE
                    template = get_template("adm_docenteinvitado/modal/aprobarhorario.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'detallehorario':
                try:
                    data['horario'] = horario = HorarioDocenteInvitado.objects.get(pk=int(encrypt(request.GET['idh'])))
                    funcion = FuncionDocenteInvitado.objects.get(pk=int(encrypt(request.GET['idf'])))
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
                            if horario.detallehorariodocenteinvitado_set.values("id").filter(status=True, turno=turno, dia=dia['numero'], funcion=funcion).exists():
                                lista_dias_turno.append({"numerodia": dia["numero"], "idturno": turno.id, "idfuncion": funcion.id, "marcado": "S", "bloqueado": "N"})
                            else:
                                lista_dias_turno.append({"numerodia": dia["numero"], "idturno": turno.id, "idfuncion": "0", "marcado": "N", "bloqueado": "S"})

                        lista_turnos.append({"turno": turno, "dias": lista_dias_turno})

                    data['turnos'] = lista_turnos
                    template = get_template("adm_docenteinvitado/modal/detallehorario.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editnombrefirma':
                try:
                    data['title'] = u'Editar Nombre para Firma de Documentos'
                    data['docenteinvitado'] = DocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("adm_docenteinvitado/modal/editnombrefirma.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'finalizarcontrato':
                try:
                    data['title'] = u'Finalizar Contrato de Profesor Invitado'
                    data['docenteinvitado'] = DocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("adm_docenteinvitado/modal/finalizarcontrato.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'informes':
                try:
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True, tipo=1, estado__in=[3, 4, 5, 6]), ''
                    desde, hasta, estadoid = request.GET.get('desde', ''), request.GET.get('hasta', ''), int(request.GET.get('estadoid', '0'))
                    idi = request.GET.get('idi', '')
                    idr = request.GET.get('idr', '')

                    if idi:
                        informe = InformeDocenteInvitado.objects.get(pk=int(encrypt(idi)))
                        data['informe'] = informe.archivofirmado.url
                        data['tipoinforme'] = 'Informe Técnico de Actividades Firmado'

                    if idr:
                        asistencia = AsistenciaDocenteInvitado.objects.get(pk=int(encrypt(idr)))
                        data['reporteactividad'] = asistencia.archivorepfirmado.url if asistencia.archivorepfirmado else asistencia.archivorep.url
                        data['tipoinforme'] = 'Reporte de Actividades Ejecutadas Firmado' if asistencia.archivorepfirmado else 'Reporte de Actividades Ejecutadas sin Firmar'

                    if search:
                        data['s'] = search
                        ss = search.split(" ")
                        if len(ss) == 1:
                            filtro = filtro & (Q(docente__profesor__persona__nombres__icontains=search) |
                                               Q(docente__profesor__persona__apellido1__icontains=search) |
                                               Q(docente__profesor__persona__apellido2__icontains=search))
                        else:
                            filtro = filtro & (Q(docente__profesor__persona__apellido1__contains=ss[0]) &
                                               Q(docente__profesor__persona__apellido2__contains=ss[1]))

                        url_vars += f'&s={search}'

                    if desde:
                        data['desde'] = datetime.strptime(desde, '%Y-%m-%d').date()
                        filtro = filtro & Q(fecha__gte=desde)
                        url_vars += f'&desde={desde}'

                    if hasta:
                        data['hasta'] = datetime.strptime(hasta, '%Y-%m-%d').date()
                        filtro = filtro & Q(fecha__lte=hasta)
                        url_vars += f'&hasta={hasta}'

                    data['estadoid'] = estadoid
                    if estadoid:
                        filtro = filtro & Q(estado=estadoid)
                        url_vars += f'&estadoid={estadoid}'

                    informes = InformeDocenteInvitado.objects.filter(filtro).order_by('-fechaenvio')

                    paging = MiPaginador(informes, 25)
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
                    data['informes'] = page.object_list
                    data['estados'] = [{"id": 3, "descripcion": "POR VALIDAR"},
                                       {"id": 4, "descripcion": "VALIDADA"}]
                    data['title'] = u'Informes de Actividades de los Docentes Invitados'
                    data['esuath'] = es_uath

                    if not es_uath:
                        ic_pendientes_firma = existen_informes_conformidad_pendiente_firmar()
                        data['icsinfirma'] = ic_pendientes_firma['icsinfirma']
                        data['mensaje'] = ic_pendientes_firma['mensaje']

                    return render(request, "adm_docenteinvitado/informe.html", data)
                except Exception as ex:
                    pass

            elif action == 'validarinforme':
                try:
                    data['title'] = u'Validar Informe de Actividades del Profesor Invitado'
                    data['informe'] = informe = InformeDocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['actividadesinforme'] = informe.actividades()
                    data['conclusiones'] = informe.conclusiones()
                    data['recomendaciones'] = informe.recomendaciones()
                    data['estados'] = [{"id": 4, "descripcion": "VALIDADA"},
                                       {"id": 5, "descripcion": "NOVEDAD"}]
                    data['estadosavance'] = VALOR_AVANCE_ACTIVIDAD

                    return render(request, "adm_docenteinvitado/validarinforme.html", data)
                except Exception as ex:
                    pass

            elif action == 'firmarinforme':
                try:
                    tipofirma = request.GET['tipofirma']

                    informe = InformeDocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))

                    data['iddoc'] = informe.id
                    data['tipofirma'] = tipofirma

                    if tipofirma == 'VAL':  # Persona que valida
                        data['title'] = u'Firmar Informe Técnico. Validado por: {}'.format(informe.valida.nombre_completo_inverso())
                        data['idper'] = informe.valida.id
                    else:  # Persona que aprueba
                        data['title'] = u'Firmar Informe Técnico. Aprobado por: {}'.format(informe.aprueba.nombre_completo_inverso())
                        data['idper'] = informe.aprueba.id

                    data['mensaje'] = "Firma del Informe de Actividades N° <b>{}</b> del docente <b>{}</b>".format(informe.numero, informe.docente.profesor.persona.nombre_completo_inverso())
                    data['accionfirma'] = action

                    template = get_template("pro_becadocente/firmardocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'asistencias':
                try:
                    idsol = request.GET.get('idsol', '')
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
                    desde, hasta, estadoid = request.GET.get('desde', ''), request.GET.get('hasta', ''), int(request.GET.get('estadoid', '0'))

                    if search:
                        data['s'] = search
                        ss = search.split(" ")
                        if len(ss) == 1:
                            filtro = filtro & (Q(informe__docente__profesor__persona__nombres__icontains=search) |
                                               Q(informe__docente__profesor__persona__apellido1__icontains=search) |
                                               Q(informe__docente__profesor__persona__apellido2__icontains=search))
                        else:
                            filtro = filtro & (Q(informe__docente__profesor__persona__apellido1__contains=ss[0]) &
                                               Q(informe__docente__profesor__persona__apellido2__contains=ss[1]))

                        url_vars += f'&s={search}'

                    if desde:
                        data['desde'] = desde
                        filtro = filtro & Q(fechaenvio__gte=desde)
                        url_vars += f'&desde={desde}'

                    if hasta:
                        data['hasta'] = hasta
                        filtro = filtro & Q(fechaenvio__lte=hasta)
                        url_vars += f'&hasta={hasta}'

                    data['estadoid'] = estadoid
                    if estadoid:
                        filtro = filtro & Q(estado=estadoid)
                        url_vars += f'&estadoid={estadoid}'

                    solicitudes = AsistenciaDocenteInvitado.objects.filter(filtro).order_by('-fechaenvio', '-secuencia')

                    paging = MiPaginador(solicitudes, 25)
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
                    data['solicitudes'] = page.object_list
                    data['estados'] = [{"id": 1, "descripcion": "POR VALIDAR"},
                                       {"id": 2, "descripcion": "EN REVISIÓN"},
                                       {"id": 3, "descripcion": "APROBADO"}]
                    data['fechadesde'] = datetime.now().date()
                    data['fechahasta'] = datetime.now().date()
                    data['title'] = u'Solicitudes de Validación de Asistencia de los Profesores Invitados'
                    data['esuath'] = es_uath

                    if not es_uath:
                        ic_pendientes_firma = existen_informes_conformidad_pendiente_firmar()
                        data['icsinfirma'] = ic_pendientes_firma['icsinfirma']
                        data['mensaje'] = ic_pendientes_firma['mensaje']

                    if idsol:
                        solicitudasistencia = AsistenciaDocenteInvitado.objects.get(pk=int(encrypt(idsol)))
                        data['solicitudasistencia'] = solicitudasistencia.archivosolfirmada.url if solicitudasistencia.archivosolfirmada else solicitudasistencia.archivosol.url
                        data['titulo'] = 'Solicitud de Validación de Asistencias Firmada' if solicitudasistencia.archivosolfirmada else 'Solicitud de Validación de Asistencias'

                    return render(request, "adm_docenteinvitado/asistencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'addsolicitudasistencia':
                try:
                    data['title'] = u'Agregar Solicitud de Validación de Asistencias'

                    # Consulto los informes que deberían formar parte de la solicitud
                    informes = InformeDocenteInvitado.objects.filter(status=True, tipo=1, estado=4, detalleasistenciadocenteinvitado__isnull=True).order_by('numero')

                    if not informes:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No existen informes validados y pendientes de solicitar validación de asistencias", "showSwal": "True", "swalType": "warning"})

                    fechavalida = informes[0].inicio
                    data['fecha'] = datetime.now().date()
                    data['anio'] = fechavalida.year
                    data['mes'] = getmonthname(fechavalida)
                    data['informes'] = informes
                    data['totaldocentes'] = len(informes)

                    template = get_template("adm_docenteinvitado/modal/addsolicitudasistencia.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al obtener los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

            elif action == 'firmarsolicitudasistencia':
                try:
                    tipofirma = request.GET['tipofirma']

                    asistenciadocente = AsistenciaDocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))

                    data['iddoc'] = asistenciadocente.id
                    data['tipofirma'] = tipofirma
                    data['title'] = u'Firmar Solicitud de Validación. Solicitado por: {}'.format(asistenciadocente.solicita.nombre_completo_inverso())
                    data['idper'] = asistenciadocente.solicita.id

                    data['mensaje'] = "Firma de la Solicitud de Validación de asistencias N° <b>{}</b>".format(asistenciadocente.numero)
                    data['accionfirma'] = action

                    template = get_template("pro_becadocente/firmardocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'detalleasistencia':
                try:
                    solicitud = AsistenciaDocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    search, filtro, url_vars = request.GET.get('s', ''), Q(solicitud=solicitud, status=True), ''
                    desde, hasta, estadoid = request.GET.get('desde', ''), request.GET.get('hasta', ''), int(request.GET.get('estadoid', '0'))

                    if 'imp' in request.GET:
                        data['reporteasistencia'] = solicitud.archivorepfirmado.url if solicitud.archivorepfirmado else solicitud.archivorep.url
                        data['tituloreporte'] = 'Reporte de Validación de Asistencia Firmado' if solicitud.archivorepfirmado else 'Reporte de Validación de Asistencia sin Firmar'

                    if search:
                        data['s'] = search
                        ss = search.split(" ")
                        if len(ss) == 1:
                            filtro = filtro & (Q(informe__docente__profesor__persona__nombres__icontains=search) |
                                               Q(informe__docente__profesor__persona__apellido1__icontains=search) |
                                               Q(informe__docente__profesor__persona__apellido2__icontains=search))
                        else:
                            filtro = filtro & (Q(informe__docente__profesor__persona__apellido1__contains=ss[0]) &
                                               Q(informe__docente__profesor__persona__apellido2__contains=ss[1]))

                        url_vars += f'&s={search}'

                    if desde:
                        data['desde'] = desde
                        filtro = filtro & Q(fechaenvio__gte=desde)
                        url_vars += f'&desde={desde}'

                    if hasta:
                        data['hasta'] = hasta
                        filtro = filtro & Q(fechaenvio__lte=hasta)
                        url_vars += f'&hasta={hasta}'

                    data['estadoid'] = estadoid
                    if estadoid:
                        filtro = filtro & Q(estado=estadoid)
                        url_vars += f'&estadoid={estadoid}'

                    detalles = DetalleAsistenciaDocenteInvitado.objects.filter(filtro).order_by('id')

                    paging = MiPaginador(detalles, 25)
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
                    data['detalles'] = page.object_list
                    data['estados'] = [{"id": 1, "descripcion": "POR VALIDAR"},
                                       {"id": 2, "descripcion": "EN REVISIÓN"},
                                       {"id": 3, "descripcion": "APROBADO"}]
                    data['fechadesde'] = datetime.now().date()
                    data['fechahasta'] = datetime.now().date()
                    data['title'] = u'Detalle de Profesores para Validación de asistencia'
                    data['esuath'] = es_uath
                    data['esanluath'] = es_analista_uath
                    data['esexpuath'] = es_experto_uath
                    data['esdiruath'] = es_director_uath
                    data['solicitud'] = solicitud

                    return render(request, "adm_docenteinvitado/detalleasistencia.html", data)
                except Exception as ex:
                    pass

            elif action == 'validarasistencia':
                try:
                    data['tipo'] = tipo = request.GET['tipo']
                    data['asistencia'] = asistencia = DetalleAsistenciaDocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    puedevalidar = puederevisar = puedeaprobar = False

                    if tipo == 'I':
                        title = u"Información de Asistencia del Profesor Invitado"
                    elif tipo == 'V':
                        puedevalidar = asistencia.puede_validar()
                        title = u'Validar Asistencia del Profesor Invitado' if puedevalidar else u'Información de Asistencia del Profesor Invitado'
                        data['estados'] = [{"id": 2, "descripcion": "VALIDADO"},
                                           {"id": 5, "descripcion": "RECHAZADO"}]
                    elif tipo == 'R':
                        puederevisar = asistencia.puede_revisar()
                        title = u'Revisar Asistencia del Profesor Invitado' if puederevisar else u'Información de Asistencia del Profesor Invitado'
                        data['estados'] = [{"id": 3, "descripcion": "REVISADO"}]
                    else:
                        puedeaprobar = asistencia.puede_aprobar()
                        title = u'Aprobar Asistencia del Profesor Invitado' if puedeaprobar else u'Información de Asistencia del Profesor Invitado'
                        data['estados'] = [{"id": 4, "descripcion": "APROBADO"}]

                    data['puedevalidar'] = puedevalidar
                    data['puederevisar'] = puederevisar
                    data['puedeaprobar'] = puedeaprobar
                    template = get_template("adm_docenteinvitado/modal/validarasistencia.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al obtener los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

            elif action == 'firmarreporteasistencia':
                try:
                    tipofirma = request.GET['tipofirma']

                    asistenciadocente = AsistenciaDocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))

                    data['iddoc'] = asistenciadocente.id
                    data['tipofirma'] = tipofirma
                    data['title'] = u'Firmar Reporte de Validación. Aprobado por: {}'.format(asistenciadocente.aprueba.nombre_completo_inverso())
                    data['idper'] = asistenciadocente.aprueba.id

                    data['mensaje'] = "Firma del Reporte de Validación de asistencias N° <b>{}</b>".format(asistenciadocente.numerorep)
                    data['accionfirma'] = action

                    template = get_template("pro_becadocente/firmardocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'informesdocente':
                try:
                    data['title'] = u'Informes de Actividades del Profesor Invitado'
                    data['docente'] = docenteinvitado = DocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['informes'] = docenteinvitado.informes()
                    return render(request, "adm_docenteinvitado/informedocente.html", data)
                except Exception as ex:
                    pass

            elif action == 'anexosinforme':
                try:
                    data['title'] = u'Anexos del Informe de Actividades'
                    data['informe'] = informe = InformeDocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['docente'] = informe.docente
                    data['actividadesinforme'] = informe.actividades()
                    data['puedeeditar'] = False
                    return render(request, "adm_docenteinvitado/anexoinformedocente.html", data)
                except Exception as ex:
                    pass

            elif action == 'informesconformidad':
                try:
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True, tipo=2), ''
                    desde, hasta, estadoid = request.GET.get('desde', ''), request.GET.get('hasta', ''), int(request.GET.get('estadoid', '0'))
                    id = request.GET.get('id', '')
                    imp = request.GET.get('imp', '')
                    idi = request.GET.get('idi', '')

                    if id and imp:
                        informe = InformeDocenteInvitado.objects.get(pk=int(encrypt(id)))
                        data['informe'] = informe.archivo.url
                        data['tipoinforme'] = 'Informe Técnico de Conformidad de Resultados sin Firmar'

                    if idi:
                        informe = InformeDocenteInvitado.objects.get(pk=int(encrypt(idi)))
                        data['informe'] = informe.archivofirmado.url
                        data['tipoinforme'] = 'Informe Técnico de Conformidad de Resultados Firmado'

                    if search:
                        data['s'] = search
                        ss = search.split(" ")
                        if len(ss) == 1:
                            filtro = filtro & (Q(solicitudasistencia__detalleasistenciadocenteinvitado__informe__docente__profesor__persona__nombres__icontains=search) |
                                               Q(solicitudasistencia__detalleasistenciadocenteinvitado__informe__docente__profesor__persona__apellido1__icontains=search) |
                                               Q(solicitudasistencia__detalleasistenciadocenteinvitado__informe__docente__profesor__persona__apellido2__icontains=search))
                        else:
                            filtro = filtro & (Q(solicitudasistencia__detalleasistenciadocenteinvitado__informe__docente__profesor__persona__apellido1__contains=ss[0]) &
                                               Q(solicitudasistencia__detalleasistenciadocenteinvitado__informe__docente__profesor__persona__apellido2__contains=ss[1]))

                        url_vars += f'&s={search}'

                    if desde:
                        data['desde'] = datetime.strptime(desde, '%Y-%m-%d').date()
                        filtro = filtro & Q(fecha__gte=desde)
                        url_vars += f'&desde={desde}'

                    if hasta:
                        data['hasta'] = datetime.strptime(hasta, '%Y-%m-%d').date()
                        filtro = filtro & Q(fecha__lte=hasta)
                        url_vars += f'&hasta={hasta}'

                    data['estadoid'] = estadoid
                    if estadoid:
                        filtro = filtro & Q(estado=estadoid)
                        url_vars += f'&estadoid={estadoid}'

                    informes = InformeDocenteInvitado.objects.filter(filtro).order_by('-fecha')

                    paging = MiPaginador(informes, 25)
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
                    data['informes'] = page.object_list
                    data['estados'] = [{"id": 1, "descripcion": "EN EDICIÓN"},
                                       {"id": 3, "descripcion": "ELABORADO"},
                                       {"id": 4, "descripcion": "VALIDADO"},
                                       {"id": 6, "descripcion": "APROBADO"}]

                    data['title'] = u'Informes de Conformidad de Resultados'
                    data['esuath'] = es_uath

                    if not es_uath:
                        ic_pendientes_firma = existen_informes_conformidad_pendiente_firmar()
                        data['icsinfirma'] = ic_pendientes_firma['icsinfirma']
                        data['mensaje'] = ic_pendientes_firma['mensaje']

                    return render(request, "adm_docenteinvitado/informeconformidad.html", data)
                except Exception as ex:
                    pass

            elif action == 'addinformeconformidad':
                try:
                    data['title'] = u'Agregar Informe de Conformidad de Resultados'
                    data['vicerrector'] = vicerrector_investigacion_posgrado()
                    data['decano'] = decano_investigacion()
                    data['fecha'] = datetime.now().date()
                    data['reportesasistencia'] = asistencias = AsistenciaDocenteInvitado.objects.filter(status=True, estado=3, tieneinforme=False).order_by('numerorep')
                    data['totalreportes'] = totalreportes = len(asistencias)

                    if totalreportes == 1:
                        reporteasistencia = asistencias[0]
                        conclusion = "Que de acuerdo a los informes de actividades mensuales presentados por los profesores invitados " \
                            "se evidencia avances en los productos y servicios que se establecen en el presente contrato por prestación de servicios profesionales, " \
                            f"mismos que permiten dar continuidad al proceso de pago correspondiente al mes de {getmonthname(reporteasistencia.fechavalida).title()} {reporteasistencia.fechavalida.year}."
                    else:
                        reporteasistencia = None
                        conclusion = None

                    data['reporteasistencia'] = reporteasistencia
                    data['conclusion'] = conclusion
                    return render(request, "adm_docenteinvitado/addinformeconformidad.html", data)
                except Exception as ex:
                    pass

            elif action == 'evaluacioninforme':
                try:
                    data['title'] = u'Evaluación de Avance de Actividades y Productos'
                    data['informe'] = informe = InformeDocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("adm_docenteinvitado/modal/evaluacionavance.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editinformeconformidad':
                try:
                    data['title'] = u'Editar Informe de Conformidad de Resultados'
                    data['informe'] = informe = InformeDocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    # data['totalinformes'] = informe.docente.informes().count()
                    # data['actividades'] = informe.actividades()
                    data['conclusiones'] = informe.conclusiones()
                    data['recomendaciones'] = informe.recomendaciones()
                    # data['estados'] = ESTADO_CUMPLIMIENTO_ACTIVIDAD
                    # data['fecha'] = datetime.now().date()
                    return render(request, "adm_docenteinvitado/editinformeconformidad.html", data)
                except Exception as ex:
                    pass

            elif action == 'firmarinformeconformidad':
                try:
                    tipofirma = request.GET['tipofirma']

                    informe = InformeDocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))

                    data['iddoc'] = informe.id
                    data['tipofirma'] = tipofirma

                    if tipofirma == 'ELA':  # Persona que elabora
                        data['title'] = u'Firmar Informe de Conformidad. Elaborado por: {}'.format(informe.elabora.nombre_completo_inverso())
                        data['idper'] = informe.elabora.id
                    elif tipofirma == 'VAL':  # Persona que valida
                        data['title'] = u'Firmar Informe de Conformidad. Validado por: {}'.format(informe.valida.nombre_completo_inverso())
                        data['idper'] = informe.valida.id
                    else:  # Persona que aprueba
                        data['title'] = u'Firmar Informe de Conformidad. Aprobado por: {}'.format(informe.aprueba.nombre_completo_inverso())
                        data['idper'] = informe.aprueba.id

                    data['mensaje'] = "Firma del Informe de Conformidad N° <b>{}</b> del mes de <b>{}</b> del <b>{}</b>".format(informe.numero, getmonthname(informe.inicio), informe.inicio.year)
                    data['accionfirma'] = action

                    template = get_template("pro_becadocente/firmardocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})



            elif action == 'firmarreporte':
                try:
                    tipofirma = request.GET['tipofirma']

                    asistenciadocente = AsistenciaDocenteInvitado.objects.get(pk=int(encrypt(request.GET['id'])))
                    informe = asistenciadocente.informe

                    data['iddoc'] = asistenciadocente.id
                    data['tipofirma'] = tipofirma

                    if tipofirma == 'VAL':  # Persona que valida
                        data['title'] = u'Firmar Reporte de Actividades. Validado por: {}'.format(informe.valida.nombre_completo_inverso())
                        data['idper'] = informe.valida.id
                    else:  # Persona que aprueba
                        data['title'] = u'Firmar Reporte de Actividades. Aprobado por: {}'.format(informe.aprueba.nombre_completo_inverso())
                        data['idper'] = informe.aprueba.id

                    data['mensaje'] = "Firma del Reporte de actividades ejecutadas N° <b>{}</b> del docente <b>{}</b>".format(asistenciadocente.numerorep, informe.docente.profesor.persona.nombre_completo_inverso())
                    data['accionfirma'] = action

                    template = get_template("pro_becadocente/firmardocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


            return HttpResponseRedirect(request.path)
        else:
            try:
                search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''

                if search:
                    data['s'] = search
                    ss = search.split(" ")
                    if len(ss) == 1:
                        filtro = filtro & (Q(profesor__persona__nombres__icontains=search) |
                                           Q(profesor__persona__apellido1__icontains=search) |
                                           Q(profesor__persona__apellido2__icontains=search))
                    else:
                        filtro = filtro & (Q(profesor__persona__apellido1__contains=ss[0]) &
                                           Q(profesor__persona__apellido2__contains=ss[1]))

                    url_vars += '&s=' + search

                docentes = DocenteInvitado.objects.filter(filtro).order_by('profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres')

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
                data['esuath'] = es_uath

                if not es_uath:
                    ic_pendientes_firma = existen_informes_conformidad_pendiente_firmar()
                    data['icsinfirma'] = ic_pendientes_firma['icsinfirma']
                    data['mensaje'] = ic_pendientes_firma['mensaje']

                data['title'] = u'Profesores Invitados'

                return render(request, "adm_docenteinvitado/view.html", data)
            except Exception as ex:
                pass

