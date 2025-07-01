from rest_framework import serializers
from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from api.serializers.base.persona import PersonaBaseSerializer
from certi.models import ConfiguracionCarnet, Carnet
from sga.models import Matricula, Persona


class PersonaSerializer(PersonaBaseSerializer):

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ConfiguracionCarnetSerializer(Helper_ModelSerializer):
    es_digital = serializers.SerializerMethodField()
    es_fisico = serializers.SerializerMethodField()
    es_anverso = serializers.SerializerMethodField()
    es_reverso = serializers.SerializerMethodField()
    es_anverso_y_reverso = serializers.SerializerMethodField()
    es_estudiante = serializers.SerializerMethodField()
    es_administrativo = serializers.SerializerMethodField()
    es_docente = serializers.SerializerMethodField()

    class Meta:
        model = ConfiguracionCarnet
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_es_digital(self, obj):
        return obj.es_digital()

    def get_es_fisico(self, obj):
        return obj.es_fisico()

    def get_es_anverso(self, obj):
        return obj.es_anverso()

    def get_es_reverso(self, obj):
        return obj.es_reverso()

    def get_es_anverso_y_reverso(self, obj):
        return obj.es_anverso_y_reverso()

    def get_es_estudiante(self, obj):
        return obj.es_estudiante()

    def get_es_administrativo(self, obj):
        return obj.es_administrativo()

    def get_es_docente(self, obj):
        return obj.es_docente()


class MatriculaSerializer(Helper_ModelSerializer):
    persona = serializers.SerializerMethodField()

    class Meta:
        model = Matricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_persona(self, obj):
        return PersonaSerializer(obj.inscripcion.persona).data if obj.inscripcion.persona else {}


class CarnetSerializer(Helper_ModelSerializer):
    persona = PersonaSerializer()
    png_anverso = serializers.SerializerMethodField()
    png_reverso = serializers.SerializerMethodField()
    pdf = serializers.SerializerMethodField()

    class Meta:
        model = Carnet
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_png_anverso(self, obj):
        if obj.png_anverso:
            return self.get_media_url(obj.png_anverso)
        return None

    def get_png_reverso(self, obj):
        if obj.png_reverso:
            return self.get_media_url(obj.png_reverso)
        return None

    def get_pdf(self, obj):
        if obj.pdf:
            return self.get_media_url(obj.pdf)
        return None


