# coding=latin-1
from urllib.parse import urlencode
from urllib.request import urlopen, Request
import calendar
import json
import random
from django.contrib.auth import authenticate, login
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from sga.funciones import fechatope, loglogin
from moodle.models import UserAuth
from posgrado.models import InscripcionAspirante, CohorteMaestria, InscripcionCohorte, FormatoCarreraIpec, SecuenciaContratoPagare, MaestriasAdmision
from sagest.models import *
from settings import CONTACTO_EMAIL, EMAIL_DOMAIN, DECLARACION_SAGEST, ARCHIVO_TIPO_MANUALES, USA_TIPOS_INSCRIPCIONES, TIPO_INSCRIPCION_INICIAL
from sga.commonviews import adduserdata
from sga.funciones import log, calculate_username, generar_usuario_admision, variable_valor, resetear_clavepostulante
from sga.models import Persona, miinstitucion, DeclaracionUsuario, Noticia, Archivo, Carrera, PerfilUsuario, Nivel, \
    Periodo, Titulacion, CamposTitulosPostulacion, Graduado, DocumentosDeInscripcion, InscripcionTesDrive, \
    InscripcionTipoInscripcion, \
    ItinerarioMallaEspecilidad, CUENTAS_CORREOS
from inno.models import ProgramaPac
from sga.tasks import send_html_mail, conectar_cuenta
from posgrado.forms import RegistroForm, RegistroAdmisionIpecForm
from sga.templatetags.sga_extras import encrypt
from bd.models import APP_SGA, APP_SAGEST, APP_POSGRADO, FLAG_FAILED, FLAG_SUCCESSFUL, FLAG_UNKNOWN, TemplateBaseSetting


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
            if 'seleccionposgrado' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginpostulacion')
            elif 'sagest' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginsagest')
            elif 'postulate' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginpostulate')
            elif 'sga' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginsga')
            else:
                return HttpResponseRedirect('/loginsga')

    ipvalidas = ['192.168.61.96', '192.168.61.97', '192.168.61.98', '192.168.61.99']
    client_address = get_client_ip(request)
    site_maintenance = variable_valor('SITIO_MANTENIMIENTO')
    if site_maintenance:
        data = {}
        return render(request, "maintenance.html", data)
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
                            loglogin(action_flag=FLAG_FAILED, action_app=APP_POSGRADO, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, user=user, change_message=u"Usuario no activo")
                            return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, usuario no activo.'})
                        else:
                            if not UserAuth.objects.filter(usuario=user).exists():
                                usermoodle = UserAuth(usuario=user)
                                usermoodle.set_data()
                                usermoodle.set_password(request.POST['pass'])
                                usermoodle.save()
                            else:
                                usermoodle = UserAuth.objects.filter(usuario=user).first()
                                isUpdateUserMoodle = False
                                if not usermoodle.check_password(request.POST['pass']) or usermoodle.check_data():
                                    if not usermoodle.check_password(request.POST['pass']):
                                        usermoodle.set_password(request.POST['pass'])
                                    usermoodle.save()
                            if Persona.objects.filter(usuario=user).exists():
                                persona = Persona.objects.filter(usuario=user)[0]
                                if persona.tiene_perfil():
                                    app = 'posgrado'
                                    if not InscripcionAspirante.objects.filter(persona=persona):
                                        aspirante = InscripcionAspirante(persona=persona)
                                        aspirante.save()
                                        persona.crear_perfil(inscripcionaspirante=aspirante)
                                        usuario = User.objects.get(pk=persona.usuario.id)
                                        g = Group.objects.get(pk=199)
                                        g.user_set.add(usuario)
                                        g.save()
                                    if not Group.objects.filter(pk=199, user=persona.usuario):
                                        usuario = User.objects.get(pk=persona.usuario.id)
                                        g = Group.objects.get(pk=199)
                                        g.user_set.add(usuario)
                                        g.save()
                                    perfilesvalida = persona.mis_perfilesusuarios_app(app)
                                    perfilprincipalvalida = persona.perfilusuario_principal(perfilesvalida, app)
                                    if not perfilprincipalvalida:
                                        aspirante = InscripcionAspirante.objects.filter(persona=persona)[0]
                                        persona.crear_perfil(inscripcionaspirante=aspirante)
                                        persona.mi_perfil()
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
                                    nombresistema = u'Sistema Posgrado'
                                    request.session['eTemplateBaseSetting'] = None
                                    request.session['nombresistema'] = nombresistema
                                    loglogin(action_flag=FLAG_SUCCESSFUL, action_app=APP_POSGRADO, ip_private=capippriva,
                                             ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                             screen_size=screensize, user=user)
                                    # log(u'Login con exito: %s - %s - %s - %s - %s' % (persona, browser, ops, client_address, capippriva), request, "add")
                                    # validacion ldap por sga
                                    if client_address in ipvalidas:
                                        if DECLARACION_SAGEST:
                                            declaracionusuario = DeclaracionUsuario(persona=persona,
                                                                                    fecha=datetime.now(),
                                                                                    ip=client_address,
                                                                                    sistema='POSGRADO')
                                            declaracionusuario.save(request)
                                            log(u'Declaracion de usuario en el posgrado: %s [%s]' % (declaracionusuario, declaracionusuario.id), request, "add")
                                    adduserdata(request, data)
                                    # send_html_mail("Login exitoso POSGRADO", "emails/loginexito.html", {'sistema': request.session['nombresistema'], 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies, 'screensize': screensize, 't': miinstitucion()}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[28][1])
                                    return JsonResponse({"result": "ok", "sessionid": request.session.session_key})
                                else:
                                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existen perfiles activos.'})
                            else:
                                loglogin(action_flag=FLAG_UNKNOWN, action_app=APP_POSGRADO, ip_private=capippriva,
                                         ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                         screen_size=screensize, change_message=u"USUARIO: %s - CLAVE: %s" % (request.POST['user'].lower().strip(), request.POST['pass']))
                                # log(u'Login fallido, no existe el usuario: %s' % request.POST['user'], request, "add")
                                return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existe el usuario.'})
                    else:
                        if not Persona.objects.filter(usuario__username=request.POST['user'].lower()).exists():
                            loglogin(action_flag=FLAG_UNKNOWN, action_app=APP_POSGRADO, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, change_message=u"USUARIO: %s - CLAVE: %s" % (request.POST['user'].lower().strip(), request.POST['pass']))
                        if Persona.objects.filter(usuario__username=request.POST['user'].lower()).exists():
                            persona = Persona.objects.filter(usuario__username=request.POST['user'].lower())[0]
                            loglogin(action_flag=FLAG_FAILED, action_app=APP_POSGRADO, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, user=persona.usuario, change_message=u"Clave Incorrecta")
                            # log(u'Login fallido POSGRADO: %s - %s - %s - %s - %s' % (persona, browser, ops, client_address, capippriva), request, "add", user=persona.usuario)
                            send_html_mail("Login fallido POSGRADO.", "emails/loginfallido.html", {'sistema': u'Login fallido, no existen perfiles activos.', 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies, 'screensize': screensize, 't': miinstitucion()}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[28][1])
                        return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, credenciales incorrectas.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, Error en el sistema.'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'persona' in request.session:
            return HttpResponseRedirect("/alu_requisitosmaestria")
            # return HttpResponseRedirect("/")
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
            arregloemail = [23, 24, 25, 26, 27, 28]
            emailaleatorio = random.choice(arregloemail)
            tipoconta = None
            tipobeca = None
            # if int(tipobeca) == 0:
            #     tipobeca = None
            idcarrera = encrypt(request.POST['idcarrera'])
            nomcarrera = Carrera.objects.get(pk=encrypt(request.POST['idcarrera']))
            # idtitulo = request.POST['titulo']
            # cantexperiencia = request.POST['cantexperiencia']
            itinerario = 0
            if 'itinerario' in request.POST:
                if request.POST['itinerario'] != '':
                    itinerario = request.POST['itinerario']
            hoy = datetime.now().date()
            canal = request.POST['canal']
            convenio = None
            if request.POST['convenio'] != "":
                convenio = request.POST['convenio']
            zona = False
            if request.POST['zona'] == 'true':
                zona = True
            elif request.POST['zona'] == 'false':
                zona = False
            f = RegistroAdmisionIpecForm(request.POST)
            if f.is_valid():
                if (f.cleaned_data['cedula'][:2] == u'VS' or f.cleaned_data['cedula'][:2] == u'vs') and not Persona.objects.filter(pasaporte=f.cleaned_data['cedula'][2:]).exists():
                    persona = Persona(pasaporte=f.cleaned_data['cedula'][2:],
                                      nombres=f.cleaned_data['nombres'],
                                      apellido1=f.cleaned_data['apellido1'],
                                      apellido2=f.cleaned_data['apellido2'],
                                      email=f.cleaned_data['email'],
                                      telefono=f.cleaned_data['telefono'],
                                      sexo_id=request.POST['genero'],
                                      nacimiento='1999-01-01',
                                      pais_id=request.POST['pais'],
                                      provincia_id=request.POST['provincia'],
                                      canton_id=request.POST['canton'],
                                      direccion=request.POST['direccion'],
                                      direccion2=''
                                      )
                    persona.save()
                    nomusername = calculate_username(persona)
                    persona.emailinst = nomusername + '@unemi.edu.ec'
                    persona.save()
                    generar_usuario_admision(persona, nomusername, 199)
                    if not InscripcionAspirante.objects.filter(persona=persona, status=True).exists():
                        aspirante = InscripcionAspirante(persona=persona)
                        aspirante.save()
                    else:
                        aspirante = InscripcionAspirante.objects.filter(persona=persona, status=True)[0]

                    if InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes__maestriaadmision__carrera=nomcarrera, status=False, activo=True,
                                                         estado_aprobador__in=[1, 2]).exists():
                        ins = InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante,
                                                                cohortes__maestriaadmision__carrera=nomcarrera,
                                                                status=False,
                                                                estado_aprobador__in=[1, 2]).order_by('-id').first()
                        ins.revivir_postulacion()
                        return HttpResponse(json.dumps({"result": "ok", "mensaje": "Usted ya ha postulado anteriormente en una cohorte de este programa de maestría. Por favor, revise su plataforma de admisión posgrado."}), content_type="application/json")
                    else:
                        if CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True).exists():
                            cohortemaestria = CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True)[0]
                            if nomcarrera.malla():
                                if nomcarrera.malla().tiene_itinerario_malla_especialidad():
                                    if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                        inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                cohortes=cohortemaestria,
                                                                                tipobeca_id=tipobeca,
                                                                                contactomaestria=tipoconta,
                                                                                # tiulacionaspirante_id=idtitulo,
                                                                                # cantexperiencia=cantexperiencia,
                                                                                formapagopac_id=1,
                                                                                itinerario=request.POST['itinerario'],
                                                                                canal_id=canal,
                                                                                leaddezona=zona,
                                                                                convenio_id=convenio)
                                        inscripcioncohorte.save(request)
                                        asesorconvenio = False
                                        if inscripcioncohorte.convenio:
                                            asesorconvenio = inscripcioncohorte.asignar_asesor_convenio()
                                        if not asesorconvenio:
                                            inscripcioncohorte.reservar_lead_territorio()
                                            inscripcioncohorte.asignar_mismo_asesor()
                                        # inscripcioncohorte.reservar_lead_territorio()
                                        # inscripcioncohorte.asignar_mismo_asesor()
                                else:
                                    if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                        inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                cohortes=cohortemaestria,
                                                                                tipobeca_id=tipobeca,
                                                                                # tiulacionaspirante_id=idtitulo,
                                                                                # cantexperiencia=cantexperiencia,
                                                                                formapagopac_id=1,
                                                                                contactomaestria=tipoconta,
                                                                                canal_id=canal,
                                                                                leaddezona=zona,
                                                                                convenio_id=convenio)
                                        inscripcioncohorte.save(request)
                                        asesorconvenio = False
                                        if inscripcioncohorte.convenio:
                                            asesorconvenio = inscripcioncohorte.asignar_asesor_convenio()
                                        if not asesorconvenio:
                                            inscripcioncohorte.reservar_lead_territorio()
                                            inscripcioncohorte.asignar_mismo_asesor()
                                        # inscripcioncohorte.reservar_lead_territorio()
                                        # inscripcioncohorte.asignar_mismo_asesor()
                            else:
                                if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                    inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                            cohortes=cohortemaestria,
                                                                            tipobeca_id=tipobeca,
                                                                            # tiulacionaspirante_id=idtitulo,
                                                                            # cantexperiencia=cantexperiencia,
                                                                            formapagopac_id=1,
                                                                            contactomaestria=tipoconta,
                                                                            canal_id=canal,
                                                                            leaddezona=zona,
                                                                            convenio_id=convenio)
                                    inscripcioncohorte.save(request)
                                    asesorconvenio = False
                                    if inscripcioncohorte.convenio:
                                        asesorconvenio = inscripcioncohorte.asignar_asesor_convenio()
                                    if not asesorconvenio:
                                        inscripcioncohorte.reservar_lead_territorio()
                                        inscripcioncohorte.asignar_mismo_asesor()
                                    # inscripcioncohorte.reservar_lead_territorio()
                                    # inscripcioncohorte.asignar_mismo_asesor()
                        persona.crear_perfil(inscripcionaspirante=aspirante)
                        persona.mi_perfil()
                        lista = []
                        if persona.emailinst:
                            lista.append(persona.emailinst)
                        if persona.email:
                            lista.append(persona.email)
                        resetear_clavepostulante(persona)
                        if persona.cedula:
                            clavepostulante = persona.cedula.strip()
                        elif persona.pasaporte:
                            clavepostulante = persona.pasaporte.strip()
                        validapersonal(aspirante, idcarrera, lista, nomcarrera, persona.usuario.username, clavepostulante, itinerario, canal)
                        return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")
                else:
                    if not Persona.objects.filter(Q(cedula=f.cleaned_data['cedula']) | Q(pasaporte=f.cleaned_data['cedula'])).exists():
                        # if not Persona.objects.filter(email=f.cleaned_data['email']).exists():
                        persona = Persona(cedula=f.cleaned_data['cedula'],
                                          nombres=f.cleaned_data['nombres'],
                                          apellido1=f.cleaned_data['apellido1'],
                                          apellido2=f.cleaned_data['apellido2'],
                                          email=f.cleaned_data['email'],
                                          telefono=f.cleaned_data['telefono'],
                                          sexo_id=request.POST['genero'],
                                          nacimiento='1999-01-01',
                                          pais_id=request.POST['pais'],
                                          provincia_id=request.POST['provincia'],
                                          canton_id=request.POST['canton'],
                                          direccion=request.POST['direccion'],
                                          direccion2=''
                                          )
                        persona.save()
                        nomusername = calculate_username(persona)
                        persona.emailinst = nomusername + '@unemi.edu.ec'
                        persona.save()
                        generar_usuario_admision(persona, nomusername, 199)
                        aspirante = InscripcionAspirante(persona=persona)
                        aspirante.save()

                        if InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes__maestriaadmision__carrera=nomcarrera, status=False, activo=True,
                                                             estado_aprobador__in=[1, 2]).exists():
                            ins = InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante,
                                                                    cohortes__maestriaadmision__carrera=nomcarrera,
                                                                    status=False, estado_aprobador__in=[1, 2]).order_by('-id').first()
                            ins.revivir_postulacion()
                            return HttpResponse(json.dumps({"result": "ok", "mensaje": "Usted ya ha postulado anteriormente en una cohorte de este programa de maestría. Por favor, revise su plataforma de admisión posgrado."}), content_type="application/json")
                        else:
                            if CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True).exists():
                                cohortemaestria = CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True)[0]
                                if nomcarrera.malla():
                                    if nomcarrera.malla().tiene_itinerario_malla_especialidad():
                                        if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                            inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                    cohortes=cohortemaestria,
                                                                                    tipobeca_id=tipobeca,
                                                                                    contactomaestria=tipoconta,
                                                                                    # tiulacionaspirante_id=idtitulo,
                                                                                    # cantexperiencia=cantexperiencia,
                                                                                    formapagopac_id=1,
                                                                                    itinerario=request.POST['itinerario'],
                                                                                    canal_id=canal,
                                                                                    leaddezona=zona,
                                                                                    convenio_id=convenio)
                                            inscripcioncohorte.save(request)
                                            asesorconvenio = False
                                            if inscripcioncohorte.convenio:
                                                asesorconvenio = inscripcioncohorte.asignar_asesor_convenio()
                                            if not asesorconvenio:
                                                inscripcioncohorte.reservar_lead_territorio()
                                                inscripcioncohorte.asignar_mismo_asesor()
                                            # inscripcioncohorte.reservar_lead_territorio()
                                            # inscripcioncohorte.asignar_mismo_asesor()
                                    else:
                                        if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                            inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                    cohortes=cohortemaestria,
                                                                                    tipobeca_id=tipobeca,
                                                                                    # tiulacionaspirante_id=idtitulo,
                                                                                    # cantexperiencia=cantexperiencia,
                                                                                    formapagopac_id=1,
                                                                                    contactomaestria=tipoconta,
                                                                                    canal_id=canal,
                                                                                    leaddezona=zona,
                                                                                    convenio_id=convenio)
                                            inscripcioncohorte.save(request)
                                            asesorconvenio = False
                                            if inscripcioncohorte.convenio:
                                                asesorconvenio = inscripcioncohorte.asignar_asesor_convenio()
                                            if not asesorconvenio:
                                                inscripcioncohorte.reservar_lead_territorio()
                                                inscripcioncohorte.asignar_mismo_asesor()
                                            # inscripcioncohorte.reservar_lead_territorio()
                                            # inscripcioncohorte.asignar_mismo_asesor()
                                else:
                                    if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                        inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                cohortes=cohortemaestria,
                                                                                tipobeca_id=tipobeca,
                                                                                # tiulacionaspirante_id=idtitulo,
                                                                                # cantexperiencia=cantexperiencia,
                                                                                formapagopac_id=1,
                                                                                contactomaestria=tipoconta,
                                                                                canal_id=canal,
                                                                                leaddezona=zona,
                                                                                convenio_id=convenio)
                                        inscripcioncohorte.save(request)
                                        asesorconvenio = False
                                        if inscripcioncohorte.convenio:
                                            asesorconvenio = inscripcioncohorte.asignar_asesor_convenio()
                                        if not asesorconvenio:
                                            inscripcioncohorte.reservar_lead_territorio()
                                            inscripcioncohorte.asignar_mismo_asesor()
                                        # inscripcioncohorte.reservar_lead_territorio()
                                        # inscripcioncohorte.asignar_mismo_asesor()
                            persona.crear_perfil(inscripcionaspirante=aspirante)
                            persona.mi_perfil()
                            lista = []
                            if persona.emailinst:
                                lista.append(persona.emailinst)
                            if persona.email:
                                lista.append(persona.email)
                            resetear_clavepostulante(persona)
                            if persona.cedula:
                                clavepostulante = persona.cedula.strip()
                            elif persona.pasaporte:
                                clavepostulante = persona.pasaporte.strip()
                            validapersonal(aspirante, idcarrera, lista, nomcarrera, persona.usuario.username, clavepostulante, itinerario, canal)
                            # return HttpResponse(json.dumps({"result": "ok", "mensaje": "Usuario ya pre inscrito, te hemos enviado un email con tu usuario y clave para poder acceder a https://admisionposgrado.unemi.edu.ec/loginposgrado <a class='btn btn-success' href='https://admisionposgrado.unemi.edu.ec/loginposgrado' target='_blank'><i class='fa fa-arrow-right'></i> Ingresar</a> \n usuario:" + persona.usuario.username + " \n clave: " + clavepostulante + ""}), content_type="application/json")
                            return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")
                    else:
                        postulante = Persona.objects.get(Q(cedula=f.cleaned_data['cedula']) | Q(pasaporte=f.cleaned_data['cedula']),status=True)

                        if InscripcionCohorte.objects.filter(inscripcionaspirante__persona=postulante, cohortes__maestriaadmision__carrera=nomcarrera, status=False, activo=True,
                                                             estado_aprobador__in=[1, 2]).exists():
                            ins = InscripcionCohorte.objects.filter(inscripcionaspirante__persona=postulante,
                                                                    cohortes__maestriaadmision__carrera=nomcarrera,
                                                                    status=False,
                                                                    estado_aprobador__in=[1, 2]).order_by('-id').first()
                            ins.revivir_postulacion()
                            return HttpResponse(json.dumps({"result": "ok", "mensaje": "Usted ya ha postulado anteriormente en una cohorte de este programa de maestría. Por favor, revise su plataforma de admisión posgrado."}), content_type="application/json")
                        else:
                            # valida ya está graduado en la maestria
                            if nomcarrera.malla().tiene_itinerario_malla_especialidad():
                                if Graduado.objects.filter(status=True, inscripcion__persona=postulante, inscripcion__carrera=nomcarrera, inscripcion__itinerario=itinerario).exists():
                                    raise NameError(u"Usted ya se encuentra graduado en la maestría y mención seleccionada")

                                if InscripcionCohorte.objects.filter(inscripcionaspirante__persona=postulante, cohortes__maestriaadmision__carrera=nomcarrera, activo=True, status=True, itinerario=itinerario).exists():
                                    obtenerinscripcion = InscripcionCohorte.objects.filter(inscripcionaspirante__persona=postulante,
                                                                      cohortes__maestriaadmision__carrera=nomcarrera,
                                                                      activo=True, status=True, itinerario=itinerario)[0]
                                    raise NameError(u"Usted ya se encuentra registrado, en la cohorte %s. Un asesor/a lo contactará en el menor tiempo posible, revise su correo electrónico para más información." % (obtenerinscripcion.cohortes))
                            else:
                                if Graduado.objects.filter(status=True, inscripcion__persona=postulante, inscripcion__carrera=nomcarrera).exists():
                                    raise NameError("Usted ya se encuentra graduado en la maestría seleccionada")

                                if InscripcionCohorte.objects.filter(inscripcionaspirante__persona=postulante, cohortes__maestriaadmision__carrera=nomcarrera, activo=True, status=True).exists():
                                    obtenerinscripcion = InscripcionCohorte.objects.filter(inscripcionaspirante__persona=postulante,
                                                                      cohortes__maestriaadmision__carrera=nomcarrera,
                                                                      activo=True, status=True)[0]
                                    raise NameError(u"Usted ya se encuentra registrado, en la cohorte %s. Un asesor/a lo contactará en el menor tiempo posible, revise su correo electrónico para más información." % (obtenerinscripcion.cohortes))

                            tiene_postulaciones_con_matricula = False
                            tiene_postulaciones_validas = False
                            inscripcionesenotracohortes=InscripcionCohorte.objects.filter(inscripcionaspirante__persona=postulante,
                                                                              activo=True,
                                                                              status=True).exclude(cohortes__maestriaadmision__carrera=nomcarrera)
                            if inscripcionesenotracohortes.values('id').exists():
                                tiene_postulaciones_validas = True
                                for otracohorte in inscripcionesenotracohortes:
                                    if otracohorte.matricula_activa_cohorte() == True:
                                        tiene_postulaciones_con_matricula = True
                                        break
                            lista = []
                            if postulante.emailinst:
                                lista.append(postulante.emailinst)
                            if postulante.email:
                                lista.append(postulante.email)
                                if not postulante.usuario:
                                    nomusername = calculate_username(postulante)
                                    generar_usuario_admision(postulante, nomusername, 199)
                                else:
                                    nomusername = postulante.usuario.username
                                if not postulante.emailinst:
                                    postulante.emailinst = nomusername + '@unemi.edu.ec'
                                postulante.save()
                                if not InscripcionAspirante.objects.filter(persona=postulante, status=True).exists():
                                    aspirante = InscripcionAspirante(persona=postulante)
                                    aspirante.save(request)
                                else:
                                    aspirante = InscripcionAspirante.objects.filter(persona=postulante, status=True)[0]
                                if not PerfilUsuario.objects.filter(persona=postulante, inscripcionaspirante=aspirante).exists():
                                    postulante.crear_perfil(inscripcionaspirante=aspirante)
                                postulante.mi_perfil()
                                if CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True).exists():
                                    cohortemaestria = CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True)[0]
                                    if nomcarrera.malla():
                                        if nomcarrera.malla().tiene_itinerario_malla_especialidad():
                                            if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante, cohortes=cohortemaestria, tipobeca_id=tipobeca,
                                                                                        # tiulacionaspirante_id=idtitulo,
                                                                                        # cantexperiencia=cantexperiencia,
                                                                                        formapagopac_id=1,
                                                                                        contactomaestria=tipoconta, itinerario=request.POST['itinerario'],
                                                                                        canal_id=canal,
                                                                                        leaddezona=zona,
                                                                                        convenio_id=convenio)
                                                inscripcioncohorte.save(request)
                                                asesorconvenio = False
                                                if inscripcioncohorte.convenio:
                                                    asesorconvenio = inscripcioncohorte.asignar_asesor_convenio()
                                                if not asesorconvenio:
                                                    inscripcioncohorte.reservar_lead_territorio()
                                                    inscripcioncohorte.asignar_mismo_asesor()
                                                # inscripcioncohorte.reservar_lead_territorio()
                                                # inscripcioncohorte.asignar_mismo_asesor()

                                                if tiene_postulaciones_con_matricula == True or tiene_postulaciones_validas == True:
                                                    inscripcioncohorte.doblepostulacion = True
                                                    inscripcioncohorte.save(request)
                                        else:
                                            if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante, cohortes=cohortemaestria, tipobeca_id=tipobeca,
                                                                                        # tiulacionaspirante_id=idtitulo,
                                                                                        # cantexperiencia=cantexperiencia,
                                                                                        formapagopac_id=1, contactomaestria=tipoconta, canal_id=canal, leaddezona=zona,
                                                                                        convenio_id=convenio)
                                                inscripcioncohorte.save(request)
                                                asesorconvenio = False
                                                if inscripcioncohorte.convenio:
                                                    asesorconvenio = inscripcioncohorte.asignar_asesor_convenio()
                                                if not asesorconvenio:
                                                    inscripcioncohorte.reservar_lead_territorio()
                                                    inscripcioncohorte.asignar_mismo_asesor()
                                                # inscripcioncohorte.reservar_lead_territorio()
                                                # inscripcioncohorte.asignar_mismo_asesor()

                                                if tiene_postulaciones_con_matricula == True or tiene_postulaciones_validas == True:
                                                    inscripcioncohorte.doblepostulacion = True
                                                    inscripcioncohorte.save(request)
                                    else:
                                        if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                            inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante, cohortes=cohortemaestria, tipobeca_id=tipobeca,
                                                                                    # tiulacionaspirante_id=idtitulo,
                                                                                    #     cantexperiencia=cantexperiencia,
                                                                                        formapagopac_id=1, contactomaestria=tipoconta, canal_id=canal, leaddezona=zona,
                                                                                    convenio_id=convenio)
                                            inscripcioncohorte.save(request)
                                            asesorconvenio = False
                                            if inscripcioncohorte.convenio:
                                                asesorconvenio = inscripcioncohorte.asignar_asesor_convenio()
                                            if not asesorconvenio:
                                                inscripcioncohorte.reservar_lead_territorio()
                                                inscripcioncohorte.asignar_mismo_asesor()
                                            # inscripcioncohorte.reservar_lead_territorio()
                                            # inscripcioncohorte.asignar_mismo_asesor()

                                            if tiene_postulaciones_con_matricula == True or tiene_postulaciones_validas == True:
                                                inscripcioncohorte.doblepostulacion = True
                                                inscripcioncohorte.save(request)
                                if postulante.cedula:
                                    clavepostulante = postulante.cedula.strip()
                                elif postulante.pasaporte:
                                    clavepostulante = postulante.pasaporte.strip()
                                resetear_clavepostulante(postulante)

                                if postulante.es_administrativo() and postulante.es_personalactivo():
                                    validapersonalinterno(postulante, idcarrera, hoy, request, lista, nomcarrera, tipobeca, tipoconta, itinerario, canal)
                                    # return HttpResponse(json.dumps({"result": "ok", "mensaje": "Usuario ya pre inscrito, favor acceder con las mismas credenciales del SGA o SAGEST a https://admisionposgrado.unemi.edu.ec/loginposgrado <a class='btn btn-success' href='https://admisionposgrado.unemi.edu.ec/loginposgrado' target='_blank'><i class='fa fa-arrow-right'></i> Ingresar</a> "}), content_type="application/json")
                                    return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")
                                if postulante.es_profesor() and postulante.es_personalactivo():
                                    validapersonalinterno(postulante, idcarrera, hoy, request, lista, nomcarrera, tipobeca, tipoconta, itinerario, canal)
                                    return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")

                                validapersonal(aspirante, idcarrera, lista, nomcarrera, postulante.usuario.username, clavepostulante, itinerario, canal)
                                return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")
                            if postulante.es_estudiante() and not postulante.es_personalactivo():
                                if not InscripcionAspirante.objects.filter(persona=postulante):
                                    nomusername = postulante.usuario.username
                                    postulante.email = f.cleaned_data['email']
                                    postulante.save()
                                    aspirante = InscripcionAspirante(persona=postulante)
                                    aspirante.save()
                                    if CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True).exists():
                                        cohortemaestria = CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True)[0]
                                        if nomcarrera.malla():
                                            if nomcarrera.malla().tiene_itinerario_malla_especialidad():
                                                if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                    inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                            cohortes=cohortemaestria,
                                                                                            tipobeca_id=tipobeca,
                                                                                            contactomaestria=tipoconta,
                                                                                            # tiulacionaspirante_id=idtitulo,
                                                                                            # cantexperiencia=cantexperiencia,
                                                                                            formapagopac_id=1,
                                                                                            itinerario=request.POST['itinerario'],
                                                                                            canal_id=canal,
                                                                                            leaddezona=zona,
                                                                                            convenio = convenio)
                                                    inscripcioncohorte.save(request)
                                                    asesorconvenio = False
                                                    if inscripcioncohorte.convenio:
                                                        asesorconvenio = inscripcioncohorte.asignar_asesor_convenio()
                                                    if not asesorconvenio:
                                                        inscripcioncohorte.reservar_lead_territorio()
                                                        inscripcioncohorte.asignar_mismo_asesor()
                                                    # inscripcioncohorte.reservar_lead_territorio()
                                                    # inscripcioncohorte.asignar_mismo_asesor()

                                                    if tiene_postulaciones_con_matricula == True or tiene_postulaciones_validas == True:
                                                        inscripcioncohorte.doblepostulacion = True
                                                        inscripcioncohorte.save(request)
                                            else:
                                                if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                    inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                            cohortes=cohortemaestria,
                                                                                            tipobeca_id=tipobeca,
                                                                                            # tiulacionaspirante_id=idtitulo,
                                                                                            # cantexperiencia=cantexperiencia,
                                                                                            formapagopac_id=1,
                                                                                            contactomaestria=tipoconta,
                                                                                            canal_id=canal,
                                                                                            leaddezona=zona,
                                                                                            convenio = convenio)
                                                    inscripcioncohorte.save(request)
                                                    asesorconvenio = False
                                                    if inscripcioncohorte.convenio:
                                                        asesorconvenio = inscripcioncohorte.asignar_asesor_convenio()
                                                    if not asesorconvenio:
                                                        inscripcioncohorte.reservar_lead_territorio()
                                                        inscripcioncohorte.asignar_mismo_asesor()
                                                    # inscripcioncohorte.reservar_lead_territorio()
                                                    # inscripcioncohorte.asignar_mismo_asesor()

                                                    if tiene_postulaciones_con_matricula == True or tiene_postulaciones_validas == True:
                                                        inscripcioncohorte.doblepostulacion = True
                                                        inscripcioncohorte.save(request)
                                        else:
                                            if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                        cohortes=cohortemaestria,
                                                                                        tipobeca_id=tipobeca,
                                                                                        # tiulacionaspirante_id=idtitulo,
                                                                                        # cantexperiencia=cantexperiencia,
                                                                                        formapagopac_id=1,
                                                                                        contactomaestria=tipoconta,
                                                                                        canal_id=canal,
                                                                                        leaddezona=zona,
                                                                                        convenio = convenio)
                                                inscripcioncohorte.save(request)
                                                asesorconvenio = False
                                                if inscripcioncohorte.convenio:
                                                    asesorconvenio = inscripcioncohorte.asignar_asesor_convenio()
                                                if not asesorconvenio:
                                                    inscripcioncohorte.reservar_lead_territorio()
                                                    inscripcioncohorte.asignar_mismo_asesor()
                                                # inscripcioncohorte.reservar_lead_territorio()
                                                # inscripcioncohorte.asignar_mismo_asesor()

                                                if tiene_postulaciones_con_matricula == True or tiene_postulaciones_validas == True:
                                                    inscripcioncohorte.doblepostulacion = True
                                                    inscripcioncohorte.save(request)
                                    postulante.crear_perfil(inscripcionaspirante=aspirante)
                                    postulante.mi_perfil()
                                    usuario = User.objects.get(pk=postulante.usuario.id)
                                    g = Group.objects.get(pk=199)
                                    g.user_set.add(usuario)
                                    g.save()
                                    resetear_clavepostulante(postulante)
                                    postulante.emailinst = postulante.usuario.username + '@unemi.edu.ec'
                                    postulante.save()
                                    if postulante.cedula:
                                        clavepostulante = postulante.cedula.strip()
                                    elif postulante.pasaporte:
                                        clavepostulante = postulante.pasaporte.strip()
                                    validapersonal(aspirante, idcarrera, lista, nomcarrera, postulante.usuario.username, postulante.identificacion(), itinerario, canal)
                                    # return HttpResponse(json.dumps({"result": "ok", "mensaje": "Usuario ya pre inscrito, te hemos enviado un email con tu usuario y clave para poder acceder a https://admisionposgrado.unemi.edu.ec/loginposgrado <a class='btn btn-success' href='https://admisionposgrado.unemi.edu.ec/loginposgrado' target='_blank'><i class='fa fa-arrow-right'></i> Ingresar</a> \n usuario:"+ postulante.usuario.username +" \n clave: " + clavepostulante + ""}), content_type="application/json")
                                    return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")
                                else:
                                    aspirante = InscripcionAspirante.objects.filter(persona=postulante, status=True)[0]
                                    if CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True).exists():
                                        cohortemaestria = CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True)[0]
                                        if nomcarrera.malla():
                                            if nomcarrera.malla().tiene_itinerario_malla_especialidad():
                                                if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                    inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                            cohortes=cohortemaestria,
                                                                                            tipobeca_id=tipobeca,
                                                                                            contactomaestria=tipoconta,
                                                                                            # tiulacionaspirante_id=idtitulo,
                                                                                            # cantexperiencia=cantexperiencia,
                                                                                            formapagopac_id=1,
                                                                                            itinerario=request.POST['itinerario'],
                                                                                            canal_id=canal,
                                                                                            leaddezona=zona,
                                                                                            convenio_id=convenio)
                                                    inscripcioncohorte.save(request)
                                                    asesorconvenio = False
                                                    if inscripcioncohorte.convenio:
                                                        asesorconvenio = inscripcioncohorte.asignar_asesor_convenio()
                                                    if not asesorconvenio:
                                                        inscripcioncohorte.reservar_lead_territorio()
                                                        inscripcioncohorte.asignar_mismo_asesor()
                                                    # inscripcioncohorte.reservar_lead_territorio()
                                                    # inscripcioncohorte.asignar_mismo_asesor()

                                                    if tiene_postulaciones_con_matricula == True or tiene_postulaciones_validas == True:
                                                        inscripcioncohorte.doblepostulacion = True
                                                        inscripcioncohorte.save(request)
                                            else:
                                                if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                    inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                            cohortes=cohortemaestria,
                                                                                            tipobeca_id=tipobeca,
                                                                                            # tiulacionaspirante_id=idtitulo,
                                                                                            # cantexperiencia=cantexperiencia,
                                                                                            formapagopac_id=1,
                                                                                            contactomaestria=tipoconta,
                                                                                            canal_id=canal,
                                                                                            leaddezona=zona,
                                                                                            convenio_id=convenio)
                                                    inscripcioncohorte.save(request)
                                                    asesorconvenio = False
                                                    if inscripcioncohorte.convenio:
                                                        asesorconvenio = inscripcioncohorte.asignar_asesor_convenio()
                                                    if not asesorconvenio:
                                                        inscripcioncohorte.reservar_lead_territorio()
                                                        inscripcioncohorte.asignar_mismo_asesor()
                                                    # inscripcioncohorte.reservar_lead_territorio()
                                                    # inscripcioncohorte.asignar_mismo_asesor()

                                                    if tiene_postulaciones_con_matricula == True or tiene_postulaciones_validas == True:
                                                        inscripcioncohorte.doblepostulacion = True
                                                        inscripcioncohorte.save(request)
                                        else:
                                            if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                        cohortes=cohortemaestria,
                                                                                        tipobeca_id=tipobeca,
                                                                                        # tiulacionaspirante_id=idtitulo,
                                                                                        # cantexperiencia=cantexperiencia,
                                                                                        formapagopac_id=1,
                                                                                        contactomaestria=tipoconta,
                                                                                        canal_id=canal,
                                                                                        leaddezona=zona,
                                                                                        convenio_id=convenio)
                                                inscripcioncohorte.save(request)
                                                asesorconvenio = False
                                                if inscripcioncohorte.convenio:
                                                    asesorconvenio = inscripcioncohorte.asignar_asesor_convenio()
                                                if not asesorconvenio:
                                                    inscripcioncohorte.reservar_lead_territorio()
                                                    inscripcioncohorte.asignar_mismo_asesor()
                                                # inscripcioncohorte.reservar_lead_territorio()
                                                # inscripcioncohorte.asignar_mismo_asesor()

                                                if tiene_postulaciones_con_matricula == True or tiene_postulaciones_validas == True:
                                                    inscripcioncohorte.doblepostulacion = True
                                                    inscripcioncohorte.save(request)

                                    nomusername = postulante.usuario.username
                                    postulante.email = f.cleaned_data['email']
                                    postulante.save()
                                    resetear_clavepostulante(postulante)
                                    if postulante.cedula:
                                        clavepostulante = postulante.cedula.strip()
                                    elif postulante.pasaporte:
                                        clavepostulante = postulante.pasaporte.strip()
                                    validapersonal(aspirante, idcarrera, lista, nomcarrera, postulante.usuario.username, clavepostulante, itinerario, canal)
                                    # return HttpResponse(json.dumps({"result": "ok", "mensaje": "Usuario ya pre inscrito, te hemos enviado un email con tu usuario y clave para poder acceder a https://admisionposgrado.unemi.edu.ec/loginposgrado <a class='btn btn-success' href='https://admisionposgrado.unemi.edu.ec/loginposgrado' target='_blank'><i class='fa fa-arrow-right'></i> Ingresar</a> \n usuario:"+ postulante.usuario.username +" \n clave: " + clavepostulante + ""}), content_type="application/json")
                                    return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")
                                validapersonal(aspirante, idcarrera, lista, nomcarrera, postulante.usuario.username, postulante.identificacion(), itinerario, canal)
                            if postulante.externo_set.filter(status=True) and not postulante.es_personalactivo():
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
                                    if CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True).exists():
                                        cohortemaestria = CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True)[0]
                                        if nomcarrera.malla():
                                            if nomcarrera.malla().tiene_itinerario_malla_especialidad():
                                                if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                    inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                            cohortes=cohortemaestria,
                                                                                            tipobeca_id=tipobeca,
                                                                                            contactomaestria=tipoconta,
                                                                                            # tiulacionaspirante_id=idtitulo,
                                                                                            # cantexperiencia=cantexperiencia,
                                                                                            formapagopac_id=1,
                                                                                            itinerario=request.POST['itinerario'],
                                                                                            canal_id=canal,
                                                                                            leaddezona=zona,
                                                                                            convenio = convenio)
                                                    inscripcioncohorte.save(request)
                                                    asesorconvenio = False
                                                    if inscripcioncohorte.convenio:
                                                        asesorconvenio = inscripcioncohorte.asignar_asesor_convenio()
                                                    if not asesorconvenio:
                                                        inscripcioncohorte.reservar_lead_territorio()
                                                        inscripcioncohorte.asignar_mismo_asesor()
                                                    # inscripcioncohorte.reservar_lead_territorio()
                                                    # inscripcioncohorte.asignar_mismo_asesor()

                                                    if tiene_postulaciones_con_matricula == True or tiene_postulaciones_validas == True:
                                                        inscripcioncohorte.doblepostulacion = True
                                                        inscripcioncohorte.save(request)
                                            else:
                                                if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                    inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                            cohortes=cohortemaestria,
                                                                                            tipobeca_id=tipobeca,
                                                                                            # tiulacionaspirante_id=idtitulo,
                                                                                            # cantexperiencia=cantexperiencia,
                                                                                            formapagopac_id=1,
                                                                                            contactomaestria=tipoconta,
                                                                                            canal_id=canal,
                                                                                            leaddezona=zona,
                                                                                            convenio_id=convenio)
                                                    inscripcioncohorte.save(request)
                                                    asesorconvenio = False
                                                    if inscripcioncohorte.convenio:
                                                        asesorconvenio = inscripcioncohorte.asignar_asesor_convenio()
                                                    if not asesorconvenio:
                                                        inscripcioncohorte.reservar_lead_territorio()
                                                        inscripcioncohorte.asignar_mismo_asesor()
                                                    # inscripcioncohorte.reservar_lead_territorio()
                                                    # inscripcioncohorte.asignar_mismo_asesor()

                                                    if tiene_postulaciones_con_matricula == True or tiene_postulaciones_validas == True:
                                                        inscripcioncohorte.doblepostulacion = True
                                                        inscripcioncohorte.save(request)
                                        else:
                                            if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                        cohortes=cohortemaestria,
                                                                                        tipobeca_id=tipobeca,
                                                                                        # tiulacionaspirante_id=idtitulo,
                                                                                        # cantexperiencia=cantexperiencia,
                                                                                        formapagopac_id=1,
                                                                                        contactomaestria=tipoconta,
                                                                                        canal_id=canal,
                                                                                        leaddezona=zona,
                                                                                        convenio = convenio)
                                                inscripcioncohorte.save(request)
                                                asesorconvenio = False
                                                if inscripcioncohorte.convenio:
                                                    asesorconvenio = inscripcioncohorte.asignar_asesor_convenio()
                                                if not asesorconvenio:
                                                    inscripcioncohorte.reservar_lead_territorio()
                                                    inscripcioncohorte.asignar_mismo_asesor()
                                                # inscripcioncohorte.reservar_lead_territorio()
                                                # inscripcioncohorte.asignar_mismo_asesor()

                                                if tiene_postulaciones_con_matricula == True or tiene_postulaciones_validas == True:
                                                    inscripcioncohorte.doblepostulacion = True
                                                    inscripcioncohorte.save(request)

                                    postulante.crear_perfil(inscripcionaspirante=aspirante)
                                    postulante.mi_perfil()
                                    usuario = User.objects.get(pk=postulante.usuario.id)
                                    g = Group.objects.get(pk=199)
                                    g.user_set.add(usuario)
                                    g.save()
                                    resetear_clavepostulante(postulante)
                                    postulante.emailinst = postulante.usuario.username + '@unemi.edu.ec'
                                    postulante.save()
                                    lista = []
                                    if postulante.emailinst:
                                        lista.append(postulante.emailinst)
                                    if postulante.email:
                                        lista.append(postulante.email)
                                    if postulante.cedula:
                                        clavepostulante = postulante.cedula.strip()
                                    elif postulante.pasaporte:
                                        clavepostulante = postulante.pasaporte.strip()
                                    validapersonal(aspirante, idcarrera, lista, nomcarrera, postulante.usuario.username, clavepostulante, itinerario, canal)
                                    # send_html_mail("Registro exitoso Admision-UNEMI.", "emails/registroexitoadmisionposgrado.html", {'sistema': u'Admision - UNEMI', 'preinscrito': postulante,'usuario': postulante.usuario.username,'clave': postulante.identificacion(), 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'os': ops, 'cookies': cookies,'screensize': screensize, 't': miinstitucion()}, postulante.emailpersonal(),  [], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])
                                    return HttpResponse(json.dumps({"result": "ok", "usu": nomusername}), content_type="application/json")
                            if postulante.inscripcionaspirante_set.filter(status=True) and not postulante.es_personalactivo():
                                aspirante = InscripcionAspirante.objects.filter(persona=postulante, status=True)[0]
                                if CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy,  activo=True, status=True).exists():
                                    cohortemaestria = CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True)[0]
                                    if nomcarrera.malla():
                                        if nomcarrera.malla().tiene_itinerario_malla_especialidad():
                                            if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                        cohortes=cohortemaestria,
                                                                                        tipobeca_id=tipobeca,
                                                                                        contactomaestria=tipoconta,
                                                                                        # tiulacionaspirante_id=idtitulo,
                                                                                        # cantexperiencia=cantexperiencia,
                                                                                        formapagopac_id=1,
                                                                                        itinerario=request.POST['itinerario'],
                                                                                        canal_id=canal,
                                                                                        leaddezona=zona,
                                                                                        convenio = convenio)
                                                inscripcioncohorte.save(request)
                                                asesorconvenio = False
                                                if inscripcioncohorte.convenio:
                                                    asesorconvenio = inscripcioncohorte.asignar_asesor_convenio()
                                                if not asesorconvenio:
                                                    inscripcioncohorte.reservar_lead_territorio()
                                                    inscripcioncohorte.asignar_mismo_asesor()
                                                # inscripcioncohorte.reservar_lead_territorio()
                                                # inscripcioncohorte.asignar_mismo_asesor()

                                                if tiene_postulaciones_con_matricula == True or tiene_postulaciones_validas == True:
                                                    inscripcioncohorte.doblepostulacion = True
                                                    inscripcioncohorte.save(request)
                                        else:
                                            if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                                inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                        cohortes=cohortemaestria,
                                                                                        tipobeca_id=tipobeca,
                                                                                        # tiulacionaspirante_id=idtitulo,
                                                                                        # cantexperiencia=cantexperiencia,
                                                                                        formapagopac_id=1,
                                                                                        contactomaestria=tipoconta,
                                                                                        canal_id=canal,
                                                                                        leaddezona=zona,
                                                                                        convenio_id=convenio)
                                                inscripcioncohorte.save(request)
                                                asesorconvenio = False
                                                if inscripcioncohorte.convenio:
                                                    asesorconvenio = inscripcioncohorte.asignar_asesor_convenio()
                                                if not asesorconvenio:
                                                    inscripcioncohorte.reservar_lead_territorio()
                                                    inscripcioncohorte.asignar_mismo_asesor()
                                                # inscripcioncohorte.reservar_lead_territorio()
                                                # inscripcioncohorte.asignar_mismo_asesor()

                                                if tiene_postulaciones_con_matricula == True or tiene_postulaciones_validas == True:
                                                    inscripcioncohorte.doblepostulacion = True
                                                    inscripcioncohorte.save(request)
                                    else:
                                        if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                                            inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                                                    cohortes=cohortemaestria,
                                                                                    tipobeca_id=tipobeca,
                                                                                    # tiulacionaspirante_id=idtitulo,
                                                                                    # cantexperiencia=cantexperiencia,
                                                                                    formapagopac_id=1,
                                                                                    contactomaestria=tipoconta,
                                                                                    canal_id=canal,
                                                                                    leaddezona=zona,
                                                                                    convenio_id=convenio)
                                            inscripcioncohorte.save(request)
                                            asesorconvenio = False
                                            if inscripcioncohorte.convenio:
                                                asesorconvenio = inscripcioncohorte.asignar_asesor_convenio()
                                            if not asesorconvenio:
                                                inscripcioncohorte.reservar_lead_territorio()
                                                inscripcioncohorte.asignar_mismo_asesor()
                                            # inscripcioncohorte.reservar_lead_territorio()
                                            # inscripcioncohorte.asignar_mismo_asesor()

                                            if tiene_postulaciones_con_matricula == True or tiene_postulaciones_validas == True:
                                                inscripcioncohorte.doblepostulacion = True
                                                inscripcioncohorte.save(request)

                                if not postulante.emailinst:
                                    resetear_clavepostulante(postulante)
                                    postulante.emailinst = postulante.usuario.username + '@unemi.edu.ec'
                                    postulante.save()
                                lista = []
                                if postulante.emailinst:
                                    lista.append(postulante.emailinst)
                                if postulante.email:
                                    lista.append(postulante.email)
                                if postulante.cedula:
                                    clavepostulante = postulante.cedula.strip()
                                elif postulante.pasaporte:
                                    clavepostulante = postulante.pasaporte.strip()
                                resetear_clavepostulante(postulante)
                                validapersonal(aspirante, idcarrera, lista, nomcarrera, postulante.usuario.username, clavepostulante, itinerario, canal)
                                # return HttpResponse(json.dumps({"result": "ok", "mensaje": "Usuario ya pre inscrito, te hemos enviado un email con tu usuario y clave para poder acceder a https://admisionposgrado.unemi.edu.ec/loginposgrado <a class='btn btn-success' href='https://admisionposgrado.unemi.edu.ec/loginposgrado' target='_blank'><i class='fa fa-arrow-right'></i> Ingresar</a> \n usuario:"+ postulante.usuario.username +" \n clave: " + clavepostulante + "  "}), content_type="application/json")
                                return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")
                                # return HttpResponse(json.dumps({"result": "bad", "mensaje": "Persona ya existe, favor ingresar con su usuario y clave.: "}), content_type="application/json")
                            if postulante.es_administrativo() and postulante.es_personalactivo():
                                validapersonalinterno(postulante,idcarrera,hoy,request, lista, nomcarrera,tipobeca, tipoconta, itinerario, canal)
                                return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")
                            if postulante.es_profesor() and postulante.es_personalactivo():
                                validapersonalinterno(postulante,idcarrera,hoy,request, lista, nomcarrera,tipobeca, tipoconta, itinerario, canal)
                                return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")
                            return HttpResponse(json.dumps({"result": "bad", "mensaje": "Error al guardar.: "}), content_type="application/json")
                return HttpResponse(json.dumps({"result": "ok", "mensaje": "Gracias por su registro, revise el correo electrónico para más información, pronto un asesor/a se contactará."}), content_type="application/json")
        except Exception as ex:
            transaction.set_rollback(True)
            return HttpResponse(json.dumps({"result": "bad", "mensaje": "%s"%ex}), content_type="application/json")



