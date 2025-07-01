# coding=utf-8
from django.contrib.auth.models import User, Group
from rest_framework import serializers
from api.helpers.formats_helper import *
from api.helpers.functions_helper import get_variable
from sga.templatetags.sga_extras import encrypt


class Helper_ModelSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    display = serializers.SerializerMethodField()
    usuario_creacion_id = serializers.SerializerMethodField()
    usuario_modificacion_id = serializers.SerializerMethodField()

    def get_usuario_creacion_id(self, obj):
        return encrypt(obj.usuario_creacion_id) if obj.usuario_creacion_id else None

    def get_fecha_creacion(self, obj):
        return obj.fecha_creacion.strftime(DATETIME_FORMAT) if obj.fecha_creacion else None

    def get_usuario_modificacion_id(self, obj):
        return encrypt(obj.usuario_modificacion_id) if obj.usuario_modificacion_id else None

    def get_fecha_modificacion(self, obj):
        return obj.fecha_modificacion.strftime(DATETIME_FORMAT) if obj.fecha_modificacion else None

    def get_id(self, obj):
        return encrypt(obj.id) if obj.id else None

    def get_display(self, obj):
        return obj.__str__() if obj.__str__() else None

    def get_media_url(self, media):
        value = get_variable('SITE_URL_SGA')
        return f"{value}{media}"

    def get_static_url(self, static):
        value = get_variable('SITE_URL_SGA')
        return f"{value}{static}"
