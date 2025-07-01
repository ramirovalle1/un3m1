# coding=utf-8
import json
import os
import sys
from datetime import datetime, timedelta, date
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django.db import connection, transaction, connections, connection
from django.template.defaultfilters import floatformat
from django.db.models import Q, Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status

from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.views.alumno.matricula.functions import validate_entry_to_student_api, action_enroll_pregrado
from api.serializers.alumno.matriculacion import MatriInscripcionSerializer, MatriPeriodoMatriculaSerializer, \
    MatriInscripcionMallaSerializer, MatriNivelMallaSerializer, MatriMateriaAsignadaSerializer, MatriNivelSerializer, \
    MatriMallaSerializer, MatriCarreraSerializer, MatriPersonaSerializer, MatriPreMatriculaSerializer, \
    MatriculaSerializer, MatriCasoUltimaMatriculaSerializer, MatriRequisitoIngresoUnidadIntegracionCurricularSerializer, \
    MatriRubro, MatriSesionSerializer
from matricula.models import PeriodoMatricula, CasoUltimaMatricula, DetalleRubroMatricula, CostoOptimoMalla,SolicitudReservaCupoMateria, DetalleSolicitudReservaCupoMateria
from sagest.models import TipoOtroRubro, Rubro, Pago
from settings import MATRICULACION_LIBRE, NIVEL_MALLA_CERO, NIVEL_MALLA_UNO, RUBRO_ARANCEL, RUBRO_MATRICULA, PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD
from sga.commonviews import ficha_socioeconomica
from sga.funciones import log, variable_valor, null_to_numeric, null_to_decimal
from sga.models import Noticia, Inscripcion, PerfilUsuario, Periodo, ConfirmarMatricula, Nivel, AsignaturaMalla, \
    RecordAcademico, Materia, GruposProfesorMateria, NivelMalla, Matricula, Persona, HistoricoRecordAcademico, \
    PreMatricula, AuditoriaMatricula, Graduado, Egresado, Paralelo, Sesion, MateriaAsignada, PeriodoGrupoSocioEconomico, ModuloMalla
from inno.models import RequisitoIngresoUnidadIntegracionCurricular, RequisitoMateriaUnidadIntegracionCurricular, \
    PeriodoMalla, DetallePeriodoMalla, MallaHorasSemanalesComponentes
from sga.templatetags.sga_extras import encrypt
from matricula.funciones import get_nivel_matriculacion, puede_matricularse_seguncronograma_carrera, \
    puede_matricularse_seguncronograma_coordinacion, ubicar_nivel_matricula, get_practicas_data, \
    get_horarios_clases_informacion, get_deuda_persona, get_horarios_clases_data, valida_conflicto_materias_estudiante, \
    valid_intro_module_estudiante, to_unicode, get_materias_x_inscripcion_x_asignatura, tiene_deudas_vencidas_persona, contar_nivel_matricula
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.cache import cache


CASO_ULTIMA_MATRICULA_ID = 1
EJE_FORMATIVO_PRACTICAS = 9
EJE_FORMATIVO_VINCULACION = 11
EXCLUDE_EJE_FORMATIVO = [EJE_FORMATIVO_PRACTICAS, EJE_FORMATIVO_VINCULACION]


class MatriculaPregradoAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_MATRICULA'

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
                cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario,TIEMPO_ENCACHE)
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
            action = request.data.get('action')
            if not action:
                raise NameError(u'Acción no permitida')

            elif action == 'loadInitialData':
                try:
                    matricula_tardia = variable_valor('MATRICULA_TARDIA')
                    if matricula_tardia:
                        matricula_tardia_fecha = variable_valor('MATRICULA_TARDIA_FECHA')
                        hoy = matricula_tardia_fecha
                    nivel_id = encrypt(request.data['nid']) if 'nid' in request.data and request.data['nid'] else None
                    eNivelEnCache = cache.get(f"nivel_id_{nivel_id}")
                    if eNivelEnCache:
                        eNivel = eNivelEnCache
                    else:
                        if not Nivel.objects.values('id').filter(pk=nivel_id).exists():
                            raise NameError(u"Nivel no existe")
                        eNivel = Nivel.objects.get(pk=nivel_id)
                        cache.set(f"nivel_id_{nivel_id}", eNivel, TIEMPO_ENCACHE)
                    ePeriodoMatricula = eNivel.periodo.periodomatricula_set.filter(status=True).first()
                    if not ePeriodoMatricula:
                        raise NameError(u"Periodo académico no existe")
                    eInscripcionMalla = eInscripcion.malla_inscripcion()
                    eInscripcionNivel = eInscripcion.mi_nivel()
                    if eInscripcionMalla.malla.modalidad.id == 3:
                        asignaturas_malla = eInscripcionMalla.malla.asignaturamalla_set.select_related().filter(status=True).exclude((Q(nivelmalla_id=NIVEL_MALLA_CERO) | Q(opcional=True))).order_by('nivelmalla', 'ejeformativo')
                    else:
                        asignaturas_malla = eInscripcionMalla.malla.asignaturamalla_set.select_related().filter(status=True).exclude((Q(nivelmalla_id=NIVEL_MALLA_CERO) | Q(opcional=True) | Q(ejeformativo_id__in=EXCLUDE_EJE_FORMATIVO))).order_by('nivelmalla', 'ejeformativo')
                    va_ultima_matricula = eInscripcion.va_ultima_matricula(ePeriodoMatricula.num_matriculas)
                    num_va_ultima_matricula = eInscripcion.num_va_ultima_matricula(ePeriodoMatricula.num_matriculas)
                    aData = []
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
                        """PERMITE QUE UNICAMENTE PUEDAN SELECCIONAR SOLO MATERIAS DE ULTIMA MATRICULA"""
                        if va_ultima_matricula and num_va_ultima_matricula >= ePeriodoMatricula.num_materias_maxima_ultima_matricula and puedetomar and estado in [2, 3] and totalmatriculaasignatura != (ePeriodoMatricula.num_matriculas - 1) and am.nivelmalla.orden > eInscripcionNivel.nivel.orden:
                            puedetomar = False
                        if puedetomar and estado in [2, 3] and totalmatriculaasignatura < ePeriodoMatricula.num_matriculas:
                            eMateriasAbiertas = Materia.objects.filter(Q(asignatura=am.asignatura, inicio__gte=hoy, nivel__cerrado=False, nivel__periodo=eNivel.periodo), status=True).order_by('id')
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
                            if len(eMateriasAbiertas) > 0:
                                puede_ver_horario = 1
                                if am.validarequisitograduacion:
                                    eRequisitos_aux = RequisitoMateriaUnidadIntegracionCurricular.objects.filter(materia__in=eMateriasAbiertas, status=True, activo=True, obligatorio=True, inscripcion=True)
                                    eRequisitos = RequisitoIngresoUnidadIntegracionCurricular.objects.filter(asignaturamalla=am, requisito__id__in=eRequisitos_aux.values_list("requisito__id", flat=True)).distinct()
                                    # eRequisitos = RequisitoIngresoUnidadIntegracionCurricular.objects.filter(status=True, asignaturamalla=am, activo=True, obligatorio=True)
                                    for eRequisito in eRequisitos:
                                        eRequisito_data = MatriRequisitoIngresoUnidadIntegracionCurricularSerializer(eRequisito).data
                                        if eRequisito.enlineamatriculacion:
                                            eRequisito_data.__setitem__('cumple', False)
                                        else:
                                            cumple = eRequisito.run(eInscripcion.pk)
                                            eRequisito_data.__setitem__('cumple', cumple)
                                        aRequisitos.append(eRequisito_data)
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
                                if m.nivel.puede_agregar_materia_matricula():
                                    puede_agregar = True
                                eProfesor = '-- SIN DEFINIR --'
                                if ePeriodoMatricula.ver_profesor_materia:
                                    if m.asignaturamalla.malla.modalidad.es_enlinea():
                                        profesor_principal = m.profesor_principal_virtual()
                                    else:
                                        profesor_principal = m.profesor_principal()
                                    if profesor_principal:
                                        eProfesor = profesor_principal.persona.nombre_completo()
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
                                                 "profesor": eProfesor,
                                                 'inicio': m.inicio.strftime("%d-%m-%Y"),
                                                 'fin': m.fin.strftime("%d-%m-%Y"),
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
                                                 "validaconflictohorarioalu": m.validaconflictohorarioalu
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
                                      "orden": am.nivelmalla.orden,
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
                                      "existe_disponibiliad_cupo_en_materias": any(materia["disponibles"] != 0 for materia in materias) if materias else False,
                                      "puede_ver_horario": puede_ver_horario,
                                      "validarequisitograduacion": am.validarequisitograduacion,
                                      "requisitos": aRequisitos,
                                      "asignaturapracticas": am.asignaturapracticas,
                                      "asignaturavinculacion": am.asignaturavinculacion,
                                      "existe_oferta": Materia.objects.filter(status=True,nivel__periodo=Periodo.objects.get(pk=variable_valor('PERIOD_MATRICULA_PREGRADO_ACTUAL')),asignaturamalla=am).exists()
                                      })
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadCupoMateria':
                try:
                    if not 'asignatura' in request.data:
                        raise NameError(u"Parametro de asignatura no valido")
                    if not 'idn' in request.data:
                        raise NameError(u"Parametro de nivel no valido")
                    if not 'idp' in request.data:
                        raise NameError(u"Parametro de paralelo no valido")
                    eNivel = Nivel.objects.get(pk=encrypt(request.data['idn']))
                    eParalelo = None
                    if int(request.data['idp']) > 0:
                        eParalelo = Paralelo.objects.get(pk=request.data['idp'])
                    asignatura = json.loads(request.data['asignatura'])
                    if not asignatura:
                        raise NameError(u"Parametro no valido")
                    try:
                        eAsignaturaMalla = AsignaturaMalla.objects.get(pk=asignatura['id'])
                    except ObjectDoesNotExist:
                        raise NameError(u"No se encontro la asignatura en malla")

                    asignatura['materias'] = get_materias_x_inscripcion_x_asignatura(eNivel, eInscripcion, eAsignaturaMalla, eParalelo)
                    # materias = []
                    # for m in asignatura['materias']:
                    #     disponibles = 0
                    #     for key, value in m.items():
                    #         if 'id' == key:
                    #             materia = Materia.objects.get(pk=int(m['id']))
                    #             disponibles = materia.capacidad_disponible()
                    #     m['disponibles'] = disponibles
                    #     materias.append(m)
                    # asignatura['materias'] = materias
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
                        if materia['practica'] and len(materia['practica']['horarios']) > 0 and materia['validaconflictohorarioalu']:
                            mis_clases.append(materia['practica']['horarios'])
                        if materia['horarios'] and len(materia['horarios']) > 0 and materia['validaconflictohorarioalu']:
                            mis_clases.append(materia['horarios'])
                    if mi_materia['practica'] and len(mi_materia['practica']) > 0 and mi_materia['validaconflictohorarioalu']:
                        mi_clase.append(mi_materia['practica']['horarios'])
                    if mi_materia['horarios'] and len(mi_materia['horarios']) > 0 and mi_materia['validaconflictohorarioalu']:
                        mi_clase.append(mi_materia['horarios'])
                    tiene_conflicto, mensaje = False, 'No se registra conflicto de horario'
                    if len(mi_clase) > 0:
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
                    validacion_matricula = variable_valor('VALIDACION_MATRICULA')
                    if validacion_matricula == True:
                        aData = {}
                        nivelmalla = None
                        mismaterias = json.loads(request.data['mismaterias'])
                        res = ubicar_nivel_matricula(mismaterias)
                        res2 = contar_nivel_matricula(mismaterias)
                        malla_id = json.loads(request.data['malla_id'])
                        if res:
                            if NivelMalla.objects.values('id').filter(pk=res).exists():
                                nivelmalla = NivelMalla.objects.get(pk=res)
                            else:
                                nivelmalla = NivelMalla.objects.get(pk=NIVEL_MALLA_UNO)
                            aData['id'] = nivelmalla.id
                            aData['nombre'] = nivelmalla.nombre
                        if res2:
                            aData['nivelesdiferentes'] = res2
                        if nivelmalla:
                            if horassemanalesnivel := MallaHorasSemanalesComponentes.objects.filter(status=True,malla_id=encrypt(malla_id),nivelmalla_id=nivelmalla.id):
                                horassemanalesACD = horassemanalesnivel.values_list('acd_horassemanales', flat=True)
                                aData['horassemanales'] = horassemanalesACD.first()
                    else:
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
                        ePeriodoMatricula = eNivel.periodo.periodomatricula_set.filter(status=True).first()
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
                        valid, msg, aData = action_enroll_pregrado(request, eInscripcion, ePeriodoMatricula, eNivel, mis_clases, cobro, eCasoUltimaMatricula)
                        if not valid:
                            raise NameError(msg)
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error en la matriculación: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'to_differ':
                with transaction.atomic():
                    try:
                        idm = int(request.data['idm'])
                        eMatricula = Matricula.objects.get(pk=idm)
                        ePeriodoMatricula = None
                        if PeriodoMatricula.objects.values('id').filter(status=True, activo=True, periodo=eMatricula.nivel.periodo).exists():
                            ePeriodoMatricula = PeriodoMatricula.objects.get(status=True, activo=True, periodo=eMatricula.nivel.periodo)
                        if not ePeriodoMatricula:
                            raise NameError(u"No se permite diferir arancel")
                        if ePeriodoMatricula.valida_cuotas_rubro and ePeriodoMatricula.num_cuotas_rubro <= 0:
                            raise NameError(u"Periodo acádemico no permite diferir arancel")
                        if not ePeriodoMatricula.tiene_fecha_cuotas_rubro():
                            raise NameError(u"Periodo acádemico no permite diferir arancel")
                        if ePeriodoMatricula.monto_rubro_cuotas == 0:
                            raise NameError(u"Periodo acádemico no permite diferir arancel")
                        if eMatricula.aranceldiferido == 1:
                            raise NameError(u"El rubro arancel ya ha sido diferido. Verifique módulo Mis Finanzas")
                        if not Rubro.objects.values('id').filter(matricula=eMatricula, tipo_id=RUBRO_ARANCEL, status=True).exists():
                            raise NameError(u"No se puede procesar el registro.")
                        arancel = Rubro.objects.filter(matricula=eMatricula, tipo_id=RUBRO_ARANCEL, status=True).first()
                        nombrearancel = arancel.nombre
                        valorarancel = Decimal(arancel.valortotal).quantize(Decimal('.01'))
                        if valorarancel < ePeriodoMatricula.monto_rubro_cuotas:
                            raise NameError(f"Periodo acádemico no permite diferir arancel manor a ${ePeriodoMatricula.monto_rubro_cuotas}")
                        num_cuotas = ePeriodoMatricula.num_cuotas_rubro
                        try:
                            valor_cuota_mensual = (valorarancel / num_cuotas).quantize(Decimal('.01'))
                        except ZeroDivisionError:
                            valor_cuota_mensual = 0
                        if valor_cuota_mensual == 0:
                            raise NameError(u"No se puede procesar el registro.")
                        eRubroMatricula = Rubro.objects.filter(matricula=eMatricula, tipo_id=RUBRO_MATRICULA)[0]
                        eRubroMatricula.relacionados = None
                        eRubroMatricula.save(request, update_fields=['relacionados'])
                        lista = []
                        c = 0
                        for r in ePeriodoMatricula.fecha_cuotas_rubro().values('fecha').distinct():
                            c += 1
                            lista.append([c, valor_cuota_mensual, r['fecha']])
                        for item in lista:
                            rubro = Rubro(tipo_id=RUBRO_ARANCEL,
                                          persona=Persona.objects.get(pk=ePersona.id),
                                          relacionados=eRubroMatricula,
                                          matricula=eMatricula,
                                          nombre=nombrearancel,
                                          cuota=item[0],
                                          fecha=datetime.now().date(),
                                          fechavence=item[2],
                                          valor=item[1],
                                          iva_id=1,
                                          valoriva=0,
                                          valortotal=item[1],
                                          saldo=item[1],
                                          cancelado=False)
                            rubro.save(request)
                        arancel.delete()
                        # Matricula.objects.filter(pk=eMatricula.id).update(aranceldiferido=1)
                        url_acta_compromiso = ""
                        if ePeriodoMatricula.valida_rubro_acta_compromiso:
                            isResult, message = eMatricula.generar_actacompromiso_matricula_pregrado(request)
                            if not isResult:
                                raise NameError(message)
                            url_acta_compromiso = message
                            eMatricula.aranceldiferido = 1
                            eMatricula.actacompromiso = url_acta_compromiso
                            eMatricula.save(request, update_fields=['aranceldiferido', 'actacompromiso'])
                        return Helper_Response(isSuccess=True, data={'acta_compromiso': url_acta_compromiso}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error al diferir: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'aceptarAutomatricula':
                with transaction.atomic():
                    try:
                        id = int(encrypt(request.data['id'])) if 'id' in request.data and request.data['id'] else 0
                        if not Inscripcion.objects.filter(pk=id):
                            raise NameError(u"No se reconocio al estudiante.")
                        termino = int(request.data['termino']) if 'termino' in request.data and request.data['termino'] else 0
                        if not Inscripcion.objects.values("id").filter(pk=id):
                            raise NameError(u"No se reconocio al estudiante.")
                        if not termino:
                            raise NameError(u"Debe aceptar los terminos.")
                        inscripcion = Inscripcion.objects.get(pk=id)
                        if not inscripcion.matricula_set.values("id").filter(automatriculapregrado=True, termino=False, nivel__periodo=ePeriodo).exists():
                            raise NameError(u"Debe aceptar los terminos.")
                        matricula = inscripcion.matricula_set.filter(automatriculapregrado=True, termino=False, nivel__periodo=ePeriodo)[0]
                        matricula.termino = True
                        matricula.fechatermino = datetime.now()
                        matricula.save(request, update_fields=['termino', 'fechatermino'])
                        log(u'Acepto los terminos de la matricula: %s' % matricula, request, "edit")
                        if not matricula.confirmarmatricula_set.filter(matricula=matricula):
                            confirmar = ConfirmarMatricula(matricula=matricula, estado=True)
                            confirmar.save(request)
                            log(u'Confirmo la matricula: %s' % confirmar, request, "add")
                        matricula.rubro_set.all().update(status=True)
                        valorpagar = str(null_to_decimal(matricula.rubro_set.filter(status=True).aggregate(valor=Sum('valortotal'))['valor']))
                        descripcionarancel = ''
                        valorarancel = ''
                        if (ra := matricula.rubro_set.filter(status=True, tipo_id=RUBRO_ARANCEL).first()) is not None:
                            descripcionarancel = ra.nombre
                            valorarancel = str(ra.valortotal)
                            matricula.aranceldiferido = 2
                            matricula.save(request)

                        return Helper_Response(isSuccess=True, data={"valorpagar": valorpagar, "descripcionarancel": descripcionarancel, "valorarancel": valorarancel, "phase": matricula.id, "periodo_id": encrypt(matricula.nivel.periodo.id)}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error al guardar: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'rechazoAutomatricula':
                with transaction.atomic():
                    try:
                        id = int(encrypt(request.data['id'])) if 'id' in request.data and request.data['id'] else 0
                        if not Inscripcion.objects.filter(pk=id):
                            raise NameError(u"No se reconocio al estudiante.")
                        inscripcion = Inscripcion.objects.get(pk=id)
                        if not inscripcion.matricula_set.values("id").filter(automatriculapregrado=True, termino=False, nivel__periodo=ePeriodo).exists():
                            raise NameError(u"Debe aceptar los terminos.")
                        matricula = inscripcion.matricula_set.filter(automatriculapregrado=True, termino=False, nivel__periodo=ePeriodo)[0]
                        rubro = Rubro.objects.filter(matricula=matricula, status=True)
                        if rubro:
                            if Rubro.objects.filter(matricula=matricula, status=True)[0].tiene_pagos():
                                raise NameError(u"No puede eliminar la matricula, porque existen rubros de la matricula ya cancelados.")
                        delmatricula = matricula
                        auditoria = AuditoriaMatricula(inscripcion=matricula.inscripcion,
                                                       periodo=matricula.nivel.periodo,
                                                       tipo=3)
                        auditoria.save(request)
                        matricula.delete()
                        log(u'Elimino matricula: %s' % delmatricula, request, "del")
                        return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error al rechazar: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadDetalleRubros':
                try:
                    id = int(encrypt(request.data['id'])) if 'id' in request.data and request.data['id'] else 0
                    try:
                        eMatricula = Matricula.objects.get(pk=id)
                    except ObjectDoesNotExist:
                        raise NameError(u"No se reconocio al estudiante.")
                    ePeriodoMatricula = None
                    if eMatricula.nivel.periodo.periodomatricula_set.values('id').filter(status=True).exists():
                        ePeriodoMatricula = eMatricula.nivel.periodo.periodomatricula_set.filter(status=True)[0]
                    if not eMatricula.inscripcion.coordinacion_id in [1, 2, 3, 4, 5]:
                        raise NameError(u"No se reconocio la coordinación.")
                    porcentaje_perdidad_parcial_gratuidad = PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD
                    if ePeriodoMatricula and ePeriodoMatricula.porcentaje_perdidad_parcial_gratuidad > 0:
                        porcentaje_perdidad_parcial_gratuidad = ePeriodoMatricula.porcentaje_perdidad_parcial_gratuidad
                    cursor = connection.cursor()
                    itinerario = 0
                    if not eMatricula.inscripcion.itinerario is None and eMatricula.inscripcion.itinerario > 0:
                        itinerario = eMatricula.inscripcion.itinerario
                    sql = f"select am.nivelmalla_id, count(am.nivelmalla_id) as cantidad_materias_seleccionadas from sga_materiaasignada ma, sga_materia m, sga_asignaturamalla am where ma.status=true and ma.matricula_id={str(eMatricula.id)} and m.status=true and m.id=ma.materia_id and am.status=true and am.id=m.asignaturamalla_id GROUP by am.nivelmalla_id, am.malla_id order by count(am.nivelmalla_id) desc, am.nivelmalla_id desc limit 1;"
                    if itinerario > 0:
                        sql = f"select am.nivelmalla_id, count(am.nivelmalla_id) as cantidad_materias_seleccionadas from sga_materiaasignada ma, sga_materia m, sga_asignaturamalla am where ma.status=true and ma.matricula_id={str(eMatricula.id)} and m.status=true and m.id=ma.materia_id and am.status=true and am.id=m.asignaturamalla_id and (am.itinerario=0 or am.itinerario=" + str(
                            itinerario) + ") GROUP by am.nivelmalla_id, am.malla_id order by count(am.nivelmalla_id) desc, am.nivelmalla_id desc limit 1;"

                    cursor.execute(sql)
                    results = cursor.fetchall()
                    nivel = 0
                    for per in results:
                        nivel = per[0]
                        cantidad_seleccionadas = per[1]
                    cantidad_nivel = 0
                    materiasnivel = []
                    eAsignaturaMallas = AsignaturaMalla.objects.filter(nivelmalla__id=nivel, status=True,
                                                                       malla=eMatricula.inscripcion.mi_malla())
                    if itinerario > 0:
                        eAsignaturaMallas = eAsignaturaMallas.filter(Q(itinerario=0) | Q(itinerario=itinerario))
                    for eAsignaturaMalla in eAsignaturaMallas:
                        if Materia.objects.values('id').filter(nivel__periodo=eMatricula.nivel.periodo,
                                                               asignaturamalla=eAsignaturaMalla).exists():
                            if eMatricula.inscripcion.estado_asignatura(eAsignaturaMalla.asignatura) != 1:
                                cantidad_nivel += 1

                    porcentaje_seleccionadas = int(round(Decimal(
                        (float(cantidad_nivel) * float(porcentaje_perdidad_parcial_gratuidad)) / 100).quantize(
                        Decimal('.00')), 0))
                    cobro = 0
                    if eMatricula.inscripcion.estado_gratuidad == 1 or eMatricula.inscripcion.estado_gratuidad == 2:
                        if (cantidad_seleccionadas < porcentaje_seleccionadas):
                            mensaje = f"Estudiante irregular, se ha matriculado en menos del {porcentaje_perdidad_parcial_gratuidad}%, debe cancelar por todas las asignaturas."
                            cobro = 1
                        else:
                            mensaje = u"Debe cancelar por las asignaturas que se matriculó por más de una vez."
                            cobro = 2
                    else:
                        if eMatricula.inscripcion.estado_gratuidad == 2:
                            mensaje = u"Su estado es de pérdida parcial de la gratuidad. Debe cancelar por las asignaturas que se matriculó por más de una vez."
                            cobro = 2
                        else:
                            mensaje = u"Alumno Regular"
                            cobro = 3
                    if eMatricula.inscripcion.persona.tiene_otro_titulo(inscripcion=eMatricula.inscripcion):
                        mensaje = u"El estudiante registra título en otra IES Pública o SENESCYT ha reportado. Su estado es de pérdida total de la gratuidad. Debe cancelar por todas las asignaturas."
                        cobro = 3
                    if cobro > 0:
                        for eMateriaAsignada in eMatricula.materiaasignada_set.filter(status=True,
                                                                                      retiramateria=False):
                            if cobro == 1:
                                materiasnivel.append(eMateriaAsignada.id)
                            else:
                                if cobro == 2:
                                    if eMateriaAsignada.matriculas > 1:
                                        materiasnivel.append(eMateriaAsignada.id)
                                else:
                                    materiasnivel.append(eMateriaAsignada.id)

                    matriculagruposocioeconomico = eMatricula.matriculagruposocioeconomico_set.filter(status=True)

                    if matriculagruposocioeconomico.values("id").exists():
                        eGrupoSocioEconomico = matriculagruposocioeconomico[0].gruposocioeconomico
                    else:
                        eGrupoSocioEconomico = eMatricula.inscripcion.persona.grupoeconomico()
                    eTipoOtroRubroArancel = TipoOtroRubro.objects.get(pk=RUBRO_ARANCEL)
                    eTipoOtroRubroMatricula = TipoOtroRubro.objects.get(pk=RUBRO_MATRICULA)
                    # valorMatricula = 0
                    # valorArancel = 0
                    aMateriaAsignadas = []
                    if eMatricula.nivel.periodo.tipocalculo in (1, 2, 3, 4, 5):
                        valorGrupo = 0
                        if eMatricula.nivel.periodo.tipocalculo == 1:
                            ePeriodoGrupoSocioEconomico = \
                            PeriodoGrupoSocioEconomico.objects.filter(status=True, periodo=eMatricula.nivel.periodo,
                                                                      gruposocioeconomico=eGrupoSocioEconomico)[0]
                            valorGrupo = ePeriodoGrupoSocioEconomico.valor
                        elif eMatricula.nivel.periodo.tipocalculo in (2, 3, 4, 5):
                            malla = eMatricula.inscripcion.mi_malla()
                            if malla is None:
                                raise NameError(u"Malla sin configurar")
                            periodomalla = PeriodoMalla.objects.filter(periodo=eMatricula.nivel.periodo,
                                                                       malla=malla, status=True)
                            if not periodomalla.values("id").exists():
                                raise NameError(u"Malla no tiene configurado valores de cobro")
                            periodomalla = periodomalla[0]
                            detalleperiodomalla = DetallePeriodoMalla.objects.filter(periodomalla=periodomalla,
                                                                                     gruposocioeconomico=eGrupoSocioEconomico,
                                                                                     status=True)
                            if not detalleperiodomalla.values("id").exists():
                                raise NameError(
                                    u"Malla en grupo socioeconomico no tiene configurado valores de cobro")
                            valorGrupo = detalleperiodomalla[0].valor
                        for eMateriaAsignada in MateriaAsignada.objects.filter(pk__in=materiasnivel):
                            creditos = 0
                            total = 0
                            if eMateriaAsignada.existe_modulo_en_malla():
                                creditos = eMateriaAsignada.materia_modulo_malla().creditos
                                total = null_to_decimal((Decimal(creditos).quantize(Decimal('.01')) * Decimal(
                                    valorGrupo).quantize(Decimal('.01'))).quantize(Decimal('.01')), 2)
                            elif eMateriaAsignada.materia.asignaturamalla.creditos > 0:
                                creditos = eMateriaAsignada.materia.asignaturamalla.creditos
                                total = null_to_decimal((Decimal(creditos).quantize(Decimal('.01')) * Decimal(
                                    valorGrupo).quantize(Decimal('.01'))).quantize(Decimal('.01')), 2)
                            else:
                                creditos = eMateriaAsignada.materia.creditos
                                total = null_to_decimal((Decimal(creditos).quantize(Decimal('.01')) * Decimal(
                                    valorGrupo).quantize(Decimal('.01'))).quantize(Decimal('.01')), 2)
                            aMateriaAsignadas.append({"id": encrypt(eMateriaAsignada.id),
                                                      "asignatura": eMateriaAsignada.materia.asignaturamalla.asignatura.nombre,
                                                      "creditos": creditos,
                                                      "valor": valorGrupo,
                                                      "total": total,
                                                      "fecha_asignacion": eMateriaAsignada.fecha_creacion.strftime(
                                                          "%d-%m-%Y %H:%M:%S"),
                                                      "fecha_eliminacion": None,
                                                      "activo": True,
                                                      "nivel": eMateriaAsignada.materia.asignaturamalla.nivelmalla.nombre})
                        # valorArancel = null_to_decimal(Rubro.objects.filter(matricula=eMatricula, status=True,
                        #                                                     tipo=eTipoOtroRubroArancel).aggregate(
                        #     valor=Sum('valortotal'))['valor'])
                        # valorMatricula = null_to_decimal(Rubro.objects.filter(matricula=eMatricula, status=True,
                        #                                                       tipo=eTipoOtroRubroMatricula).aggregate(
                        #     valor=Sum('valortotal'))['valor'])
                    elif eMatricula.nivel.periodo.tipocalculo == 6:
                        eDetalleRubroMatriculas = DetalleRubroMatricula.objects.filter(matricula=eMatricula)
                        # eDetalleRubroMatriculas_m = eDetalleRubroMatriculas.filter(materia__isnull=True)
                        eDetalleRubroMatriculas_a = eDetalleRubroMatriculas.filter(materia__isnull=False)
                        # if eDetalleRubroMatriculas_m.values("id").exists():
                        #     valorMatricula = null_to_decimal(Rubro.objects.filter(matricula=eMatricula, status=True,
                        #                                                           tipo=eTipoOtroRubroMatricula).aggregate(
                        #         valor=Sum('valortotal'))['valor'])
                        # if eDetalleRubroMatriculas_a.values("id").exists():
                        #     valorArancel = null_to_decimal(Rubro.objects.filter(matricula=eMatricula, status=True,
                        #                                                         tipo=eTipoOtroRubroArancel).aggregate(
                        #         valor=Sum('valortotal'))['valor'])
                        for eDetalleRubroMatricula in eDetalleRubroMatriculas_a:
                            total = null_to_decimal((Decimal(eDetalleRubroMatricula.creditos).quantize(
                                Decimal('.01')) * Decimal(eDetalleRubroMatricula.costo).quantize(
                                Decimal('.01'))).quantize(Decimal('.01')), 2)
                            aMateriaAsignadas.append({"id": encrypt(eDetalleRubroMatricula.materia.id),
                                                      "asignatura": eDetalleRubroMatricula.materia.asignaturamalla.asignatura.nombre,
                                                      "creditos": eDetalleRubroMatricula.creditos,
                                                      "valor": eDetalleRubroMatricula.costo,
                                                      "total": total,
                                                      "fecha_asignacion": eMateriaAsignada.fecha_creacion.strftime(
                                                          "%d-%m-%Y %H:%M:%S"),
                                                      "fecha_eliminacion": eDetalleRubroMatricula.fecha.strftime(
                                                          "%d-%m-%Y %H:%M:%S") if eDetalleRubroMatricula.fecha else None,
                                                      "activo": eDetalleRubroMatricula.activo,
                                                      "nivel": eDetalleRubroMatricula.materia.asignaturamalla.nivelmalla.nombre})
                    else:
                        raise NameError(u"No se encontro configuración del proceso de cobro de matriculación")
                    return Helper_Response(isSuccess=True, data=aMateriaAsignadas, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'savereservacupoasignatura':
                with transaction.atomic():
                    try:
                        idsesion = int(encrypt(request.data['idsesion'])) if 'idsesion' in request.data and request.data['idsesion'] else 0
                        idam = int(request.data['idam']) if 'idam' in request.data and request.data['idam'] else 0
                        eSesion = Sesion.objects.get(pk=idsesion)
                        ePeriodoMatriculaReserva =PeriodoMatricula.objects.filter(status=True, activo=True, tipo=2).first()
                        eAsignaturaMalla = AsignaturaMalla.objects.get(pk=idam)
                        if not SolicitudReservaCupoMateria.objects.filter(status=True,periodo_id= ePeriodo.id,inscripcion_id= eInscripcion.id,periodomatricula_id= ePeriodoMatriculaReserva.id).exists():
                            eSolicitudReservaCupoMateria = SolicitudReservaCupoMateria(
                                periodo_id= ePeriodo.id,
                                inscripcion_id= eInscripcion.id,
                                periodomatricula_id= ePeriodoMatriculaReserva.id,
                                estado= 0,
                            )
                            eSolicitudReservaCupoMateria.save(request)
                            log(f'adiciono cabecera reserva cupo asignatura: {eInscripcion} {ePeriodo} - {ePeriodoMatriculaReserva} - {eSesion} ', request, "add")
                        else:
                            eSolicitudReservaCupoMateria = SolicitudReservaCupoMateria.objects.filter(status=True,periodo= ePeriodo,inscripcion= eInscripcion,periodomatricula= ePeriodoMatriculaReserva).first()

                        if eSolicitudReservaCupoMateria:
                            eDetalleSolicitudReservaCupoMateria = DetalleSolicitudReservaCupoMateria(
                                solicitud_id = eSolicitudReservaCupoMateria.id,
                                asignaturamalla_id = eAsignaturaMalla.id,
                                sesion_id = eSesion.id,
                            )
                            eDetalleSolicitudReservaCupoMateria.save(request)
                            log(f'adiciono cabecera reserva cupo asignatura: {eInscripcion} {ePeriodo} - {ePeriodoMatriculaReserva} - {eDetalleSolicitudReservaCupoMateria} ', request, "add")

                        aData = {}
                        aData['eDetalleSolicitudReservaCupoMateria'] = DetalleSolicitudReservaCupoMateria.objects.filter(
                                status=True, solicitud__periodo_id=ePeriodo.id,
                                solicitud__inscripcion_id=eInscripcion.id,
                                solicitud__periodomatricula_id=ePeriodoMatriculaReserva.id).values_list(
                                'asignaturamalla', 'sesion__nombre', 'id')

                        return Helper_Response(isSuccess=True,message=f'Recuerde usted no se ha matriculado, usted ha realizado la solicitud de cupo en {eAsignaturaMalla.asignatura}, sesión:{eSesion.nombre}', data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                                   status=status.HTTP_200_OK)

            elif action == 'savereservacupoasignaturaenlineasemipresencial':
                with transaction.atomic():
                    try:
                        idam = int(request.data['idam']) if 'idam' in request.data and request.data['idam'] else 0
                        ePeriodoMatriculaReserva =PeriodoMatricula.objects.filter(status=True, activo=True, tipo=2).first()
                        eAsignaturaMalla = AsignaturaMalla.objects.get(pk=idam)
                        if not SolicitudReservaCupoMateria.objects.filter(status=True,periodo_id= ePeriodo.id,inscripcion_id= eInscripcion.id,periodomatricula_id= ePeriodoMatriculaReserva.id).exists():
                            eSolicitudReservaCupoMateria = SolicitudReservaCupoMateria(
                                periodo_id= ePeriodo.id,
                                inscripcion_id= eInscripcion.id,
                                periodomatricula_id= ePeriodoMatriculaReserva.id,
                                estado= 0,

                            )
                            eSolicitudReservaCupoMateria.save(request)
                            log(f'adiciono cabecera reserva cupo asignatura: {eInscripcion} {ePeriodo} - {ePeriodoMatriculaReserva} - {eInscripcion.sesion} ', request, "add")
                        else:
                            eSolicitudReservaCupoMateria = SolicitudReservaCupoMateria.objects.filter(status=True,periodo_id= ePeriodo.id,inscripcion_id= eInscripcion.id,periodomatricula_id= ePeriodoMatriculaReserva.id).first()

                        if eSolicitudReservaCupoMateria:
                            eDetalleSolicitudReservaCupoMateria = DetalleSolicitudReservaCupoMateria(
                                solicitud_id = eSolicitudReservaCupoMateria.id,
                                asignaturamalla_id = eAsignaturaMalla.id,
                                sesion_id=eInscripcion.sesion.id
                            )
                            eDetalleSolicitudReservaCupoMateria.save(request)
                            log(f'adiciono cabecera reserva cupo asignatura: {eInscripcion} {ePeriodo} - {ePeriodoMatriculaReserva} - {eDetalleSolicitudReservaCupoMateria} ', request, "add")

                        aData = {}
                        aData['eDetalleSolicitudReservaCupoMateria'] = DetalleSolicitudReservaCupoMateria.objects.filter(
                                status=True, solicitud__periodo_id=ePeriodo.id,
                                solicitud__inscripcion_id=eInscripcion.id,
                                solicitud__periodomatricula_id=ePeriodoMatriculaReserva.id).values_list(
                                'asignaturamalla', 'sesion__nombre', 'id')

                        return Helper_Response(isSuccess=True,message=f'Recuerde usted no se ha matriculado, usted ha realizado la solicitud de cupo en {eAsignaturaMalla.asignatura}, sesión {eInscripcion.sesion}', data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                                   status=status.HTTP_200_OK)

            elif action == 'removerreservacupoasignatura':
                    with transaction.atomic():
                        try:
                            aData = {}
                            iddetallesolicitudreserva = int(request.data['iddetallesolicitudreserva']) if 'iddetallesolicitudreserva' in request.data and request.data['iddetallesolicitudreserva'] else 0
                            idam = int(request.data['idam']) if 'idam' in request.data and request.data['idam'] else 0
                            ePeriodoMatriculaReserva =PeriodoMatricula.objects.filter(status=True, activo=True, tipo=2).first()
                            eAsignaturaMalla = AsignaturaMalla.objects.get(pk=idam)
                            eDetalleSolicitudReservaCupoMateria = DetalleSolicitudReservaCupoMateria.objects.get(pk=iddetallesolicitudreserva)
                            eDetalleSolicitudReservaCupoMateria.status=False
                            eDetalleSolicitudReservaCupoMateria.save(request)
                            log(f'edlimino  reserva cupo asignatura: {eDetalleSolicitudReservaCupoMateria}',  request, "del")


                            aData['asigmalla_id'] = eDetalleSolicitudReservaCupoMateria.asignaturamalla.id
                            aData['eDetalleSolicitudReservaCupoMateria'] = DetalleSolicitudReservaCupoMateria.objects.filter(
                                status=True, solicitud__periodo_id=ePeriodo.id,
                                solicitud__inscripcion_id=eInscripcion.id,
                                solicitud__periodomatricula_id=ePeriodoMatriculaReserva.id).values_list(
                                'asignaturamalla', 'sesion__nombre', 'id')

                            return Helper_Response(isSuccess=True,message=f'Removió la solicitud de solicitud de cupo en la asignatura {eDetalleSolicitudReservaCupoMateria.asignaturamalla.asignatura.nombre}, sesión {eDetalleSolicitudReservaCupoMateria.sesion}', data=aData, status=status.HTTP_200_OK)
                        except Exception as ex:
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={},
                                                   message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                                   status=status.HTTP_200_OK)


            return Helper_Response(isSuccess=False, data={}, message=f'Acción no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)

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
            eInscripcion = ePerfilUsuario.inscripcion
            ePersona = eInscripcion.persona
            ePeriodoMatricula = None
            eMatricula = None
            ePeriodo = None
            if 'id' in payload['periodo']:
                periodoEnCache = cache.get(f"periodo_id_{payload['periodo']['id']}")
                if periodoEnCache:
                    ePeriodo = periodoEnCache
                else:
                    if payload['periodo']['id'] is None:
                        if not PeriodoMatricula.objects.values("id").filter(tipo=2, activo=True).exists():
                            raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el periodo de matriculación se encuentra inactivo")
                        ePeriodoMatricula = PeriodoMatricula.objects.filter(status=True, tipo=2, activo=True).order_by('-pk')[0]
                        ePeriodo = ePeriodoMatricula.periodo
                    else:
                        ePeriodo = Periodo.objects.db_manager("sga_select").get(pk=encrypt(payload['periodo']['id']))
                    cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)

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
                eMatricula = Matricula.objects.filter(nivel__periodo=ePeriodoMatricula.periodo, inscripcion=eInscripcion, status=True).first()
                eNivel = eMatricula.nivel
                if not eNivel.fechainicioagregacion or not eNivel.fechatopematricula or not eNivel.fechatopematriculaex or not eNivel.fechatopematriculaes:
                    raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el proceso de matrícula se encuentra inactivo...")

                if hoy < eNivel.fechainicioagregacion:
                    raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el proceso de matrícula empieza el %s" % eNivel.fechainicioagregacion.__str__())
                if hoy <= eNivel.fechatopematriculaes:
                    if hoy > eNivel.fechatopematriculaex:
                        if ePeriodoMatricula.valida_proceos_matricula_especial:
                            raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el proceso de matrícula especial termina el {eNivel.fechatopematriculaes.__str__()}. <br>Verificar en el módulo <a href='/alu_solicitudmatricula' class='bloqueo_pantalla'>Solicitud de Matrícula</a>")
                        else:
                            raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el proceso de matrícula especial termina el {eNivel.fechatopematriculaes.__str__()}.")
                else:
                    if hoy > eNivel.fechatopematriculaes:
                        raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el proceso de matrícula especial terminó el %s" % eNivel.fechatopematriculaes.__str__())

                if ePeriodoMatricula.valida_cronograma:
                    if not puede_matricularse_seguncronograma_coordinacion(eInscripcion, eNivel.periodo):
                        raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, aún no está habilitado el cronograma de matriculación de su carrera.")
                else:
                    if ePeriodoMatricula.tiene_cronograma_carreras():
                        a = puede_matricularse_seguncronograma_carrera(eInscripcion, eNivel.periodo)
                        if a[0] == 2:
                            raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, aún no está habilitado el cronograma de matriculación de su carrera.")
                        if a[0] == 3:
                            raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, usted no realizó su Pre-Matrícula (matricularse después de dos días de haber iniciado matrícula ordinaria).")
                        if a[0] == 4:
                            log(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el periodo de matriculación no se encuentra activo.... %s" % (
                                eInscripcion.info()), request, "add")
                            raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el periodo de matriculación no se encuentra activo")
                eMalla = eInscripcion.malla_inscripcion().malla
                tiene_rubro_pagado_matricula = False
                tiene_rubro_pagado_materias = False
                # valor_pagados = 0.0
                # valor_pendiente = 0.0
                # if eMatricula.rubro_set.values("id").filter(status=True).exists():
                    # tiene_rubro_pagado_materias = tiene_rubro_pagado_matricula = eMatricula.tiene_pagos_matricula()
                    # valor_pagados = eMatricula.total_pagado_rubro()
                    # valor_pendiente = eMatricula.total_saldo_rubro()

                ePersona_serializer = MatriPersonaSerializer(eInscripcion.persona)
                eInscripcion_serializer = MatriInscripcionSerializer(eInscripcion)
                eCarrera_serializer = MatriCarreraSerializer(eInscripcion.carrera)
                data_json = {
                    'is_superuser': ePersona.usuario.is_superuser
                }
                ePeriodoMatricula_serializer = MatriPeriodoMatriculaSerializer(ePeriodoMatricula, context=data_json)
                eInscripcionMalla_serializer = MatriInscripcionMallaSerializer(eInscripcion.malla_inscripcion())
                eMalla_serializer = MatriMallaSerializer(eMalla)
                eNivelMalla_serializer = MatriNivelMallaSerializer(eInscripcion.mi_nivel().nivel)
                eMatricula_serializer = MatriculaSerializer(eMatricula)
                eMateriaAsignada_serializer = MatriMateriaAsignadaSerializer(eInscripcion.materias_automatriculapregrado_por_confirmar(ePeriodoMatricula.periodo), many=True)
                aData['ePersona'] = ePersona_serializer.data if ePersona_serializer else None
                aData['eInscripcion'] = eInscripcion_serializer.data if eInscripcion_serializer else None
                aData['eCarrera'] = eCarrera_serializer.data if eCarrera_serializer else None
                aData['eMalla'] = eMalla_serializer.data if eMalla_serializer else None
                aData['FichaSocioEconomicaINEC'] = ePersona.fichasocioeconomicainec()
                aData['ePeriodoMatricula'] = ePeriodoMatricula_serializer.data if ePeriodoMatricula_serializer else None
                aData['eInscripcionMalla'] = eInscripcionMalla_serializer.data if eInscripcionMalla_serializer else None
                aData['eNivelMalla'] = eNivelMalla_serializer.data if eNivelMalla_serializer else None
                aData['Title'] = "Confirmación de automatrícula"
                aData['eMatricula'] = eMatricula_serializer.data if eMatricula_serializer else None
                aData['eMateriasAsignadas'] = eMateriaAsignada_serializer.data if eMateriaAsignada_serializer else []
                valorMatricula = valorArancel = valorTotal  = 0.0
                if len(eRubros := eMatricula.rubro_set.filter(tipo_id__in=[RUBRO_ARANCEL, RUBRO_MATRICULA])) > 0:
                    valorArancel = null_to_decimal(eRubros.filter(tipo_id=RUBRO_ARANCEL).aggregate(valor=Sum('valortotal'))['valor'], 2)
                    valorMatricula = null_to_decimal(eRubros.filter(tipo_id=RUBRO_MATRICULA).aggregate(valor=Sum('valortotal'))['valor'], 2)
                    valorTotal = null_to_decimal((valorMatricula + valorArancel), 2)

                aData['valorMatricula'] = valorMatricula
                aData['valorArancel'] = valorArancel
                aData['valorTotal'] = valorTotal
                tiene_valores_pendientes = False
                msg_valores_pendientes = ''
                tipo_valores_alerta = ''
                if ePeriodoMatricula.valida_deuda:
                    filtros = Q(persona=ePersona) & Q(cancelado=False) & Q(status=True)
                    if ePeriodoMatricula.tiene_tiposrubros():
                        filtros = filtros & Q(tipo__in=ePeriodoMatricula.tiposrubros())
                    _rubros = Rubro.objects.filter(filtros)
                    if _rubros.values("id").exists():
                        tiene_valores_pendientes = True
                        rubros_vencidos = _rubros.filter(fechavence__lt=datetime.now().date()).distinct()
                        if rubros_vencidos.exists():
                            valor_rubros = null_to_numeric(rubros_vencidos.aggregate(valor=Sum('valortotal'))['valor'])
                            valor_pagos = null_to_numeric(Pago.objects.filter(rubro__in=rubros_vencidos, status=True).distinct().aggregate(valor=Sum('valortotal'))['valor'])
                            valores_vencidos = valor_rubros - valor_pagos
                            msg_valores_pendientes = f"""Estimad{'a' if ePersona.es_mujer() else 'o'} {ePersona.__str__()}, aún posee <b>VALORES PENDIENTES POR PAGAR</b>. Total de deuda: <b>${valores_vencidos}</b>"""
                            tipo_valores_alerta = 'danger'
                        else:
                            valor_rubros = null_to_numeric(_rubros.aggregate(valor=Sum('valortotal'))['valor'])
                            valor_pagos = null_to_numeric(Pago.objects.filter(rubro__in=_rubros, status=True).distinct().aggregate(valor=Sum('valortotal'))['valor'])
                            valores_pendientes = valor_rubros - valor_pagos
                            msg_valores_pendientes = f"""Estimad{'a' if ePersona.es_mujer() else 'o'} {ePersona.__str__()}, posee <b>VALORES PENDIENTES POR PAGAR</b>.  Total de deuda: <b>${valores_pendientes}</b>"""
                            tipo_valores_alerta = 'warning'
                aData['tiene_valores_pendientes'] = tiene_valores_pendientes
                aData['msg_valores_pendientes'] = msg_valores_pendientes
                aData['tipo_valores_alerta'] = tipo_valores_alerta
                return Helper_Response(isSuccess=True, data={"tipo": "automatricula", "aData": aData}, status=status.HTTP_200_OK)

            if ePeriodo and ePeriodoMatricula and ePeriodoMatricula.periodo.id == ePeriodo.id and ePersona.tiene_matricula_periodo(ePeriodo):
                eMatricula = eInscripcion.matricula_periodo2(ePeriodo)
                if ConfirmarMatricula.objects.values('id').filter(matricula=eMatricula).exists():
                    raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, le informamos que ya se encuentra matriculado en el Periodo {ePeriodo.__str__()}. <br>Verificar en el módulo <a href='/alu_materias' class='bloqueo_pantalla'>Mis Materias</a>")
            else:
                eMatricula = eInscripcion.matricula_periodo2(ePeriodoMatricula.periodo)
                if ConfirmarMatricula.objects.values('id').filter(matricula=eMatricula).exists():
                    raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, le informamos que ya se encuentra matriculado en el Periodo {ePeriodo.__str__()}. <br>Verificar en el módulo <a href='/alu_materias' class='bloqueo_pantalla'>Mis Materias</a>")

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
            if hoy <= eNivel.fechatopematriculaes:
                if hoy > eNivel.fechatopematriculaex:
                    if ePeriodoMatricula.valida_proceos_matricula_especial:
                        raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el proceso de matrícula especial termina el {eNivel.fechatopematriculaes.__str__()}. <br>Verificar en el módulo <a href='/alu_solicitudmatricula' class='bloqueo_pantalla'>Solicitud de Matrícula</a>")
                    else:
                        raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el proceso de matrícula especial termina el {eNivel.fechatopematriculaes.__str__()}.")
            else:
                if hoy > eNivel.fechatopematriculaes:
                    raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el proceso de matrícula especial terminó el %s" % eNivel.fechatopematriculaes.__str__())

            if ePeriodoMatricula.valida_cronograma:
                if not puede_matricularse_seguncronograma_coordinacion(eInscripcion, eNivel.periodo):
                    raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, aún no está habilitado el cronograma de matriculación de su carrera.")
            else:
                if ePeriodoMatricula.tiene_cronograma_carreras():
                    a = puede_matricularse_seguncronograma_carrera(eInscripcion, eNivel.periodo)
                    if a[0] == 2:
                        raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, aún no está habilitado el cronograma de matriculación de su carrera.")
                    if a[0] == 3:
                        raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, usted no realizó su Pre-Matrícula (matricularse después de dos días de haber iniciado matrícula ordinaria).")
                    if a[0] == 4:
                        log(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el periodo de matriculación no se encuentra activo.... %s" % (eInscripcion.info()), request, "add")
                        raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el periodo de matriculación no se encuentra activo")
            eMalla = None
            eInscripcionMalla = eInscripcion.malla_inscripcion()
            if not eInscripcion.tiene_malla():
                raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, debe tener malla asociada para poder matricularse.")
            eMalla = eInscripcionMalla.malla
            if eInscripcion.tiene_perdida_carrera(ePeriodoMatricula.num_matriculas):
                raise NameError(f"Atencion: Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, su limite de matricula por perdida de una o mas asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria de la facultad para mas informacion.")

            if variable_valor('VALIDAR_QUE_SEA_PRIMERA_MATRICULA'):
                if eInscripcion.matricula_set.values('id').filter(status=True).exists():
                    raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, no puede matricularse; solo apto para primer nivel (nuevos).")

            eAsignaturasMallas = AsignaturaMalla.objects.filter(status=True, malla_id=eInscripcion.mi_malla().id)
            fechaultimamateriaprobada = None
            ultimamateriaaprobada = RecordAcademico.objects.filter(inscripcion_id=eInscripcion.id, status=True, asignatura_id__in=eAsignaturasMallas.values_list('asignatura_id', flat=True)).exclude(noaplica=True).order_by('-fecha')
            if ultimamateriaaprobada.values("id").exists():
                fechaultimamateriaprobada = ultimamateriaaprobada[0].fecha + timedelta(days=1810)
            if fechaultimamateriaprobada:
                if fechaultimamateriaprobada < eNivel.periodo.inicio:
                    raise NameError(u"Reglamento del Régimen Académico - DISPOSICIONES GENERALES: QUINTA.- Si un estudiante no finaliza su carrera o programa y se retira, podrá reingresar a la misma carrera o programa en el tiempo máximo de 5 años contados a partir de la fecha de su retiro. Si no estuviere aplicándose el mismo plan de estudios deberá completar todos los requisitos establecidos en el plan de estudios vigente a la fecha de su reingreso. Cumplido este plazo máximo para el referido reingreso, deberá reiniciar sus estudios en una carrera o programa vigente. En este caso el estudiante podrá homologar a través del mecanismo de validación de conocimientos, las asignaturas, cursos o sus equivalentes, en una carrera o programa vigente, de conformidad con lo establecido en el presente Reglamento.")
            ePreMatricula = None
            tienePreMatricula = False
            if PreMatricula.objects.values("id").filter(inscripcion=eInscripcion, periodo=ePeriodoMatricula.periodo, status=True).exists():
                ePreMatricula = PreMatricula.objects.filter(inscripcion=eInscripcion, periodo=ePeriodoMatricula.periodo, status=True).first()
                tienePreMatricula = True
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
            aData['itinerario'] = eInscripcion.itinerario if eInscripcion.itinerario else 0
            aData['eCarrera'] = eCarrera_serializer.data if eCarrera_serializer else None
            aData['eNivelMalla'] = eNivelMalla_serializer.data if eNivelMalla_serializer else None
            aData['validacion_matricula'] = validacion_matricula = variable_valor('VALIDACION_MATRICULA')
            aData['validacion_matricula_reserva'] = validacion_matricula_reserva = variable_valor('VALIDACION_MATRICULA_RESERVA')
            val_terc_prec = False
            if validacion_matricula == True:
                eMatriculaAnterior = Matricula.objects.filter(status=True,nivel__periodo=ePeriodo, inscripcion = eInscripcion).first()
                asignatura_esp_sin_registro = False
                if eMatriculaAnterior:
                    eInscripcion_mat = eMatriculaAnterior.inscripcion
                    nivel_real = eMatriculaAnterior.nivelmalla.orden
                else:
                    eInscripcion_mat = eInscripcion
                    nivel_real = eInscripcion_mat.mi_nivel().nivel.orden
                EJE_FORMATIVO_PRACTICAS = 9
                EJE_FORMATIVO_VINCULACION = 11
                EXCLUDE_EJE_FORMATIVO = [EJE_FORMATIVO_PRACTICAS, EJE_FORMATIVO_VINCULACION]
                # if eInscripcion.itinerario > 0:
                #     print(f"Tiene itinerario: {eInscripcion.itinerario}")
                eInscripcionMalla_mat = eInscripcion_mat.malla_inscripcion()
                eMalla_mat = eInscripcionMalla_mat.malla
                eInscripcionNivel_mat = eInscripcion_mat.mi_nivel()
                itinerario = []
                itinerario.append(0)
                if eInscripcionMalla_mat.malla.modalidad.id == 3:
                    eAsignaturasMalla = eMalla_mat.asignaturamalla_set.select_related().filter(status=True).exclude(
                        Q(nivelmalla_id=0) | Q(opcional=True)).order_by('nivelmalla', 'ejeformativo').filter(
                        itinerario__in=itinerario)
                else:
                    eAsignaturasMalla = eMalla_mat.asignaturamalla_set.select_related().filter(status=True).exclude(
                        Q(nivelmalla_id=0) | Q(opcional=True) | Q(ejeformativo_id__in=EXCLUDE_EJE_FORMATIVO)).order_by('nivelmalla', 'ejeformativo').filter(
                        itinerario__in=itinerario)

                if eInscripcion_mat.itinerario:
                    if eInscripcion_mat.itinerario > 0:
                        itinerario.append(eInscripcion_mat.itinerario)
                        eAsignaturasMalla = eAsignaturasMalla.filter(itinerario__in=itinerario)

                eModulosMalla = ModuloMalla.objects.filter(malla=eInscripcionMalla_mat.malla)
                # eNivelMallaAprobadoActual = eInscripcionNivel_mat.nivel
                eNivelMallaAprobadoActual = eInscripcion_mat.recordacademico_set.filter(asignaturamalla__in=eAsignaturasMalla,status=True, aprobada=True).values_list('asignaturamalla__nivelmalla__orden', flat=True).order_by('-asignaturamalla__nivelmalla__orden').first()
                regular = True
                asignaturas_especiales = []
                if eNivelMallaAprobadoActual:
                    eAsignaturasMallaquedebeaprobar = eAsignaturasMalla.filter(
                        nivelmalla__orden__lte=eNivelMallaAprobadoActual).exclude(
                        Q(asignatura__id__in=eModulosMalla.values_list('asignatura__id', flat=True)) | Q(
                            asignatura__in=AsignaturaMalla.objects.values_list("asignatura__id", flat=True).filter(
                                malla=eMalla_mat)))
                    eAsignaturasRecord = eInscripcion_mat.recordacademico_set.filter(asignaturamalla__in=eAsignaturasMalla,
                                                                                 status=True)

                    if eAsignaturasRecord.values("id").filter(aprobada=False).exists():
                        regular = False

                    elif eAsignaturasRecord.filter(asignaturamalla__in=eAsignaturasMallaquedebeaprobar, aprobada=True, status=True).count() < eAsignaturasMallaquedebeaprobar.values("id").count():
                        regular = False

                    elif eAsignaturasRecord.filter(
                        asignaturamalla__in=eAsignaturasMalla.filter(
                            nivelmalla__orden__gte=eNivelMallaAprobadoActual + 1).exclude(
                            Q(asignatura__id__in=eModulosMalla.values_list('asignatura__id', flat=True)) | Q(
                                asignatura__in=AsignaturaMalla.objects.values_list("asignatura__id", flat=True).filter(
                                    malla=eMalla_mat))), aprobada=True, status=True).exists():
                        regular = False
                    # -----------------------------------------------------Verificar si hay asignaturas sin aprobar hasta el nivel actual
                    if eInscripcionMalla_mat.malla.modalidad.id == 3:
                        eAsignaturasMallaHastaNivelActualTodas = eMalla_mat.asignaturamalla_set.select_related().filter(status=True,itinerario__in=itinerario, nivelmalla__orden__lte=eNivelMallaAprobadoActual).exclude(
                            Q(nivelmalla_id=NIVEL_MALLA_CERO) | Q(opcional=True))
                    else:
                        eAsignaturasMallaHastaNivelActualTodas = eMalla_mat.asignaturamalla_set.select_related().filter(status=True, itinerario__in=itinerario, nivelmalla__orden__lte=eNivelMallaAprobadoActual).exclude(
                            Q(nivelmalla_id=NIVEL_MALLA_CERO) | Q(opcional=True) | Q(ejeformativo_id__in=EXCLUDE_EJE_FORMATIVO))
                    asignaturas_sin_aprobar = eAsignaturasMallaHastaNivelActualTodas.exclude(id__in=eAsignaturasRecord.values_list("asignaturamalla_id", flat=True))
                    asignatura_esp = eAsignaturasMallaHastaNivelActualTodas.exclude(id__in=eAsignaturasRecord.values_list("asignaturamalla_id", flat=True)).filter(id__in = list(map(int, variable_valor('ASIGNATURAS_ESPECIALES'))))

                    if asignatura_esp:
                        asignaturas_especiales = [asig_esp.id for asig_esp in asignatura_esp]
                        asignatura_esp_sin_registro = True

                    if asignaturas_sin_aprobar.exists():
                        regular = False
                    elif eAsignaturasRecord.values("id").filter(aprobada=False).exists():
                        regular = False

                    nivel_real = nivel_real + 1 if regular else nivel_real

                    if regular and eMatriculaAnterior:
                        niv_record = eNivelMallaAprobadoActual
                        if niv_record:
                            nivel_real = niv_record + 1

                tienerecordhomologadas = eInscripcion.recordacademico_set.values('id').filter(homologada=True, status=True).exists()
                if not eMatriculaAnterior and not tienerecordhomologadas:
                    regular = True
                    nivel_real = 1

                aData['regular'] = regular
                aData['nivel_real'] = nivel_real
                aData['asignaturas_especiales'] = asignaturas_especiales
                aData['asignatura_esp_sin_registro'] = asignatura_esp_sin_registro
                ## VALIDAR PRECEDENCIA 3ERA MATRICULA
                eInscripcionMalla_prec = eInscripcion.malla_inscripcion()
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
                    puedetomar = eInscripcion.puede_tomar_materia(am.asignatura)
                    estado = eInscripcion.estado_asignatura(am.asignatura)
                    totalmatriculaasignatura = eInscripcion.total_record_asignaturatodo(am.asignatura)
                    if puedetomar == False and estado == 2 and totalmatriculaasignatura == 2 and val_terc_prec == False:
                        val_terc_prec = True
                # asignaturas_especiales = variable_valor('ASIGNATURAS_ESPECIALES')

            if eInscripcion.modalidad_id in [3,2 ]:#en linea y semipresencial
                eSesionesReservaAsignatura = Sesion.objects.none()
            else:
                eSesionesReservaAsignatura = Sesion.objects.filter(status=True, pk__in=[1, 4, 5])


            eSesionesReservaAsignatura = Sesion.objects.filter(status=True, pk__in =[1,4,5])
            ePeriodoMatriculaReserva = PeriodoMatricula.objects.filter(status=True, activo=True, tipo=2).first()
            eDetalleSolicitudReservaCupoMateria = DetalleSolicitudReservaCupoMateria.objects.filter(status=True,solicitud__periodo_id = ePeriodo.id,solicitud__inscripcion_id = eInscripcion.id,solicitud__periodomatricula_id = ePeriodoMatriculaReserva.id).values_list('asignaturamalla','sesion__nombre','id')
            aData['eDetalleSolicitudReservaCupoMateria'] = eDetalleSolicitudReservaCupoMateria if eDetalleSolicitudReservaCupoMateria else []
            aData['eSesionesReservaAsignatura'] = MatriSesionSerializer(eSesionesReservaAsignatura, many=True).data if MatriSesionSerializer(eSesionesReservaAsignatura, many=True) else []
            aData['eNivelesMalla'] = eNivelesMalla_serializer.data if eNivelesMalla_serializer else []
            aData['isItinerarios'] = eInscripcionMalla.malla.tiene_itinerarios()
            aData['listItinerarios'] = eInscripcionMalla.malla.lista_itinerarios()
            aData['eInscripcionMalla'] = eInscripcionMalla_serializer.data if eInscripcionMalla_serializer else None
            aData['ePeriodoMatricula'] = ePeriodoMatricula_serializer.data if ePeriodoMatricula_serializer else None
            aData['ePreMatricula'] = ePreMatricula_serializer.data if tienePreMatricula else None
            aData['tienePreMatricula'] = tienePreMatricula
            aData['matriculacionLibre'] = MATRICULACION_LIBRE
            aData['eNivel'] = eNivel_serializer.data if eNivel_serializer else None
            aData['eMalla'] = eMalla_serializer.data if eMalla_serializer else None
            aData['vaUltimaMatricula'] = vaUltimaMatricula = eInscripcion.va_ultima_matricula(ePeriodoMatricula.num_matriculas)
            aData['numVaUltimaMatricula'] = eInscripcion.num_va_ultima_matricula(ePeriodoMatricula.num_matriculas)
            aData['totalMateriasNivel'] = eInscripcion.total_materias_nivel()
            aData['totalMateriasPendientesMalla'] = eInscripcion.total_materias_pendientes_malla()
            # aData['puedeMatricularseOtraVez'] = variable_valor('PUEDE_MATRICULARSE_OTRA_VEZ')
            aData['FichaSocioEconomicaINEC'] = ePersona.fichasocioeconomicainec()
            aData['Title'] = "Matriculación Online"
            aData['val_terc_prec'] = val_terc_prec
            tiene_valores_pendientes = False
            msg_valores_pendientes = ''
            if ePeriodoMatricula.valida_deuda:
                if ePeriodoMatricula.bloquea_por_deuda and not eInscripcion.persona.usuario.is_superuser:
                    if tiene_deudas_vencidas_persona(ePersona, ePeriodoMatricula):
                        raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el proceso de matrícula se encuentra bloqueado por concepto de valores vencidos.")
                else:
                    tiene_valores_pendientes, msg_valores_pendientes = get_deuda_persona(ePersona, ePeriodoMatricula)
            aData['tiene_valores_pendientes'] = tiene_valores_pendientes
            aData['msg_valores_pendientes'] = msg_valores_pendientes
            eCasoUltimaMatricula_serializer = None
            if ePeriodoMatricula.valida_configuracion_ultima_matricula and vaUltimaMatricula:
                if CasoUltimaMatricula.objects.values("id").filter(pk=CASO_ULTIMA_MATRICULA_ID).exists() and CASO_ULTIMA_MATRICULA_ID in ePeriodoMatricula.configuracion_ultima_matricula.casos().values_list("id", flat=True) and eInscripcion.promedio > 75:
                    eCasoUltimaMatricula = CasoUltimaMatricula.objects.get(pk=CASO_ULTIMA_MATRICULA_ID)
                    eCasoUltimaMatricula_serializer = MatriCasoUltimaMatriculaSerializer(eCasoUltimaMatricula)
            aData['eCasoUltimaMatricula'] = eCasoUltimaMatricula_serializer.data if eCasoUltimaMatricula_serializer else None
            # aData['eMateriasAsignadas'] = eMateriaAsignada_serializer.data if eMateriaAsignada_serializer else []
            return Helper_Response(isSuccess=True, data={"tipo": "matricula", "aData": aData}, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)
