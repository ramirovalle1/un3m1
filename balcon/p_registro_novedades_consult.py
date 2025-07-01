# coding=latin-1
import random
import sys
import json
from cgitb import html
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from django.db import connection
from django.db import transaction
from django.db.models import Count, PROTECT, Sum, Avg, Min, Max
from django.db.models.query_utils import Q
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from balcon.models import ProcesoServicio, Solicitud, Agente, Servicio, HistorialSolicitud, \
    RegistroNovedadesExternoAdmision, ConfigInformacionExterno, TipoProcesoServicio
from settings import DEBUG
from sga.funciones import variable_valor, generar_nombre, log, notificacion
from sga.models import LogReporteDescarga, Matricula, MateriaAsignada, Persona, PerfilUsuario, TestSilaboSemanal, \
    TestSilaboSemanalAdmision, LinkMateriaExamen, Inscripcion
from moodle import moodle


@transaction.atomic()
def view(request):
    data = {}
    validar_con_captcha = variable_valor('VALIDAR_CON_CAPTCHA_REGISTRO_NOVEDADES')
    if DEBUG:
        validar_con_captcha = False
    data['validar_con_captcha'] = validar_con_captcha
    data['public_key'] = public_key = variable_valor('API_GOOGLE_RECAPTCHA_PUBLIC_KEY')
    data['private_key'] = private_key = variable_valor('API_GOOGLE_RECAPTCHA_PRIVATE_KEY')
    client_address = get_client_ip(request)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'searchDocumentNew':
            try:
                if validar_con_captcha:
                    if not 'g-recaptcha-response' in request.POST:
                        raise NameError(u"Complete el captcha de seguridad.")
                    recaptcha_response = request.POST.get('g-recaptcha-response')
                    url = 'https://www.google.com/recaptcha/api/siteverify'
                    values = {'secret': private_key,
                              'response': recaptcha_response}
                    aData = urlencode(values)
                    aData = aData.encode('utf-8')
                    req = Request(url, aData)
                    response = urlopen(req)
                    result = json.loads(response.read().decode())
                    if not result['success']:
                        raise NameError(u"ReCaptcha no válido. Vuelve a intentarlo..")

                if not 'documento' in request.POST or not request.POST['documento']:
                    raise NameError(u"Número de cédula o pásaporte incorrecto")
                documento = (request.POST['documento']).strip()
                if documento == '':
                    raise NameError(u"Número de cédula o pásaporte incorrecto")
                if not Inscripcion.objects.filter(Q(persona__cedula=documento) | Q(persona__pasaporte=documento), coordinacion_id=9, status=True).exists():
                    # if not Matricula.objects.values("id").filter(Q(inscripcion__persona__cedula=documento) | Q(inscripcion__persona__pasaporte=documento), inscripcion__coordinacion_id=9, status=True).exists():
                    raise NameError(u"No se encuentra registrado como aspirante del curso de nivelación")
                inscripciones = Inscripcion.objects.filter(Q(persona__cedula=documento) | Q(persona__pasaporte=documento), coordinacion_id=9, status=True)
                perfiles = PerfilUsuario.objects.filter(persona_id__in=inscripciones.values_list("persona_id", flat=True).distinct(), inscripcion_id__in=inscripciones.values_list("id", flat=True).distinct(), status=True)
                solicitudes = Solicitud.objects.filter(status=True, solicitante_id__in=inscripciones.values_list("persona_id", flat=True).distinct(), perfil_id__in=perfiles.values_list("id", flat=True).distinct()).order_by('-id')
                data['solicitudes'] = solicitudes
                template = get_template("p_registro_novedades/listrequest.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", 'mensaje': u'Ocurrio un error al consultar los datos. %s' % ex})

        elif action == 'viewHistoric':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"Solicitud no encontrada")
                id = request.POST['id']
                if not Solicitud.objects.filter(pk=int(id)).exists():
                    raise NameError(u"Solicitud no encontrada")
                eSolicitud = Solicitud.objects.get(pk=int(id))
                data['title'] = u'Ver Historial'
                data['id'] = id
                data['filtro'] = filtro = eSolicitud
                data['detalle'] = HistorialSolicitud.objects.filter(status=True, solicitud=filtro).order_by('pk')
                template = get_template("p_registro_novedades/verhistorial.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", 'mensaje': u'Ocurrio un error al consultar los datos. %s' % ex})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            return HttpResponseRedirect('/p_registro_novedades')
        else:
            try:
                data['title'] = u"Consulta de solicitudes de novedades"
                return render(request, "p_registro_novedades/consult.html", data)

            except Exception as ex:
                return HttpResponseRedirect('/p_registro_novedades?%s' % ex)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
