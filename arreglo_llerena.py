# coding=utf-8
# !/usr/bin/env python
import base64
import os
import sys

# SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
import urllib.request

YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
# print(f"YOUR_PATH: {YOUR_PATH}")
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
# print(f"SITE_ROOT: {SITE_ROOT}")
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
# print(f"your_djangoproject_home: {your_djangoproject_home}")
sys.path.append(your_djangoproject_home)

import xlwt
from webpush import send_user_notification
from xlwt import easyxf
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from datetime import datetime, timedelta
from django.db import transaction
from sga.models import Materia, Clase, Leccion, LeccionGrupo, AsistenciaLeccion, CamposTitulosPostulacion
from sga.funciones import variable_valor
# from sga.models import *
# from sagest.models import *
import xlrd
from postulate.models import Partida, PersonaAplicarPartida, PersonaFormacionAcademicoPartida, PartidaTribunal
from sga.models import *
from sagest.models import *
from django.db.models import Sum, F, FloatField
from django.db.models.functions import Coalesce
from settings import MEDIA_ROOT, BASE_DIR
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side, colors
from django.http import HttpResponse
from sga.models import Modulo
from gdocumental.models import *
from bd.models import *

import requests
import json

# # Reemplaza las siguientes variables con tus valores específicos
# moodle_url = "https://campusvirtual.nutricapacitaciones.com"
# token = "0a95bf2d004a8598d5e25173a60d4f7d"
# course_id = 4  # Reemplaza con el ID del curso
#
# output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', ''))
# image_path = f"{output_folder}2.jpg"  # Reemplaza con la ruta al archivo de imagen
# image_filename = "2.jpg"  # Reemplaza con el nombre del archivo de imagen




asunto = u"INSIGNIA - "
send_html_mail("Postulate: Fase de Preselección", "emails/postulate_tres_puntuados.html",
               {'sistema': u'SISTEMA POSTULATE UNEMI', 'postulante': None, 'persona': None, 'partida': None,
                't': miinstitucion()}, ['rviterib1@unemi.edu.ec'], [], cuenta=CUENTAS_CORREOS[30][1])


# def upload_image(moodle_url, token, image_path, image_filename):
#     upload_url = f"{moodle_url}/webservice/upload.php?token={token}"
#     rest_url = f"{moodle_url}/webservice/rest/server.php"
#
#     with open(image_path, "rb") as image_file:
#         files = {"file": (image_filename, image_file)}
#         data = {
#             "component": "user",
#             "filearea": "draft",
#             "itemid": 0,
#             "filepath": "/",
#             "filename": image_filename,
#         }
#         response = requests.post(upload_url, files=files, data=data)
#     uploaded_file = json.loads(response.text)[0]
#     print(response.text)
#
#     return True
#
#
# def update_course_image(moodle_url, token, course_id, draft_itemid):
#     # update_url = f"{moodle_url}/webservice/rest/server.php?moodlewsrestformat=json"
#     url = 'https://campusvirtual.nutricapacitaciones.com/webservice/rest/server.php'
#     # data = {
#     #     "wstoken": token,
#     #     "wsfunction": "core_course_update_courses",
#     #     "courses[0][id]": course_id,
#     #     "courses[0][itemid]": draft_itemid,
#     #     "courses[0][filearea]": "overview",
#     #     "courses[0][filepath]": "/",
#     #     "courses[0][filename]": "new_image.jpg",
#     # }
#
#     params = {'wstoken': token, 'wsfunction': 'local_coursecoverws_update_coursecover', 'moodlewsrestformat': 'json', 'courseid': course_id, 'itemid': draft_itemid}
#     response = requests.post(url, params=params)
#     # response = requests.post(update_url, data=data)
#     print(response.text)
#     return response
#
#
# def subir_img():
#     # Leer la imagen y codificarla en base64
#     with open(image_path, 'rb') as image_file:
#         base64_image = base64.b64encode(image_file.read()).decode('utf-8')
#
#     import requests
#
#     # Reemplaza con la URL de tu instancia de Moodle, el token de tu servicio web y el ID del curso.
#     moodle_url = "https://campusvirtual.nutricapacitaciones.com/webservice/rest/server.php"
#     webservice_token = "0a95bf2d004a8598d5e25173a60d4f7d"
#     course_id = 11
#
#     # Configurar los parámetros para la llamada al servicio web.
#     params = {
#         'wstoken': webservice_token,
#         'moodlewsrestformat': 'json',
#         'wsfunction': 'local_actualizarportada_actualizar_imagen_portada',
#         'courseid': course_id,
#         'filename': image_filename,
#         'imagen': base64_image
#     }
#
#     # Realizar la llamada al servicio web de Moodle.
#     response = requests.post(moodle_url, data=params)
#     print(response.text)
#     # Verificar si la respuesta es exitosa.
#     if response.status_code == 200:
#         print('La imagen de portada se actualizó correctamente.')
#     else:
#         print('Error al actualizar la imagen de portada:', response.text)
#
#
#     # query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
#     # cursor.execute(query)
#
# # upload_image(moodle_url, token, image_path, image_filename)
# # update_course_image(moodle_url, token, course_id, draft_itemid)
# # print("Imagen de portada actualizada:", response.text)
# subir_img()
