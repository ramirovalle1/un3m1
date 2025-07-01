# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import SolicitudAperturaClaseAsignacionForm
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
    # iddepartamento = persona.mi_departamento().id
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']
    if perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de Administrativo pueden ingresar al modulo.")
    # inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'asignacion':
            try:
                f = SolicitudAperturaClaseAsignacionForm(request.POST)
                if f.is_valid():
                    solicitudtodas = SolicitudAperturaClase.objects.get(pk=request.POST['id'])
                    for solicitud in SolicitudAperturaClase.objects.filter(profesor=solicitudtodas.profesor, materia=solicitudtodas.materia, fecha=solicitudtodas.fecha):
                        solicitud.aula = f.cleaned_data['aula']
                        solicitud.trabajador = f.cleaned_data['trabajador']
                        solicitud.observacionrevision = f.cleaned_data['observacion']
                        solicitud.save(request)
                        log(u'Asignación Aula trabajador - Solicitud Apertura Clase: %s' % solicitud, request, "edit")
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

            if action == 'asignacion':
                try:
                    data['title'] = u'Asignación solicitud apertura de clase'
                    data['solicitud'] = solicitud = SolicitudAperturaClase.objects.get(pk=int(request.GET['idsolicitud']))
                    form = SolicitudAperturaClaseAsignacionForm(initial={'aula': solicitud.aula,
                                                                          'estadorevision': solicitud.trabajador})
                    data['form'] = form
                    return render(request, "asignacion_aula/asignacion.html", data)
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Asignación de Aulas y Trabajadores - Asistencias por Diferido'
            data['solicitudes'] = SolicitudAperturaClase.objects.filter(materia__nivel__periodo=periodo, status=True, tiposolicitud=4).order_by('-fecha')

            return render(request, "asignacion_aula/view.html", data)