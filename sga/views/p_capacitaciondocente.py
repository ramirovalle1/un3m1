# -*- coding: UTF-8 -*-
import os
import random
import sys
from datetime import datetime, time

import pyqrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template

from decorators import get_client_ip
from settings import SERVER_RESPONSE, DEBUG, SITE_STORAGE
from sga.funciones import variable_valor, log
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsaveqrcertificado
from sga.templatetags.sga_extras import encrypt


def encuesta(request, token=None):
    data = {}
    data['validar_con_captcha'] = validar_con_captcha = variable_valor('VALIDAR_CON_CAPTCHA_CAPACITACION')
    data['public_key'] = public_key = variable_valor('API_GOOGLE_RECAPTCHA_PUBLIC_KEY')
    data['private_key'] = private_key = variable_valor('API_GOOGLE_RECAPTCHA_PRIVATE_KEY')
    data['version_static'] = '23.0.1'
    client_address = get_client_ip(request)
    data['currenttime'] = datetime.now()
    data['remotenameaddr'] = remotenameaddr = '%s' % (request.META['SERVER_NAME'])
    data['remoteaddr'] = remoteaddr = '%s - %s' % (client_address, request.META['SERVER_NAME'])
    data['server_response'] = SERVER_RESPONSE

    if request.method == 'POST':
        action = request.POST.get('action', None)

        if action == 'saveEncuesta':
            from sga.models import CapCabeceraSolicitudDocente
            from inno.models import CapRespuestaEncuestaSatisfaccion, CapPreguntaEncuestaPeriodo, \
                CapOpcionPreguntaEncuestaPeriodo
            with transaction.atomic():
                try:
                    try:
                        eCapCabecera = CapCabeceraSolicitudDocente.objects.get(status=True, token=token)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro solicitud del evento")
                    eCapEvento = eCapCabecera.capeventoperiodo
                    eCapEncuesta = eCapEvento.encuesta
                    eCapPreguntas = CapPreguntaEncuestaPeriodo.objects.filter(encuesta=eCapEncuesta, status=True, isActivo=True)
                    # aRespuestas = []
                    for eCapPregunta in eCapPreguntas:
                        opcion_id = request.POST.get(f"opcion_pregunta_id_{encrypt(eCapPregunta.id)}", 0)
                        if opcion_id == '' and type(opcion_id) is str:
                            opcion_id = 0
                        else:
                            opcion_id = int(opcion_id)

                        # valoracion = int(request.POST.get(f"valoracion_id_{encrypt(eCapPregunta.id)}", 0))
                        observacion = request.POST.get(f"observacion_id_{encrypt(eCapPregunta.id)}", None)
                        try:
                            eCapOpcionPreguntaEncuestaPeriodo = CapOpcionPreguntaEncuestaPeriodo.objects.get(id=opcion_id)
                        except ObjectDoesNotExist:
                            raise NameError(f"Seleccione una opción de la pregunta {eCapPregunta.descripcion}")
                        #
                        # if valoracion == 0:
                        #     raise NameError(f"Pregunta {eCapPregunta.descripcion}")
                        try:
                            eCapRespuestaEncuesta = CapRespuestaEncuestaSatisfaccion.objects.get(pregunta=eCapPregunta,
                                                                                                 solicitud=eCapCabecera)
                        except ObjectDoesNotExist:
                            eCapRespuestaEncuesta = CapRespuestaEncuestaSatisfaccion(pregunta=eCapPregunta,
                                                                                     solicitud=eCapCabecera)
                        eCapRespuestaEncuesta.opcion = eCapOpcionPreguntaEncuestaPeriodo
                        eCapRespuestaEncuesta.valoracion = eCapOpcionPreguntaEncuestaPeriodo.valoracion
                        eCapRespuestaEncuesta.observacion = observacion
                        eCapRespuestaEncuesta.save(request)
                        log(u'Respuesta de encuesta de satisfacción : %s' % eCapRespuestaEncuesta, request, "add", user=eCapCabecera.participante.usuario)
                    res_js = {'isSuccess': True,
                              'message': u"Se guardo correctamente la encuesta.",
                              'data': {'url': eCapCabecera.rutapdf.url if eCapCabecera.rutapdf else f'/p_capacitaciondocente/{token}/certificado?action=create',
                                       'id': eCapCabecera.id,
                                       'name': eCapCabecera.rutapdf.name if eCapCabecera.rutapdf else None}}
                except Exception as ex:
                    transaction.set_rollback(True)
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    if DEBUG:
                        print(err)
                    msg_err = f"{ex.__str__()}"
                    res_js = {'isSuccess': False,
                              'message': msg_err,
                              'data': {'url': None, 'id': None, 'name': None}}
                return JsonResponse(res_js)

        return JsonResponse({"isSuccess": False, "message": u"Error al guardar los datos."})

    else:
        if 'action' in request.GET:
            action = request.GET.get('action', None)

            if action == 'loadEncuesta':
                from sga.models import CapCabeceraSolicitudDocente
                from inno.models import CapPreguntaEncuestaPeriodo
                try:
                    try:
                        eCapCabecera = CapCabeceraSolicitudDocente.objects.get(status=True, token=token)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro solicitud del evento")
                    eCapEvento = eCapCabecera.capeventoperiodo
                    eCapEncuesta = eCapEvento.encuesta
                    eCapPreguntas = CapPreguntaEncuestaPeriodo.objects.filter(encuesta=eCapEncuesta, status=True, isActivo=True)
                    data['eCapPreguntas'] = eCapPreguntas
                    data['frmName'] = "frmEncuesta"
                    data['eCapCabecera'] = eCapCabecera
                    template = get_template("p_capacitaciondocente/modal/formencuestasatisfaccion.html")
                    json_content = template.render(data, request=request)
                    return JsonResponse({"isSuccess": True, 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"isSuccess": False, 'message': str(ex)})

            return HttpResponseRedirect(f'/loginsga?info=Acción no permitida')

        else:
            from sga.models import CapCabeceraSolicitudDocente
            try:
                try:
                    eSolicitud = CapCabeceraSolicitudDocente.objects.get(status=True, token=token)
                except ObjectDoesNotExist:
                    raise NameError(u"Token no válido")
                if eSolicitud.aplica_encuesta():
                    if not DEBUG:
                        if eSolicitud.respondio_encuesta():
                            if eSolicitud.rutapdf:
                                return HttpResponseRedirect(f"{eSolicitud.rutapdf.url}")
                            else:
                                return HttpResponseRedirect(f"/p_capacitaciondocente/{token}/certificado?action=create")
                data['title'] = 'Encuesta de satisfacción'
                data['eSolicitud'] = eSolicitud
                return render(request, 'p_capacitaciondocente/view.html', data)
            except Exception as ex:
                return HttpResponseRedirect(f"/loginsga?info={ex.__str__()}")


