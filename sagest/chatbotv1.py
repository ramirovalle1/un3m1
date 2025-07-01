# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sagest.forms import ResolucionForm
from sagest.models import Resoluciones, TipoResolucion, PersonaRespuestaChatBot
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre, convertir_fecha


# @login_required(redirect_field_name='ret', login_url='/loginsagest')
# @secure_module
# @last_access
@transaction.atomic()
def view(request):
    data = {}
    # adduserdata(request, data)
    # persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']


            return HttpResponseRedirect(request.path)

        else:
            try:
                # data['title'] = u'ENCUESTA DE INGRESO A LOS PREDIOS DE LA UNEMI'
                # if PersonaRespuestaChatBot.objects.filter(status=True, persona=persona).exist():
                #     pass
                # else:
                return render(request, "chatbotv1/view.html", data)
            except Exception as ex:
                pass