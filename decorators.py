# -*- coding: latin-1 -*-
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django_user_agents.utils import get_user_agent

from bd.funciones import generate_code
from bd.models import UserAccessSecurityDevice, UserAccessSecurityCode
from sagest.funciones import encrypt_id
from settings import ALLOWED_IPS_FOR_INHOUSE, ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID, DEBUG
from sga.funciones import log, variable_valor
from sga.models import Modulo, IpPermitidas, Notificacion
from datetime import datetime, timedelta
from sga.funciones import logvisita
from directivo.models import PersonaSancion
from sga.templatetags.sga_extras import encrypt


def localhost(f):
    """Requires that a view be invoked from localhost only."""

    def new_f(*args, **kwargs):
        request = args[0]
        if request.META["REMOTE_ADDR"] != "127.0.0.1":
             raise Exception("This URL is only invokable by localhost.")
        return f(*args, **kwargs)
    return new_f


def secure_action(request, permision):
    user = request.user
    if not user.has_perm(permision):
         raise NameError('Error')


def secure_module(f):

    def new_f(*args, **kwargs):
        request = args[0]
        if request.user.is_authenticated:
            try:
                if 'postulate' not in request.META['HTTP_HOST']:
                    site_maintenance = variable_valor('SITIO_MANTENIMIENTO')
                    if site_maintenance:
                        return HttpResponseRedirect("/logout")
                # SE AUMENTA LINEA DE CODIGO EN CASO DE NO ENCONTRAR LA SESIÓN POR ALGUN MOTIVO,
                # MATA LA SESIÓN AL MOMENTO DE LOGOUT
                if not 'perfilprincipal' in request.session:
                    return HttpResponseRedirect("/logout")

                p = request.session['perfilprincipal']
                app = request.session['tiposistema']
                # if p.es_empleador():  SE COMENTO PARA QUE EL EMPLEADOR INGRESE A UNEMI EMPRESAS
                #     if request.path == '/reportes' or request.path == '/bolsalaboral':
                #         if request.path == '/reportes' and 'action' in request.GET:
                #             pass
                #         else:
                #             return HttpResponseRedirect("/bolsalaboral")
                #     else:
                #         return HttpResponseRedirect("/bolsalaboral")

                if p.es_postulanteempleo():
                    if request.path == '/reportes':
                        if 'action' in request.GET:
                            pass
                        else:
                            return HttpResponseRedirect("/")
                #LINEA PARA POSTULATE
                if p.es_postulate():
                    if request.path == '/reportes':
                        if 'action' in request.GET:
                            pass
                        else:
                            return HttpResponseRedirect("/")
                #LINEA PARA POSTULATE
                if p.es_estudiante() or p.es_profesor():
                    if request.path == '/reportes':
                        if 'action' in request.GET:
                            pass
                        else:
                            return HttpResponseRedirect("/")

                if p.persona.necesita_cambiar_clave():
                    # Se amumento linea para el cambio de clave no se realice en la plataforma unemi empleo o unemi empresas
                    if p.es_empleador():
                        return HttpResponseRedirect('/empresa/pass')
                    if not p.es_postulanteempleo():
                        return HttpResponseRedirect('/pass')

                # SE AUMENTA LINEA DE CODIGO PARA SABER SI EXISTE MAS DE UN PATH SEPARADO POR "/"
                # EL PATH PRINCIPAL SIEMPRE SERA EL MODULO
                urlPath = None
                if '/' in request.path[1:]:
                    sp = request.path[1:].split('/')
                    urlPath = sp[0]
                else:
                    urlPath = request.path[1:]

                if len(urlPath) > 1:
                    if p.es_empleador() or p.es_estudiante() or p.es_inscripcionaspirante() or p.es_profesor() or p.es_administrativo() or p.es_postulate() or p.es_postulanteempleo():
                        if request.path == '/reportes' and 'action' in request.GET:
                            return f(request)
                    if p.es_estudiante():
                        g = [ALUMNOS_GROUP_ID]
                    elif p.es_profesor():
                        g = [PROFESORES_GROUP_ID]
                    else:
                        g = [x.id for x in p.persona.usuario.groups.exclude(id__in=[ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID])]
                    if Modulo.objects.filter(modulogrupo__grupos__id__in=g, url=urlPath, activo=True).exists():
                        logvisita(request, urlPath, g)
                        modulo = Modulo.objects.values("sga", "sagest", "posgrado", "api", "empleo", "empresa").filter(modulogrupo__grupos__id__in=g, url=urlPath, activo=True)[0]
                        if app == 'sga' and modulo.get("api"):
                            if p.es_estudiante():
                                if not DEBUG:
                                    if 'eTemplateBaseSetting' in request.session:
                                        eTemplateBaseSetting = request.session['eTemplateBaseSetting']
                                        if eTemplateBaseSetting and eTemplateBaseSetting.use_api:
                                            if 'connectionToken' in request.session:
                                                connectionToken = request.session['connectionToken']
                                                return redirect(f'{connectionToken}/{urlPath}')
                        if app == 'sga' and modulo.get("sga"):
                            return f(request)
                        if app == 'sagest' and modulo.get("sagest"):
                            return f(request)
                        if app == 'posgrado' and modulo.get("posgrado"):
                            return f(request)
                        if app == 'empleo' and modulo.get("empleo"):
                            return f(request)
                        if app == 'empresa' and modulo.get("empresa"):
                            return f(request)
                        if not modulo.get("sagest") and not modulo.get("sga") and not modulo.get("posgrado"):
                            return f(request)
                        if app == 'investigacionevalproy' and modulo.get("sga"):
                            return f(request)
                        return HttpResponseRedirect("/")
                    else:
                        return HttpResponseRedirect("/")
                else:
                    # if p.es_estudiante():
                    #     if 'connectionToken' in request.session:
                    #         connectionToken = request.session['connectionToken']
                    #         return redirect(f'{connectionToken}/panel')
                    return f(request)
            except Exception as ex:
                p = request.session['perfilprincipal']
                if p:
                    noti = Notificacion(cuerpo=f'Ocurrió un error por lo que su sesion fue cerrada. Error: {ex}', titulo='Ocurrió un error',
                                            destinatario_id=p.persona_id, url="",
                                            prioridad=1, app_label='SGA', fecha_hora_visible=datetime.now() + timedelta(days=1),
                                            tipo=2, en_proceso=False)
                    noti.save()
                return HttpResponseRedirect("/logout")
                # return HttpResponseRedirect("/?info=SysError: %s" % ex)
        else:
            HttpResponseRedirect("/")
    return new_f


