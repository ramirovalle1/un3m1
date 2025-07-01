# coding=latin-1
from urllib.parse import urlencode
from urllib.request import urlopen, Request
import calendar
import json
from django.contrib.auth import authenticate, login
from django.db import transaction
from django.db.models import Max
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render

from directivo.models import PersonaSancion
# from faceid.models import ControlAccesoFaceId
from sagest.models import *
from sagest.models import SecuencialPresupuesto
from settings import CONTACTO_EMAIL, EMAIL_DOMAIN, DECLARACION_SAGEST, DEBUG
from sga.funciones import log, validar_ldap, loglogin
from sga.models import Persona, miinstitucion, DeclaracionUsuario, Noticia, Periodo, PlanificarCapacitaciones, CUENTAS_CORREOS
from sga.tasks import send_html_mail, conectar_cuenta
from bd.models import APP_SGA, APP_SAGEST, APP_POSGRADO, FLAG_FAILED, FLAG_SUCCESSFUL, FLAG_UNKNOWN, \
    TemplateBaseSetting, UserAccessSecurityType, UserAccessSecurity
import random

from sga.templatetags.sga_extras import encrypt


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
    ahora = datetime.now()
    fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
    tiempo_cache = fecha_fin - ahora
    TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
    if EMAIL_DOMAIN in request.META['HTTP_HOST']:
        if 'sagest' not in request.META['HTTP_HOST']:
            if 'admisionposgrado' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginposgrado')
            elif 'postulate' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginpostulate')
            elif 'seleccionposgrado' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginpostulacion')
            elif 'sga' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginsga')
            else:
                return HttpResponseRedirect('/loginsga')

    site_maintenance = variable_valor('SITIO_MANTENIMIENTO')
    if site_maintenance:
        data = {}
        return render(request, "maintenance.html", data)

    ipvalidas = ['192.168.61.96', '192.168.61.97', '192.168.61.98', '192.168.61.99']
    client_address = get_client_ip(request)
    if request.method == 'POST':

        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'login':
                try:
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
                            loglogin(action_flag=FLAG_FAILED, action_app=APP_SAGEST, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, user=user, change_message=u"Usuario no activo")
                            return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, usuario no activo.'})
                        else:
                            if Persona.objects.filter(usuario=user).exists():
                                persona = Persona.objects.filter(usuario=user)[0]
                                if persona.tiene_perfil():
                                    app = 'sagest'
                                    perfiles = persona.mis_perfilesusuarios_app(app)
                                    perfilprincipal = persona.perfilusuario_principal(perfiles, app)
                                    if not perfilprincipal:
                                        return JsonResponse({"result": "bad", 'mensaje': u'No existe un perfiles para esta aplicacion.'})
                                    request.session.set_expiry(240 * 60)
                                    request.session['login_manual'] = True
                                    login(request, user)

                                    if not DEBUG:
                                        eUserAccessSecurity = None
                                        eUserAccessSecurityType = None
                                        eUserAccessSecurity = cache.get(f"user_access_security_{encrypt(user.id)}")
                                        if not eUserAccessSecurity:
                                            eUserAccessSecurity = UserAccessSecurity.objects.filter(user=user, isActive=True).first()
                                            if eUserAccessSecurity:
                                                cache.set(f"user_access_security_{encrypt(user.id)}", eUserAccessSecurity, TIEMPO_ENCACHE)

                                        if eUserAccessSecurity:
                                            eUserAccessSecurityType = cache.get(f"user_access_security_type_{encrypt(user.id)}")
                                            if not eUserAccessSecurityType:
                                                eUserAccessSecurityType = UserAccessSecurityType.objects.filter(
                                                    user_access=eUserAccessSecurity, type=1, isActive=True).first()
                                                if eUserAccessSecurityType:
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
                                    nombresistema = u'Sistema de Gestión Administrativa'
                                    eTemplateBaseSetting = None
                                    if TemplateBaseSetting.objects.values().filter(status=True, app=2).exists():
                                        eTemplateBaseSetting = TemplateBaseSetting.objects.filter(status=True, app=2)[0]
                                        nombresistema = eTemplateBaseSetting.name_system
                                    request.session['eTemplateBaseSetting'] = eTemplateBaseSetting
                                    request.session['nombresistema'] = nombresistema
                                    loglogin(action_flag=FLAG_SUCCESSFUL, action_app=APP_SAGEST, ip_private=capippriva,
                                             ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                             screen_size=screensize, user=user)
                                    # log(u'Login con exito: %s - %s - %s - %s - %s' % (persona, browser, ops, client_address, capippriva), request, "add")
                                    # validacion ldap por sga
                                    if Periodo.objects.filter(preferenciaadmision=True).exists():
                                        if persona.distributivopersona_set.filter(unidadorganica__status=True,
                                                                                  denominacionpuesto__status=True,
                                                                                  modalidadlaboral__status=True,
                                                                                  nivelocupacional__status=True,
                                                                                  regimenlaboral__status=True,
                                                                                  estadopuesto_id=1, status=True):
                                            request.session['periodoadmision'] = Periodo.objects.filter(preferenciaadmision=True)[0]
                                    if variable_valor('VALIDAR_LDAP'):
                                        validar_ldap(request.POST['user'].lower(), request.POST['pass'], persona)
                                    if client_address in ipvalidas:
                                        if DECLARACION_SAGEST:
                                            declaracionusuario = DeclaracionUsuario(persona=persona,
                                                                                    fecha=datetime.now(),
                                                                                    ip=client_address,
                                                                                    sistema='SAGEST')
                                            declaracionusuario.save(request)
                                            log(u'Declaracion de usuario en el sagest: %s [%s]' % (declaracionusuario, declaracionusuario.id), request, "add")
                                    if variable_valor('SEND_LOGIN_EMAIL_SAGEST') and not DEBUG:
                                        send_html_mail("Login exitoso SAGEST", "emails/loginexito.html", {'sistema': request.session['nombresistema'], 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies, 'screensize': screensize, 't': miinstitucion()}, persona.emailinst, [], cuenta=CUENTAS_CORREOS[1][1])
                                    persona_sancion = PersonaSancion.objects.filter(persona=persona, status=True).first()
                                    if persona_sancion:
                                        if persona_sancion.notificacion == 1:
                                            request.session['persona_sancion_notificar'] = persona_sancion
                                        elif persona_sancion.bloqueo:
                                            request.session['persona_sancion'] = persona_sancion
                                    url_redirect = request.POST.get('next', '/')
                                    return JsonResponse({"result": "ok", "sessionid": request.session.session_key, 'url_redirect': url_redirect})
                                else:
                                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existen perfiles activos.'})
                            else:
                                loglogin(action_flag=FLAG_UNKNOWN, action_app=APP_SAGEST, ip_private=capippriva,
                                         ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                         screen_size=screensize, change_message=u"USUARIO: %s - CLAVE: %s" % (request.POST['user'].lower().strip(), request.POST['pass']))
                                # log(u'Login fallido, no existe el usuario: %s' % request.POST['user'], request, "add")
                                return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existe el usuario.'})
                    else:
                        if not Persona.objects.filter(usuario__username=request.POST['user'].lower()).exists():
                            loglogin(action_flag=FLAG_UNKNOWN, action_app=APP_SAGEST, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, change_message=u"USUARIO: %s - CLAVE: %s" % (request.POST['user'].lower().strip(), request.POST['pass']))
                        if Persona.objects.filter(usuario__username=request.POST['user'].lower()).exists():
                            persona = Persona.objects.filter(usuario__username=request.POST['user'].lower())[0]
                            loglogin(action_flag=FLAG_FAILED, action_app=APP_SAGEST, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, user=persona.usuario, change_message=u"Clave Incorrecta")
                            # log(u'Login fallido SAGEST: %s - %s - %s - %s - %s' % (persona, browser, ops, client_address, capippriva), request, "add", user=persona.usuario)
                            send_html_mail("Login fallido SAGEST.", "emails/loginfallido.html", {'sistema': u'Login fallido, no existen perfiles activos.', 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies, 'screensize': screensize, 't': miinstitucion()}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[1][1])
                        return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, credenciales incorrectas.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, Error en el sistema.'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        try:
            if 'persona' in request.session:
                return HttpResponseRedirect("/")
            data = {"title": u"Login", "background": 9}
            data['request'] = request
            hoy = datetime.now().date()
            # data['noticias'] = Noticia.objects.filter(Q(desde__lte=hoy), Q(hasta__gte=hoy), Q(imagen__isnull=True),(Q(publicacion=1) | Q(publicacion=3))).order_by('-desde', 'id')[0:5]
            data['noticias'] = Noticia.objects.filter(Q(desde__lte=hoy), Q(hasta__gte=hoy), Q(imagen__isnull=True), (Q(publicacion=1) | Q(publicacion=3)), banerderecho=False, tipos__in=[1], tiene_muestra=False).distinct().order_by('-desde', 'id')[0:5]
            # data['noticiasgraficas'] = Noticia.objects.filter(Q(desde__lte=hoy), Q(hasta__gte=hoy), Q(imagen__isnull=False),(Q(publicacion=1) | Q(publicacion=3))).order_by('-desde','id')[:1]
            data['noticiasgraficas'] = None
            data['currenttime'] = datetime.now()
            data['institucion'] = miinstitucion().nombre
            data['contacto_email'] = CONTACTO_EMAIL
            if client_address in ipvalidas:
                data['validar_con_captcha'] = False
                data['declaracion_sagest'] = False
            else:
                data['validar_con_captcha'] = variable_valor('VALIDAR_CON_CAPTCHA_SAGEST')
                data['declaracion_sagest'] = DECLARACION_SAGEST
            data['tipoentrada'] = request.session['tipoentrada'] = "SAGEST"
            data['public_key'] = variable_valor('GOOGLE_RECAPTCHA_PUBLIC_KEY')
            data['faceid_access'] = ControlAccesoFaceId.objects.filter(status=True, activo=True, app=2).last()
            #DIASCELEBRACIÓN
            data["next"] = request.GET.get('ret', False)
            data['DIA_CANCER_MAMA_19_OCTUBRE'] = variable_valor('DIA_CANCER_MAMA_19_OCTUBRE')
            return render(request, "login/loginsagest.html", data)
        except Exception as ex:
            import sys
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            pass

