# -*- coding: latin-1 -*-
import random

from django.contrib import messages
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from datetime import datetime

from django.template.loader import get_template
from decorators import last_access
from poli.acciones import *
from poli.models import AreaPolideportivo, PoliticaPolideportivo, InstructorPolideportivo, ActividadPolideportivo
from poli.forms import RegistroUsuarioExternoForm
from sga.funciones import remover_caracteres_especiales_unicode, generar_nombre, log, notificacion, validarcedula, calculate_username, generar_usuario
from sga.templatetags.sga_extras import encrypt
from utils.filtros_genericos import consultarPersona


@last_access
@transaction.atomic()
def view(request):
    data = {}
    data['tiposistema'] = 'unemideporte'
    data['nombresistema'] = 'UNEMI DEPORTE'
    data['url_entrada'] = '/unemideporte'
    data['url_offline'] = '/unemideportes'
    data['currenttime'] = hoy = datetime.now()
    data['next'] = request.GET.get('next', '')
    if 'persona' in request.session:
        return HttpResponseRedirect("/unemideporte")
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            if action == 'politicas':
                try:
                    return render(request, politicas(data))
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'actividades':
                try:
                    template, data = actividades(data, request)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'actividad':
                try:
                    template, data = actividad(data, request)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'areas':
                try:
                    template, data = areas(data)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'area':
                try:
                    template, data = area(data, request)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'instructores':
                try:
                    template, data = instructores(data, request)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'instructor':
                try:
                    template, data = instructor(data, request)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'noticias':
                try:
                    template, data = noticias(data, request)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'noticia':
                try:
                    template, data = noticia(data, request)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            return HttpResponseRedirect(request.path)
        else:
            try:
                template, data = view_inicio(data)
                return render(request, template, data)
            except Exception as ex:
                pass
