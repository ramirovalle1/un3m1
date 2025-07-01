# -*- coding: UTF-8 -*-
import io
import base64
import json
import random
import subprocess
import sys
import uuid
from datetime import datetime
from decimal import Decimal

import xlsxwriter
from django.contrib import messages
from django.contrib.admin.models import LogEntry
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.test.testcases import TestCase
import xlwt
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template.loader import get_template
from xlwt import *
from django.shortcuts import render
from zeep import Client

from decorators import secure_module
from sagest.forms import DepartamentoForm, IntegranteDepartamentoForm, ResponsableDepartamentoForm, SeccionDepartamentoForm, ServicioModeloForm, LiquidacionCompraForm, ServicioCompraForm, ReporteLiquidacionCompraFrom
from sagest.models import Departamento, SeccionDepartamento, TipoOtroRubro, ProcesoLiquidacion, SolicitudLiquidacion, \
    RequisitoLiquidacion, LiquidacionCompra, ServicioCompra, ServicioModelo, Proveedor, DetalleLiquidacionCompra, PuntoVenta, IvaAplicado, TipoRetenciones, TIPO_ASIENTO, Impuesto, ESTADO_COMPROBANTE
from settings import DEBUG, EMAIL_DOMAIN, TIPO_AMBIENTE_FACTURACION, JR_JAVA_COMMAND, JR_RUN_SING_SIGNCLI, PASSSWORD_SIGNCLI, SERVER_URL_SIGNCLI, SERVER_USER_SIGNCLI, SERVER_PASS_SIGNCLI, URL_SERVICIO_ENVIO_SRI_PRUEBAS, URL_SERVICIO_ENVIO_SRI_PRODUCCION, URL_SERVICIO_AUTORIZACION_SRI_PRUEBAS, URL_SERVICIO_AUTORIZACION_SRI_PRODUCCION
from sga.commonviews import adduserdata, obtener_reporte
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.templatetags.sga_extras import encrypt
from .commonviews import secuencia_recaudacion
from sga.funciones import MiPaginador, log, generar_nombre, null_to_decimal
from sga.models import Administrativo, Persona, miinstitucion
from .rec_notacredito import envio_comprobante_cliente_notacredito

unicode = str
Text = str


def crear_representacion_xml_liquidacion(id, proceso_siguiente=False):
    liquidacion = LiquidacionCompra.objects.get(pk=int(id))
    template = get_template("xml/liquidacion_compra.html")
    d = ({'comprobante': liquidacion,
                 'institucion': miinstitucion()})
    xml_content = template.render(d)
    liquidacion.xml = xml_content
    liquidacion.weburl = uuid.uuid4().hex
    liquidacion.xmlgenerado = True
    liquidacion.save()
    if proceso_siguiente:
        firmar_comprobante_liquidacion(liquidacion.id)


def firmar_comprobante_liquidacion(id):
    liquidacion = LiquidacionCompra.objects.get(pk=int(id))
    token = miinstitucion().token
    if not token:
        return False

    import os
    runjrcommand = [JR_JAVA_COMMAND, '-jar',
                    os.path.join(JR_RUN_SING_SIGNCLI, 'SignCLI.jar'),
                    token.file.name,
                    PASSSWORD_SIGNCLI,
                    SERVER_URL_SIGNCLI + "/sign_liquidacion/" + liquidacion.weburl]
    if SERVER_USER_SIGNCLI and SERVER_PASS_SIGNCLI:
        runjrcommand.append(SERVER_USER_SIGNCLI)
        runjrcommand.append(SERVER_PASS_SIGNCLI)
    try:
        mens = ''
        mensaje = ''
        for m in runjrcommand:
            mens += ' ' + m
        if DEBUG:
            runjr = subprocess.run(mens, shell=True, check=True)
        else:
            runjr = subprocess.call(runjrcommand)
    except:
        pass


