from django.urls import re_path
# from faceid import views_copy
from faceid.views import marcadas, adm_gestion_marcadas, adm_registro_marcadas
# from faceid import views_c
# from faceid import face_detector
# from faceid.views import my_faceid
# from faceid.views import biometrics

urlpatterns = [
    # re_path(r'^adm_marcadas$', adm_marcadas.view, name='adm_marcadas_view'),
    # re_path(r'^my_faceid$', my_faceid.view, name='my_faceid'),
    # re_path(r'^biometrics$', biometrics.view, name='my_biometrics'),
    re_path(r'^adm_marcadas$', marcadas.index, name='adm_marcadas_view'),
    # re_path(r'^face_detection/detect/$', face_detector.detect, name='face_detector'),
    # re_path(r'^face_stream$', views_c.index, name='face_stream'),
    # re_path(r'^stream$', views_c.video_feed, name='test_stream')
    # re_path(r'^video_feed$', views.video_feed, name='video_feed')
    re_path(r'^adm_gestion_marcadas$', adm_gestion_marcadas.view, name='adm_gestion_marcadas_view'),
    re_path(r'^adm_registro_marcadas$', adm_registro_marcadas.view, name='adm_registro_marcadas_view'),
]
