# coding=utf-8
from __future__ import division

import json
import sys
import uuid
import random
import string
from hashlib import md5
import redis as Redis
from django.core.cache import cache
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType
from mobi.decorators import detect_mobile

from bd.models import UserToken
from secrets import token_hex

from decorators import secure_module, last_access, inhouse_check, f_tiene_solicitud_apertura_clase
from inno.models import HorarioTutoriaAcademica, LogIngresoAsistenciaLeccion, RegistroClaseTutoriaDocente
from inno.serializers.HorarioExamen import AulaSerializer, ProfesorMateriaSerializer, ProfesorSerializer, \
    AdministrativoSerializer, MateriaAsignadaSerializer
from settings import EMAIL_DOMAIN, REDIS_HOST, REDIS_PASSWORD, REDIS_PORT, REDIS_BD, DEBUG
from sga.clases_threading import ActualizaAsistencia
from sga.funciones import log, null_to_numeric, variable_valor
from sga.models import miinstitucion, CUENTAS_CORREOS, Persona, Notificacion, Materia, PerfilUsuario, Modulo, \
    LeccionGrupo, Clase, ProfesorMateria, DetalleDistributivo, ComplexivoClase, Sesion, ComplexivoLeccion, \
    AsistenciaLeccion, MateriaAsignada, ClaseActividad, TIPOHORARIO_COLOURS, IpPermitidas, Aula, Profesor, \
    Administrativo, DetalleModeloEvaluativo, HorarioExamenDetalle, HorarioExamenDetalleAlumno, \
    InscripcionEncuestaGrupoEstudiantes, Modalidad
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from datetime import datetime, timedelta

unicode = str


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@last_access
@transaction.atomic()
@detect_mobile
def view(request):
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'loadInitialDataHorarioDocente':
            return view_pro_horarios_docente(request)

        if action == 'loadInitialDataHorarioEstudiante':
            return view_pro_horarios_estudiante(request)

        if action == 'enterClassEstudiante':
            return view_enter_class_estudiante(request)

        if action == 'checkOpenClassContinue':
            try:
                lecciongrupo = LeccionGrupo.objects.get(pk=request.POST['id'])
                asistencias = []
                periodo = request.session['periodo']
                ePeriodoAcademia = periodo.get_periodoacademia()
                if ePeriodoAcademia.utiliza_asistencia_redis:
                    for eLeccion in lecciongrupo.mis_leciones():
                        key_cache_leccion = f'data_asistencias_leccion_id_{encrypt(eLeccion.id)}'
                        if cache.has_key(key_cache_leccion):
                            c_data = cache.get(key_cache_leccion)
                            for element in c_data:
                                asistencias.append(element)
                        # for asistencia in leccion.mis_asistencias():
                        #     asistencias.append({"id": asistencia.id,
                        #                         "leccion_id": asistencia.leccion_id,
                        #                         "materiaasignada": asistencia.materiaasignada_id,
                        #                         "asistenciafinal": null_to_numeric(asistencia.materiaasignada.asistenciafinal, 0),
                        #                         "porciento_requerido": asistencia.materiaasignada.porciento_requerido(),
                        #                         "asistenciajustificada": asistencia.asistenciajustificada,
                        #                         "asistio": asistencia.asistio,
                        #                         "virtual": asistencia.virtual,
                        #                         "virtual_fecha": asistencia.virtual_fecha.__str__() if asistencia.virtual_fecha else None,
                        #                         "virtual_hora": asistencia.virtual_hora.strftime("%H:%M:%S") if asistencia.virtual_hora else None,
                        #                         "ip_private": asistencia.ip_private,
                        #                         "ip_public": asistencia.ip_public,
                        #                         "browser": asistencia.browser,
                        #                         "ops": asistencia.ops,
                        #                         "screen_size": asistencia.screen_size,
                        #                         })
                otraslecciones = LeccionGrupo.objects.filter(profesor_id=lecciongrupo.profesor_id, abierta=True).exclude(id=lecciongrupo.id)
                otrasleccionesid = 0
                if otraslecciones:
                    otrasleccionesid = otraslecciones[0].id
                return JsonResponse({"result": "ok", "abierta": lecciongrupo.abierta, "puede_cerrar_leccion_grupo": lecciongrupo.puede_cerrar_leccion_grupo(), "otras": otrasleccionesid, "asistencias": asistencias})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": "Ocurrio un error al cargar los datos: % " % ex.__str__()})

        if action == 'loadListAulas':
            try:
                aData= {}
                eAulas = Aula.objects.filter(status=True)
                aData['eAulas'] = AulaSerializer(eAulas, many=True).data if eAulas.values("id").exists() else []
                return JsonResponse({"result": "ok", "aData": aData})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        if action == 'loadListResponsableHorarioExamen':
            try:
                aData= {}
                if not 'tiporesponsable' in request.POST:
                    raise NameError('Tipo de responsable no encontrado')
                if not 'idm' in request.POST:
                    raise NameError('Materia no encontrada')
                eMateria = Materia.objects.get(pk=encrypt(request.POST['idm']))
                tiporesponsable = int(request.POST['tiporesponsable'])
                if tiporesponsable == 0:
                    aData['eResponsables'] = []
                elif tiporesponsable == 1:
                    eProfesores = eMateria.profesores_materia()
                    aData['eResponsables'] = ProfesorMateriaSerializer(eProfesores, many=True).data if eProfesores.values("id").exists() else []
                elif tiporesponsable == 2:
                    eProfesorMaterias = ProfesorMateria.objects.filter(activo=True, status=True, materia__nivel__periodo=eMateria.nivel.periodo)
                    eProfesores = Profesor.objects.filter(pk__in=eProfesorMaterias.values_list('profesor_id', flat=True))
                    aData['eResponsables'] = ProfesorSerializer(eProfesores, many=True).data if eProfesores.values("id").exists() else []
                elif tiporesponsable == 3:
                    eAdministrativos = Administrativo.objects.filter(status=True, activo=True)
                    aData['eResponsables'] = AdministrativoSerializer(eAdministrativos, many=True).data if eAdministrativos.values("id").exists() else []
                return JsonResponse({"result": "ok", "aData": aData})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        if action == 'loadListEstudiantes':
            try:
                aData= {}
                encuesta_id = 24
                if not 'idm' in request.POST:
                    raise NameError('Materia no encontrada')
                if not 'iddm' in request.POST:
                    raise NameError('Detalle de examen no encontrado')
                # if not 'ida' in request.POST:
                #     raise NameError('Aula no encontrada')
                eMateria = Materia.objects.get(pk=encrypt(request.POST['idm']))
                eDetalleModeloEvaluativo = DetalleModeloEvaluativo.objects.get(pk=encrypt(request.POST['iddm']))
                # eAula = Aula.objects.get(pk=encrypt(request.POST['ida']))
                eHorarios = HorarioExamenDetalle.objects.filter(horarioexamen__materia=eMateria, status=True, horarioexamen__status=True, horarioexamen__detallemodelo=eDetalleModeloEvaluativo).distinct().order_by('horainicio')
                eAlumnos = MateriaAsignada.objects.filter(status=True, retiramateria=False, materia=eMateria, matricula__retiradomatricula=False, matricula__status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2', 'matricula__inscripcion__persona__nombres')
                eAsignados = HorarioExamenDetalleAlumno.objects.filter(horarioexamendetalle__in=eHorarios, status=True, materiaasignada__in=eAlumnos)
                eAlumnos = eAlumnos.exclude(pk__in=eAsignados.values_list('materiaasignada_id', flat=True))
                aData['eAlumnos'] = []
                if eAlumnos.values("id").exists():
                    aData['eAlumnos'] = MateriaAsignadaSerializer(eAlumnos, many=True).data
                return JsonResponse({"result": "ok", "aData": aData})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})


