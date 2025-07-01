# -*- coding: UTF-8 -*-
import json
import os
from math import ceil

import PyPDF2
from datetime import time
from decimal import Decimal

import requests
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
from investigacion.forms import RegistroPropuestaProyectoInvestigacionForm, ContenidoProyectoInvestigacionForm, \
    PresupuestoProyectoInvestigacionForm, CronogramaActividadProyectoInvestigacionForm, ExternoForm, \
    FinalizaEdicionForm, InformeProyectoForm
from investigacion.funciones import coordinador_investigacion, vicerrector_investigacion_posgrado, reemplazar_fuente_para_formato_inscripcion
from investigacion.models import ProyectoInvestigacion, TipoRecursoPresupuesto, ProyectoInvestigacionInstitucion, \
    ProyectoInvestigacionIntegrante, ProyectoInvestigacionRecorrido, ProyectoInvestigacionItemPresupuesto, \
    TIPO_INTEGRANTE, ProyectoInvestigacionObjetivo, TipoResultadoCompromiso, ProyectoInvestigacionResultado, \
    ConvocatoriaProyecto, ConvocatoriaMontoFinanciamiento, ProyectoInvestigacionCronogramaActividad, \
    ProyectoInvestigacionCronogramaResponsable, ProyectoInvestigacionPasajeIntegrante, \
    ProyectoInvestigacionViaticoIntegrante, ProyectoInvestigacionActividadEvidencia, \
    ProyectoInvestigacionCronogramaEntregable, ProyectoInvestigacionHistorialArchivo, \
    ProyectoInvestigacionHistorialActividadEvidencia, ProyectoInvestigacionInforme, \
    ProyectoInvestigacionHistorialInforme, ProyectoInvestigacionInformeActividad, ProyectoInvestigacionInformeAnexo, ESTADO_EVALUACION_INTERNA_EXTERNA, EvaluacionProyecto, EvaluacionProyectoDetalle, ProyectoInvestigacionEvaluador
from sagest.commonviews import obtener_estado_solicitud
from sagest.models import datetime, Banco, DistributivoPersona, UnidadMedida, ExperienciaLaboral, Producto
from settings import SITE_STORAGE
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, variable_valor, \
    convertir_fecha, remover_caracteres_tildes_unicode, cuenta_email_disponible, generar_nombre, email_valido, \
    validar_archivo, null_to_decimal, cuenta_email_disponible_para_envio, fechaletra_corta
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsaveqrcertificado, convert_html_to_pdf, conviert_html_to_pdf
from sga.models import CUENTAS_CORREOS, ActividadConvalidacionPPV, Profesor, Administrativo, Inscripcion, \
    TituloInstitucion, Externo, miinstitucion, Titulo, InstitucionEducacionSuperior, Pais, NivelTitulacion, \
    AreaConocimientoTitulacion, Persona, Titulacion, ArticuloPersonaExterna, PonenciaPersonaExterna, \
    LibroPersonaExterna, ProyectoInvestigacionPersonaExterna, Coordinacion, MESES_CHOICES, RedPersona
from django.template import Context
from django.template.loader import get_template

import time as ET

