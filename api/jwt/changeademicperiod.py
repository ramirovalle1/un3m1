from django.core.cache import cache

import settings
from datetime import datetime
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
from bd.funciones import generate_code
from bd.models import UserProfileChangeToken
from sga.models import PerfilUsuario, Periodo
from sga.templatetags.sga_extras import encrypt


unicode = str


class MyChangeAcademicPeriodTokenRefreshSerializer(TokenRefreshSerializer):
    periodo_id = serializers.CharField()

    def validate(self, attrs):
        periodo_id = attrs['periodo_id']
        refresh = RefreshToken(attrs['refresh'])
        access = refresh.access_token
        # a = AccessToken()
        data = {}
        if api_settings.ROTATE_REFRESH_TOKENS:
            if api_settings.BLACKLIST_AFTER_ROTATION:
                try:
                    ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(access.payload['perfilprincipal']['id']))
                    eUserProfileChangeToken = None
                    if (eModel := UserProfileChangeToken.objects.filter(perfil_origen=ePerfilUsuario, perfil_destino=ePerfilUsuario, app=1, isActive=True).first()) is not None:
                        code = generate_code(32)
                        eUserProfileChangeToken = eModel
                    ePeriodo = Periodo.objects.get(pk=encrypt(periodo_id))
                    perfil_id = access.payload['perfilprincipal']['id']
                    ePerfilPrincipal = PerfilUsuario.objects.get(pk=encrypt(perfil_id))
                    eInscripcion = ePerfilPrincipal.inscripcion
                    eMatricula = eInscripcion.mi_matricula_periodo(ePeriodo.id)

                    if cache.has_key(f"inscripcion_id_{encrypt(eInscripcion.id)}_periodos"):
                        ePeriodos = cache.get(f"inscripcion_id_{encrypt(eInscripcion.id)}_periodos")
                    else:
                        ePeriodos = Periodo.objects.db_manager("sga_select").filter(nivel__matricula__inscripcion=eInscripcion, status=True, nivel__status=True, nivel__matricula__status=True, nivel__matricula__inscripcion__status=True).order_by('-inicio')
                        cache.set(f"inscripcion_id_{encrypt(eInscripcion.id)}_periodos", ePeriodos, 60 * 60 * 60)

                    periodos = []
                    if cache.has_key(f"login_api_estudiante_inscripcion_id_{encrypt(eInscripcion.id)}_periodos"):
                        periodos = cache.get(f"login_api_estudiante_inscripcion_id_{encrypt(eInscripcion.id)}_periodos")
                    else:
                        for periodo in ePeriodos:
                            periodos.append({"id": encrypt(periodo.id),
                                             "nombre_completo": periodo.nombre})
                        cache.set(f"login_api_estudiante_inscripcion_id_{encrypt(eInscripcion.id)}_periodos", periodos, 60 * 60 * 60)

                    """TOKEN DE ACCESO SE ACTUALIZA"""
                    access.payload['matricula'] = {"id": encrypt(eMatricula.id) if eMatricula else encrypt(0)}
                    # access.payload['periodo'] = {"id": encrypt(eMatricula.nivel.periodo.id) if eMatricula else encrypt(ePeriodo.id) if ePeriodo else 0,
                    #                              "nombre_completo": eMatricula.nivel.periodo.nombre if eMatricula else ePeriodo.nombre if ePeriodo else ""}
                    access.payload['periodo'] = {"id": encrypt(eMatricula.nivel.periodo.id) if eMatricula else encrypt(ePeriodos[0].id) if ePeriodos.values("id").exists() else encrypt(0),
                                                 "nombre_completo": eMatricula.nivel.periodo.nombre if eMatricula else ePeriodos[0].nombre if ePeriodos.values("id").exists() else ""}

                    """TOKEN DE REFRESH SE ACTUALIZA"""
                    refresh.payload['matricula'] = {"id": encrypt(eMatricula.id) if eMatricula else encrypt(0)}
                    # refresh.payload['periodo'] = {"id": encrypt(eMatricula.nivel.periodo.id) if eMatricula else encrypt(ePeriodo.id) if ePeriodo else 0,
                    #                               "nombre_completo": eMatricula.nivel.periodo.nombre if eMatricula else ePeriodo.nombre if ePeriodo else ""}
                    refresh.payload['periodo'] = {"id": encrypt(eMatricula.nivel.periodo_id) if eMatricula else encrypt(ePeriodos[0].id) if ePeriodos.values("id").exists() else encrypt(0),
                                                  "nombre_completo": eMatricula.nivel.periodo.nombre if eMatricula else ePeriodos[0].nombre if ePeriodos.values("id").exists() else ""}

                    CLASIFICACION = (
                        (1, u'PREGRADO'),
                        (2, u'POSGRADO'),
                        (3, u'ADMISION'),
                        )
                    clasificacion = 0
                    if eInscripcion.coordinacion.id == 9:
                        clasificacion = 3
                    elif eInscripcion.coordinacion.id in [7, 10]:
                        clasificacion = 2
                    elif eInscripcion.coordinacion.id in [1, 2, 3, 4, 5]:
                        clasificacion = 1

                    access.payload['coordinacion'] = {
                        "id": encrypt(eInscripcion.coordinacion.id),
                        "nombre": eInscripcion.coordinacion.nombre,
                        "alias": eInscripcion.coordinacion.alias,
                        'clasificacion': clasificacion,
                        'display_clasificacion': dict(CLASIFICACION)[clasificacion]
                        }
                    refresh.payload['coordinacion'] = {
                        "id": encrypt(eInscripcion.coordinacion.id),
                        "nombre": eInscripcion.coordinacion.nombre,
                        "alias": eInscripcion.coordinacion.alias,
                        'clasificacion': clasificacion,
                        'display_clasificacion': dict(CLASIFICACION)[clasificacion]
                        }

                    if eUserProfileChangeToken:
                        eUserProfileChangeToken.perfil_origen = ePerfilPrincipal
                        eUserProfileChangeToken.perfil_destino = ePerfilPrincipal
                        eUserProfileChangeToken.periodo = eMatricula.nivel.periodo if eMatricula else None
                        eUserProfileChangeToken.codigo = code
                        eUserProfileChangeToken.save(usuario_id=ePerfilPrincipal.persona.usuario.id)
                        lifetime = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
                        eUserToken = eUserProfileChangeToken.user_token
                        eUserToken.date_expires = datetime.now() + lifetime
                        eUserToken.save(usuario_id=ePerfilPrincipal.persona.usuario.id)
                        token_access = eUserProfileChangeToken.user_token.token
                        access.payload['connectionToken'] = f"{get_variable('SITE_URL_SGA')}/api/1.0/jwt/changetoken?token={token_access}&code={code}"
                        refresh.payload['connectionToken'] = f"{get_variable('SITE_URL_SGA')}/api/1.0/jwt/changetoken?token={token_access}&code={code}"
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


class MyChangeAcademicPeriodTokenObtainPairView(TokenViewBase):
    serializer_class = MyChangeAcademicPeriodTokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        return Response(serializer.validated_data, status=status.HTTP_200_OK)
