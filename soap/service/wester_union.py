# -*- coding: latin-1 -*-
from __future__ import unicode_literals
import json
import xml.etree.ElementTree as ET
from django.contrib.auth import authenticate
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt
from spyne.decorator import rpc
from spyne.util.django import DjangoComplexModel, DjangoService, cdict
from spyne.model.primitive import Unicode, Integer, Double, String, DateTime, AnyDict
from spyne.protocol.soap import Soap11, Soap12
from spyne.server.django import DjangoApplication, DjangoView
from spyne.service import ServiceBase, Service
from sagest.models import Rubro, CuentaBanco
from settings import FORMA_PAGO_DEPOSITO, BANCO_PACIFICO_ID, DEBUG
from sga.funciones import convertir_hora, convertir_hora_completa
from sga.models import *
from spyne import Iterable, Array, AnyXml, XmlData, XmlAttribute
from spyne import ComplexModel
from spyne.util.xml import get_object_as_xml
from django.forms.models import model_to_dict
from django.db import IntegrityError, transaction
from spyne.error import ResourceNotFoundError
from spyne.model.fault import Fault
from django.db.models.deletion import ProtectedError

from soap.decorators.banco_pacifico import login_or_basic_auth_required
from soap.functions import get_setting_soap, set_logging, LOGGING_FILE_PROCESADO, LOGGING_FILE_WEBSERVICE, \
    LOGGING_WESTERN_UNION, LOGGING_LEVEL_DEBUG, LOGGING_LEVEL_INFO, LOGGING_LEVEL_WARNING, LOGGING_LEVEL_ERROR, \
    SERVICE_WESTERN_UNION_PK
from soap.models import PagoBanco, ReversoPagoBanco


class ePersona(DjangoComplexModel):
    class Attributes(DjangoComplexModel.Attributes):
        django_model = Persona
        # django_exclude = ['excluded_field']


# class ParamsConsultarTransaccion(ComplexModel):


class Usuario(object):
    username = None
    password = None
    eUser = None
    __cdata = None

    def __init__(self, cdata):
        self.__cdata = cdata

    def procesar_data(self):
        trama = ET.ElementTree(ET.fromstring(self.__cdata)).getroot()
        username = trama.find('User')
        password = trama.find('Password')
        if username is None:
            raise NameError(u"Parametro User no encontrado")
        if password is None:
            raise NameError(u"Parametro Password no encontrado")
        self.username = username.text.lower().strip()
        self.password = password.text

    def autentificar(self, setting):
        if not setting.get_usuarios().filter(username=self.username).exists():
            raise NameError(u"Servidor no disponible")
        eUser = authenticate(username=self.username, password=self.password)
        if not eUser:
            raise NameError(u"Usuario y contraseña incorrecto")
        # SI EL USUARIO ESTA ACTIVO
        if not eUser.is_active:
            raise NameError(u"Usuario no activo")
        self.eUser = eUser


