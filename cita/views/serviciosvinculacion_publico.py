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
from cita.acciones import *
from cita.models import *
from cita.models import DepartamentoServicio

from poli.forms import RegistroUsuarioExternoForm
from sga.funciones import remover_caracteres_especiales_unicode, generar_nombre, log, notificacion, validarcedula, calculate_username, generar_usuario
from sga.templatetags.sga_extras import encrypt
from utils.filtros_genericos import consultarPersona


@last_access
@transaction.atomic()
def view(request):
    data = {}
    data['currenttime'] = hoy = datetime.now()
    data['next'] = request.GET.get('next', '')
    sistema = request.GET.get('sistema', '')
    if not sistema:
        messages.error(request, 'No se encuentra el sistema al que desea acceder.')
        return redirect('/servicios')
    data['gruposervicio'] = gruposervicio = DepartamentoServicio.objects.filter(tiposistema=sistema, status=True).order_by('-id').first()
    if not gruposervicio:
        messages.error(request, 'No existe el sistema al que desea acceder.')
        return redirect('/servicios')
    data['tiposistema'] = gruposervicio.tiposistema
    data['nombresistema'] = gruposervicio.nombresistema
    data['url_entrada'] = url_entrada = gruposervicio.url_entrada
    data['url_offline'] = f'/sites?sistema={gruposervicio.tiposistema}'
    if 'persona' in request.session:
        return HttpResponseRedirect(url_entrada)
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            # if action == 'politicas':
            #     try:
            #         return render(request, politicas(data))
            #     except Exception as ex:
            #         messages.error(request, str(ex))
            #
            # elif action == 'formativas':
            #     try:
            #         template, data = formativas(data)
            #         return render(request, template, data)
            #     except Exception as ex:
            #         messages.error(request, str(ex))
            #
            # elif action == 'formativa':
            #     try:
            #         template, data = formativa(data, request)
            #         return render(request, template, data)
            #     except Exception as ex:
            #         messages.error(request, str(ex))

            if action == 'serviciosvinculacion':
                try:
                    template, data = serviciosvinculacion(data)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            if action == 'informacionservicio':
                try:
                    template, data = informacionservicio(data, request)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            if action == 'acercanosotros':
                try:
                    template, data = acercanosotros(data)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'terminosvin':
                try:
                    return render(request, terminosvin(data))
                except Exception as ex:
                    messages.error(request, str(ex))
            elif action == 'servicio':
                try:
                    template, data = servicio(data, request)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'responsables':
                try:
                    template, data = responsables(data, request)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'responsable':
                try:
                    template, data = responsable(data, request)
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

            elif action == 'eventos':
                try:
                    template, data = eventos(data, request)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'evento':
                try:
                    template, data = evento(data, request)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['sitio'] = request.GET.get('sistema', None)
                template, data = inicio(data)
                return render(request, template, data)
            except Exception as ex:
                pass

