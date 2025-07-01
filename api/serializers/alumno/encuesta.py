# coding=utf-8
from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from sga.models import InscripcionEncuestaGrupoEstudiantes, EncuestaGrupoEstudiantes, PreguntaEncuestaGrupoEstudiantes, \
    RangoPreguntaEncuestaGrupoEstudiantes, OpcionCuadriculaEncuestaGrupoEstudiantes
from inno.models import MatriculaSedeExamen
from rest_framework import serializers

from sga.templatetags.sga_extras import encrypt


class AlumnoGrupoEncuestaSerializer(Helper_ModelSerializer):

    class Meta:
        model = InscripcionEncuestaGrupoEstudiantes
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class MatriculaSedeExamenSerializer(Helper_ModelSerializer):

    class Meta:
        model = MatriculaSedeExamen
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class RangoPreguntaEncuestaGrupoEstudiantesSerializer(Helper_ModelSerializer):

    class Meta:
        model = RangoPreguntaEncuestaGrupoEstudiantes
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class OpcionCuadriculaEncuestaGrupoEstudiantesSerializer(Helper_ModelSerializer):
    pregunta = serializers.SerializerMethodField()
    secuencia = serializers.SerializerMethodField()
    class Meta:
        model = OpcionCuadriculaEncuestaGrupoEstudiantes
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_secuencia(self, obj):
        return encrypt(obj.secuenciapregunta.id) if hasattr(obj, 'secuenciapregunta') and obj.secuenciapregunta else None

    def get_pregunta(self, obj):
        return  encrypt(obj.pregunta.id) if obj.pregunta else None


class PreguntasGrupoEncuestaSerializer(Helper_ModelSerializer):
    esta_vacia = serializers.SerializerMethodField()
    rangos = serializers.SerializerMethodField()
    total_opciones_cuadricula_filas = serializers.SerializerMethodField()
    opciones_cuadricula_columnas = serializers.SerializerMethodField()
    opciones_cuadricula_filas = serializers.SerializerMethodField()
    opciones_multiples = serializers.SerializerMethodField()
    es_secuencia = serializers.SerializerMethodField()

    class Meta:
        model = PreguntaEncuestaGrupoEstudiantes
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_esta_vacia(self, obj):
        return obj.esta_vacia()

    def get_rangos(self, obj):
        rangos = obj.rangos()
        return RangoPreguntaEncuestaGrupoEstudiantesSerializer(rangos, many=True).data if rangos.values("id").exists() else []

    def get_total_opciones_cuadricula_filas(self, obj):
        return obj.total_opciones_cuadricula_filas()

    def get_opciones_cuadricula_columnas(self, obj):
        opciones_cuadricula_columnas = obj.opciones_cuadricula_columnas()
        return OpcionCuadriculaEncuestaGrupoEstudiantesSerializer(opciones_cuadricula_columnas, many=True).data if opciones_cuadricula_columnas.only("id").exists() else []

    def get_opciones_cuadricula_filas(self, obj):
        opciones_cuadricula_filas = obj.opciones_cuadricula_filas()
        return OpcionCuadriculaEncuestaGrupoEstudiantesSerializer(opciones_cuadricula_filas, many=True).data if opciones_cuadricula_filas.only("id").exists() else []

    def get_opciones_multiples(self, obj):
        opciones_multiples = obj.opciones_multiples()
        return OpcionCuadriculaEncuestaGrupoEstudiantesSerializer(opciones_multiples, many=True).data if opciones_multiples.only("id").exists() else []

    def get_es_secuencia(self, obj):
        return PreguntaEncuestaGrupoEstudiantes.objects.filter(status=True,opcioncuadriculaencuestagrupoestudiantes__secuenciapregunta=obj.id).exclude(id=obj.id).exists()


class GrupoEncuestaSerializer(Helper_ModelSerializer):
    preguntas = serializers.SerializerMethodField()

    class Meta:
        model = EncuestaGrupoEstudiantes
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_preguntas(self, obj):
        preguntas = PreguntaEncuestaGrupoEstudiantes.objects.filter(encuesta=obj, status=True).order_by('orden')
        return PreguntasGrupoEncuestaSerializer(preguntas, many=True).data if preguntas.values("id").exists() else []

