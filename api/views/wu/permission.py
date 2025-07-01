import base64
from django.contrib.auth import authenticate, login
from rest_framework.permissions import BasePermission

from settings import DEBUG
from soap.functions import SERVICE_WESTERN_UNION_PK, get_setting_soap


class HasCsrfTokenValid(BasePermission):
    def has_permission(self, request, view):
        try:
            if 'HTTP_AUTHORIZATION' in request.META:
                auth = request.META['HTTP_AUTHORIZATION'].split()
                if len(auth) == 2:
                    if auth[0].lower() == "basic":
                        username, password = base64.b64decode(auth[1]).decode('utf-8').split(':', 1)
                        service_id = SERVICE_WESTERN_UNION_PK
                        setting = get_setting_soap(tipo=1, service_id=service_id)
                        if not setting:
                            return False
                        if not setting.get_usuarios().filter(username=username).exists():
                            return False
                        eUser = authenticate(username=username, password=password)
                        if not eUser:
                            return False
                        # SI EL USUARIO ESTA ACTIVO
                        if not eUser.is_active:
                            return False
                        request.user = eUser
                        return True
            return False
        except ValueError:
            return False