def view_pro_horarios_docente(request):
    try:
        persona = request.session['persona']
        periodo = request.session['periodo']
        perfilprincipal = request.session['perfilprincipal']
        if not perfilprincipal.es_profesor():
            NameError(u"Solo los perfiles de profesores pueden ingresar al modulo.")
        profesor = perfilprincipal.profesor
        tiene_solicitud_apertura_clase = f_tiene_solicitud_apertura_clase(profesor, periodo)
        hoy = datetime.now().date()
        horaactual = datetime.now().time()
        numerosemanaactual = datetime.today().isocalendar()[1]
        ePeriodoAcademia = periodo.get_periodoacademia()
        aSesiones = []
        aLeccionClases = []
        aMateriasNoProgramadas = []
        aClaseAbierta = {}
        clasesabiertas = LeccionGrupo.objects.filter(status=True, profesor=profesor, abierta=True, lecciones__clase__materia__nivel__periodo=periodo).order_by('-fecha', '-horaentrada')
        clasesabiertasCount = len(clasesabiertas)
        disponible = clasesabiertasCount == 0
        if clasesabiertas:
            clasesabierta = clasesabiertas[0]
            aClaseAbierta = {"id": clasesabierta.id}
            # ------VERIFICA QUE AL MENDOS TENGA UN PROFESOR DE CLASE NO VALIDA HORARIO---------
            mislecciones = clasesabierta.mis_leciones()
            if len(mislecciones) > 1:
                if not clasesabierta.verificar_profemate_novalidahor():
                    mislecciones = None
            else:
                mislecciones = None
            if mislecciones:
                for leccion in mislecciones:
                    url = None
                    if leccion.clase.materia.tieneurlwebex(leccion.clase.profesor):
                        url = f"https://unemi.webex.com/meet/{leccion.clase.profesor.persona.usuario}"
                    elif leccion.clase.profesor.urlzoom:
                        url = leccion.clase.profesor.urlzoom
                    aLeccionClases.append({"id": encrypt(leccion.id),
                                           "abierta": leccion.abierta,
                                           "nombre_mostrar_solo": leccion.clase.materia.nombre_mostrar_solo(),
                                           "url": url
                                           })
            # --------------------------------------------------------------------
        if not disponible:
            if clasesabiertasCount > 1:
                for clase in clasesabiertas[1:]:
                    clase.abierta = False
                    clase.save()
            lecciongrupo = LeccionGrupo.objects.filter(status=True, profesor=profesor, abierta=True)[0]
        diaactual = hoy.isocalendar()[2]
        semana = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
        semanatutoria = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sábado'], [7, 'Domingo']]
        clases = Clase.objects.filter(status=True, activo=True, materia__fechafinasistencias__gte=hoy, materia__status=True,
                                      materia__nivel__visibledistributivomateria=True, fin__gte=hoy,
                                      materia__nivel__periodo_id=periodo.id, materia__nivel__periodo__visible=True,
                                      materia__nivel__periodo__visiblehorario=True,
                                      materia__profesormateria__profesor_id=profesor.id,
                                      materia__profesormateria__principal=True, materia__visiblehorario=True,
                                      materia__profesormateria__tipoprofesor_id__in=[1, 2, 5, 7, 8, 10, 11, 12, 13, 14, 15, 16,17, 22],
                                      tipoprofesor_id__in=[1, 2, 5, 7, 8, 10, 11, 12, 13, 14, 15, 16,17,22]).order_by('inicio')
        clasesayudante = Clase.objects.values_list('id').filter(status=True, activo=True, materia__status=True,
                                                                materia__fechafinasistencias__gte=hoy,
                                                                materia__nivel__visibledistributivomateria=True,
                                                                fin__gte=hoy, materia__nivel__periodo_id=periodo.id,
                                                                materia__nivel__periodo__visible=True,
                                                                materia__nivel__periodo__visiblehorario=True,
                                                                materia__profesormateria__profesor_id=profesor.id,
                                                                profesorayudante_id=profesor.id,
                                                                materia__visiblehorario=True, materia__profesormateria__principal=True).order_by('inicio')

        clases_turnos = profesor.extraer_clases_y_turnos_practica(datetime.now().date(), periodo)
        clases = Clase.objects.filter(Q(pk__in=clases.values_list('id')) | Q(pk__in=clasesayudante) | Q(pk__in=clases_turnos[0].values_list('id'))).distinct()
        debe_tener_link_zoom = clases.values("id").filter(tipohorario__in=[2, 7, 8, 9]).exists()

        materiasnoprogramadas = ProfesorMateria.objects.filter(status=True, profesor_id=profesor.id, materia__status=True,
                                                               materia__nivel__periodo__visible=True,
                                                               materia__nivel__visibledistributivomateria=True,
                                                               materia__nivel__periodo__visiblehorario=True,
                                                               materia__nivel__periodo_id=periodo.id,
                                                               materia__visiblehorario=True,
                                                               tipoprofesor_id__in=[11, 12, 1, 2, 5, 8, 7, 10, 14, 15, 13, 17, 16, 22],
                                                               hasta__gt=hoy, activo=True, principal=True).exclude(materia_id__in=clases.values_list("materia_id", flat=True), profesor=profesor)
        for mnp in materiasnoprogramadas:
            aMateriasNoProgramadas.append({"id": mnp.materia.id,
                                           "materia": mnp.materia.nombre_completo(),
                                           })

        idturnostutoria = []
        if DetalleDistributivo.objects.filter(distributivo__profesor_id=profesor.id, distributivo__periodo_id=periodo.id, criteriodocenciaperiodo__criterio__procesotutoriaacademica=True).exists():
            if HorarioTutoriaAcademica.objects.filter(status=True, profesor_id=profesor.id, periodo_id=periodo.id).exists():
                idturnostutoria = HorarioTutoriaAcademica.objects.values_list('turno_id').filter(status=True, profesor_id=profesor.id, periodo_id=periodo.id).distinct()
        clasecomplexivo = complexivo = ComplexivoClase.objects.filter(status=True, activo=True, materia__profesor__profesorTitulacion_id=profesor.id, materia__status=True)

        idturnosactivdaddocente = ClaseActividad.objects.values_list('turno_id', flat=True).filter(detalledistributivo__distributivo__profesor_id=profesor.id, detalledistributivo__distributivo__periodo_id=periodo.id, estadosolicitud=2).distinct().order_by('inicio')
        sesiones = Sesion.objects.filter(Q(turno__id__in=clases.values_list('turno__id').distinct()) | Q(turno__complexivoclase__in=complexivo) | Q(turno__id__in=idturnostutoria) | Q(turno__id__in=idturnosactivdaddocente)).distinct()
        complexivoabierto = ComplexivoLeccion.objects.filter(status=True, abierta=True, clase__materia__profesor__profesorTitulacion_id=profesor.id)
        disponiblecomplexivo = len(complexivoabierto) == 0
        aTipoHorarios = []
        for sesion in sesiones:
            turnos = []
            turnosactivostutoria = []
            if sesion.id != 15:
                for turno in sesion.turnos_clasehorario(clases, clasecomplexivo):
                    semana_turno = []
                    for dia in semana:
                        # if dia[0] == 1 and sesion.id == 5:
                        #     print("pasa")
                        # if dia[0] == 5:
                        #     print("pasa")
                        clasesactuales = []
                        aux_clasesactuales = turno.horario_profesor_actual_horario(dia[0], profesor, periodo)
                        for clase in aux_clasesactuales:
                            # if clase.id == 236941 and dia[0] == 1:
                            #     print(f"Prueba f{clase.id} -> {clase.subirenlace}")
                            # if clase.id == 219251:
                            #     print(f"Prueba f{clase.id} -> {clase.subirenlace}")
                            # style_card = f"background-color: {clase.get_display_background_tipohorario_colours()} color: {clase.get_display_color_text_tipohorario_colours()}
                            style_card = f"background-color: white !important; color: #264763 !important; border-left: 5px solid {clase.get_display_color_text_tipohorario_colours()} !important;"
                            if not clase.tipohorario in [x[0] for x in aTipoHorarios]:
                                for num in TIPOHORARIO_COLOURS:
                                    if num[0] == clase.tipohorario:
                                        aTipoHorarios.append(num)
                            fechacompara = clase.compararfecha(numerosemanaactual)
                            tieneferiado = periodo.es_feriado(fechacompara, clase.materia)
                            action_button = {}
                            coordinacion = clase.materia.coordinacion()
                            modalidad = clase.materia.asignaturamalla.malla.modalidad
                            if clase.materia.modeloevaluativo_id in [27, 64] and clase.materia.asignaturamalla.transversal:
                                modalidad = Modalidad.objects.get(id=3)
                            if coordinacion is None:
                                raise NameError(u"Clase no tiene coordinación configurada")
                            if not coordinacion.id in [1, 2, 3, 4, 5, 9, 7, 10, 12]:
                                raise NameError(u"Coordinación: %s no esta configurada en horario" % coordinacion.__str__())

                            if coordinacion.id in [1, 2, 3, 4, 5, 12]:
                                # 1 => PRESENCIAL
                                if clase.tipohorario == 1:
                                    if not tieneferiado:
                                        if aux_clasesactuales[0].tipoprofesor.id != 8:
                                            aula = clase.aula
                                            puede_abrir_fuera = True
                                            if ePeriodoAcademia.valida_asistencia_in_home and not tiene_solicitud_apertura_clase:
                                                if aula and aula.bloque and aula.bloque.in_home:
                                                    if not inhouse_check(request, valida_clase=True):
                                                        puede_abrir_fuera = False
                                            if disponible and puede_abrir_fuera:
                                                if aux_clasesactuales[0].disponible(ePeriodoAcademia=ePeriodoAcademia):
                                                    clase_ids = (",".join([str(x.id) for x in turno.horario_profesor_actual_horario(dia[0], profesor, periodo, False, False)]))
                                                    url = None
                                                    if clase.materia.tieneurlwebex(clase.profesor):
                                                        url = f"https://unemi.webex.com/meet/{clase.profesor.persona.usuario}"
                                                    elif clase.profesor.urlzoom:
                                                        url = clase.profesor.urlzoom
                                                    action_button = {
                                                        "action": "open_class",
                                                        "url": url,
                                                        "parametro": clase_ids,
                                                        "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                        "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                        "verbose": u"Comenzar Clase",
                                                        "icon": u"fa fa-plus",
                                                        "style": u"background-color: #fc7e00 !important; color: #fff;",
                                                        }

                                # 2 => CLASE VIRTUAL SINCRÓNICA
                                # 8 => CLASE REFUERZO SINCRÓNICA
                                # 7 => CLASE VIRTUAL ASINCRÓNICA
                                # 9 => CLASE REFUERZO ASINCRÓNICA
                                elif clase.tipohorario in [2, 7, 8, 9]:
                                    if not tieneferiado:
                                        if modalidad:
                                            if modalidad.id in [1, 2]:
                                                """
                                                    EN MODALIDAD PRESENCIAL Y SEMIPRESENCIAL 
                                                    * LAS CLASES SINCRONICAS SE APERTURA Y LUEGO SE SUBE EL VIDEO QUE SE CONVIERTE EN CLASE ASINCRONICA
                                                """
                                                if clase.tipohorario in [2, 8]:
                                                    if disponible:
                                                        if aux_clasesactuales[0].disponible(ePeriodoAcademia=ePeriodoAcademia):
                                                            url = None
                                                            if clase.materia.tieneurlwebex(clase.profesor):
                                                                url = f"https://unemi.webex.com/meet/{clase.profesor.persona.usuario}"
                                                            elif clase.profesor.urlzoom:
                                                                url = clase.profesor.urlzoom
                                                            clase_ids = (",".join([str(x.id) for x in turno.horario_profesor_actual_horario(dia[0], profesor, periodo, False, False)]))
                                                            action_button = {
                                                                "action": "open_class",
                                                                "url": url,
                                                                "parametro": clase_ids,
                                                                "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                "verbose": u"Comenzar Clase",
                                                                "icon": u"fa fa-plus",
                                                                "style": u"background-color: #fc7e00 !important; color: #fff;",
                                                                }
                                                        else:
                                                            if clase.subirenlace:
                                                                clasesactualesasincronica = clase.horario_profesor_actualasincronica(numerosemanaactual)
                                                                if not tieneferiado:
                                                                    if not clasesactualesasincronica.values("id").exists():
                                                                        if fechacompara and fechacompara <= hoy:
                                                                            if fechacompara and fechacompara < hoy:
                                                                                action_button = {
                                                                                    "action": "create_video",
                                                                                    "url": None,
                                                                                    "parametro": None,
                                                                                    "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                                    "modalidad_display":  ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                                    "verbose": "Subir video",
                                                                                    "icon": u"fa fa-comments",
                                                                                    "style": None,
                                                                                    }
                                                                            if fechacompara and fechacompara == hoy:
                                                                                if turno.termina < horaactual:
                                                                                    action_button = {
                                                                                        "action": "create_video",
                                                                                        "url": None,
                                                                                        "parametro": None,
                                                                                        "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                                        "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                                        "verbose": "Subir video",
                                                                                        "icon": u"fa fa-comments",
                                                                                        "style": None,
                                                                                        }
                                                                    else:
                                                                        url = f"https://aulagradoa.unemi.edu.ec/mod/url/view.php?id={clasesactualesasincronica[0].idforomoodle}"
                                                                        action_button = {
                                                                            "action": "view_video",
                                                                            "url": url,
                                                                            "parametro": None,
                                                                            "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                            "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                            "verbose": "Ver video",
                                                                            "icon": u"fa fa-link",
                                                                            # "style": u"background-color: #49afcd !important;",
                                                                            }
                                                    elif clase.subirenlace:
                                                        clasesactualesasincronica = clase.horario_profesor_actualasincronica(numerosemanaactual)
                                                        if not tieneferiado:
                                                            if not clasesactualesasincronica:
                                                                if fechacompara and fechacompara <= hoy:
                                                                    if fechacompara and fechacompara < hoy:
                                                                        action_button = {
                                                                            "action": "create_video",
                                                                            "url": None,
                                                                            "parametro": None,
                                                                            "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                            "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                            "verbose": "Subir video",
                                                                            "icon": u"fa fa-comments",
                                                                            "style": None,
                                                                            }
                                                                    if fechacompara and fechacompara == hoy:
                                                                        if turno.termina < horaactual:
                                                                            action_button = {
                                                                                "action": "create_video",
                                                                                "url": None,
                                                                                "parametro": None,
                                                                                "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                                "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                                "verbose": "Subir video",
                                                                                "icon": u"fa fa-comments",
                                                                                "style": None,
                                                                                }
                                                            else:
                                                                url = f"https://aulagradoa.unemi.edu.ec/mod/url/view.php?id={clasesactualesasincronica[0].idforomoodle}"
                                                                action_button = {
                                                                    "action": "view_video",
                                                                    "url": url,
                                                                    "parametro": None,
                                                                    "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                    "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                    "verbose": "Ver video",
                                                                    "icon": u"fa fa-link",
                                                                    # "style": u"background-color: #49afcd !important;",
                                                                    }
                                            elif modalidad.id in [3]:
                                                """
                                                    EN MODALIDAD EN LINEA 
                                                    * LAS CLASES SINCRONICAS SE APERTURA LA CLASE Y LUEGO SE SUBE EL VIDEO QUE SE MANTIENE EN CLASE SINCRONICA
                                                    * LAS CLASES ASINCRONICAS SE SUBE EL VIDEO EN CLASE ASINCRONICA SE APERTURA LA CLASE, EL ESTUDIANTE PUEDE INGRESAR A VER EL VIDEO DURANTE LA SEMANA
                                                """
                                                if clase.tipohorario in [2, 8]:
                                                    if disponible:
                                                        if aux_clasesactuales[0].disponible(ePeriodoAcademia=ePeriodoAcademia):
                                                            url = None
                                                            if clase.materia.tieneurlwebex(clase.profesor):
                                                                url = f"https://unemi.webex.com/meet/{clase.profesor.persona.usuario}"
                                                            elif clase.profesor.urlzoom:
                                                                url = clase.profesor.urlzoom
                                                            clase_ids = (",".join([str(x.id) for x in turno.horario_profesor_actual_horario(dia[0], profesor, periodo, False, False)]))
                                                            action_button = {
                                                                "action": "open_class",
                                                                "url": url,
                                                                "parametro": clase_ids,
                                                                "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                "verbose": u"Comenzar Clase",
                                                                "icon": u"fa fa-plus",
                                                                "style": u"background-color: #fc7e00 !important; color: #fff;",
                                                                }
                                                        else:
                                                            if clase.subirenlace:
                                                                clasesactualessincronica = clase.horario_profesor_actualsincronica(numerosemanaactual)
                                                                if not tieneferiado:
                                                                    if not clasesactualessincronica.values("id").exists():
                                                                        if fechacompara and fechacompara <= hoy:
                                                                            if fechacompara and fechacompara < hoy:
                                                                                action_button = {
                                                                                    "action": "create_video",
                                                                                    "url": None,
                                                                                    "parametro": None,
                                                                                    "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                                    "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                                    "verbose": "Subir video",
                                                                                    "icon": u"fa fa-comments",
                                                                                    "style": None,
                                                                                    }
                                                                            if fechacompara and fechacompara == hoy:
                                                                                if turno.termina < horaactual:
                                                                                    action_button = {
                                                                                        "action": "create_video",
                                                                                        "url": None,
                                                                                        "parametro": None,
                                                                                        "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                                        "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                                        "verbose": "Subir video",
                                                                                        "icon": u"fa fa-comments",
                                                                                        "style": None,
                                                                                        }
                                                                    else:
                                                                        url = f"https://aulagradob.unemi.edu.ec/mod/url/view.php?id={clasesactualessincronica[0].idforomoodle}"
                                                                        action_button = {
                                                                            "action": "view_video",
                                                                            "url": url,
                                                                            "parametro": None,
                                                                            "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                            "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                            "verbose": "Ver video",
                                                                            "icon": u"fa fa-link",
                                                                            # "style": u"background-color: #49afcd "
                                                                            # u"!important;",
                                                                            }
                                                    elif clase.subirenlace:
                                                        clasesactualessincronica = clase.horario_profesor_actualsincronica(numerosemanaactual)
                                                        if not tieneferiado:
                                                            if not clasesactualessincronica:
                                                                if fechacompara and fechacompara <= hoy:
                                                                    if fechacompara and fechacompara < hoy:
                                                                        action_button = {
                                                                            "action": "create_video",
                                                                            "url": None,
                                                                            "parametro": None,
                                                                            "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                            "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                            "verbose": "Subir video",
                                                                            "icon": u"fa fa-comments",
                                                                            "style": None,
                                                                            }
                                                                    if fechacompara and fechacompara == hoy:
                                                                        if turno.termina < horaactual:
                                                                            action_button = {
                                                                                "action": "create_video",
                                                                                "url": None,
                                                                                "parametro": None,
                                                                                "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                                "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                                "verbose": "Subir video",
                                                                                "icon": u"fa fa-comments",
                                                                                "style": None,
                                                                                }
                                                            else:
                                                                url = f"https://aulagradob.unemi.edu.ec/mod/url/view.php?id={clasesactualessincronica[0].idforomoodle}"
                                                                action_button = {
                                                                    "action": "view_video",
                                                                    "url": url,
                                                                    "parametro": None,
                                                                    "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                    "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                    "verbose": "Ver video",
                                                                    "icon": u"fa fa-link",
                                                                    # "style": u"background-color: #49afcd !important;",
                                                                    }
                                                elif clase.tipohorario in [7, 9]:
                                                    if clase.subirenlace:
                                                        clasesactualesasincronica = clase.horario_profesor_actualasincronica(numerosemanaactual)
                                                        if not clasesactualesasincronica.values("id").exists():
                                                            if aux_clasesactuales[0].disponible(ePeriodoAcademia=ePeriodoAcademia, validaModalidad=True):
                                                                url = None
                                                                if clase.materia.tieneurlwebex(clase.profesor):
                                                                    url = f"https://unemi.webex.com/meet/{clase.profesor.persona.usuario}"
                                                                elif clase.profesor.urlzoom:
                                                                    url = clase.profesor.urlzoom
                                                                clase_ids = (",".join([str(x.id) for x in turno.horario_profesor_actual_horario(dia[0], profesor, periodo, False, False)]))
                                                                action_button = {
                                                                    "action": "open_class_asincronica",
                                                                    "url": url,
                                                                    "parametro": clase_ids,
                                                                    "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                    "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                    "verbose": u"Cargar Video",
                                                                    "icon": u"fa fa-plus",
                                                                    # "style": u"background-color: #D66E22 !important;",
                                                                    }
                                                        else:
                                                            if not tieneferiado:
                                                                url = f"https://aulagradob.unemi.edu.ec/mod/url/view.php?id={clasesactualesasincronica[0].idforomoodle}"
                                                                action_button = {
                                                                    "action": "view_video",
                                                                    "url": url,
                                                                    "parametro": None,
                                                                    "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                    "modalidad_display":
                                                                    ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                    "verbose": "Ver video",
                                                                    "icon": u"fa fa-link",
                                                                    # "style": u"background-color: #49afcd !important;",
                                                                    }

                            elif coordinacion.id in [9]:
                                # 1 => PRESENCIAL
                                if clase.tipohorario == 1:
                                    if not tieneferiado:
                                        if aux_clasesactuales[0].tipoprofesor.id != 8:
                                            aula = clase.aula
                                            puede_abrir_fuera = True
                                            if ePeriodoAcademia.valida_asistencia_in_home and not tiene_solicitud_apertura_clase:
                                                if aula and aula.bloque and aula.bloque.in_home:
                                                    if not inhouse_check(request, valida_clase=True):
                                                        puede_abrir_fuera = False
                                            if disponible and puede_abrir_fuera:
                                                if aux_clasesactuales[0].disponible(ePeriodoAcademia=ePeriodoAcademia):
                                                    clase_ids = (",".join([str(x.id) for x in turno.horario_profesor_actual_horario(dia[0], profesor, periodo, False, False)]))
                                                    url = None
                                                    if clase.materia.tieneurlwebex(clase.profesor):
                                                        url = f"https://unemi.webex.com/meet/{clase.profesor.persona.usuario}"
                                                    elif clase.profesor.urlzoom:
                                                        url = clase.profesor.urlzoom
                                                    action_button = {
                                                        "action": "open_class",
                                                        "url": url,
                                                        "parametro": clase_ids,
                                                        "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                        "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                        "verbose": u"Comenzar Clase",
                                                        "icon": u"fa fa-plus",
                                                        "style": u"background-color: #fc7e00 !important; color: #fff;",
                                                        }

                                # 2 => CLASE VIRTUAL SINCRÓNICA
                                # 8 => CLASE REFUERZO SINCRÓNICA
                                # 7 => CLASE VIRTUAL ASINCRÓNICA
                                # 9 => CLASE REFUERZO ASINCRÓNICA
                                elif clase.tipohorario in [2, 7, 8, 9]:
                                    if not tieneferiado:
                                        if clase.tipohorario in [2, 8]:
                                            if disponible:
                                                if aux_clasesactuales[0].disponible(ePeriodoAcademia=ePeriodoAcademia):
                                                    url = None
                                                    if clase.materia.tieneurlwebex(clase.profesor):
                                                        url = f"https://unemi.webex.com/meet/{clase.profesor.persona.usuario}"
                                                    elif clase.profesor.urlzoom:
                                                        url = clase.profesor.urlzoom
                                                    clase_ids = (",".join([str(x.id) for x in turno.horario_profesor_actual_horario(dia[0], profesor, periodo, False, False)]))
                                                    action_button = {
                                                        "action": "open_class",
                                                        "url": url,
                                                        "parametro": clase_ids,
                                                        "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                        "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                        "verbose": u"Comenzar Clase",
                                                        "icon": u"fa fa-plus",
                                                        "style": u"background-color: #fc7e00 !important; color: #fff;",
                                                    }
                                                else:
                                                    if clase.subirenlace:
                                                        clasesactualessincronica = clase.horario_profesor_actualsincronica(numerosemanaactual)
                                                        if not tieneferiado:
                                                            if not clasesactualessincronica.values("id").exists():
                                                                if fechacompara and fechacompara <= hoy:
                                                                    if fechacompara and fechacompara < hoy:
                                                                        action_button = {
                                                                            "action": "create_video",
                                                                            "url": None,
                                                                            "parametro": None,
                                                                            "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                            "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                            "verbose": "Subir video",
                                                                            "icon": u"fa fa-comments",
                                                                            "style": None,
                                                                        }
                                                                    if fechacompara and fechacompara == hoy:
                                                                        if turno.termina < horaactual:
                                                                            action_button = {
                                                                                "action": "create_video",
                                                                                "url": None,
                                                                                "parametro": None,
                                                                                "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                                "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                                "verbose": "Subir video",
                                                                                "icon": u"fa fa-comments",
                                                                                "style": None,
                                                                            }
                                                            else:
                                                                url = f"https://aulanivelacion.unemi.edu.ec/mod/url/view.php?id={clasesactualessincronica[0].idforomoodle}"
                                                                action_button = {
                                                                    "action": "view_video",
                                                                    "url": url,
                                                                    "parametro": None,
                                                                    "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                    "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                    "verbose": "Ver video",
                                                                    "icon": u"fa fa-link",
                                                                    # "style": u"background-color: #49afcd "
                                                                    # u"!important;",
                                                                }
                                            elif clase.subirenlace:
                                                clasesactualessincronica = clase.horario_profesor_actualsincronica(numerosemanaactual)
                                                if not clasesactualessincronica:
                                                    if fechacompara and fechacompara <= hoy:
                                                        if fechacompara and fechacompara < hoy:
                                                            action_button = {
                                                                "action": "create_video",
                                                                "url": None,
                                                                "parametro": None,
                                                                "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                "verbose": "Subir video",
                                                                "icon": u"fa fa-comments",
                                                                "style": None,
                                                            }
                                                        if fechacompara and fechacompara == hoy:
                                                            if turno.termina < horaactual:
                                                                action_button = {
                                                                    "action": "create_video",
                                                                    "url": None,
                                                                    "parametro": None,
                                                                    "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                    "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                    "verbose": "Subir video",
                                                                    "icon": u"fa fa-comments",
                                                                    "style": None,
                                                                }
                                                else:
                                                    url = f"https://aulanivelacion.unemi.edu.ec/mod/url/view.php?id={clasesactualessincronica[0].idforomoodle}"
                                                    action_button = {
                                                        "action": "view_video",
                                                        "url": url,
                                                        "parametro": None,
                                                        "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                        "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                        "verbose": "Ver video",
                                                        "icon": u"fa fa-link",
                                                        # "style": u"background-color: #49afcd !important;",
                                                    }
                                        elif clase.tipohorario in [7, 9]:
                                            if clase.subirenlace:
                                                clasesactualesasincronica = clase.horario_profesor_actualasincronica(numerosemanaactual)
                                                if not clasesactualesasincronica.values("id").exists():
                                                    if aux_clasesactuales[0].disponible(ePeriodoAcademia=ePeriodoAcademia, validaModalidad=True):
                                                        url = None
                                                        if clase.materia.tieneurlwebex(clase.profesor):
                                                            url = f"https://unemi.webex.com/meet/{clase.profesor.persona.usuario}"
                                                        elif clase.profesor.urlzoom:
                                                            url = clase.profesor.urlzoom
                                                        clase_ids = (",".join([str(x.id) for x in turno.horario_profesor_actual_horario(dia[0], profesor, periodo, False, False)]))
                                                        action_button = {
                                                            "action": "open_class_asincronica",
                                                            "url": url,
                                                            "parametro": clase_ids,
                                                            "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                            "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                            "verbose": u"Cargar Video",
                                                            "icon": u"fa fa-plus",
                                                            # "style": u"background-color: #D66E22 !important;",
                                                        }
                                                else:
                                                    if not tieneferiado:
                                                        url = f"https://aulanivelacion.unemi.edu.ec/mod/url/view.php?id={clasesactualesasincronica[0].idforomoodle}"
                                                        action_button = {
                                                            "action": "view_video",
                                                            "url": url,
                                                            "parametro": None,
                                                            "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                            "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                            "verbose": "Ver video",
                                                            "icon": u"fa fa-link",
                                                            # "style": u"background-color: #49afcd !important;",
                                                        }

                            elif coordinacion.id in [7, 10]:
                                # 1 => PRESENCIAL
                                if clase.tipohorario == 1:
                                    if aux_clasesactuales[0].tipoprofesor.id != 8:
                                        if disponible:
                                            if aux_clasesactuales[0].disponible(ePeriodoAcademia=ePeriodoAcademia):
                                                clase_ids = (",".join([str(x.id) for x in turno.horario_profesor_actual_horario(dia[0], profesor, periodo, False, False)]))
                                                url = None
                                                if clase.materia.tieneurlwebex(clase.profesor):
                                                    url = f"https://unemi.webex.com/meet/{clase.profesor.persona.usuario}"
                                                elif clase.profesor.urlzoom:
                                                    url = clase.profesor.urlzoom
                                                action_button = {
                                                    "action": "open_class",
                                                    "url": url,
                                                    "parametro": clase_ids,
                                                    "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                    "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                    "verbose": u"Comenzar Clase",
                                                    "icon": u"fa fa-plus",
                                                    "style": u"background-color: #fc7e00 !important; color: #fff;",
                                                    }
                                # 2 => CLASE VIRTUAL SINCRÓNICA
                                # 8 => CLASE REFUERZO SINCRÓNICA
                                elif clase.tipohorario in [2, 7]:
                                    if clase.tipohorario in [2, 7]:
                                        if disponible:
                                            if aux_clasesactuales[0].disponible(ePeriodoAcademia=ePeriodoAcademia):
                                                url = None
                                                if clase.materia.tieneurlwebex(clase.profesor):
                                                    url = f"https://unemi.webex.com/meet/{clase.profesor.persona.usuario}"
                                                elif clase.profesor.urlzoom:
                                                    url = clase.profesor.urlzoom
                                                clase_ids = (",".join([str(x.id) for x in turno.horario_profesor_actual_horario(dia[0], profesor, periodo, False, False)]))
                                                action_button = {
                                                    "action": "open_class",
                                                    "url": url,
                                                    "parametro": clase_ids,
                                                    "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                    "modalidad_display":  ePeriodoAcademia.get_tipo_modalidad_display(),
                                                    "verbose": u"Comenzar Clase",
                                                    "icon": u"fa fa-plus",
                                                    "style": u"background-color: #fc7e00 !important; color: #fff;",
                                                    }
                                            else:
                                                if clase.subirenlace:
                                                    clasesactualesasincronica = clase.horario_profesor_actualasincronica(numerosemanaactual)
                                                    if not tieneferiado:
                                                        if not clasesactualesasincronica:
                                                            if fechacompara and fechacompara <= hoy:
                                                                if fechacompara and fechacompara < hoy:
                                                                    action_button = {
                                                                        "action": "create_video",
                                                                        "url": None,
                                                                        "parametro": None,
                                                                        "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                        "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                        "verbose": "Subir video",
                                                                        "icon": u"fa fa-comments",
                                                                        "style": None,
                                                                        }
                                                                if fechacompara and fechacompara == hoy:
                                                                    if turno.termina < horaactual:
                                                                        action_button = {
                                                                            "action": "create_video",
                                                                            "url": None,
                                                                            "parametro": None,
                                                                            "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                            "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                            "verbose": "Subir video",
                                                                            "icon": u"fa fa-comments",
                                                                            "style": None,
                                                                            }
                                                        else:
                                                            url = f"https://posgrado.unemi.edu.ec/mod/url/view.php?id={clasesactualesasincronica[0].idforomoodle}"
                                                            action_button = {
                                                                "action": "view_video",
                                                                "url": url,
                                                                "parametro": None,
                                                                "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                "verbose": "Ver video",
                                                                "icon": u"fa fa-link",
                                                                # "style": u"background-color: #49afcd "
                                                                #          u"!important;",
                                                                }
                                        elif clase.subirenlace:
                                            clasesactualesasincronica = clase.horario_profesor_actualasincronica(numerosemanaactual)
                                            if not tieneferiado:
                                                if not clasesactualesasincronica:
                                                    if fechacompara and fechacompara <= hoy:
                                                        if fechacompara and fechacompara < hoy:
                                                            action_button = {
                                                                "action": "create_video",
                                                                "url": None,
                                                                "parametro": None,
                                                                "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                "verbose": "Subir video",
                                                                "icon": u"fa fa-comments",
                                                                "style": None,
                                                                }
                                                        if fechacompara and fechacompara == hoy:
                                                            if turno.termina < horaactual:
                                                                action_button = {
                                                                    "action": "create_video",
                                                                    "url": None,
                                                                    "parametro": None,
                                                                    "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                    "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                    "verbose": "Subir video",
                                                                    "icon": u"fa fa-comments",
                                                                    "style": None,
                                                                    }
                                                else:
                                                    url = f"https://posgrado.unemi.edu.ec/mod/url/view.php?id={clasesactualesasincronica[0].idforomoodle}"
                                                    action_button = {
                                                        "action": "view_video",
                                                        "url": url,
                                                        "parametro": None,
                                                        "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                        "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                        "verbose": "Ver video",
                                                        "icon": u"fa fa-link",
                                                        # "style": u"background-color: #49afcd !important;",
                                                        }

                            clasesactuales.append({"id": clase.id,
                                                   "dia": dia[0],
                                                   "color": clase.color(),
                                                   "asignatura": clase.materia.asignatura.nombre,
                                                   "modalidad_id": clase.materia.asignaturamalla.malla.modalidad.id,
                                                   "modalidad": clase.materia.asignaturamalla.malla.modalidad.nombre,
                                                   "identificacion": clase.materia.identificacion,
                                                   "paralelo": clase.materia.paralelo,
                                                   "alias": clase.materia.asignaturamalla.malla.carrera.alias,
                                                   "nivelmalla": clase.materia.asignaturamalla.nivelmalla.__str__(),
                                                   "inicio": clase.inicio.strftime("%d-%m-%Y"),
                                                   "fin": clase.fin.strftime("%d-%m-%Y"),
                                                   "nivel_paralelo": clase.materia.nivel.paralelo,
                                                   "aula": clase.aula.nombre,
                                                   "tipoprofesor": clase.tipoprofesor.__str__(),
                                                   "profesor": clase.profesor.__str__(),
                                                   "tipohorario": clase.tipohorario,
                                                   "tipohorario_display": clase.get_tipohorario_display(),
                                                   "action_button": action_button,
                                                   "fechacompara": fechacompara.strftime("%d-%m-%Y") if fechacompara else None,
                                                   "style_card": style_card,
                                                   })

                        clasesactualespractica = []

                        aux_clasesactualespractica = turno.horario_profesor_actual_practica(dia[0], profesor, periodo)
                        for clase in aux_clasesactualespractica:
                            # if clase.id == 240155 and dia[0]==4:
                            #     print(u"Pausa en practicas")
                            #     print(u"Materia practica: %s" % clase.materia.practicas)
                            # mi_coordinacion_id = clase.materia.coordinacion().id if clase.materia.coordinacion() else 0
                            # style_card = f"background-color: {clase.get_display_background_tipohorario_colours()} color: {clase.get_display_color_text_tipohorario_colours()}
                            style_card = f"background-color: white !important; color: #264763 !important; border-left: 5px solid {clase.get_display_color_text_tipohorario_colours()} !important;"
                            if not clase.tipohorario in [x[0] for x in aTipoHorarios]:
                                for num in TIPOHORARIO_COLOURS:
                                    if num[0] == clase.tipohorario:
                                        aTipoHorarios.append(num)
                            action_button = {}
                            coordinacion = clase.materia.coordinacion()
                            modalidad = clase.materia.asignaturamalla.malla.modalidad
                            if coordinacion is None:
                                raise NameError(u"Clase no tiene coordinación configurada")
                            if not coordinacion.id in [1, 2, 3, 4, 5, 9, 7, 10, 12]:
                                raise NameError(u"Coordinación: %s no esta configurada en horario" % coordinacion.__str__())
                            fechacompara = clase.compararfecha(numerosemanaactual)
                            tieneferiado = periodo.es_feriado(fechacompara, clase.materia)
                            grupoprofesor = None
                            if clase.tipoprofesor.id in [2, 13]:
                                if clase.grupoprofesor:
                                    if clase.grupoprofesor.paralelopractica:
                                        grupoprofesor = clase.grupoprofesor.get_paralelopractica_display()
                                        # grupoprofesor_id = clase.grupoprofesor.id
                            if coordinacion.id in [1, 2, 3, 4, 5, 12]:
                                # 1 => CLASE PRESENCIAL
                                # 2 => CLASE VIRTUAL SINCRÓNICA
                                # 8 => CLASE REFUERZO SINCRÓNICA
                                if clase.tipohorario in [1, 2, 8]:
                                    puede_abrir_fuera = True
                                    if clase.tipohorario == 1:
                                        if aux_clasesactualespractica[0].tipoprofesor.id != 8:
                                            aula = clase.aula
                                            if ePeriodoAcademia.valida_asistencia_in_home and not tiene_solicitud_apertura_clase:
                                                if aula and aula.bloque and aula.bloque.in_home:
                                                    if not inhouse_check(request, valida_clase=True):
                                                        puede_abrir_fuera = False
                                    if disponible and puede_abrir_fuera:
                                        utiliza_zoom = False
                                        tiene_zoom = False
                                        if clase.tipohorario in [2, 8]:
                                            utiliza_zoom = True
                                            if clase.materia.tieneurlwebex(clase.profesor):
                                                tiene_zoom = True
                                            elif clase.profesor.urlzoom:
                                                tiene_zoom = True
                                        if aux_clasesactualespractica[0].disponible(ePeriodoAcademia=ePeriodoAcademia):
                                            url = None
                                            if clase.materia.tieneurlwebex(clase.profesor):
                                                url = f"https://unemi.webex.com/meet/{clase.profesor.persona.usuario}"
                                            elif clase.profesor.urlzoom:
                                                url = clase.profesor.urlzoom
                                            clase_ids = (",".join([str(x.id) for x in turno.horario_profesor_actual_practica(dia[0], profesor, periodo, False, False)]))
                                            if not utiliza_zoom:
                                                action_button = {
                                                    "action": "open_class",
                                                    "url": url,
                                                    "parametro": clase_ids,
                                                    "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                    "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                    "verbose": u"Registrar Prácticas",
                                                    "icon": u"fa fa-plus",
                                                    # "style": u"background-color: #2d8cff !important;",
                                                    }
                                            elif tiene_zoom:
                                                action_button = {
                                                    "action": "open_class",
                                                    "url": url,
                                                    "parametro": clase_ids,
                                                    "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                    "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                    "verbose": u"Registrar Prácticas",
                                                    "icon": u"fa fa-plus",
                                                    # "style": u"background-color: #2d8cff !important;",
                                                    }
                                        else:
                                            if clase.tipohorario in [2, 8] and tiene_zoom:
                                                if clase.subirenlace:
                                                    if modalidad:
                                                        if modalidad.id in [1, 2]:
                                                            if not tieneferiado:
                                                                clasesactualesasincronica = clase.horario_profesor_actualasincronica(numerosemanaactual)
                                                                if not clasesactualesasincronica:
                                                                    if fechacompara and fechacompara <= hoy:
                                                                        if fechacompara and fechacompara < hoy:
                                                                            action_button = {
                                                                                "action": "create_video",
                                                                                "url": None,
                                                                                "parametro": None,
                                                                                "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                                "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                                "verbose": "Subir video",
                                                                                "icon": u"fa fa-comments",
                                                                                "style": None,
                                                                            }
                                                                        if fechacompara and fechacompara == hoy:
                                                                            if turno.termina < horaactual:
                                                                                action_button = {
                                                                                    "action": "create_video",
                                                                                    "url": None,
                                                                                    "parametro": None,
                                                                                    "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                                    "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                                    "verbose": "Subir video",
                                                                                    "icon": u"fa fa-comments",
                                                                                    "style": None,
                                                                                }
                                                                else:
                                                                    action_button = {
                                                                        "action": "view_video",
                                                                        "url": f"https://aulagradoa.unemi.edu.ec/mod/url/view.php?id={clasesactualesasincronica[0].idforomoodle}",
                                                                        "parametro": None,
                                                                        "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                        "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                        "verbose": "Ver video",
                                                                        "icon": u"fa fa-link",
                                                                        # "style": u"background-color: #49afcd !important;",
                                                                    }
                                                        elif modalidad.id in [3]:
                                                            if not tieneferiado:
                                                                clasesactualessincronica = clase.horario_profesor_actualsincronica(numerosemanaactual)
                                                                if not clasesactualessincronica:
                                                                    if fechacompara and fechacompara <= hoy:
                                                                        if fechacompara and fechacompara < hoy:
                                                                            action_button = {
                                                                                "action": "create_video",
                                                                                "url": None,
                                                                                "parametro": None,
                                                                                "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                                "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                                "verbose": "Subir video",
                                                                                "icon": u"fa fa-comments",
                                                                                "style": None,
                                                                            }
                                                                        if fechacompara and fechacompara == hoy:
                                                                            if turno.termina < horaactual:
                                                                                action_button = {
                                                                                    "action": "create_video",
                                                                                    "url": None,
                                                                                    "parametro": None,
                                                                                    "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                                    "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                                    "verbose": "Subir video",
                                                                                    "icon": u"fa fa-comments",
                                                                                    "style": None,
                                                                                }
                                                                else:
                                                                    action_button = {
                                                                        "action": "view_video",
                                                                        "url": f"https://aulagradob.unemi.edu.ec/mod/url/view.php?id={clasesactualessincronica[0].idforomoodle}",
                                                                        "parametro": None,
                                                                        "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                        "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                        "verbose": "Ver video",
                                                                        "icon": u"fa fa-link",
                                                                        # "style": u"background-color: #49afcd !important;",
                                                                    }
                                            elif not tieneferiado:
                                                if fechacompara and fechacompara <= hoy:
                                                    if fechacompara and fechacompara < hoy:
                                                        action_button = {
                                                            "action": "open_class_practica",
                                                            "url": None,
                                                            "parametro": (",".join([str(x.id) for x in aux_clasesactualespractica])),
                                                            "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                            "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                            "verbose": "Registrar Prácticas",
                                                            "icon": u"fa fa-plus",
                                                            # "style": u"background-color: #2d8cff !important;",
                                                            "fecha": fechacompara.strftime("%d-%m-%Y"),
                                                            }
                                                    if fechacompara and fechacompara == hoy:
                                                        if turno.termina < horaactual:
                                                            action_button = {
                                                                "action": "open_class_practica",
                                                                "url": None,
                                                                "parametro": (",".join([str(x.id) for x in aux_clasesactualespractica])),
                                                                "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                "verbose": "Registrar Prácticas",
                                                                "icon": u"fa fa-plus",
                                                                # "style": u"background-color: #2d8cff !important;",
                                                                "fecha": fechacompara.strftime("%d-%m-%Y"),
                                                                }
                                    else:
                                        if clase.subirenlace:
                                            if clase.tipohorario in [2, 8]:
                                                if modalidad:
                                                    if modalidad.id in [1, 2]:
                                                        clasesactualesasincronica = clase.horario_profesor_actualasincronica(numerosemanaactual)
                                                        if not tieneferiado:
                                                            if not clasesactualesasincronica:
                                                                if fechacompara and fechacompara <= hoy:
                                                                    if fechacompara and fechacompara < hoy:
                                                                        action_button = {
                                                                            "action": "create_video",
                                                                            "url": None,
                                                                            "parametro": None,
                                                                            "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                            "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                            "verbose": "Subir video",
                                                                            "icon": u"fa fa-comments",
                                                                            "style": None,
                                                                        }
                                                                    if fechacompara and fechacompara == hoy:
                                                                        if turno.termina < horaactual:
                                                                            action_button = {
                                                                                "action": "create_video",
                                                                                "url": None,
                                                                                "parametro": None,
                                                                                "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                                "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                                "verbose": "Subir video",
                                                                                "icon": u"fa fa-comments",
                                                                                "style": None,
                                                                            }
                                                            else:
                                                                action_button = {
                                                                    "action": "view_video",
                                                                    "url": f"https://aulagradoa.unemi.edu.ec/mod/url/view.php?id={clasesactualesasincronica[0].idforomoodle}",
                                                                    "parametro": None,
                                                                    "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                    "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                    "verbose": "Ver video",
                                                                    "icon": u"fa fa-link",
                                                                    # "style": u"background-color: #49afcd !important;",
                                                                }
                                                    elif modalidad.id in [3]:
                                                        clasesactualessincronica = clase.horario_profesor_actualsincronica(numerosemanaactual)
                                                        if not tieneferiado:
                                                            if not clasesactualessincronica:
                                                                if fechacompara and fechacompara <= hoy:
                                                                    if fechacompara and fechacompara < hoy:
                                                                        action_button = {
                                                                            "action": "create_video",
                                                                            "url": None,
                                                                            "parametro": None,
                                                                            "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                            "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                            "verbose": "Subir video",
                                                                            "icon": u"fa fa-comments",
                                                                            "style": None,
                                                                        }
                                                                    if fechacompara and fechacompara == hoy:
                                                                        if turno.termina < horaactual:
                                                                            action_button = {
                                                                                "action": "create_video",
                                                                                "url": None,
                                                                                "parametro": None,
                                                                                "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                                "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                                "verbose": "Subir video",
                                                                                "icon": u"fa fa-comments",
                                                                                "style": None,
                                                                            }
                                                            else:
                                                                action_button = {
                                                                    "action": "view_video",
                                                                    "url": f"https://aulagradob.unemi.edu.ec/mod/url/view.php?id={clasesactualessincronica[0].idforomoodle}",
                                                                    "parametro": None,
                                                                    "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                    "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                    "verbose": "Ver video",
                                                                    "icon": u"fa fa-link",
                                                                    # "style": u"background-color: #49afcd !important;",
                                                                }

                            elif coordinacion.id in [9]:
                                if clase.profesor.urlzoom:
                                    # 1 => CLASE PRESENCIAL
                                    # 2 => CLASE VIRTUAL SINCRÓNICA
                                    # 8 => CLASE REFUERZO SINCRÓNICA
                                    if clase.tipohorario in [1, 2, 8]:
                                        if disponible:
                                            if aux_clasesactualespractica[0].disponible(ePeriodoAcademia=ePeriodoAcademia):
                                                url = None
                                                if clase.materia.tieneurlwebex(clase.profesor):
                                                    url = f"https://unemi.webex.com/meet/{clase.profesor.persona.usuario}"
                                                elif clase.profesor.urlzoom:
                                                    url = clase.profesor.urlzoom
                                                # clase_ids = (",".join([str(x.id) for x in aux_clasesactualespractica]))
                                                clase_ids = (",".join([str(x.id) for x in turno.horario_profesor_actual_practica(dia[0], profesor, periodo, False, False)]))
                                                action_button = {
                                                    "action": "open_class",
                                                    "url": url,
                                                    "parametro": clase_ids,
                                                    "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                    "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                    "verbose": u"Registrar Prácticas",
                                                    "icon": u"fa fa-plus",
                                                    # "style": u"background-color: #2d8cff !important;",
                                                    }
                                            else:
                                                if clase.tipohorario in [2, 8]:
                                                    if clase.subirenlace:
                                                        clasesactualesasincronica = clase.horario_profesor_actualasincronica(numerosemanaactual)
                                                        if not tieneferiado:
                                                            if not clasesactualesasincronica:
                                                                if fechacompara and fechacompara <= hoy:
                                                                    if fechacompara and fechacompara < hoy:
                                                                        action_button = {
                                                                            "action": "create_video",
                                                                            "url": None,
                                                                            "parametro": None,
                                                                            "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                            "modalidad_display":
                                                                            ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                            "verbose": "Subir video",
                                                                            "icon": u"fa fa-comments",
                                                                            "style": None,
                                                                            }
                                                                    if fechacompara and fechacompara == hoy:
                                                                        if turno.termina < horaactual:
                                                                            action_button = {
                                                                                "action": "create_video",
                                                                                "url": None,
                                                                                "parametro": None,
                                                                                "modalidad":
                                                                                ePeriodoAcademia.tipo_modalidad,
                                                                                "modalidad_display":
                                                                                ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                                "verbose": "Subir video",
                                                                                "icon": u"fa fa-comments",
                                                                                "style": None,
                                                                                }
                                                            else:
                                                                action_button = {
                                                                    "action": "view_video",
                                                                    "url":
                                                                    f"https://aulagrado.unemi.edu.ec/mod/url/view.php?id={clasesactualesasincronica[0].idforomoodle}",
                                                                    "parametro": None,
                                                                    "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                    "modalidad_display":
                                                                    ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                    "verbose": "Ver video",
                                                                    "icon": u"fa fa-link",
                                                                    # "style": u"background-color: #49afcd !important;",
                                                                    }
                                                elif not tieneferiado:
                                                    if fechacompara and fechacompara <= hoy:
                                                        if fechacompara and fechacompara < hoy:
                                                            action_button = {
                                                                "action": "open_class_practica",
                                                                "url": None,
                                                                "parametro": (",".join(
                                                                    [str(x.id) for x in aux_clasesactualespractica]
                                                                    )),
                                                                "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                "modalidad_display":
                                                                ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                "verbose": "Registrar Prácticas",
                                                                "icon": u"fa fa-plus",
                                                                # "style": u"background-color: #2d8cff !important;",
                                                                "fecha": fechacompara.strftime("%d-%m-%Y"),
                                                                }
                                                        if fechacompara and fechacompara == hoy:
                                                            if turno.termina < horaactual:
                                                                action_button = {
                                                                    "action": "open_class_practica",
                                                                    "url": None,
                                                                    "parametro": (",".join(
                                                                        [str(x.id) for x in aux_clasesactualespractica]
                                                                        )),
                                                                    "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                    "modalidad_display":
                                                                        ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                    "verbose": "Registrar Prácticas",
                                                                    "icon": u"fa fa-plus",
                                                                    # "style": u"background-color: #2d8cff !important;",
                                                                    "fecha": fechacompara.strftime("%d-%m-%Y"),
                                                                    }
                                        else:
                                            if clase.subirenlace:
                                                if clase.tipohorario in [2, 8]:
                                                    clasesactualesasincronica = clase.horario_profesor_actualasincronica(numerosemanaactual)
                                                    if not tieneferiado:
                                                        if not clasesactualesasincronica:
                                                            if fechacompara and fechacompara <= hoy:
                                                                if fechacompara and fechacompara < hoy:
                                                                    action_button = {
                                                                        "action": "create_video",
                                                                        "url": None,
                                                                        "parametro": None,
                                                                        "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                        "modalidad_display":
                                                                        ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                        "verbose": "Subir video",
                                                                        "icon": u"fa fa-comments",
                                                                        "style": None,
                                                                        }
                                                                if fechacompara and fechacompara == hoy:
                                                                    if turno.termina < horaactual:
                                                                        action_button = {
                                                                            "action": "create_video",
                                                                            "url": None,
                                                                            "parametro": None,
                                                                            "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                            "modalidad_display":
                                                                            ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                            "verbose": "Subir video",
                                                                            "icon": u"fa fa-comments",
                                                                            "style": None,
                                                                            }
                                                        else:
                                                            action_button = {
                                                                "action": "view_video",
                                                                "url":
                                                                f"https://aulagrado.unemi.edu.ec/mod/url/view.php?id={clasesactualesasincronica[0].idforomoodle}",
                                                                "parametro": None,
                                                                "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                "verbose": "Ver video",
                                                                "icon": u"fa fa-link",
                                                                # "style": u"background-color: #49afcd !important;",
                                                                }
                            elif coordinacion.id in [7, 10]:
                                if clase.profesor.urlzoom:
                                    # 1 => CLASE PRESENCIAL
                                    # 2 => CLASE VIRTUAL SINCRÓNICA
                                    # 8 => CLASE REFUERZO SINCRÓNICA
                                    if clase.tipohorario in [1, 2, 8]:
                                        if disponible:
                                            if aux_clasesactualespractica[0].disponible(ePeriodoAcademia=ePeriodoAcademia):
                                                url = None
                                                if clase.materia.tieneurlwebex(clase.profesor):
                                                    url = f"https://unemi.webex.com/meet/{clase.profesor.persona.usuario}"
                                                elif clase.profesor.urlzoom:
                                                    url = clase.profesor.urlzoom
                                                # clase_ids = (",".join([str(x.id) for x in aux_clasesactualespractica]))
                                                clase_ids = (",".join([str(x.id) for x in turno.horario_profesor_actual_practica(dia[0], profesor, periodo, False, False)]))
                                                action_button = {"action": "open_class",
                                                                 "url": url,
                                                                 "parametro": clase_ids,
                                                                 "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                 "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                 "verbose": u"Registrar Prácticas",
                                                                 "icon": u"fa fa-plus",
                                                                 # "style": u"background-color: #2d8cff !important;",
                                                                 }
                                            else:
                                                if clase.tipohorario in [2, 8]:
                                                    if clase.subirenlace:
                                                        clasesactualesasincronica = clase.horario_profesor_actualasincronica(numerosemanaactual)
                                                        if not tieneferiado:
                                                            if not clasesactualesasincronica:
                                                                if fechacompara and fechacompara <= hoy:
                                                                    if fechacompara and fechacompara < hoy:
                                                                        action_button = {"action": "create_video",
                                                                                         "url": None,
                                                                                         "parametro": None,
                                                                                         "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                                         "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                                         "verbose": "Subir video",
                                                                                         "icon": u"fa fa-comments",
                                                                                         "style": None,
                                                                                         }
                                                                    if fechacompara and fechacompara == hoy:
                                                                        if turno.termina < horaactual:
                                                                            action_button = {"action": "create_video",
                                                                                             "url": None,
                                                                                             "parametro": None,
                                                                                             "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                                             "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                                             "verbose": "Subir video",
                                                                                             "icon": u"fa fa-comments",
                                                                                             "style": None,
                                                                                             }
                                                            else:
                                                                action_button = {"action": "view_video",
                                                                                 "url": f"https://aulagrado.unemi.edu.ec/mod/url/view.php?id={clasesactualesasincronica[0].idforomoodle}",
                                                                                 "parametro": None,
                                                                                 "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                                 "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                                 "verbose": "Ver video",
                                                                                 "icon": u"fa fa-link",
                                                                                 # "style": u"background-color: #49afcd !important;",
                                                                                 }
                                                elif not tieneferiado:
                                                    if fechacompara and fechacompara <= hoy:
                                                        if fechacompara and fechacompara < hoy:
                                                            action_button = {"action": "open_class_practica",
                                                                             "url": None,
                                                                             "parametro": (",".join([str(x.id) for x in aux_clasesactualespractica])),
                                                                             "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                             "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                             "verbose": "Registrar Prácticas",
                                                                             "icon": u"fa fa-plus",
                                                                             # "style": u"background-color: #2d8cff !important;",
                                                                             "fecha": fechacompara.strftime("%d-%m-%Y"),
                                                                             }
                                                        if fechacompara and fechacompara == hoy:
                                                            if turno.termina < horaactual:
                                                                action_button = {
                                                                    "action": "open_class_practica",
                                                                    "url": None,
                                                                    "parametro": (",".join(
                                                                        [str(x.id) for x in aux_clasesactualespractica])),
                                                                    "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                    "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                    "verbose": "Registrar Prácticas",
                                                                    "icon": u"fa fa-plus",
                                                                    # "style": u"background-color: #2d8cff !important;",
                                                                    "fecha": fechacompara.strftime("%d-%m-%Y"),
                                                                }
                                        else:
                                            if clase.subirenlace:
                                                if clase.tipohorario in [2, 8]:
                                                    clasesactualesasincronica = clase.horario_profesor_actualasincronica(numerosemanaactual)
                                                    if not tieneferiado:
                                                        if not clasesactualesasincronica:
                                                            if fechacompara and fechacompara <= hoy:
                                                                if fechacompara and fechacompara < hoy:
                                                                    action_button = {"action": "create_video",
                                                                                     "url": None,
                                                                                     "parametro": None,
                                                                                     "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                                     "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                                     "verbose": "Subir video",
                                                                                     "icon": u"fa fa-comments",
                                                                                     "style": None,
                                                                                     }
                                                                if fechacompara and fechacompara == hoy:
                                                                    if turno.termina < horaactual:
                                                                        action_button = {"action": "create_video",
                                                                                         "url": None,
                                                                                         "parametro": None,
                                                                                         "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                                         "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                                         "verbose": "Subir video",
                                                                                         "icon": u"fa fa-comments",
                                                                                         "style": None,
                                                                                         }
                                                        else:
                                                            action_button = {"action": "view_video",
                                                                             "url": f"https://aulagrado.unemi.edu.ec/mod/url/view.php?id={clasesactualesasincronica[0].idforomoodle}",
                                                                             "parametro": None,
                                                                             "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                             "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                             "verbose": "Ver video",
                                                                             "icon": u"fa fa-link",
                                                                             # "style": u"background-color: #49afcd !important;",
                                                                             }

                            clasesactualespractica.append({"id": clase.id,
                                                           "dia": dia[0],
                                                           "color": clase.color(),
                                                           "asignatura": clase.materia.asignatura.nombre,
                                                           "identificacion": clase.materia.identificacion,
                                                           "paralelo": clase.materia.paralelo,
                                                           "alias": clase.materia.asignaturamalla.malla.carrera.alias,
                                                           "nivelmalla": clase.materia.asignaturamalla.nivelmalla.__str__(),
                                                           "inicio": clase.inicio.strftime("%d-%m-%Y"),
                                                           "fin": clase.fin.strftime("%d-%m-%Y"),
                                                           "nivel_paralelo": clase.materia.nivel.paralelo,
                                                           "aula": clase.aula.nombre,
                                                           "tipoprofesor": clase.tipoprofesor.__str__(),
                                                           "tipoprofesor_id": clase.tipoprofesor.id,
                                                           "profesor": clase.profesor.__str__(),
                                                           "tipohorario": clase.tipohorario,
                                                           "tipohorario_display": clase.get_tipohorario_display(),
                                                           "grupoprofesor": grupoprofesor,
                                                           "materia_id": encrypt(clase.materia.id),
                                                           "fechacompara": fechacompara.strftime("%d-%m-%Y") if fechacompara else None,
                                                           "action_button": action_button,
                                                           "style_card": style_card,
                                                           })

                        clasesactualesayudante = []
                        aux_clasesactualesayudante = turno.horario_profesor_ayudante(dia[0], profesor, periodo)
                        for clase in aux_clasesactualesayudante:
                            # style_card = f"background-color: {clase.get_display_background_tipohorario_colours()} color: {clase.get_display_color_text_tipohorario_colours()}
                            style_card = f"background-color: white !important; color: #264763 !important; border-left: 5px solid {clase.get_display_color_text_tipohorario_colours()} !important;"
                            if not clase.tipohorario in [x[0] for x in aTipoHorarios]:
                                for num in TIPOHORARIO_COLOURS:
                                    if num[0] == clase.tipohorario:
                                        aTipoHorarios.append(num)
                            grupoprofesor = None
                            if clase.tipoprofesor.id == 2:
                                if clase.grupoprofesor:
                                    if clase.grupoprofesor.paralelopractica:
                                        grupoprofesor = clase.grupoprofesor.get_paralelopractica_display()
                            clasesactualesayudante.append({"id": clase.id,
                                                           "dia": dia[0],
                                                           "color": clase.color(),
                                                           "asignatura": clase.materia.asignatura.nombre,
                                                           "identificacion": clase.materia.identificacion,
                                                           "paralelo": clase.materia.paralelo,
                                                           "alias": clase.materia.asignaturamalla.malla.carrera.alias,
                                                           "nivelmalla": clase.materia.asignaturamalla.nivelmalla.__str__(),
                                                           "inicio": clase.inicio.strftime("%d-%m-%Y"),
                                                           "fin": clase.fin.strftime("%d-%m-%Y"),
                                                           "nivel_paralelo": clase.materia.nivel.paralelo,
                                                           "aula": clase.aula.nombre,
                                                           "tipoprofesor": clase.tipoprofesor.__str__(),
                                                           "profesor": clase.profesor.__str__(),
                                                           "tipohorario": clase.tipohorario,
                                                           "tipohorario_display": clase.get_tipohorario_display(),
                                                           "grupoprofesor": grupoprofesor,
                                                           "style_card": style_card,
                                                           })

                        clasesfuturas = []
                        aux_clasesfuturas = turno.horario_profesor_futuro(dia[0], profesor, periodo)
                        for clase in aux_clasesfuturas:
                            # f"background-color: {clase.get_display_background_tipohorario_colours()} color: {clase.get_display_color_text_tipohorario_colours()}
                            style_card = f"background-color: white !important; color: #264763 !important; border-left: 5px solid {clase.get_display_color_text_tipohorario_colours()} !important;"
                            if not clase.tipohorario in [x[0] for x in aTipoHorarios]:
                                for num in TIPOHORARIO_COLOURS:
                                    if num[0] == clase.tipohorario:
                                        aTipoHorarios.append(num)
                            clasesfuturas.append({"id": clase.id,
                                                  "dia": dia[0],
                                                  "color": clase.color(),
                                                  "asignatura": clase.materia.asignatura.nombre,
                                                  "identificacion": clase.materia.identificacion,
                                                  "paralelo": clase.materia.paralelo,
                                                  "alias": clase.materia.asignaturamalla.malla.carrera.alias,
                                                  "nivelmalla": clase.materia.asignaturamalla.nivelmalla.__str__(),
                                                  "inicio": clase.inicio.strftime("%d-%m-%Y"),
                                                  "fin": clase.fin.strftime("%d-%m-%Y"),
                                                  "nivel_paralelo": clase.materia.nivel.paralelo,
                                                  "aula": clase.aula.nombre,
                                                  "tipoprofesor": clase.tipoprofesor.__str__(),
                                                  "profesor": clase.profesor.__str__(),
                                                  "tipohorario": clase.tipohorario,
                                                  "tipohorario_display": clase.get_tipohorario_display(),
                                                  "style_card": style_card,
                                                  })

                        clasesfuturasayudante = []
                        aux_clasesfuturasayudante = turno.horario_profesor_futuro_ayudante(dia[0], profesor, periodo)
                        for clase in aux_clasesfuturasayudante:
                            # style_card = f"background-color: {clase.get_display_background_tipohorario_colours()} color: {clase.get_display_color_text_tipohorario_colours()}
                            style_card = f"background-color: white !important; color: #264763 !important; border-left: 5px solid {clase.get_display_color_text_tipohorario_colours()} !important;"
                            if not clase.tipohorario in [x[0] for x in aTipoHorarios]:
                                for num in TIPOHORARIO_COLOURS:
                                    if num[0] == clase.tipohorario:
                                        aTipoHorarios.append(num)
                            grupoprofesor = None
                            if clase.tipoprofesor.id == 2:
                                if clase.grupoprofesor:
                                    if clase.grupoprofesor.paralelopractica:
                                        grupoprofesor = clase.grupoprofesor.get_paralelopractica_display()
                            clasesfuturasayudante.append({"id": clase.id,
                                                          "dia": dia[0],
                                                          "color": clase.color(),
                                                          "asignatura": clase.materia.asignatura.nombre,
                                                          "identificacion": clase.materia.identificacion,
                                                          "paralelo": clase.materia.paralelo,
                                                          "alias": clase.materia.asignaturamalla.malla.carrera.alias,
                                                          "nivelmalla": clase.materia.asignaturamalla.nivelmalla.__str__(),
                                                          "inicio": clase.inicio.strftime("%d-%m-%Y"),
                                                          "fin": clase.fin.strftime("%d-%m-%Y"),
                                                          "nivel_paralelo": clase.materia.nivel.paralelo,
                                                          "aula": clase.aula.nombre,
                                                          "tipoprofesor": clase.tipoprofesor.__str__(),
                                                          "profesor": clase.profesor.__str__(),
                                                          "tipohorario": clase.tipohorario,
                                                          "tipohorario_display": clase.get_tipohorario_display(),
                                                          "grupoprofesor": grupoprofesor,
                                                          "style_card": style_card,
                                                          })
                        semana_turno.append({"dia": dia[0],
                                             "clasesactuales": clasesactuales,
                                             "clasesactualespractica": clasesactualespractica,
                                             "clasesactualesayudante": clasesactualesayudante,
                                             "clasesfuturas": clasesfuturas,
                                             "clasesfuturasayudante": clasesfuturasayudante,
                                             # "clasescomplexivo": clasescomplexivo,
                                             # "clasescomplexivofuturas": clasescomplexivofuturas,
                                             })
                    turnos.append({"id": turno.id,
                                   "verbose": turno.__str__(),
                                   "comienza": turno.comienza.strftime("%H:%M"),
                                   "termina": turno.termina.strftime("%H:%M"),
                                   "semana": semana_turno,
                                   "activo": horaactual >= turno.comienza and horaactual <= turno.termina,
                                   })

                for turno in sesion.turnos_actividades_planificacion(profesor, periodo):
                    semana_turno = []
                    for dia in semana:
                        actividadesdocentes = []
                        aux_actividadesdocentes = turno.horario_profesor_actividad_turno(dia[0], profesor, periodo, vistahorario=True)
                        for actividad in aux_actividadesdocentes:
                            action_button = {}
                            # actividad virtual
                            # marcadadoble = actividad.marcada_doble()
                            # if actividad.dia == datetime.now().weekday()+1 and (actividad.ordenmarcada == 1 or actividad.ordenmarcada == 3 and not actividad.actividad_marcada()):
                            #     verbose = 'Marcar Asistencia'
                            #     if marcadadoble and len(actividad.marcadaactividad_set.filter(status=True, logmarcada__logdia__fecha=datetime.now().date())) == 1:
                            #         verbose = 'Marcar Salida'
                            #     elif actividad.ordenmarcada == 3:
                            #         verbose = 'Marcar Salida'
                            #     action_button = {"action": "marcar_asistencia",
                            #                      "url": '/adm_marcadas',
                            #                      "modalidad": actividad.modalidad,
                            #                      "modalidad_display": actividad.get_modalidad_display(),
                            #                      "verbose": verbose,
                            #                      "icon": u"fa fa-check",
                            #                      "style": u"background-color: rgb(45, 140, 255) !important;",
                            #                      }
                            actividadnombre = ''
                            if actividad.detalledistributivo.criteriodocenciaperiodo:
                                actividadnombre = actividad.detalledistributivo.criteriodocenciaperiodo.criterio.nombre
                            if actividad.detalledistributivo.criterioinvestigacionperiodo:
                                actividadnombre = actividad.detalledistributivo.criterioinvestigacionperiodo.criterio.nombre
                            if actividad.detalledistributivo.criteriogestionperiodo:
                                actividadnombre = actividad.detalledistributivo.criteriogestionperiodo.criterio.nombre
                            # style_card = f"background-color: #e8f2ff color: #5c5776
                            style_card = f"background-color: white !important; color: #264763 !important; border-left: 5px solid #5c5776 !important;"
                            if not 10 in [x[0] for x in aTipoHorarios]:
                                aTipoHorarios.append((10, actividadnombre, '#e8f2ff', '#000000'))
                            actividadesdocentes.append({"id": actividad.id,
                                                        "dia": dia[0],
                                                        "color": '#e8f2ff',
                                                        "actividad": actividadnombre,
                                                        "inicio": actividad.inicio.strftime("%d-%m-%Y"),
                                                        "fin": actividad.fin.strftime("%d-%m-%Y"),
                                                        "action_button": action_button,
                                                        # "modalidad_display": actividad.get_modalidad_display(),
                                                        "marcada": str(actividad.get_marcada()),
                                                        "style_card": style_card
                                                        })
                        # PARA TUTORIAS

                        aux_horariotutoria = turno.horario_tutorias_academicas(dia[0], profesor, periodo)
                        action_button_upload_video = None
                        if aux_horariotutoria and profesor.urlzoom:
                            for tuto in aux_horariotutoria:
                                style_card = f"background-color: white !important;color: #264763 !important; border-left: 5px solid #1b6d85 !important;"
                                if not 11 in [x[0] for x in aTipoHorarios]:
                                    aTipoHorarios.append((11, u'ORIENTACIÓN Y ACOMPAÑAMIENTO A TRAVÉS DE TUTORÍAS PRESENCIALES O VIRTUALES, INDIVIDUALES O GRUPALES', '#cfe2eb', '#000000'))
                                action_button = {}
                                if tuto.disponibletutoria():
                                    url = None
                                    if tuto.profesor.urlzoom:
                                        url = tuto.profesor.urlzoom
                                    action_button = {"action": "add_clase_tutoria",
                                                     "url": url,
                                                     "parametro": tuto.id,
                                                     "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                     "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                     "verbose": u"Iniciar la tutoría",
                                                     "icon": u"fa fa-video-camera",
                                                     }

                                if tuto.claseactividad.detalledistributivo.criteriodocenciaperiodo.criterio.pk == 124 and not action_button:
                                    if registro := RegistroClaseTutoriaDocente.objects.filter((Q(horario__profesor=profesor) | Q(profesor=profesor)) & (Q(periodo=periodo) | Q(horario__periodo=periodo)), numerosemana=datetime.today().isocalendar()[1], status=True).order_by('-id').first():
                                        if not registro.enlaceuno:
                                            action_button_upload_video = {"action": "upload_video_actividad",
                                                                         "url": None,
                                                                         "parametro": tuto.id,
                                                                         "id_claseactividad": tuto.claseactividad.pk,
                                                                         "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                                         "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                                         "verbose": u"Subir video",
                                                                         "icon": u"fa fa-comments",
                                                                          "style": None,
                                                                         }

                                actividadesdocentes.append({"id": tuto.id,
                                                            "dia": dia[0],
                                                            "color": '#e8f2ff',
                                                            "actividad": tuto.claseactividad.detalledistributivo.criteriodocenciaperiodo.criterio.nombre,
                                                            "inicio": tuto.claseactividad.inicio.strftime("%d-%m-%Y"),
                                                            "fin": tuto.claseactividad.fin.strftime("%d-%m-%Y"),
                                                            "action_button": action_button,
                                                            "action_button_upload_video": action_button_upload_video,
                                                            "modalidad_display": tuto.claseactividad.get_modalidad_display(),
                                                            "style_card": style_card
                                                            })
                        semana_turno.append({"dia": dia[0],
                                             "actividadesdocentes": actividadesdocentes,
                                             })
                        ext = list(filter(lambda item: item['id'] == turno.id, turnos))
                        if not ext:
                            turnos.append({"id": turno.id,
                                           "verbose": turno.__str__(),
                                           "comienza": turno.comienza.strftime("%H:%M"),
                                           "termina": turno.termina.strftime("%H:%M"),
                                           "semana": semana_turno,
                                           "activo": horaactual >= turno.comienza and horaactual <= turno.termina,
                                           })
                        else:
                            if list(filter(lambda item: item['dia'] == dia[0], ext[0]['semana'])):
                                list(filter(lambda item: item['dia'] == dia[0], ext[0]['semana']))[0]['actividadesdocentes'] = actividadesdocentes
                            else:
                                ext[0]["semana"] = semana_turno
                turnos = sorted(turnos, key=lambda t: t['comienza'])

            else:
                if sesion.id == 15:
                    for turnotuto in sesion.turnosactivos_tutoria(profesor, periodo):
                        semana_tutoria = []
                        for diatuto in semanatutoria:
                            horariotutoria = []
                            aux_horariotutoria = turnotuto.horario_tutorias_academicas(diatuto[0], profesor, periodo)
                            if aux_horariotutoria and profesor.urlzoom:
                                for tuto in aux_horariotutoria:
                                    # style_card = f"background-color: #cfe2eb color: #1b6d85
                                    style_card = f"background-color: white !important;color: #264763 !important; border-left: 5px solid #1b6d85 !important;"
                                    if not 11 in [x[0] for x in aTipoHorarios]:
                                        aTipoHorarios.append((11, u'ORIENTACIÓN Y ACOMPAÑAMIENTO A TRAVÉS DE TUTORÍAS PRESENCIALES O VIRTUALES, INDIVIDUALES O GRUPALES', '#cfe2eb', '#000000'))
                                    action_button = {}
                                    if tuto.disponibletutoria():
                                        url = None
                                        if tuto.profesor.urlzoom:
                                            url = tuto.profesor.urlzoom
                                        action_button = {"action": "add_clase_tutoria",
                                                         "url": url,
                                                         "parametro": tuto.id,
                                                         "modalidad": ePeriodoAcademia.tipo_modalidad,
                                                         "modalidad_display": ePeriodoAcademia.get_tipo_modalidad_display(),
                                                         "verbose": u"Iniciar la tutoría",
                                                         "icon": u"fa fa-video-camera",
                                                         # "style": u"background-color: #2d8cff !important;",
                                                         }
                                    horariotutoria.append({"id": tuto.id,
                                                           "color": "#cfe2eb",
                                                           "verbose": u"ORIENTACIÓN Y ACOMPAÑAMIENTO A TRAVÉS DE TUTORÍAS PRESENCIALES O VIRTUALES, INDIVIDUALES O GRUPALES",
                                                           "action_button": action_button,
                                                           "style_card": style_card,
                                                           })
                            semana_tutoria.append({"dia": diatuto[0],
                                                   "horariotutoria": horariotutoria,
                                                   })
                        turnosactivostutoria.append({"id": turnotuto.id,
                                                     "verbose": turnotuto.__str__(),
                                                     "comienza": turnotuto.comienza.strftime("%H:%M"),
                                                     "termina": turnotuto.termina.strftime("%H:%M"),
                                                     "semana": semana_tutoria,
                                                     "activo": horaactual >= turnotuto.comienza and horaactual <= turnotuto.termina,
                                                     })

            aSesiones.append({"id": sesion.id,
                              "verbose": sesion.__str__(),
                              "nombre": sesion.nombre,
                              "turnos": turnos,
                              "turnosactivostutoria": turnosactivostutoria,
                              })

        return JsonResponse({"result": "ok",
                             "disponible": disponible,
                             "aLeccionClases": aLeccionClases,
                             "aClaseAbierta": aClaseAbierta,
                             "aMateriasNoProgramadas": aMateriasNoProgramadas,
                             "semana": semana,
                             "diaactual": diaactual,
                             "semanatutoria": semanatutoria,
                             "aSesiones": aSesiones,
                             "aTipoHorarios": aTipoHorarios,
                             "inhouse": inhouse_check(request),
                             "ip_scan": str(get_client_ip(request))})
    except Exception as ex:
        message_error = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
        # print(message_error)
        return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s %s" % (ex, message_error)})


