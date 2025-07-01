# -*- coding: latin-1 -*-
from datetime import datetime, date, timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template

from core.choices.models.sagest import MY_ESTADO_SOLICITUD_EQUIPO_COMPUTO
from decorators import secure_module, last_access
from sagest.forms import SolicitudPrestamoECForm
from sagest.models import SeccionDepartamento, SolicitudEquipoComputo, TerminosCondicionesEquipoComputo, \
    ConfiguracionEquipoComputo, HistorialSolicitudEC
from sga.commonviews import adduserdata
from sga.forms import ReservasCraiSolicitarForm, ReservasCraiSolicitarDetalleForm, \
    SolicitudOtraCapacitacionForm, BuzonMundoCraiForm
from sga.funciones import log, convertir_hora, convertir_fecha, tituloinstitucion, MiPaginador
from sga.models import MESES_CHOICES, ActividadesMundoCrai, ActividadesMundoCraiDetalle, NoticiasMundoCrai, \
    ContadorActividadesMundoCrai, InscripcionCapacitacionesCrai, CapacitacionesCrai, ReservasCrai, CUENTAS_CORREOS, \
    SolicitudOtrasCapacitacionesCrai, EncuestaInscripcionCapacitacionesCrai, \
    RespuestaEncuestaInscripcionCapacitacionesCrai, PreguntasEncuestaCapacitacionesCrai, BuzonMundoCrai, Club, \
    InscripcionClub, Coordinacion
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt
import random
import string
import xlsxwriter
import io