def envio_comprobante_sri_liquidacion(id, proceso_siguiente=False):
    try:
        liquidacion = LiquidacionCompra.objects.get(pk=int(id))
        xml = liquidacion.xmlfirmado
        test = TestCase
        # d = base64.b64encode(xml.encode('utf-8'))
        if liquidacion.tipoambiente == 1:
            WSDL = URL_SERVICIO_ENVIO_SRI_PRUEBAS  # 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantes?wsdl'
        else:
            WSDL = URL_SERVICIO_ENVIO_SRI_PRODUCCION  # 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantes?wsdl'
        client = Client(WSDL)
        d = base64.b64encode(liquidacion.xmlfirmado.encode('utf-8'))
        respuesta = client.service.validarComprobante(liquidacion.xmlfirmado.encode('utf-8'))
        liquidacion.falloenviodasri = False
        liquidacion.mensajeenvio = ''
        liquidacion.enviadasri = True
        estado = "RECIBIDA"
        yaenviado = False
        if respuesta.comprobantes:
            for m in respuesta.comprobantes.comprobante[0].mensajes.mensaje:
                if m.identificador == '43' or m.identificador == '45':
                    yaenviado = True
                    liquidacion.falloenviodasri = False
                    liquidacion.mensajeenvio = ''
                    liquidacion.enviadasri = True
                else:
                    if unicode(m.mensaje):
                        liquidacion.mensajeenvio = unicode(m.mensaje)
                    try:
                        if unicode(m.informacionAdicional):
                            liquidacion.mensajeenvio += ' ' + unicode(m.informacionAdicional)
                    except Exception as ex:
                        pass
        try:
            estado = unicode(respuesta.estado)
        except Exception as ex:
            pass
        if estado == "RECIBIDA" or yaenviado:
            liquidacion.falloenviodasri = False
            liquidacion.enviadasri = True
            liquidacion.mensajeenvio = ''
            liquidacion.save()
            if proceso_siguiente:
                autorizacion_comprobante_liquidacion(liquidacion.id, proceso_siguiente=proceso_siguiente)
        else:
            liquidacion.falloenviodasri = True
            liquidacion.estado = 2
            liquidacion.save()
    except Exception as ex:
        pass


