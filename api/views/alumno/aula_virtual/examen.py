# coding=utf-8
import os
import random
import calendar
import uuid
import zipfile
from _decimal import Decimal
from datetime import datetime, timedelta

import pyqrcode
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, ExpressionWrapper, F, DateField
from django.db.models.functions import TruncDate
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status

from inno.models import MateriaAsignadaPlanificacionSedeVirtualExamen, MatriculaSedeExamen, \
    DisertacionMateriaAsignadaPlanificacion
from matricula.models import PeriodoMatricula
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsavesilabo, conviert_html_to_pdfsavepracticas, \
    conviert_html_to_pdf_parametros_save, conviert_html_to_pdfsaveqrcertificado_generico
from django.db import connection, transaction, connections
from sga.commonviews import adduserdata, obtener_reporte, actualizar_nota_planificacion
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.aulavirtual import MatriculaMateriaAsignadaSerializer, MatriculaSerializer, \
    MatriculaMateriaSerializer, MallaSerializer, PeriodoSerializer, \
    CompaMateriaAsignadaSerializer, LibroKohaProgramaAnaliticoAsignaturaSerializer, Silabo_2_Serializar, \
    GPGuiaPracticaSemanal_Serializar, AvComunicacionSerializer, AvPreguntaDocenteSerializer, \
    TestSilaboSemanalSerializer, TareaSilaboSemanalSerializer, ForoSilaboSemanalSerializer, \
    TareaPracticaSilaboSemanalSerializer, HorarioExamenDetalleAlumnoSerializer, PlanificacionSedeSerializer, \
    AuxMatriculaMateriaAsignadaSerializer, MatriculaSedeExamenSerializer, \
    DisertacionMateriaAsignadaPlanificacionSerializer
from certi.models import CertificadoAsistenteCertificadora, CertificadoUnidadCertificadora, Certificado
from sga.funciones import null_to_decimal, variable_valor, log, remover_caracteres_tildes_unicode, remover_caracteres_especiales_unicode
from sga.models import Noticia, Inscripcion, PerfilUsuario, Matricula, MateriaAsignada, InscripcionMalla, \
    AsignaturaMalla, Materia, PeriodoGrupoSocioEconomico, Inscripcion, PerdidaGratuidad, AuditoriaNotas, \
    AgregacionEliminacionMaterias, Silabo, Periodo, DetalleSilaboSemanalBibliografiaDocente, \
    LibroKohaProgramaAnaliticoAsignatura, GPGuiaPracticaSemanal, Persona, AvComunicacion, AvPreguntaDocente, \
    TestSilaboSemanal, TareaSilaboSemanal, ForoSilaboSemanal, TareaPracticaSilaboSemanal, HorarioExamen, SesionZoom, \
    DetalleSesionZoom, HorarioExamenDetalleAlumno, DiapositivaSilaboSemanal, CompendioSilaboSemanal, GuiaEstudianteSilaboSemanal, MatriculaTerminoCondicionExamen
from sga.templatetags.sga_extras import encrypt
from django.template import Context
from django.template.loader import get_template
from settings import DEBUG, NOTA_ESTADO_EN_CURSO, USA_PLANIFICACION, SITE_STORAGE
from moodle import moodle
from django.shortcuts import render, redirect
from api.helpers.functions_helper import get_variable, generate_acuerdo_terminos_examen_final, generate_qr_examen_final, \
    generate_qr_examen_final2
from sga.commonviews import get_client_ip
from django.core.cache import cache


class ExamenAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_AULA_VIRTUAL'

    @api_security
    def post(self, request):
        ahora = datetime.now()
        fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_cache = fecha_fin - ahora
        tiempo_cache = int(tiempo_cache.total_seconds())
        try:

            payload = request.auth.payload
            action = request.data.get('action', None)
            if not action:
                raise NameError(u'Acción no permitida')

            # if action == 'acceptTerminosCondicionesExamen':
            #     with transaction.atomic():
            #         try:
            #             payload = request.auth.payload
            #             if cache.has_key(f"matricula_id_{payload['matricula']['id']}"):
            #                 eMatricula = cache.get(f"matricula_id_{payload['matricula']['id']}")
            #             else:
            #                 eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
            #                 cache.set(f"matricula_id_{payload['matricula']['id']}", eMatricula, tiempo_cache)
            #             # eMatriculaTerminoCondicionExamen = MatriculaTerminoCondicionExamen(matricula=eMatricula, termino_condicion=True)
            #             # eMatriculaTerminoCondicionExamen.save(request)
            #             return Helper_Response(isSuccess=True, data={'msg': 'Exito en tu semana exámenes'}, status=status.HTTP_200_OK)
            #         except Exception as ex:
            #             transaction.set_rollback(True)
            #             return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'loadPlanificacionSedeExamen':
                try:
                    if not 'id' in request.data:
                        raise NameError(u'No se encontro parametro de materia asignada.')
                    id = encrypt(request.data['id'])
                    eMateriaAsignada = MateriaAsignada.objects.get(pk=id)
                    ePlanificacionSede = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(materiaasignada=eMateriaAsignada, status=True)
                    planificacionsede = PlanificacionSedeSerializer(ePlanificacionSede, many=True).data if ePlanificacionSede.values("id").exists() else []
                    vacio = False
                    if ePlanificacionSede:
                        vacio = True
                    return Helper_Response(isSuccess=True, data={'planificacionsede': planificacionsede, 'vacio': vacio}, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadPlanificacionDisertacion':
                try:
                    if not 'id' in request.data:
                        raise NameError(u'No se encontro parametro de materia asignada.')
                    id = encrypt(request.data['id'])
                    eMateriaAsignada = MateriaAsignada.objects.get(pk=id)
                    eDisertaciones = DisertacionMateriaAsignadaPlanificacion.objects.filter(materiaasignada=eMateriaAsignada, status=True)
                    disertaciones = DisertacionMateriaAsignadaPlanificacionSerializer(eDisertaciones, many=True).data if eDisertaciones.values("id").exists() else []
                    vacio = False
                    if eDisertaciones:
                        vacio = True
                    return Helper_Response(isSuccess=True, data={'disertaciones': disertaciones, 'vacio': vacio}, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadMateriaAsignadaHorarioExamen':
                try:
                    if not 'id' in request.data:
                        raise NameError(u'No se encontro parametro de materia asignada.')
                    id = encrypt(request.data['id'])
                    eMateriaAsignada = MateriaAsignada.objects.get(pk=id)
                    fecha_actual = datetime.now().date()
                    eHorarioExamenDetalleAlumnos = HorarioExamenDetalleAlumno.objects.filter(materiaasignada=eMateriaAsignada, status=True)
                    #Horario de examen aparecerán hasta 5 dias despues de la fecha del examen
                    # eHorarioExamenDetalleAlumnos = eHorarioExamenDetalleAlumnos.annotate(fecha_aumentada=ExpressionWrapper(
                    #         TruncDate(F('horarioexamendetalle__horarioexamen__fecha')) + timedelta(days=5),
                    #         output_field=DateField()
                    #     )).filter(fecha_aumentada__gte=fecha_actual)

                    horarioexamendetallealumno = HorarioExamenDetalleAlumnoSerializer(eHorarioExamenDetalleAlumnos, many=True).data if eHorarioExamenDetalleAlumnos.values("id").exists() else []
                    vacio = False
                    if eHorarioExamenDetalleAlumnos:
                        vacio = True
                    return Helper_Response(isSuccess=True, data={'horarioexamendetallealumno': horarioexamendetallealumno, 'vacio': vacio}, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'createAcceptTerminosCondicionesExamen':
                with transaction.atomic():
                    try:
                        if cache.has_key(f"matricula_id_{payload['matricula']['id']}"):
                            eMatricula = cache.get(f"matricula_id_{payload['matricula']['id']}")
                        else:
                            eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                            cache.set(f"matricula_id_{payload['matricula']['id']}", eMatricula, tiempo_cache)
                        try:
                            eMatriculaSedeExamen = MatriculaSedeExamen.objects.get(matricula_id=eMatricula.id)
                        except ObjectDoesNotExist:
                            raise NameError(u'No permite crear borrador')
                        isDemo = request.data.get('isDemo', False)
                        result = generate_acuerdo_terminos_examen_final(eMatriculaSedeExamen, isDemo)
                        isSuccess = result.get('isSuccess', False)
                        if not isSuccess:
                            message = result.get('message', 'Error al generar documento')
                            raise NameError(message)
                        aDataAcuerdo = result.get('data', {})
                        url_pdf_acuerdo = aDataAcuerdo.get('url_pdf', '')
                        url_png_acuerdo = aDataAcuerdo.get('url_png', '')
                        if url_png_acuerdo == '' or url_pdf_acuerdo == '':
                            raise NameError(u"No se encontro url del documento")
                        if isDemo is False:
                            eMatriculaSedeExamen.aceptotermino = True
                            eMatriculaSedeExamen.fechaaceptotermino = datetime.now()
                            eMatriculaSedeExamen.urltermino = url_pdf_acuerdo
                            eMatriculaSedeExamen.save(request)
                            eMateriaAsignadaPlanificacionSedeVirtualExamenes = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(materiaasignada__matricula=eMatricula, status=True, utilizar_qr=True)
                            for eMateriaAsignadaPlanificacionSedeVirtualExamen in eMateriaAsignadaPlanificacionSedeVirtualExamenes:
                                result = generate_qr_examen_final(eMateriaAsignadaPlanificacionSedeVirtualExamen, materiaasignada_id=eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada_id)
                                isSuccess = result.get('isSuccess', False)
                                if not isSuccess:
                                    message = result.get('message', 'Error al generar documento')
                                    raise NameError(message)
                                aDataExamen = result.get('data', {})
                                url_pdf_examen = aDataExamen.get('url_pdf', '')
                                codigo_qr_examen = aDataExamen.get('codigo_qr', '')
                                if url_pdf_examen == '' and codigo_qr_examen == '':
                                    raise NameError(u"No se encontro url del documento")
                                eMateriaAsignadaPlanificacionSedeVirtualExamen.fecha_qr = datetime.now()
                                eMateriaAsignadaPlanificacionSedeVirtualExamen.url_qr = f"/media/{url_pdf_examen}"
                                eMateriaAsignadaPlanificacionSedeVirtualExamen.codigo_qr = codigo_qr_examen
                                eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request)
                            log(u'Acepto terminos y condiciones :%s ' % eMatriculaSedeExamen, request, "add")
                        link_pdf = f"{get_variable('SITE_URL_SGA')}{url_pdf_acuerdo}"
                        return Helper_Response(isSuccess=True, data={'url_pdf': link_pdf}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'generateCodigoQRMateriaAsignadaHorarioExamen':
                with transaction.atomic():
                    try:
                        if cache.has_key(f"matricula_id_{payload['matricula']['id']}"):
                            eMatricula = cache.get(f"matricula_id_{payload['matricula']['id']}")
                        else:
                            eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                            cache.set(f"matricula_id_{payload['matricula']['id']}", eMatricula, tiempo_cache)
                        try:
                            eMatriculaSedeExamen = MatriculaSedeExamen.objects.get(matricula_id=eMatricula.id)
                        except ObjectDoesNotExist:
                            raise NameError(u'No permite crear borrador')
                        if eMatriculaSedeExamen.aceptotermino is False:
                            raise NameError(u'No puede generar código QR porque no ha aceptado terminos y condiciones')
                        id = int(encrypt(request.data.get('id', encrypt('0'))))
                        try:
                            eMateriaAsignadaPlanificacionSedeVirtualExamen = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.get(id=id)
                        except ObjectDoesNotExist:
                            raise NameError(u'No se encontro materia')
                        result = generate_qr_examen_final(eMateriaAsignadaPlanificacionSedeVirtualExamen, materiaasignada_id=eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada_id)
                        isSuccess = result.get('isSuccess', False)
                        if not isSuccess:
                            message = result.get('message', 'Error al generar documento')
                            raise NameError(message)
                        aData = result.get('data', {})
                        url_pdf = aData.get('url_pdf', '')
                        codigo_qr = aData.get('codigo_qr', '')
                        if url_pdf == '' and codigo_qr == '':
                            raise NameError(u"No se encontro url del documento")
                        link_pdf = f"{get_variable('SITE_URL_SGA')}/media/{url_pdf}"
                        eMateriaAsignadaPlanificacionSedeVirtualExamen.fecha_qr = datetime.now()
                        eMateriaAsignadaPlanificacionSedeVirtualExamen.url_qr = f"/media/{url_pdf}"
                        eMateriaAsignadaPlanificacionSedeVirtualExamen.codigo_qr = codigo_qr
                        eMateriaAsignadaPlanificacionSedeVirtualExamen.save(request)
                        return Helper_Response(isSuccess=True, message="Se genero correctamente el código QR", data={'url_pdf': link_pdf}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'registreDisertacionMateriaAsignada':
                with transaction.atomic():
                    try:
                        id = int(encrypt(request.data.get('id', encrypt('0'))))
                        try:
                            eDisertacionMateriaAsignadaPlanificacion = DisertacionMateriaAsignadaPlanificacion.objects.get(pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u'No se encontro planificación')
                        eDisertacionMateriaAsignadaPlanificacion.asistencia = True
                        eDisertacionMateriaAsignadaPlanificacion.fecha_asistencia = datetime.now()
                        eDisertacionMateriaAsignadaPlanificacion.save(request)
                        link = None
                        if (eProfesor := eDisertacionMateriaAsignadaPlanificacion.grupoplanificacion.responsable.profesor()) is not None:
                            link = eProfesor.urlzoom if eProfesor.urlzoom else None
                        return Helper_Response(isSuccess=True, message="Se registro asistencia correctamente", data={'link_meet': link}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        try:
            ahora = datetime.now()
            fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
            tiempo_cache = fecha_fin - ahora
            tiempo_cache = int(tiempo_cache.total_seconds())
            payload = request.auth.payload
            if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
                ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
            else:
                ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
                cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario, tiempo_cache)
            if not ePerfilUsuario.es_estudiante():
                raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
            id_matricula = payload['matricula'].get('id', encrypt(0))
            if id_matricula == 0:
                raise NameError(u'No se encuentra matriculado.')
            if cache.has_key(f"matricula_id_{id_matricula}"):
                eMatricula = cache.get(f"matricula_id_{id_matricula}")
            else:
                try:
                    eMatricula = Matricula.objects.db_manager("sga_select").get(pk=int(encrypt(id_matricula)))
                    cache.set(f"matricula_id_{id_matricula}", eMatricula, tiempo_cache)
                except ObjectDoesNotExist:
                    eMatricula = None
            eInscripcion = eMatricula.inscripcion
            # ePersona = eInscripcion.persona
            ePeriodo = eMatricula.nivel.periodo
            if cache.has_key(f"periodo_id_{encrypt(ePeriodo.id)}_serealizer"):
                ePeriodo_serealizer = cache.get(f"periodo_id_{encrypt(ePeriodo.id)}_serealizer")
            else:
                ePeriodo_serealizer = PeriodoSerializer(ePeriodo).data
                cache.set(f"periodo_id_{encrypt(ePeriodo.id)}_serealizer", ePeriodo_serealizer, tiempo_cache)

            if cache.has_key(f"matricula_id_{encrypt(eMatricula.id)}_serealizer_aulavirtual"):
                eMatricula_serializer = cache.get(f"matricula_id_{encrypt(eMatricula.id)}_serealizer_aulavirtual")
            else:
                eMatricula_serializer = MatriculaSerializer(eMatricula).data
                cache.set(f"matricula_id_{encrypt(eMatricula.id)}_serealizer_aulavirtual", eMatricula_serializer, tiempo_cache)

            eMalla = eInscripcion.mi_malla()
            if cache.has_key(f"malla__inscripcion_id_{encrypt(eInscripcion.id)}_serealizer_aulavirtual"):
                eMalla_serializar = cache.get(f"malla__inscripcion_id_{encrypt(eInscripcion.id)}_serealizer_aulavirtual")
            else:
                eMalla_serializar = MallaSerializer(eMalla).data
                cache.set(f"malla__inscripcion_id_{encrypt(eInscripcion.id)}_serealizer_aulavirtual", eMalla_serializar, tiempo_cache)

            eMateriasAsignadas = eMatricula.materiaasignada_set.filter(status=True, retiramateria=False).exclude(Q(materia__inglesepunemi=True)).order_by('materia__inicio')
            eMateriasAsignadas = AuxMatriculaMateriaAsignadaSerializer(eMateriasAsignadas, many=True).data if eMateriasAsignadas.values("id").exists() else []
            # tiene_termino_condicion_examen = eMatricula.matriculaterminocondicionexamen_set.values('id').filter(status=True, termino_condicion=True).exists()
            # mostrar_terminos_examenes = eMatricula.nivel.periodo.periodomatricula_set.values('id').filter(status=True, mostrar_terminos_examenes=True).exists()
            # termino_condicion_examen = ''
            # if (termino := eMatricula.nivel.periodo.periodomatricula_set.filter(status=True).only('terminos_examenes').first()) is not None:
            #     termino_condicion_examen = termino.terminos_examenes
            es_admision = eInscripcion.es_admision()
            es_pregrado = eInscripcion.es_pregrado()
            data = {
                'eMateriasAsignadas': eMateriasAsignadas,
                'ePeriodo': ePeriodo_serealizer,
                'eMatricula': eMatricula_serializer,
                'es_admision': es_admision,
                'es_pregrado': es_pregrado,
                'eMalla': eMalla_serializar,
                # 'tiene_termino_condicion_examen': tiene_termino_condicion_examen,
                # 'mostrar_terminos_examenes': mostrar_terminos_examenes,
                # 'termino_condicion_examen': termino_condicion_examen
            }
            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
