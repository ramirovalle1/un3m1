from django.contrib.auth.models import User, Group

from api.helpers.functions_helper import get_variable
from sga.models import Modulo
from rest_framework import serializers
from api.helpers.serializers_model_helper import Helper_ModelSerializer


class ModuloSerializer(Helper_ModelSerializer):
    icono = serializers.SerializerMethodField()

    class Meta:
        model = Modulo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_icono(self, obj):
        return self.get_static_url(obj.icono) if obj.icono else None
