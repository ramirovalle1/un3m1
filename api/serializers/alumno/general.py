from rest_framework import serializers
from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from api.serializers.base.persona import PersonaBaseSerializer
from inno.models import CalendarioRecursoActividadAlumno, CalendarioRecursoActividad
from sagest.models import Rubro, TipoOtroRubro
from sga.models import Matricula, Persona, Inscripcion, Reporte, MatriculaGrupoSocioEconomico, \
    PeriodoGrupoSocioEconomico, Materia, Carrera, Sesion, NivelMalla, Asignatura, Malla, AsignaturaMalla, \
    MateriaAsignada, TestSilaboSemanal, TareaSilaboSemanal, ForoSilaboSemanal, TareaPracticaSilaboSemanal, Notificacion
from socioecon.models import GrupoSocioEconomico


class SesionSerializer(Helper_ModelSerializer):

    class Meta:
        model = Sesion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class PersonaSerializer(PersonaBaseSerializer):

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class CarreraSerializer(Helper_ModelSerializer):

    class Meta:
        model = Carrera
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class PeriodoGrupoSocioEconomicoSerializer(Helper_ModelSerializer):

    class Meta:
        model = PeriodoGrupoSocioEconomico
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MallaSerializer(Helper_ModelSerializer):
    carrera = CarreraSerializer()

    class Meta:
        model = Malla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NivelMallaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = NivelMalla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_idm(self, obj):
        return obj.id


class AsignaturaSerializer(Helper_ModelSerializer):

    class Meta:
        model = Asignatura
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class AsignaturaMallaSerializer(Helper_ModelSerializer):
    asignatura = AsignaturaSerializer()
    nivelmalla = NivelMallaSerializer()
    malla = MallaSerializer()

    class Meta:
        model = AsignaturaMalla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MateriaSerializer(Helper_ModelSerializer):
    asignatura = AsignaturaSerializer()
    asignaturamalla = AsignaturaMallaSerializer()

    class Meta:
        model = Materia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class InscripcionSerializer(Helper_ModelSerializer):
    persona = PersonaSerializer()
    carrera = CarreraSerializer()
    sesion = SesionSerializer()

    class Meta:
        model = Inscripcion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class GrupoSocioEconomicoSerializer(Helper_ModelSerializer):

    class Meta:
        model = GrupoSocioEconomico
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriculaSerializer(Helper_ModelSerializer):
    inscripcion = InscripcionSerializer()
    gruposocioeconomico = serializers.SerializerMethodField()

    class Meta:
        model = Matricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_gruposocioeconomico(self, obj):
        gruposocioeconomico = obj.matriculagruposocioeconomico()
        return GrupoSocioEconomicoSerializer(gruposocioeconomico).data if gruposocioeconomico else {}


class MateriaAsignadaSerializer(Helper_ModelSerializer):
    materia = MateriaSerializer()

    class Meta:
        model = MateriaAsignada
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class RubroSerializer(Helper_ModelSerializer):
    codigo_intermatico = serializers.SerializerMethodField()

    class Meta:
        model = Rubro
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_codigo_intermatico(self, obj):
        return obj.codigo_intermatico()


class TestSilaboSemanalSerializer(Helper_ModelSerializer):

    class Meta:
        model = TestSilaboSemanal
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class TareaSilaboSemanalSerializer(Helper_ModelSerializer):

    class Meta:
        model = TareaSilaboSemanal
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ForoSilaboSemanalSerializer(Helper_ModelSerializer):

    class Meta:
        model = ForoSilaboSemanal
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class TareaPracticaSilaboSemanalSerializer(Helper_ModelSerializer):

    class Meta:
        model = TareaPracticaSilaboSemanal
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']
