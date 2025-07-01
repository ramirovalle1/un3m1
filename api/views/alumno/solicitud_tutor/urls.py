from django.urls import re_path, include


from api.views.alumno.solicitud_tutor.pregrado import PregradoAPIView
from api.views.alumno.solicitud_tutor.posgrado import PosgradoAPIView


urlpatterns = [
    re_path(r'^solicitud_tutor/pregrado$', PregradoAPIView.as_view(), name="api_view_solicitud_tutor_pregrado"),
    re_path(r'^solicitud_tutor/posgrado$', PosgradoAPIView.as_view(), name="api_view_solicitud_tutor_posgrado"),
    # re_path(r'^solicitud_tutor/admision$', MatriculaAdmisionAPIView.as_view(), name="api_view_matricula_admision"),
]

