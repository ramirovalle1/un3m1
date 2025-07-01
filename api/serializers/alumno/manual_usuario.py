from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from api.serializers.base.persona import PersonaBaseSerializer
from rest_framework import serializers
from sga.models import Matricula, Persona, ManualUsuario
from med.models import ProximaCita


class ManualUsuarioSerializer(Helper_ModelSerializer):
    download_link = serializers.SerializerMethodField()

    class Meta:
        model = ManualUsuario
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_download_link(self, obj):
        if obj.archivo.url:
            return self.get_media_url(obj.archivo.url)
        return None