def last_access(f):

    def new_f(*args, **kwargs):
        request = args[0]
        if 'ultimo_acceso' in request.session:
            request.session['ultimo_acceso'] = datetime.now()
        if 'validateTwoStepAccess' in request.session:
            validateTwoStepAccess = request.session['validateTwoStepAccess']
            if validateTwoStepAccess:
                eUserAccessSecurity = request.session['eUserAccessSecurity']
                eUserAccessSecurityType = request.session['eUserAccessSecurityType']
                if eUserAccessSecurity and eUserAccessSecurityType:
                    # aux_eUserAccessSecurityDevices = eUserAccessSecurityDevices = UserAccessSecurityDevice.objects.filter(user_access_type_id=eUserAccessSecurityType.pk)
                    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                    if x_forwarded_for:
                        ip_public = x_forwarded_for.split(',')[0]
                    else:
                        ip_public = request.META.get('REMOTE_ADDR')
                    user_agent = get_user_agent(request)
                    # Let's assume that the visitor uses an iPhone...
                    type = 6
                    if user_agent.is_mobile:
                        type = 1
                    elif user_agent.is_tablet:
                        type = 2
                    elif user_agent.is_touch_capable:
                        type = 3
                    elif user_agent.is_pc:
                        type = 4
                    elif user_agent.is_bot:
                        type = 5
                    # Accessing user agent's browser attributes
                    browser = user_agent.browser
                    browser_family = browser.family
                    browser_version = browser.version_string
                    # Operating System properties
                    os = user_agent.os
                    os_family = os.family
                    os_version = os.version_string
                    # Device properties
                    device = user_agent.device
                    device_family = device.family
                    eUserAccessSecurityDevices = UserAccessSecurityDevice.objects.filter(user_access_type_id=eUserAccessSecurityType.pk,
                                                                                   ip_public=ip_public, type=type,
                                                                                   browser=browser_family,
                                                                                   browser_version=browser_version,
                                                                                   os=os_family,
                                                                                   os_version=os_version,
                                                                                   device=device_family,
                                                                                   isActive=True)
                    if not eUserAccessSecurityDevices.values("id").exists():
                        return HttpResponseRedirect("/security/device")
                    eUserAccessSecurityDevices.update(last_access=datetime.now())
            request.session['validateTwoStepAccess'] = False

        persona_sancion = obtener_persona_sancion(request)
        if persona_sancion:
            url_first = bloqueo_acciones_persona_sancion(request, persona_sancion)
            if url_first:
                return HttpResponseRedirect(url_first)

        return f(request)

    return new_f


