# coding=utf-8
from django.contrib.auth.models import User, Group

from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from sga.models import Archivo
from rest_framework import serializers


class ArchivoSerializer(Helper_ModelSerializer):
    archivo = serializers.SerializerMethodField()
    tipo_archivo = serializers.SerializerMethodField()
    icono = serializers.SerializerMethodField()

    class Meta:
        model = Archivo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_archivo(self, obj):
        return self.get_media_url(obj.archivo.url) if obj.archivo else None

    def get_tipo_archivo(self, obj):
        return obj.tipo_archivo()

    def get_icono(self, obj):
        type_file = obj.tipo_archivo()
        if type_file == 'pdf':
            return self.get_static_url("/static/images/iconos/pdf.png")
        elif type_file == 'doc' or type_file == 'docx':
            return self.get_static_url("/static/images/iconos/word.png")
        elif type_file == 'other':
            return self.get_static_url("/static/images/iconos/other.png")
        else:
            return self.get_static_url("/static/images/iconos/other.png")


