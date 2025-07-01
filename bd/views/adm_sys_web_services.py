# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sga.commonviews import adduserdata
from django.db import connection, transaction


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
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
                data['title'] = 'Servicios de gratuidad'
                # data['service_soap'] = 'Banco Pacifico'
                return render(request, "adm_sistemas/web_services/view.html", data)
            except Exception as ex:
                pass