class DataBanco(object):
    NumeroTransaccion = None
    Producto = None
    TipoTransaccion = None
    FechaTransaccion = None
    FechaContable = None
    HoraTransaccion = None
    CanalProceso = None
    Agencia = None
    Terminal = None
    Servicio = None
    TipoCodigo = None
    Codigo = None
    Auxiliar = None
    TipoNuc = None
    TipoIdentificacion = None
    NumeroIdentificacionPago = None
    CodigoAdicional = None
    NombreBeneficiario = None
    CanalUci = None
    DispUci = None
    TimeOut = None
    __ePersona = None
    __cdata = None
    CodigoRespuesta = "0047"
    MensajeRespuesta = None
    CantidadRegistros = 0
    ValorAPagar = 0
    ReferenciaOrdenante = None
    ReferenciaComproba = None
    DatosAdicionales = None
    Nut = None
    CantidadRubros = 0
    NumeroTransaccionReversar = 0
    NumeroTransaccionReversarEmp = 0
    NumeroTransaccionOpcional = None
    NutPago = None
    elementos = []

    def __init__(self):
        super(DataBanco, self).__init__()

    def dictConsulta(self):
        aData = {
            "NumeroTransaccion": self.NumeroTransaccion,
            "Producto": self.Producto,
            "TipoTransaccion": self.TipoTransaccion,
            "FechaTransaccion": self.FechaTransaccion,
            "FechaContable": self.FechaContable,
            "HoraTransaccion": self.HoraTransaccion,
            "CanalProceso": self.CanalProceso,
            "Agencia": self.Agencia,
            "Terminal": self.Terminal,
            "Servicio": self.Servicio,
            "TipoCodigo": self.TipoCodigo,
            "Codigo": self.Codigo,
            "Auxiliar": self.Auxiliar,
            "TipoNuc": self.TipoNuc,
            "NumeroIdentificacionPago": self.NumeroIdentificacionPago,
            "CodigoAdicional": self.CodigoAdicional,
            "NombreBeneficiario": self.NombreBeneficiario,
            "CanalUci": self.CanalUci,
            "DispUci": self.DispUci,
            "TimeOut": self.TimeOut,
            "CodigoRespuesta": self.CodigoRespuesta,
            "MensajeRespuesta": self.MensajeRespuesta,
            "CantidadRegistros": self.CantidadRegistros,
            "elementos": json.dumps(self.elementos),
        }
        return aData

    def dictPagar(self):
        aData = {
            "NumeroTransaccion": self.NumeroTransaccion,
            "Producto": self.Producto,
            "TipoTransaccion": self.TipoTransaccion,
            "FechaTransaccion": self.FechaTransaccion,
            "FechaContable": self.FechaContable,
            "HoraTransaccion": self.HoraTransaccion,
            "CanalProceso": self.CanalProceso,
            "Agencia": self.Agencia,
            "Terminal": self.Terminal,
            "Servicio": self.Servicio,
            "Codigo": self.Codigo,
            "TipoIdentificacion": self.TipoIdentificacion,
            "NumeroIdentificacionPago": self.NumeroIdentificacionPago,
            "ValorAPagar": self.ValorAPagar,
            "ReferenciaOrdenante": self.ReferenciaOrdenante,
            "ReferenciaComproba": self.ReferenciaComproba,
            "DatosAdicionales": self.DatosAdicionales,
            "Nut": self.Nut,
            "CantidadRubros": self.CantidadRubros,
            "CanalUci": self.CanalUci,
            "DispUci": self.DispUci,
            "TimeOut": self.TimeOut,
            "CodigoRespuesta": self.CodigoRespuesta,
            "MensajeRespuesta": self.MensajeRespuesta
        }
        return aData

    def dictReversar(self):
        aData = {
            "NumeroTransaccion": self.NumeroTransaccion,
            "Producto": self.Producto,
            "TipoTransaccion": self.TipoTransaccion,
            "FechaTransaccion": self.FechaTransaccion,
            "FechaContable": self.FechaContable,
            "HoraTransaccion": self.HoraTransaccion,
            "CanalProceso": self.CanalProceso,
            "Agencia": self.Agencia,
            "Terminal": self.Terminal,
            "Servicio": self.Servicio,
            "NumeroIdentificacionPago": self.NumeroIdentificacionPago,
            "ValorAPagar": self.ValorAPagar,
            "Codigo": self.Codigo,
            "NumeroTransaccionReversar": self.NumeroTransaccionReversar,
            "NumeroTransaccionReversarEmp": self.NumeroTransaccionReversarEmp,
            "DatosAdicionales": self.DatosAdicionales,
            "NumeroTransaccionOpcional": self.NumeroTransaccionOpcional,
            "NutPago": self.NutPago,
            "CanalUci": self.CanalUci,
            "DispUci": self.DispUci,
            "TimeOut": self.TimeOut,
            "CodigoRespuesta": self.CodigoRespuesta,
            "MensajeRespuesta": self.MensajeRespuesta
        }
        return aData

    def procesarConsulta(self, cdata, setting):
        self.__cdata = cdata
        eUsuario = Usuario(cdata=cdata)
        eUsuario.procesar_data()
        eUsuario.autentificar(setting)
        trama = ET.ElementTree(ET.fromstring(self.__cdata)).getroot()
        NumeroTransaccion = trama.find('NumeroTransaccion')
        if NumeroTransaccion is None:
            raise NameError(u"Parametro NumeroTransaccion no encontrado"[:39])
        self.NumeroTransaccion = NumeroTransaccion.text
        Producto = trama.find('Producto')
        if Producto is None:
            raise NameError(u"Parametro Producto no encontrado"[:39])
        self.Producto = Producto.text
        TipoTransaccion = trama.find('TipoTransaccion')
        if TipoTransaccion is None:
            raise NameError(u"Parametro TipoTransaccion no encontrado"[:39])
        self.TipoTransaccion = TipoTransaccion.text
        FechaTransaccion = trama.find('FechaTransaccion')
        if FechaTransaccion is None:
            raise NameError(u"Parametro FechaTransaccion no encontrado"[:39])
        self.FechaTransaccion = FechaTransaccion.text
        FechaContable = trama.find('FechaContable')
        if FechaContable is None:
            raise NameError(u"Parametro FechaContable no encontrado"[:39])
        self.FechaContable = FechaContable.text
        HoraTransaccion = trama.find('HoraTransaccion')
        if HoraTransaccion is None:
            raise NameError(u"Parametro HoraTransaccion no encontrado"[:39])
        self.HoraTransaccion = HoraTransaccion.text
        CanalProceso = trama.find('CanalProceso')
        if CanalProceso is None:
            raise NameError(u"Parametro CanalProceso no encontrado"[:39])
        self.CanalProceso = CanalProceso.text
        Agencia = trama.find('Agencia')
        if Agencia is None:
            raise NameError(u"Parametro Agencia no encontrado"[:39])
        self.Agencia = Agencia.text
        Terminal = trama.find('Terminal')
        if Terminal is None:
            raise NameError(u"Parametro Terminal no encontrado"[:39])
        self.Terminal = Terminal.text
        Servicio = trama.find('Servicio')
        if Servicio is None:
            raise NameError(u"Parametro Servicio no encontrado"[:39])
        self.Servicio = Servicio.text
        TipoCodigo = trama.find('TipoCodigo')
        if TipoCodigo is None:
            raise NameError(u"Parametro TipoCodigo no encontrado"[:39])
        self.TipoCodigo = TipoCodigo.text
        Codigo = trama.find('Codigo')
        if Codigo is None:
            raise NameError(u"Parametro Codigo no encontrado"[:39])
        self.Codigo = Codigo.text
        Auxiliar = trama.find('Auxiliar')
        if Auxiliar is None:
            raise NameError(u"Parametro Auxiliar no encontrado"[:39])
        self.Auxiliar = Auxiliar.text
        TipoNuc = trama.find('TipoNuc')
        if TipoNuc is None:
            raise NameError(u"Parametro TipoNucC no encontrado"[:39])
        self.TipoNuc = TipoNuc.text
        NumeroIdentificacionPago = trama.find('NumeroIdentificacionPago')
        if NumeroIdentificacionPago is None:
            raise NameError(u"Parametro NumeroIdentificacionPago no encontrado"[:39])
        self.NumeroIdentificacionPago = NumeroIdentificacionPago.text
        CodigoAdicional = trama.find('CodigoAdicional')
        if CodigoAdicional is None:
            raise NameError(u"Parametro CodigoAdicional no encontrado"[:39])
        self.CodigoAdicional = CodigoAdicional.text
        NombreBeneficiario = trama.find('NombreBeneficiario')
        if NombreBeneficiario is None:
            raise NameError(u"Parametro NombreBeneficiario no encontrado"[:39])
        self.NombreBeneficiario = NombreBeneficiario.text
        CanalUci = trama.find('CanalUci')
        if CanalUci is None:
            raise NameError(u"Parametro CanalUci no encontrado"[:39])
        self.CanalUci = CanalUci.text
        DispUci = trama.find('DispUci')
        if DispUci is None:
            raise NameError(u"Parametro DispUci no encontrado"[:39])
        self.DispUci = DispUci.text
        TimeOut = trama.find('TimeOut')
        if TimeOut is None:
            raise NameError(u"Parametro TimeOut no encontrado"[:39])
        self.TimeOut = TimeOut.text
        self.__procesar_persona()

    def procesarPagar(self, cdata, setting):
        self.__cdata = cdata
        eUsuario = Usuario(cdata=cdata)
        eUsuario.procesar_data()
        eUsuario.autentificar(setting)
        trama = ET.ElementTree(ET.fromstring(self.__cdata)).getroot()
        NumeroTransaccion = trama.find('NumeroTransaccion')
        if NumeroTransaccion is None:
            raise NameError(u"Parametro NumeroTransaccion no encontrado"[:39])
        self.NumeroTransaccion = NumeroTransaccion.text
        Producto = trama.find('Producto')
        if Producto is None:
            raise NameError(u"Parametro Producto no encontrado"[:39])
        self.Producto = Producto.text
        TipoTransaccion = trama.find('TipoTransaccion')
        if TipoTransaccion is None:
            raise NameError(u"Parametro TipoTransaccion no encontrado"[:39])
        self.TipoTransaccion = TipoTransaccion.text
        FechaTransaccion = trama.find('FechaTransaccion')
        if FechaTransaccion is None:
            raise NameError(u"Parametro FechaTransaccion no encontrado"[:39])
        self.FechaTransaccion = FechaTransaccion.text
        FechaContable = trama.find('FechaContable')
        if FechaContable is None:
            raise NameError(u"Parametro FechaContable no encontrado"[:39])
        self.FechaContable = FechaContable.text
        HoraTransaccion = trama.find('HoraTransaccion')
        if HoraTransaccion is None:
            raise NameError(u"Parametro HoraTransaccion no encontrado"[:39])
        self.HoraTransaccion = HoraTransaccion.text
        CanalProceso = trama.find('CanalProceso')
        if CanalProceso is None:
            raise NameError(u"Parametro CanalProceso no encontrado"[:39])
        self.CanalProceso = CanalProceso.text
        Agencia = trama.find('Agencia')
        if Agencia is None:
            raise NameError(u"Parametro Agencia no encontrado"[:39])
        self.Agencia = Agencia.text
        Terminal = trama.find('Terminal')
        if Terminal is None:
            raise NameError(u"Parametro Terminal no encontrado"[:39])
        self.Terminal = Terminal.text
        Servicio = trama.find('Servicio')
        if Servicio is None:
            raise NameError(u"Parametro Servicio no encontrado"[:39])
        self.Servicio = Servicio.text
        Codigo = trama.find('Codigo')
        if Codigo is None:
            raise NameError(u"Parametro Codigo no encontrado"[:39])
        self.Codigo = Codigo.text
        TipoIdentificacion = trama.find('TipoIdentificacion')
        if TipoIdentificacion is None:
            raise NameError(u"Parametro TipoIdentificacion no encontrado"[:39])
        self.TipoIdentificacion = TipoIdentificacion.text
        NumeroIdentificacionPago = trama.find('NumeroIdentificacionPago')
        if NumeroIdentificacionPago is None:
            raise NameError(u"Parametro NumeroIdentificacionPago no encontrado"[:39])
        self.NumeroIdentificacionPago = NumeroIdentificacionPago.text
        ValorAPagar = trama.find('ValorAPagar')
        if ValorAPagar is None:
            raise NameError(u"Parametro ValorAPagar no encontrado"[:39])
        self.ValorAPagar = ValorAPagar.text
        ReferenciaOrdenante = trama.find('ReferenciaOrdenante')
        if ReferenciaOrdenante is None:
            raise NameError(u"Parametro ReferenciaOrdenante no encontrado"[:39])
        self.ReferenciaOrdenante = ReferenciaOrdenante.text
        ReferenciaComproba = trama.find('ReferenciaComproba')
        if ReferenciaComproba is None:
            raise NameError(u"Parametro ReferenciaComproba no encontrado"[:39])
        self.ReferenciaComproba = ReferenciaComproba.text
        DatosAdicionales = trama.find('DatosAdicionales')
        if DatosAdicionales is None:
            raise NameError(u"Parametro DatosAdicionales no encontrado"[:39])
        self.DatosAdicionales = DatosAdicionales.text
        Nut = trama.find('Nut')
        if Nut is None:
            raise NameError(u"Parametro Nut no encontrado"[:39])
        self.Nut = Nut.text
        CantidadRubros = trama.find('CantidadRubros')
        if CantidadRubros is None:
            raise NameError(u"Parametro CantidadRubros no encontrado"[:39])
        self.CantidadRubros = CantidadRubros.text
        CanalUci = trama.find('CanalUci')
        if CanalUci is None:
            raise NameError(u"Parametro CanalUci no encontrado"[:39])
        self.CanalUci = CanalUci.text
        DispUci = trama.find('DispUci')
        if DispUci is None:
            raise NameError(u"Parametro DispUci no encontrado"[:39])
        self.DispUci = DispUci.text
        TimeOut = trama.find('TimeOut')
        if TimeOut is None:
            raise NameError(u"Parametro TimeOut no encontrado"[:39])
        self.TimeOut = TimeOut.text
        self.__procesar_persona()

    def procesarReverso(self, cdata, setting):
        self.__cdata = cdata
        eUsuario = Usuario(cdata=cdata)
        eUsuario.procesar_data()
        eUsuario.autentificar(setting)
        trama = ET.ElementTree(ET.fromstring(self.__cdata)).getroot()
        NumeroTransaccion = trama.find('NumeroTransaccion')
        if NumeroTransaccion is None:
            raise NameError(u"Parametro NumeroTransaccion no encontrado"[:39])
        self.NumeroTransaccion = NumeroTransaccion.text
        Producto = trama.find('Producto')
        if Producto is None:
            raise NameError(u"Parametro Producto no encontrado"[:39])
        self.Producto = Producto.text
        TipoTransaccion = trama.find('TipoTransaccion')
        if TipoTransaccion is None:
            raise NameError(u"Parametro TipoTransaccion no encontrado"[:39])
        self.TipoTransaccion = TipoTransaccion.text
        FechaTransaccion = trama.find('FechaTransaccion')
        if FechaTransaccion is None:
            raise NameError(u"Parametro FechaTransaccion no encontrado"[:39])
        self.FechaTransaccion = FechaTransaccion.text
        FechaContable = trama.find('FechaContable')
        if FechaContable is None:
            raise NameError(u"Parametro FechaContable no encontrado"[:39])
        self.FechaContable = FechaContable.text
        HoraTransaccion = trama.find('HoraTransaccion')
        if HoraTransaccion is None:
            raise NameError(u"Parametro HoraTransaccion no encontrado"[:39])
        self.HoraTransaccion = HoraTransaccion.text
        CanalProceso = trama.find('CanalProceso')
        if CanalProceso is None:
            raise NameError(u"Parametro CanalProceso no encontrado"[:39])
        self.CanalProceso = CanalProceso.text
        Agencia = trama.find('Agencia')
        if Agencia is None:
            raise NameError(u"Parametro Agencia no encontrado"[:39])
        self.Agencia = Agencia.text
        Terminal = trama.find('Terminal')
        if Terminal is None:
            raise NameError(u"Parametro Terminal no encontrado"[:39])
        self.Terminal = Terminal.text
        Servicio = trama.find('Servicio')
        if Servicio is None:
            raise NameError(u"Parametro Servicio no encontrado"[:39])
        self.Servicio = Servicio.text
        NumeroIdentificacionPago = trama.find('NumeroIdentificacionPago')
        if NumeroIdentificacionPago is None:
            raise NameError(u"Parametro NumeroIdentificacionPago no encontrado"[:39])
        self.NumeroIdentificacionPago = NumeroIdentificacionPago.text
        ValorAPagar = trama.find('ValorAPagar')
        if ValorAPagar is None:
            raise NameError(u"Parametro ValorAPagar no encontrado"[:39])
        self.ValorAPagar = ValorAPagar.text
        Codigo = trama.find('Codigo')
        if Codigo is None:
            raise NameError(u"Parametro Codigo no encontrado"[:39])
        self.Codigo = Codigo.text
        NumeroTransaccionReversar = trama.find('NumeroTransaccionReversar')
        if NumeroTransaccionReversar is None:
            raise NameError(u"Parametro NumeroTransaccionReversar no encontrado"[:39])
        self.NumeroTransaccionReversar = NumeroTransaccionReversar.text
        NumeroTransaccionReversarEmp = trama.find('NumeroTransaccionReversarEmp')
        if NumeroTransaccionReversarEmp is None:
            raise NameError(u"Parametro NumeroTransaccionReversarEmp no encontrado"[:39])
        self.NumeroTransaccionReversarEmp = NumeroTransaccionReversarEmp.text
        DatosAdicionales = trama.find('DatosAdicionales')
        if DatosAdicionales is None:
            raise NameError(u"Parametro DatosAdicionales no encontrado"[:39])
        self.DatosAdicionales = DatosAdicionales.text
        NumeroTransaccionOpcional = trama.find('NumeroTransaccionOpcional')
        if NumeroTransaccionOpcional is None:
            raise NameError(u"Parametro NumeroTransaccionOpcional no encontrado"[:39])
        self.NumeroTransaccionOpcional = NumeroTransaccionOpcional.text
        NutPago = trama.find('NutPago')
        if NutPago is None:
            raise NameError(u"Parametro NutPago no encontrado"[:39])
        self.NutPago = NutPago.text
        CanalUci = trama.find('CanalUci')
        if CanalUci is None:
            raise NameError(u"Parametro CanalUci no encontrado"[:39])
        self.CanalUci = CanalUci.text
        DispUci = trama.find('DispUci')
        if DispUci is None:
            raise NameError(u"Parametro DispUci no encontrado"[:39])
        self.DispUci = DispUci.text
        TimeOut = trama.find('TimeOut')
        if TimeOut is None:
            raise NameError(u"Parametro TimeOut no encontrado"[:39])
        self.TimeOut = TimeOut.text
        # self.__procesar_persona()

    def __procesar_persona(self):
        if 'C' in [self.TipoNuc, self.TipoIdentificacion]:
            if not Persona.objects.values("id").filter(cedula=self.NumeroIdentificacionPago).exists():
                self.CodigoRespuesta = "0047"
                raise NameError(u"Persona con número de cedula no encontrada")
            ePersona = Persona.objects.filter(cedula=self.NumeroIdentificacionPago)[0]
        elif 'P' in [self.TipoNuc, self.TipoIdentificacion]:
            if not Persona.objects.values("id").filter(pasaporte=self.NumeroIdentificacionPago).exists():
                self.CodigoRespuesta = "0047"
                raise NameError(u"Persona con pasaporte no encontrada")
            ePersona = Persona.objects.filter(pasaporte=self.NumeroIdentificacionPago)[0]
        elif 'R' in [self.TipoNuc, self.TipoIdentificacion]:
            if not Persona.objects.values("id").filter(ruc=self.NumeroIdentificacionPago).exists():
                self.CodigoRespuesta = "0047"
                raise NameError(u"Persona/Sociedad con RUC no encontrada")
            ePersona = Persona.objects.filter(pasaporte=self.NumeroIdentificacionPago)[0]
        if not ePersona:
            self.CodigoRespuesta = "0047"
            raise NameError(u"Persona/Sociedad no encontrada"[:39])
        self.__ePersona = ePersona
        self.NombreBeneficiario = ePersona.nombre_completo_inverso()

    def set_CodigoRespuesta(self, CodigoRespuesta):
        self.CodigoRespuesta = CodigoRespuesta

    def set_MensajeRespuesta(self, MensajeRespuesta):
        self.MensajeRespuesta = MensajeRespuesta

    def set_TipoTransaccion(self, TipoTransaccion):
        self.TipoTransaccion = TipoTransaccion

    def set_elementos(self, elementos):
        self.elementos = elementos
        self.CantidadRegistros = len(self.elementos)

    def get_ePersona(self):
        return self.__ePersona


