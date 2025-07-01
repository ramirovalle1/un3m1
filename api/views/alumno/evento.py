from datetime import datetime

from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.evento import PeriodoEventoSerializer, RegistroEventoSerializer, PersonaEventoSerializer
from even.models import PeriodoEvento, RegistroEvento
from sga.models import PerfilUsuario
from sga.templatetags.sga_extras import encrypt


class EventoAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_EVENTOS'

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

            if action == 'registerEvent':
                with transaction.atomic():
                    try:
                        aData = {
                        }
                        payload = request.auth.payload
                        eProfileUser = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                        ePerson = eProfileUser.persona
                        if not 'id' in eRequest:
                            raise NameError(u'No se encontro parametro del proceso.')
                        eEvento = PeriodoEvento.objects.get(pk=int(encrypt(eRequest['id'])))
                        asiste = eRequest['asiste']
                        if eEvento.cerrado:
                            raise NameError('Evento ya se encuentra cerrado.')
                        if not eEvento.publicar:
                            raise NameError('Evento no se encuentra publicado.')
                        eEventoRegistro = RegistroEvento.objects.filter(status=True, periodo=eEvento, participante=ePerson).first()
                        if eEventoRegistro is not None:
                            raise NameError('Usted ya se encuentra registrado en este evento.')
                        eEventoRegistro = RegistroEvento(status=True,
                                                         periodo=eEvento,
                                                         participante=ePerson,
                                                         perfil=eProfileUser,
                                                         inscripcion=eProfileUser.inscripcion)

                        if ePerson.canton:
                            eEvento.canton = ePerson.canton
                        if asiste == 'true':
                            eEventoRegistro.estado_confirmacion = 1
                        eEventoRegistro.save(request)
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}',  status=status.HTTP_200_OK)

            if action == 'confirmAssistance':
                with transaction.atomic():
                    try:
                        aData = {
                        }
                        payload = request.auth.payload
                        eProfileUser = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                        ePerson = eProfileUser.persona
                        if not 'id' in eRequest:
                            raise NameError(u'No se encontro parametro id.')
                        eEvento = RegistroEvento.objects.filter(status=True, pk=int(encrypt(eRequest['id']))).first()
                        if eEvento is None:
                            raise NameError(u'No se encontro un evento al parametro enviado.')
                        if eEvento.periodo.cerrado:
                            raise NameError('Evento ya se encuentra cerrado.')
                        if not eEvento.periodo.publicar:
                            raise NameError('Evento no se encuentra publicado.')
                        tipo = int(eRequest['tipo'])
                        msg = 'ASISTENCIA CONFIRMADA\nFECHA EVENTO {}'.format(str(eEvento.periodo.fechainicio)) if tipo == 1 else 'ASISTENCIA DECLINADA'
                        eEvento.estado_confirmacion = tipo
                        eEvento.save(request)
                        aData['msg'] = msg
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}',  status=status.HTTP_200_OK)

        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)


    @api_security
    def get(self, request):
        TIEMPO_ENCACHE = 60 * 15
        try:
            action = ''
            if 'action' in request.query_params:
                action = request.query_params['action']
            eRequest = request.query_params

            if action == 'getEvent':
                try:
                    aData = {
                    }
                    payload = request.auth.payload
                    eProfileUser = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                    ePeriodoEvento = PeriodoEvento.objects.get(pk=int(encrypt(eRequest['id'])))
                    aData['eEvento'] = eEvento = PeriodoEventoSerializer(ePeriodoEvento, context={'participante_id': eProfileUser.persona_id}).data
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)
            else:
                try:
                    aData = {
                    }
                    hoy = datetime.now()
                    payload = request.auth.payload
                    ePerfilUsuario = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                    if not ePerfilUsuario.es_estudiante():
                        raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                    ePersona = ePerfilUsuario.inscripcion.persona
                    aData['ePersona'] = PersonaEventoSerializer(ePersona).data
                    aData['ePeriodosEventos'] = []
                    aData['eEventos'] = []
                    opc_select = int(eRequest['opc_select'])
                    aData['opc_select'] = opc_select
                    if opc_select == 1:
                        #Eventos Disponibles
                        ePeriodosEventosEnCache = cache.get(f"eventosdisponible_persona_id{encrypt(ePersona.id)}")
                        if not ePeriodosEventosEnCache is None:
                            ePeriodosEventos = ePeriodosEventosEnCache
                        else:
                            filtros = Q(status=True, publicar=True,
                                        cerrado=False, permiteregistro=True,
                                        periodo_id=int(encrypt(payload['periodo']['id'])),
                                        tipoperfil=1) & Q(Q(todos=True) | Q(detalleperiodoevento__canton=ePersona.canton))
                            ePeriodosEventos = PeriodoEvento.objects.filter(filtros).distinct()
                            cache.set(f"eventosdisponible_persona_id{encrypt(ePersona.id)}", ePeriodosEventos, TIEMPO_ENCACHE)

                        aData['ePeriodosEventos'] = PeriodoEventoSerializer(ePeriodosEventos, many=True).data if ePeriodosEventos.values_list('id', flat=True).exists() else []
                    elif opc_select == 2:
                        #Mis Eventos
                        eEventosEnCache = cache.get(f"miseventos_persona_id{encrypt(ePersona.id)}")
                        if not eEventosEnCache is None:
                            eEventos = eEventosEnCache
                        else:
                            eEventos = PeriodoEvento.objects.filter(status=True, tipoperfil=1, registroevento__participante_id=ePersona.id, registroevento__status=True).distinct()
                            cache.set(f"miseventos_persona_id{encrypt(ePersona.id)}", eEventos, TIEMPO_ENCACHE)
                        aData['eEventos'] = PeriodoEventoSerializer(eEventos, many=True, context={'participante_id': ePersona.id}).data if eEventos.values_list('id', flat=True).exists() else []
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)
