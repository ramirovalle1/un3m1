# coding=latin-1
# -*- coding: latin-1 -*-
import random
import json

from bd.models import FLAG_FAILED, APP_POSTULATE, TemplateBaseSetting, FLAG_SUCCESSFUL, FLAG_UNKNOWN, APP_POSTULATE
from moodle.models import UserAuth
from posgrado.models import InscripcionAspirante
from postulate.models import PersonaAplicarPartida
from settings import EMAIL_DOMAIN, ARCHIVO_TIPO_MANUALES, DECLARACION_SAGEST

from urllib.parse import urlencode
from urllib.request import urlopen, Request

from django.contrib.auth import authenticate, login
from decorators import last_access
from bd.funciones import recoveryPassword
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.db.models.query_utils import Q

from datetime import datetime, timedelta

from sga.commonviews import adduserdata
from sga.funciones import variable_valor, calculate_username, generar_usuario_cedula, log, loglogin, resetear_clave, \
    resetear_clave_postulate, convertir_fecha, convertir_fecha_invertida, null_to_decimal
from sga.models import Persona, CUENTAS_CORREOS, PerfilUsuario, Postulante, Group, User, Archivo, miinstitucion, \
    DeclaracionUsuario, Notificacion
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# @last_access
@transaction.atomic()
def login_user(request):
    data = {}
    if EMAIL_DOMAIN in request.META['HTTP_HOST']:
        if 'postulate' not in request.META['HTTP_HOST']:
            if 'admisionposgrado' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginposgrado')
            elif 'sagest' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginsagest')
            elif 'seleccionposgrado' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginpostulacion')
            elif 'sga' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginsga')

    ipvalidas = ['192.168.61.96', '192.168.61.97', '192.168.61.98', '192.168.61.99']
    client_address = get_client_ip(request)
    # site_maintenance = variable_valor('SITIO_MANTENIMIENTO')
    # if site_maintenance:
    #     return render(request, "maintenance.html", data)
    data['currenttime'] = datetime.now()
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'login':
                try:
                    data = {}
                    capippriva = request.POST['capippriva'] if 'capippriva' in request.POST else ''
                    browser = request.POST['navegador']
                    ops = request.POST['os']
                    cookies = request.POST['cookies']
                    screensize = request.POST['screensize']
                    user = authenticate(username=request.POST['user'].lower().strip(), password=request.POST['pass'])
                    if user is not None:
                        if not user.is_active:
                            loglogin(action_flag=FLAG_FAILED, action_app=APP_POSTULATE, ip_private=capippriva, ip_public=client_address,
                                     browser=browser, ops=ops, cookies=cookies, screen_size=screensize, user=user, change_message=u"Usuario no activo")
                            return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, usuario no activo.'})
                        else:
                            if Persona.objects.filter(usuario=user).exists():
                                persona = Persona.objects.filter(usuario=user)[0]
                                if persona.tiene_perfil():
                                    app = 'postulate'
                                    if not Group.objects.filter(pk=356, user=persona.usuario):
                                        usuario = User.objects.get(pk=persona.usuario.id)
                                        g = Group.objects.get(pk=356)
                                        g.user_set.add(usuario)
                                        g.save()
                                    perfiles = persona.mis_perfilesusuarios_app(app)
                                    perfilprincipal = persona.perfilusuario_principal(perfiles, app)
                                    if not perfilprincipal:
                                        if not Postulante.objects.filter(status=True, persona=persona):
                                            postulante = Postulante(persona=persona, activo=True)
                                            postulante.save(request)
                                            if not PerfilUsuario.objects.filter(status=True, postulante=postulante):
                                                perfil = PerfilUsuario(persona=persona, postulante=postulante)
                                                perfil.save(request)
                                    perfilprincipal = persona.perfilusuario_principal(perfiles, app)
                                        # return JsonResponse({"result": "bad", 'mensaje': u'No existe un perfil para esta aplicacion.'})
                                    request.session.set_expiry(240 * 60)
                                    request.session['login_manual'] = True
                                    login(request, user)
                                    request.session['perfiles'] = perfiles
                                    request.session['persona'] = persona
                                    request.session['capippriva'] = capippriva
                                    request.session['tiposistema'] = app
                                    request.session['perfilprincipal'] = perfilprincipal
                                    nombresistema = u'Sistema Postulate'
                                    request.session['nombresistema'] = nombresistema
                                    loglogin(action_flag=FLAG_SUCCESSFUL, action_app=APP_POSTULATE, ip_private=capippriva,
                                             ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                             screen_size=screensize, user=user)
                                    log(u'Login con exito: %s - %s - %s - %s - %s' % (persona, browser, ops, client_address, capippriva), request, "add")
                                    adduserdata(request, data)
                                    send_html_mail("Login exitoso POSTÚLATE", "emails/loginexito.html",
                                                   {'sistema': request.session['nombresistema'], 'fecha': datetime.now().date(), 'hora': datetime.now().time(),
                                                    'bs': browser, 'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies,
                                                    'screensize': screensize, 't': miinstitucion(), 'tit': 'Postulate - Unemi'}, persona.lista_emails_envio(), [],
                                                   cuenta=CUENTAS_CORREOS[30][1])
                                    return JsonResponse({"result": "ok", "sessionid": request.session.session_key})
                                else:
                                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existen perfiles activos.'})
                            else:
                                loglogin(action_flag=FLAG_UNKNOWN, action_app=APP_POSTULATE, ip_private=capippriva,
                                         ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                         screen_size=screensize, change_message=u"USUARIO: %s - CLAVE: %s" % (request.POST['user'].lower().strip(), request.POST['pass']))
                                # log(u'Login fallido, no existe el usuario: %s' % request.POST['user'], request, "add")
                                return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existe el usuario.'})
                    else:
                        if not Persona.objects.filter(usuario__username=request.POST['user'].lower()).exists():
                            loglogin(action_flag=FLAG_UNKNOWN, action_app=APP_POSTULATE, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, change_message=u"USUARIO: %s - CLAVE: %s" % (request.POST['user'].lower().strip(), request.POST['pass']))
                        if Persona.objects.filter(usuario__username=request.POST['user'].lower()).exists():
                            persona = Persona.objects.filter(usuario__username=request.POST['user'].lower())[0]
                            loglogin(action_flag=FLAG_FAILED, action_app=APP_POSTULATE, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, user=persona.usuario, change_message=u"Clave Incorrecta")
                            # log(u'Login fallido POSGRADO: %s - %s - %s - %s - %s' % (persona, browser, ops, client_address, capippriva), request, "add", user=persona.usuario)
                            send_html_mail("Login fallido POSTULATE.", "emails/loginfallido.html",
                                           {'sistema': u'Login fallido, no existen perfiles activos.', 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser,
                                            'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies, 'screensize': screensize,
                                            't': miinstitucion(), 'tit': 'Postulate - Unemi'},
                                           persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[30][1])
                        return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, credenciales incorrectas.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, Error en el sistema. {}'.format(str(ex))})

            elif action == 'registrousuario':
                try:
                    hoy, datospersona = datetime.now().date(), None
                    cedula = request.POST['cedula'].strip()
                    tipoiden = request.POST['id_tipoiden']
                    nombres = request.POST['nombres']
                    nacimiento = convertir_fecha_invertida(request.POST['nacimiento'])
                    apellido1 = request.POST['apellido1']
                    apellido2 = request.POST['apellido2']
                    email = request.POST['email']
                    if (datetime.now().year-nacimiento.year)<18:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Su año de nacimiento indica que es menor de edad."})

                    if Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula)).exists():
                        datospersona = Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula)).first()
                        if Postulante.objects.filter(persona=datospersona):
                            return JsonResponse({"result": "bad", "mensaje": u"Usted ya cuenta con un perfil de postulante."})
                    if tipoiden == '1':
                        if Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula)).exists():
                            datospersona = Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula)).first()
                            datospersona.email = email
                            datospersona.save(request)
                        else:
                            datospersona = Persona(cedula=cedula, nombres=nombres, apellido1=apellido1,
                                                   apellido2=apellido2, email=email, nacimiento=datetime.now().date())
                            datospersona.save(request)
                    if tipoiden == '2':
                        if Persona.objects.filter(Q(pasaporte=cedula) |Q(cedula=cedula)).exists():
                            datospersona = Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula)).first()
                            datospersona.email = email
                            datospersona.save(request)
                        elif cedula[:2] == u'VS':
                            datospersona = Persona(pasaporte=cedula, nombres=nombres, apellido1=apellido1, apellido2=apellido2, email=email, nacimiento=datetime.now().date())
                            datospersona.save(request)
                        else:
                            return JsonResponse({'result': 'bad', "mensaje": u"Pasaporte mal ingresado, no olvide colocar VS al inicio."})
                    datospersona.nacimiento=nacimiento
                    datospersona.save()
                    username_ = None
                    existia = False
                    pass_ = None
                    mensaje = u"Se envio un correo de verificacion de cuenta por favor revisar"
                    if datospersona:
                        if not datospersona.usuario:
                            username_ = calculate_username(datospersona)
                            generar_usuario_cedula(datospersona, username_, 356)
                            password, anio = '', ''
                            if datospersona.nacimiento:
                                anio = "*" + str(datospersona.nacimiento)[0:4]
                            password = datospersona.cedula.strip() + anio
                            mensaje = 'Su usuario es: {} y su clave temporal es su número de cédula: {}'.format(username_, password)
                        else:
                            user_ = User.objects.get(pk=datospersona.usuario.pk)
                            username_ = user_.username
                            group_ = Group.objects.get(pk=356)
                            group_.user_set.add(user_)
                            group_.save()
                            existia = True
                            mensaje = 'Registro exitoso, acceda con sus credenciales del Sistema de Gestión Academica (SGA)'
                    postulante = Postulante(persona=datospersona, activo=True)
                    postulante.save(request)
                    perfil = PerfilUsuario(persona=datospersona, postulante=postulante)
                    perfil.save(request)
                    send_html_mail(u"Registro exitoso Postúlate-UNEMI.", "emails/postulate_registro_usuario.html",
                                   {'sistema': u'Postulación - UNEMI', 'usuario': username_, 'datospersona': datospersona,'fecha': datetime.now(), 'existia': existia, 'clave': cedula, 'tit': 'Postulate - Unemi'},
                                   datospersona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[30][1])
                    return JsonResponse({'result': 'ok', "mensaje": mensaje})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex})

            elif action == 'consultacedula':
                try:
                    cedula = request.POST['cedula'].strip()
                    datospersona, idgenero = None, 0
                    if Persona.objects.filter(cedula=cedula).exists():
                        datospersona = Persona.objects.get(cedula=cedula)
                    elif Persona.objects.filter(pasaporte=cedula).exists():
                        datospersona = Persona.objects.get(pasaporte=cedula)
                    if datospersona:
                        if datospersona.sexo:
                            idgenero = datospersona.sexo_id
                        return JsonResponse({"result": "ok","nacimiento":datospersona.nacimiento, "apellido1": datospersona.apellido1, "apellido2": datospersona.apellido2, "nombres": datospersona.nombres, "email": datospersona.email, "telefono": datospersona.telefono, "idgenero": idgenero})
                    else:
                        return JsonResponse({"result": "no"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'restaurar':
                try:
                    with transaction.atomic():
                        qspostulante = Postulante.objects.filter(status=True, persona__usuario_id=encrypt(request.POST['usuario']))
                        if qspostulante.exists():
                            postulante_ = qspostulante.first()
                            persona_ = postulante_.persona
                            password, anio = '', ''
                            if persona_.nacimiento:
                                anio = "*" + str(persona_.nacimiento)[0:4]
                            password = persona_.cedula.strip() + anio
                            resetear_clave_postulate(persona_)
                            send_html_mail("CONTRASEÑA RESTAURADA", "emails/postulate_cambiar_pass.html",
                                           {'sistema': u'SISTEMA POSTULATE UNEMI', 'persona': persona_, 'pass': password,
                                            't': miinstitucion()}, [persona_.email], [], cuenta=CUENTAS_CORREOS[30][1])
                            emailpersona = "{}*****@{}".format(persona_.email.split('@')[0][:3], persona_.email.split('@')[1])
                            msg = "Se restablecio contraseña, verificar su nueva contraseña en el correo {}".format(emailpersona)
                            res_json = {"resp": True, "message": msg}
                        else:
                            return JsonResponse({'resp': False, "message": "El usuario ingresado no esta asociado a ninguna cuenta de postulante."}, safe=False)
                except Exception as ex:
                    res_json = {'resp': False, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'persona' in request.session:
            return HttpResponseRedirect("/")
        try:
            data['title'] = "Inicio de Sesión | POSTÚLATE"
            data['currenttime'] = datetime.now()
            data['institucion'] = miinstitucion().nombre
            data['tipoentrada'] = request.session['tipoentrada'] = "POSTULATE"
            hoy = datetime.now().date()
            return render(request, "postulate/login/loginpostulate.html", data)
        except Exception as ex:
            import sys
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            pass

def notificaciones(request):
    try:
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'ViewedNotification':
                try:
                    id = request.POST['id'] if 'id' in request.POST and request.POST['id'] else 0
                    notificacion = Notificacion.objects.get(pk=id)
                    if not notificacion:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos"})

                    notificacion.leido = True
                    notificacion.visible = False
                    notificacion.fecha_hora_leido = datetime.now()
                    notificacion.save(request)
                    log(u'Leo el mensaje: %s' % notificacion, request, "edit")
                    return JsonResponse({"result": "ok", 'mensaje': u'Notificación vista'})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos %s" % ex.__str__()})
    except Exception as e:
        pass

def actualizar_nota_postulante(request, postulante=None, sel=None, valor=None):
    perfil = request.session['perfilprincipal']
    if perfil.es_estudiante():
        datos = {"result": "bad"}
    else:
        persona = perfil.persona
        if not postulante:
            postulante = PersonaAplicarPartida.objects.get(pk=request.POST['pid'])
            if not sel:
                sel = request.POST['sel']
            datos = {"result": "ok"}
            modeloevaluativo = postulante.partida.convocatoria.modeloevaluativoconvocatoria
            campomodelo = modeloevaluativo.campo(sel)
            try:
                if not valor:
                    valor = null_to_decimal(float(request.POST['val']), campomodelo.decimales)
                if valor >= campomodelo.notamaxima:
                    valor = campomodelo.notamaxima
                elif valor <= campomodelo.notaminima:
                    valor = campomodelo.notaminima
            except:
                valor = campomodelo.notaminima
            campo = postulante.campo(sel)
            campo.valor = valor
            campo.save()
            d = locals()
            exec(modeloevaluativo.logicamodelo, globals(), d)
            d['calculo_modelo_evaluativo'](postulante)
            postulante.nota_final = null_to_decimal(postulante.nota_final, 2)
            if postulante.nota_final > modeloevaluativo.notamaxima:
                postulante.nota_final = modeloevaluativo.notamaxima
            postulante.save()
            camposdependientes = []
            for campomodelo in modeloevaluativo.campos():
                if campomodelo.dependiente:
                    camposdependientes.append((campomodelo.htmlid(), postulante.valor_nombre_campo(campomodelo.nombre), campomodelo.decimales))

            postulante.actualiza_estado()
            postulante.actualiza_estadofinal()
            postulante.save()
            datos['dependientes'] = camposdependientes
            campo = postulante.campo(sel)
            datos['valor'] = campo.valor
            # log(u'Ingreso de nota Grupo Docente: %s - %s- %s - %s' % (materiaasignada.matricula.inscripcion.persona, materiaasignada.materia.asignatura, sel, str(campo.valor)), request, "add")
            datos['nota_final'] = postulante.nota_final
            datos['estado'] = postulante.get_estado_display()
            datos['estadoid'] = postulante.estado
            datos['idpostulante'] = postulante.id
    return datos
