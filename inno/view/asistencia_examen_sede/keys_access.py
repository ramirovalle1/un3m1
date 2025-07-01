# -*- coding: latin-1 -*-
import json
import sys
import random
from hashlib import md5
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from xlwt import Workbook
from xlwt import *
from django.forms.models import model_to_dict
from django.template import Context
from django.template.loader import get_template
from django.contrib.auth.decorators import login_required
from django.db import transaction, connections
from django.db.models import Q, F, Sum, Count
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render

from bd.models import FLAG_FAILED, APP_EXAMEN, FLAG_UNKNOWN, FLAG_SUCCESSFUL, UserToken
from decorators import secure_module, last_access
from inno.forms import AccesoExamenForm
from inno.funciones import generar_clave_aleatoria
from inno.models import MatriculaSedeExamen, FechaPlanificacionSedeVirtualExamen, TurnoPlanificacionSedeVirtualExamen, \
    AulaPlanificacionSedeVirtualExamen, MateriaAsignadaPlanificacionSedeVirtualExamen
from inno.runBackGround import ReportPlanificacionSedes, ReportHorariosExamenesSedes
from inno.serializers.AsistenciaExamen import MateriaAsignadaPlanificacionSedeVirtualExamenSerializer
from settings import DEBUG, PIE_PAGINA_CREATIVE_COMMON_LICENCE
from sga.commonviews import adduserdata, traerNotificaciones, get_client_ip
from sga.funciones import log, puede_realizar_accion, MiPaginador, resetear_clave, loglogin
from sga.models import Nivel, Materia, MateriaAsignada, SedeVirtual, LaboratorioVirtual, Notificacion, Persona, Malla, \
    Matricula, DetalleModeloEvaluativo, Inscripcion, Coordinacion, Periodo
from sga.templatetags.sga_extras import encrypt
from Moodle_Funciones import buscarQuiz, accesoQuizIndividual, estadoQuizIndividual
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
import time


