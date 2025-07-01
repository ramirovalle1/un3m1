# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.funciones import convertir_fecha
from sga.models import Sede


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    data['title'] = u'Distributivo de aulas para el día'
    if request.method == 'POST':

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'disponibles':
                try:
                    data['sedes'] = Sede.objects.all()
                    data['fecha'] = convertir_fecha(request.GET['fecha'])
                    return render(request, "cons_distributivo/aulas.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            if not request.session['periodo'].visible:
                return HttpResponseRedirect("/?info=Periodo Inactivo.")
            data['title'] = u'Distributivo de aulas'
            data['fecha'] = datetime.now().date()
            return render(request, "cons_distributivo/view.html", data)