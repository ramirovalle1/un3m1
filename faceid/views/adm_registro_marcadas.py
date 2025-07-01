# -*- coding: UTF-8 -*-
#PYTHON
import sys
import json
import re
import os
from decorators import secure_module
from settings import DEBUG
#DJANGO
from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.template.loader import get_template
from django.shortcuts import render, redirect
from django.db.models import Q
from django.contrib.auth.models import User
from decorators import inhouse_check, get_client_ip
from unidecode import unidecode

#SGA
from sga.commonviews import adduserdata
from sga.funciones import generar_nombre, log, variable_valor, MiPaginador, notificacion, validar_archivo, loglogin
from bd.models import APP_SGA, APP_SAGEST, APP_POSGRADO, APP_MARCADAS, FLAG_FAILED, FLAG_SUCCESSFUL, FLAG_UNKNOWN
from sga.tasks import send_html_mail
from sagest.models import LogDia, LogMarcada, MarcadasDia, RegistroMarcada
from faceid.models import PersonaMarcada
from faceid.utils.funciones import permiso_marcaje, addglobal_var, file_json_img
from faceid.functions import calculando_marcadasotro
from sagest.funciones import encrypt_id
@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['hoy'] = hoy = datetime.now()
    usuario = request.user
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    data['mi_departamento'] = mi_departamento = persona.mi_departamento()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'updateTime':
            try:
                hour = datetime.now().time().hour
                minute = datetime.now().time().minute
                second = datetime.now().time().second
                if hour < 10:
                    hour = '0' + str(hour)
                if minute < 10:
                    minute = '0' + str(minute)
                if second < 10:
                    second = '0' + str(second)
                tiempo = {"hour": str(hour),
                          "minute": str(minute),
                          "second": str(second)}
                return JsonResponse({"result": "ok", "tiempo": tiempo})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'registrarmarcada':
            try:
                permisos = permiso_marcaje(persona, request)
                if not permisos.get('result', False):
                    raise NameError(permisos.get('mensaje', ''))

                # Datos de la petición
                client_address = get_client_ip(request)
                tipo_marcaje = request.POST['marcada']
                capippriva = request.POST.get('capippriva', '')
                browser = request.POST['navegador']
                ops = request.POST['os']
                cookies = request.POST.get('cookies', 'false')
                screensize = request.POST['screensize']

                fecha = hoy.date()
                time = hoy
                horaactual = hoy.time().hour
                minutoactual = hoy.time().minute
                segundoactual = hoy.time().second

                # Verificar existencia de logdia para la fecha actual
                logdia = LogDia.objects.filter(persona=persona, fecha=fecha).first()
                if logdia:
                    logdia.cantidadmarcadas += 1
                    logdia.procesado = False
                else:
                    logdia = LogDia(persona=persona, fecha=fecha, cantidadmarcadas=1)

                # Asignar jornada si es necesario
                historial_jornada = logdia.persona.historialjornadatrabajador_set.filter(
                                    (Q(fechafin__gte=fecha) | Q(fechafin=None)), fechainicio__lte=fecha).first()
                if historial_jornada:
                    logdia.jornada = historial_jornada.jornada

                logdia.save(request)

                # Verificar si existe un registro de marcada para la hora actual
                if not logdia.logmarcada_set.filter(time=time).exists():
                    similitud = float(request.POST.get('similitud', 0))
                    registro = LogMarcada(
                        logdia=logdia,
                        time=time,
                        tipo=tipo_marcaje,
                        direccion=request.path,
                        similitud=similitud,
                        secuencia=logdia.cantidadmarcadas
                    )
                    registro.save(request)

                # Procesar todos los logdia no procesados
                logdias = LogDia.objects.filter(persona=persona, status=True, procesado=False).order_by("fecha")
                for l in logdias:
                    # Asignar jornada si no está definida
                    if not l.jornada:
                        historial_jornada = l.persona.historialjornadatrabajador_set.filter(
                                            (Q(fechafin__gte=l.fecha) | Q(fechafin=None)), fechainicio__lte=l.fecha
                        ).first()
                        if historial_jornada:
                            l.jornada = historial_jornada.jornada

                    cm = l.logmarcada_set.filter(status=True).count()
                    MarcadasDia.objects.filter(persona=l.persona, fecha=l.fecha).delete()
                    l.cantidadmarcadas = cm

                    # Procesar las marcadas si son pares
                    if cm % 2 == 0:
                        entrada = None
                        for dl in l.logmarcada_set.filter(status=True).order_by("time"):
                            if entrada:
                                salida = dl.time
                                marcadadia = MarcadasDia.objects.filter(persona=l.persona, fecha=l.fecha, logdia=l).first()
                                if not marcadadia:
                                    marcadadia = MarcadasDia(persona=l.persona, fecha=l.fecha, logdia=l, segundos=0)
                                    marcadadia.save(request)

                                if not marcadadia.registromarcada_set.filter(entrada=entrada).exists():
                                    RegistroMarcada.objects.create(
                                        marcada=marcadadia,
                                        entrada=entrada,
                                        salida=salida,
                                        segundos=(salida - entrada).seconds
                                    )
                                marcadadia.actualizar_marcadas()
                                entrada = None
                            else:
                                entrada = dl.time
                        l.procesado = True
                    else:
                        l.cantidadmarcadas = 0

                    l.save(request)

                # Calcular marcadas en otro intervalo
                calculando_marcadasotro(fecha, fecha, persona)

                # Guardar log de login
                loglogin(
                    action_flag=FLAG_SUCCESSFUL,
                    action_app=APP_MARCADAS,
                    ip_private=capippriva,
                    ip_public=client_address,
                    browser=browser,
                    ops=ops,
                    cookies=cookies,
                    screen_size=screensize,
                    user=usuario
                )

                return JsonResponse({
                    "result": "ok",
                    "persona": str(persona),
                    "fecha": fecha,
                    "horaactual": horaactual,
                    "minutoactual": minutoactual,
                    "segundoactual": segundoactual
                })

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({
                    "result": "bad",
                    "mensaje": f"Error al guardar los datos. {str(ex)}"
                })

        elif action == 'delmarcada':
            try:
                id=encrypt_id(request.POST['id'])
                marcada = LogMarcada.objects.get(id=id)
                marcada.status = False
                marcada.save(request)
                log(f'Elimino marcada {marcada}', request, "del")
                return JsonResponse({"error": False})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"error": True, "mensaje": u"Error al eliminar la marcada. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        search, filtro, url_vars  = request.GET.get('s', ''), Q(status=True), ''
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            url_vars = f'&action={action}'

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Sistema de marcadas laborales'
                data['my_ip'] = my_ip = get_client_ip(request)
                permisos = permiso_marcaje(persona, request)
                if not permisos.get('result', False):
                    data['mensaje'] = permisos.get('mensaje', '')
                    return render(request, "adm_registro_marcadas/diabled_mark.html", data)
                data['log_dia'] = log_dia = LogDia.objects.filter(persona=persona, status=True, fecha=hoy.date()).first()
                if log_dia:
                    data['log_marcadas'] = log_dia.logmarcada_set.filter(status=True).order_by('time')
                data['persona_marcada'] = permisos.get('persona_marcada', None)
                addglobal_var(data)
                return render(request, "adm_registro_marcadas/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect(f"/?info{ex.__str__()}")








