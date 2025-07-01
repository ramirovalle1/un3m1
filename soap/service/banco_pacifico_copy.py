# -*- coding: latin-1 -*-
from __future__ import unicode_literals
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from spyne.application import Application
from spyne.decorator import rpc
from spyne.util.django import DjangoComplexModel, DjangoService, cdict
from spyne.model.primitive import Unicode, Integer, Double, String, DateTime, AnyDict
from spyne.protocol.soap import Soap11, Soap12
from spyne.server.django import DjangoApplication, DjangoView
from spyne.service import ServiceBase, Service
import json

from sagest.models import Rubro, CuentaBanco
from settings import FORMA_PAGO_DEPOSITO, BANCO_PACIFICO_ID
from sga.funciones import convertir_hora, convertir_hora_completa
from sga.models import *
from spyne import Iterable, Array
from spyne import ComplexModel
from django.forms.models import model_to_dict
from django.db import IntegrityError, transaction
from spyne.error import ResourceNotFoundError
from spyne.model.fault import Fault
from django.db.models.deletion import ProtectedError

from soap.decorators.banco_pacifico import login_or_basic_auth_required
from soap.functions import get_setting_soap, set_logging, LOGGING_FILE_PROCESADO, LOGGING_FILE_WEBSERVICE, \
    LOGGING_BANCO_PACIFICO, LOGGING_LEVEL_DEBUG, LOGGING_LEVEL_INFO, LOGGING_LEVEL_WARNING, LOGGING_LEVEL_ERROR
from soap.models import PagoBanco, ReversoPagoBanco


class ePersona(DjangoComplexModel):
    class Attributes(DjangoComplexModel.Attributes):
        django_model = Persona
        # django_exclude = ['excluded_field']


