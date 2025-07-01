# -*- coding: latin-1 -*-
import json
import random

from django.core.exceptions import ObjectDoesNotExist
from xlwt import Workbook
from xlwt import *
from django.forms.models import model_to_dict
from django.template import Context
from django.template.loader import get_template
import sys
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction, connections
from django.db.models import Q, F, Sum, Count
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from inno.forms import SedeVirtualForm, LaboratorioVirtualForm, FechaPlanificacionSedeVirtualExamenForm, \
    HorarioPlanificacionSedeVirtualExamenForm, AulaPlanificacionSedeVirtualExamenForm, SedeVirtualPeriodoForm
from inno.funciones import generar_clave_aleatoria
from inno.models import MatriculaSedeExamen, FechaPlanificacionSedeVirtualExamen, TurnoPlanificacionSedeVirtualExamen, \
    AulaPlanificacionSedeVirtualExamen, MateriaAsignadaPlanificacionSedeVirtualExamen
from inno.runBackGround import ReportPlanificacionSedes, ReportHorariosExamenesSedes, ReportPlanificacionExamenes
from sga.commonviews import adduserdata, traerNotificaciones
from sga.excelbackground import reporte_persona_sin_examen
from sga.funciones import log, puede_realizar_accion, MiPaginador, generar_nombre
from sga.models import Nivel, Materia, MateriaAsignada, SedeVirtual, LaboratorioVirtual, Notificacion, Malla, Matricula, \
    DetalleModeloEvaluativo, TipoAula, Persona, SedeVirtualPeriodoAcademico
from sga.templatetags.sga_extras import encrypt
from inno.serializers.HorarioExamen import SedeVirtualSerializer, FechaPlanificacionSedeVirtualExamenSerializer, \
    TurnoPlanificacionSedeVirtualExamenSerializer, AulaPlanificacionSedeVirtualExamenSerializer, \
    MateriaAsignadaPlanificacionSedeVirtualExamenSerializer, PersonaSerializer


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    persona = request.session['persona']
    hoy = datetime.now().date()
    if request.method == 'POST':
        action = request.POST['action']

        return JsonResponse({"result": False, "message": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
        else:
            try:
                if 'info' in request.GET:
                    data['info'] = request.GET['info']
                data['title'] = u'Administración de horarios de disertación'
                data['ePeriodo'] = periodo
                data_json = {
                    'periodo_id': periodo.id,
                }
                data['eSedes'] = eSedes = SedeVirtual.objects.filter(pk=11, status=True, activa=True)
                if 'ids' in request.GET:
                    ids = int(request.GET['ids'])
                    eSedeVirtual = SedeVirtual.objects.get(pk=ids)
                    data_json['isView_FechaPlanificacion'] = True
                    eSedeSerializer = SedeVirtualSerializer(eSedeVirtual, context=data_json).data
                    data['eSede'] = eSedeSerializer
                    return render(request, "adm_horarios/examenes_sedes/sedevirtual/view.html", data)
                # if 'idf' in request.GET:
                #     idf = int(encrypt(request.GET['idf']))
                #     eFechaPlanificacionSedeVirtualExamen = FechaPlanificacionSedeVirtualExamen.objects.get(pk=idf)
                #     eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                #     # data_json['isView_FechaPlanificacion'] = True
                #     eSedeSerializer = SedeVirtualSerializer(eSedeVirtual, context={'periodo_id': periodo.id, 'isView_FechaPlanificacion': True}).data
                #     eFechaPlanificacionSedeVirtualExamenSerializer = FechaPlanificacionSedeVirtualExamenSerializer(eFechaPlanificacionSedeVirtualExamen, context={'periodo_id': periodo.id, 'isView_HoraPlanificacion': True}).data
                #     data['eSede'] = eSedeSerializer
                #     data['eFechaPlanificacionSedeVirtualExamen'] = eFechaPlanificacionSedeVirtualExamenSerializer
                #     return render(request, "adm_horarios/examenes_sedes/fechaplanificacion/view.html", data)
                # if 'idh' in request.GET:
                #     idh = int(encrypt(request.GET['idh']))
                #     eTurnoPlanificacionSedeVirtualExamen = TurnoPlanificacionSedeVirtualExamen.objects.get(pk=idh)
                #     eFechaPlanificacionSedeVirtualExamen = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion
                #     eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                #     eSedeSerializer = SedeVirtualSerializer(eSedeVirtual, context={'periodo_id': periodo.id, 'isView_FechaPlanificacion': True, 'isView_HoraPlanificacion': True}).data
                #     eFechaPlanificacionSedeVirtualExamenSerializer = FechaPlanificacionSedeVirtualExamenSerializer(eFechaPlanificacionSedeVirtualExamen, context=data_json).data
                #     eTurnoPlanificacionSedeVirtualExamenSerializer = TurnoPlanificacionSedeVirtualExamenSerializer(eTurnoPlanificacionSedeVirtualExamen, context={'periodo_id': periodo.id, 'isView_AulaPlanificacion': True}).data
                #     data['eSede'] = eSedeSerializer
                #     data['eFechaPlanificacionSedeVirtualExamen'] = eFechaPlanificacionSedeVirtualExamenSerializer
                #     data['eTurnoPlanificacionSedeVirtualExamen'] = eTurnoPlanificacionSedeVirtualExamenSerializer
                #     return render(request, "adm_horarios/examenes_sedes/horarioplanificacion/view.html", data)
                # if 'ida' in request.GET:
                #     ida = int(encrypt(request.GET['ida']))
                #     eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=ida)
                #     eTurnoPlanificacionSedeVirtualExamen = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion
                #     eFechaPlanificacionSedeVirtualExamen = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion
                #     eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                #     eSedeSerializer = SedeVirtualSerializer(eSedeVirtual, context={'periodo_id': periodo.id, 'isView_FechaPlanificacion': True, 'isView_HoraPlanificacion': True, 'isView_AulaPlanificacion': True}).data
                #     eFechaPlanificacionSedeVirtualExamenSerializer = FechaPlanificacionSedeVirtualExamenSerializer(eFechaPlanificacionSedeVirtualExamen, context=data_json).data
                #     eTurnoPlanificacionSedeVirtualExamenSerializer = TurnoPlanificacionSedeVirtualExamenSerializer(eTurnoPlanificacionSedeVirtualExamen, context=data_json).data
                #     eAulaPlanificacionSedeVirtualExamenSerializer = AulaPlanificacionSedeVirtualExamenSerializer(eAulaPlanificacionSedeVirtualExamen, context=data_json).data
                #     data['eSede'] = eSedeSerializer
                #     data['eFechaPlanificacionSedeVirtualExamen'] = eFechaPlanificacionSedeVirtualExamenSerializer
                #     data['eTurnoPlanificacionSedeVirtualExamen'] = eTurnoPlanificacionSedeVirtualExamenSerializer
                #     data['eAulaPlanificacionSedeVirtualExamen'] = eAulaPlanificacionSedeVirtualExamenSerializer
                #     data['eResponsable'] = PersonaSerializer(eAulaPlanificacionSedeVirtualExamen.responsable).data if eAulaPlanificacionSedeVirtualExamen.responsable else None
                #     search = None
                #     url_vars = ''
                #     eMateriaAsignadaPlanificacionSedeVirtualExamenes = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(aulaplanificacion=eAulaPlanificacionSedeVirtualExamen, status=True)
                #     if 'id' in request.GET:
                #         id = request.GET['id']
                #         eMateriaAsignadaPlanificacionSedeVirtualExamenes = eMateriaAsignadaPlanificacionSedeVirtualExamenes.filter(id=id)
                #
                #     if 's' in request.GET:
                #         search = request.GET['s'].strip()
                #         ss = search.split(' ')
                #         if len(ss) == 1:
                #             eMateriaAsignadaPlanificacionSedeVirtualExamenes = eMateriaAsignadaPlanificacionSedeVirtualExamenes.filter(Q(materiaasignada__matricula__inscripcion__persona__nombres__icontains=search) |
                #                                                                                                                        Q(materiaasignada__matricula__inscripcion__persona__apellido1__icontains=search) |
                #                                                                                                                        Q(materiaasignada__matricula__inscripcion__persona__apellido2__icontains=search) |
                #                                                                                                                        Q(materiaasignada__matricula__inscripcion__persona__cedula__icontains=search) |
                #                                                                                                                        Q(materiaasignada__matricula__inscripcion__persona__pasaporte__icontains=search) |
                #                                                                                                                        Q(materiaasignada__matricula__inscripcion__persona__usuario__username__icontains=search)).distinct().select_related('materiaasignada__matricula__inscripcion__persona')
                #         else:
                #             eMateriaAsignadaPlanificacionSedeVirtualExamenes = eMateriaAsignadaPlanificacionSedeVirtualExamenes.filter(Q(materiaasignada__matricula__inscripcion__persona__apellido1__icontains=ss[0]) &
                #                                                                                                                        Q(materiaasignada__matricula__inscripcion__persona__apellido2__icontains=ss[1])).distinct().select_related('materiaasignada__matricula__inscripcion__persona')
                #         url_vars += f'&s={search}'
                #     # eMateriaAsignadaPlanificacionSedeVirtualExamenSerializer = MateriaAsignadaPlanificacionSedeVirtualExamenSerializer(eMateriaAsignadaPlanificacionSedeVirtualExamenes, many=True).data if eMateriaAsignadaPlanificacionSedeVirtualExamenes.values("id").exists() else []
                #     paging = MiPaginador(eMateriaAsignadaPlanificacionSedeVirtualExamenes, 25)
                #     p = 1
                #     try:
                #         paginasesion = 1
                #         if 'paginador' in request.session:
                #             paginasesion = int(request.session['paginador'])
                #         if 'page' in request.GET:
                #             p = int(request.GET['page'])
                #         else:
                #             p = paginasesion
                #         try:
                #             page = paging.page(p)
                #         except:
                #             p = 1
                #         page = paging.page(p)
                #     except:
                #         page = paging.page(p)
                #     data['paging'] = paging
                #     data['rangospaging'] = paging.rangos_paginado(p)
                #     data['page'] = page
                #     data['search'] = search if search else ""
                #     data["url_params"] = url_vars
                #     data['eMateriaAsignadaPlanificacionSedeVirtualExamenes'] = page.object_list
                #     return render(request, "adm_horarios/examenes_sedes/aulaplanificacion/view.html", data)

                return render(request, "adm_horarios/disertaciones/panel.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return render(request, "adm_horarios/error.html", data)