def inhouse_only(f):

    def new_f(*args, **kargs):
        request = args[0]
        pcrange = request.META['REMOTE_ADDR'].split('.')
        if '*' in ALLOWED_IPS_FOR_INHOUSE:
            return f(request)
        elif request.META['REMOTE_ADDR'] in ALLOWED_IPS_FOR_INHOUSE:
            return f(request)
        else:
            for ip in ALLOWED_IPS_FOR_INHOUSE:
                if ip.endswith(".0.0"):
                    iprange = pcrange[0] + '.' + pcrange[1] + '.0.0'
                    if iprange == ip:
                        return f(request)
                if ip.endswith(".0"):
                    iprange = pcrange[0] + '.' + pcrange[1] + '.' + pcrange[2] + '.0'
                    if iprange == ip:
                        return f(request)
        return HttpResponseRedirect('/')

    return new_f


def inhouse_check(request, valida_clase=False):
    remote_addr = get_client_ip(request)
    pcrange = remote_addr.split('.')
    ippermitidas = IpPermitidas.objects.filter(status=True, habilitado=True)
    if valida_clase:
        ippermitidas = ippermitidas.filter(valida_clase=True)
    if not ippermitidas.values("id").exists():
        return True
    elif ippermitidas.values("id").filter(ip=remote_addr).exists():
        return True
    else:
        for x in ippermitidas.values_list("ip", flat=True):
            if x.endswith(".0.0"):
                iprange = pcrange[0] + '.' + pcrange[1] + '.0.0'
                if iprange == x:
                    return True
            if x.endswith(".0"):
                iprange = pcrange[0] + '.' + pcrange[1] + '.' + pcrange[2] + '.0'
                if iprange == x:
                    return True
    return False


