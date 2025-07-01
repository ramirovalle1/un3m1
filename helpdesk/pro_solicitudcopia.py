# -*- coding: UTF-8 -*-
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, F
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log

# Proceso Solicitud Copias
from helpdesk.forms import SolicitudCopiasForm
from helpdesk.models import DetalleJornadaImpresora, SolicitudCopia, HistorialSolicitudCopia
from sga.models import Profesor
import sys
from sga.templatetags.sga_extras import encrypt
import time


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':
        data['action'] = action = request.POST['action']

        if action == 'adicionar':
            try:
                f = SolicitudCopiasForm(request.POST)
                # obtener profesor
                profesor = Profesor.objects.get(persona=persona)
                if f.is_valid() and f.validador(0, profesor):
                    # parametros requeridos para llamar a la función
                    fagendarhorainicio = datetime.strptime(f"{request.POST['fechaagendada']} {request.POST['horainicio']}", "%Y-%m-%d %H:%M")
                    # eliminar segundos a fecha agendada y hora inicio ingresada en el formulario
                    fagendarhorainicio = datetime(fagendarhorainicio.year, fagendarhorainicio.month, fagendarhorainicio.day,
                                                  fagendarhorainicio.hour, fagendarhorainicio.minute, 0)
                    # llamar función calculo de hora fin, verificacion de horario disponible y verificacion de conflicto de fecha u horario especificando que es el proceso action calcular horafin
                    respuestajson, datos =  \
                        calcularhorafin_verificardisponibilidadhorario_conflictohorario(request,0, 2, fagendarhorainicio, profesor)
                    if respuestajson:
                        return respuestajson
                    # Calcular tiempo requerido con base en registro reciente de models Configuracion Copia
                    # configuracioncopia = f.cleaned_data['detallejornadaimpresora'].configuracioncopia
                    # redondear los minutos
                    # tiemporequeridomin = int(null_to_decimal((f.cleaned_data['cantidadcopia'] * configuracioncopia.tiempo) / configuracioncopia.cantidad,0))
                    # cabecera
                    solicitudcopia = SolicitudCopia(
                                             fechaagendada=f.cleaned_data['fechaagendada'],
                                             profesor=profesor,
                                             cantidadcopia= f.cleaned_data['cantidadcopia'],
                                             horainicio=f.cleaned_data['horainicio'],
                                             horafin=datos['horafin'],
                                             tiemporequerido=minutos_a_horaminuto(datos['tiemporequeridomin']),
                                             detallejornadaimpresora=datos['detallejornadaimpresora'],
                                             estado=1)
                    #detalle
                    historialsolicitudcopia = HistorialSolicitudCopia(fecha=datetime.now().date(),
                                             persona=persona,
                                             solicitudcopia=solicitudcopia,
                                             observacion=f.cleaned_data['observacion'],
                                             estado=1)
                    #guardar cabecera y detalle
                    solicitudcopia.save(request)
                    historialsolicitudcopia.save(request)
                    log(u'Adicionó nueva Solicitud de Copia: %s' % solicitudcopia, request, "adicionar")
                    log(u'Adicionó nuevo Historial de Solicitud de Copia: %s' % historialsolicitudcopia, request, "adicionar")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                         "mensaje": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos {}. \n Error on line {}".format(ex, sys.exc_info()[-1].tb_lineno)}, safe=False)


        elif action == 'edit':
            with transaction.atomic():
                try:
                    filtro = SolicitudCopia.objects.get(pk=int(encrypt(request.POST['id'])))
                    if filtro.estado != 1:
                        return JsonResponse({'error': True, "message": u"Acción no permitida. Sólo podrá editar mientras su solicitud esté en estado solicitado."}, safe=False)
                    f = SolicitudCopiasForm(request.POST)
                    # obtener profesor
                    profesor = Profesor.objects.get(persona=persona)
                    if f.is_valid() and f.validador(filtro.id, profesor):
                        # parametros requeridos para llamar a la función
                        fagendarhorainicio = datetime.strptime(f"{request.POST['fechaagendada']} {request.POST['horainicio']}", "%Y-%m-%d %H:%M")
                        # eliminar segundos a fecha agendada y hora inicio ingresada en el formulario
                        fagendarhorainicio = datetime(fagendarhorainicio.year, fagendarhorainicio.month, fagendarhorainicio.day,
                                                      fagendarhorainicio.hour, fagendarhorainicio.minute, 0)
                        # llamar función calculo de hora fin, verificacion de horario disponible y verificacion de conflicto de fecha u horario especificando que es el proceso action calcular horafin
                        respuestajson, datos = calcularhorafin_verificardisponibilidadhorario_conflictohorario(request, filtro.id, 2, fagendarhorainicio, profesor)
                        if respuestajson:
                            return respuestajson
                        # cabecera
                        filtro.fechaagendada=f.cleaned_data['fechaagendada']
                        # filtro.profesor=profesor
                        filtro.cantidadcopia=f.cleaned_data['cantidadcopia']
                        filtro.horainicio=f.cleaned_data['horainicio']
                        filtro.horafin=datos['horafin']
                        filtro.tiemporequerido=minutos_a_horaminuto(datos['tiemporequeridomin'])
                        filtro.detallejornadaimpresora=datos['detallejornadaimpresora']
                        # filtro.estado=1

                        # detalle/historial solicitud de copias
                        filtrodetalle = filtro.historialsolicitudcopia_set.filter(status=True).order_by('id').first()
                        # fecha en que realiza la solicitud de copias el docente
                        # filtrodetalle.fecha=datetime.now().date()
                        # filtrodetalle.persona=persona
                        # filtrodetalle.solicitudcopia=solicitudcopia
                        filtrodetalle.observacion=f.cleaned_data['observacion']
                        # filtrodetalle.estado=1
                        # guardar cabecera y detalle
                        filtro.save(request)
                        filtrodetalle.save(request)
                        log(u'Editó Solicitud de Copia: %s' % filtro, request, "edit")
                        log(u'Editó Historial de Solicitud de Copia: %s' % filtrodetalle, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in f.errors.items()],
                                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)
        # ERROR
        # if action == 'delserviciodep':
        #     with transaction.atomic():
        #         try:
        #             instancia = DepartamentoServicio.objects.get(pk=int(encrypt(request.POST['id'])))
        #             instancia.status = False
        #             instancia.save(request)
        #             log(u'Elimino Departamento Servicio de citas: %s' % instancia, request, "delservicio")
        #             res_json = {"error": False}
        #         except Exception as ex:
        #             res_json = {'error': True, "message": "Error: {}".format(ex)}
        #         return JsonResponse(res_json, safe=False)

        elif action == 'del':
            with transaction.atomic():
                try:
                    instancia = SolicitudCopia.objects.get(pk=int(encrypt(request.POST['id'])))
                    # if not instancia.puede_eliminar():
                    #     return JsonResponse({'error': True,
                    #                          "message": u"Este registro se encuentra en uso, no es posible eliminar."},
                    #                         safe=False)
                    if instancia.estado != 1:
                        return JsonResponse({'error': True,
                                             "message": u"Acción no permitida. Sólo podrá eliminar mientras su solicitud esté en estado solicitado."},
                                            safe=False)
                    instancia.status = False
                    for historialsolicitudcopia in instancia.historialsolicitudcopia_set.filter(status=True):
                        historialsolicitudcopia.status = False
                        historialsolicitudcopia.save(request)
                    instancia.save(request)
                    # log(u'Eliminó Historial de Solicitud de copias: %s' % instancia.historialsolicitudcopia_set.filter(status=True), request, "del")
                    log(u'Eliminó Solicitud de Solicitud de copias: %s' % instancia, request, "del")
                    res_json = {"error": False}
                    return JsonResponse(res_json, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)


        # calcular hora fin
        elif action == 'calcularhorafin':
            with transaction.atomic():
                try:
                    # validar que esten llenos los campos necesarios para el proceso cacular la hora fin
                    if request.POST['fechaagendada'] and request.POST['cantidadcopia'] and request.POST['horainicio']:
                        # inicio validaciones permitentes para el proceso calcular hora de fin
                        # fecha agendada y hora inicio ingresada en el formulario
                        fagendarhorainicio = datetime.strptime(f"{request.POST['fechaagendada']} {request.POST['horainicio']}", "%Y-%m-%d %H:%M")
                        # eliminar segundos a fecha agendada y hora inicio ingresada en el formulario
                        fagendarhorainicio = datetime(fagendarhorainicio.year, fagendarhorainicio.month, fagendarhorainicio.day,
                                                      fagendarhorainicio.hour, fagendarhorainicio.minute, 0)
                        if fagendarhorainicio.date() < datetime.now().date():
                            return JsonResponse({'result': 'bad',
                                                "mensaje": 'La fecha a agendar debe ser igual o posterior a la fecha actual.'})
                        else:
                            # fecha hora actual con cero segundos
                            fechahoraactual = datetime(datetime.now().year, datetime.now().month, datetime.now().day,
                                                       datetime.now().hour, datetime.now().minute, 0)
                            if fagendarhorainicio.date() == fechahoraactual.date() and fagendarhorainicio.time() <= fechahoraactual.time():
                                return JsonResponse({'result': 'bad',
                                                     "mensaje": 'La hora de inicio debe ser posterior a la hora actual.'})
                        # obtener profesor
                        profesor = Profesor.objects.get(status=True, persona=persona)
                        # es proceso adicionar o editar
                        id = int(encrypt(request.POST['id']))
                        # Validar que no se repita el registro en la misma fecha agendad e igual a hora de inicio (sólo igual, no mayor)
                        if SolicitudCopia.objects.filter(status=True, profesor=profesor,
                                                         fechaagendada=fagendarhorainicio.date(),
                                                         horainicio=fagendarhorainicio.time()).exclude(id=id).exists():
                            return JsonResponse({'result': 'bad',
                                                 "mensaje": 'Registro con la fecha a agendar y hora de inicio que desea ingresar ya existe.'})

                        # OJO en caso contrario validar que el mismo profesor no pueda agendar en horarios donde ya agendó

                        # fin validaciones permitentes para el proceso calcular hora de fin
                        # llamar función calculo de hora fin, verificacion de horario disponible y verificacion de conflicto de horario especificando que es el proceso action calcular horafin
                        respuestajson, datos =  calcularhorafin_verificardisponibilidadhorario_conflictohorario(request, id, 1, fagendarhorainicio, profesor)
                        return respuestajson
                    else:
                        return JsonResponse(
                            {'result': True,
                             "mensaje": 'Ingrese la fecha a agendar, cantidad de copias y hora de inicio para el cálculo automático de hora de fin.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error en el cálculo de hora fin: {}'.format(ex)})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:

            data['action'] = action = request.GET['action']

            if action == 'adicionar':
                try:
                    # validar que el profesor esté activo
                    profesor = Profesor.objects.get(persona=persona)
                    if profesor.activo == True:
                        # Validar que se haya realizado la Configuración de Copias y registrado las Jornadas
                        if DetalleJornadaImpresora.objects.filter(status=True).values('id').exists():
                            data['title'] = u'Solicitar Copias'
                            # form = SolicitudCopiasForm(initial={'fecha': datetime.now().date()})
                            form = SolicitudCopiasForm()
                            # form.adicionar()
                            data['fecha'] = str(datetime.now().date())[8:10] + '-' + str(datetime.now().date())[5:7] + '-' + str(datetime.now().date())[:4]
                            data['hora'] = str(datetime.now())[11:16]
                            data['form'] = form
                            data['proceso'] = 'adicionar'
                            template = get_template("helpdesk_pro_solicitudcopia/modal/formsolicitarcita.html")
                            return JsonResponse({"result": True, 'data': template.render(data)})
                        else:
                            return JsonResponse({"result": False,
                                             'message': u'Aún no se han asignado jornadas a las impresoras, por favor comunicar al Experto/a de operaciones.'})
                    else:
                        return JsonResponse({"result": False,
                                             'message': u'No puede realizar ésta acción porque actualmente está inactivo.'})
                except Exception as ex:
                    return JsonResponse({"result": False,
                                         'message': f'Error de conexión. {ex}'})


            elif action == 'edit':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = SolicitudCopia.objects.get(pk=id)

                    data['filtrodetalle'] = filtrodetalle = filtro.historialsolicitudcopia_set.filter(status=True).order_by('id').first()
                    form = SolicitudCopiasForm(initial={
                                               'fechaagendada': filtro.fechaagendada,
                                                'cantidadcopia': filtro.cantidadcopia,
                                                # 'horainicio': f'{filtro.horainicio.hour}:{filtro.horainicio.minute}',
                                                'horainicio': filtro.horainicio.strftime("%H:%M"),
                                                # 'horafin': datetime.strptime(f'{filtro.horafin.hour}:{filtro.horafin.minute}', '%H:%M').time(),
                                                'horafin': filtro.horafin.strftime("%H:%M"),
                                                'observacion': filtrodetalle.observacion,
                                                })
                    data['form'] = form
                    template = get_template("helpdesk_pro_solicitudcopia/modal/formsolicitarcita.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            elif action == 'detalle':
                try:
                    data = {}
                    data['solicitudcopia'] = instancia = SolicitudCopia.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['detalle'] = instancia.historial_ordenascendente()
                    template = get_template("helpdesk_pro_solicitudcopia/modal/formdetalle.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False,
                                         "mensaje": u"Error al obtener los datos {}. \n Error on line {}".format(ex, sys.exc_info()[-1].tb_lineno)})


            # elif action == 'solicitudcopiaimpresora':
            #     # Mostrar las impresoras con información relevante
            #     try:
            #         data['title'] = u'Solicitar copias'
            #         # ids=[]
            #         # horarios = Impresora.objects.filter(status=True, mostrar=True).order_by('responsableservicio__servicio_id').distinct('responsableservicio__servicio_id')
            #         # for horario in horarios:
            #         #     if horario.fechafin >= hoy:
            #         #         ids.append(horario.responsableservicio.servicio.id)
            #
            #         search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
            #         if search:
            #             filtro = filtro & (Q(nombre__unaccent__icontains=search))
            #             url_vars += '&s=' + search
            #             data['s'] = search
            #
            #         listado = Impresora.objects.filter(filtro)
            #         paging = MiPaginador(listado, 10)
            #         p = 1
            #         try:
            #             paginasesion = 1
            #             if 'paginador' in request.session:
            #                 paginasesion = int(request.session['paginador'])
            #             if 'page' in request.GET:
            #                 p = int(request.GET['page'])
            #             else:
            #                 p = paginasesion
            #             try:
            #                 page = paging.page(p)
            #             except:
            #                 p = 1
            #             page = paging.page(p)
            #         except:
            #             page = paging.page(p)
            #         request.session['paginador'] = p
            #         data['paging'] = paging
            #         data['rangospaging'] = paging.rangos_paginado(p)
            #         data['page'] = page
            #         data["url_vars"] = url_vars
            #         data['listado'] = page.object_list
            #         data['listcount'] = len(listado)
            #         request.session['viewactivo'] = 1
            #         return render(request, 'helpdesk_pro_solicitudcopia/viewsolicitudcopia.html', data)
            #     except Exception as ex:
            #         return render({'result': False, 'mensaje': '{}'.format(ex)})


            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Solicitud de copias'
                # stardate = datetime.now().strftime('%Y-%m-%d')
                # enddate = stardate
                # ids=[]
                # horarios = Impresora.objects.filter(status=True, mostrar=True).order_by('responsableservicio__servicio_id').distinct('responsableservicio__servicio_id')
                # for horario in horarios:
                #     if horario.fechafin >= hoy:
                #         ids.append(horario.responsableservicio.servicio.id)

                # obtener profesor
                profesor = ''
                if Profesor.objects.filter(status=True, persona=persona).exists():
                    profesor = Profesor.objects.get(persona=persona)
                else:
                    return HttpResponseRedirect('/?info=Acción denegada. Ud. no tiene perfil docente.')
                search, filtro, url_vars, fechasrango, hora = request.GET.get('s', '').strip() , Q(status=True, profesor__id=profesor.id), '', request.GET.get('fechas', '').strip(), request.GET.get('hora', '').strip()
                if search:
                    # filtro = filtro & (Q(horainicio__gte=search) & Q(horafin__lte=search))
                    # filtro = filtro & (Q(horainicio__icontains=search) | Q(horafin__icontains=search) | Q(detallejornadaimpresora__impresora__codigotic__icontains=search) |
                    #                    Q(detallejornadaimpresora__impresora__codigointerno__icontains=search))
                    filtro = filtro & (Q(detallejornadaimpresora__impresora__impresora__codigotic__icontains=search) |
                                       Q(detallejornadaimpresora__impresora__impresora__codigointerno__icontains=search) |
                                       Q(detallejornadaimpresora__impresora__impresora__codigogobierno__icontains=search)
                                       )
                    url_vars += '&s=' + search
                    data['s'] = search

                if fechasrango:
                    try:
                        fechasrango = fechasrango.split(' - ')
                        desde = datetime.strptime(fechasrango.__getitem__(0), '%d-%m-%Y').date()
                        hasta = datetime.strptime(fechasrango.__getitem__(1), '%d-%m-%Y').date()
                        filtro = filtro & (Q(fechaagendada__range=[desde, hasta]))
                        data['fechasrango'] = fechasrango = f"{desde.strftime('%d-%m-%Y')} - {hasta.strftime('%d-%m-%Y')}"
                        url_vars += '&fechas=' + fechasrango
                    except Exception as ex:
                        messages.error(request, u"Formato de fecha inválida. No se consideró en la búsqueda.")

                if hora:
                    hora= datetime.strptime(hora, '%H:%M').time()
                    filtro = filtro & (Q(horainicio__lte=hora, horafin__gte=hora))
                    data['hora'] = hora = hora.strftime('%H:%M')
                    url_vars += '&hora=' + hora

                listado = SolicitudCopia.objects.filter(filtro).order_by('estado', '-id')
                paging = MiPaginador(listado, 10)
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
                data['listado'] = page.object_list
                data['listcount'] = len(listado)
                request.session['viewactivo'] = 2
                return render(request, 'helpdesk_pro_solicitudcopia/viewsolicitudcopia.html', data)
            except Exception as ex:
                return render({'result': False, 'mensaje': '{}'.format(ex)})


