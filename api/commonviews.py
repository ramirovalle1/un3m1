from datetime import datetime

from django.contrib.auth import logout, login
from django.contrib.auth.models import User
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from bd.models import TemplateBaseSetting
from sga.commonviews import adduserdata
from sga.funciones import log
from sga.models import Periodo


def changeTokenUser(request):
    from bd.models import UserToken, UserProfileChangeToken
    with transaction.atomic():
        try:
            # logout(request)
            if not 'token' in request.GET or not 'code' in request.GET or not 'ret' in request.GET:
                raise NameError(u"Parametros no encontrados")
            token = request.GET['token']
            code = request.GET['code']
            ret = request.GET['ret']
            data = {}
            if not token or not code or not ret:
                raise NameError(u"Parametros invalidos")
            if not UserToken.objects.values("id").filter(token=token, action_type=4, app=1, isActive=True, date_expires__gte=datetime.now()).exists():
                raise NameError(u"Token invalido")
            eUserToken = UserToken.objects.filter(token=token, action_type=4, app=1, isActive=True, date_expires__gte=datetime.now())[0]
            if not UserProfileChangeToken.objects.values("id").filter(user_token=eUserToken, codigo=code, isActive=True).exists():
                raise NameError(u"Código invalido")
            eUserProfileChangeToken = UserProfileChangeToken.objects.filter(user_token=eUserToken, codigo=code, isActive=True)[0]
            persona = eUserProfileChangeToken.perfil_destino.persona
            user = User.objects.get(pk=persona.usuario_id)
            if request.user.is_anonymous:
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                request.session['login_manual'] = True
                login(request, user)
                log(u'%s - entro con token: %s' % (persona, str(eUserToken.token)), request, "add")
                if not persona.tiene_perfil():
                    raise NameError(u"No tiene perfil activo")
                app = 'sga'
                perfiles = persona.mis_perfilesusuarios_app(app)
                perfilprincipal = eUserProfileChangeToken.perfil_destino
                request.session['perfiles'] = perfiles
                request.session['persona'] = persona
                request.session['capippriva'] = ''
                request.session['tiposistema'] = app
                request.session['perfilprincipal'] = perfilprincipal
                nombresistema = u'Sistema de Gestión Académica'
                eTemplateBaseSetting = None
                if TemplateBaseSetting.objects.values().filter(status=True, app=1).exists():
                    eTemplateBaseSetting = TemplateBaseSetting.objects.filter(status=True, app=1)[0]
                    nombresistema = eTemplateBaseSetting.name_system
                request.session['eTemplateBaseSetting'] = eTemplateBaseSetting
                request.session['nombresistema'] = nombresistema
                if perfilprincipal.es_estudiante():
                    inscripcion = perfilprincipal.inscripcion
                    if 'periodos_estudiante' not in request.session:
                        request.session['periodos_estudiante'] = Periodo.objects.filter(nivel__matricula__inscripcion=inscripcion, status=True, nivel__status=True, nivel__matricula__status=True, nivel__matricula__inscripcion__status=True).order_by('-inicio')
                    periodos_estudiante = request.session['periodos_estudiante']
                    if 'matricula' not in request.session:
                        if eUserProfileChangeToken.periodo:
                            request.session['matricula'] = inscripcion.mi_matricula_periodo(eUserProfileChangeToken.periodo.id)
                        else:
                            request.session['matricula'] = inscripcion.matricula2()
                    matricula = request.session['matricula']
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
                            request.session['periodo'] = None
                    if 'coordinacion' not in request.session:
                        request.session['coordinacion'] = inscripcion.carrera.coordinacion_set.values_list('id', flat=True)[0]
                adduserdata(request, data)
            else:
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                request.session['login_manual'] = True
                login(request, user)
                if not persona.tiene_perfil():
                    raise NameError(u"No tiene perfil activo")
                app = 'sga'
                perfiles = persona.mis_perfilesusuarios_app(app)
                request.session['perfiles'] = perfiles
                request.session['persona'] = persona
                request.session['capippriva'] = ''
                request.session['tiposistema'] = app
                nombresistema = u'Sistema de Gestión Académica'
                eTemplateBaseSetting = None
                if TemplateBaseSetting.objects.values().filter(status=True, app=1).exists():
                    eTemplateBaseSetting = TemplateBaseSetting.objects.filter(status=True, app=1)[0]
                    nombresistema = eTemplateBaseSetting.name_system
                request.session['eTemplateBaseSetting'] = eTemplateBaseSetting
                request.session['nombresistema'] = nombresistema
                request.session['perfilprincipal'] = perfilprincipal = eUserProfileChangeToken.perfil_destino
                if perfilprincipal.es_estudiante():
                    inscripcion = perfilprincipal.inscripcion
                    request.session['periodos_estudiante'] = Periodo.objects.filter(nivel__matricula__inscripcion=inscripcion, status=True, nivel__status=True, nivel__matricula__status=True, nivel__matricula__inscripcion__status=True).order_by('-inicio')
                    periodos_estudiante = request.session['periodos_estudiante']
                    if eUserProfileChangeToken.periodo:
                        request.session['matricula'] = inscripcion.mi_matricula_periodo(eUserProfileChangeToken.periodo.id)
                    else:
                        request.session['matricula'] = inscripcion.matricula2()
                    matricula = request.session['matricula']
                    if matricula:
                        request.session['periodo'] = matricula.nivel.periodo
                    else:
                        request.session['ultimamatricula'] = inscripcion.ultima_matricula()
                        ultimamatricula = request.session['ultimamatricula']
                        if ultimamatricula:
                            request.session['periodo'] = periodos_estudiante[0] if periodos_estudiante else None
                        else:
                            request.session['periodo'] = None
                        request.session['coordinacion'] = inscripcion.carrera.coordinacion_set.values_list('id', flat=True)[0]
                    adduserdata(request, data)
            return HttpResponseRedirect(f"{ret}")
        except Exception as ex:
            transaction.set_rollback(True)
            logout(request)
            import sys
            return HttpResponseRedirect(f"/loginsga?info={ex.__str__()}**{format(sys.exc_info()[-1].tb_lineno)}")
