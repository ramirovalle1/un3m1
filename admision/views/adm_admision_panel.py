# -*- coding: UTF-8 -*-
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from bd.models import LogQuery
from decorators import secure_module, last_access
from bd.forms import *
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
import sys
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}

    adduserdata(request, data)
    persona = request.session['persona']

    if request.method == 'POST':
        action = request.POST['action']
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Administración de Nivelación y Admisión'

                menu_panel = [
                    {"url": "/nivelacion_admision/inscripciones_aspirante",
                     "img": "/static/images/iconssga/icon_inscripciones.svg",
                     "title": "Inscripciones de aspirantes",
                     "description": "Administración de inscripciones de aspirantes",
                     },
                    {"url": "/nivelacion_admision/periodo_postulacion",
                     "img": "/static/images/iconssga/icon_periodos_lectivos.svg",
                     "title": "Periodos de postulación",
                     "description": "Administración de periodos de postulación",
                     },
                    {"url": "/nivelacion_admision/test_vocacional",
                     "img": "/static/images/iconssga/icon_actividades_complementarias.svg",
                     "title": "Tests vocacionales",
                     "description": "Administración de test vocacionales",
                     },
                ]
                data['menu_panel'] = menu_panel
                return render(request, "nivelacion_admision/panel.html", data)
            except Exception as ex:
                pass
