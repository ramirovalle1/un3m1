from django.urls import path, include

urlpatterns = [
    path(r'^provider/', include('oauth2.provider.urls')),
]
