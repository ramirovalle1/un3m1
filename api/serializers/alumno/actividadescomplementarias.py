from datetime import datetime

from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from api.serializers.base.persona import PersonaBaseSerializer
from rest_framework import serializers
from sga.models import Matricula, Persona, PaeActividadesPeriodoAreas, PaeInscripcionActividades, Inscripcion, PaePeriodoAreas, PaeAreas, Coordinacion, Nivel, PaeFechaActividad, Periodo, InscripcionActividadesSolicitud


class ComplementariaPersonaSerilizer(PersonaBaseSerializer):
    class Meta:
        model = Persona
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class ComplementariaInscripcionSerializer(Helper_ModelSerializer):
    persona = ComplementariaPersonaSerilizer()
    class Meta:
        model = Inscripcion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class ComplementariaInscripcionSerializer_2(Helper_ModelSerializer):
    persona = ComplementariaPersonaSerilizer()
    class Meta:
        model = Inscripcion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class PaeInscripcionPeriodoSerilizer(Helper_ModelSerializer):
    class Meta:
        model = Periodo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class PaeInscripcionNivelSerilizer(Helper_ModelSerializer):
    periodo = PaeInscripcionPeriodoSerilizer()
    class Meta:
        model = Nivel
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class ComplementariaMatriculaSerializer(Helper_ModelSerializer):
    inscripcion = ComplementariaInscripcionSerializer()
    nivel = PaeInscripcionNivelSerilizer()
    class Meta:
        model = Matricula
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class PaeInscripcionCoordinacion(Helper_ModelSerializer):
    class Meta:
        model = Coordinacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class PaeInscripcionAreas(Helper_ModelSerializer):
    class Meta:
        model = PaeAreas
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class PaeInscripcionPaePeriodoAreas(Helper_ModelSerializer):
    areas = PaeInscripcionAreas()
    class Meta:
        model = PaePeriodoAreas
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class PaeFechaActividadSerializer_2(Helper_ModelSerializer):
    class Meta:
        model = PaeFechaActividad
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class PaeInscripcionPaeActividadesPeriodoAreas(Helper_ModelSerializer):
    coordinacion = PaeInscripcionCoordinacion()
    periodoarea = PaeInscripcionPaePeriodoAreas()
    grupo_display = serializers.SerializerMethodField()
    listafechas = serializers.SerializerMethodField()
    idm = serializers.SerializerMethodField()
    class Meta:
        model = PaeActividadesPeriodoAreas
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']
    def get_idm(self, obj):
        return obj.id
    def get_grupo_display(self, obj):
        return obj.get_grupo_display()
    def get_listafechas(self, obj):
        fechas = obj.listafechas()
        return PaeFechaActividadSerializer_2(fechas, many = True).data  if fechas else []

class PaeInscripcionActividadesSolicitud(Helper_ModelSerializer):
    estado_display = serializers.SerializerMethodField()
    class Meta:
        model = InscripcionActividadesSolicitud
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']
    def get_estado_display(self, obj):
        return obj.get_estado_display()

class PaeInscripcionActividadesSerializer(Helper_ModelSerializer):
    matricula = ComplementariaMatriculaSerializer()
    actividades = PaeInscripcionPaeActividadesPeriodoAreas()
    en_uso = serializers.SerializerMethodField()
    puedeenviarsolicitudalumno = serializers.SerializerMethodField()
    enviosolicitud = serializers.SerializerMethodField()
    download_link = serializers.SerializerMethodField()
    class Meta:
        model = PaeInscripcionActividades
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_en_uso(self, obj):
        return obj.en_uso()

    def get_puedeenviarsolicitudalumno(self, obj):
        return obj.puedeenviarsolicitudalumno()

    def get_enviosolicitud(self, obj):
        soli = obj.enviosolicitud()
        return PaeInscripcionActividadesSolicitud(soli).data if soli else None
    def get_download_link(self, obj):
        if obj.archivo:
            return obj.download_link()
        else:
            return None


class AreasSerializer(Helper_ModelSerializer):
    class Meta:
        model = PaeAreas
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class PeriodoAreasSerializer(Helper_ModelSerializer):
    areas = AreasSerializer()
    class Meta:
        model = PaePeriodoAreas
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class CoordinacionSerializer(Helper_ModelSerializer):
    class Meta:
        model = Coordinacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class NivelSerializer(Helper_ModelSerializer):
    class Meta:
        model = Nivel
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class PaeFechaActividadSerializer(Helper_ModelSerializer):
    class Meta:
        model = PaeFechaActividad
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class PaeActividadesPeriodoAreasSerializer(Helper_ModelSerializer):
    nivel = NivelSerializer()
    periodoarea = PeriodoAreasSerializer()
    idm = serializers.SerializerMethodField()
    coordinacion = CoordinacionSerializer()
    grupo_display = serializers.SerializerMethodField()
    listafechas = serializers.SerializerMethodField()
    restadisponibles = serializers.SerializerMethodField()
    entrefechas = serializers.SerializerMethodField()
    class Meta:
        model = PaeActividadesPeriodoAreas
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']
    def get_idm(self, obj):
        return obj.id
    def get_grupo_display(self, obj):
        return obj.get_grupo_display()
    def get_listafechas(self, obj):
        fechas = obj.listafechas()
        return PaeFechaActividadSerializer(fechas, many = True).data  if fechas else []
    def get_restadisponibles(self, obj):
        cupo = int(obj.cupo)
        inscritos = obj.totalinscritos()
        return cupo - inscritos
    def get_entrefechas(self, obj):
        if datetime.now().date() >= obj.fechainicio and datetime.now().date() <= obj.fechafin:
            return True
        else:
            return False
