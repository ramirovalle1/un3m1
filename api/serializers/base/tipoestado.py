# coding=utf-8

from sga.models import Persona
from rest_framework import serializers
from api.helpers.serializers_model_helper import Helper_ModelSerializer


class TipoEstadoBaseSerializer(Helper_ModelSerializer):
    aprobada = serializers.SerializerMethodField()
    reprobado = serializers.SerializerMethodField()
    encurso = serializers.SerializerMethodField()
    supletorio = serializers.SerializerMethodField()

    def get_aprobada(self, obj):
        return obj.aprobada()

    def get_reprobado(self, obj):
        return obj.reprobado()

    def get_encurso(self, obj):
        return obj.encurso()

    def get_supletorio(self, obj):
        return obj.supletorio()
