# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import SolicitudAperturaClaseObservacionForm
from sga.funciones import log
from sga.models import SolicitudAperturaClase


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
    iddepartamento = departamento.id
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']
    if perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles Administrativo pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'observacion':
            try:
                f = SolicitudAperturaClaseObservacionForm(request.POST)
                if f.is_valid():
                    solicitudtodas = SolicitudAperturaClase.objects.get(pk=request.POST['id'])
                    bandera = 0
                    for solicitud in SolicitudAperturaClase.objects.filter(profesor=solicitudtodas.profesor, materia=solicitudtodas.materia, fecha=solicitudtodas.fecha):
                        if solicitud.observacionrevision == '':
                            bandera = 1
                            solicitud.observacionrevision = f.cleaned_data['observacionrevision']
                            solicitud.aprobadorevision = f.cleaned_data['aprobadorevision']
                            solicitud.rechazadorevision = f.cleaned_data['rechazadorevision']
                            solicitud.save(request)
                            log(u'Observación Solicitud Apertura Clase: %s' % solicitud, request, "edit")
                    if bandera == 0:
                        solicitud = SolicitudAperturaClase.objects.get(pk=request.POST['id'])
                        solicitud.observacionrevision = f.cleaned_data['observacionrevision']
                        solicitud.aprobadorevision = f.cleaned_data['aprobadorevision']
                        solicitud.rechazadorevision = f.cleaned_data['rechazadorevision']
                        solicitud.save(request)
                        log(u'Observación Solicitud Apertura Clase: %s' % solicitud, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'observacion':
                try:
                    data['title'] = u'Observación solicitud apertura de clase'
                    data['solicitud'] = solicitud = SolicitudAperturaClase.objects.get(pk=int(request.GET['idsolicitud']))
                    form = SolicitudAperturaClaseObservacionForm(initial={'observacionrevision': solicitud.observacionrevision,
                                                                          'aprobadorevision': solicitud.aprobadorevision,
                                                                          'rechazadorevision': solicitud.rechazadorevision})
                    data['form'] = form
                    return render(request, "observacion_tecnica/observacion.html", data)
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)
        else:
            if iddepartamento == 25:
                data['title'] = u'Observaciones Técnicas Obras Universitarias de las Asistencias por Diferido'
                data['solicitudes'] = SolicitudAperturaClase.objects.filter(materia__nivel__periodo=periodo, tiposolicitud=2, status=True).exclude(tiposolicitud=4).order_by('-fecha')
            else:
                if iddepartamento == 13:
                    data['title'] = u'Observaciones Técnicas Técnologia de las Asistencias por Diferido'
                    data['solicitudes'] = SolicitudAperturaClase.objects.filter(materia__nivel__periodo=periodo, tiposolicitud=1, status=True).exclude(tiposolicitud=4).order_by('-fecha')
                else:
                    data['title'] = u'Observaciones Técnicas Académicas de las Asistencias por Diferido'
                    data['solicitudes'] = SolicitudAperturaClase.objects.filter(materia__nivel__periodo=periodo, tiposolicitud=3, status=True, materia__asignaturamalla__malla__carrera__in=persona.mis_carreras()).exclude(tiposolicitud=4).order_by('-fecha')

            return render(request, "observacion_tecnica/view.html", data)