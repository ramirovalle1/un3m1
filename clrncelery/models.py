# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


from celery.backends.base import BaseBackend
from django.db import models
from django.db.models import Q
from django.db.models.query import QuerySet
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from celery.result import AsyncResult
from celery.utils import uuid
from celery import signals
from sga.funciones import ModeloBase
from sga.models import Persona

# from django.contrib.auth.models import User


TYPE_APP_LABEL = (
    (1, u'sga'),
    (2, u'sagest'),
    (3, u'posgrado')
)


# Crea un modelo de Django para almacenar los resultados
class TaskResult(models.Model):
    task_id = models.CharField(unique=True, max_length=255)
    result = models.BinaryField()
    status = models.CharField(max_length=50)
    traceback = models.TextField(null=True, blank=True)


class CustomDatabaseBackend(BaseBackend):
    def __init__(self, app, *args, **kwargs):
        super().__init__(app, *args, **kwargs)

    def _store_result(self, task_id, result, state, traceback=None):
        """
        Almacena el resultado de la tarea en la base de datos.
        """
        # Guarda el resultado en la base de datos
        TaskResult.objects.create(task_id=task_id, result=result, status=state, traceback=traceback)

    def get_result(self, task_id):
        """
        Recupera el resultado de la tarea desde la base de datos.
        """
        try:
            result = TaskResult.objects.get(task_id=task_id)
            return result.result
        except TaskResult.DoesNotExist:
            return None


class BatchTasks(ModeloBase):
    title = models.CharField(verbose_name=u'Titulo de la Tarea', max_length=300)
    body = models.CharField(verbose_name=u'Cuerpo de la Tarea', max_length=500)
    person = models.ForeignKey('sga.persona',on_delete=models.CASCADE, verbose_name=u'Persona')
    url = models.CharField(verbose_name=u'URL de enlace directo', max_length=300, null=True, blank=True)
    task_id = models.CharField(verbose_name=u'ID de la Tarea', max_length=100)
    task_name = models.CharField(verbose_name=u'Nombre de la Tarea', max_length=200, null=True, blank=True)
    app_label = models.IntegerField(choices=TYPE_APP_LABEL, null=True, blank=True, verbose_name=u'Tipo de Aplicación')
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, verbose_name=u'Tipo de Contenido', blank=True, null=True)
    # object_id = models.PositiveIntegerField(u'Object id')
    # content_object = GenericForeignKey('content_type', 'object_id')

    def statusProcess(self):
        task = AsyncResult(self.task_id)
        return task.status

    def resultProcess(self):
        task = AsyncResult(self.task_id)
        return task.result

    def cancelProcess(self):
        result = AsyncResult(self.task_id)
        result.revoke(terminate=True)