def secuencia_activos(request):
    if not SecuenciaActivos.objects.exists():
        secuencia = SecuenciaActivos()
        secuencia.save(request)
        return secuencia
    else:
        return SecuenciaActivos.objects.all()[0]


def secuencia_bodega(request):
    if not SecuenciaBodega.objects.exists():
        secuencia = SecuenciaBodega()
        secuencia.save(request)
        return secuencia
    else:
        return SecuenciaBodega.objects.all()[0]


def secuencia_recaudacion(request, puntoventa, campo=None):
    # Valores Campo: 1 factura - 2 notacredito - 3 comprobante - 4 nocur - 5 documento - 6 recibocaja - 7 recibocajapago
    if not SecuencialRecaudaciones.objects.filter(puntoventa=puntoventa).exists():
        qsbasesecuencial = SecuencialRecaudaciones.objects.create(puntoventa=puntoventa)
    else:
        qsbasesecuencial = SecuencialRecaudaciones.objects.filter(puntoventa=puntoventa).first()
    secuencial_ = model_to_dict(qsbasesecuencial)[campo]
    if secuencial_ > 0:
        secuencial_ += 1
    else:
        secuencial_ = 1
    if campo == 'factura':
        SecuencialRecaudaciones.objects.filter(puntoventa=puntoventa).update(factura=secuencial_)
    elif campo == 'notacredito':
        SecuencialRecaudaciones.objects.filter(puntoventa=puntoventa).update(notacredito=secuencial_)
    elif campo == 'comprobante':
        SecuencialRecaudaciones.objects.filter(puntoventa=puntoventa).update(comprobante=secuencial_)
    elif campo == 'nocur':
        SecuencialRecaudaciones.objects.filter(puntoventa=puntoventa).update(nocur=secuencial_)
    elif campo == 'documento':
        SecuencialRecaudaciones.objects.filter(puntoventa=puntoventa).update(documento=secuencial_)
    elif campo == 'recibocaja':
        SecuencialRecaudaciones.objects.filter(puntoventa=puntoventa).update(recibocaja=secuencial_)
    elif campo == 'recibocajapago':
        SecuencialRecaudaciones.objects.filter(puntoventa=puntoventa).update(recibocajapago=secuencial_)
    elif campo == 'liquidacioncompra':
        SecuencialRecaudaciones.objects.filter(puntoventa=puntoventa).update(liquidacioncompra=secuencial_)
    return secuencial_


