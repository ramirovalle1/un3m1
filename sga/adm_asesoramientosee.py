# -*- coding: UTF-8 -*-
from   datetime import datetime

from django.contrib import messages
import random
import xlwt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.template.loader import get_template
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from xlwt import *
from settings import EMAIL_DOMAIN
from sga.forms import AsesoramientoSEEValidacionForm, SubirAnexoAsesoramientoSeeForm
from sga.models import AsesoramientoSEE, AsesoramientoSEETipoTrabajo, ESTADOS_SOLICITUD_ASESORAMIENTOSEE, miinstitucion, \
    Persona, Carrera, CUENTAS_CORREOS
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, puede_realizar_accion, generar_nombre
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.tasks import send_html_mail
from decorators import secure_module, last_access

@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'cambiarestado':
            try:
                form = AsesoramientoSEEValidacionForm(request.POST)
                if not form.is_valid():
                    # [(k, v[0]) for k, v in f.errors.items()]
                    for k, v in form.errors.items():
                        raise NameError(f'{k}:{v[0]}')
                funcionarioasesortecnico = None
                if int(request.POST['funcionarioasesortecnico']) > 0:
                    funcionarioasesortecnico = Persona.objects.get(pk=int(request.POST['funcionarioasesortecnico']))
                asesoramiento = AsesoramientoSEE.objects.get(pk=int(request.POST['id']))
                asesoramiento.estado = form.cleaned_data['estado']
                asesoramiento.horaculminacion = form.cleaned_data['horaculminacion']
                asesoramiento.funcionarioasesortecnico = funcionarioasesortecnico
                asesoramiento.observacion = form.cleaned_data.get('observacion','').strip().upper()
                asesoramiento.save(request)
                log(u'Cambio estado en registro de solicitud de servicios de estudios estadisticos: %s' % asesoramiento, request, "edit")
                cuenta = CUENTAS_CORREOS[0][1]
                estado_p = ''
                if(asesoramiento.estado == '2'):
                    estado_p = 'APROBADO'
                elif(asesoramiento.estado == '4'):
                    estado_p = 'RECHAZADO'
                elif(asesoramiento.estado == '3'):
                    estado_p = 'FINALIZADO'
                correos = asesoramiento.persona.lista_emails_envio()
                send_html_mail("Asesoría de Servicios del Centro de Estudios Estadísticos Informa!", "adm_asesoramientosee/emails/asesoramientoemail.html",
                                   {'sistema': request.session['nombresistema'], 'registro': asesoramiento,'palabra_estado':estado_p,
                                    't': miinstitucion(), 'dominio': EMAIL_DOMAIN}, correos, [],cuenta=CUENTAS_CORREOS[0][1])
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        if action == 'delete':
            try:
                asesoramiento = AsesoramientoSEE.objects.get(pk=request.POST['id'])
                asesoramiento.status = False
                asesoramiento.save(request)
                log(u'Eliminó Asesoramiento de Estudio Estadisticos: %s' % asesoramiento, request, "del")
                return JsonResponse({"result": "ok", 'mensaje': u'Registro eliminado correctamente.'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'uploadanexo':
            try:
                form = SubirAnexoAsesoramientoSeeForm(request.POST, request.FILES)
                if not form.is_valid():
                    # [(k, v[0]) for k, v in f.errors.items()]
                    for k, v in form.errors.items():
                        raise NameError(f'{k}:{v[0]}')
                asesoramiento = AsesoramientoSEE.objects.get(pk=request.POST['id'])
                newfile = None
                newfile = request.FILES['archivoanexo']
                newfile._name = generar_nombre(f"anexoasesoramiento_{asesoramiento.id}_{asesoramiento.persona}", newfile._name)
                asesoramiento.archivoanexo = newfile
                asesoramiento.save(request)
                log(u'Cargo Anexo Asesoramiento de Estudio Estadisticos: %s' % asesoramiento, request, "edit")
                messages.success(request, u'Cargo correctamente. el anexo %s' % (asesoramiento))
                return JsonResponse({"result": "ok", 'mensaje': u'Cargo correctamente. el anexo %s' % (asesoramiento)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % str(ex)})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'datos':
                try:
                    asesoramiento = AsesoramientoSEE.objects.get(pk=int(request.GET['id']))
                    data['asesoramiento'] = asesoramiento
                    data['horacuminaciontemp'] = asesoramiento.horaculminacion
                    hora_culmi = asesoramiento.horaculminacion if asesoramiento.horaculminacion else str(datetime.now().time().strftime('%H:%M'))
                    funcionarioasesortecnico = asesoramiento.funcionarioasesortecnico.id if asesoramiento.funcionarioasesortecnico else 0
                    form = AsesoramientoSEEValidacionForm(initial={'estado': asesoramiento.estado,
                                                                   'observacion': asesoramiento.observacion,
                                                                   'horaculminacion': hora_culmi,
                                                                   'funcionarioasesortecnico': funcionarioasesortecnico})
                    form.editar()
                    form.fields['estado'].choices = (
                                    ('', u'--Seleccione--'),
                                    (2, u'APROBADO'),
                                    (4, u'RECHAZADO'),
                                    (3, u'FINALIZADO'),
                    )
                    data['form'] = form
                    template = get_template("adm_asesoramientosee/datos.html")
                    return JsonResponse({"result": True, 'datos': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': u'Error al obtener los datos'})

            if action == 'excel_rango_fecha':
                try:

                    fechainicio = request.GET['fechainicio']
                    fechafin = request.GET['fechafin']
                    fechai = datetime.strptime(f'{fechainicio}', '%d-%m-%Y')
                    fechaf = datetime.strptime(f'{fechafin}', '%d-%m-%Y')

                    asesoramientos = AsesoramientoSEE.objects.filter(status=True, fecha_creacion__range=[fechai, fechaf]) #periodo=periodo,
                    __author__ = 'Unemi'

                    title = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')

                    fuentecabecera = easyxf(
                        'font: name Calibri, color-index black, bold on, height 200; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Calibri, color-index black, height 200; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('RegistrosAsesoramientoSEE')
                    ws.write_merge(0, 0, 0, 15, f'SOLICITUDES DE ASESORAMIENTO SERVICIOS DE ESTUDIOS ESTADÍSTICOSDES \n DESDE {fechainicio} HASTA {fechafin}', title)

                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = f'attachment; filename=listado_asesoramiento_see_{fechainicio}_{fechafin}_' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"DOCENTE", 10000),
                        (u"CEDULA", 3000),
                        (u"TELEFONO", 3000),
                        (u"CORREO", 10000),
                        (u"TÍTULO TERCER NIVEL", 25000),
                        (u"TÍTULO CUARTO NIVEL", 25000),
                        (u"DOCTORADO", 3000),
                        (u"TÍTULO", 17000),
                        (u"TIPO TRABAJO", 8000),
                        (u"DESCRIPCIÓN", 25000),
                        (u"ESTADO", 3000),
                        (u"OBSERVACIÓN", 17000),
                        (u"FUNCIONARIO ASESOR TÉCNICO", 10000),
                        (u"FECHA ATENCIÓN", 5000),
                        (u"HORA ATENCIÓN", 5000),
                        (u"HORA CULMINACIÓN", 5000),
                    ]
                    row_num = 4
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'

                    listado = asesoramientos.order_by('fecha_creacion')
                    row_num = 5
                    i = 0
                    for lista in listado:
                        campo1 = lista.persona.__str__()
                        campo2 = lista.persona.cedula
                        campo3 = lista.persona.telefono
                        campo4 = lista.persona.emailinst
                        campo5 = lista.persona.titulo_3er_nivel().__str__() if lista.persona.titulo_3er_nivel() else ''
                        campo6 = lista.persona.titulo_4to_nivel().__str__() if lista.persona.titulo_4to_nivel() else ''
                        campo7 = 'SI' if lista.persona.tiene_titulo_doctorado_phd() else 'NO'
                        campo8 = lista.titulo
                        campo9 = lista.tipotrabajo.__str__() if lista.tipotrabajo else 'SIN TIPO'
                        campo10 = lista.descripcion
                        campo11 = lista.get_estado_display()
                        campo12 = lista.observacion
                        campo13 = lista.funcionarioasesortecnico.__str__() if lista.funcionarioasesortecnico else ''
                        campo14 = lista.fechaatencion.strftime('%d-%m-%Y') if lista.fechaatencion else ''
                        campo15 = lista.horaatencion.strftime('%H:%M:%S %p') if lista.horaatencion else ''
                        campo16 = lista.horaculminacion.strftime('%H:%M:%S %p') if lista.horaculminacion else ''
                        ws.write(row_num, 0, campo1, fuentenormal)
                        ws.write(row_num, 1, campo2, fuentenormal)
                        ws.write(row_num, 2, campo3, fuentenormal)
                        ws.write(row_num, 3, campo4, fuentenormal)
                        ws.write(row_num, 4, campo5, fuentenormal)
                        ws.write(row_num, 5, campo6, fuentenormal)
                        ws.write(row_num, 6, campo7, fuentenormal)
                        ws.write(row_num, 7, campo8, fuentenormal)
                        ws.write(row_num, 8, campo9, fuentenormal)
                        ws.write(row_num, 9, campo10, fuentenormal)
                        ws.write(row_num, 10, campo11, fuentenormal)
                        ws.write(row_num, 11, campo12, fuentenormal)
                        ws.write(row_num, 12, campo13, fuentenormal)
                        ws.write(row_num, 13, campo14, fuentenormal)
                        ws.write(row_num, 14, campo15, fuentenormal)
                        ws.write(row_num, 15, campo16, fuentenormal)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass


            if action == 'downloadactaasesoramiento':
                try:
                    data['asesoramiento'] = asesoramiento = AsesoramientoSEE.objects.get(pk=int(request.GET['id']))
                    data['fechaactual'] = datetime.now()

                    return conviert_html_to_pdf('adm_asesoramientosee/pdf/acta_asesoramiento_pdf.html',
                                                {
                                                    'pagesize': 'A4',
                                                    'data': data,

                                                }
                                                )
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': u'Error al obtener los datos'})
            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = 'Administración Solicitudes Asesoramiento de Servicios de Estudios Estadísticos'
                search = None
                ids = None
                asesoramientos = None
                data['tipos'] = tipos = AsesoramientoSEETipoTrabajo.objects.filter(status=True)
                asesoramientos = AsesoramientoSEE.objects.filter(status=True)#periodo=periodo
                if 's' in request.GET:
                    search = request.GET['s']
                    asesoramientos = asesoramientos.filter(
                        Q(titulo__icontains=search) |
                        Q(persona__nombres__icontains=search) |
                        Q(persona__apellido1__icontains=search) |
                        Q(persona__apellido2__icontains=search)|
                        Q(persona__cedula__icontains=search)
                    )

                elif 'id' in request.GET:
                    ids = request.GET['id']
                    asesoramientos = asesoramientos.objects.filter(id=ids)

                estado = 0
                if 'est' in request.GET and int(request.GET['est']) > 0:
                    estado = int(request.GET['est'])
                    asesoramientos = asesoramientos.filter(estado=estado)

                tipo = 0
                if 't' in request.GET and int(request.GET['t']) > 0:
                    tipo = int(request.GET['t'])
                    asesoramientos = asesoramientos.filter(tipotrabajo_id=tipo)

                paging = MiPaginador(asesoramientos, 20)
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

                data['asesocarreras'] = Carrera.objects.filter(id__in=asesoramientos.values_list('carrera_id', flat=True).distinct())
                request.session['paginador'] = p
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['estados'] = ESTADOS_SOLICITUD_ASESORAMIENTOSEE
                data['estado'] = estado
                data['tipo'] = tipo
                data['totalsolicitados'] = asesoramientos.filter(estado=1).count()
                data['totalaprobados'] = asesoramientos.filter(estado=2).count()
                data['totalanulados'] = asesoramientos.filter(estado=3).count()
                data['totalrechazados'] = asesoramientos.filter(estado=4).count()
                data['asesoramientos'] = page.object_list
                data['formanexo'] = SubirAnexoAsesoramientoSeeForm()
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                data['ip_privada'] = s.getsockname()[0]
                data['objeto_ip'] = s.getsockname()

                if 'export_to_excel' in request.GET:
                    __author__ = 'Unemi'

                    title = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')

                    fuentecabecera = easyxf(
                        'font: name Calibri, color-index black, bold on, height 200; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Calibri, color-index black, height 200; borders: left thin, right thin, top thin, bottom thin')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('RegistrosAsesoramientoSEE')
                    ws.write_merge(0, 0, 0, 15, 'SOLICITUDES DE ASESORAMIENTO SERVICIOS DE ESTUDIOS ESTADÍSTICOS', title)

                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=listado_asesoramiento_see' + random.randint(
                        1, 10000).__str__() + '.xls'

                    columns = [
                        (u"DOCENTE", 10000),
                        (u"CEDULA", 3000),
                        (u"TELEFONO", 3000),
                        (u"CORREO", 10000),
                        (u"TÍTULO TERCER NIVEL", 25000),
                        (u"TÍTULO CUARTO NIVEL", 25000),
                        (u"DOCTORADO", 3000),
                        (u"TÍTULO", 17000),
                        (u"TIPO TRABAJO", 8000),
                        (u"DESCRIPCIÓN", 25000),
                        (u"ESTADO", 3000),
                        (u"OBSERVACIÓN", 17000),
                        (u"FUNCIONARIO ASESOR TÉCNICO", 10000),
                        (u"FECHA ATENCIÓN", 5000),
                        (u"HORA ATENCIÓN", 5000),
                        (u"HORA CULMINACIÓN", 5000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'

                    listado = asesoramientos.order_by('fecha_creacion')
                    row_num = 4
                    i = 0
                    for lista in listado:
                        campo1 = lista.persona.__str__()
                        campo2 = lista.persona.cedula
                        campo3 = lista.persona.telefono
                        campo4 = lista.persona.emailinst
                        campo5 = lista.persona.titulo_3er_nivel().__str__() if lista.persona.titulo_3er_nivel() else ''
                        campo6 = lista.persona.titulo_4to_nivel().__str__() if lista.persona.titulo_4to_nivel() else ''
                        campo7 = 'SI' if lista.persona.tiene_titulo_doctorado_phd() else 'NO'
                        campo8 = lista.titulo
                        campo9 = lista.tipotrabajo.__str__() if lista.tipotrabajo else 'SIN TIPO'
                        campo10 = lista.descripcion
                        campo11 = lista.get_estado_display()
                        campo12 = lista.observacion
                        campo13 = lista.funcionarioasesortecnico.__str__() if lista.funcionarioasesortecnico else ''
                        campo14 = lista.fechaatencion.strftime('%d-%m-%Y') if lista.fechaatencion else ''
                        campo15 = lista.horaatencion.strftime('%H:%M:%S %p') if lista.horaatencion else ''
                        campo16 = lista.horaculminacion.strftime('%H:%M:%S %p') if lista.horaculminacion else ''
                        ws.write(row_num, 0, campo1, fuentenormal)
                        ws.write(row_num, 1, campo2, fuentenormal)
                        ws.write(row_num, 2, campo3, fuentenormal)
                        ws.write(row_num, 3, campo4, fuentenormal)
                        ws.write(row_num, 4, campo5, fuentenormal)
                        ws.write(row_num, 5, campo6, fuentenormal)
                        ws.write(row_num, 6, campo7, fuentenormal)
                        ws.write(row_num, 7, campo8, fuentenormal)
                        ws.write(row_num, 8, campo9, fuentenormal)
                        ws.write(row_num, 9, campo10, fuentenormal)
                        ws.write(row_num, 10, campo11, fuentenormal)
                        ws.write(row_num, 11, campo12, fuentenormal)
                        ws.write(row_num, 12, campo13, fuentenormal)
                        ws.write(row_num, 13, campo14, fuentenormal)
                        ws.write(row_num, 14, campo15, fuentenormal)
                        ws.write(row_num, 15, campo16, fuentenormal)
                        row_num += 1
                    wb.save(response)
                    return response
                return render(request, "adm_asesoramientosee/view.html", data)
            except Exception as ex:
                pass
