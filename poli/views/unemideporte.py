# -*- coding: UTF-8 -*-
import random
import sys
import calendar
from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template.loader import get_template
from django.shortcuts import render, redirect
from unidecode import unidecode

from django import forms
from decorators import secure_module
from med.models import PersonaExamenFisico
from poli.forms import PersonaPrimariaForm
from sagest.forms import DatosPersonalesForm, DatosNacimientoForm, DatosDomicilioForm, FamiliarForm, ContactoEmergenciaForm, DatosMedicosForm, PersonaEnfermedadForm, TitulacionPersonaForm
from sagest.models import DistributivoPersona
from settings import EMAIL_DOMAIN
from poli.views.commonviews import adduserdata
from sga.funciones import generar_nombre, log, variable_valor, elimina_tildes
from sga.models import Persona, PersonaDocumentoPersonal, PersonaDatosFamiliares, Externo, PersonaEnfermedad, Titulacion, Titulo, CUENTAS_CORREOS, Graduado
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from poli.models import *
from poli.acciones import *
from django.db.models import Q


@login_required(redirect_field_name='ret', login_url='/unemideportes?next=login')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    hoy = datetime.now().date()
    usuario = request.user
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    esestudiante = perfilprincipal.es_estudiante()
    data['puede_modificar_hv'] = variable_valor('PUEDE_MODIFICAR_HV')
    data['solo_perfil_externo'] = solo_perfil_externo = len(persona.mis_perfilesusuarios()) == 1 and persona.tiene_usuario_externo()
    data['es_instructor'] = es_instructor = persona.instructorpolideportivo_set.filter(status=True).exists()
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'inscribirse':
            try:
                planificacion = PlanificacionActividad.objects.get(id=encrypt_id(request.POST['id']))
                horarios = HorarioActividadPolideportivo.objects.filter(id__in=request.POST.getlist('horarios'))
                tercero = 'parafamiliar' in request.POST
                familiar = request.POST.get('familiar', None)
                tipotercero = 1 if tercero else None
                if planificacion.tiene_reserva(persona, familiar):
                    raise NameError('Usted ya se inscribió en esta actividad.')
                if not horarios:
                    raise NameError('Seleccione un horario por dia a reservar.')
                if planificacion.cupos_disponibles() <= 0:
                    raise NameError('No existe disponibilidad de cupos para inscribirse a esta actividad')
                seccionesarea = planificacion.actividad.area.secciones()
                turno = planificacion.generar_turno(str(persona))
                reserva = ReservacionPersonaPoli(persona=persona,
                                                 area=planificacion.actividad.area,
                                                 actividad=planificacion.actividad,
                                                 planificacion=planificacion,
                                                 familiar_id=familiar,
                                                 tercero=tercero,
                                                 tipotercero=tipotercero,
                                                 perfil=perfilprincipal,
                                                 finicialreserva = planificacion.fechainicio,
                                                 ffinalreserva = planificacion.fechafin,
                                                 inscripcion = perfilprincipal.inscripcion if persona.es_estudiante() else None,
                                                 codigo=turno)
                reserva.save(request)

                for horario in horarios:
                    inicio = planificacion.fechainicio
                    fin = planificacion.fechafin
                    while inicio <= fin:
                        turnos = horario.cupos_disponible_fecha(inicio)
                        if inicio.weekday()+1 == horario.dia and turnos > 0:
                            reservacionfecha = ReservacionFechasPoli(reservacion=reserva, freservacion=inicio)
                            reservacionfecha.save(request)
                            reservacionturno = ReservacionTurnosPoli(fechareservacion=reservacionfecha, turno=horario)
                            reservacionturno.save(request)
                        inicio += timedelta(days=1)


                log(u'{} : Inicio reservación en actividad {}'.format(persona, reserva.actividad.__str__()), request, "add")
                url_ = f'/perfil_usuario?action=misinscripciones'
                return JsonResponse({"result": False, "to": url_})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": f"{ex}"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'actividades':
                try:
                    template, data = actividades(data, request)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'actividad':
                try:
                    data['persona'] = persona
                    template, data = actividad(data, request)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'areas':
                try:
                    template, data = areas(data)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'area':
                try:
                    template, data = area(data, request)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'instructores':
                try:
                    template, data = instructores(data, request)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'politicas':
                try:
                    return render(request, politicas(data))
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'instructor':
                try:
                    template, data = instructor(data, request)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'noticias':
                try:
                    template, data = noticias(data, request)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            elif action == 'noticia':
                try:
                    template, data = noticia(data, request)
                    return render(request, template, data)
                except Exception as ex:
                    messages.error(request, str(ex))

            return HttpResponseRedirect(request.path)
        else:
            try:
                template, data = view_inicio(data)
                return render(request, template, data)
            except Exception as ex:
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                pass
