# -*- coding: UTF-8 -*-
import sys
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from decorators import secure_module
from sga.commonviews import adduserdata
from django.shortcuts import render, redirect
from .forms import AuditoriaInformaticaForm
from .models import Auditoria
from django.utils import timezone
from django.template.loader import get_template
from sga.funciones import log
from sga.templatetags.sga_extras import encrypt

@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()

def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['title'] = u'Auditorías'

    if request.method == 'POST':
        pass
    else:
        if Auditoria.objects.all().exists():
            data['registros'] = Auditoria.objects.all()
        return render(request,'adm_auditoria/view.html', data)