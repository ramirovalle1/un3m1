# coding=utf-8
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from django.db import transaction
from operator import itemgetter
from django.contrib.contenttypes.fields import ContentType, GenericForeignKey
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.functions_helper import get_variable
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.certificado import CertificadoSerializer, CertificadoMatriculaSerializer
from api.serializers.alumno.secretary import AsignaturaMallaSerializer, SolicitudSerializer, CarreraSerializer
from certi.models import Certificado, CertificadoAsistenteCertificadora, CertificadoUnidadCertificadora
from secretaria.models import Servicio, CategoriaServicio, SolicitudAsignatura, Solicitud
from sga.models import PerfilUsuario, Carrera, Matricula, Graduado, MateriaAsignada, InscripcionMalla, AsignaturaMalla, RecordAcademico
from sga.templatetags.sga_extras import encrypt, traducir_mes
from secretaria.models import Solicitud
from posgrado.models import ProductoSecretaria, InscripcionCohorte, VentasProgramaMaestria
from sga.funciones import variable_valor

class ProductAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_SECRETARY'

    @api_security
    def post(self, request):
        TIEMPO_ENCACHE = 60 * 15
        try:
            if not 'action' in request.data:
                raise NameError(u'Parametro de acciòn no encontrado')

            action = request.data['action']

            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        data = {}
        try:
            action = ''
            if 'action' in request.query_params:
                action = request.query_params['action']

            if action == 'listaasignaturas':
                try:
                    payload = request.auth.payload
                    ePerfilUsuario = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                    eInscripcionMalla = InscripcionMalla.objects.get(status=True, inscripcion=ePerfilUsuario.inscripcion)
                    eAsignaturas = AsignaturaMalla.objects.filter(status=True, malla=eInscripcionMalla.malla)
                    postulante = InscripcionCohorte.objects.get(status=True, inscripcion=ePerfilUsuario.inscripcion)

                    eProducto = ProductoSecretaria.objects.get(pk=2)
                    eServicio = eProducto.servicio
                    eContentTypeProducto = ContentType.objects.get_for_model(eProducto)

                    # asignaturas_serializer = AsignaturaMallaSerializer(eAsignaturas, many=True)
                    eSolicitud = None
                    eSolicitudes = Solicitud.objects.filter(status=True, perfil_id=ePerfilUsuario.pk, servicio_id=eServicio.pk,
                                                            origen_content_type_id=eContentTypeProducto.pk,
                                                            inscripcioncohorte=postulante,
                                                            origen_object_id=eProducto.id)
                    serializer = SolicitudSerializer(eSolicitudes, many=True)
                    nombre = ''
                    homologada = '0'
                    estado = 'No solicitado'
                    horasacdtotal = horasapetotal = horasautonomas = horas = creditos = 0
                    eAsignaturamalla = []
                    asigho = None
                    for eAsignatura in eAsignaturas:
                        color = '0'
                        nota = 0
                        if eSolicitudes.values("id").exists():
                            eSolicitud = eSolicitudes.first()
                            homologada = asignatura_seleccionada(eSolicitud, eAsignatura)
                            estado = estado_asignatura(eSolicitud, eAsignatura)
                            asigho = asignatura_ho(eSolicitud, eAsignatura)
                            nota = eSolicitud.solicitud_asignatura_record(eAsignatura).nota if eSolicitud.solicitud_asignatura_record(eAsignatura) is not None else 0
                            if asigho:
                                color = asignatura_ho(eSolicitud, eAsignatura).color_estado_display()

                        nombre = eAsignatura.asignatura.nombre
                        horasacdtotal = eAsignatura.horasacdtotal
                        horasapetotal = eAsignatura.horasapetotal
                        horasautonomas = eAsignatura.horasautonomas
                        horas = eAsignatura.horas
                        creditos = eAsignatura.creditos

                        eAsignaturamalla.append({
                            "pk": eAsignatura.id,
                            "nombre": nombre,
                            "horasacdtotal": horasacdtotal,
                            "horasapetotal": horasapetotal,
                            "horasautonomas": horasautonomas,
                            "horas": horas,
                            "creditos": creditos,
                            "homologada": homologada,
                            "estado": estado,
                            "color": color,
                            "nota": nota if nota is not None else 0
                        })
                    serializeruno = SolicitudSerializer(eSolicitud)
                    
                    serializercarrera = CarreraSerializer(ePerfilUsuario.inscripcion.carrera)
                    aData = {
                        'eAsignaturas': eAsignaturamalla,
                        'eSolicitudes': serializer.data if eSolicitudes.values("id").exists() else [],
                        'eSolicitudAct': serializeruno.data if eSolicitud is not None else None,
                        'eCarreraPos': serializercarrera.data if ePerfilUsuario.inscripcion.carrera is not None else None
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
            else:
                payload = request.auth.payload
                ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
                if not ePerfilUsuario.es_estudiante():
                    raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                if not 'id' in request.query_params:
                    raise NameError(u"Servicio no encontrado")
                id = int(encrypt(request.query_params.get('id', '')))
                eServicios = Servicio.objects.filter(pk=id)
                if not eServicios.values("id").exists():
                    raise NameError(u"Servicio no encontrado")
                eServicio = eServicios.first()
                if eServicio.proceso in [1, 2, 8, 10]:
                    result = list_certificate_products(ePerfilUsuario, eServicio)
                    if not result['isSuccess']:
                        raise NameError(result['message'])
                    data = result['data']
                elif eServicio.proceso in [7, 9]:
                    result = list_degree_products(ePerfilUsuario, eServicio)
                    if not result['isSuccess']:
                        raise NameError(result['message'])
                    data = result['data']
                return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data=data, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


def list_certificate_products(ePerfilUsuario, eServicio):
    try:
        if not ePerfilUsuario.es_estudiante():
            raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
        eInscripcion = ePerfilUsuario.inscripcion
        tmculmi = eInscripcion.tiene_malla_culminada_posgrado()
        # ePersona = eInscripcion.persona
        eCoordinacion = eInscripcion.carrera.coordinacion_set.all()[0]
        eMatriculas = Matricula.objects.filter(inscripcion=eInscripcion, status=True).order_by("-nivel__periodo__inicio")
        if eServicio.proceso == 1:
            """ CERTIFICADOS INTERNOS """
            filter_carreras = CertificadoAsistenteCertificadora.objects.filter(status=True, carrera__in=Carrera.objects.filter(pk=eInscripcion.carrera_id), asistente__firmapersona__tipofirma=2)
            filter_unidades = CertificadoUnidadCertificadora.objects.filter(coordinacion_id=eCoordinacion.id, status=True, pk__in=filter_carreras.values_list('unidad_certificadora_id', flat=True).distinct(), responsable__firmapersona__tipofirma=2)
            certificado_internos_1 = Certificado.objects.filter(servicio=eServicio, status=True, visible=True, tipo_origen=1, destino=1, pk__in=filter_unidades.values_list('certificado_id', flat=True).distinct())
            filter_unidades = CertificadoUnidadCertificadora.objects.filter(coordinacion__isnull=True, status=True, responsable__firmapersona__tipofirma=2)
            certificado_internos_2 = Certificado.objects.filter(servicio=eServicio, status=True, visible=True, tipo_origen=1, destino=1, coordinacion__in=eInscripcion.carrera.coordinacion_set.all(), pk__in=filter_unidades.values_list('certificado_id', flat=True).distinct()).exclude(pk__in=certificado_internos_1.values_list('id', flat=True).distinct())
            eCertificados = certificado_internos_1 | certificado_internos_2
            eCertificados = eCertificados.distinct()
        elif eServicio.proceso == 2:
            """ CERTIFICADOS EXTERNOS """
            filter_unidades = CertificadoUnidadCertificadora.objects.filter(coordinacion__isnull=True, status=True, responsable__firmapersona__tipofirma=2)
            eCertificadosEx = Certificado.objects.filter(servicio=eServicio, status=True, visible=True, tipo_origen=2, destino=1, coordinacion__in=eInscripcion.carrera.coordinacion_set.all(), pk__in=filter_unidades.values_list('certificado_id', flat=True).distinct()).exclude(id=61)
            # certificados_externo = Certificado.objects.filter(servicio=eServicio, status=True, visible=True, tipo_origen=2, destino=1, pk__in=filter_unidades.values_list('certificado_id', flat=True).distinct())
            # eCertificados = certificados_externo | eCertificadosEx
            eCertificados = eCertificadosEx
        elif eServicio.proceso == 8:
            """ CERTIFICADOS FÍSICOS """
            # filter_unidades = CertificadoUnidadCertificadora.objects.filter(coordinacion__isnull=True, status=True, responsable__firmapersona__tipofirma=2)
            eCertificadosFi = Certificado.objects.filter(servicio=eServicio, status=True, visible=True, tipo_origen=3, destino=1, coordinacion__in=eInscripcion.carrera.coordinacion_set.all())
            # certificados_externo = Certificado.objects.filter(servicio=eServicio, status=True, visible=True, tipo_origen=2, destino=1, pk__in=filter_unidades.values_list('certificado_id', flat=True).distinct())
            eCertificados = eCertificadosFi
        elif eServicio.proceso == 10:
            """ CERTIFICADOS RÚBRICA """
            # filter_unidades = CertificadoUnidadCertificadora.objects.filter(coordinacion__isnull=True, status=True, responsable__firmapersona__tipofirma=2)
            eCertificadosRu = Certificado.objects.filter(servicio=eServicio, status=True, visible=True, tipo_origen=4, destino=1, coordinacion__in=eInscripcion.carrera.coordinacion_set.all())
            # certificados_externo = Certificado.objects.filter(servicio=eServicio, status=True, visible=True, tipo_origen=2, destino=1, pk__in=filter_unidades.values_list('certificado_id', flat=True).distinct())
            eCertificados = eCertificadosRu
        else:
            eCertificados = Certificado.objects.none()
        eProducts = []
        base_url = get_variable('SITE_URL_SGA')
        for eCertificado in eCertificados:
            cost = 0
            if eCertificado.costo > 0:
                if eCoordinacion.id != 7:
                    if not eInscripcion.graduado():
                        if not eInscripcion.egresado():
                            if eInscripcion.estado_gratuidad != 3:
                                cost = (Decimal(0).quantize(Decimal('.01'))).__float__()
                            else:
                                cost = (Decimal(eCertificado.costo).quantize(Decimal('.01')) if eCertificado.costo else Decimal(0).quantize(Decimal('.01'))).__float__()
                        else:
                            cost = (Decimal(eCertificado.costo).quantize(Decimal('.01')) if eCertificado.costo else Decimal(0).quantize(Decimal('.01'))).__float__()
                    else:
                        cost = (Decimal(eCertificado.costo).quantize(Decimal('.01')) if eCertificado.costo else Decimal(0).quantize(Decimal('.01'))).__float__()
                else:
                    # if eMatriculas:
                    if eCertificado.servicio.proceso == 8:
                        cost = (Decimal(eCertificado.costo).quantize(Decimal('.01')) if eCertificado.costo else Decimal(0).quantize(Decimal('.01'))).__float__()
                    else:
                        if eInscripcion.tiene_malla_culminada_posgrado() == '1' and not eInscripcion.es_graduado():
                            cost = (Decimal(0).quantize(Decimal('.01'))).__float__()
                        else:
                            cost = (Decimal(eCertificado.costo).quantize(Decimal('.01')) if eCertificado.costo else Decimal(0).quantize(Decimal('.01'))).__float__()
                    # else:
                    #     cost = (Decimal(eCertificado.costo).quantize(Decimal('.01')) if eCertificado.costo else Decimal(0).quantize(Decimal('.01'))).__float__()
            eContentType = ContentType.objects.get_for_model(eCertificado)
            eProducts.append({
                "id": encrypt(eCertificado.pk),
                "idm": encrypt(eContentType.pk),
                "ids": encrypt(eServicio.pk),
                "imagen": f"{base_url}/static/bootstrap5/images/placeholder/placeholder-4by3.svg",
                "name": f"{eCertificado.codigo} - {eCertificado.certificacion}",
                "certification_type": eCertificado.tipo_certificacion,
                "description": f"El certificado {eCertificado.get_tipo_origen_display().lower()} {eCertificado.codigo}",
                "detail": f"La emisión del certificado {eCertificado.get_tipo_origen_display().lower() if eCertificado.id != 55 else 'personalizado'} {eCertificado.codigo}, tiene un costo de {Decimal(eServicio.costo).quantize(Decimal('.01')) if eServicio else Decimal(0).quantize(Decimal('.01'))} USD.",
                "cost": cost,
                "reqmallaculminada": eCertificado.mallaculminada,
                "proceso": eCertificado.servicio.proceso,
                "idsinencryptar": eCertificado.pk,
                #"cost": (Decimal(eCertificado.costo).quantize(Decimal('.01')) if eCertificado.costo else Decimal(0).quantize(Decimal('.01'))).__float__(),
                "validity": {
                    "display": eCertificado.tiempo_vigencia(),
                    "time": eCertificado.vigencia,
                    "type": eCertificado.tipo_vigencia
                },
                "report": {
                    "id": eCertificado.reporte.id,
                    "name": eCertificado.reporte.nombre,
                    "version": eCertificado.reporte.version,
                    "types": eCertificado.reporte.tiporeporte(),
                }
            })
        data = {
            'eProductos': eProducts,
            'extras': {
                        'eMatriculas': CertificadoMatriculaSerializer(eMatriculas, many=True).data if eMatriculas.values("id").exists() else []
            },
            'eMallaCulminada': tmculmi,
            'eCoordinacion_id': eCoordinacion.id
        }
        return {'isSuccess': True, 'message': '', 'data': data}
    except Exception as ex:
        return {'isSuccess': False, 'message': ex.__str__(), 'data': {}}

def apto_para_homologacion(inscripcion):
    fechaactual = datetime.now().date()
    apto = '0'
    eMateriaAsi = None
    eMatricula = Matricula.objects.filter(status=True, inscripcion=inscripcion, retiradomatricula=False).order_by('-id').first()
    ePostulante = InscripcionCohorte.objects.filter(status=True, inscripcion=inscripcion).order_by('-id').first()
    if Graduado.objects.filter(status=True, inscripcion=inscripcion).exists():
        apto = '1'
    elif not RecordAcademico.objects.filter(status=True, inscripcion__carrera__coordinacion__id=7,
                                          inscripcion__persona=inscripcion.persona,
                                          asignaturamalla__isnull=False).exclude(inscripcion__carrera=inscripcion.carrera).exists():
        apto = '2'
    elif not VentasProgramaMaestria.objects.filter(status=True, inscripcioncohorte=ePostulante, valida=True).exists():
        apto = '3'

    enteros_resultantes = [int(num) for num in variable_valor('IDS_HOMOLOGACION')]

    if inscripcion.id in enteros_resultantes:
        apto = '0'
    return apto

def asignatura_seleccionada(solicitud, asignaturam):
    estado = '0'
    if SolicitudAsignatura.objects.filter(status=True, solicitud=solicitud, asignaturamalla=asignaturam).exists():
        estado = '1'
    return estado

def asignatura_ho(solicitud, asignaturam):
    obj = None
    if SolicitudAsignatura.objects.filter(status=True, solicitud=solicitud, asignaturamalla=asignaturam).exists():
        obj = SolicitudAsignatura.objects.filter(status=True, solicitud=solicitud, asignaturamalla=asignaturam).first()
    return obj

def estado_asignatura(solicitud, asignaturam):
    estado = 'No solicitado'
    if SolicitudAsignatura.objects.filter(status=True, solicitud=solicitud, asignaturamalla=asignaturam).exists():
        estado = SolicitudAsignatura.objects.filter(status=True, solicitud=solicitud, asignaturamalla=asignaturam).first().get_estado_display()
    return estado

def list_degree_products(ePerfilUsuario, eServicio):
    from api.views.alumno.secretary.solicitud import costo_tit_ex
    try:
        if not ePerfilUsuario.es_estudiante():
            raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
        eInscripcion = ePerfilUsuario.inscripcion
        homologa = apto_para_homologacion(ePerfilUsuario.inscripcion)
        eCoordinacion = eInscripcion.carrera.coordinacion_set.all()[0]
        eMatriculas = Matricula.objects.filter(inscripcion=eInscripcion, status=True).order_by("-nivel__periodo__inicio")

        eProductos = ProductoSecretaria.objects.filter(status=True, servicio=eServicio)
        eProducts = []
        base_url = get_variable('SITE_URL_SGA')
        eSolicitudT = None
        serializeruno = None
        for eProducto in eProductos:
            cost = 0
            realcosto = costo_tit_ex(eInscripcion)
            eContentTypeProducto = ContentType.objects.get_for_model(eProducto)

            if eProducto.costo > 0:
                cost = (Decimal(eProducto.costo).quantize(Decimal('.01'))).__float__()

            detail = ''
            if eProducto.id == 2:
                eSolicitudes = Solicitud.objects.filter(status=True, perfil_id=ePerfilUsuario.pk,
                                                        servicio_id=eServicio.pk,
                                                        origen_content_type_id=eContentTypeProducto.pk,
                                                        origen_object_id=eProducto.id)
                if eSolicitudes.values("id").exists():
                    eSolicitudT = eSolicitudes.first()
                    serializeruno = SolicitudSerializer(eSolicitudT)

                detail = f"La elaboración del informe técnico de pertinencia para determinar la aplicabilidad de la homologación de las asignaturas seleccionadas tiene un costo de ${cost}. En caso de que las asignaturas sean consideradas aptas para homologar, se aplicará un cargo adicional de $50 por todas las asignaturas homologadas."
            else:
                detail = f"La elaboración del informe técnico para saber si puede aplicar a la titulación extraordinaria tiene un costo de ${cost} y la inscripción al proceso tiene un valor de ${realcosto}, equivalente a dos módulos de una maestría"


            eContentType = ContentType.objects.get_for_model(eProducto)
            eProducts.append({
                "id": encrypt(eProducto.pk),
                "idsin": eProducto.pk,
                "idm": encrypt(eContentType.pk),
                "ids": encrypt(eServicio.pk),
                "imagen": f"{base_url}/static/bootstrap5/images/placeholder/placeholder-4by3.svg",
                "name": f"{eProducto.codigo} - {eProducto.descripcion}",
                # "certification_type": eCertificado.tipo_certificacion,
                "description": f"Titulación extraordinaria de Posgrado",
                "detail": detail,
                "cost": cost,
                "cost2modules": realcosto,
                "proceso": eProducto.servicio.proceso,
                "homologa": homologa,
                "carrera": f'{eInscripcion.carrera.nombre} CON MENCIÓN EN {eInscripcion.carrera.mencion} MODALIDAD {eInscripcion.carrera.get_modalidad_display()}' if eInscripcion.carrera.mencion else f'{eInscripcion.carrera.nombre} MODALIDAD {eInscripcion.carrera.get_modalidad_display()}',
                "idsinencryptar": eProducto.pk
                # "reqmallaculminada": eCertificado.mallaculminada,
                #"cost": (Decimal(eCertificado.costo).quantize(Decimal('.01')) if eCertificado.costo else Decimal(0).quantize(Decimal('.01'))).__float__(),
                # "validity": {
                #     "display": eCertificado.tiempo_vigencia(),
                #     "time": eCertificado.vigencia,
                #     "type": eCertificado.tipo_vigencia
                # },
                # "report": {
                #     "id": eCertificado.reporte.id,
                #     "name": eCertificado.reporte.nombre,
                #     "version": eCertificado.reporte.version,
                #     "types": eCertificado.reporte.tiporeporte(),
                # }
            })
        data = {
            'eProductos': eProducts,
            'eSolicitudT': serializeruno.data if eSolicitudT is not None else None
            # 'extras': {
            #             'eMatriculas': CertificadoMatriculaSerializer(eMatriculas, many=True).data if eMatriculas.values("id").exists() else []
            # }
        }
        return {'isSuccess': True, 'message': '', 'data': data}
    except Exception as ex:
        return {'isSuccess': False, 'message': ex.__str__(), 'data': {}}
