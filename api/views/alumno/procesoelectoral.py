# coding=utf-8
import json
from datetime import datetime

from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.procesoelectoral import CabPadronElectoralSerializer, DetPersonaPadronElectoralSerializer, \
    JustificacionPersonaPadronElectoralSerializer, HistorialJustificacionPersonaPadronElectoralSerializer, \
    TipoSolicitudInformacionPadronElectoralSerializer, SolicitudInformacionPadronElectoralSerializer
from sga.funciones import remover_caracteres_especiales_unicode, generar_nombre
from sga.models import PerfilUsuario, CabPadronElectoral, DetPersonaPadronElectoral, \
    SolicitudInformacionPadronElectoral, JustificacionPersonaPadronElectoral, ESTADO_JUSTIFICACION, \
    HistorialJustificacionPersonaPadronElectoral, TipoSolicitudInformacionPadronElectoral
from sga.templatetags.sga_extras import encrypt


class ProcesoElectoralAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_PROCESO_ELECTORAL'

    @api_security
    def post(self, request):
        hoy = datetime.now().date()
        payload = request.auth.payload
        ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
        if not ePerfilUsuario.es_estudiante():
            raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
        eInscripcion = ePerfilUsuario.inscripcion
        ePersona = eInscripcion.persona
        modalidad = eInscripcion.modalidad
        es_virtual = True if modalidad.pk == 3 else False
        en_milagro = True if ePersona.canton.pk == 2 else False

        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data
        try:
            if not 'action' in eRequest:
                raise NameError(u'Parametro de acciòn no encontrado')

            action = eRequest['action']

            if action == 'addsolicitud':
                try:
                    with transaction.atomic():
                        json_string = '{"value":1,"label":"hi"}'
                        # Convertir la cadena JSON a un diccionario de Python
                        data = json.loads(json_string)
                        cab = CabPadronElectoral.objects.get(pk=int(eRequest['id']))
                        solicitud = SolicitudInformacionPadronElectoral(persona=ePersona,
                                                                        cab=cab,
                                                                        estados=0,
                                                                        tipo_id=data['value'],
                                                                        titulo='',
                                                                        observacion=eRequest['observacion'])
                        solicitud.save(request)

                    aData = {

                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)




            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                   status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        try:
            if 'action' in request.query_params:
                action = request.query_params['action']

                if action == 'loadFormSolicitarInformacion':
                    try:
                        id = request.query_params['id']
                        filtro = CabPadronElectoral.objects.filter(status=True, pk=id).first()
                        filtro_serializer = CabPadronElectoralSerializer(filtro)
                        eTipoSolicitudInformacionPadronElectoral = TipoSolicitudInformacionPadronElectoral.objects.filter(status=True).order_by('descripcion')
                        tipo_serializer = TipoSolicitudInformacionPadronElectoralSerializer(eTipoSolicitudInformacionPadronElectoral, many = True)

                        aData = {
                            'id': id,
                            'filtro': filtro_serializer.data if filtro else [],
                            'tipo': tipo_serializer.data if eTipoSolicitudInformacionPadronElectoral else [],
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
                        raise NameError(u'Solo los perfiles de estudiantes pueden ingresar a la información.')
                    eInscripcion = ePerfilUsuario.inscripcion
                    persona = eInscripcion.persona
                    soliprocesoactivos = None
                    procesoactivo = CabPadronElectoral.objects.filter(status=True, activo=True).first()

                    if procesoactivo:
                        soliprocesoactivos = SolicitudInformacionPadronElectoral.objects.filter(persona=persona, cab=procesoactivo).order_by( '-pk')

                    listvigente = DetPersonaPadronElectoral.objects.filter(status=True, persona=persona,
                                                                           cab__activo=True).order_by('-pk')
                    listpasados = DetPersonaPadronElectoral.objects.filter(status=True, persona=persona,
                                                                           cab__activo=False).order_by('-pk')

                    procesoactivo_serializer = CabPadronElectoralSerializer(procesoactivo)
                    soliprocesoactivos_serializer = SolicitudInformacionPadronElectoralSerializer(soliprocesoactivos, many=True)
                    listvigente_serializer = DetPersonaPadronElectoralSerializer(listvigente, many=True)
                    listpasados_serializer = DetPersonaPadronElectoralSerializer(listpasados, many=True)

                    data = {
                        'procesoactivo': procesoactivo_serializer.data if procesoactivo else [],
                        'soliprocesoactivos': soliprocesoactivos_serializer.data if soliprocesoactivos else [],
                        'listvigente': listvigente_serializer.data if listvigente else [],
                        'listpasados': listpasados_serializer.data if listpasados else [],

                    }
                    return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                   status=status.HTTP_200_OK)


class ProcesoElectoralJustificacionAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_PROCESO_ELECTORAL'

    @api_security
    def post(self, request):
        hoy = datetime.now().date()
        payload = request.auth.payload
        ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
        if not ePerfilUsuario.es_estudiante():
            raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
        eInscripcion = ePerfilUsuario.inscripcion
        ePersona = eInscripcion.persona
        modalidad = eInscripcion.modalidad
        es_virtual = True if modalidad.pk == 3 else False
        en_milagro = True if ePersona.canton.pk == 2 else False

        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data
        try:
            if not 'action' in eRequest:
                raise NameError(u'Parametro de acciòn no encontrado')

            action = eRequest['action']

            if action == 'add':
                try:
                    with transaction.atomic():
                        newfile = None
                        id = int(eRequest['id'])
                        virtual = False
                        if es_virtual:
                            virtual = True
                            if en_milagro:
                                virtual = False

                        filtro = DetPersonaPadronElectoral.objects.get(pk=id)
                        nombre_persona = remover_caracteres_especiales_unicode(filtro.persona.__str__().lower().replace(' ', '_')).lower().replace(' ', '_')
                        nombre_persona = remover_caracteres_especiales_unicode(filtro.persona.__str__().lower().replace(' ', '_')).lower().replace(' ', '_')
                        nombre_persona = nombre_persona.replace(u'Ü', u'U').replace(u'ü', u'u')
                        justificacion = JustificacionPersonaPadronElectoral(inscripcion=filtro, observacion=eRequest['observacion'])
                        validador = False
                        cantdocumentos = 0
                        if virtual:
                            justificacion.estudiante_enlinea = True
                            justificacion.estudiante_presencial = False

                        else:
                            justificacion.estudiante_enlinea = False
                            justificacion.estudiante_presencial = True
                        if 'certificado_medico' in eFiles:
                            validador = True
                            cantdocumentos += 1
                            newfile = eFiles['certificado_medico']
                            extension = newfile._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if newfile.size > 4194304:
                                raise NameError("Error, el tamaño del archivo es mayor a 4 Mb.")
                            if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                                newfile._name = generar_nombre("certificado_medico_{}".format(nombre_persona), newfile._name)
                            else:
                                transaction.set_rollback(True)
                                raise NameError("Error, solo archivos .pdf,.jpg, .jpeg"
                                                )
                            justificacion.certificado_medico = newfile
                        if 'certificado_upc' in eFiles:
                            validador = True
                            cantdocumentos += 1
                            newfile = eFiles['certificado_upc']
                            extension = newfile._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if newfile.size > 4194304:
                                raise NameError("Error, el tamaño del archivo es mayor a 4 Mb.")
                            if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                                newfile._name = generar_nombre("certificado_upc_{}".format(nombre_persona), newfile._name)
                            else:
                                transaction.set_rollback(True)
                                raise NameError("Error, solo archivos .pdf,.jpg, .jpeg")

                            justificacion.certificado_upc = newfile
                        if 'certificado_defuncion' in eFiles:
                            validador = True
                            cantdocumentos += 1
                            newfile = eFiles['certificado_defuncion']
                            extension = newfile._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if newfile.size > 4194304:
                                raise NameError("Error, el tamaño del archivo es mayor a 4 Mb.")
                            if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                                newfile._name = generar_nombre( "certificado_defuncion_{}".format(nombre_persona), newfile._name)
                            else:
                                transaction.set_rollback(True)
                                raise NameError("Error, solo archivos .pdf,.jpg, .jpeg")
                            justificacion.certificado_defuncion = newfile
                        if 'certificado_licencia' in eFiles:
                            validador = True
                            cantdocumentos += 1
                            newfile = eFiles['certificado_licencia']
                            extension = newfile._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if newfile.size > 4194304:
                                raise NameError("Error, el tamaño del archivo es mayor a 4 Mb.")
                            if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                                newfile._name = generar_nombre("certificado_licencia_{}".format(nombre_persona),  newfile._name)
                            else:
                                transaction.set_rollback(True)
                                raise NameError("Error, solo archivos .pdf,.jpg, .jpeg")
                            justificacion.certificado_licencia = newfile
                        if 'certificado_alterno' in eFiles:
                            validador = True
                            cantdocumentos += 1
                            newfile = eFiles['certificado_alterno']
                            extension = newfile._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if newfile.size > 4194304:
                                raise NameError("Error, el tamaño del archivo es mayor a 4 Mb.")
                            if exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                                newfile._name = generar_nombre("certificado_alterno_{}".format(nombre_persona), newfile._name)
                            else:
                                transaction.set_rollback(True)
                                raise NameError("Error, solo archivos .pdf,.jpg, .jpeg")
                            justificacion.certificado_alterno = newfile

                        if validador and cantdocumentos == 1:
                            filtro.puede_justificar = False
                            filtro.save(request)
                            justificacion.tipo = 1
                            justificacion.save(request)
                        else:
                            transaction.set_rollback(True)
                            raise NameError("Debe subir un solo documento de acuerdo a la categoría escogida.")


                    aData = {

                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                   status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        try:
            if 'action' in request.query_params:
                action = request.query_params['action']

                if action == 'loadFormJustificar':
                    try:
                        id = request.query_params['id']

                        aData = {
                            'id': id,
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)




                if action == 'loadViewObservacion':
                    try:
                        id = request.query_params['id']
                        filtro = JustificacionPersonaPadronElectoral.objects.filter(status=True,pk=id).first()
                        if filtro:
                            detalle = filtro.historialjustificacionpersonapadronelectoral_set.all().order_by( 'pk')
                        else:
                            detalle=None

                        filtro_serializer= JustificacionPersonaPadronElectoralSerializer(filtro)
                        detalle_serializer = HistorialJustificacionPersonaPadronElectoralSerializer(detalle,many=True)

                        aData = {
                            'id': id,
                            'filtro':filtro_serializer.data if filtro else [],
                            'detalle': detalle_serializer.data if detalle else [],
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
                        raise NameError(u'Solo los perfiles de estudiantes pueden ingresar a la información.')

                    if not 'id' in request.query_params:
                        raise NameError(u"Categoría no encontrada")

                    id = int(request.query_params.get('id', '0'))
                    if id == 0:
                        raise NameError(u'Parametro no encontrado.')

                    eInscripcion = ePerfilUsuario.inscripcion
                    persona = eInscripcion.persona
                    _ESTADO_JUSTIFICACION = ESTADO_JUSTIFICACION
                    filtro = DetPersonaPadronElectoral.objects.get(pk=id)
                    listado = JustificacionPersonaPadronElectoral.objects.filter(status=True,
                                                                                 inscripcion=filtro).order_by('-pk')

                    listado_serializer = JustificacionPersonaPadronElectoralSerializer(listado, many=True)
                    filtro_serializer = DetPersonaPadronElectoralSerializer(filtro)

                    data = {
                        'id': id,
                        'estados_justificacion': _ESTADO_JUSTIFICACION,
                        'filtro': filtro_serializer.data if filtro else [],
                        'listado': listado_serializer.data if listado else [],
                    }
                    return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                   status=status.HTTP_200_OK)
