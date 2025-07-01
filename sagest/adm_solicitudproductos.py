# -*- coding: UTF-8 -*-
import json
import random
import sys
from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
import xlwt
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import Context
from django.template.loader import get_template
from xlwt import *
from django.shortcuts import render, redirect

from balcon.forms import SolicitudBalconEditForm
from decorators import secure_module
from sagest.forms import DepartamentoForm, IntegranteDepartamentoForm, ResponsableDepartamentoForm, \
    SeccionDepartamentoForm, SolicitudObservacionForm, ResponsableSolicitudForm
from sagest.models import Departamento, SeccionDepartamento, TipoOtroRubro, ESTADOS_SOLICITUD_PRODUCTOS, Producto, \
    InventarioReal, DistributivoPersona, SolicitudObservacionesProductos, SalidaProducto, DetalleSalidaProducto, \
    ResponsablesSolicitudDepartamentos, PersonaDepartamentoFirmas, ActivoFijo
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.tasks import send_html_mail
from .commonviews import secuencia_bodega
from .forms import SolicitudProductoForm
from sga.funciones import MiPaginador, log, generar_nombre, puede_realizar_accion, null_to_decimal, \
    puede_realizar_accion_afirmativo, generar_codigo, notificacion
from sga.models import Administrativo, Persona, CUENTAS_CORREOS
from .models import SolicitudProductos, SolicitudDetalleProductos
from django.db.models import Value, Count, Sum, F, FloatField
from django.db.models.functions import Coalesce

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    PREFIX = 'UNEMI'
    SUFFIX = 'OP'
    adduserdata(request, data)
    persona = request.session['persona']
    departamentopersona = Departamento.objects.filter(Q(responsable=persona) | Q(responsable_subrogante=persona), integrantes__isnull=False).first()
    if not departamentopersona:
        departamentopersona = persona.departamento_set.all().first() if persona.departamento_set.all().exists() else None
    departamentogestion = Departamento.objects.filter(permisodepartamento=1, status=True).first()
    responsable_bodega, responsable_subroganteb,responsable_subrogante, permitidoingreso, puede_administrar, puede_aprobar  =  None, None,None, False, False, False
    if departamentogestion:
        responsable_subroganteb = PersonaDepartamentoFirmas.objects.filter(status=True, denominacionpuesto_id=565,departamento=departamentogestion,activo=True).first()
        responsable_bodega = departamentogestion.responsable
        if responsable_subroganteb:
            responsable_subrogante = responsable_subroganteb.personadepartamento
        else:
            responsable_subrogante = departamentogestion.responsable_subrogante.all().first() if departamentogestion.responsable_subrogante.all().exists() else departamentogestion.responsable
        puede_administrar = puede_administrar_solicitudes(departamentogestion, persona)
        permitidoingreso = puede_administrar
        if departamentogestion.responsable == persona:
            puede_aprobar = True

    add_solicitudes = puede_solicitar(request, departamentopersona, persona, responsable_subrogante)
    data['add_solicitudes'] = add_solicitudes
    if not puede_administrar:
        permitidoingreso = add_solicitudes
    if not permitidoingreso:
        messages.warning(request, 'SOLO LOS DIRECTORES PUEDEN ACCEDER A ESTE MÓDULO')
        return redirect('/')
    data['puede_administrar'] = puede_administrar
    data['puede_aprobar'] = puede_aprobar
    data['title'] = u'Solicitud de Productos'
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = SolicitudProductoForm(request.POST)
                if f.is_valid():
                    datos = json.loads(request.POST['lista_items1'])
                    if len(datos) > 0:
                        numsolicitud = SolicitudProductos.objects.filter(departamento=departamentopersona, fechaoperacion__year=datetime.now().year).count() + 1
                        responsable = persona
                        distributivo = DistributivoPersona.objects.filter(status=True, persona=responsable).first()
                        denominacionpuesto_persona = ''
                        unidadorganica_persona = ''
                        if distributivo:
                            denominacionpuesto_persona = distributivo.denominacionpuesto.descripcion if distributivo.denominacionpuesto else ''
                            unidadorganica_persona = distributivo.unidadorganica.responsable if distributivo.unidadorganica else ''
                        denominaciondirector = DistributivoPersona.objects.filter(status=True, persona=distributivo.unidadorganica.responsable, unidadorganica=distributivo.unidadorganica).first()
                        denominacionpuesto_director = ''
                        if denominaciondirector:
                            denominacionpuesto_director = denominaciondirector.denominacionpuesto.descripcion if denominaciondirector.denominacionpuesto else ''
                        solicitudprod = SolicitudProductos(departamento=departamentopersona,
                                                           numerodocumento=numsolicitud,
                                                           codigodocumento=generar_codigo(numsolicitud, PREFIX, SUFFIX),
                                                           fechaoperacion=datetime.now().date(),
                                                           responsable=persona,
                                                           denominacionpuesto=denominacionpuesto_persona,
                                                           director=unidadorganica_persona,
                                                           directordenominacionpuesto=denominacionpuesto_director,
                                                           descripcion=f.cleaned_data['descripcion'],
                                                           observaciones=f.cleaned_data['observaciones'])
                        solicitudprod.save(request)
                        for elemento in datos:
                            producto = Producto.objects.get(pk=elemento['id'])
                            detallesalprod = SolicitudDetalleProductos(solicitud=solicitudprod,
                                                                       producto=producto,
                                                                       cantidad=Decimal(elemento['cantidad']).quantize(
                                                                           Decimal('.0001')))
                            detallesalprod.save(request)

                        url = ("%s?id=%s" % (request.path, solicitudprod.id))
                        titulo = 'Nueva Solicitud de Pedido Nro. %s' % solicitudprod.codigodocumento
                        if departamentogestion:
                            asunto = '💡 [NOTIFICACIÓN] Nueva solicitud de productos pendiente de aprobación.'
                            template = 'emails/ingreso_solicitud.html'
                            datos_email = {'sistema': 'SAGEST UNEMI', 'solicitud': solicitudprod, 'responsable': responsable_bodega}
                            lista_email = [responsable_bodega.emailinst,]
                            # lista_email = ['hllerenaa@unemi.edu.ec',]
                            send_html_mail(asunto, template, datos_email, lista_email, [], [], cuenta=CUENTAS_CORREOS[4][1])
                            notificacion(titulo, 'Nueva solicitud de productos', responsable_bodega, None, url, solicitudprod.pk, 1, 'sagest', SolicitudProductos, request)
                        log(u'Adiciono nueva solicitud de productos: %s' % solicitudprod, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe agregar productos a la solicitud."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": 'Error al guardar los datos, {}'.format(ex)})

        elif action == 'delsolicitud':
            try:
                solicitud = SolicitudProductos.objects.get(pk=request.POST['id'])
                log(u'Eliminó solicitud de productos: %s' % (solicitud), request, "del")
                solicitud.status = False
                solicitud.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos. Detalle: %s" % (msg)})

        elif action == 'editcantidad':
            try:
                with transaction.atomic():
                    data = json.loads(request.POST['data'])
                    valoractual = Decimal(request.POST['value']).quantize(Decimal('.0001'))
                    valoranterior = SolicitudDetalleProductos.objects.get(pk=int(data["pk"]))
                    bandera = True
                    if valoractual > valoranterior.cantidad:
                        bandera = False
                        return JsonResponse({'error': True, "message": 'EL valor a entregar es mayor al valor solicitado'}, safe=False)
                    if valoractual > valoranterior.producto.stock_inventario():
                        bandera = False
                        return JsonResponse({'error': True, "message": 'EL valor a entregar es mayor al valor en existencia'}, safe=False)
                    if valoranterior.cantentregar == valoractual:
                        bandera = False
                        return JsonResponse({'error': True, "message": 'EL valor es el mismo, cambio no aplicado'}, safe=False)
                    if bandera:
                        valnuevo = SolicitudDetalleProductos.objects.get(pk=int(data["pk"]))
                        valnuevo.cantentregar = valoractual
                        valnuevo.save(request)
                        log(u'Edito cantidad a entregar: %s' % valnuevo, request, "edit")
                        res_json = {"error": False, }
            except Exception as ex:
                res_json = {'error': True, "message": str(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'editobservacion':
            try:
                with transaction.atomic():
                    id = request.POST['id']
                    obs = request.POST['value']
                    filtro = SolicitudDetalleProductos.objects.get(pk=int(id))
                    filtro.observacion = obs.upper()
                    filtro.save(request)
                    log(u'Edito cantidad a entregar: %s' % filtro, request, "edit")
                    res_json = {"error": False,}
            except Exception as ex:
                res_json = {'error': True, "message": str(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'buscarresponsable':
            try:
                departamento = Departamento.objects.get(pk=int(request.POST['id']))
                lista = []
                for integrante in departamento.integrantes.filter(administrativo__isnull=False):
                    lista.append([integrante.id, integrante.nombre_completo_inverso()])
                return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        elif action == 'addobservacion':
            try:
                with transaction.atomic():
                    filtro = SolicitudProductos.objects.get(pk=int(request.POST['id']))
                    form = SolicitudObservacionForm(request.POST)
                    if form.is_valid():
                        filtro.estados = form.cleaned_data['estados']
                        filtro.save(request)
                        soli = SolicitudObservacionesProductos(solicitud=filtro,
                                                                    observacion=form.cleaned_data['descripcion'].upper(),
                                                                    estados=form.cleaned_data['estados'])
                        soli.save(request)
                        titulo = 'Solicitud Nro.{} ({})'.format(filtro.codigodocumento, soli.dict_estados())
                        url = ("%s?id=%s" % (request.path, filtro.id))
                        if departamentogestion:
                            para = filtro.responsable
                            notificacion(titulo, soli.observacion, para, None, url, filtro.pk, 1, 'sagest', SolicitudProductos, request)
                        log(u'Adiciono Observación en solicitud: %s' % soli, request, "add")
                        # return JsonResponse({"result": False,'to':'/nuevaurl'}, safe=False) SI DESEAS REDIRECCIONAR ADICIONARLE TO A LA RESPUESTA
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'addaprobar':
            try:
                with transaction.atomic():
                    filtro = SolicitudProductos.objects.get(pk=int(request.POST['id']))
                    form = SolicitudObservacionForm(request.POST)
                    if form.is_valid():
                        filtro.estados = form.cleaned_data['estados']
                        filtro.save(request)
                        soli = SolicitudObservacionesProductos(solicitud=filtro,
                                                                    observacion=form.cleaned_data['descripcion'].upper(),
                                                                    estados=form.cleaned_data['estados'])
                        soli.save(request)
                        titulo = 'Solicitud Nro.{} ({})'.format(filtro.codigodocumento, soli.dict_estados())
                        url = ("%s?id=%s" % (request.path, filtro.id))
                        if departamentogestion:
                            if soli.estados == '1':
                                asunto = '💡 [NOTIFICACIÓN] Nueva solicitud de productos aprobada.'
                                template = 'emails/aprobacion_solicitud.html'
                                datos_email = {'sistema': 'SAGEST UNEMI', 'solicitud': soli,
                                               'responsable': responsable_subrogante}
                                lista_email = [responsable_subrogante.emailinst,]
                                # lista_email = ['hllerenaa@unemi.edu.ec', ]
                                send_html_mail(asunto, template, datos_email, lista_email, [], [],
                                               cuenta=CUENTAS_CORREOS[4][1])
                                notificacion(titulo, soli.observacion, responsable_subrogante, None, url, filtro.pk, 1, 'sagest',
                                             SolicitudProductos, request)
                            para = filtro.responsable
                            notificacion(titulo, soli.observacion, para, None, url, filtro.pk, 1, 'sagest', SolicitudProductos, request)
                        log(u'Adiciono Observación en solicitud: %s' % soli, request, "add")
                        # return JsonResponse({"result": False,'to':'/nuevaurl'}, safe=False) SI DESEAS REDIRECCIONAR ADICIONARLE TO A LA RESPUESTA
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'entregar':
            try:
                with transaction.atomic():
                    filtro = SolicitudProductos.objects.get(pk=int(request.POST['id']))
                    for elemento in filtro.solicituddetalleproductos_set.all():
                        producto = Producto.objects.get(pk=int(elemento.producto.pk))
                        if null_to_decimal(producto.stock_inventario(),2) < null_to_decimal(float(elemento.cantentregar)):
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": u"El producto %s no tiene la existencia ingresada." % producto.codigo}, safe=False)
                    bandera = False
                    for elemento in filtro.solicituddetalleproductos_set.all():
                        if Decimal(elemento.cantentregar).quantize(Decimal('.0001')) > 0:
                            bandera = True
                    if bandera:
                        filtro.estados = 3
                        filtro.fechaentrega = datetime.now()
                        filtro.save(request)

                        soli = SolicitudObservacionesProductos(solicitud=filtro,
                                                               observacion=request.POST['detentrega'].upper(),
                                                               estados=3)
                        soli.save(request)

                        salidaprod = SalidaProducto(departamento=filtro.departamento,
                                                    responsable=filtro.responsable,
                                                    solicitud=filtro,
                                                    fechaoperacion=datetime.now(),
                                                    descripcion=filtro.descripcion,
                                                    observaciones=request.POST['detentrega'].upper())
                        salidaprod.save(request)
                        secuencia = secuencia_bodega(request)
                        secuencia.salida += 1
                        secuencia.save(request)
                        salidaprod.numerodocumento = secuencia.salida
                        salidaprod.save(request)
                        for elemento in filtro.solicituddetalleproductos_set.all():
                            if Decimal(elemento.cantentregar).quantize(Decimal('.0001')) > 0:
                                elemento.entregado = True
                                elemento.save(request)
                                producto = Producto.objects.get(pk=int(elemento.producto.pk))
                                detallesalprod = DetalleSalidaProducto(producto=producto,
                                                                       cantidad=Decimal(elemento.cantentregar).quantize(Decimal('.0001')))
                                detallesalprod.save(request)
                                salidaprod.productos.add(detallesalprod)
                                # ACTUALIZAR INVENTARIO REAL
                                producto.actualizar_inventario_salida(detallesalprod, request)
                        salidaprod.save(request)
                        log(u'Entregó los productos de la solicitud: %s' % filtro, request, "add")
                        log(u'Adiciono nueva salida de inventario: %s' % salidaprod, request, "add")

                        titulo = 'Solicitud Nro.{} fue entregada'.format(filtro.codigodocumento)
                        url = ("%s?id=%s" % (request.path, filtro.id))
                        if departamentogestion:
                            para = filtro.responsable
                            notificacion(titulo, soli.observacion, para, None, url, filtro.pk, 1, 'sagest', SolicitudProductos, request)
                        messages.success(request, 'Solicitud fue entregada')
                        return JsonResponse({"result": False,'to':'/adm_solicitudproductos'}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True,
                                             "mensaje": u"Debe asignar cantidad a entregar almenos un producto"}, safe=False)
                    # return JsonResponse({"result": False}, safe=False)
                    # transaction.set_rollback(True)
                    # return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'addpersonalmodal':
            try:
                with transaction.atomic():
                    if ResponsablesSolicitudDepartamentos.objects.filter(responsable_id=int(request.POST['responsable']), status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Está persona ya se encuentra registrado como responsable."}, safe=False)
                    f = ResponsableSolicitudForm(request.POST)
                    if f.is_valid():
                        personalb = ResponsablesSolicitudDepartamentos(responsable=f.cleaned_data['responsable'], departamento=f.cleaned_data['departamento'],
                                                     estado=f.cleaned_data['estado'])
                        personalb.save(request)
                        log(u'Adiciono Responsable a Solicitud Productos: %s' % personalb, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editpersonalmodal':
            try:
                with transaction.atomic():
                    filtro = ResponsablesSolicitudDepartamentos.objects.get(pk=request.POST['id'])
                    f = ResponsableSolicitudForm(request.POST)
                    if f.is_valid():
                        filtro.estado = f.cleaned_data['estado']
                        filtro.save(request)
                        log(u'Modificó Responsable Solicitud Producto: %s' % filtro, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'delpersona':
            try:
                serviciob = ResponsablesSolicitudDepartamentos.objects.get(pk=request.POST['id'])
                serviciob.status = False
                serviciob.save(request)
                log(u'Elimino Responsable Solicitud Producto: %s' % serviciob, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'deleteresponsable':
            try:
                with transaction.atomic():
                    id = request.POST['id']
                    filtro = ResponsablesSolicitudDepartamentos.objects.get(pk=id)
                    filtro.status = False
                    filtro.save(request)
                    log(u'Elimino Responsable Solicitud Producto: %s' % filtro, request, "del")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": str(ex)}
            return JsonResponse(res_json, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'add':
                try:
                    numsolicitud = SolicitudProductos.objects.filter(departamento=departamentopersona, fechaoperacion__year=datetime.now().year).count() + 1
                    ultimo = generar_codigo(numsolicitud, PREFIX, SUFFIX, 9, True)
                    form = SolicitudProductoForm(initial={'codigodocumento': ultimo,
                                                          'fechaordenpedido': datetime.now().date()})
                    form.adicionar()
                    # if not puede_administrar:
                    midepartamento = Departamento.objects.filter(pk=departamentopersona.pk)
                    integrantes = Persona.objects.filter(pk=persona.pk)
                    form.fields['departamento'].queryset = midepartamento
                    form.fields['departamento'].initial = midepartamento.first().pk
                    form.fields['responsable'].queryset = integrantes
                    form.fields['responsable'].initial = persona.pk
                    data['form'] = form
                    return render(request, "adm_solicitudproductos/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'delsolicitud':
                try:
                    data['title'] = u'Eliminar Solicitud'
                    data['solicitud'] = solicitud = SolicitudProductos.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_solicitudproductos/deletesolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'buscarproductos':
                try:
                    q = request.GET['q'].upper().strip()
                    qset = Producto.objects.filter(status=True).filter(
                        Q(codigo__icontains=q) | Q(descripcion__icontains=q)).order_by('codigo').distinct()[:15]
                    data = {"result": "ok",
                            "results": [{"id": x.id, "name": "{}.{} {} [Stock: {}]".format(x.cuenta.cuenta, x.codigo, x.descripcion, x.stock_inventario())} for x in qset]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'consultarproducto':
                try:
                    id = request.GET['id']
                    filtro = Producto.objects.get(pk=id)
                    dict_filtro = model_to_dict(filtro)
                    codigo = "{}.{}".format(filtro.cuenta.cuenta, filtro.codigo)
                    cuentacontable = "{}".format(filtro.cuenta.cuenta)
                    unidadmedida = "{}".format(filtro.unidadmedida.nombre)
                    inv = InventarioReal.objects.filter(status=True, producto=filtro)
                    stock = 0
                    if inv.exists():
                        stock = inv.first().cantidad
                    response = JsonResponse(
                        {'state': True, 'modelo': dict_filtro, 'stock': stock, 'unidadmedida': unidadmedida,
                         'codigo': codigo, 'cuentacontable': cuentacontable})
                except Exception as ex:
                    response = JsonResponse({'state': False})
                return HttpResponse(response.content)

            elif action == 'entregar':
                try:
                    data['title'] = 'Entregar'
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = SolicitudProductos.objects.get(pk=request.GET['id'])
                    data['detalle'] = detalle = SolicitudDetalleProductos.objects.filter(solicitud=filtro).order_by('pk')
                    return render(request, 'adm_solicitudproductos/entregar.html', data)
                except Exception as ex:
                    pass

            elif action == 'versolicitud':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = SolicitudProductos.objects.get(pk=request.GET['id'])
                    data['detalle'] = detalle = filtro.solicituddetalleproductos_set.all().order_by('pk')
                    template = get_template("adm_solicitudproductos/modal/detalleproceso.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'verobservaciones':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = SolicitudProductos.objects.get(pk=request.GET['id'])
                    data['detalle'] = detalle = filtro.solicitudobservacionesproductos_set.all().order_by('pk')
                    template = get_template("adm_solicitudproductos/modal/detalleobs.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addobservacion':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = SolicitudProductos.objects.get(pk=request.GET['id'])
                    data['detalle'] = detalle = filtro.solicituddetalleproductos_set.all().order_by('pk')
                    data['detalle_obs'] = detalle_obs = filtro.solicitudobservacionesproductos_set.all().order_by('pk')
                    form = SolicitudObservacionForm()
                    ESTADOS_SOLICITUD_PRODUCTOS_OBSERVACION = (
                        (2, u'EN REVISIÓN'),
                        (4, u'RECHAZADO'),
                    )
                    form.fields['estados'].choices = ESTADOS_SOLICITUD_PRODUCTOS_OBSERVACION
                    data['form2'] = form
                    template = get_template("adm_solicitudproductos/modal/formobservacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addaprobar':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = SolicitudProductos.objects.get(pk=request.GET['id'])
                    data['detalle'] = detalle = filtro.solicituddetalleproductos_set.all().order_by('pk')
                    form = SolicitudObservacionForm()
                    ESTADOS_SOLICITUD_PRODUCTOS_OBSERVACION = (
                        (1, u'APROBADO'),
                        (4, u'RECHAZADO'),
                    )
                    form.fields['estados'].choices = ESTADOS_SOLICITUD_PRODUCTOS_OBSERVACION
                    data['form2'] = form
                    template = get_template("adm_solicitudproductos/modal/formobservacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'configuraciones':
                try:
                    data['title'] = u'Configuraciones'
                    data['responsables'] = ResponsablesSolicitudDepartamentos.objects.filter(status=True).order_by('responsable__apellido1')
                    return render(request, "adm_solicitudproductos/configuraciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'addpersonalmodal':
                try:
                    form = ResponsableSolicitudForm()
                    form.fields['responsable'].queryset = Persona.objects.none()
                    data['form2'] = form
                    template = get_template("adm_solicitudproductos/modal/formagente.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editpersonalmodal':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ResponsablesSolicitudDepartamentos.objects.get(pk=request.GET['id'])
                    form = ResponsableSolicitudForm(initial=model_to_dict(filtro))
                    form.fields['departamento'].queryset = Departamento.objects.filter(pk=filtro.departamento.pk)
                    form.fields['responsable'].queryset = Persona.objects.filter(pk=filtro.responsable.pk)
                    data['form2'] = form
                    template = get_template("adm_solicitudproductos/modal/formagente.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'delpersona':
                try:
                    data['title'] = u'ELIMINAR RESPONSABLE'
                    data['servicio'] = ResponsablesSolicitudDepartamentos.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_solicitudproductos/delpersona.html', data)
                except Exception as ex:
                    pass

            elif action == 'buscarpersona2':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    qspersona = Persona.objects.filter(status=True)
                    if len(s) == 1:
                        per = qspersona.filter((Q(distributivopersona__isnull=False) | Q(profesor__isnull=False)),
                                                     (Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(cedula__icontains=q) | Q(
                                                         apellido2__icontains=q) | Q(cedula__contains=q)),
                                                     Q(status=True)).distinct()[:15]
                    elif len(s) == 2:
                        per = qspersona.filter((Q(distributivopersona__isnull=False) | Q(profesor__isnull=False)),
                                                     (Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) | (
                                                             Q(nombres__icontains=s[0]) & Q(
                                                         nombres__icontains=s[1])) | (
                                                             Q(nombres__icontains=s[0]) & Q(
                                                         apellido1__contains=s[1]))).filter(status=True).distinct()[
                              :15]
                    else:
                        per = qspersona.filter((Q(distributivopersona__isnull=False) | Q(profesor__isnull=False)),
                                                     (Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(
                                                         apellido2__contains=s[2])) | (Q(nombres__contains=s[0]) & Q(
                                                         nombres__contains=s[1]) & Q(apellido1__contains=s[2]))).filter(
                            status=True).distinct()[:15]

                    data = {"result": "ok",
                            "results": [{"id": x.id, "name": "{} - {}".format(x.cedula, x.nombre_completo())}
                                        for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'historialentregas':
                try:
                    data['title'] = 'Historial de Pedidos'
                    idsdep = SolicitudProductos.objects.filter(status=True).values_list('departamento__id', flat=True)
                    data['departamentos'] = dep = Departamento.objects.filter(status=True, id__in=idsdep).order_by('nombre')
                    options, departamento, desde, hasta, id, search, filtros, url_vars = request.GET.get('options', ''), request.GET.get('departamento', ''), request.GET.get('desde', ''),  request.GET.get('hasta', ''),  request.GET.get('id', ''),  request.GET.get('search', ''), Q(status=True), ''
                    if desde:
                        data['desde'] = desde
                        filtros = filtros & Q(fecha_creacion__gte=desde)
                        url_vars += "&desde={}".format(desde)
                    if hasta:
                        data['hasta'] = hasta
                        filtros = filtros & Q(fecha_creacion__lte=hasta)
                        url_vars += "&hasta={}".format(hasta)
                    if departamento:
                        data['departamento'] = int(departamento)
                        filtros = filtros & (Q(departamento_id=departamento))
                        url_vars += '&departamento={}'.format(departamento)
                    url_vars += '&action={}'.format(action)
                    data["url_vars"] = url_vars
                    qsfiltro = SolicitudProductos.objects.filter(filtros)
                    ids_solicitudes = qsfiltro.values_list('id', flat=True)
                    querydetalle = SolicitudDetalleProductos.objects.filter(status=True, solicitud__in=ids_solicitudes)
                    if options:
                        data['options'] = int(options)
                        if options == '1':
                            querydetalle = querydetalle.filter(entregado=True)
                        if options == '2':
                            querydetalle = querydetalle.filter(entregado=False)
                        url_vars += "&options={}".format(options)
                    # querydetalle_entregados = SolicitudDetalleProductos.objects.filter(status=True, solicitud__in=ids_solicitudes, entregado=True)
                    listado = querydetalle.values_list('producto', flat=True).annotate(totcont=Count('producto'), cant=Sum('cantidad'), cant_entregada=Sum('cantentregar')).values('producto__codigo', 'producto__descripcion', 'producto__cuenta__cuenta', 'totcont', 'cant_entregada', 'cant').order_by('-totcont')
                    # listado_entregados = querydetalle_entregados.values_list('producto', flat=True).annotate(totcont=Count('producto'), cant=Sum('cantidad'), cant_entregada=Sum('cantentregar')).values('producto__codigo',
                    #                                                                                                                            'producto__descripcion',
                    #                                                                                                                            'producto__cuenta__cuenta', 'totcont', 'cant_entregada', 'cant').order_by('-totcont')
                    if 'report_pdf' in request.GET:
                        template_pdf = 'adm_solicitudproductos/report_pdf.html'
                        response = conviert_html_to_pdf(template_pdf, {
                                'pagesize': 'A4',
                                'listado': listado,
                                'departamento': Departamento.objects.get(id=departamento).nombre if departamento else 'TODOS LOS DEPARTAMENTOS',
                                'desde': desde,
                                'hasta': hasta,
                            })
                        return response
                    data['totalcount'] = qsfiltro.count()
                    data['totalpendientes'] = qsfiltro.filter(estados=0).count()
                    data['totalaprobados'] = qsfiltro.filter(estados=1).count()
                    data['totalenrevision'] = qsfiltro.filter(estados=2).count()
                    data['totalfinalizadas'] = qsfiltro.filter(estados=3).count()
                    data['totalanuladas'] = qsfiltro.filter(estados=4).count()
                    data['listado'] = listado
                    return render(request, 'adm_solicitudproductos/historial.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Solicitud Productos'
            url_vars = ''
            filtro = Q(status=True)
            search = None
            ids = None
            tipo = request.GET.get('tipo', '')
            id = request.GET.get('id', '')
            departamento = request.GET.get('departamento', '')

            if 's' in request.GET:
                if request.GET['s'] != '':
                    search = request.GET['s']

            if id:
                filtro = filtro & (Q(pk=int(id)))
                url_vars += '&id=' + str(id)

            if search:
                filtro = filtro & (Q(codigo__icontains=search)) | Q(responsable__cedula__icontains=search) | Q(
                    responsable__apellido1__icontains=search) | Q(departamento__nombre__icontains=search)
                url_vars += '&s=' + search

            if tipo:
                data['tipo'] = int(tipo)
                filtro = filtro & (Q(estados=int(tipo)))
                url_vars += '&tipo=' + tipo

            if departamento:
                data['departamento'] = int(departamento)
                filtro = filtro & (Q(departamento_id=int(departamento)))
                url_vars += '&departamento=' + departamento

            if not puede_administrar:
                if departamentopersona:
                    procesos = SolicitudProductos.objects.filter(filtro).filter(
                        departamento=departamentopersona).order_by('-fecha_creacion')
                else:
                    messages.error(request, 'Usted no pertenece a ningun departamento')
                    return redirect('/')
            else:
                procesos = SolicitudProductos.objects.filter(filtro).order_by('-fecha_creacion')
            data['totalcount'] = procesos.count()
            data['totalpendientes'] = procesos.filter(estados=0).count()
            data['totalaprobados'] = procesos.filter(estados=1).count()
            data['totalenrevision'] = procesos.filter(estados=2).count()
            data['totalfinalizadas'] = procesos.filter(estados=3).count()
            data['totalanuladas'] = procesos.filter(estados=4).count()

            paging = MiPaginador(procesos, 25)
            p = 1
            try:
                paginasesion = 1
                if 'paginador' in request.session:
                    paginasesion = int(request.session['paginador'])
                if 'page' in request.GET:
                    p = int(request.GET['page'])
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
            data["url_vars"] = url_vars
            data['ids'] = ids if ids else ""
            data['listado'] = page.object_list
            data['email_domain'] = EMAIL_DOMAIN
            data['estados_solicitud'] = ESTADOS_SOLICITUD_PRODUCTOS
            if puede_administrar:
                data['departamentos'] = Departamento.objects.filter(integrantes__isnull=False, status=True).distinct()
            return render(request, 'adm_solicitudproductos/view.html', data)


def puede_solicitar(request, departamentopersona, persona, responsable_subrogante):
    existe_resp, responsable, idscustodios = None, None, ids_custodios_af()
    if departamentopersona:
        existe_resp = departamentopersona.responsable_subrogante.filter(pk=persona.pk).exists()
        responsable = departamentopersona.responsable
    return request.user.is_superuser or persona.id in idscustodios or existe_resp or responsable_subrogante == persona or responsable == persona

def puede_administrar_solicitudes(departamentogestion, persona):
    tiene_integrantes = departamentogestion.mis_integrantes().filter(id=persona.pk).exists()
    # idscustodios = ids_custodios_af()
    # return persona.id in idscustodios or tiene_integrantes
    return tiene_integrantes

def ids_custodios_af():
    return ActivoFijo.objects.filter(status=True).values_list('custodio_id', flat=True).order_by('custodio_id').distinct()