# -*- coding: latin-1 -*-
import time as pausaparaemail
from datetime import datetime
from itertools import chain
import requests
import sys
import json
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction, connections
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decimal import Decimal
from decorators import secure_module, last_access
from sagest.commonviews import obtener_estado_solicitud, obtener_tipoarchivo_solicitud
from sagest.models import Rubro, CompromisoPagoPosgrado, CompromisoPagoPosgradoRecorrido, CompromisoPagoPosgradoGarante, \
    CompromisoPagoPosgradoGaranteArchivo, DistributivoPersona, RubroRefinanciamiento, CuentaContable, ComprobanteAlumno
from sagest.forms import RegistroPagoForm
from sga.forms import CompromisoPagoSubirDocumentoForm, CompromisoPagoSubirDocumentoPersonalForm, \
    CompromisoPagoDatosConyugeForm, CompromisoPagoDatosGaranteForm, CompromisoPagoDatosConyugeGaranteForm, \
    RefinanciamientoPosgradoSubirComprobantePagoForm
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import Matricula, PeriodoGrupoSocioEconomico, Inscripcion, miinstitucion, CUENTAS_CORREOS, \
    PersonaDocumentoPersonal, MESES_CHOICES, SolicitudRefinanciamientoPosgradoRecorrido, Persona
