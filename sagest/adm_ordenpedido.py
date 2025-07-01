# -*- coding: UTF-8 -*-

import json
from datetime import datetime, timedelta
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module
from sagest.forms import OrdenPedidoForm, DetalleOrdenPedidoForm
from sagest.models import Producto, OrdenPedido, Departamento, DetalleOrdenPedido, InventarioReal, HdIncidente, \
    OrdenTrabajo, DistributivoPersona, ESTADO_ORDEN_PEDIDO
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import log, MiPaginador, puede_realizar_accion, null_to_decimal, generar_codigo
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, add_tabla_reportlab, generar_pdf_reportlab, \
    add_titulo_reportlab, add_graficos_barras_reportlab, add_graficos_circular_reporlab
from sagest.commonviews import secuencia_ordentrabajo
from sga.models import Notificacion


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    PREFIX = 'UNEMI'
    SUFFIX = 'OP'
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'SearchProduct':
            try:
                if not 'q' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})
                q = request.POST['q']
                productos = Producto.objects.filter(Q(cuenta__cuenta__icontains=q) |
                                                    Q(codigo__icontains=q) |
                                                    Q(descripcion__icontains=q) |
                                                    Q(alias__icontains=q), status=True).distinct()[:20]
                results = []
                for producto in productos:
                    results.append({"id": producto.id,
                                    "alias": producto.flexbox_alias_orden_pedido(),
                                    "name": producto.flexbox_repr_orden_pedido()})
                return JsonResponse({"result": "ok", "results": results})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'SearchResponsible':
            try:
                departamento = Departamento.objects.get(pk=int(request.POST['id']))
                aData = []
                for integrante in departamento.integrantes.filter(administrativo__isnull=False, status=True):
                    aData.append([integrante.id, integrante.nombre_completo_inverso()])
                return JsonResponse({"result": "ok", "aData": aData})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'SaveAddOrdenPedido':
            try:
                f = OrdenPedidoForm(request.POST)
                if f.is_valid():
                    datos = json.loads(request.POST['lista_items1'])
                    if not datos:
                        return JsonResponse({"result": "bad",
                                             "mensaje": u"Error al guardar los datos, no registra detalles de productos"})

                    numerodocumento = 1
                    try:
                        numerodocumento = OrdenPedido.objects.all().order_by("-id")[0].numerodocumento
                        numerodocumento = int(numerodocumento) + 1
                    except:
                        pass
                    responsable = f.cleaned_data['responsable']
                    distributivo = DistributivoPersona.objects.filter(status=True, persona=responsable)[0]
                    ordenPedido = OrdenPedido(departamento=f.cleaned_data['departamento'],
                                              responsable=responsable,
                                              denominacionpuesto=distributivo.denominacionpuesto.descripcion,
                                              director=distributivo.unidadorganica.responsable,
                                              directordenominacionpuesto=DistributivoPersona.objects.filter(status=True,
                                                                                                            persona=distributivo.unidadorganica.responsable,
                                                                                                            unidadorganica=distributivo.unidadorganica)[0].denominacionpuesto.descripcion,
                                              numerodocumento=numerodocumento,
                                              codigodocumento=generar_codigo(numerodocumento, PREFIX, SUFFIX),
                                              fechaoperacion=datetime.now(),
                                              descripcion=f.cleaned_data['descripcion'],
                                              observaciones=f.cleaned_data['observaciones'])
                    ordenPedido.save(request)
                    for elemento in datos:
                        producto = Producto.objects.get(pk=int(elemento['id']))
                        if not producto:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"El producto %s no exite." % int(elemento['id'])})

                        cantidad = Decimal(elemento['cantidad']).quantize(Decimal('.0001'))
                        costo = Decimal(elemento['costo']).quantize(Decimal('.000000000000001'))
                        existencia = Decimal(elemento['stock']).quantize(Decimal('.0001'))
                        valor = costo * cantidad

                        detalleOrdenPedido = DetalleOrdenPedido(producto=producto,
                                                                cantidad=cantidad,
                                                                costo=costo,
                                                                valor=valor,
                                                                existencia=existencia
                                                                )
                        detalleOrdenPedido.save(request)
                        ordenPedido.productos.add(detalleOrdenPedido)
                    ordenPedido.save(request)
                    log(u'Adiciono orden de pedido: %s' % ordenPedido, request, "add")
                    url = ("%s?id=%s" % (request.path, ordenPedido.id))
                    notificacion = Notificacion(titulo='Nueva Orden de Pedido Nro. %s' % ordenPedido.codigodocumento,
                                                cuerpo='Tiene una una orden de pedido Nro. %s, con estado Solicitado' % ordenPedido.codigodocumento,
                                                destinatario=ordenPedido.director,
                                                url=url,
                                                content_type=ContentType.objects.get_for_model(ordenPedido),
                                                object_id=ordenPedido.pk,
                                                prioridad=2,
                                                fecha_hora_visible=datetime.now()+timedelta(days=30),
                                                app_label='sagest',
                                                )
                    notificacion.save(request)
                    log(u'Adiciono una notificación de orden de pedido: %s' % ordenPedido, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        if action == 'LoadDetailOrdenPedido':
            try:
                data['orden'] = orden = OrdenPedido.objects.get(pk=request.POST['id'])
                data['detalles'] = orden.productos.all()
                template = get_template("adm_ordenpedido/detalles_orden_pedido.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content, 'numero': orden.codigodocumento})
            except Exception as ex:
                return JsonResponse({"result": "bad","mensaje": u"Error al cargar los datos" + ex})

        if action == 'RunOT':
            mensaje = "Problemas al generar Orden de trabajo."
            try:
                incidente = HdIncidente.objects.get(id=request.POST['id'])
                if incidente.tipoincidente_id == 3 and incidente.ordentrabajo == None:
                    secuencia = secuencia_ordentrabajo(request, datetime.now().year)
                    secuencia.secuenciaincidente += 1
                    secuencia.save(request)
                    ordentrabajo = OrdenTrabajo(codigoorden="0000"+str(secuencia.secuenciaincidente) + str("-"+str(datetime.now().year)))
                    ordentrabajo.save()
                    incidente.ordentrabajo = ordentrabajo
                    incidente.save()
                return conviert_html_to_pdf('adm_hdincidente/ordentrabajo.html',
                                            {'pagesize': 'A4',
                                             'incidente': incidente,'hoy':datetime.now().date()
                                             })
            except Exception as ex:
                return HttpResponseRedirect("/adm_hdincidente?info=%s" % mensaje)

        if action == 'AppoveOrdenPedido':
            try:
                orden = OrdenPedido.objects.get(pk=int(request.POST['id']))
                if not orden:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos, no se encontro orden de pedido"})
                orden.estado = 2
                orden.save(request)
                log(u'Apruebo orden de pedido: %s' % orden, request, "edit")
                notificaciones = Notificacion.objects.filter(content_type=ContentType.objects.get_for_model(orden), object_id=orden.id)
                for notificacion in notificaciones:
                    if not notificacion.leido and notificacion.visible:
                        notificacion.leido = True
                        notificacion.visible = False
                        notificacion.fecha_hora_leido = datetime.now()
                        notificacion.save(request)
                        log(u'Leo el mensaje: %s' % notificacion, request, "edit")
                return JsonResponse({"result": "ok", 'mensaje': u"Se aprobo la orden de pedido %s" % orden.codigodocumento})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar orden de pedido" + ex})

        if action == 'DenyOrdenPedido':
            try:
                orden = OrdenPedido.objects.get(pk=int(request.POST['id']))
                if not orden:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos, no se encontro orden de pedido"})
                observacion = request.POST['observacion'] if 'observacion' in request.POST and request.POST['observacion'] else None
                if not observacion:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos, ingrese una observación de porque rechaza y/o anula la orden de pedido"})
                orden.estado = 3
                orden.anulado = True
                orden.observacionanulado = observacion
                orden.save(request)
                log(u'Anulo orden de pedido: %s' % orden, request, "edit")
                notificaciones = Notificacion.objects.filter(content_type=ContentType.objects.get_for_model(orden),object_id=orden.id)
                for notificacion in notificaciones:
                    if not notificacion.leido and notificacion.visible:
                        notificacion.leido = True
                        notificacion.visible = False
                        notificacion.fecha_hora_leido = datetime.now()
                        notificacion.save(request)
                        log(u'Leo el mensaje: %s' % notificacion, request, "edit")
                return JsonResponse({"result": "ok", 'mensaje': u"Se rechazo/anulo la orden de pedido %s" % orden.codigodocumento})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al rechazo/anulo orden de pedido" + ex})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'add':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_dar_salida_inventario')
                    ultimo = 1
                    try:
                        ultimo = OrdenPedido.objects.all().order_by("-id")[0].numerodocumento
                        ultimo = int(ultimo) + 1
                    except:
                        pass
                    ultimo = generar_codigo(ultimo, PREFIX, SUFFIX, 9, True)
                    form = OrdenPedidoForm(initial={'codigodocumento': ultimo,
                                                    'fechaordenpedido': datetime.now().date()})
                    form.adicionar()
                    data['form'] = form
                    form2 = DetalleOrdenPedidoForm()
                    form2.adicionar()
                    data['form2'] = form2
                    data['title'] = u'Nueva orden de pedido'
                    return render(request, "adm_ordenpedido/add.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                search = None
                ids = None
                estado_id = None
                mis_ordenes = None
                isDirector = False
                ordenes_pedidos = OrdenPedido.objects.all().order_by('-fechaoperacion')
                ordenes_pedidos_director = OrdenPedido.objects.filter(director=persona)
                if 's' in request.GET:
                    search = request.GET['s']
                    if search:
                        ordenes_pedidos = ordenes_pedidos.filter(Q(codigodocumento__icontains=search) |
                                                                 Q(departamento__nombre__icontains=search) |
                                                                 Q(numerodocumento__icontains=search) |
                                                                 Q(descripcion__icontains=search) |
                                                                 Q(observaciones__icontains=search))
                if 'id' in request.GET:
                    ids = request.GET['id']
                    if ids:
                        ordenes_pedidos = ordenes_pedidos.filter(id=ids)

                if 'eid' in request.GET:
                    if int(request.GET['eid']) > 0:
                        estado_id = ESTADO_ORDEN_PEDIDO[int(request.GET['eid'])-1][0]
                        ordenes_pedidos = ordenes_pedidos.filter(estado=estado_id)
                    else:
                        estado_id = int(request.GET['eid'])

                if 'myids' in request.GET:
                    mis_ordenes = request.GET['myids']
                    if mis_ordenes == 'my':
                        if ordenes_pedidos_director.exists():
                            ordenes_pedidos = ordenes_pedidos.filter(director=persona)
                        else:
                            ordenes_pedidos = ordenes_pedidos.filter(responsable=persona)
                    else:
                        mis_ordenes = "all"

                if ordenes_pedidos_director.exists():
                    isDirector = True

                paging = MiPaginador(ordenes_pedidos, 25)
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
                data['ids'] = ids if ids else ""
                data['reporte_0'] = obtener_reporte('comprobante_orden_pedido')
                data['ordenes'] = page.object_list
                data['estados'] = ESTADO_ORDEN_PEDIDO
                data['eid'] = estado_id if estado_id else 0
                data['myids'] = mis_ordenes if mis_ordenes else 'all'
                data['isDirector'] = isDirector
                data['title'] = u'Ordenes de Pedidos'
                return render(request, "adm_ordenpedido/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect("/")



