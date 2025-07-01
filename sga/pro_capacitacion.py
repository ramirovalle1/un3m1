# -*- coding: UTF-8 -*-
# import datetime
import sys
from datetime import  datetime, timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Case, When, Value, BooleanField, Exists, OuterRef, Q
from django.views.decorators.csrf import csrf_exempt

from django.contrib.auth.decorators import login_required
from django.db import transaction

from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template


from decorators import last_access, secure_module
from settings import DEBUG

from sga.commonviews import adduserdata
from sga.funciones import log, variable_valor
from sga.templatetags.sga_extras import encrypt

unicode = str


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(days=n)


@csrf_exempt
@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']
    data['persona'] = persona
    data['profesor'] = profesor = persona.profesor()
    if not perfilprincipal.es_profesor():
        return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    profesor = perfilprincipal.profesor
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'addinscripcion':
                from sga.models import CapEventoPeriodoDocente, CapCabeceraSolicitudDocente, CapDetalleSolicitudDocente,ProfesorDistributivoHoras
                try:
                    if CapCabeceraSolicitudDocente.objects.values('id').filter(participante=persona, capeventoperiodo_id=int(request.POST['id'])).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra inscrito o está en estado solicitado"})
                    if not CapEventoPeriodoDocente.objects.get(pk=int(request.POST['id'])).hay_cupo_inscribir():
                        return JsonResponse({"result": "bad", "mensaje": u"No hay cupo para continuar adicionando"})
                    evento = CapEventoPeriodoDocente.objects.get(pk=int(request.POST['id']))
                    carrera = ProfesorDistributivoHoras.objects.filter(profesor__persona=persona,periodo=periodo).first()
                    #carrera = profesor.carrera_comun_periodo(evento.periodoac)
                    facultad = None
                    if carrera:
                        facultad = carrera.coordinacion.id
                    cabecera = CapCabeceraSolicitudDocente(capeventoperiodo_id=int(request.POST['id']),
                                                                   solicita=persona,
                                                                   fechasolicitud=datetime.now().date(),
                                                                   estadosolicitud=variable_valor('APROBADO_CAPACITACION'),
                                                                   fechaultimaestadosolicitud=datetime.now(),
                                                                   participante=persona,
                                                                   carrera = carrera.carrera,
                                                                   facultad_id = facultad
                                                                    )
                    cabecera.save(request)
                    log(u'Se inscribió en Evento Docente: %s' % cabecera, request, "add")
                    detalle = CapDetalleSolicitudDocente(cabecera=cabecera,
                                                            aprueba=persona,
                                                            fechaaprobacion=datetime.now().date(),
                                                            estado=2)
                    detalle.save(request)
                    log(u'Ingreso Detalle Inscribio de Evento Docente: %s  (fechaaprobacion: %s)-[%id]' % (detalle, detalle.fechaaprobacion, detalle.id), request, "add")
                    return JsonResponse({"result": "ok" , "mensaje": u"Usted se encuentra correctamente inscrito."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al inscribirse. %s" % ex})

            elif action == 'delinscripcion':
                from sga.models import CapCabeceraSolicitudDocente
                try:
                    cabecera = CapCabeceraSolicitudDocente.objects.get(participante=persona, capeventoperiodo_id=int(request.POST['id']))
                    # if not cabecera.puede_eliminar_inscrito():
                    #     return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, el inscrito ya cuenta con asistencia"})
                    if not cabecera.puede_eliminar_inscrito2():
                        return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar, ya cuenta con asistencia o calificación"})
                    cabecera.capdetallesolicituddocente_set.all().delete()
                    # cabecera.mail_notificar_talento_humano(request.session['nombresistema'])
                    log(u'Elimino Incrito cabecera y sus detalle de Solicitud Docente: %s' % cabecera, request, "del")
                    cabecera.delete()
                    return JsonResponse({"result": "ok", "mensaje": u"Eliminó su inscripción."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'saveEncuesta':
                from inno.models import CapRespuestaEncuestaSatisfaccion, CapPreguntaEncuestaPeriodo, \
                    CapOpcionPreguntaEncuestaPeriodo
                from sga.models import CapCabeceraSolicitudDocente
                try:
                    id = encrypt(request.POST.get('id', encrypt('0')))
                    try:
                        eCapCabecera = CapCabeceraSolicitudDocente.objects.get(id=id)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro solicitud del evento")
                    eCapEvento = eCapCabecera.capeventoperiodo
                    eCapEncuesta = eCapEvento.encuesta
                    eCapPreguntas = CapPreguntaEncuestaPeriodo.objects.filter(encuesta=eCapEncuesta, status=True, isActivo=True)
                    # aRespuestas = []
                    for eCapPregunta in eCapPreguntas:
                        opcion_id = request.POST.get(f"opcion_pregunta_id_{encrypt(eCapPregunta.id)}", 0)
                        if opcion_id == '' and type(opcion_id) is str:
                            opcion_id = 0
                        else:
                            opcion_id = int(opcion_id)
                        # valoracion = int(request.POST.get(f"valoracion_id_{encrypt(eCapPregunta.id)}", 0))
                        observacion = request.POST.get(f"observacion_id_{encrypt(eCapPregunta.id)}", None)
                        try:
                            eCapOpcionPreguntaEncuestaPeriodo = CapOpcionPreguntaEncuestaPeriodo.objects.get(id=opcion_id)
                        except ObjectDoesNotExist:
                            raise NameError(f"Seleccione una opción de la pregunta {eCapPregunta.descripcion}")
                        #
                        # if valoracion == 0:
                        #     raise NameError(f"Pregunta {eCapPregunta.descripcion}")
                        try:
                            eCapRespuestaEncuesta = CapRespuestaEncuestaSatisfaccion.objects.get(pregunta=eCapPregunta, solicitud=eCapCabecera)
                        except ObjectDoesNotExist:
                            eCapRespuestaEncuesta = CapRespuestaEncuestaSatisfaccion(pregunta=eCapPregunta,
                                                                                     solicitud=eCapCabecera)
                        eCapRespuestaEncuesta.opcion = eCapOpcionPreguntaEncuestaPeriodo
                        eCapRespuestaEncuesta.valoracion = eCapOpcionPreguntaEncuestaPeriodo.valoracion
                        eCapRespuestaEncuesta.observacion = observacion
                        eCapRespuestaEncuesta.save(request)
                        log(u'Respuesta de encuesta de satisfacción : %s' % eCapRespuestaEncuesta, request, "add")
                    res_js = {'isSuccess': True,
                              'message': u"Se guardo correctamente la encuesta.",
                              'data': {'url': eCapCabecera.rutapdf.url if eCapCabecera.rutapdf else None,
                                       'id': eCapCabecera.id,
                                       'name': eCapCabecera.rutapdf.name if eCapCabecera.rutapdf else None}}
                except Exception as ex:
                    transaction.set_rollback(True)
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    if DEBUG:
                        print(err)
                    msg_err = f"{ex.__str__()}"
                    res_js = {'isSuccess': False,
                              'message': msg_err,
                              'data': {'url': None, 'id': None, 'name': None}}
                return JsonResponse(res_js)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'verdetalle':
                from sga.models import CapEventoPeriodoDocente
                try:
                    data['title'] = u'Detalles del curso de capacitación'
                    data['evento'] = evento = CapEventoPeriodoDocente.objects.get(pk=int(request.GET['id']))
                    data['instructores']  = evento.capinstructordocente_set.filter(status=True)
                    template = get_template("pro_capacitacion/modal/listactividades.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'mensaje': ex})

            elif action == 'loadEncuesta':
                from inno.models import CapPreguntaEncuestaPeriodo
                from sga.models import CapCabeceraSolicitudDocente
                try:
                    id = encrypt(request.GET.get('id', encrypt('0')))
                    try:
                        eCapCabecera = CapCabeceraSolicitudDocente.objects.get(id=id)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro solicitud del evento")
                    eCapEvento = eCapCabecera.capeventoperiodo
                    eCapEncuesta = eCapEvento.encuesta
                    eCapPreguntas = CapPreguntaEncuestaPeriodo.objects.filter(encuesta=eCapEncuesta, status=True,
                                                                              isActivo=True)
                    data['eCapPreguntas'] = eCapPreguntas
                    data['frmName'] = "frmEncuesta"
                    data['eCapCabecera'] = eCapCabecera
                    template = get_template("pro_capacitacion/modal/formencuestasatisfaccion.html")
                    json_content = template.render(data, request=request)
                    return JsonResponse({"isSuccess": True, 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"isSuccess": False, 'message': str(ex)})

            return HttpResponseRedirect(request.path)
        else:
            from sga.models import CapEventoPeriodoDocente, CapCabeceraSolicitudDocente
            from sagest.models import DistributivoPersona
            try:
                data['title'] = u'Capacitación docente'
                fechamostrar = datetime.now()
                distributivopersona = DistributivoPersona.objects.filter(estadopuesto__id=1, status=True, persona=persona).values('id', 'regimenlaboral_id')
                data['distributivopersona'] = distributivopersona.first()
                data['fechaactual'] = hoy = datetime.now().date()
                fechaactual_3 = hoy + timedelta(days=3)
                data['listadocapacitacion'] = CapEventoPeriodoDocente.objects.filter(status=True, visualizar=True, fechainicio__gte=fechamostrar).annotate(
                    puede_inscribirse_en_fecha=Case(
                        When(fechainicio__gte=fechaactual_3, then=Value(True)),
                        default=Value(False),
                        output_field=BooleanField(),
                    )).annotate(aplica_modalidadlaboral=Exists(distributivopersona.filter(estadopuesto__id=1, status=True, persona=persona, modalidadlaboral__in=OuterRef('modalidadlaboral')))).annotate(
                    inscrito_capacitacion_docente=Exists(CapCabeceraSolicitudDocente.objects.filter(status=True, participante=persona, capeventoperiodo_id=OuterRef('id')))
                )

                data['miscursos'] = CapCabeceraSolicitudDocente.objects.filter(status=True, participante=persona).order_by('-capeventoperiodo__fechafin')

                return render(request, "pro_capacitacion/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect(f"/?info={ex.__str__()}")






