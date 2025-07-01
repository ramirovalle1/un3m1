from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.serializers.base.persona import PersonaBaseSerializer
from sga.models import Matricula, Persona, Notificacion


class MedicoPersonaSerilizer(PersonaBaseSerializer):

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NotificacionSerializer(Helper_ModelSerializer):

    class Meta:
        model = Notificacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']



