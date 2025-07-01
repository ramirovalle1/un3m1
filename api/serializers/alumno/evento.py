from api.helpers.serializers_model_helper import Helper_ModelSerializer
from rest_framework import serializers

from api.serializers.base.persona import PersonaBaseSerializer
from even.models import PeriodoEvento, RegistroEvento, Evento, TipoEvento
from sga.models import Persona
from sga.templatetags.sga_extras import encrypt


class PersonaEventoSerializer(PersonaBaseSerializer):
    direccion_completa = serializers.SerializerMethodField()
    numero_asistire = serializers.SerializerMethodField()
    numero_pendiente = serializers.SerializerMethodField()
    numero_no_asistire = serializers.SerializerMethodField()

    class Meta:
        model = Persona
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_direccion_completa(self, obj):
        return obj.direccion_completa()

    def cantidad_confirmacion(self, obj, estado):
        return obj.registroevento_set.filter(status=True, estado_confirmacion=estado).values_list('id', flat=True).count()


    def get_numero_asistire(self, obj):
        return self.cantidad_confirmacion(obj, 1)

    def get_numero_pendiente(self, obj):
        return self.cantidad_confirmacion(obj, 0)

    def get_numero_no_asistire(self, obj):
        return self.cantidad_confirmacion(obj, 2)


class EventoSerializer(Helper_ModelSerializer):

    class Meta:
        model = Evento
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class TipoEventoSerializer(Helper_ModelSerializer):
    class Meta:
        model = TipoEvento
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class RegistroEventoSerializer(Helper_ModelSerializer):
    imagen = serializers.SerializerMethodField()
    periodo = serializers.SerializerMethodField()

    class Meta:
        model = RegistroEvento
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


    def get_imagen(self, obj):
        return self.get_media_url(obj.periodo.imagen.url) if obj.periodo.imagen.name != '' else None

    def get_periodo(self, obj):
        return encrypt(obj.periodo_id)

class PeriodoEventoSerializer(Helper_ModelSerializer):
    evento = EventoSerializer()
    tipo = TipoEventoSerializer()
    imagen = serializers.SerializerMethodField()
    inscrito = serializers.SerializerMethodField()
    portada = serializers.SerializerMethodField()
    no_confirme = serializers.SerializerMethodField()

    class Meta:
        model = PeriodoEvento
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_imagen(self, obj):
        return self.get_media_url(obj.imagen.url) if obj.imagen.name != '' else None

    def get_portada(self, obj):
        return self.get_media_url(obj.portada.url) if obj.portada.name != '' else self.get_static_url('/images/aok/bd_becas.png')

    def get_inscrito(self, obj):
        participante_id = self.context.get('participante_id', 0)
        inscrito = {}
        if (participante_id > 0):
            inscrito = obj.registroevento_set.filter(status=True, participante_id=participante_id).first()
            inscrito = RegistroEventoSerializer(inscrito).data if inscrito is not None else {}
        return inscrito

    def get_no_confirme(self, obj):
        participante_id = self.context.get('participante_id', 0)
        inscrito = {}
        if (participante_id > 0):
            inscrito = obj.registroevento_set.filter(status=True, participante_id=participante_id, estado_confirmacion=0).values_list('id', flat=True).exists()
        return inscrito
