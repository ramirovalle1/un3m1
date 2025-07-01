# coding=utf-8
from django.contrib.auth.models import User, Group

from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from api.serializers.base.persona import PersonaBaseSerializer
from sga.models import BecaSolicitud, BecaTipo
from rest_framework import serializers

from sga.templatetags.sga_extras import encrypt


class BecaTipoSerializer(Helper_ModelSerializer):

    class Meta:
        model = BecaTipo
        exclude = ['usuario_creacion', 'usuario_modificacion']

class BecaSolicitudSerializer(Helper_ModelSerializer):
    becatipo = BecaTipoSerializer()
    url_acta = serializers.SerializerMethodField()
    tiene_documentacion_pendiente = serializers.SerializerMethodField()
    periodo_idenc = serializers.SerializerMethodField()

    class Meta:
        model = BecaSolicitud
        exclude = ['usuario_creacion','usuario_modificacion']

    def get_tiene_documentacion_pendiente(self, obj):
        return obj.tiene_documentacion_pendiente if hasattr(obj, 'tiene_documentacion_pendiente') else ''

    def get_url_acta(self, obj):
        return obj.url_acta if hasattr(obj, 'url_acta') else ''

    def get_periodo_idenc(self, obj):
        return encrypt(obj.periodo_id)