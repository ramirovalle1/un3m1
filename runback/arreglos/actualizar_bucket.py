#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

from django.db import transaction

# SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
# print(f"YOUR_PATH: {YOUR_PATH}")
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
# print(f"SITE_ROOT: {SITE_ROOT}")
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
# print(f"your_djangoproject_home: {your_djangoproject_home}")
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

# CARGAR IMAGENES AL BUCKET DE GOOGLE STORAGE
from google.cloud import storage


# Ejemplo de uso
# bucket_name = 'admision_proctoring_unemi'
# source_file_name = '/mnt/nfs/home/storage/media/fotos/2023/01/22/foto_2023122155514.jpg'
# destination_blob_name = 'michaeloc_20.jpg'
def upload_to_bucket(bucket_name, source_file_name, destination_blob_name):
    """Carga un archivo en un bucket de Google Cloud Storage."""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)

    print(f"Archivo {source_file_name} cargado en {bucket_name}/{destination_blob_name}.")


bucket_name = 'admision_proctoring_unemi'
from inno.models import *
# import openpyxl
# try:
#     miarchivo = openpyxl.load_workbook("plan_materia_lenguaje.xlsx")
#     lista = miarchivo.get_sheet_by_name('resultados')
#     totallista = lista.rows
#     a = 0
#     listos = 0
#     for filas in totallista:
#         a += 1
#         if a > 2:
#             matricula_id = int(filas[0].value)
#             matriculasedeexamen = MatriculaSedeExamen.objects.filter(migrargsbucket=True, matricula_id=matricula_id, status=True).order_by("-fecha_modificacion")
#             if matriculasedeexamen:
#                 matriculasedeexamen = matriculasedeexamen[0]
#                 if matriculasedeexamen.archivofoto:
#                     username = matriculasedeexamen.matricula.inscripcion.persona.usuario.username
#                     source_file_name = f'/mnt/nfs/home/storage/media/{matriculasedeexamen.archivofoto}'
#                     destination_blob_name = f'{username}.jpg'
#
#                     upload_to_bucket(bucket_name, source_file_name, destination_blob_name)
#                     MatriculaSedeExamen.objects.filter(id=matriculasedeexamen.id, status=True).update(migrargsbucket=False)
#             else:
#                 listos += 1
#     print(f"Total actualizados {listos}")
# except Exception as ex:
#     print('error: %s' % ex)


try:
    for matriculasedeexamen in MatriculaSedeExamen.objects.filter(migrargsbucket=True, status=True):
        if matriculasedeexamen.archivofoto:
            username = matriculasedeexamen.matricula.inscripcion.persona.usuario.username
            source_file_name = f'/mnt/nfs/home/storage/media/{matriculasedeexamen.archivofoto}'
            destination_blob_name = f'{username}.jpg'
            upload_to_bucket(bucket_name, source_file_name, destination_blob_name)
            # print(f"foto ruta: {source_file_name} ruta dos:{destination_blob_name}")
        MatriculaSedeExamen.objects.filter(id=matriculasedeexamen.id, status=True).update(migrargsbucket=False)
except Exception as ex:
    print('error: %s' % ex)