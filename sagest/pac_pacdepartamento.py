# -*- coding: UTF-8 -*-
import random

import xlrd
import xlwt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template

from decorators import secure_module
from sagest.forms import PacForm, ImportarArchivoForm, BienesServiciosInsumosPacForm
from sagest.models import PeriodoPac, Pac, ObjetivoOperativo, AccionDocumento, IndicadorPoa, datetime, \
    TopePeriodoPac, null_to_numeric, NominaPac, BienesServiciosInsumosPac
from settings import IVA, ARCHIVO_TIPO_GENERAL
from sga.commonviews import adduserdata
from sga.funciones import log, MiPaginador, null_to_decimal, generar_nombre
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import Archivo


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    departamento = persona.mi_cargo_activo().unidadorganica
    if not departamento:
        return HttpResponseRedirect("/?info=No tiene asignado ningun departamento para acceder al modulo.")
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addpacdepartamento':
            try:
                if Pac.objects.filter(periodo_id=int(request.POST['idperiodo']), departamento=departamento, caracteristicas_id=int(request.POST['caracteristicas']), status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                if TopePeriodoPac.objects.filter(periodo_id=int(request.POST['idperiodo']), status=True, departamento=departamento, estadotope=True).exists():
                    topeperiodopac = TopePeriodoPac.objects.filter(periodo_id=int(request.POST['idperiodo']), status=True, departamento=departamento, estadotope=True)[0]
                    sumatoria = float(request.POST['total'])
                    if Pac.objects.filter(periodo_id=int(request.POST['idperiodo']), departamento=departamento, status=True).exists():
                        sumatoria = float(Pac.objects.filter(periodo_id=int(request.POST['idperiodo']), departamento=departamento, status=True).aggregate(total=Sum('total'))['total'])+float(request.POST['total'])
                    if sumatoria > topeperiodopac.valor:
                        return JsonResponse({"result": "bad", "mensaje": "El Total de su PROFORMA PRESUPUESTARIA sobrepaso el limite de lo configurado."})
                # catalogobien = CatalogoBien.objects.filter(pk=int(request.POST['caracteristicas']), status=True)[0]
                pac = Pac(periodo_id=int(request.POST['idperiodo']),
                          departamento=departamento,
                          # acciondocumento_id=int(request.POST['acciondocumento']),
                          caracteristicas_id=int(request.POST['caracteristicas']),
                          cantidadenero=int(request.POST['cantidadenero']),
                          cantidadfebrero=int(request.POST['cantidadfebrero']),
                          cantidadmarzo=int(request.POST['cantidadmarzo']),
                          cantidadabril=int(request.POST['cantidadabril']),
                          cantidadmayo=int(request.POST['cantidadmayo']),
                          cantidadjunio=int(request.POST['cantidadjunio']),
                          cantidadjulio=int(request.POST['cantidadjulio']),
                          cantidadagosto=int(request.POST['cantidadagosto']),
                          cantidadseptiembre=int(request.POST['cantidadseptiembre']),
                          cantidadoctubre=int(request.POST['cantidadoctubre']),
                          cantidadnoviembre=int(request.POST['cantidadnoviembre']),
                          cantidaddiciembre=int(request.POST['cantidaddiciembre']),
                          unidadmedida_id=int(request.POST['unidadmedida']),
                          costounitario=null_to_decimal(request.POST['costounitario'],2),
                          iva=null_to_decimal(request.POST['iva'],2),
                          subtotal=null_to_decimal(request.POST['subtotal'],2),
                          total=null_to_decimal(request.POST['total'],2),
                          saldo=null_to_decimal(request.POST['total'],2),
                          item=None,
                          fechaejecucion=None)
                pac.save(request)
                log(u'Registro nuevo caracteristicas productos : %s' % pac, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'addpacbienes':
            try:
                if BienesServiciosInsumosPac.objects.filter(descripcion=request.POST['descripcion'], tipo=request.POST['tipo'],status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                bienesserviciosinsumospac = BienesServiciosInsumosPac(descripcion=request.POST['descripcion'],
                                                                      tipo=request.POST['tipo'])
                bienesserviciosinsumospac.save(request)
                log(u'Registro nuevo Bienes Servicios Insumos : %s' % bienesserviciosinsumospac, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'editpacdepartamento':
            try:
                pac = Pac.objects.get(pk=int(request.POST['idpac']), status=True)
                periodopac = pac.periodo
                if TopePeriodoPac.objects.filter(periodo=periodopac, status=True, departamento=departamento, estadotope=True).exists():
                    topeperiodopac = TopePeriodoPac.objects.filter(periodo=periodopac, status=True, departamento=departamento, estadotope=True)[0]
                    if Pac.objects.filter(periodo=periodopac, departamento=departamento, status=True).exclude(pk=int(request.POST['idpac'])).exists():
                        sumatoria = float(Pac.objects.filter(periodo=periodopac, departamento=departamento, status=True).exclude(pk=int(request.POST['idpac'])).aggregate(total=Sum('total'))['total']) + float(request.POST['total'])
                    else:
                        sumatoria = float(request.POST['total'])
                    if sumatoria > topeperiodopac.valor:
                        return JsonResponse({"result": "bad", "mensaje": "El Total de su PROFORMA PRESUPUESTARIA sobrepaso el limite de lo configurado."})
                pac.cantidadenero=int(request.POST['cantidadenero'])
                pac.cantidadfebrero=int(request.POST['cantidadfebrero'])
                pac.cantidadmarzo=int(request.POST['cantidadmarzo'])
                pac.cantidadabril=int(request.POST['cantidadabril'])
                pac.cantidadmayo=int(request.POST['cantidadmayo'])
                pac.cantidadjunio=int(request.POST['cantidadjunio'])
                pac.cantidadjulio=int(request.POST['cantidadjulio'])
                pac.cantidadagosto=int(request.POST['cantidadagosto'])
                pac.cantidadseptiembre=int(request.POST['cantidadseptiembre'])
                pac.cantidadoctubre=int(request.POST['cantidadoctubre'])
                pac.cantidadnoviembre=int(request.POST['cantidadnoviembre'])
                pac.cantidaddiciembre=int(request.POST['cantidaddiciembre'])
                pac.unidadmedida_id=int(request.POST['unidadmedida'])
                pac.costounitario=request.POST['costounitario']
                pac.iva=request.POST['iva']
                pac.total=request.POST['total']
                pac.subtotal=request.POST['subtotal']
                pac.saldo=request.POST['total']
                # pac.fechaejecucion=convertir_fecha(request.POST['fechaejecucion'])
                pac.save(request)
                log(u'Registro modificado caracteristicas productos PROFORMA PRESUPUESTARIA: %s' % pac, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al editar los datos."})

        if action == 'deletepac':
            try:
                pac = Pac.objects.get(pk=request.POST['id'], status=True)
                pac.status=False
                pac.save(request)
                log(u'Elimino caracteristicas productos PROFORMA PRESUPUESTARIA: %s' % pac, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'segmento':
            try:
                # data['acciondocumento'] = acciondocumento = AccionDocumento.objects.get(pk=int(request.POST['acciondocumento']), status=True)
                data['acciondocumento'] = acciondocumento = None
                data['periodopac'] = periodopac = PeriodoPac.objects.filter(pk=request.POST['periodo'], status=True)[0]
                data['pac'] = pac = Pac.objects.filter(periodo=periodopac ,departamento=departamento, acciondocumento=acciondocumento, status=True, estado__in=[1,2]).order_by('caracteristicas')
                data['permiso']= periodopac.permisoinicio <= datetime.now().date() <= periodopac.permisofin
                data['total_pac'] = null_to_numeric(Pac.objects.filter(departamento=departamento, status=True).aggregate(total=Sum('total'))['total'])
                template = get_template("pac_pacdepartamento/segmento.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'importar':
            try:
                form = ImportarArchivoForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not (ext == '.xlsx' or ext == '.xls'):
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .xlsx, .xls"})
                        if newfile.size > 12582912:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                if form.is_valid():
                    periodopac = PeriodoPac.objects.filter(pk=request.POST['id'], status=True)[0]
                    NominaPac.objects.filter(periodopac=periodopac).delete()
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("subirpacnomina_", nfile._name)
                    archivo = Archivo(nombre='SUBIR PROFORMA PRESUPUESTARIA MODIFICACION PRESUPUESTO',
                                      fecha=datetime.now().date(),
                                      archivo=nfile,
                                      tipo_id=ARCHIVO_TIPO_GENERAL)
                    archivo.save(request)
                    workbook = xlrd.open_workbook(archivo.archivo.file.name)
                    sheet = workbook.sheet_by_index(0)
                    linea = 1
                    for rowx in range(sheet.nrows):
                        if linea > 6:
                            cols = sheet.row_values(rowx)
                            nominapac = NominaPac(periodopac = periodopac,
                                                  programa = str(cols[0]),
                                                  subprograma = str(cols[1]),
                                                  proyecto = str(cols[2]),
                                                  actividad = str(cols[3]),
                                                  funcion = str(cols[4]),
                                                  geografico = str(cols[5]),
                                                  fuente = str(cols[6]),
                                                  organismo = str(cols[7]),
                                                  correlativo = str(cols[8]),
                                                  item = str(cols[9]),
                                                  descripcion_item = str(cols[10]),
                                                  regimen_laboral = str(cols[11]),
                                                  rmu = str(cols[12]),
                                                  estado = str(cols[13]),
                                                  desde = str(cols[14]),
                                                  hasta = str(cols[15]),
                                                  unidad_organizacional = str(cols[16]),
                                                  cedula = str(cols[17]),
                                                  nomina = str(cols[18]),
                                                  rmu_sueldo_enero = null_to_decimal(cols[19],2),
                                                  decimo_tercero_enero = null_to_decimal(cols[20],2),
                                                  decimo_cuarto_enero = null_to_decimal(cols[21],2),
                                                  aporte_patronal_enero = null_to_decimal(cols[22],2),
                                                  fondos_reserva_enero = null_to_decimal(cols[23],2),
                                                  rmu_sueldo_febrero = null_to_decimal(cols[24],2),
                                                  decimo_tercero_febrero = null_to_decimal(cols[25],2),
                                                  decimo_cuarto_febrero = null_to_decimal(cols[26],2),
                                                  aporte_patronal_febrero = null_to_decimal(cols[27],2),
                                                  fondos_reserva_febrero = null_to_decimal(cols[28],2),
                                                  rmu_sueldo_marzo = null_to_decimal(cols[29],2),
                                                  decimo_tercero_marzo = null_to_decimal(cols[30],2),
                                                  decimo_cuarto_marzo = null_to_decimal(cols[31],2),
                                                  aporte_patronal_marzo = null_to_decimal(cols[32],2),
                                                  fondos_reserva_marzo = null_to_decimal(cols[33],2),
                                                  rmu_sueldo_abril = null_to_decimal(cols[34],2),
                                                  decimo_tercero_abril = null_to_decimal(cols[35],2),
                                                  decimo_cuarto_abril = null_to_decimal(cols[36],2),
                                                  aporte_patronal_abril = null_to_decimal(cols[37],2),
                                                  fondos_reserva_abril = null_to_decimal(cols[38],2),
                                                  rmu_sueldo_mayo = null_to_decimal(cols[39],2),
                                                  decimo_tercero_mayo = null_to_decimal(cols[40],2),
                                                  decimo_cuarto_mayo = null_to_decimal(cols[41],2),
                                                  aporte_patronal_mayo = null_to_decimal(cols[42],2),
                                                  fondos_reserva_mayo = null_to_decimal(cols[43],2),
                                                  rmu_sueldo_junio = null_to_decimal(cols[44],2),
                                                  decimo_tercero_junio = null_to_decimal(cols[45],2),
                                                  decimo_cuarto_junio = null_to_decimal(cols[46],2),
                                                  aporte_patronal_junio = null_to_decimal(cols[47],2),
                                                  fondos_reserva_junio = null_to_decimal(cols[48],2),
                                                  rmu_sueldo_julio = null_to_decimal(cols[49],2),
                                                  decimo_tercero_julio = null_to_decimal(cols[50],2),
                                                  decimo_cuarto_julio = null_to_decimal(cols[51],2),
                                                  aporte_patronal_julio = null_to_decimal(cols[52],2),
                                                  fondos_reserva_julio = null_to_decimal(cols[53],2),
                                                  rmu_sueldo_agosto = null_to_decimal(cols[54],2),
                                                  decimo_tercero_agosto = null_to_decimal(cols[55],2),
                                                  decimo_cuarto_agosto = null_to_decimal(cols[56],2),
                                                  aporte_patronal_agosto = null_to_decimal(cols[57],2),
                                                  fondos_reserva_agosto = null_to_decimal(cols[58],2),
                                                  rmu_sueldo_septiembre = null_to_decimal(cols[59],2),
                                                  decimo_tercero_septiembre = null_to_decimal(cols[60],2),
                                                  decimo_cuarto_septiembre = null_to_decimal(cols[61],2),
                                                  aporte_patronal_septiembre = null_to_decimal(cols[62],2),
                                                  fondos_reserva_septiembre = null_to_decimal(cols[63],2),
                                                  rmu_sueldo_octubre = null_to_decimal(cols[64],2),
                                                  decimo_tercero_octubre = null_to_decimal(cols[65],2),
                                                  decimo_cuarto_octubre = null_to_decimal(cols[66],2),
                                                  aporte_patronal_octubre = null_to_decimal(cols[67],2),
                                                  fondos_reserva_octubre = null_to_decimal(cols[68],2),
                                                  rmu_sueldo_noviembre = null_to_decimal(cols[69],2),
                                                  decimo_tercero_noviembre = null_to_decimal(cols[70],2),
                                                  decimo_cuarto_noviembre = null_to_decimal(cols[71],2),
                                                  aporte_patronal_noviembre = null_to_decimal(cols[72],2),
                                                  fondos_reserva_noviembre = null_to_decimal(cols[73],2),
                                                  rmu_sueldo_diciembre = null_to_decimal(cols[74],2),
                                                  decimo_tercero_diciembre = null_to_decimal(cols[75],2),
                                                  decimo_cuarto_diciembre = null_to_decimal(cols[76],2),
                                                  aporte_patronal_diciembre = null_to_decimal(cols[77],2),
                                                  fondos_reserva_diciembre = null_to_decimal(cols[78],2))
                            nominapac.save(request)
                        linea += 1
                    log(u'Importo PROFORMA PRESUPUESTARIA nomina: %s' % persona, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'ingresopac':
                try:
                    data['title'] = u'PROFORMA PRESUPUESTARIA - ' + departamento.nombre
                    data['periodopac'] = periodopac = PeriodoPac.objects.filter(pk=request.GET['id'], status=True)[0]
                    search = None
                    idobjetivooperativo = 0
                    idindicadorpoa = 0
                    idacciondocumento = 0
                    objetivosoperativos = None
                    indicadorpoa = None
                    acciondocumento = None
                    # objetivo opertaivo
                    data['objetivosoperativos'] = objetivosoperativos1 = departamento.objetivos_operativos(periodopac.anio)
                    if 'idobjetivooperativo' in request.GET:
                        idobjetivooperativo = request.GET['idobjetivooperativo']
                        objetivosoperativos = ObjetivoOperativo.objects.filter(pk=int(idobjetivooperativo), status=True)[0]
                    else:
                        if objetivosoperativos1:
                            objetivosoperativos = objetivosoperativos1[0]
                            idobjetivooperativo = objetivosoperativos.id

                    # indicador poa
                    if 'idindicadorpoa' in request.GET:
                        idindicadorpoa = request.GET['idindicadorpoa']
                        indicadorpoa = IndicadorPoa.objects.filter(pk=int(idindicadorpoa), status=True)[0]
                    else:
                        if objetivosoperativos:
                            indicadorpoa = objetivosoperativos.indicadorpoa_set.filter(status=True)[0]
                            idindicadorpoa = indicadorpoa.id

                    # accion documento
                    if 'idacciondocumento' in request.GET:
                        idacciondocumento = request.GET['idacciondocumento']
                        acciondocumento = AccionDocumento.objects.filter(pk=int(idacciondocumento), status=True)[0]
                    else:
                        if indicadorpoa:
                            acciondocumento = indicadorpoa.acciondocumento_set.filter(status=True)[0]
                            idacciondocumento =  acciondocumento.id

                    data['idobjetivooperativo'] = idobjetivooperativo
                    data['idindicadorpoa'] = idindicadorpoa
                    data['idacciondocumento'] = idacciondocumento

                    # acciondocumento = AccionDocumento.objects.filter(indicadorpoa__objetivooperativo=objetivosoperativo)[0]
                    data['departamento'] = departamento
                    if 'acciondocumento' in request.GET:
                        search = request.GET['acciondocumento']
                    if search:
                        acciondocumento = AccionDocumento.objects.filter(pk=search)[0]
                        # pac = Pac.objects.filter(departamento=departamento,acciondocumento=acciondocumento , status=True)
                        data['idacciondocumento'] = acciondocumento.id
                    else:
                        acciondocumento1 = acciondocumento
                        # periodopac = Pac.objects.filter(departamento=departamento,acciondocumento=acciondocumento1 , status=True)
                    data['permiso'] = periodopac.permisoinicio <= datetime.now().date() <= periodopac.permisofin
                    data['form2'] = PacForm()
                    data['form3'] = BienesServiciosInsumosPacForm()
                    data['IVA'] = IVA
                    data['nomina'] = False
                    if 'TALENTO HUMANO' in departamento.nombre:
                        data['nomina'] = True
                        data['nominapacs'] = NominaPac.objects.filter(status=True)
                    return render(request, "pac_pacdepartamento/ingresopac.html", data)
                except Exception as ex:
                    pass

            if action == 'deletepac':
                try:
                    data['title'] = u'Eliminar Caracteristica Producto PROFORMA PRESUPUESTARIA'
                    data['pac'] = Pac.objects.get(pk=request.GET['id'], status=True)
                    return render(request, 'pac_pacdepartamento/deletepac.html', data)
                except Exception as ex:
                    pass

            if action == 'importar':
                try:
                    data['title'] = u'Importar datos de la nomina'
                    data['form'] = ImportarArchivoForm()
                    data['periodoid'] = request.GET['id']
                    return render(request, "pac_pacdepartamento/importar.html", data)
                except Exception as ex:
                    pass

            if action == 'descargarexcel':
                try:
                    periodopac = PeriodoPac.objects.get(pk=int(request.GET['periodo']))
                    __author__ = 'Unemi'
                    title = xlwt.easyxf('font: name Times New Roman, color-index black, bold on , height 300; alignment: horiz centre')
                    title2 = xlwt.easyxf('font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    style1 = xlwt.easyxf(num_format_str='D-MMM-YY')
                    # style = xlwt.easyxf('font: bold on; border: left thin, right thin, top thin, bottom thin; align: wrap on, vert centre, horiz center;')
                    style = xlwt.easyxf('font: name Times New Roman, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    style1 = xlwt.easyxf('font: name Times New Roman, color-index black, height 150; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    style2 = xlwt.easyxf('font: name Times New Roman, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    style3 = xlwt.easyxf('align: wrap on, vert centre, horiz center;')
                    style4 = xlwt.easyxf('align: wrap on, vert centre;')
                    style5 = xlwt.easyxf('font: bold on; align: wrap on, vert centre, horiz center;')
                    font_style = xlwt.XFStyle()
                    font_style.font.bold = True
                    font_style2 = xlwt.XFStyle()
                    font_style2.font.bold = False
                    wb = xlwt.Workbook(encoding='utf-8')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=proforma_presupuestaria_' + random.randint(1, 10000).__str__() + '.xls'
                    ws = wb.add_sheet('GENERAL')
                    ws.write_merge(0, 0, 0, 44, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 44, u'MATRIZ DE LEVANTAMIENTO DE INFORMACIÓN PARA ESTRUCTURA DE PROFORMA PRESUPUESTARIA %s' % periodopac.anio,title2)
                    ws.write_merge(2, 2, 0, 44, u'UNIDAD ORGANIZACIONAL: UNEMI', title2)
                    ws.write_merge(3, 3, 8, 44, u'PROYECCIÓN DE ADQUISICIÓN/CONTRATACIÓN EN PORCENTAJES', style)
                    ws.write_merge(4, 4, 8, 10, u'ENERO', style)
                    ws.write_merge(4, 4, 11, 13, u'FEBRERO', style)
                    ws.write_merge(4, 4, 14, 16, u'MARZO', style)
                    ws.write_merge(4, 4, 17, 19, u'ABRIL', style)
                    ws.write_merge(4, 4, 20, 22, u'MAYO', style)
                    ws.write_merge(4, 4, 23, 25, u'JUNIO', style)
                    ws.write_merge(4, 4, 26, 28, u'JULIO', style)
                    ws.write_merge(4, 4, 29, 31, u'AGOSTO', style)
                    ws.write_merge(4, 4, 32, 34, u'SEPTIEMBRE', style)
                    ws.write_merge(4, 4, 35, 37, u'OCTUBRE', style)
                    ws.write_merge(4, 4, 38, 40, u'NOVIEMBRE', style)
                    ws.write_merge(4, 4, 41, 43, u'DICIEMBRE', style)

                    columns = [
                        (u"ITEM BIEN Y/O SERVICIO", 5000),
                        (u"DETALLE DEL PRODUCTO (Descripción de la contratación)", 10000),
                        (u"CANTIDAD", 2000),
                        (u"UNIDAD (metro, litro, período)", 6000),
                        (u"COSTO UNITARIO (Dólares)", 3000),
                        (u"SUBTOTAL", 3000),
                        (u"IVA", 3000),
                        (u"TOTAL", 3000),
                        (u"CANTIDAD", 3000),
                        (u"%", 3000),
                        (u"MONTO", 3000),
                        (u"CANTIDAD", 3000),
                        (u"%", 3000),
                        (u"MONTO", 3000),
                        (u"CANTIDAD", 3000),
                        (u"%", 3000),
                        (u"MONTO", 3000),
                        (u"CANTIDAD", 3000),
                        (u"%", 3000),
                        (u"MONTO", 3000),
                        (u"CANTIDAD", 3000),
                        (u"%", 3000),
                        (u"MONTO", 3000),
                        (u"CANTIDAD", 3000),
                        (u"%", 3000),
                        (u"MONTO", 3000),
                        (u"CANTIDAD", 3000),
                        (u"%", 3000),
                        (u"MONTO", 3000),
                        (u"CANTIDAD", 3000),
                        (u"%", 3000),
                        (u"MONTO", 3000),
                        (u"CANTIDAD", 3000),
                        (u"%", 3000),
                        (u"MONTO", 3000),
                        (u"CANTIDAD", 3000),
                        (u"%", 3000),
                        (u"MONTO", 3000),
                        (u"CANTIDAD", 3000),
                        (u"%", 3000),
                        (u"MONTO", 3000),
                        (u"CANTIDAD", 3000),
                        (u"%", 3000),
                        (u"MONTO", 3000),
                        (u"∑", 3000),
                    ]
                    row_num = 5
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], style)
                        ws.col(col_num).width = columns[col_num][1]
                    pacs = Pac.objects.filter(periodo=periodopac, status=True, estado__in=[1,2],departamento=departamento).order_by('departamento','caracteristicas')
                    row_num = 6
                    total_pac = 0
                    for r in pacs:
                        campo1 = r.caracteristicas.get_tipo_display()
                        campo2 = r.caracteristicas.descripcion
                        campo3 = r.cantidad()
                        campo4 = r.unidadmedida.nombre
                        campo5 = r.costounitario
                        campo6 = r.subtotal
                        campo7 = r.iva
                        campo8 = r.total
                        campo9 = ''
                        porcentaje = 0
                        if r.cantidadenero > 0:
                            campo9 = round(((r.cantidadenero / r.cantidad()) * 100), 2)
                            porcentaje += campo9
                        campo10 = ''
                        if r.cantidadfebrero > 0:
                            campo10 = round(((r.cantidadfebrero / r.cantidad()) * 100), 2)
                            porcentaje += campo10
                        campo11 = ''
                        if r.cantidadmarzo > 0:
                            campo11 = round(((r.cantidadmarzo / r.cantidad()) * 100), 2)
                            porcentaje += campo11
                        campo12 = ''
                        if r.cantidadabril > 0:
                            campo12 = round(((r.cantidadabril / r.cantidad()) * 100), 2)
                            porcentaje += campo12
                        campo13 = ''
                        if r.cantidadmayo > 0:
                            campo13 = round(((r.cantidadmayo / r.cantidad()) * 100), 2)
                            porcentaje += campo13
                        campo14 = ''
                        if r.cantidadjunio > 0:
                            campo14 = round(((r.cantidadjunio / r.cantidad()) * 100), 2)
                            porcentaje += campo14
                        campo15 = ''
                        if r.cantidadjulio > 0:
                            campo15 = round(((r.cantidadjulio / r.cantidad()) * 100), 2)
                            porcentaje += campo15
                        campo16 = ''
                        if r.cantidadagosto > 0:
                            campo16 = round(((r.cantidadagosto / r.cantidad()) * 100), 2)
                            porcentaje += campo16
                        campo17 = ''
                        if r.cantidadseptiembre > 0:
                            campo17 = round(((r.cantidadseptiembre / r.cantidad()) * 100), 2)
                            porcentaje += campo17
                        campo18 = ''
                        if r.cantidadoctubre > 0:
                            campo18 = round(((r.cantidadoctubre / r.cantidad()) * 100), 2)
                            porcentaje += campo18
                        campo19 = ''
                        if r.cantidadnoviembre > 0:
                            campo19 = round(((r.cantidadnoviembre / r.cantidad()) * 100), 2)
                            porcentaje += campo19
                        campo20 = ''
                        if r.cantidaddiciembre > 0:
                            campo20 = round(((r.cantidaddiciembre / r.cantidad()) * 100), 2)
                            porcentaje += campo20
                        diferenciaresta = 0
                        diferenciasuma = 0
                        if porcentaje != 100:
                            if porcentaje > 100:
                                diferenciaresta = round((porcentaje - 100), 2)
                            else:
                                diferenciasuma = round((100 - porcentaje), 2)
                            if campo20 != '':
                                campo20 = campo20 + diferenciasuma - diferenciaresta
                            else:
                                if campo19 != '':
                                    campo19 = campo19 + diferenciasuma - diferenciaresta
                                else:
                                    if campo18 != '':
                                        campo18 = campo18 + diferenciasuma - diferenciaresta
                                    else:
                                        if campo17 != '':
                                            campo17 = campo17 + diferenciasuma - diferenciaresta
                                        else:
                                            if campo16 != '':
                                                campo16 = campo16 + diferenciasuma - diferenciaresta
                                            else:
                                                if campo15 != '':
                                                    campo15 = campo15 + diferenciasuma - diferenciaresta
                                                else:
                                                    if campo14 != '':
                                                        campo14 = campo14 + diferenciasuma - diferenciaresta
                                                    else:
                                                        if campo13 != '':
                                                            campo13 = campo13 + diferenciasuma - diferenciaresta
                                                        else:
                                                            if campo12 != '':
                                                                campo12 = campo12 + diferenciasuma - diferenciaresta
                                                            else:
                                                                if campo11 != '':
                                                                    campo11 = campo11 + diferenciasuma - diferenciaresta
                                                                else:
                                                                    if campo10 != '':
                                                                        campo10 = campo10 + diferenciasuma - diferenciaresta
                                                                    else:
                                                                        if campo9 != '':
                                                                            campo9 = campo9 + diferenciasuma - diferenciaresta
                        montoenero = ''
                        if round((r.cantidadenero * r.costounitario), 2) > 0:
                            montoenero = round((r.cantidadenero * r.costounitario), 2)
                        montofebrero = ''
                        if round((r.cantidadfebrero * r.costounitario), 2) > 0:
                            montofebrero = round((r.cantidadfebrero * r.costounitario), 2)
                        montomarzo = ''
                        if round((r.cantidadmarzo * r.costounitario), 2) > 0:
                            montomarzo = round((r.cantidadmarzo * r.costounitario), 2)
                        montoabril = ''
                        if round((r.cantidadabril * r.costounitario), 2) > 0:
                            montoabril = round((r.cantidadabril * r.costounitario), 2)
                        montomayo = ''
                        if round((r.cantidadmayo * r.costounitario), 2) > 0:
                            montomayo = round((r.cantidadmayo * r.costounitario), 2)
                        montojunio = ''
                        if round((r.cantidadjunio * r.costounitario), 2) > 0:
                            montojunio = round((r.cantidadjunio * r.costounitario), 2)
                        montojulio = ''
                        if round((r.cantidadjulio * r.costounitario), 2) > 0:
                            montojulio = round((r.cantidadjulio * r.costounitario), 2)
                        montoagosto = ''
                        if round((r.cantidadagosto * r.costounitario), 2) > 0:
                            montoagosto = round((r.cantidadagosto * r.costounitario), 2)
                        montoseptiembre = ''
                        if round((r.cantidadseptiembre * r.costounitario), 2) > 0:
                            montoseptiembre = round((r.cantidadseptiembre * r.costounitario), 2)
                        montooctubre = ''
                        if round((r.cantidadoctubre * r.costounitario), 2) > 0:
                            montooctubre = round((r.cantidadoctubre * r.costounitario), 2)
                        montonoviembre = ''
                        if round((r.cantidadnoviembre * r.costounitario), 2) > 0:
                            montonoviembre = round((r.cantidadnoviembre * r.costounitario), 2)
                        montodiciembre = ''
                        if round((r.cantidaddiciembre * r.costounitario), 2) > 0:
                            montodiciembre = round((r.cantidaddiciembre * r.costounitario), 2)

                        cantidadenero = ''
                        if r.cantidadenero > 0:
                            cantidadenero = r.cantidadenero
                        cantidadfebrero = ''
                        if r.cantidadfebrero > 0:
                            cantidadfebrero = r.cantidadfebrero
                        cantidadmarzo = ''
                        if r.cantidadmarzo > 0:
                            cantidadmarzo = r.cantidadmarzo
                        cantidadabril = ''
                        if r.cantidadabril > 0:
                            cantidadabril = r.cantidadabril
                        cantidadmayo = ''
                        if r.cantidadmayo > 0:
                            cantidadmayo = r.cantidadmayo
                        cantidadjunio = ''
                        if r.cantidadjunio > 0:
                            cantidadjunio = r.cantidadjunio
                        cantidadjulio = ''
                        if r.cantidadjulio > 0:
                            cantidadjulio = r.cantidadjulio
                        cantidadagosto = ''
                        if r.cantidadagosto > 0:
                            cantidadagosto = r.cantidadagosto
                        cantidadseptiembre = ''
                        if r.cantidadseptiembre > 0:
                            cantidadseptiembre = r.cantidadseptiembre
                        cantidadoctubre = ''
                        if r.cantidadoctubre > 0:
                            cantidadoctubre = r.cantidadoctubre
                        cantidadnoviembre = ''
                        if r.cantidadnoviembre > 0:
                            cantidadnoviembre = r.cantidadnoviembre
                        cantidaddiciembre = ''
                        if r.cantidaddiciembre > 0:
                            cantidaddiciembre = r.cantidaddiciembre

                        ws.write(row_num, 0, campo1, style2)
                        ws.write(row_num, 1, campo2, style2)
                        ws.write(row_num, 2, campo3, style1)
                        ws.write(row_num, 3, campo4, style2)
                        ws.write(row_num, 4, campo5, style1)
                        ws.write(row_num, 5, campo6, style1)
                        ws.write(row_num, 6, campo7, style1)
                        ws.write(row_num, 7, campo8, style1)
                        ws.write(row_num, 8, cantidadenero, style1)
                        ws.write(row_num, 9, campo9, style1)
                        ws.write(row_num, 10, montoenero, style1)
                        ws.write(row_num, 11, cantidadfebrero, style1)
                        ws.write(row_num, 12, campo10, style1)
                        ws.write(row_num, 13, montofebrero, style1)
                        ws.write(row_num, 14, cantidadmarzo, style1)
                        ws.write(row_num, 15, campo11, style1)
                        ws.write(row_num, 16, montomarzo, style1)
                        ws.write(row_num, 17, cantidadabril, style1)
                        ws.write(row_num, 18, campo12, style1)
                        ws.write(row_num, 19, montoabril, style1)
                        ws.write(row_num, 20, cantidadmayo, style1)
                        ws.write(row_num, 21, campo13, style1)
                        ws.write(row_num, 22, montomayo, style1)
                        ws.write(row_num, 23, cantidadjunio, style1)
                        ws.write(row_num, 24, campo14, style1)
                        ws.write(row_num, 25, montojunio, style1)
                        ws.write(row_num, 26, cantidadjulio, style1)
                        ws.write(row_num, 27, campo15, style1)
                        ws.write(row_num, 28, montojulio, style1)
                        ws.write(row_num, 29, cantidadagosto, style1)
                        ws.write(row_num, 30, campo16, style1)
                        ws.write(row_num, 31, montoagosto, style1)
                        ws.write(row_num, 32, cantidadseptiembre, style1)
                        ws.write(row_num, 33, campo17, style1)
                        ws.write(row_num, 34, montoseptiembre, style1)
                        ws.write(row_num, 35, cantidadoctubre, style1)
                        ws.write(row_num, 36, campo18, style1)
                        ws.write(row_num, 37, montooctubre, style1)
                        ws.write(row_num, 38, cantidadnoviembre, style1)
                        ws.write(row_num, 39, campo19, style1)
                        ws.write(row_num, 40, montonoviembre, style1)
                        ws.write(row_num, 41, cantidaddiciembre, style1)
                        ws.write(row_num, 42, campo20, style1)
                        ws.write(row_num, 43, montodiciembre, style1)
                        ws.write(row_num, 44, porcentaje + diferenciasuma - diferenciaresta, style1)
                        # while i < len(r):
                        #     # ws.write(row_num, i, r[i], font_style)
                        #     # ws.col(i).width = columns[i][1]
                        row_num += 1
                        total_pac += r.total
                    ws.write(row_num, 7, total_pac, style)

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'pdf':
                try:
                    data['periodopac'] = periodopac = PeriodoPac.objects.get(pk=int(request.GET['periodo']))
                    data['departamento'] = departamento.nombre
                    data['jefe'] = persona.nombre_titulo()
                    data['pacs'] =  pacs = Pac.objects.filter(periodo=periodopac, status=True, estado__in=[1, 2], departamento=departamento).order_by('departamento', 'caracteristicas')
                    return conviert_html_to_pdf(
                        'pac_pacdepartamento/pdfproforma.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Ingreso Proforma Presupuestaria Departamental'
            search = None
            tipo = None
            if 's' in request.GET:
                search = request.GET['s']
            if search:
                periodopac = PeriodoPac.objects.filter(Q(descripcion__icontains=search) |
                                                       Q(anio__icontains=search), status=True, id__gt=5).order_by('-id')
            else:
                periodopac = PeriodoPac.objects.filter(status=True, id__gt=5).order_by('-id')
            paging = MiPaginador(periodopac, 25)
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
            data['periodopacs'] = page.object_list
            data['departamento'] = departamento
            return render(request, 'pac_pacdepartamento/view.html', data)