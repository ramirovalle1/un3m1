# -*- coding: UTF-8 -*-
import base64
import os
import subprocess
import uuid
from django.test.testcases import TestCase
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template
from typing import Text
from zeep import Client
from decorators import last_access, secure_module
from sagest.forms import FacturaCanceladaForm, MoverFacturaForm
from sagest.models import Factura, NotaCredito
from settings import JR_JAVA_COMMAND, JR_RUN_SING_SIGNCLI, PASSSWORD_SIGNCLI, SERVER_URL_SIGNCLI, SERVER_USER_SIGNCLI, \
    SERVER_PASS_SIGNCLI, SITE_STORAGE, JR_RUN, DATABASES, REPORTE_PDF_NOTACREDITO_ID, URL_SERVICIO_ENVIO_SRI_PRUEBAS, \
    URL_SERVICIO_ENVIO_SRI_PRODUCCION, URL_SERVICIO_AUTORIZACION_SRI_PRUEBAS, URL_SERVICIO_AUTORIZACION_SRI_PRODUCCION
from settings import MODELO_IMPRESION_NUEVO
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import MiPaginador, log, generar_nombre
from sga.models import miinstitucion, Reporte, CUENTAS_CORREOS
from sga.tasks import send_html_mail, conectar_cuenta

unicode =str

def crear_representacion_xml_notacredito(id, proceso_siguiente=False):
    notacredito = NotaCredito.objects.get(pk=int(id))
    template = get_template("xml/notacredito.html")
    d = {'comprobante': notacredito,
                 'institucion': miinstitucion()}
    xml_content = template.render(d)
    notacredito.xml = xml_content
    notacredito.weburl = uuid.uuid4().hex
    notacredito.xmlgenerado = True
    notacredito.save()
    if proceso_siguiente:
        firmar_comprobante_notacredito(notacredito.id)


def firmar_comprobante_notacredito(id):
    notacredito = NotaCredito.objects.get(pk=int(id))
    token = miinstitucion().token
    if not token:
        return False

    import os
    runjrcommand = [JR_JAVA_COMMAND, '-jar',
                    os.path.join(JR_RUN_SING_SIGNCLI, 'SignCLI.jar'),
                    token.file.name,
                    PASSSWORD_SIGNCLI,
                    SERVER_URL_SIGNCLI + "/sign_notacredito/" + notacredito.weburl]
    if SERVER_USER_SIGNCLI and SERVER_PASS_SIGNCLI:
        runjrcommand.append(SERVER_USER_SIGNCLI)
        runjrcommand.append(SERVER_PASS_SIGNCLI)
    try:
        runjr = subprocess.call(runjrcommand)
    except:
        pass


def envio_comprobante_sri_notacredito(id, proceso_siguiente=False):
    notacredito = NotaCredito.objects.get(pk=int(id))
    if not notacredito.claveacceso:
        notacredito.claveacceso = notacredito.genera_clave_acceso_notacredito()
        notacredito.save()
    xml = notacredito.xmlfirmado
    test = TestCase
    # d = base64.b64encode(xml)
    if notacredito.tipoambiente == 1:
        WSDL = URL_SERVICIO_ENVIO_SRI_PRUEBAS  # 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantes?wsdl'
    else:
        WSDL = URL_SERVICIO_ENVIO_SRI_PRODUCCION  # 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantes?wsdl'
    client = Client(WSDL)
    # d = base64.b64encode(notacredito.xmlfirmado.encode('utf-8'))
    respuesta = client.service.validarComprobante(notacredito.xmlfirmado.encode('utf-8'))
    notacredito.falloenviodasri = False
    notacredito.mensajeenvio = ''
    notacredito.enviadasri = True

    yaenviado = False
    estado = "RECIBIDA"
    if respuesta.comprobantes:
        for m in respuesta.comprobantes.comprobante[0].mensajes.mensaje:
            if m.identificador == '43' or m.identificador == '45':
                yaenviado = True
                notacredito.falloenviodasri = False
                notacredito.mensajeenvio = ''
                notacredito.enviadasri = True
            else:
                if unicode(m.mensaje):
                    notacredito.mensajeenvio = unicode(m.mensaje)
                try:
                    if unicode(m.informacionAdicional):
                        notacredito.mensajeenvio += ' ' + unicode(m.informacionAdicional)
                except Exception as ex:
                    pass
    estado = "NO RECIBIDO"
    try:
        estado = unicode(respuesta.estado)
    except Exception as ex:
        pass
    if estado == "RECIBIDA" or yaenviado:
        notacredito.falloenviodasri = False
        notacredito.enviadasri = True
        notacredito.mensajeenvio = ''
        notacredito.save()
        if proceso_siguiente:
            autorizacion_comprobante_notacredito(notacredito.id, proceso_siguiente)
    else:
        notacredito.falloenviodasri = True
        notacredito.estado = 2
        notacredito.save()


