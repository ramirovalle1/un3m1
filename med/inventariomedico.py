# -*- coding: latin-1 -*-
import json
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template

import os
from decorators import last_access
from decorators import secure_module
from investigacion.funciones import FORMATOS_CELDAS_EXCEL
from med.forms import InventarioMedicoLoteForm, AjusteInventarioMedicoLoteForm
from sagest.models import SalidaProducto, Producto, DetalleSalidaProducto
from med.models import InventarioMedicoLote, TIPOINVENTARIOMEDICO_CHOICES, InventarioMedico, InventarioMedicoMovimiento, RecepcionInsumo, RecepcionInsumoDetalle
from settings import SITE_STORAGE
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, null_to_decimal, convertir_fecha_invertida
from sga.templatetags.sga_extras import encrypt

import xlsxwriter


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = InventarioMedicoLoteForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['fechaelaboracion'] > f.cleaned_data['fechavencimiento']:
                        return JsonResponse({"result": "bad", "mensaje": u"Error fechas incorrectas."})
                    if InventarioMedico.objects.filter(codigobarra=f.cleaned_data['codigobarra']).exists():
                        inventariomedico = InventarioMedico.objects.filter(codigobarra=f.cleaned_data['codigobarra'])[0]
                    else:
                        inventariomedico = InventarioMedico(codigobarra=f.cleaned_data['codigobarra'],
                                                            nombre=f.cleaned_data['nombre'],
                                                            descripcion=f.cleaned_data['descripcion'],
                                                            tipo=int(f.cleaned_data['tipo']))
                        inventariomedico.save()
                        log(u'Adiciono inventario medico: %s' % inventariomedico, request, "add")

                    if InventarioMedicoLote.objects.filter(inventariomedico=inventariomedico, numero=f.cleaned_data['numero']).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Este producto ya existe con ese numero de lote"})
                    else:
                        invmedicolote = InventarioMedicoLote(inventariomedico=inventariomedico,
                                                             numero=f.cleaned_data['numero'],
                                                             fechaelaboracion=f.cleaned_data['fechaelaboracion'],
                                                             fechavencimiento=f.cleaned_data['fechavencimiento'],
                                                             costo=f.cleaned_data['costo'],
                                                             cantidad=f.cleaned_data['cantidad'])
                        invmedicolote.save()
                        log(u'Adiciono inventario medico lote: %s' % invmedicolote, request, "add")
                    movimiento = InventarioMedicoMovimiento(inventariomedicolote=invmedicolote,
                                                            numerodocumento=f.cleaned_data['documento'],
                                                            tipo=1,
                                                            fecha=datetime.now().date(),
                                                            cantidad=f.cleaned_data['cantidad'],
                                                            detalle=f.cleaned_data['detalle'],
                                                            entrega=None,
                                                            recibe=request.session['persona'])
                    movimiento.save()
                    log(u'Movimiento de inventario medico: %s' % movimiento, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editar':
            try:
                invmedicolote = InventarioMedicoLote.objects.get(pk=request.POST['id'])
                f = InventarioMedicoLoteForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['fechaelaboracion'] > f.cleaned_data['fechavencimiento']:
                        return JsonResponse({"result": "bad", "mensaje": u"Error fechas incorrectas."})
                    invmedicolote.fechaelaboracion = f.cleaned_data['fechaelaboracion']
                    invmedicolote.fechavencimiento = f.cleaned_data['fechavencimiento']
                    invmedicolote.costo = f.cleaned_data['costo']
                    invmedicolote.save()
                    log(u'Modifico inventario medico lote: %s' % invmedicolote, request, "edit")
                    invmedicolote.inventariomedico.descripcion = f.cleaned_data['descripcion']
                    invmedicolote.inventariomedico.tipo = f.cleaned_data['tipo']
                    invmedicolote.inventariomedico.save()
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'datos':
            try:
                if InventarioMedico.objects.filter(codigobarra=request.POST['codigobarra']).exists():
                    im = InventarioMedico.objects.filter(codigobarra=request.POST['codigobarra'])[0]
                    return JsonResponse({"result": "ok", "nombre": im.nombre, "descripcion": im.descripcion, "tipo": im.tipo})
                else:
                     raise NameError('Error')
            except Exception as ex:
                return JsonResponse({"result": "bad"})

        elif action == 'ajuste':
            try:
                f = AjusteInventarioMedicoLoteForm(request.POST)
                invmedicolote = InventarioMedicoLote.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    if int(f.cleaned_data['tipo']) == 2:
                        if invmedicolote.cantidad < f.cleaned_data['cantidad']:
                            return JsonResponse({"result": "bad", "mensaje": u"La cantidad no puede ser mayor a la existencia."})
                        invmedicolote.cantidad -= f.cleaned_data['cantidad']
                    else:
                        invmedicolote.cantidad += f.cleaned_data['cantidad']
                    invmedicolote.save(request)
                    movimiento = InventarioMedicoMovimiento(inventariomedicolote=invmedicolote,
                                                            numerodocumento=f.cleaned_data['documento'],
                                                            tipo=f.cleaned_data['tipo'],
                                                            fecha=datetime.now().date(),
                                                            cantidad=f.cleaned_data['cantidad'],
                                                            entrega=data['persona'],
                                                            recibe=data['persona'],
                                                            detalle=f.cleaned_data['detalle'])
                    movimiento.save(request)
                    log(u'Ajuste de inventario medico lote: %s' % invmedicolote, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addingresoinsumo':
            try:
                if not 'ids' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Obtengo los valores del formulario
                fechaingreso = datetime.strptime(request.POST['fechaingreso'], '%Y-%m-%d').date()
                totalingreso = request.POST['totalingreso']
                concepto = request.POST['concepto'].strip().upper()
                idsproducto = request.POST.getlist('idproducto[]')  # IDS de productos
                descripciones = request.POST.getlist('descripcion[]')  # Descripciones productos
                costostotales = request.POST.getlist('total[]')  # Costo totales de productos
                tipos = request.POST.getlist('tipo[]')  # Tipos
                lotes = request.POST.getlist('lote[]')  # Lotes
                fechaselabora = request.POST.getlist('fechaelabora[]')  # Fecha de elaboración
                fechasvence = request.POST.getlist('fechavence[]')  # Fecha de vencimiento
                cantidades = request.POST.getlist('cantidad[]')  # Cantidades
                costos = request.POST.getlist('costo[]')  # Costos

                # Consulto la salida de bodega
                salidaproducto = SalidaProducto.objects.get(pk=int(encrypt(request.POST['ids'])))

                # Validar que la fecha de ingreso sea mayor o igual a la de salida de productos
                if fechaingreso < salidaproducto.fechaoperacion.date():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de ingreso debe ser mayor o igual a la fecha de comprobante", "showSwal": "True", "swalType": "warning"})

                # Validar las fechas de elaboración y caducidad
                fila = 0
                for fechae, fechav in zip(fechaselabora, fechasvence):
                    fechae = datetime.strptime(fechae, '%Y-%m-%d').date()
                    fechav = datetime.strptime(fechav, '%Y-%m-%d').date()
                    fila += 1

                    if fechav < fechae:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha vence debe ser mayor a la fecha elabora en la fila # <b>{}</b> en el detalle de insumos recibidos".format(fila), "showSwal": "True", "swalType": "warning"})

                # Guardo el ingreso de recepción de insumos
                recepcioninsumo = RecepcionInsumo(
                    egresobodega=salidaproducto,
                    fecha=fechaingreso,
                    concepto=concepto,
                    total=totalingreso,
                    confirmada=False
                )
                recepcioninsumo.save(request)

                # Guardo el detalle de recepción de insumos
                for idproducto, descripcion, costototal, tipo, lote, fechaelabora, fechavence, cantidad, costo in zip(idsproducto, descripciones, costostotales, tipos, lotes, fechaselabora, fechasvence, cantidades, costos):
                    # Consulto el producto
                    producto = Producto.objects.get(pk=idproducto)

                    # Guardo el detalle
                    detallerecepcion = RecepcionInsumoDetalle(
                        recepcioninsumo=recepcioninsumo,
                        producto=producto,
                        descripcion=descripcion,
                        tipo=tipo,
                        lote=lote,
                        fechaelabora=fechaelabora,
                        fechavence=fechavence,
                        cantidad=cantidad,
                        costo=costo,
                        costototal=costototal
                    )
                    detallerecepcion.save(request)

                log(u'% agregó ingreso de insumos médicos: %s' % (persona, recepcioninsumo), request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editingresoinsumo':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                # Consulto la recepción de insumos
                recepcioninsumo = RecepcionInsumo.objects.get(pk=int(encrypt(request.POST['id'])))

                # Verifico que pueda editar
                if not recepcioninsumo.puede_editar():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"No se puede actualizar el Registro porque ya ha sido editado por otra instancia", "showSwal": "True", "swalType": "warning"})

                # Obtengo los valores del formulario
                fechaingreso = datetime.strptime(request.POST['fechaingreso'], '%Y-%m-%d').date()
                concepto = request.POST['concepto'].strip().upper()
                totalingreso = request.POST['totalingreso']
                idsreg = request.POST.getlist('idreg[]')  # IDS de detalles
                idsproducto = request.POST.getlist('idproducto[]')  # IDS de productos
                descripciones = request.POST.getlist('descripcion[]')  # Descripciones productos
                costostotales = request.POST.getlist('total[]')  # Costo totales de productos
                tipos = request.POST.getlist('tipo[]')  # Tipos
                lotes = request.POST.getlist('lote[]')  # Lotes
                fechaselabora = request.POST.getlist('fechaelabora[]')  # Fecha de elaboración
                fechasvence = request.POST.getlist('fechavence[]')  # Fecha de vencimiento
                cantidades = request.POST.getlist('cantidad[]')  # Cantidades
                costos = request.POST.getlist('costo[]')  # Costos
                insumos_e = json.loads(request.POST['lista_items1'])  # Insumos eliminados

                # Obtengo la salida de bodega
                salidaproducto = recepcioninsumo.egresobodega

                # Validar que la fecha de ingreso sea mayor o igual a la de salida de productos
                if fechaingreso < salidaproducto.fechaoperacion.date():
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de ingreso debe ser mayor o igual a la fecha de comprobante", "showSwal": "True", "swalType": "warning"})

                # Validar las fechas de elaboración y caducidad
                fila = 0
                for fechae, fechav in zip(fechaselabora, fechasvence):
                    fechae = datetime.strptime(fechae, '%Y-%m-%d').date()
                    fechav = datetime.strptime(fechav, '%Y-%m-%d').date()
                    fila += 1

                    if fechav < fechae:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha vence debe ser mayor a la fecha elabora en la fila # <b>{}</b> en el detalle de insumos recibidos".format(fila), "showSwal": "True", "swalType": "warning"})

                # Actualizo el ingreso de recepción de insumos
                recepcioninsumo.fecha = fechaingreso
                recepcioninsumo.concepto = concepto
                recepcioninsumo.total = totalingreso
                recepcioninsumo.save(request)

                # Guardo o actualizo el detalle de recepción de insumos
                for idreg, idproducto, descripcion, costototal, tipo, lote, fechaelabora, fechavence, cantidad, costo in zip(idsreg, idsproducto, descripciones, costostotales, tipos, lotes, fechaselabora, fechasvence, cantidades, costos):
                    # Si es nuevo registro
                    if int(idreg) == 0:
                        # Consulto el producto
                        producto = Producto.objects.get(pk=idproducto)

                        # Guardo el detalle
                        detallerecepcion = RecepcionInsumoDetalle(
                            recepcioninsumo=recepcioninsumo,
                            producto=producto,
                            descripcion=descripcion,
                            tipo=tipo,
                            lote=lote,
                            fechaelabora=fechaelabora,
                            fechavence=fechavence,
                            cantidad=cantidad,
                            costo=costo,
                            costototal=costototal
                        )
                    else:
                        # Actualizo detalle
                        detallerecepcion = RecepcionInsumoDetalle.objects.get(pk=idreg)
                        detallerecepcion.descripcion = descripcion
                        detallerecepcion.tipo = tipo
                        detallerecepcion.lote = lote
                        detallerecepcion.fechaelabora = fechaelabora
                        detallerecepcion.fechavence = fechavence
                        detallerecepcion.cantidad = cantidad
                        detallerecepcion.costo = costo
                        detallerecepcion.costototal = costototal

                    detallerecepcion.save(request)

                # Elimino los insumos que se borraron del detalle
                if insumos_e:
                    for insumo in insumos_e:
                        detallerecepcion = RecepcionInsumoDetalle.objects.get(pk=int(insumo['idreg']))
                        detallerecepcion.status = False
                        detallerecepcion.save(request)

                log(u'%s editó ingreso de insumos médicos: %s' % (persona, recepcioninsumo), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True, "id": request.POST['id']})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'confirmaringreso':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al enviar los datos", "showSwal": "True", "swalType": "error"})

                # Consulto la recepción de insumos
                recepcioninsumo = RecepcionInsumo.objects.get(pk=int(encrypt(request.POST['id'])))
                detalles = recepcioninsumo.detalles()

                # Actualizo el ingreso de recepción de insumos
                recepcioninsumo.confirmada = True
                recepcioninsumo.save(request)

                # Guardo los productos recibidos
                for detalle in detalles:
                    # Consulto el producto
                    producto = detalle.producto
                    saldoanterior = 0

                    # Si no existe en inventario médico lo creo
                    if not InventarioMedico.objects.values("id").filter(status=True, producto=producto).exists():
                        inventariomedico = InventarioMedico(
                            producto=producto,
                            codigobarra='',
                            nombre=detalle.descripcion,
                            descripcion=detalle.descripcion,
                            tipo=detalle.tipo,
                            stock=detalle.stock
                        )
                    else:
                        inventariomedico = InventarioMedico.objects.get(producto=producto, status=True)
                        inventariomedico.nombre = detalle.descripcion
                        inventariomedico.descripcion = detalle.descripcion
                        inventariomedico.tipo = detalle.tipo
                        inventariomedico.stock = inventariomedico.stock + detalle.cantidad

                    inventariomedico.save(request)

                    # Si no existe lote del producto se debe crear
                    if not InventarioMedicoLote.objects.values("id").filter(status=True, inventariomedico=inventariomedico, numero=detalle.lote).exists():
                        # Creo el lote
                        inventariomedicolote = InventarioMedicoLote(
                            inventariomedico=inventariomedico,
                            recepcioninsumo=recepcioninsumo,
                            numero=detalle.lote,
                            fechaelabora=detalle.fechaelabora,
                            fechavence=detalle.fechavence,
                            costo=detalle.costo,
                            cantidad=detalle.cantidad,
                            stock=detalle.cantidad,
                            costototal=detalle.costototal
                        )
                    else:
                        # Consulto el lote y actualizo valores
                        inventariomedicolote = InventarioMedicoLote.objects.get(status=True, inventariomedico=inventariomedico, numero=detalle.lote)

                        # Actualizo valores
                        inventariomedicolote.fechaelabora = detalle.fechaelabora
                        inventariomedicolote.fechavence = detalle.fechavence
                        inventariomedicolote.costo = detalle.costo
                        saldoanterior = inventariomedicolote.stock
                        inventariomedicolote.cantidad = inventariomedicolote.cantidad + detalle.cantidad
                        inventariomedicolote.stock = inventariomedicolote.stock + detalle.cantidad
                        inventariomedicolote.costototal = inventariomedicolote.costototal + detalle.costototal

                    inventariomedicolote.save(request)

                    # Creo el movimiento
                    movimientoinventario = InventarioMedicoMovimiento(
                        inventariomedicolote=inventariomedicolote,
                        numerodocumento=str(recepcioninsumo.egresobodega.numerodocumento),
                        tipo=1,
                        fecha=recepcioninsumo.fecha,
                        cantidad=detalle.cantidad,
                        saldoant=saldoanterior,
                        ingreso=detalle.cantidad,
                        saldo=detalle.cantidad + saldoanterior,
                        detalle='RECEPCIÓN INSUMOS MEDIANTE COMPROBANTE DE BODEGA # {}'.format(recepcioninsumo.egresobodega.numerodocumento)
                    )
                    movimientoinventario.save(request)

                log(u'%s confirmó ingreso de insumos médicos: %s' % (persona, recepcioninsumo), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro de ingreso de insumos médicos confirmado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Inventario Médico'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'inventario':
                try:
                    search, idt, filtro, url_vars = request.GET.get('s', ''), request.GET.get('idt', ''), (Q(status=True) & Q(inventariomedico__status=True)), '&action=' + action

                    if idt:
                        filtro = filtro & Q(inventariomedico__tipo=idt)
                        url_vars += '&idt=' + str(idt)

                    if search:
                        data['s'] = search
                        filtro = filtro & (Q(inventariomedico__codigobarra__icontains=search) | Q(inventariomedico__nombre__icontains=search) | Q(inventariomedico__descripcion__icontains=search))

                        url_vars += '&s=' + search

                    inventariosmedicoslotes = InventarioMedicoLote.objects.filter(filtro).order_by('inventariomedico__nombre').distinct()

                    paging = MiPaginador(inventariosmedicoslotes, 25)
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
                    data['url_vars'] = url_vars
                    data['inventariosmedicoslotes'] = page.object_list
                    data['title'] = u'Inventario Médico'
                    data['tiposinventariosmedicos'] = TIPOINVENTARIOMEDICO_CHOICES
                    data['idt'] = int(idt) if idt else ''
                    data['enlaceatras'] = "/inventariomedico"

                    return render(request, "inventariomedico/inventario.html", data)
                except Exception as ex:
                    pass

            elif action == 'movimientos':
                try:
                    title = u'Movimientos del Inventario'
                    inventariolote = InventarioMedicoLote.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['inventariolote'] = inventariolote
                    data['movimientos'] = inventariolote.movimientos()
                    template = get_template("inventariomedico/movimiento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': title})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'add':
                try:
                    data['title'] = u'Adicionar inventario médico'
                    form = InventarioMedicoLoteForm(initial={'fechaelaboracion': datetime.now().date(),
                                                             'fechavencimiento': datetime.now().date(),
                                                             'costo': 0,
                                                             'cantidad': 1})
                    data['form'] = form
                    return render(request, "inventariomedico/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'editar':
                try:
                    data['title'] = u'Editar inventario'
                    inventariolote = InventarioMedicoLote.objects.get(pk=request.GET['id'])
                    form = InventarioMedicoLoteForm(initial={'codigobarra': inventariolote.inventariomedico.codigobarra,
                                                             'nombre': inventariolote.inventariomedico.nombre,
                                                             'descripcion': inventariolote.inventariomedico.descripcion,
                                                             'numero': inventariolote.numero,
                                                             'tipo': inventariolote.inventariomedico.tipo,
                                                             'fechaelaboracion': inventariolote.fechaelaboracion,
                                                             'fechavencimiento': inventariolote.fechavencimiento,
                                                             'costo': inventariolote.costo})
                    form.editar()
                    data['form'] = form
                    data['inventario'] = inventariolote
                    return render(request, "inventariomedico/editar.html", data)
                except Exception as ex:
                    pass

            elif action == 'ajuste':
                try:
                    data['title'] = u'Ajuste de inventario'
                    inventariolote = InventarioMedicoLote.objects.get(pk=request.GET['id'])
                    form = AjusteInventarioMedicoLoteForm(initial={'cantidad': 1})
                    data['form'] = form
                    data['inventario'] = inventariolote
                    return render(request, "inventariomedico/ajuste.html", data)
                except Exception as ex:
                    pass

            elif action == 'addingresoinsumo':
                try:
                    data['title'] = u'Agregar Ingreso de Insumos Médicos'
                    data['fecha'] = datetime.now().date()
                    return render(request, "inventariomedico/addingresoinsumo.html", data)
                except Exception as ex:
                    pass

            elif action == 'verificarcomprobante':
                try:
                    comprobante = request.GET['comprobante'].strip()

                    # Verificar que el comprobante de egreso exista
                    if not SalidaProducto.objects.values("id").filter(status=True, numerodocumento=comprobante).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El comprobante de egreso de Bodega no existe", "showSwal": "True", "swalType": "warning"})

                    # Verificar que el comprobante de egreso corresponda a la Dirección de Bienestar Universitario
                    if not SalidaProducto.objects.values("id").filter(status=True, numerodocumento=comprobante, departamento_id=97).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El comprobante de egreso de Bodega no corresponde a la Dirección de Bienestar Universitario", "showSwal": "True", "swalType": "warning"})

                    # Verificar que el comprobante de egreso no haya sido registrado como ingreso de insumos
                    if RecepcionInsumo.objects.values("id").filter(status=True, egresobodega__numerodocumento=comprobante).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"Ya existe un Ingreso de insumos médicos con ese número de comprobante de egreso", "showSwal": "True", "swalType": "warning"})

                    salidaproducto = SalidaProducto.objects.get(status=True, numerodocumento=comprobante, departamento_id=97)

                    data['detalles'] = detalles = salidaproducto.detalle_productos()
                    cantidaddetalles = detalles.count()
                    data['fecha'] = datetime.now().date()

                    template = get_template("inventariomedico/detalleingresoinsumo.html")
                    json_content = template.render(data)

                    return JsonResponse({"result": "ok", "idsalida": encrypt(salidaproducto.id) , "fechacomprobante": salidaproducto.fechaoperacion.strftime('%d-%m-%Y'), "cantidaddetalles": cantidaddetalles, "total": null_to_decimal(salidaproducto.valor, 2), 'data': json_content})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al obtener los datos. %s" % (msg), "showSwal": "True", "swalType": "error"})

            elif action == 'addinsumo':
                try:
                    data['title'] = u'Agregar Insumo al Detalle'
                    data['ids'] = request.GET['ids']

                    template = get_template("inventariomedico/addinsumo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscarinsumo':
                try:
                    q = request.GET['q'].upper().strip()

                    insumos = DetalleSalidaProducto.objects.filter(
                        Q(producto__cuenta__cuenta__icontains=q) |
                        Q(producto__descripcion__icontains=q),
                        status=True,
                        salidaproducto__pk=int(encrypt(request.GET['ids']))
                    )

                    data = {"result": "ok", "results": [{"id": x.producto.id, "name": str(x.producto.flexbox_repr()), "idproducto": x.producto.id, "descripcion": x.producto.descripcion, "valor": x.valor} for x in insumos]}
                    return JsonResponse(data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'editingresoinsumo':
                try:
                    data['title'] = u'Editar Ingreso de Insumos Médicos'
                    data['recepcioninsumo'] = recepcioninsumo = RecepcionInsumo.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['detalles'] = detalles = recepcioninsumo.detalles()
                    data['cantidaddetalles'] = detalles.count()
                    data['fecha'] = datetime.now().date()
                    return render(request, "inventariomedico/editingresoinsumo.html", data)
                except Exception as ex:
                    pass

            elif action == 'reporteinsumosrecibidos':
                try:
                    recepcioninsumo = RecepcionInsumo.objects.get(pk=int(encrypt(request.GET['id'])))
                    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'bienestar'))

                    nombrearchivo = "INSUMOS_MEDICOS_RECIBIDOS_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xlsx"

                    # Create un nuevo archivo de excel y le agrega una hoja
                    workbook = xlsxwriter.Workbook(output_folder + '/' + nombrearchivo)
                    ws = workbook.add_worksheet("Listado")

                    fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])
                    fceldageneral = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdageneral"])
                    ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
                    fceldafecha = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdafecha"])
                    fceldamoneda = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdamoneda"])
                    ftitulo2izq = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo2izq"])
                    ftitulo3izq = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo3izq"])
                    fceldafechaDMA = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdafechaDMA"])
                    fceldamoneda = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdamoneda"])

                    ws.merge_range(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo2izq)
                    ws.merge_range(1, 0, 1, 8, 'DIRECCIÓN DE BIENESTAR UNIVERSITARIO', ftitulo2izq)
                    ws.merge_range(2, 0, 2, 8, 'ÁREA DE ATENCIÓN MÉDICA', ftitulo2izq)
                    ws.merge_range(3, 0, 3, 8, 'DETALLE DE INSUMOS MÉDICOS RECIBIDOS', ftitulo2izq)
                    ws.merge_range(4, 0, 4, 8, 'FECHA DE CORTE: ' + str(datetime.now().date().strftime("%d-%m-%Y")), ftitulo2izq)

                    columns = [
                        (u"N°", 4),
                        (u"CÓDIGO", 19),
                        (u"DESCRIPCIÓN", 60),
                        (u"TIPO", 20),
                        (u"LOTE", 12),
                        (u"FECHA ELABORA", 16),
                        (u"FECHA VENCE", 16),
                        (u"CANTIDAD", 15),
                        (u"COSTO", 15)
                    ]

                    row_num = 6
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                        ws.set_column(col_num, col_num, columns[col_num][1])

                    row_num = 7

                    detalles = recepcioninsumo.detalles()
                    secuencia = 1

                    for detalle in detalles:
                        ws.write(row_num, 0, secuencia, fceldageneral)
                        ws.write(row_num, 1, detalle.producto.cuenta.cuenta + "." + str(detalle.producto.codigo), fceldageneral)
                        ws.write(row_num, 2, detalle.descripcion, fceldageneral)
                        ws.write(row_num, 3, detalle.get_tipo_display(), fceldageneral)
                        ws.write(row_num, 4, detalle.lote, fceldageneral)
                        ws.write(row_num, 5, detalle.fechaelabora, fceldafechaDMA)
                        ws.write(row_num, 6, detalle.fechavence, fceldafechaDMA)
                        ws.write(row_num, 7, detalle.cantidad, fceldageneral)
                        ws.write(row_num, 8, detalle.costo, fceldamoneda)

                        row_num += 1
                        secuencia += 1

                    workbook.close()

                    ruta = "media/bienestar/" + nombrearchivo
                    return JsonResponse({'result': 'ok', 'archivo': ruta})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar el reporte. [%s]" % msg, "showSwal": "True", "swalType": "error"})

            elif action == 'reportegeneral':
                try:
                    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'bienestar'))

                    nombrearchivo = "INSUMOS_MEDICOS_EN_EXISTENCIA_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xlsx"

                    # Create un nuevo archivo de excel y le agrega una hoja
                    workbook = xlsxwriter.Workbook(output_folder + '/' + nombrearchivo)
                    ws = workbook.add_worksheet("Listado")

                    fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])
                    fceldageneral = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdageneral"])
                    ftitulo1 = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo1"])
                    fceldafecha = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdafecha"])
                    fceldamoneda = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdamoneda"])
                    ftitulo2izq = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo2izq"])
                    ftitulo3izq = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo3izq"])
                    fceldafechaDMA = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdafechaDMA"])

                    ws.merge_range(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo2izq)
                    ws.merge_range(1, 0, 1, 7, 'DIRECCIÓN DE BIENESTAR UNIVERSITARIO', ftitulo2izq)
                    ws.merge_range(2, 0, 2, 7, 'ÁREA DE ATENCIÓN MÉDICA', ftitulo2izq)
                    ws.merge_range(3, 0, 3, 7, 'LISTADO GENERAL DE EXISTENCIAS DE INSUMOS MÉDICOS', ftitulo2izq)
                    ws.merge_range(4, 0, 4, 7, 'FECHA DE CORTE: ' + str(datetime.now().date().strftime("%d-%m-%Y")), ftitulo2izq)

                    columns = [
                        (u"N°", 4),
                        (u"CÓDIGO", 19),
                        (u"PRODUCTO", 60),
                        (u"TIPO", 20),
                        (u"LOTE", 12),
                        (u"FECHA ELABORA", 16),
                        (u"FECHA VENCE", 16),
                        (u"STOCK DISPONIBLE", 15)
                    ]

                    row_num = 6
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fcabeceracolumna)
                        ws.set_column(col_num, col_num, columns[col_num][1])

                    row_num = 7

                    detalles = InventarioMedicoLote.objects.filter(status=True, inventariomedico__status=True).order_by('inventariomedico__nombre').distinct()

                    secuencia = 1

                    for detalle in detalles:
                        ws.write(row_num, 0, secuencia, fceldageneral)
                        ws.write(row_num, 1, detalle.inventariomedico.producto.cuenta.cuenta + "." + str(detalle.inventariomedico.producto.codigo), fceldageneral)
                        ws.write(row_num, 2, detalle.inventariomedico.nombre, fceldageneral)
                        ws.write(row_num, 3, detalle.inventariomedico.get_tipo_display(), fceldageneral)
                        ws.write(row_num, 4, detalle.numero, fceldageneral)
                        ws.write(row_num, 5, detalle.fechaelabora, fceldafechaDMA)
                        ws.write(row_num, 6, detalle.fechavence, fceldafechaDMA)
                        ws.write(row_num, 7, detalle.stock, fceldageneral)

                        row_num += 1
                        secuencia += 1

                    workbook.close()

                    ruta = "media/bienestar/" + nombrearchivo
                    return JsonResponse({'result': 'ok', 'archivo': ruta})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al generar el reporte. [%s]" % msg, "showSwal": "True", "swalType": "error"})

            return HttpResponseRedirect(request.path)
        else:
            try:
                search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''

                if search:
                    data['s'] = search
                    filtro = filtro & (Q(nombre__unaccent__icontains=search))
                    url_vars += '&s=' + search

                recepcionesinsumos = RecepcionInsumo.objects.filter(filtro).order_by('-fecha')

                paging = MiPaginador(recepcionesinsumos, 25)
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
                data['url_vars'] = url_vars
                data['recepcionesinsumos'] = page.object_list
                data['title'] = u'Ingreso de Insumos Médicos'
                data['enlaceatras'] = "/"

                return render(request, "inventariomedico/view.html", data)
            except Exception as ex:
                pass
