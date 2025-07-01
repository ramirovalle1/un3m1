# -*- coding: UTF-8 -*-
import random

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from bd.funciones import recoveryPassword
from bd.models import LogQuery, UserToken
from decorators import secure_module
from bd.forms import *
from moodle.models import UserAuth
from settings import DEBUG
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
import sys
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery, variable_valor, \
    validar_ldap_aux
from sga.models import CambioClavePersona,Matricula
from sga.templatetags.sga_extras import encrypt


@transaction.atomic()
def view(request):
    if request.method == 'POST':
        action = request.POST['action']

        if action == "searchSGA":
            try:
                if not 'documento' in request.POST:
                    raise NameError(u"Documento invalido.")
                documento = (request.POST['documento']).upper()
                ePersona = Persona.objects.filter(Q(cedula=documento) | Q(pasaporte=documento))
                if not ePersona.values("id").exists():
                    raise NameError(u"Tu búsqueda no ha devuelto resultado. Vuelve a intentarlo con otra información.")
                persona = ePersona[0]
                if not persona.usuario:
                    raise NameError(u"Tu búsqueda no ha devuelto resultado. Vuelve a intentarlo con otra información.")
                if persona.usuario.is_superuser:
                    raise NameError(u"Tu búsqueda no ha devuelto resultado. Vuelve a intentarlo con otra información.")
                if persona.es_administrativo() and persona.es_administrativo_perfilactivo():
                    raise NameError(u"Esta opción para su perfil no está disponible, solicitar el cambio de contraseña al personal de soporte de TIC.")
                elif persona.es_profesor():
                    lista = persona.lista_emails()
                    if lista.__len__() <= 0:
                        return JsonResponse({"result": "ok", "cantidad": 1, "id": str(encrypt(persona.usuario.id)), "ced": persona.cedula, "nombre": persona.nombre_completo(), "user": persona.usuario.username, "permisoboton": 0, "perfiles": persona.mis_perfilesusuarios().count()})
                    return JsonResponse({"result": "ok", "cantidad": 1, "id": str(encrypt(persona.usuario.id)), "ced": persona.cedula, "nombre": persona.nombre_completo(), "user": persona.usuario.username, "permisoboton": 1, "perfiles": persona.mis_perfilesusuarios().count()})
                elif persona.es_estudiante():
                    id_periodo = variable_valor('ID_PERIODO_ADMISION_LOGIN')
                    if id_periodo:
                        if Matricula.objects.values('id').filter(status=True, nivel__periodo_id=id_periodo, inscripcion__persona=persona).exists():
                            return JsonResponse({"result": "bad",  "mensaje": u"Esta opción para su perfil no está disponible, por favor diríjase  al botón: Consultar credenciales - Curso de Nivelación."})

                    lista = persona.lista_emails()
                    if lista.__len__() <= 0:
                        return JsonResponse({"result": "ok", "cantidad": 1, "id": str(encrypt(persona.usuario.id)), "ced": persona.cedula, "nombre": persona.nombre_completo(), "user": persona.usuario.username, "permisoboton": 0, "perfiles": persona.mis_perfilesusuarios().count()})
                    return JsonResponse({"result": "ok", "cantidad": 1, "id": str(encrypt(persona.usuario.id)), "ced": persona.cedula, "nombre": persona.nombre_completo(), "user": persona.usuario.username, "permisoboton": 1, "perfiles": persona.mis_perfilesusuarios().count()})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Esta opción para su perfil no está disponible, solicitar el cambio de contraseña al personal de soporte de TIC."})
                return JsonResponse({"result": "bad", "mensaje": u"Tu búsqueda no ha devuelto resultado. Vuelve a intentarlo con otra información."})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})

        elif action == "searchSAGEST":
            try:
                if not 'documento' in request.POST:
                    raise NameError(u"Documento invalido.")
                documento = (request.POST['documento']).upper()
                if not Persona.objects.filter(Q(cedula=documento) | Q(pasaporte=documento)).exists():
                    raise NameError(u"No tiene acceso al sistema.")
                persona = Persona.objects.filter(Q(cedula=documento) | Q(pasaporte=documento))[0]
                if not persona.usuario:
                    raise NameError(u"Tu búsqueda no ha devuelto resultado. Vuelve a intentarlo con otra información.")
                if persona.usuario.is_superuser:
                    raise NameError(u"Tu búsqueda no ha devuelto resultado. Vuelve a intentarlo con otra información.")
                if persona.es_administrativo() or persona.es_profesor():
                    return JsonResponse({"result": "ok", "id": str(encrypt(persona.usuario.id))})
                return JsonResponse({"result": "bad", "mensaje": u"Esta opción solo está disponible para los administrativos.."})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})

        elif action == "searchPOSGRADO":
            try:
                if not 'documento' in request.POST:
                    raise NameError(u"Documento invalido.")
                documento = (request.POST['documento']).upper()
                if not Persona.objects.filter(Q(cedula=documento) | Q(pasaporte=documento)).exists():
                    raise NameError(u"No tiene acceso al sistema.")
                persona = Persona.objects.filter(Q(cedula=documento) | Q(pasaporte=documento))[0]
                if not persona.usuario:
                    raise NameError(u"Tu búsqueda no ha devuelto resultado. Vuelve a intentarlo con otra información.")
                if persona.usuario.is_superuser:
                    raise NameError(u"Tu búsqueda no ha devuelto resultado. Vuelve a intentarlo con otra información.")
                if persona.es_administrativo():
                # if persona.es_administrativo() or persona.es_profesor():
                    raise NameError(u"Esta opción solo está disponible para aspirantes.")
                return JsonResponse({"result": "ok", "id": str(encrypt(persona.usuario.id)), "email": persona.email, "user": persona.usuario.username})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": ex.__str__()})

        elif action == "searchPOSTULATE":
            try:
                if not 'documento' in request.POST:
                    raise NameError(u"Documento invalido.")
                documento = (request.POST['documento']).upper()
                if not Persona.objects.filter(Q(cedula=documento) | Q(pasaporte=documento)).exists():
                    raise NameError(u"No tiene acceso al sistema.")
                persona = Persona.objects.filter(Q(cedula=documento) | Q(pasaporte=documento))[0]
                if not persona.usuario:
                    raise NameError(u"Tu búsqueda no ha devuelto resultado. Vuelve a intentarlo con otra información.")
                if persona.usuario.is_superuser:
                    raise NameError(u"Tu búsqueda no ha devuelto resultado. Vuelve a intentarlo con otra información.")
                return JsonResponse({"result": "ok", "id": str(encrypt(persona.usuario.id)), "ced": persona.cedula, "nombre": persona.nombre_completo(), "user": persona.usuario.username})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": ex.__str__()})

        elif action == "generatepassword":
            try:
                if not Persona.objects.filter(usuario_id=int(encrypt(request.POST['id']))).exists():
                    raise NameError(u"No existe el usuario")
                if not 'app' in request.POST:
                    raise NameError(u"Acción no identificada")
                app = int(request.POST['app'])
                persona = Persona.objects.get(usuario_id=int(encrypt(request.POST['id'])))
                return recoveryPassword(request, persona, app)
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": ex.__str__()})

        elif action == "changepassword":
            try:
                if not UserToken.objects.filter(token=request.POST['token']).exists():
                    raise NameError(u"Token invalido.")
                eUserToken = UserToken.objects.get(token=request.POST['token'])
                if not eUserToken.isValidoToken():
                    raise NameError(u"Token invalido.")
                persona = Persona.objects.get(usuario=eUserToken.user)
                password = request.POST['clave']
                espacio = mayuscula = minuscula = numeros = False
                long = len(password)  # Calcula la longitud de la contraseña
                # y = password.isalnum()  # si es alfanumérica retona True
                for carac in password:
                    espacio = True if carac.isspace() else espacio  # si encuentra un espacio se cambia el valor user
                    mayuscula = True if carac.isupper() else mayuscula  # acumulador o contador de mayusculas
                    minuscula = True if carac.islower() == True else minuscula  # acumulador o contador de minúsculas
                    numeros = True if carac.isdigit() == True else numeros  # acumulador o contador de numeros

                if espacio == True:  # hay espacios en blanco
                    raise NameError(u"La clave no puede contener espacios.")
                if not mayuscula or not minuscula or not numeros or long < 8:
                    raise NameError(u"La clave elegida no es segura: debe contener letras minúsculas, mayúsculas, números y al menos 8 carácter.")

                if not CambioClavePersona.objects.values("id").filter(persona=persona).exists():
                    raise NameError(u"Solicitud de cambio antigua.")

                persona.clave_cambiada()
                usuario = persona.usuario
                usuario.set_password(password)
                usuario.save()
                if (eUserAuth := UserAuth.objects.filter(usuario=usuario).first()) is not None:
                    if not eUserAuth.check_password(request.POST['clave']) or eUserAuth.check_data():
                        if not eUserAuth.check_password(request.POST['clave']):
                            eUserAuth.set_password(request.POST['clave'])
                        eUserAuth.save()
                else:
                    eUserAuth = UserAuth(usuario=usuario)
                    eUserAuth.set_data()
                    eUserAuth.set_password(request.POST['clave'])
                    eUserAuth.save()
                eUserToken.inactiveToken()

                if not DEBUG:
                    if variable_valor('VALIDAR_LDAP'):
                        validar_ldap_aux(usuario.username, password, persona)
                log(u'Reseteo clave - modo recuperacion: %s [%s] - cambio clave: %s ' % (persona, persona.id, usuario), request, "add", user=persona.usuario)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"No se pudo cambiar la clave. %s" % ex.__str__()})

        elif action == "searchAdmision":
            try:
                if not 'cedula_admision' in request.POST:
                    raise NameError(u"Documento invalido.")
                cedula_admision = (request.POST['cedula_admision']).upper()
                if not Persona.objects.filter(Q(cedula=cedula_admision) | Q(pasaporte=cedula_admision)).exists():
                    raise NameError(u"No tiene acceso al sistema.")
                persona = Persona.objects.filter(Q(cedula=cedula_admision) | Q(pasaporte=cedula_admision))[0]
                if not persona.usuario:
                    raise NameError(u"Tu búsqueda no ha devuelto resultado. Vuelve a intentarlo con otra información.")
                if persona.usuario.is_superuser:
                    raise NameError(u"Tu búsqueda no ha devuelto resultado. Vuelve a intentarlo con otra información.")
                if persona.es_administrativo() or persona.es_profesor():
                    raise NameError(u"Esta opción para su perfil no está disponible, solicitar el cambio de contraseña al personal de soporte de TIC.")
                id_periodo= variable_valor('ID_PERIODO_ADMISION_LOGIN')
                if id_periodo:
                    periodo = variable_valor('PERIODO_ADMISION_LOGIN')
                    if Matricula.objects.values('id').filter(status=True, nivel__periodo_id=periodo,inscripcion__persona=persona).exists():
                        return JsonResponse({"result": "ok", "user": str(persona.usuario),"id": str(encrypt(persona.usuario.id))})
                return JsonResponse({"result": "bad", "mensaje": u"Tu búsqueda no ha devuelto resultado. Vuelve a intentarlo con otra información."})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})

        elif action == "resetear_clave_admision":
            try:
                if not Persona.objects.db_manager("sga_select").filter(usuario_id=int(encrypt(request.POST['id']))).exists():
                    raise NameError(u"No existe el usuario")
                if not 'app' in request.POST:
                    raise NameError(u"Acción no identificada")
                app = int(request.POST['app'])
                persona = Persona.objects.get(usuario_id=int(encrypt(request.POST['id'])))
                user = persona.usuario
                usuario = persona.usuario
                persona.clave_cambiada()
                usuario.set_password(persona.identificacion())
                usuario.save()
                cambioclave = persona.cambiar_clave()
                cambioclave.solicitada = True
                cambioclave.clavecambio = persona.identificacion()
                cambioclave.save(request)
                log(u'Genero nuevo cambio de contraseña: %s [%s]' % (persona, persona.id), request, "add", user=user)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error, %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            return HttpResponseRedirect("/")
        else:
            try:
                data = {}
                if not 'token' in request.GET:
                    return HttpResponseRedirect('/')

                token = request.GET['token']
                if not UserToken.objects.values("id").filter(token=token).exists():
                    return HttpResponseRedirect('/')
                data['eUserToken'] = eUserToken = UserToken.objects.get(token=token)
                data['persona'] = persona = Persona.objects.get(usuario=eUserToken.user)
                if not persona.cambioclavepersona_set.exists():
                    return HttpResponseRedirect('/')
                data['background'] = random.randint(1, 2)
                return render(request, 'recoverypassword/view.html', data)
            except Exception as ex:
                return HttpResponseRedirect("/")
