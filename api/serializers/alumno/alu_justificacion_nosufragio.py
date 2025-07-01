from api.helpers.serializers_model_helper import Helper_ModelSerializer
from rest_framework import serializers

from sagest.models import SolicitudJustificacionPE


class JustificacionNoSufragioSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    download_link = serializers.SerializerMethodField()
    fecha_creacion_format = serializers.SerializerMethodField()
    periodo_academico = serializers.SerializerMethodField()
    proceso_id = serializers.SerializerMethodField()
    proceso_des = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudJustificacionPE
        fields = ['id', 'status', 'motivo', 'download_link', 'estado', 'pk', 'fecha_creacion_format', 'observacion',
                  'periodo_academico', 'proceso_id', 'proceso_des']

    def get_pk(self, obj):
        return obj.pk

    def get_download_link(self, obj):
        if obj.archivo:
            return self.get_media_url(obj.archivo.url)
        return ''

    def get_fecha_creacion_format(self, obj):
        return obj.fecha_creacion.strftime('%d-%m-%Y %H:%M')

    def get_periodo_academico(self, obj):
        return obj.proceso.periodoacademico.nombre

    def get_proceso_id(self, obj):
        return obj.proceso.id

    def get_proceso_des(self, obj):
        return obj.proceso.descripcion