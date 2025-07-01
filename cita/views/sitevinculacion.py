import json
import random
import sys
import calendar
from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template.loader import get_template
from django.shortcuts import render, redirect
from unidecode import unidecode

from cita.funciones import turnosdisponible
from django import forms
from decorators import secure_module
from med.models import PersonaExamenFisico
from poli.forms import PersonaPrimariaForm
from sagest.forms import DatosPersonalesForm, DatosNacimientoForm, DatosDomicilioForm, FamiliarForm, ContactoEmergenciaForm, DatosMedicosForm, PersonaEnfermedadForm, TitulacionPersonaForm
from sagest.models import DistributivoPersona
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import generar_nombre, log, variable_valor, elimina_tildes
from sga.models import Persona, PersonaDocumentoPersonal, PersonaDatosFamiliares, Externo, PersonaEnfermedad, Titulacion, Titulo, CUENTAS_CORREOS, Graduado
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from poli.models import *
from cita.acciones import *
from django.db.models import Q
from cita.models import *

#@login_required(redirect_field_name='ret', login_url='/unemideportes?next=login')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    if 'persona' in request.session:
        url_entrada = request.session['url_entrada']
        return redirect(url_entrada)
    if request.method == 'POST':
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'serviciosvin':
                try:
                    template, data = serviciosvin(data)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

        else:
            data['title'] = 'Servicios Vinculación'
            data['departamentos'] = DepartamentoServicio.objects.filter(status=True)
            template = 'serviciosvinculacion/menuvin.html'
            return render(request, template, data)