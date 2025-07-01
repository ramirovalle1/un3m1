# -*- coding: UTF-8 -*-
import json
import os
from math import ceil

import PyPDF2
from datetime import time
from decimal import Decimal

import requests
from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
import time as pausaparaemail
from xlwt import easyxf, XFStyle, Workbook
import random
from decorators import secure_module
from settings import SITE_STORAGE, ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID
from sga.commonviews import adduserdata
from sga.models import Profesor, Administrativo, Inscripcion, Externo, Persona, ModuloGrupo, Modulo
from django.template import Context


from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt

from django.core.cache import cache

IDS_MODULOS_CONVOCATORIAS = [381, 430, 423, 477, 495]
IDS_MODULOS_NO_AGRUPADOS = [510, 531, 554, 558]

@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']

    es_profesor = perfilprincipal.es_profesor()
    es_externo = perfilprincipal.es_externo()
    es_administrativo = perfilprincipal.es_administrativo()

    if es_externo and request.session['tiposistema'] != 'sga':
        request.session['tiposistema'] = 'sga'

    if not es_profesor and not es_externo and not es_administrativo:
        return HttpResponseRedirect("/?info=El Módulo está disponible para docentes y administrativos.")

    permiso_convocatorias = tiene_acceso_convocatorias(persona, es_profesor, es_administrativo, es_externo)
    permiso_no_agrupados = tiene_acceso_modulos_no_agrupados(persona, es_profesor, es_administrativo, es_externo)

    if not permiso_convocatorias and not permiso_no_agrupados:
        return HttpResponseRedirect("/?info=Usted no tiene asignado permisos a los módulos de la Gestión de Investigación.")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'accionpost':
            try:
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'metricas':
                try:
                    data['title'] = u'Métricas'

                    return render(request, "pro_investigacion/viewcapacitacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'capacitaciones':
                try:
                    data['title'] = u'Capacitaciones Especializadas'

                    return render(request, "pro_investigacion/viewcapacitacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'convocatorias':
                try:
                    data['title'] = u'Convocatorias'
                    modulos = []
                    misgrupos = mis_grupos(persona, es_profesor, es_administrativo, es_externo)

                    for modulo in mis_modulos(misgrupos, IDS_MODULOS_CONVOCATORIAS, True):
                        modulo = {
                            "id": modulo['id'],
                            "url": modulo['url'],
                            "icono": modulo['icono'],
                            "nombre": modulo['nombre'],
                            "descripcion": modulo['descripcion']
                        }
                        modulos.append(modulo)

                    data['modulos2'] = modulos
                    data['enlaceatras'] = "/pro_investigacion"

                    return render(request, "pro_investigacion/panel.html", data)
                except Exception as ex:
                    pass

            elif action == 'buzon':
                try:
                    data['title'] = u'Buzón de Sugerencias'

                    return render(request, "pro_investigacion/viewcapacitacion.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Investigación'
                modulos = []

                if permiso_convocatorias:
                    modulo = {
                        "id": 0,
                        "url": "pro_investigacion?action=convocatorias",
                        "icono": "/static/images/iconssga/icon_articulos.svg",
                        "nombre": "Convocatorias",
                        "descripcion": "Becas, Proyectos y Ponencias",
                    }
                    modulos.append(modulo)

                if permiso_no_agrupados:
                    misgrupos = mis_grupos(persona, es_profesor, es_administrativo, es_externo)

                    for modulo in mis_modulos(misgrupos, IDS_MODULOS_NO_AGRUPADOS, True):
                        modulo = {
                            "id": modulo['id'],
                            "url": modulo['url'],
                            "icono": modulo['icono'],
                            "nombre": modulo['nombre'],
                            "descripcion": modulo['descripcion']
                        }
                        modulos.append(modulo)

                data['modulos2'] = modulos
                data['enlaceatras'] = "/"
                return render(request, "pro_investigacion/panel.html", data)
            except Exception as ex:
                pass


def tiene_acceso_produccion_cientifica(persona, es_profesor, es_administrativo, es_externo):
    if es_profesor or es_administrativo:
        misgrupos = mis_grupos(persona, es_profesor, es_administrativo, es_externo)
        accesomodulos = True if mis_modulos(misgrupos, IDS_MODULOS_PRODUCCION_CIENTIFICA, False) else False
        return accesomodulos
    else:
        return False


def tiene_acceso_convocatorias(persona, es_profesor, es_administrativo, es_externo):
    misgrupos = mis_grupos(persona, es_profesor, es_administrativo, es_externo)
    accesomodulos = True if mis_modulos(misgrupos, IDS_MODULOS_CONVOCATORIAS, True) else False
    return accesomodulos


def tiene_acceso_modulos_no_agrupados(persona, es_profesor, es_administrativo, es_externo):
    misgrupos = mis_grupos(persona, es_profesor, es_administrativo, es_externo)
    accesomodulos = True if mis_modulos(misgrupos, IDS_MODULOS_NO_AGRUPADOS, True) else False
    return accesomodulos


def mis_grupos(persona, es_profesor, es_administrativo, es_externo):
    if es_profesor:
        return ModuloGrupo.objects.filter(grupos__in=[PROFESORES_GROUP_ID]).distinct()
    elif es_administrativo:
        return ModuloGrupo.objects.filter(grupos__in=[13]).distinct()
    else:
        idsgrupos = []
        if persona.es_evaluador_externo_proyectos_investigacion():
            idsgrupos.append(335)
        if persona.es_evaluador_externo_obras_relevancia():
            idsgrupos.append(456)
        if persona.es_integrante_externo_proyecto_investigacion():
            idsgrupos.append(444)
        return ModuloGrupo.objects.filter(grupos__in=idsgrupos).distinct()


def mis_modulos(misgrupos, idsmodulos, es_submodulo):
    return Modulo.objects.values("id", "url", "icono", "nombre", "descripcion").filter(Q(modulogrupo__in=misgrupos), activo=True, submodulo=es_submodulo, pk__in=idsmodulos).distinct().order_by('nombre')


