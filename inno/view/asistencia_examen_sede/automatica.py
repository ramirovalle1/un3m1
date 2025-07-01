# -*- coding: latin-1 -*-
import json
import random

from django.contrib.auth.models import User
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
from inno.forms import AccesoExamenForm
from inno.funciones import generar_clave_aleatoria
from inno.models import MatriculaSedeExamen, FechaPlanificacionSedeVirtualExamen, TurnoPlanificacionSedeVirtualExamen, \
    AulaPlanificacionSedeVirtualExamen, MateriaAsignadaPlanificacionSedeVirtualExamen
from inno.runBackGround import ReportPlanificacionSedes, ReportHorariosExamenesSedes
from inno.serializers.AsistenciaExamen import MateriaAsignadaPlanificacionSedeVirtualExamenSerializer
from settings import DEBUG
from sga.commonviews import adduserdata, traerNotificaciones
from sga.funciones import log, puede_realizar_accion, MiPaginador, resetear_clave
from sga.models import Nivel, Materia, MateriaAsignada, SedeVirtual, LaboratorioVirtual, Notificacion, Persona, Malla, \
    Matricula, DetalleModeloEvaluativo, Inscripcion, Coordinacion
from sga.templatetags.sga_extras import encrypt
from Moodle_Funciones import buscarQuiz, accesoQuizIndividual, estadoQuizIndividual
import time


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
def view(request):
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    persona = request.session['persona']
    hoy = datetime.now().date()
    if request.method == 'POST':
        action = request.POST.get('action', None)
        if action is None:
            return JsonResponse({"result": False, "message": u"Acción no encontrada"})

        if action == 'validateCode':
            with transaction.atomic():
                try:
                    code = request.POST.get('code', None)
                    id = request.POST.get('id', None)
                    if code is None:
                        raise NameError(u"Código no encontrado, contactarse con el administrador del sistema.")
                    if id is None:
                        raise NameError(u"Turno no encontrado, contactarse con el administrador del sistema.")
                    try:
                        eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.get(codigo_qr=code)
                    except ObjectDoesNotExist:
                        raise NameError(u"Código inválido, acérquese a la mesa técnica.")
                    if not DEBUG:
                        if eMateriaAsignadaPlanificacionSedeVirtualExamen.asistencia:
                            fecha_asistencia = eMateriaAsignadaPlanificacionSedeVirtualExamen.fecha_asistencia
                            eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamenSerializer(eMateriaAsignadaPlanificacionSedeVirtualExamen).data
                            return JsonResponse({"result": False, "aData": {'eMateriaAsignadaPlanificacionSedeVirtualExamen': eMateriaAsignadaPlanificacionSedeVirtualExamen}, "message": f"Código QR fue utilizado el {fecha_asistencia.strftime('%Y-%m-%d %H:%M:%S')}."})
                    try:
                        eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamenSerializer(eMateriaAsignadaPlanificacionSedeVirtualExamen).data
                        return JsonResponse({"result": False, "aData": {'eMateriaAsignadaPlanificacionSedeVirtualExamen': eMateriaAsignadaPlanificacionSedeVirtualExamen}, "message": f"No se encontro turno valido, contactarse con el administrador del sistema."})
                    eTurnoPlanificacionSedeVirtualExamen = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion
                    if eMateriaAsignadaPlanificacionSedeVirtualExamen.aulaplanificacion.turnoplanificacion.fechaplanificacion.sede_id != eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion.sede_id:
                        eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamenSerializer(eMateriaAsignadaPlanificacionSedeVirtualExamen).data
                        return JsonResponse({"result": False, "aData": {'eMateriaAsignadaPlanificacionSedeVirtualExamen': eMateriaAsignadaPlanificacionSedeVirtualExamen}, "message": f"Su sede no corresponde a la ubicación actual, acérquese a la mesa técnica."})
                    if eMateriaAsignadaPlanificacionSedeVirtualExamen.aulaplanificacion.turnoplanificacion_id != eTurnoPlanificacionSedeVirtualExamen.pk:
                        eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamenSerializer(eMateriaAsignadaPlanificacionSedeVirtualExamen).data
                        return JsonResponse({"result": False, "aData": {'eMateriaAsignadaPlanificacionSedeVirtualExamen': eMateriaAsignadaPlanificacionSedeVirtualExamen}, "message": f"Aún no le corresponde ingresar, espere su fecha y hora que corresponde"})
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.asistencia = True
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.fecha_asistencia = datetime.now()
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request)
                    eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamenSerializer(eMateriaAsignadaPlanificacionSedeVirtualExamen).data
                    return JsonResponse({"result": True, "aData": {'eMateriaAsignadaPlanificacionSedeVirtualExamen': eMateriaAsignadaPlanificacionSedeVirtualExamen}, "message": f""})
                except Exception as ex:
                    transaction.set_rollback(True)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return JsonResponse({"result": False, "message": ex.__str__()})

        return JsonResponse({"result": False, "message": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'visor':
                try:
                    id = int(encrypt(request.GET.get('id', encrypt('0'))))
                    try:
                        eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro aula valido")
                    eTurnoPlanificacionSedeVirtualExamen = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion
                    data['eAulaPlanificacionSedeVirtualExamen'] = eAulaPlanificacionSedeVirtualExamen
                    data['eTurnoPlanificacionSedeVirtualExamen'] = eTurnoPlanificacionSedeVirtualExamen
                    data['title'] = u'Registro de asistencia automático (Visor)'
                    data['ruta'] = None
                    data['persona'] = None
                    data['periodo'] = None
                    return render(request, "adm_asistenciaexamensede/automatica/visor/view.html", data)
                except Exception as ex:
                    data['msg_error'] = ex.__str__()
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return render(request, "adm_asistenciaexamensede/error.html", data)

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Registro de asistencia automática de examenes en sede'
                data['ePeriodo'] = periodo
                # if persona.usuario.is_superuser:
                #     eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.filter(turnoplanificacion__fechaplanificacion__periodo=periodo, status=True)
                # else:
                #     eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.filter(Q(responsable=persona) | Q(turnoplanificacion__fechaplanificacion__supervisor=persona) | Q(supervisor=persona), turnoplanificacion__fechaplanificacion__periodo=periodo, status=True)
                eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.filter(turnoplanificacion__fechaplanificacion__periodo=periodo, status=True)
                data['eSedes'] = SedeVirtual.objects.filter(status=True, pk__in=eAulaPlanificacionSedeVirtualExamen.values_list('turnoplanificacion__fechaplanificacion__sede_id', flat=True))
                if 'ids' in request.GET:
                    ids = int(encrypt(request.GET['ids']))
                    data['eSede'] = eSedeVirtual = SedeVirtual.objects.get(pk=ids)
                    return render(request, "adm_asistenciaexamensede/automatica/sedevirtual/view.html", data)
                if 'idf' in request.GET:
                    idf = int(encrypt(request.GET['idf']))
                    data['eFechaPlanificacionSedeVirtualExamen'] = eFechaPlanificacionSedeVirtualExamen = FechaPlanificacionSedeVirtualExamen.objects.get(pk=idf)
                    data['eSede'] = eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                    return render(request, "adm_asistenciaexamensede/automatica/fechaplanificacion/view.html", data)
                if 'idh' in request.GET:
                    idh = int(encrypt(request.GET['idh']))
                    data['eTurnoPlanificacionSedeVirtualExamen'] = eTurnoPlanificacionSedeVirtualExamen = TurnoPlanificacionSedeVirtualExamen.objects.get(pk=idh)
                    data['eSede'] = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion.sede
                    data['eFechaPlanificacionSedeVirtualExamen'] = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion
                    return render(request, "adm_asistenciaexamensede/automatica/horarioplanificacion/view.html", data)
                if 'ida' in request.GET:
                    ida = int(encrypt(request.GET['ida']))
                    eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=ida)
                    data['eSede'] = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion.fechaplanificacion.sede
                    data['eFechaPlanificacionSedeVirtualExamen'] = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion.fechaplanificacion
                    data['eTurnoPlanificacionSedeVirtualExamen'] = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion
                    data['eAulaPlanificacionSedeVirtualExamen'] = eAulaPlanificacionSedeVirtualExamen
                    return render(request, "adm_asistenciaexamensede/automatica/aulaplanificacion/view.html", data)
                return render(request, "adm_asistenciaexamensede/automatica/panel.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return render(request, "adm_asistenciaexamensede/error.html", data)
