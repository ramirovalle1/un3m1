from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from api.serializers.base.persona import PersonaBaseSerializer
from rest_framework import serializers
from sga.models import Matricula, Persona
from med.models import ProximaCita


class MedicoPersonaSerilizer(PersonaBaseSerializer):
    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ProximaCitaSerializer(Helper_ModelSerializer):
    medico = MedicoPersonaSerilizer()
    vigente = serializers.SerializerMethodField()

    class Meta:
        model = ProximaCita
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_vigente(self, obj):
        return obj.vigente()



