# -*- coding: UTF-8 -*-
import json
import sys
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from faceid.backEnd import FaceRecognition
from faceid.models import PersonTrainFace
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
from django.template.loader import get_template

from sga.funciones import log, MiPaginador
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    # print("ENTRE AL FACE ID")
    if request.method == 'POST':
        action = request.POST['action']

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Demo'
                return render(request, "biometrics/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect(f"/?info={ex.__str__()}")
