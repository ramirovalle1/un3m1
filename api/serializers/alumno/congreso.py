from api.helpers.serializers_model_helper import Helper_ModelSerializer
from rest_framework import serializers
from sagest.models import InscritoCongreso, Congreso, TipoParticipacionCongreso, Rubro


class RubroSerializer(Helper_ModelSerializer):
    class Meta:
        model = Rubro
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class CongresoSerializer(Helper_ModelSerializer):
    pk = serializers.SerializerMethodField()

    class Meta:
        model = Congreso
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_pk(self, obj):
        return obj.id


class TipoParticipacionCongresoSerializer(Helper_ModelSerializer):
    class Meta:
        model = TipoParticipacionCongreso
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']


class InscritoCongresoSerializer(Helper_ModelSerializer):
    congreso = CongresoSerializer()
    tipoparticipacion = TipoParticipacionCongresoSerializer()
    existerubrocurso_2 = serializers.SerializerMethodField()
    pagorubrocurso_2 = serializers.SerializerMethodField()
    rutapdfct = serializers.SerializerMethodField()

    class Meta:
        model = InscritoCongreso
        # fields = "__all__"
        exclude = ['usuario_creacion', 'usuario_modificacion']

    def get_existerubrocurso_2(selfl, obj):
        return obj.existerubrocurso_2()

    def get_pagorubrocurso_2(self, obj):
        return obj.pagorubrocurso_2()

    def get_rutapdfct(self, obj):
        return str(obj.rutapdf)


