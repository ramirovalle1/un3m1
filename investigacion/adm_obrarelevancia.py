# -*- coding: UTF-8 -*-
import io
import json
import os
from math import ceil

import PyPDF2
from datetime import time, datetime
from decimal import Decimal

import requests
import xlsxwriter
from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
import time as pausaparaemail
from xlwt import easyxf, XFStyle, Workbook
import random
from decorators import secure_module
from investigacion.forms import GrupoInvestigacionForm, FinanciamientoPonenciaForm, EvaluadorObraRelevanciaForm, ConvocatoriaObraRelevanciaForm
from investigacion.funciones import FORMATOS_CELDAS_EXCEL
from investigacion.models import GrupoInvestigacion, FUNCION_INTEGRANTE_GRUPO_INVESTIGACION, GrupoInvestigacionIntegrante, ConvocatoriaObraRelevancia, ObraRelevancia, ObraRelevanciaRecorrido, ObraRelevanciaEvaluador, EvaluacionObraRelevancia, RubricaObraRelevancia, RubricaObraRelevanciaConvocatoria
from sagest.commonviews import obtener_estado_solicitud
from settings import SITE_STORAGE
from sga.commonviews import adduserdata
from sga.forms import PlanificarPonenciasForm
from sga.funciones import MiPaginador, log, variable_valor, \
    convertir_fecha, remover_caracteres_tildes_unicode, cuenta_email_disponible, generar_nombre, email_valido, \
    validar_archivo, null_to_decimal, cuenta_email_disponible_para_envio, fechaletra_corta, fecha_letra_rango
