# -*- coding: UTF-8 -*-
import os
from datetime import time

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from xlwt import easyxf, XFStyle, Workbook
import random
from decorators import secure_module
from sagest.forms import BancoForm
from sagest.funciones import encrypt_id
from sagest.models import datetime, Banco
from settings import SITE_ROOT, SITE_STORAGE, DEBUG
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, variable_valor, \
    convertir_fecha, remover_caracteres_tildes_unicode, generar_nombre
from sga.models import Persona, BecaSolicitudRecorrido, BecaSolicitud, miinstitucion, BecaPeriodo, BecaAsignacion, \
    CuentaBancariaPersona
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

        if action == 'validarcuenta':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] else None
                if not CuentaBancariaPersona.objects.filter(pk=id).exists():
                    raise NameError(u"No existe beneficiario a validar")
                cuentabancaria = CuentaBancariaPersona.objects.get(pk=id)
                beneficiario = cuentabancaria.persona

                if not 'bp' in request.POST and not request.POST['bp'] and int(request.POST['bp']) == 0:
                    raise NameError(u"Seleccione un periodo de beca para validar")
                becaperiodo = BecaPeriodo.objects.get(periodo_id=int(request.POST['bp']))

                # if not becaperiodo.puede_revisar_validar_cuentabancaria():
                #     raise NameError(u"Se completo el límite de becados del período %s"%(becaperiodo))

                solicitudayuda = solicitudbeca = None

                if becaperiodo.periodo.id == 110 and BecaSolicitud.objects.filter(inscripcion__persona=cuentabancaria.persona, periodo=becaperiodo.periodo, status=True, becaaceptada=2).exists():
                    solicitudayuda = BecaSolicitud.objects.get(inscripcion__persona=cuentabancaria.persona, periodo=becaperiodo.periodo, status=True, becaaceptada=2)

                if BecaSolicitud.objects.filter(inscripcion__persona=cuentabancaria.persona, periodo=becaperiodo.periodo, status=True, becaaceptada=2).exists():
                    solicitudbeca = BecaSolicitud.objects.get(inscripcion__persona=cuentabancaria.persona, periodo=becaperiodo.periodo, status=True, becaaceptada=2)

                cuentabancaria.banco_id = int(request.POST['banco'])
                cuentabancaria.tipocuentabanco_id = int(request.POST['tipocuenta'])
                cuentabancaria.numero = request.POST['numerocuenta'].strip()
                cuentabancaria.estadorevision = int(request.POST['estadocuenta'])
                cuentabancaria.observacion = request.POST['observacion'].strip().upper() if 'observacion' in request.POST else ''
                cuentabancaria.fechavalida = datetime.now().date() if int(request.POST['estadocuenta']) == 2 else None
                cuentabancaria.save(request)

                solicitud = solicitudayuda if solicitudayuda else solicitudbeca

                if cuentabancaria.estadorevision == 3:
                    tituloemail = "Novedades con la Cuenta Bancaria"
                    mensaje = " se presentaron novedades con la revisión de la información de su cuenta bancaria"
                    observaciones = cuentabancaria.observacion

                    recorrido = BecaSolicitudRecorrido(solicitud=solicitud,
                                                       observacion=observaciones,
                                                       estado=16,
                                                       fecha=datetime.now().date())
                    recorrido.save(request)

                    send_html_mail(tituloemail, "emails/notificarrevisiondocumento.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'mensaje': mensaje,
                                    'fecha': datetime.now().date(),
                                    'hora': datetime.now().time(),
                                    'observaciones': observaciones,
                                    'saludo': 'Estimada' if solicitud.inscripcion.persona.sexo_id == 1 else 'Estimado',
                                    'estudiante': solicitud.inscripcion.persona.nombre_completo_inverso(),
                                    'autoridad2': '',
                                    't': miinstitucion()
                                    },
                                   solicitud.inscripcion.persona.lista_emails_envio(),
                                   [],
                                   cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                   )
                else:

                    recorrido = BecaSolicitudRecorrido(solicitud=solicitud,
                                                       observacion="CUENTA BANCARIA VALIDADA",
                                                       estado=15,
                                                       fecha=datetime.now().date())
                    recorrido.save(request)
                    tituloemail = "Cuenta Bancaria Validada"
                    mensaje = "la información correspondiente a la cuenta bancaria registrada para la Beca ha sido Validada"
                    observaciones = ""
                    correos = solicitud.inscripcion.persona.lista_emails_envio()
                    if DEBUG:
                        correos = ['atorrese@unemi.edu.ec', ]
                    send_html_mail(tituloemail, "emails/notificarrevisiondocumento.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'mensaje': mensaje,
                                    'fecha': datetime.now().date(),
                                    'hora': datetime.now().time(),
                                    'observaciones': observaciones,
                                    'saludo': 'Estimada' if solicitud.inscripcion.persona.sexo_id == 1 else 'Estimado',
                                    'estudiante': solicitud.inscripcion.persona.nombre_completo_inverso(),
                                    'autoridad2': '',
                                    't': miinstitucion()
                                    },
                                   correos,
                                   [],
                                   cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                   )
                log(u'Revisó cuenta bancaria: %s  - %s' % (persona, solicitud), request, "edit")
                messages.success(request, 'Se guardo correctamente.')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s"%(ex.__str__())})

        elif action == 'verificar_cuentas_validadas':
            try:
                if datetime.strptime(request.POST['desde'], '%d-%m-%Y') <= datetime.strptime(request.POST['hasta'], '%d-%m-%Y'):
                    desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)
                    if 'bp' in request.POST and request.POST['bp'] and int(request.POST['bp']) > 0:
                        becaperiodos = BecaPeriodo.objects.filter(periodo_id=int(request.POST['bp']), status=True)
                    else:
                        becaperiodos = BecaPeriodo.objects.filter(status=True)

                    if Persona.objects.filter(cuentabancariapersona__status=True,
                                              cuentabancariapersona__archivo__isnull=False,
                                              inscripcion__becasolicitud__periodo_id__in=becaperiodos.values_list('periodo_id'),
                                              inscripcion__becasolicitud__becaasignacion__status=True,
                                              cuentabancariapersona__fechavalida__range=(desde, hasta),
                                              cuentabancariapersona__archivoesigef=False).exists():
                        if Persona.objects.filter(cuentabancariapersona__status=True,
                                              cuentabancariapersona__archivo__isnull=False,
                                              inscripcion__becasolicitud__periodo_id__in=becaperiodos.values_list('periodo_id'),
                                              inscripcion__becasolicitud__becaasignacion__status=True,
                                              cuentabancariapersona__fechavalida__range=(desde, hasta),
                                              cuentabancariapersona__archivoesigef=False,
                                              cuentabancariapersona__banco__codigo='').exists():
                            return JsonResponse({"result": "bad", "mensaje": "No se puede generar el archivo, existen registros de bancos sin código"})
                        else:
                            return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "No existen cuentas bancarias validadas en el rango de fechas"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "La fecha desde debe ser menor o igual a la fecha hasta"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'verificar_cuentas_validadas_reporte':
            try:
                if datetime.strptime(request.POST['desde'], '%d-%m-%Y') <= datetime.strptime(request.POST['hasta'], '%d-%m-%Y'):
                    desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)
                    if 'bp' in request.POST and request.POST['bp'] and int(request.POST['bp']) > 0:
                        becaperiodos = BecaPeriodo.objects.filter(periodo_id=int(request.POST['bp']), status=True)
                    else:
                        becaperiodos = BecaPeriodo.objects.filter(status=True)
                    if Persona.objects.filter(cuentabancariapersona__status=True,
                                              cuentabancariapersona__archivo__isnull=False,
                                              inscripcion__becasolicitud__periodo_id__in=becaperiodos.values_list('periodo_id'),
                                              inscripcion__becasolicitud__becaasignacion__status=True,
                                              cuentabancariapersona__fechavalida__range=(desde, hasta)
                                              ).exists():
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "No existen cuentas bancarias validadas en el rango de fechas"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "La fecha desde debe ser menor o igual a la fecha hasta"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'verificar_cuentas_rechazadas':
            try:
                if 'bp' in request.POST and request.POST['bp'] and int(request.POST['bp']) > 0:
                    becaperiodos = BecaPeriodo.objects.filter(periodo_id=int(request.POST['bp']), status=True)
                else:
                    becaperiodos = BecaPeriodo.objects.filter(status=True)
                if Persona.objects.filter(cuentabancariapersona__status=True,
                                       cuentabancariapersona__archivo__isnull=False,
                                       inscripcion__becasolicitud__periodo_id__in=becaperiodos.values_list('periodo_id'),
                                       inscripcion__becasolicitud__becaasignacion__status=True,
                                       cuentabancariapersona__estadorevision=3).exists():
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "No existen cuentas bancarias rechazadas para generar el reporte"})

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'verificar_cuentas_pendientes_revisar':
            try:
                if 'bp' in request.POST and request.POST['bp'] and int(request.POST['bp']) > 0:
                    becaperiodos = BecaPeriodo.objects.filter(periodo_id=int(request.POST['bp']), status=True)
                else:
                    becaperiodos = BecaPeriodo.objects.filter(status=True)
                if Persona.objects.filter(cuentabancariapersona__status=True,
                                       cuentabancariapersona__archivo__isnull=False,
                                       inscripcion__becasolicitud__periodo_id__in=becaperiodos.values_list('periodo_id'),
                                       inscripcion__becasolicitud__becaasignacion__status=True,
                                       cuentabancariapersona__estadorevision=1).exists():
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "No existen cuentas bancarias pendientes de revisar para generar el reporte"})

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'validarcuenta':
                try:
                    data['title'] = u'Revisar/Validar Cuenta Bancaria de Beneficiario'
                    data['idb'] = int(request.GET['idb'])
                    cuentabancaria = CuentaBancariaPersona.objects.get(pk=int(request.GET['idb']))
                    beneficiario = cuentabancaria.persona
                    data['beneficiario'] = beneficiario
                    data['cuentabancaria'] = cuentabancaria
                    data['ed'] = request.GET['ed']
                    data['bp'] = request.GET['bp']
                    data['bancos'] = Banco.objects.filter(status=True).order_by('nombre')

                    if cuentabancaria.personarevisa:
                        # if cuentabancaria.personarevisa != persona and cuentabancaria.estadorevision != 1:
                        #     return JsonResponse({"result": "bad", "mensaje": "La cuenta está siendo revisada por otro usuario."})
                        # else:
                        if cuentabancaria.estadorevision != 2 and cuentabancaria.estadorevision != 3:
                            cuentabancaria.personarevisa = persona
                            cuentabancaria.estadorevision = 5
                    else:
                        cuentabancaria.personarevisa = persona
                        cuentabancaria.estadorevision = 5

                    cuentabancaria.save(request)

                    if cuentabancaria.estadorevision in [2, 3]:
                        data['permite_modificar'] = False
                    else:
                        data['permite_modificar'] = True

                    template = get_template("rec_cuentabeneficiario/validarcuenta.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'generarbeneficiarioscsv':
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
                        ws.write(row_num, 14, cuentabeneficiario.observacion if cuentabeneficiario else '', fuentenormal)

                    wb.save(response)
                    return response
                except Exception as ex:
                    print("Error...")
                    pass

            elif action == 'beneficiarioscuentasvalidadas':
                try:
                    __author__ = 'Unemi'

                    desde = datetime.combine(convertir_fecha(request.GET['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.GET['hasta']), time.max)
                    if 'bp' in request.POST and request.POST['bp'] and int(request.POST['bp']) > 0:
                        becaperiodos = BecaPeriodo.objects.filter(periodo_id=int(request.POST['bp']), status=True)
                    else:
                        becaperiodos = BecaPeriodo.objects.filter(status=True)

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
                    response['Content-Disposition'] = 'attachment; filename=cuentas_validadas_' + random.randint(1,10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 15, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 15, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', titulo2)
                    ws.write_merge(2, 2, 0, 15, 'LISTADO DE BENEFICIARIOS CON CUENTAS VALIDADAS', titulo2)

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
                                       inscripcion__becasolicitud__periodo_id__in=becaperiodos.values_list('periodo_id'),
                                       inscripcion__becasolicitud__becaasignacion__status=True,
                                       cuentabancariapersona__estadorevision=2,
                                       cuentabancariapersona__fechavalida__range=(desde, hasta)).distinct().order_by('apellido1', 'apellido2', 'nombres')

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

                    if 'bp' in request.POST and request.POST['bp'] and int(request.POST['bp']) > 0:
                        becaperiodos = BecaPeriodo.objects.filter(periodo_id=int(request.POST['bp']), status=True)
                    else:
                        becaperiodos = BecaPeriodo.objects.filter(status=True)

                    beneficiarios = Persona.objects.filter(cuentabancariapersona__status=True,
                                       cuentabancariapersona__archivo__isnull=False,
                                       inscripcion__becasolicitud__periodo_id__in=becaperiodos.values_list('periodo_id'),
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

            elif action == 'bancos':
                try:
                    data['title'] = u'Bancos'
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), f'&action={action}'
                    if search:
                        data['s'] = search
                        url_vars += f'&s={search}'
                        filtro = filtro & (Q(nombre__icontains=search) | \
                                            Q(codigo__icontains=search) | \
                                            Q(codigo_tthh__icontains=search))
                    listado = Banco.objects.filter(filtro).order_by('fecha_creacion')
                    paging = MiPaginador(listado, 10)
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
                    data["url_vars"] = url_vars
                    data['listado'] = page.object_list
                    data['totcount'] = listado.count()
                    return render(request, 'rec_cuentabeneficiario/bancos.html', data)
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'addbanco':
                try:
                    form = BancoForm()
                    data['form'] = form
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editbanco':
                try:
                    instancia = Banco.objects.get(id=encrypt_id(request.GET['id']))
                    form = BancoForm(initial=model_to_dict(instancia))
                    data['id'] = instancia.id
                    data['form'] = form
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Cuentas Bancarias de Beneficiarios'
                search = None
                ids = None
                becaperiodos = BecaPeriodo.objects.filter(status=True).order_by('periodo__inicio')
                becaperiodo = None

                if becaperiodos.filter(vigente=True).exists():
                    becaperiodo = becaperiodos.filter(vigente=True).first()
                else:
                    becaperiodo = becaperiodos.all().order_by('periodo__inicio').first()

                if 'bp' in request.GET:
                    bp = int(request.GET['bp'])
                    if bp > 0:
                        if becaperiodos.filter(periodo_id=bp).exists():
                            becaperiodo = becaperiodos.filter(periodo_id=bp).first()

                becasolicitud = BecaSolicitud.objects.filter(status=True, periodo=becaperiodo.periodo,
                                                                inscripcion__persona__cuentabancariapersona__status=True,
                                                                 inscripcion__persona__cuentabancariapersona__archivo__isnull=False,
                                                                 ).exclude(Q(becaaceptada=3) | Q(estado=3)).values_list('inscripcion__persona_id', flat=True).distinct()
                cuentast = cuentas = CuentaBancariaPersona.objects.filter(status=True,
                                                                          activapago=True,
                                                                          persona_id__in=becasolicitud,
                                                                          # persona__inscripcion__becasolicitud__becaaceptada=2,
                                                                          persona__personadocumentopersonal__estadocedula=2,
                                                                          persona__personadocumentopersonal__cedula__isnull=False,
                                                                          ).distinct().order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
                # beneficiariost = beneficiarios = Persona.objects.filter(pk__in=becaasignaciones.values_list('solicitud__inscripcion__persona_id', flat=True).distinct(), cuentabancariapersona__status=True).order_by('apellido1', 'apellido2', 'nombres').distinct()



                # cuentas = cuentas.filter(persona__inscripcion__becasolicitud__periodo=becaperiodo.periodo, persona__inscripcion__becasolicitud__becaaceptada=2).distinct()
                # cuentas = cuentas.filter(persona__inscripcion__becasolicitud__periodo=becaperiodo.periodo).distinct()
                # cuentast = cuentast.filter(persona__inscripcion__becasolicitud__periodo=becaperiodo.periodo).distinct()

                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        cuentas = cuentas.filter(Q(persona__nombres__icontains=search) | Q(persona__apellido1__icontains=search) | Q(persona__apellido2__icontains=search) | Q(persona__cedula__icontains=search) | Q(persona__ruc__icontains=search) | Q(persona__pasaporte__icontains=search))
                        if search.isdigit():
                            cuentas = cuentas.filter(Q(persona__nombres__icontains=search) | Q(persona__apellido1__icontains=search) | Q(persona__apellido2__icontains=search) | Q(persona__cedula__icontains=search) | Q(persona__ruc__icontains=search) | Q(persona__pasaporte__icontains=search) | Q(numero=search) | Q(pk=search))
                    else:
                        cuentas = cuentas.filter(Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1]))
                if 'id' in request.GET:
                    ids = request.GET['id']
                    cuentas = cuentas.filter(id=ids)

                ed = 0
                if 'ed' in request.GET:
                    ed = int(request.GET['ed'])
                    if ed > 0:
                        cuentas = cuentas.filter(estadorevision=ed)


                paging = MiPaginador(cuentas, 25)
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
                data['puede_revisar_validar_cuentabancaria'] = puede_revisar_validar_cuentabancaria = becaperiodo.puede_revisar_validar_cuentabancaria()
                request.session['paginador'] = p
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['beneficiarios'] = page.object_list
                data['totalcuentas'] = total = cuentast.count()
                data['totalaprobadas'] = aprobadas = cuentast.filter(estadorevision=2).count()
                data['totalrechazadas'] = rechazadas = cuentast.filter(estadorevision=3).count()
                data['totalrevision'] = revision = cuentast.filter(estadorevision=5).count()
                data['totalpendiente'] = pendiente = cuentast.filter(estadorevision=1).count()
                data['ed'] = ed
                data['becaperiodos'] = becaperiodos
                data['becaperiodo'] = becaperiodo
                data['fechaactual'] = datetime.now().strftime('%d-%m-%Y')
                return render(request, "rec_cuentabeneficiario/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect("/?info=%s" % ex.__str__())
