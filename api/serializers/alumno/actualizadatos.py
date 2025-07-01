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
from posgrado.models import InscripcionCohorte
from sga.models import Matricula, Persona, Inscripcion, Reporte, MatriculaGrupoSocioEconomico, Nivel, Periodo, PersonaEstadoCivil, Carrera, PerfilInscripcion, \
    Titulacion, Pais, Provincia, Canton, Parroquia, Raza, NacionalidadIndigena, Titulo, InstitucionEducacionSuperior
from med.models import PersonaExtension
from socioecon.models import GrupoSocioEconomico
from sagest.models import CuentaBanco, Banco


class MatriRazaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = Raza
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class MatriNacionalidadIndigenaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = NacionalidadIndigena
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class PaisSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = Pais
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None


class ProvinciaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = Provincia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class CantonSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = Canton
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

class ParroquiaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = Parroquia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None


class TituloSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    nombretitulo = serializers.SerializerMethodField()

    class Meta:
        model = Titulo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id

    def get_nombretitulo(self, obj):
        return obj.__str__()

class InstitucionEducacionSuperiorSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    nombreinstitucion = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()

    class Meta:
        model = InstitucionEducacionSuperior
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id

    def get_value(self, obj):
        return obj.id

    def get_label(self, obj):
        return obj.nombre if obj and obj.nombre else None

    def get_nombreinstitucion(self, obj):
        return obj.nombre if obj and obj.nombre else None

class TitulacionSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    nombre = serializers.SerializerMethodField()
    institucion_des = serializers.SerializerMethodField()
    pdfarchivo = serializers.SerializerMethodField()
    pdfarchivosenecyt = serializers.SerializerMethodField()

    class Meta:
        model = Titulacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id

    def get_nombre(self, obj):
        return obj.titulo.__str__() if obj.titulo else None

    def get_institucion_des(self, obj):
        return obj.institucion.nombre if obj and obj.institucion else None

    def get_pdfarchivosenecyt(self, obj):
        return self.get_media_url(obj.registroarchivo.url) if obj.registroarchivo else None

    def get_pdfarchivo(self, obj):
        return self.get_media_url(obj.archivo.url) if obj.archivo else None

class PerfilSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    raza = MatriRazaSerializer()
    nombre_raza = serializers.SerializerMethodField()
    nacionalidadindigena = MatriNacionalidadIndigenaSerializer()
    nombre_nacionalidadindigena = serializers.SerializerMethodField()

    class Meta:
        model = PerfilInscripcion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id
    def get_nombre_raza(self, obj):
        return obj.raza.__str__() if obj.raza else None
    def get_nombre_nacionalidadindigena(self, obj):
        return obj.nacionalidadindigena.__str__() if obj.nacionalidadindigena else None


class DatosPersonaSerializer(PersonaBaseSerializer):
    pais = PaisSerializer()
    provincia = ProvinciaSerializer()
    canton = CantonSerializer()
    parroquia = ParroquiaSerializer()

    paisnacimiento = PaisSerializer()
    provincianacimiento = ProvinciaSerializer()
    cantonnacimiento = CantonSerializer()
    parroquianacimiento = ParroquiaSerializer()

    total_rubros = serializers.SerializerMethodField()
    total_pagado = serializers.SerializerMethodField()
    total_adeudado = serializers.SerializerMethodField()
    datos_domicilio_completos = serializers.SerializerMethodField()
    estado_civil = serializers.SerializerMethodField()
    estado_civil_des = serializers.SerializerMethodField()
    sexo_des = serializers.SerializerMethodField()
    paisnacimiento_des = serializers.SerializerMethodField()
    provincianacimiento_des = serializers.SerializerMethodField()
    cantonnacimiento_des = serializers.SerializerMethodField()
    parroquianacimiento_des = serializers.SerializerMethodField()

    pais_des = serializers.SerializerMethodField()
    provincia_des = serializers.SerializerMethodField()
    canton_des = serializers.SerializerMethodField()
    parroquia_des = serializers.SerializerMethodField()
    perfil = serializers.SerializerMethodField()
    titulacion_tercernivel = serializers.SerializerMethodField()

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_titulacion_tercernivel(self, obj):
        titulo = obj.mis_titulacionesxgrupo(3)
        return TitulacionSerializer(titulo, many=True).data if titulo else []

    def get_perfil(self, obj):
        perfil = obj.mi_perfil()
        return PerfilSerializer(perfil).data if perfil else None

    def get_sexo_des(self, obj):
        sexo = obj.sexo.nombre
        return sexo

    def get_paisnacimiento_des(self, obj):
        des = None
        if obj and obj.paisnacimiento:
            des = obj.paisnacimiento.nombre
        return des

    def get_provincianacimiento_des(self, obj):
        des = None
        if obj and obj.provincianacimiento:
            des = obj.provincianacimiento.nombre
        return des

    def get_cantonnacimiento_des(self, obj):
        des = None
        if obj and obj.cantonnacimiento:
            des = obj.cantonnacimiento.nombre
        return des

    def get_parroquianacimiento_des(self, obj):
        des = None
        if obj and obj.parroquianacimiento:
            des = obj.parroquianacimiento.nombre
        return des

    def get_pais_des(self, obj):
        des = None
        if obj and obj.pais:
            des = obj.pais.nombre
        return des

    def get_provincia_des(self, obj):
        des = None
        if obj and obj.provincia:
            des = obj.provincia.nombre
        return des

    def get_canton_des(self, obj):
        des = None
        if obj and obj.canton:
            des = obj.canton.nombre
        return des

    def get_parroquia_des(self, obj):
        des = None
        if obj and obj.parroquia:
            des = obj.parroquia.nombre
        return des

    def get_estado_civil(self, obj):
        civil = obj.estado_civil()
        id = civil.id if civil else 0
        return id

    def get_estado_civil_des(self, obj):
        civil = obj.estado_civil()
        return civil.nombre if civil else None

    def get_total_rubros(self, obj):
        return obj.total_rubros()

    def get_total_pagado(self, obj):
        return obj.total_pagado()

    def get_total_adeudado(self, obj):
        return obj.total_adeudado()

    def get_datos_domicilio_completos(self, obj):
        return obj.datos_domicilio_completos()

