# coding=latin-1
import random
import sys
import json
from cgitb import html
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from django.db import connection
from django.db import transaction
from django.db.models import Count, PROTECT, Sum, Avg, Min, Max
from django.db.models.query_utils import Q
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from balcon.models import ProcesoServicio, Solicitud, Agente, Servicio, HistorialSolicitud, \
    RegistroNovedadesExternoAdmision, ConfigInformacionExterno, TipoProcesoServicio
from settings import DEBUG
from sga.funciones import variable_valor, generar_nombre, log, notificacion
from sga.models import LogReporteDescarga, Matricula, MateriaAsignada, Persona, PerfilUsuario, TestSilaboSemanal, \
    TestSilaboSemanalAdmision, LinkMateriaExamen
from moodle import moodle


@transaction.atomic()
def view(request):
    data = {}
    procesoservicio = None
    config = None
    if ConfigInformacionExterno.objects.values("id").filter(activo=True).exists():
        config = ConfigInformacionExterno.objects.filter(activo=True)[0]
        if config.fechaapertura <= datetime.now() and config.fechacierre >= datetime.now():
            procesoservicio = config.informacion.servicio

    if request.method == 'POST':
        action = request.POST['action']

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            return HttpResponseRedirect('/')
        else:
            try:
                data['title'] = u"Registro de novedades"
                data['config'] = config
                data['procesoservicio'] = procesoservicio
                if 'info' in request.GET:
                    data['info'] = request.GET['info']
                return render(request, "p_registro_novedades/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/info=%s' % ex)


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
