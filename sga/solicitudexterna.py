# -*- coding: latin-1 -*-
import json
import sys
from decimal import Decimal
from itertools import count
import random
from PIL.ImageOps import _lut
from django.contrib import messages
from django.contrib.auth.decorators import login_required
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
# from posgrado.forms import AdmiPeriodoForm
from sga.forms import SolicitudExternoForm,ClienteExternoForm
from sagest.models import TipoOtroRubro, Rubro, CapPeriodoIpec, CapEventoPeriodoIpec, CapInscritoIpec, CuentaBanco
from sga.commonviews import obtener_reporte
# from sga.forms import ActextracurricularForm, RegistrarCertificadoForm, InscripcionCursoProsgradoForm
from sga.funciones import MiPaginador, log, variable_valor, generar_nombre, convertir_fecha
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import Persona, Provincia, Externo, Matricula, RecordAcademico, CUENTAS_CORREOS, miinstitucion

# @login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


@last_access
@transaction.atomic()
def view(request):
    data = {}
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'addpersona':
                try:
                    with transaction.atomic():
                        form = ClienteExternoForm(request.POST)
                        if form.is_valid():
                            personaex = Persona(nombres=form.cleaned_data['nombres'],
                                              apellido1=form.cleaned_data['apellido1'],
                                              apellido2=form.cleaned_data['apellido2'],
                                              nacimiento=form.cleaned_data['nacimiento'],
                                              sexo=form.cleaned_data['sexo'],
                                              sector=form.cleaned_data['sector'],
                                              direccion=form.cleaned_data['direccion'],
                                              direccion2=form.cleaned_data['direccion2'],
                                              num_direccion=form.cleaned_data['num_direccion'],
                                              telefono=form.cleaned_data['telefono'],
                                              email=form.cleaned_data['email'],
                                              )
                            personaex.save()
                            tipo = int(request.POST['tipoident'])
                            if tipo == 1:
                                personaex.cedula = form.cleaned_data['cedula']
                            else:
                                personaex.pasaporte = form.cleaned_data['cedula']
                            personaex.save()



                                # messages.success(request, '<i class="fa fa-check-circle"></i> {} SU COMPROBANTE DE {} FUE REGISTRADO'.format(nombrepersona.upper(), comprobante.get_tipocomprobante()))
                            return JsonResponse({"result": True, "cedula":"0603972456","tipo":tipo, "mensaje": 'Datos guardados correctamente.'}, safe=False)
                                # return JsonResponse({"result": True, "to": '/purl',}, safe=False)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": False, "mensaje": "Complete los datos requeridos."}, safe=False)
                except Exception as ex:
                    mensajeerror = "{} - {}".format(ex, 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    # messages.error(request, mensajeerror)
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "mensaje": "Intentelo más tarde.", "mensajeerror": mensajeerror}, safe=False)

            if action == 'segmento':
                try:
                    datospersona = None
                    tipoiden = int(request.POST['tipoiden'])
                    documento = request.POST['cedula'].strip()
                    if Persona.objects.filter(cedula=documento).exists():
                        datospersona = Persona.objects.get(cedula=documento)
                    if Persona.objects.filter(pasaporte=documento).exists():
                        datospersona = Persona.objects.get(pasaporte=documento)
                    if not datospersona:
                        template = get_template("solicitudexterna/segmentoinscripcion.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content})
                        # return JsonResponse({"result": "bad", "mensaje": u"Usted no se encuentra registrado"})
                    data['datospersona'] = datospersona
                    if tipoiden == 1:
                        data['txtdocumento'] = 'Cédula'
                        data['documento'] = datospersona.cedula
                    elif tipoiden == 2:
                        data['txtdocumento'] = 'Pasaporte'
                        data['documento'] = datospersona.pasaporte
                    template = get_template("solicitudexterna/segmento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

            if action == 'addsolicitud':
                try:
                    datospersona = None
                    tipoiden = int(request.POST['tipoiden'])
                    documento = request.POST['cedula'].strip()
                    data['form2'] = form = ClienteExternoForm()
                    if Persona.objects.filter(cedula=documento).exists():
                        datospersona = Persona.objects.get(cedula=documento)
                    if Persona.objects.filter(pasaporte=documento).exists():
                        datospersona = Persona.objects.get(pasaporte=documento)
                    if not datospersona:
                        data['form2'] = form = ClienteExternoForm()
                        return JsonResponse({"result": "bad", "mensaje": u"Usted no se encuentra registrado"})
                    data['datospersona'] = datospersona
                    if tipoiden == 1:
                        data['txtdocumento'] = 'Cédula'
                        data['documento'] = datospersona.cedula
                    elif tipoiden == 2:
                        data['txtdocumento'] = 'Pasaporte'
                        data['documento'] = datospersona.pasaporte
                    template = get_template("solicitudexterna/addsolicitante.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'buscarnombrerubros':
                try:
                    persona = int(encrypt(request.GET['persona']))
                    q = request.GET['q'].upper().strip()
                    per = Rubro.objects.filter(persona_id=persona, status=True, cancelado=False).filter(nombre__icontains=q).distinct('nombre')[:15]
                    data = {"result": "ok", "results": [{"id": x.id, "nombre": str(x.nombre)} for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'addsolicitante':
                try:
                    form = ClienteExternoForm()
                    data['form2'] = form
                    template = get_template("solicitudexterna/addsolicitante.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'addpersona':
                try:
                    form = ClienteExternoForm()
                    data['form2'] = form
                    template = get_template("solicitudexterna/addpersona.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Registrar certificado'
                data['currenttime'] = datetime.now()
                hoy = datetime.now().date()
                data['cursos'] = CapEventoPeriodoIpec.objects.filter(status=True)
                return render(request, "solicitudexterna/solicitud.html", data)
            except Exception as ex:
                pass