def validapersonalinterno(postulante, idcarrera, hoy, request, lista, nomcarrera,tipobeca, tipoconta, itinerario, canal):
    arregloemail = [23, 24, 25, 26, 27, 28]
    correo = []
    correo.append(postulante.email)
    correo.append(postulante.emailinst)
    emailaleatorio = random.choice(arregloemail)
    maestria = MaestriasAdmision.objects.get(status=True, carrera=idcarrera)
    if not InscripcionAspirante.objects.filter(persona=postulante, status=True).exists():
        aspirante = InscripcionAspirante(persona=postulante)
        aspirante.save()
    else:
        aspirante = InscripcionAspirante.objects.filter(persona=postulante, status=True)[0]
    if CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True).exists():
        cohortemaestria = CohorteMaestria.objects.filter(maestriaadmision__carrera=idcarrera, fechainicioinsp__lte=hoy, fechafininsp__gte=hoy, activo=True, status=True)[0]
        if nomcarrera.malla():
            if nomcarrera.malla().tiene_itinerario_malla_especialidad() == True:
                if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                    inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                            cohortes=cohortemaestria,
                                                            tipobeca_id=tipobeca,
                                                            contactomaestria=tipoconta,
                                                            # tiulacionaspirante_id=idtitulo,
                                                            # cantexperiencia=cantexperiencia,
                                                            formapagopac_id=1,
                                                            itinerario=itinerario,
                                                            canal_id=canal)
                    inscripcioncohorte.save(request)
            else:
                if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                    inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                            cohortes=cohortemaestria,
                                                            tipobeca_id=tipobeca,
                                                            # tiulacionaspirante_id=idtitulo,
                                                            # cantexperiencia=cantexperiencia,
                                                            formapagopac_id=1,
                                                            contactomaestria=tipoconta,
                                                            canal_id=canal)
                    inscripcioncohorte.save(request)
        else:
            if not InscripcionCohorte.objects.filter(inscripcionaspirante=aspirante, cohortes=cohortemaestria, status=True).exists():
                inscripcioncohorte = InscripcionCohorte(inscripcionaspirante=aspirante,
                                                        cohortes=cohortemaestria,
                                                        tipobeca_id=tipobeca,
                                                        # tiulacionaspirante_id=idtitulo,
                                                        # cantexperiencia=cantexperiencia,
                                                        formapagopac_id=1,
                                                        contactomaestria=tipoconta,
                                                        canal_id=canal)
                inscripcioncohorte.save(request)
    if not Group.objects.filter(pk=199, user=postulante.usuario):
        usuario = User.objects.get(pk=postulante.usuario.id)
        g = Group.objects.get(pk=199)
        g.user_set.add(usuario)
        g.save()
    archivoadjunto = ''
    banneradjunto = ''
    if FormatoCarreraIpec.objects.filter(carrera_id=idcarrera, status=True):
        formatocorreo = FormatoCarreraIpec.objects.filter(carrera_id=idcarrera, status=True)[0]
        archivoadjunto = formatocorreo.archivo
        banneradjunto = formatocorreo.banner
        if formatocorreo.correomaestria:
            lista.append(formatocorreo.correomaestria)
    asunto = u"Registro exitoso para admisión de " + nomcarrera.nombre

    mencion=''
    if nomcarrera.malla().tiene_itinerario_malla_especialidad() == True:
        iti = ItinerarioMallaEspecilidad.objects.get(status=True, malla=nomcarrera.malla(), itinerario=itinerario)
        mencion = iti.nombre

    if archivoadjunto:
        # send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html", {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante, 'formato': banneradjunto}, lista, [], [archivoadjunto], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])
        send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html",
                       {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante, 'formato': banneradjunto,
                        'nomcarrera': nomcarrera.nombre[11:] if nomcarrera.nombre[:6] == 'MAESTR' else nomcarrera.nombre,
                        'mencion':mencion},
                       correo, [], [archivoadjunto],
                       cuenta=CUENTAS_CORREOS[18][1])
    else:
        # send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html", {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante, 'formato': banneradjunto}, lista, [], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])
        send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html",
                       {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante, 'formato': banneradjunto,
                        'nomcarrera': nomcarrera.nombre[11:] if nomcarrera.nombre[:6] == 'MAESTR' else nomcarrera.nombre,
                        'mencion':mencion},
                       correo, [],
                       cuenta=CUENTAS_CORREOS[18][1])
    # send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html", {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante, 'formato': banneradjunto}, lista, [], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])
    # send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html", {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante, 'formato': banneradjunto}, lista, [], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])

    return aspirante

