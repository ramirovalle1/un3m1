# coding=utf-8
import json
import os
import sys
from datetime import datetime, timedelta, date
from decimal import Decimal

from django.db import connection, transaction, connections
from django.template.defaultfilters import floatformat
from django.db.models import Q, Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status

from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.views.alumno.matricula.functions import validate_entry_to_student_api, generateCodeDeleteMatricula, \
    reenvioCodeDeleteMatricula, generateCodeRemoveMateria, reenvioCodeRemoveMateria
from api.views.alumno.addremove_matricula.functions import valida_conflicto_materias_estudiante_enroll
from api.serializers.alumno.matriculacion import MatriInscripcionSerializer, MatriPeriodoMatriculaSerializer, \
    MatriInscripcionMallaSerializer, MatriNivelMallaSerializer, MatriMateriaAsignadaSerializer, MatriNivelSerializer, \
    MatriMallaSerializer, MatriCarreraSerializer, MatriPersonaSerializer, MatriculaSerializer, \
    MatriMateriaSerializer, MatriAsignaturaMallaSerializer, MatriRequisitoIngresoUnidadIntegracionCurricularSerializer, \
    MatriSesionSerializer
from bd.models import UserToken
from matricula.models import PeriodoMatricula, DetalleSolicitudReservaCupoMateria
from settings import MATRICULACION_LIBRE, NIVEL_MALLA_CERO, NOTIFICA_ELIMINACION_MATERIA, FINANCIERO_GROUP_ID, \
    SECRETARIA_GROUP_ID, NOTA_ESTADO_EN_CURSO, HOMITIRCAPACIDADHORARIO
from sga.funciones import log, variable_valor, tituloinstitucion, lista_correo, null_to_numeric
from sga.models import PerfilUsuario, Periodo, ConfirmarMatricula, Nivel, AsignaturaMalla, Materia, Matricula, \
    AuditoriaMatricula, CUENTAS_CORREOS, MateriaAsignada, GruposProfesorMateria, ProfesorMateria, \
    AlumnosPracticaMateria, AgregacionEliminacionMaterias, Paralelo, Sesion, ModuloMalla
from inno.models import RequisitoIngresoUnidadIntegracionCurricular, RequisitoMateriaUnidadIntegracionCurricular
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from matricula.funciones import get_nivel_matriculacion, get_practicas_data, get_horarios_clases_data, \
    to_unicode, get_client_ip, get_tipo_matricula, calcula_nivel, valida_conflicto_materias_estudiante, \
    TIPO_PROFESOR_PRACTICA, get_horarios_practicas_informacion, get_horarios_practicas_data, \
    get_materias_x_inscripcion_x_asignatura_aux, generar_acta_compromiso, pre_inscripcion_practicas_pre_profesionales
from django.core.cache import cache

EJE_FORMATIVO_PRACTICAS = 9
EJE_FORMATIVO_VINCULACION = 11
EXCLUDE_EJE_FORMATIVO = [EJE_FORMATIVO_PRACTICAS, EJE_FORMATIVO_VINCULACION]


class AddRemoveMatriculaPregradoAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_ADD_REMOVE_MATRICULA'


    @api_security
    def post(self, request):
        TIEMPO_ENCACHE = 60 * 15
        try:
            hoy = datetime.now()
            payload = request.auth.payload
            if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
                ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
            else:
                ePerfilUsuario = PerfilUsuario.objects.db_manager("sga_select").get(pk=encrypt(payload['perfilprincipal']['id']))
                cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario, TIEMPO_ENCACHE)
            valid, msg_error = validate_entry_to_student_api(ePerfilUsuario, 'pregrado')
            if not valid:
                raise NameError(msg_error)

            ePeriodo = None
            if 'id' in payload['periodo']:
                periodoEnCache = cache.get(f"periodo_id_{payload['periodo']['id']}")
                if periodoEnCache:
                    ePeriodo = periodoEnCache
                else:
                    ePeriodo = Periodo.objects.db_manager("sga_select").get(pk=encrypt(payload['periodo']['id']))
                    cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)
            if Periodo is None:
                raise NameError(u"Periodo académico no encontrado, favor matricularse para ingresar a esta módulo")
            eInscripcion = ePerfilUsuario.inscripcion
            ePersona = eInscripcion.persona
            ePeriodoMatricula = None
            eMatricula = None
            action = request.data.get('action')
            if not action:
                raise NameError(u'Acción no permitida')

            if action == 'loadInitialData':
                try:
                    aData = {}
                    matricula_tardia = variable_valor('MATRICULA_TARDIA')
                    if matricula_tardia:
                        matricula_tardia_fecha = variable_valor('MATRICULA_TARDIA_FECHA')
                        hoy = matricula_tardia_fecha
                    idm = int(encrypt(request.data['idm'])) if 'idm' in request.data and request.data['idm'] else None
                    if not Matricula.objects.values('id').filter(pk=idm).exists():
                        raise NameError(u"Matricula no existe")
                    eMatricula = Matricula.objects.get(pk=idm)
                    eInscripcion = eMatricula.inscripcion
                    eInscripcionNivel = eInscripcion.mi_nivel()
                    eNivel = eMatricula.nivel
                    ePeriodoMatricula = None
                    if eNivel.periodo.periodomatricula_set.values('id').filter(status=True).exists():
                        ePeriodoMatricula = eNivel.periodo.periodomatricula_set.filter(status=True)[0]
                    if not ePeriodoMatricula:
                        raise NameError(u"Periodo académico de matrícula no existe")
                    tiene_rubro_pagado_matricula = False
                    tiene_rubro_pagado_materias = False
                    if eMatricula.rubro_set.values("id").filter(status=True).exists():
                        tiene_rubro_pagado_materias = tiene_rubro_pagado_matricula = eMatricula.tiene_pagos_matricula()
                    # eMateriasAsignadas = eMatricula.materiaasignada_set.filter(status=True).order_by('materia__asignaturamalla__nivelmalla__orden')
                    materias_ingles = Materia.objects.filter(status=True, asignaturamalla__malla_id__in=[353],nivel__periodo=eNivel.periodo).values_list('asignaturamalla__asignatura_id', flat=True).distinct()
                    eMateriasAsignadas = eMatricula.materiaasignada_set.filter(status=True).exclude(materia__asignaturamalla__asignatura_id__in=materias_ingles).order_by('materia__asignaturamalla__nivelmalla__orden')
                    """EMPIEZA RESPECTO A ASIGNATURAS MALLA """
                    eInscripcionMalla = eInscripcion.malla_inscripcion()
                    record = eInscripcion.recordacademico().filter(status=True, aprobada=True, asignaturamalla__isnull=False)
                    AsignaturasMalla = eInscripcionMalla.malla.asignaturamalla_set.filter(status=True).exclude(nivelmalla_id=NIVEL_MALLA_CERO)
                    AsignaturasMalla = AsignaturasMalla.exclude(pk__in=eMateriasAsignadas.values_list('materia__asignaturamalla_id', flat=True))
                    AsignaturasMalla = AsignaturasMalla.exclude(pk__in=record.values_list('asignaturamalla_id', flat=True)).order_by('nivelmalla__orden')
                    va_ultima_matricula = eInscripcion.va_ultima_matricula(ePeriodoMatricula.num_matriculas)
                    num_va_ultima_matricula = eInscripcion.num_va_ultima_matricula(ePeriodoMatricula.num_matriculas)
                    aAsignaturasMalla = []
                    for eAsignaturaMalla in AsignaturasMalla:
                        puedetomar = eInscripcion.puede_tomar_materia(eAsignaturaMalla.asignatura)
                        estado = eInscripcion.estado_asignatura(eAsignaturaMalla.asignatura)
                        totalmatriculaasignatura = eInscripcion.total_record_asignaturatodo(eAsignaturaMalla.asignatura)
                        if not estado in [1, 2]:
                            if eInscripcion.itinerario:
                                if eAsignaturaMalla.itinerario:
                                    if eInscripcion.itinerario == eAsignaturaMalla.itinerario:
                                        estado = 3
                                    else:
                                        estado = 0
                                else:
                                    estado = 3
                            else:
                                estado = 3

                        aMaterias = []
                        aRequisitos = []
                        puede_ver_horario = 0
                        """PERMITE QUE UNICAMENTE PUEDAN SELECCIONAR SOLO MATERIAS DE TERCERA MATRICULA"""
                        if va_ultima_matricula and num_va_ultima_matricula >= ePeriodoMatricula.num_materias_maxima_ultima_matricula and puedetomar and estado in [2, 3] and totalmatriculaasignatura != (ePeriodoMatricula.num_matriculas - 1) and eAsignaturaMalla.nivelmalla.orden > eInscripcionNivel.nivel.orden:
                            puedetomar = False
                        if puedetomar and estado in [2, 3] and totalmatriculaasignatura < ePeriodoMatricula.num_matriculas:
                            eMateriasAbiertas = Materia.objects.filter(Q(asignatura=eAsignaturaMalla.asignatura, inicio__gte=hoy, nivel__cerrado=False, nivel__periodo=eNivel.periodo), status=True).order_by('id')
                            if ePeriodoMatricula and ePeriodoMatricula.valida_materia_carrera:
                                eMateriasAbiertas = eMateriasAbiertas.filter(asignaturamalla__malla=eInscripcion.mi_malla()).distinct().order_by('id')
                            eSesiones = Sesion.objects.filter(status=True, clasificacion=1, tipo=1)
                            PRESENCIALES = [1, 4, 5]
                            SEMIPRESENCIALES = [7]
                            EN_LINEA = [13]
                            if eInscripcion.sesion_id in PRESENCIALES:
                                eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.filter(pk__in=PRESENCIALES))
                            elif eInscripcion.sesion_id in EN_LINEA:
                                eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.filter(pk__in=EN_LINEA))
                            elif eInscripcion.sesion_id in SEMIPRESENCIALES:
                                eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.filter(pk__in=SEMIPRESENCIALES))
                            else:
                                eModalidad = eInscripcion.modalidad
                                if eModalidad:
                                    if eModalidad.es_presencial():
                                        eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.filter(pk__in=PRESENCIALES))
                                    elif eModalidad.es_semipresencial():
                                        eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.filter(pk__in=SEMIPRESENCIALES))
                                    elif eModalidad.es_enlinea():
                                        eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.filter(pk__in=EN_LINEA))
                                    else:
                                        eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.none())
                                else:
                                    eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion__in=eSesiones.none())
                            if ePeriodoMatricula and ePeriodoMatricula.valida_seccion and not va_ultima_matricula:
                                eMateriasAbiertas_s = eMateriasAbiertas.filter(nivel__sesion=eInscripcion.sesion)
                                capacidad = null_to_numeric(eMateriasAbiertas_s.aggregate(capacidad=Sum('cupo'))['capacidad'])
                                asignados = MateriaAsignada.objects.values("id").filter(status=True, materia__in=eMateriasAbiertas).count()
                                if eMateriasAbiertas_s.values("id").exists() and asignados < capacidad:
                                    eMateriasAbiertas = eMateriasAbiertas_s
                            if ePeriodoMatricula.puede_agregar_materia_rubro_pagados:
                                if len(eMateriasAbiertas.values("id")) > 0:
                                    puede_ver_horario = 1
                            else:
                                if len(eMateriasAbiertas.values("id")) > 0 and not tiene_rubro_pagado_materias:
                                    puede_ver_horario = 1

                            if puede_ver_horario == 1:
                                if eAsignaturaMalla.validarequisitograduacion:
                                    eRequisitos_aux = RequisitoMateriaUnidadIntegracionCurricular.objects.filter(materia__in=eMateriasAbiertas, status=True, activo=True, obligatorio=True, inscripcion=True)
                                    eRequisitos = RequisitoIngresoUnidadIntegracionCurricular.objects.filter(asignaturamalla=eAsignaturaMalla, requisito__id__in=eRequisitos_aux.values_list("requisito__id", flat=True)).distinct()
                                    # eRequisitos = RequisitoIngresoUnidadIntegracionCurricular.objects.filter(status=True, asignaturamalla=eAsignaturaMalla, activo=True, obligatorio=True)
                                    for eRequisito in eRequisitos:
                                        eRequisito_data = MatriRequisitoIngresoUnidadIntegracionCurricularSerializer(eRequisito).data
                                        if eRequisito.enlineamatriculacion:
                                            # ultimoNivel = eInscripcionMalla.malla.ultimo_nivel_malla()
                                            ultimoNivel = eAsignaturaMalla.nivelmalla
                                            cumple = False
                                            if eMateriasAbiertas.values("id").filter(asignaturamalla__nivelmalla=ultimoNivel).exists():
                                                numAsignaturasOfertadas = len(eMateriasAbiertas.values("id").filter(Q(asignaturamalla__itinerario=0) | Q(asignaturamalla__itinerario__isnull=True), asignaturamalla__nivelmalla=ultimoNivel).exclude(asignaturamalla__validarequisitograduacion=True)) + len(eMateriasAbiertas.values("id").filter(asignaturamalla__itinerario__gt=0, asignaturamalla__nivelmalla=ultimoNivel).exclude(asignaturamalla__validarequisitograduacion=True))
                                                numAsignaturasSeleccionadas = len(eMateriasAsignadas.values("id").filter(Q(materia__asignaturamalla__itinerario=0) | Q(materia__asignaturamalla__itinerario__isnull=True), materia__asignaturamalla__nivelmalla=ultimoNivel).exclude(materia__asignaturamalla__validarequisitograduacion=True)) + len(eMateriasAsignadas.values("id").filter(materia__asignaturamalla__itinerario__gt=0, materia__asignaturamalla__nivelmalla=ultimoNivel).exclude(materia__asignaturamalla__validarequisitograduacion=True))
                                                if numAsignaturasOfertadas > numAsignaturasSeleccionadas:
                                                    cumple = False
                                                else:
                                                    cumple = True
                                            eRequisito_data.__setitem__('cumple', cumple)
                                        else:
                                            cumple = eRequisito.run(eInscripcion.pk)
                                            eRequisito_data.__setitem__('cumple', cumple)
                                        aRequisitos.append(eRequisito_data)

                            for eMateria in eMateriasAbiertas:
                                eMateria_data = MatriMateriaSerializer(eMateria).data
                                eMateria_data.__setitem__('horarios', get_horarios_clases_data(eMateria) if ePeriodoMatricula.valida_conflicto_horario or ePeriodoMatricula.ver_horario_materia else [])
                                eMateria_data.__setitem__('mispracticas', get_practicas_data(eMateria))
                                eMateria_data.__setitem__('disponibles', eMateria.capacidad_disponible() if ePeriodoMatricula.valida_cupo_materia else 0)
                                # eMateria.__setitem__('carrera', to_unicode(eM.asignaturamalla.malla.carrera.nombre_completo()) if eM.asignaturamalla.malla.carrera.nombre else "")
                                eMateria_data.__setitem__('profesor', (eMateria.profesor_principal().persona.nombre_completo()) if eMateria.profesor_principal() else 'SIN DEFINIR')
                                eMateria_data.__setitem__('session', to_unicode(eMateria.nivel.sesion.nombre))
                                eMateria_data.__setitem__('tipomateria_display', eMateria.get_tipomateria_display())
                                aMaterias.append(eMateria_data)

                        eAsignaturaMalla_data = MatriAsignaturaMallaSerializer(eAsignaturaMalla).data
                        eAsignaturaMalla_data.__setitem__('predecesoras', [p.predecesora.asignatura.nombre for p in eAsignaturaMalla.lista_predecesoras()])
                        eAsignaturaMalla_data.__setitem__('totalrecordasignatura', totalmatriculaasignatura)
                        eAsignaturaMalla_data.__setitem__('va_num_matricula', totalmatriculaasignatura + 1)
                        eAsignaturaMalla_data.__setitem__('cantidad_predecesoras', eAsignaturaMalla.cantidad_predecesoras())
                        eAsignaturaMalla_data.__setitem__('puede_ver_horario', puede_ver_horario)
                        eAsignaturaMalla_data.__setitem__('estado', estado)
                        eAsignaturaMalla_data.__setitem__('eMaterias', aMaterias)
                        eAsignaturaMalla_data.__setitem__('ejeformativo', eAsignaturaMalla.ejeformativo.nombre)
                        eAsignaturaMalla_data.__setitem__('aRequisitos', aRequisitos)
                        eAsignaturaMalla_data.__setitem__('orden', eAsignaturaMalla.nivelmalla.orden)
                        eAsignaturaMalla_data.__setitem__('asigmal_id', eAsignaturaMalla.id)
                        eAsignaturaMalla_data.__setitem__('tiene_solicitud_cupo', eAsignaturaMalla.detallesolicitudreservacupomateria_set.filter(status=True, solicitud__inscripcion=eInscripcion, solicitud__periodomatricula=ePeriodoMatricula).exists())
                        aAsignaturasMalla.append(eAsignaturaMalla_data)
                    eMatricula_serializer = MatriculaSerializer(eMatricula)
                    aData['eMatricula'] = eMatricula_serializer.data if eMatricula_serializer else None
                    eMateriaAsignada_ = []
                    for eMA in eMateriasAsignadas:
                        eMateriaAsignada_serializer = MatriMateriaAsignadaSerializer(eMA)
                        _eMateriaAsignada = eMateriaAsignada_serializer.data if eMateriaAsignada_serializer else []
                        if _eMateriaAsignada:
                            eMateria_serializer = MatriMateriaSerializer(eMA.materia)
                            eMateria = eMateria_serializer.data if eMateria_serializer else None
                            eMateria.__setitem__('horarios', get_horarios_clases_data(eMA.materia) if ePeriodoMatricula.valida_conflicto_horario or ePeriodoMatricula.ver_horario_materia else [])
                            mipractica = None
                            if AlumnosPracticaMateria.objects.values("id").filter(materiaasignada__matricula__inscripcion=eInscripcion, status=True, materiaasignada__status=True).exists():
                                apm = AlumnosPracticaMateria.objects.filter(materiaasignada__matricula__inscripcion=eInscripcion, status=True, materiaasignada__status=True)[0]
                                if apm.grupoprofesor:
                                    mipractica = {"id": apm.grupoprofesor.id,
                                                  "horarios_verbose": get_horarios_practicas_informacion(apm.grupoprofesor) if ePeriodoMatricula and ePeriodoMatricula.ver_horario_materia else '',
                                                  "horarios": get_horarios_practicas_data(apm.grupoprofesor) if ePeriodoMatricula and ePeriodoMatricula.valida_conflicto_horario else [],
                                                  "cupos": apm.grupoprofesor.cupo if ePeriodoMatricula and ePeriodoMatricula.valida_cupo_materia else 0,
                                                  "disponibles": apm.grupoprofesor.cuposdisponiblesgrupoprofesor() if ePeriodoMatricula and ePeriodoMatricula.valida_cupo_materia else 0,
                                                  "paralelo": apm.grupoprofesor.get_paralelopractica_display(),
                                                  "profesor": apm.grupoprofesor.profesormateria.profesor.persona.nombre_completo_inverso().__str__(),
                                                  }
                            eMateria.__setitem__('mispracticas', mipractica)
                            _eMateriaAsignada['materia'] = eMateria
                        eMateriaAsignada_.append(_eMateriaAsignada)
                    aData['eMateriasAsignadas'] = eMateriaAsignada_
                    aData['eAsignaturasMalla'] = aAsignaturasMalla
                    aData['validacion_matricula'] = validacion_matricula = variable_valor('VALIDACION_MATRICULA')
                    aData['validacion_matricula_reserva'] = validacion_matricula_reserva = variable_valor('VALIDACION_MATRICULA_RESERVA')
                    # if validacion_matricula_reserva:
                    #     solicitud = eInscripcion.solicitudreservacupomateria_set.filter(status = True).first()
                    #     if solicitud:
                    #         solicitud_serializer = SolicitudReservaCupoMateriaSerializer(solicitud).data
                    #         aData['solicitud_serializer'] = solicitud_serializer
                    if validacion_matricula == True:
                        matricula_primer_nivel = False
                        eMatriculaAnterior = Matricula.objects.filter(status=True,inscripcion=eInscripcion).order_by('-nivel__periodo_id')
                        asignatura_esp_sin_registro = False
                        if eMatriculaAnterior:
                            if eMatriculaAnterior.count() >= 2:
                                eMatriculaAnterior = eMatriculaAnterior[1]
                            else:
                                eMatriculaAnterior = eMatriculaAnterior.first()
                                matricula_primer_nivel = True
                            eInscripcion_mat = eMatriculaAnterior.inscripcion
                            nivel_real = eMatriculaAnterior.nivelmalla.orden
                        else:
                            eInscripcion_mat = eInscripcion
                            nivel_real = eInscripcion_mat.mi_nivel().nivel.orden
                        EJE_FORMATIVO_PRACTICAS = 9
                        EJE_FORMATIVO_VINCULACION = 11
                        EXCLUDE_EJE_FORMATIVO = [EJE_FORMATIVO_PRACTICAS, EJE_FORMATIVO_VINCULACION]
                        eInscripcionMalla_mat = eInscripcion_mat.malla_inscripcion()
                        eMalla_mat = eInscripcionMalla_mat.malla
                        eInscripcionNivel_mat = eInscripcion_mat.mi_nivel()
                        itinerario = []
                        itinerario.append(0)
                        if eInscripcionMalla_mat.malla.modalidad.id == 3:
                            eAsignaturasMalla = eMalla_mat.asignaturamalla_set.select_related().filter(status=True).exclude(Q(nivelmalla_id=0) | Q(opcional=True)).order_by('nivelmalla','ejeformativo').filter(itinerario__in=itinerario)
                        else:
                            eAsignaturasMalla = eMalla_mat.asignaturamalla_set.select_related().filter(
                                status=True).exclude(Q(nivelmalla_id=0) | Q(opcional=True) | Q(ejeformativo_id__in=EXCLUDE_EJE_FORMATIVO)).order_by('nivelmalla', 'ejeformativo').filter(itinerario__in=itinerario)
                        if eInscripcion_mat.itinerario:
                            if eInscripcion_mat.itinerario > 0:
                                itinerario.append(eInscripcion_mat.itinerario)
                                eAsignaturasMalla = eAsignaturasMalla.filter(itinerario__in=itinerario)
                        eModulosMalla = ModuloMalla.objects.filter(malla=eInscripcionMalla_mat.malla)
                        # eNivelMallaAprobadoActual = eInscripcionNivel_mat.nivel
                        eNivelMallaAprobadoActual = eInscripcion_mat.recordacademico_set.filter(
                            asignaturamalla__in=eAsignaturasMalla, status=True, aprobada=True).values_list(
                            'asignaturamalla__nivelmalla__orden', flat=True).order_by(
                            '-asignaturamalla__nivelmalla__orden').first()
                        regular = True
                        asignaturas_especiales = []
                        if eNivelMallaAprobadoActual:
                            eAsignaturasMallaquedebeaprobar = eAsignaturasMalla.filter(
                                nivelmalla__orden__lte=eNivelMallaAprobadoActual).exclude(
                                Q(asignatura__id__in=eModulosMalla.values_list('asignatura__id', flat=True)) | Q(asignatura__in=AsignaturaMalla.objects.values_list("asignatura__id", flat=True).filter(malla=eMalla_mat)))
                            eAsignaturasRecord = eInscripcion_mat.recordacademico_set.filter(asignaturamalla__in=eAsignaturasMalla,status=True)
                            regular = True
                            if eAsignaturasRecord.values("id").filter(aprobada=False).exists():
                                regular = False
                            elif eAsignaturasRecord.filter(asignaturamalla__in=eAsignaturasMallaquedebeaprobar,aprobada=True,status=True).count() < eAsignaturasMallaquedebeaprobar.values("id").count():
                                regular = False
                            elif eAsignaturasRecord.filter(asignaturamalla__in=eAsignaturasMalla.filter(nivelmalla__orden__gte=eNivelMallaAprobadoActual + 1).exclude(
                                    Q(asignatura__id__in=eModulosMalla.values_list('asignatura__id', flat=True)) | Q(
                                        asignatura__in=AsignaturaMalla.objects.values_list("asignatura__id",flat=True).filter(malla=eMalla_mat))), aprobada=True, status=True).exists():
                                regular = False
                            # -----------------------------------------------------Verificar si hay asignaturas sin aprobar hasta el nivel actual
                            if eInscripcionMalla_mat.malla.modalidad.id == 3:
                                eAsignaturasMallaHastaNivelActualTodas = eMalla_mat.asignaturamalla_set.select_related().filter(
                                    status=True, itinerario__in=itinerario, nivelmalla__orden__lte=eNivelMallaAprobadoActual).exclude(Q(nivelmalla_id=NIVEL_MALLA_CERO) | Q(opcional=True))
                            else:
                                eAsignaturasMallaHastaNivelActualTodas = eMalla_mat.asignaturamalla_set.select_related().filter(
                                    status=True, itinerario__in=itinerario, nivelmalla__orden__lte=eNivelMallaAprobadoActual).exclude(Q(nivelmalla_id=NIVEL_MALLA_CERO) | Q(opcional=True) | Q(ejeformativo_id__in=EXCLUDE_EJE_FORMATIVO))
                            asignaturas_sin_aprobar = eAsignaturasMallaHastaNivelActualTodas.exclude(
                                id__in=eAsignaturasRecord.values_list("asignaturamalla_id", flat=True))
                            asignatura_esp = eAsignaturasMallaHastaNivelActualTodas.exclude(
                                id__in=eAsignaturasRecord.values_list("asignaturamalla_id", flat=True)).filter(
                                id__in=list(map(int, variable_valor('ASIGNATURAS_ESPECIALES'))))
                            asignaturas_especiales = []
                            if asignatura_esp:
                                asignaturas_especiales = [asig_esp.id for asig_esp in asignatura_esp]
                                asignatura_esp_sin_registro = True
                            aData['asignatura_esp_sin_registro'] = asignatura_esp_sin_registro
                            if asignaturas_sin_aprobar.exists():
                                regular = False
                            elif eAsignaturasRecord.values("id").filter(aprobada=False).exists():
                                regular = False

                            nivel_real = nivel_real + 1 if regular else nivel_real

                            if matricula_primer_nivel:
                                nivel_orden = eMatriculaAnterior.nivelmalla.orden
                                if nivel_orden == 1:
                                    regular = True
                                    nivel_real = 1
                            if regular and eMatriculaAnterior:
                                niv_record = eNivelMallaAprobadoActual
                                if niv_record:
                                    nivel_real = niv_record + 1
                        aData['regular'] = regular
                        aData['nivel_real'] = nivel_real
                        aData['asignaturas_especiales'] = asignaturas_especiales
                        ## VALIDAR PRECEDENCIA 3ERA MATRICULA
                        eInscripcionMalla_prec = eInscripcion_mat.malla_inscripcion()
                        if eInscripcionMalla_prec.malla.modalidad.id == 3:
                            asignaturas_malla = eInscripcionMalla_prec.malla.asignaturamalla_set.select_related().filter(
                                status=True).exclude((Q(nivelmalla_id=NIVEL_MALLA_CERO) | Q(opcional=True))).order_by(
                                'nivelmalla', 'ejeformativo')
                        else:
                            asignaturas_malla = eInscripcionMalla_prec.malla.asignaturamalla_set.select_related().filter(
                                status=True).exclude((Q(nivelmalla_id=NIVEL_MALLA_CERO) | Q(opcional=True) | Q(
                                ejeformativo_id__in=EXCLUDE_EJE_FORMATIVO))).order_by('nivelmalla', 'ejeformativo')
                        val_terc_prec = False
                        for am in asignaturas_malla:
                            puedetomar = eInscripcion_mat.puede_tomar_materia(am.asignatura)
                            estado = eInscripcion_mat.estado_asignatura(am.asignatura)
                            totalmatriculaasignatura = eInscripcion_mat.total_record_asignaturatodo(am.asignatura)
                            if puedetomar == False and estado == 2 and totalmatriculaasignatura == 2 and val_terc_prec == False:
                                val_terc_prec = True
                        aData['val_terc_prec'] = val_terc_prec
                    eDetalleSolicitudReservaCupoMateria = DetalleSolicitudReservaCupoMateria.objects.filter(status=True,
                                                                                                            solicitud__inscripcion_id=eInscripcion.id,
                                                                                                            solicitud__periodomatricula_id=ePeriodoMatricula.id).values_list(
                        'asignaturamalla', 'sesion__nombre', 'id')
                    eSesionesReservaAsignatura = Sesion.objects.filter(status=True, pk__in=[1, 4, 5])
                    aData['eDetalleSolicitudReservaCupoMateria'] = eDetalleSolicitudReservaCupoMateria if eDetalleSolicitudReservaCupoMateria else []
                    aData['eSesionesReservaAsignatura'] = MatriSesionSerializer(eSesionesReservaAsignatura, many=True).data if MatriSesionSerializer(eSesionesReservaAsignatura, many=True) else []

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == "generateCodeEliminarMatricula":
                with transaction.atomic():
                    try:
                        if not 'id' in request.data:
                            raise NameError(u"Matrícula no valida")
                        if not Matricula.objects.values("id").filter(pk=encrypt(request.data['id'])).exists():
                            raise NameError(u"Matrícula no encontrada")
                        eMatricula = Matricula.objects.get(pk=encrypt(request.data['id']))
                        return generateCodeDeleteMatricula(request, eMatricula)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == "cancelarEliminarMatricula":
                with transaction.atomic():
                    try:
                        if not 'id' in request.data:
                            raise NameError(u"Matrícula no valida")
                        if not Matricula.objects.values("id").filter(pk=encrypt(request.data['id'])).exists():
                            raise NameError(u"Matrícula no encontrada")
                        eMatricula = Matricula.objects.get(pk=encrypt(request.data['id']))
                        tokens = eMatricula.matriculatoken_set.filter(status=True, isActive=True)
                        tokens.update(isActive=False)
                        UserToken.objects.filter(pk__in=tokens.values("user_token__id")).update(isActive=False)
                        return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == "reenviarEliminarMatricula":
                with transaction.atomic():
                    try:
                        if not 'id' in request.data:
                            raise NameError(u"Matricula no valida")
                        if not Matricula.objects.values("id").filter(pk=encrypt(request.data['id'])).exists():
                            raise NameError(u"Matricula no encontrada")
                        eMatricula = Matricula.objects.get(pk=encrypt(request.data['id']))
                        if not eMatricula.puede_reenviar_email_token():
                            raise NameError(u"Ha agotado el número máximo de reenvio de correo electrónico por día de la matrícula")
                        return reenvioCodeDeleteMatricula(request, eMatricula)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteMatricula':
                with transaction.atomic():
                    try:
                        if not 'id' in request.data:
                            raise NameError(u"Matricula no valida")
                        if not Matricula.objects.values("id").filter(pk=encrypt(request.data['id'])).exists():
                            raise NameError(u"Matricula no encontrada")
                        eMatricula = Matricula.objects.get(pk=encrypt(request.data['id']))
                        if eMatricula.rubro_set.values("id").filter(status=True).exists():
                            if eMatricula.tiene_pagos_matricula():
                                raise NameError(u"No puede eliminar la matricula, porque existen rubros de la matricula ya cancelados.")
                        if not 'utilizaSeguridad' in request.data:
                            raise NameError(u"Código no valido")
                        utilizaSeguridad = request.data['utilizaSeguridad'] == '1' or request.data['utilizaSeguridad'] == 1
                        if utilizaSeguridad:
                            if not 'code' in request.data:
                                raise NameError(u"Código no valido")
                            code = request.data['code']
                            tokens = eMatricula.matriculatoken_set.filter(status=True, isActive=True, user_token__isActive=True, user_token__action_type=3, user_token__date_expires__gte=datetime.now())
                            if not tokens.values("id").filter(codigo=code).exists():
                                raise NameError(u"Código no valido")
                            tokens.update(isActive=False)
                            UserToken.objects.filter(pk__in=tokens.values("user_token__id")).update(isActive=False)

                        delpersona = eMatricula
                        auditoria = AuditoriaMatricula(inscripcion=eMatricula.inscripcion,
                                                       periodo=eMatricula.nivel.periodo,
                                                       tipo=3)
                        auditoria.save(request)
                        if eMateriaAsig := eMatricula.materiaasignada_set.filter(status=True, materia__asignaturamalla__asignaturapracticas=True).first():
                            pre_inscripcion_practicas_pre_profesionales(request, eMateriaAsig, eMatricula, None, 'del')
                        eMatricula.delete()
                        try:
                            if NOTIFICA_ELIMINACION_MATERIA:
                                send_html_mail("Matricula eliminada",
                                               "emails/matriculaeliminada.html",
                                               {
                                                   'sistema': 'SIE',
                                                   'matricula': delpersona,
                                                   't': tituloinstitucion()
                                               }, lista_correo([FINANCIERO_GROUP_ID, SECRETARIA_GROUP_ID]), [],
                                               cuenta=CUENTAS_CORREOS[0][1])
                            send_html_mail("Confirmación de retiro de materia",
                                           "emails/confirmacion_matricula_eliminada.html",
                                           {
                                               'sistema': 'SIE',
                                               'fecha': datetime.now().date,
                                               'fecha_g': datetime.now().date(),
                                               'hora_g': datetime.now().time(),
                                               'persona': ePersona,
                                               'matricula': delpersona,
                                               't': tituloinstitucion(),
                                               'ip': get_client_ip(request),
                                           },
                                           ePersona.lista_emails(), [],
                                           cuenta=CUENTAS_CORREOS[7][1])
                        except Exception as ex1:
                            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                            pass
                        log(u'Elimino matricula: %s' % delpersona, request, "del")
                        return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == "generateRetiroMateria":
                with transaction.atomic():
                    try:
                        if not 'id' in request.data:
                            raise NameError(u"Materia no valida")
                        if not MateriaAsignada.objects.values("id").filter(pk=encrypt(request.data['id'])).exists():
                            raise NameError(u"Materia no encontrada")
                        eMateriaAsignada = MateriaAsignada.objects.get(pk=encrypt(request.data['id']))
                        return generateCodeRemoveMateria(request, eMateriaAsignada)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == "reenviarRetiroMateria":
                with transaction.atomic():
                    try:
                        if not 'id' in request.data:
                            raise NameError(u"Materia no valida")
                        if not MateriaAsignada.objects.values("id").filter(pk=encrypt(request.data['id'])).exists():
                            raise NameError(u"Materia no encontrada")
                        eMateriaAsignada = MateriaAsignada.objects.get(pk=encrypt(request.data['id']))
                        if not eMateriaAsignada.puede_reenviar_email_token():
                            raise NameError(u"Ha agotado el número máximo de reenvio de correo electrónico por día de la materia")
                        return reenvioCodeRemoveMateria(request, eMateriaAsignada)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == "cancelarRetiroMateria":
                with transaction.atomic():
                    try:
                        if not 'id' in request.data:
                            raise NameError(u"Materia no valida")
                        if not MateriaAsignada.objects.values("id").filter(pk=encrypt(request.data['id'])).exists():
                            raise NameError(u"Materia no encontrada")
                        eMateriaAsignada = MateriaAsignada.objects.get(pk=encrypt(request.data['id']))
                        tokens = eMateriaAsignada.materiaasignadatoken_set.filter(status=True, isActive=True)
                        tokens.update(isActive=False)
                        UserToken.objects.filter(pk__in=tokens.values("user_token__id")).update(isActive=False)
                        return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteMateria':
                with transaction.atomic():
                    try:
                        if not 'id' in request.data:
                            raise NameError(u"Materia no valida")
                        if not MateriaAsignada.objects.values("id").filter(pk=encrypt(request.data['id'])).exists():
                            raise NameError(u"Materia no encontrada")
                        eMateriaAsignada = MateriaAsignada.objects.get(pk=encrypt(request.data['id']))
                        if not 'utilizaSeguridad' in request.data:
                            raise NameError(u"Código no valido")
                        utilizaSeguridad = request.data['utilizaSeguridad'] == '1' or request.data['utilizaSeguridad'] == 1
                        if utilizaSeguridad:
                            if not 'code' in request.data:
                                raise NameError(u"Código no valido")
                            code = request.data['code']
                            tokens = eMateriaAsignada.materiaasignadatoken_set.filter(status=True, isActive=True,
                                                                                      user_token__isActive=True,
                                                                                      user_token__action_type=2,
                                                                                      user_token__date_expires__gte=datetime.now())
                            if not tokens.filter(codigo=code).exists():
                                raise NameError(u"Código no valido")
                            tokens.update(isActive=False)
                            UserToken.objects.filter(pk__in=tokens.values("user_token__id")).update(isActive=False)

                        eMatricula = eMateriaAsignada.matricula
                        eInscripcion = eMatricula.inscripcion
                        ePersona = eInscripcion.persona
                        ePeriodoMatricula = None
                        if eMatricula.nivel.periodo.periodomatricula_set.values('id').filter(status=True).exists():
                            ePeriodoMatricula = eMatricula.nivel.periodo.periodomatricula_set.filter(status=True)[0]
                        if not ePeriodoMatricula:
                            raise NameError(u"Periodo académico no existe")

                        # if matricula.rubro_set.filter(status=True, cancelado=True).exists():
                        #     raise NameError(u"No puede eliminar materia, porque existen rubros de la matricula cancelados")
                        eMateria = eMateriaAsignada.materia
                        if eMateria.asignaturamalla.asignaturapracticas:
                            pre_inscripcion_practicas_pre_profesionales(request, eMateriaAsignada, eMatricula, None, 'del')
                        if eMatricula.nivel.nivelgrado:
                            if len(eMatricula.materiaasignada_set.values('id').filter(status=True)) > 1:
                                bandera = 0
                                log(u'Elimino materia asignada: %s' % eMateriaAsignada, request, "del")
                                eMateriaAsignada.inactivar_detalle_rubro_matricula()
                                eMateriaAsignada.materia.descontar_cupo_adicional(request)
                                eMateriaAsignada.delete()
                                eMatricula.actualizar_horas_creditos()
                                eMatricula.aranceldiferido = 2
                                eMatricula.save(request)
                            else:
                                bandera = 1
                                if eMatricula.rubro_set.values("id").filter(status=True).exists():
                                    if eMatricula.tiene_pagos_matricula():
                                        raise NameError(u"No puede eliminar ultima materia, porque matricula tiene rubros pagados")
                                log(u'Elimino matricula por ultima materia: %s' % eMateriaAsignada, request, "del")
                                eMateriaAsignada.inactivar_detalle_rubro_matricula()
                                eMateriaAsignada.materia.descontar_cupo_adicional(request)
                                eMateriaAsignada.delete()
                                eMatricula.inactivar_detalle_rubro_matricula()
                                eMatricula.delete()
                        else:
                            if eMatricula.nivel.fechafinquitar >= datetime.now().date():
                                if len(eMatricula.materiaasignada_set.values('id').filter(status=True)) > 1:
                                    bandera = 0
                                    log(u'Elimino materia asignada: %s' % eMateriaAsignada, request, "del")
                                    eMateriaAsignada.inactivar_detalle_rubro_matricula()
                                    eMateriaAsignada.materia.descontar_cupo_adicional(request)
                                    eMatricula.eliminar_materia_api(eMateriaAsignada, ePersona, request)
                                    eMatricula.actualizar_horas_creditos()
                                    eMatricula.aranceldiferido = 2
                                    eMatricula.save(request)
                                else:
                                    bandera = 1
                                    if eMatricula.rubro_set.values("id").filter(status=True).exists():
                                        if eMatricula.tiene_pagos_matricula():
                                            raise NameError(u"No puede eliminar ultima materia, porque matricula tiene rubros pagados")
                                        log(u'Elimino matricula por ultima materia: %s' % eMateriaAsignada, request, "del")
                                        eMateriaAsignada.inactivar_detalle_rubro_matricula()
                                        eMateriaAsignada.materia.descontar_cupo_adicional(request)
                                        eMatricula.eliminar_materia_api(eMateriaAsignada, ePersona, request)
                                        eMatricula.inactivar_detalle_rubro_matricula()
                                        eMatricula.delete()
                                    else:
                                        log(u'Elimino materia asignada: %s' % eMateriaAsignada, request, "del")
                                        eMateriaAsignada.inactivar_detalle_rubro_matricula()
                                        eMateriaAsignada.materia.descontar_cupo_adicional(request)
                                        eMatricula.eliminar_materia_api(eMateriaAsignada, ePersona, request)
                                        eMatricula.actualizar_horas_creditos()
                                        eMatricula.aranceldiferido = 2
                                        eMatricula.save(request)
                            else:
                                raise NameError(u"No se puede eliminar, por lo menos debe de existir una materia")
                        # if CALCULO_POR_CREDITO:
                        if bandera == 0:
                            eMatricula.agregacion_aux(request)
                            eMatricula.actualizar_horas_creditos()
                            eMatricula.actualiza_matricula()
                            eMatricula.inscripcion.actualiza_estado_matricula()
                            valid, msg, aData = get_tipo_matricula(request, eMatricula)
                            if not valid:
                                raise NameError(msg)
                            cantidad_nivel = aData['cantidad_nivel']
                            porcentaje_perdidad_parcial_gratuidad = aData['porcentaje_perdidad_parcial_gratuidad']
                            cantidad_seleccionadas = aData['cantidad_seleccionadas']
                            porcentaje_seleccionadas = int(round(Decimal((float(cantidad_nivel) * float(porcentaje_perdidad_parcial_gratuidad)) / 100).quantize(Decimal('.00')), 0))
                            if (cantidad_seleccionadas < porcentaje_seleccionadas):
                                eMatricula.grupo_socio_economico(2)
                            else:
                                eMatricula.grupo_socio_economico(1)

                            calcula_nivel(eMatricula)
                            if ePeriodoMatricula.valida_envio_mail:
                                if NOTIFICA_ELIMINACION_MATERIA:
                                    try:
                                        send_html_mail("Materia eliminada",
                                                       "emails/materiaeliminada.html",
                                                       {
                                                           'sistema': request.session['nombresistema'],
                                                           'materia': eMateria,
                                                           'matricula': eMatricula,
                                                           't': tituloinstitucion()
                                                       }, lista_correo([FINANCIERO_GROUP_ID, SECRETARIA_GROUP_ID]), [],
                                                       cuenta=CUENTAS_CORREOS[0][1])
                                    except Exception as ex1:
                                        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                                        pass
                                try:
                                    send_html_mail("Confirmación de retiro de materia",
                                                   "emails/confirmacion_materia_eliminada.html",
                                                   {
                                                       'sistema': request.session['nombresistema'],
                                                       'fecha': datetime.now().date,
                                                       'fecha_g': datetime.now().date(),
                                                       'hora_g': datetime.now().time(),
                                                       'persona': ePersona,
                                                       'materia': eMateria,
                                                       'matricula': eMatricula,
                                                       't': tituloinstitucion(),
                                                       'ip': get_client_ip(request),
                                                   },
                                                   ePersona.lista_emails(), [],
                                                   cuenta=CUENTAS_CORREOS[7][1])
                                except Exception as ex1:
                                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                                    pass
                        eMateriaAsignadas = eMatricula.materiaasignada_set.filter(status=True)
                        itinerario = 0
                        if not eMateriaAsignadas.values("id").filter(materia__asignaturamalla__itinerario__gt=0).exists():
                            eInscripcion.itinerario = eInscripcion.mi_itinerario_record()
                            eInscripcion.save(request)
                            # itinerarios = eMateriaAsignadas.values_list('materia__asignaturamalla__itinerario', flat=True).distinct()
                        return Helper_Response(isSuccess=True, data={}, message=f'Se quito correctamente la materia', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error al quitar materia: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadCupoMateria':
                try:
                    if not 'aData' in request.data:
                        raise NameError(u"Parametro no valido")
                    if not 'idn' in request.data:
                        raise NameError(u"Parametro de nivel no valido")
                    if not 'idp' in request.data:
                        raise NameError(u"Parametro de paralelo no valido")
                    eNivel = Nivel.objects.get(pk=encrypt(request.data['idn']))
                    eParalelo = None
                    if int(request.data['idp']) > 0:
                        eParalelo = Paralelo.objects.get(pk=request.data['idp'])
                    aData = json.loads(request.data['aData'])
                    if not aData:
                        raise NameError(u"Parametro no valido")
                    eAsignaturasMalla = AsignaturaMalla.objects.filter(pk=encrypt(aData['id']))
                    if not eAsignaturasMalla.values("id").exists():
                        raise NameError(u"No se encontro la asignatura en malla")
                    eAsignaturaMalla = eAsignaturasMalla[0]
                    aData['eMaterias'] = get_materias_x_inscripcion_x_asignatura_aux(eNivel, eInscripcion, eAsignaturaMalla, eParalelo)
                    # eMaterias = []
                    # for m in aData['eMaterias']:
                    #     disponibles = 0
                    #     for key, value in m.items():
                    #         if 'id' == key:
                    #             eMateria = Materia.objects.get(pk=encrypt(m['id']))
                    #             disponibles = eMateria.capacidad_disponible()
                    #     m['disponibles'] = disponibles
                    #     eMaterias.append(m)
                    # aData['eMaterias'] = eMaterias
                    return Helper_Response(isSuccess=True, data={'aData': aData}, status=status.HTTP_200_OK)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadCupoPractica':
                try:
                    if not 'aData' in request.data:
                        raise NameError(u"Parametro no valido")
                    aData = json.loads(request.data['aData'])
                    if not aData:
                        raise NameError(u"Parametro no valido")
                    practicas = []
                    for p in aData['mispracticas']:
                        disponibles = 0
                        for key, value in p.items():
                            if 'id' == key:
                                eGruposProfesorMateria = GruposProfesorMateria.objects.get(pk=int(p['id']))
                                disponibles = eGruposProfesorMateria.cuposdisponiblesgrupoprofesor()
                        p['disponibles'] = disponibles
                        practicas.append(p)
                    aData['mispracticas'] = practicas
                    return Helper_Response(isSuccess=True, data={'aData': aData}, status=status.HTTP_200_OK)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'validConflictoHorario':
                try:
                    if not 'materias' in request.data:
                        raise NameError(u"Parametro de materias seleccionadas no valido")
                    mis_materias = json.loads(request.data['materias'])
                    if not 'materia' in request.data:
                        raise NameError(u"Parametro de materia seleccionada no valido")
                    mi_materia = json.loads(request.data['materia'])
                    mis_clases = []
                    mi_clase = []
                    for materia in mis_materias:
                        if 'mispracticas' in materia and materia['mispracticas'] and len(materia['mispracticas']['horarios']) > 0 and materia['validaconflictohorarioalu']:
                            mis_clases.append(materia['mispracticas']['horarios'])
                        if 'horarios' in materia and materia['horarios'] and len(materia['horarios']) > 0 and materia['validaconflictohorarioalu']:
                            mis_clases.append(materia['horarios'])
                    if 'mispracticas' in mi_materia and mi_materia['mispracticas'] and len(mi_materia['mispracticas']) > 0 and mi_materia['validaconflictohorarioalu']:
                        mi_clase.append(mi_materia['mispracticas']['horarios'])
                    if 'horarios' in mi_materia and mi_materia['horarios'] and len(mi_materia['horarios']) > 0 and mi_materia['validaconflictohorarioalu']:
                        mi_clase.append(mi_materia['horarios'])
                    tiene_conflicto, mensaje = False, 'No se registra conflicto de horario'
                    if len(mi_clase) > 0:
                        tiene_conflicto, mensaje = valida_conflicto_materias_estudiante(mis_clases, mi_clase)
                    return Helper_Response(isSuccess=True, data={"conflicto": tiene_conflicto, "mensaje": mensaje}, status=status.HTTP_200_OK)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'setMateria':
                with transaction.atomic():
                    try:
                        if not 'id' in request.data:
                            raise NameError(u"Parametro de matrícula no valida")
                        if not Matricula.objects.values("id").filter(pk=encrypt(request.data['id'])).exists():
                            raise NameError(u"Matrícula no valida")
                        eMatricula = Matricula.objects.get(pk=encrypt(request.data['id']))
                        eInscripcion = eMatricula.inscripcion
                        eMalla = eInscripcion.mi_malla()
                        ePersona = eInscripcion.persona
                        if not 'materias' in request.data:
                            raise NameError(u"Parametro de materias no valida")
                        mis_clases = json.loads(request.data['materias'])
                        if not 'materia' in request.data:
                            raise NameError(u"Parametro de materia seleccionada no valida")
                        mi_materia = json.loads(request.data['materia'])
                        if not Materia.objects.values("id").filter(pk=encrypt(mi_materia['id']),status=True).exists():
                            raise NameError(u"Materia seleccionada no valida")
                        eMateria = Materia.objects.get(pk=encrypt(mi_materia['id']))
                        # MATERIAS PRACTICAS
                        mi_practica = 0
                        mis_materias_congrupo = 0
                        if mi_materia['mispracticas']:
                            for k, v in mi_materia['mispracticas'].items():
                                if k == 'id':
                                    mi_practica = v
                                    mis_materias_congrupo = int(encrypt(mi_materia['id']))

                        mi_materia_singrupo = 0
                        if eMateria.asignaturamalla.tipomateria_id == TIPO_PROFESOR_PRACTICA:
                            if eMateria.id != mis_materias_congrupo:
                                mi_materia_singrupo = eMateria.id

                        if not eInscripcion.itinerario or eInscripcion.itinerario < 1:
                            if eMateria.asignaturamalla.itinerario > 0:
                                eInscripcion.itinerario = int(eMateria.asignaturamalla.itinerario)
                                eInscripcion.save(request)

                        if eMateria.asignaturamalla.practicas:
                            if mi_practica == 0:
                                raise NameError(u"Materia es TP, seleccione un horario de prácticas.")
                            # if not GruposProfesorMateria.objects.values("id").filter(pk=mi_practica).exists():
                            #     raise NameError(u"No existe grupo de prácticas.")
                            # grupoprofesormateria = GruposProfesorMateria.objects.get(pk=mi_practica)
                        # MATERIAS PRACTICAS
                        grupoprofesormaterias = GruposProfesorMateria.objects.filter(pk=mi_practica)
                        profesoresmateriassingrupo = ProfesorMateria.objects.filter(materia_id=mi_materia_singrupo, tipoprofesor_id=TIPO_PROFESOR_PRACTICA)

                        if eMatricula.inscripcion.existe_en_malla(eMateria.asignatura) and not eMatricula.inscripcion.puede_tomar_materia(eMateria.asignatura):
                            raise NameError(u"No puede tomar esta materia por tener precedencias")
                        if eMatricula.inscripcion.existe_en_modulos(eMateria.asignatura) and not eMatricula.inscripcion.puede_tomar_materia_modulo(eMateria.asignatura):
                            raise NameError(u"No puede tomar esta materia por tener precedencias")
                        ePeriodoMatricula = None
                        if eMatricula.nivel.periodo.periodomatricula_set.values('id').filter(status=True).exists():
                            ePeriodoMatricula = eMatricula.nivel.periodo.periodomatricula_set.filter(status=True)[0]
                        if not ePeriodoMatricula:
                            raise NameError(u"Periodo académico no existe")
                        if not ePeriodoMatricula.puede_agregar_materia:
                            raise NameError(u"No se permite agregar materia a la matricula")

                        if ePeriodoMatricula.valida_conflicto_horario and eInscripcion.carrera.modalidad != 3:
                            conflicto, msg = valida_conflicto_materias_estudiante_enroll(mis_clases)
                            if conflicto:
                                raise NameError(msg)
                        if ePeriodoMatricula.valida_cupo_materia:
                            if not eMateria.tiene_capacidad():
                                raise NameError(u"No existe cupo para esta materia.")
                                # VERIFICANDO CUPO MATERIAS PRACTICAS EN PROFESOR MATERIA CON PÁRALELO
                                for gpm in grupoprofesormaterias:
                                    validar = True
                                    if gpm.profesormateria.materia.tipomateria == TIPO_PROFESOR_PRACTICA:
                                        validar = variable_valor('VALIDAR_HORARIO_CUPO_MATERIA_VIRTUAL')
                                    if validar:
                                        if not HOMITIRCAPACIDADHORARIO and gpm.cuposdisponiblesgrupoprofesor() <= 0:
                                            raise NameError(u"Capacidad limite de la materia en la práctica:  " + str(gpm.profesormateria.materia) + ", seleccione otro.")

                        if eMatricula.materiaasignada_set.values('id').filter(materia=eMateria).exists():
                            raise NameError(u"Ya se encuentra matriculado en esta materia")

                        eMateriaAsignada = MateriaAsignada(matricula=eMatricula,
                                                           materia=eMateria,
                                                           notafinal=0,
                                                           asistenciafinal=0,
                                                           cerrado=False,
                                                           observaciones='',
                                                           estado_id=NOTA_ESTADO_EN_CURSO,
                                                           sinasistencia=False,
                                                           casoultimamatricula=eMatricula.mi_casoultimamatricula())
                        if ePeriodoMatricula.periodo.valida_asistencia:
                            if eMalla.modalidad.es_enlinea():
                                eMateriaAsignada.sinasistencia = True
                        else:
                            eMateriaAsignada.sinasistencia = True
                        eMateriaAsignada.save(request)

                        # MATRICULA EN LA PRACTICA QUE NO TENGAN GRUPO
                        if profesoresmateriassingrupo.values('id').filter(materia=eMateria).exists():
                            profemate = profesoresmateriassingrupo.filter(materia=eMateria)[0]
                            alumnopractica = AlumnosPracticaMateria(materiaasignada=eMateriaAsignada,
                                                                    profesormateria=profemate)
                            alumnopractica.save(request)
                            log(u'Materia (%s) con profesor practica (%s) seleccionada matrícula: %s en tabla alumnopractica (%s)' % (eMateria, profemate, eMateriaAsignada, alumnopractica.id), request, "add")
                        # MATRICULA EN LA PRACTICA QUE SI TENGAN GRUPOS
                        elif grupoprofesormaterias.values('id').filter(profesormateria__materia=eMateria).exists():
                            profemate_congrupo = grupoprofesormaterias.filter(profesormateria__materia=eMateria)[0]
                            if ePeriodoMatricula.valida_cupo_materia:
                                validar = True
                                if profemate_congrupo.profesormateria.materia.tipomateria == 2:
                                    validar = variable_valor('VALIDAR_HORARIO_CUPO_MATERIA_VIRTUAL')
                                if validar:
                                    if not HOMITIRCAPACIDADHORARIO and profemate_congrupo.cuposdisponiblesgrupoprofesor() <= 0:
                                        raise NameError(u"Capacidad limite de la materia en la práctica:  " + str(profemate_congrupo.profesormateria.materia) + ", seleccione otro.")

                            alumnopractica = AlumnosPracticaMateria(materiaasignada=eMateriaAsignada,
                                                                    profesormateria=profemate_congrupo.profesormateria,
                                                                    grupoprofesor=profemate_congrupo)
                            alumnopractica.save(request)
                            log(u'Materia (%s) con grupo profesor practica (%s) seleccionada matricula: %s en tabla alumnopractica (%s)' % (eMateria, profemate_congrupo, eMateriaAsignada, alumnopractica.id), request, "add")
                        eMateriaAsignada.matriculas = eMateriaAsignada.cantidad_matriculas()
                        eMateriaAsignada.asistencias()
                        eMateriaAsignada.evaluacion()
                        eMateriaAsignada.mis_planificaciones()
                        solicitud_cupo = eMateria.asignaturamalla.detallesolicitudreservacupomateria_set.filter(status=True, solicitud__inscripcion=eInscripcion, solicitud__periodomatricula=ePeriodoMatricula).values_list('id', flat=True)
                        if solicitud_cupo:
                            asignaturamalla = eMateria.asignaturamalla
                            asignaturamalla.detallesolicitudreservacupomateria_set.filter(status=True, solicitud__inscripcion=eInscripcion, solicitud__periodomatricula=ePeriodoMatricula).update(status=False)
                            log(f'Eliminó soliciutd de cupo de la asignatura : {asignaturamalla.asignatura} en el periodo {eMateria.nivel.periodo}', request, "del")

                        if eMateria.asignaturamalla.asignaturapracticas and eMateria.asignaturamalla.asignaturavinculacion:
                            pdf2, response2 = generar_acta_compromiso(eMateriaAsignada)
                            pre_inscripcion_practicas_pre_profesionales(request, eMateriaAsignada, eMatricula, pdf2, 'add')
                            eMateriaAsignada.actacompromisopracticas = pdf2
                            eMateriaAsignada.actacompromisovinculacion = pdf2
                        elif eMateria.asignaturamalla.asignaturapracticas:
                            pdf, response = generar_acta_compromiso(eMateriaAsignada)
                            pre_inscripcion_practicas_pre_profesionales(request, eMateriaAsignada, eMatricula, pdf, 'add')
                            eMateriaAsignada.actacompromisopracticas = pdf
                        elif eMateria.asignaturamalla.asignaturavinculacion:
                            pdfv, responsev = generar_acta_compromiso(eMateriaAsignada)
                            eMateriaAsignada.actacompromisovinculacion = pdfv
                        eMateriaAsignada.save(request)
                        if eMatricula.nivel.nivelgrado:
                            log(u'Adiciono materia: %s' % eMateriaAsignada, request, "add")
                        else:
                            if datetime.now().date() < eMateria.nivel.fechainicioagregacion:
                                # AGREGACION DE MATERIAS EN MATRICULACION REGULAR SIN REALIZAR PAGOS
                                eMateriaAsignada.save(request)
                                log(u'Adiciono materia: %s' % eMateriaAsignada, request, "add")
                            elif eMatricula.nivel.puede_agregar_materia_matricula():
                                # AGREGACION DE MATERIAS EN FECHAS DE AGREGACIONES
                                registro = AgregacionEliminacionMaterias(matricula=eMatricula,
                                                                         agregacion=True,
                                                                         asignatura=eMateriaAsignada.materia.asignatura,
                                                                         responsable=ePersona,
                                                                         fecha=datetime.now().date(),
                                                                         creditos=eMateriaAsignada.materia.creditos,
                                                                         nivelmalla=eMateriaAsignada.materia.nivel.nivelmalla if eMateriaAsignada.materia.nivel.nivelmalla else None,
                                                                         matriculas=eMateriaAsignada.matriculas)
                                registro.save(request)
                                log(u'Adiciono materia: %s' % eMateriaAsignada, request, "add")
                            else:
                                if not eMateria.asignatura.modulo:
                                    raise NameError(u"Materia no permitida")
                                registro = AgregacionEliminacionMaterias(matricula=eMatricula,
                                                                         agregacion=True,
                                                                         asignatura=eMateriaAsignada.materia.asignatura,
                                                                         responsable=ePersona,
                                                                         fecha=datetime.now().date(),
                                                                         creditos=eMateriaAsignada.materia.creditos,
                                                                         nivelmalla=eMateriaAsignada.materia.nivel.nivelmalla if eMateriaAsignada.materia.nivel.nivelmalla else None,
                                                                         matriculas=eMateriaAsignada.matriculas)
                                registro.save(request)
                                log(u'Adiciono materia: %s' % eMateriaAsignada, request, "add")
                        eMatricula.actualizar_horas_creditos()
                        eMatricula.actualiza_matricula()
                        eMatricula.inscripcion.actualiza_estado_matricula()
                        valid, msg, aData = get_tipo_matricula(request, eMatricula)
                        if not valid:
                            raise NameError(msg)
                        cantidad_nivel = aData['cantidad_nivel']
                        porcentaje_perdidad_parcial_gratuidad = aData['porcentaje_perdidad_parcial_gratuidad']
                        cantidad_seleccionadas = aData['cantidad_seleccionadas']
                        porcentaje_seleccionadas = int(round(Decimal((float(cantidad_nivel) * float(porcentaje_perdidad_parcial_gratuidad)) / 100).quantize(Decimal('.00')), 0))
                        if (cantidad_seleccionadas < porcentaje_seleccionadas):
                            eMatricula.grupo_socio_economico(2)
                        else:
                            eMatricula.grupo_socio_economico(1)
                        calcula_nivel(eMatricula)
                        eMatricula.agregacion_aux(request)
                        eMatricula.calcula_nivel()
                        eMatricula.aranceldiferido = 2
                        eMatricula.save(request)
                        return Helper_Response(isSuccess=True, data={}, message=f'Se adiciono correctamente la materia', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acción no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        TIEMPO_ENCACHE = 60 * 15
        try:
            aData = {}
            hoy = datetime.now().date()
            payload = request.auth.payload
            if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
                ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
            else:
                ePerfilUsuario = PerfilUsuario.objects.db_manager("sga_select").get(pk=encrypt(payload['perfilprincipal']['id']))
                cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario, TIEMPO_ENCACHE)
            valid, msg_error = validate_entry_to_student_api(ePerfilUsuario, 'pregrado')
            if not valid:
                raise NameError(msg_error)
            ePeriodo = None
            if 'id' in payload['periodo']:
                periodoEnCache = cache.get(f"periodo_id_{payload['periodo']['id']}")
                if periodoEnCache:
                    ePeriodo = periodoEnCache
                else:
                    ePeriodo = Periodo.objects.db_manager("sga_select").get(pk=encrypt(payload['periodo']['id']))
                    cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)
            eInscripcion = ePerfilUsuario.inscripcion
            ePersona = eInscripcion.persona
            ePeriodoMatricula = None
            eMatricula = None

            if not PeriodoMatricula.objects.values('id').filter(status=True, activo=True, tipo=2).exists():
                raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el periodo de matriculación se encuentra inactivo")
            ePeriodoMatricula = PeriodoMatricula.objects.filter(status=True, activo=True, tipo=2)
            if len(ePeriodoMatricula) > 1:
                raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, proceso de matriculación no se encuentra activo")
            ePeriodoMatricula = ePeriodoMatricula[0]
            if not ePeriodoMatricula.esta_periodoactivomatricula():
                raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el periodo de matriculación se encuentra inactivo")
            if eInscripcion.tiene_perdida_carrera(ePeriodoMatricula.num_matriculas):
                raise NameError(u"ATENCIÓN: Su limite de matricula por perdida de una o mas asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria para mas informacion.")
            if ePeriodoMatricula.periodo and eInscripcion.tiene_automatriculapregrado_por_confirmar(ePeriodoMatricula.periodo):
                return Helper_Response(isSuccess=True, data={"tipo": "automatricula", "aData": {"redirect": True, 'page': 'alu_matricula'}}, status=status.HTTP_200_OK)

            if ePeriodo and ePeriodoMatricula and ePeriodoMatricula.periodo.id == ePeriodo.id and ePersona.tiene_matricula_periodo(ePeriodo):
                eMatricula = eInscripcion.matricula_periodo2(ePeriodo)
                if not ConfirmarMatricula.objects.values('id').filter(matricula=eMatricula).exists():
                    raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, le informamos que ya se encuentra matriculado en el Periodo {ePeriodo.__str__()}. <br>Verificar en el módulo <a href='/alu_materias' class='bloqueo_pantalla'>Mis Materias</a>")

            eNivel = None
            eNivel_id = get_nivel_matriculacion(eInscripcion, ePeriodoMatricula.periodo)
            if eNivel_id < 0:
                if eNivel_id == -1:
                    raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el periodo de matriculación no se encuentra activo")
                if eNivel_id == -2:
                    raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, no existen niveles con cupo para matricularse")
                if eNivel_id == -3:
                    raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, no existen paralelos disponibles")
                if eNivel_id == -4:
                    raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, no existen paralelos para su nivel")
            eNivel = Nivel.objects.get(pk=eNivel_id)
            if not Matricula.objects.values('id').filter(inscripcion=eInscripcion,nivel__periodo=ePeriodoMatricula.periodo).exists():
                raise NameError(u"ATENCIÓN: Para usar este módulo, debe estar matriculado en el periodo actual: [%s]" % ePeriodoMatricula.periodo)

            eMalla = None
            eInscripcionMalla = eInscripcion.malla_inscripcion()
            if not eInscripcion.tiene_malla():
                raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, debe tener malla asociada para poder matricularse.")
            eMalla = eInscripcionMalla.malla
            eAsignaturasMallas = AsignaturaMalla.objects.filter(status=True, malla_id=eInscripcion.mi_malla().id)
            ePersona_serializer = MatriPersonaSerializer(ePersona)
            eInscripcion_serializer = MatriInscripcionSerializer(eInscripcion)
            eCarrera_serializer = MatriCarreraSerializer(eInscripcion.carrera)
            eNivelMalla_serializer = MatriNivelMallaSerializer(eInscripcion.mi_nivel().nivel)
            eNivelesMalla_serializer = MatriNivelMallaSerializer(eInscripcionMalla.malla.niveles_malla(), many=True)
            eInscripcionMalla_serializer = MatriInscripcionMallaSerializer(eInscripcion.malla_inscripcion())
            ePeriodoMatricula_serializer = MatriPeriodoMatriculaSerializer(ePeriodoMatricula)
            eNivel_serializer = MatriNivelSerializer(eNivel)
            eMalla_serializer = MatriMallaSerializer(eMalla)
            aData['ePersona'] = ePersona_serializer.data if ePersona_serializer else None
            aData['eInscripcion'] = eInscripcion_serializer.data if eInscripcion_serializer else None
            aData['itinerario'] = eInscripcion.itinerario if eInscripcion.itinerario else 0
            aData['eCarrera'] = eCarrera_serializer.data if eCarrera_serializer else None
            aData['eNivelMalla'] = eNivelMalla_serializer.data if eNivelMalla_serializer else None
            aData['eNivelesMalla'] = eNivelesMalla_serializer.data if eNivelesMalla_serializer else []
            aData['isItinerarios'] = eInscripcionMalla.malla.tiene_itinerarios()
            aData['listItinerarios'] = eInscripcionMalla.malla.lista_itinerarios()
            aData['eInscripcionMalla'] = eInscripcionMalla_serializer.data if eInscripcionMalla_serializer else None
            aData['ePeriodoMatricula'] = ePeriodoMatricula_serializer.data if ePeriodoMatricula_serializer else None
            aData['matriculacionLibre'] = MATRICULACION_LIBRE
            aData['eNivel'] = eNivel_serializer.data if eNivel_serializer else None
            aData['eMalla'] = eMalla_serializer.data if eMalla_serializer else None
            aData['vaUltimaMatricula'] = eInscripcion.va_ultima_matricula(ePeriodoMatricula.num_matriculas)
            aData['numVaUltimaMatricula'] = eInscripcion.num_va_ultima_matricula(ePeriodoMatricula.num_matriculas)
            aData['totalMateriasNivel'] = eInscripcion.total_materias_nivel()
            aData['totalMateriasPendientesMalla'] = eInscripcion.total_materias_pendientes_malla()
            aData['puedeMatricularseOtraVez'] = variable_valor('PUEDE_MATRICULARSE_OTRA_VEZ')
            aData['FichaSocioEconomicaINEC'] = ePersona.fichasocioeconomicainec()
            aData['Title'] = "Adicionar y Quitar - Matriculación Online"
            return Helper_Response(isSuccess=True, data={"tipo": "matricula", "aData": aData}, status=status.HTTP_200_OK)
        except Exception as ex:
            mensaje_ex = f'Error on line {sys.exc_info()[-1].tb_lineno} {ex.__str__()}'
            print(mensaje_ex)
            return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)
