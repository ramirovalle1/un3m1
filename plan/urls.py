from django.urls import re_path

from plan import th_plancarrera

urlpatterns = [
    re_path(r'^th_plancarrera$', th_plancarrera.view, name='th_plancarrera_view'),

]