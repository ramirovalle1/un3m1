# -*- coding: UTF-8 -*-
import os
import sys
import threading
import time

import pyqrcode
import xlrd
import random

from PIL import Image
from pdf2image import convert_from_bytes
from xlwt import *
from xlwt import easyxf
import xlwt
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.forms import model_to_dict
from django.template.loader import get_template

from feria.forms import SolicitudFeriaForm
from feria.models import CronogramaFeria, SolicitudFeria, SolicitudFeriaHistorial, ParticipanteFeria
from settings import SITE_STORAGE, DEBUG, SITE_POPPLER
from sga.commonviews import adduserdata
from sga.funciones import puede_realizar_accion, log, elimina_tildes
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdfsaveqrcertificado_generico, conviert_html_to_pdfsaveqrcertificadoferiaparticipacion
from decorators import secure_module, last_access
from django.db import transaction
from django.db.models import Q, F
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render

from sga.models import Carrera, Administrativo, Notificacion, CUENTAS_CORREOS
from sga.templatetags.sga_extras import encrypt
from sga.tasks import send_html_mail

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'loadDataTable':
            try:
                txt_filter = request.POST['sSearch'] if request.POST['sSearch'] else ''
                limit = int(request.POST['iDisplayLength']) if request.POST['iDisplayLength'] else 25
                offset = int(request.POST['iDisplayStart']) if request.POST['iDisplayStart'] else 0
                carreras = int(request.POST['carreras']) if request.POST['carreras'] else 0
                tCount = 0
                solicitudes = SolicitudFeria.objects.filter(cronograma_id=int(encrypt(request.POST['id'])), status=True)
                if txt_filter:
                    search = txt_filter.strip()
                    solicitudes = solicitudes.filter(Q(titulo__icontains=search))
                if carreras > 0:
                    solicitudes = solicitudes.filter(Q(participanteferia__matricula__inscripcion__carrera_id=carreras, participanteferia__matricula__inscripcion__persona__usuario_id=F('usuario_creacion_id'))).distinct()
                tCount = solicitudes.count()
                if offset == 0:
                    rows = solicitudes[offset:limit]
                else:
                    rows = solicitudes[offset:offset + limit]
                aaData = []
                for row in rows:
                    modulosgrupos = []
                    solicitante = row.usuario_creacion.persona_set.first()
                    participante=ParticipanteFeria.objects.filter(status=True,solicitud=row, matricula__inscripcion__persona__usuario=row.usuario_creacion)
                    carrera = "SIN CARRERA"
                    if participante.exists():
                        carrera = participante.first().matricula.inscripcion.carrera.__str__()
                    aaData.append([row.titulo,
                                   row.resumen,
                                   {
                                       "estado": row.estado,
                                       "estado_display": row.get_estado_display(),
                                   },
                                   {"id": row.id,
                                    "id_enc": encrypt(row.id),
                                    "name": row.titulo,
                                    "tutor": {
                                        'name': row.tutor.__str__(),
                                        'foto': row.tutor.persona.get_foto(),
                                    },
                                    "solicitante": {
                                        'name': solicitante.__str__(),
                                        'foto': solicitante.get_foto(),
                                        'carrera': carrera,
                                        'correo': solicitante.emailinst,
                                        'celular': solicitante.telefono
                                    },
                                    "ganador": row.es_ganador,
                                    "puesto": row.puesto,
                                    "resumen": row.resumen,
                                    "propuesta": row.docpresentacionpropuesta.url if row.docpresentacionpropuesta else None,
                                    "ganadorfacultad": row.es_ganadorfacultad
                                    },
                                   ])
                return JsonResponse({"result": "ok", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        if action == 'changeStatusRequest':
            try:
                id = int(encrypt(request.POST['id'])) if 'id' in request.POST and request.POST['id'] and int(encrypt(request.POST['id'])) != 0 else None
                estado = request.POST['estado']
                observacion = request.POST['observacion']
                eSolicitudFeria = SolicitudFeria.objects.filter(pk=id, status=True).first()
                if eSolicitudFeria is None:
                    raise NameError('Parametro  no encrontro el cronograma')
                eSolicitudFeria.estado = estado
                eSolicitudFeria.save(request)
                for participante in eSolicitudFeria.participanteferia_set.filter(status=True):
                    tituloemail = "Estado Solicitud - Feria FACI"

                    send_html_mail(tituloemail,
                                   "emails/feria_cambio_estado_solicitud.html",
                                   {'sistema': u'SGA',
                                    'saludo': 'Estimada' if participante.inscripcion.persona.sexo.id == 1 else 'Estimado',
                                    'solicitud': eSolicitudFeria,
                                    'participante':participante
                                    },
                                   participante.inscripcion.persona.lista_emails_envio_2(),
                                   # ['isaltosm@unemi.edu.ec'],
                                   [],
                                   cuenta=CUENTAS_CORREOS[0][1]
                                   )

                eSolicitudFeriaHistorial = SolicitudFeriaHistorial(solicitud=eSolicitudFeria,
                                                                   observacion=observacion,
                                                                   estado=eSolicitudFeria.estado)
                eSolicitudFeriaHistorial.save(request)
                return JsonResponse({"result": "ok", "mensaje": u"Se cambio correctamente el estado de la solicitud"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

        if action == 'declareWinner':
            try:
                id = int(encrypt(request.POST['id'])) if 'id' in request.POST and request.POST['id'] and int(encrypt(request.POST['id'])) != 0 else None
                puesto = request.POST['puesto']
                eSolicitudFeria = SolicitudFeria.objects.filter(pk=id).first()
                eParticipante = eSolicitudFeria.participanteferia_set.filter(status=True).first()
                if eParticipante is not None:
                    eCarrera = eParticipante.matricula.inscripcion.carrera
                    if SolicitudFeria.objects.filter(participanteferia__matricula__inscripcion__carrera=eCarrera, participanteferia__matricula__inscripcion__persona__usuario_id=F('usuario_creacion_id'), status=True, es_ganador=True, cronograma_id=eSolicitudFeria.cronograma.id).distinct().exists():
                        raise NameError('Solo puede haber un ganador por Carrera')
                if eSolicitudFeria is None:
                    raise NameError('Parametro  no encrontro el cronograma')
                if eSolicitudFeria.estado !=2:
                    raise NameError('Proyecto feria debe estar en estado Aprobado')
                eSolicitudFeria.es_ganador = True
                eSolicitudFeria.puesto = puesto
                eSolicitudFeria.save(request)
                eSolicitudFeriaHistorial = SolicitudFeriaHistorial(solicitud=eSolicitudFeria,
                                                                   observacion=f'Declarado ganador en el puesto {puesto}',
                                                                   es_ganador=eSolicitudFeria.es_ganador,
                                                                   puesto=eSolicitudFeria.puesto,
                                                                   estado=eSolicitudFeria.estado)
                eSolicitudFeriaHistorial.save(request)
                eParticipantes = eSolicitudFeria.participanteferia_set.filter(status=True)
                errores_certificados = generateCertificatesWinners(request, eParticipantes)
                if len(errores_certificados) > 0:
                    raise u"Fallo declaracioón del proyecto No se generaron los siguientes certificados de ganadores:%s" % ('\n'.join(errores_certificados))
                log(u'Declaro ganador como ganador a %s en el puesto %s' % (eSolicitudFeria.titulo, eSolicitudFeria.puesto), request, "edit")
                return JsonResponse({"result": "ok", "mensaje": u"Se declaro correctamente como ganador al proyecto %s"%(eSolicitudFeria.titulo)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

        if action == 'declareWinnerFaculty':
            try:
                id = int(encrypt(request.POST['id'])) if 'id' in request.POST and request.POST['id'] and int(encrypt(request.POST['id'])) != 0 else None
                eSolicitudFeria = SolicitudFeria.objects.filter(pk=id).first()
                eSolicitudes = SolicitudFeria.objects.filter(status=True, cronograma=eSolicitudFeria.cronograma, es_ganadorfacultad=2).first()
                if eSolicitudes is not None:
                    raise NameError('Solo puede haber un ganador de la facultad')
                if eSolicitudFeria is None:
                    raise NameError('Parametro  no encrontro el cronograma')
                if eSolicitudFeria.estado !=2:
                    raise NameError('Proyecto feria debe estar en estado Aprobado')
                eSolicitudFeria.es_ganadorfacultad = 2
                eSolicitudFeria.save(request)
                eSolicitudFeriaHistorial = SolicitudFeriaHistorial(solicitud=eSolicitudFeria,
                                                                   observacion=f'Declarado ganador facultad',
                                                                   es_ganadorfacultad=eSolicitudFeria.es_ganadorfacultad,
                                                                   estado=eSolicitudFeria.estado)
                eSolicitudFeriaHistorial.save(request)
                eParticipantes = eSolicitudFeria.participanteferia_set.filter(status=True)
                errores_certificados = generateCertificatesWinnersFaculty(request, eParticipantes)
                if len(errores_certificados) > 0:
                    raise u"No se generaron los siguientes certificados de ganadores:%s" % ('\n'.join(errores_certificados))
                log(u'Declaró como ganador de la facultad a %s' % eSolicitudFeria.titulo, request, "edit")
                return JsonResponse({"result": "ok", "mensaje": u"Se declaró correctamente como ganador de la facultad al proyecto %s"%(eSolicitudFeria.titulo)})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

        if action == 'removeWinner':
            try:
                id = int(encrypt(request.POST['id'])) if 'id' in request.POST and request.POST['id'] and int(encrypt(request.POST['id'])) != 0 else None
                eSolicitudFeria = SolicitudFeria.objects.filter(pk=id).first()
                if eSolicitudFeria is None:
                    raise NameError('Parametro no encrontro la solicitud')
                eSolicitudFeria.es_ganador = False
                puesto = eSolicitudFeria.puesto
                eSolicitudFeria.puesto = None
                eSolicitudFeria.save(request)

                eSolicitudFeriaHistorial = SolicitudFeriaHistorial(solicitud=eSolicitudFeria,
                                                                   observacion=f'Removio ganador con en el puesto {puesto}',
                                                                   es_ganador=eSolicitudFeria.es_ganador,
                                                                   puesto=puesto,
                                                                   estado=eSolicitudFeria.estado)
                eSolicitudFeriaHistorial.save(request)
                #Remover certificados ganadores aparticipante
                eSolicitudFeria.participanteferia_set.filter(status=True).update(certificadoganador=None)
                log(u'Removió ganador como ganador a %s que ocupo el puesto %s' % (eSolicitudFeria.titulo, puesto), request, "edit")
                return JsonResponse({"result": "ok", "mensaje": u"Se removió correctamente de ganador al proyecto %s"%(eSolicitudFeria.titulo)})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

        if action == 'removeWinnerFaculty':
            try:
                id = int(encrypt(request.POST['id'])) if 'id' in request.POST and request.POST['id'] and int(encrypt(request.POST['id'])) != 0 else None
                eSolicitudFeria = SolicitudFeria.objects.filter(pk=id).first()
                if eSolicitudFeria is None:
                    raise NameError('Parametro no encrontro la solicitud')
                eSolicitudFeria.es_ganadorfacultad = 1
                eSolicitudFeria.save(request)

                eSolicitudFeriaHistorial = SolicitudFeriaHistorial(solicitud=eSolicitudFeria,
                                                                   observacion=f'Removio ganador de la facultad',
                                                                   es_ganadorfacultad=eSolicitudFeria.es_ganadorfacultad,
                                                                   estado=eSolicitudFeria.estado)
                eSolicitudFeriaHistorial.save(request)
                #Remover certificados ganadores aparticipante
                eSolicitudFeria.participanteferia_set.filter(status=True).update(certificadoganadorfacultad=None)
                log(u'Removió como ganador de la facultad a %s' % eSolicitudFeria.titulo, request, "edit")
                return JsonResponse({"result": "ok", "mensaje": u"Se removió correctamente de ganador  de la facultad al proyecto %s"%(eSolicitudFeria.titulo)})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

        if action == 'changeWinner':
            try:
                id = int(encrypt(request.POST['id'])) if 'id' in request.POST and request.POST['id'] and int(encrypt(request.POST['id'])) != 0 else None
                estado = request.POST['estado']
                observacion = request.POST['observacion']
                eParticipante = ParticipanteFeria.objects.filter(pk=id).first()
                if eParticipante is None:
                    raise NameError('Parametro  no encrontro en Participantes')
                eParticipante.es_ganador = not eParticipante.es_ganador
                eParticipante.observacionganador = observacion
                eParticipante.save(request)
                return JsonResponse({"result": "ok", "es_ganador":eParticipante.es_ganador, "mensaje": u"Se cambio correctamente el estado Ganadador"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

        if action == 'generateCertificatesParticipants':
            try:
                GenerateBackground(request=request, data=data).start()
                return JsonResponse({"result": "ok", "mensaje": u"Se ha procedido a ejecutar el proceso de generación de certificados de participación, en cuanto este se procedera a notificar"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error %s" % ex.__str__()})

        if action == 'generateCertificateParticipant':
            try:
                id = encrypt(request.POST.get('id'))
                eParticipante = ParticipanteFeria.objects.get(id=id)
                eInscripcion = eParticipante.inscripcion
                eUsuario = eInscripcion.persona.usuario
                aData = {}
                url_path = 'http://127.0.0.1:8000'
                if not DEBUG:
                    url_path = 'https://sga.unemi.edu.ec'

                aData['rector'] = rector = Administrativo.objects.get(pk=225)
                aData['rectorfirma'] = rectorfirma = rector.persona.firmapersona_set.filter(status=True).order_by('-tipofirma').first()
                aData['decano'] = decano = Administrativo.objects.get(pk=415)
                #1458
                aData['decanofirma'] = decanofirma = decano.persona.firmapersona_set.filter(status=True).order_by('-tipofirma').first()
                aData['url_path'] = url_path
                aData['eParticipante'] = eParticipante
                aData['hoy'] = hoy = datetime.now().date()
                username = elimina_tildes(eUsuario.username)
                qrname = f'feria_qr_certificadoparticipacion_{eInscripcion.id}{eParticipante.solicitud.id}{eParticipante.id}'
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'feria', 'certificados', 'participantes', username, 'participacion', ''))
                folder2 = os.path.join(os.path.join(SITE_STORAGE, 'media', 'feria', 'certificados', 'participantes', username, 'qrcode', ''))
                os.makedirs(folder, exist_ok=True)
                os.makedirs(folder2, exist_ok=True)
                foldersave = f'feria/certificados/participantes/{username}/participacion/{qrname}.pdf'

                rutapdf = folder + qrname + '.pdf'
                aData['url_qr'] = rutaimg = folder2 + qrname + '.png'
                aData['version'] = datetime.now().strftime('%Y%m%d_%H%M%S')
                if os.path.isfile(rutapdf):
                    os.remove(rutapdf)
                elif os.path.isfile(rutaimg):
                    os.remove(rutaimg)
                url = pyqrcode.create(f'{url_path}/media/feria/certificados/participantes/{username}/participacion/{qrname}.pdf')
                aData['image_qrcode'] = f'{url_path}/media/feria/certificados/participantes/{username}/qrcode/{qrname}.png'
                imageqr = url.png(rutaimg, 16, '#000000')
                valida, pdf, result = conviert_html_to_pdfsaveqrcertificadoferiaparticipacion(
                    request,
                    'adm_feria/utileria/3feria_certificado_participante.html',
                    {'pagesize': 'A4', 'data': aData}, folder, qrname + '.pdf'
                )
                if not valida:
                    raise NameError('Error al generar Certificado')
                eParticipante.certificado = foldersave
                eParticipante.save(request)
                return JsonResponse({"result": "ok", "mensaje": u"Se genero correctamente el Certificado", "id": encrypt(eParticipante.solicitud.id)})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error %s" % ex.__str__()})

        if action == 'generateCertificatesWinners':
            try:
                idc = int(encrypt(request.POST['idc'])) if 'idc' in request.POST and request.POST['idc'] and int(encrypt(request.POST['idc'])) != 0 else None
                eParticipantes = ParticipanteFeria.objects.filter(solicitud__cronograma_id=idc,
                                                                  solicitud__estado=2,
                                                                  solicitud__es_ganador=True,
                                                                  solicitud__status=True,
                                                                  status=True)
                errores_certificados = generateCertificatesWinners(request, eParticipantes)
                if len(errores_certificados) > 0:
                    raise u"No se generaron los siguientes certificados de ganadores:%s" % ('\n'.join(errores_certificados))
                return JsonResponse({"result": "ok", "mensaje": u"Se generaron correctamente todos los certificados"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error  %s" % ex.__str__()})

        # if action == 'generateCertificatesWinnersFaculty':
        #     try:
        #         idc = int(encrypt(request.POST['idc'])) if 'idc' in request.POST and request.POST['idc'] and int(encrypt(request.POST['idc'])) != 0 else None
        #         eParticipantes = ParticipanteFeria.objects.filter(solicitud__cronograma_id=idc,
        #                                                           solicitud__estado=2,
        #                                                           solicitud__es_ganadorfacultad=True,
        #                                                           solicitud__status=True,
        #                                                           status=True)
        #         errores_certificados = generateCertificatesWinnersFaculty(request, eParticipantes)
        #         if len(errores_certificados) > 0:
        #             raise u"No se generaron los siguientes certificados de ganadores:%s" % ('\n'.join(errores_certificados))
        #         return JsonResponse({"result": "ok", "mensaje": u"Se generaron correctamente todos los certificados"})
        #     except Exception as ex:
        #         return JsonResponse({"result": "bad", "mensaje": u"Error  %s" % ex.__str__()})

        if action == 'generateCertificateWinner':
            try:
                id = int(encrypt(request.POST['id'])) if 'id' in request.POST and request.POST['id'] and int(encrypt(request.POST['id'])) != 0 else None
                eParticipantes = ParticipanteFeria.objects.filter(solicitud__estado=2,
                                                                  solicitud__es_ganador=True,
                                                                  solicitud__status=True,
                                                                  pk=id,
                                                                  status=True)
                if not eParticipantes.values_list('id', flat=True).exists():
                    raise NameError('No existe participante')
                errores_certificados = generateCertificatesWinners(request, eParticipantes)
                if len(errores_certificados) > 0:
                    raise u"No se genero el certificado: %s" % ('\n'.join(errores_certificados))
                return JsonResponse({"result": "ok", "mensaje": u"Se generaron correctamente todos los certificados"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error  %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'loadFormRequestFair':
                try:
                    typeForm = request.GET['typeForm'] if 'typeForm' in request.GET and request.GET['typeForm'] and str(request.GET['typeForm']) in ['new', 'edit', 'view'] else None
                    if typeForm is None:
                        raise NameError(u"No se encontro el tipo de formulario")
                    f = SolicitudFeriaForm()
                    eSolicitudFeria = None
                    id = 0
                    if typeForm in ['edit', 'view']:
                        id = int(encrypt(request.GET['id'])) if 'id' in request.GET and encrypt(request.GET['id']) and int(encrypt(request.GET['id'])) != 0 else None
                        eSolicitudFeria = SolicitudFeria.objects.filter(pk=id).first()
                        if eSolicitudFeria is None:
                            raise NameError(u"No existe formulario a editar")
                        f.initial = model_to_dict(eSolicitudFeria)
                        if typeForm == 'view':
                            f.view()
                        if typeForm == 'edit':
                            puede_realizar_accion(request, 'feria.puede_modificar_cronogramaferia')
                        data['eSolicitudFeria'] = eSolicitudFeria
                    else:
                        pass
                        puede_realizar_accion(request, 'feria.puede_agregar_cronogramaferia')
                    url_path = 'http://127.0.0.1:8000'
                    if not DEBUG:
                        url_path = 'https://sga.unemi.edu.ec'
                    data['url_path'] = url_path
                    data['form'] = f
                    data['frmName'] = "frmCronograma"
                    data['typeForm'] = typeForm
                    data['id'] = encrypt(id)
                    template = get_template("adm_feria/solicitudes/frm.html")
                    json_content = template.render(data, request)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            if action == 'reportParticipants':
                try:
                    id_cronograma = int(encrypt(request.GET['id']))
                    eCrongrama = CronogramaFeria.objects.get(pk=id_cronograma)
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False

                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_participantes')
                    ws.write_merge(0, 0, 0, 13, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 13, eCrongrama.__str__(), title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_proyectos_feria' + random.randint(1, 10000).__str__() + '.xls'
                    row_num = 3
                    columns = [
                        (u"N.", 2000),
                        (u"NOMBRES", 5000),
                        (u"APELLIDOS", 6000),
                        (u"CÉDULA", 4000),
                        (u"EMAIL", 9000),
                        (u"TUTOR", 10000),
                        (u"TITULO DEL PROYECTO", 16000),
                        (u"RESUMEN DEL PROYECTO", 16000),
                        (u"OBJETIVO GENERAL", 16000),
                        (u"OBJETIVOS ESPECÍFICOS", 16000),
                        (u"MATERIALES", 16000),
                        (u"RESULTADOS", 16000),
                        (u"ESTADO", 4000),
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listado = ParticipanteFeria.objects.filter(solicitud__cronograma_id=eCrongrama.id, solicitud__status=True, status=True)
                    row_num = 4
                    for lista in listado:
                        row_num += 1
                        persona = lista.matricula.inscripcion.persona
                        campo2 = persona.nombres
                        campo3 = persona.apellido1 + ' ' + persona.apellido2
                        if persona.cedula:
                            campo4 = persona.cedula
                        else:
                            campo4 = persona.pasaporte
                        campo5 = persona.email

                        campo6 = lista.solicitud.tutor.__str__()
                        campo7 = lista.solicitud.titulo
                        campo8 = lista.solicitud.resumen
                        campo9 = lista.solicitud.objetivogeneral
                        campo10 = lista.solicitud.objetivoespecifico
                        campo11 = lista.solicitud.materiales
                        campo12 = lista.solicitud.resultados
                        campo13 = lista.solicitud.get_estado_display()

                        ws.write(row_num, 0, row_num, font_style2)
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
                        ws.write(row_num, 12, campo13, font_style2)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'firmavistaprevia':
                try:
                    directory_qr = os.path.join(SITE_STORAGE, 'media', 'qrcode', 'firmaelectronica')
                    try:
                        os.stat(directory_qr)
                    except:
                        os.mkdir(directory_qr)
                    qrname = 'qr_firma_{}'.format(persona.id)
                    rutapdf = '{}/{}.pdf'.format(directory_qr, qrname)
                    rutaimg = '{}/{}.png'.format(directory_qr, qrname)
                    if os.path.isfile(rutapdf):
                        os.remove(rutaimg)
                        os.remove(rutapdf)
                    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'adm_archivosdepartamentales', 'ejemplo', 'participantes', 'participacion', ''))
                    os.makedirs(folder, exist_ok=True)
                    url = pyqrcode.create(f'FIRMADO POR: {persona.__str__()}\nFECHA: {datetime.now()}\nVALIDAR CON: www.firmadigital.gob.ec\nFIRMADO EN: sga.unemi.edu.ec')
                    url.png('{}/{}.png'.format(directory_qr, qrname), 16, '#000000')#'#1C3247'
                    url.svg('{}/{}.svg'.format(directory_qr, qrname), 16, '#1C3247')
                    # img = Image.open('{}/{}.png'.format(directory_qr, qrname))
                    # img.convert("RGBA")
                    # width, height = img.size
                    # logo_size = 50
                    # logo = Image.open(f'{directory_qr}/logosga.jpg')
                    # logo.convert("RGBA")
                    # xmin = ymin = int((width / 2) - (logo_size / 2))
                    # xmax = ymax = int((width / 2) + (logo_size / 2))
                    # logo = logo.resize((xmax - xmin, ymax - ymin))
                    # img.paste(logo, (xmin, ymin, xmax, ymax))
                    #
                    # img.show()
                    url_path = 'http://127.0.0.1:8000'
                    if not DEBUG:
                        url_path = 'https://sga.unemi.edu.ec'

                    data['url_path'] = url_path
                    data['qrname'] = '{}'.format(qrname)
                    data['persona'] = persona
                    # return  conviert_html_to_pdf('adm_archivosdepartamentales/firma/vistapreviafirma.html', {'data': data,'pagesize':'A4'})
                    valida, pdfge, result = conviert_html_to_pdfsaveqrcertificado_generico(request,

                        'adm_archivosdepartamentales/firma/vistapreviafirma.html',
                        {'data': data}, folder, qrname + '.pdf'

                    )
                    if valida:
                        with open(f'{folder}{qrname}.pdf', mode='rb') as pdf:
                            images = convert_from_bytes(pdf.read(),
                                                        output_folder=folder,
                                                        poppler_path=SITE_POPPLER,
                                                        fmt="png",
                                                        single_file=True,
                                                        output_file=qrname)#dpi=95, size=(150, 45)
                        return JsonResponse({"result": "ok", "mensaje": u"Se genero correctamente la firma electronica.", 'url': f'{url_path}/'+'/'.join(['media', 'adm_archivosdepartamentales', 'ejemplo', 'participantes', 'participacion', f'{qrname}.png' ])})
                except Exception as ex:
                    pass
            return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s"})
        else:
            try:
                data['title'] = u'Solicitudes de Ferias'
                data['id'] = request.GET['id']
                id = int(encrypt(request.GET['id'])) if 'id' in request.GET and encrypt(request.GET['id']) and int(encrypt(request.GET['id'])) != 0 else None
                if id is None:
                    raise NameError('Parametro  id incorrecto')
                eCronogramaFeria = CronogramaFeria.objects.filter(pk=id).first()
                if eCronogramaFeria is None:
                    raise NameError('Parametro  no encrontro el cronograma')
                data['eCronogramaFeria'] = eCronogramaFeria
                data['carreras'] = eCronogramaFeria.carreras.all()
                return render(request, "adm_feria/solicitudes/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect("/adm_feria")



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
            if action == 'generateCertificatesParticipants':
                return generateCertificatesParticipants(request, data)



def generateCertificatesParticipants(request, data):
    idc = int(encrypt(request.POST['idc'])) if 'idc' in request.POST and request.POST['idc'] and int(encrypt(request.POST['idc'])) != 0 else None
    eParticipantes = ParticipanteFeria.objects.filter(solicitud__cronograma_id=idc,
                                                      #solicitud_id=88,
                                                      solicitud__estado=2,
                                                      solicitud__status=True,
                                                      status=True)
    errores = []
    for eParticipante in eParticipantes:
        eInscripcion = eParticipante.inscripcion
        eUsuario = eInscripcion.persona.usuario
        with transaction.atomic(using='default'):
            try:
                aData = {}
                url_path = 'http://127.0.0.1:8000'
                if not DEBUG:
                    url_path = 'https://sga.unemi.edu.ec'

                aData['rector'] = rector = Administrativo.objects.get(pk=225)
                aData['rectorfirma'] = rectorfirma = rector.persona.firmapersona_set.filter(status=True).order_by('-tipofirma').first()
                aData['decano'] = decano = Administrativo.objects.get(pk=415)
                aData['decanofirma'] = decanofirma = decano.persona.firmapersona_set.filter(status=True).order_by('-tipofirma').first()
                aData['url_path'] = url_path
                aData['eParticipante'] = eParticipante
                aData['hoy'] = hoy = datetime.now().date()
                username = elimina_tildes(eUsuario.username)
                qrname = f'feria_qr_certificadoparticipacion_{eInscripcion.id}{eParticipante.solicitud.id}{eParticipante.id}'
                folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'feria', 'certificados', 'participantes', username, 'participacion', ''))
                folder2 = os.path.join(os.path.join(SITE_STORAGE, 'media', 'feria', 'certificados', 'participantes', username, 'qrcode', ''))
                os.makedirs(folder, exist_ok=True)
                os.makedirs(folder2, exist_ok=True)
                foldersave = f'feria/certificados/participantes/{username}/participacion/{qrname}.pdf'

                rutapdf = folder + qrname + '.pdf'
                aData['url_qr'] = rutaimg = folder2 + qrname + '.png'
                aData['version'] = datetime.now().strftime('%Y%m%d_%H%M%S')
                if os.path.isfile(rutapdf):
                    os.remove(rutapdf)
                elif os.path.isfile(rutaimg):
                    os.remove(rutaimg)
                url = pyqrcode.create(f'{url_path}/media/feria/certificados/participantes/{username}/participacion/{qrname}.pdf')
                aData['image_qrcode'] = f'{url_path}/media/feria/certificados/participantes/{username}/qrcode/{qrname}.png'
                imageqr = url.png(rutaimg, 16, '#000000')
                valida, pdf, result = conviert_html_to_pdfsaveqrcertificadoferiaparticipacion(
                    request,
                    'adm_feria/utileria/3feria_certificado_participante.html',
                    {'pagesize': 'A4', 'data': aData}, folder, qrname + '.pdf'
                )
                if valida:
                    eParticipante.certificado = foldersave
                    eParticipante.save(request)
                time.sleep(3)
            except Exception as ex:
                transaction.set_rollback(True, using='default')
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_error = f'({eInscripcion}   ocurrio el siguiente error {str(ex)} {err}'
                errores.append(msg_error)

    if len(errores) > 0:
        notificacion = Notificacion(titulo=f"Error en el proceso de generación de certificados de participación",
                                    cuerpo=u"No se generaron los siguientes certificados de participación:%s" % ('\n'.join(errores)),
                                    destinatario=request.session['persona'],
                                    url=f"/adm_feria/solicitudes?id={encrypt(idc)}",
                                    content_type=None,
                                    object_id=None,
                                    prioridad=2,
                                    app_label=request.session['tiposistema'],
                                    fecha_hora_visible=datetime.now() + timedelta(days=2))
        notificacion.save(request)
    else:
        notificacion = Notificacion(titulo=f"Proceso finalizado de generación de certificados de participación",
                                    cuerpo=f"Se genero correctamente el proceso",
                                    destinatario=request.session['persona'],
                                    url=f"/adm_feria/solicitudes?id={encrypt(idc)}",
                                    content_type=None,
                                    object_id=None,
                                    prioridad=2,
                                    app_label=request.session['tiposistema'],
                                    fecha_hora_visible=datetime.now() + timedelta(days=2))
        notificacion.save(request)

def generateCertificatesWinners(request, eParticipantes):
    errores = []
    for eParticipante in eParticipantes:
        eInscripcion = eParticipante.inscripcion
        eUsuario = eInscripcion.persona.usuario
        aData = {}
        url_path = 'http://127.0.0.1:8000'
        if not DEBUG:
            url_path = 'https://sga.unemi.edu.ec'

        aData['rector'] = rector = Administrativo.objects.get(pk=225)

        # aData['rectorfirma'] = rectorfirma = rector.persona.firmapersona_set.filter(status=True).order_by('-tipofirma').first()
        aData['decano'] = decano = Administrativo.objects.get(pk=415)
        aData['decanofirma'] = decanofirma = decano.persona.firmapersona_set.filter(status=True).order_by('-tipofirma').first()
        aData['url_path'] = url_path
        aData['eParticipante'] = eParticipante
        aData['hoy'] = hoy = datetime.now().date()
        username = elimina_tildes(eUsuario.username)
        qrname = f'feria_qr_certificadoganador_{eInscripcion.id}{eParticipante.solicitud.id}{eParticipante.id}'
        folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'feria', 'certificados', 'ganadores', username, 'ganador', ''))
        folder2 = os.path.join(os.path.join(SITE_STORAGE, 'media', 'feria', 'certificados', 'ganadores', username, 'qrcode', ''))
        foldersave = f'feria/certificados/ganadores/{username}/ganador/{qrname}.pdf'
        rutapdf = folder + qrname + '.pdf'
        aData['url_qr'] = rutaimg = folder2 + qrname + '.png'
        aData['version'] = datetime.now().strftime('%Y%m%d_%H%M%S')
        aData['image_qrcode'] = f'{url_path}/media/feria/certificados/ganadores/{username}/qrcode/{qrname}.png'
        if os.path.isfile(rutapdf):
            os.remove(rutapdf)
        elif os.path.isfile(rutaimg):
            os.remove(rutaimg)
        if eParticipante.solicitud.es_ganador:
            #with transaction.atomic(using='default'):
            try:
                os.makedirs(folder, exist_ok=True)
                os.makedirs(folder2, exist_ok=True)
                url = pyqrcode.create(f'{url_path}/media/feria/certificados/ganadores/{username}/ganador/{qrname}.pdf')
                imageqr = url.png(rutaimg, 16, '#000000')
                valida, pdf, result = conviert_html_to_pdfsaveqrcertificadoferiaparticipacion(
                    request,
                    'adm_feria/utileria/3feria_certificado_ganador_carrera.html',
                    {'pagesize': 'A4', 'data': aData}, folder, qrname + '.pdf'
                )
                if valida:
                    eParticipante.certificadoganador = foldersave
                    eParticipante.save(request)
                time.sleep(3)
            except Exception as ex:
                #transaction.set_rollback(True, using='default')
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_error = f'({eInscripcion}   ocurrio el siguiente error {str(ex)} {err}'
                print(msg_error)
                errores.append(msg_error)

        else:
            if eParticipante.certificadoganador is not None:
                eParticipante.certificadoganador = None
                eParticipante.save(request)

    return errores

def generateCertificatesWinnersFaculty(request, eParticipantes):
    errores = []
    for eParticipante in eParticipantes:
        eInscripcion = eParticipante.inscripcion
        eUsuario = eInscripcion.persona.usuario
        aData = {}
        url_path = 'http://127.0.0.1:8000'
        if not DEBUG:
            url_path = 'https://sga.unemi.edu.ec'

        aData['rector'] = rector = Administrativo.objects.get(pk=225)

        # aData['rectorfirma'] = rectorfirma = rector.persona.firmapersona_set.filter(status=True).order_by('-tipofirma').first()
        aData['decano'] = decano = Administrativo.objects.get(pk=415)
        aData['decanofirma'] = decanofirma = decano.persona.firmapersona_set.filter(status=True).order_by('-tipofirma').first()
        aData['url_path'] = url_path
        aData['eParticipante'] = eParticipante
        aData['hoy'] = hoy = datetime.now().date()
        username = elimina_tildes(eUsuario.username)
        qrname = f'feria_qr_certificadoganadorfacultad_{eInscripcion.id}{eParticipante.solicitud.id}{eParticipante.id}'
        folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'feria', 'certificados', 'ganadores', username, 'ganador', ''))
        folder2 = os.path.join(os.path.join(SITE_STORAGE, 'media', 'feria', 'certificados', 'ganadores', username, 'qrcode', ''))
        foldersave = f'feria/certificados/ganadores/{username}/ganador/{qrname}.pdf'
        rutapdf = folder + qrname + '.pdf'
        aData['url_qr'] = rutaimg = folder2 + qrname + '.png'
        aData['version'] = datetime.now().strftime('%Y%m%d_%H%M%S')
        aData['image_qrcode'] = f'{url_path}/media/feria/certificados/ganadores/{username}/qrcode/{qrname}.png'
        if os.path.isfile(rutapdf):
            os.remove(rutapdf)
        elif os.path.isfile(rutaimg):
            os.remove(rutaimg)
        if eParticipante.solicitud.es_ganadorfacultad:
            #with transaction.atomic(using='default'):
            try:
                os.makedirs(folder, exist_ok=True)
                os.makedirs(folder2, exist_ok=True)
                url = pyqrcode.create(f'{url_path}/media/feria/certificados/ganadores/{username}/ganador/{qrname}.pdf')
                imageqr = url.png(rutaimg, 16, '#000000')
                valida, pdf, result = conviert_html_to_pdfsaveqrcertificadoferiaparticipacion(
                    request,
                    'adm_feria/utileria/3feria_certificado_ganador_facultad.html',
                    {'pagesize': 'A4', 'data': aData}, folder, qrname + '.pdf'
                )
                if valida:
                    eParticipante.certificadoganadorfacultad = foldersave
                    eParticipante.save(request)
                time.sleep(3)
            except Exception as ex:
                #transaction.set_rollback(True, using='default')
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_error = f'({eInscripcion}   ocurrio el siguiente error {str(ex)} {err}'
                print(msg_error)
                errores.append(msg_error)

        else:
            if eParticipante.certificadoganadorfacultad is not None:
                eParticipante.certificadoganadorfacultad = None
                eParticipante.save(request)

    return errores