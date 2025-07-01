# -*- coding: UTF-8 -*-
import json
from decimal import Decimal

import xlrd
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models import Q, Sum
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template import RequestContext
from django.template.loader import get_template
from django.utils.encoding import smart_str

from decorators import secure_module
from sagest.forms import PacDetalleGeneralForm, PacDetalleGeneralAprobadoForm, ImportarArchivoForm
from sagest.models import PeriodoPac, ObjetivoOperativo, null_to_numeric, Departamento, ObjetivosPac, PacGeneral, PacDetalladoGeneral, \
    datetime, PacArchivo, ProductosPac, Productos, null_to_decimal, PeriodoPoa
from settings import ARCHIVO_TIPO_GENERAL
from sga.commonviews import adduserdata
from sga.funciones import log, MiPaginador, convertir_fecha, generar_nombre, remover_caracteres_especiales_unicode
from sga.models import Archivo
unicode =str

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()


def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addpacgeneral':
            try:
                if PacGeneral.objects.filter(periodo_id=int(request.POST['idperiodo']), objetivospac__departamento_id=int(request.POST['departamento']), objetivospac_id=int(request.POST['objetivooperativo']), productospac_id=int(request.POST['productospac']), status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                total = Decimal(request.POST['valorenero']).quantize(Decimal('.01')) + Decimal(request.POST['valorfebrero']).quantize(Decimal('.01')) + Decimal(request.POST['valormarzo']).quantize(Decimal('.01')) + Decimal(request.POST['valorabril']).quantize(Decimal('.01')) + Decimal(request.POST['valormayo']).quantize(Decimal('.01')) + Decimal(request.POST['valorjunio']).quantize(Decimal('.01')) + Decimal(request.POST['valorjulio']).quantize(Decimal('.01')) + Decimal(request.POST['valoragosto']).quantize(Decimal('.01')) + Decimal(request.POST['valorseptiembre']).quantize(Decimal('.01')) + Decimal(request.POST['valoroctubre']).quantize(Decimal('.01')) + Decimal(request.POST['valornoviembre']).quantize(Decimal('.01')) + Decimal(request.POST['valordiciembre']).quantize(Decimal('.01'))

                pacgeneral = PacGeneral(periodo_id=int(request.POST['idperiodo']),
                                        objetivospac_id=int(request.POST['objetivooperativo']),
                                        productospac_id=int(request.POST['productospac']),
                                        total=total,
                                        saldo=total)
                pacgeneral.save(request)
                # enero
                pacdetallegeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                        mes = 1,
                                                        valor = Decimal(request.POST['valorenero']).quantize(Decimal('.01')))
                pacdetallegeneral.save(request)
                # febrero
                pacdetallegeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                        mes = 2,
                                                        valor = Decimal(request.POST['valorfebrero']).quantize(Decimal('.01')))
                pacdetallegeneral.save(request)
                # marzo
                pacdetallegeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                        mes = 3,
                                                        valor = Decimal(request.POST['valormarzo']).quantize(Decimal('.01')))
                pacdetallegeneral.save(request)
                # abril
                pacdetallegeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                        mes = 4,
                                                        valor = Decimal(request.POST['valorabril']).quantize(Decimal('.01')))
                pacdetallegeneral.save(request)
                # mayo
                pacdetallegeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                        mes = 5,
                                                        valor = Decimal(request.POST['valormayo']).quantize(Decimal('.01')))
                pacdetallegeneral.save(request)
                # junio
                pacdetallegeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                        mes = 6,
                                                        valor = Decimal(request.POST['valorjunio']).quantize(Decimal('.01')))
                pacdetallegeneral.save(request)
                # julio
                pacdetallegeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                        mes = 7,
                                                        valor = Decimal(request.POST['valorjulio']).quantize(Decimal('.01')))
                pacdetallegeneral.save(request)
                # agosto
                pacdetallegeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                        mes = 8,
                                                        valor = Decimal(request.POST['valoragosto']).quantize(Decimal('.01')))
                pacdetallegeneral.save(request)
                # septiembre
                pacdetallegeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                        mes = 9,
                                                        valor = Decimal(request.POST['valorseptiembre']).quantize(Decimal('.01')))
                pacdetallegeneral.save(request)
                # octubre
                pacdetallegeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                        mes = 10,
                                                        valor = Decimal(request.POST['valoroctubre']).quantize(Decimal('.01')))
                pacdetallegeneral.save(request)
                # noviembre
                pacdetallegeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                        mes = 11,
                                                        valor = Decimal(request.POST['valornoviembre']).quantize(Decimal('.01')))
                pacdetallegeneral.save(request)
                # diciembre
                pacdetallegeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                        mes = 12,
                                                        valor = Decimal(request.POST['valordiciembre']).quantize(Decimal('.01')))
                pacdetallegeneral.save(request)
                log(u'Registro nuevo caracteristicas productos PAC: %s' % pacgeneral, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'editpacdepartamento':
            try:
                pacgeneral = PacGeneral.objects.get(pk=int(request.POST['idpac']), status=True)
                total = Decimal(request.POST['valorenero']).quantize(Decimal('.01')) + Decimal(request.POST['valorfebrero']).quantize(Decimal('.01')) + Decimal(request.POST['valormarzo']).quantize(Decimal('.01')) + Decimal(request.POST['valorabril']).quantize(Decimal('.01')) + Decimal(request.POST['valormayo']).quantize(Decimal('.01')) + Decimal(request.POST['valorjunio']).quantize(Decimal('.01')) + Decimal(request.POST['valorjulio']).quantize(Decimal('.01')) + Decimal(request.POST['valoragosto']).quantize(Decimal('.01')) + Decimal(request.POST['valorseptiembre']).quantize(Decimal('.01')) + Decimal(request.POST['valoroctubre']).quantize(Decimal('.01')) + Decimal(request.POST['valornoviembre']).quantize(Decimal('.01')) + Decimal(request.POST['valordiciembre']).quantize(Decimal('.01'))
                pacgeneral.total=total
                pacgeneral.saldo=total - pacgeneral.valorejecutada()
                pacgeneral.save(request)
                # enero
                pacdetallegeneral = PacDetalladoGeneral.objects.filter(pacgeneral=pacgeneral, status=True, mes=1)[0]
                pacdetallegeneral.valor = Decimal(request.POST['valorenero']).quantize(Decimal('.01'))
                pacdetallegeneral.save(request)
                # febrero
                pacdetallegeneral = PacDetalladoGeneral.objects.filter(pacgeneral=pacgeneral, status=True, mes=2)[0]
                pacdetallegeneral.valor = Decimal(request.POST['valorfebrero']).quantize(Decimal('.01'))
                pacdetallegeneral.save(request)
                # marzo
                pacdetallegeneral = PacDetalladoGeneral.objects.filter(pacgeneral=pacgeneral, status=True, mes=3)[0]
                pacdetallegeneral.valor = Decimal(request.POST['valormarzo']).quantize(Decimal('.01'))
                pacdetallegeneral.save(request)
                # abril
                pacdetallegeneral = PacDetalladoGeneral.objects.filter(pacgeneral=pacgeneral, status=True, mes=4)[0]
                pacdetallegeneral.valor = Decimal(request.POST['valorabril']).quantize(Decimal('.01'))
                pacdetallegeneral.save(request)
                # mayo
                pacdetallegeneral = PacDetalladoGeneral.objects.filter(pacgeneral=pacgeneral, status=True, mes=5)[0]
                pacdetallegeneral.valor = Decimal(request.POST['valormayo']).quantize(Decimal('.01'))
                pacdetallegeneral.save(request)
                # junio
                pacdetallegeneral = PacDetalladoGeneral.objects.filter(pacgeneral=pacgeneral, status=True, mes=6)[0]
                pacdetallegeneral.valor = Decimal(request.POST['valorjunio']).quantize(Decimal('.01'))
                pacdetallegeneral.save(request)
                # julio
                pacdetallegeneral = PacDetalladoGeneral.objects.filter(pacgeneral=pacgeneral, status=True, mes=7)[0]
                pacdetallegeneral.valor = Decimal(request.POST['valorjulio']).quantize(Decimal('.01'))
                pacdetallegeneral.save(request)
                # agosto
                pacdetallegeneral = PacDetalladoGeneral.objects.filter(pacgeneral=pacgeneral, status=True, mes=8)[0]
                pacdetallegeneral.valor = Decimal(request.POST['valoragosto']).quantize(Decimal('.01'))
                pacdetallegeneral.save(request)
                # septiembre
                pacdetallegeneral = PacDetalladoGeneral.objects.filter(pacgeneral=pacgeneral, status=True, mes=9)[0]
                pacdetallegeneral.valor = Decimal(request.POST['valorseptiembre']).quantize(Decimal('.01'))
                pacdetallegeneral.save(request)
                # octubre
                pacdetallegeneral = PacDetalladoGeneral.objects.filter(pacgeneral=pacgeneral, status=True, mes=10)[0]
                pacdetallegeneral.valor = Decimal(request.POST['valoroctubre']).quantize(Decimal('.01'))
                pacdetallegeneral.save(request)
                # noviembre
                pacdetallegeneral = PacDetalladoGeneral.objects.filter(pacgeneral=pacgeneral, status=True, mes=11)[0]
                pacdetallegeneral.valor = Decimal(request.POST['valornoviembre']).quantize(Decimal('.01'))
                pacdetallegeneral.save(request)
                # diciembre
                pacdetallegeneral = PacDetalladoGeneral.objects.filter(pacgeneral=pacgeneral, status=True, mes=12)[0]
                pacdetallegeneral.valor = Decimal(request.POST['valordiciembre']).quantize(Decimal('.01'))
                pacdetallegeneral.save(request)

                log(u'Registro modificado producto PAC: %s' % pacgeneral, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al editar los datos."})

        if action == 'deletepac':
            try:
                pac = PacGeneral.objects.get(pk=request.POST['id'], status=True)
                pac.status=False
                pac.save(request)
                log(u'Elimino productos PAC: %s' % pac, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'aprobarpacgeneral':
            try:
                pacdetalladogeneral = PacDetalladoGeneral.objects.get(pk=request.POST['id'], status=True)
                if request.POST['aprobado'] == 'false':
                    pacdetalladogeneral.aprobado = False
                    pacdetalladogeneral.fechaaprobado = None
                    pacdetalladogeneral.observacionejecutado = ''
                    pacdetalladogeneral.fechaajudicado = None
                    pacdetalladogeneral.observacionajudicado = ''
                    pacdetalladogeneral.valorejecutado = 0
                    pacdetalladogeneral.valorajudicado = 0
                else:
                    pacdetalladogeneral.aprobado = True
                    pacdetalladogeneral.fechaaprobado = convertir_fecha(request.POST['fechaejecutado'])
                    pacdetalladogeneral.observacionejecutado = request.POST['observacionejecutado']
                    pacdetalladogeneral.observacionajudicado = request.POST['observacionajudicado']
                    pacdetalladogeneral.fechaajudicado = convertir_fecha(request.POST['fechaajudicado'])
                    pacdetalladogeneral.valorejecutado = Decimal(request.POST['valorejecutado']).quantize(Decimal('.01'))
                    pacdetalladogeneral.valorajudicado = Decimal(request.POST['valorajudicado']).quantize(Decimal('.01'))
                pacdetalladogeneral.save(request)
                pacgeneral = pacdetalladogeneral.pacgeneral
                pacgeneral.save(request)
                log(u'Aprobo productos PAC: %s' % pacdetalladogeneral, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al aprobar los datos."})

        if action == 'segmento':
            try:
                data['objetivosoperativo'] = objetivosoperativo = ObjetivosPac.objects.get(pk=int(request.POST['objetivooperativo']), status=True)
                data['pacgeneral'] = pacgeneral = PacGeneral.objects.filter(objetivospac__departamento_id=int(request.POST['departamento']), objetivospac=objetivosoperativo, status=True).order_by('productospac')
                data['periodopac'] = periodopac = PeriodoPac.objects.filter(pk=request.POST['periodo'], status=True)[0]
                data['total_pac'] = null_to_numeric(PacGeneral.objects.filter(objetivospac__departamento_id=int(request.POST['departamento']), status=True).aggregate(total=Sum('total'))['total'])
                data['ejecutado_pac'] = null_to_numeric(PacGeneral.objects.filter(objetivospac__departamento_id=int(request.POST['departamento']), status=True).aggregate(valorejecutado=Sum('valorejecutado'))['valorejecutado'])
                data['saldo_pac'] = null_to_numeric(PacGeneral.objects.filter(objetivospac__departamento_id=int(request.POST['departamento']), status=True).aggregate(saldo=Sum('saldo'))['saldo'])
                data['meses'] = [1,2,3,4,5,6,7,8,9,10,11,12]
                template = get_template("pac_pacgeneral/segmento.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'importar':

            def vaciar_caracter(cadena):
                valor = ''
                if cadena != '':
                    valor = str(int(cadena))
                return valor

            try:
                form = ImportarArchivoForm(request.POST, request.FILES)
                periodopac = PeriodoPac.objects.filter(pk=request.POST['periodopac'], status=True)[0]
                if form.is_valid():
                    hoy = datetime.now().date()
                    nfile = request.FILES['archivo']
                    numeroarchivo = 0
                    # try:
                    #     numeroarchivo = int(nfile._name.split('_')[1].split('(')[0].split('.')[0])
                    # except:
                    #     return JsonResponse({"result": "bad", "mensaje": u"Error de numeracion de archivo."})
                    nfile._name = generar_nombre("importacion_", nfile._name)
                    # if DistributivoPersona.objects.filter(numeroarchivo__gte=numeroarchivo).exists():
                    #     return JsonResponse({"result": "bad", "mensaje": u"Error al subir un archivo antiguo."})
                    archivo = Archivo(nombre='IMPORTACION PAC',
                                      fecha=datetime.now().date(),
                                      archivo=nfile,
                                      tipo_id=ARCHIVO_TIPO_GENERAL)
                    archivo.save(request)
                    workbook = xlrd.open_workbook(archivo.archivo.file.name)
                    sheet = workbook.sheet_by_index(0)
                    periodopoa = PeriodoPoa.objects.filter(anio=periodopac.anio)[0]
                    PacArchivo.objects.filter(periodo=periodopac).delete()
                    PacGeneral.objects.filter(periodo=periodopac).delete()
                    ObjetivosPac.objects.filter(periodopoa=periodopoa).delete()
                    linea = 1
                    for rowx in range(sheet.nrows):
                        if linea >= 2:
                            cols = sheet.row_values(rowx)
                            if cols[6] != '':
                                if len(cols) == 63:
                                    if linea == 438:
                                        pass

                                    #  PRODUCTO PAC
                                    productospac = None
                                    if not ProductosPac.objects.filter(descripcion=cols[6].strip().upper()).exists():
                                        productospac = ProductosPac(descripcion=cols[6].strip().upper())
                                        productospac.save(request)
                                    else:
                                        productospac = ProductosPac.objects.filter(descripcion=cols[6].strip().upper())[0]

                                    #  DEPARTAMENTO
                                    depa = remover_caracteres_especiales_unicode(cols[7].strip().upper())
                                    departamento = None

                                    if not Departamento.objects.filter(nombre=depa).exists():
                                        transaction.set_rollback(True)
                                        return JsonResponse({"result": "bad", "mensaje": u"Departamento %s no existe." % depa})
                                    else:
                                        departamento = Departamento.objects.filter(nombre=depa)[0]

                                    #  PRODUCTO
                                    productos = None
                                    if not Productos.objects.filter(descripcion=cols[8].strip().upper()).exists():
                                        productos = Productos(descripcion=cols[8].strip().upper())
                                        productos.save(request)
                                    else:
                                        productos = Productos.objects.filter(descripcion=cols[8].strip().upper())[0]

                                    # CUATRIMESTRE1
                                    cuatrimestre1 = False
                                    if cols[18].strip() != '':
                                        cuatrimestre1 = True

                                    # CUATRIMESTRE2
                                    cuatrimestre2 = False
                                    if cols[19].strip() != '':
                                        cuatrimestre2 = True

                                    # CUATRIMESTRE3
                                    cuatrimestre3 = False
                                    if cols[20].strip() != '':
                                        cuatrimestre3 = True

                                    # cantidadanual
                                    cantidadanual = 0
                                    if cols[9] != '':
                                        cantidadanual = int(cols[9])


                                    # # REMUNERACION ESCALA
                                    # rmuescala = 0
                                    # try:
                                    #     rmuescala = float(cols[12].replace(',',''))
                                    # except:
                                    #     pass

                                    pacarchivo = PacArchivo(periodo = periodopac,
                                                            programa = cols[0].strip(),
                                                            actividad = cols[1].strip(),
                                                            renglo = str(cols[2]).strip(),
                                                            fuente = cols[3].strip(),
                                                            codigocategoria = vaciar_caracter(cols[4]),
                                                            tipocompra = cols[5].strip(),
                                                            productospac = productospac,
                                                            departamento = departamento,
                                                            productos = productos,
                                                            costototal = null_to_decimal(cols[12],2),
                                                            compreforma = str(cols[13]),
                                                            resolucionreforma = cols[14].strip(),
                                                            aumenta = null_to_decimal(cols[15],2),
                                                            disminuye = null_to_decimal(cols[16],2),
                                                            saldoreforma = null_to_decimal(cols[17],2),
                                                            cuatrimestre1 = cuatrimestre1,
                                                            cuatrimestre2 = cuatrimestre2,
                                                            cuatrimestre3 = cuatrimestre3,
                                                            tipoproducto = cols[21].strip(),
                                                            catalodoelectronico = cols[22].strip(),
                                                            procedimientosugerido = cols[23].strip(),
                                                            tiporegimen = cols[24].strip(),
                                                            comprometidoeneromonto = null_to_decimal(cols[25],2),
                                                            comprometidoenero = cols[26],
                                                            comprometidofebreromonto = null_to_decimal(cols[27],2),
                                                            comprometidofebrero = cols[28],
                                                            comprometidomarzomonto = null_to_decimal(cols[29],2),
                                                            comprometidomarzo = cols[30],
                                                            comprometidoabrilmonto = null_to_decimal(cols[31],2),
                                                            comprometidoabril = cols[32],
                                                            comprometidomayomonto = null_to_decimal(cols[33],2),
                                                            comprometidomayo = cols[34],
                                                            comprometidojuniomonto = null_to_decimal(cols[35],2),
                                                            comprometidojunio = cols[36],
                                                            comprometidojuliomonto = null_to_decimal(cols[37],2),
                                                            comprometidojulio = cols[38],
                                                            comprometidoagostomonto = null_to_decimal(cols[39],2),
                                                            comprometidoagosto = cols[40],
                                                            comprometidoseptiembremonto = null_to_decimal(cols[41],2),
                                                            comprometidoseptiembre = cols[42],
                                                            comprometidooctubremonto = null_to_decimal(cols[43],2),
                                                            comprometidooctubre = cols[44],
                                                            comprometidonoviembremonto = null_to_decimal(cols[45],2),
                                                            comprometidonoviembre = cols[46],
                                                            comprometidodiciembremonto = null_to_decimal(cols[47],2),
                                                            comprometidodiciembre = cols[48],
                                                            paccomprometido = null_to_decimal(cols[49],2),
                                                            pacdisponible = null_to_decimal(cols[50],2),
                                                            planificadoenero = null_to_decimal(cols[51],2),
                                                            planificadofebrero = null_to_decimal(cols[52],2),
                                                            planificadomarzo = null_to_decimal(cols[53],2),
                                                            planificadoabril = null_to_decimal(cols[54],2),
                                                            planificadomayo = null_to_decimal(cols[55],2),
                                                            planificadojunio = null_to_decimal(cols[56],2),
                                                            planificadojulio = null_to_decimal(cols[57],2),
                                                            planificadoagosto = null_to_decimal(cols[58],2),
                                                            planificadoseptiembre = null_to_decimal(cols[59],2),
                                                            planificadooctubre = null_to_decimal(cols[60],2),
                                                            planificadonoviembre = null_to_decimal(cols[61],2),
                                                            planificadodiciembre = null_to_decimal(cols[62],2))
                                    pacarchivo.save(request)

                        linea += 1

                    # llenar en la tablas principales
                    cursor = connection.cursor()
                    # sql = "select pa.departamento_id,pa.productospac_id, sum(pa.planificadoenero+pa.planificadofebrero+pa.planificadomarzo+pa.planificadoabril+pa.planificadomayo+pa.planificadojunio+pa.planificadojulio+pa.planificadoagosto+pa.planificadoseptiembre+pa.planificadooctubre+pa.planificadonoviembre+pa.planificadodiciembre) as planificado, " \
                    #       " sum(pa.comprometidoeneromonto+pa.comprometidofebreromonto+pa.comprometidomarzomonto+pa.comprometidoabrilmonto+pa.comprometidomayomonto+pa.comprometidojuniomonto+pa.comprometidojuliomonto+pa.comprometidoagostomonto+pa.comprometidoseptiembremonto+pa.comprometidooctubremonto+pa.comprometidonoviembremonto+pa.comprometidodiciembremonto) as devengado " \
                    #       " from sagest_pacarchivo pa where pa.periodo_id="+ str(periodopac.id) +" GROUP by pa.departamento_id,pa.productospac_id "

                    sql = "select pa.departamento_id, pa.productospac_id, sum(pa.planificadoenero),sum(pa.comprometidoeneromonto), sum(pa.planificadofebrero),sum(pa.comprometidofebreromonto), " \
                          " sum(pa.planificadomarzo),sum(pa.comprometidomarzomonto), sum(pa.planificadoabril),sum(pa.comprometidoabrilmonto), sum(pa.planificadomayo),sum(pa.comprometidomayomonto), " \
                          " sum(pa.planificadojunio),sum(pa.comprometidojuniomonto), sum(pa.planificadojulio),sum(pa.comprometidojuliomonto), sum(pa.planificadoagosto),sum(pa.comprometidoagostomonto), " \
                          " sum(pa.planificadoseptiembre),sum(pa.comprometidoseptiembremonto), sum(pa.planificadooctubre),sum(pa.comprometidooctubremonto), sum(pa.planificadonoviembre),sum(pa.comprometidonoviembremonto), " \
                          " sum(pa.planificadodiciembre),sum(pa.comprometidodiciembremonto) from sagest_pacarchivo pa where pa.periodo_id="+ str(periodopac.id) +" GROUP by pa.departamento_id, pa.productospac_id "

                    cursor.execute(sql)
                    results = cursor.fetchall()
                    for r in results:
                        objetivospac = None
                        if ObjetivosPac.objects.filter(periodopoa=periodopoa, descripcion='NINGUNA', departamento_id=r[0],status=True).exists():
                            objetivospac = ObjetivosPac.objects.filter(periodopoa=periodopoa, descripcion='NINGUNA', departamento_id=r[0],status=True)[0]
                        else:
                            objetivospac = ObjetivosPac(periodopoa=periodopoa,
                                                        descripcion='NINGUNA',
                                                        departamento_id=r[0])
                            objetivospac.save(request)

                        pacgeneral = PacGeneral(periodo = periodopac,
                                                objetivospac = objetivospac,
                                                productospac_id = r[1],
                                                total = null_to_decimal(r[2]+r[4]+r[6]+r[8]+r[10]+r[12]+r[14]+r[16]+r[18]+r[20]+r[22]+r[24]),
                                                valorejecutado = null_to_decimal(r[3]+r[5]+r[7]+r[9]+r[11]+r[13]+r[15]+r[17]+r[19]+r[21]+r[23]+r[25]),
                                                saldo =null_to_decimal(r[2]+r[4]+r[6]+r[8]+r[10]+r[12]+r[14]+r[16]+r[18]+r[20]+r[22]+r[24])-null_to_decimal(r[3]+r[5]+r[7]+r[9]+r[11]+r[13]+r[15]+r[17]+r[19]+r[21]+r[23]+r[25]))
                        pacgeneral.save(request)
                        # enero
                        pacdetalladogeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                                  mes = 1,
                                                                  valor = null_to_decimal(r[2]),
                                                                  valorejecutado = null_to_decimal(r[3]),
                                                                  saldo = null_to_decimal(r[2]-r[3]))
                        pacdetalladogeneral.save(request)
                        # febrero
                        pacdetalladogeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                                  mes = 2,
                                                                  valor = null_to_decimal(r[4]),
                                                                  valorejecutado = null_to_decimal(r[5]),
                                                                  saldo = null_to_decimal(r[4]-r[5]))
                        pacdetalladogeneral.save(request)
                        # marzo
                        pacdetalladogeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                                  mes = 3,
                                                                  valor = null_to_decimal(r[6]),
                                                                  valorejecutado = null_to_decimal(r[7]),
                                                                  saldo = null_to_decimal(r[6]-r[7]))
                        pacdetalladogeneral.save(request)
                        # abril
                        pacdetalladogeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                                  mes = 4,
                                                                  valor = null_to_decimal(r[8]),
                                                                  valorejecutado = null_to_decimal(r[9]),
                                                                  saldo = null_to_decimal(r[8]-r[9]))
                        pacdetalladogeneral.save(request)
                        # mayo
                        pacdetalladogeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                                  mes = 5,
                                                                  valor = null_to_decimal(r[10]),
                                                                  valorejecutado = null_to_decimal(r[11]),
                                                                  saldo = null_to_decimal(r[10]-r[11]))
                        pacdetalladogeneral.save(request)
                        # junio
                        pacdetalladogeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                                  mes = 6,
                                                                  valor = null_to_decimal(r[12]),
                                                                  valorejecutado = null_to_decimal(r[13]),
                                                                  saldo = null_to_decimal(r[12]-r[13]))
                        pacdetalladogeneral.save(request)
                        # julio
                        pacdetalladogeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                                  mes = 7,
                                                                  valor = null_to_decimal(r[14]),
                                                                  valorejecutado = null_to_decimal(r[15]),
                                                                  saldo = null_to_decimal(r[14]-r[15]))
                        pacdetalladogeneral.save(request)
                        # agosto
                        pacdetalladogeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                                  mes = 8,
                                                                  valor = null_to_decimal(r[16]),
                                                                  valorejecutado = null_to_decimal(r[17]),
                                                                  saldo = null_to_decimal(r[16]-r[17]))
                        pacdetalladogeneral.save(request)
                        # septiembre
                        pacdetalladogeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                                  mes = 9,
                                                                  valor = null_to_decimal(r[18]),
                                                                  valorejecutado = null_to_decimal(r[19]),
                                                                  saldo = null_to_decimal(r[18]-r[19]))
                        pacdetalladogeneral.save(request)
                        # octubre
                        pacdetalladogeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                                  mes = 10,
                                                                  valor = null_to_decimal(r[20]),
                                                                  valorejecutado = null_to_decimal(r[21]),
                                                                  saldo = null_to_decimal(r[20]-r[21]))
                        pacdetalladogeneral.save(request)
                        # noviembre
                        pacdetalladogeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                                  mes = 11,
                                                                  valor = null_to_decimal(r[22]),
                                                                  valorejecutado = null_to_decimal(r[23]),
                                                                  saldo = null_to_decimal(r[22]-r[23]))
                        pacdetalladogeneral.save(request)
                        # diciembre
                        pacdetalladogeneral = PacDetalladoGeneral(pacgeneral = pacgeneral,
                                                                  mes = 12,
                                                                  valor = null_to_decimal(r[24]),
                                                                  valorejecutado = null_to_decimal(r[25]),
                                                                  saldo = null_to_decimal(r[24]-r[25]))
                        pacdetalladogeneral.save(request)
                    connection.close()
                    log(u'Importo plantilla PAC: %s' % pacarchivo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. en la linea %s" % linea})


        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'ingresopac':
                try:
                    data['title'] = u'PAC UNIVERSIDAD ESTATAL DE MILAGRO '
                    data['periodopac'] = periodopac = PeriodoPac.objects.filter(pk=request.GET['id'], status=True)[0]
                    data['departamentos'] = departamentos = Departamento.objects.filter(status=True, objetivospac__isnull=False, objetivospac__periodopoa__anio=periodopac.anio).distinct()

                    search = None
                    idobjetivooperativo = 0
                    iddepartamento = 0

                    # departamento
                    if 'iddepartamento' in request.GET:
                        iddepartamento = request.GET['iddepartamento']
                        departamento = Departamento.objects.filter(pk=int(iddepartamento), status=True)[0]
                    else:
                        departamento = departamentos[0]
                        iddepartamento = departamento.id

                    # objetivo opertaivo
                    data['objetivosoperativos'] = objetivosoperativos1 = departamento.objetivos_operativosgeneral(periodopac.anio)
                    if 'idobjetivooperativo' in request.GET:
                        idobjetivooperativo = request.GET['idobjetivooperativo']
                        # data['objetivosoperativos'] = objetivosoperativos1 = ObjetivoOperativo.objects.filter(pk=int(idobjetivooperativo))
                        objetivosoperativos = ObjetivoOperativo.objects.filter(pk=int(idobjetivooperativo), status=True)[0]
                    else:
                        objetivosoperativos = objetivosoperativos1[0]
                        idobjetivooperativo = objetivosoperativos.id


                    data['idobjetivooperativo'] = idobjetivooperativo
                    data['iddepartamento'] = iddepartamento

                    data['aprobado'] = periodopac.aprobado
                    data['form2'] = PacDetalleGeneralForm()
                    data['form3'] = PacDetalleGeneralAprobadoForm()
                    return render(request, "pac_pacgeneral/ingresopac.html", data)
                except Exception as ex:
                    pass

            if action == 'deletepac':
                try:
                    data['title'] = u'Eliminar Producto PAC UNEMI'
                    data['pac'] = PacGeneral.objects.get(pk=request.GET['id'], status=True)
                    return render(request, 'pac_pacgeneral/deletepac.html', data)
                except Exception as ex:
                    pass

            if action == 'importar':
                try:
                    data['title'] = u'Importar datos del Pac'
                    data['periodopac'] = PeriodoPac.objects.get(pk=request.GET['idperiodo'], status=True)
                    data['form'] = ImportarArchivoForm()
                    return render(request, "pac_pacgeneral/importar.html", data)
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Ingreso PAC UNEMI'
            search = None
            tipo = None

            if 's' in request.GET:
                search = request.GET['s']
            if search:
                periodopac = PeriodoPac.objects.filter(Q(descripcion__icontains=search) |
                                                       Q(anio__icontains=search), status=True).order_by('-id')
            else:
                periodopac = PeriodoPac.objects.filter(status=True).order_by('-id')
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
            # data['departamento'] = departamento

            return render(request, 'pac_pacgeneral/view.html', data)