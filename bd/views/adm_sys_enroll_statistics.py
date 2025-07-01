# -*- coding: UTF-8 -*-
from django.contrib import messages
from django.contrib.admin.models import LogEntry, ADDITION, DELETION
from django.contrib.admin.utils import unquote
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction, router
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils.encoding import force_str

from bd.models import LogQuery, get_deleted_objects, LogEntryLogin
from decorators import secure_module
from bd.forms import *
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
import sys
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery, convertir_fecha, \
    resetear_clave, variable_valor, null_to_numeric
from sga.models import VariablesGlobales, Periodo, Matricula, Nivel, Modalidad
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    try:
        puede_realizar_accion(request, 'bd.puede_ver_periodo_academico_estadistica_matricula')
    except Exception as ex:
        return HttpResponseRedirect(f"/?info={ex.__str__()}")
    adduserdata(request, data)
    persona = request.session['persona']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'loadDataPregrado':
            try:
                if not 'id' in request.POST:
                    raise NameError("Parametro de periodo no encontrado")
                if not Periodo.objects.filter(pk=int(request.POST['id'])).exists():
                    raise NameError("Periodo no encontrado")
                ePeriodo = Periodo.objects.get(pk=int(request.POST['id']))
                if not PeriodoMatricula.objects.filter(periodo=ePeriodo).exists():
                    raise NameError("Periodo de matrícula no encontrado")
                ePeriodoMatricula = PeriodoMatricula.objects.get(periodo=ePeriodo)
                matriculas = Matricula.objects.filter(nivel__periodo=ePeriodo, status=True).exclude(inscripcion__coordinacion_id=9)
                aaData = {}
                aaData['total_matriculados'] = total_matriculados = matriculas.count()
                aaData['total_faci'] = total_faci = matriculas.filter(inscripcion__coordinacion_id__in=[4]).count()
                aaData['total_facsecyd'] = total_facsecyd = matriculas.filter(inscripcion__coordinacion_id__in=[3, 2]).count()
                aaData['total_face'] = total_face = matriculas.filter(inscripcion__coordinacion_id__in=[5]).count()
                aaData['total_facs'] = total_facs = matriculas.filter(inscripcion__coordinacion_id__in=[1]).count()
                coordinaciones = []
                coordinaciones.append({"nombre": "FACULTAD CIENCIAS E INGENIERÍA",
                                       "alias": "FACI",
                                       "total": total_faci})
                coordinaciones.append({"nombre": "FACULTAD CIENCIAS SOCIALES, EDUCACIÓN COMERCIAL Y DERECHO",
                                       "alias": "FACSECYD",
                                       "total": total_facsecyd})
                coordinaciones.append({"nombre": "FACULTAD EDUCACIÓN",
                                       "alias": "FACE",
                                       "total": total_face})
                coordinaciones.append({"nombre": "FACULTAD SALUD Y SERVICIOS SOCIALES",
                                       "alias": "FACS",
                                       "total": total_facs})
                return JsonResponse({"result": "ok", "data": aaData, "coordinaciones": coordinaciones})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        elif action == 'loadDataAdmision':
            try:
                if not 'id' in request.POST:
                    raise NameError("Parametro de periodo no encontrado")
                if not Periodo.objects.filter(pk=int(request.POST['id'])).exists():
                    raise NameError("Periodo no encontrado")
                ePeriodo = Periodo.objects.get(pk=int(request.POST['id']))
                if not PeriodoMatricula.objects.filter(periodo=ePeriodo).exists():
                    raise NameError("Periodo de matrícula no encontrado")
                ePeriodoMatricula = PeriodoMatricula.objects.get(periodo=ePeriodo)
                matriculas = Matricula.objects.filter(nivel__periodo=ePeriodo, status=True, inscripcion__coordinacion_id=9)
                aaData = {}
                aaData['total_matriculados'] = total_matriculados = matriculas.count()
                aaData['total_confirmados'] = total_confirmados = matriculas.filter(automatriculaadmision=True, termino=True).count()
                aaData['total_por_confirmar'] = total_por_confirmar = (total_matriculados - total_confirmados)
                try:
                    total_confirmados_por = round(null_to_numeric((total_confirmados * 100) / total_matriculados), 2)
                except ZeroDivisionError:
                    total_confirmados_por = 0

                try:
                    total_por_confirmar_por = round(null_to_numeric((total_por_confirmar * 100) / total_matriculados), 2)
                except ZeroDivisionError:
                    total_por_confirmar_por = 0
                aaData['total_confirmados_por'] = total_confirmados_por
                aaData['total_por_confirmar_por'] = total_por_confirmar_por
                aModalidades = []
                aCarreras = []
                count = 0
                for modalidad in Modalidad.objects.filter(pk__in=matriculas.values_list("inscripcion__modalidad_id", flat=True).distinct()):
                    for carrera in Carrera.objects.filter(pk__in=matriculas.values_list("inscripcion__carrera_id", flat=True).filter(inscripcion__modalidad=modalidad).distinct()):
                        count += 1
                        total_matriculados_c = matriculas.filter(inscripcion__modalidad=modalidad, inscripcion__carrera=carrera).count()
                        total_confirmados_c = matriculas.filter(inscripcion__modalidad=modalidad, inscripcion__carrera=carrera, automatriculaadmision=True, termino=True).count()
                        total_por_confirmar_c = (total_matriculados_c - total_confirmados_c)
                        try:
                            total_confirmados_c_p = round(null_to_numeric((total_confirmados_c * 100) / total_matriculados_c), 2)
                        except ZeroDivisionError:
                            total_confirmados_c_p = 0
                        try:
                            total_por_confirmar_c_p = round(null_to_numeric((total_por_confirmar_c * 100) / total_matriculados_c), 2)
                        except ZeroDivisionError:
                            total_por_confirmar_c_p = 0
                        aCarreras.append({"id": carrera.id,
                                          "nombre": carrera.nombre,
                                          "modalidad": modalidad.nombre,
                                          "total_matriculados": total_matriculados_c,
                                          "total_confirmados": total_confirmados_c,
                                          "total_por_confirmar": total_por_confirmar_c,
                                          "total_confirmados_p": total_confirmados_c_p,
                                          "total_por_confirmar_p": total_por_confirmar_c_p,
                                          "contador": count,
                                          })
                    total_matriculados_m = matriculas.filter(inscripcion__modalidad=modalidad).count()
                    total_confirmados_m = matriculas.filter(inscripcion__modalidad=modalidad, automatriculaadmision=True, termino=True).count()
                    total_por_confirmar_m = (total_matriculados_m - total_confirmados_m)
                    color = None
                    if modalidad.id == 1:
                        color = "rgba(255, 99, 132, 0.2)"
                    elif modalidad.id == 2:
                        color = "rgba(54, 162, 235, 0.2)"
                    elif modalidad.id == 3:
                        color = "rgba(255, 206, 86, 0.2)"
                    try:
                        total_confirmados_m_p = round(null_to_numeric((total_confirmados_m * 100) / total_matriculados_m), 2)
                    except ZeroDivisionError:
                        total_confirmados_m_p = 0
                    try:
                        total_por_confirmar_m_p = round(null_to_numeric((total_por_confirmar_m * 100) / total_matriculados_m), 2)
                    except ZeroDivisionError:
                        total_por_confirmar_m_p = 0
                    aModalidades.append({"id": modalidad.id,
                                         "nombre": modalidad.nombre,
                                         "total_matriculados": total_matriculados_m,
                                         "total_confirmados": total_confirmados_m,
                                         "total_por_confirmar": total_por_confirmar_m,
                                         "total_confirmados_p": total_confirmados_m_p,
                                         "total_por_confirmar_p": total_por_confirmar_m_p,
                                         "color": color
                                         })
                aChar = {}
                aChar['total_presencial'] = matriculas.filter(status=True, inscripcion__modalidad_id=1, automatriculaadmision=True, termino=True).count()
                aChar['total_semipresencial'] = matriculas.filter(status=True, inscripcion__modalidad_id=2, automatriculaadmision=True, termino=True).count()
                aChar['total_linea'] = matriculas.filter(status=True, inscripcion__modalidad_id=3, automatriculaadmision=True, termino=True).count()

                return JsonResponse({"result": "ok", "data": aaData, "aCarreras": aCarreras, "aModalidades": aModalidades, "aChar": aChar})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex.__str__(), "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = 'Estadísticas de Matrícula'
                if not 'id' in request.GET:
                    raise NameError("Parametro de periodo no encontrado")
                if not Periodo.objects.filter(pk=int(request.GET['id'])).exists():
                    raise NameError("Periodo no encontrado")
                ePeriodo = Periodo.objects.get(pk=int(request.GET['id']))
                if not PeriodoMatricula.objects.filter(periodo=ePeriodo).exists():
                    raise NameError("Periodo de matrícula no encontrado")
                ePeriodoMatricula = PeriodoMatricula.objects.get(periodo=ePeriodo)
                data['ePeriodoMatricula'] = ePeriodoMatricula
                if not 't' in request.GET:
                    if ePeriodoMatricula.tipo == '1': # ADMISION
                        return render(request, "adm_sistemas/academic_period/statistics_admision.html", data)
                    if ePeriodoMatricula.tipo == '2': # PREGRADO
                        return render(request, "adm_sistemas/academic_period/statistics_pregrado.html", data)
                    else: # POSGRADO
                        return render(request, "adm_sistemas/academic_period/statistics_pregrado.html", data)
                else:
                    t = request.GET.get('t', 0)
                    if t == 0:
                        raise NameError(u"No se encontro tipo")
                    elif t == '1': # ADMISION
                        return render(request, "adm_sistemas/academic_period/statistics_admision.html", data)
                    elif t == '2': # PREGRADO
                        return render(request, "adm_sistemas/academic_period/statistics_pregrado.html", data)
                    else: # POSGRADO
                        return render(request, "adm_sistemas/academic_period/statistics_pregrado.html", data)
            except Exception as ex:
                return HttpResponseRedirect("/adm_sistemas/academic_period?info=%s" % ex.__str__())
