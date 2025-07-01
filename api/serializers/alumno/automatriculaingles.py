from rest_framework import serializers
from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.serializers.base.modalidad import BaseModalidadSerializer
from api.serializers.base.persona import PersonaBaseSerializer
from sga.models import Asignatura, Malla, Carrera, Persona, Modalidad, Inscripcion, Nivel


class AsignaturaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    class Meta:
        model = Asignatura
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

class NivelSerializer(Helper_ModelSerializer):
    class Meta:
        model = Nivel
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class CarreraSerializer(Helper_ModelSerializer):
    modalidad_display = serializers.SerializerMethodField()

    class Meta:
        model = Carrera
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_modalidad_display(self, obj):
        return obj.get_modalidad_display()

class MallaSerializer(Helper_ModelSerializer):
    carrera = CarreraSerializer()

    class Meta:
        model = Malla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class PersonaSerializer(PersonaBaseSerializer):

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class ModalidadSerializer(BaseModalidadSerializer):
    class Meta:
        model = Modalidad
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class InscripcionSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    persona = PersonaSerializer()
    carrera = CarreraSerializer()
    modalidad = ModalidadSerializer()

    class Meta:
        model = Inscripcion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk