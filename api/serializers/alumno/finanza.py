from rest_framework import serializers
from django.db.models import Sum, F
from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from api.serializers.base.persona import PersonaBaseSerializer
from api.serializers.base.reporte import ReporteBaseSerializer
from matricula.models import PeriodoMatricula
from sagest.models import Rubro, TipoOtroRubro, CompromisoPagoPosgrado, Pago, Factura, PagoReciboCaja, SesionCaja, \
    LugarRecaudacion, ComprobanteAlumno, CompromisoPagoPosgradoRecorrido, CompromisoPagoPosgradoGarante, TipoCuentaBanco, HistorialGestionComprobanteAlumno,\
    ComprobanteAlumnoRubros
from settings import RUBRO_MATRICULA, RUBRO_ARANCEL
from sga.funciones import null_to_decimal
from sga.models import Matricula, Persona, Inscripcion, Reporte, MatriculaGrupoSocioEconomico, Nivel, Periodo, PersonaEstadoCivil
from med.models import PersonaExtension
from socioecon.models import GrupoSocioEconomico
from sagest.models import CuentaBanco, Banco


class FinanzaPersonaSerializer(PersonaBaseSerializer):
    # datos_domicilio_completos = serializers.SerializerMethodField()
    total_rubros = serializers.SerializerMethodField()
    total_pagado = serializers.SerializerMethodField()
    total_adeudado = serializers.SerializerMethodField()
    datos_domicilio_completos = serializers.SerializerMethodField()
    estado_civil = serializers.SerializerMethodField()
    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    # def get_datos_domicilio_completos(self, obj):
    #     return obj.datos_domicilio_completos()
    def get_estado_civil(self, obj):
        civil = obj.estado_civil()
        id = civil.id if civil else 0
        return id

    def get_total_rubros(self, obj):
        return obj.total_rubros()

    def get_total_pagado(self, obj):
        return obj.total_pagado()

    def get_total_adeudado(self, obj):
        return obj.total_adeudado()

    def get_datos_domicilio_completos(self, obj):
        return obj.datos_domicilio_completos()


class InscripcionSerializer(Helper_ModelSerializer):
    persona = FinanzaPersonaSerializer()
    perdida_gratuidad_senescyt = serializers.SerializerMethodField()

    class Meta:
        model = Inscripcion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_perdida_gratuidad_senescyt(self, obj):
        return obj.perdida_gratuidad_senescyt()


class TipoOtroRubroSerializer(Helper_ModelSerializer):

    class Meta:
        model = TipoOtroRubro
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class GrupoSocioEconomicoSerializer(Helper_ModelSerializer):

    class Meta:
        model = GrupoSocioEconomico
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriculaGrupoSocioEconomicoSerializer(Helper_ModelSerializer):

    class Meta:
        model = MatriculaGrupoSocioEconomico
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class PeriodoSerializer(Helper_ModelSerializer):

    class Meta:
        model = Periodo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class PeriodoMatriculaSerializer(Helper_ModelSerializer):

    class Meta:
        model = PeriodoMatricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NivelSerializer(Helper_ModelSerializer):
    periodo = PeriodoSerializer()

    class Meta:
        model = Nivel
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriculaSerializer(Helper_ModelSerializer):
    inscripcion = InscripcionSerializer()
    gratuidad = serializers.SerializerMethodField()
    nivel = NivelSerializer()
    tiene_pagos_rubro_matricula = serializers.SerializerMethodField()
    tiene_pagos_rubro_arancel = serializers.SerializerMethodField()
    puede_diferir_rubro_arancel = serializers.SerializerMethodField()
    rubro_arancel = serializers.SerializerMethodField()

    class Meta:
        model = Matricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_tiene_pagos_rubro_matricula(self, obj):
        return obj.tiene_pagos_rubro_matricula()

    def get_tiene_pagos_rubro_arancel(self, obj):
        return obj.tiene_pagos_rubro_arancel()

    def get_puede_diferir_rubro_arancel(self, obj):
        return obj.puede_diferir_rubro_arancel()

    def get_rubro_arancel(self, obj):
        descripcion = ''
        valorarancel = obj.valor_total_rubros_arancel()
        if (rubro := obj.rubro_set.filter(status=True, tipo_id=RUBRO_ARANCEL).first()) is not None:
            descripcion = rubro.nombre
        return {'valorarancel': valorarancel, 'descripcion': descripcion}

    def get_gratuidad(self, obj):
        return obj.gratuidad()



class ReporteSerializer(ReporteBaseSerializer):

    class Meta:
        model = Reporte
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class FaturaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = Factura
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class PagoReciboCajaSerializer(Helper_ModelSerializer):
    pdfarchivo = serializers.SerializerMethodField()

    class Meta:
        model = PagoReciboCaja
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pdfarchivo(self, obj):
        return self.get_media_url(obj.pdfarchivo.url) if obj.pdfarchivo else None


class LugarRecaudacionSerializer(Helper_ModelSerializer):

    class Meta:
        model = LugarRecaudacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class SesionCajaCajaSerializer(Helper_ModelSerializer):
    caja = LugarRecaudacionSerializer()

    class Meta:
        model = SesionCaja
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class PagoSerializer(Helper_ModelSerializer):
    sesion = SesionCajaCajaSerializer()
    factura = serializers.SerializerMethodField()
    recibocaja = serializers.SerializerMethodField()
    tipo = serializers.SerializerMethodField()
    urlfacturaepunemi = serializers.SerializerMethodField()

    class Meta:
        model = Pago
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_factura(self, obj):
        factura = obj.factura()
        return FaturaSerializer(factura).data if factura else None

    def get_recibocaja(self, obj):
        recibo = obj.recibocaja()
        return PagoReciboCajaSerializer(recibo).data if recibo else None

    def get_tipo(self, obj):
        return obj.tipo()

    def get_urlfacturaepunemi(self, obj):
        if obj.idpagoepunemi:
            return f"http://sagest.epunemi.gob.ec/media/{obj.url_factura()}"
        if obj.rubro.epunemi:
            factura = obj.factura()
            return self.get_media_url(factura.pdfarchivo.url) if factura and factura.pdfarchivo else None
        return None


