# -*- coding: UTF-8 -*-
import json
import sys
from itertools import chain

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import get_template
from django.template import Context

from balcon.models import Informacion, Proceso, Solicitud, Agente, Servicio, HistorialSolicitud, ProcesoServicio, \
    RequisitosConfiguracion, RequisitosSolicitud, Categoria
from decorators import secure_module, last_access
from even.models import PeriodoEvento, RegistroEvento, DetallePeriodoEvento
from sga.commonviews import adduserdata
from sga.funciones import log, generar_nombre, notificacion, remover_caracteres_especiales_unicode
from sga.templatetags.sga_extras import encrypt
from django.db import connections

import random
@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'asistenciaevento':
            try:
                with transaction.atomic():
                    evento = PeriodoEvento.objects.get(pk=int(request.POST['id']))
                    if not evento.cerrado:
                        if evento.publicar:
                            if not RegistroEvento.objects.filter(status=True, periodo=evento, participante=persona).exists():
                                registro = RegistroEvento(status=True,
                                                          periodo=evento,
                                                          participante=persona,
                                                          perfil=perfilprincipal,
                                                          inscripcion=perfilprincipal.inscripcion)
                                if persona.canton:
                                    registro.canton=persona.canton
                                registro.save(request)
                                response = JsonResponse({'resp': True})
                            else:
                                response = JsonResponse({'resp': False, 'msg': 'Usted ya se encuentra registrado en este evento.'})
                        else:
                            response = JsonResponse({'resp': False, 'msg': 'Evento no se encuentra publicado.'})
                    else:
                        response = JsonResponse({'resp': False, 'msg': 'Evento ya se encuentra cerrado.'})
                    return HttpResponse(response.content)
            except Exception as ex:
                response = JsonResponse({'resp': False, 'msg': ex})
                return HttpResponse(response.content)
        if action == 'asistenciaeventoconfirmacion':
            try:
                with transaction.atomic():
                    evento = PeriodoEvento.objects.get(pk=int(request.POST['id']))
                    if not evento.cerrado:
                        if evento.publicar:
                            if not RegistroEvento.objects.filter(status=True, periodo=evento, participante=persona).exists():
                                registro = RegistroEvento(status=True,
                                                          periodo=evento,
                                                          participante=persona,
                                                          perfil=perfilprincipal,
                                                          inscripcion=perfilprincipal.inscripcion,
                                                          estado_confirmacion=1)
                                if persona.canton:
                                    registro.canton=persona.canton
                                registro.save(request)
                                response = JsonResponse({'resp': True})
                            else:
                                response = JsonResponse({'resp': False, 'msg': 'Usted ya se encuentra registrado en este evento.'})
                        else:
                            response = JsonResponse({'resp': False, 'msg': 'Evento no se encuentra publicado.'})
                    else:
                        response = JsonResponse({'resp': False, 'msg': 'Evento ya se encuentra cerrado.'})
                    return HttpResponse(response.content)
            except Exception as ex:
                response = JsonResponse({'resp': False, 'msg': ex})
                return HttpResponse(response.content)
        if action == 'eliminarevento':
            try:
                with transaction.atomic():
                    evento = PeriodoEvento.objects.get(pk=int(request.POST['id']))
                    if not evento.cerrado:
                        if evento.publicar:
                            if RegistroEvento.objects.filter(status=True, periodo=evento, participante=persona).exists():
                                registro = RegistroEvento.objects.filter(status=True, periodo=evento, participante=persona).first()
                                registro.status=False
                                registro.estado_confirmacion=0
                                registro.save(request)
                                response = JsonResponse({'resp': True})
                            else:
                                response = JsonResponse({'resp': False, 'msg': 'Usted ya no se encuentra registrado en este evento.'})
                        else:
                            response = JsonResponse({'resp': False, 'msg': 'Evento no se encuentra publicado.'})
                    else:
                        response = JsonResponse({'resp': False, 'msg': 'Evento ya se encuentra cerrado.'})
                    return HttpResponse(response.content)
            except Exception as ex:
                response = JsonResponse({'resp': False, 'msg': ex})
                return HttpResponse(response.content)
        if action == 'confirmaasistencia':
            try:
                with transaction.atomic():
                    evento = PeriodoEvento.objects.get(pk=int(encrypt(request.POST['id'])))
                    if not evento.cerrado:
                        if evento.publicar:
                            if RegistroEvento.objects.filter(status=True, periodo=evento, participante=persona).exists():
                                registro = RegistroEvento.objects.filter(status=True, periodo=evento, participante=persona).first()
                                registro.estado_confirmacion=int(request.POST['tipo'])
                                registro.save(request)
                                msg = 'ASISTENCIA DECLINADA'
                                link = ''
                                if int(request.POST['tipo']) == 1:
                                    msg = 'ASISTENCIA CONFIRMADA\nFECHA EVENTO {}'.format(str(registro.periodo.fechainicio))
                                    link = evento.link
                                response = JsonResponse({'resp': True, 'msg': msg, 'link': link})
                            else:
                                response = JsonResponse({'resp': False, 'msg': 'Usted ya no se encuentra registrado en este evento.'})
                        else:
                            response = JsonResponse({'resp': False, 'msg': 'Evento no se encuentra publicado.'})
                    else:
                        response = JsonResponse({'resp': False, 'msg': 'Evento ya se encuentra cerrado.'})
                    return HttpResponse(response.content)
            except Exception as ex:
                response = JsonResponse({'resp': False, 'msg': ex})
                return HttpResponse(response.content)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'verevento':
                data['id'] = id = int(encrypt(request.GET['id']))
                data['evento'] = evento = PeriodoEvento.objects.get(pk=id)
                data['yainscrito'] = yainscrito = RegistroEvento.objects.filter(status=True, periodo=evento, participante=persona).exists()
                data['noconfirme'] = noconfirme = RegistroEvento.objects.filter(status=True, periodo=evento, participante=persona, estado_confirmacion=0).exists()
                data['title'] = u'{}'.format(evento.evento.nombre)
                return render(request, "alu_eventos/detalle.html", data)

            if action == 'traerinfo':
                try:
                    data['persona'] = persona
                    data['evento'] = evento = PeriodoEvento.objects.get(pk=int(request.GET['id']))
                    template = get_template("alu_eventos/get_evento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))


            if action == 'miseventos':
                try:
                    data['title'] = 'Mis Eventos'
                    data['eventos'] = RegistroEvento.objects.filter(participante=persona, status=True).order_by('-id')
                    return render(request, "alu_eventos/miseventos.html", data)
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Eventos Disponibles'
                # misinscripciones = RegistroEvento.objects.filter(participante=persona,status=True).values_list('periodo_id', flat=True)
                # .exclude(id__in=misinscripciones)
                qsbase = PeriodoEvento.objects.filter(status=True, publicar=True, cerrado=False, periodo=periodo, permiteregistro=True)
                listahabilitados = []
                listatodos = []
                listacanton = []
                if qsbase.filter(todos=True).exists():
                    listatodos = qsbase.filter(todos=True).values_list('id',flat=True)
                if DetallePeriodoEvento.objects.filter(periodo__in=qsbase.values_list('id',flat=True), canton=persona.canton).exists():
                    listacanton = DetallePeriodoEvento.objects.filter(periodo__in=qsbase.values_list('id',flat=True), canton=persona.canton).values_list('periodo_id', flat=True)
                listahabilitados = list(chain(listatodos, listacanton))
                data['eventos'] = qsbase.filter(pk__in=listahabilitados).order_by('fechainicio')
                return render(request, "alu_eventos/listado.html", data)
            except Exception as ex:
                return redirect('/')