from settings import COBRA_COMISION_BANCO
from sga.commonviews import adduserdata, obtener_reporte, secuencia_contrato_maestria, secuencia_pagare_maestria
from sga.funciones import log, generar_nombre, cuenta_email_disponible_para_envio, validar_archivo, fechaletra_corta, convertir_fecha
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['periodoseleccionado'] = periodoseleccionado = request.session['periodo']
    data['persona'] = persona
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        # return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
        inscripcion = perfilprincipal.inscripcion
    else:
        inscripcion = None
    urlepunemi = 'https://sagest.epunemi.gob.ec/'
    # urlepunemi = 'http://127.0.0.1:8001/'
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'recibo':
                try:
                    rubro = Rubro.objects.get(pk=int(request.POST['id']))
                    rubro.generar_recibo()
                    log(u'Genero Recibo: %s' % rubro, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'subirdocumento':
                try:
                    # Consulto el compromiso de pago
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=int(encrypt(request.POST['idc'])))
                    # Consulto los documentos personales del alumnos: cedula y papeleta de votación
                    documentospersonales = persona.documentos_personales()
                    hayarchivos = False
                    if 'cedula' in request.FILES:
                        hayarchivos = True
                        descripcionarchivo = 'Cédula de ciudadanía'
                        resp = validar_archivo(descripcionarchivo, request.FILES['cedula'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    if 'votacion' in request.FILES:
                        hayarchivos = True
                        descripcionarchivo = 'Papeleta de votación'
                        resp = validar_archivo(descripcionarchivo, request.FILES['votacion'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    f = CompromisoPagoSubirDocumentoPersonalForm(request.POST, request.FILES)

                    if f.is_valid():
                        if hayarchivos:
                            if not documentospersonales:
                                acedula = request.FILES['cedula']
                                acedula._name = generar_nombre("cedula", acedula._name)

                                avotacion = request.FILES['votacion']
                                avotacion._name = generar_nombre("papeleta", avotacion._name)

                                documentospersonales = PersonaDocumentoPersonal(persona=persona,
                                                                                cedula=acedula,
                                                                                estadocedula=1,
                                                                                observacioncedula='',
                                                                                papeleta=avotacion,
                                                                                observacionpapeleta='',
                                                                                estadopapeleta=1)
                                documentospersonales.save(request)
                            else:
                                if 'cedula' in request.FILES:
                                    acedula = request.FILES['cedula']
                                    acedula._name = generar_nombre("cedula", acedula._name)
                                    documentospersonales.cedula = acedula
                                    documentospersonales.estadocedula = 1
                                    documentospersonales.observacioncedula = ''

                                if 'votacion' in request.FILES:
                                    avotacion = request.FILES['votacion']
                                    avotacion._name = generar_nombre("papeleta", avotacion._name)
                                    documentospersonales.papeleta = avotacion
                                    documentospersonales.estadopapeleta = 1
                                    documentospersonales.observacionpapeleta = ''

                                documentospersonales.save(request)

                                if compromisopago.puede_cambiar_estado():
                                    # Consulto el estado DOCUMENTOS CARGADOS
                                    estado = obtener_estado_solicitud(2, 3)
                                    compromisopago.estado = estado
                                    compromisopago.observacion = ''
                                    compromisopago.save(request)

                                    # Creo el recorrido del compromiso
                                    recorrido = CompromisoPagoPosgradoRecorrido(compromisopago=compromisopago,
                                                                                fecha=datetime.now().date(),
                                                                                observacion='DOCUMENTOS CARGADOS',
                                                                                estado=estado
                                                                                )
                                    recorrido.save(request)

                                    # Si el compromiso de pago es por refinanciamieno
                                    if compromisopago.tipo == 2:
                                        # Actualizo el estado en la solicitud
                                        solicitud = compromisopago.solicitudrefinanciamiento
                                        solicitud.estado = estado
                                        solicitud.observacion = ''
                                        solicitud.save(request)

                                        # Creo el recorrido de la solicitud
                                        recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                                               fecha=datetime.now().date(),
                                                                                               observacion='DOCUMENTOS CARGADOS',
                                                                                               estado=estado
                                                                                               )
                                        recorrido.save(request)

                                    enviar_correo_notificacion(persona, estado)


                            log(u'Cargó documentos personales %s' % (persona), request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

            elif action == 'subircomprobantepago':
                try:
                    # Consulto el compromiso de pago
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=int(encrypt(request.POST['idc'])))

                    if 'comprobantepago' in request.FILES:
                        descripcionarchivo = 'Comprobante de pago'
                        resp = validar_archivo(descripcionarchivo, request.FILES['comprobantepago'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    f = RefinanciamientoPosgradoSubirComprobantePagoForm(request.POST, request.FILES)

                    if f.is_valid():
                        archivo = request.FILES['comprobantepago']
                        archivo._name = generar_nombre("comprobantepago", archivo._name)

                        solicitud = compromisopago.solicitudrefinanciamiento
                        solicitud.comprobantepago = archivo
                        solicitud.save(request)

                        compromisopago.archivocomprobante = archivo
                        compromisopago.observacioncomprobante = ""
                        compromisopago.estadocomprobante = 1
                        compromisopago.save(request)

                        if compromisopago.puede_cambiar_estado():
                            # Consulto el estado DOCUMENTOS CARGADOS
                            estado = obtener_estado_solicitud(2, 3)
                            compromisopago.estado = estado
                            compromisopago.observacion = ''
                            compromisopago.save(request)

                            # Creo el recorrido del compromiso
                            recorrido = CompromisoPagoPosgradoRecorrido(compromisopago=compromisopago,
                                                                        fecha=datetime.now().date(),
                                                                        observacion='DOCUMENTOS CARGADOS',
                                                                        estado=estado
                                                                        )
                            recorrido.save(request)

                            # Si el compromiso de pago es por refinanciamieno
                            if compromisopago.tipo == 2:
                                # Actualizo el estado en la solicitud
                                solicitud = compromisopago.solicitudrefinanciamiento
                                solicitud.estado = estado
                                solicitud.observacion = ''
                                solicitud.save(request)

                                # Creo el recorrido de la solicitud
                                recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                                       fecha=datetime.now().date(),
                                                                                       observacion='DOCUMENTOS CARGADOS',
                                                                                       estado=estado
                                                                                       )
                                recorrido.save(request)

                            enviar_correo_notificacion(persona, estado)


                        log(u'Cargó documento comprobante de pago %s' % (persona), request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

            elif action == 'guardardatosconyuge':
                try:
                    # Consulto el compromiso de pago
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=int(encrypt(request.POST['id'])))
                    acedula = avotacion = None
                    if 'archivocedula' in request.FILES:
                        descripcionarchivo = 'Cédula de ciudadanía'
                        resp = validar_archivo(descripcionarchivo, request.FILES['archivocedula'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    if 'archivovotacion' in request.FILES:
                        descripcionarchivo = 'Papeleta de votación'
                        resp = validar_archivo(descripcionarchivo, request.FILES['archivovotacion'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    f = CompromisoPagoDatosConyugeForm(request.POST, request.FILES)

                    if f.is_valid():
                        if 'archivocedula' in request.FILES:
                            acedula = request.FILES['archivocedula']
                            acedula._name = generar_nombre("cedula", acedula._name)

                        if 'archivovotacion' in request.FILES:
                            avotacion = request.FILES['archivovotacion']
                            avotacion._name = generar_nombre("papeleta", avotacion._name)

                        conyuge = compromisopago.datos_conyuge()
                        # Si no existen datos del conyuge se crea
                        if not conyuge:
                            conyuge = CompromisoPagoPosgradoGarante(compromisopago=compromisopago,
                                                                    tipo=1,
                                                                    cedula=f.cleaned_data['cedula'],
                                                                    nombres=f.cleaned_data['nombres'],
                                                                    apellido1=f.cleaned_data['apellido1'],
                                                                    apellido2=f.cleaned_data['apellido2'],
                                                                    genero=f.cleaned_data['genero'],
                                                                    estadocivil=f.cleaned_data['estadocivil'],
                                                                    direccion=f.cleaned_data['direccion']
                                                                    )
                            conyuge.save(request)
                            # Tipo de archivo cedula del conyuge
                            tipoarchivo = obtener_tipoarchivo_solicitud(2, 1)
                            # Guardo archivo de la cedula
                            archivoconyuge = CompromisoPagoPosgradoGaranteArchivo(garante=conyuge,
                                                                                  tipoarchivo=tipoarchivo,
                                                                                  archivo=acedula,
                                                                                  estado=1)
                            archivoconyuge.save(request)

                            # Tipo de archivo papeleta de votacion del conyuge
                            tipoarchivo = obtener_tipoarchivo_solicitud(2, 2)
                            # Guardo archivo de la papeleta de votación
                            archivoconyuge = CompromisoPagoPosgradoGaranteArchivo(garante=conyuge,
                                                                                  tipoarchivo=tipoarchivo,
                                                                                  archivo=avotacion,
                                                                                  estado=1)
                            archivoconyuge.save(request)

                            log(u'Agregó datos del conyuge %s' % (persona), request, "add")
                        else:
                            conyuge.cedula = f.cleaned_data['cedula']
                            conyuge.nombres = f.cleaned_data['nombres']
                            conyuge.apellido1 = f.cleaned_data['apellido1']
                            conyuge.apellido2 = f.cleaned_data['apellido2']
                            conyuge.genero = f.cleaned_data['genero']
                            conyuge.estadocivil = f.cleaned_data['estadocivil']
                            conyuge.direccion = f.cleaned_data['direccion']
                            conyuge.save(request)

                            if acedula:
                                archivocedula = conyuge.archivocedulaconyuge()
                                archivocedula.archivo = acedula
                                archivocedula.estado = 1
                                archivocedula.observacion = ''
                                archivocedula.save(request)
                            if avotacion:
                                archivovotacion = conyuge.archivovotacionconyuge()
                                archivovotacion.archivo = avotacion
                                archivovotacion.estado = 1
                                archivovotacion.observacion = ''
                                archivovotacion.save(request)


                            if compromisopago.puede_cambiar_estado():
                                # Consulto el estado DOCUMENTOS CARGADOS
                                estado = obtener_estado_solicitud(2, 3)
                                compromisopago.estado = estado
                                compromisopago.observacion = ''
                                compromisopago.save(request)

                                # Creo el recorrido del compromiso
                                recorrido = CompromisoPagoPosgradoRecorrido(compromisopago=compromisopago,
                                                                            fecha=datetime.now().date(),
                                                                            observacion='DOCUMENTOS CARGADOS',
                                                                            estado=estado
                                                                            )
                                recorrido.save(request)

                                # Si el compromiso de pago es por refinanciamieno
                                if compromisopago.tipo == 2:
                                    # Actualizo el estado en la solicitud
                                    solicitud = compromisopago.solicitudrefinanciamiento
                                    solicitud.estado = estado
                                    solicitud.observacion = ''
                                    solicitud.save(request)

                                    # Creo el recorrido de la solicitud
                                    recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                                           fecha=datetime.now().date(),
                                                                                           observacion='DOCUMENTOS CARGADOS',
                                                                                           estado=estado
                                                                                           )
                                    recorrido.save(request)

                                enviar_correo_notificacion(persona, estado)

                            log(u'Actualizó datos del conyuge %s' % (persona), request, "edit")

                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

            elif action == 'guardardatosgarante':
                try:
                    # Consulto el compromiso de pago
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=int(encrypt(request.POST['id'])))
                    acedula = avotacion = arolpago = aimppredio = afactuserv = ariseruc = aconstitucion = None
                    aexistencia = arenta = anombramiento = aactajunta = aruc = None
                    if 'archivocedula' in request.FILES:
                        descripcionarchivo = 'Cédula de ciudadanía'
                        resp = validar_archivo(descripcionarchivo, request.FILES['archivocedula'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    if 'archivovotacion' in request.FILES:
                        descripcionarchivo = 'Papeleta de votación'
                        resp = validar_archivo(descripcionarchivo, request.FILES['archivovotacion'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    if 'archivorolpago' in request.FILES:
                        descripcionarchivo = 'Rol de pagos'
                        resp = validar_archivo(descripcionarchivo, request.FILES['archivorolpago'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    if 'archivoimpuestopredial' in request.FILES:
                        descripcionarchivo = 'Pago de impuesto predial'
                        resp = validar_archivo(descripcionarchivo, request.FILES['archivoimpuestopredial'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    if 'archivoserviciobasico' in request.FILES:
                        descripcionarchivo = 'Factura Servicio básico'
                        resp = validar_archivo(descripcionarchivo, request.FILES['archivoserviciobasico'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    if 'archivoriseruc' in request.FILES:
                        descripcionarchivo = 'RISE o RUC'
                        resp = validar_archivo(descripcionarchivo, request.FILES['archivoriseruc'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    if 'archivoconstitucion' in request.FILES:
                        descripcionarchivo = 'Copia Constitución y estatutos'
                        resp = validar_archivo(descripcionarchivo, request.FILES['archivoconstitucion'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    if 'archivoexistencia' in request.FILES:
                        descripcionarchivo = 'Certificado Existencia legal'
                        resp = validar_archivo(descripcionarchivo, request.FILES['archivoexistencia'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    if 'archivorenta' in request.FILES:
                        descripcionarchivo = 'Declaración impuesto renta'
                        resp = validar_archivo(descripcionarchivo, request.FILES['archivorenta'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    if 'archivorepresentante' in request.FILES:
                        descripcionarchivo = 'Nombramiento representante'
                        resp = validar_archivo(descripcionarchivo, request.FILES['archivorepresentante'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    if 'archivoacta' in request.FILES:
                        descripcionarchivo = 'Acta junta accionistas'
                        resp = validar_archivo(descripcionarchivo, request.FILES['archivoacta'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    if 'archivoruc' in request.FILES:
                        descripcionarchivo = 'RUC'
                        resp = validar_archivo(descripcionarchivo, request.FILES['archivoruc'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    f = CompromisoPagoDatosGaranteForm(request.POST, request.FILES)

                    if f.is_valid():
                        if 'archivocedula' in request.FILES:
                            acedula = request.FILES['archivocedula']
                            acedula._name = generar_nombre("cedula", acedula._name)

                        if 'archivovotacion' in request.FILES:
                            avotacion = request.FILES['archivovotacion']
                            avotacion._name = generar_nombre("papeleta", avotacion._name)

                        if 'archivorolpago' in request.FILES:
                            arolpago = request.FILES['archivorolpago']
                            arolpago._name = generar_nombre("rolpago", arolpago._name)

                        if 'archivoimpuestopredial' in request.FILES:
                            aimppredio = request.FILES['archivoimpuestopredial']
                            aimppredio._name = generar_nombre("impuestopredio", aimppredio._name)

                        if 'archivoserviciobasico' in request.FILES:
                            afactuserv = request.FILES['archivoserviciobasico']
                            afactuserv._name = generar_nombre("facturaservbas", afactuserv._name)

                        if 'archivoriseruc' in request.FILES:
                            ariseruc = request.FILES['archivoriseruc']
                            ariseruc._name = generar_nombre("riseruc", ariseruc._name)

                        if 'archivoconstitucion' in request.FILES:
                            aconstitucion = request.FILES['archivoconstitucion']
                            aconstitucion._name = generar_nombre("constitucion", aconstitucion._name)

                        if 'archivoexistencia' in request.FILES:
                            aexistencia = request.FILES['archivoexistencia']
                            aexistencia._name = generar_nombre("existencialegal", aexistencia._name)

                        if 'archivorenta' in request.FILES:
                            arenta = request.FILES['archivorenta']
                            arenta._name = generar_nombre("declaracionrenta", arenta._name)

                        if 'archivorepresentante' in request.FILES:
                            anombramiento = request.FILES['archivorepresentante']
                            anombramiento._name = generar_nombre("nombramientorep", anombramiento._name)

                        if 'archivoacta' in request.FILES:
                            aactajunta = request.FILES['archivoacta']
                            aactajunta._name = generar_nombre("actajunta", aactajunta._name)

                        if 'archivoruc' in request.FILES:
                            aruc = request.FILES['archivoruc']
                            aruc._name = generar_nombre("ruc", aruc._name)

                        garante = compromisopago.datos_garante()
                        # Si no existen datos del garante se crea
                        if not garante:
                            garante = CompromisoPagoPosgradoGarante(compromisopago=compromisopago,
                                                                    tipo=2,
                                                                    cedula=f.cleaned_data['cedula'],
                                                                    nombres=f.cleaned_data['nombres'],
                                                                    apellido1=f.cleaned_data['apellido1'],
                                                                    apellido2=f.cleaned_data['apellido2'],
                                                                    genero=f.cleaned_data['genero'],
                                                                    estadocivil=f.cleaned_data['estadocivil'],
                                                                    direccion=f.cleaned_data['direccion'],
                                                                    personajuridica=f.cleaned_data['personajuridica'],
                                                                    relaciondependencia=f.cleaned_data['relaciondependencia'] if int(f.cleaned_data['personajuridica']) == 2 else None
                                                                    )
                            garante.save(request)

                            # Tipo de archivo cedula del garante
                            tipoarchivo = obtener_tipoarchivo_solicitud(2, 3)

                            archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                  tipoarchivo=tipoarchivo,
                                                                                  archivo=acedula,
                                                                                  estado=1)
                            archivogarante.save(request)

                            # Tipo de archivo papeleta de votacion del garante
                            tipoarchivo = obtener_tipoarchivo_solicitud(2, 4)

                            archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                  tipoarchivo=tipoarchivo,
                                                                                  archivo=avotacion,
                                                                                  estado=1)
                            archivogarante.save(request)

                            # Si no es persona juridica
                            if int(f.cleaned_data['personajuridica']) == 2:
                                # si trabaja bajo relacion de dependencia
                                if int(f.cleaned_data['relaciondependencia']) == 1:
                                    # Tipo de archivo rol de pago
                                    tipoarchivo = obtener_tipoarchivo_solicitud(2, 5)

                                    archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                          tipoarchivo=tipoarchivo,
                                                                                          archivo=arolpago,
                                                                                          estado=1)
                                    archivogarante.save(request)
                                else:
                                    # Tipo de archivo pago impuestos prediales
                                    tipoarchivo = obtener_tipoarchivo_solicitud(2, 6)

                                    archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                          tipoarchivo=tipoarchivo,
                                                                                          archivo=aimppredio,
                                                                                          estado=1)
                                    archivogarante.save(request)

                                    if afactuserv:
                                        # Tipo de archivo factura de servicio básico
                                        tipoarchivo = obtener_tipoarchivo_solicitud(2, 7)

                                        archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                              tipoarchivo=tipoarchivo,
                                                                                              archivo=afactuserv,
                                                                                              estado=1)
                                        archivogarante.save(request)

                                    # Tipo de archivo RISE o RUC
                                    tipoarchivo = obtener_tipoarchivo_solicitud(2, 8)

                                    archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                          tipoarchivo=tipoarchivo,
                                                                                          archivo=ariseruc,
                                                                                          estado=1)
                                    archivogarante.save(request)
                            else:
                                # Tipo de archivo copia de constitucion
                                tipoarchivo = obtener_tipoarchivo_solicitud(2, 9)

                                archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                      tipoarchivo=tipoarchivo,
                                                                                      archivo=aconstitucion,
                                                                                      estado=1)
                                archivogarante.save(request)

                                # Tipo de archivo certificado existencia legal
                                tipoarchivo = obtener_tipoarchivo_solicitud(2, 10)

                                archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                      tipoarchivo=tipoarchivo,
                                                                                      archivo=aexistencia,
                                                                                      estado=1)
                                archivogarante.save(request)

                                # Tipo de archivo impuesto a la renta
                                tipoarchivo = obtener_tipoarchivo_solicitud(2, 11)

                                archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                      tipoarchivo=tipoarchivo,
                                                                                      archivo=arenta,
                                                                                      estado=1)
                                archivogarante.save(request)

                                # Tipo de archivo nombramiento de reprsentante
                                tipoarchivo = obtener_tipoarchivo_solicitud(2, 12)

                                archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                      tipoarchivo=tipoarchivo,
                                                                                      archivo=anombramiento,
                                                                                      estado=1)
                                archivogarante.save(request)

                                # Tipo de archivo acta junta de accionistas
                                tipoarchivo = obtener_tipoarchivo_solicitud(2, 13)

                                archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                      tipoarchivo=tipoarchivo,
                                                                                      archivo=aactajunta,
                                                                                      estado=1)
                                archivogarante.save(request)

                                # Tipo de archivo copia del ruc
                                tipoarchivo = obtener_tipoarchivo_solicitud(2, 14)

                                archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                      tipoarchivo=tipoarchivo,
                                                                                      archivo=aruc,
                                                                                      estado=1)
                                archivogarante.save(request)

                            log(u'Agregó datos del garante %s' % (persona), request, "add")
                        else:
                            garante.cedula = f.cleaned_data['cedula']
                            garante.nombres = f.cleaned_data['nombres']
                            garante.apellido1 = f.cleaned_data['apellido1']
                            garante.apellido2 = f.cleaned_data['apellido2']
                            if f.cleaned_data['genero']:
                                garante.genero = f.cleaned_data['genero']

                            if f.cleaned_data['estadocivil']:
                                garante.estadocivil = f.cleaned_data['estadocivil']

                            garante.direccion = f.cleaned_data['direccion']
                            garante.save(request)

                            if acedula:
                                archivogarante = garante.archivocedulagarante()
                                archivogarante.archivo = acedula
                                archivogarante.observacion = ''
                                archivogarante.estado = 1
                                archivogarante.save(request)

                            if avotacion:
                                archivogarante = garante.archivovotaciongarante()
                                archivogarante.archivo = avotacion
                                archivogarante.estado = 1
                                archivogarante.observacion = ''
                                archivogarante.save(request)

                            # si no es persona juridica
                            if garante.personajuridica == 2:
                                # si trabaja bajo relacion de dependencia
                                relaciondependencia = int(f.cleaned_data['relaciondependencia']) if f.cleaned_data['relaciondependencia'] else garante.relaciondependencia
                                if relaciondependencia == 1:
                                    if arolpago:
                                        archivogarante = garante.archivorolpagos()
                                        if archivogarante:
                                            archivogarante.archivo = arolpago
                                            archivogarante.observacion = ''
                                            archivogarante.estado = 1
                                            archivogarante.save(request)

                                            garante.relaciondependencia = relaciondependencia
                                            garante.save(request)
                                        else:
                                            # Tipo de archivo rol de pago
                                            tipoarchivo = obtener_tipoarchivo_solicitud(2, 5)

                                            archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                                  tipoarchivo=tipoarchivo,
                                                                                                  archivo=arolpago,
                                                                                                  estado=1)
                                            archivogarante.save(request)

                                            garante.relaciondependencia = relaciondependencia
                                            garante.save(request)
                                else:
                                    if aimppredio:
                                        archivogarante = garante.archivoimpuestopredial()
                                        archivogarante.archivo = aimppredio
                                        archivogarante.observacion = ''
                                        archivogarante.estado = 1
                                        archivogarante.save(request)

                                    if afactuserv:
                                        archivogarante = garante.archivofacturaserviciobasico()
                                        archivogarante.archivo = afactuserv
                                        archivogarante.observacion = ''
                                        archivogarante.estado = 1
                                        archivogarante.save(request)

                                    if ariseruc:
                                        archivogarante = garante.archivoriseruc()
                                        archivogarante.archivo = ariseruc
                                        archivogarante.observacion = ''
                                        archivogarante.estado = 1
                                        archivogarante.save(request)
                            else:
                                if aconstitucion:
                                    archivogarante = garante.archivoconstitucion()
                                    archivogarante.archivo = aconstitucion
                                    archivogarante.observacion = ''
                                    archivogarante.estado = 1
                                    archivogarante.save(request)

                                if aexistencia:
                                    archivogarante = garante.archivoexistencialegal()
                                    archivogarante.archivo = aexistencia
                                    archivogarante.observacion = ''
                                    archivogarante.estado = 1
                                    archivogarante.save(request)

                                if arenta:
                                    archivogarante = garante.archivoimpuestorenta()
                                    archivogarante.archivo = arenta
                                    archivogarante.observacion = ''
                                    archivogarante.estado = 1
                                    archivogarante.save(request)

                                if anombramiento:
                                    archivogarante = garante.archivonombramientorepresentante()
                                    archivogarante.archivo = anombramiento
                                    archivogarante.observacion = ''
                                    archivogarante.estado = 1
                                    archivogarante.save(request)

                                if aactajunta:
                                    archivogarante = garante.archivojuntaaccionistas()
                                    archivogarante.archivo = aactajunta
                                    archivogarante.observacion = ''
                                    archivogarante.estado = 1
                                    archivogarante.save(request)

                                if aruc:
                                    archivogarante = garante.archivoruc()
                                    archivogarante.archivo = aruc
                                    archivogarante.observacion = ''
                                    archivogarante.estado = 1
                                    archivogarante.save(request)

                            if compromisopago.puede_cambiar_estado():
                                # Consulto el estado DOCUMENTOS CARGADOS
                                estado = obtener_estado_solicitud(2, 3)
                                compromisopago.estado = estado
                                compromisopago.observacion = ''
                                compromisopago.save(request)

                                # Creo el recorrido del compromiso
                                recorrido = CompromisoPagoPosgradoRecorrido(compromisopago=compromisopago,
                                                                            fecha=datetime.now().date(),
                                                                            observacion='DOCUMENTOS CARGADOS',
                                                                            estado=estado
                                                                            )
                                recorrido.save(request)

                                # Si el compromiso de pago es por refinanciamieno
                                if compromisopago.tipo == 2:
                                    # Actualizo el estado en la solicitud
                                    solicitud = compromisopago.solicitudrefinanciamiento
                                    solicitud.estado = estado
                                    solicitud.observacion = ''
                                    solicitud.save(request)

                                    # Creo el recorrido de la solicitud
                                    recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                                           fecha=datetime.now().date(),
                                                                                           observacion='DOCUMENTOS CARGADOS',
                                                                                           estado=estado
                                                                                           )
                                    recorrido.save(request)

                                enviar_correo_notificacion(persona, estado)

                            log(u'Actualizó datos del garante %s' % (persona), request, "edit")

                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

            elif action == 'guardardatosconyugegarante':
                try:
                    # Consulto el compromiso de pago
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=int(encrypt(request.POST['id'])))
                    acedula = avotacion = None
                    if 'archivocedula' in request.FILES:
                        descripcionarchivo = 'Cédula de ciudadanía'
                        resp = validar_archivo(descripcionarchivo, request.FILES['archivocedula'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    if 'archivovotacion' in request.FILES:
                        descripcionarchivo = 'Papeleta de votación'
                        resp = validar_archivo(descripcionarchivo, request.FILES['archivovotacion'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    f = CompromisoPagoDatosConyugeGaranteForm(request.POST, request.FILES)

                    if f.is_valid():
                        if 'archivocedula' in request.FILES:
                            acedula = request.FILES['archivocedula']
                            acedula._name = generar_nombre("cedula", acedula._name)

                        if 'archivovotacion' in request.FILES:
                            avotacion = request.FILES['archivovotacion']
                            avotacion._name = generar_nombre("papeleta", avotacion._name)

                        conyugegarante = compromisopago.datos_conyuge_garante()
                        # Si no existen datos del conyuge del garante se crea
                        if not conyugegarante:
                            conyugegarante = CompromisoPagoPosgradoGarante(compromisopago=compromisopago,
                                                                    tipo=3,
                                                                    cedula=f.cleaned_data['cedula'],
                                                                    nombres=f.cleaned_data['nombres'],
                                                                    apellido1=f.cleaned_data['apellido1'],
                                                                    apellido2=f.cleaned_data['apellido2'],
                                                                    genero=f.cleaned_data['genero'],
                                                                    estadocivil=f.cleaned_data['estadocivil'],
                                                                    direccion=f.cleaned_data['direccion']
                                                                    )
                            conyugegarante.save(request)
                            # Tipo de archivo cedula del conyuge de garante
                            tipoarchivo = obtener_tipoarchivo_solicitud(2, 15)
                            # Guardo archivo de la cedula
                            archivoconyuge = CompromisoPagoPosgradoGaranteArchivo(garante=conyugegarante,
                                                                                  tipoarchivo=tipoarchivo,
                                                                                  archivo=acedula,
                                                                                  estado=1)
                            archivoconyuge.save(request)

                            # Tipo de archivo papeleta de votacion del conyuge de garante
                            tipoarchivo = obtener_tipoarchivo_solicitud(2, 16)
                            # Guardo archivo de la papeleta de votación
                            archivoconyuge = CompromisoPagoPosgradoGaranteArchivo(garante=conyugegarante,
                                                                                  tipoarchivo=tipoarchivo,
                                                                                  archivo=avotacion,
                                                                                  estado=1)
                            archivoconyuge.save(request)

                            log(u'Agregó datos del conyuge del garante %s' % (persona), request, "add")
                        else:
                            conyugegarante.cedula = f.cleaned_data['cedula']
                            conyugegarante.nombres = f.cleaned_data['nombres']
                            conyugegarante.apellido1 = f.cleaned_data['apellido1']
                            conyugegarante.apellido2 = f.cleaned_data['apellido2']
                            if f.cleaned_data['genero']:
                                conyugegarante.genero = f.cleaned_data['genero']
                            if f.cleaned_data['estadocivil']:
                                conyugegarante.estadocivil = f.cleaned_data['estadocivil']
                            conyugegarante.direccion = f.cleaned_data['direccion']
                            conyugegarante.save(request)

                            if acedula:
                                archivocedula = conyugegarante.archivocedulaconyugegarante()
                                archivocedula.archivo = acedula
                                archivocedula.observacion = ''
                                archivocedula.estado = 1
                                archivocedula.save(request)
                            if avotacion:
                                archivovotacion = conyugegarante.archivovotacionconyugegarante()
                                archivovotacion.archivo = avotacion
                                archivovotacion.observacion = ''
                                archivovotacion.estado = 1
                                archivovotacion.save(request)

                            if compromisopago.puede_cambiar_estado():
                                # Consulto el estado DOCUMENTOS CARGADOS
                                estado = obtener_estado_solicitud(2, 3)
                                compromisopago.estado = estado
                                compromisopago.observacion = ''
                                compromisopago.save(request)

                                # Creo el recorrido del compromiso
                                recorrido = CompromisoPagoPosgradoRecorrido(compromisopago=compromisopago,
                                                                            fecha=datetime.now().date(),
                                                                            observacion='DOCUMENTOS CARGADOS',
                                                                            estado=estado
                                                                            )
                                recorrido.save(request)

                                # Si el compromiso de pago es por refinanciamieno
                                if compromisopago.tipo == 2:
                                    # Actualizo el estado en la solicitud
                                    solicitud = compromisopago.solicitudrefinanciamiento
                                    solicitud.estado = estado
                                    solicitud.observacion = ''
                                    solicitud.save(request)

                                    # Creo el recorrido de la solicitud
                                    recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                                           fecha=datetime.now().date(),
                                                                                           observacion='DOCUMENTOS CARGADOS',
                                                                                           estado=estado
                                                                                           )
                                    recorrido.save(request)

                                enviar_correo_notificacion(persona, estado)

                            log(u'Actualizó datos del conyuge del garante %s' % (persona), request, "edit")

                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

            elif action == 'generarnumerocontrato':
                try:
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=int(encrypt(request.POST['idc'])))
                    # Si no existe numero de contrato para el compromiso
                    if not compromisopago.numerocontrato:
                        secuencia = secuencia_contrato_maestria()

                        # En caso que ya exista el número de contrato
                        if CompromisoPagoPosgrado.objects.filter(status=True, numerocontrato=secuencia, fecha__year=datetime.now().year).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Error al generar el contrato, intente nuevamente"})
                        else:
                            # Consulto el costo del programa
                            costoprograma = compromisopago.matricula.costo_programa()
                            totalpagado = compromisopago.matricula.total_pagado_alumno()
                            # Actualizo los datos del contrato en el compromiso de pago
                            compromisopago.fechacontrato = datetime.now().date()
                            compromisopago.numerocontrato = secuencia
                            compromisopago.montocontrato = costoprograma
                            compromisopago.montopagado = totalpagado
                            compromisopago.save(request)

                            # Actualizo el codigo de compromiso de pago en los rubros de la matricula y se bloquea debido a que el total se genera con los rubros de la matricula
                            Rubro.objects.filter(status=True, matricula=compromisopago.matricula).update(compromisopago=compromisopago, bloqueado=True)

                        log(u'Agregó número de contrato al compromiso de pago: %s' % compromisopago, request, "edit")

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar la secuencia del contrato."})

            elif action == 'contratomaestriapdf':
                try:
                    data = {}

                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=int(encrypt(request.POST['idc'])))

                    data['numerocontrato'] = "CONTRATO Nº " + str(compromisopago.numerocontrato).zfill(4) + "-" + str(compromisopago.fechacontrato.year)
                    data['fechacontrato'] = fechaletra_corta(compromisopago.fechacontrato)
                    data['compromisopago'] = compromisopago
                    data['costoprograma'] = compromisopago.matricula.costo_programa()
                    data['nombregarante'] = compromisopago.nombre_completo_garante()
                    data['cedulagarante'] = compromisopago.cedula_garante()

                    directorposgrado = DistributivoPersona.objects.filter(denominacionpuesto_id=511, estadopuesto_id=1, status=True)
                    if directorposgrado:
                        data['nombredelegado'] = directorposgrado[0].persona.nombre_completo()
                        data['ceduladelegado'] = directorposgrado[0].persona.cedula
                        data['cargodelegado'] = directorposgrado[0].denominacionpuesto.descripcion

                    return conviert_html_to_pdf(
                        'alu_finanzas/contratomaestriapdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    return HttpResponseRedirect("/alu_finanzas?info=%s" % "Error al generar el reporte del contrato de la maestría")

            elif action == 'generarnumeropagare':
                # conexión a base de datos EPUNEMI
                conexion = connections['epunemi']
                cnepunemi = conexion.cursor()
                try:
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=int(encrypt(request.POST['idc'])))
                    # Si no existe numero de pagaré para el compromiso
                    if not compromisopago.numeropagare:
                        # Si es por refinanciamiento no hay contrato y se debe generar la secuencia del pagaré
                        if compromisopago.tipo == 2:
                            secuencia = secuencia_contrato_maestria()
                            # En caso que ya exista el número de pagaré
                            if CompromisoPagoPosgrado.objects.filter(status=True, numeropagare=secuencia, fecha__year=datetime.now().year).exists():
                                return JsonResponse({"result": "bad", "mensaje": u"Error al generar el pagaré, intente nuevamente"})
                            else:
                                compromisopago.numerocontrato = secuencia
                                compromisopago.save(request)

                                solicitud = compromisopago.solicitudrefinanciamiento
                                # Consulto el estado REFINANCIADO
                                estado = obtener_estado_solicitud(1, 15)
                                solicitud.estado = estado

                                # Creo el recorrido de la solicitud
                                recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                                       fecha=datetime.now().date(),
                                                                                       observacion='REFINANCIAMIENTO GENERADO AUTOMÁTICAMENTE',
                                                                                       estado=estado
                                                                                       )
                                recorrido.save()

                                # Si los rubros nuevos no han sido generados
                                if not solicitud.rubrosgenerados:
                                    # CREAR TABLA DE AMORTIZACION
                                    rubromaestria = Rubro.objects.filter(status=True, matricula=solicitud.matricula).order_by('-fechavence')[0].tipo

                                    # Consulto los rubros de la tabla amortizacion original para guardarlos en el compromiso por refinanciamiento
                                    rubros = Rubro.objects.filter(status=True, matricula=solicitud.matricula).order_by('fechavence')
                                    for rubro in rubros:
                                        fechapago = None
                                        vencido = False

                                        pagosrubro = rubro.pago_set.filter(status=True).order_by('-fecha')

                                        if pagosrubro:
                                            fechapago = pagosrubro[0].fecha

                                        if not rubro.cancelado:
                                            vencido = datetime.now().date() > rubro.fechavence

                                        rubrocompromiso = RubroRefinanciamiento(compromisopago=compromisopago,
                                                                                rubro=rubro,
                                                                                valor=rubro.valor,
                                                                                fechaemite=rubro.fecha,
                                                                                fechavence=rubro.fechavence,
                                                                                saldo=rubro.saldo,
                                                                                vencido=vencido,
                                                                                cancelado=rubro.cancelado)
                                        rubrocompromiso.save(request)

                                    # Los rubros no cancelados y que no tengan pagos se inactivan y se coloca estado refinanciado True
                                    for rubro in rubros.filter(cancelado=False):
                                        pagosrubro = rubro.pago_set.filter(status=True).order_by('-fecha')
                                        if not pagosrubro:
                                            rubro.refinanciado = True
                                            rubro.status = False
                                            rubro.observacion = "REFINANCIADO POSGRADO"
                                            rubro.save(request)

                                            # Actualizar en base de epunemi
                                            sql = """UPDATE sagest_rubro SET status=FALSE, refinanciado=TRUE, observacion = 'REFINANCIADO POSGRADO' WHERE idrubrounemi=%s AND status=true""" % (rubro.id)
                                            cnepunemi.execute(sql)

                                    # Consulto los rubros con saldo
                                    rubrosconsaldo = Rubro.objects.filter(status=True, matricula=solicitud.matricula, saldo__gt=0).order_by('fechavence')
                                    for rubrosaldo in rubrosconsaldo:
                                        pagosrubro = rubrosaldo.pago_set.filter(status=True).order_by('-fecha')
                                        # si tiene pagos actualizo el valor del rubro que seria valor original - saldo
                                        if pagosrubro:
                                            rubrosaldo.valor = rubrosaldo.valor - rubrosaldo.saldo
                                            rubrosaldo.cancelado = True
                                            rubrosaldo.refinanciado = True
                                            rubrosaldo.observacion = ""
                                            rubrosaldo.save(request)

                                            # Hacer la misma actalizacion en EPUNEMI
                                            sql = """UPDATE sagest_rubro SET valor=%s, valortotal=%s, saldo=0.00, cancelado=TRUE, refinanciado=TRUE, observacion = '' WHERE idrubrounemi=%s AND status=true""" % (rubrosaldo.valor, rubrosaldo.valor, rubrosaldo.id)
                                            cnepunemi.execute(sql)

                                    # Consulto la persona por cedula en base de epunemi
                                    cedula = solicitud.matricula.inscripcion.persona.cedula

                                    sql = """SELECT pe.id FROM sga_persona AS pe WHERE pe.cedula='%s' AND pe.status=TRUE;  """ % (cedula)
                                    cnepunemi.execute(sql)
                                    registro = cnepunemi.fetchone()
                                    codigoalumno = registro[0]

                                    #  Se crean los nuevos rubros según la propuesta aceptada
                                    propuesta = solicitud.solicitudrefinanciamientoposgradopropuesta_set.filter(status=True).order_by('id')
                                    for cuota in propuesta:
                                        nuevorubro = Rubro(fecha=datetime.now().date(),
                                                           valor=cuota.valorcuota,
                                                           valortotal=cuota.valorcuota,
                                                           saldo=cuota.valorcuota,
                                                           persona=solicitud.matricula.inscripcion.persona,
                                                           matricula=solicitud.matricula,
                                                           nombre=rubromaestria.nombre,
                                                           tipo=rubromaestria,
                                                           cancelado=False,
                                                           observacion='',
                                                           iva_id=1,
                                                           epunemi=True,
                                                           fechavence=cuota.fechacuota,
                                                           compromisopago=compromisopago,
                                                           bloqueado=True
                                                           )
                                        nuevorubro.save(request)

                                        # Consulto el tipo otro rubro en epunemi
                                        sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (rubromaestria.id)
                                        cnepunemi.execute(sql)
                                        registro = cnepunemi.fetchone()

                                        # Si existe
                                        if registro is not None:
                                            tipootrorubro = registro[0]
                                        else:
                                            # Debo crear ese tipo de rubro
                                            # Consulto centro de costo
                                            sql = """SELECT id FROM sagest_centrocosto WHERE status=True AND unemi=True AND tipo=%s;""" % (rubromaestria.tiporubro)
                                            cnepunemi.execute(sql)
                                            centrocosto = cnepunemi.fetchone()
                                            idcentrocosto = centrocosto[0]

                                            # Consulto la cuenta contable
                                            cuentacontable = CuentaContable.objects.get(partida=rubromaestria.partida,status=True)

                                            # Creo el tipo de rubro en epunemi
                                            sql = """ Insert Into sagest_tipootrorubro (status, nombre, partida_id, valor, interface, activo, ivaaplicado_id, nofactura, exportabanco, cuentacontable_id, centrocosto_id, tiporubro, idtipootrorubrounemi, unemi)
                                                                VALUES(TRUE, '%s', %s, %s, FALSE, TRUE, %s, FALSE, TRUE, %s, %s, 1, %s, TRUE); """ % (
                                                rubromaestria.nombre, cuentacontable.partida.id, rubromaestria.valor,
                                                rubromaestria.ivaaplicado.id, cuentacontable.id, idcentrocosto,
                                                rubromaestria.id)
                                            cnepunemi.execute(sql)

                                        # Insertar en base de datos epunemi
                                        sql = """ INSERT INTO sagest_rubro (status, usuario_creacion_id, fecha_creacion, cuota, tipocuota, valoriva, tienenotacredito, valornotacredito, valordescuento, anulado, fecha, valor ,valortotal, saldo, persona_id, nombre, tipo_id, cancelado, observacion, iva_id, idrubrounemi, totalunemi, fechavence, compromisopago, bloqueado, refinanciado, bloqueadopornovedad, titularcambiado) 
                                                                                                      VALUES (TRUE, 1, NOW(), 0, 3, 0, FALSE, 0, 0, FALSE, NOW(),                   %s, %s,    %s, %s,     '%s', %s,   FALSE,    '',              1,   %s,        %s,     '/%s/',   %s, FALSE, FALSE, FALSE, FALSE); """ \
                                              % (cuota.valorcuota, cuota.valorcuota, cuota.valorcuota, codigoalumno,
                                                 rubromaestria.nombre, tipootrorubro, nuevorubro.id, cuota.valorcuota,
                                                 cuota.fechacuota, compromisopago.id)
                                        cnepunemi.execute(sql)

                                    solicitud.rubrosgenerados = True
                                    solicitud.save(request)
                                    # CREAR TABLA DE AMORTIZACION

                        conexion.commit()
                        cnepunemi.close()
                        # secuencia = secuencia_pagare_maestria()

                        # En caso que ya exista el número de pagaré
                        # if CompromisoPagoPosgrado.objects.filter(status=True, numeropagare=secuencia, fecha__year=datetime.now().year).exists():
                        #     return JsonResponse({"result": "bad", "mensaje": u"Error al generar el pagaré, intente nuevamente"})
                        # else:
                        #     # Consulto el total pendiente de rubros del alumno
                        totalpendiente = compromisopago.matricula.total_saldo_rubrosinanular()

                        # Consulto la ultima fecha de vencimiento de los rubrps
                        x = Rubro.objects.filter(status=True, matricula=compromisopago.matricula, saldo__gt=0).order_by('-fechavence')
                        fechavence = Rubro.objects.filter(status=True, matricula=compromisopago.matricula, saldo__gt=0).order_by('-fechavence')[0].fechavence

                        # Actualizo los datos del pagaré en el compromiso de pago
                        compromisopago.fechapagare = datetime.now().date()
                        compromisopago.numeropagare = compromisopago.numerocontrato
                        compromisopago.montopagare = totalpendiente
                        compromisopago.total = totalpendiente
                        compromisopago.fechavencepagare = fechavence
                        compromisopago.save(request)

                        log(u'Agregó número de pagaré al compromiso de pago: %s' % compromisopago, request, "edit")

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    conexion.rollback()
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar la secuencia del contrato."})

            elif action == 'pagaremaestriapdf':
                try:
                    data = {}

                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=int(encrypt(request.POST['idc'])))

                    data['numeropagare'] = "Milagro.- No. " + str(compromisopago.numeropagare).zfill(4) + "-" + str(compromisopago.fechapagare.year)
                    data['fechapagare'] = fechaletra_corta(compromisopago.fechapagare)
                    data['fechapagare2'] = str(compromisopago.fechapagare.day) + " de " + MESES_CHOICES[compromisopago.fechapagare.month - 1][1].capitalize() + " del " + str(compromisopago.fechapagare.year)
                    data['montopagare'] = compromisopago.montopagare
                    data['fechavence'] = compromisopago.fechavencepagare

                    data['fechavence'] = str(compromisopago.fechavencepagare.day) + " de " + MESES_CHOICES[compromisopago.fechavencepagare.month - 1][1].capitalize() + " del " + str(compromisopago.fechavencepagare.year)

                    # Consulto datos del alumno
                    alumno = {}
                    alumno['nombres'] = compromisopago.matricula.inscripcion.persona.nombre_completo()
                    alumno['cedula'] = compromisopago.matricula.inscripcion.persona.cedula
                    alumno['direccion'] = compromisopago.matricula.inscripcion.persona.direccion_corta()
                    alumno['programa'] = compromisopago.matricula.inscripcion.carrera.nombre
                    alumno['numerocohorte'] = compromisopago.matricula.nivel.periodo.numero_cohorte_maestria()
                    data['alumno'] = alumno

                    # consulto datos del conyuge del alumno
                    conyuge = compromisopago.datos_conyuge()
                    if conyuge:
                        conyuge_alumno = {}
                        conyuge_alumno['nombres'] = compromisopago.nombre_completo_conyuge()
                        conyuge_alumno['cedula'] = conyuge.cedula
                        conyuge_alumno['direccion'] = conyuge.direccion
                        data['conyuge_alumno'] = conyuge_alumno

                    # consulto datos del garante
                    garante = {}
                    garantealumno = compromisopago.datos_garante()
                    garante['nombres'] = compromisopago.nombre_completo_garante()
                    garante['cedula'] = garantealumno.cedula
                    garante['direccion'] = garantealumno.direccion
                    data['garante'] = garante

                    # consulto datos de conyuge del garante
                    conyugegarantealumno = compromisopago.datos_conyuge_garante()
                    if conyugegarantealumno:
                        conyuge_garante = {}
                        conyuge_garante['nombres'] = compromisopago.nombre_completo_conyuge_garante()
                        conyuge_garante['cedula'] = conyugegarantealumno.cedula
                        conyuge_garante['direccion'] = conyugegarantealumno.direccion
                        data['conyuge_garante'] = conyuge_garante


                    return conviert_html_to_pdf(
                        'alu_finanzas/pagaremaestriapdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    return HttpResponseRedirect("/alu_finanzas?info=%s" % "Error al generar el reporte del pagaré de la maestría")


            elif action == 'subirdocumentopagare':
                try:
                    # Consulto el compromiso de pago
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=int(encrypt(request.POST['id'])))

                    if compromisopago.estado.valor == 2:
                        return JsonResponse({"result": "bad", "mensaje": u"No se puede cargar los documentos debido a que ya se asignó estado LEGALIZADO al compromiso de pago."})

                    if 'compromisopago' in request.FILES:
                        descripcionarchivo = 'Tabla de amortización'
                        resp = validar_archivo(descripcionarchivo, request.FILES['compromisopago'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    if 'contrato' in request.FILES:
                        descripcionarchivo = 'Contrato de Maestría'
                        resp = validar_archivo(descripcionarchivo, request.FILES['contrato'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    if 'pagare' in request.FILES:
                        descripcionarchivo = 'Pagaré'
                        resp = validar_archivo(descripcionarchivo, request.FILES['pagare'], ['pdf'], '4MB')
                        if resp['estado'] != "OK":
                            return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                    f = CompromisoPagoSubirDocumentoForm(request.POST, request.FILES)

                    if f.is_valid():
                        # Consulto el estado DOCUMENTOS CARGADOS
                        estado = obtener_estado_solicitud(2, 3)

                        if 'compromisopago' in request.FILES:
                            acompromisopago = request.FILES['compromisopago']
                            acompromisopago._name = generar_nombre("compromisopago", acompromisopago._name)
                            compromisopago.archivocompromiso = acompromisopago
                            compromisopago.observacioncompromiso = ''
                            compromisopago.estadocompromiso = 1

                        if 'contrato' in request.FILES:
                            acontrato = request.FILES['contrato']
                            acontrato._name = generar_nombre("contratomaestria", acontrato._name)
                            compromisopago.archivocontrato = acontrato
                            compromisopago.observacioncontrato = ''
                            compromisopago.estadocontrato = 1

                        if 'pagare' in request.FILES:
                            apagare = request.FILES['pagare']
                            apagare._name = generar_nombre("pagare", apagare._name)
                            compromisopago.archivopagare = apagare
                            compromisopago.observacionpagare = ''
                            compromisopago.estadopagare = 1

                        compromisopago.save(request)

                        if compromisopago.puede_cambiar_estado():
                            # Consulto el estado DOCUMENTOS CARGADOS
                            estado = obtener_estado_solicitud(2, 3)
                            estadosolicitud = obtener_estado_solicitud(1, 21)

                            compromisopago.estado = estado
                            compromisopago.observacion = ''
                            compromisopago.save(request)

                            # Creo el recorrido del compromiso
                            recorrido = CompromisoPagoPosgradoRecorrido(compromisopago=compromisopago,
                                                                        fecha=datetime.now().date(),
                                                                        observacion='DOCUMENTOS CARGADOS',
                                                                        estado=estado
                                                                        )
                            recorrido.save(request)

                            # Si el compromiso de pago es por refinanciamiento
                            if compromisopago.tipo == 2:
                                # Actualizo el estado en la solicitud
                                solicitud = compromisopago.solicitudrefinanciamiento
                                solicitud.estado = estadosolicitud
                                solicitud.observacion = ''
                                solicitud.save(request)

                                # Creo el recorrido de la solicitud
                                recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                                       fecha=datetime.now().date(),
                                                                                       observacion='DOCUMENTOS CARGADOS',
                                                                                       estado=estadosolicitud
                                                                                       )
                                recorrido.save(request)

                            enviar_correo_notificacion(persona, estado)

                        log(u'Cargó documentos para su compromiso de pago %s - %s' % (persona, compromisopago), request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

            elif action == 'registropago':
                try:
                    with transaction.atomic():
                        matricula = Matricula.objects.get(pk=int(encrypt(request.POST['id'])))
                        cuentadeposito = int(request.POST['cuentadeposito'])
                        telefono = str(request.POST['telefono'])
                        email = str(request.POST['email'])
                        fechapago = convertir_fecha(request.POST['fecha'])
                        valor = Decimal(request.POST['valor'])
                        observacion = request.POST['observacion']
                        tipocomprobante = int(request.POST['tipocomprobante'])
                        persona_get = Persona.objects.get(pk=matricula.inscripcion.persona.id)
                        persona_get.telefono = telefono
                        persona_get.email = email
                        persona_get.save()
                        cuentadepositoget = cuentadeposito
                        if valor <= 0:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "El valor debe ser mayor a cero."}, safe=False)
                        if 'archivo' in request.FILES:
                            form = RegistroPagoForm(request.POST)
                            if form.is_valid():
                                nombrepersona = persona_get.__str__()
                                nombrepersona_str = persona_get.__str__().lower().replace(' ', '_')
                                comprobante = ComprobanteAlumno(persona=persona_get,
                                                                telefono=telefono,
                                                                email=email,
                                                                curso=matricula.inscripcion.carrera.nombre,
                                                                carrera=matricula.inscripcion.carrera.nombre,
                                                                cuentadeposito=cuentadepositoget,
                                                                valor=valor,
                                                                fechapago=fechapago,
                                                                observacion=observacion,
                                                                matricula=matricula,
                                                                tipocomprobante=tipocomprobante)
                                if 'archivo' in request.FILES:
                                    newfile = request.FILES['archivo']
                                    if newfile.size > 10485760:
                                        transaction.set_rollback(True)
                                        return JsonResponse({"result": "bad",
                                                             "mensaje": u"Error, Tamaño de archivo Maximo permitido es de 10Mb"})

                                    newfilesd = newfile._name
                                    ext = newfilesd[newfilesd.rfind("."):]
                                    if not (ext.lower() == '.pdf' or ext.lower() == '.png'):
                                        transaction.set_rollback(True)
                                        return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf o .png"}, safe=False)

                                    nombrefoto = 'comprobante_{}'.format(nombrepersona_str)
                                    newfile._name = generar_nombre(nombrefoto.strip(), newfile._name)
                                    comprobante.comprobantes = newfile
                                comprobante.save()
                                if persona.cedula:
                                    personacedula = str(persona.cedula)
                                if persona.pasaporte:
                                    personacedula = str(persona.pasaporte)
                                if persona.ruc:
                                    personacedula = str(persona.ruc)
                                url = urlepunemi + "api?a=apisavecomprobante" \
                                      "&tiporegistro=1&clavesecreta=unemiepunemi2022&personacedula=" + personacedula + "&cuentadeposito=" + str(cuentadeposito) + \
                                      "&telefono=" + str(persona.telefono) + \
                                      "&email=" + persona.email + \
                                      "&fecha=" + str(comprobante.fechapago) + \
                                      "&archivocomprobante=" + str(comprobante.comprobantes) + \
                                      "&valor=" + str(comprobante.valor) + \
                                      "&curso=" + comprobante.curso + \
                                      "&carrera=" + comprobante.carrera + \
                                      "&observacion=" + comprobante.observacion + \
                                      "&codigocomprobante=" + str(comprobante.id) + \
                                      "&tipocomprobante=" + str(comprobante.tipocomprobante)
                                print(url)
                                r = requests.get(url)
                                for lista in r.json():
                                    comprobante.idcomprobanteepunemi = lista['codigocomprobante']
                                    comprobante.save()
                                return JsonResponse({"result": False, "mensaje": '{} SU COMPROBANTE DE {} FUE REGISTRADO. EN 48 HORAS SE VALIDARAN SUS DATOS.'.format(nombrepersona.upper(), comprobante.get_tipocomprobante())}, safe=False)
                            else:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Falta subir evidencia del comprobante de pago."}, safe=False)
                except Exception as ex:
                    mensajeerror = "{} - {}".format(ex, 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    messages.error(request, mensajeerror)
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde.", "mensajeerror": mensajeerror}, safe=False)


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u' Mis finanzas'
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'pagos':
                try:
                    data['title'] = u'Pagos del rubro'
                    data['rubro'] = rubro = Rubro.objects.get(pk=request.GET['id'])
                    # data['pagos'] = rubro.pago_set.all().order_by('-fecha')
                    data['pagos'] = rubro.pago_set.filter(status=True).order_by('-fecha')
                    data['reporte_1'] = obtener_reporte('factura_reporte')
                    return render(request, "alu_finanzas/pagos.html", data)
                except Exception as ex:
                    pass

            elif action == 'recibo':
                try:
                    data['title'] = u'Confirmar imrpimir Recibo'
                    data['rubro'] = Rubro.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_finanzas/recibo.html", data)
                except:
                    pass

            elif action == 'mostrardocumentos':
                try:
                    data = {}
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=int(encrypt(request.GET['id'])))
                    documentos = []

                    # Consulto los documentos personales del alumnos: cedula y papeleta de votación
                    documentospersonales = persona.documentos_personales()
                    if documentospersonales:
                        documentos.append(['Cédula de ciudadanía', documentospersonales.cedula.url, documentospersonales.get_estadocedula_display(), documentospersonales.estadocedula, documentospersonales.observacioncedula])
                        documentos.append(['Papeleta de votación', documentospersonales.papeleta.url, documentospersonales.get_estadopapeleta_display(), documentospersonales.estadopapeleta, documentospersonales.observacionpapeleta])
                    else:
                        documentos.append(['Cédula de ciudadanía', None, None, None, None])
                        documentos.append(['Papeleta de votación', None, None, None, None])

                    # Si el compromiso de pago es por refinanciamiento
                    if compromisopago.tipo == 2:
                        documentos.append(['Comprobante de Pago', compromisopago.archivocomprobante.url, compromisopago.get_estadocomprobante_display(), compromisopago.estadocomprobante, compromisopago.observacioncomprobante])

                    # Consulto los documentos del conyuge
                    conyuge = compromisopago.datos_conyuge()
                    if conyuge:
                        archivocedula = conyuge.archivocedulaconyuge()
                        documentos.append([archivocedula.tipoarchivo.descripcion, archivocedula.archivo.url, archivocedula.get_estado_display(), archivocedula.estado, archivocedula.observacion])
                        archivovotacion = conyuge.archivovotacionconyuge()
                        documentos.append([archivovotacion.tipoarchivo.descripcion, archivovotacion.archivo.url, archivovotacion.get_estado_display(), archivovotacion.estado, archivovotacion.observacion])

                    # Consulto los documentos del garante
                    garante = compromisopago.datos_garante()
                    if garante:
                        archivocedula = garante.archivocedulagarante()
                        documentos.append([archivocedula.tipoarchivo.descripcion, archivocedula.archivo.url, archivocedula.get_estado_display(), archivocedula.estado, archivocedula.observacion])
                        archivovotacion = garante.archivovotaciongarante()
                        documentos.append([archivovotacion.tipoarchivo.descripcion, archivovotacion.archivo.url, archivovotacion.get_estado_display(), archivovotacion.estado, archivovotacion.observacion])

                        # Si no es persona juridica
                        if garante.personajuridica == 2:
                            # si trabaja bajo relacion de dependencia
                            if garante.relaciondependencia == 1:
                                archivorolpagos = garante.archivorolpagos()
                                documentos.append([archivorolpagos.tipoarchivo.descripcion, archivorolpagos.archivo.url, archivorolpagos.get_estado_display(), archivorolpagos.estado, archivorolpagos.observacion])
                            else:
                                archivopredios = garante.archivoimpuestopredial()
                                documentos.append([archivopredios.tipoarchivo.descripcion, archivopredios.archivo.url, archivopredios.get_estado_display(), archivopredios.estado, archivopredios.observacion])
                                archivofacserv = garante.archivofacturaserviciobasico()
                                if archivofacserv:
                                    documentos.append([archivofacserv.tipoarchivo.descripcion, archivofacserv.archivo.url, archivofacserv.get_estado_display(), archivofacserv.estado, archivofacserv.observacion])
                                archivoriseruc = garante.archivoriseruc()
                                documentos.append([archivoriseruc.tipoarchivo.descripcion, archivoriseruc.archivo.url, archivoriseruc.get_estado_display(), archivoriseruc.estado, archivoriseruc.observacion])
                        else:
                            archivoconstitucion = garante.archivoconstitucion()
                            documentos.append([archivoconstitucion.tipoarchivo.descripcion, archivoconstitucion.archivo.url, archivoconstitucion.get_estado_display(), archivoconstitucion.estado, archivoconstitucion.observacion])
                            archivoexistencia = garante.archivoexistencialegal()
                            documentos.append([archivoexistencia.tipoarchivo.descripcion, archivoexistencia.archivo.url, archivoexistencia.get_estado_display(), archivoexistencia.estado, archivoexistencia.observacion])
                            archivorenta = garante.archivoimpuestorenta()
                            documentos.append([archivorenta.tipoarchivo.descripcion, archivorenta.archivo.url, archivorenta.get_estado_display(), archivorenta.estado, archivorenta.observacion])
                            archivorepresentante = garante.archivonombramientorepresentante()
                            documentos.append([archivorepresentante.tipoarchivo.descripcion, archivorepresentante.archivo.url, archivorepresentante.get_estado_display(), archivorepresentante.estado, archivorepresentante.observacion])
                            archivoacta = garante.archivojuntaaccionistas()
                            documentos.append([archivoacta.tipoarchivo.descripcion, archivoacta.archivo.url, archivoacta.get_estado_display(), archivoacta.estado, archivoacta.observacion])
                            archivoruc = garante.archivoruc()
                            documentos.append([archivoruc.tipoarchivo.descripcion, archivoruc.archivo.url, archivoruc.get_estado_display(), archivoruc.estado, archivoruc.observacion])

                        # Consulto los documentos del conyuge del garante
                        conyugegarante = compromisopago.datos_conyuge_garante()
                        if conyugegarante:
                            archivocedula = conyugegarante.archivocedulaconyugegarante()
                            documentos.append([archivocedula.tipoarchivo.descripcion, archivocedula.archivo.url, archivocedula.get_estado_display(), archivocedula.estado, archivocedula.observacion])
                            archivovotacion = conyugegarante.archivovotacionconyugegarante()
                            documentos.append([archivovotacion.tipoarchivo.descripcion, archivovotacion.archivo.url, archivovotacion.get_estado_display(), archivovotacion.estado, archivovotacion.observacion])

                    # Consulto el compromiso, contrato y pagare
                    if compromisopago.archivopagare:
                        documentos.append(['Tabla de amortización', compromisopago.archivocompromiso.url, compromisopago.get_estadocompromiso_display(), compromisopago.estadocompromiso, compromisopago.observacioncompromiso])

                        if compromisopago.tipo == 1:
                            documentos.append(['Contrato de Maestría', compromisopago.archivocontrato.url, compromisopago.get_estadocontrato_display(), compromisopago.estadocontrato, compromisopago.observacioncontrato])

                        documentos.append(['Pagaré', compromisopago.archivopagare.url, compromisopago.get_estadopagare_display(), compromisopago.estadopagare, compromisopago.observacionpagare])

                    data['documentos'] = documentos

                    template = get_template("alu_finanzas/mostrardocumentos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'subirdocumento':
                try:
                    form = CompromisoPagoSubirDocumentoPersonalForm()
                    data['title'] = u'Subir Documentos Personales'
                    data['idm'] = request.GET['id']
                    data['idc'] = request.GET['idc']
                    data['form'] = form
                    data['saludo'] = 'Estimada' if persona.sexo_id == 1 else 'Estimado'
                    cedulaoblig = votacionoblig = True
                    # Si existe registro de documentos verifico que no estén vacios para validar
                    if persona.personadocumentopersonal_set.values("id").exists():
                        documentospersonales = persona.documentos_personales()
                        cedulaoblig = True if documentospersonales.cedula == '' or documentospersonales.estadocedula == 3 else False
                        votacionoblig = True if documentospersonales.papeleta == '' or documentospersonales.estadopapeleta == 3 else False

                    data['cedulaoblig'] = cedulaoblig
                    data['votacionoblig'] = votacionoblig

                    template = get_template("alu_finanzas/subirdocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'subircomprobante':
                try:
                    form = RefinanciamientoPosgradoSubirComprobantePagoForm()
                    data['title'] = u'Subir Comprobante de Pago'

                    pagorequerido = CompromisoPagoPosgrado.objects.get(pk=int(encrypt(request.GET['idc']))).solicitudrefinanciamiento.pagorequerido

                    data['idc'] = request.GET['idc']
                    data['form'] = form
                    data['pagorequerido'] = pagorequerido
                    data['saludo'] = 'Estimada' if persona.sexo_id == 1 else 'Estimado'

                    template = get_template("alu_finanzas/subircomprobantepago.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'datosconyuge':
                try:
                    data['title'] = u'Datos del Cónyuge del Alumno'
                    data['idc'] = request.GET['idc']
                    cedulaoblig = votacionoblig = True

                    # Consulto compromiso de pago
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=int(encrypt(request.GET['idc'])))
                    # Consulto datos del conyuge del compromiso de pago
                    conyuge = compromisopago.datos_conyuge()

                    if conyuge:
                        form = CompromisoPagoDatosConyugeForm(initial={'cedula': conyuge.cedula,
                                                                       'nombres': conyuge.nombres,
                                                                       'apellido1': conyuge.apellido1,
                                                                       'apellido2': conyuge.apellido2,
                                                                       'genero': conyuge.genero,
                                                                       'estadocivil': conyuge.estadocivil,
                                                                       'direccion': conyuge.direccion})
                        # Si la cedula o papeleta de votacion fueron rechazadas es obligación cargar
                        cedulaoblig = True if conyuge.archivocedulaconyuge().estado == 3 else False
                        votacionoblig = True if conyuge.archivovotacionconyuge().estado == 3 else False

                    else:
                        form = CompromisoPagoDatosConyugeForm()


                    data['form'] = form
                    data['cedulaoblig'] = cedulaoblig
                    data['votacionoblig'] = votacionoblig

                    template = get_template("alu_finanzas/datosconyuge.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'datosgarante':
                try:
                    data['title'] = u'Datos del Garante'
                    data['idc'] = request.GET['idc']
                    cedulaoblig = votacionoblig = True

                    # Consulto compromiso de pago
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=int(encrypt(request.GET['idc'])))
                    # Consulto datos del garante del compromiso de pago
                    garante = compromisopago.datos_garante()

                    if garante:
                        data['tiporeg'] = 'E'
                        form = CompromisoPagoDatosGaranteForm(initial={'cedula': garante.cedula,
                                                                       'nombres': garante.nombres,
                                                                       'apellido1': garante.apellido1,
                                                                       'apellido2': garante.apellido2,
                                                                       'genero': garante.genero,
                                                                       'estadocivil': garante.estadocivil,
                                                                       'direccion': garante.direccion,
                                                                       'relaciondependencia': garante.relaciondependencia,
                                                                       'personajuridica': garante.personajuridica})
                        # Si la cedula o papeleta de votacion fueron rechazadas es obligación cargar
                        cedulaoblig = True if garante.archivocedulagarante().estado == 3 else False
                        votacionoblig = True if garante.archivovotaciongarante().estado == 3 else False
                        data['bloqueacedula'] = garante.archivocedulagarante().estado == 2
                        data['bloqueavotacion'] = garante.archivovotaciongarante().estado == 2

                        # Si no es persona juridica
                        if garante.personajuridica == 2:
                            # Si trabaja bajo relacion de dependencia
                            if garante.relaciondependencia == 1:
                                data['rolpagooblig'] = True if garante.archivorolpagos().estado == 3 else False
                                data['bloquearolpago'] = garante.archivorolpagos().estado == 2
                            else:
                                data['impuestopredialoblig'] = True if garante.archivoimpuestopredial().estado == 3 else False
                                data['bloqueapredial'] = garante.archivoimpuestopredial().estado == 2
                                if garante.archivofacturaserviciobasico():
                                    data['serviciobasicooblig'] = True if garante.archivofacturaserviciobasico().estado == 3 else False
                                    data['bloqueaserv'] = garante.archivofacturaserviciobasico().estado == 2
                                data['riserucoblig'] = True if garante.archivoriseruc().estado == 3 else False
                                data['bloquearise'] = garante.archivoriseruc().estado == 2
                        else:
                            data['personajuridica'] = True
                            data['constitucionoblig'] = True if garante.archivoconstitucion().estado == 3 else False
                            data['bloqueaconstitucion'] = garante.archivoconstitucion().estado == 2
                            data['existenciaoblig'] = True if garante.archivoexistencialegal().estado == 3 else False
                            data['bloqueaexistencia'] = garante.archivoexistencialegal().estado == 2
                            data['rentaoblig'] = True if garante.archivoimpuestorenta().estado == 3 else False
                            data['bloquearenta'] = garante.archivoimpuestorenta().estado == 2
                            data['representanteoblig'] = True if garante.archivonombramientorepresentante().estado == 3 else False
                            data['bloquearepresentante'] = garante.archivonombramientorepresentante().estado == 2
                            data['actaoblig'] = True if garante.archivojuntaaccionistas().estado == 3 else False
                            data['bloquearacta'] = garante.archivojuntaaccionistas().estado == 2
                            data['rucoblig'] = True if garante.archivoruc().estado == 3 else False
                            data['bloquearruc'] = garante.archivoruc().estado == 2

                        # Si esta casado verifico que no existan datos del conyuge para que pueda editar su estado civil o no
                        if garante.estadocivil == 2:
                            conyugegarante = compromisopago.datos_conyuge_garante()
                            if conyugegarante:
                                data['conyugegarante'] = True
                    else:
                        data['tiporeg'] = 'N'
                        form = CompromisoPagoDatosGaranteForm()


                    data['form'] = form
                    data['cedulaoblig'] = cedulaoblig
                    data['votacionoblig'] = votacionoblig

                    template = get_template("alu_finanzas/datosgarante.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'datosconyugegarante':
                try:
                    data['title'] = u'Datos del Cónyuge del Garante'
                    data['idc'] = request.GET['idc']
                    cedulaoblig = votacionoblig = True

                    # Consulto compromiso de pago
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=int(encrypt(request.GET['idc'])))
                    # Consulto datos del conyuge del garante del compromiso de pago
                    conyuge = compromisopago.datos_conyuge_garante()

                    if conyuge:
                        form = CompromisoPagoDatosConyugeGaranteForm(initial={'cedula': conyuge.cedula,
                                                                       'nombres': conyuge.nombres,
                                                                       'apellido1': conyuge.apellido1,
                                                                       'apellido2': conyuge.apellido2,
                                                                       'genero': conyuge.genero,
                                                                       'estadocivil': conyuge.estadocivil,
                                                                       'direccion': conyuge.direccion})
                        # Si la cedula o papeleta de votacion fueron rechazadas es obligación cargar
                        cedulaoblig = True if conyuge.archivocedulaconyugegarante().estado == 3 else False
                        votacionoblig = True if conyuge.archivovotacionconyugegarante().estado == 3 else False
                        data['bloqueacedula'] = conyuge.archivocedulaconyugegarante().estado == 2
                        data['bloqueapapeleta'] = conyuge.archivovotacionconyugegarante().estado == 2
                    else:
                        form = CompromisoPagoDatosConyugeGaranteForm()


                    data['form'] = form
                    data['cedulaoblig'] = cedulaoblig
                    data['votacionoblig'] = votacionoblig

                    template = get_template("alu_finanzas/datosconyugegarante.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'subirdocumentopagare':
                try:
                    form = CompromisoPagoSubirDocumentoForm()
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=int(encrypt(request.GET['idc'])))
                    data['title'] = u'Subir Tabla amortización, Contrato y Pagaré' if compromisopago.tipo == 1 else u'Subir Tabla amortización y Pagaré'
                    data['idc'] = request.GET['idc']
                    data['form'] = form
                    data['tipocompromiso'] = compromisopago.tipo
                    data['saludo'] = 'Estimada' if persona.sexo_id == 1 else 'Estimado'
                    compromisooblig = pagareoblig = True

                    if compromisopago.tipo == 1:
                        contratooblig = True
                    else:
                        contratooblig = False
                        data['bloqueacontrato'] = True

                    if compromisopago.archivopagare:
                        compromisooblig = True if compromisopago.estadocompromiso == 3 else False
                        data['bloqueacompromiso'] = compromisopago.estadocompromiso == 2

                        if compromisopago.tipo == 1:
                            contratooblig = True if compromisopago.estadocontrato == 3 else False
                            data['bloqueacontrato'] = compromisopago.estadocontrato == 2

                        pagareoblig = True if compromisopago.estadopagare == 3 else False
                        data['bloqueapagare'] = compromisopago.estadopagare == 2

                    data['compromisooblig'] = compromisooblig
                    data['contratooblig'] = contratooblig
                    data['pagareoblig'] = pagareoblig

                    template = get_template("alu_finanzas/subirdocumentopagare.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'listacomprobantes':
                try:
                    data['title'] = u'Listado de comprobantes'
                    inscripcion = perfilprincipal.inscripcion
                    data['matricula'] = matricula = Matricula.objects.filter(nivel__periodo=periodoseleccionado, inscripcion=inscripcion)[0]
                    data['listacomprobantes'] = comprobantes = matricula.comprobantealumno_set.filter(status=True)
                    cursor = connections['epunemi'].cursor()
                    if comprobantes.filter(estados=1):
                       for listacom in comprobantes.filter(estados__in=[1,3]):
                            sql = """
                                    SELECT estados, cuenta.numero,tipo.nombre,banco.nombre
                                    FROM sagest_comprobantealumno compro,
                                    sagest_cuentabanco cuenta,
                                    sagest_tipocuentabanco tipo,
                                    sagest_banco banco
                                    WHERE compro.cuentadeposito_id=cuenta.id
                                    AND cuenta.tipocuenta_id=tipo.id
                                    AND cuenta.banco_id=banco.id
                                    and compro.id = %s
                                """ % (listacom.idcomprobanteepunemi)
                            cursor.execute(sql)
                            row = cursor.fetchone()
                            listacom.estados = row[0]
                            listacom.cuentadeposito = str(row[3]) + ' - #:' + str(row[1]) + ' - Cta:' + str(row[2])
                            listacom.save()
                    return render(request, "alu_finanzas/listacomprobantes.html", data)
                except Exception as ex:
                    pass

            elif action == 'registropago':
                try:
                    data['title'] = u'Registro de pago'
                    data['matricula'] = Matricula.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = RegistroPagoForm(initial={'telefono': persona.telefono,
                                                     'email': persona.email})
                    data['form2'] = form
                    url = urlepunemi + "api?a=apicuentas&clavesecreta=unemiepunemi2022"
                    r = requests.get(url)
                    listadocuentas = []
                    for lista in r.json():
                        listadocuentas.append([lista['id'], lista['nombre'], lista['numerocuenta'], lista['tipo']])
                    data['listadocuentas'] = listadocuentas
                    template = get_template("alu_finanzas/registropago.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Listado de rubros'
                rubrosnocancelados = persona.rubro_set.filter(cancelado=False, status=True).order_by('cancelado', 'fechavence')
                rubroscanceldos = persona.rubro_set.filter(cancelado=True, status=True).order_by('cancelado', '-fechavence')
                rubros = list(chain(rubrosnocancelados, rubroscanceldos))
                data['inscripcion'] = inscripcion
                paging = Paginator(rubros, 30)
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
                data['page'] = page
                data['rubros'] = page.object_list
                data['cobra_comision_banco'] = COBRA_COMISION_BANCO
                data['total_rubros'] = persona.total_rubros()
                data['total_pagado'] = persona.total_pagado()
                data['total_adeudado'] = persona.total_adeudado()
                data['reporte_0'] = obtener_reporte('listado_deuda_xinscripcion')
                data['reporte_1'] = obtener_reporte('recibo_cobro')
                data['reporte_2'] = obtener_reporte('factura_reporte')
                data['codigo_devolucion'] = 2951
                if perfilprincipal.es_estudiante() and periodoseleccionado:
                    data['inscripcion'] = inscripcion = perfilprincipal.inscripcion
                    matricula1 = Matricula.objects.filter(nivel__periodo=periodoseleccionado, inscripcion=inscripcion)
                    if matricula1:
                        data['matricula'] = matricula = matricula1[0]
                    else:
                        data['matricula'] = matricula = inscripcion.ultima_matricula()
                    data['periodotipo'] = False
                    valorgrupo = 0
                    if matricula:
                        if PeriodoGrupoSocioEconomico.objects.filter(status=True, periodo=matricula.nivel.periodo, gruposocioeconomico=matricula.matriculagruposocioeconomico()):
                            valorgrupo = PeriodoGrupoSocioEconomico.objects.filter(status=True, periodo=matricula.nivel.periodo, gruposocioeconomico=matricula.matriculagruposocioeconomico())[0].valor
                            data['valorgrupo'] = valorgrupo
                    if periodoseleccionado.tipo.id == 2:
                        data['periodotipo'] = True

                    if matricula:
                        # MAESTRIAS CON INICIO DESDE EL 25-03-2021
                        fecharige = datetime.strptime('2021-03-25', '%Y-%m-%d').date()
                        if periodoseleccionado.inicio >= fecharige and periodoseleccionado.tipo.id == 3 and en_fecha_disponible():
                            data['imprimircompromiso'] = True
                            data['reporte_3'] = obtener_reporte("tabla_amortizacion_posgrado")
                            data['matricula'] = matricula

                            # Si no existe compromiso de pago lo creo
                            if not CompromisoPagoPosgrado.objects.filter(matricula=matricula, status=True, vigente=True, tipo=1).exists():
                                # Consulto el estado Compromiso Generado
                                estado = obtener_estado_solicitud(2, 1)
                                compromisopago = CompromisoPagoPosgrado(matricula=matricula,
                                                                        fecha=datetime.now().date(),
                                                                        tipo=1,
                                                                        vigente=True,
                                                                        estado=estado)
                                compromisopago.save(request)

                                # Creo el recorrido del compromiso de pago
                                recorrido = CompromisoPagoPosgradoRecorrido(compromisopago=compromisopago,
                                                                            fecha=datetime.now().date(),
                                                                            observacion='COMPROMISO DE PAGO GENERADO',
                                                                            estado=estado
                                                                            )
                                recorrido.save(request)

                            # Compromiso de pago nuevo
                            data['compromisopago'] = compromiso = matricula.compromisopagoposgrado_set.filter(status=True, vigente=True, tipo=1)[0]

                            # Si el primer compromiso está LEGALIZADO(Compromiso que no es por refinanciamiento)
                            if compromiso.estado.id == 14:
                                # Compromiso de pago por refinanciamiento
                                if matricula.compromisopagoposgrado_set.filter(status=True, vigente=True, tipo=2).exists():
                                    data['compromisopago'] = matricula.compromisopagoposgrado_set.filter(status=True, vigente=True, tipo=2)[0]

                        elif en_fecha_disponible() and periodoseleccionado.tipo.id == 3 and matricula.compromisopagoposgrado_set.filter(status=True, vigente=True, tipo=2).exists():
                            data['imprimircompromiso'] = True
                            data['reporte_3'] = obtener_reporte("tabla_amortizacion_refinanciamiento_posgrado")
                            data['matricula'] = matricula
                            # Compromiso de pago por refinanciamiento
                            data['compromisopago'] = matricula.compromisopagoposgrado_set.filter(status=True, vigente=True, tipo=2)[0]
                        else:
                            data['imprimircompromiso'] = False

                perfilprincipal = request.session['perfilprincipal']
                mostrarbann = False
                if perfilprincipal.es_estudiante():
                    if not perfilprincipal.inscripcion.coordinacion.id ==7:
                        mostrarbann = True
                data['banner'] = mostrarbann


                return render(request, "alu_finanzas/view.html", data)
            except Exception as ex:
                pass

def enviar_correo_notificacion(persona, estado):
    # Envio de e-mail de notificacion al estudiante
    # listacuentascorreo = [23, 24, 25, 26, 27]
    # posgrado1_unemi@unemi.edu.ec
    # posgrado2_unemi@unemi.edu.ec
    # posgrado3_unemi@unemi.edu.ec
    # posgrado4_unemi@unemi.edu.ec
    # posgrado5_unemi@unemi.edu.ec

    listacuentascorreo = [18]  # posgrado@unemi.edu.ec

    fechaenvio = datetime.now().date()
    horaenvio = datetime.now().time()
    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
    tituloemail = "Carga de Documentos - Contrato de Programas de Posgrado"

    send_html_mail(tituloemail,
                   "emails/notificacion_estado_compromisopago.html",
                   {'sistema': u'Posgrado UNEMI',
                    'fecha': fechaenvio,
                    'hora': horaenvio,
                    'saludo': 'Estimada' if persona.sexo.id == 1 else 'Estimado',
                    'estudiante': persona.nombre_completo_inverso(),
                    'estado': estado.valor,
                    'observaciones': '',
                    'destinatario': 'ALUMNO',
                    't': miinstitucion()
                    },
                   persona.lista_emails_envio(),
                   # ['isaltosm@unemi.edu.ec'],
                   [],
                   cuenta=CUENTAS_CORREOS[cuenta][1]
                   )

    # Temporizador para evitar que se bloquee el servicio de gmail
    pausaparaemail.sleep(1)

    # Envío de e-mail de notificación a Posgrado
    lista_email_posgrado = []

    lista_email_posgrado.append('dmaciasv@unemi.edu.ec')
    lista_email_posgrado.append('smendietac@unemi.edu.ec')

    # lista_email_posgrado.append('ivan_saltos_medina@hotmail.com')
    # lista_email_posgrado.append('ivan.saltos.medina@gmail.com')

    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

    send_html_mail(tituloemail,
                   "emails/notificacion_estado_compromisopago.html",
                   {'sistema': u'Posgrado UNEMI',
                    'fecha': fechaenvio,
                    'hora': horaenvio,
                    'saludo': 'Estimados',
                    'estudiante': persona.nombre_completo_inverso(),
                    'estado': estado.valor,
                    'genero': 'la' if persona.sexo.id == 1 else 'él',
                    'destinatario': 'POSGRADO',
                    't': miinstitucion()
                    },
                   lista_email_posgrado,
                   [],
                   cuenta=CUENTAS_CORREOS[cuenta][1]
                   )
    # Temporizador para evitar que se bloquee el servicio de gmail
    pausaparaemail.sleep(1)


def en_fecha_disponible():
    fechadisponible = datetime.strptime('2021-06-01', '%Y-%m-%d').date()
    fechaactual = datetime.now().date()
    return fechaactual.__ge__(fechadisponible)