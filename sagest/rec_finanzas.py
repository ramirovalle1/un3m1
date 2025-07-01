# -*- coding: UTF-8 -*-
import base64
import io
import json
import os
import random
import sys
import uuid
import math
import time as ET
from datetime import datetime, date
from decimal import Decimal
from itertools import chain

import xlsxwriter
from django.db.models import Sum
from django.test.testcases import TestCase
from typing import Text

# from werkzeug.urls import url_fix
from zeep import Client
import subprocess
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction,connections
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse, request
from django.shortcuts import render, redirect
from django.template.loader import get_template
from decorators import secure_module, last_access
from matricula.models import PeriodoMatricula
from sagest.commonviews import secuencia_recaudacion, anio_ejercicio
from sagest.forms import RubroForm, FormaPagoForm, LiquidarRubroForm, NombreRubroForm, RubroValorForm, PeriodoForm
from sagest.models import Rubro, Pago, TipoOtroRubro, SesionCaja, Factura, RubroNotaDebito, \
    IvaAplicado, PagoLiquidacion, PagoCheque, PagoTransferenciaDeposito, PagoTarjeta, PagoCuentaporCobrar, \
    PagoDineroElectronico, null_to_decimal, ReciboCaja, CapEventoPeriodoIpec, PagoReciboCaja, logRubros, \
    ComprobanteAlumno, HistorialGestionComprobanteAlumno, CuentaContable
from settings import FORMA_PAGO_EFECTIVO, FORMA_PAGO_TARJETA, FORMA_PAGO_CHEQUE, FORMA_PAGO_DEPOSITO, \
    FORMA_PAGO_TRANSFERENCIA, \
    DESCUENTOS_EN_FACTURAS, FORMA_PAGO_ELECTRONICO, FORMA_PAGO_CUENTA_PORCOBRAR, TIPO_AMBIENTE_FACTURACION, \
    JR_JAVA_COMMAND, JR_RUN_SING_SIGNCLI, PASSSWORD_SIGNCLI, SERVER_URL_SIGNCLI, SERVER_USER_SIGNCLI, \
    SERVER_PASS_SIGNCLI, SITE_STORAGE, REPORTE_PDF_FACTURA_ID, JR_RUN, DATABASES, URL_SERVICIO_ENVIO_SRI_PRUEBAS, \
    URL_SERVICIO_ENVIO_SRI_PRODUCCION, URL_SERVICIO_AUTORIZACION_SRI_PRUEBAS, URL_SERVICIO_AUTORIZACION_SRI_PRODUCCION, \
    DEBUG, SUBREPOTRS_FOLDER, RUBRO_ARANCEL, RUBRO_MATRICULA
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import MiPaginador, log, convertir_fecha, generar_nombre, variable_valor, salvaRubros, notificacion, puede_realizar_accion2
from sga.models import Persona, miinstitucion, Reporte, Matricula, Nivel, CUENTAS_CORREOS, Periodo
from secretaria.models import HistorialSolicitud
from sga.reportes import transform_jasperstarter
from sga.tasks import send_html_mail, conectar_cuenta
from moodle import moodle
from sga.templatetags.sga_extras import encrypt

unicode = str

def crear_representacion_xml_factura(id, proceso_siguiente=False):
    factura = Factura.objects.get(pk=int(id))
    template = get_template("xml/factura.html")
    d = ({'comprobante': factura,
                 'institucion': miinstitucion()})
    xml_content = template.render(d)
    factura.xml = xml_content
    factura.weburl = uuid.uuid4().hex
    factura.xmlgenerado = True
    factura.save()
    if proceso_siguiente:
        firmar_comprobante_factura(factura.id)


def firmar_comprobante_factura(id):
    factura = Factura.objects.get(pk=int(id))
    token = miinstitucion().token
    if not token:
        return False

    import os
    runjrcommand = [JR_JAVA_COMMAND, '-jar',
                    os.path.join(JR_RUN_SING_SIGNCLI, 'SignCLI.jar'),
                    token.file.name,
                    PASSSWORD_SIGNCLI,
                    SERVER_URL_SIGNCLI + "/sign_factura/" + factura.weburl]
    if SERVER_USER_SIGNCLI and SERVER_PASS_SIGNCLI:
        runjrcommand.append(SERVER_USER_SIGNCLI)
        runjrcommand.append(SERVER_PASS_SIGNCLI)
    try:
        runjr = subprocess.call(runjrcommand)
    except Exception as ex:
        print('Error ({}) al firmar en la linea: {}'.format(str(ex), sys.exc_info()[-1].tb_lineno))
        pass


def envio_comprobante_sri_factura(id, proceso_siguiente=False):
    try:
        factura = Factura.objects.get(pk=int(id))
        xml = factura.xmlfirmado
        test = TestCase
        # d = base64.b64encode(xml.encode('utf-8'))
        if factura.tipoambiente == 1:
            WSDL = URL_SERVICIO_ENVIO_SRI_PRUEBAS #'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantes?wsdl'
        else:
            WSDL = URL_SERVICIO_ENVIO_SRI_PRODUCCION #'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantes?wsdl'
        client = Client(WSDL)
        d = base64.b64encode(factura.xmlfirmado.encode('utf-8'))
        respuesta = client.service.validarComprobante(factura.xmlfirmado.encode('utf-8'))
        factura.falloenviodasri = False
        factura.mensajeenvio = ''
        factura.enviadasri = True
        estado = "RECIBIDA"
        yaenviado = False
        if respuesta.comprobantes:
            for m in respuesta.comprobantes.comprobante[0].mensajes.mensaje:
                if m.identificador == '43' or m.identificador == '45':
                    yaenviado = True
                    factura.falloenviodasri = False
                    factura.mensajeenvio = ''
                    factura.enviadasri = True
                else:
                    if unicode(m.mensaje):
                        factura.mensajeenvio = unicode(m.mensaje)
                    try:
                        if unicode(m.informacionAdicional):
                            factura.mensajeenvio += ' ' + unicode(m.informacionAdicional)
                    except Exception as ex:
                        pass
        try:
            estado = unicode(respuesta.estado)
        except Exception as ex:
            pass
        if estado == "RECIBIDA" or yaenviado:
            factura.falloenviodasri = False
            factura.enviadasri = True
            factura.mensajeenvio = ''
            factura.save()
            if proceso_siguiente:
                autorizacion_comprobante_factura(factura.id, proceso_siguiente=proceso_siguiente)
        else:
            factura.falloenviodasri = True
            factura.estado = 2
            factura.save()
    except Exception as ex:
        pass

def autorizacion_comprobante_factura(id, proceso_siguiente=False):
    factura = Factura.objects.get(pk=int(id))
    if not factura.enviadasri:
        return False
    if factura.tipoambiente == 1:
        WSDL = URL_SERVICIO_AUTORIZACION_SRI_PRUEBAS #'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantes?wsdl'
    else:
        WSDL = URL_SERVICIO_AUTORIZACION_SRI_PRODUCCION #'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantes?wsdl'
    client = Client(WSDL)
    respuesta = client.service.autorizacionComprobante(factura.claveacceso)
    factura.autorizada = False
    factura.falloautorizacionsri = True
    if int(respuesta.numeroComprobantes) > 0:
        autorizacion = respuesta.autorizaciones.autorizacion[0]
        if autorizacion.estado == 'AUTORIZADO':
            factura.autorizada = True
            factura.falloautorizacionsri = False
            factura.autorizacion = unicode(autorizacion.numeroAutorizacion) if autorizacion.estado == 'AUTORIZADO' else ''
            factura.fechaautorizacion = autorizacion.fechaAutorizacion
            factura.save()
            if proceso_siguiente:
                envio_comprobante_cliente_factura(factura.id)
        elif type(autorizacion.mensajes) != Text:
            factura.falloautorizacionsri = True
            factura.estado = 2
            for mensaje in autorizacion.mensajes.mensaje:
                if unicode(mensaje.mensaje):
                    factura.mensajeautorizacion = unicode(mensaje.mensaje)
                if unicode(mensaje.informacionAdicional):
                    factura.mensajeautorizacion += ' ' + unicode(mensaje.informacionAdicional)
    factura.save()


def envio_comprobante_cliente_factura(id):
    factura = Factura.objects.get(pk=int(id))
    direccion = os.path.join(SITE_STORAGE, 'media', 'comprobantes', 'factura')
    if not factura.xmlarchivo:
        xmlname = generar_nombre('Factura', 'fichero.xml')
        filename_xml = os.path.join(direccion, xmlname)
        f = open(filename_xml, "wb")
        f.write(factura.xmlfirmado.encode('utf-8'))
        f.close()
        factura.xmlarchivo.name = 'comprobantes/factura/%s' % xmlname
    if not factura.pdfarchivo:
        try:
            pdfname = generar_nombre('Factura', 'fichero')
            filename_pdf = os.path.join(direccion, pdfname)
            reporte = Reporte.objects.get(pk=REPORTE_PDF_FACTURA_ID)
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
            factura.pdfarchivo.name = 'comprobantes/factura/%s.pdf' % pdfname
        except Exception as ex:
            pass
    if factura.pdfarchivo and factura.xmlarchivo:
        listacorreos = []

        listacorreos.append(factura.email)
        listacorreos.append('tesoreria@unemi.edu.ec')

        send_html_mail("Comprobante Electrónico", "emails/comprobanteelectronico_factura.html", {'sistema': u'Sistema de Gestión Administrativa', 'factura': factura, 't': miinstitucion()}, listacorreos, [], cuenta=CUENTAS_CORREOS[1][1])
        factura.enviadacliente = True
        factura.estado = 2
        factura.save()


