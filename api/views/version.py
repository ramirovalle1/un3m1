from rest_framework.views import APIView
from api.helpers.response_herlper import Helper_Response
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

unicode = str


class VersionView(APIView):
    #permission_classes = (IsAuthenticated,)

    def get(self, request):
        response = Helper_Response(isSuccess=True, status=status.HTTP_200_OK)
        return response
