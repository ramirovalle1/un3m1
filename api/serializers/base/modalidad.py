# coding=utf-8

from sga.models import Modalidad
from rest_framework import serializers
from api.helpers.serializers_model_helper import Helper_ModelSerializer


class BaseModalidadSerializer(Helper_ModelSerializer):
    es_presencial = serializers.SerializerMethodField()
    es_semipresencial = serializers.SerializerMethodField()
    es_enlinea = serializers.SerializerMethodField()
    es_hibrida = serializers.SerializerMethodField()

    def get_es_presencial(self, obj):
        return obj.es_presencial()

    def get_es_semipresencial(self, obj):
        return obj.es_semipresencial()

    def get_es_enlinea(self, obj):
        return obj.es_enlinea()

    def get_es_hibrida(self, obj):
        return obj.es_hibrida()

