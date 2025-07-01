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
from inno.runBackGround import ReportPlanificacionSedes, ReportHorariosExamenesSedes
from sga.commonviews import adduserdata, traerNotificaciones
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

        return JsonResponse({"result": "bad", "message": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'resumensedes':
                try:
                    from sga.models import Coordinacion
                    data['title'] = u"Resumen de examenes en sedes"
                    return render(request, "adm_horarios/asistencia/resumen_sedes/view.html", data)
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'maintenancecampus':
                try:
                    data['title'] = u'Mantenimiento de sedes'
                    search = None
                    ids = None
                    url_vars = ''
                    eSedes = SedeVirtual.objects.filter(status=True)
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        eSedes = eSedes.filter(id=ids)
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        eSedes = eSedes.filter(Q(nombre__icontains=search)).distinct()
                        url_vars += '&s=' + search
                    paging = MiPaginador(eSedes, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data["url_params"] = url_vars
                    data['eSedes'] = page.object_list
                    return render(request, "adm_horarios/mantenimiento/sedes/view.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'searchPersonas':
                try:
                    q = request.GET['q'].upper().strip()
                    ePersonas = Persona.objects.filter(Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False))
                    search = q.strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        ePersonas = ePersonas.filter(Q(cedula__icontains=search) |
                                                     Q(pasaporte__icontains=search) |
                                                     Q(nombres__icontains=search) |
                                                     Q(apellido1__icontains=search) |
                                                     Q(apellido2__icontains=search))
                    else:
                        ePersonas = ePersonas.filter(Q(nombres__icontains=search) |
                                                     Q(apellido1__icontains=ss[0]) &
                                                     Q(apellido2__icontains=ss[1]))
                    ePersonas = ePersonas.distinct().order_by('apellido1', 'apellido2', 'nombres')[:15]
                    aData = {"results": [{"id": x.id, "name": "({}) - {}".format(x.documento(), x.nombre_completo())} for x in ePersonas]}
                    return JsonResponse({"result": True, 'mensaje': '', 'aData': aData})
                except Exception as ex:
                    return JsonResponse({"result": True, 'mensaje': f'{ex.__str__()}', 'aData': {"results": []}})

            return HttpResponseRedirect(request.path)
        else:
            try:
                if 'info' in request.GET:
                    data['info'] = request.GET['info']
                data['title'] = u'Administración de asistencias de examenes en sedes'
                data['ePeriodo'] = periodo
                data_json = {
                    'periodo_id': periodo.id,
                }
                eMatriculas = Matricula.objects.filter(status=True, retiradomatricula=False, inscripcion__modalidad_id__lte=3, nivel__periodo=periodo)
                # eMaterias = Materia.objects.filter(nivel__periodo=periodo, asignaturamalla__malla__modalidad_id__lte=3, status=True)
                # eNiveles = Nivel.objects.filter(periodo=periodo, materia__isnull=False, id__in=eMaterias.values_list('nivel_id', flat=True)).distinct()
                # eMatriculaSedeExamenes = MatriculaSedeExamen.objects.filter(status=True, matricula__status=True, matricula__retiradomatricula=False, matricula__nivel__in=eNiveles, matricula__inscripcion__modalidad_id=3, matricula__id__in=eMatriculas.values("id").distinct())
                eSedes = SedeVirtual.objects.filter(sedevirtualperiodoacademico__periodo=periodo, sedevirtualperiodoacademico__status=True, status=True,activa=True)
                data['eSedes'] = SedeVirtualSerializer(eSedes, many=True, context=data_json).data if eSedes.values("id").exists() else []
                if 'ids' in request.GET:
                    ids = int(encrypt(request.GET['ids']))
                    eSedeVirtual = SedeVirtual.objects.get(pk=ids)
                    data_json['isView_FechaPlanificacion'] = True
                    eSedeSerializer = SedeVirtualSerializer(eSedeVirtual, context=data_json).data
                    data['eSede'] = eSedeSerializer
                    data['cantidad_Asistencias'] = eSedeVirtual.get_asistencias(sede=eSedeVirtual, fecha=None, turno=None, aula=None,periodo=periodo)
                    return render(request, "adm_horarios/examenes_sedes/asistencia/sedevirtual/view.html", data)
                if 'idf' in request.GET:
                    idf = int(encrypt(request.GET['idf']))
                    eFechaPlanificacionSedeVirtualExamen = FechaPlanificacionSedeVirtualExamen.objects.get(pk=idf)
                    eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                    # data_json['isView_FechaPlanificacion'] = True
                    eSedeSerializer = SedeVirtualSerializer(eSedeVirtual, context={'periodo_id': periodo.id, 'isView_FechaPlanificacion': True}).data
                    eFechaPlanificacionSedeVirtualExamenSerializer = FechaPlanificacionSedeVirtualExamenSerializer(eFechaPlanificacionSedeVirtualExamen, context={'periodo_id': periodo.id, 'isView_HoraPlanificacion': True}).data
                    data['eSede'] = eSedeSerializer
                    data['eFechaPlanificacionSedeVirtualExamen'] = eFechaPlanificacionSedeVirtualExamenSerializer
                    return render(request, "adm_horarios/examenes_sedes/asistencia/fechaplanificacion/view.html", data)
                if 'idh' in request.GET:
                    idh = int(encrypt(request.GET['idh']))
                    eTurnoPlanificacionSedeVirtualExamen = TurnoPlanificacionSedeVirtualExamen.objects.get(pk=idh)
                    eFechaPlanificacionSedeVirtualExamen = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion
                    eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                    eSedeSerializer = SedeVirtualSerializer(eSedeVirtual, context={'periodo_id': periodo.id, 'isView_FechaPlanificacion': True, 'isView_HoraPlanificacion': True}).data
                    eFechaPlanificacionSedeVirtualExamenSerializer = FechaPlanificacionSedeVirtualExamenSerializer(eFechaPlanificacionSedeVirtualExamen, context=data_json).data
                    eTurnoPlanificacionSedeVirtualExamenSerializer = TurnoPlanificacionSedeVirtualExamenSerializer(eTurnoPlanificacionSedeVirtualExamen, context={'periodo_id': periodo.id, 'isView_AulaPlanificacion': True}).data
                    data['eSede'] = eSedeSerializer
                    data['eFechaPlanificacionSedeVirtualExamen'] = eFechaPlanificacionSedeVirtualExamenSerializer
                    data['eTurnoPlanificacionSedeVirtualExamen'] = eTurnoPlanificacionSedeVirtualExamenSerializer
                    return render(request, "adm_horarios/examenes_sedes/asistencia/horarioplanificacion/view.html", data)

                infoMatriculados = {'matriculados': len(eMatriculas.values_list("id", flat=True)),
                                    'asignados': 0,
                                    'x_asignar': len(eMatriculas.values_list("id", flat=True)) - 0}
                data['infoMatriculados'] = infoMatriculados
                return render(request, "adm_horarios/examenes_sedes/asistencia/panel.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return render(request, "adm_horarios/error.html", data)
