# -*- coding: latin-1 -*-
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from decorators import secure_module, last_access
from django.db import transaction


@login_required(redirect_field_name='ret', login_url='/loginsga')
@last_access
@secure_module
@transaction.atomic()

def view(request):
    data = {}
    data['persona']= request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']
        return HttpResponseRedirect('/?info=Módulo de actualización de datos no se encuentra activo para SGA')
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            return HttpResponseRedirect('/?info=Módulo de actualización de datos no se encuentra activo para SGA')
        else:
            try:
                data['datos'] = ''
                return HttpResponseRedirect('/?info=Módulo de actualización de datos no se encuentra activo para SGA')
            except Exception as ex:
                pass