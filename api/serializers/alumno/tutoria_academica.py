from rest_framework import serializers
from django.db.models import Sum, F
from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from datetime import datetime, timedelta

from api.serializers.alumno.ubicacion import PaisSerializer, ProvinciaSerializer, CantonSerializer, ParroquiaSerializer
from api.serializers.base.persona import Helper_ModelSerializer, PersonaBaseSerializer
from inno.models import SolicitudTutoriaIndividual, HorarioTutoriaAcademica, SolicitudTutoriaIndividualTema
from settings import DEBUG
from sga.models import Persona, Profesor, Asignatura, Materia, MateriaAsignada, Periodo, Turno, DetalleSilaboSemanalTema


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


class PeriodoSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = Periodo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk


class TurnoSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = Turno
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk


class HorarioTutoriaAcademicaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    turno = TurnoSerializer()
    disponibletutoria = serializers.SerializerMethodField()

    class Meta:
        model = HorarioTutoriaAcademica
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_disponibletutoria(self, obj):
        if DEBUG:
            return True
        return obj.disponibletutoria()


class SolicitudTutoriaIndividualTemaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    descripcion = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudTutoriaIndividualTema
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_descripcion(self, obj):
        return obj.tema.temaunidadresultadoprogramaanalitico.descripcion


class SolicitudTutoriaIndividualSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    horario = HorarioTutoriaAcademicaSerializer()
    profesor = ProfesorSerializer()
    materiaasignada = MateriaAsignadaSerializer()
    estado_display = serializers.SerializerMethodField()
    topico_display = serializers.SerializerMethodField()
    tipo_display = serializers.SerializerMethodField()
    tipotutoria_display = serializers.SerializerMethodField()
    temas = serializers.SerializerMethodField()
    fechatutoria = serializers.SerializerMethodField()
    puede_aperturar_tutoria = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudTutoriaIndividual
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_estado_display(self, obj):
        return obj.get_estado_display()

    def get_topico_display(self, obj):
        return obj.get_topico_display()

    def get_tipo_display(self, obj):
        return obj.get_tipo_display()

    def get_tipotutoria_display(self, obj):
        return obj.get_tipotutoria_display()

    def get_temas(self, obj):
        eTemas = obj.temas()
        return SolicitudTutoriaIndividualTemaSerializer(eTemas, many=True).data if eTemas.values("id").exists() else []

    def get_fechatutoria(self, obj):
        return obj.fechatutoria.strftime(DATE_FORMAT) if obj.fechatutoria else None

    def get_puede_aperturar_tutoria(self, obj):
        hoy = datetime.now()
        if obj.estado in (1, 4) or obj.tipotutoria == 4:
            return False
        antes = datetime.combine(datetime.min, obj.tutoriacomienza) - timedelta(minutes=30)
        return obj.fechatutoria.date() == hoy.date() and antes.time() <= hoy.time() <= obj.tutoriatermina