def validapersonal(aspirante, idcarrera, lista, nomcarrera, userpostulante, clavepostulante, itinerario, canal):
    archivoadjunto = ''
    banneradjunto = ''
    correo = []
    maestria = MaestriasAdmision.objects.get(status=True, carrera=idcarrera)
    if FormatoCarreraIpec.objects.filter(carrera_id=idcarrera, status=True):
        formatocorreo = FormatoCarreraIpec.objects.filter(carrera_id=idcarrera, status=True)[0]
        archivoadjunto = formatocorreo.archivo
        banneradjunto = formatocorreo.banner
        if formatocorreo.correomaestria:
            lista.append(formatocorreo.correomaestria)
    lista.append(conectar_cuenta(CUENTAS_CORREOS[18][1]))
    correo.append(aspirante.persona.email)
    correo.append(aspirante.persona.emailinst)
    arregloemail = [23, 24, 25, 26, 27, 28]
    emailaleatorio = random.choice(arregloemail)
    asunto = u"Registro exitoso para admisión de " + nomcarrera.nombre

    mencion=''
    if nomcarrera.malla().tiene_itinerario_malla_especialidad() == True:
        iti = ItinerarioMallaEspecilidad.objects.get(status=True, malla=nomcarrera.malla(), itinerario=itinerario)
        mencion = iti.nombre
    if archivoadjunto:
        # send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html", {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante, 'usuario': userpostulante, 'clave': clavepostulante, 'formato': banneradjunto}, lista, [], [archivoadjunto], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])
        send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html",
                       {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante, 'usuario': userpostulante, 'clave': clavepostulante, 'formato': banneradjunto,
                        'nomcarrera': nomcarrera.nombre[11:] if nomcarrera.nombre[:6] == 'MAESTR' else nomcarrera.nombre,
                        'mencion':mencion},
                       correo, [], [archivoadjunto],
                       cuenta=CUENTAS_CORREOS[18][1])
    else:
        # send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html", {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante,  'usuario': userpostulante, 'clave': clavepostulante, 'formato': banneradjunto}, lista, [], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])
        send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html",
                       {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante, 'usuario': userpostulante,
                        'clave': clavepostulante, 'formato': banneradjunto,
                        'nomcarrera': nomcarrera.nombre[11:] if nomcarrera.nombre[:6] == 'MAESTR' else nomcarrera.nombre,
                        'mencion':mencion},
                       correo, [],
                       cuenta=CUENTAS_CORREOS[18][1])
    # send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html", {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante,  'usuario': userpostulante, 'clave': clavepostulante, 'formato': banneradjunto}, lista, [], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])
    # send_html_mail(asunto, "emails/registroexitoadmisionposgrado.html", {'sistema': 'Posgrado UNEMI', 'preinscrito': aspirante,  'usuario': userpostulante, 'clave': clavepostulante, 'formato': banneradjunto}, lista, [], cuenta=variable_valor('CUENTAS_CORREOS')[emailaleatorio])
    return aspirante

