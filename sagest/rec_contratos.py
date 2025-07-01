# -*- coding: UTF-8 -*-
import json
from datetime import date, datetime
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module
from sagest.forms import ContratoRecaudacionForm, \
    DetalleContratoRecaudacionForm
from sagest.models import CatalogoBien, ContratoRecaudacion, \
    DetalleContratoRecaudacion, IvaAplicado, TipoOtroRubro, Rubro
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre, proximafecha, convertir_fecha


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = ContratoRecaudacionForm(request.POST, request.FILES)
                if f.is_valid():
                    datos = json.loads(request.POST['lista_items1'])
                    nfile = None
                    if 'archivo' in request.FILES:
                        nfile = request.FILES['archivo']
                        nfile._name = generar_nombre("contratos", nfile._name)
                    if not datos:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe especificar los valores del contrato."})
                    contrato = ContratoRecaudacion(cliente_id=f.cleaned_data['cliente'],
                                                   numero=f.cleaned_data['numero'],
                                                   fechainicio=f.cleaned_data['fechainicio'],
                                                   fechafin=f.cleaned_data['fechafin'],
                                                   descripcion=f.cleaned_data['descripcion'],
                                                   diacobro=f.cleaned_data['diacobro'],
                                                   tipoarriendo=f.cleaned_data['tipoarriendo'],
                                                   archivo=nfile,
                                                   lugar=f.cleaned_data['lugar'],
                                                   finalizado=False)
                    contrato.save(request)
                    for elemento in datos:
                        detallesalprod = DetalleContratoRecaudacion(contrato=contrato,
                                                                    rubro_id=elemento['nombre'],
                                                                    iva_id=elemento['iva'],
                                                                    porcientorecargo=int(elemento['recargo']),
                                                                    recargo=True if int(elemento['recargo']) > 0 else False,
                                                                    valor=float(elemento['valor']))
                        detallesalprod.save(request)
                    contrato.save(request)
                    log(u'Adiciono nuevo contrato: %s' % contrato, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                f = ContratoRecaudacionForm(request.POST, request.FILES)
                if f.is_valid():
                    datos = json.loads(request.POST['lista_items1'])
                    nfile = None
                    if 'archivo' in request.FILES:
                        nfile = request.FILES['archivo']
                        nfile._name = generar_nombre("contratos", nfile._name)
                    if not datos:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe especificar los valores del contrato."})
                    contrato = ContratoRecaudacion.objects.get(pk=request.POST['id'])
                    contrato.numero = f.cleaned_data['numero']
                    contrato.fechainicio = f.cleaned_data['fechainicio']
                    contrato.fechafin = f.cleaned_data['fechafin']
                    contrato.descripcion = f.cleaned_data['descripcion']
                    contrato.diacobro = f.cleaned_data['diacobro']
                    contrato.tipoarriendo = f.cleaned_data['tipoarriendo']
                    contrato.lugar = f.cleaned_data['lugar']
                    contrato.save(request)
                    contrato.detallecontratorecaudacion_set.all().delete()
                    for elemento in datos:
                        detallesalprod = DetalleContratoRecaudacion(contrato=contrato,
                                                                    rubro_id=elemento['nombre'],
                                                                    iva_id=elemento['iva'],
                                                                    porcientorecargo=int(elemento['recargo']),
                                                                    recargo=True if int(elemento['recargo']) > 0 else False,
                                                                    valor=float(elemento['valor']))
                        detallesalprod.save(request)
                    contrato.save(request)

                    log(u'Modifico contrato: %s' % contrato, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'generarrubro':
            try:
                contrato = ContratoRecaudacion.objects.get(pk=request.POST['id'])
                if contrato.rubro_set.exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Ya existen rubros asociados a este contrato."})
                fechacobro = contrato.fechainicio
                fechacobrofinal = fechacobro
                for cuota in range(contrato.meses()):
                    if cuota == 0:
                        if fechacobro.day >= contrato.diacobro:
                            fechacobrofinal = date(fechacobro.year, fechacobro.month, fechacobro.day)
                        else:
                            fechacobrofinal = contrato.fechainicio
                    else:
                        fechacobrofinal = proximafecha(fechacobrofinal, 3, contrato.diacobro)
                    for detalle in contrato.detallecontratorecaudacion_set.all():
                        valor_iva = 0
                        recargo = Decimal(Decimal(detalle.valor * detalle.porcientorecargo) / 100).quantize(Decimal('.01'))
                        if detalle.iva == 2:
                            valor_iva = Decimal(detalle.valor * 0.12).quantize(Decimal('.01'))
                        if detalle.iva == 3:
                            valor_iva = Decimal(detalle.valor * 0.14).quantize(Decimal('.01'))
                        valor_total = detalle.valor + valor_iva + recargo
                        rubro = Rubro(tipo=detalle.rubro,
                                      persona=contrato.cliente,
                                      nombre=detalle.rubro.nombre,
                                      contratorecaudacion=contrato,
                                      fecha=contrato.fechainicio,
                                      fechavence=fechacobrofinal,
                                      valor=detalle.valor,
                                      iva=detalle.iva,
                                      valoriva=valor_iva,
                                      valortotal=valor_total,
                                      saldo=valor_total,
                                      cancelado=False)
                        rubro.save(request)
                contrato.finalizado = True
                contrato.save(request)
                log(u'Adicionó rubros: %s' % contrato, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'extender':
            try:
                contrato = ContratoRecaudacion.objects.get(pk=int(request.POST['id']))
                fecha = convertir_fecha(request.POST['fecha'])
                mifechafin = contrato.fechafin
                if fecha < mifechafin:
                    return JsonResponse({"result": "bad", "mensaje": u"Ya existen rubros asociados a este contrato dentro de esa fecha."})
                fechacobro = mifechafin
                fechacobrofinal = fecha
                contrato.fechafin = fecha
                contrato.save(request)
                for cuota in range(contrato.meses_nuevo(fechacobro)):
                    if cuota == 0:
                        if fechacobro.day >= contrato.diacobro:
                            fechacobrofinal = date(fechacobro.year, fechacobro.month, fechacobro.day)
                        else:
                            fechacobrofinal = mifechafin
                    else:
                        fechacobrofinal = proximafecha(fechacobrofinal, 3, contrato.diacobro)
                    for detalle in contrato.detallecontratorecaudacion_set.all():
                        valor_iva = 0
                        recargo = Decimal(Decimal(detalle.valor * detalle.porcientorecargo) / 100).quantize(Decimal('.01'))
                        if detalle.iva == 2:
                            valor_iva = Decimal(detalle.valor * 0.12).quantize(Decimal('.01'))
                        if detalle.iva == 3:
                            valor_iva = Decimal(detalle.valor * 0.14).quantize(Decimal('.01'))
                        valor_total = detalle.valor + valor_iva + recargo
                        rubro = Rubro(tipo=detalle.rubro,
                                      persona=contrato.cliente,
                                      nombre=detalle.rubro.nombre,
                                      contratorecaudacion=contrato,
                                      fecha=contrato.fechainicio,
                                      fechavence=fechacobrofinal,
                                      valor=detalle.valor,
                                      iva=detalle.iva,
                                      valoriva=valor_iva,
                                      valortotal=valor_total,
                                      saldo=valor_total,
                                      cancelado=False)
                        rubro.save(request)
                contrato.finalizado = True
                contrato.save(request)
                log(u'Adicionó rubros: %s' % contrato, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'anular':
            try:
                contrato = ContratoRecaudacion.objects.get(pk=int(request.POST['id']))
                fechai = convertir_fecha(request.POST['fechai'])
                fechaf = convertir_fecha(request.POST['fechaf'])
                if contrato.rubro_set.filter(status=True, cancelado=False, fechavence__range=(fechai, fechaf)).exists():
                    for r in contrato.rubro_set.filter(status=True, cancelado=False, fechavence__range=(fechai, fechaf)):
                        r.status = False
                        r.save(request)
                    log(u'Eliminó rubros: %s' % contrato, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delete':
            try:
                catalogo = CatalogoBien.objects.get(pk=request.POST['id'])
                log(u'Elimino catalogo: %s' % catalogo, request, "del")
                catalogo.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'segotros':
            try:
                data['tiposotros'] = TipoOtroRubro.objects.filter(interface=True, activo=True)
                data['tiposiva'] = IvaAplicado.objects.filter(activo=True)
                data['hoy'] = datetime.now().date()
                template = get_template("rec_contratos/segotros.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({'result': 'bad', "mensaje": u"Error al obtener los datos."})

        if action == 'detalle_contrato':
            try:
                data['contrato'] = contrato = ContratoRecaudacion.objects.get(pk=int(request.POST['id']))
                data['detalles'] = contrato.detallecontratorecaudacion_set.all()
                template = get_template("rec_contratos/detalle_contrato.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Contratos'
                    data['form'] = ContratoRecaudacionForm()
                    data['form2'] = DetalleContratoRecaudacionForm()
                    return render(request, 'rec_contratos/add.html', data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Modificar Contrato'
                    data['contrato'] = contrato = ContratoRecaudacion.objects.get(pk=request.GET['id'])
                    data['contrato'] = contrato = ContratoRecaudacion.objects.get(pk=request.GET['id'])
                    data['detalles'] = contrato.detallecontratorecaudacion_set.all()
                    form = ContratoRecaudacionForm(initial={'fechainicio': contrato.fechainicio,
                                                            'cliente': contrato.cliente,
                                                            'fechafin': contrato.fechafin,
                                                            'descripcion': contrato.descripcion,
                                                            'diacobro': contrato.diacobro,
                                                            'tipoarriendo': contrato.tipoarriendo,
                                                            'lugar': contrato.lugar,
                                                            'archivo': contrato.archivo})
                    form.editar(contrato)
                    data['form'] = form
                    return render(request, 'rec_contratos/edit.html', data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar Catálogo'
                    data['catalogo'] = CatalogoBien.objects.get(pk=request.GET['id'])
                    return render(request, 'af_catalogo/delete.html', data)
                except Exception as ex:
                    pass

            if action == 'generarrubro':
                try:
                    data['title'] = u'Generar rubros'
                    data['contrato'] = ContratoRecaudacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "rec_contratos/generarrubro.html", data)
                except:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Contratos'
            search = None
            tipo = None
            if 's' in request.GET:
                search = request.GET['s']
            if search:
                contratos = ContratoRecaudacion.objects.filter(Q(cliente__nombres__icontains=search) |
                                                               Q(cliente__apellido1=search) |
                                                               Q(cliente__apellido2=search) |
                                                               Q(descripcion__icontains=search))
            else:
                contratos = ContratoRecaudacion.objects.filter(status=True)
            paging = MiPaginador(contratos, 25)
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
            data['fecha'] = datetime.now().date()
            data['search'] = search if search else ""
            data['contratos'] = page.object_list
            return render(request, "rec_contratos/view.html", data)
