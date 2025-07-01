from api.helpers.serializers_model_helper import Helper_ModelSerializer
from api.serializers.base.persona import PersonaBaseSerializer
from sga.models import ConvenioEmpresa, EmpresaEmpleadora, \
    TipoConvenio, ArchivoConvenio, TipoArchivoConvenio, \
    Persona, ConvenioCarrera
from sagest.models import DenominacionPuesto, DistributivoPersona

from rest_framework import serializers
from datetime import datetime

class ConvenioCarreraSerializer(Helper_ModelSerializer):

    modalidad = serializers.SerializerMethodField()

    class Meta:
        model = ConvenioCarrera
        fields = '__all__'

    def get_modalidad(self,obj):
        return obj.carrera.get_modalidad_display()

class TipoConvenioSerializer(Helper_ModelSerializer):
    class Meta:
        model = TipoConvenio
        # fields = ('nombre',)
        fields = '__all__'

class TipoArchivoConvenioSerializer(Helper_ModelSerializer):

    class Meta:
        model = TipoArchivoConvenio
        fields = '__all__'

class EmpresaEmpleadoraSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()

    class Meta:
        model = EmpresaEmpleadora
        fields = ('nombre','idm')

    def get_idm(self, obj):
        return obj.id

class PersonaResponsableSerializer(PersonaBaseSerializer):

    class Meta:
        model = Persona
        fields= ('nombre_completo', )
class DenominacionPuestoSerializer(Helper_ModelSerializer):
    class Meta:
        model = DenominacionPuesto
        fields = '__all__'

class DistributivoPersonaSerializer(Helper_ModelSerializer):
    denominacionpuesto = DenominacionPuestoSerializer()
    persona = PersonaResponsableSerializer()
    class Meta:
        model = DistributivoPersona
        fields = '__all__'

class ConvenioEmpresaSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    empresaempleadora = EmpresaEmpleadoraSerializer()
    tipoconvenio = TipoConvenioSerializer()
    # cargo_denominaciones = DenominacionPuestoSerializer()
    vigente = serializers.SerializerMethodField()
    tienecarreras = serializers.SerializerMethodField()
    archivosconvenio = serializers.SerializerMethodField()
    responsables = serializers.SerializerMethodField()

    carreras = serializers.SerializerMethodField()

    def get_idm(self, obj):
        return obj.id

    class Meta:
        model = ConvenioEmpresa
        fields = '__all__'

    def get_vigente(self, obj):
        fecha_actual = datetime.now().date()
        return "VIGENTE" if obj.fechafinalizacion > fecha_actual else "NO VIGENTE"

    def get_tienecarreras(self, obj):
        if obj.conveniocarrera_set.filter(status=True).exists():
            return True
        else:
            return False

    def get_carreras(self, obj):
        if obj.conveniocarrera_set.filter(status=True).exists():
            carreras = obj.conveniocarrera_set.filter(status=True)
            return ConvenioCarreraSerializer(carreras, many=True).data
        else:
            return None

    def get_responsables(self, obj):
        cargos = obj.cargo_denominaciones.all()
        distributivo = DistributivoPersona.objects.filter(denominacionpuesto__in=cargos, status=True)
        return DistributivoPersonaSerializer(distributivo, many=True).data
    def get_archivosconvenio(self, obj):
        archivos = obj.archivoconvenio_set.filter(status=True)
        return ArchivoConvenioSerializer(archivos, many= True).data if archivos else None


class ArchivoConvenioSerializer(Helper_ModelSerializer):
    idm = serializers.SerializerMethodField()
    tipoarchivoconvenio = TipoArchivoConvenioSerializer()
    download_link = serializers.SerializerMethodField()
    class Meta:
        model = ArchivoConvenio
        fields = '__all__'

    def get_idm(self, obj):
        return obj.id

    def get_download_link(self, obj):
        return self.get_media_url(obj.archivo.url)