from sga.funcionesxhtml2pdf import convert_html_to_pdf
from sga.models import CUENTAS_CORREOS, Persona, PlanificarPonencias, ConvocatoriaPonencia, CriterioPonencia, PlanificarPonenciasCriterio, PlanificarPonenciasRecorrido, MESES_CHOICES, Matricula
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

    if not es_administrativo:
        return HttpResponseRedirect("/?info=El Módulo está disponible para administrativos.")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addconvocatoria':
            try:
                f = ConvocatoriaObraRelevanciaForm(request.POST, request.FILES)

                # Consulto las rúbricas de evaluación
                rubricas = RubricaObraRelevancia.objects.filter(status=True, vigente=True).order_by('numero')

                if not rubricas:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No existen rúbricas de evaluación para la convocatoria", "showSwal": "True", "swalType": "warning"})

                # Validar los archivos
                if 'archivo' in request.FILES:
                    archivo = request.FILES['archivo']
                    descripcionarchivo = 'Convocatoria'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocga' in request.FILES:
                    archivo = request.FILES['archivocga']
                    descripcionarchivo = 'Resolución CGA'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    if not ConvocatoriaObraRelevancia.objects.filter(status=True, descripcion=f.cleaned_data['descripcion'].strip().upper()).exists():
                        if f.cleaned_data['finpos'] <= f.cleaned_data['iniciopos']:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de postulación debe ser mayor a la fecha de inicio de postulación ", "showSwal": "True", "swalType": "warning"})

                        if f.cleaned_data['finevalint'] <= f.cleaned_data['inicioevalint']:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de evaluación interna debe ser mayor a la fecha de inicio de evaluación interna", "showSwal": "True", "swalType": "warning"})

                        if f.cleaned_data['finevalext'] <= f.cleaned_data['inicioevalext']:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de evaluación externa debe ser mayor a la fecha de inicio de evaluación externa", "showSwal": "True", "swalType": "warning"})

                        # Obtengo estado PUBLICADO
                        estado = obtener_estado_solicitud(16, 2)

                        # Guardo la convocatoria
                        convocatoria = ConvocatoriaObraRelevancia(
                            descripcion=f.cleaned_data['descripcion'].strip().upper(),
                            iniciopos=f.cleaned_data['iniciopos'],
                            finpos=f.cleaned_data['finpos'],
                            inicioevalint=f.cleaned_data['inicioevalint'],
                            finevalint=f.cleaned_data['finevalint'],
                            inicioevalext=f.cleaned_data['inicioevalext'],
                            finevalext=f.cleaned_data['finevalext'],
                            publicada=True,
                            estado=estado
                        )
                        convocatoria.save(request)

                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("convocatoria", newfile._name)
                            convocatoria.archivo = newfile

                        if 'archivocga' in request.FILES:
                            newfile = request.FILES['archivocga']
                            newfile._name = generar_nombre("resolucioncga", newfile._name)
                            convocatoria.archivocga = newfile

                        convocatoria.save(request)

                        # Guardo las rúbricas de evaluación para la convocatoria
                        secuencia = 1
                        for rubrica in rubricas:
                            rubricaconvocatoria = RubricaObraRelevanciaConvocatoria(
                                convocatoria=convocatoria,
                                rubrica=rubrica,
                                secuencia=secuencia
                            )
                            rubricaconvocatoria.save(request)

                            secuencia += 1

                        log(u'%s agregó convocatoria para obras de relevancia: %s' % (persona, convocatoria), request, "add")
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La convocatoria para obras de relevancia ya ha sido ingresada", "showSwal": "True", "swalType": "warning"})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in f.errors.items()])
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editconvocatoria':
            try:
                f = ConvocatoriaObraRelevanciaForm(request.POST, request.FILES)

                # Validar los archivos
                if 'archivo' in request.FILES:
                    archivo = request.FILES['archivo']
                    descripcionarchivo = 'Convocatoria'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if 'archivocga' in request.FILES:
                    archivo = request.FILES['archivocga']
                    descripcionarchivo = 'Resolución CGA'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    if not ConvocatoriaObraRelevancia.objects.filter(status=True, descripcion=f.cleaned_data['descripcion'].strip().upper()).exclude(pk=int(encrypt(request.POST['id']))).exists():
                        # Consultar la convocatoria
                        convocatoria = ConvocatoriaObraRelevancia.objects.get(pk=int(encrypt(request.POST['id'])))

                        if f.cleaned_data['finpos'] <= f.cleaned_data['iniciopos']:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de postulación debe ser mayor a la fecha de inicio de postulación ", "showSwal": "True", "swalType": "warning"})

                        if f.cleaned_data['finevalint'] <= f.cleaned_data['inicioevalint']:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de evaluación interna debe ser mayor a la fecha de inicio de evaluación interna", "showSwal": "True", "swalType": "warning"})

                        if f.cleaned_data['finevalext'] <= f.cleaned_data['inicioevalext']:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de evaluación externa debe ser mayor a la fecha de inicio de evaluación externa", "showSwal": "True", "swalType": "warning"})

                        # Actualizo la convocatoria
                        convocatoria.descripcion = f.cleaned_data['descripcion'].strip().upper()
                        convocatoria.iniciopos = f.cleaned_data['iniciopos']
                        convocatoria.finpos = f.cleaned_data['finpos']
                        convocatoria.inicioevalint = f.cleaned_data['inicioevalint']
                        convocatoria.finevalint = f.cleaned_data['finevalint']
                        convocatoria.inicioevalext = f.cleaned_data['inicioevalext']
                        convocatoria.finevalext = f.cleaned_data['finevalext']

                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("convocatoria", newfile._name)
                            convocatoria.archivo = newfile

                        if 'archivocga' in request.FILES:
                            newfile = request.FILES['archivocga']
                            newfile._name = generar_nombre("resolucioncga", newfile._name)
                            convocatoria.archivocga = newfile

                        convocatoria.save(request)

                        log(u'%s editó convocatoria para obras de relevancia: %s' % (persona, convocatoria), request, "edit")
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La convocatoria para obras de relevancia ya ha sido ingresada", "showSwal": "True", "swalType": "warning"})
                else:
                    msg = ",".join([k + ': ' + v[0] for k, v in f.errors.items()])
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'habilitaredicion':
            try:
                # Consulto la postulación
                obrarelevancia = ObraRelevancia.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que tenga estado SOLICITADO
                if not obrarelevancia.estado.valor == 2:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el Registro porque no tiene estado SOLICITADO", "showSwal": "True", "swalType": "warning"})

                # Obtengo estado EN EDICIÓN
                estado = obtener_estado_solicitud(15, 1)

                # Actualizo la postulación
                obrarelevancia.estado = estado
                obrarelevancia.observacion = ""
                obrarelevancia.save(request)

                # Guardo el recorrido
                recorrido = ObraRelevanciaRecorrido(
                    obrarelevancia=obrarelevancia,
                    fecha=datetime.now().date(),
                    persona=persona,
                    observacion='POSTULACIÓN EN EDICIÓN',
                    estado=estado
                )
                recorrido.save(request)

                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, ..., sga7@unemi.edu.ec

                # E-mail del destinatario
                lista_email_envio = obrarelevancia.profesor.persona.lista_emails_envio()
                # lista_email_envio = ['isaltosm@unemi.edu.ec']
                lista_email_cco = []
                lista_archivos_adjuntos = []

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                asuntoemail = "Habilitación Edición Registro de Postulación a Obra de Relevancia"
                titulo = "Postulación Obra de Relevancia"
                tiponotificacion = "HABEDI"

                send_html_mail(asuntoemail,
                               "emails/postulacionobrarelevancia.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'saludo': 'Estimada' if obrarelevancia.profesor.persona.sexo_id == 1 else 'Estimado',
                                'nombrepersona': obrarelevancia.profesor.persona.nombre_completo_inverso(),
                                'obrarelevancia': obrarelevancia
                                },
                               lista_email_envio,
                               lista_email_cco,
                               lista_archivos_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                log(u'%s habilitó edición de postulación para obra de relevancia: %s' % (persona, obrarelevancia), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'asignarevaluador':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Obtengo los valores de los arreglos
                evalinternos = json.loads(request.POST['lista_items1'])
                evalinternoseliminados = json.loads(request.POST['lista_items3']) if 'lista_items3' in request.POST else []
                evalinternosnotificar = json.loads(request.POST['lista_items5']) if 'lista_items5' in request.POST else []
                evalexternos = json.loads(request.POST['lista_items2']) if 'lista_items2' in request.POST else []
                evalexternoseliminados = json.loads(request.POST['lista_items4']) if 'lista_items4' in request.POST else []
                evalexternosnotificar = json.loads(request.POST['lista_items6']) if 'lista_items6' in request.POST else []

                # Consulto la obra de relevancia
                obrarelevancia = ObraRelevancia.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verificar que no sean integrantes de la obra de relevancia
                if obrarelevancia.obrarelevanciaparticipante_set.filter(status=True, tipo=1, persona__id__in=[item['idpe'] for item in evalinternos]).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"Los evaluadores internos no deben ser participantes de la obra de relevancia", "showSwal": "True", "swalType": "warning"})

                if evalexternos:
                    if obrarelevancia.obrarelevanciaparticipante_set.filter(status=True, tipo=2, persona__id__in=[item['idpe'] for item in evalexternos]).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"Los evaluadores externos no deben ser participantes de la obra de relevancia", "showSwal": "True", "swalType": "warning"})

                registro_nuevo = not obrarelevancia.tiene_asignado_evaluadores()

                # Lista de los evaluadores que deben ser notificados por correo
                lista_evaluadores = []

                # Guardo los evaluadores internos
                for evaluador, notificar in zip(evalinternos, evalinternosnotificar):
                    personaevaluador = Persona.objects.get(pk=int(evaluador['idpe']))

                    # Nuevo evaluador interno
                    if int(evaluador['idreg']) == 0:
                        # Guardo evaluador
                        evaluadorinterno = ObraRelevanciaEvaluador(
                            obrarelevancia=obrarelevancia,
                            tipo=1,
                            persona=personaevaluador,
                            notificado=notificar['valor']
                        )
                        evaluadorinterno.save(request)

                        # Para enviar el e-mail al evaluador
                        if notificar['valor']:
                            evaluador = {
                                "nombre": personaevaluador.nombre_completo_inverso(),
                                "saludo": 'Estimada' if personaevaluador.sexo_id == 1 else 'Estimado',
                                "direccionemail": personaevaluador.lista_emails_envio(),
                                "inicioeval": obrarelevancia.convocatoria.inicioevalint,
                                "fineval": obrarelevancia.convocatoria.finevalint,
                                "tipo": "EVALUADOR INTERNO",
                                "usuario": "",
                                "contrasenia": ""
                            }
                            lista_evaluadores.append(evaluador)
                    else:
                        # Notificar por e-mail a los no notificados
                        if notificar['valor']:
                            evaluadorobra = ObraRelevanciaEvaluador.objects.get(pk=int(evaluador['idreg']))
                            if evaluadorobra.notificado is False:
                                evaluadorobra.notificado = True
                                evaluadorobra.save(request)

                                evaluador = {
                                    "nombre": personaevaluador.nombre_completo_inverso(),
                                    "saludo": 'Estimada' if personaevaluador.sexo_id == 1 else 'Estimado',
                                    "direccionemail": personaevaluador.lista_emails_envio(),
                                    "inicioeval": obrarelevancia.convocatoria.inicioevalint,
                                    "fineval": obrarelevancia.convocatoria.finevalint,
                                    "tipo": "EVALUADOR INTERNO",
                                    "usuario": "",
                                    "contrasenia": ""
                                }
                                lista_evaluadores.append(evaluador)

                # Elimino los que se borraron del detalle
                if evalinternoseliminados:
                    for evaluador in evalinternoseliminados:
                        evaluadorinterno = ObraRelevanciaEvaluador.objects.get(pk=int(evaluador['idreg']))
                        evaluadorinterno.status = False
                        evaluadorinterno.save(request)

                # Guardo los evaluadores externos
                for evaluador, notificar in zip(evalexternos, evalexternosnotificar):
                    personaevaluador = Persona.objects.get(pk=int(evaluador['idpe']))

                    # Nuevo evaluador externo
                    if int(evaluador['idreg']) == 0:
                        # Guardo evaluador
                        evaluadorexterno = ObraRelevanciaEvaluador(
                            obrarelevancia=obrarelevancia,
                            tipo=2,
                            persona=personaevaluador,
                            notificado=notificar['valor']
                        )
                        evaluadorexterno.save(request)

                        # Consulto usuario de la persona
                        usuarioevaluador = personaevaluador.usuario

                        # En caso de no tener asignado el grupo 335: INVESTIGACIÓN EVALUADOR EXTERNO, se le debe asignar
                        if not usuarioevaluador.groups.filter(id=335):
                            from django.contrib.auth.models import Group
                            grupo = Group.objects.get(pk=335)
                            grupo.user_set.add(usuarioevaluador)
                            grupo.save()

                        # Para enviar el e-mail al evaluador
                        if notificar['valor']:
                            evaluador = {
                                "nombre": personaevaluador.nombre_completo_inverso(),
                                "saludo": 'Estimada' if personaevaluador.sexo_id == 1 else 'Estimado',
                                "direccionemail": personaevaluador.lista_emails_envio(),
                                "inicioeval": obrarelevancia.convocatoria.inicioevalext,
                                "fineval": obrarelevancia.convocatoria.finevalext,
                                "tipo": "EVALUADOR EXTERNO",
                                "usuario": personaevaluador.usuario.username,
                                "contrasenia": personaevaluador.identificacion() + "*" + str(personaevaluador.nacimiento)[0:4]
                            }
                            lista_evaluadores.append(evaluador)
                    else:
                        # Notificar por e-mail a los no notificados
                        if notificar['valor']:
                            evaluadorobra = ObraRelevanciaEvaluador.objects.get(pk=int(evaluador['idreg']))
                            if evaluadorobra.notificado is False:
                                evaluadorobra.notificado = True
                                evaluadorobra.save(request)

                                evaluador = {
                                    "nombre": personaevaluador.nombre_completo_inverso(),
                                    "saludo": 'Estimada' if personaevaluador.sexo_id == 1 else 'Estimado',
                                    "direccionemail": personaevaluador.lista_emails_envio(),
                                    "inicioeval": obrarelevancia.convocatoria.inicioevalext,
                                    "fineval": obrarelevancia.convocatoria.finevalext,
                                    "tipo": "EVALUADOR EXTERNO",
                                    "usuario": personaevaluador.usuario.username,
                                    "contrasenia": personaevaluador.identificacion() + "*" + str(personaevaluador.nacimiento)[0:4]
                                }
                                lista_evaluadores.append(evaluador)

                # Elimino los que se borraron del detalle
                if evalexternoseliminados:
                    for evaluador in evalexternoseliminados:
                        evaluadorexterno = ObraRelevanciaEvaluador.objects.get(pk=int(evaluador['idreg']))
                        evaluadorexterno.status = False
                        evaluadorexterno.save(request)

                # Para guardar recorrido
                if registro_nuevo:
                    # Actualizo el estado de la obra a EVALUADORES ASIGNADOS
                    mensaje = "Registro guardado con éxito"
                    estado = obtener_estado_solicitud(15, 6)
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

                    log(u'% agregó evaluadores a obra de relevancia: %s' % (persona, obrarelevancia), request, "add")
                else:
                    mensaje = "Registro actualizado con éxito"
                    log(u'%s editó evaluadores de obra de relevancia: %s' % (persona, obrarelevancia), request, "edit")

                # Notificar por e-mail
                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [29]  # investigacion@unemi.edu.ec

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                for evaluador in lista_evaluadores:
                    # lista_email_envio = ['ivan_saltos_medina@hotmail.com']
                    lista_email_envio = evaluador['direccionemail']

                    tituloemail = "Designación Evaluador de Obra de Relevancia"
                    tiponotificacion = "EVALPROPASIG"

                    lista_archivos_adjuntos = []
                    # lista_email_cco = []
                    lista_email_cco = ['ivan_saltos_medina@hotmail.com']
                    titulo = "Obras de Relevancia"

                    send_html_mail(tituloemail,
                                   "emails/postulacionobrarelevancia.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'titulo': titulo,
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'tiponotificacion': tiponotificacion,
                                    'saludo': evaluador['saludo'],
                                    'nombrepersona': evaluador['nombre'],
                                    'obrarelevancia': obrarelevancia,
                                    'tipoevaluador': evaluador['tipo'],
                                    'inicioeval': evaluador['inicioeval'],
                                    'fineval': evaluador['fineval'],
                                    'usuario': evaluador['usuario'],
                                    'contrasenia': evaluador['contrasenia'],
                                    'enlace': 'http://127.0.0.1:8000/pro_obrarelevancia' if variable_valor('IS_DEBUG') else 'https://sga.unemi.edu.ec/pro_obrarelevancia'
                                    },
                                   lista_email_envio,  # Destinatarioa
                                   lista_email_cco,  # Copia oculta
                                   lista_archivos_adjuntos,  # Adjunto(s)
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": mensaje, "showSwal": True})
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
                evaluacion.archivofirmado = archivo
                evaluacion.estado = 3
                evaluacion.save(request)

                log(u'%s subió acta de evaluación firmada: %s' % (persona, evaluacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

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

        elif action == 'cerrarevaluacion':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la evaluacion
                evaluacion = EvaluacionObraRelevancia.objects.get(pk=int(encrypt(request.POST['id'])))
                obrarelevancia = evaluacion.obrarelevancia
                notificardocente = False

                # Verificar que no haya sido cerrada
                if evaluacion.estado == 6:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La evaluación ya ha sido cerrada anteriormente", "showSwal": "True", "swalType": "warning"})

                # Obtengo los valores de los campos del formulario
                estado = int(request.POST['estado'])
                observacion = request.POST['observacion'].strip().upper() if 'observacion' in request.POST else ''

                # Actualizar la evaluación
                evaluacion.revisor = persona
                evaluacion.fecharevision = datetime.now()
                evaluacion.revisado = True
                evaluacion.observacionrevision = observacion
                evaluacion.estado = estado
                evaluacion.save(request)

                # Si estado de evaluación es CERRADA
                if estado == 6:
                    # Si las evaluaciones están cerradas, incluyendo la actual
                    if obrarelevancia.evaluaciones_cerradas():
                        notificardocente = True
                        esuperada = not obrarelevancia.evaluaciones().filter(cumplerequisito=False).exists()

                        # Obtener estado E. SUPERADA o NO SUPERADA
                        estadoobra = obtener_estado_solicitud(15, 8) if esuperada else obtener_estado_solicitud(15, 9)

                        # Actulizar obra de relevancia
                        obrarelevancia.estado = estadoobra
                        obrarelevancia.save(request)

                        # Guardo el recorrido
                        recorrido = ObraRelevanciaRecorrido(
                            obrarelevancia=obrarelevancia,
                            fecha=datetime.now().date(),
                            persona=persona,
                            observacion=estadoobra.observacion,
                            estado=estadoobra
                        )
                        recorrido.save(request)

                        # En caso de no superar Evaluacianes asignar estado RECHAZADO
                        if not esuperada:
                            # Obtener estado RECHAZADO
                            estadoobra = obtener_estado_solicitud(15, 11)

                            # Actulizar obra de relevancia
                            obrarelevancia.estado = estadoobra
                            obrarelevancia.save(request)

                            # Guardo el recorrido
                            recorrido = ObraRelevanciaRecorrido(
                                obrarelevancia=obrarelevancia,
                                fecha=datetime.now().date(),
                                persona=persona,
                                observacion=estadoobra.observacion,
                                estado=estadoobra
                            )
                            recorrido.save(request)
                        else:
                            # En caso de superar evalución asignar estado ACEPTADO PARA IR A CGA
                            estadoobra = obtener_estado_solicitud(15, 10)

                            # Actulizar obra de relevancia
                            obrarelevancia.estado = estadoobra
                            obrarelevancia.save(request)

                            # Guardo el recorrido
                            recorrido = ObraRelevanciaRecorrido(
                                obrarelevancia=obrarelevancia,
                                fecha=datetime.now().date(),
                                persona=persona,
                                observacion=estadoobra.observacion,
                                estado=estadoobra
                            )
                            recorrido.save(request)


                # Notificar por e-mail al evaluador
                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [29]  # investigacion@unemi.edu.ec

                # Destinatarios
                personaevaluador = evaluacion.evaluador
                lista_email_envio = personaevaluador.lista_emails_envio()
                # lista_email_envio = ['ivan_saltos_medina@hotmail.com']
                lista_email_cco = []
                lista_archivos_adjuntos = []

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                # CERRADA
                if estado == 6:
                    if evaluacion.tipo == 1:
                        tiponotificacion = "EVALINTCERR"
                        tituloemail = "Evaluación Interna de Obra de Relevancia Cerrada"
                    else:
                        tiponotificacion = "EVALEXTCERR"
                        tituloemail = "Evaluación Externa de Obra de Relevancia Cerrada"
                else:
                    # NOVEDAD
                    if evaluacion.tipo == 1:
                        tiponotificacion = "EVALINTNOV"
                        tituloemail = "Novedades Evaluación Interna de Obra de Relevancia"
                    else:
                        tiponotificacion = "EVALEXTNOV"
                        tituloemail = "Novedades Evaluación Externa de Obra de Relevancia"

                titulo = "Obras de Relevancia"

                send_html_mail(tituloemail,
                               "emails/postulacionobrarelevancia.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'obrarelevancia': obrarelevancia,
                                'saludo': 'Estimada' if personaevaluador.sexo_id == 1 else 'Estimado',
                                'nombrepersona': personaevaluador.nombre_completo_inverso(),
                                'observaciones': observacion
                                },
                               lista_email_envio,  # Destinatarioa
                               lista_email_cco,  # Copia oculta
                               lista_archivos_adjuntos,  # Adjunto(s)
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                # Notificar al docente
                if notificardocente:
                    if obrarelevancia.estado.valor == 8:
                        tiponotificacion = "EVALSUP"
                        tituloemail = "Evaluación de Propuesta de Obra de Relevancia Superada"
                    else:
                        tiponotificacion = "EVALNOSUP"
                        tituloemail = "Evaluación de Propuesta de Obra de Relevancia No Superada"

                    lista_email_envio = obrarelevancia.profesor.persona.lista_emails_envio()
                    # lista_email_envio.append('ivan_saltos_medina@hotmail.com')
                    lista_archivos_adjuntos = []

                    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
                    titulo = "Obras de Relevancia"
                    send_html_mail(tituloemail,
                                   "emails/postulacionobrarelevancia.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'titulo': titulo,
                                    'fecha': fechaenvio,
                                    'hora': horaenvio,
                                    'tiponotificacion': tiponotificacion,
                                    'saludo': 'Estimada' if obrarelevancia.profesor.persona.sexo_id == 1 else 'Estimado',
                                    'nombrepersona': obrarelevancia.profesor.persona.nombre_completo_inverso(),
                                    'observaciones': '',
                                    'obrarelevancia': obrarelevancia
                                    },
                                   lista_email_envio,  # Destinatarioa
                                   lista_email_cco,  # Copia oculta, poner [] para que no me envíe jaja
                                   lista_archivos_adjuntos,  # Adjunto(s)
                                   cuenta=CUENTAS_CORREOS[cuenta][1]
                                   )

                if estado == 6:
                    log(u'%s confirmó evaluación %s para obra de relevancia: %s' % (persona, 'interna' if evaluacion.tipo == 1 else 'externa', evaluacion), request, "edit")
                else:
                    log(u'%s registró novedades para evaluación %s para obra de relevancia: %s' % (persona, 'interna' if evaluacion.tipo == 1 else 'externa', evaluacion), request, "edit")

                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Solicitud incorrecta.", "showSwal": "True", "swalType": "error"})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addconvocatoria':
                try:
                    data['title'] = u'Agregar Convocatoria para Obras de Relevancia'
                    form = ConvocatoriaObraRelevanciaForm()
                    data['form'] = form
                    data['rubricas'] = RubricaObraRelevancia.objects.filter(status=True, vigente=True)
                    return render(request, "adm_obrarelevancia/addconvocatoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'editconvocatoria':
                try:
                    data['title'] = u'Editar Convocatoria para Obras de Relevancia'
                    convocatoria = ConvocatoriaObraRelevancia.objects.get(pk=int(encrypt(request.GET['idc'])))

                    form = ConvocatoriaObraRelevanciaForm(
                        initial={
                            'descripcion': convocatoria.descripcion,
                            'iniciopos': convocatoria.iniciopos,
                            'finpos': convocatoria.finpos,
                            'inicioevalint': convocatoria.inicioevalint,
                            'finevalint': convocatoria.finevalint,
                            'inicioevalext': convocatoria.inicioevalext,
                            'finevalext': convocatoria.finevalext
                        }
                    )

                    data['form'] = form
                    data['id'] = request.GET['idc']
                    data['rubricas'] = convocatoria.rubricas_evaluacion()

                    return render(request, "adm_obrarelevancia/editconvocatoria.html", data)
                except Exception as ex:
                    pass

            elif action == 'postulaciones':
                try:
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), '&action=' + action
                    idc, ids = request.GET.get('idc', ''), request.GET.get('id', '')
                    url_vars += '&idc=' + idc

                    data['convocatoria'] = convocatoria = ConvocatoriaObraRelevancia.objects.get(pk=int(encrypt(idc)))

                    if ids:
                        filtro = filtro & (Q(pk=int(encrypt(ids))))
                        url_vars += '&ids=' + ids
                    else:
                        filtro = filtro & (Q(convocatoria=convocatoria))

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
                    data['title'] = u'Postulaciones para Obras de Relevancia'

                    return render(request, "adm_obrarelevancia/postulaciones.html", data)
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

            elif action == 'reportegeneral':
                try:
                    convocatoria = ConvocatoriaObraRelevancia.objects.get(pk=int(encrypt(request.GET['idc'])))
                    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'postgrado'))

                    nombrearchivo = "POSTULACIONES_OBRAS_RELEVANCIA_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xlsx"

                    # Crea un nuevo archivo de excel y le agrega una hoja
                    workbook = xlsxwriter.Workbook(output_folder + '/' + nombrearchivo)
                    ws = workbook.add_worksheet("Listado")

                    fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])
                    fceldageneral = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdageneral"])
                    fceldageneralcent = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdageneralcent"])
                    ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
                    fceldafechaDMA = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdafechaDMA"])

                    ws.merge_range(0, 0, 0, 14, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo1)
                    ws.merge_range(1, 0, 1, 14, 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADO', ftitulo1)
                    ws.merge_range(2, 0, 2, 14, 'COORDINACIÓN DE INVESTIGACIÓN', ftitulo1)
                    ws.merge_range(3, 0, 3, 14, 'LISTADO GENERAL DE POSTULACIONES A OBRAS DE RELEVANCIA', ftitulo1)
                    ws.merge_range(4, 0, 4, 14, 'CONVOCATORIA: ' + convocatoria.descripcion, ftitulo1)

                    columns = [
                        (u"FECHA", 10),
                        (u"NÚMERO", 10),
                        (u"PROFESOR", 35),
                        (u"TIPO DE OBRA", 13),
                        (u"TÍTULO DEL LIBRO", 40),
                        (u"TÍTULO DEL CAPÍTULO", 40),
                        (u"ISBN", 20),
                        (u"AÑO PUBLICACIÓN", 13),
                        (u"EDITORIAL", 20),
                        (u"ÁREA DE CONOCIMIENTO", 40),
                        (u"SUB-ÁREA DE CONOCIMIENTO", 40),
                        (u"SUB-ÁREA ESPECÍFICA", 40),
                        (u"LÍNEA DE INVESTIGACIÓN", 40),
                        (u"PARTICIPANTES", 30),
                        (u"ESTADO", 15),
                        (u"EVALUADOR INTERNO 1", 35),
                        (u"ÁREA DE CONOCIMIENTO", 40),
                        (u"APROBADO", 15),
                        (u"EVALUADOR INTERNO 2", 35),
                        (u"ÁREA DE CONOCIMIENTO", 40),
                        (u"APROBADO", 15),
                        (u"EVALUADOR EXTERNO 1", 35),
                        (u"ÁREA DE CONOCIMIENTO", 40),
                        (u"APROBADO", 15),
                        (u"APROBACIÓN FINAL", 20)
                    ]

                    row_num = 6
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                        ws.set_column(col_num, col_num, columns[col_num][1])

                    row_num = 7

                    postulaciones = ObraRelevancia.objects.filter(status=True, convocatoria=convocatoria).order_by('id')

                    for postulacion in postulaciones:
                        ws.write(row_num, 0, postulacion.fecha_creacion, fceldafechaDMA)
                        ws.write(row_num, 1, str(postulacion.id).zfill(6), fceldageneralcent)
                        ws.write(row_num, 2, postulacion.profesor.persona.nombre_completo_inverso(), fceldageneral)
                        ws.write(row_num, 3, postulacion.get_tipo_display(), fceldageneralcent)
                        ws.write(row_num, 4, postulacion.titulolibro, fceldageneral)
                        ws.write(row_num, 5, postulacion.titulocapitulo, fceldageneral)
                        ws.write(row_num, 6, postulacion.isbn, fceldageneral)
                        ws.write(row_num, 7, postulacion.aniopublicacion, fceldageneral)
                        ws.write(row_num, 8, postulacion.editorial, fceldageneral)
                        ws.write(row_num, 9, postulacion.areaconocimiento.nombre, fceldageneral)
                        ws.write(row_num, 10, postulacion.subareaconocimiento.nombre, fceldageneral)
                        ws.write(row_num, 11, postulacion.subareaespecificaconocimiento.nombre, fceldageneral)
                        ws.write(row_num, 12, postulacion.lineainvestigacion.nombre, fceldageneral)
                        ws.write(row_num, 13, postulacion.listado_participantes_agrupado(), fceldageneral)
                        ws.write(row_num, 14, postulacion.estado.descripcion, fceldageneralcent)

                        if postulacion.evaluaciones_cerradas():
                            col = 15
                            reprobado = False
                            for evaluacion in postulacion.evaluaciones_internas():
                                ws.write(row_num, col, evaluacion.evaluador.nombre_completo_inverso(), fceldageneral)
                                col +=1
                                ws.write(row_num, col, evaluacion.titulo.titulo.areaconocimiento.nombre if evaluacion.titulo.titulo.areaconocimiento else "", fceldageneral)
                                col += 1
                                ws.write(row_num, col, "SI" if evaluacion.cumplerequisito else "NO", fceldageneral)
                                col += 1
                                reprobado = not evaluacion.cumplerequisito

                            for evaluacion in postulacion.evaluaciones_externas():
                                ws.write(row_num, col, evaluacion.evaluador.nombre_completo_inverso(), fceldageneral)
                                col +=1
                                ws.write(row_num, col, evaluacion.titulo.titulo.areaconocimiento.nombre if evaluacion.titulo.titulo.areaconocimiento else "", fceldageneral)
                                col += 1
                                ws.write(row_num, col, "SI" if evaluacion.cumplerequisito else "NO", fceldageneral)
                                col += 1
                                reprobado = not evaluacion.cumplerequisito

                            ws.write(row_num, 24, "ES RELEVANTE" if not reprobado else "NO ES RELEVANTE", fceldageneral)
                        else:
                            for col in range(15, 25):
                                ws.write(row_num, col, "", fceldageneral)

                        row_num += 1


                    workbook.close()

                    ruta = "media/postgrado/" + nombrearchivo
                    return JsonResponse({'result': 'ok', 'archivo': ruta})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar el reporte. [%s]" % msg, "showSwal": "True", "swalType": "error"})

            elif action == 'asignarevaluador':
                try:
                    data['title'] = u'Asignar Evaluadores a Obras de Relevancia'
                    obrarelevancia = ObraRelevancia.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = EvaluadorObraRelevanciaForm(initial={
                        'profesor': obrarelevancia.profesor,
                        'tipo': obrarelevancia.get_tipo_display(),
                        'titulolibro': obrarelevancia.titulolibro,
                        'titulocapitulo': obrarelevancia.titulocapitulo
                    })
                    data['form'] = form
                    data['obrarelevancia'] = obrarelevancia
                    data['convocatoria'] = obrarelevancia.convocatoria
                    data['evaluadoresinternos'] = evaluadores = obrarelevancia.evaluadores_internos()
                    data['totalinternos'] = evaluadores.count()
                    data['evaluadoresexternos'] = evaluadores = obrarelevancia.evaluadores_externos()
                    data['totalexternos'] = evaluadores.count()
                    data['einternascompletas'] = einternascompletas = obrarelevancia.evaluaciones_internas_completas()
                    data['eexternascompletas'] = eexternascompletas = obrarelevancia.evaluaciones_externas_completas()
                    data['evaluacionescompletas'] = einternascompletas and eexternascompletas
                    data['maximointerno'] = 2
                    data['maximoexterno'] = 1

                    return render(request, "adm_obrarelevancia/asignarevaluador.html", data)
                except Exception as ex:
                    pass

            elif action == 'addevaluador':
                try:
                    data['title'] = u'Agregar Evaluador Interno a Propuesta de Obra de Relevancia' if request.GET['tipo'] == 'I' else u'Agregar Evaluador Externo a Propuesta de Obra de Relevancia'
                    data['tipo'] = request.GET['tipo']
                    template = get_template("adm_obrarelevancia/addevaluador.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'evaluaciones':
                try:
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True, estado__in=[2, 3, 5, 6 ,7]), '&action=' + action
                    id, ide = request.GET.get('id', ''), request.GET.get('ide', '')
                    url_vars += '&id=' + id

                    data['obrarelevancia'] = obrarelevancia = ObraRelevancia.objects.get(pk=int(encrypt(id)))

                    if ide:
                        filtro = filtro & (Q(pk=int(encrypt(ide))))
                        url_vars += '&ide=' + ide
                    else:
                        filtro = filtro & (Q(obrarelevancia=obrarelevancia))

                    if search:
                        data['s'] = search
                        ss = search.split(" ")
                        if len(ss) == 1:
                            filtro = filtro & (Q(evaluador__nombres__icontains=search) |
                                               Q(evaluador__apellido1__icontains=search) |
                                               Q(evaluador__apellido2__icontains=search))
                        else:
                            filtro = filtro & (Q(evaluador__apellido1__contains=ss[0]) &
                                               Q(evaluador__apellido2__contains=ss[1]))

                        url_vars += '&s=' + search

                    evaluaciones = EvaluacionObraRelevancia.objects.filter(filtro).order_by('-fecha_creacion')

                    paging = MiPaginador(evaluaciones, 25)
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
                    data['evaluaciones'] = page.object_list
                    data['title'] = u'Evaluaciones de Obra de Relevancia'

                    return render(request, "adm_obrarelevancia/evaluaciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'subiracta':
                try:
                    data['title'] = u'Subir Acta de Evaluación Firmada'
                    data['evaluacion'] = EvaluacionObraRelevancia.objects.get(pk=int(encrypt(request.GET['id'])))

                    template = get_template("adm_obrarelevancia/subiracta.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cerrarevaluacion':
                try:
                    evaluacion = EvaluacionObraRelevancia.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'{} Evaluación de Obra de Relevancia'.format('Cerrar' if evaluacion.estado != 6 else 'Mostrar')
                    data['evaluacion'] = evaluacion
                    data['detalles'] = evaluacion.detalle_rubricas()
                    template = get_template("adm_obrarelevancia/cerrarevaluacion.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            try:
                search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''

                # if search:
                #     data['s'] = search
                #     filtro = filtro & (Q(nombre__unaccent__icontains=search))
                #     url_vars += '&s=' + search
                convocatorias = ConvocatoriaObraRelevancia.objects.filter(filtro).order_by('-iniciopos', '-finpos')

                paging = MiPaginador(convocatorias, 25)
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
                data['convocatorias'] = page.object_list
                data['title'] = u'Convocatorias para Obras de Relevancia'
                data['enlaceatras'] = "/ges_investigacion?action=convocatorias"

                return render(request, "adm_obrarelevancia/view.html", data)
            except Exception as ex:
                pass