def ip_whitelist_check(request, app=None):
    from bd.models import IPWhiteList
    remote_addr = get_client_ip(request)
    pcrange = remote_addr.split('.')
    if app == 'sga':
        ippermitidas = IPWhiteList.objects.values_list("ip").filter(habilitado=True, sga=True) if IPWhiteList.objects.filter(habilitado=True, sga=True).exists() else ['*']
    elif app == 'sagest':
        ippermitidas = IPWhiteList.objects.values_list("ip").filter(habilitado=True, sagest=True) if IPWhiteList.objects.filter(habilitado=True, sagest=True).exists() else ['*']
    elif app == 'posgrado':
        ippermitidas = IPWhiteList.objects.values_list("ip").filter(habilitado=True, posgrado=True) if IPWhiteList.objects.filter(habilitado=True, posgrado=True).exists() else ['*']
    else:
        ippermitidas = IPWhiteList.objects.values_list("ip").filter(habilitado=True, sga=False, sagest=False, posgrado=False) if IPWhiteList.objects.filter(habilitado=True, sga=False, sagest=False, posgrado=False).exists() else ['*']

    if '*' in ippermitidas:
        return False
    elif app == 'sga' and IPWhiteList.objects.filter(habilitado=True, sga=True, ip=remote_addr).exists():
        return True
    elif app == 'sagest' and IPWhiteList.objects.filter(habilitado=True, sagest=True, ip=remote_addr).exists():
        return True
    elif app == 'posgrado' and IPWhiteList.objects.filter(habilitado=True, posgrado=True, ip=remote_addr).exists():
        return True
    elif IPWhiteList.objects.filter(habilitado=True, sga=False, sagest=False, posgrado=False, ip=remote_addr).exists():
        return True
    else:
        for x in ippermitidas:
            if x[0].endswith(".0.0"):
                iprange = pcrange[0] + '.' + pcrange[1] + '.0.0'
                if iprange == x[0]:
                    return True
            if x[0].endswith(".0"):
                iprange = pcrange[0] + '.' + pcrange[1] + '.' + pcrange[2] + '.0'
                if iprange == x[0]:
                    return True
    return False


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def check_ip_interna_externa(ip):
    pcrange = ip.split('.')
    ippermitidas = IpPermitidas.objects.values_list("ip").filter(habilitado=True) if IpPermitidas.objects.filter(habilitado=True).exists() else ['*']
    if '*' in ippermitidas:
        return True
    elif IpPermitidas.objects.filter(habilitado=True, ip=ip).exists():
        return True
    else:
        for x in ippermitidas:
            if x[0].endswith(".0.0"):
                iprange = pcrange[0] + '.' + pcrange[1] + '.0.0'
                if iprange == x[0]:
                    return True
            if x[0].endswith(".0"):
                iprange = pcrange[0] + '.' + pcrange[1] + '.' + pcrange[2] + '.0'
                if iprange == x[0]:
                    return True
    return False


def change_periodo_perfil(f):
    def new_f(*args, **kwargs):
        request = args[0]
        from sga.models import AperturaPeriodoCambioCarrera, PerfilUsuario
        apertura = AperturaPeriodoCambioCarrera.objects.get(id=request.GET['id']) if 'id' in request.GET and AperturaPeriodoCambioCarrera.objects.filter(id=request.GET['id']).exists() else None
        persona = request.session['persona']
        if not PerfilUsuario.objects.filter(persona=persona, administrativo__isnull=False, visible=True).exists():
            return f(request)
        else:
            perfilprincipal = PerfilUsuario.objects.filter(persona=persona, administrativo__isnull=False, visible=True)[0]
            periodo = request.session['periodo']
            if apertura is not None:
                if perfilprincipal.administrativo:
                    request.session['periodo'] = periodo
                    request.session['perfilprincipal'] = perfilprincipal
            return f(request)
    return new_f


def f_tiene_solicitud_apertura_clase(profesor, periodo):
    from django.db.models import Q
    from inno.models import SolicitudAperturaClaseVirtual
    hoy = datetime.now().date()
    solicitudes_periodo = SolicitudAperturaClaseVirtual.objects.filter(status=True, profesor=profesor, periodo=periodo, estadosolicitud=2)
    return solicitudes_periodo.filter(Q(totalperiodo=True) | Q(fechafin__lte=hoy, fechainicio__gte=hoy)).exists()


def obtener_persona_sancion(request):
    if 'persona_sancion' in request.session and request.session['persona_sancion']:
        return request.session['persona_sancion']
    if 'persona' in request.session:
        persona_sancion = PersonaSancion.objects.filter(persona=request.session['persona'], status=True, bloqueo=True).first()
        if persona_sancion:
            request.session['persona_sancion'] = persona_sancion
            return persona_sancion
    return None


def bloqueo_acciones_persona_sancion(request, persona_sancion):
    action = request.GET.get('action', '') if request.method == 'GET' else request.POST.get('action', '')
    url = f'{request.path}?action={action}&id={request.GET.get("id", "")}'

    if persona_sancion:
        actions_allowed = [
            'respuestadescargo', 'editrespuestadescargo', 'delrespuesta',
            'confirmardescargo', 'confirmarasistencia',
            'justificarnoasistencia', 'detalleaudiencia', 'sifirmaraccionpers', 'nofirmaraccionpers'
        ]
        url_first = f"/th_hojavida?action=revisarincidencia&id={encrypt(persona_sancion.incidencia.id)}"
        if url != url_first and (action not in actions_allowed or request.path != '/th_hojavida'):
            return url_first
    return None