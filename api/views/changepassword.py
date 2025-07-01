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
from sga.funciones import variable_valor, validar_ldap_aux, log, validar_ldap_reseteo
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsavesilabo, conviert_html_to_pdfsavepracticas
import os
import random
from django.db import connection, transaction, connections
from sga.commonviews import adduserdata, obtener_reporte, actualizar_nota_planificacion, get_client_ip
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from sga.models import Persona, Matricula, CambioClavePersona, PerfilUsuario, CUENTAS_CORREOS
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from django.template import Context
from django.template.loader import get_template
from settings import DEBUG
from django.shortcuts import render, redirect
from api.helpers.functions_helper import get_variable


class ChangePasswordAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        TIEMPO_ENCACHE = 60 * 15
        try:
            if not 'action' in request.data:
                raise NameError(u'Parametro de acciòn no encontrado')

            action = request.data['action']

            if action == "changePassword":
                with transaction.atomic():
                    try:
                        data = request.data
                        if not 'password1' in data:
                            raise NameError(u"Contraseña invalida")
                        if not 'password2' in data:
                            raise NameError(u"Contraseña invalida")
                        if not 'password3' in data:
                            raise NameError(u"Contraseña invalida")
                        if data['password1'] == data['password2']:
                            raise NameError(u"Contraseña nueva debe ser diferente a la antigua")
                        if data['password2'] != data['password3']:
                            raise NameError(u"Contraseña nueva debe confirmar")
                        password = data['password2']
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
                        payload = request.auth.payload
                        ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
                        usuario = ePerfilUsuario.persona.usuario
                        ePersona = ePerfilUsuario.persona
                        if password == ePersona.documento():
                            raise NameError(u"No puede usar como clave su numero de Cédula o Pasaporte.")
                        if not usuario.check_password(data['password1']):
                            raise NameError(u"Contraseña antigua invalida")
                        usuario.set_password(data['password2'])
                        usuario.save()
                        if not UserAuth.objects.db_manager("sga_select").values("id").filter(usuario=usuario).exists():
                            usermoodle = UserAuth(usuario=usuario)
                            usermoodle.set_data()
                            usermoodle.set_password(data['password2'])
                            usermoodle.save()
                        else:
                            usermoodle = UserAuth.objects.filter(usuario=usuario).first()
                            isUpdateUserMoodle = False
                            if not usermoodle.check_password(data['password2']) or usermoodle.check_data():
                                if not usermoodle.check_password(data['password2']):
                                    usermoodle.set_password(data['password2'])
                                usermoodle.save()

                        ePersona.clave_cambiada()
                        if variable_valor('VALIDAR_LDAP'):
                            validar_ldap_reseteo(usuario.username, data['password2'], ePersona)
                        log(u'%s - cambio clave desde IP %s' % (ePersona, get_client_ip(request)), request, "add")
                        send_html_mail("Cambio Clave SGAEstudiante.", "emails/cambio_clave.html",
                                       {'sistema': u'Sistema de Gestión Académica Estudiantil', 'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(), 'ip': get_client_ip(request),
                                        'persona': ePersona}, ePersona.lista_emails_envio(), [],
                                       cuenta=CUENTAS_CORREOS[0][1])
                        return Helper_Response(isSuccess=True, data={}, message="Se ha cambiada correctamente la contraseña", status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == "veryNeedChangePassword":
                with transaction.atomic():
                    try:
                        data = request.data
                        payload = request.auth.payload
                        ePerfilUsuario = PerfilUsuario.objects.db_manager("sga_select").get(pk=encrypt(payload['perfilprincipal']['id']))
                        usuario = ePerfilUsuario.persona.usuario
                        ePersona = ePerfilUsuario.persona
                        aData = {'veryNeedChangePassword': ePersona.necesita_cambiar_clave(),
                                 'ePersona': PersonaSerializer(ePersona).data}
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
