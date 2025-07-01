# from settings import NOMBRE_INSTITUCION\
#     , TOKEN, CLIENT_ID, ORGANIZATION_ID
# import requests
# # -*- coding: UTF-8 -*-
# import json
# from django.contrib import messages
# from django.contrib.auth.decorators import login_required
# from django.db import transaction
# from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
# from django.shortcuts import render
# from django.template.loader import get_template
# from django.template.context import Context
# from datetime import datetime, timedelta
# from decorators import secure_module, last_access
# from sagest.models import CapInscritoIpec
# from sga.models import Persona, miinstitucion
#
# # @login_required(redirect_field_name='ret', login_url='/loginsga')
# # @secure_module
#
#
# @last_access
# @transaction.atomic()
#
# def view(request):
#     try:
#         data = {}
#
#         if 'id' in request.GET:
#             data["DOMINIO_DEL_SISTEMA"] = dominio_sistema = request.build_absolute_uri('/')[:-1].strip("/")
#             data['id'] = id = int(request.GET['id'])
#             inscrito = CapInscritoIpec.objects.get(pk=id)
#             evento = inscrito.capeventoperiodo
#             descripciontexto = u"CERTIFICADO - " + inscrito.capeventoperiodo.capevento.nombre
#             descripcioncomentario = u"CERTIFICADO - " + inscrito.capeventoperiodo.capevento.nombre
#             urlpdf = '{}/media/{}'.format(dominio_sistema, inscrito.rutapdf)
#             # urlpdf = "https://sga.unemi.edu.ec/media/archivo/2019/04/16/capacitacion_2019416231147.pdf"
#             connect()
#             shared(descripciontexto, descripcioncomentario, urlpdf)
#             return JsonResponse({"result": "ok", "mensaje": "Se ha compartido en Linkedin."})
#     except Exception as ex:
#         messages.error(request, ex)
#         return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})
#
# def connect():
#     headers = {'Authorization': f'Bearer {TOKEN}'}
#     response = requests.get('https://api.linkedin.com/v2/me', headers=headers)
#     user_info = response.json()
#     print(user_info)
#
#
# def shared(descripciontexto, descripcioncomentario, urlpdf):
#     headers = {
#         'Authorization': f'Bearer {TOKEN}',
#         'Content-Type': 'application/json',
#         'X-Restli-Protocol-Version': '2.0.0'
#     }
#     payload = {
#         "author": f"urn:li:person:{CLIENT_ID}",
#         # "author": f"urn:li:organization:{ORGANIZATION_ID}",
#         "lifecycleState": "PUBLISHED",
#         "specificContent": {
#             "com.linkedin.ugc.ShareContent": {
#                 "shareCommentary": {
#                     "text": descripcioncomentario
#                 },
#                 "shareMediaCategory": "ARTICLE",
#                 "media": [
#                     {
#                         "status": "READY",
#                         "description": {
#                             "text": descripciontexto
#                         },
#                         "originalUrl": urlpdf,
#                         "title": {
#                             "text": NOMBRE_INSTITUCION
#                         }
#                     }
#                 ]
#             }
#         },
#         "visibility": {
#             "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
#         }
#     }
#     print(payload)
#     response = requests.post('https://api.linkedin.com/v2/ugcPosts', headers=headers, json=payload)
#     print(response.status_code)
#     data = response.json()
#     print(data)