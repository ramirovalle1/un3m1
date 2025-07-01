from api.helpers.serializers_model_helper import Helper_ModelSerializer
from rest_framework import serializers
from api.serializers.base.persona import PersonaBaseSerializer
from bd.models import UserToken
from sga.models import Persona


class PersonaSerializer(PersonaBaseSerializer):

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class UserTokenSerializer(Helper_ModelSerializer):

    class Meta:
        model = UserToken
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']