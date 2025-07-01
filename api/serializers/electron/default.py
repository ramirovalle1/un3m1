from django.db.models import Q

import settings
from hashlib import md5
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model, authenticate
from rest_framework import exceptions, status, serializers
from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer, PasswordField
from api.helpers.functions_helper import get_variable
from api.helpers.response_herlper import Helper_Response
from api.helpers.serializers_model_helper import Helper_ModelSerializer
from bd.funciones import generate_code
from bd.models import UserToken, UserProfileChangeToken, TemplateBaseSetting, WebSocket, PeriodoGrupo
from matricula.funciones import puede_matricularse_seguncronograma_coordinacion_prematricula, \
    puede_matricularse_seguncronograma_coordinacion
from matricula.models import PeriodoMatricula
from moodle.models import UserAuth
from sga.funciones import variable_valor
from sga.models import Persona, PerfilUsuario, Periodo, Inscripcion, Matricula, ProfesorDistributivoHoras
from sga.templatetags.sga_extras import encrypt
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.settings import api_settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from settings import TIPO_PERIODO_REGULAR


unicode = str
TIEMPO_ENCACHE = 60 * 60


class WebSocketSerializer(Helper_ModelSerializer):

    class Meta:
        model = WebSocket
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class TokenObtainSerializer(serializers.Serializer):
    username_field = get_user_model().USERNAME_FIELD
    token_class = None

    default_error_messages = {
        "no_active_account": u"No se encontró una cuenta activa con las credenciales dadas"
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields[self.username_field] = serializers.CharField()
        self.fields["password"] = PasswordField()

    def validate(self, attrs):
        authenticate_kwargs = {
            self.username_field: attrs[self.username_field],
            "password": attrs["password"],
        }
        try:
            authenticate_kwargs["request"] = self.context["request"]
        except KeyError:
            pass

        self.user = authenticate(**authenticate_kwargs)

        if not api_settings.USER_AUTHENTICATION_RULE(self.user):
            raise exceptions.AuthenticationFailed(self.error_messages["no_active_account"], "no_active_account")

        return {}

    @classmethod
    def get_token(cls, user):
        return cls.token_class.for_user(user)


class TokenObtainPairSerializer(TokenObtainSerializer):
    token_class = RefreshToken

    def validate(self, attrs):
        from django.contrib.auth.models import update_last_login
        data = super().validate(attrs)

        refresh = self.get_token(self.user)

        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)

        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, self.user)

        return data


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        try:
            token = super().get_token(user)
            # Add custom claims
            try:
                ePersona = Persona.objects.get(usuario=user)
            except ObjectDoesNotExist:
                raise NameError('No tiene perfil asignado')
            if not ePersona.tiene_perfil():
                raise NameError('No tiene perfil asignado')
            if not ePersona.es_administrativo() or not ePersona.es_profesor():
                raise NameError('No tiene perfil asignado')
            foto_perfil = ePersona.mi_foto_url()
            api_site_url_sga = get_variable('SITE_URL_SGA')
            if api_site_url_sga:
                foto_perfil = f"{api_site_url_sga}{foto_perfil}"

            ePerfiles = ePersona.perfilusuario_set.filter(Q(administrativo__isnull=False, administrativo__activo=True) | Q(profesor__isnull=False, profesor__activo=True), visible=True)
            if not ePerfiles.values("id").exists():
                raise NameError(u"No tiene perfiles asignados")
            ePerfilPrincipal = None
            if ePerfiles.values("id").filter(administrativo__isnull=False, administrativo__activo=True, persona__usuario__is_superuser=True).exists():
                ePerfilPrincipal = ePerfiles.filter(administrativo__isnull=False, visible=True, administrativo__activo=True).first()
            elif ePerfiles.values("id").filter(profesor__isnull=False, profesor__activo=True).exists():
                ePerfilPrincipal = ePerfiles.filter(profesor__isnull=False, profesor__activo=True).first()

            token['ePerfilPrincipal'] = {
                'id': ePerfilPrincipal.pk,
            }
            ePeriodos = Periodo.objects.none()

            if ePersona.usuario.is_superuser or ePersona.usuario.has_perm('sga.puede_visible_periodo'):
                if ePersona.usuario.is_superuser:
                    ePeriodos = Periodo.objects.all().order_by('-inicio')
                else:
                    periodos_1 = Periodo.objects.filter(visible=True).order_by('-inicio').exclude(pk__in=PeriodoGrupo.objects.values_list('periodo_id', flat=True).filter(visible=True).distinct())
                    periodos_2 = Periodo.objects.filter(pk__in=PeriodoGrupo.objects.values_list('periodo_id', flat=True).filter(grupos__in=ePersona.usuario.groups.all())).order_by('-inicio')
                    periodos_3 = Periodo.objects.filter(pk__in=PeriodoGrupo.objects.values_list('periodo_id', flat=True).filter(grupos__isnull=True)).order_by('-inicio')
                    ePeriodos = periodos_1 | periodos_2 | periodos_3
            else:
                periodos_1 = Periodo.objects.filter(visible=True).order_by('-inicio').exclude(pk__in=PeriodoGrupo.objects.values_list('periodo_id', flat=True).filter(visible=True).distinct())
                periodos_2 = Periodo.objects.filter(pk__in=PeriodoGrupo.objects.values_list('periodo_id', flat=True).filter(grupos__in=ePersona.usuario.groups.all())).order_by('-inicio')
                periodos_3 = Periodo.objects.filter(pk__in=PeriodoGrupo.objects.values_list('periodo_id', flat=True).filter(grupos__isnull=True)).order_by('-inicio')
                ePeriodos = periodos_1 | periodos_2 | periodos_3
            aPeriodos = []
            for ePeriodo in ePeriodos:
                aPeriodos.append({"id": ePeriodo.pk,
                                  "nombre_completo": ePeriodo.nombre})
            token['ePeriodos'] = aPeriodos
            ePeriodo = None
            if Periodo.objects.values('id').filter(tipo=TIPO_PERIODO_REGULAR, inicio__lte=datetime.now().date(), activo=True, fin__gte=datetime.now().date()).exists():
                if Periodo.objects.values('id').filter(tipo=TIPO_PERIODO_REGULAR, activo=True, inicio__lte=datetime.now().date(), fin__gte=datetime.now().date()).order_by('id').count()>1:
                    ePeriodo = Periodo.objects.filter(tipo=TIPO_PERIODO_REGULAR, activo=True,marcardefecto=True, inicio__lte=datetime.now().date(),fin__gte=datetime.now().date()).order_by('id')[0] if Periodo.objects.filter(tipo=TIPO_PERIODO_REGULAR, activo=True,marcardefecto=True, inicio__lte=datetime.now().date(),fin__gte=datetime.now().date()).exists() else None
                else:
                    ePeriodo = Periodo.objects.filter(tipo=TIPO_PERIODO_REGULAR, activo=True, inicio__lte=datetime.now().date(), fin__gte=datetime.now().date()).order_by('id')[0] if Periodo.objects.filter(tipo=TIPO_PERIODO_REGULAR, activo=True, inicio__lte=datetime.now().date(), fin__gte=datetime.now().date()).exists() else None
            else:
                ePeriodo = None
            if ePeriodo is None:
                if Periodo.objects.values('id').filter(tipo=TIPO_PERIODO_REGULAR, activo=True, inicio_agregacion__lte=datetime.now().date()).exists():
                    ePeriodo = Periodo.objects.filter(tipo=TIPO_PERIODO_REGULAR, activo=True, inicio_agregacion__lte=datetime.now().date()).order_by('-inicio_agregacion')[0]
                elif Periodo.objects.values('id').filter(tipo=TIPO_PERIODO_REGULAR, activo=True, fin__lte=datetime.now().date()).exists():
                    ePeriodo = Periodo.objects.filter(tipo=TIPO_PERIODO_REGULAR, activo=True, fin__lte=datetime.now().date()).order_by('-fin')[0]
                else:
                    ePeriodo = Periodo.objects.filter(tipo=TIPO_PERIODO_REGULAR, activo=True).order_by('-fin')[0]
            token['ePeriodo'] = {"id": ePeriodo.pk,
                                  "nombre_completo": ePeriodo.nombre}

            token['ePersona'] = {
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
            token['eUser'] = {
                'username': user.username,
            }

            return token
        except TokenError as e:
            raise InvalidToken(e.args[0])


class MyTokenRefreshSerializer(TokenRefreshSerializer):

    def validate(self, attrs):
        refresh = RefreshToken(attrs['refresh'])
        access = refresh.access_token
        # a = AccessToken()
        data = {}
        if api_settings.ROTATE_REFRESH_TOKENS:
            if api_settings.BLACKLIST_AFTER_ROTATION:
                try:
                    pass
                    #refresh.blacklist()
                except AttributeError:
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
