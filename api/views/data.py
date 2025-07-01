# coding=utf-8
import calendar
from _decimal import Decimal
from datetime import datetime
from django.db.models import Q, Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from django.apps import apps
from sga.models import *
from sagest.models import *
from bib.models import *
from certi.models import *
from socioecon.models import *
from med.models import *


class DataModelAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = None

    @api_security
    def get(self, request):
        try:
            action = request.query_params.get('action', None)
            if action is None:
                raise NameError(u"Acción no encontrada")
            if action == 'data':
                try:
                    m = request.query_params.get('model', None)
                    limit = request.query_params.get('limit', 25)
                    app = request.query_params.get('app', None)
                    if type(limit) is not int:
                        limit = int(limit)
                    if m is None:
                        raise NameError(u"Modelo no encontrado")
                    if 'q' in request.query_params:
                        q = (request.query_params.get('q', '')).upper().strip()
                        if ':' in m:
                            sp = m.split(':')
                            if app:
                                model = apps.get_model(app, sp[0])
                            else:
                                model = eval(sp[0])
                            if len(sp) > 1:
                                query = model.flexbox_query(q, extra=sp[1], limit=limit)
                            else:
                                query = model.flexbox_query(q, limit=limit)
                        else:
                            if app:
                                model = apps.get_model(app, m)
                            else:
                                model = eval(m)
                            query = model.flexbox_query(q, limit=limit)
                    else:
                        if ':' in m:
                            sp = m.split(':')
                            if app:
                                model = apps.get_model(app, sp[0])
                            else:
                                model = eval(sp[0])
                            if len(sp) > 1:
                                query = model.flexbox_query('', extra=sp[1], limit=limit)
                            else:
                                resultquery = model.flexbox_query('')
                                try:
                                    query = eval('resultquery.filter(%s, status=True).distinct()' % (sp[1]))
                                except Exception as ex:
                                    query = resultquery
                        else:
                            if app:
                                model = apps.get_model(app, m)
                            else:
                                model = eval(m)
                            query = model.flexbox_query('', limit=limit)
                    aData = {"results": [{"id": x.id, "name": x.flexbox_repr(), 'alias': x.flexbox_alias() if hasattr(x, 'flexbox_alias') else []} for x in query]}
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acción no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)