
from django.views.i18n import JavaScriptCatalog
from django.urls import re_path

from wpush import misdispositivos, offline
from django.views.decorators.cache import cache_page
from django.utils import timezone
from wpush.views import save_info, ServiceWorkerView
from pwa.views import service_worker, manifest
last_modified_date = timezone.now().strftime("%Y-%m-%d_%H:%M:%S")

urlpatterns = [
    re_path('jsi18n/', cache_page(86400, key_prefix='js18n-%s' % last_modified_date)(JavaScriptCatalog.as_view(packages=['webpush'])), name='javascript-catalog'),
    re_path(r'^webpush/save_information$', save_info, name='save_webpush_info'),
    re_path('service-worker.js', ServiceWorkerView.as_view(), name='service_worker'),
    re_path(r'^my_devices$', misdispositivos.view, name='misdispositivos'),
    re_path(r'serviceworker.js', service_worker, name='serviceworker'),
    re_path(r'^manifest\.json$', manifest, name='manifest'),
    re_path(r'^offline$', offline.view, name='offline'),

]
