import settings
from hashlib import md5
from datetime import datetime, timedelta
from django.contrib.auth.hashers import make_password
from rest_framework import serializers, exceptions
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from api.helpers.functions_helper import get_variable
from api.helpers.serializers_model_helper import Helper_ModelSerializer
from bd.funciones import generate_code
from bd.models import UserToken, UserProfileChangeToken, TemplateBaseSetting, WebSocket
from matricula.funciones import puede_matricularse_seguncronograma_coordinacion_prematricula
from matricula.models import PeriodoMatricula
from sga.funciones import variable_valor
from sga.models import Persona, PerfilUsuario, Periodo, Inscripcion, Matricula
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist


unicode = str


class WebSocketSerializer(Helper_ModelSerializer):

    class Meta:
        model = WebSocket
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class CodeField(serializers.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('style', {})

        kwargs['style']['input_type'] = 'password'
        kwargs['write_only'] = True

        super().__init__(*args, **kwargs)


class TokenObtainSerializer(serializers.Serializer):

    default_error_messages = {
        'no_active_account': u'No se encontró una cuenta activa con las credenciales dadas'
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['token'] = serializers.CharField()
        self.fields['code'] = CodeField()

    def validate(self, attrs):
        authenticate_kwargs = {'token': attrs['token'],
                               'code': attrs['code']}
        try:
            authenticate_kwargs['request'] = self.context['request']
        except KeyError:
            pass

        token = attrs['token']
        code = attrs['code']
        eUserTokens = UserToken.objects.filter(token=token)
        if not eUserTokens.values("id").exists():
            raise exceptions.AuthenticationFailed(self.error_messages['no_active_account'], 'no_active_account')
        eUserProfileChangeTokens = UserProfileChangeToken.objects.filter(user_token__token=token, isActive=True, user_token__action_type=4, user_token__app=4)
        if not eUserProfileChangeTokens.values("id").filter(codigo=code).exists():
            raise exceptions.AuthenticationFailed(self.error_messages['no_active_account'], 'no_active_account')
        eUserProfileChangeToken = eUserProfileChangeTokens.filter(codigo=code).first()
        if not eUserProfileChangeToken.isValidoCodigo(code):
            raise exceptions.AuthenticationFailed(self.error_messages['no_active_account'], 'no_active_account')
        if not eUserProfileChangeToken.perfil_destino.es_estudiante():
            raise exceptions.AuthenticationFailed(self.error_messages['no_active_account'], 'no_active_account')
        eInscripcion = eUserProfileChangeToken.perfil_destino.inscripcion
        self.user = eInscripcion.persona.usuario
        if self.user is None or not self.user.is_active:
            raise exceptions.AuthenticationFailed(self.error_messages['no_active_account'], 'no_active_account')
        TIEMPO_ENCACHE = 60 * 60
        tokenEnCache = cache.get(f"UserToken_{encrypt(self.user.id)}")
        if tokenEnCache:
            cache.delete(f"UserToken_{encrypt(self.user.id)}")
        eUserToken = eUserTokens.first()
        cache.set(f"UserToken_{encrypt(self.user.id)}", eUserToken, TIEMPO_ENCACHE)
        return {}

    @classmethod
    def get_token(cls, user):
        raise NotImplementedError('Must implement `get_token` method for `TokenObtainSerializer` subclasses')


class TokenObtainPairSerializer(TokenObtainSerializer):

    @classmethod
    def get_token(cls, user):
        return RefreshToken.for_user(user)

    def validate(self, attrs):
        data = super().validate(attrs)

        refresh = self.get_token(self.user)

        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)

        return data


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):
        try:
            token = super().get_token(user)
            # Add custom claims
            try:
                ePersona = Persona.objects.db_manager("sga_select").get(usuario=user)
            except ObjectDoesNotExist:
                raise NameError('No tiene perfil asignado')

            if not ePersona.tiene_perfil() or not ePersona.tiene_perfil_inscripcion_vigente():
                raise NameError('No tiene perfil asignado')

            foto_perfil = ePersona.mi_foto_url()
            api_site_url_sga = get_variable('SITE_URL_SGA')
            if api_site_url_sga:
                foto_perfil = f"{api_site_url_sga}{foto_perfil}"

            if cache.has_key(f"persona_id_{encrypt(ePersona.id)}_perfiles_visible"):
                ePerfilUsuarios = cache.get(f"persona_id_{encrypt(ePersona.id)}_perfiles_visible")
            else:
                ePerfilUsuarios = PerfilUsuario.objects.db_manager("sga_select").filter(status=True, visible=True, inscripcion__isnull=False, persona=ePersona)
                cache.set(f"persona_id_{encrypt(ePersona.id)}_perfiles_visible", ePerfilUsuarios, 60 * 60 * 60)

            perfiles = []
            if cache.has_key(f"login_api_estudiante_persona_id_{encrypt(ePersona.id)}_perfiles"):
                perfiles = cache.get(f"login_api_estudiante_persona_id_{encrypt(ePersona.id)}_perfiles")
            else:
                for ePerfilUsuario in ePerfilUsuarios:
                    perfiles.append({
                        'id': encrypt(ePerfilUsuario.id),
                        'carrera': ePerfilUsuario.tipo()
                    })
                cache.set(f"login_api_estudiante_persona_id_{encrypt(ePersona.id)}_perfiles", perfiles, 60 * 60 * 60)

            eUserToken = cache.get(f"UserToken_{encrypt(user.id)}")
            if not eUserToken:
                raise NameError('Token invalido')
            if not UserToken.objects.values("id").filter(token=eUserToken.token).exists():
                raise NameError('Token invalido')
            eUserProfileChangeTokens = UserProfileChangeToken.objects.filter(user_token__token=eUserToken.token, isActive=True, user_token__action_type=4, user_token__app=4)
            if not eUserProfileChangeTokens.values("id").exists():
                raise NameError('Código del Token invalido')
            eUserProfileChangeToken = eUserProfileChangeTokens.first()
            if not eUserProfileChangeToken.perfil_destino.es_estudiante():
                raise NameError('Token no valido para estudiante')
            # ePerfilPrincipal = ePerfilUsuarios[0]
            ePerfilPrincipal = eUserProfileChangeToken.perfil_destino
            ePeriodo = eUserProfileChangeToken.periodo
            token['perfilprincipal'] = {
                'id': encrypt(ePerfilPrincipal.id),
            }
            eInscripcion = ePerfilPrincipal.inscripcion
            if ePeriodo is None:
                eMatricula = eInscripcion.matricula2()
            else:
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

            token['periodos'] = periodos
            token['inscripcion'] = {"id": encrypt(eInscripcion.id), }
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

            token['coordinacion'] = {"id": encrypt(eInscripcion.coordinacion.id),
                                     "nombre": eInscripcion.coordinacion.nombre,
                                     "alias": eInscripcion.coordinacion.alias,
                                     'clasificacion': clasificacion,
                                     'display_clasificacion': dict(CLASIFICACION)[clasificacion]
                                     }
            token['matricula'] = {"id": encrypt(eMatricula.id) if eMatricula else None, }
            token['periodo'] = {"id": encrypt(eMatricula.nivel.periodo.id) if eMatricula else None,
                                "nombre_completo": eMatricula.nivel.periodo.nombre if eMatricula else None, }

            token['persona'] = {
                'id': encrypt(ePersona.id),
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
                'foto': foto_perfil
            }
            token['user'] = {
                'username': user.username,
            }
            token['perfiles'] = perfiles
            token['app'] = 'sie'
            token['permiteWebPush'] = permiteWebPush = variable_valor('PERMITE_WEBPUSH')
            if permiteWebPush:
                webpush_settings = getattr(settings, 'WEBPUSH_SETTINGS', {})
                vapid_key = webpush_settings.get('VAPID_PUBLIC_KEY')
                token['vapid_key'] = vapid_key


            fecha = datetime.now().date()
            hora = datetime.now().time()
            fecha_hora = fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + \
                         hora.minute.__str__() + hora.second.__str__()
            code = generate_code(32)
            token_access = md5(str(encrypt(user.id) + fecha_hora).encode("utf-8")).hexdigest()
            lifetime = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
            UserToken.objects.filter(user=user, action_type=4, app=1, usuario_creacion=ePersona.usuario).delete()
            eUserToken = UserToken(user=user,
                                   token=token_access,
                                   action_type=4,
                                   date_expires=datetime.now() + lifetime,
                                   app=1,
                                   isActive=True
                                   )
            eUserToken.save(usuario_id=ePersona.usuario.id)
            perfilprincipal_origen = ePerfilPrincipal
            perfilprincipal_destino = ePerfilPrincipal
            if not perfilprincipal_destino:
                raise NameError('No tiene perfil asignado')
            if not UserProfileChangeToken.objects.values("id").filter(perfil_origen__persona=ePersona, perfil_destino__persona=ePersona, app=1, isActive=True).exists():
                eUserProfileChangeToken = UserProfileChangeToken(perfil_origen=perfilprincipal_origen,
                                                                 perfil_destino=perfilprincipal_destino,
                                                                 user_token=eUserToken,
                                                                 codigo=code,
                                                                 isActive=True,
                                                                 app=1,
                                                                 periodo=eMatricula.nivel.periodo if eMatricula else None
                                                                 )
                eUserProfileChangeToken.save(usuario_id=ePersona.usuario.id)
            else:
                eUserProfileChangeToken = UserProfileChangeToken.objects.filter(perfil_origen__persona=ePersona, perfil_destino__persona=ePersona, app=1, isActive=True)[0]
                eUserProfileChangeToken.codigo = code
                eUserProfileChangeToken.user_token = eUserToken
                eUserProfileChangeToken.save(usuario_id=ePersona.usuario.id)
            token['connectionToken'] = f"{get_variable('SITE_URL_SGA')}/api/1.0/jwt/changetoken?token={token_access}&code={code}"
            eTemplateBaseSetting = None
            if TemplateBaseSetting.objects.values("id").filter(status=True, app=4).exists():
                eTemplateBaseSetting = TemplateBaseSetting.objects.filter(status=True, app=4)[0]
            if eTemplateBaseSetting:
                token['templatebasesetting'] = {
                    'name_system': eTemplateBaseSetting.name_system,
                    'app': eTemplateBaseSetting.app,
                    'use_menu_favorite_module': eTemplateBaseSetting.use_menu_favorite_module,
                    'use_menu_notification': eTemplateBaseSetting.use_menu_notification,
                    'use_menu_user_manual': eTemplateBaseSetting.use_menu_user_manual,
                    'use_api': eTemplateBaseSetting.use_api,
                    }
            else:
                token['templatebasesetting'] = None
            token['websocket'] = None
            if WebSocket.objects.values('id').filter(habilitado=True, api=True).exists():
                eWebSocket = WebSocket.objects.filter(habilitado=True, api=True).first()
                token['websocket'] = WebSocketSerializer(eWebSocket).data
            return token
        except TokenError as e:
            raise InvalidToken(e.args[0])

