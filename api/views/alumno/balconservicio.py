import json
from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.balconservicio import ProcesoSerializer, CategoriaSerializer, InformacionSerializer, SolicitudSerializer, HistorialSolicitudSerializer, EncuestaProcesoSerializer
from balcon.models import Proceso, Categoria, Informacion, ProcesoServicio, Solicitud, Agente, RequisitosSolicitud, HistorialSolicitud, RespuestaEncuestaSatisfaccion
from sga.funciones import remover_caracteres_especiales_unicode, generar_nombre, log, notificacion
from sga.models import PerfilUsuario
from sga.templatetags.sga_extras import encrypt


class BalconServicioAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_BALCON_SERVICIOS'

    @api_security
    def post(self, request):
        TIEMPO_ENCACHE = 60 * 15
        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data
            eFiles  = {}
        try:
            if not 'action' in eRequest:
                raise NameError(u'Parametro de acciòn no encontrado')

            action = eRequest['action']

            if action == 'getInformationsServices':
                try:
                    aData = {
                    }
                    if not 'id' in eRequest:
                        raise NameError(u'No se encontro parametro del proceso.')
                    eProcess = Proceso.objects.get(pk=int(encrypt(eRequest['id'])))
                    idslist = eProcess.procesoservicio_set.filter(status=True).values_list('id', flat=True)
                    eInformationsServices = Informacion.objects.filter(mostrar=True, tipo=2, status=True, servicio_id__in=idslist)
                    aData['eInformationsServices'] = InformacionSerializer(eInformationsServices,  many=True).data if eInformationsServices.values_list('id', flat=True).exists() else []
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}',  status=status.HTTP_200_OK)

            if action == 'addRequestService':
                with transaction.atomic():
                    try:
                        aData = {
                        }
                        payload = request.auth.payload
                        eProfileUser = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                        if not 'service_id' in eRequest:
                            raise NameError(u'No se encontro servicio del proceso.')
                        ePerson = eProfileUser.persona
                        eProcessService = ProcesoServicio.objects.get(pk=int(encrypt(eRequest['service_id'])))
                        eAgents = Agente.objects.filter(status=True, estado=True)
                        if not eAgents.values_list('id', flat=True).exists():
                            raise NameError(u'No se existen agentes disponibles para atender su solicitud.')

                        eHistoricalRequest = HistorialSolicitud.objects.filter((Q(solicitud__estado=1) |
                                                                                Q(solicitud__estado=3)),
                                                                               solicitud__solicitante_id=ePerson,
                                                                               solicitud__status=True,
                                                                               servicio=eProcessService)
                        if eHistoricalRequest.values_list('id', flat=True).exists():
                            raise NameError(u'TIENE SOLICITUDES PENDIENTES EN EL PROCESO %s  '%(eProcessService.servicio))

                        eBalconyRequestlast = Solicitud.objects.filter(solicitante=ePerson).order_by('numero').last()
                        numberBalconyRequest = eBalconyRequestlast.numero + 1 if eBalconyRequestlast else 1
                        type = int(eRequest['tipo'])
                        eBalconyRequest = Solicitud(
                            descripcion=eRequest['descripcion'],
                            tipo=type,
                            solicitante=ePerson,
                            perfil=eProfileUser,
                            estado=1,
                            numero=numberBalconyRequest
                        )
                        if eProcessService.proceso.subesolicitud:
                            if 'file_uprequest' in eFiles:
                                newfile = eFiles['file_uprequest']
                                extension = newfile._name.split('.')
                                tam = len(extension)
                                exte = extension[tam - 1]
                                if newfile.size > 4194304:
                                    raise NameError('El archivo de solicitud subido, su tamaño es mayor a 4 Mb.')
                                if not exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                                   raise NameError('El archivo de solicitud subido, solo permite .pdf, .jpg, .jpeg, .png')
                                newfile._name = generar_nombre("solicitud_", newfile._name)
                                eBalconyRequest.archivo = newfile
                            else:
                                raise NameError('Falta subir el archivo de solicitud.')

                        AgentsList = {eAgent.pk: eAgent.total_solicitud() for eAgent in eAgents}
                        AgentsListOrder = sorted(AgentsList.items(), key=lambda x: x[1])
                        if AgentsListOrder:
                            #AgentFree = Agente.objects.get(pk=AgentsListOrder[0][0])
                            eBalconyRequest.agente_id = AgentsListOrder[0][0] #AgentFree
                            eBalconyRequest.save(request)

                        eRequirementsBalconyRequest = eProcessService.requisitosconfiguracion_set.filter(status=True)
                        for eRequirement in eRequirementsBalconyRequest:
                            idenc = encrypt(eRequirement.id)
                            if not f'file_requirement_{idenc}' in eFiles:
                                if eRequirement.obligatorio:
                                    nameDocument = remover_caracteres_especiales_unicode(eRequirement.requisito.descripcion)
                                    raise NameError(f'FALTA SUBIR {nameDocument}')
                            else:
                                nameDocumentPerson = remover_caracteres_especiales_unicode(ePerson.__str__()).lower().replace(' ', '_')
                                nameRequiremt = eRequirement.requisito.nombre_input()
                                nameFile = f'{nameDocumentPerson}_{nameRequiremt}'
                                newfile = eFiles[f'file_requirement_{idenc}']
                                newfile._name = generar_nombre(nameFile.strip(), newfile._name)
                                eDetailRequirement = RequisitosSolicitud(solicitud=eBalconyRequest, requisito=eRequirement, archivo=newfile)
                                eDetailRequirement.save(request)
                        log(u'Adiciono Solicitud para el balcon: %s' % eBalconyRequest, request, "add")

                        eHistoricalRequest = HistorialSolicitud(servicio=eProcessService,
                                                                solicitud=eBalconyRequest,
                                                                asignadorecibe=eBalconyRequest.agente.persona)
                        eHistoricalRequest.save(request)
                        log(u'Se asigna servicio: %s' % eHistoricalRequest.servicio, request, "add")
                        cuerpo = ('Ha recibido una solicitud de %s' % eBalconyRequest)
                        notificacion("Solicitud de %s en balcón de servicios" % eBalconyRequest.solicitante,
                                     cuerpo, eBalconyRequest.agente.persona, None, 'adm_solicitudbalcon', eBalconyRequest.id,
                                     1, 'sga', Solicitud, request)
                        aData['urlservice'] = eProcessService.url
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}',  status=status.HTTP_200_OK)


            if action == 'getMyRequests':
                try:
                    aData = {
                    }
                    payload = request.auth.payload
                    eProfileUser = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                    ePerson = eProfileUser.persona

                    eBalconyRequestsEnCache = cache.get(f"balconsolicitudes_persona_id{encrypt(ePerson.id)}")
                    if not eBalconyRequestsEnCache is None:
                        eBalconyRequests = eBalconyRequestsEnCache
                    else:
                        eBalconyRequests = Solicitud.objects.filter(solicitante=ePerson, status=True).order_by('-id')
                        cache.set(f"balconsolicitudes_persona_id{encrypt(ePerson.id)}", eBalconyRequests, TIEMPO_ENCACHE)
                        #if eBalconyRequests.values_list('id', flat=True).exists():

                    aData['eBalconyRequests'] = SolicitudSerializer(eBalconyRequests,  many=True).data if eBalconyRequests.values_list('id', flat=True).exists() else []
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}',  status=status.HTTP_200_OK)

            if action == 'editRequestService':
                with transaction.atomic():
                    try:
                        aData = {
                        }
                        payload = request.auth.payload
                        if not 'id' in eRequest:
                            raise NameError(u'No se encontro el id de la solicitud.')
                        if not 'descripcion' in eRequest:
                            raise NameError(u'No se encontro la descripcion de la solicitud.')
                        id = int(encrypt(eRequest['id']))
                        eBalconyRequest = Solicitud.objects.get(id=id)
                        eBalconyRequest.descripcion = eRequest['descripcion']
                        eBalconyRequest.save(request)
                        log(u'Modificó Solicitud Balcon: %s' % eBalconyRequest, request, "edit")
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'delRequestService':
                with transaction.atomic():
                    try:
                        aData = {
                        }
                        payload = request.auth.payload
                        if not 'id' in eRequest:
                            raise NameError(u'No se encontro el id de la solicitud.')
                        id = int(encrypt(eRequest['id']))
                        eBalconyRequest = Solicitud.objects.get(id=id)
                        eBalconyRequest.delete()
                        #log(u'Modificó Solicitud Balcon: %s' % eBalconyRequest, request, "edit")
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'saveRequestQuestionstoQualify':
                with transaction.atomic():
                    try:
                        aData = {
                        }
                        payload = request.auth.payload
                        if not 'id' in eRequest:
                            raise NameError(u'No se encontro el id de la solicitud.')
                        id = int(encrypt(eRequest['id']))
                        eBalconyRequest = Solicitud.objects.get(id=id)
                        content_type = ContentType.objects.get_for_model(eBalconyRequest)
                        eAnswersQuestions = json.loads(eRequest['eAnswersQuestions'])
                        for eQuestion in eAnswersQuestions:
                            eAnswer = RespuestaEncuestaSatisfaccion(
                                pregunta_id=int(encrypt(eQuestion['id'])),
                                solicitud=eBalconyRequest,
                                valoracion=eQuestion['valoracion'],
                                observacion=eQuestion['observacion'],
                                object_id=id,
                                content_type=content_type)
                            eAnswer.save(request)
                            log(u'Calificó Pregunta de Solicitud Balcon: %s %s' %(eBalconyRequest, eAnswer), request, "edit")
                        log(u'Calificó Solicitud Balcon: %s' % eBalconyRequest, request, "edit")
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)


    @api_security
    def get(self, request):
        try:
            action = ''
            if 'action' in request.query_params:
                action = request.query_params['action']
            eRequest = request.query_params
            if action == 'getViewHistoricalRequestService':
                try:
                    aData = {
                    }
                    if not 'id' in eRequest:
                        raise NameError(u'No se encontro el id de la solicitud.')
                    id = int(encrypt(eRequest['id']))
                    eBalconyRequest = Solicitud.objects.get(id=id)
                    eBalconyRequestHistories = eBalconyRequest.historialsolicitud_set.filter(status=True).order_by('pk')
                    aData['eBalconyRequest'] = SolicitudSerializer(eBalconyRequest).data if eBalconyRequest is not None else []
                    aData['eBalconyRequestHistories'] = HistorialSolicitudSerializer(eBalconyRequestHistories, many=True).data if eBalconyRequestHistories.values_list('id', flat=True).exists() else []
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'getMyRequestService':
                try:
                    aData = {
                    }
                    payload = request.auth.payload
                    eProfileUser = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                    ePerson = eProfileUser.persona
                    if not 'id' in eRequest:
                        raise NameError(u'No se encontro el id de la solicitud.')
                    id = int(encrypt(eRequest['id']))
                    eBalconyRequest = Solicitud.objects.get(id=id)
                    aData['eBalconyRequest'] = SolicitudSerializer(eBalconyRequest).data if eBalconyRequest else {}
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}',  status=status.HTTP_200_OK)

            elif action == 'getMyRequestQuestionstoQualify':
                try:
                    aData = {
                    }
                    payload = request.auth.payload
                    if not 'id' in eRequest:
                        raise NameError(u'No se encontro el id de la solicitud.')
                    eProfileUser = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                    ePerson = eProfileUser.persona
                    id = int(encrypt(eRequest['id']))
                    eBalconyRequest = Solicitud.objects.get(id=id)
                    eSurveysProcess = eBalconyRequest.encuesta_proceso_preguntas_vigentes()
                    aData['eBalconyRequest'] = SolicitudSerializer(eBalconyRequest).data if eBalconyRequest else {}
                    aData['eSurveysProcess'] = EncuestaProcesoSerializer(eSurveysProcess,  many=True, context={'solicitud': eBalconyRequest}).data if eSurveysProcess.values_list('id', flat=True).exists() else []
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}',  status=status.HTTP_200_OK)

            else:
                try:
                    hoy = datetime.now()
                    payload = request.auth.payload
                    ePerfilUsuario = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))

                    if not ePerfilUsuario.es_estudiante():
                        raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                    if not 'id' in payload['matricula']:
                        raise NameError(u'No se encuentra matriculado.')
                    eData = {}
                    eCoordinacion = ePerfilUsuario.inscripcion.mi_coordinacion()
                    #eProcesos = Proceso.objects.filter(status=True, activo=True)
                    eCategorias = Categoria.objects.filter(status=True, estado=True, coordinaciones=eCoordinacion).order_by('descripcion')

                    from inno.models import PresidenteCurso
                    presi = PresidenteCurso.objects.filter(status=True, matricula__nivel__periodo=int(encrypt(payload['periodo']['id'])),
                                                   matricula__isnull=False, matricula__inscripcion = ePerfilUsuario.inscripcion )
                    ban = False
                    if presi:
                        ban = True
                    eData['eCategorias'] = CategoriaSerializer(eCategorias, many=True).data if eCategorias.values_list('id', flat=True).exists() else []
                    eData['ban'] = ban
                    #eData['eProcesos'] = ProcesoSerializer(eProcesos, many=True).data if eProcesos.values_list('id', flat=True).exists() else []
                    return Helper_Response(isSuccess=True, data=eData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)
