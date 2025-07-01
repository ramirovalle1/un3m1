# -*- coding: latin-1 -*-
import json
import sys
import urllib
from decimal import Decimal
from itertools import count
import random
from PIL.ImageOps import _lut
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Sum, F, FloatField
from django.db.models.functions import Coalesce
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.template.context import Context
from django.db.models.query_utils import Q
from datetime import datetime, timedelta
from xlwt import *
from xlwt import easyxf
import xlwt

from decorators import secure_module, last_access
from settings import DEBUG
from .adm_padronelectoral import generar_qr_padronelectoral
from .models import CabPadronElectoral, DetPersonaPadronElectoral, MesasPadronElectoral
from sga.funciones import MiPaginador, log, variable_valor, generar_nombre, convertir_fecha
from sga.funcionesxhtml2pdf import conviert_html_to_pdf, conviert_html_to_pdf_name_bitacora
from sga.models import Persona, Provincia, Externo, Matricula, RecordAcademico, CUENTAS_CORREOS, miinstitucion

from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt
import socket

from urllib.parse import urlencode
from urllib.request import urlopen, Request

@last_access
@transaction.atomic()
def view(request):
    data = {}
    validar_con_captcha = False
    # data['validar_con_captcha'] = validar_con_captcha = variable_valor('VALIDAR_CON_CAPTCHA_REGISTRO_NOVEDADES')
    # data['public_key'] = public_key = variable_valor('API_GOOGLE_RECAPTCHA_PUBLIC_KEY')
    # data['private_key'] = private_key = variable_valor('API_GOOGLE_RECAPTCHA_PRIVATE_KEY')

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'consultar':
                try:
                    with transaction.atomic():
                        # if validar_con_captcha:
                        #     recaptcha_response = request.POST.get('g-recaptcha-response')
                        #     url = 'https://www.google.com/recaptcha/api/siteverify'
                        #     values = {'secret': variable_valor('GOOGLE_RECAPTCHA_SECRET_KEY'),
                        #               'response': recaptcha_response}
                        #     data = urlencode(values)
                        #     data = data.encode('utf-8')
                        #     req = Request(url, data)
                        #     response = urlopen(req)
                        #     result = json.loads(response.read().decode())
                        #     if not result['success']:
                        #         transaction.set_rollback(True)
                        #         return JsonResponse({"result": True, "mensaje": "Complete el captcha de seguridad."},safe=False)
                        cedula = request.POST['cedula'].strip()
                        anionacimiento = int(request.POST['anionacimiento'].strip())
                        datos = {}
                        if Persona.objects.filter(cedula=cedula).exists():
                            datos['datospersona'] = datospersona = Persona.objects.filter(cedula=cedula).first()
                            if datospersona.nacimiento.year != anionacimiento:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": True, "mensaje": "Datos Incorrectos."},safe=False)
                            datos['evento'] = evento = CabPadronElectoral.objects.filter(activo=True, status=True).first()
                            if DetPersonaPadronElectoral.objects.filter(cab=evento, status=True, persona=datospersona).exists():
                                datos['milugar'] = milugar = DetPersonaPadronElectoral.objects.filter(cab=evento, status=True, persona=datospersona)
                                template = get_template("adm_padronelectoral/milugarvotacion/resultado.html")
                                return JsonResponse({"result": False, 'data': template.render(datos)})
                            else:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": True, "mensaje": "Usted no se encuentra empadronado en este proceso electoral."},safe=False)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Usted no se encuentra empadronado en este proceso electoral."},safe=False)

                except Exception as ex:
                    mensajeerror = "{} - {}".format(ex, 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    messages.error(request, mensajeerror)
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde.", "mensajeerror": mensajeerror}, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'generarqr':
                try:
                    id = request.GET['id']
                    data['person'] = person = DetPersonaPadronElectoral.objects.get(id=id)
                    data['tittle'] = 'PDF QR Electoral'
                    data['foto'] = person.persona.get_foto()
                    result = generar_qr_padronelectoral(person, detalle_id=person.id)
                    link_pdf = ''
                    if result.get('isSuccess', {}):
                        aData = result.get('data', {})
                        url_pdf = aData.get('url_pdf', None)
                        if url_pdf == None:
                            raise NameError(u"No se encontro url del documento")
                        link_pdf = f"https://sga.unemi.edu.ec/media/{url_pdf}"
                        person.pdf = url_pdf
                        person.save(request)
                        return JsonResponse({"result": True, "url_pdf": link_pdf})
                    else:
                        return JsonResponse({"result": False, "msg": result.get('message')})
                except Exception as ex:
                    print(ex)
                    # messages.success(request, f"{ex} - {sys.exc_info()[-1].tb_lineno}")
                    return JsonResponse({"result": False, "msg": f"{ex} - {sys.exc_info()[-1].tb_lineno}"})

        else:
            try:
                data['title'] = u'Consulta tu lugar de votación'
                data['currenttime'] = datetime.now()
                hoy = datetime.now().date()
                data['valida_captcha'] = False
                data['public_key'] = False
                data['existeuno'] = CabPadronElectoral.objects.filter(activo=True, status=True).exists()
                data['traerprimero'] = CabPadronElectoral.objects.filter(activo=True, status=True).first()
                return render(request, "adm_padronelectoral/milugarvotacion/milugarvotacion.html", data)
            except Exception as ex:
                pass