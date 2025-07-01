# -*- coding: latin-1 -*-
#import redis
#import json
from celery_setting import app
from celery import shared_task
from sga.models import Persona
from django.core.cache import cache
from celery.utils.log import get_task_logger
from datetime import datetime, timedelta
from sga.templatetags.sga_extras import encrypt

logger = get_task_logger(__name__)


# @app.task(name='process-demo', bind=True)
# @app.task(name='process-demo')
# @app.task
@shared_task
def demo_task():
    # Coloca aquí el código que deseas ejecutar en segundo plano
    print("Tarea Celery ejecutada")
