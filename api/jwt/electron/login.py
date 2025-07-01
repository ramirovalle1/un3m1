from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from api.serializers.electron.default import MyTokenObtainPairSerializer
from bd.models import FLAG_SUCCESSFUL, APP_ESTUDIANTE
from decorators import get_client_ip
from sga.funciones import loglogin

unicode = str


class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            #token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as ex:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class LogoutAllView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        tokens = OutstandingToken.objects.filter(user_id=request.user.id)
        for token in tokens:
            t, _ = BlacklistedToken.objects.get_or_create(token=token)

        return Response(status=status.HTTP_205_RESET_CONTENT)


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            try:
                serializer.is_valid(raise_exception=True)
            except TokenError as e:
                raise InvalidToken(e.args[0])
            user = serializer.user
            # client_address = get_client_ip(request)
            # data = request.data
            # browser = data['clientNavegador'] if 'clientNavegador' in data else ''
            # ops = data['clientOS'] if 'clientOS' in data else ''
            # screensize = data['clientScreensize'] if 'clientScreensize' in data else ''
            # loglogin(action_flag=FLAG_SUCCESSFUL, action_app=APP_ESTUDIANTE, ip_private='',
            #          ip_public=client_address, browser=browser, ops=ops, cookies='',
            #          screen_size=screensize, user=user)
            return super().post(request, args, kwargs)
        except Exception as ex:
            return Response({'message': ex.__str__()}, status=status.HTTP_401_UNAUTHORIZED)
