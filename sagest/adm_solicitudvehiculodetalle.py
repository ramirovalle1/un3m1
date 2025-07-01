# -*- coding: UTF-8 -*-
import os
import xlwt
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from xlwt import *
from decorators import secure_module
from sagest.forms import SolicitudVehiculo2Form, SolicitudVehiculoDetalleForm, VehiculoUnemiForm
from sagest.models import SolicitudVehiculo, SolicitudVehiculoCantonCerca, SolicitudVehiculoDetalle, VehiculoUnemi, \
    secuencia_codigo
from settings import SITE_STORAGE
from sga.commonviews import adduserdata
from sga.funciones import log, generar_nombre, convertir_fecha
from sga.models import Canton
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
                form = SolicitudVehiculo2Form(request.POST)
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
                                                          departamentosolicitante=form.cleaned_data['departamentosolicitante'],
                                                          tiposolicitud=form.cleaned_data['departamentosolicitante'].tipo,
                                                          administradorgeneral_id=29040,
                                                          directoradministrativo_id=1195,
                                                          estado=3,
                                                          codigo=secuencia_codigo("solicitudvehiculo"))
                    solicitudvehiculo.save(request)
                    # if departamento.tipo == 1:
                    #     mail = ['administrativo@unemi.edu.ec']
                    # else:
                    #     mail = ['academivo@unemi.edu.ec']
                    # fechas = "DEL: " + str(solicitudvehiculo.fechasalida) + " " + str(solicitudvehiculo.horasalida) + " HASTA " + str(solicitudvehiculo.fechallegada) + " " + str(solicitudvehiculo.horaingreso)
                    # send_html_mail("Solicitud Vehiculo", "emails/solicitudvehiculo.html", {'sistema': request.session['nombresistema'], 'motivo': solicitudvehiculo.finalidadviaje, 'departamento': departamento, 'responsable': solicitudvehiculo.responsablegira, 'fechas': fechas }, mail, [])
                    log(u'Registro nuevo Solicitud de Vehiculo por Administrador: %s' % solicitudvehiculo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'detallesolicitud':
            try:
                form = SolicitudVehiculoDetalleForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    arch = request.FILES['archivo']
                    extencion = arch._name.split('.')
                    exte = extencion[1]
                    if arch.size > 5242880:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 5 Mb."})
                    if not exte == 'pdf':
                        return JsonResponse({"result": "bad", "mensaje": u"Solo archivos .pdf"})

                if form.is_valid():
                    solicitudvehiculo = SolicitudVehiculo.objects.get(pk=request.POST['id'])
                    if solicitudvehiculo.solicitudvehiculodetalle_set.values('id').filter(status=True).exists():
                        solicitudvehiculo.solicitudvehiculodetalle_set.filter(status=True).update(status=False)
                    solicitudvehiculodetalle = SolicitudVehiculoDetalle(solicitud=solicitudvehiculo,
                                                                        transporteinstitucional=form.cleaned_data['transporteinstitucional'],
                                                                        vehiculo=form.cleaned_data['vehiculo'],
                                                                        conductor=form.cleaned_data['conductor'],
                                                                        fechainicio=form.cleaned_data['fechainicio'],
                                                                        fechafin=form.cleaned_data['fechafin'],
                                                                        laborable=form.cleaned_data['laborable'],
                                                                        dia=form.cleaned_data['dia'],
                                                                        horadesde=form.cleaned_data['horadesde'],
                                                                        horahasta=form.cleaned_data['horahasta'],
                                                                        observacion=form.cleaned_data['observacion'])
                    solicitudvehiculodetalle.save(request)
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("solicitudvehiculo_", newfile._name)
                        solicitudvehiculodetalle.archivo = newfile
                        solicitudvehiculodetalle.save()
                    log(u'Registro Detalle Solicitud de Vehiculo: %s' % solicitudvehiculodetalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al modificar los datos."})

        if action == 'pdfsolicitud':
            try:
                data = {}
                data['solicitudvehiculo'] = solicitudvehiculo = SolicitudVehiculo.objects.get(pk=request.POST['idsolicitud'])
                data['solicitudvehiculodetalle'] = solicitudvehiculo.solicitudvehiculodetalle_set.filter(status=True)
                if SolicitudVehiculoCantonCerca.objects.values('id').filter(canton=solicitudvehiculo.cantondestino).exists():
                    return conviert_html_to_pdf('adm_solicitudvehiculodetalle/solicitud_pdf.html',
                                                {'pagesize': 'A4',
                                                 'data': data,
                                                 })
                else:
                    return conviert_html_to_pdf('adm_solicitudvehiculodetalle/solicitud_pdf2.html',
                                                {'pagesize': 'A4',
                                                 'data': data,
                                                 })
            except Exception as ex:
                pass

        if action == 'descargar':
            try:
                fechadesde = convertir_fecha(request.POST['fechadesde'])
                fechahasta = convertir_fecha(request.POST['fechahasta'])
                solicitudvehiculodetalle = SolicitudVehiculoDetalle.objects.filter(solicitud__fechasalida__gte=fechadesde, solicitud__fechasalida__lte=fechahasta, status=True, solicitud__status=True, solicitud__estado=3)
                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'solicitud_vehiculo'))
                __author__ = 'Unemi'
                style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                style1 = easyxf(num_format_str='D-MMM-YY')
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')

                ws = wb.add_sheet('Sheetname')
                ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                ws.write(1, 0, "DEPARTAMENTO ADMINISTRATIVO", font_style2)
                ws.write(2, 0, "Fecha Desde: " + request.POST['fechadesde'], font_style2)
                ws.write(3, 0, "Fecha Hasta: " + request.POST['fechahasta'], font_style2)
                nombre = "SOLICITUDVEHICULO_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
                filename = os.path.join(output_folder, nombre)
                ruta = "media/solicitud_vehiculo/" + nombre
                book = xlwt.Workbook()
                columns = [
                    (u"FECHA DESDE", 6000),
                    (u"FECHA HASTA", 6000),
                    (u"CIUDAD", 6000),
                    (u"HORA DESDE", 6000),
                    (u"HORA HASTA", 6000),
                    (u"VEHICULO", 6000),
                    (u"CONDUCTOR", 6000),
                    (u"RESPONSABLE GIRO", 6000),
                    (u"DEPARTAMENTO", 6000),
                ]
                row_num = 4
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]
                row_num = 5
                for r in solicitudvehiculodetalle:
                    campo1 = str(r.solicitud.fechasalida)
                    campo2 = str(r.solicitud.fechallegada)
                    campo3 = r.solicitud.cantondestino.nombre
                    campo4 = str(r.solicitud.horasalida)
                    campo5 = str(r.solicitud.horaingreso)
                    campo6 = r.vehiculo.descripcion
                    campo7 = r.conductor.nombre_completo_inverso()
                    campo8 = r.solicitud.responsablegira.nombre_completo_inverso()
                    campo9 = r.solicitud.departamentosolicitante.nombre

                    ws.write(row_num, 0, campo1, font_style2)
                    ws.write(row_num, 1, campo2, font_style2)
                    ws.write(row_num, 2, campo3, font_style2)
                    ws.write(row_num, 3, campo4, font_style2)
                    ws.write(row_num, 4, campo5, font_style2)
                    ws.write(row_num, 5, campo6, font_style2)
                    ws.write(row_num, 6, campo7, font_style2)
                    ws.write(row_num, 7, campo8, font_style2)
                    ws.write(row_num, 8, campo9, font_style2)

                    row_num += 1
                wb.save(filename)
                # return book
                return JsonResponse({'result': 'ok', 'archivo': ruta})
            except Exception as ex:
                pass

        if action == 'addvehiculo':
            try:
                if VehiculoUnemi.objects.values('id').filter(vehiculo_id=int(request.POST['vehiculo']), status=True).exists():
                    return JsonResponse({"result": "bad", "mensaje": "Registro Repetido, Activo Fijo."})
                vehiculounemi = VehiculoUnemi(vehiculo_id=int(request.POST['vehiculo']),
                                              descripcion=request.POST['descripcion'],
                                              matricula=request.POST['matricula'],
                                              aceite=int(request.POST['aceite']),
                                              kilometraje=int(request.POST['kilometraje']),
                                              estado=int(request.POST['estado']))
                vehiculounemi.save(request)
                log(u'Registro nuevo Vehiculo UNEMI: %s' % vehiculounemi, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'editvehiculo':
            try:
                vehiculounemi = VehiculoUnemi.objects.get(pk=int(request.POST['id']), status=True)

                vehiculounemi.aceite=int(request.POST['aceite'])
                vehiculounemi.kilometraje=int(request.POST['kilometraje'])
                vehiculounemi.estado=int(request.POST['estado'])
                vehiculounemi.descripcion=request.POST['descripcion']
                vehiculounemi.matricula=request.POST['matricula']

                vehiculounemi.save(request)
                log(u'Registro modificado Vehiculo UNEMI: %s' % vehiculounemi, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al editar los datos."})

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addsolicitud':
                try:
                    data['title'] = u'Nuevo Solicitud de Vehiculo'
                    form = SolicitudVehiculo2Form(initial={'cantonsalida': Canton.objects.filter(pk=2)[0]})
                    data['form'] = form
                    # data['personas'] = Persona.objects.filter(status=True, distributivopersona__unidadorganica=departamento, distributivopersona__estadopuesto__id=PUESTO_ACTIVO_ID)
                    return render(request, "adm_solicitudvehiculodetalle/addsolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'detallesolicitud':
                try:
                    data['title'] = u'Detalle Solicitud de Vehiculo'
                    data['solicitudvehiculo'] = solicitudvehiculo = SolicitudVehiculo.objects.get(pk=request.GET['id'])
                    if solicitudvehiculo.solicitudvehiculodetalle_set.values('id').filter(status=True).exists():
                        solicitudvehiculodetalle = solicitudvehiculo.solicitudvehiculodetalle_set.get(status=True)
                        form = SolicitudVehiculoDetalleForm(initial={'transporteinstitucional': solicitudvehiculodetalle.transporteinstitucional,
                                                                      'vehiculo': solicitudvehiculodetalle.vehiculo,
                                                                      'conductor': solicitudvehiculodetalle.conductor,
                                                                      'fechainicio': solicitudvehiculodetalle.fechainicio,
                                                                      'fechafin': solicitudvehiculodetalle.fechafin,
                                                                      'laborable': solicitudvehiculodetalle.laborable,
                                                                      'dia': solicitudvehiculodetalle.dia,
                                                                      'horadesde': str(solicitudvehiculodetalle.horadesde)[0:5],
                                                                      'horahasta': str(solicitudvehiculodetalle.horahasta)[0:5],
                                                                      'observacion': solicitudvehiculodetalle.observacion})
                    else:
                        form = SolicitudVehiculoDetalleForm()
                    data['form'] = form
                    # data['personas'] = Persona.objects.filter(status=True, distributivopersona__unidadorganica=departamento, distributivopersona__estadopuesto__id=PUESTO_ACTIVO_ID)
                    return render(request, "adm_solicitudvehiculodetalle/detallesolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'detalle_solicitud':
                try:
                    data['solicitudvehiculo'] = solicitudvehiculo = SolicitudVehiculo.objects.get(pk=request.GET['cid'])
                    if solicitudvehiculo.solicitudvehiculodetalle_set.values('id').filter(status=True).exists():
                        data['solicitudvehiculodetalle'] = solicitudvehiculo.solicitudvehiculodetalle_set.get(status=True)
                    else:
                        data['solicitudvehiculodetalle'] = None
                    return render(request, 'adm_solicitudvehiculodetalle/detalle_solicitud.html', data)
                except Exception as ex:
                    pass

            if action == 'mantenimientovehiculo':
                try:
                    data['title'] = u'Vehiculos UNEMI'
                    data['vehiculounemis'] = vehiculounemis = VehiculoUnemi.objects.filter(status=True).order_by('-id')
                    data['form2'] = VehiculoUnemiForm()
                    return render(request, "adm_solicitudvehiculodetalle/mantenimientovehiculo.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Solicitudes de Vehiculos - UNEMI'
            data['solicitudvehiculos'] = SolicitudVehiculo.objects.filter(status=True, estado__in=[3,4]).order_by('-id')
            return render(request, 'adm_solicitudvehiculodetalle/view.html', data)
