# -*- coding: UTF-8 -*-
import json
import xlrd
import random
import xlwt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import Context
from django.template.loader import get_template
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import PeriodoPacForm, TopePeriodoPacForm, ReformaForm, PacForm, PacReformaForm, \
    ImportarArchivoForm
from sagest.models import PeriodoPac, TopePeriodoPac, Pac, datetime, CatalogoBien, Reforma, ReformaPac, Departamento, \
    ObjetivoOperativo, IndicadorPoa, AccionDocumento, PartidaPrograma, PartidaActividad, PartidaFuente, Partida, \
    NominaPac, BienesServiciosInsumosPac, UnidadMedida
from settings import IVA, ARCHIVO_TIPO_GENERAL, SITE_ROOT
from sga.commonviews import adduserdata
from sga.funciones import log, MiPaginador, null_to_decimal, convertir_fecha, null_to_numeric, generar_nombre
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import Archivo


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    departamentopersona = persona.mi_departamento()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addperiodo':
            try:
                form = PeriodoPacForm(request.POST)
                if form.is_valid():
                    periodopac = PeriodoPac(anio=form.cleaned_data['anio'],
                                            descripcion=form.cleaned_data['descripcion'],
                                            observacion=form.cleaned_data['observacion'],
                                            permisoinicio=form.cleaned_data['permisoinicio'],
                                            permisofin=form.cleaned_data['permisofin'])
                    periodopac.save(request)
                    log(u'Registro nuevo Periodo PROFORMA PRESUPUESTARIA: %s' % periodopac, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'editperiodo':
            try:
                form = PeriodoPacForm(request.POST)
                if form.is_valid():
                    periodopac = PeriodoPac.objects.get(pk=int(request.POST['id']), status=True)
                    periodopac.descripcion = form.cleaned_data['descripcion']
                    periodopac.observacion = form.cleaned_data['observacion']
                    periodopac.permisoinicio = form.cleaned_data['permisoinicio']
                    periodopac.permisofin = form.cleaned_data['permisofin']
                    periodopac.save(request)
                    log(u'Registro modificado Periodo PROFORMA PRESUPUESTARIA: %s' % periodopac, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al editar los datos."})

        if action == 'deleteperiodo':
            try:
                periodopac = PeriodoPac.objects.get(pk=request.POST['id'], status=True)
                periodopac.status=False
                periodopac.save(request)
                log(u'Elimino Periodo PROFORMA PRESUPUESTARIA: %s' % periodopac, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'addtopeperiodo':
            try:
                periodopac = PeriodoPac.objects.get(pk=request.GET['id'], status=True)
                form = TopePeriodoPacForm(request.POST)
                if form.is_valid():

                    # if TopePeriodoPac.objects.filter(periodo=periodopac, departamento=)
                    topeperiodopac = TopePeriodoPac(periodo=periodopac,
                                                    departamento=form.cleaned_data['departamento'],
                                                    valor=null_to_decimal(form.cleaned_data['valor'],2),
                                                    estadotope=form.cleaned_data['estadotope'])
                    topeperiodopac.save(request)
                    log(u'Registro nuevo Tope Periodo Periodo PROFORMA PRESUPUESTARIA: %s - %s' % (periodopac,topeperiodopac), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Departamento ya tiene configurado Tope."})

        if action == 'edittopeperiodo':
            try:
                form = TopePeriodoPacForm(request.POST)
                if form.is_valid():
                    topeperiodopac = TopePeriodoPac.objects.get(pk=request.POST['id'], status=True)
                    topeperiodopac.valor = form.cleaned_data['valor']
                    topeperiodopac.estadotope = form.cleaned_data['estadotope']
                    topeperiodopac.save(request)
                    log(u'Registro nuevo Tope Periodo Periodo PROFORMA PRESUPUESTARIA: %s - %s' % (topeperiodopac.periodo, topeperiodopac), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al editar los datos."})

        if action == 'aprobar':
            try:
                periodo = PeriodoPac.objects.get(pk=request.POST['id'], status=True)
                periodo.aprobado = True
                periodo.fechaaprobado = datetime.now().date()
                periodo.save(request)
                log(u'Aprobo Pac: %s' % periodo, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar los datos."})

        if action == 'eliminar':
            try:
                pac = Pac.objects.get(pk=request.POST['id'], status=True)
                periodo = pac.periodo
                periodo.status = False
                periodo.save(request)
                log(u'Elimino Pac: %s' % pac, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar los datos."})

        # ajuste

        if action == 'addpacdepartamento':
            try:
                # , acciondocumento_id = int(request.POST['acciondocumento'])
                if Pac.objects.filter(periodo_id=int(request.POST['idperiodo']), departamento_id=int(request.POST['departamento']), acciondocumento=None, caracteristicas_id=int(request.POST['caracteristicas']), status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": "Registro Repetido."})
                # catalogobien = CatalogoBien.objects.filter(pk=int(request.POST['caracteristicas']), status=True)[0]
                pac = Pac(periodo_id=int(request.POST['idperiodo']),
                          departamento_id=int(request.POST['departamento']),
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
                          costounitario=null_to_decimal(request.POST['costounitario'], 2),
                          iva=null_to_decimal(request.POST['iva'], 2),
                          subtotal=null_to_decimal(request.POST['subtotal'], 2),
                          total=null_to_decimal(request.POST['total'], 2),
                          saldo=null_to_decimal(request.POST['total'], 2),
                          item=None,
                          fechaejecucion=None)
                pac.save(request)
                log(u'Registro nuevo caracteristicas productos PROFORMA PRESUPUESTARIA: %s' % pac, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'editpacdepartamento':
            try:
                pac = Pac.objects.get(pk=int(request.POST['idpac']), status=True)
                pac.cantidadenero = int(request.POST['cantidadenero'])
                pac.cantidadfebrero = int(request.POST['cantidadfebrero'])
                pac.cantidadmarzo = int(request.POST['cantidadmarzo'])
                pac.cantidadabril = int(request.POST['cantidadabril'])
                pac.cantidadmayo = int(request.POST['cantidadmayo'])
                pac.cantidadjunio = int(request.POST['cantidadjunio'])
                pac.cantidadjulio = int(request.POST['cantidadjulio'])
                pac.cantidadagosto = int(request.POST['cantidadagosto'])
                pac.cantidadseptiembre = int(request.POST['cantidadseptiembre'])
                pac.cantidadoctubre = int(request.POST['cantidadoctubre'])
                pac.cantidadnoviembre = int(request.POST['cantidadnoviembre'])
                pac.cantidaddiciembre = int(request.POST['cantidaddiciembre'])
                pac.unidadmedida_id=int(request.POST['unidadmedida'])
                pac.costounitario=null_to_decimal(request.POST['costounitario'],2)
                pac.iva=null_to_decimal(request.POST['iva'],2)
                pac.subtotal=null_to_decimal(request.POST['subtotal'],2)
                pac.total=null_to_decimal(request.POST['total'],2)
                pac.saldo=null_to_decimal(request.POST['total'],2)
                pac.fechaejecucion = None
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
                pac.estado = 3
                pac.save(request)
                log(u'Elimino caracteristicas productos PROFORMA PRESUPUESTARIA: %s' % pac, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'recuperarpac':
            try:
                pac = Pac.objects.get(pk=request.POST['id'])
                pac.status=True
                pac.estado = 2
                pac.save(request)
                log(u'Recupero caracteristicas productos PROFORMA PRESUPUESTARIA: %s' % pac, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        # if action == 'segmento':
        #     try:
        #         # data['acciondocumento'] = acciondocumento = AccionDocumento.objects.get(pk=int(request.POST['acciondocumento']), status=True)
        #         data['acciondocumento'] = acciondocumento = None
        #         data['pac'] = Pac.objects.filter(departamento_id=int(request.POST['departamento']), acciondocumento=acciondocumento, status=True).order_by('id')
        #         data['periodopac'] = periodopac = PeriodoPac.objects.filter(pk=request.POST['periodo'], status=True)[0]
        #         data['total_pac'] = null_to_numeric(Pac   .objects.filter(departamento_id=int(request.POST['departamento']), status=True).aggregate(total=Sum('total'))['total'])
        #         data['aprobado'] = periodopac.aprobado
        #         template = get_template("pac_pacrevision/segmento.html")
        #         json_content = template.render(data)
        #         return JsonResponse({"result": "ok", 'data': json_content})
        #     except Exception as ex:
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})
        #

        if action == 'segmento2':
            try:
                # data['acciondocumento'] = acciondocumento = AccionDocumento.objects.get(pk=int(request.POST['acciondocumento']), status=True)
                data['acciondocumento'] = acciondocumento = None
                data['periodopac'] = periodopac = PeriodoPac.objects.filter(pk=request.POST['periodo'], status=True)[0]
                if int(request.POST['departamento']) > 0:
                    data['pac'] = Pac.objects.filter(periodo=periodopac, departamento_id=int(request.POST['departamento']), acciondocumento=acciondocumento, status=True, estado__in=[1,2]).order_by('id')
                else:
                    data['pac'] = Pac.objects.filter(periodo=periodopac, acciondocumento=acciondocumento, status=True, estado__in=[1,2]).order_by('id')
                if int(request.POST['departamento']) > 0:
                    data['total_pac'] = null_to_numeric(Pac.objects.filter(periodo=periodopac, departamento_id=int(request.POST['departamento']), status=True).aggregate(total=Sum('total'))['total'])
                else:
                    data['total_pac'] = null_to_numeric(Pac.objects.filter(periodo=periodopac, status=True).aggregate(total=Sum('total'))['total'])
                data['aprobado'] = periodopac.aprobado
                template = get_template("pac_periodo/segmento2.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'segmento3':
            try:
                # data['acciondocumento'] = acciondocumento = AccionDocumento.objects.get(pk=int(request.POST['acciondocumento']), status=True)
                data['acciondocumento'] = acciondocumento = None
                if int(request.POST['departamento']) > 0:
                    data['pac_historial'] = Pac.objects.filter(departamento_id=int(request.POST['departamento']), acciondocumento=acciondocumento, status=False, estado__in=[3]).order_by('id')
                else:
                    data['pac_historial'] = Pac.objects.filter(acciondocumento=acciondocumento, status=False, estado__in=[3]).order_by('id')
                data['periodopac'] = periodopac = PeriodoPac.objects.filter(pk=request.POST['periodo'], status=True)[0]
                if int(request.POST['departamento']) > 0:
                    data['total_pac_historial'] = null_to_numeric(Pac.objects.filter(departamento_id=int(request.POST['departamento']), status=False, estado__in=[3]).aggregate(total=Sum('total'))['total'])
                else:
                    data['total_pac_historial'] = null_to_numeric(Pac.objects.filter(status=False, estado__in=[3]).aggregate(total=Sum('total'))['total'])
                data['aprobado'] = periodopac.aprobado
                template = get_template("pac_periodo/segmento3.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'addreforma':
            try:
                form = ReformaForm(request.POST)
                if form.is_valid():
                    datos = json.loads(request.POST['lista_items1'])
                    if len(datos) == 0:
                        return JsonResponse({"result": "bad", "mensaje": u"Seleccione al menos un campo del Contrato."})

                    reforma = Reforma(descripcion=form.cleaned_data['descripcion'],
                                      memorando=form.cleaned_data['memorando'],
                                      informe=form.cleaned_data['informe'],
                                      estadoreforma=form.cleaned_data['estadoreforma'],
                                      departamento=form.cleaned_data['departamento'],
                                      fecha=form.cleaned_data['fecha'])
                    reforma.save(request)
                    for elemento in datos:
                        if elemento['tipo'] == 'DISMINUCION':
                            pac = Pac.objects.filter(pk=int(elemento['id']), status=True)[0]
                            reformapac = ReformaPac(periodo_id=int(request.POST['id']),
                                                    departamento=pac.departamento,
                                                    acciondocumento=pac.acciondocumento,
                                                    caracteristicas=pac.caracteristicas,
                                                    cantidad=pac.cantidad,
                                                    unidadmedida=pac.unidadmedida,
                                                    costounitario=pac.costounitario,
                                                    total=elemento['valor'],
                                                    item=pac.item,
                                                    fechaejecucion=pac.fechaejecucion,
                                                    programa=pac.programa,
                                                    actividad=pac.actividad,
                                                    fuente=pac.fuente,
                                                    tiporeforma=2)
                            reformapac.save(request)
                            # pac.saldo=pac.saldo - Decimal(elemento['valor']).quantize(Decimal('.01'))
                            # pac.save(request)
                        else:
                            catalogobien = CatalogoBien.objects.filter(pk=int(elemento['caracteristica']), status=True)[0]
                            reformapac = ReformaPac(periodo_id=int(request.POST['id']),
                                                    departamento=form.cleaned_data['departamento'],
                                                    acciondocumento_id=int(elemento['actividadproyecto']),
                                                    caracteristicas_id=int(elemento['caracteristica']),
                                                    cantidad=int(elemento['cantidad']),
                                                    unidadmedida_id=int(elemento['unidadmedida']),
                                                    costounitario=null_to_decimal(elemento['costounitario'],2),
                                                    total=null_to_decimal(elemento['total'],2),
                                                    item=catalogobien.item,
                                                    fechaejecucion=convertir_fecha(elemento['fechaejecucion']),
                                                    programa_id=int(elemento['programa']),
                                                    actividad_id=int(elemento['actividad']),
                                                    fuente_id=int(elemento['fuente']),
                                                    tiporeforma=1)
                            reformapac.save(request)
                            if Pac.objects.filter(periodo_id=int(request.POST['id']), departamento=form.cleaned_data['departamento'], acciondocumento_id=int(elemento['actividadproyecto']), caracteristicas_id=int(elemento['caracteristica']),unidadmedida_id=int(elemento['unidadmedida']), costounitario=null_to_decimal(elemento['costounitario'],2), item=catalogobien.item, fechaejecucion=convertir_fecha(elemento['fechaejecucion']), programa_id=int(elemento['programa']), actividad_id=int(elemento['actividad']), fuente_id=int(elemento['fuente']), status=True).exists():
                                pac = Pac.objects.filter(periodo_id=int(request.POST['id']), departamento=form.cleaned_data['departamento'], acciondocumento_id=int(elemento['actividadproyecto']), caracteristicas_id=int(elemento['caracteristica']),unidadmedida_id=int(elemento['unidadmedida']), costounitario=null_to_decimal(elemento['costounitario'],2), item=catalogobien.item, fechaejecucion=convertir_fecha(elemento['fechaejecucion']), programa_id=int(elemento['programa']), actividad_id=int(elemento['actividad']), fuente_id=int(elemento['fuente']), status=True)[0]
                                pac.cantidad = pac.cantidad + int(elemento['cantidad'])
                                pac.total = pac.total + null_to_decimal(elemento['total'],2)
                                # pac.saldo = pac.saldo + float(elemento['total'])
                                pac.save(request)
                            else:
                                pac = Pac(periodo_id=int(request.POST['id']),
                                          departamento=form.cleaned_data['departamento'],
                                          acciondocumento_id=int(elemento['actividadproyecto']),
                                          caracteristicas_id=int(elemento['caracteristica']),
                                          cantidad=int(elemento['cantidad']),
                                          unidadmedida_id=int(elemento['unidadmedida']),
                                          costounitario=null_to_decimal(elemento['costounitario'],2),
                                          total=null_to_decimal(elemento['total'],2),
                                          saldo=null_to_decimal(elemento['total'],2),
                                          item=catalogobien.item,
                                          fechaejecucion=convertir_fecha(elemento['fechaejecucion']),
                                          programa_id=int(elemento['programa']),
                                          actividad_id=int(elemento['actividad']),
                                          fuente_id=int(elemento['fuente']),
                                          estadoitem=2,
                                          tipo=2)
                                pac.save(request)
                    log(u'Registro nuevo Reforma: %s' % reforma, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        # codificacion
        if action == 'importar':
            mensaje = None
            try:
                form = ImportarArchivoForm(request.POST, request.FILES)
                newfile = None
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
                    pac=None

                    hoy = datetime.now().date()
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("subirpac_", nfile._name)
                    archivo = Archivo(nombre='SUBIR PROFORMA PRESUPUESTARIA MODIFICACION PRESUPUESTO',
                                      fecha=datetime.now().date(),
                                      archivo=nfile,
                                      tipo_id=ARCHIVO_TIPO_GENERAL)
                    archivo.save(request)
                    workbook = xlrd.open_workbook(archivo.archivo.file.name)
                    sheet = workbook.sheet_by_index(0)
                    linea = 1
                    for rowx in range(sheet.nrows):
                        if linea >= 6:
                            cols = sheet.row_values(rowx)
                            # PAC
                            partidaprograma = None
                            if (cols[3]) != '':
                                if PartidaPrograma.objects.filter(codigo=int(cols[3]), status=True).exists():
                                    partidaprograma = PartidaPrograma.objects.filter(codigo=int(cols[3]), status=True)[0]

                            partidaactividad = None
                            if (cols[4]) != '':
                                if PartidaActividad.objects.filter(codigo=int(cols[4]), status=True).exists():
                                    partidaactividad = PartidaActividad.objects.filter(codigo=int(cols[4]), status=True)[0]

                            partidafuente = None
                            if (cols[5]) != '':
                                if PartidaFuente.objects.filter(codigo=int(cols[5]), status=True).exists():
                                    partidafuente = PartidaFuente.objects.filter(codigo=int(cols[5]), status=True)[0]

                            partida = None
                            if (cols[6]) != '':
                                if Partida.objects.filter(codigo=str(int(cols[6])), status=True).exists():
                                    partida = Partida.objects.filter(codigo=str(int(cols[6])), status=True)[0]

                            cantidad = 0
                            if cols[7] !='':
                                cantidad = int(cols[7])
                            costo = 0
                            if cols[9] !='':
                                costo = null_to_decimal((cols[9]),2)
                            subtotal = 0
                            if cols[10] !='':
                                subtotal = null_to_decimal((cols[10]),2)
                            iva = 0
                            if cols[11] !='':
                                iva = null_to_decimal((cols[11]),2)
                            total = 0
                            if cols[12] !='':
                                total = null_to_decimal((cols[12]),2)
                            cantidadenero = 0
                            if cols[13] !='':
                                cantidadenero = null_to_decimal((cols[13]),2)
                            cantidadfebrero = 0
                            if cols[16] !='':
                                cantidadfebrero = null_to_decimal((cols[16]),2)
                            cantidadmarzo = 0
                            if cols[19] !='':
                                cantidadmarzo = null_to_decimal((cols[19]),2)
                            cantidadabril = 0
                            if cols[22] !='':
                                cantidadabril = null_to_decimal((cols[22]),2)
                            cantidadmayo = 0
                            if cols[25] !='':
                                cantidadmayo = null_to_decimal((cols[25]),2)
                            cantidadjunio = 0
                            if cols[28] !='':
                                cantidadjunio = null_to_decimal((cols[28]),2)
                            cantidadjulio = 0
                            if cols[31] !='':
                                cantidadjulio = null_to_decimal((cols[31]),2)
                            cantidadagosto = 0
                            if cols[34] !='':
                                cantidadagosto = null_to_decimal((cols[34]),2)
                            cantidadseptiembre = 0
                            if cols[37] !='':
                                cantidadseptiembre = null_to_decimal((cols[37]),2)
                            cantidadoctubre = 0
                            if cols[40] !='':
                                cantidadoctubre = null_to_decimal((cols[40]),2)
                            cantidadnoviembre = 0
                            if cols[43] !='':
                                cantidadnoviembre = null_to_decimal((cols[43]),2)
                            cantidaddiciembre = 0
                            if cols[46] !='':
                                cantidaddiciembre = null_to_decimal((cols[46]),2)

                            pac = Pac.objects.get(pk=int(cols[100]), status=True)
                            if cols[50].strip().upper() == 'N':
                                pac.item = partida
                                pac.programa = partidaprograma
                                pac.actividad = partidaactividad
                                pac.fuente = partidafuente
                                pac.costounitario = costo
                                pac.subtotal = subtotal
                                pac.iva = iva
                                pac.total = total
                                pac.cantidadenero = cantidadenero
                                pac.cantidadfebrero = cantidadfebrero
                                pac.cantidadmarzo = cantidadmarzo
                                pac.cantidadabril = cantidadabril
                                pac.cantidadmayo = cantidadmayo
                                pac.cantidadjunio = cantidadjunio
                                pac.cantidadjulio = cantidadjulio
                                pac.cantidadagosto = cantidadagosto
                                pac.cantidadseptiembre = cantidadseptiembre
                                pac.cantidadoctubre = cantidadoctubre
                                pac.cantidadnoviembre = cantidadnoviembre
                                pac.cantidaddiciembre = cantidaddiciembre
                                pac.save(request)
                            else:
                                if cols[50].strip().upper() == 'S':
                                    pac.status = False
                                    pac.estado = 3
                                    pac.save(request)
                                    log(u'Elimino caracteristicas productos PROFORMA PRESUPUESTARIA: %s' % pac, request, "del")
                                else:
                                    if cols[50].strip().upper() == 'I':
                                        departamentoingresado = Departamento.objects.get(nombre=cols[0].strip())
                                        bienesserviciosinsumospac = BienesServiciosInsumosPac.objects.get(descripcion=cols[2].strip())
                                        unidadmedida = UnidadMedida.objects.get(nombre=cols[8].strip())
                                        pac = Pac(periodo_id=int(request.POST['idperiodo']),
                                                  departamento=departamentoingresado,
                                                  # acciondocumento_id=int(request.POST['acciondocumento']),
                                                  caracteristicas=bienesserviciosinsumospac,
                                                  cantidadenero=cantidadenero,
                                                  cantidadfebrero=cantidadfebrero,
                                                  cantidadmarzo=cantidadmarzo,
                                                  cantidadabril=cantidadabril,
                                                  cantidadmayo=cantidadmayo,
                                                  cantidadjunio=cantidadjunio,
                                                  cantidadjulio=cantidadjulio,
                                                  cantidadagosto=cantidadagosto,
                                                  cantidadseptiembre=cantidadseptiembre,
                                                  cantidadoctubre=cantidadoctubre,
                                                  cantidadnoviembre=cantidadnoviembre,
                                                  cantidaddiciembre=cantidaddiciembre,
                                                  unidadmedida=unidadmedida,
                                                  costounitario=costo,
                                                  iva=iva,
                                                  subtotal=subtotal,
                                                  total=total,
                                                  saldo=total,
                                                  item = partida,
                                                  programa = partidaprograma,
                                                  actividad = partidaactividad,
                                                  fuente = partidafuente,
                                                  fechaejecucion=None)
                                        pac.save(request)

                                    else:
                                        mensaje = "la fila %s no tiene N, S, I" % linea
                                        raise NameError('No contiene modificacion de presupuesto')


                        linea += 1

                    if pac:
                        log(u'Importo plantilla PROFORMA PRESUPUESTARIA: %s' % pac , request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        mensaje = "No contiene modificacion de presupuesto"
                        raise NameError('No contiene modificacion de presupuesto')
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos." if not mensaje else mensaje})



        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addperiodo':
                try:
                    data['title'] = u'Nuevo Periodo PROFORMA PRESUPUESTARIA'
                    data['form'] = PeriodoPacForm()
                    return render(request, "pac_periodo/addperiodo.html", data)
                except Exception as ex:
                    pass

            if action == 'editperiodo':
                try:
                    data['title'] = u'Modificación Periodo PROFORMA PRESUPUESTARIA'
                    data['periodopac'] = periodopac = PeriodoPac.objects.get(pk=request.GET['id'], status=True)
                    form = PeriodoPacForm(initial={'anio': periodopac.anio,
                                                   'descripcion': periodopac.descripcion,
                                                   'observacion': periodopac.observacion,
                                                   'permisoinicio': periodopac.permisoinicio,
                                                   'permisofin': periodopac.permisofin})
                    form.editar()
                    data['form'] = form
                    return render(request, "pac_periodo/editperiodo.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteperiodo':
                try:
                    data['title'] = u'Eliminar Periodo PROFORMA PRESUPUESTARIA'
                    data['periodopac'] = PeriodoPac.objects.get(pk=request.GET['id'], status=True)
                    return render(request, 'pac_periodo/deleteperiodo.html', data)
                except Exception as ex:
                    pass

            if action == 'topedepartamento':
                try:
                    data['periodopac'] = periodopac = PeriodoPac.objects.get(pk=request.GET['id'], status=True)
                    data['title'] = u'Configuración Techo Presupuestario ' + periodopac.descripcion
                    data['topeperiodopacs'] = topeperiodopac = TopePeriodoPac.objects.filter(periodo=periodopac, status=True)
                    return render(request, "pac_periodo/topedepartamento.html", data)
                except Exception as ex:
                    pass

            if action == 'addtopeperiodo':
                try:
                    data['title'] = u'Nuevo Tope Periodo'
                    data['periodopac'] = periodopac = PeriodoPac.objects.get(pk=request.GET['id'], status=True)

                    form = TopePeriodoPacForm()
                    form.addtopeperiodo(periodopac)
                    data['form'] = form

                    return render(request, "pac_periodo/addtopeperiodo.html", data)
                except Exception as ex:
                    pass

            if action == 'edittopeperiodo':
                try:
                    data['title'] = u'Modificación Tope Periodo'
                    data['topeperiodopac'] = topeperiodopac = TopePeriodoPac.objects.get(pk=request.GET['id'], status=True)
                    data['periodopac'] = topeperiodopac.periodo
                    form = TopePeriodoPacForm(initial={'departamento': topeperiodopac.departamento,
                                                       'valor': topeperiodopac.valor,
                                                       'estadotope': topeperiodopac.estadotope})
                    form.editar()
                    data['form'] = form
                    return render(request, "pac_periodo/edittopeperiodo.html", data)
                except Exception as ex:
                    pass

            if action == 'aprobar':
                try:
                    data['title'] = u'APROBAR PROFORMA PRESUPUESTARIA UNEMI'
                    data['periodopac'] = PeriodoPac.objects.get(pk=int(request.GET['id']), status=True)
                    return render(request, "pac_periodo/aprobar.html", data)
                except Exception as ex:
                    pass

            # ajuste
            if action == 'revisionpac':
                try:
                    data['title'] = u'PROFORMA PRESUPUESTARIA UNIVERSIDAD ESTATAL DE MILAGRO '
                    data['periodopac'] = periodopac = PeriodoPac.objects.filter(pk=request.GET['id'], status=True)[0]
                    # data['departamentos'] = departamentos = Departamento.objects.filter(status=True, objetivoestrategico__isnull=False, objetivoestrategico__periodopoa__anio=periodopac.anio).distinct()
                    data['departamentos'] = departamentos = Departamento.objects.filter(status=True, pac__isnull=False).distinct()

                    search = None
                    idobjetivooperativo = 0
                    idindicadorpoa = 0
                    idacciondocumento = 0
                    iddepartamento = 0
                    objetivosoperativos = None
                    indicadorpoa = None
                    acciondocumento = None
                    # departamento
                    if 'iddepartamento' in request.GET:
                        iddepartamento = request.GET['iddepartamento']
                        departamento = Departamento.objects.filter(pk=int(iddepartamento), status=True)[0]
                    else:
                        departamento = departamentos[0]
                        iddepartamento = departamento.id

                    # objetivo opertaivo
                    data['objetivosoperativos'] = objetivosoperativos1 = departamento.objetivos_operativos(periodopac.anio)
                    if 'idobjetivooperativo' in request.GET:
                        idobjetivooperativo = request.GET['idobjetivooperativo']
                        # data['objetivosoperativos'] = objetivosoperativos1 = ObjetivoOperativo.objects.filter(pk=int(idobjetivooperativo))
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
                    data['iddepartamento'] = iddepartamento

                    # acciondocumento = AccionDocumento.objects.filter(indicadorpoa__objetivooperativo=objetivosoperativo)[0]
                    if 'acciondocumento' in request.GET:
                        search = request.GET['acciondocumento']
                    if search:
                        acciondocumento = AccionDocumento.objects.filter(pk=search)[0]
                        # pac = Pac.objects.filter(departamento=departamento,acciondocumento=acciondocumento , status=True)
                        data['idacciondocumento'] = acciondocumento.id
                    else:
                        acciondocumento1 = acciondocumento
                        # pac = Pac.objects.filter(departamento=departamento,acciondocumento=acciondocumento1 , status=True)
                    data['aprobado'] = periodopac.aprobado
                    data['form2'] = PacForm()
                    data['IVA'] = IVA
                    data['nominapacs'] = NominaPac.objects.filter(status=True, periodopac=periodopac)
                    return render(request, "pac_periodo/revisionpac.html", data)
                except Exception as ex:
                    pass

            if action == 'deletepac':
                try:
                    data['title'] = u'Eliminar Caracteristica Producto Proforma Presupuestaria'
                    data['pac'] = Pac.objects.get(pk=request.GET['id'], status=True)
                    return render(request, 'pac_periodo/deletepac.html', data)
                except Exception as ex:
                    pass

            if action == 'recuperarpac':
                try:
                    data['title'] = u'Recuperar Caracteristica Producto Proforma Presupuestaria'
                    data['pac'] = Pac.objects.get(pk=request.GET['id'])
                    return render(request, 'pac_periodo/recuperarpac.html', data)
                except Exception as ex:
                    pass

            if action == 'addreforma':
                try:
                    data['title'] = u'Nuevo Reforma'
                    data['periodopac'] = periodopac = PeriodoPac.objects.get(pk=request.GET['idperiodo'], status=True)
                    data['pacs'] = Pac.objects.filter(periodo=periodopac, status=True).order_by('-id')
                    data['departamentos'] = departamentos = Departamento.objects.filter(status=True, objetivoestrategico__isnull=False, objetivoestrategico__periodopoa__anio=periodopac.anio).distinct()
                    form = ReformaForm()
                    form.adicionar(departamentos)
                    data['form'] = form
                    form2 = PacReformaForm()
                    form2.adicionar()
                    data['form2'] = form2

                    search = None
                    idobjetivooperativo = 0
                    idindicadorpoa = 0
                    idacciondocumento = 0
                    iddepartamento = 0

                    # departamento
                    departamento = departamentos[0]
                    iddepartamento = departamento.id

                    # objetivo opertaivo
                    data['objetivosoperativos'] = objetivosoperativos1 = departamento.objetivos_operativos(periodopac.anio)
                    objetivosoperativos = objetivosoperativos1[0]
                    idobjetivooperativo = objetivosoperativos.id

                    # indicador poa
                    indicadorpoa = objetivosoperativos.indicadorpoa_set.filter(status=True)[0]
                    idindicadorpoa = indicadorpoa.id

                    # accion documento
                    acciondocumento = indicadorpoa.acciondocumento_set.filter(status=True)[0]
                    idacciondocumento = acciondocumento.id

                    data['idobjetivooperativo'] = idobjetivooperativo
                    data['idindicadorpoa'] = idindicadorpoa
                    data['idacciondocumento'] = idacciondocumento
                    data['iddepartamento'] = iddepartamento

                    return render(request, "pac_periodo/addreforma.html", data)
                except Exception as ex:
                    pass

            # codificacion
            if action == 'descargar':
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
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 12, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(2, 2, 9, 49, u'PROYECCIÓN DE ADQUISICIÓN/CONTRATACIÓN EN PORCENTAJES', style)
                    ws.write_merge(3, 3, 13, 15, u'ENERO', style)
                    ws.write_merge(3, 3, 16, 18, u'FEBRERO', style)
                    ws.write_merge(3, 3, 19, 21, u'MARZO', style)
                    ws.write_merge(3, 3, 22, 24, u'ABRIL', style)
                    ws.write_merge(3, 3, 25, 27, u'MAYO', style)
                    ws.write_merge(3, 3, 28, 30, u'JUNIO', style)
                    ws.write_merge(3, 3, 31, 33, u'JULIO', style)
                    ws.write_merge(3, 3, 34, 36, u'AGOSTO', style)
                    ws.write_merge(3, 3, 37, 39, u'SEPTIEMBRE', style)
                    ws.write_merge(3, 3, 40, 42, u'OCTUBRE', style)
                    ws.write_merge(3, 3, 43, 45, u'NOVIEMBRE', style)
                    ws.write_merge(3, 3, 46, 48, u'DICIEMBRE', style)

                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=proforma_presupuestaria_' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"DEPARTAMENTO", 10000),
                        (u"ITEM BIEN Y/O SERVICIO", 5000),
                        (u"DETALLE DEL PRODUCTO (Descripción de la contratación)", 10000),
                        (u"PROGRAMA", 2000),
                        (u"ACTIVIDAD", 2000),
                        (u"FUENTE", 2000),
                        (u"ITEM", 2000),
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
                        (u"ELIMINAR S/N", 3000),
                    ]
                    row_num = 4

                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], style)
                        ws.col(col_num).width = columns[col_num][1]
                    ws.write(row_num, 100, "CODIGO", style)
                    pacs = Pac.objects.filter(periodo=periodopac, status=True, estado__in=[1, 2]).order_by('departamento', 'caracteristicas')
                    row_num = 5
                    total_pac = 0
                    for r in pacs:
                        codigoregistro = r.id
                        campo0 = r.departamento.nombre
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

                        programa = ''
                        if r.programa:
                            programa = r.programa.codigo
                        actividad = ''
                        if r.actividad:
                            actividad = r.actividad.codigo
                        fuente = ''
                        if r.fuente:
                            fuente = r.fuente.codigo
                        item = ''
                        if r.item:
                            item = r.item.codigo

                        ws.write(row_num, 0, campo0, style2)
                        ws.write(row_num, 1, campo1, style2)
                        ws.write(row_num, 2, campo2, style2)
                        ws.write(row_num, 3, programa, style2)
                        ws.write(row_num, 4, actividad, style2)
                        ws.write(row_num, 5, fuente, style2)
                        ws.write(row_num, 6, item, style2)
                        ws.write(row_num, 7, campo3, style1)
                        ws.write(row_num, 8, campo4, style2)
                        ws.write(row_num, 9, campo5, style1)
                        ws.write(row_num, 10, campo6, style1)
                        ws.write(row_num, 11, campo7, style1)
                        ws.write(row_num, 12, campo8, style1)
                        ws.write(row_num, 13, cantidadenero, style1)
                        ws.write(row_num, 14, campo9, style1)
                        ws.write(row_num, 15, montoenero, style1)
                        ws.write(row_num, 16, cantidadfebrero, style1)
                        ws.write(row_num, 17, campo10, style1)
                        ws.write(row_num, 18, montofebrero, style1)
                        ws.write(row_num, 19, cantidadmarzo, style1)
                        ws.write(row_num, 20, campo11, style1)
                        ws.write(row_num, 21, montomarzo, style1)
                        ws.write(row_num, 22, cantidadabril, style1)
                        ws.write(row_num, 23, campo12, style1)
                        ws.write(row_num, 24, montoabril, style1)
                        ws.write(row_num, 25, cantidadmayo, style1)
                        ws.write(row_num, 26, campo13, style1)
                        ws.write(row_num, 27, montomayo, style1)
                        ws.write(row_num, 28, cantidadjunio, style1)
                        ws.write(row_num, 29, campo14, style1)
                        ws.write(row_num, 30, montojunio, style1)
                        ws.write(row_num, 31, cantidadjulio, style1)
                        ws.write(row_num, 32, campo15, style1)
                        ws.write(row_num, 33, montojulio, style1)
                        ws.write(row_num, 34, cantidadagosto, style1)
                        ws.write(row_num, 35, campo16, style1)
                        ws.write(row_num, 36, montoagosto, style1)
                        ws.write(row_num, 37, cantidadseptiembre, style1)
                        ws.write(row_num, 38, campo17, style1)
                        ws.write(row_num, 39, montoseptiembre, style1)
                        ws.write(row_num, 40, cantidadoctubre, style1)
                        ws.write(row_num, 41, campo18, style1)
                        ws.write(row_num, 42, montooctubre, style1)
                        ws.write(row_num, 43, cantidadnoviembre, style1)
                        ws.write(row_num, 44, campo19, style1)
                        ws.write(row_num, 45, montonoviembre, style1)
                        ws.write(row_num, 46, cantidaddiciembre, style1)
                        ws.write(row_num, 47, campo20, style1)
                        ws.write(row_num, 48, montodiciembre, style1)
                        ws.write(row_num, 49, porcentaje + diferenciasuma - diferenciaresta, style1)
                        ws.write(row_num, 50, "N", style1)
                        ws.write(row_num, 100, codigoregistro, style1)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'descargarexcel':
                try:
                    periodopac = PeriodoPac.objects.get(pk=int(request.GET['periodo']))
                    departamentos = Pac.objects.values_list('departamento__id', flat=True).filter(periodo=periodopac, status=True).distinct()
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
                    ws.write_merge(0, 0, 0, 49, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 49, u'MATRIZ DE LEVANTAMIENTO DE INFORMACIÓN PARA ESTRUCTURA DE PROFORMA PRESUPUESTARIA %s' % periodopac.anio,title2)
                    ws.write_merge(2, 2, 0, 49, u'UNIDAD ORGANIZACIONAL: UNEMI', title2)
                    ws.write_merge(3, 3, 9, 49, u'PROYECCIÓN DE ADQUISICIÓN/CONTRATACIÓN EN PORCENTAJES', style)
                    ws.write_merge(4, 4, 13, 15, u'ENERO', style)
                    ws.write_merge(4, 4, 16, 18, u'FEBRERO', style)
                    ws.write_merge(4, 4, 19, 21, u'MARZO', style)
                    ws.write_merge(4, 4, 22, 24, u'ABRIL', style)
                    ws.write_merge(4, 4, 25, 27, u'MAYO', style)
                    ws.write_merge(4, 4, 28, 30, u'JUNIO', style)
                    ws.write_merge(4, 4, 31, 33, u'JULIO', style)
                    ws.write_merge(4, 4, 34, 36, u'AGOSTO', style)
                    ws.write_merge(4, 4, 37, 39, u'SEPTIEMBRE', style)
                    ws.write_merge(4, 4, 40, 42, u'OCTUBRE', style)
                    ws.write_merge(4, 4, 43, 45, u'NOVIEMBRE', style)
                    ws.write_merge(4, 4, 46, 48, u'DICIEMBRE', style)

                    columns = [
                        (u"DEPARTAMENTO", 10000),
                        (u"ITEM BIEN Y/O SERVICIO", 5000),
                        (u"DETALLE DEL PRODUCTO (Descripción de la contratación)", 10000),
                        (u"PROGRAMA", 2000),
                        (u"ACTIVIDAD", 2000),
                        (u"FUENTE", 2000),
                        (u"ITEM", 2000),
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
                    pacs = Pac.objects.filter(periodo=periodopac, status=True, estado__in=[1,2]).order_by('departamento','caracteristicas')
                    row_num = 6
                    total_pac = 0
                    for r in pacs:
                        campo0= r.departamento.nombre
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

                        programa = ''
                        if r.programa:
                            programa = r.programa.codigo
                        actividad = ''
                        if r.actividad:
                            actividad = r.actividad.codigo
                        fuente = ''
                        if r.fuente:
                            fuente = r.fuente.codigo
                        item = ''
                        if r.item:
                            item = r.item.codigo

                        ws.write(row_num, 0, campo0, style2)
                        ws.write(row_num, 1, campo1, style2)
                        ws.write(row_num, 2, campo2, style2)
                        ws.write(row_num, 3, programa, style2)
                        ws.write(row_num, 4, actividad, style2)
                        ws.write(row_num, 5, fuente, style2)
                        ws.write(row_num, 6, item, style2)
                        ws.write(row_num, 7, campo3, style1)
                        ws.write(row_num, 8, campo4, style2)
                        ws.write(row_num, 9, campo5, style1)
                        ws.write(row_num, 10, campo6, style1)
                        ws.write(row_num, 11, campo7, style1)
                        ws.write(row_num, 12, campo8, style1)
                        ws.write(row_num, 13, cantidadenero, style1)
                        ws.write(row_num, 14, campo9, style1)
                        ws.write(row_num, 15, montoenero, style1)
                        ws.write(row_num, 16, cantidadfebrero, style1)
                        ws.write(row_num, 17, campo10, style1)
                        ws.write(row_num, 18, montofebrero, style1)
                        ws.write(row_num, 19, cantidadmarzo, style1)
                        ws.write(row_num, 20, campo11, style1)
                        ws.write(row_num, 21, montomarzo, style1)
                        ws.write(row_num, 22, cantidadabril, style1)
                        ws.write(row_num, 23, campo12, style1)
                        ws.write(row_num, 24, montoabril, style1)
                        ws.write(row_num, 25, cantidadmayo, style1)
                        ws.write(row_num, 26, campo13, style1)
                        ws.write(row_num, 27, montomayo, style1)
                        ws.write(row_num, 28, cantidadjunio, style1)
                        ws.write(row_num, 29, campo14, style1)
                        ws.write(row_num, 30, montojunio, style1)
                        ws.write(row_num, 31, cantidadjulio, style1)
                        ws.write(row_num, 32, campo15, style1)
                        ws.write(row_num, 33, montojulio, style1)
                        ws.write(row_num, 34, cantidadagosto, style1)
                        ws.write(row_num, 35, campo16, style1)
                        ws.write(row_num, 36, montoagosto, style1)
                        ws.write(row_num, 37, cantidadseptiembre, style1)
                        ws.write(row_num, 38, campo17, style1)
                        ws.write(row_num, 39, montoseptiembre, style1)
                        ws.write(row_num, 40, cantidadoctubre, style1)
                        ws.write(row_num, 41, campo18, style1)
                        ws.write(row_num, 42, montooctubre, style1)
                        ws.write(row_num, 43, cantidadnoviembre, style1)
                        ws.write(row_num, 44, campo19, style1)
                        ws.write(row_num, 45, montonoviembre, style1)
                        ws.write(row_num, 46, cantidaddiciembre, style1)
                        ws.write(row_num, 47, campo20, style1)
                        ws.write(row_num, 48, montodiciembre, style1)
                        ws.write(row_num, 49, porcentaje + diferenciasuma - diferenciaresta, style1)
                        # while i < len(r):
                        #     # ws.write(row_num, i, r[i], font_style)
                        #     # ws.col(i).width = columns[i][1]
                        row_num += 1
                        total_pac += r.total
                    ws.write(row_num, 12, total_pac, style)

                    i = 0
                    for d in departamentos:
                        # xlwt.Worksheet.insert_bitmap('A1',SITE_ROOT+'\\statict\\images\\iconos\\word.png',1,1)
                        i += 1
                        depa = Departamento.objects.get(pk=int(d))
                        ws = wb.add_sheet(str(i))
                        ws.write_merge(0, 0, 0, 44, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                        ws.write_merge(1, 1, 0, 44, u'MATRIZ DE LEVANTAMIENTO DE INFORMACIÓN PARA ESTRUCTURA DE PROFORMA PRESUPUESTARIA %s' % periodopac.anio, title2)
                        ws.write_merge(2, 2, 0, 44, u'UNIDAD ORGANIZACIONAL: %s' % depa.nombre, title2)
                        # response = HttpResponse(content_type="application/ms-excel")
                        # response['Content-Disposition'] = 'attachment; filename=proforma_presupuestaria_' + random.randint(1, 10000).__str__() + '.xls'
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
                        # pac_fechas= Pac.objects.filter(periodo=periodopac, departamento=depa, status=True, estado__in=[1,2])[0]
                        # fecha_creacion1 = pac_fechas.primera_creacion(depa)
                        # fecha_modificacion1 = pac_fechas.ultima_modificacion(depa)
                        fecha_creacion1 = ''
                        fecha_modificacion1 = ''
                        pacs = Pac.objects.filter(periodo=periodopac, departamento=depa, status=True, estado__in=[1,2]).distinct('caracteristicas')
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
                                campo9 = round(((r.cantidadenero/r.cantidad())*100),2)
                                porcentaje += campo9
                            campo10 = ''
                            if r.cantidadfebrero > 0:
                                campo10 = round(((r.cantidadfebrero/r.cantidad())*100),2)
                                porcentaje += campo10
                            campo11 = ''
                            if r.cantidadmarzo > 0:
                                campo11 = round(((r.cantidadmarzo/r.cantidad())*100),2)
                                porcentaje += campo11
                            campo12 = ''
                            if r.cantidadabril > 0:
                                campo12 = round(((r.cantidadabril/r.cantidad())*100),2)
                                porcentaje += campo12
                            campo13 = ''
                            if r.cantidadmayo > 0:
                                campo13 = round(((r.cantidadmayo/r.cantidad())*100),2)
                                porcentaje += campo13
                            campo14 = ''
                            if r.cantidadjunio > 0:
                                campo14 = round(((r.cantidadjunio/r.cantidad())*100),2)
                                porcentaje += campo14
                            campo15 = ''
                            if r.cantidadjulio > 0:
                                campo15 = round(((r.cantidadjulio/r.cantidad())*100),2)
                                porcentaje += campo15
                            campo16 = ''
                            if r.cantidadagosto > 0:
                                campo16 = round(((r.cantidadagosto/r.cantidad())*100),2)
                                porcentaje += campo16
                            campo17 = ''
                            if r.cantidadseptiembre > 0:
                                campo17 = round(((r.cantidadseptiembre/r.cantidad())*100),2)
                                porcentaje += campo17
                            campo18 = ''
                            if r.cantidadoctubre > 0:
                                campo18 = round(((r.cantidadoctubre/r.cantidad())*100),2)
                                porcentaje += campo18
                            campo19 = ''
                            if r.cantidadnoviembre > 0:
                                campo19 = round(((r.cantidadnoviembre/r.cantidad())*100),2)
                                porcentaje += campo19
                            campo20 = ''
                            if r.cantidaddiciembre > 0:
                                campo20 = round(((r.cantidaddiciembre/r.cantidad())*100),2)
                                porcentaje += campo20
                            diferenciaresta = 0
                            diferenciasuma = 0
                            if porcentaje != 100:
                                if porcentaje > 100:
                                    diferenciaresta = round((porcentaje - 100),2)
                                else:
                                    diferenciasuma = round((100 - porcentaje),2)
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
                        row_num += 5
                        ws.write(row_num, 0, u'Fecha de creación: %s' % fecha_creacion1, style)
                        row_num += 1
                        ws.write(row_num, 0,  u'Fecha de modificación: %s' %  fecha_modificacion1, style)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'importar':
                try:
                    data['title'] = u'Subir Modificaciones Presupuestaria'
                    data['idperiodo'] = int(request.GET['idperiodo'])
                    data['form'] = ImportarArchivoForm()
                    return render(request, "pac_periodo/importar.html", data)
                except Exception as ex:
                    pass

            if action == 'pdf':
                try:
                    data['periodopac'] = periodopac = PeriodoPac.objects.get(pk=int(request.GET['periodo']))
                    data['departamento'] = departamentopersona.nombre
                    data['jefe'] = persona.nombre_titulo()
                    data['pacs'] =  pacs = Pac.objects.filter(periodo=periodopac, status=True, estado__in=[1, 2]).order_by('departamento', 'caracteristicas')
                    return conviert_html_to_pdf(
                        'pac_periodo/pdfproforma.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Periodo Proforma Presupuestaria'
            search = None
            tipo = None
            if 's' in request.GET:
                search = request.GET['s']
            if search:
                periodopac = PeriodoPac.objects.filter(Q(descripcion__icontains=search) | Q(anio__icontains=search), status=True, id__gt=5).order_by('-id')
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
            return render(request, 'pac_periodo/view.html', data)