# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from django.db import transaction

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    if request.method == 'POST':

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data = {}
        data['title'] = u'Listado de backups de la base de datos'
        adduserdata(request, data)
        data['dia_actual'] = datetime.now().isoweekday()
        data['dias'] = range(1, 8)
        return render(request, "databasebackup/view.html", data)