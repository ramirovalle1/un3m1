# -*- coding: latin-1 -*-
import json
from django.contrib.auth import authenticate
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen, Request

from decorators import last_access, secure_module, inhouse_check
from sagest.models import LogDia, LogMarcada, RegistroMarcada, MarcadasDia, TrabajadorDiaJornada, \
    PermisoInstitucionalDetalle, MarcadaActividad
from sagest.th_marcadas import calculando_marcadas
from sga.funciones import log, loglogin, variable_valor
from sga.models import Persona, DiasNoLaborable, ClaseActividad
from bd.models import APP_SGA, APP_SAGEST, APP_POSGRADO, APP_MARCADAS, FLAG_FAILED, FLAG_SUCCESSFUL, FLAG_UNKNOWN


# @login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    client_address = get_client_ip(request)
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'actualizahora':
                try:
                    horaactual = 0
                    minutoactual = 0
                    segundoactual = 0
                    horaactual = datetime.now().time().hour
                    minutoactual = datetime.now().time().minute
                    segundoactual = datetime.now().time().second
                    if horaactual < 10:
                        horaactual = '0' + str(horaactual)
                    if minutoactual < 10:
                        minutoactual = '0' + str(minutoactual)
                    if segundoactual < 10:
                        segundoactual = '0' + str(segundoactual)
                    horafinal = str(horaactual) + ':' + str(minutoactual)
                    return JsonResponse({"result": "ok", "horaactualizar": horafinal})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'verificauser':
                try:
                    if not inhouse_check(request):
                        return JsonResponse({"result": "bad", 'mensaje': u'No puede ingresar marcadas fuera de la institucion.'})
                    valorregistro = request.POST['valorregistro']
                    capippriva = request.POST['capippriva'] if 'capippriva' in request.POST else ''
                    browser = request.POST['navegador']
                    ops = request.POST['os']
                    cookies = request.POST['cookies']
                    screensize = request.POST['screensize']
                    if variable_valor('VALIDAR_CON_CAPTCHA_MARCADAS'):
                        recaptcha_response = request.POST.get('g-recaptcha-response')
                        url = 'https://www.google.com/recaptcha/api/siteverify'
                        values = {'secret': variable_valor('GOOGLE_RECAPTCHA_SECRET_KEY'),
                                  'response': recaptcha_response}
                        data = urlencode(values)
                        data = data.encode('utf-8')
                        req = Request(url, data)
                        response = urlopen(req)
                        result = json.loads(response.read().decode())
                        if not result['success']:
                            return JsonResponse({"result": "bad", 'mensaje': u'ReCaptcha no válido. Vuelve a intentarlo..'})

                    user = authenticate(username=request.POST['user'].lower().strip(), password=request.POST['pass'])
                    if user is not None:
                        if not user.is_active:
                            loglogin(action_flag=FLAG_FAILED, action_app=APP_MARCADAS, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, user=user, change_message=u"Usuario no activo")
                            return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, usuario no activo.'})
                        else:
                            if Persona.objects.filter(usuario=user).exists():
                                persona = Persona.objects.filter(usuario=user)[0]
                                if persona.perfilusuario_set.filter(administrativo__isnull=False, status=True) or persona.perfilusuario_set.filter(profesor__isnull=False, status=True):
                                    # if persona.distributivopersona_set.filter(estadopuesto_id=1, status=True).exists():
                                    fecha = datetime.now().date()
                                    time = datetime.now()
                                    horaactual = datetime.now().time().hour
                                    minutoactual = datetime.now().time().minute
                                    segundoactual = datetime.now().time().second
                                    if persona.logdia_set.filter(fecha=fecha).exists():
                                        logdia = persona.logdia_set.filter(fecha=fecha)[0]
                                        if logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin__gte=logdia.fecha).exists():
                                            logdia.jornada = logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin__gte=logdia.fecha).order_by('fechainicio')[0].jornada
                                        elif logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin=None).exists():
                                            logdia.jornada = logdia.persona.historialjornadatrabajador_set.filter(fechainicio__lte=logdia.fecha, fechafin=None)[0].jornada
                                        logdia.cantidadmarcadas += 1
                                        logdia.procesado = False
                                    else:
                                        logdia = LogDia(persona=persona,
                                                        fecha=fecha,
                                                        cantidadmarcadas=1)
                                    logdia.save(request)
                                    if not logdia.logmarcada_set.filter(time=time).exists():
                                        registro = LogMarcada(logdia=logdia,
                                                              time=time,
                                                              direccion=request.path,
                                                              secuencia=logdia.cantidadmarcadas)
                                        registro.save(request)
                                    for l in LogDia.objects.filter(persona=persona, status=True, procesado=False).order_by("fecha"):
                                        if not l.jornada:
                                            if l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin__gte=l.fecha).exists():
                                                l.jornada = l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin__gte=l.fecha).order_by('fechainicio')[0].jornada
                                            elif l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin=None).exists():
                                                l.jornada = l.persona.historialjornadatrabajador_set.filter(fechainicio__lte=l.fecha, fechafin=None)[0].jornada

                                        cm = l.logmarcada_set.filter(status=True).count()
                                        MarcadasDia.objects.filter(persona=l.persona, fecha=l.fecha).delete()
                                        l.cantidadmarcadas = cm
                                        if (cm % 2) == 0:
                                            marini = 1
                                            for dl in l.logmarcada_set.filter(status=True).order_by("time"):
                                                if marini == 2:
                                                    salida = dl.time
                                                    marini = 1
                                                    if l.persona.marcadasdia_set.filter(fecha=l.fecha).exists():
                                                        marcadadia = l.persona.marcadasdia_set.filter(fecha=l.fecha)[0]
                                                    else:
                                                        marcadadia = MarcadasDia(persona=l.persona,
                                                                                 fecha=l.fecha,
                                                                                 logdia=l,
                                                                                 segundos=0)
                                                        marcadadia.save(request)
                                                    if not marcadadia.registromarcada_set.filter(entrada=entrada).exists():
                                                        registro = RegistroMarcada(marcada=marcadadia,
                                                                                   entrada=entrada,
                                                                                   salida=salida,
                                                                                   segundos=(salida - entrada).seconds)
                                                        registro.save(request)
                                                    marcadadia.actualizar_marcadas()
                                                else:
                                                    entrada = dl.time
                                                    marini += 1
                                            l.procesado = True
                                        else:
                                            l.cantidadmarcadas = 0
                                        l.save(request)
                                        # if l.procesado:
                                        #     calculando_marcadas(request, l.fecha, l.fecha, l.persona)
                                    calculando_marcadasotro(fecha, fecha, persona)
                                    nombres = persona.apellido1 + ' ' + persona.apellido2 + ' ' + persona.nombres
                                    loglogin(action_flag=FLAG_SUCCESSFUL, action_app=APP_MARCADAS, ip_private=capippriva,
                                             ip_public=client_address, browser=browser, ops=ops, cookies=cookies, screen_size=screensize, user=user)
                                    # log(u'(Marcadas) Marcó correctamente: %s' % request.POST['user'], request, "add",user=user)
                                    return JsonResponse({"result": "ok", "persona": nombres, "fecha": fecha, "horaactual": horaactual, "minutoactual": minutoactual, "segundoactual": segundoactual})
                                else:
                                    loglogin(action_flag=FLAG_FAILED, action_app=APP_MARCADAS, ip_private=capippriva,
                                             ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                             screen_size=screensize, user=user, change_message=u"Usuario no activo")
                                    # log(u'(Marcadas) Login fallido, no existe el usuario: %s' % request.POST['user'], request, "add")
                                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, usuario no activo.'})
                            else:
                                loglogin(action_flag=FLAG_UNKNOWN, action_app=APP_MARCADAS, ip_private=capippriva,
                                         ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                         screen_size=screensize, change_message=u"USUARIO: %s - CLAVE: %s" % (request.POST['user'].lower().strip(), request.POST['pass']))
                                # log(u'(Marcadas) Login fallido, no existe el usuario: %s' % request.POST['user'], request, "add")
                                return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existe el usuario.'})
                    else:
                        return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, credenciales incorrectas.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'insripcioncursoposgrado':
                try:
                    a = 0
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Registrar marcada'
                hoy = datetime.now().date()
                remote_addr = get_client_ip(request)
                data['ipfuera'] = remote_addr
                mensaje = True
                if not inhouse_check(request):
                    mensaje = False
                # # comentar
                # mensaje = True
                # # //////////
                data['mensaje'] = mensaje
                data['validar_con_captcha'] = variable_valor('VALIDAR_CON_CAPTCHA_MARCADAS')
                data['public_key'] = variable_valor('GOOGLE_RECAPTCHA_PUBLIC_KEY')
                tiposistemas_ = None
                if 'postulate' not in request.META['HTTP_HOST']:
                    tiposistemas_ = 'POSTULATE'
                elif 'admisionposgrado' in request.META['HTTP_HOST']:
                    tiposistemas_ = 'ADMISIONPOSGRADO'
                elif 'sagest' in request.META['HTTP_HOST']:
                    tiposistemas_ = 'SAGEST'
                elif 'seleccionposgrado' in request.META['HTTP_HOST']:
                    tiposistemas_ = 'seleccionposgrado'
                elif 'sga' in request.META['HTTP_HOST']:
                    tiposistemas_ = 'SGA'
                data['tiposistemas'] = tiposistemas_
                return render(request, "adm_marcadas/marcadas.html", data)
            except Exception as ex:
                pass


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def calculando_marcadasotro(fechai, fechaf, persona):
    b = range(86400)
    while fechai <= fechaf:
        c = [[] for i in b]
        if not DiasNoLaborable.objects.filter(fecha=fechai).exclude(periodo__isnull=False).exists():
            if persona.historialjornadatrabajador_set.filter(fechainicio__lte=fechai, fechafin__gte=fechai).exists():
                jornada = persona.historialjornadatrabajador_set.filter(fechainicio__lte=fechai, fechafin__gte=fechai).order_by('fechainicio')[0]
                if jornada.jornada.detallejornada_set.filter(dia=fechai.isoweekday()).exists():
                    jornadasdia = jornada.jornada.detallejornada_set.filter(dia=fechai.isoweekday())
                    if TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai).exists():
                        diajornada = TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai)[0]
                        diajornada.jornada = jornada.jornada
                        diajornada.totalsegundostrabajados = 0
                        diajornada.totalsegundospermisos = 0
                        diajornada.totalsegundosextras = 0
                        diajornada.totalsegundosatrasos = 0
                    else:
                        diajornada = TrabajadorDiaJornada(persona=persona,
                                                          fecha=fechai,
                                                          anio=fechai.year,
                                                          mes=fechai.month,
                                                          jornada=jornada.jornada)
                        diajornada.save()
                    if persona.marcadasdia_set.filter(fecha=fechai).exists():
                        marcadadia = persona.marcadasdia_set.filter(fecha=fechai)[0]
                    else:
                        marcadadia = MarcadasDia(persona=persona, fecha=fechai)
                        marcadadia.save()
                    totalsegundostrabajados = 0
                    totalsegundosextras = 0
                    totalsegundosatraso = 0
                    totalpermisos = 0
                    totalpermisosantes = 0
                    for marcada in marcadadia.registromarcada_set.all():
                        duracion = (marcada.salida - marcada.entrada).seconds
                        inicio = (marcada.entrada.time().hour * 60 * 60) + (marcada.entrada.time().minute * 60) + marcada.entrada.time().second
                        fin = (marcada.salida.time().hour * 60 * 60) + (marcada.salida.time().minute * 60) + marcada.salida.time().second
                        while inicio <= fin:
                            c[inicio].append('m')
                            inicio += 1
                    for jornadamarcada in jornadasdia:
                        duracionjornada = (datetime(fechai.year, fechai.month, fechai.day, jornadamarcada.horafin.hour, jornadamarcada.horafin.minute, jornadamarcada.horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, jornadamarcada.horainicio.hour, jornadamarcada.horainicio.minute, jornadamarcada.horainicio.second))).seconds
                        iniciojornada = (jornadamarcada.horainicio.hour * 60 * 60) + (jornadamarcada.horainicio.minute * 60) + jornadamarcada.horainicio.second
                        finjornada = (jornadamarcada.horafin.hour * 60 * 60) + (jornadamarcada.horafin.minute * 60) + jornadamarcada.horafin.second
                        while iniciojornada <= finjornada:
                            c[iniciojornada].append('j')
                            iniciojornada += 1
                    for permiso in PermisoInstitucionalDetalle.objects.filter(permisoinstitucional__solicita=persona, fechainicio__lte=fechai, fechafin__gte=fechai, permisoinstitucional__estadosolicitud=3):
                        # VACACIONES
                        if permiso.permisoinstitucional.tiposolicitud == 3:
                            horainicio = datetime(2016, 1, 0, 0, 0, 0)
                            horafin = datetime(2016, 1, 1, 23, 0, 0)
                            duracionpermiso = (datetime(fechai.year, fechai.month, fechai.day, horafin.hour, horafin.minute, horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, horainicio.hour, horainicio.minute, horainicio.second))).seconds
                            iniciopermiso = (horainicio.hour * 60 * 60) + (horainicio.minute * 60) + horainicio.second
                            finpermiso = (horafin.hour * 60 * 60) + (horafin.minute * 60) + horafin.second
                        else:
                            duracionpermiso = (datetime(fechai.year, fechai.month, fechai.day, permiso.horafin.hour, permiso.horafin.minute, permiso.horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, permiso.horainicio.hour, permiso.horainicio.minute, permiso.horainicio.second))).seconds
                            iniciopermiso = (permiso.horainicio.hour * 60 * 60) + (permiso.horainicio.minute * 60) + permiso.horainicio.second
                            finpermiso = (permiso.horafin.hour * 60 * 60) + (permiso.horafin.minute * 60) + permiso.horafin.second
                        while iniciopermiso <= finpermiso:
                            c[iniciopermiso].append('p')
                            iniciopermiso += 1
                    for i in c:
                        if len(i):
                            if 'm' in i:
                                if 'j' in i:
                                    totalsegundostrabajados += 1
                                else:
                                    totalsegundosextras += 1
                            elif 'j' in i:
                                if 'p' in i:
                                    totalpermisos += 1
                                else:
                                    totalsegundosatraso += 1
                            else:
                                totalpermisosantes += 1
                    diajornada.totalsegundosatrasos = totalsegundosatraso
                    diajornada.totalsegundostrabajados = totalsegundostrabajados
                    diajornada.totalsegundosextras = totalsegundosextras
                    diajornada.totalsegundospermisos = totalpermisos
                    diajornada.save()
            elif persona.historialjornadatrabajador_set.filter(fechainicio__lte=fechai, fechafin=None).exists():
                jornada = persona.historialjornadatrabajador_set.filter(fechainicio__lte=fechai, fechafin=None)[0]
                if jornada.jornada.detallejornada_set.filter(dia=fechai.isoweekday()).exists():
                    jornadasdia = jornada.jornada.detallejornada_set.filter(dia=fechai.isoweekday())
                    if TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai).exists():
                        diajornada = TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai)[0]
                        diajornada.jornada = jornada.jornada
                        diajornada.totalsegundostrabajados = 0
                        diajornada.totalsegundospermisos = 0
                        diajornada.totalsegundosextras = 0
                        diajornada.totalsegundosatrasos = 0
                    else:
                        diajornada = TrabajadorDiaJornada(persona=persona,
                                                          fecha=fechai,
                                                          anio=fechai.year,
                                                          mes=fechai.month,
                                                          jornada=jornada.jornada)
                        diajornada.save()
                    if persona.marcadasdia_set.filter(fecha=fechai).exists():
                        marcadadia = persona.marcadasdia_set.filter(fecha=fechai)[0]
                    else:
                        marcadadia = MarcadasDia(persona=persona, fecha=fechai)
                        marcadadia.save()
                    totalsegundostrabajados = 0
                    totalsegundosextras = 0
                    totalsegundosatraso = 0
                    totalpermisos = 0
                    totalpermisosantes = 0
                    for marcada in marcadadia.registromarcada_set.all():
                        duracion = (marcada.salida - marcada.entrada).seconds
                        inicio = (marcada.entrada.time().hour * 60 * 60) + (marcada.entrada.time().minute * 60) + marcada.entrada.time().second
                        fin = (marcada.salida.time().hour * 60 * 60) + (marcada.salida.time().minute * 60) + marcada.salida.time().second
                        while inicio <= fin:
                            c[inicio].append('m')
                            inicio += 1
                    for jornadamarcada in jornadasdia:
                        duracionjornada = (datetime(fechai.year, fechai.month, fechai.day, jornadamarcada.horafin.hour, jornadamarcada.horafin.minute, jornadamarcada.horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, jornadamarcada.horainicio.hour, jornadamarcada.horainicio.minute, jornadamarcada.horainicio.second))).seconds
                        iniciojornada = (jornadamarcada.horainicio.hour * 60 * 60) + (jornadamarcada.horainicio.minute * 60) + jornadamarcada.horainicio.second
                        finjornada = (jornadamarcada.horafin.hour * 60 * 60) + (jornadamarcada.horafin.minute * 60) + jornadamarcada.horafin.second
                        while iniciojornada <= finjornada:
                            c[iniciojornada].append('j')
                            iniciojornada += 1
                    for permiso in PermisoInstitucionalDetalle.objects.filter(permisoinstitucional__solicita=persona, fechainicio__lte=fechai, fechafin__gte=fechai, permisoinstitucional__estadosolicitud=3):
                        # VACACIONES
                        if permiso.permisoinstitucional.tiposolicitud == 3:
                            horainicio = datetime(2016, 1, 1, 0, 0, 0)
                            horafin = datetime(2016, 1, 1, 23, 0, 0)
                            duracionpermiso = (datetime(fechai.year, fechai.month, fechai.day, horafin.hour, horafin.minute, horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, horainicio.hour, horainicio.minute, horainicio.second))).seconds
                            iniciopermiso = (horainicio.hour * 60 * 60) + (horainicio.minute * 60) + horainicio.second
                            finpermiso = (horafin.hour * 60 * 60) + (horafin.minute * 60) + horafin.second
                        else:
                            duracionpermiso = (datetime(fechai.year, fechai.month, fechai.day, permiso.horafin.hour, permiso.horafin.minute, permiso.horafin.second) - (datetime(fechai.year, fechai.month, fechai.day, permiso.horainicio.hour, permiso.horainicio.minute, permiso.horainicio.second))).seconds
                            iniciopermiso = (permiso.horainicio.hour * 60 * 60) + (permiso.horainicio.minute * 60) + permiso.horainicio.second
                            finpermiso = (permiso.horafin.hour * 60 * 60) + (permiso.horafin.minute * 60) + permiso.horafin.second
                        while iniciopermiso <= finpermiso:
                            c[iniciopermiso].append('p')
                            iniciopermiso += 1
                    for i in c:
                        if len(i):
                            if 'm' in i:
                                if 'j' in i:
                                    totalsegundostrabajados += 1
                                else:
                                    totalsegundosextras += 1
                            elif 'j' in i:
                                if 'p' in i:
                                    totalpermisos += 1
                                else:
                                    totalsegundosatraso += 1
                            else:
                                totalpermisosantes += 1
                    diajornada.totalsegundosatrasos = totalsegundosatraso
                    diajornada.totalsegundostrabajados = totalsegundostrabajados
                    diajornada.totalsegundosextras = totalsegundosextras
                    diajornada.totalsegundospermisos = totalpermisos
                    diajornada.save()
        else:
            if TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai).exists():
                jornada = persona.historialjornadatrabajador_set.filter(fechainicio__lte=fechai, fechafin=None)[0]
                diajornada = TrabajadorDiaJornada.objects.filter(persona=persona, fecha=fechai)[0]
                diajornada.jornada = jornada.jornada
                diajornada.totalsegundostrabajados = 0
                diajornada.totalsegundospermisos = 0
                diajornada.totalsegundosextras = 0
                diajornada.totalsegundosatrasos = 0
                diajornada.status = False
                diajornada.save()
        fechai += timedelta(days=1)