def valida_inhouse_check(request):
    remote_addr = get_client_ip(request)
    return IpPermitidas.objects.values("id").filter(status=True, habilitado=True, valida_clase=True, ip=remote_addr).exists()


def view_pro_horarios_estudiante(request):
    try:
        persona = request.session['persona']
        periodo = request.session['periodo']
        perfilprincipal = request.session['perfilprincipal']
        if not perfilprincipal.es_estudiante():
            NameError(u"Solo los perfiles de estudiantes pueden ingresar al modulo.")
        inscripcion = perfilprincipal.inscripcion
        ePeriodoAcademia = periodo.get_periodoacademia()
        hoy = datetime.now().date()
        horaactual = datetime.now().time()
        aSesiones = []
        numerosemanaactual = datetime.today().isocalendar()[1]
        diaactual = hoy.isocalendar()[2]
        semana = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'],
                  [7, 'Domingo']]
        matricula = inscripcion.mi_matricula_periodo(periodo.id)
        materias = matricula.materiaasignada_set.all()
        clases = Clase.objects.db_manager("sga_select").filter(fin__gte=hoy, activo=True, materia__materiaasignada__matricula_id=matricula.id, materia__materiaasignada__retiramateria=False).distinct().order_by('inicio')
        clases2 = Clase.objects.db_manager("sga_select").filter(fin__lt=hoy, activo=True, materia__materiaasignada__matricula_id=matricula.id, materia__materiaasignada__retiramateria=False).distinct().order_by('inicio')
        sesiones = Sesion.objects.db_manager("sga_select").filter(turno__clase__in=clases.values_list("id").distinct() | clases2.values_list("id").distinct()).distinct()
        for sesion in sesiones:
            turnos = []
            for turno in sesion.turnos_clase2(clases):
                semana_turno = []
                for dia in semana:
                    # if dia[0] == 4 and turno.id == 12:
                    #     # print("para hacer una pausa")
                    clasesactuales = []
                    for clase in turno.horario_alumno_presente_consulta(hoy, dia[0], matricula, periodo.id):
                        grupoprofesor = None
                        disponible = clase.disponiblezoom(ePeriodoAcademia=ePeriodoAcademia)
                        disponible_hora = clase.disponiblezoom(always=True, ePeriodoAcademia=ePeriodoAcademia)
                        if clase.tipoprofesor and clase.grupoprofesor and clase.tipoprofesor.id == 2 and clase.grupoprofesor.paralelopractica:
                            grupoprofesor = clase.grupoprofesor.get_paralelopractica_display()
                        action_button = {}
                        # 1 => PRESENCIAL
                        # 2 => CLASE VIRTUAL SINCRÓNICA
                        # 7 => CLASE VIRTUAL ASINCRÓNICA
                        # 8 => CLASE REFUERZO SINCRÓNICA
                        if clase.tipohorario == 2 or clase.tipohorario == 8 or clase.tipohorario == 7:
                            if clase.dia == diaactual and hoy >= clase.inicio and hoy <= clase.fin:
                                if clase.tipohorario == 2 or clase.tipohorario == 8:
                                    if disponible_hora:
                                        """SOLO PARA ADMISIÓN Y QUE SEA PROPEDÉUTICO"""
                                        if clase.materia.coordinacion().id == 9 and clase.materia.asignatura.id == 4837:
                                            url = f"https://www.facebook.com/groups/aspirantes2021.unemioficial"
                                            style = u"background-color: #2d8cff !important;"
                                            action_button = {"action": "go_class",
                                                             "url": url,
                                                             "wait": False,
                                                             "disponible": disponible,
                                                             "verbose": u"Entrar a clase" if disponible else u"Ir a clase",
                                                             "icon": u"fa fa-facebook-square",
                                                             # "style": style if disponible else u"background-color: #F46839 !important;",
                                                             "key": f'c_id:{encrypt(clase.id)};t_id:{encrypt(clase.turno.id)};usu_id:{encrypt(persona.usuario.id)};day:{encrypt(dia[0])};date:{hoy.strftime("%d-%m-%Y")}',
                                                             }
                                        else:
                                            url = None
                                            style = None
                                            if clase.profesor:
                                                if clase.materia.tieneurlwebex(clase.profesor):
                                                    url = f"https://unemi.webex.com/meet/{clase.profesor.persona.usuario}"
                                                    style = u"background-color: #2d8cff !important;"
                                                elif clase.profesor.urlzoom:
                                                    url = clase.profesor.urlzoom
                                                    style = u"background-color: #2d8cff !important;"
                                            action_button = {"action": "go_class",
                                                             "url": url,
                                                             "wait": True,
                                                             "disponible": disponible,
                                                             "verbose": u"Entrar a clase" if disponible else u"Ir a clase",
                                                             "icon": u"fa fa-video-camera",
                                                             # "style": style if disponible else u"background-color: #F46839 !important;",
                                                             "key": f'c_id:{encrypt(clase.id)};t_id:{encrypt(clase.turno.id)};usu_id:{encrypt(persona.usuario.id)};day:{encrypt(dia[0])};date:{hoy.strftime("%d-%m-%Y")}',
                                                             }
                                elif clase.tipohorario == 7:
                                    clasesactualesasincronica = clase.horario_profesor_actualasincronica(numerosemanaactual)
                                    url = None
                                    if clasesactualesasincronica.exists():
                                        url = f"https://aulagrado.unemi.edu.ec/mod/forum/view.php?id={clasesactualesasincronica[0].idforomoodle}"
                                    action_button = {"action": "go_class",
                                                     "url": url,
                                                     "wait": False,
                                                     "disponible": False,
                                                     "verbose": u"Ir a la clase",
                                                     "icon": u"fa fa-comments",
                                                     "style": None,
                                                     }

                        clasesactuales.append({"id": clase.id,
                                               "asignatura": clase.materia.asignatura.nombre,
                                               "nivelmalla": clase.materia.asignaturamalla.nivelmalla.__str__(),
                                               "paralelo": clase.materia.paralelo,
                                               "alias": clase.materia.asignaturamalla.malla.carrera.alias,
                                               "aula": clase.aula.nombre,
                                               "sede": clase.aula.sede.nombre,
                                               "inicio": clase.inicio.strftime("%d-%m-%Y"),
                                               "fin": clase.fin.strftime("%d-%m-%Y"),
                                               "tipoprofesor_id": clase.tipoprofesor.id if clase.tipoprofesor else None,
                                               "tipoprofesor": clase.tipoprofesor.__str__() if clase.tipoprofesor else None,
                                               "profesor": clase.profesor.__str__() if clase.profesor else None,
                                               "profesor_sexo_id": clase.profesor.persona.sexo.id if clase.profesor and clase.profesor.persona.sexo else 2,
                                               "tipohorario": clase.tipohorario,
                                               "tipohorario_display": clase.get_tipohorario_display(),
                                               "grupoprofesor": grupoprofesor,
                                               "action_button": action_button,
                                               })
                    semana_turno.append({"dia": dia[0],
                                         "clases": clasesactuales})
                turnos.append({"id": turno.id,
                               "verbose": turno.__str__(),
                               "comienza": turno.comienza.strftime("%H:%M"),
                               "termina": turno.termina.strftime("%H:%M"),
                               "semana": semana_turno,
                               "activo": horaactual >= turno.comienza and horaactual <= turno.termina,
                               })
            turnos_old = []
            for turno in sesion.turnos_clase2(clases2):
                semana_turno = []
                for dia in semana:
                    clasespasadas = []
                    for clase in turno.horario_alumno_pasado_consulta(hoy, dia[0], matricula, periodo.id):
                        disponible = clase.disponiblezoom(ePeriodoAcademia=ePeriodoAcademia)
                        disponible_hora = clase.disponiblezoom(always=True, ePeriodoAcademia=ePeriodoAcademia)
                        grupoprofesor = None
                        if clase.tipoprofesor and clase.grupoprofesor and clase.tipoprofesor == 2 and clase.dia == diaactual and disponible_hora and clase.grupoprofesor.paralelopractica:
                            grupoprofesor = clase.grupoprofesor.get_paralelopractica_display()
                        clasespasadas.append({"id": clase.id,
                                              "asignatura": clase.materia.asignatura.nombre,
                                              "nivelmalla": clase.materia.asignaturamalla.nivelmalla.__str__(),
                                              "paralelo": clase.materia.paralelo,
                                              "alias": clase.materia.asignaturamalla.malla.carrera.alias,
                                              "aula": clase.aula.nombre,
                                              "inicio": clase.inicio.strftime("%d-%m-%Y"),
                                              "fin": clase.fin.strftime("%d-%m-%Y"),
                                              "tipoprofesor": clase.tipoprofesor.__str__() if clase.tipoprofesor else None,
                                              "profesor": clase.profesor.__str__() if clase.profesor else None,
                                              "tipohorario": clase.tipohorario,
                                              "tipohorario_display": clase.get_tipohorario_display(),
                                              "grupoprofesor": grupoprofesor,
                                              })
                    semana_turno.append({"dia": dia[0],
                                         "clases": clasespasadas})
                turnos_old.append({"id": turno.id,
                                   "verbose": turno.__str__(),
                                   "comienza": turno.comienza.strftime("%H:%M"),
                                   "termina": turno.termina.strftime("%H:%M"),
                                   "semana": semana_turno,
                                   "activo": horaactual >= turno.comienza and horaactual <= turno.termina,
                                   })

            aSesiones.append({"id": sesion.id,
                              "verbose": sesion.nombre if inscripcion and inscripcion.coordinacion.id == 9 else sesion.__str__(),
                              "nombre": sesion.nombre,
                              "turnos": turnos,
                              "turnos_old": turnos_old,
                              })

        return JsonResponse({"result": "ok", "diaactual": diaactual, "semana": semana, "aSesiones": aSesiones})
    except Exception as ex:
        return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})