def autorizacion_comprobante_notacredito(id, proceso_siguiente=False):
    notacredito = NotaCredito.objects.get(pk=int(id))
    if not notacredito.enviadasri:
        return False
    if notacredito.tipoambiente == 1:
        WSDL = URL_SERVICIO_AUTORIZACION_SRI_PRUEBAS  # 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantes?wsdl'
    else:
        WSDL = URL_SERVICIO_AUTORIZACION_SRI_PRODUCCION  # 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantes?wsdl'
    client = Client(WSDL)
    respuesta = client.service.autorizacionComprobante(notacredito.claveacceso)
    notacredito.autorizada = False
    notacredito.falloautorizacionsri = True
    if int(respuesta.numeroComprobantes) > 0:
        autorizacion = respuesta.autorizaciones.autorizacion[0]
        if autorizacion.estado == 'AUTORIZADO':
            notacredito.autorizada = True
            notacredito.estado = 3
            notacredito.falloautorizacionsri = False
            notacredito.autorizacion = unicode(autorizacion.numeroAutorizacion) if autorizacion.estado == 'AUTORIZADO' else ''
            notacredito.fechaautorizacion = autorizacion.fechaAutorizacion
            notacredito.save()
            if proceso_siguiente:
                envio_comprobante_cliente_notacredito(notacredito.id)
        if type(autorizacion.mensajes) != Text:
            if autorizacion.mensajes:
                notacredito.falloautorizacionsri = True
                notacredito.estado = 2
                for mensaje in autorizacion.mensajes.mensaje:
                    if unicode(mensaje.mensaje):
                        notacredito.mensajeautorizacion = unicode(mensaje.mensaje)
                    if unicode(mensaje.informacionAdicional):
                        notacredito.mensajeautorizacion += ' ' + unicode(mensaje.informacionAdicional)
                    notacredito.save()


def envio_comprobante_cliente_notacredito(id):
    notacredito = NotaCredito.objects.get(pk=int(id))
    direccion = os.path.join(SITE_STORAGE, 'media', 'comprobantes', 'notacredito')
    if not notacredito.xmlarchivo:
        xmlname = generar_nombre('NotaCredito', 'fichero.xml')
        filename_xml = os.path.join(direccion, xmlname)
        f = open(filename_xml, "wb")
        f.write(notacredito.xmlfirmado.encode('utf-8'))
        f.close()
        notacredito.xmlarchivo.name = 'comprobantes/notacredito/%s' % xmlname
    if not notacredito.pdfarchivo:
        try:
            pdfname = generar_nombre('NotaCredito', 'fichero')
            filename_pdf = os.path.join(direccion, pdfname)
            reporte = Reporte.objects.get(pk=REPORTE_PDF_NOTACREDITO_ID)
            tipo = 'pdf'
            runjrcommand = [JR_JAVA_COMMAND, '-jar',
                            os.path.join(JR_RUN, 'jasperstarter.jar'),
                            'pr', reporte.archivo.file.name,
                            '--jdbc-dir', JR_RUN,
                            '-f', tipo,
                            '-t', 'postgres',
                            '-H', DATABASES['sga_select']['HOST'],
                            '-n', DATABASES['sga_select']['NAME'],
                            '-u', DATABASES['sga_select']['USER'],
                            '-p', f"'{DATABASES['sga_select']['PASSWORD']}'",
                            '-o', filename_pdf]
            mensaje = ''
            for m in runjrcommand:
                mensaje += ' ' + m
            mensaje +=' -P id=' + str(id)
            runjr = subprocess.call(mensaje.encode("latin1"), shell=True)
            sp = os.path.split(reporte.archivo.file.name)
            notacredito.pdfarchivo.name = 'comprobantes/factura/%s.pdf' % pdfname
        except Exception as ex:
            # print(ex.__str__())
            pass
    if notacredito.pdfarchivo and notacredito.xmlarchivo:
        send_html_mail("Comprobante Electronico", "emails/comprobanteelectronico_notacredito.html", {'sistema': u'Sistema de Gestión Administrativa', 'notacredito': notacredito, 't': miinstitucion()}, [notacredito.email, ], [], cuenta=CUENTAS_CORREOS[16][1])
        notacredito.enviadacliente = True
        notacredito.estado = 2
        notacredito.save()