def secuencia_caja(request, anio):
    anioe = AnioEjercicio.objects.get(anioejercicio=anio)
    if not SecuenciaSesionCaja.objects.filter(anioejercicio=anioe).exists():
        secuencia = SecuenciaSesionCaja(anioejercicio=anioe)
        secuencia.save(request)
        return secuencia
    else:
        return SecuenciaSesionCaja.objects.filter(anioejercicio=anioe)[0]


def secuencia_egreso(request):
    if not SecuenciaEgresos.objects.exists():
        secuencia = SecuenciaEgresos()
        secuencia.save(request)
        return secuencia
    else:
        return SecuenciaEgresos.objects.all()[0]


def secuencia_presupuesto(request):
    if not SecuencialPresupuesto.objects.exists():
        secuencia = SecuencialPresupuesto()
        secuencia.save(request)
        return secuencia
    else:
        return SecuencialPresupuesto.objects.all()[0]

def secuencia_ordentrabajo(request, anio):
    anioe = AnioEjercicio.objects.get(anioejercicio=anio)
    if not SecuenciaHdIncidente.objects.filter(anioejercicio=anioe).exists():
        secuencia = SecuenciaHdIncidente(anioejercicio=anioe)
        secuencia.save(request)
        return secuencia
    else:
        return SecuenciaHdIncidente.objects.filter(anioejercicio=anioe)[0]
