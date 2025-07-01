# coding=utf-8
from datetime import datetime

from sga.funciones import null_to_decimal
from sga.models import Inscripcion, NivelMalla, MateriaAsignada, Nivel, Malla, Carrera, Persona, \
    Periodo, Asignatura, Sesion, Materia, AsignaturaMalla, Coordinacion, Sede, RecordAcademico, ModuloMalla, \
    MateriaCursoEscuelaComplementaria, CursoEscuelaComplementaria, Profesor, Modalidad, MateriaAsignadaHomologacion, \
    MateriaAsignadaConvalidacion, HomologacionInscripcion, EjeFormativo, MONTH_NAMES, AsignaturaMallaPredecesora
from rest_framework import serializers
from api.serializers.base.persona import PersonaBaseSerializer
from api.serializers.base.modalidad import BaseModalidadSerializer
from api.helpers.serializers_model_helper import Helper_ModelSerializer


class NivelMallaSerializer(Helper_ModelSerializer):

    class Meta:
        model = NivelMalla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ModalidadSerializer(BaseModalidadSerializer):

    class Meta:
        model = Modalidad
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MallaPersonaSerializer(PersonaBaseSerializer):

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class CoordinacionSerializer(Helper_ModelSerializer):

    class Meta:
        model = Coordinacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class CarreraSerializer(Helper_ModelSerializer):

    class Meta:
        model = Carrera
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class InscripcionSerializer(Helper_ModelSerializer):
    persona = MallaPersonaSerializer()
    carrera = CarreraSerializer()
    coordinacion = CoordinacionSerializer()
    modalidad = ModalidadSerializer()

    class Meta:
        model = Inscripcion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class EjeFormativoSerializer(Helper_ModelSerializer):

    class Meta:
        model = EjeFormativo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MallaSerializer(Helper_ModelSerializer):
    carrera = CarreraSerializer()
    modalidad = ModalidadSerializer()
    niveles = serializers.SerializerMethodField()
    ejesformativos = serializers.SerializerMethodField()
    fecha_display = serializers.SerializerMethodField()

    class Meta:
        model = Malla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_niveles(self, obj):
        niveles = obj.niveles_malla()
        if niveles.values("id").exists():
            return NivelMallaSerializer(niveles, many=True).data
        return []

    def get_ejesformativos(self, obj):
        ejes = EjeFormativo.objects.filter(status=True, id__in=AsignaturaMalla.objects.values_list('ejeformativo_id', flat=True).filter(malla=obj, status=True, vigente=True).distinct()).order_by('nombre')
        return EjeFormativoSerializer(ejes, many=True).data if ejes.values("id").exists() else []

    def get_fecha_display(self, obj):
        return u"%s %s" % (MONTH_NAMES[obj.inicio.month - 1], str(obj.inicio.year))


class AsignaturaSerializer(Helper_ModelSerializer):

    class Meta:
        model = Asignatura
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class AsignaturaMallaSerializer(Helper_ModelSerializer):
    asignatura = AsignaturaSerializer()
    nivelmalla = NivelMallaSerializer()
    ejeformativo = EjeFormativoSerializer()

    class Meta:
        model = AsignaturaMalla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class AsignaturaMallaPredecesoraSerializer(Helper_ModelSerializer):
    predecesora = AsignaturaMallaSerializer()

    class Meta:
        model = AsignaturaMallaPredecesora
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class RecordAcademicoSerializer(Helper_ModelSerializer):

    class Meta:
        model = RecordAcademico
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']
