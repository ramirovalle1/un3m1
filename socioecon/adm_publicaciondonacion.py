import random
import sys
import calendar
import datetime

import openpyxl
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
import xlwt
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import Context
from django.template.loader import get_template
from django.urls import reverse
from xlwt import *
from django.shortcuts import render, redirect
from decorators import secure_module, last_access
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from .models import *
from django.db.models import Sum, Q, F, FloatField
from .forms import *
from sga.funciones import log, generar_nombre, convertir_fecha_invertida, convertir_fecha, MiPaginador
from sga.templatetags.sga_extras import encrypt
from sga.tasks import send_html_mail
from sga.models import CUENTAS_CORREOS
from sga.funciones_templatepdf import download_html_to_pdf

@login_required(redirect_field_name='ret', login_url='/loginsga')
@last_access
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    hoy = datetime.datetime.now().date()
    usuario = request.user
    data['persona'] = persona = request.session['persona']
    periodo = request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']
    data['email_domain'] = EMAIL_DOMAIN

    if persona.es_administrativo():
        if request.method == 'POST':
            data = {}
            action = data['action'] = request.POST['action']
            if action == 'addpublicacion':
                try:
                    form = PublicacionDonacionForm(request.POST)
                    file = newfile = None
                    valid_ext = ['.pdf', '.PDF', ".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG"]
                    if 'evidencianecesidad' in request.FILES:
                        file = request.FILES['evidencianecesidad']
                        if file:
                            if file.size > 4194304:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo es mayor a 4 Mb."})
                            else:
                                newfilesd = file._name
                                ext = newfilesd[newfilesd.rfind("."):]

                                if ext in valid_ext:
                                    file._name = generar_nombre("evidencianecesidad", file._name)
                                else:
                                    return JsonResponse(
                                        {"result": "bad", "mensaje": u"Error, Solo archivos con extención {}".format(
                                            ['.pdf', '.PDF', ".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG"])})

                    if 'evidenciaejecucion' in request.FILES:
                        newfile = request.FILES['evidenciaejecucion']
                        if newfile:
                            if newfile.size > 4194304:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo es mayor a 4 Mb."})
                            else:
                                newfilesd = newfile._name
                                ext = newfilesd[newfilesd.rfind("."):]

                                if ext in valid_ext:
                                    newfile._name = generar_nombre("evidenciaejecucion", newfile._name)
                                else:
                                    return JsonResponse(
                                        {"result": "bad", "mensaje": u"Error, Solo archivos con extención {}".format(['.pdf', '.PDF', ".jpg", ".JPG", ".jpeg", ".JPEG", ".png", ".PNG"])})

                    if form.is_valid():
                        publicaciondonacion = PublicacionDonacion(
                                                                persona=persona,
                                                                objetivo=form.cleaned_data['objetivo'],
                                                                poblacion_id=form.cleaned_data['poblacion'],
                                                                tipodonacion_id=form.cleaned_data['tipodonacion'],
                                                                fechainiciorecepcion=convertir_fecha(form.cleaned_data['fechainiciorecepcion']),
                                                                fechafinrecepcion=convertir_fecha(form.cleaned_data['fechafinrecepcion']),
                                                                fechainicioentrega=convertir_fecha(form.cleaned_data['fechainicioentrega']),
                                                                fechafinentrega=convertir_fecha(form.cleaned_data['fechafinentrega']),
                                                                producto_id=form.cleaned_data['producto'],
                                                                )
                        if file:
                            publicaciondonacion.evidencianecesidad = file

                        if newfile:
                            publicaciondonacion.evidenciaejecucion = newfile

                        publicaciondonacion.save(request)
                        log(u'Adiciono nuevo requisito: %s' % publicaciondonacion, request, "addpublicacion")

                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al validar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'informetotalproductos_excel':
                try:
                    fechadesde = u"%s 00:00:00" % convertir_fecha(request.POST['fd']) if request.POST['fd'].strip() else ''
                    fechahasta = u"%s 23:59:59" % convertir_fecha(request.POST['fh']) if request.POST['fh'].strip() else ''
                    model = PublicacionDonacion()
                    soli = model.filtros(request.POST, persona)
                    if not soli.exists():
                        mensaje = f"Estimad{'a' if persona.es_mujer() else 'o'} expert{'a' if persona.es_mujer() else 'o'}, no existen publicaciones en el periodo seleccionado."
                        return HttpResponseRedirect("/adm_publicaciondonacion?info=%s" % mensaje)

                    __author__ = 'Unemi'
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    title2 = easyxf( 'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    title3 = easyxf('font: name Times New Roman, color-index black, bold on , height 200; alignment: horiz centre')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Hoja1')
                    ws.write_merge(0, 0, 0, 11, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 11, f'REPORTE DEL TOTAL DE PRODUCTOS SOLICITADOS/DONADOS', title2)
                    ws.write_merge(2, 2, 0, 11, f'{persona}', title2)
                    fi = u"%s" % fechadesde if fechadesde else f'{soli.last().fecha_creacion.date()}'
                    ff = u"%s" % fechahasta if fechahasta else f'{soli.first().fecha_creacion.date()}'
                    ws.write_merge(3, 3, 0, 11, f'DESDE  { fi } HASTA { ff }', title3)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=reporte_solicitudes_donacion_' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"SOLICITUD", 6000),
                        (u"SOLICITANTE", 6000),
                        (u"DONADOR", 6000),
                        (u"PRODUCTO", 6000),
                        (u"UNIDAD DE MEDIDA", 6000),
                        (u"CANTIDAD SOLICITADA", 6000),
                        (u"CANTIDAD RECAUDADA", 6000),
                        (u"PORCENTAJE", 6000),
                    ]
                    row_num = 5
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 6
                    for r in soli:
                        for p in r.get_productos():
                            campo1 = u"%s" % r.nombre
                            campo2 = u"%s" % r.persona
                            campo3 = u"%s" % p.detallecontribuidordonacion_set.filter(status=True).first().contribuidordonacion.persona.nombre_completo_inverso() if p.detallecontribuidordonacion_set.filter(status=True) else ''
                            campo4 = u"%s" % p.producto
                            campo5 = u"%s" % p.unidadmedida
                            campo6 = u"%s" % p.cantidad
                            campo7 = u"%s" % p.get_cantidadrecaudada()
                            campo8 = u"%.2f" % p.get_porcentaje() + ' %'
                            ws.write(row_num, 0, campo1, font_style2)
                            ws.write(row_num, 1, campo2, font_style2)
                            ws.write(row_num, 2, campo3, font_style2)
                            ws.write(row_num, 3, campo4, font_style2)
                            ws.write(row_num, 4, campo5, font_style2)
                            ws.write(row_num, 5, campo6, font_style2)
                            ws.write(row_num, 6, campo7, font_style2)
                            ws.write(row_num, 7, campo8, font_style2)
                            row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    messages.error(request, str(ex))

            if action == 'informetotalpublicaciones_excel':
                try:
                    fechadesde = u"%s 00:00:00" % convertir_fecha(request.POST['fd']) if request.POST['fd'].strip() else ''
                    fechahasta = u"%s 23:59:59" % convertir_fecha(request.POST['fh']) if request.POST['fh'].strip() else ''
                    model = PublicacionDonacion()
                    soli = model.filtros(request.POST, persona)
                    if not soli.exists():
                        mensaje = f"Estimad{'a' if persona.es_mujer() else 'o'} expert{'a' if persona.es_mujer() else 'o'}, no existen publicaciones en el periodo seleccionado."
                        return HttpResponseRedirect("/adm_publicaciondonacion?info=%s" % mensaje)

                    __author__ = 'Unemi'
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    title2 = easyxf( 'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    title3 = easyxf('font: name Times New Roman, color-index black, bold on , height 200; alignment: horiz centre')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Hoja1')
                    ws.write_merge(0, 0, 0, 11, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 11, f'REPORTE DE SOLICITUDES DE DONACIÓN', title2)
                    ws.write_merge(2, 2, 0, 11, f'{persona}', title2)
                    fi = u"%s" % fechadesde if fechadesde else f'{soli.last().fecha_creacion.date()}'
                    ff = u"%s" % fechahasta if fechahasta else f'{soli.first().fecha_creacion.date()}'
                    ws.write_merge(3, 3, 0, 11, f'DESDE  { fi } HASTA { ff }', title3)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=reporte_solicitudes_donacion_' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"PERSONA", 6000),
                        (u"SOLICITUD", 6000),
                        (u"OBJETIVO", 15000),
                        (u"TIPO SOLICITUD", 6000),
                        (u"F. INICIO RECEPCION", 6000),
                        (u"F. FIN RECEPCION", 6000),
                        (u"F. INICIO ENTREGA", 6000),
                        (u"F. FIN ENTREGA", 6000),
                        (u"PRIORIDAD", 6000),
                        (u"APROBACIÓN", 6000),
                        (u"EVIDENCIA DE NECESIDAD", 6000),
                        (u"EVIDENCIA DE EJECUCIÓN", 6000),
                    ]
                    row_num = 5
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 6
                    for r in soli:
                        campo1 = u"%s" % r.persona
                        campo2 = u"%s" % r.nombre
                        campo3 = u"%s" % r.objetivo
                        campo4 = u"%s" % r.tipodonacion
                        campo5 = u"%s" % r.fechainiciorecepcion
                        campo6 = u"%s" % r.fechafinrecepcion
                        campo7 = u"%s" % r.fechainicioentrega
                        campo8 = u"%s" % r.fechafinentrega
                        campo9 = u"%s" % r.get_estadoprioridad_display()
                        campo10 = u"%s" % r.get_estado_display()
                        campo11 = u"%s" % 'SI' if r.evidencianecesidad else 'NO'
                        campo12 = u"%s" % 'SI' if r.evidenciaejecucion else 'NO'
                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, campo7, font_style2)
                        ws.write(row_num, 7, campo8, font_style2)
                        ws.write(row_num, 8, campo9, font_style2)
                        ws.write(row_num, 9, campo10, font_style2)
                        ws.write(row_num, 10, campo11, font_style2)
                        ws.write(row_num, 11, campo12, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    messages.error(request, str(ex))
                    #pass

            elif action == 'informetotalpublicaciones_pdf':
                try:
                    idpersona = (int(request.POST['idp']) if request.POST['idp'] else 0) if 'idp' in request.POST else 0
                    fechadesde = u"%s 00:00:00" % convertir_fecha(request.POST['fd']) if request.POST['fd'].strip() else ''
                    fechahasta = u"%s 23:59:59" % convertir_fecha(request.POST['fh']) if request.POST['fh'].strip() else ''
                    model = PublicacionDonacion()
                    soli = model.filtros(request.POST, persona)
                    if not soli.exists():
                        mensaje = f"Estimad{'a' if persona.es_mujer() else 'o'} expert{'a' if persona.es_mujer() else 'o'}, no existen publicaciones en el periodo seleccionado."
                        return HttpResponseRedirect("/adm_publicaciondonacion?info=%s" % mensaje)

                    return download_html_to_pdf('adm_publicaciondonacion/informe_total_publicaciones.html', {'pagesize': 'A4', 'data': {'soli':soli, 'individual':True if idpersona else False, 'desde':fechadesde, 'hasta':fechahasta}})
                except Exception as ex:
                    import sys
                    print('Error on line %s exception => %s'% (sys.exc_info()[-1].tb_lineno, ex.__str__()))
                    return HttpResponseRedirect("/adm_publicaciondonacion?info=Problemas al generar el informe. Intentelo más tarde.")

            if action == 'deletepublicacion':
                try:
                    soli = PublicacionDonacion.objects.get(pk=int(encrypt(request.POST['id'])))
                    soli.status = False
                    soli.save(request)
                    log(u'Eliminó solicitud de donación: %s' % soli, request, "del")
                    return JsonResponse({"error": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'addtipodonacion':
                try:
                    with transaction.atomic():
                        if TipoDonacion.objects.filter(nombre=request.POST['nombre'].strip().upper(), status=True).exists():
                            transaction.set_rollback(True)
                            return JsonResponse({'error': True, "message": 'Ya existe el tipo de donación.'}, safe=False)
                        form = TipoDonacionForm(request.POST)
                        if form.is_valid():
                            instance = TipoDonacion(nombre=form.cleaned_data['nombre'])
                            instance.save(request)
                            log(u'Adiciono tipo de donacion: %s' % instance, request, "add")
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                                 "message": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            if action == 'edittipodonacion':
                try:
                    with transaction.atomic():
                        filtro = TipoDonacion.objects.get(pk=int(encrypt(request.POST['id'])))
                        f = TipoDonacionForm(request.POST)
                        if f.is_valid():
                            filtro.nombre = f.cleaned_data['nombre']
                            filtro.save(request)
                            log(u'Edito tipo donacion: %s' % filtro, request, "edittipodonacion")
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            if action == 'deletetipodonacion':
                try:
                    with transaction.atomic():
                        instancia = TipoDonacion.objects.get(pk=int(request.POST['id']))
                        instancia.status = False
                        instancia.save(request)
                        log(u'Eliminó tipo donación: %s' % instancia, request, "deletetipodonacion")
                        res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            if action == 'deleteunidadmedida':
                try:
                    with transaction.atomic():
                        instancia = UnidadMedidaDonacion.objects.get(pk=int(encrypt(request.POST['id'])))
                        instancia.status = False
                        instancia.save(request)
                        log(u'Eliminó unidad de medida: %s' % instancia, request, "delete")
                        res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            if action == 'addtipoproducto':
                try:
                    with transaction.atomic():
                        if TipoProducto.objects.filter(descripcion=request.POST['descripcion'], status=True).exists():
                            transaction.set_rollback(True)
                            return JsonResponse({'error': True, "message": 'Ya existe el tipo de donación.'}, safe=False)
                        form = TipoProductoForm(request.POST)
                        if form.is_valid():
                            instance = TipoProducto(descripcion=form.cleaned_data['descripcion'])
                            instance.save(request)
                            log(u'Adiciono tipo de producto: %s' % instance, request, "addtipoproducto")
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()],"message": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            if action == 'edittipoproducto':
                try:
                    with transaction.atomic():
                        filtro = TipoProducto.objects.get(pk=int(encrypt(request.POST['id'])))
                        f = TipoProductoForm(request.POST)
                        if f.is_valid():
                            filtro.descripcion = f.cleaned_data['descripcion']
                            filtro.save(request)
                            log(u'Edito tipo producto: %s' % filtro, request, "edittipoproducto")
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            if action == 'deletetipoproducto':
                try:
                    with transaction.atomic():
                        instancia = TipoProducto.objects.get(pk=int(request.POST['id']))
                        instancia.status = False
                        instancia.save(request)
                        log(u'Eliminó tipo donación: %s' % instancia, request, "deletetipoproducto")
                        res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            if action == 'addpoblacion':
                try:
                    with transaction.atomic():
                        if PoblacionDonacion.objects.filter(nombre=request.POST['nombre'], status=True).exists():
                            transaction.set_rollback(True)
                            return JsonResponse({'error': True, "message": 'Ya existe el tipo de población.'}, safe=False)
                        form = PoblacionDonacionForm(request.POST)
                        if form.is_valid():
                            instance = PoblacionDonacion(nombre=form.cleaned_data['nombre'])
                            instance.save(request)
                            log(u'Adiciono población: %s' % instance, request, "addpoblacion")
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                                 "message": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            if action == 'addunidadmedida':
                try:
                    if UnidadMedidaDonacion.objects.filter(nombre=request.POST['nombre'].upper(), status=True).exists():
                        transaction.set_rollback(True)
                        return JsonResponse({'error': True, "message": 'Ya existe el tipo de medida.'}, safe=False)
                    form = UnidadMedidaDonacionForm(request.POST)
                    if form.is_valid():
                        instance = UnidadMedidaDonacion(nombre=form.cleaned_data['nombre'], abreviatura=form.cleaned_data['abreviatura'])
                        instance.save(request)
                        log(u'Adicionó unidad de medida: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            if action == 'editunidadmedida':
                try:
                    with transaction.atomic():
                        filtro = UnidadMedidaDonacion.objects.get(pk=int(encrypt(request.POST['id'])))
                        f = UnidadMedidaDonacionForm(request.POST)
                        if f.is_valid():
                            filtro.nombre = f.cleaned_data['nombre']
                            filtro.save(request)
                            log(u'Edito unidad de medida: %s' % filtro, request, "edit")
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            if action == 'editpoblacion':
                try:
                    with transaction.atomic():
                        filtro = PoblacionDonacion.objects.get(pk=int(encrypt(request.POST['id'])))
                        f = PoblacionDonacionForm(request.POST)
                        if f.is_valid():
                            filtro.nombre = f.cleaned_data['nombre']
                            filtro.save(request)
                            log(u'Edito tipo donacion: %s' % filtro, request, "editpoblacion")
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            if action == 'deletepoblacion':
                try:
                    with transaction.atomic():
                        instancia = PoblacionDonacion.objects.get(pk=int(encrypt(request.POST['id'])))
                        instancia.status = False
                        instancia.save(request)
                        log(u'Eliminó tipo población: %s' % instancia, request, "deletepoblacion")
                        res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            if action == 'addproducto':
                try:
                    with transaction.atomic():
                        if Producto.objects.filter(descripcion=request.POST['descripcion'].upper(), status=True).exists():
                            transaction.set_rollback(True)
                            return JsonResponse({'error': True, "message": 'Ya existe el tipo de producto.'}, safe=False)
                        form = ProductoForm(request.POST)
                        if form.is_valid():
                            instance = Producto(descripcion=form.cleaned_data['descripcion'], tipoproducto_id=request.POST['tipoproducto'])
                            instance.save(request)
                            log(u'Adiciono producto: %s' % instance, request, "addproducto")
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()],"message": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            if action == 'editproducto':
                try:
                    with transaction.atomic():
                        filtro = Producto.objects.get(pk=int(encrypt(request.POST['id'])))
                        f = ProductoForm(request.POST)
                        if f.is_valid():
                            filtro.descripcion = f.cleaned_data['descripcion']
                            filtro.tipoproducto_id = f.cleaned_data['tipoproducto']
                            filtro.save(request)
                            log(u'Edito producto: %s' % filtro, request, "editproducto")
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            if action == 'deleteproducto':
                try:
                    with transaction.atomic():
                        instancia = Producto.objects.get(pk=int(request.POST['id']))
                        instancia.status = False
                        instancia.save(request)
                        log(u'Eliminó producto: %s' % instancia, request, "deleteproducto")
                        res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            if action == 'aprobacionsolicitud':
                try:
                    with transaction.atomic():
                        form = DetalleAprobacionPublicacionDonacionForm(request.POST)
                        detalleaprobacion = DetalleAprobacionPublicacionDonacion.objects.all()
                        instance = detalleaprobacion.filter(publicaciondonacion_id=request.POST['id']).order_by('-id')[0] if detalleaprobacion.filter(publicaciondonacion_id=request.POST['id']) else ''
                        if form.is_valid():
                            if instance and instance.estado == form.cleaned_data['estado']:
                                instance.observacion = form.cleaned_data['observacion']
                                instance.persona = persona
                                instance.save(request)
                            else:
                                instance = DetalleAprobacionPublicacionDonacion(publicaciondonacion_id=request.POST['id'], observacion=form.cleaned_data['observacion'], estado=form.cleaned_data['estado'], persona=persona)
                                instance.save(request)

                                # solicitud = detalleaprobacion.filter(pk=instance.pk).annotate(ffinsolicitud=(F('publicaciondonacion__fechafinentrega') - F('publicaciondonacion__fechainiciorecepcion')), ffinentrega=(F('publicaciondonacion__fechafinentrega') - hoy))[0]
                                # data['solicitud'] = solicitud
                                # asunto = u"SOLICITUD DE DONACIÓN " + solicitud.publicaciondonacion.nombre.upper()
                                #
                                # send_html_mail(asunto, "emails/notificacionaprobaciondonacion.html",
                                #                {'sistema': request.session['nombresistema'], 'solicitud': solicitud,
                                #                 'persona': persona},
                                #                solicitud.publicaciondonacion.lista_responsables(), [], cuenta=CUENTAS_CORREOS[16][1])

                            soli = PublicacionDonacion.objects.get(pk=request.POST['id'])
                            soli.estado = form.cleaned_data['estado']
                            soli.estadoprioridad = form.cleaned_data['estadoprioridad']
                            soli.save(request)

                            log(u'Aprobó solicitud: %s' % instance, request, "add")
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                                 "message": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)


            return HttpResponseRedirect('/adm_publicaciondonacion')

        #INICIO GET
        else:
            if 'action' in request.GET:
                action = data['action'] = request.GET['action']

                # if action == 'addpublicacion':
                #     try:
                #         form = PublicacionDonacionForm()
                #         form.es_agregar()
                #         data['form'] = form
                #         template = get_template("alu_publicaciondonacion/modal/addpublicacion.html")
                #         return JsonResponse({"result": True, 'data': template.render(data)})
                #     except Exception as ex:
                #         pass

                if action == 'aprobacionsolicitud':
                    try:
                        data['id'] = id = int(encrypt(request.GET['id']))
                        if DetalleAprobacionPublicacionDonacion.objects.filter(publicaciondonacion_id=id, status=True).exists():
                            detalle = DetalleAprobacionPublicacionDonacion.objects.filter(publicaciondonacion_id=id, status=True).order_by('-id').first()
                            form = DetalleAprobacionPublicacionDonacionForm(initial={'estadoprioridad': detalle.publicaciondonacion.estadoprioridad,'observacion': detalle.observacion,'estado': detalle.estado})
                        else:
                            form = DetalleAprobacionPublicacionDonacionForm()
                        data['form2'] = form
                        template = get_template("adm_publicaciondonacion/modal/formmodal.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    except Exception as ex:
                        pass

                if action == 'configuraciones':
                    try:
                        data['title'] = u'Configuraciones'
                        data['listaproducto'] = Producto.objects.filter(status=True).order_by('-id')
                        data['listatipoproducto'] = TipoProducto.objects.filter(status=True).order_by('-id')
                        data['listapoblaciondonacion'] = PoblacionDonacion.objects.filter(status=True).order_by('-id')
                        data['listatipodonacion'] = TipoDonacion.objects.filter(status=True).order_by('-id')
                        data['listaunidadmedida'] = UnidadMedidaDonacion.objects.filter(status=True).order_by('-id')
                        return render(request, "adm_publicaciondonacion/configuraciones.html", data)
                    except Exception as ex:
                        pass

                if action == 'addtipodonacion':
                    try:
                        form = TipoDonacionForm()
                        data['form2'] = form
                        template = get_template("adm_publicaciondonacion/modal/formmodal.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    except Exception as ex:
                        pass

                if action == 'edittipodonacion':
                    try:
                        data['id'] = request.GET['id']
                        data['filtro'] = filtro = TipoDonacion.objects.get(pk=int(encrypt(request.GET['id'])))
                        form = TipoDonacionForm(initial=model_to_dict(filtro))
                        data['form2'] = form
                        template = get_template("adm_publicaciondonacion/modal/formmodal.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    except Exception as ex:
                        pass

                if action == 'addtipoproducto':
                    try:
                        form = TipoProductoForm()
                        data['form2'] = form
                        template = get_template("adm_publicaciondonacion/modal/formmodal.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    except Exception as ex:
                        pass

                if action == 'edittipoproducto':
                    try:
                        data['id'] = request.GET['id']
                        data['filtro'] = filtro = TipoProducto.objects.get(pk=int(encrypt(request.GET['id'])))
                        form = TipoProductoForm(initial=model_to_dict(filtro))
                        data['form2'] = form
                        template = get_template("adm_publicaciondonacion/modal/formmodal.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    except Exception as ex:
                        pass

                if action == 'addpoblacion':
                    try:
                        form = PoblacionDonacionForm()
                        data['form2'] = form
                        template = get_template("adm_publicaciondonacion/modal/formmodal.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    except Exception as ex:
                        pass

                if action == 'editpoblacion':
                    try:
                        data['id'] = request.GET['id']
                        data['filtro'] = filtro = PoblacionDonacion.objects.get(pk=int(encrypt(request.GET['id'])))
                        form = PoblacionDonacionForm(initial=model_to_dict(filtro))
                        data['form2'] = form
                        template = get_template("adm_publicaciondonacion/modal/formmodal.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    except Exception as ex:
                        pass

                if action == 'addproducto':
                    try:
                        form = ProductoForm()
                        data['form2'] = form
                        template = get_template("adm_publicaciondonacion/modal/formmodal.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    except Exception as ex:
                        pass

                if action == 'addunidadmedida':
                    try:
                        form = UnidadMedidaDonacionForm()
                        data['form2'] = form
                        template = get_template("adm_publicaciondonacion/modal/formmodal.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    except Exception as ex:
                        pass

                if action == 'editunidadmedida':
                    try:
                        data['id'] = request.GET['id']
                        data['filtro'] = filtro = UnidadMedidaDonacion.objects.get(pk=int(encrypt(request.GET['id'])))
                        form = UnidadMedidaDonacionForm(initial=model_to_dict(filtro))
                        data['form2'] = form
                        template = get_template("adm_publicaciondonacion/modal/formmodal.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    except Exception as ex:
                        pass

                if action == 'editproducto':
                    try:
                        data['id'] = request.GET['id']
                        data['filtro'] = filtro = Producto.objects.get(pk=int(encrypt(request.GET['id'])))
                        form = ProductoForm(initial=model_to_dict(filtro))
                        data['form2'] = form
                        template = get_template("adm_publicaciondonacion/modal/formmodal.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    except Exception as ex:
                        pass

                if action == 'addpublicacion':
                    try:
                        form = PublicacionDonacionForm()
                        form.es_agregar()
                        data['form'] = form
                        data['title'] = "Agregar publicación"
                        return render(request, "publicaciondonacion/modal/addpublicacion.html", data)
                    except Exception as ex:
                        pass

                if action == 'mostrardetalleaprobacion_view':
                    try:
                        publicaciond = PublicacionDonacion.objects.filter(pk=int(encrypt(request.GET['id']))).first()
                        detalle = DetalleAprobacionPublicacionDonacion.objects.filter(publicaciondonacion_id=publicaciond.pk, status=True).order_by('-id')
                        data['detalleaprobacion'] = detalle
                        data['publicaciondonacion'] = publicaciond
                        data['estadochoices'] = PUBLICACION_DONACION_ESTADO
                        template = get_template("adm_publicaciondonacion/modal/mostrardetalleaprobacion_view.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    except Exception as ex:
                        pass

                if action == 'detalleevidencia':
                    try:
                        pd = PublicacionDonacion.objects.get(pk=int(encrypt(request.GET['id'])))
                        data['evd'] = pd
                        template = get_template("adm_publicaciondonacion/modal/detalleevidencia.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                    except Exception as ex:
                        pass

                return HttpResponseRedirect('/adm_publicaciondonacion')
            else:
                data['title'] = u'Donaciones'
                filtro = Q(status=True)
                search, tipodonacion, estadodonacion, url_vars = request.GET.get('s', ''), request.GET.get('td', '0'), request.GET.get('ed', '0'), ''

                if search:
                    filtro = filtro & (Q(nombre__icontains=search.strip()) | Q(persona__cedula=search.strip()) | Q(persona__apellido1__icontains=search.strip()) | Q(persona__apellido2__icontains=search.strip()))
                    url_vars += '&s=' + search
                    data['search'] = search

                if int(tipodonacion):
                    filtro = filtro & (Q(tipodonacion_id=tipodonacion))
                    url_vars += '&td=' + tipodonacion
                    data['td'] = tipodonacion

                if int(estadodonacion):
                    filtro = filtro & (Q(estado=estadodonacion))
                    url_vars += '&ed=' + estadodonacion
                    data['ed'] = estadodonacion

                if 'pk' in request.GET:
                    pk = int(encrypt(request.GET['pk']))
                    filtro = filtro & (Q(pk=pk))
                    data['pk'] = pk

                listado = PublicacionDonacion.objects.filter(filtro)
                paging = MiPaginador(listado, 20)
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
                data['email_domain'] = EMAIL_DOMAIN
                data['listadonaciones'] = page.object_list
                data['url_vars'] = url_vars
                data['tipodonacion'] = TipoDonacion.objects.values_list('id', 'nombre').filter(pk__in=PublicacionDonacion.objects.values_list('tipodonacion_id', flat=True).filter(status=True), status=True).distinct()
                data['estadodonacion'] = PUBLICACION_DONACION_ESTADO
                data['estadopriridad'] = PUBLICACION_DONACION_PRIORIDAD

                return render(request, 'adm_publicaciondonacion/view.html', data)


    else:
        return HttpResponseRedirect("/?info=Usted no pertenece al grupo de administrativos.")
