# coding=utf-8
import json

from _decimal import Decimal
from datetime import datetime
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status

from api.serializers.login.recoverypassword import PersonaSerializer, UserTokenSerializer
from bd.funciones import recoveryPassword
from bd.models import UserToken
from moodle.models import UserAuth
from sga.funciones import variable_valor, validar_ldap_aux, log
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsavesilabo, conviert_html_to_pdfsavepracticas
import os
import random
from django.db import connection, transaction, connections
from sga.commonviews import adduserdata, obtener_reporte, actualizar_nota_planificacion
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from sga.models import Persona, Matricula, CambioClavePersona
from sga.templatetags.sga_extras import encrypt
from django.template import Context
from django.template.loader import get_template
from settings import DEBUG
from django.shortcuts import render, redirect
from api.helpers.functions_helper import get_variable


class RecoveryPasswordAPIView(APIView):

    def post(self, request):
        TIEMPO_ENCACHE = 60 * 15
        try:
            if not 'action' in request.data:
                raise NameError(u'Parametro de acciòn no encontrado')

            action = request.data['action']
            if action == 'searchPerson':
                try:
                    if not 'documento' in request.data:
                        raise NameError(u"Documento invalido.")
                    documento = (request.data['documento']).upper()
                    ePersona = Persona.objects.filter(Q(cedula=documento) | Q(pasaporte=documento))
                    if not ePersona.values("id").exists():
                        raise NameError(u"Tu búsqueda no ha devuelto resultado. Vuelve a intentarlo con otra información.")
                    persona = ePersona[0]
                    if not persona.usuario:
                        raise NameError(u"Tu búsqueda no ha devuelto resultado. Vuelve a intentarlo con otra información.")
                    if persona.usuario.is_superuser:
                        raise NameError(u"Tu búsqueda no ha devuelto resultado. Vuelve a intentarlo con otra información.")
                    if persona.es_administrativo() and persona.es_administrativo_perfilactivo():
                        raise NameError(u"Esta opción para su perfil no está disponible, solicitar el cambio de contraseña al personal de Servicios Informáticos.")
                    elif persona.es_profesor():
                        raise NameError(u"Esta opción para su perfil no está disponible, solicitar el cambio de contraseña al personal de Servicios Informáticos.")
                    elif persona.es_estudiante():
                        id_periodo = variable_valor('ID_PERIODO_ADMISION_LOGIN')
                        if id_periodo:
                            if Matricula.objects.values('id').filter(status=True, nivel__periodo_id=id_periodo, inscripcion__persona=persona).exists():
                                raise NameError(u"Esta opción para su perfil no está disponible, por favor diríjase  al botón: Consultar credenciales - Curso de Nivelación.")
                        lista = persona.lista_emails()
                        if lista.__len__() <= 0:
                            tieneCorreo = False
                        else:
                            tieneCorreo = True
                        aData = {"cantidad": 1,
                                 "id": str(encrypt(persona.usuario.id)),
                                 "documento": persona.documento(),
                                 "nombre_completo": persona.nombre_completo(),
                                 "es_mujer": persona.es_mujer(),
                                 "es_hombre": persona.es_hombre(),
                                 "usuario": persona.usuario.username,
                                 "tieneCorreo": tieneCorreo,
                                 "correos": ", ".join(lista),
                                 "perfiles": len(persona.mis_perfilesusuarios())}
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    else:
                        raise NameError(u"Esta opción para su perfil no está disponible, solicitar el cambio de contraseña al personal de Atención al Estudiante.")
                    raise NameError(u"Tu búsqueda no ha devuelto resultado. Vuelve a intentarlo con otra información.")
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)

            elif action == "generatePassword":
                try:
                    if not 'id' in request.data:
                        raise NameError(u"Parametros incompletos")
                    id = int(encrypt(request.data['id']))
                    ePersonas = Persona.objects.filter(usuario_id=id)
                    if not ePersonas.values("id").exists():
                        raise NameError(u"No existe el usuario")
                    persona = ePersonas.first()
                    result = recoveryPassword(request, persona, 4)
                    r = json.loads(result.content.decode())
                    if r['result'] == 'bad':
                        raise NameError(f"{r['mensaje']}")
                    return Helper_Response(isSuccess=True, data={}, message=r['mensaje'], status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)

            elif action == "verifyToken":
                try:
                    data = request.data
                    if not 'token' in data:
                        raise NameError(u"Token invalido")
                    token = data['token']
                    if not UserToken.objects.values("id").filter(token=token).exists():
                        raise NameError(u"Token invalido")
                    eUserToken = UserToken.objects.get(token=token)
                    if not eUserToken.isValidoToken():
                        raise NameError(u"Token invalido")
                    ePersona = Persona.objects.get(usuario=eUserToken.user)
                    if not ePersona.cambioclavepersona_set.values("id").exists():
                        raise NameError(u"Token invalido")
                    aData = {
                        "ePersona": PersonaSerializer(ePersona).data,
                        "eUserToken": UserTokenSerializer(eUserToken).data
                    }
                    return Helper_Response(isSuccess=True, data=aData, message="", status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == "changePassword":
                with transaction.atomic():
                    try:
                        data = request.data
                        if not 'token' in data:
                            raise NameError(u"Token invalido")
                        token = data['token']
                        if not UserToken.objects.values("id").filter(token=token).exists():
                            raise NameError(u"Token invalido")
                        eUserToken = UserToken.objects.get(token=token)
                        if not eUserToken.isValidoToken():
                            raise NameError(u"Token invalido")
                        ePersona = Persona.objects.get(usuario=eUserToken.user)
                        if not ePersona.cambioclavepersona_set.values("id").exists():
                            raise NameError(u"Token invalido")
                        if not 'password1' in data:
                            raise NameError(u"Contraseña invalida")
                        if not 'password2' in data:
                            raise NameError(u"Contraseña invalida")
                        if data['password1'] != data['password2']:
                            raise NameError(u"Contraseña invalida")
                        password = data['password1']
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
                        if not CambioClavePersona.objects.values("id").filter(persona=ePersona).exists():
                            raise NameError(u"Solicitud de cambio antigua.")

                        ePersona.clave_cambiada()
                        usuario = ePersona.usuario
                        usuario.set_password(password)
                        usuario.save()
                        eUserToken.inactiveToken()

                        if not UserAuth.objects.db_manager("sga_select").values("id").filter(usuario=usuario).exists():
                            usermoodle = UserAuth(usuario=usuario)
                            usermoodle.set_data()
                            usermoodle.set_password(password)
                            usermoodle.save()
                        else:
                            usermoodle = UserAuth.objects.filter(usuario=usuario).first()
                            isUpdateUserMoodle = False
                            if not usermoodle.check_password(password) or usermoodle.check_data():
                                if not usermoodle.check_password(password):
                                    usermoodle.set_password(password)
                                usermoodle.save()

                        if not DEBUG:
                            if variable_valor('VALIDAR_LDAP'):
                                validar_ldap_aux(usuario.username, password, ePersona)
                        log(u'Reseteo clave - modo recuperacion: %s [%s] - cambio clave: %s ' % (ePersona, ePersona.id, usuario), request, "add", user=ePersona.usuario)
                        return Helper_Response(isSuccess=True, data={}, message="Se ha cambiada correctamente la contraseña", status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
