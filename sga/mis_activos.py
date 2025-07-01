# -*- coding: latin-1 -*-
import json
import os
import io
from itertools import count
import random

import xlsxwriter
from django.contrib.auth.decorators import login_required
from django.db import transaction

from core.firmar_documentos_ec import JavaFirmaEc
from core.firmar_documentos_ec_descentralizada import qrImgFirma
from sagest.forms import ActivoBodegaVirtualForm
from sagest.funciones import encrypt_id
from settings import SITE_STORAGE
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.templatetags.sga_extras import encrypt
from django.db.models import Sum, F, Window
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.template.context import Context
from django.db.models.query_utils import Q
from datetime import datetime, timedelta
from xlwt import *
from xlwt import easyxf
import xlwt
from django.db.models.functions import RowNumber

from decorators import secure_module, last_access
from sagest.models import ActivoFijo, SolicitudActivos, PrestamoActivosOperaciones, \
    AuditoriaPrestamoActivosOperaciones, Ubicacion, SolicitudTraspasoActivos, SeguimientoSolicitudTraspaso, \
    TraspasoActivo, DetalleTraspasoActivo, CorreccionesSolicitudTraspasoActivos, CronogramaPersonaConstatacionAT, \
    DetalleConstatacionFisicaActivoTecnologico, HistorialDocumentosFirmadosConstatacionAT, \
    Notificacionactivoresponsable, ConstatacionFisica, ActaConstatacion, BodegaVirtual, GruposCategoria
from core.firmar_documentos import firmararchivogenerado
from helpdesk.models import SolicitudConfirmacionMantenimiento, HistorialSolicitudConfirmacionMantenimiento, \
    HdIncidenteProductoDetalle
