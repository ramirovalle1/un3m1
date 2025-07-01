# -*- coding: UTF-8 -*-
import json
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import SolicitudVehiculoForm
from sagest.models import SolicitudVehiculo, SolicitudVehiculoCantonCerca
from sga.commonviews import adduserdata
from sga.funciones import log, variable_valor
from sga.models import Canton, CUENTAS_CORREOS
from sga.tasks import send_html_mail, conectar_cuenta
from sga.funcionesxhtml2pdf import conviert_html_to_pdf


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    departamento = persona.mi_departamento()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsolicitud':
            try:
                form = SolicitudVehiculoForm(request.POST)
                if form.is_valid():
                    solicitudvehiculo = SolicitudVehiculo(cantonsalida=form.cleaned_data['cantonsalida'],
                                                          cantondestino=form.cleaned_data['cantondestino'],
                                                          fechasalida=form.cleaned_data['fechasalida'],
                                                          fechallegada=form.cleaned_data['fechallegada'],
                                                          horasalida=form.cleaned_data['horasalida'],
                                                          horaingreso=form.cleaned_data['horaingreso'],
                                                          finalidadviaje=form.cleaned_data['finalidadviaje'],
                                                          tiempoviaje=form.cleaned_data['tiempoviaje'],
                                                          numeropersonas=form.cleaned_data['numeropersonas'],
                                                          responsablegira=form.cleaned_data['responsablegira'],
                                                          departamentosolicitante=departamento,
                                                          tiposolicitud=departamento.tipo,
                                                          administradorgeneral_id=29040,
                                                          directoradministrativo_id=1195)
                    solicitudvehiculo.save(request)
                    if departamento.tipo == 1:
                        mail = ['administrativo@unemi.edu.ec']
                    else:
                        mail = ['academivo@unemi.edu.ec']
                    mail = ['loyolaromerocarlos@hotmail.com']
                    fechas = "DEL: " + str(solicitudvehiculo.fechasalida) + " " + str(solicitudvehiculo.horasalida) + " HASTA " + str(solicitudvehiculo.fechallegada) + " " + str(solicitudvehiculo.horaingreso)
                    send_html_mail("Solicitud Vehiculo", "emails/solicitudvehiculo.html", {'sistema': request.session['nombresistema'], 'motivo': solicitudvehiculo.finalidadviaje, 'departamento': departamento, 'responsable': solicitudvehiculo.responsablegira, 'fechas': fechas }, mail, [], cuenta=CUENTAS_CORREOS[4][1])
                    log(u'Registro nuevo Solicitud de Vehiculo: %s' % solicitudvehiculo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."}),

        if action == 'editsolicitud':
            try:

                form = SolicitudVehiculoForm(request.POST)
                if form.is_valid():
                    solicitudvehiculo = SolicitudVehiculo.objects.filter(pk=request.POST['id'])[0]
                    solicitudvehiculo.cantonsalida=form.cleaned_data['cantonsalida']
                    solicitudvehiculo.cantondestino=form.cleaned_data['cantondestino']
                    solicitudvehiculo.fechasalida=form.cleaned_data['fechasalida']
                    solicitudvehiculo.fechallegada=form.cleaned_data['fechallegada']
                    solicitudvehiculo.horasalida=form.cleaned_data['horasalida']
                    solicitudvehiculo.horaingreso=form.cleaned_data['horaingreso']
                    solicitudvehiculo.finalidadviaje=form.cleaned_data['finalidadviaje']
                    solicitudvehiculo.tiempoviaje=form.cleaned_data['tiempoviaje']
                    solicitudvehiculo.numeropersonas=form.cleaned_data['numeropersonas']
                    solicitudvehiculo.responsablegira=form.cleaned_data['responsablegira']
                    solicitudvehiculo.administradorgeneral_id = 29040
                    solicitudvehiculo.directoradministrativo_id = 1195
                    # solicitudvehiculo.departamentosolicitante=form.cleaned_data['departamentosolicitante']
                    solicitudvehiculo.save(request)
                    log(u'Registro modificado Solicitud de Vehiculo: %s' % solicitudvehiculo, request, "edit")
                    return HttpResponse(json.dumps({"result": "ok"}), content_type="application/json")
                else:
                     raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al modificar los datos."})

        if action == 'deletesolicitud':
            try:
                solicitudvehiculo = SolicitudVehiculo.objects.filter(pk=request.POST['id'])[0]
                solicitudvehiculo.status=False
                solicitudvehiculo.save(request)
                log(u'Elimino Solicitud de Vehiculo: %s' % solicitudvehiculo, request, "del")
                return JsonResponse({"result": "ok", "id": solicitudvehiculo.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar datos."})

        if action == 'pdfsolicitud':
            try:
                data = {}
                data['solicitudvehiculo'] = solicitudvehiculo = SolicitudVehiculo.objects.get(pk=request.POST['idsolicitud'])
                data['solicitudvehiculodetalle'] = solicitudvehiculo.solicitudvehiculodetalle_set.filter(status=True)
                if SolicitudVehiculoCantonCerca.objects.filter(canton=solicitudvehiculo.cantondestino).exists():
                    return conviert_html_to_pdf('adm_solicitudvehiculo/solicitud_pdf.html',
                                                {'pagesize': 'A4',
                                                 'data': data,
                                                 })
                else:
                    return conviert_html_to_pdf('adm_solicitudvehiculo/solicitud_pdf2.html',
                                                {'pagesize': 'A4',
                                                 'data': data,
                                                 })

            except Exception as ex:
                pass

        return HttpResponse(json.dumps({"result": "bad", "mensaje": "Solicitud Incorrecta."}), content_type="application/json")
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addsolicitud':
                try:
                    data['title'] = u'Nuevo Solicitud de Vehiculo'
                    form = SolicitudVehiculoForm(initial={'cantonsalida': Canton.objects.filter(pk=2)[0]})
                    data['form'] = form
                    # data['personas'] = Persona.objects.filter(status=True, distributivopersona__unidadorganica=departamento, distributivopersona__estadopuesto__id=PUESTO_ACTIVO_ID)
                    return render(request, "adm_solicitudvehiculo/addsolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'editsolicitud':
                try:
                    data['title'] = u'Editar Solicitud de Vehiculo'
                    solicitudvehiculo = SolicitudVehiculo.objects.filter(pk=request.GET['id'])[0]
                    form = SolicitudVehiculoForm(initial={'cantonsalida': solicitudvehiculo.cantonsalida,
                                                          'cantondestino': solicitudvehiculo.cantondestino,
                                                          'fechasalida': solicitudvehiculo.fechasalida,
                                                          'fechallegada': solicitudvehiculo.fechallegada,
                                                          'horasalida': str(solicitudvehiculo.horasalida)[0:5],
                                                          'horaingreso': str(solicitudvehiculo.horaingreso)[0:5],
                                                          'finalidadviaje': solicitudvehiculo.finalidadviaje,
                                                          'tiempoviaje': str(solicitudvehiculo.tiempoviaje)[0:5],
                                                          'numeropersonas': solicitudvehiculo.numeropersonas,
                                                          'responsablegira': solicitudvehiculo.responsablegira,
                                                          'departamentosolicitante': solicitudvehiculo.departamentosolicitante})
                    data['form'] = form
                    data['solicitudvehiculo'] = solicitudvehiculo
                    return render(request, "adm_solicitudvehiculo/editsolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'deletesolicitud':
                try:
                    data['title'] = u'Eliminar Solicitud de Vehiculo'
                    data['solicitudvehiculo'] = SolicitudVehiculo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_solicitudvehiculo/deletesolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'detalle_solicitud':
                try:
                    data['solicitudvehiculo'] = solicitudvehiculo = SolicitudVehiculo.objects.get(pk=request.GET['cid'])
                    if solicitudvehiculo.solicitudvehiculodetalle_set.filter(status=True).exists():
                        data['solicitudvehiculodetalle'] = solicitudvehiculo.solicitudvehiculodetalle_set.get(status=True)
                    else:
                        data['solicitudvehiculodetalle'] = None
                    return render(request, 'adm_solicitudvehiculo/detalle_solicitud.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Solicitudes de Vehiculos'
            data['solicitudvehiculos'] = SolicitudVehiculo.objects.filter(status=True, departamentosolicitante=departamento).order_by('-id')
            return render(request, 'adm_solicitudvehiculo/view.html', data)
