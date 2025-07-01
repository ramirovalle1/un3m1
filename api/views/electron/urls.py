from django.urls import re_path
from api.jwt.electron.login import LogoutView, MyTokenObtainPairView, LogoutAllView


urlpatterns = [
    re_path(r'^logout$', LogoutView.as_view(), name='api_view_logout'),
    re_path(r'^logout_all$', LogoutAllView.as_view(), name='api_view_logout_all'),
    re_path(r'^token/login$', MyTokenObtainPairView.as_view(), name="api_view_token"),

]