def pagaryfacturar(request, caja, extra=None):
    from bd.models import PeriodoCrontab
    from sagest.models import SecuencialRecaudaciones
    try:
        qsbasesecuencial = SecuencialRecaudaciones.objects.filter(puntoventa=caja.puntoventa).first()
        ultima_factura = Factura.objects.filter(status=True).order_by('numero').last()
        if qsbasesecuencial.factura != ultima_factura.numero:
            qsbasesecuencial.factura = ultima_factura.numero
            qsbasesecuencial.save(request)

        if 'aniofiscalpresupuesto' in request.session:
            anio = request.session['aniofiscalpresupuesto']
        else:
            anio = anio_ejercicio().anioejercicio
        sesion_caja = caja.sesion_caja()
        if extra:
            pagos = extra['pagos']
            idrubros = extra['rubros']
        else:
            pagos = json.loads(request.POST['pagos'])
            idrubros = json.loads(request.POST['rubros'])
        nofactura = False
        for rubro in Rubro.objects.filter(id__in=[int(x['rubro']) for x in idrubros]):
            rubro_seleccionado = rubro
            if rubro.tipo.nofactura:
                nofactura = True
            if not rubro.tipo.partida_saldo(anio):
                return {'result': 'bad', "mensaje": u"El Rubro %s no cuenta con un Saldo de Partida Asociado" % rubro.nombre}

        if extra:
            personacliente = Persona.objects.get(pk=int(extra['id']))
        else:
            personacliente = Persona.objects.get(pk=int(request.POST['id']))

        # SE GENERA FACTURA
        if not nofactura:
            secuencia = secuencia_recaudacion(request, sesion_caja.caja.puntoventa, 'factura')
            # secuencia.factura += 1
            # secuencia.save(request)
            if Factura.objects.filter(puntoventa=sesion_caja.caja.puntoventa, numero=secuencia).exists():
                return {'result': 'bad', "mensaje": u"Numero de factura ya existe."}
            clientefactura = personacliente.cliente_factura(request)
            if not extra:
                clientefactura.nombre = request.POST['nombre']
                clientefactura.identificacion = request.POST['identificacion']
                clientefactura.tipo = int(request.POST['tipoidentificacion'])
                clientefactura.direccion = request.POST['direccion']
                clientefactura.telefono = request.POST['tel']
                clientefactura.email = request.POST['email']
            clientefactura.save(request)

            direccion_factura = "N"
            if clientefactura.direccion:
                if len(clientefactura.direccion.strip()) > 0: direccion_factura = clientefactura.direccion

            factura = Factura(numerocompleto=caja.puntoventa.establecimiento.strip() + "-" + caja.puntoventa.puntoventa.strip() + "-" + str(secuencia).zfill(9),
                              numero=secuencia,
                              puntoventa=caja.puntoventa,
                              fecha=sesion_caja.fecha,
                              valida=True,
                              pagada=True,
                              electronica=True,
                              cliente=personacliente,
                              impresa=False,
                              sesioncaja=sesion_caja,
                              identificacion=clientefactura.identificacion,
                              tipo=clientefactura.tipo,
                              nombre=clientefactura.nombre,
                              # direccion=clientefactura.direccion if clientefactura.direccion,
                              direccion=direccion_factura,
                              telefono=clientefactura.telefono,
                              email=clientefactura.email,
                              tipoambiente=TIPO_AMBIENTE_FACTURACION)
            factura.save(request)
        else:
            # SE GENERA RECIBO DE CAJA
            secuencia = secuencia_recaudacion(request, sesion_caja.caja.puntoventa, 'recibocaja')
            # secuencia.recibocaja += 1
            # secuencia.save(request)
            if ReciboCaja.objects.filter(numero=secuencia).exists():
                return {'result': 'bad', "mensaje": u"Numero de recibo caja ya existe."}
            # clienterecibo = persona.cliente_factura(request)
            # if not extra:
            #     clienterecibo.nombre = request.POST['nombre']
            #     clienterecibo.identificacion = request.POST['identificacion']
            #     clienterecibo.tipo = int(request.POST['tipoidentificacion'])
            #     clienterecibo.direccion = request.POST['direccion']
            #     clienterecibo.telefono = request.POST['tel']
            #     clienterecibo.email = request.POST['email']
            #     clienterecibo.save(request)

            if personacliente.cedula:
                tipoidentificacion = 1
                identificacion = personacliente.cedula
            elif personacliente.ruc:
                tipoidentificacion = 2
                identificacion = personacliente.ruc
            else:
                tipoidentificacion = 3
                identificacion = personacliente.pasaporte

            recibocaja = ReciboCaja(numerocompleto=caja.puntoventa.establecimiento.strip() + "-" + caja.puntoventa.puntoventa.strip() + "-" + str(secuencia).zfill(9),
                                    numero=secuencia,
                                    sesioncaja=sesion_caja,
                                    persona=personacliente,
                                    partida=rubro_seleccionado.tipo.partida_saldo(anio).partidassaldo,
                                    concepto=rubro_seleccionado.tipo.nombre)
            recibocaja.save(request)

        valorpagorecibo = 0

        for pago in pagos:
            tp = None
            fechapago = sesion_caja.fecha
            valorpago = 0
            if int(pago['tipo']) == FORMA_PAGO_EFECTIVO:
                valorpago = Decimal(pago['valor'])
                fechapago = sesion_caja.fecha
            elif int(pago['tipo']) == FORMA_PAGO_CUENTA_PORCOBRAR:
                tp = PagoCuentaporCobrar(fecha=sesion_caja.fecha,
                                         valor=Decimal(pago['valor']))
                tp.save(request)
                fechapago = sesion_caja.fecha
                if not nofactura:
                    factura.pagada = False
                    factura.save(request)
                valorpago = Decimal(pago['valor'])
            elif int(pago['tipo']) == FORMA_PAGO_CHEQUE:
                tp = PagoCheque(numero=pago['numero'],
                                cuenta=pago['cuenta'],
                                banco_id=int(pago['banco']),
                                tipocheque_id=int(pago['tipocheque']),
                                fecha=sesion_caja.fecha,
                                fechacobro=convertir_fecha(pago['fechacobro']),
                                emite=pago['emite'],
                                valor=Decimal(pago['valor']),
                                protestado=False)
                tp.save(request)
                valorpago = Decimal(pago['valor'])
                fechapago = sesion_caja.fecha
            elif int(pago['tipo']) == FORMA_PAGO_ELECTRONICO:
                tp = PagoDineroElectronico(referencia=pago['referenciaelec'],
                                           fecha=sesion_caja.fecha,
                                           valor=Decimal(pago['valor']))
                tp.save(request)
                fechapago = sesion_caja.fecha
                valorpago = Decimal(pago['valor'])
            elif int(pago['tipo']) == FORMA_PAGO_DEPOSITO:
                tp = PagoTransferenciaDeposito(referencia=pago['referenciadep'],
                                               fecha=convertir_fecha(pago['fechadep']),
                                               cuentabanco_id=int(pago['cuentadep']),
                                               valor=Decimal(pago['valor']),
                                               deposito=True,
                                               recaudacionventanilla=True if extra else False)
                tp.save(request)
                fechapago = convertir_fecha(pago['fechadep'])
                valorpago = Decimal(pago['valor'])
            elif int(pago['tipo']) == FORMA_PAGO_TRANSFERENCIA:
                tp = PagoTransferenciaDeposito(referencia=pago['referenciatrans'],
                                               fecha=convertir_fecha(pago['fechatrans']),
                                               cuentabanco_id=int(pago['cuentatrans']),
                                               tipotransferencia_id=int(pago['tipotran']),
                                               valor=Decimal(pago['valor']),
                                               deposito=False)
                tp.save(request)
                fechapago = convertir_fecha(pago['fechatrans'])
                valorpago = Decimal(pago['valor'])
            elif int(pago['tipo']) == FORMA_PAGO_TARJETA:
                tp = PagoTarjeta(banco_id=int(pago['bancotar']),
                                 tipo_id=int(pago['tipotar']),
                                 procedencia_id=int(pago['procedencia']),
                                 poseedor=pago['poseedor'],
                                 valor=Decimal(pago['valor']),
                                 procesadorpago_id=int(pago['procesador']),
                                 referencia=pago['referenciatarj'],
                                 fecha=sesion_caja.fecha)
                tp.save(request)
                fechapago = sesion_caja.fecha
                valorpago = Decimal(pago['valor'])
            # rubro_pagado = []
            valorpagorecibo += valorpago
            for rubro in Rubro.objects.filter(id__in=[int(x['rubro']) for x in idrubros], cancelado=False).order_by('fechavence'):
                # rubro_pagado.append(rubro.id)
                # qs_anterior = list(Rubro.objects.filter(pk=rubro.id).values())
                iva = 0
                if rubro.saldo >= valorpago:
                    valorapagar = Decimal(valorpago)
                else:
                    valorapagar = Decimal(rubro.saldo)
                if null_to_decimal(valorpago, 2) > 0:
                    if rubro.iva.porcientoiva == 0:
                        subtotaliva = 0
                        subtotal0 = valorapagar
                        iva = 0
                    else:
                        subtotaliva = Decimal(valorapagar / (rubro.iva.porcientoiva + 1)).quantize(Decimal('.01'))
                        iva = Decimal(valorapagar - subtotaliva).quantize(Decimal('.01'))
                        subtotal0 = 0
                    pagorubro = Pago(fecha=fechapago,
                                     subtotal0=subtotal0,
                                     subtotaliva=subtotaliva,
                                     iva=iva,
                                     valordescuento=0,
                                     valortotal=valorapagar,
                                     rubro=rubro,
                                     efectivo=True if not tp else False,
                                     sesion=sesion_caja)
                    pagorubro.save(request)
                    if pagorubro.rubro.iva.porcientoiva:
                        if not nofactura:
                            factura.ivaaplicado = pagorubro.rubro.iva

                    if extra:
                        if 'fecha_verificacion' in extra:
                            fecha_verificacion = extra['fecha_verificacion']
                            eSolicitud = rubro.solicitud
                            if eSolicitud:
                                eSolicitud.verificar_fecha(fecha_verificacion)
                    rubro.save(request)
                    rubro.bloqueo_matricula_actualizar()
                    # GUARDA AUDITORIA RUBRO
                    # qs_nuevo = list(Rubro.objects.filter(pk=rubro.id).values())
                    # salvaRubros(request, rubro, 'pagaryfacturar', qs_nuevo=qs_nuevo, qs_anterior=qs_anterior)
                    # GUARDA AUDITORIA RUBRO

                    matricula = rubro.matricula

                    if matricula:
                        matricula.actualiza_matricula()
                        coordinacion = matricula.inscripcion.carrera.mi_coordinacion2()
                        if coordinacion == 7:
                            matricula.bloqueomatricula = False
                            if matricula.bloqueo_matricula_pago():
                                matricula.bloqueomatricula = True
                                log(u'%s: %s' % (u'Bloquear matricula ventanilla', matricula), request, "edit")
                            matricula.save(request)
                        elif coordinacion in [9, 1, 2, 3, 4, 5]:
                            if PeriodoCrontab.objects.values("id").filter(status=True, periodo=matricula.nivel.periodo, bloqueo_state_enrollment=True).exists():
                                matricula.bloqueomatricula = False
                                if matricula.estado_matricula == 1:
                                    matricula.bloqueomatricula = True
                                matricula.save(request)
                                log(u'%s: %s' % (u'Se actualiza estado de bloqueo de matrícula', matricula), request, "edit")
                                usermoodle = matricula.inscripcion.persona.usuario.username
                                if coordinacion == 9:
                                    cursor = connections['db_moodle_virtual'].cursor()
                                else:
                                    cursor = connections['moodle_db'].cursor()
                                if cursor:
                                    if usermoodle:
                                        # Consulta en mooc_user
                                        sql = """SELECT id FROM mooc_user WHERE username='%s'""" % (usermoodle)
                                        cursor.execute(sql)
                                        registro = cursor.fetchall()
                                        if registro:
                                            sql = """UPDATE mooc_user SET suspended=%s WHERE username='%s'""" % (1 if matricula.bloqueomatricula else 0, usermoodle)
                                            cursor.execute(sql)

                    # BANCO_ACTUALIZA_MATRICULA = variable_valor('BANCO_ACTUALIZA_MATRICULA')
                    # if BANCO_ACTUALIZA_MATRICULA:
                    #     if matricula:
                    #         matricula.actualiza_matricula()
                    #         if matricula.inscripcion.coordinacion_id == 9:
                    #             tipourl = 2
                    #         else:
                    #             tipourl = 1
                    #         for materiaasignada in matricula.mis_materias_sin_retiro():
                    #             materiaasignada.materia.crear_actualizar_un_estudiante_curso(moodle, tipourl, matricula)
                    #         if matricula.bloqueo_matricula_pago():
                    #             matricula.bloqueomatricula = True
                    #             matricula.save()
                    #             log(u'%s: %s' % (u'Bloquear matricula Subida Archivo', matricula), request, "edit")

                    if not nofactura:
                        factura.pagos.add(pagorubro)

                    if tp:
                        tp.pagos.add(pagorubro)
                    valorpago -= valorapagar
            if not nofactura:
                factura.save(request)
                factura.claveacceso = factura.genera_clave_acceso_factura()
                factura.save(request)
                crear_representacion_xml_factura(factura.id)
            else:
                recibocaja.valor = valorpagorecibo
                recibocaja.save(request)

        if nofactura:
            numero = recibocaja.numerocompleto
            idfactura = recibocaja.id
            tipo = 2
        else:
            numero = factura.numerocompleto
            idfactura = factura.id
            tipo = 1
        log(u'Se facturo para: %s - %s con número factura' % (personacliente.nombre_completo_inverso(), numero), request, "add")
        return {'result': 'ok', 'numerofactura': numero, 'id': idfactura, "tipo": tipo}

    except Exception as ex:
        raise NameError(f"Error def pagaryfacturar: {ex} - linea: {sys.exc_info()[-1].tb_lineno}")

