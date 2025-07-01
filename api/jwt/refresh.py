from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.views import TokenViewBase
from rest_framework.response import Response
from rest_framework import status

from api.serializers.login.default import MyTokenRefreshSerializer

unicode = str


class MyTokenRefreshView(TokenViewBase):
    serializer_class = MyTokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            try:
                serializer.is_valid(raise_exception=True)
            except TokenError as e:
                raise InvalidToken(e.args[0])
            # user = serializer.user
            return super().post(request, args, kwargs)
        except Exception as ex:
            return Response({'message': ex.__str__()}, status=status.HTTP_401_UNAUTHORIZED)
