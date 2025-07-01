# -*- coding: latin-1 -*-
import json
import random

from django.contrib.auth.models import User
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
    AulaPlanificacionSedeVirtualExamen, MateriaAsignadaPlanificacionSedeVirtualExamen, SupervisorAulaPlanificacionSedeVirtualExamen
from inno.runBackGround import ReportPlanificacionSedes, ReportHorariosExamenesSedes
from settings import DEBUG
from sga.commonviews import adduserdata, traerNotificaciones
from sga.funciones import log, puede_realizar_accion, MiPaginador, resetear_clave, variable_valor
from sga.models import Nivel, Materia, MateriaAsignada, SedeVirtual, LaboratorioVirtual, Notificacion, Persona, Malla, \
    Matricula, DetalleModeloEvaluativo, Inscripcion, Coordinacion
from sga.templatetags.sga_extras import encrypt
from Moodle_Funciones import buscarQuiz, accesoQuizIndividual, estadoQuizIndividual
import time


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

        if action == 'registrarAsistenciaExamen':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el parametro de registro")
                idr = int(request.POST['id'])
                if not MateriaAsignadaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=idr):
                    raise NameError(u"No se encontro el registro")
                eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.get(pk=idr)
                idtestmoodle = 0
                eMateriaAsignadaPlanificacionSedeVirtualExamen.asistencia = True
                eMateriaAsignadaPlanificacionSedeVirtualExamen.fecha_asistencia = datetime.now()
                examenplanificado = eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada.materia.examenplanificadosilabo(eMateriaAsignadaPlanificacionSedeVirtualExamen.detallemodeloevaluativo)
                if examenplanificado:
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.idtestmoodle = int(examenplanificado.get('idtestmoodle'))
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.aviability = u"%s" % eMateriaAsignadaPlanificacionSedeVirtualExamen.generaraviability()
                eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request)
                log(u'Registra asistencia examen en sede: %s' % eMateriaAsignadaPlanificacionSedeVirtualExamen, request, 'edit')
                data['acceso_examen'] = variable_valor('ACCESO_EXAMEN')
                template_examen = get_template("adm_asistenciaexamensede/manual/detalleexamen.html")
                template_clave = get_template("adm_asistenciaexamensede/manual/detalleclave.html")
                template_asistencia = get_template("adm_asistenciaexamensede/manual/detalleasistencia.html")
                data['eMateriaAsignadaPlanificacionSedeVirtualExamen'] = eMateriaAsignadaPlanificacionSedeVirtualExamen
                aData = {
                    'fecha_asistencia': eMateriaAsignadaPlanificacionSedeVirtualExamen.fecha_asistencia.strftime('%d-%m-%Y %I:%M %p'),
                    'password': eMateriaAsignadaPlanificacionSedeVirtualExamen.password,
                    'persona': eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada.matricula.inscripcion.persona.nombre_completo(),
                    'contenedor_examen': template_examen.render(data),
                    'contenedor_clave': template_clave.render(data),
                    'contenedor_asistencia': template_asistencia.render(data)
                }
                return JsonResponse({"result": True, 'aData': aData})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'quitarAsistenciaExamen':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el parametro de registro")
                idr = int(request.POST['id'])
                if not MateriaAsignadaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=idr):
                    raise NameError(u"No se encontro el registro")
                eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.get(pk=idr)
                eMateriaAsignadaPlanificacionSedeVirtualExamen.asistencia = False
                eMateriaAsignadaPlanificacionSedeVirtualExamen.fecha_asistencia = None
                eMateriaAsignadaPlanificacionSedeVirtualExamen.idtestmoodle = None
                eMateriaAsignadaPlanificacionSedeVirtualExamen.aviability = None
                eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request)
                log(u'Se quita asistencia examen en sede: %s' % eMateriaAsignadaPlanificacionSedeVirtualExamen, request, 'edit')
                template_examen = get_template("adm_asistenciaexamensede/manual/detalleexamen.html")
                template_clave = get_template("adm_asistenciaexamensede/manual/detalleclave.html")
                template_asistencia = get_template("adm_asistenciaexamensede/manual/detalleasistencia.html")
                data['eMateriaAsignadaPlanificacionSedeVirtualExamen'] = eMateriaAsignadaPlanificacionSedeVirtualExamen
                aData = {
                    'contenedor_examen': template_examen.render(data),
                    'contenedor_clave': template_clave.render(data),
                    'contenedor_asistencia': template_asistencia.render(data)
                }
                return JsonResponse({"result": True, 'aData': aData})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'accesoExamenIndividual':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el parametro de registro")
                idr = int(request.POST['id'])
                if not MateriaAsignadaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=idr):
                    raise NameError(u"No se encontro el registro")
                if not 'idtestmoodle' in request.POST:
                    raise NameError(u"No existe examen en moodle configurado")
                form = AccesoExamenForm(request.POST)
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError(v[0])
                fecha = form.cleaned_data['fecha']
                horainicio = form.cleaned_data['horainicio']
                horafin = form.cleaned_data['horafin']
                password = form.cleaned_data['password']
                fechadesde = datetime(fecha.year, fecha.month, fecha.day, horainicio.hour, horainicio.minute, horainicio.second)
                fechadesde = int(time.mktime(fechadesde.timetuple()))
                fechahasta = datetime(fecha.year, fecha.month, fecha.day, horafin.hour, horafin.minute, horafin.second)
                fechahasta = int(time.mktime(fechahasta.timetuple()))
                eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.get(pk=idr)
                eMateriaAsignadaPlanificacionSedeVirtualExamen.idtestmoodle = int(request.POST['idtestmoodle'])
                eMateriaAsignadaPlanificacionSedeVirtualExamen.password = password
                eMateriaAsignadaPlanificacionSedeVirtualExamen.habilitadoexamen = True
                eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request, updatePassword=True)
                eMateriaAsignada = eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada
                if not DEBUG:
                    isResult, msgError = accesoQuizIndividual(eMateriaAsignada.matricula.inscripcion.persona.usuario.username,
                                                              eMateriaAsignada.materia,
                                                              eMateriaAsignadaPlanificacionSedeVirtualExamen.idtestmoodle,
                                                              {'timeopen': fechadesde,
                                                               'timeclose': fechahasta,
                                                               'timelimit': int(form.cleaned_data['limite']) * 60,
                                                               'password': eMateriaAsignadaPlanificacionSedeVirtualExamen.password,
                                                               'attempts': int(form.cleaned_data['intentos'])}
                                                              )
                    if not isResult:
                        raise NameError(msgError)
                log(u'Habilita examen en sede individual a: %s' % eMateriaAsignadaPlanificacionSedeVirtualExamen, request, 'edit')
                data['eMateriaAsignadaPlanificacionSedeVirtualExamen'] = eMateriaAsignadaPlanificacionSedeVirtualExamen
                template_1 = get_template("adm_asistenciaexamensede/manual/detalleexamen.html")
                template_2 = get_template("adm_asistenciaexamensede/manual/detalleclave.html")
                data['eMateriaAsignadaPlanificacionSedeVirtualExamen'] = eMateriaAsignadaPlanificacionSedeVirtualExamen
                aData = {
                    'id': eMateriaAsignadaPlanificacionSedeVirtualExamen.pk,
                    'contenedor_examen': template_1.render(data),
                    'contenedor_clave_examen': template_2.render(data)
                }
                return JsonResponse({"result": True, 'aData': aData})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'accesoExamenTodos':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro parametro")
                ida = int(request.POST['id'])
                if not AulaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=ida).exists():
                    raise NameError(u"No se encontro el aula de planificación")
                form = AccesoExamenForm(request.POST)
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError(v[0])
                fecha = form.cleaned_data['fecha']
                horainicio = form.cleaned_data['horainicio']
                horafin = form.cleaned_data['horafin']
                password = form.cleaned_data['password']
                fechadesde = datetime(fecha.year, fecha.month, fecha.day, horainicio.hour, horainicio.minute, horainicio.second)
                fechadesde = int(time.mktime(fechadesde.timetuple()))
                fechahasta = datetime(fecha.year, fecha.month, fecha.day, horafin.hour, horafin.minute, horafin.second)
                fechahasta = int(time.mktime(fechahasta.timetuple()))
                eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=ida)
                eAulaPlanificacionSedeVirtualExamen.password = password
                eAulaPlanificacionSedeVirtualExamen.registrohabilitacion = datetime.now()
                eAulaPlanificacionSedeVirtualExamen.save(request)
                if eAulaPlanificacionSedeVirtualExamen.password == '' or not eAulaPlanificacionSedeVirtualExamen.password:
                    raise NameError(u"Generar contraseña para hablitar el examen")
                eMateriaAsignadaPlanificacionSedeVirtualExamenes = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(aulaplanificacion=eAulaPlanificacionSedeVirtualExamen, aulaplanificacion__turnoplanificacion__fechaplanificacion__periodo=periodo, status=True)
                if not eMateriaAsignadaPlanificacionSedeVirtualExamenes.values("id").exists():
                    raise NameError(u"No existe alumno o alumnos con registro de asistencia")
                for eMateriaAsignadaPlanificacionSedeVirtualExamen in eMateriaAsignadaPlanificacionSedeVirtualExamenes:
                    # if not eMateriaAsignadaPlanificacionSedeVirtualExamen.habilitadoexamen:
                    eMateriaAsignada = eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada
                    username = eMateriaAsignada.matricula.inscripcion.persona.usuario.username
                    password = eMateriaAsignadaPlanificacionSedeVirtualExamen.password
                    if not eMateriaAsignadaPlanificacionSedeVirtualExamen.password:
                        eMateriaAsignadaPlanificacionSedeVirtualExamen.create_update_password()
                        password = eMateriaAsignadaPlanificacionSedeVirtualExamen.password
                    examenplanificado = eMateriaAsignada.materia.examenplanificadosilabo(eMateriaAsignadaPlanificacionSedeVirtualExamen.detallemodeloevaluativo)
                    if examenplanificado:
                        quiz = buscarQuiz(examenplanificado.get("idtestmoodle"), eMateriaAsignada.materia.coordinacion().id)
                        if quiz:
                            limite = int(quiz[3])
                            try:
                                intentos = form.cleaned_data['intentos']
                                if intentos == 0:
                                    intentos = examenplanificado.get('vecesintento')
                                    if intentos is None or intentos == 0:
                                        intentos = form.cleaned_data['intentos']
                            except Exception as exIn:
                                intentos = 1
                            estado_examen = estadoQuizIndividual(username, eMateriaAsignada.materia, examenplanificado.get("idtestmoodle"))
                            if estado_examen != 'inprogress':
                                eMateriaAsignadaPlanificacionSedeVirtualExamen.idtestmoodle = int(examenplanificado.get("idtestmoodle"))
                                eMateriaAsignadaPlanificacionSedeVirtualExamen.password = password
                                eMateriaAsignada = eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada
                                isResult, msgError = accesoQuizIndividual(eMateriaAsignada.matricula.inscripcion.persona.usuario.username,
                                                                          eMateriaAsignada.materia,
                                                                          eMateriaAsignadaPlanificacionSedeVirtualExamen.idtestmoodle,
                                                                          {'timeopen': fechadesde,
                                                                           'timeclose': fechahasta,
                                                                           'timelimit': limite,
                                                                           'password': eMateriaAsignadaPlanificacionSedeVirtualExamen.password,
                                                                           'attempts': intentos})
                                if isResult:
                                    eMateriaAsignadaPlanificacionSedeVirtualExamen.habilitadoexamen = True
                                    log(u'Habilita examen en sede individual a: %s' % eMateriaAsignadaPlanificacionSedeVirtualExamen, request, 'edit')
                                eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request)
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'generatePasswordAulaPlanificacion':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el parametro de registro aula planificación")
                if not 'edicion' in request.POST:
                    raise NameError(u"No se encontro el parametro de edición")
                if not AulaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=request.POST['id']):
                    raise NameError(u"No se encontro el registro aula planificación")
                eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=request.POST['id'])
                if request.POST['edicion'] == 'new':
                    eAulaPlanificacionSedeVirtualExamen.create_update_password()
                    eAulaPlanificacionSedeVirtualExamen.save(request)
                    password = eAulaPlanificacionSedeVirtualExamen.password
                    for eMateriaAsignadaPlanificacionSedeVirtualExamen in eAulaPlanificacionSedeVirtualExamen.materiaasignadaplanificadas():
                        eMateriaAsignadaPlanificacionSedeVirtualExamen.password = password
                        eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request)
                    log(u'Generó una contraseña al aula de planificación de examen virtual: %s' % eAulaPlanificacionSedeVirtualExamen, request, 'add')
                else:
                    password = generar_clave_aleatoria(10)
                    eAulaPlanificacionSedeVirtualExamen.password = password
                    eAulaPlanificacionSedeVirtualExamen.save(request)
                    for eMateriaAsignadaPlanificacionSedeVirtualExamen in eAulaPlanificacionSedeVirtualExamen.materiaasignadaplanificadas():
                        eMateriaAsignadaPlanificacionSedeVirtualExamen.password = password
                        eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request)
                    log(u'Se cambio la contraseña al aula de planificación de examen virtual: %s' % eAulaPlanificacionSedeVirtualExamen, request, 'edit')
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'generatePasswordMateriaAsignadaPlanificacion':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el parametro de registro materia asignada planificación")
                if not 'edicion' in request.POST:
                    raise NameError(u"No se encontro el parametro de edición")
                if not MateriaAsignadaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=request.POST['id']):
                    raise NameError(u"No se encontro el registro materia asignada planificación")
                eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.get(pk=request.POST['id'])
                if request.POST['edicion'] == 'new':
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.create_update_password()
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request)
                    log(u'Generó una contraseña a la materia asignada de planificación de examen virtual: %s' % eMateriaAsignadaPlanificacionSedeVirtualExamen, request, 'add')
                else:
                    password = generar_clave_aleatoria(10)
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.password = password
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request, updatePassword=True)
                    log(u'Se cambio la contraseña a la materia asignada de planificación de examen virtual: %s' % eMateriaAsignadaPlanificacionSedeVirtualExamen, request, 'edit')
                template = get_template("adm_asistenciaexamensede/manual/detalleclave.html")
                data['eMateriaAsignadaPlanificacionSedeVirtualExamen'] = eMateriaAsignadaPlanificacionSedeVirtualExamen
                aData = {
                    'id': eMateriaAsignadaPlanificacionSedeVirtualExamen.pk,
                    'contenedor_clave_examen': template.render(data)
                }
                return JsonResponse({"result": True, 'aData': aData})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'generatePasswordUser':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el parametro de persona")
                if not Persona.objects.values("id").filter(pk=request.POST['id']):
                    raise NameError(u"No se encontro la persona")
                ePersona = Persona.objects.get(pk=request.POST['id'])
                documento = ePersona.documento()
                if not documento:
                    documento = f"unemi*{datetime.now().year}"
                eUser = ePersona.usuario
                if not eUser:
                    raise NameError(u"No tiene asignado usuario activo")
                eUser.set_password(documento)
                eUser.save()
                ePersona.cambiar_clave()
                log(u'Reseteo clave de persona : %s' % ePersona, request, "add")
                return JsonResponse({"result": True, 'aData': {'clave': documento}})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'generateTokenAsistencia':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el parametro de persona")
                if not AulaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=request.POST['id']):
                    raise NameError(u"No se encontro la persona")
                eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=request.POST['id'])
                eAulaPlanificacionSedeVirtualExamen.token = eAulaPlanificacionSedeVirtualExamen.generate_token()
                eAulaPlanificacionSedeVirtualExamen.save(request)
                log(u'Se genero enlace de asistencia: %s' % eAulaPlanificacionSedeVirtualExamen, request, "add")
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'deleteAlumnoPlanificacion':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro parametro correcto")
                if not MateriaAsignadaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=request.POST['id']):
                    raise NameError(u"No se encontro la materia a eliminar")
                eMateriaAsignadaPlanificacionSedeVirtualExamen = eDelete = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.get(pk=request.POST['id'])
                if eMateriaAsignadaPlanificacionSedeVirtualExamen.habilitadoexamen:
                    raise NameError(f"Alumno {eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada.matricula.inscripcion.persona} tiene habilitado el examen, no puede eliminarlo")
                eDelete.delete()
                log(u'Elimino planificación de alumno: %s' % eMateriaAsignadaPlanificacionSedeVirtualExamen, request, "del")
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'addAlumnoPlanificacion':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el parametro de alumno")
                if not MateriaAsignada.objects.values("id").filter(pk=request.POST['id']):
                    raise NameError(u"No se encontro el alumno")
                if not 'ida' in request.POST:
                    raise NameError(u"No se encontro el parametro de persona")
                if not AulaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=request.POST['ida']):
                    raise NameError(u"No se encontro la persona")
                detallemodeloevaluativo_id = 0
                if periodo.es_pregrado():
                    detallemodeloevaluativo_id = 37
                elif periodo.es_admision():
                    detallemodeloevaluativo_id = 114
                eMateriaAsignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                eMatricula = eMateriaAsignada.matricula
                eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=request.POST['ida'])
                eMateriaAsignadaPlanificacionSedeVirtualExamenes = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(materiaasignada=eMateriaAsignada,
                                                                                                                                detallemodeloevaluativo_id=detallemodeloevaluativo_id)
                if eMateriaAsignadaPlanificacionSedeVirtualExamenes.values("id").exists():
                    raise NameError(f"Materia ({eMateriaAsignada.materia.asignatura.nombre}) de la persona {eMatricula.inscripcion.persona} ya se encuentra asignada")
                eTurnoPlanificacionSedeVirtualExamen = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion
                eFechaPlanificacionSedeVirtualExamen = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion
                horainicio = eTurnoPlanificacionSedeVirtualExamen.horainicio
                horafin = eTurnoPlanificacionSedeVirtualExamen.horafin
                fecha = eFechaPlanificacionSedeVirtualExamen.fecha
                filter_conflicto = (Q(aulaplanificacion__turnoplanificacion__horainicio__lte=horafin,
                                      aulaplanificacion__turnoplanificacion__horafin__gte=horafin,
                                      aulaplanificacion__turnoplanificacion__fechaplanificacion__fecha=fecha) |
                                    Q(aulaplanificacion__turnoplanificacion__horainicio__lte=horainicio,
                                      aulaplanificacion__turnoplanificacion__horafin__gte=horainicio,
                                      aulaplanificacion__turnoplanificacion__fechaplanificacion__fecha=fecha))
                eMateriaAsignadaPlanificacionSedeVirtualExamenes = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(Q(materiaasignada__matricula=eMatricula) |
                                                                                                                                Q(materiaasignada__matricula__inscripcion__persona=eMatricula.inscripcion.persona),
                                                                                                                                status=True,
                                                                                                                                aulaplanificacion__turnoplanificacion__fechaplanificacion__periodo=periodo,
                                                                                                                                detallemodeloevaluativo_id=detallemodeloevaluativo_id)
                eMateriaAsignadaPlanificacionSedeVirtualExamenes = eMateriaAsignadaPlanificacionSedeVirtualExamenes.filter(filter_conflicto)
                if eMateriaAsignadaPlanificacionSedeVirtualExamenes.values("id").exists():
                    raise NameError(f"Materia ({eMateriaAsignada.materia.asignatura.nombre}) de la persona {eMatricula.inscripcion.persona} tiene conflicto de horario")
                eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamen(aulaplanificacion=eAulaPlanificacionSedeVirtualExamen,
                                                                                                               materiaasignada=eMateriaAsignada,
                                                                                                               detallemodeloevaluativo_id=detallemodeloevaluativo_id)
                eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request)
                log(u'Se adiciono persona (%s) en la planificación: %s' % (eMatricula.inscripcion.persona, eAulaPlanificacionSedeVirtualExamen), request, "add")
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'loadAuditoriaAccesoMoodle':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el parametro de alumno")
                if not MateriaAsignadaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=request.POST['id']):
                    raise NameError(u"No se encontro el alumno")
                eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.get(pk=request.POST['id'])
                template = get_template("adm_asistenciaexamensede/manual/auditoria_examen.html")
                data['eMateriaAsignadaPlanificacionSedeVirtualExamen'] = eMateriaAsignadaPlanificacionSedeVirtualExamen
                aData = {
                    'html': template.render(data)
                }
                return JsonResponse({"result": True, 'aData': aData})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'saveUrlVideo':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el parametro de registro aula planificación")
                if not 'url' in request.POST or request.POST['url'] == '':
                    raise NameError(u"No igresó una url valida")
                if not AulaPlanificacionSedeVirtualExamen.objects.values("id").filter(pk=request.POST['id']):
                    raise NameError(u"No se encontro el registro aula planificación")
                eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=request.POST['id'])
                eAulaPlanificacionSedeVirtualExamen.url_video = request.POST['url']
                eAulaPlanificacionSedeVirtualExamen.save(request)
                log(u'Ingresó una grabacion de examen virtual: %s' % eAulaPlanificacionSedeVirtualExamen, request, 'add')
                return JsonResponse({"result": True, 'message': 'Se agregó la url correctamente'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})
        elif action == 'editUrlVideo':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"No se encontro el parametro de registro aula planificación")
                if not 'url' in request.POST or request.POST['url'] == '':
                    raise NameError(u"No igresó una url valida")
                eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.filter(pk=request.POST['id']).first()
                if not eAulaPlanificacionSedeVirtualExamen:
                    raise NameError(u"No se encontro el registro aula planificación")
                eAulaPlanificacionSedeVirtualExamen.url_video = request.POST['url']
                eAulaPlanificacionSedeVirtualExamen.save(request, update_fields=['url_video'])
                log(u'Ingresó una grabacion de examen virtual: %s' % eAulaPlanificacionSedeVirtualExamen, request, 'edit')
                return JsonResponse({"result": True, 'message': 'Se editó la url correctamente'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'message': str(ex)})


        return JsonResponse({"result": "bad", "message": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'loadFormAccesoExamenIndividual':
                try:
                    id=0
                    if 'id' in request.GET:
                        id = int(request.GET['id'])
                    eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.get(pk=id)
                    materiaasignada = eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada
                    username = materiaasignada.matricula.inscripcion.persona.usuario.username
                    password = eMateriaAsignadaPlanificacionSedeVirtualExamen.password
                    if not eMateriaAsignadaPlanificacionSedeVirtualExamen.password:
                        eMateriaAsignadaPlanificacionSedeVirtualExamen.create_update_password()
                        password = eMateriaAsignadaPlanificacionSedeVirtualExamen.password
                    examenplanificado = materiaasignada.materia.examenplanificadosilabo(eMateriaAsignadaPlanificacionSedeVirtualExamen.detallemodeloevaluativo)
                    if not examenplanificado:
                        raise NameError("No existe planificación de examen")

                    quiz = buscarQuiz(examenplanificado.get("idtestmoodle"), materiaasignada.materia.coordinacion().id)
                    limite = int(int(quiz[3]) / 60 if quiz else 60)
                    try:
                        intentos = int(quiz[4])
                        if intentos == 0:
                            intentos = examenplanificado.get('vecesintento')
                            if intentos is None or intentos == 0:
                                intentos = 1
                    except Exception as exIn:
                        intentos = 1
                    estado_examen = estadoQuizIndividual(username, materiaasignada.materia, examenplanificado.get("idtestmoodle"))
                    data['estado_examen'] = estado_examen
                    turno = eMateriaAsignadaPlanificacionSedeVirtualExamen.aulaplanificacion.turnoplanificacion
                    form = AccesoExamenForm(initial={'fecha': turno.fechaplanificacion.fecha,
                                                     'horainicio': turno.horainicio,
                                                     'horafin': turno.horafin,
                                                     'limite': limite,
                                                     'password': password,
                                                     'intentos': intentos})
                    data['form'] = form
                    data['id'] = id
                    data['idtestmoodle'] = examenplanificado.get("idtestmoodle")
                    template = get_template("adm_asistenciaexamensede/manual/formAccesoExamenIndividual.html")
                    return JsonResponse({"result": True, 'html': template.render(data), 'estado_examen': estado_examen})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'loadFormAccesoExamenTodos':
                try:
                    id=0
                    if 'id' in request.GET:
                        id = int(request.GET['id'])
                    eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=id)
                    password = eAulaPlanificacionSedeVirtualExamen.password
                    if not eAulaPlanificacionSedeVirtualExamen.password:
                        eAulaPlanificacionSedeVirtualExamen.create_update_password()
                        password = eAulaPlanificacionSedeVirtualExamen.password
                    turno = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion
                    form = AccesoExamenForm(initial={'fecha': turno.fechaplanificacion.fecha,
                                                     'horainicio': turno.horainicio,
                                                     'horafin': turno.horafin,
                                                     'limite': 60,
                                                     'password': password,
                                                     'intentos': 1})
                    data['form'] = form
                    data['id'] = id
                    template = get_template("adm_asistenciaexamensede/manual/formAccesoExamenTodos.html")
                    return JsonResponse({"result": True, 'html': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'listAlumno':
                try:
                    id = 0
                    if 'id' in request.GET:
                        id = int(request.GET['id'])
                    eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=id)
                    eTurnoPlanificacionSedeVirtualExamen = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion
                    eFechaPlanificacionSedeVirtualExamen = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion
                    eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                    ePeriodo = eFechaPlanificacionSedeVirtualExamen.periodo
                    detallemodeloevaluativo_id = 0
                    if periodo.es_pregrado():
                        detallemodeloevaluativo_id = 37
                    elif periodo.es_admision():
                        detallemodeloevaluativo_id = 114
                    if detallemodeloevaluativo_id == 0:
                        raise NameError(u"No se encontro modelo evaluativo")
                    cursor = connections['sga_select'].cursor()
                    # eMallasIngles = Malla.objects.filter(pk__in=[353, 22]).values_list('id', flat=True)
                    eMatriculaSedeExamenes = MatriculaSedeExamen.objects.filter(sede=eSedeVirtual,
                                                                                detallemodeloevaluativo_id=detallemodeloevaluativo_id,
                                                                                status=True, matricula__status=True,
                                                                                matricula__retiradomatricula=False,
                                                                                matricula__nivel__periodo=ePeriodo).distinct()
                    eMatriculas = Matricula.objects.filter(pk__in=eMatriculaSedeExamenes.values_list("matricula__id", flat=True), status=True, retiradomatricula=False, bloqueomatricula=False, nivel__periodo=ePeriodo)
                    sql = f"""SELECT 
                                    "sga_matricula"."id", 
                                    COUNT("sga_materia"."asignaturamalla_id") 
                                            FILTER (WHERE ("sga_asignaturamalla"."malla_id" NOT IN (SELECT U0."id"
                                                                                                        FROM "sga_malla" U0
                                                                                                        WHERE U0."id" IN (353, 22)
                                                                                                    ) AND 
                                                            "sga_nivel"."periodo_id" = {ePeriodo.pk} AND 
                                                            "sga_matricula"."status" AND 
                                                            "sga_materia"."asignatura_id" NOT IN (4837)
                                                            )
                                                    ) AS "total_general", 
                                    COUNT("sga_materia"."asignaturamalla_id") 
                                            FILTER (WHERE ("sga_materiaasignada"."id" IN (	SELECT U0."materiaasignada_id"
                                                                                                FROM "inno_materiaasignadaplanificacionsedevirtualexamen" U0
                                                                                                INNER JOIN "sga_materiaasignada" U1 ON U1."id" = U0.materiaasignada_id
                                                                                                WHERE U1."matricula_id" = "sga_matricula"."id"
                                                                                            ) AND
                                                            "sga_nivel"."periodo_id" = {ePeriodo.pk} AND 
                                                            "sga_matricula"."status" AND 
                                                            "sga_materia"."asignatura_id" NOT IN (4837))
                                                    ) AS "total_planificadas"
                                FROM "sga_matricula"
                                INNER JOIN "sga_inscripcion" ON "sga_matricula"."inscripcion_id" = "sga_inscripcion"."id"
                                INNER JOIN "sga_inscripcionmalla" ON "sga_inscripcion"."id" = "sga_inscripcionmalla"."inscripcion_id"
                                INNER JOIN "sga_nivel" ON "sga_matricula"."nivel_id" = "sga_nivel"."id"
                                INNER JOIN "sga_periodo" ON "sga_nivel"."periodo_id" = "sga_periodo"."id"
                                LEFT OUTER JOIN "sga_materiaasignada" ON "sga_matricula"."id" = "sga_materiaasignada"."matricula_id"
                                LEFT OUTER JOIN "sga_materia" ON "sga_materiaasignada"."materia_id" = "sga_materia"."id"
                                LEFT OUTER JOIN "sga_asignaturamalla" ON "sga_materia"."asignaturamalla_id" = "sga_asignaturamalla"."id"
                                WHERE (
                                    NOT "sga_matricula"."bloqueomatricula" AND 
                                    "sga_nivel"."periodo_id" = {ePeriodo.pk} AND 
                                    "sga_matricula"."id" IN (
                                                                        SELECT DISTINCT 
                                                                            U0."matricula_id"
                                                                        FROM "inno_matriculasedeexamen" U0
                                                                            INNER JOIN "sga_matricula" U2 ON U0."matricula_id" = U2."id"
                                                                            INNER JOIN "sga_nivel" U3 ON U2."nivel_id" = U3."id"
                                                                        WHERE (
                                                                                    U0."detallemodeloevaluativo_id" = {detallemodeloevaluativo_id} AND 
                                                                                    U3."periodo_id" = {ePeriodo.pk} AND 
                                                                                    NOT U2."retiradomatricula" AND 
                                                                                    U2."status" AND 
                                                                                    U0."sede_id" = {eSedeVirtual.pk} AND 
                                                                                    U0."status"
                                                                                )
                                                                    ) AND 
                                    NOT "sga_matricula"."retiradomatricula" AND 
                                    "sga_matricula"."status"
                                    )
                                GROUP BY "sga_matricula"."id"
                                HAVING 
                                        COUNT("sga_materia"."asignaturamalla_id") 
                                            FILTER (WHERE ("sga_asignaturamalla"."malla_id" NOT IN (SELECT U0."id"
                                                                                                        FROM "sga_malla" U0
                                                                                                        WHERE U0."id" IN (353, 22)
                                                                                                    ) AND 
                                                            "sga_nivel"."periodo_id" = {ePeriodo.pk} AND 
                                                            "sga_matricula"."status" AND 
                                                            "sga_materia"."asignatura_id" NOT IN (4837)
                                                            )
                                                    ) 
                                        <> 
                                        COUNT("sga_materia"."asignaturamalla_id") 
                                            FILTER (WHERE ("sga_materiaasignada"."id" IN (SELECT U0."materiaasignada_id"
                                                                                            FROM "inno_materiaasignadaplanificacionsedevirtualexamen" U0
                                                                                            INNER JOIN "sga_materiaasignada" U1 ON U1."id" = U0.materiaasignada_id
                                                                                            WHERE U1."matricula_id" = "sga_matricula"."id"
                                                                                        ) AND
                                                            "sga_nivel"."periodo_id" = {ePeriodo.pk} AND 
                                                            "sga_matricula"."status" AND 
                                                            "sga_materia"."asignatura_id" NOT IN (4837))
                                                    )"""
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    ids_matricula = [r[0] for r in results]
                    eMatriculas = eMatriculas.filter(pk__in=ids_matricula)
                    search = None
                    url_vars = ''
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            eMatriculas = eMatriculas.filter(Q(inscripcion__persona__nombres__icontains=search) |
                                                             Q(inscripcion__persona__apellido1__icontains=search) |
                                                             Q(inscripcion__persona__apellido2__icontains=search) |
                                                             Q(inscripcion__persona__cedula__icontains=search) |
                                                             Q(inscripcion__persona__pasaporte__icontains=search) |
                                                             Q(inscripcion__persona__usuario__username__icontains=search)).distinct().select_related('inscripcion__persona')
                        else:
                            eMatriculas = eMatriculas.filter(Q(inscripcion__persona__apellido1__icontains=ss[0]) &
                                                             Q(inscripcion__persona__apellido2__icontains=ss[1])).distinct().select_related('inscripcion__persona')
                        url_vars += f'&s={search}'
                    eMatriculas = eMatriculas.order_by('inscripcion__inscripcionnivel__nivel__orden',
                                                       'inscripcion__persona__apellido1',
                                                       'inscripcion__persona__apellido2',
                                                       'inscripcion__persona__nombres').distinct()

                    paging = MiPaginador(eMatriculas, 50)
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
                    data["url_params"] = url_vars
                    data['eAulaPlanificacionSedeVirtualExamen'] = eAulaPlanificacionSedeVirtualExamen
                    data['eMatriculas'] = page.object_list
                    data['ePeriodo'] = periodo
                    data['eDetalleModeloEvaluativo'] = DetalleModeloEvaluativo.objects.get(pk=detallemodeloevaluativo_id)
                    data['eSedeVirtual'] = eSedeVirtual
                    template = get_template("adm_asistenciaexamensede/manual/listadoAlumno.html")
                    aData = {
                        'html': template.render(data)
                    }
                    return JsonResponse({"result": True, 'aData': aData})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'searchHorarioAlumno':
                try:
                    eMatriculas = Matricula.objects.filter(status=True, nivel__periodo=periodo, retiradomatricula=False)
                    eInscripciones = Inscripcion.objects.filter(pk__in=eMatriculas.values_list('inscripcion__id', flat=True))
                    search = None
                    url_vars = ''
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            eInscripciones = eInscripciones.filter(Q(persona__nombres__icontains=search) |
                                                                   Q(persona__apellido1__icontains=search) |
                                                                   Q(persona__apellido2__icontains=search) |
                                                                   Q(persona__cedula__icontains=search) |
                                                                   Q(persona__pasaporte__icontains=search) |
                                                                   Q(persona__usuario__username__icontains=search)).distinct().select_related('persona')
                        else:
                            eInscripciones = eInscripciones.filter(Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1])).distinct().select_related('persona')
                        url_vars += f'&s={search}'
                    eInscripciones = eInscripciones.order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres').distinct()
                    paging = MiPaginador(eInscripciones, 25)
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
                    data["url_params"] = url_vars
                    data['eInscripciones'] = page.object_list
                    template = get_template("adm_asistenciaexamensede/manual/searchHorarioAlumno.html")
                    aData = {
                        'html': template.render(data)
                    }
                    return JsonResponse({"result": True, 'aData': aData})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            elif action == 'reportPlanificacionSedes':
                try:
                    if data['permiteWebPush']:
                        data['isFilter'] = True
                        eNotificacion = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                                     titulo=f'Excel Planificación de sedes {periodo.get_clasificacion_display() if periodo.clasificacion else ""}'.strip(),
                                                     destinatario=persona,
                                                     url='',
                                                     prioridad=1,
                                                     app_label='SGA',
                                                     fecha_hora_visible=datetime.now() + timedelta(days=1),
                                                     tipo=2,
                                                     en_proceso=True)
                        eNotificacion.save(request)
                        ReportPlanificacionSedes(request=request, data=data, eNotificacion=eNotificacion).start()
                        return JsonResponse({"result": True,
                                             "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                             "btn_notificaciones": traerNotificaciones(request, data, persona)})
                    else:
                        __author__ = 'Unemi'
                        title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                        titulo2 = easyxf('font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                        font_style = XFStyle()
                        font_style.font.bold = True
                        font_style2 = XFStyle()
                        font_style2.font.bold = False
                        wb = Workbook(encoding='utf-8')
                        ws = wb.add_sheet('hoja1')
                        ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                        ws.write_merge(1, 1, 0, 9, 'REPORTE DE PLANIFICACIÓN DE SEDES', titulo2)
                        response = HttpResponse(content_type="application/ms-excel")
                        response['Content-Disposition'] = 'attachment; filename=reporte_planificación_sedes' + random.randint(1, 10000).__str__() + '.xls'
                        columns = [
                            (u"#", 1000),
                            (u"SEDE", 10000),
                            (u"FECHA", 6000),
                            (u"HORA INICIO", 6000),
                            (u"HORA FIN", 6000),
                            (u"SALA/LABORATORIO", 6000),
                            (u"CAPACIDAD", 6000),
                            (u"PLANIFICADOS", 6000),
                            (u"SUPERVISOR", 6000),
                            (u"APLICADOR", 6000),
                        ]
                        row_num = 3
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        ePeriodo = periodo
                        eMaterias = Materia.objects.filter(nivel__periodo=ePeriodo, status=True).exclude(asignatura_id=4837)
                        eNiveles = Nivel.objects.filter(status=True, periodo=periodo, materia__isnull=False, id__in=eMaterias.values_list('nivel_id', flat=True)).distinct()
                        eMatriculaSedeExamenes = MatriculaSedeExamen.objects.filter(status=True, matricula__status=True, matricula__retiradomatricula=False, matricula__nivel__in=eNiveles)
                        eSedes = SedeVirtual.objects.filter(pk__in=eMatriculaSedeExamenes.values_list('sede_id', flat=True))
                        eAulaPlanificacionSedeVirtualExamenes = AulaPlanificacionSedeVirtualExamen.objects.filter(status=True,
                                                                                                                  turnoplanificacion__fechaplanificacion__periodo=ePeriodo,
                                                                                                                  turnoplanificacion__fechaplanificacion__sede__in=eSedes)
                        row_num = 4
                        i = 0
                        for eAulaPlanificacionSedeVirtualExamen in eAulaPlanificacionSedeVirtualExamenes:
                            i += 1
                            eLaboratorioVirtual = eAulaPlanificacionSedeVirtualExamen.aula
                            eAplicador = eAulaPlanificacionSedeVirtualExamen.responsable
                            eTurnoPlanificacionSedeVirtualExamen = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion
                            eFechaPlanificacionSedeVirtualExamen = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion
                            eSupervisor = eFechaPlanificacionSedeVirtualExamen.supervisor
                            eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                            ws.write(row_num, 0, str(i), font_style2)
                            ws.write(row_num, 1, eSedeVirtual.nombre, font_style2)
                            ws.write(row_num, 2, eFechaPlanificacionSedeVirtualExamen.fecha.__str__(), font_style2)
                            ws.write(row_num, 3, eTurnoPlanificacionSedeVirtualExamen.horainicio.__str__(), font_style2)
                            ws.write(row_num, 4, eTurnoPlanificacionSedeVirtualExamen.horafin.__str__(), font_style2)
                            ws.write(row_num, 5, eLaboratorioVirtual.nombre, font_style2)
                            ws.write(row_num, 6, str(eLaboratorioVirtual.capacidad), font_style2)
                            ws.write(row_num, 7, str(eAulaPlanificacionSedeVirtualExamen.cantidadad_planificadas()), font_style2)
                            ws.write(row_num, 8, eSupervisor.nombre_completo() if eSupervisor else '', font_style2)
                            ws.write(row_num, 9, eAplicador.nombre_completo() if eAplicador else '', font_style2)
                            row_num += 1
                        wb.save(response)
                        return response
                except Exception as ex:
                    if data['permiteWebPush']:
                        return JsonResponse({"result": False, "mensaje": f"Error al generar reporte, {ex.__str__()}"})
                    else:
                        HttpResponseRedirect(f"{request.path}?info=Error al generar reporte, {ex.__str__()}")

            elif action == 'reportAlumnoHorarios':
                try:
                    if data['permiteWebPush']:
                        data['isFilter'] = True
                        eNotificacion = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                                     titulo=f'Excel Horario de examenes en sedes {periodo.get_clasificacion_display() if periodo.clasificacion else ""}'.strip(),
                                                     destinatario=persona,
                                                     url='',
                                                     prioridad=1,
                                                     app_label='SGA',
                                                     fecha_hora_visible=datetime.now() + timedelta(days=1),
                                                     tipo=2,
                                                     en_proceso=True)
                        eNotificacion.save(request)
                        ReportHorariosExamenesSedes(request=request, data=data, eNotificacion=eNotificacion).start()
                        return JsonResponse({"result": True,
                                             "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                             "btn_notificaciones": traerNotificaciones(request, data, persona)})
                    else:
                        __author__ = 'Unemi'
                        title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                        titulo2 = easyxf('font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                        font_style = XFStyle()
                        font_style.font.bold = True
                        font_style2 = XFStyle()
                        font_style2.font.bold = False
                        wb = Workbook(encoding='utf-8')
                        ws = wb.add_sheet('hoja1')
                        ws.write_merge(0, 0, 0, 15, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                        ws.write_merge(1, 1, 0, 15, 'REPORTE DE HORARIOS DE EXAMENES DE ALUMNOS EN SEDES', titulo2)
                        response = HttpResponse(content_type="application/ms-excel")
                        response['Content-Disposition'] = 'attachment; filename=reporte_horarios_examenes_sedes' + random.randint(1, 10000).__str__() + '.xls'
                        columns = [
                            (u"#", 1000),
                            (u"TIPO DOCUMENTO", 10000),
                            (u"DOCUMENTO", 10000),
                            (u"ALUMNO", 10000),
                            (u"CARRERA", 10000),
                            (u"MODALIDAD", 10000),
                            (u"NIVEL", 10000),
                            (u"ASIGNATURA", 10000),
                            (u"SEDE", 10000),
                            (u"FECHA", 6000),
                            (u"HORA INICIO", 6000),
                            (u"HORA FIN", 6000),
                            (u"SALA/LABORATORIO", 6000),
                            (u"SUPERVISOR", 6000),
                            (u"APLICADOR", 6000),
                            (u"NUM. PLANIFICACIÓN", 6000),
                        ]
                        row_num = 3
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        ePeriodo = periodo
                        eMaterias = Materia.objects.filter(nivel__periodo=ePeriodo, status=True).exclude(asignatura_id=4837)
                        eMateriaAsignadas = MateriaAsignada.objects.filter(materia__in=eMaterias, matricula__status=True, matricula__bloqueomatricula=False, retiramateria=False, status=True).order_by('matricula__inscripcion__persona__apellido1','matricula__inscripcion__persona__apellido2', 'matricula__inscripcion__persona__nombres').distinct()
                        row_num = 4
                        i = 0
                        for eMateriaAsignada in eMateriaAsignadas:
                            i += 1
                            eMateriaAsignadaPlanificacionSedeVirtualExamenes = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(materiaasignada=eMateriaAsignada)
                            eMateria = eMateriaAsignada.materia
                            eAsignaturaMalla = eMateria.asignaturamalla
                            eNivelMalla = eAsignaturaMalla.nivelmalla
                            eAsignatura = eAsignaturaMalla.asignatura
                            eMatricula = eMateriaAsignada.matricula
                            eInscripcion = eMatricula.inscripcion
                            eModalidad = eInscripcion.modalidad
                            eCarrera = eInscripcion.carrera
                            ePersona = eInscripcion.persona
                            eLaboratorioVirtual = None
                            eAplicador = None
                            eSupervisor = None
                            eTurnoPlanificacionSedeVirtualExamen = None
                            eFechaPlanificacionSedeVirtualExamen = None
                            eSedeVirtual = None
                            if eMateriaAsignadaPlanificacionSedeVirtualExamenes.values("id").exists():
                                eMateriaAsignadaPlanificacionSedeVirtualExamen = eMateriaAsignadaPlanificacionSedeVirtualExamenes.first()
                                eAulaPlanificacionSedeVirtualExamen = eMateriaAsignadaPlanificacionSedeVirtualExamen.aulaplanificacion
                                eLaboratorioVirtual = eAulaPlanificacionSedeVirtualExamen.aula
                                eAplicador = eAulaPlanificacionSedeVirtualExamen.responsable
                                eTurnoPlanificacionSedeVirtualExamen = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion
                                eFechaPlanificacionSedeVirtualExamen = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion
                                eSupervisor = eFechaPlanificacionSedeVirtualExamen.supervisor
                                eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                            if not eSedeVirtual:
                                eMatriculaSedeExamenes = MatriculaSedeExamen.objects.filter(matricula=eMateriaAsignada.matricula, status=True)
                                if eMatriculaSedeExamenes.values("id").exists():
                                    eMatriculaSedeExamen = eMatriculaSedeExamenes.first()
                                    eSedeVirtual = eMatriculaSedeExamen.sede
                            ws.write(row_num, 0, str(i), font_style2)
                            ws.write(row_num, 1, ePersona.tipo_documento(), font_style2)
                            ws.write(row_num, 2, ePersona.documento(), font_style2)
                            ws.write(row_num, 3, ePersona.nombre_completo(), font_style2)
                            ws.write(row_num, 4, eCarrera.nombrevisualizar if eCarrera.nombrevisualizar else eCarrera.nombre, font_style2)
                            ws.write(row_num, 5, eModalidad.nombre if eModalidad else '', font_style2)
                            ws.write(row_num, 6, eNivelMalla.nombre, font_style2)
                            ws.write(row_num, 7, eAsignatura.nombre, font_style2)
                            ws.write(row_num, 8, eSedeVirtual.nombre if eSedeVirtual else '', font_style2)
                            ws.write(row_num, 9, eFechaPlanificacionSedeVirtualExamen.fecha.__str__() if eFechaPlanificacionSedeVirtualExamen else '', font_style2)
                            ws.write(row_num, 10, eTurnoPlanificacionSedeVirtualExamen.horainicio.__str__() if eTurnoPlanificacionSedeVirtualExamen else '', font_style2)
                            ws.write(row_num, 11, eTurnoPlanificacionSedeVirtualExamen.horafin.__str__() if eTurnoPlanificacionSedeVirtualExamen else '', font_style2)
                            ws.write(row_num, 12, eLaboratorioVirtual.nombre if eLaboratorioVirtual else '', font_style2)
                            ws.write(row_num, 13, eSupervisor.nombre_completo() if eSupervisor else '', font_style2)
                            ws.write(row_num, 14, eAplicador.nombre_completo() if eAplicador else '', font_style2)
                            ws.write(row_num, 15, len(eMateriaAsignadaPlanificacionSedeVirtualExamenes.values("id")), font_style2)
                            row_num += 1
                        wb.save(response)
                        return response
                except Exception as ex:
                    if data['permiteWebPush']:
                        return JsonResponse({"result": False, "mensaje": f"Error al generar reporte, {ex.__str__()}"})
                    else:
                        HttpResponseRedirect(f"{request.path}?info=Error al generar reporte, {ex.__str__()}")

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Registro de asistencia manual de examenes en sede'
                data['ePeriodo'] = periodo
                if persona.usuario.is_superuser:
                    eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.filter(turnoplanificacion__fechaplanificacion__periodo=periodo, status=True)
                else:
                    idsindividual = AulaPlanificacionSedeVirtualExamen.objects.filter(Q(responsable=persona) | Q(turnoplanificacion__fechaplanificacion__supervisor=persona) | Q(supervisor=persona),
                                                                                                            turnoplanificacion__fechaplanificacion__periodo=periodo,
                                                                                                            status=True).distinct().values_list('id', flat=True)
                    idsgrupal = SupervisorAulaPlanificacionSedeVirtualExamen.objects.filter(Q(responsable=persona) | Q(supervisor=persona), status=True).distinct().values_list('aulaplanificacion_id', flat=True)

                    eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.filter(Q(id__in=idsindividual) | Q(id__in=idsgrupal))
                data['eSedes'] = SedeVirtual.objects.filter(status=True, pk__in=eAulaPlanificacionSedeVirtualExamen.values_list('turnoplanificacion__fechaplanificacion__sede_id', flat=True))
                if 'ids' in request.GET:
                    ids = int(encrypt(request.GET['ids']))
                    data['eSede'] = eSedeVirtual = SedeVirtual.objects.get(pk=ids)
                    return render(request, "adm_asistenciaexamensede/manual/sedevirtual/view.html", data)
                if 'idf' in request.GET:
                    idf = int(encrypt(request.GET['idf']))
                    data['eFechaPlanificacionSedeVirtualExamen'] = eFechaPlanificacionSedeVirtualExamen = FechaPlanificacionSedeVirtualExamen.objects.get(pk=idf)
                    data['eSede'] = eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                    return render(request, "adm_asistenciaexamensede/manual/fechaplanificacion/view.html", data)
                if 'idh' in request.GET:
                    idh = int(encrypt(request.GET['idh']))
                    data['eTurnoPlanificacionSedeVirtualExamen'] =eTurnoPlanificacionSedeVirtualExamen = TurnoPlanificacionSedeVirtualExamen.objects.get(pk=idh)
                    data['eSede'] = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion.sede
                    data['eFechaPlanificacionSedeVirtualExamen'] = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion
                    return render(request, "adm_asistenciaexamensede/manual/horarioplanificacion/view.html", data)
                if 'ida' in request.GET:
                    ida = int(encrypt(request.GET['ida']))
                    eAulaPlanificacionSedeVirtualExamen = AulaPlanificacionSedeVirtualExamen.objects.get(pk=ida)
                    data['eSede'] = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion.fechaplanificacion.sede
                    data['eFechaPlanificacionSedeVirtualExamen'] = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion.fechaplanificacion
                    data['eTurnoPlanificacionSedeVirtualExamen'] = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion
                    data['eAulaPlanificacionSedeVirtualExamen'] = eAulaPlanificacionSedeVirtualExamen
                    search = None
                    url_vars = ''
                    if persona.usuario.is_superuser:
                        eMateriaAsignadaPlanificacionSedeVirtualExamenes = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(aulaplanificacion=eAulaPlanificacionSedeVirtualExamen,
                                                                                                                                        aulaplanificacion__turnoplanificacion__fechaplanificacion__periodo=periodo,
                                                                                                                                        status=True)
                    else:
                        idsgrupal = SupervisorAulaPlanificacionSedeVirtualExamen.objects.filter(Q(responsable=persona) | Q(supervisor=persona), status=True, aulaplanificacion=eAulaPlanificacionSedeVirtualExamen).distinct().values_list('aulaplanificacion_id', flat=True)
                        eMateriaAsignadaPlanificacionSedeVirtualExamenes = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(Q(aulaplanificacion__responsable=persona) |
                                                                                                                                        Q(aulaplanificacion__turnoplanificacion__fechaplanificacion__supervisor=persona) |
                                                                                                                                        Q(aulaplanificacion__supervisor=persona) | Q(aulaplanificacion_id__in=idsgrupal),
                                                                                                                                        aulaplanificacion=eAulaPlanificacionSedeVirtualExamen,
                                                                                                                                        aulaplanificacion__turnoplanificacion__fechaplanificacion__periodo=periodo,
                                                                                                                                        status=True)
                    eMateriaAsignadaPlanificacionSedeVirtualExamenes_copia = eMateriaAsignadaPlanificacionSedeVirtualExamenes
                    aCoordinaciones = []
                    for eCoordinacion in Coordinacion.objects.filter(pk__in=eMateriaAsignadaPlanificacionSedeVirtualExamenes_copia.values_list('materiaasignada__materia__asignaturamalla__malla__carrera__coordinacion__id', flat=True)).distinct():
                        aMallas = []
                        for eMalla in Malla.objects.filter(carrera__coordinacion=eCoordinacion, pk__in=eMateriaAsignadaPlanificacionSedeVirtualExamenes_copia.values_list('materiaasignada__materia__asignaturamalla__malla__id', flat=True)).distinct():
                            aMaterias = []
                            for eMateria in Materia.objects.filter(asignaturamalla__malla__carrera__coordinacion=eCoordinacion, asignaturamalla__malla=eMalla, pk__in=eMateriaAsignadaPlanificacionSedeVirtualExamenes_copia.values_list('materiaasignada__materia__id', flat=True)).order_by('asignaturamalla__asignatura__nombre', 'paralelomateria__nombre').distinct():
                                total = len(eMateriaAsignadaPlanificacionSedeVirtualExamenes_copia.filter(materiaasignada__materia__asignaturamalla__malla__carrera__coordinacion=eCoordinacion, materiaasignada__materia__asignaturamalla__malla=eMalla, materiaasignada__materia=eMateria))
                                eProfesor = eMateria.profesor_principal_virtual()
                                aMaterias.append({'id': eMateria.pk,
                                                  'nombre': eMateria.asignaturamalla.asignatura.nombre,
                                                  'nivel': eMateria.asignaturamalla.nivelmalla.nombre,
                                                  'paralelo': eMateria.paralelomateria.nombre,
                                                  'profesor': eProfesor.persona.nombre_completo_inverso() if eProfesor else '',
                                                  'total': total,
                                                  'idcursomoodle': eMateria.idcursomoodle})
                            aMallas.append({'id': eMalla.pk,
                                            'nombre': eMalla.nombre_corto(),
                                            'aMaterias': aMaterias})
                        aCoordinaciones.append({'id': eCoordinacion.pk,
                                                'nombre': eCoordinacion.nombre,
                                                'aMallas': aMallas})
                    data['aCoordinaciones'] = aCoordinaciones

                    if 'id' in request.GET:
                        id = request.GET['id']
                        eMateriaAsignadaPlanificacionSedeVirtualExamenes = eMateriaAsignadaPlanificacionSedeVirtualExamenes.filter(id=id)

                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            eMateriaAsignadaPlanificacionSedeVirtualExamenes = eMateriaAsignadaPlanificacionSedeVirtualExamenes.filter(Q(materiaasignada__matricula__inscripcion__persona__nombres__icontains=search) |
                                                                                                                                       Q(materiaasignada__matricula__inscripcion__persona__apellido1__icontains=search) |
                                                                                                                                       Q(materiaasignada__matricula__inscripcion__persona__apellido2__icontains=search) |
                                                                                                                                       Q(materiaasignada__matricula__inscripcion__persona__cedula__icontains=search) |
                                                                                                                                       Q(materiaasignada__matricula__inscripcion__persona__pasaporte__icontains=search) |
                                                                                                                                       Q(materiaasignada__matricula__inscripcion__persona__usuario__username__icontains=search)).distinct().select_related('materiaasignada__matricula__inscripcion__persona')
                        else:
                            eMateriaAsignadaPlanificacionSedeVirtualExamenes = eMateriaAsignadaPlanificacionSedeVirtualExamenes.filter(Q(materiaasignada__matricula__inscripcion__persona__apellido1__icontains=ss[0]) &
                                                                                                                                       Q(materiaasignada__matricula__inscripcion__persona__apellido2__icontains=ss[1])).distinct().select_related('materiaasignada__matricula__inscripcion__persona')
                        url_vars += f'&s={search}'
                    paging = MiPaginador(eMateriaAsignadaPlanificacionSedeVirtualExamenes, 100)
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
                    data["url_params"] = url_vars
                    data['acceso_examen'] = variable_valor('ACCESO_EXAMEN')
                    data['eMateriaAsignadaPlanificacionSedeVirtualExamenes'] = page.object_list
                    data['isLocal'] = DEBUG
                    return render(request, "adm_asistenciaexamensede/manual/aulaplanificacion/view.html", data)
                return render(request, "adm_asistenciaexamensede/manual/panel.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return render(request, "adm_asistenciaexamensede/error.html", data)
