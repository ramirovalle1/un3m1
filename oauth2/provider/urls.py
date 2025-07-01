from django.urls import path, include
from oauth2_provider.views import AuthorizationView, TokenView, RevokeTokenView, ApplicationList, \
    ApplicationRegistration, ApplicationDetail, ApplicationUpdate, AuthorizedTokensListView, \
    AuthorizedTokenDeleteView, ApplicationDelete

from settings import DEBUG
from oauth2.provider.views.login import login_user, logout_user

# OAuth2 provider endpoints
oauth2_endpoint_views = [
    path(r'^authorize$', AuthorizationView.as_view(), name="authorize"),
    path(r'^token$', TokenView.as_view(), name="token"),
    path(r'^revoke_token$', RevokeTokenView.as_view(), name="revoke-token"),
]

if DEBUG:
    # OAuth2 Application Management endpoints

    oauth2_endpoint_views += [
        path(r'^applications/$', ApplicationList.as_view(), name="list"),
        path(r'^applications/register/$', ApplicationRegistration.as_view(), name="register"),
        path(r'^applications/(?P<pk>[\w-]+)/$', ApplicationDetail.as_view(), name="detail"),
        path(r'^applications/(?P<pk>[\w-]+)/delete/$', ApplicationDelete.as_view(), name="delete"),
        path(r'^applications/(?P<pk>[\w-]+)/update/$', ApplicationUpdate.as_view(), name="update"),
        # OAuth2 Token Management endpoints
        path(r'^authorized_tokens/$', AuthorizedTokensListView.as_view(), name="authorized-token-list"),
        path(r'^authorized_tokens/(?P<pk>[\w-]+)/delete/$', AuthorizedTokenDeleteView.as_view(), name="authorized-token-delete"),
    ]

urlpatterns = [
    #path(r'^', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path(r'^', include((oauth2_endpoint_views, 'oauth2_provider'), namespace="oauth2_provider")),
    #path(r'^api/hello', ApiEndpoint.as_view()),  # an example resource endpoint
    path(r'^login$', login_user, name='login_user'),
    path(r'^logout$', logout_user, name='logout_user'),
    #path(r'^profile/view/<int:pk>/', ProfileView.as_view(), name='profile-view'),
    #path(r'^profile/', profile, name='profile'),
]