# METODOS PARA VER PAGOS Y FORMAS DE PAGOS DEL DIA, ADEMAS DATOS ESTADISTICOS Y ACADEMICOS GENERALES
def total_efectivo_dia(fecha):
    return null_to_decimal(Pago.objects.filter(sesion__fecha=fecha, efectivo=True, factura__valida=True).aggregate(valor=Sum('valortotal'))['valor'])


def total_efectivo_rango(inicio, fin):
    return null_to_decimal(Pago.objects.filter(sesion__fecha__gte=inicio, sesion__fecha__lte=fin, efectivo=True, factura__valida=True).aggregate(valor=Sum('valortotal'))['valor'])


def total_efectivo_mes():
    hoy = datetime.now().date()
    ultimodia = calendar.monthrange(hoy.year, hoy.month)[1]
    inicio = date(hoy.year, hoy.month, 1)
    fin = date(hoy.year, hoy.month, ultimodia)
    return null_to_decimal(Pago.objects.filter(sesion__fecha__gte=inicio, sesion__fecha__lte=fin, efectivo=True).aggregate(valor=Sum('valortotal'))['valor'])


def cantidad_facturas_dia(fecha):
    return Factura.objects.values('id').filter(pagos__sesion__fecha=fecha).distinct().count()


def cantidad_facturas_rango(inicio, fin):
    return Factura.objects.values('id').filter(pagos__sesion__fecha__gte=inicio, pagos__sesion__fecha__lte=fin).distinct().count()


def cantidad_cheques_dia(fecha):
    return PagoCheque.objects.values('id').filter(pagos__fecha=fecha).distinct().count()


def cantidad_cheques_rango(inicio, fin):
    return PagoCheque.objects.values('id').filter(pagos__fecha__gte=inicio, pagos__fecha__lte=fin).distinct().count()


def total_cheque_dia(fecha):
    return null_to_numeric(Pago.objects.filter(fecha=fecha, pagocheque__isnull=False).aggregate(valor=Sum('valortotal'))['valor'])


