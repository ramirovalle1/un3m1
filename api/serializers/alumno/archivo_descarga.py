from api.helpers.serializers_model_helper import Helper_ModelSerializer
from sagest.models import InscritoCongreso, Congreso, TipoParticipacionCongreso, Rubro, ArchivoDescarga


class ArchivoDescargaSerializer(Helper_ModelSerializer):
    class Meta:
        model = ArchivoDescarga
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


