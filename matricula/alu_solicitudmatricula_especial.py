# -*- coding: UTF-8 -*-
import json
import random
from datetime import datetime, timedelta, date
from decimal import Decimal

import xlwt
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
from matricula.funciones import valid_intro_module_estudiante, get_nivel_matriculacion, \
    puede_matricularse_seguncronograma_coordinacion, puede_matricularse_seguncronograma_carrera, \
    get_horarios_clases_informacion, get_horarios_clases_data, get_practicas_data, generar_codigo_matricula_especial
from matricula.models import PeriodoMatricula, SolicitudMatriculaEspecial, ProcesoMatriculaEspecial, \
    MotivoMatriculaEspecial, ConfigProcesoMatriculaEspecial, SolicitudMatriculaEspecialAsignatura, \
    HistorialSolicitudMatriculaEspecial, ConfigProcesoMatriculaEspecialAsistente, EstadoMatriculaEspecial
from settings import HOMITIRCAPACIDADHORARIO, CALCULO_POR_CREDITO, NOTA_ESTADO_EN_CURSO, MATRICULACION_LIBRE, \
    NIVEL_MALLA_CERO
from sga.commonviews import adduserdata, conflicto_materias_seleccionadas
from sga.forms import SolicitudForm, ConfiguracionTerceraMatriculaForm
from sga.funciones import MiPaginador, log, generar_nombre, fechatope, variable_valor
from sga.models import SolicitudMatricula, SolicitudDetalle, AsignaturaMalla, Asignatura, Matricula, Materia, \
    AgregacionEliminacionMaterias, MateriaAsignada, \
    Coordinacion, TipoSolicitud, ConfiguracionTerceraMatricula, Inscripcion, ProfesorMateria, GruposProfesorMateria, \
    AlumnosPracticaMateria, ConfirmarMatricula, Nivel, RecordAcademico, Notificacion
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    valid, msg_error = valid_intro_module_estudiante(request, 'pregrado')
    if not valid:
        return HttpResponseRedirect(f"/?info={msg_error}")
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']
    inscripcion = perfilprincipal.inscripcion
    hoy = datetime.now().date()
    miscarreras = persona.mis_carreras()

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'loadInitialData':
            try:
                solicitudes = SolicitudMatriculaEspecial.objects.filter(status=True, inscripcion=inscripcion).order_by('-secuencia')
                aSolicitudes = []
                count = 0
                for solicitud in solicitudes:
                    count += 1
                    aAsignaturas = []
                    if solicitud.tiene_detalle_asignaturas():
                        for a in solicitud.detalle_asignaturas():
                            aAsignaturas.append({"id": a.id,
                                                 "asignatura": a.asignatura.__str__(),
                                                 "asignatura_id": a.asignatura.id,
                                                 "estado": a.get_estado_display(),
                                                 "observacion": a.observacion})
                    aSolicitudes.append({"id": solicitud.id,
                                         "codigo": solicitud.codigo,
                                         "periodo": solicitud.periodo.nombre,
                                         "periodo_id": solicitud.periodo.id,
                                         "descripcion": solicitud.descripcion,
                                         "motivo": solicitud.motivo.__str__(),
                                         "motivo_id": solicitud.motivo.id,
                                         "fecha": solicitud.fecha.strftime('%d-%m-%Y'),
                                         "hora": solicitud.hora.strftime('%H:%M %p'),
                                         "archivo": solicitud.archivo.url if solicitud.archivo else None,
                                         "estado": solicitud.estado.__str__(),
                                         "estado_color": solicitud.estado.color,
                                         "estado_id": solicitud.estado.id,
                                         "puede_cancelar": solicitud.estado.accion in [1, 4],
                                         "asignaturas": aAsignaturas,
                                         "contador": count,
                                         })

                periodomatricula = None
                matricula = None
                has_error = False
                mensaje_error = ""
                isValidoExpecial = False
                configuraciones_proceso = None
                try:
                    if not PeriodoMatricula.objects.values('id').filter(status=True, activo=True, tipo=2).exists():
                        raise NameError(u"Estimado/a estudiante, el periodo de matriculación se encuentra inactivo")
                    periodomatricula = PeriodoMatricula.objects.filter(status=True, activo=True, tipo=2)
                    if periodomatricula.count() > 1:
                        raise NameError(u"Estimado/a estudiante, proceso de matriculación no se encuentra activo")
                    periodomatricula = periodomatricula[0]
                    if not periodomatricula.esta_periodoactivomatricula():
                        raise NameError(u"Estimado/a estudiante, el periodo de matriculación se encuentra inactivo")
                    if inscripcion.tiene_perdida_carrera(periodomatricula.num_matriculas):
                        raise NameError(u"ATENCIÓN: Su limite de matricula por perdida de una o mas asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria para mas informacion.")
                    if periodo and periodomatricula and periodomatricula.periodo.id == periodo.id and inscripcion.persona.tiene_matricula_periodo(periodo):
                        matricula = inscripcion.matricula_periodo2(periodo)
                        if ConfirmarMatricula.objects.values('id').filter(matricula=matricula).exists():
                            raise NameError(f"Estimado/a estudiante, le informamos que ya se encuentra matriculado en el Periodo {periodo.__str__()}. <br>Verificar en el módulo <a href='/alu_materias' class='bloqueo_pantalla'>Mis Materias</a>")
                    if periodomatricula.valida_coordinacion:
                        if not inscripcion.coordinacion in periodomatricula.coordinaciones():
                            raise NameError(u"Estimado/a estudiante, su coordinación/facultad no esta permitida para la matriculación")
                    if periodomatricula.periodo and inscripcion.tiene_automatriculapregrado_por_confirmar(periodomatricula.periodo):
                        raise NameError(f"Estimado/a estudiante, le informamos que registra una matrícula por confirmar en el Periodo {periodo.__str__()}. <br>Verificar en el módulo <a href='/alu_matricula' class='bloqueo_pantalla'>Matriculación</a>")
                    nivel = None
                    nivelid = get_nivel_matriculacion(inscripcion, periodomatricula.periodo)

                    if nivelid < 0:
                        if nivelid == -1:
                            log(u"Estimado/a estudiante, el periodo de matriculación no se encuentra activo.... %s" % (inscripcion.info()), request, "add")
                            raise NameError(u"Estimado/a estudiante, el periodo de matriculación no se encuentra activo")
                        if nivelid == -2:
                            raise NameError(u"Estimado/a estudiante, no existen niveles con cupo para matricularse")
                        if nivelid == -3:
                            raise NameError(u"Estimado/a estudiante, no existen paralelos disponibles")
                        if nivelid == -4:
                            raise NameError(u"Estimado/a estudiante, no existen paralelos para su nivel")
                    nivel = Nivel.objects.get(pk=nivelid)

                    if not nivel.fechainicioagregacion or not nivel.fechatopematricula or not nivel.fechatopematriculaex or not nivel.fechatopematriculaes:
                        raise NameError(u"Estimado/a estudiante, el proceso de matrícula se encuentra inactivo...")

                    if hoy < nivel.fechainicioagregacion:
                        raise NameError(u"Estimado/a estudiante, el proceso de matrícula empieza el %s" % nivel.fechainicioagregacion.__str__())

                    if hoy <= nivel.fechatopematriculaes:
                        if hoy > nivel.fechatopematriculaex:
                            isValidoExpecial = True
                    else:
                        if hoy > nivel.fechatopematriculaes:
                            raise NameError(u"Estimado/a estudiante, el proceso de matrícula especial terminó el %s" % nivel.fechatopematriculaes.__str__())

                    if periodomatricula.valida_cronograma:
                        if not puede_matricularse_seguncronograma_coordinacion(inscripcion, nivel.periodo):
                            raise NameError(u"Estimado/a estudiante, aún no está habilitado el cronograma de matriculación de su carrera.")
                    else:
                        if periodomatricula.tiene_cronograma_carreras():
                            a = puede_matricularse_seguncronograma_carrera(inscripcion, nivel.periodo)
                            if a[0] == 2:
                                raise NameError(u"Estimado/a estudiante, aún no está habilitado el cronograma de matriculación de su carrera.")
                            if a[0] == 3:
                                raise NameError(u"Estimado/a estudiante, usted no realizó su Pre-Matrícula (matricularse después de dos días de haber iniciado matrícula ordinaria).")
                            if a[0] == 4:
                                log(u"Estimado/a estudiante, el periodo de matriculación no se encuentra activo.... %s" % (inscripcion.info()), request, "add")
                                raise NameError(u"Estimado/a estudiante, el periodo de matriculación no se encuentra activo")

                    malla = None
                    inscripcion_malla = inscripcion.malla_inscripcion()
                    if not inscripcion.tiene_malla():
                        raise NameError(u"Estimado/a estudiante, debe tener malla asociada para poder matricularse.")
                    malla = inscripcion_malla.malla

                    if inscripcion.tiene_ultima_matriculas(periodomatricula.num_matriculas):
                        raise NameError(u"Atencion: Estimado/a estudiante, su limite de matricula por perdida de una o mas asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria de la facultad para mas informacion.")

                    if variable_valor('VALIDAR_QUE_SEA_PRIMERA_MATRICULA'):
                        if inscripcion.matricula_set.values('id').filter(status=True).exists():
                            raise NameError(u"Estimado/a estudiante, no puede matricularse; solo apto para primer nivel (nuevos).")

                    minivel = inscripcion.mi_nivel().nivel

                    asignaturasmalla = AsignaturaMalla.objects.values_list('asignatura_id', flat=True).filter(status=True, malla_id=inscripcion.mi_malla().id)
                    fechaultimamateriaprobada = None
                    ultimamateriaaprobada = RecordAcademico.objects.filter(inscripcion_id=inscripcion.id, status=True, asignatura_id__in=asignaturasmalla).exclude(noaplica=True).order_by('-fecha')
                    if ultimamateriaaprobada:
                        fechaultimamateriaprobada = ultimamateriaaprobada[0].fecha + timedelta(days=1810)
                    if fechaultimamateriaprobada:
                        if fechaultimamateriaprobada < nivel.periodo.inicio:
                            raise NameError(u"Reglamento del Régimen Académico - DISPOSICIONES GENERALES: QUINTA.- Si un estudiante no finaliza su carrera o programa y se retira, podrá reingresar a la misma carrera o programa en el tiempo máximo de 5 años contados a partir de la fecha de su retiro. Si no estuviere aplicándose el mismo plan de estudios deberá completar todos los requisitos establecidos en el plan de estudios vigente a la fecha de su reingreso. Cumplido este plazo máximo para el referido reingreso, deberá reiniciar sus estudios en una carrera o programa vigente. En este caso el estudiante podrá homologar a través del mecanismo de validación de conocimientos, las asignaturas, cursos o sus equivalentes, en una carrera o programa vigente, de conformidad con lo establecido en el presente Reglamento.")
                    if not periodomatricula.valida_proceos_matricula_especial:
                        raise NameError(u"Estimado/a estudiante, el proceso de matrícula especial se encuentra inactivo.")
                    if not periodomatricula.proceso_matricula_especial:
                        raise NameError(u"Estimado/a estudiante, el proceso de matrícula especial se encuentra inactivo.")
                    procesomatriculaespecial = periodomatricula.proceso_matricula_especial
                    if not procesomatriculaespecial.activo:
                        raise NameError(u"Estimado/a estudiante, el proceso de matrícula especial se encuentra inactivo.")
                    if not procesomatriculaespecial.tiene_motivos():
                        raise NameError(u"Estimado/a estudiante, el proceso de matrícula especial no permite ningún motivo de solicitud")
                    if not procesomatriculaespecial.tiene_configurado():
                        raise NameError(u"Estimado/a estudiante, el proceso de matrícula especial no se encuentra configurado. Contactrase con Servicios Informaticos")
                    configuraciones_proceso = procesomatriculaespecial.configuraciones_proceso()
                    if configuraciones_proceso.count() == 0:
                        raise NameError(u"Estimado/a estudiante, el proceso de matrícula especial no se encuentra configurado. Contactrase con Servicios Informaticos")
                    if not configuraciones_proceso.filter(tipo_validacion=1).exists():
                        raise NameError(u"Estimado/a estudiante, el proceso de matrícula especial no se encuentra configurado. Contactrase con Servicios Informaticos")

                except Exception as e:
                    has_error = True
                    mensaje_error = e.__str__()
                aMotivos = []
                aData = []
                aProcesos = []
                aProceso = {}
                aPeriodoMatricula = {}
                puede_solicitar = False
                if not has_error and isValidoExpecial:
                    puede_solicitar = True
                    aPeriodoMatricula = {"id": periodomatricula.id,
                                         "periodo_id": periodomatricula.periodo.id,
                                         "proceso_id": periodomatricula.proceso_matricula_especial.id,
                                         "valida_materias_maxima": periodomatricula.valida_materias_maxima,
                                         "num_materias_maxima": periodomatricula.num_materias_maxima,
                                         }
                    for motivo in procesomatriculaespecial.motivos():
                        aMotivos.append({"id": motivo.id,
                                         "nombre": motivo.nombre,
                                         "detalle": motivo.detalle,
                                         "tipo": motivo.tipo})
                    for proceso in configuraciones_proceso:
                        aProcesos.append({"id": proceso.id,
                                          "nombre": proceso.nombre,
                                          "orden": proceso.orden,
                                          "tipo_validacion": proceso.tipo_validacion,
                                          "tipo_validacion_verbose": proceso.get_tipo_validacion_display(),
                                          "tipo_entidad": proceso.tipo_entidad,
                                          "tipo_entidad_verbose": proceso.get_tipo_entidad_display(),
                                          "class": "active" if proceso.tipo_validacion == 1 else "disabled",
                                          "active": proceso.tipo_validacion == 1,
                                          })
                        if proceso.tipo_validacion == 1:
                            aProceso = {"id": proceso.id,
                                        "nombre": proceso.nombre,
                                        "orden": proceso.orden,
                                        "tipo_validacion": proceso.tipo_validacion,
                                        "tipo_validacion_verbose": proceso.get_tipo_validacion_display(),
                                        "tipo_entidad": proceso.tipo_entidad,
                                        "tipo_entidad_verbose": proceso.get_tipo_entidad_display(),
                                        "obligar_archivo": proceso.obligar_archivo,
                                        "obligar_observacion": proceso.obligar_observacion,
                                        "accion_ok": proceso.accion_ok,
                                        "accion_ok_verbose": proceso.get_accion_ok_display().lower(),
                                        "accion_nok": proceso.accion_nok,
                                        "accion_nok_verbose": proceso.get_accion_nok_display().lower(),
                                        "boton_ok_verbose": proceso.boton_ok_verbose,
                                        "boton_ok_label": proceso.boton_ok_label,
                                        "boton_nok_verbose": proceso.boton_nok_verbose,
                                        "boton_nok_label": proceso.boton_nok_label,
                                        }

                    if solicitudes.values("id").filter(periodo=periodomatricula.periodo).exclude(estado__accion__in=[2, 6]).exists():
                        # aux_solicitudes = solicitudes.filter(periodo=periodomatricula.periodo)
                        # solicitud = solicitudes.filter(periodo=periodomatricula.periodo)[0]
                        puede_solicitar = False
                    # cancelo_rechazo = False
                    # for s in solicitudes.filter(periodo=periodomatricula.periodo):
                    #     if s.tiene_historial():
                    #         acciones = s.historial().values_list('estado__accion', flat=True).distinct()
                    #         if 2 in acciones or 6 in acciones:
                    #             if not 3 in acciones or not 5 in acciones:
                    #                 cancelo_rechazo = True
                    #                 break
                    # puede_solicitar = cancelo_rechazo

                    inscripcion_malla = inscripcion.malla_inscripcion()
                    asignaturas_malla = inscripcion_malla.malla.asignaturamalla_set.select_related().all().exclude(nivelmalla_id=NIVEL_MALLA_CERO).order_by('nivelmalla', 'ejeformativo')
                    va_ultima_matricula = inscripcion.va_ultima_matricula(periodomatricula.num_matriculas)
                    for am in asignaturas_malla:
                        puedetomar = inscripcion.puede_tomar_materia(am.asignatura)
                        estado = inscripcion.estado_asignatura(am.asignatura)
                        totalmatriculaasignatura = inscripcion.total_asignatura_record(am.asignatura)
                        if not estado in [1, 2]:
                            if inscripcion.itinerario:
                                if am.itinerario:
                                    if inscripcion.itinerario == am.itinerario:
                                        estado = 3
                                    else:
                                        estado = 0
                                else:
                                    estado = 3
                            else:
                                estado = 3

                        if am.itinerario > 0:
                            itinerario_verbose = f"ITINERARIO {am.itinerario}"
                        else:
                            itinerario_verbose = ''
                        puede_agregar = False
                        """PERMITE QUE UNICAMENTE PUEDAN SELECCIONAR SOLO MATERIAS DE ULTIMA MATRICULA"""
                        if va_ultima_matricula and puedetomar and estado in [2, 3] and totalmatriculaasignatura != (periodomatricula.num_matriculas - 1):
                            puedetomar = False
                        if puedetomar and estado in [2, 3] and totalmatriculaasignatura < periodomatricula.num_matriculas:
                            materiasabiertas = Materia.objects.filter(Q(asignatura=am.asignatura, inicio__gte=hoy, nivel__cerrado=False, nivel__periodo=nivel.periodo), status=True).order_by('id')
                            if periodomatricula and periodomatricula.valida_materia_carrera:
                                materiasabiertas = materiasabiertas.filter(asignaturamalla__malla=inscripcion.mi_malla()).distinct().order_by('id')
                            if periodomatricula and periodomatricula.valida_seccion and not va_ultima_matricula:
                                materiasabiertas = materiasabiertas.filter(nivel__sesion=inscripcion.sesion).distinct().order_by('id')
                            if materiasabiertas.count() > 0:
                                puede_agregar = True
                        predecesoras_verbose = ' , '.join((p.predecesora.asignatura.nombre for p in am.lista_predecesoras()))
                        aData.append({"id": am.id,
                                      "asignatura": am.asignatura.nombre,
                                      "nivelmalla_id": am.nivelmalla.id,
                                      "nivelmalla": am.nivelmalla.nombre,
                                      "ejeformativo": am.ejeformativo.nombre,
                                      "estado": estado,
                                      "creditos": am.creditos,
                                      "itinerario": am.itinerario,
                                      "itinerario_verbose": itinerario_verbose,
                                      "horas": am.horas,
                                      "cantidad_predecesoras": am.cantidad_predecesoras(),
                                      "totalrecordasignatura": totalmatriculaasignatura,
                                      "predecesoras": predecesoras_verbose,
                                      "puede_agregar": puede_agregar,
                                      })
                return JsonResponse({"result": "ok", "aSolicitudes": aSolicitudes, "aMotivos": aMotivos, "aPeriodoMatricula": aPeriodoMatricula, "aProcesos": aProcesos, "aProceso": aProceso, "has_error": has_error, "msg_error": mensaje_error, "aData": aData, "puede_solicitar": puede_solicitar})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error al cargar los datos. %s" % ex.__str__()})

        if action == 'viewSolicitud':
            try:
                if not 'id' in request.POST:
                    raise NameError(u"Parametro solicitud no encontrado")
                if not SolicitudMatriculaEspecial.objects.filter(pk=request.POST['id']).exists():
                    raise NameError(u"Solicitud no encontrada")
                eSolicitudMatriculaEspecial = SolicitudMatriculaEspecial.objects.filter(pk=request.POST['id'])[0]
                aSolicitud = {}
                aSolicitud['id'] = eSolicitudMatriculaEspecial.id
                aSolicitud['codigo'] = eSolicitudMatriculaEspecial.codigo
                aSolicitud['proceso_id'] = eSolicitudMatriculaEspecial.proceso.id
                aSolicitud['periodo'] = eSolicitudMatriculaEspecial.periodo.__str__()
                aSolicitud['periodo_id'] = eSolicitudMatriculaEspecial.periodo.id
                aSolicitud['descripcion'] = eSolicitudMatriculaEspecial.descripcion
                aSolicitud['motivo_id'] = eSolicitudMatriculaEspecial.motivo.id
                aSolicitud['motivo'] = eSolicitudMatriculaEspecial.motivo.__str__()
                aSolicitud['archivo'] = eSolicitudMatriculaEspecial.archivo.url if eSolicitudMatriculaEspecial.archivo else None
                aSolicitud['fecha'] = eSolicitudMatriculaEspecial.fecha.__str__()
                aSolicitud['hora'] = eSolicitudMatriculaEspecial.hora.__str__()
                aSolicitud['estado'] = eSolicitudMatriculaEspecial.estado.__str__()
                aSolicitud['estado_color'] = eSolicitudMatriculaEspecial.estado.color
                aSolicitud['estado_id'] = eSolicitudMatriculaEspecial.estado.id
                aAsignaturas = []
                if eSolicitudMatriculaEspecial.tiene_detalle_asignaturas():
                    for a in eSolicitudMatriculaEspecial.detalle_asignaturas():
                        aAsignaturas.append({"id": a.id,
                                             "asignatura": a.asignatura.__str__(),
                                             "asignatura_id": a.asignatura.id,
                                             "estado": a.get_estado_display(),
                                             "observacion": a.observacion})
                aSolicitud['asignaturas'] = aAsignaturas

                pasos = ConfigProcesoMatriculaEspecial.objects.filter(proceso=eSolicitudMatriculaEspecial.proceso, status=True).distinct()
                aPasos = []
                aux_pasos = ConfigProcesoMatriculaEspecial.objects.filter(pk__in=HistorialSolicitudMatriculaEspecial.objects.values_list("paso_id", flat=True).filter(solicitud=eSolicitudMatriculaEspecial, status=True).distinct()).distinct()
                for paso in pasos.order_by('orden'):
                    eHistorial = []
                    eHistorialSolicitud = HistorialSolicitudMatriculaEspecial.objects.filter(solicitud=eSolicitudMatriculaEspecial, paso=paso, status=True)
                    for historial in eHistorialSolicitud:
                        eHistorial.append({"id": historial.id,
                                           "fecha": historial.fecha.strftime('%d-%m-%Y'),
                                           "hora": historial.hora.strftime('%H:%M %p'),
                                           "estado": historial.estado.__str__(),
                                           "estado_color": historial.estado.color,
                                           "estado_id": historial.estado.id,
                                           "observacion": historial.observacion,
                                           "archivo": historial.archivo.url if historial.archivo else None,
                                           "coordinacion": historial.coordinacion.__str__() if historial.paso.es_coordinacion or historial.paso.es_usuario() else None,
                                           "departamento": historial.departamento.__str__() if historial.paso.es_departamento else None,
                                           "responsable": historial.responsable.__str__()})

                    eResponsables = []
                    if paso.es_departamento() or paso.es_coordinacion():
                        if paso.es_departamento():
                            if paso.tiene_responsables():
                                for responsable in paso.responsables():
                                    eResponsables.append({"id": responsable.id,
                                                          "departamento": responsable.departamento.__str__(),
                                                          "responsable": responsable.responsable.__str__()})
                        else:
                            if paso.tiene_responsables():
                                for responsable in paso.responsables().filter(carrera=eSolicitudMatriculaEspecial.inscripcion.carrera):
                                    eResponsables.append({"id": responsable.id,
                                                          "coordinacion": responsable.coordinacion.__str__(),
                                                          "responsable": responsable.responsable.__str__()})
                    clase = ""
                    active = False
                    if len(eHistorial) == 0:
                        clase = "disabled"
                        active = False
                    if eSolicitudMatriculaEspecial.paso.id == paso.id:
                        clase = "active"
                        active = True
                    aPasoAtras = {}
                    if pasos.filter(orden=paso.orden - 1).exists():
                        aAtras = ConfigProcesoMatriculaEspecial.objects.filter(pk__in=HistorialSolicitudMatriculaEspecial.objects.values_list("paso_id", flat=True).filter(solicitud=eSolicitudMatriculaEspecial, status=True).distinct(), orden__lte=paso.orden - 1).distinct()
                        if aAtras.exists():
                            aAtras = aAtras.order_by('-orden')[0]
                            aPasoAtras['id'] = aAtras.id
                            aPasoAtras['orden'] = aAtras.orden
                            aPasoAtras['class'] = "active"
                            aPasoAtras['active'] = True

                    aPasoSiguiente = {}
                    if pasos.filter(orden=paso.orden + 1).exists():
                        aSiguiente = ConfigProcesoMatriculaEspecial.objects.filter(pk__in=HistorialSolicitudMatriculaEspecial.objects.values_list("paso_id", flat=True).filter(solicitud=eSolicitudMatriculaEspecial, status=True).distinct(), orden__gte=paso.orden + 1).distinct()
                        if aSiguiente.exists():
                            aSiguiente = aSiguiente.order_by('orden')[0]
                            aPasoSiguiente['id'] = aSiguiente.id
                            aPasoSiguiente['orden'] = aSiguiente.orden
                            aPasoSiguiente['class'] = "active"
                            aPasoSiguiente['active'] = True

                    aPasos.append({"id": paso.id,
                                   "orden": paso.orden,
                                   "nombre": paso.nombre,
                                   "tipo_entidad": paso.tipo_entidad,
                                   "tipo_entidad_display": paso.get_tipo_entidad_display(),
                                   "tipo_validacion": paso.get_tipo_validacion_display(),
                                   "responsables": eResponsables,
                                   "historial": eHistorial,
                                   "class": clase,
                                   "active": active,
                                   "inicio": paso.orden == aux_pasos.values_list("orden").order_by('orden').first()[0],
                                   "fin": paso.orden == aux_pasos.values_list("orden").order_by('orden').last()[0],
                                   "siguiente": aPasoSiguiente,
                                   "atras": aPasoAtras
                                   })
                return JsonResponse({"result": "ok", "aSolicitud": aSolicitud, "aPasos": aPasos})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error al cargar los datos. %s" % ex.__str__()})

        if action == 'sendSolicitud':
            try:
                if not 'idpm' in request.POST:
                    raise NameError(u"Parametro periodo de matrícula no encontrado")
                if not PeriodoMatricula.objects.values("id").filter(pk=request.POST['idpm']).exists():
                    raise NameError(u"Periodo de matrícula no encontrado")
                ePeriodoMatricula = PeriodoMatricula.objects.get(pk=request.POST['idpm'])
                if not ePeriodoMatricula.valida_proceos_matricula_especial:
                    raise NameError(u"Proceso de matrícula especial no activo")
                ePeriodo = ePeriodoMatricula.periodo
                eProcesoMatriculaEspecial = ePeriodoMatricula.proceso_matricula_especial
                if not 'motivo' in request.POST:
                    raise NameError(u"Parametro de motivo no encontrado")
                if not MotivoMatriculaEspecial.objects.values("id").filter(pk=request.POST['motivo']).exists():
                    raise NameError(u"Motivo no encontrado")
                eMotivoMatriculaEspecial = MotivoMatriculaEspecial.objects.get(pk=request.POST['motivo'])
                if not eMotivoMatriculaEspecial.id in eProcesoMatriculaEspecial.motivos().values_list("id", flat=True).distinct():
                    raise NameError(u"Motivo no configurado en el proceso de matrícula especial")
                if not ConfigProcesoMatriculaEspecial.objects.filter(proceso=eProcesoMatriculaEspecial).exists():
                    raise NameError(u"Configuración del proceso matrícula especial no encontrado")
                if not EstadoMatriculaEspecial.objects.values("id").filter(accion=1).exists():
                    raise NameError(u"Estado no encontrado")
                eEstadoMatriculaEspecial = EstadoMatriculaEspecial.objects.filter()

                eConfigProcesos = ConfigProcesoMatriculaEspecial.objects.filter(proceso=eProcesoMatriculaEspecial)
                if not eConfigProcesos.values("id").filter(tipo_validacion=1).exists():
                    raise NameError(u"No se permiten solicitudes")
                eConfigProcesoSolicitud = eConfigProcesos.filter(tipo_validacion=1)[0]
                if eConfigProcesoSolicitud.obligar_archivo:
                    if not 'archivo' in request.FILES:
                        raise NameError(u"No se encontro archivo de justificación")
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
                if eConfigProcesoSolicitud.obligar_observacion:
                    if not 'descripcion' in request.POST:
                        raise NameError(u"No se encontro la descripción de la justificación")
                    if not request.POST['descripcion']:
                        raise NameError(u"Descripción de la justificación no debe estar vacia")
                descripcion = request.POST['descripcion']
                if not eEstadoMatriculaEspecial.values("id").filter(accion=1).exists():
                    raise NameError(u"Estado de solictud no configurado")
                SOLICITADO = eEstadoMatriculaEspecial.filter(accion=1)[0]
                codigo, secuencia = generar_codigo_matricula_especial(eProcesoMatriculaEspecial.sufijo)
                eSolicitudMatriculaEspecial = SolicitudMatriculaEspecial(proceso=eProcesoMatriculaEspecial,
                                                                         paso=eConfigProcesoSolicitud,
                                                                         codigo=codigo,
                                                                         secuencia=secuencia,
                                                                         inscripcion=inscripcion,
                                                                         periodo=ePeriodo,
                                                                         descripcion=descripcion,
                                                                         motivo=eMotivoMatriculaEspecial,
                                                                         archivo=archivo,
                                                                         fecha=datetime.now().date(),
                                                                         hora=datetime.now().time(),
                                                                         estado=SOLICITADO,
                                                                         )
                eSolicitudMatriculaEspecial.save(request)
                log(f'Adiciono solicitud de matrícula especial: {eSolicitudMatriculaEspecial.__str__()}', request, "add")
                asignaturas = json.loads(request.POST['asignaturas'])
                for am in AsignaturaMalla.objects.filter(pk__in=asignaturas):
                    eSolicitudMatriculaEspecialAsignatura = SolicitudMatriculaEspecialAsignatura(solicitud=eSolicitudMatriculaEspecial,
                                                                                                 asignatura=am,
                                                                                                 estado=1,
                                                                                                 )
                    eSolicitudMatriculaEspecialAsignatura.save(request)
                    log(f'Adiciono asignatura ({eSolicitudMatriculaEspecialAsignatura.asignatura.__str__()}) a la solicitud de matrícula especial: {eSolicitudMatriculaEspecial.__str__()}', request, "add")

                eHistorialSolicitudMatriculaEspecial = HistorialSolicitudMatriculaEspecial(solicitud=eSolicitudMatriculaEspecial,
                                                                                           paso=eConfigProcesoSolicitud,
                                                                                           fecha=eSolicitudMatriculaEspecial.fecha,
                                                                                           hora=eSolicitudMatriculaEspecial.hora,
                                                                                           estado=SOLICITADO,
                                                                                           departamento=None,
                                                                                           coordinacion=eSolicitudMatriculaEspecial.inscripcion.coordinacion,
                                                                                           responsable=eSolicitudMatriculaEspecial.inscripcion.persona,
                                                                                           observacion=eSolicitudMatriculaEspecial.descripcion,
                                                                                           archivo=archivo,
                                                                                           )
                eHistorialSolicitudMatriculaEspecial.save(request)
                log(f'Adiciono historial de solicitud de matrícula especial: {eHistorialSolicitudMatriculaEspecial.__str__()}', request, "add")
                eSolicitudMatriculaEspecial.estado = SOLICITADO
                eSolicitudMatriculaEspecial.paso = eHistorialSolicitudMatriculaEspecial.paso
                eSolicitudMatriculaEspecial.save(request)

                if not eEstadoMatriculaEspecial.values("id").filter(accion=4).exists():
                    raise NameError(u"Estado de solictud no configurado")
                EN_REVISION = eEstadoMatriculaEspecial.filter(accion=4)[0]
                if not eConfigProcesos.values("id").filter(tipo_validacion=2).exists():
                    raise NameError(u"No existe configuración de departamento de responsable de la revisión")
                eConfigProcesoRevisar = eConfigProcesos.filter(tipo_validacion=2)[0]
                if not ConfigProcesoMatriculaEspecialAsistente.objects.values("id").filter(configuracion=eConfigProcesoRevisar, status=True).exists():
                    raise NameError(u"Responsable del departamento de revisón de matrícula especial no se encontro")
                responsable = None
                departamento = None
                if eConfigProcesoRevisar.es_departamento():
                    eConfigProcesoResponsable = ConfigProcesoMatriculaEspecialAsistente.objects.filter(configuracion=eConfigProcesoRevisar, status=True)[0]
                    eHistorialSolicitudMatriculaEspecial = HistorialSolicitudMatriculaEspecial(solicitud=eSolicitudMatriculaEspecial,
                                                                                               paso=eConfigProcesoRevisar,
                                                                                               fecha=datetime.now().date(),
                                                                                               hora=datetime.now().time(),
                                                                                               estado=EN_REVISION,
                                                                                               departamento=eConfigProcesoResponsable.departamento,
                                                                                               coordinacion=None,
                                                                                               responsable=eConfigProcesoResponsable.responsable,
                                                                                               observacion='ASIGNACIÓN AUTOMATICA MEDIANTE EL SGA AL PROCESO DE MATRÍCULA ESPECIAL',
                                                                                               archivo=None,
                                                                                               )
                    responsable = eConfigProcesoResponsable.responsable
                    departamento = eConfigProcesoResponsable.departamento
                elif eConfigProcesoRevisar.es_coordinacion():
                    if not ConfigProcesoMatriculaEspecialAsistente.objects.filter(configuracion=eConfigProcesoRevisar, status=True, coordinacion=inscripcion.coordinacion, carrera=inscripcion.carrera).exists():
                        raise NameError(u"No existe responsable de facultad que atienda la solicitud")
                    eConfigProcesoResponsable = ConfigProcesoMatriculaEspecialAsistente.objects.filter(configuracion=eConfigProcesoRevisar, status=True, coordinacion=inscripcion.coordinacion, carrera=inscripcion.carrera)[0]
                    eHistorialSolicitudMatriculaEspecial = HistorialSolicitudMatriculaEspecial(solicitud=eSolicitudMatriculaEspecial,
                                                                                               paso=eConfigProcesoRevisar,
                                                                                               fecha=datetime.now().date(),
                                                                                               hora=datetime.now().time(),
                                                                                               estado=EN_REVISION,
                                                                                               departamento=None,
                                                                                               coordinacion=eConfigProcesoResponsable.coordinacion,
                                                                                               responsable=eConfigProcesoResponsable.responsable,
                                                                                               observacion='ASIGNACIÓN AUTOMATICA MEDIANTE EL SGA AL PROCESO DE MATRÍCULA ESPECIAL',
                                                                                               archivo=None,
                                                                                               )
                    responsable = eConfigProcesoResponsable.responsable
                    departamento = eConfigProcesoResponsable.coordinacion
                else:
                    raise NameError(u"No se encontro responsables para la solicitud")
                eSolicitudMatriculaEspecial.estado = EN_REVISION
                eSolicitudMatriculaEspecial.paso = eHistorialSolicitudMatriculaEspecial.paso
                eSolicitudMatriculaEspecial.save(request)
                notificacion = Notificacion(titulo=f"Registro de Nro.{eSolicitudMatriculaEspecial.codigo} solicitud de matrícula especial",
                                            cuerpo=f"Tu solicitud de matrícula especial fue recibida y esta en proceso de revisión en {departamento.__str__()}",
                                            destinatario=eSolicitudMatriculaEspecial.inscripcion.persona,
                                            url=f"/alu_solicitudmatricula/especial?id={eSolicitudMatriculaEspecial.id}",
                                            fecha_hora_visible=datetime.now() + timedelta(days=1),
                                            content_type=ContentType.objects.get_for_model(eSolicitudMatriculaEspecial),
                                            object_id=eSolicitudMatriculaEspecial.id,
                                            prioridad=1,
                                            app_label='sga')
                notificacion.save(request)
                notificacion = Notificacion(titulo=f"Nro.{eSolicitudMatriculaEspecial.codigo} de solicitud de matrícula especial",
                                            cuerpo=f"Tiene una solicitud de matrícula especial de {eSolicitudMatriculaEspecial.inscripcion.persona.__str__()}",
                                            destinatario=responsable,
                                            url=f"/adm_solicitudmatricula/especial?action=solicitudes&id={eSolicitudMatriculaEspecial.id}",
                                            fecha_hora_visible=datetime.now() + timedelta(days=7),
                                            content_type=ContentType.objects.get_for_model(eSolicitudMatriculaEspecial),
                                            object_id=eSolicitudMatriculaEspecial.id,
                                            prioridad=1,
                                            app_label='sga')
                notificacion.save(request)
                eHistorialSolicitudMatriculaEspecial.save(request)
                log(f'Adiciono historial de solicitud de matrícula especial: {eHistorialSolicitudMatriculaEspecial.__str__()}', request, "add")

                return JsonResponse({"result": "ok", "mensaje": u"Solicitud guardada correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar solicitud. %s" % ex.__str__()})

        if action == 'cancelarSolicitud':
            try:
                if not 'ids' in request.POST:
                    raise NameError(u"Parametro solicitud no encontrado")
                if not SolicitudMatriculaEspecial.objects.values("id").filter(pk=request.POST['ids']).exists():
                    raise NameError(u"Solicitud no encontrada")
                eSolicitudMatriculaEspecial = SolicitudMatriculaEspecial.objects.get(pk=request.POST['ids'])
                eProcesoMatriculaEspecial = eSolicitudMatriculaEspecial.proceso
                if not EstadoMatriculaEspecial.objects.values("id").filter(status=True).exists():
                    raise NameError(u"No se encontro estados configurado")
                eEstadoMatriculaEspecial = EstadoMatriculaEspecial.objects.filter(status=True)
                if not eEstadoMatriculaEspecial.values("id").filter(accion=6).exists():
                    raise NameError(u"Estado de solictud no configurado")
                CANCELAR = eEstadoMatriculaEspecial.filter(accion=6)[0]
                eHistorialSolicitudMatriculaEspecial = HistorialSolicitudMatriculaEspecial(solicitud=eSolicitudMatriculaEspecial,
                                                                                           paso=eSolicitudMatriculaEspecial.paso,
                                                                                           fecha=datetime.now().date(),
                                                                                           hora=datetime.now().time(),
                                                                                           estado=CANCELAR,
                                                                                           departamento=None,
                                                                                           coordinacion=eSolicitudMatriculaEspecial.inscripcion.coordinacion,
                                                                                           responsable=eSolicitudMatriculaEspecial.inscripcion.persona,
                                                                                           observacion='ESTUDIANTE CANCELO SOLICITUD DE MATRÍCULA ESPECIAL',
                                                                                           archivo=None,
                                                                                           )
                eHistorialSolicitudMatriculaEspecial.save(request)
                log(f'Adiciono historial de solicitud de matrícula especial: {eHistorialSolicitudMatriculaEspecial.__str__()}', request, "add")
                if not ConfigProcesoMatriculaEspecial.objects.values("id").filter(proceso=eProcesoMatriculaEspecial).exists():
                    raise NameError(u"No existe configuración activa para el proceso de matrícula especial")
                eConfigProcesosMatriculaEspecial = ConfigProcesoMatriculaEspecial.objects.filter(proceso=eProcesoMatriculaEspecial)
                eConfigProcesoCancelar = eConfigProcesosMatriculaEspecial.filter(tipo_validacion=4)[0]
                if not eEstadoMatriculaEspecial.values("id").filter(accion=7).exists():
                    raise NameError(u"Estado de solictud no configurado")
                NOTIFICAR = eEstadoMatriculaEspecial.filter(accion=7)[0]
                eHistorialSolicitudMatriculaEspecial = HistorialSolicitudMatriculaEspecial(solicitud=eSolicitudMatriculaEspecial,
                                                                                           paso=eConfigProcesoCancelar,
                                                                                           fecha=datetime.now().date(),
                                                                                           hora=datetime.now().time(),
                                                                                           estado=NOTIFICAR,
                                                                                           departamento=None,
                                                                                           coordinacion=eSolicitudMatriculaEspecial.inscripcion.coordinacion,
                                                                                           responsable=eSolicitudMatriculaEspecial.inscripcion.persona,
                                                                                           observacion='Notificación automatica mediante SGA',
                                                                                           archivo=None,
                                                                                           )
                eHistorialSolicitudMatriculaEspecial.save(request)
                eSolicitudMatriculaEspecial.estado = CANCELAR
                eSolicitudMatriculaEspecial.paso = eHistorialSolicitudMatriculaEspecial.paso
                eSolicitudMatriculaEspecial.save(request)
                if eSolicitudMatriculaEspecial.tiene_detalle_asignaturas():
                    for am in eSolicitudMatriculaEspecial.detalle_asignaturas():
                        am.estado = 5
                        am.observacion = 'ESTUDIANTE CANCELO SOLICITUD DE MATRÍCULA ESPECIAL'
                        am.save(request)
                log(f'Adiciono historial de solicitud de matrícula especial: {eHistorialSolicitudMatriculaEspecial.__str__()}', request, "add")
                notificacion = Notificacion(titulo=f"Solicitud de matrícula especial Nro.{eSolicitudMatriculaEspecial.codigo} se cancelo",
                                            cuerpo=f"Tu solicitud de matrícula especial Nro.{eSolicitudMatriculaEspecial.codigo} se cancelo",
                                            destinatario=eSolicitudMatriculaEspecial.inscripcion.persona,
                                            url=f"/alu_solicitudmatricula/especial?id={eSolicitudMatriculaEspecial.id}",
                                            fecha_hora_visible=datetime.now() + timedelta(days=1),
                                            content_type=ContentType.objects.get_for_model(eSolicitudMatriculaEspecial),
                                            object_id=eSolicitudMatriculaEspecial.id,
                                            prioridad=1,
                                            app_label='sga'
                                            )
                notificacion.save(request)
                return JsonResponse({"result": "ok", "mensaje": u"Solicitud cancelada correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al cancelar solicitud. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Solicitudes de matrícula especial'
                data['inscripcion'] = inscripcion
                data['inscripcionmalla'] = inscripcion.malla_inscripcion()
                data['solicitudes'] = SolicitudMatriculaEspecial.objects.filter(status=True)
                return render(request, "alu_solicitudmatricula/especial/view.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                return render(request, "alu_solicitudmatricula/error.html", data)
