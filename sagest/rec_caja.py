# -*- coding: UTF-8 -*-
import json
import os
from datetime import datetime
import random

import xlsxwriter
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module, last_access
from sagest.commonviews import secuencia_caja, anio_ejercicio
from sagest.forms import CierreSesionCajaForm, CajeroForm, ReporteFacturaCajeroForm
from sagest.models import LugarRecaudacion, SesionCaja, CierreSesionCaja, Factura, NotaCredito, AnioEjercicio
from settings import TESORERO_ID, MEDIA_ROOT
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import MiPaginador, log, variable_valor, null_to_decimal
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsaveqr_generico
from sga.models import Persona
from utils.filtros_genericos import filtro_persona_select


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if 'aniofiscalpresupuesto' in request.session:
        anio = request.session['aniofiscalpresupuesto']
    else:
        anio = anio_ejercicio().anioejercicio
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsesion':
            try:
                lugarrecaudacion = persona.lugar_recaudacion()

                if SesionCaja.objects.filter(caja=lugarrecaudacion, fecha=datetime.now().date()).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Ya existe un registro de Sesión de Caja para [ %s ] con fecha [ %s ]." % (lugarrecaudacion.nombre, datetime.now().date())})
                if not lugarrecaudacion:
                    return JsonResponse({"result": "bad", "mensaje": u"No existe lugar de recaudación definido para esta persona."})
                if lugarrecaudacion.esta_abierta():
                    return JsonResponse({"result": "bad", "mensaje": u"La caja se encuentra abierta."})
                secuencia = secuencia_caja(request, datetime.now().year)
                secuencia.secuenciacaja += 1
                secuencia.save(request)
                sesioncaja = SesionCaja(caja=lugarrecaudacion,
                                        fecha=datetime.now().date(),
                                        fondo=0,
                                        abierta=True,
                                        anioejercicio=anio_ejercicio(),
                                        numero=secuencia.secuenciacaja)
                sesioncaja.save(request)
                log(u'Adiciono sesion de caja: %s' % sesioncaja, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addcajero':
            try:
                form = CajeroForm(request.POST)
                if form.is_valid():
                    if not LugarRecaudacion.objects.filter(persona=form.cleaned_data['persona']).exists():
                        cajero = LugarRecaudacion(persona=form.cleaned_data['persona'],
                                                  nombre = form.cleaned_data['nombre'],
                                                  puntoventa=form.cleaned_data['puntoventa'],
                                                  activo=True)
                        cajero.save(request)

                        log(u'Adiciono cajero: %s' % cajero, request, "add")
                        return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
                    return JsonResponse({"result": True, "mensaje": "La persona ya se encuentra registrada"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"{ex}"})

        if action == 'reportefactura':
            try:
                form = ReporteFacturaCajeroForm(request.POST)
                if form.is_valid():
                    data['tesorero'] = Persona.objects.get(pk=int(variable_valor('TESORERO')))
                    tipoarchivo = int(form.cleaned_data['tipoarchivo'])
                    fecha = form.cleaned_data['fecha']
                    cajerorep = form.cleaned_data['cajero']
                    ruta = 'media/recaudaciones/'
                    data['sesioncajarep'] = sesioncajarep= SesionCaja.objects.filter(fecha=fecha,caja=cajerorep).first()
                    if sesioncajarep:
                        data['facturas'] = facturas = Factura.objects.filter(pagos__fecha=fecha, sesioncaja=sesioncajarep
                                                                             ).exclude(
                            pagos__pagocuentaporcobrar__isnull=False).exclude(
                            pagos__rubro__contratorecaudacion__isnull=False).exclude(
                            pagos__pagotransferenciadeposito__isnull=False).distinct()
                        data['valorfacturas'] = null_to_decimal(facturas.aggregate(valor=Sum('total'))['valor'])
                        data['valoranulada'] = null_to_decimal(facturas.filter(valida=False).aggregate(valor=Sum('total'))['valor'])
                        data['valorvalida'] = null_to_decimal(facturas.filter(valida=True).aggregate(valor=Sum('total'))['valor'])
                        data['totalanuladas'] = facturas.filter(valida=False).count()
                        data['totalvalidas'] = facturas.filter(valida=True).count()

                        if tipoarchivo==2:
                            __author__ = 'Unemi'
                            filename = f'reporte_facturas_{random.randint(1, 10000).__str__()}.xlsx'
                            directory = os.path.join(MEDIA_ROOT, 'recaudaciones', filename)
                            workbook = xlsxwriter.Workbook(directory, {'constant_memory': True})
                            ws = workbook.add_worksheet('paz_salvo')
                            formatosubtitulocolumna = workbook.add_format(
                                {'align': 'left', 'valign': 'vcenter', 'bold': 1, 'font_size': 12,
                                 'text_wrap': True, 'fg_color': '#ECF6FF', 'font_color': 'black'})

                            ws.set_column(0, 10, 40)
                            # Titulos
                            ws.write('A1', f'Cajero/a: {sesioncajarep.caja.persona}')
                            ws.write('A2', f'Fecha: {sesioncajarep.fecha}')
                            ws.write('A3', f'Sesión: {sesioncajarep.numero}')
                            fila = 4
                            ws.write('A' + str(fila), 'Doc. fuente', formatosubtitulocolumna)
                            ws.write('B' + str(fila), 'Fecha', formatosubtitulocolumna)
                            ws.write('C' + str(fila), 'Cedula/RUC', formatosubtitulocolumna)
                            ws.write('D' + str(fila), 'Cliente', formatosubtitulocolumna)
                            ws.write('E' + str(fila), 'Correo', formatosubtitulocolumna)
                            ws.write('F' + str(fila), 'Sub_0', formatosubtitulocolumna)
                            ws.write('G' + str(fila), 'Sub_Iva', formatosubtitulocolumna)
                            ws.write('H' + str(fila), 'IVA', formatosubtitulocolumna)
                            ws.write('I' + str(fila), 'Total', formatosubtitulocolumna)
                            ws.write('J' + str(fila), 'Estado', formatosubtitulocolumna)
                            ws.write('K' + str(fila), 'Anulado', formatosubtitulocolumna)
                            fila += 1
                            for factura in facturas:
                                ws.write('A' + str(fila), str(factura.numerocompleto))
                                ws.write('B' + str(fila), str(factura.fecha))
                                ws.write('C' + str(fila), str(factura.identificacion))
                                ws.write('D' + str(fila), factura.nombre)
                                ws.write('E' + str(fila), str(factura.email))
                                ws.write('F' + str(fila), str(factura.subtotal_base0))
                                ws.write('G' + str(fila), str(factura.subtotal_base_iva))
                                ws.write('H' + str(fila), str(factura.total_iva))
                                ws.write('I' + str(fila), str(factura.total))
                                ws.write('J' + str(fila), str(factura.get_estado_display()))
                                ws.write('K' + str(fila), 'Si' if not factura.valida else 'No')
                                fila += 1
                            workbook.close()
                            ruta = ruta + filename
                        else:
                            directory_p = os.path.join(MEDIA_ROOT, 'recaudaciones')
                            filename = f'reporte_facturas_{random.randint(1, 10000).__str__()}.pdf'
                            try:
                                os.stat(directory_p)
                            except:
                                os.mkdir(directory_p)
                            context = {'pagesize': 'A4 landscape', 'data': data}
                            valido = conviert_html_to_pdfsaveqr_generico(request,
                                                                         'rec_caja/reporte_caja.html',
                                                                         context,
                                                                         directory_p, filename)
                            if not valido[0]:
                                raise NameError('Error al generar el informe')
                            ruta = f'media/recaudaciones/{filename}'
                        return JsonResponse({'to': ruta})

                    return JsonResponse({'result': True, 'mensaje': 'No existen datos para mostrar'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"{ex}"})

        elif action == 'cerrarsesion':
            try:
                form = CierreSesionCajaForm(request.POST)
                lugarrecaudacion = LugarRecaudacion.objects.filter(persona=persona)[0]
                sesioncaja = lugarrecaudacion.sesioncaja_set.get(pk=int(request.POST['id']))
                tesorero_id = variable_valor('TESORERO')
                if not sesioncaja.abierta:
                    return JsonResponse({"result": "bad", "mensaje": u"La sesión de caja ya esta cerrada."})
                # if Factura.objects.filter(estado=1, valida=True, sesioncaja=sesioncaja).exists():
                #     return JsonResponse({"result": "bad", "mensaje": u"Existen Facturas pendientes de autorización."})
                if NotaCredito.objects.filter(estado=1, valida=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Existen Notas de Crédito pendientes de autorización."})
                if form.is_valid():
                    cs = CierreSesionCaja(sesion=sesioncaja,
                                          bill100=form.cleaned_data['bill100'],
                                          bill50=form.cleaned_data['bill50'],
                                          bill20=form.cleaned_data['bill20'],
                                          bill10=form.cleaned_data['bill10'],
                                          bill5=form.cleaned_data['bill5'],
                                          bill2=form.cleaned_data['bill2'],
                                          bill1=form.cleaned_data['bill1'],
                                          total=0,
                                          mon1=form.cleaned_data['mon1'],
                                          mon50=form.cleaned_data['mon50'],
                                          mon25=form.cleaned_data['mon25'],
                                          mon10=form.cleaned_data['mon10'],
                                          mon5=form.cleaned_data['mon5'],
                                          mon1c=form.cleaned_data['mon1c'],
                                          deposito=form.cleaned_data['deposito'],
                                          cheques=form.cleaned_data['cheques'],
                                          transfer=form.cleaned_data['transfer'],
                                          tarjeta=form.cleaned_data['tarjeta'],
                                          electronico=form.cleaned_data['electronico'],
                                          recibocaja=form.cleaned_data['recibocaja'],
                                          tesorero_id=tesorero_id,
                                          fecha=datetime.now())
                    cs.save(request)
                    sesioncaja.abierta = False
                    sesioncaja.save(request)
                    sesioncaja.generar_resumen_partida()
                    log(u'Cerro sesion en caja: %s [%s]' % (sesioncaja, sesioncaja.id), request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'modificarcierre':
            try:
                form = CierreSesionCajaForm(request.POST)
                # lugarrecaudacion = LugarRecaudacion.objects.filter(persona=persona)[0]
                if form.is_valid():
                    cs = CierreSesionCaja.objects.get(pk=int(request.POST['id']))
                    cs.bill100 = form.cleaned_data['bill100']
                    cs.bill50 = form.cleaned_data['bill50']
                    cs.bill20 = form.cleaned_data['bill20']
                    cs.bill10 = form.cleaned_data['bill10']
                    cs.bill5 = form.cleaned_data['bill5']
                    cs.bill2 = form.cleaned_data['bill2']
                    cs.bill1=form.cleaned_data['bill1']
                    cs.total = 0,
                    cs.mon1 = form.cleaned_data['mon1']
                    cs.mon50 = form.cleaned_data['mon50']
                    cs.mon25 = form.cleaned_data['mon25']
                    cs.mon10 = form.cleaned_data['mon10']
                    cs.mon5 = form.cleaned_data['mon5']
                    cs.mon1c = form.cleaned_data['mon1c']
                    cs.deposito = form.cleaned_data['deposito']
                    cs.cheques = form.cleaned_data['cheques']
                    cs.transfer = form.cleaned_data['transfer']
                    cs.tarjeta = form.cleaned_data['tarjeta']
                    cs.electronico = form.cleaned_data['electronico']
                    cs.recibocaja = form.cleaned_data['recibocaja']
                    cs.save(request)
                    cs.sesion.generar_resumen_partida()
                    log(u'Modifico cierre de caja: %s [%s]' % (cs, cs.id), request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addsesion':
                try:
                    data['title'] = u'Abrir sesión de cobranzas en caja'
                    lugarrecaudacion = LugarRecaudacion.objects.get(persona=request.session['persona'])
                    return render(request, "rec_caja/addsesion.html", data)
                except Exception as ex:
                    pass

            elif action == 'cerrarsesion':
                try:
                    data['title'] = u"Cierre de sesión de cobranzas en caja"
                    data['sesioncaja'] = sesioncaja = SesionCaja.objects.get(pk=request.GET['id'])
                    if sesioncaja.caja.persona != request.session['persona']:
                         raise NameError('Error')
                    data['form'] = CierreSesionCajaForm(initial={'tarjeta': sesioncaja.total_tarjeta_sesion(),
                                                                 'cheques': sesioncaja.total_cheque_sesion(),
                                                                 'deposito': sesioncaja.total_deposito_sesion(),
                                                                 'electronico': sesioncaja.total_electronico_sesion(),
                                                                 'transfer': sesioncaja.total_transferencia_sesion(),
                                                                 'recibocaja': sesioncaja.total_recibocaja_sesion()})
                    return render(request, "rec_caja/cerrarsesion.html", data)
                except Exception as ex:
                    pass

            if action == 'cambioperiodo':
                try:
                    anio = AnioEjercicio.objects.get(id=int(request.GET['id']))
                    request.session['aniofiscalpresupuesto'] = anio.anioejercicio
                except Exception as ex:
                    pass

            elif action == 'modificarcierre':
                try:
                    data['title'] = u"Cierre de sesión de cobranzas en caja"
                    data['sesioncaja'] = sesioncaja = SesionCaja.objects.get(pk=request.GET['id'])
                    data['cierre'] = cierre = sesioncaja.cierre_sesion()
                    initial = model_to_dict(cierre)
                    data['form'] = CierreSesionCajaForm(initial=initial)
                    return render(request, "rec_caja/modificarcierre.html", data)
                except Exception as ex:
                    pass

            if action == 'detalle_sesioncaja':
                try:
                    data['sesion'] = sesion = SesionCaja.objects.get(pk=int(request.GET['id']))
                    data['cierre'] = sesion.cierre_sesion()
                    template = get_template("rec_caja/detalle.html")
                    return JsonResponse({"result":True,"data":template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'detalle_sesioncaja_abierta':
                try:
                    data['sesion'] = sesioncaja = SesionCaja.objects.get(pk=int(request.GET['id']))
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
                    template = get_template("rec_caja/detalle_abierta.html")
                    return JsonResponse({"result":True,"data":template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'cajeros':
                try:
                    data['title'] = u'Cajeros'
                    search = None
                    cajeros = LugarRecaudacion.objects.all().order_by('-fecha_creacion')
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            cajeros = cajeros.filter(Q(persona__apellido1__icontains=search) |
                                                                 Q(persona__apellido2__icontains=search) |
                                                                 Q(persona__nombres__icontains=search)).distinct().order_by(
                                '-fecha_creacion')
                        else:
                            cajeros = cajeros.filter(Q(persona__apellido1__icontains=ss[0]) &
                                                                 Q(persona__apellido2__icontains=ss[1])).distinct().order_by(
                                '-fecha_creacion')

                    paging = MiPaginador(cajeros, 25)
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
                    data['cajeros'] = paging.object_list
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    return render(request, "rec_caja/viewcajero.html", data)
                except Exception as ex:
                    return JsonResponse({"result":"bad","mensaje":"Error al mostrar los datos"})

            if action == 'addcajero':
                try:
                    form = CajeroForm()
                    form.fields['persona'].queryset = Persona.objects.none()
                    data['form'] = form
                    template = get_template("rec_caja/modal/formcajero.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'reportefactura':
                try:
                    form = ReporteFacturaCajeroForm()
                    data['form'] = form
                    template = get_template("ajaxformmodal.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'buscarpersonas':
                try:
                    resp = filtro_persona_select(request)
                    return HttpResponse(json.dumps({'status': True, 'results': resp}))
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Registro de sesiones de cobranza en caja'
                ids = None
                search = None
                data['mianio'] = anio
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        sesiones = SesionCaja.objects.filter(Q(caja__persona__apellido1__icontains=search) |
                                                             Q(caja__persona__apellido2__icontains=search) |
                                                             Q(caja__persona__nombres__icontains=search), anioejercicio__anioejercicio=anio).distinct().order_by('-fecha')
                    else:
                        sesiones = SesionCaja.objects.filter(Q(caja__persona__apellido1__icontains=ss[0]) &
                                                             Q(caja__persona__apellido2__icontains=ss[1]), anioejercicio__anioejercicio=anio).distinct().order_by('-fecha')

                elif 'id' in request.GET:
                    ids = request.GET['id']
                    sesiones = SesionCaja.objects.filter(id=ids, anioejercicio__anioejercicio=anio).order_by('-fecha')
                else:
                    sesiones = SesionCaja.objects.filter(anioejercicio__anioejercicio=anio).order_by('-fecha')
                paging = MiPaginador(sesiones, 25)
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
                if LugarRecaudacion.objects.filter(persona=request.session['persona'], puntoventa__activo=True,activo=True).exists():
                    data['caja'] = LugarRecaudacion.objects.filter(persona=request.session['persona'], puntoventa__activo=True,activo=True)[0]
                data['rangospaging'] = paging.rangos_paginado(p)
                data['ids'] = ids if ids else None
                data['page'] = page
                data['sesiones'] = page.object_list
                data['reporte_0'] = obtener_reporte('cierre_sesion_caja')
                data['reporte_1'] = obtener_reporte('resumen_tipo_rubro')
                data['reporte_2'] = obtener_reporte('resumen_recibo_caja')
                data['reporte_3'] = obtener_reporte('resumen_rubro_arriendos')
                data['reporte_7'] = obtener_reporte('resumen_rubro_bancos')
                data['reporte_4'] = obtener_reporte('total_recaudado')
                data['reporte_5'] = obtener_reporte('total_dep_tercero')
                data['reporte_6'] = obtener_reporte('total_rec_banco')
                data['reporte_8'] = obtener_reporte('resumen_tipo_rubro_todo')
                data['anios'] = AnioEjercicio.objects.all()
                data['anioejercicio'] = anio_ejercicio().anioejercicio
                data['search'] = search if search else ""
                data['fecha'] = hoy = datetime.now().date()
                data['NOMBRE_CERTIFICADO'] = variable_valor('NOMBRE_CERTIFICADO')
                data['FECHA_CADUCIDAD_CERTIFICADO'] = fecha = variable_valor('FECHA_CADUCIDAD_CERTIFICADO')
                x = fecha - hoy
                data['dias'] = x.days
                return render(request, "rec_caja/view.html", data)
            except Exception as ex:
                pass