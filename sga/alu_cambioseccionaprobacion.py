# -*- coding: latin-1 -*-
import json
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from decorators import last_access, secure_module
from sga.commonviews import adduserdata
from sga.funciones import log
from sga.models import CambioInscripcionSeccion


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_administrativo():
        return HttpResponseRedirect("/?info=Solo los perfiles de administrativo pueden ingresar al modulo.")
    carreras = persona.mis_carreras()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'estadosolicitud':
            try:
                solicitud = CambioInscripcionSeccion.objects.get(pk=request.POST['id'])
                inscripcion = solicitud.inscripcion
                solicitud.estado = request.POST['tipo']
                solicitud.responsableaprobacion = persona
                solicitud.fechaprobacion = datetime.now().date()
                solicitud.save(request)
                inscripcion.sesion=solicitud.seccionsolicitada
                inscripcion.save(request)
                if request.POST['tipo'] == '2':
                    log(u'Aprobo solicitud de cambio de sección: %s' % solicitud, request, "edit")
                else:
                    log(u'Rechazo solicitud de cambio de sección: %s' % solicitud, request, "edit")
                return HttpResponse(json.dumps({"result": "ok"}), content_type="application/json")
            except Exception as ex:
                transaction.set_rollback(True)
                return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Error al actualizar los datos."}), content_type="application/json")

        return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Solicitud Incorrecta."}), content_type="application/json")

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'estadosolicitud':
                try:
                    if request.GET['tipo'] == '2':
                        data['title'] = u'Autorizar solicitud - cambio sección'
                    else:
                        data['title'] = u'Rechazar solicitud - cambio sección'
                    data['solicitud'] = CambioInscripcionSeccion.objects.get(pk=request.GET['id'])
                    data['tipo'] = request.GET['tipo']
                    return render(request, "alu_cambiosesionaprobacion/estadosolicitud.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Aprobacio/Rechazo Solicitd Cambio - Sesión'
            data['solicitudes'] = CambioInscripcionSeccion.objects.filter(inscripcion__carrera__in=carreras,status=True).distinct()
            return render(request, "alu_cambiosesionaprobacion/view.html", data)