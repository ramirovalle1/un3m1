# coding=utf-8
from datetime import datetime
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status

from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.certificado import CertificadoSerializer, CertificadoMatriculaSerializer
from certi.models import CertificadoAsistenteCertificadora, CertificadoUnidadCertificadora, Certificado
from matricula.models import PeriodoMatricula
from sga.models import Noticia, Inscripcion, PerfilUsuario, Matricula, Periodo, Carrera
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache


class CertificadosAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_CERTIFICADO'

    @api_security
    def post(self, request):
        TIEMPO_ENCACHE = 60 * 60
        try:
            hoy = datetime.now()
            payload = request.auth.payload
            ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
            if not ePerfilUsuario.es_estudiante():
                raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
            eInscripcion = ePerfilUsuario.inscripcion
            ePersona = eInscripcion.persona
            eCoordinacion = eInscripcion.carrera.coordinacion_set.all()[0]
            eMatriculas = []
            if eInscripcion.matricula_set.filter(status=True).exists():
                eMatriculas = Matricula.objects.filter(inscripcion_id=eInscripcion.id, status=True).order_by("-nivel__periodo__inicio")
            ePeriodo = None
            if 'id' in payload['periodo']:
                periodoEnCache = cache.get(f"periodo_id_{payload['periodo']['id']}")
                if periodoEnCache:
                    ePeriodo = periodoEnCache
                else:
                    if payload['periodo']['id'] is None:
                        return Helper_Response(isSuccess=False, data={},
                                               message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, para utilizar este módulo debe estar matriculad{'a' if ePersona.es_mujer() else 'o'}",
                                               status=status.HTTP_200_OK, module_access=False)
                    else:
                        if not Periodo.objects.values("id").filter(pk=encrypt(payload['periodo']['id']), status=True).exists():
                            return Helper_Response(isSuccess=False, data={},
                                                   message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, para utilizar este módulo debe estar matriculad{'a' if ePersona.es_mujer() else 'o'}",
                                                   status=status.HTTP_200_OK, module_access=False)
                        ePeriodo = Periodo.objects.get(pk=encrypt(payload['periodo']['id']), status=True)
                    cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)
            # automatricula de pregrado
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

            filter_carreras = CertificadoAsistenteCertificadora.objects.filter(status=True, carrera__in=Carrera.objects.filter(pk=eInscripcion.carrera_id), asistente__firmapersona__tipofirma=2)
            filter_unidades = CertificadoUnidadCertificadora.objects.filter(coordinacion_id=eCoordinacion.id, status=True, pk__in=filter_carreras.values_list('unidad_certificadora_id', flat=True).distinct(), responsable__firmapersona__tipofirma=2)
            certificado_internos_1 = Certificado.objects.filter(status=True, visible=True, tipo_origen=1, destino=1, pk__in=filter_unidades.values_list('certificado_id', flat=True).distinct())
            filter_unidades = CertificadoUnidadCertificadora.objects.filter(coordinacion__isnull=True, status=True, responsable__firmapersona__tipofirma=2)
            certificado_internos_2 = Certificado.objects.filter(status=True, visible=True, tipo_origen=1, destino=1, coordinacion__in=eInscripcion.carrera.coordinacion_set.all(), pk__in=filter_unidades.values_list('certificado_id', flat=True).distinct()).exclude(pk__in=certificado_internos_1.values_list('id', flat=True).distinct())
            certificado_internos = certificado_internos_1 | certificado_internos_2
            filter_unidades = CertificadoUnidadCertificadora.objects.filter(coordinacion__isnull=True, status=True, responsable__firmapersona__tipofirma=2)
            certificado_externos = Certificado.objects.filter(status=True, visible=True, tipo_origen=2, destino=1, coordinacion__in=eInscripcion.carrera.coordinacion_set.all(), pk__in=filter_unidades.values_list('certificado_id', flat=True).distinct())
            eCertificados_internos_serializer = CertificadoSerializer(certificado_internos, many=True)
            eCertificados_externos_serializer = CertificadoSerializer(certificado_externos, many=True)
            eMatriculas_serializer = CertificadoMatriculaSerializer(eMatriculas, many=True)

            data = {
                'internos': eCertificados_internos_serializer.data if certificado_internos.exists() else [],
                'externos': eCertificados_externos_serializer.data if certificado_externos.exists() else [],
                'matriculas': eMatriculas_serializer.data if eMatriculas and eMatriculas.exists() else [],
            }
            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
