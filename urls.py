
# -*- coding: latin-1 -*-
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import re_path, include, path
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.static import static

# Uncomment the next two lines to enable the admin:
from django.contrib import admin, messages
from django.http import HttpResponseRedirect, HttpResponse
from django.utils.encoding import smart_str
import posixpath
from django.utils._os import safe_join
from pathlib import Path

import settings
from resttoken.AuhToken import CustomAuthToken
from sga import diccionario
from django.views.static import serve
# from rest_framework.authtoken import views
from django.core.exceptions import ObjectDoesNotExist
from wsgiref.util import FileWrapper
import mimetypes, os

from sga.funciones import puede_realizar_accion_is_superuser

urlpatterns = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += staticfiles_urlpatterns()


class FixedFileWrapper(FileWrapper):
    def __iter__(self):
        self.filelike.seek(0)
        return self


# @login_required(redirect_field_name='ret', login_url='/loginsga?info=Permiso denegado')
def protected_serve(request, path, document_root=None):
    try:
        data = {}
        from gdocumental.models import DepartamentoArchivoDocumentos
        if not request.user.is_authenticated:
            loginurl_ = 'loginsga' if True else 'loginsagest'
            url_ = '/{}?ret={}'.format(loginurl_, request.path)
            messages.error(request, 'Debe iniciar sesión para continuar.')
            return redirect(url_)
        permisototal = False
        # if 'persona' in request.session:
        #     if request.session['persona'].usuario.is_superuser:
        #         permisototal = True
        # if permisototal:
        #     return serve(request, path, document_root)
        first_folder = path.split('/')[0]
        # if '.backup' not in path and '.zip' not in path and '.tar' not in path:
        if not first_folder == 'backups':
            if request.user.is_superuser:
                return serve(request, path, document_root)
            else:
                documento_ = DepartamentoArchivoDocumentos.objects.db_manager('sga_select').values('id', 'usuario_creacion_id').filter(status=True).filter(Q(archivo=path))
                permisototal = documento_.exists()
                if permisototal:
                    # if request.user.id in documento_.values_list('usuario_creacion_id', flat=True):
                    return serve(request, path, document_root)
        else:
            # iddevteam = [810, 822, 840, 10724, 20533, 22207, 25298, 28141, 43766, 31352, 32363, 35314, 28134, 35279, 35269, 35288, 28195, 29882, 21960]
            if puede_realizar_accion_is_superuser(request, 'sga.puede_descargar_db_backup'):
                my_file = str(Path(safe_join(document_root, path)))
                response = HttpResponse(FixedFileWrapper(open(my_file, 'rb')), content_type=mimetypes.guess_type(my_file)[0])
                response['Content-Length'] = os.path.getsize(my_file)
                response['Content-Disposition'] = "attachment; filename=%s" % os.path.basename(my_file)
                return response
        data['title'] = f'Solicitar Acceso'
        return render(request, 'login/accesodenegado.html', data)
    except ObjectDoesNotExist:
        messages.warning(request, 'Ud. no tiene permisos para acceder a esta ruta')
        return redirect('/')
    except Exception as ex:
        from django.http import JsonResponse
        msg_ex = str(ex).replace('?','').replace('\\','/')
        messages.warning(request, msg_ex)
        return JsonResponse({"result": "bad", "msg": f"{msg_ex}"})


# import debug_toolbar


# if not settings.DEBUG:
urlpatterns += [re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
                re_path(r'^media/(?P<path>.*)$', protected_serve, {'document_root': settings.MEDIA_ROOT}),
                re_path(r'^mediadocumental/(?P<path>.*)$', protected_serve, {'document_root': settings.MEDIA_ROOT_SECRET}), ]