class ServiceCobro(Service):

    @rpc(String, _returns=AnyDict)
    def testConnection(ctx, parametro):
        try:
            request = ctx.transport.req
            eUser = request.user
            if eUser.id is None:
                CodigoRespuesta = "0047"
                raise NameError(u"Usuario no identificado")
            CodigoRespuesta = ""
            setting = get_setting_soap(tipo=1, banco_id=BANCO_PACIFICO_ID)
            if not setting:
                CodigoRespuesta = "0047"
                raise NameError(u"Servidor no disponible")
            if not setting.get_usuarios().filter(username=eUser.username).exists():
                CodigoRespuesta = "0047"
                raise NameError(u"Servidor no disponible")
            data = {'CodigoRespuesta': "0001",
                    'MensajeRespuesta': "OK",
                    'Ambiente': setting.get_tipo_ambiente_display(),
                    }
            print(data)
            set_logging(LOGGING_BANCO_PACIFICO, LOGGING_LEVEL_INFO, LOGGING_FILE_WEBSERVICE, json.dumps({"testConnection": data}))
            return data
        except Exception as ex:
            data = {'CodigoRespuesta': CodigoRespuesta,
                    'MensajeRespuesta': ex.__str__(),
                    'Ambiente': setting.get_tipo_ambiente_display(),
                    }
            print(data)
            set_logging(LOGGING_BANCO_PACIFICO, LOGGING_LEVEL_ERROR, LOGGING_FILE_WEBSERVICE, json.dumps({"testConnection": data}))
            return data

    @rpc(Integer, Integer, Integer, Integer, Integer, Integer, String, Integer, String, String, String, String, String, String, String, String, String, String, String, Integer, _returns=AnyDict)
    def consultarTransaccion(ctx, NumeroTransaccion, Producto, TipoTransaccion, FechaTransaccion, FechaContable, HoraTransaccion, CanalProceso, Agencia, Terminal, Servicio, TipoCodigo, Codigo, Auxiliar, TipoNuc, NumeroIdentificacionPago, CodigoAdicional, NombreBeneficiario, CanalUci, DispUci, TimeOut):
        try:
            persona = None
            data = {}
            CodigoRespuesta = ""
            elementos = []
            request = ctx.transport.req
            eUser = request.user
            if eUser.id is None:
                CodigoRespuesta = "0047"
                raise NameError(u"Usuario no identificado")
            CodigoRespuesta = ""
            setting = get_setting_soap(tipo=1, banco_id=BANCO_PACIFICO_ID)
            if not setting:
                CodigoRespuesta = "0047"
                raise NameError(u"Servidor no disponible")
            if not setting.get_usuarios().filter(username=eUser.username).exists():
                CodigoRespuesta = "0047"
                raise NameError(u"Servidor no disponible")

            if TipoNuc == 'C':
                if not Persona.objects.values("id").filter(cedula=NumeroIdentificacionPago).exists():
                    CodigoRespuesta = "0047"
                    raise NameError(u"Persona con número de cedula no encontrada")
                persona = Persona.objects.filter(cedula=NumeroIdentificacionPago)[0]
            elif TipoNuc == 'P':
                if not Persona.objects.values("id").filter(pasaporte=NumeroIdentificacionPago).exists():
                    CodigoRespuesta = "0047"
                    raise NameError(u"Persona con pasaporte no encontrada")
                persona = Persona.objects.filter(pasaporte=NumeroIdentificacionPago)[0]
            elif TipoNuc == 'R':
                if not Persona.objects.values("id").filter(ruc=NumeroIdentificacionPago).exists():
                    CodigoRespuesta = "0047"
                    raise NameError(u"Persona/Sociedad con RUC no encontrada")
                persona = Persona.objects.filter(pasaporte=NumeroIdentificacionPago)[0]
            if not persona:
                CodigoRespuesta = "0047"
                raise NameError(u"Persona/Sociedad no encontrada")
            pagos = PagoBanco.objects.filter(persona=persona, config=setting, status=True).distinct()
            rubros = Rubro.objects.filter(persona=persona, epunemi=False, cancelado=False, saldo__gt=0, fecha__lte=datetime.now(), status=True).exclude(pk__in=pagos.values_list("rubro_id", flat=True)).order_by('fecha')
            for rubro in rubros:
                elementos.append({"NombreCliente": persona.nombre_completo_inverso(),
                                  "ValorAPagar": null_to_decimal(rubro.saldo, 2),
                                  "TipoIdentificacion": TipoNuc,
                                  "NumeroIdentificacion": NumeroIdentificacionPago,
                                  "Referencia01": rubro.nombre,
                                  "Referencia02": "",
                                  "Codigo": rubro.id,
                                  "ValorCapital": 0.00,
                                  "ValorInteres": 0.00,
                                  "ValorMora": 0.00,
                                  "ValorComi": 0.00,
                                  "ValorImpuesto": 0.00,
                                  })
            data = {'NumeroTransaccion': NumeroTransaccion,
                    'Producto': Producto,
                    'TipoTransaccion': TipoTransaccion,
                    'FechaTransaccion': FechaTransaccion,
                    'FechaContable': FechaContable,
                    'HoraTransaccion': HoraTransaccion,
                    'CanalProceso': CanalProceso,
                    'Agencia': Agencia,
                    'Terminal': Terminal,
                    'Servicio': Servicio,
                    'CodigoRespuesta': "0001",
                    'MensajeRespuesta': "OK",
                    'CantidadRegistros': rubros.count(),
                    'elementos': elementos,
                    }
            print(data)
            set_logging(LOGGING_BANCO_PACIFICO, LOGGING_LEVEL_INFO, LOGGING_FILE_WEBSERVICE, json.dumps({"ConsultaValores": data}))
            return data
        except Exception as ex:
            data = {'NumeroTransaccion': NumeroTransaccion,
                    'Producto': Producto,
                    'TipoTransaccion': TipoTransaccion,
                    'FechaTransaccion': FechaTransaccion,
                    'FechaContable': FechaContable,
                    'HoraTransaccion': HoraTransaccion,
                    'CanalProceso': CanalProceso,
                    'Agencia': Agencia,
                    'Terminal': Terminal,
                    'Servicio': Servicio,
                    'CodigoRespuesta': CodigoRespuesta,
                    'MensajeRespuesta': ex.__str__(),
                    'CantidadRegistros': 0,
                    'elementos': elementos,
                    }
            print(data)
            set_logging(LOGGING_BANCO_PACIFICO, LOGGING_LEVEL_ERROR, LOGGING_FILE_WEBSERVICE, json.dumps({"ConsultaValores": data}))
            return data

    @rpc(Integer, Integer, Integer, Integer, Integer, Integer, String, Integer, String, String, String, String, String, String, Double, String, String, String, String, Integer, String, String, Integer, _returns=AnyDict)
    def pagarTransaccion(ctx, NumeroTransaccion, Producto, TipoTransaccion, FechaTransaccion, FechaContable, HoraTransaccion, CanalProceso, Agencia, Terminal, Servicio, TipoCodigo, Codigo, TipoIdentificacion, NumeroIdentificacionPago, ValorAPagar, ReferenciaOrdenante, ReferenciaComproba, DatosAdicionales, Nut, CantidadRubros, CanalUci, DispUci, TimeOut):
        with transaction.atomic():
            try:
                persona = None
                data = {}
                CodigoRespuesta = ""
                request = ctx.transport.req
                eUser = request.user
                if eUser.id is None:
                    CodigoRespuesta = "0047"
                    raise NameError(u"Usuario no identificado")
                CodigoRespuesta = ""
                setting = get_setting_soap(tipo=1, banco_id=BANCO_PACIFICO_ID)
                if not setting:
                    CodigoRespuesta = "0047"
                    raise NameError(u"Servidor no disponible")
                if not setting.get_usuarios().filter(username=eUser.username).exists():
                    CodigoRespuesta = "0047"
                    raise NameError(u"Servidor no disponible")

                if TipoIdentificacion == 'C':
                    if not Persona.objects.values("id").filter(cedula=NumeroIdentificacionPago).exists():
                        CodigoRespuesta = "0047"
                        raise NameError(u"Persona con número de cedula no encontrada")
                    persona = Persona.objects.filter(cedula=NumeroIdentificacionPago)[0]
                elif TipoIdentificacion == 'P':
                    if not Persona.objects.values("id").filter(pasaporte=NumeroIdentificacionPago).exists():
                        CodigoRespuesta = "0047"
                        raise NameError(u"Persona con pasaporte no encontrada")
                    persona = Persona.objects.filter(pasaporte=NumeroIdentificacionPago)[0]
                elif TipoIdentificacion == 'R':
                    if not Persona.objects.values("id").filter(ruc=NumeroIdentificacionPago).exists():
                        CodigoRespuesta = "0047"
                        raise NameError(u"Persona/Sociedad con RUC no encontrada")
                    persona = Persona.objects.filter(pasaporte=NumeroIdentificacionPago)[0]
                if not persona:
                    CodigoRespuesta = "0047"
                    raise NameError(u"Persona/Sociedad no encontrada")
                if not Codigo:
                    CodigoRespuesta = "0047"
                    raise NameError(u"Código no encontrado")
                if not Rubro.objects.values("id").filter(persona=persona, pk=int(Codigo), cancelado=False).exists():
                    CodigoRespuesta = "0047"
                    raise NameError(u"Código no encontrado")
                rubro = Rubro.objects.filter(persona=persona, pk=int(Codigo), cancelado=False)[0]
                # cuenta = setting.cuenta
                if PagoBanco.objects.values("id").filter(persona=persona, config=setting, rubro=rubro, valor=ValorAPagar).exists():
                    CodigoRespuesta = "9277"
                    raise NameError(u"Rubro ya se encuentra pagado")

                pago = PagoBanco(config=setting,
                                 num_transaccion=NumeroTransaccion,
                                 producto=Producto,
                                 tipo_transaccion=int(TipoTransaccion),
                                 fecha_transaccion=convertir_fecha_invertida(f"{str(FechaTransaccion)[0:4]}-{str(FechaTransaccion)[4:6]}-{str(FechaTransaccion)[6:8]}"),
                                 fecha_contable=convertir_fecha_invertida(f"{str(FechaContable)[0:4]}-{str(FechaContable)[4:6]}-{str(FechaContable)[6:8]}"),
                                 hora_transaccion=convertir_hora_completa(f"{str(HoraTransaccion)[0:2]}:{str(HoraTransaccion)[2:4]}:{str(HoraTransaccion)[4:6]}"),
                                 canal_proceso=CanalProceso,
                                 agencia=Agencia,
                                 terminal=Terminal,
                                 servicio=Servicio,
                                 rubro=rubro,
                                 valor=ValorAPagar,
                                 persona=persona,
                                 procesado=False,
                                 )
                pago.save()

                data = {'NumeroTransaccion': NumeroTransaccion,
                        'Producto': Producto,
                        'TipoTransaccion': TipoTransaccion,
                        'FechaTransaccion': FechaTransaccion,
                        'FechaContable': FechaContable,
                        'HoraTransaccion': HoraTransaccion,
                        'CanalProceso': CanalProceso,
                        'Agencia': Agencia,
                        'Terminal': Terminal,
                        'Servicio': Servicio,
                        'ValorBaseImponible': 0.00,
                        'ValorIVAServicio': 0.00,
                        'ValorIvaBien': 0.00,
                        'NumeroTransaccionEmpresa': "",
                        'CodigoRespuesta': "0001",
                        'MensajeRespuesta': u"Transacción Exitosa",
                        }
                print(data)
                set_logging(LOGGING_BANCO_PACIFICO, LOGGING_LEVEL_INFO, LOGGING_FILE_WEBSERVICE, json.dumps({"PagarValores": data}))
                return data
            except Exception as ex:
                transaction.set_rollback(True)
                data = {'NumeroTransaccion': NumeroTransaccion,
                        'Producto': Producto,
                        'TipoTransaccion': TipoTransaccion,
                        'FechaTransaccion': FechaTransaccion,
                        'FechaContable': FechaContable,
                        'HoraTransaccion': HoraTransaccion,
                        'CanalProceso': CanalProceso,
                        'Agencia': Agencia,
                        'Terminal': Terminal,
                        'Servicio': Servicio,
                        'ValorBaseImponible': 0.00,
                        'ValorIVAServicio': 0.00,
                        'ValorIvaBien': 0.00,
                        'NumeroTransaccionEmpresa': "",
                        'CodigoRespuesta': CodigoRespuesta,
                        'MensajeRespuesta': ex.__str__(),
                        }
                print(data)
                set_logging(LOGGING_BANCO_PACIFICO, LOGGING_LEVEL_ERROR, LOGGING_FILE_WEBSERVICE, json.dumps({"PagarValores": data}))
                return data

    @rpc(Integer, Integer, Integer, Integer, Integer, Integer, String, Integer, String, String, String, Double, String, Integer, Integer, String, String, String, String, String, Integer, _returns=AnyDict)
    def reversarTransaccion(ctx, NumeroTransaccion, Producto, TipoTransaccion, FechaTransaccion, FechaContable, HoraTransaccion, CanalProceso, Agencia, Terminal, Servicio, NumeroIdentificacionPago, ValorAPagar, Codigo, NumeroTransaccionReversar, NumeroTransaccionReversarEmp, DatosAdicionales, NumeroTransaccionOpcional, NutPago,  CanalUci, DispUci, TimeOut):
        with transaction.atomic():
            try:
                persona = None
                data = {}
                CodigoRespuesta = ""
                request = ctx.transport.req
                eUser = request.user
                if eUser.id is None:
                    CodigoRespuesta = "0047"
                    raise NameError(u"Usuario no identificado")
                CodigoRespuesta = ""
                setting = get_setting_soap(tipo=1, banco_id=BANCO_PACIFICO_ID)
                if not setting:
                    CodigoRespuesta = "0047"
                    raise NameError(u"Servidor no disponible")
                if not setting.get_usuarios().filter(username=eUser.username).exists():
                    CodigoRespuesta = "0047"
                    raise NameError(u"Servidor no disponible")
                if not PagoBanco.objects.values("id").filter(num_transaccion=NumeroTransaccion, config=setting).exists():
                    CodigoRespuesta = "0047"
                    raise NameError(u"Pago no encontrado")

                pago = PagoBanco.objects.filter(num_transaccion=NumeroTransaccion, config=setting)[0]
                if pago.reverso:
                    CodigoRespuesta = "0047"
                    raise NameError(u"Pago ya fure anulado con anterioridad")
                if pago.procesado:
                    CodigoRespuesta = "0047"
                    raise NameError(u"Pago ya fue procesado por la institución. Acercarse a Tesoreria")
                reverso = ReversoPagoBanco(pago=pago,
                                           fecha_transaccion=convertir_fecha_invertida(f"{str(FechaTransaccion)[0:4]}-{str(FechaTransaccion)[4:6]}-{str(FechaTransaccion)[6:8]}"),
                                           fecha_contable=convertir_fecha_invertida(f"{str(FechaContable)[0:4]}-{str(FechaContable)[4:6]}-{str(FechaContable)[6:8]}"),
                                           hora_transaccion=convertir_hora_completa(f"{str(HoraTransaccion)[0:2]}:{str(HoraTransaccion)[2:4]}:{str(HoraTransaccion)[4:6]}"),
                                           canal_proceso=CanalProceso,
                                           agencia=Agencia,
                                           terminal=Terminal,
                                           servicio=Servicio,
                                           )
                reverso.save()
                data = {'NumeroTransaccion': NumeroTransaccion,
                        'Producto': Producto,
                        'TipoTransaccion': TipoTransaccion,
                        'FechaTransaccion': FechaTransaccion,
                        'FechaContable': FechaContable,
                        'HoraTransaccion': HoraTransaccion,
                        'CanalProceso': CanalProceso,
                        'Agencia': Agencia,
                        'Terminal': Terminal,
                        'Servicio': Servicio,
                        'CodigoRespuesta': "0001",
                        'MensajeRespuesta': u"TRANSACCIÓN REVERSA EXITOSA",
                        }
                print(data)
                set_logging(LOGGING_BANCO_PACIFICO, LOGGING_LEVEL_INFO, LOGGING_FILE_WEBSERVICE, json.dumps({"ReversoValores": data}))
                return data
            except Exception as ex:
                transaction.set_rollback(True)
                data = {'NumeroTransaccion': NumeroTransaccion,
                        'Producto': Producto,
                        'TipoTransaccion': TipoTransaccion,
                        'FechaTransaccion': FechaTransaccion,
                        'FechaContable': FechaContable,
                        'HoraTransaccion': HoraTransaccion,
                        'CanalProceso': CanalProceso,
                        'Agencia': Agencia,
                        'Terminal': Terminal,
                        'Servicio': Servicio,
                        'CodigoRespuesta': CodigoRespuesta,
                        'MensajeRespuesta': ex.__str__(),
                        }
                print(data)
                set_logging(LOGGING_BANCO_PACIFICO, LOGGING_LEVEL_ERROR, LOGGING_FILE_WEBSERVICE, json.dumps({"ReversoValores": data}))
                return data


url_banco_pacifico = csrf_exempt(DjangoView.as_view(services=[ServiceCobro], tns='web.bancopacifico.service', in_protocol=Soap12(validator="lxml"), out_protocol=Soap12()))


@login_or_basic_auth_required
def banco_pacifico_cobro(request):
    return url_banco_pacifico(request)