# coding=utf-8
from django.contrib.auth.models import User, Group

from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from api.serializers.base.persona import PersonaBaseSerializer
from sga.models import InsigniaPersona, Insignia, CategoriaInsignia, Persona
from rest_framework import serializers

class PersonaParticipanteSerializer(PersonaBaseSerializer):

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class CategoriaInsigniaSerializer(Helper_ModelSerializer):

    class Meta:
        model = CategoriaInsignia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class InsigniaSerializer(Helper_ModelSerializer):

    class Meta:
        model = Insignia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class InsigniaPersonaSerializer(Helper_ModelSerializer):
    insignia = InsigniaSerializer()
    persona = PersonaParticipanteSerializer()

    class Meta:
        model = InsigniaPersona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']



