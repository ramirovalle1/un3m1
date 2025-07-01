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
from investigacion.forms import GrupoInvestigacionForm, FinanciamientoPonenciaForm, EvaluadorObraRelevanciaForm, ConvocatoriaObraRelevanciaForm, CronogramavaluacionInvestigacionForm
from investigacion.funciones import FORMATOS_CELDAS_EXCEL
from investigacion.models import GrupoInvestigacion, FUNCION_INTEGRANTE_GRUPO_INVESTIGACION, GrupoInvestigacionIntegrante, ConvocatoriaObraRelevancia, ObraRelevancia, ObraRelevanciaRecorrido, ObraRelevanciaEvaluador, EvaluacionObraRelevancia, RubricaObraRelevancia, RubricaObraRelevanciaConvocatoria, \
    CronogramaEvaluacionInvestigacion, CriterioEvaluacionInvestigacion, PeriodoEvaluacionInvestigacion, PeriodoCronogramaEvaluacionInvestigacion, CriterioCronogramaEvaluacionInvestigacion
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

        if action == 'addcronograma':
            try:
                f = CronogramavaluacionInvestigacionForm(request.POST, request.FILES)

                # Consulto las criterios de evaluación y periodos académicos a evaluar
                criterios = CriterioEvaluacionInvestigacion.objects.filter(status=True, vigente=True).order_by('numero')
                periodosevaluacion = PeriodoEvaluacionInvestigacion.objects.filter(status=True, vigente=True).order_by('-id')

                if not periodosevaluacion:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No existen periodos académicos vigentes para evaluar", "showSwal": "True", "swalType": "warning"})

                if not criterios:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No existen criterios de evaluación", "showSwal": "True", "swalType": "warning"})

                # Validar los archivos
                if 'instructivo' in request.FILES:
                    archivo = request.FILES['instructivo']
                    descripcionarchivo = 'Instructivo'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    if not CronogramaEvaluacionInvestigacion.objects.filter(status=True, descripcion=f.cleaned_data['descripcion'].strip().upper()).exists():
                        if f.cleaned_data['fin'] <= f.cleaned_data['inicio']:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de evaluación debe ser mayor a la fecha de inicio", "showSwal": "True", "swalType": "warning"})

                        inicioperiodo = periodosevaluacion[0].periodo.inicio
                        finperiodo = periodosevaluacion[0].periodo.fin

                        if f.cleaned_data['inicio'] <= finperiodo:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La fecha de inicio de evaluación debe ser mayor a <b>{:%d-%m-%Y}</b>".format(finperiodo), "showSwal": "True", "swalType": "warning"})

                        # Obtener los valores de los detalles del formulario
                        idscriterios = request.POST.getlist('idcriterios[]')  # Todos los códigos de los criterios
                        porcentajes = request.POST.getlist('porcentajes[]')  # Todos los porcentajes de cada criterio

                        # Obtengo estado POR INICIAR
                        estado = obtener_estado_solicitud(20, 1)

                        # Guardo el cronograma
                        cronograma = CronogramaEvaluacionInvestigacion(
                            descripcion=f.cleaned_data['descripcion'].strip().upper(),
                            inicio=f.cleaned_data['inicio'],
                            fin=f.cleaned_data['fin'],
                            iniciopleceval=inicioperiodo,
                            finpleceval=finperiodo,
                            estado=estado
                        )
                        cronograma.save(request)

                        if 'instructivo' in request.FILES:
                            newfile = request.FILES['instructivo']
                            newfile._name = generar_nombre("instructivo", newfile._name)
                            cronograma.instructivo = newfile

                        cronograma.save(request)

                        # Guardo los periodos académicos a evaluar
                        for periodoevaluacion in periodosevaluacion:
                            periodocronograma = PeriodoCronogramaEvaluacionInvestigacion(
                                cronograma=cronograma,
                                periodo=periodoevaluacion.periodo
                            )
                            periodocronograma.save(request)

                        # Guardo las criterios de evaluación para el cronograma
                        for idcriterio, porcentaje in zip(idscriterios, porcentajes):
                            criteriocronograma = CriterioCronogramaEvaluacionInvestigacion(
                                cronograma=cronograma,
                                criterio_id=idcriterio,
                                porcentaje=porcentaje
                            )
                            criteriocronograma.save(request)

                        log(u'%s agregó cronograma de evaluación de investigación: %s' % (persona, cronograma), request, "add")
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El cronograma de evaluación ya ha sido ingresado", "showSwal": "True", "swalType": "warning"})
                else:
                    for k, v in f.errors.items():
                        raise NameError( k + ', ' + v[0])
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editcronograma':
            try:
                f = CronogramavaluacionInvestigacionForm(request.POST, request.FILES)

                # Validar los archivos
                if 'instructivo' in request.FILES:
                    archivo = request.FILES['instructivo']
                    descripcionarchivo = 'Instructivo'
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                if f.is_valid():
                    if not CronogramaEvaluacionInvestigacion.objects.filter(status=True, descripcion=f.cleaned_data['descripcion'].strip().upper()).exclude(pk=int(encrypt(request.POST['id']))).exists():
                        # Consultar el cronograma
                        cronograma = CronogramaEvaluacionInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                        periodosevaluacion = cronograma.periodos_evaluacion()

                        if f.cleaned_data['fin'] <= f.cleaned_data['inicio']:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de fin de evaluación debe ser mayor a la fecha de inicio", "showSwal": "True", "swalType": "warning"})

                        finperiodo = periodosevaluacion[0].periodo.fin

                        if f.cleaned_data['inicio'] <= finperiodo:
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "La fecha de inicio de evaluación debe ser mayor a <b>{:%d-%m-%Y}</b>".format(finperiodo), "showSwal": "True", "swalType": "warning"})

                        # Obtener los valores de los detalles del formulario
                        idsregcriterios = request.POST.getlist('idregcriterios[]')  # Todos los ids de detalles de los criterios
                        porcentajes = request.POST.getlist('porcentajes[]')  # Todos los porcentajes de cada criterio

                        # Actualizo el cronograma
                        cronograma.descripcion = f.cleaned_data['descripcion'].strip().upper()
                        cronograma.inicio = f.cleaned_data['inicio']
                        cronograma.fin = f.cleaned_data['fin']

                        if 'instructivo' in request.FILES:
                            newfile = request.FILES['instructivo']
                            newfile._name = generar_nombre("instructivo", newfile._name)
                            cronograma.instructivo = newfile

                        cronograma.save(request)

                        # Guardo las criterios de evaluación para el cronograma
                        for idreg, porcentaje in zip(idsregcriterios, porcentajes):
                            criteriocronograma = CriterioCronogramaEvaluacionInvestigacion.objects.get(pk=idreg)
                            criteriocronograma.porcentaje = porcentaje
                            criteriocronograma.save(request)

                        log(u'%s editó cronograma de evaluación de investigación: %s' % (persona, cronograma), request, "edit")
                        return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
                    else:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El cronograma de evaluación ya ha sido ingresado", "showSwal": "True", "swalType": "warning"})
                else:
                    for k, v in f.errors.items():
                        raise NameError( k + ', ' + v[0])
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

            if action == 'addcronograma':
                try:
                    data['title'] = u'Agregar Cronograma de Evaluación de Investigación'
                    form = CronogramavaluacionInvestigacionForm()
                    data['form'] = form
                    data['periodosevaluacion'] = PeriodoEvaluacionInvestigacion.objects.filter(status=True, vigente=True).order_by('id')
                    data['criterios'] = CriterioEvaluacionInvestigacion.objects.filter(status=True, vigente=True).order_by('numero')
                    return render(request, "adm_evaluacioninvestigacion/addperiodo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcronograma':
                try:
                    data['title'] = u'Editar Cronograma de Evaluación de Investigación'
                    data['cronograma'] = cronograma = CronogramaEvaluacionInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))

                    form = CronogramavaluacionInvestigacionForm(
                        initial={
                            'descripcion': cronograma.descripcion,
                            'inicio': cronograma.inicio,
                            'fin': cronograma.fin
                        }
                    )

                    data['form'] = form
                    data['id'] = request.GET['id']
                    data['periodosevaluacion'] = cronograma.periodos_evaluacion()
                    data['criteriosevaluacion'] = cronograma.criterios_evaluacion()
                    data['tieneevaluaciones'] = cronograma.tiene_evaluaciones()

                    return render(request, "adm_evaluacioninvestigacion/editperiodo.html", data)
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

                cronogramas = CronogramaEvaluacionInvestigacion.objects.filter(filtro).order_by('-inicio', '-fin')

                paging = MiPaginador(cronogramas, 25)
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
                data['cronogramas'] = page.object_list
                data['title'] = u'Cronogramas Evaluacion Investigación'
                data['puedeagregar'] = not cronogramas.filter(estado__valor=1).exists()
                data['enlaceatras'] = "/ges_investigacion"

                return render(request, "adm_evaluacioninvestigacion/view.html", data)
            except Exception as ex:
                pass
