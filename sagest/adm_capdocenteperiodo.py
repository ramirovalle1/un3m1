# -*- coding: UTF-8 -*-
import json
from decimal import Decimal

import xlwt
from googletrans import Translator
from datetime import datetime, date, timedelta, time
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from num2words import num2words
from xlwt import *
from decorators import secure_module, last_access
from sagest.forms import CapDocentePeriodoForm, CapacitacionPersonaDocenteForm
from sagest.models import CapPeriodo, DistributivoPersona, Departamento
from settings import PUESTO_ACTIVO_ID
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import PlanificarCapacitacionesForm, PlanificarCapacitacionesDevolucionForm, \
    ConfirmarEjecutadoCapacitacionesForm, SubirEvidenciaEjecutadoCapacitacionesForm, DescuentoRolForm, \
    PlanificarCapacitacionesArchivoForm
from sga.funciones import MiPaginador, log, variable_valor, generar_nombre, fechaletra_corta, convertir_fecha, \
    validar_archivo, null_to_decimal
from sga.models import Administrativo, Persona, Pais, Provincia, Canton, Parroquia, DIAS_CHOICES, \
    CronogramaCapacitacionDocente, PlanificarCapacitaciones, PlanificarCapacitacionesRecorrido, \
    PlanificarCapacitacionesDetalleCriterios, miinstitucion, Coordinacion, ProfesorDistributivoHoras, Titulacion, \
    MESES_CHOICES, ESTADOS_PLANIFICAR_CAPACITACIONES, Periodo, ResponsableCoordinacion, CoordinadorCarrera, Capacitacion
