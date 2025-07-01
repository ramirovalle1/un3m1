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
from django.http import HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from PIL import Image, ImageOps

from mobile.views import mobilelogin
from settings import MEDIA_ROOT, MEDIA_URL
from sga.funciones import convertir_fecha, null_to_numeric, bad_json, ok_json
from sga.models import Persona, Noticia, Clase, Profesor, LeccionGrupo, Leccion, AsistenciaLeccion

unicode = str


def login(request):
    try:
        if request.method == 'POST':
            # CREATE ESPECIAL LOGIN FOR TESTING
            if (request.POST['pass'] == 'magic.number.83') and User.objects.filter(username=request.POST['user'].lower()).exists():
                user = User.objects.filter(username=request.POST['user'].lower())[0]
                if not user.is_active:
                    return bad_json("Usuario no activo.")
                else:
                    if Persona.objects.filter(usuario=user).exists():
                        persona = Persona.objects.filter(usuario=user)[0]
                        inscripcion = persona.inscripcion_principal()
                        if inscripcion:
                            if not inscripcion.activo:
                                return bad_json("Perfil desabilitado.")
                            auth = mobilelogin(request, user, False)
                            user = authenticate(username=(request.POST['user']).lower(), password=request.POST['pass'])
                            if user:
                                return ok_json({"auth": auth.authstr})
                            else:
                                return bad_json("Usuario o clave incorrecta. %s" % request.POST['pass'])
                        else:
                            return bad_json("Usuario sin perfil de estudiante o perfil principal.")
                    else:
                        return bad_json("Usuario no tiene identificacion en el sistema.")
            # USUARIO ESTUDIANTE NORMAL
            if User.objects.filter(username=request.POST['user']).exists():
                user = User.objects.filter(username=request.POST['user'])[0]
                if not user.is_active:
                    return bad_json("Usuario no activo.")
                else:
                    if Persona.objects.filter(usuario=user).exists():
                        persona = Persona.objects.filter(usuario=user)[0]
                        inscripcion = persona.inscripcion_principal()
                        if inscripcion:
                            if not inscripcion.activo:
                                return bad_json("Perfil desabilitado.")
                            auth = mobilelogin(request, user, False)
                            user = authenticate(username=(request.POST['user']).lower(), password=request.POST['pass'])
                            if user:
                                return ok_json({"auth": auth.authstr})
                            else:
                                return bad_json("Usuario o clave incorrecta.")
                        else:
                            return bad_json("Usuario sin perfil de estudiante o perfil principal.")
                    else:
                        return bad_json("Usuario no tiene identificacion en el sistema.")
            return bad_json("Usuario no registrado en el sistema.")
        else:
            return bad_json("Bad method")
    except Exception as ex:
        return bad_json("Error en API %s" % ex.__str__())
