from datetime import datetime
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status

from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from settings import SERVER_RESPONSE


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class FooterInfoAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = None

    # @api_security
    def post(self, request):
        # TIEMPO_ENCACHE = 60 * 15
        try:
            hoy = datetime.now()
            # payload = request.auth.payload
            remotenameaddr = '%s' % (request.META['SERVER_NAME'])
            remoteaddr = '%s - %s' % (get_client_ip(request), request.META['SERVER_NAME'])
            aData={
                'hora': hoy,
                'remotenameaddr': remotenameaddr,
                'remoteaddr': remoteaddr,
                'server_response': SERVER_RESPONSE
            }
            return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
