# coding=utf-8

from sga.models import Reporte
from rest_framework import serializers
from api.helpers.serializers_model_helper import Helper_ModelSerializer


class ReporteBaseSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    codigo = serializers.SerializerMethodField()
    tipos = serializers.SerializerMethodField()
    arreglotipos = serializers.SerializerMethodField()

    def get_idm(self, obj):
        return obj.id

    def get_codigo(self, obj):
        return obj.id

    def get_tipos(self, obj):
        return obj.tiporeporte()

    def get_arreglotipos(self, obj):
        return obj.arreglotiporeporte()



