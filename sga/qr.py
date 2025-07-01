# -*- coding: latin-1 -*-
from datetime import datetime

from django.http import HttpResponseRedirect
from django.shortcuts import render
from settings import EMAIL_DOMAIN
from sga.models import Aula, Clase


def aula(request, ida):
    try:
        data = {'title': u'Aula'}
        data['aula'] = miaula = Aula.objects.get(pk=ida)
        data['hoy'] = hoy = datetime.now().date()
        dia = hoy.weekday() + 1
        data['clases'] = Clase.objects.filter(activo=True, aula=miaula, materia__nivel__cerrado=False, dia=dia, inicio__lte=hoy, fin__gte=hoy).order_by('turno__comienza')
        return render(request, "qr/aula.html", data)
    except Exception as ex:
        return HttpResponseRedirect("/")


def qraula(request, ida):
    try:
        data = {'title': u'Aula'}
        data['aula'] = Aula.objects.get(pk=ida)
        data['dominio'] = EMAIL_DOMAIN
        return render(request, "qr/qraula.html", data)
    except Exception as ex:
        return HttpResponseRedirect("/")