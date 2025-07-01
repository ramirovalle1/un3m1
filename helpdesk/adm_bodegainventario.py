# -*- coding: latin-1 -*-
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import get_template
from django.contrib import messages

from sagest.models import GruposCategoria
from sga.templatetags.sga_extras import encrypt

from decorators import last_access, secure_module
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre

from helpdesk.models import BodegaProducto, BodegaUnidadMedida, BodegaTipoTransaccion, BodegaKardex, \
    DetalleFacturaCompra, FacturaCompra, BodegaProductoDetalle, actualizar_kardex_e_s
from helpdesk.forms import BodegaKardexForm, BodegaProductoForm, BodegaUnidadMedidaForm, BodegaTipoTransaccionForm, \
    Factura, DetalleFactura, GruposCategoriaForm, BodegaProductoDetalleForm
from decimal import Decimal
from sga.funcionesxhtml2pdf import conviert_html_to_pdf

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    hoy = datetime.now().date()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addregistro':
            try:
                with transaction.atomic():
                    form = BodegaKardexForm(request.POST)
                    if form.is_valid():
                        instance = BodegaKardex(factura=form.cleaned_data['factura'],
                                                producto=form.cleaned_data['producto'],
                                                tipotransaccion=form.cleaned_data['tipotransaccion'],
                                                unidadmedida=form.cleaned_data['unidadmedida'],
                                                cantidad=form.cleaned_data['cantidad']
                                                )
                        instance.save(request)
                        log(u'Adicionó bodega Kardex: %s' % instance, request, "add")
                        messages.success(request, 'Registro guardado con éxito.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)


        elif action == 'addfactura':
            try:
                if not request.POST.getlist('producto')[0]:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Ingrese un producto"})
                productos = request.POST.getlist('producto')
                unidadmedidas = request.POST.getlist('unidadmedida')
                cantidades = request.POST.getlist('cantidad')
                costos = request.POST.getlist('costo')
                subtotales = request.POST.getlist('subtotal')
                f = Factura(request.POST, request.FILES)
                if f.is_valid():
                    factura = FacturaCompra(codigo=f.cleaned_data['codigo'],
                                            fecha=f.cleaned_data['fecha'],
                                            proveedor=f.cleaned_data['proveedor'],
                                            total=f.cleaned_data['total'],
                                            detalle = f.cleaned_data['detalle']
                                            )
                    if 'archivo' in request.FILES:
                        archivo = request.FILES['archivo']
                        if archivo:
                            if archivo.size > 4485760:
                                raise NameError(u"Archivo mayor a 4 Mb.")
                            archivoname = archivo._name
                            ext = archivoname[archivoname.rfind("."):]
                            if not ext in ['.pdf','.jpg', '.jpeg', '.png']:
                                raise NameError(u"Solo archivo con extensión. pdf, jpg, jpeg.")
                            archivo._name = generar_nombre("facturacompra", archivo._name)
                        factura.archivo = archivo

                    factura.save(request)
                    log(u'Adicionó factura compra: %s' % factura, request, "add")
                    contador = 0
                    for producto in productos:
                        if contador < len(productos) - 1:
                            um = BodegaProductoDetalle.objects.get(pk=int(unidadmedidas[contador]))
                            valor_um = um.valor
                            detalle = DetalleFacturaCompra(factura=factura, producto_id=int(producto),
                                                           unidadmedida=um,
                                                           cantidad=int(cantidades[contador]),
                                                           costo=Decimal(costos[contador]),
                                                           total=Decimal(subtotales[contador]))
                            detalle.save(request)
                            log(u'Adicionó detalle factura compra: %s' % detalle, request, "add")

                            tipo = 1
                            cantidad = int(cantidades[contador])
                            if cantidad > 0:
                                cantidad = cantidad * valor_um
                            kardex = actualizar_kardex_e_s(tipo, cantidad, detalle)
                            kardex.save(request)
                            log(u'Adicionar Bodega Kardex: %s' % kardex, request, "add")
                            contador += 1
                        else:
                            break

                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})


        elif action == 'detalle_factura':
            try:
                data['factura'] = factura = FacturaCompra.objects.get(pk=int(request.POST['id']))
                data['detallefactura'] = detallefactura = DetalleFacturaCompra.objects.filter(factura=factura.id)

                template = get_template("adm_bodegainventario/modal/detallefactura.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'editregistro':
            try:
                with transaction.atomic():
                    filtro = BodegaKardex.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = BodegaKardexForm(request.POST)
                    if f.is_valid():
                        filtro.factura = f.cleaned_data['factura']
                        filtro.producto = f.cleaned_data['producto']
                        filtro.tipotransaccion = f.cleaned_data['tipotransaccion']
                        filtro.unidadmedida = f.cleaned_data['unidadmedida']
                        filtro.cantidad = f.cleaned_data['cantidad']
                        filtro.save(request)
                        log(u'Editó bodega kardex: %s' % filtro, request, "edit")
                        messages.success(request, 'Registro editado con éxito.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'delregistro':
            try:
                with transaction.atomic():
                    instancia = BodegaKardex.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó bodega kardex: %s' % instancia, request, "delete")
                    messages.success(request, 'Registro eliminado con éxito.')
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addproducto':
            try:
                with transaction.atomic():
                    form = BodegaProductoForm(request.POST)
                    if form.is_valid():
                        if not BodegaProducto.objects.filter(status= True, descripcion=form.cleaned_data['descripcion'].upper()).exists():
                            instance = BodegaProducto(descripcion=form.cleaned_data['descripcion'], grupo = form.cleaned_data['grupo'])
                            instance.save(request)
                            log(u'Adicionó bodega producto: %s' % instance, request, "add")

                            productodetalle = BodegaProductoDetalle(producto=instance,
                                                             unidadmedida=BodegaUnidadMedida.objects.get(pk=1),
                                                             valor=1)
                            productodetalle.save(request)
                            log(u'Adicionó Unidad Medida Producto: %s' % productodetalle, request, "add")

                            messages.success(request, 'Registro guardado con éxito.')
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            raise NameError(u'El registro ya existe.')
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'addgrupocategoria':
            try:
                with transaction.atomic():
                    form = GruposCategoriaForm(request.POST)
                    if form.is_valid():
                        if not GruposCategoria.objects.filter(status= True, descripcion=form.cleaned_data['descripcion'].upper()).exists():
                            instance = GruposCategoria(descripcion=form.cleaned_data['descripcion'], identificador = form.cleaned_data['identificador'])
                            instance.save(request)
                            log(u'Adicionar grupo: %s' % instance, request, "add")
                            messages.success(request, 'Registro guardado con éxito.')
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            raise NameError(u'El registro ya existe.')
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'editgrupocategoria':
            try:
                with transaction.atomic():
                    filtro = GruposCategoria.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = GruposCategoriaForm(request.POST)
                    if f.is_valid():

                        if not GruposCategoria.objects.filter(status= True, descripcion=f.cleaned_data['descripcion'].upper()).exists():
                            filtro.descripcion = f.cleaned_data['descripcion']
                            filtro.identificador = f.cleaned_data['identificador']
                            filtro.save(request)
                            log(u'Edita grupo: %s' % filtro, request, "edit")
                            messages.success(request, 'Registro editado con éxito.')
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            raise NameError(u'El registro ya existe.')

                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)


        elif action == 'editBodegaProductoDetalle':
            try:
                with transaction.atomic():
                    filtro = BodegaProductoDetalle.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = BodegaProductoDetalleForm(request.POST)
                    idp = request.GET['id']
                    p = BodegaProducto.objects.get(pk=idp)

                    if f.is_valid():
                        unidad_medida = f.cleaned_data['unidadmedida']
                        valor = f.cleaned_data['valor']

                        # Verificar si la unidad de medida y el valor ya existen en otro registro diferente
                        if BodegaProductoDetalle.objects.filter(producto=p, unidadmedida=unidad_medida,
                                                                valor=valor).exists():
                            raise NameError(u'El registro ya existe.')

                        # Verificar si la unidad de medida es la misma que la actual
                        if filtro.unidadmedida != unidad_medida:
                            # Verificar si la nueva unidad de medida ya existe en otro registro diferente
                            if BodegaProductoDetalle.objects.filter(producto=p, unidadmedida=unidad_medida).exists():
                                raise NameError(u'Medida ya existe.')
                            filtro.unidadmedida = unidad_medida

                        # Verificar si el valor es diferente al actual
                        if filtro.valor != valor:
                            if valor <= 0:
                                raise NameError(u'Equivalencia debe ser mayor a 1.')
                            # Verificar si el nuevo valor ya existe en otro registro diferente
                            if BodegaProductoDetalle.objects.filter(producto=p,
                                                                    valor=valor).exists():
                                raise NameError(u'Equivalencia existe.')
                            if filtro.valor == 1:
                                raise NameError(u'Esta equivalencia no puede ser modificada.')

                            filtro.valor = valor

                        filtro.save(request)
                        log(u'Edita BodegaProductoDetalle: %s' % filtro, request, "edit")
                        messages.success(request, 'Registro editado con éxito.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                             "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'delBodegaProductoDetalle':
            try:
                with transaction.atomic():
                    instancia = BodegaProductoDetalle.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó BodegaProductoDetalle: %s' % instancia, request, "delete")
                    messages.success(request, 'Registro eliminado con éxito.')
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)


        elif action == 'cargar_unidadesmedida':
            try:
                lista = []
                id = int(request.POST['id'])
                p = BodegaProducto.objects.get(pk=id, status=True)
                medidas = BodegaProductoDetalle.objects.filter(producto=p, status=True)
                for m in medidas:
                    lista.append([m.id, m.unidadmedida.descripcion])

                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


        elif action == 'delgrupocategoria':
            try:
                with transaction.atomic():
                    instancia = GruposCategoria.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó Grupo Categoria: %s' % instancia, request, "delete")
                    messages.success(request, 'Registro eliminado con éxito.')
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'editproducto':
            try:
                with transaction.atomic():
                    filtro = BodegaProducto.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = BodegaProductoForm(request.POST)
                    if f.is_valid():

                        if not BodegaProducto.objects.filter(status= True, descripcion=f.cleaned_data['descripcion'].upper(), grupo=f.cleaned_data['grupo']).exists():
                            filtro.descripcion = f.cleaned_data['descripcion']
                            filtro.grupo = f.cleaned_data['grupo']
                            filtro.save(request)
                            log(u'Editó bodega producto: %s' % filtro, request, "edit")
                            messages.success(request, 'Registro editado con éxito.')
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            raise NameError(u'El registro ya existe.')

                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'delproducto':
            try:
                with transaction.atomic():
                    instancia = BodegaProducto.objects.get(pk=int(encrypt(request.POST['id'])))

                    unidadesdemedidas = BodegaProductoDetalle.objects.filter(status=True, producto=instancia)
                    if unidadesdemedidas:
                        for u in unidadesdemedidas:
                            u.status = False
                            u.save(request)

                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó bodega producto: %s' % instancia, request, "delete")
                    messages.success(request, 'Registro eliminado con éxito.')
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)



        elif action == 'delfactura':
            try:
                with transaction.atomic():
                    instancia = FacturaCompra.objects.get(pk=int(encrypt(request.POST['id'])))
                    detallefacturas = DetalleFacturaCompra.objects.filter(status=True, factura= instancia)

                    for detallefactura in detallefacturas:
                        valor = detallefactura.unidadmedida.valor
                        kardex = BodegaKardex.objects.get(detallefactura=detallefactura)
                        tipo = 3
                        cantidad = detallefactura.cantidad
                        if cantidad > 0:
                            cantidad = cantidad * valor
                        kardex.status = False
                        kardex.save(request)
                        log(u'Eliminó Bodega Kardex: %s' % kardex, request, "delete")
                        instacia = detallefactura.actualizar_kardex(tipo, cantidad)
                        instacia.save(request)


                        detallefactura.status = False
                        detallefactura.save(request)
                        log(u'Eliminó detalle de factura: %s' % detallefactura, request, "delete")

                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó factura: %s' % instancia, request, "delete")
                    messages.success(request, 'Registro eliminado con éxito.')
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addunidadmedida':
            try:
                with transaction.atomic():
                    form = BodegaUnidadMedidaForm(request.POST)
                    if form.is_valid():
                        if not BodegaUnidadMedida.objects.values('id').filter(descripcion=form.cleaned_data['descripcion']).exists():
                            instance = BodegaUnidadMedida(descripcion=form.cleaned_data['descripcion'])
                            instance.save(request)
                            log(u'Adicionó bodega unidad medida: %s' % instance, request, "add")
                            messages.success(request, 'Registro guardado con éxito.')
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            raise NameError(u'El registro ya existe.')
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'addBodegaProductoDetalle':
            try:
                with transaction.atomic():
                    form = BodegaProductoDetalleForm(request.POST)
                    id = int(encrypt(request.POST['id']))
                    product = BodegaProducto.objects.get(pk=id)
                    if form.is_valid():
                        valor = form.cleaned_data['valor']
                        if valor <= 1:
                            raise NameError(u'Equivalencia de ser mayor a 1.')
                        if BodegaProductoDetalle.objects.values('id').filter(valor=valor, status=True, producto=product).exists():
                            raise NameError(u'Equivalencia ya existe.')
                        if not BodegaProductoDetalle.objects.values('id').filter(status = True, producto=product, unidadmedida=form.cleaned_data['unidadmedida']).exists():
                            instance = BodegaProductoDetalle(producto=product, unidadmedida=form.cleaned_data['unidadmedida'], valor=form.cleaned_data['valor'])
                            instance.save(request)
                            log(u'Adicionó Unidad de Medida Producto: %s' % instance, request, "add")
                            messages.success(request, 'Registro guardado con éxito.')
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            raise NameError(u'El registro ya existe.')
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'editunidadmedida':
            try:
                with transaction.atomic():
                    filtro = BodegaUnidadMedida.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = BodegaUnidadMedidaForm(request.POST)
                    if f.is_valid():
                        filtro.descripcion = f.cleaned_data['descripcion']
                        filtro.save(request)
                        log(u'Editó bodega unidad medida: %s' % filtro, request, "edit")
                        messages.success(request, 'Registro editado con éxito.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'delunidadmedida':
            try:
                with transaction.atomic():
                    instancia = BodegaUnidadMedida.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó bodega unidad medida: %s' % instancia, request, "delete")
                    messages.success(request, 'Registro eliminado con éxito.')
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addtipotransaccion':
            try:
                with transaction.atomic():
                    form = BodegaTipoTransaccionForm(request.POST)
                    if form.is_valid():
                        if not BodegaTipoTransaccion.objects.values('id').filter(descripcion=form.cleaned_data['descripcion']).exists():
                            instance = BodegaTipoTransaccion(descripcion=form.cleaned_data['descripcion'])
                            instance.save(request)
                            log(u'Adicionó bodega tipo transaccion: %s' % instance, request, "add")
                            messages.success(request, 'Registro guardado con éxito.')
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            raise NameError(u'El registro ya existe.')
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s' % ex}, safe=False)

        elif action == 'edittipotransaccion':
            try:
                with transaction.atomic():
                    filtro = BodegaTipoTransaccion.objects.get(pk=int(encrypt(request.POST['id'])))
                    f = BodegaTipoTransaccionForm(request.POST)
                    if f.is_valid():
                        filtro.descripcion = f.cleaned_data['descripcion']
                        filtro.save(request)
                        log(u'Editó bodega tipo transaccion: %s' % filtro, request, "edit")
                        messages.success(request, 'Registro editado con éxito.')
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": '%s'%ex}, safe=False)

        elif action == 'deltipotransaccion':
            try:
                with transaction.atomic():
                    instancia = BodegaTipoTransaccion.objects.get(pk=int(encrypt(request.POST['id'])))
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó bodega tipo transaccion: %s' % instancia, request, "delete")
                    messages.success(request, 'Registro eliminado con éxito.')
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addregistro':
                try:
                    form = BodegaKardexForm()
                    data['action'] = 'addregistro'
                    data['form'] = form
                    template = get_template("adm_bodegainventario/modal/formbodega.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editregistro':
                try:
                    data['id'] = request.GET['id']
                    data['action'] = 'editregistro'
                    data['filtro'] = filtro = BodegaKardex.objects.get(pk=request.GET['id'])
                    form = BodegaKardexForm(initial={'factura': filtro.factura,
                                                     'producto': filtro.producto,
                                                     'tipotransaccion': filtro.tipotransaccion,
                                                     'unidadmedida': filtro.unidadmedida,
                                                     'cantidad': filtro.cantidad
                                                     })
                    data['form'] = form
                    template = get_template("adm_bodegainventario/modal/formbodega.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'configuracion':
                try:
                    data['title'] = 'Configuración de Productos'
                    filtros, s, url_vars = Q(status=True), request.GET.get('s', ''), ''
                    data['count'] = BodegaProducto.objects.values("id").filter(filtros).count()
                    url_vars = "&action=configuracion"
                    if s:
                        filtros = filtros & (Q(descripcion__icontains=s))
                        data['s'] = f"{s}"
                        url_vars += f"&s={s}"
                    listado = BodegaProducto.objects.filter(filtros).order_by('id')
                    paging = MiPaginador(listado, 20)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    request.session['viewactivo'] = 1
                    return render(request, "adm_bodegainventario/viewproducto.html", data)
                except Exception as ex:
                    pass

            elif action == 'addproducto':
                try:
                    form = BodegaProductoForm()
                    data['action'] = 'addproducto'
                    data['form'] = form
                    template = get_template("adm_bodegainventario/modal/formconfiguracionproducto.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editproducto':
                try:
                    data['id'] = request.GET['id']
                    data['action'] = 'editproducto'
                    data['filtro'] = filtro = BodegaProducto.objects.get(pk=request.GET['id'])
                    form = BodegaProductoForm(initial={'descripcion': filtro.descripcion, 'grupo': filtro.grupo})
                    data['form'] = form
                    template = get_template("adm_bodegainventario/modal/formconfiguracionproducto.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'configunidadmedida':
                try:
                    data['title'] = 'Configuración de Unidad de Medida'
                    filtros, s, url_vars = Q(status=True), request.GET.get('s', ''), ''
                    data['count'] = BodegaUnidadMedida.objects.values("id").filter(filtros).count()
                    url_vars = "&action=configunidadmedida"
                    if s:
                        filtros = filtros & (Q(descripcion__icontains=s))
                        data['s'] = f"{s}"
                        url_vars += f"&s={s}"
                    listado = BodegaUnidadMedida.objects.filter(filtros).order_by('id')
                    paging = MiPaginador(listado, 20)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    request.session['viewactivo'] = 2
                    return render(request, "adm_bodegainventario/viewunidadmedida.html", data)
                except Exception as ex:
                    pass


            elif action == 'configBodegaProductoDetalle':
                try:

                    filtros, s, url_vars = Q(status=True), request.GET.get('s', ''), ''
                    id = int(request.GET['id'])
                    filtros = filtros & (Q(producto=id))
                    data['count'] = BodegaProductoDetalle.objects.values("id").filter(filtros).count()
                    pro = BodegaProducto.objects.get(pk=id)
                    data['title'] = 'Unidades de Medida: '+ pro.descripcion
                    data['id_producto'] = id
                    url_vars = "&action=configBodegaProductoDetalle"
                    if s:
                        filtros = filtros & (Q(descripcion__icontains=s))
                        data['s'] = f"{s}"
                        url_vars += f"&s={s}"
                    listado = BodegaProductoDetalle.objects.filter(filtros).order_by('valor')
                    paging = MiPaginador(listado, 20)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    request.session['viewactivo'] = 1
                    return render(request, "adm_bodegainventario/viewproductodetalle.html", data)
                except Exception as ex:
                    pass

            elif action == 'addunidadmedida':
                try:
                    form = BodegaUnidadMedidaForm()
                    data['action'] = 'addunidadmedida'
                    data['form'] = form
                    template = get_template("adm_bodegainventario/modal/formconfigunidadmedida.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addBodegaProductoDetalle':
                try:
                    data['id'] = request.GET['id']
                    data['action'] = 'addBodegaProductoDetalle'
                    data['filtro'] = filtro = BodegaProducto.objects.get(pk=request.GET['id'])
                    form = BodegaProductoDetalleForm(initial={'producto': filtro.id})
                    data['form'] = form
                    template = get_template("adm_bodegainventario/modal/formproductodetalle.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editBodegaProductoDetalle':
                try:
                    data['id'] = request.GET['id']
                    data['action'] = 'editBodegaProductoDetalle'
                    data['filtro'] = filtro = BodegaProductoDetalle.objects.get(pk=request.GET['id'])
                    form = BodegaProductoDetalleForm(initial={'producto': filtro.id, 'unidadmedida': filtro.unidadmedida, 'valor': filtro.valor})
                    data['form'] = form
                    template = get_template("adm_bodegainventario/modal/formproductodetalle.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addgrupocategoria':
                try:
                    form = GruposCategoriaForm()
                    data['action'] = 'addgrupocategoria'
                    data['form'] = form
                    template = get_template("adm_bodegainventario/modal/formgrupocategoria.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editgrupocategoria':
                try:
                    data['id'] = request.GET['id']
                    data['action'] = 'editgrupocategoria'
                    data['filtro'] = filtro = GruposCategoria.objects.get(pk=request.GET['id'])
                    form = GruposCategoriaForm(initial={'descripcion': filtro.descripcion, 'identificador': filtro.identificador})
                    data['form'] = form
                    template = get_template("adm_bodegainventario/modal/formgrupocategoria.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            elif action == 'editunidadmedida':
                try:
                    data['id'] = request.GET['id']
                    data['action'] = 'editunidadmedida'
                    data['filtro'] = filtro = BodegaUnidadMedida.objects.get(pk=request.GET['id'])
                    form = BodegaUnidadMedidaForm(initial={'descripcion': filtro.descripcion})
                    data['form'] = form
                    template = get_template("adm_bodegainventario/modal/formconfigunidadmedida.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'configtipotransaccion':
                try:
                    data['title'] = 'Configuración de Tipo de Transacción'
                    filtros, s, url_vars = Q(status=True), request.GET.get('s', ''), ''
                    data['count'] = BodegaTipoTransaccion.objects.values("id").filter(filtros).count()
                    url_vars = "&action=configtipotransaccion"
                    if s:
                        filtros = filtros & (Q(descripcion__icontains=s))
                        data['s'] = f"{s}"
                        url_vars += f"&s={s}"
                    listado = BodegaTipoTransaccion.objects.filter(filtros).order_by('id')
                    paging = MiPaginador(listado, 20)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    request.session['viewactivo'] = 3
                    return render(request, "adm_bodegainventario/viewtipotransaccion.html", data)
                except Exception as ex:
                    pass

            elif action == 'configfacturacompra':
                try:
                    data['title'] = 'Registro de Facturas'
                    filtros, s, url_vars = Q(status=True), request.GET.get('s', ''), ''

                    url_vars = "&action=configfacturacompra"
                    if s:
                        filtros = filtros & (Q(codigo__icontains=s))
                        data['s'] = f"{s}"
                        url_vars += f"&s={s}"

                    listado = FacturaCompra.objects.filter(filtros).order_by('id')
                    paging = MiPaginador(listado, 20)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    request.session['viewactivo'] = 4
                    return render(request, "adm_bodegainventario/viewfacturacompra.html", data)
                except Exception as ex:
                    pass

            elif action == 'configgrupocategoria':
                try:
                    data['title'] = u'Grupos categoria'
                    filtros, s, url_vars = Q(status=True), request.GET.get('s', ''), ''
                    url_vars = "&action=configgrupocategoria"
                    if s:
                        filtros = filtros & (Q(descripcion__icontains=s))
                        data['s'] = f"{s}"
                        url_vars += f"&s={s}"
                    listado = GruposCategoria.objects.filter(filtros).order_by('-id')
                    paging = MiPaginador(listado, 20)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    request.session['viewactivo'] = 5
                    return render(request, "adm_bodegainventario/viewgrupocategoria.html", data)
                except Exception as ex:
                    pass

            if action == 'editfacturacompra':
                try:
                    id = int(encrypt(request.GET['id']))
                    fact = FacturaCompra.objects.get(pk=id)
                    form = Factura(initial={'codigo': fact.codigo, 'fecha': fact.fecha, 'proveedor': fact.proveedor, 'total': fact.total})
                    data['form'] = form

                    return render(request, "adm_bodegainventario/addfactura.html")
                except Exception as ex:
                    pass

            if action == 'addfactura':
                try:
                    form = Factura()
                    form2 = DetalleFactura()
                    data['form'] = form

                    data['form2'] = form2

                    data['title'] = 'Ingreso de Factura'

                    return render(request, "adm_bodegainventario/addfactura.html", data)
                except Exception as ex:
                    pass

            elif action == 'addtipotransaccion':
                try:
                    form = BodegaTipoTransaccionForm()
                    data['action'] = 'addtipotransaccion'
                    data['form'] = form
                    template = get_template("adm_bodegainventario/modal/formconfigtipotransaccion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edittipotransaccion':
                try:
                    data['id'] = request.GET['id']
                    data['action'] = 'edittipotransaccion'
                    data['filtro'] = filtro = BodegaTipoTransaccion.objects.get(pk=request.GET['id'])
                    form = BodegaTipoTransaccionForm(initial={'descripcion': filtro.descripcion})
                    data['form'] = form
                    template = get_template("adm_bodegainventario/modal/formconfigtipotransaccion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'pdfreportebodegakardex':
                mensaje = "Problemas al Imprimir Reporte."
                try:
                    filtros = Q(status=True)
                    producto = 0
                    if 'producto' in request.GET:
                        producto = int(request.GET['producto'])

                    if producto > 0:
                        data['producto'] = producto
                        filtros = filtros & Q(producto_id=producto)

                    results = BodegaKardex.objects.filter(filtros).order_by('producto__id', 'fecha').distinct(
                        'producto__id', 'fecha')
                    data['results'] = results
                    data['hoy'] = str(datetime.now().date())
                    # return conviert_html_to_pdf_name(
                    #     'inventario_activofijo/informes/activotecnologicopdf.html',
                    #     {'pagesize': 'A4', 'data': data,}, nombrearchivo)
                    return conviert_html_to_pdf(
                        '../templates/adm_bodegainventario/reportes/pdfreportekardex.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        },
                    )

                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Bodega de Inventario'
                filtros, s, url_vars = '', request.GET.get('s', ''), ''
                filtros = Q(status=True)
                if s:
                    filtros = filtros & (Q(producto__descripcion__icontains=s) |
                                         Q(tipotransaccion__descripcion__icontains=s) |
                                         Q(cantidad__icontains=s) |
                                         Q(unidadmedida__unidadmedida__descripcion__icontains=s)
                                         )
                    data['s'] = f"{s}"
                    url_vars += f"&s={s}"

                tipotransaccion = 0
                if 'tipotransaccion' in request.GET:
                    tipotransaccion = int(request.GET['tipotransaccion'])

                if tipotransaccion > 0:
                    data['tipotransaccion'] = tipotransaccion
                    filtros = filtros & Q(tipotransaccion_id=tipotransaccion)
                    url_vars += "&tipotransaccion={}".format(tipotransaccion)

                unidadmedida = 0
                if 'unidadmedida' in request.GET:
                    unidadmedida = int(request.GET['unidadmedida'])

                if unidadmedida > 0:
                    data['unidadmedida'] = unidadmedida
                    filtros = filtros & Q(unidadmedida_id=unidadmedida)
                    url_vars += "&unidadmedida={}".format(unidadmedida)

                producto = 0
                if 'producto' in request.GET:
                    producto = int(request.GET['producto'])

                if producto > 0:
                    data['producto'] = producto
                    filtros = filtros & Q(producto_id=producto)
                    url_vars += "&producto={}".format(producto)


                data['listatipotransaccion'] = BodegaTipoTransaccion.objects.filter(status=True)
                data['listaunidadmedida'] = BodegaProductoDetalle.objects.filter(status=True)
                data['listaproductos'] = BodegaProducto.objects.filter(status=True)
                #listado = BodegaKardex.objects.filter(filtros)

                if filtros:
                    listado = BodegaKardex.objects.filter(filtros).order_by('-fecha', 'producto__id').distinct('producto__id', 'fecha')
                else:
                    listado = BodegaKardex.objects.filter().order_by('-fecha', 'producto__id').distinct('producto__id', 'fecha')


                paging = MiPaginador(listado, 25)
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
                data['listado'] = page.object_list
                data['listcount'] = len(listado)

                return render(request, "adm_bodegainventario/view.html", data)
            except Exception as ex:
                HttpResponseRedirect(f"/?info={ex.__str__()}")
