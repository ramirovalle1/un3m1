# coding=utf-8
from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.serializers.base.reporte import ReporteBaseSerializer
from api.helpers.formats_helper import *
from certi.models import Certificado
from rest_framework import serializers
from sga.models import Matricula, Nivel, Periodo, TipoPeriodo, Reporte


class CertificadoReporteSerializer(ReporteBaseSerializer):

    class Meta:
        model = Reporte
        fields = ['id', 'nombre', 'version', 'tipos', 'codigo']


class CertificadoSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    primera_emision = serializers.SerializerMethodField()
    ultima_modificacion = serializers.SerializerMethodField()
    reporte = CertificadoReporteSerializer()

    class Meta:
        model = Certificado
        fields = "__all__"
        # exclude = ['users']

    def get_primera_emision(self, obj):
        return obj.primera_emision.strftime(DATE_FORMAT) if obj.primera_emision else None

    def get_ultima_modificacion(self, obj):
        return obj.ultima_modificacion.strftime(DATE_FORMAT) if obj.ultima_modificacion else None

    def get_pk(self, obj):
        return obj.pk


class CertificadoTipoPeriodoSerializer(Helper_ModelSerializer):
    orden_id = serializers.SerializerMethodField()

    class Meta:
        model = TipoPeriodo
        fields = ['id', 'nombre', 'orden_id']

    def get_orden_id(self, obj):
        return obj.id


class CertificadoPeriodoSerializer(Helper_ModelSerializer):
    tipo = CertificadoTipoPeriodoSerializer()

    class Meta:
        model = Periodo
        fields = ['id', 'nombre', 'tipo']


class CertificadoNivelSerializer(Helper_ModelSerializer):
    periodo = CertificadoPeriodoSerializer()

    class Meta:
        model = Nivel
        fields = ['id', 'periodo', 'cerrado']


class CertificadoMatriculaSerializer(Helper_ModelSerializer):
    nivel = CertificadoNivelSerializer()

    class Meta:
        model = Matricula
        fields = ['id', 'cerrada', 'nivel']