class ServiceCobro(Service):

    @rpc(String, _returns=String)
    def testConnection(ctx, Test):
        try:
            template_xml = "wester_union/conexion.xml"
            eDataBanco = {}
            service_id = SERVICE_WESTERN_UNION_PK
            setting = get_setting_soap(tipo=1, service_id=service_id)
            if not setting:
                raise NameError(u"Servidor no disponible"[:39])
            eUsuario = Usuario(cdata=Test)
            eUsuario.procesar_data()
            eUsuario.autentificar(setting)
            data = {'CodigoRespuesta': "0001",
                    'MensajeRespuesta': "OK",
                    'Ambiente': setting.get_tipo_ambiente_display(),
                    }
            template = get_template(template_xml)
            xml_content = template.render(data)
            set_logging(LOGGING_WESTERN_UNION, LOGGING_LEVEL_INFO, LOGGING_FILE_WEBSERVICE, json.dumps({"testConnection": data}))
            return xml_content
        except Exception as ex:
            data = {'CodigoRespuesta': "0047",
                    'MensajeRespuesta': ex.__str__()[:39],
                    'Ambiente': setting.get_tipo_ambiente_display(),
                    }
            template = get_template(template_xml)
            xml_content = template.render(data)
            set_logging(LOGGING_WESTERN_UNION, LOGGING_LEVEL_ERROR, LOGGING_FILE_WEBSERVICE, json.dumps({"testConnection": data}))
            return xml_content

    @rpc(String, _returns=String)
    def consultarTransaccion(ctx, Consulta):
        try:
            template_xml = "wester_union/consulta.xml"
            eDataBanco = DataBanco()
            service_id = SERVICE_WESTERN_UNION_PK
            setting = get_setting_soap(tipo=1, service_id=service_id)
            if not setting:
                eDataBanco.set_CodigoRespuesta("0047")
                raise NameError(u"NO EXISTE INFORMACIÓN."[:39])
            eDataBanco.procesarConsulta(cdata=Consulta, setting=setting)
            ePersona = eDataBanco.get_ePersona()
            ePagoBancos = PagoBanco.objects.filter(persona=ePersona, status=True, reverso=False, tipo_ambiente=setting.tipo_ambiente).distinct()
            eRubros = Rubro.objects.filter(persona=ePersona, epunemi=False, cancelado=False, saldo__gt=0, fecha__lte=datetime.now(), status=True).order_by('fecha')
            eDataBanco.set_CodigoRespuesta("0001")
            eDataBanco.set_MensajeRespuesta("OK")
            elementos = []
            for eRubro in eRubros:
                saldo = eRubro.saldo
                if ePagoBancos.values("id").filter(rubro=eRubro).exists():
                    valorPagados = null_to_numeric(ePagoBancos.filter(rubro=eRubro).aggregate(pagos=Sum('valor'))['pagos'])
                    saldo = saldo - valorPagados
                if saldo > 0:
                    elementos.append({"NombreCliente": ePersona.nombre_completo_inverso()[:39],
                                      "ValorAPagar": null_to_decimal(saldo, 2),
                                      "TipoIdentificacion": eDataBanco.TipoNuc,
                                      "NumeroIdentificacion": eDataBanco.NumeroIdentificacionPago,
                                      "Referencia01": eRubro.nombre[:50],
                                      "Referencia02": "",
                                      "Codigo": eRubro.id,
                                      "ValorCapital": 0.00,
                                      "ValorInteres": 0.00,
                                      "ValorMora": 0.00,
                                      "ValorComi": 0.00,
                                      "ValorImpuesto": 0.00,
                                      })
            eDataBanco.set_elementos(elementos)
            eDataBanco.set_TipoTransaccion("0002")
            template = get_template(template_xml)
            data = {'eDataBanco': eDataBanco}
            xml_content = template.render(data)
            data_json = eDataBanco.dictConsulta() if isinstance(eDataBanco, DataBanco) else {}
            # print(data_json)
            set_logging(LOGGING_WESTERN_UNION, LOGGING_LEVEL_INFO, LOGGING_FILE_WEBSERVICE, json.dumps({"consultarTransaccion": data_json}))
            return xml_content
        except Exception as ex:
            if eDataBanco:
                eDataBanco.set_TipoTransaccion("0002")
                eDataBanco.set_MensajeRespuesta(ex.__str__()[:39])
                eDataBanco.set_elementos([])
            template = get_template(template_xml)
            data = {'eDataBanco': eDataBanco}
            xml_content = template.render(data)
            data_json = eDataBanco.dictConsulta() if isinstance(eDataBanco, DataBanco) else {}
            # print(data_json)
            set_logging(LOGGING_WESTERN_UNION, LOGGING_LEVEL_ERROR, LOGGING_FILE_WEBSERVICE, json.dumps({"consultarTransaccion": data_json}))
            return xml_content

    @rpc(String, _returns=String)
    def pagarTransaccion(ctx, Pagar):
        with transaction.atomic():
            try:
                template_xml = "wester_union/pagar.xml"
                eDataBanco = DataBanco()
                service_id = SERVICE_WESTERN_UNION_PK
                setting = get_setting_soap(tipo=1, service_id=service_id)
                if not setting:
                    eDataBanco.set_CodigoRespuesta("0047")
                    raise NameError(u"NO EXISTE INFORMACIÓN."[:39])
                eDataBanco.procesarPagar(cdata=Pagar, setting=setting)
                ePersona = eDataBanco.get_ePersona()
                eRubros = Rubro.objects.filter(persona=ePersona, pk=int(eDataBanco.Codigo), cancelado=False)
                if not eRubros.values("id").exists():
                    eDataBanco.set_CodigoRespuesta("0047")
                    raise NameError(u"CÓDIGO NO ENCONTRADO"[:39])
                eRubro = eRubros.first()
                # eCuenta = setting.cuenta
                if PagoBanco.objects.values("id").filter(persona=ePersona, rubro=eRubro, valor=eDataBanco.ValorAPagar, reverso=False, tipo_ambiente=setting.tipo_ambiente).exists():
                    eDataBanco.set_CodigoRespuesta("9277")
                    raise NameError(u"LA TRANSACCION TIENE ESTADO PAGADO, POR LO CUAL NO PUEDE SER PROCESADA."[:39])
                ePagoBanco = PagoBanco(config=setting,
                                       tipo_ambiente=setting.tipo_ambiente,
                                       num_transaccion=eDataBanco.NumeroTransaccion,
                                       producto=eDataBanco.Producto,
                                       tipo_transaccion=int(eDataBanco.TipoTransaccion),
                                       fecha_transaccion=convertir_fecha_invertida(f"{str(eDataBanco.FechaTransaccion)[0:4]}-{str(eDataBanco.FechaTransaccion)[4:6]}-{str(eDataBanco.FechaTransaccion)[6:8]}"),
                                       fecha_contable=convertir_fecha_invertida(f"{str(eDataBanco.FechaContable)[0:4]}-{str(eDataBanco.FechaContable)[4:6]}-{str(eDataBanco.FechaContable)[6:8]}"),
                                       hora_transaccion=convertir_hora_completa(f"{str(eDataBanco.HoraTransaccion)[0:2]}:{str(eDataBanco.HoraTransaccion)[2:4]}:{str(eDataBanco.HoraTransaccion)[4:6]}"),
                                       canal_proceso=eDataBanco.CanalProceso,
                                       agencia=eDataBanco.Agencia,
                                       terminal=eDataBanco.Terminal,
                                       servicio=eDataBanco.Servicio,
                                       rubro=eRubro,
                                       valor=eDataBanco.ValorAPagar,
                                       persona=ePersona,
                                       procesado=False)
                ePagoBanco.save()
                eDataBanco.set_TipoTransaccion("0004")
                eDataBanco.set_CodigoRespuesta("0001")
                eDataBanco.set_MensajeRespuesta("Transaccion Exitosa"[:39])
                template = get_template(template_xml)
                data = {'eDataBanco': eDataBanco}
                xml_content = template.render(data)
                data_json = eDataBanco.dictPagar() if isinstance(eDataBanco, DataBanco) else {}
                # print(data_json)
                set_logging(LOGGING_WESTERN_UNION, LOGGING_LEVEL_INFO, LOGGING_FILE_WEBSERVICE, json.dumps({"pagarTransaccion": data_json}))
                return xml_content
            except Exception as ex:
                transaction.set_rollback(True)
                if eDataBanco:
                    eDataBanco.set_TipoTransaccion("0004")
                    eDataBanco.set_MensajeRespuesta(ex.__str__()[:39])
                template = get_template(template_xml)
                data = {'eDataBanco': eDataBanco}
                xml_content = template.render(data)
                data_json = eDataBanco.dictPagar() if isinstance(eDataBanco, DataBanco) else {}
                # print(data_json)
                set_logging(LOGGING_WESTERN_UNION, LOGGING_LEVEL_ERROR, LOGGING_FILE_WEBSERVICE, json.dumps({"pagarTransaccion": data_json}))
                return xml_content

    @rpc(String, _returns=String)
    def reversarTransaccion(ctx, Reversar):
        with transaction.atomic():
            try:
                template_xml = "wester_union/reversar.xml"
                eDataBanco = DataBanco()
                service_id = SERVICE_WESTERN_UNION_PK
                setting = get_setting_soap(tipo=1, service_id=service_id)
                if not setting:
                    eDataBanco.set_CodigoRespuesta("0047")
                    raise NameError(u"NO EXISTE INFORMACIÓN."[:39])
                eDataBanco.procesarReverso(cdata=Reversar, setting=setting)
                ePagoBancos = PagoBanco.objects.filter(num_transaccion=eDataBanco.NumeroTransaccionReversar, config=setting, tipo_ambiente=setting.tipo_ambiente)
                if not ePagoBancos.values("id").exists():
                    eDataBanco.set_CodigoRespuesta("9282")
                    raise NameError(u"ERROR AL PROCESAR EL REVERSO, PAGO NO ENCONTRADO."[:39])
                ePagoBancos = ePagoBancos.filter(valor=eDataBanco.ValorAPagar)
                if not ePagoBancos.values("id").exists():
                    eDataBanco.set_CodigoRespuesta("9282")
                    raise NameError(u"ERROR AL PROCESAR EL REVERSO, VALOR DEL PAGO NO COINCIDE CON EL VALOR ANULAR"[:39])
                ePagoBanco = ePagoBancos.first()
                if ePagoBanco.reverso:
                    eDataBanco.set_CodigoRespuesta("9282")
                    raise NameError(u"ERROR AL PROCESAR EL REVERSO, PAGO YA FUE ANULADO CON ANTERIORIDAD"[:39])
                if ePagoBanco.procesado:
                    eDataBanco.set_CodigoRespuesta("9282")
                    raise NameError(u"ERROR AL PROCESAR EL REVERSO, PAGO YA FUE PROCESADO POR LA INSTITUCIÓN. ACERCARSE A TESORERIA"[:39])
                if ePagoBanco.fecha_creacion <= datetime.now():
                    eDataBanco.set_CodigoRespuesta("0505")
                    raise NameError(u"EL REVERSO DEL PAGO SOLO PUEDE SER EL MISMO DIA"[:39])
                eReversoPagoBanco = ReversoPagoBanco(pago=ePagoBanco,
                                                     tipo_ambiente=setting.tipo_ambiente,
                                                     fecha_transaccion=convertir_fecha_invertida(f"{str(eDataBanco.FechaTransaccion)[0:4]}-{str(eDataBanco.FechaTransaccion)[4:6]}-{str(eDataBanco.FechaTransaccion)[6:8]}"),
                                                     fecha_contable=convertir_fecha_invertida(f"{str(eDataBanco.FechaContable)[0:4]}-{str(eDataBanco.FechaContable)[4:6]}-{str(eDataBanco.FechaContable)[6:8]}"),
                                                     hora_transaccion=convertir_hora_completa(f"{str(eDataBanco.HoraTransaccion)[0:2]}:{str(eDataBanco.HoraTransaccion)[2:4]}:{str(eDataBanco.HoraTransaccion)[4:6]}"),
                                                     canal_proceso=eDataBanco.CanalProceso,
                                                     agencia=eDataBanco.Agencia,
                                                     terminal=eDataBanco.Terminal,
                                                     servicio=eDataBanco.Servicio)
                eReversoPagoBanco.save()
                ePagoBanco.reverso = True
                ePagoBanco.save()
                eDataBanco.set_TipoTransaccion("0006")
                eDataBanco.set_CodigoRespuesta("0001")
                eDataBanco.set_MensajeRespuesta("Transaccion Exitosa"[:39])
                template = get_template(template_xml)
                data = {'eDataBanco': eDataBanco}
                xml_content = template.render(data)
                data_json = eDataBanco.dictReversar() if isinstance(eDataBanco, DataBanco) else {}
                # print(data_json)
                set_logging(LOGGING_WESTERN_UNION, LOGGING_LEVEL_INFO, LOGGING_FILE_WEBSERVICE, json.dumps({"reversarTransaccion": data_json}))
                return xml_content
            except Exception as ex:
                transaction.set_rollback(True)
                if eDataBanco:
                    eDataBanco.set_TipoTransaccion("0006")
                    eDataBanco.set_MensajeRespuesta(ex.__str__()[:39])
                template = get_template(template_xml)
                data = {'eDataBanco': eDataBanco}
                xml_content = template.render(data)
                data_json = eDataBanco.dictReversar() if isinstance(eDataBanco, DataBanco) else {}
                # print(data_json)
                set_logging(LOGGING_WESTERN_UNION, LOGGING_LEVEL_ERROR, LOGGING_FILE_WEBSERVICE, json.dumps({"reversarTransaccion": data_json}))
                return xml_content


# url_banco_pacifico = csrf_exempt(DjangoView.as_view(services=[ServiceCobro], tns='web.bancopacifico.service', in_protocol=Soap12(validator="lxml"), out_protocol=Soap12()))
url_wester_union = csrf_exempt(DjangoView.as_view(services=[ServiceCobro], tns='web.westernunion.service', in_protocol=Soap11(validator='lxml'), out_protocol=Soap11()))


# @login_or_basic_auth_required
def wester_union_cobro(request):
    return url_wester_union(request)