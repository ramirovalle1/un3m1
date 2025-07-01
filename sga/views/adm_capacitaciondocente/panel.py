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
    periodo = request.session['periodo']
    puede_ingresar = False
    grupos = []
    if persona.usuario.is_superuser:
        puede_ingresar = True
        grupos = [1, 2, 3, 4, 5]
    else:
        if persona.grupo_evaluacion():
            puede_ingresar = True
            grupos.append(1)
        if persona.es_responsablecoordinacion(periodo):
            # DECANO DE FACULTAD
            puede_ingresar = True
            grupos.append(2)
        if persona.es_coordinadorcarrera(periodo):
            # DIRECTOR DE CARRERA
            puede_ingresar = True
            grupos.append(3)
        if persona.distributivopersona_set.values("id").filter(denominacionpuesto_id__in=[70, 51, 795], estadopuesto_id=1, status=True).exists():
            # TESORERA GENERAL [70, 51]
            # VICERRECTOR ACADEMICO [795]
            puede_ingresar = True
            grupos.append(4)
            grupos.append(5)

    if puede_ingresar is False:
        return HttpResponseRedirect("/?info=Este módulo solo es para uso de la perfeccionamiento académico o autoridades académicas.")

    if request.method == 'POST':
        action = request.POST['action']
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Perfeccionamiento académico'
                data['subtitle'] = 'Administración de solicitudes, eventos'
                menu_panel = []
                for grupo in grupos:
                    if grupo in [1]:
                        menu_panel.append({"url": "/adm_capacitaciondocente/gestion",
                                           "img": "/static/images/iconssga/icon_aprobacion_capacitacion.svg",
                                           "title": "Administración de eventos",
                                           "description": "Gestionar periodos de ventos",
                                           })
                    if grupo in [1, 2, 3]:
                        menu_panel.append({"url": "/adm_capacitaciondocente/formulario",
                                           "img": "/static/images/iconssga/icon_consulta_de_asistencia.svg",
                                           "title": "Registro de identificación de necesidades",
                                           "description": "Gestionar formulario de registro de identificación de necesidades",
                                           })
                unique_menu_panel = []
                seen = set()
                for menu in menu_panel:
                    menu_tuple = tuple(menu.items())
                    if menu_tuple not in seen:
                        unique_menu_panel.append(dict(menu_tuple))
                        seen.add(menu_tuple)
                data['menu_panel'] = unique_menu_panel
                return render(request, "adm_capacitaciondocente/panel.html", data)
            except Exception as ex:
                return HttpResponseRedirect(f"/?info={ex.__str__()}")
