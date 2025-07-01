#!/usr/bin/env python

import sys
import os

from sga.tasks import send_html_mail

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from datetime import datetime
from sga.models import Profesor, miinstitucion, Materia, LogEntryBackupdos
from django.contrib.admin.models import LogEntry


# totallog = LogEntry.objects.all().count()
totallog = LogEntry.objects.filter(action_time__lte='2020-12-31')
total = totallog.count()
contador = 0
for pasarlog in totallog:
    respaldo = LogEntryBackupdos(id=pasarlog.id,
                              action_time=pasarlog.action_time,
                              user=pasarlog.user,
                              content_type=pasarlog.content_type,
                              object_id=pasarlog.object_id,
                              object_repr=pasarlog.object_repr,
                              action_flag=pasarlog.action_flag,
                              change_message=pasarlog.change_message)
    respaldo.save()
    pasarlog.delete()
    contador = contador + 1
    print(str(contador) + ' de '+ str(total))
# LogEntryBackup

