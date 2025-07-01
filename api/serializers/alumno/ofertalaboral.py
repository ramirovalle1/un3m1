from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.helpers.formats_helper import *
from api.serializers.base.persona import PersonaBaseSerializer
from rest_framework import serializers
from sga.models import Matricula, Persona, OfertaLaboral, AreaOfertaLaboral, AplicanteOferta, AplicanteOfertaObservacion, Carrera, EmpresaEmpleadora, Sexo, Canton
from med.models import ProximaCita

class AplicanteOfertaObservacionSerializer(Helper_ModelSerializer):

    class Meta:
        model = AplicanteOfertaObservacion
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class AplicanteOfertaSerializer(Helper_ModelSerializer):
    confirmar_cita = serializers.SerializerMethodField()

    class Meta:
        model = AplicanteOferta
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']
    def get_confirmar_cita(self, obj):
        return obj.confirmar_cita()

class AreaOfertaLaboralSerializer(Helper_ModelSerializer):

    class Meta:
        model = AreaOfertaLaboral
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']
class CarreraSerializer(Helper_ModelSerializer):

    class Meta:
        model = Carrera
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class EmpresaEmpleadoraSerializer(Helper_ModelSerializer):

    class Meta:
        model = EmpresaEmpleadora
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class SexoSerializer(Helper_ModelSerializer):

    class Meta:
        model = Sexo
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

class CantonSerializer(Helper_ModelSerializer):

    class Meta:
        model = Canton
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']



class OfertaLaboralSerializer(Helper_ModelSerializer):
    canton = CantonSerializer()
    empresa = EmpresaEmpleadoraSerializer()
    area = AreaOfertaLaboralSerializer()
    esta_cerrada = serializers.SerializerMethodField()
    vercarreras = serializers.SerializerMethodField()
    sexo = SexoSerializer()
    class Meta:
        model = OfertaLaboral
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_esta_cerrada(self, obj):
        return obj.esta_cerrada()

    def get_vercarreras(self, obj):
        carr = obj.vercarreras()
        carrdetalle = CarreraSerializer(carr, many=True)
        return carrdetalle.data if carr.exists() else []


