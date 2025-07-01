# -*- coding: UTF-8 -*-
import random
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.http import HttpResponse
from bd.models import LogQuery
from decorators import secure_module, last_access
from bd.forms import *
from settings import MEDIA_ROOT, MEDIA_URL
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
import sys
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery
import xlwt
from xlwt import *
import io
import xlsxwriter

@login_required(redirect_field_name='ret', login_url='/loginsagest')
# @secure_module
# @last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['title'] = f'Documentación linea grafica'

    if request.method == 'GET':
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

    try:
        if persona.usuario.is_superuser:
            request.session['viewactivo'] = 1
            return render(request, "estandares/vistamenu/vistamenu.html", data)
        else:
            return redirect('/')
    except Exception as ex:
        pass
