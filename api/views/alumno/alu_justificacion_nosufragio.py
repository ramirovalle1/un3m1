# coding=utf-8
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.alu_justificacion_nosufragio import JustificacionNoSufragioSerializer
from api.serializers.alumno.alu_vinculacion_posgrado import ParticipanteProyectoVinculacionPosSerializer, \
    DetalleAprobacionProyectoSerializer, ProyectoVinculacionSerializer
from django.db.models import Q

from sagest.funciones import encrypt_id
from sagest.models import SolicitudJustificacionPE, ProcesoEleccion
from sga.templatetags.sga_extras import encrypt
from sga.funciones import log, generar_nombre
from sga.models import PerfilUsuario
from posgrado.models import ParticipanteProyectoVinculacionPos, ProyectoVinculacion, DetalleAprobacionProyecto, \
    TIPO_EVIDENCIA
from rest_framework.pagination import LimitOffsetPagination


class AluJustificacioNoSufragioAPIView(APIView, LimitOffsetPagination):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALU_JUSTIFICACION_NOSUFRAGIO'
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
                periodo_id = encrypt_id(payload['periodo']['id'])
                procesoEleccion = ProcesoEleccion.objects.filter(status=True, activo=True).first()

                filtro = Q(status=True, persona=ePerfilUsuario.persona)

                eSearch = request.query_params.get('search', None)
                if eSearch:
                    eSearch = eSearch.strip()
                    filtro = filtro & (Q(motivo__icontains=eSearch))

                listado = SolicitudJustificacionPE.objects.filter(filtro)
                listado_pag = self.paginate_queryset(listado, request, view=self)
                serializer = JustificacionNoSufragioSerializer(listado_pag, many=True)
                data = {
                    'listado': serializer.data if listado.exists() else [],
                    'next': self.get_next_link(),
                    'previous': self.get_previous_link(),
                    'count': self.count,
                    'limit': self.default_limit
                }
                if eSearch:
                    data['search'] = eSearch

                if procesoEleccion:
                    data['adicionarsolicitud'] = True
                    data['proceso_activo_id'] = procesoEleccion.id
                else:
                    data['adicionarsolicitud'] = False

            elif action == 'load_form_justificacion_nosufragio':
                data = {}
                if id:
                    id = int(encrypt_id(id))
                    justificacion = SolicitudJustificacionPE.objects.filter(pk=id).first()
                    if justificacion:
                        serializer = JustificacionNoSufragioSerializer(justificacion)
                        data['justificacion'] = serializer.data

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
            ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt_id(payload['perfilprincipal']['id']))
            periodo_id = encrypt_id(payload['periodo']['id'])
            action = eRequest.get('action', None)

            if action == 'delete_justificacion_nosufragio':
                id = eRequest.get('id', None)
                if id is None:
                    raise ValueError('ID no proporcionado')
                id = int(encrypt_id(id))
                justificacion = SolicitudJustificacionPE.objects.filter(pk=id).first()
                if justificacion:
                    justificacion.status = False
                    justificacion.save(request)
                    return Helper_Response(isSuccess=True, data={}, message='Registro eliminado correctamente',
                                           status=status.HTTP_200_OK)
                raise NameError(u'No se encontro el registro')

            if action == 'save_justificacion_nosufragio':
                motivo = eRequest.get('motivo', None)

                procesoEleccion = ProcesoEleccion.objects.filter(status=True, activo=True).first()
                if not procesoEleccion:
                    raise NameError(u'No se encontro proceso electoral activo')

                if SolicitudJustificacionPE.objects.filter(persona=ePerfilUsuario.persona, proceso=procesoEleccion, status=True).exists():
                    raise NameError(u'Ya se ha registrado una solicitud de justificación en este proceso')

                justificacion = SolicitudJustificacionPE(
                    persona=ePerfilUsuario.persona,
                    motivo=motivo.strip().upper(),
                    proceso=procesoEleccion,
                )

                if 'fileDocumento' in eFiles:
                    nfileDocumento = eFiles['fileDocumento']
                    extensionDocumento = nfileDocumento._name.split('.')
                    tamDocumento = len(extensionDocumento)
                    exteDocumento = extensionDocumento[tamDocumento - 1]
                    if nfileDocumento.size > 5500000:
                        raise NameError(u"Error al cargar, el archivo es mayor a 55 Mb.")
                    if not exteDocumento.lower() == 'pdf':
                        raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                else:
                    raise NameError(u"Error al cargar, no se encontro el archivo .pdf")
                nfileDocumento._name = generar_nombre(f"archivo_{ePerfilUsuario.persona.id}_", 'evidencia.pdf')
                justificacion.archivo = nfileDocumento
                justificacion.save(request)

                return Helper_Response(isSuccess=True, data={"idp": justificacion.pk},
                                       message='Solitud registrada correctamente', status=status.HTTP_200_OK)

            if action == 'update_justificacion_nosufragio':
                id = eRequest.get('id', None)
                if id is None:
                    raise ValueError('ID no proporcionado')
                id = int(encrypt_id(id))
                justificacion = SolicitudJustificacionPE.objects.filter(pk=id).first()
                if justificacion:
                    motivo = eRequest.get('motivo', None)
                    justificacion.motivo = motivo.strip().upper()
                    if 'fileDocumento' in eFiles:
                        nfileDocumento = eFiles['fileDocumento']
                        extensionDocumento = nfileDocumento._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if nfileDocumento.size > 5500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 55 Mb.")
                        if not exteDocumento.lower() == 'pdf':
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        nfileDocumento._name = generar_nombre(f"archivo_{ePerfilUsuario.persona.id}_", 'evidencia.pdf')
                        justificacion.archivo = nfileDocumento
                    else:
                        archivo = eRequest.get('archivo', None)
                        if not archivo:
                            raise NameError(u"Error al cargar, no se encontro el archivo .pdf")

                    justificacion.save(request)
                    return Helper_Response(isSuccess=True, data={"idp": justificacion.pk},
                                           message='Solitud actualizada correctamente', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acción no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                   status=status.HTTP_200_OK)
