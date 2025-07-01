from api.helpers.serializers_model_helper import Helper_ModelSerializer
from rest_framework import serializers
from posgrado.models import ParticipanteProyectoVinculacionPos, ProyectoVinculacion, DetalleAprobacionProyecto


class ProyectoVinculacionSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()
    detalleaprobacionproyecto = serializers.SerializerMethodField()

    class Meta:
        model = ProyectoVinculacion
        fields = ['id', 'status', 'titulo', 'descripcion', 'estadoaprobacion', 'pk', 'detalleaprobacionproyecto']

    def get_pk(self, obj):
        return obj.pk

    def get_detalleaprobacionproyecto(self, obj):
        return obj.detalleaprobacionproyecto_set.filter(status=True).first().observacion if obj.detalleaprobacionproyecto_set.filter(status=True) else ''


class ParticipanteProyectoVinculacionPosSerializer(Helper_ModelSerializer):
    proyectovinculacion = ProyectoVinculacionSerializer()
    download_link = serializers.SerializerMethodField()
    nombre = serializers.SerializerMethodField()
    fecha = serializers.SerializerMethodField()
    hora = serializers.SerializerMethodField()


    class Meta:
        model = ParticipanteProyectoVinculacionPos
        fields = ['id', 'status', 'proyectovinculacion',
                  'tipoevidencia', 'download_link', 'inscripcion', 'nombre', 'fecha', 'hora']

    def get_download_link(self, obj):
        if obj.evidencia.url:
            if obj.tipoevidencia == 1:
                return self.get_media_url(obj.evidencia.url)
            return obj.evidencia.name
        return ''

    def get_nombre(self, obj):
        return f'{obj.inscripcion.persona.apellido1} {obj.inscripcion.persona.apellido2} {obj.inscripcion.persona.nombres}'

    def get_fecha(self, obj):
        return obj.fecha_creacion.strftime('%Y-%m-%d')

    def get_hora(self, obj):
        return obj.fecha_creacion.strftime('%H:%M:%S')



class DetalleAprobacionProyectoSerializer(Helper_ModelSerializer):
    proyectovinculacion = ProyectoVinculacionSerializer()
    persona = serializers.SerializerMethodField()
    fecha = serializers.SerializerMethodField()
    hora = serializers.SerializerMethodField()

    class Meta:
        model = DetalleAprobacionProyecto
        fields = ['observacion', 'estadoaprobacion', 'proyectovinculacion', 'persona', 'fecha', 'hora']

    def get_persona(self, obj):
        return F'{obj.persona.apellido1} {obj.persona.apellido2} {obj.persona.nombres}'

    def get_fecha(self, obj):
        return obj.fecha_creacion.strftime('%Y-%m-%d')

    def get_hora(self, obj):
        return obj.fecha_creacion.strftime('%H:%M:%S')
