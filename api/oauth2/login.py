# coding=latin-1
import json
import random
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen, Request

from django.contrib import messages
from django.contrib.auth import views, get_user_model
from django.contrib.auth import authenticate, logout, login
from oauth2_provider.models import Application
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, QueryDict
from django.shortcuts import render, redirect
from django.views.generic import CreateView, UpdateView
from django.urls import reverse_lazy
from oauth2_provider.decorators import protected_resource
from sga.commonviews import get_client_ip
from sga.funciones import variable_valor, log
from sga.models import Persona, TituloInstitucion, DeclaracionUsuario, Matricula

from oauth2.forms import SignUpForm, LoginForm, UpdateUserForm
from settings import EMAIL_DOMAIN, SERVER_RESPONSE, CONTACTO_EMAIL, URL_APLICACION_ESTUDIANTE_ANDROID, \
    URL_APLICACION_ESTUDIANTE_IOS, URL_APLICACION_PROFESOR_ANDROID, DECLARACION_SGA

User = get_user_model()


@transaction.atomic()
def login_user(request):
    data = {}
    capippriva = ''
    # if EMAIL_DOMAIN in request.META['HTTP_HOST']:
    #     if 'sga' not in request.META['HTTP_HOST'] and 'pruebasonline' not in request.META['HTTP_HOST']:
    #         if 'admisionposgrado' in request.META['HTTP_HOST']:
    #             return HttpResponseRedirect('/loginposgrado')
    #         else:
    #             return HttpResponseRedirect('/loginsagest')

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
                    app_client = None
                    next = request.POST['next'] if 'next' in request.POST and request.POST['next'] else None
                    client_id = request.POST['client_id'] if 'client_id' in request.POST and request.POST['client_id'] else None
                    if not next or not client_id or not Application.objects.filter(client_id=client_id).exists():
                        return JsonResponse({"result": "bad", 'mensaje': u'Servicio no encontrado'})
                    app_client = Application.objects.filter(client_id=client_id).first()
                    user = authenticate(username=request.POST['user'].lower().strip(), password=request.POST['pass'])
                    if not user:
                        #log(u'Login fallido, no existe el usuario: %s' % request.POST['user'], request, "add")
                        return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existe el usuario.'})
                    if not user.is_active:
                        return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, usuario no activo.'})

                    if Persona.objects.db_manager("sga_select").only("id").filter(usuario=user).exists():
                        persona = Persona.objects.filter(usuario=user)[0]
                        if not persona.tiene_perfil():
                            return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, no existen perfiles activos.'})
                        app = 'sga'
                        perfiles = persona.mis_perfilesusuarios_app(app)
                        perfilprincipal = persona.perfilusuario_principal(perfiles, app)
                        # # validacion login matricula
                        if variable_valor('BLOQUEO_LOGIN_MATRICULA'):
                            if Matricula.objects.values('id').filter(nivel__periodo__id=variable_valor('ID_BLOQUEO_LOGIN_MATRICULA'), status=True, inscripcion=perfilprincipal.inscripcion_id).exists():
                                return JsonResponse({"result": "bad", 'mensaje': u'Estimado estudiante, estamos teniendo intermitencia en nuestros servicios, intentelo mas tarde...'})
                        # # validacion ldap por sga
                        if not perfilprincipal:
                            return JsonResponse({"result": "bad", 'mensaje': u'No existe un perfiles para esta aplicacion.'})

                        request.session.set_expiry(240 * 60)
                        request.session['login_manual'] = True
                        login(request, user)
                        request.session['perfiles'] = perfiles
                        request.session['persona'] = persona
                        request.session['capippriva'] = capippriva
                        request.session['tiposistema'] = app
                        request.session['perfilprincipal'] = perfilprincipal
                        request.session['nombresistema'] = u'Sistema de Gestión Académica'
                        log(u'Login con exito: %s - %s - %s - IPPU: %s - IPPR: %s' % (persona, browser, ops, client_address, capippriva), request, "add")
                        # if client_address in ipvalidas:
                        #     if DECLARACION_SGA:
                        #         declaracionusuario = DeclaracionUsuario(persona=persona,
                        #                                                 fecha=datetime.now(),
                        #                                                 ip=client_address,
                        #                                                 sistema='MOODLE')
                        #         declaracionusuario.save(request)
                        #         log(u'Declaracion de usuario en el MOODLE: %s [%s]' % (declaracionusuario, declaracionusuario.id), request, "add")
                        return JsonResponse({"result": "ok", "sessionid": request.session.session_key, "next": next})
                    else:
                        if Persona.objects.filter(usuario__username=request.POST['user'].lower()).exists():
                            persona = Persona.objects.filter(usuario__username=request.POST['user'].lower()).first()
                            log(u'Login fallido SGA-OAuth: %s - %s - %s - IPPU: %s - IPPR: %s' % (persona, browser, ops, client_address, capippriva), request, "add", user=persona.usuario)
                            if persona.es_administrativo() or persona.es_profesor() or persona.es_administrador():
                                pass
                        return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, credenciales incorrectas.'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", 'mensaje': u'Login fallido, Error en el sistema.'})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        # cache_page(60 * 15)
        app_client = None
        client_id = None
        redirecto_to_next = None
        print(request.META['QUERY_STRING'])
        if 'next' in request.GET and request.GET['next']:
            redirecto_to_next = request.GET['next']
            url, next = request.GET['next'].split(sep="?")
            qGET = QueryDict(next, mutable=True)
            client_id = qGET['client_id'] if 'client_id' in qGET and qGET['client_id'] else None
            if client_id and Application.objects.filter(client_id=client_id).exists():
                app_client = Application.objects.filter(client_id=client_id).first()
            if 'persona' in request.session:
                if app_client:
                    return HttpResponseRedirect("/api/1.0/oauth/2/authorize?client_id=%s" % app_client.client_id)
                else:
                    return HttpResponseRedirect("/api/1.0/oauth/2/logout")
        data = {"title": u"MOODLE", "background": random.randint(1, 2)}
        data['request'] = request
        data['info'] = request.GET['info'] if 'info' in request.GET else ''
        hoy = datetime.now().date()
        data['currenttime'] = datetime.now()
        data['institucion'] = TituloInstitucion.objects.db_manager("sga_select").values("nombre").all()[0]['nombre'] if TituloInstitucion.objects.values('id').exists() else ''
        if client_address in ipvalidas:
            data['validar_con_captcha'] = False
            data['declaracion_sga'] = False
        else:
            data['validar_con_captcha'] = variable_valor('VALIDAR_CON_CAPTCHA_SGA')
            data['declaracion_sga'] = DECLARACION_SGA

        data['server_response'] = SERVER_RESPONSE
        data['tipoentrada'] = request.session['tipoentrada'] = "Moodle"
        data['app_client'] = app_client
        if not app_client:
            messages.error(request, 'Usuario no encontrado')
            return redirect('/')
        data['redirecto_to_next'] = redirecto_to_next
        data['form'] = LoginForm()
        return render(request, "oauth2/login.html", data)


def logout_user(request):
    logout(request)
    return HttpResponseRedirect("/api/1.0/oauth/2/login")


"""
class LoginViewAuth(LoginView):
    form_class = LoginForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Login'
        return context

    def get_success_url(self):
        url = self.get_redirect_url()
        return url or reverse_lazy('profile-view', args=(self.request.user.id,))


class RegistrationForm(CreateView):
    form_class = SignUpForm
    template_name = 'registration/signup.html'
    success_url = reverse_lazy('login')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(*kwargs)
        context['title'] = 'Sign Up'
        return context


class ProfileView(UpdateView):
    model = User
    template_name = 'consumer/profile.html'
    form_class = UpdateUserForm

    def get_success_url(self):
        return reverse_lazy('profile-view', args=(self.request.user.id,))

    def get_queryset(self):
        if self.request.user.is_anonymous:
            return None
        return self.model.objects.filter(id=self.request.user.id)


@protected_resource(scopes=['read'])
def profile(request):
    return HttpResponse(json.dumps({
        "id": request.resource_owner.id,
        "username": request.resource_owner.username,
        "email": request.resource_owner.email,
        "first_name": request.resource_owner.first_name,
        "last_name": request.resource_owner.last_name
    }), content_type="application/json")
"""