from django.template.context import Context
from django.db.models import Max, Q, Sum
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.tasks import conectar_cuenta, send_html_mail
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret',login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    lista = []
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user


    if not persona.grupo_talentohumano() and not persona.grupo_asistente_talentohumano() and not persona.grupo_evaluacion():
        return HttpResponseRedirect("/?info=Este módulo solo es para uso de la unidad de talento humano.")

    if request.method == 'POST':
        action = request.POST['action']
        #PERIODO
        if action == 'addperiodo':
            try:
                if 'modeloinforme' in request.FILES:
                    descripcionarchivo = 'Modelo Informe'
                    resp = validar_archivo(descripcionarchivo, request.FILES['modeloinforme'], ['doc', 'docx'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'resolucionocas' in request.FILES:
                    descripcionarchivo = 'Resolución OCAS'
                    resp = validar_archivo(descripcionarchivo, request.FILES['resolucionocas'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'instructivo' in request.FILES:
                    descripcionarchivo = 'Instructivo'
                    resp = validar_archivo(descripcionarchivo, request.FILES['instructivo'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'manualusuario' in request.FILES:
                    descripcionarchivo = 'Manual de usuario'
                    resp = validar_archivo(descripcionarchivo, request.FILES['manualusuario'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'conveniodevengacion' in request.FILES:
                    descripcionarchivo = 'Convenio de devengación'
                    resp = validar_archivo(descripcionarchivo, request.FILES['conveniodevengacion'], ['doc', 'docx'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})


                form = CapDocentePeriodoForm(request.POST, request.FILES)

                if form.is_valid():
                    if form.cleaned_data['inicio'] < form.cleaned_data['fin']:
                        if form.cleaned_data['fin'].month > 9:
                            return JsonResponse({"result": "bad", "mensaje": u"El mes de la fecha de fin no debe superar Septiembre"})

                        if form.cleaned_data['fin'].year != form.cleaned_data['inicio'].year:
                            return JsonResponse({"result": "bad", "mensaje": u"El año de la fecha de inicio y fin deben ser iguales"})

                        if form.cleaned_data['monto'] <= 0:
                            return JsonResponse({"result": "bad", "mensaje": u"El monto debe ser mayor a $ 0.00"})

                        if form.cleaned_data['iniciocapacitacion'] < form.cleaned_data['inicio']:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio de capacitación debe ser mayor o igual que la fecha inicio del cronograma"})

                        if form.cleaned_data['iniciocapacitacion'] > form.cleaned_data['fincapacitacion']:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha de fin de capacitación debe ser mayor que la fecha de inicio"})

                        if CronogramaCapacitacionDocente.objects.values('id').filter(descripcion=form.cleaned_data['descripcion'], status=True, tipo=form.cleaned_data['tipo']).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"La descripción ya existe."})

                        periodo = CronogramaCapacitacionDocente(tipo=form.cleaned_data['tipo'],
                                                              descripcion=form.cleaned_data['descripcion'].upper(),
                                                              resolucion=form.cleaned_data['resolucion'].upper(),
                                                              inicio=form.cleaned_data['inicio'],
                                                              fin=form.cleaned_data['fin'],
                                                              monto=form.cleaned_data['monto'],
                                                              iniciocapacitacion=form.cleaned_data['iniciocapacitacion'],
                                                              fincapacitacion=form.cleaned_data['fincapacitacion'],
                                                              fechaconvenio=form.cleaned_data['fechaconvenio']
                                                              )

                        periodo.save(request)

                        if 'modeloinforme' in request.FILES:
                            arch = request.FILES['modeloinforme']
                            arch._name = generar_nombre("informecomisioncap", arch._name)
                            periodo.modeloinforme = arch

                        if 'resolucionocas' in request.FILES:
                            arch = request.FILES['resolucionocas']
                            arch._name = generar_nombre("resolucionocas", arch._name)
                            periodo.resolucionocas = arch

                        if 'instructivo' in request.FILES:
                            arch = request.FILES['instructivo']
                            arch._name = generar_nombre("instructivo", arch._name)
                            periodo.instructivo = arch

                        if 'manualusuario' in request.FILES:
                            arch = request.FILES['manualusuario']
                            arch._name = generar_nombre("manualusuario", arch._name)
                            periodo.manualusuario = arch

                        if 'conveniodevengacion' in request.FILES:
                            arch = request.FILES['conveniodevengacion']
                            arch._name = generar_nombre("conveniodevengacion", arch._name)
                            periodo.conveniodevengacion = arch

                        periodo.save(request)

                        log(u'Agrego Período de Cronograma de capacitaciones: %s - [%s]' % (periodo,periodo.id), request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "Las fechas no concuerdan"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "mensaje":translator.translate(ex.__str__(),'es').text})

        elif action == 'addcaprecorrido':
            try:
                browser = request.POST['navegador']
                ops = request.POST['os']
                cookies = request.POST['cookies']
                screensize = request.POST['screensize']
                hoy = datetime.now().date()
                capacitacion = PlanificarCapacitaciones.objects.get(pk=request.POST['id'])
                estado = int(request.POST['esta'])
                fase = request.POST['fase']

                if fase == 'LEG':
                    if capacitacion.estado == 4 or capacitacion.estado == 10:
                        esValido = True
                    else:
                        esValido = False
                        mensaje = u"No se puede grabar debido a que el Registro tiene estado actual %s" % (capacitacion.get_estado_display())

                    if not capacitacion.archivoconvenio and estado == 5:
                        esValido = False
                        mensaje = u"No se puede grabar debido a que el solicitante no ha subido en el sistema el convenio de devengación"

                if esValido:
                    recorridocap = PlanificarCapacitacionesRecorrido(planificarcapacitaciones=capacitacion,
                                                                     observacion=request.POST['obse'],
                                                                     estado=int(request.POST['esta']),
                                                                     fecha=datetime.now().date(),
                                                                     persona=persona)
                    recorridocap.save(request)
                    capacitacion.estado = estado
                    capacitacion.save(request)

                    #micorreo = Persona.objects.get(cedula='0923704928')
                    autoridad2 = capacitacion.obtenerdatosautoridad('TES', None)
                    enviaremail = True
                    tituloemail = 'Legalización de Solicitud de capacitación'

                    if capacitacion.tipo == 1:
                        if persona.grupo_evaluacion():
                            send_html_mail("Cambio de Estado de solicitud de capacitación",
                                           "emails/aprobacion_capdocente.html",
                                           {'sistema': u'SGA - UNEMI',
                                            'docente': capacitacion.profesor.persona,
                                            'numero': capacitacion.id,
                                            'solicitud': capacitacion,
                                            'cronograma': capacitacion.cronograma,
                                            'estadoap': estado,
                                            'observacionap': request.POST['obse'],
                                            'aprueba': 'la Dirección de Evaluaciòn y Perfeccionamiento Académico',
                                            'fecha': datetime.now().date(),
                                            'hora': datetime.now().time(),
                                            'bs': browser,
                                            'os': ops,
                                            'cookies': cookies,
                                            'screensize': screensize,
                                            't': miinstitucion()},
                                           capacitacion.profesor.persona.lista_emails_envio(),
                                           [],
                                           cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                           )
                        else:
                            send_html_mail("Cambio de Estado de solicitud de capacitación",
                                           "emails/aprobacion_capdocente.html",
                                           {'sistema': u'SGA - UNEMI',
                                            'docente': capacitacion.profesor.persona,
                                            'numero': capacitacion.id,
                                            'solicitud': capacitacion,
                                            'cronograma': capacitacion.cronograma,
                                            'estadoap': estado,
                                            'observacionap': request.POST['obse'],
                                            'aprueba':'la Dirección de Talento humano',
                                            'fecha': datetime.now().date(),
                                            'hora': datetime.now().time(),
                                            'bs': browser,
                                            'os': ops,
                                            'cookies': cookies,
                                            'screensize': screensize,
                                            't': miinstitucion()},
                                           capacitacion.profesor.persona.lista_emails_envio(),
                                           [],
                                           cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                           )


                        if autoridad2 and estado == 5:
                            send_html_mail(tituloemail,
                                           "emails/notificacion_capdocente.html",
                                           {'sistema': u'SGA - UNEMI',
                                            'fase': fase,
                                            'fecha': datetime.now().date(),
                                            'hora': datetime.now().time(),
                                            'numero': capacitacion.id,
                                            'solicitud': capacitacion,
                                            'cronograma': capacitacion.cronograma,
                                            'docente': capacitacion.profesor.persona,
                                            'autoridad1': persona,
                                            'autoridad2': autoridad2.persona,
                                            't': miinstitucion()
                                            },
                                           autoridad2.persona.lista_emails_envio(),
                                           [],
                                           cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                           )

                    else:
                        estadocorreo = "LEGALIZADA" if estado == 5 else "DENEGADA"
                        if persona.grupo_evaluacion():
                            tituloemail = "Solicitud de Capacitación " + estadocorreo + " por la Dirección de Evaluaciòn y Perfeccionamiento Académico"
                            send_html_mail(tituloemail,
                                           "emails/aprobacion_capadmtra.html",
                                           {'sistema': u'SAGEST - UNEMI',
                                            'administrativo': capacitacion.administrativo.persona,
                                            'numero': capacitacion.id,
                                            'solicitud': capacitacion,
                                            'cronograma': capacitacion.cronograma,
                                            'estadoap': estado,
                                            'observacionap': request.POST['obse'],
                                            'aprueba': 'la Dirección de Talento humano',
                                            'textoadicional': '',
                                            'fecha': datetime.now().date(),
                                            'hora': datetime.now().time(),
                                            't': miinstitucion()},
                                           capacitacion.administrativo.persona.lista_emails_envio(),
                                           [],
                                           cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                           )
                        else:
                            tituloemail = "Solicitud de Capacitación " + estadocorreo + " por la Dirección de Talento humano"
                            send_html_mail(tituloemail,
                                           "emails/aprobacion_capadmtra.html",
                                           {'sistema': u'SAGEST - UNEMI',
                                            'administrativo': capacitacion.administrativo.persona,
                                            'numero': capacitacion.id,
                                            'solicitud': capacitacion,
                                            'cronograma': capacitacion.cronograma,
                                            'estadoap': estado,
                                            'observacionap': request.POST['obse'],
                                            'aprueba': 'la Dirección de Talento humano',
                                            'textoadicional': '',
                                            'fecha': datetime.now().date(),
                                            'hora': datetime.now().time(),
                                            't': miinstitucion()},
                                           capacitacion.administrativo.persona.lista_emails_envio(),
                                           [],
                                           cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                           )

                        if autoridad2 and estado == 5:
                            tituloemail = 'Legalización de Solicitud de capacitación - LOSEP y Código de Trabajo'
                            send_html_mail(tituloemail,
                                           "emails/notificacion_capadmtra.html",
                                           {'sistema': u'SAGEST - UNEMI',
                                            'fase': fase,
                                            'fecha': datetime.now().date(),
                                            'hora': datetime.now().time(),
                                            'numero': capacitacion.id,
                                            'solicitud': capacitacion,
                                            'cronograma': capacitacion.cronograma,
                                            'administrativo': capacitacion.administrativo.persona,
                                            'autoridad1': persona,
                                            'autoridad2': autoridad2.persona,
                                            't': miinstitucion()
                                            },
                                           autoridad2.persona.lista_emails_envio(),
                                           [],
                                           cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                           )

                    log(u'Adiciono recorrido en solicitud de capacitaciones: %s - %s - Estado %s' % (recorridocap.planificarcapacitaciones, recorridocap.persona, recorridocap.estado), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "%s" % (mensaje)})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar recorrido de solicitud"})

        elif action == 'confirmarejecutadocap':
            try:
                form = ConfirmarEjecutadoCapacitacionesForm(request.POST)
                if form.is_valid():
                    capacitacion = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.POST['id'])))
                    observacion = form.cleaned_data['observacion'].strip().upper()
                    estado = int(form.cleaned_data['estado'])

                    capacitacion.estado = estado
                    capacitacion.save()

                    recorridocap = PlanificarCapacitacionesRecorrido(planificarcapacitaciones=capacitacion,
                                                                     observacion=observacion,
                                                                     estado=estado,
                                                                     fecha=datetime.now().date(),
                                                                     persona=persona)
                    recorridocap.save(request)

                    log(u'Actualizó el estado a la solicitud de capacitacion/actualización: %s' % capacitacion, request, "edit")
                    log(u'Adiciono recorrido en solicitud de capacitaciones: %s - %s - Estado %s' % (recorridocap.planificarcapacitaciones, recorridocap.persona, recorridocap.estado), request, "add")

                    # Enviar correo
                    # micorreo = Persona.objects.get(cedula='0923704928')
                    if capacitacion.tipo == 1:
                        send_html_mail("Cambio de Estado de solicitud de capacitación",
                                       "emails/aprobacion_capdocente.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'docente': capacitacion.profesor.persona,
                                        'numero': capacitacion.id,
                                        'solicitud': capacitacion,
                                        'cronograma': capacitacion.cronograma,
                                        'estadoap': estado,
                                        'observacionap': observacion,
                                        'aprueba': 'la Dirección de Talento Humano',
                                        'textoadicional': '',
                                        'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(),
                                        't': miinstitucion()},
                                       capacitacion.profesor.persona.lista_emails_envio(),
                                       [],
                                       cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                       )
                    else:
                        send_html_mail("Cambio de Estado de solicitud de capacitación - Personal LOSEP",
                                       "emails/aprobacion_capadmtra.html",
                                       {'sistema': u'SAGEST - UNEMI',
                                        'docente': capacitacion.administrativo.persona,
                                        'numero': capacitacion.id,
                                        'cronograma': capacitacion.cronograma,
                                        'solicitud': capacitacion,
                                        'estadoap': estado,
                                        'observacionap': observacion,
                                        'aprueba': 'la Dirección de Talento Humano',
                                        'textoadicional': '',
                                        'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(),
                                        't': miinstitucion()},
                                       capacitacion.administrativo.persona.lista_emails_envio(),
                                       [],
                                       cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                       )

                    return JsonResponse({"result": "ok"})
                else:
                    #print (form.errors)
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'subirevidenciaejecutadocap':
            try:
                f = SubirEvidenciaEjecutadoCapacitacionesForm(request.POST, request.FILES)
                newfile = None
                if not 'factura' in request.FILES and not 'certificado' in request.FILES:
                    return JsonResponse({"result": "bad", "mensaje": u"Atención, debe subir mínimo un archivo de las evidencias."})

                if 'factura' in request.FILES:
                    arch = request.FILES['factura']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo de la factura es mayor a 4 Mb."})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if 'certificado' in request.FILES:
                    arch = request.FILES['certificado']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 4194304:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo del certificado es mayor a 4 Mb."})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if f.is_valid():
                    capacitacion = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.POST['id'])))

                    if 'factura' in request.FILES:
                        newfile = request.FILES['factura']
                        newfile._name = generar_nombre("evidejecapfactura", newfile._name)
                        capacitacion.archivofactura = newfile

                    if 'certificado' in request.FILES:
                        newfile = request.FILES['certificado']
                        newfile._name = generar_nombre("evidejecapcertificado", newfile._name)
                        capacitacion.archivocertificado = newfile
                        newfile = request.FILES['certificado']
                        newfile._name = generar_nombre("capacitacion_", newfile._name)
                        if capacitacion.capacitacion is None:
                            capacitacionth = Capacitacion(persona=capacitacion.profesor.persona,
                                                          institucion=capacitacion.institucion,
                                                          nombre=capacitacion.tema,
                                                          anio=datetime.now().date().year,
                                                          pais=capacitacion.pais,
                                                          fechainicio=capacitacion.fechainicio,
                                                          fechafin=capacitacion.fechafin,
                                                          horas=capacitacion.horas,
                                                          modalidad=capacitacion.modalidad,
                                                          tipocapacitacion_id=1,
                                                          archivo=newfile)
                            capacitacionth.save(request)
                            log(u'Adiciono capacitacion: %s' % persona, request, "add")
                            capacitacion.capacitacion = capacitacionth
                        else:
                            capacitacionth = Capacitacion.objects.get(pk=capacitacion.capacitacion.id)
                            capacitacionth.archivo = newfile

                    capacitacion.estado = 14
                    capacitacion.save(request)

                    log(u'Agregó archivos de evidencia de ejecución a la solicitud de capacitacion/actualización: %s' % capacitacion, request, "edit")

                    recorridocap = PlanificarCapacitacionesRecorrido(planificarcapacitaciones=capacitacion,
                                                                     observacion='Agregó archivos de evidencia de capacitación ejecutada',
                                                                     estado=14,
                                                                     fecha=datetime.now().date(),
                                                                     persona=persona)
                    recorridocap.save(request)
                    log(u'Adiciono recorrido en solicitud de capacitaciones: %s - %s - Estado %s' % (recorridocap.planificarcapacitaciones, recorridocap.persona, recorridocap.estado), request, "add")

                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editcapacitacionth':
            try:
                persona = request.session['persona']
                capacitacion = Capacitacion.objects.get(pk=int(request.POST['id']))
                f = CapacitacionPersonaDocenteForm(request.POST, request.FILES)
                if f.is_valid():
                    capacitacion.institucion = f.cleaned_data['institucion']
                    capacitacion.nombre = f.cleaned_data['nombre']
                    capacitacion.descripcion = f.cleaned_data['descripcion']
                    capacitacion.tipocurso = f.cleaned_data['tipocurso']
                    capacitacion.tipocapacitacion = f.cleaned_data['tipocapacitacion']
                    capacitacion.tipocertificacion = f.cleaned_data['tipocertificacion']
                    capacitacion.tipoparticipacion = f.cleaned_data['tipoparticipacion']
                    capacitacion.areaconocimiento = f.cleaned_data['areaconocimiento']
                    capacitacion.subareaconocimiento = f.cleaned_data['subareaconocimiento']
                    capacitacion.subareaespecificaconocimiento = f.cleaned_data['subareaespecificaconocimiento']
                    capacitacion.pais = f.cleaned_data['pais']
                    capacitacion.provincia = f.cleaned_data['provincia']
                    capacitacion.canton = f.cleaned_data['canton']
                    capacitacion.parroquia = f.cleaned_data['parroquia']
                    capacitacion.fechainicio = f.cleaned_data['fechainicio']
                    capacitacion.fechafin = f.cleaned_data['fechafin']
                    capacitacion.horas = f.cleaned_data['horas']
                    capacitacion.modalidad = f.cleaned_data['modalidad']
                    capacitacion.otramodalidad = f.cleaned_data['otramodalidad']
                    capacitacion.save(request)
                    solicitud = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.POST['idsolicitud'])))
                    solicitud.infocompletacap = True
                    solicitud.save(request)
                    log(u'Modifico capacitacion: %s' % persona, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'devolucion':
            try:
                f = PlanificarCapacitacionesDevolucionForm(request.FILES)
                newfile = None

                montodevolucion = Decimal(request.POST['devolucion']).quantize(Decimal('0.00'))
                costo = Decimal(request.POST['costo']).quantize(Decimal('0.00'))
                estado = int(request.POST['tipo'])
                observacion = request.POST['observaciondev'].upper()

                if estado == 12:
                    if montodevolucion != costo:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el monto de devolución debe ser %s." % (str(costo))})
                else:
                    if montodevolucion <= 0 or montodevolucion >= costo:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el monto de devolución debe ser mayor a 0 y menor a %s." % (str(costo))})

                if 'archivodevolucion' in request.FILES:
                    arch = request.FILES['archivodevolucion']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 10485760:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, debe subir un archivo."})

                if f.is_valid():
                    solicitud = PlanificarCapacitaciones.objects.get(pk=int(request.POST['id']))
                    if 'archivodevolucion' in request.FILES:
                        newfile = request.FILES['archivodevolucion']
                        newfile._name = generar_nombre("devolucion", newfile._name)
                        solicitud.archivodevolucion = newfile

                    solicitud.devolucion = montodevolucion
                    solicitud.costoneto = solicitud.costo - montodevolucion
                    solicitud.estado = estado
                    solicitud.save(request)

                    log(u'Agregó archivo de devolución a la solicitud de capacitacion/actualización: %s' % solicitud,
                    request, "edit")

                    recorridocap = PlanificarCapacitacionesRecorrido(planificarcapacitaciones=solicitud,
                                                                     observacion=observacion,
                                                                     estado=estado,
                                                                     fecha=datetime.now().date(),
                                                                     persona=persona)
                    recorridocap.save(request)

                    log(u'Adiciono recorrido en solicitud de capacitaciones: %s - %s - Estado %s' % (recorridocap.planificarcapacitaciones, recorridocap.persona, recorridocap.estado), request, "add")

                    if estado == 12:
                        solicitud.estado = 16
                        solicitud.save()

                        recorridocap = PlanificarCapacitacionesRecorrido(planificarcapacitaciones=solicitud,
                                                                         observacion='CAPACITACIÓN NO EJECUTADA',
                                                                         estado=16,
                                                                         fecha=datetime.now().date(),
                                                                         persona=persona)
                        recorridocap.save(request)

                        log(u'Adiciono recorrido en solicitud de capacitaciones: %s - %s - Estado %s' % (
                        recorridocap.planificarcapacitaciones, recorridocap.persona, recorridocap.estado), request,
                            "add")


                    # Enviar correo
                    #micorreo = Persona.objects.get(cedula='0923704928')
                    if solicitud.tipo == 1:
                        send_html_mail("Cambio de Estado de solicitud de capacitación",
                                       "emails/aprobacion_capdocente.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'docente': solicitud.profesor.persona,
                                        'numero': solicitud.id,
                                        'solicitud': solicitud,
                                        'cronograma': solicitud.cronograma,
                                        'estadoap': estado,
                                        'observacionap': request.POST['observaciondev'],
                                        'aprueba': 'la Dirección de Talento Humano',
                                        'textoadicional': '',
                                        'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(),
                                        't': miinstitucion()},
                                       solicitud.profesor.persona.lista_emails_envio(),
                                       [],
                                       [solicitud.archivodevolucion],
                                       cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                       )
                    else:
                        send_html_mail("Cambio de Estado de solicitud de capacitación - LOSEP y Código de Trabajo",
                                       "emails/aprobacion_capdadmtra.html",
                                       {'sistema': u'SAGEST - UNEMI',
                                        'docente': solicitud.administrativo.persona,
                                        'cronograma': solicitud.cronograma,
                                        'solicitud': solicitud,
                                        'numero': solicitud.id,
                                        'estadoap': estado,
                                        'observacionap': request.POST['observaciondev'],
                                        'aprueba': 'la Dirección de Talento Humano',
                                        'textoadicional': '',
                                        'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(),
                                        't': miinstitucion()},
                                       solicitud.administrativo.persona.lista_emails_envio(),
                                       [],
                                       [solicitud.archivodevolucion],
                                       cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                       )


                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'descuentorol':
            try:
                f = DescuentoRolForm(request.FILES)
                newfile = None
                motivo = int(request.POST['motivo'])
                if motivo == 0:
                    return JsonResponse({"result": "bad", "mensaje": u"Seleccione el motivo"})

                estado = 18 if motivo == 1 else 19
                observacion = request.POST['observaciondes'].upper()

                if 'archivodescuentorol' in request.FILES:
                    arch = request.FILES['archivodescuentorol']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 10485760:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                if f.is_valid():
                    solicitud = PlanificarCapacitaciones.objects.get(pk=int(request.POST['idsol']))
                    if 'archivodescuentorol' in request.FILES:
                        newfile = request.FILES['archivodescuentorol']
                        newfile._name = generar_nombre("descuentorol", newfile._name)
                        solicitud.archivodescuentorol = newfile

                    solicitud.estado = estado
                    solicitud.save(request)

                    log(u'Cambio de estado a la solicitud de capacitacion/actualización: %s' % solicitud, request, "edit")

                    recorridocap = PlanificarCapacitacionesRecorrido(planificarcapacitaciones=solicitud,
                                                                     observacion=observacion,
                                                                     estado=estado,
                                                                     fecha=datetime.now().date(),
                                                                     persona=persona)
                    recorridocap.save(request)

                    log(u'Adiciono recorrido en solicitud de capacitaciones: %s - %s - Estado %s' % (recorridocap.planificarcapacitaciones, recorridocap.persona, recorridocap.estado), request, "add")

                    # Enviar correo
                    #micorreo = Persona.objects.get(cedula='0923704928')

                    texto_adicional = "Nota: Se realizará el descuento en el rol del pago por el monto del valor otorgado para la actualización académica, de conformidad a lo estipulado en el convenio de devengación."
                    send_html_mail("Solicitud de capacitación - Registro Descuento en Rol de pago",
                                   "emails/aprobacion_capdocente.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'docente': solicitud.profesor.persona,
                                    'numero': solicitud.id,
                                    'solicitud': solicitud,
                                    'cronograma': solicitud.cronograma,
                                    'estadoap': estado,
                                    'observacionap': request.POST['observaciondes'],
                                    'aprueba': 'la Dirección de Talento Humano',
                                    'textoadicional': texto_adicional,
                                    'fecha': datetime.now().date(),
                                    'hora': datetime.now().time(),
                                    't': miinstitucion()},
                                   solicitud.profesor.persona.lista_emails_envio(),
                                   [],
                                   [solicitud.archivodescuentorol if solicitud.archivodescuentorol else ''],
                                   cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                   )

                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'detallecap':
            try:
                data['fase'] = request.POST['fase']
                data['capacitacion'] = capacitacion = PlanificarCapacitaciones.objects.get(id=request.POST['id'])
                data['capacitaciondetallecriterio'] = capacitacion.planificarcapacitacionesdetallecriterios_set.filter(status=True).order_by('criterio_id')
                data['capacitacionrecorrido'] = capacitacion.planificarcapacitacionesrecorrido_set.filter(status=True).order_by('id')

                # if capacitacion.tipo == 1:
                template = get_template("adm_capdocente/detallecapacitacion.html")
                # else:
                #     template = get_template("adm_capacitacion/detallecapacitacion.html")

                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'editperiodo':
            try:
                if 'modeloinforme' in request.FILES:
                    descripcionarchivo = 'Modelo Informe'
                    resp = validar_archivo(descripcionarchivo, request.FILES['modeloinforme'], ['doc', 'docx'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'resolucionocas' in request.FILES:
                    descripcionarchivo = 'Resolución OCAS'
                    resp = validar_archivo(descripcionarchivo, request.FILES['resolucionocas'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'instructivo' in request.FILES:
                    descripcionarchivo = 'Instructivo'
                    resp = validar_archivo(descripcionarchivo, request.FILES['instructivo'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                if 'manualusuario' in request.FILES:
                    descripcionarchivo = 'Manual de usuario'
                    resp = validar_archivo(descripcionarchivo, request.FILES['manualusuario'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                # if 'conveniodevengacion' in request.FILES:
                #     descripcionarchivo = 'Convenio de devengación'
                #     resp = validar_archivo(descripcionarchivo, request.FILES['conveniodevengacion'], ['doc', 'docx'], '4MB')
                #     if resp['estado'] != "OK":
                #         return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})
                if 'manualregistroevidencia' in request.FILES:
                    descripcionarchivo = 'Manual de registro de evidencia'
                    resp = validar_archivo(descripcionarchivo, request.FILES['manualregistroevidencia'], ['pdf'], '4MB')
                    if resp['estado'] != "OK":
                        return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                form = CapDocentePeriodoForm(request.POST, request.FILES)

                if form.is_valid():
                    if form.cleaned_data['inicio'] < form.cleaned_data['fin']:
                        if form.cleaned_data['fin'].month > 9:
                            return JsonResponse({"result": "bad", "mensaje": u"El mes de la fecha de fin no debe superar Septiembre"})

                        if form.cleaned_data['fin'].year != form.cleaned_data['inicio'].year:
                            return JsonResponse({"result": "bad", "mensaje": u"El año de la fecha de inicio y fin deben ser iguales"})

                        if form.cleaned_data['monto']:
                            if form.cleaned_data['monto'] <= 0:
                                return JsonResponse({"result": "bad", "mensaje": u"El monto debe ser mayor a $ 0.00"})

                        if form.cleaned_data['iniciocapacitacion'] < form.cleaned_data['inicio']:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio de capacitación debe ser mayor o igual que la fecha inicio del cronograma"})

                        if form.cleaned_data['iniciocapacitacion'] > form.cleaned_data['fincapacitacion']:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha de fin de capacitación debe ser mayor que la fecha de inicio"})


                        periodo = CronogramaCapacitacionDocente.objects.get(pk=int(request.POST['id']))
                        periodo.descripcion = form.cleaned_data['descripcion'].upper()
                        periodo.resolucion = form.cleaned_data['resolucion'].upper()
                        periodo.inicio = form.cleaned_data['inicio']
                        periodo.fin = form.cleaned_data['fin']
                        periodo.iniciocapacitacion = form.cleaned_data['iniciocapacitacion']
                        periodo.fincapacitacion = form.cleaned_data['fincapacitacion']
                        periodo.iniciocapacitaciontecdoc = form.cleaned_data['iniciocapacitaciontecdoc']
                        periodo.fincapacitaciontecdoc = form.cleaned_data['fincapacitaciontecdoc']
                        periodo.fechaconvenio=form.cleaned_data['fechaconvenio']

                        if form.cleaned_data['monto']:
                            periodo.monto = form.cleaned_data['monto']
                            periodo.tipo = form.cleaned_data['tipo']

                        if 'modeloinforme' in request.FILES:
                            arch = request.FILES['modeloinforme']
                            arch._name = generar_nombre("informecomisioncap", arch._name)
                            periodo.modeloinforme = arch

                        if 'resolucionocas' in request.FILES:
                            arch = request.FILES['resolucionocas']
                            arch._name = generar_nombre("resolucionocas", arch._name)
                            periodo.resolucionocas = arch

                        if 'instructivo' in request.FILES:
                            arch = request.FILES['instructivo']
                            arch._name = generar_nombre("instructivo", arch._name)
                            periodo.instructivo = arch

                        if 'manualusuario' in request.FILES:
                            arch = request.FILES['manualusuario']
                            arch._name = generar_nombre("manualusuario", arch._name)
                            periodo.manualusuario = arch

                        # if 'conveniodevengacion' in request.FILES:
                        #     arch = request.FILES['conveniodevengacion']
                        #     arch._name = generar_nombre("conveniodevengacion", arch._name)
                        #     periodo.conveniodevengacion = arch
                        if 'manualregistroevidencia' in request.FILES:
                            arch = request.FILES['manualregistroevidencia']
                            arch._name = generar_nombre("manualregistroevidencia", arch._name)
                            periodo.manualregistroevidencia = arch

                        periodo.save(request)
                        log(u'Editar Período de Cronograma de capacitaciones: %s - [%s]' % (periodo, periodo.id), request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"La Fecha de inicio debe ser menor a la fecha fin."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'conveniodevengacion_pdf':
            try:
                data = {}

                idsolicitud = request.POST['id']

                data['dth'] = dth = DistributivoPersona.objects.get(denominacionpuesto_id=83, estadopuesto_id=1, status=True)


                titulos = dth.persona.titulo3y4nivel()
                # tit1 = tit2 = ""
                # tit1th = None
                # dir = dth.persona.titulacion_principal_senescyt_registro()
                # if not dir is '':
                #     tit1th = dth.persona.titulacion_set.filter(titulo__nivel_id=3).order_by('-fechaobtencion')[0]
                #     tit1 = tit1th.titulo.abreviatura
                #     tit1 = tit1 + "." if tit1.find(".") < 0 else tit1
                #
                # tit2th = dth.persona.titulacion_principal_senescyt_registro()
                # if tit2th:
                #     tit2 = tit2th.titulo.abreviatura if tit2th.titulo.nivel_id == 4 else ''
                #     if tit2 != '':
                #         tit2 = tit2 + "." if tit2.find(".") < 0 else tit2
                #
                # if tit1 != "":
                #     if tit2 != "":
                #         tit2 = ", " + tit2
                # else:
                #     if tit2 != "":
                #         tit1 = tit2
                #         tit2 = ""

                data['titulo1dth'] = titulos['tit1']
                data['titulo2dth'] = titulos['tit2']
                data['capacitacion'] = capacitacion = PlanificarCapacitaciones.objects.get(id=idsolicitud)

                titulos = capacitacion.profesor.persona.titulo3y4nivel()

                # tit1 = tit2 = ""
                # tit1doc = None
                #
                #
                #
                # doc = capacitacion.profesor.persona.titulacion_principal_senescyt_registro()
                # if not doc is '':
                #     if Titulacion.objects.filter(titulo__nivel_id=3, persona=doc.persona).exists():
                #         tit1th = \
                #         Titulacion.objects.filter(titulo__nivel_id=3, persona=doc.persona).order_by('-fechaobtencion')[
                #             0]
                #         tit1 = tit1th.titulo.abreviatura
                #         tit1 = tit1 + "." if tit1.find(".") < 0 else tit1
                #
                # tit2doc = capacitacion.profesor.persona.titulacion_principal_senescyt_registro()
                # if tit2doc:
                #     tit2 = tit2doc.titulo.abreviatura if tit2doc.titulo.nivel_id == 4 else ''
                #     if tit2 != '':
                #         tit2 = tit2 + "." if tit2.find(".") < 0 else tit2
                #
                # if tit1 != "":
                #     if tit2 != "":
                #         tit2 = ", " + tit2
                # else:
                #     if tit2 != "":
                #         tit1 = tit2
                #         tit2 = ""

                data['numeroconvenio'] = "N° " + str(capacitacion.numeroconvenio).zfill(3) + ".DEPA.LOES." + str(capacitacion.fechaconvenio.year)
                data['fechaconvenio'] = fechaletra_corta(capacitacion.fechaconvenio)
                data['titulo1bene'] = titulos['tit1']
                data['titulo2bene'] = titulos['tit2']
                data['fechainiciocap'] = str(capacitacion.fechainicio.day) + " de " + MESES_CHOICES[capacitacion.fechainicio.month - 1][1].capitalize() + " del " + str(capacitacion.fechainicio.year)
                data['fechafincap'] = str(capacitacion.fechafin.day) + " de " + MESES_CHOICES[capacitacion.fechafin.month - 1][1].capitalize() + " del " + str(capacitacion.fechafin.year)
                return conviert_html_to_pdf(
                    'adm_capdocente/conveniodevengacion_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass
        elif action == 'preview_conveniodevengacion_pdf':
            try:
                data = {}
                data['dvice'] = dth = Departamento.objects.get(pk=158)
                idsolicitud = request.POST['id']
                # data['dth'] = dth = DistributivoPersona.objects.get(denominacionpuesto_id=83, estadopuesto_id=1, status=True)
                titulos = dth.responsable.titulo3y4nivel()
                data['titulo1dth'] = titulos['tit1']
                data['titulo2dth'] = titulos['tit2']
                data['capacitacion'] = capacitacion = PlanificarCapacitaciones.objects.get(id=idsolicitud)
                data['cronograma'] = cronograma = capacitacion.cronograma
                data['monto_natural'] = num2words(cronograma.monto, lang='es')
                hoy = datetime.now().date()
                data['fecha_natural'] = {'dia': num2words(hoy.day, lang='es'), 'mes': MESES_CHOICES[hoy.month - 1][1], 'anio': num2words(hoy.year, lang='es')}
                titulos = capacitacion.profesor.persona.titulo3y4nivel()
                data['numeroconvenio'] = "N° " + str(capacitacion.numeroconvenio).zfill(3) + ".DEPA.LOES." + str(capacitacion.fechaconvenio.year)
                data['fechaconvenio'] = fechaletra_corta(capacitacion.fechaconvenio)
                data['titulo1bene'] = titulos['tit1']
                data['titulo2bene'] = titulos['tit2']
                data['fechainiciocap'] = str(capacitacion.fechainicio.day) + " de " + MESES_CHOICES[capacitacion.fechainicio.month - 1][1].capitalize() + " del " + str(capacitacion.fechainicio.year)
                data['fechafincap'] = str(capacitacion.fechafin.day) + " de " + MESES_CHOICES[capacitacion.fechafin.month - 1][1].capitalize() + " del " + str(capacitacion.fechafin.year)
                return conviert_html_to_pdf(
                    'pro_cronograma/conveniodevengacion_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        elif action == 'editcapacitacion':
            try:
                form = PlanificarCapacitacionesForm(request.POST, request.FILES)
                convocatoria = CronogramaCapacitacionDocente.objects.get(pk=int(request.POST['convocatoria']))
                fechainicio = str(convocatoria.iniciocapacitacion)
                fechainicio = fechainicio[8:10] + '-' + fechainicio[5:7] + '-' + fechainicio[0:4]
                fechafin = str(convocatoria.fincapacitacion)
                fechafin = fechafin[8:10] + '-' + fechafin[5:7] + '-' + fechafin[0:4]
                solicitud = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.POST['id'])))
                costosolcap = solicitud.costo
                saldo = null_to_decimal(convocatoria.monto - (convocatoria.totalmonto_profesor(profesor=solicitud.profesor, convocatoria=convocatoria) - costosolcap))
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})
                if form.is_valid():
                    if form.cleaned_data['fechainicio'] < convocatoria.iniciocapacitacion:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio debe ser mayor o igual a %s" % (fechainicio)})
                    if form.cleaned_data['fechafin'] > convocatoria.fincapacitacion:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha de fin debe ser menor o igual a %s" % (fechafin)})
                    if form.cleaned_data['fechainicio'] > form.cleaned_data['fechafin']:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha de inicio deber ser menor o igual a la fecha fin"})
                    if form.cleaned_data['horas'] <= 0:
                        return JsonResponse({"result": "bad", "mensaje": u"El número de horas debe ser mayor a 0"})
                    if form.cleaned_data['costo'] <= 0:
                        return JsonResponse({"result": "bad", "mensaje": u"El costo debe ser mayor a $ 0.00"})
                    costo = Decimal(form.cleaned_data['costo']).quantize(Decimal('0.00'))
                    if costo > saldo:
                        return JsonResponse({"result": "bad", "mensaje": u"El costo supera el monto disponible: $ %s" % saldo})
                    lista = json.loads(request.POST['lista_items1'])
                    for l in lista:
                        if l['obligatorio'] is True and l['valor'] is False:
                            return JsonResponse({"result": "bad", "mensaje": u'El criterio "%s" es obligatorio de marcar' % l['criterio']})
                    solicitud = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.POST['id'])))
                    solicitud.tema = form.cleaned_data['tema']
                    solicitud.justificacion = form.cleaned_data['justificacion']
                    solicitud.institucion = form.cleaned_data['institucion'].upper()
                    solicitud.link = form.cleaned_data['link']
                    solicitud.fechainicio = form.cleaned_data['fechainicio']
                    solicitud.fechafin = form.cleaned_data['fechafin']
                    solicitud.pais = form.cleaned_data['pais']
                    solicitud.modalidad = form.cleaned_data['modalidad']
                    solicitud.costo = form.cleaned_data['costo']
                    solicitud.costoneto = form.cleaned_data['costo']
                    solicitud.horas = form.cleaned_data['horas']
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("archivocapacitaciondocente", newfile._name)
                        solicitud.archivo = newfile
                    solicitud.save(request)
                    if 'lista_items1' in request.POST:
                        lista = json.loads(request.POST['lista_items1'])
                        for l in lista:
                            detallecriterios = PlanificarCapacitacionesDetalleCriterios.objects.get(pk=int(l['id']))
                            detallecriterios.estadodocente = l['valor']
                            detallecriterios.save()
                    log(u'Editó solicitud de capacitacion/actualización: %s' % solicitud, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addarchivoconvenio':
            try:
                f = PlanificarCapacitacionesArchivoForm(request.FILES)
                newfile = None
                if 'archivoconvenio' in request.FILES:
                    arch = request.FILES['archivoconvenio']
                    extension = arch._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if arch.size > 10485760:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                    if not exte.lower() == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, debe subir un archivo."})

                if f.is_valid():
                    solicitud = PlanificarCapacitaciones.objects.get(pk=int(request.POST['idarchivofirmado']))
                    newfile = request.FILES['archivoconvenio']
                    newfile._name = generar_nombre("conveniofirmadovice", newfile._name)
                    solicitud.archivoconveniofirmadovice = newfile
                    solicitud.save(request)
                    log(u'Agregó archivo de conveniofirmado por vicerector a la solicitud de capacitacion/actualización: %s' % solicitud, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'anulasolicitud':
            try:
                solicitud = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.POST['id'])))
                recorridocap = PlanificarCapacitacionesRecorrido(planificarcapacitaciones=solicitud,
                                                                 observacion=request.POST['observacion'],
                                                                 estado=20,
                                                                 fecha=datetime.now().date(),
                                                                 persona=persona)
                recorridocap.save(request)
                solicitud.estado = 20
                solicitud.save(request)
                log(u'Anuló solicitud: %s - [%s]' % (solicitud, solicitud.id), request, "anular")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al anular solicitud los datos."})


        elif action == 'generarnuevoconvenio':
            try:
                capacitacion = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.POST['id'])))
                capacitacion.archivoconvenio = None
                capacitacion.numeroconvenio = None
                capacitacion.archivoconveniofirmadovice = None
                capacitacion.nuevoconvenio = True
                capacitacion.estado = 4
                capacitacion.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar nuevo convenio."})

        elif action == 'finalizarsolicitud':
            try:
                solicitud = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.POST['id'])))
                if solicitud.finalizarproceso:
                    solicitud.finalizarproceso = False
                else:
                    solicitud.finalizarproceso = True
                solicitud.save(request)
                log(u'Finalizó solicitud: %s - [%s]' % (solicitud, solicitud.id), request, "finalizar")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al anular solicitud los datos."})

        elif action == 'delperiodo':
            try:
                periodo = CronogramaCapacitacionDocente.objects.get(pk=int(request.POST['id']))
                # if periodo.esta_cap_evento_periodo_activo():
                #     return JsonResponse({"result": "bad","mensaje": u"No se puede Eliminar el Periodo, tiene planificacion de evento Activas.."})
                log(u'Elimino Período de Cronograma de capacitaciones: %s - [%s]' % (periodo, periodo.id), request, "del")
                periodo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'verificalistadosolicitudaut_pdf':
            try:
                if datetime.strptime(request.POST['desde'], '%d-%m-%Y') <= datetime.strptime(request.POST['hasta'], '%d-%m-%Y'):
                    iddepartamento = int(request.POST['departamento'])
                    desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)
                    estado = int(request.POST['estado'])

                    participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma__tipo=2, fecha_creacion__range=(desde, hasta)).order_by('-fecha_creacion', 'administrativo__persona__apellido1')
                    codigospersonas = DistributivoPersona.objects.values_list('persona__id', flat=True).filter(unidadorganica_id=iddepartamento, status=True, estadopuesto_id=1)
                    participantes = participantes.filter(administrativo__persona__id__in=codigospersonas)

                    if estado == 9 or estado == 3:
                        if participantes.filter(estado=estado).exists():
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                    elif estado == 4:
                        if participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20])).exists():
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                    else:
                        if participantes.filter(estado__in=[3, 9]).exists() or participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20])).exists():
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "La fecha desde debe ser menor o igual a la fecha hasta"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Formatos de fechas incorrectas."})

        elif action == 'listadosolicitudaut_pdf':
            try:
                data = {}

                iddepartamento = int(request.POST['departamento'])
                desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)
                estado = int(request.POST['estado'])
                departamentosol = Departamento.objects.get(pk=iddepartamento)

                participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma__tipo=2, fecha_creacion__range=(desde, hasta))
                codigospersonas = DistributivoPersona.objects.values_list('persona__id', flat=True).filter(unidadorganica=departamentosol, status=True, estadopuesto_id=1)
                participantes = participantes.filter(administrativo__persona__id__in=codigospersonas)

                if estado == 9 or estado == 3:
                    participantes = participantes.filter(estado=estado)
                elif estado == 4:
                    participantes = participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20]))
                else:
                    p1 = participantes.filter(estado__in=[3, 9])
                    p2 = participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20]))
                    participantes = p1 | p2

                participantes = participantes.order_by('-fecha_creacion', 'administrativo__persona__apellido1')

                calculo = participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20])).aggregate(total=Sum('costo'))
                totsol = participantes.count()
                totaut = participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20])).count()
                totden = participantes.filter(estado=9).count()
                totpend = totsol - (totaut + totden)

                #Vicerrector administrativo
                dpvice = DistributivoPersona.objects.filter(denominacionpuesto_id=114, estadopuesto_id=1, status=True).order_by('estadopuesto_id')[0]
                personavice = dpvice.persona
                titulos = personavice.titulo3y4nivel()

                data['titulo1vice'] = titulos['tit1']
                data['titulo2vice'] = titulos['tit2']
                data['denominacionpuestovice'] = dpvice.denominacionpuesto.descripcion
                data['vicerrector'] = personavice
                data['nombredptovice'] = dpvice.unidadorganica

                # Jefe departamento solicitante
                dpjefe = DistributivoPersona.objects.filter(persona=departamentosol.responsable, unidadorganica=departamentosol, estadopuesto_id=1, status=True).order_by('estadopuesto_id')[0]
                personajefe = dpjefe.persona
                titulos = personajefe.titulo3y4nivel()

                data['titulo1jefe'] = titulos['tit1']
                data['titulo2jefe'] = titulos['tit2']
                data['denominacionpuestojefe'] = dpjefe.denominacionpuesto.descripcion
                data['jefe'] = personajefe

                data['desde'] = request.POST['desde']
                data['hasta'] = request.POST['hasta']
                data['departamento'] = departamentosol
                data['participantes'] = participantes
                data['costoacumulado'] = calculo['total'] if calculo['total'] is not None else 0.00
                data['estadoreporte'] = ' Autorizadas' if estado == 4 else ' Denegadas' if estado == 9 else ''
                data['estado'] = estado
                data['totsol'] = totsol
                data['totaut'] = totaut
                data['totden'] = totden
                data['totpend'] = totpend

                return conviert_html_to_pdf(
                    'adm_capacitacion/listadosolicitudaut_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )

            except Exception as ex:
                pass

        elif action == 'verificalistadosolicitudloes_pdf':
            try:
                if datetime.strptime(request.POST['desde'], '%d-%m-%Y') <= datetime.strptime(request.POST['hasta'], '%d-%m-%Y'):
                    desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)
                    periodosol = Periodo.objects.get(pk=int(request.POST['periodo']))
                    facultadsol = Coordinacion.objects.get(pk=int(request.POST['facultad']))
                    estado = int(request.POST['estado'])
                    codigosprofesores = facultadsol.profesordistributivohoras_set.values_list('profesor__id', flat=True).filter(periodo=periodosol, status=True)

                    # participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma__tipo=1, fecha_creacion__range=(desde, hasta), periodo=periodosol, profesor_id__in=codigosprofesores)
                    if estado != 0:
                        participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma__tipo=1, periodo=periodosol, profesor_id__in=codigosprofesores,
                                                                                planificarcapacitacionesrecorrido__fecha__range=(desde, hasta),
                                                                                planificarcapacitacionesrecorrido__estado=estado,
                                                                                planificarcapacitacionesrecorrido__status=True)

                        if estado == 3:
                            participantes = participantes.exclude(planificarcapacitacionesrecorrido__estado__in=[4, 9])
                        # elif estado == 9:
                        #     participantes = participantes.exclude(planificarcapacitacionesrecorrido__estado__in=[3, 4])
                    else:
                        participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma__tipo=1, periodo=periodosol,
                                                                                profesor_id__in=codigosprofesores,
                                                                                planificarcapacitacionesrecorrido__fecha__range=(desde, hasta),
                                                                                planificarcapacitacionesrecorrido__estado__in=[3, 4, 9],
                                                                                planificarcapacitacionesrecorrido__status=True)

                    if participantes:
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse(
                            {"result": "bad", "mensaje": "No existen registros para generar el reporte"})

                    # if estado == 9 or estado == 3:
                    #     if participantes.filter(estado=estado).exists():
                    #         return JsonResponse({"result": "ok"})
                    #     else:
                    #         return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                    # elif estado == 4:
                    #     if participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20])).exists():
                    #         return JsonResponse({"result": "ok"})
                    #     else:
                    #         return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                    # else:
                    #     if participantes.filter(estado__in=[3, 9]).exists() or participantes.filter(
                    #             ~Q(estado__in=[1, 2, 3, 7, 8, 9, 20])).exists():
                    #         return JsonResponse({"result": "ok"})
                    #     else:
                    #         return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "La fecha desde debe ser menor o igual a la fecha hasta"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Formatos de fechas incorrectas."})

        elif action == 'listadosolicitudloesaut_pdf':
            try:
                data = {}

                desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)
                periodosol = Periodo.objects.get(pk=int(request.POST['periodo']))
                facultadsol = Coordinacion.objects.get(pk=int(request.POST['facultad']))
                estado = int(request.POST['estado'])

                codigosprofesores = facultadsol.profesordistributivohoras_set.values_list('profesor__id', flat=True).filter(periodo=periodosol, status=True, carrera_id__isnull=False)


                # participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma__tipo=1, fecha_creacion__range=(desde, hasta), periodo=periodosol, profesor_id__in=codigosprofesores)
                if estado == 0:
                    participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma__tipo=1, periodo=periodosol, profesor_id__in=codigosprofesores,
                                                                            planificarcapacitacionesrecorrido__fecha__range=(desde, hasta),
                                                                            planificarcapacitacionesrecorrido__status=True,
                                                                            planificarcapacitacionesrecorrido__estado__in=[3, 4, 9]).distinct()
                else:
                    participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma__tipo=1, periodo=periodosol, profesor_id__in=codigosprofesores,
                                                                            planificarcapacitacionesrecorrido__fecha__range=(desde, hasta),
                                                                            planificarcapacitacionesrecorrido__status=True,
                                                                            planificarcapacitacionesrecorrido__estado=estado).distinct()

                    if estado == 3:
                        participantes = participantes.exclude(planificarcapacitacionesrecorrido__estado__in=[4, 9])
                    # elif estado == 9:
                    #     participantes = participantes.exclude(planificarcapacitacionesrecorrido__estado__in=[3, 4])


                # if estado == 9 or estado == 3:
                #     participantes = participantes.filter(estado=estado)
                # elif estado == 4:
                #     participantes = participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20]))
                # else:
                #     p1 = participantes.filter(estado__in=[3, 9])
                #     p2 = participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20]))
                #     participantes = p1 | p2

                participantes = participantes.order_by('-fecha_creacion', 'profesor__persona__apellido1')

                codigoscarreras = facultadsol.profesordistributivohoras_set.values_list('carrera__id', flat=True).filter(periodo=periodosol, status=True, carrera_id__isnull=False, profesor_id__in=participantes.values_list('profesor_id', flat=True).distinct()).distinct()

                calculo = participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20])).aggregate(total=Sum('costo'))
                totsol = participantes.count()
                totaut = participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20])).count()
                totden = participantes.filter(estado=9).count()
                totpend = totsol - (totaut + totden)

                # Vicerrector académico
                dpvice = DistributivoPersona.objects.filter(denominacionpuesto_id=115, estadopuesto_id=1, status=True).order_by('estadopuesto_id')[0]
                personavice = dpvice.persona
                titulos = personavice.titulo3y4nivel()
                tit1 = titulos['tit1']
                tit2 = titulos['tit2']

                data['titulo1vice'] = tit1
                data['titulo2vice'] = tit2
                data['denominacionpuestovice'] = dpvice.denominacionpuesto.descripcion
                data['vicerrector'] = personavice
                data['nombredptovice'] = dpvice.unidadorganica

                # Decano de facultad
                dpdeca = ResponsableCoordinacion.objects.filter(periodo=periodosol, coordinacion=facultadsol)[0]
                personadecano = dpdeca.persona
                titulos = personadecano.titulo3y4nivel()
                tit1 = titulos['tit1']
                tit2 = titulos['tit2']

                data['titulo1decano'] = tit1
                data['titulo2decano'] = tit2
                data['denominacionpuestodecano'] = "DECANA" if personadecano.sexo.id == 1 else "DECANO"
                data['decano'] = personadecano

                # Directores de carrera
                directores = CoordinadorCarrera.objects.values_list('persona__id', 'persona__apellido1','persona__apellido2','persona__nombres','carrera__nombre').filter(carrera_id__in=codigoscarreras, periodo=periodosol, status=True).order_by('carrera__nombre')
                dircar = []
                fila = []
                c = 1
                for dc in directores:
                    titulos = Persona.objects.get(pk=dc[0]).titulo3y4nivel()
                    dato = [dc[1] + ' ' + dc[2] + ' ' + dc[3], dc[4], titulos['tit1'], titulos['tit2']]
                    if c % 4 == 0:
                        aux = fila[:]
                        dircar.append(aux)
                        fila.clear()

                    fila.append(dato)
                    c += 1

                aux = fila[:]
                dircar.append(aux)

                data['desde'] = request.POST['desde']
                data['hasta'] = request.POST['hasta']
                data['facultad'] = facultadsol.nombre + " (" + facultadsol.alias+ ")"
                data['participantes'] = participantes
                data['costoacumulado'] = calculo['total'] if calculo['total'] is not None else 0.00
                data['estadoreporte'] = ' Autorizadas' if estado == 4 else ' Denegadas' if estado == 9 else ' Por autorizar' if estado == 3 else ''
                data['estado'] = estado
                data['totsol'] = totsol
                data['totaut'] = totaut
                data['totden'] = totden
                data['totpend'] = totpend
                data['directores'] = dircar

                return conviert_html_to_pdf(
                    'adm_capdocente/listadosolicitudaut_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )


            except Exception as ex:
                pass



        return HttpResponseRedirect(request.path)

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            #PERIODO
            if action == 'addperiodo':
                try:
                    data['title'] = u'Adicionar Cronograma de capacitaciones/actualizaciones'
                    form = CapDocentePeriodoForm()
                    if persona.grupo_evaluacion():
                        form.esparaacademico()
                    else:
                        form.esparaadministrativo()
                    data['form'] = form

                    return render(request, "adm_capdocente/addperiodo.html", data)
                except Exception as ex:
                    pass

            elif action == 'subirevidenciaejecutadocap':
                try:
                    data['title'] = u'Subir Evidencias de capacitación Ejecutada'
                    solicitud = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.GET['idcap'])))
                    form = SubirEvidenciaEjecutadoCapacitacionesForm()
                    form.quitarcamposevidencia('FAC')
                    data['form'] = form
                    data['tema'] = solicitud.tema
                    data['solicitante'] = solicitud.profesor
                    data['informe'] = solicitud.archivoinforme
                    data['factura'] = solicitud.archivofactura
                    data['certificado'] = solicitud.archivocertificado
                    data['id'] = request.GET['idcap']
                    data['cronograma'] = request.GET['idcron']
                    data['eSol'] = request.GET['eSol']

                    return render(request, "adm_capdocente/subirevidenciaejecutado.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcapacitacionth':
                try:
                    data['title'] = u'Registrar certificado - Hoja de vida'
                    data['convocatoria'] = request.GET['convocatoria']
                    data['idsolicitud'] = request.GET['id']
                    data['capacitacion'] = capacitacion = Capacitacion.objects.get(pk=int(request.GET['idcth']))
                    data['modalidad1'] = capacitacion.modalidad
                    data['cronograma'] = request.GET['idcron']
                    data['eSol'] = request.GET['eSol']
                    form = CapacitacionPersonaDocenteForm(initial={'institucion': capacitacion.institucion,
                                                            'nombre': capacitacion.nombre,
                                                            'descripcion': capacitacion.descripcion,
                                                            'tipocurso': capacitacion.tipocurso,
                                                            'tipocertificacion': capacitacion.tipocertificacion,
                                                            'tipocapacitacion': capacitacion.tipocapacitacion,
                                                            'tipoparticipacion': capacitacion.tipoparticipacion,
                                                            'anio': capacitacion.anio,
                                                            'areaconocimiento': capacitacion.areaconocimiento,
                                                            'subareaconocimiento': capacitacion.subareaconocimiento,
                                                            'subareaespecificaconocimiento': capacitacion.subareaespecificaconocimiento,
                                                            'pais': capacitacion.pais,
                                                            'provincia': capacitacion.provincia,
                                                            'canton': capacitacion.canton,
                                                            'parroquia': capacitacion.parroquia,
                                                            'fechainicio': capacitacion.fechainicio,
                                                            'fechafin': capacitacion.fechafin,
                                                            'horas': capacitacion.horas,
                                                            'modalidad': capacitacion.modalidad,
                                                            'otramodalidad': capacitacion.otramodalidad})
                    form.editar(capacitacion)
                    form.quitar_campo_archivo()
                    data['form'] = form
                    return render(request, "adm_capdocente/editcapacitacionth.html", data)
                except Exception as ex:
                    pass

            elif action == 'confirmarejecutadocap':
                try:
                    data['title'] = u'Revisión de Evidencias de capacitación Ejecutada/Confirmar ejecutado'
                    solicitud = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.GET['idcap'])))
                    form = ConfirmarEjecutadoCapacitacionesForm()
                    form.estados_confirmar()
                    data['form'] = form
                    data['solicitante'] = solicitud.profesor if solicitud.tipo == 1 else solicitud.administrativo
                    data['tema'] = solicitud.tema
                    data['informe'] = solicitud.archivoinforme
                    data['factura'] = solicitud.archivofactura
                    data['certificado'] = solicitud.archivocertificado
                    data['eSol'] = request.GET['eSol']
                    data['capacitacion'] = request.GET['idcap']
                    data['cronograma'] = request.GET['idcron']

                    return render(request, "adm_capdocente/confirmarejecutadocap.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadosolicitud_excel':
                try:
                    cronogramaid = request.GET['id']

                    __author__ = 'Unemi'
                    title2 = easyxf(
                        'font: name Verdana, color-index black, bold on , height 270; alignment: horiz centre')

                    stylec = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre', num_format_str='yyyy-mm-dd')
                    styler2 = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
                    stylel = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz left')
                    styler = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right', num_format_str='#,##0.00')

                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listado')
                    ws.write_merge(0, 0, 0, 16, 'UNIVERSIDAD ESTATAL DE MILAGRO', title2)
                    ws.write_merge(1, 1, 0, 16, 'SOLICITUDES DE CAPACITACIONES/ACTUALIZACIONES DE ACADÉMICOS', title2)

                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=SOLICITUDES_ACADEMICOS ' + cronogramaid.__str__() + '.xls'
                    columns = [
                        (u"NÚMERO SOL.", 3000),
                        (u"FECHA SOL.", 3000),
                        (u"FACULTAD", 9000),
                        (u"CÉDULA", 4000),
                        (u"DOCENTE", 9000),
                        (u"CELULAR", 4000),
                        (u"E-MAIL", 4000),
                        (u"TEMA", 9000),
                        (u"INSTITUCIÓN", 9000),
                        (u"PAÍS", 6000),
                        (u"JUSTIFICACIÓN", 6000),
                        (u"MODALIDAD", 5000),
                        (u"FECHA INICIO", 3000),
                        (u"FECHA FIN", 3000),
                        (u"HORAS", 3000),
                        (u"COSTO", 3000),
                        (u"ESTADO", 4500)
                    ]

                    row_num = 2
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    participantes = PlanificarCapacitaciones.objects.filter(status=True,
                                                                            cronograma=cronogramaid).order_by(
                        '-fecha_creacion', 'profesor__persona__apellido1')

                    row_num += 1
                    cont = 0
                    for p in participantes:
                        cont += 1
                        ws.write(row_num, 0, str(p.id).zfill(6), stylel)
                        ws.write(row_num, 1, p.fecha_creacion, stylec)
                        profesorcoord = ProfesorDistributivoHoras.objects.values_list('coordinacion_id', 'carrera_id').filter(profesor=p.profesor, status=True, periodo=p.periodo)[0]
                        facultad = Coordinacion.objects.get(id=profesorcoord[0])
                        ws.write(row_num, 2, facultad.nombre, stylel)
                        ws.write(row_num, 3, p.profesor.persona.cedula if p.profesor.persona.cedula else p.profesor.persona.pasaporte, stylel)
                        ws.write(row_num, 4, p.profesor.persona.apellido1 + ' ' + p.profesor.persona.apellido2 + ' '+ p.profesor.persona.nombres, stylel)
                        ws.write(row_num, 5, p.profesor.persona.telefono, stylel)
                        ws.write(row_num, 6, p.profesor.persona.emailinst, stylel)
                        ws.write(row_num, 7, p.tema, stylel)
                        ws.write(row_num, 8, p.institucion, stylel)
                        ws.write(row_num, 9, p.pais.nombre if p.pais else '', stylel)
                        ws.write(row_num, 10, p.justificacion, stylel)
                        ws.write(row_num, 11, p.get_modalidad_display(), stylel)
                        ws.write(row_num, 12, p.fechainicio if p.fechainicio else '', stylec)
                        ws.write(row_num, 13, p.fechafin if p.fechafin else '', stylec)
                        ws.write(row_num, 14, p.horas if p.horas else '', styler2)
                        ws.write(row_num, 15, p.costo if p.costo else '', styler)
                        ws.write(row_num, 16, p.get_estado_display(), stylel)
                        row_num += 1

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass


            elif action == 'listadosolicitudlosep_excel':
                try:
                    cronogramaid = request.GET['id']

                    __author__ = 'Unemi'
                    title2 = easyxf(
                        'font: name Verdana, color-index black, bold on , height 270; alignment: horiz centre')

                    stylec = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre', num_format_str='yyyy-mm-dd')
                    styler2 = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
                    stylel = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz left')
                    styler = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right', num_format_str='#,##0.00')

                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listado')
                    ws.write_merge(0, 0, 0, 16, 'UNIVERSIDAD ESTATAL DE MILAGRO', title2)
                    ws.write_merge(1, 1, 0, 16, 'SOLICITUDES DE CAPACITACIONES DEL PERSONAL LOSEP Y CÓDIGO DE TRABAJO', title2)

                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=SOLICITUDES_LOSEP_CT_ ' + cronogramaid.__str__() + '.xls'
                    columns = [
                        (u"NÚMERO SOL.", 3000),
                        (u"FECHA SOL.", 3000),
                        (u"DEPARTAMENTO", 9000),
                        (u"CÉDULA", 4000),
                        (u"SERVIDOR", 9000),
                        (u"CELULAR", 4000),
                        (u"E-MAIL", 4000),
                        (u"TEMA", 9000),
                        (u"INSTITUCIÓN", 9000),
                        (u"PAÍS", 6000),
                        (u"JUSTIFICACIÓN", 6000),
                        (u"MODALIDAD", 5000),
                        (u"FECHA INICIO", 3000),
                        (u"FECHA FIN", 3000),
                        (u"HORAS", 3000),
                        (u"COSTO", 3000),
                        (u"ESTADO", 4500)
                    ]

                    row_num = 2
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    participantes = PlanificarCapacitaciones.objects.filter(status=True,
                                                                            cronograma=cronogramaid).order_by(
                        '-fecha_creacion', 'administrativo__persona__apellido1')

                    row_num += 1
                    cont = 0
                    for p in participantes:
                        cont += 1
                        ws.write(row_num, 0, str(p.id).zfill(6), stylel)
                        ws.write(row_num, 1, p.fecha_creacion, stylec)

                        #departamento = p.administrativo.persona.mi_departamento()

                        #departamento = p.administrativo.persona.distributivopersona_set.filter(status=True, estadopuesto_id=1)[0].unidadorganica.nombre
                        departamento = p.administrativo.persona.departamentopersona()


                        ws.write(row_num, 2, departamento, stylel)
                        ws.write(row_num, 3, p.administrativo.persona.cedula if p.administrativo.persona.cedula else p.administrativo.persona.pasaporte, stylel)
                        ws.write(row_num, 4, p.administrativo.persona.apellido1 + ' ' + p.administrativo.persona.apellido2 + ' '+ p.administrativo.persona.nombres, stylel)
                        ws.write(row_num, 5, p.administrativo.persona.telefono, stylel)
                        ws.write(row_num, 6, p.administrativo.persona.emailinst, stylel)
                        ws.write(row_num, 7, p.tema, stylel)
                        ws.write(row_num, 8, p.institucion, stylel)
                        ws.write(row_num, 9, p.pais.nombre if p.pais else '', stylel)
                        ws.write(row_num, 10, p.justificacion, stylel)
                        ws.write(row_num, 11, p.get_modalidad_display(), stylel)
                        ws.write(row_num, 12, p.fechainicio if p.fechainicio else '', stylec)
                        ws.write(row_num, 13, p.fechafin if p.fechafin else '', stylec)
                        ws.write(row_num, 14, p.horas if p.horas else '', styler2)
                        ws.write(row_num, 15, p.costo if p.costo else '', styler)
                        ws.write(row_num, 16, p.get_estado_display(), stylel)
                        row_num += 1

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'participantes':
                try:
                    data['title'] = u'Solicitudes de capacitaciones/actualizaciones'
                    data['fase'] = 'LEG'
                    if 'url_vars' in request.GET:
                        url_vars = request.GET['url_vars']
                    else:
                        url_vars = ''
                    url_vars += "&action={}".format(action)
                    data['estados'] = ESTADOS_PLANIFICAR_CAPACITACIONES
                    search = None
                    cronogramaid = request.GET['id']
                    data['cronogramaid'] = cronogramaid
                    if cronogramaid:
                        url_vars += "&id={}".format(cronogramaid)
                    # v = CronogramaCapacitacionDocente.objects.get(pk=int(cronogramaid)).get_tipo_display()
                    # v = CronogramaCapacitacionDocente.objects.get(pk=int(cronogramaid)).tipo
                    cron = CronogramaCapacitacionDocente.objects.get(pk=int(cronogramaid))
                    data['cronograma']  = cron
                    data['tipopersonal'] = cron.get_tipo_display()
                    data['idtipo'] = cron.tipo
                    departamentos = []
                    facultades = []
                    periodos = []

                    if cron.tipo == 2:
                        departamentos = Departamento.objects.values_list('id', 'nombre').filter(status=True,
                                                pk__in=DistributivoPersona.objects.values_list('unidadorganica_id').filter(status=True, regimenlaboral__codigo__in=[1, 2],
                                                    persona_id__in=Administrativo.objects.values_list('persona_id').filter(status=True,
                                                        pk__in=PlanificarCapacitaciones.objects.values_list('administrativo_id').filter(tipo=2, status=True)
                                                        )
                                                    )
                                                )
                    else:
                        periodos = Periodo.objects.values_list('id', 'nombre').filter(status=True, pk__in=PlanificarCapacitaciones.objects.values_list('periodo_id').filter(tipo=1,status=True).distinct()).order_by('-inicio')
                        facultades = Coordinacion.objects.values_list('id', 'nombre', 'alias').filter(excluir=False, status=True).exclude(pk__in=[10, 11]).order_by('id')
                    estadosol = 4
                    if 'eSol' in request.GET:
                        estadosol = int(request.GET['eSol'])
                    url_vars += "&eSol={}".format(estadosol)

                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        url_vars += "&s={}".format(search)
                        ss = search.split(' ')
                        if len(ss) == 1:
                            if estadosol == 0:
                                if cron.tipo == 1:
                                    participantes = PlanificarCapacitaciones.objects.filter(Q(profesor__persona__apellido1__icontains=search) | Q(profesor__persona__apellido2__icontains=search) | Q(profesor__persona__nombres__icontains=search),status=True, cronograma=cronogramaid).order_by('-fecha_creacion', 'profesor__persona__apellido1')
                                else:
                                    participantes = PlanificarCapacitaciones.objects.filter(Q(administrativo__persona__apellido1__icontains=search) | Q(administrativo__persona__apellido2__icontains=search) | Q(administrativo__persona__nombres__icontains=search),status=True, cronograma=cronogramaid).order_by('-fecha_creacion', 'administrativo__persona__apellido1')
                            else:
                                if cron.tipo == 1:
                                    participantes = PlanificarCapacitaciones.objects.filter(Q(profesor__persona__apellido1__icontains=search) | Q(profesor__persona__apellido2__icontains=search) | Q(profesor__persona__nombres__icontains=search),status=True, cronograma=cronogramaid, estado=estadosol).order_by('-fecha_creacion', 'profesor__persona__apellido1')
                                else:
                                    participantes = PlanificarCapacitaciones.objects.filter(Q(administrativo__persona__apellido1__icontains=search) | Q(administrativo__persona__apellido2__icontains=search) | Q(administrativo__persona__nombres__icontains=search),status=True, cronograma=cronogramaid, estado=estadosol).order_by('-fecha_creacion', 'administrativo__persona__apellido1')
                        else:
                            if estadosol == 0:
                                if cron.tipo == 1:
                                    participantes = PlanificarCapacitaciones.objects.filter(Q(profesor__persona__apellido1__icontains=ss[0]) & Q(profesor__persona__apellido2__icontains=ss[1]), status=True, cronograma=cronogramaid).order_by('-fecha_creacion', 'profesor__persona__apellido1')
                                else:
                                    participantes = PlanificarCapacitaciones.objects.filter(Q(administrativo__persona__apellido1__icontains=ss[0]) & Q(administrativo__persona__apellido2__icontains=ss[1]), status=True, cronograma=cronogramaid).order_by('-fecha_creacion', 'administrativo__persona__apellido1')
                            else:
                                if cron.tipo == 1:
                                    participantes = PlanificarCapacitaciones.objects.filter(Q(profesor__persona__apellido1__icontains=ss[0]) & Q(profesor__persona__apellido2__icontains=ss[1]), status=True, cronograma=cronogramaid, estado=estadosol).order_by('-fecha_creacion', 'profesor__persona__apellido1')
                                else:
                                    participantes = PlanificarCapacitaciones.objects.filter(Q(administrativo__persona__apellido1__icontains=ss[0]) & Q(administrativo__persona__apellido2__icontains=ss[1]), status=True, cronograma=cronogramaid, estado=estadosol).order_by('-fecha_creacion', 'administrativo__persona__apellido1')
                    else:
                        if estadosol == 0:
                            participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma=cronogramaid).order_by('-fecha_creacion', 'profesor__persona__apellido1')
                        else:
                            participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma=cronogramaid, estado=estadosol).order_by('-fecha_creacion', 'profesor__persona__apellido1')
                    paging = MiPaginador(participantes, 15)
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
                    data['participantes'] = page.object_list
                    data['estadosol'] = estadosol
                    data['fecharep'] = datetime.now().strftime('%d-%m-%Y')

                    form2 = PlanificarCapacitacionesDevolucionForm()
                    form2.tipo_devolucion()
                    data['form2'] = form2
                    data['form3'] = DescuentoRolForm()
                    data['departamentos'] = departamentos
                    data['periodos'] = periodos
                    data['facultades'] = facultades
                    data['cronogramacapacitacion'] = cron
                    data['form4'] = PlanificarCapacitacionesArchivoForm()
                    data['monto_natural'] = num2words(cron.monto, lang='es')
                    data['url_vars'] = url_vars
                    return render(request, "adm_capdocente/participantecapth.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcapacitacion':
                try:
                    data['title'] = u'Editar solicitud de capacitación/actualización'
                    data['convocatoria'] = convocatoria = request.GET['convocatoria']
                    data['solicitud'] = solicitud = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = PlanificarCapacitacionesForm(initial={'tema': solicitud.tema,
                                                                 'institucion': solicitud.institucion,
                                                                 'pais': solicitud.pais,
                                                                 'justificacion': solicitud.justificacion,
                                                                 'modalidad': solicitud.modalidad,
                                                                 'fechainicio': solicitud.fechainicio,
                                                                 'fechafin': solicitud.fechafin,
                                                                 'costo': solicitud.costo,
                                                                 'horas': solicitud.horas,
                                                                 'link': solicitud.link})

                    data['form'] = form
                    data['criterios'] = solicitud.planificarcapacitacionesdetallecriterios_set.filter(status=True).order_by('criterio_id')
                    return render(request, "adm_capdocente/editcapacitacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'delperiodo':
                try:
                    data['title'] = u'Eliminar Cronograma de capacitaciones'
                    data['periodo'] = CronogramaCapacitacionDocente.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_capdocente/delperiodo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editperiodo':
                try:
                    data['title'] = u'Editar Cronograma de capacitaciones/actualizaciones'
                    data['periodo'] = periodo = CronogramaCapacitacionDocente.objects.get(pk=int(request.GET['id']))
                    form = CapDocentePeriodoForm(initial={'tipo':periodo.tipo,
                                                          'descripcion':periodo.descripcion,
                                                          'resolucion':periodo.resolucion,
                                                          'inicio':periodo.inicio,
                                                          'fin':periodo.fin,
                                                          'monto':periodo.monto,
                                                          'iniciocapacitacion':periodo.iniciocapacitacion,
                                                          'fincapacitacion':periodo.fincapacitacion,
                                                          'iniciocapacitaciontecdoc': periodo.iniciocapacitaciontecdoc,
                                                          'fincapacitaciontecdoc': periodo.fincapacitaciontecdoc,
                                                          'fechaconvenio': periodo.fechaconvenio
                                                          })

                    if periodo.contar_inscripcion_periodo() > 0:
                        form.editar()

                    data['form'] = form
                    return render(request, "adm_capdocente/editperiodo.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Cronograma de capacitaciones'
            data['fase'] = 'LEG'
            if persona.grupo_evaluacion():
                data['periodo'] = CronogramaCapacitacionDocente.objects.filter(pk__gt=4, tipo=1, status=True).order_by('-inicio')
            else:
                data['periodo'] = CronogramaCapacitacionDocente.objects.filter(status=True).exclude(pk__in=CronogramaCapacitacionDocente.objects.filter(pk__gt=4, tipo=1, status=True).values_list('id')).order_by('-inicio')
            return render(request, "adm_capdocente/viewperiodo.html", data)