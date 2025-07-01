# coding=utf-8
from datetime import datetime
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.idiomas import PeriodoSerializer, GrupoSerializer, GrupoInscripcionSerializer, \
    IdiomaSerializer, GrupoInscripcionAsignaturaSerializer
from idioma.models import Grupo, Periodo, GrupoInscripcion, GrupoInscripcionAsignatura, PeriodoCarrera
from sga.funciones import log
from sga.models import PerfilUsuario, Malla, RecordAcademico, Idioma
from sga.templatetags.sga_extras import encrypt

class IdiomaAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_IDIOMA_KEY'

    @api_security
    def post(self, request):
        hoy = datetime.now().date()
        payload = request.auth.payload
        ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
        if not ePerfilUsuario.es_estudiante():
            raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
        eInscripcion = ePerfilUsuario.inscripcion

        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data
        try:
            if not 'action' in eRequest:
                raise NameError(u'Parametro de acciòn no encontrado')

            action = eRequest['action']

            if action == 'guardar_inscripcion':
                try:
                    ESTADO_SOLICITADO = 0
                    id = int(encrypt(eRequest['id']))
                    eGrupo = Grupo.objects.get(pk=id)
                    if eGrupo.periodo.sinmodulosaprobados:
                        malla_ingles = Malla.objects.get(pk=353)
                        id_asignaturas_ingles=malla_ingles.lista_materias_malla().values_list('asignatura__id',flat = True)
                        aprobo_modulo_de_ingles = RecordAcademico.objects.filter(status=True, inscripcion=eInscripcion, asignatura_id__in=id_asignaturas_ingles, aprobada=True).exists()
                        if aprobo_modulo_de_ingles:
                            raise NameError(u'Ya se encuentra registrada su inscripción')
                    if GrupoInscripcion.objects.values('id').filter(status=True, grupo=eGrupo,inscripcion=eInscripcion).exists():
                        raise NameError(u'No puede inscribirse en este módulo ya que usted ya cuenta con módulos de idiomas aprobados')
                    if not eGrupo.existe_cupo_disponible():
                        raise NameError(u'Lo sentimos, no existe cupos disponibles en este grupo, actualice e intente de nuevo.')
                    eGrupoInscripcion = GrupoInscripcion(grupo=eGrupo, inscripcion = eInscripcion, estado = ESTADO_SOLICITADO)
                    eGrupoInscripcion.save(request)
                    log(u"Adicionó inscripción de inglés: %s" % eGrupoInscripcion, request, "add")
                    aData = {}
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)
            elif action == 'eliminar_inscripcion':
                try:
                    id = int(encrypt(eRequest['id']))
                    if eGrupoInscripcion := GrupoInscripcion.objects.filter(pk=id).first():
                        log(u"Eliminó inscripción de inglés: %s" % eGrupoInscripcion, request, "del")
                        eGrupoInscripcion.delete()
                    else:
                        raise NameError(u'Usted ya no esta inscrito en este grupo.')
                    aData = {}
                    return Helper_Response(isSuccess=True, data=aData, message='Inscripción eliminada correctamente!',  status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)




            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        try:
            if 'action' in request.query_params:
                action = request.query_params['action']
                if action == 'loadGrupos':
                    try:
                        id = int(encrypt(request.query_params['id']))
                        ePeriodo = Periodo.objects.get(pk=id)
                        if ePeriodo.sinmodulosaprobados:
                            payload = request.auth.payload
                            ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
                            if not ePerfilUsuario.es_estudiante():
                                raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                            eInscripcion = ePerfilUsuario.inscripcion
                            malla_ingles = Malla.objects.get(pk=353)
                            id_asignaturas_ingles = malla_ingles.lista_materias_malla().values_list('asignatura__id', flat=True)
                            aprobo_modulo_de_ingles = RecordAcademico.objects.filter(status=True, inscripcion=eInscripcion, asignatura_id__in=id_asignaturas_ingles, aprobada=True).exists()
                            if aprobo_modulo_de_ingles:
                                raise NameError(u'No puede inscribirse en este módulo ya que usted ya cuenta con módulos de idiomas aprobados')
                        # eGrupo= ePeriodo.primer_grupo_disponible()
                        eGrupo= ePeriodo.grupos_disponibles()
                        grupoSerializer = GrupoSerializer(eGrupo, many=True)
                        aData = {
                            'eGrupos': grupoSerializer.data if eGrupo else [],

                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'loadModulosHomologados':
                    try:
                        id = int(encrypt(request.query_params['id']))
                        eGrupoInscripcion = GrupoInscripcion.objects.get(pk = id)
                        eGrupoInscripcion_serializer = GrupoInscripcionSerializer(eGrupoInscripcion)

                        aData = {
                            'eGrupoInscripcion': eGrupoInscripcion_serializer.data if eGrupoInscripcion else [],

                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'loadTablaHomologar':
                    try:
                        id = int(encrypt(request.query_params['id']))
                        eGrupoInscripcion = GrupoInscripcion.objects.get(pk=id)
                        eGrupoInscripcion_serializer = GrupoInscripcionSerializer(eGrupoInscripcion)

                        aData = {
                            'eGrupoInscripcion': eGrupoInscripcion_serializer.data if eGrupoInscripcion else [],

                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            else:
                try:
                    hoy = datetime.now().date()
                    payload = request.auth.payload
                    ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
                    if not ePerfilUsuario.es_estudiante():
                        raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                    inscripcion = ePerfilUsuario.inscripcion
                    periodolectivo = int(encrypt(payload['periodo']['id']))
                    matricula = inscripcion.matricula_set.filter(status=True, nivel__periodo_id=periodolectivo).exclude(retiromatricula=True).first()
                    if not matricula:
                        raise NameError(f'Lo sentimos, no puede inscribirse porque debe estar matriculado en el periodo actual.')
                    nivel_matricula = matricula.nivelmalla_id
                    carrera_id = inscripcion.carrera_id
                    mi_malla = inscripcion.mi_malla()
                    if carrera_id in [7, 138, 129, 90, 157]:
                        raise NameError(u'Lo sentimos, no puedes inscribirte porque ya constan las materias de ingles en tu carrera.')

                    eIdioma = Idioma.objects.filter(status=True)
                    idiomas_serializer = IdiomaSerializer(eIdioma, many=True)
                    eCarreraPeriodo = PeriodoCarrera.objects.filter(status=True, carrera__malla=mi_malla, carrera_id=carrera_id, nivel=nivel_matricula).values_list('periodo_id', flat=True)
                    ePeriodo = Periodo.objects.filter(status=True, estado=True, fecinicioinscripcion__lte=hoy, fecfininscripcion__gte=hoy, id__in=eCarreraPeriodo)
                    periodoSerializer = PeriodoSerializer(ePeriodo, many=True)
                    cursa_modulo_de_ingles = False
                    eGrupoInscripcion = GrupoInscripcion.objects.filter(status=True, inscripcion=inscripcion)
                    gruposInscripcionSerializer = GrupoInscripcionSerializer(eGrupoInscripcion, many=True)
                    data = {
                        'ePeriodo': periodoSerializer.data if ePeriodo else [],
                        'mis_gruposInscripcion': gruposInscripcionSerializer.data if eGrupoInscripcion else [],
                        'idiomas': idiomas_serializer.data if eIdioma else [],
                        'cursa_modulo_de_ingles': cursa_modulo_de_ingles,

                    }
                    return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                   status=status.HTTP_200_OK)