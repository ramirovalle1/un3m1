# coding=latin-1
import json
import os
import io
import sys
from hashlib import md5
from cgitb import html
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from _decimal import Decimal
from django.contrib import messages
from django.contrib.auth import authenticate, logout, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.db import transaction, connection, connections
from django.db.models import F, Sum, Exists, OuterRef
from django.db.models import Q
from django.db.models.aggregates import Count, Max
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.core.exceptions import ObjectDoesNotExist
import settings
from api.helpers.functions_helper import get_variable
from bd.funciones import generate_code, action_registre_log_clic_commonviews
from bib.models import Documento, ReferenciaWeb, ReservaDocumento
from core.pipelines import loginchangeuser
from decorators import secure_module, last_access, ip_whitelist_check
from even.models import PeriodoEvento, DetallePeriodoEvento, RegistroEvento
from inno.models import PeriodoAcademia, PerfilRequeridoPac, TerminosCondiciones, TerminosCondicionesProfesorDistributivo
from matricula.funciones import puede_matricularse_seguncronograma_coordinacion_prematricula, \
    puede_matricularse_seguncronograma_coordinacion
from matricula.models import PeriodoMatricula
from posgrado.models import IntegranteGrupoExamenMsc, IntegranteGrupoEntrevitaMsc
from postulaciondip.models import InscripcionInvitacion, Requisito, ActividadEconomica, RequisitosProceso, InscripcionPostulante, RequisitosConvocatoria, Convocatoria, InscripcionConvocatoria, TIPO_CONVOCATORIA
from postulate.models import PersonaPeriodoConvocatoria
from sagest.models import Rubro, TipoOtroRubro, VacunaCovid, CapInscritoIpec, CapInstructorIpec, CapDetalleNotaIpec
from sagest.models import CompromisoPagoPosgrado
from settings import NOMBRE_INSTITUCION, ALUMNOS_GROUP_ID, SEXO_FEMENINO, SEXO_MASCULINO, UTILIZA_FICHA_MEDICA, \
    RECTORADO_GROUP_ID, SISTEMAS_GROUP_ID, UTILIZA_MODULO_ENCUESTAS, TIPO_PERIODO_REGULAR, DATOS_OBLIGATORIOS, \
    CONTACTO_EMAIL, MATRICULACION_LIBRE, CHEQUEAR_CONFLICTO_HORARIO, HOMITIRCAPACIDADHORARIO, \
    URL_APLICACION_ESTUDIANTE_ANDROID, URL_APLICACION_ESTUDIANTE_IOS, URL_APLICACION_PROFESOR_ANDROID, \
    NOTA_ESTADO_EN_CURSO, MATRICULACION_POR_NIVEL, MODULO_EVALUACION_PARESDIRECTIVOS_ID, CHEQUEAR_CORREO, \
    PORCIENTO_RECUPERACION_FALTAS, PIE_PAGINA_CREATIVE_COMMON_LICENCE, PROFESORES_GROUP_ID, \
    EMPLEADORES_GRUPO_ID, EMAIL_DOMAIN, ARCHIVO_TIPO_MANUALES, DECLARACION_SGA, PANTALLA_PREINSCRIPCION, \
    SERVER_RESPONSE, RUBRO_ARANCEL, PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD, RUBRO_MATRICULA, DEBUG, SITE_STORAGE
from sga.forms import CambioClaveForm, ConfirmaExtensionForm, ConfirmaCredoPoliticaForm, ConfirmaDatosBienestarForm, \
    BecaSolicitudSubirCedulaForm, PersonaSubirCedulaForm
from sga.funciones import to_unicode, log, fechatope, variable_valor, puede_realizar_accion_afirmativo, \
    null_to_decimal, validar_ldap, validar_ldap_aux, generar_nombre, validar_ldap_reseteo, loglogin,convertir_fecha_invertida,convertir_fecha
from sga.models import Persona, ModuloGrupo, Periodo, Noticia, Profesor, Inscripcion, Archivo, \
    TituloInstitucion, Matricula, Incidencia, Encuesta, Modulo, MateriaAsignada, AsistenciaLeccion, Reporte, \
    Asignatura, AsignaturaMalla, Nivel, Materia, Clase, RespuestaEncuesta, \
    IndicadorAmbitoInstrumentoEvaluacion, DatoRespuestaEncuesta, years_ago, miinstitucion, \
    JustificacionAusenciaAsistenciaLeccion, PreMatricula, PerfilUsuario, Respuesta, PreMatriculaModulo, \
    DeclaracionUsuario, ComplexivoPeriodo, MateriaAsignadaPlanificacion, \
    RespuestaEvaluacionAcreditacion, ActividadDetalleDistributivoCarrera, Graduado, Egresado, PersonaActualizaExtension, \
    ProfesorMateria, CUENTAS_CORREOS, AuditoriaNotas, OfertasPracticas, PublicarEnlace, \
    PersonaConfirmarEncuesta, AlumnosPracticaMateria, GruposProfesorMateria, ProfesorDistributivoHoras, Leccion, \
    PreMatriculaAsignatura, PracticasPreprofesionalesInscripcion, PreInscripcionPracticasPP, \
    DetallePreInscripcionPracticasPP, DetalleRespuestaPreInscripcionPPP, RespuestaPreInscripcionPracticasPP, \
    EncuestaMovilidad, ConfirmacionPracticasInscripcion, ConfirmaCapacidadTecnologica, \
    InscripcionEncuestaGrupoEstudiantes, EncuestaGrupoEstudiantes, PreguntaEncuestaGrupoEstudiantes, \
    RespuestaPreguntaEncuestaGrupoEstudiantes, OpcionCuadriculaEncuestaGrupoEstudiantes, \
    RespuestaCuadriculaEncuestaGrupoEstudiantes, BecaAsignacion, BecaSolicitud, \
    RespuestaMultipleEncuestaGrupoEstudiantes, RespuestaRangoEncuestaGrupoEstudiantes, PersonaDocumentoPersonal, \
    SolicitudPagoBeca, UsuarioLdap, EncuestaFormsGoogle, EncuestaFormsGoogleInscripcion, AuditoriaMatricula, \
    ConfirmarMatricula, PerdidaGratuidad, PeriodoGrupoSocioEconomico, TipoArchivo, BecaPeriodo, \
    NotificacionDeudaPeriodo, CabPadronElectoral, DetPersonaPadronElectoral, Pais, Provincia, Canton, Parroquia, \
    UbicacionPersona, AperturaPeriodoCambioCarrera, NivelTitulacion, OpcionMultipleEncuestaGrupoEstudiantes, \
    NoticiaMuestra, ClaseActividad, Titulacion, InsigniaPersona, CamposTitulosPostulacion, ModuloCategorias, \
    RetiroCarrera
from sga.tasks import send_html_mail, conectar_cuenta
from moodle.models import UserAuth
from sga.templatetags.sga_extras import encrypt, encrypt_alu
from socioecon.models import FichaSocioeconomicaINEC
from bd.models import APP_SGA, APP_SAGEST, APP_POSGRADO, FLAG_FAILED, FLAG_SUCCESSFUL, FLAG_UNKNOWN, PeriodoGrupo, \
    WebSocket, TemplateBaseSetting, MenuFavoriteProfile, UserToken, UserProfileChangeToken, UserAccessSecurity, \
    UserAccessSecurityType
from voto.models import PersonasSede, SedesElectoralesPeriodo
from django.core.cache import cache
from directivo.models import PersonaSancion
# from faceid.models import ControlAccesoFaceId
import random
unicode = str


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# from django.views.decorators.cache import cache_page
# AUTENTIFICA EL USUARIO
@transaction.atomic()
def login_user(request):
    ahora = datetime.now()
    fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
    tiempo_cache = fecha_fin - ahora
    TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
    data = {}
    capippriva = ''
    if EMAIL_DOMAIN in request.META['HTTP_HOST']:
        if 'sga' not in request.META['HTTP_HOST']:
            if 'admisionposgrado' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginposgrado')
            elif 'sagest' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginsagest')
            elif 'postulate' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginpostulate')
            elif 'seleccionposgrado' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginpostulacion')
            elif 'empleo' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/loginempleo')
            elif 'vinculacion' in request.META['HTTP_HOST']:
                return HttpResponseRedirect('/servicios')

    site_maintenance = variable_valor('SITIO_MANTENIMIENTO')
    if site_maintenance:
        return render(request, "maintenance.html", data)

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
                    profile = request.POST.get('profile', None)
                    if variable_valor('VALIDAR_CON_CAPTCHA_SGA'):
                        if not ip_whitelist_check(request, 'sga') and not DEBUG:
                            recaptcha_response = request.POST.get('g-recaptcha-response')
                            url = 'https://www.google.com/recaptcha/api/siteverify'
                            values = {'secret': variable_valor('GOOGLE_RECAPTCHA_SECRET_KEY'), 'response': recaptcha_response}
                            data = urlencode(values)
                            data = data.encode('utf-8')
                            req = Request(url, data)
                            response = urlopen(req)
                            result = json.loads(response.read().decode())
                            if not result['success']:
                                return JsonResponse({"result": "bad", 'mensaje': u'ReCaptcha no válido. Vuelve a intentarlo..'})
                    user = authenticate(username=request.POST['user'].lower().strip(), password=request.POST['pass'])
                    if user is None:
                        persona = Persona.objects.db_manager("sga_select").filter(usuario__username=request.POST['user'].lower()).first()
                        if not persona:
                            loglogin(action_flag=FLAG_UNKNOWN, action_app=APP_SGA, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, change_message=u"USUARIO: %s - CLAVE: %s" % (request.POST['user'].lower().strip(), request.POST['pass']))
                        else:
                            loglogin(action_flag=FLAG_FAILED, action_app=APP_SGA, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, user=persona.usuario, change_message=u"Clave Incorrecta")
                            if persona.es_administrativo() or persona.es_profesor() or persona.es_administrador():
                                send_html_mail("Login fallido SGA.", "emails/loginfallido.html", {'sistema': u'Sistema de Gestión Académica', 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies, 'screensize': screensize, 't': miinstitucion()}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[0][1])
                        return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, credenciales incorrectas.'})

                    else:
                        if not user.is_active:
                            loglogin(action_flag=FLAG_FAILED, action_app=APP_SGA, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, user=user, change_message=u"Usuario no activo")
                            return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, usuario no activo.'})
                        else:
                            if (persona := Persona.objects.filter(usuario=user).first()) is not None:
                                if not persona.tiene_perfil():
                                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existen perfiles activos.'})
                                if not persona.es_administrativo() and not persona.es_profesor():
                                    if persona.es_estudiante():
                                        return JsonResponse({"result": "bad", 'mensaje': f'Estimad{"a" if persona.es_mujer() else "o"} para ingresar utilice perfil estudiante'})

                                app = 'sga'
                                if persona.es_evaluador_externo_proyectos_investigacion() or persona.es_evaluador_externo_obras_relevancia() or persona.es_integrante_externo_proyecto_investigacion():
                                    app = 'investigacionevalproy'
                                perfiles = persona.mis_perfilesusuarios_app(app)
                                perfilprincipal = persona.perfilusuario_principal(perfiles, app, profile)

                                if not perfilprincipal:
                                    return JsonResponse({"result": "bad", 'mensaje': u'No existe un perfiles para esta aplicacion.'})

                                request.session.set_expiry(240 * 60)
                                request.session['login_manual'] = True
                                login(request, user)
                                if not DEBUG:
                                    eUserAccessSecurity = None
                                    eUserAccessSecurityType = None
                                    # if cache.has_key(f"user_access_security_{encrypt(user.id)}"):
                                    #     eUserAccessSecurity = cache.get(f"user_access_security_{encrypt(user.id)}")
                                    # else:
                                    #     eUserAccessSecurities = UserAccessSecurity.objects.filter(user=user, isActive=True)
                                    #     if eUserAccessSecurities.values("id").exists():
                                    #         eUserAccessSecurity = eUserAccessSecurities.first()
                                    #     cache.set(f"user_access_security_{encrypt(user.id)}", eUserAccessSecurity, TIEMPO_ENCACHE)
                                    # if eUserAccessSecurity:
                                    #     if cache.has_key(f"user_access_security_type_{encrypt(user.id)}"):
                                    #         eUserAccessSecurityType = cache.get(f"user_access_security_type_{encrypt(user.id)}")
                                    #     else:
                                    #         eUserAccessSecurityTypes = UserAccessSecurityType.objects.filter(user_access=eUserAccessSecurity, type=1, isActive=True)
                                    #         if eUserAccessSecurityTypes.values("id").exists():
                                    #             eUserAccessSecurityType = eUserAccessSecurityTypes.first()
                                    #         cache.set(f"user_access_security_type_{encrypt(user.id)}", eUserAccessSecurityType, TIEMPO_ENCACHE)

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
                                nombresistema = u'Sistema de Gestión Académica'
                                eTemplateBaseSetting = None
                                if (eTemplateBaseSetting := TemplateBaseSetting.objects.filter(status=True, app=1).first()) is not None:
                                    nombresistema = eTemplateBaseSetting.name_system
                                request.session['eTemplateBaseSetting'] = eTemplateBaseSetting
                                request.session['nombresistema'] = nombresistema
                                loglogin(action_flag=FLAG_SUCCESSFUL, action_app=APP_SGA, ip_private=capippriva,
                                         ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                         screen_size=screensize, user=user)
                                if persona.administrativo_activo() or persona.es_profesor() or persona.es_administrador():
                                    if variable_valor('SEND_LOGIN_EMAIL_SGA') and not DEBUG:
                                        send_html_mail("Login exitoso SGA.", "emails/loginexito.html",
                                                       {'sistema': request.session['nombresistema'],
                                                        'fecha': datetime.now().date(), 'hora': datetime.now().time(),
                                                        'bs': browser, 'ip': client_address, 'ipvalida': capippriva,
                                                        'os': ops, 'cookies': cookies, 'screensize': screensize,
                                                        't': miinstitucion()}, [persona.emailinst,], [],
                                                       cuenta=CUENTAS_CORREOS[0][1])

                                usuario = user
                                if not UserAuth.objects.db_manager("sga_select").values("id").filter(usuario=usuario).exists():
                                    usermoodle = UserAuth(usuario=usuario)
                                    usermoodle.set_data()
                                    usermoodle.set_password(request.POST['pass'])
                                    usermoodle.save()
                                else:
                                    usermoodle = UserAuth.objects.filter(usuario=usuario).first()
                                    if not usermoodle.check_password(request.POST['pass']) or usermoodle.check_data():
                                        if not usermoodle.check_password(request.POST['pass']):
                                            usermoodle.set_password(request.POST['pass'])
                                        usermoodle.save()
                                #SANCIONES
                                persona_sancion = PersonaSancion.objects.filter(persona=persona, status=True).first()
                                if persona_sancion:
                                    if persona_sancion.notificacion == 1:
                                        request.session['persona_sancion_notificar'] = persona_sancion
                                    elif persona_sancion.bloqueo:
                                        request.session['persona_sancion'] = persona_sancion

                                url_redirect = request.POST.get('next', '/')
                                return JsonResponse({"result": "ok", "sessionid": request.session.session_key, 'url_redirect': url_redirect})
                            else:
                                loglogin(action_flag=FLAG_UNKNOWN, action_app=APP_SGA, ip_private=capippriva,
                                         ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                         screen_size=screensize, change_message=u"USUARIO: %s - CLAVE: %s" % (request.POST['user'].lower().strip(), request.POST['pass']))
                                # log(u'Login fallido, no existe el usuario: %s' % request.POST['user'], request, "add")
                                return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existe el usuario.'})

                    """if user is not None:
                        if not user.is_active:
                            loglogin(action_flag=FLAG_FAILED, action_app=APP_SGA, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, user=user, change_message=u"Usuario no activo")
                            return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, usuario no activo.'})
                        else:
                            if (persona := Persona.objects.filter(usuario=user).first()) is not None :
                                # persona = Persona.objects.filter(usuario=user)[0]
                                if not persona.es_administrativo() and not persona.es_profesor():
                                    if persona.es_estudiante():
                                        return JsonResponse({"result": "bad", 'mensaje': f'Estimad{"a" if persona.es_mujer() else "o"} para ingresar utilice perfil estudiante'})

                                if persona.tiene_perfil():
                                    app = 'sga'
                                    if persona.es_evaluador_externo_proyectos_investigacion() or persona.es_evaluador_externo_obras_relevancia() or persona.es_integrante_externo_proyecto_investigacion():
                                        app = 'investigacionevalproy'
                                    perfiles = persona.mis_perfilesusuarios_app(app)
                                    perfilprincipal = persona.perfilusuario_principal(perfiles, app)

                                    if not perfilprincipal:
                                        return JsonResponse({"result": "bad", 'mensaje': u'No existe un perfiles para esta aplicacion.'})

                                    request.session.set_expiry(240 * 60)
                                    request.session['login_manual'] = True
                                    login(request, user)
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
                                        nombresistema = eTemplateBaseSetting.name_system
                                    request.session['eTemplateBaseSetting'] = eTemplateBaseSetting
                                    request.session['nombresistema'] = nombresistema
                                    loglogin(action_flag=FLAG_SUCCESSFUL, action_app=APP_SGA, ip_private=capippriva,
                                             ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                             screen_size=screensize, user=user)
                                    if persona.administrativo_activo() or persona.es_profesor() or persona.es_administrador():
                                        if variable_valor('SEND_LOGIN_EMAIL_SGA') and not DEBUG:
                                            send_html_mail("Login exitoso SGA.", "emails/loginexito.html", {'sistema': request.session['nombresistema'], 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies, 'screensize': screensize, 't': miinstitucion()}, persona.emailinst, [], cuenta=CUENTAS_CORREOS[0][1])
                                    # if app != 'bolsa':
                                    #     if variable_valor('VALIDAR_LDAP') and not DEBUG:
                                    #         validar_ldap(request.POST['user'].lower(), request.POST['pass'],persona)

                                    # if perfilprincipal.es_profesor():
                                    #     profesor = perfilprincipal.profesor
                                    #     da = profesor.datos_habilitacion()
                                    #     da.habilitado = False
                                    # da.clavegenerada = profesor.generar_clave_notas()
                                    # da.save(request)
                                    # log(u'Perfil del profesor clave generada de notas en commoviews: %s [%s] - %s' % (profesor, profesor.id, da), request, "edit")
                                    #     pantalla de declaracion del usuario
                                    usuario = user
                                    if not UserAuth.objects.db_manager("sga_select").values("id").filter(usuario=usuario).exists():
                                        usermoodle = UserAuth(usuario=usuario)
                                        usermoodle.set_data()
                                        usermoodle.set_password(request.POST['pass'])
                                        usermoodle.save()
                                    else:
                                        usermoodle = UserAuth.objects.filter(usuario=usuario).first()
                                        if not usermoodle.check_password(request.POST['pass']) or usermoodle.check_data():
                                            if not usermoodle.check_password(request.POST['pass']):
                                                usermoodle.set_password(request.POST['pass'])
                                            usermoodle.save()
                                    url_redirect = request.POST.get('next', '/')
                                    return JsonResponse({"result": "ok", "sessionid": request.session.session_key, 'url_redirect': url_redirect})
                                else:
                                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existen perfiles activos.'})
                            else:
                                loglogin(action_flag=FLAG_UNKNOWN, action_app=APP_SGA, ip_private=capippriva,
                                         ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                         screen_size=screensize, change_message=u"USUARIO: %s - CLAVE: %s" % (request.POST['user'].lower().strip(), request.POST['pass']))
                                # log(u'Login fallido, no existe el usuario: %s' % request.POST['user'], request, "add")
                                return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existe el usuario.'})
                    else:
                        if not Persona.objects.filter(usuario__username=request.POST['user'].lower()).exists():
                            loglogin(action_flag=FLAG_UNKNOWN, action_app=APP_SGA, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, change_message=u"USUARIO: %s - CLAVE: %s" % (request.POST['user'].lower().strip(), request.POST['pass']))
                        if Persona.objects.db_manager("sga_select").filter(usuario__username=request.POST['user'].lower()).exists():
                            persona = Persona.objects.db_manager("sga_select").filter(usuario__username=request.POST['user'].lower())[0]
                            loglogin(action_flag=FLAG_FAILED, action_app=APP_SGA, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, user=persona.usuario, change_message=u"Clave Incorrecta")
                            if persona.es_administrativo() or persona.es_profesor() or persona.es_administrador():
                                send_html_mail("Login fallido SGA.", "emails/loginfallido.html", {'sistema': u'Sistema de Gestión Académica', 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies, 'screensize': screensize, 't': miinstitucion()}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[0][1])
                        return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, credenciales incorrectas.'})"""
                except Exception as ex:
                    # print(ex)
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, Error en el sistema.'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        # cache_page(60 * 15)
        if 'persona' in request.session:
            return HttpResponseRedirect("/")
        data = {"title": u"SGA - Iniciar Sesión", "background": random.randint(1, 2)}
        data['request'] = request
        data['info'] = request.GET['info'] if 'info' in request.GET else ''
        hoy = datetime.now().date()
        data['currenttime'] = datetime.now()
        data['aplicacion_estudiantes_android'] = URL_APLICACION_ESTUDIANTE_ANDROID
        data['aplicacion_estudiantes_ios'] = URL_APLICACION_ESTUDIANTE_IOS
        data['aplicacion_profesor_android'] = URL_APLICACION_PROFESOR_ANDROID
        data['declaracion_sga'] = DECLARACION_SGA
        data['contacto_email'] = CONTACTO_EMAIL
        data['validar_con_captcha'] = variable_valor('VALIDAR_CON_CAPTCHA_SGA')
        if data['validar_con_captcha']:
            if ip_whitelist_check(request, 'sga'):
                data['validar_con_captcha'] = False
            elif DEBUG:
                    data['validar_con_captcha'] = False

        data['server_response'] = SERVER_RESPONSE
        data['tipoentrada'] = request.session['tipoentrada'] = "SGA"
        data['public_key'] = variable_valor('GOOGLE_RECAPTCHA_PUBLIC_KEY')
        if variable_valor('ID_PERIODO_ADMISION_LOGIN'):
            data['id_periodo_admision'] = variable_valor('ID_PERIODO_ADMISION_LOGIN')
            data['nombre_priodo_admision'] = variable_valor('NOMBRE_PERIODO_ADMISION_LOGIN')
        data["next"] = request.GET.get('ret', False)
        data['DIA_CANCER_MAMA_19_OCTUBRE'] = variable_valor('DIA_CANCER_MAMA_19_OCTUBRE')
        data['DIA_DE_LA_MADRE'] = variable_valor('DIA_DE_LA_MADRE')
        data['LOGIN_GMAIL'] = variable_valor('LOGIN_GMAIL')
        data['CAROUSEL_LOGIN_IMG'] = variable_valor('CAROUSEL_LOGIN_IMG')
        data['SITE_URL_SIE'] = get_variable('SITE_URL_SIE')
        # data['faceid_access'] = ControlAccesoFaceId.objects.filter(status=True, activo=True, app=1).last()
        data['DEBUG'] = DEBUG
        return render(request, "login/loginsga.html", data)


# CIERRA LA SESSION DEL USUARIO
def logout_user(request):
    if 'tiposistema' in request.session:
        tipo = request.session['tiposistema']
        logout(request)
        return HttpResponseRedirect("/login" + tipo)
    else:
        logout(request)
        return HttpResponseRedirect("/loginsga")


# ADICIONA LOS DATOS DEL USUARIO A LA SESSION
def adduserdata(request, data, isPanel=False):
    # ADICIONA EL USUARIO A LA SESSION
    if 'persona' not in request.session:
        if not request.user.is_authenticated:
            raise Exception('Usuario no autentificado en el sistema')
        request.session['persona'] = Persona.objects.get(usuario=request.user)
    data['version_static'] = '23.0.1'
    data['persona'] = persona = request.session['persona']
    data['check_session'] = False
    data['server_response'] = SERVER_RESPONSE
    data['DEBUG'] = DEBUG
    tipoentrada = 'SGA'
    if 'tipoentrada' in request.session:
        data['tipoentrada'] = tipoentrada = request.session['tipoentrada'] if request.session['tipoentrada'] else "SGA"
    else:
        data['tipoentrada'] = tipoentrada = "SGA"
    if 'ultimo_acceso' not in request.session:
            request.session['ultimo_acceso'] = datetime.now()
    if request.method == 'GET':
        if 'ret' in request.GET:
            data['ret'] = request.GET['ret']
        if 'mensj' in request.GET:
            data['mensj'] = request.GET['mensj']
        if 'useModal' in request.GET:
            data['useModal'] = int(request.GET['useModal']) == 1
    data['nombresistema'] = request.session['nombresistema']
    data['tiposistema'] = request.session['tiposistema']
    data['currenttime'] = datetime.now()
    data['remotenameaddr'] = '%s' % (request.META['SERVER_NAME'])
    data['remoteaddr'] = '%s - %s' % (get_client_ip(request), request.META['SERVER_NAME'])
    data['pie_pagina_creative_common_licence'] = PIE_PAGINA_CREATIVE_COMMON_LICENCE
    data['chequear_correo'] = CHEQUEAR_CORREO
    eUser = persona.usuario
    request.user.is_superuser = False
    data['request'] = request
    data['info'] = request.GET['info'] if 'info' in request.GET else ''
    validateTwoStepAccess = False
    if 'validateTwoStepAccess' in request.session:
        validateTwoStepAccess = request.session['validateTwoStepAccess']
    if not validateTwoStepAccess:
        request.user.is_superuser = eUser.is_superuser
        data['request'] = request
        data['validateTwoStepAccess'] = validateTwoStepAccess
        data['permiteWebPush'] = permiteWebPush = variable_valor('PERMITE_WEBPUSH')
        if permiteWebPush:
            from sga.models import Notificacion
            fecha_ahora = datetime.now()
            qsnotification = Notificacion.objects.filter(status=True, leido=False, destinatario=persona, fecha_hora_visible__gte=fecha_ahora, app_label__icontains=tipoentrada).order_by('-pk')
            data['listnotification'] = qsnotification[:10]
            data['totnotification'] = len(qsnotification)
            if persona.es_asesor():
                qsnotificationasesor = Notificacion.objects.filter(status=True, leido=False, destinatario=persona,
                                                             fecha_hora_visible__gte=fecha_ahora,
                                                             app_label__icontains=tipoentrada,
                                                             titulo__in=['POSTULANTE ADMITIDO']).order_by('-pk')
                data['listnotificationasesor'] = qsnotificationasesor[:10]
                data['totnotificationasesor'] = len(qsnotificationasesor)
            # NOTIFICACIONES WEB
            webpush_settings = getattr(settings, 'WEBPUSH_SETTINGS', {})
            vapid_key = webpush_settings.get('VAPID_PUBLIC_KEY')
            data['vapid_key'] = vapid_key
        data['perfiles_usuario'] = request.session['perfiles']
        data['perfilprincipal'] = perfilprincipal = request.session['perfilprincipal']
        if 'periodos_todos' not in request.session:
            hace_tres_anios = datetime.now() - relativedelta(years=1)
            if request.user.is_superuser or request.user.has_perm('sga.puede_visible_periodo'):
                # request.session['periodos_todos'] = Periodo.objects.values("id", "nombre").all().order_by('-inicio')

                if request.user.is_superuser:
                    request.session['periodos_todos'] = Periodo.objects.filter(inicio__gte=hace_tres_anios.date()).order_by('-inicio')
                else:
                    periodos_1 = Periodo.objects.filter(inicio__gte=hace_tres_anios.date(), visible=True).order_by('-inicio').exclude(pk__in=PeriodoGrupo.objects.values_list('periodo_id', flat=True).filter(visible=True).distinct())
                    periodos_2 = Periodo.objects.filter(inicio__gte=hace_tres_anios.date(), pk__in=PeriodoGrupo.objects.values_list('periodo_id', flat=True).filter(grupos__in=request.user.groups.all())).order_by('-inicio')
                    periodos_3 = Periodo.objects.filter(inicio__gte=hace_tres_anios.date(), pk__in=PeriodoGrupo.objects.values_list('periodo_id', flat=True).filter(grupos__isnull=True)).order_by('-inicio')
                    request.session['periodos_todos'] = periodos_1 | periodos_2 | periodos_3
            else:
                periodos_1 = Periodo.objects.filter(inicio__gte=hace_tres_anios.date(), visible=True).order_by('-inicio').exclude(pk__in=PeriodoGrupo.objects.values_list('periodo_id', flat=True).filter(visible=True).distinct())
                periodos_2 = Periodo.objects.filter(inicio__gte=hace_tres_anios.date(), pk__in=PeriodoGrupo.objects.values_list('periodo_id', flat=True).filter(grupos__in=request.user.groups.all())).order_by('-inicio')
                periodos_3 = Periodo.objects.filter(inicio__gte=hace_tres_anios.date(), pk__in=PeriodoGrupo.objects.values_list('periodo_id', flat=True).filter(grupos__isnull=True)).order_by('-inicio')
                request.session['periodos_todos'] = periodos_1 | periodos_2 | periodos_3
                # request.session['periodos_todos'] = Periodo.objects.values("id", "nombre").filter(visible=True).order_by('-inicio')
        data['periodos_todos'] = periodos = request.session['periodos_todos']
        if 'grupos_usuarios' not in request.session:
            if perfilprincipal.es_profesor():
                request.session['grupos_usuarios'] = request.user.groups.filter(id=PROFESORES_GROUP_ID)
            elif perfilprincipal.es_estudiante():
                request.session['grupos_usuarios'] = request.user.groups.filter(id=ALUMNOS_GROUP_ID)
            else:
                request.session['grupos_usuarios'] = request.user.groups.exclude(id__in=[ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID])
        data['grupos_usuarios'] = request.session['grupos_usuarios']

        if perfilprincipal.es_estudiante():
            inscripcion = perfilprincipal.inscripcion

            if 'periodos_estudiante' not in request.session:
                request.session['periodos_estudiante'] = Periodo.objects.filter(nivel__matricula__inscripcion=inscripcion, status=True, nivel__status=True, nivel__matricula__status=True, nivel__matricula__inscripcion__status=True).order_by('-inicio')
            periodos_estudiante = request.session['periodos_estudiante']

            if 'matricula' not in request.session:
                request.session['matricula'] = inscripcion.matricula2()
            matricula = request.session['matricula']

            data['periodos'] = periodos_estudiante
            if matricula:
                if 'periodo' not in request.session:
                    request.session['periodo'] = matricula.nivel.periodo
            else:
                if 'ultimamatricula' not in request.session:
                    request.session['ultimamatricula'] = inscripcion.ultima_matricula()
                ultimamatricula = request.session['ultimamatricula']
                if ultimamatricula:
                    request.session['periodo'] = periodos_estudiante[0] if periodos_estudiante else None
                else:
                    data['periodos'] = None
                    request.session['periodo'] = None
            if 'coordinacion' not in request.session:
                request.session['coordinacion'] = inscripcion.carrera.coordinacion_set.values_list('id', flat=True)[0]
            data['periodo'] = periodo = request.session['periodo']
            lifetime = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
            if not 'eUserProfileChangeToken' in request.session:
                fecha = datetime.now().date()
                hora = datetime.now().time()
                fecha_hora = fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__()
                code = generate_code(32)
                token_access = md5(str(encrypt(persona.usuario.id) + fecha_hora).encode("utf-8")).hexdigest()
                UserToken.objects.filter(user=persona.usuario, action_type=4, app=4, usuario_creacion=persona.usuario).delete()
                eUserToken = UserToken(user=persona.usuario,
                                       token=token_access,
                                       action_type=4,
                                       date_expires=datetime.now() + lifetime,
                                       app=4,
                                       isActive=True
                                       )
                eUserToken.save(request)
                if not perfilprincipal:
                    raise NameError('No tiene perfil asignado')
                if not UserProfileChangeToken.objects.values("id").filter(perfil_origen__persona=persona, perfil_destino__persona=persona, app=4, isActive=True).exists():
                    eUserProfileChangeToken = UserProfileChangeToken(perfil_origen=perfilprincipal,
                                                                     perfil_destino=perfilprincipal,
                                                                     user_token=eUserToken,
                                                                     codigo=code,
                                                                     isActive=True,
                                                                     app=4,
                                                                     periodo=request.session['periodo']
                                                                     )
                    eUserProfileChangeToken.save(request)
                else:
                    eUserProfileChangeToken = UserProfileChangeToken.objects.filter(perfil_origen__persona=persona, perfil_destino__persona=persona, app=4, isActive=True)[0]
                    eUserProfileChangeToken.codigo = code
                    eUserProfileChangeToken.user_token = eUserToken
                    eUserProfileChangeToken.save(request)
                data['eUserProfileChangeToken'] = request.session['eUserProfileChangeToken'] = eUserProfileChangeToken
                data['connectionToken'] = request.session['connectionToken'] = f"{get_variable('SITE_URL_SIE')}/checktoken/{token_access}/{code}"
            else:
                eUserProfileChangeToken = request.session['eUserProfileChangeToken']
                if (eUserProfileChangeToken.perfil_origen != perfilprincipal or eUserProfileChangeToken.perfil_destino != perfilprincipal or eUserProfileChangeToken.periodo != periodo):
                    eUserProfileChangeToken = UserProfileChangeToken.objects.get(pk=eUserProfileChangeToken.pk)
                    code = generate_code(32)
                    eUserProfileChangeToken.perfil_origen = perfilprincipal
                    eUserProfileChangeToken.perfil_destino = perfilprincipal
                    eUserProfileChangeToken.periodo = periodo
                    eUserProfileChangeToken.codigo = code
                    eUserProfileChangeToken.isActive = True
                    eUserProfileChangeToken.save(request)
                    eUserToken = eUserProfileChangeToken.user_token
                    eUserToken.date_expires = datetime.now() + lifetime
                    eUserToken.isActive = True
                    eUserToken.save(request)
                    token_access = eUserToken.token
                    data['eUserProfileChangeToken'] = request.session['eUserProfileChangeToken'] = eUserProfileChangeToken
                    data['connectionToken'] = request.session['connectionToken'] = f"{get_variable('SITE_URL_SIE')}/checktoken/{token_access}/{code}"
                else:
                    if eUserProfileChangeToken.user_token.date_expires < datetime.now():
                        eUserProfileChangeToken = UserProfileChangeToken.objects.get(pk=eUserProfileChangeToken.pk)
                        code = generate_code(32)
                        eUserProfileChangeToken.codigo = code
                        eUserProfileChangeToken.isActive = True
                        eUserProfileChangeToken.save(request)
                        eUserToken = eUserProfileChangeToken.user_token
                        eUserToken.date_expires = datetime.now() + lifetime
                        eUserToken.isActive = True
                        eUserToken.save(request)
                        token_access = eUserToken.token
                        data['eUserProfileChangeToken'] = request.session['eUserProfileChangeToken'] = eUserProfileChangeToken
                        data['connectionToken'] = request.session['connectionToken'] = f"{get_variable('SITE_URL_SIE')}/checktoken/{token_access}/{code}"
        elif perfilprincipal.es_profesor():
            # listasalud = ProfesorMateria.objects.values_list('materia__nivel__periodo_id').filter(profesor__persona=persona, materia__nivel__nivellibrecoordinacion__coordinacion_id=1, materia__nivel__periodo_id=113).distinct()
            listasalud = ProfesorDistributivoHoras.objects.values_list('periodo__id').filter(profesor__persona=persona, coordinacion__id=1, periodo_id=113)
            periodoid = ProfesorDistributivoHoras.objects.values_list('periodo__id').filter(profesor__persona=persona, periodo__visible=True, periodo__status=True)
            if listasalud:
                periodoid = periodoid | listasalud
            periodosdocente = Periodo.objects.select_related('tipo').filter(activodocente=True, id__in=periodoid).order_by('-inicio')
            if periodosdocente:
                if 'periodo' not in request.session:
                    # request.session['periodo'] = periodosdocente[0]
                    # request.session['periodo'] = periodosdocente[0]
                    request.session['periodo'] = periodosdocente.filter(inicio__lte=datetime.now().date(), fin__gte=datetime.now().date()).order_by('-marcardefecto')[0] if periodosdocente.filter(inicio__lte=datetime.now().date(), fin__gte=datetime.now().date()).exists() else None
                    if not request.session['periodo']:
                        request.session['periodo'] = periodosdocente[0]
                else:
                    if request.session['periodo']:
                        request.session['periodo'] = Periodo.objects.get(pk=request.session['periodo'].id)
                data['periodos'] = periodosdocente
                request.session['periodos'] = periodosdocente
            else:
                data['periodos'] = None
                request.session['periodo'] = None
            data['periodo'] = request.session['periodo']
        else:
            data['periodos'] = periodos

        if 'periodo' not in request.session:
            if Periodo.objects.values('id').filter(tipo=TIPO_PERIODO_REGULAR, inicio__lte=datetime.now().date(), activo=True, fin__gte=datetime.now().date()).exists():
                if Periodo.objects.values('id').filter(tipo=TIPO_PERIODO_REGULAR, activo=True, inicio__lte=datetime.now().date(), fin__gte=datetime.now().date()).order_by('id').count()>1:
                    request.session['periodo'] = Periodo.objects.filter(tipo=TIPO_PERIODO_REGULAR, activo=True,marcardefecto=True, inicio__lte=datetime.now().date(),fin__gte=datetime.now().date()).order_by('id')[0] if Periodo.objects.filter(tipo=TIPO_PERIODO_REGULAR, activo=True,marcardefecto=True, inicio__lte=datetime.now().date(),fin__gte=datetime.now().date()).exists() else None
                else:
                    request.session['periodo'] = Periodo.objects.filter(tipo=TIPO_PERIODO_REGULAR, activo=True, inicio__lte=datetime.now().date(), fin__gte=datetime.now().date()).order_by('id')[0] if Periodo.objects.filter(tipo=TIPO_PERIODO_REGULAR, activo=True, inicio__lte=datetime.now().date(), fin__gte=datetime.now().date()).exists() else None
            else:
                request.session['periodo'] = None
            if not request.session['periodo']:
                if Periodo.objects.values('id').filter(tipo=TIPO_PERIODO_REGULAR, activo=True, inicio_agregacion__lte=datetime.now().date()).exists():
                    request.session['periodo'] = Periodo.objects.filter(tipo=TIPO_PERIODO_REGULAR, activo=True, inicio_agregacion__lte=datetime.now().date()).order_by('-inicio_agregacion')[0]
                elif Periodo.objects.values('id').filter(tipo=TIPO_PERIODO_REGULAR, activo=True, fin__lte=datetime.now().date()).exists():
                    # request.session['periodo'] = Periodo.objects.filter(tipo=TIPO_PERIODO_REGULAR, activo=True, fin__lte=datetime.now().date()).order_by('-id')[0]
                    request.session['periodo'] = Periodo.objects.filter(tipo=TIPO_PERIODO_REGULAR, activo=True, fin__lte=datetime.now().date()).order_by('-fin')[0]
                else:
                    request.session['periodo'] = Periodo.objects.filter(tipo=TIPO_PERIODO_REGULAR, activo=True).order_by('-fin')[0]
        data['periodo'] = request.session['periodo']
        if 'institucion' not in request.session:
            request.session['institucion'] = TituloInstitucion.objects.all()[0]
        data['institucion'] = request.session['institucion']
        if 'ruta' not in request.session:
            request.session['ruta'] = [['/', 'Inicio']]
        rutalista = request.session['ruta']
        if request.path and request.method == 'GET':
            if '/' in request.path[1:]:
                sp = request.path[1:].split('/')
                urlPath = sp[0]
            else:
                urlPath = request.path[1:]
            try:
                eModulo = Modulo.objects.get(url=urlPath)
                url = ['/' + eModulo.url, eModulo.nombre]
                if rutalista.count(url) <= 0:
                    if rutalista.__len__() >= 8:
                        b = rutalista[1]
                        rutalista.remove(b)
                        rutalista.append(url)
                    else:
                        rutalista.append(url)
                request.session['ruta'] = rutalista
                data["url_back"] = '/'
                url_back = [data['url_back']]
                request.session['url_back'] = url_back
            except ObjectDoesNotExist:
                pass
            # if Modulo.objects.values("id").filter(url=urlPath).exists():
            #     modulo = Modulo.objects.values("url", "nombre").filter(url=urlPath)[0]
            #     url = ['/' + modulo['url'], modulo['nombre']]
            #     if rutalista.count(url) <= 0:
            #         if rutalista.__len__() >= 8:
            #             b = rutalista[1]
            #             rutalista.remove(b)
            #             rutalista.append(url)
            #         else:
            #             rutalista.append(url)
            #     request.session['ruta'] = rutalista
            #     data["url_back"] = '/'
            #     url_back = [data['url_back']]
            #     request.session['url_back'] = url_back
        data["ruta"] = rutalista
        data['permite_modificar'] = True
        if data['tipoentrada'] == 'SGA' and WebSocket.objects.values('id').filter(habilitado=True, sga=True).exists():
            data['websocket'] = WebSocket.objects.filter(habilitado=True, sga=True).first()
        elif data['tipoentrada'] == 'SAGEST' and WebSocket.objects.values('id').filter(habilitado=True, sagest=True).exists():
            data['websocket'] = WebSocket.objects.filter(habilitado=True, sagest=True).first()
        elif data['tipoentrada'] == 'POSGRADO' and WebSocket.objects.values('id').filter(habilitado=True, posgrado=True).exists():
            data['websocket'] = WebSocket.objects.filter(habilitado=True, posgrado=True).first()
        elif data['tipoentrada'] == 'POSTULACIONPOSGRADO' and WebSocket.objects.values('id').filter(habilitado=True, postulacionposgrado=True).exists():
            data['websocket'] = WebSocket.objects.filter(habilitado=True, postulacionposgrado=True).first()
        elif data['tipoentrada'] == 'POSTULATE' and WebSocket.objects.values('id').filter(habilitado=True, postulacionposgrado=True).exists():
            data['websocket'] = WebSocket.objects.filter(habilitado=True, postulacionposgrado=True).first()
        elif data['tipoentrada'] == 'FORMACIONEJECUTIVA' and WebSocket.objects.values('id').filter(habilitado=True, postulacionposgrado=True).exists():
            data['websocket'] = WebSocket.objects.filter(habilitado=True, postulacionposgrado=True).first()
        else:
            data['websocket'] = None
        data['eTemplateBaseSetting'] = eTemplateBaseSetting = request.session['eTemplateBaseSetting'] if 'eTemplateBaseSetting' in request.session and request.session['eTemplateBaseSetting'] else None
        modulos_favoritos = None
        ids_modulos_favoritos = []
        if eTemplateBaseSetting and request.method == 'GET':
            if eTemplateBaseSetting.use_menu_favorite_module:
                if MenuFavoriteProfile.objects.values("id").filter(setting=eTemplateBaseSetting, profile=perfilprincipal).exists():
                    eMenuFavoriteProfile = MenuFavoriteProfile.objects.filter(setting=eTemplateBaseSetting, profile=perfilprincipal)[0]
                    ids_modulos_favoritos = eMenuFavoriteProfile.mis_modulos_id()
                    modulos_favoritos = eMenuFavoriteProfile.mis_modulos()
        data['ids_modulos_favoritos'] = ids_modulos_favoritos
        data['modulos_favoritos'] = modulos_favoritos
    if not DEBUG:
        if variable_valor('HABILITAR_REGISTRO_CLIC'):
            action_registre_log_clic_commonviews(request)



# FUNCION GLOBAL DE NOTIFICACIONES:
def traerNotificaciones(request, data, persona):
    from django.template.loader import render_to_string
    from sga.models import Notificacion
    qsnoti = Notificacion.objects.filter(status=True, leido=False, destinatario=persona, tipo=2).order_by('-pk')
    datosBtn = {"totalnot": qsnoti.count(), "notificaciones": qsnoti[:5],}
    return render_to_string('btnNotificaciones.html', datosBtn)


# PANEL PRINCIPAL DEL SISTEMA
def traerNotificaciones2(persona):
    from django.template.loader import render_to_string
    from sga.models import Notificacion
    qsnoti = Notificacion.objects.filter(status=True, leido=False, destinatario=persona, tipo=2).order_by('-pk')
    datosBtn = {"totalnot": qsnoti.count(), "notificaciones": qsnoti[:5],}
    return render_to_string('btnNotificaciones.html', datosBtn)


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
# @cache_page(0)
def panel(request):
    data = {}
    adduserdata(request, data, True)
    persona = request.session['persona']
    UTILIZA_MODULO_BIBLIOTECA = variable_valor('UTILIZA_MODULO_BIBLIOTECA')
    perfilprincipal = request.session['perfilprincipal']
    es_estudiante = perfilprincipal.es_estudiante()

    es_profesor = perfilprincipal.es_profesor()
    es_administrativo = perfilprincipal.es_administrativo()
    # if not es_estudiante and not es_profesor and not es_administrativo and persona.es_empleador():
    #     return HttpResponseRedirect('/bolsalaboral')
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'fintour':
                try:
                    with transaction.atomic():
                        per_ = Persona.objects.get(pk=persona.id)
                        per_.visualizar_tutorial = False
                        per_.save(request)
                        log(u'Finalizo el tour inicial: %s' % per_, request, "edit")
                        return JsonResponse({'error': False}, safe=False)
                except Exception as ex:
                    return JsonResponse({'error': True, "message": "Error: {}".format(ex)}, safe=False)

            elif action == 'lista_periodos':
                try:
                    from django.template.loader import get_template
                    data['title'] = u"Periodos académicos"
                    ePeriodos = Periodo.objects.none()
                    if perfilprincipal.es_estudiante():
                        inscripcion = perfilprincipal.inscripcion
                        ePeriodos = Periodo.objects.filter(nivel__matricula__inscripcion=inscripcion, status=True, nivel__status=True, nivel__matricula__status=True, nivel__matricula__inscripcion__status=True).order_by('-inicio')
                    elif perfilprincipal.es_profesor():
                        listasalud = ProfesorDistributivoHoras.objects.values_list('periodo__id').filter(profesor__persona=persona, coordinacion__id=1, periodo_id=113)
                        periodoid = ProfesorDistributivoHoras.objects.values_list('periodo__id').filter(profesor__persona=persona, periodo__visible=True, periodo__status=True)
                        if listasalud:
                            periodoid = periodoid | listasalud
                        ePeriodos = Periodo.objects.select_related('tipo').filter(activodocente=True, id__in=periodoid).order_by('-inicio')
                    else:
                        if request.user.is_superuser or request.user.has_perm('sga.puede_visible_periodo'):
                            if request.user.is_superuser:
                                ePeriodos = Periodo.objects.filter(status=True).order_by('-inicio')
                            else:
                                periodos_1 = Periodo.objects.filter(status=True, visible=True).exclude(pk__in=PeriodoGrupo.objects.values_list('periodo_id', flat=True).filter(visible=True).distinct()).order_by('-inicio')
                                periodos_2 = Periodo.objects.filter(pk__in=PeriodoGrupo.objects.values_list('periodo_id', flat=True).filter(grupos__in=request.user.groups.all())).order_by('-inicio')
                                periodos_3 = Periodo.objects.filter(pk__in=PeriodoGrupo.objects.values_list('periodo_id', flat=True).filter(grupos__isnull=True)).order_by('-inicio')
                                ePeriodos = periodos_1 | periodos_2 | periodos_3
                        else:
                            periodos_1 = Periodo.objects.filter(visible=True).exclude(pk__in=PeriodoGrupo.objects.values_list('periodo_id', flat=True).filter(visible=True).distinct()).order_by('-inicio')
                            periodos_2 = Periodo.objects.filter(pk__in=PeriodoGrupo.objects.values_list('periodo_id', flat=True).filter(grupos__in=request.user.groups.all())).order_by('-inicio')
                            periodos_3 = Periodo.objects.filter(pk__in=PeriodoGrupo.objects.values_list('periodo_id', flat=True).filter(grupos__isnull=True)).order_by('-inicio')
                            ePeriodos = periodos_1 | periodos_2 | periodos_3

                    data['ePeriodos'] = ePeriodos
                    template = get_template("panelperiodos.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': ex.__str__()})

            elif action == 'periodo':
                try:
                    request.session['periodo'] = periodo = Periodo.objects.get(pk=int(encrypt(request.POST['id'])))
                    lifetime = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
                    if 'eUserProfileChangeToken' in request.session:
                        eUserProfileChangeToken = request.session['eUserProfileChangeToken']
                        eUserProfileChangeToken = UserProfileChangeToken.objects.get(pk=eUserProfileChangeToken.pk)
                        code = generate_code(32)
                        eUserProfileChangeToken.perfil_origen = perfilprincipal
                        eUserProfileChangeToken.perfil_destino = perfilprincipal
                        eUserProfileChangeToken.periodo = periodo
                        eUserProfileChangeToken.codigo = code
                        eUserProfileChangeToken.isActive = True
                        eUserProfileChangeToken.save(request)
                        eUserToken = eUserProfileChangeToken.user_token
                        eUserToken.date_expires = datetime.now() + lifetime
                        eUserToken.isActive = True
                        eUserToken.save(request)
                        token_access = eUserToken.token
                        request.session['eUserProfileChangeToken'] = eUserProfileChangeToken
                        request.session['connectionToken'] = f"{get_variable('SITE_URL_SIE')}/checktoken/{token_access}/{code}"
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'RegisterPoll':
                try:
                    persona = request.session['persona']
                    id = request.POST['id']
                    persona_ = Persona.objects.get(pk=int(id))
                    encuesta = EncuestaFormsGoogle.objects.get(pk=1)
                    reg = EncuestaFormsGoogleInscripcion(encuesta=encuesta,
                                                         persona=persona_,
                                                         fecha=datetime.now())
                    reg.save(request)
                    log(u'Realizo la encuesta: %s' % encuesta, request, "add")

                    return JsonResponse({"result": "ok", "mensaje": u"Se registro la encuesta"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Clave anterior no coincide."})

            elif action == 'actualizarlocalizacionpersona':
                try:
                    persona = request.session['persona']

                    if 'pais' in request.POST:
                        persona.pais_id = int(request.POST['pais'])

                    persona.provincia_id = int(request.POST['provincia'])
                    persona.canton_id = int(request.POST['canton'] if 'canton' in request.POST and request.POST['canton'] else None)
                    persona.parroquia_id = int(request.POST['parroquia'] if 'parroquia' in request.POST and request.POST['parroquia'] else None)
                    persona.sector = request.POST['sector'].strip().upper()
                    persona.num_direccion = request.POST['numerocasa'].strip().upper()
                    persona.direccion = request.POST['direccion1'].strip().upper()
                    persona.direccion2 = request.POST['direccion2'].strip().upper()
                    persona.referencia = request.POST['referencia'].strip().upper()
                    persona.telefono_conv = request.POST['telefono'].strip().upper()
                    persona.telefono = request.POST['celular'].strip().upper()
                    persona.tipocelular = int(request.POST['operadora'])
                    persona.localizacionactualizada = True
                    persona.save(request)

                    log(u'Actualizó datos de localización de la persona: %s' % persona, request, "edit")
                    # return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    # return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                return HttpResponseRedirect("/")

            elif action == 'subirdocumentocedula':
                try:
                    documentos = persona.documentos_personales()

                    f = PersonaSubirCedulaForm(request.POST, request.FILES)

                    if 'cedula' in request.FILES:
                        arch = request.FILES['cedula']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. (Cédula de ciudadanía)"})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf (Cédula de ciudadanía)"})

                    if 'papeleta' in request.FILES:
                        arch = request.FILES['papeleta']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb. (Papeleta de votación)"})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf (Papeleta de votación)"})

                    if f.is_valid():
                        newfile = request.FILES['cedula']
                        newfile._name = generar_nombre("cedula", newfile._name)

                        newfile2 = request.FILES['papeleta']
                        newfile2._name = generar_nombre("papeleta", newfile2._name)

                        if documentos is None:
                            documentos = PersonaDocumentoPersonal(persona=persona,
                                                                  cedula=newfile,
                                                                  estadocedula=1,
                                                                  papeleta=newfile2,
                                                                  estadopapeleta=1,
                                                                  actualizadouath=True,
                                                                  observacion=""
                                                                  )
                        else:
                            documentos.cedula = newfile
                            documentos.estadocedula = 1
                            documentos.papeleta = newfile2
                            documentos.estadopapeleta = 1
                            documentos.actualizadouath = True
                            documentos.observacion = ""

                        documentos.save(request)
                        log(u'Agregó documentos cédula y papeleta de votación: %s' % (persona), request, "add")
                        return JsonResponse({"result": False})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

            elif action == 'reservalibro':
                try:
                    documento = Documento.objects.get(pk=request.POST['id'])
                    if not (documento.disponibilidad_reserva() > int(documento.copias_total() / 2) and documento.copias_total() > 1):
                        return JsonResponse({'result': 'bad', 'mensaje': u'No existen copias disponibles.'})
                    if persona.documentos_reservados().count() >= 3:
                        return JsonResponse({'result': 'bad', 'mensaje': u'Usted tiene el maximo de reservas permitidas.'})
                    if persona.documentos_reservados().filter(documento=documento).exists():
                        return JsonResponse({'result': 'bad', 'mensaje': u'Usted tiene una reserva sobre este libro.'})
                    reserva = ReservaDocumento(documento=documento,
                                               persona=persona,
                                               fechareserva=datetime.now(),
                                               limitereserva=datetime.now() + timedelta(hours=24),
                                               entregado=False)
                    reserva.save()
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'rechazarmalla':
                try:
                    codigoinscripcion = Inscripcion.objects.get(pk=request.POST['codigoins'])
                    codigoinscripcion.confirmacion = True
                    codigoinscripcion.motivomalla = request.POST['idmotivo'].upper().strip()
                    codigoinscripcion.fechaconfirmacion = datetime.now().date()
                    codigoinscripcion.save(request)
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'aplicarmalla':
                try:
                    codigoinscripcion = Inscripcion.objects.get(pk=request.POST['codigoins'])
                    codigoinscripcion.confirmacion = True
                    codigoinscripcion.confirmarmatricula = True
                    codigoinscripcion.fechaconfirmacion = datetime.now().date()
                    # Desactivar perfil anterior
                    perfilaccesoanterior = PerfilUsuario.objects.get(persona=codigoinscripcion.persona, inscripcion=codigoinscripcion.inscripcionold, visible=True)
                    perfilaccesoanterior.visible = False
                    perfilaccesoanterior.save(request)
                    # Activar perfil actual
                    perfilacceso = PerfilUsuario.objects.get(persona=codigoinscripcion.persona, inscripcion=codigoinscripcion, visible=False)
                    perfilacceso.visible = True
                    perfilacceso.save(request)
                    codigoinscripcion.save(request)
                    return JsonResponse({'result': 'ok', "codigoperfilusuario": encrypt(perfilacceso.id) })
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'eliminarreservalibro':
                try:
                    reserva = ReservaDocumento.objects.get(pk=request.POST['id'])
                    reserva.anulado = True
                    reserva.save()
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'encuestamovilidad':
                try:
                    inscripcion = perfilprincipal.inscripcion

                    encuestamovilidad = EncuestaMovilidad(fecha=datetime.now().date(),
                                                          inscripcion=inscripcion,
                                                          aresp1=request.POST['respuesta1'],
                                                          aresp1otro=request.POST['respuesta1otro'],
                                                          aresp2=request.POST['respuesta2'],
                                                          aresp3=request.POST['respuesta3'],
                                                          aresp3otro=request.POST['respuesta3otro'],
                                                          aresp4=request.POST['respuesta4'],
                                                          sresp1=request.POST['respuesta5'],
                                                          sresp1otro=request.POST['respuesta5otro'],
                                                          sresp2=request.POST['respuesta6'],
                                                          sresp3=request.POST['respuesta7'],
                                                          sresp3otro=request.POST['respuesta7otro'],
                                                          sresp4=request.POST['respuesta8']
                                                          )
                    encuestamovilidad.save(request)
                except Exception as ex:
                    transaction.set_rollback(True)
                return HttpResponseRedirect("/")

            elif action == 'responder':
                try:
                    nummatricula = None
                    if es_estudiante:
                        inscripcion = perfilprincipal.inscripcion
                        if inscripcion.matricula_set.filter(estado_matricula__in=[2,3], cerrada=False, status=True):
                            nummatricula = inscripcion.matricula_set.filter(estado_matricula__in=[2,3], cerrada=False, status=True)[0]
                    encuesta = Encuesta.objects.get(pk=request.POST['id'])
                    respuesta = RespuestaEncuesta(encuesta=encuesta,
                                                  fecha=datetime.now().date(),
                                                  observacion=request.POST['obsg'],
                                                  matricula=nummatricula,
                                                  persona=persona)
                    respuesta.save(request)
                    for x, y in request.POST.items():
                        if len(x) > 5 and x[:5] == 'valor':
                            indicador = IndicadorAmbitoInstrumentoEvaluacion.objects.get(pk=x[5:])
                            valor = y
                            bandera=0
                            try:
                                valor = int(y)
                                bandera=1
                            except:
                                pass
                            if bandera==1:
                                tiporesp = Respuesta.objects.get(pk=valor)
                                dato = DatoRespuestaEncuesta(respuesta=respuesta,
                                                             indicador=indicador,
                                                             respuestapregunta=tiporesp,
                                                             observaciones=request.POST['obs' + x[5:]])
                            else:
                                dato = DatoRespuestaEncuesta(respuesta=respuesta,
                                                             indicador=indicador,
                                                             respuestapregunta=None,
                                                             respuestapreguntaabierta=valor,
                                                             observaciones=request.POST['obs' + x[5:]])
                            dato.save(request)
                except Exception as ex:
                    transaction.set_rollback(True)
                return HttpResponseRedirect("/")

            elif action == 'encuestagrupo':
                try:
                    encuesta = EncuestaGrupoEstudiantes.objects.get(pk=request.POST['id'])
                    if encuesta.tipoperfil == 4:
                        inscripcionencuesta = InscripcionEncuestaGrupoEstudiantes.objects.get(persona=persona, encuesta__tipoperfil=4, encuesta__activo=True, encuesta=encuesta, status=True)
                        inscripcionencuesta.respondio = True
                        inscripcionencuesta.save(request)
                    else:
                        if es_estudiante:
                            inscripcion = perfilprincipal.inscripcion
                            inscripcionencuesta = InscripcionEncuestaGrupoEstudiantes.objects.get(inscripcion=inscripcion, encuesta__tipoperfil=1, encuesta__activo=True, encuesta=encuesta, status=True)
                            inscripcionencuesta.respondio = True
                            inscripcionencuesta.save(request)

                        if es_profesor:
                            profesor = perfilprincipal.profesor
                            inscripcionencuesta = InscripcionEncuestaGrupoEstudiantes.objects.get(profesor=profesor, encuesta__tipoperfil=2, encuesta__activo=True, encuesta=encuesta, status=True)
                            inscripcionencuesta.respondio = True
                            inscripcionencuesta.save(request)

                        if es_administrativo:
                            administrativo = perfilprincipal.administrativo
                            inscripcionencuesta = InscripcionEncuestaGrupoEstudiantes.objects.get(administrativo=administrativo, encuesta__tipoperfil=3, encuesta__activo=True, encuesta=encuesta, status=True)
                            inscripcionencuesta.respondio = True
                            inscripcionencuesta.save(request)


                    for x, y in request.POST.items():
                        if x != 'id' and x != 'action' and x!= 'encuesta_completa' and x != 'csrfmiddlewaretoken':
                            rtipo = str(x).split("_")[0]
                            rpregunta = str(x).split("_")[1]
                            pregunta = PreguntaEncuestaGrupoEstudiantes.objects.get(pk=int(rpregunta))
                            if rtipo == 'cuadricula':
                                iditemfila = str(x).split("_")[2]
                                opcioncuadricula = OpcionCuadriculaEncuestaGrupoEstudiantes.objects.get(pk=int(iditemfila))
                                valorseleccionado = y
                                if OpcionCuadriculaEncuestaGrupoEstudiantes.objects.get(pregunta=pregunta, valor=y).opcotros:
                                    valorseleccionado = request.POST['respuestaotros_'+str(pregunta.pk)]
                                respcuadricula = RespuestaCuadriculaEncuestaGrupoEstudiantes(inscripcionencuesta=inscripcionencuesta,
                                                                                             pregunta=pregunta,
                                                                                             opcioncuadricula=opcioncuadricula,
                                                                                             respuesta=valorseleccionado
                                                                                             )

                                if OpcionCuadriculaEncuestaGrupoEstudiantes.objects.get(pregunta=pregunta, valor=y).oparchivo:
                                    archivo = request.FILES['respuestaarchivo_' + str(pregunta.pk)]
                                    nfile = archivo.name.split('.')
                                    if not nfile[-1] in ['pdf','jpeg','jpg','png']:
                                        raise NameError('Formato de archivo no permitido, se admite .pdf,.jpeg,.jpg,.png')
                                    respcuadricula.archivo = archivo
                                respcuadricula.save(request)
                            if rtipo == 'multiple':
                                iditemfila = str(x).split("_")[2]
                                opcionmultiple = OpcionMultipleEncuestaGrupoEstudiantes.objects.get(id=iditemfila)
                                valorseleccionado = y
                                if opcionmultiple.opcotros:
                                    valorseleccionado = request.POST['respuestaotros_'+str(pregunta.pk)]
                                respmultiple = RespuestaMultipleEncuestaGrupoEstudiantes(inscripcionencuesta=inscripcionencuesta,
                                                                                             pregunta=pregunta,
                                                                                             opcionmultiple=opcionmultiple,
                                                                                             respuesta=valorseleccionado
                                                                                             )
                                respmultiple.save(request)

                            if rtipo == 'respuestaotros':
                                try:
                                    iditemfila = str(x).split("_")[2]
                                    opcionmultiple = OpcionMultipleEncuestaGrupoEstudiantes.objects.get(id=iditemfila)
                                    valorseleccionado = y
                                    if opcionmultiple.opcotros:
                                        valorseleccionado = "otros: " + request.POST[
                                            'respuestaotros_' + str(pregunta.pk) + "_" + str(iditemfila)]
                                    respmultiple = RespuestaMultipleEncuestaGrupoEstudiantes(
                                        inscripcionencuesta=inscripcionencuesta,
                                        pregunta=pregunta,
                                        opcionmultiple=opcionmultiple,
                                        respuesta=valorseleccionado
                                        )
                                    respmultiple.save(request)
                                except Exception as ex:
                                    pass
                            else:
                                respuestapreguntaencuestagrupoestudiantes=RespuestaPreguntaEncuestaGrupoEstudiantes.objects.filter(inscripcionencuesta=inscripcionencuesta , pregunta=pregunta, status=True)
                                if respuestapreguntaencuestagrupoestudiantes:
                                    if rtipo == 'pregunta':
                                        respuestapreguntaencuestagrupoestudiantes[0].respuesta=y
                                    else:
                                        respuestapreguntaencuestagrupoestudiantes[0].respuestaporno = y
                                    respuestapreguntaencuestagrupoestudiantes[0].save(request)
                                else:
                                    if rtipo == 'pregunta':
                                        respuestapreguntaencuestagrupoestudiantes = RespuestaPreguntaEncuestaGrupoEstudiantes(inscripcionencuesta=inscripcionencuesta,
                                                                                                                              pregunta=pregunta,
                                                                                                                              respuesta=y)
                                    else:
                                        respuestapreguntaencuestagrupoestudiantes = RespuestaPreguntaEncuestaGrupoEstudiantes(inscripcionencuesta=inscripcionencuesta,
                                                                                                                              pregunta=pregunta,
                                                                                                                              respuestaporno=y)
                                    respuestapreguntaencuestagrupoestudiantes.save(request)
                    if encuesta.id == 15:
                        return HttpResponseRedirect("/alu_prematricula")
                except Exception as ex:
                    transaction.set_rollback(True)
                    messages.error(request,ex.__str__())
                return HttpResponseRedirect("/")

            elif action == 'addencuestagrupo':
                try:
                    encuesta = EncuestaGrupoEstudiantes.objects.get(pk=request.POST['id'])
                    listadorespuesta = request.POST['lista']
                    if encuesta.tipoperfil == 4:
                        persona = perfilprincipal
                        inscripcionencuesta = InscripcionEncuestaGrupoEstudiantes.objects.get(persona=persona, encuesta__tipoperfil=3, encuesta__activo=True, encuesta=encuesta, status=True)
                    if es_estudiante:
                        inscripcion = perfilprincipal.inscripcion
                        inscripcionencuesta = InscripcionEncuestaGrupoEstudiantes.objects.get(inscripcion=inscripcion, encuesta__tipoperfil=1, encuesta__activo=True, encuesta=encuesta, status=True)

                    if es_profesor:
                        profesor = perfilprincipal.profesor
                        inscripcionencuesta = InscripcionEncuestaGrupoEstudiantes.objects.get(profesor=profesor, encuesta__tipoperfil=2, encuesta__activo=True, encuesta=encuesta, status=True)

                    if es_administrativo:
                        administrativo = perfilprincipal.administrativo
                        inscripcionencuesta = InscripcionEncuestaGrupoEstudiantes.objects.get(administrativo=administrativo, encuesta__tipoperfil=3, encuesta__activo=True, encuesta=encuesta, status=True)

                    inscripcionencuesta.respondio = True
                    inscripcionencuesta.save(request)
                    for respuestas in listadorespuesta.split(","):
                        cadena = respuestas.split("_")
                        if cadena[0] == '2':
                            resprango = RespuestaRangoEncuestaGrupoEstudiantes(inscripcionencuesta=inscripcionencuesta,
                                                                               pregunta_id=cadena[1],
                                                                               opcionrango_id=cadena[2])
                            resprango.save(request)
                        if cadena[0] == '6':
                            respmultiple = RespuestaMultipleEncuestaGrupoEstudiantes(inscripcionencuesta=inscripcionencuesta,
                                                                                     pregunta_id=cadena[1],
                                                                                     opcionmultiple_id=cadena[2])
                            respmultiple.save(request)
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)

            # elif action == 'addaplicaroferta':
            #     try:
            #         perfilprincipal = request.session['perfilprincipal']
            #         if es_estudiante:
            #             inscripcion = perfilprincipal.inscripcion
            #             oferta = OfertasPracticas.objects.get(pk=request.POST['id'])
            #             if not oferta.tieneinscripcion(inscripcion):
            #                 inscriofe=OfertasPracticasInscripciones(oferta=oferta,inscripcion=inscripcion )
            #                 inscriofe.save(request)
            #                 cupoant=oferta.cupos
            #                 oferta.cupos=cupoant-1
            #                 oferta.save(request)
            #                 return JsonResponse({'result': 'ok'})
            #             else:
            #                 return JsonResponse({"result": "bad", "mensaje": u"Ya esta Inscrito."})
            #     except Exception as ex:
            #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'confirmar_enmcuesta':
                try:
                    if 'id' in request.POST:
                        if not PersonaConfirmarEncuesta.objects.filter(publicarenlace_id=int(request.POST['id']), persona_id=persona.id).exists():
                            conf = PersonaConfirmarEncuesta(publicarenlace_id=int(request.POST['id']), persona_id=persona.id)
                            conf.save(request)
                            return JsonResponse({'result': 'ok'})
                        else:
                            return JsonResponse({"result": "bad", 'mensaje': u'Ya se a registrado su encuesta.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, Error en el sistema.'})

            elif action == 'preinscripcionppp':
                try:
                    if 'idp' in request.POST and 'id' in request.POST:
                        inscripcion = Inscripcion.objects.get(id=int(request.POST['id']))
                        for i in json.loads(request.POST['listapreinscripcion']):
                            detalle = DetallePreInscripcionPracticasPP(preinscripcion_id= int(request.POST['idp']),
                                                                       inscripcion=inscripcion,
                                                                       itinerariomalla_id=None if int(i)==0 else int(i),
                                                                       estado=1,
                                                                       fecha=datetime.now())
                            detalle.save(request)
                        lr = json.loads(request.POST['listarespuesta'])
                        if len(lr)>0:
                            if not DetalleRespuestaPreInscripcionPPP.objects.filter(status=True, preinscripcion_id=int(request.POST['idp']), inscripcion=inscripcion).exists():
                                lista = []
                                for r in json.loads(request.POST['listarespuesta']):
                                    lista.append(int(r[1]))
                                resp = RespuestaPreInscripcionPracticasPP.objects.filter(status=True, id__in=lista)
                                res = DetalleRespuestaPreInscripcionPPP(preinscripcion_id=int(request.POST['idp']), inscripcion=inscripcion)
                                res.save(request)
                                res.respuesta=resp
                                res.save(request)
                        return JsonResponse({'result': 'ok'})
                    else:
                        return JsonResponse({"result": "bad", 'mensaje': u'Error al guardar los datos.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", 'mensaje': u'Error al obtener los datos.'})

            elif action == 'conflictohorario':
                try:
                    from itertools import chain
                    mispracticas = json.loads(request.POST['mispracticas'])
                    periodo = request.session['periodo']
                    inscripcion = perfilprincipal.inscripcion
                    matricula = inscripcion.matricula_periodo(periodo)
                    conflicto = conflicto_estudiante_conpracticas_seleccionadas(matricula, mispracticas)
                    if conflicto:
                        return JsonResponse({"result": "bad", "mensaje": conflicto})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", 'mensaje': u'Error al verificar conflicto de horario.'})

            elif action == 'aceptopractica':
                try:
                    horario = int(request.POST['horario'])
                    inscripcion = perfilprincipal.inscripcion
                    if inscripcion.comunicado == True:
                        confirmacion = ConfirmacionPracticasInscripcion(inscripcion=inscripcion,acepto=True, horario=horario)
                        confirmacion.save()
                        inscripcion.comunicado = False
                        inscripcion.save()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", 'mensaje': u'Error al guardar los datos.'})

            elif action == 'noaceptopractica':
                try:
                    inscripcion = perfilprincipal.inscripcion
                    if inscripcion.comunicado == True:
                        confirmacion = ConfirmacionPracticasInscripcion(inscripcion=inscripcion, acepto=False)
                        confirmacion.save()
                        inscripcion.comunicado = False
                        inscripcion.save()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", 'mensaje': u'Error al matricular estudiante.'})

            elif action == 'ingreso_sugerencia':
                try:
                    id_sugerencia_admision = request.POST['id_sugerencia_admision']
                    periodo = request.session['periodo']
                    if perfilprincipal.inscripcion.matricula_admision_virtual(periodo):
                        matricula = perfilprincipal.inscripcion.matricula_admision_virtual(periodo)
                        if matricula:
                            if matricula.puede_sugerencia():
                                sugerencia = matricula.puede_sugerencia()
                                sugerencia.observaciones = id_sugerencia_admision
                                sugerencia.fecha = datetime.now()
                                sugerencia.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", 'mensaje': u'Error al guardar los datos.'})

            elif action == 'ingreso_encuesta_tecnologica_presencial':
                try:
                    from sga.models import EncuestaTecnologica,PreguntaEncuestaTecnologica
                    respuestas = json.loads(request.POST['lista_items1'])
                    periodo = request.session['periodo']
                    if perfilprincipal.inscripcion.matricula_admision_virtual(periodo):
                        matricula = perfilprincipal.inscripcion.matricula_admision_virtual(periodo)
                        if matricula:
                            for r in respuestas:
                                pregunta = PreguntaEncuestaTecnologica.objects.filter(status=True,id=int(r['idp']) )[0]
                                res = int(r['res'])
                                if pregunta.tipo == 1:
                                    encuesta = EncuestaTecnologica(
                                        matricula=matricula,
                                        pregunta=pregunta,
                                        respuestasino=res
                                    )
                                    encuesta.save(request)
                                elif pregunta.tipo == 2:
                                    encuesta = EncuestaTecnologica(
                                        matricula=matricula,
                                        pregunta=pregunta,
                                        respuestarango=res
                                    )
                                    encuesta.save(request)
                                elif pregunta.tipo == 3:
                                    encuesta = EncuestaTecnologica(
                                        matricula=matricula,
                                        pregunta=pregunta,
                                        descripcion=res
                                    )
                                    encuesta.save(request)
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", 'mensaje': u'Error al guardar los datos.'})

            elif action == 'ingreso_encuesta_tecnologica_virtual':
                try:
                    from sga.models import EncuestaTecnologica
                    respuesta1 = request.POST['respuesta1']
                    respuesta2 = request.POST['respuesta2']
                    respuesta3 = request.POST['respuesta3']
                    respuesta4 = request.POST['respuesta4']
                    periodo = request.session['periodo']
                    if perfilprincipal.inscripcion.matricula_admision_virtual(periodo):
                        matricula = perfilprincipal.inscripcion.matricula_admision_virtual(periodo)
                        if matricula:
                            encuesta = EncuestaTecnologica(
                                inscripcion=perfilprincipal.inscripcion,
                                pregunta_id=1,
                                respuestarango=respuesta1
                            )
                            encuesta.save(request)

                            encuesta = EncuestaTecnologica(
                                inscripcion=perfilprincipal.inscripcion,
                                pregunta_id=2,
                                respuestasino=respuesta2)
                            encuesta.save(request)

                            encuesta = EncuestaTecnologica(
                                inscripcion=perfilprincipal.inscripcion,
                                pregunta_id=6,
                                respuestasino=respuesta3)
                            encuesta.save(request)

                            encuesta = EncuestaTecnologica(
                                inscripcion=perfilprincipal.inscripcion,
                                pregunta_id=7,
                                respuestasino=respuesta4)
                            encuesta.save(request)

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", 'mensaje': u'Error al guardar los datos.'})

            elif action == 'actualizarlocalidad':
                from sga.forms import ActualizacionLocalidadPersonaPadron
                try:
                    form = ActualizacionLocalidadPersonaPadron(request.POST)
                    if form.is_valid():
                        persona.telefono = str(form.cleaned_data['telefono'])
                        persona.email = form.cleaned_data['email']
                        persona.pais = form.cleaned_data['pais']
                        persona.provincia = form.cleaned_data['provincia']
                        persona.canton = form.cleaned_data['canton']
                        persona.parroquia = form.cleaned_data['parroquia']
                        persona.sector = form.cleaned_data['sector']
                        persona.direccion = form.cleaned_data['direccion']
                        persona.direccion2 = form.cleaned_data['direccion2']
                        persona.referencia = form.cleaned_data['referencia']
                        persona.ciudadela = form.cleaned_data['ciudadela']
                        persona.save(request)
                        if variable_valor('ACTUALIZACION_LOCALIDAD_MAPA'):
                            if 'latitud' in request.POST and 'longitud' in request.POST:
                                if request.POST['latitud'] == '' or request.POST['latitud'] == None:
                                    return JsonResponse({"result": True, "mensaje": u"Debe marcar su ubicación actual en el mapa para continuar con esta operación."})
                                if request.POST['longitud'] == '' or request.POST['longitud'] == None:
                                    return JsonResponse({"result": True, "mensaje": u"Debe marcar su ubicación actual en el mapa para continuar con esta operación."})
                                if not UbicacionPersona.objects.filter(persona=persona, latitud=request.POST['latitud'], longitud=request.POST['longitud']).exists():
                                    UbicacionPersona.objects.filter(persona=persona).update(actual=False)
                                    nuevaUbi = UbicacionPersona(persona=persona, latitud=request.POST['latitud'], longitud=request.POST['longitud'], actual=True)
                                    nuevaUbi.save(request)
                        persona.localizacionactualizada = True
                        persona.save(request)
                        log(u'Actualizo información de localidad : %s' % (persona), request, "add")
                        return JsonResponse({"result": False, 'mensaje': 'INFORMACIÓN ACTUALIZADA', 'modalsuccess': True}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()], "mensaje": "Error en el formulario" })
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": u"Error al obtener los datos. {}".format(ex)})

            elif action == 'confirmacionSedeElectoral':
                try:
                    if request.POST['idsede']:
                        idsede = int(request.POST['idsede'])
                        idperiodoelectoral = int(encrypt(request.POST['periodoelectoral']))
                        if es_estudiante:
                            if idsede > 0:
                                periodoelectoral = CabPadronElectoral.objects.get(pk=idperiodoelectoral)
                                sedeelectoral = SedesElectoralesPeriodo.objects.get(pk=idsede)
                                getmatricula= Matricula.objects.select_related('inscripcion').filter(status=True, inscripcion__persona=persona, nivel__periodo=periodoelectoral.periodo, cerrada=False).first()
                                persede = PersonasSede(persona=persona,
                                                       sede=sedeelectoral,
                                                       canton=persona.canton,
                                                       perfil=perfilprincipal,
                                                       matricula=getmatricula,
                                                       inscripcion=perfilprincipal.inscripcion)
                                persede.save(request)
                                log(u'Confirmo Lugar de Votación: %s' % (persede), request, "add")
                                return JsonResponse({"result": False, 'mensaje': 'LUGAR DE VOTACIÓN CONFIRMADO\n CANTÓN: {}\n PROVINCIA: {}'.format(sedeelectoral.canton.nombre, sedeelectoral.canton.provincia.nombre), 'modalsuccess': True}, safe=False)
                            else:
                                return JsonResponse({'result': True, "mensaje": "Debe seleccionar un lugar de votación" })
                        else:
                            return JsonResponse({'result': True, "mensaje": "Su perfil actual debe ser de estudiante"})
                    else:
                        return JsonResponse({'result': True, "mensaje": "Debe seleccionar un lugar de votación" })
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": u"Error al obtener los datos. {}".format(ex)})

            elif action == 'editSedeElectoral':
                try:
                    if request.POST['idsede']:
                        idsede = int(request.POST['idsede'])
                        id = int(encrypt(request.POST['id']))
                        if idsede > 0:
                            sedeelectoral = SedesElectoralesPeriodo.objects.get(pk=idsede)
                            persede = PersonasSede.objects.get(pk=id)
                            persede.sede = sedeelectoral
                            persede.canton = persona.canton
                            persede.save(request)
                            log(u'Edito Lugar de Votación: %s' % (persede), request, "edit")
                            return JsonResponse({"result": False, 'mensaje': 'LUGAR DE VOTACIÓN CONFIRMADO\n CANTÓN: {}\n PROVINCIA: {}'.format(sedeelectoral.canton.nombre, sedeelectoral.canton.provincia.nombre), 'modalsuccess': True}, safe=False)
                        else:
                            return JsonResponse({'result': True, "mensaje": "Debe seleccionar un lugar de votación"})
                    else:
                        return JsonResponse({'result': True, "mensaje": "Debe seleccionar un lugar de votación" })
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": u"Error al obtener los datos. {}".format(ex)})

            elif action == 'saveFavoriteMenu':
                try:
                    if not 'idm' in request.POST:
                        raise NameError(u"Parameto de modulo no encontrado")
                    idm = int(request.POST['idm'])
                    if not Modulo.objects.values("id").filter(pk=idm).exists():
                        raise NameError(u"Modulo no encontrado")
                    eModulo = Modulo.objects.get(pk=idm)
                    if not 'value' in request.POST:
                        raise NameError(u"Parameto de valor no encontrado")
                    """
                    * value = 1 => QUITAR MODULO DE FAVORITOS
                    * value = 0 => AGREGAR MODULO DE FAVORITOS
                    """
                    value = int(request.POST['value'])
                    eTemplateBaseSetting = request.session['eTemplateBaseSetting']
                    if MenuFavoriteProfile.objects.values("id").filter(setting=eTemplateBaseSetting, profile=perfilprincipal).exists():
                        eMenuFavoriteProfile = MenuFavoriteProfile.objects.filter(setting=eTemplateBaseSetting, profile=perfilprincipal)[0]
                    else:
                        eMenuFavoriteProfile = MenuFavoriteProfile(setting=eTemplateBaseSetting,
                                                                   profile=perfilprincipal)
                        eMenuFavoriteProfile.save(request)
                    modulos_ids = eMenuFavoriteProfile.mis_modulos_id()
                    if value == 1:
                        if eModulo.id in modulos_ids:
                            eMenuFavoriteProfile.modules.remove(eModulo.id)
                            log(u'Quito modulo favorito: %s de la APP: %s' % (eModulo, eMenuFavoriteProfile.setting), request, "del")
                    else:
                        if not modulos_ids:
                            eMenuFavoriteProfile.modules.add(eModulo.id)
                            log(u'Agrego modulo favorito: %s de la APP: %s' % (eModulo, eMenuFavoriteProfile.setting), request, "add")
                        else:
                            if eMenuFavoriteProfile.mis_modulos().count() > 100:
                                raise NameError(u"Limite de seleccionar módulos favorito es de %s" % str(100))
                            elif not eModulo.id in modulos_ids:
                                eMenuFavoriteProfile.modules.add(eModulo.id)
                                log(u'Agrego modulo favorito: %s de la APP: %s' % (eModulo, eMenuFavoriteProfile.setting), request, "add")

                    return JsonResponse({'result': "ok", "mensaje": u"¡Has quitado un módulo de tus favoritos!" if value == 1 else u"¡Has agregado un módulo a tus favoritos!"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. {}".format(ex.__str__())})

            elif action == 'saveInsignia':
                try:
                    id = encrypt(request.POST['id'])
                    if InsigniaPersona.objects.values('id').filter(status=True,persona=persona,visto=False,id=int(id)).exists():
                        insignia = InsigniaPersona.objects.get(status=True,persona=persona,visto=False,id=int(id))
                        insignia.visto = True
                        insignia.save(request)
                        log(u'Registro insignia nueva %s'%insignia,request,'edit')
                    return JsonResponse({'result':'ok','mensaje':u'¡Has agregado una nueva insignia!'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. {}".format(ex.__str__())})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        hoy = datetime.now()
        data['title'] = NOMBRE_INSTITUCION
        if variable_valor('REDIRECT_SIE') and es_estudiante:
            if 'eTemplateBaseSetting' in request.session:
                eTemplateBaseSetting = request.session['eTemplateBaseSetting']
                if eTemplateBaseSetting and eTemplateBaseSetting.use_api:
                    if 'connectionToken' in request.session:
                        connectionToken = request.session['connectionToken']
                        return redirect(f'{connectionToken}/')
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'encuestamovilidad':
                try:
                    # IMSM
                    # data['encuesta'] = encuesta = Encuesta.objects.get(pk=request.GET['id'])
                    # instrumento = encuesta.instrumento
                    # data['ambitos'] = instrumento.ambitoinstrumentoevaluacion_set.all()
                    # data['fecha'] = datetime.now()
                    # data['respuesta'] = None
                    # data['tiporespuesta'] = encuesta.tiporespuesta.respuesta_set.all()
                    # if RespuestaEncuesta.objects.filter(encuesta=encuesta, persona=data['persona']).exists():
                    #     data['respuesta'] = RespuestaEncuesta.objects.filter(encuesta=encuesta, persona=data['persona'])[0]
                    horaactual = datetime.now().time()
                    data['titulo'] = "Movilidad Estudiantil"
                    data['leyenda'] = "Encuesta sobre el uso del transporte que utilizan los estudiantes para el arribo y la salida de la Universidad Estatal de Milagro."

                    data['apregunta1'] = "¿Desde que lugar o ciudad sales para llegar a Unemi?"
                    data['arespuesta1'] = ((1,"MILAGRO"),
                                           (2,"GUAYAQUIL"),
                                           (3,"DURÁN"),
                                           (4,"NARANJITO"),
                                           (5,"MARCELINO MARIDUEÑA"),
                                           (6,"SIMÓN BOLIVAR"),
                                           (7,"YAGUACHI"),
                                           (8,"EL TRIUNFO"),
                                           (9,"LA TRONCAL"),
                                           (10,"VIRGEN DE FÁTIMA(KM26)"),
                                           (11,"MARISCAL SUCRE"),
                                           (12,"BUCAY"),
                                           (-1,"OTROS(ESPECIFIQUE)"),
                                           )

                    data['apregunta2'] = "¿Qué servicio de transporte utilizas?"
                    data['arespuesta2'] = ((1, "URBANO"),
                                           (2, "INTERCANTONAL"),
                                           (3, "INTERPROVINCIAL")
                                           )

                    data['apregunta3'] = "Seleccione la cooperativa de transporte:"
                    data['arespuesta3'] = ((1, "KM 26"),
                                           (2, "EXPRESO MILAGRO"),
                                           (3, "EJECUTIVO EXPRESS"),
                                           (4, "RUTAS MILAGREÑAS"),
                                           (5, "CITIM"),
                                           (6, "MARISCAL SUCRE"),
                                           (7, "COOP. CIUDAD DE MILAGRO"),
                                           (-1, "OTROS(ESPECIFIQUE)")
                                           )

                    data['apregunta4'] = "¿A qué hora sales de tu residencia para trasladarte a Unemi?"

                    data['spregunta1'] = "¿Cuál es tu lugar de destino?"
                    data['srespuesta1'] = ((1, "MILAGRO"),
                                           (2, "GUAYAQUIL"),
                                           (3, "DURÁN"),
                                           (4, "NARANJITO"),
                                           (5, "MARCELINO MARIDUEÑA"),
                                           (6, "SIMÓN BOLIVAR"),
                                           (7, "YAGUACHI"),
                                           (8, "EL TRIUNFO"),
                                           (9, "LA TRONCAL"),
                                           (10, "VIRGEN DE FÁTIMA(KM26)"),
                                           (11, "MARISCAL SUCRE"),
                                           (12, "BUCAY"),
                                           (-1, "OTROS(ESPECIFIQUE)"),
                                           )

                    data['spregunta2'] = "¿Qué servicio de transporte utilizas?"
                    data['srespuesta2'] = ((1, "URBANO"),
                                           (2, "INTERCANTONAL"),
                                           (3, "INTERPROVINCIAL")
                                           )

                    data['spregunta3'] = "Seleccione la cooperativa de transporte:"
                    data['srespuesta3'] = ((1, "KM 26"),
                                           (2, "EXPRESO MILAGRO"),
                                           (3, "EJECUTIVO EXPRESS"),
                                           (4, "RUTAS MILAGREÑAS"),
                                           (5, "CITIM"),
                                           (6, "MARISCAL SUCRE"),
                                           (7, "COOP. CIUDAD DE MILAGRO"),
                                           (-1, "OTROS(ESPECIFIQUE)")
                                           )
                    data['spregunta4'] = "¿A qué hora llegas a tu lugar de destino?"
                    data['horaactual'] = horaactual

                    return render(request, "encuestas/movilidadestudiantes.html", data)
                except Exception as ex:
                    pass

            elif action == 'responder':
                try:
                    # IMSM
                    data['encuesta'] = encuesta = Encuesta.objects.get(pk=request.GET['id'])
                    instrumento = encuesta.instrumento
                    data['ambitos'] = instrumento.ambitoinstrumentoevaluacion_set.all()
                    data['fecha'] = datetime.now()
                    data['respuesta'] = None
                    if encuesta.tiporespuesta:
                        data['tiporespuesta'] = encuesta.tiporespuesta.respuesta_set.all()
                    if RespuestaEncuesta.objects.filter(encuesta=encuesta, persona=data['persona']).exists():
                        data['respuesta'] = RespuestaEncuesta.objects.filter(encuesta=encuesta, persona=data['persona'])[0]
                    return render(request, "encuestas/responder.html", data)
                except Exception as ex:
                    pass

            elif action == 'encuestagrupo':
                try:
                    data['encuesta'] = encuesta = EncuestaGrupoEstudiantes.objects.get(pk=request.GET['id'])
                    data['preguntas'] = PreguntaEncuestaGrupoEstudiantes.objects.filter(encuesta=encuesta, status=True).order_by('orden')
                    data['fecha'] = datetime.now()
                    if encuesta.tipoencuesta == 1:
                        return render(request, "encuestas/encuestadinamicagrupo.html", data)
                    else:
                        return render(request, "encuestas/encuestagrupo.html", data)
                except Exception as ex:
                    pass

            elif action == 'subirdocumentocedula':
                try:
                    from django.template.loader import get_template
                    from django.template import Context
                    form = PersonaSubirCedulaForm()
                    data['title'] = u'Actualizar Documentos Personales'
                    data['form'] = form
                    data['action'] = action
                    template = get_template("th_hojavida/modal/fsubirdocumento.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'tareas_pendientes':
                try:
                    data['fecha'] = datetime.now()
                    if es_estudiante:
                        inscripcion = perfilprincipal.inscripcion
                        periodo = request.session['periodo']
                        matricula = inscripcion.matricula_periodo(periodo)
                        if not matricula.inscripcion.carrera_id == 7 and not matricula.inscripcion.coordinacion_id == 9 and not matricula.inscripcion.coordinacion_id == 7:
                            data['modulos_ingles_faltante'] = matricula.modulos_ingles_pendiente()
                            data['presentar_modulo_ingles'] = True
                        else:
                            data['presentar_modulo_ingles'] = False
                        data['tareas_pendientes'] = MateriaAsignadaPlanificacion.objects.filter(fechaentrega__isnull=True, planificacion__status=True, planificacion__desde__lte=hoy.date(), planificacion__hasta__gte=hoy.date(), materiaasignada__matricula__inscripcion=inscripcion, status=True).order_by("planificacion__hasta")
                    else:
                        data['tareas_pendientes'] = []
                    return render(request, "alu_documentos/tareaspendientes.html", data)
                except Exception as ex:
                    pass

            elif action == 'ofertas_practicas':
                try:
                    data['fecha'] = datetime.now()
                    if es_estudiante:
                        inscripcion = perfilprincipal.inscripcion
                        hoy = datetime.now()
                        data['ofertas_practicas'] = OfertasPracticas.objects.filter(carrera__id__in=[inscripcion.carrera.id],inicio__gte=hoy.date(), fin__lte=hoy.date(), status=True)
                    else:
                        data['ofertas_practicas'] = []
                    return render(request, "alu_documentos/ofertaspracticas.html", data)
                except Exception as ex:
                    pass

            elif action == 'selectpract':
                try:
                    from django.template.loader import get_template
                    from django.template import Context
                    data['materiasasignadas'] = []
                    data['inscripcion'] = []
                    tieneconflicto = None
                    if es_estudiante:
                        data['inscripcion'] = inscripcion = perfilprincipal.inscripcion
                        if inscripcion.carrera.id.__str__() in variable_valor('LISTA_CARRERA_PARA_MATRICULA_GRUPO_PRACTICA'):
                            periodo = request.session['periodo']
                            matricula = inscripcion.matricula_periodo(periodo)
                            if matricula:
                                # VERIFICAR CONFLICTO
                                materias = Materia.objects.filter(id__in=matricula.materiaasignada_set.values_list('materia__id').filter(sinasistencia=False),status=True)
                                alumnaspracticascongrupo = AlumnosPracticaMateria.objects.values_list('profesormateria__id', 'grupoprofesor__id').filter(materiaasignada__materia__id__in=materias.values_list('id'), materiaasignada__matricula=matricula, grupoprofesor__isnull=False)
                                data['tieneconflicto'] = conflicto_materias_estudiante(materias=materias, lista_pm_grupo=alumnaspracticascongrupo)
                                data['materiasasignadas'] = matricula.materiaasignada_set.filter(Q(sinasistencia=False), Q(materia__asignaturamalla__practicas=True), (Q(alumnospracticamateria__isnull=True) | Q(alumnospracticamateria__grupoprofesor__isnull=True)))
                    return render(request, "alu_documentos/seleccionpracticaspendientes.html", data)
                except Exception as ex:
                    pass

            elif action == 'aceptapractica':
                try:
                    from django.template.loader import get_template
                    from django.template import Context
                    perfilprincipal = request.session['perfilprincipal']
                    data['materiasasignadas'] = []
                    data['inscripcion'] = None
                    if es_estudiante:
                        data['inscripcion'] = inscripcion = perfilprincipal.inscripcion
                    return render(request, "alu_documentos/aceptapractica.html", data)
                except Exception as ex:
                    pass

            elif action == 'actualizarlocalidad':
                from django.template.loader import get_template
                from django.forms import model_to_dict
                from sga.forms import ActualizacionLocalidadPersonaPadron
                dictpersona = model_to_dict(persona)
                del dictpersona['pais']
                del dictpersona['provincia']
                del dictpersona['canton']
                del dictpersona['parroquia']
                form = ActualizacionLocalidadPersonaPadron(initial=dictpersona)
                form.fields['pais'].queryset = Pais.objects.none()
                form.fields['provincia'].queryset = Provincia.objects.none()
                form.fields['canton'].queryset = Canton.objects.none()
                form.fields['parroquia'].queryset = Parroquia.objects.none()
                data['form2'] = form
                data['actualizacion_localidad_con_mapa'] = variable_valor('ACTUALIZACION_LOCALIDAD_MAPA')
                template = get_template("adm_padronelectoral/modal/actualizarlocalizacionpersonaleatflet.html")
                return JsonResponse({"result": True, 'data': template.render(data)})

            elif action == 'actualizarlocalidadsinmapa':
                from django.template.loader import get_template
                from django.forms import model_to_dict
                from sga.forms import ActualizacionLocalidadPersonaPadron
                dictpersona = model_to_dict(persona)
                del dictpersona['pais']
                del dictpersona['provincia']
                del dictpersona['canton']
                del dictpersona['parroquia']
                form = ActualizacionLocalidadPersonaPadron(initial=dictpersona)
                form.fields['pais'].queryset = Pais.objects.none()
                form.fields['provincia'].queryset = Provincia.objects.none()
                form.fields['canton'].queryset = Canton.objects.none()
                form.fields['parroquia'].queryset = Parroquia.objects.none()
                data['form2'] = form
                template = get_template("adm_padronelectoral/modal/actualizarlocalizacionpersonasinmapa.html")
                return JsonResponse({"result": True, 'data': template.render(data)})

            elif action == 'confirmacionSedeElectoral':
                from django.template.loader import get_template
                from django.forms import model_to_dict
                from sga.forms import ActualizacionLocalidadPersonaPadron
                data['action'] = action
                padronelectoral = CabPadronElectoral.objects.filter(activo=True, status=True).first()
                if persona.canton:
                    if SedesElectoralesPeriodo.objects.filter(status=True, periodo=padronelectoral).filter(provincias__in=[persona.canton.provincia]).exists():
                        data['ubirecomendada'] = SedesElectoralesPeriodo.objects.filter(status=True, periodo=padronelectoral).filter(provincias__in=[persona.canton.provincia]).first()
                data['persona'] = persona
                data['padronelectoral'] = padronelectoral
                data['listadosedes'] = SedesElectoralesPeriodo.objects.filter(status=True, periodo=padronelectoral).order_by('canton__provincia__nombre')
                template = get_template("adm_padronelectoral/modal/elegirsede.html")
                return JsonResponse({"result": True, 'data': template.render(data)})

            elif action == 'editSedeElectoral':
                from django.template.loader import get_template
                from django.forms import model_to_dict
                from sga.forms import ActualizacionLocalidadPersonaPadron
                data['action'] = action
                padronelectoral = CabPadronElectoral.objects.filter(activo=True, status=True).first()
                data['id'] = idsede = int(encrypt(request.GET['idsede']))
                sedeubicada = PersonasSede.objects.get(pk=idsede)
                data['ubirecomendada'] = sedeubicada.sede
                data['persona'] = persona
                data['padronelectoral'] = padronelectoral
                data['listadosedes'] = SedesElectoralesPeriodo.objects.filter(status=True, periodo=padronelectoral).order_by('canton__provincia__nombre')
                template = get_template("adm_padronelectoral/modal/elegirsede.html")
                return JsonResponse({"result": True, 'data': template.render(data)})

            return HttpResponseRedirect(request.path)
        else:
            try:
                if DATOS_OBLIGATORIOS and persona.datos_incompletos():
                    return HttpResponseRedirect('/account')
                INSTRUCTOR_GROUP_ID = variable_valor('INSTRUCTOR_GROUP_ID')
                periodo = request.session['periodo']
                grupos = persona.usuario.groups.filter(id__in=[ALUMNOS_GROUP_ID])
                # ESTUDIANTES
                puede_ver_mensaje = False
                aperturasolicitudpractica = None
                tienepenalizacionpractica = None
                data['valor_pendiente'] = 0
                data['valor_pagados'] = 0
                data['tiene_valores_pendientes'] = tiene_valores_pendientes = False
                if InsigniaPersona.objects.values('id').filter(status=True,persona=persona,visto = False, insignia__tipoinsignia__in =[1,2,3],insignia__vigente=True).exists():
                    data['tiene_insignia_por_ver'] = InsigniaPersona.objects.filter(status=True,persona=persona,visto = False, insignia__tipoinsignia__in =[1,2,3],insignia__vigente=True).order_by('-id').first()
                    #data['tiene_insignia_por_ver'] = InsigniaPersona.objects.filter(status=True,persona=persona,visto = False, insignia__tipoinsignia__in =[2,3]).exists()
                if data['tiposistema'] == 'seleccionposgrado':
                    try:
                        from postulaciondip.models import Convocatoria
                        eConvocatorias = Convocatoria.objects.filter(fechafin__gte=datetime.now().date(), status=True, activo=True).order_by('-fechafin')
                        data['niveltituloposgrado'] = NivelTitulacion.objects.filter(pk__in=[3, 4, 30], status=True).order_by('-nivel')
                        data['personaposgrado'] = Persona.objects.get(pk=persona.id)
                        data['listadoinvitaciones'] = listadoinvitaciones = InscripcionInvitacion.objects.filter(inscripcion__postulante__persona=persona, status=True,configuracionrequisitos = True)
                        data['invitacionesaceptadas'] = listadoinvitaciones.filter(pasosproceso_id=2)
                        if InscripcionPostulante.objects.filter(persona=persona, status=True).exists():
                            data['postulante'] = aspirante = InscripcionPostulante.objects.filter(persona=persona,status=True)[0]
                            inscripcionconvocatoria = InscripcionConvocatoria.objects.values_list('convocatoria_id', flat=True).filter(postulante=aspirante, convocatoria__activo=True, convocatoria__status=True, postulante__status=True, status=True)
                            data['inscripcionconvocatoria'] = inscripcionconvocatoria
                            data['listadorequisitos'] = RequisitosConvocatoria.objects.filter(convocatoria__in=inscripcionconvocatoria, requisito__status=True, status=True).order_by('id')
                            if not inscripcionconvocatoria:
                                aspirante.estado = 1
                                aspirante.save(request)
                        if not aspirante.existen_convocatorias_disponibles(eConvocatorias):
                            data['msj'] = f"Estimad{'a' if persona.es_mujer() else 'o'} { persona.nombres.split(' ')[0] if len(persona.nombres.split(' ')) else persona.nombre_completo_inverso() }, al momento no existe una convocatoria que se ajuste a su formación académica."

                        data['tipo_convocatoria'] = TIPO_CONVOCATORIA
                        data['eInscripcionConvocatorias'] = InscripcionConvocatoria.objects.filter(status=True, postulante__persona=persona).order_by('-id')
                        return render(request, "paneldip.html", data)
                    except Exception as ex:
                        logout(request)
                        return HttpResponseRedirect("/loginpostulacion?info=%s" % ex.__str__())
                elif data['tiposistema'] == 'postulate':
                    from postulate.models import Convocatoria
                    misgrupos = ModuloGrupo.objects.filter(grupos__in=persona.usuario.groups.all()).exclude(grupos__in=[ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID]).distinct()
                    modulos = Modulo.objects.values("id", "url", "icono", "nombre", "descripcion").filter(Q(modulogrupo__in=misgrupos), activo=True, postulate=True).distinct().order_by('nombre')
                    data['mismodulos'] = modulos
                    data['convocatorias_vigente'] = convocatorias = Convocatoria.objects.values('id').filter(status=True, finicio__lte=hoy, ffin__gte=hoy, vigente=True).exists()
                    lista = []
                    if PersonaPeriodoConvocatoria.objects.values('id').filter(status=True, persona=persona).order_by('-id'):
                        requisitosperiodoconvocatoria = PersonaPeriodoConvocatoria.objects.filter(status=True, persona=persona,estado=0).order_by('-id')
                        for doc in requisitosperiodoconvocatoria:
                            if doc.traerrequisitospendiente():
                                lista.append(True)
                        data['subirrequisitos'] = True if len(lista) > 0 else False
                    return render(request, "postulate/panelpostulate.html", data)
                elif data['tiposistema'] == 'empleo':
                    misgrupos = ModuloGrupo.objects.filter(grupos__in=persona.usuario.groups.all()).exclude(grupos__in=[ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID]).distinct()
                    modulos = Modulo.objects.values("id", "url", "icono", "nombre", "descripcion").filter(Q(modulogrupo__in=misgrupos), activo=True, empleo=True).distinct().order_by('nombre')
                    banerderecho = Noticia.objects.db_manager("sga_select").values("titular", "cuerpo",
                                                                                   "imagen__archivo").filter(
                        Q(desde__lte=hoy), Q(hasta__gte=hoy), Q(publicacion__in=[4]), banerderecho=True,
                        tipos__in=[1],
                        tiene_muestra=False).distinct().order_by('-desde', 'id', 'fecha_creacion')[0:5]
                    data['banerderecho'] = banerderecho
                    data['mismodulos'] = modulos
                    # data['convocatorias_vigente'] = convocatorias = Convocatoria.objects.values('id').filter(status=True, finicio__lte=hoy, ffin__gte=hoy, vigente=True).exists()
                    return render(request, "empleo/panelpostulateempleo.html", data)
                elif data['tiposistema'] == 'empresa':
                    misgrupos = ModuloGrupo.objects.filter(grupos__in=persona.usuario.groups.all()).exclude(grupos__in=[ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID]).distinct()
                    modulos = Modulo.objects.values("id", "url", "icono", "nombre", "descripcion").filter(Q(modulogrupo__in=misgrupos), activo=True, empresa=True).distinct().order_by('nombre')
                    data['mismodulos'] = modulos
                    # data['convocatorias_vigente'] = convocatorias = Convocatoria.objects.values('id').filter(status=True, finicio__lte=hoy, ffin__gte=hoy, vigente=True).exists()
                    return render(request, "empleo/panelpostulateempleo.html", data)
                elif data['tiposistema'] == 'unemideporte':
                    return redirect(f"/unemideporte")
                # VINCULACION REDIRECCIONAR SITIOS
                from cita.models import DepartamentoServicio
                sitios_vinculacion = DepartamentoServicio.objects.filter(status=True, tiposistema__isnull=False).values('tiposistema', 'url_entrada')
                for sitio in sitios_vinculacion:
                    if data['tiposistema'] == sitio['tiposistema']:
                        request.session['tipoentrada'] = sitio['tiposistema']
                        return redirect(f"{sitio['url_entrada']}")

                if 'periodoadmision' in request.session:
                    data['admisionperiodo'] = request.session['periodoadmision']
                if 'paginador' in request.session:
                    del request.session['paginador']
                if es_estudiante:
                    periodomatricula = None
                    tipo_val = 0
                    data['inscripcion'] = inscripcion = perfilprincipal.inscripcion
                    persona = inscripcion.persona
                    modalidad = inscripcion.carrera.modalidad
                    matricula = inscripcion.matricula_periodo(periodo)
                    cordinacionid = inscripcion.carrera.mi_coordinacion2()  # extrae el id de la corrdinacion
                    if periodo:
                        data['necesita_evaluar'] = False
                        if not cordinacionid in (7, 9):
                            if variable_valor('EVALUACION_ALUMNOS_OBLIGATORIO'):
                                proceso = periodo.proceso_evaluativo()
                                if proceso.instrumentoheteroactivo:
                                    if matricula:
                                        for profesormateria in matricula.mis_profesores_acreditacion():
                                            profesortienerubricas = profesormateria.mis_rubricas_hetero()
                                            if not profesormateria.evaluado(
                                                    matricula) and profesortienerubricas and profesormateria.pueden_evaluar_docente_acreditacion(
                                                    matricula):
                                                return HttpResponseRedirect('/pro_aluevaluacion')

                                        respuestaeval = RespuestaEvaluacionAcreditacion.objects.filter(
                                            tipoinstrumento=1,
                                            proceso=proceso,
                                            evaluador=persona).order_by('materiaasignada__materia')
                                        docentesdirectores = ActividadDetalleDistributivoCarrera.objects.values_list(
                                            'actividaddetalle__criterio__distributivo__profesor_id', flat=True).filter(
                                            actividaddetalle__criterio__distributivo__periodo=periodo,
                                            actividaddetalle__criterio__criteriogestionperiodo__isnull=False,
                                            actividaddetalle__criterio__hetero=True,
                                            actividaddetalle__criterio__status=True, carrera=inscripcion.carrera,
                                            status=True).distinct()
                                        for listadirectores in docentesdirectores:
                                            profe = Profesor.objects.get(pk=listadirectores)
                                            if profe.mis_rubricas_heterodirectivos(periodo.id):
                                                if not respuestaeval.filter(profesor=profe, materia__isnull=True,
                                                                            materiaasignada__isnull=True).exists():
                                                    return HttpResponseRedirect('/pro_aluevaluacion')
                            else:
                                if matricula:
                                    if matricula.tiene_encuesta_obligatoria(periodo):
                                        return HttpResponseRedirect('/pro_aluevaluacion')

                    # se cancela porque esta en Svelte
                    # if variable_valor('FICHASOC_OBLIGATORIA'):
                    #     if Graduado.objects.db_manager("sga_select").filter(inscripcion=inscripcion, status=True).exists():
                    #         if FichaSocioeconomicaINEC.objects.db_manager("sga_select").values('id').filter(persona_id=inscripcion.persona_id).exists():
                    #             FichaSocioeconomicaINEC.objects.filter(persona_id=inscripcion.persona_id).update(confirmar=True)
                    #     if Egresado.objects.db_manager("sga_select").filter(inscripcion=inscripcion, status=True).exists():
                    #         if FichaSocioeconomicaINEC.objects.db_manager("sga_select").values('id').filter(persona_id=inscripcion.persona_id).exists():
                    #             FichaSocioeconomicaINEC.objects.filter(persona_id=inscripcion.persona_id).update(confirmar=True)
                    #     if cordinacionid != 7:
                    #         if FichaSocioeconomicaINEC.objects.db_manager("sga_select").values('id').filter(persona_id=inscripcion.persona_id).exists():
                    #             ficha = FichaSocioeconomicaINEC.objects.db_manager("sga_select").values('confirmar').filter(persona_id=inscripcion.persona_id)[0]
                    #             if ficha.get('confirmar') == False:
                    #                 return HttpResponseRedirect('/alu_socioecon')
                    #         else:
                    #             fichasocioeconomica = ficha_socioeconomica(persona)
                    #             return HttpResponseRedirect('/alu_socioecon')


                    # cordinacionid = inscripcion.carrera.mi_coordinacion2() # extrae el id de la corrdinacion
                    if cordinacionid == 9:
                        tipo_val = 1
                    elif cordinacionid in [7, 10]:
                        tipo_val = 3
                    elif cordinacionid in [1, 2, 3, 4, 5]:
                        tipo_val = 2
                    if PeriodoMatricula.objects.db_manager("sga_select").values('id').filter(status=True, activo=True, tipo=tipo_val).exists():
                        if tipo_val == 2:
                            if inscripcion.tiene_automatriculapregrado_por_confirmar(periodo):
                                return HttpResponseRedirect("/alu_matricula")
                        elif tipo_val == 1:
                            if inscripcion.tiene_automatriculaadmision_por_confirmar(periodo):
                                return HttpResponseRedirect("/alu_matricula")

                        verperiodomatricula = PeriodoMatricula.objects.db_manager("sga_select").values("valida_cronograma", "valida_redirect_panel").filter(status=True, activo=True, tipo=tipo_val).order_by('-id')[0]
                        if verperiodomatricula.get("valida_cronograma") and verperiodomatricula.get("valida_redirect_panel"):
                            periodomatricula = PeriodoMatricula.objects.filter(status=True, activo=True, tipo=tipo_val).order_by('-id')[0]
                            tiene_automatricula = False
                            if tipo_val == 1:
                                tiene_automatricula = inscripcion.tiene_automatriculaadmision_por_confirmar(periodomatricula.periodo)
                            elif tipo_val == 2:
                                tiene_automatricula = inscripcion.tiene_automatriculapregrado_por_confirmar(periodomatricula.periodo)

                            if not tiene_automatricula and Matricula.objects.values('id').filter(inscripcion=inscripcion, nivel__periodo=periodomatricula.periodo).exists():
                                return HttpResponseRedirect("/logout?info=%s" % 'Estimado estudiante ya se encuentra matriculado')
                            if periodomatricula.tiene_cronograma_coordinaciones():
                                cronograma = periodomatricula.cronograma_coordinaciones()
                                if cordinacionid in list(cronograma.values_list('coordinacion_id', flat=True)):
                                    dc = cronograma.filter(coordinacion_id=cordinacionid)[0]
                                    if not dc.activo:
                                        return HttpResponseRedirect("/logout?info=%s" % 'Estimado estudiante el proceso de matricula se encuntra inactivo')
                                    if datetime.now().date() >= dc.fechainicio and datetime.now().date() <= dc.fechafin:
                                        return HttpResponseRedirect("/alu_matricula")
                    if variable_valor('REDIRECT_SIE') and not es_administrativo and not es_profesor:
                        if 'eTemplateBaseSetting' in request.session:
                            eTemplateBaseSetting = request.session['eTemplateBaseSetting']
                            if eTemplateBaseSetting and eTemplateBaseSetting.use_api:
                                if 'connectionToken' in request.session:
                                    connectionToken = request.session['connectionToken']
                                    return redirect(f'{connectionToken}/')

                    noticias = Noticia.objects.db_manager("sga_select").values("titular", "cuerpo").filter(Q(desde__lte=hoy), Q(hasta__gte=hoy), Q(imagen=None), Q(publicacion__in=[1, 2]), banerderecho=False, tipos__in=[1, 4], carreras__id=inscripcion.carrera_id, tiene_muestra=False).distinct().order_by('-desde','id')[0:5]
                    banerderecho = Noticia.objects.db_manager("sga_select").values("titular", "cuerpo", "imagen__archivo").filter(Q(desde__lte=hoy), Q(hasta__gte=hoy), Q(publicacion__in=[1, 2]), banerderecho=True, tipos__in=[1, 4], carreras__id=inscripcion.carrera_id, tiene_muestra=False).distinct().order_by('-desde','id', 'fecha_creacion')[0:5]

                    data['reporte_0'] = obtener_reporte('ficha_preinscripcion')
                    data['imprimirficha'] = (datetime(inscripcion.fecha.year, inscripcion.fecha.month, inscripcion.fecha.day, 0, 0, 0) + timedelta(days=30)).date() > datetime.now().date()
                    data['ofertasdisponibles'] = inscripcion.tiene_ofertas_disponibles()
                    # data['ofertasdisponibles'] = False
                    data['entrevistaspendientes'] = inscripcion.tiene_entrevistas_pendientes()
                    data['proceso'] = None
                    data['es_profesor'] = False
                    data['necesita_evaluarse'] = False
                    hoy = datetime.now()
                    pendientetarea = None
                    pendienteingles = None
                    matriculadossinpracticas = False
                    data['tareas_pendientes'] = True if pendientetarea or pendienteingles else False
                    data['seleccionar_practicas_pendientes'] = matriculadossinpracticas
                    data['incidencias'] = []
                    misgrupos = ModuloGrupo.objects.filter(grupos__in=[ALUMNOS_GROUP_ID]).distinct()

                    modulosEnCache = cache.get(f"modulos__{ALUMNOS_GROUP_ID}")
                    if modulosEnCache:
                        modulos = modulosEnCache
                    else:
                        modulos = Modulo.objects.filter(Q(modulogrupo__in=misgrupos), activo=True, submodulo=False).order_by('nombre')
                        cache.set(f"modulos__{ALUMNOS_GROUP_ID}", modulos, 60*60*12)
                    modulos = modulos.values("id", "url", "icono", "nombre", "descripcion").order_by('nombre')
                    frolvacio = Q(roles__isnull=True) | Q(roles='')
                    inscripcion_principal = perfilprincipal.inscripcion
                    coordinacion_principal = inscripcion_principal.coordinacion_id

                    if coordinacion_principal == 9:
                        #Mostrar modulos  para la coordinación de Admisión
                        data['mismodulos'] = modulos.filter(frolvacio | Q(roles__icontains=1)).distinct()
                    elif coordinacion_principal == 7:
                        # Mostrar modulos  para la coordinación de Postgrado
                        data['mismodulos'] = modulos.filter(frolvacio | Q(roles__icontains=3)).distinct()
                        if matricula and matricula.bloqueomatricula:
                            data['mismodulos'] = Modulo.objects.filter(pk__in=[4, 383]).distinct()
                            data['matriculaposgrado'] = matricula
                    else:
                        # Mostrar modulos  para la coordinación de Pregado
                        data['mismodulos'] = modulos.filter(frolvacio | Q(roles__icontains=2)).distinct()

                    # if not matricula:
                    #     data['mismodulos'] = Modulo.objects.values("id", "url", "icono", "nombre", "descripcion").filter(Q(modulogrupo__in=misgrupos), activo=True).distinct().order_by('nombre')
                    # else:
                    #     # Si la matricula es de posgrado
                    #     if matricula.inscripcion.coordinacion_id == 7:
                    #         # Si la matricula esta bloqueada solo deben aparecer las opciones Mis Finanzas y Refinanciamiento de deudas
                    #         if matricula.bloqueomatricula:
                    #             data['mismodulos'] = Modulo.objects.values("id", "url", "icono", "nombre", "descripcion").filter(Q(modulogrupo__in=misgrupos), activo=True, pk__in=[4, 383]).distinct().order_by('nombre')
                    #             data['matriculaposgrado'] = matricula
                    #         else:
                    #             data['mismodulos'] = Modulo.objects.values("id", "url", "icono", "nombre", "descripcion").filter(Q(modulogrupo__in=misgrupos), activo=True).distinct().order_by('nombre')
                    #     else:
                    #         data['mismodulos'] = Modulo.objects.values("id", "url", "icono", "nombre", "descripcion").filter(Q(modulogrupo__in=misgrupos), activo=True).distinct().order_by('nombre')
                    #

                    data['datosincompletos'] = persona.datos_incompletos()
                    data['datosmedicosincompletos'] = persona.datos_medicos_incompletos()
                    data['utiliza_ficha_medica'] = UTILIZA_FICHA_MEDICA
                    data['hojavidallena'] = False if persona.hojavida_llena() else True
                    hoy1 = datetime.now().date()

                    if NotificacionDeudaPeriodo.objects.values("id").filter(periodo=periodo, vigente=True, fechafinnotificacion__gte=datetime.now()).exists():
                        notideudaperiodo = NotificacionDeudaPeriodo.objects.get(periodo=periodo, vigente=True)
                        if cordinacionid in notideudaperiodo.coordinaciones.values_list('id', flat=True):
                            if datetime.now().date() >= notideudaperiodo.fechainicionotificacion.date() and datetime.now().date() <= notideudaperiodo.fechafinnotificacion.date():
                                d = locals()
                                exec(notideudaperiodo.logicanotificacion, globals(), d)
                                x = d['decrifrar_notificacion'](persona, periodo)
                                data['tiene_valores_pendientes'] = x['tiene_valores_pendientes']
                                data['msg_valores_pendientes'] = x['msg_valores_pendientes']

                    data['es_inscripcion'] = True
                    # VALIDACIÓN PARA PREGRADO DE AUTOMATRICULA

                    data['mostrarmensajecovid'] = False
                    data['aplica_beca'] = False

                    if BecaPeriodo.objects.values("id").filter(periodo=periodo, vigente=True).exists():
                        becaperiodo = BecaPeriodo.objects.get(periodo=periodo, vigente=True)

                        if inscripcion.tienesolicitudbeca():
                            fechainicio = becaperiodo.fechainiciosolicitud.date()
                            fechafin = becaperiodo.fechafinsolicitud.date()
                            fechaactual = datetime.now().date()
                            if fechaactual >= fechainicio and fechaactual <= fechafin:
                                if inscripcion.solicitudaprobadaperiodo(periodo) and inscripcion.becapendienteaceptarperiodo(periodo):
                                    MAXIMO_DIAS_ACEPTAR = (fechafin - fechainicio).days
                                    solicitud = BecaSolicitud.objects.filter(inscripcion=inscripcion, status=True, periodo=periodo)[0]
                                    fechaaprobacion = datetime.strptime(str(solicitud.fecha_modificacion)[:10], "%Y-%m-%d").date()
                                    plazo = MAXIMO_DIAS_ACEPTAR - abs((fechaactual - fechaaprobacion).days)
                                    if plazo > 0:
                                        #data['tipomensaje'] = 'MENSAJEBECA'
                                        data['aplica_beca'] = True
                                        msg_html = f"""<span style="font-size: 30px; font-family: 'Montserrat', sans-serif;"><strong>Estimad{'a' if inscripcion.persona.sexo_id == 1 else 'o'} estudiante</strong></span><br><br><span style="font-size:17px; font-family: 'Montserrat', sans-serif;">Informamos que su solicitud de Beca de tipo <strong>{solicitud.becatipo.nombre.upper()}</strong> para el Periodo Académico {str(solicitud.periodo)}, fue <strong>APROBADA</strong> el {str(solicitud.fecha_modificacion)[:10]}. Por lo tanto, <strong>dispone de {str(plazo)}</strong> días para ingresar al módulo <a href="/alu_becas" style="text-decoration:none; color:#ffffff"><strong>BECA ESTUDIANTIL</strong></a> y ACEPTAR o RECHAZAR este beneficio.</span> <br><br><span style="font-size: 17px; font-family: 'Montserrat', sans-serif;"><strong>IMPORTANTE:</strong> Pasado el plazo establecido y en caso de no haber ACEPTADO la BECA; la misma será RECHAZADA automáticamente.</span>"""
                                        msg_html_2 = f"""<span style="font-size: 22px; font-family: 'Montserrat', sans-serif;"><strong>Estimad{'a' if inscripcion.persona.sexo_id == 1 else 'o'} estudiante</strong></span><br><br><span style="font-size:14px; font-family: 'Montserrat', sans-serif;">Informamos que su solicitud de Beca de tipo <strong>{solicitud.becatipo.nombre.upper()}</strong> para el Periodo Académico {str(solicitud.periodo)}, fue <strong>APROBADA</strong> el {str(solicitud.fecha_modificacion)[:10]}. Por lo tanto, <strong>dispone de {str(plazo)}</strong> días para ingresar al módulo <a href="/alu_becas" style="text-decoration:none; color:#000000"><strong>BECA ESTUDIANTIL</strong></a> y ACEPTAR o RECHAZAR este beneficio.</span> <br><br><span style="font-size: 14px; font-family: 'Montserrat', sans-serif;"><strong>IMPORTANTE:</strong> Pasado el plazo establecido y en caso de no haber ACEPTADO la BECA; la misma será RECHAZADA automáticamente.</span>"""
                                        data['textomensajebeca'] = msg_html
                                        data['textomensajebeca2'] = msg_html_2

                        if inscripcion.becasolicitud_set.filter(status=True, periodo=periodo).exclude(estado__in=[5,3]).exists():
                            solicitudbeca = inscripcion.becasolicitud_set.filter(status=True, periodo=periodo).exclude(estado__in=[5,3]).first()
                            if solicitudbeca.puede_actualizar_documentos():
                                if solicitudbeca.becatipo.id == 21 and not solicitudbeca.inscripcion.persona.tiene_documento_raza():
                                    messages.add_message(request, messages.WARNING, f'Favor subir documento de declaración juramentada en la solicitud de beca')
                                if BecaAsignacion.objects.filter(solicitud=solicitudbeca, infoactualizada=False).exists():
                                    messages.add_message(request, messages.WARNING, f'Estimado estudiante, favor actualizar información de la solicitud de beca')

                        if becaperiodo.obligadosubircomprobante:
                            if inscripcion.persona.obligado_a_cargar_comprobante_venta_beca_periodo(periodo):
                                return HttpResponseRedirect('/alu_becas')

                    # encuesta grupo estudiantes y docente
                    data['realizar_encuesta_grupo'] = False
                    inscripcionencuestagrupoestudiantes = InscripcionEncuestaGrupoEstudiantes.objects.filter(inscripcion=inscripcion, encuesta__tipoperfil=1, encuesta__activo=True, status=True, encuesta__status=True)
                    if inscripcionencuestagrupoestudiantes.exists():
                        if inscripcionencuestagrupoestudiantes[0].respondio == False:

                            per2 = Persona.objects.values('localizacionactualizada').get(pk=persona.id)
                            if per2['localizacionactualizada'] is False:
                                data['title'] = "Actualización de Datos de Domicilio y contacto de la Persona"
                                return render(request, "alu_becas/actualizarlocalizacionpersona.html", data)

                            data['idencuestagrupo'] = inscripcionencuestagrupoestudiantes[0].encuesta.id
                            data['realizar_encuesta_grupo'] = True

                    data['existeperiodocambiocarrera'] = existeperiodocambiocarrera = AperturaPeriodoCambioCarrera.objects.filter(status=True, fechacierre__gte=datetime.now(), fechaapertura__lte=datetime.now()).exists()
                    data['aptosolicitar'] = aptosolicitar = perfilprincipal.inscripcion.puede_solicitar_cambio_carrera()
                    if Matricula.objects.select_related('inscripcion').filter(status=True, inscripcion__persona=persona,
                                                                              nivel__periodo=periodo,
                                                                              nivelmalla__gt=1,
                                                                              cerrada=False):
                        data['aptosolicitar'] = aptosolicitar = True
                    else:
                        data['aptosolicitar'] = aptosolicitar = False
                    if existeperiodocambiocarrera and aptosolicitar:
                        data['datosperiodo'] = datosperiodo = AperturaPeriodoCambioCarrera.objects.filter(status=True, fechacierre__gte=datetime.now(), fechaapertura__lte=datetime.now()).first()

                elif es_profesor:
                    noticias = Noticia.objects.db_manager("sga_select").values("titular", "cuerpo").filter(Q(desde__lte=hoy), Q(hasta__gte=hoy), Q(imagen=None), Q(publicacion__in=[1, 2]), banerderecho=False, tipos__in=[1, 5], carreras__coordinacion__id=perfilprincipal.profesor.coordinacion_id, tiene_muestra=False).distinct().order_by('-desde','id')[0:5]
                    banerderecho = Noticia.objects.db_manager("sga_select").values("titular", "cuerpo", "imagen__archivo").filter(Q(desde__lte=hoy), Q(hasta__gte=hoy), Q(publicacion__in=[1, 2]), banerderecho=True, tipos__in=[1, 5], carreras__coordinacion__id=perfilprincipal.profesor.coordinacion_id, tiene_muestra=False).distinct().order_by('-desde','id', 'fecha_creacion')[0:5]

                    misgrupos = ModuloGrupo.objects.filter(grupos__in=[PROFESORES_GROUP_ID]).distinct()
                    data['mismodulos'] = Modulo.objects.values("id", "url", "icono", "nombre", "descripcion").filter(Q(modulogrupo__in=misgrupos) | Q(id=MODULO_EVALUACION_PARESDIRECTIVOS_ID), activo=True, submodulo=False).distinct().order_by('nombre')
                    grupos = persona.usuario.groups.filter(id__in=[PROFESORES_GROUP_ID])
                    profesor = perfilprincipal.profesor
                    data['es_profesor'] = True
                    data['profesornombre'] = profesor
                    data['necesita_evaluarse'] = False
                    if periodo:
                        data['proceso'] = proceso = periodo.proceso_evaluativo()
                        if proceso.instrumentoautoactivo and not profesor.autoevaluado_periodo(periodo):
                            data['necesita_evaluarse'] = True
                    data['es_profesor'] = True
                    persona = perfilprincipal.profesor.persona
                    profesor = perfilprincipal.profesor
                    # encuesta grupo estudiantes y docente
                    data['realizar_encuesta_grupo'] = False
                    inscripcionencuestagrupoestudiantes = InscripcionEncuestaGrupoEstudiantes.objects.filter(profesor=profesor, encuesta__tipoperfil=2, encuesta__activo=True, status=True, respondio=False, encuesta__status=True)
                    if inscripcionencuestagrupoestudiantes:
                        if inscripcionencuestagrupoestudiantes[0].respondio == False:
                            per2 = Persona.objects.values('localizacionactualizada').get(pk=persona.id)
                            if per2['localizacionactualizada'] is False:
                                data['title'] = "Actualización de Datos de Domicilio y contacto de la Persona"
                                return render(request, "alu_becas/actualizarlocalizacionpersona.html", data)

                            data['idencuestagrupo'] = inscripcionencuestagrupoestudiantes[0].encuesta.id
                            data['realizar_encuesta_grupo'] = True

                    if periodo and periodo.id >= 126:
                        if PeriodoAcademia.objects.filter(status=True, periodo=periodo).exists():
                            periodoacademia= PeriodoAcademia.objects.get(status=True, periodo=periodo)
                            if periodoacademia.fecha_limite_ingreso_act:
                                fechalimite = periodoacademia.fecha_limite_ingreso_act
                                fechaactual = datetime.now().date()
                                if fechaactual > fechalimite:
                                    if ClaseActividad.objects.filter(detalledistributivo__distributivo__profesor=profesor, detalledistributivo__distributivo__periodo=periodo).exists():
                                        actividades = ClaseActividad.objects.filter(detalledistributivo__distributivo__profesor=profesor,detalledistributivo__distributivo__periodo=periodo).count()
                                    else:
                                        actividades = 0
                                    if ProfesorDistributivoHoras.objects.filter(profesor=profesor, periodo=periodo).exists():
                                        pdistri = ProfesorDistributivoHoras.objects.get(profesor=profesor, periodo=periodo)
                                        horastotales= pdistri.total_horas_planificacion()

                                    if actividades != horastotales:
                                        data['mensaje'] = True

                elif perfilprincipal.es_instructor():
                    misgrupos = ModuloGrupo.objects.filter(grupos__id__in=[INSTRUCTOR_GROUP_ID]).distinct()
                    data['mismodulos'] = Modulo.objects.values("id", "url", "icono", "nombre", "descripcion").filter(Q(modulogrupo__in=misgrupos), activo=True, submodulo=False).distinct().order_by('nombre')
                    grupos = persona.usuario.groups.filter(id__in=[variable_valor('INSTRUCTOR_GRUPO_ID')])
                    data['es_instructor'] = True
                    noticias = Noticia.objects.db_manager("sga_select").values("titular", "cuerpo").filter(Q(desde__lte=hoy), Q(hasta__gte=hoy), Q(imagen=None), Q(publicacion__in=[1, 2]), banerderecho=False, tipos__in=[1], tiene_muestra=False).distinct().order_by('-desde','id')[0:5]
                    banerderecho = Noticia.objects.db_manager("sga_select").values("titular", "cuerpo", "imagen__archivo").filter(Q(desde__lte=hoy), Q(hasta__gte=hoy), Q(publicacion__in=[1, 2]), banerderecho=True, tipos__in=[1], tiene_muestra=False).distinct().order_by('-desde','id', 'fecha_creacion')[0:5]

                else:
                    noticias = Noticia.objects.db_manager("sga_select").values("titular", "cuerpo").filter(Q(desde__lte=hoy), Q(hasta__gte=hoy), Q(imagen=None), Q(publicacion__in=[1, 3]), banerderecho=False, tipos__in=[1, 2, 3], tiene_muestra=False).distinct().order_by('-desde','id')[0:5]
                    banerderecho = Noticia.objects.db_manager("sga_select").values("titular", "cuerpo", "imagen__archivo").filter(Q(desde__lte=hoy), Q(hasta__gte=hoy), Q(publicacion__in=[1, 2]), banerderecho=True, tipos__in=[1, 2, 3], tiene_muestra=False).distinct().order_by('-desde','id', 'fecha_creacion')[0:5]

                    misgrupos = ModuloGrupo.objects.filter(grupos__in=persona.usuario.groups.all()).exclude(grupos__in=[ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID]).distinct()
                    modulos = Modulo.objects.values("id", "url", "icono", "nombre", "descripcion").filter(Q(modulogrupo__in=misgrupos), activo=True, submodulo=False).distinct().order_by('nombre')
                    if data['tiposistema'] == 'sga':
                        modulos = modulos.filter(sga=True).distinct().order_by('nombre')
                    if data['tiposistema'] == 'sagest':
                        modulos = modulos.filter(sagest=True).distinct().order_by('nombre')
                    if data['tiposistema'] == 'posgrado':
                        modulos = modulos.filter(posgrado=True).distinct().order_by('nombre')
                    if data['tiposistema'] == 'seleccionposgrado':
                        modulos = modulos.filter(postulacionposgrado=True).distinct().order_by('nombre')
                    if data['tiposistema'] == 'postulate':
                        modulos = modulos.filter(postulate=True).distinct().order_by('nombre')
                    data['mismodulos'] = modulos
                    grupos = persona.usuario.groups.exclude(id__in=[ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID])

                tiposistema = request.session['tiposistema']

                # if tiposistema == 'sga':
                #     if 'archivos' not in request.session:
                #         request.session['archivos'] = Archivo.objects.filter(tipo__id=ARCHIVO_TIPO_MANUALES, grupo__in=grupos, sga=True, visible=True)
                #
                # else:
                #     if 'archivos' not in request.session:
                #         request.session['archivos'] = Archivo.objects.filter(tipo__id=ARCHIVO_TIPO_MANUALES, grupo__in=grupos, sagest=True, visible=True)

                # data['archivos'] = request.session['archivos'] if 'archivos' in request.session else []
                data['grupos'] = misgrupos

                # MODULO DE ENCUESTAS
                if UTILIZA_MODULO_ENCUESTAS:
                    if periodo:
                        deppersona = persona.mi_departamento()
                        cordpersona = persona.mis_coordinaciones()
                        distpersona = persona.distributivopersona_set.filter(status=True)
                        regimenpersona = []
                        if distpersona.exists():
                            if distpersona.first().regimenlaboral:
                                regimenpersona = [distpersona.first().regimenlaboral.pk]
                        # if periodo.id == 112:
                        grupos = []
                        if es_estudiante:
                            if not persona.confirmardatosbienestar:
                                data = {}
                                data['title'] = u'DIRECCIÓN DE BIENESTAR UNIVERSITARIO'
                                adduserdata(request, data)

                                form = ConfirmaDatosBienestarForm(initial={'sectorlugar': persona.sectorlugar,
                                                                           'nacionalidad': persona.nacionalidad,
                                                                           'pais': persona.pais,
                                                                           'provincia': persona.provincia,
                                                                           'canton': persona.canton,
                                                                           'unicoestudia': persona.unicoestudia,
                                                                           'labora': persona.labora
                                                                           })
                                form.editar(persona)
                                if persona.sexo_id !=1:
                                    form.ocutar()
                                data['form'] = form
                                return render(request, "emails/confirmar_datosbienestar.html", data)
                            # if not persona.preferenciapolitica:
                            #     data = {}
                            #     data['title'] = u'Universidad Estatal de Milagro'
                            #     adduserdata(request, data)
                            #     data['form'] = ConfirmaCredoPoliticaForm()
                            #     return render(request, "emails/confirmar_politicacredo.html", data)
                            # permsona=Persona.objects.get(id=persona.id)
                            # if permsona.aceptaservicio == 0 or permsona.aceptaservicio == None:
                            #     return HttpResponseRedirect('/encuestaparentesco?action=encuesta&cedula=%s'%permsona.identificacion())
                            grupos = persona.usuario.groups.filter(id=ALUMNOS_GROUP_ID)
                        elif es_administrativo or es_profesor:
                            if not persona.confirmarextensiontelefonia:
                                data = {}
                                data['title'] = u'Inicio'
                                adduserdata(request, data)
                                data['form'] = ConfirmaExtensionForm(initial={'extension': persona.telefonoextension})
                                return render(request, "emails/confirmar_extension.html", data)
                            grupos = persona.usuario.groups.exclude(id__in=[ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID, EMPLEADORES_GRUPO_ID, INSTRUCTOR_GROUP_ID])
                            if es_profesor:
                                grupos = persona.usuario.groups.filter(id=PROFESORES_GROUP_ID)
                        elif es_profesor:
                            grupos = persona.usuario.groups.filter(id=PROFESORES_GROUP_ID)

                        qsencuesta = Encuesta.objects.filter(Q(fechainicio__lte=hoy) & Q(fechafin__gte=hoy) & Q(activa=True)).filter(Q(grupos__in=grupos)| Q(departamentos__in=[deppersona]) | Q(facultades__in=cordpersona) | Q(regimenlaboral__in=regimenpersona) | Q(muestraencuesta__persona=persona)).exclude(respuestaencuesta__persona=persona).distinct()
                        if qsencuesta.exists():
                            esexcluido = False
                            if qsencuesta.first().exclude_grupos.all():
                                esexcluido = qsencuesta.first().exclude_grupos.filter(id__in=grupos).exists()
                            if not esexcluido:
                                encuesta_pendiente = qsencuesta.distinct().order_by('-id')
                                ea = encuesta_pendiente[0]
                                if ea.muestraencuesta_set.filter(status=True):
                                    if ea.muestraencuesta_set.filter(persona=persona, status=True):
                                        if not ea.respuestaencuesta_set.filter(persona=persona).exists():
                                            if ea.sexo == 0:
                                                if ea.puede_seguir_encuestando_por_grupo(grupos) or ea.puede_seguir_encuestando_por_muestra_persona(persona):
                                                    if es_estudiante:
                                                        if ea.matriculados:
                                                            if inscripcion.matricula_set.filter(estado_matricula__in=[2,3], cerrada=False, status=True):
                                                                data['encuestaobligatoria'] = ea
                                                        else:
                                                            data['encuestaobligatoria'] = ea
                                                    else:
                                                        data['encuestaobligatoria'] = ea
                                                    data['encuestas'] = encuesta_pendiente

                                            if ea.sexo == persona.sexo_id:
                                                if ea.puede_seguir_encuestando_por_grupo(grupos) or ea.puede_seguir_encuestando_por_muestra_persona(persona):
                                                    if es_estudiante:
                                                        if ea.matriculados:
                                                            if inscripcion.matricula_set.filter(estado_matricula__in=[2,3], cerrada=False,
                                                                                                status=True):
                                                                data['encuestaobligatoria'] = ea
                                                        else:
                                                            data['encuestaobligatoria'] = ea
                                                    else:
                                                        data['encuestaobligatoria'] = ea
                                                    data['encuestas'] = encuesta_pendiente
                                else:
                                    if ea.sexo == 0:
                                        if ea.puede_seguir_encuestando_por_grupo(grupos) or ea.puede_seguir_encuestando_por_muestra_persona(persona):
                                            if es_estudiante:
                                                if ea.matriculados:
                                                    if inscripcion.matricula_set.filter(estado_matricula__in=[2,3], cerrada=False,
                                                                                        status=True):
                                                        data['encuestaobligatoria'] = ea
                                                else:
                                                    data['encuestaobligatoria'] = ea
                                            else:
                                                data['encuestaobligatoria'] = ea
                                            data['encuestas'] = encuesta_pendiente

                                    if ea.sexo == persona.sexo_id:
                                        if ea.puede_seguir_encuestando_por_grupo(grupos) or ea.puede_seguir_encuestando_por_muestra_persona(persona):
                                            if es_estudiante:
                                                if ea.matriculados:
                                                    if inscripcion.matricula_set.filter(estado_matricula__in=[2,3], cerrada=False,
                                                                                        status=True):
                                                        data['encuestaobligatoria'] = ea
                                                else:
                                                    data['encuestaobligatoria'] = ea
                                            else:
                                                data['encuestaobligatoria'] = ea
                                            data['encuestas'] = encuesta_pendiente

                # NOTICIAS Y AVISOS DEL DIA
                data['utiliza_modulo_biblioteca'] = UTILIZA_MODULO_BIBLIOTECA
                if data['tiposistema'] == 'sagest':
                    data['tipoentrada'] = request.session['tipoentrada'] = "SAGEST"
                elif data['tiposistema'] == 'posgrado':
                    data['tipoentrada'] = request.session['tipoentrada'] = "POSGRADO"
                elif data['tiposistema'] == 'seleccionposgrado':
                    data['tipoentrada'] = request.session['tipoentrada'] = "POSTULACIONPOSGRADO"
                elif data['tiposistema'] == 'postulate':
                    data['tipoentrada'] = request.session['tipoentrada'] = "POSTULATE"

                if data['tiposistema'] == 'sga':
                    # LISTADO DE ESTUDIANTES Y PROFESORES QUE ESTAN DE CUMPLEAÑOS
                    data['tipoentrada'] = request.session['tipoentrada'] = "SGA"
                    if UTILIZA_MODULO_BIBLIOTECA:
                        data['documentossinentregar'] = persona.documentos_sin_entregar()
                        data['biblioteca'] = [Documento.objects.filter(fisico=True).count(), Documento.objects.exclude(digital='').count(), ReferenciaWeb.objects.count()]
                        data['referenciasweb'] = ReferenciaWeb.objects.all().order_by('id')
                        data['reservaslibros'] = persona.documentos_reservados()
                    data['utiliza_modulo_biblioteca'] = UTILIZA_MODULO_BIBLIOTECA
                    if persona.en_grupo(RECTORADO_GROUP_ID) or persona.en_grupo(SISTEMAS_GROUP_ID):
                        data['incidencias'] = Incidencia.objects.filter(cerrada=False).order_by('-lecciongrupo__fecha')[:25]
                    else:
                        data['incidencias'] = Incidencia.objects.filter(cerrada=False, tipo__responsable=persona).order_by('-lecciongrupo__fecha')[:25]
                elif data['tiposistema'] == 'posgrado':
                    noticias = None
                    banerderecho = None
                elif data['tiposistema'] == 'seleccionposgrado':
                    noticias = None
                    banerderecho = None
                elif data['tiposistema'] == 'postulate':
                    noticias = None
                    banerderecho = None

                data['noticias'] = noticias
                data['banerderecho'] = banerderecho

                banerderecho_muestra = NoticiaMuestra.objects.db_manager("sga_select").values("noticia__titular", "noticia__cuerpo", "noticia__imagen__archivo").filter(Q(noticia__desde__lte=hoy), Q(noticia__hasta__gte=hoy), Q(noticia__publicacion__in=[1, 2]), noticia__tiene_muestra=True, persona=persona).distinct().order_by('-noticia__desde', 'noticia__id', 'noticia__fecha_creacion')[0:5]
                data['banerderecho_muestra'] = banerderecho_muestra

                data['utiliza_modulo_encuestas'] = UTILIZA_MODULO_ENCUESTAS
                data['institucion'] = NOMBRE_INSTITUCION
                if 'info' in request.GET:
                    data['info'] = request.GET['info']
                data['cantidadcomplexivo'] = 0
                data['PANTALLA_PREINSCRIPCION'] = False
                data['PANTALLA_PREINSCRIPCION'] = varpreinscripcion = PANTALLA_PREINSCRIPCION
                data['complexivoperiodo'] = None
                cantidadcomplexivo = 0
                if cantidadcomplexivo == 0:
                    data['PANTALLA_PREINSCRIPCION'] = False
                publicaciones = None
                listaencuentas = PersonaConfirmarEncuesta.objects.values_list("publicarenlace__id", flat=False).filter(persona=persona, status=True, publicarenlace__fechainicio__lte=datetime.now().date(), publicarenlace__fechafin__gte=datetime.now().date(), publicarenlace__status=True)
                if PublicarEnlace.objects.values('id').filter(fechainicio__lte=datetime.now().date(), fechafin__gte=datetime.now().date(), status=True).exclude(id__in=listaencuentas).exists():
                    publicaciones = PublicarEnlace.objects.filter(fechainicio__lte=datetime.now().date(), fechafin__gte=datetime.now().date(), status=True).exclude(id__in=listaencuentas)
                data['publicaciones'] = publicaciones
                if es_administrativo:
                    data['es_administrativo'] = True
                    persona = persona
                    administrativo = perfilprincipal.administrativo
                    data['realizar_encuesta_grupo'] = False
                    inscripcionencuestagrupoestudiantes = InscripcionEncuestaGrupoEstudiantes.objects.filter(administrativo=administrativo, encuesta__tipoperfil=3, encuesta__activo=True, status=True, encuesta__status=True,respondio=False)
                    if inscripcionencuestagrupoestudiantes:
                        if inscripcionencuestagrupoestudiantes[0].respondio == False:

                            per2 = Persona.objects.values('localizacionactualizada').get(pk=persona.id)
                            if per2['localizacionactualizada'] is False:
                                data['title'] = "Actualización de Datos de Domicilio y contacto de la Persona"
                                return render(request, "alu_becas/actualizarlocalizacionpersona.html", data)

                            data['idencuestagrupo'] = inscripcionencuestagrupoestudiantes[0].encuesta.id
                            data['realizar_encuesta_grupo'] = True
                perfil = persona.mi_perfil()
                if variable_valor('ACEPTAR_MIGRACIONMALLA'):
                    if persona.inscripcion_set.filter(inscripcionold__isnull=False, confirmacion=False, status=True):
                        inscripcionmallamigrar = persona.inscripcion_set.filter(inscripcionold__isnull=False, confirmacion=False, status=True)[0]
                        data['inscripcionmallamigrar'] = inscripcionmallamigrar
                data['tiene_discapasidad'] = False
                if perfil.tienediscapacidad and perfil.verificadiscapacidad:
                    data['tiene_discapasidad'] = True
                data['VER_TAREAS_MODULOS_PENDIENTES'] = variable_valor('VER_TAREAS_MODULOS_PENDIENTES')
                data['SELECCIONAR_PRACTICAS_ESTUDIANTES'] = variable_valor('SELECCIONAR_PRACTICAS_ESTUDIANTES')
                data['comunicado'] = False
                if perfilprincipal.inscripcion:
                    if perfilprincipal.inscripcion.comunicado == True:
                        data['comunicado'] = True
                data['aperturasolicitudpractica'] = aperturasolicitudpractica
                data['tienepenalizacionpractica'] = tienepenalizacionpractica
                data['puede_ver_mensaje'] = puede_ver_mensaje
                data['si_sugerencia'] = False
                data['cargadocumentocedula'] = False
                if es_administrativo or es_profesor:
                    if persona.distributivopersona_set.values('id').filter(estadopuesto_id=1, status=True).exists():
                        # Regimen: 1 Administrativos, 2 Trabajadores, 3 Docentes
                        if persona.regimen_vigente() != 3:
                            documentos = persona.documentos_personales()
                            if not documentos:
                                data['cargadocumentocedula'] = True
                            else:
                                data['cargadocumentocedula'] = not documentos.actualizadouath
                data['puede_ver_linea'] = variable_valor('VER_LINEA_TIEMPO')

                # VACUNACION COVID19
                data['encuesta_vacuna_activa'] = variable_valor('ENCUESTA_VACUNA')
                data['mostrarventanavacunacovid'] = True if not VacunaCovid.objects.filter(persona=persona, recibiodosiscompleta=True, status=True).exists() else False
                # if variable_valor('PROCESO_ELECTORAL'):
                #     #EVENTO ELECTORAL
                #     data['existeperiodoactivo'] = existeperiodo = CabPadronElectoral.objects.filter(activo=True, status=True).exists()
                #     if existeperiodo:
                #         data['periodoelectoral'] = padronelectoral = CabPadronElectoral.objects.filter(activo=True, status=True).first()
                #         data['confirmansedeelectoral'] = padronelectoral.confirmacion_sede
                #         if padronelectoral.confirmacion_sede and es_estudiante:
                #             if not PersonasSede.objects.filter(status=True, persona=persona, sede__periodo=padronelectoral).exists():
                #                 if Matricula.objects.select_related('inscripcion').filter(status=True, inscripcion__persona=persona,  nivel__periodo=padronelectoral.periodo, nivelmalla__in=[3,4,5,6,7,8,9,10], cerrada=False):
                #                     data['confirmacion_sede'] = True
                #             else:
                #                 data['personasedeubicacion'] = PersonasSede.objects.filter(status=True, persona=persona, sede__periodo=padronelectoral).first()
                #         data['milugarvotacion'] = DetPersonaPadronElectoral.objects.filter(cab=padronelectoral, status=True, persona=persona)
                #ACTUALIZACION DE DATOS GEO
                data['actualizacion_localidad'] = actualizarlocalidad = variable_valor('ACTUALIZACION_LOCALIDAD')
                data['actualizacion_localidad_con_mapa'] = variable_valor('ACTUALIZACION_LOCALIDAD_MAPA')
                if actualizarlocalidad:
                    data['localizacionactualizada_est'] = localizacionactualizada_est = Persona.objects.get(pk=persona.id).localizacionactualizada
                #CAMBIO CARRERA
                data['visualizar_tutorial'] = Persona.objects.values('visualizar_tutorial').get(pk=persona.id)['visualizar_tutorial']
                inscripcionencuestagrupoestudiantes = InscripcionEncuestaGrupoEstudiantes.objects.filter(persona=persona, encuesta__tipoperfil=4, encuesta__activo=True, status=True, encuesta__status=True, respondio=False)
                if inscripcionencuestagrupoestudiantes:
                    if inscripcionencuestagrupoestudiantes[0].respondio == False:

                        per2 = Persona.objects.values('localizacionactualizada').get(pk=persona.id)
                        if per2['localizacionactualizada'] is False:
                            data['title'] = "Actualización de Datos de Domicilio y contacto de la Persona"
                            return render(request, "alu_becas/actualizarlocalizacionpersona.html", data)

                        data['idencuestagrupo'] = inscripcionencuestagrupoestudiantes[0].encuesta.id
                        data['realizar_encuesta_grupo'] = True
                if data['modulos_favoritos']:
                    data['mismodulos'] = data['mismodulos'].exclude(id__in=data['modulos_favoritos'].values_list('id', flat=True))

                data['CATEGORIAS_MODULOS'] = CATEGORIAS_MODULOS = ModuloCategorias.objects.filter(status=True, id__in=Modulo.objects.values('categorias').filter(status=True, id__in=data['mismodulos'].values('id'), categorias__isnull=False).values_list('categorias', flat=True)).order_by('prioridad')

                # VALIDACIÓN PARA QUE SALGAN EVENTOS DISPONIBLE EN TU CANTÓN,
                from even.configuraciones import traerEventosDisponibles
                data['eventos'] = eventodisponible = traerEventosDisponibles(request, persona, periodo)
                if eventodisponible:
                    data['misinscripcionespendientes'] = RegistroEvento.objects.filter(participante=persona, status=True, estado_confirmacion=0, periodo=eventodisponible)
                else:
                    data['misinscripcionespendientes'] = None
                # FIN VALIDACIÓN EVENTO DEL CANTÓN
                #DIASCELEBRACIÓN
                data['DIA_CANCER_MAMA_19_OCTUBRE'] = variable_valor('DIA_CANCER_MAMA_19_OCTUBRE')
                data['CATEGORIZACION_MODULOS'] = variable_valor('CATEGORIZACION_MODULOS')
                data['MODAL_CANCER_MAMA_ID'] = random.randint(1, 2)
                ins_encuesta=inscripcionencuestagrupoestudiantes.first()
                if ins_encuesta:
                    data['encuesta_required'] = ins_encuesta.encuesta.obligatoria

                if 'persona_sancion_notificar' in request.session:
                    data['obj_persona_sancion'] = request.session['persona_sancion_notificar']

                return render(request, "panelnew.html", data)
                # return render(request, "panel.html", data)
            except Exception as ex:
                import sys
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return HttpResponseRedirect('/logout')


# CAMBIO CLAVES
@login_required(redirect_field_name='ret', login_url='/loginsga')
@last_access
@transaction.atomic()
def passwd(request):
    if request.method == 'POST':
        if 'action' in request.POST:

            action = request.POST['action']
            if action == 'changepass':
                try:
                    f = CambioClaveForm(request.POST)
                    if f.is_valid():
                        data = {}
                        password = f.cleaned_data['nueva']
                        espacio = mayuscula = minuscula = numeros = False
                        long = len(password)  # Calcula la longitud de la contraseña
                        # y = password.isalnum()  # si es alfanumérica retona True
                        for carac in password:
                            espacio = True if carac.isspace() else espacio # si encuentra un espacio se cambia el valor user
                            mayuscula = True if carac.isupper() else mayuscula # acumulador o contador de mayusculas
                            minuscula = True if carac.islower() == True else minuscula # acumulador o contador de minúsculas
                            numeros = True if carac.isdigit() == True else numeros # acumulador o contador de numeros

                        if espacio == True:  # hay espacios en blanco
                            return JsonResponse({"result": "bad", "mensaje": u"La clave no puede contener espacios."})
                        if not mayuscula or not minuscula or not numeros or long < 8:
                            return JsonResponse({"result": "bad", "mensaje": u"La clave elegida no es segura: debe contener letras minúsculas, mayúsculas, números y al menos 8 carácter."})

                        adduserdata(request, data)
                        persona = data['persona']
                        if f.cleaned_data['nueva'].lower() == f.cleaned_data['anterior'].lower():
                            return JsonResponse({"result": "bad", "mensaje": u"Clave nueva no puede ser igual a la clave actual."})
                        if f.cleaned_data['nueva'] == persona.cedula:
                            return JsonResponse({"result": "bad", "mensaje": u"No puede usar como clave su numero de Cédula."})
                        usuario = persona.usuario
                        if usuario.check_password(f.cleaned_data['anterior']):
                            usuario.set_password(f.cleaned_data['nueva'])
                            usuario.save()
                            persona.clave_cambiada()
                            if not data['tiposistema'] == 'postulate':
                                if variable_valor('VALIDAR_LDAP'):
                                    validar_ldap_reseteo(usuario.username, f.cleaned_data['nueva'], persona)
                            log(u'%s - cambio clave desde IP %s' % (persona, get_client_ip(request)), request, "add")
                            if not UserAuth.objects.db_manager("sga_select").values("id").filter(usuario=usuario).exists():
                                usermoodle = UserAuth(usuario=usuario)
                                usermoodle.set_data()
                                usermoodle.set_password(request.POST['nueva'])
                                usermoodle.save()
                            else:
                                usermoodle = UserAuth.objects.filter(usuario=usuario).first()
                                isUpdateUserMoodle = False
                                if not usermoodle.check_password(request.POST['nueva']) or usermoodle.check_data():
                                    if not usermoodle.check_password(request.POST['nueva']):
                                        usermoodle.set_password(request.POST['nueva'])
                                    usermoodle.save()

                            send_html_mail("Cambio Clave SGA.", "emails/cambio_clave.html", {'sistema': u'Sistema de Gestión Académica', 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'ip': get_client_ip(request),'persona': persona}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[0][1])
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Clave anterior no coincide."})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"No puedo cambiar la clave."})

            if action == 'updateextension':
                try:
                    f = ConfirmaExtensionForm(request.POST)
                    if f.is_valid():
                        data = {}
                        adduserdata(request, data)
                        persona = data['persona']
                        if not len(str(f.cleaned_data['extension']))==4:
                            return JsonResponse({"result": "bad", "mensaje": u"Extensión telefónica debe tener 4 dígitos."})
                        extensionanterior = persona.telefonoextension
                        persona.telefonoextension = f.cleaned_data['extension']
                        persona.confirmarextensiontelefonia = True
                        peractualiza = PersonaActualizaExtension(persona=persona,
                                                                 telefonoextensionanterior=extensionanterior,
                                                                 telefonoextensionactual=f.cleaned_data['extension']
                                                                 )
                        peractualiza.save(request)
                        persona.save(request)
                        request.session['persona'] = persona
                        request.session['perfiles'] = perfiles = persona.mis_perfilesusuarios_app(request.session['tiposistema'])
                        request.session['perfilprincipal'] = persona.perfilusuario_principal(perfiles, request.session['tiposistema'])
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'updatedatosbienestar':
                try:
                    f = ConfirmaDatosBienestarForm(request.POST)
                    if f.is_valid():
                        data = {}
                        adduserdata(request, data)
                        persona = data['persona']
                        persona.sectorlugar = f.cleaned_data['sectorlugar']
                        persona.nacionalidad = f.cleaned_data['nacionalidad']
                        persona.pais = f.cleaned_data['pais']
                        persona.provincia = f.cleaned_data['provincia']
                        persona.canton = f.cleaned_data['canton']
                        persona.unicoestudia = f.cleaned_data['unicoestudia']
                        persona.labora = f.cleaned_data['labora']
                        persona.fechaactualizabienestar = datetime.now().date()
                        persona.confirmardatosbienestar = True
                        persona.eszurdo = f.cleaned_data['eszurdo']
                        if persona.sexo_id == 1:
                            persona.estadogestacion = f.cleaned_data['estadogestacion']
                        persona.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'updatecredopolitica':
                try:
                    f = ConfirmaCredoPoliticaForm(request.POST)
                    if f.is_valid():
                        data = {}
                        adduserdata(request, data)
                        persona = data['persona']
                        persona.credo = f.cleaned_data['credo']
                        persona.preferenciapolitica = f.cleaned_data['preferenciapolitica']
                        persona.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        try:
            data = {}
            adduserdata(request, data)
            data['title'] = u'Cambio de clave'
            data['form'] = CambioClaveForm()
            persona = data['persona']
            data['cambio_clave_obligatorio'] = persona.necesita_cambiar_clave()
            return render(request, "changepass.html", data)
        except Exception as ex:
            return HttpResponseRedirect('/')


def get_user_info(request):
    from user_agents import parse
    user_agent = parse(request.META.get('HTTP_USER_AGENT'))
    user_ip = get_client_ip(request)
    user_device = user_agent.device.family
    user_browser = user_agent.browser.family
    user_os_type = user_agent.os.family
    user_os_version = user_agent.os.version_string
    user_device_type = 'Otros'
    if user_agent.is_pc:
        user_device_type = 'PC'
    elif user_agent.is_mobile:
        user_device_type = 'Telófono Movil'
    elif user_agent.is_tablet:
        user_device_type = 'Tablet'
    user_info = {
        'fecha': datetime.now().date(),
        'hora': datetime.now().time(),
        'bs': user_browser,
        'ip': user_ip,
        'os': '{} - {}'.format(user_os_type, user_os_version),
        'dispositivo': '{} - {}'.format(user_device_type, user_device)
    }
    return user_info


# ENVIO DE CORREO AL INGRESAR COMO
def send_mail_login_on(request, persona_new,persona_old, tiposistema):
    if not persona_old.usuario.is_superuser:
        from user_agents import parse
        user_agent = parse(request.META.get('HTTP_USER_AGENT'))
        user_ip = get_client_ip(request)
        user_device = user_agent.device.family
        user_browser = user_agent.browser.family
        user_os_type = user_agent.os.family
        user_os_version = user_agent.os.version_string
        user_device_type = 'Otros'
        if user_agent.is_pc:
            user_device_type = 'PC'
        elif user_agent.is_mobile:
            user_device_type = 'Telófono Movil'
        elif user_agent.is_tablet:
            user_device_type = 'Tablet'
        send_html_mail(u"Ingreso a perfil",
                       "emails/ingreso_perfil.html",
                       {'sistema': u'Sistema de Gestión Académica',
                        'fecha': datetime.now().date(), 'hora': datetime.now().time(),
                        'bs': user_browser, 'ip': user_ip,
                        'os': '{} - {}'.format(user_os_type, user_os_version),
                        'dispositivo': '{} - {}'.format(user_device_type, user_device), 'tiposistema_': tiposistema,
                        't': miinstitucion(),
                        'persona_destino': persona_new, 'persona_ingresa': persona_old},
                       persona_old.lista_emails_envio(), ['sga@unemi.edu.ec'], [], cuenta=CUENTAS_CORREOS[16][1])

# CAMBIO DE USUARIO DESDE ADMINISTRADOR
@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
def changeuser(request):
    from bd.models import UserToken, UserProfileChangeToken
    from api.helpers.functions_helper import get_variable
    try:
        data = {}
        adduserdata(request, data)
        persona = data['persona']
        persona_anterior = persona
        if persona.usuario.is_superuser or puede_realizar_accion_afirmativo(request, 'sga.puede_ingresar_como_graduado') or puede_realizar_accion_afirmativo(request,'sga.puede_entrar_como_estudiante') or puede_realizar_accion_afirmativo(request,'sga.puede_entrar_como_docente') or puede_realizar_accion_afirmativo(request,'posgrado.puede_entrar_como_usuario') or puede_realizar_accion_afirmativo(request,'postulate.puede_entrar_usuario_postulate'):
            user = User.objects.get(pk=request.GET['id'])
            if not persona.usuario.is_staff:
                return HttpResponseRedirect('/?info=no puede entrar como este usuario')
            if not user.is_active:
                return HttpResponseRedirect('/?info=usuario no activo')
            if user.is_superuser:
                return HttpResponseRedirect('/?info=no puede entrar como este usuario')
            if 'app' in request.GET:
                app = request.GET['app']
                if app == 'sie':
                    if not puede_realizar_accion_afirmativo(request,'sga.puede_entrar_como_estudiante'):
                        return HttpResponseRedirect('/?info=no puede entrar como este usuario')
                    fecha = datetime.now().date()
                    hora = datetime.now().time()
                    fecha_hora = fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__()
                    code = generate_code(32)
                    token = md5(str(encrypt(user.id) + fecha_hora).encode("utf-8")).hexdigest()
                    UserToken.objects.filter(user=user, action_type=4, app=4, isActive=True, usuario_creacion=persona.usuario).update(isActive=False)
                    eUserToken = UserToken(user=user,
                                           token=token,
                                           action_type=4,
                                           date_expires=datetime.now() + timedelta(days=1),
                                           app=4,
                                           isActive=True
                                           )
                    eUserToken.save(request)
                    perfilprincipal_origen = data['perfilprincipal']
                    persona_destino = Persona.objects.get(usuario_id=user.id)
                    perfilprincipal_destino = persona_destino.perfilusuario_principal_estudiante()
                    if not perfilprincipal_destino:
                        return HttpResponseRedirect(f"{request.path}?info=Estudiante {persona_destino.__str__()}: No tiene perfil de estudiante asignado")
                    UserProfileChangeToken.objects.filter(perfil_origen__persona=perfilprincipal_origen.persona,
                                                          perfil_destino__persona=perfilprincipal_destino.persona,
                                                          user_token__action_type=4,
                                                          user_token__app=4,
                                                          user_token__isActive=True).update(isActive=False)
                    eUserProfileChangeToken = UserProfileChangeToken(perfil_origen=perfilprincipal_origen,
                                                                     perfil_destino=perfilprincipal_destino,
                                                                     user_token=eUserToken,
                                                                     codigo=code,
                                                                     isActive=True
                                                                     )
                    eUserProfileChangeToken.save(request)
                    base_url = get_variable('SITE_URL_SIE')
                    send_mail_login_on(request, persona_destino, persona_anterior, request.session['tiposistema'])
                    return redirect(f'{base_url}/checktoken/{token}/{code}')
                if app == 'seleccionposgrado':
                    nombresistema = "Sistema Posgrado"
                    tiposistema = "seleccionposgrado"
                    eTemplateBaseSetting = None
                    capippriva = request.session['capippriva'] if 'capippriva' in request.session else ''
                    user.backend = 'django.contrib.auth.backends.ModelBackend'
                    log(u'%s - entro como este usuario: %s' % (persona, unicode(user)), request, "add")
                    us_anterior = request.user
                    request.session['login_manual'] = True
                    loginchangeuser(request, user)
                    request.session['login_manual'] = True
                    request.session['nombresistema'] = nombresistema
                    request.session['tiposistema'] = tiposistema
                    request.session['capippriva'] = capippriva
                    request.session['eTemplateBaseSetting'] = eTemplateBaseSetting
                    request.session['persona'] = persona = Persona.objects.get(usuario__id=user.id)
                    aspirante = InscripcionPostulante.objects.filter(persona=persona)[0]
                    request.session['postulante'] = aspirante
                    request.session['perfiles'] = perfiles = persona.mis_perfilesusuarios_app(tiposistema)
                    request.session['perfilprincipal'] = perfilprincipal = persona.perfilusuario_principal(perfiles, tiposistema)
                    request.session['user_anterior'] = us_anterior
                    if not perfilprincipal:
                        return HttpResponseRedirect('/logout')
                    return HttpResponseRedirect('/')
            if 'apli' in request.GET and 'tipoapli' in request.GET:
                nombresistema = request.GET['apli']
                tiposistema = request.GET['tipoapli']
                eTemplateBaseSetting = None
                # if 'eTemplateBaseSetting' in request.session:
                #     eTemplateBaseSetting = request.session['eTemplateBaseSetting']
                capippriva = request.session['capippriva'] if 'capippriva' in request.session else ''
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                log(u'%s - entro como este usuario: %s' % (persona, unicode(user)), request, "add")
                us_anterior = request.user
                loginchangeuser(request, user)
                request.session['nombresistema'] = nombresistema
                request.session['tiposistema'] = tiposistema
                request.session['capippriva'] = capippriva
                request.session['eTemplateBaseSetting'] = eTemplateBaseSetting
                request.session['persona'] = persona = Persona.objects.get(usuario__id=user.id)
                request.session['perfiles'] = perfiles = persona.mis_perfilesusuarios_app(tiposistema)
                request.session['perfilprincipal'] = perfilprincipal = persona.perfilusuario_principal(perfiles, tiposistema)
                request.session['user_anterior'] = us_anterior
                if not perfilprincipal:
                    return HttpResponseRedirect('/logout')
                send_mail_login_on(request, persona, persona_anterior, request.session['tiposistema'])
                return HttpResponseRedirect('/alu_requisitosmaestria')
            else:
                nombresistema = request.session['nombresistema']
                tiposistema = request.session['tiposistema']
                eTemplateBaseSetting = None
                if 'eTemplateBaseSetting' in request.session:
                    eTemplateBaseSetting = request.session['eTemplateBaseSetting']
                capippriva = request.session['capippriva'] if 'capippriva' in request.session else ''
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                log(u'%s - entro como este usuario: %s' % (persona, unicode(user)), request, "add")
                us_anterior = request.user
                request.session['login_manual'] = True
                loginchangeuser(request, user)
                request.session['login_manual'] = True
                request.session['nombresistema'] = nombresistema
                request.session['tiposistema'] = tiposistema
                request.session['capippriva'] = capippriva
                request.session['eTemplateBaseSetting'] = eTemplateBaseSetting
                request.session['persona'] = persona = Persona.objects.get(usuario__id=user.id)
                request.session['perfiles'] = perfiles = persona.mis_perfilesusuarios_app(tiposistema)
                request.session['perfilprincipal'] = perfilprincipal = persona.perfilusuario_principal(perfiles, tiposistema)
                request.session['user_anterior'] = us_anterior
                if not perfilprincipal:
                    return HttpResponseRedirect('/logout')
                send_mail_login_on(request, persona, persona_anterior, tiposistema)
                return HttpResponseRedirect('/')
        else:
            return HttpResponseRedirect(f"{request.path}?info=Acción no permitida: No tiene permisos")
    except Exception as ex:
        transaction.set_rollback(True)
        return HttpResponseRedirect('/logout')


# CAMBIO DE USUARIO DESDE EL MISMO USUARIO
@login_required(redirect_field_name='ret', login_url='/loginsga')
def changeuserdu(request):
    with transaction.atomic():
        try:
            data = {}
            adduserdata(request, data)
            if request.session['perfilprincipal'].es_estudiante():
                del request.session['matricula']
                del request.session['periodos_estudiante']
                del request.session['coordinacion']

            persona = data['persona']
            perfilprincipal = persona.perfilusuario_set.filter(id=int(encrypt(request.GET['id'])), visible=True).first()
            # perfilprincipal = PerfilUsuario.objects.get(pk=int(encrypt(request.GET['id'])))
            if not perfilprincipal:
                raise NameError('Perfil no disponible')
            if perfilprincipal.activo():
                del request.session['periodo']
                del request.session['grupos_usuarios']
                request.session['perfilprincipal'] = perfilprincipal
                if perfilprincipal.es_estudiante():
                    perfilprincipal.establecer_estudiante_principal()
                    if 'eUserProfileChangeToken' in request.session:
                        del request.session['eUserProfileChangeToken']
            return HttpResponseRedirect('/')
        except Exception as ex:
            transaction.set_rollback(True)
            return HttpResponseRedirect(f'/?info={ex.__str__()}')
        return HttpResponseRedirect('/')


# DATOS ACADEMICOS Y ADMINISTRATIVOS
def total_matriculados(periodo):
    return Matricula.objects.filter(nivel__periodo=periodo,estado_matricula__in=[2,3],status=True).count()


def total_matriculados_mujeres(periodo):
    return Matricula.objects.filter(inscripcion__persona__sexo=SEXO_FEMENINO,estado_matricula__in=[2,3], nivel__periodo=periodo,status=True).count()


def total_matriculados_hombres(periodo):
    return Matricula.objects.filter(inscripcion__persona__sexo=SEXO_MASCULINO,estado_matricula__in=[2,3], nivel__periodo=periodo,status=True).count()


def cantidad_matriculados_beca(periodo):
    return Matricula.objects.filter(becado=True, nivel__periodo=periodo,status=True,estado_matricula__in=[2,3]).count()


def porciento_matriculados_beca(periodo):
    return null_to_decimal((cantidad_matriculados_beca(periodo) / float(total_matriculados(periodo))) * 100, 2) if total_matriculados(periodo) else 0


def cantidad_matriculados_discapacidad(periodo):
    return Matricula.objects.filter(inscripcion__persona__perfilinscripcion__tienediscapacidad=True, nivel__periodo=periodo,status=True,estado_matricula__in=[2,3] ).distinct().count()


def porciento_matriculados_discapacidad(periodo):
    return null_to_decimal((cantidad_matriculados_discapacidad(periodo) / float(total_matriculados(periodo))) * 100, 2) if total_matriculados(periodo) else 0


# MATRICULADOS POR RANGO DE EDADES
def total_matriculados_menor_30(periodo):
    year30 = years_ago(30, datetime.now())
    return Matricula.objects.filter(inscripcion__persona__nacimiento__gte=year30, inscripcion__persona__nacimiento__lte=datetime.now().date(), nivel__periodo=periodo,status=True,estado_matricula__in=[2,3]).count()


def total_matriculados_31_40(periodo):
    year40 = years_ago(40, datetime.now())
    year31 = years_ago(31, datetime.now())
    return Matricula.objects.filter(status=True,estado_matricula__in=[2,3],inscripcion__persona__nacimiento__gte=year40, inscripcion__persona__nacimiento__lte=year31, nivel__periodo=periodo).count()


def total_matriculados_41_50(periodo):
    year50 = years_ago(50, datetime.now())
    year41 = years_ago(41, datetime.now())
    return Matricula.objects.filter(status=True,estado_matricula__in=[2,3],inscripcion__persona__nacimiento__gte=year50, inscripcion__persona__nacimiento__lte=year41, nivel__periodo=periodo).count()


def total_matriculados_51_60(periodo):
    year60 = years_ago(60, datetime.now())
    year51 = years_ago(51, datetime.now())
    return Matricula.objects.filter(status=True,estado_matricula__in=[2,3],inscripcion__persona__nacimiento__gte=year60, inscripcion__persona__nacimiento__lte=year51, nivel__periodo=periodo).count()


def total_matriculados_mayor_61(periodo):
    year61 = years_ago(61, datetime.now())
    return Matricula.objects.filter(status=True,estado_matricula__in=[2,3], inscripcion__persona__nacimiento__lte=year61, nivel__periodo=periodo).count()

def total_ventas_edades(reportadas, tipo, v1, v2=None):
    from posgrado.models import InscripcionCohorte
    lista = []
    datos = InscripcionCohorte.objects.filter(id__in=reportadas)
    if v2 and tipo == 'doble':
        for dat in datos:
            edad = datetime.now().year - dat.inscripcionaspirante.persona.nacimiento.year
            if edad >= v1 and edad <= v2:
                lista.append(dat.id)
    elif tipo == 'menor':
        for dat in datos:
            edad = datetime.now().year - dat.inscripcionaspirante.persona.nacimiento.year
            if edad <= v1:
                lista.append(dat.id)
    elif tipo == 'mayor':
        for dat in datos:
            edad = datetime.now().year - dat.inscripcionaspirante.persona.nacimiento.year
            if edad >= v1:
                lista.append(dat.id)
    return len(lista)

def total_ventas_prov_sexo(reportadas, tipo):
    from posgrado.models import InscripcionCohorte
    datos = None
    if tipo == 'femenino':
        datos = InscripcionCohorte.objects.filter(id__in=reportadas, inscripcionaspirante__persona__sexo__id=1).count()
    elif tipo == 'masculino':
        datos = InscripcionCohorte.objects.filter(id__in=reportadas, inscripcionaspirante__persona__sexo__id=2).count()
    return datos

def materias_abiertas(request, alumno=False, secretaria=False):
    try:
        validarcupos = False # IMSM
        asignatura = Asignatura.objects.get(pk=request.POST['ida'])
        paralelosseleccionadas = None
        if 'paralelosseleccionadas' in request.POST:
            paralelosseleccionadas = request.POST['paralelosseleccionadas']
        asigmalla = None
        if 'idam' in request.POST and request.POST['idam'] != "0":
            asigmalla = AsignaturaMalla.objects.get(pk=request.POST['idam'])
        inscripcion = Inscripcion.objects.get(pk=request.POST['id'])


        # IMSM
        puede_seleccionar = True
        # SE COMENTO BLOQUE DE TERCERA MATRICULA PORQUE YA SE VALIDA AL MATRICULARSE QUE ESCOJA PRIMERO LAS ASIGNATURAS POR 3RA VEZ
        # if inscripcion.tiene_tercera_matricula():
        #     if inscripcion.recordacademico_set.filter(aprobada=False, asignatura=asignatura).exists():
        #         materia_en_record = inscripcion.recordacademico_set.filter(aprobada=False, asignatura=asignatura)[0]
        #         if materia_en_record.historicorecordacademico_set.values("id").count() == 2:
        #             puede_seleccionar = True
        #         else:
        #             puede_seleccionar = False
        # IMSM

        nivelmallaaux = AsignaturaMalla.objects.filter(asignatura=asignatura, malla=inscripcion.mi_malla(), status=True)
        nivelmalla = None
        if nivelmallaaux:
            nivelmalla = nivelmallaaux[0].nivelmalla
        estado = inscripcion.estado_asignatura(asignatura)


        hoy = datetime.now().date()
        minivelmalla = inscripcion.mi_nivel().nivel
        nivel = Nivel.objects.get(pk=request.POST['nivel'])
        if alumno:
            if not paralelosseleccionadas:
                materiasabiertas = Materia.objects.filter(Q(asignatura=asignatura, inicio__gte=hoy, nivel__cerrado=False, nivel__periodo=nivel.periodo), status=True).order_by('id')
            else:
                materiasabiertas = Materia.objects.filter(Q(asignatura=asignatura, inicio__gte=hoy, nivel__cerrado=False, nivel__periodo=nivel.periodo), paralelo=paralelosseleccionadas, status=True).order_by('id')
            if estado == 2:
                # if variable_valor('VALIDAR_HORARIO_CUPO_MATERIA_VIRTUAL'):
                #     materiasabiertas = materiasabiertas.filter(clase__isnull=False, clase__activo=True)
                # se quito este codigo y se dejo solo para que vea las materias del periodo seleccionado
                # materiasabiertas = Materia.objects.filter(Q(asignaturamalla=asigmalla, nivel__cerrado=False, fin__gte=hoy, clase__isnull=False, clase__activo=True) | Q(asignatura=asignatura, rectora=True, nivel__cerrado=False, fin__gte=hoy, nivel__periodo=nivel.periodo, carrerascomunes__id__in=[inscripcion.carrera.id], clase__isnull=False, clase__activo=True) | Q(asignatura=asignatura, rectora=True, nivel__cerrado=False, fin__gte=hoy, nivel__periodo=nivel.periodo, carrerascomunes__isnull=True, clase__isnull=False, clase__activo=True)).distinct().order_by('id')

                # SE BLOQUEO PARA QUE SOLO SALGAN LAS MATERIAS DE LA CARRERA
                # materiasabiertas = Materia.objects.filter(Q(asignatura=asignatura, rectora=True, nivel__cerrado=False, nivel__periodo=nivel.periodo, carrerascomunes__id__in=[inscripcion.carrera.id], clase__isnull=False, clase__activo=True) | Q(asignatura=asignatura, rectora=True, nivel__cerrado=False, nivel__periodo=nivel.periodo, carrerascomunes__isnull=True, clase__isnull=False, clase__activo=True)).distinct().order_by('id')
                if nivelmallaaux:
                    materiasabiertas = materiasabiertas.filter(asignaturamalla__malla=inscripcion.mi_malla()).distinct().order_by('id')
                else:
                    if not paralelosseleccionadas:
                        idmateriasturismo = Materia.objects.values_list('id', flat=True).filter(nivel__cerrado=False, nivel__periodo=nivel.periodo, asignaturamalla__malla__carrera__id=7, status=True).distinct()
                    else:
                        idmateriasturismo = Materia.objects.values_list('id', flat=True).filter(nivel__cerrado=False, nivel__periodo=nivel.periodo, asignaturamalla__malla__carrera__id=7, paralelo=paralelosseleccionadas, status=True).distinct()
                    materiasabiertas = materiasabiertas.exclude(id__in=idmateriasturismo).distinct().order_by('id')
            else:
                # se quito este codigo y se dejo solo para que vea las materias del periodo seleccionado
                # materiasabiertas = Materia.objects.filter(Q(asignaturamalla=asigmalla, nivel__cerrado=False, fin__gte=hoy, clase__isnull=False, clase__activo=True) | Q(asignatura=asignatura, rectora=True, nivel__cerrado=False, fin__gte=hoy, nivel__periodo=nivel.periodo, carrerascomunes__id__in=[inscripcion.carrera.id], clase__isnull=False, clase__activo=True) | Q(asignatura=asignatura, rectora=True, nivel__cerrado=False, fin__gte=hoy, nivel__periodo=nivel.periodo, carrerascomunes__isnull=True, clase__isnull=False, clase__activo=True)).distinct().order_by('id')

                # SE BLOQUEO PARA QUE SOLO SALGAN LAS MATERIAS DE LA CARRERA
                # materiasabiertas = Materia.objects.filter(Q(asignatura=asignatura, rectora=True, nivel__cerrado=False, nivel__periodo=nivel.periodo, carrerascomunes__id__in=[inscripcion.carrera.id], clase__isnull=False, clase__activo=True) | Q(asignatura=asignatura, rectora=True, nivel__cerrado=False, nivel__periodo=nivel.periodo, carrerascomunes__isnull=True, clase__isnull=False, clase__activo=True)).distinct().order_by('id')
                if nivelmallaaux:
                    materiasabiertas = materiasabiertas.filter(asignaturamalla__malla=inscripcion.mi_malla()).distinct().order_by('id')
                else:
                    if not paralelosseleccionadas:
                        idmateriasturismo = Materia.objects.values_list('id', flat=True).filter(nivel__cerrado=False, nivel__periodo=nivel.periodo, asignaturamalla__malla__carrera__id=7, status=True).distinct()
                    else:
                        idmateriasturismo = Materia.objects.values_list('id', flat=True).filter(nivel__cerrado=False, nivel__periodo=nivel.periodo, asignaturamalla__malla__carrera__id=7, paralelo=paralelosseleccionadas, status=True).distinct()
                    materiasabiertas = materiasabiertas.exclude(id__in=idmateriasturismo).distinct().order_by('id')
        else:
            # se quito este codigo y se dejo solo para que vea las materias del periodo seleccionado
            # materiasabiertas = Materia.objects.filter(Q(asignaturamalla=asigmalla, nivel__cerrado=False, fin__gte=hoy, clase__isnull=False, clase__activo=True) | Q(asignatura=asignatura, rectora=True, nivel__cerrado=False, fin__gte=hoy, nivel__periodo=nivel.periodo, carrerascomunes__id__in=[inscripcion.carrera.id], clase__isnull=False, clase__activo=True) | Q(asignatura=asignatura, rectora=True, nivel__cerrado=False, fin__gte=hoy, nivel__periodo=nivel.periodo, carrerascomunes__isnull=True, clase__isnull=False, clase__activo=True)).distinct().order_by('id')
            # materiasabiertas = Materia.objects.filter(Q(asignatura=asignatura,  nivel__cerrado=False, nivel__periodo=nivel.periodo, carrerascomunes__id__in=[inscripcion.carrera.id], clase__isnull=False, clase__activo=True) | Q(asignatura=asignatura, nivel__cerrado=False, nivel__periodo=nivel.periodo, carrerascomunes__isnull=True, clase__isnull=False, clase__activo=True), status=True).distinct().order_by('id')
            if not paralelosseleccionadas:
                materiasabiertas = Materia.objects.filter(Q(asignatura=asignatura,  nivel__cerrado=False, nivel__periodo=nivel.periodo, carrerascomunes__id__in=[inscripcion.carrera.id]) | Q(asignatura=asignatura, nivel__cerrado=False, nivel__periodo=nivel.periodo, carrerascomunes__isnull=True), status=True).distinct().order_by('id')
            else:
                materiasabiertas = Materia.objects.filter(Q(asignatura=asignatura,  nivel__cerrado=False, nivel__periodo=nivel.periodo, carrerascomunes__id__in=[inscripcion.carrera.id]) | Q(asignatura=asignatura, nivel__cerrado=False, nivel__periodo=nivel.periodo, carrerascomunes__isnull=True), paralelo=paralelosseleccionadas, status=True).distinct().order_by('id')
        materias = {}
        # VALIDA SI NO TIENE HORARIO SOLO PARA PRESENTAR EL MENSAJE Q DEBE TENER HORARIO
        mensajenotienehorario = True
        tipo_materia = 2
        for materia in materiasabiertas:
            if materia.nivel.nivellibrecoordinacion_set.exists():
                origen = materia.nivel.nivellibrecoordinacion_set.all()[0].coordinacion.alias
            else:
                origen = materia.nivel.carrera.nombre
            mat = {}
            paralelo = materia.paralelo
            novalidar_horario_cupo_materiavirtual = True
            # if materia.tipomateria == 2:
            #     novalidar_horario_cupo_materiavirtual = True
            #SECRETARIA PUEDE MATRICULAR CON CUPOS ADICIONAL

            if validarcupos:# IMSM
                tiene_cupos_adicional = False
                if not materia.capacidad_disponible() > 0 and materia.cupos_restante_adicional() > 0 and secretaria:
                    tiene_cupos_adicional = True
            else:# IMSM
                tiene_cupos_adicional = True # IMSM

            # novalidar_horario_cupo_materiavirtual = materia.tipomateria == 2 and not variable_valor('VALIDAR_HORARIO_CUPO_MATERIA_VIRTUAL')

            # HABILITAR LA LINEA SIGUIENTE PARA EL PROXIMO PERIODO: IMSM
            if materia.capacidad_disponible() > 0 or HOMITIRCAPACIDADHORARIO or tiene_cupos_adicional:
                # if tiene_cupos_adicional:# QUITAR ESTA LINEA Y HABILITAR LA ANTERIOR PARA EL PROXIMO PERIODO: IMSM
                horariosmateria= materia.clases_informacion_teoria_practica()
                #SE PODRAN MATRICULAS LOS DE FACS CON  TIPO FIRMA ACTA Y PRACTICA
                # matricular_facs = materia.matricular_sin_horario()
                matricular_facs = True
                #SI TIENE HORARIO Y TIPO MATERIA ES 1(PRESENCIAL) PRESENTA PARA LA MATRICULACION, CASO CONTRARIO ES TIPO MATERIA 2 PRESENTA SI NO TIENE HORARIO
                if horariosmateria or matricular_facs:
                    mensajenotienehorario = False
                    mat[materia.id] = {'nivel': to_unicode(materia.nivel.nivelmalla.nombre) if materia.nivel.nivelmalla else "",
                                       # 'idnivel': to_unicode(materia.asignaturamalla.nivelmalla.id) if materia.asignaturamalla.nivelmalla else "",
                                       'sede': to_unicode(materia.nivel.sede.nombre) if materia.nivel.sede else "",
                                       'profesor': (materia.profesor_principal().persona.nombre_completo()) if materia.profesor_principal() else 'SIN DEFINIR',
                                       'horario': "<br>".join(x for x in horariosmateria),
                                       'id': materia.id,
                                       'tipomateria': materia.tipomateria,
                                       'teopract': 2 if materia.asignaturamalla.practicas else 1,
                                       'inicio': materia.inicio.strftime("%d-%m-%Y"),
                                       'session': to_unicode(materia.nivel.sesion.nombre),
                                       'fin': materia.fin.strftime("%d-%m-%Y"), 'identificacion': materia.identificacion,
                                       'coordcarrera': origen,
                                       'paralelo': paralelo,
                                       'cupo': materia.cupo if novalidar_horario_cupo_materiavirtual else materia.capacidad_disponible(),
                                       'matriculados': materia.cantidad_matriculas_materia(),
                                       'novalhorcup': not variable_valor('VALIDAR_HORARIO_CUPO_MATERIA_VIRTUAL'),
                                       'carrera': to_unicode(materia.asignaturamalla.malla.carrera.nombre) if materia.asignaturamalla.malla.carrera.nombre else "",
                                       'cupoadicional': materia.cupos_restante_adicional()}
                    materias.update(mat)
                else:
                    mensajenotienehorario = True
            tipo_materia=materia.tipomateria
        mensaje = 'NO EXISTEN CUPOS DISPONIBLES O MATERIAS PROGRAMADAS'

        estaabierta = True if materiasabiertas else False

        # IMSM
        if puede_seleccionar is False:
            materias = {}
        # IMSM

        if nivelmallaaux:
            return JsonResponse({"result": "ok", "idd": asignatura.id, "asignatura": unicode(asignatura.nombre)+" "+unicode(nivelmalla), "abiertas": materiasabiertas.__len__(), "disponibles": materias.__len__(), "materias": materias, "notienehorario":mensajenotienehorario, "mensaje":mensaje, "estaabierta" : estaabierta, "puede_seleccionar": puede_seleccionar})
        else:
            return JsonResponse({"result": "ok", "idd": asignatura.id, "asignatura": unicode(asignatura.nombre), "abiertas": materiasabiertas.__len__(), "disponibles": materias.__len__(), "materias": materias, "notienehorario":mensajenotienehorario, "mensaje":mensaje, "estaabierta" : estaabierta, "puede_seleccionar": puede_seleccionar})
    except Exception as ex:
        return JsonResponse({"result": "bad", 'error': unicode(ex)})


def materias_abiertas2(request, alumno=False, secretaria=False):
    try:
        validarcupos = False # IMSM
        asignatura = Asignatura.objects.get(pk=request.POST['ida'])
        asigmalla = None
        if 'idam' in request.POST and request.POST['idam'] != "0":
            asigmalla = AsignaturaMalla.objects.get(pk=request.POST['idam'])
        inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
        # IMSM
        puede_seleccionar = True
        nivelmallaaux = AsignaturaMalla.objects.filter(asignatura=asignatura, malla=inscripcion.mi_malla(), status=True)
        nivelmalla = None
        if nivelmallaaux:
            nivelmalla = nivelmallaaux[0].nivelmalla
        estado = inscripcion.estado_asignatura(asignatura)
        hoy = datetime.now().date()
        minivelmalla = inscripcion.mi_nivel().nivel
        nivel = Nivel.objects.get(pk=request.POST['nivel'])
        #-----------------------------------------------------------
        malla_materias_actuales_creadas = 353 #MODULOS DE INGLES (ABRIL 2019) PRESENCIAL 2019.0000 - SNIESE
        nivel_materias_ofertadas_actual_creadas = Nivel.objects.get(pk=1501)
        id_materias_ofertadas_actual_creadas = nivel_materias_ofertadas_actual_creadas.materia_set.values_list('id',flat=True).filter(status=True, asignaturamalla__malla_id=malla_materias_actuales_creadas)
        #-----------------------------------------------------------
        if alumno:
            materiasabiertas = Materia.objects.filter(Q(asignatura=asignatura,nivel_id=nivel_materias_ofertadas_actual_creadas.pk, nivel__cerrado=False), status=True,id__in=id_materias_ofertadas_actual_creadas ).exclude(asignaturamalla__malla__carrera__id__in=[7,138,129,90,157]).order_by('id')
        else:
            materiasabiertas = Materia.objects.filter(Q(asignatura=asignatura,nivel_id=nivel_materias_ofertadas_actual_creadas.pk,  nivel__cerrado=False, nivel__periodo=nivel.periodo, carrerascomunes__id__in=[inscripcion.carrera.id]) | Q(asignatura=asignatura, nivel__cerrado=False, nivel__periodo=nivel.periodo, carrerascomunes__isnull=True), status=True,id__in=id_materias_ofertadas_actual_creadas).distinct().order_by('id')
        materias = {}
        # VALIDA SI NO TIENE HORARIO SOLO PARA PRESENTAR EL MENSAJE Q DEBE TENER HORARIO
        mensajenotienehorario = False
        tipo_materia = 2
        for materia in materiasabiertas:
            if materia.nivel.nivellibrecoordinacion_set.exists():
                origen = materia.nivel.nivellibrecoordinacion_set.all()[0].coordinacion.alias
            else:
                origen = materia.nivel.carrera.nombre
            mat = {}
            paralelo = materia.paralelo
            novalidar_horario_cupo_materiavirtual = True
            # HABILITAR LA LINEA SIGUIENTE PARA EL PROXIMO PERIODO: IMSM
            if materia.capacidad_disponible() > 0:
                horariosmateria= materia.clases_informacion_teoria_practica()
                # if horariosmateria:
                mensajenotienehorario = False
                mat[materia.id] = {'nivel': to_unicode(materia.nivel.nivelmalla.nombre) if materia.nivel.nivelmalla else "",
                                   'sede': to_unicode(materia.nivel.sede.nombre) if materia.nivel.sede else "",
                                   'profesor': (materia.profesor_principal().persona.nombre_completo()) if materia.profesor_principal() else 'SIN DEFINIR',
                                   'horario': "<br>".join(x for x in horariosmateria), 'id': materia.id,
                                   'tipomateria': materia.tipomateria,
                                   'teopract':2 if materia.asignaturamalla.practicas else 1,
                                   'inicio': materia.inicio.strftime("%d-%m-%Y"), 'session': to_unicode(materia.nivel.sesion.nombre),
                                   'fin': materia.fin.strftime("%d-%m-%Y"), 'identificacion': materia.identificacion,
                                   'coordcarrera': origen, 'paralelo': paralelo, 'cupo': materia.cupo if novalidar_horario_cupo_materiavirtual else materia.capacidad_disponible(),
                                   'matriculados': materia.cantidad_matriculas_materia(),
                                   'novalhorcup': variable_valor('VALIDAR_HORARIO_CUPO_MATERIA_VIRTUAL'),
                                   'carrera': to_unicode(materia.asignaturamalla.malla.carrera.nombre) if materia.asignaturamalla.malla.carrera.nombre else "",
                                   'cupoadicional': materia.cupos_restante_adicional()}
                materias.update(mat)
                # else:
                #     mensajenotienehorario = False
            tipo_materia=materia.tipomateria
        mensaje = 'NO EXISTEN CUPOS DISPONIBLES O MATERIAS PROGRAMADAS'

        estaabierta = True if materiasabiertas else False

        # IMSM
        if puede_seleccionar is False:
            materias = {}
        # IMSM

        if nivelmallaaux:
            return JsonResponse({"result": "ok", "idd": asignatura.id, "asignatura": unicode(asignatura.nombre)+" "+unicode(nivelmalla), "abiertas": materiasabiertas.__len__(), "disponibles": materias.__len__(), "materias": materias, "notienehorario":mensajenotienehorario, "mensaje":mensaje, "estaabierta" : estaabierta, "puede_seleccionar": puede_seleccionar})
        else:
            return JsonResponse({"result": "ok", "idd": asignatura.id, "asignatura": unicode(asignatura.nombre), "abiertas": materiasabiertas.__len__(), "disponibles": materias.__len__(), "materias": materias, "notienehorario":mensajenotienehorario, "mensaje":mensaje, "estaabierta" : estaabierta, "puede_seleccionar": puede_seleccionar})
    except Exception as ex:
        return JsonResponse({"result": "bad", 'error': unicode(ex)})

def conflicto_materias_seleccionadas(materias):
    if CHEQUEAR_CONFLICTO_HORARIO:
        # materias = materias.filter(cerrado=False, fin__gte=datetime.now().date())
        clasesmaterias = Clase.objects.filter(materia__in=materias, activo=True, fin__gte=datetime.now().date(), status=True, materia__status=True, materia__profesormateria__status=True).order_by('dia')
        clasesverificadas = []
        for clase in clasesmaterias:
            clasesverificadas.append(clase.id)
            if clasesmaterias.filter((Q(turno__comienza__lte=clase.turno.termina, turno__termina__gte=clase.turno.termina, dia=clase.dia) | Q(turno__comienza__lte=clase.turno.comienza, turno__termina__gte=clase.turno.comienza, dia=clase.dia)) & (Q(inicio__lte=clase.inicio, fin__gte=clase.inicio) | Q(inicio__lte=clase.fin, fin__gte=clase.fin)), status=True, materia__status=True, materia__profesormateria__status=True).exclude(id__in=clasesverificadas).exists():
                conflicto = clasesmaterias.filter((Q(turno__comienza__lte=clase.turno.termina, turno__termina__gte=clase.turno.termina, dia=clase.dia) | Q(turno__comienza__lte=clase.turno.comienza, turno__termina__gte=clase.turno.comienza, dia=clase.dia)) & (Q(inicio__lte=clase.inicio, fin__gte=clase.inicio) | Q(inicio__lte=clase.fin, fin__gte=clase.fin)), status=True, materia__status=True, materia__profesormateria__status=True).exclude(id__in=clasesverificadas)[0]
                if ProfesorMateria.objects.filter(materia=clase.materia, tipoprofesor=1, status=True):
                    profe = ProfesorMateria.objects.filter(materia=clase.materia, tipoprofesor=1, status=True)[0]
                    return "conflicto de horario: " + to_unicode(clase.materia.asignatura.nombre) + "(" + to_unicode(clase.materia.identificacion) + ") y " + to_unicode(conflicto.materia.asignatura.nombre) + "(" + to_unicode(conflicto.materia.identificacion) + ") DIA: " + conflicto.dia.__str__() + " PROFESOR " + profe.profesor.persona.apellido1 + " " + profe.profesor.persona.apellido2 + " " + " " + profe.profesor.persona.nombres
                else:
                    return "conflicto de horario: " + to_unicode(clase.materia.asignatura.nombre) + "(" + to_unicode(clase.materia.identificacion) + ") y " + to_unicode(conflicto.materia.asignatura.nombre) + "(" + to_unicode(conflicto.materia.identificacion) + ") DIA: " + conflicto.dia.__str__()
    return ""


def conflicto_estudiante_conpracticas_seleccionadas(matricula, mispracticas):
    # MIS PRACTICAS DEBE LLEGAR ENCRIPTADO EL ID DEL PROFESORMATERIA Y EL ID ENCRIPTADO DEL GRUPO
    from itertools import chain
    materias = Materia.objects.filter(id__in=matricula.materiaasignada_set.values_list('materia__id').filter(sinasistencia=False),status=True)
    alumnaspracticascongrupo = AlumnosPracticaMateria.objects.values_list('profesormateria__id','grupoprofesor__id').filter(materiaasignada__materia__id__in=materias.values_list('id'), materiaasignada__matricula=matricula, grupoprofesor__isnull=False)
    listaprofemateriaid_congrupo = []
    for x in mispracticas:
        listaprofemateriaid_congrupo.append([int(encrypt(x[0])), int(encrypt(x[1]))])
    listaprofemateriaid_congrupo = list(chain(alumnaspracticascongrupo, listaprofemateriaid_congrupo))
    conflicto = conflicto_materias_estudiante(materias=materias, lista_pm_grupo=listaprofemateriaid_congrupo)
    return conflicto


def matricular_estudiante_enpracticas(request, matricula, mispracticas):
    try:
        from itertools import chain
        if not mispracticas:
            return JsonResponse({"result": "bad", 'mensaje': u'Debe seleccionar al menos una práctica'})
        materias = Materia.objects.filter(id__in=matricula.materiaasignada_set.values_list('matricula__id').filter(sinasistencia=False),status=True)
        alumnaspracticascongrupo = AlumnosPracticaMateria.objects.values_list('profesormateria__id', 'grupoprofesor__id').filter(materiaasignada__materia__id__in=materias.values_list('id'), materiaasignada__matricula=matricula, grupoprofesor__isnull=False)
        listaprofemateriaid_congrupo = []
        listagrupos = []
        listamateriaasignada = []
        for x in mispracticas:
            listaprofemateriaid_congrupo.append([int(encrypt(x[0])), int(encrypt(x[1]))])
            listagrupos.append(int(encrypt(x[1])))
            listamateriaasignada.append(int(encrypt(x[2])))
        listaprofemateriaid_congrupo = list(chain(alumnaspracticascongrupo, listaprofemateriaid_congrupo))
        # VERIFICA SI HAY HAY CUPOS
        gruposprofesor = GruposProfesorMateria.objects.filter(pk__in=listagrupos)
        for grupoprofesor in gruposprofesor:
            if not grupoprofesor.cuposdisponiblesgrupoprofesor_congrupos() > 0:
                return JsonResponse({"result": "bad", 'mensaje': u'No hay cupos disponibles.'})
        for x in mispracticas:
            materiaasignada = MateriaAsignada.objects.get(pk=int(encrypt(x[2])))
            grupoprofesor = GruposProfesorMateria.objects.get(pk=int(encrypt(x[1])))
            if AlumnosPracticaMateria.objects.values('id').filter(materiaasignada=materiaasignada, status=True).exists():
                alumnopractica = AlumnosPracticaMateria.objects.filter(materiaasignada=materiaasignada, status=True)[0]
                alumnopractica.profesormateria = grupoprofesor.profesormateria
                alumnopractica.grupoprofesor = grupoprofesor
            else:
                alumnopractica = AlumnosPracticaMateria(profesormateria=grupoprofesor.profesormateria,
                                                        materiaasignada=materiaasignada,
                                                        grupoprofesor=grupoprofesor)
            alumnopractica.save(request)
            log(u'Asigno practica en la materiaasignada(%s) - profesormateria(%s) - grupoprofesor(%s)' % (materiaasignada, grupoprofesor.profesormateria, grupoprofesor.id), request, "add")
        # VERIFICA SI HAY CONFLICTOS
        conflicto = matricula.verificar_conflicto_en_materias()
        if conflicto:
            transaction.set_rollback(True)
            return JsonResponse({"result": "bad", "mensaje": conflicto})
        return JsonResponse({"result": "ok"})
    except Exception as ex:
        transaction.set_rollback(True)
        return JsonResponse({"result": "bad", 'mensaje': u'Error al matricular estudiante.'})


def matricular_estudiante_enpracticas_masivo(request, matricula, mispracticas, materiaasignada):
    try:
        from itertools import chain
        if not mispracticas:
            return JsonResponse({"result": "bad", 'mensaje': u'Debe seleccionar al menos una práctica'})
        listaprofemateriaid_congrupo = []
        listagrupos = []
        listamateriaasignada = []
        for x in mispracticas:
            listaprofemateriaid_congrupo.append([int(encrypt(x[0])), int(encrypt(x[1]))])
            listagrupos.append(int(encrypt(x[1])))
            listamateriaasignada.append(int(encrypt(x[2])))
        # VERIFICA SI HAY HAY CUPOS
        gruposprofesor = GruposProfesorMateria.objects.filter(pk__in=listagrupos)
        for grupoprofesor in gruposprofesor:
            if not grupoprofesor.cuposdisponiblesgrupoprofesor_congrupos() > 0:
                return JsonResponse({"result": "bad", 'mensaje': u'No hay cupos disponibles.'})
        for x in mispracticas:
            grupoprofesor = GruposProfesorMateria.objects.get(pk=int(encrypt(x[1])))
            if AlumnosPracticaMateria.objects.values('id').filter(materiaasignada=materiaasignada, status=True).exists():
                alumnopractica = AlumnosPracticaMateria.objects.filter(materiaasignada=materiaasignada, status=True)[0]
                alumnopractica.profesormateria = grupoprofesor.profesormateria
                alumnopractica.grupoprofesor = grupoprofesor
            else:
                alumnopractica = AlumnosPracticaMateria(profesormateria=grupoprofesor.profesormateria,
                                                        materiaasignada=materiaasignada,
                                                        grupoprofesor=grupoprofesor)
            alumnopractica.save(request)
            log(u'Asigno practica en la materiaasignada(%s) - profesormateria(%s) - grupoprofesor(%s)' % (materiaasignada, grupoprofesor.profesormateria, grupoprofesor.id), request, "add")
        # VERIFICA SI HAY CONFLICTOS
        # conflicto = matricula.verificar_conflicto_en_materias()
        # if conflicto:
        #     transaction.set_rollback(True)
        #     return JsonResponse({"result": "bad", "mensaje": conflicto})
    except Exception as ex:
        transaction.set_rollback(True)
        return JsonResponse({"result": "bad", 'mensaje': u'Error al matricular estudiante.'})

def conflicto_materias_estudiante(materias, practicas_pm=None, lista_pm_grupo=None, extraerlistaclasesconflicto=False):
    if CHEQUEAR_CONFLICTO_HORARIO:
        validar_virtual=variable_valor('VALIDAR_HORARIO_CUPO_MATERIA_VIRTUAL')
        # SE VERIFICA CON LAS CLASES DE LAS TEORICAS SOLO PRESENCIAL, NO VALIDA HORARIO DE TIPO MATERIA VIRTUAL
        clasessinpractica = Clase.objects.values_list('id').filter(materia__in=materias, activo=True, fin__gte=datetime.now().date(), status=True, materia__status=True, materia__profesormateria__status=True).exclude(tipoprofesor__in=[2, 13]).order_by('dia')
        if not validar_virtual:
            clasessinpractica = clasessinpractica.filter(materia__tipomateria=1)
        # SE VERIFICA CON LAS CLASES DE LAS PRACTICAS SIN PARALELO
        clasespracticas = []
        if practicas_pm:
            clasespracticas = Clase.objects.filter(activo=True, tipoprofesor__in=[2, 13], fin__gte=datetime.now().date(), status=True, materia__status=True, materia__profesormateria__status=True, profesor__in = [pm.profesor for pm in practicas_pm], materia__profesormateria__in=practicas_pm).order_by('dia')
            if not validar_virtual:
                clasespracticas = clasespracticas.filter(materia__tipomateria=1)
            clasespracticas = clasespracticas.values_list('id')
        #HORARIO CON PARALELO LISTA[ID_PROFESORMATERIA, PARALELO] ------------------------------------------
        id_clase_congrupo = []
        if lista_pm_grupo:
            for x in lista_pm_grupo:
                proma = ProfesorMateria.objects.get(id=int(x[0]))
                clasespracticas_paralelo = Clase.objects.filter(activo=True, tipoprofesor__in=[2, 13], fin__gte=datetime.now().date(), status=True, materia__status=True, materia__profesormateria__status=True,profesor=proma.profesor,materia__profesormateria=proma, grupoprofesor=int(x[1])).order_by('dia')
                if not validar_virtual:
                    clasespracticas_paralelo = clasespracticas_paralelo.filter(materia__tipomateria=1)
                clasespracticas_paralelo = clasespracticas_paralelo.values_list('id', flat=True)
                id_clase_congrupo.extend(clasespracticas_paralelo)
        #---------FIN---------
        clasesmaterias = Clase.objects.filter(Q(pk__in=clasessinpractica) | Q(pk__in=clasespracticas) | Q(pk__in=id_clase_congrupo)).distinct().order_by('dia')
        clasesverificadas = []
        for clase in clasesmaterias:
            clasesverificadas.append(clase.id)
            # if clasesmaterias.filter((Q(turno__comienza__lte=clase.turno.termina, turno__termina__gte=clase.turno.termina, dia=clase.dia) | Q(turno__comienza__lte=clase.turno.comienza, turno__termina__gte=clase.turno.comienza, dia=clase.dia)) & (Q(inicio__lte=clase.inicio, fin__gte=clase.inicio) | Q(inicio__lte=clase.fin, fin__gte=clase.fin)), status=True, materia__status=True, materia__profesormateria__status=True).exclude(id__in=clasesverificadas).exists():
            conflicto = clasesmaterias.filter((Q(turno__comienza__lte=clase.turno.termina,
                                                 turno__termina__gte=clase.turno.termina,
                                                 dia=clase.dia) |
                                               Q(turno__comienza__lte=clase.turno.comienza,
                                                 turno__termina__gte=clase.turno.comienza,
                                                 dia=clase.dia)) &
                                              ((Q(inicio__gte=clase.inicio) & Q(fin__lte=clase.fin)) | (Q(inicio__lte=clase.inicio) & Q(fin__gte=clase.fin)) | (Q(inicio__lte=clase.fin) & Q(inicio__gte=clase.inicio)) | (Q(fin__gte=clase.inicio) & Q(fin__lte=clase.fin))), status=True, materia__status=True, materia__profesormateria__status=True).exclude(id__in=clasesverificadas)
            if conflicto.exists():
                conflicto = conflicto[0]
                if not extraerlistaclasesconflicto:
                    return "FCME: conflicto de horario " + to_unicode(clase.materia.asignatura.nombre) + "(" + to_unicode(clase.materia.identificacion) + ") y " + to_unicode(conflicto.materia.asignatura.nombre) + "(" + to_unicode(conflicto.materia.identificacion) + ") DIA: " + conflicto.dia.__str__()
                else:
                    return [clase, conflicto]
    return ""


def conflicto_materias_seleccionadas_aux(materias, profesormateria):
    profesor= profesormateria.profesor
    if CHEQUEAR_CONFLICTO_HORARIO:
        # materias = materias.filter(cerrado=False, fin__gte=datetime.now().date())
        clasesmaterias = Clase.objects.filter(materia__in=materias, activo=True, fin__gte=datetime.now().date(), status=True, materia__status=True, materia__profesormateria__status=True).order_by('dia')
        clasesverificadas = []
        for clase in clasesmaterias:
            clasesverificadas.append(clase.id)
            tipoprofesor = ProfesorMateria.objects.filter(materia=clase.materia, status=True, profesor=profesor)[0].tipoprofesor
            if tipoprofesor == clase.tipoprofesor:
                if clasesmaterias.filter((Q(turno__comienza__lte=clase.turno.termina, turno__termina__gte=clase.turno.termina, dia=clase.dia) | Q(turno__comienza__lte=clase.turno.comienza, turno__termina__gte=clase.turno.comienza, dia=clase.dia)) & (Q(inicio__lte=clase.inicio, fin__gte=clase.inicio) | Q(inicio__lte=clase.fin, fin__gte=clase.fin)), status=True, materia__status=True, materia__profesormateria__status=True,tipoprofesor=tipoprofesor).exclude(id__in=clasesverificadas).exists():
                    conflicto = clasesmaterias.filter((Q(turno__comienza__lte=clase.turno.termina, turno__termina__gte=clase.turno.termina, dia=clase.dia) | Q(turno__comienza__lte=clase.turno.comienza, turno__termina__gte=clase.turno.comienza, dia=clase.dia)) & (Q(inicio__lte=clase.inicio, fin__gte=clase.inicio) | Q(inicio__lte=clase.fin, fin__gte=clase.fin)), status=True, materia__status=True, materia__profesormateria__status=True,tipoprofesor=tipoprofesor).exclude(id__in=clasesverificadas)[0]
                    return "conflicto de horario: " + to_unicode(clase.materia.asignatura.nombre) + "(" + to_unicode(clase.materia.identificacion) + ") y " + to_unicode(conflicto.materia.asignatura.nombre) + "(" + to_unicode(conflicto.materia.identificacion) + ") DIA: " + conflicto.dia.__str__()
    return ""


def matricularpre(request, estudiante=False):
    try:
        inscripcion = Inscripcion.objects.get(pk=int(request.POST['idmatriculaconfirmar']))
        persona = inscripcion.persona
        mismaterias = json.loads(request.POST['lista'])
        seleccion = []
        for m in mismaterias:
            seleccion.append(int(m['id']))

        # if inscripcion.sesion_id == 13:
        #     entorno = AsignaturaMalla.objects.get(asignatura_id=2678, malla=inscripcion.mi_malla())
        #     seleccion.append(entorno.id)
        #     mismaterias.append({'id': entorno.id})
        nivelid = nivel_matriculacion(inscripcion)
        nivel = Nivel.objects.get(pk=nivelid)
        paralelo = ''
        for mate in Materia.objects.filter(nivel=nivel,status=True, asignaturamalla_id__in=seleccion, asignaturamalla__malla=inscripcion.mi_malla()).order_by("paralelo"):
            if mate.capacidad_disponible() > 0:
                paralelo = mate.paralelo
                break
        materias = Materia.objects.filter(nivel=nivel, status=True, asignaturamalla_id__in=seleccion, asignaturamalla__malla=inscripcion.mi_malla(), paralelo=paralelo)
        if not materias.count() == len(mismaterias):
            return JsonResponse({"result": "bad", "reload": True,  "mensaje": u"Materias no se encuentran aperturadas %s" % paralelo})

        #MATERIAS PRACTICAS
        # CONFLICTO DE HORARIO PARA EL ESTUDIANTE
        materiasasistir = []
        for m in materias:
            if not inscripcion.sin_asistencia(m.asignatura):
                materiasasistir.append(m)
        # LIMITE DE MATRICULAS EN EL PARALELO
        if not MATRICULACION_LIBRE and nivel.capacidadmatricula <= nivel.matricula_set.values('id').count():
            return JsonResponse({"result": "bad", "reload": True, "mensaje": u"Capacidad matricula limite del paralelo: " + unicode(nivel.paralelo) + ", seleccione otro."})
        costo_materia_total = 0
        if not inscripcion.matriculado_periodo(nivel.periodo):
            matricula = Matricula(inscripcion=inscripcion,
                                  nivel=nivel,
                                  pago=False,
                                  iece=False,
                                  becado=False,
                                  porcientobeca=0,
                                  fecha=datetime.now().date(),
                                  hora=datetime.now().time(),
                                  fechatope=fechatope(datetime.now().date()))
            matricula.save(request)
            matricula.confirmar_matricula()
            for materia in materias:
                matriculacupoadicional = False
                if not materia.tiene_cupo_materia():
                    if materia.cupoadicional > 0:
                        if not materia.existen_cupos_con_adicional():
                            transaction.set_rollback(True)
                            return JsonResponse({"result": "bad", "reload": True,"mensaje": u"Capacidad limite de la materia: " + unicode(materia.asignatura) + ", seleccione otro."})
                        else:
                            matriculacupoadicional = True
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "reload": True,"mensaje": u"Capacidad limite de la materia: " + unicode( materia.asignatura) + ", seleccione otro."})
                matriculas = matricula.inscripcion.historicorecordacademico_set.values('id').filter(asignatura=materia.asignatura, fecha__lt=materia.nivel.fin).count() + 1
                materiaasignada = MateriaAsignada(matricula=matricula,
                                                  materia=materia,
                                                  notafinal=0,
                                                  asistenciafinal=0,
                                                  cerrado=False,
                                                  matriculas=matriculas,
                                                  observaciones='',
                                                  estado_id=NOTA_ESTADO_EN_CURSO)
                materiaasignada.save(request)
                if matriculacupoadicional:
                    materia.totalmatriculadocupoadicional += 1
                    materia.cupo += 1
                    materia.save(request)
                    log(u'Estudiante matriculado en cupo adicional materia: %s - estudiante: %s y se aumento un cupo en materia' % (materia, matricula), request, "add")
                materiaasignada.asistencias()
                materiaasignada.evaluacion()
                materiaasignada.save(request)
                log(u'Materia seleccionada matricula: %s' % materiaasignada, request, "add")
            matricula.actualizar_horas_creditos()
            matricula.agregacion_preunemi(request)
            matricula.actualiza_matricula()
            matricula.inscripcion.actualiza_estado_matricula()

            if estudiante:
                send_html_mail("Automatricula", "emails/matricula.html", {'sistema': request.session['nombresistema'], 'matricula': matricula, 't': miinstitucion()}, inscripcion.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[5][1])
                log(u'Automatricula estudiante: %s' % matricula, request, "add")
            else:
                send_html_mail("Matricula por secretaria", "emails/matricula.html", {'sistema': request.session['nombresistema'], 'matricula': matricula, 't': miinstitucion()}, inscripcion.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[5][1])
                log(u'Matricula secretaria: %s' % matricula, request, "add")
            valorpagar =  str(null_to_decimal(matricula.rubro_set.filter(status=True).aggregate(valor=Sum('valortotal'))['valor']))
            request.session['periodo'] = matricula.nivel.periodo
            return JsonResponse({"result": "ok", "valorpagar":valorpagar})
        else:
            transaction.set_rollback(True)
            return JsonResponse({"result": "bad", "reload": True, "mensaje": u"Ya se encuentra matriculado."})
    except Exception as ex:
        transaction.set_rollback(True)
        return JsonResponse({"result": "bad", "reload": False, "mensaje": u"Hubieron errores en la matriculacion"})


def matricular(request, validartodo, estudiante=False):
    try:
        inscripcion = Inscripcion.objects.get(pk=int(request.POST['id']))
        if not inscripcion.perfilusuario_set.filter(status=True, visible=True):
            return JsonResponse({"result": "bad", "reload": False, "mensaje": u"Esta inscripción se encuentra inactiva, por lo cual no puede matricularse en el periodo"})
        persona = inscripcion.persona
        mismaterias = json.loads(request.POST['materias'])
        mispracticas = []
        if not inscripcion.carrera.coordinaciones().values('id').filter(id=9).exists():
            mispracticas = json.loads(request.POST['practicas'])
        periodo = request.session['periodo']
        cobro = request.POST['cobro']
        # regular o irregular
        tipo_matricula_ri = request.POST['tipo_matricula']
        seleccion = []
        for m in mismaterias:
            seleccion.append(int(m))
        materias = Materia.objects.filter(id__in=seleccion, status=True)
        #MATERIAS PRACTICAS
        listaprofemateriaid_singrupo = []
        listaprofemateriaid_congrupo = []
        listagrupoprofesorid = []
        for x in mispracticas:
            if not int(x[1]) > 0:
                listaprofemateriaid_singrupo.append(int(x[0]))
            else:
                listaprofemateriaid_congrupo.append([int(x[0]), int(x[1])])
                listagrupoprofesorid.append(int(x[1]))
        profesoresmateriassingrupo = ProfesorMateria.objects.filter(id__in=listaprofemateriaid_singrupo)
        grupoprofesormateria = GruposProfesorMateria.objects.filter(id__in=listagrupoprofesorid)

        if validartodo:
            # VALIDACION MATERIAS TIENE PRACTICAS PARA LA CARRERA DE ENFERMERIA Y NUTRICION
            if inscripcion.carrera.id in [1, 3]:
                totalpracticas = materias.values('id').filter(asignaturamalla__practicas=True, id__in=profesoresmateriassingrupo.values('materia__id')).count() + materias.values('id').filter(asignaturamalla__practicas=True, id__in=grupoprofesormateria.values('profesormateria__materia__id')).count()
                if not materias.values('id').filter(asignaturamalla__practicas=True).count() == totalpracticas:
                    return JsonResponse({"result": "bad", "mensaje": "Falta de seleccionar horario de practicas"})

        if validartodo:
            # CONFLICTO DE HORARIO PARA EL ESTUDIANTE
            materiasasistir = []
            for m in materias:
                if not inscripcion.sin_asistencia(m.asignatura):
                    materiasasistir.append(m)
            # conflicto = ""
            # if materiasasistir:
            if not inscripcion.carrera.modalidad == 3:
                conflicto = conflicto_materias_estudiante(materiasasistir, profesoresmateriassingrupo, listaprofemateriaid_congrupo)
                if conflicto:
                    return JsonResponse({"result": "bad", "mensaje": conflicto})

        nivel = Nivel.objects.get(pk=request.POST['nivel'])
        if validartodo:
            # VERIFICANDO CUPO MATERIAS PRACTICAS EN PROFESOR MATERIA CON PÁRALELO
            for grupoprofemat in grupoprofesormateria:
                grupoprofemat.verificar_capacidad_limite_grupoprofesor()
            hoy = datetime.now().date()
            nivel = Nivel.objects.get(pk=request.POST['nivel'])
            # LIMITE DE MATRICULAS EN EL PARALELO
            if not MATRICULACION_LIBRE and nivel.capacidadmatricula <= nivel.matricula_set.values('id').count():
                return JsonResponse({"result": "bad", "reload": True, "mensaje": u"Capacidad matricula limite del paralelo: " + unicode(nivel.paralelo) + ", seleccione otro."})
            # habilitar cuando sea matriculacion
            # if estudiante and 'matriculamodulos' not in request.POST:
            #     if nivel.fechatopematriculaex and hoy > nivel.fechatopematriculaex:
            #         return JsonResponse({"result": "bad", "reload": False, "mensaje": u"Fuera del periodo de matriculacion."})
            # habilitar cuando sea matriculacion
            # PERDIDA DE CARRERA POR 4TA MATRICULA
            if inscripcion.tiene_perdida_carrera():
                return JsonResponse({"result": "bad", "mensaje": u"Tiene limite de matriculas."})
            # MATRICULA
            costo_materia_total = 0

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
                if 'fecha_matricula' in request.POST:
                    fecha_matricula=convertir_fecha(request.POST['fecha_matricula'])
                    if datetime.now().date() != fecha_matricula:
                        matricula.fecha=fecha_matricula
                matricula.save(request)
                # matricula.grupo_socio_economico()
                # matriculagruposocioeconomico = matricula.matriculagruposocioeconomico_set.all()[0]
                # matriculagruposocioeconomico.tipomatricula=tipo_matricula
                # matriculagruposocioeconomico.save()
                matricula.confirmar_matricula()
                codigoitinerario = 0
                for materia in materias:
                    matriculacupoadicional = False
                    if not inscripcion.itinerario or inscripcion.itinerario < 1:
                        # if inscripcion.itinerario < 1:
                        if materia.asignaturamalla.itinerario > 0:
                            codigoitinerario = int(materia.asignaturamalla.itinerario)
                    if validartodo:
                        if not materia.tiene_cupo_materia():
                            if materia.cupoadicional > 0:
                                if not materia.existen_cupos_con_adicional():
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": "bad", "reload": True,"mensaje": u"Capacidad limite de la materia: " + unicode(materia.asignatura) + ", seleccione otro."})
                                else:
                                    matriculacupoadicional = True
                            else:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": "bad", "reload": True,"mensaje": u"Capacidad limite de la materia: " + unicode( materia.asignatura) + ", seleccione otro."})

                    matriculas = matricula.inscripcion.historicorecordacademico_set.values('id').filter(asignatura=materia.asignatura, fecha__lt=materia.nivel.fin).count() + 1
                    if inscripcion.carrera.modalidad == 3:
                        materiaasignada = MateriaAsignada(matricula=matricula,
                                                          materia=materia,
                                                          notafinal=0,
                                                          sinasistencia=True,
                                                          asistenciafinal=100,
                                                          cerrado=False,
                                                          matriculas=matriculas,
                                                          observaciones='',
                                                          estado_id=NOTA_ESTADO_EN_CURSO)
                    else:
                        materiaasignada = MateriaAsignada(matricula=matricula,
                                                          materia=materia,
                                                          notafinal=0,
                                                          asistenciafinal=0,
                                                          cerrado=False,
                                                          matriculas=matriculas,
                                                          observaciones='',
                                                          estado_id=NOTA_ESTADO_EN_CURSO)
                    materiaasignada.save(request)
                    if matriculacupoadicional:
                        materia.totalmatriculadocupoadicional += 1
                        materia.cupo += 1
                        materia.save(request)
                        log(u'Estudiante matriculado en cupo adicional materia: %s - estudiante: %s y se aumento un cupo en materia' % (materia, matricula), request, "add")
                    materiaasignada.asistencias()
                    materiaasignada.evaluacion()
                    materiaasignada.mis_planificaciones()
                    materiaasignada.save(request)
                    #MATRICULA EN LA PRACTICA QUE NO TENGAN GRUPO
                    if profesoresmateriassingrupo.values('id').filter(materia=materia).exists():
                        profemate = profesoresmateriassingrupo.filter(materia=materia)[0]
                        alumnopractica = AlumnosPracticaMateria(materiaasignada= materiaasignada,
                                                                profesormateria= profemate)
                        alumnopractica.save(request)
                        log(u'Materia (%s) con profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (materia, profemate, materiaasignada, alumnopractica.id), request, "add")
                    # MATRICULA EN LA PRACTICA QUE SI TENGAN GRUPOS
                    elif grupoprofesormateria.values('id').filter(profesormateria__materia=materia).exists():
                        profemate_congrupo = grupoprofesormateria.filter(profesormateria__materia=materia)[0]

                        if validartodo:
                            profemate_congrupo.verificar_capacidad_limite_grupoprofesor()

                        alumnopractica = AlumnosPracticaMateria(materiaasignada=materiaasignada,
                                                                profesormateria=profemate_congrupo.profesormateria,
                                                                grupoprofesor=profemate_congrupo)
                        alumnopractica.save(request)
                        log(u'Materia (%s) con grupo profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (materia, profemate_congrupo, materiaasignada, alumnopractica.id), request, "add")
                    log(u'Materia seleccionada matricula: %s' % materiaasignada, request, "add")
                matricula.actualizar_horas_creditos()
                if not inscripcion.itinerario or inscripcion.itinerario < 1:
                    inscripcion.itinerario = codigoitinerario
                    inscripcion.save(request)
            with transaction.atomic():
                if int(cobro) > 0:
                    if matricula.inscripcion.mi_coordinacion().id != 9:
                        # matricula.calcular_rubros_matricula(request,int(cobro))
                        matricula.agregacion_aux(request)
                matricula.actualiza_matricula()
                matricula.inscripcion.actualiza_estado_matricula()
                matricula.grupo_socio_economico(tipo_matricula_ri)
                matricula.calcula_nivel()

            if estudiante:
                send_html_mail("Automatricula", "emails/matricula.html", {'sistema': request.session['nombresistema'], 'matricula': matricula, 't': miinstitucion()}, inscripcion.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[5][1])
                log(u'Automatricula estudiante: %s' % matricula, request, "add")
            else:
                send_html_mail("Matricula por secretaria", "emails/matricula.html", {'sistema': request.session['nombresistema'], 'matricula': matricula, 't': miinstitucion()}, inscripcion.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[5][1])
                log(u'Matricula secretaria: %s' % matricula, request, "add")
            valorpagar = str(null_to_decimal(matricula.rubro_set.filter(status=True).aggregate(valor=Sum('valortotal'))['valor']))

            descripcionarancel = ''
            valorarancel = ''
            if matricula.rubro_set.filter(status=True, tipo_id=RUBRO_ARANCEL).exists():
                ra = matricula.rubro_set.get(tipo_id=RUBRO_ARANCEL)
                descripcionarancel = ra.nombre
                valorarancel = str(ra.valortotal)

                matricula.aranceldiferido = 2
                matricula.save(request)

            ConfirmaCapacidadTecnologica.objects.filter(persona=matricula.inscripcion.persona).update(confirmado=True)

            request.session['periodo'] = matricula.nivel.periodo
            return JsonResponse({"result": "ok", "valorpagar":valorpagar, "descripcionarancel": descripcionarancel, "valorarancel": valorarancel, "phase": matricula.id})
        else:
            transaction.set_rollback(True)
            return JsonResponse({"result": "bad", "reload": True, "mensaje": u"Ya se encuentra matriculado."})
    except Exception as ex:
        transaction.set_rollback(True)
        import sys
        return JsonResponse({"result": "bad", "reload": False, "mensaje": u"Hubieron errores en la matriculacion %s - %s" % (ex, sys.exc_info()[-1].tb_lineno)})


def matricular_admision(request, validartodo):
    try:
        inscripcion = Inscripcion.objects.get(pk=int(request.POST['id']))
        persona = inscripcion.persona
        mismaterias = json.loads(request.POST['materias'])
        mispracticas = []
        if not inscripcion.carrera.coordinaciones().values('id').filter(id=9).exists():
            mispracticas = json.loads(request.POST['practicas'])
        periodo = request.session['periodo']
        cobro = request.POST['cobro']
        # regular o irregular
        tipo_matricula_ri = request.POST['tipo_matricula']
        seleccion = []
        for m in mismaterias:
            seleccion.append(int(m))
        materias = Materia.objects.filter(id__in=seleccion, status=True)
        #MATERIAS PRACTICAS
        listaprofemateriaid_singrupo = []
        listaprofemateriaid_congrupo = []
        listagrupoprofesorid = []
        for x in mispracticas:
            if not int(x[1]) > 0:
                listaprofemateriaid_singrupo.append(int(x[0]))
            else:
                listaprofemateriaid_congrupo.append([int(x[0]), int(x[1])])
                listagrupoprofesorid.append(int(x[1]))
        profesoresmateriassingrupo = ProfesorMateria.objects.filter(id__in=listaprofemateriaid_singrupo)
        grupoprofesormateria = GruposProfesorMateria.objects.filter(id__in=listagrupoprofesorid)

        if validartodo:
            # VALIDACION MATERIAS TIENE PRACTICAS PARA LA CARRERA DE ENFERMERIA Y NUTRICION
            if inscripcion.carrera.id in [1, 3]:
                totalpracticas = materias.values('id').filter(asignaturamalla__practicas=True, id__in=profesoresmateriassingrupo.values('materia__id')).count() + materias.values('id').filter(asignaturamalla__practicas=True, id__in=grupoprofesormateria.values('profesormateria__materia__id')).count()
                if not materias.values('id').filter(asignaturamalla__practicas=True).count() == totalpracticas:
                    return JsonResponse({"result": "bad", "mensaje": "Falta de seleccionar horario de practicas"})

        if validartodo:
            # CONFLICTO DE HORARIO PARA EL ESTUDIANTE
            materiasasistir = []
            for m in materias:
                if not inscripcion.sin_asistencia(m.asignatura):
                    materiasasistir.append(m)
            # conflicto = ""
            # if materiasasistir:
            if not inscripcion.carrera.modalidad == 3:
                conflicto = conflicto_materias_estudiante(materiasasistir, profesoresmateriassingrupo, listaprofemateriaid_congrupo)
                if conflicto:
                    return JsonResponse({"result": "bad", "mensaje": conflicto})

        nivel = Nivel.objects.get(pk=request.POST['nivel'])
        if validartodo:
            # VERIFICANDO CUPO MATERIAS PRACTICAS EN PROFESOR MATERIA CON PÁRALELO
            for grupoprofemat in grupoprofesormateria:
                grupoprofemat.verificar_capacidad_limite_grupoprofesor()
            hoy = datetime.now().date()
            nivel = Nivel.objects.get(pk=request.POST['nivel'])
            # LIMITE DE MATRICULAS EN EL PARALELO
            if not MATRICULACION_LIBRE and nivel.capacidadmatricula <= nivel.matricula_set.values('id').count():
                return JsonResponse({"result": "bad", "reload": True, "mensaje": u"Capacidad matricula limite del paralelo: " + unicode(nivel.paralelo) + ", seleccione otro."})
            # habilitar cuando sea matriculacion
            # if estudiante and 'matriculamodulos' not in request.POST:
            #     if nivel.fechatopematriculaex and hoy > nivel.fechatopematriculaex:
            #         return JsonResponse({"result": "bad", "reload": False, "mensaje": u"Fuera del periodo de matriculacion."})
            # habilitar cuando sea matriculacion
            # PERDIDA DE CARRERA POR 4TA MATRICULA
            if inscripcion.tiene_perdida_carrera():
                return JsonResponse({"result": "bad", "mensaje": u"Tiene limite de matriculas."})
            # MATRICULA
            costo_materia_total = 0

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
                                      termino=False,
                                      fechatermino=None,
                                      automatriculaadmision=True)
                matricula.save(request)
                # matricula.grupo_socio_economico()
                # matriculagruposocioeconomico = matricula.matriculagruposocioeconomico_set.all()[0]
                # matriculagruposocioeconomico.tipomatricula=tipo_matricula
                # matriculagruposocioeconomico.save()
                matricula.confirmar_matricula()
                codigoitinerario = 0
                if PerdidaGratuidad.objects.filter(inscripcion=inscripcion).exists():
                    inscripcion.estado_gratuidad = 3
                for materia in materias:
                    matriculacupoadicional = False
                    if not inscripcion.itinerario or inscripcion.itinerario < 1:
                        # if inscripcion.itinerario < 1:
                        if materia.asignaturamalla.itinerario > 0:
                            codigoitinerario = int(materia.asignaturamalla.itinerario)
                    if validartodo:
                        if not materia.tiene_cupo_materia():
                            if materia.cupoadicional > 0:
                                if not materia.existen_cupos_con_adicional():
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": "bad", "reload": True,"mensaje": u"Capacidad limite de la materia: " + unicode(materia.asignatura) + ", seleccione otro."})
                                else:
                                    matriculacupoadicional = True
                            else:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": "bad", "reload": True,"mensaje": u"Capacidad limite de la materia: " + unicode( materia.asignatura) + ", seleccione otro."})

                    matriculas = matricula.inscripcion.historicorecordacademico_set.values('id').filter(asignatura=materia.asignatura, fecha__lt=materia.nivel.fin).count() + 1
                    cobroperdidagratuidad = False
                    if matriculas > 1:
                        cobroperdidagratuidad = True
                        inscripcion.estado_gratuidad = 3
                    if inscripcion.carrera.modalidad == 3:
                        materiaasignada = MateriaAsignada(matricula=matricula,
                                                          materia=materia,
                                                          notafinal=0,
                                                          sinasistencia=True,
                                                          asistenciafinal=100,
                                                          cerrado=False,
                                                          matriculas=matriculas,
                                                          observaciones='',
                                                          estado_id=NOTA_ESTADO_EN_CURSO,
                                                          cobroperdidagratuidad=cobroperdidagratuidad)
                    else:
                        materiaasignada = MateriaAsignada(matricula=matricula,
                                                          materia=materia,
                                                          notafinal=0,
                                                          asistenciafinal=0,
                                                          cerrado=False,
                                                          matriculas=matriculas,
                                                          observaciones='',
                                                          estado_id=NOTA_ESTADO_EN_CURSO,
                                                          cobroperdidagratuidad=cobroperdidagratuidad)
                    materiaasignada.save(request)
                    if matriculacupoadicional:
                        materia.totalmatriculadocupoadicional += 1
                        materia.cupo += 1
                        materia.save(request)
                        log(u'Estudiante matriculado en cupo adicional materia: %s - estudiante: %s y se aumento un cupo en materia' % (materia, matricula), request, "add")
                    materiaasignada.asistencias()
                    materiaasignada.evaluacion()
                    materiaasignada.mis_planificaciones()
                    materiaasignada.save(request)
                    #MATRICULA EN LA PRACTICA QUE NO TENGAN GRUPO
                    if profesoresmateriassingrupo.values('id').filter(materia=materia).exists():
                        profemate = profesoresmateriassingrupo.filter(materia=materia)[0]
                        alumnopractica = AlumnosPracticaMateria(materiaasignada= materiaasignada,
                                                                profesormateria= profemate)
                        alumnopractica.save(request)
                        log(u'Materia (%s) con profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (materia, profemate, materiaasignada, alumnopractica.id), request, "add")
                    # MATRICULA EN LA PRACTICA QUE SI TENGAN GRUPOS
                    elif grupoprofesormateria.values('id').filter(profesormateria__materia=materia).exists():
                        profemate_congrupo = grupoprofesormateria.filter(profesormateria__materia=materia)[0]

                        if validartodo:
                            profemate_congrupo.verificar_capacidad_limite_grupoprofesor()

                        alumnopractica = AlumnosPracticaMateria(materiaasignada=materiaasignada,
                                                                profesormateria=profemate_congrupo.profesormateria,
                                                                grupoprofesor=profemate_congrupo)
                        alumnopractica.save(request)
                        log(u'Materia (%s) con grupo profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (materia, profemate_congrupo, materiaasignada, alumnopractica.id), request, "add")
                    log(u'Materia seleccionada matricula: %s' % materiaasignada, request, "add")
                matricula.actualizar_horas_creditos()
                if not inscripcion.itinerario or inscripcion.itinerario < 1:
                    inscripcion.itinerario = codigoitinerario
                inscripcion.save(request)
            with transaction.atomic():
                if inscripcion.estado_gratuidad == 3:
                    if inscripcion.sesion_id == 13:
                        tiporubromatricula = TipoOtroRubro.objects.get(pk=3019)
                    else:
                        tiporubromatricula = TipoOtroRubro.objects.get(pk=3011)

                    if matricula.tipomatricula_id == 1:
                        matricula.estado_matricula = 2
                        matricula.save(request)
                    num_materias = MateriaAsignada.objects.filter(matricula=matricula, cobroperdidagratuidad=True).count()
                    valor_x_materia = 20
                    valor_total = num_materias * valor_x_materia
                    if not Rubro.objects.filter(persona=inscripcion.persona, matricula=matricula).exists():
                        rubro1 = Rubro(tipo=tiporubromatricula,
                                       persona=inscripcion.persona,
                                       matricula=matricula,
                                       nombre=tiporubromatricula.nombre + ' - ' + periodo.nombre,
                                       cuota=1,
                                       fecha=datetime.now().date(),
                                       fechavence=datetime.now().date() + timedelta(days=25),
                                       valor=valor_total,
                                       iva_id=1,
                                       valoriva=0,
                                       valortotal=valor_total,
                                       saldo=valor_total,
                                       cancelado=False)
                        rubro1.save(request)


                matricula.actualiza_matricula()
                matricula.inscripcion.actualiza_estado_matricula()
                matricula.grupo_socio_economico(tipo_matricula_ri)
                matricula.calcula_nivel()

                send_html_mail("Matricula por secretaria", "emails/matricula.html", {'sistema': request.session['nombresistema'], 'matricula': matricula, 't': miinstitucion()}, inscripcion.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[5][1])
                log(u'Matricula secretaria: %s' % matricula, request, "add")
            valorpagar = str(null_to_decimal(matricula.rubro_set.filter(status=True).aggregate(valor=Sum('valortotal'))['valor']))

            descripcionarancel = ''
            valorarancel = ''
            if matricula.rubro_set.filter(status=True, tipo_id=RUBRO_ARANCEL).exists():
                ra = matricula.rubro_set.get(tipo_id=RUBRO_ARANCEL)
                descripcionarancel = ra.nombre
                valorarancel = str(ra.valortotal)

                matricula.aranceldiferido = 2
                matricula.save(request)

            ConfirmaCapacidadTecnologica.objects.filter(persona=matricula.inscripcion.persona).update(confirmado=True)

            request.session['periodo'] = matricula.nivel.periodo
            return JsonResponse({"result": "ok", "valorpagar":valorpagar, "descripcionarancel": descripcionarancel, "valorarancel": valorarancel, "phase": matricula.id})
        else:
            transaction.set_rollback(True)
            return JsonResponse({"result": "bad", "reload": True, "mensaje": u"Ya se encuentra matriculado."})
    except Exception as ex:
        transaction.set_rollback(True)
        import sys
        return JsonResponse({"result": "bad", "reload": False, "mensaje": u"Hubieron errores en la matriculacion %s - %s" % (ex, sys.exc_info()[-1].tb_lineno)})


def matricular_ingles_egresado(request, estudiante=False):
    try:
        inscripcion = Inscripcion.objects.get(pk=int(request.POST['id']))
        persona = inscripcion.persona
        mismaterias = json.loads(request.POST['materias'])
        mispracticas = []
        if inscripcion.mi_coordinacion().id != 9:
            mispracticas = json.loads(request.POST['practicas'])
        periodo_matricular = Periodo.objects.get(id=177)
        if request.POST['cobro']!='':
            cobro = request.POST['cobro']
        else:
            cobro=0
        # regular o irregular
        tipo_matricula_ri = request.POST['tipo_matricula']
        seleccion = []
        for m in mismaterias:
            seleccion.append(int(m))
        materias = Materia.objects.filter(id__in=seleccion, status=True)
        #MATERIAS PRACTICAS
        listaprofemateriaid_singrupo = []
        listaprofemateriaid_congrupo = []
        listagrupoprofesorid = []
        for x in mispracticas:
            if not int(x[1]) > 0:
                listaprofemateriaid_singrupo.append(int(x[0]))
            else:
                listaprofemateriaid_congrupo.append([int(x[0]), int(x[1])])
                listagrupoprofesorid.append(int(x[1]))
        profesoresmateriassingrupo = ProfesorMateria.objects.filter(id__in=listaprofemateriaid_singrupo)
        grupoprofesormateria = GruposProfesorMateria.objects.filter(id__in=listagrupoprofesorid)
        # VALIDACION MATERIAS TIENE PRACTICAS PARA LA CARRERA DE ENFERMERIA Y NUTRICION
        if inscripcion.carrera.id in [1, 3]:
            totalpracticas = materias.values('id').filter(asignaturamalla__practicas=True, id__in=profesoresmateriassingrupo.values('materia__id')).count() + materias.values('id').filter(asignaturamalla__practicas=True, id__in=grupoprofesormateria.values('profesormateria__materia__id')).count()
            if not materias.values('id').filter(asignaturamalla__practicas=True).count() == totalpracticas:
                return JsonResponse({"result": "bad", "mensaje": "Falta de seleccionar horario de practicas"})
        # CONFLICTO DE HORARIO PARA EL ESTUDIANTE
        materiasasistir = []
        for m in materias:
            if not inscripcion.sin_asistencia(m.asignatura):
                materiasasistir.append(m)
        # conflicto = ""
        # if materiasasistir:
        conflicto = conflicto_materias_estudiante(materiasasistir, profesoresmateriassingrupo, listaprofemateriaid_congrupo)
        if conflicto:
            return JsonResponse({"result": "bad", "mensaje": conflicto})
        # CAPACIDAD LIMITE DE CUPO
        for materia in materias:
            #VERIFICO SI ES MATERIA VIRTUAL Y SI VALIDA CUPO SEGUN LA VARIBALE
            validar = True
            if materia.tipomateria  == 2:
                # validar = variable_valor('VALIDAR_HORARIO_CUPO_MATERIA_VIRTUAL')
                validar = True
            if validar:
                if not HOMITIRCAPACIDADHORARIO and materia.capacidad_disponible() <= 0:
                    return JsonResponse({"result": "bad", "reload": True, "mensaje": u"Capacidad limite de la materia: " + unicode(materia.asignatura) + ", seleccione otro."})
        # VERIFICANDO CUPO MATERIAS PRACTICAS EN PROFESOR MATERIA CON PÁRALELO
        for grupoprofemat in grupoprofesormateria:
            # VERIFICO SI ES MATERIA VIRTUAL Y SI VALIDA CUPO SEGUN LA VARIBALE
            validar = True
            if grupoprofemat.profesormateria.materia.tipomateria == 2:
                validar = variable_valor('VALIDAR_HORARIO_CUPO_MATERIA_VIRTUAL')
            if validar:
                if not HOMITIRCAPACIDADHORARIO and grupoprofemat.cuposdisponiblesgrupoprofesor()<=0:
                    return JsonResponse({"result": "bad", "reload": True, "mensaje": u"Capacidad limite de la materia en la practica:  " + unicode(grupoprofemat.profesormateria.materia) + ", seleccione otro."})
        hoy = datetime.now().date()
        nivel = Nivel.objects.get(pk=1501)
        # LIMITE DE MATRICULAS EN EL PARALELO
        if not MATRICULACION_LIBRE and nivel.capacidadmatricula <= nivel.matricula_set.count():
            return JsonResponse({"result": "bad", "reload": True, "mensaje": u"Capacidad matricula limite del paralelo: " + unicode(nivel.paralelo) + ", seleccione otro."})
        # habilitar cuando sea matriculacion
        # if estudiante and 'matriculamodulos' not in request.POST:
        #     if nivel.fechatopematriculaex and hoy > nivel.fechatopematriculaex:
        #         return JsonResponse({"result": "bad", "reload": False, "mensaje": u"Fuera del periodo de matriculacion."})
        # habilitar cuando sea matriculacion
        # PERDIDA DE CARRERA POR 4TA MATRICULA
        # if inscripcion.tiene_perdida_carrera():
        #     return JsonResponse({"result": "bad", "mensaje": u"Tiene limite de matriculas."})
        # MATRICULA
        costo_materia_total = 0
        if not inscripcion.matriculado_periodo(periodo_matricular):
            matricula = Matricula(inscripcion=inscripcion,
                                  nivel=nivel,
                                  pago=False,
                                  iece=False,
                                  becado=False,
                                  porcientobeca=0,
                                  fecha=datetime.now().date(),
                                  hora=datetime.now().time(),
                                  fechatope=fechatope(datetime.now().date()))
            matricula.save(request)
            # matricula.grupo_socio_economico()
            # matriculagruposocioeconomico = matricula.matriculagruposocioeconomico_set.all()[0]
            # matriculagruposocioeconomico.tipomatricula=tipo_matricula
            # matriculagruposocioeconomico.save()
            # matricula.confirmar_matricula()

            # matricula.actualizar_horas_creditos()
            matricula.tipomatricula.id=1
            matricula.save(request)
            # if int(cobro) > 0:
            #     if matricula.inscripcion.mi_coordinacion().id != 9:
            #         # matricula.calcular_rubros_matricula(request,int(cobro))
            #         matricula.agregacion_aux(request)
            matricula.actualiza_matricula()
            matricula.inscripcion.actualiza_estado_matricula()
            matricula.grupo_socio_economico(tipo_matricula_ri)
            matricula.calcula_nivel()

            #
            for materia in materias:
                matriculas = matricula.inscripcion.historicorecordacademico_set.filter(asignatura=materia.asignatura,
                                                                                       fecha__lt=materia.nivel.fin).count() + 1
                materiaasignada = MateriaAsignada(matricula=matricula,
                                                  materia=materia,
                                                  notafinal=0,
                                                  asistenciafinal=100,
                                                  cerrado=False,
                                                  matriculas=matriculas,
                                                  observaciones='',
                                                  estado_id=NOTA_ESTADO_EN_CURSO
                                                  )
                materiaasignada.save(request)
                materiaasignada.asistencias()
                materiaasignada.evaluacion()
                materiaasignada.mis_planificaciones()
                materiaasignada.save(request)
                if matriculas > 1 or matricula.inscripcion.persona.tiene_otro_titulo(matricula.inscripcion):
                    matricula.nuevo_calculo_matricula_ingles(materiaasignada)
                log(u'Materia seleccionada matricula: %s' % materiaasignada, request, "add")
        else:
            matricula=inscripcion.matricula_periodo(periodo_matricular)
            for materia in materias:
                matriculas = matricula.inscripcion.historicorecordacademico_set.filter(asignatura=materia.asignatura, fecha__lt=materia.nivel.fin).count() + 1
                materiaasignada = MateriaAsignada(matricula=matricula,
                                                  materia=materia,
                                                  notafinal=0,
                                                  asistenciafinal=100,
                                                  cerrado=False,
                                                  matriculas=matriculas,
                                                  observaciones='',
                                                  estado_id=NOTA_ESTADO_EN_CURSO
                                                  )
                materiaasignada.save(request)
                materiaasignada.asistencias()
                materiaasignada.evaluacion()
                materiaasignada.mis_planificaciones()
                materiaasignada.save(request)
                if matriculas > 1 or matricula.inscripcion.persona.tiene_otro_titulo(matricula.inscripcion):
                    matricula.nuevo_calculo_matricula_ingles(materiaasignada)
                # #MATRICULA EN LA PRACTICA QUE NO TENGAN GRUPO
                # if profesoresmateriassingrupo.filter(materia=materia).exists():
                #     profemate = profesoresmateriassingrupo.filter(materia=materia)[0]
                #     alumnopractica = AlumnosPracticaMateria(materiaasignada= materiaasignada,
                #                                             profesormateria= profemate)
                #     alumnopractica.save(request)
                #     log(u'Materia (%s) con profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (materia, profemate, materiaasignada, alumnopractica.id), request, "add")
                # # MATRICULA EN LA PRACTICA QUE SI TENGAN GRUPOS
                # elif grupoprofesormateria.filter(profesormateria__materia=materia).exists():
                #     profemate_congrupo = grupoprofesormateria.filter(profesormateria__materia=materia)[0]
                #     alumnopractica = AlumnosPracticaMateria(materiaasignada=materiaasignada,
                #                                             profesormateria=profemate_congrupo.profesormateria,
                #                                             grupoprofesor=profemate_congrupo)
                #     alumnopractica.save(request)
                #     log(u'Materia (%s) con grupo profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (materia, profemate_congrupo, materiaasignada, alumnopractica.id), request, "add")
                log(u'Materia seleccionada matricula: %s' % materiaasignada, request, "add")
        if estudiante:
            # send_html_mail("Automatricula", "emails/matricula.html", {'sistema': request.session['nombresistema'], 'matricula': matricula, 't': miinstitucion()}, inscripcion.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[5][1])
            log(u'Automatricula estudiante: %s' % matricula, request, "add")
        else:
            # send_html_mail("Matricula por secretaria", "emails/matricula.html", {'sistema': request.session['nombresistema'], 'matricula': matricula, 't': miinstitucion()}, inscripcion.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[5][1])
            log(u'Matricula secretaria: %s' % matricula, request, "add")
        valorpagar =  str(null_to_decimal(Rubro.objects.filter(status=True, persona=persona, cancelado=False,observacion="INGLÉS %s" % periodo_matricular.nombre).aggregate(valor=Sum('valortotal'))['valor']))
        return JsonResponse({"result": "ok", "valorpagar":valorpagar})
        # else:
        #     transaction.set_rollback(True)
        #     return JsonResponse({"result": "bad", "reload": True, "mensaje": u"Ya se encuentra matriculado."})
    except Exception as ex:
        transaction.set_rollback(True)
        return JsonResponse({"result": "bad", "reload": False, "mensaje": u"Hubieron errores en la matriculacion"})


def prematricular(request, valormatriculapago):
    with transaction.atomic():
        try:
            horascontactodocente = 0
            horastotalesmateria = 0
            inscripcion = Inscripcion.objects.get(pk=int(request.POST['id']))
            inscripcionmalla = inscripcion.malla_inscripcion()
            malla= inscripcionmalla.malla
            periodo = Periodo.objects.get(pk=request.POST['pid'])
            if inscripcion.tiene_perdida_carrera():
                return JsonResponse({"result": "bad", "mensaje": u"Tiene limite de matriculas (4ta matricula)."})
            # MATRICULA
            if not inscripcion.prematricula_set.filter(periodo=periodo).exists():
                mismaterias = json.loads(request.POST['materias'])
                prematricula = PreMatricula(inscripcion=inscripcion,
                                            periodo=periodo,
                                            fecha=datetime.now().date(),
                                            hora=datetime.now().time(),
                                            aceptaterminos=True,
                                            sesion_id=int(encrypt_alu(request.POST['turno'])),
                                            valorpagoaprox=valormatriculapago)
                prematricula.save(request)
                horasdocentes = 20
                horastotal = 45
                if inscripcion.carrera.coordinacion_set.values_list('id', flat=True)[0] == 1:  # Configuracion de horas si es facultad de salud
                    horasdocentes = 40
                    horastotal = 60
                if inscripcion.carrera.modalidad == 3 and not inscripcion.carrera.id == 133:  # Configuracion de horas si es modalidad en linea exepto carrera de ingenieria en tics
                    horastotal = 55
                for m in mismaterias:
                    asignatura = Materia.objects.get(pk=encrypt_alu(m['idmat']))
                    horascontactodocente += asignatura.asignaturamalla.horasacdsemanal
                    horastotalesmateria += asignatura.asignaturamalla.horastotal()
                    if horascontactodocente <= horasdocentes and horastotalesmateria <= horastotal:
                        # countcoupo = len(PreMatriculaAsignatura.objects.filter(asignatura=asignatura.asignatura, prematricula__inscripcion__carrera=inscripcion.carrera, sesion_id=int(m['turno'])).values('id'))
                        # if asignatura.cupo >= countcoupo:
                            prematriculaasignatura = PreMatriculaAsignatura(asignatura=asignatura.asignatura, modalidad=int(m['modalidad']))
                            # if inscripcion.sesion_id == 7:
                            #     # asignatura = Asignatura.objects.get(pk=m['id'])
                            #
                            #     prematriculaasignatura = PreMatriculaAsignatura(asignatura=asignatura.asignatura, tipo=m['tipo'])
                            # else:
                                # asignatura = Asignatura.objects.get(pk=m['id'])

                            if int(m['turno']) > 0:
                                prematriculaasignatura.sesion_id = m['turno']
                            else:
                                prematriculaasignatura.sesion = prematricula.sesion
                            prematriculaasignatura.save(request)
                            prematricula.prematriculaasignatura.add(prematriculaasignatura)
                            prematricula.asignaturas.add(asignatura.asignatura)
                        # else:
                        #     raise NameError('Lo sentimos la materia {} que intentas planificar ya no cuenta con cupo disponible'.format(asignatura.asignatura.nombre))
                            # return JsonResponse({"result": "bad", "reload": False, "mensaje": 'Lo sentimos la materia {} que te intenas matricular ya no cuenta con cupo disponible'.format(asignatura.asignatura.nombre)})
                    else:
                        # transaction.set_rollback(True)
                        raise NameError('Solo puede elegir materias que sumen hasta %s horas de contacto docente o %s horas totales a la semana'%(horasdocentes,horastotal))
                        # return JsonResponse({"result": "bad", "reload": False, "mensaje": 'Lo sentimos la materia {} que te intenas matricular ya no cuenta con cupo disponible'.format(asignatura.asignatura.nombre)})

                send_html_mail("Planificación de matrícula", "emails/prematricula.html", {'sistema': request.session['nombresistema'], 'prematricula': prematricula, 'malla': malla, 't': miinstitucion()}, inscripcion.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[5][1])
                # send_html_mail("Confirmacion de Simalacion de prematricula", "emails/prematricula.html", {'sistema': request.session['nombresistema'], 'prematricula': prematricula, 't': miinstitucion()}, 'chrisstianandres@gmail.com', [], cuenta=CUENTAS_CORREOS[5][1])
                log(u'Prematricula de asignaturas: %s' % prematricula, request, "add")
                return JsonResponse({"result": "ok", 'valormatriculapago': str(valormatriculapago)})
            else:
                # transaction.set_rollback(True)
                raise NameError(u"Ya se encuentra prematriculado.")
                # return JsonResponse({"result": "bad", "reload": True, "mensaje": u"Ya se encuentra prematriculado."})
        except Exception as ex:
            import sys
            transaction.set_rollback(True)
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            return JsonResponse({"result": "bad", "reload": False, "mensaje": u"%s" % ex})


def prematricularmodulo(request, tipo1):
    try:
        inscripcion = Inscripcion.objects.get(pk=int(request.POST['id']))
        mismaterias = request.POST['materias']
        periodo = Periodo.objects.get(pk=request.POST['pid'])
        seleccion = []
        for m in mismaterias.replace('[', '').replace('"', '').replace(']', '').split(','):
            seleccion.append(int(m))
        materias = Asignatura.objects.filter(id__in=seleccion)
        # PERDIDA DE CARRERA POR 4TA MATRICULA
        if inscripcion.tiene_perdida_carrera():
            return JsonResponse({"result": "bad", "mensaje": u"Tiene limite de matriculas (4ta matricula)."})
        # MATRICULA
        if not inscripcion.prematriculamodulo_set.filter(periodo=periodo, tipo=tipo1).exists():
            for mate in materias:
                prematricula = PreMatriculaModulo(inscripcion=inscripcion,
                                                  periodo=periodo,
                                                  fecha=datetime.now().date(),
                                                  hora=datetime.now().time(),
                                                  asignaturas=mate,
                                                  tipo=tipo1)
                prematricula.save()
            # prematricula.asignaturas = materias
            # send_html_mail("Prematricula Modulo", "emails/prematriculamodulo.html", {'sistema': request.session['nombresistema'], 'prematricula': prematricula, 't': miinstitucion()}, inscripcion.persona.lista_emails_envio(), [])
            # log(u'Prematricula Modulo la asignatura: %s' % prematricula, request, "add")
            return JsonResponse({"result": "ok"})
        else:
            transaction.set_rollback(True)
            return JsonResponse({"result": "bad", "reload": True, "mensaje": u"Ya se encuentra prematriculado en los Modulos."})
    except Exception as ex:
        transaction.set_rollback(True)
        return JsonResponse({"result": "bad", "reload": False, "mensaje": u"Hubieron errores en la prematriculacion de los Modulos"})


def prematricularmoduloespecial(request, tipo1):
    try:
        inscripcion = Inscripcion.objects.get(pk=int(request.POST['id']))
        mismaterias = request.POST['materias']
        periodo = Periodo.objects.get(pk=request.POST['pid'])
        seleccion = []
        for m in mismaterias.replace('[', '').replace('"', '').replace(']', '').split(','):
            seleccion.append(int(m))
        materias = Asignatura.objects.filter(id__in=seleccion)
        # PERDIDA DE CARRERA POR 4TA MATRICULA
        if inscripcion.tiene_perdida_carrera():
            return JsonResponse({"result": "bad", "mensaje": u"Tiene limite de matriculas (4ta matricula)."})
        # MATRICULA
        if not inscripcion.prematriculamodulo_set.filter(periodo=periodo, tipo=tipo1, asignaturas__id__in=[1818, 1819]).exists():
            for mate in materias:
                prematricula = PreMatriculaModulo(inscripcion=inscripcion,
                                                  periodo=periodo,
                                                  fecha=datetime.now().date(),
                                                  hora=datetime.now().time(),
                                                  asignaturas=mate,
                                                  tipo=tipo1)
                prematricula.save()
                # aqui tienen algo mal en el contenido del correo
                # send_html_mail("Prematricula Modulo", "emails/prematriculamodulo.html", {'sistema': request.session['nombresistema'], 'prematricula': prematricula, 't': miinstitucion()}, inscripcion.persona.lista_emails_envio(), [])
                log(u'Prematricula Modulo la asignatura: %s' % prematricula, request, "add")
            return JsonResponse({"result": "ok"})
        else:
            transaction.set_rollback(True)
            return JsonResponse({"result": "bad", "reload": True, "mensaje": u"Ya se encuentra prematriculado en los Modulos."})
    except Exception as ex:
        transaction.set_rollback(True)
        return JsonResponse({"result": "bad", "reload": False, "mensaje": u"Hubieron errores en la prematriculacion de los Modulos"})


def total_prematriculados(periodo):
    return PreMatricula.objects.filter(status=True, periodo=periodo).count()


# FUNCIONES COMUNES
def actualizar_nota(request, materiaasignada=None, sel=None, valor=None):
    perfil = request.session['perfilprincipal']
    if perfil.es_estudiante():
        datos = {"result": "bad"}
    else:
        persona = perfil.persona
        if not materiaasignada:
            materiaasignada = MateriaAsignada.objects.get(pk=request.POST['maid'])
        if not sel:
            sel = request.POST['sel']
        datos = {"result": "ok"}
        modeloevaluativo = materiaasignada.materia.modeloevaluativo
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
        campo = materiaasignada.campo(sel)
        campo.valor = valor
        campo.save(request)
        d = locals()
        exec(modeloevaluativo.logicamodelo, globals(), d)
        d['calculo_modelo_evaluativo'](materiaasignada)

        # FUNCION DIMAMICA
        materiaasignada.notafinal = null_to_decimal(materiaasignada.notafinal, modeloevaluativo.notafinaldecimales)
        if materiaasignada.notafinal > modeloevaluativo.notamaxima:
            materiaasignada.notafinal = modeloevaluativo.notamaxima
        materiaasignada.save(request, update_fields=['notafinal'])
        camposdependientes = []
        encurso = True
        for campomodelo in modeloevaluativo.campos():
            if campomodelo.dependiente:
                camposdependientes.append((campomodelo.htmlid(), materiaasignada.valor_nombre_campo(campomodelo.nombre), campomodelo.decimales))
            if campomodelo.actualizaestado and materiaasignada.valor_nombre_campo(campomodelo.nombre) > 0:
                encurso = False
        if not encurso:
            materiaasignada.actualiza_estado()
        else:
            materiaasignada.estado_id = NOTA_ESTADO_EN_CURSO
            materiaasignada.save(request, update_fields=['estado_id'])
        datos['dependientes'] = camposdependientes
        campo = materiaasignada.campo(sel)
        datos['valor'] = campo.valor
        auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=True, calificacion=campo.valor)
        auditorianotas.save(request)
        # log(u'Ingreso de notas: %s - %s- %s - %s' % (materiaasignada.matricula.inscripcion.persona, materiaasignada.materia.asignatura, sel, str(campo.valor)), request, "add")
        datos['nota_final'] = materiaasignada.notafinal
        datos['valida_asistencia'] = materiaasignada.materia.nivel.periodo.valida_asistencia
        datos['estado'] = materiaasignada.estado.nombre
        datos['estadoid'] = materiaasignada.estado.id
        if materiaasignada.materia.cerrado:
            materiaasignada.cierre_materia_asignada()
    return datos


def actualizar_nota_docente(request, materiaasignada=None, sel=None, valor=None):
    perfil = request.session['perfilprincipal']
    if perfil.es_estudiante():
        datos = {"result": "bad"}
    else:
        persona = perfil.persona
        if not materiaasignada:
            materiaasignada = MateriaAsignada.objects.get(pk=request.POST['maid'])
        if materiaasignada.materia.cerrado:
            datos = {"result": "bad"}
        else:
            if not sel:
                sel = request.POST['sel']
            datos = {"result": "ok"}
            modeloevaluativo = materiaasignada.materia.modeloevaluativo
            cronograma = materiaasignada.materia.cronogramacalificaciones()
            if not modeloevaluativo.campo(sel).permite_ingreso_nota(materiaasignada, cronograma):
                datos = {"result": "bad"}
            else:
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
                campo = materiaasignada.campo(sel)
                campo.valor = valor
                campo.save()
                d = locals()
                exec(modeloevaluativo.logicamodelo, globals(), d)
                d['calculo_modelo_evaluativo'](materiaasignada)
                materiaasignada.notafinal = null_to_decimal(materiaasignada.notafinal, modeloevaluativo.notafinaldecimales)
                if materiaasignada.notafinal > modeloevaluativo.notamaxima:
                    materiaasignada.notafinal = modeloevaluativo.notamaxima
                materiaasignada.save()
                camposdependientes = []
                encurso = True
                for campomodelo in modeloevaluativo.campos():
                    if campomodelo.dependiente:
                        camposdependientes.append((campomodelo.htmlid(), materiaasignada.valor_nombre_campo(campomodelo.nombre), campomodelo.decimales))
                    if campomodelo.actualizaestado and materiaasignada.valor_nombre_campo(campomodelo.nombre) > 0:
                        encurso = False
                if not encurso:
                    materiaasignada.actualiza_estado()
                else:
                    materiaasignada.estado_id = NOTA_ESTADO_EN_CURSO
                    materiaasignada.save()
                datos['dependientes'] = camposdependientes
                campo = materiaasignada.campo(sel)
                datos['valor'] = campo.valor
                auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=True, calificacion=campo.valor)
                auditorianotas.save(request)
                # log(u'Ingreso de nota Grupo Docente: %s - %s- %s - %s' % (materiaasignada.matricula.inscripcion.persona, materiaasignada.materia.asignatura, sel, str(campo.valor)), request, "add")
                datos['nota_final'] = materiaasignada.notafinal
                datos['valida_asistencia'] = materiaasignada.materia.nivel.periodo.valida_asistencia
                datos['estado'] = materiaasignada.estado.nombre
                datos['estadoid'] = materiaasignada.estado.id
    return datos


def actualizar_nota_planificacion(materiaasignada_id, sel_id, valor):
    materiaasignada = MateriaAsignada.objects.get(pk=materiaasignada_id)
    if materiaasignada.materia.cerrado:
        datos = {"result": "bad"}
    else:
        sel = sel_id
        datos = {"result": "ok"}
        modeloevaluativo = materiaasignada.materia.modeloevaluativo
        campomodelo = modeloevaluativo.campo(sel)
        try:
            if not valor:
                valor = null_to_decimal(float(valor), campomodelo.decimales)
            if valor >= campomodelo.notamaxima:
                valor = campomodelo.notamaxima
            elif valor <= campomodelo.notaminima:
                valor = campomodelo.notaminima
        except:
            valor = campomodelo.notaminima
        campo = materiaasignada.campo(sel)
        campo.valor = valor
        campo.save()
        # FUNCION DIMAMICA
        d = locals()
        exec(modeloevaluativo.logicamodelo, globals(), d)
        d['calculo_modelo_evaluativo'](materiaasignada)
        # calculo_modelo_evaluativo(materiaasignada)
        materiaasignada.notafinal = null_to_decimal(materiaasignada.notafinal, modeloevaluativo.notafinaldecimales)
        if materiaasignada.notafinal > modeloevaluativo.notamaxima:
            materiaasignada.notafinal = modeloevaluativo.notamaxima
        materiaasignada.save()
        camposdependientes = []
        encurso = True
        for campomodelo in modeloevaluativo.campos():
            if campomodelo.dependiente:
                camposdependientes.append((campomodelo.htmlid(), materiaasignada.valor_nombre_campo(campomodelo.nombre), campomodelo.decimales))
            if campomodelo.actualizaestado and materiaasignada.valor_nombre_campo(campomodelo.nombre) > 0:
                encurso = False
        if not encurso:
            materiaasignada.actualiza_estado()
        else:
            materiaasignada.estado_id = NOTA_ESTADO_EN_CURSO
            materiaasignada.save()


def actualizar_nota_grupo(request, materiaasignada_id, sel_id, valor):
    materiaasignada = IntegranteGrupoExamenMsc.objects.get(pk=materiaasignada_id)
    sel = sel_id
    datos = {"result": "ok"}
    modeloevaluativo = materiaasignada.grupoexamen.cohorte
    materiaasignada.notaexa = float(valor)
    materiaasignada.notatest = float(valor)
    materiaasignada.notafinal = float(valor)
    # materiaasignada.save()
    # if materiaasignada.notafinal > modeloevaluativo.notamaximaexa:
    #     materiaasignada.notafinal = modeloevaluativo.notamaximaexa
    # materiaasignada.save()
    if materiaasignada.notafinal >= modeloevaluativo.notaminimaexa:
        materiaasignada.estado = 2
    if materiaasignada.notafinal < modeloevaluativo.notaminimaexa:
        materiaasignada.estado = 3

    materiaasignada.save(request)
    log(u'Actualizo nota grupo, integrante: %s' % (materiaasignada), request, "add")

def copiar_nota_entrevista(materiaasignada_id, valexamen, valfinal, estadoexa):
    materiaasignada = IntegranteGrupoEntrevitaMsc.objects.get(pk=materiaasignada_id, status=True)
    materiaasignada.notaentrevista = valexamen
    materiaasignada.notafinal = round(((valexamen + valfinal)/2), 2)
    materiaasignada.estado = estadoexa
    materiaasignada.save()

def actualizar_nota_instructor(inscrito_id, sel_id, valor,instructor_id,request):
    inscrito = CapInscritoIpec.objects.get(pk=inscrito_id)
    instructor = CapInstructorIpec.objects.get(pk=instructor_id)
    sel = sel_id
    datos = {"result": "ok"}
    notaaterior=''
    modeloevaluativo = instructor.modelo_calificacion(instructor.capeventoperiodo).filter(modelo__nombre=sel_id)
    if modeloevaluativo:
        if CapDetalleNotaIpec.objects.filter(cabeceranota_id=modeloevaluativo[0], inscrito=inscrito,
                                             cabeceranota__instructor__capeventoperiodo=instructor.capeventoperiodo).exists():
            detalle = CapDetalleNotaIpec.objects.get(cabeceranota_id=modeloevaluativo[0],
                                                     inscrito=inscrito,
                                                     cabeceranota__instructor__capeventoperiodo=instructor.capeventoperiodo)
            notaanterior = detalle.nota
            detalle.nota = float(valor)
        else:
            detalle = CapDetalleNotaIpec(cabeceranota_id=modeloevaluativo, inscrito=inscrito,
                                         nota=float(valor))
        detalle.save()
        log(u'Actualizo nota en tarea de capacitacion IPEC: %s nota anterior: %s nota actualizada: %s del modelo de evaluativo %s' % (
        detalle, str(notaanterior), str(detalle.nota), detalle.cabeceranota.modelo), request, "edit")
        inscrito.nofinal = detalle.inscrito.nota_total_evento_porinstructor(instructor.capeventoperiodo.id, instructor.pk)


def actualizar_nota_proceso( materiaasignada=None, sel=None, valor=None):
    datos = {"result": "ok"}
    modeloevaluativo = materiaasignada.materia.modeloevaluativo
    campomodelo = modeloevaluativo.campo(sel)
    try:
        if valor >= campomodelo.notamaxima:
            valor = campomodelo.notamaxima
        elif valor <= campomodelo.notaminima:
            valor = campomodelo.notaminima
    except:
        valor = campomodelo.notaminima
    campo = materiaasignada.campo(sel)
    campo.valor = valor
    campo.save()
    d = locals()
    exec(modeloevaluativo.logicamodelo, globals(), d)
    d['calculo_modelo_evaluativo'](materiaasignada)

    # FUNCION DIMAMICA
    materiaasignada.notafinal = null_to_decimal(materiaasignada.notafinal, modeloevaluativo.notafinaldecimales)
    if materiaasignada.notafinal > modeloevaluativo.notamaxima:
        materiaasignada.notafinal = modeloevaluativo.notamaxima
    materiaasignada.save()
    camposdependientes = []
    encurso = True
    for campomodelo in modeloevaluativo.campos():
        if campomodelo.dependiente:
            camposdependientes.append((campomodelo.htmlid(), materiaasignada.valor_nombre_campo(campomodelo.nombre), campomodelo.decimales))
        if campomodelo.actualizaestado and materiaasignada.valor_nombre_campo(campomodelo.nombre) > 0:
            encurso = False
    if not encurso:
        materiaasignada.actualiza_estado()
    else:
        materiaasignada.estado_id = NOTA_ESTADO_EN_CURSO
        materiaasignada.save()
    datos['dependientes'] = camposdependientes
    campo = materiaasignada.campo(sel)
    datos['valor'] = campo.valor
    auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=True, calificacion=campo.valor)
    auditorianotas.save()
    # log(u'Ingreso de notas: %s - %s- %s - %s' % (materiaasignada.matricula.inscripcion.persona, materiaasignada.materia.asignatura, sel, str(campo.valor)), request, "add")
    datos['nota_final'] = materiaasignada.notafinal
    datos['valida_asistencia'] = materiaasignada.materia.nivel.periodo.valida_asistencia
    datos['estado'] = materiaasignada.estado.nombre
    datos['estadoid'] = materiaasignada.estado.id
    if materiaasignada.materia.cerrado:
        materiaasignada.cierre_materia_asignada()


def justificar_asistencia(request, asistencialeccion=None):
    datos = {"result": "ok"}
    if not asistencialeccion:
        asistencialeccion = AsistenciaLeccion.objects.get(pk=request.POST['id'])
    if not JustificacionAusenciaAsistenciaLeccion.objects.filter(asistencialeccion=asistencialeccion).exists():
        asistencialeccion.asistio = True
        asistencialeccion.save(request)
        justificacionausenciaasistencialeccion = JustificacionAusenciaAsistenciaLeccion(asistencialeccion=asistencialeccion,
                                                                                        porcientojustificado=PORCIENTO_RECUPERACION_FALTAS,
                                                                                        motivo=request.POST['motivo'],
                                                                                        fecha=datetime.now().date(),
                                                                                        persona=request.session['persona'])
        justificacionausenciaasistencialeccion.save(request)
    materiaasignada = asistencialeccion.materiaasignada
    materiaasignada.save(actualiza=True)
    materiaasignada.actualiza_estado()
    datos['id'] = asistencialeccion.id
    datos['materiaasignada'] = materiaasignada
    datos['total_general'] = materiaasignada.real_dias_asistencia()
    datos['total_presentes'] = materiaasignada.asistencia_real()
    datos['total_faltas'] = materiaasignada.real_dias_asistencia() - materiaasignada.asistencia_real()
    datos['porcientoasist'] = materiaasignada.asistenciafinal
    datos['porcientorequerido'] = materiaasignada.porciento_requerido()
    datos['mensaje'] = 'Asistencia justificada correctamente'
    datos['esta_justificada'] = asistencialeccion.esta_justificada()
    log(u'Justifico asistencia: %s - %s - %s, motivo: %s' % (materiaasignada.materia.asignatura.nombre, asistencialeccion.materiaasignada.matricula.inscripcion.persona.nombre_completo(), asistencialeccion.leccion.fecha.strftime("%Y-%m-%d"), request.POST['motivo']), request, "edit")
    return datos


def actualizar_asistencia(request, apertura_toma_asistencia=False):
    datos = {"result": "ok"}
    asistio = request.POST['val'] == 'y'
    asistencialeccion = AsistenciaLeccion.objects.get(pk=request.POST['id'])
    asistencialeccion.asistio = asistio
    asistencialeccion.save(request, update_fields=['asistio'])
    if asistencialeccion.mi_registro_practica_asistencia():
        asistenciapractica = asistencialeccion.mi_registro_practica_asistencia()
        asistenciapractica.asistencia = asistencialeccion.asistio
        asistenciapractica.save(request, update_fields=['asistencia'])
        practica = asistenciapractica.practica
        practica.cerrado = not asistencialeccion.leccion.abierta
        practica.save(request, update_fields=['cerrado'])
    materiaasignada = asistencialeccion.materiaasignada
    if not asistencialeccion.leccion.abierta:
        calcula_procentaje_apertura = True
    materiaasignada.save(actualiza=apertura_toma_asistencia)
    # materiaasignada.actualiza_estado()
    estado = 'falta'
    if asistencialeccion.asistio:
        estado = 'presente'
    datos['materiaasignada'] = materiaasignada
    datos['porcientoasist'] = materiaasignada.asistenciafinal
    datos['porcientorequerido'] = materiaasignada.porciento_requerido()
    log(u'Asistencia en clase: %s - %s - %s, estado: %s' % (materiaasignada.materia.asignatura.nombre, asistencialeccion.materiaasignada.matricula.inscripcion.persona.nombre_completo_inverso(), asistencialeccion.leccion.fecha.strftime("%Y-%m-%d"), estado), request, "edit")
    # log(u'Asistencia en clase: %s - %s - %s' % (materiaasignada.materia.asignatura.nombre, asistencialeccion.materiaasignada.matricula.inscripcion.persona.nombre_completo(), asistencialeccion.leccion.fecha.strftime("%Y-%m-%d")), request, "edit")
    return datos


def actualizar_contenido(request):
    perfil = request.session['perfilprincipal']
    if perfil.es_estudiante():
        datos = {"result": "bad"}
    else:
        datos = {"result": "ok"}
        leccion = Leccion.objects.get(pk=int(request.POST['id']))
        leccion.contenido = request.POST['val']
        leccion.save(request)
        if not leccion.aperturaleccion:
            lecciongrupo = leccion.leccion_grupo()
            lecciongrupo.contenido = request.POST['val']
            lecciongrupo.save(request)
        log(u'Modifico contenido de leccion: %s' % leccion, request, "edit")
    return datos


def actualizar_estrategiasmetodologicas(request):
    perfil = request.session['perfilprincipal']
    if perfil.es_estudiante():
        datos = {"result": "bad"}
    else:
        datos = {"result": "ok"}
        leccion = Leccion.objects.get(pk=int(request.POST['id']))
        leccion.estrategiasmetodologicas = request.POST['val']
        leccion.save()
        if not leccion.aperturaleccion:
            lecciongrupo = leccion.leccion_grupo()
            lecciongrupo.estrategiasmetodologicas = request.POST['val']
            lecciongrupo.save()
        log(u'Modifico estrategia metedologica de leccion: %s' % leccion, request, "edit")
    return datos


def obtener_reporte(nombre):
    return Reporte.objects.filter(nombre=nombre)[0] if Reporte.objects.db_manager("sga_select").filter(nombre=nombre).exists() else None


def ficha_socioeconomica(persona):
    if not persona.fichasocioeconomicainec_set.exists():
        fichasocioecon = FichaSocioeconomicaINEC(persona=persona)
        fichasocioecon.save()
    else:
        fichasocioecon = persona.fichasocioeconomicainec_set.all()[0]
    return fichasocioecon


def nivel_matriculacion(inscripcion):
    nivel = None
    if not MATRICULACION_LIBRE:
        # MATERIAS POR NIVEL
        if MATRICULACION_POR_NIVEL:
            minivelmalla = inscripcion.mi_nivel().nivel
            # MATRICULACION SEGUN NIVEL MALLA O GRUPO
            if Nivel.objects.filter(nivelgrado=False, nivelmalla__gte=minivelmalla, modalidad=inscripcion.modalidad, sesion=inscripcion.sesion, sede=inscripcion.sede, carrera=inscripcion.carrera, cerrado=False, fin__gt=datetime.now().date()).exists():
                for nivelseleccion in Nivel.objects.filter(nivelgrado=False, nivelmalla__gte=minivelmalla, modalidad=inscripcion.modalidad, sesion=inscripcion.sesion, sede=inscripcion.sede, carrera=inscripcion.carrera, cerrado=False, fin__gt=datetime.now().date()).order_by('nivelmalla', 'id'):
                    if nivelseleccion.capacidadmatricula > nivelseleccion.matricula_set.count() and nivelseleccion.pagonivel_set.exists():
                        nivel = nivelseleccion
                        break
                if not nivel:
                    return -3
            else:
                return -4
        else:
            grupo = inscripcion.grupo()
            for nivelseleccion in Nivel.objects.annotate(matriculados=Count('matricula')).filter(capacidadmatricula__gt=F("matriculados")).filter(grupo=grupo, nivelgrado=False, cerrado=False, fin__gt=datetime.now().date()).order_by('id'):
                if nivelseleccion.capacidadmatricula > nivelseleccion.matricula_set.count() and nivelseleccion.pagonivel_set.exists():
                    nivel = nivelseleccion
                    break
            if not nivel:
                return -2
    else:
        # MATERIAS X LIBRES X COORDINACIONES
        # HABILITAR PARA EL PROXIMO PERIODO
        if Nivel.objects.filter(periodo__matriculacionactiva=True, nivellibrecoordinacion__coordinacion__carrera=inscripcion.carrera, nivellibrecoordinacion__coordinacion__sede=inscripcion.sede, sesion=inscripcion.sesion, cerrado=False, fin__gte=datetime.now().date(), periodo__tipo__id=TIPO_PERIODO_REGULAR).exists():
            nivel = Nivel.objects.filter(periodo__matriculacionactiva=True,nivellibrecoordinacion__coordinacion__carrera=inscripcion.carrera, nivellibrecoordinacion__coordinacion__sede=inscripcion.sede, sesion=inscripcion.sesion, cerrado=False, fin__gte=datetime.now().date(), periodo__tipo__id=TIPO_PERIODO_REGULAR).order_by('-fin')[0]
        else:
            return -1

        # quite la modalidad
        # if Nivel.objects.filter(periodo__matriculacionactiva=True, nivellibrecoordinacion__coordinacion__carrera=inscripcion.carrera, nivellibrecoordinacion__coordinacion__sede=inscripcion.sede, sesion=inscripcion.sesion, modalidad=inscripcion.modalidad, cerrado=False, fin__gte=datetime.now().date(), periodo__tipo__id=TIPO_PERIODO_REGULAR).exists():
        #     nivel = Nivel.objects.filter(periodo__matriculacionactiva=True,nivellibrecoordinacion__coordinacion__carrera=inscripcion.carrera, nivellibrecoordinacion__coordinacion__sede=inscripcion.sede, sesion=inscripcion.sesion, modalidad=inscripcion.modalidad, cerrado=False, fin__gte=datetime.now().date(), periodo__tipo__id=TIPO_PERIODO_REGULAR).order_by('-fin')[0]
        # else:
        #     return -1

        # BORRAR PARA EL PROXIMO PERIODO
        # if Nivel.objects.filter(periodo__matriculacionactiva=True, nivellibrecoordinacion__coordinacion__carrera=inscripcion.carrera, nivellibrecoordinacion__coordinacion__sede=inscripcion.sede, modalidad=inscripcion.modalidad, cerrado=False, fin__gte=datetime.now().date(), periodo__tipo__id=TIPO_PERIODO_REGULAR).exists():
        #     nivel = Nivel.objects.filter(periodo__matriculacionactiva=True,nivellibrecoordinacion__coordinacion__carrera=inscripcion.carrera, nivellibrecoordinacion__coordinacion__sede=inscripcion.sede, modalidad=inscripcion.modalidad, cerrado=False, fin__gte=datetime.now().date(), periodo__tipo__id=TIPO_PERIODO_REGULAR).order_by('-fin')[0]
        # else:
        #     return -1
    return nivel.id


def contar_nivel(niveles):
    try:
        mismaterias_aux = ""
        cantidad = len(niveles)
        i = 1
        for x in niveles:
            if i != cantidad:
                mismaterias_aux = mismaterias_aux + str(int(x)) + ","
            else:
                mismaterias_aux = mismaterias_aux + str(int(x))
            i += 1
        nivel = 0
        if mismaterias_aux != "":
            cursor = connection.cursor()
            # conocer en que nivel va, segun las materias seleccionadas
            sql = "select nm.id from sga_materia mate, sga_asignaturamalla am, sga_nivelmalla nm " \
                  " where mate.id in (" + mismaterias_aux + ") and mate.status = true and mate.asignaturamalla_id=am.id and am.status=true " \
                                                            " and nm.id=am.nivelmalla_id and nm.status=true GROUP by nm.id order by count(nm.id) desc, nm.id desc limit 1"
            cursor.execute(sql)
            results = cursor.fetchall()
            nivel = 0
            for per in results:
                nivel = per[0]
        return nivel
    except Exception as ex:
        raise NameError('Error')


def verificar_si_pertenece_materia_docente(idverifica, periodo, profesor, request):
    materias = Materia.objects.filter(profesormateria__profesor=profesor , status=True, profesormateria__principal=True, nivel__periodo=periodo, nivel__periodo__visible=True).distinct().order_by('asignatura')
    materia_r = Materia.objects.filter(profesormateria__tipoprofesor_id=6, status=True, profesormateria__profesor=profesor, nivel__periodo=periodo, nivel__periodo__visible=True).distinct().order_by('asignatura')
    if materia_r:
        if materias:
            allmateria = materias | materia_r
        else:
            allmateria = materia_r
    else:
        allmateria = materias
        if not allmateria:
            raise Exception('Permiso denegado.')
    materiano = Materia.objects.get(pk=idverifica)
    if not allmateria.filter(pk=idverifica).exists():
        log(u'Profesor %s intento ingresar notas de debere en materias no asignadas %s' % (profesor, materiano), request, "add")
        raise Exception('Permiso denegado.')


def secuencia_contrato_beca(becatipo):
    if becatipo == 23:
        reg = BecaAsignacion.objects.filter(status=True, solicitud__becatipo_id=23).aggregate(contrato=Max('numerocontrato') + 1)
    else:
        reg = BecaAsignacion.objects.filter(~Q(solicitud__becatipo_id=23), status=True).aggregate(contrato=Max('numerocontrato') + 1)

    if reg['contrato'] is None:
        secuencia = 1
    else:
        secuencia = reg['contrato']
    return secuencia


def secuencia_contrato_beca_aux(periodo):
    reg = BecaAsignacion.objects.filter(status=True, solicitud__periodo=periodo).aggregate(contrato=Max('numerocontrato') + 1)
    if reg['contrato'] is None:
        secuencia = 1
    else:
        secuencia = reg['contrato']
    return secuencia


def secuencia_solicitud_pago_beca(periodo):
    reg = SolicitudPagoBeca.objects.filter(status=True, periodo=periodo).aggregate(solicitud=Max('numerosolicitud') + 1)

    if reg['solicitud'] is None:
        secuencia = 1
    else:
        secuencia = reg['solicitud']
    return secuencia


def secuencia_contrato_maestria():
    reg = CompromisoPagoPosgrado.objects.filter(status=True, fecha__year=datetime.now().year).aggregate(contrato=Max('numerocontrato') + 1)

    if reg['contrato'] is None:
        secuencia = 1
    else:
        secuencia = reg['contrato']

    return secuencia


def secuencia_pagare_maestria():
    reg = CompromisoPagoPosgrado.objects.filter(status=True, fecha__year=datetime.now().year).aggregate(pagare=Max('numeropagare') + 1)

    if reg['pagare'] is None:
        secuencia = 1
    else:
        secuencia = reg['pagare']

    return secuencia


# def decrifrar_notificacion(persona, periodo):
#     from sagest.models import Pago, Rubro
#     from sga.funciones import null_to_numeric
#     tiene_valores_pendientes = False
#     msg= {}
#     data = {}
#     if persona:
#         if Rubro.objects.filter(persona=persona, cancelado=False, matricula__nivel__periodo=periodo, status=True).exists():
#             tiene_valores_pendientes = True
#             rubros = Rubro.objects.filter(persona=persona, cancelado=False, matricula__nivel__periodo=periodo, status=True).distinct()
#             rubros_vencidos = rubros.filter(fechavence__lt=datetime.now().date()).distinct()
#             if rubros_vencidos.exists():
#                 valor_rubros = null_to_numeric(rubros_vencidos.aggregate(valor=Sum('valortotal'))['valor'])
#                 valor_pagos = null_to_numeric(Pago.objects.filter(rubro__in=rubros_vencidos, status=True).distinct().aggregate(valor=Sum('valortotal'))['valor'])
#                 valores_vencidos = valor_rubros - valor_pagos
#                 msg = """<div class="alert alert-danger">
#                             <a  href="javascript:;" class="close" data-dismiss="alert">×</a>
#                             <h4 class="alert-heading">ALERTA</h4>
#                             Estimado/a estudiante, aun le quedan <b>VALORES PENDIENTES POR PAGAR</b>, total de deuda {{ persona.valores_vencidos|floatformat:2 }}
#                         </div>"""
#             else:
#                 valor_rubros = null_to_numeric(rubros.aggregate(valor=Sum('valortotal'))['valor'])
#                 valor_pagos = null_to_numeric(Pago.objects.filter(rubro__in=rubros, status=True).distinct().aggregate(valor=Sum('valortotal'))['valor'])
#                 valores_pendientes = valor_rubros - valor_pagos
#                 msg = """<div class="alert alert-warnign">
#                             <a  href="javascript:;" class="close" data-dismiss="alert">×</a>
#                             <h4 class="alert-heading">ALERTA</h4>
#                             Estimado/a estudiante, aun le quedan <b>VALORES PENDIENTES POR PAGAR</b>, total de deuda {{ persona.valores_pendientes|floatformat:2 }}
#                         </div>"""
#
#     data['tiene_valores_pendientes'] = tiene_valores_pendientes
#     data['msg_valores_pendientes'] = msg
#     return data


@transaction.atomic()
def oauth2epunemi(request):
    data = {}
    site_maintenance = variable_valor('SITIO_MANTENIMIENTO')
    if site_maintenance:
        return render(request, "maintenance.html", data)
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
                    client_id = request.POST['client_id']
                    user = authenticate(username=request.POST['user'].lower().strip(), password=request.POST['pass'])
                    if user is not None:
                        if not user.is_active:
                            loglogin(action_flag=FLAG_FAILED, action_app=APP_SGA, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, user=user, change_message=u"Usuario no activo")
                            return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, usuario no activo.'})
                        else:
                            if Persona.objects.db_manager("sga_select").only("id").filter(usuario=user).exists():
                                persona = Persona.objects.filter(usuario=user)[0]
                                if persona.tiene_perfil():
                                    app = 'sga'
                                    # perfiles = persona.mis_perfilesusuarios_app(app)
                                    # perfilprincipal = persona.perfilusuario_principal(perfiles, app)
                                    # if not perfilprincipal:
                                    #     return JsonResponse({"result": "bad", 'mensaje': u'No existe un perfiles para esta aplicacion.'})

                                    loglogin(action_flag=FLAG_SUCCESSFUL, action_app=APP_SGA, ip_private=capippriva,
                                             ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                             screen_size=screensize, user=user)

                                    if persona.es_administrativo() or persona.es_profesor() or persona.es_administrador():
                                        if variable_valor('SEND_LOGIN_EMAIL_SGA') and not DEBUG:
                                            send_html_mail("Login exitoso SGA.", "emails/loginexito.html", {'sistema': 'SGA-EPUNEMI', 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies, 'screensize': screensize, 't': miinstitucion()}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[0][1])

                                    url_redirect = request.POST.get('next', '/')
                                    tokenid = encrypt(persona.id)
                                    return JsonResponse({"result": "ok", "sessionid": request.session.session_key, 'url_redirect': f'{url_redirect}?client_id={client_id}&tkn={tokenid}'})
                                else:
                                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existen perfiles activos.'})
                            else:
                                loglogin(action_flag=FLAG_UNKNOWN, action_app=APP_SGA, ip_private=capippriva,
                                         ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                         screen_size=screensize, change_message=u"USUARIO: %s - CLAVE: %s" % (request.POST['user'].lower().strip(), request.POST['pass']))
                                # log(u'Login fallido, no existe el usuario: %s' % request.POST['user'], request, "add")
                                return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existe el usuario.'})
                    else:
                        if not Persona.objects.filter(usuario__username=request.POST['user'].lower()).exists():
                            loglogin(action_flag=FLAG_UNKNOWN, action_app=APP_SGA, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, change_message=u"USUARIO: %s - CLAVE: %s" % (request.POST['user'].lower().strip(), request.POST['pass']))
                        if Persona.objects.db_manager("sga_select").filter(usuario__username=request.POST['user'].lower()).exists():
                            persona = Persona.objects.db_manager("sga_select").filter(usuario__username=request.POST['user'].lower())[0]
                            loglogin(action_flag=FLAG_FAILED, action_app=APP_SGA, ip_private=capippriva,
                                     ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                     screen_size=screensize, user=persona.usuario, change_message=u"Clave Incorrecta")
                            if persona.es_administrativo() or persona.es_profesor() or persona.es_administrador():
                                send_html_mail("Login fallido SGA.", "emails/loginfallido.html", {'sistema': u'Sistema de Gestión Académica', 'fecha': datetime.now().date(), 'hora': datetime.now().time(), 'bs': browser, 'ip': client_address, 'ipvalida': capippriva, 'os': ops, 'cookies': cookies, 'screensize': screensize, 't': miinstitucion()}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[0][1])
                        return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, credenciales incorrectas.'})
                except Exception as ex:
                    error = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    print(ex)
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, Error en el sistema. Detalle: %s - %s'%(ex.__str__(),error)})
            if action == 'validarlog':
                try:
                    with transaction.atomic():
                        from bd.models import UserToken
                        persona = request.session['persona']
                        fecha = datetime.now().date()
                        hora = datetime.now().time()
                        fecha_hora = fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__()
                        token_ = md5(str(encrypt(persona.usuario.id) + fecha_hora).encode("utf-8")).hexdigest()
                        lifetime = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
                        perfil_ = UserToken.objects.create(user=request.user, token=token_, action_type=5, app=5, isActive=True, date_expires = datetime.now() + lifetime)
                        res_json = {"result": True, "url_redirect": f'http://epunemi.gob.ec/oauth2/?tknbtn={token_}&tkn={encrypt(persona.id)}'}
                except Exception as ex:
                    res_json = {'result': False, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

        # cache_page(60 * 15)
        data = {"title": u"SGA - Iniciar Sesión", "background": random.randint(1, 2)}
        data['request'] = request
        data['info'] = request.GET['info'] if 'info' in request.GET else ''
        hoy = datetime.now().date()
        data['currenttime'] = datetime.now()
        data['aplicacion_estudiantes_android'] = URL_APLICACION_ESTUDIANTE_ANDROID
        data['aplicacion_estudiantes_ios'] = URL_APLICACION_ESTUDIANTE_IOS
        data['aplicacion_profesor_android'] = URL_APLICACION_PROFESOR_ANDROID
        data['declaracion_sga'] = DECLARACION_SGA
        data['contacto_email'] = CONTACTO_EMAIL
        data['server_response'] = SERVER_RESPONSE
        data['tipoentrada'] = request.session['tipoentrada'] = "SGA"
        data['public_key'] = variable_valor('GOOGLE_RECAPTCHA_PUBLIC_KEY')
        data["next"] = request.GET.get('next_url', False)
        data["client_id"] = request.GET.get('client_id', False)
        return render(request, "oauth2epunemi/loginsga.html", data)