def matricularposgrado(codigoinscripcion, idnivel, codigoperiodo,request):
    try:
        inscripcion = Inscripcion.objects.get(pk=int(codigoinscripcion))
        persona = inscripcion.persona
        periodo = Periodo.objects.get(pk=int(codigoperiodo))
        # cobro = request.POST['cobro']
        # regular o irregular
        # tipo_matricula_ri = request.POST['tipo_matricula']

        nivel = Nivel.objects.get(pk=idnivel)

        if not inscripcion.matriculado_periodo(nivel.periodo):
            with transaction.atomic():
                matricula = Matricula(inscripcion=inscripcion,
                                      nivel=nivel,
                                      pago=False,
                                      iece=False,
                                      becado=False,
                                      porcientobeca=0,
                                      fecha=datetime.now().date(),
                                      hora=datetime.now().time(),
                                      fechatope=fechatope(datetime.now().date()),
                                      termino=True,
                                      fechatermino=datetime.now())
                matricula.save(request)
                codigoitinerario = inscripcion.inscripcioncohorte_set.last().itinerario if inscripcion.inscripcioncohorte_set.last() else 0
                matricula.actualizar_horas_creditos()
                if not inscripcion.itinerario or inscripcion.itinerario < 1:
                    inscripcion.itinerario = codigoitinerario
                    inscripcion.save()
            with transaction.atomic():
                # if int(cobro) > 0:
                #     if matricula.inscripcion.mi_coordinacion().id != 9:
                #         matricula.agregacion_aux(request)
                matricula.actualiza_matricula()
                matricula.asigna_matricula_rubros()
                matricula.inscripcion.actualiza_estado_matricula()
                # matricula.grupo_socio_economico(tipo_matricula_ri)
                matricula.calcula_nivel()

            banneradjunto = archivoadjunto = ''
            if FormatoCarreraIpec.objects.filter(carrera_id=matricula.inscripcion.carrera.id,
                                                 status=True):
                formatocorreo = \
                FormatoCarreraIpec.objects.filter(carrera_id=matricula.inscripcion.carrera.id,
                                                  status=True)[0]
                archivoadjunto = formatocorreo.archivo
                banneradjunto = formatocorreo.banner

            mencion = ''
            if matricula.inscripcion.carrera.malla().tiene_itinerario_malla_especialidad() == True:
                iti = ItinerarioMallaEspecilidad.objects.get(status=True,
                                                             malla=matricula.inscripcion.carrera.malla(),
                                                             itinerario=matricula.inscripcion.itinerario)
                mencion = iti.nombre

            send_html_mail("Bienvenido", "emails/registrobienvenidomaestria.html",
                           {'sistema': u'BIENVENIDOS - UNEMI-POSGRADOS', 'fecha': datetime.now().date(),
                            'hora': datetime.now().time(), 't': miinstitucion(), 'formato': banneradjunto,
                            'matriculado': matricula,
                            'nomcarrera': matricula.inscripcion.carrera.nombre[11:] if matricula.inscripcion.carrera.nombre[:6] == 'MAESTR' else matricula.inscripcion.carrera.nombre,
                            'mencion':mencion},
                            matricula.inscripcion.persona.emailpersonal(), [],
                           cuenta=variable_valor('CUENTAS_CORREOS')[16])
            # return JsonResponse({"result": "ok"})
            return JsonResponse({"result": False}, safe=False)
        else:
            transaction.set_rollback(True)
            return JsonResponse({"result": "bad", "reload": True, "mensaje": u"Ya se encuentra matriculado."})
    except Exception as ex:
        transaction.set_rollback(True)
        return JsonResponse({"result": "bad", "reload": False, "mensaje": u"Hubieron errores en la matriculacion"})

