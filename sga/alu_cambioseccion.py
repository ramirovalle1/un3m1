# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import last_access, secure_module
from sga.commonviews import adduserdata
from sga.forms import CambioInscripcionSeccionForm
from sga.funciones import log, generar_nombre
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
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsolicitud':
            try:
                f = CambioInscripcionSeccionForm(request.POST, request.FILES)
                if f.is_valid():
                    solicitud = CambioInscripcionSeccion(fecha=datetime.now().date(),
                                                         inscripcion=inscripcion,
                                                         seccionactual=inscripcion.sesion,
                                                         periodo=periodo,
                                                         seccionsolicitada=f.cleaned_data['seccionsolicitada'],
                                                         motivo=f.cleaned_data['motivo'],
                                                         estado=1)

                    solicitud.save()
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("cambioseccion_", newfile._name)
                        solicitud.archivo = newfile
                        solicitud.save()
                        log(u'Adiciono solicitud cambio sección: %s' % solicitud, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos, tipo de archivo incorrecto."})

        if action == 'delsolicitud':
            try:
                solicitud = CambioInscripcionSeccion.objects.get(pk=request.POST['id'])
                solicitud.delete()
                log(u'Elimino solicitud de cambio de sección: %s' % solicitud, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addsolicitud':
                try:
                    data['title'] = u'Nueva solicitud cambio sección'
                    data['inscripcion'] = inscripcion
                    form = CambioInscripcionSeccionForm()
                    data['form'] = form
                    return render(request, "alu_cambiosesion/addsolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'delsolicitud':
                try:
                    data['title'] = u'Eliminar solicitud cambio sección'
                    data['solicitud'] = CambioInscripcionSeccion.objects.get(pk=request.GET['id'])
                    return render(request, "alu_cambiosesion/delsolicitud.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Solicitd Cambio - Sesión'
            data['inscripcion'] = inscripcion
            data['cantidad'] = CambioInscripcionSeccion.objects.values('id').filter(periodo=periodo, inscripcion=inscripcion, status=True).count()
            data['solicitudes'] = CambioInscripcionSeccion.objects.filter(periodo=periodo, inscripcion=inscripcion, status=True).distinct()
            return render(request, "alu_cambiosesion/view.html", data)