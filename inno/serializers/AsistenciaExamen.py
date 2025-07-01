# coding=utf-8
from datetime import datetime

from django.core.exceptions import ObjectDoesNotExist

from inno.models import FechaPlanificacionSedeVirtualExamen, TurnoPlanificacionSedeVirtualExamen, \
    AulaPlanificacionSedeVirtualExamen, MateriaAsignadaPlanificacionSedeVirtualExamen, MatriculaSedeExamen
from sga.funciones import null_to_decimal, null_to_numeric, variable_valor
from sga.models import Carrera, Sesion, Coordinacion, Modalidad, Malla, NivelMalla, Paralelo, AsignaturaMalla, \
    Materia, Asignatura, MateriaAsignada, ModeloEvaluativo, Persona, ProfesorMateria, Profesor, TipoProfesor, Clase, \
    Aula, Bloque, Turno, DetalleModeloEvaluativo, HorarioExamen, HorarioExamenDetalle, Administrativo, Matricula, \
    Inscripcion, InscripcionEncuestaGrupoEstudiantes, RespuestaPreguntaEncuestaGrupoEstudiantes, MONTH_NAMES, \
    SedeVirtual, LaboratorioVirtual, Nivel, Periodo
from rest_framework import serializers
from api.serializers.base.modalidad import BaseModalidadSerializer
from api.serializers.base.persona import PersonaBaseSerializer
from api.helpers.serializers_model_helper import Helper_ModelSerializer
from sga.templatetags.sga_extras import encrypt


class PersonaSerializer(PersonaBaseSerializer):

    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class Persona2Serializer(Helper_ModelSerializer):
    nombre_completo = serializers.CharField(read_only=True)
    tipo_documento = serializers.CharField(read_only=True)
    documento = serializers.CharField(read_only=True)
    foto_perfil = serializers.SerializerMethodField()

    class Meta:
        model = Persona
        fields = ['nombre_completo', 'tipo_documento', 'documento', 'foto_perfil']
        # exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_nombre_completo(self, obj):
        return obj.nombre_completo()

    def get_documento(self, obj):
        return obj.documento()

    def get_tipo_documento(self, obj):
        return obj.tipo_documento()

    def get_foto_perfil(self, obj):
        if obj.tiene_foto():
            return obj.foto().foto.url
        if obj.sexo and obj.sexo.id == 1:
            foto_perfil = '/static/images/iconos/mujer.png'
        else:
            foto_perfil = '/static/images/iconos/hombre.png'
        return foto_perfil


class CarreraSerializer(Helper_ModelSerializer):
    modalidad_display = serializers.SerializerMethodField()

    class Meta:
        model = Carrera
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_modalidad_display(self, obj):
        return obj.get_modalidad_display()


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
        return obj.id


class PeriodoSerializer(Helper_ModelSerializer):

    class Meta:
        model = Periodo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class NivelSerializer(Helper_ModelSerializer):
    periodo = PeriodoSerializer()

    class Meta:
        model = Nivel
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MatriculaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    nivel = NivelSerializer()
    inscripcion = InscripcionSerializer()

    class Meta:
        model = Matricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class MatriculaSedeExamenSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    download_archivoidentidad = serializers.SerializerMethodField()
    download_archivofoto = serializers.SerializerMethodField()

    class Meta:
        model = MatriculaSedeExamen
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_download_archivoidentidad(self, obj):
        archivoidentidad = obj.archivoidentidad
        if archivoidentidad:
            return self.get_media_url(archivoidentidad.url) if archivoidentidad else None
        return None

    def get_download_archivofoto(self, obj):
        archivofoto = obj.archivofoto
        if archivofoto:
            return self.get_media_url(archivofoto.url) if archivofoto else None
        return None


class AsignaturaSerializer(Helper_ModelSerializer):

    class Meta:
        model = Asignatura
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class MallaSerializer(Helper_ModelSerializer):
    carrera = CarreraSerializer()
    display = serializers.SerializerMethodField()

    class Meta:
        model = Malla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_display(self, obj):
        return u'%s (%s %s)' % (obj.carrera.nombre_completo(), MONTH_NAMES[obj.inicio.month - 1], str(obj.inicio.year))


