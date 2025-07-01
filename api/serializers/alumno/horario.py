from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from django.utils.safestring import mark_safe

from api.serializers.base.modalidad import BaseModalidadSerializer
from api.serializers.base.persona import PersonaBaseSerializer
from rest_framework import serializers

from inno.models import PeriodoAcademia
from sga.models import Persona, Carrera, Coordinacion, Modalidad, Inscripcion, Matricula, Periodo, Malla, NivelMalla, \
    Sesion, Nivel, MONTH_NAMES, Clase, Aula, TipoUbicacionAula, Bloque


class PersonaSerializer(PersonaBaseSerializer):

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NivelMallaSerializer(Helper_ModelSerializer):

    class Meta:
        model = NivelMalla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class SesionSerializer(Helper_ModelSerializer):

    class Meta:
        model = Sesion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class PeriodoSerializer(Helper_ModelSerializer):

    class Meta:
        model = Periodo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class PeriodoAcademiaSerializer(Helper_ModelSerializer):
    periodo = PeriodoSerializer()

    class Meta:
        model = PeriodoAcademia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class CarreraSerializer(Helper_ModelSerializer):

    class Meta:
        model = Carrera
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class CoordinacionSerializer(Helper_ModelSerializer):

    class Meta:
        model = Coordinacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ModalidadSerializer(BaseModalidadSerializer):

    class Meta:
        model = Modalidad
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class InscripcionSerializer(Helper_ModelSerializer):
    persona = PersonaSerializer()
    carrera = CarreraSerializer()
    coordinacion = CoordinacionSerializer()
    modalidad = ModalidadSerializer()
    sesion = SesionSerializer()

    class Meta:
        model = Inscripcion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NivelSerializer(Helper_ModelSerializer):
    periodo = PeriodoSerializer()

    class Meta:
        model = Nivel
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriculaSerializer(Helper_ModelSerializer):
    inscripcion = InscripcionSerializer()
    nivel = NivelSerializer()

    class Meta:
        model = Matricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MallaSerializer(Helper_ModelSerializer):
    carrera = CarreraSerializer()
    modalidad = ModalidadSerializer()
    fecha_display = serializers.SerializerMethodField()

    class Meta:
        model = Malla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_fecha_display(self, obj):
        return u"%s %s" % (MONTH_NAMES[obj.inicio.month - 1], str(obj.inicio.year))


class TipoUbicacionAulaSerializer(Helper_ModelSerializer):

    class Meta:
        model = TipoUbicacionAula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class BloqueSerializer(Helper_ModelSerializer):
    foto = serializers.SerializerMethodField()

    class Meta:
        model = Bloque
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_foto(self, obj):
        return self.get_media_url(obj.foto.url) if obj.foto else None


class AulaSerializer(Helper_ModelSerializer):
    tipoubicacion = TipoUbicacionAulaSerializer()
    bloque = BloqueSerializer()

    class Meta:
        model = Aula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ClaseSerializer(Helper_ModelSerializer):
    aula = AulaSerializer()

    class Meta:
        model = Clase
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']
