# coding=utf-8

from sga.models import Provincia, Pais, Canton, Parroquia
from rest_framework import serializers
from api.helpers.serializers_model_helper import Helper_ModelSerializer


class PaisSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = Pais
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class ProvinciaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = Provincia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class CantonSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = Canton
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class ParroquiaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = Parroquia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id
