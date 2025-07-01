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
from matricula.funciones import valid_intro_module_estudiante
from settings import SITE_STORAGE
from sga.commonviews import adduserdata, obtener_reporte
from sga.models import Matricula, Inscripcion
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsavecertificados
from django.db import connections, transaction

from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    valid, msg_error = valid_intro_module_estudiante(request, 'posgrado')
    if not valid:
        return HttpResponseRedirect(f"/?info={msg_error}")
    try:
        return render(request, "matricula/view.html", data)
    except Exception as ex:
        data['msg_matricula'] = ex.__str__()
        return render(request, "matricula/view.html", data)
