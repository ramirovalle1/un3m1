# -*- coding: UTF-8 -*-
import json
import random
import sys
import calendar
from datetime import datetime, timedelta, date

import openpyxl
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q
import xlwt
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template import Context
from django.template.loader import get_template
from django.urls import reverse
from xlwt import *
from django.shortcuts import render, redirect

from balcon.models import RespuestaEncuestaSatisfaccion
from decorators import secure_module
from sagest.funciones import encrypt_id, encuesta_objeto
from sagest.models import Departamento, SeccionDepartamento, OpcionSistema
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.templatetags.sga_extras import encrypt
from poli.forms import AreaPolideportivoForm
from sga.funciones import MiPaginador, log, generar_nombre, remover_caracteres_especiales_unicode, \
    convertir_fecha_invertida, convertir_fecha
from sga.models import Administrativo, Persona, PersonaDatosFamiliares, MESES_CHOICES
from poli.models import *
from django.db.models import Sum, Q, F, FloatField
from django.db.models.functions import Coalesce


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    hoy=datetime.now().date()
    usuario = request.user
    data['persona']=persona = request.session['persona']
    periodo = request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']

    if request.method == 'POST':
        res_json = []
        action = request.POST['action']
        # ACCIONES DE ANTERIOR POLI
        if action == 'iniciarreservacion':
            try:
                if ReservacionPersonaPoli.objects.filter(status=True, estado=1, persona=persona).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Usted ya cuenta con una reservación en proceso, por favor finalice la pendiente para iniciar otra."})
                instance = AreaPolideportivo.objects.get(id=int(request.POST['id']))
                finicioreserva = convertir_fecha_invertida(request.POST['freserva'])
                if finicioreserva < datetime.now().date():
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Fecha de reservación debe ser mayor o igual a la fecha actual."})
                ffinreserva = finicioreserva + timedelta(days=instance.numdias)
                horaterminar = (datetime.now() + timedelta(minutes=20))
                idactividad=int(request.POST['idactividad'])
                reserva = ReservacionPersonaPoli(persona=persona, area=instance, fechaexpira=horaterminar,actividad_id=idactividad)
                reserva.perfil = perfilprincipal
                if persona.es_estudiante():
                    reserva.inscripcion = perfilprincipal.inscripcion
                reserva.finicialreserva = finicioreserva
                reserva.ffinalreserva = ffinreserva
                reserva.save(request)
                listadias = [fecha for fecha in (finicioreserva, ffinreserva)]
                log(u'{} : Inicio Reservacion de Area Polideportivo {}'.format(persona, instance.__str__()), request, "add")
                url_ = '{}?action=confreservacion&id={}'.format(request.path, encrypt(reserva.id))
                return JsonResponse({"result": "ok", "to": url_})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'terminarExpiracion':
            try:
                with transaction.atomic():
                    idcab = int(encrypt(request.POST['id']))
                    reservacion = ReservacionPersonaPoli.objects.get(pk=idcab)
                    reservacion.estado = 3
                    reservacion.status = False
                    reservacion.save(request)
                    log(u'Finalizo Reservacionpor falta de tiempo: %s' % reservacion, request, "add")
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "mensaje": "Intentelo más tarde."}, safe=False)

        # NUEVAS ACCIONES FUNCIONALES
        if action == 'reservar':
            try:
                fecha=datetime.strptime(request.POST['fecha'],'%Y-%m-%d').date()
                cantidad=0
                tercero=False
                tipotercero=None
                if 'tercero' in request.POST:
                    tercero=True
                    # if not 'tipotercero' in request.POST:
                    #     return JsonResponse(
                    #         {"result": True, "mensaje": "Seleccione el tipo de acompañantes que desea incluir."})
                    # tipotercero= int(request.POST['tipotercero'])
                    tipotercero=3
                if not request.POST['horario']:
                    transaction.set_rollback(True)
                    return JsonResponse(
                        {"result": True, "mensaje": "Seleccione un horario a reservar."})
                horario=HorarioActividadPolideportivo.objects.get(id=request.POST['horario'])
                seccionesarea = horario.actividad.area.secciones()
                turno=horario.generar_turno(str(persona))
                reserva = ReservacionPersonaPoli(persona=persona,
                                                 area=horario.actividad.area,
                                                 estado= 2,
                                                 actividad=horario.actividad,
                                                 tercero=tercero,
                                                 tipotercero=tipotercero,
                                                 codigo=turno)
                reserva.perfil = perfilprincipal
                if persona.es_estudiante():
                    reserva.inscripcion = perfilprincipal.inscripcion
                reserva.finicialreserva = fecha
                reserva.ffinalreserva = fecha

                turnos = horario.cupos_reservados(fecha)
                # if tercero and tipotercero == 2 :
                #     if not 'cantidad' in request.POST or int(request.POST['cantidad'])==0:
                #         transaction.set_rollback(True)
                #         return JsonResponse({"result": True, "mensaje": "La cantidad de externos no tiene que ser 0."})
                #     cantidad=int(request.POST['cantidad'])
                #     if not cantidad < turnos:
                #         transaction.set_rollback(True)
                #         return JsonResponse({"result": True, "mensaje": "La cantidad de externos excede el limite por turno."})
                #     reserva.cantidad=int(request.POST['cantidad'])
                reserva.save(request)

                reservacionfecha=ReservacionFechasPoli(reservacion=reserva, freservacion=hoy)
                reservacionfecha.save(request)

                reservacionturno = ReservacionTurnosPoli(fechareservacion=reservacionfecha, turno=horario)
                reservacionturno.save(request)

                # if tercero and tipotercero == 1:
                #     familiares = request.POST.getlist('familiares[]')
                #     cantidad=len(familiares)
                #     if familiares:
                #         f = 0
                #         if not cantidad <= turnos:
                #             transaction.set_rollback(True)
                #             return JsonResponse({"result": True, "mensaje": "La cantidad de familiares excede el limite por turno."})
                #         while f < len(familiares):
                #             reservatercero = ReservacionTercerosPoli(reservacion=reservacionturno,familiar_id=int(familiares[f]))
                #             reservatercero.save(request)
                #             f += 1
                #         reservatercero.save(request)
                #         log(u'Adicionó Terceros: %s' % reservatercero, request, "add")
                #         # return JsonResponse({"result": False}, safe=False)
                #     else:
                #         transaction.set_rollback(True)
                #         return JsonResponse({"result": True, "mensaje": "Registre al menos un Familiar."})

                if tercero:
                    grupointerno = request.POST.getlist('grupointerno[]')
                    cantidad=len(grupointerno)
                    maxgrupo=horario.actividad.numacompanantes
                    if cantidad > maxgrupo:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Cantida máxima de acompañantes permitido {}".format(maxgrupo)})

                    if grupointerno:
                        g = 0
                        if not cantidad <= turnos:
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "La cantidad de acompañantes excede el limite por turno."})
                        while g < len(grupointerno):
                            reservatercero = ReservacionTercerosPoli(reservacion=reservacionturno,persona_id=int(grupointerno[g]))
                            reservatercero.save(request)
                            g += 1
                        reservatercero.save(request)
                        log(u'Adicionó Terceros: %s' % reservatercero, request, "add")
                        # return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Registre al menos un acompañante."})

                if seccionesarea:
                    if not 'seccion[]' in request.POST:
                        transaction.set_rollback(True)
                        return JsonResponse(
                            {"result": True, "mensaje": 'Por favor seleccione la sección en la que desea reservar'})
                    cantidad+=1
                    seccionesmarcadas = request.POST.getlist('seccion[]')
                    if cantidad > 1:
                        cupos = horario.actividad.area.cantidad_cupo_secciones(horario,seccionesmarcadas, fecha)
                        if cantidad <= cupos:
                            comprobador=cantidad
                            cont=0
                            cupos1=0
                            listaordenada=[]
                            dicordenado=horario.actividad.area.listado_cupos(horario,seccionesmarcadas, fecha)
                            for dic in dicordenado:
                                cont+=1
                                cupos1+=dic.get('cupos')
                                if comprobador <= cupos1 and len(seccionesmarcadas) > 1 and cont < len(seccionesmarcadas):
                                    transaction.set_rollback(True)
                                    return JsonResponse(
                                        {"result": True,
                                         "mensaje": 'La cantidad de externos o familiares pueden ingresar en menos secciones que las que selecciono.'})
                                listaordenada.append(dic.get('id'))
                            for idseccion in listaordenada:
                                seccion=seccionesarea.get(id=idseccion)
                                seccionreserva = ReservacionSeccionPoli(reservacionturno=reservacionturno,seccion=seccion)
                                seccionreserva.save(request)
                                reservacionturno.seccion.add(seccion)
                                cuposeccion = seccion.cupo_disponible_seccion(fecha,horario)
                                # if tipotercero == 2:
                                if cantidad >= cuposeccion:
                                    cantidad-=cuposeccion
                                    seccionreserva.cantidad=cuposeccion
                                elif cantidad != 0:
                                    seccionreserva.cantidad=cantidad
                                    cantidad = 0
                                seccionreserva.save(request)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse(
                                {"result": True, "mensaje": 'El número de secciones seleccionados no cubre el número de extras asignados'})
                    elif len(seccionesmarcadas) == 1:
                        idseccion=eval(seccionesmarcadas[0])
                        seccionreserva = ReservacionSeccionPoli(reservacionturno=reservacionturno, seccion_id=idseccion, cantidad=cantidad)
                        seccionreserva.save(request)
                        for seccion in seccionesmarcadas:
                            reservacionturno.seccion.add(seccion)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse(
                            {"result": True, "mensaje": 'Al ser solo una reservación para su persona, solo debe seleccionar una sección.'})
                log(u'{} : Inicio Reservacion de Area Polideportivo {}'.format(persona, horario.actividad.area.__str__()), request, "add")
                url_ = '{}?action=misreservas'.format(request.path)
                return JsonResponse({"result": False, "to": url_})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'delreserva':
            try:
                with transaction.atomic():
                    reserva= ReservacionPersonaPoli.objects.get(id=int(request.POST['id']))
                    if reserva.puede_cancelar() == False:
                        res_json = {"error": True, "message": "El tiempo para cancelar una reserva finalizo, usted ya no puede cancelar esta reserva."}
                        return JsonResponse(res_json, safe=False)
                    reserva.estado = 3
                    reserva.save(request)

                    reservafechas = reserva.reservacionfechaspoli_set.get(status=True)
                    reservafechas.status = False
                    reservafechas.save(request)

                    reservaturno = reservafechas.reservacionturnospoli_set.get(status=True)
                    reservaturno.status = False
                    reservaturno.save(request)

                    reservafamiliar = reservaturno.reservaciontercerospoli_set.filter(status=True)
                    if reservafamiliar:
                        for familiar in reservafamiliar:
                            familiar.status = True
                            familiar.save(request)

                    reservacionseccion = reservaturno.reservacionseccionpoli_set.filter(status=True)
                    for reservaseccion in reservacionseccion:
                        reservaseccion.status = False
                        reservaseccion.save(request)

                    log(u'Anulo Reservacion: %s' % reserva, request, "delreserva")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'buscarpersonas':
            try:
                item = []
                param = request.POST['term'].upper().strip()
                s = param.split(" ")
                perfiles=PerfilUsuario.objects.filter((Q(administrativo__isnull=False) | Q(inscripcion__isnull=False) | Q(profesor__isnull=False)), status=True, externo__isnull=True).order_by('persona_id').distinct('persona_id').values_list('persona_id')
                personas=Persona.objects.filter(status=True, id__in=perfiles).exclude(id=persona.id)
                if len(s) == 1:
                    personas = personas.filter((Q(nombres__icontains=param) |
                                           Q(apellido1__icontains=param) |
                                           Q(apellido2__icontains=param) |
                                           Q(cedula__contains=param))).distinct()[:15]
                elif len(s) == 2:
                    personas = personas.filter((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) |
                                          (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) |
                                          (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1]))).distinct()[:15]
                else:
                    personas = personas.filter((Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(apellido2__contains=s[2])) |
                                               (Q(nombres__contains=s[0]) & Q(nombres__contains=s[1]) & Q(apellido1__contains=s[2]))).distinct()[:15]

                for p in personas:
                    text = str(p)
                    item.append({'id': p.id, 'text': text})

                return JsonResponse(item, safe=False)
            except Exception as e:
                pass

        if action == 'deltercero':
            try:
                with transaction.atomic():
                    id=int(encrypt(request.POST['id']))
                    reservatercero = ReservacionTercerosPoli.objects.get(status=True, id=id)
                    reservatercero.status=False
                    reservatercero.save(request)
                    log(u'Elimino reserva de tercero: %s' % reservatercero, request, "deltercero")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        # CALIFICAR ENCUESTA:
        elif action == 'calificarencuesta':
            try:
                reservapersona = ReservacionPersonaPoli.objects.get(id=encrypt_id(request.POST['id']))
                content_type = ContentType.objects.get_for_model(reservapersona)
                preguntas = reservapersona.actividad.preguntas_encuesta()
                preguntasresueltas = json.loads(request.POST.get('lista_items1'))
                msg_error = 'Por favor complete la encuestas, marcando por lo menos una estrella en cada pregunta'
                if not len(preguntas) == len(preguntasresueltas):
                    raise NameError(msg_error)
                for pregunta in preguntasresueltas:
                    if int(pregunta['valoracion']) == 0:
                        raise NameError(msg_error)
                    respuesta = RespuestaEncuestaSatisfaccion(
                                pregunta_id=int(encrypt(pregunta['pregunta_id'])),
                                valoracion=int(pregunta['valoracion']),
                                observacion=pregunta['observacion'],
                                object_id=reservapersona.id,
                                content_type=content_type)
                    respuesta.save(request)
                    log(u'Calificó pregunta de modelo: %s' % reservapersona, request, "add")
                return JsonResponse({"result": False, "mensaje": "Se guardo correctamente la encuesta de satisfacción"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "%s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            #CREADAS EN ANTERIOR POLI
            if action == 'confreservacion':
                try:
                    data['title'] = u'Confirmación Reserva de espacios deportivos'
                    data['id'] = id = encrypt(request.GET['id'])
                    data['area']=area=AreaPolideportivo.objects.get(pk=int(id))
                    data['politicas']=PoliticaPolideportivo.objects.filter(status=True, area=area)
                    lista=[]
                    perfil=None
                    carrera=None
                    actividades = ActividadPolideportivo.objects.filter(area=int(id), mostrar=True, status=True).order_by('nombre')
                    if perfilprincipal.es_estudiante():
                        perfil=1
                        carrera=perfilprincipal.inscripcion.carrera
                        actividades=actividades.filter(Q(carreras=carrera) | Q(carreras=None))
                    elif perfilprincipal.es_administrativo():
                        perfil=2
                    elif perfilprincipal.es_profesor():
                        perfil=3
                    elif perfilprincipal.es_externo():
                        perfil=4

                    for actividad in actividades:
                        perfiles=PerfilesActividad.objects.filter(status=True, actividad=actividad)
                        if perfiles.filter(perfil=perfil, activo=True).exists():
                            lista.append(actividad)
                    data['actividades']=lista
                    return render(request, 'alu_reservapolideportivo/listactividades.html', data)
                except Exception as ex:
                    messages.error(request, str(ex))
                    return redirect(request.path)

            if action == 'listactividad':
                try:
                    id=request.GET['idarea']
                    # data['actividad']=actividad=ActividadPolideportivo.objects.get(id=id)
                    horarios=HorarioActividadPolideportivo.objects.filter(status=True, actividad__area_id=id)
                    # horarioinicio=horarios.order_by('fechainicio').first()
                    # horariofin=horarios.order_by('fechafin').last()
                    rangofechas=[]
                    # ban=True
                    # if horarios:
                    #     if horarioinicio.fechainicio < datetime.now().date():
                    #         ban=False
                    #         for horario in horarios.order_by('fechainicio'):
                    #            if horario.fechainicio >= datetime.now().date():
                    #                horarioinicio=horario
                    #                ban = True
                    #                break
                    #     if ban:
                    #         fi = horarioinicio.fechainicio
                    #         ff = horariofin.fechafin
                    if 'fechainicio' in request.GET and 'fechafin' in request.GET:
                        fi= convertir_fecha_invertida(request.GET['fechainicio'])
                        ff = convertir_fecha_invertida(request.GET['fechafin'])
                        for horario in horarios:
                            if fi >= horario.fechainicio and ff <= horario.fechafin:
                                # instance=str(horario.id) + horario.actividad.nombre
                                # rangofechas.append(instance)
                                # actividad=ActividadPolideportivo.objects.get(status=True, pk=horario.actividad.id)
                                # if not (next((x for x in rangofechas if x["id"] == actividad.id), False)) :
                                rangofechas.append(horario)
                        data['horarios']=rangofechas

                    # for day in range((ff - fi).days + 1):
                    #     fechafiltro = fi + timedelta(days=day)
                    #     # rangofechas.append("{} {}".format((fechadesde + timedelta(days=day)).strftime("%d"), (fechadesde + timedelta(days=day)).strftime("%b")))
                    #     rangofechas.append(fechafiltro)
                    # data['rangofechas']=rangofechas
                    template = get_template("alu_reservapolideportivo/modal/listturnos.html")
                    return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    mensaje = 'Intentelo mas tarde'
                    return JsonResponse({"result": 'bad', "mensaje": mensaje})

            if action == 'listturnos':
                try:
                    if 'fecha' in request.GET:
                        id = request.GET['idactividad']
                        data['actividad']=ActividadPolideportivo.objects.get(pk=id)
                        data['fecha'] = fecha=request.GET['fecha']
                        fecha = convertir_fecha_invertida(fecha)
                        dia=fecha.weekday()+1
                        horarios = HorarioActividadPolideportivo.objects.filter(status=True,
                                                                                actividad_id=id,
                                                                                dia=dia,
                                                                                fechainicio__lte=fecha,
                                                                                fechafin__gte=fecha)
                        horariosactividad = []
                        for horario in horarios:
                            if fecha >= hoy:
                                horariosactividad.append(horario)
                        data['horarios'] = horariosactividad
                    template = get_template("alu_reservapolideportivo/modal/listturnos.html")
                    return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    mensaje = 'Intentelo mas tarde'
                    return JsonResponse({"result": 'bad', "mensaje": mensaje})

            #NUEVAS ACCIONES FUNCIONALES
            if action == 'selturnos':
                try:
                    actividad = ActividadPolideportivo.objects.get(pk=request.GET['actividadid'])
                    if ReservacionPersonaPoli.objects.filter(status=True,actividad=actividad ,estado__in=[1, 2], persona=persona).exists():
                        return JsonResponse({"result": False,"reservado":True,
                                             "mensaje": u"Usted ya cuenta con una reservación de esta actividad en proceso, por favor finalice o cancele la pendiente para iniciar otra."})

                    horariosid = request.GET.getlist("listaid[]")
                    if not type(eval(horariosid[0])) is int:
                        horariosid = list(eval(horariosid[0]))
                    data['fecha']=request.GET['fecha']
                    data['actividad']=actividad
                    data['horarios']=horario=HorarioActividadPolideportivo.objects.filter(id__in=horariosid, status=True, mostrar=True).order_by('id')
                    data['horariodia']=horario.first()
                    data['familiares']=PersonaDatosFamiliares.objects.filter(status=True,persona=persona)
                    data['tipoterceros']=TIPO_TERCERO
                    data['secciones']=SeccionPolideportivo.objects.filter(status=True, area=actividad.area, mostrar=True).order_by('id')
                    template = get_template("alu_reservapolideportivo/formreserva.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'cargarcalendario':
                try:
                    fecha = datetime.now().date()
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

                    id = request.GET['idactividad']
                    s_anio = panio
                    s_mes = pmes
                    s_dia = 1
                    data['mes'] = MESES_CHOICES[s_mes - 1]
                    data['ws'] = [0, 7, 14, 21, 28, 35]
                    lista = {}
                    listahorarios = []
                    data['actividad'] = actividad = ActividadPolideportivo.objects.get(pk=id)
                    data['horarios'] = horarios = HorarioActividadPolideportivo.objects.filter(status=True,
                                                                                               actividad_id=id,
                                                                                               # mostrar=True,
                                                                                               fechafin__gte=hoy,
                                                                                               )

                    diasreserva = actividad.area.numdias
                    anio_actual = hoy.year
                    if hoy.month != s_mes:
                        anioubicado = s_anio
                        cont = 0
                        while anioubicado >= anio_actual:
                            iden = True
                            if anio_actual == anioubicado and cont == 0:
                                mes = hoy.month
                                mesubicado = s_mes
                            elif anio_actual == anioubicado:
                                mes = hoy.month
                                mesubicado = 12
                            elif anio_actual < anioubicado and cont == 0:
                                mes = 0
                                mesubicado = s_mes
                            elif anio_actual < anioubicado:
                                mes = 0
                                mesubicado = 12
                            while mesubicado > mes:
                                if anio_actual < anioubicado and iden:
                                    mes = 1
                                    iden=False
                                numsinhorario = 0
                                msiguiente = calendar.monthrange(s_anio, mes)
                                rango = range(1, int(msiguiente[1] + 1), 1)
                                if mes == hoy.month:
                                    rango = range(int(hoy.day), int(msiguiente[1] + 1), 1)
                                for dia in rango:
                                    ban = False
                                    fecha = date(s_anio, mes, dia)
                                    numdia = fecha.weekday() + 1
                                    for horario in horarios:
                                        if horario.dia == numdia:
                                            ban = True
                                    if ban == False:
                                        numsinhorario += 1
                                diasreserva += numsinhorario
                                if mes == hoy.month:
                                    diasreserva -= msiguiente[1] - (hoy.day - 1)
                                else:
                                    diasreserva = diasreserva - msiguiente[1]

                                mes += 1
                            cont += 1
                            anioubicado -= 1

                    for i in range(1, 43, 1):
                        dia = {i: 'no'}
                        lista.update(dia)
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
                            lista.update(dia)
                            # if horarios:
                            #     data['ultimafecha'] = ultimafecha = horarios.order_by('fechafin').last()
                            #     data['year'] = ultimafecha.fechafin.year

                            listhorario = []
                            sinhorario = True
                            puedereservar = False
                            numerodia = fecha.weekday() + 1
                            if fecha >= hoy:
                                turnos = 0
                                listturnos = []
                                for horario in horarios:
                                    if horario.dia == numerodia and fecha <= horario.fechafin:
                                        listhorario.append(horario.id)
                                if listhorario:
                                    sinhorario = False
                                    filter = horarios.filter(status=True, pk__in=listhorario)
                                    for horario in filter:
                                        listturnos.append(horario.turno.comienza)
                                        turnos += horario.cupos_reservados(fecha)

                                monthRange = calendar.monthrange(s_anio, s_mes)
                                if diasreserva > 0 and s_dia <= monthRange[1] and not sinhorario:
                                    ordenadas = []
                                    ordenadas = sorted(listturnos, reverse=True)
                                    if ordenadas[0] > datetime.now().time() or fecha > datetime.now().date():
                                        puedereservar = True
                                        diasreserva -= 1
                                diccionario = {'dia': s_dia, 'turnos': turnos, 'listahorario': listhorario,
                                               'sinhorario': sinhorario, 'fecha': fecha, 'puedereservar': puedereservar}
                                listahorarios.append(diccionario)
                            s_dia += 1

                    if horarios:
                        data['ultimafecha'] = ultimafecha = horarios.order_by('fechafin').last().fechafin
                        primerafecha = horarios.order_by('fechafin').first().fechafin
                        anio = primerafecha.year
                        rango = ultimafecha.year - primerafecha.year
                        for i in range(0, rango, 1):
                            if s_anio == anio + (i + 1):
                                anio = s_anio
                        data['year'] = anio
                    data['dias_mes'] = lista
                    data['dwnm'] = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
                    data['dwn'] = [1, 2, 3, 4, 5, 6, 7]
                    data['daymonth'] = 1
                    data['s_anio'] = s_anio
                    data['s_mes'] = s_mes
                    data['lista'] = lista
                    data['hoy']=hoy
                    data['hoy_dia'] = hoy.day
                    data['hoy_mes'] = hoy.month
                    data['listahorarios'] = listahorarios
                    ultimo_dia = calendar.monthrange(hoy.year, hoy.month)[1]
                    data['fechaactual'] = date(hoy.year, hoy.month, ultimo_dia)
                    data['fechacalendario'] = date(s_anio, s_mes, s_dia - 1)
                    template = get_template("alu_reservapolideportivo/calendarioreservas.html")
                    return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'verpoliticas':
                try:
                    data['title'] = u'Políticas'
                    data['politicas']=politicas=PoliticaPolideportivo.objects.filter(status=True, mostrar=True).order_by('id')
                    return render(request, 'alu_reservapolideportivo/politicas.html', data)
                except Exception as ex:
                    messages.error(request, str(ex))
                    return redirect(request.path)

            if action == 'veractividades':
                try:
                    data['title'] = u'Actividades desponibles'
                    data['id'] = id = encrypt(request.GET['id'])
                    data['area'] = area = AreaPolideportivo.objects.get(pk=int(id))
                    data['actividades']=actividades = ActividadPolideportivo.objects.filter(area=area, mostrar=True, status=True).order_by('nombre')
                    template = get_template("alu_reservapolideportivo/modal/listactividades.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result":False, 'mensaje':ex})

            if action == 'reservar':
                try:
                    if perfilprincipal.es_estudiante() and not perfilprincipal.inscripcion.matriculado():
                        messages.error(request, 'Usted no cuenta con una matrícula activa, por lo que no puede realizar una reserva con este perfil.')
                        return redirect(request.path)
                    data['title']='Reservar'
                    fecha = datetime.now().date()
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

                    id = request.GET['idactividad']
                    s_anio = panio
                    s_mes = pmes
                    s_dia = 1
                    data['mes'] = MESES_CHOICES[s_mes - 1]
                    data['ws'] = [0, 7, 14, 21, 28, 35]
                    lista = {}
                    listahorarios = []
                    data['actividad'] = actividad = ActividadPolideportivo.objects.get(pk=id)
                    data['horarios'] = horarios = HorarioActividadPolideportivo.objects.filter(status=True,
                                                                                               actividad_id=id,
                                                                                               mostrar=True,
                                                                                               fechafin__gte=hoy,
                                                                                               )

                    diasreserva = actividad.area.numdias
                    if hoy.month != s_mes:
                        mes = hoy.month
                        mesubicado = s_mes
                        while mesubicado > mes:
                            numsinhorario = 0
                            msiguiente = calendar.monthrange(s_anio, mes)
                            rango = range(1, int(msiguiente[1] + 1), 1)
                            if mes == hoy.month:
                                rango = range(int(hoy.day), int(msiguiente[1] + 1), 1)
                            for dia in rango:
                                ban = False
                                fecha = date(s_anio, mes, dia)
                                numdia = fecha.weekday() + 1
                                for horario in horarios:
                                    if horario.dia == numdia:
                                        ban = True
                                if ban == False:
                                    numsinhorario += 1
                            diasreserva += numsinhorario
                            if mes == hoy.month:
                                diasreserva -= msiguiente[1] - (hoy.day - 1)
                            else:
                                diasreserva = diasreserva - msiguiente[1]

                            mes += 1

                    for i in range(1, 43, 1):
                        dia = {i: 'no'}
                        lista.update(dia)
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
                            lista.update(dia)
                            if horarios:
                                data['ultimafecha'] = ultimafecha = horarios.order_by('fechafin').last()
                                data['year'] = ultimafecha.fechafin.year

                            listhorario = []
                            sinhorario = True
                            puedereservar = False
                            numerodia = fecha.weekday() + 1
                            if fecha >= hoy:
                                turnos = 0
                                listturnos = []
                                for horario in horarios:
                                    if horario.dia == numerodia:
                                        listhorario.append(horario.id)
                                if listhorario:
                                    sinhorario = False
                                    filter = horarios.filter(status=True, pk__in=listhorario)
                                    for horario in filter:
                                        listturnos.append(horario.turno.comienza)
                                        turnos += horario.cupos_reservados(fecha)

                                monthRange = calendar.monthrange(s_anio, s_mes)
                                if diasreserva > 0 and s_dia <= monthRange[1] and not sinhorario:
                                    ordenadas = []
                                    ordenadas = sorted(listturnos, reverse=True)
                                    if ordenadas[0] > datetime.now().time() or fecha > datetime.now().date():
                                        puedereservar = True
                                        diasreserva -= 1
                                diccionario = {'dia': s_dia, 'turnos': turnos, 'listahorario': listhorario,
                                               'sinhorario': sinhorario, 'fecha': fecha, 'puedereservar': puedereservar}
                                listahorarios.append(diccionario)
                            s_dia += 1
                    data['dias_mes'] = lista
                    data['dwnm'] = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
                    data['dwn'] = [1, 2, 3, 4, 5, 6, 7]
                    data['daymonth'] = 1
                    data['s_anio'] = s_anio
                    data['s_mes'] = s_mes
                    data['lista'] = lista
                    data['hoy_dia'] = hoy.day
                    data['hoy_mes'] = hoy.month
                    data['listahorarios'] = listahorarios
                    data['fechainicio'] = date(datetime.now().year, 1, 1)
                    data['fechafin'] = datetime.now().date()
                    return render(request, 'alu_reservapolideportivo/reservar.html', data)
                except Exception as ex:
                    messages.error(request, str(ex))
                    return redirect(request.path)

            # HISTORIAL DE RESERVACION
            if action == 'inforeserva':
                try:
                    id=int(request.GET['id'])
                    data['reserva']=reserva=ReservacionTurnosPoli.objects.get(pk=id)
                    data['reservafamiliares']=familiares=ReservacionTercerosPoli.objects.filter(status=True,reservacion=reserva)
                    data['cantidadreserva']=reserva.fechareservacion.reservacion.cantidad+len(familiares)+1
                    data['title']=reserva.turno.fechainicio
                    template=get_template('alu_reservapolideportivo/modal/inforeserva.html')
                    return JsonResponse({'result':'ok','data':template.render(data)})
                except Exception as ex:
                    pass

            if action == 'misreservas':
                try:
                    data['title'] = u'Historial Reservaciones'
                    filtro = request.GET.get('f', '')
                    search, filtros, url_vars = request.GET.get('search', ''), Q(fechareservacion__reservacion__status=True),f'&action={action}'

                    if filtro== 'progreso':
                        filtros = filtros & Q(
                            fechareservacion__reservacion__persona=persona,
                            fechareservacion__reservacion__finicialreserva__gte=hoy,
                            fechareservacion__reservacion__estado__in=[1, 2],
                            )
                        request.session['viewactivo'] = 2
                    elif filtro == 'finalizado':
                        filtros = filtros & Q(
                            fechareservacion__reservacion__persona=persona,
                            fechareservacion__reservacion__finicialreserva__lt=hoy,
                            fechareservacion__reservacion__estado=4)
                        request.session['viewactivo'] = 3
                    elif filtro == 'anulado':
                        filtros = filtros & Q(
                            fechareservacion__reservacion__persona=persona,
                            fechareservacion__reservacion__estado=3)
                        request.session['viewactivo'] = 4
                    else:
                        filtros = filtros & Q(fechareservacion__reservacion__persona=persona)
                        request.session['viewactivo'] = 1
                    if search:
                        data['search'] = search
                        s = search.split()
                        if len(s) == 1:
                            filtros = filtros & (Q(fechareservacion__reservacion__codigo__unaccent__icontains=search) |
                                                    Q(fechareservacion__reservacion__actividad__nombre__unaccent__icontains=search))
                        else:
                            filtros = filtros & (Q(fechareservacion__reservacion__actividad__nombre__unaccent__icontains=s[0]) &
                                                    Q(fechareservacion__reservacion__actividad__nombre__unaccent__icontains=s[1]))
                        url_vars += '&search={}'.format(search)
                    if filtro != '':
                        url_vars += '&f={}'.format(filtro)
                    reservas = ReservacionTurnosPoli.objects.filter(filtros).order_by('-pk')
                    paging = MiPaginador(reservas, 5)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data["url_vars"] = url_vars
                    data['filtro']=filtro
                    data['reservas'] = page.object_list
                    return render(request, 'alu_reservapolideportivo/verreservas.html',data)
                except Exception as ex:
                    pass

            if action == 'acompanantes':
                try:
                    id = int(encrypt(request.GET['id']))
                    data['reserva'] = reserva = ReservacionTurnosPoli.objects.get(pk=id)
                    template = get_template('alu_reservapolideportivo/modal/infoacompanantes.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'calificarencuesta':
                try:
                    actividad = ActividadPolideportivo.objects.get(id=encrypt_id(request.GET['id']))
                    data['encuesta'] = encuesta = encuesta_objeto(actividad).filter(vigente=True).first()
                    data['id'] = encrypt_id(request.GET['idex'])
                    template = get_template("alu_reservapolideportivo/modal/formencuesta.html")
                    json_content = template.render(data, request=request)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"%s" % ex.__str__()})
        else:
            data['title'] = u'Reserva de espacios deportivos'
            data['perfilprincipal']=perfilprincipal
            qsareas = AreaPolideportivo.objects.filter(status=True,en_mantenimiento=False).order_by('nombre')
            data['politicas']=politicas=PoliticaPolideportivo.objects.filter(status=True, general=True, mostrar=True).order_by('id')
            if ReservacionPersonaPoli.objects.values('id').filter(status=True, estado=1, persona=persona).exists():
                data['tiene_reserva_iniciada'] = ReservacionPersonaPoli.objects.values('id').filter(status=True, estado=1, persona=persona).first()
            data['areas_disponibles'] = qsareas
            return render(request, 'alu_reservapolideportivo/view1.html', data)