def total_cheque_rango(inicio, fin):
    return null_to_decimal(Pago.objects.filter(fecha__gte=inicio, fecha__lte=fin, pagocheque__isnull=False).aggregate(valor=Sum('valortotal'))['valor'])


def cantidad_tarjetas_dia(fecha):
    return PagoTarjeta.objects.values('id').filter(pagos__fecha=fecha).distinct().count()


def cantidad_tarjetas_rango(inicio, fin):
    return PagoTarjeta.objects.values('id').filter(pagos__fecha__gte=inicio, pagos__fecha__lte=fin).distinct().count()


def total_tarjeta_dia(fecha):
    return null_to_decimal(Pago.objects.filter(fecha=fecha, pagotarjeta__isnull=False).aggregate(valor=Sum('valortotal'))['valor'])


def total_tarjeta_rango(inicio, fin):
    return null_to_decimal(Pago.objects.filter(fecha__gte=inicio, fecha__lte=fin, pagotarjeta__isnull=False).aggregate(valor=Sum('valortotal'))['valor'])


def cantidad_depositos_dia(fecha):
    return PagoTransferenciaDeposito.objects.values('id').filter(pagos__fecha=fecha, deposito=True).distinct().count()


def cantidad_depositos_rango(inicio, fin):
    return PagoTransferenciaDeposito.objects.values('id').filter(pagos__fecha__gte=inicio, pagos__fecha__lte=fin, deposito=True).distinct().count()


def total_deposito_dia(fecha):
    return null_to_decimal(Pago.objects.filter(fecha=fecha, pagotransferenciadeposito__isnull=False, pagotransferenciadeposito__deposito=True).aggregate(valor=Sum('valortotal'))['valor'])


def total_deposito_rango(inicio, fin):
    return null_to_decimal(Pago.objects.filter(fecha__gte=inicio, fecha__lte=fin, pagotransferenciadeposito__isnull=False, pagotransferenciadeposito__deposito=True).aggregate(valor=Sum('valortotal'))['valor'])


def cantidad_transferencias_dia(fecha):
    return PagoTransferenciaDeposito.objects.values('id').filter(pagos__fecha=fecha, deposito=False).distinct().count()


def cantidad_transferencias_rango(inicio, fin):
    return PagoTransferenciaDeposito.objects.values('id').filter(pagos__fecha__gte=inicio, pagos__fecha__lte=fin, deposito=False).distinct().count()


def total_transferencia_dia(fecha):
    return null_to_decimal(Pago.objects.filter(fecha=fecha, pagotransferenciadeposito__isnull=False, pagotransferenciadeposito__deposito=False).aggregate(valor=Sum('valortotal'))['valor'])


def total_transferencia_rango(inicio, fin):
    return null_to_decimal(Pago.objects.filter(fecha__gte=inicio, fecha__lte=fin, pagotransferenciadeposito__isnull=False, pagotransferenciadeposito__deposito=False).aggregate(valor=Sum('valortotal'))['valor'])


def total_dia(fecha):
    return total_efectivo_dia(fecha) + total_cheque_dia(fecha) + total_deposito_dia(fecha) + total_transferencia_dia(fecha) + total_tarjeta_dia(fecha)


def total_rango(inicio, fin):
    return total_efectivo_rango(inicio, fin) + total_cheque_rango(inicio, fin) + total_deposito_rango(inicio, fin) + total_transferencia_rango(inicio, fin) + total_tarjeta_rango(inicio, fin)


def facturas_total_fecha(fecha):
    return Factura.objects.values('id').filter(pagos__sesion__fecha=fecha).distinct().count() if Factura.objects.values('id').filter(pagos__sesion__fecha=fecha).exists() else 0


def pagos_total_fecha(fecha):
    return null_to_decimal(Pago.objects.filter(fecha=fecha, factura__valida=True).aggregate(valor=Sum('valortotal'))['valor'])


def cantidad_facturas_total_fechas(inicio, fin):
    return Factura.objects.values('id').filter(sesioncaja__fecha__gte=inicio, sesioncaja__fecha__lte=fin, valida=True).distinct().distinct().count()