urlpatterns += [re_path(r'^apimobile/', include('mobile.urls')),
                # re_path(r'^oauth/2/', include('oauth2.urls')),
                re_path(r'^api/1.0/', include('api.urls')),
                # re_path(r'^api-token-auth/', views.obtain_auth_token),
                re_path(r'^', include('posgrado.urls')),
                re_path(r'^', include('sga.urls')),
                re_path(r'^', include('balcon.urls')),
                re_path(r'^', include('even.urls')),
                re_path(r'^', include('inno.urls')),
                re_path(r'^', include('bd.urls')),
                # re_path(r'^__debug__/', include(debug_toolbar.urls)),
                re_path(r'^', include('sagest.urls')),
                re_path(r'^', include('helpdesk.urls')),
                re_path(r'^', include('investigacion.urls')),
                re_path(r'^', include('becadocente.urls')),
                re_path(r'^', include('certi.urls')),
                re_path(r'^', include('matricula.urls')),
                re_path(r'^', include('soap.urls')),
                re_path(r'^', include('pdip.urls')),
                re_path(r'^', include('poli.urls')),
                re_path(r'^', include('gdocumental.urls')),
                # AUTOMATIZACIÓN DE PROCESOS
                re_path(r'^', include('automatiza.urls')),
                path('unemi_2021_admin_desarrollo_/', admin.site.urls),
                # re_path(r'^unemi_2021_admin_desarrollo_/', include(admin.site.urls)),
                re_path(r'^diccionario$', diccionario.view, name='sga_diccionario_view'),
                re_path(r'^ckeditor/', include('ckeditor_uploader.urls')),
                # Admision
                re_path(r'^', include('juventud.urls')),
                re_path(r'^', include('admision.urls')),
                re_path(r'^', include('moodle.urls')),

                # re_path(r'^api-auth/', include('rest_framework.urls')),
                re_path(r'^api-token-auth/', CustomAuthToken.as_view()),
                re_path("select2/", include("django_select2.urls")),
                re_path(r'^', include('postulaciondip.urls')),
                # re_path(r'^', include('clrncelery.urls')),
                # NOTIFICACIONES WEB
                # re_path('', include('pwa.urls')),
                re_path('^', include('wpush.urls')),
                # NOTIFICACIONES WEB
                re_path('^', include('ws.urls')),

                # POSTULATE
                re_path(r'^', include('postulate.urls')),
                # POSTULATE
                # FERIA
                re_path(r'^', include('feria.urls')),
                # FERIA

                #SOCIOECON
                re_path(r'^', include('socioecon.urls')),
                #SOCIOECON

                # AGENDAMIENTO DE CITA
                re_path(r'^', include('cita.urls')),
                # AGENDAMIENTO DE CITA

                # FACE ID
                re_path(r'^', include('faceid.urls')),
                # FACE ID

                # LABORATORIO
                re_path(r'^', include('laboratorio.urls')),
                # LABORATORIO

                # EMPLEO
                re_path(r'^', include('empleo.urls')),

                # # EMPRESA
                # re_path(r'^', include('empresa.urls')),
                # PLAN DE CARRERA TALENTO HUMANO
                re_path(r'^', include('plan.urls')),

                # SECRETARIA
                re_path(r'^', include('secretaria.urls')),
                #
                # # # BLOCKCHAIN
                # re_path(r'^', include('valida.urls')),

                # AYUDANTIAS DE INVESTIGACION
                re_path(r'^', include('vincula.urls')),
                # AYUDANTIAS DE INVESTIGACION
                #
                # HOMOLOGACION DE ASIGNATURAS
                re_path(r'^', include('homologa.urls')),


                # EDCON
                re_path(r'^', include('edcon.urls')),

                # IDIOMA
                re_path(r'^', include('idioma.urls')),

                # OFIMATICA (OMA)
                re_path(r'^', include('oma.urls')),

                # FORMACION EJECUTIVA
                re_path(r'^', include('ejecuform.urls')),
                # socialauth
                path('social-auth/', include('social_django.urls', namespace="social")),

                #DIRECTIVO
                re_path(r'^', include('directivo.urls')),
                ]
