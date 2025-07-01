# coding=utf-8
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.alu_vinculacion_posgrado import ParticipanteProyectoVinculacionPosSerializer, \
    DetalleAprobacionProyectoSerializer, ProyectoVinculacionSerializer
from django.db.models import Q
from sga.templatetags.sga_extras import encrypt
from sga.funciones import log, generar_nombre
from sga.models import PerfilUsuario
from posgrado.models import ParticipanteProyectoVinculacionPos, ProyectoVinculacion, DetalleAprobacionProyecto, \
    TIPO_EVIDENCIA
from rest_framework.pagination import LimitOffsetPagination


class AluVinculacionPosgradoAPIView(APIView, LimitOffsetPagination):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALU_VINCULACION_POSGRADO'
    default_limit = 20

    @api_security
    def get(self, request):
        try:
            payload = request.auth.payload
            ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
            if not ePerfilUsuario.es_estudiante():
                raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')

            action = request.query_params.get('action', None)
            id = request.query_params.get('id', None)
            if action == 'list':
                filtro = Q(proyectovinculacion__status=True) & Q(status=True) & Q(inscripcion__id=ePerfilUsuario.inscripcion.id) & Q(inscripcion__coordinacion_id=7)

                eSearch = request.query_params.get('search', None)
                if eSearch:
                    eSearch = eSearch.strip()
                    filtro = filtro & (Q(proyectovinculacion__titulo__icontains=eSearch) | Q(inscripcion__persona__cedula=eSearch))

                listado = ParticipanteProyectoVinculacionPos.objects.filter(filtro)
                manuales_pag = self.paginate_queryset(listado, request, view=self)
                serializer = ParticipanteProyectoVinculacionPosSerializer(manuales_pag, many=True)
                data = {
                    'listado': serializer.data if listado.exists() else [],
                    'next': self.get_next_link(),
                    'previous': self.get_previous_link(),
                    'count': self.count,
                    'limit': self.default_limit
                }
                if eSearch:
                    data['search'] = eSearch

            elif action == 'load_form_proyecto_vinculacion':
                data = {}
                if id:
                    id = int(encrypt(id))
                    participanteproyectov = ParticipanteProyectoVinculacionPos.objects.filter(pk=id).first()
                    if participanteproyectov:
                        serializerparticipanteproyectov = ParticipanteProyectoVinculacionPosSerializer(participanteproyectov)
                        data['participanteproyectov'] = serializerparticipanteproyectov.data

                data['tipo_evidencia'] = [{"id": id, "nombre": nombre , 'value': id} for id, nombre in TIPO_EVIDENCIA]

                return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                   status=status.HTTP_200_OK)

    def post(self, request):
        try:
            if 'multipart/form-data' in request.content_type:
                eRequest = request._request.POST
                eFiles = request._request.FILES
            else:
                eRequest = request.data
            payload = request.auth.payload
            inscripcion = int(encrypt(payload['inscripcion']['id']))
            action = eRequest.get('action', None)

            if action is None:
                raise NameError(u'Parametro de acciòn no encontrado')

            if action == 'delete_proyecto_vinculacion':
                id = eRequest.get('id', None)
                if id:
                    id = int(encrypt(id))
                    participanteproyectov = ParticipanteProyectoVinculacionPos.objects.filter(pk=id).first()
                    if participanteproyectov:
                        pv = ProyectoVinculacion.objects.filter(pk=participanteproyectov.proyectovinculacion.pk).first()
                        participanteproyectov.status = pv.status = False
                        participanteproyectov.save(request)
                        pv.save(request)
                        return Helper_Response(isSuccess=True, data={}, message='Se elimino correctamente',
                                               status=status.HTTP_200_OK)
                    else:
                        raise NameError(u'No se encontro el registro')

            if action == 'save_proyecto_vinculacion':
                titulo = eRequest.get('titulo', None)
                descripcion = eRequest.get('descripcion', None)
                tipo_evidencia_id = eRequest.get('tipo_evidencia_id', None)
                if tipo_evidencia_id:
                    tipo_evidencia_id = int(tipo_evidencia_id)
                else:
                    raise NameError(u'El tipo de evidencia es requerido')

                proyectovinculacion = ProyectoVinculacion(
                    titulo=titulo.strip().upper(),
                    descripcion=descripcion.strip().upper(),
                )
                proyectovinculacion.save(request)
                participanteproyecto = ParticipanteProyectoVinculacionPos(
                    inscripcion_id=inscripcion,
                    proyectovinculacion=proyectovinculacion,
                    tipoevidencia=tipo_evidencia_id)

                if tipo_evidencia_id == 1:
                    if 'fileDocumento' in eFiles:
                        nfileDocumento = eFiles['fileDocumento']
                        extensionDocumento = nfileDocumento._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if nfileDocumento.size > 15000000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() == 'pdf':
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                    else:
                        raise NameError(u"Error al cargar, no se encontro el archivo .pdf")
                    nfileDocumento._name = generar_nombre("evidencia_", nfileDocumento._name)
                    participanteproyecto.evidencia = nfileDocumento
                elif tipo_evidencia_id == 2:
                    participanteproyecto.evidencia = eRequest.get('url', '')
                participanteproyecto.save(request)
                return Helper_Response(isSuccess=True, data={"idp": proyectovinculacion.pk},
                                       message='Se guardo correctamente solicitud', status=status.HTTP_200_OK)

            if action == 'update_proyecto_vinculacion':
                id = eRequest.get('id', None)
                if id:
                    id = int(encrypt(id))
                    participanteproyectov = ParticipanteProyectoVinculacionPos.objects.filter(pk=id).first()
                    if participanteproyectov:
                        titulo = eRequest.get('titulo', None)
                        descripcion = eRequest.get('descripcion', None)
                        tipo_evidencia_id = eRequest.get('tipo_evidencia_id', None)
                        if tipo_evidencia_id:
                            tipo_evidencia_id = int(tipo_evidencia_id)
                        else:
                            raise NameError(u'El tipo de evidencia es requerido')

                        proyectovinculacion = ProyectoVinculacion.objects.filter(pk=participanteproyectov.proyectovinculacion.id).first()
                        if proyectovinculacion:
                            proyectovinculacion.titulo = titulo.strip().upper()
                            proyectovinculacion.descripcion = descripcion.strip().upper()
                            proyectovinculacion.save(request)
                            participanteproyectov.tipoevidencia = tipo_evidencia_id
                            if tipo_evidencia_id == 1:
                                if 'fileDocumento' in eFiles:
                                    nfileDocumento = eFiles['fileDocumento']
                                    extensionDocumento = nfileDocumento._name.split('.')
                                    tamDocumento = len(extensionDocumento)
                                    exteDocumento = extensionDocumento[tamDocumento - 1]
                                    if nfileDocumento.size > 1500000:
                                        raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                                    if not exteDocumento.lower() == 'pdf':
                                        raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                                    nfileDocumento._name = generar_nombre("evidencia_", nfileDocumento._name)
                                    participanteproyectov.evidencia = nfileDocumento
                                else:
                                    archivo = eRequest.get('archivo', None)
                                    if not archivo:
                                        raise NameError(u"Error al cargar, no se encontro el archivo .pdf")

                            elif tipo_evidencia_id == 2:
                                participanteproyectov.evidencia = eRequest.get('url', '')
                            participanteproyectov.save(request)
                            return Helper_Response(isSuccess=True, data={"idp": proyectovinculacion.pk},
                                                   message='Se actualizo correctamente solicitud', status=status.HTTP_200_OK)


            if action == 'detalle_proyecto_vinculacion':
                data = {
                    'participanteproyectov': {},
                    'detalle_aprobacion': []
                }
                if request.data['id']:
                    participanteproyectov = ParticipanteProyectoVinculacionPos.objects.filter(
                        pk=int(encrypt(request.data['id']))).first()
                    if participanteproyectov:
                        serializerparticipanteproyectov = ParticipanteProyectoVinculacionPosSerializer(
                            participanteproyectov)
                        data['participanteproyectov'] = serializerparticipanteproyectov.data

                        detalleaprobacion = DetalleAprobacionProyecto.objects.filter(
                            proyectovinculacion__id=participanteproyectov.proyectovinculacion.id)
                        if detalleaprobacion.exists():
                            serializerdetalleaprobacion = DetalleAprobacionProyectoSerializer(detalleaprobacion,
                                                                                              many=True)
                            data['detalle_aprobacion'] = serializerdetalleaprobacion.data

                    return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                   status=status.HTTP_200_OK)