@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['sesion_caja'] = None
    if persona.puede_recibir_pagos():
        caja = persona.caja()
        sesion_caja = caja.sesion_caja()
        data['sesion_caja'] = sesion_caja
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'anular':
            try:
                factura = Factura.objects.get(pk=request.POST['id'])
                f = FacturaCanceladaForm(request.POST)
                if f.is_valid():
                    factura.cancelar(f.cleaned_data['motivo'], request)
                    factura.save(request)
                    log(u'Anulo factura: %s' % factura, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'mover':
            try:
                factura = Factura.objects.get(pk=request.POST['id'])
                f = MoverFacturaForm(request.POST)
                if f.is_valid():
                    pagos = factura.pagos.all()
                    for pa in pagos:
                        pa.sesion = f.cleaned_data['sesion']
                        pa.save()
                    log(u'Movio factura de pago en nota de credito: %s' % factura, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'detalle_nota':
            try:
                data['comprobante'] = credito = NotaCredito.objects.get(pk=int(request.POST['id']))
                data['institucion'] = miinstitucion()
                data['detalles'] = credito.detalle.all()
                template = get_template("rec_notacredito/detalle_notacredito.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'anularnotacredito':
            try:
                nota = NotaCredito.objects.get(id=request.POST['id'])
                nota.estado= 3
                nota.save()
                log(u'Anulo nota de credito: %s' % nota, request, "edit")

                return JsonResponse({"result": "ok"})

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al anular nota de credito." % ex.__str__()})



        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'generarxml':
                try:
                    notacredito = NotaCredito.objects.get(pk=request.GET['id'])
                    crear_representacion_xml_notacredito(notacredito.id)
                except Exception as ex:
                    pass

            if action == 'firmar':
                try:
                    notacredito = NotaCredito.objects.get(pk=request.GET['id'])
                    firmar_comprobante_notacredito(notacredito.id)
                except Exception as ex:
                    pass

            if action == 'enviosri':
                try:
                    notacredito = NotaCredito.objects.get(pk=request.GET['id'])
                    envio_comprobante_sri_notacredito(notacredito.id)
                except Exception as ex:
                    pass

            if action == 'enviarcliente':
                try:
                    notacredito = NotaCredito.objects.get(pk=request.GET['id'])
                    envio_comprobante_cliente_notacredito(notacredito.id)
                except Exception as ex:
                    pass

            if action == 'autorizar':
                try:
                    notacredito = NotaCredito.objects.get(pk=request.GET['id'])
                    autorizacion_comprobante_notacredito(notacredito.id)
                except Exception as ex:
                    pass

            elif action == 'rubros':
                try:
                    data['title'] = u'Listado de rubros de la factura'
                    data['factura'] = factura = Factura.objects.get(pk=request.GET['id'])
                    data['pagos'] = factura.pagos.all()
                    return render(request, "rec_facturas/rubros.html", data)
                except Exception as ex:
                    pass

            elif action == 'mover':
                try:
                    data['title'] = u'Mover factura a otra sesion de caja'
                    data['factura'] = factura = Factura.objects.get(pk=request.GET['id'])
                    form = MoverFacturaForm()
                    form.fechainicio(factura)
                    data['form'] = form
                    return render(request, "rec_facturas/mover.html", data)
                except Exception as ex:
                    pass

            elif action == 'anularnotacredito':
                try:
                    data['title'] = u'Anular Nota de Crédito'
                    data['nota'] = notacredito = NotaCredito.objects.get(pk=request.GET['id'])
                    return render(request, "rec_notacredito/anular_notacredito_confirm.html", data)

                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Listado de Notas de Crédito'
                search = None
                ids = None
                if 'id' in request.GET:
                    ids = int(request.GET['id'])
                    notas = NotaCredito.objects.filter(id=ids)
                elif 's' in request.GET:
                    search = request.GET['s']
                    notas = NotaCredito.objects.filter(Q(numero__icontains=search) |
                                                      Q(total__icontains=search) |
                                                      Q(cliente__nombres__icontains=search) |
                                                      Q(cliente__cedula__icontains=search) |
                                                      Q(cliente__ruc__icontains=search) |
                                                      Q(factura__numero__icontains=search)
                                                      # Q(caja__nombre__icontains=search) |
                                                      # Q(caja__puntoventa__contains=search)
                                                       ).distinct().order_by('-numero')
                #     order '-fecha', '-numero'
                else:
                    notas = NotaCredito.objects.all().order_by('-numero')
                paging = MiPaginador(notas, 25)
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
                paging.rangos_paginado(p)
                data['paging'] = paging
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['modelo_impresion_nuevo'] = MODELO_IMPRESION_NUEVO
                data['notas'] = page.object_list
                data['reporte_0'] = obtener_reporte('comprobante_entrega_nota')
                data['reporte_1'] = obtener_reporte('notacredito_reporte')
                persona = request.session['persona']
                data['puede_pagar'] = persona.puede_recibir_pagos()
                return render(request, "rec_notacredito/view.html", data)
            except Exception as ex:
                messages.error(request, "Error: {}".format(ex))