def controlar_horas(fecha, horadesde, horahasta, salacrai):
    if ReservasCrai.objects.filter(fecha=fecha, salacrai=salacrai, horadesde__lte=horadesde, horahasta__gte=horadesde, status=True).exists():
        return True
    if ReservasCrai.objects.filter(fecha=fecha, salacrai=salacrai, horadesde__gte=horadesde, horahasta__gte=horadesde, horadesde__lte=horahasta, horahasta__lte=horahasta, status=True).exists():
        return True
    return False


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodosesion = request.session['periodo']
    # if perfilprincipal.es_administrativo():
    #     return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes y docentes pueden ingresar al modulo.")
    # adminitrativo = False
    # estudiante = False
    # docente = False
    # if perfilprincipal.es_administrativo():
    #     adminitrativo = True
    # if perfilprincipal.es_estudiante():
    #     estudiante = True
    # if perfilprincipal.es_profesor():
    #     docente = True

    inscripcion = perfilprincipal.inscripcion
    profesor = perfilprincipal.profesor
    administrativo = perfilprincipal.administrativo
    if profesor:
        tipoingreso = 1
    if inscripcion:
        tipoingreso = 2
    if administrativo:
        tipoingreso = 3

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'contar':
                try:
                    idregistro = int(request.POST['idr'])
                    hoy = datetime.now().date()
                    contar = ContadorActividadesMundoCrai(actividadesmundocraiprincipal_id=idregistro,
                                                          tipoingreso=tipoingreso,
                                                          fecha=hoy)
                    contar.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

            if action == 'segmento':
                try:
                    data['nivel'] = int(request.POST['nivel'])
                    data['tipoactividad'] = int(request.POST['tipoactividad'])
                    atras = 0
                    if 'atras' in request.POST:
                        atras = int(request.POST['atras'])
                    if 'id' in request.POST:
                        if int(request.POST['id']) > 0:
                            if atras == 0:
                                actividadid = ActividadesMundoCraiDetalle.objects.values_list('actividadesmundocraidetalle__id',flat=True).filter(actividadesmundocraiprincipal__id=int(request.POST['id']),status=True)
                                data['id'] = int(request.POST['id'])
                                if ActividadesMundoCrai.objects.filter(id__in=actividadid, status=True,tipomundocrai=int(request.POST['tipomundo']),principal=True).exists():
                                    # tiene hijos
                                    detallesid = ActividadesMundoCraiDetalle.objects.values_list('actividadesmundocraidetalle__id', flat=True).filter(actividadesmundocraiprincipal__id=int(request.POST['id']), status=True)
                                    data['basedatos'] = ActividadesMundoCrai.objects.filter(id__in=detallesid,status=True,tipomundocrai=int(request.POST['tipomundo']),tipoactividad=int(request.POST['tipoactividad']),principal=True, estado=True,orden=int(request.POST['nivel'])).order_by('id')
                                    template = get_template("alu_mundocrai/segmento4.html")
                                else:
                                    # es el ultimo nivel
                                    detallesid = ActividadesMundoCraiDetalle.objects.values_list('actividadesmundocraidetalle__id', flat=True).filter(actividadesmundocraiprincipal__id=int(request.POST['id']), status=True)
                                    data['archivos'] = ActividadesMundoCrai.objects.filter(id__in=detallesid,status=True,tipomundocrai=int(request.POST['tipomundo']),tipoactividad=int(request.POST['tipoactividad']),estado=True, orden=int(request.POST['nivel'])).exclude(archivo='').order_by('id')
                                    data['enlaces'] = ActividadesMundoCrai.objects.filter(id__in=detallesid,status=True,tipomundocrai=int(request.POST['tipomundo']),tipoactividad=int(request.POST['tipoactividad']),estado=True, orden=int(request.POST['nivel']), video=False).exclude(enlace='').order_by('id')
                                    data['videos'] = ActividadesMundoCrai.objects.filter(id__in=detallesid, status=True,tipomundocrai=int(request.POST['tipomundo']),tipoactividad=int(request.POST['tipoactividad']),estado=True, orden=int(request.POST['nivel']), video=True).order_by('id')
                                    template = get_template("alu_mundocrai/segmento42.html")
                            else:
                                if ActividadesMundoCraiDetalle.objects.filter(actividadesmundocraidetalle__id=request.POST['id'], status=True).exists():
                                    id = ActividadesMundoCraiDetalle.objects.filter(actividadesmundocraidetalle__id=request.POST['id'], status=True)[0].actividadesmundocraiprincipal.id
                                    actividadid = ActividadesMundoCraiDetalle.objects.values_list('actividadesmundocraidetalle__id', flat=True).filter(actividadesmundocraiprincipal__id=id, status=True)
                                    data['id'] = id
                                    if ActividadesMundoCrai.objects.filter(id__in=actividadid, status=True,tipomundocrai=int(request.POST['tipomundo']),principal=True).exists():
                                        # tiene hijos
                                        detallesid = ActividadesMundoCraiDetalle.objects.values_list('actividadesmundocraidetalle__id', flat=True).filter(actividadesmundocraiprincipal__id=int(id), status=True)
                                        data['basedatos'] = ActividadesMundoCrai.objects.filter(id__in=detallesid,status=True,tipomundocrai=int(request.POST['tipomundo']),tipoactividad=int(request.POST['tipoactividad']),principal=True,estado=True, orden=int(request.POST['nivel'])).order_by('id')
                                        template = get_template("alu_mundocrai/segmento4.html")
                                    else:
                                        # es el ultimo nivel
                                        detallesid = ActividadesMundoCraiDetalle.objects.values_list('actividadesmundocraidetalle__id', flat=True).filter(actividadesmundocraiprincipal__id=int(id), status=True)
                                        data['archivos'] = ActividadesMundoCrai.objects.filter(id__in=detallesid,status=True,tipomundocrai=int(request.POST['tipomundo']),tipoactividad=int(request.POST['tipoactividad']),estado=True, orden=int(request.POST['nivel'])).exclude(archivo='').order_by('id')
                                        data['enlaces'] = ActividadesMundoCrai.objects.filter(id__in=detallesid,status=True,tipomundocrai=int(request.POST['tipomundo']),tipoactividad=int(request.POST['tipoactividad']),estado=True, orden=int(request.POST['nivel']), video=False).exclude(enlace='').order_by('id')
                                        data['videos'] = ActividadesMundoCrai.objects.filter(id__in=detallesid,status=True,tipomundocrai=int(request.POST['tipomundo']),tipoactividad=int(request.POST['tipoactividad']), estado=True, orden=int(request.POST['nivel']), video=True).order_by('id')
                                        template = get_template("alu_mundocrai/segmento42.html")

                                else:
                                    if ActividadesMundoCrai.objects.filter(principal=True, status=True,tipomundocrai=int(request.POST['tipomundo']),orden=int(request.POST['nivel']),tipoactividad=int(request.POST['tipoactividad']),estado=True).exists():
                                        data['basedatos'] = ActividadesMundoCrai.objects.filter(principal=True,status=True,tipomundocrai=int(request.POST['tipomundo']),orden=int(request.POST['nivel']),tipoactividad=int(request.POST['tipoactividad']),estado=True).order_by('id')
                                        template = get_template("alu_mundocrai/segmento4.html")
                                    else:
                                        data['archivos'] = ActividadesMundoCrai.objects.filter(status=True,tipomundocrai=int(request.POST['tipomundo']),tipoactividad=int(request.POST['tipoactividad']),estado=True, orden=int(request.POST['nivel'])).exclude(archivo='').order_by('id')
                                        data['enlaces'] = ActividadesMundoCrai.objects.filter(status=True,tipomundocrai=int(request.POST['tipomundo']),tipoactividad=int(request.POST['tipoactividad']),estado=True, orden=int(request.POST['nivel']), video=False).exclude(enlace='').order_by('id')
                                        data['videos'] = ActividadesMundoCrai.objects.filter(status=True,tipomundocrai=int(request.POST['tipomundo']),tipoactividad=int(request.POST['tipoactividad']),estado=True, orden=int(request.POST['nivel']), video=True).order_by('id')
                                        template = get_template("alu_mundocrai/segmento42.html")
                        else:
                            if ActividadesMundoCrai.objects.filter(principal=True,status=True,tipomundocrai=int(request.POST['tipomundo']),orden=int(request.POST['nivel']), tipoactividad=int(request.POST['tipoactividad']),estado=True).exists():
                                data['basedatos'] = ActividadesMundoCrai.objects.filter(principal=True,status=True,tipomundocrai=int(request.POST['tipomundo']),orden=int(request.POST['nivel']), tipoactividad=int(request.POST['tipoactividad']),estado=True).order_by('id')
                                template = get_template("alu_mundocrai/segmento4.html")
                            else:
                                data['archivos'] = ActividadesMundoCrai.objects.filter(status=True,tipomundocrai=int(request.POST['tipomundo']),tipoactividad=int(request.POST['tipoactividad']), estado=True, orden=int(request.POST['nivel'])).exclude(archivo='').order_by('id')
                                data['enlaces'] = ActividadesMundoCrai.objects.filter(status=True,tipomundocrai=int(request.POST['tipomundo']),tipoactividad=int(request.POST['tipoactividad']), estado=True, orden=int(request.POST['nivel']),video=False).exclude(enlace='').order_by('id')
                                data['videos'] = ActividadesMundoCrai.objects.filter(status=True,tipomundocrai=int(request.POST['tipomundo']),tipoactividad=int(request.POST['tipoactividad']), estado=True, orden=int(request.POST['nivel']), video=True).order_by('id')
                                template = get_template("alu_mundocrai/segmento42.html")
                    else:
                        if ActividadesMundoCrai.objects.filter(principal=True,status=True,tipomundocrai=int(request.POST['tipomundo']),orden=int(request.POST['nivel']), tipoactividad=int(request.POST['tipoactividad']),estado=True).exists():
                            data['basedatos'] = ActividadesMundoCrai.objects.filter(principal=True,status=True,tipomundocrai=int(request.POST['tipomundo']),orden=int(request.POST['nivel']), tipoactividad=int(request.POST['tipoactividad']),estado=True).order_by('id')
                            template = get_template("alu_mundocrai/segmento4.html")
                        else:
                            data['archivos'] = ActividadesMundoCrai.objects.filter(status=True,tipomundocrai=int(request.POST['tipomundo']),tipoactividad=int(request.POST['tipoactividad']), estado=True, orden=int(request.POST['nivel'])).exclude(archivo='').order_by('-id')
                            data['enlaces'] = ActividadesMundoCrai.objects.filter(status=True,tipomundocrai=int(request.POST['tipomundo']),tipoactividad=int(request.POST['tipoactividad']), estado=True, orden=int(request.POST['nivel']),video=False).exclude(enlace='').order_by('-id')
                            data['videos'] = ActividadesMundoCrai.objects.filter(status=True,tipomundocrai=int(request.POST['tipomundo']),tipoactividad=int(request.POST['tipoactividad']), estado=True, orden=int(request.POST['nivel']), video=True).order_by('-id')
                            template = get_template("alu_mundocrai/segmento42.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

            if action == 'segmento_aux':
                try:
                    data['id'] = int(request.POST['id'])
                    fecha = request.POST['fecha']
                    fecha_hasta = request.POST['fecha_hasta']
                    cursor = connection.cursor()
                    data['title'] = u'Gráficas Acceso al Mundo CRAI, fecha desde: ' + fecha + ' fecha hasta: ' + fecha_hasta
                    colores = [u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8", u"FF335B", u"33FFA4", u"#b87333",u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8",u"FF335B", u"33FFA4", u"#b87333", u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33",u"3370FF", u"D733FF", u"FF33A8", u"FF335B", u"33FFA4", u"#b87333", u"silver", u"gold",u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8", u"FF335B", u"33FFA4",u"#b87333", u"silver", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF",u"FF33A8", u"FF335B", u"33FFA4", u"#b87333", u"silver", u"gold", u"#e5e4e2"]
                    # atras = 0
                    # atras = int(request.POST['atras'])
                    resultadosgeneral = []
                    total = 0
                    if fecha != '' and fecha_hasta != '':
                        if int(request.POST['id']) > 0:
                            if int(request.POST['id']) >= 1 and  int(request.POST['id']) <=4 :
                                sql = "select (case am.tipomundocrai when 1 then 'BIBLIOTECA' when 2 then 'DOCENCIA' when 3 then 'INVESTIGACION' else 'CULTURAL' end ) tipomundocrai, am.descripcion, count(am.id) " \
                                      " from sga_contadoractividadesmundocrai ca, sga_actividadesmundocrai am " \
                                      " where ca.status=true and ca.actividadesmundocraiprincipal_id=am.id and am.status=true and am.tipomundocrai="+ request.POST['id']  +" " \
                                      " and ca.fecha between '"+ f"{convertir_fecha(fecha)}" +"' and '"+ f"{convertir_fecha(fecha_hasta)}" +"' " \
                                      " GROUP by am.id order by 1,2"
                                cursor.execute(sql)
                                results = cursor.fetchall()
                                resultadosgeneral = []
                                total = 0
                                i = 0
                                for r in results:
                                    resultadosgeneral.append([r[1], r[2], u'%s' % colores[i]])
                                    i += 1
                                    total = total + int(r[2])

                                data['total'] = total
                                data['resultadosgeneral'] = resultadosgeneral
                                template = get_template("alu_mundocrai/segmento_aux.html")
                            if int(request.POST['id']) == 5:
                                fecha = convertir_fecha(request.POST['fecha'])
                                fecha_hasta = convertir_fecha(request.POST['fecha_hasta'])
                                capacitacionescrais = CapacitacionesCrai.objects.filter(status=True,fechadesde__range=(fecha, fecha_hasta)).order_by('id')
                                data['capacitacionescrais'] = capacitacionescrais
                                template = get_template("alu_mundocrai/segmento_aux_capacitacion.html")
                            if int(request.POST['id']) == 6:
                                fecha = convertir_fecha(request.POST['fecha'])
                                fecha_hasta = convertir_fecha(request.POST['fecha_hasta'])
                                reservascrais = ReservasCrai.objects.filter(status=True,fecha__range=(fecha, fecha_hasta)).order_by('id')
                                data['reservascrais'] = reservascrais
                                template = get_template("alu_mundocrai/segmento_aux_reserva.html")


                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Seleccione bien las fechas"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

            if action == 'addinscripcioncapacitacion':
                try:
                    if profesor:
                        inscripcioncapacitacionescrai=InscripcionCapacitacionesCrai(capacitacionescrai_id=request.POST['capacitacionid'],
                                                                                    fecha=datetime.now().date(),
                                                                                    profesor=profesor)
                        persona_solicitud = profesor.persona
                    else:
                        if inscripcion:
                            inscripcioncapacitacionescrai=InscripcionCapacitacionesCrai(capacitacionescrai_id=request.POST['capacitacionid'],
                                                                                        fecha=datetime.now().date(),
                                                                                        inscripcion=inscripcion)
                            persona_solicitud = inscripcion.persona
                        else:
                            inscripcioncapacitacionescrai=InscripcionCapacitacionesCrai(capacitacionescrai_id=request.POST['capacitacionid'],
                                                                                        fecha=datetime.now().date(),
                                                                                        administrativo=administrativo)
                            persona_solicitud = administrativo.persona
                    inscripcioncapacitacionescrai.save(request)
                    if inscripcioncapacitacionescrai.capacitacionescrai.tipomundocrai == 3:
                        lista = ['sop_investigacion_crai@unemi.edu.ec']
                    else:
                        lista = ['sop_docencia_crai@unemi.edu.ec']
                    send_html_mail("Solicitud Capacitación", "emails/solicitudcapacitacion.html",{'tema': inscripcioncapacitacionescrai.capacitacionescrai.tema, 'persona': persona_solicitud}, lista, [], cuenta=CUENTAS_CORREOS[1][1])
                    log(u'Solicitud capacitación CRAI: %s' % inscripcioncapacitacionescrai, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar los datos."})

            if action == 'deletecapacitacioncrai':
                try:
                    inscripcioncapacitacionescrai = InscripcionCapacitacionesCrai.objects.get(pk=request.POST['id'])
                    log(u'Elimino solicitud Capacitacion CRAI: %s' % inscripcioncapacitacionescrai, request, "del")
                    inscripcioncapacitacionescrai.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al aprobar los datos."})

            if action == 'adddetalle':
                try:
                    horadesde = convertir_hora(request.POST['horadesde'])
                    horahasta = convertir_hora(request.POST['horahasta'])
                    fecha = convertir_fecha(request.POST['idfecha'])
                    descripcion = request.POST['descripcion']
                    salacrai = request.POST['salacrai']
                    cantidad = request.POST['cantidad']
                    if not horadesde <= horahasta:
                        return JsonResponse({"result": "bad", "mensaje": u"La hora desde debe ser mayor que la hora hasta"})
                    if not controlar_horas(fecha, horadesde, horahasta, salacrai):
                        reservascrai = ReservasCrai(solicitanteprofesor=profesor,
                                                    solicitanteinscripcion=inscripcion,
                                                    solicitanteadministrativo=administrativo,
                                                    descripcion=descripcion,
                                                    salacrai_id=salacrai,
                                                    cantidad=cantidad,
                                                    fecha=fecha,
                                                    horadesde=horadesde,
                                                    horahasta=horahasta,
                                                    lunes=True if fecha.isoweekday() == 1 else False,
                                                    martes=True if fecha.isoweekday() == 2 else False,
                                                    miercoles=True if fecha.isoweekday() == 3 else False,
                                                    jueves=True if fecha.isoweekday() == 4 else False,
                                                    viernes=True if fecha.isoweekday() == 5 else False,
                                                    sabado=True if fecha.isoweekday() == 6 else False,
                                                    domingo=True if fecha.isoweekday() == 7 else False)
                        reservascrai.save(request)
                        lista = ['rparedesh@unemi.edu.ec',	'iburgosv@unemi.edu.ec']
                        if profesor:
                            send_html_mail("Reserva Sala CRAI (DOCENTE)", "emails/reservasalacrai.html", {'sistema': request.session['nombresistema'], 'participante': profesor, 'descripcion': descripcion, 'salacrai': salacrai, 't': tituloinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[4][1])
                        else:
                            if inscripcion:
                                send_html_mail("Reserva Sala CRAI (ESTUDIANTE)", "emails/reservasalacraiestudiante.html", {'sistema': request.session['nombresistema'], 'participante': inscripcion, 'descripcion': descripcion, 'salacrai': salacrai, 't': tituloinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[4][1])
                            else:
                                send_html_mail("Reserva Sala CRAI (ADMINISTRATIVO)", "emails/reservasalacraiadministrativo.html", {'sistema': request.session['nombresistema'], 'participante': administrativo,'descripcion': descripcion, 'salacrai': salacrai, 't': tituloinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[4][1])
                        log(u'Adiciono nueva solicitud reserva sala CRAI, sola: %s' % reservascrai, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Ya tiene registrado un registro en esas horas."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'deletedetalle':
                try:
                    reservascrai = ReservasCrai.objects.get(pk=int(request.POST['id']))
                    lista = ['rparedesh@unemi.edu.ec',	'iburgosv@unemi.edu.ec']
                    if profesor:
                        send_html_mail("Eliminación Reserva Sala CRAI (DOCENTE)", "emails/eliminacionreservasalacrai.html", {'sistema': request.session['nombresistema'], 'participante': profesor, 'descripcion': reservascrai.descripcion, 'salacrai': reservascrai.salacrai, 't': tituloinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[4][1])
                    else:
                        pass
                    if inscripcion:
                        send_html_mail("Eliminación Reserva Sala CRAI (ESTUDIANTE)", "emails/eliminacionreservasalacraiestudiante.html", {'sistema': request.session['nombresistema'], 'participante': inscripcion, 'descripcion': reservascrai.descripcion, 'salacrai': reservascrai.salacrai, 't': tituloinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[4][1])
                    else:
                        send_html_mail("Eliminación Reserva Sala CRAI (ADMINISTRATIVO)", "emails/eliminacionreservasalacraiadministrativo.html", {'sistema': request.session['nombresistema'], 'participante': administrativo, 'descripcion': reservascrai.descripcion, 'salacrai': reservascrai.salacrai, 't': tituloinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[4][1])
                    log(u'Elimino reserva sala CRAI: %s' % (reservascrai), request, "add")
                    reservascrai.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})
            # if action == 'addmasivo':
            #     try:
            #         form = ReservasCraiSolicitarMasivoForm(request.POST)
            #         if form.is_valid():
            #             fechas = []
            #             inicio = form.cleaned_data['fechadesde']
            #             fin = form.cleaned_data['fechahasta']
            #             if inicio == fin:
            #                 fechas.append(inicio)
            #             else:
            #                 for dia in daterange(inicio, (fin + timedelta(days=1))):
            #                     fechas.append(dia)
            #             guardo = False
            #             for fechalista in fechas:
            #                 bandera = False
            #                 dia_semanalista = fechalista.isoweekday()
            #                 if form.cleaned_data['lunes'] and dia_semanalista == 1:
            #                     bandera = True
            #                 if form.cleaned_data['martes'] and dia_semanalista == 2:
            #                     bandera = True
            #                 if form.cleaned_data['miercoles'] and dia_semanalista == 3:
            #                     bandera = True
            #                 if form.cleaned_data['jueves'] and dia_semanalista == 4:
            #                     bandera = True
            #                 if form.cleaned_data['viernes'] and dia_semanalista == 5:
            #                     bandera = True
            #                 if form.cleaned_data['sabado'] and dia_semanalista == 6:
            #                     bandera = True
            #                 if form.cleaned_data['domingo'] and dia_semanalista == 7:
            #                     bandera = True
            #                 if bandera:
            #                     if not controlar_horas(profesor, inscripcion, administrativo, fechalista, form.cleaned_data['horadesde'], form.cleaned_data['horahasta']):
            #                         guardo = True
            #                         reservascrai = ReservasCrai(solicitanteprofesor=profesor,
            #                                                     solicitanteinscripcion=inscripcion,
            #                                                     solicitanteadministrativo=administrativo,
            #                                                     descripcion=form.cleaned_data['descripcion'],
            #                                                     salacrai=form.cleaned_data['salacrai'],
            #                                                     cantidad=form.cleaned_data['cantidad'],
            #                                                     fecha=fechalista,
            #                                                     horadesde=form.cleaned_data['horadesde'],
            #                                                     horahasta=form.cleaned_data['horahasta'],
            #                                                     lunes=True if fechalista.isoweekday() == 1 else False,
            #                                                     martes=True if fechalista.isoweekday() == 2 else False,
            #                                                     miercoles=True if fechalista.isoweekday() == 3 else False,
            #                                                     jueves=True if fechalista.isoweekday() == 4 else False,
            #                                                     viernes=True if fechalista.isoweekday() == 5 else False,
            #                                                     sabado=True if fechalista.isoweekday() == 6 else False,
            #                                                     domingo=True if fechalista.isoweekday() == 7 else False)
            #                         reservascrai.save(request)
            #             if not guardo:
            #                 transaction.set_rollback(True)
            #                 return JsonResponse({"result": "bad", "mensaje": u"No se guardo ningun regisro, fechas incorrectas en los días seleccionados"})
            #             log(u'Adiciono nueva solicitud reserva sala CRAI: %s' % reservascrai, request, "add")
            #             return JsonResponse({"result": "ok"})
            #         else:
            #             raise NameError('Error')
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            if action == 'listar':
                try:
                    fecha = convertir_fecha(request.POST['idfecha'])
                    if profesor:
                        data['reservascrais'] = ReservasCrai.objects.filter(status=True,fecha=fecha, solicitanteprofesor=profesor).order_by('horadesde')
                    else:
                        if inscripcion:
                            data['reservascrais'] = ReservasCrai.objects.filter(status=True, fecha=fecha, solicitanteinscripcion=inscripcion).order_by('horadesde')
                        else:
                            data['reservascrais'] = ReservasCrai.objects.filter(status=True, fecha=fecha, solicitanteadministrativo=administrativo).order_by('horadesde')
                    data['form2'] = ReservasCraiSolicitarDetalleForm()
                    template = get_template("alu_mundocrai/listar.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'editdetalle':
                try:
                    horadesde = convertir_hora(request.POST['horadesde'])
                    horahasta = convertir_hora(request.POST['horahasta'])
                    cantidad = convertir_hora(request.POST['cantidad'])
                    salacrai = convertir_hora(request.POST['salacrai'])
                    if not horadesde <= horahasta:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"La hora desde debe ser mayor que la hora hasta"})
                    reservascrai = ReservasCrai.objects.get(pk=int(request.POST['id']))
                    reservascrai.horadesde = horadesde
                    reservascrai.horahasta = horahasta
                    reservascrai.cantidad = cantidad
                    reservascrai.salacrai_id = salacrai
                    reservascrai.save(request)
                    log(u'Edito solicitud reserva sala CRAI: %s - [%s %s]' % (reservascrai, horadesde, horahasta), request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'addsolicitud':
                try:
                    f = SolicitudOtraCapacitacionForm(request.POST)
                    if f.is_valid():
                        solicitudotrascapacitacionescrai = SolicitudOtrasCapacitacionesCrai(profesor=profesor,
                                                                                            tema=f.cleaned_data['tema'],
                                                                                            fecha = f.cleaned_data['fecha'],
                                                                                            horadesde = f.cleaned_data['horadesde'],
                                                                                            horahasta = f.cleaned_data['horahasta'] )
                        solicitudotrascapacitacionescrai.save(request)
                        lista = ['sop_docencia_crai@unemi.edu.ec']
                        send_html_mail("Solicitud Otra Capacitación", "emails/solicitudotracapacitacion.html",{'tema': solicitudotrascapacitacionescrai.tema, 'fecha': solicitudotrascapacitacionescrai.fecha, 'horadesde': solicitudotrascapacitacionescrai.horadesde, 'horahasta': solicitudotrascapacitacionescrai.horahasta, 'persona': solicitudotrascapacitacionescrai.profesor}, lista, [], cuenta=CUENTAS_CORREOS[1][1])
                        log(u'Ingreso Solicitud Otra Capacitacion: %s' % persona, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'delsolicitud':
                try:
                    solicitud = SolicitudOtrasCapacitacionesCrai.objects.get(pk=request.POST['id'])
                    log(u'Elimino solicitud: %s' % solicitud, request, "del")
                    solicitud.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'pagina':
                try:
                    data['direccion'] = request.POST['direccion']
                    template = get_template("alu_mundocrai/pagina.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            if action == 'respuesta':
                try:
                    inscripcion = InscripcionCapacitacionesCrai.objects.filter(pk=int(request.POST['idinscripcion']))[0]
                    encuesta = inscripcion.capacitacionescrai.encuesta
                    encuestainscripcioncapacitacionescrai = EncuestaInscripcionCapacitacionesCrai(inscripcion=inscripcion,encuesta=encuesta)
                    encuestainscripcioncapacitacionescrai.save(request)
                    for x, y in request.POST.items():
                        if len(x) > 5 and x[:5] == 'valor':
                            pregunta = PreguntasEncuestaCapacitacionesCrai.objects.get(pk=x[5:])
                            valor = y
                            bandera = 0
                            try:
                                valor = int(y)
                                bandera = 1
                            except:
                                pass
                            if bandera == 1:
                                dato = RespuestaEncuestaInscripcionCapacitacionesCrai(encuestainscripcion=encuestainscripcioncapacitacionescrai,
                                                                                      pregunta=pregunta,
                                                                                      nivel_id=valor)
                            dato.save(request)
                    log(u'Realizo Encuesta Satisfaccion crai: %s' % encuestainscripcioncapacitacionescrai, request, "add")
                    return HttpResponseRedirect("/alu_mundocrai?action=certificados")
                    # return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)

            if action == 'addbuzon':
                with transaction.atomic():
                    try:
                        form = BuzonMundoCraiForm(request.POST)
                        if form.is_valid():
                            registro = BuzonMundoCrai(tipobuzon_id=1, contenido=form.cleaned_data['contenido'])
                            registro.save(request)
                            log(u'Adiciono Servicio de Citas: %s' % registro, request, "add")
                            return JsonResponse({"result": False}, safe=False)
                        else:
                            raise NameError('Error')
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            if action == 'addinscripcion':
                try:
                    club = Club.objects.get(pk=request.POST['idclub'], status=True)
                    if not club.inscripcionclub_set.values("id").filter(inscripcion=inscripcion,status=True).exists():
                        totalinscritos = club.inscripcionclub_set.values("id").filter(status=True).count()
                        if totalinscritos >= club.cupo:
                            return JsonResponse({"result": "bad", "mensaje": u"Lo sentimos, no hay cupo disponible."})
                        inscripcionclub = InscripcionClub(inscripcion=inscripcion,
                                                          club=club)
                        inscripcionclub.save(request)
                        lista = ['rparedesh@unemi.edu.ec', 'iburgosv@unemi.edu.ec']
                        send_html_mail("Reserva Sala CRAI (ESTUDIANTE)", "emails/reservasalacraiestudiante.html", {'sistema': request.session['nombresistema'], 'participante': inscripcionclub.inscripcion, 'club': inscripcionclub.club.nombre, 't': tituloinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[4][1])
                        log(u'Adiciono Inscripcion a los Clubes: %s' % inscripcionclub, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Lo sentimos, ya esta inscrito en este club."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'addsolicitudequipo':
                try:

                    config = ConfiguracionEquipoComputo.objects.get(id=int(request.POST['configuracion']))
                    terminos = TerminosCondicionesEquipoComputo.objects.get(id=int(request.POST['terminos']))
                    f = SolicitudPrestamoECForm(request.POST)
                    if not f.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in f.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})

                    solicitudes_fecha = SolicitudEquipoComputo.objects.filter(status=True, solicitante=persona, fechauso=f.cleaned_data['fechauso']).count()
                    if solicitudes_fecha >= 1:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": u"Ya realizo una solicitud con la fecha seleccionada."})

                    codigo = generate_unique_code_ec()

                    solicitud = SolicitudEquipoComputo(
                        configuracion=config,
                        terminos=terminos,
                        solicitante=persona,
                        inscripcion=perfilprincipal.inscripcion,
                        estadosolicitud=1,
                        motivo=f.cleaned_data['motivo'],
                        codigo=codigo,
                        # horainicio=f.cleaned_data['horainicio'],
                        # horafin=f.cleaned_data['horafin'],
                        fechauso=f.cleaned_data['fechauso'],
                    )
                    solicitud.save(request)

                    historial = HistorialSolicitudEC(solicitudec=solicitud,
                                                     estadosolicitud=solicitud.estadosolicitud,
                                                     observacion='SOLICITUD CREADA',
                                                     persona=persona)
                    historial.save(request)

                    return JsonResponse({"result": False, "mensaje": u"Datos guardados correctamente."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos. [%s]" % ex})

            elif action == 'editsolicitudequipo':
                try:
                    id = request.POST['id']
                    solicitud = SolicitudEquipoComputo.objects.get(pk=int(encrypt(id)))
                    f = SolicitudPrestamoECForm(request.POST, instancia=solicitud)
                    if not f.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in f.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})

                    solicitud.fechauso = f.cleaned_data['fechauso']
                    # solicitud.horainicio = f.cleaned_data['horainicio']
                    # solicitud.horafin = f.cleaned_data['horafin']
                    solicitud.motivo = f.cleaned_data['motivo']
                    solicitud.save(request)

                    return JsonResponse({"result": False, "mensaje": u"Datos guardados correctamente."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos. [%s]" % ex})

            elif action == 'delsolicitudequipo':
                try:
                    id = request.POST['id']
                    solicitud = SolicitudEquipoComputo.objects.get(pk=int(id))
                    solicitud.status = False
                    solicitud.save(request)
                    return JsonResponse({"error": False})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"error": True, "message": u"Error al eliminar el registro. [%s]" % ex})

            return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action']=action = request.GET['action']
            if action == 'biblioteca':
                try:
                    data['title'] = u'Biblioteca'
                    data['nivel'] = 1
                    return render(request, "alu_mundocrai/biblioteca.html", data)
                except:
                    pass

            if action == 'docencia':
                try:
                    data['title'] = u'Docencia'
                    data['nivel'] = 1
                    return render(request, "alu_mundocrai/docencia.html", data)
                except:
                    pass

            if action == 'investigacion':
                try:
                    data['title'] = u'Investigación'
                    data['nivel'] = 1
                    return render(request, "alu_mundocrai/investigacion.html", data)
                except:
                    pass

            if action == 'cultural':
                try:
                    data['title'] = u'Gestión Cultural'
                    data['nivel'] = 1
                    data['perfil'] = tipoingreso
                    data['inscripcion'] = inscripcion
                    if tipoingreso==2:
                        hoy = datetime.now().date()
                        data['clubes'] = Club.objects.select_related().filter(((Q(coordinacion__isnull=True) | Q(coordinacion=inscripcion.coordinacion)) & (Q(carrera__isnull=True) | Q(carrera=inscripcion.carrera))),status=True, fechainicioinscripcion__lte=hoy, fechafininscripcion__gte=hoy).order_by('seccionclub__nombre', 'coordinacion', 'nombre')
                    return render(request, "alu_mundocrai/cultural.html", data)
                except:
                    pass

            if action == 'estadistica':
                try:
                    data['title'] = u'Datos del CRAI'
                    return render(request, "alu_mundocrai/estadistica.html", data)
                except Exception as ex:
                    pass

            if action == 'capacitacion':
                try:
                    data['title'] = u'Solicitud de Inscripción'
                    data['solicitudes'] = InscripcionCapacitacionesCrai.objects.filter((Q(inscripcion__persona=persona) | Q(profesor__persona=persona) | Q(administrativo__persona=persona)), status=True, aprobado=False).order_by('-fecha')
                    data['certificados'] = InscripcionCapacitacionesCrai.objects.filter((Q(inscripcion__persona=persona) | Q(profesor__persona=persona) | Q(administrativo__persona=persona)), status=True, aprobado=True).order_by('-fecha')
                    data['solicitudotrascapacitacionescrais'] = SolicitudOtrasCapacitacionesCrai.objects.filter(profesor=profesor, status=True)
                    data['capacitacionescrais'] = None
                    if profesor:
                        data['capacitacionescrais'] = CapacitacionesCrai.objects.filter(fechadesde__gt=datetime.now().date(), status=True).order_by('-id').exclude(tipo=3)
                    if inscripcion:
                        data['capacitacionescrais'] = CapacitacionesCrai.objects.filter(fechadesde__gt=datetime.now().date(), status=True).order_by('-id').exclude(tipo=2)
                    ver = False
                    if profesor:
                        ver = True
                    data['ver'] = ver
                    data['persona'] = persona
                    data['hoy'] = datetime.now().date()
                    return render(request, "alu_mundocrai/capacitacion.html", data)
                except:
                    pass

            if action == 'reservas':
                try:
                    data['title'] = u'Reservas Sala CRAI'
                    fecha = datetime.now().date()
                    hoy = datetime.now().date()
                    pdia = fecha.day
                    panio = fecha.year
                    pmes = fecha.month
                    if 'mover' in request.GET:
                        mover = request.GET['mover']

                        if mover == 'anterior':
                            mes = int(request.GET['mes'])
                            anio = int(request.GET['anio'])
                            pmes = mes - 1
                            if pmes == 0:
                                pmes = 12
                                panio = anio - 1
                            else:
                                panio = anio

                        elif mover == 'proximo':
                            mes = int(request.GET['mes'])
                            anio = int(request.GET['anio'])
                            pmes = mes + 1
                            if pmes == 13:
                                pmes = 1
                                panio = anio + 1
                            else:
                                panio = anio

                    s_anio = panio
                    s_mes = pmes
                    s_dia = 1
                    data['mes'] = MESES_CHOICES[s_mes - 1]
                    data['ws'] = [0, 7, 14, 21, 28, 35]
                    lista = {}
                    listaactividades = {}
                    for i in range(1, 43, 1):
                        dia = {i: 'no'}
                        actividaddia = {i: None}
                        lista.update(dia)
                        listaactividades.update(actividaddia)
                    comienzo = False
                    fin = False
                    for i in lista.items():
                        try:
                            fecha = date(s_anio, s_mes, s_dia)
                            if fecha.isoweekday() == i[0] and fin is False and comienzo is False:
                                comienzo = True
                        except Exception as ex:
                            pass
                        if comienzo:
                            try:
                                fecha = date(s_anio, s_mes, s_dia)
                            except Exception as ex:
                                fin = True
                        if comienzo and fin is False:
                            dia = {i[0]: s_dia}
                            s_dia += 1
                            lista.update(dia)
                            if profesor:
                                actividaddias = ReservasCrai.objects.filter(status=True, fecha=fecha, solicitanteprofesor=profesor)
                            else:
                                if inscripcion:
                                    actividaddias = ReservasCrai.objects.filter(status=True, fecha=fecha, solicitanteinscripcion=inscripcion)
                                else:
                                    actividaddias = ReservasCrai.objects.filter(status=True, fecha=fecha, solicitanteadministrativo=administrativo)
                            diaact = []
                            if actividaddias.exists():
                                valor = ""
                                for actividaddia in actividaddias:
                                    # &#13;
                                    cadena = u"Hora: %s a %s, Motivo: %s; " % (str(actividaddia.horadesde), str(actividaddia.horahasta), str(actividaddia.descripcion))
                                    valor = valor + cadena
                            else:
                                valor = ""
                            act = [valor, (fecha < datetime.now().date() and valor == ""), 1,
                                   fecha.strftime('%d-%m-%Y')]
                            diaact.append(act)
                            listaactividades.update({i[0]: diaact})
                    data['dias_mes'] = lista
                    data['dwnm'] = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
                    data['dwn'] = [1, 2, 3, 4, 5, 6, 7]
                    data['daymonth'] = 1
                    data['s_anio'] = s_anio
                    data['s_mes'] = s_mes
                    data['lista'] = lista
                    data['listaactividades'] = listaactividades
                    data['archivo'] = None

                    persona = request.session['persona']
                    data['check_session'] = False
                    data['fechainicio'] = date(datetime.now().year, 1, 1)
                    data['fechafin'] = datetime.now().date()
                    data['form3'] = ReservasCraiSolicitarForm()
                    data['hoy'] = hoy
                    return render(request, "alu_mundocrai/reservas.html", data)
                except:
                    pass
            # if action == 'addmasivo':
            #     try:
            #         data['title'] = u'Adicionar Configuración'
            #         form = ReservasCraiSolicitarMasivoForm()
            #         data['form'] = form
            #         return render(request, "alu_mundocrai/addmasivo.html", data)
            #     except Exception as ex:
            #         pass
            if action == 'addinscripcioncapacitacion':
                try:
                    data['title'] = u'Solicitud Capacitación'
                    if profesor:
                        data['participante'] = profesor
                        data['tipo'] = 1
                    else:
                        if inscripcion:
                            data['participante'] = inscripcion
                            data['tipo'] = 2
                        else:
                            data['participante'] = administrativo
                            data['tipo'] = 3
                    data['capacitacionescraiid'] = request.GET['id']
                    return render(request, "alu_mundocrai/addinscripcioncapacitacion.html", data)
                except Exception as ex:
                    pass

            if action == 'deletecapacitacioncrai':
                try:
                    data['title'] = u'Eliminar solicitud Capacitacón Crai'
                    data['inscripcioncapacitacionescrai'] = InscripcionCapacitacionesCrai.objects.get(pk=request.GET['id'])
                    return render(request, "alu_mundocrai/deletecapacitacioncrai.html", data)
                except Exception as ex:
                    pass

            if action == 'addsolicitud':
                try:
                    data['title'] = u'Adicionar Solicitud otra Capacitación'
                    form = SolicitudOtraCapacitacionForm()
                    data['form'] = form
                    return render(request, "alu_mundocrai/addsolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'delsolicitud':
                try:
                    data['title'] = u'Eliminar solicitud'
                    data['solicitud'] = SolicitudOtrasCapacitacionesCrai.objects.get(pk=request.GET['id'])
                    return render(request, "alu_mundocrai/delsolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'certificados':
                try:
                    data['title'] = u'Certificados Cursos CRAI'
                    data['certificados'] = InscripcionCapacitacionesCrai.objects.filter((Q(inscripcion__persona=persona) | Q(profesor__persona=persona) | Q(administrativo__persona=persona)), status=True, aprobado=True).order_by('-fecha')
                    data['persona'] = persona
                    data['hoy'] = datetime.now().date()
                    return render(request, "alu_mundocrai/certificados.html", data)
                except:
                    pass

            if action == 'certificadosclub':
                try:
                    data['title'] = u'Certificados CLUB CRAI'
                    data['certificados'] = InscripcionClub.objects.filter(inscripcion__persona=persona, status=True, aprobacion=3).order_by('-id')
                    data['persona'] = persona
                    data['hoy'] = datetime.now().date()
                    return render(request, "alu_mundocrai/certificadosclub.html", data)
                except:
                    pass
            if action == 'reportes':
                try:
                    data['title'] = u'Reportes'
                    return render(request, "alu_mundocrai/reportes.html", data)
                except Exception as ex:
                    pass

            elif action == 'reporteporfacu':
                try:
                    data['title'] = u'Reporte de libros por facultad'
                    data['facuSelected'] = True
                    idl = int(request.GET.get('idl', '0'))
                    ids = ActividadesMundoCraiDetalle.objects.values_list('actividadesmundocraidetalle__id', flat=True).filter(actividadesmundocraiprincipal__id=80, status=True).distinct()
                    data['facultades'] = facultades = ActividadesMundoCrai.objects.filter(id__in=ids, status=True, tipomundocrai=1, tipoactividad=4, principal=True, estado=True, orden=3).order_by('id')
                    if idl:
                        data['facuSelected'] = False
                        data['idl'] = idl
                        ids = ActividadesMundoCraiDetalle.objects.values_list('actividadesmundocraidetalle__id', flat=True).filter(actividadesmundocraiprincipal__id=idl, status=True).distinct()
                        areaconocimiento = ActividadesMundoCrai.objects.filter(id__in=ids, status=True, tipomundocrai=1, tipoactividad=4, principal=True, estado=True, orden=4).order_by('id')
                        dict = []
                        for x in areaconocimiento:
                            librosporarea = ActividadesMundoCrai.objects.filter(id__in=ActividadesMundoCraiDetalle.objects.values_list('actividadesmundocraidetalle__id', flat=True).filter(actividadesmundocraiprincipal__id=x.id, status=True).distinct(), status=True, tipomundocrai=1, tipoactividad=4, estado=True, orden=5).order_by('id')
                            dict.append({"title": x.descripcion, "data": librosporarea})
                        data['libros'] = dict
                    else:
                        data['idl'] = 0
                        # idac = ActividadesMundoCraiDetalle.objects.values_list('actividadesmundocraidetalle__id', flat=True).filter(
                        #     actividadesmundocraiprincipal__id__in=facultades.values_list('id', flat=True), status=True).distinct()
                        # temp = ActividadesMundoCrai.objects.filter(id__in=idac, status=True, tipomundocrai=1,
                        #                                            tipoactividad=4, principal=True, estado=True,
                        #                                            orden=4).order_by('id')
                        dict = []
                        for facu in facultades:
                            idac = ActividadesMundoCraiDetalle.objects.values_list('actividadesmundocraidetalle__id',
                                                                                   flat=True).filter(
                                actividadesmundocraiprincipal__id=facu.pk,
                                status=True).distinct()
                            temp = ActividadesMundoCrai.objects.filter(id__in=idac, status=True, tipomundocrai=1,
                                                                       tipoactividad=4, principal=True, estado=True,
                                                                       orden=4).order_by('id')
                            for x in temp:
                                temp2 = ActividadesMundoCrai.objects.filter(id__in=ActividadesMundoCraiDetalle.objects.values_list('actividadesmundocraidetalle__id', flat=True).filter(actividadesmundocraiprincipal__id=x.id, status=True).distinct(), status=True, tipomundocrai=1, tipoactividad=4, estado=True, orden=5).order_by('id')
                                # if facu.id == temp2.
                                dict.append({"facultad":facu.descripcion,"title": x.descripcion, "data": temp2})
                        data['libros'] = dict
                    return render(request, "alu_mundocrai/reporteporfacultad.html", data)
                except Exception as ex:
                    pass

            elif action == 'reporteporfacu_excel':
                try:
                    output = io.BytesIO()
                    __author__ = 'Unemi'
                    workbook = xlsxwriter.Workbook(output)
                    hoy = datetime.now().date()
                    ws = workbook.add_worksheet('%s' % hoy)
                    ws.set_column(0, 0, 50)
                    ws.set_column(1, 1, 50)
                    ws.set_column(2, 2, 50)
                    ws.set_column(3, 3, 50)
                    ws.set_column(4, 4, 50)
                    ws.set_column(5, 5, 50)
                    formatotitulo_filtros = workbook.add_format({'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14, 'font_color': 'white', 'fg_color': '#1C3247'})
                    formatoceldacenter = workbook.add_format({'valign': 'vcenter', 'text_wrap': 1, 'border': 1, 'font_size': 8, 'font_name': 'Verdana'})
                    formatoceldacab = workbook.add_format({'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247','font_color': 'white'})

                    idl = int(request.GET.get('idl', '0'))

                    if idl:

                        facultad = ActividadesMundoCrai.objects.filter(id=idl).first()
                        ws.merge_range('A1:E1', '%s' % facultad.descripcion, formatotitulo_filtros)
                        ws.write(1, 0, 'AREA DE CONOCIMIENTO', formatoceldacab)
                        ws.write(1, 1, 'NOMBRE DEL LIBRO', formatoceldacab)
                        ws.write(1, 2, 'CONCEPTO', formatoceldacab)
                        ws.write(1, 3, 'TIPO MUNDO', formatoceldacab)
                        ws.write(1, 4, 'TIPO ACTIVIDAD', formatoceldacab)


                        areasdeconocimiento = ActividadesMundoCraiDetalle.objects.filter(actividadesmundocraiprincipal__id=idl,
                                                                                         actividadesmundocraidetalle__status=True,
                                                                                         actividadesmundocraidetalle__tipomundocrai=1,
                                                                                         actividadesmundocraidetalle__tipoactividad=4,
                                                                                         actividadesmundocraidetalle__principal=True,
                                                                                         actividadesmundocraidetalle__estado=True,
                                                                                         actividadesmundocraidetalle__orden=4,
                                                                                         status=True).order_by('actividadesmundocraidetalle__descripcion')

                        filas_recorridas = 3
                        for x in areasdeconocimiento:
                            actividadesmundocrai = x.actividadesmundocraidetalle
                            list = ActividadesMundoCraiDetalle.objects.values_list('actividadesmundocraidetalle__id', flat=True).filter(
                                actividadesmundocraiprincipal__id=actividadesmundocrai.id,
                                status=True).distinct()
                            libros = ActividadesMundoCrai.objects.filter(id__in=list, status=True, estado=True, orden=5).order_by('id')
                            for libro in libros:
                                ws.write('A%s' % filas_recorridas, u'%s' % actividadesmundocrai.descripcion, formatoceldacenter)
                                ws.write('B%s' % filas_recorridas, u'%s' % libro.descripcion, formatoceldacenter)
                                concepto = u'%s' % libro.concepto
                                if not concepto:
                                    concepto = "N/A"

                                ws.write('C%s' % filas_recorridas, concepto, formatoceldacenter)
                                ws.write('D%s' % filas_recorridas, libro.get_tipomundocrai_display(), formatoceldacenter)
                                ws.write('E%s' % filas_recorridas, libro.get_tipoactividad_display(), formatoceldacenter)

                                filas_recorridas += 1
                    else:
                        #idl = 0

                        ids = ActividadesMundoCraiDetalle.objects.values_list('actividadesmundocraidetalle__id',
                                                                              flat=True).filter(
                            actividadesmundocraiprincipal__id=80, status=True).distinct()
                        facultad = ActividadesMundoCrai.objects.filter(id__in=ids, status=True,
                                                                                              tipomundocrai=1,
                                                                                              tipoactividad=4,
                                                                                              principal=True,
                                                                                              estado=True,
                                                                                              orden=3).order_by('id')

                        ws.merge_range('A1:F1', 'REPORTE GENERAL DE LIBRO', formatotitulo_filtros)
                        ws.write(1, 0, 'FACULTAD', formatoceldacab)
                        ws.write(1, 1, 'AREA DE CONOCIMIENTO', formatoceldacab)
                        ws.write(1, 2, 'NOMBRE DEL LIBRO', formatoceldacab)
                        ws.write(1, 3, 'CONCEPTO', formatoceldacab)
                        ws.write(1, 4, 'TIPO MUNDO', formatoceldacab)
                        ws.write(1, 5, 'TIPO ACTIVIDAD', formatoceldacab)


                        filas_recorridas = 3
                        for fa in facultad:
                            areasdeconocimiento = ActividadesMundoCraiDetalle.objects.filter(
                                actividadesmundocraiprincipal__id=fa.pk,
                                actividadesmundocraidetalle__status=True,
                                actividadesmundocraidetalle__tipomundocrai=1,
                                actividadesmundocraidetalle__tipoactividad=4,
                                actividadesmundocraidetalle__principal=True,
                                actividadesmundocraidetalle__estado=True,
                                actividadesmundocraidetalle__orden=4,
                                status=True).order_by('actividadesmundocraidetalle__descripcion')
                            for x in areasdeconocimiento:
                                actividadesmundocrai = x.actividadesmundocraidetalle
                                list = ActividadesMundoCraiDetalle.objects.values_list('actividadesmundocraidetalle__id', flat=True).filter(
                                    actividadesmundocraiprincipal__id=actividadesmundocrai.id,
                                    status=True).distinct()
                                libros = ActividadesMundoCrai.objects.filter(id__in=list, status=True, estado=True, orden=5).order_by('id')
                                for libro in libros:
                                    ws.write('A%s' % filas_recorridas, u'%s' % fa.descripcion, formatoceldacenter)
                                    ws.write('B%s' % filas_recorridas, u'%s' % actividadesmundocrai.descripcion, formatoceldacenter)
                                    ws.write('C%s' % filas_recorridas, u'%s' % libro.descripcion, formatoceldacenter)
                                    concepto = u'%s' % libro.concepto
                                    if not concepto:
                                        concepto = "N/A"
                                    ws.write('D%s' % filas_recorridas, concepto, formatoceldacenter)
                                    ws.write('E%s' % filas_recorridas, libro.get_tipomundocrai_display(), formatoceldacenter)
                                    ws.write('F%s' % filas_recorridas, libro.get_tipoactividad_display(), formatoceldacenter)
                                    filas_recorridas += 1

                    workbook.close()
                    output.seek(0)
                    name_document = 'reporte_libros{}'.format(str(datetime.now().strftime('%Y%m%d_%H%M%S')))
                    filename = f'{name_document}.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'pencuesta':
                try:
                    data = {}
                    capacitacion = InscripcionCapacitacionesCrai.objects.get(pk=int(request.GET['id'])).capacitacionescrai
                    data['idinscripcion'] = request.GET['id']
                    data['preguntas'] = capacitacion.encuesta.preguntasencuestacapacitacionescrai_set.filter(status=True).order_by('id')
                    data['niveles'] = capacitacion.encuesta.nivelsatisfacionencuestacapacitacionescrai_set.filter(status=True).order_by('orden')
                    # template = get_template("alu_mundocrai/pencuesta.html")
                    # json_content = template.render(data)
                    # return JsonResponse({"result": "ok", 'data': json_content})
                    return render(request, "alu_mundocrai/pencuesta.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'organigrama':
                try:
                    data = {}
                    data['secciones'] = SeccionDepartamento.objects.filter(departamento_id=109).order_by('id')
                    template = get_template("alu_mundocrai/organigrama.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos."})

            elif action =='addbuzon':
                try:
                    data['form'] = BuzonMundoCraiForm()
                    template = get_template("alu_mundocrai/modal/formbuzon.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'prestamoequipos':
                try:

                    fecha_actual = datetime.now().date()
                    periodo_actual = fecha_actual >= periodosesion.inicio and fecha_actual <= periodosesion.fin
                    es_estudiante = perfilprincipal.es_estudiante()

                    configuracionactiva = ConfiguracionEquipoComputo.objects.filter(status=True, activo=True)
                    terminosactivo = TerminosCondicionesEquipoComputo.objects.filter(status=True, activo=True)

                    data['title'] = u'Solicitud de equipos'
                    data['subtitle'] = u'Préstamo de equipos de cómputo'

                    url_vars, filtro, search, = f'&action={action}', Q(status=True), request.GET.get('s', '').strip()
                    estado = int(request.GET.get('estado', 0))

                    if search:
                        filtro = filtro & Q(Q(titulo__icontains=search) | Q(descripcion__icontains=search))
                        data['s'] = search
                        url_vars += f'&s={search}'

                    if estado != 0:
                        filtro = filtro & Q(estadosolicitud=estado)
                        data['estado'] = estado
                        url_vars += f'&estado={estado}'

                    solicitudes = SolicitudEquipoComputo.objects.filter(status=True, solicitante=persona).order_by('-id')
                    solicitudes_diarias = solicitudes.filter(fecha_creacion__date=fecha_actual).count()

                    paging = MiPaginador(solicitudes, 10)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    request.session['viewactivo'] = 1
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['solicitudes'] = page.object_list
                    data['url_vars'] = url_vars
                    data['estados'] = MY_ESTADO_SOLICITUD_EQUIPO_COMPUTO
                    data['puedacrearsolicitud'] = configuracionactiva and terminosactivo and periodo_actual and es_estudiante and solicitudes_diarias < 3
                    return render(request, "alu_mundocrai/prestamoequipos.html", data)
                except:
                    pass

            elif action == 'addsolicitudequipo':
                try:
                    form = SolicitudPrestamoECForm()
                    data['form'] = form
                    data['action'] = action
                    data['terminos'] = TerminosCondicionesEquipoComputo.objects.filter(status=True, activo=True).first()
                    data['configuracion'] = ConfiguracionEquipoComputo.objects.filter(status=True, activo=True).first()
                    template = get_template('adm_equiposcomputo/modal/formsolicitudprestamoequipo.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editsolicitudequipo':
                try:
                    data['id'] = id = request.GET['id']
                    solicitud = SolicitudEquipoComputo.objects.get(pk=int(id))
                    form = SolicitudPrestamoECForm(initial=model_to_dict(solicitud))
                    data['form'] = form
                    data['action'] = action
                    data['configuracion'] = ConfiguracionEquipoComputo.objects.filter(status=True, activo=True)[0]
                    template = get_template('adm_equiposcomputo/modal/formsolicitudprestamoequipo.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'detallesolicitud':
                try:
                    id = request.GET['id']
                    data['solicitud'] = solicitud = SolicitudEquipoComputo.objects.get(pk=id)
                    data['termino'] = solicitud.terminos
                    data['historial'] = solicitud.historialsolicitudec_set.filter(status=True).order_by('id')
                    template = get_template('adm_equiposcomputo/modal/verterminoycondicion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Bienvenido al Mundo CRAI - UNEMI'
                data['noticias'] = NoticiasMundoCrai.objects.filter(status=True).order_by('-id')
                return render(request, "alu_mundocrai/view.html", data)
            except Exception as ex:
                pass


def generate_unique_code_ec():
    length = 8
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if not SolicitudEquipoComputo.objects.filter(codigo=code).exists():
            break
    return code