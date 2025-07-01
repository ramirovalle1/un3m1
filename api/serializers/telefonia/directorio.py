from rest_framework import serializers
from api.helpers.functions_helper import get_variable
from sagest.models import DistributivoPersona
from django.utils.text import capfirst


class DistributivoPersonaSerializer(serializers.ModelSerializer):
    persona = serializers.SerializerMethodField()
    foto = serializers.SerializerMethodField()
    denominacionpuesto = serializers.SerializerMethodField()
    unidadorganica = serializers.SerializerMethodField()
    telefono = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    class Meta:
        model = DistributivoPersona
        fields = ['id', 'persona', 'foto', 'denominacionpuesto', 'unidadorganica', 'telefono', 'email']

    def get_persona(self, obj):
        ePersona = obj.persona
        apellido1 = ePersona.apellido1
        apellido2 = ePersona.apellido2
        nombres = ePersona.nombres
        return f"{capfirst(apellido1.lower())} {capfirst(apellido2.lower())} {nombres.lower().title()}"

    def get_foto(self, obj):
        if obj.persona.tiene_foto():
            value = get_variable('SITE_URL_SGA')
            return f"{value}{obj.persona.foto().foto.url}"
        if obj.persona.sexo and obj.persona.sexo_id == 1:
            foto_perfil = '/static/images/iconos/mujer.png'
        else:
            foto_perfil = '/static/images/iconos/hombre.png'
        value = get_variable('SITE_URL_SGA')
        return f"{value}{foto_perfil}"

    def get_denominacionpuesto(self, obj):
        descripcion = obj.denominacionpuesto.descripcion
        return f"{capfirst(descripcion.lower())}"

    def get_unidadorganica(self, obj):
        unidadorganica = obj.unidadorganica.nombre
        return f"{capfirst(unidadorganica.lower())}"

    def get_telefono(self, obj):
        return obj.persona.telefonoextension

    def get_email(self, obj):
        return obj.persona.emailinst
