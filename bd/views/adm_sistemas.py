# -*- coding: UTF-8 -*-
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from bd.models import LogQuery
from decorators import secure_module, last_access
from bd.forms import *
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
import sys
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}

    adduserdata(request, data)
    persona = request.session['persona']

    if request.method == 'POST':
        action = request.POST['action']
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Administración del sistema'

                if persona.sexo.id == 1:
                    icon_user_access_profile = "/static/images/iconos/user_access_profile_women.png"
                elif persona.sexo.id == 2:
                    icon_user_access_profile = "/static/images/iconos/user_access_profile_men.png"
                else:
                    icon_user_access_profile = "/static/images/iconos/user_access_profile.png"
                menu_panel = [
                    {"url": "/adm_sistemas/imagen_moodle",
                     "img": "/static/images/iconssga/icon_linea_grafica.svg",
                     "title": "Imágenes moodle",
                     "description": "Imágenes de moodle",
                     },
                    {"url": "/adm_sistemas/linea_grafica",
                     "img": "/static/images/iconssga/icon_linea_grafica.svg",
                     "title": "Linea Grafica",
                     "description": "Plantilla y elementos de desarrollo",
                     },
                    {"url": "/adm_sistemas/users",
                     "img": "/static/images/iconssga/icon_users.svg",
                     "title": "Usuarios",
                     "description": "Administración de usuarios",
                     },
                    {"url": "/adm_sistemas/groups",
                     "img": "/static/images/iconssga/icon_grupo.svg",
                     "title": "Grupos",
                     "description": "Administración de grupos",
                     },
                    {"url": "/adm_sistemas/modules",
                     "img": "/static/images/iconssga/icon_modulos.svg",
                     "title": "Modulos",
                     "description": "Administración de modulos",
                     },
                    {"url": "/adm_sistemas/persons",
                     "img": "/static/images/iconssga/icon_personas.svg",
                     "title": "Personas",
                     "description": "Administración de personas",
                     },
                    {"url": "/adm_sistemas/groups_modules",
                     "img": "/static/images/iconssga/icon_grupo_de_modulos.svg",
                     "title": "Grupos de Modulos",
                     "description": "Administración de grupos de modulos",
                     },
                    {"url": "/adm_sistemas/user_access_profile",
                     "img": "/static/images/iconssga/icon_perfil_acceso_usuario.svg",
                     "title": "Perfil Acceso Usuario",
                     "description": "Administración de perfiles de acceso usuarios",
                     },
                    {"url": "/adm_sistemas/academic_period",
                     "img": "/static/images/iconssga/icon_periodos_lectivos.svg",
                     "title": "Periodos académicos",
                     "description": "Administración de periodos académicos",
                     },
                    {"url": "/adm_sistemas/global_variables",
                     "img": "/static/images/iconssga/icon_variables.svg",
                     "title": "Variables Globales",
                     "description": "Administración de variables globales",
                     },
                    {"url": "/adm_sistemas/special_enrollment_process",
                     "img": "/static/images/iconssga/icon_proceso_matricula_especial.svg",
                     "title": "Proceso de matrícula especial",
                     "description": "Administración del proceso de matrícula especial",
                     },
                    {"url": "/adm_sistemas/remove_enrollment_process",
                     "img": "/static/images/iconssga/icon_proceso_retiro_matricula.svg",
                     "title": "Proceso de retiro de asignatura o matrícula",
                     "description": "Administración del proceso del retiro de asignatura o matrícula",
                     },
                    {"url": "/adm_sistemas/config_carnet",
                     "img": "/static/images/iconssga/icon_configuracion_carnet.svg",
                     "title": "Configuración de Carné",
                     "description": "Administración del proceso de carné estudiantil, administrativo y docente",
                     },
                    {"url": "/adm_sistemas/web_services",
                     "img": "/static/images/iconssga/icon_servicios_web.svg",
                     "title": "Servicios web",
                     "description": "Administración de servicios web",
                     },
                    {"url": "/adm_sistemas/setting_template",
                     "img": "/static/images/iconssga/icon_ajuste_plantillas.svg",
                     "title": "Ajustes de Plantillas",
                     "description": "Administración de ajustes de plantillas",
                     },
                    {"url": "/adm_sistemas/non_working_days",
                     "img": "/static/images/iconssga/icon_dias_no_laborables.svg",
                     "title": "Días no laborables",
                     "description": "Administración de días no laborables",
                     },
                    {"url": "/adm_sistemas/visita_modulos",
                     "img": "/static/images/iconssga/icon_visita_modulos.svg",
                     "title": "Visita de Modulos",
                     "description": "Estadistica de Visita de Modulos",
                     },
                    {"url": "/adm_sistemas/permissions",
                     "img": "/static/images/iconssga/icon_perfil_acceso_usuario.svg",
                     "title": "Administración de permisos",
                     "description": "Administración de permisos del sistema",
                     },
                    {"url": "/adm_sistemas/report_list",
                     "img": "/static/images/iconssga/icon_ajuste_plantillas.svg",
                     "title": "Reportes",
                     "description": "Reportes",
                     },
                    {"url": "/adm_sistemas/secretary/services",
                     "img": "/static/images/iconssga/icon_servicios_web.svg",
                     "title": "Servicios de secretaría",
                     "description": "Administración de servicios de secretaría",
                     },
                     {"url": "/adm_sistemas/options",
                      "img": "/static/images/iconssga/icon_configuracion_de_periodos.svg",
                      "title": "Opciones del Sistema",
                      "description": "Administración de opciones del SGA",
                     },
                    {"url": "/adm_sistemas/arbolcategoriassga",
                     "img": "/static/images/iconssga/icon_visita_modulos.svg",
                     "title": "Categorias de Modulos SGA",
                     "description": "Organizar Categorias SGA",
                     },
                    {"url": "/adm_sistemas/arbolcategoriassagest",
                     "img": "/static/images/iconssga/icon_visita_modulos.svg",
                     "title": "Categorias de Modulos SAGEST",
                     "description": "Organizar Categorias SAGEST",
                     },
                ]
                data['menu_panel'] = menu_panel
                return render(request, "adm_sistemas/panel.html", data)
            except Exception as ex:
                pass
