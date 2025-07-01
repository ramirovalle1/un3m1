# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import SolicitudVehiculoObservacionForm
from sagest.models import SolicitudVehiculo, secuencia_codigo
from sga.commonviews import adduserdata
from sga.funciones import log, variable_valor
from sga.models import CUENTAS_CORREOS
from sga.tasks import send_html_mail, conectar_cuenta


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'envioaprobacion':
            try:
                solicitudvehiculo = SolicitudVehiculo.objects.get(pk=request.POST['id'])
                solicitudvehiculo.estado=2
                solicitudvehiculo.envioaprobacion=persona
                solicitudvehiculo.save(request)
                mail = ['rectorado@unemi.edu.ec']
                mail = ['loyolaromerocarlos@hotmail.com']
                fechas = "DEL: " + str(solicitudvehiculo.fechasalida) + " " + str(solicitudvehiculo.horasalida) + " HASTA " + str(solicitudvehiculo.fechallegada) + " " + str(solicitudvehiculo.horaingreso)
                send_html_mail("Solicitud Vehiculo", "emails/solicitudvehiculoenvioaprobacion.html", {'sistema': request.session['nombresistema'], 'motivo': solicitudvehiculo.finalidadviaje, 'departamento': solicitudvehiculo.departamentosolicitante, 'responsable': solicitudvehiculo.responsablegira, 'fechas': fechas}, mail, [], cuenta=CUENTAS_CORREOS[4][1])
                log(u'Envio para aprobación solicitud de vehiculo: %s' % solicitudvehiculo, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos."})

        if action == 'aprobacion':
            try:
                solicitudvehiculo = SolicitudVehiculo.objects.get(pk=request.POST['id'])
                solicitudvehiculo.aprobado = persona
                solicitudvehiculo.estado=3
                solicitudvehiculo.codigo = secuencia_codigo("solicitudvehiculo")
                solicitudvehiculo.save(request)
                mail = solicitudvehiculo.responsablegira.emails()
                # mail = ['loyolaromerocarlos@hotmail.com']
                fechas = "DEL: " + str(solicitudvehiculo.fechasalida) + " " + str(solicitudvehiculo.horasalida) + " HASTA " + str(solicitudvehiculo.fechallegada) + " " + str(solicitudvehiculo.horaingreso)
                send_html_mail("Solicitud Vehiculo", "emails/solicitudvehiculoaprobacion.html", {'sistema': request.session['nombresistema'], 'motivo': solicitudvehiculo.finalidadviaje, 'departamento': solicitudvehiculo.departamentosolicitante, 'responsable': solicitudvehiculo.responsablegira, 'fechas': fechas}, mail, [], cuenta=CUENTAS_CORREOS[4][1])
                log(u'Aprobo solicitud de vehiculo: %s' % solicitudvehiculo, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos."})

        if action == 'cancelacion':
            try:
                form = SolicitudVehiculoObservacionForm(request.POST)
                if form.is_valid():
                    solicitudvehiculo = SolicitudVehiculo.objects.get(pk=request.POST['id'])
                    solicitudvehiculo.cancelado = persona
                    solicitudvehiculo.motivocancelado = form.cleaned_data['observacion']
                    solicitudvehiculo.estado=4
                    solicitudvehiculo.save(request)
                    mail = solicitudvehiculo.responsablegira.emails()
                    mail = ['loyolaromerocarlos@hotmail.com']
                    fechas = "DEL: " + str(solicitudvehiculo.fechasalida) + " " + str(solicitudvehiculo.horasalida) + " HASTA " + str(solicitudvehiculo.fechallegada) + " " + str(solicitudvehiculo.horaingreso)
                    send_html_mail("Solicitud Vehiculo", "emails/solicitudvehiculocancelacion.html", {'sistema': request.session['nombresistema'],'motivo': solicitudvehiculo.finalidadviaje,'departamento': solicitudvehiculo.departamentosolicitante, 'responsable': solicitudvehiculo.responsablegira, 'fechas': fechas, 'motivocancelacion': solicitudvehiculo.motivocancelado, 'canceladopor' : solicitudvehiculo.cancelado}, mail, [], cuenta=CUENTAS_CORREOS[4][1])
                    log(u'Cancelo solicitud de vehiculo: %s' % solicitudvehiculo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos."})

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'envioaprobacion':
                try:
                    data['title'] = u'Envio para Aprobación'
                    data['solicitudvehiculo'] = SolicitudVehiculo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_solicitudvehiculoaprobacion/envioaprobacion.html", data)
                except Exception as ex:
                    pass

            if action == 'aprobacion':
                try:
                    data['title'] = u'Aprobación'
                    data['solicitudvehiculo'] = SolicitudVehiculo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_solicitudvehiculoaprobacion/aprobacion.html", data)
                except Exception as ex:
                    pass

            if action == 'cancelacion':
                try:
                    data['title'] = u'Cancelación'
                    data['form'] = SolicitudVehiculoObservacionForm()
                    data['solicitudvehiculo'] = SolicitudVehiculo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_solicitudvehiculoaprobacion/cancelacion.html", data)
                except Exception as ex:
                    pass

            if action == 'detalle_solicitud':
                try:
                    data['solicitudvehiculo'] = solicitudvehiculo = SolicitudVehiculo.objects.get(pk=request.GET['cid'])
                    if solicitudvehiculo.solicitudvehiculodetalle_set.filter(status=True).exists():
                        data['solicitudvehiculodetalle'] = solicitudvehiculo.solicitudvehiculodetalle_set.get(status=True)
                    else:
                        data['solicitudvehiculodetalle'] = None
                    return render(request, 'adm_solicitudvehiculoaprobacion/detalle_solicitud.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Verificación - Aprobación Solicitud de Vehiculos'
            if request.user.has_perm("sagest.solicitud_vehiculo_rectorado"):
                tiposolicitud = [1,2]
                estado = [2,3]

                tiposolicitud2 = []
                estado2 = []

                tiposolicitud_aux = 1
            else:
                if request.user.has_perm("sagest.solicitud_vehiculo_administrativo"):
                    tiposolicitud = [1]
                    estado = [1,2,3]

                    tiposolicitud2 = [1, 2]
                    estado2 = [2, 3]

                    tiposolicitud_aux = 2
                else:
                    tiposolicitud = [2]
                    estado = [1]

                    tiposolicitud2 = [1,2]
                    estado2 = [3]

                    tiposolicitud_aux = 3
            data['tiposolicitud'] = tiposolicitud_aux
            data['solicitudvehiculos'] = SolicitudVehiculo.objects.filter((Q(estado__in=estado2 ,tiposolicitud__in=tiposolicitud2) | Q(estado__in=estado ,tiposolicitud__in=tiposolicitud) ) ,status=True).order_by('-id')
            return render(request, 'adm_solicitudvehiculoaprobacion/view.html', data)