from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']

    es_evaluador_externo = persona.es_evaluador_externo_proyectos_investigacion()
    es_evaluador_interno = persona.es_evaluador_interno_proyectos_investigacion()

    if not es_evaluador_externo and not es_evaluador_interno:
        return HttpResponseRedirect("/?info=El Módulo está disponible para Evaluadores de Proyectos de investigación.")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addevaluacioninterna':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                if '<img' in request.POST['observacion'].strip():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": f"El campo observaciones no debe contener imágenes incrustadas", "showSwal": "True", "swalType": "warning"})

                # Consulto el proyecto de investigación
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                estadoactual = proyecto.estado.valor
                reevaluacion = proyecto.estado.valor in [9, 32, 34]
                evaluador = ProyectoInvestigacionEvaluador.objects.get(persona=persona, proyecto=proyecto, status=True)

                # Obtengo los valores de los campos del formulario
                fuente = "Berlin Sans FB Demi"
                tamanio = "14"

                puntajetotal = request.POST['puntajetotal']
                observacion = reemplazar_fuente_para_formato_inscripcion(request.POST['observacion'].strip(), fuente, tamanio)

                # Verifico que no exista evaluación interna con el evaluador para el proyecto
                if EvaluacionProyecto.objects.filter(status=True, proyecto=proyecto, evaluador_id=evaluador, tipo=1).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La evaluación ya ha sido guardada", "showSwal": "True", "swalType": "warning"})

                archivo = ''
                if 'archivo' in request.FILES:
                    archivo = request.FILES['archivo']
                    descripcionarchivo = 'Archivo de Novedades'
                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                    archivo._name = generar_nombre("observacionevalinterna", archivo._name)

                # Obtengo los valores de los campos tipo arreglo del formulario
                idsrubricaitem = request.POST.getlist('idrubricaitem[]')
                puntajesasignados = request.POST.getlist('puntajeasignado[]')

                # Guardo la evaluación interna
                evaluacion = EvaluacionProyecto(
                    proyecto=proyecto,
                    fecha=datetime.now().date(),
                    tipo=1,
                    evaluador=evaluador,
                    puntajetotal=puntajetotal,
                    observacion=observacion,
                    estado=5,
                    adicional=reevaluacion,
                    estadoregistro=1
                )
                evaluacion.save(request)

                if archivo:
                    evaluacion.archivo = archivo
                    evaluacion.save(request)

                # Guardo el detalle de la evaluación interna
                numero = 1
                for idrubricaitem, puntajeasignado in zip(idsrubricaitem, puntajesasignados):
                    detalleevaluacion = EvaluacionProyectoDetalle(
                        evaluacion=evaluacion,
                        rubricaitem_id=idrubricaitem,
                        puntaje=puntajeasignado,
                        numero=numero
                    )
                    detalleevaluacion.save(request)
                    numero += 1

                if not reevaluacion:
                    # Si no tiene estado EVALUACION INTERNA EN CURSO
                    if estadoactual != 7:
                        # Actualizo el estado del proyecto a EVALUACION INTERNA EN CURSO
                        estado = obtener_estado_solicitud(3, 7)
                        proyecto.estado = estado
                        proyecto.save(request)

                        # Creo el recorrido del proyecto
                        recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                   fecha=datetime.now().date(),
                                                                   observacion='EVALUACIÓN INTERNA EN CURSO',
                                                                   estado=estado
                                                                   )
                        recorrido.save(request)
                else:
                    # Si no tiene estado REEVALUACIÓN INTERNA II
                    if estadoactual != 34:
                        # Si no tiene estado REEVALUACION INTERNA EN CURSO
                        if estadoactual != 32:
                            # Actualizo el estado del proyecto a REEVALUACION INTERNA EN CURSO
                            estado = obtener_estado_solicitud(3, 32)
                            proyecto.estado = estado
                            proyecto.save(request)

                            # Creo el recorrido del proyecto
                            recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                       fecha=datetime.now().date(),
                                                                       observacion='REEVALUACIÓN INTERNA EN CURSO',
                                                                       estado=estado
                                                                       )
                            recorrido.save(request)
                    else:
                        # Actualizo el estado del proyecto a REEVALUACION INTERNA II EN CURSO
                        estado = obtener_estado_solicitud(3, 36)
                        proyecto.estado = estado
                        proyecto.save(request)

                        # Creo el recorrido del proyecto
                        recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                   fecha=datetime.now().date(),
                                                                   observacion='REEVALUACIÓN INTERNA II EN CURSO',
                                                                   estado=estado
                                                                   )
                        recorrido.save(request)

                log(f'{persona} agregó evaluación interna al proyecto de investigación: {evaluacion}', request, "add")
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
                evaluacion = EvaluacionProyecto.objects.get(pk=int(encrypt(request.POST['id'])))

                # Obtengo los valores de los campos del formulario
                borrararchivo = request.POST['borrararchivo']
                puntajetotal = request.POST['puntajetotal']
                estadoevaluacion = request.POST['estadoevaluacion']
                observacion= request.POST['observacion'].strip().upper()

                archivo = ''
                if 'archivo' in request.FILES:
                    archivo = request.FILES['archivo']
                    descripcionarchivo = 'Archivo de Observaciones'
                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                    archivo._name = generar_nombre("observacionevalinterna", archivo._name)

                # Obtengo los valores de los campos tipo arreglo del formulario
                idsdetalles = request.POST.getlist('iddetalle[]')
                puntajesasignados = request.POST.getlist('puntajeasignado[]')

                # Actualizo la evaluación interna
                evaluacion.puntajetotal = puntajetotal
                evaluacion.observacion = observacion
                evaluacion.estado = estadoevaluacion
                evaluacion.estadoregistro = 1

                if archivo:
                    evaluacion.archivo = archivo
                elif borrararchivo == 'SI':
                    rutaarchivo = SITE_STORAGE + "/" + evaluacion.archivo.url
                    os.remove(rutaarchivo)
                    evaluacion.archivo = None

                evaluacion.save(request)

                # Actualizo los detalles de la evaluación interna
                for iddetalle, puntajeasignado in zip(idsdetalles, puntajesasignados):
                    # Consulto el detalle
                    detalleevaluacion = EvaluacionProyectoDetalle.objects.get(pk=iddetalle)
                    detalleevaluacion.puntaje = puntajeasignado
                    detalleevaluacion.save(request)

                log(u'%s editó evaluación interna al proyecto de investigación: %s' % (persona, evaluacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'imprimiractaevalinterna':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                evaluacion = EvaluacionProyecto.objects.get(pk=int(encrypt(request.POST['id'])))

                # if evaluacion.estado == 5:
                #     return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El resultado de la evaluación debe ser diferente a EN PROCESO DE EVALUACIÓN ", "showSwal": "True", "swalType": "warning"})

                data['evaluacion'] = evaluacion
                data['rubricas'] = evaluacion.proyecto.convocatoria.rubricas_evaluacion()
                data['evaluador'] = persona
                data['coordinador'] = coordinador_investigacion()
                data['director'] = vicerrector_investigacion_posgrado()
                data['minimoaprobacion'] = evaluacion.proyecto.convocatoria.minimoaprobacion
                fechaevaluacion = evaluacion.fecha
                # data['fechaevaluacion'] = str(fechaconfirma.day) + " de " + MESES_CHOICES[fechaconfirma.month - 1][1].capitalize() + " del " + str(fechaconfirma.year)
                data['fechaevaluacion'] = str(fechaevaluacion.day) + " de " + MESES_CHOICES[fechaevaluacion.month - 1][1].capitalize() + " del " + str(fechaevaluacion.year)

                directorio = SITE_STORAGE + '/media/proyectoinvestigacion/evaluaciones'
                try:
                    os.stat(directorio)
                except:
                    os.mkdir(directorio)

                # Archivo con la evaluación del proyecto
                fecha = datetime.now().date()
                hora = datetime.now().time()

                nombrearchivo = 'evaluacioninterna' + fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__() + '.pdf'
                valida = convert_html_to_pdf(
                    'eva_proyectoinvestigacion/actaevaluacioninternapdf.html',
                    {'pagesize': 'A4', 'data': data},
                    nombrearchivo,
                    directorio
                )

                if not valida:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar acta de evaluación.", "showSwal": "True", "swalType": "error"})

                ruta = "/media/proyectoinvestigacion/evaluaciones/" + nombrearchivo

                if evaluacion.estadoregistro == 1:
                    evaluacion.estadoregistro = 3
                    evaluacion.save(request)

                    log(u'%s generó acta de evaluación interna del proyecto de investigación: %s' % (persona, evaluacion), request, "edit")

                return JsonResponse({"result": "ok", "documento": ruta})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar acta de evaluación. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'subiracta':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                archivo = request.FILES['archivoacta']
                descripcionarchivo = 'Archivo Acta de evaluación firmada'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto la evaluación
                evaluacion = EvaluacionProyecto.objects.get(pk=int(encrypt(request.POST['id'])))

                archivo._name = generar_nombre("evalinternafirmaev" if evaluacion.tipo == 1 else "evalexternafirmaev", archivo._name)

                # Actualizo la evaluación
                evaluacion.archivoevaluacion = archivo
                evaluacion.estadoregistro = 4
                evaluacion.save(request)

                if evaluacion.tipo == 1:
                    log(u'%s subió acta de evaluación interna del proyecto de investigación: %s' % (persona, evaluacion), request, "edit")
                else:
                    log(u'%s subió acta de evaluación externa del proyecto de investigación: %s' % (persona, evaluacion), request, "edit")

                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'confirmarevaluacion':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la evaluación interna
                evaluacion = EvaluacionProyecto.objects.get(pk=int(encrypt(request.POST['id'])))
                proyecto = evaluacion.proyecto

                # Actualizo evaluación
                evaluacion.fechaconfirma = datetime.now().date()
                evaluacion.estadoregistro = 2
                evaluacion.save(request)

                # Notificar por e-mail a la coordinación de investigación
                # Obtengo la(s) cuenta(s) de correo desde la cual(es) se envía el e-mail
                listacuentascorreo = [0, 8, 9, 10, 11, 12, 13]  # sga@unemi.edu.ec, sga2@unemi.edu.ec, . . .sga7@unemi.edu.ec

                # Destinatarios
                lista_email_envio = ['investigacion@unemi.edu.ec']
                lista_email_cco = ['ivan.saltos.medina@gmail.com']
                # lista_email_envio = ['ivan_saltos_medina@hotmail.com']
                lista_adjuntos = []

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                if evaluacion.tipo == 1:
                    tituloemail = "Registro de Evaluación Interna de Propuesta de Proyecto de Investigación"
                    tiponotificacion = 'EVALINTCONF'
                else:
                    tituloemail = "Registro de Evaluación Externa de Propuesta de Proyecto de Investigación"
                    tiponotificacion = 'EVALEXTCONF'

                titulo = "Proyectos de Investigación"
                send_html_mail(tituloemail,
                               "emails/propuestaproyectoinvestigacion.html",
                               {'sistema': u'SGA - UNEMI',
                                'titulo': titulo,
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'tiponotificacion': tiponotificacion,
                                'proyecto': proyecto,
                                'evaluador': persona.nombre_completo_inverso()
                                },
                               lista_email_envio,  # Destinatarioa
                               lista_email_cco,  # Copia oculta, poner [] para que no me envíe jaja
                               lista_adjuntos,
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                if evaluacion.tipo == 1:
                    log(u'%s confirmó evaluación interna del proyecto de investigación: %s' % (persona, evaluacion), request, "edit")
                else:
                    log(u'%s confirmó evaluación externa del proyecto de investigación: %s' % (persona, evaluacion), request, "edit")

                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro de evaluación confirmado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addevaluacionexterna':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto el proyecto de investigación
                proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.POST['id'])))
                estadoactual = proyecto.estado.valor
                reevaluacion = proyecto.estado.valor in [12, 33, 35]
                evaluador = ProyectoInvestigacionEvaluador.objects.get(persona=persona, proyecto=proyecto, status=True)

                # Obtengo los valores de los campos del formulario
                puntajetotal = request.POST['puntajetotal']
                estadoevaluacion = request.POST['estadoevaluacion']
                observacion = request.POST['observacion'].strip().upper()

                # Verifico que no exista evaluación externa con el evaluador para el proyecto
                if EvaluacionProyecto.objects.filter(status=True, proyecto=proyecto, evaluador_id=evaluador, tipo=2).exists():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La evaluación ya ha sido guardada", "showSwal": "True", "swalType": "warning"})

                archivo = ''
                if 'archivo' in request.FILES:
                    archivo = request.FILES['archivo']
                    descripcionarchivo = 'Archivo de Observaciones'
                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                    archivo._name = generar_nombre("observacionevalexterna", archivo._name)

                # Obtengo los valores de los campos tipo arreglo del formulario
                idsrubricaitem = request.POST.getlist('idrubricaitem[]')
                puntajesasignados = request.POST.getlist('puntajeasignado[]')

                # Guardo la evaluación interna
                evaluacion = EvaluacionProyecto(
                    proyecto=proyecto,
                    fecha=datetime.now().date(),
                    tipo=2,
                    evaluador=evaluador,
                    puntajetotal=puntajetotal,
                    observacion=observacion,
                    estado=estadoevaluacion,
                    adicional=reevaluacion,
                    estadoregistro=1
                )
                evaluacion.save(request)

                if archivo:
                    evaluacion.archivo = archivo
                    evaluacion.save(request)

                # Guardo el detalle de la evaluación externa
                numero = 1
                for idrubricaitem, puntajeasignado in zip(idsrubricaitem, puntajesasignados):
                    detalleevaluacion = EvaluacionProyectoDetalle(
                        evaluacion=evaluacion,
                        rubricaitem_id=idrubricaitem,
                        puntaje=puntajeasignado,
                        numero=numero
                    )
                    detalleevaluacion.save(request)
                    numero += 1

                if not reevaluacion:
                    # Si no tiene estado EVALUACION EXTERNA EN CURSO
                    if estadoactual != 10:
                        # Actualizo el estado del proyecto a EVALUACION EXTERNA EN CURSO
                        estado = obtener_estado_solicitud(3, 10)
                        proyecto.estado = estado
                        proyecto.save(request)

                        # Creo el recorrido del proyecto
                        recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                   fecha=datetime.now().date(),
                                                                   observacion='EVALUACIÓN EXTERNA EN CURSO',
                                                                   estado=estado
                                                                   )
                        recorrido.save(request)
                else:
                    # Si no tiene estado REEVALUACIÓN EXTERNA II
                    if estadoactual != 35:
                        # Si no tiene estado REEVALUACION EXTERNA EN CURSO
                        if estadoactual != 33:
                            # Actualizo el estado del proyecto a REEVALUACION EXTERNA EN CURSO
                            estado = obtener_estado_solicitud(3, 33)
                            proyecto.estado = estado
                            proyecto.save(request)

                            # Creo el recorrido del proyecto
                            recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                       fecha=datetime.now().date(),
                                                                       observacion='REEVALUACIÓN EXTERNA EN CURSO',
                                                                       estado=estado
                                                                       )
                            recorrido.save(request)
                    else:
                        # Actualizo el estado del proyecto a REEVALUACION EXTERNA II EN CURSO
                        estado = obtener_estado_solicitud(3, 37)
                        proyecto.estado = estado
                        proyecto.save(request)

                        # Creo el recorrido del proyecto
                        recorrido = ProyectoInvestigacionRecorrido(proyecto=proyecto,
                                                                   fecha=datetime.now().date(),
                                                                   observacion='REEVALUACIÓN EXTERNA II EN CURSO',
                                                                   estado=estado
                                                                   )
                        recorrido.save(request)

                log(u'% agregó evaluación externa al proyecto de investigación: %s' % (persona, evaluacion), request, "add")
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
                evaluacion = EvaluacionProyecto.objects.get(pk=int(encrypt(request.POST['id'])))

                # Obtengo los valores de los campos del formulario
                borrararchivo = request.POST['borrararchivo']
                puntajetotal = request.POST['puntajetotal']
                estadoevaluacion = request.POST['estadoevaluacion']
                observacion= request.POST['observacion'].strip().upper()

                archivo = ''
                if 'archivo' in request.FILES:
                    archivo = request.FILES['archivo']
                    descripcionarchivo = 'Archivo de Observaciones'
                    # Validar el archivo
                    resp = validar_archivo(descripcionarchivo, archivo, ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                    archivo._name = generar_nombre("observacionevalexterna", archivo._name)

                # Obtengo los valores de los campos tipo arreglo del formulario
                idsdetalles = request.POST.getlist('iddetalle[]')
                puntajesasignados = request.POST.getlist('puntajeasignado[]')

                # Actualizo la evaluación interna
                evaluacion.puntajetotal = puntajetotal
                evaluacion.observacion = observacion
                evaluacion.estado = estadoevaluacion
                evaluacion.estadoregistro = 1

                if archivo:
                    evaluacion.archivo = archivo
                elif borrararchivo == 'SI':
                    rutaarchivo = SITE_STORAGE + "/" + evaluacion.archivo.url
                    os.remove(rutaarchivo)
                    evaluacion.archivo = None

                evaluacion.save(request)

                # Actualizo los detalles de la evaluación interna
                for iddetalle, puntajeasignado in zip(idsdetalles, puntajesasignados):
                    # Consulto el detalle
                    detalleevaluacion = EvaluacionProyectoDetalle.objects.get(pk=iddetalle)
                    detalleevaluacion.puntaje = puntajeasignado
                    detalleevaluacion.save(request)

                log(u'%s editó evaluación externa al proyecto de investigación: %s' % (persona, evaluacion), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'imprimiractaevalexterna':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                evaluacion = EvaluacionProyecto.objects.get(pk=int(encrypt(request.POST['id'])))

                if evaluacion.estado == 5:
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El resultado de la evaluación debe ser diferente a EN PROCESO DE EVALUACIÓN ", "showSwal": "True", "swalType": "warning"})

                data['evaluacion'] = evaluacion
                data['rubricas'] = evaluacion.proyecto.convocatoria.rubricas_evaluacion()
                data['evaluador'] = persona
                data['coordinador'] = coordinador_investigacion()
                data['director'] = vicerrector_investigacion_posgrado()
                data['minimoaprobacion'] = evaluacion.proyecto.convocatoria.minimoaprobacion
                fechaevaluacion = evaluacion.fecha
                # data['fechaevaluacion'] = str(fechaconfirma.day) + " de " + MESES_CHOICES[fechaconfirma.month - 1][1].capitalize() + " del " + str(fechaconfirma.year)
                data['fechaevaluacion'] = str(fechaevaluacion.day) + " de " + MESES_CHOICES[fechaevaluacion.month - 1][1].capitalize() + " del " + str(fechaevaluacion.year)

                directorio = SITE_STORAGE + '/media/proyectoinvestigacion/evaluaciones'
                try:
                    os.stat(directorio)
                except:
                    os.mkdir(directorio)

                # Archivo con la evaluación del proyecto
                fecha = datetime.now().date()
                hora = datetime.now().time()

                nombrearchivo = 'evaluacionexterna' + fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__() + '.pdf'
                valida = convert_html_to_pdf(
                    'eva_proyectoinvestigacion/actaevaluacionexternapdf.html',
                    {'pagesize': 'A4', 'data': data},
                    nombrearchivo,
                    directorio
                )

                if not valida:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar acta de evaluación.", "showSwal": "True", "swalType": "error"})

                ruta = "/media/proyectoinvestigacion/evaluaciones/" + nombrearchivo

                if evaluacion.estadoregistro == 1:
                    evaluacion.estadoregistro = 3
                    evaluacion.save(request)

                    log(u'%s generó acta de evaluación externa del proyecto de investigación: %s' % (persona, evaluacion), request, "edit")

                return JsonResponse({"result": "ok", "documento": ruta})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar acta de evaluación. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'verificarevaluacion':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                evaluacioncompleta = True
                # Consulto la evaluación externa
                evaluacion = EvaluacionProyecto.objects.get(pk=int(encrypt(request.POST['id'])))

                # Si el estado es EN PROCESO DE EVALUACIÓN
                if evaluacion.estado == 5:
                    return JsonResponse({"result": "bad", "mensaje": u"El estado de la evaluación no debe ser EN PROCESO DE EVALUACIÓN"})

                # Si el estado no es ACEPTADO Y NO REQUIERE MODIFICACIONES
                if evaluacion.estado != 1:
                    # Verificar si tiene subido el archivo de las observaciones
                    if not evaluacion.archivo:
                        evaluacioncompleta = False

                if evaluacioncompleta:
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Falta subir el archivo de las observaciones en la evaluación"})

            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. [%s]" % msg})

        return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Solicitud incorrecta.", "showSwal": "True", "swalType": "error"})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'propuestas':
                try:
                    search = None
                    ids = None

                    tipoevaluacion = int(request.GET['tipoeval'])
                    reevaluacion = request.GET['reeval'] == 'S'
                    convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.GET['idc'])))

                    if 'id' in request.GET:
                        ids = request.GET['id']
                        proyectos = ProyectoInvestigacion.objects.filter(convocatoria=convocatoria, status=True, pk=int(encrypt(request.GET['id'])))
                    elif 's' in request.GET:
                        search = request.GET['s']
                        proyectos = ProyectoInvestigacion.objects.filter(convocatoria=convocatoria, status=True,  proyectoinvestigacionevaluador__persona=persona, proyectoinvestigacionevaluador__tipo=tipoevaluacion, proyectoinvestigacionevaluador__tipoproyecto=1, proyectoinvestigacionevaluador__status=True, proyectoinvestigacionevaluador__reevaluacion=reevaluacion, titulo__icontains=search).exclude(estado__valor=14)
                    else:
                        proyectos = ProyectoInvestigacion.objects.filter(convocatoria=convocatoria, status=True, proyectoinvestigacionevaluador__persona=persona, proyectoinvestigacionevaluador__tipo=tipoevaluacion, proyectoinvestigacionevaluador__tipoproyecto=1, proyectoinvestigacionevaluador__status=True, proyectoinvestigacionevaluador__reevaluacion=reevaluacion).exclude(estado__valor=14).order_by('-id')

                    paging = MiPaginador(proyectos, 25)
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
                    data['proyectos'] = page.object_list

                    if not reevaluacion:
                        data['periodoevaluacionvigente'] = convocatoria.evaluacion_interna_abierta() if tipoevaluacion == 1 else convocatoria.evaluacion_externa_abierta()
                    else:
                        data['periodoevaluacionvigente'] = convocatoria.reevaluacion_interna_abierta() if tipoevaluacion == 1 else convocatoria.reevaluacion_externa_abierta()

                    data['title'] = u'Evaluación de Propuestas de Proyectos de Investigación' if not reevaluacion else u'Reevaluación de Propuestas de Proyectos de Investigación'
                    data['tituloconvocatoria'] = convocatoria.descripcion if convocatoria else ''
                    data['idconvocatoria'] = convocatoria.id
                    data['tipoevaluacion'] = tipoevaluacion
                    data['reevaluacion'] = reevaluacion
                    data['reeval'] = request.GET['reeval']

                    return render(request, "eva_proyectoinvestigacion/propuestas.html", data)
                except Exception as ex:
                    pass

            elif action == 'informacionproyecto':
                try:
                    data['title'] = u'Información de la Propuesta de Proyecto de Investigación'
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))

                    data['id'] = request.GET['id']
                    data['proyecto'] = proyecto
                    data['convocatoriamonto'] = proyecto.convocatoria.convocatoriamontofinanciamiento_set.filter(status=True, tipoequipamiento=proyecto.compraequipo)[0]

                    return render(request, "eva_proyectoinvestigacion/informacionproyecto.html", data)
                except Exception as ex:
                    pass

            elif action == 'mostrarhojavida':
                try:
                    title = u'Hoja de Vida del Integrante'
                    integranteproyecto = ProyectoInvestigacionIntegrante.objects.get(pk=int(encrypt(request.GET['id'])))

                    data['integranteproyecto'] = integranteproyecto
                    data['integrante'] = integranteproyecto.persona
                    data['formacionacademica'] = integranteproyecto.formacion_academica()
                    data['experiencia'] = integranteproyecto.experiencia_laboral()
                    data['experienciaunemi'] = integranteproyecto.experiencia_laboral_unemi()
                    data['tipopersona'] = integranteproyecto.tipo
                    data['evaluacion'] = True

                    if integranteproyecto.tipo != 4:
                        data['articulos'] = integranteproyecto.articulos_publicados()
                        data['ponencias'] = integranteproyecto.ponencias_publicadas()
                        data['libros'] = integranteproyecto.libros_publicados()
                        data['capitulos'] = integranteproyecto.capitulos_libro_publicados()
                        data['proyectosunemi'] = integranteproyecto.proyectos_investigacion_unemi()
                        data['proyectosexternos'] = integranteproyecto.proyectos_investigacion_externo()
                    else:
                        data['articulos_externa'] = integranteproyecto.articulos_publicados_persona_externa()
                        data['ponencias_externa'] = integranteproyecto.ponencias_publicadas_persona_externa()
                        data['libros_externa'] = integranteproyecto.libros_publicados_persona_externa()
                        data['capitulos_externa'] = integranteproyecto.capitulos_libro_publicados_persona_externa()
                        data['proyectos_externa'] = integranteproyecto.proyectos_investigacion_persona_externa()

                    template = get_template("pro_proyectoinvestigacion/mostrarhojavida.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addevaluacioninterna':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))
                    data['title'] = u'Agregar Evaluación Interna de la Propuesta de Proyecto de Investigación' if proyecto.estado.valor != 9 else u'Agregar Reevaluación Interna de la Propuesta de Proyecto de Investigación'
                    data['proyecto'] = proyecto
                    data['estados'] = ESTADO_EVALUACION_INTERNA_EXTERNA
                    data['evaluador'] = proyecto.proyectoinvestigacionevaluador_set.filter(status=True, persona=persona, tipo=1, tipoproyecto=1)[0]
                    data['rubricas'] = proyecto.convocatoria.rubricas_evaluacion()
                    data['fecha'] = datetime.now().date()
                    data['tipoevaluacion'] = 1
                    data['minimoaprobacion'] = proyecto.convocatoria.minimoaprobacion
                    data['reeval'] = 'S' if proyecto.estado.valor in [9, 32, 34] else 'N'

                    convocatoria = proyecto.convocatoria
                    # if proyecto.compraequipo:
                    #     convocatoriamonto = proyecto.convocatoria.convocatoriamontofinanciamiento_set.filter(status=True, tipoequipamiento=proyecto.compraequipo)[0]
                    # else:
                    #     convocatoriamonto = proyecto.convocatoria.convocatoriamontofinanciamiento_set.filter(status=True, categoria=proyecto.categoria2)[0]

                    # data['convocatoriamonto'] = convocatoriamonto
                    data['recursosconvocatoria'] = convocatoria.tipos_recursos_presupuesto()
                    # regfin = convocatoriamonto
                    # data['montominimoequipos'] = Decimal(proyecto.montounemi * (regfin.porcentajecompra) / 100).quantize(Decimal('.01'))
                    # data['totalequipos'] = proyecto.totales_detalle_equipos()['totaldetalle']

                    data['objetivos'] = proyecto.objetivos_especificos()
                    data['ponderacion'] = proyecto.total_ponderacion_actividades()
                    data['cumplimiento'] = 0
                    data['porcumplir'] = 0

                    return render(request, "eva_proyectoinvestigacion/addevaluacioninterna.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editevaluacioninterna':
                try:
                    evaluacion = EvaluacionProyecto.objects.get(pk=int(encrypt(request.GET['ide'])))
                    data['title'] = u'Editar Evaluación Interna de la Propuesta de Proyecto de Investigación' if not evaluacion.adicional else u'Editar Reevaluación Interna de la Propuesta de Proyecto de Investigación'
                    data['evaluacion'] = evaluacion
                    data['proyecto'] = proyecto = evaluacion.proyecto

                    if evaluacion.puntajetotal >= proyecto.convocatoria.minimoaprobacion:
                        estados = (
                            (5, u'EN PROCESO DE EVALUACIÓN'),
                            (1, u'ACEPTADO Y NO REQUIERE MODIFICACIONES'),
                            (2, u'SERÁ ACEPTADO LUEGO DE MODIFICACIONES MENORES')
                        )
                    else:
                        estados = (
                            (5, u'EN PROCESO DE EVALUACIÓN'),
                            (3, u'DEBE SER PRESENTADO NUEVAMENTE LUEGO DE MODIFICACIONES MAYORES'),
                            (4, u'RECHAZADO')
                        )

                    data['estados'] = estados
                    data['rubricas'] = proyecto.convocatoria.rubricas_evaluacion()
                    data['tipoevaluacion'] = 1
                    data['minimoaprobacion'] = proyecto.convocatoria.minimoaprobacion
                    data['reeval'] = 'S' if evaluacion.adicional else 'N'

                    return render(request, "eva_proyectoinvestigacion/editevaluacioninterna.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'subiracta':
                try:
                    data['title'] = u'Subir Acta de Evaluación Firmada'
                    evaluacion = EvaluacionProyecto.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['evaluacion'] = evaluacion
                    template = get_template("eva_proyectoinvestigacion/subiracta.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addevaluacionexterna':
                try:
                    proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['idp'])))
                    data['title'] = u'Agregar Evaluación Externa de la Propuesta de Proyecto de Investigación' if proyecto.estado.valor != 12 else u'Agregar Reevaluación Externa de la Propuesta de Proyecto de Investigación'
                    data['proyecto'] = proyecto
                    data['estados'] = ESTADO_EVALUACION_INTERNA_EXTERNA
                    data['evaluador'] = proyecto.proyectoinvestigacionevaluador_set.filter(status=True, persona=persona, tipo=2, tipoproyecto=1)[0]
                    data['rubricas'] = proyecto.convocatoria.rubricas_evaluacion()
                    data['fecha'] = datetime.now().date()
                    data['tipoevaluacion'] = 2
                    data['minimoaprobacion'] = proyecto.convocatoria.minimoaprobacion
                    data['reeval'] = 'S' if proyecto.estado.valor in [12, 33, 35] else 'N'
                    return render(request, "eva_proyectoinvestigacion/addevaluacionexterna.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editevaluacionexterna':
                try:
                    evaluacion = EvaluacionProyecto.objects.get(pk=int(encrypt(request.GET['ide'])))
                    data['title'] = u'Editar Evaluación Externa de la Propuesta de Proyecto de Investigación' if not evaluacion.adicional else u'Editar Reevaluación Externa de la Propuesta de Proyecto de Investigación'
                    data['evaluacion'] = evaluacion
                    data['proyecto'] = proyecto = evaluacion.proyecto

                    if evaluacion.puntajetotal >= proyecto.convocatoria.minimoaprobacion:
                        estados = (
                            (5, u'EN PROCESO DE EVALUACIÓN'),
                            (1, u'ACEPTADO Y NO REQUIERE MODIFICACIONES'),
                            (2, u'SERÁ ACEPTADO LUEGO DE MODIFICACIONES MENORES')
                        )
                    else:
                        estados = (
                            (5, u'EN PROCESO DE EVALUACIÓN'),
                            (3, u'DEBE SER PRESENTADO NUEVAMENTE LUEGO DE MODIFICACIONES MAYORES'),
                            (4, u'RECHAZADO')
                        )

                    data['estados'] = estados
                    data['rubricas'] = proyecto.convocatoria.rubricas_evaluacion()
                    data['tipoevaluacion'] = 2
                    data['minimoaprobacion'] = proyecto.convocatoria.minimoaprobacion
                    data['reeval'] = 'S' if evaluacion.adicional else 'N'

                    return render(request, "eva_proyectoinvestigacion/editevaluacionexterna.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'mostrarformacionacademica':
                try:
                    data['proyecto'] = proyecto = ProyectoInvestigacion.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['participantes'] = proyecto.integrantes_proyecto_informe()

                    template = get_template("eva_proyectoinvestigacion/formacionacademicaintegrantes.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editevaluacionexterna2':
                try:
                    evaluacion = EvaluacionProyecto.objects.get(pk=int(encrypt(request.GET['ide'])))
                    data['title'] = u'Evaluación Externa de la Propuesta de Proyecto de Investigación'
                    data['evaluacion'] = evaluacion
                    data['proyecto'] = proyecto = evaluacion.proyecto

                    if evaluacion.puntajetotal >= 70:
                        estados = (
                            (5, u'EN PROCESO DE EVALUACIÓN'),
                            (1, u'ACEPTADO Y NO REQUIERE MODIFICACIONES'),
                            (2, u'SERÁ ACEPTADO LUEGO DE MODIFICACIONES MENORES')
                        )
                    else:
                        estados = (
                            (5, u'EN PROCESO DE EVALUACIÓN'),
                            (3, u'DEBE SER PRESENTADO NUEVAMENTE LUEGO DE MODIFICACIONES MAYORES'),
                            (4, u'RECHAZADO')
                        )

                    data['estados'] = estados
                    data['evaluador'] = proyecto.proyectoinvestigacionevaluador_set.filter(status=True, persona=persona, tipo=2, tipoproyecto=1)[0]
                    data['rubricas'] = proyecto.convocatoria.rubricas_evaluacion()
                    return render(request, "eva_proyectoinvestigacion/editevaluacionexterna.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            convocatoriasevalinterna = ConvocatoriaProyecto.objects.filter(status=True, proyectoinvestigacion__status=True, proyectoinvestigacion__proyectoinvestigacionevaluador__persona=persona, proyectoinvestigacion__proyectoinvestigacionevaluador__tipo=1, proyectoinvestigacion__proyectoinvestigacionevaluador__tipoproyecto=1, proyectoinvestigacion__proyectoinvestigacionevaluador__status=True, proyectoinvestigacion__proyectoinvestigacionevaluador__reevaluacion=False).distinct().order_by('-apertura', '-cierre')
            convocatoriasreevalinterna = ConvocatoriaProyecto.objects.filter(status=True, proyectoinvestigacion__status=True, proyectoinvestigacion__proyectoinvestigacionevaluador__persona=persona, proyectoinvestigacion__proyectoinvestigacionevaluador__tipo=1, proyectoinvestigacion__proyectoinvestigacionevaluador__tipoproyecto=1, proyectoinvestigacion__proyectoinvestigacionevaluador__status=True, proyectoinvestigacion__proyectoinvestigacionevaluador__reevaluacion=True).distinct().order_by('-apertura', '-cierre')
            convocatoriasevalexterna = ConvocatoriaProyecto.objects.filter(status=True, proyectoinvestigacion__status=True, proyectoinvestigacion__proyectoinvestigacionevaluador__persona=persona, proyectoinvestigacion__proyectoinvestigacionevaluador__tipo=2, proyectoinvestigacion__proyectoinvestigacionevaluador__tipoproyecto=1, proyectoinvestigacion__proyectoinvestigacionevaluador__status=True, proyectoinvestigacion__proyectoinvestigacionevaluador__reevaluacion=False).distinct().order_by('-apertura', '-cierre')
            convocatoriasreevalexterna = ConvocatoriaProyecto.objects.filter(status=True, proyectoinvestigacion__status=True, proyectoinvestigacion__proyectoinvestigacionevaluador__persona=persona, proyectoinvestigacion__proyectoinvestigacionevaluador__tipo=2, proyectoinvestigacion__proyectoinvestigacionevaluador__tipoproyecto=1, proyectoinvestigacion__proyectoinvestigacionevaluador__status=True, proyectoinvestigacion__proyectoinvestigacionevaluador__reevaluacion=True).distinct().order_by('-apertura', '-cierre')

            data['convocatoriasevalinterna'] = convocatoriasevalinterna
            data['convocatoriasreevalinterna'] = convocatoriasreevalinterna
            data['convocatoriasevalexterna'] = convocatoriasevalexterna
            data['convocatoriasreevalexterna'] = convocatoriasreevalexterna
            data['title'] = u'Convocatorias a Proyectos de Investigación'

            return render(request, "eva_proyectoinvestigacion/convocatoriaproyecto.html", data)

