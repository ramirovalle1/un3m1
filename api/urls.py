from django.urls import re_path, include

from api.jwt.recoverypassword import RecoveryPasswordAPIView
from api.jwt.refresh import MyTokenRefreshView
from api.views.changepassword import ChangePasswordAPIView
from api.views.changeprofile import ChangeProfileAPIView
from api.views.push_notification import saveInfoNotificationAPIView
from api.views.reporte import RunAPIView
from api.views.version import VersionView
from api.jwt.login import LogoutView, MyTokenObtainPairView, LogoutAllView
from api.jwt.changecareer import MyChangeCareerTokenObtainPairView
from api.jwt.changeademicperiod import MyChangeAcademicPeriodTokenObtainPairView
from api.jwt.changeprofile import MyProfileTokenObtainPairView
from api.jwt.token import CheckTokenView, TokenLoginView
from api.views.user import profile
from api.commonviews import changeTokenUser
from api.oauth2.login import login_user, logout_user
from oauth2_provider.views import AuthorizationView, TokenView, RevokeTokenView, ApplicationList, \
    ApplicationRegistration, ApplicationDetail, ApplicationUpdate, AuthorizedTokensListView, \
    AuthorizedTokenDeleteView, ApplicationDelete
from rest_framework_simplejwt.views import TokenVerifyView
from settings import DEBUG
from .lookproxy.views import LoginLookProxyView
from api.views.data import DataModelAPIView
from api.views.acceso_examen import AccesoExamenAPIView
from .views.alumno.login.panel import CronogramaMatriulaAPIView
from .views.consultas.consultas import EmailAPIView
from .views.telefonia.directorio import DistributivoPersonaLista
from .odilo.odilo_controlador import OdiloConsumidor
# OAuth2 provider endpoints


oauth2_endpoint_views = [
    re_path(r'^login$', login_user, name='login_user'),
    re_path(r'^logout$', logout_user, name='logout_user'),
    re_path(r'^authorize$', AuthorizationView.as_view(), name="authorize"),
    re_path(r'^token$', TokenView.as_view(), name="token"),
    re_path(r'^revoke_token$', RevokeTokenView.as_view(), name="revoke-token"),
]

if DEBUG:
    # OAuth2 Application Management endpoints

    oauth2_endpoint_views += [
        re_path(r'^applications/$', ApplicationList.as_view(), name="list"),
        re_path(r'^applications/register/$', ApplicationRegistration.as_view(), name="register"),
        re_path(r'^applications/(?P<pk>[\w-]+)/$', ApplicationDetail.as_view(), name="detail"),
        re_path(r'^applications/(?P<pk>[\w-]+)/delete/$', ApplicationDelete.as_view(), name="delete"),
        re_path(r'^applications/(?P<pk>[\w-]+)/update/$', ApplicationUpdate.as_view(), name="update"),
        # OAuth2 Token Management endpoints
        re_path(r'^authorized_tokens/$', AuthorizedTokensListView.as_view(), name="authorized-token-list"),
        re_path(r'^authorized_tokens/(?P<pk>[\w-]+)/delete/$', AuthorizedTokenDeleteView.as_view(), name="authorized-token-delete"),
    ]

jwt_views = [
    # re_path(r'^demo_login$', token.view, name='api_view_demo_login'),
    # re_path(r'^demo_nologin$', token.some_view, name='api_view_demo_nologin'),
    # re_path(r'^login$', LoginView.as_view(), name='api_view_login'),
    re_path(r'^logout$', LogoutView.as_view(), name='api_view_logout'),
    re_path(r'^logout_all$', LogoutAllView.as_view(), name='api_view_logout_all'),
    re_path(r'^token/login$', MyTokenObtainPairView.as_view(), name="api_view_token"),
    re_path(r'^changetoken$', changeTokenUser, name="api_view_change_profile_login"),
    re_path(r'^token/refresh$', MyTokenRefreshView.as_view(), name="api_view_token_refresh"),
    re_path(r'^token/verify$', TokenVerifyView.as_view(), name='api_view_token_verify'),
    re_path(r'^token/check$', CheckTokenView.as_view(), name="api_view_token_check"),
    re_path(r'^token/logincheck$', TokenLoginView.as_view(), name="api_view_token_check"),
    re_path(r'^token/change/career$', MyChangeCareerTokenObtainPairView.as_view(), name="api_view_token_change_career"),
    re_path(r'^token/change/academic_period$', MyChangeAcademicPeriodTokenObtainPairView.as_view(), name="api_view_token_change_academic_period"),
    re_path(r'^token/change/profile$', MyProfileTokenObtainPairView.as_view(), name="api_view_token_change_profile"),
    re_path(r'^token/recoverypassword$', RecoveryPasswordAPIView.as_view(), name="api_view_recovery_password"),
    re_path(r'^changepassword$', ChangePasswordAPIView.as_view(), name="api_view_change_password"),
    # re_path(r'^changeprofile$', ChangeProfileAPIView.as_view(), name="api_view_change_picture_profile"), #DESPUES ELIMINAR
    re_path(r'^changepicture$', ChangeProfileAPIView.as_view(), name="api_view_change_picture_profile"),
    re_path(r'^report/run$', RunAPIView.as_view(), name="api_view_report_run"),
    re_path(r'^webpush/save_information_notification$', saveInfoNotificationAPIView.as_view(), name='api_view_webpush_notification'),
    re_path(r'^model/data$', DataModelAPIView.as_view(), name='api_view_data_model'),
    re_path(r'^acceso-examen$', AccesoExamenAPIView.as_view(), name="api_view_acceso_examen"),
    re_path(r'^cronograma$', CronogramaMatriulaAPIView.as_view(), name="api_view_cronograma_matricula"),
    re_path(r'^alumno/', include('api.views.alumno.urls')),
    re_path(r'^electron/', include('api.views.electron.urls')),
]


urlpatterns = [
    re_path(r'^v$', VersionView.as_view(), name='api_view_version'),
    re_path(r'^telefonia/', include('api.views.telefonia.urls')),
    re_path(r'^jwt/', include((jwt_views, 'jwt_views'), namespace="jwt_views")),
    re_path(r'^oauth/2/', include((oauth2_endpoint_views, 'oauth2_provider'), namespace="oauth2_provider")),
    re_path(r'^accounts/profile/', profile, name='profile'),
    re_path(r'^login/lookproxy$', LoginLookProxyView.as_view(), name="api_lookproxy_login"),
    re_path(r'^login/odilo$', LoginLookProxyView.as_view(), name="api_lookproxy_login"),
    re_path(r'^odilo$', OdiloConsumidor, name="odilo-api"),
    re_path(r'^wu/', include('api.views.wu.urls')),
    re_path(r'^services_email/(?P<correo>.+)/$', EmailAPIView.as_view(), name="api_view_email"),
    #re_path(r'^oauth/2/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    #re_path(r'^users/', UserList.as_view()),
    #re_path(r'^users/<pk>/', UserDetails.as_view()),
    #re_path(r'^groups/', GroupList.as_view()),
]
