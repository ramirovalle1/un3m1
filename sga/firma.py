# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from sagest.models import DistributivoPersona
from sga.templatetags.sga_extras import encrypt

@login_required(redirect_field_name='ret', login_url='/loginsagest')
def view(request):
    data = {}
    data['persona']= request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']


            return HttpResponseRedirect(request.path)

        else:
            try:
                data['plantilla'] = ''
                if 'persona' not in request.GET:
                    data['plantilla'] = DistributivoPersona.objects.get(id=int(encrypt(request.GET['plantilla'])))

                return render(request, "th_hojavida/firma.html", data)
            except Exception as ex:
                pass
