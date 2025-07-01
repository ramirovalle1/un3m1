# -*- coding: UTF-8 -*-
from datetime import datetime
from django.db import transaction
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import AUTH_HEADER_TYPES
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from api.helpers.response_herlper import Helper_Response
from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.serializers.login.token import MyTokenObtainPairSerializer
from api.serializers.base.persona import PersonaBaseSerializer
from bd.models import UserToken, UserProfileChangeToken
from sga.models import Persona, Inscripcion, Carrera, Modalidad


class PersonaSerializer(PersonaBaseSerializer):

    class Meta:
        model = Persona
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ModalidadSerializer(Helper_ModelSerializer):

    class Meta:
        model = Modalidad
        exclude = ['usuario_creacion', 'usuario_modificacion']


class CarreraSerializer(Helper_ModelSerializer):

    class Meta:
        model = Carrera
        exclude = ['usuario_creacion', 'usuario_modificacion']


class InscripcionSerializer(Helper_ModelSerializer):
    persona = PersonaSerializer()
    carrera = CarreraSerializer()
    modalidad = ModalidadSerializer()

    class Meta:
        model = Inscripcion
        exclude = ['usuario_creacion', 'usuario_modificacion']


class CheckTokenView(APIView):

    def post(self, request, *args, **kwargs):
        try:
            hoy = datetime.now()
            if not 'token' in request.data:
                raise NameError(u'No se encontro parametro de token.')
            token = request.data['token']
            if not 'code' in request.data:
                raise NameError(u'No se encontro parametro de código.')
            code = request.data['code']
            if not UserToken.objects.values("id").filter(token=token).exists():
                raise NameError(u'Token invalido')
            eUserProfileChangeTokens = UserProfileChangeToken.objects.filter(user_token__token=token, isActive=True)
            if not eUserProfileChangeTokens.values("id").filter(codigo=code).exists():
                raise NameError(u'Código invalido')
            eUserProfileChangeToken = eUserProfileChangeTokens.filter(codigo=code).first()
            if not eUserProfileChangeToken.isValidoCodigo(code):
                raise NameError(u'Código invalido')
            ePersona = eUserProfileChangeToken.perfil_destino.persona
            if not eUserProfileChangeToken.perfil_destino.es_estudiante():
                raise NameError(u'Acción no permitida')
            eInscripcion = eUserProfileChangeToken.perfil_destino.inscripcion

            aData = {'ePersona': PersonaSerializer(ePersona).data,
                     'eInscripcion': InscripcionSerializer(eInscripcion).data}
            return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


class TokenViewBase(generics.GenericAPIView):
    permission_classes = ()
    authentication_classes = ()

    serializer_class = None

    www_authenticate_realm = 'api'

    def get_authenticate_header(self, request):
        return '{0} realm="{1}"'.format(
            AUTH_HEADER_TYPES[0],
            self.www_authenticate_realm,
        )

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        return Response(serializer.validated_data, status=status.HTTP_200_OK)


class TokenLoginView(TokenViewBase):
    serializer_class = MyTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)

            try:
                serializer.is_valid(raise_exception=True)
            except TokenError as e:
                raise InvalidToken(e.args[0])

            user = serializer.user

            return super().post(request, args, kwargs)
        except Exception as ex:
            return Response({'message': ex.__str__()}, status=status.HTTP_401_UNAUTHORIZED)
