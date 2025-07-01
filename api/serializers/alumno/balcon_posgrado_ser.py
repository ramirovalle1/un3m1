from rest_framework import serializers

from api.helpers.serializers_model_helper import Helper_ModelSerializer

from sga.models import Periodo
from posgrado.models import SolicitudBalcon, TipoSolicitudBalcon

class PeriodoSerializer(Helper_ModelSerializer):
    class Meta:
        model = Periodo
        fields = '__all__'

class TipoSolicitudSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = TipoSolicitudBalcon
        fields = ['pk', 'nombre', 'descripcion']

    def get_pk(self, obj):
        return obj.pk

class HistorialSolicitudSerializer(Helper_ModelSerializer):
    history_date = serializers.SerializerMethodField()
    estado_display = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudBalcon.history.model
        fields = '__all__'

    def get_history_date(self, obj):
        return obj.history_date.strftime('%d/%m/%Y')

    def get_estado_display(self, obj):
        return obj.get_estado_display()

class SolicitudBalconSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    tipo_solicitud = serializers.SerializerMethodField()
    estado = serializers.SerializerMethodField()
    maestrante = serializers.SerializerMethodField()
    es_reasignada = serializers.SerializerMethodField()
    is_calificada = serializers.SerializerMethodField()
    calificacion_display = serializers.SerializerMethodField()
    historycal = serializers.SerializerMethodField()
    archivo_respuesta = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudBalcon
        fields = '__all__'

    def get_pk(self, obj):
        return obj.pk

    def get_estado(self, obj):
        return obj.get_estado_display()

    def get_tipo_solicitud(self, obj):
        return obj.tipo_solicitud.nombre

    def get_maestrante(self, obj):
        return obj.materia_asignada.matricula.inscripcion.__str__()

    def get_es_reasignada(self, obj):
        return obj.es_reasignada()

    def get_is_calificada(self, obj):
        if obj.estado == 3:
            return obj.is_finalizada_calificacion()
        return True

    def get_calificacion_display(self, obj):
        estrellas_llenas = '★' * obj.calificacion
        estrellas_vacias = '☆' * (5 - obj.calificacion)
        return f'{estrellas_llenas}{estrellas_vacias}'

    def get_historycal(self, obj):
        return HistorialSolicitudSerializer(obj.historical_solicitud(), many=True).data if obj.historical_solicitud() else None

    def get_archivo_respuesta(self, obj):
        return self.get_media_url(obj.get_respuesta_archivo().url) if obj.get_respuesta_archivo() else None