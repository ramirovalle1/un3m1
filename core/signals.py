from datetime import datetime

from django.contrib.auth import authenticate, logout, login
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.contrib import messages

from bd.models import TemplateBaseSetting, UserAccessSecurity, UserAccessSecurityType
from decorators import get_client_ip
from moodle.models import UserAuth
from settings import EMAIL_DOMAIN, DEBUG
from sga.funciones import loglogin, variable_valor
from sga.models import Persona, miinstitucion, CUENTAS_CORREOS
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache


@receiver(user_logged_in)
def handle_user_logged_in(sender, request, user, **kwargs):
    try:
        ahora = datetime.now()
        fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_cache = fecha_fin - ahora
        TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
        data = {}
        capippriva = ''

        if EMAIL_DOMAIN in request.META['HTTP_HOST']:
            if 'sga' not in request.META['HTTP_HOST']:
                if 'admisionposgrado' in request.META['HTTP_HOST']:
                    return False
                elif 'postulate' in request.META['HTTP_HOST']:
                    return False
                elif 'seleccionposgrado' in request.META['HTTP_HOST']:
                    return False
                elif 'empleo' in request.META['HTTP_HOST']:
                    return False

        if 'tipoentrada' in request.session:
            if 'POSTULATE' == request.session['tipoentrada']:
                return False
            elif 'POSGRADO' == request.session['tipoentrada']:
                return False
            elif 'POSTULACIONPOSGRADO' == request.session['tipoentrada']:
                return False
            elif 'EMPLEO' == request.session['tipoentrada']:
                return False
            elif 'EMPRESA' == request.session['tipoentrada']:
                return False

        ipvalidas = ['192.168.61.96', '192.168.61.97', '192.168.61.98', '192.168.61.99']
        client_address = get_client_ip(request)
        if 'login_manual' in request.session:
            return False
        if user is not None:
            if not user.is_active:
                loglogin(action_flag=2, action_app=1, ip_private=capippriva,
                         ip_public=client_address, browser='', ops='', cookies='',
                         screen_size='', user=user, change_message=u"Usuario no activo")
                logout(request)
                return False
            else:
                if (persona := Persona.objects.filter(usuario=user).first()) is not None:
                    if persona.tiene_perfil():
                        app = 'sga'
                        if persona.es_evaluador_externo_proyectos_investigacion():
                            app = 'investigacionevalproy'
                        perfiles = persona.mis_perfilesusuarios_app(app)
                        perfilprincipal = persona.perfilusuario_principal(perfiles, app)

                        if not perfilprincipal:
                            logout(request)
                            messages.error(request, 'No existe un perfiles para esta aplicacion.')
                            return False

                        request.session.set_expiry(240 * 60)
                        # login(request, user)
                        if not DEBUG:
                            eUserAccessSecurity = UserAccessSecurity.objects.none()
                            eUserAccessSecurityType = UserAccessSecurityType.objects.none()
                            if cache.has_key(f"user_access_security_{encrypt(user.id)}"):
                                eUserAccessSecurity = cache.get(f"user_access_security_{encrypt(user.id)}")
                            else:
                                eUserAccessSecurities = UserAccessSecurity.objects.filter(user=user, isActive=True)
                                if eUserAccessSecurities.values("id").exists():
                                    eUserAccessSecurity = eUserAccessSecurities.first()
                                cache.set(f"user_access_security_{encrypt(user.id)}", eUserAccessSecurity, TIEMPO_ENCACHE)
                            if eUserAccessSecurity:
                                if cache.has_key(f"user_access_security_type_{encrypt(user.id)}"):
                                    eUserAccessSecurityType = cache.get(f"user_access_security_type_{encrypt(user.id)}")
                                else:
                                    eUserAccessSecurityTypes = UserAccessSecurityType.objects.filter(user_access=eUserAccessSecurity, type=1, isActive=True)
                                    if eUserAccessSecurityTypes.values("id").exists():
                                        eUserAccessSecurityType = eUserAccessSecurityTypes.first()
                                    cache.set(f"user_access_security_type_{encrypt(user.id)}", eUserAccessSecurityType, TIEMPO_ENCACHE)
                            if eUserAccessSecurity and eUserAccessSecurityType:
                                request.session['validateTwoStepAccess'] = True
                                request.session['eUserAccessSecurity'] = eUserAccessSecurity
                                request.session['eUserAccessSecurityType'] = eUserAccessSecurityType
                        request.session['perfiles'] = perfiles
                        request.session['persona'] = persona
                        request.session['capippriva'] = capippriva
                        request.session['tiposistema'] = app
                        request.session['perfilprincipal'] = perfilprincipal
                        nombresistema = u'Sistema de Gestión Académica'
                        eTemplateBaseSetting = None
                        if (eTemplateBaseSetting := TemplateBaseSetting.objects.filter(status=True, app=1).first()) is not None:
                            # eTemplateBaseSetting = TemplateBaseSetting.objects.filter(status=True, app=1)[0]
                            nombresistema = eTemplateBaseSetting.name_system
                        request.session['eTemplateBaseSetting'] = eTemplateBaseSetting
                        request.session['nombresistema'] = nombresistema
                        loglogin(action_flag=1, action_app=1, ip_private=capippriva,
                                 ip_public=client_address, browser='', ops='', cookies='',
                                 screen_size='', user=user)
                        # log(u'Login con exito: %s - %s - %s - IPPU: %s - IPPR: %s' % (persona, browser, ops, client_address, capippriva), request, "add")
                        if persona.administrativo_activo() or persona.es_profesor() or persona.es_administrador():
                            if variable_valor('SEND_LOGIN_EMAIL_SGA') and not DEBUG:
                                send_html_mail("Login exitoso SGA.", "emails/loginexito.html", {'sistema': request.session['nombresistema'], 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': "", 'ip': client_address, 'ipvalida': capippriva, 'os': "", 'cookies': "", 'screensize': "", 't': miinstitucion()}, persona.emailinst, [], cuenta=CUENTAS_CORREOS[0][1])
    except Exception as ex:
        messages.error(request, f"{ex}")
        return False