def autorizacion_comprobante_liquidacion(id, proceso_siguiente=False):
    liquidacion = LiquidacionCompra.objects.get(pk=int(id))
    if not liquidacion.enviadasri:
        return False
    if liquidacion.tipoambiente == 1:
        WSDL = URL_SERVICIO_AUTORIZACION_SRI_PRUEBAS  # 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantes?wsdl'
    else:
        WSDL = URL_SERVICIO_AUTORIZACION_SRI_PRODUCCION  # 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantes?wsdl'
    client = Client(WSDL)
    respuesta = client.service.autorizacionComprobante(liquidacion.claveacceso)
    liquidacion.autorizada = False
    liquidacion.falloautorizacionsri = True
    if int(respuesta.numeroComprobantes) > 0:
        autorizacion = respuesta.autorizaciones.autorizacion[0]
        if autorizacion.estado == 'AUTORIZADO':
            liquidacion.autorizada = True
            liquidacion.falloautorizacionsri = False
            liquidacion.autorizacion = unicode(autorizacion.numeroAutorizacion) if autorizacion.estado == 'AUTORIZADO' else ''
            liquidacion.fechaautorizacion = autorizacion.fechaAutorizacion
            liquidacion.save()
            # if proceso_siguiente:
            #     envio_comprobante_cliente_liquidacion(liquidacion.id)
        elif type(autorizacion.mensajes) != Text:
            liquidacion.falloautorizacionsri = True
            liquidacion.estado = 2
            # for mensaje in autorizacion.mensajes.mensaje:
            for mensaje in autorizacion.mensajes.mensaje:
                if unicode(mensaje.mensaje):
                    liquidacion.mensajeautorizacion = unicode(mensaje.mensaje)
                if unicode(mensaje.informacionAdicional):
                    liquidacion.mensajeautorizacion += ' ' + unicode(mensaje.informacionAdicional)
            liquidacion.save()

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']
        #servicos modelo
        if action == 'addserviciomodelo':
            try:
                with transaction.atomic():
                    form = ServicioModeloForm(request.POST)
                    if form.is_valid():
                        liquidacion = ServicioModelo(
                            descripcion = form.cleaned_data['descripcion'])
                        liquidacion.save(request)
                        log(u'Adicionó servicio modelo para liquidacion en compra: %s' % liquidacion, request, "add")
                        return JsonResponse({"result": False}, safe=False)

                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True,'modalsuccess': True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True,'modalsuccess': True, "mensaje": "Intentelo más tarde."}, safe=False)
        elif action == 'editserviciomodelo':
            try:
                with transaction.atomic():
                    servicio = ServicioModelo.objects.get(pk=request.POST['id'])
                    form = ServicioModeloForm(request.POST)
                    if form.is_valid():
                        servicio.descripcion = form.cleaned_data['descripcion']
                        servicio.save(request)
                        log(u'Editó servicio modelo para liquidacion en compra: %s' % servicio, request, "add")
                        return JsonResponse({"result": False}, safe=False)

                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, 'modalsuccess': True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True,'modalsuccess': True, "mensaje": "Intentelo más tarde."}, safe=False)
        elif action == 'delserviciomodelo':
            try:
                with transaction.atomic():
                    servicio = ServicioModelo.objects.get(pk=request.POST['id'])
                    if not servicio.en_uso():
                        servicio.status = False
                        servicio.save(request)
                        log(u'Eliminó servicio modelo para liquidacion en compra: %s' % servicio, request, "add")
                        return JsonResponse({"error": False})
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, 'modalsuccess': True, "mensaje": "No puede eliminar este servicio"}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True,'modalsuccess': True, "mensaje": "Intentelo más tarde."}, safe=False)
        # servicio para liquidacion de compra
        elif action == 'addservicio':
            try:
                with transaction.atomic():
                    form = ServicioCompraForm(request.POST)
                    if form.is_valid():
                        liquidacion = ServicioCompra(
                            descripcion = form.cleaned_data['descripcion'],
                            tiposervicio = form.cleaned_data['tiposervicio'],
                            valor = form.cleaned_data['valor']
                        )
                        liquidacion.save(request)
                        log(u'Adicionó servicio para liquidacion en compra: %s' % liquidacion, request, "add")
                        return JsonResponse({"result": False}, safe=False)

                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True,'modalsuccess': True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True,'modalsuccess': True, "mensaje": "Intentelo más tarde."}, safe=False)
        elif action == 'editservicio':
            try:
                with transaction.atomic():
                    servicio = ServicioCompra.objects.get(pk=request.POST['id'])
                    form = ServicioCompraForm(request.POST)
                    if form.is_valid():
                        servicio.descripcion = form.cleaned_data['descripcion']
                        servicio.tiposervicio = form.cleaned_data['tiposervicio']
                        servicio.valor = form.cleaned_data['valor']
                        servicio.save(request)
                        log(u'Editó servicio para liquidacion en compra: %s' % servicio, request, "add")
                        return JsonResponse({"result": False}, safe=False)

                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, 'modalsuccess': True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True,'modalsuccess': True, "mensaje": "Intentelo más tarde."}, safe=False)
        elif action == 'delservicio':
            try:
                with transaction.atomic():
                    servicio = ServicioCompra.objects.get(pk=request.POST['id'])
                    if not servicio.en_uso():
                        servicio.status = False
                        servicio.save(request)
                        log(u'Eliminó servicio para liquidacion en compra: %s' % servicio, request, "add")
                        return JsonResponse({"error": False})
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, 'modalsuccess': True, "mensaje": "No puede eliminar este servicio"}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True,'modalsuccess': True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'get_proveedor':
            try:
                id = int(request.POST['id'])
                proveedor = Proveedor.objects.get(id=id)
                fecha = "%02d-%02d-%4d" % (proveedor.fechacaducidad.day, proveedor.fechacaducidad.month, proveedor.fechacaducidad.year) if proveedor.fechacaducidad else None
                data = {
                    "result": "ok",
                    "autorizacion": proveedor.autorizacion.strip() if proveedor.autorizacion else None,
                    "fechacaducidad": fecha,
                }
                return JsonResponse(data)
            except Exception as ex:
                messages.error(request, ex)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'get_impuesto':
            try:
                id = int(request.POST['id'])
                impuesto = Impuesto.objects.get(id=id)
                data = {"result": "ok", "porcentaje": (impuesto.porcentaje) if impuesto.porcentaje else 0 }
                return JsonResponse((data))
            except Exception as ex:
                messages.error(request, ex)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addliquidacioncompra_old':
            try:
                f = LiquidacionCompraForm(request.POST)
                if not f.is_valid():
                    raise NameError([{k: v[0]} for k, v in f.errors.items()])
                ids = json.loads(request.POST['lista_items1'])
                if len(ids) < 1:
                    raise NameError('Debe selecionar al menos un servicio')
                proveedor = Proveedor.objects.filter(id=int(f.cleaned_data['proveedor'].id)).first()

                puntoventa = PuntoVenta.objects.get(id=1)
                secuencial = LiquidacionCompra.genera_secuencial()
                secuencial_req = int(request.POST.get('secuencial'))

                liquidacion_generada = LiquidacionCompra.objects.filter(puntoventa=puntoventa, numero=secuencial)
                if liquidacion_generada.values('id').exists():
                    raise NameError(u"Número de liquidación ya existe.")

                # if proveedor is not None:
                #     if proveedor.autorizacion != f.cleaned_data['autorizacion']:
                #         proveedor.autorizacion = f.cleaned_data['autorizacion']
                #
                #     if proveedor.fechacaducidad != f.cleaned_data['fechacaducidad']:
                #         proveedor.fechacaducidad = f.cleaned_data['fechacaducidad']
                #
                #     proveedor.save(request)

                if not proveedor.email:
                    raise NameError('El proveedor seleccionado debe tener registrado email')

                glosa = 'Liquidación en compras por concepto de: '

                secuencial= LiquidacionCompra.genera_secuencial()
                numerocompleto = LiquidacionCompra.genera_secuencial_comprobante()
                iva_aplicado = IvaAplicado.objects.filter(status=True, porcientoiva=(f.cleaned_data['impuesto'].porcentaje / 100)).first()

                liq = LiquidacionCompra(proveedor=proveedor,
                                        fecha=datetime.now(),
                                        numerocompleto=numerocompleto,
                                        numero=secuencial,
                                        puntoventa=puntoventa,
                                        valida=True,
                                        pagada=True,
                                        electronica=True,
                                        impresa=False,
                                        identificacion=proveedor.identificacion,
                                        tipo=proveedor.tipoidentificacion,
                                        nombre=proveedor.nombre,
                                        direccion=proveedor.direccion,
                                        telefono=proveedor.telefono,
                                        email=proveedor.email,
                                        tipoambiente=TIPO_AMBIENTE_FACTURACION,
                                        observacion=glosa,
                                        ivaaplicado=iva_aplicado)
                liq.save()
                secuencia_recaudacion(request, puntoventa, campo='liquidacioncompra')
                query = ServicioCompra.objects.filter(status=True, id__in=ids)
                subtotal = request.POST['subtotal']
                iva = request.POST['iva']
                total = request.POST['total']
                if iva_aplicado.id == 1:
                    liq.subtotal_base0 = subtotal
                else:
                    liq.subtotal_base_iva = subtotal
                liq.total_iva = iva
                liq.total = total
                liq.save(request)
                for serv in query:
                    det = DetalleLiquidacionCompra(liquidacion=liq,
                                                   servicio=serv,
                                                   valor=serv.subtotal_sin_iva(liq.ivaaplicado.porcientoiva),
                                                   subtotal=serv.subtotal_sin_iva(liq.ivaaplicado.porcientoiva),
                                                   iva=serv.valor_iva(liq.ivaaplicado.porcientoiva),
                                                   total=serv.valor_total(liq.ivaaplicado.porcientoiva))
                    det.save(request)
                    glosa += str(serv.descripcion)
                liq.claveacceso = liq.genera_clave_acceso_liquidacion()
                liq.save(request)
                log('Adiciono nueva liquidadcion en compra', request, 'add')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s" % ex.__str__()})

        elif action == 'addliquidacioncompra':
            try:
                f = LiquidacionCompraForm(request.POST)
                if not f.is_valid():
                    raise NameError([{k: v[0]} for k, v in f.errors.items()])
                jsonLiquidacion = json.loads(request.POST['table-data-services'])
                if jsonLiquidacion['items'].__len__() < 1:
                    raise NameError('Debe selecionar al menos un servicio')
                puntoventa_id = 1
                secuencial = LiquidacionCompra.genera_secuencial()
                liquidacion_generada = LiquidacionCompra.objects.filter(puntoventa_id=puntoventa_id, numero=secuencial)
                if liquidacion_generada.values('id').exists():
                    raise NameError(u"Número de liquidación ya existe.")

                if not f.cleaned_data['proveedor'].email:
                    raise NameError('El proveedor seleccionado debe tener registrado email')

                glosa = 'Liquidación en compras por concepto de: '
                numerocompleto = LiquidacionCompra.genera_secuencial_comprobante()
                iva_aplicado = IvaAplicado.objects.filter(status=True, porcientoiva=(f.cleaned_data['impuesto'].porcentaje / 100)).first()
                liquidacion = LiquidacionCompra(proveedor=f.cleaned_data['proveedor'],
                                                fecha=datetime.now(),
                                                numerocompleto=numerocompleto,
                                                numero=secuencial,
                                                puntoventa_id=puntoventa_id,
                                                valida=True,
                                                pagada=True,
                                                electronica=True,
                                                impresa=False,
                                                identificacion=f.cleaned_data['proveedor'].identificacion,
                                                tipo=f.cleaned_data['proveedor'].tipoidentificacion,
                                                nombre=f.cleaned_data['proveedor'].nombre,
                                                direccion=f.cleaned_data['proveedor'].direccion,
                                                telefono=f.cleaned_data['proveedor'].telefono,
                                                email=f.cleaned_data['proveedor'].email,
                                                tipoambiente=TIPO_AMBIENTE_FACTURACION,
                                                observacion=glosa,
                                                ivaaplicado=iva_aplicado)
                liquidacion.save()
                secuencia_recaudacion(request, liquidacion.puntoventa, campo='liquidacioncompra')
                if iva_aplicado.id == 1:
                    liquidacion.subtotal_base0 = jsonLiquidacion['subtotal']
                else:
                    liquidacion.subtotal_base_iva = jsonLiquidacion['subtotal']
                liquidacion.total_iva = jsonLiquidacion['iva']
                liquidacion.total = jsonLiquidacion['total']
                itemsServices = jsonLiquidacion['items']
                for item in itemsServices:
                    detalle = DetalleLiquidacionCompra(
                        liquidacion=liquidacion,
                        servicio_id=item['id'],
                        valor=null_to_decimal(item['valor'], 2),
                        cantidad=int(item['cantidad']),
                        subtotal=null_to_decimal(item['subtotal'], 2),
                        iva=null_to_decimal(item['iva'], 2),
                        total=null_to_decimal(item['total'], 2)
                    )
                    # detalle.iva = null_to_decimal((detalle.subtotal)*null_to_decimal(iva_aplicado.porcientoiva, 2), 2)
                    # detalle.total = null_to_decimal(detalle.subtotal + detalle.iva, 2)
                    detalle.save(request)
                    glosa += str(detalle.servicio.descripcion)
                liquidacion.claveacceso = liquidacion.genera_clave_acceso_liquidacion()
                liquidacion.save(request)
                log('Adiciono nueva liquidadcion en compra %s' % liquidacion, request, 'add')
                print(request.POST)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"%s" % ex.__str__()})

        elif action == 'anular_liquidacion_compra':
            try:
                id = int(request.POST['id'])
                liquidacion = LiquidacionCompra.objects.get(pk=id)
                liquidacion.estado = 3
                liquidacion.save(request)
                log(u'Anuló liquidacion compra: %s' % liquidacion, request, "add")
                data = {"result": "ok"}
                return JsonResponse(data)
            except Exception as ex:
                messages.error(request, ex)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'enviarcliente':
            try:
                liquidacion = LiquidacionCompra.objects.get(pk=request.POST.get('id'))
                liquidacion.enviar_comprobante_liquidacion_a_cliente(request, data)
                return JsonResponse({"result": 'ok', 'mensaje': u'se envió correctamente  el comprobante al correo <b>%s<b>' % liquidacion.email})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": 'bad', 'mensaje': u'%s' % ex.__str__()})

        elif action == 'loadDataTableServices':
            try:
                txt_filter = request.POST['sSearch'] if request.POST['sSearch'] else ''
                limit = int(request.POST['iDisplayLength']) if request.POST['iDisplayLength'] else 25
                offset = int(request.POST['iDisplayStart']) if request.POST['iDisplayStart'] else 0
                excl = json.loads(request.POST.get('excl', ''))
                servicios = ServicioCompra.objects.filter(status=True).exclude(pk__in=excl)
                if txt_filter:
                    servicios = servicios.filter(
                        tiposervicio__descripcion__icontains=txt_filter,
                        descripcion__icontains=txt_filter
                    )
                tCount = servicios.__len__()
                if offset == 0:
                    rows = servicios[offset:limit]
                else:
                    rows = servicios[offset:offset + limit]

                aaData = [serv.convertir_json() for serv in rows]
                return JsonResponse({"result": "ok", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            # modelo de servicio para usar varios como detalle
            if action == 'listaserviciosmodelo':
                data['title'] = u'Tipo de Servicios'
                url_vars = ''
                filtro = Q(status=True)
                search = None
                ids = None
                if 's' in request.GET:
                    if request.GET['s'] != '':
                        search = request.GET['s']

                if search:
                    filtro = filtro & (Q(descripcion__icontains=search))
                    url_vars += '&s=' + search

                servicios = ServicioModelo.objects.filter(filtro).order_by('descripcion')

                data['total'] = len(servicios)

                paging = MiPaginador(servicios, 25)
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
                data["url_vars"] = url_vars
                data['ids'] = ids if ids else ""
                data['servicios'] = page.object_list
                return render(request, 'adm_liquidacioncompras/serviciosmodeloview.html', data)
            elif action == 'addserviciomodelo':
                try:
                    data['form'] = ServicioModeloForm()
                    data['action'] = action
                    template = get_template("adm_liquidacioncompras/modal/serviciocompra.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            elif action == 'editserviciomodelo':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ServicioModelo.objects.get(pk=request.GET['id'])
                    data['form'] = ServicioModeloForm(initial=model_to_dict(filtro))
                    template = get_template("adm_liquidacioncompras/modal/serviciocompra.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            # servicio para liquidacion de compra
            elif action == 'addservicio':
                try:
                    data['form'] = ServicioCompraForm()
                    data['action'] = action
                    template = get_template("adm_liquidacioncompras/modal/serviciocompra.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            elif action == 'editservicio':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ServicioCompra.objects.get(pk=request.GET['id'])
                    data['form'] = ServicioCompraForm(initial=model_to_dict(filtro))
                    data['action'] = action
                    template = get_template("adm_liquidacioncompras/modal/serviciocompra.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass
            elif action == 'listaservicios':

                data['title'] = u'Servicios'
                url_vars = ''
                filtro = Q(status=True)
                search = None
                ids = None
                if 's' in request.GET:
                    if request.GET['s'] != '':
                        search = request.GET['s']

                if search:
                    filtro = filtro & (Q(descripcion__icontains=search))
                    url_vars += '&s=' + search

                servicios = ServicioCompra.objects.filter(filtro).order_by('tiposervicio')

                data['total'] = len(servicios)

                paging = MiPaginador(servicios, 25)
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
                data["url_vars"] = url_vars
                data['ids'] = ids if ids else ""
                data['servicios'] = page.object_list
                data['email_domain'] = EMAIL_DOMAIN
                return render(request, 'adm_liquidacioncompras/serviciosview.html', data)

            elif action == 'get_proveedor':
                try:
                    data = {}
                    id = request.GET['id']
                    proveedor = Proveedor.objects.get(id=id)
                    data['data'] = {'nombre': proveedor.nombre, 'tipoidentificacion': proveedor.get_tipoidentificacion_display(),
                                    'alias': proveedor.alias, 'tipoproveedor': proveedor.get_tipoproveedor_display(),
                                   'identificacion': proveedor.identificacion, 'autorizacion': proveedor.autorizacion,
                    'fechacaducidad': str(proveedor.fechacaducidad) if proveedor.fechacaducidad else '', 'direccion': proveedor.direccion, 'pais': proveedor.pais.nombre if proveedor.pais else '',  'telefono': proveedor.telefono,
                    'celular': proveedor.celular, 'email': proveedor.email, 'fax': proveedor.fax, 'obligado': proveedor.obligado, 'cuentabanco': proveedor.cuentabanco.__str__()}
                    data['result'] = True
                    return HttpResponse(json.dumps(data), content_type='application/json')
                except Exception as e:
                    print(e)
                    pass

            elif action == 'searchserviciocompra':
                ids = json.loads(request.GET['idser'])
                data = {}
                query = ServicioCompra.objects.filter(status=True).exclude(id__in=ids)
                if 'term' in request.GET:
                    data['term'] = term = request.GET['term']
                    query = query.filter(descripcion__icontains=term)
                data['servicios'] = query
                template = get_template("adm_liquidacioncompras/modal/detalleservicio.html")
                return JsonResponse({'result': True,'html': template.render(data)}, safe=False)

            elif action == 'llenardetalle':
                query = ServicioCompra.objects.filter(status=True)
                subtotal = 0
                iva = 0
                total = 0
                impuesto = Impuesto.objects.get(id=int(request.GET['idimpuesto']))
                porcien = impuesto.porcentaje / 100
                masuno = 1+porcien
                if 'idser' in request.GET:
                    ids = json.loads(request.GET['idser'])
                    if len(ids) > 0:
                        query = query.filter(id__in=ids)
                        total = query.aggregate(sub=Sum('valor')).get('sub')
                    else:
                        query = query.none()
                else:
                    query = query.none()
                data['servicios'] = query
                template = get_template("adm_liquidacioncompras/detalleservicioprincipal.html")

                # ivaaplicado = Impuesto.objects.get(id=request.GET['porcentaje']).get('porcentaje')
                #data['subtotal'] = subtotal = round(float(total)/float(masuno), 2)
                data['subtotal'] = subtotal = round(Decimal(total), 2)
                data['iva'] = iva = round(subtotal*Decimal(porcien), 2)
                data['total'] = total = round(Decimal(total) + iva, 2)


                template2 = get_template("adm_liquidacioncompras/totales.html")
                return JsonResponse({'result': True, 'html': template.render(data), 'totales': template2.render(data), 'total': total, 'iva': iva, 'subtotal': subtotal}, safe=False)


            elif action == 'getserviciocompra':
                data = []
                id = request.POST['id']
                liquidacion = ServicioCompra.objects.filter(pk=id)
                for i in liquidacion:
                    item = i.toJSON()
                    item['cantidad'] = 1
                    item['subtotal'] = 0.00
                    data.append(item)
                return HttpResponse(json.dumps(data), content_type='application/json')

            elif action == 'detalleliquidacion':
                try:
                    data['liquidacion'] = liq = LiquidacionCompra.objects.get(id=int(encrypt(request.GET['id'])))
                    data['liq'] = True
                    template = get_template("adm_liquidacioncompras/modal/detalle.html")
                    return JsonResponse({'result': True, 'data': template.render(data)}, safe=False)
                except Exception as ex:
                    pass

            elif action == 'addliquidacioncompra_old':
                try:
                    data['title'] = u'Adicionar Liquidacion en Compras'
                    secuencial = LiquidacionCompra.genera_secuencial()
                    numerodocumento = LiquidacionCompra.genera_secuencial_comprobante()
                    form = LiquidacionCompraForm()
                    form.fields['numerodocumento'].initial = numerodocumento
                    data['form'] = form
                    data['secuencial'] = secuencial
                    data['retencion2'] = TipoRetenciones.objects.filter(fuenteservicio=True)
                    data['retencion3'] = TipoRetenciones.objects.filter(iva=True)
                    data['tipo_asiento'] = TIPO_ASIENTO
                    data['action'] = action
                    return render(request, "adm_liquidacioncompras/addliquidacion_old.html", data)
                except Exception as ex:
                    pass

            elif action == 'addliquidacioncompra':
                try:
                    data['title'] = u'Adicionar Liquidacion en Compras'
                    secuencial = LiquidacionCompra.genera_secuencial()
                    data['impuesto'] = impuesto = Impuesto.objects.filter(tipo=0).first()
                    numerodocumento = LiquidacionCompra.genera_secuencial_comprobante()
                    form = LiquidacionCompraForm()
                    form.fields['numerodocumento'].initial = numerodocumento
                    form.fields['impuesto'].initial = impuesto
                    data['form'] = form
                    data['secuencial'] = secuencial
                    data['action'] = action
                    return render(request, "adm_liquidacioncompras/addliquidacion.html", data)
                except Exception as ex:
                    pass

            # procesos del sri
            elif action == 'generarxmlliqu':
                try:
                    cuenta = LiquidacionCompra.objects.get(pk=int((request.GET['id'])))
                    crear_representacion_xml_liquidacion(cuenta.id)
                except Exception as ex:
                    messages.warning(request, ex)

            elif action == 'firmarliqu':
                try:
                    cuenta = LiquidacionCompra.objects.get(pk=int((request.GET['id'])))
                    firmar_comprobante_liquidacion(cuenta.id)
                except Exception as ex:
                    messages.warning(request, ex)

            elif action == 'enviosriliqu':
                try:
                    cuenta = LiquidacionCompra.objects.get(pk=int((request.GET['id'])))
                    envio_comprobante_sri_liquidacion(cuenta.id)
                except Exception as ex:
                    messages.warning(request, ex)

            elif action == 'autorizarliqu':
                try:
                    cuenta = LiquidacionCompra.objects.get(pk=int((request.GET['id'])))
                    autorizacion_comprobante_liquidacion(cuenta.id)
                except Exception as ex:
                    messages.warning(request, ex)

            if action == 'rpt_liquidacion_compra':
                try:
                    filtro = Q(status=True)
                    fecha_desde = request.GET.get('fecha_desde')
                    fecha_hasta = request.GET.get('fecha_hasta')
                    report_title = 'REPORTE DE  LIQUIDACIONES DE COMPRA DE BIENES Y PRESTACIÓN DE SERVICIOS'
                    d_fecha_desde = None
                    d_fecha_hasta = None
                    if fecha_desde and fecha_hasta:
                        report_title += f'DESDE {fecha_desde} HASTA {fecha_hasta}'
                        d_fecha_desde = datetime.strptime(fecha_desde, '%d-%m-%Y').date()
                        d_fecha_hasta = datetime.strptime(fecha_hasta, '%d-%m-%Y').date()
                        filtro &= Q(fecha__range=[d_fecha_desde, d_fecha_hasta])
                    elif fecha_desde or fecha_hasta:
                        report_title += f'CON FECHA DE {fecha_desde if fecha_desde else fecha_hasta}'
                        d_fecha = datetime.strptime(fecha_desde if fecha_desde else fecha_hasta, '%d-%m-%Y').date()
                        filtro &= Q(fecha=d_fecha)

                    estado = request.GET.get('estado')
                    if estado:
                        estado = int(estado)
                        filtro &= Q(estado=estado)

                    liquidaciones = LiquidacionCompra.objects.filter(filtro)

                    tipoarchivo = request.GET.get('tipoarchivo')
                    if tipoarchivo == '1':
                        data['listado'] = liquidaciones
                        data['fechaactual'] = ahora = datetime.now()
                        data['fecha_desde'] = d_fecha_desde
                        data['fecha_hasta'] = d_fecha_hasta
                        data['report_title'] = report_title
                        time_codigo = ahora.strftime('%Y%m%d_%H%M%S')
                        data['name_file'] = name_file = f'reporte_liquidaciones_compras_{time_codigo}.pdf'
                        template_ = 'adm_liquidacioncompras/liquidacioncompras_pdf.html'
                        data['pagesize'] = 'A4'
                        return conviert_html_to_pdf(template_, data)

                    if tipoarchivo == '2':
                        __author__ = 'Unemi'
                        ahora = datetime.now()
                        time_codigo = ahora.strftime('%Y%m%d_%H%M%S')
                        name_file = f'reporte_excel_liquidaciones_compras_{time_codigo}.xlsx'
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
                            ('N°', 40),
                            ('Fecha', 40),
                            ('Hora', 40),
                            ('Proveedor', 50),
                            ('Identificación', 20),
                            ('Subtotal 0', 10),
                            ('Subtotal IVA', 10),
                            ('Iva', 10),
                            ('Descuento', 10),
                            ('Total', 10),
                            ('Pag.', 10),
                            ('XML.', 10),
                            ('Fir.', 10),
                            ('SRI.', 10),
                            ('Aut.', 10),
                            ('Estado.', 15),
                        ]

                        ws.merge_range(0, 0, 0, columnas.__len__() - 1, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', fuenteencabezado)
                        ws.merge_range(1, 0, 1, columnas.__len__() - 1, report_title, fuenteencabezado)
                        row_num, numcolum = 2, 0

                        for col_name in columnas:
                            ws.write(row_num, numcolum, col_name[0], fuentecabecera)
                            ws.set_column(numcolum, numcolum, col_name[1])
                            numcolum += 1

                        row_num += 1

                        for liquidacion in liquidaciones:
                            ws.write(row_num, 0, liquidacion.numerocompleto, formatoceldacenter)
                            ws.write_datetime(row_num, 1, liquidacion.fecha, formatoceldafecha)#.strftime('%d/%m/%Y')
                            ws.write_datetime(row_num, 2, liquidacion.fecha_creacion, formatoceldafecha)#.strftime('%d/%m/%Y')
                            ws.write(row_num, 3, liquidacion.proveedor.nombre, formatoceldacenter)
                            ws.write(row_num, 4, liquidacion.proveedor.identificacion, formatoceldacenter)
                            ws.write(row_num, 5, liquidacion.subtotal_base0, formatoceldacenter)
                            ws.write(row_num, 6, liquidacion.subtotal_base_iva, formatoceldacenter)
                            ws.write(row_num, 7, liquidacion.total_iva, formatoceldacenter)
                            ws.write(row_num, 8, liquidacion.total_descuento, formatoceldacenter)
                            ws.write(row_num, 9, liquidacion.total, formatoceldacenter)
                            ws.write(row_num, 10, 'SI' if liquidacion.pagada else 'No', formatoceldacenter)
                            ws.write(row_num, 11, 'SI' if liquidacion.xmlgenerado else 'No', formatoceldacenter)
                            ws.write(row_num, 12, 'SI' if liquidacion.firmada else 'No', formatoceldacenter)
                            ws.write(row_num, 13, 'SI' if liquidacion.enviadasri else 'No', formatoceldacenter)
                            ws.write(row_num, 14, 'SI' if liquidacion.autorizada else 'No', formatoceldacenter)
                            ws.write(row_num, 15, liquidacion.get_estado_display(), formatoceldacenter)
                            row_num += 1
                        workbook.close()
                        output.seek(0)
                        response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                        response['Content-Disposition'] = f'attachment; filename="{name_file}"'
                        return response
                except Exception as ex:
                    pass

            if action == 'autocompleteServicio':
                try:
                    term = request.GET.get('term', '')
                    excl = json.loads(request.GET.get('excl', ''))
                    servicios = ServicioCompra.objects.filter(status=True).exclude(pk__in=excl)
                    if term:
                        servicios = servicios.filter(
                            Q(tiposervicio__descripcion__icontains=term) |
                            Q(descripcion__icontains=term)
                        )
                    listado = [serv.convertir_json() for serv in servicios]
                    return JsonResponse(listado, safe=False)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Liquidación de compras o servicios'

                url_vars = ''
                filtro = Q(status=True)
                search = None
                ids = None
                if 's' in request.GET:
                    if request.GET['s'] != '':
                        search = request.GET['s']

                if search:
                    filtro = filtro & (Q(proveedor_nombre__icontains=search) | Q(identificacion__icontains=search))
                    url_vars += '&s=' + search

                data['est'] = estado = request.GET.get('est')
                if estado:
                    data['est'] = estado = int(estado)
                    filtro &= Q(estado=estado)
                    url_vars += f'&est={estado}'

                data['fecha_desde'] = fecha_desde = request.GET.get('fecha_desde', '')
                data['fecha_hasta'] = fecha_hasta = request.GET.get('fecha_hasta', '')

                if fecha_desde and fecha_hasta:
                    d_fecha_desde = datetime.strptime(fecha_desde, '%d-%m-%Y').date()
                    d_fecha_hasta = datetime.strptime(fecha_hasta, '%d-%m-%Y').date()
                    filtro = filtro & Q(fecha__range=[d_fecha_desde, d_fecha_hasta])
                    url_vars += f'&fecha_desde={fecha_desde}&fecha_hasta={fecha_hasta}'
                elif fecha_desde:
                    d_fecha_desde = datetime.strptime(fecha_desde, '%d-%m-%Y').date()
                    filtro = filtro & Q(fecha=d_fecha_desde)
                    url_vars += f'&fecha_desde={fecha_desde}'
                elif fecha_hasta:
                    d_fecha_hasta = datetime.strptime(fecha_hasta, '%d-%m-%Y').date()
                    filtro = filtro & Q(fecha=d_fecha_hasta)
                    url_vars += f'&fecha_hasta={fecha_hasta}'

                procesos = LiquidacionCompra.objects.filter(filtro).order_by('-id')

                data['total'] = len(procesos)

                paging = MiPaginador(procesos, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session:
                        paginasesion = int(request.session['paginador'])
                    if 'page' in request.GET:
                        p = int(request.GET['page'])
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
                data['formReporteLiquidacionCompra'] = ReporteLiquidacionCompraFrom()
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data["url_vars"] = url_vars
                data['ids'] = ids if ids else ""
                data['listado'] = page.object_list
                data['estados'] = ESTADO_COMPROBANTE
                data['email_domain'] = EMAIL_DOMAIN
                data['reporte_1'] = obtener_reporte('liquidacion_compra_reporte')
                data['reporte_2'] = obtener_reporte('comprobante_retencion')
                return render(request, 'adm_liquidacioncompras/view.html', data)
            except Exception as ex:
                return HttpResponseRedirect("/")