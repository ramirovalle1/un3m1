# -*- coding: UTF-8 -*-
import io
import json
import os
from math import ceil

import PyPDF2
from datetime import time, datetime
from decimal import Decimal
import time as ET

import requests
from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
import time as pausaparaemail

from fitz import fitz
from xlwt import easyxf, XFStyle, Workbook
from django.core.files import File as DjangoFile
import random

from core.firmar_documentos import firmar
from core.firmar_documentos_ec import JavaFirmaEc
from decorators import secure_module
from investigacion.forms import GrupoInvestigacionForm, FinanciamientoPonenciaForm, PostulacionObraRelevanciaForm
from investigacion.funciones import analista_investigacion, tecnico_investigacion
from investigacion.models import GrupoInvestigacion, FUNCION_INTEGRANTE_GRUPO_INVESTIGACION, GrupoInvestigacionIntegrante, ConvocatoriaObraRelevancia, ObraRelevancia, TIPO_FILIACION, ObraRelevanciaParticipante, ObraRelevanciaRecorrido, EvaluacionObraRelevancia, EvaluacionObraRelevanciaDetalle
from sagest.commonviews import obtener_estado_solicitud
from settings import SITE_STORAGE
from sga.commonviews import adduserdata
from sga.forms import PlanificarPonenciasForm
from sga.funciones import MiPaginador, log, variable_valor, \
    convertir_fecha, remover_caracteres_tildes_unicode, cuenta_email_disponible, generar_nombre, email_valido, \
    validar_archivo, null_to_decimal, cuenta_email_disponible_para_envio, fechaletra_corta, fecha_letra_rango
