from django.urls import re_path

from poli.views import adm_areaspolideportivo, alu_reservapolideportivo, adm_revisareserva, unemideporte_publico, unemideporte, commonviews, perfil_usuario

urlpatterns = [
    re_path(r'^adm_areaspolideportivo$', adm_areaspolideportivo.view, name='adm_areaspolideportivo'),
    re_path(r'^alu_reservapolideportivo$', alu_reservapolideportivo.view, name='alu_reservapolideportivo'),
    re_path(r'^adm_revisareserva$', adm_revisareserva.view, name='adm_revisareserva'),
    re_path(r'^unemideportes$', unemideporte_publico.view, name='unemideportes'),
    re_path(r'^unemideporte$', unemideporte.view, name='unemideporte'),
    re_path(r'^perfil_usuario$', perfil_usuario.view, name='perfil_usuario'),
    re_path(r'^control_acceso$', commonviews.control_acceso, name='control_acceso'),
    re_path(r'^signout$', commonviews.signout_user, name='signout'),
    re_path(r'^changepass$', commonviews.passwd, name='changepass'),

]
