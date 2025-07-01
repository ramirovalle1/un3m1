# -*- coding: UTF-8 -*-
from datetime import time
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from xlwt import easyxf, XFStyle, Workbook
import random
from decorators import secure_module
from sagest.models import datetime, Banco
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, variable_valor, \
    convertir_fecha, remover_caracteres_tildes_unicode, cuenta_email_disponible
from sga.models import Persona, \
    BecaSolicitudRecorrido, BecaSolicitud, miinstitucion, SolicitudDevolucionDinero, SolicitudDevolucionDineroRecorrido, \
    CUENTAS_CORREOS
from django.template import Context
from django.template.loader import get_template

from sga.tasks import send_html_mail, conectar_cuenta


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'validarsolicitud':
            try:
                id = int(request.POST['id'])
                estado = int(request.POST['estadosolicitud'])
                validacuenta = request.POST['validacuenta']

                solicitud = SolicitudDevolucionDinero.objects.get(pk=id)
                beneficiario = solicitud.persona

                solicitud.estado = estado
                solicitud.personarevisa = persona
                solicitud.observacion = request.POST['observacion'].strip().upper() if 'observacion' in request.POST else ''
                solicitud.fechavalida = datetime.now().date() if estado == 2 else None
                solicitud.montodevolver = request.POST['montodevolver'] if 'montodevolver' in request.POST else None
                solicitud.save(request)

                recorrido = SolicitudDevolucionDineroRecorrido(solicituddevolucion=solicitud,
                                                               fecha=datetime.now().date(),
                                                               observacion='APROBADO POR TESORERÍA' if estado == 2 else solicitud.observacion,
                                                               estado=estado
                                                               )
                recorrido.save(request)

                if validacuenta == 'S' and estado == 2:
                    cuentabancaria = beneficiario.cuentabancaria()
                    cuentabancaria.banco_id = int(request.POST['banco'])
                    cuentabancaria.tipocuentabanco_id = int(request.POST['tipocuenta'])
                    cuentabancaria.numero = request.POST['numerocuenta'].strip()
                    cuentabancaria.estadorevision = 2
                    cuentabancaria.observacion = ''
                    cuentabancaria.fechavalida = datetime.now().date()
                    cuentabancaria.save(request)

                if solicitud.estado == 2:
                    tituloemail = "Solicitud de Devolución de Dinero - APROBADA"
                    mensaje = "su solicitud de devolución de dinero fue <strong>APROBADA</strong>"
                    observaciones = ""
                else:
                    tituloemail = "Solicitud de Devolución de Dinero - RECHAZADA"
                    mensaje = "se presentaron novedades durante la revisión de su solicitud de devolución de dinero. Su solicitud fue <strong>RECHAZADA</strong>"
                    observaciones = solicitud.observacion

                cuenta = cuenta_email_disponible()

                send_html_mail(tituloemail,
                               "emails/notificarestadodevoluciondinero.html",
                               {'sistema': u'SGA - UNEMI',
                                'mensaje': mensaje,
                                'fecha': datetime.now().date(),
                                'hora': datetime.now().time(),
                                'observaciones': observaciones,
                                'saludo': 'Estimada' if solicitud.persona.sexo_id == 1 else 'Estimado',
                                'estudiante': solicitud.persona.nombre_completo_inverso(),
                                'autoridad2': '',
                                't': miinstitucion()
                                },
                               solicitud.persona.lista_emails_envio(),
                               [],
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                log(u'Revisó solicitud de devolución de dinero: %s  - %s' % (persona, solicitud), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'verificar_solicitudes_validadas_reporte':
            try:
                if datetime.strptime(request.POST['desde'], '%d-%m-%Y') <= datetime.strptime(request.POST['hasta'], '%d-%m-%Y'):
                    desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)

                    if SolicitudDevolucionDinero.objects.filter(status=True, estado=2, fechavalida__range=(desde, hasta)).exists():
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "No existen solicitudes validadas en el rango de fechas"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "La fecha desde debe ser menor o igual a la fecha hasta"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'verificar_solicitudes_rechazadas':
            try:
                if SolicitudDevolucionDinero.objects.filter(status=True, estado=3).exists():
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "No existen solicitudes rechazadas para generar el reporte"})

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'verificar_solicitudes_pendientes_revisar':
            try:
                if SolicitudDevolucionDinero.objects.filter(status=True, estado=1).exists():
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "No existen solicitudes pendientes de revisar para generar el reporte"})

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'validarsolicitud':
                try:
                    data['title'] = u'Revisar/Aprobar Solicitud de Devolución'
                    data['ids'] = int(request.GET['ids'])

                    data['solicitud'] = solicitud = SolicitudDevolucionDinero.objects.get(pk=int(request.GET['ids']))

                    beneficiario = solicitud.persona
                    cuentabancaria = beneficiario.cuentabancaria()
                    data['beneficiario'] = beneficiario
                    data['cuentabancaria'] = cuentabancaria
                    data['validarcuenta'] = False if cuentabancaria.estadorevision == 2 else True
                    data['estadodocumento'] = request.GET['estadodocumento']

                    data['bancos'] = Banco.objects.filter(status=True).order_by('nombre')

                    if solicitud.personarevisa:
                        if solicitud.personarevisa != persona and solicitud.estado != 1:
                            return JsonResponse({"result": "bad", "mensaje": "La solicitud está siendo revisada por otro usuario."})
                        else:
                            if solicitud.estado != 2 and solicitud.estado != 3:
                                solicitud.personarevisa = persona
                                solicitud.estado = 5
                    else:
                        solicitud.personarevisa = persona
                        solicitud.estado = 5

                    solicitud.save(request)

                    if solicitud.estado in [2, 3]:
                        data['permite_modificar'] = False
                    else:
                        data['permite_modificar'] = True

                    template = get_template("rec_devoluciondinero/validarsolicitud.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'generarbeneficiarioscsv':
                try:
                    __author__ = 'Unemi'
                    desde = datetime.combine(convertir_fecha(request.GET['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.GET['hasta']), time.max)

                    fuentenormal = easyxf('font: name Verdana, color-index black, height 150;')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Beneficiarios')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=beneficiarios_' + random.randint(1,10000).__str__() + '.csv'

                    row_num = 0

                    for col_num in range(12):
                        ws.col(col_num).width = 5000

                    beneficiarios = Persona.objects.filter(cuentabancariapersona__status=True,
                                           cuentabancariapersona__archivo__isnull=False,
                                           inscripcion__becasolicitud__periodo_id__in=[110, 90],
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


                    wb.save(response)
                    return response
                except Exception as ex:
                    transaction.set_rollback(True)
                    print("Error...")
                    pass

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

                    beneficiarios = Persona.objects.filter(cuentabancariapersona__status=True,
                                       cuentabancariapersona__archivo__isnull=False,
                                       inscripcion__becasolicitud__periodo_id__in=[110, 90],
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

            elif action == 'solicitudesvalidadas':
                try:
                    __author__ = 'Unemi'

                    desde = datetime.combine(convertir_fecha(request.GET['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.GET['hasta']), time.max)

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
                    fuentenormalcent = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')

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
                    ws = wb.add_sheet('Solicitudes')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=solicitudes_validadas_' + random.randint(1,10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 11, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 11, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', titulo2)
                    ws.write_merge(2, 2, 0, 11, 'LISTADO DE SOLICITUDES DE DEVOLUCIÓN DE DINERO VALIDADAS', titulo2)

                    row_num = 4
                    columns = [
                        (u"# SOLICITUD", 3000),
                        (u"FECHA APROBACIÓN", 3500),
                        (u"IDENTIFICACIÓN", 5000),
                        (u"NOMBRES COMPLETOS", 10000),
                        (u"CORREO PERSONAL", 8000),
                        (u"CORREO UNEMI", 8000),
                        (u"TELÉFONO", 5000),
                        (u"CELULAR", 5000),
                        (u"OPERADORA", 5000),
                        (u"MOTIVO DEVOLUCIÓN", 10000),
                        (u"TOTAL DEPOSITADO", 5000),
                        (u"TOTAL A DEVOLVER", 5000)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    solicitudes = SolicitudDevolucionDinero.objects.filter(status=True, estado=2, fechavalida__range=(desde, hasta)).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    for solicitud in solicitudes:
                        row_num += 1
                        ws.write(row_num, 0, str(solicitud.id).zfill(5), fuentenormalcent)
                        ws.write(row_num, 1, solicitud.fechavalida, fuentefecha)
                        ws.write(row_num, 2, solicitud.persona.identificacion(), fuentenormal)
                        ws.write(row_num, 3, solicitud.persona.nombre_completo_inverso(), fuentenormal)
                        ws.write(row_num, 4, solicitud.persona.email, fuentenormal)
                        ws.write(row_num, 5, solicitud.persona.emailinst, fuentenormal)
                        ws.write(row_num, 6, solicitud.persona.telefono_conv, fuentenormal)
                        ws.write(row_num, 7, solicitud.persona.telefono, fuentenormal)
                        ws.write(row_num, 8, solicitud.persona.get_tipocelular_display() if solicitud.persona.tipocelular else '', fuentenormal)
                        ws.write(row_num, 9, solicitud.motivo.strip(), fuentenormal)
                        ws.write(row_num, 10, solicitud.monto, fuentemoneda)
                        ws.write(row_num, 11, solicitud.montodevolver, fuentemoneda)

                    wb.save(response)
                    return response
                except Exception as ex:
                    print("Error...")
                    pass

            elif action == 'solicitudesrechazadas':
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

                    fuentenormalwrap = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormalwrap.alignment.wrap = True

                    fuentenormalcent = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')

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
                    ws = wb.add_sheet('Solicitudes')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=solicitudes_rechazadas_' + random.randint(1,10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 11, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 11, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', titulo2)
                    ws.write_merge(2, 2, 0, 11, 'LISTADO DE SOLICITUDES DE DEVOLUCIÓN DE DINERO RECHAZADAS', titulo2)

                    row_num = 4
                    columns = [
                        (u"# SOLICITUD", 3000),
                        (u"FECHA RECHAZO", 3500),
                        (u"IDENTIFICACIÓN", 5000),
                        (u"NOMBRES COMPLETOS", 10000),
                        (u"CORREO PERSONAL", 8000),
                        (u"CORREO UNEMI", 8000),
                        (u"TELÉFONO", 5000),
                        (u"CELULAR", 5000),
                        (u"OPERADORA", 5000),
                        (u"MOTIVO DEVOLUCIÓN", 10000),
                        (u"TOTAL DEPOSITADO", 5000),
                        (u"OBSERVACIÓN", 30000)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    solicitudes = SolicitudDevolucionDinero.objects.filter(status=True, estado=3).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    for solicitud in solicitudes:
                        row_num += 1
                        ws.write(row_num, 0, str(solicitud.id).zfill(5), fuentenormalcent)
                        ws.write(row_num, 1, solicitud.fecha_modificacion, fuentefecha)
                        ws.write(row_num, 2, solicitud.persona.identificacion(), fuentenormal)
                        ws.write(row_num, 3, solicitud.persona.nombre_completo_inverso(), fuentenormal)
                        ws.write(row_num, 4, solicitud.persona.email, fuentenormal)
                        ws.write(row_num, 5, solicitud.persona.emailinst, fuentenormal)
                        ws.write(row_num, 6, solicitud.persona.telefono_conv, fuentenormal)
                        ws.write(row_num, 7, solicitud.persona.telefono, fuentenormal)
                        ws.write(row_num, 8, solicitud.persona.get_tipocelular_display() if solicitud.persona.tipocelular else '', fuentenormal)
                        ws.write(row_num, 9, solicitud.motivo.strip(), fuentenormal)
                        ws.write(row_num, 10, solicitud.monto, fuentemoneda)
                        ws.write(row_num, 11, solicitud.observacion.strip(), fuentenormalwrap)

                    wb.save(response)
                    return response
                except Exception as ex:
                    print("Error...")
                    pass

            elif action == 'solicitudespendientesrevisar':
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

                    fuentenormalwrap = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormalwrap.alignment.wrap = True

                    fuentenormalcent = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')

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
                    ws = wb.add_sheet('Solicitudes')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=solicitudes_pendientes_' + random.randint(1,10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 10, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', titulo2)
                    ws.write_merge(2, 2, 0, 10, 'LISTADO DE SOLICITUDES DE DEVOLUCIÓN DE DINERO PENDIENTES DE REVISAR', titulo2)

                    row_num = 4
                    columns = [
                        (u"# SOLICITUD", 3000),
                        (u"FECHA SOLICITUD", 3500),
                        (u"IDENTIFICACIÓN", 5000),
                        (u"NOMBRES COMPLETOS", 10000),
                        (u"CORREO PERSONAL", 8000),
                        (u"CORREO UNEMI", 8000),
                        (u"TELÉFONO", 5000),
                        (u"CELULAR", 5000),
                        (u"OPERADORA", 5000),
                        (u"MOTIVO DEVOLUCIÓN", 10000),
                        (u"TOTAL DEPOSITADO", 5000)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    solicitudes = SolicitudDevolucionDinero.objects.filter(status=True, estado=1).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    for solicitud in solicitudes:
                        row_num += 1
                        ws.write(row_num, 0, str(solicitud.id).zfill(5), fuentenormalcent)
                        ws.write(row_num, 1, solicitud.fecha_creacion, fuentefecha)
                        ws.write(row_num, 2, solicitud.persona.identificacion(), fuentenormal)
                        ws.write(row_num, 3, solicitud.persona.nombre_completo_inverso(), fuentenormal)
                        ws.write(row_num, 4, solicitud.persona.email, fuentenormal)
                        ws.write(row_num, 5, solicitud.persona.emailinst, fuentenormal)
                        ws.write(row_num, 6, solicitud.persona.telefono_conv, fuentenormal)
                        ws.write(row_num, 7, solicitud.persona.telefono, fuentenormal)
                        ws.write(row_num, 8, solicitud.persona.get_tipocelular_display() if solicitud.persona.tipocelular else '', fuentenormal)
                        ws.write(row_num, 9, solicitud.motivo.strip(), fuentenormal)
                        ws.write(row_num, 10, solicitud.monto, fuentemoneda)

                    wb.save(response)
                    return response
                except Exception as ex:
                    print("Error...")
                    pass

            elif action == 'beneficiarioscuentaspendientesrevisar':
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
                    response['Content-Disposition'] = 'attachment; filename=cuentas_pendientes_revisar_' + random.randint(1,10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 14, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 14, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', titulo2)
                    ws.write_merge(2, 2, 0, 14, 'LISTADO DE BENEFICIARIOS CON CUENTAS PENDIENTES DE REVISAR', titulo2)

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
                        (u"OPERADORA", 5000)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    beneficiarios = Persona.objects.filter(cuentabancariapersona__status=True,
                                       cuentabancariapersona__archivo__isnull=False,
                                       inscripcion__becasolicitud__periodo_id__in=[110, 90],
                                       inscripcion__becasolicitud__becaasignacion__status=True,
                                       inscripcion__becasolicitud__becaasignacion__tipo=1,
                                       inscripcion__becasolicitud__becaasignacion__cargadocumento=True,
                                       cuentabancariapersona__estadorevision=1).distinct().order_by('apellido1', 'apellido2', 'nombres')

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
                        # cuentabeneficiario = beneficiario.cuentabancaria()

                    wb.save(response)
                    return response
                except Exception as ex:
                    print("Error...")
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Solicitudes de Devolución de Dinero'
            search = None
            ids = None

            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    solicitudes = SolicitudDevolucionDinero.objects.filter(Q(persona__nombres__icontains=search)|
                                                     Q(persona__apellido1__icontains=search)|
                                                     Q(persona__apellido2__icontains=search)|
                                                     Q(persona__cedula__icontains=search)|
                                                     Q(persona__ruc__icontains=search)|
                                                     Q(persona__pasaporte__icontains=search), status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                else:
                    solicitudes = SolicitudDevolucionDinero.objects.filter(Q(persona__apellido1__icontains=ss[0]) &
                                                                           Q(persona__apellido2__icontains=ss[1])
                                                                           ,status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
            elif 'id' in request.GET:
                ids = request.GET['id']
                solicitudes = SolicitudDevolucionDinero.objects.filter(id=ids, status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
            else:
                solicitudes = SolicitudDevolucionDinero.objects.filter(status=True).order_by('persona__apellido1',
                                                                                             'persona__apellido2',
                                                                                             'persona__nombres')

            estadodocumento = 0
            if 'estadodocumento' in request.GET:
                estadodocumento = int(request.GET['estadodocumento'])
                if estadodocumento > 0:
                    solicitudes = solicitudes.filter(estado=estadodocumento)


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

            data['totalsolicitudes'] = total = solicitudes.count()
            data['totalaprobadas'] = aprobadas = solicitudes.filter(estado=2).count()
            data['totalrechazadas'] = rechazadas = solicitudes.filter(estado=3).count()
            data['totalrevision'] = revision = solicitudes.filter(estado=5).count()
            data['totalpendiente'] = total - (aprobadas + rechazadas + revision)
            data['estadodocumento'] = estadodocumento


            data['fechaactual'] = datetime.now().strftime('%d-%m-%Y')
            return render(request, "rec_devoluciondinero/view.html", data)
