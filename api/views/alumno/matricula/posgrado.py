# coding=utf-8
import json
import sys
from datetime import datetime
from django.db import transaction
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status

from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.views.alumno.matricula.functions import validate_entry_to_student_api, action_enroll_posgrado
from api.serializers.alumno.matriculacion import MatriInscripcionSerializer, MatriPeriodoMatriculaSerializer, \
    MatriInscripcionMallaSerializer, MatriNivelMallaSerializer, MatriMateriaAsignadaSerializer, MatriNivelSerializer, \
    MatriMallaSerializer, MatriCarreraSerializer, MatriPersonaSerializer, MatriPreMatriculaSerializer, \
    MatriculaSerializer, MatriCasoUltimaMatriculaSerializer, MatriRequisitoIngresoUnidadIntegracionCurricularSerializer
from matricula.models import PeriodoMatricula, CasoUltimaMatricula
from settings import MATRICULACION_LIBRE, NIVEL_MALLA_CERO, NIVEL_MALLA_UNO
from sga.funciones import log, variable_valor
from sga.models import Noticia, Inscripcion, PerfilUsuario, Periodo, ConfirmarMatricula, Nivel, AsignaturaMalla, \
    RecordAcademico, Materia, GruposProfesorMateria, NivelMalla, Matricula, Persona
from inno.models import RequisitoIngresoUnidadIntegracionCurricular
from posgrado.models import ITINERARIO_ASIGNATURA_MALLA
from sga.templatetags.sga_extras import encrypt
from matricula.funciones import get_nivel_matriculacion, puede_matricularse_seguncronograma_carrera, \
    puede_matricularse_seguncronograma_coordinacion, ubicar_nivel_matricula, get_practicas_data, \
    get_horarios_clases_informacion, get_deuda_persona_posgrado, get_horarios_clases_data, valida_conflicto_materias_estudiante,\
    valid_intro_module_estudiante, to_unicode, get_bloqueo_matricula_posgrado
from django.core.cache import cache
from settings import SIMPLE_JWT
from hashlib import md5
from bd.models import UserToken

CASO_ULTIMA_MATRICULA_ID = 1
EJE_FORMATIVO_PRACTICAS = 9
EJE_FORMATIVO_VINCULACION = 11
EXCLUDE_EJE_FORMATIVO = [EJE_FORMATIVO_PRACTICAS, EJE_FORMATIVO_VINCULACION]

class MatriculaPosgradoAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_MATRICULA'

    @api_security
    def post(self, request):
        TIEMPO_ENCACHE = 60 * 15
        try:
            hoy = datetime.now().date()
            payload = request.auth.payload
            if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
                ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
            else:
                ePerfilUsuario = PerfilUsuario.objects.db_manager("sga_select").get(pk=encrypt(payload['perfilprincipal']['id']))
                cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario,TIEMPO_ENCACHE)
            valid, msg_error = validate_entry_to_student_api(ePerfilUsuario, 'posgrado')
            if not valid:
                raise NameError(msg_error)
            eInscripcion = ePerfilUsuario.inscripcion
            ePersona = eInscripcion.persona
            ePeriodo = None
            if 'id' in payload['periodo'] and payload['periodo']['id']:
                periodoEnCache = cache.get(f"periodo_id_{payload['periodo']['id']}")
                if periodoEnCache:
                    ePeriodo = periodoEnCache
                else:
                    if not ePeriodo and eInscripcion.inscripcioncohorte_set.values('id').filter(status=True).exists():
                        ePeriodo = eInscripcion.inscripcioncohorte_set.filter(status=True).last().cohortes.periodoacademico
                        if not ePeriodo:
                            raise NameError(u"Periodo no encontrado")
                        # ePeriodo = Periodo.objects.db_manager("sga_select").get(pk=encrypt(payload['periodo']['id']))
                        cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)

            if not ePeriodo and eInscripcion.inscripcioncohorte_set.values('id').filter(status=True).exists():
                ePeriodo = eInscripcion.inscripcioncohorte_set.filter(status=True).last().cohortes.periodoacademico
                if not ePeriodo:
                    raise NameError(u"Periodo no encontrado")

            ePeriodoMatricula = None
            eMatricula = None
            action = request.data.get('action')
            if not action:
                raise NameError(u'Acción no permitida')

            elif action == 'loadInitialData':
                try:
                    nivel_id = encrypt(request.data['nid']) if 'nid' in request.data and request.data['nid'] else None
                    eNivelEnCache = cache.get(f"nivel_id_{nivel_id}")
                    if eNivelEnCache:
                        eNivel = eNivelEnCache
                    else:
                        if not Nivel.objects.values('id').filter(pk=nivel_id).exists():
                            raise NameError(u"Nivel no existe")
                        eNivel = Nivel.objects.get(pk=nivel_id)
                        cache.set(f"nivel_id_{nivel_id}", eNivel, TIEMPO_ENCACHE)
                    ePeriodoMatricula = None
                    if eNivel.periodo.periodomatricula_set.values('id').filter(status=True).exists():
                        ePeriodoMatricula = eNivel.periodo.periodomatricula_set.filter()[0]
                    if not ePeriodoMatricula:
                        raise NameError(u"Periodo académico no existe")

                    # eMatricula = None
                    if 'id' in payload['matricula'] and payload['matricula']['id']:
                        matriculaEnCache = cache.get(f"matricula_id_{payload['matricula']['id']}")
                        if matriculaEnCache:
                            eMatricula = matriculaEnCache
                        else:
                            eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                            cache.set(f"matricula_id_{payload['matricula']['id']}", eMatricula, TIEMPO_ENCACHE)

                    bandera_pendiente_evaluaciondocente = 0
                    eMateriasMatriculado = []
                    if eMatricula:
                        eMateriasMatriculado = eMatricula.listado_materias()

                    eInscripcionMalla = eInscripcion.malla_inscripcion()
                    eInscripcionNivel = eInscripcion.mi_nivel()
                    inscohorte = eInscripcion.inscripcioncohorte_set.filter(status=True).last()
                    asignaturas_malla = None
                    if inscohorte.itinerario > 0:
                        listaitinerarios = ITINERARIO_ASIGNATURA_MALLA
                        nueva = []
                        for c in list(listaitinerarios):
                            if not c[0] in (inscohorte.itinerario,0) :
                                nueva.append(c[0])
                        asignaturas_malla = eInscripcionMalla.malla.asignaturamalla_set.select_related().all().exclude((Q(nivelmalla_id=NIVEL_MALLA_CERO) | Q(opcional=True) | Q(itinerario__in=nueva) | Q(ejeformativo_id__in=EXCLUDE_EJE_FORMATIVO))).order_by('nivelmalla', 'ejeformativo')
                    else:
                        asignaturas_malla = eInscripcionMalla.malla.asignaturamalla_set.select_related().all().exclude((Q(nivelmalla_id=NIVEL_MALLA_CERO) | Q(opcional=True) | Q(ejeformativo_id__in=EXCLUDE_EJE_FORMATIVO))).order_by('nivelmalla', 'ejeformativo')
                    va_ultima_matricula = eInscripcion.va_ultima_matricula(ePeriodoMatricula.num_matriculas)
                    num_va_ultima_matricula = eInscripcion.num_va_ultima_matricula(ePeriodoMatricula.num_matriculas)
                    aData = []

                    if len(eMateriasMatriculado) > 0:
                        for am in asignaturas_malla:
                            eMaterias = Materia.objects.values_list('id').filter(Q(asignatura=am.asignatura, nivel=eNivel), status=True).order_by('id')
                            if eMaterias:
                                for mm in eMateriasMatriculado:
                                    if mm in eMaterias:
                                        materia = Materia.objects.get(pk=mm[0])
                                        registros_encuesta = materia.respuestaevaluacionacreditacion_set.values('evaluador_id').filter(
                                            tipoinstrumento=1, evaluador_id=ePersona.id, status=True).distinct()
                                        if registros_encuesta:
                                            totaldocentes = materia.profesores_materia().count()
                                            if registros_encuesta.count() != totaldocentes:
                                                bandera_pendiente_evaluaciondocente += 1
                                        else:
                                            bandera_pendiente_evaluaciondocente += 1
                    tiene_bloqueo_matricula = get_bloqueo_matricula_posgrado(ePersona, inscohorte, ePeriodoMatricula)
                    TienePago = inscohorte.pago_rubro_matricula() if inscohorte else False
                    for am in asignaturas_malla:
                        puedetomar = eInscripcion.puede_tomar_materia(am.asignatura)
                        estado = eInscripcion.estado_asignatura(am.asignatura)
                        totalmatriculaasignatura = eInscripcion.total_record_asignaturatodo(am.asignatura)
                        if not estado in [1, 2]:
                            if eInscripcion.itinerario:
                                if am.itinerario:
                                    if eInscripcion.itinerario == am.itinerario:
                                        estado = 3
                                    else:
                                        estado = 0
                                else:
                                    estado = 3
                            else:
                                estado = 3

                        materias = []
                        aRequisitos = []
                        puede_ver_horario = 0
                        bandera_disponible_matricular = 0
                        matriculado_materia = False
                        """PERMITE QUE UNICAMENTE PUEDAN SELECCIONAR SOLO MATERIAS DE ULTIMA MATRICULA"""
                        if va_ultima_matricula and num_va_ultima_matricula >= ePeriodoMatricula.num_materias_maxima_ultima_matricula and puedetomar and estado in [2, 3] and totalmatriculaasignatura != (ePeriodoMatricula.num_matriculas - 1) and am.nivelmalla.orden > eInscripcionNivel.nivel.orden:
                            puedetomar = False
                        if puedetomar and estado in [2, 3] and totalmatriculaasignatura < ePeriodoMatricula.num_matriculas:
                            eMaterias = Materia.objects.values_list('id').filter(Q(asignatura=am.asignatura, nivel__periodo=eNivel.periodo), status=True).order_by('id')
                            eMateriasAbiertas = Materia.objects.filter(Q(asignatura=am.asignatura, inicio__gte=hoy, nivel__cerrado=False, nivel__periodo=eNivel.periodo), status=True).order_by('id')
                            if ePeriodoMatricula and ePeriodoMatricula.valida_materia_carrera:
                                eMateriasAbiertas = eMateriasAbiertas.filter(asignaturamalla__malla=eInscripcion.mi_malla()).distinct().order_by('id')
                            if ePeriodoMatricula and ePeriodoMatricula.valida_seccion and not va_ultima_matricula:
                                eMateriasAbiertas = eMateriasAbiertas.filter(nivel__sesion=eInscripcion.sesion).distinct().order_by('id')
                            if len(eMateriasAbiertas) > 0:
                                puede_ver_horario = 1
                                if am.validarequisitograduacion:
                                    eRequisitos = RequisitoIngresoUnidadIntegracionCurricular.objects.filter(status=True, asignaturamalla=am, activo=True, obligatorio=True)
                                    for eRequisito in eRequisitos:
                                        eRequisito_data = MatriRequisitoIngresoUnidadIntegracionCurricularSerializer(eRequisito).data
                                        if eRequisito.enlineamatriculacion:
                                            eRequisito_data.__setitem__('cumple', False)
                                        else:
                                            cumple = eRequisito.run(eInscripcion.pk)
                                            eRequisito_data.__setitem__('cumple', cumple)
                                        aRequisitos.append(eRequisito_data)
                            if eMaterias:
                                for mm in eMateriasMatriculado:
                                    if mm in eMaterias:
                                        matriculado_materia = True
                            for m in eMateriasAbiertas:
                                puede_agregar = False
                                coordinacion = m.coordinacion()
                                horarios_verbose = []
                                horarios = []
                                horarios_verbose_aux = []
                                _horarios = get_horarios_clases_data(m)
                                if ePeriodoMatricula.ver_horario_materia:
                                    horarios_verbose = get_horarios_clases_informacion(m)
                                    horarios_verbose_aux = _horarios
                                if ePeriodoMatricula.valida_conflicto_horario:
                                    horarios = _horarios
                                mispracticas = get_practicas_data(m)
                                if m.fechainiciomatriculacionposgrado and m.fechafinmatriculacionposgrado and m.fechainiciomatriculacionposgrado <= hoy <= m.fechafinmatriculacionposgrado:
                                    disponible_fechas_matricular = True
                                    bandera_disponible_matricular = 1
                                else:
                                    disponible_fechas_matricular = False
                                if m.nivel.puede_agregar_materia_matricula() and disponible_fechas_matricular and bandera_pendiente_evaluaciondocente == 0:
                                    puede_agregar = True
                                materias.append({"id": m.id,
                                                 "asignatura": m.asignatura.nombre,
                                                 "nivelmalla": to_unicode(m.asignaturamalla.nivelmalla.nombre) if m.asignaturamalla.nivelmalla else "",
                                                 "nivelmalla_id": m.asignaturamalla.nivelmalla.id if m.asignaturamalla.nivelmalla else 0,
                                                 'sede': to_unicode(m.nivel.sede.nombre) if m.nivel.sede else "",
                                                 "carrera": to_unicode(m.asignaturamalla.malla.carrera.nombre_completo()) if m.asignaturamalla.malla.carrera else "",
                                                 "coordinacion": coordinacion.nombre if coordinacion else None,
                                                 "coordinacion_alias": coordinacion.alias if coordinacion else None,
                                                 "paralelo": m.paralelomateria.nombre,
                                                 "paralelo_id": m.paralelomateria.id,
                                                 "profesor": (m.profesor_principal().persona.nombre_completo()) if m.profesor_principal() else 'SIN DEFINIR',
                                                 "genero_profesor": 'Profesora' if m.profesor_principal() and m.profesor_principal().persona.es_mujer() else 'Profesor',
                                                 'inicio': m.inicio.strftime("%d-%m-%Y"),
                                                 'fin': m.fin.strftime("%d-%m-%Y"),
                                                 'iniciomatriculacion': m.fechainiciomatriculacionposgrado.strftime("%d-%m-%Y") if m.fechainiciomatriculacionposgrado else '',
                                                 'finmatriculacion': m.fechafinmatriculacionposgrado.strftime("%d-%m-%Y") if m.fechafinmatriculacionposgrado else '',
                                                 'session': to_unicode(m.nivel.sesion.nombre),
                                                 'identificacion': m.identificacion,
                                                 "tipomateria": m.tipomateria,
                                                 "tipomateria_display": m.get_tipomateria_display(),
                                                 "teoriapractica": 1 if m.asignaturamalla.practicas else 0,
                                                 "cupos": m.cupo if ePeriodoMatricula and ePeriodoMatricula.valida_cupo_materia else 0,
                                                 "disponibles": m.capacidad_disponible() if ePeriodoMatricula and ePeriodoMatricula.valida_cupo_materia else 0,
                                                 "horarios_verbose": horarios_verbose,
                                                 "horarios_verbose_aux": horarios_verbose_aux,
                                                 "horarios": horarios,
                                                 "mispracticas": mispracticas,
                                                 "puede_agregar": puede_agregar,
                                                 })
                        if am.itinerario > 0:
                            itinerario_verbose = f"ITINERARIO {am.itinerario}"
                        else:
                            itinerario_verbose = ''
                        predecesoras = [p.predecesora.asignatura.nombre for p in am.lista_predecesoras()]
                        aData.append({"id": am.id,
                                      "asignatura": am.asignatura.nombre,
                                      "asignatura_id": am.asignatura.id,
                                      "tipomateria_id": am.tipomateria.id if am.tipomateria else None,
                                      "tipomateria_nombre": am.tipomateria.nombre if am.tipomateria else None,
                                      "nivelmalla_id": am.nivelmalla.id,
                                      "nivelmalla": am.nivelmalla.nombre,
                                      "ejeformativo": am.ejeformativo.nombre,
                                      "estado": estado,
                                      "creditos": am.creditos,
                                      "itinerario": am.itinerario,
                                      "itinerario_verbose": itinerario_verbose,
                                      "horas": am.horas,
                                      "horas_semanal": am.horastotal(),
                                      "horas_contacto_docente": am.horasacdsemanal,
                                      "cantidad_predecesoras": am.cantidad_predecesoras(),
                                      "totalrecordasignatura": totalmatriculaasignatura,
                                      "va_num_matricula": totalmatriculaasignatura + 1,
                                      "predecesoras": predecesoras,
                                      "materias": materias,
                                      "puede_ver_horario": puede_ver_horario,
                                      "validarequisitograduacion": am.validarequisitograduacion,
                                      "requisitos": aRequisitos,
                                      "matricula_bloqueda": True if tiene_bloqueo_matricula or not TienePago else False,
                                      "disponible_fechas_matricular": True if bandera_disponible_matricular == 1 else False,
                                      "pendiente_evaluaciondocente": True if bandera_pendiente_evaluaciondocente > 0 else False,
                                      "matriculado_materia": matriculado_materia,
                                      })
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadCupoMateria':
                try:
                    if not 'asignatura' in request.data:
                        raise NameError(u"Parametro no valido")
                    asignatura = json.loads(request.data['asignatura'])
                    if not asignatura:
                        raise NameError(u"Parametro no valido")
                    materias = []
                    for m in asignatura['materias']:
                        disponibles = 0
                        for key, value in m.items():
                            if 'id' == key:
                                materia = Materia.objects.get(pk=int(m['id']))
                                disponibles = materia.capacidad_disponible()
                        m['disponibles'] = disponibles
                        materias.append(m)
                    asignatura['materias'] = materias
                    return Helper_Response(isSuccess=True, data=asignatura, status=status.HTTP_200_OK)
                except Exception as ex:
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
                        if materia['practica'] and len(materia['practica']['horarios']) > 0:
                            mis_clases.append(materia['practica']['horarios'])
                        if materia['horarios'] and len(materia['horarios']) > 0:
                            mis_clases.append(materia['horarios'])
                    if mi_materia['practica'] and len(mi_materia['practica']) > 0:
                        mi_clase.append(mi_materia['practica']['horarios'])
                    if mi_materia['horarios'] and len(mi_materia['horarios']) > 0:
                        mi_clase.append(mi_materia['horarios'])
                    tiene_conflicto, mensaje = valida_conflicto_materias_estudiante(mis_clases, mi_clase)
                    return Helper_Response(isSuccess=True, data={"conflicto": tiene_conflicto, "mensaje": mensaje}, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadCupoPractica':
                try:
                    if not 'materia' in request.data:
                        raise NameError(u"Parametro no valido")
                    materia = json.loads(request.data['materia'])
                    if not materia:
                        raise NameError(u"Parametro no valido")
                    practicas = []
                    for p in materia['mispracticas']:
                        disponibles = 0
                        for key, value in p.items():
                            if 'id' == key:
                                grupo = GruposProfesorMateria.objects.get(pk=int(p['id']))
                                disponibles = grupo.cuposdisponiblesgrupoprofesor()
                        p['disponibles'] = disponibles
                        practicas.append(p)
                    materia['mispracticas'] = practicas
                    return Helper_Response(isSuccess=True, data={'materia': materia}, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'locateEnrollmentLevel':
                try:
                    # raise NameError("ERROR CAIDO")
                    mismaterias = json.loads(request.data['mismaterias'])
                    res = ubicar_nivel_matricula(mismaterias)
                    aData = {}
                    if res:
                        if NivelMalla.objects.values('id').filter(pk=res).exists():
                            nivelmalla = NivelMalla.objects.get(pk=res)
                        else:
                            nivelmalla = NivelMalla.objects.get(pk=NIVEL_MALLA_UNO)
                        aData['id'] = nivelmalla.id
                        aData['nombre'] = nivelmalla.nombre
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'enroll':
                with transaction.atomic():
                    try:
                        nivel_id = encrypt(request.data['nivel_id']) if 'nivel_id' in request.data and request.data['nivel_id'] else None
                        if not Nivel.objects.values('id').filter(pk=nivel_id).exists():
                            raise NameError(u"Nivel no existe")
                        eNivel = Nivel.objects.get(pk=nivel_id)
                        ePeriodoMatricula = None
                        if eNivel.periodo.periodomatricula_set.values('id').filter(status=True).exists():
                            ePeriodoMatricula = eNivel.periodo.periodomatricula_set.filter()[0]
                        if not ePeriodoMatricula:
                            raise NameError(u"Periodo académico no existe")
                        eInscripcion = Inscripcion.objects.get(pk=eInscripcion.id)
                        va_ultima_matricula = eInscripcion.va_ultima_matricula(ePeriodoMatricula.num_matriculas)
                        if ePeriodoMatricula.valida_terminos:
                            if not 'acept_t' in request.data or int(request.data['acept_t']) != 1:
                                raise NameError(u"Para continuar, favor acepte los terminos y condiciones")
                        if not 'materias' in request.data:
                            raise NameError(u"Parametro de materias seleccionadas no valido")
                        mis_clases = json.loads(request.data['materias'])
                        if not 'cobro' in request.data:
                            raise NameError(u"Parametro de cobro no valido")
                        cobro = int(request.data['cobro'])
                        eCasoUltimaMatricula = None
                        if ePeriodoMatricula.valida_configuracion_ultima_matricula and va_ultima_matricula:
                            if not 'caso' in request.data or request.data['caso'] == 0:
                                raise NameError(u"Para continuar, favor seleccione un caso")
                            caso = encrypt(request.data['caso'])
                            if not CasoUltimaMatricula.objects.values("id").filter(pk=caso).exists():
                                raise NameError(u"Caso de matrícula no identificado")
                            eCasoUltimaMatricula = CasoUltimaMatricula.objects.get(pk=caso)
                        valid, msg, aData = action_enroll_posgrado(request, eInscripcion, ePeriodoMatricula, eNivel, mis_clases, cobro, eCasoUltimaMatricula)
                        if not valid:
                            raise NameError(msg)
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error en la matriculación: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'pay_pending_values':
                try:
                    hoy = datetime.now()
                    payload = request.auth.payload
                    ePerfilUsuario = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                    if not ePerfilUsuario.es_estudiante():
                        raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                    if not 'id' in payload['matricula']:
                        raise NameError(u'No se encuentra matriculado.')
                    eMatricula = None
                    ePeriodoMatricula = None
                    eInscripcion = ePerfilUsuario.inscripcion
                    ePersona = eInscripcion.persona
                    if 'id' in payload['matricula'] and payload['matricula']['id']:
                        eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                        ePeriodo = eMatricula.nivel.periodo
                    else:
                        if 'id' in request.data.get() and request.data.get('id'):
                            ePersona = Persona.objects.get(pk=int(encrypt(request.data.get('id'))))

                    fecha = datetime.now().date()
                    hora = datetime.now().time()
                    fecha_hora = fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__()
                    token_ = md5(str(encrypt(ePersona.usuario.id) + fecha_hora).encode("utf-8")).hexdigest()
                    lifetime = SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
                    perfil_ = UserToken.objects.create(user=request.user, token=token_, action_type=5, app=5, isActive=True, date_expires=datetime.now() + lifetime)
                    return Helper_Response(isSuccess=True, redirect=f'http://epunemi.gob.ec/oauth2/?tknbtn={token_}&tkn={encrypt(ePersona.id)}', module_access=False, token=True, status=status.HTTP_200_OK)

                except Exception as ex:
                    transaction.set_rollback(True)
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acción no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
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
            valid, msg_error = validate_entry_to_student_api(ePerfilUsuario, 'posgrado')
            if not valid:
                raise NameError(msg_error)
            eInscripcion = ePerfilUsuario.inscripcion
            ePersona = eInscripcion.persona
            ePeriodoMatricula = None
            eMatricula = None
            ePeriodo = None
            #informacionmatriz
            datospersonales, datosdomicilio, datosetnia, datostitulo, campos, datosactualizados = eInscripcion.tiene_informacion_matriz_completa()
            if datospersonales or datosdomicilio or datosetnia or datostitulo or datosactualizados:
                return Helper_Response(isSuccess=False, data={'url_matricula':True}, redirect="alu_actualizadatos", module_access=False, token=True, status=status.HTTP_200_OK)
            if 'id' in payload['periodo'] and payload['periodo']['id']:
                periodoEnCache = cache.get(f"periodo_id_{payload['periodo']['id']}")
                if periodoEnCache:
                    ePeriodo = periodoEnCache
                else:
                    if payload['periodo']['id'] is None:
                        if not PeriodoMatricula.objects.values("id").filter(tipo=3, periodo=ePeriodo, activo=True).exists():
                            raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el periodo de matriculación se encuentra inactivo")
                        ePeriodoMatricula = PeriodoMatricula.objects.filter(status=True, tipo=3, periodo=ePeriodo, activo=True).order_by('-pk')[0]
                        ePeriodo = ePeriodoMatricula.periodo
                    else:
                        if not ePeriodo and eInscripcion.inscripcioncohorte_set.values('id').filter(status=True).exists():
                            ePeriodo = eInscripcion.inscripcioncohorte_set.filter(status=True).last().cohortes.periodoacademico
                            if not ePeriodo:
                                raise NameError(u"Periodo no encontrado")
                            # ePeriodo = Periodo.objects.db_manager("sga_select").get(pk=encrypt(payload['periodo']['id']))
                            cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)
                    # cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)

            if not ePeriodo and eInscripcion.inscripcioncohorte_set.values('id').filter(status=True).exists():
                ePeriodo = eInscripcion.inscripcioncohorte_set.filter(status=True).last().cohortes.periodoacademico
                if not ePeriodo:
                    raise NameError(u"Periodo no encontrado")

            if not PeriodoMatricula.objects.values('id').filter(status=True, activo=True, periodo=ePeriodo, tipo=3).exists():
                raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el periodo de matriculación se encuentra inactivo")
            ePeriodoMatricula = PeriodoMatricula.objects.filter(status=True, periodo=ePeriodo, activo=True, tipo=3)
            if len(ePeriodoMatricula) > 1:
                raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, proceso de matriculación no se encuentra activo")
            ePeriodoMatricula = ePeriodoMatricula[0]
            if not ePeriodoMatricula.esta_periodoactivomatricula():
                raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el periodo de matriculación se encuentra inactivo")
            # if eInscripcion.tiene_perdida_carrera(ePeriodoMatricula.num_matriculas):
            #     raise NameError(u"ATENCIÓN: Su limite de matricula por perdida de una o mas asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria para mas informacion.")

            if ePeriodoMatricula.valida_coordinacion:
                if not eInscripcion.coordinacion in ePeriodoMatricula.coordinaciones():
                    raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, en su facultad no esta permitida para la matriculación")
            eNivel = None
            eNivel_id = get_nivel_matriculacion(eInscripcion, ePeriodoMatricula.periodo)
            if eNivel_id < 0:
                if eNivel_id == -1:
                    log(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el periodo de matriculación no se encuentra activo.... %s" % (eInscripcion.info()), request, "add")
                    raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el periodo de matriculación no se encuentra activo")
                if eNivel_id == -2:
                    raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, no existen niveles con cupo para matricularse")
                if eNivel_id == -3:
                    raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, no existen paralelos disponibles")
                if eNivel_id == -4:
                    raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, no existen paralelos para su nivel")
            eNivel = Nivel.objects.get(pk=eNivel_id)

            if not eNivel.fechainicioagregacion or not eNivel.fechatopematricula or not eNivel.fechatopematriculaex or not eNivel.fechatopematriculaes:
                raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el proceso de matrícula se encuentra inactivo...")

            if hoy < eNivel.fechainicioagregacion:
                raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el proceso de matrícula empieza el %s" % eNivel.fechainicioagregacion.__str__())
            # if hoy <= eNivel.fechatopematriculaes:
            #     if hoy > eNivel.fechatopematriculaex:
            #         if ePeriodoMatricula.valida_proceos_matricula_especial:
            #             raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el proceso de matrícula especial termina el {eNivel.fechatopematriculaes.__str__()}. <br>Verificar en el módulo <a href='/alu_solicitudmatricula' class='bloqueo_pantalla'>Solicitud de Matrícula</a>")
            #         else:
            #             raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el proceso de matrícula especial termina el {eNivel.fechatopematriculaes.__str__()}.")
            # else:
            #     if hoy > eNivel.fechatopematriculaes:
            #         raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el proceso de matrícula especial terminó el %s" % eNivel.fechatopematriculaes.__str__())

            # if ePeriodoMatricula.valida_cronograma:
            #     if not puede_matricularse_seguncronograma_coordinacion(eInscripcion, eNivel.periodo):
            #         raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, aún no está habilitado el cronograma de matriculación de su carrera.")
            # else:
            #     if ePeriodoMatricula.tiene_cronograma_carreras():
            #         a = puede_matricularse_seguncronograma_carrera(eInscripcion, eNivel.periodo)
            #         if a[0] == 2:
            #             raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, aún no está habilitado el cronograma de matriculación de su carrera.")
            #         if a[0] == 3:
            #             raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, usted no realizó su Pre-Matrícula (matricularse después de dos días de haber iniciado matrícula ordinaria).")
            #         if a[0] == 4:
            #             log(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el periodo de matriculación no se encuentra activo.... %s" % (eInscripcion.info()), request, "add")
            #             raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el periodo de matriculación no se encuentra activo")
            eMalla = None
            eInscripcionMalla = eInscripcion.malla_inscripcion()
            if not eInscripcion.tiene_malla():
                raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, debe tener malla asociada para poder matricularse.")
            eMalla = eInscripcionMalla.malla
            # if eInscripcion.tiene_perdida_carrera(ePeriodoMatricula.num_matriculas):
            #     raise NameError(f"Atencion: Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, su limite de matricula por perdida de una o mas asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria de la facultad para mas informacion.")

            # if variable_valor('VALIDAR_QUE_SEA_PRIMERA_MATRICULA'):
            #     if eInscripcion.matricula_set.values('id').filter(status=True).exists():
            #         raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, no puede matricularse; solo apto para primer nivel (nuevos).")

            ePreMatricula = None
            tienePreMatricula = False

            inscohorte = eInscripcion.inscripcioncohorte_set.filter(status=True)
            ePersona_serializer = MatriPersonaSerializer(eInscripcion.persona)
            eInscripcion_serializer = MatriInscripcionSerializer(eInscripcion)
            eCarrera_serializer = MatriCarreraSerializer(eInscripcion.carrera)
            eNivelMalla_serializer = MatriNivelMallaSerializer(eInscripcion.mi_nivel().nivel)
            eNivelesMalla_serializer = MatriNivelMallaSerializer(eInscripcionMalla.malla.niveles_malla(), many=True)
            eInscripcionMalla_serializer = MatriInscripcionMallaSerializer(eInscripcion.malla_inscripcion())
            ePeriodoMatricula_serializer = MatriPeriodoMatriculaSerializer(ePeriodoMatricula)
            eNivel_serializer = MatriNivelSerializer(eNivel)
            eMalla_serializer = MatriMallaSerializer(eMalla)
            ePreMatricula_serializer = MatriPreMatriculaSerializer(ePreMatricula)
            aData['ePersona'] = ePersona_serializer.data if ePersona_serializer else None
            aData['eInscripcion'] = eInscripcion_serializer.data if eInscripcion_serializer else None
            aData['itinerario'] = inscohorte.last().itinerario if inscohorte and inscohorte.last().itinerario > 0 else eInscripcion.itinerario
            aData['eCarrera'] = eCarrera_serializer.data if eCarrera_serializer else None
            aData['eNivelMalla'] = eNivelMalla_serializer.data if eNivelMalla_serializer else None
            aData['eNivelesMalla'] = eNivelesMalla_serializer.data if eNivelesMalla_serializer else []
            aData['isItinerarios'] = eInscripcionMalla.malla.tiene_itinerarios()
            aData['listItinerarios'] = inscohorte.values_list('itinerario', flat=True) if inscohorte and inscohorte.last().itinerario > 0 else eInscripcionMalla.malla.lista_itinerarios()
            aData['eInscripcionMalla'] = eInscripcionMalla_serializer.data if eInscripcionMalla_serializer else None
            aData['ePeriodoMatricula'] = ePeriodoMatricula_serializer.data if ePeriodoMatricula_serializer else None
            aData['ePreMatricula'] = ePreMatricula_serializer.data if tienePreMatricula else None
            aData['tienePreMatricula'] = tienePreMatricula
            aData['NoTienePago'] = inscohorte.last().pago_rubro_matricula() if inscohorte else False
            aData['matriculacionLibre'] = MATRICULACION_LIBRE
            aData['eNivel'] = eNivel_serializer.data if eNivel_serializer else None
            aData['eMalla'] = eMalla_serializer.data if eMalla_serializer else None
            aData['vaUltimaMatricula'] = vaUltimaMatricula = eInscripcion.va_ultima_matricula(ePeriodoMatricula.num_matriculas)
            aData['numVaUltimaMatricula'] = eInscripcion.num_va_ultima_matricula(ePeriodoMatricula.num_matriculas)
            aData['totalMateriasNivel'] = eInscripcion.total_materias_nivel()
            aData['totalMateriasPendientesMalla'] = eInscripcion.total_materias_pendientes_malla()

            aData['FichaSocioEconomicaINEC'] = ePersona.fichasocioeconomicainec()
            aData['Title'] = "Matriculación Online"

            tiene_valores_pendientes, msg_valores_pendientes = get_deuda_persona_posgrado(ePersona, ePeriodoMatricula)
            aData['tiene_valores_pendientes'] = tiene_valores_pendientes
            aData['msg_valores_pendientes'] = msg_valores_pendientes
            eCasoUltimaMatricula_serializer = None
            if ePeriodoMatricula.valida_configuracion_ultima_matricula and vaUltimaMatricula:
                if CasoUltimaMatricula.objects.values("id").filter(pk=CASO_ULTIMA_MATRICULA_ID).exists() and CASO_ULTIMA_MATRICULA_ID in ePeriodoMatricula.configuracion_ultima_matricula.casos().values_list("id", flat=True) and eInscripcion.promedio > 75:
                    eCasoUltimaMatricula = CasoUltimaMatricula.objects.get(pk=CASO_ULTIMA_MATRICULA_ID)
                    eCasoUltimaMatricula_serializer = MatriCasoUltimaMatriculaSerializer(eCasoUltimaMatricula)
            aData['eCasoUltimaMatricula'] = eCasoUltimaMatricula_serializer.data if eCasoUltimaMatricula_serializer else None
            return Helper_Response(isSuccess=True, data={"tipo": "matricula", "aData": aData}, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)