# @login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
# @last_access
def view(request):
    data = {}
    # adduserdata(request, data)
    # periodo = request.session['periodo']
    # persona = request.session['persona']
    data['tiposistema'] = 'sga'
    data['tipoentrada'] = 'SGA'
    data['currenttime'] = datetime.now()
    data['remotenameaddr'] = '%s' % (request.META['SERVER_NAME'])
    data['remoteaddr'] = '%s - %s' % (get_client_ip(request), request.META['SERVER_NAME'])
    data['pie_pagina_creative_common_licence'] = PIE_PAGINA_CREATIVE_COMMON_LICENCE
    hoy = datetime.now().date()
    if request.method == 'POST':
        action = request.POST.get('action', None)
        if action is None:
            return JsonResponse({"result": False, "message": u"Acción no encontrada"})

        if action == 'verifyIdentity':
            with transaction.atomic():
                try:
                    capippriva = request.POST.get('capippriva', '')
                    browser = request.POST.get('navegador', '')
                    ops = request.POST.get('os', '')
                    cookies = request.POST.get('cookies', '')
                    screensize = request.POST.get('screensize', '')
                    username = request.POST.get('username', None)
                    password = request.POST.get('password', None)
                    if username is None or password is None:
                        # return JsonResponse({"result": False, "message": u"Usuario y contraseña incorrecto"})
                        raise NameError(u"Usuario y contraseña incorrecto")
                    user = authenticate(username=username.lower().strip(), password=password)
                    if user is None:
                        # return JsonResponse({"result": False, "message": u"Credenciales incorrectas"})
                        raise NameError(u"Credenciales incorrectas")
                    client_address = get_client_ip(request)
                    if not user.is_active:
                        loglogin(action_flag=FLAG_FAILED, action_app=APP_EXAMEN, ip_private=capippriva,
                                 ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                 screen_size=screensize, user=user, change_message=u"Usuario no activo")
                        raise NameError(u"Usuario no activo")
                    ePersona = Persona.objects.filter(usuario=user).first()
                    if ePersona is None:
                        loglogin(action_flag=FLAG_UNKNOWN, action_app=APP_EXAMEN, ip_private=capippriva,
                                 ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                 screen_size=screensize,
                                 change_message=u"USUARIO: %s - CLAVE: %s" % (username.lower().strip(), password))
                        raise NameError(f"Usuario no existe")
                    if not ePersona.perfilusuario_set.values("id").filter(Q(administrativo__isnull=False) | Q(profesor__isnull=False), status=True):
                        loglogin(action_flag=FLAG_FAILED, action_app=APP_EXAMEN, ip_private=capippriva,
                                 ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                                 screen_size=screensize, user=user, change_message=u"Usuario no activo")
                        raise NameError(f"Usuario no activo")
                    if not ePersona.usuario.is_superuser:
                        if not ePersona.usuario.groups.filter(id__in=[388, 387]).exists():
                            raise NameError(f"No pertenece al grupo para acceder a ver la clave del examen")
                        if not ePersona.usuario.has_perm('inno.puede_ver_clave_examen_sede'):
                            raise NameError(f"No tiene permisos para acceder a ver la clave del examen")
                    loglogin(action_flag=FLAG_SUCCESSFUL, action_app=APP_EXAMEN, ip_private=capippriva,
                             ip_public=client_address, browser=browser, ops=ops, cookies=cookies,
                             screen_size=screensize, user=user)
                    id = request.POST.get('id', 0)
                    try:
                        eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro aula valido")
                    lifetime = 360 * 60
                    request.session.set_expiry(lifetime)
                    request.session['login_manual'] = True
                    login(request, user)
                    request.session['persona'] = ePersona
                    request.session['capippriva'] = capippriva
                    request.session['tiposistema'] = 'sga'
                    request.session['nombresistema'] = u'Sistema de Gestión Académica'
                    # request.session['periodo'] = Periodo.objects.get(pk=177)
                    if not eAulaPlanificacionSedeVirtualExamen.token:
                        ahora = datetime.now()
                        fecha = ahora.date()
                        hora = ahora.time()
                        fecha_hora = fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__()
                        token = md5(str(encrypt(user.id) + fecha_hora).encode("utf-8")).hexdigest()
                        eAulaPlanificacionSedeVirtualExamen.token = token
                        eAulaPlanificacionSedeVirtualExamen.save(usuario_id=ePersona.usuario.id)
                    token = eAulaPlanificacionSedeVirtualExamen.token
                    return JsonResponse({"result": True, "sessionid": request.session.session_key, 'token': token})
                except Exception as ex:
                    transaction.set_rollback(True)
                    # print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return JsonResponse({"result": False, 'message': ex.__str__()})

        elif action == 'verKey':
            try:
                id = request.POST.get('id', 0)
                try:
                    eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=id)
                except ObjectDoesNotExist:
                    raise NameError(u"No se encontro aula valido")
                return JsonResponse({"result": True, "password": eAulaPlanificacionSedeVirtualExamen.password})
            except Exception as ex:
                return JsonResponse({"result": False, 'message': ex.__str__()})

        return JsonResponse({"result": False, "message": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'viewKey':
                try:
                    periodo = request.session.get('periodo', None)
                    if periodo is None:
                        raise NameError(u"No se ha verificado su identidad")
                    id = int(encrypt(request.GET.get('id', encrypt('0'))))
                    token = request.GET.get('token', None)
                    try:
                        eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(Q(pk=id) | Q(token=token))
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro aula valido")
                    data['eTurnoPlanificacionSedeVirtualExamen'] = eTurnoPlanificacionSedeVirtualExamen = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion
                    data['eFechaPlanificacionSedeVirtualExamen'] = eFechaPlanificacionSedeVirtualExamen = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion
                    data['eSedeVirtual'] = eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                    data['eAulaPlanificacionSedeVirtualExamen'] = eAulaPlanificacionSedeVirtualExamen
                    data['title'] = f'Visualización de clave de accesso al examen {eAulaPlanificacionSedeVirtualExamen.aula.__str__()}'
                    data['ruta'] = None
                    data['persona'] = request.session['persona']
                    data['check_session'] = True
                    data['periodo'] = None
                    # data['ret'] = f'/adm_asistenciaexamensede/keys_access?idh={encrypt(eTurnoPlanificacionSedeVirtualExamen.id)}'
                    # fecha = eFechaPlanificacionSedeVirtualExamen.fecha
                    # horainicio = eTurnoPlanificacionSedeVirtualExamen.horainicio
                    # horafin = eTurnoPlanificacionSedeVirtualExamen.horafin
                    # data['ruta'] = [[f'/adm_asistenciaexamensede/keys_access?ids={encrypt(eSedeVirtual.id)}', f'{eSedeVirtual.nombre}'],
                    #                 [f'/adm_asistenciaexamensede/keys_access?idf={encrypt(eFechaPlanificacionSedeVirtualExamen.id)}', f'{fecha.strftime("%Y-%m-%d")}'],
                    #                 [f'/adm_asistenciaexamensede/keys_access?idh={encrypt(eTurnoPlanificacionSedeVirtualExamen.id)}', f'{horainicio.strftime("%H:%M")}-{horafin.strftime("%H:%M")}']]
                    return render(request, "adm_asistenciaexamensede/keys_access/visor/view.html", data)
                except Exception as ex:
                    data['msg_error'] = ex.__str__()
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return render(request, "adm_asistenciaexamensede/error.html", data)

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Claves de accesso de exámenes'
                # data['periodo'] = periodo = Periodo.objects.get(pk=224)
                data['periodo'] = periodo = request.session.get('periodo', None)
                data['persona'] = request.session.get('persona', None)
                eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.filter(turnoplanificacion__fechaplanificacion__periodo=periodo, status=True)
                data['eSedes'] = SedeVirtual.objects.filter(status=True, pk__in=eAulaPlanificacionSedeVirtualExamen.values_list('turnoplanificacion__fechaplanificacion__sede_id', flat=True))
                if 'ids' in request.GET:
                    ids = int(encrypt(request.GET['ids']))
                    data['eSede'] = eSedeVirtual = SedeVirtual.objects.get(pk=ids)
                    return render(request, "adm_asistenciaexamensede/keys_access/sedevirtual/view.html", data)
                if 'idf' in request.GET:
                    idf = int(encrypt(request.GET['idf']))
                    data['eFechaPlanificacionSedeVirtualExamen'] = eFechaPlanificacionSedeVirtualExamen = FechaPlanificacionSedeVirtualExamen.objects.get(pk=idf)
                    data['eSede'] = eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                    return render(request, "adm_asistenciaexamensede/keys_access/fechaplanificacion/view.html", data)
                if 'idh' in request.GET:
                    idh = int(encrypt(request.GET['idh']))
                    data['eTurnoPlanificacionSedeVirtualExamen'] = eTurnoPlanificacionSedeVirtualExamen = TurnoPlanificacionSedeVirtualExamen.objects.get(pk=idh)
                    data['eSede'] = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion.sede
                    data['eFechaPlanificacionSedeVirtualExamen'] = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion
                    return render(request, "adm_asistenciaexamensede/keys_access/horarioplanificacion/view.html", data)
                # if 'ida' in request.GET:
                #     ida = int(encrypt(request.GET['ida']))
                #     eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=ida)
                #     data['eSede'] = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion.fechaplanificacion.sede
                #     data['eFechaPlanificacionSedeVirtualExamen'] = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion.fechaplanificacion
                #     data['eTurnoPlanificacionSedeVirtualExamen'] = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion
                #     data['eAulaPlanificacionSedeVirtualExamen'] = eAulaPlanificacionSedeVirtualExamen
                #     return render(request, "adm_asistenciaexamensede/keys_access/aulaplanificacion/view.html", data)
                return render(request, "adm_asistenciaexamensede/keys_access/panel.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return render(request, "adm_asistenciaexamensede/error.html", data)
