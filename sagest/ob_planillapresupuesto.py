# -*- coding: UTF-8 -*-
from decimal import Decimal
import xlwt
from googletrans import Translator
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module
from sagest.forms import PlanillaPresupuestoObraForm
from sagest.models import PlanillaPresupuestoObra, RecursoActividadPresupuestObra, PresupuestoObra, DetallePlanillaPresupuestoObra, \
    AprobacionPresupuestoObra, CronogramaPresupuestoObra, null_to_decimal
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = PlanillaPresupuestoObraForm(request.POST)
                max_duracion_presupuesto = PresupuestoObra.objects.filter(estado=2).order_by('duracion')[0]
                f.planilla_mes(max_duracion_presupuesto.duracion)
                if f.is_valid():
                    presupuesto = f.cleaned_data['presupuestoobra']
                    f.planilla_mes(presupuesto.duracion)
                    if (presupuesto.saldoplanilla == presupuesto.valor) and f.cleaned_data['tipoplanilla'] == '1':
                        return JsonResponse({"result": "bad", "mensaje": u'Planilla Unica por Avance fue concluido, Eliga Complementaria'})
                    mes = f.cleaned_data['mesplanilla'] if f.cleaned_data['mesplanilla'] else None
                    if f.cleaned_data['tipoplanilla'] != 1:
                        mes = None
                    recursos = RecursoActividadPresupuestObra.objects.filter(grupoactividadpresupuestobra__actividadpresupuestoobra__presupuestoobra=presupuesto)
                    planilla = PlanillaPresupuestoObra(presupuestoobra=presupuesto,
                                                       periodoinicio=f.cleaned_data['periodoinicio'],
                                                       periodofin=f.cleaned_data['periodofin'],
                                                       tipoplanilla=f.cleaned_data['tipoplanilla'],
                                                       mesplanilla=mes,)
                    planilla.save(request)
                    if f.cleaned_data['tipoplanilla'] != '3':
                        for recurso in recursos:
                            detplanilla = DetallePlanillaPresupuestoObra(planillapresupuestoobra=planilla,
                                                                         recursoactividadpresupuestobra=recurso,)
                            detplanilla.save(request)
                    log(u'Adiciono una nuevo planilla: %s' % planilla, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        if action == 'recursos':
            try:
                data = {}
                data['planilla'] = planilla = PlanillaPresupuestoObra.objects.get(pk=int(request.POST['id']))
                presupuesto = planilla.presupuestoobra
                if planilla.tipoplanilla == 1:
                    detalle = planilla.detalleplanillapresupuestoobra_set.filter(recursoactividadpresupuestobra__cantidadsaldo__gt=0)
                elif planilla.tipoplanilla == 2:
                    detalle = planilla.detalleplanillapresupuestoobra_set.filter(recursoactividadpresupuestobra__cantidadsaldo=0)
                else:
                    data['planilla'] = planilla
                    data['detalles'] = planilla.detalleplanillapresupuestoobra_set.all()
                    template = get_template("ob_planillapresupuesto/detalleextra.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'plantilla': json_content, 'tipoplantilla': str(planilla.tipoplanilla)})
                pagina = 1
                paging = MiPaginador(detalle, 10)
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
                data['detalles'] = page.object_list
                data['usuario'] = request.user
                template = get_template("ob_planillapresupuesto/detallerecursos.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content, 'contador': planilla.contador_plantilla(), 'monto': str(planilla.monto), 'tipoplantilla': str(planilla.tipoplanilla)})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'marcarseleccionado':
            try:
                detalle = DetallePlanillaPresupuestoObra.objects.get(pk=int(request.POST['id']))
                detalle.seleccionado = request.POST['valor'] == u'true'
                if not detalle.seleccionado:
                    detalle.cantidadavance = 0
                    detalle.porcentajeavance = 0
                    detalle.costoavance = 0
                detalle.save(request)
                recurso = detalle.recursoactividadpresupuestobra
                recurso.actualizar_cantidad_saldo()
                planilla = detalle.planillapresupuestoobra
                planilla.monto = monto = Decimal(planilla.valor_planilla()).quantize(Decimal('.01'))
                planilla.montoapagar = Decimal(monto - planilla.valoranticipo).quantize(Decimal('.01'))
                planilla.save(request)
                return JsonResponse({"result": "ok", "reload": 'False', 'contador': detalle.planillapresupuestoobra.contador_plantilla(), 'recursocantidadsaldo': str(recurso.cantidadsaldo), 'monto': str(monto)})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        if action == 'marcartodos':
            try:
                planilla = PlanillaPresupuestoObra.objects.get(pk=int(request.POST['id']))
                estado = request.POST['valor'] == u'true'
                planilla.detalleplanillapresupuestoobra_set.all().update(seleccionado=estado)
                return JsonResponse({"result": "ok", "reload": 'True', 'contador': planilla.contador_plantilla()})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        if action == 'editcantidarecurso':
            try:
                detallerecurso = DetallePlanillaPresupuestoObra.objects.get(pk=request.POST['idd'])
                planilla = detallerecurso.planillapresupuestoobra
                cantidad = Decimal(request.POST['cantidad'])
                anticipado = Decimal(request.POST['anticipado']).quantize(Decimal('.01'))
                cantidadpermitida = 0
                if planilla.tipoplanilla == 1:
                    cantidadpermitida = detallerecurso.recursoactividadpresupuestobra.cantidad
                if planilla.tipoplanilla == 2:
                    cantidadpermitida = cantidad
                if cantidad <= cantidadpermitida:
                    detallerecurso.cantidadavance = cantidad
                    detallerecurso.porcentajeavance = Decimal((cantidad / cantidadpermitida) * 100).quantize(Decimal('.01'))
                    detallerecurso.costoavance = Decimal(cantidad * detallerecurso.recursoactividadpresupuestobra.preciounitario).quantize(Decimal('.01'))
                    detallerecurso.save(request)
                    recurso = detallerecurso.recursoactividadpresupuestobra
                    recurso.actualizar_cantidad_saldo()
                    presupuesto = detallerecurso.planillapresupuestoobra.presupuestoobra
                    planilla = detallerecurso.planillapresupuestoobra
                    planilla.monto = monto = Decimal(planilla.valor_planilla()).quantize(Decimal('.01'))
                    planilla.montoapagar = monto - anticipado
                    planilla.save(request)
                    if planilla.tipoplanilla == 1:
                        presupuesto.saldoplanilla = null_to_decimal(PlanillaPresupuestoObra.objects.filter(presupuestoobra=presupuesto).aggregate(totalmonto=Sum('monto'))['totalmonto'])
                        presupuesto.valoranticipo = null_to_decimal(PlanillaPresupuestoObra.objects.filter(presupuestoobra=presupuesto).aggregate(totalanticipo=Sum('valoranticipo'))['totalanticipo'])
                        presupuesto.save(request)
                    log(u'Modifico recurso de planilla: %s' % detallerecurso, request, "edit")
                    return JsonResponse({"result": "ok", "monto": str(monto), 'recursocantidadsaldo': str(recurso.cantidadsaldo), "porcentaje": str(detallerecurso.porcentajeavance), "costo": str(detallerecurso.costoavance)})
                return JsonResponse({"result": "ok", 'superacantidad': 1, 'cantidadrecomendado': str(cantidad - detallerecurso.recursoactividadpresupuestobra.cantidad)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al editar los datos'})

        if action == 'finalizar':
            try:
                planillaactual = PlanillaPresupuestoObra.objects.get(pk=request.POST['id'])
                presupuesto = planillaactual.presupuestoobra
                for detalle in planillaactual.detalleplanillapresupuestoobra_set.filter(seleccionado=True):
                    cantidadavance = null_to_decimal(DetallePlanillaPresupuestoObra.objects.filter(planillapresupuestoobra__presupuestoobra=planillaactual.presupuestoobra, recursoactividadpresupuestobra=detalle.recursoactividadpresupuestobra, planillapresupuestoobra__tipoplanilla=planillaactual.tipoplanilla, planillapresupuestoobra__estado=2).distinct().aggregate(cantidadavance=Sum('cantidadavance'))['cantidadavance'])
                    detalle.cantidadacumulada = detalle.cantidadavance + cantidadavance
                    detalle.cantidadanterior = cantidadavance
                    porcentajeavance = null_to_decimal(DetallePlanillaPresupuestoObra.objects.filter(planillapresupuestoobra__presupuestoobra=planillaactual.presupuestoobra, recursoactividadpresupuestobra=detalle.recursoactividadpresupuestobra, planillapresupuestoobra__tipoplanilla=planillaactual.tipoplanilla, planillapresupuestoobra__estado=2).distinct().aggregate(porcentajeavance=Sum('porcentajeavance'))['porcentajeavance'])
                    detalle.porcentajeacumulada = detalle.porcentajeavance + porcentajeavance
                    detalle.porcentajeanterior = porcentajeavance
                    costoavance = null_to_decimal(DetallePlanillaPresupuestoObra.objects.filter(planillapresupuestoobra__presupuestoobra=planillaactual.presupuestoobra, recursoactividadpresupuestobra=detalle.recursoactividadpresupuestobra, planillapresupuestoobra__tipoplanilla=planillaactual.tipoplanilla, planillapresupuestoobra__estado=2).distinct().aggregate(costoavance=Sum('costoavance'))['costoavance'])
                    detalle.costoacumulada = detalle.costoavance + costoavance
                    detalle.costoanterior = costoavance
                    detalle.save(request)
                planillaactual.estado = 2
                planillaanteriores = null_to_decimal(planillaactual.detalleplanillapresupuestoobra_set.all().aggregate(planillaanteriores=Sum('costoanterior'))['planillaanteriores'], 2)
                totalfecha = Decimal(planillaactual.monto - planillaanteriores).quantize(Decimal('.01'))
                planillaactual.saldoanticipo = Decimal(totalfecha - planillaactual.valoranticipo).quantize(Decimal('.01'))
                planillaactual.save(request)
                if planillaactual.tipoplanilla == 1:
                    planillaacumulada = null_to_decimal(planillaactual.detalleplanillapresupuestoobra_set.all().aggregate(planillaacumulada=Sum('costoacumulada'))['planillaacumulada'], 2)
                    avanceejecutado = Decimal((planillaactual.monto / presupuesto.valor) * 100).quantize(Decimal('.01'))
                    avanceacumulado = Decimal((planillaacumulada / presupuesto.valor) * 100).quantize(Decimal('.01'))
                    cronogramapresupuesto = CronogramaPresupuestoObra.objects.get(presupuestoobra=presupuesto, mes=planillaactual.mesplanilla)
                    cronogramapresupuesto.ejecutado = planillaactual.monto
                    cronogramapresupuesto.porcientoavance = avanceacumulado
                    cronogramapresupuesto.save(request)
                    presupuesto.actualiza_planificado()
                log(u'Modifico planilla de presupuesto: %s' % planillaactual, request, "edit")
                return JsonResponse({"result": "ok", 'estado': planillaactual.rep_estado()})
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "mensaje": translator.translate(ex.__str__(),'es').text})

        if action == 'edit':
            try:
                planilla = PlanillaPresupuestoObra.objects.get(pk=request.POST['id'])
                presupuesto = planilla.presupuestoobra
                f = PlanillaPresupuestoObraForm(request.POST)
                if f.is_valid():
                    totalanticipado = null_to_decimal(PlanillaPresupuestoObra.objects.filter(presupuestoobra=presupuesto).distinct().aggregate(totalanticipado=Sum('valoranticipo'))['totalanticipado'])
                    if totalanticipado > presupuesto.valor:
                        return JsonResponse({"result": "bad", "mensaje": u'El valor del anticipo supera el presupuesto'})
                    valoranticipo = f.cleaned_data['valoranticipo']
                    planilla.valoranticipo = valoranticipo
                    planilla.montoapagar = Decimal(planilla.monto - valoranticipo).quantize(Decimal('.01'))
                    planilla.save(request)
                    if planilla.tipoplanilla == 1:
                        presupuesto.saldoplanilla = null_to_decimal(PlanillaPresupuestoObra.objects.filter(presupuestoobra=presupuesto).aggregate(totalmonto=Sum('monto'))['totalmonto'])
                        presupuesto.valoranticipo = null_to_decimal(PlanillaPresupuestoObra.objects.filter(presupuestoobra=presupuesto).aggregate(totalanticipo=Sum('valoranticipo'))['totalanticipo'])
                        presupuesto.save(request)
                    log(u'Modifico planilla de presupuesto: %s' % planilla, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "mensaje": translator.translate(ex.__str__(),'es').text})

        if action == 'addrecursoextra':
            try:
                data['planilla'] = planilla = PlanillaPresupuestoObra.objects.get(pk=int(request.POST['idp']))
                cantidad = Decimal(request.POST['cantidad']).quantize(Decimal('.01'))
                precio = Decimal(request.POST['precio']).quantize(Decimal('.0001'))
                costoavance = Decimal(cantidad * precio).quantize(Decimal('.0001'))
                porcentaje = Decimal((cantidad / cantidad) * 100).quantize(Decimal('.01'))
                detalle = DetallePlanillaPresupuestoObra(planillapresupuestoobra=planilla,
                                                         extra=request.POST['descripcion'],
                                                         cantidadavance=cantidad,
                                                         porcentajeavance=porcentaje,
                                                         preciounitarioextra=precio,
                                                         costoavance=costoavance,
                                                         seleccionado=True,)
                detalle.save(request)
                planilla.monto = monto = Decimal(planilla.valor_planilla()).quantize(Decimal('.01'))
                planilla.save(request)
                data['detalles'] = planilla.detalleplanillapresupuestoobra_set.all()
                template = get_template("ob_planillapresupuesto/detalleextra.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'plantilla': json_content, 'monto': str(planilla.monto)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        if action == 'editrecursoextra':
            try:
                detalle = DetallePlanillaPresupuestoObra.objects.get(pk=int(request.POST['iddr']))
                cantidad = Decimal(request.POST['cantidad']).quantize(Decimal('.01'))
                precio = Decimal(request.POST['precio']).quantize(Decimal('.0001'))
                costoavance = Decimal(cantidad * precio).quantize(Decimal('.0001'))
                porcentaje = Decimal((cantidad / cantidad) * 100).quantize(Decimal('.01'))
                detalle.extra = request.POST['descripcion']
                detalle.preciounitarioextra = precio
                detalle.cantidadavance = cantidad
                detalle.porcentajeavance = porcentaje
                detalle.costoavance = costoavance
                detalle.save(request)
                planilla = detalle.planillapresupuestoobra
                planilla.monto = monto = Decimal(planilla.valor_planilla()).quantize(Decimal('.01'))
                planilla.save(request)
                return JsonResponse({"result": "ok", 'monto': str(planilla.monto), 'costoavance': str(detalle.costoavance)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al guardar los datos'})

        if action == 'delitemdetrecurso':
            try:
                detallerecurso = DetallePlanillaPresupuestoObra.objects.get(pk=request.POST['id'])
                planilla = detallerecurso.planillapresupuestoobra
                log(u'Elimino actividad de presupuesto: %s' % detallerecurso, request, "del")
                detallerecurso.delete()
                planilla.monto = monto = Decimal(planilla.valor_planilla()).quantize(Decimal('.01'))
                planilla.save(request)
                return JsonResponse({"result": "ok", 'monto': str(planilla.monto)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'delete':
            try:
                planilla = PlanillaPresupuestoObra.objects.get(pk=request.POST['id'])
                presupuesto = planilla.presupuestoobra
                for detalle in planilla.detalleplanillapresupuestoobra_set.all():
                    recurso = detalle.recursoactividadpresupuestobra
                    recurso.cantidadsaldo = recurso.cantidadsaldo + detalle.cantidadavance
                    detalle.delete()
                    recurso.save()
                log(u'Elimino planilla: %s' % planilla, request, "del")
                if planilla.tipoplanilla == 1:
                    planilla.delete()
                    presupuesto.saldoplanilla = null_to_decimal(PlanillaPresupuestoObra.objects.filter(presupuestoobra=presupuesto).aggregate(totalmonto=Sum('monto'))['totalmonto'])
                    presupuesto.save(request)
                planilla.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'numeroplanilla':
            try:
                presupuesto = PresupuestoObra.objects.get(pk=request.POST['idp'])
                opciones = [(i, i) for i in range(1, presupuesto.duracion + 1)]
                return JsonResponse({"result": "ok", 'opciones': opciones})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al cargar los datos."})

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Planilla Presupuesto'
                    form = PlanillaPresupuestoObraForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, 'ob_planillapresupuesto/add.html', data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar Planilla'
                    data['planilla'] = planilla = PlanillaPresupuestoObra.objects.get(pk=request.GET['id'])
                    data['presupuesto'] = presupuesto = planilla.presupuestoobra
                    initial = model_to_dict(planilla)
                    form = PlanillaPresupuestoObraForm(initial=initial)
                    form.editar()
                    if planilla.tipoplanilla == 1:
                        form.planilla_mes(presupuesto.duracion)
                    if planilla.tipoplanilla != 1:
                        form.complementaria()
                    data['form'] = form
                    return render(request, "ob_planillapresupuesto/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar Planilla de Presupuesto'
                    data['planilla'] = PlanillaPresupuestoObra.objects.get(pk=request.GET['id'])
                    return render(request, 'ob_planillapresupuesto/delete.html', data)
                except Exception as ex:
                    pass

            if action == 'finalizar':
                try:
                    data['title'] = u'Finalizar Planilla'
                    data['planilla'] = PlanillaPresupuestoObra.objects.get(pk=request.GET['id'])
                    return render(request, 'ob_planillapresupuesto/finalizar.html', data)
                except Exception as ex:
                    pass

            if action == 'reporte':
                try:
                    planilla = PlanillaPresupuestoObra.objects.get(pk=request.GET['id'])
                    presupuesto = planilla.presupuestoobra
                    planillaacumulada = null_to_decimal(planilla.detalleplanillapresupuestoobra_set.all().aggregate(planillaacumulada=Sum('costoacumulada'))['planillaacumulada'], 2)
                    planillaanteriores = null_to_decimal(planilla.detalleplanillapresupuestoobra_set.all().aggregate(planillaanteriores=Sum('costoanterior'))['planillaanteriores'], 2)
                    avanceejecutado = Decimal((planilla.monto / presupuesto.valor) * 100).quantize(Decimal('.01'))
                    avanceacumulado = Decimal((planillaacumulada / presupuesto.valor) * 100).quantize(Decimal('.01'))
                    totalfecha = Decimal(planilla.monto - planillaanteriores).quantize(Decimal('.01'))
                    aprobacion = AprobacionPresupuestoObra.objects.filter(presupuestoobra=presupuesto)[0]
                    detalles = planilla.detalleplanillapresupuestoobra_set.all()
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=planilla.xls'
                    book = xlwt.Workbook()
                    style = xlwt.easyxf('font: height 150, bold on; border: left thin, right thin, top thin, bottom thin; align: wrap on, vert centre, horiz center;')
                    style1 = xlwt.easyxf('font: bold on; align: wrap on, vert centre, horiz center;')
                    style2 = xlwt.easyxf('font: bold on; align: wrap on, vert centre;')
                    style3 = xlwt.easyxf('font: height 150; border: left thin, right thin, top thin, bottom thin; align: wrap on, vert centre, horiz center;')
                    style4 = xlwt.easyxf('font: height 150, bold on; border: left thin, right thin, top thin, bottom thin; align: wrap on, vert centre;')
                    style5 = xlwt.easyxf('font: bold on; align: wrap on, vert centre, horiz center;')
                    stylefecha = xlwt.easyxf(num_format_str='dd/mm/yyyy')
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'dd/mm/yyyy'
                    sheet1 = book.add_sheet('PLANILLA')
                    estilo = xlwt.easyxf('font: height 300, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    estilo1 = xlwt.easyxf('font: height 170, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    estilo2 = xlwt.easyxf('font: height 150, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    estilo3 = xlwt.easyxf('font: height 120, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    estilo4 = xlwt.easyxf('font: height 150, name Arial, colour_index black, bold on, italic on; align: wrap on;')
                    estilo5 = xlwt.easyxf('font: height 150, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    sheet1.write_merge(1, 1, 1, 15, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                    sheet1.write_merge(2, 2, 1, 15, 'DIRECCION DE OBRS UNIVERSITARIAS', estilo1)
                    sheet1.write_merge(3, 3, 1, 15, 'PLANILLA UNICA ' + planilla.rep_planilla(), estilo1)
                    sheet1.write_merge(4, 4, 1, 2, 'CONTRATISTA: ' + aprobacion.contratista, estilo4)
                    sheet1.write_merge(5, 5, 1, 2, 'CONTRATO N: ' + str(aprobacion.contratonumero), estilo4)
                    sheet1.write_merge(6, 6, 5, 6, 'PLANILLA: ', style)
                    sheet1.write_merge(6, 6, 7, 8, str(planilla.monto), style)
                    sheet1.write_merge(7, 7, 6, 6, 'PERIODO: ', style)
                    sheet1.write_merge(7, 7, 7, 8, str(planilla.periodoinicio.date().strftime("%d-%m-%Y")), style)
                    sheet1.write_merge(8, 8, 7, 8, str(planilla.periodofin.date().strftime("%d-%m-%Y")), style)
                    sheet1.write_merge(6, 6, 10, 11, 'MONTO DEL CONTRATO: ', style)
                    sheet1.write_merge(6, 6, 12, 13, str(presupuesto.valor), style)
                    sheet1.write_merge(7, 7, 10, 11, 'ANTICIPO RECIBIDO: ', style)
                    sheet1.write_merge(7, 7, 12, 13, str(presupuesto.valoranticipo if presupuesto.valoranticipo else '-'), style)
                    sheet1.write_merge(8, 8, 10, 11, 'DESCONTADO A LA FECHA: ', style)
                    sheet1.write_merge(8, 8, 12, 13, '-', style)
                    sheet1.write_merge(9, 9, 10, 11, 'POR DESCONTAR: ', style)
                    sheet1.write_merge(9, 9, 12, 13, '-', style)
                    sheet1.write_merge(7, 7, 1, 1, 'OBRA: ', estilo1)
                    sheet1.write_merge(8, 9, 1, 2, presupuesto.descripcion, style)
                    sheet1.col(0).width = 1000
                    sheet1.col(1).width = 1700
                    sheet1.col(2).width = 15000
                    sheet1.col(3).width = 2400
                    sheet1.col(4).width = 2600
                    sheet1.col(5).width = 2600
                    sheet1.col(6).width = 2600
                    sheet1.col(7).width = 2600
                    sheet1.col(8).width = 2600
                    sheet1.col(9).width = 2600
                    sheet1.col(10).width = 2600
                    sheet1.col(11).width = 2600
                    sheet1.col(12).width = 2600
                    sheet1.col(13).width = 2600
                    sheet1.col(14).width = 2600
                    sheet1.col(15).width = 2600
                    sheet1.write_merge(11, 12, 1, 1, 'ITEM', style)
                    sheet1.write_merge(11, 12, 2, 2, 'DESCRIPCION', style)
                    sheet1.write_merge(11, 12, 3, 3, 'UNIDAD', style)
                    sheet1.write_merge(11, 12, 4, 4, 'CANTIDAD CONTRATO', style)
                    sheet1.write_merge(11, 12, 5, 5, 'PRECIO UNITARIO', style)
                    sheet1.write_merge(11, 12, 6, 6, 'PRECIO TOTAL', style)
                    sheet1.write_merge(11, 11, 7, 9, 'AVANCE DE OBRA', style)
                    sheet1.write_merge(12, 12, 7, 7, 'CANTIDAD', style)
                    sheet1.write_merge(12, 12, 8, 8, '%', style)
                    sheet1.write_merge(12, 12, 9, 9, 'COSTO', style)
                    sheet1.write_merge(11, 11, 10, 12, 'PLANILLAS ANTERIORES', style)
                    sheet1.write_merge(12, 12, 10, 10, 'CANTIDAD', style)
                    sheet1.write_merge(12, 12, 11, 11, '%', style)
                    sheet1.write_merge(12, 12, 12, 12, 'COSTO', style)
                    sheet1.write_merge(11, 11, 13, 15, 'TOTAL A LA FECHA', style)
                    sheet1.write_merge(12, 12, 13, 13, 'CANTIDAD', style)
                    sheet1.write_merge(12, 12, 14, 14, '%', style)
                    sheet1.write_merge(12, 12, 15, 15, 'COSTO', style)
                    a = 13
                    nivel1 = 13
                    item1 = 1
                    for detalle in detalles:
                        descripcion = ''
                        unidadmedida = ''
                        cantidad = 0
                        preciounitario = 0
                        valor = 0
                        if detalle.planillapresupuestoobra.tipoplanilla != 3:
                            descripcion = detalle.recursoactividadpresupuestobra.descripcion
                            unidadmedida = detalle.recursoactividadpresupuestobra.unidadmedida.descripcion
                            cantidad = Decimal(detalle.recursoactividadpresupuestobra.cantidad).quantize(Decimal('.01'))
                            preciounitario = Decimal(detalle.recursoactividadpresupuestobra.preciounitario).quantize(Decimal('.01'))
                            valor = detalle.recursoactividadpresupuestobra.valor
                        if detalle.planillapresupuestoobra.tipoplanilla == 3:
                            descripcion = detalle.extra
                            unidadmedida = ''
                            cantidad = ''
                            preciounitario = ''
                            valor = ''
                        sheet1.write_merge(nivel1, nivel1 + 1, 1, 1, str(item1), style3)
                        sheet1.write_merge(nivel1, nivel1 + 1, 2, 2, descripcion, style3)
                        sheet1.write_merge(nivel1, nivel1 + 1, 3, 3, unidadmedida, style3)
                        sheet1.write_merge(nivel1, nivel1 + 1, 4, 4, str(cantidad), style3)
                        sheet1.write_merge(nivel1, nivel1 + 1, 5, 5, '$' + str(preciounitario), style3)
                        sheet1.write_merge(nivel1, nivel1 + 1, 6, 6, '$' + str(valor), style3)
                        sheet1.write_merge(nivel1, nivel1 + 1, 7, 7, '$' + str(detalle.cantidadavance), style3)
                        sheet1.write_merge(nivel1, nivel1 + 1, 8, 8, str(detalle.porcentajeavance), style3)
                        sheet1.write_merge(nivel1, nivel1 + 1, 9, 9, '$' + str(detalle.costoavance), style3)
                        sheet1.write_merge(nivel1, nivel1 + 1, 10, 10, '$' + str(detalle.cantidadanterior), style3)
                        sheet1.write_merge(nivel1, nivel1 + 1, 11, 11, str(detalle.porcentajeanterior), style3)
                        sheet1.write_merge(nivel1, nivel1 + 1, 12, 12, '$' + str(detalle.costoanterior), style3)
                        sheet1.write_merge(nivel1, nivel1 + 1, 13, 13, '$' + str(detalle.cantidadacumulada), style3)
                        sheet1.write_merge(nivel1, nivel1 + 1, 14, 14, str(detalle.porcentajeacumulada), style3)
                        sheet1.write_merge(nivel1, nivel1 + 1, 15, 15, '$' + str(detalle.costoacumulada), style3)
                        nivel1 += 2
                        item1 += 1
                    nivel1 += 3
                    sheet1.write_merge(nivel1, nivel1, 4, 6, 'LIQUIDACION DE PLANILLA ', style4)
                    sheet1.write_merge(nivel1, nivel1, 7, 7, '', style)
                    sheet1.write_merge(nivel1, nivel1, 8, 11, 'RESUMEN DE DEDUCCIONES', style)
                    sheet1.write_merge(nivel1, nivel1, 13, 15, 'AVANCE FISICO PONDERADO', style)
                    nivel1 += 1
                    sheet1.write_merge(nivel1, nivel1, 4, 6, 'VALOR DE LA PLANILLA', style4)
                    sheet1.write_merge(nivel1, nivel1, 7, 7, '$' + str(planilla.monto), style)
                    sheet1.write_merge(nivel1, nivel1, 8, 11, 'DEDUCCIONES', style4)
                    sheet1.write_merge(nivel1, nivel1, 13, 13, '', style4)
                    sheet1.write_merge(nivel1, nivel1, 14, 14, 'PLANILLA', style4)
                    sheet1.write_merge(nivel1, nivel1, 15, 15, 'ACUMULADO', style4)
                    nivel1 += 1
                    sheet1.write_merge(nivel1, nivel1, 4, 6, 'SUBTOTAL', style4)
                    sheet1.write_merge(nivel1, nivel1, 7, 7, '$' + str(planilla.monto), style)
                    sheet1.write_merge(nivel1, nivel1, 8, 10, 'ESTA PLANILLA', style4)
                    sheet1.write_merge(nivel1, nivel1, 11, 11, '$' + str(planilla.monto), style)
                    sheet1.write_merge(nivel1, nivel1, 13, 13, 'PROGRAM.', style4)
                    sheet1.write_merge(nivel1, nivel1, 14, 14, '100%', style4)
                    sheet1.write_merge(nivel1, nivel1, 15, 15, '100%', style4)
                    nivel1 += 1
                    sheet1.write_merge(nivel1, nivel1, 4, 6, 'SALDO DEL ANTICIPO', style4)
                    sheet1.write_merge(nivel1, nivel1, 7, 7, '$' + str(planilla.valoranticipo), style)
                    sheet1.write_merge(nivel1, nivel1, 8, 10, 'TOTAL ANTERIORES PLANTILLA', style4)
                    sheet1.write_merge(nivel1, nivel1, 11, 11, str(planillaanteriores), style)
                    sheet1.write_merge(nivel1, nivel1, 13, 13, 'EJECUTADO', style4)
                    sheet1.write_merge(nivel1, nivel1, 14, 14, str(avanceejecutado) + '%', style4)
                    sheet1.write_merge(nivel1, nivel1, 15, 15, str(avanceacumulado) + '%', style4)
                    nivel1 += 1
                    sheet1.write_merge(nivel1, nivel1, 4, 6, '', style)
                    sheet1.write_merge(nivel1, nivel1, 7, 7, '', style)
                    sheet1.write_merge(nivel1, nivel1, 8, 10, 'TOTAL A LA FECHA', style4)
                    sheet1.write_merge(nivel1, nivel1, 11, 11, str(totalfecha), style)
                    sheet1.write_merge(nivel1, nivel1, 13, 15, 'PERIODO DE EJECUCION', style)
                    nivel1 += 1
                    sheet1.write_merge(nivel1, nivel1, 4, 6, '', style)
                    sheet1.write_merge(nivel1, nivel1, 7, 7, '', style)
                    sheet1.write_merge(nivel1, nivel1, 8, 10, 'VALOR ANTICIPO', style4)
                    sheet1.write_merge(nivel1, nivel1, 11, 11, str(planilla.valoranticipo), style)
                    sheet1.write_merge(nivel1, nivel1, 13, 14, 'DESDE', style)
                    sheet1.write_merge(nivel1, nivel1, 15, 15, str(planilla.periodoinicio.date().strftime("%d-%m-%Y")), style)
                    nivel1 += 1
                    sheet1.write_merge(nivel1, nivel1, 4, 6, '', style)
                    sheet1.write_merge(nivel1, nivel1, 7, 7, '', style)
                    sheet1.write_merge(nivel1, nivel1, 8, 10, 'SALDO DEL ANTICIPO', style4)
                    sheet1.write_merge(nivel1, nivel1, 11, 11, str(planilla.saldoanticipo), style)
                    sheet1.write_merge(nivel1, nivel1, 13, 14, 'HASTA', style)
                    sheet1.write_merge(nivel1, nivel1, 15, 15, str(planilla.periodofin.date().strftime("%d-%m-%Y")), style)
                    nivel1 += 1
                    sheet1.write_merge(nivel1, nivel1 + 1, 4, 6, 'TOTAL A PAGARSE SIN DESCONTAR IMPUESTOS', style)
                    sheet1.write_merge(nivel1, nivel1 + 1, 7, 7, '$' + str(planilla.montoapagar), style)

                    nivel1 += 8
                    sheet1.write_merge(nivel1, nivel1, 2, 2, aprobacion.administradorcontrato, estilo5)
                    sheet1.write_merge(nivel1, nivel1, 4, 8, aprobacion.fiscalizador, estilo5)
                    sheet1.write_merge(nivel1, nivel1, 11, 15, aprobacion.contratista, estilo5)
                    nivel1 += 1
                    sheet1.write_merge(nivel1, nivel1, 2, 2, '________________________________________________________', estilo5)
                    sheet1.write_merge(nivel1, nivel1, 4, 8, '________________________________________________________', estilo5)
                    sheet1.write_merge(nivel1, nivel1, 11, 15, '________________________________________________________', estilo5)
                    nivel1 += 1
                    sheet1.write_merge(nivel1, nivel1, 2, 2, 'ADMINISTRADOR DEL CONTRATO', estilo5)
                    sheet1.write_merge(nivel1, nivel1, 4, 8, 'FISCALIZADOR', estilo5)
                    sheet1.write_merge(nivel1, nivel1, 11, 15, 'CONTRATISTA', estilo5)

                    book.save(response)
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Planilla Presupuesto'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                planillas = PlanillaPresupuestoObra.objects.filter(presupuestoobra__descripcion__icontains=search, status=True)
            elif 'id' in request.GET:
                ids = request.GET['id']
                planillas = PlanillaPresupuestoObra.objects.filter(id=ids)
            else:
                planillas = PlanillaPresupuestoObra.objects.filter(status=True)
            paging = MiPaginador(planillas, 25)
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
            data['planillas'] = page.object_list
            return render(request, "ob_planillapresupuesto/view.html", data)