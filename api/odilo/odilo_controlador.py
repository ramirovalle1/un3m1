# Create your views here.
from datetime import datetime, timedelta
import json
import os
import string
import uuid
import itertools
from hashlib import md5
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponse, Http404, JsonResponse
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt
from PIL import Image, ImageOps
from mobile.views import mobilelogin
from settings import MEDIA_ROOT, MEDIA_URL
from api.odilo import  odilo_service
from sga.funciones import bad_json
from api.odilo.odilo_service import OdiloAPI

def OdiloConsumidor(request):
    try:
        data = {}
        if request.method == 'POST':
            pass
        else:
            if 'action' in request.GET:
                data['action'] = action = request.GET['action']
                if action == 'loadModalLibros':
                    try:
                        lista_odilo_libros = request.session['lista_odilo_libros']
                    except Exception as ex:
                        request.session['lista_odilo_libros'] = []
                        lista_odilo_libros = request.session['lista_odilo_libros']
                    data['lista_odilo_libros'] = lista_odilo_libros
                    template = get_template("odilo/contenedor.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                if action == 'buscarLibros':
                    try:
                        try:
                            lista_odilo_libros = request.session['lista_odilo_libros']
                        except Exception as ex:
                            request.session['lista_odilo_libros'] = []
                            lista_odilo_libros = request.session['lista_odilo_libros']
                        search_ = request.GET['search']
                        if not search_:
                            return JsonResponse({'result': False, 'msg': 'Campos Vacios'})
                        # autor_, aniodesde_, aniohasta_ = request.GET.get('autor', ''), request.GET.get('aniodesde', ''),  request.GET.get('aniohasta', '')
                        odilo = OdiloAPI()
                        odilo.get_access_token()
                        data['libros'] = search_results = odilo.search_catalog(search_)
                        data['lista_odilo_libros'] = lista_odilo_libros
                        template = get_template("odilo/libros.html")
                        return JsonResponse({'result': True, 'data': template.render(data)})
                    except Exception as ex:
                        return JsonResponse({'result': False, 'msg': str(ex)})

                if action == 'buscadorLibros':
                    try:
                        search_ = request.GET['q'].upper().strip()
                        odilo = OdiloAPI()
                        odilo.get_access_token()
                        search_results = odilo.search_catalog(search_)
                        return JsonResponse({"result": "ok", "results": [{"id": x['isbn'], "name": "%s %s" % ("",x['title'])} for x in search_results]})
                    except Exception as ex:
                        pass

                if action == 'reservarLibro':
                    try:
                        try:
                            lista_odilo_libros = request.session['lista_odilo_libros']
                        except Exception as ex:
                            request.session['lista_odilo_libros'] = []
                            lista_odilo_libros = request.session['lista_odilo_libros']
                        isbn = request.GET['isbn']
                        encontrado = False
                        for item in lista_odilo_libros:
                            if item[0] == isbn:
                                encontrado = True
                                raise NameError('Libro ya se encuentra en la lista de recursos')
                        odilo = OdiloAPI()
                        odilo.get_access_token()
                        search_results = odilo.search_catalog(isbn)
                        if len(search_results) > 0:
                            libro = search_results[0]
                            lista_odilo_libros.append((isbn, libro))
                            request.session['lista_odilo_libros'] = lista_odilo_libros
                        else:
                            raise NameError('Libro no disponible, inténtelo más tarde')
                        return JsonResponse({'result': True, 'totalLibros': len(lista_odilo_libros)})
                    except Exception as ex:
                        return JsonResponse({'result': False, 'msg': str(ex)})
                if action == 'eliminarLibro':
                    try:
                        try:
                            lista_odilo_libros = request.session['lista_odilo_libros']
                        except Exception as ex:
                            request.session['lista_odilo_libros'] = []
                            lista_odilo_libros = request.session['lista_odilo_libros']
                        isbn = request.GET['isbn']
                        encontrado = False
                        for item in lista_odilo_libros:
                            if item[0] == isbn:
                                lista_odilo_libros.remove(item)
                                encontrado = True
                                break
                        request.session['lista_odilo_libros'] = lista_odilo_libros
                        return JsonResponse({'result': True, 'totalLibros': len(lista_odilo_libros)})
                    except Exception as ex:
                        return JsonResponse({'result': False, 'msg': str(ex)})
                if action == 'consultarLibros':
                    try:
                        lista_odilo_libros = request.session['lista_odilo_libros']
                    except Exception as ex:
                        request.session['lista_odilo_libros'] = []
                        lista_odilo_libros = request.session['lista_odilo_libros']
                    data['libros'] = lista_odilo_libros
                    template = get_template("odilo/librospreguardar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
    except Exception as ex:
        return bad_json("Error en API %s" % ex.__str__())
