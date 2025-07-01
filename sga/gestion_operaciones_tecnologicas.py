# -*- coding: latin-1 -*-
import json
from itertools import count
import random
from django.contrib.auth.decorators import login_required
from django.db import transaction
from sga.templatetags.sga_extras import encrypt
from django.db.models import Sum
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
from sga.commonviews import obtener_reporte, adduserdata
from sga.forms import ActextracurricularForm, RegistrarCertificadoForm, InscripcionCursoProsgradoForm
from sga.funciones import MiPaginador, log, variable_valor
from sga.models import Persona, Provincia, Externo, Matricula, RecordAcademico, ModuloGrupo, Modulo
from settings import ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID

from sga.tasks import send_html_mail, conectar_cuenta

IDS_MODULOS_OPERACIONES = [451, 462, 487, 491, 492, 385, 508, 509, 522]

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']


            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Operaciones tecnológicas'
                modulos = []
                misgrupos = mis_grupos(persona)
                modulos = mis_modulos(misgrupos, IDS_MODULOS_OPERACIONES)
                data['modulos2'] = modulos
                return render(request, "gestion_operaciones/panel.html", data)
            except Exception as ex:
                pass

def mis_grupos(persona):
    return ModuloGrupo.objects.filter(grupos__in=persona.usuario.groups.all()).exclude(grupos__in=[ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID]).distinct()


def mis_modulos(misgrupos, idsmodulos):
    return Modulo.objects.values("id", "url", "icono", "nombre", "descripcion").filter(Q(modulogrupo__in=misgrupos), activo=True, submodulo=True, pk__in=idsmodulos).distinct().order_by('nombre')
