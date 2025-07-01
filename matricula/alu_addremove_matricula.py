# -*- coding: latin-1 -*-
import os
from datetime import datetime
import code128
import pyqrcode
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from settings import SITE_STORAGE
from sga.commonviews import adduserdata, obtener_reporte
from sga.models import Matricula, Inscripcion
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsavecertificados
from django.db import connections
from django.db import transaction

from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion

    try:
        if inscripcion.coordinacion.id == 9:
            return HttpResponseRedirect("/alu_addremove_matricula/admision")
        elif inscripcion.coordinacion.id in [7, 10]:
            return HttpResponseRedirect("/alu_addremove_matricula/posgrado")
        elif inscripcion.coordinacion.id in [1, 2, 3, 4, 5]:
            return HttpResponseRedirect("/alu_addremove_matricula/pregrado")
        return HttpResponseRedirect(f"/info=No tiene definido una coordinación valida, favor contactarse con la coordinación de la carrera")
    except Exception as ex:
        return HttpResponseRedirect("/?info=%s" % ex)
