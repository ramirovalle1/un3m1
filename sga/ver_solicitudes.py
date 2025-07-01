# -*- coding: latin-1 -*-
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.models import SolicitudAperturaClase
from django.db import transaction

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    departamento = persona.mi_departamento()
    perfilprincipal = request.session['perfilprincipal']
    if perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles Administrativo pueden ingresar al modulo.")
    if not departamento:
        return HttpResponseRedirect("/?info=Solo los perfiles Administrativo con Departamento pueden ingresar al modulo.")
    iddepartamento = departamento.id
    periodo = request.session['periodo']
    inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':
        action = request.POST['action']

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            return HttpResponseRedirect(request.path)
        else:
            hoy = datetime.now().date()
            restardias = (hoy - timedelta(days=2))
            data['title'] = u'Solicitud de Apertura de Clases sin Respuesta'
            if iddepartamento == 10: # VICE ADMINISTRATIVO
                data['solicitudes'] = SolicitudAperturaClase.objects.filter(materia__nivel__periodo=periodo, status=True, fecha_creacion__lt=restardias, observacionrevision='', tiposolicitud__in=[1,2]).order_by('-fecha')
            else:
                if iddepartamento == 2:  # VICE ACADEMICO
                    data['solicitudes'] = SolicitudAperturaClase.objects.filter(materia__nivel__periodo=periodo, status=True, fecha_creacion__lt=restardias, observacionrevision='',tiposolicitud=3).order_by('-fecha')
                else:
                    data['solicitudes'] = None


            return render(request, "ver_solicitudes/view.html", data)