from django.db.models import Exists, OuterRef

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
from bd.models import UserToken, UserProfileChangeToken, TemplateBaseSetting, WebSocket
from matricula.funciones import puede_matricularse_seguncronograma_coordinacion_prematricula, \
    puede_matricularse_seguncronograma_coordinacion
from matricula.models import PeriodoMatricula, SolicitudReservaCupoMateria,DetalleSolicitudReservaCupoMateria
from moodle.models import UserAuth
from sga.funciones import variable_valor
from sga.models import Persona, PerfilUsuario, Periodo, Inscripcion, Matricula, RetiroCarrera
from sga.templatetags.sga_extras import encrypt
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.settings import api_settings
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist


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
        user = self.user
        if user:
            try:
                usermoodle = UserAuth.objects.get(usuario=user)
                isUpdateUserMoodle = False
                if not usermoodle.check_password(attrs["password"]) or usermoodle.check_data():
                    if not usermoodle.check_password(attrs["password"]):
                        usermoodle.set_password(attrs["password"])
                    usermoodle.save()
            except ObjectDoesNotExist:
                usermoodle = UserAuth(usuario=user)
                usermoodle.set_data()
                usermoodle.set_password(attrs["password"])
                usermoodle.save()

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
                ePerfilUsuarios = PerfilUsuario.objects.db_manager("sga_select").filter(status=True, visible=True, inscripcion__isnull=False, persona=ePersona).order_by('-inscripcionprincipal', '-id')
                cache.set(f"persona_id_{encrypt(ePersona.id)}_perfiles_visible", ePerfilUsuarios, 60 * 60 * 60)

            perfiles = []
            if cache.has_key(f"login_api_estudiante_persona_id_{encrypt(ePersona.id)}_perfiles"):
                perfiles = cache.get(f"login_api_estudiante_persona_id_{encrypt(ePersona.id)}_perfiles")
            else:
                for ePerfilUsuario in ePerfilUsuarios:
                    clasif = 0
                    display_clasif = ''
                    if ePerfilUsuario.inscripcion.coordinacion_id == 9:
                        clasif = 3
                        display_clasif = 'Nivelación'
                    elif ePerfilUsuario.inscripcion.coordinacion_id in [7, 10]:
                        clasif = 2
                        display_clasif = 'Posgrado'
                    elif ePerfilUsuario.inscripcion.coordinacion_id in [1, 2, 3, 4, 5]:
                        clasif = 1
                        display_clasif = 'Grado'
                    perfiles.append({
                        'id': encrypt(ePerfilUsuario.id),
                        'carrera': ePerfilUsuario.tipo(),
                        'clasificacion': clasif,
                        'display_clasificacion': display_clasif
                    })
                cache.set(f"login_api_estudiante_persona_id_{encrypt(ePersona.id)}_perfiles", perfiles, 60 * 60 * 60)

            ePerfilPrincipal = ePerfilUsuarios[0]
            token['perfilprincipal'] = {
                'id': encrypt(ePerfilPrincipal.id),
            }
            eInscripcion = ePerfilPrincipal.inscripcion
            eMatricula = eInscripcion.matricula2()

            if cache.has_key(f"inscripcion_id_{encrypt(eInscripcion.id)}_periodos"):
                ePeriodos = cache.get(f"inscripcion_id_{encrypt(eInscripcion.id)}_periodos")
            else:
                ePeriodos = Periodo.objects.db_manager("sga_select").filter(nivel__matricula__inscripcion=eInscripcion, status=True, nivel__status=True, nivel__matricula__status=True, nivel__matricula__inscripcion__status=True).order_by('-inicio')
                cache.set(f"inscripcion_id_{encrypt(eInscripcion.id)}_periodos", ePeriodos, 60 * 60 * 60)

            # tipo_val = 0
            cordinacionid = eInscripcion.carrera.coordinacion_carrera().id
            if cordinacionid == 9:
                tipo_val = 1
                if (ePeriodoMatricula := PeriodoMatricula.objects.filter(status=True, tipo=tipo_val, valida_login=True).first()) is not None:
                    periodo = ePeriodoMatricula.periodo
                    if tipo_val == 1:
                        if Matricula.objects.values("id").filter(inscripcion=eInscripcion, nivel__periodo=periodo).exists() and Matricula.objects.values("id").filter(inscripcion__persona=ePersona).count() == 1:
                            raise NameError('Estimado aspirante su acceso al SGA está restringido. Para rendir su test o examen ingrese al enlace https://aulanivelacion.unemi.edu.ec/login/index.php.')
            periodos = []
            if cache.has_key(f"login_api_estudiante_inscripcion_id_{encrypt(eInscripcion.id)}_periodos"):
                periodos = cache.get(f"login_api_estudiante_inscripcion_id_{encrypt(eInscripcion.id)}_periodos")
            else:
                for periodo in ePeriodos:
                    periodos.append({"id": encrypt(periodo.id),
                                     "nombre_completo": periodo.nombre})
                cache.set(f"login_api_estudiante_inscripcion_id_{encrypt(eInscripcion.id)}_periodos", periodos, 60 * 60 * 60)

            token['periodos'] = periodos

            eSesion = {}
            if (_eSesion := eInscripcion.sesion) is not None:
                _imagen = None
                if _eSesion.id in [1, 9]: #Matutina
                  _imagen = f"{get_variable('SITE_URL_SGA')}/static/logos/jornada_matutina.svg"
                elif _eSesion.id in [4]: #VESPERTINA
                  _imagen = f"{get_variable('SITE_URL_SGA')}/static/logos/jornada_vespertino.svg"
                elif _eSesion.id in [5, 10]: #NOCTURNA
                  _imagen = f"{get_variable('SITE_URL_SGA')}/static/logos/jornada_nocturna.svg"
                elif _eSesion.id in [13, 16]: #EN LINEA
                  _imagen = f"{get_variable('SITE_URL_SGA')}/static/logos/jornada_en_linea.svg"
                elif _eSesion.id in [7, 8, 11, 12]: #FIN DE SEMANA
                  _imagen = f"{get_variable('SITE_URL_SGA')}/static/logos/jornada_fin_semana.svg"
                else: #SIN DEFINIR
                  _imagen = f"{get_variable('SITE_URL_SGA')}/static/logos/jornada_fin_semana.svg"
                eSesion = {
                    'id': encrypt(_eSesion.id),
                    'nombre': _eSesion.nombre_display().lower(),
                    'imagen': _imagen
                }
            eModalidad = {}
            if (eMalla := eInscripcion.mi_malla()) is not None:
                if (_eModalidad := eMalla.modalidad) is not None:
                    eModalidad = {
                        'id': encrypt(_eModalidad.id),
                        'nombre': _eModalidad.nombre.lower(),
                        'tipo': _eModalidad.id
                    }

            token['inscripcion'] = {
                "id": encrypt(eInscripcion.id),
                "seccion": eSesion,
                "modalidad": eModalidad,
                "isGraduado": eInscripcion.es_graduado(),
                "isEgresado": eInscripcion.egresado(),
            }
            CLASIFICACION = (
                (1, u'PREGRADO'),
                (2, u'POSGRADO'),
                (3, u'ADMISION'),
            )
            cordinacionid = eInscripcion.carrera.coordinacion_carrera().id
            clasificacion = 0
            tipo_val = 0
            if cordinacionid == 9:
                clasificacion = 3
                tipo_val = 1
            elif cordinacionid in [7, 10]:
                clasificacion = 2
                tipo_val = 3
            elif cordinacionid in [1, 2, 3, 4, 5]:
                clasificacion = 1
                tipo_val = 2
            # print(cls)

            #### SOLO HABILITAR EN EL PROCESO DE MATRICULA
            if variable_valor('BLOQUEO_LOGIN_MATRICULA'):
                if not ePersona.es_administrativo() and not ePersona.es_profesor():
                    if ePersona.es_estudiante():
                        # periodomatricula = None
                        id_periodo_login_matricula = variable_valor('ID_BLOQUEO_LOGIN_MATRICULA')
                        if id_periodo_login_matricula is None:
                            id_periodo_login_matricula = 0
                        _eInscripcion = eInscripcion
                        _ePeriodoMatriculas = PeriodoMatricula.objects.filter(status=True, tipo=tipo_val, valida_login=True, periodo_id=id_periodo_login_matricula)
                        if (_ePeriodoMatricula := _ePeriodoMatriculas.filter(activo=True, valida_cronograma=True).first()) is not None:
                            if _ePeriodoMatricula.valida_cronograma and _ePeriodoMatricula.valida_login and _ePeriodoMatricula.tiene_cronograma_coordinaciones():
                                _ePeriodo = _ePeriodoMatricula.periodo
                                cronograma = _ePeriodoMatricula.cronograma_coordinaciones()
                                if cordinacionid in list(cronograma.values_list('coordinacion_id', flat=True)):
                                    dc = cronograma.filter(coordinacion_id=cordinacionid)[0]
                                    if not dc.activo:
                                        raise NameError(f'Estimado estudiante, estamos teniendo intermitencia en nuestros servicios, intentelo mas tarde...')
                                    elif not puede_matricularse_seguncronograma_coordinacion(_eInscripcion, _ePeriodo):
                                        raise NameError(f'{"Estimada" if ePersona.es_mujer() else "Estimado"} estudiante, de acuerdo al cronograma de su matriculación no se encuentra activa.')
                        if _ePeriodoMatriculas.values("id").exists():
                            _ePeriodoMatricula = _ePeriodoMatriculas[0]
                            _ePeriodo = _ePeriodoMatricula.periodo
                            tiene_automatricula = False
                            if tipo_val == 1:
                                tiene_automatricula = _eInscripcion.tiene_automatriculaadmision_por_confirmar(_ePeriodo)
                            elif tipo_val == 2:
                                valida_login_con_matricula = variable_valor('VALIDA_LOGIN_CON_MATRICULA')
                                if valida_login_con_matricula:
                                    tiene_automatricula = _eInscripcion.tiene_automatriculapregrado_por_confirmar(_ePeriodo)
                                    if not tiene_automatricula and Matricula.objects.values('id').filter(inscripcion=_eInscripcion, nivel__periodo=_ePeriodo, termino=True).exists():
                                        raise NameError(f"{'Estimada' if ePersona.es_mujer() else 'Estimado'} {ePersona.__str__()} ya se encuentra {'matriculada' if ePersona.es_mujer() else 'matriculado'}")
                                    if DetalleSolicitudReservaCupoMateria.objects.filter(status=True,solicitud__inscripcion = _eInscripcion).exists():
                                        raise NameError(f"{'Estimada' if ePersona.es_mujer() else 'Estimado'} {ePersona.__str__()} ya realizó una solicitud de cupo")

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
            fecha_hora = fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__()
            code = generate_code(32)
            token_access = md5(str(encrypt(user.id) + fecha_hora).encode("utf-8")).hexdigest()
            UserToken.objects.filter(user=user, action_type=4, app=1, usuario_creacion=ePersona.usuario).delete()
            lifetime = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
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
                eUserProfileChangeToken = UserProfileChangeToken(perfil_origen_id=perfilprincipal_origen.id if perfilprincipal_origen else None,
                                                                 perfil_destino_id=perfilprincipal_destino.id if perfilprincipal_destino else None,
                                                                 user_token_id=eUserToken.id if eUserToken else None,
                                                                 codigo=code,
                                                                 isActive=True,
                                                                 app=1,
                                                                 periodo_id=eMatricula.nivel.periodo.id if eMatricula else None
                                                                 )
                eUserProfileChangeToken.save(usuario_id=ePersona.usuario.id)
            else:
                eUserProfileChangeToken = UserProfileChangeToken.objects.filter(perfil_origen__persona=ePersona, perfil_destino__persona=ePersona, app=1, isActive=True)[0]
                eUserProfileChangeToken.codigo = code
                eUserProfileChangeToken.user_token = eUserToken
                eUserProfileChangeToken.save(usuario_id=ePersona.usuario.id, update_fields=['codigo', 'user_token'])
            token['connectionToken'] = f"{get_variable('SITE_URL_SGA')}/api/1.0/jwt/changetoken?token={token_access}&code={code}"
            if cache.has_key(f"template_base_setting_app_sie_serializer"):
                token['templatebasesetting'] = cache.get(f"template_base_setting_app_sie_serializer")
            else:
                templatebasesetting = {}
                if (eTemplateBaseSetting := TemplateBaseSetting.objects.db_manager("sga_select").filter(status=True, app=4).first()) is not None:
                    templatebasesetting = {
                        'id': encrypt(eTemplateBaseSetting.id),
                        'name_system': eTemplateBaseSetting.name_system,
                        'app': eTemplateBaseSetting.app,
                        'use_menu_favorite_module': eTemplateBaseSetting.use_menu_favorite_module,
                        'use_menu_notification': eTemplateBaseSetting.use_menu_notification,
                        'use_menu_user_manual': eTemplateBaseSetting.use_menu_user_manual,
                        'use_api': eTemplateBaseSetting.use_api,
                        }
                cache.set(f"template_base_setting_app_sie_serializer", templatebasesetting, 60 * 60 * 60 * 60)
                token['templatebasesetting'] = templatebasesetting
            if cache.has_key(f"web_socket_api_serializer"):
                token['websocket'] = cache.get(f"web_socket_api_serializer")
            else:
                if (eWebSocket := WebSocket.objects.db_manager("sga_select").filter(habilitado=True, api=True).first()) is not None:
                    eWebSocket = WebSocketSerializer(eWebSocket).data
                else:
                    eWebSocket = {}
                cache.set(f"web_socket_api_serializer", eWebSocket, 60 * 60 * 60 * 60)
                token['websocket'] = eWebSocket

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
                    if cache.has_key(f"perfilprincipal_id_{access.payload['perfilprincipal']['id']}"):
                        ePerfilUsuario = cache.get(f"perfilprincipal_id_{access.payload['perfilprincipal']['id']}")
                    else:
                        ePerfilUsuario = PerfilUsuario.objects.db_manager("sga_select").get(pk=encrypt(access.payload['perfilprincipal']['id']))
                        cache.set(f"perfilprincipal_id_{access.payload['perfilprincipal']['id']}", ePerfilUsuario, TIEMPO_ENCACHE)

                    if UserProfileChangeToken.objects.db_manager("sga_select").values("id").filter(perfil_origen=ePerfilUsuario, perfil_destino=ePerfilUsuario, app=1, isActive=True).exists():
                        code = generate_code(32)
                        eUserProfileChangeToken = UserProfileChangeToken.objects.filter(perfil_origen=ePerfilUsuario, perfil_destino=ePerfilUsuario, app=1, isActive=True)[0]
                        eUserProfileChangeToken.codigo = code
                        eUserProfileChangeToken.save(usuario_id=ePerfilUsuario.persona.usuario.id, update_fields=['codigo'])
                        lifetime = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
                        eUserToken = eUserProfileChangeToken.user_token
                        eUserToken.date_expires = datetime.now() + lifetime
                        eUserToken.save(usuario_id=ePerfilUsuario.persona.usuario.id, update_fields=['date_expires'])
                        token_access = eUserProfileChangeToken.user_token.token
                        access.payload['connectionToken'] = f"{get_variable('SITE_URL_SGA')}/api/1.0/jwt/changetoken?token={token_access}&code={code}"
                        refresh.payload['connectionToken'] = f"{get_variable('SITE_URL_SGA')}/api/1.0/jwt/changetoken?token={token_access}&code={code}"
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
