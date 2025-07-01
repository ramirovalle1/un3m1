# coding=utf-8
from _decimal import Decimal
from datetime import datetime
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from django.db import connection, transaction, connections
import json
from inno.models import PeriodoMalla, DetallePeriodoMalla
from matricula.models import PeriodoMatricula
from sga.commonviews import adduserdata, obtener_reporte, actualizar_nota_planificacion
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.materia import MatriculaMateriaAsignadaSerializer, MatriculaSerializer, \
    MatriculaMateriaSerializer, MallaSerializer, PeriodoSerializer, CompaMateriaAsignadaSerializer, \
    InscripcionEncuestaEstudianteSeguimientoSilaboSerializer
from api.serializers.alumno.encuesta import AlumnoGrupoEncuestaSerializer, GrupoEncuestaSerializer
from certi.models import CertificadoAsistenteCertificadora, CertificadoUnidadCertificadora, Certificado
from sga.funciones import null_to_decimal, variable_valor, log
from sga.models import Noticia, Inscripcion, PerfilUsuario, Matricula, MateriaAsignada, InscripcionMalla, AsignaturaMalla, Materia, \
    PeriodoGrupoSocioEconomico, Inscripcion, PerdidaGratuidad, AuditoriaNotas, AgregacionEliminacionMaterias, Silabo, Periodo, EncuestaGrupoEstudiantes, PreguntaEncuestaGrupoEstudiantes, RespuestaPreguntaEncuestaGrupoEstudiantes
from inno.models import InscripcionEncuestaEstudianteSeguimientoSilabo, RespuestaPreguntaEncuestaSilaboGrupoEstudiantes, EncuestaGrupoEstudianteSeguimientoSilabo
from sga.templatetags.sga_extras import encrypt
from django.template import Context
from django.template.loader import get_template
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from settings import DEBUG, NOTA_ESTADO_EN_CURSO
from moodle import moodle


class MateriasAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_MATERIA'

    @api_security
    def post(self, request):
        TIEMPO_ENCACHE = 60 * 15
        try:
            if not 'action' in request.data:
                raise NameError(u'Parametro de acciòn no encontrado')

            action = request.data['action']
            if action == 'listarCompanerios':
                try:
                    if not 'id' in request.data:
                        raise NameError(u'No se encontro parametro de materia asignada.')
                    id = encrypt(request.data['id'])

                    materiaasignada = MateriaAsignada.objects.get(pk=int(id))
                    materiasasignadas = MateriaAsignada.objects.filter(status=False, materia__id=materiaasignada.materia.id).order_by("matricula__inscripcion__persona")

                    matriasig_serializer = CompaMateriaAsignadaSerializer(materiasasignadas, many=True)

                    nombreasig = materiaasignada.materia.nombre_completo()

                    aData = {
                        'companeros': matriasig_serializer.data if materiasasignadas.exists() else [],
                        'nombremateria': nombreasig,

                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'confirmarAutomatriculaMateriaAsignada':
                with transaction.atomic():
                    try:
                        if not 'id' in request.data:
                            raise NameError(u"Parametro no encontrado")
                        if not MateriaAsignada.objects.values("id").filter(pk=encrypt(request.data['id'])).exists():
                            raise NameError(u"Materia no encontrada")
                        eMateriaAsignada = MateriaAsignada.objects.get(pk=encrypt(request.data['id']))
                        if not eMateriaAsignada.automatricula:
                            eMateriaAsignada.automatricula = True
                            eMateriaAsignada.save(request)
                            if variable_valor('ENROLAR_INGLES') and not DEBUG:
                                eMateriaAsignada.materia.crear_actualizar_un_estudiante_curso(moodle, 1, eMateriaAsignada.matricula)
                            log(u'Acepta auto matricula materia asignada: %s' % eMateriaAsignada, request, "edit")
                        aData = {
                            'url' : f'{ eMateriaAsignada.matricula.nivel.periodo.urlmoodle }/course/view.php?id={eMateriaAsignada.materia.idcursomoodle}'
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'actualizar_un_estudiante_moodle':
                with transaction.atomic():
                    try:
                        if not 'id' in request.data:
                            raise NameError(u"Parametro de materia")
                        if not 'idmatri' in request.data:
                            raise NameError(u"Parametro de matricula")
                        id = int(encrypt(request.data['id']))
                        idmatri = int(encrypt(request.data['idmatri']))
                        matricula = Matricula.objects.get(pk=idmatri, status=True)
                        materia = Materia.objects.get(pk=id, status=True)

                        cursoid = materia.idcursomoodle
                        tipourl = 0
                        if materia.coordinacion():
                            if materia.coordinacion().id == 9:
                                cursor = connections['db_moodle_virtual'].cursor()
                                tipourl = 2
                            elif materia.coordinacion().id == 7:
                                cursor = connections['moodle_pos'].cursor()
                                tipourl = 3
                            else:
                                cursor = connections['moodle_db'].cursor()
                                tipourl = 1
                        if tipourl == 0:
                            raise NameError(u"Materia sin coordinación")
                        # cursor = connections['moodle_db'].cursor()
                        queryest = """ SELECT DISTINCT asi.userid, asi.roleid
                                        FROM  mooc_role_assignments asi
                                        INNER JOIN MOOC_CONTEXT CON ON asi.CONTEXTID=CON.ID 
                                        AND ASI.ROLEID=%s AND CON.INSTANCEID=%s AND asi.userid =%s
                                          """ % (materia.nivel.periodo.rolestudiante, cursoid, matricula.inscripcion.persona.idusermoodle)
                        cursor.execute(queryest)
                        rowest = cursor.fetchall()
                        if rowest:
                            raise NameError(u"Ya se encuentra enrolado al cuso de moodle")

                        materia.crear_actualizar_un_estudiante_curso(moodle, tipourl, matricula)
                        log(u'Se enrolo en el curso en moodle : %s - %s [%s]' % (matricula.inscripcion.persona, materia.asignatura.nombre , materia.id), request, "add")

                        aData = {
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'preLoadImportarNotaIngles':
                try:

                    if not 'id' in request.data:
                        raise NameError(u"Parametro no encontrado")
                    if not MateriaAsignada.objects.values("id").filter(pk=encrypt(request.data['id'])).exists():
                        raise NameError(u"Materia no encontrada")
                    eMateriaAsignada = MateriaAsignada.objects.filter(pk=encrypt(request.data['id']))
                    eMateria = eMateriaAsignada.first().materia
                    data = {}
                    data['inscritos'] = eMateriaAsignada
                    data['materia'] = eMateria
                    template = get_template("alu_materias/notasmoodle.html")
                    json_content = template.render(data)
                    aData = {
                        'html': json_content
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'confirmarImportarNotaIngles':
                with transaction.atomic():
                    try:
                        if not 'id' in request.data:
                            raise NameError(u"Parametro no encontrado")
                        if not MateriaAsignada.objects.values("id").filter(pk=encrypt(request.data['id'])).exists():
                            raise NameError(u"Materia no encontrada")
                        eMateriaAsignada = MateriaAsignada.objects.get(pk=encrypt(request.data['id']))
                        eMatricula = eMateriaAsignada.matricula
                        eMateria = eMateriaAsignada.materia
                        if not eMateria.notas_de_moodle(eMatricula.inscripcion.persona):
                            raise NameError(u"Lo sentimos, no se encuentra notas del examen.")
                        for notasmooc in eMateria.notas_de_moodle(eMatricula.inscripcion.persona):
                            campo = eMateriaAsignada.campo(notasmooc[1].upper())
                            if Decimal(notasmooc[0]) <= 0:
                                raise NameError(u"Lo sentimos, no se puede importar notas con cero.")
                            if type(notasmooc[0]) is Decimal:
                                if null_to_decimal(campo.valor) != float(notasmooc[0]) or (eMateriaAsignada.asistenciafinal < campo.detallemodeloevaluativo.modelo.asistenciaaprobar):
                                    actualizar_nota_planificacion(eMateriaAsignada.id, notasmooc[1].upper(), notasmooc[0])
                                    auditorianotas = AuditoriaNotas(evaluaciongenerica=campo,
                                                                    manual=False,
                                                                    calificacion=notasmooc[0])
                                    auditorianotas.save(request)
                            else:
                                if null_to_decimal(campo.valor) != float(0) or (eMateriaAsignada.asistenciafinal < campo.detallemodeloevaluativo.modelo.asistenciaaprobar):
                                    actualizar_nota_planificacion(eMateriaAsignada.id, notasmooc[1].upper(), notasmooc[0])
                                    auditorianotas = AuditoriaNotas(evaluaciongenerica=campo,
                                                                    manual=False,
                                                                    calificacion=0)
                                    auditorianotas.save(request)
                        eMateriaAsignada.importa_nota = True
                        eMateriaAsignada.cerrado = True
                        eMateriaAsignada.fechacierre = datetime.now().date()
                        eMateriaAsignada.save(request, actualiza=False)
                        d = locals()
                        exec(eMateria.modeloevaluativo.logicamodelo, globals(), d)
                        d['calculo_modelo_evaluativo'](eMateriaAsignada)
                        eMateriaAsignada.cierre_materia_asignada()
                        if not eMatricula.inscripcion.modulos_ingles_mi_malla():
                            raise NameError(u"Su malla no tiene módulo configurados, por favor contáctese con su Director de carrera.")
                        auxiliar_cupo = 0
                        modulomalla = eMatricula.inscripcion.ultimo_modulo_ingles_pendiente()
                        if modulomalla:
                            materias = Materia.objects.filter(status=True, nivel_id=658, asignatura=modulomalla.asignatura, inglesepunemi=True).exclude(id__in=[46031, 46032, 46033, 46034, 46035, 46036, 46037, 46038, 46039, 46040])
                            for materia in materias:
                                if materia.tiene_capacidad():
                                    matriculas = 1
                                    materiaasignada = None
                                    matriculas = len(eMatricula.inscripcion.historicorecordacademico_set.filter(asignatura=materia.asignatura, status=True)) + 1
                                    if not MateriaAsignada.objects.values("id").filter(matricula=eMatricula, materia__asignatura=modulomalla.asignatura).exists():
                                        materiaasignada = MateriaAsignada(matricula=eMatricula,
                                                                          materia=materia,
                                                                          notafinal=0,
                                                                          asistenciafinal=100,
                                                                          cerrado=False,
                                                                          matriculas=matriculas,
                                                                          observaciones='',
                                                                          estado_id=NOTA_ESTADO_EN_CURSO,
                                                                          automatricula=False,
                                                                          importa_nota=False,
                                                                          sinasistencia=True)
                                        materiaasignada.save()
                                        materiaasignada.evaluacion()
                                        creditos = materiaasignada.materia.creditos
                                        if materiaasignada.existe_modulo_en_malla():
                                            creditos = materiaasignada.materia_modulo_malla().creditos
                                        registro = AgregacionEliminacionMaterias(matricula=eMatricula,
                                                                                 agregacion=True,
                                                                                 asignatura=materiaasignada.materia.asignatura,
                                                                                 responsable=eMatricula.inscripcion.persona,
                                                                                 fecha=datetime.now().date(),
                                                                                 creditos=creditos,
                                                                                 nivelmalla=materiaasignada.materia.nivel.nivelmalla if materiaasignada.materia.nivel.nivelmalla else None,
                                                                                 matriculas=materiaasignada.matriculas)
                                        registro.save()
                                        if matriculas > 1 or eMatricula.inscripcion.persona.tiene_otro_titulo(eMatricula.inscripcion):
                                            eMatricula.calculo_matricula_ingles(materiaasignada)
                                        auxiliar_cupo = 1
                                        break
                        else:
                            auxiliar_cupo = 1
                        if auxiliar_cupo == 0:
                            raise NameError(u"Lo lamentamos, no hay cupo para el siguiente módulo de inglés: %s" % modulomalla.asignatura)
                        log(u'Importa nota inglés %s' % eMateriaAsignada, request, "edit")
                        eMatricula_serializer = MatriculaSerializer(eMatricula)
                        eMateriasAsignadas = eMatricula.materias().order_by('materia__inicio')
                        eMateriasAsignadas_serializer = MatriculaMateriaAsignadaSerializer(eMateriasAsignadas,  many=True)
                        aData = {
                            'eMatricula': eMatricula_serializer.data,
                            'eMateriasAsignadas': eMateriasAsignadas_serializer.data,
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        ahora = datetime.now()
        fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_cache = fecha_fin - ahora
        TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
        try:
            payload = request.auth.payload
            ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
            if not ePerfilUsuario.es_estudiante():
                raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
            if not 'id' in payload['matricula']:
                raise NameError(u'No se encuentra matriculado.')
            if payload['matricula']['id'] is None:
                raise NameError(u'No se encuentra matriculado.')
            if cache.has_key(f"matricula_id_{payload['matricula']['id']}"):
                eMatricula = cache.get(f"matricula_id_{payload['matricula']['id']}")
            else:
                eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                cache.set(f"matricula_id_{payload['matricula']['id']}", eMatricula, TIEMPO_ENCACHE)
            if cache.has_key(f"data__matricula_id_{payload['matricula']['id']}_serealizer_materias"):
                aData = cache.get(f"data__matricula_id_{payload['matricula']['id']}_serealizer_materias")
                materiasIds = [int(encrypt(l['materia']['id'])) for l in aData['eMateriasAsignadas']]
                eInscripcion = eMatricula.inscripcion
                consulta = InscripcionEncuestaEstudianteSeguimientoSilabo.objects.filter(status=True,
                                                                                         inscripcion=eInscripcion,
                                                                                         materia_id__in=materiasIds)
                eInscripcionencuesta = InscripcionEncuestaEstudianteSeguimientoSilaboSerializer(consulta, many=True)
            else:
                eInscripcion = eMatricula.inscripcion
                ePersona = eInscripcion.persona
                ePeriodo = eMatricula.nivel.periodo
                confirmar_automatricula_pregrado = eInscripcion.tiene_automatriculapregrado_por_confirmar(ePeriodo)
                if confirmar_automatricula_pregrado:
                    mat = eInscripcion.mi_matricula_periodo(ePeriodo.id)
                    if mat.nivel.fechainicioagregacion > datetime.now().date():
                        return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                               message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, se informa que el proceso de aceptación de matrícula empieza {mat.nivel.fechainicioagregacion.__str__()}",
                                               status=status.HTTP_200_OK)
                    if mat.nivel.fechafinagregacion < datetime.now().date():
                        return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                               message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el período de confirmación de la automatrícula ha culminado, usted no se encuentra matriculado",
                                               status=status.HTTP_200_OK)
                    if PeriodoMatricula.objects.values("id").filter(periodo=ePeriodo, status=True).exists():
                        ePeriodoMatricula = PeriodoMatricula.objects.filter(periodo=ePeriodo, status=True)[0]
                        if not ePeriodoMatricula.activo:
                            return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                                   message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, se informa que el proceso de matrícula se encuentra inactivo",
                                                   status=status.HTTP_200_OK)
                    return Helper_Response(isSuccess=False, redirect="alu_matricula", module_access=False,
                                           message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, se informa que el proceso de matrícula se encuentra activo debe aceptar la automatricula",
                                           status=status.HTTP_200_OK)

                # automatricula de admisión
                confirmar_automatricula_admision = eInscripcion.tiene_automatriculaadmision_por_confirmar(ePeriodo)
                if confirmar_automatricula_admision:
                    mat = eInscripcion.mi_matricula_periodo(ePeriodo.id)
                    if mat.nivel.fechainicioagregacion > datetime.now().date():
                        return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                               message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} aspirante, se informa que el proceso de aceptación de matrícula empieza {mat.nivel.fechainicioagregacion.__str__()}",
                                               status=status.HTTP_200_OK)
                    if mat.nivel.fechafinagregacion < datetime.now().date():
                        return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                               message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} aspirante, el período de confirmación de la automatrícula ha culminado, usted no se encuentra matriculado",
                                               status=status.HTTP_200_OK)
                    if PeriodoMatricula.objects.values("id").filter(periodo=ePeriodo, status=True).exists():
                        ePeriodoMatricula = PeriodoMatricula.objects.filter(periodo=ePeriodo, status=True)[0]
                        if not ePeriodoMatricula.activo:
                            return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                                   message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} aspirante, se informa que el proceso de matrícula se encuentra inactivo",
                                                   status=status.HTTP_200_OK)
                    return Helper_Response(isSuccess=False, redirect="alu_matricula", module_access=False,
                                           message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} aspirante, se informa que el proceso de matrícula se encuentra activo debe aceptar la automatricula",
                                           status=status.HTTP_200_OK)
                ePeriodo_serealizer = PeriodoSerializer(ePeriodo)
                eMatricula_serializer = MatriculaSerializer(eMatricula)
                eMateriasAsignadas = eMatricula.materias().order_by('materia__inicio')
                eMateriasAsignadas_serializer = MatriculaMateriaAsignadaSerializer(eMateriasAsignadas, many=True)
                eMalla = eInscripcion.mi_malla()
                eMalla_serializar = MallaSerializer(eMalla)
                es_admision = eInscripcion.mi_coordinacion().id == 9
                es_pregrado = eInscripcion.mi_coordinacion().id in [1,2,3,4,5]
                coordinacion_detalles = eInscripcion.mi_coordinacion().id
                valorGrupo = 0
                graduado = eInscripcion.graduado().values("id").exists()
                consulta =  InscripcionEncuestaEstudianteSeguimientoSilabo.objects.filter(status=True, inscripcion = eInscripcion, materia_id__in = eMateriasAsignadas.values_list('materia_id', flat=True))
                eInscripcionencuesta = InscripcionEncuestaEstudianteSeguimientoSilaboSerializer(consulta, many=True)

                    # if coordinacion_detalles < 6:
                    #     matriculagruposocioeconomico = eMatricula.matriculagruposocioeconomico_set.filter(status=True)
                    #
                    #     if matriculagruposocioeconomico.values("id").exists():
                    #         eGrupoSocioEconomico = matriculagruposocioeconomico[0].gruposocioeconomico
                    #     else:
                    #         eGrupoSocioEconomico = eMatricula.inscripcion.persona.grupoeconomico()

                    # if eMatricula.nivel.periodo.tipocalculo == 1:
                    #     if PeriodoGrupoSocioEconomico.objects.filter(status=True, periodo=eMatricula.nivel.periodo, gruposocioeconomico=eGrupoSocioEconomico).exists():
                    #         ePeriodoGrupoSocioEconomico = PeriodoGrupoSocioEconomico.objects.filter(status=True, periodo=eMatricula.nivel.periodo, gruposocioeconomico=eGrupoSocioEconomico)[0]
                    #         valorGrupo = ePeriodoGrupoSocioEconomico.valor
                    # elif eMatricula.nivel.periodo.tipocalculo in (2, 3, 4, 5):
                    #     malla = eMatricula.inscripcion.mi_malla()
                    #     if malla is None:
                    #         raise NameError(u"Malla sin configurar")
                    #     periodomalla = PeriodoMalla.objects.filter(periodo=eMatricula.nivel.periodo, malla=malla, status=True)
                    #     if not periodomalla.values("id").exists():
                    #         raise NameError(u"Malla no tiene configurado valores de cobro")
                    #     periodomalla = periodomalla[0]
                    #     detalleperiodomalla = DetallePeriodoMalla.objects.filter(periodomalla=periodomalla,
                    #                                                              gruposocioeconomico=eGrupoSocioEconomico,
                    #                                                              status=True)
                    #     if not detalleperiodomalla.values("id").exists():
                    #         raise NameError(u"Malla en grupo socioeconomico no tiene configurado valores de cobro")
                    #     valorGrupo = detalleperiodomalla[0].valor
                    # elif eMatricula.nivel.periodo.tipocalculo == 6:
                    #     pass

                aData = {
                    'eMateriasAsignadas': eMateriasAsignadas_serializer.data if eMateriasAsignadas.exists() else [],
                    'es_graduado': graduado,
                    'eMatricula': eMatricula_serializer.data,
                    'ePeriodo': ePeriodo_serealizer.data,
                    'es_admision': es_admision,
                    'es_pregrado': es_pregrado,
                    'valorGrupo': valorGrupo,
                    'eMalla': eMalla_serializar.data,
                    'coordinacion_detalles': coordinacion_detalles,

                }
                cache.set(f"data__matricula_id_{payload['matricula']['id']}_serealizer_materias", aData, TIEMPO_ENCACHE)
            aData['horassegundos'] = ahora.strftime('%Y%m%d_%H%M%S')
            aData['fecha_actual'] = ahora.date()
            aData['eInscripcionencuesta'] = eInscripcionencuesta.data if consulta.exists() else []
            aData['admision_visualiza_materias'] = variable_valor('ADMISION_VISUALIZA_MATERIAS')
            return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


class EncuestaEstudianteSilaboAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_MATERIA'
    @api_security
    def post(self, request):
        TIEMPO_ENCACHE = 60 * 15
        try:
            if not 'action' in request.data:
                raise NameError(u'Parámetro de acción no encontrado')
            action = request.data['action']

            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                   status=status.HTTP_200_OK)
    @api_security
    def get(self, request):
        TIEMPO_ENCACHE = 60 * 60 * 60
        try:
            action = ''
            if 'action' in request.query_params:
                action = request.query_params['action']

            if action == 'traerEncuesta':
                with transaction.atomic():
                    try:
                        hoy = datetime.now()
                        payload = request.auth.payload
                        eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                        ePeriodo = eMatricula.nivel.periodo
                        eInscripcionEnCache = cache.get(f"inscripcion_id_{payload['inscripcion']['id']}")
                        if eInscripcionEnCache:
                            eInscripcion = eInscripcionEnCache
                        else:
                            if not Inscripcion.objects.db_manager("sga_select").values("id").filter(
                                    pk=encrypt(payload['inscripcion']['id'])).exists():
                                raise NameError(u"Inscripción no válida")
                            eInscripcion = Inscripcion.objects.db_manager("sga_select").get(
                                pk=encrypt(payload['inscripcion']['id']))
                            cache.set(f"inscripcion_id_{payload['inscripcion']['id']}", eInscripcion, TIEMPO_ENCACHE)
                        # ePersona = eInscripcion.persona
                        if 'id' in request.query_params:
                            id = encrypt(request.query_params['id'])
                            idInscripcion = InscripcionEncuestaEstudianteSeguimientoSilabo.objects.values_list('encuesta_id',flat=True).filter(materia_id=id)
                            encuesta = EncuestaGrupoEstudianteSeguimientoSilabo.objects.values_list('fechainicioencuesta',
                                                                                                    'fechafinencuesta').filter(
                                encuestagrupoestudiantes_id__in=idInscripcion, status= True, periodo= ePeriodo)
                            if not (encuesta[0][0] <= hoy.date() and encuesta[0][1] >= hoy.date()):
                                raise NameError(u'La fecha plazo para realizar la encuesta ha finalizado.')
                            eEncuestas_x_contestar = []
                            eEncuestas_x_contetsar_EnCache = cache.get(
                                f"encuesta_silabo_alumnos{encrypt(eInscripcion.id)}{encrypt(id)}") if cache.get(
                                f"encuesta_silabo_alumnos{encrypt(eInscripcion.id)}{encrypt(id)}") else None
                            if not eEncuestas_x_contetsar_EnCache is None:
                                eEncuestas_x_contestar = eEncuestas_x_contetsar_EnCache
                            else:
                                eAlumnoGrupoEncuestas = InscripcionEncuestaEstudianteSeguimientoSilabo.objects.filter(
                                    inscripcion__id=eInscripcion.id, materia_id = id, encuesta__tipoperfil=1, encuesta__activo=True, status=True,
                                    encuesta__encuestagrupoestudianteseguimientosilabo__fechainicioencuesta__lte=hoy.date(),
                                    encuesta__encuestagrupoestudianteseguimientosilabo__fechafinencuesta__gte=hoy.date(),
                                    encuesta__encuestagrupoestudianteseguimientosilabo__periodo=ePeriodo,
                                    encuesta__status=True, respondio=False)
                                if eAlumnoGrupoEncuestas.values("id").exists():
                                    eEncuestaGrupoEstudiantes = EncuestaGrupoEstudiantes.objects.filter(
                                        pk__in=eAlumnoGrupoEncuestas.values_list("encuesta_id", flat=True))
                                    eEncuestas_x_contestar = GrupoEncuestaSerializer(eEncuestaGrupoEstudiantes, many=True).data
                                cache.set(f"encuesta_silabo_alumnos{encrypt(eInscripcion.id)}{encrypt(id)}",
                                          eEncuestas_x_contestar, TIEMPO_ENCACHE)
                            eEncuestas = []
                            eEncuestas_EnCache = cache.get(
                                f"encuesta_silabo_alumnos_contestadas_{encrypt(eInscripcion.id)}{encrypt(id)}")
                            if not eEncuestas_EnCache is None:
                                eEncuestas = eEncuestas_EnCache
                            else:
                                eAlumnoGrupoEncuestas = InscripcionEncuestaEstudianteSeguimientoSilabo.objects.filter(
                                    inscripcion=eInscripcion, materia_id = id, encuesta__tipoperfil=1, encuesta__activo=True, status=True,
                                    encuesta__encuestagrupoestudianteseguimientosilabo__fechainicioencuesta__lte=hoy.date(),
                                    encuesta__encuestagrupoestudianteseguimientosilabo__fechafinencuesta__gte=hoy.date(),
                                    encuesta__encuestagrupoestudianteseguimientosilabo__periodo=ePeriodo,
                                    encuesta__status=True, respondio=True)
                                if eAlumnoGrupoEncuestas.values("id").exists():
                                    eEncuestaGrupoEstudiantes = EncuestaGrupoEstudiantes.objects.filter(
                                        pk__in=eAlumnoGrupoEncuestas.values_list("encuesta_id", flat=True))
                                    eEncuestas = GrupoEncuestaSerializer(eEncuestaGrupoEstudiantes, many=True).data
                                cache.set(f"encuesta_silabo_alumnos_contestadas_{encrypt(eInscripcion.id)}{encrypt(id)}", eEncuestas, TIEMPO_ENCACHE)
                            aData = {
                                'eQuizzes_to_answer': eEncuestas_x_contestar,  # encuestas por contestar
                                'eQuizzes_answered': eEncuestas,  # enucestas contestadas
                            }
                        else:
                            # idInscripcion = InscripcionEncuestaEstudianteSeguimientoSilabo.objects.values_list(
                            #     'encuesta_id', flat=True).filter(inscripcion_id=eInscripcion.id)
                            # encuesta = EncuestaGrupoEstudianteSeguimientoSilabo.objects.values_list(
                            #     'fechainicioencuesta',
                            #     'fechafinencuesta').filter(
                            #     encuestagrupoestudiantes_id__in=idInscripcion)
                            # if not (encuesta[0][0] <= hoy.date() and encuesta[0][1] >= hoy.date()):
                            #     raise NameError(u'La fecha plazo para realizar la encuesta ha finalizado.')
                            eEncuestas_x_contestar = []
                            eEncuestas_x_contetsar_EnCache = cache.get(
                                f"encuesta_silabo_alumnos{encrypt(eInscripcion.id)}") if cache.get(
                                f"encuesta_silabo_alumnos{encrypt(eInscripcion.id)}") else None
                            if not eEncuestas_x_contetsar_EnCache is None:
                                eEncuestas_x_contestar = eEncuestas_x_contetsar_EnCache
                            else:
                                eAlumnoGrupoEncuestas = InscripcionEncuestaEstudianteSeguimientoSilabo.objects.filter(
                                    inscripcion__id=eInscripcion.id, encuesta__tipoperfil=1,
                                    encuesta__activo=True, status=True,
                                    encuesta__encuestagrupoestudianteseguimientosilabo__fechainicioencuesta__lte=hoy.date(),
                                    encuesta__encuestagrupoestudianteseguimientosilabo__periodo=ePeriodo,
                                    encuesta__encuestagrupoestudianteseguimientosilabo__fechafinencuesta__gte=hoy.date(),
                                    encuesta__status=True, respondio=False)
                                if eAlumnoGrupoEncuestas.values("id").exists():
                                    eEncuestaGrupoEstudiantes = EncuestaGrupoEstudiantes.objects.filter(
                                        pk__in=eAlumnoGrupoEncuestas.values_list("encuesta_id", flat=True),status=True, activo = True, encuestagrupoestudianteseguimientosilabo__fechainicioencuesta__lte=hoy.date(),
                                        encuestagrupoestudianteseguimientosilabo__periodo=ePeriodo,
                                        encuestagrupoestudianteseguimientosilabo__fechafinencuesta__gte=hoy.date())
                                    eEncuestas_x_contestar = GrupoEncuestaSerializer(eEncuestaGrupoEstudiantes,
                                                                                     many=True).data
                                cache.set(f"encuesta_silabo_alumnos{encrypt(eInscripcion.id)}",
                                          eEncuestas_x_contestar, TIEMPO_ENCACHE)
                            eEncuestas = []
                            eEncuestas_EnCache = cache.get(
                                f"encuesta_silabo_alumnos_contestadas_{encrypt(eInscripcion.id)}")
                            if not eEncuestas_EnCache is None:
                                eEncuestas = eEncuestas_EnCache
                            else:
                                eAlumnoGrupoEncuestas = InscripcionEncuestaEstudianteSeguimientoSilabo.objects.filter(
                                    inscripcion=eInscripcion, encuesta__tipoperfil=1,
                                    encuesta__activo=True, status=True,
                                    encuesta__encuestagrupoestudianteseguimientosilabo__fechainicioencuesta__lte=hoy.date(),
                                    encuesta__encuestagrupoestudianteseguimientosilabo__periodo=ePeriodo,
                                    encuesta__encuestagrupoestudianteseguimientosilabo__fechafinencuesta__gte=hoy.date(),
                                    encuesta__status=True, respondio=True)
                                if eAlumnoGrupoEncuestas.values("id").exists():
                                    eEncuestaGrupoEstudiantes = EncuestaGrupoEstudiantes.objects.filter(
                                        pk__in=eAlumnoGrupoEncuestas.values_list("encuesta_id", flat=True))
                                    eEncuestas = GrupoEncuestaSerializer(eEncuestaGrupoEstudiantes, many=True).data
                                cache.set(
                                    f"encuesta_silabo_alumnos_contestadas_{encrypt(eInscripcion.id)}",
                                    eEncuestas, TIEMPO_ENCACHE)
                            encuestas_sin_contestar = EncuestaGrupoEstudianteSeguimientoSilabo.objects.values_list('fechainicioencuesta','fechafinencuesta','encuestagrupoestudiantes__activo').filter(
                                encuestagrupoestudiantes__inscripcionencuestaestudianteseguimientosilabo__inscripcion_id=eInscripcion.id, status= True, periodo = ePeriodo).distinct().first()
                            if encuestas_sin_contestar:
                                encuestas_sin_contestar_fecha_desde = encuestas_sin_contestar[0]
                                encuestas_sin_contestar_fecha_hasta = encuestas_sin_contestar[1]
                                encuestas_sin_contestar_activo = encuestas_sin_contestar[2]

                                if (not (encuestas_sin_contestar_fecha_desde <= hoy.date() and encuestas_sin_contestar_fecha_hasta >= hoy.date())) or encuestas_sin_contestar_activo == False:
                                    eEncuestas_x_contestar = []

                            aData = {
                                'eQuizzes_to_answer_sil': eEncuestas_x_contestar,  # encuestas por contestar
                                'eQuizzes_answered_sil': eEncuestas,  # enucestas contestadas
                            }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
            else:
                try:

                    return Helper_Response(isSuccess=True, data='', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

class SaveEncuestaSilaboAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = None

    @api_security
    def post(self, request):

        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data

        TIEMPO_ENCACHE = 60 * 60 * 60
        with transaction.atomic():
            try:
                hoy = datetime.now()
                payload = request.auth.payload
                eInscripcionEnCache = cache.get(f"inscripcion_id_{payload['inscripcion']['id']}")
                eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                ePeriodo = eMatricula.nivel.periodo
                if eInscripcionEnCache:
                    eInscripcion = eInscripcionEnCache
                else:
                    if not Inscripcion.objects.db_manager("sga_select").values("id").filter(pk=encrypt(payload['inscripcion']['id'])).exists():
                        raise NameError(u"Inscripción no válida")
                    eInscripcion = Inscripcion.objects.db_manager("sga_select").get(pk=encrypt(payload['inscripcion']['id']))
                    cache.set(f"inscripcion_id_{payload['inscripcion']['id']}", eInscripcion, TIEMPO_ENCACHE)
                # ePersona = eInscripcion.persona
                if not 'id' in eRequest:
                    raise NameError(u"Parametro de encuesta no encontrado")
                if not 'respuestas' in eRequest:
                    raise NameError(u"Respuestas de encuesta no encontrada")
                if not 'idMateria' in eRequest:
                    raise NameError(u"Falta el identificador de la materia")
                eEncuestaGrupoEstudiantes = EncuestaGrupoEstudiantes.objects.get(pk=encrypt(eRequest['id']))
                idMateria = encrypt(eRequest['idMateria'])
                idInscripcion = InscripcionEncuestaEstudianteSeguimientoSilabo.objects.values_list('encuesta_id',
                                                                                                   flat=True).filter(
                    materia_id=idMateria)
                encuesta = EncuestaGrupoEstudianteSeguimientoSilabo.objects.values_list('fechainicioencuesta',
                                                                                        'fechafinencuesta').filter(
                    encuestagrupoestudiantes_id__in=idInscripcion, status=True, periodo = ePeriodo)
                if not (encuesta[0][0] <= hoy.date() and encuesta[0][1] >= hoy.date()):
                    raise NameError(u'La fecha plazo para realizar la encuesta ha finalizado.')
                if not InscripcionEncuestaEstudianteSeguimientoSilabo.objects.filter(
                    inscripcion_id=eInscripcion.id,
                    materia_id = idMateria,
                    encuesta__tipoperfil=1,
                    encuesta__activo=True,
                    encuesta=eEncuestaGrupoEstudiantes, status=True, respondio=True).exists():
                    eInscripcionEncuestaEstudianteSeguimientoSilabo = InscripcionEncuestaEstudianteSeguimientoSilabo.objects.get(
                        inscripcion_id=eInscripcion.id,
                        materia_id = idMateria,
                        encuesta__tipoperfil=1,
                        encuesta__activo=True,
                        encuesta=eEncuestaGrupoEstudiantes, status=True)
                    eInscripcionEncuestaEstudianteSeguimientoSilabo.respondio = True
                    eInscripcionEncuestaEstudianteSeguimientoSilabo.save(request)
                    respuestas = json.loads(eRequest['respuestas'])
                    for respuesta in respuestas:
                        # print(respuesta)
                        ePreguntaEncuestaGrupoEstudiantes = PreguntaEncuestaGrupoEstudiantes.objects.get(pk=encrypt(respuesta.get('id_pregunta')))
                        if respuesta.get('tipo') == 1:
                            for r in respuesta.get('respuestas'):
                                valor = r.get('valor')
                                if not RespuestaPreguntaEncuestaSilaboGrupoEstudiantes.objects.filter(inscripcionencuestasilabo=eInscripcionEncuestaEstudianteSeguimientoSilabo,
                                                                                                                       pregunta=ePreguntaEncuestaGrupoEstudiantes,
                                                                                                                       respuesta='SI' if valor == 1 else 'NO').exists():
                                    eRespuestaPreguntaEncuestaGrupoEstudiantes = RespuestaPreguntaEncuestaSilaboGrupoEstudiantes(inscripcionencuestasilabo=eInscripcionEncuestaEstudianteSeguimientoSilabo,
                                                                                                                           pregunta=ePreguntaEncuestaGrupoEstudiantes,
                                                                                                                           respuesta='SI' if valor == 1 else 'NO',
                                                                                                                           respuestaporno='' if valor == 1 else r.get('observacion'))
                                    eRespuestaPreguntaEncuestaGrupoEstudiantes.save(request)

                    log(u'Respondio encuesta: %s - %s' % (eEncuestaGrupoEstudiantes, eInscripcionEncuestaEstudianteSeguimientoSilabo), request, "add")

                eEncuestas_x_contestar_EnCache = cache.get(f"encuesta_silabo_alumnos{encrypt(eInscripcion.id)}{encrypt(idMateria)}")
                if eEncuestas_x_contestar_EnCache:
                    cache.delete(f"encuesta_silabo_alumnos{encrypt(eInscripcion.id)}{encrypt(idMateria)}")

                eEncuestas_EnCache = cache.get(f"encuesta_silabo_alumnos_contestadas_{encrypt(eInscripcion.id)}{encrypt(idMateria)}")
                if eEncuestas_EnCache:
                    cache.delete(f"encuesta_silabo_alumnos_contestadas_{encrypt(eInscripcion.id)}{encrypt(idMateria)}")
                eEncuestas_EnCache = cache.get(f"encuesta_silabo_alumnos{encrypt(eInscripcion.id)}")
                if eEncuestas_EnCache:
                    cache.delete(f"encuesta_silabo_alumnos{encrypt(eInscripcion.id)}")
                return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
            except Exception as ex:
                transaction.set_rollback(True)
                return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)