from sga.commonviews import adduserdata
from sga.forms import SolicitudTraspasoActivoForm
from sga.funciones import MiPaginador, log, generar_nombre, null_to_decimal
from sga.models import Persona
from settings import DEBUG
from django.core.files import File as DjangoFile
from sga.tasks import send_html_mail
from django.contrib import messages
unicode = str


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']

    h = 'https'
    if DEBUG:
        h = 'http'
    base_url = request.META['HTTP_HOST']
    data['DOMINIO_DEL_SISTEMA'] = dominio_sistema = f"{h}://{unicode(base_url)}"

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'confmantenimiento':
                try:
                    solicitud = SolicitudConfirmacionMantenimiento.objects.get(pk=int(encrypt_id(request.POST['id'])))
                    solicitud.estado = 2
                    solicitud.save(request)
                    log(u'Confirmó el mantenimiento realizado: %s' % solicitud, request, "add")
                    historial = HistorialSolicitudConfirmacionMantenimiento(
                        solicitud=solicitud,
                        observacion=solicitud.observacion,
                        estado=solicitud.estado,
                        persona=persona
                    )
                    historial.save(request)
                    log(u'Agrego registro de historial de confirmacion de mantenimiento %s' % (historial.__str__()),
                        request, "add")
                    return JsonResponse({"result": 'ok', "mensaje": "Guardado con éxito", }, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": 'bad', "mensaje": u"Error al guardar los datos. [%s]" % ex})

            elif action == 'confirmanoti':
                try:
                    notificacion = Notificacionactivoresponsable.objects.get(pk=int(request.POST['id']))
                    notificacion.estado = 2
                    notificacion.fechaestado = datetime.now().date()
                    notificacion.horaestado = datetime.now().time()
                    notificacion.save(request)
                    log(u'Confirmó la notificación : %s' % notificacion, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)

            elif action == 'rechazarnoti':
                try:
                    notificacion = Notificacionactivoresponsable.objects.get(pk=int(request.POST['id']))
                    notificacion.estado = 3
                    notificacion.fechaestado = datetime.now().date()
                    notificacion.horaestado = datetime.now().time()
                    notificacion.save(request)
                    log(u'Rechazó la notificación : %s' % notificacion, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)

            elif action == 'confirmalicencia':
                try:
                    notificacion = HdIncidenteProductoDetalle.objects.get(pk=int(request.POST['id']))
                    notificacion.estado = 2
                    notificacion.fechaestado = datetime.now().date()
                    notificacion.horaestado = datetime.now().time()
                    notificacion.save(request)
                    log(u'Confirmó entrega licencia : %s' % notificacion, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)

            elif action == 'rechazalicencia':
                try:
                    notificacion = HdIncidenteProductoDetalle.objects.get(pk=int(request.POST['id']))
                    notificacion.estado = 3
                    notificacion.fechaestado = datetime.now().date()
                    notificacion.horaestado = datetime.now().time()
                    notificacion.save(request)
                    log(u'Rechazó entrega licencia : %s' % notificacion, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)

            elif action == 'rechmantenimiento':
                try:
                    solicitud = SolicitudConfirmacionMantenimiento.objects.get(pk=encrypt_id(request.POST['id']))
                    solicitud.estado = 3
                    solicitud.save(request)
                    log(u'Rechazó el mantenimiento realizado: %s' % solicitud, request, "add")
                    historial = HistorialSolicitudConfirmacionMantenimiento(
                        solicitud=solicitud,
                        observacion=solicitud.observacion,
                        estado=solicitud.estado,
                        persona=persona
                    )
                    historial.save(request)
                    log(u'Agrego registro de historial de confirmacion de mantenimiento %s' % (historial.__str__()),
                        request, "add")
                    return JsonResponse({"result": 'ok', "mensaje": "Guardado con éxito", }, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": 'bad', "mensaje": u"Error al guardar los datos. [%s]" % ex})

            elif action == 'traspasoconfirmado':
                try:
                    solicitud = SolicitudActivos.objects.filter(pk=int(request.POST['id']), status=True)[0]
                    solicitud.estado = 2
                    solicitud.save(request)
                    data['activo'] = solicitud.activo
                    data['solicitante'] = solicitud.solicitante
                    qrname = 'Activo-' + str(solicitud.activo.id)
                    asunto = u"SOLICITUD DE TRASPASO DE ACTIVOS " + solicitud.activo.descripcion
                    send_html_mail(asunto, "emails/notificaractivo.html",
                                   {'sistema': request.session['nombresistema'], 'Activo': solicitud.activo,
                                    'responsable': solicitud.responsableasignacion,
                                    'activo': solicitud.activo.descripcion,
                                    'codigo': solicitud.activo.codigogobierno},
                                   ['dcevalloss1@unemi.edu.ec'], [],
                                   cuenta=CUENTAS_CORREOS[16][1])
                    log(u'Confirmó solicitud traspaso: %s' % solicitud, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    pass

            elif action == 'traspasoeliminar':
                try:
                    id = int(request.POST['id'])
                    solicitud = SolicitudActivos.objects.get(pk=id, status=True)
                    solicitud.estado = 3
                    solicitud.save(request)
                    log(u'Solicitud no confirmada: %s' % solicitud, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    pass

            elif action == 'responsableconfirmatraspaso':
                try:
                    if 'id' in request.POST:
                        solicitud = SolicitudActivos.objects.filter(pk=int(request.POST['id']), status=True)[0]
                        solicitud.estado = 4
                        solicitud.save(request)
                        log(u'Responsable confirmó solicitud traspaso: %s' % solicitud, request, "add")
                        return JsonResponse({"result": "ok"})
                except Exception as ex:
                    pass

            elif action == 'responsableeliminatraspaso':
                try:
                    id = int(request.POST['id'])
                    solicitud = SolicitudActivos.objects.get(pk=id, status=True)
                    solicitud.estado = 5
                    solicitud.save(request)
                    log(u'Responsable rechaza solicitud traspaso: %s' % solicitud, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u'Error al rechazar la solicitud'})

            elif action == 'devolveractivo':
                try:
                    prestamo = PrestamoActivosOperaciones.objects.get(pk=encrypt_id(request.POST['id']))
                    # prestamo.fechadevolucion = datetime.now().date()
                    prestamo.estado = 4
                    prestamo.save(request)
                    log(u'Solicita devolucion activo: %s' % prestamo, request, "act")
                    auditoria = AuditoriaPrestamoActivosOperaciones(
                        prestamo=prestamo,
                        personaentrega=prestamo.personaentrega,
                        personarecibe=prestamo.personarecibe,
                        desde=prestamo.desde,
                        hasta=prestamo.hasta,
                        fechadevolucion=prestamo.fechadevolucion,
                        observacion=prestamo.observacion,
                        estado=8
                    )
                    auditoria.save(request)
                    log(u'Auditoria solicita devuelve activo %s - %s' % (persona, auditoria), request, "add")
                    return JsonResponse({"result": False, "mensaje": "Guardado con exito", }, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos. [%s]" % ex})

            elif action == 'addsolicitudtraspaso':
                try:
                    form = SolicitudTraspasoActivoForm(request.POST)
                    if form.is_valid():

                        # Recibe lista de activos seleccionados para traspaso
                        listado_activos = json.loads(request.POST['lista_items1'])
                        if listado_activos:
                            lista = []
                            for activo in listado_activos:
                                idactivos = activo['id']
                                idactivos = int(idactivos)
                                lista.append(idactivos)
                        else:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u'Por favor, seleccione al menos 1 activo.'})

                        # Verificar si hay activos con solicitudes pendientes de traspaso
                        solicitudespendientes = SolicitudTraspasoActivos.objects.filter(usuarioentrega=persona,
                                                                                        estado__in=[1, 2, 4, 5, 8],
                                                                                        status=True)

                        indice = 0
                        for solicitud in solicitudespendientes:
                            for activo in eval(solicitud.activos):
                                if activo in lista:
                                    indice = 1

                        # Verificar si los activos seleccionados no se encuentran pendientes de traspaso en otras solicitudes
                        if indice == 1:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u'Algunos activos ya cuentan con solicitudes pendientes.'})

                        # Verificar que el usuario bien entrega no sea el mismo que el usuario bien recibe
                        if form.cleaned_data['usuariobienentrega'] == form.cleaned_data['usuariobienrecibe'].id:
                            return JsonResponse({"result": "bad",
                                                 "mensaje": u'El usuario que recibe debe de ser distinto al usuario que entrega.'})

                        nuevasolicitud = SolicitudTraspasoActivos(
                            solicitante=persona,
                            fecha=form.cleaned_data['fecha'],
                            usuarioentrega_id=form.cleaned_data['usuariobienentrega'],
                            custodioentrega_id=form.cleaned_data['custodiobienentrega'],
                            ubicacionentrega_id=form.cleaned_data['ubicacionbienentrega'],
                            usuariorecibe_id=form.cleaned_data['usuariobienrecibe'].id,
                            custodiorecibe_id=form.cleaned_data['custodiobienrecibe'].id,
                            ubicacionrecibe_id=form.cleaned_data['ubicacionbienrecibe'].id,
                            observacion=form.cleaned_data['observacion'],
                            activos=lista,
                            estado=1,
                            quiensolicita=1)
                        nuevasolicitud.save(request)
                        log(u'Nueva solicitud traspaso %s - %s' % (persona, nuevasolicitud), request, "add")

                        # Seguimiento de la solicitud de traspaso
                        seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=nuevasolicitud, estado=1)
                        seguimiento.save(request)
                        seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=nuevasolicitud, estado=2)
                        seguimiento.save(request)
                        log(u'Responsable realiza solicitud traspaso %s - %s' % (persona, seguimiento), request, "add")
                        return JsonResponse({"result": "ok"})
                except Exception as ex:
                    pass

            elif action == 'editarsolicitudtraspaso':
                try:
                    form = SolicitudTraspasoActivoForm(request.POST)
                    if form.is_valid():

                        # Recibe lista de activos seleccionados para traspaso
                        listado_activos = json.loads(request.POST['lista_items1'])
                        if listado_activos:
                            lista = []
                            for activo in listado_activos:
                                idactivos = activo['id']
                                idactivos = int(idactivos)
                                lista.append(idactivos)
                        else:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u'Por favor, seleccione al menos 1 activo.'})

                        # Verificar si hay activos con solicitudes pendientes de traspaso
                        solicitudespendientes = SolicitudTraspasoActivos.objects.filter(usuarioentrega=persona,
                                                                                        estado__in=[1, 2, 4, 5, 8],
                                                                                        status=True).exclude(
                            id=int(request.POST['id']))

                        indice = 0
                        for solicitud in solicitudespendientes:
                            for activo in eval(solicitud.activos):
                                if activo in lista:
                                    indice = 1

                        # Verificar si los activos seleccionados no se encuentran pendientes de traspaso en otras solicitudes
                        if indice == 1:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u'Algunos activos ya cuentan con solicitudes pendientes.'})

                        # Verificar que el usuario bien entrega no sea el mismo que el usuario bien recibe
                        if form.cleaned_data['usuariobienentrega'] == form.cleaned_data['usuariobienrecibe'].id:
                            return JsonResponse({"result": "bad",
                                                 "mensaje": u'El usuario que recibe debe de ser distinto al usuario que entrega.'})

                        editarsolicitud = SolicitudTraspasoActivos.objects.get(id=int(request.POST['id']))
                        editarsolicitud.fecha = form.cleaned_data['fecha']
                        editarsolicitud.usuariorecibe_id = form.cleaned_data['usuariobienrecibe'].id
                        editarsolicitud.custodiorecibe_id = form.cleaned_data['custodiobienrecibe'].id
                        editarsolicitud.ubicacionrecibe_id = form.cleaned_data['ubicacionbienrecibe'].id
                        editarsolicitud.observacion = form.cleaned_data['observacion']
                        editarsolicitud.activos = lista
                        editarsolicitud.save(request)
                        if editarsolicitud.estado == 1:
                            log(u'Edita solicitud traspaso %s - %s' % (persona, editarsolicitud), request, "act")
                        elif editarsolicitud.estado == 20:
                            editarsolicitud.estado = 21
                            editarsolicitud.save(request)
                            log(u'Corrige solicitud traspaso %s - %s' % (persona, editarsolicitud), request, "act")
                            seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=editarsolicitud, estado=21)
                            seguimiento.save(request)
                            editarsolicitud.estado == 1
                        return JsonResponse({"result": "ok"})
                except Exception as ex:
                    pass

            elif action == 'confirmasolicitudcustodiorecibe':
                try:
                    idsolicitud = int(request.POST['id'])
                    confirmasolicitud = SolicitudTraspasoActivos.objects.get(id=idsolicitud)
                    texto_log = ''
                    confirmasolicitud.estado = 17
                    seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=confirmasolicitud, estado=17)
                    texto_log = 'Custodio recibe'
                    confirmasolicitud.save(request)
                    log(texto_log + u' acepta solicitud traspaso %s - %s' % (persona, confirmasolicitud), request,
                        "act")
                    seguimiento.save(request)
                    log(texto_log + u' acepta solicitud traspaso %s - %s' % (persona, seguimiento), request, "add")

                    # Nuevo traspaso por sistema
                    traspaso = TraspasoActivo(custodiobienrecibe=confirmasolicitud.custodiorecibe,
                                              usuariobienentrega=confirmasolicitud.usuarioentrega,
                                              custodiobienentrega=confirmasolicitud.custodioentrega,
                                              usuariobienrecibe=confirmasolicitud.usuariorecibe,
                                              ubicacionbienentrega=confirmasolicitud.ubicacionentrega,
                                              responsablebienes_id=1204,
                                              ubicacionbienrecibe=confirmasolicitud.ubicacionrecibe,
                                              fecha=confirmasolicitud.fecha,
                                              solicitante=confirmasolicitud.solicitante,
                                              fechaoficio=confirmasolicitud.fecha,
                                              observacion=confirmasolicitud.observacion,
                                              tiposolicitud=5,
                                              tipotraspaso=1,
                                              tipo=2)
                    traspaso.save(request)
                    log(u'Adicionó traspaso activo: %s' % traspaso, request, "add")

                    # Recorrer los activos seleccionados y guardarlos en DetalleTraspasoActivo
                    for activo in eval(confirmasolicitud.activos):
                        detalletraspaso = DetalleTraspasoActivo(codigotraspaso=traspaso,
                                                                activo_id=activo,
                                                                seleccionado=True)
                        detalletraspaso.save(request)
                        log(u'Se registran activos para el traspaso: %s' % detalletraspaso, request, "add")
                    # Solicitud actualiza a estado TRASPASO PENDIENTE
                    confirmasolicitud.traspasoactivofijo = traspaso
                    confirmasolicitud.estado = 8
                    confirmasolicitud.save(request)
                    log(u'Traspaso pendiente %s - %s' % (persona, confirmasolicitud), request, "act")

                    # Seguimiento solicitud traspaso
                    seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=confirmasolicitud, estado=8)
                    seguimiento.save(request)
                    asunto = u"Solicitud de traspaso recibida"
                    para = Persona.objects.get(id=1204)
                    notificacion(asunto, confirmasolicitud.observacion, para, None,
                                 '/af_activofijo?action=movimientos&id=' + str(traspaso.pk), traspaso.pk, 1, 'sagest',
                                 TraspasoActivo, request)
                    log(u'Traspaso activo pendiente %s - %s' % (persona, seguimiento), request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u'Error al confirmar la solicitud'})

            elif action == 'confirmasolicitudusuariorecibe':
                try:
                    idsolicitud = int(request.POST['id'])
                    confirmasolicitud = SolicitudTraspasoActivos.objects.get(id=idsolicitud)
                    texto_log = ''

                    if confirmasolicitud.quiensolicita == 1:
                        confirmasolicitud.estado = 4
                        seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=confirmasolicitud, estado=4)
                        texto_log = 'Usuario recibe'

                    if confirmasolicitud.quiensolicita == 2:
                        if confirmasolicitud.estado == 1:
                            confirmasolicitud.estado = 2
                            seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=confirmasolicitud, estado=2)
                            texto_log = 'Usuario entrega'

                        if confirmasolicitud.estado == 2:
                            confirmasolicitud.estado = 4
                            seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=confirmasolicitud, estado=4)
                            texto_log = 'Usuario recibe'

                    confirmasolicitud.save(request)
                    log(texto_log + u' acepta solicitud traspaso %s - %s' % (persona, confirmasolicitud), request,
                        "act")
                    seguimiento.save(request)
                    log(texto_log + u' acepta solicitud traspaso %s - %s' % (persona, seguimiento), request, "add")
                    return JsonResponse({"result": "ok", "mensaje": u'Solicitud confirmada con éxito.'})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u'Error al confirmar la solicitud'})

            elif action == 'rechazasolicitudusuariorecibe':
                try:
                    idsolicitud = int(request.POST['id'])
                    rechazasolicitud = SolicitudTraspasoActivos.objects.get(id=idsolicitud)

                    if rechazasolicitud.quiensolicita == 1:
                        rechazasolicitud.estado = 20
                        seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=rechazasolicitud, estado=5)
                        texto_log = 'Futuro responsable'

                    if rechazasolicitud.quiensolicita == 2:
                        if rechazasolicitud.estado == 1:
                            rechazasolicitud.estado = 3
                            seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=rechazasolicitud, estado=3)
                            texto_log = 'Responsable'

                    if rechazasolicitud.estado == 2:
                        rechazasolicitud.estado = 20
                        seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=rechazasolicitud, estado=5)
                        texto_log = 'Futuro responsable'

                    rechazasolicitud.save(request)
                    log(texto_log + u' rechaza solicitud traspaso %s - %s' % (persona, rechazasolicitud), request,
                        "act")
                    seguimiento.save(request)
                    log(texto_log + u' rechaza solicitud traspaso %s - %s' % (persona, seguimiento), request, "add")
                    seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=rechazasolicitud, estado=20)
                    seguimiento.save(request)
                    if rechazasolicitud.quiensolicita == 1:
                        correccion = CorreccionesSolicitudTraspasoActivos(solicitudtraspaso=rechazasolicitud,
                                                                          observacion=request.POST[
                                                                              'observacionrechazo'], estado=5)
                        correccion.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u'Error al rechazar la solicitud'})

            elif action == 'rechazasolicitudcustodiorecibe':
                try:
                    idsolicitud = int(request.POST['id'])
                    rechazasolicitud = SolicitudTraspasoActivos.objects.get(id=idsolicitud)

                    rechazasolicitud.estado = 20
                    seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=rechazasolicitud, estado=18)
                    texto_log = 'Custodio recibe'
                    rechazasolicitud.save(request)
                    log(texto_log + u' rechaza solicitud traspaso %s - %s' % (persona, rechazasolicitud), request,
                        "act")
                    seguimiento.save(request)
                    log(texto_log + u' rechaza solicitud traspaso %s - %s' % (persona, seguimiento), request, "add")
                    seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=rechazasolicitud, estado=20)
                    seguimiento.save(request)
                    correccion = CorreccionesSolicitudTraspasoActivos(solicitudtraspaso=rechazasolicitud,
                                                                      observacion=request.POST['message'],
                                                                      estado=18)
                    correccion.save(request)
                    return JsonResponse({"result": "ok", "mensaje": u'Solicitud rechazada con éxito.'})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u'Error al rechazar la solicitud'})

            elif action == 'cancelarsolicitud':
                try:
                    cancelasolicitud = SolicitudTraspasoActivos.objects.get(id=int(request.POST['id']))
                    cancelasolicitud.estado = 7
                    cancelasolicitud.save(request)
                    log(u'Responsable cancela solicitud traspaso %s - %s' % (persona, cancelasolicitud), request, "act")
                    seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=cancelasolicitud, estado=7)
                    seguimiento.save(request)
                    log(u'Responsable cancela solicitud traspaso %s - %s' % (persona, seguimiento), request, "add")
                    return JsonResponse({"result": "ok", "mensaje": u'Solicitud cancelada con éxito.', "showSwal": True})
                except Exception as ex:
                    pass

            elif action == 'firmardocumento':
                try:
                    # Parametros
                    txtFirmas = json.loads(request.POST['txtFirmas'])
                    if not txtFirmas:
                        raise NameError("Debe seleccionar ubicación de la firma")
                    x = txtFirmas[-1]
                    idtraspaso = int(encrypt(request.POST['id_objeto']))
                    responsables = request.POST.getlist('responsables[]')
                    firma = request.FILES["firma"]
                    passfirma = request.POST['palabraclave']
                    url_archivo = (SITE_STORAGE + request.POST["url_archivo"]).replace('\\', '/')
                    _name = generar_nombre(f'actatraspasoactivo{request.user.username}_{idtraspaso}_', 'firmada')
                    folder = os.path.join(SITE_STORAGE, 'media', 'traspasoactivofirma', '')

                    # Firmar y guardar archivo en folder definido.
                    firma = firmararchivogenerado(request, passfirma, firma, url_archivo, folder, _name, x["numPage"],
                                                  x["x"], x["y"], x["width"], x["height"])
                    if firma != True:
                        raise NameError(firma)
                    log(u'Firmo Documento: {}'.format(_name), request, "add")

                    folder_save = os.path.join('traspasoactivofirma', '').replace('\\', '/')
                    url_file_generado = f'{folder_save}{_name}.pdf'
                    actualizaracta = TraspasoActivo.objects.get(id=int(idtraspaso))
                    actualizaracta.traspasoactivofirma = url_file_generado
                    actualizaracta.save(request)
                    log(u'Guardo archivo firmado: {}'.format(actualizaracta), request, "act")
                    solicitudtraspaso = SolicitudTraspasoActivos.objects.get(traspasoactivofijo_id=int(idtraspaso))
                    asunto = ''
                    if solicitudtraspaso.usuarioentrega == persona and solicitudtraspaso.custodioentrega == persona:
                        if solicitudtraspaso.firmaresponsable == False and solicitudtraspaso.firmacustodioentrega == False:
                            solicitudtraspaso.firmaresponsable = True
                            seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=solicitudtraspaso, estado=12)
                            asunto = u"Usuario entrega firma acta de traspaso"
                        else:
                            if solicitudtraspaso.firmaresponsable == False:
                                solicitudtraspaso.firmaresponsable = True
                                seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=solicitudtraspaso,
                                                                           estado=12)
                                asunto = u"Usuario entrega firma acta de traspaso"
                            elif solicitudtraspaso.firmacustodioentrega == False:
                                solicitudtraspaso.firmacustodioentrega = True
                                seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=solicitudtraspaso,
                                                                           estado=15)
                                asunto = u"Custodio entrega firma acta de traspaso"
                    else:
                        if solicitudtraspaso.usuariorecibe == persona and solicitudtraspaso.custodiorecibe == persona:
                            if solicitudtraspaso.firmafuturoresponsable == False and solicitudtraspaso.firmacustodiorecibe == False:
                                solicitudtraspaso.firmafuturoresponsable = True
                                seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=solicitudtraspaso,
                                                                           estado=13)
                                asunto = u"Usuario recibe firma acta de traspaso"
                            else:
                                if solicitudtraspaso.firmafuturoresponsable == False:
                                    solicitudtraspaso.firmafuturoresponsable = True
                                    seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=solicitudtraspaso,
                                                                               estado=13)
                                    asunto = u"Usuario recibe firma acta de traspaso"
                                elif solicitudtraspaso.firmacustodiorecibe == False:
                                    solicitudtraspaso.firmacustodiorecibe = True
                                    seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=solicitudtraspaso,
                                                                               estado=16)
                                    asunto = u"Custodio recibe firma acta de traspaso"
                        else:

                            if solicitudtraspaso.usuarioentrega == persona:
                                solicitudtraspaso.firmaresponsable = True
                                seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=solicitudtraspaso,
                                                                           estado=12)
                                asunto = u"Usuario entrega firma acta de traspaso"
                            elif solicitudtraspaso.usuariorecibe == persona:
                                solicitudtraspaso.firmafuturoresponsable = True
                                seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=solicitudtraspaso,
                                                                           estado=13)
                                asunto = u"Usuario recibe firma acta de traspaso"

                            elif solicitudtraspaso.custodioentrega == persona:
                                solicitudtraspaso.firmacustodioentrega = True
                                seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=solicitudtraspaso,
                                                                           estado=15)
                                asunto = u"Custodio entrega firma acta de traspaso"
                            elif solicitudtraspaso.custodiorecibe == persona:
                                solicitudtraspaso.firmacustodiorecibe = True
                                seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=solicitudtraspaso,
                                                                           estado=16)
                                asunto = u"Custodio recibe firma acta de traspaso"
                                # if persona.id == 1204:
                                #     solicitudtraspaso.firmaactivofijo = True
                                #     seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=solicitudtraspaso, estado=14)
                    solicitudtraspaso.save(request)
                    log(u'Firman participantes: {}'.format(solicitudtraspaso), request, "act")
                    seguimiento.save(request)
                    log(u'Seguimiento solicitud traspaso activo: {}'.format(seguimiento), request, "add")
                    para = Persona.objects.get(id=1204)
                    notificacion(asunto, solicitudtraspaso.observacion, para, None,
                                 '/af_activofijo?action=movimientos&id=' + str(solicitudtraspaso.traspasoactivofijo_id),
                                 solicitudtraspaso.pk, 1, 'sagest',
                                 TraspasoActivo, request)
                    if solicitudtraspaso.firmaresponsable == True and solicitudtraspaso.firmafuturoresponsable == True and solicitudtraspaso.firmaactivofijo == True and solicitudtraspaso.firmacustodioentrega == True and solicitudtraspaso.firmacustodiorecibe == True:
                        solicitudtraspaso.puedefirmar = False
                        solicitudtraspaso.estado = 6
                        solicitudtraspaso.save(request)
                        seguimiento = SeguimientoSolicitudTraspaso(solicitudtraspaso=solicitudtraspaso, estado=6)
                        seguimiento.save(request)
                        log(u'Solicitud traspaso activo finalizado: {}'.format(seguimiento), request, "add")
                    # return JsonResponse({"result": False, "mensaje": "Guardado con exito",}, safe=False)
                    return HttpResponseRedirect("/mis_activos")
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar. %s" % ex.__str__()},
                                        safe=False)

            elif action == 'cerrarconstatacion':
                try:
                    id = int(encrypt(request.POST['id']))
                    instancia = CronogramaPersonaConstatacionAT.objects.get(id=id)
                    instancia.estado = 4
                    instancia.fechacierre = datetime.now()
                    instancia.save(request)
                    # titulo = u"Finalización de constatación fisica de activos"
                    # mensaje = u"Por favor revisar la constatacion realizada y confirme que todo esta en orden"
                    # notificacion(titulo, mensaje, instancia.persona, None,
                    #              f'/mis_activos?action=constataciones&id={encrypt(instancia.id)}',
                    #              instancia.pk, 1, 'sga', CronogramaPersonaConstatacionAT, request)
                    log(u'Cambio de estado a cerrado: %s' % instancia, request, "edit")
                    res_json = {"result": True}
                except Exception as ex:
                    res_json = {'result': False, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            elif action == 'firmaracta':
                try:
                    # Parametros
                    txtFirmas = json.loads(request.POST['txtFirmas'])
                    if not txtFirmas:
                        raise NameError("Debe seleccionar ubicación de la firma")
                    x = txtFirmas[-1]
                    id_cronograma = int(encrypt(request.POST['id_objeto']))
                    responsables = request.POST.getlist('responsables[]')
                    firma = request.FILES["firma"]
                    passfirma = request.POST['palabraclave']
                    url_archivo = (SITE_STORAGE + request.POST["url_archivo"]).replace('\\', '/')
                    _name = generar_nombre(f'actafirmada_{request.user.username}_{id_cronograma}_', 'firmada')
                    folder = os.path.join(SITE_STORAGE, 'media', 'activostecnologicos/acta_constatacion/', '')

                    # Firmar y guardar archivo en folder definido.
                    firma = firmararchivogenerado(request, passfirma, firma, url_archivo, folder, _name, x["numPage"], x["x"], x["y"], x["width"], x["height"])
                    if firma != True:
                        raise NameError(firma)
                    folder_save = os.path.join('activostecnologicos/acta_constatacion/', '').replace('\\', '/')
                    url_file_generado = f'{folder_save}{_name}.pdf'
                    historial = HistorialDocumentosFirmadosConstatacionAT(cronograma_id=id_cronograma, persona=persona, orden=2)
                    historial.save(request)
                    historial.archivo = url_file_generado
                    historial.save(request)
                    log(u'Guardo archivo firmado: {}'.format(historial), request, "add")
                    return JsonResponse({"result": False, "mensaje": "Guardado con exito", }, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": u"Error al guardar. %s" % ex.__str__()}, safe=False)

            elif action == 'firmaractaconstatacion':
                try:
                    id = encrypt_id(request.POST['id'])
                    constatacion = ConstatacionFisica.objects.get(pk=id)
                    documento_a_firmar = constatacion.get_documento()
                    certificado = request.FILES["firma"]
                    contrasenaCertificado = request.POST['palabraclave']
                    razon = request.POST['razon'] if 'razon' in request.POST else ''
                    jsonFirmas = json.loads(request.POST['txtFirmas'])
                    _name, extension_documento_a_firmar = f'acta_constatacion_{constatacion.usuariobienes.usuario.username}', '.pdf'
                    extension_certificado = os.path.splitext(certificado.name)[1][1:]
                    bytes_certificado = certificado.read()
                    if not jsonFirmas:
                        raise NameError("Debe seleccionar ubicación de la firma")
                    for membrete in jsonFirmas:
                        datau = JavaFirmaEc(
                            archivo_a_firmar=documento_a_firmar, archivo_certificado=bytes_certificado, extension_certificado=extension_certificado,
                            password_certificado=contrasenaCertificado,
                            page=int(membrete["numPage"]), reason=razon, lx=membrete["x"], ly=membrete["y"]
                        ).sign_and_get_content_bytes()
                        documento_a_firmar = io.BytesIO()
                        documento_a_firmar.write(datau)
                        documento_a_firmar.seek(0)

                    file_obj = DjangoFile(documento_a_firmar, name=f"{_name}.pdf")
                    constatacion.estadoacta = 4
                    constatacion.save(request)
                    log(u'Remito acta a usuario para firmar: {}'.format(constatacion), request, "edit")
                    acta = ActaConstatacion(constatacion=constatacion,
                                            archivo=file_obj,
                                            estado=2,
                                            persona=persona)
                    acta.save(request)
                    log(u'Firmo Documento: {}'.format(_name), request, "add")

                    return JsonResponse({'result': False, 'mensaje': 'Guardado correctamente'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

            elif action == 'addactivobodegavirtual':
                try:
                    id = encrypt_id(request.POST['id'])
                    activo = ActivoFijo.objects.get(pk=id)
                    f = ActivoBodegaVirtualForm(request.POST, request.FILES)
                    if f.is_valid():
                        bodega = BodegaVirtual(
                            activo=activo,
                            responsable=activo.responsable,
                            custodio=activo.custodio,
                            observacion=f.cleaned_data['observacion'].strip().upper(),
                            foto=f.cleaned_data['fotoactivo'],
                        )
                        bodega.save(request)

                        log(u'Adicionó activo a bodega virtual: %s' % bodega, request, "add")
                        return JsonResponse({'result': False, 'mensaje': 'Guardado correctamente'})
                    return JsonResponse({'result': True, 'mensaje': 'Error al guardar los datos.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

            elif action == 'quitaractivodebodegav':
                try:
                    id = encrypt_id(request.POST['id'])
                    activobv = BodegaVirtual.objects.get(pk=id)
                    activobv.status = False
                    activobv.save(request)
                    log(u'Eliminó activo de bodega virtual: %s' % activobv, request, "del")
                    return JsonResponse({'result': 'ok', 'mensaje': 'Removido de la bodega virtual correctamente'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', "mensaje": 'Error: {}'.format(ex)}, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action']= action = request.GET['action']

            if action == 'confmantenimiento':
                try:
                    data['title'] = u'Confirmar mantenimiento'
                    data['mantenimiento'] = SolicitudConfirmacionMantenimiento.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_hojavida/modal/confmantenimiento.html", data)
                except:
                    pass

            elif action == 'rechmantenimiento':
                try:
                    data['title'] = u'Rechazar mantenimiento'
                    data['mantenimiento'] = SolicitudConfirmacionMantenimiento.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_hojavida/modal/rechmantenimiento.html", data)
                except:
                    pass

            elif action == 'traspasoconfirmado':
                try:
                    data['title'] = u'Confirmar Solicitud'
                    data['responsable'] = int(request.GET['responsable'])
                    data['solicitud'] = int(request.GET['solicitud'])
                    data['traspaso'] = ActivoFijo.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_hojavida/traspasoconfirmado.html", data)
                except:
                    pass

            elif action == 'traspasoeliminar':
                try:
                    data['title'] = u'Confirmar eliminación'
                    data['traspaso'] = int(request.GET['id'])
                    return render(request, "th_hojavida/traspasoeliminar.html", data)
                except:
                    pass

            elif action == 'responsableconfirmatraspaso':
                try:
                    data['title'] = u'Confirmar Solicitud'
                    data['responsable'] = int(request.GET['responsable'])
                    data['solicitud'] = int(request.GET['solicitud'])
                    data['traspaso'] = ActivoFijo.objects.get(pk=int(request.GET['id']))
                    return render(request, "th_hojavida/responsableconfirmatraspaso.html", data)
                except:
                    pass

            elif action == 'responsableeliminatraspaso':
                try:
                    data['title'] = u'Confirmar eliminación'
                    data['traspaso'] = int(request.GET['id'])
                    return render(request, "th_hojavida/responsableeliminatraspaso.html", data)
                except:
                    pass

            elif action == 'addsolicitudtraspaso':
                try:
                    data['title'] = u'Nueva solicitud traspaso'
                    persona_activo = Persona.objects.filter(status=True, id=persona.id).values_list(
                        'responsableactivo__ubicacion')
                    if persona_activo[0][0] != None:
                        ubicacionentrega = Ubicacion.objects.get(id=persona_activo[0][0])
                        custodioentrega = Persona.objects.filter(custodioactivo__ubicacion_id=persona_activo[0][0],
                                                                 custodioactivo__responsable=persona,
                                                                 custodioactivo__statusactivo=1)
                        data['listadoactivos'] = listadoactivos = ActivoFijo.objects.filter(status=True,
                                                                                            responsable=persona)
                        form = SolicitudTraspasoActivoForm()
                        form.cargar_ubicacionbienentrega(ubicacionentrega)
                        form.cargar_usuariobienentrega(persona)
                        form.cargar_custodiobienentrega(custodioentrega[0])
                        data['form'] = form
                        return render(request, "mis_activos/addsolicitudtraspaso.html", data)
                    else:
                        # return JsonResponse({"result":False, "mensaje": u'Usted no cuenta con activos bajo su cargo'})
                        return HttpResponseRedirect("/mis_activos?info=Usted no cuenta con activos bajo su cargo")
                except Exception as ex:
                    pass

            elif action == 'detallesolicitudtraspaso':
                try:
                    solicitudtraspaso = SolicitudTraspasoActivos.objects.filter(id=encrypt_id(request.GET['id'])).order_by('-id')
                    data['listadoactivos'] = ActivoFijo.objects.filter(status=True,
                                                                       id__in=eval(solicitudtraspaso[0].activos))
                    data['solicitudtraspaso'] = solicitudtraspaso
                    template = get_template('mis_activos/modal/detallesolicitudtraspaso.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'recorridosolicitud':
                try:
                    seguimientosolicitud = SeguimientoSolicitudTraspaso.objects.filter(
                        solicitudtraspaso_id=encrypt_id(request.GET['id'])).order_by('-id')
                    data['seguimientosolicitud'] = seguimientosolicitud
                    template = get_template('mis_activos/modal/recorridosolicitud.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'firmaractatraspaso':
                try:
                    solicitudtraspaso = SolicitudTraspasoActivos.objects.get(id=int(request.GET['id']))
                    traspasoactivoporfirmar = TraspasoActivo.objects.get(id=solicitudtraspaso.traspasoactivofijo_id)
                    data['action_firma'] = 'firmardocumento'
                    data['id_objeto'] = traspasoactivoporfirmar.id
                    data['archivo'] = archivoporfirmar = '/media/' + traspasoactivoporfirmar.traspasoactivofirma.name
                    data['url_archivo'] = '{}{}'.format(dominio_sistema,
                                                        '/media/' + traspasoactivoporfirmar.traspasoactivofirma.name)
                    template = get_template("formfirmaelectronica.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editarsolicitudtraspaso':
                try:
                    data['title'] = u'Editar solicitud traspaso'
                    data['solicitudtraspaso'] = solicitudtraspaso = SolicitudTraspasoActivos.objects.get(
                        id=int(request.GET['id']))
                    form = SolicitudTraspasoActivoForm(initial={'desde': solicitudtraspaso.fecha,
                                                                'observacion': solicitudtraspaso.observacion})
                    form.cargar_ubicacionbienentrega(solicitudtraspaso.ubicacionentrega)
                    form.cargar_usuariobienentrega(solicitudtraspaso.usuarioentrega)
                    form.cargar_custodiobienentrega(solicitudtraspaso.custodioentrega)
                    data['form'] = form
                    data['listadoactivos'] = listadoactivos = ActivoFijo.objects.filter(
                        id__in=eval(solicitudtraspaso.activos), status=True)
                    listadoactivos = listadoactivos.values_list('id', flat=True)
                    data['activosnoelegidos'] = ActivoFijo.objects.filter(status=True, responsable=persona).exclude(
                        id__in=listadoactivos)
                    return render(request, "mis_activos/editarsolicitudtraspaso.html", data)
                except Exception as ex:
                    pass

            elif action == 'correccionessolicitudtraspaso':
                try:
                    data['correcciones'] = CorreccionesSolicitudTraspasoActivos.objects.filter(status=True,
                                                                                               solicitudtraspaso_id=encrypt_id(
                                                                                                   request.GET['id'])).order_by('-id')
                    template = get_template("mis_activos/modal/correccionessolicitudtraspaso.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'constataciones':
                try:
                    data['title'] = u'Constataciones'
                    data['id'] = id = request.GET['id']
                    data['cronograma'] = cronograma = CronogramaPersonaConstatacionAT.objects.get(id=int(encrypt(id)))
                    estado, search, filtro, url_vars = int(request.GET.get('estado', '0')), request.GET.get('s', ''), Q(
                        status=True, cronograma_id=cronograma.id), f'&action={action}&id={id}'
                    if search:
                        filtro = filtro & (Q(activo__descripcion__unaccent__icontains=search) | Q(
                            activo__activotecnologico__codigogobierno__icontains=search) | Q(
                            activo__codigotic__icontains=search))
                        url_vars += '&s=' + search
                        data['s'] = search

                    if estado != 0:
                        url_vars += f'&estado={estado}'
                        data['estado'] = estado
                        constatado = True if estado == 1 else False
                        filtro = filtro & Q(constatado=constatado)

                    listado = DetalleConstatacionFisicaActivoTecnologico.objects.filter(filtro)
                    paging = MiPaginador(listado, 10)
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
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    data['t_constatados'] = t_constatados = len(cronograma.constataciones().filter(constatado=True))
                    data['t_activos'] = t_activos = len(cronograma.constataciones())
                    data['t_porconstatar'] = t_activos - t_constatados

                    return render(request, 'mis_activos/constataciones.html', data)
                except Exception as ex:
                    return render({'result': False, 'mensaje': '{}'.format(ex)})

            elif action == 'detalle_activo':
                try:
                    data['activo'] = activo = ActivoFijo.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("at_activostecnologicos/detalleActM.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'detalleconstatacion':
                try:
                    data['detalle_cat'] = DetalleConstatacionFisicaActivoTecnologico.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("mis_activos/modal/detalleconstatacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'viewlistnotificaciones':
                try:
                    data['title'] = u'Solicitud de proceso a un activo'
                    search, url_vars = request.GET.get('s', ''), ''
                    url_vars = f"&action=viewlistnotificaciones"
                    filtro = Q(status=True) & Q(responsable_id=persona.id)
                    if search:
                        data['s'] = search = request.GET['s'].strip()
                        ss = search.split(' ')
                        url_vars += "&s={}".format(search)
                        if len(ss) == 1:
                            filtro = filtro & (Q(activo__descripcion__icontains=search) |
                                               Q(activo__codigogobierno__icontains=search) |
                                               Q(asunto__icontains=search) |
                                               Q(detalle__icontains=search) |
                                               Q(activo__codigointerno__icontains=search) |
                                               Q(activo__modelo__icontains=search) |
                                               Q(responsable__nombres__icontains=search) |
                                               Q(responsable__apellido1__icontains=search) |
                                               Q(responsable__apellido2__icontains=search))
                        else:
                            filtro = filtro & (Q(responsable__apellido1__unaccent__icontains=ss[0]) &
                                               Q(responsable__apellido2__unaccent__icontains=ss[1]))



                        url_vars += f"&s={search}"
                    componente = Notificacionactivoresponsable.objects.filter(filtro).order_by('estado')
                    paging = MiPaginador(componente, 25)
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
                    data['notificaciones'] = page.object_list
                    data['url_vars'] = url_vars
                    data['usuario'] = request.user
                    return render(request, 'at_activostecnologicos/listnotificacionresponsable.html', data)

                except Exception as ex:
                    pass

            elif action == 'viewnotificacionlicencia':
                try:
                    data['title'] = u'Notificaciones'
                    search, url_vars = request.GET.get('s', ''), ''
                    url_vars = f"&action=viewnotificacionlicencia"
                    filtro = Q(status=True) & Q(incidente__persona_id=persona.id) & Q(producto__grupo_id=26)
                    if search:
                        data['s'] = search = request.GET['s'].strip()
                        ss = search.split(' ')
                        url_vars += "&s={}".format(search)
                        if len(ss) == 1:
                            filtro = filtro & (Q(incidente__asunto__icontains=search) |
                                               Q(producto__descripcion__icontains=search))

                        url_vars += f"&s={search}"
                    instancia = HdIncidenteProductoDetalle.objects.filter(filtro).order_by('estado')
                    paging = MiPaginador(instancia, 25)
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
                    data['notificaciones'] = page.object_list
                    data['url_vars'] = url_vars
                    data['usuario'] = request.user
                    return render(request, 'at_activostecnologicos/listnotificacionlicencia.html', data)

                except Exception as ex:
                    pass

            elif action == 'rpt_mis_activos':
                try:
                    filtro = Q(status=True, responsable=persona, statusactivo=1, catalogo__clasificado=True)
                    report_title = 'REPORTE DE MIS ACTIVOS '
                    activos = ActivoFijo.objects.filter(filtro).order_by('ubicacion', 'descripcion')
                    tipoarchivo = request.GET.get('tpa')
                    data['url_path'] = url_path = request.build_absolute_uri('/')[:-1].strip("/")
                    if tipoarchivo == '1':
                        data['listado'] = activos
                        data['fechaactual'] = ahora = datetime.now()
                        data['report_title'] = report_title
                        time_codigo = ahora.strftime('%Y%m%d_%H%M%S')
                        data['name_file'] = name_file = f'reporte_mis_activos{time_codigo}.pdf'
                        template_ = 'mis_activos/pdf/rpt_activos.html'
                        data['pagesize'] = 'A4'
                        return conviert_html_to_pdf(template_, data)

                    if tipoarchivo == '2':
                        __author__ = 'Unemi'
                        ahora = datetime.now()
                        time_codigo = ahora.strftime('%Y%m%d_%H%M%S')
                        name_file = f'reporte_excel_mis_activos_{time_codigo}.xlsx'
                        output = io.BytesIO()
                        workbook = xlsxwriter.Workbook(output)
                        ws = workbook.add_worksheet("LiquidacionesCompras")

                        fuentecabecera = workbook.add_format({
                            'align': 'center',
                            'bg_color': 'silver',
                            'border': 1,
                            'bold': 1
                        })

                        formatoceldafecha = workbook.add_format({
                            'num_format': 'dd/mm/yyyy',
                            'border': 1,
                            'valign': 'vcenter',
                            'align': 'center'
                        })

                        formatoceldacenter = workbook.add_format({
                            'border': 1,
                            'valign': 'vcenter',
                            'align': 'center'})

                        fuenteencabezado = workbook.add_format({
                            'align': 'center',
                            'bg_color': '#1C3247',
                            'font_color': 'white',
                            'border': 1,
                            'font_size': 24,
                            'bold': 1
                        })
                        columnas = [
                            ('Código gobierno', 40),
                            ('Código interno', 40),
                            ('Activo', 40),
                            ('Descripcion', 40),
                            ('Ubicación', 50),
                            ('Serie', 20),
                            ('Modelo', 10),
                            ('Marca', 10),
                            ('Valor', 10),
                            ('Proc. Baja', 10),
                            ('Infor. Baja', 10),
                            ('Estado', 10),
                            ('Archivo', 10)
                        ]
                        ws.merge_range(0, 0, 0, columnas.__len__() - 1, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', fuenteencabezado)
                        ws.merge_range(1, 0, 1, columnas.__len__() - 1, report_title, fuenteencabezado)
                        row_num, numcolum = 2, 0

                        for col_name in columnas:
                            ws.write(row_num, numcolum, col_name[0], fuentecabecera)
                            ws.set_column(numcolum, numcolum, col_name[1])
                            numcolum += 1

                        row_num += 1
                        for activo in activos:
                            ws.write(row_num, 0, activo.codigogobierno, formatoceldacenter)
                            ws.write(row_num, 1, activo.codigointerno, formatoceldacenter)#.strftime('%d/%m/%Y')
                            ws.write(row_num, 2, activo.catalogo.__str__(), formatoceldacenter)#.strftime('%d/%m/%Y')
                            ws.write(row_num, 3, activo.descripcion, formatoceldacenter)
                            ws.write(row_num, 4, activo.ubicacion.__str__(), formatoceldacenter)
                            ws.write(row_num, 5, activo.serie, formatoceldacenter)
                            ws.write(row_num, 6, activo.modelo.__str__(), formatoceldacenter)
                            ws.write(row_num, 7, activo.marca.__str__(), formatoceldacenter)
                            ws.write(row_num, 8, null_to_decimal(activo.costo, 2), formatoceldacenter)
                            ws.write(row_num, 9, 'SI' if activo.procesobaja else 'NO', formatoceldacenter)
                            ws.write(row_num, 10, 'SI' if activo.existeinformebaja() else 'NO', formatoceldacenter)
                            ws.write(row_num, 11, activo.estado.__str__(), formatoceldacenter)
                            ws.write(row_num, 12, f"{url_path}{activo.archivobaja.url}"if activo.archivobaja else '', formatoceldacenter)
                            row_num += 1
                        workbook.close()
                        output.seek(0)
                        response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                        response['Content-Disposition'] = f'attachment; filename="{name_file}"'
                        return response
                except Exception as ex:
                    pass

            elif action == 'firmaracta':
                try:
                    cronograma = CronogramaPersonaConstatacionAT.objects.get(id=request.GET['id'])
                    data['archivo'] = archivo = cronograma.acta_firmada_orden_1().archivo.url
                    data['url_archivo'] = '{}{}'.format(dominio_sistema, archivo)
                    data['id_objeto'] = cronograma.id
                    data['action_firma'] = 'firmaracta'
                    template = get_template("formfirmaelectronica.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'det_constatacion':
                try:
                    data['constatacion'] = constatacion = ConstatacionFisica.objects.get(pk=encrypt_id(request.GET['id']))
                    data['detallepert'] = detalles = constatacion.detalleconstatacionfisica_set.filter(
                        perteneceusuario=True)
                    data['detallenopert'] = detalles = constatacion.detalleconstatacionfisica_set.filter(
                        perteneceusuario=False)
                    data['detallenoiden'] = detalles = constatacion.detallenoidentificado_set.all()
                    template = get_template("af_activofijo/detallecons.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'firmaractaconstatacion':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    qr = qrImgFirma(request, persona, "png", paraMostrar=True)
                    data["qrBase64"] = qr[0]
                    data['filtro'] = filtro = ConstatacionFisica.objects.get(id=id)
                    data['archivo_url'] = filtro.get_documento().url
                    template = get_template("formfirmaelectronica_v2.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'devolveractivo':
                try:
                    prestamo = PrestamoActivosOperaciones.objects.get(pk=encrypt_id(request.GET['id']))
                    data['id'] = prestamo.id
                    data['header_info'] = u'¿Está seguro(a) de solicitar la devolución el activo: {}?'.format(prestamo.activotecnologico)
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action == 'detalle_mi_activo':
                try:
                    data['activo'] = activo = ActivoFijo.objects.get(pk=int(encrypt(request.GET['id'])))
                    template = get_template("mis_activos/modal/detalle_mi_activo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addactivobodegavirtual':
                try:
                    activo = ActivoFijo.objects.get(pk=encrypt_id(request.GET['id']))
                    form = ActivoBodegaVirtualForm()
                    data['form'] = form
                    data['id'] = activo.id
                    template = get_template("ajaxformmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'mantenimientosactivos':
                try:
                    request.session['viewactivoth'] = ['administracion', action]
                    data['title'] = u'Mantenimientos de activos'
                    data['action'] = action

                    url_vars, search, = f'&action={action}', request.GET.get('s', '').strip()
                    filtro =  Q(status=True, mantenimiento__activotecno__activotecnologico__responsable=persona)

                    search = request.GET.get('s', '')
                    if search:
                        url_vars += f"&s={search}"
                        data['s'] = search
                        filtro = filtro & (Q(mantenimiento__activotecno__activotecnologico__codigogobierno=search) | Q(mantenimiento__activotecno__activotecnologico__codigointerno=search))

                    solicitudesm = SolicitudConfirmacionMantenimiento.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(solicitudesm, 15)
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
                    request.session['viewactivo'] = 1
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['solicitudesm'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, "mis_activos/solicitudmantenimiento.html", data)
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'solicitudestraspasos':
                try:
                    request.session['viewactivoth'] = ['administracion', action]
                    data['title'] = u'Solicitudes de traspaso'
                    data['action'] = action

                    url_vars, search, = f'&action={action}', request.GET.get('s', '').strip()
                    filtro =  Q(status=True) & ((Q(responsableasignacion=persona) | (Q(activo__responsable=persona))))

                    search = request.GET.get('s', '')
                    if search:
                        url_vars += f"&s={search}"
                        data['s'] = search
                        filtro = filtro & (Q(activo__codigogobierno=search) | Q(activo__codigointerno=search))

                    solicitudestraspasos = SolicitudActivos.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(solicitudestraspasos, 15)
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
                    request.session['viewactivo'] = 1
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['solicitudestraspasos'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, "mis_activos/solicitudestraspasos.html", data)
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'prestamos':
                try:
                    request.session['viewactivoth'] = ['administracion', action]
                    data['title'] = u'Préstamos'
                    data['action'] = action
                    data['fechaactual'] = datetime.now().date()
                    url_vars, search, = f'&action={action}', request.GET.get('s', '').strip()
                    filtro =  Q(status=True, personarecibe=persona)

                    search = request.GET.get('s', '')
                    if search:
                        url_vars += f"&s={search}"
                        data['s'] = search
                        filtro = filtro & (Q(activotecnologico__activotecnologico__codigogobierno=search) | Q(activotecnologico__activotecnologico__codigointerno=search))

                    prestamoactivosoperaciones = PrestamoActivosOperaciones.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(prestamoactivosoperaciones, 15)
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
                    request.session['viewactivo'] = 1
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['prestamoactivosoperaciones'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, "mis_activos/prestamosactivos.html", data)
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'traspasos':
                try:
                    request.session['viewactivoth'] = ['administracion', action]
                    data['title'] = u'Traspasos'
                    data['action'] = action
                    url_vars, search, = f'&action={action}', request.GET.get('s', '').strip()
                    filtro =  Q(status=True)

                    search = request.GET.get('s', '')
                    if search:
                        url_vars += f"&s={search}"
                        data['s'] = search
                        filtro = filtro & (Q(activotecnologico__activotecnologico__codigogobierno=search) | Q(activotecnologico__activotecnologico__codigointerno=search))

                    solicitudestraspasos = SolicitudTraspasoActivos.objects.filter(
                        Q(status=True) & Q(quiensolicita=1) & Q(usuarioentrega=persona)).order_by('-id')
                    solicitudestraspasosrecibidas = SolicitudTraspasoActivos.objects.filter(Q(status=True) & (
                            Q(usuariorecibe=persona) | (Q(custodioentrega=persona) & ~Q(solicitante=persona)) | Q(
                        custodiorecibe=persona))).exclude(estado=7, solicitante=persona).order_by('-id')


                    data['solicitudestraspasos'] = solicitudestraspasos
                    data['solicitudestraspasosrecibidas'] = solicitudestraspasosrecibidas
                    data['url_vars'] = url_vars
                    return render(request, "mis_activos/traspasos.html", data)
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'constatacionesmisactivos':
                try:
                    request.session['viewactivoth'] = ['administracion', action]
                    data['title'] = u'Constataciones'
                    data['action'] = action
                    url_vars, search, = f'&action={action}', request.GET.get('s', '').strip()
                    filtro = Q(status=True)

                    search = request.GET.get('s', '')
                    if search:
                        url_vars += f"&s={search}"
                        data['s'] = search
                        filtro = filtro & (Q(activotecnologico__activotecnologico__codigogobierno=search) | Q(
                            activotecnologico__activotecnologico__codigointerno=search))

                    cronogramas_cat = CronogramaPersonaConstatacionAT.objects.filter(status=True,
                                                                                             persona_id=persona.id,
                                                                                             estado__in=[3, 4])
                    constataciones_af = ConstatacionFisica.objects.filter(status=True, usuariobienes=persona,
                                                                                  estadoacta__in=[3, 4])

                    data['cronogramas_cat'] = cronogramas_cat
                    data['constataciones_af'] = constataciones_af
                    data['url_vars'] = url_vars
                    return render(request, "mis_activos/constataciones_mis_activos.html", data)
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'bodegavirtual':
                try:
                    request.session['viewactivoth'] = ['administracion', action]
                    data['title'] = u'Mis activos en bodega virtual'
                    data['action'] = action

                    url_vars, search, = f'&action={action}', request.GET.get('s', '').strip()
                    filtro = Q(status=True)

                    if 'actselect' in request.GET:
                        data['actselect'] = actselect = int(request.GET['actselect'])
                        url_vars += f"&actselect={actselect}"
                        if actselect == 1:
                            filtro = filtro & Q(activo__catalogo__equipoelectronico=True)
                        if actselect == 2:
                            filtro = filtro & Q(activo__catalogo__equipoelectronico=False)

                    misactivos = 'misact' in request.GET
                    codigo = request.GET.get('codigo', '0')
                    if misactivos:
                        filtro = filtro & Q(responsable=persona)
                        data['misact'] = misactivos
                        url_vars += f"&misact={misactivos}"


                    search = request.GET.get('s', '')
                    if search:
                        url_vars += f"&s={search}"
                        data['s'] = search
                        filtro = filtro & (Q(activo__codigogobierno=search) | Q(activo__codigointerno=search))

                    if codigo != '0':
                        data['codigo'] = codigo = int(codigo)
                        url_vars += f'&codigo={codigo}'
                        filtro = filtro & Q(activo__catalogo__grupo__id=codigo)

                    mibodega = BodegaVirtual.objects.filter(filtro).annotate(
                        row_number=Window(
                            expression=RowNumber(),
                            order_by=F('id').desc()
                        )
                    ).order_by('-id')
                    paging = MiPaginador(mibodega, 9)
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
                    request.session['viewactivo'] = 1
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['mibodega'] = page.object_list
                    data['url_vars'] = url_vars
                    data['grupocatalogo'] = GruposCategoria.objects.filter(status=True)
                    return render(request, "mis_activos/bodegavirtual.html", data)
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'mibodegavirtual':
                try:
                    request.session['viewactivoth'] = ['administracion', action]
                    data['title'] = u'Mis activos en bodega virtual'
                    data['action'] = action

                    url_vars, search, = f'&action={action}', request.GET.get('s', '').strip()
                    filtro = Q(status=True, responsable=persona)

                    search = request.GET.get('s', '')
                    if search:
                        url_vars += f"&s={search}"
                        data['s'] = search
                        filtro = filtro & (Q(activo__codigogobierno=search) | Q(activo__codigointerno=search))

                    mibodega = BodegaVirtual.objects.filter(filtro).annotate(
                        row_number=Window(
                            expression=RowNumber(),
                            order_by=F('id').desc()
                        )
                    ).order_by('-id')
                    paging = MiPaginador(mibodega, 9)
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
                    request.session['viewactivo'] = 1
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['mibodega'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, "mis_activos/mibodegavirtual.html", data)
                except Exception as ex:
                    messages.error(request, f'{ex}')

            return HttpResponseRedirect(request.path)
        else:
            try:
                request.session['viewactivoth'] = ['administracion', 'activos']
                data['title'] = u'Mis activos'
                data['fechaactual'] = datetime.now().date()
                filtro = Q(status=True, responsable=persona, statusactivo=1)
                url_vars = ''
                if 'actselect' in request.GET:
                    data['actselect'] = actselect = int(request.GET['actselect'])
                    url_vars += f"&actselect={actselect}"
                    if actselect == 1:
                        filtro = filtro & Q(catalogo__equipoelectronico=True)
                    if actselect == 2:
                        filtro = filtro & Q(catalogo__equipoelectronico=False)
                search = request.GET.get('s', '')
                if search:
                    url_vars += f"&s={search}"
                    data['s'] = search
                    filtro = filtro & (Q(codigogobierno=search) | Q(codigointerno=search))

                activos = ActivoFijo.objects.filter(filtro).order_by('ubicacion', 'descripcion')
                paging = MiPaginador(activos, 15)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session:
                        paginasesion = int(request.session['paginador'])
                    else:
                        p = paginasesion
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
                data['rangospaging'] = paging.rangos_paginado(p)
                data['search'] = search if search else ""
                data['url_vars'] = url_vars
                data['activos'] = page.object_list

                # data['solicitudestraspasosat'] = SolicitudActivos.objects.filter(Q(status=True) & (
                #         (Q(responsableasignacion=persona) & Q(estado=4)) | (
                #         Q(activo__responsable=persona) & Q(estado=1))))
                # data['solicitudestraspasosatatendidas'] = SolicitudActivos.objects.filter(Q(status=True) & (
                #         Q(activo__responsable=persona) & (
                #         Q(estado=2) | Q(estado=3) | Q(estado=4) | Q(estado=5) | Q(estado=7))))
                # data['solicitudestraspasosatatendidasfuturo'] = SolicitudActivos.objects.filter(Q(status=True) & (
                #         Q(responsableasignacion=persona) & (Q(estado=2) |
                #                                             Q(estado=3) |
                #                                             Q(estado=7))))
                # data['solicitudmantenimiento'] = SolicitudConfirmacionMantenimiento.objects.filter(status=True,
                #                                                                                    mantenimiento__activotecno__activotecnologico__responsable=persona)
                # data['prestamoactivosoperaciones'] = PrestamoActivosOperaciones.objects.filter(personarecibe=persona,
                #                                                                                status=True).order_by(
                #     '-id')
                # data['solicitudestraspasos'] = SolicitudTraspasoActivos.objects.filter(
                #     Q(status=True) & Q(quiensolicita=1) & Q(usuarioentrega=persona)).order_by('-id')
                # data['solicitudestraspasosrecibidas'] = SolicitudTraspasoActivos.objects.filter(Q(status=True) & (
                #             Q(usuariorecibe=persona) | (Q(custodioentrega=persona) & ~Q(solicitante=persona)) | Q(
                #         custodiorecibe=persona))).exclude(estado=7, solicitante=persona).order_by('-id')
                # data['idpersonamisactivos'] = persona.id
                # data['cronogramas_cat']=CronogramaPersonaConstatacionAT.objects.filter(status=True,persona_id=persona.id,estado__in=[3,4])
                # data['constataciones_af'] = ConstatacionFisica.objects.filter(status=True, usuariobienes=persona, estadoacta__in=[3, 4])
                data['notificaciones']=True if Notificacionactivoresponsable.objects.filter(status=True,responsable_id=persona.id, estado=1).exists() else False
                data['notilicencias']=True if HdIncidenteProductoDetalle.objects.filter(status=True,incidente__persona_id=persona.id, estado=1, producto__grupo_id=26).exists() else False
                return render(request, "mis_activos/mis_activos.html", data)
            except Exception as ex:
                pass
