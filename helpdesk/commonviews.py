# coding=latin-1
from urllib.parse import urlencode
from urllib.request import urlopen, Request
import calendar
import json
from django.contrib.auth import authenticate, login
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from posgrado.models import InscripcionAspirante, CohorteMaestria
from sagest.models import *
from settings import CONTACTO_EMAIL, EMAIL_DOMAIN, DECLARACION_SAGEST, ARCHIVO_TIPO_MANUALES
from sga.commonviews import adduserdata
from sga.funciones import log, calculate_username, generar_usuario_admision, variable_valor, resetear_clavepostulante
from sga.models import Persona, miinstitucion, DeclaracionUsuario, Noticia, Archivo
from sga.tasks import send_html_mail, conectar_cuenta
from posgrado.forms import RegistroForm

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# AUTENTIFICA EL USUARIO
@transaction.atomic()
def login_user(request):
    if EMAIL_DOMAIN in request.META['HTTP_HOST']:
        if 'admisionposgrado' not in request.META['HTTP_HOST']:
            if 'sagest' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginsagest')
            else:
                return HttpResponseRedirect('/loginsga')

    ipvalidas = ['192.168.61.96', '192.168.61.97', '192.168.61.98', '192.168.61.99']
    client_address = get_client_ip(request)
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
                    if not client_address in ipvalidas:
                        if variable_valor('VALIDAR_CON_CAPTCHA_SAGEST'):
                            # ''' Inicio recaptcha validacion '''
                            recaptcha_response = request.POST.get('g-recaptcha-response')
                            url = 'https://www.google.com/recaptcha/api/siteverify'
                            values = {'secret': variable_valor('GOOGLE_RECAPTCHA_SECRET_KEY'),
                                      'response': recaptcha_response
                                      }
                            data = urlencode(values)
                            data = data.encode('utf-8')
                            req = Request(url, data)
                            response = urlopen(req)
                            result = json.loads(response.read().decode())
                            if Persona.objects.filter(usuario__username=request.POST['user'].lower()).exists():
                                persona = Persona.objects.filter(usuario__username=request.POST['user'].lower())[0]
                                log(u'CAPTCHA ERROR SAGEST: %s - %s - %s - %s' % (persona, browser, ops, client_address), request, "add", user=persona.usuario)
                            if not result['success']:
                                return HttpResponse(
                                    json.dumps({"result": "bad", 'mensaje': u'ReCaptcha no válido. Vuelve a intentarlo..'}),content_type="application/json")
                            # ''' Fin recaptcha validacion '''

                    user = authenticate(username=request.POST['user'].lower().strip(), password=request.POST['pass'])
                    if user is not None:
                        if not user.is_active:
                            return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, usuario no activo.'})
                        else:
                            if Persona.objects.filter(usuario=user).exists():
                                persona = Persona.objects.filter(usuario=user)[0]
                                if persona.tiene_perfil():
                                    app = 'helpdesk'
                                    if not InscripcionAspirante.objects.filter(persona=persona):
                                        aspirante = InscripcionAspirante(persona=persona)
                                        aspirante.save()
                                        persona.crear_perfil(inscripcionaspirante=aspirante)
                                        usuario = User.objects.get(pk=persona.usuario.id)
                                        g = Group.objects.get(pk=199)
                                        g.user_set.add(usuario)
                                        g.save()
                                    perfiles = persona.mis_perfilesusuarios_app(app)
                                    perfilprincipal = persona.perfilusuario_principal(perfiles, app)
                                    if not perfilprincipal:
                                        return JsonResponse({"result": "bad", 'mensaje': u'No existe un perfiles para esta aplicacion.'})
                                    request.session.set_expiry(240 * 60)
                                    request.session['login_manual'] = True
                                    login(request, user)
                                    data['archivos'] = Archivo.objects.filter(tipo__id=ARCHIVO_TIPO_MANUALES,grupo_id=199, sga=True, visible=True)
                                    request.session['perfiles'] = perfiles
                                    request.session['persona'] = persona
                                    request.session['capippriva'] = capippriva
                                    request.session['tiposistema'] = app
                                    request.session['perfilprincipal'] = perfilprincipal
                                    request.session['nombresistema'] = u'Sistema HelpDesk'

                                    log(u'Login con exito: %s - %s - %s - %s - %s' % (persona, browser, ops, client_address, capippriva), request, "add")
                                    # validacion ldap por sga
                                    if client_address in ipvalidas:
                                        if DECLARACION_SAGEST:
                                            declaracionusuario = DeclaracionUsuario(persona=persona,
                                                                                    fecha=datetime.now(),
                                                                                    ip=client_address,
                                                                                    sistema='HELPDESK')
                                            declaracionusuario.save(request)
                                            log(u'Declaracion de usuario en el helpdesk: %s [%s]' % (declaracionusuario, declaracionusuario.id), request, "add")
                                    adduserdata(request, data)
                                    send_html_mail("Login exitoso HELPDESK", "emails/loginexito.html", {'sistema': request.session['nombresistema'], 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies, 'screensize': screensize, 't': miinstitucion()}, persona.lista_emails_envio(), [], cuenta=variable_valor('CUENTAS_CORREOS')[4])
                                    return JsonResponse({"result": "ok", "sessionid": request.session.session_key})
                                else:
                                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existen perfiles activos.'})
                            else:
                                log(u'Login fallido, no existe el usuario: %s' % request.POST['user'], request, "add")
                                return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existe el usuario.'})
                    else:
                        if Persona.objects.filter(usuario__username=request.POST['user'].lower()).exists():
                            persona = Persona.objects.filter(usuario__username=request.POST['user'].lower())[0]
                            log(u'Login fallido HELPDESK: %s - %s - %s - %s - %s' % (persona, browser, ops, client_address, capippriva), request, "add", user=persona.usuario)
                            send_html_mail("Login fallido POSGRADO.", "emails/loginfallido.html", {'sistema': u'Login fallido, no existen perfiles activos.', 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies, 'screensize': screensize, 't': miinstitucion()}, persona.lista_emails_envio(), [], cuenta=variable_valor('CUENTAS_CORREOS')[4])
                        return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, credenciales incorrectas.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, Error en el sistema.'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'persona' in request.session:
            return HttpResponseRedirect("/")
        data = {"title": u"Login", "background": 9}
        data['request'] = request
        hoy = datetime.now().date()
        # data['noticias'] = Noticia.objects.filter(Q(desde__lte=hoy), Q(hasta__gte=hoy), Q(imagen__isnull=True),(Q(publicacion=1) | Q(publicacion=3))).order_by('-desde', 'id')[0:5]
        data['noticias'] = Noticia.objects.filter(Q(desde__lte=hoy), Q(hasta__gte=hoy), Q(imagen__isnull=True), (Q(publicacion=1) | Q(publicacion=3)), banerderecho=False, tipos__in=[1]).distinct().order_by('-desde', 'id')[0:5]
        # data['noticiasgraficas'] = Noticia.objects.filter(Q(desde__lte=hoy), Q(hasta__gte=hoy), Q(imagen__isnull=False),(Q(publicacion=1) | Q(publicacion=3))).order_by('-desde','id')[:1]
        data['noticiasgraficas'] = None
        data['currenttime'] = datetime.now()
        data['institucion'] = miinstitucion().nombre
        data['contacto_email'] = CONTACTO_EMAIL
        data['puedeinscribirse'] = CohorteMaestria.objects.filter(fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True)
        if client_address in ipvalidas:
            data['validar_con_captcha'] = False
            data['declaracion_sagest'] = False
        else:
            data['validar_con_captcha'] = variable_valor('VALIDAR_CON_CAPTCHA_SAGEST')
            data['declaracion_sagest'] = DECLARACION_SAGEST
        data['tipoentrada'] = request.session['tipoentrada'] = "POSGRADO"
        data['public_key'] = variable_valor('GOOGLE_RECAPTCHA_PUBLIC_KEY')
        return render(request, "loginposgrado.html", data)