# proceso 1 = calcularhorafin, 2 = add y edit
def calcularhorafin_verificardisponibilidadhorario_conflictohorario(request, idsolicitudcopia, proceso, fagendarhorainicio, profesor):
    # inicio proceso calcular hora fin, verificar disponibilidad y conflitcto de horario
    fechaagendada = fagendarhorainicio.date()
    cantidadcopia = int(request.POST['cantidadcopia'])
    horainicio = fagendarhorainicio.time()
    # Obtiene todas las jornadas existentes segun los datos ingresados
    if not DetalleJornadaImpresora.objects.filter(status=True,
                                                  jornadaimpresora__dia=fechaagendada.isoweekday(),
                                                  jornadaimpresora__comienza__lte=horainicio).order_by('id').exists():
        return JsonResponse({'result': True, "mensaje": 'Horario no habilitado, por favor elija otra hora y/o fecha'}), None
    # model = DetalleJornadaImpresora.objects.filter(status=True,
    #                                                jornadaimpresora__dia=fechaagendada.isoweekday(),
    #                                                jornadaimpresora__comienza__lte=horainicio).order_by('id')
    model = DetalleJornadaImpresora.objects.filter(status=True,
                                                   jornadaimpresora__dia=fechaagendada.isoweekday(),
                                                   jornadaimpresora__comienza__lte=horainicio)
    model = model.annotate(tiempoasignado=F('jornadaimpresora__termina') - F('jornadaimpresora__comienza')).order_by('-tiempoasignado')
    # bandera que me informa si ya tiene una solicitud realizada en la fecha y hora ingresada o dentro de ese rango de horario.
    banconflictofechauhorario = False
    for detallejornadaimpresora in model:
        # Calcular hora fin
        # redondear los minutos porque el formato es hora minuto
        tiemporequeridomin = (cantidadcopia * detallejornadaimpresora.impresora.configuracioncopia.tiempo) / detallejornadaimpresora.impresora.configuracioncopia.cantidad
        # si el resultado contiene decimales se aumenta un minuto al tiemporequeridomin
        if not isinstance(tiemporequeridomin, int):
            tiemporequeridomin = int(tiemporequeridomin) + 1
        horafin = (fagendarhorainicio + timedelta(minutes=tiemporequeridomin)).time()
        # una vez calculado la hora fin verifico que el detalle de jornada este dentro de la hora fin, caso contrario continua
        if detallejornadaimpresora.jornadaimpresora.termina >= horafin:

            # se quita la validacion a solicitud del usuario Luis Castillo
            # verificar que este horario esté disponible para permitir agendarlo y mostrar en el form hora fin
            # if not SolicitudCopia.objects.filter(Q(status=True,
            #                                      detallejornadaimpresora__id=detallejornadaimpresora.id,
            #                                      fechaagendada=fechaagendada) &
            #                                     (Q(horafin__range=(horainicio, horafin)) | (Q(horainicio__range=(horainicio, horafin))))).exclude(idsolicitudcopia).exists():
            # se quita la validacion a solicitud del usuario Luis Castillo

                # agregar detalle ojo pendiente
                # verificar que éste profesor no haya agendado otra solicitud en la misma fecha y en el rango de horario ingresado
                if not SolicitudCopia.objects.filter(Q(status=True,
                                                     profesor__id=profesor.id,
                                                     fechaagendada=fechaagendada) &
                                                     (Q(horafin__range=(horainicio, horafin)) | (Q(horainicio__range=(horainicio, horafin))))).exclude(id=idsolicitudcopia).exists():
                    if proceso==1:
                        return JsonResponse({'result': False, 'horafin': horafin.hour , 'minutofin': horafin.minute, "mensaje": 'Hora fin calculado.'}), None
                    else:
                        return None, {'detallejornadaimpresora': detallejornadaimpresora, 'horafin': horafin, 'tiemporequeridomin': tiemporequeridomin}
                else:
                    banconflictofechauhorario = True
    if banconflictofechauhorario == True:
        return JsonResponse(
            {'result': True,
             "mensaje": 'Ud. ya tiene una solicitud en la misma fecha y dentro del rango de horario ingresado, por favor elija otro día y/u horario.'}), None
    return JsonResponse(
        {'result': True, "mensaje": 'Horario no disponible, por favor elija otra hora y/o fecha'}), None
    # fin proceso calcular hora fin, verificar disponibilidad y conflitcto de horario


def minutos_a_horaminuto(tiempoenminutos):
    horaminuto = (datetime(1, 1, 1, 0, 0, 0) + timedelta(minutes=tiempoenminutos)).time()
    return horaminuto

def segundos_a_horaminutosegundo(tiempoensegundos):
    horas = int(tiempoensegundos / 60 / 60)
    tiempoensegundos -= horas * 60 * 60
    minutos = int(tiempoensegundos / 60)
    tiempoensegundos -= minutos * 60
    return f"{horas:02d}:{minutos:02d}:{tiempoensegundos:02d}"