def total_pagos_rango_fechas(inicio, fin):
    return null_to_decimal(Pago.objects.filter(fecha__gte=inicio, fecha__lte=fin, factura__valida=True).aggregate(valor=Sum('valortotal'))['valor'])


def valor_total_deudores_activos_30dias():
    hoy = datetime.now().date()
    fechavence = hoy - timedelta(days=30)
    return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lt=hoy, fechavence__gte=fechavence).aggregate(valor=Sum('saldo'))['valor'])


def valor_total_apagar_activos_30dias():
    hoy = datetime.now().date()
    fechavence = (datetime.now() + timedelta(days=30)).date()
    return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lt=hoy, fechavence__gte=fechavence).aggregate(valor=Sum('saldo'))['valor'])


def valor_total_deudores_activos_31_90dias():
    hoy = (datetime.now() - timedelta(days=31)).date()
    fechavence = (datetime.now() - timedelta(days=90)).date()
    return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lt=hoy, fechavence__gte=fechavence).aggregate(valor=Sum('saldo'))['valor'])


def valor_total_apagar_activos_31_90dias():
    hoy = (datetime.now() + timedelta(days=31)).date()
    fechavence = (datetime.now() + timedelta(days=90)).date()
    return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lt=hoy, fechavence__gte=fechavence).aggregate(valor=Sum('saldo'))['valor'])


def valor_total_deudores_activos_mas_90dias():
    hoy = (datetime.now() - timedelta(days=91)).date()
    return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lt=hoy).aggregate(valor=Sum('saldo'))['valor'])


def valor_total_apagar_activos_mas_90dias():
    hoy = (datetime.now() - timedelta(days=91)).date()
    return null_to_numeric(Rubro.objects.filter(cancelado=False, fechavence__lt=hoy).aggregate(valor=Sum('saldo'))['valor'])


def valor_deudores_activos_total():
    return valor_total_deudores_activos_30dias() + valor_total_deudores_activos_31_90dias() + valor_total_deudores_activos_mas_90dias()


def valor_apagar_activos_total():
    return valor_total_apagar_activos_30dias() + valor_total_apagar_activos_31_90dias() + valor_total_apagar_activos_mas_90dias()


def valor_deudas_activos_total():
    return valor_deudores_activos_total() + valor_apagar_activos_total()


def cantidad_total_deudores():
    return Persona.objects.values('id').filter(rubro__fechavence__lt=datetime.now().date(), rubro__cancelado=False).distinct().count()


def cantidad_total_apagar():
    return Persona.objects.values('id').filter(rubro__fechavence__gt=datetime.now().date(), rubro__cancelado=False).distinct().count()


def anio_ejercicio():
    anio = datetime.now().year
    if AnioEjercicio.objects.filter(anioejercicio=anio).exists():
        anioejercicio = AnioEjercicio.objects.filter(anioejercicio=anio)[0]
    else:
        anioejercicio = AnioEjercicio(anioejercicio=anio)
        anioejercicio.save()
    return anioejercicio


def secuencia_convenio_devengacion(tipo):
    reg = PlanificarCapacitaciones.objects.filter(status=True, fechaconvenio__year=datetime.now().year, tipo=tipo).aggregate(numconv=Max('numeroconvenio') + 1)
    if reg['numconv'] is None:
        secuencia = 1
    else:
        secuencia = reg['numconv']
    return secuencia

def obtener_estado_solicitud(opcionid, valorestado):
    return EstadoSolicitud.objects.get(opcion_id=opcionid, valor=valorestado, status=True)

def obtener_estados_solicitud(opcionid, valoresestado):
    return EstadoSolicitud.objects.filter(opcion_id=opcionid, valor__in=valoresestado, status=True).order_by('valor')

def obtener_estado_solicitud_por_id(id):
    return EstadoSolicitud.objects.get(pk=id)

def obtener_tipoarchivo_solicitud(opcionid, valorestado):
    return TipoArchivoSolicitud.objects.get(opcion_id=opcionid, valor=valorestado)
