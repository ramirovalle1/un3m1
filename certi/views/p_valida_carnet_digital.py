# coding=latin-1
import json
import random
from cgitb import html
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db import transaction
from django.db.models import Count, PROTECT, Sum, Avg, Min, Max
from django.db.models.query_utils import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
import xlwt
from django.template.loader import get_template
from django.template import Context
from openpyxl import load_workbook
from xlwt import *
import random
import time as pausaparaemail

# from datetime import datetime
from datetime import datetime, time
from decimal import Decimal

from django.contrib import messages
from django.db.models import Max
import xlrd as xlrd
from decorators import secure_module, last_access
from sagest.commonviews import secuencia_convenio_devengacion
from sagest.models import DistributivoPersona
from settings import DEBUG
from sga.funciones import variable_valor
from certi.funciones import valida_tiempo_certificado
from certi.models import Certificado, LogValidaCertificado, Carnet
from sga.models import LogReporteDescarga, Matricula


@transaction.atomic()
def view(request):
    data = {}
    data['validar_con_captcha'] = validar_con_captcha = variable_valor('VALIDAR_CON_CAPTCHA_CERTIFICADO')
    data['public_key'] = public_key = variable_valor('API_GOOGLE_RECAPTCHA_PUBLIC_KEY')
    data['private_key'] = private_key = variable_valor('API_GOOGLE_RECAPTCHA_PRIVATE_KEY')
    client_address = get_client_ip(request)
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'validar':
            try:
                capippriva = request.POST['capippriva'] if 'capippriva' in request.POST else ''
                browser = request.POST['navegador']
                ops = request.POST['os']
                cookies = request.POST['cookies']
                screensize = request.POST['screensize']
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
                if not 'codigo' in request.POST and request.POST['codigo']:
                    raise NameError(u"Código invalido")
                codigo = request.POST['codigo']
                if not LogReporteDescarga.objects.filter(codigo=codigo).exists():
                    raise NameError(u"Código invalido, no existe!")
                logreporte = LogReporteDescarga.objects.filter(codigo=codigo).first()
                if not Certificado.objects.filter(reporte=logreporte.reporte, visible=True, status=True).exists():
                    raise NameError(u"Certificadon invalido, no existe!")
                certificado = Certificado.objects.filter(reporte=logreporte.reporte, visible=True, status=True).first()
                valido = valida_tiempo_certificado(certificado.vigencia, certificado.tipo_vigencia, logreporte.fechahora)
                matricula = logreporte.get_model_data_matricula()
                inscripcion = logreporte.get_model_data_inscripcion()
                persona = logreporte.get_model_data_persona()
                carrera = inscripcion.carrera if inscripcion else None
                # periodo = matricula.nivel.periodo if matricula else None
                # isCertificadoMatricula = True if matricula else False

                if not matricula and not inscripcion and not persona:
                    raise NameError(u"Certificadon invalido, no existe!")

                logvalida = LogValidaCertificado(browser=browser,
                                                 os=ops,
                                                 client_address=client_address,
                                                 ippu=capippriva,
                                                 screensize=screensize,
                                                 fechahora=datetime.now(),
                                                 logdescarga=logreporte)
                logvalida.save()
                data = {
                    'codigo': logreporte.codigo,
                    'persona': persona.__str__(),
                    'certificado': certificado.certificacion,
                    'version': certificado.version,
                    'fechaemision': logreporte.fechahora,
                    'valido': valido,
                    'carrera': carrera.__str__() if carrera else 'S/N',
                    'url': logreporte.url,
                }
                template = get_template("p_valida_certificado/ver_certificado.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content, 'data': data})
            except Exception as ex:
                return JsonResponse({"result": "bad", 'mensaje': u'Ocurrio un error al validar el certificado. %s' % ex})
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            return HttpResponseRedirect('/')
        else:
            try:
                data['title'] = u"Validación de Carnet Digital"
                if not  'code' in request.GET:
                    raise NameError('El parámetro es incorrecto')
                code = request.GET['code']
                if not code.isdigit():
                    raise NameError('El código es inválido')
                data['tpp'] = tipo_perfil = request.GET.get('tpp') # tpp contiene el tipo de perfil si no existe el parametro es estudiante
                eCarnets = None
                id_code = code[6::]
                if tipo_perfil is None:
                    eMatriculas = Matricula.objects.filter(id=id_code)
                    if not eMatriculas.values("id").exists():
                        raise NameError('El código no existe')
                    eMatricula = eMatriculas.first()
                    eCarnets = Carnet.objects.filter(matricula=eMatricula, status=True)
                    if not eCarnets.values("id").exists():
                        raise NameError('No existe un carnet digital')
                    data['inscripcion'] = eMatricula.inscripcion
                    data['matricula'] = eMatricula.inscripcion
                elif tipo_perfil == 'ad':# Credenciales con docente y administrativo
                    eDistibutivos = DistributivoPersona.objects.filter(id=id_code)
                    if not eDistibutivos.values("id").exists():
                        raise NameError('El código no existe')
                    eDistibutivo = eDistibutivos.first()
                    eCarnets = Carnet.objects.filter(distributivo=eDistibutivo, status=True)
                    data['distributivo'] = eDistibutivo
                #print(eMatricula)
                data['carnet'] = carnet = eCarnets.first()
                data['persona'] = carnet.persona
                return render(request, "p_valida_carnet_digital/view.html", data)
            except Exception as ex:
                return render(request, "p_valida_carnet_digital/error.html", {'msg_error': str(ex), 'title': 'Error al cansultar carnet digital'})


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
