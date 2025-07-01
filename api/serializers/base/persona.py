# coding=utf-8

from sga.models import Persona
from rest_framework import serializers
from api.helpers.serializers_model_helper import Helper_ModelSerializer


class PersonaBaseSerializer(Helper_ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)
    nombre_completo_minus = serializers.CharField(read_only=True)
    tipo_documento = serializers.CharField(read_only=True)
    documento = serializers.CharField(read_only=True)
    foto_perfil = serializers.SerializerMethodField()
    tiene_foto = serializers.SerializerMethodField()
    direccion_corta = serializers.SerializerMethodField()
    tiene_otro_titulo = serializers.SerializerMethodField()
    es_mujer = serializers.SerializerMethodField()
    es_hombre = serializers.SerializerMethodField()
    lista_emails = serializers.SerializerMethodField()

    def get_nombre_completo(self, obj):
        return obj.nombre_completo()

    def get_nombre_completo_minus(self, obj):
        return obj.nombre_completo_minus()

    def get_documento(self, obj):
        return obj.documento()

    def get_tipo_documento(self, obj):
        return obj.tipo_documento()

    def get_foto_perfil(self, obj):
        if obj.tiene_foto():
            return self.get_media_url(obj.foto().foto.url)
        if obj.sexo and obj.sexo.id == 1:
            foto_perfil = '/static/images/iconos/mujer.png'
        else:
            foto_perfil = '/static/images/iconos/hombre.png'
        return self.get_static_url(foto_perfil)

    def get_tiene_foto(self, obj):
        return obj.tiene_foto()

    def get_direccion_corta(self, obj):
        return obj.direccion_corta()

    def get_tiene_otro_titulo(self, obj):
        return obj.tiene_otro_titulo()

    def get_es_mujer(self, obj):
        return obj.es_mujer()

    def get_es_hombre(self, obj):
        return obj.es_hombre()

    def get_lista_emails(self, obj):
        return obj.lista_emails_2()
