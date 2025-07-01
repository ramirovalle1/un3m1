# -*- coding: latin-1 -*-
from django.template import Context
from django.template.loader import get_template
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from posgrado.forms import AdmiPeriodoForm
from settings import MATRICULACION_LIBRE, VERIFICAR_CONFLICTO_DOCENTE
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import ClaseForm, AulaForm, ClaseTodosturnosForm, ClaseHorarioForm
from sga.funciones import log, variable_valor
from sga.models import Sede, Carrera, Nivel, Turno, Clase, Materia, NivelMalla, Malla, Aula, Profesor, ProfesorMateria, \
    ClaseAsincronica, DIAS_CHOICES, Bloque, Sesion
from sga.templatetags.sga_extras import encrypt


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
                if 'info' in request.GET:
                    raise NameError(f"{request.GET['info']}")
                data['title'] = u'Administración de horarios'
                menu_panel = [
                    {"url": "/adm_horarios/clases",
                     "img": "/static/images/iconos/class_schedule.png",
                     "title": "Horarios de clases",
                     "description": "Administración de horarios de clases",
                     },
                    {"url": "/adm_horarios/examenes",
                     "img": "/static/images/iconos/exam-online-study.png",
                     "title": "Horarios de exámenes",
                     "description": "Administración de horarios de exámenes",
                     },
                    {"url": "/adm_horarios/examenes_bloques",
                     "img": "/static/images/iconos/exam-calendar-test.png",
                     "title": "Visualizar horario de examenes",
                     "description": "Visualizar horario de examenes por bloques y aulas",
                     },
                    {"url": "/adm_horarios/examenes_ensedes",
                     "img": "/static/images/iconos/exam-online-study.png",
                     "title": "Horarios de exámenes en sedes",
                     "description": "Administración de horarios de exámenes en sedes",
                     },
                    {"url": "/adm_horarios/disertaciones",
                     "img": "/static/images/iconos/carrera.png",
                     "title": "Horarios de disertaciones",
                     "description": "Administración de horarios de disertaciones",
                     },

                ]
                if persona.es_coordinadorcarrera_enlinea(request.session['periodo']) or persona.usuario.is_superuser or persona.grupos().values("id").filter(pk=143).exists():
                    menu_panel.append({
                        "url": "/adm_horarios/examenes_ensedes/coordinacion",
                        "img": "/static/images/iconos/exam-calendar-test.png",
                        "title": "Resumen de examenes en sedes",
                        "description": "Resumen de examenes en sedes para directores de carrera",
                    })
                data['menu_panel'] = menu_panel
                return render(request, "adm_horarios/panel.html", data)

            except Exception as ex:
                data['msg_error'] = ex.__str__()
                return render(request, "adm_horarios/error.html", data)
