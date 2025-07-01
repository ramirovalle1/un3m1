from rest_framework import serializers
from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from api.serializers.base.persona import PersonaBaseSerializer
from sga.models import Matricula, Persona, SolicitudTutorSoporteMatricula, Profesor, SolicitudTutorSoporteMateria, \
    MateriaAsignada, Materia, Asignatura


class PersonaSerializer(PersonaBaseSerializer):

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ProfesorSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    persona = PersonaSerializer()

    class Meta:
        model = Profesor
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk


class AsignaturaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = Asignatura
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk


class MateriaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    asignatura = AsignaturaSerializer()

    class Meta:
        model = Materia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk


class MateriaAsignadaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    materia = MateriaSerializer()

    class Meta:
        model = MateriaAsignada
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk


class SolicitudTutorSoporteMateriaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    tipo_display = serializers.SerializerMethodField()
    download_archivo = serializers.SerializerMethodField()
    estado_display = serializers.SerializerMethodField()
    profesor = ProfesorSerializer()
    materiaasignada = MateriaAsignadaSerializer()

    class Meta:
        model = SolicitudTutorSoporteMateria
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

    def get_tipo_display(self, obj):
        return obj.get_tipo_display()

    def get_download_archivo(self, obj):
        return self.get_media_url(obj.archivo.url) if obj.archivo else None

    def get_estado_display(self, obj):
        return obj.get_estado_display()


class SolicitudTutorSoporteMatriculaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    tipo_display = serializers.SerializerMethodField()
    download_archivo = serializers.SerializerMethodField()
    estado_display = serializers.SerializerMethodField()
    tutor = ProfesorSerializer()
    fue_atendido = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudTutorSoporteMatricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

    def get_tipo_display(self, obj):
        return obj.get_tipo_display()

    def get_download_archivo(self, obj):
        return self.get_media_url(obj.archivo.url) if obj.archivo else None

    def get_estado_display(self, obj):
        return obj.get_estado_display()

    def get_fue_atendido(self, obj):
        return obj.fue_atendido()






