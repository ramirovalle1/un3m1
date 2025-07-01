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
from settings import DEBUG
from sga.commonviews import adduserdata, traerNotificaciones
from sga.funciones import log, puede_realizar_accion, MiPaginador, resetear_clave, variable_valor
from sga.models import Nivel, Materia, MateriaAsignada, SedeVirtual, LaboratorioVirtual, Notificacion, Persona, Malla, \
    Matricula, DetalleModeloEvaluativo, Inscripcion, Coordinacion
from moodle.models import UserAuth
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
        action = request.POST['action']

        if action == 'generatePasswordUser':
            with transaction.atomic():
                try:
                    id = request.POST.get('id', None)
                    if id is None:
                        raise NameError(u"No se encontro el parametro de persona")
                    try:
                        ePersona = Persona.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro la persona")
                    documento = ePersona.documento()
                    if not documento:
                        documento = f"unemi*{datetime.now().year}"
                    eUser = ePersona.usuario
                    if not eUser:
                        raise NameError(u"No tiene asignado usuario activo")
                    eUser.set_password(documento)
                    eUser.save()
                    ePersona.clave_cambiada()
                    eUserAuth = UserAuth.objects.filter(usuario=eUser).first()
                    if eUserAuth is None:
                        eUserAuth = UserAuth(usuario=eUser)
                        eUserAuth.set_data()
                        eUserAuth.set_password(documento)
                        eUserAuth.save()
                    else:
                        if not eUserAuth.check_password(documento) or eUserAuth.check_data():
                            if not eUserAuth.check_password(documento):
                                eUserAuth.set_password(documento)
                            eUserAuth.save()
                    log(u'Reseteo clave de persona : %s' % ePersona, request, "add")
                    return JsonResponse({"result": True, 'aData': {'clave': documento}})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, 'message': str(ex)})

        elif action == 'actionHorarioExamen':
            with transaction.atomic():
                try:
                    id = request.POST.get('id', None)
                    if id is None:
                        raise NameError('No se encontro parametro')
                    visiblehorarioexamen = request.POST.get('visiblehorarioexamen', 'ocultar')
                    visiblehorarioexamen = visiblehorarioexamen == 'mostrar'
                    try:
                        eMatricula = Matricula.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        raise NameError('No se encontro matricula')
                    MateriaAsignada.objects.filter(matricula=eMatricula).update(visiblehorarioexamen=visiblehorarioexamen)
                    eMatricula.delete_cache()
                    eInscripcion = eMatricula.inscripcion
                    eInscripcion.delete_cache()
                    ePersona = eInscripcion.persona
                    ePersona.delete_cache()
                    return JsonResponse({"result": True, "message": f'Se {"activo" if visiblehorarioexamen else "inactivo"} horario de examen correctamente'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "message": f"Ocurrio un error: {ex.__str__()}"})

        elif action == 'actionResetExamen':
            from inno.models import MatriculaSedeExamen
            with transaction.atomic():
                try:
                    id = request.POST.get('id', None)
                    if id is None:
                        raise NameError('No se encontro parametro')
                    try:
                        eMatriculaSedeExamen = MatriculaSedeExamen.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        raise NameError('No se encontro matricula')
                    eMatriculaSedeExamen.archivoidentidad = None
                    eMatriculaSedeExamen.archivofoto = None
                    eMatriculaSedeExamen.aceptotermino = False
                    eMatriculaSedeExamen.fechaaceptotermino = None
                    eMatriculaSedeExamen.urltermino = None
                    eMatriculaSedeExamen.save(request)
                    eMatricula = eMatriculaSedeExamen.matricula
                    eMatricula.delete_cache()
                    eInscripcion = eMatricula.inscripcion
                    eInscripcion.delete_cache()
                    ePersona = eInscripcion.persona
                    ePersona.delete_cache()
                    log(u'Restablecio proceso de archivos y acuerdo de terminos y condiciones de examenes finales: %s' % eMatriculaSedeExamen, request, "add")
                    return JsonResponse({"result": True, "message": f'Se restablecio proceso de examenes'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, "message": f"Ocurrio un error: {ex.__str__()}"})

        elif action == 'registrarAsistenciaExamen':
            with transaction.atomic():
                try:
                    idr = request.POST.get('id', None)
                    if idr is None:
                        raise NameError(u"No se encontro el parametro de registro")
                    try:
                        eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.get(pk=idr)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro el registro")
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
                    template_examen = get_template("adm_asistenciaexamensede/cogs/views/detalleexamen.html")
                    template_clave = get_template("adm_asistenciaexamensede/cogs/views/detalleclave.html")
                    template_asistencia = get_template("adm_asistenciaexamensede/cogs/views/detalleasistencia.html")
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
            with transaction.atomic():
                try:
                    idr = request.POST.get('id', None)
                    if idr is None:
                        raise NameError(u"No se encontro el parametro de registro")
                    try:
                        eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.get(pk=idr)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro el registro")
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.asistencia = False
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.fecha_asistencia = None
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.idtestmoodle = None
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.aviability = None
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request)
                    log(u'Se quita asistencia examen en sede: %s' % eMateriaAsignadaPlanificacionSedeVirtualExamen, request, 'edit')
                    data['acceso_examen'] = variable_valor('ACCESO_EXAMEN')
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
            with transaction.atomic():
                try:
                    if variable_valor('BLOQUEAR_REPLANIFICAR'):
                        raise NameError(u"No tiene permitido replanificar")
                    idr = request.POST.get('id', None)
                    if idr is None:
                        raise NameError(u"No se encontro el parametro de registro")
                    idtestmoodle = request.POST.get('idtestmoodle', None)
                    if idtestmoodle is None:
                        raise NameError(u"No existe examen en moodle configurado")
                    try:
                        eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.get(pk=idr)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro el registro")
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
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.idtestmoodle = int(idtestmoodle)
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.password = password
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.habilitadoexamen = True
                    eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request, updatePassword=True)
                    eMateriaAsignada = eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada
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
                    data['acceso_examen'] = variable_valor('ACCESO_EXAMEN')
                    template_1 = get_template("adm_asistenciaexamensede/cogs/views/detalleexamen.html")
                    template_2 = get_template("adm_asistenciaexamensede/cogs/views/detalleclave.html")
                    data['eMateriaAsignadaPlanificacionSedeVirtualExamen'] = eMateriaAsignadaPlanificacionSedeVirtualExamen
                    aData = {
                        'id': eMateriaAsignadaPlanificacionSedeVirtualExamen.pk,
                        'contenedor_examen': template_1.render(data),
                        'contenedor_clave_examen': template_2.render(data)
                    }
                    return JsonResponse({"result": True, 'aData': aData})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False, 'message': f"{ex.__str__()}"})

        return JsonResponse({"result": False, "message": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'loadHorarioExamenes':
                try:
                    from inno.models import MatriculaSedeExamen
                    id = request.GET.get('id', None)
                    if id is None:
                        raise NameError(u"No se encontro el parametro de persona")
                    try:
                        eMatricula = Matricula.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro la matrícula")
                    eInscripcion = eMatricula.inscripcion
                    data['persona'] = persona
                    data['eMatricula'] = eMatricula
                    data['acceso_examen']  = variable_valor('ACCESO_EXAMEN')
                    data['eInscripcion'] = eInscripcion
                    data['eMatriculaSedeExamenes'] = MatriculaSedeExamen.objects.filter(status=True, matricula=eMatricula)
                    template = get_template("adm_asistenciaexamensede/cogs/views/horario_examenes.html")
                    aData = {
                        'html': template.render(data)
                    }
                    return JsonResponse({"result": True, 'aData': aData})
                except Exception as ex:
                    return JsonResponse({"result": False, "message": ex.__str__()})

            elif action == 'loadFormAccesoExamenIndividual':
                try:
                    id = request.GET.get('id', None)
                    if id is None:
                        raise NameError(u"No se encontro el parametro de registro")
                    try:
                        eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro el registro")
                    materiaasignada = eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada
                    username = materiaasignada.matricula.inscripcion.persona.usuario.username
                    password = eMateriaAsignadaPlanificacionSedeVirtualExamen.password
                    if not eMateriaAsignadaPlanificacionSedeVirtualExamen.password:
                        eMateriaAsignadaPlanificacionSedeVirtualExamen.create_update_password()
                        password = eMateriaAsignadaPlanificacionSedeVirtualExamen.password
                    examenplanificado = materiaasignada.materia.examenplanificadosilabo(eMateriaAsignadaPlanificacionSedeVirtualExamen.detallemodeloevaluativo)
                    if not examenplanificado:
                        raise NameError("No existe planificación de examen")
                    quiz = None
                    intentos = 1
                    limite = 60
                    estado_examen = None
                    if not DEBUG:
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
                    template = get_template("adm_asistenciaexamensede/cogs/views/formAccesoExamenIndividual.html")
                    return JsonResponse({"result": True, 'html': template.render(data), 'estado_examen': estado_examen})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Mesa ténica de examenes en sede'
                data['ePeriodo'] = periodo
                data['eMatriculas'] = None
                if 'search' in request.GET:
                    url_vars = ''
                    search = request.GET['search'].strip()
                    url_vars += f'&s={search}'
                    ss = search.split(' ')
                    filtro = Q(status=True) & Q(nivel__periodo=periodo)
                    if len(ss) == 1:
                        filtro = filtro & (Q(inscripcion__persona__nombres__icontains=search) |
                                           Q(inscripcion__persona__apellido1__icontains=search) |
                                           Q(inscripcion__persona__apellido2__icontains=search) |
                                           Q(inscripcion__persona__cedula__icontains=search) |
                                           Q(inscripcion__persona__pasaporte__icontains=search) |
                                           Q(inscripcion__persona__usuario__username__icontains=search))
                    else:
                        filtro = filtro & (Q(inscripcion__persona__apellido1__icontains=ss[0]) &
                                           Q(inscripcion__persona__apellido2__icontains=ss[1]))
                    eMatriculas = Matricula.objects.filter(filtro).order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2').select_related('inscripcion')
                    paging = MiPaginador(eMatriculas, 10)
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
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['eMatriculas'] = page.object_list
                    data['url_vars'] = url_vars
                return render(request, "adm_asistenciaexamensede/cogs/index.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                return render(request, "adm_asistenciaexamensede/error.html", data)