class NivelMallaSerializer(Helper_ModelSerializer):

    class Meta:
        model = NivelMalla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class AsignaturaMallaSerializer(Helper_ModelSerializer):
    malla = MallaSerializer()
    asignatura = AsignaturaSerializer()
    nivelmalla = NivelMallaSerializer()

    class Meta:
        model = AsignaturaMalla
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class ParaleloSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = Paralelo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class MateriaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    asignaturamalla = AsignaturaMallaSerializer()
    asignatura = AsignaturaSerializer()
    paralelomateria = ParaleloSerializer()

    class Meta:
        model = Materia
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class MateriaAsignadaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    matricula = MatriculaSerializer()
    materia = MateriaSerializer()

    class Meta:
        model = MateriaAsignada
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class SedeVirtualSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    imagen_url = serializers.SerializerMethodField()

    class Meta:
        model = SedeVirtual
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_fields(self):
        fields = super().get_fields()

        exclude_fields = self.context.get('exclude_fields', [])
        for field in exclude_fields:
            # providing a default prevents a KeyError
            # if the field does not exist
            fields.pop(field, default=None)

        return fields

    def get_imagen_url(self, obj):
        if obj.foto and obj.foto.url:
            return obj.foto.url
        return None


class FechaPlanificacionSedeVirtualExamenSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    sede = SedeVirtualSerializer()
    es_pasado = serializers.SerializerMethodField()

    class Meta:
        model = FechaPlanificacionSedeVirtualExamen
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_fields(self):
        fields = super().get_fields()

        exclude_fields = self.context.get('exclude_fields', [])
        for field in exclude_fields:
            # providing a default prevents a KeyError
            # if the field does not exist
            fields.pop(field, default=None)

        return fields

    def get_es_pasado(self, obj):
        from datetime import datetime
        ahora = datetime.now()
        return obj.fecha < ahora.date()


class TurnoPlanificacionSedeVirtualExamenSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    fechaplanificacion = FechaPlanificacionSedeVirtualExamenSerializer()
    es_pasado = serializers.SerializerMethodField()

    class Meta:
        model = TurnoPlanificacionSedeVirtualExamen
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_fields(self):
        fields = super().get_fields()

        exclude_fields = self.context.get('exclude_fields', [])
        for field in exclude_fields:
            # providing a default prevents a KeyError
            # if the field does not exist
            fields.pop(field, default=None)

        return fields

    def get_es_pasado(self, obj):
        from datetime import datetime
        ahora = datetime.now()
        if obj.fechaplanificacion.fecha < ahora.date():
            return True
        else:
            if obj.fechaplanificacion.fecha == ahora.date():
                # horainicio = obj.horainicio
                horafin = obj.horafin
                return not ahora.time() <= horafin
            return False



class BloqueSerializer(Helper_ModelSerializer):

    class Meta:
        model = Bloque
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class LaboratorioVirtualSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    bloque = BloqueSerializer()

    class Meta:
        model = LaboratorioVirtual
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_fields(self):
        fields = super().get_fields()

        exclude_fields = self.context.get('exclude_fields', [])
        for field in exclude_fields:
            # providing a default prevents a KeyError
            # if the field does not exist
            fields.pop(field, default=None)

        return fields


class AulaPlanificacionSedeVirtualExamenSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    turnoplanificacion = TurnoPlanificacionSedeVirtualExamenSerializer()
    aula = LaboratorioVirtualSerializer()

    class Meta:
        model = AulaPlanificacionSedeVirtualExamen
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id

    def get_fields(self):
        fields = super().get_fields()

        exclude_fields = self.context.get('exclude_fields', [])
        for field in exclude_fields:
            # providing a default prevents a KeyError
            # if the field does not exist
            fields.pop(field, default=None)

        return fields


class MateriaAsignadaPlanificacionSedeVirtualExamenSerializer(Helper_ModelSerializer):
    aulaplanificacion = AulaPlanificacionSedeVirtualExamenSerializer()
    materiaasignada = MateriaAsignadaSerializer()
    matriculasedeexamen = serializers.SerializerMethodField()

    class Meta:
        model = MateriaAsignadaPlanificacionSedeVirtualExamen
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_matriculasedeexamen(self, obj):
        eMatricula = obj.materiaasignada.matricula
        try:
            eMatriculaSedeExamen = MatriculaSedeExamen.objects.get(matricula=eMatricula)
            return MatriculaSedeExamenSerializer(eMatriculaSedeExamen).data
        except ObjectDoesNotExist:
            return None
