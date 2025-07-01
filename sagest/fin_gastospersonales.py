# -*- coding: UTF-8 -*-
import json
import pandas as pd
import os
from datetime import datetime
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction, connection
from django.db.models import Q, Sum
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from xlwt import *
from decorators import last_access, secure_module
from sagest.forms import PeriodoGastosForm, PoblacionForm, GastosPersonalesForm
from sagest.models import GastosPersonales, PeriodoGastosPersonales, \
    TablaImpuestoRenta, ResumenMesGastosPersonales, DeclaracionSriAnual, DetallePeriodoRol
from settings import PORCENTAJE_SEGURO, NOMINA_RUBRO_SOBRESUELDOS, NOMINA_RUBRO_DECIMOTERCER, \
    NOMINA_RUBRO_DECIMOCUARTO, NOMINA_RUBRO_FONDORESERVA, NOMINA_RUBRO_SEGURO_ID, NOMINA_RUBRO_SUELDOS,  SITE_STORAGE
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import log, MiPaginador, generar_nombre
from sga.models import TIPO_CELULAR, Persona
from sga.templatetags.sga_extras import encrypt
from utils.filtros_genericos import filtro_persona, filtro_persona_select


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    hoy = datetime.now()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addgasto':
            try:
                persona1 = Persona.objects.get(pk=int(request.POST['id']))
                datos = json.loads(request.POST['lista_items1'])
                if not PeriodoGastosPersonales.objects.filter(fechadesde__lte=datetime.now().date(), fechahasta__gte=datetime.now().date()).exists():
                    return JsonResponse({'result': 'bad', 'mensaje': u'No existe un Periodo de actualización'})
                periodo = PeriodoGastosPersonales.objects.filter(fechadesde__lte=datetime.now().date(), fechahasta__gte=datetime.now().date())[0]
                if GastosPersonales.objects.filter(persona=persona1, periodogastospersonales=periodo, mes=datetime.now().date().month).exists():
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ya existe una declaración en este mes, debe modificarla.'})
                for elemento in datos:
                    gasto = GastosPersonales(persona=persona1,
                                             rmuproyectado=Decimal(elemento['rmu_proyectado']),
                                             mes=datetime.now().month,
                                             periodogastospersonales=periodo,
                                             rmupagado=Decimal(elemento['rmu_pagado']),
                                             horasextraspagado=Decimal(elemento['horas_extras_pagado']),
                                             horasextrasactual=Decimal(elemento['horas_extras_actual']),
                                             horasextrasproyectado=Decimal(elemento['horas_extras_proyectada']),
                                             otrosingresos=Decimal(elemento['total_ingresos_con_otro']),
                                             totalingresos=Decimal(elemento['total_anual_base']),
                                             otrosgastos=Decimal(elemento['otrosgastos']),
                                             rebajasotros=Decimal(elemento['rebajasotros']),
                                             totalgastos=Decimal(elemento['total_gastos']),
                                             detallevivienda=Decimal(elemento['vivienda']),
                                             detalleeducacion=Decimal(elemento['educacion']),
                                             detallesalud=Decimal(elemento['salud']),
                                             detallealimentacion=Decimal(elemento['alimnentacion']),
                                             detallevestimenta=Decimal(elemento['vestimenta']),
                                             excepcionesgastos=int(elemento['excepcion']),
                                             retensionmensual=int(elemento['retencion']),
                                             valorexcepcionedad=Decimal(elemento['valorexcepcionedad']),
                                             valorexcepciondiscapacidad=Decimal(elemento['valorexcepciondiscapacidad']),
                                             fraccionbasica=Decimal(elemento['fraccionbasica']),
                                             excedentehasta=Decimal(elemento['excedentehasta']),
                                             impuestofraccion=Decimal(elemento['impuestofraccion']),
                                             porcentajeimpuesto=Decimal(elemento['porcentajeimpuesto']),
                                             segurogastos=Decimal(elemento['segurogastos']),
                                             valorretenido=Decimal(elemento['valorretenido']),
                                             impuestopagar=Decimal(elemento['impuestopagar']))
                    gasto.save(request)
                    gasto.actualiza_detalle()
                log(u'Adiciono archivo de capacitacion: %s' % persona1, request, "add")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'editgasto':
            try:
                datos = json.loads(request.POST['lista_items1'])
                if not PeriodoGastosPersonales.objects.filter(fechadesde__lte=datetime.now().date(), fechahasta__gte=datetime.now().date()).exists():
                    return JsonResponse({'result': 'bad', 'mensaje': u'No existe un Periodo de actualización'})
                periodo = PeriodoGastosPersonales.objects.filter(fechadesde__lte=datetime.now().date(), fechahasta__gte=datetime.now().date())[0]
                gasto = GastosPersonales.objects.get(pk=int(request.POST['id']))
                for elemento in datos:
                    gasto.rmuproyectado = Decimal(elemento['rmu_proyectado'])
                    gasto.mes = int(datetime.now().month)
                    gasto.rmupagado = Decimal(elemento['rmu_pagado'])
                    gasto.horasextraspagado = Decimal(elemento['horas_extras_pagado'])
                    gasto.horasextrasactual = Decimal(elemento['horas_extras_actual'])
                    gasto.horasextrasproyectado = Decimal(elemento['horas_extras_proyectada'])
                    gasto.otrosingresos = Decimal(elemento['total_ingresos_con_otro'])
                    gasto.totalingresos = Decimal(elemento['total_anual_base'])
                    gasto.otrosgastos = Decimal(elemento['otrosgastos'])
                    gasto.rebajasotros = Decimal(elemento['rebajasotros'])
                    gasto.totalgastos = Decimal(elemento['total_gastos'])
                    gasto.detallevivienda = Decimal(elemento['vivienda'])
                    gasto.detalleeducacion = Decimal(elemento['educacion'])
                    gasto.detallesalud = Decimal(elemento['salud'])
                    gasto.detallealimentacion = Decimal(elemento['alimnentacion'])
                    gasto.detallevestimenta = Decimal(elemento['vestimenta'])
                    gasto.excepcionesgastos = int(elemento['excepcion'])
                    gasto.retensionmensual = Decimal(elemento['retencion'])
                    gasto.valorexcepcionedad = Decimal(elemento['valorexcepcionedad'])
                    gasto.valorexcepciondiscapacidad = Decimal(elemento['valorexcepciondiscapacidad'])
                    gasto.fraccionbasica = Decimal(elemento['fraccionbasica'])
                    gasto.excedentehasta = Decimal(elemento['excedentehasta'])
                    gasto.impuestofraccion = Decimal(elemento['impuestofraccion'])
                    gasto.porcentajeimpuesto = Decimal(elemento['porcentajeimpuesto'])
                    gasto.segurogastos = Decimal(elemento['segurogastos'])
                    gasto.valorretenido = Decimal(elemento['valorretenido'])
                    gasto.impuestopagar = Decimal(elemento['impuestopagar'])
                    gasto.save(request)
                    gasto.actualiza_detalle()
                log(u'Adiciono archivo de capacitacion: %s' % persona, request, "add")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
            return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

        if action == 'deletegasto':
            try:
                gasto = GastosPersonales.objects.get(pk=request.POST['id'])
                log(u'Elimino declaracion: %s' % gasto, request, "del")
                gasto.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'deleteperiodo':
            try:
                periodo = PeriodoGastosPersonales.objects.get(pk=int(encrypt(request.POST['id'])))
                periodo.status=False
                periodo.save(request)
                log(u'Elimino periodo de declaración: %s' % periodo, request, "del")
                res_json = {"error": False, "mensaje": 'Registro eliminado'}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'lista_plantilla':
            try:
                lista = []
                anio = int(request.POST['anio'])
                for per in GastosPersonales.objects.filter(periodogastospersonales__anio=anio):
                    personas = {'distributivo': per.persona.nombre_completo(), 'id': per.persona.id}
                    lista.append(personas)
                return JsonResponse({"result": "ok", "cantidad": len(lista), "personas": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar lista para calcular jornadas"})

        if action == 'calcular_declaraciones':
            try:
                persona = Persona.objects.get(pk=request.POST['maid'])
                anio = int(request.POST['anio'])
                if persona.gastospersonales_set.filter(periodogastospersonales__anio=anio).exists():
                    if not PeriodoGastosPersonales.objects.filter(anio=anio).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"No existe periodo de actualización para este año"})
                    periodo = PeriodoGastosPersonales.objects.filter(anio=anio)[0]
                    if not GastosPersonales.objects.filter(persona=persona, periodogastospersonales=periodo).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Esta persona no ha realizado su declaración en este año %s" % persona})
                    gasto = GastosPersonales.objects.filter(persona=persona, periodogastospersonales=periodo)[0]
                    sueldo_salario = 0
                    sobresueldo = 0
                    decimotercer = 0
                    decimocuarto = 0
                    fondoreserva = 0
                    aportepersonal = 0
                    if DetallePeriodoRol.objects.filter(persona=persona, periodo__anio=periodo.anio, status=True, rubro__id__in=NOMINA_RUBRO_SUELDOS).exists():
                        sueldo_salario = DetallePeriodoRol.objects.filter(persona=persona, periodo__anio=periodo.anio, status=True, rubro__id__in=NOMINA_RUBRO_SUELDOS).aggregate(valor=Sum('valor'))[
                            'valor']
                    if DetallePeriodoRol.objects.filter(persona=persona, periodo__anio=periodo.anio, status=True, rubro__id__in=NOMINA_RUBRO_SOBRESUELDOS).exists():
                        sobresueldo = DetallePeriodoRol.objects.filter(persona=persona, periodo__anio=periodo.anio, status=True, rubro__id__in=NOMINA_RUBRO_SOBRESUELDOS).aggregate(valor=Sum('valor'))[
                            'valor']
                    if DetallePeriodoRol.objects.filter(persona=persona, periodo__anio=periodo.anio, status=True, rubro__id__in=NOMINA_RUBRO_DECIMOTERCER).exists():
                        decimotercer = \
                        DetallePeriodoRol.objects.filter(persona=persona, periodo__anio=periodo.anio, status=True, rubro__id__in=NOMINA_RUBRO_DECIMOTERCER).aggregate(valor=Sum('valor'))['valor']
                    if DetallePeriodoRol.objects.filter(persona=persona, periodo__anio=periodo.anio, status=True, rubro__id__in=NOMINA_RUBRO_DECIMOCUARTO).exists():
                        decimocuarto = \
                        DetallePeriodoRol.objects.filter(persona=persona, periodo__anio=periodo.anio, status=True, rubro__id__in=NOMINA_RUBRO_DECIMOCUARTO).aggregate(valor=Sum('valor'))['valor']
                    if DetallePeriodoRol.objects.filter(persona=persona, periodo__anio=periodo.anio, status=True, rubro__id__in=NOMINA_RUBRO_FONDORESERVA).exists():
                        fondoreserva = \
                        DetallePeriodoRol.objects.filter(persona=persona, periodo__anio=periodo.anio, status=True, rubro__id__in=NOMINA_RUBRO_FONDORESERVA).aggregate(valor=Sum('valor'))['valor']
                    if DetallePeriodoRol.objects.filter(persona=persona, periodo__anio=periodo.anio, status=True, rubro__id__in=NOMINA_RUBRO_SEGURO_ID).exists():
                        aportepersonal = DetallePeriodoRol.objects.filter(persona=persona, periodo__anio=periodo.anio, status=True, rubro__id__in=NOMINA_RUBRO_SEGURO_ID).aggregate(valor=Sum('valor'))[
                            'valor']
                    if DeclaracionSriAnual.objects.filter(periodogastospersonales=periodo, persona=persona).exists():
                        declaracionanterior = DeclaracionSriAnual.objects.filter(periodogastospersonales=periodo, persona=persona)
                        declaracionanterior.delete()
                    declaracion = DeclaracionSriAnual(persona=persona,
                                                      periodogastospersonales=periodo,
                                                      sueldosysalarios=Decimal(sueldo_salario),
                                                      sobresueldos=Decimal(sobresueldo),
                                                      otrosingresos=gasto.otrosingresos,
                                                      decimotercer=Decimal(decimotercer),
                                                      decimocuarto=Decimal(decimocuarto),
                                                      fondoreserva=Decimal(fondoreserva),
                                                      aportepersonaleste=Decimal(aportepersonal),
                                                      totalingresos=gasto.totalingresos,
                                                      otrosgastos=gasto.otrosgastos,
                                                      excepcionesgastos=gasto.excepcionesgastos,
                                                      valorexcepcionedad=gasto.valorexcepcionedad,
                                                      valorexcepciondiscapacidad=gasto.valorexcepciondiscapacidad,
                                                      segurogastos=gasto.segurogastos,
                                                      valorretenido=gasto.valorretenido,
                                                      fraccionbasica=gasto.fraccionbasica,
                                                      impuestopagar=gasto.impuestopagar,
                                                      totalgastos=gasto.totalgastos,
                                                      detallevivienda=gasto.detallevivienda,
                                                      detalleeducacion=gasto.detalleeducacion,
                                                      detallesalud=gasto.detallesalud,
                                                      detallealimentacion=gasto.detallealimentacion,
                                                      detallevestimenta=gasto.detallevestimenta,
                                                      retensionmensual=gasto.retensionmensual)
                    declaracion.save(request)
                    declaracion.baseimponible = Decimal(
                        sueldo_salario + sobresueldo + declaracion.otrosingresos - declaracion.otrosgastos - declaracion.valorexcepcionedad - declaracion.valorexcepciondiscapacidad - declaracion.totalgastos - aportepersonal)
                    declaracion.ingresosgravados = Decimal(sueldo_salario + sobresueldo)
                    declaracion.save(request)
                    log(u'Calculo declaraciones de SRI anual: %s - %s - %s - [%s]' % (declaracion.persona, declaracion.sueldosysalarios, declaracion.totalgastos, declaracion.id), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        if action == 'addperiodo':
            try:
                f = PeriodoGastosForm(request.POST)
                if f.is_valid():
                    if PeriodoGastosPersonales.objects.filter(anio=f.cleaned_data['anio']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un periodo en ese año, con fecha vigente."})
                    if f.cleaned_data['fechadesde'] > f.cleaned_data['fechahasta']:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha final no puede ser menor a la inicial."})
                    periodo = PeriodoGastosPersonales(anio=f.cleaned_data['anio'],
                                                      fechahasta=f.cleaned_data['fechahasta'],
                                                      fechadesde=f.cleaned_data['fechadesde'],
                                                      descripcion=f.cleaned_data['descripcion'])
                    periodo.save(request)
                    if 'formato' in request.FILES:
                        newfile = request.FILES['formato']
                        newfile._name = generar_nombre("formatogastos", newfile._name)
                        periodo.formato = newfile
                        periodo.save()
                    log(u'Adiciono periodo para declaraciones: %s' % periodo, request, "add")
                    return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
                else:
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in f.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editperiodo':
            try:
                f = PeriodoGastosForm(request.POST)
                f.fields['anio'].required=False
                f.fields['descripcion'].required=False
                if f.is_valid():
                    periodo = PeriodoGastosPersonales.objects.get(pk=int(encrypt(request.POST['id'])))
                    if f.cleaned_data['fechadesde'] > f.cleaned_data['fechahasta']:
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha final no puede ser menor a la inicial."})
                    periodo.fechahasta = f.cleaned_data['fechahasta']
                    periodo.fechadesde = f.cleaned_data['fechadesde']
                    periodo.mostrar = f.cleaned_data['mostrar']
                    if 'formato' in request.FILES:
                        newfile = request.FILES['formato']
                        newfile._name = generar_nombre("formatogastos", newfile._name)
                        periodo.formato = newfile

                    periodo.save(request)
                    log(u'Edito periodo para declaraciones: %s' % periodo, request, "add")
                    return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
                else:
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in f.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'detallegasto':
            try:
                data['empleado'] = persona = Persona.objects.get(pk=int(request.POST['id']), status=True)
                data['gasto'] = GastosPersonales.objects.get(pk=int(request.POST['idg']), status=True)
                data['periodo'] = periodo = PeriodoGastosPersonales.objects.get(pk=int(request.POST['idp']))
                data['detalles'] = ResumenMesGastosPersonales.objects.filter(gastospersonales__persona=persona, gastospersonales__periodogastospersonales__anio=periodo.anio).order_by('mes')
                template = get_template("fin_gastospersonales/detallegasto.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'verificar_tabla':
            try:
                valor = Decimal(request.POST['valor'])
                if valor < 0:
                    valor = 0
                anio = datetime.now().year
                if TablaImpuestoRenta.objects.filter(anio=anio, fraccionbasica__lte=valor, excesohasta__gte=valor).exists():
                    tabla = TablaImpuestoRenta.objects.filter(anio=anio, fraccionbasica__lte=valor, excesohasta__gte=valor)[0]
                else:
                    tabla = TablaImpuestoRenta.objects.filter(anio=anio, fraccionbasica__lte=valor, excesohasta__gte=valor).order_by('-excesohasta')[0]
                return JsonResponse({"result": "ok", "fraccion": str(tabla.fraccionbasica), "impuesto": str(tabla.impuestofraccionbasica), "valorexcesohasta": str(tabla.excesohasta),
                                     "porcentaje": str(tabla.porcentajeimpuestofraccionbasica), "valorfraccion": str(tabla.valorfraccionbasica)})
            except Exception as ex:
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al obtener los datos'})

        if action == 'lista_plantilla_excel':
            try:
                anio = request.POST['anio']
                mes = request.POST['mes']

                __author__ = 'Unemi'
                style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                style1 = easyxf(num_format_str='D-MMM-YY')
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('exp_xls_post_part')
                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'gastospersonales'))
                ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                # ws.write_merge(0, 0, 1, 10, 'DEPARTAMENTO FINANCIERO', title)
                # ws.write_merge(0, 0, 2, 10, 'SECCION CONTABILIDAD', title)
                # ws.write_merge(0, 0, 3, 10, 'PROYECCION DE GASTOS PERSONALES', title)
                # ws.write_merge(0, 0, 4, 10, anio, title)
                # response = HttpResponse(content_type="application/ms-excel")
                # response['Content-Disposition'] = 'attachment; filename=gastos_personales_' + random.randint(1, 10000).__str__() + '.xls'
                nombre = "GASTOS_PERSONALES_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
                ruta = "media/gastospersonales/" + nombre
                filename = os.path.join(output_folder, nombre)
                columns = [
                    (u"CEDULA", 6000),
                    (u"APELLIDOS_NOMBRES", 6000),
                    (u"VIVIENDA", 6000),
                    (u"EDUCACION", 6000),
                    (u"SALUD", 6000),
                    (u"ALIMENTACION", 6000),
                    (u"VESTIMENTA", 6000),
                    (u"TIPO", 6000),
                    (u"OTROS INGRESOS", 6000),
                ]
                row_num = 5
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]
                cursor = connection.cursor()
                sql = "SELECT sga_persona.cedula AS sga_persona_cedula, sga_persona.apellido1||' '||sga_persona.apellido2||' '||sga_persona.nombres AS sga_persona_nombres, " \
                      " sagest_gastospersonales.detallevivienda AS sagest_gastospersonales_detallevivienda, sagest_gastospersonales.detalleeducacion AS sagest_gastospersonales_detalleeducacion, " \
                      " sagest_gastospersonales.detallesalud AS sagest_gastospersonales_detallesalud, sagest_gastospersonales.detallealimentacion AS sagest_gastospersonales_detallealimentacion, " \
                      " sagest_gastospersonales.detallevestimenta AS sagest_gastospersonales_detallevestimenta, sagest_periodogastospersonales.descripcion AS sagest_periodogastospersonales_descripcion, " \
                      " (case sagest_gastospersonales.excepcionesgastos when 1 then 'NINGUNO' when 2 then 'MAYOR EDAD' when 3 then 'DISCAPACITADO' else 'TERCERA EDAD Y DISCAPACITADO' end) as excepcionesgastos, " \
                      " sagest_gastospersonales.otrosingresos AS sagest_gastospersonales_otros " \
                      " FROM sagest_periodogastospersonales sagest_periodogastospersonales " \
                      " RIGHT OUTER JOIN sagest_gastospersonales sagest_gastospersonales ON sagest_periodogastospersonales.id = sagest_gastospersonales.periodogastospersonales_id and sagest_gastospersonales.status=true " \
                      " LEFT OUTER JOIN sga_persona sga_persona ON sagest_gastospersonales.persona_id = sga_persona.id and sga_persona.status=true " \
                      " WHERE sagest_periodogastospersonales.anio = " + anio + " and sagest_gastospersonales.mes=" + mes + " and sagest_periodogastospersonales.status=true"
                cursor.execute(sql)
                results = cursor.fetchall()
                row_num = 6
                for r in results:
                    i = 0
                    campo1 = r[0]
                    campo2 = r[1]
                    campo3 = r[2]
                    campo4 = r[3]
                    campo5 = r[4]
                    campo6 = r[5]
                    campo7 = r[6]
                    campo8 = r[8]
                    campo9 = r[9]

                    ws.write(row_num, 0, campo1, font_style2)
                    ws.write(row_num, 1, campo2, font_style2)
                    ws.write(row_num, 2, campo3, font_style2)
                    ws.write(row_num, 3, campo4, font_style2)
                    ws.write(row_num, 4, campo5, font_style2)
                    ws.write(row_num, 5, campo6, font_style2)
                    ws.write(row_num, 6, campo7, font_style2)
                    ws.write(row_num, 7, campo8, font_style2)
                    ws.write(row_num, 8, campo9, font_style2)

                    row_num += 1
                wb.save(filename)
                connection.close()
                # return book
                return JsonResponse({'result': 'ok', 'archivo': ruta})

            except Exception as ex:
                pass

        #NUEVAS ACCIONES
        if action == 'importargastopersonal':
            try:
                idp = int(encrypt(request.POST['idp']))
                form = PoblacionForm(request.POST, request.FILES)
                if not form.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})

                archivo = request.FILES['archivo']
                df = pd.read_excel(archivo)
                if not 'CEDULA' in df.columns:
                    raise NameError('Formato de archivo erróneo, columna CEDULA faltante.')
                for index, row in df.iterrows():
                    cedula = str(int(row['CEDULA']))
                    cedula = cedula if len(cedula) == 10 else f'0{cedula}'
                    pers = Persona.objects.filter(cedula=cedula).first()
                    if pers:
                        gastos = pers.gastospersonales_set.filter(status=True, periodogastospersonales_id=idp)
                        mes = hoy.date().month
                        if not gastos.exists():
                            instancia = GastosPersonales(periodogastospersonales_id=idp, persona=pers, mes=mes)
                            instancia.save(request)
                            log(f'Agrego gasto personal en opción de importar con excel: {instancia}', request, 'add')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': str(ex)})

        if action == 'addgastopersonal':
            try:
                idp = int(encrypt(request.POST['idp']))
                periodo=PeriodoGastosPersonales.objects.get(id=idp)
                form = GastosPersonalesForm(request.POST, request.FILES, instancia=periodo)
                if not form.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})

                instancia = GastosPersonales(periodogastospersonales_id=idp,
                                             persona=form.cleaned_data['persona'],
                                             mes=form.cleaned_data['mes'])
                instancia.save(request)
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("gastospersonales_", newfile._name)
                    instancia.archivo = newfile
                    instancia.save(request)
                log(f'Agrego gasto personal: {instancia}', request, 'add')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': str(ex)})

        if action == 'editgastopersonal':
            try:
                id = int(encrypt(request.POST['id']))
                instancia=GastosPersonales.objects.get(id=id)
                form = GastosPersonalesForm(request.POST, request.FILES, instancia=instancia)
                if not form.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("gastospersonales_", newfile._name)
                    instancia.archivo = newfile
                instancia.persona=form.cleaned_data['persona']
                instancia.mes=form.cleaned_data['mes']
                instancia.save(request)
                log(f'Edito gasto personal: {instancia}', request, 'edit')
                return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': str(ex)})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addgasto':
                try:
                    data['title'] = u'Adicionar Gastos Personales'
                    hoy = datetime.now().date()
                    data['empleado'] = persona1 = Persona.objects.get(pk=int(request.GET['id']))
                    fechaingreso = persona1.mi_fechaingreso()
                    data['gastospersonales'] = GastosPersonales.objects.filter(persona=persona1, periodogastospersonales__anio=datetime.now().date().year, status=True).order_by(
                        'periodogastospersonales__anio')
                    data['rolpago_ingresos'] = persona1.rolpago_ingresos()
                    data['rmu_actual'] = actual = persona1.mi_plantilla_actual().rmupuesto
                    data['extras_actual'] = extrasactual = persona1.horasextra_ingresos_mes()
                    data['rolpago_horasextras'] = persona1.rolpago_horasextras()
                    data['rolpago_renta'] = persona1.rolpago_renta()
                    data['porcentaje_seguro'] = PORCENTAJE_SEGURO
                    valorresta = 13
                    if persona1.rolpago_ingresos_mes():
                        valorresta -= 1
                    proyectado = valorresta - hoy.month
                    data['rmu_proyectado'] = (proyectado * actual)
                    data['mes'] = proyectado
                    data['rolpago_iess'] = Decimal(persona1.rolpago_iess()) + ((Decimal(actual) * Decimal(PORCENTAJE_SEGURO)) * Decimal(proyectado))
                    return render(request, "fin_gastospersonales/addgasto.html", data)
                except Exception as ex:
                    pass

            elif action == 'editgasto':
                try:
                    data['title'] = u'Editar Gastos Personales'
                    hoy = datetime.now().date()
                    data['gasto'] = gasto = GastosPersonales.objects.get(pk=int(request.GET['id']))
                    data['empleado'] = persona1 = gasto.persona
                    fechaingreso = persona1.mi_fechaingreso()
                    data['rolpago_ingresos'] = persona1.rolpago_ingresos()
                    data['rmu_actual'] = actual = persona1.mi_plantilla_actual().rmupuesto
                    data['extras_actual'] = extrasactual = persona1.horasextra_ingresos_mes()
                    data['rolpago_horasextras'] = persona1.rolpago_horasextras()
                    data['rolpago_renta'] = persona1.rolpago_renta()
                    data['porcentaje_seguro'] = PORCENTAJE_SEGURO
                    valorresta = 13
                    if persona1.rolpago_ingresos_mes():
                        valorresta -= 1
                    proyectado = valorresta - hoy.month
                    data['rmu_proyectado'] = (proyectado * actual)
                    data['mes'] = proyectado
                    data['rolpago_iess'] = Decimal(persona1.rolpago_iess()) + ((Decimal(actual) * Decimal(PORCENTAJE_SEGURO)) * Decimal(proyectado))
                    return render(request, "fin_gastospersonales/editgasto.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletegasto':
                try:
                    data['title'] = u'Eliminar Gasto Personal'
                    data['gasto'] = GastosPersonales.objects.get(pk=request.GET['id'])
                    return render(request, 'fin_gastospersonales/delete.html', data)
                except Exception as ex:
                    pass

            elif action == 'deleteperiodo':
                try:
                    data['title'] = u'Eliminar Periodo'
                    data['periodo'] = PeriodoGastosPersonales.objects.get(pk=request.GET['id'])
                    return render(request, 'fin_gastospersonales/deleteperiodo.html', data)
                except Exception as ex:
                    pass

            elif action == 'personagasto':
                try:
                    data['title'] = u'Gastos Personales'
                    data['idp']=request.GET['idp']
                    data['empleado'] = persona = Persona.objects.get(pk=int(request.GET['id']))
                    data['perfilprincipal'] = request.session['perfilprincipal']
                    roles = persona.rolpago_set.filter(periodo__estado=5, status=True)
                    paging = MiPaginador(roles, 25)
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
                    data['paging_rol'] = paging
                    data['rangospaging_rol'] = paging.rangos_paginado(p)
                    data['page_rol'] = page
                    if persona.tipocelular == 0:
                        data['tipocelular'] = '-'
                    else:
                        data['tipocelular'] = TIPO_CELULAR[int(persona.tipocelular) - 1][1]
                    data['roles'] = page.object_list
                    data['gastospersonales'] = persona.gastospersonales_set.all().order_by('-periodogastospersonales__anio')
                    data['reporte_0'] = obtener_reporte('declaracion_sri')
                    data['puede_ingresar_gastos'] = puedeingresar = PeriodoGastosPersonales.objects.filter(fechadesde__lte=datetime.now().date(), fechahasta__gte=datetime.now().date()).exists()
                    data['periodo'] = None
                    if puedeingresar:
                        data['periodo'] = PeriodoGastosPersonales.objects.filter(fechadesde__lte=datetime.now().date(), fechahasta__gte=datetime.now().date())[0]
                    return render(request, "fin_gastospersonales/personagasto.html", data)
                except Exception as ex:
                    pass

            # NUEVAS ACCIONES
            elif action == 'addperiodo':
                try:
                    data['title'] = u'Crear Periodo'
                    data['form'] = PeriodoGastosForm()
                    data['switchery']=True
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editperiodo':
                try:
                    data['title'] = u'Crear Periodo'
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['switchery'] = True
                    data['periodo'] = periodo = PeriodoGastosPersonales.objects.get(pk=id)
                    initial = model_to_dict(periodo)
                    form = PeriodoGastosForm(initial=initial)
                    form.editar()
                    data['form'] = form
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'personal':
                try:
                    data['title'] = u'Personal que registra gastos.'
                    id = request.GET['id']
                    periodo = PeriodoGastosPersonales.objects.get(id=int(encrypt(id)))
                    url_vars, id, search, filtro = f'&action={action}&id={id}', int(encrypt(id)), \
                                                   request.GET.get('s', ''), Q(periodogastospersonales=periodo, status=True)
                    if 's' in request.GET:
                        data['s'] = search = request.GET['s'].strip()
                        filtro=filtro_persona(search, filtro)
                    personal = GastosPersonales.objects.filter(filtro).order_by('-fecha_creacion')
                    paging = MiPaginador(personal, 20)
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
                    data['listado'] = page.object_list
                    data['page'] = page
                    data['periodo'] = periodo
                    data['hoy'] = hoy
                    data['t_conarchivos']=len(personal.exclude(Q(archivo__isnull=True) | Q(archivo='')))
                    data['t_sinarchivos']=len(personal.filter(Q(archivo__isnull=True) | Q(archivo='')))
                    data['url_vars'] = url_vars
                    request.session['viewactivo'] = 1
                    return render(request, "fin_gastospersonales/view.html", data)
                except Exception as ex:
                    pass

            elif action == 'importargastopersonal':
                try:
                    form = PoblacionForm()
                    data['idp'] = int(encrypt(request.GET['idp']))
                    data['form'] = form
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'addgastopersonal':
                try:
                    form = GastosPersonalesForm()
                    form.fields['persona'].queryset=Persona.objects.none()
                    data['idp'] = int(encrypt(request.GET['idp']))
                    data['form'] = form
                    template = get_template('fin_gastospersonales/modal/formgastospersonales.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editgastopersonal':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    instancia=GastosPersonales.objects.get(id=id)
                    form = GastosPersonalesForm(initial=model_to_dict(instancia))
                    form.fields['persona'].queryset = Persona.objects.filter(id=instancia.persona.id)
                    data['form'] = form
                    template = get_template('fin_gastospersonales/modal/formgastospersonales.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'buscarpersonas':
                try:
                    resp = filtro_persona_select(request)
                    return HttpResponse(json.dumps({'status': True, 'results': resp}))
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Periodos de gastos personales'
                data['subtitle'] = u'Listado de periodos creados'
                url_vars, filtro = f'',  Q(status=True)
                if 's' in request.GET:
                    data['s'] = search = request.GET['s'].strip()
                    url_vars=f'&s={search}'
                    filtro = filtro & Q(descripcion__icontains=search)
                periodos = PeriodoGastosPersonales.objects.filter(filtro).order_by('-anio')
                paging = MiPaginador(periodos, 20)
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
                data['rangospaging_activo'] = paging.rangos_paginado(p)
                data['page_activo'] = page
                data['url_vars'] = url_vars
                data['periodos'] = page.object_list
                request.session['viewactivo'] = 1
                return render(request, "fin_gastospersonales/periodos.html", data)
            except Exception as ex:
                pass
