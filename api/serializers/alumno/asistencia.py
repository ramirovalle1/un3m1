from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from api.serializers.base.persona import PersonaBaseSerializer
from rest_framework import serializers

from inno.models import LogIngresoAsistenciaLeccion
from sga.models import Matricula, Persona, Inscripcion, Carrera, Malla, Modalidad, MONTH_NAMES, MateriaAsignada, Materia, AsistenciaLeccion, Leccion


class AsistenciaPersonaSerilizer(PersonaBaseSerializer):

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class AistenciaInscripcionSerializer(Helper_ModelSerializer):
    persona = AsistenciaPersonaSerilizer()

    class Meta:
        model = Inscripcion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class AsistenciaMallaSerializer(Helper_ModelSerializer):

    class Meta:
        model = Malla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class AsistenciaMateriaSerializer(Helper_ModelSerializer):
    nombre_mostrar = serializers.SerializerMethodField()

    class Meta:
        model = Materia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_nombre_mostrar(self, obj):
        nombre = obj.nombre_mostrar()
        ePeriodoMatriculas = obj.nivel.periodo.periodomatricula_set.filter(status=True)
        if ePeriodoMatriculas.values("id").exists():
            ePeriodoMatricula = ePeriodoMatriculas[0]
            if not ePeriodoMatricula.ver_profesor_materia:
                nombre = obj.nombre_mostrar_sin_profesor()
        return nombre


class LeccionSerializer(Helper_ModelSerializer):

    class Meta:
        model = Leccion
        exclude = ['usuario_creacion', 'usuario_modificacion']


class LogIngresoAsistenciaLeccionSerializer(Helper_ModelSerializer):
    class Meta:
        model = LogIngresoAsistenciaLeccion
        exclude = ['usuario_creacion', 'usuario_modificacion']


class AsistenciaLeccionSerializer(Helper_ModelSerializer):

    leccion = LeccionSerializer()
    fecha_clase_verbose = serializers.SerializerMethodField()
    valida = serializers.SerializerMethodField()

    class Meta:
        model = AsistenciaLeccion
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_fecha_clase_verbose(self, obj):
        return obj.fecha_clase_verbose()

    def get_valida(self, obj):
        return obj.valida()


class AsistenciaLeccionSerializer2(Helper_ModelSerializer):
    leccion = LeccionSerializer()
    fecha_clase_verbose = serializers.SerializerMethodField()
    valida = serializers.SerializerMethodField()

    class Meta:
        model = AsistenciaLeccion
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_fecha_clase_verbose(self, obj):
        return obj.fecha_clase_verbose()

    def get_valida(self, obj):
        return obj.valida()


class AsistenciaMateriaAsignada(Helper_ModelSerializer):
    materia = AsistenciaMateriaSerializer()
    porciento_asistencia_justificada_asis = serializers.SerializerMethodField()
    real_dias_asistencia = serializers.SerializerMethodField()
    asistencia_real = serializers.SerializerMethodField()
    faltas = serializers.SerializerMethodField()

    class Meta:
        model = MateriaAsignada
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_porciento_asistencia_justificada_asis(self, obj):
        return obj.porciento_asistencia_justificada_asis()

    def get_real_dias_asistencia(self, obj):
        return obj.real_dias_asistencia()

    def get_asistencia_real(self, obj):
        return obj.asistencia_real()

    def get_faltas(self, obj):
        dias = obj.real_dias_asistencia()
        asis = obj.asistencia_real()
        resta = int(dias) - int(asis)
        return resta


class MatriculaSerializer(Helper_ModelSerializer):
    class Meta:
        model = Matricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