from sga.funcionesxhtml2pdf import convert_html_to_pdf
from sga.models import CUENTAS_CORREOS, Persona, PlanificarPonencias, ConvocatoriaPonencia, CriterioPonencia, PlanificarPonenciasCriterio, PlanificarPonenciasRecorrido, MESES_CHOICES, Externo, Profesor, AreaConocimientoTitulacion, Titulacion, InstitucionEducacionSuperior, Pais, Titulo
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
    es_evaluador_externo = persona.es_evaluador_externo_obra_relevancia()
    es_evaluador_interno = persona.es_evaluador_interno_obra_relevancia()

    if not es_profesor and not es_evaluador_interno and not es_evaluador_externo:
        return HttpResponseRedirect("/?info=El Módulo está disponible para profesores y evaluadores de obras de relevancia.")

    data['profesor'] = profesor = perfilprincipal.profesor
    periodo = request.session['periodo']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addpostulacion':
            try:
                form = PostulacionObraRelevanciaForm(request.POST, request.FILES)

                # Validar los archivos
                if 'archivolibro' in request.FILES:
                    archivo = request.FILES['archivolibro']
                    descripcionarchivo = 'Libro'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocapitulo' in request.FILES:
                    archivo = request.FILES['archivocapitulo']
                    descripcionarchivo = 'Capítulo de Libro'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivoeditorial' in request.FILES:
                    archivo = request.FILES['archivoeditorial']
                    descripcionarchivo = 'Certificado Editorial'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivoinforme' in request.FILES:
                    archivo = request.FILES['archivoinforme']
                    descripcionarchivo = 'Informe Revisión pares'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if form.is_valid():
                    # Validar que la obra de relevancia no esté repetida
                    if int(form.cleaned_data['tipo']) == 1:
                        if ObraRelevancia.objects.values('id').filter(profesor=profesor, titulolibro__icontains=form.cleaned_data['titulolibro'], status=True).exists():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El Título del libro ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})
                    else:
                        if ObraRelevancia.objects.values('id').filter(profesor=profesor, titulolibro__icontains=form.cleaned_data['titulolibro'], titulocapitulo__icontains=form.cleaned_data['titulocapitulo'], status=True).exists():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El Título del libro ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    # Obtengo lista de participantes
                    participantes = json.loads(request.POST['lista_items1'])

                    # Verifico que el solicitante conste en la lista de participantes
                    lista = list(filter(lambda item: int(item['idpersona']) == persona.id, participantes))
                    if len(lista) == 0:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El solicitante no ha sido agregado al detalle de participantes de la obra", "showSwal": "True", "swalType": "warning"})

                    # Consulto la convocatoria
                    convocatoria = ConvocatoriaObraRelevancia.objects.get(pk=int(encrypt(request.POST['idc'])))

                    # Obtengo estado SOLICITADO
                    estado = obtener_estado_solicitud(15, 1)

                    # Guardo la obra de relevancia
                    obrarelevancia = ObraRelevancia(
                        convocatoria=convocatoria,
                        profesor=profesor,
                        tipo=form.cleaned_data['tipo'],
                        titulolibro=form.cleaned_data['titulolibro'].strip(),
                        titulocapitulo=form.cleaned_data['titulocapitulo'].strip(),
                        isbn=form.cleaned_data['isbn'].strip(),
                        aniopublicacion=form.cleaned_data['aniopublicacion'],
                        editorial=form.cleaned_data['editorial'].strip(),
                        areaconocimiento=form.cleaned_data['areaconocimiento'],
                        subareaconocimiento=form.cleaned_data['subareaconocimiento'],
                        subareaespecificaconocimiento=form.cleaned_data['subareaespecificaconocimiento'],
                        lineainvestigacion=form.cleaned_data['lineainvestigacion'],
                        observacion='',
                        estado=estado
                    )
                    obrarelevancia.save(request)

                    if 'archivolibro' in request.FILES:
                        newfile = request.FILES['archivolibro']
                        newfile._name = generar_nombre("libro", newfile._name)
                        obrarelevancia.archivolibro = newfile

                    if 'archivocapitulo' in request.FILES:
                        newfile = request.FILES['archivocapitulo']
                        newfile._name = generar_nombre("capitulolibro", newfile._name)
                        obrarelevancia.archivocapitulo = newfile

                    if 'archivoeditorial' in request.FILES:
                        newfile = request.FILES['archivoeditorial']
                        newfile._name = generar_nombre("certeditorial", newfile._name)
                        obrarelevancia.archivoeditorial = newfile

                    if 'archivoinforme' in request.FILES:
                        newfile = request.FILES['archivoinforme']
                        newfile._name = generar_nombre("informerevision", newfile._name)
                        obrarelevancia.archivoinforme = newfile

                    obrarelevancia.save(request)

                    # Guardo a los participantes
                    # TEMPORAL
                    # Guardo al solicitante primero
                    for participante in participantes:
                        if int(participante['idpersona']) == persona.id:
                            participanteobra = ObraRelevanciaParticipante(
                                obrarelevancia=obrarelevancia,
                                filiacion=participante['filiacion'],
                                tipo=1,
                                persona_id=participante['idpersona']
                            )
                            participanteobra.save(request)
                            break

                    # Guardo al resto de participantes
                    for participante in participantes:
                        if int(participante['idpersona']) != persona.id:
                            participanteobra = ObraRelevanciaParticipante(
                                obrarelevancia=obrarelevancia,
                                filiacion=participante['filiacion'],
                                tipo=1,
                                persona_id=participante['idpersona']
                            )
                            participanteobra.save(request)
                    # TEMPORAL

                    # for participante in participantes:
                    #     participanteobra = ObraRelevanciaParticipante(
                    #         obrarelevancia=obrarelevancia,
                    #         filiacion=participante['filiacion'],
                    #         tipo=1,
                    #         persona_id=participante['idpersona']
                    #     )
                    #     participanteobra.save(request)

                    # Guardo el recorrido
                    recorrido = ObraRelevanciaRecorrido(
                        obrarelevancia=obrarelevancia,
                        fecha=datetime.now().date(),
                        persona=persona,
                        observacion='POSTULACIÓN EN EDICIÓN',
                        estado=estado
                    )
                    recorrido.save(request)

                    log(u'%s adicionó postulación a obra de relevancia: %s' % (persona, obrarelevancia), request, "add")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in form.errors.items()])
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editpostulacion':
            try:
                form = PostulacionObraRelevanciaForm(request.POST, request.FILES)

                # Validar los archivos
                if 'archivolibro' in request.FILES:
                    archivo = request.FILES['archivolibro']
                    descripcionarchivo = 'Libro'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocapitulo' in request.FILES:
                    archivo = request.FILES['archivocapitulo']
                    descripcionarchivo = 'Capítulo de Libro'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '10MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivoeditorial' in request.FILES:
                    archivo = request.FILES['archivoeditorial']
                    descripcionarchivo = 'Certificado Editorial'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivoinforme' in request.FILES:
                    archivo = request.FILES['archivoinforme']
                    descripcionarchivo = 'Informe Revisión pares'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if form.is_valid():
                    # Consultar la obra de relevancia
                    obrarelevancia = ObraRelevancia.objects.get(pk=int(encrypt(request.POST['id'])))

                    # Validar que la obra de relevancia no esté repetida
                    if obrarelevancia.tipo == 1:
                        if ObraRelevancia.objects.values('id').filter(profesor=profesor, titulolibro__icontains=form.cleaned_data['titulolibro'], status=True).exclude(pk=int(encrypt(request.POST['id']))).exists():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El Título del libro ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})
                    else:
                        if ObraRelevancia.objects.values('id').filter(profesor=profesor, titulolibro__icontains=form.cleaned_data['titulolibro'], titulocapitulo__icontains=form.cleaned_data['titulocapitulo'], status=True).exclude(pk=int(encrypt(request.POST['id']))).exists():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El Título del libro ya ha sido ingresado anteriormente", "showSwal": "True", "swalType": "warning"})

                    # Obtengo lista de participantes
                    participantes = json.loads(request.POST['lista_items1'])

                    # Verifico que el solicitante conste en la lista de participantes
                    lista = list(filter(lambda item: int(item['idpersona']) == persona.id, participantes))
                    if len(lista) == 0:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El solicitante no ha sido agregado al detalle de participantes de la obra", "showSwal": "True", "swalType": "warning"})

                    # Obtengo lista de participantes eliminados
                    participanteseliminados = json.loads(request.POST['lista_items2']) if 'lista_items2' in request.POST else []

                    # Actualizo la obra de relevancia
                    obrarelevancia.titulolibro = form.cleaned_data['titulolibro'].strip()
                    obrarelevancia.titulocapitulo = form.cleaned_data['titulocapitulo'].strip()
                    obrarelevancia.isbn = form.cleaned_data['isbn'].strip()
                    obrarelevancia.aniopublicacion = form.cleaned_data['aniopublicacion']
                    obrarelevancia.editorial = form.cleaned_data['editorial'].strip()
                    obrarelevancia.areaconocimiento = form.cleaned_data['areaconocimiento']
                    obrarelevancia.subareaconocimiento = form.cleaned_data['subareaconocimiento']
                    obrarelevancia.subareaespecificaconocimiento = form.cleaned_data['subareaespecificaconocimiento']
                    obrarelevancia.lineainvestigacion = form.cleaned_data['lineainvestigacion']

                    if 'archivolibro' in request.FILES:
                        newfile = request.FILES['archivolibro']
                        newfile._name = generar_nombre("libro", newfile._name)
                        obrarelevancia.archivolibro = newfile

                    if 'archivocapitulo' in request.FILES:
                        newfile = request.FILES['archivocapitulo']
                        newfile._name = generar_nombre("capitulolibro", newfile._name)
                        obrarelevancia.archivocapitulo = newfile

                    if 'archivoeditorial' in request.FILES:
                        newfile = request.FILES['archivoeditorial']
                        newfile._name = generar_nombre("certeditorial", newfile._name)
                        obrarelevancia.archivoeditorial = newfile

                    if 'archivoinforme' in request.FILES:
                        newfile = request.FILES['archivoinforme']
                        newfile._name = generar_nombre("informerevision", newfile._name)
                        obrarelevancia.archivoinforme = newfile

                    obrarelevancia.save(request)

                    # Guardo los participantes de la obra de relevancia
                    # TEMPORAL
                    # Guardo primero al solicitante
                    for participante in participantes:
                        # Nuevo integrante
                        if int(participante['idreg']) == 0 and int(participante['idpersona']) == persona.id:
                            participanteobra = ObraRelevanciaParticipante(
                                obrarelevancia=obrarelevancia,
                                filiacion=participante['filiacion'],
                                tipo=1,
                                persona_id=participante['idpersona']
                            )
                            participanteobra.save(request)
                            break

                    # Guardo al resto de participantes
                    for participante in participantes:
                        # Nuevo integrante
                        if int(participante['idreg']) == 0 and int(participante['idpersona']) != persona.id:
                            participanteobra = ObraRelevanciaParticipante(
                                obrarelevancia=obrarelevancia,
                                filiacion=participante['filiacion'],
                                tipo=1,
                                persona_id=participante['idpersona']
                            )
                            participanteobra.save(request)
                    # TEMPORAL

                    # for participante in participantes:
                    #     # Nuevo integrante
                    #     if int(participante['idreg']) == 0:
                    #         participanteobra = ObraRelevanciaParticipante(
                    #             obrarelevancia=obrarelevancia,
                    #             filiacion=participante['filiacion'],
                    #             tipo=1,
                    #             persona_id=participante['idpersona']
                    #         )
                    #         participanteobra.save(request)

                    # Elimino los que se borraron del detalle
                    if participanteseliminados:
                        for participante in participanteseliminados:
                            participanteobra = ObraRelevanciaParticipante.objects.get(pk=int(participante['idreg']))
                            participanteobra.status = False
                            participanteobra.save(request)

                    log(u'%s editó postulación a obra de relevancia: %s' % (persona, obrarelevancia), request, "edit")
                    return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in form.errors.items()])
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'confirmarpostulacion':
            try:
                # Consulto la postulación
                obrarelevancia = ObraRelevancia.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que tenga estado EN EDICIÓN
                if not obrarelevancia.estado.valor == 1:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el Registro porque no tiene estado EN EDICIÓN", "showSwal": "True", "swalType": "warning"})

                # Obtengo estado SOLICITADO
                estado = obtener_estado_solicitud(15, 2)

                # Actualizo la postulación
                obrarelevancia.estado = estado
                obrarelevancia.save(request)

                # Guardo el recorrido
                recorrido = ObraRelevanciaRecorrido(
                    obrarelevancia=obrarelevancia,
                    fecha=datetime.now().date(),
                    persona=persona,
                    observacion='POSTULACIÓN REGISTRADA',
                    estado=estado
                )
                recorrido.save(request)

                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, ..., sga7@unemi.edu.ec

                # E-mail del destinatario
                lista_email_envio = persona.lista_emails_envio()
                # lista_email_envio = ['isaltosm@unemi.edu.ec']
                lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                lista_archivos_adjuntos = []

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                asuntoemail = "Registro de Postulación a Obra de Relevancia"
                titulo = "Postulación Obra de Relevancia"
                tiponotificacion = "REGSOL"

                send_html_mail(asuntoemail,
                               "emails/postulacionobrarelevancia.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'saludo': 'Estimada' if persona.sexo_id == 1 else 'Estimado',
                                'nombrepersona': persona.nombre_completo_inverso(),
                                'obrarelevancia': obrarelevancia
                                },
                               lista_email_envio,
                               lista_email_cco,
                               lista_archivos_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                # Notificar por e-mail al Técnico de Investigación
                personadestinatario = tecnico_investigacion()

                # E-mail del destinatario
                lista_email_envio = personadestinatario.lista_emails_envio()
                # lista_email_envio = ['isaltosm@unemi.edu.ec']

                asuntoemail = "Registro de Postulación a Obra de Relevancia"
                titulo = "Postulación Obra de Relevancia"
                tiponotificacion = "REGANLINV"

                send_html_mail(asuntoemail,
                               "emails/postulacionobrarelevancia.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'saludo': 'Estimada' if personadestinatario.sexo_id == 1 else 'Estimado',
                                'nombrepersona': personadestinatario.nombre_completo_inverso(),
                                'nombredocente': persona.nombre_completo_inverso(),
                                'saludodocente': 'la docente' if persona.sexo_id == 1 else 'el docente',
                                'obrarelevancia': obrarelevancia
                                },
                               lista_email_envio,
                               lista_email_cco,
                               lista_archivos_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                log(u'%s confirmó postulación para obra de relevancia: %s' % (persona, obrarelevancia), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro de postulación confirmado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'delpostulacion':
            try:
                # Consulto la postulación
                obrarelevancia = ObraRelevancia.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que tenga estado EN EDICIÓN
                if not obrarelevancia.estado.valor == 1:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede eliminar el Registro porque no tiene estado EN EDICIÓN", "showSwal": "True", "swalType": "warning"})

                # Obtengo estado ANULADO
                estado = obtener_estado_solicitud(15, 5)

                # Elimino la postulación
                obrarelevancia.estado = estado
                obrarelevancia.observacion = "ELIMINADA POR EL SOLICITANTE"
                obrarelevancia.status = False
                obrarelevancia.save(request)

                # Guardo el recorrido
                recorrido = ObraRelevanciaRecorrido(
                    obrarelevancia=obrarelevancia,
                    fecha=datetime.now().date(),
                    persona=persona,
                    observacion='POSTULACIÓN ELIMINADA',
                    estado=estado
                )
                recorrido.save(request)

                log(u'%s eliminó postulación para obra de relevancia: %s' % (persona, obrarelevancia), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al eliminar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addevaluacioninterna':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la obra de relevancia
                obrarelevancia = ObraRelevancia.objects.get(pk=int(encrypt(request.POST['id'])))
                convocatoria = obrarelevancia.convocatoria
                estadoactual = obrarelevancia.estado.valor

                # Verifico que no exista evaluación interna con el evaluador para la obra de relevancia
                if EvaluacionObraRelevancia.objects.filter(status=True, obrarelevancia=obrarelevancia, evaluador=persona, tipo=1).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La evaluación ya ha sido guardada", "showSwal": "True", "swalType": "warning"})

                # Obtengo los valores de los switch de las rubricas
                rubricas = json.loads(request.POST['lista_items1'])

                # Obtiene los valores de los arreglos
                iddetallesrrub = request.POST.getlist('iddetallerub[]')  # IDs de rubricas
                observacionesrub = request.POST.getlist('observacionrub[]')  # Observaciones detalles de rubricas

                # Guardo la evaluación interna
                evaluacion = EvaluacionObraRelevancia(
                    obrarelevancia=obrarelevancia,
                    fecha=datetime.now().date(),
                    tipo=1,
                    evaluador=persona,
                    titulo_id=request.POST['tituloacademico'],
                    cumplerequisito=request.POST['cumplerequisito'] == 'S',
                    observacion=request.POST['observacion'].strip(),
                    estado=1
                )
                evaluacion.save(request)

                # Guardo el detalle de la evaluación interna
                numero = 1
                for idrubrica, rubrica, observacion in zip(iddetallesrrub, rubricas, observacionesrub):
                    detalleevaluacion = EvaluacionObraRelevanciaDetalle(
                        evaluacion=evaluacion,
                        numero=numero,
                        rubrica_id=idrubrica,
                        cumple=rubrica['valor'],
                        observacion=observacion.strip().upper()
                    )
                    detalleevaluacion.save(request)
                    numero += 1

                # Si no tiene estado EVALUACION EN CURSO
                if estadoactual != 7:
                    # Actualizo el estado de la obra a EVALUACION EN CURSO
                    estado = obtener_estado_solicitud(15, 7)
                    obrarelevancia.estado = estado
                    obrarelevancia.save(request)

                    # Guardo el recorrido
                    recorrido = ObraRelevanciaRecorrido(
                        obrarelevancia=obrarelevancia,
                        fecha=datetime.now().date(),
                        persona=persona,
                        observacion=estado.observacion,
                        estado=estado
                    )
                    recorrido.save(request)

                log(u'% agregó evaluación interna de obra de relevancia: %s' % (persona, evaluacion), request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editevaluacioninterna':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la evaluación intena
                evaluacion = EvaluacionObraRelevancia.objects.get(pk=int(encrypt(request.POST['id'])))

                # Obtengo los valores de los switch de las rubricas
                rubricas = json.loads(request.POST['lista_items1'])

                # Obtiene los valores de los arreglos
                iddetallesrrub = request.POST.getlist('iddetallerub[]')  # IDs de detalles rubricas
                observacionesrub = request.POST.getlist('observacionrub[]')  # Observaciones detalles de rubricas

                # Actualizo la evaluación interna
                evaluacion.cumplerequisito = request.POST['cumplerequisito'] == 'S'
                evaluacion.observacion = request.POST['observacion'].strip()
                evaluacion.titulo_id = request.POST['tituloacademico']
                evaluacion.estado = 1
                evaluacion.archivo = None
                evaluacion.archivofirmado = None
                evaluacion.observacionrevision = ''
                evaluacion.revisor = None
                evaluacion.revisado = False
                evaluacion.fecharevision = None
                evaluacion.save(request)

                # Actualizo los detalles de la evaluación interna
                for iddetalle, rubrica, observacion in zip(iddetallesrrub, rubricas, observacionesrub):
                    # Consulto el detalle
                    detalleevaluacion = EvaluacionObraRelevanciaDetalle.objects.get(pk=iddetalle)
                    detalleevaluacion.cumple = rubrica['valor']
                    detalleevaluacion.observacion = observacion.strip().upper()
                    detalleevaluacion.save(request)

                log(u'%s editó evaluación interna de obra de relevancia: %s' % (persona, evaluacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'actaevaluacionpdf':
            try:
                data = {}
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la evaluación
                evaluacion = EvaluacionObraRelevancia.objects.get(pk=int(encrypt(request.POST['id'])))

                data['evaluacion'] = evaluacion
                data['obrarelevancia'] = obrarelevancia = evaluacion.obrarelevancia
                data['participantes'] = obrarelevancia.listado_participantes_acta_evaluacion()
                detalle = evaluacion.detalle_rubricas()
                data['editorialscopwos'] = detalle.filter(rubrica__numero=7)[0].cumple
                data['rubricas'] = detalle.exclude(rubrica__numero=7)

                # Creacion del archivo
                directorio = SITE_STORAGE + '/media/certificadoedocente'
                try:
                    os.stat(directorio)
                except:
                    os.mkdir(directorio)

                # Archivo de la solicitud de beca
                nombrearchivo = generar_nombre('actaevaluacioninterna', 'actaevaluacioninterna.pdf') if evaluacion.tipo == 1 else generar_nombre('actaevaluacionexterna', 'actaevaluacionexterna.pdf')

                valida = convert_html_to_pdf(
                    'pro_obrarelevancia/actaevaluacionpdf.html',
                    {'pagesize': 'A4', 'data': data},
                    nombrearchivo,
                    directorio
                )

                if not valida:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar el documento de acta de evaluación.", "showSwal": "True", "swalType": "error"})

                # archivo = 'media/certificadoedocente/' + nombrearchivo
                archivo = SITE_STORAGE + '/media/certificadoedocente/' + nombrearchivo

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
                archivocopiado.name = nombrearchivo

                # Actualizo la evaluacion
                evaluacion.archivo = archivocopiado
                evaluacion.estado = 2
                evaluacion.observacionrevision = ''
                evaluacion.revisor = None
                evaluacion.revisado = False
                evaluacion.fecharevision = None
                evaluacion.save(request)

                ET.sleep(3)
                # Borro la evaluación creada de manera general, no la del registro
                os.remove(archivo)

                return JsonResponse({"result": "ok", "documento": evaluacion.archivo.url})
            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar el documento del acta de evaluación. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'firmaractaevaluacion':
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

                # Consulto la evaluación de la obra
                evaluacion = EvaluacionObraRelevancia.objects.get(pk=int(encrypt(request.POST['iddoc'])))

                # Obtengo el archivo de la evaluación
                archivosolicitud = evaluacion.archivo
                rutapdfarchivo = SITE_STORAGE + archivosolicitud.url
                textoabuscar = 'Firma del evaluador'

                vecescontrado = 0
                ocurrencia = 1

                # Obtener coordenadas para ubicar al firma dependiendo de donde se encuentra ubicado el nombre de la persona
                documento = fitz.open(rutapdfarchivo)
                numpaginafirma = int(documento.page_count) - 1

                saltolinea = False
                words_dict = {}
                for page_number, page in enumerate(documento):
                    if page_number == numpaginafirma:
                        words = page.get_text("blocks")
                        words_dict[0] = words

                valor = None
                for cadena in words_dict[0]:
                    linea = cadena[4].replace("\n", " ")
                    if linea:
                        linea = linea.strip()

                    if textoabuscar in linea:
                        valor = cadena

                        vecescontrado += 1
                        if vecescontrado == ocurrencia:
                            break

                if valor:
                    y = 5000 - int(valor[3]) - 4100  # 4095 0 4100
                else:
                    y = 0

                # x = 87  # izq
                x = 230  # cent
                # x = 374  # der

                # Si no existe el nombre de la persona en el documento
                if y == 0:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"No se encuentra el nombre del firmante en el documento", "showSwal": "True", "swalType": "warning"})

                # Obtener extensión y leer archivo de la firma
                extfirma = os.path.splitext(archivofirma.name)[1][1:]
                bytesfirma = archivofirma.read()

                # Firma del documento
                datau = JavaFirmaEc(
                    archivo_a_firmar=archivosolicitud,
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

                if evaluacion.tipo == 1:
                    nombrearchivofirmado = generar_nombre('actaevaluacioninternafirmada', 'actaevaluacioninternafirmada.pdf')
                else:
                    nombrearchivofirmado = generar_nombre('actaevaluacionexternafirmada', 'actaevaluacionexternafirmada.pdf')

                objarchivo = DjangoFile(generar_archivo_firmado, nombrearchivofirmado)

                evaluacion.estado = 3
                evaluacion.archivofirmado = objarchivo
                evaluacion.observacionrevision = ''
                evaluacion.revisor = None
                evaluacion.revisado = False
                evaluacion.fecharevision = None
                evaluacion.save(request)

                log(u'%s firmó evaluación %s para la obra de relevancia: %s' % (persona, 'interna' if evaluacion.tipo == 1 else 'externa' , evaluacion.obrarelevancia), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Documento firmado con éxito", "showSwal": True, "documento": evaluacion.archivofirmado.url})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al firmar el documento. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'confirmarevaluacion':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la evaluacion
                evaluacion = EvaluacionObraRelevancia.objects.get(pk=int(encrypt(request.POST['id'])))
                obrarelevancia = evaluacion.obrarelevancia

                # Actualizo la evaluación
                evaluacion.fechaconfirma = datetime.now().date()
                evaluacion.estado = 5
                evaluacion.save(request)

                # Notificar por e-mail a la coordinación de investigación
                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, . . .sga7@unemi.edu.ec

                # Destinatarios
                lista_email_envio = ['investigacion@unemi.edu.ec']
                lista_email_cco = []
                # lista_email_envio = ['ivan_saltos_medina@hotmail.com']
                lista_archivos_adjuntos = []

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                if evaluacion.tipo == 1:
                    asuntoemail = "Registro de Evaluación Interna de Obra de Relevancia"
                    titulo = "Evaluación Interna de Postulación a Obra de Relevancia"
                    tiponotificacion = 'EVALINTCONF'
                else:
                    asuntoemail = "Registro de Evaluación Externa de Obra de Relevancia"
                    titulo = "Evaluación Externa de Postulación a Obra de Relevancia"
                    tiponotificacion = 'EVALEXTCONF'

                send_html_mail(asuntoemail,
                               "emails/postulacionobrarelevancia.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'evaluador': evaluacion.evaluador.nombre_completo_inverso(),
                                'obrarelevancia': obrarelevancia
                                },
                               lista_email_envio,
                               lista_email_cco,
                               lista_archivos_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                log(u'%s confirmó evaluación %s de propuesta de obra de relevancia: %s' % (persona, 'interna' if evaluacion.tipo == 1 else 'externa', evaluacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro de evaluación confirmado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addformacion':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                archivo = request.FILES['archivotitulo']
                descripcionarchivo = 'Archivo Título obtenido'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Verificar que no esté repetido el título de la persona
                if Titulacion.objects.filter(status=True, persona=persona, titulo_id=request.POST['titulo']).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La persona ya tiene asignada ese título académico", "showSwal": "True", "swalType": "warning"})

                archivo._name = generar_nombre("titulacion_", archivo._name)

                # Guardo el título académico de la persona
                titulacion = Titulacion(
                    persona=persona,
                    titulo_id=request.POST['titulo'],
                    institucion_id=request.POST['institucion'],
                    fechaobtencion=request.POST['fechaobtencion'],
                    registro=request.POST['registrosenescyt'].strip(),
                    archivo=archivo,
                    pais_id=request.POST['pais']
                )
                titulacion.save(request)

                log(u'%s agregó formación académica: %s' % (persona, titulacion), request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editformacion':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                archivo = None

                if 'archivotitulo' in request.FILES:
                    archivo = request.FILES['archivotitulo']
                    descripcionarchivo = 'Archivo Título obtenido'

                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Verificar que no esté repetido el título de la persona
                if Titulacion.objects.filter(status=True, persona=persona, titulo_id=request.POST['tituloe']).exclude(pk=int(encrypt(request.POST['id']))).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La persona ya tiene asignada ese título académico", "showSwal": "True", "swalType": "warning"})

                # Consulto el título
                titulacion = Titulacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Actualizo el título académico
                titulacion.titulo_id = request.POST['tituloe']
                titulacion.fechaobtencion = request.POST['fechaobtencione']
                titulacion.registro = request.POST['registrosenescyte'].strip()
                titulacion.pais_id = request.POST['paise']

                if archivo:
                    archivo._name = generar_nombre("titulacion_", archivo._name)
                    titulacion.archivo = archivo

                titulacion.save(request)

                log(u'%s editó formación académica: %s' % (persona, titulacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'delformacion':
            try:
                # Consulto el título
                titulacion = Titulacion.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que se pueda eliminar
                if titulacion.en_uso_evaluacion_obra_relevancia():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede eliminar el Registro", "showSwal": "True", "swalType": "warning"})

                # Elimino el grupo de investigación
                titulacion.status = False
                titulacion.save(request)

                log(u'%s eliminó formación académica %s' % (persona, titulacion), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al eliminar el registro. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addevaluacionexterna':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la obra de relevancia
                obrarelevancia = ObraRelevancia.objects.get(pk=int(encrypt(request.POST['id'])))
                convocatoria = obrarelevancia.convocatoria
                estadoactual = obrarelevancia.estado.valor

                # Consultar titulación del evaluador externo
                titulacion = persona.mis_titulaciones().filter(titulo__nivel__nivel__in=[3, 4, 5]).order_by('-titulo__nivel__nivel')[0] if persona.mis_titulaciones().filter(titulo__nivel__nivel__in=[3, 4, 5]).exists() else None

                # Verifico que no exista evaluación externa con el evaluador para la obra de relevancia
                if EvaluacionObraRelevancia.objects.filter(status=True, obrarelevancia=obrarelevancia, evaluador=persona, tipo=2).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La evaluación ya ha sido guardada", "showSwal": "True", "swalType": "warning"})

                # Obtengo los valores de los switch de las rubricas
                rubricas = json.loads(request.POST['lista_items1'])

                # Obtiene los valores de los arreglos
                iddetallesrrub = request.POST.getlist('iddetallerub[]')  # IDs de rubricas
                observacionesrub = request.POST.getlist('observacionrub[]')  # Observaciones detalles de rubricas

                if not titulacion:
                    # Guardar la formación académica del evaluador externo
                    archivo = request.FILES['archivotitulo']
                    descripcionarchivo = 'Archivo Título obtenido'

                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                    # Verificar que no esté repetido el título de la persona
                    if Titulacion.objects.filter(status=True, persona=persona, titulo_id=request.POST['titulo']).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La persona ya tiene asignada ese título académico", "showSwal": "True", "swalType": "warning"})

                    archivo._name = generar_nombre("titulacion_", archivo._name)

                    # Guardo el título académico de la persona
                    titulacion = Titulacion(
                        persona=persona,
                        titulo_id=request.POST['titulo'],
                        institucion_id=request.POST['institucion'],
                        fechaobtencion=request.POST['fechaobtencion'],
                        registro=request.POST['registrosenescyt'].strip(),
                        archivo=archivo,
                        pais_id=request.POST['pais']
                    )
                    titulacion.save(request)

                    log(u'%s agregó formación académica: %s' % (persona, titulacion), request, "add")

                # Guardo la evaluación externa
                evaluacion = EvaluacionObraRelevancia(
                    obrarelevancia=obrarelevancia,
                    fecha=datetime.now().date(),
                    tipo=2,
                    evaluador=persona,
                    titulo=titulacion,
                    cumplerequisito=request.POST['cumplerequisito'] == 'S',
                    observacion=request.POST['observacion'].strip(),
                    estado=1
                )
                evaluacion.save(request)

                # Guardo el detalle de la evaluación externa
                numero = 1
                for idrubrica, rubrica, observacion in zip(iddetallesrrub, rubricas, observacionesrub):
                    detalleevaluacion = EvaluacionObraRelevanciaDetalle(
                        evaluacion=evaluacion,
                        numero=numero,
                        rubrica_id=idrubrica,
                        cumple=rubrica['valor'],
                        observacion=observacion.strip().upper()
                    )
                    detalleevaluacion.save(request)
                    numero += 1

                # Si no tiene estado EVALUACION EN CURSO
                if estadoactual != 7:
                    # Actualizo el estado de la obra a EVALUACION EN CURSO
                    estado = obtener_estado_solicitud(15, 7)
                    obrarelevancia.estado = estado
                    obrarelevancia.save(request)

                    # Guardo el recorrido
                    recorrido = ObraRelevanciaRecorrido(
                        obrarelevancia=obrarelevancia,
                        fecha=datetime.now().date(),
                        persona=persona,
                        observacion=estado.observacion,
                        estado=estado
                    )
                    recorrido.save(request)

                log(u'% agregó evaluación externa de obra de relevancia: %s' % (persona, evaluacion), request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editevaluacionexterna':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la evaluación externa
                evaluacion = EvaluacionObraRelevancia.objects.get(pk=int(encrypt(request.POST['id'])))
                titulacion = evaluacion.titulo

                # Obtengo los valores de los switch de las rubricas
                rubricas = json.loads(request.POST['lista_items1'])

                # Obtiene los valores de los arreglos
                iddetallesrrub = request.POST.getlist('iddetallerub[]')  # IDs de detalles rubricas
                observacionesrub = request.POST.getlist('observacionrub[]')  # Observaciones detalles de rubricas

                if not persona.tiene_actas_evaluacion_obrarelevancia_generadas() or evaluacion.estado == 2:
                    archivo = None

                    if 'archivotitulo' in request.FILES:
                        archivo = request.FILES['archivotitulo']
                        descripcionarchivo = 'Archivo Título obtenido'

                        # Validar el archivo
                        resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                    # Actualizo el título académico
                    titulacion.titulo_id = request.POST['titulo']
                    titulacion.fechaobtencion = request.POST['fechaobtencion']
                    titulacion.registro = request.POST['registrosenescyt'].strip()
                    titulacion.pais_id = request.POST['pais']

                    if archivo:
                        archivo._name = generar_nombre("titulacion_", archivo._name)
                        titulacion.archivo = archivo

                    titulacion.save(request)

                    log(u'%s editó formación académica: %s' % (persona, titulacion), request, "edit")

                # Actualizo la evaluación externa
                evaluacion.cumplerequisito = request.POST['cumplerequisito'] == 'S'
                evaluacion.observacion = request.POST['observacion'].strip()
                evaluacion.estado = 1
                evaluacion.archivo = None
                evaluacion.archivofirmado = None
                evaluacion.observacionrevision = ''
                evaluacion.revisor = None
                evaluacion.revisado = False
                evaluacion.fecharevision = None
                evaluacion.save(request)

                # Actualizo los detalles de la evaluación externa
                for iddetalle, rubrica, observacion in zip(iddetallesrrub, rubricas, observacionesrub):
                    # Consulto el detalle
                    detalleevaluacion = EvaluacionObraRelevanciaDetalle.objects.get(pk=iddetalle)
                    detalleevaluacion.cumple = rubrica['valor']
                    detalleevaluacion.observacion = observacion.strip().upper()
                    detalleevaluacion.save(request)

                log(u'%s editó evaluación externa de obra de relevancia: %s' % (persona, evaluacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'subiracta':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                archivo = request.FILES['archivoacta']
                descripcionarchivo = 'Archivo Acta Firmada'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto la evaluación
                evaluacion = EvaluacionObraRelevancia.objects.get(pk=int(encrypt(request.POST['id'])))

                archivo._name = generar_nombre("actaevaluacionexternafirmada", archivo._name)

                evaluacion.estado = 3
                evaluacion.archivofirmado = archivo
                evaluacion.observacionrevision = ''
                evaluacion.revisor = None
                evaluacion.revisado = False
                evaluacion.fecharevision = None
                evaluacion.save(request)

                log(u'%s subió acta de evaluación firmada: %s' % (persona, evaluacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Solicitud incorrecta.", "showSwal": "True", "swalType": "error"})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'postulaciones':
                try:
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), '&action=' + action
                    idc, ids = request.GET.get('idc', ''), request.GET.get('id', '')
                    url_vars += '&idc=' + idc

                    data['convocatoria'] = convocatoria = ConvocatoriaObraRelevancia.objects.get(pk=int(encrypt(idc)))

                    if ids:
                        filtro = filtro & (Q(pk=int(encrypt(ids))))
                        url_vars += '&ids=' + ids
                    else:
                        filtro = filtro & (Q(convocatoria=convocatoria) & Q(profesor=profesor))

                    postulaciones = ObraRelevancia.objects.filter(filtro).order_by('-fecha_creacion')

                    existenovedad = False #postulaciones.filter(estado__valor__in=[4, 6]).exists()

                    paging = MiPaginador(postulaciones, 25)
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
                    data['postulaciones'] = page.object_list
                    data['title'] = u'Mis postulaciones para Obras de Relevancia'
                    data['existenovedad'] = existenovedad

                    return render(request, "pro_obrarelevancia/postulaciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'mostrarrecorrido':
                try:
                    title = u'Recorrido Postulación a Obra de Relevancia'
                    obrarelevancia = ObraRelevancia.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['obrarelevancia'] = obrarelevancia
                    data['recorrido'] = obrarelevancia.obrarelevanciarecorrido_set.filter(status=True).order_by('id')
                    template = get_template("pro_obrarelevancia/recorridopostulacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'mostrarinformacion':
                try:
                    title = u'Información de la Postulación a Obra de Relevancia'
                    obrarelevancia = ObraRelevancia.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['obrarelevancia'] = obrarelevancia
                    data['participantes'] = obrarelevancia.participantes()
                    template = get_template("pro_obrarelevancia/informacionpostulacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addpostulacion':
                try:
                    data['title'] = u'Agregar Postulación para Obra de Relevancia'
                    form = PostulacionObraRelevanciaForm()
                    data['convocatoria'] = ConvocatoriaObraRelevancia.objects.get(pk=int(encrypt(request.GET['idc'])))
                    data['idc'] = request.GET['idc']
                    data['anioactual'] = datetime.now().year
                    data['form'] = form
                    return render(request, "pro_obrarelevancia/addpostulacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addparticipante':
                try:
                    data['title'] = u'Agregar Integrante a la Obra'
                    data['tipofiliacion'] = TIPO_FILIACION

                    template = get_template("pro_obrarelevancia/addparticipante.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editpostulacion':
                try:
                    data['title'] = u'Editar Postulación para Obra de Relevancia'
                    obrarelevancia = ObraRelevancia.objects.get(pk=int(encrypt(request.GET['id'])))

                    form = PostulacionObraRelevanciaForm(
                        initial={
                            'tipo': obrarelevancia.tipo,
                            'titulolibro': obrarelevancia.titulolibro,
                            'titulocapitulo': obrarelevancia.titulocapitulo,
                            'isbn': obrarelevancia.isbn,
                            'aniopublicacion': obrarelevancia.aniopublicacion,
                            'editorial': obrarelevancia.editorial,
                            'areaconocimiento': obrarelevancia.areaconocimiento,
                            'subareaconocimiento': obrarelevancia.subareaconocimiento,
                            'subareaespecificaconocimiento': obrarelevancia.subareaespecificaconocimiento,
                            'lineainvestigacion': obrarelevancia.lineainvestigacion
                        }
                    )

                    form.editar(obrarelevancia)
                    data['form'] = form
                    data['id'] = request.GET['id']
                    data['anioactual'] = datetime.now().year
                    data['participantes'] = participantes = obrarelevancia.participantes()
                    data['totalparticipantes'] = participantes.count()
                    data['convocatoria'] = obrarelevancia.convocatoria

                    return render(request, "pro_obrarelevancia/editpostulacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'buscarpersona':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")

                    if len(s) == 1:
                        personas = Persona.objects.filter(Q(apellido1__icontains=s[0])
                                                        | Q(apellido2__icontains=s[0])
                                                        | Q(cedula__icontains=s[0])
                                                        | Q(ruc__icontains=s[0])
                                                        | Q(pasaporte__icontains=s[0]),
                                                        status=True,).order_by('apellido1', 'apellido2', 'nombres')
                    else:
                        personas = Persona.objects.filter(apellido1__icontains=s[0],
                                                           apellido2__icontains=s[1],
                                                           status=True).order_by('apellido1', 'apellido2', 'nombres')

                    data = {"result": "ok", "results": [{"id": persona.id, "name": str(persona.nombre_completo_inverso()), "identificacion": persona.identificacion(), "idpersona": persona.id, "idperfil": 0} for persona in personas]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'postulacionesevaluacion':
                try:
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), '&action=' + action
                    idc, ids = request.GET.get('idc', ''), request.GET.get('id', '')
                    tipoevaluacion = request.GET['tipoeval']

                    url_vars += '&idc=' + idc + '&tipoeval=' + tipoevaluacion

                    data['convocatoria'] = convocatoria = ConvocatoriaObraRelevancia.objects.get(pk=int(encrypt(idc)))

                    if ids:
                        filtro = filtro & (Q(pk=int(encrypt(ids))))
                        url_vars += '&ids=' + ids
                    else:
                        filtro = filtro & (Q(convocatoria=convocatoria) &
                                           Q(obrarelevanciaevaluador__persona=persona) &
                                           Q(obrarelevanciaevaluador__tipo=tipoevaluacion) &
                                           Q(obrarelevanciaevaluador__status=True)
                                           )

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

                    postulaciones = ObraRelevancia.objects.filter(filtro).order_by('-fecha_creacion')

                    paging = MiPaginador(postulaciones, 25)
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
                    data['postulaciones'] = page.object_list
                    data['tipoevaluacion'] = int(tipoevaluacion)
                    data['periodoevaluacionvigente'] = convocatoria.evaluacion_interna_abierta() if int(tipoevaluacion) == 1 else convocatoria.evaluacion_externa_abierta()
                    data['title'] = u'Evaluación Interna Obras de Relevancia' if int(tipoevaluacion) == 1 else u'Evaluación Externa Obras de Relevancia'

                    return render(request, "pro_obrarelevancia/postulacionesevaluacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'addevaluacioninterna':
                try:
                    data['title'] = u'Agregar Evaluación Interna de Obra de Relevancia'
                    data['obrarelevancia'] = obrarelevancia = ObraRelevancia.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['participantes'] = obrarelevancia.participantes()
                    data['documentos'] = documentos = obrarelevancia.evidencias()
                    data['primerdocumento'] = documentos[0]
                    data['rubricas'] = obrarelevancia.convocatoria.rubricas_evaluacion()
                    data['titulos'] = persona.mis_titulaciones().filter(titulo__nivel__nivel__in=[3, 4, 5]).order_by('-titulo__nivel__nivel')
                    data['tipoevaluacion'] = 1
                    return render(request, "pro_obrarelevancia/addevaluacioninterna.html", data)
                except Exception as ex:
                    pass

            elif action == 'editevaluacioninterna':
                try:
                    data['title'] = u'Editar Evaluación Interna de Obra de Relevancia'
                    evaluacion = EvaluacionObraRelevancia.objects.get(pk=int(encrypt(request.GET['ide'])))
                    data['evaluacion'] = evaluacion
                    data['obrarelevancia'] = obrarelevancia = evaluacion.obrarelevancia
                    data['participantes'] = obrarelevancia.participantes()
                    data['documentos'] = documentos = obrarelevancia.evidencias()
                    data['primerdocumento'] = documentos[0]
                    data['rubricas'] = evaluacion.detalle_rubricas()
                    data['titulos'] = persona.mis_titulaciones().filter(titulo__nivel__nivel__in=[3, 4, 5]).order_by('-titulo__nivel__nivel')
                    data['areasconocimiento'] = AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True).order_by('nombre')
                    data['tipoevaluacion'] = 1
                    return render(request, "pro_obrarelevancia/editevaluacioninterna.html", data)
                except Exception as ex:
                    pass

            elif action == 'firmaractaevaluacion':
                try:
                    evaluacion = EvaluacionObraRelevancia.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Firmar Acta de Evaluación {} de Obra de Relevancia'.format('Interna' if evaluacion.tipo == 1 else 'Externa')
                    data['solicitud'] = evaluacion
                    data['iddoc'] = evaluacion.id  # ID del documento a firmar
                    data['idper'] = evaluacion.evaluador.id  # ID de la persona que firma
                    data['tipofirma'] = 'SOL'
                    data['mensaje'] = "Firma de Acta de Evaluación {} de obra de relevancia del tipo <b>{}</b> para el profesor <b>{}</b>".format('Interna' if evaluacion.tipo == 1 else 'Externa', evaluacion.obrarelevancia.get_tipo_display(), evaluacion.obrarelevancia.profesor.persona.nombre_completo_inverso())
                    data['accionfirma'] = action

                    template = get_template("pro_becadocente/firmardocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'formacionacademica':
                try:
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), '&action=' + action
                    id = request.GET.get('id', '')

                    if id:
                        filtro = filtro & (Q(pk=int(encrypt(id))))
                        url_vars += '&id=' + id
                    else:
                        filtro = filtro & (Q(persona=persona) &
                                           Q(titulo__nivel__nivel__in=[3, 4, 5])
                                           )
                    if search:
                        data['s'] = search
                        filtro = filtro & (Q(titulo__nombre__icontains=search))
                        url_vars += '&s=' + search

                    titulos = Titulacion.objects.filter(filtro).order_by('-fechaobtencion')

                    paging = MiPaginador(titulos, 25)
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
                    data['titulos'] = page.object_list
                    data['title'] = u'Formación Académica del Evaluador Externo'

                    return render(request, "pro_obrarelevancia/formacionacademica.html", data)
                except Exception as ex:
                    pass

            elif action == 'addformacion':
                try:
                    data['title'] = u'Agregar Formación Académica'
                    data['titulos'] = Titulo.objects.filter(status=True, nivel__nivel__in=[3, 4, 5]).order_by('nombre')
                    data['universidades'] = InstitucionEducacionSuperior.objects.filter(status=True).order_by('nombre')
                    data['paises'] = Pais.objects.filter(status=True).order_by('nombre')
                    data['fecha'] = datetime.now().date()

                    template = get_template("pro_obrarelevancia/addformacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editformacion':
                try:
                    data['title'] = u'Editar Formación Académica'
                    data['titulacion'] = Titulacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['titulos'] = Titulo.objects.filter(status=True, nivel__nivel__in=[3, 4, 5]).order_by('nombre')
                    data['universidades'] = InstitucionEducacionSuperior.objects.filter(status=True).order_by('nombre')
                    data['paises'] = Pais.objects.filter(status=True).order_by('nombre')
                    data['fecha'] = datetime.now().date()

                    template = get_template("pro_obrarelevancia/editformacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addevaluacionexterna':
                try:
                    data['title'] = u'Agregar Evaluación Externa de Obra de Relevancia'
                    data['obrarelevancia'] = obrarelevancia = ObraRelevancia.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['participantes'] = obrarelevancia.participantes()
                    data['documentos'] = documentos = obrarelevancia.evidencias()
                    data['primerdocumento'] = documentos[0]
                    data['rubricas'] = obrarelevancia.convocatoria.rubricas_evaluacion()

                    if not persona.mis_titulaciones().filter(titulo__nivel__nivel__in=[3, 4, 5]).exists():
                        data['titulos'] = Titulo.objects.filter(status=True, nivel__nivel__in=[3, 4, 5]).order_by('nombre')
                        data['universidades'] = InstitucionEducacionSuperior.objects.filter(status=True).order_by('nombre')
                        data['paises'] = Pais.objects.filter(status=True).order_by('nombre')
                        data['fecha'] = datetime.now().date()

                    data['titulacion'] = persona.mis_titulaciones().filter(titulo__nivel__nivel__in=[3, 4, 5]).order_by('-titulo__nivel__nivel')[0] if persona.mis_titulaciones().filter(titulo__nivel__nivel__in=[3, 4, 5]).exists() else None

                    # data['titulos2'] = persona.mis_titulaciones().filter(titulo__nivel__nivel__in=[3, 4, 5]).order_by('-titulo__nivel__nivel')
                    # data['areasconocimiento'] = AreaConocimientoTitulacion.objects.filter(status=True, tipo=1, vigente=True).order_by('nombre')
                    data['tipoevaluacion'] = 2
                    return render(request, "pro_obrarelevancia/addevaluacionexterna.html", data)
                except Exception as ex:
                    pass

            elif action == 'editevaluacionexterna':
                try:
                    data['title'] = u'Editar Evaluación Externa de Obra de Relevancia'
                    evaluacion = EvaluacionObraRelevancia.objects.get(pk=int(encrypt(request.GET['ide'])))
                    data['evaluacion'] = evaluacion
                    data['obrarelevancia'] = obrarelevancia = evaluacion.obrarelevancia
                    data['participantes'] = obrarelevancia.participantes()
                    data['documentos'] = documentos = obrarelevancia.evidencias()
                    data['primerdocumento'] = documentos[0]
                    data['rubricas'] = evaluacion.detalle_rubricas()

                    actagenerada = persona.tiene_actas_evaluacion_obrarelevancia_generadas()
                    if evaluacion.estado == 2:
                        actagenerada = False

                    if not actagenerada:
                        data['titulos'] = Titulo.objects.filter(status=True, nivel__nivel__in=[3, 4, 5]).order_by('nombre')
                        data['universidades'] = InstitucionEducacionSuperior.objects.filter(status=True).order_by('nombre')
                        data['paises'] = Pais.objects.filter(status=True).order_by('nombre')

                    data['titulacion'] = evaluacion.titulo
                    data['actagenerada'] = actagenerada
                    data['tipoevaluacion'] = 2
                    return render(request, "pro_obrarelevancia/editevaluacionexterna.html", data)
                except Exception as ex:
                    pass

            elif action == 'subiracta':
                try:
                    data['title'] = u'Subir Acta de Evaluación Firmada (App Externa)'
                    data['evaluacion'] = EvaluacionObraRelevancia.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['origen'] = 'evaluador'

                    template = get_template("adm_obrarelevancia/subiracta.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            try:
                search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
                convocatorias = convocatoriasevalinterna = convocatoriasevalexterna = None

                if es_profesor:
                    convocatorias = ConvocatoriaObraRelevancia.objects.filter(filtro).order_by('-iniciopos', '-finpos')
                if es_evaluador_interno:
                    convocatoriasevalinterna = ConvocatoriaObraRelevancia.objects.filter(filtro, obrarelevancia__obrarelevanciaevaluador__persona=persona, obrarelevancia__obrarelevanciaevaluador__tipo=1, obrarelevancia__obrarelevanciaevaluador__status=True).distinct().order_by('-iniciopos', '-finpos')
                else:
                    convocatoriasevalexterna = ConvocatoriaObraRelevancia.objects.filter(filtro, obrarelevancia__obrarelevanciaevaluador__persona=persona, obrarelevancia__obrarelevanciaevaluador__tipo=2, obrarelevancia__obrarelevanciaevaluador__status=True).distinct().order_by('-iniciopos', '-finpos')

                data['convocatorias'] = convocatorias
                data['convocatoriasevalinterna'] = convocatoriasevalinterna
                data['convocatoriasevalexterna'] = convocatoriasevalexterna
                data['title'] = u'Convocatorias para Obras de Relevancia'
                data['enlaceatras'] = "/pro_investigacion?action=convocatorias"
                return render(request, "pro_obrarelevancia/view.html", data)
            except Exception as ex:
                pass
