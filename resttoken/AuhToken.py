from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.status import (HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_200_OK)


class HojaRuta(APIView):
    @csrf_exempt
    def get(self):
        return None


class CustomAuthToken(ObtainAuthToken):
    def get(self, request, *args, **kwargs):
        if 'tokenappunemi' in request.GET:
            if not request.GET['tokenappunemi'] == 'token Unemi04m76#%5&*fg8Unemi6677d%8lv02t$hkjwUnemi8emvaedan118y6aUnemi':
                return Response({'error': 'Unemi Access-Control-Allow-Origin False'}, status=HTTP_400_BAD_REQUEST)
        else:
            return Response({'error': 'Cabeceras incompletas'}, status=HTTP_400_BAD_REQUEST)
        username = request.GET['username']
        password = request.GET['password']
        if username is None or password is None:
            return Response({'error': 'Proporcione tanto el nombre de usuario como la contraseña'}, status=HTTP_400_BAD_REQUEST)
        user = authenticate(username=username, password=password)
        if not user:
            return Response({'error': 'Invalid Credentials'}, status=HTTP_404_NOT_FOUND)
        token, created = Token.objects.get_or_create(user=user)
        data = {}
        data['nombre'] = user.persona_set.all()[0].nombre_completo()
        data['photo'] = '%s' % user.persona_set.all()[0].foto().foto
        data['result'] = 'ok'
        data['token'] = token.key
        data['usuario'] = user.username

        response = Response(data, status=HTTP_200_OK)
        response.__setitem__("Content-type", "application/json")
        response.__setitem__("Access-Control-Allow-Origin", "*")
        return response