def view_enter_class_estudiante(request):
    try:
        persona = request.session['persona']
        periodo = request.session['periodo']
        perfilprincipal = request.session['perfilprincipal']
        hoy = datetime.now().date()
        horaactual = datetime.now().time()
        if not 'idc' in request.POST:
            raise NameError(u"Clase no encontrada")
        if not 'navegador' in request.POST:
            raise NameError(u"Navegador no identificado")
        if not 'os' in request.POST:
            raise NameError(u"Sistema Operativo no identificado")
        if not 'screensize' in request.POST:
            raise NameError(u"Tamaño de la pantalla no identificado")
        navegador = request.POST['navegador']
        ops = request.POST['os']
        screen_size = request.POST['screensize']
        ip_public = get_client_ip(request)
        mensaje = None
        label_color = None
        if not perfilprincipal.inscripcion_id > 0:
            NameError(u"Solo los perfiles de estudiantes pueden ingresar al modulo.")
        isWait = True
        isRedis = False
        data_redis = None
        clasesabiertas = None
        ePeriodoAcademia = periodo.get_periodoacademia()
        if ePeriodoAcademia:
            if ePeriodoAcademia.utiliza_asistencia_redis and (ePeriodoAcademia.es_virtual() or ePeriodoAcademia.es_hibrida()):
                isRedis = True
                if not 'key' in request.POST:
                    raise NameError(u"Token de acceso no encontrado")
                token = request.POST['key']
                redis = Redis.StrictRedis(host=REDIS_HOST, password=REDIS_PASSWORD, port=REDIS_PORT, db=REDIS_BD)
                token_data = redis.get(token)
                if token_data:
                    data_redis = json.loads(token_data)

        if not Clase.objects.db_manager("sga_select").values("id").filter(pk=int(request.POST['idc'])).exists():
            raise NameError(u"Clase no encontrada")
        else:
            clase = Clase.objects.filter(pk=request.POST['idc'])[0]

        if isRedis:
            if data_redis:
                leccion_grupo_id = data_redis['leccion_grupo_id'] if 'leccion_grupo_id' in data_redis and data_redis['leccion_grupo_id'] else 0
                clasesabiertas = LeccionGrupo.objects.filter(pk=leccion_grupo_id, abierta=True).order_by('-fecha', '-horaentrada')
        else:
            clasesabiertas = LeccionGrupo.objects.filter(status=True, fecha=hoy, turno=clase.turno, dia=clase.dia, profesor_id=clase.profesor.id, abierta=True).order_by('-fecha', '-horaentrada')
        if clasesabiertas and clasesabiertas.values("id").exists():
            if clasesabiertas[0].mis_leciones().values('id').filter(clase=clase).exists():
                inscripcion = perfilprincipal.inscripcion
                leccion = clasesabiertas[0].mis_leciones().filter(clase=clase)[0]
                matricula = inscripcion.mi_matricula_periodo(periodo.id)
                materiaasignada = matricula.materiaasignada_set.filter(materia=clase.materia)[0]
                asistencias = AsistenciaLeccion.objects.filter(leccion=leccion, materiaasignada=materiaasignada)
                disponible = clase.disponiblezoom(ePeriodoAcademia=ePeriodoAcademia)
                disponible_hora = clase.disponiblezoom(always=True, ePeriodoAcademia=ePeriodoAcademia)
                if not asistencias.values("id").exists():
                    if materiaasignada.matricula.estado_matricula == 1:
                        log(u'Dio click en el botón en horario para ingresar en la clase: %s, pero no se registra asistencia por deuda' % clase, request, "add")
                        mensaje = u"Su asistencia no ha sido registrada por deuda pendiente. Revisar modulo de <a href='/alu_finanzas' target='_blank'>Mis Finanzas</a>"
                        return JsonResponse({"result": "ok", "isWait": False, "mensaje": mensaje, "label_color": "warning"})
                    else:
                        if clase.tipoprofesor.id == 2 and clase.tipohorario in [1, 2, 8]:
                            if clase.grupoprofesor:
                                if clase.grupoprofesor.paralelopractica:
                                    # grupoprofesor_id = clase.grupoprofesor.id
                                    if clase.grupoprofesor.listado_inscritos_grupos_practicas().exists():
                                        listado_alumnos_practica = clase.grupoprofesor.listado_inscritos_grupos_practicas()
                                        if ePeriodoAcademia.valida_asistencia_pago:
                                            asignados = MateriaAsignada.objects.filter(pk__in=listado_alumnos_practica.values_list('materiaasignada_id', flat=True).distinct(), matricula__estado_matricula__in=[2, 3])
                                        else:
                                            asignados = MateriaAsignada.objects.filter( pk__in=listado_alumnos_practica.values_list('materiaasignada_id', flat=True).distinct())
                                        if not materiaasignada.id in asignados.values_list("id", flat=True):
                                            log(u'Dio click en el botón en horario para ingresar en la clase: %s, pero no se registra asistencia porque al momento de iniciar la clase el profesor. El estudiante no tiene asignado grupo' % clase, request, "add")
                                            mensaje = u"Su asistencia no ha sido registrada porque no tiene asignado grupo de practica. Favor contactarse con director/a de carrera."
                                            lista = ['gestionacademica@unemi.edu.ec',
                                                     'planificacionacademica@unemi.edu.ec',
                                                     'kromanc1@unemi.edu.ec', ]
                                            send_html_mail("Estudiante si grupo de práctica",
                                                           "alu_horarios/emails/notificacion_sin_grupo_practica.html",
                                                           {'sistema': request.session['nombresistema'],
                                                            'persona': persona,
                                                            'inscripcion': inscripcion,
                                                            'clase': clase,
                                                            't': miinstitucion(),
                                                            }, lista, [],
                                                           cuenta=CUENTAS_CORREOS[0][1])
                                            return JsonResponse({"result": "ok", "isWait": False, "mensaje": mensaje,
                                                                 "label_color": "warning"})
                if asistencias.values("id").filter(asistio=False, virtual=False).exists():
                    asistencialeccion = asistencias.filter(asistio=False, virtual=False)[0]
                    if disponible:
                        asistencialeccion.asistio = True
                        asistencialeccion.virtual = True
                        asistencialeccion.virtual_fecha = hoy
                        asistencialeccion.virtual_hora = horaactual
                        asistencialeccion.ip_public = ip_public
                        asistencialeccion.browser = navegador
                        asistencialeccion.ops = ops
                        asistencialeccion.screen_size = screen_size
                        asistencialeccion.save(request)
                        if variable_valor('ACTUALIZA_ASISTENCIA'):
                            if not asistencialeccion.materiaasignada.sinasistencia:
                                ActualizaAsistencia(asistencialeccion.materiaasignada.id)
                        mensaje = u"Su asistencia ha sido registrada exitosamente."
                        label_color = 'success'
                        log(u'Adiciono asistencia en la clase: %s. Durante el tiempo establecido' % clase, request, "add")
                    elif disponible_hora:
                        asistencialeccion.asistio = False
                        asistencialeccion.virtual = True
                        asistencialeccion.virtual_fecha = hoy
                        asistencialeccion.virtual_hora = horaactual
                        asistencialeccion.ip_public = ip_public
                        asistencialeccion.browser = navegador
                        asistencialeccion.ops = ops
                        asistencialeccion.screen_size = screen_size
                        asistencialeccion.save(request)
                        if variable_valor('ACTUALIZA_ASISTENCIA'):
                            if not asistencialeccion.materiaasignada.sinasistencia:
                                ActualizaAsistencia(asistencialeccion.materiaasignada.id)
                        mensaje = f"Su asistencia no se ha registrado, usted ha ingresado a clases a las <b style='font-size: 22px;'>{datetime.now().time().strftime('%H:%M')}</b>"
                        label_color = 'warning'
                        log(u'Ingresa a la clase pero no se adiciono asistencia: %s. Debe informar al docente' % clase, request, "add")
                elif asistencias.values("id").filter(asistio=True, virtual=False).exists():
                    asistencialeccion = asistencias.filter(asistio=True, virtual=False)[0]
                    asistencialeccion.virtual = True
                    asistencialeccion.virtual_fecha = hoy
                    asistencialeccion.virtual_hora = horaactual
                    asistencialeccion.ip_public = ip_public
                    asistencialeccion.browser = navegador
                    asistencialeccion.ops = ops
                    asistencialeccion.screen_size = screen_size
                    asistencialeccion.save(request)
                    if variable_valor('ACTUALIZA_ASISTENCIA'):
                        if not asistencialeccion.materiaasignada.sinasistencia:
                            ActualizaAsistencia(asistencialeccion.materiaasignada.id)
                    mensaje = u"Su asistencia ya fue registrada por el/la profesor/a."
                    label_color = 'warning'
                    log(u'Ingresa a la clase su asistencia ya fue registrada previamente: %s.' % clase, request, "add")
                elif asistencias.values("id").filter(asistio=False, virtual=True).exists():
                    mensaje = f"Su asistencia no se ha registrado, usted ha ingresado a clases a las <b style='font-size: 22px;'>{datetime.now().time().strftime('%H:%M')}</b>"
                    label_color = 'warning'
                    log(u'Ingresa a la clase y su asistencia no se ha registrado por motivo de ingreso tarde: %s.' % clase,
                        request, "add")
                else:
                    mensaje = u"Su asistencia ya ha sido registrada con anterioridad."
                    label_color = 'success'
                asistencia = asistencias[0]
                logingreso = LogIngresoAsistenciaLeccion(asistencia=asistencia,
                                                         fecha=datetime.now().date(),
                                                         hora=datetime.now().time(),
                                                         ip_private=None,
                                                         ip_public=ip_public,
                                                         browser=navegador,
                                                         ops=ops,
                                                         screen_size=screen_size
                                                         )
                logingreso.save(request)
                """ SE COMENTO PORQUE EN EL SAVE DEL LOGINGRESO SE MANDA ACTUALIZAR"""
                # logingreso.actualizar(request)
                log(u'Dio click en el botón en horario para ingresar en la clase: %s' % logingreso, request, "add")
                isWait = False
        return JsonResponse({"result": "ok", "isWait": isWait, "mensaje": mensaje, "label_color": label_color})
    except Exception as ex:
        transaction.set_rollback(True)
        return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. %s" % ex})


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip