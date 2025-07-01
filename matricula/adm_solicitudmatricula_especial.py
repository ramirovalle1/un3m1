# -*- coding: UTF-8 -*-
import json
import random
from datetime import datetime, timedelta

import xlwt
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.aggregates import Avg
from django.db.models.query_utils import Q
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from xlwt import *

from decorators import secure_module, last_access
from matricula.forms import MatriculaEspecialActionForm
from matricula.models import SolicitudMatriculaEspecial, ConfigProcesoMatriculaEspecial, \
    HistorialSolicitudMatriculaEspecial, ProcesoMatriculaEspecial, ConfigProcesoMatriculaEspecialAsistente, \
    EstadoMatriculaEspecial, SolicitudMatriculaEspecialAsignatura
from settings import HOMITIRCAPACIDADHORARIO, CALCULO_POR_CREDITO, NOTA_ESTADO_EN_CURSO, MATRICULACION_LIBRE, \
    MATRICULAR_CON_DEUDA, MAXIMO_MATERIA_ONLINE, UTILIZA_GRATUIDADES, PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD, \
    PORCIENTO_PERDIDA_TOTAL_GRATUIDAD
from sga.commonviews import adduserdata, conflicto_materias_seleccionadas, matricular
from sga.forms import SolicitudForm, ConfiguracionTerceraMatriculaForm
from sga.funciones import MiPaginador, log, generar_nombre, fechatope, variable_valor, puede_realizar_accion, \
    puede_modificar_inscripcion
from sga.models import SolicitudMatricula, SolicitudDetalle, AsignaturaMalla, Asignatura, Matricula, Materia, \
    AgregacionEliminacionMaterias, MateriaAsignada, \
    Coordinacion, TipoSolicitud, ConfiguracionTerceraMatricula, Inscripcion, ProfesorMateria, GruposProfesorMateria, \
    AlumnosPracticaMateria, Carrera, Notificacion, Nivel
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    miscarreras = persona.mis_carreras()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'listSolicitudes':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"Parametro de inscripción no encontrado")
                if not Inscripcion.objects.filter(pk=int(request.POST['id'])).exists():
                    raise NameError(u"Inscripción no encontrada")
                data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=int(request.POST['id']))
                data['solicitudes'] = SolicitudMatriculaEspecial.objects.filter(inscripcion=inscripcion, periodo=periodo).order_by('-secuencia')
                template = get_template("adm_solicitudmatricula/especial/solicitudes.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'aData': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'viewSolicitud':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"Parametro solicitud no encontrado")
                if not SolicitudMatriculaEspecial.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Solicitud no encontrada")
                eSolicitudMatriculaEspecial = SolicitudMatriculaEspecial.objects.filter(pk=request.POST['id'])[0]
                data['eSolicitudMatriculaEspecial'] = eSolicitudMatriculaEspecial
                pasos = ConfigProcesoMatriculaEspecial.objects.filter(proceso=eSolicitudMatriculaEspecial.proceso, status=True).distinct()
                data['pasos'] = pasos
                template = get_template("adm_solicitudmatricula/especial/ver_solicitud.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", "contenido": json_content, "codigo": eSolicitudMatriculaEspecial.codigo})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error al cargar los datos. %s" % ex.__str__()})

        elif action == 'viewReasignarSolicitud':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"Parametro solicitud no encontrado")
                if not SolicitudMatriculaEspecial.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Solicitud no encontrada")
                eSolicitudMatriculaEspecial = SolicitudMatriculaEspecial.objects.filter(pk=request.POST['id'])[0]
                data['eSolicitudMatriculaEspecial'] = eSolicitudMatriculaEspecial
                asistentes_departamento = ConfigProcesoMatriculaEspecialAsistente.objects.filter(configuracion__proceso=eSolicitudMatriculaEspecial.proceso, activo=True, coordinacion__isnull=True)
                asistentes_facultad = ConfigProcesoMatriculaEspecialAsistente.objects.filter(configuracion__proceso=eSolicitudMatriculaEspecial.proceso, activo=True, departamento__isnull=True, carrera=eSolicitudMatriculaEspecial.inscripcion.carrera)
                asistentes = asistentes_departamento | asistentes_facultad
                data['asistentes'] = asistentes
                template = get_template("adm_solicitudmatricula/especial/ver_reasignar_solicitud.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", "contenido": json_content, "codigo": eSolicitudMatriculaEspecial.codigo})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error al cargar los datos. %s" % ex.__str__()})

        elif action == 'reasignarSolicitud':
            try:
                if not 'ids' in request.POST:
                    raise NameError(u"Parametro solicitud no encontrado")
                if not 'idr' in request.POST:
                    raise NameError(u"Parametro responsable no encontrado")
                if not 'observacion' in request.POST:
                    raise NameError(u"Parametro de observación no encontrado")
                if not SolicitudMatriculaEspecial.objects.filter(pk=request.POST['ids']).exists():
                    raise NameError(u"Solicitud no encontrada")
                if not ConfigProcesoMatriculaEspecialAsistente.objects.filter(pk=request.POST['idr']).exists():
                    raise NameError(u"Responsable no encontrado")
                observacion = request.POST['observacion']
                eSolicitudMatriculaEspecial = SolicitudMatriculaEspecial.objects.filter(pk=request.POST['ids'])[0]
                # PRIMERO NOTIFICAR AL SERVIDOR ACTUAL QUE TIENE LA SOLICITUD
                eHistorialSolicitudMatriculaEspecialActual = HistorialSolicitudMatriculaEspecial.objects.filter(solicitud=eSolicitudMatriculaEspecial, paso=eSolicitudMatriculaEspecial.paso).order_by('-fecha', '-hora')[0]
                notificacion = Notificacion(titulo=f"Solicitud cancelada Nro.{eSolicitudMatriculaEspecial.codigo} de matrícula especial",
                                            cuerpo=f"Solicitud de matrícula especial Nro.{eSolicitudMatriculaEspecial.codigo} fue reasignada a otro/a servidor/a",
                                            destinatario=eHistorialSolicitudMatriculaEspecialActual.responsable,
                                            url=f"/adm_solicitudmatricula/especial?action=solicitudes&id={eSolicitudMatriculaEspecial.id}",
                                            fecha_hora_visible=datetime.now() + timedelta(days=3),
                                            content_type=ContentType.objects.get_for_model(eSolicitudMatriculaEspecial),
                                            object_id=eSolicitudMatriculaEspecial.id,
                                            prioridad=1,
                                            app_label='sga')
                notificacion.save(request)

                # REASIGNAR LA MATRICULA
                eConfigProcesoMatriculaEspecialAsistente = ConfigProcesoMatriculaEspecialAsistente.objects.filter(pk=request.POST['idr'])[0]
                eHistorialSolicitudMatriculaEspecial = HistorialSolicitudMatriculaEspecial(solicitud=eSolicitudMatriculaEspecial,
                                                                                           paso=eConfigProcesoMatriculaEspecialAsistente.configuracion,
                                                                                           fecha=datetime.now().date(),
                                                                                           hora=datetime.now().time(),
                                                                                           estado=eHistorialSolicitudMatriculaEspecialActual.estado,
                                                                                           departamento=None,
                                                                                           coordinacion=None,
                                                                                           responsable=eConfigProcesoMatriculaEspecialAsistente.responsable,
                                                                                           observacion=f"Reasignado por {persona}. Observación: {observacion}",
                                                                                           archivo=eHistorialSolicitudMatriculaEspecialActual.archivo,
                                                                                           )
                eHistorialSolicitudMatriculaEspecial.save(request)
                departamento = None
                if eConfigProcesoMatriculaEspecialAsistente.configuracion.es_departamento():
                    departamento = eConfigProcesoMatriculaEspecialAsistente.departamento
                    eHistorialSolicitudMatriculaEspecial.departamento = eConfigProcesoMatriculaEspecialAsistente.departamento
                elif eConfigProcesoMatriculaEspecialAsistente.configuracion.es_coordinacion():
                    departamento = eConfigProcesoMatriculaEspecialAsistente.coordinacion
                    eHistorialSolicitudMatriculaEspecial.coordinacion = eConfigProcesoMatriculaEspecialAsistente.coordinacion
                else:
                    raise NameError(u"No se configuración adecuada para reasignar la solicitud")
                eHistorialSolicitudMatriculaEspecial.save(request)
                log(f'Adiciono historial de solicitud de matrícula especial: {eHistorialSolicitudMatriculaEspecial.__str__()}', request, "add")
                notificacion = Notificacion(titulo=f"Tiene una solicitud Nro.{eSolicitudMatriculaEspecial.codigo} de matrícula especial",
                                            cuerpo=f"Solicitud de matrícula especial Nro.{eSolicitudMatriculaEspecial.codigo} por gestionar",
                                            destinatario=eConfigProcesoMatriculaEspecialAsistente.responsable,
                                            url=f"/adm_solicitudmatricula/especial?action=solicitudes&id={eSolicitudMatriculaEspecial.id}",
                                            fecha_hora_visible=datetime.now() + timedelta(days=3),
                                            content_type=ContentType.objects.get_for_model(eSolicitudMatriculaEspecial),
                                            object_id=eSolicitudMatriculaEspecial.id,
                                            prioridad=1,
                                            app_label='sga')
                notificacion.save(request)
                eSolicitudMatriculaEspecial.estado = eHistorialSolicitudMatriculaEspecial.estado
                eSolicitudMatriculaEspecial.paso = eHistorialSolicitudMatriculaEspecial.paso
                eSolicitudMatriculaEspecial.save(request)
                notificacion = Notificacion(titulo=f"Cambio de estado de la solicitud Nro.{eSolicitudMatriculaEspecial.codigo}",
                                            cuerpo=f"Tu solicitud de matrícula especial Nro.{eSolicitudMatriculaEspecial.codigo} se reasigno {eConfigProcesoMatriculaEspecialAsistente.responsable.__str__()} y se encuentra en {departamento.__str__()}",
                                            destinatario=eSolicitudMatriculaEspecial.inscripcion.persona,
                                            url=f"/alu_solicitudmatricula/especial?id={eSolicitudMatriculaEspecial.id}",
                                            fecha_hora_visible=datetime.now() + timedelta(days=1),
                                            content_type=ContentType.objects.get_for_model(eSolicitudMatriculaEspecial),
                                            object_id=eSolicitudMatriculaEspecial.id,
                                            prioridad=1,
                                            app_label='sga')
                notificacion.save(request)
                return JsonResponse({"result": "ok", "mensaje": u"Se reasigno correctamento"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error al guardar los datos. %s" % ex.__str__()})

        elif action == 'rechazar':
            try:
                if not 'ids' in request.POST:
                    raise NameError(u"Parametro de solicitud no encontrado")
                if not SolicitudMatriculaEspecial.objects.values("id").filter(pk=request.POST['ids']).exists():
                    raise NameError(u"Solicitud no encontrada")
                eSolicitudMatriculaEspecial = SolicitudMatriculaEspecial.objects.get(pk=request.POST['ids'])
                f = MatriculaEspecialActionForm(request.POST, request.FILES)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                archivo = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext in ['.pdf', '.PDF']:
                            raise NameError(u"Archivo erroneo, solo se permiten .pdf")
                        if newfile.size > 10485760:
                            raise NameError(u"Archivo erroneo, solo se permiten menor a 10 Mb.")
                        if newfile:
                            newfile._name = generar_nombre(f"{persona.usuario}/justificacion", newfile._name)
                    archivo = newfile
                eProcesoMatriculaEspecial = eSolicitudMatriculaEspecial.proceso
                if not EstadoMatriculaEspecial.objects.values("id").filter(status=True).exists():
                    raise NameError(u"No se encontro estados configurado")
                eEstadoMatriculaEspecial = EstadoMatriculaEspecial.objects.filter(status=True)
                if not ConfigProcesoMatriculaEspecial.objects.values("id").filter(proceso=eProcesoMatriculaEspecial).exists():
                    raise NameError(u"No existe configuración activa para el proceso de matrícula especial")
                eConfigProcesoRechazar = eSolicitudMatriculaEspecial.paso
                if not eEstadoMatriculaEspecial.values("id").filter(accion=2).exists():
                    raise NameError(u"Estado de solictud no configurado")
                estado_nok = eSolicitudMatriculaEspecial.paso.estado_nok
                eHistorialSolicitudMatriculaEspecial = HistorialSolicitudMatriculaEspecial(solicitud=eSolicitudMatriculaEspecial,
                                                                                           paso=eConfigProcesoRechazar,
                                                                                           fecha=datetime.now().date(),
                                                                                           hora=datetime.now().time(),
                                                                                           estado=estado_nok,
                                                                                           departamento=None,
                                                                                           coordinacion=None,
                                                                                           responsable=persona,
                                                                                           observacion=f.cleaned_data['observacion'],
                                                                                           archivo=archivo,
                                                                                           )
                eHistorialSolicitudMatriculaEspecial.save(request)
                if eConfigProcesoRechazar.es_departamento():
                    eConfigProcesoResponsable = ConfigProcesoMatriculaEspecialAsistente.objects.filter(configuracion=eConfigProcesoRechazar, status=True, activo=True)[0]
                    eHistorialSolicitudMatriculaEspecial.departamento = eConfigProcesoResponsable.departamento
                elif eConfigProcesoRechazar.es_coordinacion():
                    if not ConfigProcesoMatriculaEspecialAsistente.objects.filter(configuracion=eConfigProcesoRechazar, activo=True, status=True, coordinacion=eSolicitudMatriculaEspecial.inscripcion.coordinacion, carrera=eSolicitudMatriculaEspecial.inscripcion.carrera).exists():
                        raise NameError(u"No existe responsable de facultad que atienda la solicitud")
                    eConfigProcesoResponsable = ConfigProcesoMatriculaEspecialAsistente.objects.filter(configuracion=eConfigProcesoRechazar, activo=True, status=True, coordinacion=eSolicitudMatriculaEspecial.inscripcion.coordinacion, carrera=eSolicitudMatriculaEspecial.inscripcion.carrera)[0]
                    eHistorialSolicitudMatriculaEspecial.coordinacion = eConfigProcesoResponsable.coordinacion
                else:
                    raise NameError(u"No se encontro responsables para la solicitud")
                eHistorialSolicitudMatriculaEspecial.save(request)
                log(f'Adiciono historial de solicitud de matrícula especial: {eHistorialSolicitudMatriculaEspecial.__str__()}', request, "add")

                if not eEstadoMatriculaEspecial.values("id").filter(accion=6).exists():
                    raise NameError(u"Estado de solictud no configurado")
                if not ConfigProcesoMatriculaEspecial.objects.values("id").filter(proceso=eProcesoMatriculaEspecial).exists():
                    raise NameError(u"Proceso de notificar no se encontro")
                eConfigProcesosMatriculaEspecial = ConfigProcesoMatriculaEspecial.objects.filter(proceso=eProcesoMatriculaEspecial)
                eConfigProcesoNotificar = eConfigProcesosMatriculaEspecial.filter(tipo_validacion=4)[0]
                eHistorialSolicitudMatriculaEspecial = HistorialSolicitudMatriculaEspecial(solicitud=eSolicitudMatriculaEspecial,
                                                                                           paso=eConfigProcesoNotificar,
                                                                                           fecha=datetime.now().date(),
                                                                                           hora=datetime.now().time(),
                                                                                           estado=estado_nok,
                                                                                           departamento=None,
                                                                                           coordinacion=eSolicitudMatriculaEspecial.inscripcion.coordinacion,
                                                                                           responsable=eSolicitudMatriculaEspecial.inscripcion.persona,
                                                                                           observacion=f.cleaned_data['observacion'],
                                                                                           archivo=None,
                                                                                           )
                eHistorialSolicitudMatriculaEspecial.save(request)
                log(f'Adiciono historial de solicitud de matrícula especial: {eHistorialSolicitudMatriculaEspecial.__str__()}', request, "add")
                eSolicitudMatriculaEspecial.estado = estado_nok
                eSolicitudMatriculaEspecial.paso = eConfigProcesoNotificar
                eSolicitudMatriculaEspecial.save(request)
                if eSolicitudMatriculaEspecial.tiene_detalle_asignaturas():
                    for am in eSolicitudMatriculaEspecial.detalle_asignaturas():
                        am.estado = 4
                        am.observacion = f.cleaned_data['observacion']
                        am.save(request)

                notificacion = Notificacion(titulo=f"Solicitud de matrícula especial Nro.{eSolicitudMatriculaEspecial.codigo} fue rechazada",
                                            cuerpo=f"Tu solicitud de matrícula especial Nro.{eSolicitudMatriculaEspecial.codigo} fue rechazada. {f.cleaned_data['observacion']}",
                                            destinatario=eSolicitudMatriculaEspecial.inscripcion.persona,
                                            url=f"/alu_solicitudmatricula/especial?id={eSolicitudMatriculaEspecial.id}",
                                            fecha_hora_visible=datetime.now() + timedelta(days=1),
                                            content_type=ContentType.objects.get_for_model(eSolicitudMatriculaEspecial),
                                            object_id=eSolicitudMatriculaEspecial.id,
                                            prioridad=1,
                                            app_label='sga'
                                            )
                notificacion.save(request)
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente los cambios')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error al rechazar solicitud. %s" % ex.__str__()})

        elif action == 'aprobar':
            try:
                if not 'ids' in request.POST:
                    raise NameError(u"Parametro de solicitud no encontrado")
                if not SolicitudMatriculaEspecial.objects.values("id").filter(pk=request.POST['ids']).exists():
                    raise NameError(u"Solicitud no encontrada")
                eSolicitudMatriculaEspecial = SolicitudMatriculaEspecial.objects.get(pk=request.POST['ids'])
                f = MatriculaEspecialActionForm(request.POST, request.FILES)
                if not f.is_valid():
                    for k, v in f.errors.items():
                        raise NameError(v[0])
                archivo = None
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    if newfile:
                        newfilesd = newfile._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext in ['.pdf', '.PDF']:
                            raise NameError(u"Archivo erroneo, solo se permiten .pdf")
                        if newfile.size > 10485760:
                            raise NameError(u"Archivo erroneo, solo se permiten menor a 10 Mb.")
                        if newfile:
                            newfile._name = generar_nombre(f"{persona.usuario}/justificacion", newfile._name)
                    archivo = newfile
                if not EstadoMatriculaEspecial.objects.values("id").filter(status=True).exists():
                    raise NameError(u"No se encontro estados configurado")
                eEstadoMatriculaEspecial = EstadoMatriculaEspecial.objects.filter(status=True)
                eProcesoMatriculaEspecial = eSolicitudMatriculaEspecial.proceso
                estado_ok = eSolicitudMatriculaEspecial.paso.estado_ok
                eHistorialSolicitudMatriculaEspecial = HistorialSolicitudMatriculaEspecial(solicitud=eSolicitudMatriculaEspecial,
                                                                                           paso=eSolicitudMatriculaEspecial.paso,
                                                                                           fecha=datetime.now().date(),
                                                                                           hora=datetime.now().time(),
                                                                                           estado=estado_ok,
                                                                                           departamento=None,
                                                                                           coordinacion=None,
                                                                                           responsable=persona,
                                                                                           observacion=f.cleaned_data['observacion'],
                                                                                           archivo=archivo,
                                                                                           )
                eHistorialSolicitudMatriculaEspecial.save(request)
                if eSolicitudMatriculaEspecial.paso.es_departamento():
                    eConfigProcesoResponsable = ConfigProcesoMatriculaEspecialAsistente.objects.filter(configuracion=eSolicitudMatriculaEspecial.paso, activo=True, status=True)[0]
                    eHistorialSolicitudMatriculaEspecial.departamento = eConfigProcesoResponsable.departamento
                elif eSolicitudMatriculaEspecial.paso.es_coordinacion():
                    if not ConfigProcesoMatriculaEspecialAsistente.objects.filter(configuracion=eSolicitudMatriculaEspecial.paso, activo=True, status=True, coordinacion=eSolicitudMatriculaEspecial.inscripcion.coordinacion, carrera=eSolicitudMatriculaEspecial.inscripcion.carrera).exists():
                        raise NameError(u"No existe responsable de facultad que atienda la solicitud")
                    eConfigProcesoResponsable = ConfigProcesoMatriculaEspecialAsistente.objects.filter(configuracion=eSolicitudMatriculaEspecial.paso, activo=True, status=True, coordinacion=eSolicitudMatriculaEspecial.inscripcion.coordinacion, carrera=eSolicitudMatriculaEspecial.inscripcion.carrera)[0]
                    eHistorialSolicitudMatriculaEspecial.coordinacion = eConfigProcesoResponsable.coordinacion
                else:
                    raise NameError(u"No se encontro responsables para la solicitud")
                eHistorialSolicitudMatriculaEspecial.save(request)
                log(f'Adiciono historial de solicitud de matrícula especial: {eHistorialSolicitudMatriculaEspecial.__str__()}', request, "add")
                if not eEstadoMatriculaEspecial.values("id").filter(accion=5).exists():
                    raise NameError(u"Estado de solictud no configurado")
                EN_TRAMITE = eEstadoMatriculaEspecial.filter(accion=5)[0]
                if not ConfigProcesoMatriculaEspecial.objects.values("id").filter(proceso=eProcesoMatriculaEspecial).exists():
                    raise NameError(u"Proceso de notificar no se encontro")
                eConfigProcesosMatriculaEspecial = ConfigProcesoMatriculaEspecial.objects.filter(proceso=eProcesoMatriculaEspecial)
                if not eConfigProcesosMatriculaEspecial.filter(orden=eSolicitudMatriculaEspecial.paso.orden + 1).exists():
                    raise NameError(u"No existe proceso mas proceso por continuar")
                eConfigProcesoMatriculaEspecialSiguiente = eConfigProcesosMatriculaEspecial.filter(orden=eSolicitudMatriculaEspecial.paso.orden + 1)[0]
                responsable = None
                departamento = None
                if eConfigProcesoMatriculaEspecialSiguiente.es_departamento():
                    eConfigProcesoResponsable = ConfigProcesoMatriculaEspecialAsistente.objects.filter(configuracion=eConfigProcesoMatriculaEspecialSiguiente, activo=True, status=True)[0]
                    eHistorialSolicitudMatriculaEspecial = HistorialSolicitudMatriculaEspecial(solicitud=eSolicitudMatriculaEspecial,
                                                                                               paso=eConfigProcesoMatriculaEspecialSiguiente,
                                                                                               fecha=datetime.now().date(),
                                                                                               hora=datetime.now().time(),
                                                                                               estado=EN_TRAMITE,
                                                                                               departamento=eConfigProcesoResponsable.departamento,
                                                                                               coordinacion=None,
                                                                                               responsable=eConfigProcesoResponsable.responsable,
                                                                                               observacion='ASIGNACIÓN AUTOMATICA MEDIANTE EL SGA',
                                                                                               archivo=None,
                                                                                               )
                    responsable = eConfigProcesoResponsable.responsable
                    departamento = eConfigProcesoResponsable.departamento
                elif eConfigProcesoMatriculaEspecialSiguiente.es_coordinacion():
                    if not ConfigProcesoMatriculaEspecialAsistente.objects.filter(configuracion=eConfigProcesoMatriculaEspecialSiguiente, activo=True, status=True, coordinacion=eSolicitudMatriculaEspecial.inscripcion.coordinacion, carrera=eSolicitudMatriculaEspecial.inscripcion.carrera).exists():
                        raise NameError(u"No existe responsable de facultad que atienda la solicitud")
                    eConfigProcesoResponsable = ConfigProcesoMatriculaEspecialAsistente.objects.filter(configuracion=eConfigProcesoMatriculaEspecialSiguiente, activo=True, status=True, coordinacion=eSolicitudMatriculaEspecial.inscripcion.coordinacion, carrera=eSolicitudMatriculaEspecial.inscripcion.carrera)[0]
                    eHistorialSolicitudMatriculaEspecial = HistorialSolicitudMatriculaEspecial(solicitud=eSolicitudMatriculaEspecial,
                                                                                               paso=eConfigProcesoMatriculaEspecialSiguiente,
                                                                                               fecha=datetime.now().date(),
                                                                                               hora=datetime.now().time(),
                                                                                               estado=EN_TRAMITE,
                                                                                               departamento=None,
                                                                                               coordinacion=eConfigProcesoResponsable.coordinacion,
                                                                                               responsable=eConfigProcesoResponsable.responsable,
                                                                                               observacion='ASIGNACIÓN AUTOMATICA MEDIANTE EL SGA',
                                                                                               archivo=None,
                                                                                               )
                    responsable = eConfigProcesoResponsable.responsable
                    departamento = eConfigProcesoResponsable.coordinacion
                else:
                    raise NameError(u"No se encontro responsables para la solicitud")
                eHistorialSolicitudMatriculaEspecial.save(request)
                log(f'Adiciono historial de solicitud de matrícula especial: {eHistorialSolicitudMatriculaEspecial.__str__()}', request, "add")
                notificacion = Notificacion(titulo=f"Tiene una solicitud Nro.{eSolicitudMatriculaEspecial.codigo} de matrícula especial",
                                            cuerpo=f"Solicitud de matrícula especial Nro.{eSolicitudMatriculaEspecial.codigo} por gestionar",
                                            destinatario=responsable,
                                            url=f"/adm_solicitudmatricula/especial?action=solicitudes&id={eSolicitudMatriculaEspecial.id}",
                                            fecha_hora_visible=datetime.now() + timedelta(days=3),
                                            content_type=ContentType.objects.get_for_model(eSolicitudMatriculaEspecial),
                                            object_id=eSolicitudMatriculaEspecial.id,
                                            prioridad=1,
                                            app_label='sga')
                notificacion.save(request)
                eSolicitudMatriculaEspecial.estado = EN_TRAMITE
                eSolicitudMatriculaEspecial.paso = eHistorialSolicitudMatriculaEspecial.paso
                eSolicitudMatriculaEspecial.save(request)
                notificacion = Notificacion(titulo=f"Cambio de estado de la solicitud Nro.{eSolicitudMatriculaEspecial.codigo}",
                                            cuerpo=f"Tu solicitud de matrícula especial Nro.{eSolicitudMatriculaEspecial.codigo} cambio de estado {EN_TRAMITE} y se encuentra en {departamento.__str__()}",
                                            destinatario=eSolicitudMatriculaEspecial.inscripcion.persona,
                                            url=f"/alu_solicitudmatricula/especial?id={eSolicitudMatriculaEspecial.id}",
                                            fecha_hora_visible=datetime.now() + timedelta(days=1),
                                            content_type=ContentType.objects.get_for_model(eSolicitudMatriculaEspecial),
                                            object_id=eSolicitudMatriculaEspecial.id,
                                            prioridad=1,
                                            app_label='sga')
                notificacion.save(request)
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente los cambios')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error al aceptar solicitud. %s" % ex.__str__()})

        elif action == 'matricular':
            try:
                if not 'ids' in request.POST:
                    raise NameError(u"Parametro de solicitud no encontrado")
                if not SolicitudMatriculaEspecial.objects.values("id").filter(pk=request.POST['ids']).exists():
                    raise NameError(u"Solicitud no encontrada")
                eSolicitudMatriculaEspecial = SolicitudMatriculaEspecial.objects.get(pk=request.POST['ids'])
                eEstadoMatriculaEspecial = EstadoMatriculaEspecial.objects.filter(status=True)
                eProcesoMatriculaEspecial = eSolicitudMatriculaEspecial.proceso
                estado_ok = eSolicitudMatriculaEspecial.paso.estado_ok
                eHistorialSolicitudMatriculaEspecial = HistorialSolicitudMatriculaEspecial(solicitud=eSolicitudMatriculaEspecial,
                                                                                           paso=eSolicitudMatriculaEspecial.paso,
                                                                                           fecha=datetime.now().date(),
                                                                                           hora=datetime.now().time(),
                                                                                           estado=estado_ok,
                                                                                           departamento=None,
                                                                                           coordinacion=eSolicitudMatriculaEspecial.inscripcion.coordinacion,
                                                                                           responsable=persona,
                                                                                           observacion=f'Se procede a matricular mediante el SGA',
                                                                                           archivo=None,
                                                                                           )
                eHistorialSolicitudMatriculaEspecial.save(request)
                log(f'Adiciono historial de solicitud de matrícula especial: {eHistorialSolicitudMatriculaEspecial.__str__()}', request, "add")
                if not eEstadoMatriculaEspecial.values("id").filter(accion=7).exists():
                    raise NameError(u"Estado de solictud no configurado")
                NOTIFICADO = eEstadoMatriculaEspecial.filter(accion=7)[0]
                if not ConfigProcesoMatriculaEspecial.objects.values("id").filter(proceso=eProcesoMatriculaEspecial).exists():
                    raise NameError(u"Proceso de notificar no se encontro")
                eConfigProcesosMatriculaEspecial = ConfigProcesoMatriculaEspecial.objects.filter(proceso=eProcesoMatriculaEspecial)
                if not eConfigProcesosMatriculaEspecial.filter(orden=eSolicitudMatriculaEspecial.paso.orden + 1).exists():
                    raise NameError(u"No existe mas proceso por continuar")
                eConfigProcesoMatriculaEspecialSiguiente = eConfigProcesosMatriculaEspecial.filter(orden=eSolicitudMatriculaEspecial.paso.orden + 1)[0]
                eHistorialSolicitudMatriculaEspecial = HistorialSolicitudMatriculaEspecial(solicitud=eSolicitudMatriculaEspecial,
                                                                                           paso=eConfigProcesoMatriculaEspecialSiguiente,
                                                                                           fecha=datetime.now().date(),
                                                                                           hora=datetime.now().time(),
                                                                                           estado=NOTIFICADO,
                                                                                           departamento=None,
                                                                                           coordinacion=eSolicitudMatriculaEspecial.inscripcion.coordinacion,
                                                                                           responsable=eSolicitudMatriculaEspecial.inscripcion.persona,
                                                                                           observacion='Matriculación mediante secretaria de la facultad',
                                                                                           archivo=None,
                                                                                           )
                eHistorialSolicitudMatriculaEspecial.save(request)
                log(f'Adiciono historial de solicitud de matrícula especial: {eHistorialSolicitudMatriculaEspecial.__str__()}', request, "add")
                eSolicitudMatriculaEspecial.estado = estado_ok
                eSolicitudMatriculaEspecial.paso = eHistorialSolicitudMatriculaEspecial.paso
                eSolicitudMatriculaEspecial.save(request)
                notificacion = Notificacion(titulo=f"Cambio de estado de la solicitud Nro.{eSolicitudMatriculaEspecial.codigo}",
                                            cuerpo=f"Tu solicitud de matrícula especial Nro.{eSolicitudMatriculaEspecial.codigo} cambio de estado {NOTIFICADO}",
                                            destinatario=eSolicitudMatriculaEspecial.inscripcion.persona,
                                            url=f"/alu_solicitudmatricula/especial?id={eSolicitudMatriculaEspecial.id}",
                                            fecha_hora_visible=datetime.now() + timedelta(days=1),
                                            content_type=ContentType.objects.get_for_model(eSolicitudMatriculaEspecial),
                                            object_id=eSolicitudMatriculaEspecial.id,
                                            prioridad=1,
                                            app_label='sga')
                notificacion.save(request)
                mat = matricular(request, True, False)
                # mat = JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error al rechazar solicitud"})
                res = json.loads(mat.content)
                if res['result'] == 'bad':
                    transaction.set_rollback(True)
                    return mat
                if not 'phase' in res:
                    raise NameError(u"Matricula no encontrada")
                matricula_id = int(res['phase'])
                eSolicitudMatriculaEspecial.matricula_id = matricula_id
                eSolicitudMatriculaEspecial.save(request)
                asignaturas = SolicitudMatriculaEspecialAsignatura.objects.filter(solicitud=eSolicitudMatriculaEspecial)
                if eSolicitudMatriculaEspecial.tiene_detalle_asignaturas():
                    for am in eSolicitudMatriculaEspecial.detalle_asignaturas():
                        if am.id in MateriaAsignada.objects.values_list("materia__asignaturamalla__id", flat=True).filter(matricula=eSolicitudMatriculaEspecial.matricula).distinct():
                            am.estado = 2
                            am.observacion = 'Matriculación mediante secretaria de la facultad'
                            am.save(request)
                        else:
                            am.estado = 3
                            am.observacion = 'Matriculación mediante secretaria de la facultad'
                            am.save(request)
                # for ma in MateriaAsignada.objects.filter(matricula=eSolicitudMatriculaEspecial.matricula):
                #     if ma.materia.asignaturamalla.id in asignaturas.values_list("asignatura__id", flat=True).distinct():
                #         asignatura = asignaturas.filter(asignatura=ma.materia.asignaturamalla)[0]
                #         asignatura.materiaasignada = ma
                #         asignatura.estado = 2
                #         asignatura.save(request)
                return mat
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error al matricular. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'solicitudes':
                try:
                    data['title'] = "Gestionar solicitudes"
                    solicitudes = SolicitudMatriculaEspecial.objects.filter(status=True, periodo=periodo)
                    if not ProcesoMatriculaEspecial.objects.values("id").filter(pk__in=solicitudes.values_list('proceso_id', flat=True).distinct(), status=True).exists():
                        raise NameError(u"Proceso de matrícula especial no encontrado")
                    proceso = ProcesoMatriculaEspecial.objects.filter(pk__in=solicitudes.values_list('proceso_id', flat=True).distinct(), status=True)[0]
                    data['proceso'] = proceso
                    if not ConfigProcesoMatriculaEspecialAsistente.objects.values("id").filter(configuracion__proceso=proceso, activo=True, status=True, responsable=persona).exists():
                        raise NameError(u"No tiene permisos para proceso de matrícula especial")
                    data['pasos'] = proceso.configuraciones_proceso()
                    asistente = ConfigProcesoMatriculaEspecialAsistente.objects.filter(configuracion__proceso=proceso, activo=True, status=True, responsable=persona)[0]
                    paso = asistente.configuracion
                    # data['solicitudes'] = solicitudes.filter(paso=paso)
                    data['paso'] = paso
                    solicitudes = solicitudes.filter(paso=paso)
                    if paso.es_coordinacion():
                        solicitudes = solicitudes.filter(inscripcion__carrera__in=asistente.carreras())
                    carreras = Carrera.objects.filter(pk__in=solicitudes.values("inscripcion__carrera__id").distinct())
                    search = None
                    ids = None
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        solicitudes = solicitudes.filter(pk=ids)
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            solicitudes = solicitudes.filter(Q(inscripcion__persona__nombres__icontains=search) |
                                                             Q(inscripcion__persona__apellido1__icontains=search) |
                                                             Q(inscripcion__persona__apellido2__icontains=search) |
                                                             Q(inscripcion__persona__cedula__icontains=search) |
                                                             Q(inscripcion__persona__pasaporte__icontains=search) |
                                                             Q(inscripcion__identificador__icontains=search)).distinct()
                        else:
                            solicitudes = solicitudes.filter(Q(inscripcion__persona__apellido1__icontains=ss[0]) &
                                                             Q(inscripcion__persona__apellido2__icontains=ss[1])).distinct()
                    carreraselect = 0
                    if 'c' in request.GET:
                        carreraselect = int(request.GET['c'])
                        if carreraselect > 0:
                            solicitudes = solicitudes.filter(inscripcion__carrera_id=carreraselect)
                    modalidadselect = 0
                    if 'm' in request.GET:
                        modalidadselect = int(request.GET['m'])
                        if modalidadselect > 0:
                            solicitudes = solicitudes.filter(inscripcion__modalidad_id=modalidadselect)
                    paging = MiPaginador(solicitudes, 25)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['solicitudes'] = page.object_list
                    data['carreras'] = carreras
                    data['carreraselect'] = carreraselect
                    data['modalidadselect'] = modalidadselect
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "adm_solicitudmatricula/especial/gestionar.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'rechazar':
                try:
                    if not 'ids' in request.GET:
                        raise NameError(u"Parametro de solicitud no encontrado")
                    if not SolicitudMatriculaEspecial.objects.values("id").filter(pk=request.GET['ids']).exists():
                        raise NameError(u"Solicitud no encontrada")
                    data['eSolicitudMatriculaEspecial'] = eSolicitudMatriculaEspecial = SolicitudMatriculaEspecial.objects.get(pk=request.GET['ids'])
                    data['title'] = f'Rechazar solicitud Nro.{eSolicitudMatriculaEspecial.codigo}'
                    data['action'] = 'rechazar'
                    f = MatriculaEspecialActionForm()
                    data['form'] = f
                    return render(request, "adm_solicitudmatricula/especial/form.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'aprobar':
                try:
                    if not 'ids' in request.GET:
                        raise NameError(u"Parametro de solicitud no encontrado")
                    if not SolicitudMatriculaEspecial.objects.values("id").filter(pk=request.GET['ids']).exists():
                        raise NameError(u"Solicitud no encontrada")
                    data['eSolicitudMatriculaEspecial'] = eSolicitudMatriculaEspecial = SolicitudMatriculaEspecial.objects.get(pk=request.GET['ids'])
                    data['title'] = f'Aprobar solicitud Nro.{eSolicitudMatriculaEspecial.codigo}'
                    data['action'] = 'aprobar'
                    f = MatriculaEspecialActionForm()
                    data['form'] = f
                    return render(request, "adm_solicitudmatricula/especial/form.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            elif action == 'niveles':
                try:
                    if not request.user.has_perm('sga.puede_visible_periodo'):
                        if not periodo.visible:
                            raise NameError(u"Periodo inactivo")
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    if not 'ids' in request.GET:
                        raise NameError(u"Parametro de solicitud no encontrado")
                    if not SolicitudMatriculaEspecial.objects.values("id").filter(pk=request.GET['ids']).exists():
                        raise NameError(u"Solicitud no encontrada")
                    data['eSolicitudMatriculaEspecial'] = eSolicitudMatriculaEspecial = SolicitudMatriculaEspecial.objects.get(pk=request.GET['ids'])
                    data['title'] = u'Niveles académicos'
                    data['periodo'] = periodo
                    data['coordinaciones'] = persona.mis_coordinaciones()
                    return render(request, "adm_solicitudmatricula/especial/niveles.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?action=solicitudes&info={ex.__str__()}")

            elif action == 'matricular':
                try:
                    puede_realizar_accion(request, 'sga.puede_modificar_matriculas')
                    if not 'ids' in request.GET:
                        raise NameError(u"Parametro de solicitud no encontrado")
                    if not SolicitudMatriculaEspecial.objects.values("id").filter(pk=request.GET['ids']).exists():
                        raise NameError(u"Solicitud no encontrada")
                    eSolicitudMatriculaEspecial = SolicitudMatriculaEspecial.objects.get(pk=request.GET['ids'])
                    if not 'idn' in request.GET:
                        return HttpResponseRedirect(f"{request.path}?action=niveles&ids={eSolicitudMatriculaEspecial.id}")
                    data['title'] = u'Matricular estudiante'
                    data['eSolicitudMatriculaEspecial'] = eSolicitudMatriculaEspecial
                    data['inscripcion'] = inscripcion = eSolicitudMatriculaEspecial.inscripcion
                    puede_modificar_inscripcion(request, inscripcion)
                    if not MATRICULACION_LIBRE:
                        raise NameError(u"No tiene permisos para matriculación libre")
                    hoy = datetime.now().date()
                    data['periodo'] = periodo = request.session['periodo']
                    data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['idn'])
                    data['total_materias_nivel'] = 0
                    if not variable_valor('PUEDE_MATRICULARSE_OTRA_VEZ'):
                        asignaturaid = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(Q(malla__id=22) | Q(malla__carrera_id=37))
                        if inscripcion.recordacademico_set.filter(status=True, aprobada=False).exclude(asignatura__id__in=asignaturaid).count() > 0:
                            raise NameError(u"La matriculación se encuentra activa solo para estudiantes que han aprobado todas sus asignaturas")
                    if inscripcion.persona.tiene_matricula_periodo(periodo):
                        raise NameError(u"Ya se encuentra matriculado en el periodo en otra Carrera")
                    if inscripcion.carrera not in nivel.coordinacion().carrera.all():
                        raise NameError(u"Carrera no esta acorde a la inscripción")
                    if inscripcion.modalidad != nivel.modalidad:
                        raise NameError(u"Modalidad no esta acorde a la inscripción")
                    if inscripcion.sesion != nivel.sesion:
                        raise NameError(u"Sección no esta acorde a la inscripción")
                    inscripcionmalla = inscripcion.malla_inscripcion()
                    if not inscripcionmalla:
                        raise NameError(u"Debe tener malla asociada para poder matricularse")
                    if not MATRICULAR_CON_DEUDA:
                        if inscripcion.adeuda_a_la_fecha():
                            raise NameError(u"Estudiante registra  deuda")
                    if inscripcion.matriculado_periodo(periodo):
                        raise NameError(u"Estudiante registra  matrícula en el periodo")
                    data['total_materias_nivel'] = inscripcion.total_materias_nivel()
                    data['materiasmalla'] = inscripcionmalla.malla.asignaturamalla_set.all().order_by('nivelmalla', 'ejeformativo')
                    data['materiasmodulos'] = inscripcionmalla.malla.modulomalla_set.all()
                    data['total_materias_pendientes_malla'] = inscripcion.total_materias_pendientes_malla()
                    data['materiasmaximas'] = MAXIMO_MATERIA_ONLINE
                    data['utiliza_gratuidades'] = UTILIZA_GRATUIDADES
                    data['err'] = int(request.GET['err']) if 'err' in request.GET else ''
                    data['nombreerroneo'] = Inscripcion.objects.get(pk=request.GET['ide']).persona.nombre_completo() if 'err' in request.GET else ''
                    data['porciento_perdida_parcial_gratuidad'] = PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD
                    data['porciento_perdida_total_gratuidad'] = PORCIENTO_PERDIDA_TOTAL_GRATUIDAD
                    data['NOTIFICACION_NO_MATRICULARSE_OTRA_VEZ'] = 'Aun no esta habilitada la matriculación por mas de una vez en las materia'
                    data['PUEDE_MATRICULARSE_OTRA_VEZ'] = variable_valor('PUEDE_MATRICULARSE_OTRA_VEZ')
                    return render(request, "adm_solicitudmatricula/especial/addmatriculalibre.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"{request.path}?info={ex.__str__()}")

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Solicitudes de matrícula especial'
                search = None
                ids = None
                solicitudes = SolicitudMatriculaEspecial.objects.filter(status=True, periodo=periodo)
                can_manage_requests = False
                if ProcesoMatriculaEspecial.objects.values("id").filter(pk__in=solicitudes.values_list('proceso_id', flat=True).distinct(), status=True).exists():
                    proceso = ProcesoMatriculaEspecial.objects.filter(pk__in=solicitudes.values_list('proceso_id', flat=True).distinct(), status=True)[0]
                    can_manage_requests = ConfigProcesoMatriculaEspecialAsistente.objects.values("id").filter(configuracion__proceso=proceso, activo=True, status=True, responsable=persona).exists()
                data['can_manage_requests'] = can_manage_requests
                inscripciones = Inscripcion.objects.filter(pk__in=solicitudes.values("inscripcion__id").distinct()).order_by('persona__apellido1', 'persona__apellido2')
                carreras = Carrera.objects.filter(pk__in=inscripciones.values("carrera__id").distinct())
                if 'id' in request.GET:
                    ids = request.GET['id']
                    inscripciones = inscripciones.filter(pk=ids)
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        inscripciones = inscripciones.filter(Q(persona__nombres__icontains=search) |
                                                             Q(persona__apellido1__icontains=search) |
                                                             Q(persona__apellido2__icontains=search) |
                                                             Q(persona__cedula__icontains=search) |
                                                             Q(persona__pasaporte__icontains=search) |
                                                             Q(identificador__icontains=search)).distinct()
                    else:
                        inscripciones = inscripciones.filter(Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1])).distinct()
                carreraselect = 0
                if 'c' in request.GET:
                    carreraselect = int(request.GET['c'])
                    if carreraselect > 0:
                        inscripciones = inscripciones.filter(carrera_id=carreraselect)
                modalidadselect = 0
                if 'm' in request.GET:
                    modalidadselect = int(request.GET['m'])
                    if modalidadselect > 0:
                        inscripciones = inscripciones.filter(modalidad_id=modalidadselect)
                paging = MiPaginador(inscripciones, 25)
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
                data['page'] = page
                data['rangospaging'] = paging.rangos_paginado(p)
                data['inscripciones'] = page.object_list
                data['carreras'] = carreras
                data['carreraselect'] = carreraselect
                data['modalidadselect'] = modalidadselect
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                return render(request, "adm_solicitudmatricula/especial/view.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                return render(request, "adm_solicitudmatricula/error.html", data)