class RubroSerializer(Helper_ModelSerializer):
    tipo = TipoOtroRubroSerializer()
    matricula = MatriculaSerializer()
    esta_anulado = serializers.SerializerMethodField()
    rubro_devolucion = serializers.SerializerMethodField()
    codigo_intermatico = serializers.SerializerMethodField()
    no_salga = serializers.SerializerMethodField()
    total_pagado = serializers.SerializerMethodField()
    tiene_factura = serializers.SerializerMethodField()
    saldo = serializers.SerializerMethodField()
    idm = serializers.SerializerMethodField()
    adeudado = serializers.SerializerMethodField()
    total_pagado = serializers.SerializerMethodField()
    esta_liquidado = serializers.SerializerMethodField()

    class Meta:
        model = Rubro
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_esta_anulado(self, obj):
        return obj.esta_anulado()

    def get_rubro_devolucion(self, obj):
        return obj.rubro_devolucion()

    def get_codigo_intermatico(self, obj):
        return obj.codigo_intermatico()

    def get_no_salga(self, obj):
        return obj.no_salga()

    def get_total_pagado(self, obj):
        return obj.total_pagado()

    def get_tiene_factura(self, obj):
        return obj.tiene_factura()

    def get_saldo(self, obj):
        return float(obj.saldo)

    def get_idm(self, obj):
        return obj.id

    def get_adeudado(self, obj):
        return obj.adeudado()

    def get_total_pagado(self, obj):
        return obj.total_pagado()

    def get_esta_liquidado(self, obj):
        if obj and obj.esta_liquidado():
            return True


class CompromisoPagoPosgradoSerializer(Helper_ModelSerializer):
    puede_subir_documentos_personales = serializers.SerializerMethodField()

    class Meta:
        model = CompromisoPagoPosgrado
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_puede_subir_documentos_personales(self, obj):
        return obj.puede_subir_documentos_personales()


class ComprobantePersonaSerializer(PersonaBaseSerializer):
    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class CompromisoPagoPosgradoRecorridoSerializer(Helper_ModelSerializer):
    puede_subir_documentos_personales = serializers.SerializerMethodField()
    puede_subir_comprobante_pago = serializers.SerializerMethodField()
    puede_agregar_conyuge = serializers.SerializerMethodField()
    puede_agregar_garante = serializers.SerializerMethodField()
    puede_agregar_conyuge_garante = serializers.SerializerMethodField()
    class Meta:
        model = CompromisoPagoPosgrado
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']
    def get_puede_subir_documentos_personales(self, obj):
        return obj.puede_subir_documentos_personales()

    def get_puede_subir_comprobante_pago(self, obj):
        return obj.puede_subir_comprobante_pago()

    def get_puede_agregar_conyuge(self, obj):
        return obj.puede_agregar_conyuge()

    def get_puede_agregar_garante(self, obj):
        return obj.puede_agregar_garante()

    def get_puede_agregar_conyuge_garante(self, obj):
        return obj.puede_agregar_conyuge_garante()


class PersonaEstadoCivilFinanzaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    class Meta:
        model = PersonaEstadoCivil
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id

class CompromisoPagoPosgradoGaranteFinanzaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    class Meta:
        model = CompromisoPagoPosgradoGarante
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id

class BancoSerializer(Helper_ModelSerializer):
    nombre = serializers.SerializerMethodField()

    class Meta:
        model = Banco
        exclude = ['usuario_creacion', 'usuario_modificacion']

class TipoCuentaBancoSerializer(Helper_ModelSerializer):
    nombre = serializers.SerializerMethodField()

    class Meta:
        model = TipoCuentaBanco
        exclude = ['usuario_creacion', 'usuario_modificacion']

class CuentaBancoSerializer(Helper_ModelSerializer):
    banco = BancoSerializer()
    tipocuenta = TipoCuentaBancoSerializer()

    class Meta:
        model = CuentaBanco
        exclude = ['usuario_creacion', 'usuario_modificacion']

class ComprobanteAlumnoSerializer(Helper_ModelSerializer):
    persona = FinanzaPersonaSerializer()
    tipocomprobante_nombre = serializers.SerializerMethodField()
    estados_display = serializers.SerializerMethodField()
    typefile = serializers.SerializerMethodField()
    cuentabancaria = CuentaBancoSerializer()
    rubro = RubroSerializer()
    valorrubros = serializers.SerializerMethodField()
    class Meta:
        model = ComprobanteAlumno
        exclude = ['usuario_creacion', 'usuario_modificacion']
    def get_tipocomprobante_nombre(self, obj):
        return obj.get_tipocomprobante()
    def get_estados_display(self, obj):
        return obj.get_estados_display()
    def get_typefile(self, obj):
        return obj.typefile()
    def get_valorrubros(self, obj):
        return obj.valor_rubros_asignados()

class HistorialComprobanteAlumnoSerializer(Helper_ModelSerializer):
    comprobante = ComprobanteAlumnoSerializer()
    persona = FinanzaPersonaSerializer()
    estado_display = serializers.SerializerMethodField()
    class Meta:
        model = HistorialGestionComprobanteAlumno
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_estado_display(self, obj):
        return obj.get_estado_display()