# -*- coding: UTF-8 -*-
import json
import os
import sys
import time
from datetime import timedelta
import threading
import xlsxwriter
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from webpush import send_user_notification
from xlwt import easyxf, XFStyle, Workbook
import random
from core.firmar_documentos import firmararchivogenerado
from decorators import secure_module
from sagest.forms import SubirPagoForm
from sagest.models import datetime, Banco
from settings import SITE_ROOT, SITE_STORAGE, DEBUG, MEDIA_ROOT, MEDIA_URL
from sga.commonviews import adduserdata, traerNotificaciones
from sga.funciones import MiPaginador, log, variable_valor, \
    convertir_fecha, remover_caracteres_tildes_unicode, generar_nombre, bad_json, validarcedula
from sga.models import Persona, BecaSolicitudRecorrido, BecaSolicitud, miinstitucion, BecaPeriodo, BecaAsignacion, \
    CuentaBancariaPersona, SolicitudPagoBeca, SolicitudPagoBecaHistorialArchivoFirma, Notificacion, \
    SolicitudPagoBecaDetalle, unicode
from django.template import Context
from django.template.loader import get_template

from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
#@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    if request.method == 'POST':
        data['action'] = action = request.POST['action']

        if action == 'firma_reporte_solicitud_pago_pdf':
            try:
                txtFirmas = json.loads(request.POST['txtFirmas'])
                if not txtFirmas:
                    raise NameError("Debe seleccionar ubicación de la firma")
                x = txtFirmas[-1]
                id = int(encrypt(request.POST['id_objeto']))
                responsables = request.POST.getlist('responsables[]')
                firma = request.FILES["firma"]
                passfirma = request.POST['palabraclave']
                archivo_generado = request.POST["url_archivo"]
                url_archivo = (SITE_STORAGE + archivo_generado).replace('\\', '/')
                url_archivo_short = archivo_generado.replace('/media/', '')
                eSolicitudPagoBeca = SolicitudPagoBeca.objects.get(id=id)
                fechaactual = datetime.now()
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'becas', 'solicitudes_pagos_becas', 'historial', str(eSolicitudPagoBeca.periodo_id), str(eSolicitudPagoBeca.id), ''))
                url_short = '/'.join(['becas', 'solicitudes_pagos_becas', 'historial', str(eSolicitudPagoBeca.periodo_id), str(eSolicitudPagoBeca.id), ''])
                _name = f'acta_solicitudpagobeca_{fechaactual.year}{fechaactual.month}{fechaactual.day}_{fechaactual.hour}{fechaactual.minute}{fechaactual.second}'
                firma = firmararchivogenerado(request, passfirma, firma, url_archivo, folder, _name, x["numPage"], x["x"], x["y"], x["width"], x["height"])
                if firma != True:
                    raise NameError(firma)
                log(u'Firmo Documento Acta Solicitud Pago Beca: {}'.format(_name), request, "add")
                url_file_generado = f'{folder}{_name}.pdf'
                eHistorialArchivoSolicitudBeca = eSolicitudPagoBeca.solicitudpagobecahistorialarchivofirma_set.filter(status=True).order_by('orden').last()
                if eHistorialArchivoSolicitudBeca is None:
                    eHistorialArchivoSolicitudBeca1 = SolicitudPagoBecaHistorialArchivoFirma(
                        solicitudpago=eSolicitudPagoBeca,
                        estado=1,
                        archivo=url_archivo_short,
                        orden=1,
                        personafirma=request.session['persona']
                    )
                    eHistorialArchivoSolicitudBeca1.save(request)
                    eHistorialArchivoSolicitudBeca2 = SolicitudPagoBecaHistorialArchivoFirma(
                        solicitudpago=eSolicitudPagoBeca,
                        estado=2,
                        archivo=f'{url_short}{_name}.pdf',
                        orden=2,
                        personafirma=request.session['persona']
                    )
                    eHistorialArchivoSolicitudBeca2.save(request)
                else:
                    eHistorialArchivoSolicitudBeca = SolicitudPagoBecaHistorialArchivoFirma(
                        solicitudpago=eSolicitudPagoBeca,
                        estado=2,
                        archivo=f'{url_short}{_name}.pdf',
                        orden=eHistorialArchivoSolicitudBeca.orden + 1,
                        personafirma=request.session['persona']
                    )
                    eHistorialArchivoSolicitudBeca.save(request)
                log(u'Guardo archivo solicitud de pago firma firmado: {}'.format(eSolicitudPagoBeca), request, "add")
                return JsonResponse({"result": False, "mensaje": "Guardado con exito", }, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar. %s" % ex.__str__()}, safe=False)

        elif action == 'generate_reporte_pendientes_pago_becas_financiero':
            try:
                noti = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                    titulo='Excel reporte de pendiente de pago financiero',
                                    destinatario=persona,
                                    url='',
                                    prioridad=1, app_label='SGA',
                                    fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                    en_proceso=True)
                noti.save(request)
                GenerateBackground(request=request, data=data, noti=noti).start()
                return JsonResponse({"result": "ok",
                                     "mensaje": u"Se ha procedido a ejecutar el proceso, en cuanto este se procedera a notificar",
                                     "btn_notificaciones": traerNotificaciones(request, data, persona)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar los datos.%s " % ex})

        elif action == 'subirdocumento':
            try:
                with transaction.atomic():
                    solicitud = SolicitudPagoBeca.objects.get(pk=request.POST['id'])
                    eHistorialArchivoSolicitudBeca = solicitud.solicitudpagobecahistorialarchivofirma_set.filter(
                        status=True).order_by('orden').last()
                    form = SubirPagoForm(request.POST)
                    if form.is_valid():
                        instance = SolicitudPagoBecaHistorialArchivoFirma(solicitudpago=solicitud,
                                                     personafirma=persona,
                                                     observacion = 'Documento cargado',
                                                     estado = 2,
                                                     orden=eHistorialArchivoSolicitudBeca.orden + 1,
                                                     )
                        instance.save(request)
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            fechaactual = datetime.now()
                            url_short = '/'.join(
                                [str(solicitud.periodo_id),
                                 str(solicitud.id), ''])
                            _name = f'acta_solicitudpagobeca_{fechaactual.year}{fechaactual.month}{fechaactual.day}_{fechaactual.hour}{fechaactual.minute}{fechaactual.second}'

                            newfile._name = f'{url_short}{_name}.pdf'
                            instance.archivo = newfile
                            instance.save(request)

                        log(u'Subió solicitud de pago firmado %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'generarbeneficiarioscsv':
                try:
                    __author__ = 'Unemi'
                    desde = datetime.combine(convertir_fecha(request.GET['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.GET['hasta']), time.max)

                    if 'bp' in request.POST and request.POST['bp'] and int(request.POST['bp']) > 0:
                        becaperiodos = BecaPeriodo.objects.filter(periodo_id=int(request.POST['bp']), status=True)
                    else:
                        becaperiodos = BecaPeriodo.objects.filter(status=True)

                    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'cuentabeneficiarioesigef'))

                    fuentenormal = easyxf('font: name Verdana, color-index black, height 150;')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Beneficiarios')

                    nombre = generar_nombre("beneficiarios_", "beneficiarios.csv")
                    filename = os.path.join(output_folder, nombre)

                    row_num = 0

                    for col_num in range(12):
                        ws.col(col_num).width = 5000

                    beneficiarios = Persona.objects.filter(cuentabancariapersona__status=True,
                                           cuentabancariapersona__archivo__isnull=False,
                                           inscripcion__becasolicitud__periodo_id__in=becaperiodos.values_list('periodo_id'),
                                           inscripcion__becasolicitud__becaasignacion__status=True,
                                           cuentabancariapersona__fechavalida__range=(desde, hasta),
                                           cuentabancariapersona__archivoesigef=False).distinct().order_by('apellido1', 'apellido2', 'nombres')

                    for beneficiario in beneficiarios:
                        ws.write(row_num, 0, beneficiario.identificacion(), fuentenormal)
                        ws.write(row_num, 1, remover_caracteres_tildes_unicode(beneficiario.nombre_completo_inverso()[:100]), fuentenormal)
                        ws.write(row_num, 2, remover_caracteres_tildes_unicode(beneficiario.direccion_completa()[:300]), fuentenormal)
                        ws.write(row_num, 3, beneficiario.telefono, fuentenormal)
                        ws.write(row_num, 4, '0', fuentenormal)
                        ws.write(row_num, 5, beneficiario.emailinst, fuentenormal)
                        ws.write(row_num, 6, beneficiario.cuentabancaria().banco.codigo, fuentenormal)
                        ws.write(row_num, 7, beneficiario.cuentabancaria().tipocuentabanco.id, fuentenormal)
                        ws.write(row_num, 8, beneficiario.cuentabancaria().numero, fuentenormal)
                        ws.write(row_num, 9, 'C', fuentenormal)
                        ws.write(row_num, 10, 'N', fuentenormal)
                        row_num += 1

                        cuentabeneficiario = beneficiario.cuentabancaria()
                        cuentabeneficiario.archivoesigef = True
                        cuentabeneficiario.save(request)

                    wb.save(filename)

                    response = HttpResponse(open(filename, 'rb'), content_type='application/ms-excel')
                    response['Content-Disposition'] = 'attachment; filename=' + nombre
                    return response
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar el archivo. Detalle: %s" % (msg)})

            elif action == 'beneficiarioscuentasrechazadas':
                try:
                    __author__ = 'Unemi'

                    fuentenormal = easyxtitulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo2 = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentemoneda = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str=' "$" #,##0.00')
                    fuentefecha = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                        num_format_str='yyyy-mm-dd')
                    fuentenumerodecimal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str='#,##0.00')
                    fuentenumeroentero = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Beneficiarios')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=cuentas_rechazadas_' + random.randint(1,10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 15, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 15, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', titulo2)
                    ws.write_merge(2, 2, 0, 15, 'LISTADO DE BENEFICIARIOS CON CUENTAS RECHAZADAS', titulo2)

                    row_num = 4
                    columns = [
                        (u"NOMBRES COMPLETOS", 10000),
                        (u"IDENTIFICACIÓN", 5000),
                        (u"PROVINCIA", 5000),
                        (u"CANTÓN", 5000),
                        (u"PARROQUIA", 5000),
                        (u"DIRECCIÓN", 15000),
                        (u"REFERENCIA", 15000),
                        (u"SECTOR", 15000),
                        (u"# CASA", 5000),
                        (u"CORREO PERSONAL", 8000),
                        (u"CORREO UNEMI", 8000),
                        (u"TELÉFONO", 5000),
                        (u"CELULAR", 5000),
                        (u"OPERADORA", 5000),
                        (u"OBSERVACIÓN", 20000)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    if 'bp' in request.POST and request.POST['bp'] and int(request.POST['bp']) > 0:
                        becaperiodos = BecaPeriodo.objects.filter(periodo_id=int(request.POST['bp']), status=True)
                    else:
                        becaperiodos = BecaPeriodo.objects.filter(status=True)
                    beneficiarios = Persona.objects.filter(cuentabancariapersona__status=True,
                                       cuentabancariapersona__archivo__isnull=False,
                                       inscripcion__becasolicitud__periodo_id__in=becaperiodos.values_list('periodo_id'),
                                       inscripcion__becasolicitud__becaasignacion__status=True,
                                       cuentabancariapersona__estadorevision=3).distinct().order_by('apellido1', 'apellido2', 'nombres')

                    for beneficiario in beneficiarios:
                        row_num += 1
                        ws.write(row_num, 0, beneficiario.nombre_completo_inverso(), fuentenormal)
                        ws.write(row_num, 1, beneficiario.identificacion(), fuentenormal)
                        ws.write(row_num, 2, str(beneficiario.provincia) if beneficiario.provincia else '', fuentenormal)
                        ws.write(row_num, 3, str(beneficiario.canton) if beneficiario.canton else '', fuentenormal)
                        ws.write(row_num, 4, str(beneficiario.parroquia) if beneficiario.parroquia else '', fuentenormal)
                        ws.write(row_num, 5, beneficiario.direccion_corta().upper(), fuentenormal)
                        ws.write(row_num, 6, beneficiario.referencia.upper(), fuentenormal)
                        ws.write(row_num, 7, beneficiario.sector.upper(), fuentenormal)
                        ws.write(row_num, 8, beneficiario.num_direccion, fuentenormal)
                        ws.write(row_num, 9, beneficiario.email, fuentenormal)
                        ws.write(row_num, 10, beneficiario.emailinst, fuentenormal)
                        ws.write(row_num, 11, beneficiario.telefono_conv, fuentenormal)
                        ws.write(row_num, 12, beneficiario.telefono, fuentenormal)
                        ws.write(row_num, 13, beneficiario.get_tipocelular_display() if beneficiario.tipocelular else '', fuentenormal)
                        cuentabeneficiario = beneficiario.cuentabancaria()
                        ws.write(row_num, 14, cuentabeneficiario.observacion, fuentenormal)

                    wb.save(response)
                    return response
                except Exception as ex:
                    print("Error...")
                    pass

            elif action == 'reporte_solicitud_pago_pdf':
                try:
                    if not 'id' in request.GET:
                        raise NameError('Parametro id no encontrado')
                    id = request.GET['id']
                    h = 'https'
                    if DEBUG:
                        h = 'http'
                    base_url = request.META['HTTP_HOST']
                    data['url_path'] = url_path = f"{h}://{unicode(base_url)}"

                    eSolicitudPagoBeca = SolicitudPagoBeca.objects.get(id=int(id))
                    eHistorialArchivoSolicitudBeca = eSolicitudPagoBeca.solicitudpagobecahistorialarchivofirma_set.filter(status=True).order_by('orden').last()
                    url_acta_compromiso = ''
                    if eHistorialArchivoSolicitudBeca is not None:
                        url_acta_compromiso = eHistorialArchivoSolicitudBeca.archivo.url
                    else:
                        isResult, message = eSolicitudPagoBeca.generar_reportepagobeca(request=request, url_path=url_path)
                        if not isResult:
                            raise NameError(message)
                        url_acta_compromiso = f'/media/{message}'

                    data['archivo'] = archivo = url_acta_compromiso
                    data['action_firma'] = 'firma_reporte_solicitud_pago_pdf'
                    data['url_archivo'] = f'{url_path}{url_acta_compromiso}'
                    data['id_objeto'] = eSolicitudPagoBeca.id
                    template = get_template("formfirmaelectronica.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(mensaje="Error, al generar el reporte. %s" % ex.__str__())

            elif action == 'subirdocumento':
                try:
                    form = ()
                    data['form'] = SubirPagoForm
                    data['filtro'] = SolicitudPagoBeca.objects.get(pk=int(request.GET['id']))
                    template = get_template("adm_solicitudpagobeca/modal/formsubir.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"Error al generar el archivo. Detalle: %s" % (msg)})



            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Solicitudes de pago'
                search = None
                ids = None
                solicitudes = SolicitudPagoBeca.objects.filter(status=True).order_by('-id')
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        solicitudes = solicitudes.filter(Q(persona__nombres__icontains=search) | Q(persona__apellido1__icontains=search) | Q(persona__apellido2__icontains=search) | Q(persona__cedula__icontains=search) | Q(persona__ruc__icontains=search) | Q(persona__pasaporte__icontains=search))
                        if search.isdigit():
                            solicitudes = solicitudes.filter(Q(persona__nombres__icontains=search) | Q(persona__apellido1__icontains=search) | Q(persona__apellido2__icontains=search) | Q(persona__cedula__icontains=search) | Q(persona__ruc__icontains=search) | Q(persona__pasaporte__icontains=search) | Q(numero=search) | Q(pk=search))
                    else:
                        solicitudes = solicitudes.filter(Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1]))
                if 'id' in request.GET:
                    ids = request.GET['id']
                    solicitudes = solicitudes.filter(id=ids)


                paging = MiPaginador(solicitudes, 25)
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
                data['solicitudes'] = page.object_list

                return render(request, "adm_solicitudpagobeca/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect("/?info=%s" % ex.__str__())


class GenerateBackground(threading.Thread):
    def __init__(self, request, data, noti=None):
        self.request = request
        self.data = data
        self.noti = noti
        threading.Thread.__init__(self)

    def run(self):
        request, data = self.request, self.data
        if request.method == 'POST':
            action = request.POST['action']
            if action == 'generate_reporte_pendientes_pago_becas_financiero':
                return generate_reporte_pendientes_pago_becas_financiero(request, data, noti=self.noti)


def generate_reporte_pendientes_pago_becas_financiero(request, data, noti=None):
    nombre_archivo = 'reporte_pagos_pendientes' + random.randint(1, 10000).__str__() + '.csv'
    folder = os.path.join(MEDIA_ROOT, 'becas', 'pagos_pendientes_financiero', '')
    os.makedirs(folder, exist_ok=True)
    directory = f'{folder}{nombre_archivo}'
    usernotify = request.user
    personadestino = Persona.objects.get(usuario_id=request.user.pk)
    with transaction.atomic():
        try:
            personadestino = request.session['persona']
            workbook = xlsxwriter.Workbook(directory)
            ws = workbook.add_worksheet('DETALLE')
            formatocabeceracolumna = workbook.add_format({
                'bold': 1,
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': 'silver',
                'text_wrap': 1,
                'font_size': 10})

            formatocelda = workbook.add_format({
                'border': 1
            })

            formatotitulo = workbook.add_format(
                {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 16})
            columns = [
                (u"IDENTIFICACIÓN", 15),
                (u"ESTUDIANTE", 50),
                (u"VALOR", 10),
                (u"TIPO BECA", 50),
                (u"SOLICITUD", 50),
                (u"PERIODO", 50),
                (u"IDENTIFICACIÓN VÁLIDA", 50),
            ]
            row_num = 0
            for col_num in range(len(columns)):
                ws.write(row_num, col_num, columns[col_num][0], formatocabeceracolumna)
                ws.set_column(col_num, col_num, columns[col_num][1])

            if 'id' in request.POST:
                if request.POST['id']:
                    id = [int(request.POST['id'])]

            if 'lista' in request.POST:
                lista = json.loads(request.POST['lista'])
                id = lista

            eSolicitudPagoBeca = SolicitudPagoBeca.objects.values_list("id",flat=True).filter(id__in=id)
            pagos = SolicitudPagoBecaDetalle.objects.filter(status=True,solicitudpago_id__in=eSolicitudPagoBeca)
            row_num = 1
            valido=""
            for pago in pagos:
                ws.write(row_num, 0, pago.asignacion.solicitud.inscripcion.persona.identificacion(), formatocelda)
                ws.write(row_num, 1, remover_caracteres_tildes_unicode(pago.asignacion.solicitud.inscripcion.persona.__str__()), formatocelda)
                ws.write(row_num, 2, pago.monto, formatocelda)
                ws.write(row_num, 3, remover_caracteres_tildes_unicode(pago.asignacion.solicitud.becatipo.__str__()), formatocelda)
                ws.write(row_num, 4, str(pago.solicitudpago.numerosolicitud), formatocelda)
                ws.write(row_num, 5, str(pago.solicitudpago.periodo), formatocelda)
                if pago.asignacion.solicitud.inscripcion.persona.cedula:
                    valido = validarcedula(pago.asignacion.solicitud.inscripcion.persona.cedula)
                ws.write(row_num, 6, str(valido), formatocelda)
                pago.generadofinanciero = True
                pago.save(request)
                row_num += 1
            workbook.close()
            response = HttpResponse(directory, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename=%s' % nombre_archivo
            if noti is None:
                noti = Notificacion(cuerpo='Reporte Listo',
                                    titulo='Reporte de pendiente de pagos beca financiero',
                                    destinatario=personadestino,
                                    url="{}becas/pagos_pendientes_financiero/{}".format(MEDIA_URL, nombre_archivo),
                                    prioridad=1,
                                    app_label='SGA',
                                    fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2, en_proceso=False)
                noti.save(request)
            else:
                noti.en_proceso = False
                noti.cuerpo = 'Reporte Listo'
                noti.url = "{}becas/pagos_pendientes_financiero/{}".format(MEDIA_URL, nombre_archivo)
                noti.save()
            send_user_notification(user=usernotify, payload={
                "head": "Reporte terminado",
                "body": 'Reporte de Pendientes de Pagos Beca Financiero',
                "action": "notificacion",
                "timestamp": time.mktime(datetime.now().timetuple()),
                "url": "{}becas/pagos_pendientes_financiero/{}".format(MEDIA_URL, nombre_archivo),
                "btn_notificaciones": traerNotificaciones(request, data, personadestino),
                "mensaje": "Su reporte ha sido terminado"
            }, ttl=500)
        except Exception as ex:
            transaction.set_rollback(True)
            print(ex)
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            textoerror = 'Reporte Fallido - {} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
            if noti is None:
                noti = Notificacion(cuerpo='Reporte Fallido', titulo='Reporte de Pendientes de Pagos Beca Financiero falló en la ejecución',
                                    destinatario=personadestino, prioridad=1, app_label='SGA', fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2, en_proceso=False, error=True)
                noti.save(request)
            else:
                noti.en_proceso = False
                noti.error = True
                noti.titulo = 'Reporte de Pendientes de Pagos Beca Financiero falló en la ejecución'
                noti.cuerpo = textoerror
                noti.url = "{}becas/pagos_pendientes_financiero/{}".format(MEDIA_URL, nombre_archivo)
                noti.save()

            send_user_notification(user=usernotify, payload={
                "head": "Reporte Fallido",
                "body": 'Reporte de Pendientes de Pagos Beca Financiero a fallado',
                "action": "notificacion",
                "timestamp": time.mktime(datetime.now().timetuple()),
                "btn_notificaciones": traerNotificaciones(request, data, personadestino),
                "mensaje": textoerror,
                "error": True
            }, ttl=500)