import api.serializers.alumno.finanza
from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.serializers.base.persona import PersonaBaseSerializer
from rest_framework import serializers
from sagest.models import TipoResolucion, Resoluciones
from sga.funciones import MiPaginador


class TipoResolucionesSerializer(Helper_ModelSerializer):

    class Meta:
        model = TipoResolucion
        fields = '__all__'

class ResolucionesSerializer(Helper_ModelSerializer):
    tipo = TipoResolucionesSerializer()
    download_link = serializers.SerializerMethodField()
    class Meta:
        model = Resoluciones
        fields = '__all__'

    def get_download_link(self, obj):
        return self.get_media_url(obj.archivo.url)


