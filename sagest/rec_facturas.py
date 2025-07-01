# -*- coding: UTF-8 -*-
import os
from datetime import datetime
import xlwt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template
from django.forms.models import model_to_dict

from decorators import secure_module, last_access
from sagest.commonviews import secuencia_recaudacion, Sum
from sagest.rec_finanzas import crear_representacion_xml_factura, firmar_comprobante_factura, envio_comprobante_sri_factura, \
    autorizacion_comprobante_factura, envio_comprobante_cliente_factura
from sagest.rec_notacredito import crear_representacion_xml_notacredito
from settings import MODELO_IMPRESION_NUEVO, TIPO_AMBIENTE_FACTURACION, SITE_ROOT
from sga.commonviews import adduserdata, obtener_reporte, traerNotificaciones
from sagest.forms import FacturaCanceladaForm, MoverFacturaForm, CorreoFacturaForm, FacturaCorreccionForm
from sga.excelbackground import reporte_generar_csv_facturas_esigef_background
from sga.funciones import MiPaginador, log, convertir_fecha, generar_nombre,variable_valor
from sagest.models import Factura, NotaCredito, DetalleNotaCredito, ClienteFactura
from sga.models import miinstitucion, Notificacion
from datetime import date, timedelta


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

        if action == 'generarnota':
            try:
                factura = Factura.objects.get(pk=request.POST['id'])
                if factura.autorizada and not factura.notacredito_set.exists():
                    sesion_caja = factura.sesioncaja
                    secuencia = secuencia_recaudacion(request, sesion_caja.caja.puntoventa, 'notacredito')
                    # if secuencia.notacredito > 0:
                    #     secuencia.notacredito += 1
                    # else:
                    #     secuencia.notacredito = 1
                    # secuencia.save(request)
                    notacredito = NotaCredito(puntoventa=factura.puntoventa,
                                              numerocompleto=factura.puntoventa.establecimiento.strip() + "-" + factura.puntoventa.puntoventa.strip() + "-" + str(secuencia).zfill(9),
                                              motivo=factura.datos_anulacion().motivo,
                                              numero=secuencia,
                                              fecha=datetime.now().date(),
                                              factura=factura,
                                              valida=True,
                                              electronica=True,
                                              cliente=factura.cliente,
                                              impresa=False,
                                              sesioncaja=sesion_caja,
                                              identificacion=factura.identificacion,
                                              tipo=factura.tipo,
                                              nombre=factura.nombre,
                                              direccion=factura.direccion,
                                              telefono=factura.telefono,
                                              email=factura.email,
                                              ivaaplicado=factura.ivaaplicado,
                                              subtotal_base_iva=factura.subtotal_base_iva,
                                              subtotal_base0=factura.subtotal_base0,
                                              total_descuento=factura.total_descuento,
                                              total_iva=factura.total_iva,
                                              total=factura.total,
                                              tipoemision=factura.tipoemision,
                                              tipoambiente=TIPO_AMBIENTE_FACTURACION)
                    notacredito.save(request)
                    for pago in factura.pagos.all():
                        detalle = DetalleNotaCredito(sesion=factura.sesioncaja,
                                                     nombre=pago.rubro.nombre,
                                                     cantidad=1,
                                                     subtotal0=pago.subtotal0,
                                                     subtotaliva=pago.subtotaliva,
                                                     iva=pago.iva,
                                                     ivaaplicado=pago.rubro.iva,
                                                     valordescuento=pago.valordescuento,
                                                     valortotal=pago.valortotal)
                        detalle.save(request)
                        notacredito.detalle.add(detalle)
                    notacredito.claveacceso = notacredito.genera_clave_acceso_notacredito()
                    notacredito.save(request)
                    crear_representacion_xml_notacredito(notacredito.id)
                log(u'Creó nota de credito: %s' % factura, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'arreglarfactura':
            try:
                Factura.objects.filter(pk=request.POST['id']).update(enviadacliente=False, xml=None, xmlfirmado=None,firmada=False,enviadasri=False,autorizada=False,xmlgenerado=False, mensajeautorizacion=None,falloautorizacionsri=False,xmlarchivo=None,falloenviodasri=False,mensajeenvio=None)
                log(u'Arreglo Factura id: %s' % request.POST['id'], request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'mover':
            try:
                factura = Factura.objects.get(pk=request.POST['id'])
                f = MoverFacturaForm(request.POST)
                if f.is_valid():
                    sesion = f.cleaned_data['sesion']
                    pagos = factura.pagos.all()
                    factura.sesioncaja = sesion
                    factura.fecha = sesion.fecha
                    factura.save(request)
                    for pa in pagos:
                        pa.sesion = sesion
                        pa.fecha = sesion.fecha
                        pa.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'generar_xml':
            try:
                book = xlwt.Workbook()
                fechai = convertir_fecha(request.POST['fechai'])
                fechaf = convertir_fecha(request.POST['fechaf'])
                facturas = Factura.objects.filter(fecha__gte=fechai, fecha__lte=fechaf)
                total_ventas = facturas.aggregate(valor=Sum('total'))['valor']
                template = get_template("xml/facturas.html")
                d = Context({'comprobantes': facturas,
                             'institucion': miinstitucion(),
                             'total_ventas': total_ventas})
                xml_content = template.render(d)
                direccion = os.path.join(SITE_ROOT, 'media', 'comprobantes')
                archivoname = generar_nombre('Facturas_Generadas', 'fichero.txt')
                filename = os.path.join(direccion, archivoname)
                f = open(filename, "wb")
                f.write(xml_content)
                f.close()
                return JsonResponse({"result": "ok", 'archivo': '/media/comprobantes/%s' % archivoname})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'detalle_factura':
            try:
                data['comprobante'] = factura = Factura.objects.get(pk=int(request.POST['id']))
                data['institucion'] = miinstitucion()
                data['pagos'] = factura.pagos.all()
                template = get_template("rec_facturas/detalle_factura.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'editcorreo':
            try:
                f = CorreoFacturaForm(request.POST)
                if f.is_valid():
                    factura = Factura.objects.get(pk=int(request.POST['id']))
                    factura.email = f.cleaned_data['email']
                    factura.save(request)
                    clientefactura = factura.cliente.clientefactura_set.filter(status=True)[0]
                    clientefactura.email = f.cleaned_data['email']
                    clientefactura.save(request)
                    log(u'Modifico correo en factura: %s' % factura, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'editfacturacorreccion':
            try:
                f = FacturaCorreccionForm(request.POST)
                if f.is_valid():
                    factura = Factura.objects.get(pk=int(request.POST['id']))
                    factura.email = f.cleaned_data['email']
                    factura.tipo = f.cleaned_data['tipo']
                    factura.identificacion = f.cleaned_data['identificacion']
                    factura.save(request)
                    clientefactura = factura.cliente.clientefactura_set.filter(status=True)[0]
                    clientefactura.email = f.cleaned_data['email']
                    clientefactura.tipo = f.cleaned_data['tipo']
                    clientefactura.identificacion = f.cleaned_data['identificacion']
                    clientefactura.save(request)
                    log(u'Modifico datos en factura: %s' % factura, request, "edit")
                    return JsonResponse({'result': 'ok'})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        elif action == 'arreglar':
            try:
                facturas = Factura.objects.filter(status=True, valida=True, enviadacliente=False, autorizada=False, fecha_creacion__lt=datetime.now().date()).order_by('-fecha', '-numero')
                for f in facturas:
                    f.firmada=False
                    f.enviadasri=False
                    f.falloautorizacionsri=False
                    f.mensajeautorizacion=None
                    f.xmlgenerado=False
                    f.xml=None
                    f.xmlfirmado=None
                    f.autorizada=False
                    f.estado=1
                    f.save()
                log(u'Arreglo facturas con errores' , request, "edit")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'anular':
                try:
                    data['title'] = u'Anular Factura'
                    data['factura'] = factura = Factura.objects.get(pk=request.GET['id'])
                    data['form'] = FacturaCanceladaForm()
                    return render(request, "rec_facturas/anular.html", data)
                except Exception as ex:
                    pass

            if action == 'generarnota':
                try:
                    data['title'] = u'Generar Nota de Crédito'
                    data['factura'] = factura = Factura.objects.get(pk=request.GET['id'])
                    return render(request, "rec_facturas/generarnota.html", data)
                except Exception as ex:
                    pass

            if action == 'arreglarfactura':
                try:
                    data['title'] = u'Arreglar Factura'
                    data['factura'] = factura = Factura.objects.get(pk=request.GET['id'])
                    return render(request, "rec_facturas/arreglarfactura.html", data)
                except Exception as ex:
                    pass

            if action == 'generarxml':
                try:
                    factura = Factura.objects.get(pk=request.GET['id'])
                    crear_representacion_xml_factura(factura.id)
                except Exception as ex:
                    pass

            if action == 'firmar':
                try:
                    factura = Factura.objects.get(pk=request.GET['id'])
                    firmar_comprobante_factura(factura.id)
                except Exception as ex:
                        pass

            if action == 'enviosri':
                try:
                    factura = Factura.objects.get(pk=request.GET['id'])
                    envio_comprobante_sri_factura(factura.id)
                except Exception as ex:
                    pass

            if action == 'enviarcliente':
                try:
                    factura = Factura.objects.get(pk=request.GET['id'])
                    envio_comprobante_cliente_factura(factura.id)
                except Exception as ex:
                    pass

            if action == 'autorizar':
                try:
                    factura = Factura.objects.get(pk=request.GET['id'])
                    autorizacion_comprobante_factura(factura.id)
                except Exception as ex:
                    pass

            if action == 'mover':
                try:
                    data['factura'] = factura = Factura.objects.get(pk=request.GET['id'])
                    data['title'] = u'Mover Factura'
                    form = MoverFacturaForm()
                    form.fechainicio(factura)
                    data['form'] = form
                    return render(request, "rec_facturas/mover.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcorreo':
                try:
                    data['title'] = u'Editar Correo de cliente'
                    data['factura'] = factura = Factura.objects.get(pk=request.GET['id'])
                    form = CorreoFacturaForm(initial={'email':factura.email})
                    data['form'] = form
                    return render(request, "rec_facturas/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'listapagos':
                try:
                    data['factura'] = factura = Factura.objects.get(pk=request.GET['id'])
                    data['title'] = u'Pagos de la cuenta por cobrar '
                    data['cuenta'] = cuenta = factura.cuenta_por_cobrar()
                    data['cancelaciones'] = None
                    return render(request, "rec_facturas/pagos.html", data)
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

            elif action == 'verfacturas':
                try:
                    data['title'] = u'Facturas con inconvenientes'
                    search = None
                    ids = None
                    a = None
                    if 'id' in request.GET:
                        ids = int(request.GET['id'])
                        facturas = Factura.objects.filter(id=ids, valida=True, enviadacliente=False, autorizada=False)
                    elif 's' in request.GET:
                        search = request.GET['s']
                        facturas = Factura.objects.filter(Q(numero__icontains=search) |
                                                          Q(total__icontains=search) |
                                                          Q(nombre__icontains=search) |
                                                          Q(identificacion__icontains=search) |
                                                          Q(
                                                              puntoventa__puntoventa__contains=search), valida=True, enviadacliente=False, autorizada=False, fecha_creacion__lt=datetime.now().date()).distinct().order_by(
                            '-fecha', '-numero')
                    elif 'a' in request.GET:
                        a = int(request.GET['a'])
                        if a == 1:
                            facturas = Factura.objects.filter(status=True, valida=True, enviadacliente=False, autorizada=False, fecha_creacion__lt=datetime.now().date()).order_by('-fecha', '-numero')
                        elif a == 2:
                            facturas = Factura.objects.filter(status=True, valida=True, enviadacliente=False, autorizada=False, fecha_creacion__lt=datetime.now().date()).order_by('-fecha', '-numero')
                    else:
                        facturas = Factura.objects.filter(status=True, valida=True, enviadacliente=False, autorizada=False, fecha_creacion__lt=datetime.now().date()).order_by('-fecha', '-numero')
                    paging = MiPaginador(facturas, 25)
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
                    data['a'] = a if a else ""
                    data['ids'] = ids if ids else ""
                    data['modelo_impresion_nuevo'] = MODELO_IMPRESION_NUEVO
                    data['facturas'] = page.object_list
                    data['reporte_0'] = obtener_reporte('comprobante_entrega_factura')
                    data['reporte_1'] = obtener_reporte('factura_reporte')
                    persona = request.session['persona']
                    data['puede_pagar'] = persona.puede_recibir_pagos()
                    data['fecha'] = hoy = datetime.now().date()
                    data['NOMBRE_CERTIFICADO'] = variable_valor('NOMBRE_CERTIFICADO')
                    data['FECHA_CADUCIDAD_CERTIFICADO'] = fecha = variable_valor('FECHA_CADUCIDAD_CERTIFICADO')
                    x = fecha - hoy
                    data['dias'] = x.days
                    return render(request, "rec_facturas/verfacturas.html", data)
                except Exception as ex:
                    pass

            elif action == 'editfacturacorreccion':
                try:
                    data['title'] = u'Editar datos factura'
                    data['factura'] = factura = Factura.objects.get(pk=int(request.GET['id']))
                    initial = model_to_dict(factura)
                    form = FacturaCorreccionForm(initial=initial)
                    data['form'] = form
                    return render(request, "rec_facturas/editfacturacorreccion.html", data)
                except Exception as ex:
                    pass

            elif action == 'generar_csv_facturas_esigef':
                try:
                    # Se considerarán las facturas a partir de Agosto 2023
                    if 'tiporeporte' not in request.GET or 'fechadesde' not in request.GET or 'fechahasta' not in request.GET:
                        return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                    tiporeporte = int(request.GET['tiporeporte'])
                    fechadesde = datetime.strptime(request.GET['fechadesde'], '%d-%m-%Y').date()
                    fechahasta = datetime.strptime(request.GET['fechahasta'], '%d-%m-%Y').date()

                    # Verificar si existen registros de facturas pendientes de generar CSV
                    if tiporeporte == 1:
                        if not Factura.objects.values("id").filter(status=True, fecha__gte=datetime.strptime('2023-08-01', "%Y-%m-%d").date(), enviadacliente=True, archivofacturaesigefdetalle__isnull=True).exists():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No existen Registros de Facturas pendientes de generar el archivo CSV - eSIGEF", "showSwal": "True", "swalType": "warning"})
                    else:
                        if not Factura.objects.values("id").filter(status=True, fecha__range = [fechadesde, fechahasta], enviadacliente=True, archivofacturaesigefdetalle__isnull=True).exists():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No existen Registros de Facturas pendientes de generar el archivo CSV - eSIGEF en ese rango de fechas", "showSwal": "True", "swalType": "warning"})

                    # Guardar la notificación
                    notificacion = Notificacion(
                        cuerpo='Generación de reporte csv en progreso',
                        titulo='Reporte CSV Facturas Emitidas para subir al eSIGEF',
                        destinatario=persona,
                        url='',
                        prioridad=1,
                        app_label='SGA',
                        fecha_hora_visible=datetime.now() + timedelta(days=1),
                        tipo=2,
                        en_proceso=True
                    )
                    notificacion.save(request)

                    reporte_generar_csv_facturas_esigef_background(request=request, data=data, idnotificacion=notificacion.id, tiporeporte=tiporeporte, fechadesde=fechadesde, fechahasta=fechahasta).start()

                    return JsonResponse({"result": "ok",
                                         "mensaje": u"El reporte se está generando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    print("error")
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar el reporte. [%s]" % msg})


            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Facturas'
                url_vars = ''
                filtro = Q()
                fecha_desde = request.GET.get('fecha_desde', '')
                fecha_hasta = request.GET.get('fecha_hasta', '')
                search = request.GET.get('s', '')
                estado = request.GET.get('estado', '')

                # search = None
                ids = None
                if 'id' in request.GET:
                    ids = int(request.GET['id'])
                    facturas = Factura.objects.filter(id=ids)
                else:
                    if search:
                        # search = request.GET['s']
                        # facturas = Factura.objects.filter(Q(numero__icontains=search) |
                        #                                   Q(total__icontains=search) |
                        #                                   Q(nombre__icontains=search) |
                        #                                   Q(identificacion__icontains=search) |
                        #                                   Q(puntoventa__puntoventa__contains=search)).distinct().order_by('-fecha', '-numero')
                        filtro = filtro & (Q(numero__icontains=search) |
                                            Q(total__icontains=search) |
                                            Q(nombre__icontains=search) |
                                            Q(identificacion__icontains=search) |
                                            Q(puntoventa__puntoventa__contains=search))
                        url_vars += f'&s={search}'

                    if fecha_desde:
                        filtro = filtro & Q(fecha__gte=fecha_desde)
                        data['fecha_desde'] = fecha_desde
                        url_vars += f'&fecha_desde={fecha_desde}'

                    if fecha_hasta:
                        filtro = filtro & Q(fecha__lte=fecha_hasta)
                        data['fecha_hasta'] = fecha_hasta
                        url_vars += f'&fecha_hasta={fecha_hasta}'

                    if estado:
                        estado = int(request.GET['estado'])
                        if estado == 1:
                            filtro = filtro & Q(enviadacliente=True)
                        elif estado == 2:
                            filtro = filtro & Q(enviadacliente=False)
                        data['estado'] = estado
                        url_vars += f'&estado={estado}'

                    facturas = Factura.objects.filter(filtro).order_by('-fecha', '-numero')

                if 'export_excel' in request.GET:
                    #Bloque para generar exel segun lo filtrado
                    if facturas.count() < 65000:
                        resp = generar_excel(facturas)
                        if resp == 1: pass
                        else: return resp

                paging = MiPaginador(facturas, 25)
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
                data['facturas'] = page.object_list
                # data['reporte_0'] = obtener_reporte('comprobante_entrega_factura')
                data['reporte_0'] = obtener_reporte('comprobante_entrega_factura_membrete')
                data['reporte_1'] = obtener_reporte('factura_reporte')
                persona = request.session['persona']
                data['puede_pagar'] = persona.puede_recibir_pagos()
                data['fecha'] = hoy = datetime.now().date()
                data['NOMBRE_CERTIFICADO'] = variable_valor('NOMBRE_CERTIFICADO')
                data['FECHA_CADUCIDAD_CERTIFICADO'] = fecha = variable_valor('FECHA_CADUCIDAD_CERTIFICADO')
                x = fecha - hoy
                data['dias'] = x.days
                data['url_vars'] = url_vars
                return render(request, "rec_facturas/view.html", data)
            except Exception as ex:
                pass


def generar_excel(query):
    try:
        from xlwt import easyxf,XFStyle,Workbook
        from django.shortcuts import HttpResponse
        import random
        __author__ = 'Unemi'
        title = easyxf(
            'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
        font_style = XFStyle()
        font_style.font.bold = True
        font_style2 = XFStyle()
        font_style2.font.bold = False
        wb = Workbook(encoding='utf-8')
        ws = wb.add_sheet('reporte')
        ws.write_merge(0, 0, 0, 5, 'REPORTE DE FACTURAS', title)
        response = HttpResponse(content_type="application/ms-excel")
        response['Content-Disposition'] = 'attachment; filename=listado_facturas' + random.randint(1,
                                                                                                             10000).__str__() + '.xls'
        columns = [
            (u"N°", 8000),
            (u"FECHA", 4000),
            (u"CLIENTE", 9000),
            (u"TIPO. IDENT.", 4000),
            (u"IDENT.", 4000),
            (u"SUBT.0", 2500),
            (u"SUBT.IVA", 2500),
            (u"IVA.", 2500),
            (u"DESC.", 2500),
            (u"TOTAL.", 2500),
            (u"PAG.", 1000),
            (u"XML.", 1500),
            (u"FIR.", 1500),
            (u"SRI.", 1500),
            (u"AUT.", 1500),
            (u"ENV.", 1500),
            (u"ANL", 1500),

        ]
        row_num = 1
        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num][0], font_style)
            ws.col(col_num).width = columns[col_num][1]
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'yyyy/mm/dd'
        media = 'https://sga.unemi.edu.ec/media/'
        row_num = 2

        for index, factura in enumerate(query):
            #factura functions
            tipo_ident = factura.tipo_identificacion()
            enviosri_estado = ''
            if factura.enviadasri:
                if factura.falloenviodasri:
                    enviosri_estado = 'ERROR'
                else: enviosri_estado = 'SI'
            facaut_estado = ''
            if factura.autorizada:
                if factura.falloautorizacionsri:
                    facaut_estado = 'ERROR AUT.'
                else:
                    facaut_estado = 'SI'

            ws.write(row_num, 0,factura.numerocompleto if factura.numerocompleto else '', font_style2)
            ws.write(row_num, 1, factura.fecha.strftime('%Y-%m-%d') if factura.fecha else '', font_style2)
            ws.write(row_num, 2, factura.cliente.nombre_completo_inverso() if factura.cliente else '', font_style2)
            ws.write(row_num, 3, tipo_ident if tipo_ident else '', font_style2)
            ws.write(row_num, 4, factura.identificacion, font_style2)
            ws.write(row_num, 5, factura.subtotal_base0, font_style2)
            ws.write(row_num, 6, factura.subtotal_base_iva, font_style2)
            ws.write(row_num, 7, factura.total_iva , font_style2)
            ws.write(row_num, 8, factura.total_descuento, font_style2)
            ws.write(row_num, 9, factura.total, font_style2)
            ws.write(row_num, 10, "SI" if factura.pagada else '', font_style2)
            ws.write(row_num, 11, "SI" if factura.xmlgenerado else '', font_style2)
            ws.write(row_num, 12, "SI" if factura.firmada else '', font_style2)
            ws.write(row_num, 13, enviosri_estado, font_style2)
            ws.write(row_num, 14, facaut_estado, font_style2)
            ws.write(row_num, 15, 'SI' if factura.enviadacliente else '', font_style2)
            ws.write(row_num, 16, 'SI' if not factura.valida else '', font_style2)
            row_num += 1
        wb.save(response)
        return response
    except Exception as ex:
        return 1
