import settings
from datetime import datetime
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.hashers import make_password
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenViewBase
from rest_framework import status, serializers
from api.helpers.functions_helper import get_variable
from api.helpers.response_herlper import Helper_Response
from sga.models import Persona
from sga.templatetags.sga_extras import encrypt


unicode = str


class MyProfileTokenRefreshSerializer(TokenRefreshSerializer):
    # periodo_id = serializers.CharField()

    def validate(self, attrs):
        # periodo_id = attrs['periodo_id']
        refresh = RefreshToken(attrs['refresh'])
        access = refresh.access_token
        # a = AccessToken()
        data = {}
        if api_settings.ROTATE_REFRESH_TOKENS:
            if api_settings.BLACKLIST_AFTER_ROTATION:
                try:
                    try:
                        ePersona = Persona.objects.db_manager("sga_select").get(pk=encrypt(access.payload['persona']['id']))
                    except ObjectDoesNotExist:
                        raise NameError('No tiene perfil asignado')
                    foto_perfil = ePersona.mi_foto_url()

                    api_site_url_sga = get_variable('SITE_URL_SGA')
                    if api_site_url_sga:
                        foto_perfil = f"{api_site_url_sga}{foto_perfil}"
                    aPersona = {
                        'id': encrypt(ePersona.id),
                        'nombre_minus': ePersona.nombre_minus(),
                        'nombre_completo': ePersona.nombre_completo(),
                        'apellido_paterno': ePersona.apellido1,
                        'apellido_materno': ePersona.apellido2,
                        'nombres': ePersona.nombres,
                        'documento': ePersona.documento(),
                        'tipo_documento': ePersona.tipo_documento(),
                        'correo_institucional': ePersona.emailinst,
                        'correo_personal': ePersona.email,
                        'ciudad': ePersona.canton.nombre if ePersona.canton else None,
                        'direccion': ePersona.direccion_corta(),
                        'foto': foto_perfil,
                        'sexo_id': ePersona.sexo_id,
                    }
                    """TOKEN DE ACCESO SE ACTUALIZA"""
                    access.payload['persona'] = aPersona
                    """TOKEN DE REFRESH SE ACTUALIZA"""
                    refresh.payload['persona'] = aPersona

                    #refresh.blacklist()

                except AttributeError:
                    # If blacklist app not installed, `blacklist` method will
                    # not be present
                    pass

            refresh.set_jti()
            refresh.set_exp()
            data['refresh'] = str(refresh)
        data['access'] = str(access)

        return data

    @classmethod
    def get_token(cls, user):
        try:
            token = super().get_token(user)
            return token
        except TokenError as e:
            raise InvalidToken(e.args[0])

    def options(self, request):
        try:
            return Helper_Response(isSuccess=True, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, message='Ocurrio un error: %s' % ex.__str__(), status=status.HTTP_202_ACCEPTED)


class MyProfileTokenObtainPairView(TokenViewBase):
    serializer_class = MyProfileTokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
