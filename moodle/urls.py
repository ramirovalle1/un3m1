from django.urls import re_path
from moodle import silabo

urlpatterns = [re_path(r'^adm_silabo$', silabo.view, name='silabo_view'),
]

