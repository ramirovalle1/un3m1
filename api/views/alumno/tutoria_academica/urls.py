from django.urls import re_path, include


from api.views.alumno.tutoria_academica.index import TutoriaAcademicaAPIView


urlpatterns = [
    re_path(r'^tutoria_academica$', TutoriaAcademicaAPIView.as_view(), name="api_view_tutoria_academica"),
]