def certificado(request, token=None):
    data = {}
    data['validar_con_captcha'] = validar_con_captcha = variable_valor('VALIDAR_CON_CAPTCHA_CAPACITACION')
    data['public_key'] = public_key = variable_valor('API_GOOGLE_RECAPTCHA_PUBLIC_KEY')
    data['private_key'] = private_key = variable_valor('API_GOOGLE_RECAPTCHA_PRIVATE_KEY')
    data['version_static'] = '23.0.1'
    client_address = get_client_ip(request)
    data['currenttime'] = datetime.now()
    data['remotenameaddr'] = remotenameaddr = '%s' % (request.META['SERVER_NAME'])
    data['remoteaddr'] = remoteaddr = '%s - %s' % (client_address, request.META['SERVER_NAME'])
    data['server_response'] = SERVER_RESPONSE

    if request.method == 'POST':
        action = request.POST.get('action', None)

        return JsonResponse({"isSuccess": False, "message": u"Error al guardar los datos."})

    else:
        if 'action' in request.GET:
            action = request.GET.get('action', None)

            if action == 'create':
                from sga.models import CapCabeceraSolicitudDocente
                from inno.models import CapPreguntaEncuestaPeriodo
                with transaction.atomic():
                    try:
                        try:
                            inscrito = CapCabeceraSolicitudDocente.objects.get(status=True, token=token)
                        except ObjectDoesNotExist:
                            raise NameError(u"No se encontro solicitud del evento")
                        eventoperiodo = inscrito.capeventoperiodo
                        firmacertificado = 'robles'
                        fechacambio = (datetime(2019, 11, 1, 0, 0, 0)).date()
                        if eventoperiodo.fechafin >= fechacambio:
                            firmacertificado = 'firmaguillermo'
                        data['firmacertificado'] = firmacertificado

                        eventoperiodo.actualizar_folio()

                        data['inscrito'] = inscrito

                        url_path = data['url_path'] = 'http://127.0.0.1:8000'
                        if not DEBUG:
                            url_path = data['url_path'] = 'https://sga.unemi.edu.ec'

                        qrname = 'capins_qr_certificado_' + str(inscrito.id)
                        folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', 'certificados', 'qr'))
                        rutapdf = folder + qrname + '.pdf'
                        rutaimg = folder + qrname + '.png'
                        if os.path.isfile(rutapdf):
                            os.remove(rutaimg)
                            os.remove(rutapdf)
                        url = pyqrcode.create(f'{url_path}//media/qrcode/certificados/' + qrname + '.pdf')
                        imageqr = url.png(folder + qrname + '.png', 16, '#000000')
                        data['qrname'] = 'qr' + qrname
                        data['url_path'] = 'http://127.0.0.1:8000'
                        d = datetime.now()
                        data['horasegundo'] = d.strftime('%Y%m%d_%H%M%S')

                        valida = conviert_html_to_pdfsaveqrcertificado(
                            'adm_capacitaciondocente/gestion/certificado_individual_pdf.html',
                            {'pagesize': 'A4', 'data': data}, qrname + '.pdf'
                        )
                        if not valida:
                            raise NameError(u"Error al obtener el certificado")
                        inscrito.rutapdf = 'qrcode/certificados/' + qrname + '.pdf'
                        inscrito.notificado = True
                        inscrito.fechanotifica = datetime.now()
                        inscrito.personanotifica = None
                        if not inscrito.token:
                            inscrito.token = token
                        inscrito.save(request)
                        asunto = u"CERTIFICADO - " + inscrito.capeventoperiodo.capevento.nombre
                        if not DEBUG:
                            inscrito.mail_notificar_certificado(request.session['nombresistema'])
                        return HttpResponseRedirect(f"{inscrito.rutapdf.url}")
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return HttpResponseRedirect(f'/loginsga?info={ex.__str__()}')

            return HttpResponseRedirect(f'/loginsga?info=Acción no permitida')

        else:
            from sga.models import CapCabeceraSolicitudDocente
            try:
                try:
                    eSolicitud = CapCabeceraSolicitudDocente.objects.get(status=True, token=token)
                except ObjectDoesNotExist:
                    raise NameError(u"Token no válido")
                if eSolicitud.aplica_encuesta():
                    if eSolicitud.respondio_encuesta():
                        if eSolicitud.rutapdf:
                            return HttpResponseRedirect(f"{eSolicitud.rutapdf.url}")
                    else:
                        return HttpResponseRedirect(f"/p_capacitaciondocente/{token}/encuesta")
                return HttpResponseRedirect(f"/loginsga?info=Acción no encontrada")
            except Exception as ex:
                return HttpResponseRedirect(f"/loginsga?info={ex.__str__()}")