def pagaryemitirrecibocaja(request, caja):
    if 'aniofiscalpresupuesto' in request.session:
        anio = request.session['aniofiscalpresupuesto']
    else:
        anio = anio_ejercicio().anioejercicio

    sesion_caja = caja.sesion_caja()

    # Formas de pago
    pagos = json.loads(request.POST['pagos'])
    # Rubros
    idrubros = json.loads(request.POST['rubros'])
    # Motivo
    motivorecibo = request.POST['motivorecibo'].strip().upper()

    # Verificación de que los rubros tengan partida asociada
    for rubro in Rubro.objects.filter(id__in=[int(x['rubro']) for x in idrubros]):
        if not rubro.tipo.partida_saldo(anio):
            return {'result': 'bad', "mensaje": u"El Rubro %s no cuenta con un Saldo de Partida Asociado" % rubro.nombre}

    personacliente = Persona.objects.get(pk=int(request.POST['id']))

    # Crea o actualiza un registro de Cliente Factura
    clientefactura = personacliente.cliente_factura(request)
    clientefactura.nombre = request.POST['nombre']
    clientefactura.identificacion = request.POST['identificacion']
    clientefactura.tipo = int(request.POST['tipoidentificacion'])
    clientefactura.direccion = request.POST['direccion']
    clientefactura.telefono = request.POST['tel']
    clientefactura.email = request.POST['email']
    clientefactura.save(request)

    # Secuencia del recibo de caja
    secuencia = secuencia_recaudacion(request, sesion_caja.caja.puntoventa, 'recibocaja')
    # secuencia.recibocaja += 1
    # secuencia.save(request)
    if PagoReciboCaja.objects.filter(puntoventa=sesion_caja.caja.puntoventa, numero=secuencia).exists():
        return {'result': 'bad', "mensaje": u"El Número de Recibo de Caja ya existe."}

    # Crear el recibo de caja
    recibocaja = PagoReciboCaja(puntoventa=caja.puntoventa,
                                sesioncaja=sesion_caja,
                                numero=secuencia,
                                numerocompleto=caja.puntoventa.establecimiento.strip() + "-" + caja.puntoventa.puntoventa.strip() + "-" + str(secuencia).zfill(9),
                                fecha=sesion_caja.fecha,
                                persona=personacliente,
                                motivo=motivorecibo,
                                enviadocliente=False,
                                valor=0#Este valor se actualizará al final despues de procesar cada rubro
                                )
    recibocaja.save(request)

    valorpagorecibo = 0

    # Recorrer las formas de pago
    for formapago in pagos:
        fpago = None
        fechapago = sesion_caja.fecha
        valorpago = 0

        # Guardo la o las formas de pago(excepto cuando es pago en efectivo)
        if int(formapago['tipo']) == FORMA_PAGO_EFECTIVO:
            valorpago = Decimal(formapago['valor'])
            fechapago = sesion_caja.fecha
        elif int(formapago['tipo']) == FORMA_PAGO_CUENTA_PORCOBRAR:
            fpago = PagoCuentaporCobrar(fecha=sesion_caja.fecha,
                                     valor=Decimal(formapago['valor']))
            fpago.save(request)
            fechapago = sesion_caja.fecha
            valorpago = Decimal(formapago['valor'])
        elif int(formapago['tipo']) == FORMA_PAGO_CHEQUE:
            fpago = PagoCheque(numero=formapago['numero'],
                            cuenta=formapago['cuenta'],
                            banco_id=int(formapago['banco']),
                            tipocheque_id=int(formapago['tipocheque']),
                            fecha=sesion_caja.fecha,
                            fechacobro=convertir_fecha(formapago['fechacobro']),
                            emite=formapago['emite'],
                            valor=Decimal(formapago['valor']),
                            protestado=False)
            fpago.save(request)
            valorpago = Decimal(formapago['valor'])
            fechapago = sesion_caja.fecha
        elif int(formapago['tipo']) == FORMA_PAGO_ELECTRONICO:
            fpago = PagoDineroElectronico(referencia=formapago['referenciaelec'],
                                       fecha=sesion_caja.fecha,
                                       valor=Decimal(formapago['valor']))
            fpago.save(request)
            fechapago = sesion_caja.fecha
            valorpago = Decimal(formapago['valor'])
        elif int(formapago['tipo']) == FORMA_PAGO_DEPOSITO:
            fpago = PagoTransferenciaDeposito(referencia=formapago['referenciadep'].strip().upper(),
                                           fecha=convertir_fecha(formapago['fechadep']),
                                           cuentabanco_id=int(formapago['cuentadep']),
                                           valor=Decimal(formapago['valor']),
                                           deposito=True,
                                           recaudacionventanilla=False)
            fpago.save(request)
            fechapago = convertir_fecha(formapago['fechadep'])
            valorpago = Decimal(formapago['valor'])
        elif int(formapago['tipo']) == FORMA_PAGO_TRANSFERENCIA:
            fpago = PagoTransferenciaDeposito(referencia=formapago['referenciatrans'],
                                           fecha=convertir_fecha(formapago['fechatrans']),
                                           cuentabanco_id=int(formapago['cuentatrans']),
                                           tipotransferencia_id=int(formapago['tipotran']),
                                           valor=Decimal(formapago['valor']),
                                           deposito=False)
            fpago.save(request)
            fechapago = convertir_fecha(formapago['fechatrans'])
            valorpago = Decimal(formapago['valor'])
        elif int(formapago['tipo']) == FORMA_PAGO_TARJETA:
            fpago = PagoTarjeta(banco_id=int(formapago['bancotar']),
                             tipo_id=int(formapago['tipotar']),
                             procedencia_id=int(formapago['procedencia']),
                             poseedor=formapago['poseedor'],
                             valor=Decimal(formapago['valor']),
                             procesadorpago_id=int(formapago['procesador']),
                             referencia=formapago['referenciatarj'],
                             fecha=sesion_caja.fecha)
            fpago.save(request)
            fechapago = sesion_caja.fecha
            valorpago = Decimal(formapago['valor'])

        # Acumulo el valor total del recibo de pago
        valorpagorecibo += valorpago

        # Recorro los rubros
        for rubro in Rubro.objects.filter(id__in=[int(x['rubro']) for x in idrubros], cancelado=False).order_by('fechavence'):
            iva = 0
            if rubro.saldo >= valorpago:
                valorapagar = Decimal(valorpago)
            else:
                valorapagar = Decimal(rubro.saldo)

            if valorpago > 0:
                if rubro.iva.porcientoiva == 0:
                    subtotaliva = 0
                    subtotal0 = valorapagar
                    iva = 0
                else:
                    subtotaliva = Decimal(valorapagar / (rubro.iva.porcientoiva + 1)).quantize(Decimal('.01'))
                    iva = Decimal(valorapagar - subtotaliva).quantize(Decimal('.01'))
                    subtotal0 = 0
                # Grabo el pago
                pagorubro = Pago(fecha=fechapago,
                                 subtotal0=subtotal0,
                                 subtotaliva=subtotaliva,
                                 iva=iva,
                                 valordescuento=0,
                                 valortotal=valorapagar,
                                 rubro=rubro,
                                 efectivo=False,
                                 sesion=sesion_caja)
                pagorubro.save(request)

                rubro.save(request)

                matricula = rubro.matricula
                if matricula:
                    coordinacion = matricula.inscripcion.carrera.mi_coordinacion2()
                    if coordinacion == 7:
                        if matricula.bloqueo_matricula_pago():
                            matricula.bloqueomatricula = True
                            log(u'%s: %s' % (u'Bloquear matricula ventanilla', matricula), request, "edit")
                        else:
                            matricula.bloqueomatricula = False
                        matricula.save(request)
                if matricula:
                    matricula.actualiza_matricula()

                # Agrego el pago al recibo de caja
                recibocaja.pagos.add(pagorubro)

                # Si existe creada la forma de pago agrego el pago a la forma de pago
                if fpago:
                    fpago.pagos.add(pagorubro)

                valorpago -= valorapagar

    # Actualizo el total del recibo de caja
    recibocaja.valor = valorpagorecibo
    recibocaja.save(request)

    numero = recibocaja.numerocompleto
    idfactura = recibocaja.id
    tipo = 3

    log(u'Se registró recibo de caja para: %s - %s con número ' % (personacliente.nombre_completo_inverso(), numero), request, "add")
    return {'result': 'ok', 'numerofactura': numero, 'id': idfactura, "tipo": tipo}

def pagaryemitirrecibocajamatriculas1718diciembre(request, caja, extra=None):
    if 'aniofiscalpresupuesto' in request.session:
        anio = request.session['aniofiscalpresupuesto']
    else:
        anio = anio_ejercicio().anioejercicio

    sesion_caja = caja.sesion_caja()

    pagos = extra['pagos']
    idrubros = extra['rubros']

    # Motivo
    motivorecibo = "PAGOS EN BANCO PACÍFICO AÑO 2020"

    # Verificación de que los rubros tengan partida asociada
    for rubro in Rubro.objects.filter(id__in=[int(x['rubro']) for x in idrubros]):
        if not rubro.tipo.partida_saldo(anio):
            return {'result': 'bad', "mensaje": u"El Rubro %s no cuenta con un Saldo de Partida Asociado" % rubro.nombre}

    # personacliente = Persona.objects.get(pk=int(request.POST['id']))
    personacliente = Persona.objects.get(pk=int(extra['id']))

    # Crea o actualiza un registro de Cliente Factura
    clientefactura = personacliente.cliente_factura(request)
    # clientefactura.nombre = request.POST['nombre']
    # clientefactura.identificacion = request.POST['identificacion']
    # clientefactura.tipo = int(request.POST['tipoidentificacion'])
    # clientefactura.direccion = request.POST['direccion']
    # clientefactura.telefono = request.POST['tel']
    # clientefactura.email = request.POST['email']
    # clientefactura.save(request)

    # Secuencia del recibo de caja
    secuencia = secuencia_recaudacion(request, sesion_caja.caja.puntoventa, 'recibocaja')
    # secuencia.recibocaja += 1
    # secuencia.save(request)
    if PagoReciboCaja.objects.filter(puntoventa=sesion_caja.caja.puntoventa, numero=secuencia).exists():
        return {'result': 'bad', "mensaje": u"El Número de Recibo de Caja ya existe."}

    # Crear el recibo de caja
    recibocaja = PagoReciboCaja(puntoventa=caja.puntoventa,
                                sesioncaja=sesion_caja,
                                numero=secuencia,
                                numerocompleto=caja.puntoventa.establecimiento.strip() + "-" + caja.puntoventa.puntoventa.strip() + "-" + str(secuencia).zfill(9),
                                fecha=sesion_caja.fecha,
                                persona=personacliente,
                                motivo=motivorecibo,
                                enviadocliente=False,
                                valor=0#Este valor se actualizará al final despues de procesar cada rubro
                                )
    recibocaja.save(request)

    valorpagorecibo = 0

    # Recorrer las formas de pago
    for formapago in pagos:
        fpago = None
        fechapago = sesion_caja.fecha
        valorpago = 0

        # Guardo la o las formas de pago(excepto cuando es pago en efectivo)
        if int(formapago['tipo']) == FORMA_PAGO_EFECTIVO:
            valorpago = Decimal(formapago['valor'])
            fechapago = sesion_caja.fecha
        elif int(formapago['tipo']) == FORMA_PAGO_CUENTA_PORCOBRAR:
            fpago = PagoCuentaporCobrar(fecha=sesion_caja.fecha,
                                     valor=Decimal(formapago['valor']))
            fpago.save(request)
            fechapago = sesion_caja.fecha
            valorpago = Decimal(formapago['valor'])
        elif int(formapago['tipo']) == FORMA_PAGO_CHEQUE:
            fpago = PagoCheque(numero=formapago['numero'],
                            cuenta=formapago['cuenta'],
                            banco_id=int(formapago['banco']),
                            tipocheque_id=int(formapago['tipocheque']),
                            fecha=sesion_caja.fecha,
                            fechacobro=convertir_fecha(formapago['fechacobro']),
                            emite=formapago['emite'],
                            valor=Decimal(formapago['valor']),
                            protestado=False)
            fpago.save(request)
            valorpago = Decimal(formapago['valor'])
            fechapago = sesion_caja.fecha
        elif int(formapago['tipo']) == FORMA_PAGO_ELECTRONICO:
            fpago = PagoDineroElectronico(referencia=formapago['referenciaelec'],
                                       fecha=sesion_caja.fecha,
                                       valor=Decimal(formapago['valor']))
            fpago.save(request)
            fechapago = sesion_caja.fecha
            valorpago = Decimal(formapago['valor'])
        elif int(formapago['tipo']) == FORMA_PAGO_DEPOSITO:
            fpago = PagoTransferenciaDeposito(referencia=formapago['referenciadep'].strip().upper(),
                                           fecha=convertir_fecha(formapago['fechadep']),
                                           cuentabanco_id=int(formapago['cuentadep']),
                                           valor=Decimal(formapago['valor']),
                                           deposito=True,
                                           recaudacionventanilla=True)
            fpago.save(request)
            fechapago = convertir_fecha(formapago['fechadep'])
            valorpago = Decimal(formapago['valor'])
        elif int(formapago['tipo']) == FORMA_PAGO_TRANSFERENCIA:
            fpago = PagoTransferenciaDeposito(referencia=formapago['referenciatrans'],
                                           fecha=convertir_fecha(formapago['fechatrans']),
                                           cuentabanco_id=int(formapago['cuentatrans']),
                                           tipotransferencia_id=int(formapago['tipotran']),
                                           valor=Decimal(formapago['valor']),
                                           deposito=False)
            fpago.save(request)
            fechapago = convertir_fecha(formapago['fechatrans'])
            valorpago = Decimal(formapago['valor'])
        elif int(formapago['tipo']) == FORMA_PAGO_TARJETA:
            fpago = PagoTarjeta(banco_id=int(formapago['bancotar']),
                             tipo_id=int(formapago['tipotar']),
                             procedencia_id=int(formapago['procedencia']),
                             poseedor=formapago['poseedor'],
                             valor=Decimal(formapago['valor']),
                             procesadorpago_id=int(formapago['procesador']),
                             referencia=formapago['referenciatarj'],
                             fecha=sesion_caja.fecha)
            fpago.save(request)
            fechapago = sesion_caja.fecha
            valorpago = Decimal(formapago['valor'])

        # Acumulo el valor total del recibo de pago
        valorpagorecibo += valorpago

        # Recorro los rubros
        for rubro in Rubro.objects.filter(id__in=[int(x['rubro']) for x in idrubros], cancelado=False).order_by('fechavence'):
            iva = 0
            if rubro.saldo >= valorpago:
                valorapagar = Decimal(valorpago)
            else:
                valorapagar = Decimal(rubro.saldo)

            if valorpago > 0:
                if rubro.iva.porcientoiva == 0:
                    subtotaliva = 0
                    subtotal0 = valorapagar
                    iva = 0
                else:
                    subtotaliva = Decimal(valorapagar / (rubro.iva.porcientoiva + 1)).quantize(Decimal('.01'))
                    iva = Decimal(valorapagar - subtotaliva).quantize(Decimal('.01'))
                    subtotal0 = 0
                # Grabo el pago
                pagorubro = Pago(fecha=fechapago,
                                 subtotal0=subtotal0,
                                 subtotaliva=subtotaliva,
                                 iva=iva,
                                 valordescuento=0,
                                 valortotal=valorapagar,
                                 rubro=rubro,
                                 efectivo=False,
                                 sesion=sesion_caja)
                pagorubro.save(request)

                rubro.save(request)

                matricula = rubro.matricula
                if matricula:
                    coordinacion = matricula.inscripcion.carrera.mi_coordinacion2()
                    if coordinacion == 7:
                        if matricula.bloqueo_matricula_pago():
                            matricula.bloqueomatricula = True
                            log(u'%s: %s' % (u'Bloquear matricula ventanilla', matricula), request, "edit")
                        else:
                            matricula.bloqueomatricula = False
                        matricula.save(request)
                if matricula:
                    matricula.actualiza_matricula()

                # Agrego el pago al recibo de caja
                recibocaja.pagos.add(pagorubro)

                # Si existe creada la forma de pago agrego el pago a la forma de pago
                if fpago:
                    fpago.pagos.add(pagorubro)

                valorpago -= valorapagar

    # Actualizo el total del recibo de caja
    recibocaja.valor = valorpagorecibo
    recibocaja.save(request)

    # # Enviar el recibo de caja por e-mail al cliente
    # envio_recibocaja_cliente(recibocaja.id)

    numero = recibocaja.numerocompleto
    idfactura = recibocaja.id
    tipo = 3

    log(u'Se registró recibo de caja para: %s - %s con número ' % (personacliente.nombre_completo_inverso(), numero), request, "add")
    return {'result': 'ok', 'numerofactura': numero, 'id': idfactura, "tipo": tipo}


