# coding=utf-8
import json
import csv
import os
import sys
import threading
from decimal import Decimal

import pyqrcode
import subprocess
import io as StringIO
from django.core.files import File
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.db import transaction
from rest_framework.exceptions import ParseError
from rest_framework.parsers import MultiPartParser, FormParser, FileUploadParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from api.helpers.response_herlper import Helper_Response
from api.views.wu.permission import HasCsrfTokenValid
from settings import SITE_STORAGE
from sga.funciones import convertir_fecha_invertida, generar_nombre
from soap.functions import get_setting_soap, SERVICE_WESTERN_UNION_PK
from soap.models import ConciliacionPago, PagoBanco, ConciliacionDetallePago


class ConciliacionAPIView(APIView):
    permission_classes = (HasCsrfTokenValid,)
    # parser_class = (MultiPartParser, FormParser,)

    def post(self, request, format=None, *args, **kwargs):
        with transaction.atomic():
            try:
                if 'multipart/form-data' in request.content_type:
                    eRequest = request._request.POST
                    # eFiles = request._request.FILES
                else:
                    eRequest = request.data
                # eRequest = request.data
                fecha_conciliacion = eRequest.get('fecha', '')
                transacciones_str=eRequest.get('transacciones', [])
                fecha_conciliacion = convertir_fecha_invertida(fecha_conciliacion)
                service_id = SERVICE_WESTERN_UNION_PK
                eUser = request.user
                if not transacciones_str:
                    raise NameError(u"Por favor llene el campo transacciones con los parametros a solicitar.")
                transacciones = json.loads(transacciones_str)
                for transaccion in transacciones:
                    for clave, valor in transaccion.items():
                        if not valor:
                            raise NameError(f"Campo {clave} requerido")
                        if clave in ['num_transaccion','id','tipo_ambiente']:
                            try:
                                valor_c = int(valor)
                                if valor_c == 0:
                                    raise NameError(f"Campo {clave} tiene que ser diferente de 0")
                            except Exception as ex:
                                raise NameError(f"Campo {clave} tiene que ser de tipo entero (int)")
                        elif clave == 'fecha':
                            try:
                                fecha = datetime.strptime(valor, "%Y/%m/%d")
                            except Exception as ex:
                                raise NameError(f"Campo {clave} tiene que ser de tipo {clave} (date)")
                        elif clave == 'hora':
                            try:
                                v=valor.split(':')
                                if len(v)==3:
                                    hora = datetime.strptime(valor, "%H:%M:%S").time()
                                elif len(v) == 2:
                                    hora = datetime.strptime(valor, "%H:%M").time()
                                elif len(v) == 1:
                                    hora = datetime.strptime(valor, "%H").time()

                            except Exception as ex:
                                raise NameError(f"Campo {clave} tiene que ser de tipo {clave} (time)")
                        elif clave in ['valor_cobrado', 'valor_conciliado']:
                            try:
                                valor_c=float(valor)
                            except Exception as ex:
                                raise NameError(f"Campo {clave} tiene que ser de tipo float")
                setting = get_setting_soap(tipo=1, service_id=service_id)
                if not setting:
                    raise NameError(u"Configuración no existe")
                if not setting.get_usuarios().filter(username=eUser.username).exists():
                    raise NameError(u"Configuración no existe")
                try:
                    eConciliacionPago = ConciliacionPago.objects.get(config=setting, tipo_ambiente=setting.tipo_ambiente, fecha_conciliacion=fecha_conciliacion)
                    if eConciliacionPago.procesado:
                        raise NameError(f"Conciliación de la fecha {fecha_conciliacion.strftime('%Y-%m-%d')} fue procesado el {eConciliacionPago.fecha_procesado.strftime('%Y-%m-%d')} a las {eConciliacionPago.hora_procesado.strftime('%H:%M:%S')}")
                except ObjectDoesNotExist:
                    raise NameError(u"No se encontro la conciliación")
                # if not 'archivo' in eFiles:
                #     raise NameError(u"No se encontro archivo de conciliación")
                # nFile = None
                # if 'archivo' in eFiles:
                #     nFile = eFiles['archivo']
                #     extFile = nFile._name.split('.')
                #     tamFile = len(extFile)
                #     exteFile = extFile[tamFile - 1]
                #     if nFile.size > 2500000:
                #         raise NameError(u"Error al cargar, el archivo es mayor a 25 Mb.")
                #     if not exteFile.lower() == 'csv':
                #         raise NameError(u"Error al cargar, solo se permiten archivos .csv")
                # nFile._name = generar_nombre(f"archivo_procesado_", nFile._name)
                # directory = os.path.join(os.path.join(SITE_STORAGE, 'media', 'soap', 'western_union', 'conciliacion', str(fecha_conciliacion.year), f'{fecha_conciliacion.month:02d}', f'{fecha_conciliacion.day:02d}', ''))
                # os.makedirs(directory, exist_ok=True)
                # eConciliacionPago.archivo_procesado = nFile
                # eConciliacionPago.save(request)
                # with open(eConciliacionPago.archivo_procesado.path, newline='', encoding="utf8") as f:
                #     reader = csv.reader(f, delimiter='|', quoting=csv.QUOTE_MINIMAL)
                #     contador = 0
                #     for row in reader:
                #         if contador > 0:
                #             print(row)
                return Response(data={'message': f'Transacción fue procesada correctamente','isSuccess':True}, status=status.HTTP_200_OK)
            except Exception as ex:
                print(f'Error on line {sys.exc_info()[-1].tb_lineno} {ex.__str__()}')
                transaction.set_rollback(True)
                return Response(data={'message': f'{ex.__str__()}','isSuccess':False}, status=status.HTTP_401_UNAUTHORIZED)

    # def get(self, request):
    #     with transaction.atomic():
    #         try:
    #             fecha_conciliacion = request.query_params.get('fecha', '')
    #             fecha_conciliacion = convertir_fecha_invertida(fecha_conciliacion)
    #             service_id = SERVICE_WESTERN_UNION_PK
    #             eUser = request.user
    #             setting = get_setting_soap(tipo=1, service_id=service_id)
    #             if not setting:
    #                 raise NameError(u"Configuración no existe")
    #             if not setting.get_usuarios().filter(username=eUser.username).exists():
    #                 raise NameError(u"Configuración no existe")
    #             hora_conciliacion = setting.hora_conciliacion if setting.hora_conciliacion else datetime(fecha_conciliacion.year, fecha_conciliacion.month, fecha_conciliacion.day, 23, 59, 59).time()
    #             try:
    #                 eConciliacionPago = ConciliacionPago.objects.get(config=setting, tipo_ambiente=setting.tipo_ambiente, fecha_conciliacion=fecha_conciliacion, hora_conciliacion=hora_conciliacion)
    #                 if eConciliacionPago.procesado:
    #                     raise NameError(f"Conciliación de la fecha {fecha_conciliacion.strftime('%Y-%m-%d')} fue procesado el {eConciliacionPago.fecha_procesado.strftime('%Y-%m-%d')} a las {eConciliacionPago.hora_procesado.strftime('%H:%M:%S')}")
    #             except ObjectDoesNotExist:
    #                 eConciliacionPago = ConciliacionPago(config=setting,
    #                                                      tipo_ambiente=setting.tipo_ambiente,
    #                                                      fecha_conciliacion=fecha_conciliacion,
    #                                                      hora_conciliacion=hora_conciliacion,
    #                                                      fecha_transaccion=datetime.now().date(),
    #                                                      hora_transaccion=datetime.now().time())
    #                 eConciliacionPago.save(request)
    #             myData = [["id", "num_transaccion", "tipo_ambiente", "detalle", "fecha", "hora", "valor_cobrado"]]
    #             for ePagoBanco in PagoBanco.objects.filter(status=True, reverso=False, config=setting, tipo_ambiente=setting.tipo_ambiente, fecha_transaccion=fecha_conciliacion, hora_transaccion__lte=hora_conciliacion):
    #                 try:
    #                     eConciliacionDetallePago = ConciliacionDetallePago.objects.get(conciliacion=eConciliacionPago, pago=ePagoBanco)
    #                 except ObjectDoesNotExist:
    #                     eConciliacionDetallePago = ConciliacionDetallePago(conciliacion=eConciliacionPago,
    #                                                                        pago=ePagoBanco,
    #                                                                        valor_cobrado=ePagoBanco.valor,
    #                                                                        valor_conciliado=0)
    #                     eConciliacionDetallePago.save(request)
    #                 myData.append([u"%s" % eConciliacionDetallePago.pago_id,
    #                                u"%s" % eConciliacionDetallePago.pago.num_transaccion,
    #                                u"%s" % eConciliacionDetallePago.pago.get_tipo_ambiente_display(),
    #                                u"%s" % eConciliacionDetallePago.pago.rubro.nombre,
    #                                u"%s" % eConciliacionDetallePago.pago.fecha_transaccion.strftime('%Y-%m-%d'),
    #                                u"%s" % eConciliacionDetallePago.pago.hora_transaccion.strftime('%H:%M:%S'),
    #                                u"%s" % eConciliacionDetallePago.pago.hora_transaccion.strftime('%H:%M:%S'),
    #                                u"%s" % Decimal(eConciliacionDetallePago.pago.valor).quantize(Decimal('.01'))
    #                                ])
    #             ahora = datetime.now()
    #             directory = os.path.join(os.path.join(SITE_STORAGE, 'media', 'soap', 'western_union', 'conciliacion', str(fecha_conciliacion.year), f'{fecha_conciliacion.month:02d}', f'{fecha_conciliacion.day:02d}', ''))
    #             file_name = f'archivo_original_{ahora.strftime("%Y%m%d_%H%M%S")}.csv'
    #             os.makedirs(directory, exist_ok=True)
    #             ruta_file = '{}{}'.format(directory, file_name)
    #             with open(ruta_file, 'w') as csvfile:
    #                 writer = csv.writer(csvfile, delimiter='|', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    #                 for data in myData:
    #                     writer.writerow(data)
    #             csvfile.close()
    #             eConciliacionPago.archivo_original.name = f'soap/western_union/conciliacion/{str(fecha_conciliacion.year)}/{fecha_conciliacion.month:02d}/{fecha_conciliacion.day:02d}/{file_name}'
    #             eConciliacionPago.save(request)
    #             return Response(data={'archivo': f"https://sga.unemi.edu.ec{eConciliacionPago.archivo_original.url}"}, status=status.HTTP_200_OK)
    #         except Exception as ex:
    #             transaction.set_rollback(True)
    #             return Response(data={'message': f'{ex.__str__()}'}, status=status.HTTP_401_UNAUTHORIZED)