@transaction.atomic()
def registro_user(request):
    if request.method == 'POST':
        try:
            browser = request.POST['navegador']
            ops = request.POST['os']
            cookies = request.POST['cookies']
            screensize = request.POST['screensize']
            hoy = datetime.now().date()
            f = RegistroForm(request.POST)
            if f.is_valid():
                if f.cleaned_data['cedula'][:2] == u'VS':
                    if not Persona.objects.filter(pasaporte=f.cleaned_data['cedula'][2:]).exists():
                        if not Persona.objects.filter(email=f.cleaned_data['email']).exists():
                            persona = Persona(pasaporte=f.cleaned_data['cedula'][2:],
                                              nombres=f.cleaned_data['nombres'],
                                              apellido1=f.cleaned_data['apellido1'],
                                              apellido2=f.cleaned_data['apellido2'],
                                              email=f.cleaned_data['email'],
                                              sexo_id=request.POST['genero'],
                                              nacimiento='1999-01-01',
                                              direccion='',
                                              direccion2=''
                                              )
                            persona.save()
                            nomusername = calculate_username(persona)
                            generar_usuario_admision(persona, nomusername, 199)
                            # username = persona.identificacion()
                            # clave = persona.identificacion()
                            # generar_usuario_admision(persona, username,clave)
                            # send_html_mail(u"Registro exitoso Admisión-UNEMI.","emails/registroexito.html",  {'sistema': u'Admisión - UNEMI', 'usuario': nomusername, 'fecha': datetime.now().date(), 'hora': datetime.now().time(),'clave': persona.identificacion(), 't': miinstitucion()}, persona.emailpersonal(), [], cuenta=CUENTAS_CORREOS[4][1])
                            send_html_mail("Registro exitoso Admision-UNEMI.", "emails/registroexito.html", {'sistema': u'Admision - UNEMI', 'usuario': nomusername,'clave': persona.identificacion(), 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'os': ops, 'cookies': cookies,  'screensize': screensize, 't': miinstitucion()}, persona.emailpersonal(),  [], cuenta=variable_valor('CUENTAS_CORREOS')[4])
                        else:
                            return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Correo ya existe, si no recuerda el usuario y la clave, siga los pasos en la opción, Olvidó su usuario y contraseña?.: "}), content_type="application/json")
                    else:
                        return HttpResponse(json.dumps({"result": "bad", "mensaje": "Persona ya existe.: "}), content_type="application/json")
                else:
                    if not Persona.objects.filter(cedula=f.cleaned_data['cedula']).exists():
                        # if not Persona.objects.filter(email=f.cleaned_data['email']).exists():
                        persona = Persona(cedula=f.cleaned_data['cedula'],
                                          nombres=f.cleaned_data['nombres'],
                                          apellido1=f.cleaned_data['apellido1'],
                                          apellido2=f.cleaned_data['apellido2'],
                                          email=f.cleaned_data['email'],
                                          sexo_id=request.POST['genero'],
                                          nacimiento='1999-01-01',
                                          direccion='',
                                          direccion2=''
                                          )
                        persona.save()
                        nomusername = calculate_username(persona)
                        generar_usuario_admision(persona, nomusername, 199)
                        aspirante = InscripcionAspirante(persona=persona)
                        aspirante.save()
                        # persona.guardar_inscripcion()
                        persona.crear_perfil(inscripcionaspirante=aspirante)
                        persona.mi_perfil()
                        # username = persona.identificacion()
                        # clave = persona.identificacion()
                        # generar_usuario_admision(persona, username, clave)
                        # send_html_mail(u"Registro exitoso Admisión-UNEMI.", "emails/registroexito.html",  {'sistema': u'Admisión - UNEMI', 'usuario': nomusername, 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'clave': persona.identificacion(), 't': miinstitucion()}, persona.emailpersonal(), [], cuenta=CUENTAS_CORREOS[4][1])
                        send_html_mail("Registro exitoso Admision-UNEMI.", "emails/registroexito.html",{'sistema': u'Admision - UNEMI','usuario': nomusername,'clave': persona.identificacion(), 'fecha': datetime.now().date(),'hora': datetime.now().time(), 'bs': browser,'os': ops, 'cookies': cookies,'screensize': screensize, 't': miinstitucion()},persona.emailpersonal(), [],cuenta=variable_valor('CUENTAS_CORREOS')[4])
                    # else:
                    #     return HttpResponse(json.dumps({"result": "bad", "mensaje": u"Correo ya existe, si no recuerda el usuario y la clave, siga los pasos en la opción, Olvidó su usuario y contraseña?.: "}), content_type="application/json")
                    else:
                        postulante = Persona.objects.get(cedula=f.cleaned_data['cedula'])
                        if postulante.es_estudiante() and not postulante.es_profesor()and not postulante.es_administrativo():
                            if not InscripcionAspirante.objects.filter(persona=postulante):
                                nomusername = postulante.usuario.username
                                postulante.email = f.cleaned_data['email']
                                postulante.save()
                                aspirante = InscripcionAspirante(persona=postulante)
                                aspirante.save()
                                postulante.crear_perfil(inscripcionaspirante=aspirante)
                                postulante.mi_perfil()
                                usuario = User.objects.get(pk=postulante.usuario.id)
                                g = Group.objects.get(pk=199)
                                g.user_set.add(usuario)
                                g.save()
                                resetear_clavepostulante(postulante)

                                send_html_mail("Registro exitoso Admision-UNEMI.", "emails/registroexito.html", {'sistema': u'Admision - UNEMI', 'usuario': postulante.usuario.username,'clave': postulante.identificacion(), 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'os': ops, 'cookies': cookies,'screensize': screensize, 't': miinstitucion()}, postulante.emailpersonal(),  [], cuenta=variable_valor('CUENTAS_CORREOS')[4])
                                return HttpResponse(json.dumps({"result": "ok", "usu": nomusername}), content_type="application/json")
                            else:
                                nomusername = postulante.usuario.username
                                postulante.email = f.cleaned_data['email']
                                postulante.save()
                                resetear_clavepostulante(postulante)

                                send_html_mail("Registro exitoso Admision-UNEMI.", "emails/registroexito.html",{'sistema': u'Admision - UNEMI', 'usuario': postulante.usuario.username, 'clave': postulante.identificacion(), 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'os': ops, 'cookies': cookies, 'screensize': screensize, 't': miinstitucion()},postulante.emailpersonal(), [],cuenta=variable_valor('CUENTAS_CORREOS')[4])
                                return HttpResponse(json.dumps({"result": "ok", "usu": nomusername}), content_type="application/json")
                            send_html_mail("Registro exitoso Admision-UNEMI.", "emails/registroexito.html", {'sistema': u'Admision - UNEMI', 'usuario': postulante.usuario.username,'clave': postulante.identificacion(), 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'os': ops, 'cookies': cookies,'screensize': screensize, 't': miinstitucion()}, postulante.emailpersonal(),  [], cuenta=variable_valor('CUENTAS_CORREOS')[4])
                        if postulante.externo_set.filter(status=True) and not postulante.es_profesor()and not postulante.es_administrativo():
                            if not InscripcionAspirante.objects.filter(persona=postulante):
                                if not postulante.usuario:
                                    nomusername = calculate_username(postulante)
                                    generar_usuario_admision(postulante, nomusername, 199)
                                else:
                                    nomusername = postulante.usuario.username
                                postulante.email = f.cleaned_data['email']
                                postulante.emailinst = f.cleaned_data['email']
                                postulante.save()
                                aspirante = InscripcionAspirante(persona=postulante)
                                aspirante.save()
                                postulante.crear_perfil(inscripcionaspirante=aspirante)
                                postulante.mi_perfil()
                                usuario = User.objects.get(pk=postulante.usuario.id)
                                g = Group.objects.get(pk=199)
                                g.user_set.add(usuario)
                                g.save()
                                resetear_clavepostulante(postulante)

                                send_html_mail("Registro exitoso Admision-UNEMI.", "emails/registroexito.html", {'sistema': u'Admision - UNEMI', 'usuario': postulante.usuario.username,'clave': postulante.identificacion(), 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'os': ops, 'cookies': cookies,'screensize': screensize, 't': miinstitucion()}, postulante.emailpersonal(),  [], cuenta=variable_valor('CUENTAS_CORREOS')[4])
                                return HttpResponse(json.dumps({"result": "ok", "usu": nomusername}), content_type="application/json")
                        if postulante.inscripcionaspirante_set.filter(status=True):
                            return HttpResponse(json.dumps({"result": "bad", "mensaje": "Persona ya existe, favor ingresar con su usuario y clave.: "}), content_type="application/json")
                        if postulante.es_administrativo():
                            return HttpResponse(json.dumps({"result": "bad", "mensaje": "Persona ya existe, favor ingresar con su usuario y clave.: "}), content_type="application/json")
                        if postulante.es_profesor():
                            return HttpResponse(json.dumps({"result": "bad", "mensaje": "Persona ya existe, favor ingresar con su usuario y clave.: "}), content_type="application/json")
                        return HttpResponse(json.dumps({"result": "bad", "mensaje": "Error al guardar.: "}), content_type="application/json")
                return HttpResponse(json.dumps({"result": "ok","usu": nomusername}), content_type="application/json")
        except Exception as ex:
            transaction.set_rollback(True)
            return HttpResponseRedirect('/loginposgrado')
def secuencia_ordentrabajo(request, anio):
    anioe = AnioEjercicio.objects.get(anioejercicio=anio)
    if not SecuenciaHdIncidente.objects.filter(anioejercicio=anioe).exists():
        secuencia = SecuenciaHdIncidente(anioejercicio=anioe)
        secuencia.save(request)
        return secuencia
    else:
        return SecuenciaHdIncidente.objects.filter(anioejercicio=anioe)[0]