def secuencia_contratopagare(request, anio):
    anioe = AnioEjercicio.objects.get(anioejercicio=anio)
    if not SecuenciaContratoPagare.objects.filter(anioejercicio=anioe).exists():
        secuencia = SecuenciaContratoPagare(anioejercicio=anioe)
        secuencia.save(request)
        return secuencia
    else:
        return SecuenciaContratoPagare.objects.filter(anioejercicio=anioe)[0]

def crear_inscripcion(request, insc):
    if not Inscripcion.objects.filter(persona=insc.inscripcionaspirante.persona, carrera_id=insc.cohortes.maestriaadmision.carrera.id).exists():
        carrera = insc.cohortes.maestriaadmision.carrera
        if insc.cohortes.periodoacademico:
            if insc.cohortes.periodoacademico.nivel_set.filter(nivellibrecoordinacion__coordinacion_id=7, modalidad=insc.cohortes.modalidad, status=True):
                nivel = insc.cohortes.periodoacademico.nivel_set.get(nivellibrecoordinacion__coordinacion_id=7, modalidad=insc.cohortes.modalidad, status=True)
                modalidad = nivel.modalidad
                sesion = nivel.sesion

                inscripcion = Inscripcion(persona=insc.inscripcionaspirante.persona,
                                          fecha=datetime.now().date(),
                                          carrera=carrera,
                                          modalidad=modalidad,
                                          sesion=sesion,
                                          sede_id=1,
                                          colegio='',
                                          aplica_b2=True,
                                          fechainicioprimernivel=datetime.now().date(),
                                          fechainiciocarrera=datetime.now().date())
                inscripcion.save(request)

                insc.inscripcion = inscripcion
                insc.save(request)

                insc.inscripcionaspirante.persona.crear_perfil(inscripcion=inscripcion)
                if PerfilUsuario.objects.values_list('id').filter(inscripcion=inscripcion, status=True).exists():
                    perfil = PerfilUsuario.objects.filter(inscripcion=inscripcion, status=True).last()
                    perfil.inscripcionprincipal = True
                    perfil.save(request)

                documentos = DocumentosDeInscripcion(inscripcion=inscripcion,
                                                     titulo=False,
                                                     acta=False,
                                                     cedula=False,
                                                     votacion=False,
                                                     actaconv=False,
                                                     partida_nac=False,
                                                     pre=False,
                                                     observaciones_pre='',
                                                     fotos=False)
                documentos.save()
                preguntasinscripcion = inscripcion.preguntas_inscripcion()
                inscripciontesdrive = InscripcionTesDrive(inscripcion=inscripcion,
                                                          licencia=False,
                                                          record=False,
                                                          certificado_tipo_sangre=False,
                                                          prueba_psicosensometrica=False,
                                                          certificado_estudios=False)
                inscripciontesdrive.save()
                inscripcion.malla_inscripcion()
                inscripcion.actualizar_nivel()
                if USA_TIPOS_INSCRIPCIONES:
                    inscripciontipoinscripcion = InscripcionTipoInscripcion(inscripcion=inscripcion, tipoinscripcion_id=TIPO_INSCRIPCION_INICIAL)
                    inscripciontipoinscripcion.save()
    if not insc.inscripcion:
        i = Inscripcion.objects.filter(persona=insc.inscripcionaspirante.persona, carrera_id=insc.cohortes.maestriaadmision.carrera.id).last()
        if i:
            insc.inscripcion = i
            insc.save(request)
