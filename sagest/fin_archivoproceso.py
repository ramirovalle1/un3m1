# -*- coding: UTF-8 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum, Max
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sagest.forms import ArchivoProcesoForm, PaginaArchivoForm, TipoPagoArchivoForm, ProveedorForm, NumeroForm
from sagest.models import ArchivoProceso, PaginaArchivo, TipoPagoArchivo, SubTipoPagoArchivo, Proveedor, \
    ProveedorArchivo, PerchaArchivo, FilaArchivo, TIPO_TRAMITE
from settings import SITE_STORAGE
from sga.commonviews import adduserdata
from django.template.loader import get_template
from sga.funciones import MiPaginador, log, generar_nombre, convertir_fecha, puede_realizar_accion, null_to_decimal, \
    null_to_numeric, convertir_fecha_hora
from PyPDF2 import PdfFileReader, PdfFileWriter
import xlrd
import random
import xlwt
from xlwt import *
from django.forms import model_to_dict
from sga.funcionesxhtml2pdf import conviert_html_to_pdf

from sga.models import Externo


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'add':
            try:
                f = ArchivoProcesoForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['externo']>0 and f.cleaned_data['tipo']==1:
                        externo =  Externo.objects.get(id=f.cleaned_data['externo'])
                    else:
                        externo=None
                    documentos = ArchivoProceso(codigo=f.cleaned_data['codigo'],
                                                descripcion=f.cleaned_data['descripcion'],
                                                tipopago=f.cleaned_data['tipopago'],
                                                subtipopago=f.cleaned_data['subtipopago'],
                                                ubicacion_id=1,
                                                nombrepercha=f.cleaned_data['nombrepercha'],
                                                nopercha=f.cleaned_data['nopercha'],
                                                externo=externo,
                                                nofila=f.cleaned_data['nofila'],
                                                proveedor=f.cleaned_data['proveedor'],
                                                tipo=f.cleaned_data['tipo'],
                                                egring=f.cleaned_data['egring'],
                                                fechadocumento=f.cleaned_data['fechadocumento'],
                                                observacion=f.cleaned_data['observacion'],
                                                )
                    documentos.save(request)
                    log(u'Adiciono Archivo proceso: %s' % documentos, request, "add")
                    return JsonResponse({"result": "ok",})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'archivos':
            try:
                f = PaginaArchivoForm(request.POST, request.FILES)
                if f.is_valid():
                    nombrearchivo=None
                    archivoproceso = ArchivoProceso.objects.get(pk=int(request.POST['id']))
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile:
                            nombrearchivo = newfile._name[:newfile._name.rfind(".")]
                            newfile._name = generar_nombre("Archivo", newfile._name)
                    orden = null_to_numeric(PaginaArchivo.objects.filter(status=True,archivoproceso=archivoproceso).aggregate(secu=Max("orden"))['secu'])
                    if orden :
                        orden =orden +1
                    else:
                        orden = 1
                    paginaarchivo = PaginaArchivo(archivoproceso=archivoproceso,
                                                  fechadocumento=datetime.now(),
                                                  observacion=nombrearchivo,
                                                  archivo=newfile,
                                                  orden=orden)
                    paginaarchivo.save(request)
                    log(u'Adiciono archivo en pagina: %s [%s]' % (paginaarchivo,paginaarchivo.id), request, "add")
                    return JsonResponse({"result": "ok", })
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'cerrar_proceso':
            try:
                archivoproceso = ArchivoProceso.objects.get(pk=int(request.POST['id']))
                output = PdfFileWriter()
                for d in archivoproceso.paginaarchivo_set.filter(status=True).order_by('orden'):
                    if d.archivo:
                        append_pdf(PdfFileReader(open(SITE_STORAGE + d.archivo.url, "rb"), strict=False), output)
                newfile  = generar_nombre("Final_", "UnionFinalPDF.pdf")
                output.write(open(SITE_STORAGE+ '/media/digitales/' + newfile, "wb"))
                archivoproceso.archivo = "digitales/" + newfile
                archivoproceso.save(request)
                log(u'Cerro proceso en archivo: %s - %s [%s]' % (archivoproceso, archivoproceso.archivo, archivoproceso.id), request, "edit")
                return JsonResponse({"result": "ok", })
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex})

        elif action == 'abrir_proceso':
            try:
                archivoproceso = ArchivoProceso.objects.get(pk=int(request.POST['id']))
                archivoproceso.archivo = None
                archivoproceso.save(request)
                log(u'Abrir proceso en archivo: %s [%s]' % (archivoproceso, archivoproceso.id), request, "edit")
                return JsonResponse({"result": "ok", })
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'edit':
            try:
                f = ArchivoProcesoForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['tipo'] == 1 and f.cleaned_data['externo'] == 0:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar depositante"})
                    documentos = ArchivoProceso.objects.get(pk=int(request.POST['id']))
                    documentos.codigo = f.cleaned_data['codigo'] if f.cleaned_data['codigo'] else documentos.codigo
                    documentos.descripcion = f.cleaned_data['descripcion'] if f.cleaned_data['descripcion'] else documentos.descripcion
                    documentos.tipopago = f.cleaned_data['tipopago'] if f.cleaned_data['tipopago'] else documentos.tipopago
                    documentos.subtipopago = f.cleaned_data['subtipopago'] if f.cleaned_data['subtipopago'] else documentos.subtipopago
                    documentos.ubicacion=f.cleaned_data['ubicacion'] if f.cleaned_data['ubicacion'] else documentos.ubicacion
                    documentos.nombrepercha=f.cleaned_data['nombrepercha'] if f.cleaned_data['nombrepercha'] else documentos.nombrepercha
                    documentos.nopercha=f.cleaned_data['nopercha'] if f.cleaned_data['nopercha'] else documentos.nopercha
                    documentos.externo_id=f.cleaned_data['externo'] if f.cleaned_data['externo'] else documentos.externo
                    documentos.nofila = f.cleaned_data['nofila'] if f.cleaned_data['nofila'] else documentos.nofila
                    documentos.proveedor = f.cleaned_data['proveedor'] if f.cleaned_data['proveedor'] else documentos.proveedor
                    documentos.tipo=f.cleaned_data['tipo'] if f.cleaned_data['tipo'] else documentos.tipo
                    documentos.egring=f.cleaned_data['egring'] if f.cleaned_data['egring'] else documentos.egring
                    documentos.fechadocumento=f.cleaned_data['fechadocumento'] if f.cleaned_data['fechadocumento'] else documentos.fechadocumento
                    documentos.observacion=f.cleaned_data['observacion'] if f.cleaned_data['observacion'] else documentos.observacion
                    documentos.save(request)
                    log(u'Edito Archivo proceso: %s' % documentos, request, "edi")
                    return JsonResponse({"result": "ok",})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'reportearchivoexcel':
            try:
                fechai = convertir_fecha(request.POST['ini'])
                fechaf = convertir_fecha(request.POST['fin'])
                fechaic = str(fechai)
                fechafc = str(fechaf)
                tipo = int(request.POST['tipo'])
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                title = easyxf('font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                title1 = easyxf('font: name Times New Roman, color-index black, bold on , height 200; alignment: horiz centre')
                wb = Workbook(encoding='utf-8')
                archivos = ArchivoProceso.objects.filter(status=True, fechadocumento__gte=fechai, fechadocumento__lte=fechaf, tipo=tipo).order_by('descripcion')
                if tipo == 2:
                    ws = wb.add_sheet('inscritos')
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 10, 'DEPARTAMENTO FINANCIERO - AREA ARCHIVO', title)
                    ws.write_merge(2, 2, 0, 10, 'DETALLE DE TRAMITES POR COMPROBANTE EGRESOS', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=archivoprocesos' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"Usuario creación", 6000),
                        (u"Fecha creación", 6000),
                        (u"Fecha comprobante egreso", 6000),
                        (u"No. de Trámite", 6000),
                        (u"Nombre Proveedor", 6000),
                        (u"Descripción", 3000),
                        (u"No. comprobante de egresos", 3000),
                        (u"Nombre percha", 3000),
                        (u"No. percha", 3000),
                        (u"Fila", 3000),
                        (u"Observación", 3000)
                    ]
                    row_num = 4
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    row_num = 5
                    i = 0
                    for r in archivos:
                        i=i+1
                        campo1 = str(r.usuario_creacion)
                        campo2 = str(r.fecha_creacion.date())
                        campo3 = str(r.fechadocumento)
                        campo4 = str(r.codigo)
                        campo5 = str(r.proveedor) if r.proveedor else ""
                        campo6 = str(r.descripcion)
                        campo7 = str(r.egring)
                        campo8 = str(r.nombrepercha)
                        campo9 = str(r.nopercha)
                        campo10 = str(r.nofila)
                        campo11 = str(r.observacion)
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
                        row_num += 1
                elif tipo == 1:
                    ws = wb.add_sheet('inscritos')
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 10, 'DEPARTAMENTO FINANCIERO - AREA ARCHIVO', title)
                    ws.write_merge(2, 2, 0, 10, 'DETALLE DE TRAMITES POR COMPROBANTE INGRESOS', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=archivoprocesos' + random.randint(1,  10000).__str__() + '.xls'
                    columns = [
                        (u"Usuario creación", 6000),
                        (u"Fecha creación", 6000),
                        (u"Fecha comprobante ingreso", 6000),
                        (u"No. comprobante de ingreso", 6000),
                        (u"Nombre del depositante", 6000),
                        (u"Descripción", 3000),
                        (u"No. percha", 3000),
                        (u"Fila", 3000),
                        (u"Observación", 3000)
                    ]
                    row_num = 4
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    row_num = 5
                    i = 0
                    for r in archivos:
                        i = i + 1
                        campo1 = str(r.usuario_creacion)
                        campo2 = str(r.fecha_creacion.date())
                        campo3 = str(r.fechadocumento)
                        campo4 = str(r.egring)
                        if r.externo:
                            if r.externo.persona:
                                campo5 = str(r.externo.persona.nombre_completo_inverso())
                            elif r.externo.nombrecomercial:
                                campo5 = str(r.externo.nombrecomercial)
                            else:
                                campo5 = ""
                        else:
                            campo5 = ""
                        campo6 = str(r.descripcion)
                        campo7 = str(r.nopercha)
                        campo8 = str(r.nofila)
                        campo9 = str(r.observacion)
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
                row_num=row_num + 1
                ws.write_merge(row_num, row_num, 0, 1, 'OBSERVACIONES:', title1)
                ws.write_merge(row_num, row_num, 2, 9, '', title1)
                wb.save(response)
                return response
            except Exception as ex:
                pass

        elif action == 'reportearchivoexcelinv':
            try:
                fechai = convertir_fecha(request.POST['ini'])
                fechaf = convertir_fecha(request.POST['fin'])
                fechaic = str(fechai)
                fechafc = str(fechaf)
                tipo = int(request.POST['tipo'])
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                title = easyxf('font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                title1 = easyxf('font: name Times New Roman, color-index black, bold on , height 200; alignment: horiz centre')
                wb = Workbook(encoding='utf-8')
                archivos = ArchivoProceso.objects.filter(status=True, fechadocumento__gte=fechai, fechadocumento__lte=fechaf, tipo=tipo).order_by('descripcion')
                if tipo == 2:
                    ws = wb.add_sheet('inscritos')
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 10, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', title)
                    ws.write_merge(2, 2, 0, 10, 'INVENTARIO DOCUMENTAL DEL ARCHIVO DE GESTIÓN', title)
                    ws.write_merge(3, 3, 0, 1, 'Sección: Dirección Administrativa y Financiera', font_style2)
                    ws.write_merge(4, 4, 0, 1, 'Sub sección: Contabilidad', font_style2)
                    ws.write_merge(3, 3, 5, 7, 'Desde: ' + str(fechai), font_style2)
                    ws.write_merge(4, 4, 5, 7, 'Hasta: ' + str(fechaf), font_style2)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=archivoprocesosinventario' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"Tipo de trámite", 6000),
                        (u"Serie documental", 6000),
                        (u"Fecha comprobante egreso", 6000),
                        (u"No. de Trámite", 6000),
                        (u"Nombre Proveedor", 6000),
                        (u"Descripción", 3000),
                        (u"No. comprobante de egresos", 3000),
                        (u"Nombre percha", 3000),
                        (u"No. percha", 3000),
                        (u"Fila", 3000),
                        (u"Original", 3000),
                        (u"Digitalizado", 3000),
                        (u"Disponible", 3000),
                        (u"Mes/Carpeta", 3000)
                    ]
                    row_num = 5
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    row_num = 6
                    i = 0
                    for r in archivos:
                        i=i+1
                        campo1 = str(r.get_tipo_display())
                        campo2 = str(r.nombrepercha)
                        campo3 = str(r.fechadocumento)
                        campo4 = str(r.codigo)
                        campo5 = str(r.proveedor) if r.proveedor else ""
                        campo6 = str(r.descripcion)
                        campo7 = str(r.egring)
                        campo8 = str(r.nombrepercha)
                        campo9 = str(r.nopercha)
                        campo10 = str(r.nofila)
                        campo11 = str(r.observacion)
                        tienearchivo = 'NO'
                        if r.archivo:
                            tienearchivo = 'SI'
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
                        ws.write(row_num, 10, tienearchivo, font_style2)
                        ws.write(row_num, 11, tienearchivo, font_style2)
                        ws.write(row_num, 12, tienearchivo, font_style2)
                        ws.write(row_num, 13, campo11, font_style2)
                        row_num += 1
                elif tipo == 1:
                    ws = wb.add_sheet('inscritos')
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 10, 'DEPARTAMENTO FINANCIERO - AREA ARCHIVO', title)
                    ws.write_merge(2, 2, 0, 10, 'DETALLE DE TRAMITES POR COMPROBANTE INGRESOS', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=archivoprocesos' + random.randint(1,  10000).__str__() + '.xls'
                    columns = [
                        (u"Usuario creación", 6000),
                        (u"Fecha creación", 6000),
                        (u"Fecha comprobante ingreso", 6000),
                        (u"No. comprobante de ingreso", 6000),
                        (u"Nombre del depositante", 6000),
                        (u"Descripción", 3000),
                        (u"No. percha", 3000),
                        (u"Fila", 3000),
                        (u"Observación", 3000)
                    ]
                    row_num = 4
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    row_num = 5
                    i = 0
                    for r in archivos:
                        i = i + 1
                        campo1 = str(r.usuario_creacion)
                        campo2 = str(r.fecha_creacion.date())
                        campo3 = str(r.fechadocumento)
                        campo4 = str(r.egring)
                        if r.externo:
                            if r.externo.persona:
                                campo5 = str(r.externo.persona.nombre_completo_inverso())
                            elif r.externo.nombrecomercial:
                                campo5 = str(r.externo.nombrecomercial)
                            else:
                                campo5 = ""
                        else:
                            campo5 = ""
                        campo6 = str(r.descripcion)
                        campo7 = str(r.nopercha)
                        campo8 = str(r.nofila)
                        campo9 = str(r.observacion)
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
                row_num=row_num + 1
                ws.write_merge(row_num, row_num, 0, 1, 'Total de trámites: ' + str(archivos.count()), font_style2)
                ws.write_merge(row_num + 1, row_num + 1, 0, 1, 'Ubicación del trámite: Archivo Financiero', font_style2)
                ws.write_merge(row_num + 3, row_num + 3, 0, 1, 'Fecha de creación del documento: ' + str(datetime.now().date()), font_style2)
                ws.write_merge(row_num + 4, row_num + 4, 0, 1, 'Elaborado por: ' + str(usuario), font_style2)
                ws.write_merge(row_num + 5, row_num + 5, 0, 4, 'Revisado por: Contador General ___________________________', font_style2)
                ws.write_merge(row_num + 6, row_num + 6, 0, 1, 'Aprobado por: Director Administrativo y Financiero', font_style2)
                wb.save(response)
                return response
            except Exception as ex:
                pass

        if action == 'reportearchivopdfinv':
            try:
                data = {}
                data['fechai'] = fechai = convertir_fecha(request.POST['ini'])
                data['fechaf'] = fechaf = convertir_fecha(request.POST['fin'])
                tipo = int(request.POST['tipo'])
                data['archivos'] = archivo = ArchivoProceso.objects.filter(status=True, fechadocumento__gte=fechai, fechadocumento__lte=fechaf, tipo=tipo).order_by('descripcion')
                data['total'] = archivo.count()
                data['fechaactual'] = datetime.now().date()
                data['usuario'] = request.user
                return conviert_html_to_pdf(
                    'fin_archivoproceso/reportearchivopdfinv.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        elif action == 'reporteingresodiarioexcel':
            try:
                fechai = convertir_fecha(request.POST['ini'])
                fechafaux = str(request.POST['fin']) + ' 23:59:00'
                fechaf = convertir_fecha_hora(fechafaux)
                fechaic = str(fechai)
                fechafc = str(convertir_fecha(request.POST['fin']))
                tipo = int(request.POST['tipo'])
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                title = easyxf('font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                title1 = easyxf('font: name Times New Roman, color-index black, bold on , height 200; alignment: horiz centre')
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('archivos')
                archivos = ArchivoProceso.objects.filter(
                    Q(status=True) & Q(fecha_creacion__gte=fechai) & Q(fecha_creacion__lte=fechaf)).order_by(
                    'descripcion')
                if tipo == 2:
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 10, 'DEPARTAMENTO FINANCIERO - AREA ARCHIVO', title)
                    ws.write_merge(2, 2, 0, 10, 'DETALLE DE TRAMITES POR COMPROBANTE EGRESOS', title)
                    ws.write_merge(3, 3, 0, 10, 'DESDE: %s HASTA: %s' % (fechaic, fechafc), title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=archivoprocesos' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"Usuario creación", 6000),
                        (u"Fecha creación", 6000),
                        (u"Fecha comprobante egreso", 6000),
                        (u"No. de Trámite", 6000),
                        (u"Nombre Proveedor", 6000),
                        (u"Descripción", 3000),
                        (u"No. comprobante de egresos", 3000),
                        (u"Nombre percha", 3000),
                        (u"No. percha", 3000),
                        (u"Fila", 3000),
                        (u"Observación", 3000)
                    ]
                    row_num = 4
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    row_num = 5
                    i = 0
                    for r in archivos:
                        i=i+1
                        campo1 = str(r.usuario_creacion)
                        campo2 = str(r.fecha_creacion.date())
                        campo3 = str(r.fechadocumento)
                        campo4 = str(r.codigo)
                        campo5 = str(r.proveedor) if r.proveedor else ""
                        campo6 = str(r.descripcion)
                        campo7 = str(r.egring)
                        campo8 = str(r.nombrepercha)
                        campo9 = str(r.nopercha)
                        campo10 = str(r.nofila)
                        campo11 = str(r.observacion)
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
                        row_num += 1
                elif tipo == 1:
                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 10, 'DEPARTAMENTO FINANCIERO - AREA ARCHIVO', title)
                    ws.write_merge(2, 2, 0, 10, 'DETALLE DE TRAMITES POR COMPROBANTE INGRESOS', title)
                    ws.write_merge(3, 3, 0, 10, 'DESDE: %s HASTA: %s' % (fechaic, fechafc), title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=archivoprocesos' + random.randint(1,  10000).__str__() + '.xls'
                    columns = [
                        (u"Fecha creación", 6000),
                        (u"Fecha comprobante ingreso", 6000),
                        (u"No. comprobante de ingreso", 6000),
                        (u"Nombre del depositante", 6000),
                        (u"Descripción", 3000),
                        (u"No. percha", 3000),
                        (u"Fila", 3000),
                        (u"Observación", 3000)
                    ]
                    row_num = 4
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    row_num = 5
                    i = 0
                    for r in archivos:
                        i = i + 1
                        campo1 = str(r.fecha_creacion.date())
                        campo2 = str(r.fechadocumento)
                        campo3 = str(r.egring)
                        if r.externo:
                            if r.externo.persona:
                                campo4 = str(r.externo.persona.nombre_completo_inverso())
                            elif r.externo.nombrecomercial:
                                campo4 = str(r.externo.nombrecomercial)
                            else:
                                campo4 = ""
                        else:
                            campo4 = ""
                        campo5 = str(r.descripcion)
                        campo6 = str(r.nopercha)
                        campo7 = str(r.nofila)
                        campo8 = str(r.observacion)
                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, campo7, font_style2)
                        ws.write(row_num, 7, campo8, font_style2)
                        row_num += 1
                row_num=row_num + 1
                ws.write_merge(row_num, row_num, 0, 1, 'OBSERVACIONES:', title1)
                ws.write_merge(row_num, row_num, 2, 9, '', title1)
                wb.save(response)
                return response
            except Exception as ex:
                pass

        elif action == 'addtipopago':
            try:
                f = TipoPagoArchivoForm(request.POST)
                if f.is_valid():
                    if TipoPagoArchivo.objects.values('id').filter(nombre=f.cleaned_data['nombre'].strip()).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un tipo de pago registrado con ese nombre."})
                    tipopago = TipoPagoArchivo(nombre=f.cleaned_data['nombre'])
                    tipopago.save(request)
                    log(u'Adiciono nuevo tipo pago archivo: %s' % tipopago, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edittipopago':
            try:
                tipopago = TipoPagoArchivo.objects.get(pk=request.POST['id'])
                f = TipoPagoArchivoForm(request.POST)
                if f.is_valid():
                    tipopago.nombre = f.cleaned_data['nombre']
                    tipopago.save(request)
                    log(u'Modificó tipo pago: %s' % tipopago, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletetipopago':
            try:
                tipopago = TipoPagoArchivo.objects.get(pk=request.POST['id'])
                if tipopago.usado():
                    return JsonResponse({"result": "bad", "mensaje": u"El tipo de pago ya esat siendo utilizado."})
                log(u'Eliminó tipo pago: %s' % tipopago, request, "del")
                tipopago.status=False
                tipopago.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addsubtipopago':
            try:
                f = TipoPagoArchivoForm(request.POST)
                if f.is_valid():
                    if SubTipoPagoArchivo.objects.values('id').filter(nombre=f.cleaned_data['nombre'].strip()).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un sub tipo de pago registrado con ese nombre."})
                    tipopago = TipoPagoArchivo.objects.get(id=request.POST['idti'])
                    subtipopago = SubTipoPagoArchivo(nombre=f.cleaned_data['nombre'], tipopago=tipopago)
                    subtipopago.save(request)
                    log(u'Adiciono nuevo sub tipo pago archivo: %s' % tipopago, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editsubtipopago':
            try:
                subtipopago = SubTipoPagoArchivo.objects.get(pk=request.POST['id'])
                f = TipoPagoArchivoForm(request.POST)
                if f.is_valid():
                    subtipopago.nombre = f.cleaned_data['nombre']
                    subtipopago.save(request)
                    log(u'Modificó sub tipo pago: %s' % subtipopago, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletesubtipopago':
            try:
                subtipopago = SubTipoPagoArchivo.objects.get(pk=request.POST['id'])
                log(u'Eliminó sub tipo pago: %s' % subtipopago, request, "del")
                subtipopago.status=False
                subtipopago.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'busquedasubtipopago':
            try:
                id=request.POST['id']
                subtipopago=None
                if int(id) >0:
                    subtipopago = SubTipoPagoArchivo.objects.filter(status=True, tipopago__id=id)
                else:
                    subtipopago = SubTipoPagoArchivo.objects.filter(status=True)
                lista = []
                for x in subtipopago:
                    lista.append([x.id, x.nombre])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                pass

        elif action == 'updateorden':
            try:
                pagina = PaginaArchivo.objects.get(pk=int(request.POST['id']))
                maximoorden = pagina.archivoproceso.paginaarchivo_set.values('id').filter(status=True).order_by('-orden').count()
                valor = int(request.POST['vc'])
                if valor <= maximoorden:
                    pagina.orden = valor
                    id = pagina.id
                    pagina.save(request)
                    ordennuevo=0
                    demasarchivos = pagina.archivoproceso.paginaarchivo_set.filter(status=True).exclude(pk=id).order_by('orden')
                    for x in demasarchivos:
                        ordennuevo += 1
                        if valor == ordennuevo:
                            ordennuevo += 1
                        x.orden=ordennuevo
                        x.save(request)
                else:
                    return JsonResponse({'result': 'bad', "mensaje": u"Orden no pertenece al rango permitido."})

                return JsonResponse({'result': 'ok', 'valor': pagina.orden})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u"Error al actualizar el orden."})

        elif action == 'deletearchivo':
            try:
                pagina = PaginaArchivo.objects.get(pk=request.POST['id'])
                log(u'Elimino archivo: %s' % PaginaArchivo, request, "del")
                pagina.status=False
                pagina.save(request)
                ordennuevo = 0
                demasarchivos = pagina.archivoproceso.paginaarchivo_set.filter(status=True).order_by('orden')
                for x in demasarchivos:
                    ordennuevo += 1
                    x.orden = ordennuevo
                    x.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addproveedor':
            try:
                f = ProveedorForm(request.POST)
                if f.is_valid():
                    if ProveedorArchivo.objects.values('id').filter(identificacion=f.cleaned_data['identificacion'].strip()).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un proveedor registrado con ese número de identificacion."})
                    proveedor = ProveedorArchivo(identificacion=f.cleaned_data['identificacion'],
                                          nombre=f.cleaned_data['nombre'],
                                          alias=f.cleaned_data['alias'],
                                          pais=f.cleaned_data['pais'],
                                          direccion=f.cleaned_data['direccion'],
                                          telefono=f.cleaned_data['telefono'],
                                          celular=f.cleaned_data['celular'],
                                          email=f.cleaned_data['email'],
                                          fax=f.cleaned_data['fax'])
                    proveedor.save(request)
                    log(u'Adiciono nuevo proveedor archivo: %s' % proveedor, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editproveedor':
            try:
                proveedor = ProveedorArchivo.objects.get(pk=request.POST['id'])
                f = ProveedorForm(request.POST)
                if f.is_valid():
                    proveedor.nombre = f.cleaned_data['nombre']
                    proveedor.alias = f.cleaned_data['alias']
                    proveedor.direccion = f.cleaned_data['direccion']
                    proveedor.pais = f.cleaned_data['pais']
                    proveedor.telefono = f.cleaned_data['telefono']
                    proveedor.celular = f.cleaned_data['celular']
                    proveedor.email = f.cleaned_data['email']
                    proveedor.fax = f.cleaned_data['fax']
                    proveedor.save(request)
                    log(u'Modificó proveedor archivo: %s' % proveedor, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleteproveedor':
            try:
                proveedor = ProveedorArchivo.objects.get(pk=request.POST['id'])
                if proveedor.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"El proveedor se encuentra en uso, no es posible eliminar."})
                log(u'Eliminó proveedor archivo: %s' % proveedor, request, "del")
                proveedor.status=False
                proveedor.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addpercha':
            try:
                f = NumeroForm(request.POST)
                if f.is_valid():
                    if PerchaArchivo.objects.values('id').filter(numero=f.cleaned_data['numero']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe el número."})
                    percha = PerchaArchivo(numero=f.cleaned_data['numero'])
                    percha.save(request)
                    log(u'Adiciono percha de archivo: %s' % percha, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editpercha':
            try:
                percha = PerchaArchivo.objects.get(pk=request.POST['id'])
                f = NumeroForm(request.POST)
                if f.is_valid():
                    if PerchaArchivo.objects.values('id').filter(numero=f.cleaned_data['numero']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe el número."})
                    percha.numero = f.cleaned_data['numero']
                    percha.save(request)
                    log(u'Modificó percha de archivo: %s' % percha, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletepercha':
            try:
                percha = PerchaArchivo.objects.get(pk=request.POST['id'])
                log(u'Eliminó percha de archivo: %s' % percha, request, "del")
                percha.status=False
                percha.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'addfila':
            try:
                f = NumeroForm(request.POST)
                if f.is_valid():
                    if FilaArchivo.objects.values('id').filter(numero=f.cleaned_data['numero']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe el número."})
                    fila = FilaArchivo(numero=f.cleaned_data['numero'])
                    fila.save(request)
                    log(u'Adiciono fila de archivo: %s' % fila, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editfila':
            try:
                fila = FilaArchivo.objects.get(pk=request.POST['id'])
                f = NumeroForm(request.POST)
                if f.is_valid():
                    if FilaArchivo.objects.values('id').filter(numero=f.cleaned_data['numero']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe el número."})
                    fila.numero = f.cleaned_data['numero']
                    fila.save(request)
                    log(u'Modificó fila de archivo: %s' % fila, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletefila':
            try:
                fila = FilaArchivo.objects.get(pk=request.POST['id'])
                log(u'Eliminó fila de archivo: %s' % fila, request, "del")
                fila.status=False
                fila.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'updatefila':
            try:
                archivoproceso = ArchivoProceso.objects.get(pk=int(request.POST['idr']))
                valor = int(request.POST['valor'])
                valoranterior = archivoproceso.nofila
                archivoproceso.nofila_id = valor
                archivoproceso.save(request)
                log(u'Actualizo fila de archivo: %s anterior: %s actual: %s' % (archivoproceso ,str(valoranterior if valoranterior else ""), str(valor)), request, "add")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u"Error al actualizar."})

        elif action == 'updatepercha':
            try:
                archivoproceso = ArchivoProceso.objects.get(pk=int(request.POST['idr']))
                valor = int(request.POST['valor'])
                valoranterior = archivoproceso.nofila
                archivoproceso.nopercha_id = valor
                archivoproceso.save(request)
                log(u'Actualizo percha de archivo: %s anterior: %s actual: %s' % (archivoproceso ,str(valoranterior if valoranterior else ""), str(valor)), request, "add")
                return JsonResponse({'result': 'ok'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', "mensaje": u"Error al actualizar."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar Proceso'
                    form = ArchivoProcesoForm()
                    form.add()
                    data['form'] = form
                    return render(request, "fin_archivoproceso/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'cerrar_proceso':
                try:
                    data['title'] = u'Cerrar Proceso'
                    data['proceso'] = ArchivoProceso.objects.get(pk=int(request.GET['id']))
                    return render(request, "fin_archivoproceso/cerrar.html", data)
                except Exception as ex:
                    pass

            elif action == 'abrir_proceso':
                try:
                    data['title'] = u'Abrir Proceso'
                    data['proceso'] = ArchivoProceso.objects.get(pk=int(request.GET['id']))
                    return render(request, "fin_archivoproceso/abrir.html", data)
                except Exception as ex:
                    pass

            elif action == 'archivos':
                try:
                    data['title'] = u'Adicionar Archivo'
                    form = PaginaArchivoForm()
                    data['proceso'] = ArchivoProceso.objects.get(pk=int(request.GET['id']))
                    data['archivos'] = PaginaArchivo.objects.filter(archivoproceso=data['proceso'], status=True).order_by('orden')
                    data['form'] = form
                    return render(request, "fin_archivoproceso/archivos.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar Archivo'
                    data['doc'] = doc = ArchivoProceso.objects.get(pk=int(request.GET['id']))
                    initial = model_to_dict(doc)
                    form = ArchivoProcesoForm(initial=initial)
                    form.edit(doc.externo)
                    data['form'] = form
                    return render(request, "fin_archivoproceso/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'tipopago':
                try:
                    data['title'] = u'Tipo pago'
                    ids = None
                    search = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        tipopago = TipoPagoArchivo.objects.filter(Q(nombre__icontains=search)).distinct().order_by('nombre')
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        tipopago = TipoPagoArchivo.objects.filter(id=ids).order_by('nombre')
                    else:
                        tipopago = TipoPagoArchivo.objects.filter(status=True).order_by('nombre')
                    paging = MiPaginador(tipopago, 25)
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
                    data['ids'] = ids if ids else None
                    data['page'] = page
                    data['tipopagos'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request, "fin_archivoproceso/tipopagos.html", data)
                except Exception as ex:
                    pass

            elif action == 'addtipopago':
                try:
                    data['title'] = u'Adicionar tipo pago'
                    data['form'] = TipoPagoArchivoForm()
                    if 'destino' in request.GET:
                        data['destino'] = request.GET['destino']
                    return render(request, "fin_archivoproceso/addtipopago.html", data)
                except Exception as ex:
                    pass

            elif action == 'edittipopago':
                try:
                    data['title'] = u'Editar tipo pago'
                    data['tipopago'] = tipopago = TipoPagoArchivo.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(tipopago)
                    form = TipoPagoArchivoForm(initial=initial)
                    data['form'] = form
                    return render(request, "fin_archivoproceso/edittipopago.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletetipopago':
                try:
                    data['title'] = u'Borrar tipo pago'
                    data['tipopago'] = TipoPagoArchivo.objects.get(pk=request.GET['id'])
                    return render(request, "fin_archivoproceso/deletetipopago.html", data)
                except Exception as ex:
                    pass

            elif action == 'subtipopago':
                try:
                    data['title'] = u'Sub tipo pago'
                    ids = None
                    search = None
                    tipopago = None
                    if 'idt' in request.GET:
                        tipopago = TipoPagoArchivo.objects.get(id=int(request.GET['idt']))
                        subtipopago = SubTipoPagoArchivo.objects.filter(tipopago=tipopago, status=True).distinct().order_by('nombre')
                    else:
                        subtipopago = SubTipoPagoArchivo.objects.filter(status=True).distinct().order_by('nombre')
                    if 's' in request.GET:
                        search = request.GET['s']
                        subtipopago = subtipopago.filter(Q(nombre__icontains=search)).distinct().order_by('nombre')
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        subtipopago = subtipopago.filter(id=ids).order_by('nombre')
                    paging = MiPaginador(subtipopago, 25)
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
                    data['ids'] = ids if ids else None
                    data['tipopago'] = tipopago if tipopago else None
                    data['page'] = page
                    data['subtipopagos'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request, "fin_archivoproceso/subtipopagos.html", data)
                except Exception as ex:
                    pass

            elif action == 'addsubtipopago':
                try:
                    data['title'] = u'Adicionar sub tipo pago'
                    tipopago = None
                    if 'idt' in request.GET:
                        data['tipopago'] = TipoPagoArchivo.objects.get(id=int(request.GET['idt']))
                    data['form'] = TipoPagoArchivoForm()
                    return render(request, "fin_archivoproceso/addsubtipopago.html", data)
                except Exception as ex:
                    pass

            elif action == 'editsubtipopago':
                try:
                    data['title'] = u'Editar sub tipo pago'
                    data['subtipopago'] = subtipopago = SubTipoPagoArchivo.objects.get(pk=request.GET['idsub'])
                    initial = model_to_dict(subtipopago)
                    form = TipoPagoArchivoForm(initial=initial)
                    data['form'] = form
                    return render(request, "fin_archivoproceso/editsubtipopago.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletesubtipopago':
                try:
                    data['title'] = u'Borrar sub tipo pago'
                    data['subtipopago'] = SubTipoPagoArchivo.objects.get(pk=request.GET['idsub'])
                    return render(request, "fin_archivoproceso/deletesubtipopago.html", data)
                except Exception as ex:
                    pass

            elif action == 'detalleproceso':
                try:
                    data = {}
                    data['proceso'] = proceso = ArchivoProceso.objects.get(pk=int(request.GET['id']))
                    data['paginas'] = proceso.paginaarchivo_set.filter(status=True)
                    template = get_template("fin_archivoproceso/detalleproceso.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'addproveedor':
                try:
                    data['title'] = u'Adicionar Proveedor'
                    data['form'] = ProveedorForm()
                    if 'destino' in request.GET:
                        data['destino'] = request.GET['destino']
                    return render(request, "fin_archivoproceso/addproveedor.html", data)
                except Exception as ex:
                    pass

            elif action == 'editproveedor':
                try:
                    data['title'] = u'Editar Proveedor'
                    data['proveedor'] = proveedor = ProveedorArchivo.objects.get(pk=request.GET['id'])
                    form = ProveedorForm(initial={'identificacion': proveedor.identificacion,
                                                  'nombre': proveedor.nombre,
                                                  'alias': proveedor.alias,
                                                  'direccion': proveedor.direccion,
                                                  'pais': proveedor.pais,
                                                  'telefono': proveedor.telefono,
                                                  'celular': proveedor.celular,
                                                  'email': proveedor.email,
                                                  'fax': proveedor.fax})
                    # form.editar()
                    data['form'] = form
                    return render(request, "fin_archivoproceso/editproveedor.html", data)
                except Exception as ex:
                    pass

            elif action == 'deleteproveedor':
                try:
                    data['title'] = u'Borrar Proveedor'
                    data['proveedor'] = ProveedorArchivo.objects.get(pk=request.GET['id'])
                    return render(request, "fin_archivoproceso/deleteproveedor.html", data)
                except Exception as ex:
                    pass

            elif action == 'proveedores':
                try:
                    data['title'] = u'Proveedor'
                    ids = None
                    search = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        proveedores = ProveedorArchivo.objects.filter(Q(nombre__icontains=search) | Q(identificacion__icontains=search)).distinct().order_by('nombre')
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        proveedores = ProveedorArchivo.objects.filter(id=ids).order_by('nombre')
                    else:
                        proveedores = ProveedorArchivo.objects.filter(status=True).order_by('nombre')
                    paging = MiPaginador(proveedores, 25)
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
                    data['ids'] = ids if ids else None
                    data['page'] = page
                    data['proveedores'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request, "fin_archivoproceso/proveedores.html", data)
                except Exception as ex:
                    pass

            elif action == 'perchas':
                try:
                    data['title'] = u'Perchas'
                    ids = None
                    search = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        perchas = PerchaArchivo.objects.filter(Q(numero__icontains=search), status=True ).distinct().order_by('numero')
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        perchas = PerchaArchivo.objects.filter(id=ids, status=True).order_by('numero')
                    else:
                        perchas = PerchaArchivo.objects.filter(status=True).order_by('numero')
                    paging = MiPaginador(perchas, 25)
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
                    data['ids'] = ids if ids else None
                    data['page'] = page
                    data['perchas'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request, "fin_archivoproceso/perchas.html", data)
                except Exception as ex:
                    pass

            elif action == 'addpercha':
                try:
                    data['title'] = u'Adicionar Percha'
                    data['form'] = NumeroForm()
                    return render(request, "fin_archivoproceso/addpercha.html", data)
                except Exception as ex:
                    pass

            elif action == 'editpercha':
                try:
                    data['title'] = u'Editar percha'
                    data['percha'] = percha = PerchaArchivo.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(percha)
                    form = NumeroForm(initial=initial)
                    data['form'] = form
                    return render(request, "fin_archivoproceso/editpercha.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletepercha':
                try:
                    data['title'] = u'Borrar percha'
                    data['percha'] = PerchaArchivo.objects.get(pk=request.GET['id'])
                    return render(request, "fin_archivoproceso/deletepercha.html", data)
                except Exception as ex:
                    pass

            elif action == 'filas':
                try:
                    data['title'] = u'Filas'
                    ids = None
                    search = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        filas = FilaArchivo.objects.filter(Q(numero__icontains=search), status=True ).distinct().order_by('numero')
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        filas = FilaArchivo.objects.filter(id=ids, status=True).order_by('numero')
                    else:
                        filas = FilaArchivo.objects.filter(status=True).order_by('numero')
                    paging = MiPaginador(filas, 25)
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
                    data['ids'] = ids if ids else None
                    data['page'] = page
                    data['filas'] = page.object_list
                    data['search'] = search if search else ""
                    return render(request, "fin_archivoproceso/filas.html", data)
                except Exception as ex:
                    pass

            elif action == 'addfila':
                try:
                    data['title'] = u'Adicionar fila'
                    data['form'] = NumeroForm()
                    return render(request, "fin_archivoproceso/addfila.html", data)
                except Exception as ex:
                    pass

            elif action == 'editfila':
                try:
                    data['title'] = u'Editar fila'
                    data['fila'] = fila = FilaArchivo.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(fila)
                    form = NumeroForm(initial=initial)
                    data['form'] = form
                    return render(request, "fin_archivoproceso/editfila.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletefila':
                try:
                    data['title'] = u'Borrar fila'
                    data['fila'] = FilaArchivo.objects.get(pk=request.GET['id'])
                    return render(request, "fin_archivoproceso/deletefila.html", data)
                except Exception as ex:
                    pass

            elif action == 'buscarcliente':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if len(s) == 1:
                        per = Externo.objects.filter((Q(persona__nombres__icontains=q)|Q(persona__apellido1__icontains=q)|Q(persona__apellido2__icontains=q)|Q(persona__cedula__contains=q)), Q(status= True)).distinct()[:15]
                    elif len(s) == 2:
                        per = Externo.objects.filter((Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1]))| (Q(persona__nombres__icontains=s[0]) & Q(persona__nombres__icontains=s[1]))|(Q(persona__nombres__icontains=s[0])&Q(persona__apellido1__contains=s[1]))).filter(status=True).distinct()[:15]
                    else:
                        per = Externo.objects.filter((Q(persona__nombres__contains=s[0]) & Q(persona__apellido1__contains=s[1]) & Q(persona__apellido2__contains=s[2])) | (Q(persona__nombres__contains=s[0]) & Q(persona__nombres__contains=s[1]) & Q(persona__apellido1__contains=s[2]))).filter(status=True).distinct()[:15]
                    data = {"result": "ok","results": [{"id": x.id, "name": x.flexbox_repr()} for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Archivos(Tramites y Procesos)'
                ids = None
                search = None
                if 's' in request.GET:
                    search = request.GET['s']
                    documentos = ArchivoProceso.objects.filter(Q(codigo__icontains=search) |
                                                               Q(descripcion__icontains=search) |
                                                               Q(nombrepercha__icontains=search) |
                                                               Q(egring__icontains=search) |
                                                               Q(observacion__icontains=search) |
                                                               Q(ubicacion__descripcion__icontains=search)).distinct().order_by('-fechadocumento')
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    documentos = ArchivoProceso.objects.filter(id=ids).order_by('-id')
                else:
                    documentos = ArchivoProceso.objects.all().order_by('-id')
                paging = MiPaginador(documentos, 25)
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
                data['ids'] = ids if ids else None
                data['page'] = page
                data['documentos'] = page.object_list
                data['search'] = search if search else ""
                data['tipotramite'] = TIPO_TRAMITE
                data['perchas'] =PerchaArchivo.objects.filter(status=True)
                data['filas'] =FilaArchivo.objects.filter(status=True)
                return render(request, "fin_archivoproceso/view.html", data)
            except Exception as ex:
                pass

def append_pdf(input, output):
    [output.addPage(input.getPage(page_num)) for page_num in range(input.numPages)]