class CarreraSerializer(Helper_ModelSerializer):
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = Carrera
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_nombre_completo(self, obj):
        return obj.__str__()


class InscripcionSerializer(Helper_ModelSerializer):
    persona = DatosPersonaSerializer()
    carrera = CarreraSerializer()
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

class InscripcionCohorteSerializer(Helper_ModelSerializer):
    inscripcion = InscripcionSerializer()

    class Meta:
        model = InscripcionCohorte
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

    def get_gratuidad(self, obj):
        return obj.gratuidad()

    def get_tiene_pagos_rubro_matricula(self, obj):
        return obj.tiene_pagos_rubro_matricula()

    def get_tiene_pagos_rubro_arancel(self, obj):
        return obj.tiene_pagos_rubro_arancel()

    def get_puede_diferir_rubro_arancel(self, obj):
        return obj.puede_diferir_rubro_arancel()

    def get_rubro_arancel(self, obj):
        descripcion = ''
        valorarancel = obj.valor_total_rubros_arancel()
        if obj.rubro_set.values("id").filter(status=True, tipo_id=RUBRO_ARANCEL).exists():
            descripcion = obj.rubro_set.filter(status=True, tipo_id=RUBRO_ARANCEL).first().nombre
        return {'valorarancel': valorarancel, 'descripcion': descripcion}


#
# class ReporteSerializer(ReporteBaseSerializer):
#
#     class Meta:
#         model = Reporte
#         # fields = "__all__"
#         exclude = ['usuario_creacion', 'usuario_modificacion']


# class RubroSerializer(Helper_ModelSerializer):
#     tipo = TipoOtroRubroSerializer()
#     matricula = MatriculaSerializer()
#     esta_anulado = serializers.SerializerMethodField()
#     rubro_devolucion = serializers.SerializerMethodField()
#     codigo_intermatico = serializers.SerializerMethodField()
#     no_salga = serializers.SerializerMethodField()
#     total_pagado = serializers.SerializerMethodField()
#     tiene_factura = serializers.SerializerMethodField()
#     saldo = serializers.SerializerMethodField()
#     idm = serializers.SerializerMethodField()
#     adeudado = serializers.SerializerMethodField()
#     total_pagado = serializers.SerializerMethodField()
#
#     class Meta:
#         model = Rubro
#         # fields = "__all__"
#         exclude = ['usuario_creacion', 'usuario_modificacion']
#
#     def get_esta_anulado(self, obj):
#         return obj.esta_anulado()
#
#     def get_rubro_devolucion(self, obj):
#         return obj.rubro_devolucion()
#
#     def get_codigo_intermatico(self, obj):
#         return obj.codigo_intermatico()
#
#     def get_no_salga(self, obj):
#         return obj.no_salga()
#
#     def get_total_pagado(self, obj):
#         return obj.total_pagado()
#
#     def get_tiene_factura(self, obj):
#         return obj.tiene_factura()
#
#     def get_saldo(self, obj):
#         return float(obj.saldo)
#
#     def get_idm(self, obj):
#         return obj.id
#
#     def get_adeudado(self, obj):
#         return obj.adeudado()
#
#     def get_total_pagado(self, obj):
#         return obj.total_pagado()


class PersonaEstadoCivilFinanzaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    class Meta:
        model = PersonaEstadoCivil
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id