def generar_recibo_caja(id):
    envio_recibocaja_cliente(id)
    return {'result': 'ok'}

def envio_recibocaja_cliente(id):
    recibocaja = PagoReciboCaja.objects.get(pk=int(id))
    direccion = os.path.join(SITE_STORAGE, 'media', 'comprobantes', 'recibocaja')

    # Si no existe el PDF del recibo de caja se lo crea
    if not recibocaja.pdfarchivo:
        try:
            pdfname = generar_nombre('ReciboCaja', 'fichero')
            filename_pdf = os.path.join(direccion, pdfname)
            reporte = Reporte.objects.get(pk=461)
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

            runjrcommand.append('-P id='+str(id))

            mens = ''
            for m in runjrcommand:
                mens += ' ' + m

            if DEBUG:
                runjr = subprocess.run(mens, shell=True, check=True)
                # print('runjr:', runjr.returncode)
            else:
                runjr = subprocess.call(mens.encode("latin1"), shell=True)

            sp = os.path.split(reporte.archivo.file.name)

            recibocaja.pdfarchivo.name = 'comprobantes/recibocaja/%s.pdf' % pdfname
        except Exception as ex:
            msg = ex.__str__()
            pass

    recibocaja.save()

    if recibocaja.pdfarchivo:
        listacorreos = []

        listacorreos.append(recibocaja.direccion_email_cliente())
        # listacorreos.append('isaltosm@unemi.edu.ec')
        # listacorreos.append('ivan_saltos_medina@hotmail.com')
        listacorreos.append('tesoreria@unemi.edu.ec')

        send_html_mail("Comprobante Electrónico", "emails/comprobante_recibocaja.html",
                       {'sistema': u'Sistema de Gestión Administrativa', 'recibocaja': recibocaja, 't': miinstitucion()},
                       listacorreos, [], cuenta=CUENTAS_CORREOS[1][1])
        # Temporizador para evitar que se bloquee el servicion de gmail
        ET.sleep(5)
        recibocaja.enviadocliente = True
        recibocaja.save()

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if 'aniofiscalpresupuesto' in request.session:
        anio = request.session['aniofiscalpresupuesto']
    else:
        anio = anio_ejercicio().anioejercicio
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'pagaryfacturar':
            try:
                persona = request.session['persona']
                cajero = persona.caja()
                return JsonResponse(pagaryfacturar(request, cajero))
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u'Error al guardar los datos'})

        if action == 'delrubro':
            try:
                rubro = Rubro.objects.get(pk=request.POST['id'])

                if rubro.tiene_pagos() or rubro.bloqueado:
                    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar este rubro."})

                if rubro.fechavence < datetime.now().date() and persona.id != 2570:
                    return JsonResponse({"result": "bad", "mensaje": u"La fecha del rubro debe ser mayor o igual a la fecha actual para poder eliminarlo."})

                # qs_anterior = list(Rubro.objects.filter(pk=request.POST['id']).values())

                rubro.status = False
                rubro.save(request)
                #GUARDA AUDITORIA RUBRO
                # qs_nuevo = list(Rubro.objects.filter(pk=rubro.id).values())
                # salvaRubros(request, rubro, action,  qs_nuevo=qs_nuevo, qs_anterior=qs_anterior)
                #GUARDA AUDITORIA RUBRO
                if rubro.epunemi and rubro.idrubroepunemi>0:
                    cursor = connections['epunemi'].cursor()
                    sql = "UPDATE sagest_rubro SET status=false WHERE sagest_rubro.status=true and sagest_rubro.id="+str(rubro.idrubroepunemi)
                    cursor.execute(sql)
                    cursor.close()

                log(u'Elimino rubro: %s - %s' % (rubro, rubro.persona), request, "del")
                return JsonResponse({'result': 'ok'})
            except:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad'})

        if action == 'addotro':
            try:
                tipootro = TipoOtroRubro.objects.get(pk=request.POST['tid'])
                matricula = Matricula.objects.get(pk=request.POST['matricula']) if int(request.POST['matricula']) > 0 else None
                fecharubro = request.POST['fe'].strip()

                fechar = datetime.strptime(fecharubro[6:10] + "-" + fecharubro[3:5] + "-" + fecharubro[0:2], '%Y-%m-%d').date()
                if fechar < datetime.now().date() and persona.id != 2570:
                    return JsonResponse({"result": "bad", "mensaje": u"La fecha del rubro debe ser mayor o igual a la fecha actual."})

                # Si hay matricula
                if matricula:
                    # Si esa matricula posee un rubro bloqueado no se podrán agregar rubros a la matrícula
                    if Rubro.objects.values("id").filter(status=True, matricula=matricula, bloqueado=True).exists():
                        return JsonResponse({'result': 'bad', "mensaje": u'No se puede agregar rubro a la matrícula debido a que existe un compromiso de pago/solicitud de refinanciamiento registrada'})

                iva = IvaAplicado.objects.get(pk=request.POST['iva'])
                cliente = Persona.objects.get(pk=request.POST['id'])
                nombrerubro = request.POST['nombre']
                ncuota = int(request.POST['ncuota'])
                a = request.POST['fe']
                dia = int(a[0:2])
                mes = int(a[3:5])
                anio = int(a[6:10])
                # fechavence = date(int(a[6:10]), int(a[3:5]), int(a[0:2]))
                bandera = 0
                ultimo_dia = int(a[0:2])
                for n in range(ncuota):
                    if bandera == 0:
                        fechavence = date(anio, mes, dia)
                        bandera = 1
                    else:
                        salio = True
                        d = 0
                        while salio:
                            try:
                                fechavence = date(anio, mes, dia - d)
                                salio = False
                            except:
                                salio = True
                            d += 1
                    mes += 1
                    if mes == 13:
                        mes = 1
                        anio += 1

                    epunemi = False

                    if tipootro.tiporubro == 1 or tipootro.tiporubro == 2 or tipootro.tiporubro == 7 or request.POST['isE'] == 'true':
                         epunemi = True

                    rubro = Rubro(fecha=datetime.now().date(),
                                  valor=null_to_decimal(float(request.POST['valor']), 2),
                                  valortotal=null_to_decimal(float(request.POST['valor']), 2),
                                  saldo=null_to_decimal(float(request.POST['valor']), 2),
                                  persona=cliente,
                                  matricula=matricula,
                                  nombre=nombrerubro,
                                  tipo=tipootro,
                                  cancelado=False,
                                  observacion='',
                                  iva=iva,
                                  epunemi=epunemi,
                                  fechavence=fechavence)

                    rubro.save(request)

                    if rubro.epunemi:
                        # -------CREAR PERSONA EPUNEMI-------
                        cursor = connections['epunemi'].cursor()
                        sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (cliente.cedula, cliente.cedula, cliente.cedula)
                        cursor.execute(sql)
                        idalumno = cursor.fetchone()

                        if idalumno is None:
                            sql = """ INSERT INTO sga_persona (status, nombres, apellido1, apellido2, cedula, ruc, pasaporte,
                                        nacimiento, tipopersona, sector, direccion,  direccion2,
                                        num_direccion, telefono, telefono_conv, email, contribuyenteespecial,
                                        anioresidencia, nacionalidad, ciudad, referencia, emailinst, identificacioninstitucion,
                                        regitrocertificacion, libretamilitar, servidorcarrera, concursomeritos, telefonoextension,
                                        tipocelular, periodosabatico, real, lgtbi, datosactualizados, confirmarextensiontelefonia,
                                        acumuladecimo, acumulafondoreserva, representantelegal, inscripcioncurso, unemi,
                                        idunemi)
                                                VALUES(TRUE, '%s', '%s', '%s', '%s', '%s', '%s', '/%s/', %s, '%s', '%s', '%s', '%s', '%s', '%s', '%s', 
                                                FALSE, 0, '', '', '', '', '', '', '', FALSE, FALSE, '', 0, FALSE, TRUE, FALSE, 0, FALSE, TRUE, FALSE, FALSE, 
                                                FALSE, FALSE, 0); """ % (
                                cliente.nombres,
                                cliente.apellido1,
                                cliente.apellido2,
                                cliente.cedula,
                                cliente.ruc if cliente.ruc else '',
                                cliente.pasaporte if cliente.pasaporte else '',
                                cliente.nacimiento,
                                cliente.tipopersona if cliente.tipopersona else 1,
                                cliente.sector if cliente.sector else '',
                                cliente.direccion if cliente.direccion else '',
                                cliente.direccion2 if cliente.direccion2 else '',
                                cliente.num_direccion if cliente.num_direccion else '',
                                cliente.telefono if cliente.telefono else '',
                                cliente.telefono_conv if cliente.telefono_conv else '',
                                cliente.email if cliente.email else '')
                            cursor.execute(sql)

                            if cliente.sexo:
                                sql = """SELECT sexo.id FROM sga_sexo AS sexo WHERE sexo.id='%s'  AND sexo.status=TRUE;  """ % (
                                    cliente.sexo.id)
                                cursor.execute(sql)
                                sexo = cursor.fetchone()

                                if sexo is not None:
                                    sql = """UPDATE sga_persona SET sexo_id='%s' WHERE cedula='%s'; """ % (
                                    sexo[0], cliente.cedula)
                                    cursor.execute(sql)

                            if cliente.pais:
                                sql = """SELECT pai.id FROM sga_pais AS pai WHERE pai.id='%s'  AND pai.status=TRUE;  """ % (
                                    cliente.pais.id)
                                cursor.execute(sql)
                                pais = cursor.fetchone()

                                if pais is not None:
                                    sql = """UPDATE sga_persona SET pais_id='%s' WHERE cedula='%s'; """ % (
                                    pais[0], cliente.cedula)
                                    cursor.execute(sql)

                            if cliente.parroquia:
                                sql = """SELECT pa.id FROM sga_parroquia AS pa WHERE pa.id='%s'  AND pa.status=TRUE;  """ % (
                                    cliente.parroquia.id)
                                cursor.execute(sql)
                                parroquia = cursor.fetchone()

                                if parroquia is not None:
                                    sql = """UPDATE sga_persona SET parroquia_id='%s' WHERE cedula='%s'; """ % (
                                    parroquia[0], cliente.cedula)
                                    cursor.execute(sql)

                            if cliente.canton:
                                sql = """SELECT ca.id FROM sga_canton AS ca WHERE ca.id='%s'  AND ca.status=TRUE;  """ % (
                                    cliente.canton.id)
                                cursor.execute(sql)
                                canton = cursor.fetchone()

                                if canton is not None:
                                    sql = """UPDATE sga_persona SET canton_id='%s' WHERE cedula='%s'; """ % (
                                    canton[0], cliente.cedula)
                                    cursor.execute(sql)

                            if cliente.provincia:
                                sql = """SELECT pro.id FROM sga_provincia AS pro WHERE pro.id='%s'  AND pro.status=TRUE;  """ % (
                                    cliente.provincia.id)
                                cursor.execute(sql)
                                provincia = cursor.fetchone()

                                if provincia is not None:
                                    sql = """UPDATE sga_persona SET provincia_id='%s' WHERE cedula='%s'; """ % (
                                    provincia[0], cliente.cedula)
                                    cursor.execute(sql)

                            # ID DE PERSONA EN EPUNEMI
                            sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (
                            cliente.cedula, cliente.cedula,
                            cliente.cedula)
                            cursor.execute(sql)
                            idalumno = cursor.fetchone()
                            alumnoepu = idalumno[0]
                        else:
                            alumnoepu = idalumno[0]

                        # Consulto el tipo otro rubro en epunemi
                        sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (rubro.tipo.id)
                        cursor.execute(sql)
                        registro = cursor.fetchone()

                        # Si existe
                        if registro is not None:
                            tipootrorubro = registro[0]
                        else:
                            # Debo crear ese tipo de rubro
                            # Consulto centro de costo
                            sql = """SELECT id FROM sagest_centrocosto WHERE status=True AND unemi=True AND tipo=%s;""" % (rubro.tipo.tiporubro)
                            cursor.execute(sql)
                            centrocosto = cursor.fetchone()
                            idcentrocosto = centrocosto[0]

                            # Consulto la cuenta contable
                            cuentacontable = CuentaContable.objects.get(partida=rubro.tipo.partida, status=True)

                            # Creo el tipo de rubro en epunemi
                            sql = """ Insert Into sagest_tipootrorubro (status, nombre, partida_id, valor, interface, activo, ivaaplicado_id, nofactura, exportabanco, cuentacontable_id, centrocosto_id, tiporubro, idtipootrorubrounemi, unemi, es_especie, es_convalidacionconocimiento)
                                                VALUES(TRUE, '%s', %s, %s, FALSE, TRUE, %s, FALSE, TRUE, %s, %s, 1, %s, TRUE, FALSE, FALSE); """ % (rubro.tipo.nombre, cuentacontable.partida.id,
                                                                                                                                                    rubro.tipo.valor, rubro.tipo.ivaaplicado.id,
                                                                                                                                                    cuentacontable.id, idcentrocosto, rubro.tipo.id)
                            cursor.execute(sql)

                            print(".:: Tipo de Rubro creado en EPUNEMI ::.")

                            # Obtengo el id recién creado del tipo de rubro
                            sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (rubro.tipo.id)
                            cursor.execute(sql)
                            registro = cursor.fetchone()
                            tipootrorubro = registro[0]

                        # pregunto si no existe rubro con ese id de unemi
                        sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE; """ % (rubro.id)
                        cursor.execute(sql)
                        registrorubro = cursor.fetchone()

                        if registrorubro is None:
                            # Creo nuevo rubro en epunemi
                            sql = """ INSERT INTO sagest_rubro (status, persona_id, nombre, cuota, tipocuota, fecha, fechavence,
                                        valor, saldo, iva_id, valoriva, totalunemi, valortotal, cancelado, observacion, 
                                        idrubrounemi, tipo_id, fecha_creacion, usuario_creacion_id, tienenotacredito, valornotacredito, 
                                        valordescuento, anulado, compromisopago, refinanciado, bloqueado, bloqueadopornovedad, 
                                        titularcambiado, coactiva) 
                                      VALUES (TRUE, %s, '%s', %s, %s, '/%s/', '/%s/', %s, %s, %s, %s, %s, %s, %s, '%s', %s, %s, NOW(), 1, FALSE, 0, 0, FALSE, %s, %s, %s, FALSE, FALSE, %s); """ \
                                  % (alumnoepu, rubro.nombre, rubro.cuota, rubro.tipocuota, rubro.fecha, rubro.fechavence, rubro.saldo, rubro.saldo,
                                     rubro.iva_id, rubro.valoriva, rubro.valor,
                                     rubro.valortotal, rubro.cancelado, rubro.observacion, rubro.id, tipootrorubro,
                                     rubro.compromisopago if rubro.compromisopago else 0,
                                     rubro.refinanciado, rubro.bloqueado, rubro.coactiva)
                            cursor.execute(sql)

                            sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND anulado=FALSE; """ % (rubro.id)
                            cursor.execute(sql)
                            registro = cursor.fetchone()
                            rubroepunemi = registro[0]

                            rubro.idrubroepunemi = rubroepunemi
                            rubro.save()

                            print(".:: Rubro creado en EPUNEMI ::.")
                        else:
                            sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND cancelado=FALSE; """ % (rubro.id)
                            cursor.execute(sql)
                            rubronoc = cursor.fetchone()

                            if rubronoc is not None:
                                sql = """SELECT id FROM sagest_pago WHERE rubro_id=%s; """ % (registrorubro[0])
                                cursor.execute(sql)
                                tienerubropagos = cursor.fetchone()

                                if tienerubropagos is not None:
                                    pass
                                else:
                                    sql = """UPDATE sagest_rubro SET nombre = '%s', fecha = '/%s/', fechavence = '/%s/',
                                           valor = %s, saldo = %s, iva_id = %s, valoriva = %s, totalunemi = %s,
                                           valortotal = %s, observacion = '%s', tipo_id = %s
                                           WHERE id=%s; """ % (
                                    rubro.nombre, rubro.fecha, rubro.fechavence, rubro.saldo, rubro.saldo, rubro.iva_id,
                                    rubro.valoriva, rubro.valor, rubro.valortotal, rubro.observacion, tipootrorubro,
                                    registrorubro[0])
                                    cursor.execute(sql)
                                rubro.idrubroepunemi = registrorubro[0]
                                rubro.save()
                    # GUARDA AUDITORIA
                    # qs_nuevo = list(Rubro.objects.filter(pk=rubro.id).values())
                    # salvaRubros(request, rubro, action,
                    #             qs_nuevo=qs_nuevo)
                    # GUARDA AUDITORIA

                    log(u'Adiciono rubro: %s a %s' % (rubro,cliente), request, "add")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)

                return JsonResponse({'result': 'bad', "mensaje": u'Error al guardar los datos'})

        if action == 'editrubro':
            try:
                est = puede_realizar_accion2(request, 'posgrado.puede_editar_rubro_fechas')
                rubro = Rubro.objects.get(pk=request.POST['id'])

                if rubro.bloqueado:
                    return JsonResponse({'result': 'bad', "mensaje": u'No se puede editar la fecha debido a que el rubro está bloqueado'})

                # qs_anterior = list(Rubro.objects.filter(pk=request.POST['id']).values())
                f = RubroForm(request.POST)
                if f.is_valid():
                    if not est:
                        if f.cleaned_data['fechavence'] < datetime.now().date() and persona.id != 2570:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha del rubro debe ser mayor o igual a la fecha actual."})

                    rubro.fechavence = f.cleaned_data['fechavence']
                    rubro.save(request)
                    #GUARDA AUDITORIA RUBRO
                    # qs_nuevo = list(Rubro.objects.filter(pk=rubro.id).values())
                    # salvaRubros(request, rubro, action,  qs_nuevo=qs_nuevo, qs_anterior=qs_anterior)
                    #GUARDA AUDITORIA RUBRO

                    if rubro.matricula:
                        rubro.matricula.actualiza_matricula()

                    if rubro.epunemi and rubro.idrubroepunemi > 0:
                        cursor = connections['epunemi'].cursor()
                        sql = "UPDATE sagest_rubro SET fechavence = '%s' WHERE sagest_rubro.status= true and sagest_rubro.id= %s" %(rubro.fechavence,rubro.idrubroepunemi)
                        cursor.execute(sql)
                        cursor.close()
                    log(u'Modifico fecha vencimiento de rubro: %s - %s' % (rubro, rubro.persona), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editrubrovalor':
            try:
                rubro = Rubro.objects.get(pk=request.POST['id'])

                if rubro.bloqueado:
                    return JsonResponse({'result': 'bad', "mensaje": u'No se puede editar el valor debido a que el rubro está bloqueado'})

                if rubro.fechavence < datetime.now().date() and persona.id != 2570:
                    return JsonResponse({"result": "bad", "mensaje": u"La fecha del rubro debe ser mayor o igual a la fecha actual para poder editar el valor."})

                # qs_anterior = list(Rubro.objects.filter(pk=request.POST['id']).values())
                f = RubroValorForm(request.POST)
                if f.is_valid():
                    rubro_valor = rubro.valor
                    rubro.valor = f.cleaned_data['valor']
                    rubro.save(request)
                    #GUARDA AUDITORIA RUBRO
                    # qs_nuevo = list(Rubro.objects.filter(pk=rubro.id).values())
                    # salvaRubros(request, rubro, action,  qs_nuevo=qs_nuevo, qs_anterior=qs_anterior)
                    #GUARDA AUDITORIA RUBRO
                    if rubro.epunemi and rubro.idrubroepunemi > 0:
                        cursor = connections['epunemi'].cursor()
                        sql = "UPDATE sagest_rubro SET valor = '%s', valortotal = '%s', saldo = '%s' , totalunemi = '%s' WHERE sagest_rubro.status= true and sagest_rubro.id= %s" %(rubro.valor, rubro.valor , rubro.valor,rubro.valor,rubro.idrubroepunemi)
                        cursor.execute(sql)
                        cursor.close()

                    #envio de correo a tics
                    listacorreos = ['direccion.tic@unemi.edu.ec']
                    send_html_mail("Modificación de rubro en el módulo Finanzas", "emails/notificacion_edit_rubro_tics.html",
                                   {'rubro': rubro, 'tiposistema_': 2, "responsable": persona, "rubrovalor": rubro_valor},
                                   listacorreos, [], cuenta=CUENTAS_CORREOS[1][1])
                    # Temporizador para evitar que se bloquee el servicion de gmail
                    ET.sleep(2)

                    log(u'Modifico valor del rubro: %s - %s, valor anterior: %s, valor actual: %s ' % (rubro, rubro.persona, rubro_valor, rubro.valor), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editnombrerubro':
            try:
                rubro = Rubro.objects.get(pk=request.POST['id'])

                if rubro.bloqueado:
                    return JsonResponse({'result': 'bad', "mensaje": u'No se puede editar el nombre debido a que el rubro está bloqueado'})

                # qs_anterior = list(Rubro.objects.filter(pk=request.POST['id']).values())
                f = NombreRubroForm(request.POST)
                if f.is_valid():
                    rubro.nombre = f.cleaned_data['nombre']
                    rubro.save(request)
                    #GUARDA AUDITORIA RUBRO
                    # qs_nuevo = list(Rubro.objects.filter(pk=rubro.id).values())
                    # salvaRubros(request, rubro, action,  qs_nuevo=qs_nuevo, qs_anterior=qs_anterior)
                    #GUARDA AUDITORIA RUBRO
                    if rubro.epunemi and rubro.idrubroepunemi > 0:
                        cursor = connections['epunemi'].cursor()
                        sql = "UPDATE sagest_rubro SET nombre = '%s' WHERE sagest_rubro.status= true and sagest_rubro.id= %s" %(rubro.nombre,rubro.idrubroepunemi)
                        cursor.execute(sql)
                        cursor.close()
                    log(u'Modifico nombre de rubro: %s - %s' % (rubro, rubro.persona), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'act_obser':
            try:
                rubro = Rubro.objects.get(pk=request.POST['id'])
                # qs_anterior = list(Rubro.objects.filter(pk=request.POST['id']).values())
                rubro.observacion = request.POST['valor']
                rubro.save(request)
                #GUARDA AUDITORIA RUBRO
                # qs_nuevo = list(Rubro.objects.filter(pk=rubro.id).values())
                # salvaRubros(request, rubro, action,  qs_nuevo=qs_nuevo, qs_anterior=qs_anterior)
                #GUARDA AUDITORIA RUBRO
                log(u'Modifico observacion de rubro: %s' % rubro, request, "edit")
                return JsonResponse({"result": "ok"})
            except:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'liquidar':
            try:
                rubro = Rubro.objects.get(pk=request.POST['id'])

                if rubro.bloqueado:
                    return JsonResponse({'result': 'bad', "mensaje": u'No se puede liquidar debido a que el rubro está bloqueado'})

                f = LiquidarRubroForm(request.POST)
                if f.is_valid():
                    subtotal0 = 0
                    subtotaliva = 0
                    iva = 0
                    if rubro.iva.porcientoiva > 0:
                        subtotaliva = Decimal(rubro.saldo / (rubro.iva.porcientoiva + 1)).quantize(Decimal('.01'))
                        iva = Decimal(rubro.saldo - subtotaliva).quantize(Decimal('.01'))
                    else:
                        subtotal0 = rubro.saldo
                    pago = Pago(rubro=rubro,
                                fecha=datetime.now().date(),
                                subtotal0=subtotal0,
                                subtotaliva=subtotaliva,
                                iva=iva,
                                valordescuento=0,
                                valortotal=rubro.saldo,
                                efectivo=False)
                    pago.save(request)
                    liquidacion = PagoLiquidacion(fecha=datetime.now().date(),
                                                  motivo=f.cleaned_data['motivo'],
                                                  valor=rubro.saldo)
                    liquidacion.save(request)
                    liquidacion.pagos.add(pago)
                    rubro.save(request)
                    log(u"Se liquido rubro: %s - %s" % (rubro, rubro.persona), request, "add")
                    data = {"result": "ok", "rid": rubro.id, "fecha": rubro.fechavence.strftime("%d-%m-%Y"), "vencido": rubro.vencido()}
                else:
                     raise NameError('Error')
                return JsonResponse(data)
            except:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al liquidar."})

        if action == 'liquidarconvenioposgrado':
            try:
                rubro = Rubro.objects.get(pk=request.POST['id'])

                if rubro.bloqueado:
                    return JsonResponse({'result': 'bad', "mensaje": u'No se puede liquidar debido a que el rubro está bloqueado'})

                f = LiquidarRubroForm(request.POST)
                if f.is_valid():
                    subtotal0 = 0
                    subtotaliva = 0
                    iva = 0
                    if rubro.iva.porcientoiva > 0:
                        subtotaliva = Decimal(rubro.saldo / (rubro.iva.porcientoiva + 1)).quantize(Decimal('.01'))
                        iva = Decimal(rubro.saldo - subtotaliva).quantize(Decimal('.01'))
                    else:
                        subtotal0 = rubro.saldo
                    pago = Pago(rubro=rubro,
                                fecha=datetime.now().date(),
                                subtotal0=subtotal0,
                                subtotaliva=subtotaliva,
                                iva=iva,
                                valordescuento=0,
                                valortotal=rubro.saldo,
                                epunemipago = True,
                                efectivo=False)
                    pago.save(request)

                    cursor = connections['epunemi'].cursor()
                    sql = """  INSERT INTO sagest_pago(id, status, rubro_id, fecha, subtotal0, subtotaliva, iva, valordescuento, valortotal,migradounemi,efectivo,secuencia)
                                        VALUES (default, True, %s, '%s', %s, %s, %s, %s, %s, TRUE,FALSE, 1);
                            """ % (pago.rubro.idrubroepunemi, pago.fecha, pago.subtotal0, pago.subtotaliva, pago.iva, pago.valordescuento, pago.valortotal)
                    cursor.execute(sql)

                    sql = """SELECT id FROM sagest_pago WHERE rubro_id =%s AND status=TRUE; """ % (pago.rubro.idrubroepunemi)
                    cursor.execute(sql)
                    registro = cursor.fetchone()

                    if registro is not None:
                        pagoepunemi = registro[0]
                        sql = """UPDATE sagest_rubro SET cancelado = TRUE, saldo = 0 WHERE id=%s; """ % (pago.rubro.idrubroepunemi)
                        cursor.execute(sql)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": "Error al liquidar en epunemi."})

                    pago.idpagoepunemi = pagoepunemi
                    pago.save()

                    liquidacion = PagoLiquidacion(fecha=datetime.now().date(),
                                                  motivo=f.cleaned_data['motivo'],
                                                  valor=rubro.saldo)
                    liquidacion.save(request)
                    liquidacion.pagos.add(pago)
                    rubro.save(request)
                    log(u"Se liquido rubro: %s - %s" % (rubro, rubro.persona), request, "add")
                    data = {"result": "ok", "rid": rubro.id, "fecha": rubro.fechavence.strftime("%d-%m-%Y"), "vencido": rubro.vencido()}
                else:
                     raise NameError('Error')
                return JsonResponse(data)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al liquidar."})

        if action == 'pagar':
            try:
                caja = persona.mi_lugar_recaudacion()
                # En caso de que la acción 'pagar' sea llamada desde otro módulo por defecto
                # se asigna la variable emitefactura = S caso contrario el valor  que haya sido asignado en la pantalla Pago de Rubros
                emitefactura = request.POST['emitefactura'] if 'emitefactura' in request.POST else 'S'

                if emitefactura == 'S':
                    return JsonResponse(pagaryfacturar(request, caja))
                else:
                    return JsonResponse(pagaryemitirrecibocaja(request, caja))

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"Error al procesar pago: {ex}"})

        if action == 'generarrecibo':
            try:
                return JsonResponse(generar_recibo_caja(50))
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al procesar pago."})

        if action == 'segotros':
            try:
                data['cliente'] = persona = Persona.objects.get(pk=request.POST['id'])
                data['tiposotros'] = TipoOtroRubro.objects.filter(interface=True, activo=True)
                data['tiposiva'] = IvaAplicado.objects.filter(activo=True)
                data['hoy'] = datetime.now().date()
                data['matricula'] = Matricula.objects.filter(cerrada=False, inscripcion__persona=persona)
                template = get_template("rec_finanzas/segotros.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        if action == 'matriculas':
            try:
                data['cliente'] = persona = Persona.objects.get(pk=request.POST['id'])
                data['matricula'] = Matricula.objects.filter(cerrada=False, inscripcion__persona=persona)
                data['idr'] = request.POST['idr']
                data['hoy'] = datetime.now().date()
                template = get_template("rec_finanzas/matricula.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        if action == 'diferirarancel':
            try:
                rid = int(request.POST['id'])
                arancel = Rubro.objects.get(pk=rid)

                pago = arancel.tiene_pagos()
                matriculaid=arancel.matricula.id
                eMatricula = Matricula.objects.get(pk=matriculaid)
                ePeriodoMatricula = PeriodoMatricula.objects.get(status=True, activo=True,periodo=eMatricula.nivel.periodo)
                nombrearancel = arancel.nombre
                valorarancel = Decimal(arancel.valortotal).quantize(Decimal('.01'))
                if valorarancel < ePeriodoMatricula.monto_rubro_cuotas:
                    raise NameError(f"Periodo acádemico no permite diferir arancel menor a ${ePeriodoMatricula.monto_rubro_cuotas}")
                num_cuotas = ePeriodoMatricula.num_cuotas_rubro
                try:
                    valor_cuota_mensual = (valorarancel / num_cuotas).quantize(Decimal('.01'))
                except ZeroDivisionError:
                    valor_cuota_mensual = 0
                if valor_cuota_mensual == 0:
                    raise NameError(u"No se puede procesar el registro.")
                eRubroMatricula = Rubro.objects.filter(matricula=eMatricula, tipo_id=RUBRO_MATRICULA)[0]
                eRubroMatricula.relacionados = None
                eRubroMatricula.save(request)
                lista = []
                c = 0
                fechas_cuotas = ePeriodoMatricula.fecha_cuotas_rubro().values('fecha').distinct()
                if not fechas_cuotas:
                    raise NameError(u"No se puede procesar el registro, no se han configurado las fechas de cuotas.")
                for r in fechas_cuotas:
                    c += 1
                    lista.append([c, valor_cuota_mensual, r['fecha']])
                for item in lista:
                    rubro = Rubro(tipo_id=RUBRO_ARANCEL,
                                  persona=eMatricula.inscripcion.persona,
                                  relacionados=eRubroMatricula,
                                  matricula=eMatricula,
                                  nombre=nombrearancel,
                                  cuota=item[0],
                                  fecha=datetime.now().date(),
                                  fechavence=item[2],
                                  valor=item[1],
                                  iva_id=1,
                                  valoriva=0,
                                  valortotal=item[1],
                                  saldo=item[1],
                                  cancelado=False)
                    rubro.save(request)
                arancel.delete()
                eMatricula.aranceldiferido = 1
                eMatricula.save(request)
                log(u'Rubro diferido: %s' % (arancel), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al diferir los rubros."})

        if action == 'addmatricula':
            try:
                mid = int(request.POST['mid'])
                rid = int(request.POST['rid'])
                rubro  = Rubro.objects.get(pk=rid)
                matricula  = Matricula.objects.get(pk=mid)

                # Si esa matricula posee un rubro bloqueado no se podrán agregar rubros a la matrícula
                if Rubro.objects.values("id").filter(status=True, matricula=matricula, bloqueado=True).exists():
                    return JsonResponse({'result': 'bad', "mensaje": u'No se puede asignar rubro a la matrícula debido a que existe un compromiso de pago/solicitud de refinanciamiento registrada'})

                rubro.matricula = matricula
                rubro.save(request)
                matricula.actualiza_matricula()
                log(u'Vinculo matricula: %s - %s' % (rubro, matricula), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        if action == 'delmatricula':
            try:
                rid = int(request.POST['id'])
                rubro  = Rubro.objects.get(pk=rid)

                if rubro.bloqueado:
                    return JsonResponse({'result': 'bad', "mensaje": u'No se puede quitar de matrícula debido a que el rubro está bloqueado'})

                matricula  = rubro.matricula
                rubro.matricula = None
                rubro.save(request)
                matricula.actualiza_matricula()
                log(u'Desvinculo matricula: %s - %s' % (rubro, matricula), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        if action == 'eventoperiodoipec':
            try:
                data['cliente'] = persona = Persona.objects.get(pk=request.POST['id'])
                data['eventos'] = CapEventoPeriodoIpec.objects.filter(status=True, visualizar=True)
                data['idr'] = request.POST['idr']
                template = get_template("rec_finanzas/eventosperiodoipec.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        if action == 'addeventoperiodoipec':
            try:
                eid = int(request.POST['eid'])
                rid = int(request.POST['rid'])
                rubro  = Rubro.objects.get(pk=rid)
                evento  = CapEventoPeriodoIpec.objects.get(pk=eid)
                rubro.capeventoperiodoipec = evento
                rubro.save(request)
                log(u"Asigno capacitacion evento periodo Ipec en rubro rubro: %s - %s - %s" % (rubro, rubro.persona, evento), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        if action == 'verificarelacionado':
            try:
                cont = 0
                rubros = Rubro.objects.filter(cancelado=False, epunemi=False,
                                             relacionados__isnull=False, status=True)
                for rubro in rubros:
                    relacionado = Rubro.objects.get(pk=rubro.relacionados_id)
                    if relacionado:
                        if relacionado.cancelado:
                            rubro.relacionados_id=None
                            rubro.save()
                            cont += 1
                    else:
                        rubro.relacionados_id = None
                        rubro.save()
                        cont += 1
                return JsonResponse({"result": "ok","tot":cont})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        if action == 'reverso':
            try:
                datos = request.POST['ids']
                datos = datos.split(',')
                for id in datos:
                    rubro = Rubro.objects.get(pk=id)

                    if rubro.epunemi :
                        if rubro.idrubroepunemi > 0:
                            cursor = connections['epunemi'].cursor()

                            if rubro.tiene_pagos():
                                sql = "UPDATE sagest_rubro SET cancelado=True, saldo=0 , valor= %s , valortotal= %s  WHERE sagest_rubro.status=true and sagest_rubro.id=%s" %(rubro.total_pagado(),rubro.total_pagado(),rubro.idrubroepunemi)

                            else:
                                sql = "UPDATE sagest_rubro SET status=false WHERE sagest_rubro.status=true and sagest_rubro.id=" + str(
                                rubro.idrubroepunemi)
                            cursor.execute(sql)
                            cursor.close()
                        rubro.epunemi=False
                        rubro.idrubroepunemi=0
                        rubro.save()
                        log(u"Reverso de rubro %s - pk = %s" % ( rubro,rubro.id), request, "edit")

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        if action == 'aprecomprobantepago':
            try:
                id = encrypt(request.POST['id'])
                tipo = int(request.POST['tipo'])
                observacion = request.POST['observacion']
                comprobante = ComprobanteAlumno.objects.get(id = int(id))
                mensaje = ''
                if tipo == 1:
                    comprobante.estados = 2
                elif tipo == 2:
                    comprobante.estados = 3
                    mensaje = u'Se ha rechazado'
                elif tipo == 3:
                    comprobante.estados = 4
                    mensaje = u'Se ha recaudado'
                else:
                    raise NameError("Inconsistencia de información")
                comprobante.save(request)
                log(u"Editó el estado del comprobante de pago %s"%(comprobante), request, 'edit')
                historial = HistorialGestionComprobanteAlumno(
                    comprobante = comprobante,
                    persona = persona,
                    observacion = observacion,
                    estado = comprobante.estados,
                    fecha = datetime.today()
                )
                if tipo == 2:
                    notificacion(
                        f'{mensaje} su pago.',
                        f'{mensaje} los valores de su comprobante de pago. {observacion}',
                        comprobante.persona,
                        None,
                        '/alu_finanzas',
                        comprobante.id,
                        1,
                        'SIE',
                        comprobante,
                        request
                    )
                elif tipo == 3:
                    notificacion(
                        f'{mensaje} su pago.',
                        f'{mensaje} los valores de su comprobante de pago. {observacion}',
                        comprobante.persona,
                        None,
                        '/alu_finanzas',
                        comprobante.id,
                        1,
                        'SIE',
                        comprobante,
                        request
                    )
                historial.save(request)
                log(u"Agregó historial al cambio de estado del comprobante de pago %s"%historial,request,'add')
                return JsonResponse({'result':'ok', 'mensaje':'Registro actualizado'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result':'bad', "mensaje": u"Error al guardar los datos. Detalle: %s"%(ex.__str__())})

        if action == 'aprecomprobantepagomasivo':
            try:
                id = request.POST.getlist('lista_items1[]',None)
                if id is None:
                    raise NameError("No se ha seleccionado al menos un registro")
                tipo = int(request.POST['tipo'])
                observacion = request.POST['observacion']
                for compro_id in id:
                    comprobante = ComprobanteAlumno.objects.get(id = int(encrypt(compro_id)))
                    if comprobante.estados == 3 or comprobante.estados == 4:
                        continue
                    mensaje = ''
                    if tipo == 1:
                        if comprobante.estados == 2:
                            continue
                        comprobante.estados = 2
                    elif tipo == 2:
                        comprobante.estados = 3
                        mensaje = u'Se ha rechazado'
                    elif tipo == 3:
                        comprobante.estados = 4
                        mensaje = u'Se ha recaudado'
                    else:
                        raise NameError("Inconsistencia de información")
                    comprobante.save(request)
                    log(u"Editó el estado del comprobante de pago %s"%(comprobante), request, 'edit')
                    historial = HistorialGestionComprobanteAlumno(
                        comprobante = comprobante,
                        persona = persona,
                        observacion = observacion,
                        estado = comprobante.estados,
                        fecha = datetime.today()
                    )
                    if tipo == 2:
                        notificacion(
                            f'{mensaje} su pago.',
                            f'{mensaje} los valores de su comprobante de pago. {observacion}',
                            comprobante.persona,
                            None,
                            '/alu_finanzas',
                            comprobante.id,
                            1,
                            'SIE',
                            comprobante,
                            request
                        )
                    elif tipo == 3:
                        notificacion(
                            f'{mensaje} su pago.',
                            f'{mensaje} los valores de su comprobante de pago. {observacion}',
                            comprobante.persona,
                            None,
                            '/alu_finanzas',
                            comprobante.id,
                            1,
                            'SIE',
                            comprobante,
                            request
                        )
                    historial.save(request)
                    log(u"Agregó historial al cambio de estado del comprobante de pago %s"%historial,request,'add')
                return JsonResponse({'result':'ok', 'mensaje':'Registro actualizado'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result':'bad', "mensaje": u"Error al guardar los datos. Detalle: %s"%(ex.__str__())})

        if action == 'removeliquidacion':
            try:
                if not 'id' in request.POST:
                    raise NameError('No se encontró el rubro seleccionado')
                id = int(encrypt(request.POST['id']))
                rubro = Rubro.objects.filter(status=True, id=id).first()
                if not rubro:
                    raise NameError('No se encontró el rubro seleccionado')
                if rubro.bloqueado:
                    raise NameError('El rubro seleccionado se encuentra bloqueado')
                if not rubro.esta_liquidado():
                    raise NameError('El rubro seleccionado no se encuentra liquidado')
                if not rubro.pagos_liquidados():
                    raise NameError('El rubro seleccionado no tiene pagos liquidados')
                pagos_liquidados = rubro.pagos_liquidados()
                liquidacion = PagoLiquidacion.objects.filter(pagos__in=pagos_liquidados).first()
                if not liquidacion:
                    raise NameError('No se contró la liquidación del rubro')
                liquidacion.pagos.clear()
                for pago in Pago.objects.filter(id__in=pagos_liquidados):
                    pago.delete()
                liquidacion.delete()
                rubro.cancelado = False
                rubro.save(request)
                log(u"Removió liquidación del rubro {}".format(rubro), request, 'del')
                return JsonResponse({'result': 'ok', 'mensaje': 'Liquidación removida'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": 'Error en la transacción. {}'.format(ex)})

        elif action == 'reporteperiodo':
            try:
                from settings import MEDIA_ROOT
                ruta = 'media/recaudaciones/'
                f = PeriodoForm(request.POST)
                if f.is_valid():
                    __author__ = 'Unemi'
                    filename = 'reporte_periodo_' + random.randint(1, 10000).__str__() + '.xlsx'
                    directory = os.path.join(MEDIA_ROOT, 'recaudaciones', filename)
                    workbook = xlsxwriter.Workbook(directory, {'constant_memory': True})
                    ws = workbook.add_worksheet('diagnostico')

                    periodo = f.cleaned_data['periodo']
                    formatoceldagris = workbook.add_format(
                        {'align': 'center', 'border': 1, 'text_wrap': True, 'fg_color': '#B6BFC0'})
                    formatocontable = workbook.add_format(
                        {'num_format': '_($* #,##0.00_);_($* (#,##0.00);_($* "-"??_);_(@_)'})
                    ws.write(0, 0, "PERIODO", formatoceldagris)
                    ws.write(0, 1, "CARRERA", formatoceldagris)
                    ws.write(0, 2, "ESTUDIANTE", formatoceldagris)
                    ws.write(0, 3, "IDENTIFICACION", formatoceldagris)
                    ws.write(0, 4, "EMAIL", formatoceldagris)
                    ws.write(0, 5, "CELULAR", formatoceldagris)
                    ws.write(0, 6, "VALOR", formatoceldagris)
                    ws.write(0, 7, "VALOR ADEUDADO", formatoceldagris)
                    ws.write(0, 8, "VALOR CANCELADO", formatoceldagris)
                    matriculados = Matricula.objects.filter(status=True, nivel__periodo=periodo).exclude(
                        retiradomatricula=True).order_by('nivel__periodo_id')
                    fila = 1
                    for mat in matriculados:
                        ws.write(fila, 0, str(periodo))
                        ws.write(fila, 1, str(mat.inscripcion.carrera))
                        ws.write(fila, 2, str(mat.inscripcion.persona))
                        ws.write(fila, 3, str(mat.inscripcion.persona.identificacion()))
                        ws.write(fila, 4, str(mat.inscripcion.persona.email))
                        ws.write(fila, 5, str(mat.inscripcion.persona.telefono))
                        valor = 0
                        valor = null_to_decimal(
                            Rubro.objects.filter(status=True, matricula=mat).aggregate(valor=Sum('valortotal'))['valor'], 2)
                        valoradeudado = null_to_decimal(
                            Rubro.objects.filter(status=True, matricula=mat, cancelado=False).aggregate(
                                valor=Sum('valortotal'))['valor'], 2)
                        valorcancelado = null_to_decimal(
                            Rubro.objects.filter(status=True, matricula=mat, cancelado=True).aggregate(
                                valor=Sum('valortotal'))['valor'], 2)
                        ws.write(fila, 6, valor,formatocontable)
                        ws.write(fila, 7, valoradeudado,formatocontable)
                        ws.write(fila, 8, valorcancelado,formatocontable)
                        fila = fila + 1
                    workbook.close()
                    ruta = ruta + filename
                    return JsonResponse({'to': ruta})
                else:
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            except Exception as ex:
                print(ex)
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'enviarclienterecibocaja':
                try:
                    recibo = PagoReciboCaja.objects.get(pk=request.GET['id'])
                    envio_recibocaja_cliente(recibo.id)
                except Exception as ex:
                    pass

            if action == 'diferirarancel':
                try:
                    data['title'] = u'Diferir Arancel'
                    data['rubro'] = Rubro.objects.get(pk=request.GET['rid'])
                    return render(request, "rec_finanzas/diferirarancel.html", data)
                except Exception as ex:
                    pass

            if action == 'delrubro':
                try:
                    data['title'] = u'Eliminar Rubro'
                    data['rubro'] = rubro = Rubro.objects.get(pk=request.GET['id'])
                    return render(request, "rec_finanzas/delrubro.html", data)
                except Exception as ex:
                    pass

            if action == 'delmatricula':
                try:
                    data['title'] = u'Desvincular Matricula'
                    data['rubro'] = Rubro.objects.get(pk=request.GET['id'])
                    return render(request, "rec_finanzas/delmatricula.html", data)
                except Exception as ex:
                    pass

            if action == 'liquidar':
                try:
                    data['title'] = u'Liquidar Rubro'
                    data['action'] = action
                    data['rubro'] = Rubro.objects.get(pk=request.GET['id'])
                    data['form'] = LiquidarRubroForm()
                    return render(request, "rec_finanzas/liquidar.html", data)
                except Exception as ex:
                    pass

            if action == 'liquidarconvenioposgrado':
                try:
                    data['title'] = u'Liquidar Rubro Posgrado'
                    data['action'] = action
                    data['rubro'] = Rubro.objects.get(pk=request.GET['id'])
                    data['form'] = LiquidarRubroForm()
                    return render(request, "rec_finanzas/liquidar.html", data)
                except Exception as ex:
                    pass

            if action == 'editrubro':
                try:
                    data['title'] = u'Editar Fecha de Rubro'
                    data['rubro'] = rubro = Rubro.objects.get(pk=request.GET['id'])
                    data['form'] = RubroForm(initial={'fechavence': rubro.fechavence})
                    return render(request, "rec_finanzas/editrubro.html", data)
                except Exception as ex:
                    pass

            if action == 'editrubrovalor':
                try:
                    data['title'] = u'Editar Rubro Valor'
                    data['rubro'] = rubro = Rubro.objects.get(pk=request.GET['id'])
                    data['form'] = RubroValorForm(initial={'valor': rubro.valor})
                    return render(request, "rec_finanzas/editrubrovalor.html", data)
                except Exception as ex:
                    pass

            if action == 'editnombrerubro':
                try:
                    data['title'] = u'Editar Rubro'
                    data['rubro'] = rubro = Rubro.objects.get(pk=request.GET['id'])
                    data['form'] = NombreRubroForm(initial={'nombre': rubro.nombre})
                    return render(request, "rec_finanzas/editnombrerubro.html", data)
                except Exception as ex:
                    pass

            if action == 'rubros':
                try:
                    nivel=None
                    url_vars = ''
                    data['title'] = u'Listado de rubros'
                    id = request.GET['id']
                    data['cliente'] = cliente = Persona.objects.get(pk=id)
                    url_vars += f'&id={id}'
                    url_vars += f'&action={action}'
                    data['puede_pagar'] = data['persona'].puede_recibir_pagos()
                    if 'nivel' in request.GET:
                        nivel = Nivel.objects.get(pk=int(request.GET['nivel']))
                        url_vars += f'&nivel={nivel}'
                    if 'ret' in request.GET:
                        ret = request.GET['ret']
                        url_vars += f'&ret={ret}'

                    rubrosnocancelados = cliente.rubro_set.filter(cancelado=False, status=True).order_by('cancelado', 'fechavence')
                    rubroscanceldos = cliente.rubro_set.filter(cancelado=True, status=True).order_by('fechavence')
                    rubros = list(chain(rubrosnocancelados, rubroscanceldos))
                    data['nivel']=nivel
                    paging = Paginator(rubros, 150)
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
                    data['rubro_arancel'] = RUBRO_ARANCEL
                    data['url_vars'] = url_vars
                    data['habilitado'] = True if data['puede_pagar'] and datetime.now().date() == data['persona'].ultima_fecha_caja() else False
                    data['asesorfinancieroposgrado'] = True if persona.es_asesor_financiamiento() else False
                    data['tiene_nota_debito'] = RubroNotaDebito.objects.filter(rubro__persona=cliente, rubro__cancelado=False).exists()
                    return render(request, "rec_finanzas/rubros.html", data)
                except Exception as ex:
                    pass

            if action == 'pagar':
                try:
                    data['title'] = u'Pago de Rubros'
                    ids = request.GET['ids'].split(",")
                    # aniorubro = int(request.GET['ar'])
                    tipodoc = request.GET['tdoc']
                    data['rubros'] = rubros = Rubro.objects.filter(id__in=ids).order_by('fechavence')
                    # for rubro in rubros:
                    #     if rubro.matricula:
                    #         if rubro.matricula.nivel.periodo_id == 158:
                    #             return HttpResponseRedirect("/rec_finanzas?action=rubros&id=%s&info=No se puede facturar rubros de matrícula de admisión 1s 2022."%rubro.persona_id)

                    valor = null_to_decimal(rubros.aggregate(valor=Sum('saldo'))['valor'], 2)
                    data['cliente'] = cliente = rubros[0].persona
                    data['clientefactura'] = cliente.cliente_factura(request)
                    data['puede_pagar'] = data['persona'].puede_recibir_pagos()
                    data['form'] = FormaPagoForm(initial={'fechacobro': datetime.now().date(),
                                                          'fecharet': datetime.now().date(),
                                                          'valor': valor})
                    data['pago_efectivo_id'] = FORMA_PAGO_EFECTIVO
                    data['pago_tarjeta_id'] = FORMA_PAGO_TARJETA
                    data['pago_cheque_id'] = FORMA_PAGO_CHEQUE
                    data['pago_deposito_id'] = FORMA_PAGO_DEPOSITO
                    data['pago_transferencia_id'] = FORMA_PAGO_TRANSFERENCIA
                    data['pago_electronico_id'] = FORMA_PAGO_ELECTRONICO
                    data['pago_porcobrar_id'] = FORMA_PAGO_CUENTA_PORCOBRAR
                    caja = request.session['persona'].lugarrecaudacion_set.get()
                    sesion_caja = caja.sesion_caja()
                    data['descuentos_facturas'] = DESCUENTOS_EN_FACTURAS
                    # data['reporte_0'] = obtener_reporte('comprobante_entrega_factura')
                    data['reporte_0'] = obtener_reporte('comprobante_entrega_factura_membrete')
                    data['reporte_1'] = obtener_reporte('comprobante_entrega_factura_no')

                    # data['reporte_2'] = obtener_reporte('comprobante_recibo_caja')

                    data['totalapagar'] = sum([x.saldo for x in rubros])
                    # SI EL RUBRO ES DE AÑO ACTUAL SE EMITE FACTURA CASO CONTRARIO RECIBO DE CAJA
                    data['emitefactura'] = True if tipodoc == 'F' else False
                    return render(request, "rec_finanzas/pagar.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'pagos':
                try:
                    data['rubro'] = rubro = Rubro.objects.get(pk=request.GET['id'])
                    data['title'] = u'Pagos del rubro '
                    data['pagos'] = rubro.pago_set.all()
                    # data['pagos'] = rubro.pago_set.filter(status=True)

                    data['reporte_rc'] = obtener_reporte('recibocaja_reporte')

                    return render(request, "rec_finanzas/pagos.html", data)
                except Exception as ex:
                    pass

            elif action == 'verdetalleevento':
                try:
                    data = {}
                    data['evento'] = CapEventoPeriodoIpec.objects.get(pk=int(request.GET['id']))
                    template = get_template("adm_capacitacioneventoperiodoipec/detalleevento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'ver_detalle_aud':
                try:
                    data["auditoria"] = auditoria = logRubros.objects.get(id=int(request.GET["pk"]))
                    if auditoria.datos_json and auditoria.datos_json != '[]':
                        datos = json.loads(auditoria.datos_json)
                        modelo = datos[0]["model"]
                        campos = sorted([x for x in list(datos[0]["fields"].keys()) if x != '__ff_detalle_ff__'])
                        if modelo == 'auth.user':
                            campos_temp = campos
                            campos = []
                            for c in campos_temp:
                                if c != 'password' and c != 'user_permissions':
                                    campos.append(c)
                        campos_tabla = [str(x).replace('_', ' ').strip().capitalize() for x in campos]
                        campos_tabla = campos_tabla
                        data["campos_tabla"] = ['Registro'] + campos_tabla
                        data["campos"] = ['__ff_detalle_ff__'] + campos
                        data["datos"] = datos
                        template = get_template('rec_finanzas/audlogdetalle.html',)
                        return JsonResponse({"resp": True, 'data': template.render(data), 'nombre': auditoria.rubroname})
                except Exception as ex:
                    print(sys.exc_info()[-1].tb_lineno)
                    return JsonResponse({"resp": False})

            elif action == 'logrubros':
                if not request.user.is_superuser:
                    return redirect(request.path)
                data['title'] = u'Auditoria de Rubros'
                desde, hasta, search, filtros, url_vars = request.GET.get('desde', ''),  request.GET.get('hasta', ''),  request.GET.get('search', ''), Q(status=True), ''

                if desde:
                    data['desde'] = desde
                    url_vars += "&desde={}".format(desde)
                    filtros = filtros & Q(fecha_creacion__gte=desde)
                else:
                    desde = str(datetime.today().date())
                    data['desde'] = desde
                    url_vars += "&desde={}".format(desde)
                    filtros = filtros & Q(fecha_creacion__gte=desde)
                if hasta:
                    data['hasta'] = hasta
                    url_vars += "&hasta={}".format(hasta)
                    filtros = filtros & Q(fecha_creacion__lte=hasta)
                if search:
                    data['search'] = search
                    filtros = filtros & (Q(idrubro__icontains=search) | Q(cedulapersona__icontains=search) | Q(persona__icontains=search))
                    url_vars += '&search={}'.format(search)
                url_vars += '&action={}'.format(action)
                data["url_vars"] = url_vars
                query = logRubros.objects.filter(filtros).order_by('-pk')
                data['listcount'] = query.count()
                paging = MiPaginador(query, 25)
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
                data['lista'] = page.object_list
                return render(request, "rec_finanzas/audlog.html", data)

            elif action == 'reporteperiodo':
                try:
                    data['form'] = PeriodoForm()
                    template = get_template("ajaxformmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            pass
            if action == 'comprobantespagos':
                try:
                    search = None
                    data['title'] = u'Comprobantes de pagos'
                    url_vars = ''
                    comprobante = ComprobanteAlumno.objects.filter(status=True,matricula__isnull = False, matricula__inscripcion__coordinacion__in = [1,2,3,4,5,9])
                    if 's' in request.GET:
                        data['s'] = search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) >1:
                            comprobante = comprobante.filter(Q(persona__apellido1__icontains = ss[0])&Q(persona__apellido2__icontains = ss[1]))
                        else:
                            comprobante = comprobante.filter(Q(id__icontains=search) | Q(persona__apellido1__icontains=search) | Q(persona__cedula__icontains = search)).distinct()
                        url_vars += f"&s={search}"
                    if 'estado' in request.GET:
                        data['estado'] = estado = int(request.GET['estado'])
                        comprobante = comprobante.filter(estados=estado)
                        url_vars +=f"&estado={estado}"

                    paging = MiPaginador(comprobante.order_by('-fecha_modificacion','-fecha_creacion'),25)
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
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data["url_vars"] = url_vars
                    data['listado']  = page.object_list
                    return render(request,'rec_finanzas/viewcomprobantes.html',data)
                except Exception as ex:
                    pass

            if action == 'historialcomprobantes':
                try:
                    data['title'] = u'Historial comprobante de pagos'
                    if not 'id' in request.GET:
                        raise NameError(u'No se encontro parametro de hostorial asignada.')
                    id = encrypt(request.GET['id'])
                    data['hisotrial']=historial = HistorialGestionComprobanteAlumno.objects.filter(comprobante_id=int(id))
                    template = get_template('rec_finanzas/modal/historialcomp.html')
                    return JsonResponse({'result':'ok','data':template.render(data)})
                except Exception as ex:
                    pass

            if action == 'comprobantesxlsx':
                try:
                    search = None
                    url_vars = ''
                    comprobante = ComprobanteAlumno.objects.filter(status=True, matricula__isnull=False, matricula__inscripcion__coordinacion__in=[1, 2, 3, 4, 5, 9])
                    if 's' in request.GET:
                        data['s'] = search = request.GET['s']
                        ss = search.split(' ')
                        if len(ss) > 1:
                            comprobante = comprobante.filter(Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1]))
                        else:
                            comprobante = comprobante.filter(Q(id__icontains=search) | Q(persona__apellido1__icontains=search) | Q(persona__cedula__icontains=search)).distinct()
                        url_vars += f"&s={search}"
                    if 'estado' in request.GET:
                        data['estado'] = estado = int(request.GET['estado'])
                        comprobante = comprobante.filter(estados=estado)
                        url_vars += f"&estado={estado}"
                    __author__ = 'Unemi'
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('comprobantesalumnos')
                    ws.set_column(0, 100, 60)
                    titulo = workbook.add_format({'font_name': 'Calibri', 'border': 1, 'align': 'center', 'font_size': 12, 'valign': 'vcenter', 'bg_color': '#E4E5DF'})
                    style2 = workbook.add_format({'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'align': 'center', 'font_size': 12, 'valign': 'vcenter'})
                    money = workbook.add_format({'text_wrap': True, 'font_name': 'Calibri', 'border': 1, 'align': 'center', 'font_size': 12, 'valign': 'vcenter', 'num_format': '$#,##0.00'})
                    row_num = 0
                    column = [
                        ('Estudiante',80),
                        ('Cedula',20),
                        ('Rubros',100),
                        ('Valor Rubros',20),
                        ('Valor a pagar',30),
                        ('Banco',60),
                        ('Tipo comprobante',60),
                        ('Fecha Pago',60),
                        ('Fecha Registro',60),
                        ('Estado',30),
                        ('Documento',50),
                    ]
                    for cl in range(len(column)):
                        ws.write(row_num,cl, column[cl][0],titulo)
                        ws.set_column(cl,cl,column[cl][1])
                    row_num +=1

                    for comp in comprobante:
                        if len(comp.rubroscomprobantealumno()) > 1:
                            roww=len(comp.rubroscomprobantealumno())+row_num
                            ws.merge_range("A%s:A%s"%(row_num+1,roww),comp.persona.nombre_completo(),style2)
                            ws.merge_range("B%s:B%s"%(row_num+1,roww),comp.persona.cedula,style2)
                            ws.merge_range("D%s:D%s"%(row_num+1,roww),comp.saldototalrubro(),money)
                            ws.merge_range("E%s:E%s"%(row_num+1,roww),comp.valor,money)
                            ws.merge_range("F%s:F%s"%(row_num+1,roww),comp.cuentabancaria.__str__(),style2)
                            ws.merge_range("G%s:G%s"%(row_num+1,roww),comp.get_tipocomprobante_display(),style2)
                            ws.merge_range("H%s:H%s"%(row_num+1,roww),str(comp.fechapago),style2)
                            ws.merge_range("I%s:I%s"%(row_num+1,roww),str(comp.fecha_creacion.strftime('%Y-%m-%d %H:%M')),style2)
                            ws.merge_range("J%s:J%s"%(row_num+1,roww),comp.get_estados_display(),style2)
                            ws.merge_range("K%s:K%s"%(row_num+1,roww),f"https://sga.unemi.edu.ec/{comp.comprobantes.url}",style2)
                            for rubros in comp.rubroscomprobantealumno():
                                ws.write(row_num,2,rubros.rubro.__str__(),style2)
                                row_num+=1
                        else:
                            ws.write(row_num, 0, comp.persona.nombre_completo(), style2)
                            ws.write(row_num, 1, comp.persona.cedula, style2)
                            ws.write(row_num, 2, comp.rubroscomprobantealumno().first().rubro.__str__() if comp.rubroscomprobantealumno() else "N/A", style2)
                            ws.write(row_num, 3, comp.saldototalrubro() if comp.rubroscomprobantealumno() else "0.00", money)
                            ws.write(row_num, 4, comp.valor, money)
                            ws.write(row_num, 5, comp.cuentabancaria.__str__(), style2)
                            ws.write(row_num, 6, comp.get_tipocomprobante_display(), style2)
                            ws.write(row_num, 7, str(comp.fechapago), style2)
                            ws.write(row_num, 8, str(comp.fecha_creacion.strftime('%Y-%m-%d %H:%M')), style2)
                            ws.write(row_num, 9, comp.get_estados_display(), style2)
                            ws.write(row_num, 10, f"https://sga.unemi.edu.ec/{comp.comprobantes.url}", style2)
                            row_num+=1
                    workbook.close()
                    output.seek(0)
                    filename = 'comprobantespago.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Consulta de finanzas'
            search = None
            ids = None
            url_vars = ""
            if 's' in request.GET:
                search = request.GET['s']
                url_vars += f'&s={search}'
                ss = search.split(' ')
                if len(ss) == 1:
                    personas = Persona.objects.filter(Q(nombres__icontains=search) |
                                                      Q(apellido1__icontains=search) |
                                                      Q(apellido2__icontains=search) |
                                                      Q(cedula__icontains=search) |
                                                      Q(pasaporte__icontains=search) |
                                                      Q(ruc__icontains=search)).distinct()
                else:
                    personas = Persona.objects.filter(Q(apellido1__icontains=ss[0]) &
                                                      Q(apellido2__icontains=ss[1])).distinct()
            elif 'id' in request.GET:
                ids = int(request.GET['id'])
                url_vars += f'&id={ids}'
                personas = Persona.objects.filter(id=ids)
            else:
                personas = Persona.objects.all()
            paging = MiPaginador(personas, 25)
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
            data['rangospaging'] = paging.rangos_paginado(p)
            data['url_vars'] = url_vars
            data['page'] = page
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['clientes'] = page.object_list
            caja = None
            sesioncaja = None
            try:
                caja = persona.mi_lugar_recaudacion()
                if SesionCaja.objects.filter(caja=caja, abierta=True).exists():
                    sesioncaja = SesionCaja.objects.get(caja=caja, abierta=True)
                    data['total_efectivo_sesion'] = sesioncaja.total_efectivo_sesion()
                    data['total_electronico_sesion'] = sesioncaja.total_electronico_sesion()
                    data['total_cuentasxcobrar_sesion'] = sesioncaja.total_cuentasxcobrar_sesion()
                    data['cantidad_facturas_sesion'] = sesioncaja.cantidad_facturas_sesion()
                    data['cantidad_facturasanuladas_sesion'] = sesioncaja.cantidad_facturasanuladas_sesion()
                    data['cantidad_cheques_sesion'] = sesioncaja.cantidad_cheques_sesion()
                    data['cantidad_cuentasxcobrar_sesion'] = sesioncaja.cantidad_cuentasxcobrar_sesion()
                    data['total_cheque_sesion'] = sesioncaja.total_cheque_sesion()
                    data['cantidad_tarjetas_sesion'] = sesioncaja.cantidad_tarjetas_sesion()
                    data['total_tarjeta_sesion'] = sesioncaja.total_tarjeta_sesion()
                    data['cantidad_depositos_sesion'] = sesioncaja.cantidad_depositos_sesion()
                    data['total_deposito_sesion'] = sesioncaja.total_deposito_sesion()
                    data['total_recibocaja_sesion'] = sesioncaja.total_recibocaja_sesion()
                    data['cantidad_transferencias_sesion'] = sesioncaja.cantidad_transferencias_sesion()
                    data['total_transferencia_sesion'] = sesioncaja.total_transferencia_sesion()
                    data['total_sesion'] = sesioncaja.total_sesion()
            except:
                pass
            data['caja'] = caja
            data['sesioncaja'] = sesioncaja
            data['puede_pagar'] = data['persona'].puede_recibir_pagos()
            data['fecha'] = hoy = datetime.now().date()
            data['NOMBRE_CERTIFICADO'] = variable_valor('NOMBRE_CERTIFICADO')
            data['FECHA_CADUCIDAD_CERTIFICADO'] = fecha = variable_valor('FECHA_CADUCIDAD_CERTIFICADO')
            x = fecha - hoy
            data['dias'] = x.days
            data['periodos'] = Periodo.objects.filter(status=True).order_by('pk')
            return render(request, "rec_finanzas/view.html", data)
