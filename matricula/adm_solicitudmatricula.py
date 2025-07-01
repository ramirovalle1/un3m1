# -*- coding: UTF-8 -*-
import random
from datetime import datetime

import xlwt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.aggregates import Avg
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from xlwt import *

from decorators import secure_module, last_access
from matricula.funciones import valid_intro_module_estudiante
from settings import HOMITIRCAPACIDADHORARIO, CALCULO_POR_CREDITO, NOTA_ESTADO_EN_CURSO, MATRICULACION_LIBRE
from sga.commonviews import adduserdata, conflicto_materias_seleccionadas
from sga.forms import SolicitudForm, ConfiguracionTerceraMatriculaForm
from sga.funciones import MiPaginador, log, generar_nombre, fechatope, variable_valor
from sga.models import SolicitudMatricula, SolicitudDetalle, AsignaturaMalla, Asignatura, Matricula, Materia, \
    AgregacionEliminacionMaterias, MateriaAsignada, \
    Coordinacion, TipoSolicitud, ConfiguracionTerceraMatricula, Inscripcion, ProfesorMateria, GruposProfesorMateria, \
    AlumnosPracticaMateria
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_administrativo():
        return HttpResponseRedirect(f"/?info=Solo se permite perfiles administrativos")
    persona = request.session['persona']
    periodo = request.session['periodo']
    hoy = datetime.now().date()
    miscarreras = persona.mis_carreras()

    if request.method == 'POST':
        action = request.POST['action']

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Servicios de matrícula'
                data['servicios'] = [
                    {"img": "/static/images/iconos/enrollment_special.png",
                     "title": "Matrícula especial",
                     "description": "Envio de solicitud de matrícula especial",
                     "url": "/adm_solicitudmatricula/especial"
                     },
                    # {"img": "/static/images/iconos/remove_enrollment.png",
                    #  "title": "Retiro de asignatura o matrícula",
                    #  "description": "Envio de solicitud de retiro de asignatura o matrícula",
                    #  "url": "/adm_solicitudmatricula/especial"
                    #  },
                ]
                return render(request, "adm_solicitudmatricula/view.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                return render(request, "adm_solicitudmatricula/error.html", data)
