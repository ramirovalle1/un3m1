from rest_framework import serializers

from api.helpers.serializers_model_helper import Helper_ModelSerializer
from idioma.models import Periodo, Grupo, GrupoInscripcion, GrupoInscripcionAsignatura
from sga.models import Idioma, Asignatura


def current_date_format(date):
    months = ("Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre")
    days = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")
    day_of_week = days[int(date.strftime("%w")) - 1]
    day = date.day
    month = months[date.month - 1]
    year = date.year
    return "{}, {} de {} del {}".format(day_of_week, day, month, year)

def day_of_week(date):
    months = ("Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre")
    days = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")
    day_of_week = days[int(date.strftime("%w")) - 1]
    day = date.day
    month = months[date.month - 1]
    year = date.year
    return "{}".format(day_of_week)

class IdiomaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    class Meta:
        model = Idioma
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

class PeriodoSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    idioma = IdiomaSerializer()
    fecinicioinscripcion_display = serializers.SerializerMethodField()
    fecfininscripcion_display = serializers.SerializerMethodField()
    cronograma_fechas_inscripcion_activa = serializers.SerializerMethodField()
    class Meta:
        model = Periodo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

    def get_fecinicioinscripcion_display(self, obj):
        return current_date_format(obj.fecinicioinscripcion) if obj.fecinicioinscripcion else None

    def get_fecfininscripcion_display(self, obj):
        return current_date_format(obj.fecfininscripcion) if obj.fecfininscripcion else None

    def get_cronograma_fechas_inscripcion_activa(self,obj):
        return obj.cronograma_fechas_inscripcion_activa()


class GrupoSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    periodo = PeriodoSerializer()
    inicio_display = serializers.SerializerMethodField()
    fecha_inicio_display = serializers.SerializerMethodField()
    existe_cupo_disponible = serializers.SerializerMethodField()
    horario = serializers.SerializerMethodField()
    cupos_disponible  = serializers.SerializerMethodField()
    existe_curso_moodle  = serializers.SerializerMethodField()
    puede_visualizar_url_moodle  = serializers.SerializerMethodField()

    class Meta:
        model = Grupo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

    def get_inicio_display(self, obj):
        return day_of_week(obj.fecinicio) if obj.fecinicio else None

    def get_fecha_inicio_display(self, obj):
        return current_date_format(obj.fecinicio) if obj.fecinicio else None

    def get_existe_cupo_disponible(self,obj):
        return obj.existe_cupo_disponible()

    def get_horario(self,obj):
        return obj.horario()

    def get_cupos_disponible(self,obj):
        return obj.cupos_disponible()

    def get_existe_curso_moodle(self,obj):
        return obj.existe_curso_moodle()

    def get_puede_visualizar_url_moodle(self,obj):
        return obj.puede_visualizar_url_moodle()

class AsignaturaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    class Meta:
        model = Asignatura
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk


class GrupoInscripcionSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    grupo = GrupoSerializer()
    estado_display  = serializers.SerializerMethodField()
    obtener_asignaturas_homologadas  = serializers.SerializerMethodField()
    permite_eliminar = serializers.SerializerMethodField()


    class Meta:
        model = GrupoInscripcion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

    def get_obtener_asignaturas_homologadas(self, obj):
        return GrupoInscripcionAsignaturaSerializer(obj.obtener_asignaturas_homologadas(), many=True).data if obj.obtener_asignaturas_homologadas() else []

    def get_estado_display(self,obj):
        return obj.get_estado_display()

    def get_permite_eliminar(self, obj):
        from datetime import datetime
        from sga.funciones import variable_valor
        return obj.grupo.periodo.fecfininscripcion.date() >= datetime.now().date() or variable_valor('ELIMINAR_INSCRIPCION_INGLES')

class GrupoInscripcionAsignaturaSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    asignatura = AsignaturaSerializer()

    class Meta:
        model = GrupoInscripcionAsignatura
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.pk

